#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""Hold the multi-store protocol models to the Isabelle model by trace validation (MSA-I6, the multi-store sketch's section 4.6 and MSA-Q17).

The protocol models A to D of tools/models/multi-store-protocols/ each state one of the four operations the multi-store model of
spikes/multi-store-model states as a command of its IR: A the delta replace, B the event append, C the create (or, where the row is created
beforehand, the first replace) and D the key claim write. Each model's store steps are written by hand in TLA+, and the IR's in Isabelle. This
check runs every behaviour TLC finds for a configuration through the interpreter Isabelle exports, and compares each step's outcome and the
state after it.

1. Finds TLC in the jar ``TLA2TOOLS_JAR`` names, Java as the models' runner does, and Isabelle as the formal-methods driver does. Where one is
   missing it says what it skipped and exits 0.
2. Builds and gates the session MultiStoreModel, exports its Scala, and compiles it, as generated, with the spike's driver
   ``replay/Replay.scala`` and this check's ``TraceReplay.scala``, under ``.build/formal/multi-store-traces/``.
3. Runs TLC on each configuration the manifest marks with ``trace``, with every invariant but ``TypeOK`` taken out so the whole state graph
   is explored, and has it dump the graph with each step's action (``-dump dot,actionlabels``), under ``.build/formal/tlc-traces/``.
4. Walks every behaviour from an initial state, in the product of the model's state graph and a tree of the IR commands met so far, so a
   step met in many behaviours with the same IR state before it is checked once. A store step becomes the IR command with its parameters. A
   step with no IR command, a client's read or a store's snapshot read or aborted commit, must leave the store as it was. The bump of the
   dataset epoch has no IR command, and is written into the IR's state as the entry its guard reads.
5. Runs the tree through the exported interpreter in one call, and compares, after every step, the outcome the model gives with the IR's and
   the state the model holds with the IR's, each read into the lines both hold.

A configuration marked ``trace = "agree"`` fails where any step disagrees, and one marked ``trace = "differ"``, a store weaker than the IR's
atomic step, fails where none does. Each disagreement found is printed with the shortest behaviour that reaches it.

Usage: python tools/models/trace_validation.py [configuration | pattern ...]
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lattice_repo_catalogue import load  # noqa: E402

CATALOGUE = load()
ROOT = CATALOGUE.root
MODELS = ROOT / CATALOGUE.area("tools") / "models" / "multi-store-protocols"
TRACE_SCALA = ROOT / CATALOGUE.area("tools") / "models" / "TraceReplay.scala"
PROOFS = ROOT / CATALOGUE.area("tools") / "proofs"
FORMAL_ENV = ROOT / CATALOGUE.area("spikes") / "formal-prover" / "env"
OUT = ROOT / ".build" / "formal" / "multi-store-traces"
TLC_WORK = ROOT / ".build" / "formal" / "tlc-traces"
EXPECTATIONS = ("agree", "differ")


# ---- TLC's values and state graph

