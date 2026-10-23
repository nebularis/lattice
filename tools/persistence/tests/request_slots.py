# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Test-side stand-in for whatever fills an instantiated operation's
request-time slots, the plain-text ``{{{name}}}`` markers (H2.9-Q1).
Substitutes the text, as any caller in any language would."""

from __future__ import annotations

from persistence.ir_render import fill_slots

PAYLOAD_SUBSTITUTE = "<urn:example:s> <urn:example:p> <urn:example:o> ."
LOG_GRAPHS_SUBSTITUTE = "<urn:g:txlog/2026-08> <urn:g:txlog/2026-09>"
EVENT_ROWS_SUBSTITUTE = (
    '(<urn:example:event> <urn:example:Type> "1"^^<http://www.w3.org/2001/XMLSchema#long> '
    '"2026-10-12T10:00:00Z"^^<http://www.w3.org/2001/XMLSchema#dateTime>)'
)
EVENT_TRIPLES_SUBSTITUTE = '<urn:example:event> <urn:example:p> "v" .'
ASSERT_TRIPLES_SUBSTITUTE = '<urn:example:s> <urn:example:p> <urn:example:added> .'
RETRACT_TRIPLES_SUBSTITUTE = '<urn:example:s> <urn:example:p> <urn:example:removed> .'
ADDED_MEMBERS_SUBSTITUTE = '<urn:example:s> <urn:example:addsMember> <urn:example:added> .'
DROPPED_MEMBERS_SUBSTITUTE = '<urn:example:s> <urn:example:dropsMember> <urn:example:removed> .'


def fill_request_slots(text: str) -> str:
    return fill_slots(
        text, {
            "payloadTriples": PAYLOAD_SUBSTITUTE, "logGraphs": LOG_GRAPHS_SUBSTITUTE,
            "eventRows": EVENT_ROWS_SUBSTITUTE, "eventTriples": EVENT_TRIPLES_SUBSTITUTE,
            "assertTriples": ASSERT_TRIPLES_SUBSTITUTE, "retractTriples": RETRACT_TRIPLES_SUBSTITUTE,
            "addedMembers": ADDED_MEMBERS_SUBSTITUTE, "droppedMembers": DROPPED_MEMBERS_SUBSTITUTE,
        }
    )
