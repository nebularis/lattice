# src/spc/util/iri.py
"""IRI minting utilities for A-Box individuals."""

from rdflib import URIRef
from spc.util.namespaces import PROTO


def mint_global_type_iri(protocol_name: str, *path_segments: str) -> URIRef:
    """Mint an IRI for a global type individual."""
    segments = "_".join(str(s) for s in path_segments)
    return PROTO[f"{protocol_name}/global/{segments}"]


def mint_local_type_iri(protocol_name: str, participant: str, *path_segments: str) -> URIRef:
    """Mint an IRI for a local type individual."""
    segments = "_".join(str(s) for s in path_segments)
    return PROTO[f"{protocol_name}/local/{participant}/{segments}"]


def mint_message_option_iri(parent_iri: URIRef, label: str) -> URIRef:
    """Mint an IRI for a message option."""
    return URIRef(f"{parent_iri}/opt_{label}")


def mint_type_option_iri(parent_iri: URIRef, label: str) -> URIRef:
    """Mint an IRI for a type option (local type branch)."""
    return URIRef(f"{parent_iri}/opt_{label}")


def mint_participant_iri(protocol_name: str, name: str) -> URIRef:
    """Mint an IRI for a participant role."""
    return PROTO[f"{protocol_name}/participant/{name}"]


def mint_sort_iri(sort_name: str) -> URIRef:
    """Mint an IRI for a sort."""
    return PROTO[f"sort/{sort_name}"]


def mint_ext_iri(protocol_name: str, ext_type: str, *path_segments: str) -> URIRef:
    """Mint an IRI for an extension annotation individual."""
    segments = "_".join(str(s) for s in path_segments)
    return PROTO[f"{protocol_name}/ext/{ext_type}/{segments}"]