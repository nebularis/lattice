# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Extract each literate README a version bump changed, then regenerate the XML catalogs and the release
register, which read the generated documents.

It reads ``<README>\\t<module>`` lines, as ``bump_version.py`` prints them, from stdin, or, given
``bump_version.py``'s arguments, runs it first and reads its output. The second form is what the mise task
``version:bump`` uses, since a task's arguments cannot reach the first command of a pipe portably::

    mise exec -- python tools/bump_version.py --layer-target persistence --increment minor | mise exec -- python tools/extract_bumped.py
    mise run version:bump -- --layer-target persistence --increment minor
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

TOOLS = Path(__file__).resolve().parent


def extract_args(root: Path, readme: str, module: str) -> list[str]:
    """The extractor's arguments for one README, as the literate hook check passes them."""
    args = [str(TOOLS / "literate_extract.py"), readme, "--layer", module, "--root", "."]
    if "isabelle-spec" in (root / readme).read_text(encoding="utf-8"):
        args += ["--proofs-root", "tools/proofs", "--reference-root", "tools/reference"]
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    sys.path.insert(0, str(TOOLS))
    import lattice_repo_catalogue
    root = lattice_repo_catalogue.find_root(None)
    if {"-h", "--help"} & set(argv):
        return subprocess.run([sys.executable, str(TOOLS / "bump_version.py"), *argv], cwd=root).returncode
    if argv:
        bumped = subprocess.run([sys.executable, str(TOOLS / "bump_version.py"), *argv], cwd=root, stdout=subprocess.PIPE, text=True)
        if bumped.returncode:
            return bumped.returncode
        lines = bumped.stdout.splitlines()
    else:
        lines = sys.stdin.read().splitlines()
    for line in filter(None, (l.strip() for l in lines)):
        readme, module = line.split("\t")
        print(f"extracting {readme}", file=sys.stderr)
        if subprocess.run([sys.executable, *extract_args(root, readme, module)], cwd=root).returncode:
            print(f"BUMP {readme} did not extract. Its version IRIs are bumped, and its generated files are not", file=sys.stderr)
            return 1
    for command in (["ontology_catalog.py", "write"], ["ontology_releases.py", "write"]):
        subprocess.run([sys.executable, str(TOOLS / command[0]), *command[1:]], cwd=root, check=True)
    print("done. Read the lines above, run `mise run check:ontology-versioning -- --base-ref main` and `mise run check`, "
          "and list the tags `build:ontology-releases` added for the maintainer", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
