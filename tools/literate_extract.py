# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Literate-spec extractor.

A LATTICE layer's ``README.md`` is the authoritative specification. The compiled
Turtle under ``spec/``, ``vocab/`` and ``shapes/`` is mechanically extracted from
its fenced blocks, in document order, so the two artefacts cannot drift. An
``isabelle-spec`` block does the same for a layer's Isabelle theory's closed
datatypes (ADR-A-FM2, epic principle E1): the proofs and functions built on
top of those datatypes are hand-written directly in the ``.thy`` file, not
generated, since only the closed datatypes are meant to track the README.

Fence tags recognised:

====================  ================================================
``turtle-spec``       concatenated into ``spec/<layer>.ttl``, or into the
                      file its ``@output-file`` directive names
``turtle-vocab``      concatenated into ``vocab/<layer>-vocab.ttl``
``turtle-shapes``     written, in document order, to the shape files
                      named by the layer's extraction contract
``turtle-example``    never extracted
``isabelle-spec``     concatenated into ``<proofs-root>/<layer>/Kernel.thy``
====================  ================================================

Each extracted ``.ttl``/``.thy`` gains the project's SPDX header as its first
line (``#``-style for Turtle, ``(* ... *)``-style for Isabelle).

A layer with more than one spec document (ADR-A120) sends a ``turtle-spec``
block elsewhere with a directive as the block's first line, a path relative to
the layer directory::

    # @output-file "spec/behaviour-runtime.ttl"

The directive is read only on the first line, and is not written out. Such a
document gains the ``@prefix`` lines of ``spec/<layer>.ttl``'s blocks after its
SPDX header, so its blocks state only its own ontology header and content. All
of a layer's spec documents carry the same version (``owl:versionIRI ending
/X.Y.Z``), or extraction fails.

Usage::

    python3 -m tools.lattice.literate_extract ontology/surface/README.md \\
        --layer surface \\
        --root . \\
        --shapes shapes/structural.ttl shapes/constraints.ttl

    python3 -m tools.lattice.literate_extract ontology/surface/README.md \\
        --layer surface --root . --check

    python3 -m tools.lattice.literate_extract ontology/eligibility/README.md \\
        --layer eligibility --root . --proofs-root tools/proofs
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

SPDX_TTL = "# SPDX-License-Identifier: MPL-2.0"
SPDX_THY = "(* SPDX-License-Identifier: MPL-2.0 *)"

FENCE_RE = re.compile(
    r"^```(?P<tag>turtle-spec|turtle-vocab|turtle-shapes|turtle-example|isabelle-spec)\s*$"
)
FENCE_END_RE = re.compile(r"^```\s*$")
OUTPUT_FILE_RE = re.compile(r'^#\s*@output-file\s+"(?P<path>[^"]+)"\s*$')
PREFIX_RE = re.compile(r"^@prefix\s.*$", re.MULTILINE)
VERSION_RE = re.compile(r"owl:versionIRI\s+<[^>]*/(?P<version>\d+\.\d+\.\d+)>")


@dataclass(frozen=True)
class Block:
    """One fenced block, with its tag, its ordinal within that tag, and its body."""

    tag: str
    ordinal: int
    body: str
    start_line: int


def parse_blocks(markdown: str) -> List[Block]:
    """Collect every recognised fenced block from a literate specification."""
    blocks: List[Block] = []
    counters: Dict[str, int] = {}
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        match = FENCE_RE.match(lines[index])
        if match is None:
            index += 1
            continue
        tag = match.group("tag")
        start = index + 1
        end = start
        while end < len(lines) and not FENCE_END_RE.match(lines[end]):
            end += 1
        if end >= len(lines):
            raise ValueError(f"Unterminated {tag} block opened at line {index + 1}")
        ordinal = counters.get(tag, 0)
        counters[tag] = ordinal + 1
        blocks.append(
            Block(
                tag=tag,
                ordinal=ordinal,
                body="\n".join(lines[start:end]).rstrip() + "\n",
                start_line=index + 1,
            )
        )
        index = end + 1
    return blocks


def render(bodies: Sequence[str], header: str = SPDX_TTL) -> str:
    """Concatenate block bodies into one document under the given SPDX header."""
    if not bodies:
        return ""
    return header + "\n\n" + "\n".join(body.rstrip() + "\n" for body in bodies)


