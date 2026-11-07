#!/usr/bin/env python3
"""Remove build output and caches, the same on Windows, Linux and macOS (STD-322), for the `clean:*` tasks.

`python` removes Python caches and build folders, `frontend` Node and Yarn artefacts and the frontend build output and
then runs `yarn cache clean`, `build` the generated build outputs, and `docs` the local Jekyll and Bundler artefacts,
never the committed Gemfile. A folder's dotfiles, such as `.gitkeep`, stay where only its contents go. A path that is
not there is skipped. Nothing under `.git`, `.venv` or `node_modules` is walked for caches."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lattice_repo_catalogue as rc  # noqa: E402

NOT_WALKED = {".git", ".venv", "node_modules"}


def remove(path: Path) -> None:
    """``path`` and everything under it. A link or a junction is removed, never what it points at. A read-only file,
    which Windows refuses to delete, is made writable first."""
    def writable_then_retry(function: Callable, name: str, _error: BaseException) -> None:
        os.chmod(name, stat.S_IWRITE)
        function(name)

    if path.is_symlink() or path.is_junction() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path, onexc=writable_then_retry)


def contents(folder: Path) -> list[Path]:
    """What a folder holds, its dotfiles left out."""
    return [p for p in folder.iterdir() if not p.name.startswith(".")] if folder.is_dir() else []


def caches(root: Path, names: tuple[str, ...]) -> Iterable[Path]:
    """Every folder under ``root`` whose name matches one of ``names``, outside the folders never walked."""
    for here, folders, _ in os.walk(root):
        folders[:] = [f for f in folders if f not in NOT_WALKED]
        for folder in list(folders):
            if any(Path(folder).match(name) for name in names):
                folders.remove(folder)
                yield Path(here) / folder


def python(catalogue: rc.Catalogue) -> int:
    root = catalogue.root
    targets = [*contents(root / ".build" / "pytest-cache"), root / ".pytest_cache", root / "__pycache__", root / "build",
               *root.glob("*.egg-info"), root / catalogue.area("workers") / "build"]
    targets += list(caches(root, ("__pycache__", "*.egg-info")))
    for target in targets:
        remove(target)
    return 0


def frontend(catalogue: rc.Catalogue) -> int:
    root = catalogue.root
    apps = root / catalogue.area("apps")
    targets = [root / "node_modules", root / ".yarn", *apps.glob("*/node_modules"), *apps.glob("*/dist"),
               *contents(root / ".build" / "yarn-cache")]
    for results in (root / ".build").glob("*-test-results"):
        targets += contents(results)
    for target in targets:
        remove(target)
    yarn = shutil.which("yarn")
    if yarn is None:
        print("clean: yarn is not on the path, so its cache was not cleaned", file=sys.stderr)
        return 0
    return subprocess.run([yarn, "cache", "clean"], cwd=root).returncode


def build(catalogue: rc.Catalogue) -> int:
    root = catalogue.root
    for target in (root / "build", root / catalogue.module("mork").directory("mtp") / "out",
                   root / ".build" / "authoring", root / ".build" / "config-studio"):
        remove(target)
    return 0


def docs(catalogue: rc.Catalogue) -> int:
    root = catalogue.root
    site = root / Path(catalogue.site[0].page).parent  # the folder of the site's home page
    for name in ("vendor", ".bundle", "_site", ".jekyll-cache", ".jekyll-metadata"):
        remove(site / name)
    return 0


AREAS = {"python": python, "frontend": frontend, "build": build, "docs": docs}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("area", choices=sorted(AREAS))
    args = parser.parse_args(argv)
    return AREAS[args.area](rc.load())


if __name__ == "__main__":
    sys.exit(main())