class _Values:
    """A reader of the values TLC prints: numbers, strings, booleans, model values, sequences, sets, records and functions. A string and a
    model value are both read as a str, a sequence as a tuple, a set as a frozenset, and a record or a function as a dict."""

    def __init__(self, text: str) -> None:
        self.s, self.i = text, 0

    def _ws(self) -> None:
        while self.i < len(self.s) and self.s[self.i] in " \t\r\n":
            self.i += 1

    def _at(self, token: str) -> bool:
        self._ws()
        return self.s.startswith(token, self.i)

    def _eat(self, token: str) -> None:
        if not self._at(token):
            raise ValueError(f"expected {token!r} at {self.i} in {self.s!r}")
        self.i += len(token)

    def _name(self) -> str:
        self._ws()
        match = re.compile(r"[A-Za-z_][A-Za-z0-9_]*").match(self.s, self.i)
        if not match:
            raise ValueError(f"expected a name at {self.i} in {self.s!r}")
        self.i = match.end()
        return match.group(0)

    def _items(self, close: str) -> list:
        items = []
        if self._at(close):
            self._eat(close)
            return items
        while True:
            items.append(self.value())
            if self._at(","):
                self._eat(",")
                continue
            self._eat(close)
            return items

    def value(self):
        self._ws()
        if self._at("<<"):
            self._eat("<<")
            return tuple(self._items(">>"))
        c = self.s[self.i]
        if c == "{":
            self._eat("{")
            return frozenset(self._items("}"))
        if c == "[":
            self._eat("[")
            record: dict = {}
            if self._at("]"):
                self._eat("]")
                return record
            while True:
                key = self._name()
                self._eat("|->")
                record[key] = self.value()
                if self._at(","):
                    self._eat(",")
                    continue
                self._eat("]")
                return record
        if c == "(":
            self._eat("(")
            function: dict = {}
            while True:
                key = self.value()
                self._eat(":>")
                function[key] = self.value()
                if self._at("@@"):
                    self._eat("@@")
                    continue
                self._eat(")")
                return function
        if c == '"':
            j = self.i + 1
            text = []
            while self.s[j] != '"':
                if self.s[j] == "\\":
                    j += 1
                text.append(self.s[j])
                j += 1
            self.i = j + 1
            return "".join(text)
        match = re.compile(r"-?\d+").match(self.s, self.i)
        if match:
            self.i = match.end()
            return int(match.group(0))
        name = self._name()
        return {"TRUE": True, "FALSE": False}.get(name, name)


def tla_value(text: str):
    reader = _Values(text)
    value = reader.value()
    reader._ws()
    if reader.i != len(reader.s):
        raise ValueError(f"text after the value in {text!r}")
    return value


def tla_state(text: str) -> dict:
    """A state as TLC prints it, one ``/\\ name = value`` a conjunct, a value perhaps over several lines."""
    state, current = {}, None
    for line in text.splitlines():
        if line.startswith("/\\ "):
            current = line[3:]
            name, _, value = current.partition(" = ")
            state[name.strip()] = value
        elif current is not None and state:
            last = next(reversed(state))
            state[last] += "\n" + line
    return {name: tla_value(value) for name, value in state.items()}


def _unescape(text: str) -> str:
    out, i = [], 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            out.append("\n" if text[i + 1] == "n" else text[i + 1])
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


_NODE = re.compile(r'^(-?\d+) \[label="((?:[^"\\]|\\.)*)"(.*)\]')
_EDGE = re.compile(r'^(-?\d+) -> (-?\d+) \[label="((?:[^"\\]|\\.)*)"')


@dataclass
class Graph:
    states: dict = field(default_factory=dict)     # node id -> state
    inits: list = field(default_factory=list)      # the initial states' ids, in the order TLC wrote them
    edges: list = field(default_factory=list)      # (from, to, action)
    out: dict = field(default_factory=dict)        # node id -> indices into edges


def read_dot(text: str) -> Graph:
    """The state graph ``-dump dot,actionlabels`` writes. An initial state is the one TLC fills."""
    graph, seen_edges = Graph(), set()
    for line in text.splitlines():
        edge = _EDGE.match(line)
        if edge:
            key = (edge.group(1), edge.group(2), _unescape(edge.group(3)))
            if key not in seen_edges:
                seen_edges.add(key)
                graph.out.setdefault(key[0], []).append(len(graph.edges))
                graph.edges.append(key)
            continue
        node = _NODE.match(line)
        if node and node.group(1) not in graph.states:
            graph.states[node.group(1)] = tla_state(_unescape(node.group(2)))
            if "filled" in node.group(3):
                graph.inits.append(node.group(1))
    for n in graph.states:
        graph.out.setdefault(n, [])
    return graph


def behaviours(graph: Graph, weight) -> tuple[int, int, int]:
    """The behaviours of an acyclic state graph, each from an initial state to a state with no successor, the steps they hold together, and
    how many of those steps ``weight`` counts, each counted once in every behaviour it is in."""
    indegree = Counter(to for _, to, _ in graph.edges)
    order, ready = [], [n for n in graph.states if indegree[n] == 0]
    while ready:
        n = ready.pop()
        order.append(n)
        for e in graph.out[n]:
            to = graph.edges[e][1]
            indegree[to] -= 1
            if indegree[to] == 0:
                ready.append(to)
    if len(order) != len(graph.states):
        raise SystemExit("the state graph has a cycle, so its behaviours are not finite")
    paths, steps, weighted = {}, {}, {}
    for n in reversed(order):
        succ = [(graph.edges[e][1], e) for e in graph.out[n]]
        paths[n] = sum(paths[m] for m, _ in succ) if succ else 1
        steps[n] = sum(paths[m] + steps[m] for m, _ in succ)
        weighted[n] = sum(paths[m] * weight(e) + weighted[m] for m, e in succ)
    return (sum(paths[i] for i in graph.inits), sum(steps[i] for i in graph.inits), sum(weighted[i] for i in graph.inits))


