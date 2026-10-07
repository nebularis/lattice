#!/usr/bin/env python3
"""Builds track D's pinned image set (mise task bootstrap:formal-images), cross-platform.

Stages an optional extra root CA into each build context as extra-ca.crt (named by
NODE_EXTRA_CA_CERTS, following the general toolchain-feasibility spike's convention) and removes
it afterwards, so it is never left in an image layer or committed to git.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ENV_DIR = Path(__file__).resolve().parent
IMAGES = {
    "rocq-metarocq": "lattice-fm/rocq-metarocq:spike",
    "ghc-wasm": "lattice-fm/ghc-wasm:spike",
}


def staged_ca(context: Path) -> Path:
    target = context / "extra-ca.crt"
    ca = os.environ.get("NODE_EXTRA_CA_CERTS")
    if ca and Path(ca).is_file():
        shutil.copyfile(ca, target)
    else:
        target.write_text("")
    return target


def main() -> int:
    only = sys.argv[1:] or list(IMAGES)
    for name in only:
        tag = IMAGES[name]
        context = ENV_DIR / "docker" / name
        ca_file = staged_ca(context)
        try:
            print(f"+ docker build -t {tag} {context}", file=sys.stderr)
            result = subprocess.run(["docker", "build", "-t", tag, str(context)])
            if result.returncode != 0:
                return result.returncode
        finally:
            ca_file.unlink(missing_ok=True)
    subprocess.run(["docker", "image", "ls", "lattice-fm/*", "--format", "{{.Repository}}:{{.Tag}} {{.Size}}"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
