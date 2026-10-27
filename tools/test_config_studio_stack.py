# SPDX-License-Identifier: MPL-2.0
"""Tests the stack script's process and download handling, which `up` and `down` rest on."""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_studio_stack as stack  # noqa: E402
import lattice_repo_catalogue  # noqa: E402


def test_a_spawned_process_and_its_children_stop(tmp_path: Path) -> None:
    studio = stack.Stack(lattice_repo_catalogue.find_root())
    studio.run = tmp_path
    child = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); time.sleep(60)"
    pid = studio.spawn("sleeper", [sys.executable, "-c", child])
    assert studio.pid("sleeper") == pid
    assert studio.stop("sleeper")
    deadline = time.monotonic() + 10
    while stack.alive(pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not stack.alive(pid)
    assert studio.pid("sleeper") is None
    assert not studio.stop("sleeper")


def test_a_download_with_the_wrong_checksum_is_refused(tmp_path: Path) -> None:
    source = tmp_path / "release.bin"
    source.write_bytes(b"release")
    url = source.as_uri()
    with pytest.raises(SystemExit, match="Refused"):
        stack.download(url, "0" * 64, tmp_path / "into")
    assert not list((tmp_path / "into").iterdir())
    good = hashlib.sha256(b"release").hexdigest()
    assert stack.download(url, good, tmp_path / "into").read_bytes() == b"release"