# ---- each model's steps read as the IR's commands

@dataclass(frozen=True)
class Step:
    kind: str                  # "ir" a command of the IR, "ext" a step the IR has no command for that changes the store, "none" no store change
    key: tuple | None = None   # ("C", op, arg, params) or ("X", "depoch", n)
    outcome: str | None = None  # the outcome the model gives an IR command


def _actor(src: dict, dst: dict, var: str = "pc") -> str | None:
    moved = [w for w in src[var] if src[var][w] != dst[var][w]]
    return moved[0] if len(moved) == 1 else None


def _ir_fields(line: str) -> tuple[list[str], dict]:
    parts = line.split("\t")
    return parts, {p.split("=", 1)[0]: p.split("=", 1)[1] for p in parts if "=" in p}


class Mapping:
    """How one model's states and steps are read in the IR's terms."""
    store_steps: tuple = ()     # the actions that are one request to the store
    no_command: dict = {}       # the actions with no IR command, and what each is
    ir_only: str = ""           # what the IR's state holds that the model's does not
    model_only: str = ""        # what the model holds that the IR's state does not

    def __init__(self, constants: dict) -> None:
        self.constants = constants

    def seed(self, state: dict) -> tuple:
        return ()

    def command(self, src: dict, dst: dict, actor: str) -> tuple:
        raise NotImplementedError

    def outcome(self, src: dict, dst: dict, actor: str) -> str:
        return dst["reply"][actor]

    def step(self, src: dict, dst: dict, action: str) -> Step:
        if action in self.store_steps:
            actor = _actor(src, dst)
            return Step("ir", ("C", *self.command(src, dst, actor)), self.outcome(src, dst, actor))
        if action == "BumpStep":
            return Step("ext", ("X", "depoch", str(dst["dEpoch"])))
        if action in self.no_command:
            return Step("none")
        raise SystemExit(f"{type(self).__name__} has no reading of the action {action}")

    def model_lines(self, state: dict) -> list[str]:
        raise NotImplementedError

    def ir_lines(self, dump: list[str]) -> list[str]:
        raise NotImplementedError


def _request(w: str) -> tuple:
    return (("PA", "TxnId", f"txn-{w}"), ("PA", "RequestDigest", f"digest-{w}"))


class ModelA(Mapping):
    """Model A, a guarded compare-and-set, as the IR's delta replace with an empty delta."""
    store_steps = ("Cas", "Commit")
    no_command = {"Read": "the client reads the row", "Eval": "the store evaluates the guard against a snapshot"}
    ir_only = "the head, the transaction claim, the receipt's revision and previous head, the patch log and the aggregate's facts"
    model_only = "each writer's program counter, the value it read and whether its snapshot's guard held"

    def seed(self, state: dict) -> tuple:
        return (("SV", self.constants["Target"], "1", "0", ""),)

    def command(self, src: dict, dst: dict, w: str) -> tuple:
        return ("replace", "-", (("PA", "Root", self.constants["Target"]), ("PN", "EpochP", "1"),
                                 ("PN", "ExpectedSeq", str(src["expected"][w])), ("PA", "NewRev", f"rev-{w}"), *_request(w),
                                 ("PE", "Asserted", ""), ("PE", "Retracted", "")))

    def outcome(self, src: dict, dst: dict, w: str) -> str:
        # Model A names no outcome. A request that adds no entry to the log failed its one guard, the expected sequence.
        return "Applied" if len(dst["log"]) > len(src["log"]) else "Conflict Stale"

    def model_lines(self, s: dict) -> list[str]:
        return sorted([f"row seq={s['seq']}"] + [f"rcpt {e['new']} txn-{e['writer']}" for e in s["log"]])

    def ir_lines(self, dump: list[str]) -> list[str]:
        lines = []
        for line in dump:
            parts, f = _ir_fields(line)
            if parts[0] == "vrow":
                lines.append(f"row seq={f['seq']}")
            elif parts[0] == "rcpt":
                lines.append(f"rcpt {parts[3]} {f['txn']}")
        return sorted(lines)


