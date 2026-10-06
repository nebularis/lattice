#!/usr/bin/env python3
"""Track D's smoke suite (mise task check:formal-smoke): confirms the image route works, on any
Docker host. Isabelle has no image route in this spike (epic §4), so it is checked only when
--route native is given explicitly, on a host with it installed natively.

Usage: python smoke.py [--route image|native] [--tool rocq,isabelle]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ENV_DIR = Path(__file__).resolve().parent
DRIVER = ENV_DIR / "driver.py"


def run(route: str, tool: str, args: list[str]) -> bool:
    cmd = [sys.executable, str(DRIVER), "--route", route, tool, "--", *args]
    print("+", " ".join(cmd), file=sys.stderr)
    result = subprocess.run(cmd)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route", choices=["image", "native"], default="image")
    parser.add_argument("--tool", default="rocq,rocq-metarocq")
    args = parser.parse_args()

    checks = {
        "rocq": ("rocq", ["rocq", "--version"]),
        "rocq-metarocq": ("rocq-metarocq", ["opam", "list", "rocq-metarocq-template", "--short"]),
        "isabelle": ("isabelle", ["version"]),
    }
    results: dict[str, bool] = {}
    for tool in args.tool.split(","):
        if tool == "isabelle" and args.route == "image":
            continue  # no image route for Isabelle in this spike
        driver_tool, tool_args = checks[tool]
        results[tool] = run(args.route, driver_tool, tool_args)

    print()
    print(f"Results ({args.route} route)")
    for name, ok in results.items():
        print(f"  {name:<16} {'ok' if ok else 'FAIL'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
