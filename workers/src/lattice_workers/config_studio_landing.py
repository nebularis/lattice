# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Where the data of each compiled persistence target lands, as the `landing-places.json` artefact of a persistence compile
job (contracts/config-studio/README.md, landing-places.schema.json).

The reading is the worker's and never the browser's. What the compiled profile states is read from it: the target, the profile
each dimension was won by, the edges of the boundary with their ownership and reference mode, and each operation with its
template and its parameter bindings. What it does not state is derived with the compiler's own code, imported and never
written again: the scopes a target matches (`persistence.scopes`), and the graph each operation writes and the rule that names
it, from the typed operation `persistence.instantiate.build_operation` builds, so a graph is named exactly as the operation
names it. Nothing here is a guess from an IRI pattern."""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from typing import Any, Optional

from persistence.contract import ResourceKind, resource_of
from persistence.instantiate import _local, build_operation
from persistence.ir import (
    A, Bind, Const, Func, GraphBlock, GraphRole, Operation, ParamRef, Triple, Var,
)
from persistence.namespaces import DAL
from persistence.scopes import Target, all_scopes, matches
from rdflib import RDF, Graph, URIRef

LANDING_PLACES = "landing-places.json"

# The kinds of place, in the order the browser draws them.
KINDS = (
    "data-graph", "version", "events", "version-row", "receipt", "transaction-claim", "patch-log-add", "patch-log-del",
    "key-claim", "merge-record", "key-quarantine", "retention-mark", "dataset-epoch", "derived-rows",
)

_LABELS = {
    "data-graph": "Data graph, the aggregate's triples",
    "version": "The new version's triples",
    "events": "Events of the stream",
    "version-row": "Version row, with the head and the sequence",
    "receipt": "Receipt of each write",
    "transaction-claim": "Transaction claim, for a retry",
    "patch-log-add": "Patch log, the triples added",
    "patch-log-del": "Patch log, the triples removed",
    "key-claim": "Key claim",
    "merge-record": "Key merge record",
    "key-quarantine": "Key quarantine",
    "retention-mark": "Retention mark",
    "dataset-epoch": "Dataset epoch",
    "derived-rows": "Promoted rows of a surface contract",
}

_ROLE_KINDS = {
    GraphRole.META: "version-row",
    GraphRole.TXN: "transaction-claim",
    GraphRole.LOG: "receipt",
    GraphRole.PINNED: "receipt",
    GraphRole.EVENT: "events",
    GraphRole.QUARANTINE: "key-quarantine",
    GraphRole.RETENTION: "retention-mark",
    GraphRole.DATASET: "dataset-epoch",
    GraphRole.DERIVED: "derived-rows",
}


def artefact_path(group: str, operation: str) -> str:
    """The path of an operation's SPARQL artefact in the job, as `config_studio_jobs` writes it."""
    return f"{group}/{operation.replace(':', '_').replace('/', '_')}.rq"


def target_group(profile: Graph, node) -> str:
    """The group of a compiled profile's artefacts, its class's local name and its deployment's where it has one, as `instantiate` names it."""
    name = _local(profile.value(node, DAL.forTarget))
    deployment = profile.value(node, DAL.forDeployment)
    return f"{name}.{_local(deployment)}" if deployment is not None else name


# --- the naming rule of a graph, from the operation's own expressions -----------------------------------------------------


def _walk(node: Any):
    """Every dataclass of an operation's tree, in order."""
    if is_dataclass(node) and not isinstance(node, type):
        yield node
        for f in fields(node):
            yield from _walk(getattr(node, f.name))
    elif isinstance(node, (tuple, list)):
        for item in node:
            yield from _walk(item)


def _const_text(term) -> str:
    text = str(term)
    if text.startswith("<") and text.endswith(">"):
        return text[1:-1]
    if text.startswith('"'):
        return text[1:text.rfind('"')]
    return text


def _is_placeholder(text: str) -> bool:
    return text.startswith("{") and text.endswith("}") and "{" not in text[1:-1]