_SNAPSHOT_STEPS = {"Eval": "the store evaluates the guards against a snapshot",
                   "Abort": "the store aborts a commit for a write-write conflict and writes nothing",
                   "ResendStep": "the writer sends its request again"}


class ModelB(Mapping):
    """Model B, the append form, as the IR's event append under the dataset guard."""
    store_steps = ("Exec", "Commit")
    no_command = {"Read": "the writer reads the dataset epoch", **_SNAPSHOT_STEPS,
                  "BumpStep": "the dataset epoch is bumped, which the IR states no command for"}
    ir_only = "the row's head, the receipt's revision and previous head, and the claim's revision and digest"
    model_only = "each writer's program counter, the epoch it read, its reply, its snapshot and its retries, the dataset epoch in force when an append applied, and the statements each transaction wrote"

    def seed(self, state: dict) -> tuple:
        return (("SV", "stream", "1", "0", ""), ("SD", "1"))

    def command(self, src: dict, dst: dict, w: str) -> tuple:
        return ("append", "-", (("PA", "Stream", "stream"), ("PN", "EpochP", str(src["epochOf"][w])), ("PA", "RevBase", "rev/"),
                                *_request(w), ("PF", "EventRows", f"ROW ev-{w}")))

    def model_lines(self, s: dict) -> list[str]:
        return sorted([f"depoch={s['dEpoch']}", f"row epoch={s['row']['epoch']} seq={s['row']['seq']}"]
                      + [f"txn txn-{w}" for w in s["txns"]]
                      + [f"rcpt {e['epoch']} {e['pos']} txn-{e['w']}" for e in s["log"]]
                      + [f"evt {e['pos']} ev-{e['w']}" for e in s["log"]])

    def ir_lines(self, dump: list[str]) -> list[str]:
        lines = []
        for line in dump:
            parts, f = _ir_fields(line)
            if parts[0] == "depoch":
                lines.append(f"depoch={parts[1]}")
            elif parts[0] == "vrow":
                lines.append(f"row epoch={f['epoch']} seq={f['seq']}")
            elif parts[0] == "txn":
                lines.append(f"txn {parts[1]}")
            elif parts[0] == "rcpt":
                lines.append(f"rcpt {parts[2]} {parts[3]} {f['txn']}")
            elif parts[0] == "evrow":
                lines.append(f"evt {parts[2]} {parts[3]}")
        return sorted(lines)


class ModelC(Mapping):
    """Model C, the first write, as the IR's create, or as its delta replace expecting seq 0 where the row was created beforehand."""
    store_steps = ("Exec", "Commit")
    no_command = dict(_SNAPSHOT_STEPS)
    ir_only = "the row's epoch and tombstone flag, the receipt's revision and previous head, the claim's revision and digest, the patch log and the aggregate's facts"
    model_only = "a second head on the row and a second receipt at seq 1, which RDF can hold and the IR's keyed entries cannot, each writer's program counter, reply, snapshot and retries, and the statements each transaction wrote"

    def seed(self, state: dict) -> tuple:
        return (("SV", "root", "1", "0", ""),) if self.constants["FirstWrite"] == "PreCreatedRow" else ()

    def command(self, src: dict, dst: dict, w: str) -> tuple:
        common = (("PA", "Root", "root"), ("PN", "EpochP", "1"), ("PA", "NewRev", f"rev-{w}"), *_request(w))
        if self.constants["FirstWrite"] == "PreCreatedRow":
            return ("replace", "-", (*common, ("PN", "ExpectedSeq", "0"), ("PF", "Asserted", f"fact-{w}"), ("PE", "Retracted", "")))
        return ("create", "-", (*common, ("PF", "Payload", f"fact-{w}")))

    def model_lines(self, s: dict) -> list[str]:
        lines = []
        if s["row"]["exists"]:
            lines += [f"row seq={s['row']['seq']}"] + [f"head rev-{h}" for h in s["row"]["heads"]]
        lines += [f"rcpt {e['seq']} txn-{e['w']}" for e in s["log"]] + [f"txn txn-{w}" for w in s["txns"]]
        return sorted(lines)

    def ir_lines(self, dump: list[str]) -> list[str]:
        lines = []
        for line in dump:
            parts, f = _ir_fields(line)
            if parts[0] == "vrow":
                lines.append(f"row seq={f['seq']}")
                if f["head"] != "-":
                    lines.append(f"head {f['head']}")
            elif parts[0] == "rcpt":
                lines.append(f"rcpt {parts[3]} {f['txn']}")
            elif parts[0] == "txn":
                lines.append(f"txn {parts[1]}")
        return sorted(lines)


