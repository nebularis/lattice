#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Print both experiments. Run from the repository root:

    python spikes/persistence-oxigraph/run.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scenarios import append_event_runs, composite_sweep, project_sweep  # noqa: E402


def main() -> int:
    print("Composite boundary: subjects that still have triples after a replace\n")
    for label, owns, payment in (
        ("an order and its line item", False, False),
        ("a payment the shape does not own", False, True),
        ("a payment the shape owns", True, True),
    ):
        print(f"  {label:42} -> {composite_sweep(owns, payment) or 'nothing left'}")
    print(f"  {'the project fixture':42} -> {project_sweep()}")
    print("\nappend-event: what a missing parameter does\n")
    for state in append_event_runs():
        print(f"  {state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
