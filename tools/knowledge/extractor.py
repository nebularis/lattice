# SPDX-License-Identifier: MPL-2.0
"""LATTICE's extractor for Вивід: the catalogue's units with their folders, so an Owner cell of a register names a module, a tool
package, a root or a documentation area (ADR-A152 decision 1).

`vyd build` runs it as the command the `[[project.extractors]]` entry of vyvid.toml declares, in the checkout's root, with one JSON
request on standard input, and reads `result.json` from the output folder the request names. It writes no quads. The architectural
quanta (ADR-A134 addendum of 2026-10-25) are Вивід's own `quanta` kind, which takes its modules from the catalogue, and the rules of
a quantum are Вивід's (plan vyvid-migration, VM-9). The catalogue is read by its own reader (ADR-A121), never from a path written
here. Standard library only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import lattice_repo_catalogue  # noqa: E402

VERSION = "2"


def units(catalogue) -> dict[str, list[str]]:
    """The units an Owner value may name, each to the units it stands for: a module by name, a tool package by name
    or path, a root or documentation area by path, and a module kind for every module of that kind."""
    out: dict[str, list[str]] = {}
    for tool in catalogue.tools:
        out[tool.name] = out[tool.path] = [tool.path]
    for area in catalogue.roots + catalogue.docs:
        out[area.path.rstrip("/")] = [area.path.rstrip("/")]
    for kind in {m.kind for m in catalogue.modules.values()}:
        out[kind] = [m.name for m in catalogue.modules_of_kind(kind)]
    for name in catalogue.modules:
        out[name] = [name]
    return out


def unit_paths(catalogue, root: Path) -> dict[str, str]:
    """Each unit's folder, so a term declared under it is owned by that unit and meets an Owner edge. Вивід takes the
    longest path, so a module's folder wins over its root's."""
    out = {area.path.rstrip("/"): area.path.rstrip("/") for area in catalogue.roots + catalogue.docs}
    out.update({tool.path: tool.path for tool in catalogue.tools})
    out.update({(root / m.path).resolve().relative_to(root).as_posix(): m.name for m in catalogue.modules.values()})
    return out


def extract(request: dict) -> dict:
    root = Path(request["root"]).resolve()
    catalogue = lattice_repo_catalogue.load(root)
    return {"protocol": request["protocol"], "version": VERSION, "problems": [], "findings": [], "texts": {}, "prefixes": {}, "counts": {},
            "units": units(catalogue), "unit_paths": unit_paths(catalogue, root)}


def main() -> int:
    request = json.load(sys.stdin)
    result = extract(request)
    output = Path(request["output"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "result.json").write_text(json.dumps(result, indent=1), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