class ModelD(Mapping):
    """Model D, the key claim, as the IR's key claim write."""
    store_steps = ("Exec", "Commit")
    no_command = dict(_SNAPSHOT_STEPS)
    ir_only = "nothing beyond the claim's constraint and owner"
    model_only = "a second owner on the claim, which RDF can hold and the IR's one Owner field cannot, the sentinel's counter, each owner's program counter, reply, snapshot and retries, and the statements each transaction wrote"

    def command(self, src: dict, dst: dict, o: str) -> tuple:
        return ("claim", "k1", (("PA", "ClaimP", "claim-1"), ("PA", "OwnerP", o)))

    def model_lines(self, s: dict) -> list[str]:
        return sorted((["claim constraint=k1"] if s["owners"] else []) + [f"owner {o}" for o in s["owners"]])

    def ir_lines(self, dump: list[str]) -> list[str]:
        lines = []
        for line in dump:
            parts, f = _ir_fields(line)
            if parts[0] == "claim":
                lines += [f"claim constraint={f['constraint']}", f"owner {f['owner']}"]
        return sorted(lines)


MAPPINGS = {"ModelA_GuardedCas": ModelA, "ModelB_AppendForm": ModelB, "ModelC_CreateRace": ModelC, "ModelD_KeyClaim": ModelD}


# ---- the tree of IR commands and the walk of the product

class Tree:
    """The IR's steps met in the behaviours, as a tree whose nodes share their common prefixes. Node ids are global across configurations,
    and a node is created after its parent."""

    def __init__(self) -> None:
        self.records: list[str] = []
        self.children: dict = {}
        self.count = 0

    def root(self, seed: tuple) -> int:
        key = ("root", seed)
        if key not in self.children:
            self.count += 1
            self.children[key] = self.count
            self.records.append(f"R\t{self.count}")
            self.records += ["\t".join(record) for record in seed]
        return self.children[key]

    def child(self, parent: int, key: tuple) -> int:
        if (parent, key) not in self.children:
            self.count += 1
            self.children[(parent, key)] = self.count
            if key[0] == "C":
                _, op, arg, params = key
                self.records.append(f"N\t{self.count}\t{parent}\tC\t{op}\t{arg}")
                self.records += ["\t".join(p) for p in params]
            else:
                self.records.append(f"N\t{self.count}\t{parent}\tX\t{key[1]}\t{key[2]}")
        return self.children[(parent, key)]


@dataclass
class Walk:
    name: str
    mapping: Mapping
    graph: Graph
    roots: dict = field(default_factory=dict)          # initial state -> tree node
    checks: list = field(default_factory=list)         # (tree node, model state, outcome or None, source key or None, edge or None)
    unchanged: list = field(default_factory=list)      # edges with no IR command whose store state changed
    parent: dict = field(default_factory=dict)         # product key -> (product key, edge) it was first reached by
    product_edges: int = 0
    kinds: Counter = field(default_factory=Counter)


