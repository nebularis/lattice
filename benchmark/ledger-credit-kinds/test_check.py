# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The check's own tests (ADR-A124, PRI-63): it passes on a right history, fails on a wrong balance, on a filter that ignores the kind and on a fold that ignores the ceiling, does not fail on time, and leaves no store open."""

from __future__ import annotations

import itertools
import json
import os

import pytest

import check

SMALL, HIGH, LOW = 400, 0.30, 0.05
BACKENDS = check.available_backends()


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck1_each_fold_reads_the_models_balance_of_every_ancestor_at_every_point(backend):
    m = check.run_backend(backend, SMALL, HIGH)
    postings = check.stream(SMALL, HIGH)
    assert sum(r.reads for r in m.reads.values()) == len(check.FOLDS) * len(check.ANCESTORS) * len(check.read_points(postings[-1].pos))
    assert m.stored_triples == check.expected_stored(postings)


def test_ck2_the_model_tells_the_three_folds_apart_where_it_should():
    postings = check.stream(2000, HIGH)
    point = postings[-1].pos
    model = check.run_model(postings, [point])
    cap = next(i for i, a in enumerate(check.TREE) if a.accepts)
    others = [i for i in check.ANCESTORS if i != cap]
    assert model.balance[("plain", cap, point)] != model.balance[("kind-filtered", cap, point)]
    assert model.rows[("kind-filtered", cap, point)] < model.rows[("plain", cap, point)]
    assert all(model.balance[("plain", i, point)] == model.balance[("kind-filtered", i, point)] for i in others)
    assert any(model.balance[("stepwise", i, point)] != model.balance[("kind-filtered", i, point)] for i in check.ANCESTORS)
    low = check.run_model(check.stream(2000, LOW), [point])
    assert all(low.balance[("stepwise", i, point)] <= check.TREE[i].stated for i in check.ANCESTORS)


def test_ck3_a_corpus_that_cannot_fail_a_fold_is_refused():
    postings = check.stream(SMALL, 0.0)
    model = check.run_model(postings, [postings[-1].pos])
    with pytest.raises(check.WrongResult):
        check.check_discriminates(model, 0.30, postings[-1].pos)


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck4_a_balance_that_is_off_by_one_fails_the_check(monkeypatch, backend):
    real = check.read
    monkeypatch.setattr(check, "read", lambda *a: (lambda b, n: (b + 1, n))(*real(*a)))
    with pytest.raises(check.WrongResult, match="the model gives"):
        check.run_backend(backend, SMALL, HIGH)


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck5_a_filter_that_ignores_the_kind_fails_the_check(monkeypatch, backend):
    monkeypatch.setattr(check, "KIND_FILTER", "")
    with pytest.raises(check.WrongResult, match="kind-filtered"):
        check.run_backend(backend, SMALL, HIGH)


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck6_a_missing_clamp_at_the_drawn_account_fails_the_check(monkeypatch, backend):
    monkeypatch.setattr(check, "clamp_at_drawn", lambda balance, amount, stated: amount)
    with pytest.raises(check.WrongResult, match="stepwise"):
        check.run_backend(backend, SMALL, HIGH)


def test_ck6b_once_a_credit_is_clamped_where_it_is_drawn_no_ancestor_ceiling_binds():
    for share in (LOW, HIGH):
        model = check.run_model(check.stream(2000, share), [])
        assert model.ancestor_binds == 0


def test_ck7_a_wrong_stored_count_fails_the_check(monkeypatch):
    monkeypatch.setattr(check, "expected_stored", lambda postings: 0)
    with pytest.raises(check.WrongResult, match="stored"):
        check.run_backend("rdflib", SMALL, HIGH)


def test_ck8_the_check_does_not_fail_on_time(monkeypatch):
    ticks = itertools.count(0, 10**6)
    monkeypatch.setattr(check.time, "perf_counter", lambda: next(ticks))
    ms = check.run((SMALL,), (HIGH,), ["rdflib"])
    assert ms and ms[0].write_seconds >= 10**6


