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
    fired, conforming = observe_shapes([EXAMPLES_DIR / "invalid-lagwindow-missing.ttl", EXAMPLES_DIR / "baseline-single-class.ttl"])
    assert fired[Rule(SHAPE, "LagWindowRequiredShape")] == {"invalid-lagwindow-missing.ttl"}
    # the baseline example has data the shape applies to and accepts
    assert "baseline-single-class.ttl" in conforming[Rule(SHAPE, "ClassScopeShape")]
    assert "invalid-lagwindow-missing.ttl" not in conforming.get(Rule(SHAPE, "LagWindowRequiredShape"), set())


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
    real = witness.enumerate_rules
    monkeypatch.setattr(witness, "enumerate_rules", lambda: real() | {Rule(REFUSAL, "NeverRaised")})
    assert main(["witness"]) == 1
    assert "UNWITNESSED refusal:NeverRaised" in capsys.readouterr().out


# ---- H1.2b: the corrected inventory, the patch format and the drift check -------------------------


def test_h1_2_t17_a_kind_passed_through_a_helper_parameter_is_followed(tmp_path):
    """The recipe builder passes a kind to ``constraint(..., "KeyConstraintRequired")``,
    which hands it on to ``fail``. A literal-only scan missed both."""
    (tmp_path / "helper.py").write_text(
        textwrap.dedent(
            """
            class Builder:
                def fail(self, kind, where, message):
                    raise CrossAxisViolation(kind, where, message)

                def constraint(self, where, node, missing_kind):
                    if node is None:
                        self.fail(missing_kind, where, "required")

                def build(self, where, node):
                    self.constraint(where, node, "FirstKind")
                    self.constraint(where, node, missing_kind="SecondKind")
            """
        )
    )
    rules, problems = witness.scan_source(tmp_path)
    assert rules == {Rule(REFUSAL, "FirstKind"), Rule(REFUSAL, "SecondKind")}
    assert problems == []


def test_h1_2_t18_a_kind_that_cannot_be_determined_is_reported_not_skipped(tmp_path):
    (tmp_path / "opaque.py").write_text(
        textwrap.dedent(
            """
            KINDS = {"a": "X"}

            def f(key, target):
                raise CrossAxisViolation(KINDS[key], target, "x")
            """
        )
    )
    rules, problems = witness.scan_source(tmp_path)
    assert rules == set()
    assert len(problems) == 1 and "opaque.py:5" in problems[0]


def test_h1_2_t19_the_real_source_has_no_undeterminable_kind():
    assert witness.scan_source()[1] == []
    assert Rule(REFUSAL, "KeyConstraintRequired") in enumerate_rules()
    assert Rule(REFUSAL, "ClaimedIdentityWithoutKey") in enumerate_rules()


def test_h1_2_t20_a_patch_fixture_removes_from_its_base_and_adds_its_own(tmp_path):
    fixture = tmp_path / "patch.ttl"
    fixture.write_text(
        "# base: baseline-single-class.ttl\n"
        "# remove: ex:LoanApplicationClass dal:priority\n"
        "@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .\n"
        "@prefix ex: <https://example.org/lending#> .\n"
        "ex:Extra a dal:ClassScope ; dal:targetClass ex:Extra .\n"
    )
    base = witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl")
    patched = witness._load_fixture(fixture)
    ns = "https://example.org/lending#"
    priority = URIRef("https://www.nebularis.org/neuro-semantic/lattice/persistence#priority")
    assert (URIRef(ns + "LoanApplicationClass"), priority, None) in base
    assert (URIRef(ns + "LoanApplicationClass"), priority, None) not in patched
    assert (URIRef(ns + "Extra"), None, None) in patched


def test_h1_2_t21_a_patch_that_removes_nothing_is_refused(tmp_path):
    fixture = tmp_path / "noop.ttl"
    fixture.write_text(
        "# base: baseline-single-class.ttl\n"
        "# remove: ex:NoSuchNode dal:priority\n"
        "@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .\n"
        "@prefix ex: <https://example.org/lending#> .\n"
    )
    with pytest.raises(ValueError, match="matches nothing"):
        witness._load_fixture(fixture)


def test_h1_2_t22_a_witness_that_triggers_a_different_rule_than_its_name_is_a_problem(tmp_path):
    (tmp_path / "refusal-Alpha.ttl").write_text("")
    (tmp_path / "warning-Beta.ttl").write_text("")
    (tmp_path / "_base.ttl").write_text("")  # a shared base is not a witness
    observed = {Rule(REFUSAL, "Alpha"): {"refusal-Alpha.ttl"}, Rule(REFUSAL, "Gamma"): {"warning-Beta.ttl"}}
    problems = witness.named_witness_problems(observed, tmp_path)
    assert len(problems) == 1
    assert "warning-Beta.ttl" in problems[0] and "refusal:Gamma" in problems[0]


