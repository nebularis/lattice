# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The write benchmark's own tests (ADR-A124, PRI-63): a guarded writer's records equal the replay of its commits, an unguarded writer's do not, a wrong stored cut and a gap in the revisions fail the audit,
an effective fold that reads recorded positions fails, and the report is written."""

from __future__ import annotations

import pytest

import check as ck
import writes as w

SMALL, LATE = 300, 1000


def tamper(backend, old: str, new: str, where: str) -> None:
    backend.update(f"DELETE {{ GRAPH ?g {{ {old} }} }} INSERT {{ GRAPH ?g {{ {new} }} }} WHERE {{ GRAPH ?g {{ {where} }} }}")


def test_wr1_a_live_write_leaves_records_equal_to_the_replay_of_the_history():
    for guarded in (True, False):
        r = w.run_writes("oxigraph memory", SMALL, guarded, 40)
        assert r["audit"]["live"] == 40 - r["refused"] and r["audit"]["dense"]
        assert set(r["classes"]) <= set(w.CLASSES) | {w.REFUSED} and sum(c["writes"] for k, c in r["classes"].items() if k != w.REFUSED) == 40 - r["refused"]
        assert all(c["confirm"]["mean_ms"] == 0 for c in r["classes"].values()) == (not guarded)


def test_wr2_the_live_balance_equals_the_model_at_a_contract_and_at_every_ancestor():
    corpus = ck.build_cut_corpus(LATE, w.SHARE)
    point = corpus.points[-1]
    with w.opened("oxigraph memory") as backend:
        backend.load(w.ledger_quads(corpus.postings, corpus.cps, point))
        live = w.Live(backend, len(corpus.positions))
        for i in range(len(ck.TREE)):
            assert live.balance(i, point) == corpus.model.balance[("stepwise", i, point)]
        for i in ck.ANCESTORS:
            assert live.balance(i, point) == ck.read_with_cuts(backend, i, point, True)[0]


def test_wr3_requests_are_seeded_and_a_seed_changes_them():
    assert w.requests(1000, 50, w.SHARE, 1) == w.requests(1000, 50, w.SHARE, 1) != w.requests(1000, 50, w.SHARE, 2)
    assert ck.SEED == 20261111


@pytest.mark.parametrize("case", ["recoveries", "debits"])
def test_wr4_with_the_guard_the_second_writer_is_refused_retries_and_the_records_equal_the_replay(case):
    r = w.interleave(case, True)
    assert r["retries"] == 1 and r["dense"] and r["duplicate_positions"] == 0
    assert r["applied_differ"] == r["cuts_differ"] == r["balances_differ"] == r["overdrawn"] == 0
    assert r["second_refused_on_retry"] == (case == "debits")


def test_wr5_without_the_guard_a_stale_cut_lands_and_a_balance_differs_from_the_replay():
    r = w.interleave("recoveries", False)
    assert r["retries"] == 0 and r["cuts_differ"] >= 1 and r["balances_differ"] >= 1 and not r["dense"]


def test_wr6_without_the_guard_the_last_of_an_availability_is_drawn_twice():
    r = w.interleave("debits", False)
    assert r["overdrawn"] >= 1 and not r["second_refused_on_retry"]


def test_wr7_a_debit_and_a_credit_on_different_contracts_equal_the_replay_with_the_guard():
    r = w.interleave("disjoint", True)
    assert r["dense"] and r["applied_differ"] == r["cuts_differ"] == r["balances_differ"] == 0


def run_serial(guarded: bool = True):
    """The recoveries case run one writer at a time, left open for a test to change."""
    with w.small_ledger(guarded) as (backend, one, _):
        for n, r in enumerate([w.Request(w.S, True, 6, None), w.Request(w.T, True, 4, None), w.Request(w.AGG, False, 3, w.REINSTATEMENT), w.Request(w.S, False, 6, w.RECOVERY), w.Request(w.T, False, 4, w.RECOVERY)]):
            w.write_one(one, r, f"s{n}", retry=False)
        assert w.audit(backend, 0, expect=5)["dense"]
        yield backend


def test_wr8_a_wrong_stored_cut_fails_the_audit():
    for backend in run_serial():
        tamper(backend, f"?c <{ck.L}cutValue> ?v", f"?c <{ck.L}cutValue> 99", f"?c <{ck.L}cutValue> ?v")
        with pytest.raises(ck.WrongResult, match="differ from the replay"):
            w.audit(backend, 0)


def test_wr9_a_gap_in_the_revisions_fails_the_audit():
    for backend in run_serial():
        tamper(backend, f"?p <{ck.L}position> 5", f"?p <{ck.L}position> 7", f"?p <{ck.L}position> 5")
        with pytest.raises(ck.WrongResult, match="differ from the replay"):
            w.audit(backend, 0)


def test_wr10_a_duplicate_revision_fails_the_audit():
    for backend in run_serial():
        tamper(backend, f"?p <{ck.L}position> 5", f"?p <{ck.L}position> 4", f"?p <{ck.L}position> 5")
        with pytest.raises(ck.WrongResult, match="differ from the replay"):
            w.audit(backend, 0)


def test_wr11_the_stress_with_the_guard_commits_every_request_densely_and_the_audit_passes():
    r = w.run_stress(3, True, SMALL, 30)
    assert r["commits"] + r["refused"] == 30 and r["audit"]["dense"] and r["audit"]["live"] == r["commits"]


def test_wr12_the_stress_without_the_guard_runs_and_is_audited_not_asserted():
    r = w.run_stress(3, False, SMALL, 30)
    assert r["lost_races"] == 0 and r["audit"]["live"] == 30 - r["refused"]


def test_wr13_a_worker_that_fails_fails_the_run(monkeypatch):
    monkeypatch.setattr(w.Live, "prepare", lambda self, request, tag: (_ for _ in ()).throw(ck.WrongResult("boom")))
    with pytest.raises(ck.WrongResult, match="boom"):
        w.run_stress(2, True, SMALL, 4)


def test_wr14_late_positions_never_follow_the_record_and_the_late_at_a_lower_share_are_among_the_higher():
    postings = ck.build_cut_corpus(LATE, w.SHARE).postings
    low, high = w.late_positions(postings, 0.05), w.late_positions(postings, 0.20)
    assert all(x <= p.pos for x, p in zip(high, postings)) and w.late_positions(postings, 0) == [p.pos for p in postings]
    late = lambda eff: {e for e, (x, p) in enumerate(zip(eff, postings)) if x < p.pos}
    assert 0 < len(late(low)) <= len(late(high)) and late(low) <= late(high)
    assert all(p.pos - x in {n * ck.EVERY_POSITIONS for n in range(0, w.LATE_PERIODS[1] + 1)} for x, p in zip(high, postings))


def test_wr15_with_no_late_posting_the_four_numbers_agree_and_with_late_ones_they_do_not():
    none, some = w.run_late(LATE, 0), w.run_late(LATE, 0.20)
    assert none["late_postings"] == 0 and none["eff vs R"]["differs"] == none["eff vs E"]["differs"] == none["R vs E"]["differs"] == 0
    assert some["late_postings"] > 0 and some["eff vs R"]["differs"] > 0 and some["eff vs E"]["differs"] > 0 and some["R vs E"]["differs"] > 0


def test_wr16_an_effective_fold_that_reads_recorded_positions_fails(monkeypatch):
    monkeypatch.setattr(w, "READ_EFFECTIVE", "position")
    with pytest.raises(ck.WrongResult, match="effective sum"):
        w.run_late(LATE, 0.20)


def test_wr17_a_recorded_sum_that_is_off_by_one_fails(monkeypatch):
    real = ck.read_with_cuts
    monkeypatch.setattr(ck, "read_with_cuts", lambda *a, **k: (lambda b, n, u: (b + 1, n, u))(*real(*a, **k)))
    with pytest.raises(ck.WrongResult, match="recorded sum"):
        w.run_late(LATE, 0.05)


def test_wr18_the_gil_probe_reports_a_rate_for_a_query_an_update_and_the_control():
    assert set(w.gil_probe(0.1)["rate_against_alone"]) == {"query", "update", "pure python control"}


def test_wr19_the_report_has_a_table_for_each_piece(tmp_path):
    data = {"environment": {"python": "x"}, "writes": [w.run_writes("oxigraph memory", SMALL, g, 20) for g in (True, False)], "gil": {"rate_against_alone": {"query": 1.0}, "cpus": 1, "gil_enabled": True, "reading": "r"},
            "interleavings": [w.interleave("recoveries", g) for g in (True, False)], "stress": [w.run_stress(2, True, SMALL, 10)], "isolation": [{"run": 1, **w.run_stress(2, True, SMALL, 10)}], "late": [w.run_late(LATE, 0.05)]}
    text = "\n".join(w.render(data))
    for heading in ("## Piece A", "## Piece B", "## Piece C", "| recoveries |", "| unguarded |", "| oxigraph memory | 2 | 1 |"):
        assert heading in text


# LG-22: request lists that continue the preload's stream, and the cost of a refused request

def fresh_requests(preload, count, share, seed):
    """The lists as they were before LG-22, drawn from a full tree whatever the store holds."""
    with w.seeded(seed):
        return [w.Request(p.contract, p.debit, p.amount, p.kind) for p in ck.stream_two_level(count, share)]


@pytest.mark.parametrize("name", w.LIVE)
def test_wr20_one_writer_sent_a_list_in_order_against_its_preload_refuses_none(name):
    if name == "jena" and not ck.jena_available():
        pytest.skip("the Jena test kit jar is not built or there is no java (mise run bootstrap:sparql-testkit)")
    for guarded in (True, False):
        r = w.run_writes(name, LATE, guarded, 100)
        assert r["refused"] == 0 and r["audit"]["live"] == 100


def test_wr21_the_test_of_wr20_fails_on_the_lists_as_they_were_at_20000_postings(monkeypatch):
    assert w.run_writes("oxigraph memory", 20_000, True, 500)["refused"] == 0
    monkeypatch.setattr(w, "requests", fresh_requests)
    assert w.run_writes("oxigraph memory", 20_000, True, 500)["refused"] > 0


def test_wr22_each_list_of_a_stress_is_valid_alone_and_the_lists_differ_by_seed():
    base = ck.Stream(w.SHARE, True)
    base.take(w.STRESS_PRELOAD)
    lists = [w.requests(w.STRESS_PRELOAD, 250, w.SHARE, ck.SEED + 100 + t) for t in range(4)]
    assert len({tuple(x) for x in lists}) == 4
    for items in lists:
        step = list(base.step)
        for r in items:
            assert not (r.debit and ck.refuses_debit(step, r.at, r.amount))
            ck.settle_debit(step, r.at, r.amount) if r.debit else ck.settle_credit(step, r.at, r.amount, r.kind)


def test_wr23_the_run_counts_the_refusals_of_writers_that_interleave_beside_the_lost_races():
    r = w.run_stress(4, True, LATE, 200)
    assert r["commits"] + r["refused"] == r["requests"] == 200 and r["audit"]["live"] == r["commits"]
    assert r["audit"]["live_debits"] + r["audit"]["live_credits"] == r["commits"] and "lost_races" in r


def test_wr24_a_refused_request_costs_its_path_reads_and_writes_nothing():
    r = w.run_writes("oxigraph memory", LATE, True, 40)
    row = r["classes"][w.REFUSED]
    assert row["writes"] == w.REFUSALS and row["path_reads"] > 1 and row["total"]["mean_ms"] > 0
    assert row["update"]["mean_ms"] == row["confirm"]["mean_ms"] == 0 and row["triples"] == 0
    assert r["audit"]["live"] == 40 - r["refused"]
    assert all(q.debit and q.amount > ck.STATED[-1] for q in w.refusing_requests(w.REFUSALS))


def test_wr25_a_sample_that_a_writer_does_not_refuse_fails_the_run(monkeypatch):
    monkeypatch.setattr(w, "refusing_requests", lambda count: [w.Request(ck.CONTRACTS[0], True, 1, None)] * count)
    with pytest.raises(ck.WrongResult, match="was not refused"):
        w.run_writes("oxigraph memory", SMALL, True, 10)


def test_wr26_the_report_names_the_corpus_by_what_it_holds_and_the_written_debits_and_credits():
    text = "\n".join(w.render({"environment": {"store": "test"}, "writes": [w.run_writes("oxigraph memory", LATE, True, 20)], "stress": [w.run_stress(2, True, LATE, 40)],
                              "interleavings": [], "isolation": [], "late": [w.run_late(LATE, 0.05)], "gil": {"rate_against_alone": {}, "cpus": 1, "gil_enabled": True, "reading": ""}}))
    assert "### Corpora" in text and "debits written" in text and "refused debit" in text
