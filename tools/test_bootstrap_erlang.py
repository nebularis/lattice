"""bootstrap:erlang (plan vyvid-migration, VM-12): the pinned Erlang is found, or installed with the disable lifted."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bootstrap_erlang as be  # noqa: E402


def done(out: str = "", code: int = 0):
    return subprocess.CompletedProcess([], code, out, "")


def test_the_pin_is_read_from_mise_toml():
    assert be.pinned("[tools]\nerlang = \"27\"\n") == "27"


def test_an_erl_on_the_path_is_used_and_nothing_is_installed():
    calls = []
    got = be.ensure("27", which=lambda _: "/usr/bin/erl", run=lambda *a, **k: calls.append(a) or done())
    assert got == Path("/usr/bin")
    assert calls == []


def test_without_erl_the_pin_is_installed_with_erlang_not_disabled(tmp_path):
    seen = []

    def run(argv, **kw):
        seen.append((argv, kw["env"]["MISE_DISABLE_TOOLS"]))
        return done(str(tmp_path) if argv[1] == "where" else "")

    got = be.ensure("27", which=lambda _: None, run=run)
    assert got == tmp_path / "bin"
    assert [a[1] for a, _ in seen] == ["install", "where"]
    assert all("erlang" not in disabled for _, disabled in seen)


def test_a_failed_install_returns_none():
    assert be.ensure("27", which=lambda _: None, run=lambda *a, **k: done("", 1)) is None


def test_a_lookup_finds_an_installed_erlang_without_installing():
    assert be.find("27", which=lambda _: None, run=lambda a, **k: done("/m/erlang/27")) == Path("/m/erlang/27/bin")
    assert be.find("27", which=lambda _: None, run=lambda a, **k: done("", 1)) is None
