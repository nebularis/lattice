# SPDX-License-Identifier: MPL-2.0
"""Runs a compiled transform on its engine through `platform/mork-transforms`'s command line (ADR-A148 decision 7),
built by `mise run bootstrap:mork-transforms`. ``LATTICE_MORK_TRANSFORMS`` overrides the jar's path."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

JAR_RELATIVE = Path("platform/mork-transforms/target/mork-transforms.jar")


class EngineError(RuntimeError):
    """The engine refused the transform or its source."""


def jar() -> Path:
    """The jar. ``LATTICE_MORK_TRANSFORMS`` first, then the repository's build output, found as the catalogue reader
    finds the root (``LATTICE_ROOT``, then the nearest directory at or above the working directory that holds
    ``repository-catalogue.md``), never from this file's location (STD-273)."""
    if os.environ.get("LATTICE_MORK_TRANSFORMS"):
        return Path(os.environ["LATTICE_MORK_TRANSFORMS"])
    if os.environ.get("LATTICE_ROOT"):
        return Path(os.environ["LATTICE_ROOT"]) / JAR_RELATIVE
    here = Path.cwd().resolve()
    return next((c / JAR_RELATIVE for c in (here, *here.parents) if (c / "repository-catalogue.md").is_file()), here / JAR_RELATIVE)


def available() -> bool:
    return jar().is_file() and shutil.which("java") is not None


def run(engine: str, transform: str, source: str, *, timeout: int = 120) -> str:
    """The output of `transform`, an XSLT stylesheet for engine "xslt" or a JOLT chain for "jolt", on `source`."""
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix="." + engine, encoding="utf-8", delete=False) as f:
        f.write(transform)
    try:
        done = subprocess.run(["java", "-jar", str(jar()), engine, f.name], input=source.encode("utf-8"),
                              capture_output=True, timeout=timeout)
    finally:
        os.unlink(f.name)
    if done.returncode != 0:
        raise EngineError(done.stderr.decode("utf-8", "replace").strip())
    return done.stdout.decode("utf-8")
