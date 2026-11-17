# SPDX-License-Identifier: MPL-2.0
"""Emits the studio's broker topology from one declaration (investigation MSA-I12).

``declaration.json`` states the topology in logical terms. This module turns it into the three places the studio keeps a
hand copy of it, without touching any of them:

* ``emitted/amqp-topology.json``, in the structure of ``contracts/config-studio/amqp-topology.json``
* ``emitted/config-studio-topology.json``, the same text, as the worker's packaged copy
* ``emitted/Topology.java.txt``, a Java class with the constants and the ``declare`` method of ``Topology.java``

It also exposes ``operations``, the RabbitMQ calls the declaration implies, which ``compare.py`` sets against the calls
each hand copy makes. Following D1, nothing here connects to a broker. The output is text a provisioner or a build step could
apply.

Standard library only. Run it from the repository root: ``mise exec '--' python spikes/multi-store-emitted-topology/emit.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECLARATION = HERE / "declaration.json"
OUT = HERE / "emitted"

ROUTING_KEY_FOR = {"everything": "#"}


def load(path: Path = DECLARATION) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def render_json(value: object) -> str:
    """The text of the hand copies: two-space indent, one key per line, a final newline."""
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


# ---- the contract JSON ---------------------------------------------------------------------------------


def partition_arguments(decl: dict) -> dict:
    retention = decl["ordered_writes"]["retention"]
    return {"x-queue-type": "stream", "x-max-age": retention["max_age"], "x-max-length-bytes": retention["max_bytes"]}


def routing_key_prose(decl: dict) -> str:
    by = decl["ordered_writes"]["partition_by"]
    if by["function"] != "hex-prefix-modulo":
        raise ValueError(f"no emitter for the partition function {by['function']!r}")
    subject = by["of"].replace("-", " ")
    return f"the first {by['hex_digits']} hex digits of the {subject}, as an unsigned number, modulo partitions"


def contract(decl: dict) -> dict:
    """The structure of amqp-topology.json. It has one flag, deadLetter, where the declaration has two facts (what a lane does
    on failure, and which exchange its queue is bound to), so the emitter writes the flag and the second fact is lost here."""
    writes = decl["ordered_writes"]
    sink = decl["failure_sink"]
    queues = [{"name": lane["name"], "routingKey": lane["key"], "deadLetter": lane["on_failure"] == "dead-letter"}
              for lane in decl["lanes"]]
    queues.append({"name": sink["name"], "routingKey": ROUTING_KEY_FOR[sink["collects"]], "deadLetter": False})
    return {
        "exchange": decl["hub"]["name"],
        "deadLetterExchange": decl["hub"]["failures"],
        "queues": queues,
        "writes": {
            "superStream": writes["name"],
            "exchangeType": "direct",
            "exchangeArguments": {"x-super-stream": True},
            "partitions": writes["partitions"],
            "partitionStream": writes["name"] + "-{i}",
            "bindingKey": "{i}",
            "bindingArguments": {"x-stream-partition-order": "{i}"},
            "partitionArguments": partition_arguments(decl),
            "routingKey": routing_key_prose(decl),
            "consumerGroup": writes["readers"]["group"],
        },
    }


# ---- the broker operations the declaration implies ------------------------------------------------------


def _args(args: dict | None) -> str:
    return json.dumps(args or {}, sort_keys=True)


def exchange_op(name: str, kind: str, args: dict | None = None) -> tuple:
    return ("exchange", name, kind, True, False, _args(args))


def queue_op(name: str, args: dict | None = None) -> tuple:
    return ("queue", name, True, False, False, _args(args))


def bind_op(queue: str, exchange: str, key: str, args: dict | None = None) -> tuple:
    return ("bind", queue, exchange, key, _args(args))


def operations(decl: dict) -> dict[str, set[tuple]]:
    """The RabbitMQ calls, in two sets. ``core`` is what Topology.declare and declare_topology/declare_writes are for. ``events``
    is the broadcast exchange that the service and the writer declare for themselves."""
    hub, failures = decl["hub"]["name"], decl["hub"]["failures"]
    writes = decl["ordered_writes"]
    core: set[tuple] = {exchange_op(hub, "topic"), exchange_op(failures, "topic")}
    for lane in decl["lanes"]:
        dead = {"x-dead-letter-exchange": failures} if lane["on_failure"] == "dead-letter" else {}
        core.add(queue_op(lane["name"], dead))
        core.add(bind_op(lane["name"], hub, lane["key"]))
    sink = decl["failure_sink"]
    core.add(queue_op(sink["name"]))
    core.add(bind_op(sink["name"], failures, ROUTING_KEY_FOR[sink["collects"]]))
    core.add(exchange_op(writes["name"], "direct", {"x-super-stream": True}))
    for i in range(writes["partitions"]):
        stream = f"{writes['name']}-{i}"
        core.add(queue_op(stream, partition_arguments(decl)))
        core.add(bind_op(stream, writes["name"], str(i), {"x-stream-partition-order": i}))
    events = {exchange_op(b["name"], "topic") for b in decl.get("broadcasts", [])}
    return {"core": core, "events": events}


def partition_of(decl: dict, workspace: str) -> int:
    """The partition of a workspace's writes by the declared function, the reference the two hand implementations are tried against."""
    by = decl["ordered_writes"]["partition_by"]
    return int(workspace[: by["hex_digits"]], 16) % decl["ordered_writes"]["partitions"]


# ---- the Java class -------------------------------------------------------------------------------------


def _symbol(identifier: str) -> str:
    return identifier.upper().replace("-", "_")


