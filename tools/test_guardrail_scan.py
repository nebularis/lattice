# SPDX-License-Identifier: MPL-2.0
"""The guardrail scan finds what it reports on, and leaves time taken as an input alone (TD-85)."""

from __future__ import annotations

from guardrail_scan import scan


def test_a_string_joined_into_sparql_is_reported():
    text = 'q = "SELECT ?s WHERE { ?s ?p <" + iri + "> }"\nq = f"ASK {{ <{iri}> ?p ?o }}"\nq = "SELECT ?s WHERE { ?s ?p ?o }"\n'
    assert scan(text)[0] == [1, 2]


def test_a_read_of_the_wall_clock_is_reported_and_an_injected_clock_is_not():
    text = "Instant.now()\nInstant.now(clock)\ndatetime.now(timezone.utc)\nDate.now()\nnew Date(value)\n"
    assert scan(text)[1] == [1, 3, 4]
