#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""Find the TLA+ tools jar, and fetch it on demand (MSA-I6).

``jar()`` is where the models' runner and the trace validation look for TLC. ``TLA2TOOLS_JAR`` names the jar where it is
set, and is never overridden. Otherwise it is the jar this module installs, under ``LATTICE_FORMAL_ROOT``, by default
``~/.local/share/lattice-formal`` and ``C:/fmx`` on Windows, beside the native Isabelle. Nothing is committed.

``mise run bootstrap:tla-tools`` runs this module, which downloads the pinned release from the TLA+ project's releases and
keeps it only where its SHA-256 is the one pinned here. A check never downloads. Where no jar is found it skips and names
this task, since nothing fails for want of a tool (PRI-79). Behind a mirror that does not serve the release, fetch the jar
by the route that network allows and set ``TLA2TOOLS_JAR``.

Usage: python tools/models/tla_tools.py
"""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from pathlib import Path

VERSION = "1.7.4"
URL = f"https://github.com/tlaplus/tlaplus/releases/download/v{VERSION}/tla2tools.jar"
# Read from the release's jar on 2026-11-24, the release the models' figures were measured on.
SHA256 = "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"
TASK = "mise run bootstrap:tla-tools"


def formal_root() -> Path:
    """The folder native toolchains install under, as the formal-methods installer has it."""
    if os.environ.get("LATTICE_FORMAL_ROOT"):
        return Path(os.environ["LATTICE_FORMAL_ROOT"]).expanduser()
    if os.name == "nt":
        return Path("C:/fmx")
    return Path.home() / ".local" / "share" / "lattice-formal"


def installed() -> Path:
    return formal_root() / "tla" / VERSION / "tla2tools.jar"


def jar() -> tuple[Path | None, str]:
    """The jar to run TLC from, or None with the reason to print beside a skip."""
    named = os.environ.get("TLA2TOOLS_JAR")
    if named:
        return (Path(named), "") if Path(named).is_file() else (None, "TLA2TOOLS_JAR names no file")
    if installed().is_file():
        return installed(), ""
    return None, f"TLA2TOOLS_JAR is not set and no jar is installed. Run `{TASK}`, or set it to the TLA+ tools jar"


def install(url: str = URL, sha256: str = SHA256) -> Path:
    """Download the jar to its place, keeping it only where its digest is the pinned one."""
    target = installed()
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == sha256:
        return target
    with urllib.request.urlopen(url, timeout=120) as response:
        body = response.read()
    found = hashlib.sha256(body).hexdigest()
    if found != sha256:
        raise SystemExit(f"the download from {url} has SHA-256 {found}, not the pinned {sha256}, so nothing was installed")
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    partial.write_bytes(body)
    partial.replace(target)
    return target


def main() -> int:
    target = install()
    print(f"TLA+ tools {VERSION} at {target}")
    if os.environ.get("TLA2TOOLS_JAR"):
        print("TLA2TOOLS_JAR is set, so the checks use the jar it names and not this one")
    return 0


if __name__ == "__main__":
    sys.exit(main())
