# SPDX-License-Identifier: MPL-2.0
"""Compares the studio's three hand copies of its broker topology with what ``declaration.json`` implies (investigation MSA-I12).

It prints every difference it finds. It reads the hand copies and changes none of them.

1. The two JSON files are compared with each other and with the JSON the declaration emits, field by field.
2. The RabbitMQ calls each copy makes are set against the calls the declaration implies. A JSON file makes no call, so the
   real ``declare_topology`` and ``declare_writes`` of the Python worker are run against a recording channel with each file's
   text. ``Topology.declare`` is read from its source, with a small evaluator for the literals and the one loop it uses.
3. The other places in the Java sources that declare an exchange or a queue are listed, since none is in a copy.
4. The partition function is tried in Python and read from the Java source.
5. The consumer and sender settings the declaration records are looked for where the code sets them.

Standard library only. Run from the repository root: ``mise exec '--' python spikes/multi-store-emitted-topology/compare.py``.
Add ``--matrix`` to print every call and the copies that make it. Exit status 1 means at least one difference was found.
"""

from __future__ import annotations

import argparse
import importlib
import json
import random
import re
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import emit  # noqa: E402

CONTRACT = ROOT / "contracts/config-studio/amqp-topology.json"
PACKAGED = ROOT / "workers/src/lattice_workers/config-studio-topology.json"
TOPOLOGY_JAVA = ROOT / "platform/config-studio-core/src/main/java/org/nebularis/lattice/studio/jobs/Topology.java"
PLATFORM = ROOT / "platform"
WORKER_MAIN = ROOT / "workers/src/lattice_workers/config_studio_main.py"
J = "platform/config-studio-{}/src/main/java/org/nebularis/lattice/studio/{}"
STREAM_WRITER = ROOT / J.format("writer", "writer/StreamWriter.java")
JOB_BUS = ROOT / J.format("service", "jobs/RabbitJobBus.java")
TRANSFORMS_MAIN = ROOT / "platform/config-studio-transforms/src/main/java/org/nebularis/lattice/studio/transforms/TransformsMain.java"
RABBIT_WRITES = ROOT / J.format("core", "writes/RabbitWrites.java")

differences: list[tuple[str, str, str]] = []


def note(section: str, text: str, key: str | None = None, where: str = "") -> None:
    """Records and prints a difference. The summary groups the ones with the same key."""
    differences.append((section, key or text, where))
    print(f"  DIFFERENT  {text}")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


# ---- the JSON files --------------------------------------------------------------------------------------


def flatten(value: object, prefix: str = "") -> dict[str, object]:
    if isinstance(value, dict):
        out: dict[str, object] = {}
        for key, item in value.items():
            out.update(flatten(item, f"{prefix}.{key}" if prefix else key))
        return out
    if isinstance(value, list):
        out = {}
        for index, item in enumerate(value):
            out.update(flatten(item, f"{prefix}[{index}]"))
        return out
    return {prefix: value}


def compare_json(decl: dict) -> tuple[dict, dict, dict]:
    print("== 1. The two JSON copies and the JSON the declaration emits")
    texts = {"contract": CONTRACT.read_text(encoding="utf-8"), "packaged": PACKAGED.read_text(encoding="utf-8"),
             "emitted": emit.render_json(emit.contract(decl))}
    for name, text in texts.items():
        print(f"  {name:9} {len(text.encode('utf-8')):5} bytes")
    parsed = {name: json.loads(text) for name, text in texts.items()}
    flat = {name: flatten(value) for name, value in parsed.items()}
    paths = sorted(set().union(*flat.values()))
    differing = [p for p in paths if len({json.dumps(flat[n].get(p, "<absent>")) for n in flat}) > 1]
    print(f"  {len(paths)} fields, {len(paths) - len(differing)} the same in all three")
    for path in differing:
        note("json", f"{path}: " + ", ".join(f"{n}={flat[n].get(path, '<absent>')!r}" for n in flat))
    for left, right in (("contract", "packaged"), ("contract", "emitted")):
        same = texts[left] == texts[right]
        print(f"  byte for byte, {left} and {right}: {'identical' if same else 'not identical'}")
        if not same and not differing:
            note("json", f"{left} and {right} have the same fields and different text")
    return parsed["contract"], parsed["packaged"], parsed["emitted"]


# ---- what the Python worker does -------------------------------------------------------------------------


