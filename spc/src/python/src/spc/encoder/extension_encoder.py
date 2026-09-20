# src/spc/encoder/extension_encoder.py
"""
Encode extension annotations (timers, retries, errors, etc.) as
A-Box individuals in the appropriate EXT ontology namespaces.
"""

from __future__ import annotations
from rdflib import Graph, Literal, RDF, XSD
from spc.processle import ast_nodes as ast
from spc.util.namespaces import (
    EXT_TIMER, EXT_JOB, EXT_ERROR, EXT_COMP, EXT_SIGNAL, EXT_CONN,
)
from spc.util.iri import mint_ext_iri, mint_participant_iri


def encode_extensions(graph: Graph, protocol: ast.Protocol) -> None:
    """Encode all extension annotations from the protocol."""
    for ext in protocol.extensions:
        if isinstance(ext, ast.TimerAnnotation):
            _encode_timer(graph, protocol.name, ext)
        elif isinstance(ext, ast.RetryAnnotation):
            _encode_retry(graph, protocol.name, ext)
        elif isinstance(ext, ast.ErrorAnnotation):
            _encode_error(graph, protocol.name, ext)
        elif isinstance(ext, ast.CompensationAnnotation):
            _encode_compensation(graph, protocol.name, ext)
        elif isinstance(ext, ast.SignalAnnotation):
            _encode_signal(graph, protocol.name, ext)
        elif isinstance(ext, ast.ConnectorAnnotation):
            _encode_connector(graph, protocol.name, ext)


def _encode_timer(graph: Graph, protocol_name: str, t: ast.TimerAnnotation):
    iri = mint_ext_iri(protocol_name, "timer",
                       t.target_participant or "", t.target_label or "")
    graph.add((iri, RDF.type, EXT_TIMER.TimerBinding))
    if t.target_participant:
        graph.add((iri, EXT_TIMER.bindsParticipant,
                    mint_participant_iri(protocol_name, t.target_participant)))
    if t.target_label:
        graph.add((iri, EXT_TIMER.afterLabel, Literal(t.target_label)))
    graph.add((iri, EXT_TIMER.hasTimeoutType,
                Literal(t.timer_type)))
    if t.duration:
        graph.add((iri, EXT_TIMER.hasDuration,
                    Literal(t.duration, datatype=XSD.duration)))
    if t.cron:
        graph.add((iri, EXT_TIMER.hasCronString, Literal(t.cron)))
    if t.timeout_label:
        graph.add((iri, EXT_TIMER.hasTimeoutLabel, Literal(t.timeout_label)))


def _encode_retry(graph: Graph, protocol_name: str, r: ast.RetryAnnotation):
    iri = mint_ext_iri(protocol_name, "job",
                       r.target_participant or "", r.target_label or "")
    graph.add((iri, RDF.type, EXT_JOB.JobBinding))
    if r.target_participant:
        graph.add((iri, EXT_JOB.bindsParticipant,
                    mint_participant_iri(protocol_name, r.target_participant)))
    if r.target_label:
        graph.add((iri, EXT_JOB.bindsLabel, Literal(r.target_label)))
    graph.add((iri, EXT_JOB.maxAttempts,
                Literal(r.max_attempts, datatype=XSD.integer)))
    graph.add((iri, EXT_JOB.backoffStrategy, Literal(r.backoff)))
    graph.add((iri, EXT_JOB.baseDelay,
                Literal(r.base_delay, datatype=XSD.duration)))
    graph.add((iri, EXT_JOB.multiplier,
                Literal(r.multiplier, datatype=XSD.decimal)))
    graph.add((iri, EXT_JOB.jitterPercent,
                Literal(r.jitter_pct, datatype=XSD.decimal)))
    if r.on_exhausted_label:
        graph.add((iri, EXT_JOB.onExhaustedLabel,
                    Literal(r.on_exhausted_label)))
    if r.on_exhausted_escalate:
        graph.add((iri, EXT_JOB.onExhaustedEscalate,
                    mint_participant_iri(protocol_name, r.on_exhausted_escalate)))


