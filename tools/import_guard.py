# SPDX-License-Identifier: MPL-2.0
"""Import guard: no substrate layer imports, or names, a layer above it
(ADR-A01 and its 2026-10-01 addendum, ADR-A106 law B7).

Two checks over the substrate layers of the order (CCS C10a, C10a-Q2):

* every ``owl:imports`` of an ontology document under a layer names the same
  layer or one the order allows below it
* no ``.ttl`` file under a layer names the namespace of a layer it may not
  import: a higher layer, a sibling, or any applied module

Applied modules, MORK, SPC, Surface, Persistence and ``ontology/examples`` are
outside the order and not checked.

Usage::

    python tools/import_guard.py [--root <repository root>]
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from rdflib import Graph
from rdflib.namespace import OWL

ROOT = Path(__file__).resolve().parent.parent

# The order of ADR-A01's 2026-10-01 addendum: each layer and the layers it may
# import. Wording and Behaviour are siblings, so neither may name the other.
# Behaviour's configuration and runtime documents share one namespace and one
# entry. The runtime document imports configuration, which is the same layer.
SUBSTRATE = ("foundation", "vocabulary", "quantification", "party", "eligibility")
ALLOWED: dict[str, frozenset[str]] = {
    "foundation": frozenset(),
    "vocabulary": frozenset(SUBSTRATE[:1]),
    "quantification": frozenset(SUBSTRATE[:2]),
    "party": frozenset(SUBSTRATE[:3]),
    "eligibility": frozenset(SUBSTRATE[:4]),
    "wording": frozenset(SUBSTRATE),
    "behaviour": frozenset(SUBSTRATE),
    "instrument": frozenset(SUBSTRATE) | {"wording", "behaviour"},
}
APPLIED = "applied"

# A LATTICE IRI names a layer by the first path segment after lattice/:
# lattice/behaviour#, lattice/behaviour-runtime/0.8.0, lattice/wording/vocab#.
LATTICE_IRI = re.compile(r"https://www\.nebularis\.org/neuro-semantic/lattice/([a-z]+)")


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    layer: str
    named: str
    kind: str

    def render(self, root: Path) -> str:
        where = self.path.relative_to(root) if self.path.is_relative_to(root) else self.path
        return f"{where}:{self.line}: {self.layer} {self.kind} {self.named}, which the order does not allow"


def forbidden(layer: str, named: str) -> bool:
    """Whether ``layer`` may not name ``named``. Modules outside the order are not judged."""
    if named == layer:
        return False
    if named == APPLIED:
        return True
    return named in ALLOWED and named not in ALLOWED[layer]


def layer_files(root: Path) -> Iterator[tuple[str, Path]]:
    for layer in ALLOWED:
        directory = root / "ontology" / layer
        if directory.is_dir():
            for path in sorted(directory.rglob("*.ttl")):
                yield layer, path


def import_violations(layer: str, path: Path) -> Iterator[Violation]:
    graph = Graph().parse(path, format="turtle")
    lines = path.read_text().splitlines()
    for target in sorted(str(t) for t in graph.objects(None, OWL.imports)):
        match = LATTICE_IRI.match(target)
        if match and forbidden(layer, match.group(1)):
            line = next((n for n, text in enumerate(lines, 1) if target in text), 0)
            yield Violation(path, line, layer, target, "imports")


def name_violations(layer: str, path: Path) -> Iterator[Violation]:
    for number, text in enumerate(path.read_text().splitlines(), 1):
        for match in LATTICE_IRI.finditer(text):
            if forbidden(layer, match.group(1)):
                yield Violation(path, number, layer, match.group(0), "names")


def check(root: Path) -> list[Violation]:
    found: list[Violation] = []
    for layer, path in layer_files(root):
        imports = list(import_violations(layer, path))
        reported = {v.line for v in imports}
        found += imports + [v for v in name_violations(layer, path) if v.line not in reported]
    return found


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(ROOT), help="repository root (default: repo root)")
    root = Path(parser.parse_args(argv).root).resolve()
    violations = check(root)
    for violation in violations:
        print(violation.render(root))
    print(f"import guard: {len(violations)} violation(s) across {len(ALLOWED)} substrate layers")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