class Recorder:
    """A channel that records the calls, with pika's signatures and defaults, so a call that the code leaves to a default is seen."""

    def __init__(self) -> None:
        self.ops: set[tuple] = set()

    def exchange_declare(self, exchange, exchange_type="direct", passive=False, durable=False, auto_delete=False, internal=False,
                         arguments=None):
        self.ops.add(("exchange", exchange, exchange_type, durable, auto_delete, emit._args(arguments)))

    def queue_declare(self, queue, passive=False, durable=False, exclusive=False, auto_delete=False, arguments=None):
        self.ops.add(("queue", queue, durable, exclusive, auto_delete, emit._args(arguments)))

    def queue_bind(self, queue, exchange, routing_key=None, arguments=None):
        self.ops.add(("bind", queue, exchange, routing_key, emit._args(arguments)))


def load_worker():
    sys.path.insert(0, str(ROOT / "workers/src"))
    return importlib.import_module("lattice_workers.config_studio_worker")


def python_operations(worker, topology: dict) -> set[tuple]:
    recorder = Recorder()
    worker.declare_topology(recorder, topology)
    saved = worker.WRITES
    worker.WRITES = topology["writes"]
    try:
        worker.declare_writes(recorder)
    finally:
        worker.WRITES = saved
    return recorder.ops


# ---- what Topology.java does -----------------------------------------------------------------------------


def mask(source: str) -> str:
    """The source without comments, with the strings kept."""
    return re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', lambda m: m.group(0) if m.group(0)[0] == '"' else " ", source, flags=re.S)


def balanced(text: str, start: int, opening: str, closing: str) -> int:
    """The index of the bracket that closes the one at ``start``, skipping strings."""
    depth, i, quoted = 0, start, False
    while i < len(text):
        c = text[i]
        if quoted:
            if c == "\\":
                i += 1
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c == opening:
            depth += 1
        elif c == closing:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced " + opening)


def split_top(text: str, separator: str) -> list[str]:
    """Splits at a separator that is outside strings and brackets."""
    parts, depth, quoted, last, i = [], 0, False, 0, 0
    while i < len(text):
        c = text[i]
        if quoted:
            if c == "\\":
                i += 1
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == separator and depth == 0:
            parts.append(text[last:i])
            last = i + 1
        i += 1
    parts.append(text[last:])
    return [p.strip() for p in parts]


def evaluate(expression: str, scope: dict) -> object:
    expression = expression.strip()
    parts = split_top(expression, "+")
    if len(parts) > 1:
        return "".join(str(evaluate(p, scope)) for p in parts)
    if expression.startswith('"'):
        return json.loads(expression)
    if expression in ("true", "false"):
        return expression == "true"
    number = re.fullmatch(r"([\d_]+)L?", expression)
    if number:
        return int(number.group(1).replace("_", ""))
    mapping = re.fullmatch(r"Map\.of\((.*)\)", expression, re.S)
    if mapping:
        items = [evaluate(a, scope) for a in split_top(mapping.group(1), ",")] if mapping.group(1).strip() else []
        return dict(zip(items[0::2], items[1::2]))
    text = re.fullmatch(r"Integer\.toString\((.*)\)", expression, re.S)
    if text:
        return str(evaluate(text.group(1), scope))
    call = re.fullmatch(r"partition\((.*)\)", expression, re.S)
    if call and "__partition__" in scope:
        parameter, body = scope["__partition__"]
        return evaluate(body, {**scope, parameter: evaluate(call.group(1), scope)})
    if re.fullmatch(r"\w+", expression) and expression in scope:
        return scope[expression]
    raise ValueError(f"cannot evaluate {expression!r}")


def java_constants(masked: str) -> dict:
    scope: dict = {}
    for m in re.finditer(r"public static final (?:String|int|Map<String, Object>) (\w+) =\s*(.*?);", masked, re.S):
        scope[m.group(1)] = evaluate(m.group(2), scope)
    partition = re.search(r"static String partition\(int (\w+)\)\s*\{\s*return (.*?);\s*\}", masked, re.S)
    if partition:
        scope["__partition__"] = (partition.group(1), partition.group(2))
    return scope


