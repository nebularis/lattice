"""Namespaces, and the base-free IRI helpers of plan WA6 section 2.3, for minting proposal nodes."""

from __future__ import annotations

from rdflib import Namespace

WRD = Namespace("https://www.nebularis.org/neuro-semantic/lattice/wording#")
INS = Namespace("https://www.nebularis.org/neuro-semantic/lattice/instrument#")
WAP = Namespace("https://www.nebularis.org/neuro-semantic/lattice/poc/word-authoring#")
PROV = Namespace("http://www.w3.org/ns/prov#")
DCTERMS = Namespace("http://purl.org/dc/terms/")


def doc_base(wording_iri: str) -> str:
    """``D``: the document's own namespace, with a trailing ``/``. ``D + "wording" == wording_iri``."""
    if not wording_iri.endswith("wording"):
        raise ValueError(f"not a wording IRI (does not end with 'wording'): {wording_iri}")
    return wording_iri[: -len("wording")]


def element_iri(base: str, element_id: str) -> str:
    return f"{base}element/{element_id}"


def proposed_relation_iri(base: str, element_id: str) -> str:
    return f"{element_iri(base, element_id)}/meaning"


def parameter_binding_iri(base: str, element_id: str, slot_name: str) -> str:
    return f"{proposed_relation_iri(base, element_id)}/binding/{slot_name}"


def party_role_iri(base: str, definition_element_id: str) -> str:
    return f"{base}role/{definition_element_id}"


def activity_iri(proposal_graph_iri: str) -> str:
    return f"{proposal_graph_iri}#activity"
