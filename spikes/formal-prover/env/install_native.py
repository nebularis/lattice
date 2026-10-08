#!/usr/bin/env python3
"""Installs track D's native toolchains on macOS and Linux (mise tasks bootstrap:formal-native-isabelle
and bootstrap:formal-native-rocq). Windows keeps its PowerShell scripts.

Usage:
    python install_native.py isabelle    Isabelle2025-2, from the Cambridge mirror, with its prebuilt heaps
    python install_native.py rocq        an opam switch with OCaml 5.3.0 and Rocq (needs opam on PATH)

Both install under $LATTICE_FORMAL_ROOT, default ~/.local/share/lattice-formal, and are re-runnable.
Standard library only.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ISABELLE = "Isabelle2025-2"
ISABELLE_MIRROR = "https://www.cl.cam.ac.uk/research/hvg/Isabelle/dist"
OCAML = "5.3.0"
SWITCH = os.environ.get("FMX_SWITCH", "fm")
ROCQ_REPO = ("rocq-released", "https://rocq-prover.org/opam/released")
ROCQ_PACKAGES = ["rocq-prover", "dune", "ppxlib", "js_of_ocaml-compiler"]


def formal_root() -> Path:
    if os.environ.get("LATTICE_FORMAL_ROOT"):
        return Path(os.environ["LATTICE_FORMAL_ROOT"]).expanduser()
    if os.name == "nt":
        return Path("C:/fmx")
    return Path.home() / ".local" / "share" / "lattice-formal"


def isabelle_bundle() -> str:
    """The release archive's name stem for this host."""
    system, machine = platform.system(), platform.machine().lower()
    if system == "Darwin":
        return f"{ISABELLE}_macos"
    if system == "Linux":
        return f"{ISABELLE}_linux_arm" if machine in ("aarch64", "arm64") else f"{ISABELLE}_linux"
    raise SystemExit(f"no native Isabelle install scripted for {system} here (Windows: run_windows)")


def isabelle_executable() -> Path | None:
    """The isabelle tool: $FMX_ISABELLE, then the formal root (the macOS bundle or the Linux
    directory), then /opt, then PATH."""
    homes = [Path(os.environ["FMX_ISABELLE"])] if os.environ.get("FMX_ISABELLE") else []
    homes += [formal_root() / f"{ISABELLE}.app", formal_root() / ISABELLE, Path("/opt") / ISABELLE]
    for home in homes:
        if (home / "bin" / "isabelle").is_file():
            return home / "bin" / "isabelle"
    found = shutil.which("isabelle")
    return Path(found) if found else None


def install_isabelle() -> int:
    existing = isabelle_executable()
    if existing:
        print(f"Isabelle already installed: {existing}")
        return 0
    root = formal_root()
    root.mkdir(parents=True, exist_ok=True)
    url = f"{ISABELLE_MIRROR}/{isabelle_bundle()}.tar.gz"
    print(f"Downloading and unpacking {url} into {root} (about 1.2 GB)")
    with urllib.request.urlopen(url) as response, tarfile.open(fileobj=response, mode="r|gz") as archive:
        archive.extractall(root, filter="tar")
    exe = isabelle_executable()
    if not exe:
        print(f"unpacked, but no bin/isabelle found under {root}", file=sys.stderr)
        return 1
    subprocess.run([str(exe), "version"], check=False)
    print(f"Installed: {exe}. Put its directory on PATH, or leave it where the driver finds it.")
    return 0


def opam(*args: str) -> subprocess.CompletedProcess:
    print("+ opam", " ".join(args), file=sys.stderr)
    return subprocess.run(["opam", *args], capture_output=True, text=True)


def install_rocq() -> int:
    if not shutil.which("opam"):
        hint = "brew install opam" if platform.system() == "Darwin" else "apt-get install opam"
        print(f"opam is not on PATH. Install it first ({hint}).", file=sys.stderr)
        return 1
    if opam("switch", "list", "--short").returncode != 0:
        if subprocess.run(["opam", "init", "--bare", "-n", "-y"]).returncode != 0:
            return 1
    if SWITCH not in opam("switch", "list", "--short").stdout.split():
        if subprocess.run(["opam", "switch", "create", SWITCH, OCAML, "-y"]).returncode != 0:
            return 1
    name, url = ROCQ_REPO
    if name not in opam("repo", "list", f"--switch={SWITCH}", "--short").stdout.split():
        if subprocess.run(["opam", "repo", "add", name, url, f"--switch={SWITCH}"]).returncode != 0:
            return 1
    if subprocess.run(["opam", "install", f"--switch={SWITCH}", *ROCQ_PACKAGES, "-y"]).returncode != 0:
        return 1
    return subprocess.run(["opam", "exec", f"--switch={SWITCH}", "--", "rocq", "--version"]).returncode


def main(argv: list[str]) -> int:
    if argv[:1] == ["isabelle"]:
        return install_isabelle()
    if argv[:1] == ["rocq"]:
        return install_rocq()
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
