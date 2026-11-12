# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The single-writer benchmark's own tests (ADR-A124, PRI-63): one writer's records equal the replay of its commits whichever way it writes, a writer that forgets what it wrote is caught with the guard and
without it, a second writer beside the one writer is caught, and the report is written."""

from __future__ import annotations

import pytest

import check as ck
import single_writer as sw
import writes as w

PRELOAD, TOTAL = 1_000, 48  # the smallest corpus at 30% credits in which a ceiling binds


@pytest.mark.parametrize("name", ["oxigraph memory", "oxigraph disk"])
@pytest.mark.parametrize("writer,batch,guarded,backlog", [("reads", 1, True, False), ("keeps", 1, True, False), ("keeps", 1, False, True), ("keeps", 5, True, True)])
def test_sw1_one_writer_leaves_records_equal_to_the_replay_on_every_store(name, writer, batch, guarded, backlog):
    r = sw.run_queue(name, 4, writer, batch, guarded, backlog, PRELOAD, TOTAL)
    assert r["commits"] + r["refused"] == r["requests"] == TOTAL and r["commits"] > 0
    assert r["audit"]["live"] == r["commits"] and r["audit"]["dense"] and r["audit"]["cuts_differ"] == 0
    assert (r["batch_mean"] > 1) == (batch > 1) and r["waited_p95_ms"] >= 0


def test_sw2_a_batch_moves_the_revision_by_the_postings_it_writes():
    with w.opened("oxigraph memory") as backend:
        corpus, base = w.preload(backend, PRELOAD)
        live = sw.Keeper(backend, len(corpus.positions))
        plans = sw.write_batch(live, [(r, f"B{n}") for n, r in enumerate(w.requests(12, w.SHARE, ck.SEED + 7))])
        written = sum(not p.refused for p in plans)
        assert written > 1 and live.at == base + written == w.Live.revision(live)
        assert w.audit(backend, base, expect=written)["dense"]
        assert live.held == [w.Live.balance(live, i, live.at) for i in range(len(ck.TREE))]


@pytest.mark.parametrize("guarded", [True, False])
def test_sw3_a_writer_that_forgets_what_it_wrote_fails_the_run(monkeypatch, guarded):
    monkeypatch.setattr(sw.Keeper, "keep", lambda self, plan: None)
    with pytest.raises(ck.WrongResult):
        sw.run_queue("oxigraph memory", 2, "keeps", 1, guarded, True, PRELOAD, TOTAL)


def test_sw4_a_second_writer_beside_the_one_writer_is_caught_by_the_guard():
    with w.opened("oxigraph memory") as backend:
        corpus, base = w.preload(backend, PRELOAD)
        live, other = sw.Keeper(backend, len(corpus.positions)), w.Live(backend, len(corpus.positions))
        first, second = w.requests(2, w.SHARE, ck.SEED + 9)
        assert not w.write_one(other, first, "other", retry=False)[0].refused
        with pytest.raises(ck.WrongResult):
            w.write_one(live, second, "mine", retry=False)
        with pytest.raises(ck.WrongResult):
            sw.write_batch(live, [(second, "mine2")])


def test_sw5_a_batch_is_refused_to_a_writer_that_reads():
    with pytest.raises(ValueError):
        sw.run_queue("oxigraph memory", 1, "reads", 5)


def test_sw6_the_report_has_a_table_for_each_piece():
    guarded = [w.run_stress(2, True, PRELOAD, TOTAL)]
    runs = [sw.run_queue("oxigraph memory", 2, "keeps", 1, True, False, PRELOAD, TOTAL), sw.run_queue("oxigraph memory", 2, "keeps", 5, True, True, PRELOAD, TOTAL)]
    text = "\n".join(sw.render({"environment": {"store": "test"}, "guarded": guarded, "queue": runs}))
    assert "keeps, batches of 5" in text and "planned a day" in text and "against guarded" in text
    assert sw.capacity(100.0) == {"planned_per_s": 70.0, "planned_per_day": 70.0 * 86_400}
