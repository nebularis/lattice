"""Curated doctrine validation and axiom ownership checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .facts import Facts


def load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def check(doctrine: dict[str, Any], facts: Facts) -> list[str]:
    anchors = {entry["iri"]: entry for entry in doctrine.get("anchors", [])}
    known_terms = {term.iri for term in facts.terms}
    findings = [f"anchor.missing:{iri}" for iri in anchors if iri not in known_terms]
    owned = {entry.get("fingerprint") for entry in doctrine.get("covers", [])} | set(doctrine.get("deferrals", []))
    if "*" not in owned:
        findings.extend(f"axiom.unowned:{axiom.fingerprint}" for axiom in facts.axioms if axiom.fingerprint not in owned)
    return findings