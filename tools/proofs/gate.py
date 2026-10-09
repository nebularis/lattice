#!/usr/bin/env python3
"""The proof gate script (ADR-A-FM2; carried over from spikes/formal-prover/gate.py, track D's
spike). For one layer's directory under tools/proofs/:

1. Recomputes each claim's statement digest from its theory source, between
   ``(* GATE:BEGIN <subject> *)`` and ``(* GATE:END *)`` markers, **together with the normalised
   text of every datatype/fun/definition/abbreviation block found anywhere in the layer**
   (E1.4, the formal-methods epic's second review \u00a72.1), and fails on an unreviewed mismatch
   against the committed claim. Before E1.4, a gated lemma's digest covered only the lemma's own
   statement text, so redefining a constant the lemma mentions (``or3``, say) changed what every
   lemma about it means without changing a single digest. Covering every definition in the layer
   is coarser than true per-statement dependency tracking (every claim becomes sensitive to every
   definition, not only the ones it actually mentions), but it is sound, which a textual
   approximation of real dependency tracking is not guaranteed to be.
2. Runs the assumption audit: a scan of every theory source for an unreviewed
   ``Admitted``/``admit``/``sorry``/``oracle``/``axiomatization``, or a proof relying on
   Isabelle's code-generator oracle (``by eval``/``by evaluation``, which is tagged as an oracle
   dependency, not a kernel-checked proof), outside files under a ``defects/`` directory, where
   such a marker is the defect itself, not a gate failure.
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

BANNED = re.compile(r"\b(Admitted|admit|sorry|oracle|axiomatization)\b|\bby\s+eval(uation)?\b")
MARKER = re.compile(r"\(\*\s*GATE:BEGIN\s+(\S+)\s*\*\)(.*?)\(\*\s*GATE:END\s*\*\)", re.S)
DEF_HEADER = re.compile(r"^(datatype|type_synonym|fun|definition|abbreviation)\b")


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


def extract_definitions(track_dir: Path) -> str:
    """The normalised text of every ``datatype``/``type_synonym``/``fun``/``definition``/
    ``abbreviation`` block in any .thy file in this layer, outside ``defects/`` -- included in
    every claim's digest input (E1.4), not only the gated statement's own text, so changing a
    definition a statement depends on, even one declared in a file the statement's own theory
    imports, changes that statement's recomputed digest. A block runs from its header line
    through the following non-blank lines (matching how every definition in this layer is
    actually laid out: a header, its clauses, then a blank line before the next construct)."""
    found: list[str] = []
    for path in sorted(track_dir.rglob("*")):
        if path.suffix not in (".v", ".thy") or "defects" in path.parts:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        index = 0
        while index < len(lines):
            if DEF_HEADER.match(lines[index].strip()):
                block = [lines[index]]
                index += 1
                while index < len(lines) and lines[index].strip():
                    block.append(lines[index])
                    index += 1
                found.append(normalise("\n".join(block)))
            else:
                index += 1
    return " ".join(found)


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
    definitions = extract_definitions(track_dir)
    claims = load_claims(track_dir)
    banned = scan_for_banned(track_dir)

    ok = True
    print(f"Law report: {track_dir.name}")
    for claim in claims:
        subject = claim["subject"]
        recomputed = digest(statements[subject] + " " + definitions) if subject in statements else None
        mismatch = recomputed is not None and recomputed != claim["statementDigest"]
        row_ok = claim["outcome"] == "passed" and not (mismatch and not args.defect_ok)
        ok = ok and row_ok
        flag = "" if not mismatch else "  [STATEMENT DIGEST MISMATCH, unreviewed restatement]"
        print(f"  {subject:<12} {claim['method']:<8} {claim['outcome']:<7} {claim['statedAs']}{flag}")

    print("Assumption audit: " + ("clean, no sorry/oops/admit/oracle/by-eval found" if not banned else "FINDINGS"))
    if banned and not args.defect_ok:
        ok = False
        print("Banned markers found outside defects/:")
        for hit in banned:
            print(f"  {hit}")

    print("GATE: " + ("pass" if ok else "fail"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
