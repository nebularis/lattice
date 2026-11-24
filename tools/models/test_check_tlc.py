# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""The TLC runner's sizing and its verdict, without Java or TLC (MSA-I6): the heap budget, the heap each run gets, the skip
that names both figures and never starts the run, and the comparison of TLC's verdict with the manifest's."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_tlc  # noqa: E402
from check_tlc import Configuration, budget_mb, judge, plan  # noqa: E402

COMPLETED = "Model checking completed. No error has been found.\n"


def configuration(name: str = "C", *, expect: str = "no error", prop: str | None = None, kind: str | None = None,
                  peak: int | None = 20, limit: str | None = None) -> Configuration:
    return Configuration(name, "M", f"{name}.cfg", "base", expect, prop, kind, peak, limit, None)


# The budget.

def test_budget_is_a_quarter_of_physical_memory():
    assert budget_mb(65_536, 40_000, None)[0] == 16_384


def test_budget_is_never_above_what_is_available():
    budget, text = budget_mb(65_536, 3_000, None)
    assert budget == 3_000
    assert "the 3,000 MB available" in text


def test_the_variable_lowers_the_budget():
    budget, text = budget_mb(65_536, 40_000, "2048")
    assert budget == 2_048
    assert check_tlc.BUDGET_VARIABLE in text


def test_the_variable_never_raises_the_budget():
    assert budget_mb(8_192, None, "4096")[0] == 2_048


def test_the_variable_must_be_a_number():
    with pytest.raises(SystemExit):
        budget_mb(8_192, None, "2g")


# The heap of a run.

def test_a_run_gets_twice_its_peak_and_64_mb_in_steps_of_32():
    assert configuration(peak=132).heap_mb() == 352
    assert configuration(peak=1_005).heap_mb() == 2_080


def test_a_small_run_gets_at_least_256_mb():
    assert configuration(peak=15).heap_mb() == 256


def test_a_configuration_with_no_peak_has_no_heap():
    assert configuration(peak=None).heap_mb() is None


# The plan.

def test_a_configuration_over_the_budget_is_skipped_with_both_figures_and_never_started():
    big, small = configuration("Big", peak=132), configuration("Small", peak=15)
    planned, skipped = plan([big, small], 300)
    assert planned == [(small, 256)]
    assert [(r.status, r.configuration.name, r.text) for r in skipped] == [
        ("SKIP", "Big", "needs a heap of 352 MB, and the budget is 300 MB")]


def test_a_configuration_at_the_budget_runs():
    planned, skipped = plan([configuration(peak=132)], 352)
    assert [heap for _, heap in planned] == [352]
    assert skipped == []


def test_a_configuration_stopped_at_the_limit_or_never_measured_is_skipped():
    limited, unmeasured = configuration("Limited", peak=None, limit="30 minutes"), configuration("Unmeasured", peak=None)
    planned, skipped = plan([limited, unmeasured], 16_384)
    assert planned == []
    assert "stopped at machine S's limit (30 minutes)" in skipped[0].text
    assert "states no peak heap" in skipped[1].text


def test_heap_mb_measures_every_configuration_within_the_budget():
    limited, unmeasured, big = configuration("L", peak=None, limit="30 minutes"), configuration("U", peak=None), configuration("B", peak=132)
    planned, skipped = plan([limited, unmeasured, big], 4_096, measure=4_096)
    assert [(c.name, heap) for c, heap in planned] == [("L", 4_096), ("U", 4_096), ("B", 4_096)]
    planned, skipped = plan([big], 2_048, measure=4_096)
    assert planned == [] and skipped[0].text == "needs a heap of 4,096 MB, and the budget is 2,048 MB"


def test_runs_together_never_hold_more_than_the_budget():
    budget = check_tlc.Budget(300)
    budget.take(200)
    taken = threading.Event()
    second = threading.Thread(target=lambda: (budget.take(200), taken.set()))
    second.start()
    assert not taken.wait(0.2)
    budget.give(200)
    assert taken.wait(5)
    second.join()
    assert budget.used == 200


# The verdict.

