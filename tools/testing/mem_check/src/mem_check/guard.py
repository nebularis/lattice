# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Run a command one task at a time with two test workers, and stop it if the machine runs short of memory.

``python -m mem_check.guard -- mise run check`` is the slower way to run a check on a busy machine. ``MISE_JOBS`` and
``PYTEST_XDIST_AUTO_NUM_WORKERS`` carry the limits to every task under it. It prints what is available each minute, and it exits
with the command's own code, or ``STOPPED`` where it stopped the command, so a stopped run is never read as a pass or a test failure.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time

from . import GIB, RESERVE, available_bytes

STOPPED = 3
"""The exit code of a run the guard stopped."""


def _stop(process: subprocess.Popen) -> None:
    """End the command and everything it started."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
    else:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def run(command: list[str], floor: int = RESERVE, poll: float = 3.0, report_every: float = 60.0) -> int:
    """The command's exit code, or ``STOPPED`` where less than ``floor`` bytes stayed available."""
    env = {"MISE_JOBS": "1", "PYTEST_XDIST_AUTO_NUM_WORKERS": "2", **os.environ}
    process = subprocess.Popen(command, env=env, start_new_session=sys.platform != "win32")
    reported = time.monotonic()
    lowest = None
    while process.poll() is None:
        free = available_bytes()
        if free is not None:
            lowest = free if lowest is None else min(lowest, free)
            if free < floor:
                print(f"mem_check.guard: {free / GIB:.1f} GiB available, under {floor / GIB:.1f} GiB, so the run was stopped", flush=True)
                _stop(process)
                return STOPPED
            if time.monotonic() - reported >= report_every:
                print(f"mem_check.guard: {free / GIB:.1f} GiB available", flush=True)
                reported = time.monotonic()
        time.sleep(poll)
    if lowest is not None:
        print(f"mem_check.guard: the lowest available was {lowest / GIB:.1f} GiB", flush=True)
    return process.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--floor-gib", type=float, default=RESERVE / GIB, help="stop the command when less than this stays available")
    parser.add_argument("command", nargs="+", help="the command to run, after --")
    arguments = parser.parse_args(argv)
    return run(arguments.command, int(arguments.floor_gib * GIB))


if __name__ == "__main__":
    sys.exit(main())
