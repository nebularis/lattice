#!/usr/bin/env python3
"""The proof gate script (ADR-A-FM2; carried over from spikes/formal-prover/gate.py, track D's
spike, unchanged in design). For one layer's directory under tools/proofs/:

1. Recomputes each claim's statement digest from its theory source, between
   ``(* GATE:BEGIN <subject> *)`` and ``(* GATE:END *)`` markers, and fails on an unreviewed
   mismatch against the committed claim (an unreviewed restatement under an unchanged name).
2. Scans every theory source for an unreviewed ``Admitted``/``admit``/``sorry``/``oracle``/
   ``axiomatization`` outside files under a ``defects/`` directory, where such a marker is the
   defect itself, not a gate failure.
3. Prints one law-report row per claim.

Usage: python gate.py <layer-dir> [--defect-ok]

``--defect-ok`` relaxes rule 1 (a defect run states a wrong digest on purpose); it still enforces
rule 2 outside ``defects/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

BANNED = re.compile(r"\b(Admitted|admit|sorry|oracle|axiomatization)\b")
MARKER = re.compile(r"\(\*\s*GATE:BEGIN\s+(\S+)\s*\*\)(.*?)\(\*\s*GATE:END\s*\*\)", re.S)


def normalise(statement: str) -> str:
    return " ".join(statement.split())


def digest(statement: str) -> str:
    return "sha256:" + hashlib.sha256(normalise(statement).encode("utf-8")).hexdigest()


def extract_statements(track_dir: Path) -> dict[str, str]:
    """subject -> normalised statement text, from every .v/.thy file's GATE markers, outside
    defects/: a defect file may deliberately carry a weakened restatement under a real subject's
    name, and relying on which file a case-sensitive-vs-insensitive directory listing visits last
    to decide which text wins is not a gate, it is luck. scan_for_banned already excludes
    defects/ for the same reason; this mirrors it for rule 1."""
    found: dict[str, str] = {}
    for path in sorted(track_dir.rglob("*")):
        if path.suffix not in (".v", ".thy"):
            continue
        if "defects" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for match in MARKER.finditer(text):
            subject, body = match.group(1), match.group(2)
            found[subject] = normalise(body)
    return found


def scan_for_banned(track_dir: Path) -> list[str]:
    hits = []
    for path in sorted(track_dir.rglob("*")):
        if path.suffix not in (".v", ".thy"):
            continue
        if "defects" in path.parts:
            continue  # a defect file's Admitted/sorry is the defect, not a gate failure
        text = path.read_text(encoding="utf-8")
        for m in BANNED.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append(f"{path.relative_to(track_dir)}:{line}: {m.group(0)}")
    return hits


def load_claims(track_dir: Path) -> list[dict]:
    claims_dir = track_dir / "claims"
    if not claims_dir.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(claims_dir.glob("*.json"))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track_dir", type=Path)
    parser.add_argument("--defect-ok", action="store_true")
    args = parser.parse_args()
    track_dir = args.track_dir.resolve()

    statements = extract_statements(track_dir)
    claims = load_claims(track_dir)
    banned = scan_for_banned(track_dir)

    ok = True
    print(f"Law report: {track_dir.name}")
    for claim in claims:
        subject = claim["subject"]
        recomputed = digest(statements[subject]) if subject in statements else None
        mismatch = recomputed is not None and recomputed != claim["statementDigest"]
        row_ok = claim["outcome"] == "passed" and not (mismatch and not args.defect_ok)
        ok = ok and row_ok
        flag = "" if not mismatch else "  [STATEMENT DIGEST MISMATCH, unreviewed restatement]"
        print(f"  {subject:<12} {claim['method']:<8} {claim['outcome']:<7} {claim['statedAs']}{flag}")

    if banned and not args.defect_ok:
        ok = False
        print("Banned markers found outside defects/:")
        for hit in banned:
            print(f"  {hit}")

    print("GATE: " + ("pass" if ok else "fail"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