def test_h1_2_t23_every_refusal_and_warning_has_a_witness_and_only_shapes_remain():
    report = check_witness_coverage()
    assert report.ok, "\n".join(report.lines())
    assert {r.family for r in report.listed_gaps} <= {SHAPE}
    assert {r.family for r in report.covered} >= {REFUSAL, WARNING, AUDIT}
    assert Rule(WARNING, "MixedReceiptModel") in report.covered  # not reachable from the shipped example
    assert Rule(REFUSAL, "IdentityStrategyUnsupported") in report.covered


# ---- the console colours -------------------------------------------------------------------------

GREEN, RED, RESET = "\033[32m", "\033[31m", "\033[0m"


def _verbose_lines(color: bool) -> list[str]:
    witnessed, gap = Rule(SHAPE, "SomeWitnessedShape"), Rule(SHAPE, "SomeGapShape")
    report = build_report({witnessed, gap}, {witnessed: {"f.ttl"}}, {gap: "not yet"})
    return report.lines(verbose=True, color=color)


def test_h1_2_t24_witnessed_lines_are_green_and_gap_lines_red_when_colour_is_on():
    lines = _verbose_lines(color=True)
    witnessed = [line for line in lines if "WITNESSED" in line]
    gaps = [line for line in lines if "GAP shape:" in line]
    assert len(witnessed) == 1 and witnessed[0].startswith(GREEN) and witnessed[0].endswith(RESET)
    assert len(gaps) == 1 and gaps[0].startswith(RED) and gaps[0].endswith(RESET)
    # the summary and the failure lines are not coloured
    assert not any("\033" in line for line in lines if line.startswith(("witness coverage", "  shape")))


def test_h1_2_t25_without_colour_the_output_has_no_escape_codes():
    assert not any("\033" in line for line in _verbose_lines(color=False))


def test_h1_2_t26_colour_follows_the_terminal_and_the_usual_environment_switches():
    class Tty:
        def isatty(self):
            return True

    class Pipe:
        def isatty(self):
            return False

    assert witness.use_color(Tty(), {"TERM": "xterm-256color"})
    assert not witness.use_color(Pipe(), {"TERM": "xterm-256color"})
    assert not witness.use_color(Tty(), {"TERM": "dumb"})
    assert not witness.use_color(Tty(), {"NO_COLOR": "1"})
    assert witness.use_color(Pipe(), {"FORCE_COLOR": "1"})
    assert not witness.use_color(Pipe(), {"FORCE_COLOR": "0"})
    assert not witness.use_color(Tty(), {"NO_COLOR": "1", "FORCE_COLOR": "1"})


def test_h1_2_t27_cli_colours_only_when_asked(monkeypatch, capsys):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert main(["witness", "--verbose"]) == 0
    assert GREEN in capsys.readouterr().out
    monkeypatch.delenv("FORCE_COLOR")
    assert main(["witness", "--verbose"]) == 0
    assert "\033" not in capsys.readouterr().out


def test_h1_2_t28_the_known_gap_list_is_empty():
    """H1.2c closed the last gap. A new rule must arrive with its witness."""
    assert witness.read_known_gaps() == {}
    report = check_witness_coverage()
    assert report.ok and len(report.covered) == len(enumerate_rules())


def test_h1_2_t29_a_shape_witness_must_fire_the_shape_it_is_named_for(tmp_path):
    (tmp_path / "shape-Alpha.ttl").write_text("")
    observed = {Rule(SHAPE, "Beta"): {"shape-Alpha.ttl"}}
    (problem,) = witness.named_witness_problems(observed, tmp_path)
    assert "shape-Alpha.ttl" in problem and "shape:Beta" in problem


def test_h1_2_t30_a_shape_that_reports_on_every_fixture_has_no_conforming_witness(tmp_path, monkeypatch):
    """A shape that fires everywhere detects nothing, like an audit that always returns rows."""
    shapes = tmp_path / "shapes.ttl"
    shapes.write_text(
        """
        @prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
        @prefix sh:  <http://www.w3.org/ns/shacl#> .
        dal:AlwaysShape a sh:NodeShape ; sh:targetClass dal:ClassScope ;
            sh:property [ sh:path dal:describedBy ; sh:minCount 5 ] .
        """
    )
    monkeypatch.setattr(witness, "SHAPES_TTL", shapes)
    fired, conforming = observe_shapes([EXAMPLES_DIR / "baseline-single-class.ttl"])
    assert Rule(SHAPE, "AlwaysShape") in fired
    assert Rule(SHAPE, "AlwaysShape") not in conforming


def test_h1_2_t31_a_conforming_fixture_exists_for_a_shape_no_shipped_example_exercises():
    _, conforming = observe_shapes([witness.WITNESS_DIR / "ok-ShapeScopeShape.ttl"])
    assert conforming[Rule(SHAPE, "ShapeScopeShape")] == {"ok-ShapeScopeShape.ttl"}
