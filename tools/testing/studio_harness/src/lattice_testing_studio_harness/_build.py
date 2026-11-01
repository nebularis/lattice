# SPDX-License-Identifier: MPL-2.0
"""What a run needs from the checkout, taken as copies so a run never reads a file the developer's own stack writes."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from ._tools import catalogue
from .topology import HarnessError

JARS = {"service": "config-studio-service", "writer": "config-studio-writer"}
KEEP_ENV = "STUDIO_HARNESS_KEEP"
JARS_ENV = "LATTICE_STUDIO_HARNESS_JARS"
ASSETS_ENV = "LATTICE_STUDIO_HARNESS_ASSETS"
WORKER_ROOT_ENV = "LATTICE_STUDIO_HARNESS_WORKER_ROOT"


def harness_dir(root: Path) -> Path:
    return root / ".build" / "studio-harness"


def cache_dir(root: Path) -> Path:
    """Downloads, the extracted broker and the jars, shared by runs. Not a run id, so no run's folder collides with it."""
    return harness_dir(root) / "_cache"


def jars(root: Path) -> Dict[str, Path]:
    """The service's and the writer's jars, copied once into the cache under their content hash.

    The copy is made from `platform/{module}/target/{module}.jar`, which is only read, so a stack running from those jars is not disturbed. A jar that is
    missing is built with Maven, which writes `target`, so that happens only in a checkout where no stack runs from `target`.
    `LATTICE_STUDIO_HARNESS_JARS` names a folder to use instead, either holding the two jars or being another checkout's `platform` folder."""
    override = os.environ.get(JARS_ENV)
    platform = root / catalogue.load(root).area("platform")
    out: Dict[str, Path] = {}
    for key, module in JARS.items():
        if override:
            flat, nested = Path(override) / f"{module}.jar", Path(override) / module / "target" / f"{module}.jar"
            source = flat if flat.is_file() else nested
        else:
            source = platform / module / "target" / f"{module}.jar"
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
    staged = Path(os.environ[ASSETS_ENV]) if os.environ.get(ASSETS_ENV) else root / ".build" / "config-studio"
    if not (staged / "vocabulary.ttl").is_file():
        raise HarnessError(f"the studio's assets are not staged in {staged}. Run `mise run build:config-studio-assets`")
    shutil.copytree(staged, into, ignore=shutil.ignore_patterns("run", "infra", "*.trig"))
    return into


def web(root: Path, into: Path) -> Optional[Path]:
    """A copy of the built browser application (`apps/config-studio/dist`) for the service to serve, or nothing when it is not built."""
    built = root / catalogue.load(root).area("apps") / "config-studio" / "dist"
    if not (built / "index.html").is_file():
        return None
    shutil.copytree(built, into)
    return into


def worker_root(root: Path) -> Optional[Path]:
    """The checkout whose worker code runs, when `LATTICE_STUDIO_HARNESS_WORKER_ROOT` names another than `root`, so a benchmark can measure an older commit."""
    named = os.environ.get(WORKER_ROOT_ENV)
    return Path(named).resolve() if named and Path(named).resolve() != root.resolve() else None


def python_paths(root: Path) -> List[str]:
    """The source folders of a checkout's Python packages that the worker imports, to put first on `PYTHONPATH` ahead of the editable installs of this checkout."""
    c = catalogue.load(root)
    tools, packages = root / c.area("tools"), root / c.area("packages")
    found = [root / c.area("workers") / "src", tools, *sorted(tools.glob("*/src")), *sorted(packages.glob("*/python/src"))]
    return [str(p) for p in found if p.is_dir()]


def remove(path: Path) -> None:
    if os.environ.get(KEEP_ENV):
        print(f"{KEEP_ENV} is set, so {path} is kept")
        return
    shutil.rmtree(path, ignore_errors=True)
