# src/spc/encoder/abox_compiler.py
"""
Main A-Box compiler: Protocol AST → RDF graph.

Orchestrates the encoding of all AST components into OWL A-Box
individuals that instantiate the SPC T-Box.
"""

from __future__ import annotations
from pathlib import Path
from rdflib import Graph, URIRef, Literal, BNode
from rdflib import RDF, RDFS, OWL, XSD

from spc.processle import ast_nodes as ast
from spc.util.namespaces import SPC, PROTO, bind_namespaces
from spc.util.iri import (
    mint_global_type_iri, mint_local_type_iri,
    mint_message_option_iri, mint_participant_iri, mint_sort_iri,
    mint_ext_iri,
)
from spc.encoder.global_type_encoder import encode_global_type
from spc.encoder.typing_encoder import encode_typing_judgments
from spc.encoder.subtyping import compute_and_encode_subtyping
from spc.encoder.refinement_encoder import encode_refinement
from spc.encoder.extension_encoder import encode_extensions


class ABoxCompiler:
    """Compile a Protocol AST into an RDF graph of A-Box individuals."""

    def __init__(self, domain_ontology_iri: str = ""):
        self.domain_ontology_iri = domain_ontology_iri
        self.graph = Graph()
        bind_namespaces(self.graph)
        self._counter = 0

    def compile(self, protocol: ast.Protocol) -> Graph:
        """Compile the protocol to RDF. Returns the graph."""
        proto_iri = PROTO[protocol.name]

        # 1. Encode participant declarations
        for p in protocol.participants:
            p_iri = mint_participant_iri(protocol.name, p.name)
            self.graph.add((p_iri, RDF.type, SPC.ParticipantRole))
            self.graph.add((p_iri, SPC.hasRoleName, Literal(p.name)))

        # 2. Encode the global type
        gt_iri = encode_global_type(
            self.graph, protocol.name, protocol.global_type, []
        )

        # 3. Encode the protocol as a WellFormedGlobalType assertion
        self.graph.add((proto_iri, RDF.type, SPC.WellFormedGlobalType))
        self.graph.add((proto_iri, SPC.hasGlobalTypeRoot, gt_iri))
        self.graph.add((proto_iri, SPC.hasProtocolName, Literal(protocol.name)))

        # 4. Encode subprotocol declarations
        for sp in protocol.subprotocols:
            sp_iri = PROTO[f"{protocol.name}/subprotocol/{sp.name}"]
            self.graph.add((sp_iri, RDF.type, SPC.ProtocolDeclaration))
            self.graph.add((sp_iri, SPC.hasProtocolName, Literal(sp.name)))
            for rp in sp.role_params:
                rp_iri = PROTO[f"{protocol.name}/subprotocol/{sp.name}/role/{rp.name}"]
                self.graph.add((rp_iri, RDF.type, SPC.RoleParameter))
                self.graph.add((rp_iri, SPC.hasRoleName, Literal(rp.name)))
                self.graph.add((sp_iri, SPC.hasRoleParameter, rp_iri))
            sp_body_iri = encode_global_type(
                self.graph, protocol.name, sp.body,
                [f"sub_{sp.name}"],
            )
            self.graph.add((sp_iri, SPC.hasProtocolBody, sp_body_iri))

        # 5. Compute and encode typing judgments
        encode_typing_judgments(self.graph, protocol)

        # 6. Compute and encode subtyping (where needed for internal choice)
        compute_and_encode_subtyping(self.graph, protocol)

        # 7. Encode extension annotations
        encode_extensions(self.graph, protocol)

        return self.graph

    def serialize(self, path: Path, fmt: str = "turtle") -> None:
        """Serialize the graph to a file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        self.graph.serialize(destination=str(path), format=fmt)