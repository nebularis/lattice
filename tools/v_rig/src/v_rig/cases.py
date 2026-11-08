# SPDX-License-Identifier: MPL-2.0
"""A case is one programme of a rig with the documents it places and the events put to it, and its readings are the
distinct tokens its documents state for each key a scheme declares to carry a reading. Both projections of a case, the
generated theory and the vectors, are keyed by the case digest and the reading. A fact is read in one of three states,
and the keys of an event's facts reach an evaluation only through the input bindings a rig's extension declares."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from rdflib import RDF, Graph, Literal, URIRef

from . import canon
from .lift import VRIG


@dataclass(frozen=True)
class Reading:
    key: str
    token: str
    stated_by: tuple[str, ...]


@dataclass
class Case:
    programme: URIRef
    programme_id: str
    documents: list[URIRef] = field(default_factory=list)
    events: list[URIRef] = field(default_factory=list)
    readings: list[Reading] = field(default_factory=list)
    digest: str = ""

    @property
    def document_ids(self) -> list[str]:
        return [self._id for self._id in ()] or []


def rig_id(graph: Graph, node: URIRef) -> str:
    return str(graph.value(node, VRIG.rigId))


def _python(value):
    if isinstance(value, Literal):
        v = value.toPython()
        if isinstance(v, Decimal):
            return float(v) if v != v.to_integral_value() else int(v)
        if isinstance(v, (dt.date, dt.datetime)):
            return v.isoformat()
        if isinstance(v, Literal):
            return str(v)
        return v
    return str(value)


def fact_state(graph: Graph, carrier: URIRef, key: str) -> dict:
    """The fact of a key on a carrier as one of three JSON shapes, stated, unknown or absent."""
    facts = [f for f in graph.subjects(VRIG.of, carrier) if str(graph.value(f, VRIG.key)) == key]
    if not facts:
        return {"state": "absent"}
    fact = facts[0]
    return fact_value(graph, fact)


def fact_value(graph: Graph, fact: URIRef) -> dict:
    if graph.value(fact, VRIG.unknown) is not None and graph.value(fact, VRIG.unknown).toPython() is True:
        return {"state": "unknown"}
    if graph.value(fact, VRIG.empty) is not None and graph.value(fact, VRIG.empty).toPython() is True:
        return {"state": "stated", "value": None}
    if (fact, RDF.type, VRIG.Formula) in graph:
        return {"state": "stated", "formula": str(graph.value(fact, VRIG.expression)),
                "inputs": sorted(str(i) for i in graph.objects(fact, VRIG.input))}
    values = list(graph.objects(fact, VRIG.value))
    items = sorted(graph.objects(fact, VRIG["item"]), key=lambda r: int(graph.value(r, VRIG["index"]) or 0))
    if items:
        records = [{str(graph.value(f, VRIG.key)): fact_value(graph, f) for f in graph.subjects(VRIG.of, r)} for r in items]
        return {"state": "stated", "value": records}
    if len(values) == 1 and isinstance(values[0], URIRef):
        return {"state": "stated", "value": [_python(v) for v in graph.items(values[0])]}
    if len(values) == 1:
        return {"state": "stated", "value": _python(values[0])}
    return {"state": "stated", "value": sorted((_python(v) for v in values), key=str)}


def input_bindings(extensions: list[Path]) -> dict[str, str]:
    """Input name to key, from every vrig:InputBinding the extensions declare."""
    bound: dict[str, str] = {}
    for path in extensions:
        g = Graph().parse(path, format="turtle")
        for binding in g.subjects(RDF.type, VRIG.InputBinding):
            name, key = g.value(binding, VRIG.inputName), g.value(binding, VRIG.key)
            if name is not None and key is not None:
                bound[str(name)] = str(key)
    return bound


def cases(graph: Graph, rig_digest: str, reading_keys: tuple[str, ...], file_digests: dict[str, str]) -> list[Case]:
    found: list[Case] = []
    for programme in sorted(graph.subjects(RDF.type, VRIG.Programme), key=str):
        case = Case(programme, rig_id(graph, programme))
        placed: list[URIRef] = []
        for fact in graph.subjects(RDF.type, VRIG.Fact):
            if str(graph.value(fact, VRIG.key)) in ("document", "documents"):
                carrier = graph.value(fact, VRIG.of)
                if carrier is not None and graph.value(carrier, VRIG.inProgramme) == programme:
                    placed.extend(t for t in graph.objects(fact, VRIG.resolvesTo) if (t, RDF.type, VRIG.Document) in graph)
        for fact in graph.subjects(RDF.type, VRIG.Fact):
            if str(graph.value(fact, VRIG.key)) == "programme" and programme in set(graph.objects(fact, VRIG.resolvesTo)):
                carrier = graph.value(fact, VRIG.of)
                if (carrier, RDF.type, VRIG.Document) in graph:
                    placed.append(carrier)
                elif (carrier, RDF.type, VRIG.Event) in graph:
                    case.events.append(carrier)
        case.documents = sorted(set(placed), key=lambda d: rig_id(graph, d))
        case.events = sorted(set(case.events), key=lambda e: rig_id(graph, e))
        for key in reading_keys:
            tokens: dict[str, list[str]] = {}
            for document in case.documents:
                state = fact_state(graph, document, key)
                if state.get("state") == "stated" and isinstance(state.get("value"), str):
                    tokens.setdefault(state["value"], []).append(rig_id(graph, document))
            for token in sorted(tokens):
                case.readings.append(Reading(key, token, tuple(tokens[token])))
        lines = [f"rig={rig_digest}", f"programme={case.programme_id}"]
        lines += [f"document={rig_id(graph, d)}={graph.value(d, VRIG.digest)}" for d in case.documents]
        lines += [f"event={rig_id(graph, e)}={graph.value(e, VRIG.digest)}" for e in case.events]
        case.digest = canon.sha256_hex("\n".join(lines))
        found.append(case)
    return found


def layers_of(graph: Graph, case: Case) -> list[URIRef]:
    return sorted((l for l in graph.subjects(RDF.type, VRIG.Layer) if graph.value(l, VRIG.inProgramme) == case.programme),
                  key=lambda l: int(graph.value(l, VRIG.layerNumber)))


def placements_on(graph: Graph, layer: URIRef) -> list[URIRef]:
    return sorted((p for p in graph.subjects(VRIG.onLayer, layer)), key=lambda p: int(graph.value(p, VRIG["index"]) or 0))
