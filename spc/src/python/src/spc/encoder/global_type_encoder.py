# src/spc/encoder/global_type_encoder.py
"""
Encode global types (AST) → RDF A-Box individuals.

Each global type construct maps to an individual of the appropriate
SPC T-Box class, with roles connecting to sub-components.
"""

from __future__ import annotations
from rdflib import Graph, URIRef, Literal, RDF
from spc.processle import ast_nodes as ast
from spc.util.namespaces import SPC
from spc.util.iri import (
    mint_global_type_iri, mint_message_option_iri,
    mint_participant_iri, mint_sort_iri,
)
from spc.encoder.refinement_encoder import encode_refinement


def encode_global_type(
    graph: Graph,
    protocol_name: str,
    gt: ast.GlobalType,
    path: list[str],
) -> URIRef:
    """Encode a global type node and return its IRI."""

    if isinstance(gt, ast.End):
        iri = mint_global_type_iri(protocol_name, *path, "end")
        graph.add((iri, RDF.type, SPC.EndGlobalType))
        return iri

    elif isinstance(gt, ast.Communication):
        iri = mint_global_type_iri(
            protocol_name, *path, f"comm_{gt.sender}_{gt.receiver}"
        )
        graph.add((iri, RDF.type, SPC.CommunicationGlobalType))
        graph.add((iri, SPC.hasSenderRole,
                    mint_participant_iri(protocol_name, gt.sender)))
        graph.add((iri, SPC.hasReceiverRole,
                    mint_participant_iri(protocol_name, gt.receiver)))

        for i, opt in enumerate(gt.options):
            opt_iri = mint_message_option_iri(iri, opt.label)
            graph.add((opt_iri, RDF.type, SPC.MessageOption))
            graph.add((opt_iri, SPC.hasOptionLabel, Literal(opt.label)))
            graph.add((opt_iri, SPC.hasPayloadSort,
                        mint_sort_iri(opt.sort)))
            graph.add((iri, SPC.hasMessageOption, opt_iri))

            # Encode refinement predicate if present
            if opt.refinement:
                ref_iri = encode_refinement(
                    graph, protocol_name, opt.refinement,
                    path + [f"opt_{opt.label}"],
                )
                graph.add((opt_iri, SPC.hasRefinementPredicate, ref_iri))

            # Encode continuation
            if opt.continuation:
                cont_iri = encode_global_type(
                    graph, protocol_name, opt.continuation,
                    path + [f"cont_{opt.label}"],
                )
                graph.add((opt_iri, SPC.hasContinuationType, cont_iri))
            else:
                end_iri = encode_global_type(
                    graph, protocol_name, ast.End(),
                    path + [f"cont_{opt.label}"],
                )
                graph.add((opt_iri, SPC.hasContinuationType, end_iri))

        # Encode the sort for each payload
        for opt in gt.options:
            sort_iri = mint_sort_iri(opt.sort)
            if (sort_iri, RDF.type, None) not in graph:
                graph.add((sort_iri, RDF.type, SPC.Sort))
                graph.add((sort_iri, SPC.hasSortName, Literal(opt.sort)))

        return iri

    elif isinstance(gt, ast.ParallelComp):
        iri = mint_global_type_iri(protocol_name, *path, "par")
        graph.add((iri, RDF.type, SPC.ParallelGlobalType))
        left_iri = encode_global_type(
            graph, protocol_name, gt.left, path + ["par_left"]
        )
        right_iri = encode_global_type(
            graph, protocol_name, gt.right, path + ["par_right"]
        )
        graph.add((iri, SPC.hasLeftComponent, left_iri))
        graph.add((iri, SPC.hasRightComponent, right_iri))
        return iri

    elif isinstance(gt, ast.Recursion):
        iri = mint_global_type_iri(protocol_name, *path, f"rec_{gt.var}")
        graph.add((iri, RDF.type, SPC.RecursiveGlobalType))
        graph.add((iri, SPC.hasRecursionVariable, Literal(gt.var)))
        body_iri = encode_global_type(
            graph, protocol_name, gt.body, path + [f"body_{gt.var}"]
        )
        graph.add((iri, SPC.hasRecBody, body_iri))
        return iri

    elif isinstance(gt, ast.RecursionVar):
        iri = mint_global_type_iri(protocol_name, *path, f"var_{gt.var}")
        graph.add((iri, RDF.type, SPC.RecVarGlobalType))
        graph.add((iri, SPC.refersToVariable, Literal(gt.var)))
        return iri

    elif isinstance(gt, ast.SubprotocolCall):
        iri = mint_global_type_iri(
            protocol_name, *path, f"call_{gt.protocol_name}"
        )
        graph.add((iri, RDF.type, SPC.SubprotocolCallGlobalType))
        graph.add((iri, SPC.hasCallerRole,
                    mint_participant_iri(protocol_name, gt.caller)))
        graph.add((iri, SPC.hasProtocolReference, Literal(gt.protocol_name)))
        for arg in gt.role_args:
            graph.add((iri, SPC.hasSubjectArgument,
                        mint_participant_iri(protocol_name, arg)))
        if gt.continuation:
            cont_iri = encode_global_type(
                graph, protocol_name, gt.continuation,
                path + [f"call_cont_{gt.protocol_name}"],
            )
            graph.add((iri, SPC.hasContinuationType, cont_iri))
        return iri

    else:
        raise ValueError(f"Unknown global type: {type(gt).__name__}")