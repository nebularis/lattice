# SPDX-License-Identifier: MPL-2.0
"""Checks that formal-methods artefacts stay in sync with the literate README
they are built from or checked against — the same discipline
``literate_extract.py --check`` already gives Surface/Wording/Behaviour/
Quantification/Instrument's compiled Turtle (epic principle E1, ADR-A-FM2),
extended here to track E's mechanised theories and track B's hand-written
references.

Two checks, run per layer:

1. **Kernel.thy freshness** (every ``tools/proofs/<layer>/`` directory). The
   layer's README ``isabelle-spec`` blocks, re-extracted, must equal what is
   committed at ``tools/proofs/<layer>/Kernel.thy`` byte for byte. A changed
   README that adds, removes or edits a datatype without regenerating
   ``Kernel.thy`` is caught here, exactly as a changed Surface README's
   ``turtle-spec`` block is caught by ``literate_extract.py --check``.

   This does **not** call that script's own ``--check`` mode directly, which
   also compares a layer's ``spec``/``vocab``/``shapes`` output and would
   fail on TD-16's existing, unrelated drift in several layers (Vocabulary,
   Party, Eligibility — see ``docs/developer/plans/technical-debt.md``).
   Instead it calls ``parse_blocks``/``plan``/``render`` as a library and
   checks only the ``@proofs-root@`` output, the same narrow extraction
   E1.0 used when Eligibility's README was first wired (see
   ``docs/developer/status/formal-methods-track-e.md``). The shape and spec
   targets passed to ``plan()`` are placeholders, matched only in count to
   the README's own ``turtle-shapes`` blocks (``plan()`` requires the
   counts to agree) — their content is never read or compared.

2. **Law coverage** (every ``tools/reference/<layer>/`` directory). Every
   law code the README's law register declares with ``elg:lawRegister
   elg:SemanticLaw`` (or the same pattern for another layer's own law
   prefix — a ``StaticConstraint`` is SHACL's business, never a reference
   semantics', and is excluded here) must be named somewhere in the
   reference package's own Python or its own ``README.md`` — covered, or
   explicitly disclaimed as out of scope, either is acceptable, silence is
   not. A semantic law added to the ontology's README with no mention
   anywhere in the reference package is flagged: a prompt to decide
   whether it belongs in scope, not proof the reference is already wrong.

Exits non-zero if either check finds drift, printing what and where, in the
same ``DRIFT <path>`` style ``literate_extract.py --check`` already uses.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from literate_extract import parse_blocks, plan  # noqa: E402  (sibling script import)

ROOT = Path(__file__).resolve().parent.parent
PROOFS_ROOT = ROOT / "tools" / "proofs"
REFERENCE_ROOT = ROOT / "tools" / "reference"
ONTOLOGY_ROOT = ROOT / "ontology"

LAW_START_RE = re.compile(r"(?P<prefix>[a-z]+):L(?P<number>\d+)\s+a\s+(?P=prefix):Law\b")


def _semantic_laws(readme_text: str) -> List[str]:
    """Every law code declared ``elg:lawRegister elg:SemanticLaw`` (or the
    same pattern for another layer's own law prefix) in the README's
    vocabulary. Only these need a reference semantics at all — a
    ``StaticConstraint`` (or a law with no declared register, today's
    convention for a handful of structural laws) is discharged by SHACL
    directly and is never this check's business."""
    starts = list(LAW_START_RE.finditer(readme_text))
    laws = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(readme_text)
        body = readme_text[match.start():end]
        if "SemanticLaw" in body:
            laws.append(f"{match.group('prefix')}:L{match.group('number')}")
    return laws


def check_kernel_freshness(layer: str) -> List[str]:
    """Return a list of drift messages for ``layer``'s ``Kernel.thy``, empty
    if none."""
    readme_path = ONTOLOGY_ROOT / layer / "README.md"
    kernel_path = PROOFS_ROOT / layer / "Kernel.thy"
    if not readme_path.is_file():
        return [f"{kernel_path}: no README at {readme_path} to check it against"]

    blocks = parse_blocks(readme_path.read_text(encoding="utf-8"))
    shape_block_count = sum(1 for b in blocks if b.tag == "turtle-shapes")
    placeholder_shapes = [f"shapes/__freshness_check_placeholder_{i}.ttl" for i in range(shape_block_count)]
    try:
        outputs = plan(blocks, layer, placeholder_shapes, proofs_root=str(PROOFS_ROOT))
    except ValueError as error:
        return [f"{kernel_path}: could not extract {readme_path}'s isabelle-spec blocks ({error})"]

    key = f"@proofs-root@/{layer}/Kernel.thy"
    if key not in outputs:
        return [f"{kernel_path}: exists, but {readme_path} has no isabelle-spec block any more"]

    expected = outputs[key]
    actual = kernel_path.read_text(encoding="utf-8") if kernel_path.exists() else None
    if actual != expected:
        return [f"{kernel_path}: drifted from {readme_path}'s isabelle-spec block(s) — regenerate with literate_extract.py --proofs-root tools/proofs"]
    return []


def check_law_coverage(layer: str) -> List[str]:
    """Return a list of drift messages for ``layer``'s reference-semantics
    law coverage, empty if none."""
    readme_path = ONTOLOGY_ROOT / layer / "README.md"
    reference_dir = REFERENCE_ROOT / layer
    if not readme_path.is_file():
        return [f"{reference_dir}: no README at {readme_path} to check it against"]

    readme_text = readme_path.read_text(encoding="utf-8")
    declared_laws = set(_semantic_laws(readme_text))
    if not declared_laws:
        return []

    reference_text = "\n".join(
        path.read_text(encoding="utf-8")
        for pattern in ("*.py", "*.md")
        for path in reference_dir.rglob(pattern)
    )
    missing = sorted(
        law for law in declared_laws
        if not re.search(r"\b" + re.escape(law.split(":", 1)[1]) + r"\b", reference_text)
    )
    if missing:
        return [
            f"{reference_dir}: {readme_path} declares {', '.join(missing)}, named nowhere in "
            f"{reference_dir}'s own Python — update the reference, or its README's stated scope, "
            f"or both"
        ]
    return []


def main() -> int:
    drift: List[str] = []
    if PROOFS_ROOT.is_dir():
        for layer_dir in sorted(p for p in PROOFS_ROOT.iterdir() if p.is_dir() and (p / "Kernel.thy").is_file()):
            drift.extend(check_kernel_freshness(layer_dir.name))
    if REFERENCE_ROOT.is_dir():
        for layer_dir in sorted(p for p in REFERENCE_ROOT.iterdir() if p.is_dir() and (p / "pyproject.toml").is_file()):
            drift.extend(check_law_coverage(layer_dir.name))

    if drift:
        for message in drift:
            print(f"DRIFT {message}", file=sys.stderr)
        print(f"{len(drift)} formal-methods freshness check(s) failed", file=sys.stderr)
        return 1

    checked = (
        sum(1 for p in PROOFS_ROOT.iterdir() if PROOFS_ROOT.is_dir() and p.is_dir() and (p / "Kernel.thy").is_file())
        + sum(1 for p in REFERENCE_ROOT.iterdir() if REFERENCE_ROOT.is_dir() and p.is_dir() and (p / "pyproject.toml").is_file())
    )
    print(f"{checked} formal-methods artefact(s) consistent with their literate READMEs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
