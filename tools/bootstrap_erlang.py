"""Install the Erlang that mise.toml pins, where a cloud session's setup leaves it out (plan vyvid-migration, VM-12).

The cloud setup disables Erlang and Elixir in mise (tools/claude-cloud-setup.sh, section 4) so that it does not build them within
its time. The Configuration Studio's RabbitMQ needs Erlang, so this task installs the pin with that disable lifted for these
commands only. A no-op where `erl` is already on the path. It prints the folder holding `erl`, which
`tools/config_studio_stack.py` finds for itself when `erl` is not on the path."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

# The setup disables both. Only Elixir stays disabled here, since nothing in the studio needs it.
DISABLED = "elixir"


def pinned(text: str) -> str:
    return str(tomllib.loads(text)["tools"]["erlang"])


def _mise(*args: str, run=subprocess.run):
    env = {**os.environ, "MISE_DISABLE_TOOLS": DISABLED}
    return run(["mise", *args], env=env, capture_output=True, text=True)


def find(version: str, which=shutil.which, run=subprocess.run) -> Path | None:
    """The folder holding `erl`, from the path or from an installed pin, else None. Installs nothing."""
    erl = which("erl")
    if erl:
        return Path(erl).resolve().parent
    done = _mise("where", f"erlang@{version}", run=run)
    return Path(done.stdout.strip()) / "bin" if done.returncode == 0 and done.stdout.strip() else None


def ensure(version: str, which=shutil.which, run=subprocess.run) -> Path | None:
    """`find`, and where nothing is found `mise install erlang@<version>` and a second look. None if that fails."""
    erl = which("erl")
    if erl:
        return Path(erl).resolve().parent
    if _mise("install", f"erlang@{version}", run=run).returncode != 0:
        return None
    return find(version, which=which, run=run)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    version = pinned((root / "mise.toml").read_text(encoding="utf-8"))
    folder = ensure(version)
    if folder is None:
        print(f"bootstrap:erlang: could not install Erlang {version}. Run `MISE_DISABLE_TOOLS=elixir mise install erlang@{version}` to see why.", file=sys.stderr)
        return 1
    print(f"Erlang {version}: {folder}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