def walk(name: str, mapping: Mapping, graph: Graph, tree: Tree) -> Walk:
    w = Walk(name, mapping, graph)
    steps = [mapping.step(graph.states[a], graph.states[b], action) for a, b, action in graph.edges]
    lines = {n: mapping.model_lines(s) for n, s in graph.states.items()}
    for e, (a, b, action) in enumerate(graph.edges):
        w.kinds[(action, steps[e].kind)] += 1
        if steps[e].kind == "none" and lines[a] != lines[b]:
            w.unchanged.append(e)
    queue = deque()
    for i in graph.inits:
        r = tree.root(mapping.seed(graph.states[i]))
        w.roots[i] = r
        w.checks.append((r, i, None, None, None))
        w.parent[(i, r)] = None
        queue.append((i, r))
    while queue:
        n, t = queue.popleft()
        for e in graph.out[n]:
            m, step = graph.edges[e][1], steps[e]
            w.product_edges += 1
            if step.kind == "none":
                t2 = t
            else:
                t2 = tree.child(t, step.key)
                w.checks.append((t2, m, step.outcome, (n, t), e))
            if (m, t2) not in w.parent:
                w.parent[(m, t2)] = ((n, t), e)
                queue.append((m, t2))
    w.steps = steps
    return w


def witness(w: Walk, key, last_edge: int) -> list[str]:
    """The shortest behaviour the walk found to ``key``, then ``last_edge``, as each step's action and actor."""
    edges = [last_edge]
    while w.parent.get(key) is not None:
        key, e = w.parent[key]
        edges.append(e)
    out = []
    for e in reversed(edges):
        a, b, action = w.graph.edges[e]
        actor = _actor(w.graph.states[a], w.graph.states[b]) if "pc" in w.graph.states[a] else None
        out.append(f"{action}({actor})" if actor else action)
    return out


# ---- the tools

def isabelle_missing() -> str | None:
    sys.path.insert(0, str(FORMAL_ENV))
    from install_native import isabelle_executable  # noqa: E402

    return None if isabelle_executable() else "no Isabelle was found from FMX_ISABELLE, the formal root or the path"


def trace_cfg(text: str) -> str:
    """The configuration with every invariant and property but TypeOK taken out, so TLC explores the whole graph."""
    kept = []
    for line in text.splitlines():
        if re.match(r"^\s*(INVARIANTS?|PROPERTY|PROPERTIES)\b", line):
            break
        kept.append(line)
    return "\n".join(kept + ["INVARIANT", "    TypeOK", ""])


def constants(text: str) -> dict:
    found = {}
    for line in text.splitlines():
        match = re.match(r"^\s*(\w+)\s*=\s*(.+?)\s*$", line)
        if match:
            value = match.group(2)
            found[match.group(1)] = value[1:-1] if value.startswith('"') and value.endswith('"') else value
    return found


def dump_graph(entry: dict, java: str, jar: str) -> tuple[Graph, str]:
    directory = TLC_WORK / entry["name"]
    if directory.exists():
        shutil.rmtree(directory)
    (directory / "tmp").mkdir(parents=True)
    for source in MODELS.glob("*.tla"):
        shutil.copy2(source, directory)
    cfg_text = (MODELS / entry["config"]).read_text(encoding="utf-8")
    (directory / "trace.cfg").write_text(trace_cfg(cfg_text), encoding="utf-8", newline="\n")
    command = [java, "-Xmx1024m", "-XX:+UseParallelGC", "-Djava.io.tmpdir=tmp", "-cp", jar, "tlc2.TLC", "-workers", "1", "-deadlock",
               "-dump", "dot,actionlabels", "states.dot", "-config", "trace.cfg", f"{entry['module']}.tla"]
    with open(directory / "tlc.out", "w", encoding="utf-8", newline="\n") as out:
        subprocess.run(command, cwd=directory, stdout=out, stderr=subprocess.STDOUT, check=False)
    output = (directory / "tlc.out").read_text(encoding="utf-8", errors="replace")
    if "Model checking completed. No error has been found." not in output:
        raise SystemExit(f"TLC did not complete {entry['name']} with TypeOK alone. Output in {directory.as_posix()}")
    counts = re.search(r"([\d,]+) states generated, ([\d,]+) distinct states found", output)
    graph = read_dot((directory / "states.dot").read_text(encoding="utf-8"))
    printed = f"{counts.group(2)} distinct of {counts.group(1)} generated" if counts else "no count printed"
    return graph, printed


