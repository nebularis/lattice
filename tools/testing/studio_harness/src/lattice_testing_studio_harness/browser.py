# SPDX-License-Identifier: MPL-2.0
"""`mise run test:config-studio-browser`. Runs both browser suites of the studio: the journeys against the in-memory fake service, then
the real-stack suite against a single topology the harness starts in isolation from freshly packaged jars, so a developer's own stack is never touched. Exits
with the first failing suite's code."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import List, Optional

from ._tools import catalogue
from .topology import Topology

WORKSPACE = "@lattice/config-studio"


def yarn(root, script: str, env: Optional[dict] = None) -> int:
    return subprocess.run(["yarn", "workspace", WORKSPACE, "run", script], cwd=root, env={**os.environ, **(env or {})}).returncode


def main(argv: Optional[List[str]] = None) -> int:
    root = catalogue.find_root(None)
    for script in ("build", "test"):
        code = yarn(root, script)
        if code:
            return code
    # The jars are packaged afresh, since the harness builds one only when it is missing. A running stack runs from its own copies (STD-300).
    platform = root / catalogue.load(root).area("platform")
    subprocess.run(["mvn", "-q", "-f", str(platform / "pom.xml"), "-pl", "config-studio-service,config-studio-writer", "-am", "package", "-DskipTests"],
                   cwd=root, check=True)
    with Topology(name="browser").start(root=root) as studio:
        return yarn(root, "test:stack", {"LATTICE_STUDIO_URL": studio.url, "LATTICE_STUDIO_EVENTS_TLS": "1"})


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
