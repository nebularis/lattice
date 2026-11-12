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


# the two-level corpus and the cut (LG-16)


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("share", (LOW, HIGH))
def test_ck18_the_sum_with_cuts_and_the_stepwise_fold_read_the_models_balance_of_every_ancestor(backend, share):
    m = check.run_backend_cuts(backend, SMALL, share)
    postings = check.stream_two_level(SMALL, share)
    assert m.stored_triples == check.expected_stored(postings)
    assert sum(r.reads for r in m.reads.values()) == len(check.CUT_FOLDS) * len(check.ANCESTORS) * len(check.read_points(postings[-1].pos))
    assert m.notes["cuts"] == sum(len(p.cuts) for p in postings) and m.notes["cut_triples"] == check.CUT_TRIPLES * m.notes["cuts"]
    if share >= check.STEPWISE_BINDS_FROM:
        assert m.notes["cuts"] > 0 and m.notes["ancestors_where_uncut_differs_engine"] == m.notes["ancestors_where_uncut_differs"] > 0


def test_ck19_the_four_step_history_of_the_sketch(monkeypatch):
    """Built against the model's own functions on the sketch's tree (an annual cap of 20 that accepts recoveries only, an aggregate of 10, sections S and T of 10), since the benchmark's tree is fixed."""
    recovery, reinstatement = check.L + "Recovery", check.L + "Reinstatement"
    tree = [check.Account("urn:acct:cap", 2, None, (recovery,)), check.Account("urn:acct:agg", 1, 0), check.Account("urn:acct:s", 0, 1), check.Account("urn:acct:t", 0, 1)]
    monkeypatch.setattr(check, "TREE", tree)
    monkeypatch.setattr(check, "STATED", (10, 10, 20, 10**6))
    cap, agg, s, t = range(4)
    step = [a.stated for a in tree]
    check.settle_debit(step, s, 10)
    first = check.Posting(1, 0, s, True, 10, None)
    applied, cuts = check.settle_credit(step, agg, 10, reinstatement)
    second = check.Posting(2, 0, agg, False, 10, reinstatement, applied, cuts)
    assert (applied, cuts) == (10, ()) and step == [10, 10, 0, 10]
    applied, cuts = check.settle_credit(step, s, 2, recovery)
    third = check.Posting(3, 0, s, False, 2, recovery, applied, cuts)
    assert (applied, cuts) == (2, ((agg, 2),)) and step == [12, 10, 2, 10]
    check.settle_debit(step, t, 3)
    postings = [first, second, third, check.Posting(4, 0, t, True, 3, None)]
    model = check.run_model(postings, [4])
    assert [model.balance[(f, agg, 4)] for f in ("applied", "stepwise", "sum-with-cuts")] == [9, 7, 7]
    assert all(model.balance[(f, cap, 4)] == 9 for f in ("applied", "stepwise", "sum-with-cuts"))
    assert model.cuts == [(3, agg, 2)] and model.ancestor_binds == 1
    assert [model.balance[("stepwise", i, 4)] for i in range(4)] == step
    assert check.expected_stored(postings) == check.structure_triples() + 8 * 4 + 2 + 2 + check.CUT_TRIPLES
    assert sum(1 for q in check.quads(postings, {}) if q[0].startswith("urn:cut:")) == check.CUT_TRIPLES


def test_ck20_the_model_tells_the_sum_with_cuts_from_the_sum_without_them():
    postings = check.stream_two_level(2000, HIGH)
    point = postings[-1].pos
    model = check.run_model(postings, [point])
    assert model.ancestor_binds > 0 and model.ancestor_binds == sum(len(p.cuts) for p in postings) == len(model.cuts)
    assert any(model.balance[("applied", i, point)] != model.balance[("stepwise", i, point)] for i in check.ANCESTORS)
    assert all(model.balance[("sum-with-cuts", i, point)] == model.balance[("stepwise", i, point)] for i in range(len(check.TREE)))
    assert any(check.TREE[p.contract].level > 0 for p in postings if not p.debit)


def test_ck21_a_two_level_corpus_that_cannot_fail_the_cut_is_refused():
    postings = check.stream(SMALL, HIGH)
    model = check.run_model(postings, [postings[-1].pos])
    with pytest.raises(check.WrongResult, match="no ancestor's ceiling binds"):
        check.check_discriminates_cuts(model, HIGH, postings[-1].pos, postings)


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck22_a_cut_dropped_from_the_stored_data_fails_the_check(monkeypatch, backend):
    real_quads, real_stored = check.quads, check.expected_stored

    def without_one_cut(postings, cps):
        dropped = None
        for q in real_quads(postings, cps):
            if dropped is None and q[0].startswith("urn:cut:"):
                dropped = q[0]
            if q[0] != dropped:
                yield q

    monkeypatch.setattr(check, "quads", without_one_cut)
    monkeypatch.setattr(check, "expected_stored", lambda postings: real_stored(postings) - check.CUT_TRIPLES)  # the count agrees, so only the balance can tell
    with pytest.raises(check.WrongResult, match="sum-with-cuts.*the model gives"):
        check.run_backend_cuts(backend, SMALL, HIGH)


