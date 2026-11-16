# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The probes' own tests (LG-22, ADR-A124): each runs at a small size, reports what it is asked for, fails on a wrong result and puts the period length back."""

from __future__ import annotations

import pytest

import check as ck
import probes


def test_pr1_the_period_probe_reports_the_graphs_the_rows_and_the_time_of_each_length_on_both_engines():
    rows = probes.period_probe(1000, 0.05, (100, 200), 2, ("rdflib", "oxigraph"))
    assert [(r["backend"], r["period"]) for r in rows] == [("rdflib", 100), ("oxigraph", 100), ("rdflib", 200), ("oxigraph", 200)]
    assert all(r["repeats"] == 2 and r["min_ms"] <= r["median_ms"] <= r["max_ms"] and r["rows"] > 0 for r in rows)
    by = {(r["backend"], r["period"]): r for r in rows}
    assert by[("rdflib", 100)]["period_graphs"] > by[("rdflib", 200)]["period_graphs"] and by[("rdflib", 100)]["rows"] == by[("rdflib", 200)]["rows"]
    assert ck.EVERY_POSITIONS == 200


def test_pr2_a_read_that_is_wrong_fails_the_period_probe(monkeypatch):
    real = ck.read
    monkeypatch.setattr(ck, "read", lambda *a, **k: (lambda b, n: (b + 1, n))(*real(*a, **k)))
    with pytest.raises(ck.WrongResult, match="the model gives"):
        probes.period_probe(1000, 0.05, (200,), 1, ("oxigraph",))
    assert ck.EVERY_POSITIONS == 200


@pytest.mark.skipif(not ck.jena_available(), reason="the Jena test kit jar is not built or there is no java (mise run bootstrap:sparql-testkit)")
def test_pr3_the_cut_probe_reports_each_read_and_the_cuts_before_and_after():
    r = probes.cut_probe(1000, 0.30, 3, 1)
    assert set(r["modes"]) == {"from the start", "from a checkpoint"} and r["cuts"]["after LG-19"] > 0 and r["cuts"]["before LG-19"] > 0
    for cell in r["modes"].values():
        for fold in ("kind-filtered-union", "sum-with-cuts"):
            assert cell[fold]["all 27 reads"]["repeats"] == 3 and cell[fold]["root"]["median_ms"] > 0
        assert cell["sum-with-cuts / kind-filtered-union, all 27 reads"] > 0


def test_pr4_the_report_has_both_probes():
    data = {"environment": {"store": "test"}, "count": 1000, "share": 0.05, "period": probes.period_probe(1000, 0.05, (200,), 1, ("oxigraph",)), "cuts": None}
    text = "\n".join(probes.render({**data, "cuts": {"backend": "jena", "postings": 1000, "share": 0.05, "credits": {"after LG-19": 1, "before LG-19": 2}, "cuts": {"after LG-19": 3, "before LG-19": 4},
                                                       "modes": {"from the start": {"kind-filtered-union": {"all 27 reads": probes.spread([0.001]), "root": probes.spread([0.001])}, "sum-with-cuts": {"all 27 reads": probes.spread([0.002]), "root": probes.spread([0.002])},
                                                                 "sum-with-cuts / kind-filtered-union, all 27 reads": 2.0, "sum-with-cuts / kind-filtered-union, root": 2.0}}}}))
    assert "## The period probe" in text and "## The cut probe" in text and "ratio of the medians" in text


def test_pr5_the_reference_generator_posts_every_debit_it_draws():
    assert probes.legacy_stream(5000, 0.05, True)[-1].pos < ck.generate(5000, 0.05, True)[-1].pos
