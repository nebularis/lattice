# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H1.2: witness coverage for every refusal, warning, shape and audit
(formal-methods track H). Validation Pack: docs/developer/validation/FMH-H1-2.md.
Test IDs are H1.2-Tn.
"""

from __future__ import annotations

import shutil
import textwrap

import pytest
from rdflib import Graph, URIRef

from persistence import witness
from persistence.cli import main
from persistence.witness import (
    AUDIT,
    REFUSAL,
    SHAPE,
    WARNING,
    AuditWitness,
    Rule,
    audit_witnesses,
    build_report,
    check_witness_coverage,
    enumerate_rules,
    observe_audits,
    observe_compile,
    observe_shapes,
    run_audit,
    source_rules,
)

from conftest import EXAMPLES_DIR

AUDITS = sorted(a.removeprefix("audit:") for a in map(str, (r for r in enumerate_rules() if r.family == AUDIT)))


def test_h1_2_t1_the_inventory_lists_every_family():
    rules = enumerate_rules()
    assert Rule(REFUSAL, "LagWindowMissing") in rules  # a CrossAxisViolation kind
    assert Rule(REFUSAL, "ProfileAmbiguityError") in rules  # a refusal keyed by class name
    assert Rule(REFUSAL, "MintedIriTemplateRequired") in rules  # a recipe fail() kind
    assert Rule(WARNING, "WeakEtagCas") in rules
    assert Rule(WARNING, "RowLevelGuardOnly") in rules  # a Diagnostic(kind=...)
    assert Rule(SHAPE, "LagWindowRequiredShape") in rules
    assert {r.name for r in rules if r.family == AUDIT} == set(AUDITS)
    assert len(AUDITS) == 5


def test_h1_2_t2_a_new_rule_in_the_source_joins_the_inventory(tmp_path):
    (tmp_path / "rules.py").write_text(
        textwrap.dedent(
            """
            def f(target):
                raise CrossAxisViolation("BrandNewRefusal", target, "x")

            def g(target):
                return _warning("BrandNewWarning", target, "x")

            def h(shape):
                raise BoundaryConflict("x")
            """
        )
    )
    assert source_rules(tmp_path) == {
        Rule(REFUSAL, "BrandNewRefusal"),
        Rule(WARNING, "BrandNewWarning"),
        Rule(REFUSAL, "BoundaryConflict"),
    }


def test_h1_2_t3_an_unwitnessed_unlisted_rule_fails_the_report():
    vacuous = Rule(REFUSAL, "NeverRaised")
    report = build_report({vacuous}, {}, {})
    assert report.uncovered == [vacuous]
    assert not report.ok
    assert "UNWITNESSED refusal:NeverRaised" in report.lines()


def test_h1_2_t4_a_seeded_vacuous_rule_in_real_source_is_reported(tmp_path):
    """The plan's seeded check: add a rule nothing can trigger to the real
    inventory and confirm the real observation leaves it uncovered."""
    (tmp_path / "vacuous.py").write_text('raise CrossAxisViolation("CanNeverFire", t, "x")\n')
    rules = enumerate_rules() | source_rules(tmp_path)
    report = check_witness_coverage()
    seeded = build_report(rules, {**report.covered}, report.listed_gaps)
    assert Rule(REFUSAL, "CanNeverFire") in seeded.uncovered


def test_h1_2_t5_a_listed_gap_with_a_witness_is_stale():
    rule = Rule(WARNING, "WeakEtagCas")
    report = build_report({rule}, {rule: {"f.ttl"}}, {rule: "not yet"})
    assert report.stale_gaps == [rule] and not report.ok


def test_h1_2_t6_a_listed_gap_that_is_not_a_rule_is_unknown():
    ghost = Rule(SHAPE, "NoSuchShape")
    report = build_report(set(), {}, {ghost: "typo"})
    assert report.unknown_gaps == [ghost] and not report.ok


def test_h1_2_t7_a_listed_gap_is_reported_but_does_not_fail():
    rule = Rule(SHAPE, "SomeShape")
    report = build_report({rule}, {}, {rule: "H1.2c"})
    assert report.ok and report.listed_gaps == {rule: "H1.2c"}


def test_h1_2_t8_compiling_a_refusal_example_witnesses_its_rule():
    observed = observe_compile([EXAMPLES_DIR / "invalid-lagwindow-missing.ttl", EXAMPLES_DIR / "warning-epoch-unsafe-restore.ttl"])
    assert observed[Rule(REFUSAL, "LagWindowMissing")] == {"invalid-lagwindow-missing.ttl"}
    assert Rule(WARNING, "StoreLocalEpoch") in observed


def test_h1_2_t9_validating_an_example_witnesses_the_shape_that_fires():
    observed = observe_shapes([EXAMPLES_DIR / "invalid-lagwindow-missing.ttl"])
    assert Rule(SHAPE, "LagWindowRequiredShape") in observed


def test_h1_2_t10_a_property_shape_result_is_credited_to_its_named_parent():
    g = Graph()
    g.parse(
        data="""
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <https://example.org/s#> .
        ex:Parent a sh:NodeShape ; sh:property [ sh:path ex:p ; sh:minCount 1 ] .
        """,
        format="turtle",
    )
    (property_shape,) = list(g.objects(URIRef("https://example.org/s#Parent"), witness.SH.property))
    assert witness._owning_shape(g, property_shape) == URIRef("https://example.org/s#Parent")


@pytest.mark.parametrize("audit", AUDITS)
def test_h1_2_t11_each_audit_fires_on_its_violation_and_not_on_its_clean_dataset(audit):
    by_kind = {w.kind: w for w in audit_witnesses() if w.audit == audit}
    assert set(by_kind) == {"violation", "clean"}
    assert run_audit(by_kind["violation"]) >= 1
    assert run_audit(by_kind["clean"]) == 0


def test_h1_2_t12_an_audit_with_only_a_violation_witness_is_not_witnessed(tmp_path):
    (tmp_path / "audits").mkdir()
    shutil.copy(
        witness.WITNESS_DIR / "audits" / "fork-detection-audit.violation.trig",
        tmp_path / "audits" / "fork-detection-audit.violation.trig",
    )
    observed, problems = observe_audits(audit_witnesses(tmp_path))
    assert Rule(AUDIT, "fork-detection-audit") not in observed
    assert any("both a violating and a clean" in p for p in problems)


def test_h1_2_t13_an_audit_that_fires_on_its_clean_dataset_is_a_problem(tmp_path):
    """A query that returns rows for good data detects nothing."""
    (tmp_path / "audits").mkdir()
    violation = (witness.WITNESS_DIR / "audits" / "fork-detection-audit.violation.trig").read_text()
    (tmp_path / "audits" / "fork-detection-audit.violation.trig").write_text(violation)
    (tmp_path / "audits" / "fork-detection-audit.clean.trig").write_text(violation)
    observed, problems = observe_audits(audit_witnesses(tmp_path))
    assert Rule(AUDIT, "fork-detection-audit") not in observed
    assert any("the clean dataset returns rows" in p for p in problems)


def test_h1_2_t14_a_missing_request_time_binding_is_refused():
    base = next(w for w in audit_witnesses() if w.audit == "gap-scan-audit" and w.kind == "violation")
    unbound = AuditWitness(base.audit, base.kind, base.path, {}, base.dataset)
    with pytest.raises(ValueError, match="logGraphs"):
        run_audit(unbound)


def test_h1_2_t15_the_real_corpus_has_no_unlisted_gap_and_no_stale_gap():
    report = check_witness_coverage()
    assert report.ok, "\n".join(report.lines())
    assert report.uncovered == [] and report.stale_gaps == [] and report.unknown_gaps == []
    assert {r for r in report.covered if r.family == AUDIT} == {Rule(AUDIT, a) for a in AUDITS}


def test_h1_2_t16_cli_exits_zero_on_the_real_corpus_and_one_on_an_unlisted_gap(monkeypatch, capsys):
    assert main(["witness"]) == 0
    assert "witness coverage:" in capsys.readouterr().out
    monkeypatch.setattr(witness, "read_known_gaps", lambda path=witness.KNOWN_GAPS: {})
    assert main(["witness"]) == 1
    assert "UNWITNESSED" in capsys.readouterr().out
