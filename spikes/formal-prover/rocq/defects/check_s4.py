#!/usr/bin/env python3
"""Standalone demonstration that gate.py's banned-marker scan (rule 2, S4) finds an Admitted
theorem when it is not under a defects/ directory, where it is, by convention, the defect itself
and not a gate failure.
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
    shutil.copy(HERE / "S4_admitted.v", tmp_path / "S4_admitted.v")
    hits = gate.scan_for_banned(tmp_path)

print("Banned-marker scan over a copy with no defects/ component:")
for hit in hits:
    print(f"  {hit}")

if not hits:
    print("FAIL: no banned markers found; S4 would not be detected")
    sys.exit(1)

print("PASS: gate.py's banned-marker scan (rule 2) finds the Admitted outside defects/")
