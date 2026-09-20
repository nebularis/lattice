# src/spc/encoder/typing_encoder.py
"""
Compute and encode typing judgments.

Walks the AST to compute local types via projection, then creates
TypingAssertion A-Box individuals linking behaviors to local types.
"""

from __future__ import annotations
from rdflib import Graph, Literal, RDF
from spc.processle import ast_nodes as ast
from spc.util.namespaces import SPC, PROTO
from spc.util.iri import mint_participant_iri


def encode_typing_judgments(graph: Graph, protocol: ast.Protocol) -> None:
    """Compute typing judgments for each participant and encode them."""
    participants = {p.name for p in protocol.participants}

    for participant_name in participants:
        # Create a typing assertion recording that this participant
        # is typed by the protocol
        ta_iri = PROTO[f"{protocol.name}/typing/{participant_name}"]
        graph.add((ta_iri, RDF.type, SPC.TypingAssertion))
        graph.add((ta_iri, SPC.hasTypedParticipant,
                    mint_participant_iri(protocol.name, participant_name)))
        graph.add((ta_iri, SPC.hasProtocolReference,
                    Literal(protocol.name)))

        # The actual local type computation happens during projection
        # materialisation (Phase 2a) via SPARQL. Here we just record
        # the intent that a typing exists.