def test_ck23_a_writer_that_records_no_cut_fails_the_check(monkeypatch):
    real = check.settle_credit
    monkeypatch.setattr(check, "settle_credit", lambda *a: (real(*a)[0], ()))
    with pytest.raises(check.WrongResult, match="cut"):
        check.run_backend_cuts("rdflib", SMALL, HIGH)


def test_ck24_a_wrong_stored_cut_count_fails_the_check(monkeypatch):
    monkeypatch.setattr(check, "expected_stored", lambda postings: 0)
    with pytest.raises(check.WrongResult, match="stored"):
        check.run_backend_cuts("rdflib", SMALL, HIGH)


def test_ck25_the_report_has_the_two_level_rows(tmp_path):
    check.write_report(check.run((SMALL,), (HIGH,), ["rdflib"]) + check.run_cuts((SMALL,), (HIGH,), ["rdflib"]), tmp_path)
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert [m["corpus"] for m in data["measurements"]] == [check.CORPUS_ONE, check.CORPUS_TWO]
    text = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "sum-with-cuts / kind-filtered" in text and "sum-with-cuts / stepwise" in text


# like-for-like read forms, a cut that copies its position, a ceiling above a stated amount, and the sketch's tree in an engine (LG-17, part one)


def _skip_unavailable(backend):
    return pytest.param(backend, marks=pytest.mark.skipif(backend not in BACKENDS, reason="the Jena test kit jar is not built or there is no java (mise run bootstrap:sparql-testkit)"))


ALL_BACKENDS = [_skip_unavailable(b) for b in check.BACKENDS]


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck26_the_plain_union_and_shortcut_reads_of_the_two_level_corpus_equal_the_model(backend):
    m = check.run_backend_cuts(backend, SMALL, HIGH, like_for_like=True)
    points = len(check.read_points(check.stream_two_level(SMALL, HIGH)[-1].pos))
    for fold in ("plain", check.UNION_FOLD):
        assert sum(r.reads for (f, _), r in m.reads.items() if f == fold) == len(check.ANCESTORS) * points
        assert sum(r.reads for (f, _), r in m.cp_reads.items() if f == fold) == len(check.ANCESTORS) * points
    assert sum(r.reads for r in m.shortcut.values()) == 2 * len(check.ANCESTORS) * points


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck27_a_like_for_like_read_that_is_wrong_fails_the_check(monkeypatch, backend):
    real = check.read_union
    monkeypatch.setattr(check, "read_union", lambda *a: (lambda b, n: (b + 1, n))(*real(*a)))
    with pytest.raises(check.WrongResult, match=check.UNION_FOLD):
        check.run_backend_cuts(backend, SMALL, HIGH, like_for_like=True)


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck27b_a_shortcut_that_skips_a_needed_fallback_on_the_two_level_corpus_fails_the_check(monkeypatch, backend):
    monkeypatch.setattr(check, "shortcut_sound", lambda *a: True)
    with pytest.raises(check.WrongResult, match="shortcut"):
        check.run_backend_cuts(backend, SMALL, HIGH, like_for_like=True)


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck28_a_joined_and_a_copied_cut_both_read_the_models_balance_and_the_copy_costs_a_triple_a_cut(backend):
    joined, copied = check.run_backend_cut_forms(backend, SMALL, HIGH)
    cuts = joined.notes["cuts"]
    assert (joined.cut_form, copied.cut_form) == ("joined", "copied") and cuts > 0
    assert copied.stored_triples - joined.stored_triples == cuts
    assert copied.notes["cut_triples"] - joined.notes["cut_triples"] == cuts
    assert joined.stored_triples == check.expected_stored(check.stream_two_level(SMALL, HIGH))


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck29_a_copied_cut_with_a_wrong_position_fails_the_check(monkeypatch, backend):
    real = check.quads

    def wrong_position(postings, cps, **kw):
        for s, p, o, g in real(postings, cps, **kw):
            yield (s, p, ("n", o[1] + 10**6), g) if p == check.L + "cutPosition" else (s, p, o, g)

    monkeypatch.setattr(check, "quads", wrong_position)
    with pytest.raises(check.WrongResult, match="copied cut.*the model gives"):
        check.run_backend_cut_forms(backend, SMALL, HIGH)