def java_operations(source: str) -> tuple[set[tuple], list[str], dict]:
    """The calls of ``declare``, with its constants, and the calls it makes that this reader does not model."""
    masked = mask(source)
    scope = java_constants(masked)
    head = re.search(r"static void declare\(Channel channel\) throws IOException\s*\{", masked)
    if head is None:
        raise ValueError("no declare(Channel) method")
    open_at = head.end() - 1
    body = masked[open_at + 1 : balanced(masked, open_at, "{", "}")]
    segments: list[tuple[str, dict]] = []
    cursor = 0
    for loop in re.finditer(r"for \(int (\w+) = (\d+); \1 < (\w+); \1\+\+\)\s*\{", body):
        if loop.start() < cursor:
            continue
        end = balanced(body, loop.end() - 1, "{", "}")
        segments.append((body[cursor : loop.start()], {}))
        variable, low, high = loop.group(1), int(loop.group(2)), scope[loop.group(3)]
        for value in range(low, high):
            segments.append((body[loop.end() : end], {variable: value}))
        cursor = end + 1
    segments.append((body[cursor:], {}))
    ops: set[tuple] = set()
    unmodelled: list[str] = []
    for text, extra in segments:
        local = {**scope, **extra}
        for m in re.finditer(r"\bchannel\.(\w+)\(", text):
            end = balanced(text, m.end() - 1, "(", ")")
            args = [evaluate(a, local) for a in split_top(text[m.end() : end], ",")]
            method = m.group(1)
            if method == "exchangeDeclare" and len(args) == 3:
                ops.add(("exchange", args[0], args[1], args[2], False, emit._args({})))
            elif method == "exchangeDeclare" and len(args) == 5:
                ops.add(("exchange", args[0], args[1], args[2], args[3], emit._args(args[4])))
            elif method == "queueDeclare" and len(args) == 5:
                ops.add(("queue", args[0], args[1], args[2], args[3], emit._args(args[4])))
            elif method == "queueBind" and len(args) in (3, 4):
                ops.add(("bind", args[0], args[1], args[2], emit._args(args[3] if len(args) == 4 else {})))
            else:
                unmodelled.append(f"{method} with {len(args)} arguments")
    return ops, unmodelled, scope


# ---- sets of calls ---------------------------------------------------------------------------------------


def show(op: tuple) -> str:
    if op[0] == "exchange":
        return f"exchange {op[1]} {op[2]} durable={op[3]} autoDelete={op[4]} args={op[5]}"
    if op[0] == "queue":
        return f"queue {op[1]} durable={op[2]} exclusive={op[3]} autoDelete={op[4]} args={op[5]}"
    return f"bind {op[1]} to {op[2]} with key {op[3]!r} args={op[4]}"


def compare_sets(section: str, left_name: str, left: set[tuple], right_name: str, right: set[tuple]) -> None:
    only_left, only_right = sorted(left - right, key=str), sorted(right - left, key=str)
    print(f"  {left_name} against {right_name}: {len(left & right)} calls the same, {len(only_left)} only in {left_name}, {len(only_right)} only in {right_name}")
    for op in only_left:
        note(section, f"only in {left_name}: {show(op)}", key=show(op), where=f"only in {left_name}")
    for op in only_right:
        note(section, f"only in {right_name}: {show(op)}", key=show(op), where=f"only in {right_name}")


def compare_operations(decl: dict, contract: dict, packaged: dict, emitted: dict, matrix: bool) -> None:
    print("\n== 2. The calls each copy makes, against the calls the declaration implies")
    implied = emit.operations(decl)
    views: dict[str, set[tuple]] = {"declaration": implied["core"]}
    try:
        worker = load_worker()
        views["python@contract"] = python_operations(worker, contract)
        views["python@packaged"] = python_operations(worker, packaged)
        views["python@emitted"] = python_operations(worker, emitted)
    except Exception as error:  # the worker module needs its own imports
        print(f"  the Python worker could not be loaded ({error.__class__.__name__}: {error}), so its calls are not compared")
    source = TOPOLOGY_JAVA.read_text(encoding="utf-8")
    java_ops, unmodelled, constants = java_operations(source)
    views["java@Topology.java"] = java_ops
    emitted_ops, emitted_unmodelled, _ = java_operations(emit.java(decl))
    views["java@emitted"] = emitted_ops
    for name, extra in (("Topology.java", unmodelled), ("emitted Java", emitted_unmodelled)):
        for call in extra:
            note("java", f"{name} makes a call this reader does not model: {call}")
    print("  " + ", ".join(f"{n} {len(ops)} calls" for n, ops in views.items()))
    print("  the hand copies, against the declaration's core calls")
    for name in ("python@contract", "python@packaged", "java@Topology.java"):
        if name in views:
            compare_sets("calls", name, views[name], "declaration", views["declaration"])
    if "python@contract" in views:
        print("  the two hand implementations, against each other")
        compare_sets("calls", "python@contract", views["python@contract"], "java@Topology.java", views["java@Topology.java"])
    print("  what the emitter produces, against the declaration (the emitted Java also declares the events exchange)")
    if "python@emitted" in views:
        compare_sets("emitted", "python@emitted", views["python@emitted"], "declaration", views["declaration"])
    compare_sets("emitted", "java@emitted", views["java@emitted"], "declaration+events", views["declaration"] | implied["events"])
    for op in sorted(implied["events"]):
        note("calls", f"in the declaration and in no hand copy of the topology, so not in Topology.java or either JSON file: {show(op)}", key=show(op), where="only in declaration (events), no hand copy")
    if matrix:
        print("\n  every call, and which views make it (d declaration, c python@contract, p python@packaged, j java@Topology.java)")
        every = sorted(set().union(*views.values()), key=str)
        for op in every:
            marks = "".join(letter if op in views.get(name, set()) else "-"
                            for letter, name in (("d", "declaration"), ("c", "python@contract"), ("p", "python@packaged"), ("j", "java@Topology.java")))
            print(f"    {marks}  {show(op)}")


