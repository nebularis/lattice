"""Builds the proposed `ins:` graph and its graph view (plan WA6 section "Proposal graph")."""

from __future__ import annotations

from typing import Any, Optional

import rdflib
from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS

from .forms import FormProfile
from .matcher import match as match_form
from .model import Element, Wording
from .namespaces import (
    INS,
    PROV,
    WAP,
    activity_iri,
    doc_base,
    element_iri,
    parameter_binding_iri,
    party_role_iri,
    proposed_relation_iri,
)
from .tokens import tokenise

_HOLDER_CLASSES = {"Permission", "Power"}


def proposal_graph(
    wording: Wording,
    element_analyses: list[dict[str, Any]],
    proposal_graph_iri: str,
    profile: FormProfile,
) -> rdflib.Graph:
    base = doc_base(wording.iri)
    graph = rdflib.Graph()
    activity = URIRef(activity_iri(proposal_graph_iri))
    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((activity, PROV.used, URIRef(wording.iri)))
    graph.add((activity, WAP.formsProfile, Literal(f"{profile.profile_id} {profile.version}")))

    elements_by_id = {element.element_id: element for element in wording.elements}
    variables_by_key = {variable.key: variable for variable in wording.variables}
    variable_types = {variable.key: variable.value_type for variable in wording.variables}
    forms_by_id = {form.form_id: form for form in profile.forms}
    role_iris: dict[str, str] = {}

    for analysis in element_analyses:
        relation_class = analysis.get("relationClass")
        if not relation_class:
            continue
        element = elements_by_id[analysis["elementId"]]
        relation = URIRef(proposed_relation_iri(base, element.element_id))
        graph.add((relation, RDF.type, INS[relation_class]))
        graph.add((relation, INS.expressedIn, URIRef(element.iri)))
        graph.add((relation, WAP.proposalBasis, Literal(analysis["basis"])))
        graph.add((relation, PROV.wasGeneratedBy, activity))
        if analysis.get("formId"):
            graph.add((relation, WAP.sentenceForm, Literal(analysis["formId"])))

        if relation_class == "Definition":
            if element.defined_term:
                graph.add((relation, WAP.definesTerm, Literal(element.defined_term)))
            continue

        party_element_id, activity_text, variable_bindings = _reconstruct(
            analysis, element, profile, forms_by_id, variable_types
        )

        if party_element_id is not None:
            role_iri = role_iris.get(party_element_id)
            if role_iri is None:
                role_iri = party_role_iri(base, party_element_id)
                role_iris[party_element_id] = role_iri
                role = URIRef(role_iri)
                target = elements_by_id.get(party_element_id)
                graph.add((role, RDF.type, WAP.PartyRole))
                if target is not None and target.defined_term:
                    graph.add((role, RDFS.label, Literal(target.defined_term)))
                named_by = URIRef(target.iri) if target is not None else URIRef(element_iri(base, party_element_id))
                graph.add((role, WAP.namedBy, named_by))
            party_predicate = INS.holder if relation_class in _HOLDER_CLASSES else INS.obligor
            graph.add((relation, party_predicate, URIRef(role_iri)))

        for slot_name, variable_key in variable_bindings:
            variable = variables_by_key[variable_key]
            binding = URIRef(parameter_binding_iri(base, element.element_id, slot_name))
            graph.add((relation, INS.hasParameterBinding, binding))
            graph.add((binding, RDF.type, INS.ParameterBinding))
            graph.add((binding, INS.parameterKind, WAP[slot_name]))
            graph.add((binding, INS.fromVariable, URIRef(variable.iri)))

        if activity_text is not None:
            graph.add((relation, WAP.activityText, Literal(activity_text)))

    return graph


