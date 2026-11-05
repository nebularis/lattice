# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The check's own tests (ADR-A124): it passes on a right history at small sizes, fails on a wrong one, does not fail on time, and contracts no store behind."""

from __future__ import annotations

import itertools
import json
import os

import pytest

import check

SMALL, EVERY = 120, 20


@pytest.mark.parametrize("strategy", check.STRATEGIES)
def test_lc1_each_strategy_reads_the_models_balance_of_every_account_at_every_point(strategy):
    measurement, _ = check.run_strategy(strategy, SMALL, EVERY)
    assert sum(r.reads for r in measurement.reads.values()) == len(check.build_tree()) * len(check.read_points(SMALL, EVERY))


def test_lc2_the_stored_counts_follow_the_arithmetic():
    structure = check.structure_triples(check.build_tree())
    assert structure == 3 * 110 + 2 * 2
    assert check.expected_stored("post-once", 1000) == structure + 8 * 1000
    assert check.expected_stored("every-level", 1000) - structure == check.DEPTH * (check.expected_stored("post-once", 1000) - structure)
    assert check.expected_stored("post-once-balance-after", 1000) == structure + 9 * 1000
    assert check.expected_stored("post-once-checkpointed", 1000, 250) == structure + 8 * 1000 + 112 * 4 * 4
    assert check.expected_stored("post-once-period-graphs", 1000, 250) == check.expected_stored("post-once-checkpointed", 1000, 250)


@pytest.mark.parametrize("strategy", ["post-once", "post-once-period-graphs"])
def test_lc3_a_balance_that_is_off_by_one_fails_the_check(monkeypatch, strategy):
    real = check.read
    monkeypatch.setattr(check, "read", lambda *a: (lambda b, f: (b + 1, f))(*real(*a)))
    with pytest.raises(check.WrongResult, match="the model gives"):
        check.run_strategy(strategy, SMALL, EVERY)


def test_lc4_a_wrong_stored_count_fails_the_check(monkeypatch):
    monkeypatch.setattr(check, "expected_stored", lambda strategy, count, every=0: 0)
    with pytest.raises(check.WrongResult, match="stored"):
        check.run_strategy("every-level", SMALL, EVERY)


def test_lc5_a_checkpointed_read_that_folds_more_than_the_plain_read_fails_the_check(monkeypatch):
    real = check.read
    monkeypatch.setattr(check, "read", lambda strategy, *a: (lambda b, f: (b, f + 1000 if strategy == "post-once-checkpointed" else f))(*real(strategy, *a)))
    with pytest.raises(check.WrongResult, match="folded more"):
        check.run((SMALL,), EVERY)


def test_lc6_a_checkpoint_bounds_the_fold_at_a_late_point():
    _, plain = check.run_strategy("post-once", SMALL, EVERY)
    _, bounded = check.run_strategy("post-once-checkpointed", SMALL, EVERY)
    accounts = check.build_tree()
    programme = next(i for i, a in enumerate(accounts) if a.level == 2)
    assert bounded[(programme, SMALL - 1)] < plain[(programme, SMALL - 1)]


def test_lc7_the_check_does_not_fail_on_time(monkeypatch):
    ticks = itertools.count(0, 10**6)
    monkeypatch.setattr(check.time, "perf_counter", lambda: next(ticks))
    measurements = check.run((SMALL,), EVERY)
    assert measurements and all(m.write_seconds >= 10**6 for m in measurements)


def test_lc8_the_store_is_removed_when_the_run_ends_and_when_it_fails(tmp_path, monkeypatch):
    check.run_strategy("post-once", SMALL, EVERY, directory=str(tmp_path))
    assert not os.listdir(tmp_path)
    monkeypatch.setattr(check, "expected_stored", lambda strategy, count, every=0: 0)
    with pytest.raises(check.WrongResult):
        check.run_strategy("post-once", SMALL, EVERY, directory=str(tmp_path))
    assert not os.listdir(tmp_path)


def test_lc9_the_report_is_written_where_asked(tmp_path):
    check.write_report(check.run((SMALL,), EVERY), tmp_path)
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert {m["strategy"] for m in data["measurements"]} == set(check.STRATEGIES)
    assert (tmp_path / "report.md").read_text(encoding="utf-8").startswith("# Ledger posting cost")


def test_lc10_period_graphs_store_the_postings_in_graphs_and_the_same_count_as_checkpoints():
    plain, _ = check.run_strategy("post-once-checkpointed", SMALL, EVERY)
    graphed, _ = check.run_strategy("post-once-period-graphs", SMALL, EVERY)
    assert graphed.stored_triples == plain.stored_triples
    accounts = check.build_tree()
    stream = check.events(SMALL, accounts)
    model = check.run_model(SMALL, EVERY, check.read_points(SMALL, EVERY), accounts, stream)
    store = check.ox.Store()
    store.extend(check.quads_for("post-once-period-graphs", accounts, stream, model, EVERY))
    postings = {q.subject for q in store.quads_for_pattern(None, check.RDF_TYPE, check.n("Posting"), None)}
    assert len(postings) == SMALL
    assert not list(store.quads_for_pattern(None, check.RDF_TYPE, check.n("Posting"), check.ox.DefaultGraph()))
    contract, _, _ = stream[EVERY]  # event EVERY + 1, the first of period 1
    assert next(store.quads_for_pattern(check.ox.NamedNode(f"urn:posting:{EVERY + 1}:{accounts[contract].iri.value.rsplit(':', 1)[1]}"), None, None, None)).graph_name == check.period_graph(accounts[accounts[contract].parent].iri, 1)


def test_lc11_a_period_graph_fold_is_no_wider_than_the_checkpointed_fold_at_an_ancestor():
    _, checkpointed = check.run_strategy("post-once-checkpointed", SMALL, EVERY)
    _, graphed = check.run_strategy("post-once-period-graphs", SMALL, EVERY)
    accounts = check.build_tree()
    assert all(graphed[(i, p)] <= checkpointed[(i, p)] for (i, p) in graphed if accounts[i].level > 0)


def test_lc12_a_period_graph_read_that_folds_more_than_the_checkpointed_read_fails_the_check(monkeypatch):
    real = check.read
    monkeypatch.setattr(check, "read", lambda strategy, *a: (lambda b, f: (b, f + 1000 if strategy == "post-once-period-graphs" else f))(*real(strategy, *a)))
    with pytest.raises(check.WrongResult, match="period-graph read folded more"):
        check.run((SMALL,), EVERY)


def test_lc13_a_position_filter_is_left_only_in_a_period_that_the_bound_cuts(monkeypatch):
    accounts = check.build_tree()
    stream = check.events(SMALL, accounts)
    model = check.run_model(SMALL, EVERY, [], accounts, stream)
    store = check.ox.Store()
    store.extend(check.quads_for("post-once-period-graphs", accounts, stream, model, EVERY))
    programme = next(a for a in accounts if a.level == 2)
    blocks, real = [], check.graph_block
    monkeypatch.setattr(check, "graph_block", lambda names, scope, bound: (blocks.append((len(names), bound)), real(names, scope, bound))[1])
    check.fold_graphs(store, programme, 2 * EVERY, 5 * EVERY, EVERY)
    assert blocks == [(3 * 5, "")]
    blocks.clear()
    check.fold_graphs(store, programme, 2 * EVERY, 5 * EVERY - 3, EVERY)
    assert sorted(blocks) == [(5, f"FILTER(?pos <= {5 * EVERY - 3})"), (2 * 5, "")]
