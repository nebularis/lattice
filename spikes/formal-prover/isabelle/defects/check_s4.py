#!/usr/bin/env python3
"""Standalone demonstration that gate.py's banned-marker scan (rule 2, S4) finds a "sorry"
theorem when it is not under a defects/ directory, where it is, by convention, the defect
itself. Isabelle's own build already refuses "sorry" without quick_and_dirty (a stronger,
build-time rejection); this checks what the gate's *source scan* additionally catches, matching
Rocq's story (Admitted compiles silently there, and needs the same scan).
"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import gate  # noqa: E402

HERE = Path(__file__).resolve().parent

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp) / "production"  # a directory name with no "defects" path component
    tmp_path.mkdir()
    shutil.copy(HERE / "S4_sorry.thy", tmp_path / "S4_sorry.thy")
    hits = gate.scan_for_banned(tmp_path)

print("Banned-marker scan over a copy with no defects/ component:")
for hit in hits:
    print(f"  {hit}")

if not hits:
    print("FAIL: no banned markers found; S4 would not be detected")
    sys.exit(1)

print("PASS: gate.py's banned-marker scan (rule 2) finds the sorry outside defects/")
