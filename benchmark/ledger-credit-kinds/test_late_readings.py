# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The late-readings benchmark's own tests (ADR-A124, PRI-63): the three readings equal the model on a corpus with late postings, a read that forgets the recording fails, a checkpointed read that starts a
period too late fails, a settling in recorded order fails, and with no late posting nothing is restated."""

from __future__ import annotations

import pytest

import check as ck
import late_readings as lr
import writes as w

COUNT = 1_000  # the smallest corpus at 30% credits in which a ceiling binds, so cuts exist


@pytest.fixture(scope="module")
def corpus():
    return ck.build_cut_corpus(COUNT, w.SHARE)


def test_lr1_the_readings_equal_the_model_with_a_fifth_of_the_postings_late(corpus):
    r = lr.run_readings(COUNT, 0.20, corpus)
    assert r["late_postings"] > 0 and r["readings"] >= 9 * len(corpus.points) and r["heads"] == 9 * len(corpus.points)
    assert r["restated"]["debits"]["moved"] > 0, "no figure was restated, so the corpus does not show what a late posting does"
    assert set(r["mean_ms"]) == set(lr.READS) and all(v >= 0 for v in r["mean_ms"].values())


def test_lr2_with_no_late_posting_the_readings_agree_and_nothing_is_restated(corpus):
    r = lr.run_readings(COUNT, 0.0, corpus)
    assert r["late_postings"] == 0 and r["B differs at the head"] == 0
    assert all(v["moved"] == 0 for v in r["restated"].values())


def test_lr3_a_read_that_forgets_the_recording_fails(corpus, monkeypatch):
    horizon, scan = corpus.postings[-1].pos, lr.scan
    monkeypatch.setattr(lr, "scan", lambda index, day, known, first, amount: scan(index, day, horizon, first, amount))
    with pytest.raises(ck.WrongResult):
        lr.run_readings(COUNT, 0.20, corpus)


def test_lr4_a_checkpointed_read_that_starts_a_period_too_late_fails(corpus, monkeypatch):
    start = lr.start

    def late(backend, index, day, checkpointed):
        first, base = start(backend, index, day, checkpointed)
        return (first + 1, base) if checkpointed else (first, base)

    monkeypatch.setattr(lr, "start", late)
    with pytest.raises(ck.WrongResult):
        lr.run_readings(COUNT, 0.20, corpus)


def test_lr5_a_settling_in_recorded_order_fails_where_postings_are_late(corpus, monkeypatch):
    monkeypatch.setattr(lr, "in_effective_order", lambda rows: sorted(rows, key=lambda r: int(r[0].rsplit(":", 1)[1])))
    with pytest.raises(ck.WrongResult):
        lr.run_readings(COUNT, 0.20, corpus)


def test_lr6_the_days_read_and_the_report(corpus):
    assert lr.days_for(507) == [507, 400] and lr.days_for(1253) == [1253, 1200, 800] and lr.days_for(150) == [150]
    text = "\n".join(lr.render({"environment": {"store": "test"}, "readings": [lr.run_readings(COUNT, 0.05, corpus)]}))
    assert "A impossible" in text and "A from the close" in text and "the close before" in text
