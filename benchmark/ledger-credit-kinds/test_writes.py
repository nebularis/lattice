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
        assert set(r["classes"]) <= set(w.CLASSES) and sum(c["writes"] for c in r["classes"].values()) == 40 - r["refused"]
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
    assert w.requests(50, w.SHARE, 1) == w.requests(50, w.SHARE, 1) != w.requests(50, w.SHARE, 2)
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