def plan(
    blocks: Sequence[Block],
    layer: str,
    shape_targets: Sequence[str],
    proofs_root: str | None = None,
) -> Dict[str, str]:
    """Map each output path to the document it should contain.

    Every path is relative to ``--root`` (the ontology directory) except an
    ``isabelle-spec`` output, which is relative to the repository root, via
    ``proofs_root``, since ``tools/proofs/`` sits outside ``ontology/``
    entirely (ADR-A-FM2).
    """
    default_spec = f"ontology/{layer}/spec/{layer}.ttl"
    spec_docs: Dict[str, List[str]] = {}
    for block in blocks:
        if block.tag == "turtle-spec":
            target, body = _spec_target(block, layer, default_spec)
            spec_docs.setdefault(target, []).append(body)
    vocab_bodies = [b.body for b in blocks if b.tag == "turtle-vocab"]
    shape_blocks = [b for b in blocks if b.tag == "turtle-shapes"]
    isabelle_bodies = [b.body for b in blocks if b.tag == "isabelle-spec"]

    if len(shape_blocks) != len(shape_targets):
        raise ValueError(
            f"{len(shape_blocks)} turtle-shapes block(s) found but "
            f"{len(shape_targets)} shape target(s) declared; the extraction "
            f"contract in the README and the --shapes argument must agree"
        )
    if isabelle_bodies and not proofs_root:
        raise ValueError(
            "isabelle-spec block(s) found but --proofs-root was not given; "
            "pass --proofs-root tools/proofs to extract them, or remove the "
            "block(s) if this layer has no formalised theory yet"
        )

    outputs: Dict[str, str] = {}
    prefixes = PREFIX_RE.findall("\n".join(spec_docs.get(default_spec, [])))
    for target, bodies in spec_docs.items():
        if target != default_spec and prefixes:
            bodies = ["\n".join(prefixes) + "\n"] + bodies
        outputs[target] = render(bodies)
    versions = {t: VERSION_RE.search(outputs[t]) for t in spec_docs}
    found = {m.group("version") for m in versions.values() if m}
    if len(spec_docs) > 1 and len(found) > 1:
        raise ValueError(
            f"{layer}'s spec documents carry different versions "
            f"({', '.join(f'{t}: {m.group(1) if m else None}' for t, m in sorted(versions.items()))}); "
            f"a layer's spec documents move in unison (ADR-A120)"
        )
    if vocab_bodies:
        outputs[f"ontology/{layer}/vocab/{layer}-vocab.ttl"] = render(vocab_bodies)
    for block, target in zip(shape_blocks, shape_targets):
        outputs[f"ontology/{layer}/{target}"] = render([block.body])
    if isabelle_bodies:
        # A path outside `root` (ontology/), marked with a recognisable prefix so
        # main() resolves it against --proofs-root instead of --root.
        outputs[f"@proofs-root@/{layer}/Kernel.thy"] = render(
            isabelle_bodies, header=SPDX_THY
        )
    return outputs


def _spec_target(block: Block, layer: str, default: str) -> tuple[str, str]:
    """The spec document a ``turtle-spec`` block goes to, and its body without the directive."""
    first, _, rest = block.body.partition("\n")
    match = OUTPUT_FILE_RE.match(first)
    if match is None:
        return default, block.body
    path = match.group("path")
    if Path(path).is_absolute() or ".." in Path(path).parts or not path.endswith(".ttl"):
        raise ValueError(
            f"turtle-spec block at line {block.start_line}: @output-file must name a .ttl "
            f"file inside the layer directory, not {path!r}"
        )
    return f"ontology/{layer}/{path}", rest.lstrip("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract compiled Turtle from a layer README")
    parser.add_argument("readme", help="path to the layer README.md")
    parser.add_argument("--layer", required=True, help="layer directory name, e.g. surface")
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument(
        "--shapes",
        nargs="*",
        default=[],
        help="shape output paths, relative to the layer directory, in document order",
    )
    parser.add_argument(
        "--proofs-root",
        default=None,
        help=(
            "where isabelle-spec output goes, e.g. tools/proofs (resolved against the "
            "current working directory, independently of --root, since tools/proofs/ "
            "sits outside ontology/ entirely, ADR-A-FM2). Required if the README has "
            "any isabelle-spec blocks"
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit non-zero if any target differs from what would be written",
    )
    args = parser.parse_args(argv)

    readme_path = Path(args.readme)
    blocks = parse_blocks(readme_path.read_text(encoding="utf-8"))
    outputs = plan(blocks, args.layer, args.shapes, args.proofs_root)

    root = Path(args.root)
    proofs_root = Path(args.proofs_root) if args.proofs_root else None
    drifted: List[str] = []
    for relative, content in sorted(outputs.items()):
        if relative.startswith("@proofs-root@/"):
            assert proofs_root is not None  # plan() already enforced this
            target = proofs_root / relative.removeprefix("@proofs-root@/")
        else:
            target = root / relative
        if args.check:
            current = target.read_text(encoding="utf-8") if target.exists() else None
            if current != content:
                drifted.append(relative)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"wrote {relative} ({len(content.splitlines())} lines)")

    if args.check:
        for relative in drifted:
            print(f"DRIFT {relative}", file=sys.stderr)
        if drifted:
            return 1
        print(f"{len(outputs)} extracted artefact(s) consistent with {readme_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
