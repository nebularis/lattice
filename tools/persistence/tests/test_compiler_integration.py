# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""End-to-end: compile -> emit -> instantiate -> parse, for every positive
example fixture, plus the SHACL self-validation of ontology/persistence
against every fixture (sketch §3.9)."""

from __future__ import annotations

from pathlib import Path

import pyshacl
import pytest
from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery, prepareUpdate

from persistence.compiler import compile_to_graph
from persistence.instantiate import instantiate_profile

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_TTL = REPO_ROOT / "ontology" / "persistence" / "spec" / "persistence.ttl"
SHAPES_TTL = REPO_ROOT / "ontology" / "persistence" / "shapes" / "constraints.ttl"
EXAMPLES_DIR = REPO_ROOT / "ontology" / "persistence" / "examples"

PAYLOAD_SUBSTITUTE = "<urn:example:s> <urn:example:p> <urn:example:o> ."

POSITIVE_FIXTURES = [
    ("baseline-single-class.ttl", "https://example.org/lending#LoanApplication"),
    ("namespace-wide.ttl", "https://example.org/lending#CreditDecision"),
    ("value-based-cas.ttl", "https://example.org/lending#Order"),
    ("composite-property-boundary-shacl.ttl", "https://example.org/lending#Order"),
    ("epoch-dataset-level-guard.ttl", "https://example.org/lending#LoanApplication"),
]

NEGATIVE_FIXTURES = [
    "invalid-noboundary-cas.ttl",
    "invalid-compositeboundary-receiptonly.ttl",
    "invalid-metashards-changed-no-ack.ttl",
    "invalid-commitgrain-opseq.ttl",
    "invalid-uniqueness-outside-boundary.ttl",
]

SHACL_NEGATIVE_FIXTURES = ["invalid-compositeboundary-missing-shape.ttl"]

ALL_FIXTURES = [p.name for p in EXAMPLES_DIR.glob("*.ttl")]


@pytest.mark.parametrize("fixture,target_iri", POSITIVE_FIXTURES)
def test_end_to_end_compile_instantiate_parse(fixture, target_iri):
    from rdflib import URIRef

    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / fixture, format="turtle")

    out, compiled = compile_to_graph(g, classes={URIRef(target_iri)})
    assert len(compiled) >= 1

    rendered = instantiate_profile(out)
    assert rendered, f"no operations instantiated for {fixture}"

    for op_name, text in rendered.items():
        testable = text.replace("#PAYLOAD#", PAYLOAD_SUBSTITUTE)
        try:
            if any(k in testable for k in ["INSERT", "DELETE"]):
                prepareUpdate(testable)
            else:
                prepareQuery(testable)
        except Exception as e:  # pragma: no cover - failure path
            pytest.fail(f"{fixture}::{op_name} did not parse: {e}\n{testable}")


@pytest.mark.parametrize("fixture", NEGATIVE_FIXTURES)
def test_negative_fixture_fails_compile(fixture):
    from persistence.compiler import CompileError

    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / fixture, format="turtle")
    with pytest.raises(CompileError):
        compile_to_graph(g)


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_every_fixture_parses_as_turtle(fixture):
    g = Graph()
    g.parse(EXAMPLES_DIR / fixture, format="turtle")


class TestShaclSelfValidation:
    """sketch §3.9: ontology/persistence validates its own instance data."""

    @pytest.fixture(scope="class")
    def shapes(self):
        g = Graph()
        g.parse(SPEC_TTL, format="turtle")
        g.parse(SHAPES_TTL, format="turtle")
        return g

    @pytest.mark.parametrize(
        "fixture",
        [f for f in ALL_FIXTURES if f not in SHACL_NEGATIVE_FIXTURES],
    )
    def test_conforms(self, shapes, fixture):
        data = Graph()
        data.parse(SPEC_TTL, format="turtle")
        data.parse(EXAMPLES_DIR / fixture, format="turtle")
        conforms, _, report = pyshacl.validate(
            data, shacl_graph=shapes, inference="none", advanced=True, allow_warnings=True
        )
        assert conforms, f"{fixture} does not conform:\n{report}"

    @pytest.mark.parametrize("fixture", SHACL_NEGATIVE_FIXTURES)
    def test_does_not_conform(self, shapes, fixture):
        data = Graph()
        data.parse(SPEC_TTL, format="turtle")
        data.parse(EXAMPLES_DIR / fixture, format="turtle")
        conforms, _, _ = pyshacl.validate(
            data, shacl_graph=shapes, inference="none", advanced=True, allow_warnings=True
        )
        assert not conforms

    def test_shared_class_profile_warning_fires(self, shapes):
        data = Graph()
        data.parse(SPEC_TTL, format="turtle")
        data.parse(EXAMPLES_DIR / "warning-shared-class-profile.ttl", format="turtle")
        conforms, _, report = pyshacl.validate(
            data, shacl_graph=shapes, inference="none", advanced=True, allow_warnings=True
        )
        assert conforms  # warnings alone do not fail conformance
        assert "SharedClassProfileWarningShape" in report

    def test_shared_class_profile_warning_does_not_fire_on_baseline(self, shapes):
        data = Graph()
        data.parse(SPEC_TTL, format="turtle")
        data.parse(EXAMPLES_DIR / "baseline-single-class.ttl", format="turtle")
        _, _, report = pyshacl.validate(
            data, shacl_graph=shapes, inference="none", advanced=True, allow_warnings=True
        )
        assert "Results (0)" in report or "SharedClassProfileWarningShape" not in report

    def test_epoch_unsafe_restore_warnings_fire(self, shapes):
        # persistence-compiler-iri-sync Slice 1: SHACL-level defence in
        # depth for the same invariant test_validator.py checks in Python.
        data = Graph()
        data.parse(SPEC_TTL, format="turtle")
        data.parse(EXAMPLES_DIR / "warning-epoch-unsafe-restore.ttl", format="turtle")
        conforms, _, report = pyshacl.validate(
            data, shacl_graph=shapes, inference="none", advanced=True, allow_warnings=True
        )
        assert conforms  # warnings alone do not fail conformance
        assert "RowLevelGuardOnlyWarningShape" in report
        assert "StoreLocalEpochWarningShape" in report

    def test_epoch_dataset_level_guard_has_no_warnings(self, shapes):
        data = Graph()
        data.parse(SPEC_TTL, format="turtle")
        data.parse(EXAMPLES_DIR / "epoch-dataset-level-guard.ttl", format="turtle")
        conforms, _, report = pyshacl.validate(
            data, shacl_graph=shapes, inference="none", advanced=True, allow_warnings=True
        )
        assert conforms
        assert "RowLevelGuardOnlyWarningShape" not in report
        assert "StoreLocalEpochWarningShape" not in report


class TestEpochGuardScopeTemplateSelection:
    """persistence-compiler-iri-sync Slice 1 (2026-09-23): the resolved
    dal:epochGuardScope value must select the matching CAS/tombstone
    template variant, and the added dataset-level guard clause must
    survive instantiate + parse, not just render."""

    def test_dataset_level_guard_selects_dataset_guard_templates(self):
        from rdflib import URIRef

        g = Graph()
        g.parse(SPEC_TTL, format="turtle")
        g.parse(EXAMPLES_DIR / "epoch-dataset-level-guard.ttl", format="turtle")
        target = URIRef("https://example.org/lending#LoanApplication")

        out, compiled = compile_to_graph(g, classes={target})
        assert len(compiled) == 1
        cas_ops = [o for o in compiled[0].operations if o.operation == "cas-replace"]
        assert len(cas_ops) == 1
        assert cas_ops[0].template_id == "cas-replace-named-graph-dataset-guard.mustache"

        rendered = instantiate_profile(out)
        text = rendered["cas-replace"]
        assert "urn:g:dataset" in text
        prepareUpdate(text.replace("#PAYLOAD#", PAYLOAD_SUBSTITUTE))

    def test_baseline_selects_original_named_graph_template(self):
        from rdflib import URIRef

        g = Graph()
        g.parse(SPEC_TTL, format="turtle")
        g.parse(EXAMPLES_DIR / "baseline-single-class.ttl", format="turtle")
        target = URIRef("https://example.org/lending#LoanApplication")

        _, compiled = compile_to_graph(g, classes={target})
        cas_ops = [o for o in compiled[0].operations if o.operation == "cas-replace"]
        assert len(cas_ops) == 1
        assert cas_ops[0].template_id == "cas-replace-named-graph.mustache"