def build_interpreter() -> Path:
    """Builds and gates the session, exports it, and compiles the generated Scala with the two drivers. Returns the classes directory."""
    sys.path.insert(0, str(PROOFS))
    import multi_store_replay as replay  # noqa: E402

    OUT.mkdir(parents=True, exist_ok=True)
    print("-- building and gating the session MultiStoreModel", flush=True)
    built = subprocess.run([sys.executable, str(PROOFS / "check.py"), "multi-store-model"], cwd=ROOT, check=False)
    if built.returncode != 0:
        raise SystemExit("the session did not build or its gate failed")
    export = OUT / "export"
    replay.step("isabelle export", replay.isabelle("export", "-d", "base", "-d", "shared", "-d", replay.rel(replay.SPIKE), "-n", "-O",
                                                   replay.rel(export), "-x", "'*:code/**'", replay.SESSION))
    generated = export / f"{replay.SESSION}.Export" / "code" / "multi_store_model.scala"
    if not generated.is_file():
        raise SystemExit(f"no generated Scala at {generated.relative_to(ROOT).as_posix()}")
    classes = OUT / "classes"
    if classes.exists():
        shutil.rmtree(classes)
    classes.mkdir()
    compiled = replay.isabelle("scalac", "-d", replay.rel(classes), replay.rel(generated), replay.rel(replay.SPIKE / "replay" / "Replay.scala"),
                               replay.rel(TRACE_SCALA))
    replay.step("isabelle scalac", compiled)
    print(f"   generated {generated.relative_to(ROOT).as_posix()}, used as generated, compiled with replay/Replay.scala and "
          f"{TRACE_SCALA.relative_to(ROOT).as_posix()}", flush=True)
    return classes


def run_interpreter(classes: Path, tree: Tree) -> tuple[dict, dict]:
    sys.path.insert(0, str(PROOFS))
    import multi_store_replay as replay  # noqa: E402

    tsv, result = OUT / "tree.tsv", OUT / "tree-out.txt"
    tsv.write_text("\n".join(tree.records) + "\n", encoding="utf-8", newline="\n")
    replay.step("TraceReplay", replay.isabelle("scala", "-cp", replay.rel(classes), "TraceReplay", "tree", tsv.resolve().as_posix(),
                                               result.resolve().as_posix()))
    outcomes, states = {}, {}
    for line in result.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t", 2)
        if parts[0] == "O":
            outcomes[int(parts[1])] = parts[2]
            states.setdefault(int(parts[1]), [])
        elif parts[0] == "S":
            states.setdefault(int(parts[1]), []).append(parts[2])
    return outcomes, states


# ---- the check

