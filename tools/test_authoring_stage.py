# SPDX-License-Identifier: MPL-2.0
"""Tests `tools/authoring_stage.py` (plan WA10, S10-01)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from authoring_stage import stage  # noqa: E402


def _fake_tree(root: Path) -> None:
    jar = root / "platform" / "authoring-service" / "target" / "authoring-service.jar"
    jar.parent.mkdir(parents=True)
    jar.write_bytes(b"fake jar")

    dist = root / "apps" / "word-authoring-addin" / "dist"
    dist.mkdir(parents=True)
    (dist / "taskpane.html").write_text("<html>taskpane</html>", encoding="utf-8")
    (dist / "harness.html").write_text("<html>harness</html>", encoding="utf-8")

    compose_dir = root / "deployment" / "compose" / "authoring"
    compose_dir.mkdir(parents=True)
    (compose_dir / "service.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (compose_dir / "worker.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

    (root / "workers").mkdir(parents=True)


def test_stage_produces_the_expected_layout(tmp_path: Path) -> None:
    _fake_tree(tmp_path)
    calls: list[list[str]] = []

    stage(tmp_path, pip_runner=lambda args: calls.append(list(args)))

    service_dir = tmp_path / ".build" / "authoring" / "service"
    assert (service_dir / "authoring-service.jar").read_bytes() == b"fake jar"
    assert (service_dir / "Dockerfile").is_file()

    worker_dir = tmp_path / ".build" / "authoring" / "worker"
    assert (worker_dir / "Dockerfile").is_file()
    assert (worker_dir / "wheelhouse").is_dir()

    addin_dir = tmp_path / ".build" / "authoring" / "addin"
    assert (addin_dir / "taskpane.html").read_text(encoding="utf-8") == "<html>taskpane</html>"
    assert (addin_dir / "harness.html").is_file()

    assert len(calls) == 2
    assert calls[0][0] == "wheel"
    assert calls[1][0] == "download"


def test_stage_removes_and_recreates_only_the_build_authoring_directory(tmp_path: Path) -> None:
    _fake_tree(tmp_path)
    sentinel = tmp_path / ".build" / "unrelated.txt"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("keep me", encoding="utf-8")
    stale = tmp_path / ".build" / "authoring" / "stale.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale", encoding="utf-8")

    stage(tmp_path, pip_runner=lambda args: None)

    assert sentinel.read_text(encoding="utf-8") == "keep me"
    assert not stale.exists()


def test_a_missing_jar_exits_2_naming_build_authoring(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dist = tmp_path / "apps" / "word-authoring-addin" / "dist"
    dist.mkdir(parents=True)
    (dist / "taskpane.html").write_text("<html></html>", encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        stage(tmp_path, pip_runner=lambda args: None)

    assert excinfo.value.code == 2
    assert "build:authoring" in capsys.readouterr().err


def test_a_missing_taskpane_html_exits_2_naming_build_authoring(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    jar = tmp_path / "platform" / "authoring-service" / "target" / "authoring-service.jar"
    jar.parent.mkdir(parents=True)
    jar.write_bytes(b"fake jar")

    with pytest.raises(SystemExit) as excinfo:
        stage(tmp_path, pip_runner=lambda args: None)

    assert excinfo.value.code == 2
    assert "build:authoring" in capsys.readouterr().err
