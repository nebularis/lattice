# SPDX-License-Identifier: MPL-2.0
"""SHACL conformance of the fixtures under ontology/vocabulary/examples/
against ontology/vocabulary/shapes/{structural,constraints}.ttl.

Covers the SHACL-checkable validation-pack cases: VTB-01, 02, 03, 04, 07
(the context-independent equal-scope-set form), 09, 13. See
docs/developer/validation/vocabulary-temporal-binding.md.
"""

from __future__ import annotations

import pyshacl

POSITIVE_FIXTURES = [
    "unscoped-time-bounded.ttl",
    "conjunctive-scopes.ttl",
    "alternative-regional-bindings.ttl",
    "temporal-handover.ttl",
    "historical-provenance.ttl",
    "consumer-boundary.ttl",
]

NEGATIVE_FIXTURES = [
    "missing-for-contract.ttl",
    "missing-binds-scheme.ttl",
    "invalid-temporal-interval.ttl",
    "equal-specificity-conflict.ttl",
    "fallback-disagreement.ttl",
    "historical-provenance-outside-time.ttl",
]

# Negative fixtures whose violating shape carries an explicit sh:message
# (the SPARQL-based shapes in constraints.ttl); asserted on top of
# "does not conform" so a fixture cannot pass by tripping the wrong shape.
NEGATIVE_FIXTURE_MESSAGES = {
    "invalid-temporal-interval.ttl": "must not end before it begins",
    "equal-specificity-conflict.ttl": "neither can ever win by strict-superset precedence",
    "fallback-disagreement.ttl": "must name the same scheme as the contract's boundScheme fallback",
    "historical-provenance-outside-time.ttl": "must have been valid at the record's own resolution time",
}


def _validate(data_graph, shapes_graph):
    return pyshacl.validate(
        data_graph=data_graph,
        shacl_graph=shapes_graph,
        advanced=True,
        inference="none",
        allow_warnings=True,
    )


def test_positive_fixtures_conform(shapes_graph, example):
    for fixture in POSITIVE_FIXTURES:
        data = example(fixture)
        conforms, _, report = _validate(data, shapes_graph)
        assert conforms, f"{fixture} does not conform:\n{report}"


def test_negative_fixtures_do_not_conform(shapes_graph, example):
    for fixture in NEGATIVE_FIXTURES:
        data = example(fixture)
        conforms, _, report = _validate(data, shapes_graph)
        assert not conforms, f"{fixture} conforms but should not have:\n{report}"
        expected_message = NEGATIVE_FIXTURE_MESSAGES.get(fixture)
        if expected_message is not None:
            assert expected_message in report, (
                f"{fixture} did not conform, but not for the expected reason "
                f"('{expected_message}' not found):\n{report}"
            )


def test_fixtures_run_without_engine_errors(shapes_graph, example):
    """A shape the SHACL engine cannot execute also reports as
    'not conform', so a negative fixture could pass for the wrong reason.
    Every fixture, positive or negative, must validate cleanly."""
    for fixture in POSITIVE_FIXTURES + NEGATIVE_FIXTURES:
        data = example(fixture)
        _, _, report = _validate(data, shapes_graph)
        assert "Validation Failure" not in report, f"{fixture}:\n{report}"