def _encode_error(graph: Graph, protocol_name: str, e: ast.ErrorAnnotation):
    iri = mint_ext_iri(protocol_name, "error",
                       e.target_participant or "", e.error_type)
    graph.add((iri, RDF.type, EXT_ERROR.ErrorHandler))
    if e.target_participant:
        graph.add((iri, EXT_ERROR.bindsParticipant,
                    mint_participant_iri(protocol_name, e.target_participant)))
    graph.add((iri, EXT_ERROR.handlesErrorType, Literal(e.error_type)))
    if e.recovery_label:
        graph.add((iri, EXT_ERROR.recoversVia, Literal(e.recovery_label)))
    if e.escalate_to:
        graph.add((iri, EXT_ERROR.escalatesTo,
                    mint_participant_iri(protocol_name, e.escalate_to)))


def _encode_compensation(graph: Graph, protocol_name: str,
                          c: ast.CompensationAnnotation):
    scope_iri = mint_ext_iri(protocol_name, "comp_scope", c.scope_name)
    # Ensure scope exists
    graph.add((scope_iri, RDF.type, EXT_COMP.CompScope))
    graph.add((scope_iri, EXT_COMP.hasScopeId, Literal(c.scope_name)))
    graph.add((scope_iri, EXT_COMP.hasOrdering, Literal(c.ordering)))

    pair_iri = mint_ext_iri(protocol_name, "comp_pair",
                            c.action_label or "", c.comp_label or "")
    graph.add((pair_iri, RDF.type, EXT_COMP.CompPair))
    if c.action_label:
        graph.add((pair_iri, EXT_COMP.hasActionLabel, Literal(c.action_label)))
    if c.comp_label:
        graph.add((pair_iri, EXT_COMP.hasCompLabel, Literal(c.comp_label)))
    graph.add((scope_iri, EXT_COMP.includesPair, pair_iri))


def _encode_signal(graph: Graph, protocol_name: str, s: ast.SignalAnnotation):
    iri = mint_ext_iri(protocol_name, "signal",
                       s.target_participant or "", s.target_label or "")
    graph.add((iri, RDF.type, EXT_SIGNAL.SignalBinding))
    if s.target_participant:
        graph.add((iri, EXT_SIGNAL.bindsParticipant,
                    mint_participant_iri(protocol_name, s.target_participant)))
    if s.target_label:
        graph.add((iri, EXT_SIGNAL.bindsLabel, Literal(s.target_label)))
    if s.topic:
        graph.add((iri, EXT_SIGNAL.emitsTo, Literal(s.topic)))
    graph.add((iri, EXT_SIGNAL.usesExchange, Literal(s.exchange_type)))
    if s.routing_key_template:
        graph.add((iri, EXT_SIGNAL.routingKeyTemplate,
                    Literal(s.routing_key_template)))
    for cf in s.correlation_fields:
        graph.add((iri, EXT_SIGNAL.hasCorrelationField, Literal(cf)))
    graph.add((iri, EXT_SIGNAL.direction, Literal(s.direction)))


def _encode_connector(graph: Graph, protocol_name: str,
                       c: ast.ConnectorAnnotation):
    iri = mint_ext_iri(protocol_name, "connector", c.connector_name or "")
    graph.add((iri, RDF.type, EXT_CONN.ConnectorSpec))
    if c.connector_name:
        graph.add((iri, EXT_CONN.hasConnectorName, Literal(c.connector_name)))
    graph.add((iri, EXT_CONN.hasConnectorType, Literal(c.connector_type)))
    if c.base_url:
        graph.add((iri, EXT_CONN.hasBaseURL,
                    Literal(c.base_url, datatype=XSD.anyURI)))
    if c.timeout:
        graph.add((iri, EXT_CONN.hasTimeout,
                    Literal(c.timeout, datatype=XSD.duration)))
    for k, v in c.headers.items():
        header_iri = mint_ext_iri(
            protocol_name, "connector", c.connector_name or "", f"header_{k}")
        graph.add((header_iri, RDF.type, EXT_CONN.HeaderEntry))
        graph.add((header_iri, EXT_CONN.headerName, Literal(k)))
        graph.add((header_iri, EXT_CONN.headerValue, Literal(v)))
        graph.add((iri, EXT_CONN.hasHeader, header_iri))