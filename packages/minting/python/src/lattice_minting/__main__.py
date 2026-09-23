# SPDX-License-Identifier: MPL-2.0
"""``lattice-mint verify FILE…``: run conformance vectors or anchors against
this library, one line per failure, exit status 1 on any failure."""

from __future__ import annotations

import sys

from .conformance import verify


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2 or args[0] != "verify":
        print("usage: lattice-mint verify FILE…", file=sys.stderr)
        return 2
    failed = 0
    for path in args[1:]:
        report = verify(path)
        for f in report.failures:
            print("FAIL", f)
        print(f"{path}: {report.passed} checks passed, {len(report.failures)} failed")
        failed += len(report.failures)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
