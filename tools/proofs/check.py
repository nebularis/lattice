#!/usr/bin/env python3
"""Build every tools/proofs/<layer>/ session natively and run the gate (ADR-A-FM2).

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
SESSION_RE = re.compile(r"^session\s+(\S+)\s*(?:\(.*\))?\s*(?:in\s+\S+\s*)?=", re.MULTILINE)


def session_names(root_file: Path) -> list[str]:
    return SESSION_RE.findall(root_file.read_text(encoding="utf-8"))


def layers(selected: list[str]) -> list[Path]:
    if selected:
        return [HERE / name for name in selected]
    return sorted(p.parent for p in HERE.glob("*/ROOT"))


def main(argv: list[str]) -> int:
    ok = True
    for layer_dir in layers(argv):
        root_file = layer_dir / "ROOT"
        if not root_file.is_file():
            print(f"SKIP {layer_dir.name}: no ROOT file", file=sys.stderr)
            ok = False
            continue
        for session in session_names(root_file):
            print(f"-- building {layer_dir.name}/{session} (native) --")
            result = subprocess.run(
                [
                    sys.executable, str(DRIVER),
                    "--route", "native", "--workdir", str(layer_dir),
                    "isabelle", "build", "-d", ".", "-o", "timeout=90", session,
                ],
                cwd=REPO_ROOT,
            )
            ok = ok and result.returncode == 0
        print(f"-- gate: {layer_dir.name} --")
        result = subprocess.run([sys.executable, str(HERE / "gate.py"), str(layer_dir)])
        ok = ok and result.returncode == 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
