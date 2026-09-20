"""Deterministic L0 and manifest rendering."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .budget import require_budget
from .facts import Facts


def render_l0(doctrine: dict, facts: Facts) -> str:
    invariants = doctrine.get("invariants", [])
    pairs = doctrine.get("minimal_pairs", [])
    text = "# MORK Teaching Pack L0\n\n## Invariants\n" + "\n".join(f"- {item}" for item in invariants) + "\n\n## Decision ladder\n" + "\n".join(f"{index + 1}. {item}" for index, item in enumerate(doctrine.get("decision_ladder", []))) + "\n\n## Minimal pairs\n" + "\n".join(f"- {pair}" for pair in pairs) + f"\n\nOntology hash: `{facts.graph_hash}`\n"
    require_budget(text, 900, "l0")
    return text


def write_manifest(out: Path, files: list[Path], pack_version: str) -> None:
    rows = {str(path.relative_to(out)): "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}
    (out / "manifest.json").write_text(json.dumps({"mtp_version": pack_version, "files": rows}, indent=2) + "\n", encoding="utf-8")


def manifest_drift(out: Path) -> list[str]:
    manifest = out / "manifest.json"
    if not manifest.exists():
        return ["output.stale:manifest-missing"]
    expected = json.loads(manifest.read_text(encoding="utf-8")).get("files", {})
    actual = {str(path.relative_to(out)): "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() for path in out.rglob("*") if path.is_file() and path.name != "manifest.json"}
    return [f"output.stale:{name}" for name in sorted(set(expected) | set(actual)) if expected.get(name) != actual.get(name)]