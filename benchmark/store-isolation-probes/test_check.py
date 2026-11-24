# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The isolation probes' own tests: the expectations, the verdict, the reading of the Jena arm's results, and a few PostgreSQL
probes on the fixture's server, which skip, naming the package, where it is absent."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import check


def test_every_expected_probe_states_its_assumption_and_every_assumption_is_probed():
    assert {k[0] for k in check.EXPECTED} == set(check.ASSUMPTIONS)


def test_every_postgresql_probe_has_a_runner():
    for probe, store, _, _ in check.EXPECTED:
        if store == check.PG and probe != "ISO-02":
            assert hasattr(check.PgArm, check.PG_RUNNERS[probe])


def test_every_jena_row_is_one_the_java_arm_produces():
    """The Java arm names each row it writes with `new Tally(probe, store, form, mode)`, so its forms and modes must be `EXPECTED`'s."""
    source = (check.HERE / "src" / "main" / "java" / "org" / "nebularis" / "lattice" / "benchmark" / "isolation" / "IsolationProbes.java").read_text(encoding="utf-8")
    calls = {(m[0], m[1]) for m in re.findall(r'new Tally\("(ISO-\d\d)", "(fuseki|tdb2)"', source)}
    assert calls == {(k[0], k[1]) for k in check.EXPECTED if k[1] in (check.FUSEKI, check.TDB2)}
    for _, store, form, mode in (k for k in check.EXPECTED if k[1] in (check.FUSEKI, check.TDB2)):
        assert f'"{form}"' in source and f'"{mode}"' in source, (store, form, mode)


def row(probe="ISO-01", store=check.PG, form="guarded", mode=check.RC, reps=5, anomalies=0, counts=None):
    return check.Row(probe, store, "v", form, mode, reps, anomalies, {}, counts or {})


def test_a_row_expected_never_passes_only_with_no_anomaly():
    assert check.verdict(row())[0]
    ok, why = check.verdict(row(anomalies=1))
    assert not ok and "expected never" in why


def test_a_row_expected_always_passes_only_when_every_repetition_shows_it():
    assert check.verdict(row(form="unguarded", anomalies=5))[0]
    ok, why = check.verdict(row(form="unguarded", anomalies=4))
    assert not ok and "expected always" in why


def test_a_row_with_no_expectation_or_no_repetition_fails():
    assert not check.verdict(row(form="no such form"))[0]
    assert not check.verdict(row(reps=0))[0]


def test_a_probe_that_never_ran_beside_another_client_fails():
    ok, why = check.verdict(row(probe="ISO-02", reps=1, counts={"races lost": 0}))
    assert not ok and "races lost" in why
    assert check.verdict(row(probe="ISO-02", reps=1, counts={"races lost": 3}))[0]
    ok, _ = check.verdict(row(probe="ISO-06", store=check.FUSEKI, form="one query", mode="two clients", counts={"reads while the writes ran": 0}))
    assert not ok


def test_an_expected_row_no_run_produced_is_listed():
    produced = [row(), row(form="unguarded", anomalies=5)]
    gone = check.missing(produced, check.PG, "v")
    assert ("ISO-01", check.PG, "guarded", check.RC) not in gone
    assert ("ISO-01", check.PG, "guarded", check.RR) in gone


def test_the_jena_results_are_read_into_rows(tmp_path: Path):
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"environment": {"jena": "5.1.0"}, "rows": [
        {"probe": "ISO-07", "store": "fuseki", "form": "a new request from another client", "mode": "two clients", "reps": 3, "anomalies": 0,
         "outcomes": {"seen": 3}, "counts": {}}]}), encoding="utf-8")
    rows, env = check.read_jena(path, "5.1.0")
    assert env == {"jena": "5.1.0"} and rows[0].key == ("ISO-07", "fuseki", "a new request from another client", "two clients")
    assert check.verdict(rows[0])[0]


def test_the_jena_arm_is_skipped_with_the_reason_where_maven_is_absent(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(check.shutil, "which", lambda tool: None)
    assert "mvn" in check.jena_absent()


# ---- a few PostgreSQL probes on the fixture's server ------------------------------------------------------------------

@pytest.fixture
def arm(postgres_server):
    arm = check.PgArm(postgres_server, postgres_server.create_database())
    yield arm
    arm.close()


def test_iso01_a_guarded_write_refuses_the_second_writer_and_an_unguarded_one_loses_an_update(arm):
    assert arm.cas("guarded", check.RC) == ("the second refused by its guard", False)
    assert arm.cas("guarded", check.RR) == ("the second refused: serialization failure", False)
    assert arm.cas("unguarded", check.RC) == ("both applied from the same version", True)


def test_iso10_one_statement_returns_the_version_its_snapshot_held_under_read_committed(arm):
    assert arm.refusal("one statement, version from its snapshot", check.RC) == ("refused, and the version returned is 0, the one expected", True)
    assert arm.refusal("locking read before the guard", check.RC) == ("refused, and the version returned is 1", False)


def test_iso11_write_skew_appears_below_serializable_and_not_at_it(arm):
    assert arm.write_skew("check by an earlier read", check.RR) == ("both taken off", True)
    outcome, anomaly = arm.write_skew("check by an earlier read", check.SER)
    assert not anomaly and "serialization failure" in outcome
