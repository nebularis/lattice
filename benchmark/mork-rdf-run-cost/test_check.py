# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The check's own tests (ADR-A124): it passes on a right run at a small size, in both modes, and fails on a wrong count."""

from __future__ import annotations

import pytest

import check


@pytest.mark.parametrize("streamed", [False, True])
def test_mr1_a_small_run_writes_nine_triples_a_record(streamed):
    m = check.measure(200, streamed)
    assert check.verify(m) == [] and m["written"] == 1800


def test_mr2_a_wrong_count_fails_and_time_never_does():
    m = {"records": 10, "mode": "streamed", "written": 89, "findings": 0, "run_s": 1e9}
    assert len(check.verify(m)) == 1
    assert check.verify({**m, "written": 90}) == []
