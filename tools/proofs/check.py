#!/usr/bin/env python3
"""Build every tools/proofs/<layer>/ session natively and run the gate (ADR-A-FM2).

The prelude, tools/proofs/base/'s LatticeBase, is built first, and every layer's build is given
`-d base` beside its own directory, so its sessions find the prelude they parent on (ADR-A-FM2's
addendum of 2026-11-08).
`isabelle build` builds the prelude's heap where it is missing and rebuilds it where its sources
changed, by its own digests, so `-f` is never passed (STD-324).

For each layer subdirectory with a ROOT file: parses the session name(s) it declares, builds
each with `isabelle build` on the native route (spikes/formal-prover/env/driver.py's existing
native-Isabelle plumbing; no image route exists for Isabelle in this programme, see the
formal-methods status record), then runs gate.py against that layer's directory.

Usage: python tools/proofs/check.py [layer ...]   (default: every layer with a ROOT file)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
DRIVER = REPO_ROOT / "spikes" / "formal-prover" / "env" / "driver.py"
BASE = HERE / "base"
SESSION_RE = re.compile(r"^session\s+(\S+)\s*(?:\(.*\))?\s*(?:in\s+\S+\s*)?=", re.MULTILINE)
# Each session's ROOT states its own build timeout, a layer's narrow so a looping proof fails fast
# and the prelude's wide for its first build from source. A `-o timeout=` here would change every
# session's options, the prelude's included, and so force the prelude's heap to be rebuilt.


def session_names(root_file: Path) -> list[str]:
    return SESSION_RE.findall(root_file.read_text(encoding="utf-8"))


def layers(selected: list[str]) -> list[Path]:
    if selected:
        return [HERE / name for name in selected if HERE / name != BASE]
    return sorted(p.parent for p in HERE.glob("*/ROOT") if p.parent != BASE)


def build(directory: Path, session: str, dirs: list[str]) -> bool:
    # Every build runs from tools/proofs and names the prelude as `-d base`. A build run from the
    # prelude's own directory as `-d .` was not taken to be the same session as `-d ../base` from a
    # layer's, so each layer rebuilt the prelude's heap (FME-0's Validation Pack).
    print(f"-- building {directory.name}/{session} (native) --", flush=True)
    args = ["isabelle", "build"]
    for d in dirs:
        args += ["-d", d]
    result = subprocess.run(
        [sys.executable, str(DRIVER), "--route", "native", "--workdir", str(HERE), *args, session],
        cwd=REPO_ROOT,
    )
    return result.returncode == 0


def gate(directory: Path) -> bool:
    print(f"-- gate: {directory.name} --", flush=True)
    return subprocess.run([sys.executable, str(HERE / "gate.py"), str(directory)]).returncode == 0


def main(argv: list[str]) -> int:
    ok = True
    for session in session_names(BASE / "ROOT"):
        ok = build(BASE, session, ["base"]) and ok
    ok = gate(BASE) and ok
    if not ok:
        print("the prelude did not build, so no layer session was built", file=sys.stderr)
        return 1
    for layer_dir in layers(argv):
        root_file = layer_dir / "ROOT"
        if not root_file.is_file():
            print(f"SKIP {layer_dir.name}: no ROOT file", file=sys.stderr)
            ok = False
            continue
        for session in session_names(root_file):
            ok = build(layer_dir, session, ["base", layer_dir.name]) and ok
        ok = gate(layer_dir) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
