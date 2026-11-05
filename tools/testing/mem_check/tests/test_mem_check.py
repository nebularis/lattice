# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""mem_check's choice of worker count (ADR-A125)."""

import mem_check
from mem_check import GIB, MIB


def test_mc_t1_the_default_count_is_kept_when_it_fits():
    assert mem_check.workers(8, 500 * MIB, available=8 * GIB) == 8


def test_mc_t2_a_short_machine_runs_as_many_workers_as_fit():
    assert mem_check.workers(8, 700 * MIB, available=4 * GIB) == 4
    assert mem_check.workers(8, 700 * MIB, available=3 * GIB) == 2


def test_mc_t3_the_reserve_counts_against_what_is_available():
    assert mem_check.workers(4, GIB, available=4 * GIB) == 3
    assert mem_check.workers(4, GIB, available=5 * GIB) == 4


def test_mc_t4_never_fewer_than_two_and_never_more_than_the_default():
    assert mem_check.workers(8, GIB, available=0) == 2
    assert mem_check.workers(1, GIB, available=0) == 1


def test_mc_t5_an_override_stands_in_for_the_machine(monkeypatch):
    monkeypatch.setenv("MEM_CHECK_AVAILABLE_MIB", "1024")
    assert mem_check.available_bytes() == GIB
    assert mem_check.workers(8, 700 * MIB) == 2


def test_mc_t6_this_machine_reports_a_plausible_figure(monkeypatch):
    monkeypatch.delenv("MEM_CHECK_AVAILABLE_MIB", raising=False)
    free = mem_check.available_bytes()
    assert free is None or 0 < free < 4096 * GIB
    assert "using" in mem_check.report(4, 500 * MIB)