def test_ck9_the_store_is_removed_when_the_run_ends_and_when_it_fails(tmp_path, monkeypatch):
    check.run_backend("oxigraph", SMALL, HIGH, directory=str(tmp_path))
    assert not os.listdir(tmp_path)

    def failing(*a):
        raise RuntimeError("the read failed")

    monkeypatch.setattr(check, "read", failing)
    with pytest.raises(RuntimeError, match="the read failed"):
        check.run_backend("oxigraph", SMALL, HIGH, directory=str(tmp_path))
    assert not os.listdir(tmp_path)


def test_ck10_the_report_is_written_where_asked(tmp_path):
    check.write_report(check.run((SMALL,), (HIGH,), ["rdflib", "oxigraph"]), tmp_path)
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert {m["backend"] for m in data["measurements"]} == {"rdflib", "oxigraph"}
    assert data["environment"]["rdflib"] and data["environment"]["pyoxigraph"]
    assert (tmp_path / "report.md").read_text(encoding="utf-8").startswith("# Ledger credit kinds")


@pytest.mark.parametrize("form", sorted(check.KIND_JOIN))
@pytest.mark.parametrize("backend", BACKENDS)
def test_ck11_each_form_of_the_kind_join_reads_the_models_balance(monkeypatch, backend, form):
    monkeypatch.setenv("LEDGER_KINDS_FORM", form)
    assert check.run_backend(backend, SMALL, HIGH).form == form


def test_ck12_the_corpus_has_credits_with_no_kind_only_where_no_account_restricts_kinds():
    postings = check.stream(2000, HIGH)
    kindless = [p for p in postings if not p.debit and p.kind is None]
    assert kindless and all(check.unrestricted(p.contract) for p in kindless)
    model = check.run_model(postings, [postings[-1].pos])
    root = next(i for i, a in enumerate(check.TREE) if a.level == 3)
    point = postings[-1].pos
    assert model.rows[("kind-filtered", root, point)] == model.rows[("plain", root, point)]


def test_ck13_a_join_that_drops_a_credit_with_no_kind_fails_the_check(monkeypatch):
    monkeypatch.setenv("LEDGER_KINDS_FORM", "union")
    monkeypatch.setitem(check.KIND_JOIN, "union", check.UNCORRECTED_UNION)
    with pytest.raises(check.WrongResult, match="kind-filtered"):
        check.run_backend("oxigraph", SMALL, HIGH)


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck14_a_wrong_checkpoint_fails_the_check(monkeypatch, backend):
    real = check.checkpoint_balances
    monkeypatch.setattr(check, "checkpoint_balances", lambda model, positions: {k: (a, b, c + 1) for k, (a, b, c) in real(model, positions).items()})
    with pytest.raises(check.WrongResult, match="checkpointed"):
        check.run_backend(backend, 1000, HIGH)


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck15_a_shortcut_that_skips_a_needed_fallback_fails_the_check(monkeypatch, backend):
    monkeypatch.setattr(check, "shortcut_sound", lambda *a: True)
    with pytest.raises(check.WrongResult, match="shortcut"):
        check.run_backend(backend, SMALL, HIGH)


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck16_the_shortcut_falls_back_from_the_start_and_less_from_a_checkpoint(backend):
    m = check.run_backend(backend, 1000, LOW)
    start = sum(r.fallbacks for (mode, _), r in m.shortcut.items() if mode == "full")
    cp = sum(r.fallbacks for (mode, _), r in m.shortcut.items() if mode == "checkpointed")
    reads = sum(r.reads for (mode, _), r in m.shortcut.items() if mode == "full")
    assert start == reads and cp < reads


def test_ck17_the_emitted_corpus_and_expected_balances_match_the_model(tmp_path):
    check.emit(tmp_path, (SMALL,), (HIGH,))
    data = json.loads((tmp_path / "expected.json").read_text(encoding="utf-8"))
    (corpus,) = data["corpora"]
    assert sum(1 for _ in open(tmp_path / corpus["file"], encoding="utf-8")) == corpus["stored"]
    model = check.run_model(check.stream(SMALL, HIGH), corpus["points"])
    assert all(r["balance"] == model.balance[(r["fold"], check.BY_IRI[r["account"]], r["point"])] for r in corpus["reads"] if not r["checkpointed"])
