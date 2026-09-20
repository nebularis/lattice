# src/spc/extract/extension_config_gen.py
"""
Generate the runtime extension configuration JSON from the
extension A-Box individuals in Jena.

This is the bridge between the OWL-encoded extensions and the
Erlang runtime's configuration-driven extension modules.

Queries the Jena store for all EXT individuals, resolves references
to state IDs (via the state machine table), and produces the JSON
structure expected by spc_extension_config.erl.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Optional
import re
import isodate

from spc.verify.jena_client import JenaClient
from spc.util.json_ser import write_json
from spc.util.namespaces import (
    EXT_TIMER, EXT_JOB, EXT_ERROR, EXT_COMP, EXT_SIGNAL, EXT_CONN,
)


class ExtensionConfigGenerator:
    """Generate extension config JSON from the Jena knowledge base."""

    def __init__(self, jena_client: JenaClient,
                 state_table: dict[str, Any]):
        """
        Args:
            jena_client: Client for querying the Jena store
            state_table: The already-extracted state machine table (JSON dict).
                         Used to resolve participant/label references to state IDs.
        """
        self.jena = jena_client
        self.state_table = state_table
        self._label_to_state: dict[tuple[str, str], int] = {}
        self._build_label_index()

    def generate(self, protocol_name: str) -> dict[str, Any]:
        """Generate the complete extension config for a protocol."""
        return {
            "protocol": protocol_name,
            "version": "1.0.0",
            "timers": self._generate_timers(protocol_name),
            "jobs": self._generate_jobs(protocol_name),
            "errors": self._generate_errors(protocol_name),
            "compensation": self._generate_compensation(protocol_name),
            "signals": self._generate_signals(protocol_name),
            "connectors": self._generate_connectors(protocol_name),
        }

    def generate_to_file(self, protocol_name: str, path: Path) -> None:
        """Generate and write to file."""
        config = self.generate(protocol_name)
        write_json(config, path)

    # --- Timer generation ---

    def _generate_timers(self, protocol_name: str) -> list[dict]:
        query = f"""
        PREFIX ext-timer: <{EXT_TIMER}>
        PREFIX spc: <http://spc.marsh.com/ontology/core#>
        SELECT ?binding ?participant ?afterLabel ?type ?duration ?cron
               ?timeoutLabel
        WHERE {{
            ?binding a ext-timer:TimerBinding .
            OPTIONAL {{ ?binding ext-timer:bindsParticipant ?pIri .
                        ?pIri spc:hasRoleName ?participant . }}
            OPTIONAL {{ ?binding ext-timer:afterLabel ?afterLabel . }}
            OPTIONAL {{ ?binding ext-timer:hasTimeoutType ?type . }}
            OPTIONAL {{ ?binding ext-timer:hasDuration ?duration . }}
            OPTIONAL {{ ?binding ext-timer:hasCronString ?cron . }}
            OPTIONAL {{ ?binding ext-timer:hasTimeoutLabel ?timeoutLabel . }}
        }}
        """
        results = self.jena.sparql_query(query)
        timers = []
        for b in results.get("results", {}).get("bindings", []):
            participant = _val(b, "participant")
            after_label = _val(b, "afterLabel")
            timeout_label = _val(b, "timeoutLabel")
            duration_str = _val(b, "duration")
            cron = _val(b, "cron")

            # Resolve state ID from state table
            state_id = self._resolve_recv_state_after_send(
                participant, after_label)
            target_state = self._resolve_label_target(
                participant, timeout_label)

            duration_ms = _parse_duration_ms(duration_str) if duration_str else None

            timers.append({
                "participant": participant,
                "state_id": state_id,
                "type": _val(b, "type") or "interrupting",
                "duration_ms": duration_ms,
                "cron": cron,
                "timeout_label": timeout_label,
                "target_state": target_state,
            })
        return timers

    # --- Job/Retry generation ---

    def _generate_jobs(self, protocol_name: str) -> list[dict]:
        query = f"""
        PREFIX ext-job: <{EXT_JOB}>
        PREFIX spc: <http://spc.marsh.com/ontology/core#>
        SELECT ?binding ?participant ?label ?maxAttempts ?backoff
               ?baseDelay ?multiplier ?jitter ?exhaustedLabel ?exhaustedEscalate
        WHERE {{
            ?binding a ext-job:JobBinding .
            OPTIONAL {{ ?binding ext-job:bindsParticipant ?pIri .
                        ?pIri spc:hasRoleName ?participant . }}
            OPTIONAL {{ ?binding ext-job:bindsLabel ?label . }}
            OPTIONAL {{ ?binding ext-job:maxAttempts ?maxAttempts . }}
            OPTIONAL {{ ?binding ext-job:backoffStrategy ?backoff . }}
            OPTIONAL {{ ?binding ext-job:baseDelay ?baseDelay . }}
            OPTIONAL {{ ?binding ext-job:multiplier ?multiplier . }}
            OPTIONAL {{ ?binding ext-job:jitterPercent ?jitter . }}
            OPTIONAL {{ ?binding ext-job:onExhaustedLabel ?exhaustedLabel . }}
            OPTIONAL {{ ?binding ext-job:onExhaustedEscalate ?escIri .
                        ?escIri spc:hasRoleName ?exhaustedEscalate . }}
        }}
        """
        results = self.jena.sparql_query(query)
        jobs = []
        for b in results.get("results", {}).get("bindings", []):
            base_delay_str = _val(b, "baseDelay")
            on_exhausted = None
            if _val(b, "exhaustedLabel"):
                on_exhausted = {"type": "error_label",
                                "label": _val(b, "exhaustedLabel")}
            elif _val(b, "exhaustedEscalate"):
                on_exhausted = {"type": "escalate",
                                "to": _val(b, "exhaustedEscalate")}

            jobs.append({
                "participant": _val(b, "participant"),
                "label": _val(b, "label"),
                "max_attempts": int(_val(b, "maxAttempts") or 3),
                "backoff_strategy": _val(b, "backoff") or "exponential",
                "base_delay_ms": _parse_duration_ms(base_delay_str) if base_delay_str else 1000,
                "multiplier": float(_val(b, "multiplier") or 2.0),
                "jitter_pct": float(_val(b, "jitter") or 0.1),
                "max_delay_ms": 60000,
                "on_exhausted": on_exhausted,
            })
        return jobs

    # --- Error generation ---

    def _generate_errors(self, protocol_name: str) -> list[dict]:
        query = f"""
        PREFIX ext-error: <{EXT_ERROR}>
        PREFIX spc: <http://spc.marsh.com/ontology/core#>
        SELECT ?handler ?participant ?errorType ?recoveryLabel ?escalateTo
        WHERE {{
            ?handler a ext-error:ErrorHandler .
            OPTIONAL {{ ?handler ext-error:bindsParticipant ?pIri .
                        ?pIri spc:hasRoleName ?participant . }}
            OPTIONAL {{ ?handler ext-error:handlesErrorType ?errorType . }}
            OPTIONAL {{ ?handler ext-error:recoversVia ?recoveryLabel . }}
            OPTIONAL {{ ?handler ext-error:escalatesTo ?escIri .
                        ?escIri spc:hasRoleName ?escalateTo . }}
        }}
        """
        results = self.jena.sparql_query(query)
        errors = []
        for b in results.get("results", {}).get("bindings", []):
            participant = _val(b, "participant")
            recovery_label = _val(b, "recoveryLabel")
            recovery_state = self._resolve_label_target(
                participant, recovery_label) if recovery_label else None

            errors.append({
                "participant": participant,
                "error_type": _val(b, "errorType") or "unknown",
                "recovery_label": recovery_label,
                "recovery_state": recovery_state,
                "escalate_to": _val(b, "escalateTo"),
            })
        return errors

    # --- Compensation generation ---

    def _generate_compensation(self, protocol_name: str) -> list[dict]:
        query = f"""
        PREFIX ext-comp: <{EXT_COMP}>
        SELECT ?scope ?scopeId ?ordering ?pair ?actionLabel ?compLabel
        WHERE {{
            ?scope a ext-comp:CompScope .
            ?scope ext-comp:hasScopeId ?scopeId .
            ?scope ext-comp:hasOrdering ?ordering .
            ?scope ext-comp:includesPair ?pair .
            ?pair ext-comp:hasActionLabel ?actionLabel .
            ?pair ext-comp:hasCompLabel ?compLabel .
        }}
        """
        results = self.jena.sparql_query(query)

        # Group by scope
        scopes: dict[str, dict] = {}
        for b in results.get("results", {}).get("bindings", []):
            scope_id = _val(b, "scopeId")
            if scope_id not in scopes:
                scopes[scope_id] = {
                    "scope_id": scope_id,
                    "ordering": _val(b, "ordering") or "sequential",
                    "pairs": [],
                }
            action_label = _val(b, "actionLabel")
            comp_label = _val(b, "compLabel")
            scopes[scope_id]["pairs"].append({
                "action_label": action_label,
                "action_state": self._resolve_send_state(None, action_label),
                "comp_label": comp_label,
                "comp_state": self._resolve_send_state(None, comp_label),
            })

        return list(scopes.values())

    # --- Signal generation ---

    def _generate_signals(self, protocol_name: str) -> list[dict]:
        query = f"""
        PREFIX ext-signal: <{EXT_SIGNAL}>
        PREFIX spc: <http://spc.marsh.com/ontology/core#>
        SELECT ?binding ?participant ?label ?topic ?exchange
               ?routingKey ?direction ?corrField
        WHERE {{
            ?binding a ext-signal:SignalBinding .
            OPTIONAL {{ ?binding ext-signal:bindsParticipant ?pIri .
                        ?pIri spc:hasRoleName ?participant . }}
            OPTIONAL {{ ?binding ext-signal:bindsLabel ?label . }}
            OPTIONAL {{ ?binding ext-signal:emitsTo ?topic . }}
            OPTIONAL {{ ?binding ext-signal:usesExchange ?exchange . }}
            OPTIONAL {{ ?binding ext-signal:routingKeyTemplate ?routingKey . }}
            OPTIONAL {{ ?binding ext-signal:direction ?direction . }}
            OPTIONAL {{ ?binding ext-signal:hasCorrelationField ?corrField . }}
        }}
        """
        results = self.jena.sparql_query(query)

        # Group correlation fields by binding
        signal_map: dict[str, dict] = {}
        for b in results.get("results", {}).get("bindings", []):
            binding_iri = b.get("binding", {}).get("value", "")
            if binding_iri not in signal_map:
                signal_map[binding_iri] = {
                    "participant": _val(b, "participant"),
                    "label": _val(b, "label"),
                    "topic": _val(b, "topic"),
                    "exchange_type": _val(b, "exchange") or "topic",
                    "routing_key_template": _val(b, "routingKey") or "",
                    "correlation_fields": [],
                    "direction": _val(b, "direction") or "emit",
                }
            cf = _val(b, "corrField")
            if cf:
                signal_map[binding_iri]["correlation_fields"].append(cf)

        return list(signal_map.values())

    # --- Connector generation ---

    def _generate_connectors(self, protocol_name: str) -> list[dict]:
        query = f"""
        PREFIX ext-conn: <{EXT_CONN}>
        SELECT ?conn ?name ?type ?baseUrl ?timeout
        WHERE {{
            ?conn a ext-conn:ConnectorSpec .
            OPTIONAL {{ ?conn ext-conn:hasConnectorName ?name . }}
            OPTIONAL {{ ?conn ext-conn:hasConnectorType ?type . }}
            OPTIONAL {{ ?conn ext-conn:hasBaseURL ?baseUrl . }}
            OPTIONAL {{ ?conn ext-conn:hasTimeout ?timeout . }}
        }}
        """
        results = self.jena.sparql_query(query)
        connectors = []
        for b in results.get("results", {}).get("bindings", []):
            name = _val(b, "name")
            conn = {
                "name": name,
                "type": _val(b, "type") or "http",
                "base_url": _val(b, "baseUrl"),
                "timeout_ms": _parse_duration_ms(
                    _val(b, "timeout")) if _val(b, "timeout") else 30000,
            }
            # Fetch headers
            header_query = f"""
            PREFIX ext-conn: <{EXT_CONN}>
            SELECT ?headerName ?headerValue
            WHERE {{
                <{b['conn']['value']}> ext-conn:hasHeader ?h .
                ?h ext-conn:headerName ?headerName .
                ?h ext-conn:headerValue ?headerValue .
            }}
            """
            header_results = self.jena.sparql_query(header_query)
            headers = {}
            for hb in header_results.get("results", {}).get("bindings", []):
                headers[_val(hb, "headerName")] = _val(hb, "headerValue")
            if headers:
                conn["headers"] = headers
            connectors.append(conn)
        return connectors

    # --- State table index helpers ---

    def _build_label_index(self):
        """Build an index from (participant, label) to state IDs."""
        participants = self.state_table.get("participants", {})
        for part_name, part_data in participants.items():
            states = part_data.get("states", {})
            for state_id_str, state_desc in states.items():
                state_id = int(state_id_str)
                transitions = state_desc.get("transitions", {})
                for label in transitions:
                    self._label_to_state[(part_name, label)] = state_id

    def _resolve_recv_state_after_send(
        self, participant: Optional[str], send_label: Optional[str]
    ) -> Optional[int]:
        """Find the RECV state that a participant enters after sending a label."""
        if not participant or not send_label:
            return None
        participants = self.state_table.get("participants", {})
        part_data = participants.get(participant, {})
        states = part_data.get("states", {})
        for state_id_str, state_desc in states.items():
            transitions = state_desc.get("transitions", {})
            if send_label in transitions:
                return transitions[send_label]
        return None

    def _resolve_label_target(
        self, participant: Optional[str], label: Optional[str]
    ) -> Optional[int]:
        """Find the state ID that a label transitions to."""
        if not label:
            return None
        # Search all participants if participant is None
        participants = self.state_table.get("participants", {})
        search_parts = ([participant] if participant
                        else list(participants.keys()))
        for part_name in search_parts:
            part_data = participants.get(part_name, {})
            states = part_data.get("states", {})
            for state_id_str, state_desc in states.items():
                transitions = state_desc.get("transitions", {})
                if label in transitions:
                    return transitions[label]
        return None

    def _resolve_send_state(
        self, participant: Optional[str], label: Optional[str]
    ) -> Optional[int]:
        """Find the state ID from which a label can be sent."""
        if not label:
            return None
        participants = self.state_table.get("participants", {})
        search_parts = ([participant] if participant
                        else list(participants.keys()))
        for part_name in search_parts:
            part_data = participants.get(part_name, {})
            states = part_data.get("states", {})
            for state_id_str, state_desc in states.items():
                if state_desc.get("type") == "send":
                    transitions = state_desc.get("transitions", {})
                    if label in transitions:
                        return int(state_id_str)
        return None


# --- Helpers ---

def _val(binding: dict, key: str) -> Optional[str]:
    """Extract a value from a SPARQL binding."""
    entry = binding.get(key)
    if entry:
        return entry.get("value")
    return None


def _parse_duration_ms(duration_str: Optional[str]) -> Optional[int]:
    """Parse an ISO 8601 duration to milliseconds."""
    if not duration_str:
        return None
    try:
        delta = isodate.parse_duration(duration_str)
        return int(delta.total_seconds() * 1000)
    except Exception:
        # Try simple regex for common cases like "PT72H"
        m = re.match(r"PT?(\d+)([DHMS])", duration_str)
        if m:
            value = int(m.group(1))
            unit = m.group(2)
            multipliers = {"D": 86400000, "H": 3600000,
                           "M": 60000, "S": 1000}
            return value * multipliers.get(unit, 1000)
        return None