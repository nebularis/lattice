# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Architectural quanta, derived from coupling in each view of the architecture.

An architectural quantum is the smallest set that must change and be released together because of
its coupling, so its size is the lower bound on incremental change. It is derived, never declared,
and separately in each view, because the same module or component falls into different quanta in
different views (ADR-A134, addendum of 2026-10-25). The term is distinct from the claims ontology's
``clm:Quantum``, an amount claimed.

**Data view.** The substrate layers are one quantum, because they form one dependency order and one
release. Any other module is its own quantum, since its coupling to the substrate runs one way,
unless something in the substrate imports it, in which case the substrate's quantum grows to take it
in. A release member left outside the substrate's quantum shares its release number without being
coupled to it, which is the release policy straddling a quantum boundary.

**Software view.** Per deployment, from what each component's configuration points at. Two components
that use one store share state and are one quantum. A component that names another application
component is taken to call it synchronously, which binds them too. A broker is a contract between
components and never merges them, which is how middleware draws a quantum boundary, but only when
nothing else couples the two sides: a shared store defeats a broker.

The process view is modelled and not yet derived.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

STORES = ("postgres", "fuseki", "jena", "mysql", "mariadb", "mongo", "redis", "oxigraph", "graphdb", "virtuoso")
BROKERS = ("rabbitmq", "kafka", "nats", "activemq", "pulsar")

CLAIM_LIMIT = 200


@dataclass
class Quantum:
    identifier: str
    view: str
    parts: list[str]
    claim: str
    pointer: str
    deployment: str = ""


@dataclass
class _Union:
    parent: dict[str, str] = field(default_factory=dict)

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def join(self, a: str, b: str) -> None:
        self.parent[self.find(a)] = self.find(b)


def _fit(text: str) -> str:
    return text if len(text) <= CLAIM_LIMIT else text[: CLAIM_LIMIT - 1].rstrip(" ,") + "…"


def _listed(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def data_quanta(
    kinds: dict[str, str], imports: set[tuple[str, str]], release: set[str], pointers: dict[str, str]
) -> tuple[list[Quantum], list[str]]:
    """The data view's quanta, and the release members the release policy places across a boundary.

    ``kinds`` maps a catalogue module to its kind, ``imports`` holds ``(importer, imported)`` pairs
    between modules, ``release`` the modules released together, ``pointers`` a document per module.
    """
    substrate = {name for name, kind in kinds.items() if kind == "substrate"}
    grew = True
    while grew:
        grew = False
        for importer, imported in imports:
            if importer in substrate and imported not in substrate and imported in kinds:
                substrate.add(imported)
                grew = True

    found = [
        Quantum(
            identifier="data/substrate",
            view="data",
            parts=sorted(substrate),
            claim=_fit(
                f"The substrate's {len(substrate)} layers are one data quantum: one dependency order "
                f"released as one, so a change to any of them is a release of all."
            ),
            pointer="repository-catalogue.md",
        )
    ]
    for name in sorted(kinds):
        if name in substrate or kinds[name] not in ("standalone", "applied", "example"):
            continue
        shared = " It shares the substrate's release number all the same." if name in release else ""
        found.append(
            Quantum(
                identifier=f"data/{name}",
                view="data",
                parts=[name],
                claim=_fit(f"{name} is its own data quantum, depending on the substrate one way, so it changes alone.{shared}"),
                pointer=pointers.get(name, "repository-catalogue.md"),
            )
        )
    straddling = sorted(release - substrate)
    return found, straddling


def role(service: dict) -> str:
    """A component's part in coupling: a store shares state, a broker carries a contract."""
    image = str(service.get("image", "")).lower()
    if any(word in image for word in BROKERS):
        return "broker"
    if any(word in image for word in STORES):
        return "store"
    return "component"


def _environment(service: dict) -> list[str]:
    env = service.get("environment") or {}
    if isinstance(env, dict):
        return [str(v) for v in env.values() if v is not None]
    return [str(item).split("=", 1)[-1] for item in env]


def _depends(service: dict) -> list[str]:
    depends = service.get("depends_on") or []
    return list(depends) if isinstance(depends, (list, dict)) else []


def links(services: dict) -> dict[str, set[str]]:
    """What each component points at: its declared dependencies, and any other component whose name
    appears as a host in its configuration, which is how a store or a broker is usually reached."""
    found: dict[str, set[str]] = {}
    for name, service in services.items():
        targets = set(_depends(service))
        for value in _environment(service):
            for other in services:
                if other != name and re.search(rf"(?<![\w-]){re.escape(other)}(?![\w-])", value):
                    targets.add(other)
        found[name] = targets & set(services)
    return found


def software_quanta(deployment: str, compose: dict, pointer: str) -> list[Quantum]:
    """One deployment's quanta. A store or a synchronous call merges, a broker never does."""
    services = compose.get("services") or {}
    roles = {name: role(service or {}) for name, service in services.items()}
    linked = links(services)
    union = _Union()
    for name in services:
        if roles[name] != "broker":
            union.find(name)
    # ponytail: depends_on on another application component is read as a synchronous call, which
    # over-merges where it only orders start-up. Read the component's own configuration if it matters.
    for name, targets in linked.items():
        for target in targets:
            if "broker" in (roles[name], roles[target]):
                continue
            union.join(name, target)

    groups: dict[str, list[str]] = {}
    for name in services:
        if roles[name] != "broker":
            groups.setdefault(union.find(name), []).append(name)

    found = []
    for members in groups.values():
        members.sort()
        stores = [m for m in members if roles[m] == "store"]
        brokered = {m for m in members if any(roles[t] == "broker" for t in linked[m])}
        claim = f"In {deployment}, {_listed(members)} {'is its own quantum' if len(members) == 1 else 'form one quantum'}"
        if stores:
            claim += f", coupled through {_listed(stores)}"
        if len(brokered) > 1:
            claim += ", although a broker between them would otherwise separate them"
        components = [m for m in members if roles[m] == "component"] or members
        found.append(
            Quantum(
                identifier=f"software/{deployment}/{components[0]}",
                view="software",
                parts=members,
                claim=_fit(claim + "."),
                pointer=pointer,
                deployment=deployment,
            )
        )
    return sorted(found, key=lambda q: q.identifier)
