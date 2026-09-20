# SPDX-License-Identifier: MPL-2.0
"""Checks prerequisites and completed state for the ADR-A77 topology migration."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "docs" / "architecture" / "repository-topology-migration.json"
DECISIONS_PATH = ROOT / "docs" / "architecture" / "decisions"
LEGACY_ADR_PATH = ROOT / "docs" / "adr"
LEGACY_CURRENT_PATH = ROOT / "docs" / "developer" / "current"
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


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
    errors: list[str] = []
    for markdown_file in (ROOT / "docs").rglob("*.md"):
        text = markdown_file.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            target = target.strip()
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            path = target.split("#", 1)[0]
            if path and not (markdown_file.parent / path).resolve().exists():
                errors.append(f"broken link in {markdown_file.relative_to(ROOT)}: {target}")
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