def _rule(expr, binds: dict, params: dict, seen: frozenset = frozenset()) -> str:
    """The text of the naming rule an expression gives, a constant as it is and anything the caller or the write supplies as a
    `{placeholder}` in plain words."""
    if isinstance(expr, Const):
        return _const_text(expr.term)
    if isinstance(expr, ParamRef):
        param = params.get(expr.name)
        if param is not None and param.equals is not None and expr.name not in seen:
            return _rule(param.equals, binds, params, seen | {expr.name})
        return "{" + expr.name + "}"
    if isinstance(expr, Var):
        bound = binds.get(expr.name)
        if bound is not None and expr.name not in seen:
            return _rule(bound, binds, params, seen | {expr.name})
        return "{" + expr.name + "}"
    if isinstance(expr, Func):
        if expr.name in ("STR", "IRI") and len(expr.args) == 1:
            return _rule(expr.args[0], binds, params, seen)
        if expr.name == "CONCAT":
            return "".join(_rule(a, binds, params, seen) for a in expr.args)
        if expr.name == "ENCODE_FOR_URI" and len(expr.args) == 1:
            inner = _rule(expr.args[0], binds, params, seen)
            return "{" + (inner[1:-1] if _is_placeholder(inner) else inner) + ", percent-encoded}"
        if expr.name == "SUBSTR" and len(expr.args) == 3 and _is_now(expr.args[0]):
            return "{year and month of the write, as YYYY-MM}" if [_const_text(a.term) if isinstance(a, Const) else "" for a in expr.args[1:]] == ["1", "7"] else "{part of the time of the write}"
        if expr.name == "NOW":
            return "{time of the write}"
    return "{" + getattr(expr, "name", type(expr).__name__) + "}"


def _is_now(expr) -> bool:
    while isinstance(expr, Func) and expr.name == "STR" and len(expr.args) == 1:
        expr = expr.args[0]
    return isinstance(expr, Func) and expr.name == "NOW"


def _writes(operation: Operation) -> list[tuple[str, str, Optional[str]]]:
    """The places an operation writes, as (kind, graph, key) in a total order. A place is written where the operation inserts or
    deletes in a graph block, so a graph it only reads is not one."""
    binds = {}
    for node in _walk((operation.where, operation.insert, operation.delete)):
        if isinstance(node, Bind) and node.var.name not in binds:
            binds[node.var.name] = node.expr
    params = {p.name: p for p in operation.params}
    out = set()
    for block in (b for b in _walk((operation.insert, operation.delete)) if isinstance(b, GraphBlock)):
        role, term = block.graph.role, block.graph.term
        graph = _rule(term, binds, params)
        name = getattr(term, "name", "")
        predicates = [
            "a" if t.predicate == A else f"<{_const_text(t.predicate.term)}>" if isinstance(t.predicate, Const) else ""
            for t in _walk(block.elements) if isinstance(t, Triple)
        ]
        if role is GraphRole.DATA:
            kinds = ["version" if operation.id.startswith("append-version") else "data-graph"]
        elif role is GraphRole.PATCH:
            kinds = ["patch-log-del" if name == "delGraph" else "patch-log-add"]
        elif role is GraphRole.KEYS:
            kinds = sorted({"key-claim" if resource_of("keys", p) is ResourceKind.KEY_CLAIM else "merge-record" for p in predicates} or {"key-claim"})
        else:
            kinds = [_ROLE_KINDS[role]]
        for kind in kinds:
            out.add((kind, graph))
    return sorted(out, key=lambda item: (KINDS.index(item[0]), item[1]))


# --- the boundary, from the edges the compiled profile states --------------------------------------------------------------


def _edge(profile: Graph, node) -> dict:
    def local(term):
        return None if term is None else str(term).rsplit("#", 1)[-1]

    return {
        "source": str(profile.value(node, DAL.edgeSource)),
        "property": str(profile.value(node, DAL.edgePredicate)),
        "inverse": str(profile.value(node, DAL.edgeInverse)) == "true",
        "ownership": local(profile.value(node, DAL.edgeOwnership)),
        "class": None if profile.value(node, DAL.edgeTargetClass) is None else str(profile.value(node, DAL.edgeTargetClass)),
        "shape": None if profile.value(node, DAL.edgeTargetShape) is None else str(profile.value(node, DAL.edgeTargetShape)),
        "mode": local(profile.value(node, DAL.referenceMode)) or "ByIdentity",
    }


