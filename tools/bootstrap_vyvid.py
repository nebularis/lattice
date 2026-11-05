"""Install Вивід, `vyd`, as a uv tool at the version mise.toml pins (ADR-A152, plan vyvid-migration, VM-1).

A no-op where `vyd` already reports the pinned version, so a maintainer's own install is never written over.
Where `uv` is missing it says what it skipped and exits zero, since Windows is proven after the switch and
an absent tool never blocks (ADR-A152 decision 4). The version comes from VYVID_VERSION, set in mise.toml."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

SOURCE = "git+https://github.com/nebularis/vyvid"


def installed_version() -> str | None:
    """The version `vyd --version` reports, as 'Вивід (vyvid) 0.2.2' gives '0.2.2', or None where vyd is absent."""
    if shutil.which("vyd") is None:
        return None
    try:
        out = subprocess.run(["vyd", "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return out.split()[-1] if out else None


def decide(installed: str | None, pinned: str, have_uv: bool) -> tuple[str, list[str] | None]:
    """What to say and what to run, if anything."""
    if installed == pinned:
        return f"vyd {pinned} is installed", None
    if not have_uv:
        return f"uv is missing, so vyd {pinned} was not installed. mise.toml pins uv, so run `mise install`, then `mise run bootstrap:vyvid`", None
    over = f", replacing {installed}" if installed else ""
    return f"installing vyd {pinned}{over}", ["uv", "tool", "install", "--force", f"{SOURCE}@v{pinned}"]


def main() -> int:
    pinned = os.environ.get("VYVID_VERSION")
    if not pinned:
        print("bootstrap:vyvid: VYVID_VERSION is not set. mise.toml sets it under [env]", file=sys.stderr)
        return 1
    message, command = decide(installed_version(), pinned, shutil.which("uv") is not None)
    print(f"bootstrap:vyvid: {message}")
    if command is None:
        return 0
    return subprocess.run(command).returncode


if __name__ == "__main__":
    sys.exit(main())
