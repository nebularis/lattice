# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The documentation site's sections (OD-D29 to OD-D31, TD-50). The repository catalogue declares them.

``build`` copies each source that lies outside ``docs/`` into ``docs/_includes/<section>/``, mirroring its path
and wrapped in Liquid ``raw`` tags so Jekyll shows it as written, and writes the sections' layouts and titles
into ``docs/_config.yml`` as Jekyll ``defaults``. ``check`` fails when a copy or the defaults are stale, when a
section's page does not show one of its sources, and when a page, layout or source is missing.

Usage, from the repository root::

    mise run build:site-sections
    mise run check:site-sections
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue as rc  # noqa: E402

CONFIG = "docs/_config.yml"
INCLUDES = "docs/_includes"
BEGIN = "# BEGIN GENERATED site-sections. Written by `mise run build:site-sections`. Do not edit by hand."
END = "# END GENERATED site-sections"
REGION_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n", re.S)


def expand(root: Path, source: str) -> List[str]:
    """The files a source names, a directory giving every file under it, as paths from the root."""
    path = root / source
    if path.is_dir():
        return sorted(p.relative_to(root).as_posix() for p in path.rglob("*") if p.is_file() and not p.name.startswith("."))
    return [source]


def copies(catalogue: rc.Catalogue) -> Dict[str, str]:
    """Destination path (from the root) to content, for every source outside docs/."""
    plan: Dict[str, str] = {}
    for section in catalogue.site:
        for source in section.sources:
            if source.startswith("docs/"):
                continue
            for file in expand(catalogue.root, source):
                text = (catalogue.root / file).read_text(encoding="utf-8")
                if "{% endraw %}" in text:
                    raise rc.CatalogueError(f"{file} holds a Liquid endraw tag, so it cannot be copied into the site")
                plan[f"{INCLUDES}/{section.name}/{file}"] = (
                    f"{{% comment %}}Copied from {file} by mise run build:site-sections. Do not edit.{{% endcomment %}}\n"
                    f"{{% raw %}}\n{text.rstrip(chr(10))}\n{{% endraw %}}\n")
    return plan


def managed_directories(catalogue: rc.Catalogue) -> List[str]:
    return [f"{INCLUDES}/{s.name}" for s in catalogue.site if any(not x.startswith("docs/") for x in s.sources)]


def defaults(catalogue: rc.Catalogue) -> str:
    """The generated region of docs/_config.yml, a layout and title for each section page that takes a layout."""
    lines = [BEGIN, "defaults:"]
    for s in catalogue.site:
        if s.layout == "none":
            continue
        lines += [f"  - scope:", f"      path: {json.dumps(s.page[len('docs/'):])}", "    values:",
                  f"      layout: {s.layout}", f"      title: {json.dumps(s.title)}"]
    return "\n".join(lines + [END]) + "\n"


def needle(section: rc.Section, source: str) -> str:
    """The text a section's page must hold to show one source: the include path, or the file's stem."""
    stem = source.rsplit(".", 1)[0]
    if source.startswith(f"{INCLUDES}/"):
        return stem[len(INCLUDES) + 1:]
    if source.startswith("docs/"):
        return Path(source).stem
    return f"{section.name}/{stem}"


def problems(catalogue: rc.Catalogue) -> List[str]:
    found = rc._site_problems(catalogue)
    root = catalogue.root
    plan = copies(catalogue)
    for dest, text in plan.items():
        path = root / dest
        if not path.is_file():
            found.append(f"{dest} is missing. Run mise run build:site-sections")
        elif path.read_text(encoding="utf-8") != text:
            found.append(f"{dest} is stale. Run mise run build:site-sections")
    for directory in managed_directories(catalogue):
        for path in sorted((root / directory).rglob("*")) if (root / directory).is_dir() else []:
            if path.is_file() and path.relative_to(root).as_posix() not in plan:
                found.append(f"{path.relative_to(root).as_posix()} is a copy of nothing the catalogue lists. Run mise run build:site-sections")
    config = (root / CONFIG).read_text(encoding="utf-8") if (root / CONFIG).is_file() else ""
    region = REGION_RE.search(config)
    if region is None or region.group(0) != defaults(catalogue):
        found.append(f"{CONFIG} holds stale section defaults. Run mise run build:site-sections")
    for s in catalogue.site:
        page = root / s.page
        text = page.read_text(encoding="utf-8") if page.is_file() else ""
        for source in s.sources:
            for file in expand(root, source) if (root / source).exists() else []:
                if needle(s, file) not in text:
                    found.append(f"site {s.name}: {s.page} does not show {file}")
    return found


def build(catalogue: rc.Catalogue) -> None:
    root = catalogue.root
    plan = copies(catalogue)
    for directory in managed_directories(catalogue):
        for path in sorted((root / directory).rglob("*")) if (root / directory).is_dir() else []:
            if path.is_file() and path.relative_to(root).as_posix() not in plan:
                path.unlink()
    for dest, text in plan.items():
        (root / dest).parent.mkdir(parents=True, exist_ok=True)
        (root / dest).write_text(text, encoding="utf-8", newline="\n")
    config = (root / CONFIG).read_text(encoding="utf-8")
    new = defaults(catalogue)
    config = REGION_RE.sub(lambda _: new, config) if REGION_RE.search(config) else config.rstrip("\n") + "\n" + new
    (root / CONFIG).write_text(config, encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The documentation site's sections (OD-D29)")
    parser.add_argument("command", choices=("build", "check"))
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)
    try:
        catalogue = rc.load(args.root)
        if args.command == "build":
            build(catalogue)
            print(f"site sections: {len(copies(catalogue))} copy(ies) written, defaults for {len(catalogue.site)} section(s)")
            return 0
        found = problems(catalogue)
    except rc.CatalogueError as error:
        print(f"SITE {error}", file=sys.stderr)
        return 1
    for item in found:
        print(f"SITE {item}", file=sys.stderr)
    if not found:
        print(f"site sections: {len(catalogue.site)} section(s), {len(copies(catalogue))} copy(ies) current")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
