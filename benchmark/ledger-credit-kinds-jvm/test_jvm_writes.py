# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The native writer's own tests (ADR-A124, PRI-63): the audit of an export fails on a stored cut that differs from the replay and on a duplicate revision, a Java run fails on a preload that is not the corpus, and
a full small run passes and is audited."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ledger-credit-kinds"))

import check as ck  # noqa: E402
import writes  # noqa: E402

COUNT = 1_000  # the smallest corpus at 30% credits in which a ceiling binds, so cuts exist


def exported(tmp_path: Path, live: int) -> tuple[Path, int, int]:
    """A store holding the preload and `live` guarded writes, dumped as N-Quads by Python alone. Returns the file, the base revision and the commits."""
    with writes.opened("oxigraph memory") as backend:
        corpus, base = writes.preload(backend, COUNT)
        writer, commits = writes.Live(backend, len(corpus.positions), True), 0
        for n, request in enumerate(writes.requests(live, writes.SHARE, ck.SEED + 7)):
            commits += not writes.write_one(writer, request, f"W{n}", retry=False)[0].refused
        path = tmp_path / "export.nq"
        path.write_bytes(backend.store.dump(format=ck.ox.RdfFormat.N_QUADS))
    return path, base, commits


def test_jw1_the_audit_passes_on_an_export_of_the_preload_and_its_writes(tmp_path):
    path, base, commits = exported(tmp_path, 6)
    result = writes.audit_export(path, base, True, commits)
    assert result["live"] == commits > 0 and result["dense"] and result["cuts_differ"] == 0


def test_jw2_the_audit_fails_on_an_export_whose_stored_cut_differs_from_the_replay(tmp_path):
    path, base, commits = exported(tmp_path, 3)
    text = path.read_text(encoding="utf-8")
    cut = re.search(r'(<[^>]*cutValue> ")(\d+)(")', text)
    assert cut, "the corpus holds no cut, so the audit could not be told"
    path.write_text(text[:cut.start(2)] + str(int(cut.group(2)) + 1) + text[cut.end(2):], encoding="utf-8")
    with pytest.raises(ck.WrongResult):
        writes.audit_export(path, base, True, commits)
    assert writes.audit_export(path, base, False, commits)["cuts_differ"] > 0


def test_jw3_the_audit_fails_on_an_export_with_a_duplicate_revision(tmp_path):
    path, base, commits = exported(tmp_path, 4)
    assert commits >= 2
    text = path.read_text(encoding="utf-8")
    last = f'position> "{base + commits}"'
    assert last in text
    path.write_text(text.replace(last, f'position> "{base + commits - 1}"'), encoding="utf-8")
    with pytest.raises(ck.WrongResult):
        writes.audit_export(path, base, True, commits)
    result = writes.audit_export(path, base, False, commits)
    assert result["duplicate_positions"] == 1 and not result["dense"]


def test_jw4_a_store_whose_probe_lost_a_guarded_update_is_not_held_to_the_replay():
    kept = {"probe": {"guarded": [{"store": "memory", "threads": 2, "markers": 10, "target": 10, "multi_marker_revisions": 0}, {"store": "tdb2", "threads": 2, "markers": 12, "target": 10, "multi_marker_revisions": 2}]}}
    assert writes.probe_keeps_guard(kept, "memory") and not writes.probe_keeps_guard(kept, "tdb2")
    assert not writes.probe_keeps_guard({"probe": {"guarded": []}}, "memory")


needs_java = pytest.mark.skipif(shutil.which("mvn") is None or shutil.which("java") is None, reason="needs mvn and java")


def run_java(directory: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["mvn", "-q", "-f", str(HERE / "pom.xml"), "compile", "exec:exec", "-Dexec.mainClass=org.nebularis.lattice.benchmark.creditkinds.LedgerWrites", f"-Dwrites.dir={directory}",
                           f"-Dwrites.report={directory / 'writes-java.json'}"], capture_output=True, text=True, check=False, timeout=900)


def tiny(directory: Path) -> None:
    small = writes.store_plan((10, 5, 1), 12, 16, 1)
    writes.emit_jvm(directory, sizes=(COUNT,), preload_count=COUNT, threads=(2,), stores={"memory": small, "tdb2": small})


@needs_java
def test_jw5_a_small_native_run_passes_and_its_exports_pass_the_python_audit(tmp_path, monkeypatch):
    tiny(tmp_path)
    done = run_java(tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    monkeypatch.setenv("LEDGER_WRITES_REPORT_DIR", str(tmp_path))
    assert writes.audit_jvm(tmp_path) == 0
    report = json.loads((tmp_path / "writes-report.json").read_text(encoding="utf-8"))
    assert {r["store"] for r in report["stress"]} == {"memory", "tdb2"} and all(r["audit"]["live"] == r["commits"] for r in report["single"] + report["stress"])
    assert all(r["asserted"] == (r["guarded"] and report["guard_kept"][r["store"]]) for r in report["stress"])


@needs_java
def test_jw6_a_preload_that_is_not_the_corpus_fails_the_java_run(tmp_path):
    tiny(tmp_path)
    path = tmp_path / "writes-input.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["preloads"][str(COUNT)]["stored"] += 1
    path.write_text(json.dumps(data), encoding="utf-8")
    done = run_java(tmp_path)
    assert done.returncode != 0 and "WRONG RESULT" in done.stdout + done.stderr
    assert not (tmp_path / "writes-java.json").exists()
