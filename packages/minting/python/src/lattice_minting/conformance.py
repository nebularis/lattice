# SPDX-License-Identifier: MPL-2.0
"""Running conformance vectors against this library
(identity-minting-specification.md §10).

Accepts a vectors document or an anchors document. For each positive vector
it mints from ``inputs`` and compares **every trace step** with the vector,
then the IRIs. The ``ucd`` member of a normalize step is a citation for
readers and is not compared. Negative vectors must raise the named error.
Format vectors check their accept and reject examples against the pattern
and, for random strategies, freshly minted identifiers too."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .errors import MintError
from .minter import Minter
from .recipe import Recipe


@dataclass
class Report:
    passed: int = 0
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def check(self, where: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
        else:
            self.failures.append(f"{where}: {detail}")


def _strip(step: Mapping) -> dict:
    return {k: v for k, v in step.items() if k != "ucd"}


def _first_difference(want: list, got: list) -> str:
    for i, (w, g) in enumerate(zip(want, got)):
        if _strip(w) != _strip(g):
            return f"step {i} ({w.get('step')}): expected {_strip(w)}, got {_strip(g)}"
    return f"trace length: expected {len(want)} steps, got {len(got)}"


def verify_set(doc: Mapping, report: Report, label: str = "") -> None:
    where = label or doc.get("description", "vectors")[:40]
    try:
        recipe = Recipe.parse(doc["recipe"])
    except MintError as e:
        report.check(f"{where} recipe", False, str(e))
        return
    report.check(f"{where} recipe", True)
    secrets = {k: bytes.fromhex(v["hex"]) for k, v in doc.get("testSecrets", {}).items()}
    for vec in doc["positive"]:
        at = f"{where} {vec['id']}"
        try:
            minted = Minter(recipe, secrets).mint(vec["inputs"])
        except MintError as e:
            report.check(at, False, f"raised {e}")
            continue
        same = [_strip(s) for s in minted.trace] == [_strip(s) for s in vec["trace"]]
        report.check(f"{at} trace", same, "" if same else _first_difference(vec["trace"], minted.trace))
        report.check(f"{at} iri", minted.iri == vec["iri"], f"expected {vec['iri']}, got {minted.iri}")
        if "claimIris" in vec:
            report.check(f"{at} claimIris", minted.claim_iris == vec["claimIris"], f"expected {vec['claimIris']}, got {minted.claim_iris}")
    for vec in doc["negative"]:
        at = f"{where} {vec['id']}"
        inputs = dict(vec["inputs"])
        omit = inputs.pop("omitSecret", None)
        use = {k: v for k, v in secrets.items() if k != omit}
        try:
            minted = Minter(recipe, use).mint(inputs)
            report.check(at, False, f"expected {vec['error']}, minted {minted.iri}")
        except MintError as e:
            report.check(at, e.kind == vec["error"], f"expected {vec['error']}, got {e.kind}")
    for vec in doc["format"]:
        at = f"{where} {vec['id']}"
        for s in vec["accept"]:
            report.check(f"{at} accept", re.fullmatch(vec["pattern"], s) is not None, s)
        for s in vec["reject"]:
            report.check(f"{at} reject", re.fullmatch(vec["pattern"], s) is None, s)
        if recipe.strategy == "RandomSurrogateIdentity":
            for _ in range(5):
                iri = Minter(recipe).mint({}).iri
                report.check(f"{at} minted", re.fullmatch(vec["pattern"], iri) is not None, iri)


def verify(source: str | Path | Mapping) -> Report:
    """Verify a vectors or anchors document (a path, JSON text, or parsed)."""
    if isinstance(source, Path) or (isinstance(source, str) and not source.lstrip().startswith("{")):
        doc = json.loads(Path(source).read_text(encoding="utf-8"))
    elif isinstance(source, str):
        doc = json.loads(source)
    else:
        doc = source
    report = Report()
    if "sets" in doc:
        for i, s in enumerate(doc["sets"]):
            verify_set(s, report, f"set {i} ({s['recipe'].get('strategy')})")
    else:
        verify_set(doc, report)
    return report