# ---- declare sites outside the copies --------------------------------------------------------------------


def other_declare_sites() -> dict[str, str]:
    print("\n== 3. Other places in the Java sources that declare an exchange or a queue")
    sources = [p for p in sorted(PLATFORM.rglob("*.java")) if "/src/main/" in p.as_posix()]
    constants: dict[tuple[str, str], str] = {}
    for path in sources:
        for m in re.finditer(r'static final String (\w+) = ("[^"]*");', path.read_text(encoding="utf-8")):
            constants[(path.stem, m.group(1))] = json.loads(m.group(2))
    found: dict[str, str] = {}
    for path in sources:
        if path == TOPOLOGY_JAVA:
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"\.(exchangeDeclare|queueDeclare|queueBind|queueDeclarePassive)\(([^;]*)\);", text):
            args = " ".join(m.group(2).split())
            resolved = args
            for (owner, name), value in constants.items():
                resolved = re.sub(rf"(?<![\w])(?:\w+\.)*{owner}\.{name}(?!\w)", json.dumps(value), resolved)
                if owner == path.stem:
                    resolved = re.sub(rf"(?<![\w.\"]){name}(?!\w)", json.dumps(value), resolved)
            line = text.count("\n", 0, m.start()) + 1
            print(f"  {rel(path)}:{line}  {m.group(1)}({resolved})")
            found[f"{path.stem}:{line}"] = resolved
    callers = sum(len(re.findall(r"\bdeclareTopology\(", p.read_text(encoding="utf-8"))) for p in sources) - 1
    print("  None of these is in a hand copy of the topology. The declaration lists the events exchange and says nothing of the rest.")
    print(f"  RabbitMqEventPublisher.declareTopology has {callers} callers under platform/src/main, so its queue and dead-letter exchange are not declared by the studio.")
    return found


# ---- the partition function ------------------------------------------------------------------------------


def compare_routing(decl: dict, scope: dict) -> None:
    print("\n== 4. The partition function")
    by = decl["ordered_writes"]["partition_by"]
    partitions = decl["ordered_writes"]["partitions"]
    rng = random.Random(0)
    samples = [str(uuid.UUID(int=rng.getrandbits(128))) for _ in range(2000)] + ["00000000-0000-0000-0000-000000000000", "ffffffff-ffff-ffff-ffff-ffffffffffff"]
    try:
        worker = load_worker()
        wrong = [s for s in samples if worker.routing_key(s) != str(emit.partition_of(decl, s))]
        print(f"  Python routing_key against the declared function on {len(samples)} ids: {len(wrong)} different")
        if wrong:
            note("routing", f"Python routing_key differs from the declared function on {len(wrong)} ids, first {wrong[0]}")
    except Exception as error:
        print(f"  the Python worker could not be loaded ({error.__class__.__name__}), so routing_key was not tried")
    source = mask(TOPOLOGY_JAVA.read_text(encoding="utf-8"))
    m = re.search(r"static String routingKey\(String workspace\)\s*\{\s*return Long\.toString\(Long\.parseLong\(workspace\.substring\(0, (\d+)\), (\d+)\) % (\w+)\);\s*\}", source, re.S)
    if m is None:
        note("routing", "Topology.routingKey is not in the form this reader knows")
    else:
        digits, radix, modulus = int(m.group(1)), int(m.group(2)), scope.get(m.group(3))
        ok = (digits, radix, modulus) == (by["hex_digits"], 16, partitions)
        print(f"  Topology.routingKey reads {digits} digits in base {radix} modulo {m.group(3)} = {modulus}, the declaration says {by['hex_digits']} digits in base 16 modulo {partitions}: {'the same' if ok else 'different'}")
        if not ok:
            note("routing", "Topology.routingKey does not match the declared function")
        samples_java = [str(int(s[:digits], radix) % modulus) for s in samples]
        print(f"  that formula, evaluated in Python, against the declared function: {sum(a != str(emit.partition_of(decl, s)) for a, s in zip(samples_java, samples))} different")
    print("  The JSON files hold the function as a sentence: " + json.dumps(emit.routing_key_prose(decl)))