def _literal(value: object) -> str:
    """A Java literal. An integer argument to a stream is a long, as the hand copy writes it."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value:,}".replace(",", "_") + "L"
    return json.dumps(value)


def java(decl: dict) -> str:
    hub, failures = decl["hub"], decl["hub"]["failures"]
    writes = decl["ordered_writes"]
    sink = decl["failure_sink"]
    consts = [
        f'    public static final String EXCHANGE = {json.dumps(hub["name"])};',
        f'    public static final String DEAD_LETTER_EXCHANGE = {json.dumps(failures)};',
    ]
    for lane in decl["lanes"]:
        sym = _symbol(lane["id"])
        consts.append(f'    public static final String {sym}_QUEUE = {json.dumps(lane["name"])};')
        consts.append(f'    public static final String {sym}_ROUTING_KEY = {json.dumps(lane["key"])};')
    sym = _symbol(sink["id"])
    consts.append(f'    public static final String {sym}_QUEUE = {json.dumps(sink["name"])};')
    consts.append(f'    public static final String {sym}_ROUTING_KEY = {json.dumps(ROUTING_KEY_FOR[sink["collects"]])};')
    wsym = _symbol(writes["id"])
    consts.append(f'    public static final String {wsym} = {json.dumps(writes["name"])};')
    consts.append(f'    public static final int PARTITIONS = {writes["partitions"]};')
    pairs = ", ".join(f"{json.dumps(k)}, {_literal(v)}" for k, v in partition_arguments(decl).items())
    consts.append(f"    public static final Map<String, Object> PARTITION_ARGUMENTS = Map.of({pairs});")
    for b in decl.get("broadcasts", []):
        consts.append(f'    public static final String {_symbol(b["id"])}_EXCHANGE = {json.dumps(b["name"])};')

    body = ['        channel.exchangeDeclare(EXCHANGE, "topic", true);',
            '        channel.exchangeDeclare(DEAD_LETTER_EXCHANGE, "topic", true);']
    for lane in decl["lanes"]:
        sym = _symbol(lane["id"])
        arg = "Map.of(\"x-dead-letter-exchange\", DEAD_LETTER_EXCHANGE)" if lane["on_failure"] == "dead-letter" else "Map.of()"
        body.append(f"        channel.queueDeclare({sym}_QUEUE, true, false, false, {arg});")
        body.append(f"        channel.queueBind({sym}_QUEUE, EXCHANGE, {sym}_ROUTING_KEY);")
    sym = _symbol(sink["id"])
    body.append(f"        channel.queueDeclare({sym}_QUEUE, true, false, false, Map.of());")
    body.append(f"        channel.queueBind({sym}_QUEUE, DEAD_LETTER_EXCHANGE, {sym}_ROUTING_KEY);")
    body.append(f'        channel.exchangeDeclare({wsym}, "direct", true, false, Map.of("x-super-stream", true));')
    body.append("        for (int i = 0; i < PARTITIONS; i++) {")
    body.append("            channel.queueDeclare(partition(i), true, false, false, PARTITION_ARGUMENTS);")
    body.append(f'            channel.queueBind(partition(i), {wsym}, Integer.toString(i), Map.of("x-stream-partition-order", i));')
    body.append("        }")
    for b in decl.get("broadcasts", []):
        body.append(f'        channel.exchangeDeclare({_symbol(b["id"])}_EXCHANGE, "topic", true);')

    by = writes["partition_by"]
    if by["function"] != "hex-prefix-modulo":
        raise ValueError(f"no emitter for the partition function {by['function']!r}")
    lines = [
        "// SPDX-License-Identifier: MPL-2.0",
        "// Emitted by spikes/multi-store-emitted-topology/emit.py from declaration.json. A spike's output, not a replacement for Topology.java.",
        "package org.nebularis.lattice.studio.jobs;",
        "",
        "import com.rabbitmq.client.Channel;",
        "import java.io.IOException;",
        "import java.util.Map;",
        "",
        "public final class Topology {",
        *consts,
        "",
        "    private Topology() {",
        "    }",
        "",
        "    public static void declare(Channel channel) throws IOException {",
        *body,
        "    }",
        "",
        "    public static String partition(int i) {",
        f'        return {wsym} + "-" + i;',
        "    }",
        "",
        "    public static String routingKey(String workspace) {",
        f"        return Long.toString(Long.parseLong(workspace.substring(0, {by['hex_digits']}), 16) % PARTITIONS);",
        "    }",
        "}",
        "",
    ]
    return "\n".join(lines)


# ---- running it -----------------------------------------------------------------------------------------


def emit(decl: dict) -> dict[str, str]:
    """The text of each emitted file, by file name."""
    text = render_json(contract(decl))
    return {"amqp-topology.json": text, "config-studio-topology.json": text, "Topology.java.txt": java(decl)}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--declaration", type=Path, default=DECLARATION)
    parser.add_argument("--out", type=Path, default=OUT, help="where to write the emitted files, inside the spike")
    args = parser.parse_args(argv)
    decl = load(args.declaration)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"declaration: {args.declaration} ({decl['declaration']} v{decl['version']})")
    for name, text in emit(decl).items():
        path = args.out / name
        data = text.encode("utf-8")
        path.write_bytes(data)
        print(f"emitted {path.relative_to(HERE.parent.parent) if path.is_relative_to(HERE.parent.parent) else path}"
              f"  {len(data)} bytes  sha256 {hashlib.sha256(data).hexdigest()[:16]}")
    ops = operations(decl)
    kinds: dict[str, int] = {}
    for op in ops["core"]:
        kinds[op[0]] = kinds.get(op[0], 0) + 1
    print("operations implied by the declaration (core): " + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())))
    print(f"operations implied by the declaration (events, declared by the service and the writer): {len(ops['events'])} exchange")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
