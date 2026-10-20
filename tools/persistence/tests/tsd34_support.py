# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Support for the TSD-34 behaviour tests (formal-methods H2.6g). rdflib 7.6.0 may evaluate a `FILTER NOT EXISTS` with no `GRAPH` of its own, inside
a `GRAPH` block, against the default graph, depending on `PYTHONHASHSEED` (TSD-34). A test that probes this on rdflib must sweep seeds in child
processes. The parent here makes a *scenario* for every builder whose rendered text has the shape, as plain strings, and a child process runs them all
under one seed (`python tsd34_support.py <json file>`), so the sweep compiles the corpus once and imports no persistence package in the child."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import warnings
from pathlib import Path

from rdflib import Dataset, Literal, URIRef
from rdflib.namespace import XSD
from rdflib.util import from_n3

PAT = "https://example.org/lattice/patterns#"
ROOT = "urn:root:1"
LONG = lambda n: Literal(n, datatype=XSD.long)


def _iri(term) -> str:
    return str(term).strip("<>")


def scenario(stem: str, *, deleted: bool = True) -> dict:
    """A deleted row that has three heads and three current versions, so the block of the write holds several solutions before its
    `NOT EXISTS`, and the write the builder gives for `stem`. Nothing may change, because the row is tombstoned. With `deleted` false the row is
    live and the write must change the dataset, which shows the scenario is sound. Terms are N3 strings."""
    from persistence.builders import build
    from persistence.ir import Kind
    from persistence.ir_render import render
    from request_slots import fill_request_slots
    from test_builders import _first

    context = _first(stem)[3]
    op = build(stem, context)
    values = {
        "epoch": LONG(1), "expectedSeq": LONG(1), "nextSeq": LONG(2), "root": URIRef(ROOT), "requestDigest": Literal("ab" * 32),
    }
    params = {}
    for p in op.params:
        if p.kind in (Kind.PAYLOAD, Kind.ROWS, Kind.REGISTRY_LIST):
            continue
        params[p.name] = values.get(p.name) or URIRef(f"urn:p:{p.name}")
    meta = _iri(context["metaGraphPrefix"])
    quads = [(meta, ROOT, PAT + "epoch", LONG(1)), (meta, ROOT, PAT + "seq", LONG(1))]
    if deleted:
        quads.append((meta, ROOT, PAT + "deleted", Literal(True)))
    quads += [(meta, ROOT, PAT + "head", URIRef(f"urn:rev:h{i}")) for i in range(3)]
    quads += [(meta, ROOT, PAT + "currentVersion", URIRef(f"urn:version:v{i}")) for i in range(3)]
    if "datasetGraph" in context:
        quads.append((_iri(context["datasetGraph"]), _iri(context["datasetNode"]), PAT + "epoch", LONG(1)))
    return {
        "text": fill_request_slots(render(op)),
        "quads": [[g, s, p, o.n3() if hasattr(o, "n3") else URIRef(o).n3()] for g, s, p, o in quads],
        "params": {k: v.n3() for k, v in params.items()},
    }


def run_scenario(sc: dict, ds) -> bool:
    """Whether the write changed the dataset. `ds` is a dataset on the engine under test."""
    for g, s, p, o in sc["quads"]:
        ds.graph(URIRef(g)).add((URIRef(s), URIRef(p), from_n3(o)))
    before = {(str(g.identifier), t) for g in ds.graphs() for t in g}
    ds.update(sc["text"], initBindings={k: from_n3(v) for k, v in sc["params"].items()})
    return before != {(str(g.identifier), t) for g in ds.graphs() for t in g}


def members_probe() -> list:
    """The versions at which the `members` read is wrong, on the engine `engines.CURRENT` names. Nine versions with a checkpoint every 4, at versions 1, 4
    and 8, and a stray add at 2 and at 5 that no later list restates. A version after a checkpoint must not see the add before it, so a `NOT EXISTS`
    that keeps a checkpoint that is not the nearest one lets a stray add through. Which `?cp` is tested first follows the hash seed (TSD-34)."""
    import engines
    from test_membership import ADDS, DATA, L, history, members_of, store, version

    ds = store()
    model = history(ds, [({L(1), L(2)}, ())] + [({L(10 + n)}, ({L(n)} if n < 4 else ())) for n in range(1, 9)])
    ds.graph(DATA).add((version(2), ADDS, L(900)))
    ds.graph(DATA).add((version(5), ADDS, L(901)))
    wrong = []
    for n in range(1, 10):
        got = members_of(ds, n)
        want = model[n - 1] | ({L(900)} if 2 <= n <= 3 else set()) | ({L(901)} if 5 <= n <= 7 else set())
        if got != want:
            wrong.append(n)
    return wrong