def test_ck30_a_default_account_has_its_stated_amount_for_a_ceiling_and_the_variant_raises_a_share_of_them():
    assert all(a.ceiling == a.stated and a.ceiling_amount is None for a in check.TREE)
    variant = check.build_ceiling_tree()
    raised = [a for a in variant if a.ceiling_amount is not None]
    assert raised and all(a.level < 2 and a.ceiling == int(a.stated * check.CEILING_FACTOR) for a in raised)
    assert len(raised) < len([a for a in variant if a.level < 2])
    with check.using_tree(variant):
        assert check.TREE is variant and check.structure_triples() == sum(2 + (a.parent is not None) + len(a.accepts) for a in variant) + len(raised)
    assert check.TREE is not variant and check.structure_triples() == sum(2 + (a.parent is not None) + len(a.accepts) for a in check.TREE)


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck31_with_a_ceiling_above_stated_the_sum_with_cuts_equals_the_stepwise_balance_at_every_ancestor(backend):
    m = check.run_backend_cuts(backend, SMALL, HIGH, ceiling=True)
    assert m.corpus == check.CORPUS_CEILING and m.notes["cuts"] > 0 and m.notes["ancestor_reads_above_stated"] > 0 and m.notes["accounts_above_stated_at_some_point"] > 0
    assert m.notes["accounts_with_a_ceiling_above_stated"] == sum(a.ceiling_amount is not None for a in check.build_ceiling_tree())
    assert sum(r.reads for r in m.reads.values()) == len(check.CUT_FOLDS) * len(check.ANCESTORS) * len(check.read_points(check.stream_two_level(SMALL, HIGH)[-1].pos))
    assert check.TREE[0].ceiling == check.TREE[0].stated and all(a.ceiling_amount is None for a in check.TREE)


@pytest.mark.parametrize("backend", BACKENDS)
def test_ck32_a_read_that_clamps_at_the_stated_amount_fails_the_ceiling_variant(monkeypatch, backend):
    real = check.limits
    monkeypatch.setattr(check, "limits", lambda b, i: (lambda stated, ceiling: (stated, stated))(*real(b, i)))
    with pytest.raises(check.WrongResult, match="stepwise.*the model gives"):
        check.run_backend_cuts(backend, SMALL, HIGH, ceiling=True)


def test_ck32b_a_ceiling_variant_in_which_nothing_stands_above_its_stated_amount_is_refused():
    postings = check.stream_two_level(SMALL, HIGH)
    model = check.run_model(postings, [postings[-1].pos])
    with pytest.raises(check.WrongResult, match="above its stated amount"):
        check.check_discriminates_ceiling(model, HIGH, [postings[-1].pos])


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_ck33_the_sketchs_tree_and_history_read_the_sketchs_figures_through_the_engine(backend):
    got = check.run_sketch(backend)
    agg, cap = got["urn:acct:agg"], got["urn:acct:cap"]
    assert [agg[f] for f in ("applied", "stepwise", "sum-with-cuts")] == [9, 7, 7] and (agg["cuts"], agg["cut_count"]) == (2, 1)
    assert all(cap[f] == 9 for f in ("kind-filtered", "kind-filtered-union", "stepwise", "applied", "sum-with-cuts")) and cap["cut_count"] == 0
    assert check.TREE is not None and len(check.TREE) == 33


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_ck34_a_writer_that_records_no_cut_fails_the_sketch_through_the_engine(monkeypatch, backend):
    real = check.settle_credit
    monkeypatch.setattr(check, "settle_credit", lambda *a: (real(*a)[0], ()))
    with pytest.raises(check.WrongResult, match="sketch"):
        check.run_sketch(backend)


def test_ck35_the_report_has_the_like_for_like_cut_form_and_ceiling_rows(tmp_path):
    ms = check.run_cuts((SMALL,), (HIGH,), ["rdflib"], like_for_like=True) + check.run_cut_forms((SMALL,), (HIGH,), ["rdflib"]) + check.run_cuts((SMALL,), (HIGH,), ["rdflib"], ceiling=True)
    check.write_report(ms, tmp_path)
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert [m["corpus"] for m in data["measurements"]] == [check.CORPUS_TWO, check.CORPUS_FORMS, check.CORPUS_FORMS, check.CORPUS_CEILING]
    text = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert f"sum-with-cuts / {check.UNION_FOLD}" in text and "copied / joined" in text and "ancestor reads above stated" in text