def judge(w: Walk, outcomes: dict, states: dict) -> list[str]:
    """Every disagreement of the walk, as lines, the first of each kind with its shortest behaviour."""
    findings, shown = [], set()
    disagreements = Counter()
    for t, m, outcome, source, e in w.checks:
        ir_out, ir_lines = outcomes.get(t), w.mapping.ir_lines(states.get(t, []))
        model_lines = w.mapping.model_lines(w.graph.states[m])
        kinds = []
        if outcome is not None and ir_out != outcome:
            kinds.append(f"outcome: the model gives {outcome}, the IR {ir_out}")
        if ir_lines != model_lines:
            only_model = sorted((Counter(model_lines) - Counter(ir_lines)).elements())
            only_ir = sorted((Counter(ir_lines) - Counter(model_lines)).elements())
            kinds.append(f"state: only in the model {only_model}, only in the IR {only_ir}")
        if not kinds:
            continue
        disagreements["outcome" if outcome is not None and ir_out != outcome else "state"] += 1
        label = "init" if e is None else w.graph.edges[e][2]
        if (label, kinds[0].split(":")[0]) in shown:
            continue
        shown.add((label, kinds[0].split(":")[0]))
        trace = "the initial state" if e is None else " ".join(witness(w, source, e))
        findings.append(f"   at {trace}: " + ". ".join(kinds))
    for e in w.unchanged:
        a, b, action = w.graph.edges[e]
        findings.append(f"   {action} has no IR command and changed the store: {w.mapping.model_lines(w.graph.states[a])} to "
                        f"{w.mapping.model_lines(w.graph.states[b])}")
        disagreements["store moved by a step with no IR command"] += 1
    w.disagreements = disagreements
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("selectors", nargs="*", help="configuration names or patterns among those the manifest marks with trace. Default: all")
    args = parser.parse_args(argv)

    entries = [e for e in tomllib.loads((MODELS / "manifest.toml").read_text(encoding="utf-8"))["configuration"] if "trace" in e]
    for e in entries:
        if e["trace"] not in EXPECTATIONS or e["module"] not in MAPPINGS:
            raise SystemExit(f"manifest.toml: {e['name']} has trace {e['trace']!r} or a module this check cannot read, {e['module']}")
    if args.selectors:
        entries = [e for e in entries if any(fnmatch.fnmatchcase(e["name"], s) for s in args.selectors)]
        if not entries:
            raise SystemExit(f"no configuration marked with trace matches {args.selectors}")
    print(f"traces: {len(entries)} configuration(s) of multi-store-protocols, each held to the exported interpreter", flush=True)

    jar = os.environ.get("TLA2TOOLS_JAR")
    if not jar or not Path(jar).is_file():
        print(f"SKIP: TLA2TOOLS_JAR {'names no file' if jar else 'is not set'}, so no trace was checked. Set it to the TLA+ tools jar")
        return 0
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from check_tlc import find_java  # noqa: E402

    java = find_java()
    if java is None:
        print("SKIP: no java on the path or from `mise where java`, so no trace was checked. Run through mise")
        return 0
    missing = isabelle_missing()
    if missing:
        print(f"SKIP: {missing}, so no trace was checked. Run `mise run bootstrap:formal-native-isabelle`, or set FMX_ISABELLE")
        return 0

    tree, walks = Tree(), []
    for entry in entries:
        graph, printed = dump_graph(entry, java, jar)
        mapping = MAPPINGS[entry["module"]](constants((MODELS / entry["config"]).read_text(encoding="utf-8")))
        w = walk(entry["name"], mapping, graph, tree)
        w.entry, w.printed = entry, printed
        walks.append(w)
        print(f"-- {entry['name']}: TLC {printed}, {len(graph.states):,} states and {len(graph.edges):,} steps read from its dump", flush=True)

    classes = build_interpreter()
    outcomes, states = run_interpreter(classes, tree)
    print(f"-- the exported interpreter ran {tree.count:,} tree nodes, each an IR command, a seed or a step it has no command for")

    failed = 0
    for w in walks:
        findings = judge(w, outcomes, states)
        count, steps, ir_steps = behaviours(w.graph, lambda e, w=w: 1 if w.steps[e].kind != "none" else 0)
        agrees = not w.disagreements
        expected = w.entry["trace"]
        ok = agrees == (expected == "agree")
        failed += not ok
        verdict = "every step agrees" if agrees else "disagrees, " + ", ".join(f"{n} {k}" for k, n in sorted(w.disagreements.items()))
        print(f"{'PASS' if ok else 'FAIL'} {w.name}: {verdict}, expected to {expected}. {count:,} behaviours of {steps:,} steps, "
              f"{ir_steps:,} of them store steps run through the IR, {len(w.checks):,} checks over {w.product_edges:,} steps of the product "
              f"of {len(w.parent):,} pairs of a model state and an IR state")
        no_command = sorted({a for (a, kind), n in w.kinds.items() if kind == "none"})
        external = sorted({a for (a, kind), n in w.kinds.items() if kind == "ext"})
        tally = Counter(outcomes.get(t) for t, _, outcome, _, _ in w.checks if outcome is not None)
        print(f"   the IR's outcomes over the steps checked: {', '.join(f'{k} {n:,}' for k, n in sorted(tally.items()))}")
        print(f"   steps with no IR command, the store unchanged: {', '.join(no_command) or 'none'}")
        if external:
            print(f"   steps with no IR command that change the store, written into the IR's state: {', '.join(external)}")
        print(f"   the IR holds and the model does not: {w.mapping.ir_only}")
        print(f"   the model holds and the IR does not: {w.mapping.model_only}")
        for line in findings:
            print(line)
    passed = len(walks) - failed
    print(f"traces: {passed} as expected, {failed} failed, {tree.count:,} interpreter steps")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
