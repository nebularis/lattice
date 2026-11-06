import time
import sys
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


SHOW_LIMITS = "import os; print(os.environ['MISE_JOBS'], os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS'])"


def test_the_guard_limits_every_task_and_returns_the_commands_code(capfd, monkeypatch):
    from mem_check import guard

    monkeypatch.delenv("MISE_JOBS", raising=False)
    monkeypatch.delenv("PYTEST_XDIST_AUTO_NUM_WORKERS", raising=False)
    monkeypatch.setenv("MEM_CHECK_AVAILABLE_MIB", "8000")
    code = f"{SHOW_LIMITS}; raise SystemExit(7)"
    assert guard.run([sys.executable, "-c", code], poll=0.05) == 7
    assert "1 2" in capfd.readouterr().out


def test_the_guard_stops_a_run_short_of_memory_and_says_so(capfd, monkeypatch):
    from mem_check import guard

    monkeypatch.setenv("MEM_CHECK_AVAILABLE_MIB", "100")
    started = time.monotonic()
    assert guard.run([sys.executable, "-c", "import time; time.sleep(60)"], poll=0.05) == guard.STOPPED
    assert time.monotonic() - started < 30
    assert "stopped" in capfd.readouterr().out


def test_the_guard_leaves_a_limit_the_person_set(capfd, monkeypatch):
    from mem_check import guard

    monkeypatch.setenv("MISE_JOBS", "3")
    monkeypatch.setenv("MEM_CHECK_AVAILABLE_MIB", "8000")
    assert guard.run([sys.executable, "-c", SHOW_LIMITS], poll=0.05) == 0
    assert "3 " in capfd.readouterr().out
