# SPDX-License-Identifier: MPL-2.0
"""Stages the Docker build inputs for the Word authoring POC stack (plan WA10), standard library
only. `python tools/authoring_stage.py [--root .]`.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

PipRunner = Callable[[Sequence[str]], None]


def default_pip_runner(args: Sequence[str]) -> None:
    subprocess.run([sys.executable, "-m", "pip", *args], check=True)


def stage(root: Path, pip_runner: PipRunner = default_pip_runner) -> None:
    jar = root / "platform" / "authoring-service" / "target" / "authoring-service.jar"
    if not jar.is_file():
        print(
            f"missing {jar.as_posix()}: run 'mise run build:authoring' to build it first",
            file=sys.stderr,
        )
        raise SystemExit(2)

    taskpane = root / "apps" / "word-authoring-addin" / "dist" / "taskpane.html"
    if not taskpane.is_file():
        print(
            f"missing {taskpane.as_posix()}: run 'mise run build:authoring' to build it first",
            file=sys.stderr,
        )
        raise SystemExit(2)

    build_dir = root / ".build" / "authoring"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    compose_dir = root / "deployment" / "compose" / "authoring"

    service_dir = build_dir / "service"
    service_dir.mkdir(parents=True)
    shutil.copy2(jar, service_dir / "authoring-service.jar")
    shutil.copy2(compose_dir / "service.Dockerfile", service_dir / "Dockerfile")
    print(f"staged {service_dir.as_posix()}")

    worker_dir = build_dir / "worker"
    wheelhouse = worker_dir / "wheelhouse"
    wheelhouse.mkdir(parents=True)
    pip_runner(["wheel", "--no-deps", "-w", str(wheelhouse), str(root / "workers")])
    pip_runner(
        [
            "download",
            "--only-binary=:all:",
            "--platform",
            "any",
            "--python-version",
            "3.14",
            "--implementation",
            "py",
            "--abi",
            "none",
            "-d",
            str(wheelhouse),
            "pika>=1.3,<2",
            "rdflib>=7.1,<8",
        ]
    )
    shutil.copy2(compose_dir / "worker.Dockerfile", worker_dir / "Dockerfile")
    print(f"staged {worker_dir.as_posix()}")

    addin_dest = build_dir / "addin"
    shutil.copytree(taskpane.parent, addin_dest)
    print(f"staged {addin_dest.as_posix()}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    args = parser.parse_args(argv)
    stage(Path(args.root).resolve())


if __name__ == "__main__":
    main()