def test_no_error_as_expected_passes():
    assert judge(configuration(), COMPLETED) == ("PASS", "no error")


def test_the_violation_expected_passes():
    c = configuration(expect="violated", prop="NoLostWrite", kind="invariant")
    assert judge(c, "Error: Invariant NoLostWrite is violated.\n") == ("PASS", "invariant NoLostWrite violated")


def test_an_action_property_and_a_temporal_violation_pass_when_expected():
    step = configuration(expect="violated", prop="VersionStepsByOne", kind="action")
    assert judge(step, "Error: Action property VersionStepsByOne is violated.\n")[0] == "PASS"
    live = configuration(expect="violated", prop="EventuallyApplied", kind="temporal")
    assert judge(live, "Error: Temporal properties were violated.\n") == ("PASS", "temporal properties violated")


def test_a_violation_where_none_is_expected_fails():
    assert judge(configuration(), "Error: Invariant NoLostWrite is violated.\n") == (
        "FAIL", "TLC printed invariant NoLostWrite violated, expected no error")


def test_no_error_where_a_violation_is_expected_fails():
    c = configuration(expect="violated", prop="NoTornRead", kind="invariant")
    assert judge(c, COMPLETED) == ("FAIL", "TLC printed no error, expected invariant NoTornRead violated")


def test_another_property_violated_fails():
    c = configuration(expect="violated", prop="NoTornRead", kind="invariant")
    assert judge(c, "Error: Invariant AThenB is violated.\n")[0] == "FAIL"


def test_a_run_out_of_heap_is_stopped_and_does_not_fail():
    assert judge(configuration(), "Error: Java ran out of memory during liveness checking.\n") == ("STOP", "ran out of its heap")


def test_no_verdict_fails():
    assert judge(configuration(), "Fatal errors while parsing TLA+ spec in file M\n")[0] == "FAIL"


# The peak heap and the manifest.

def test_the_peak_heap_is_the_largest_heap_before_a_collection(tmp_path: Path):
    log = tmp_path / "gc.log"
    log.write_text("[0.2s][info][gc] GC(0) Pause Young (Allocation Failure) 16M->3M(245M) 1.2ms\n"
                   "[0.5s][info][gc] GC(1) Pause Full (Ergonomics) 1G->200M(1500M) 9.0ms\n"
                   "[0.9s][info][gc] GC(2) Pause Young (Allocation Failure) 219M->204M(1500M) 1.1ms\n",
                   encoding="utf-8", newline="\n")
    assert check_tlc.peak_heap(log) == 1_024


def test_the_counts_are_the_last_tlc_printed_progress_lines_included():
    output = ("Progress(18) at 2026-11-24 01:17:03: 3,496,784 states generated (3,350,894 s/min), 1,640,647 distinct states found "
              "(1,572,653 ds/min), 786,579 states left on queue.\n"
              "Progress(22) at 2026-11-24 01:45:07: 31,475,339 states generated (1,539,412 s/min), 15,754,453 distinct states found "
              "(811,142 ds/min), 5,894,824 states left on queue.\n")
    assert check_tlc.last_counts(output) == ("31,475,339", "15,754,453")
    assert check_tlc.last_counts("2,411 states generated, 1,479 distinct states found, 0 states left on queue.\n") == ("2,411", "1,479")
    assert check_tlc.last_counts("Parsing file M.tla\n") is None


def test_the_manifest_has_one_entry_for_each_configuration():
    catalogue = check_tlc.load()
    models = catalogue.root / catalogue.area("tools") / "models" / check_tlc.MODELS
    entries = check_tlc.read_manifest(models / check_tlc.MANIFEST)
    names = [c.name for c in entries]
    assert len(names) == len(set(names))
    assert sorted(f"{c.name}.cfg" for c in entries) == sorted(c.config for c in entries)
    assert sorted(c.config for c in entries) == sorted(p.name for p in models.glob("*.cfg"))
    assert all((models / f"{c.module}.tla").is_file() for c in entries)
    assert all(c.peak_heap_mb is not None or c.limit for c in entries)
    assert sum(c.tier == "base" for c in entries) == 86
