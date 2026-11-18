# SPDX-License-Identifier: MPL-2.0
"""Derives the studio's software quanta twice and compares them (investigation MSA-I12, second part).

1. From compose, as vyvid does: ``deployment/compose/config-studio/docker-compose.yml`` goes to ``software_quanta``.
2. From the declaration: ``declaration.json`` is turned into the compose-shaped input ``software_quanta`` reads, one service
   per store, broker and unit, with the hosts a unit points at in its environment, and the same function derives the quanta.

The function is vyvid's own (``vyvid.extractors.quanta``), imported, not copied. It needs PyYAML and pyoxigraph, which the
repository's ``mise`` environment lacks, so run this with an interpreter that has them, the one of the sibling ``vyvid``
checkout, from the repository root:

    ..\\vyvid\\.venv\\Scripts\\python.exe spikes/multi-store-emitted-topology/quanta.py

Set ``VYVID_SRC`` to the ``src`` folder of a vyvid checkout if it is not at ``../vyvid/src``. Nothing is written.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, os.environ.get("VYVID_SRC", str(ROOT.parent / "vyvid" / "src")))

try:
    import yaml
    from vyvid.extractors import quanta as vq
except ImportError as error:
    sys.exit(f"quanta.py needs PyYAML and pyoxigraph and a vyvid checkout (VYVID_SRC): {error}")

import emit  # noqa: E402

COMPOSE = ROOT / "deployment/compose/config-studio/docker-compose.yml"
DEPLOYMENT = "compose/config-studio"
BROKER_URI = "amqp://{broker}:5672"
STORE_URI = "http://{store}:3030"
CALL_URI = "http://{unit}:{port}"


def compose_services() -> tuple[dict, str]:
    text = COMPOSE.read_text(encoding="utf-8")
    pointer = f"{COMPOSE.relative_to(ROOT).as_posix()}:1-{text.count(chr(10))}"
    return yaml.safe_load(text), pointer


def declared_services(decl: dict, with_store: bool = True) -> dict:
    """The declaration in the shape of a compose file. Only what the quanta rules read is written: an image where the
    declaration names a product, and in each unit's environment the host of every store, the broker and the unit it uses."""
    units = {u["name"]: u for u in decl["units"]}
    services: dict[str, dict] = {decl["broker"]["name"]: {"image": decl["broker"]["product"]}}
    for store in decl["stores"]:
        services[store["name"]] = {"image": store["product"]}
    for unit in decl["units"]:
        service: dict = {}
        if "product" in unit:
            service["image"] = unit["product"]
        environment: dict[str, str] = {}
        if with_store:
            for store in unit.get("stores", []):
                environment[f"{store.upper()}_URL"] = STORE_URI.format(store=store)
        if unit.get("publishes") or unit.get("consumes"):
            environment["AMQP_URI"] = BROKER_URI.format(broker=decl["broker"]["name"])
        for call in unit.get("calls", []):
            environment[f"{call['unit'].upper().replace('-', '_')}_URL"] = CALL_URI.format(unit=call["unit"], port=units[call["unit"]].get("port", 80))
        if environment:
            service["environment"] = environment
        services[unit["name"]] = service
    if not with_store:
        for name in [s["name"] for s in decl["stores"]]:
            del services[name]
    return {"services": services}


def describe(title: str, compose: dict, found: list) -> None:
    services = compose["services"]
    print(title)
    print("  roles: " + ", ".join(f"{name}={vq.role(service or {})}" for name, service in services.items()))
    for quantum in found:
        print(f"  {quantum.identifier}")
        print(f"    parts: {', '.join(quantum.parts)}")
        print(f"    claim: {quantum.claim}")


def membership(found: list) -> dict[str, str]:
    return {part: quantum.identifier for quantum in found for part in quantum.parts}


def main() -> int:
    decl = emit.load()
    compose, pointer = compose_services()
    from_compose = vq.software_quanta(DEPLOYMENT, compose, pointer)
    describe(f"1. From compose ({pointer})", compose, from_compose)

    declared = declared_services(decl)
    from_declaration = vq.software_quanta("studio", declared, "spikes/multi-store-emitted-topology/declaration.json")
    print()
    describe("2. From the declaration, with each unit's store and broker", declared, from_declaration)

    brokered = declared_services(decl, with_store=False)
    from_broker_alone = vq.software_quanta("studio", brokered, "spikes/multi-store-emitted-topology/declaration.json")
    print()
    describe("3. From the declaration with the store taken away, which is what the broker alone would give", brokered, from_broker_alone)

    print("\n4. Each part, in the quantum each derivation puts it in")
    left, right, alone = membership(from_compose), membership(from_declaration), membership(from_broker_alone)
    rows = [(part, left.get(part, "(not in compose)"), right.get(part, "-"), alone.get(part, "-")) for part in sorted(set(left) | set(right) | set(alone))]
    width = max(len(r[0]) for r in rows)
    print(f"  {'part'.ljust(width)}  from compose | from the declaration | broker alone")
    for part, a, b, c in rows:
        print(f"  {part.ljust(width)}  {a} | {b} | {c}")

    only_declared = sorted(set(right) - set(left))
    same_split = {frozenset(q.parts) for q in from_compose} == {frozenset(q.parts) for q in from_declaration}
    print(f"\n  quanta from compose: {len(from_compose)}, from the declaration: {len(from_declaration)}, with the broker alone: {len(from_broker_alone)}")
    print(f"  parts the declaration names that compose does not: {', '.join(only_declared)}")
    print(f"  the same split of the parts: {'yes' if same_split else 'no'}")
    return 0 if same_split else 1


if __name__ == "__main__":
    sys.exit(main())