def _aggregate(profile: Graph, node, root_class: str, strategy: Optional[str]) -> dict:
    edges = sorted((_edge(profile, e) for e in profile.objects(node, DAL.referenceEdge)), key=lambda e: (e["source"], e["property"], e["inverse"], e["shape"] or ""))
    declared = sorted({str(shape) for op in profile.objects(node, DAL.generatedOperation)
                       for contract in profile.objects(op, DAL.payloadContract)
                       for shape in profile.objects(contract, DAL.boundaryShape) if shape != DAL.NoBoundaryShape})
    sources = sorted({e["source"] for e in edges} - {e["shape"] for e in edges if e["shape"]})
    root_shape = declared[0] if declared else sources[0] if sources else None

    def reference(e: dict) -> dict:
        return {"property": e["property"], "inverse": e["inverse"], "class": e["class"], "ownership": e["ownership"], "mode": e["mode"]}

    def level(shape: Optional[str], path: frozenset) -> tuple[list, list]:
        owned, references = [], []
        for e in (e for e in edges if e["source"] == shape):
            if e["ownership"] == "Owned":
                inner_owned, inner_references = level(e["shape"], path | {shape}) if e["shape"] and e["shape"] not in path | {shape} else ([], [])
                owned.append({"property": e["property"], "inverse": e["inverse"], "class": e["class"], "shape": e["shape"], "owned": inner_owned, "references": inner_references})
            else:
                references.append(reference(e))
        return owned, references

    owned, references = level(root_shape, frozenset())
    return {"strategy": strategy, "rootClass": root_class, "rootShape": root_shape, "owned": owned, "references": references}


# --- the document ----------------------------------------------------------------------------------------------------------


def landing_places(profile: Graph, source: Graph) -> dict:
    """The landing places of every target of a compiled profile. `source` is the graph the compiler was given, the persistence
    configuration with its baseline, from which the scope each winning profile applies to is read and the scopes a target matches
    are derived."""
    scopes = all_scopes(source)
    targets = []
    for node in sorted(profile.subjects(RDF.type, DAL.CompiledProfile), key=lambda n: (str(profile.value(n, DAL.forTarget)), str(profile.value(n, DAL.forDeployment) or ""))):
        cls = profile.value(node, DAL.forTarget)
        deployment = profile.value(node, DAL.forDeployment)
        group = target_group(profile, node)
        winners = sorted({str(w) for d in profile.objects(node, DAL.resolvedDimension) for w in profile.objects(d, DAL.wonBy)})
        constraints = sorted(str(c) for c in profile.objects(node, DAL.appliedUniquenessConstraint))
        resolved_from = sorted({str(s) for owner in (*winners, *constraints) for s in source.objects(URIRef(owner), DAL.appliesTo)})
        matched = sorted(str(s.iri) for s in scopes if matches(source, s, Target(cls, deployment)))
        strategy = next((str(profile.value(d, DAL.resolvedValue)).rsplit("#", 1)[-1] for d in profile.objects(node, DAL.resolvedDimension)
                         if str(profile.value(d, DAL.dimension)) == "aggregateBoundary" and profile.value(d, DAL.resolvedValue) is not None), None)
        places: dict = {}
        operations = []
        for op in profile.objects(node, DAL.generatedOperation):
            name, operation = build_operation(profile, op)
            template = str(profile.value(profile.value(op, DAL.usesTemplate), DAL.templateId))
            operations.append({
                "operation": name, "templateId": template, "kind": str(profile.value(op, DAL.operationKind)).rsplit("#", 1)[-1], "path": artefact_path(group, name),
            })
            constraint = next((str(profile.value(b, DAL.paramValue)).strip('"') for b in profile.objects(op, DAL.hasParameterBinding) if str(profile.value(b, DAL.paramName)) == "constraintId"), None)
            for kind, graph in _writes(operation):
                key = (kind, graph, constraint if kind in ("key-claim", "merge-record") else None)
                place = places.setdefault(key, {"from": set(), "operations": set()})
                place["from"].add(template)
                place["operations"].add(name)
        placed = [
            {
                "kind": kind, "label": _LABELS[kind] + (f", {constraint}" if constraint else ""), "graph": graph,
                "from": sorted(p["from"]), "operations": sorted(p["operations"]),
            }
            for (kind, graph, constraint), p in sorted(places.items(), key=lambda item: (KINDS.index(item[0][0]), item[0][1], item[0][2] or ""))
        ]
        targets.append({
            "id": group, "class": str(cls), "deployment": None if deployment is None else str(deployment),
            "profiles": winners, "scopes": resolved_from, "matchedScopes": matched,
            "aggregate": _aggregate(profile, node, str(cls), strategy),
            "places": placed,
            "operations": sorted(operations, key=lambda o: o["operation"]),
        })
    return {"targets": targets}


def landing_places_json(profile: Graph, source: Graph) -> str:
    return json.dumps(landing_places(profile, source), sort_keys=True, indent=2) + "\n"


__all__ = ["LANDING_PLACES", "KINDS", "artefact_path", "target_group", "landing_places", "landing_places_json"]
