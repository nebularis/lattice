# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""How much memory this machine has free, and how many test workers fit in it (ADR-A125).

A suite that runs in parallel asks for a worker count, given what one worker needs at its peak. When the machine has room for
the count it would use anyway, the suite keeps it. When it is short, for example with an editor and other tools open on an
8 GB machine, the suite drops to two workers, which takes longer and stays within memory.

Standard library only. "Available" is what the operating system can give a new process without swapping: on macOS the free,
inactive, speculative and purgeable pages that ``vm_stat`` reports, on Linux ``MemAvailable`` from ``/proc/meminfo``, and on
Windows ``ullAvailPhys``. Where none can be read, the answer is ``None`` and a suite keeps its own count.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

GIB = 1024 ** 3
MIB = 1024 ** 2
LOW_WORKERS = 2
RESERVE = GIB
"""What is left for everything else on the machine, an editor and the shell among them, when deciding whether workers fit."""

_OVERRIDE = "MEM_CHECK_AVAILABLE_MIB"
"""Set to a number of MiB to pretend that much is available, for a test of a suite's choice or to force the low path."""


def _macos() -> int | None:
    try:
        text = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    size = re.search(r"page size of (\d+) bytes", text)
    if not size:
        return None
    pages = 0
    for name in ("free", "inactive", "speculative", "purgeable"):
        found = re.search(rf"^Pages {name}:\s+(\d+)\.", text, re.M)
        pages += int(found.group(1)) if found else 0
    return pages * int(size.group(1))


def _linux() -> int | None:
    try:
        with open("/proc/meminfo", encoding="ascii") as meminfo:
            for line in meminfo:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


def _windows() -> int | None:
    import ctypes

    class MemoryStatus(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(MemoryStatus)
    try:
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
    except (AttributeError, OSError):
        return None
    return int(status.ullAvailPhys)


def available_bytes() -> int | None:
    """The memory a new process can have without swapping, or ``None`` where it cannot be read."""
    override = os.environ.get(_OVERRIDE)
    if override:
        return int(override) * MIB
    if sys.platform == "darwin":
        return _macos()
    if sys.platform.startswith("linux"):
        return _linux()
    if sys.platform == "win32":
        return _windows()
    return None


def workers(default: int, per_worker: int, *, reserve: int = RESERVE, low: int = LOW_WORKERS, available: int | None = None) -> int:
    """``default`` workers when they fit in what is available less ``reserve``, otherwise ``low`` (never more than ``default``).

    ``per_worker`` is a suite's own measured peak for one worker process, in bytes. ``available`` is for tests, and is read from
    the machine when absent. An unreadable machine keeps ``default``."""
    free = available_bytes() if available is None else available
    if free is None or free - reserve >= default * per_worker:
        return default
    return min(default, low)


def report(default: int, per_worker: int) -> str:
    """One line saying what was found and chosen, for a suite to print."""
    free = available_bytes()
    chosen = workers(default, per_worker, available=free)
    shown = "unknown" if free is None else f"{free / GIB:.1f} GiB"
    return f"mem_check: {shown} available, {default} worker(s) need {default * per_worker / GIB:.1f} GiB, using {chosen}"
