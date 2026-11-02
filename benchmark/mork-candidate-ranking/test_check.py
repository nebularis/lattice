# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The check's own tests (ADR-A124): it fails on a source with no pair or a method that ranks nothing, and a hit rate never fails it."""

from __future__ import annotations

import check


def _case(pairs=4, ranked=4, hits=0):
    return {"name": "x", "pairs": pairs, "ranked": {m: ranked for m in check.METHODS},
            "top5": {m: hits for m in check.METHODS}, "top10": {m: hits for m in check.METHODS}}


def test_cr1_no_hit_never_fails_and_a_missing_source_or_ranking_does():
    assert check.verify({"cases": [_case(hits=0)]}) == []
    assert check.verify({"cases": [_case(pairs=0, ranked=0)]}) != []
    assert check.verify({"cases": [_case(ranked=3)]}) != []
