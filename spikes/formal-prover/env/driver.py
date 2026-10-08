#!/usr/bin/env python3
"""The track D driver (FM-D9): runs one formal-methods tool by route, with a fixed argument
vector and a private work directory, so the same call a worker makes can be tested locally on
any host.

Usage:
    python driver.py <tool> <action> [--route image|native] [--workdir DIR] [-- extra args]

Tools: rocq, isabelle. Actions: smoke, version. Route defaults to $LATTICE_FORMAL_ROUTE or
"image". The image route is the one every recorded claim and report figure in this spike uses
(epic E9); the native route is for interactive authoring only and is never the one recorded.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BUILD_ROOT = REPO_ROOT / ".build" / "formal"

IMAGES = {
    "rocq": "rocq/rocq-prover:9.1",
    # The MetaRocq-equipped variant, when a job needs AST quotation (epic §4, Environments).
    "rocq-metarocq": "lattice-fm/rocq-metarocq:spike",
}


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd), file=sys.stderr)
    return subprocess.run(cmd, **kw)


def native_rocq(args: list[str], workdir: Path) -> int:
    """Runs a Rocq command natively, via PowerShell so env-common.ps1's PATH setup applies.
    Image route runs are what the report records; this exists for local iteration only."""
    opam_root = os.environ.get(
        "LATTICE_FORMAL_OPAMROOT",
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "fm-experiment" / "opamroot"),
    )
    switch = os.environ.get("FMX_SWITCH", "fm")
    ps = (
        f"$env:OPAMROOT='{opam_root}'; "
        f"(& opam env --switch={switch} --shell=powershell) -split \"`r?`n\" | "
        "ForEach-Object { if ($_) { Invoke-Expression $_ } }; "
        f"cd '{workdir}'; " + " ".join(args)
    )
    opam_exe = str(Path(os.environ.get("LATTICE_FORMAL_ROOT", "C:/fmx")) / "downloads" / "opam.exe")
    # opam.exe must be first on PATH for "opam" above to resolve without a full path.
    ps = f"$env:Path = (Split-Path '{opam_exe}') + ';' + $env:Path; " + ps
    result = _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps])
    return result.returncode


def image_rocq(args: list[str], workdir: Path, image: str = "rocq") -> int:
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{workdir}:/w",
        "-w", "/w",
        IMAGES[image],
        "bash", "-lc", " ".join(args),
    ]
    return _run(cmd).returncode


def native_isabelle(args: list[str], workdir: Path) -> int:
    root = os.environ.get("LATTICE_FORMAL_ROOT", "C:/fmx")
    isabelle_home = os.environ.get("FMX_ISABELLE", str(Path(root) / "Isabelle2025-2"))

    def cygpath(p: Path) -> str:
        full = str(p.resolve())
        return "/cygdrive/" + full[0].lower() + full[2:].replace("\\", "/")

    bash = str(Path(isabelle_home) / "contrib" / "cygwin" / "bin" / "bash.exe")
    isabelle = cygpath(Path(isabelle_home)) + "/bin/isabelle"
    command = f"cd {cygpath(workdir)} && {isabelle} " + " ".join(args)
    env = dict(os.environ)
    env["CHERE_INVOKING"] = "true"
    return _run([bash, "--login", "-c", command], env=env).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=["rocq", "rocq-metarocq", "isabelle"])
    parser.add_argument("args", nargs=argparse.REMAINDER, help="the tool's own argument vector")
    parser.add_argument("--route", choices=["image", "native"], default=os.environ.get("LATTICE_FORMAL_ROUTE", "image"))
    parser.add_argument("--workdir", type=Path, default=None, help="defaults to a private temp directory")
    args = parser.parse_args()

    own_workdir = args.workdir is None
    workdir = args.workdir or Path(tempfile.mkdtemp(prefix="fm-driver-", dir=BUILD_ROOT))
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        tool_args = args.args[1:] if args.args[:1] == ["--"] else args.args
        if args.tool in ("rocq", "rocq-metarocq"):
            code = image_rocq(tool_args, workdir, args.tool) if args.route == "image" else native_rocq(tool_args, workdir)
        else:
            if args.route == "image":
                raise SystemExit("isabelle has no image route in this spike (native only, epic §4)")
            code = native_isabelle(tool_args, workdir)
        return code
    finally:
        if own_workdir and os.environ.get("LATTICE_FORMAL_KEEP_WORKDIR") != "1":
            # Docker Desktop can briefly hold the bind mount open past the container's exit, so
            # retry once rather than leaving an empty (git-ignored) directory behind.
            for attempt in range(3):
                try:
                    shutil.rmtree(workdir)
                    break
                except OSError:
                    if attempt == 2:
                        break
                    time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())
