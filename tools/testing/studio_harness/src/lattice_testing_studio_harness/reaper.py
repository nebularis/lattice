# SPDX-License-Identifier: MPL-2.0
"""Stops a run's processes once the process that started them has gone, however it went.

Each process of a run is detached, so it outlives a test process that is killed, or interrupted again during its teardown, before `stop()` finishes. The reaper is detached too and holds the read end of a pipe whose write end only the starter has. The operating system closes that end when the starter ends, for any reason, SIGKILL included, and the read returns."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from . import _build
from ._tools import stack as stack_module


def start(run_dir: Path) -> subprocess.Popen:
    """A reaper for `run_dir`, which watches the calling process for as long as the returned object's `stdin` stays open."""
    return subprocess.Popen([sys.executable, "-m", "lattice_testing_studio_harness.reaper", str(run_dir)], stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **stack_module.detached())


def reap(run_dir: Path) -> None:
    """Stops every process with a pid file in the run, then removes the run's folder. After a clean `stop()` there is nothing left to do."""
    for pid_file in sorted((run_dir / "run").glob("*.pid")):
        try:
            pid = int(pid_file.read_text().strip())
        except (OSError, ValueError):
            continue
        if stack_module.alive(pid):
            stack_module.stop_tree(pid)
    _build.remove(run_dir)


if __name__ == "__main__":
    sys.stdin.buffer.read()
    reap(Path(sys.argv[1]))
