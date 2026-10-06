#!/usr/bin/env python3
"""Standalone demonstration that gate.py's digest check (rule 1, S5) catches an unreviewed
restatement in the Isabelle track. Not run as part of the gate's normal directory-wide scan over
this track: that scan would merge this defect's "TA1" marker with Kernel.thy's real one under
the same subject name, since both live somewhere under the same track directory, and
last-writer-wins in a dict keyed by subject.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import gate  # noqa: E402

HERE = Path(__file__).resolve().parent
ISABELLE = HERE.parent

real_text = (ISABELLE / "Kernel.thy").read_text(encoding="utf-8")
weak_text = (HERE / "S5_weaker_restatement.thy").read_text(encoding="utf-8")

real_statements = {m.group(1): gate.normalise(m.group(2)) for m in gate.MARKER.finditer(real_text)}
weak_statements = {m.group(1): gate.normalise(m.group(2)) for m in gate.MARKER.finditer(weak_text)}

real_digest = gate.digest(real_statements["TA1"])
weak_digest = gate.digest(weak_statements["TA1"])

print(f"TA1 (Kernel.thy)              {real_digest}")
print(f"TA1 (defects/S5, weakened) {weak_digest}")

if real_digest == weak_digest:
    print("FAIL: digests matched; S5 would not be detected")
    sys.exit(1)

print("PASS: digests differ -- gate.py's mismatch check (rule 1) flags this as an unreviewed restatement")
