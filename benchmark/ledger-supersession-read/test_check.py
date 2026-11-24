# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The check's own tests (ADR-A124): the generator holds the arithmetic, the model agrees with a plain recomputation, every variant reads the model's values, a wrong value or count
fails the check, and time does not."""

from __future__ import annotations

import itertools

import pytest

import check

SITES, EVENTS = 12, 90


def build(changes: int, events: int = EVENTS):
    accounts = check.build_accounts(SITES)
    m = check.build_model(events, changes, accounts)
    common = check.common_triples(m)
    return m, common, {v: [check.change_triples(m, v, j) for j in range(1, changes + 1)] for v in check.VARIANTS}


def test_ss1_the_tree_has_the_accounts_and_the_changes_the_arithmetic_gives():
    assert len(check.build_accounts(1000)) == 1014 and check.accounts_reached(1000) == 1013
    assert check.change_ends(100, 3) == [25, 50, 75] and check.change_ends(100, 0) == []
    assert [check.expected_record_triples(v, 1000) for v in check.VARIANTS] == [5065, 6078, 70, 18]
    assert check.config_per_change() == 159


@pytest.mark.parametrize("changes", [0, 1, 4])
def test_ss2_each_variants_triples_follow_the_arithmetic(changes):
    m, common, chunks = build(changes)
    for variant in check.VARIANTS:
        written = sum(len(c) + len(r) for c, r in chunks[variant])
        assert len(common) + written == check.expected_stored(variant, EVENTS, changes, SITES)
        assert len(set(common)) == len(common)
        for config, records in chunks[variant]:
            assert len(records) == check.expected_record_triples(variant, SITES)
            assert len(config) + len(records) == check.expected_change_triples(variant, SITES)
    assert len({tuple(len(c) for c, _ in chunks[v]) for v in check.VARIANTS}) == 1  # the configuration and the pass are the same under every variant


def test_ss3_the_model_agrees_with_a_plain_recomputation():
    m, _, _ = build(3)
    for index in check.leaves_of(m.accounts)[::3]:
        a = m.accounts[index]
        for revision in range(0, m.now + 1, 7):
            signed = sum(-amt if debit else amt for e, (leaf, debit, amt) in enumerate(m.stream, start=1) if leaf == index and m.event_revs[e - 1] <= revision)
            raised = sum(1 for r in m.change_revs if r <= revision) * check.STEP if a.definition != "cap" else 0
            assert m.balance(index, revision) == check.BASE[a.definition] + raised + signed
    assert m.change_revs == [e + j for j, e in enumerate(m.ends, start=1)]
    assert m.event_revs[-1] == EVENTS + 3


@pytest.mark.parametrize("variant", check.VARIANTS)
@pytest.mark.parametrize("changes", [0, 2])
def test_ss4_each_variant_reads_the_models_values_at_every_sampled_point(variant, changes):
    m, common, chunks = build(changes)
    result = check.run_config("oxigraph", variant, m, common, chunks[variant], 1)
    assert set(result.timings) == set(check.READS) and all(t["n"] > 0 for t in result.timings.values())
    assert (result.write_ms is None) == (changes == 0)


@pytest.mark.parametrize("changes", [1, 2])
def test_ss4b_a_read_as_of_the_revision_of_a_change_is_sampled(changes):
    m, *_ = build(changes)
    assert set(m.change_revs) <= set(check.read_points(m))


@pytest.mark.parametrize("variant", check.VARIANTS)
def test_ss4c_every_version_and_account_a_triple_names_is_written(variant):
    m, common, chunks = build(3)
    triples = common + [t for config, records in chunks[variant] for t in config + records]
    typed = {s for s, p, o in triples if p == check.RDF_TYPE}
    named = {o[1] for _, p, o in triples if p in {check.LDG + "partOf", check.LDG + "ofDefinition", check.LDG + "partOfAccount", check.FND + "supersededBy", check.B + "supersedingVersion", check.LDG + "supersedingVersion"}}
    assert named <= typed, sorted(named - typed)[:3]


def test_ss5_the_sample_holds_a_site_with_no_posting_and_one_not_posted_since_the_last_change():
    m = check.build_model(300, 2, check.build_accounts(400))
    picked = [i for i in check.sample(m) if m.accounts[i].key]
    last = m.change_revs[-1]
    assert any(i not in m.revs for i in picked)
    assert any(i in m.revs and m.revs[i][-1] <= last for i in picked)
    assert any(i in m.revs and m.revs[i][-1] > last for i in picked)


@pytest.mark.parametrize("variant", ["per-account", "per-pass"])
def test_ss6_a_value_that_is_off_by_one_fails_the_check_and_names_its_variant_and_account(monkeypatch, variant):
    real = check.stated_in_force
    monkeypatch.setattr(check, "stated_in_force", lambda *a: real(*a) + 1)
    m, common, chunks = build(2)
    with pytest.raises(check.WrongResult, match=rf"{variant} on oxigraph: .* reads .*, the model gives"):
        check.run_config("oxigraph", variant, m, common, chunks[variant], 1)


def test_ss7_a_stored_count_that_is_not_the_arithmetic_fails_the_check(monkeypatch):
    monkeypatch.setattr(check, "expected_stored", lambda *a, **k: 0)
    m, common, chunks = build(1)
    with pytest.raises(check.WrongResult, match="stored"):
        check.run_config("oxigraph", "per-pass", m, common, chunks["per-pass"], 1)


def test_ss8_a_change_that_writes_a_record_too_many_fails_the_check():
    m, common, chunks = build(1)
    config, records = chunks["per-version"][0]
    with pytest.raises(check.WrongResult, match="a change wrote"):
        check.run_config("oxigraph", "per-version", m, common, [(config, records + [("urn:x", "urn:y", ("i", "urn:z"))])], 1)


def test_ss9_time_does_not_fail_the_check(monkeypatch):
    ticks = itertools.count(0, 1000)
    monkeypatch.setattr(check.time, "perf_counter", lambda: next(ticks))
    m, common, chunks = build(1)
    result = check.run_config("oxigraph", "per-pass", m, common, chunks["per-pass"], 1)
    assert result.timings["V"]["median_ms"] > 1000


# ---- the PostgreSQL arm. The tests that need a server use the fixture's postgres_server, so they skip, naming the package, where it is absent ----------------------------


@pytest.mark.parametrize("variant", check.LAYER_VARIANTS)
@pytest.mark.parametrize("changes", [0, 4])
def test_ss10_the_decode_places_every_triple_in_the_layers_terms_as_one_fact(variant, changes):
    m, common, chunks = build(changes)
    triples = check.as_layer_terms(common + [t for config, records in chunks[variant] for t in config + records])
    assert not any(check.B in p or (o[0] == "i" and check.B in o[1]) for _, p, o in triples)
    rows = check.decode(triples)
    links = {link.name for link in check.LINKS}
    facts = sum(len(rows[name]) for name in links)
    facts += sum(1 + sum(cell is not None for cell in row[1:]) for t in check.TABLES for row in rows[t.name])
    assert facts == len(triples) == check.expected_stored(variant, EVENTS, changes, SITES)
    assert len(rows["supersession"]) == changes * (1 if variant == "per-pass" else check.REACHED_DEFS)
    assert len(rows["supersession_version"]) == changes * check.REACHED_DEFS


def test_ss11_the_decode_refuses_what_the_layout_does_not_place():
    m, common, _ = build(0)
    with pytest.raises(check.WrongResult, match="the layout places"):
        check.decode([("urn:x", check.LDG + "onAccount", ("i", "urn:y"))])
    with pytest.raises(check.WrongResult, match="has no column"):
        check.decode([("urn:x", check.RDF_TYPE, ("i", check.LDG + "Pass")), ("urn:x", check.B + "account", ("i", "urn:y"))])
    with pytest.raises(check.WrongResult, match="twice"):
        check.decode([("urn:x", check.RDF_TYPE, ("i", check.LDG + "Pass")), ("urn:x", check.LDG + "passRevision", ("n", "1")), ("urn:x", check.LDG + "passRevision", ("n", "2"))])
    with pytest.raises(check.WrongResult, match="as a s term"):
        check.decode([("urn:x", check.RDF_TYPE, ("i", check.LDG + "Pass")), ("urn:x", check.LDG + "passRevision", ("s", "1"))])
    with pytest.raises(check.WrongResult, match="has no column"):
        check.decode(check.as_layer_terms(common + build(1)[2]["per-account"][0][1]))  # a record on an account is a form the layer does not have


def test_ss12_postgresql_runs_the_forms_the_layer_built_and_no_other():
    assert check.variants_for("postgresql") == ("per-version", "per-pass") == check.LAYER_VARIANTS
    assert all(check.variants_for(e) == check.VARIANTS for e in ("oxigraph", "jena", "rdflib"))


@pytest.mark.parametrize("variant", check.LAYER_VARIANTS)
@pytest.mark.parametrize("changes", [0, 2])
def test_ss13_each_layer_variant_reads_the_models_values_on_postgresql(postgres_server, monkeypatch, variant, changes):
    monkeypatch.setattr(check, "POSTGRES", postgres_server)
    m, common, chunks = build(changes)
    result = check.run_config("postgresql", variant, m, common, chunks[variant], 1)
    assert result.stored == check.expected_stored(variant, EVENTS, changes, SITES)
    assert set(result.timings) == set(check.READS) and all(t["n"] > 0 for t in result.timings.values())
    assert (result.write_ms is None) == (result.decode_ms is None) == (changes == 0)
    with postgres_server.connect() as admin:
        assert admin.execute("SELECT count(*) FROM pg_database WHERE datname LIKE 'test_%'").fetchone() == (0,)  # each run drops its database


@pytest.mark.parametrize("read", ["stated_in_force", "balance_at", "ancestor_balance"])
def test_ss14_a_value_that_is_off_by_one_on_postgresql_fails_the_check(postgres_server, monkeypatch, read):
    monkeypatch.setattr(check, "POSTGRES", postgres_server)
    real = getattr(check.PostgresBackend, read)
    monkeypatch.setattr(check.PostgresBackend, read, lambda self, *a: real(self, *a) + 1)
    m, common, chunks = build(2)
    with pytest.raises(check.WrongResult, match=r"per-pass on postgresql: .* reads .*, the model gives"):
        check.run_config("postgresql", "per-pass", m, common, chunks["per-pass"], 1)


def test_ss15_a_bulk_read_that_is_off_for_one_account_on_postgresql_fails_the_check(postgres_server, monkeypatch):
    monkeypatch.setattr(check, "POSTGRES", postgres_server)
    real = check.PostgresBackend.bulk_in_force
    monkeypatch.setattr(check.PostgresBackend, "bulk_in_force", lambda self, revision: {a: v + a.endswith("site0003") for a, v in real(self, revision).items()})
    m, common, chunks = build(2)
    with pytest.raises(check.WrongResult, match=r"per-version on postgresql: B of .*site0003 reads"):
        check.run_config("postgresql", "per-version", m, common, chunks["per-version"], 1)


def test_ss16_a_fact_the_write_loses_on_postgresql_fails_the_stored_count(postgres_server, monkeypatch):
    monkeypatch.setattr(check, "POSTGRES", postgres_server)
    real = check.decode

    def losing(triples):
        rows = real(triples)
        rows["supersession_version"] = rows["supersession_version"][:-1]
        return rows

    monkeypatch.setattr(check, "decode", losing)
    m, common, chunks = build(1)
    with pytest.raises(check.WrongResult, match="per-pass on postgresql, 90 events, 1 changes: stored"):
        check.run_config("postgresql", "per-pass", m, common, chunks["per-pass"], 1)
