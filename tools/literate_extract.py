# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Literate-spec extractor.

A LATTICE layer's ``README.md`` is the authoritative specification. The compiled
Turtle under ``spec/``, ``vocab/`` and ``shapes/`` is mechanically extracted from
its fenced blocks, in document order, so the two artefacts cannot drift.

Fence tags recognised:

====================  ================================================
``turtle-spec``       concatenated into ``spec/<layer>.ttl``
``turtle-vocab``      concatenated into ``vocab/<layer>-vocab.ttl``
``turtle-shapes``     written, in document order, to the shape files
                      named by the layer's extraction contract
``turtle-example``    never extracted
====================  ================================================

Each extracted ``.ttl`` gains the project's SPDX header as its first line.

Usage::

    python3 -m tools.lattice.literate_extract ontology/surface/README.md \\
        --layer surface \\
        --root . \\
        --shapes shapes/structural.ttl shapes/constraints.ttl

    python3 -m tools.lattice.literate_extract ontology/surface/README.md \\
        --layer surface --root . --check
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

SPDX_TTL = "# SPDX-License-Identifier: MPL-2.0"

FENCE_RE = re.compile(
    r"^```(?P<tag>turtle-spec|turtle-vocab|turtle-shapes|turtle-example)\s*$"
)
FENCE_END_RE = re.compile(r"^```\s*$")


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


def render(bodies: Sequence[str]) -> str:
    """Concatenate block bodies into one Turtle document under the SPDX header."""
    if not bodies:
        return ""
    return SPDX_TTL + "\n\n" + "\n".join(body.rstrip() + "\n" for body in bodies)


def plan(
    blocks: Sequence[Block],
    layer: str,
    shape_targets: Sequence[str],
) -> Dict[str, str]:
    """Map each output path to the Turtle document it should contain."""
    spec_bodies = [b.body for b in blocks if b.tag == "turtle-spec"]
    vocab_bodies = [b.body for b in blocks if b.tag == "turtle-vocab"]
    shape_blocks = [b for b in blocks if b.tag == "turtle-shapes"]

    if len(shape_blocks) != len(shape_targets):
        raise ValueError(
            f"{len(shape_blocks)} turtle-shapes block(s) found but "
            f"{len(shape_targets)} shape target(s) declared; the extraction "
            f"contract in the README and the --shapes argument must agree"
        )

    outputs: Dict[str, str] = {}
    if spec_bodies:
        outputs[f"ontology/{layer}/spec/{layer}.ttl"] = render(spec_bodies)
    if vocab_bodies:
        outputs[f"ontology/{layer}/vocab/{layer}-vocab.ttl"] = render(vocab_bodies)
    for block, target in zip(shape_blocks, shape_targets):
        outputs[f"ontology/{layer}/{target}"] = render([block.body])
    return outputs


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
        "--check",
        action="store_true",
        help="do not write; exit non-zero if any target differs from what would be written",
    )
    args = parser.parse_args(argv)

    readme_path = Path(args.readme)
    blocks = parse_blocks(readme_path.read_text(encoding="utf-8"))
    outputs = plan(blocks, args.layer, args.shapes)

    root = Path(args.root)
    drifted: List[str] = []
    for relative, content in sorted(outputs.items()):
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
