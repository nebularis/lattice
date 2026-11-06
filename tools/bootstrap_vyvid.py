"""Install Вивід, `vyd`, as a uv tool at the version mise.toml pins (ADR-A152, plan vyvid-migration, VM-1).

A no-op where `vyd` already reports the pinned version. An installed `vyd` at another version is replaced only
where the tool's `uv-receipt.toml` shows a git install. An editable or local-directory install, one from pip or pipx
with no receipt, or one whose receipt cannot be read is left alone, with a line saying how to move to the pin. An
absent `vyd` is installed from the pinned tag. Where `uv` is missing it says what it skipped and exits zero, since Windows is proven after the switch and
an absent tool never blocks (ADR-A152 decision 4). The version comes from VYVID_VERSION, set in mise.toml."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

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


def install_kind(receipt: Path) -> tuple[str | None, str | None]:
    """The source key the install's receipt carries, 'git', 'editable' or 'directory', else None, and a note where the receipt is missing or cannot be read. Only 'git' is ever replaced."""
    try:
        requirement = tomllib.loads(receipt.read_text(encoding="utf-8"))["tool"]["requirements"][0]
        return next((key for key in ("git", "editable", "directory") if key in requirement), None), None
    except OSError:
        return None, f"{receipt} is missing, so the install is not taken as a uv git install"
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, KeyError, IndexError, TypeError):
        return None, f"{receipt} could not be read, so the install is not taken as a uv git install"


def decide(installed: str | None, pinned: str, have_uv: bool, kind: str | None = None) -> tuple[str, list[str] | None]:
    """What to say and what to run, if anything. `kind` is the key install_kind returned for an installed vyd."""
    if installed == pinned:
        return f"vyd {pinned} is installed", None
    if installed and kind != "git":
        what = {"editable": "an editable install", "directory": "a directory install"}.get(kind, "not a uv git install")
        return f"vyd {installed} is {what} and is left alone, mise.toml pins {pinned}. To move to the pin, run `uv tool install --force {SOURCE}@v{pinned}`", None
    if not have_uv:
        return f"uv is missing, so vyd {pinned} was not installed. mise.toml pins uv, so run `mise install`, then `mise run bootstrap:vyvid`", None
    over = f", replacing {installed}" if installed else ""
    return f"installing vyd {pinned}{over}", ["uv", "tool", "install", "--force", f"{SOURCE}@v{pinned}"]


def main() -> int:
    pinned = os.environ.get("VYVID_VERSION")
    if not pinned:
        print("bootstrap:vyvid: VYVID_VERSION is not set. mise.toml sets it under [env]", file=sys.stderr)
        return 1
    have_uv = shutil.which("uv") is not None
    installed = installed_version()
    kind, note = None, None
    if have_uv and installed:
        try:
            tool_dir = subprocess.run(["uv", "tool", "dir"], capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            tool_dir = ""
        if tool_dir:
            kind, note = install_kind(Path(tool_dir) / "vyvid" / "uv-receipt.toml")
        else:
            note = "`uv tool dir` gave no directory, so the install is not taken as a uv git install"
    message, command = decide(installed, pinned, have_uv, kind)
    if note:
        print(f"bootstrap:vyvid: {note}")
    print(f"bootstrap:vyvid: {message}")
    if command is None:
        return 0
    return subprocess.run(command).returncode


if __name__ == "__main__":
    sys.exit(main())
