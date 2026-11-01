# SPDX-License-Identifier: MPL-2.0
"""The report's form, the timer and the comparison's arithmetic and marks. They start nothing. Test IDs are SR-Tn."""

from __future__ import annotations

import getpass
import json
import socket
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lattice_testing_studio_harness import compare, reports
from lattice_testing_studio_harness._tools import catalogue
from lattice_testing_studio_harness.reports import ReportError

KIND = {"os": "Darwin", "os_version": "26.0", "architecture": "arm64", "processor_model": "Chip", "processor_count": 8, "memory_bytes": 17179869184,
        "java": "21.0.1", "python": "3.14.7", "power_mode": "powermode 0, lowpowermode 0", "load_average_at_start": [1.0, 1.0, 1.0]}
WHEN = datetime(2026, 10, 31, 14, 2, 11, tzinfo=timezone.utc)


def report(commit: str = "4029bd0f", *measures: dict, kind: dict | None = None, when: datetime = WHEN) -> dict:
    return reports.build("studio-api", commit, list(measures) or [reports.measure("save", "ms", [10, 11, 12])], dict(kind or KIND), when)


def test_sr_t1_a_report_has_the_form_the_schema_describes() -> None:
    built = report()
    assert built["date"] == "2026-10-31T14:02:11Z" and built["commit"] == "4029bd0f"
    m = built["measures"][0]
    assert (m["median"], m["iqr"], m["min"], m["max"]) == (11, [10.5, 11.5], 10, 12)
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((catalogue.find_root() / "benchmark" / "reports" / "report.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(built, schema)
    bad = {**built, "commit": "not a hash"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


@pytest.mark.parametrize("change", [
    lambda r: r.pop("machine"), lambda r: r.update(commit="zz"), lambda r: r.update(date="yesterday"), lambda r: r.update(measures=[]),
    lambda r: r["measures"][0].update(median=99), lambda r: r["measures"][0].update(min=0), lambda r: r["machine"].update(hostname="x"),
    lambda r: r["measures"].append(dict(r["measures"][0])), lambda r: r["measures"][0].update(repeats=[]),
])
def test_sr_t2_a_malformed_report_is_refused(change) -> None:  # type: ignore[no-untyped-def]
    broken = report()
    change(broken)
    with pytest.raises(ReportError):
        reports.validate(broken)


def test_sr_t3_the_machine_names_a_kind_and_never_a_host_or_a_user() -> None:
    kind = reports.machine()
    assert set(kind) == set(reports.MACHINE_KEYS) | {"load_average_at_start"}
    text = json.dumps(kind)
    for private in {socket.gethostname(), socket.gethostname().split(".")[0], getpass.getuser()} - {""}:
        assert private not in text
    reports.validate(report(kind=kind))


def test_sr_t4_a_report_is_written_under_its_benchmark_and_sorts_by_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reports, "reports_dir", lambda root=None: tmp_path)
    later = datetime(2026, 11, 1, 9, 0, 0, tzinfo=timezone.utc)
    new, old = reports.write(report("bbbbbbbb", when=later)), reports.write(report("aaaaaaaa"))
    assert old.name == "20261031T140211Z-aaaaaaaa.json" and old.parent == tmp_path / "studio-api"
    assert reports.listing("studio-api") == [old, new]
    assert reports.load(old)["commit"] == "aaaaaaaa"


def test_sr_t5_the_timer_discards_its_warm_up_repeats() -> None:
    calls = []
    out = reports.time_ms(lambda: calls.append(1), repeats=5, warmup=2)
    assert len(calls) == 7 and len(out) == 5 and all(v >= 0 for v in out)


def test_sr_t6_quartiles_and_median() -> None:
    m = reports.measure("x", "ms", [4, 1, 3, 2, 5])
    assert (m["median"], m["iqr"], m["min"], m["max"]) == (3, [2, 4], 1, 5)
    assert reports.measure("x", "ms", [7])["iqr"] == [7, 7]


def test_sr_t7_the_change_is_in_percent() -> None:
    assert compare.change_percent(10, 15) == 50 and compare.change_percent(20, 10) == -50 and compare.change_percent(0, 1) is None


def test_sr_t8_a_change_is_marked_only_outside_both_runs_ranges() -> None:
    base = reports.measure("x", "ms", [10, 11, 12])
    far = reports.measure("x", "ms", [20, 21, 22])
    near = reports.measure("x", "ms", [10.5, 11, 12])
    wide = reports.measure("x", "ms", [1, 15, 30])
    assert compare.outside_noise(base, far) and compare.outside_noise(far, base)
    assert not compare.outside_noise(base, near)
    assert not compare.outside_noise(base, wide), "the base median lies inside the wide run's range"


def test_sr_t9_rows_pair_measures_by_name_and_note_the_rest() -> None:
    base = report("aaaaaaaa", reports.measure("save", "ms", [10, 10, 10]), reports.measure("gone", "ms", [1]), reports.measure("unit", "ms", [1]))
    head = report("bbbbbbbb", reports.measure("save", "ms", [15, 15, 15]), reports.measure("new", "ms", [1]), reports.measure("unit", "s", [1]))
    body, notes = compare.rows(base, head)
    assert [(r["name"], r["percent"], r["marked"]) for r in body] == [("save", 50.0, True)]
    assert sorted(notes) == ["gone is only in the base report", "new is only in the head report",
                             "unit is in ms in the base and s in the head, so it is not compared"]


def test_sr_t10_the_table_warns_when_the_machines_differ_and_reminds_of_power_and_load() -> None:
    other = {**KIND, "processor_count": 16}
    text = compare.table(report("aaaaaaaa"), report("bbbbbbbb", kind=other))
    assert "WARNING: the machines differ in processor_count" in text and "STD-040" in text and "power mode" in text
    assert "WARNING" not in compare.table(report("aaaaaaaa"), report("bbbbbbbb"))


def test_sr_t11_compare_defaults_to_the_last_two_reports_and_exits_zero_on_a_slowdown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(reports, "reports_dir", lambda root=None: tmp_path)
    reports.write(report("aaaaaaaa", reports.measure("save", "ms", [10, 10, 10])))
    reports.write(report("bbbbbbbb", reports.measure("save", "ms", [90, 90, 90]), when=datetime(2026, 11, 1, tzinfo=timezone.utc)))
    assert compare.main(["studio-api"]) == 0
    out = capsys.readouterr().out
    assert "base aaaaaaaa" in out and "head bbbbbbbb" in out and "+800.0%" in out


def test_sr_t12_compare_exits_one_on_a_malformed_or_missing_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(reports, "reports_dir", lambda root=None: tmp_path)
    assert compare.main(["studio-api"]) == 1
    reports.write(report("aaaaaaaa"))
    assert compare.main(["studio-api"]) == 1, "one report has nothing before it"
    (tmp_path / "studio-api" / "20261102T000000Z-cccccccc.json").write_text("{not json", encoding="utf-8")
    assert compare.main(["studio-api"]) == 1
    assert "benchmark:compare" in capsys.readouterr().err
