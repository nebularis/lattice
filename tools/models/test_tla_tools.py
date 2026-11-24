# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""The TLA+ tools jar is found where it is named or installed, and a download is kept only at its pinned digest."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tla_tools  # noqa: E402


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("LATTICE_FORMAL_ROOT", str(tmp_path / "root"))
    monkeypatch.delenv("TLA2TOOLS_JAR", raising=False)
    return tmp_path


def test_a_download_with_the_pinned_digest_is_installed_and_found(root):
    source = root / "served.jar"
    source.write_bytes(b"a jar")
    target = tla_tools.install(source.as_uri(), hashlib.sha256(b"a jar").hexdigest())
    assert target == tla_tools.installed() and target.read_bytes() == b"a jar"
    assert tla_tools.jar() == (target, "")


def test_a_download_with_another_digest_is_refused_and_nothing_is_installed(root):
    source = root / "served.jar"
    source.write_bytes(b"another jar")
    with pytest.raises(SystemExit, match="not the pinned"):
        tla_tools.install(source.as_uri(), hashlib.sha256(b"a jar").hexdigest())
    assert not tla_tools.installed().exists()
    found, reason = tla_tools.jar()
    assert found is None and tla_tools.TASK in reason


def test_the_named_jar_wins_and_a_name_with_no_file_is_not_replaced(root, monkeypatch):
    tla_tools.installed().parent.mkdir(parents=True)
    tla_tools.installed().write_bytes(b"installed")
    named = root / "named.jar"
    monkeypatch.setenv("TLA2TOOLS_JAR", str(named))
    assert tla_tools.jar() == (None, "TLA2TOOLS_JAR names no file")
    named.write_bytes(b"named")
    assert tla_tools.jar() == (named, "")
