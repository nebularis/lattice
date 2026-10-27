# SPDX-License-Identifier: MPL-2.0
"""Checks prerequisites and completed state for the ADR-A77 topology migration."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "docs" / "architecture" / "repository-topology-migration.json"
DECISIONS_PATH = ROOT / "docs" / "architecture" / "decisions"
LEGACY_ADR_PATH = ROOT / "docs" / "adr"
LEGACY_CURRENT_PATH = ROOT / "docs" / "developer" / "current"
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
FENCED_CODE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
# The first line of a copy that `tools/site_sections.py` writes into docs/_includes, which names its source.
GENERATED_COPY = re.compile(r"\A\{% comment %\}Copied from (\S+) by mise run build:site-sections")


def load_manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def validate_manifest(manifest: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if manifest.get("decision") != "ADR-A77":
        errors.append("manifest must name ADR-A77")
    if not isinstance(manifest.get("moves"), list):
        errors.append("manifest must contain a moves array")
    if not isinstance(manifest.get("nonMoves"), list):
        errors.append("manifest must contain a nonMoves array")
    for move in manifest.get("moves", []):
        if not isinstance(move, dict) or not isinstance(move.get("from"), str):
            errors.append("each move must name a source path")
        elif "to" not in move:
            errors.append(f"move {move['from']} must name a destination")
    return errors


def check_preflight(manifest: dict[str, object]) -> list[str]:
    errors = validate_manifest(manifest)
    if not DECISIONS_PATH.is_dir():
        errors.append("docs/architecture/decisions must exist")
    if not (DECISIONS_PATH / "ADR-A77-repository-topology-and-documentation-governance.md").is_file():
        errors.append("ADR-A77 must exist in the decisions catalogue")
    if LEGACY_ADR_PATH.exists():
        errors.append("docs/adr must be removed before semantic roots move")
    if LEGACY_CURRENT_PATH.exists():
        errors.append("docs/developer/current must be removed before semantic roots move")
    return errors


def destination_paths(move: dict[str, object]) -> list[str]:
    destination = move["to"]
    return destination if isinstance(destination, list) else [destination]


def check_ready(manifest: dict[str, object]) -> list[str]:
    errors = check_preflight(manifest)
    for move in manifest["moves"]:
        source = ROOT / move["from"]
        if not source.exists():
            errors.append(f"missing migration source: {move['from']}")
        for destination in destination_paths(move):
            if (ROOT / destination).exists():
                errors.append(f"destination already exists: {destination}")
    return errors


def check_links() -> list[str]:
    return check_links_in(f for f in (ROOT / "docs").rglob("*.md") if "vendor" not in f.parts)


def _name(path: Path) -> str:
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


def check_links_in(markdown_files) -> list[str]:
    """Broken local links in the given Markdown files, for example the files a commit touches
    (ADR-A133). A link resolves against its file's directory, or its source's for a generated copy."""
    errors: list[str] = []
    for markdown_file in markdown_files:
        markdown_file = Path(markdown_file)
        if not markdown_file.is_absolute():
            markdown_file = ROOT / markdown_file
        if not markdown_file.is_file():
            continue
        text = markdown_file.read_text(encoding="utf-8")
        # A generated copy is verbatim, so its links are relative to the source it was copied from.
        copied = GENERATED_COPY.match(text)
        base = (ROOT / copied.group(1)).parent if copied else markdown_file.parent
        # Text in a fenced block, such as a regular expression like [A](x), is not a link.
        for target in MARKDOWN_LINK.findall(FENCED_CODE.sub("", text)):
            target = unquote(target.strip())
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            path = target.split("#", 1)[0]
            if path and not (base / path).resolve().exists():
                errors.append(f"broken link in {_name(markdown_file)}: {target}")
    return errors


def check_completed(manifest: dict[str, object]) -> list[str]:
    errors = check_preflight(manifest)
    for move in manifest["moves"]:
        source = ROOT / move["from"]
        for destination in destination_paths(move):
            if not (ROOT / destination).exists():
                errors.append(f"missing destination: {destination}")
        if source.exists():
            errors.append(f"legacy source remains: {move['from']}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--completed", action="store_true", help="assert completed relocation state")
    parser.add_argument("--ready", action="store_true", help="assert semantic-root move prerequisites")
    parser.add_argument("--links", action="store_true", help="check local Markdown links under docs")
    arguments = parser.parse_args()

    manifest = load_manifest()
    if arguments.completed:
        errors = check_completed(manifest)
    elif arguments.ready:
        errors = check_ready(manifest)
    elif arguments.links:
        errors = check_links()
    else:
        errors = check_preflight(manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("repository topology migration check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
