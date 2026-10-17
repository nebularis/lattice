# SPDX-License-Identifier: MPL-2.0

"""The JVM options for a reasoner call (see `mork_compilers.reasoning.jvm_options`). They need no
jar, since the subprocess is replaced."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph

sys.path.insert(0, str(Path(__file__).resolve().parent / "mork_compilers" / "src"))

from mork_compilers import reasoning  # noqa: E402


def test_the_archive_is_built_on_first_use_and_sits_beside_the_jar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LATTICE_REASONING_JVM_OPTIONS", raising=False)
    options = reasoning.jvm_options()
    assert "-XX:+AutoCreateSharedArchive" in options
    assert f"-XX:SharedArchiveFile={reasoning.JAR.with_suffix('.jsa')}" in options
    assert reasoning.JAR.with_suffix(".jsa").parent == reasoning.JAR.parent


def test_logging_is_off_so_a_missing_or_stale_archive_prints_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LATTICE_REASONING_JVM_OPTIONS", raising=False)
    assert "-Xlog:disable" in reasoning.jvm_options()


def test_the_environment_replaces_the_options(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LATTICE_REASONING_JVM_OPTIONS", "-Xmx512m  -XX:+UseParallelGC")
    assert reasoning.jvm_options() == ["-Xmx512m", "-XX:+UseParallelGC"]


def test_an_empty_override_runs_the_jvm_with_its_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LATTICE_REASONING_JVM_OPTIONS", "")
    assert reasoning.jvm_options() == []


def test_run_puts_the_options_before_the_jar_and_reads_the_last_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LATTICE_REASONING_JVM_OPTIONS", raising=False)
    seen: list[list[str]] = []

    def fake_run(command, **kwargs):
        seen.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="a line a JVM might print first\n{\"result\": true}\n")

    monkeypatch.setattr(reasoning.subprocess, "run", fake_run)
    assert reasoning.run("consistent", graphs=[Graph()]) is True
    command = seen[0]
    assert command[0] == "java"
    assert command[1 : 1 + len(reasoning.jvm_options())] == reasoning.jvm_options()
    assert command.index("-jar") > command.index("-XX:+AutoCreateSharedArchive")
    assert command[command.index("-jar") + 2] == "consistent"
