# SPDX-License-Identifier: MPL-2.0
"""What a run needs from the checkout, taken as copies so a run never reads a file the developer's own stack writes."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict

from ._tools import catalogue
from .topology import HarnessError

JARS = {"service": "config-studio-service", "writer": "config-studio-writer"}
KEEP_ENV = "STUDIO_HARNESS_KEEP"


def harness_dir(root: Path) -> Path:
    return root / ".build" / "studio-harness"


def cache_dir(root: Path) -> Path:
    """Downloads, the extracted broker and the jars, shared by runs. Not a run id, so no run's folder collides with it."""
    return harness_dir(root) / "_cache"


def jars(root: Path) -> Dict[str, Path]:
    """The service's and the writer's jars, copied once into the cache under their content hash.

    The copy is made from `platform/{module}/target/{module}.jar`, which is only read, so a stack running from those jars is not disturbed. A jar that is
    missing is built with Maven, which writes `target`, so that happens only in a checkout where no stack runs from `target`.
    `LATTICE_STUDIO_HARNESS_JARS` names a folder holding the two jars to use instead."""
    override = os.environ.get("LATTICE_STUDIO_HARNESS_JARS")
    platform = root / catalogue.load(root).area("platform")
    out: Dict[str, Path] = {}
    for key, module in JARS.items():
        source = Path(override) / f"{module}.jar" if override else platform / module / "target" / f"{module}.jar"
        if not source.is_file():
            if override:
                raise HarnessError(f"{source} does not exist")
            subprocess.run(["mvn", "-q", "-f", str(platform / "pom.xml"), "-pl", module, "-am", "package", "-DskipTests"], cwd=root, check=True)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
        target = cache_dir(root) / "jars" / f"{module}-{digest}.jar"
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix(".part")
            shutil.copyfile(source, partial)
            partial.replace(target)
        out[key] = target
    return out


def assets(root: Path, into: Path) -> Path:
    """Copies the staged assets (`mise run build:config-studio-assets`) into the run, leaving out the developer stack's run folder, downloads and backups."""
    staged = root / ".build" / "config-studio"
    if not (staged / "vocabulary.ttl").is_file():
        raise HarnessError(f"the studio's assets are not staged in {staged}. Run `mise run build:config-studio-assets`")
    shutil.copytree(staged, into, ignore=shutil.ignore_patterns("run", "infra", "*.trig"))
    return into


def remove(path: Path) -> None:
    if os.environ.get(KEEP_ENV):
        print(f"{KEEP_ENV} is set, so {path} is kept")
        return
    shutil.rmtree(path, ignore_errors=True)