def _reconstruct(
    analysis: dict[str, Any],
    element: Element,
    profile: FormProfile,
    forms_by_id: dict[str, Any],
    variable_types: dict[str, str],
) -> tuple[Optional[str], Optional[str], list[tuple[str, str]]]:
    """Re-derives the party, activity text and variable bindings a match (or the keyword rule)
    found. The common schema's ElementAnalysis carries no slot detail, only formId and
    relationClass, so the match is re-run deterministically against the one form it named."""
    if analysis["basis"] == "form":
        form = forms_by_id[analysis["formId"]]
        tokens = tokenise(element)
        result = match_form(tokens, form, profile.ignorable, element, variable_types)
        party_element_id: Optional[str] = None
        activity_text: Optional[str] = None
        variable_bindings: list[tuple[str, str]] = []
        if result is not None:
            for slot_name, (slot, slot_tokens) in result.slots.items():
                if slot.type == "party":
                    part = element.parts[slot_tokens[0].part_index]
                    party_element_id = part.target_element_id
                elif slot.type == "variable":
                    part = element.parts[slot_tokens[0].part_index]
                    variable_bindings.append((slot_name, part.variable_key))
                elif slot.type == "text" and slot_name == "activity":
                    activity_text = element.text[slot_tokens[0].start : slot_tokens[-1].end]
        return party_element_id, activity_text, variable_bindings

    if analysis["basis"] == "keyword":
        tokens = [token for token in tokenise(element) if token.norm not in profile.ignorable]
        if tokens and tokens[0].kind == "constant":
            part = element.parts[tokens[0].part_index]
            return part.target_element_id, None, []
        return None, None, []

    return None, None, []


def graph_view(wording: Wording, graph: rdflib.Graph) -> dict[str, Any]:
    elements_by_iri = {element.iri: element for element in wording.elements}
    variables_by_iri = {variable.iri: variable for variable in wording.variables}

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []

    for relation in sorted({str(s) for s in graph.subjects(INS.expressedIn, None)}):
        relation_ref = URIRef(relation)
        relation_class = str(next(graph.objects(relation_ref, RDF.type))).rsplit("#", 1)[-1]
        element_ref = next(graph.objects(relation_ref, INS.expressedIn))
        element = elements_by_iri[str(element_ref)]

        nodes[relation] = {"id": relation, "label": f"{relation_class} {element.object_id}", "kind": "relation"}

        element_label = ("Definition " if element.kind == "definition" else "Clause ") + element.object_id
        nodes.setdefault(str(element_ref), {"id": str(element_ref), "label": element_label, "kind": "element"})
        edges.append({"from": relation, "to": str(element_ref), "label": "expressedIn"})

        for predicate, label in ((INS.obligor, "obligor"), (INS.holder, "holder")):
            for role in graph.objects(relation_ref, predicate):
                role_iri = str(role)
                term = next(graph.objects(role, RDFS.label), None)
                nodes.setdefault(role_iri, {"id": role_iri, "label": str(term) if term else role_iri, "kind": "role"})
                edges.append({"from": relation, "to": role_iri, "label": label})

        for binding in graph.objects(relation_ref, INS.hasParameterBinding):
            parameter_kind = next(graph.objects(binding, INS.parameterKind))
            slot_name = str(parameter_kind).rsplit("#", 1)[-1]
            variable_ref = next(graph.objects(binding, INS.fromVariable))
            variable_iri_str = str(variable_ref)
            variable = variables_by_iri.get(variable_iri_str)
            label = variable.key if variable is not None else variable_iri_str
            nodes.setdefault(variable_iri_str, {"id": variable_iri_str, "label": label, "kind": "variable"})
            edges.append({"from": relation, "to": variable_iri_str, "label": slot_name})

    kind_order = {"relation": 0, "element": 1, "role": 2, "variable": 3}
    sorted_nodes = sorted(nodes.values(), key=lambda node: (kind_order[node["kind"]], node["id"]))
    sorted_edges = sorted(edges, key=lambda edge: (edge["from"], edge["label"], edge["to"]))
    return {"nodes": sorted_nodes, "edges": sorted_edges}
