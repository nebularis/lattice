# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The native Jena caller's own tests (ADR-A124, PRI-63): it passes on the Python benchmark's corpus and balances, and a run that reports a wrong balance fails with a non-zero exit."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ledger-credit-kinds"))

import check  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("mvn") is None or shutil.which("java") is None, reason="needs mvn and java")


def run_java(directory: Path, report: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["mvn", "-q", "-f", str(HERE / "pom.xml"), "compile", "exec:exec", f"-Dkinds.dir={directory}", f"-Dkinds.report={report}", "-Dkinds.forms=optional"],
                          capture_output=True, text=True, check=False, timeout=600)


def test_jv1_the_java_run_passes_on_the_emitted_corpus_and_reads_the_jena_version(tmp_path):
    check.emit(tmp_path, (400,), (0.30,))
    done = run_java(tmp_path, tmp_path / "report.json")
    assert done.returncode == 0, done.stdout + done.stderr
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert data["environment"]["jena"] and {m["backend"] for m in data["measurements"]} == {"jena-memory (java)", "jena-tdb2 (java)"}


@pytest.mark.parametrize("field", ["balance", "rows"])
def test_jv2_a_java_run_that_reports_a_wrong_balance_or_count_fails(tmp_path, field):
    check.emit(tmp_path, (400,), (0.30,))
    path = tmp_path / "expected.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["corpora"][0]["reads"][0][field] += 1
    path.write_text(json.dumps(data), encoding="utf-8")
    done = run_java(tmp_path, tmp_path / "report.json")
    assert done.returncode != 0 and "WRONG RESULT" in done.stdout + done.stderr
    assert not (tmp_path / "report.json").exists()


def test_jv3_a_wrong_shortcut_balance_fails_the_java_run(tmp_path):
    check.emit(tmp_path, (400,), (0.30,))
    path = tmp_path / "expected.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["corpora"][0]["shortcut"][0]["balance"] += 1
    path.write_text(json.dumps(data), encoding="utf-8")
    done = run_java(tmp_path, tmp_path / "report.json")
    assert done.returncode != 0 and "shortcut" in done.stdout + done.stderr
