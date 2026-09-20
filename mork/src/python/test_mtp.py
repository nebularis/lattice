from pathlib import Path

from mtp import budget, codebook, doctrine, facts, lock, mutate, partition, render, routing


def test_codebook_adapter_expands_predeclared_prefix():
    assert codebook.expand("mork:DataMapping").endswith("Mork#DataMapping")


def test_budget_rejects_text_over_limit():
    try:
        budget.require_budget("one two", 1, "test")
    except ValueError as error:
        assert "budget exceeded" in str(error)
    else:
        raise AssertionError("budget check did not fail")


def test_lock_drift_is_stable():
    assert lock.drift({"a": "1"}, {"a": "2", "b": "3"}) == ["a", "b"]


def test_term_hash_ignores_nonlogical_annotation(tmp_path: Path):
    path = tmp_path / "ontology.ttl"
    path.write_text("@prefix ex: <https://example.test/> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> . ex:A rdfs:label \"A\" .", encoding="utf-8")
    # The extractor deliberately limits teaching pins to the MORK namespace.
    assert facts.extract(path).terms == ()


def test_wildcard_deferral_owns_initial_axiom_set():
    sample = facts.Facts("sha256:test", (), (facts.Axiom("s", "p", "o", "sha256:axiom"),))
    assert doctrine.check({"anchors": [], "covers": [], "deferrals": ["*"]}, sample) == []


def test_default_partition_assigns_all_terms():
    sample = facts.Facts("sha256:test", (facts.Term("http://www.nebularis.org/ontologies/Mork#DataMapping", (), "sha256:term"),), ())
    assert partition.check({"assignments": {}, "defaultLens": "L-TBX"}, sample) == []


def test_routing_requires_every_lens_to_be_reachable():
    assert routing.check([{"lens": "L-REP"}], {"L-REP", "L-UNC"}) == ["routing.unreachable:L-UNC"]


def test_seed_mutations_have_stable_operator_names():
    assert [item.name for item in mutate.seed_mutations("x cb y df z xr q MU")] == ["drop:df", "drop:xr", "swap:cb->ap", "swap:df->dp", "retype:MU->M", "both:cb+cn"]


def test_manifest_drift_detects_missing_manifest(tmp_path: Path):
    assert render.manifest_drift(tmp_path) == ["output.stale:manifest-missing"]