# ---- consumer and sender settings ------------------------------------------------------------------------


def look(section: str, what: str, path: Path, pattern: str, expected: str | None = None) -> None:
    text = mask(path.read_text(encoding="utf-8")) if path.suffix == ".java" else path.read_text(encoding="utf-8")
    m = re.search(pattern, text)
    if m is None:
        note(section, f"{what}: not found in {rel(path)}")
        return
    found = m.group(1) if m.groups() else m.group(0)
    if expected is not None and found != expected:
        note(section, f"{what}: the declaration says {expected!r}, {rel(path)} says {found!r}")
    else:
        print(f"  {what}: {found!r} in {rel(path)}, as declared")


def compare_settings(decl: dict, contract: dict) -> None:
    print("\n== 5. Consumer and sender settings the declaration records, and where the code sets them")
    readers = decl["ordered_writes"]["readers"]
    look("settings", "reader group", STREAM_WRITER, r'static final String GROUP = "([^"]*)"', readers["group"])
    look("settings", "batch limit", STREAM_WRITER, r"static final int MAX_BATCH = (\d+)", str(readers["batch_limit"]))
    look("settings", "single active consumer", STREAM_WRITER, r"\.(singleActiveConsumer)\(\)", "singleActiveConsumer")
    look("settings", "start at the first offset", STREAM_WRITER, r"OffsetSpecification\.(first)\(\)", readers["start"])
    look("settings", "manual offset tracking", STREAM_WRITER, r"\.(manual)TrackingStrategy\(\)", readers["tracking"])
    look("settings", "reads the declared super stream", STREAM_WRITER, r"\.superStream\((Topology\.WRITES)\)", "Topology.WRITES")
    for lane in decl["lanes"]:
        if "prefetch" in lane and lane["id"] == "transforms":
            look("settings", f"prefetch of {lane['id']}", TRANSFORMS_MAIN, r"basicQos\((\d+)\)", str(lane["prefetch"]))
        if "prefetch" in lane and lane["id"] == "jobs":
            look("settings", f"prefetch of {lane['id']} and jobs-long (the Python worker)", WORKER_MAIN, r"basic_qos\(prefetch_count=(\d+)\)", str(lane["prefetch"]))
        if lane.get("expiry", {}).get("set_by") == "sender":
            look("settings", f"expiry of {lane['id']} set by the sender", JOB_BUS, r"\.(expiration)\(")
    look("settings", "the writes reply to their sender on direct reply-to", RABBIT_WRITES, r'REPLY_TO = "(amq\.rabbitmq\.reply-to)"', "amq.rabbitmq.reply-to")
    group_in_topology = re.search(r"GROUP|writers", mask(TOPOLOGY_JAVA.read_text(encoding="utf-8")))
    if group_in_topology is None:
        note("settings", f"Topology.java holds no reader group, so the string {readers['group']!r} is held by StreamWriter.GROUP and by the JSON files, and nothing checks the two against each other")
    if contract["writes"]["consumerGroup"] != readers["group"]:
        note("settings", "the contract's consumerGroup differs from the declaration")
    print("  Not in the declaration, and not checked: the value of a request's expiry (the caller chooses it per request), the stream client's")
    print("  credit strategy, and the publisher's mandatory flag, confirms and persistence.")


# ---- running it -----------------------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--declaration", type=Path, default=emit.DECLARATION)
    parser.add_argument("--matrix", action="store_true", help="print every call and the views that make it")
    args = parser.parse_args(argv)
    decl = emit.load(args.declaration)
    contract, packaged, emitted = compare_json(decl)
    compare_operations(decl, contract, packaged, emitted, args.matrix)
    other_declare_sites()
    _, _, scope = java_operations(TOPOLOGY_JAVA.read_text(encoding="utf-8"))
    compare_routing(decl, scope)
    compare_settings(decl, contract)
    grouped: dict[tuple[str, str], list[str]] = {}
    for section, key, where in differences:
        grouped.setdefault((section, key), [])
        if where and where not in grouped[(section, key)]:
            grouped[(section, key)].append(where)
    print(f"\n{len(differences)} differences found, {len(grouped)} distinct")
    for (section, key), wheres in grouped.items():
        print(f"  - {section}: {key}" + (f"  [{'; '.join(wheres)}]" if wheres else ""))
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