def random_histories_probe(per_interval: int = 8) -> list:
    """The (interval, history, version) triples at which the `members` read differs from the reference model, on the engine `engines.CURRENT` names
    (H2.8c, TD-68). For checkpoints every 2, 3 and 4 versions, ``per_interval`` random histories of 5 to 13 versions, each adding and dropping up to
    two members per version, with two stray adds that no later list restates. A stray add at version k is a member from k until the next checkpoint
    after k, whether or not k is itself one. The histories are fixed by their own seeds, so only the hash seed varies between child processes."""
    import random

    from test_membership import ADDS, DATA, L, history, members_of, store, version
    from persistence.members import is_checkpoint

    wrong = []
    for every in (2, 3, 4):
        for h in range(per_interval):
            rng = random.Random(1000 * every + h)
            state = {L(i) for i in range(6)}
            steps = [(set(state), ())]
            for _ in range(rng.randint(4, 12)):
                drop = set(rng.sample(sorted(state, key=str), min(len(state), rng.randint(0, 2))))
                add = set(rng.sample(sorted({L(i) for i in range(100, 140)} - state, key=str), rng.randint(0, 2)))
                state = (state - drop) | add
                steps.append((add, drop))
            ds = store()
            model = history(ds, steps, every=every)
            count = len(steps)
            strays = {k: L(900 + k) for k in rng.sample(range(2, count + 1), 2)}
            for k, m in strays.items():
                ds.graph(DATA).add((version(k), ADDS, m))
            checkpoints = [n for n in range(1, count + 1) if is_checkpoint(n, every)]
            for n in range(1, count + 1):
                want = set(model[n - 1]) | {m for k, m in strays.items() if k <= n < min([c for c in checkpoints if c > k] or [count + 1])}
                if members_of(ds, n) != want:
                    wrong.append((every, h, n))
    return wrong


def sweep_random_histories(seeds=range(16)) -> set:
    """The lists of wrong versions over the seeds, each seed in a child process. The children run side by side, since each takes tens of seconds."""
    here = Path(__file__).resolve()
    children = [
        subprocess.Popen([sys.executable, str(here), "random-histories"], env={**os.environ, "PYTHONHASHSEED": str(seed)}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for seed in seeds
    ]
    out = set()
    for child in children:
        stdout, stderr = child.communicate()
        if child.returncode != 0:
            raise subprocess.CalledProcessError(child.returncode, child.args, stdout, stderr)
        out.add(stdout.strip())
    return out


def sweep(scenarios: dict, seeds=range(16)) -> dict:
    """For each stem, the set of outcomes over the seeds, each seed in a child process. `True` means the tombstoned row was written."""
    here = Path(__file__).resolve()
    out = {stem: set() for stem in scenarios}
    for seed in seeds:
        proc = subprocess.run(
            [sys.executable, str(here)], input=json.dumps(scenarios), env={**os.environ, "PYTHONHASHSEED": str(seed)},
            capture_output=True, text=True, check=True,
        )
        for stem, changed in json.loads(proc.stdout).items():
            out[stem].add(changed)
    return out


def sweep_members(seeds=range(16)) -> set:
    """The sets of wrong versions over the seeds, each in a child process."""
    here = Path(__file__).resolve()
    return {
        subprocess.run([sys.executable, str(here), "members"], env={**os.environ, "PYTHONHASHSEED": str(seed)}, capture_output=True, text=True, check=True).stdout.strip()
        for seed in seeds
    }


if __name__ == "__main__" and sys.argv[1:] == ["members"]:
    print(members_probe())
elif __name__ == "__main__" and sys.argv[1:] == ["random-histories"]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        print(json.dumps(random_histories_probe()))
elif __name__ == "__main__":
    scenarios = json.loads(sys.stdin.read())
    result = {}
    for stem, sc in scenarios.items():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result[stem] = run_scenario(sc, Dataset())
    print(json.dumps(result))
