"""Tests for the Configuration Studio's vocabulary, quantification and eligibility checks
(ADR-A136, addendum of 2026-10-27), through the worker, against an in-memory store."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef

from lattice_workers.config_studio_jobs import CST, SH
from test_config_studio_worker import CATALOGUE, artefacts, results, run

VOCABULARY = CATALOGUE.module("vocabulary").directory("examples")
QUANTIFICATION = CATALOGUE.module("quantification").directory("examples")
ELIGIBILITY = CATALOGUE.module("eligibility").directory("examples")
VEX = Namespace("https://example.org/lattice/vocabulary/examples#")
EEX = Namespace("https://example.org/lattice/eligibility/")


def rows(g: Graph, job: URIRef, predicate: URIRef) -> list[dict]:
    """Each result node as {local predicate: local value or set of values}."""
    out = []
    for node in g.objects(job, predicate):
        row: dict = {}
        for p, o in g.predicate_objects(node):
            key = str(p).rsplit("#", 1)[-1]
            value = str(o).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            row[key] = (row[key] | {value}) if isinstance(row.get(key), set) else ({row[key], value} if key in row else value)
        out.append(row)
    return out


def contexts(row: dict) -> frozenset:
    value = row.get("context", set())
    return frozenset(value if isinstance(value, set) else {value})


def test_resolution_table_covers_every_segment_and_scope_combination():
    g, job = run("validate", "vocabulary", VOCABULARY / "conjunctive-scopes.ttl")
    assert g.value(job, CST.conforms) == Literal(True)
    table = rows(g, job, CST.resolution)
    assert len(table) == 2 * 4  # before and after 2026-01-01, by the four subsets of two scopes
    after = {contexts(r): r for r in table if "validFrom" in r}
    assert after[frozenset({"cnj-region-north", "cnj-tier-gold"})]["scheme"] == "cnj-scheme-region-tier"
    assert after[frozenset({"cnj-region-north"})]["binding"] == "cnj-binding-region"
    assert after[frozenset()]["outcome"] == "Fallback"
    assert all(r["outcome"] == "Fallback" for r in table if "validTo" in r)


def test_a_conflict_is_a_row_naming_the_tied_bindings_and_a_shacl_violation():
    g, job = run("validate", "vocabulary", VOCABULARY / "equal-specificity-conflict.ttl")
    assert g.value(job, CST.conforms) == Literal(False)
    assert results(g, job, SH.Violation)
    conflicts = [r for r in rows(g, job, CST.resolution) if r["outcome"] == "Conflict"]
    assert conflicts and all(isinstance(r["tied"], set) and len(r["tied"]) == 2 for r in conflicts)


def test_a_handover_resolves_to_each_edition_in_its_own_segment():
    g, job = run("validate", "vocabulary", VOCABULARY / "temporal-handover.ttl")
    by_segment = {(r.get("validFrom"), r.get("validTo")): r for r in rows(g, job, CST.resolution)}
    assert [r.get("scheme", r["outcome"]) for _, r in sorted(by_segment.items(), key=lambda kv: str(kv[0]))] == [
        "handover-scheme-v1", "handover-scheme-v2", "Unresolved",
    ]


def test_quantification_examples_conform():
    for name in ("additivity.ttl", "context-anchor.ttl"):
        g, job = run("validate", "quantification", QUANTIFICATION / name)
        assert g.value(job, CST.conforms) == Literal(True), name


def test_a_hierarchical_condition_expands_over_its_scheme():
    g, job = run("validate", "eligibility", ELIGIBILITY / "hierarchical-match.ttl")
    expansion = {r["concept"]: r["decision"] for r in rows(g, job, CST.expansion)}
    assert expansion == {"peril-root": "Denied", "fire": "Permitted", "industrial-fire": "Permitted"}
    (test,) = rows(g, job, CST.testResult)
    assert test["question"] == "subject-question" and test["decision"] == "Permitted"


def test_a_question_decided_against_its_expectation(tmp_path: Path):
    data = (ELIGIBILITY / "hierarchical-match.ttl").read_text(encoding="utf-8")
    cst = "<https://www.nebularis.org/neuro-semantic/lattice/poc/config-studio#expectedDecision>"
    elg = "<https://www.nebularis.org/neuro-semantic/lattice/eligibility#"
    config = tmp_path / "expectations.ttl"
    config.write_text(
        data
        + f"\nex:subject-question {cst} {elg}Permitted> .\n"
        + f"ex:other-question a {elg}Question> ; {elg}forCondition> ex:hierarchical-condition ; {elg}candidateConcept> ex:peril-root ; {cst} {elg}Permitted> .\n",
        encoding="utf-8",
    )
    g, job = run("validate", "eligibility", config)
    passed = {r["question"]: r["passed"] for r in rows(g, job, CST.testResult)}
    assert passed == {"subject-question": "true", "other-question": "false"}
    (failure,) = results(g, job, SH.Violation)
    assert str(g.value(failure, CST.code)) == "TestFailed"
    assert g.value(failure, SH.focusNode) == EEX["other-question"]
    assert g.value(job, CST.conforms) == Literal(False)


def test_an_interval_question_is_decided_by_the_compiled_query():
    g, job = run("validate", "eligibility", ELIGIBILITY / "interval-containment.ttl")
    (test,) = rows(g, job, CST.testResult)
    assert (test["question"], test["decision"]) == ("question-1", "Permitted")


def test_a_condition_the_compiler_refuses_is_a_violation(tmp_path: Path):
    config = tmp_path / "refused.ttl"
    config.write_text(
        "@prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .\n"
        "<https://example.org/c> a elg:Condition ; elg:matchStrategy elg:HierarchicalMatch ;"
        " elg:wildcardSemantics elg:NoWildcard ; elg:requiredConcept <https://example.org/x> .\n",
        encoding="utf-8",
    )
    g, job = run("validate", "eligibility", config)
    assert g.value(job, CST.conforms) == Literal(False)
    codes = {str(g.value(r, CST.code)) for r in results(g, job, SH.Violation)}
    assert "IRCompileError" in codes


def test_a_condition_on_bound_subjects_is_marked_as_not_tested():
    g, job = run("validate", "eligibility", ELIGIBILITY / "evidence-binding.ttl")
    assert {str(g.value(r, CST.code)) for r in results(g, job, SH.Info)} == {"EvidenceBindingNotTested"}


def test_an_eligibility_compile_gives_a_query_and_shapes_per_condition_and_profile():
    g, job = run("compile", "eligibility", ELIGIBILITY / "hierarchical-match.ttl")
    assert g.value(job, CST.conforms) == Literal(True)
    files = artefacts(g, job)
    assert files["hierarchical-condition/decision.rq"][0] == "application/sparql-query"
    assert "SELECT" in files["hierarchical-condition/decision.rq"][1]
    assert "hierarchical-profile/shapes.ttl" in files


def test_vocabulary_has_nothing_to_compile():
    g, job = run("compile", "vocabulary", VOCABULARY / "temporal-handover.ttl")
    assert g.value(job, CST.status) == CST.Failed
    assert "nothing to compile" in str(g.value(job, CST.failureMessage))


def test_a_missing_baseline_reads_as_empty():
    from test_config_studio_worker import FakeStore, submit
    from lattice_workers.config_studio_worker import ConfigStudioWorker
    from test_config_studio_worker import ROOT, _clock

    store = FakeStore()
    iri = submit(store, "validate", "vocabulary", VOCABULARY / "temporal-handover.ttl")
    del store.graphs["urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:baseline:1"]
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    assert store.graphs[iri].value(URIRef(iri), CST.status) == CST.Succeeded
