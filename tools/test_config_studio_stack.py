# SPDX-License-Identifier: MPL-2.0
"""Tests the stack script's process and download handling, which `up` and `down` rest on."""

from __future__ import annotations

import hashlib
import socket
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


def test_a_port_another_process_holds_is_refused_before_anything_starts(tmp_path: Path) -> None:
    studio = stack.Stack(lattice_repo_catalogue.find_root())
    studio.run = tmp_path
    with socket.socket() as other:
        other.bind(("127.0.0.1", 0))
        other.listen()
        port = other.getsockname()[1]
        with pytest.raises(SystemExit, match="in use by another process"):
            studio.claim("service", port)
        assert not (tmp_path / "service.pid").exists()
    assert studio.claim("service", port)


def test_workspaces_live_in_the_platform_data_folder_unless_told_otherwise() -> None:
    home = {"HOME": "/h", "USERPROFILE": "C:/Users/a"}
    assert stack.data_dir({"LATTICE_STUDIO_DATA": "/x", **home}) == Path("/x")
    assert stack.data_dir(home, "darwin") == Path("/h/Library/Application Support/LATTICE/studio")
    assert stack.data_dir({**home, "LOCALAPPDATA": "C:/L"}, "win32") == Path("C:/L/LATTICE/studio")
    assert stack.data_dir(home, "linux") == Path("/h/.local/share/lattice/studio")
    assert stack.data_dir({**home, "XDG_DATA_HOME": "/d"}, "linux") == Path("/d/lattice/studio")


def test_the_compose_files_fuseki_configuration_is_the_stacks() -> None:
    root = lattice_repo_catalogue.find_root(None)
    mounted = (root / "deployment" / "compose" / "config-studio" / "fuseki-studio.ttl").read_text()
    assert stack.FUSEKI_CONFIG.replace("{location}", "/data") in mounted
