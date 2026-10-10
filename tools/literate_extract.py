# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Literate-spec extractor.

A LATTICE layer's ``README.md`` is the authoritative specification. The compiled
Turtle under ``spec/``, ``vocab/`` and ``shapes/`` is mechanically extracted from
its fenced blocks, in document order, so the two artefacts cannot drift. An
``isabelle-spec`` block does the same for a layer's Isabelle theory's closed
datatypes and a closed set of finite, exhaustive pattern-match functions over
them (ADR-A-FM2, epic principle E1, FM-D17): the lemmas and proofs built on
top are hand-written directly in the ``.thy`` file, not generated, and a
definition that is not a finite case table over a closed datatype (such as a
predicate over equality) also stays hand-written, not generated.

A ``fun name :: "..." where "..." | ...`` block inside an ``isabelle-spec``
block, an exhaustive pattern match over a closed datatype's constructors, is
also rendered a second time, as a generated Python module, into
``<reference-root>/<layer>/src/reference_<layer>/_kernel_defs.py``: the two
languages' statements of the same function agree by construction, not by two
independent authors' care. Isabelle itself is still hand-written and extracted
verbatim, never synthesised, so the prover checks exactly what was written
and reviewed; only the Python side is generated. A README section may also
carry a plain markdown table of the same truth table for a reader (FM-D17's
convention), which is prose, not a fenced block, and is never extracted or
checked mechanically.

Fence tags recognised:

====================  ================================================
``turtle-spec``       concatenated into ``spec/<layer>.ttl``, or into the
                      file its ``@output-file`` directive names
``turtle-vocab``      concatenated into ``vocab/<layer>-vocab.ttl``
``turtle-shapes``     written, in document order, to the shape files
                      named by the layer's extraction contract
``turtle-example``    never extracted
``isabelle-spec``     concatenated into ``<proofs-root>/<layer>/Kernel.thy``;
                      any ``fun`` clauses within it are also rendered into
                      ``<reference-root>/<layer>/src/reference_<layer>/_kernel_defs.py``
====================  ================================================

Each extracted ``.ttl``/``.thy``/``.py`` gains the project's SPDX header as its
first line (``#``-style for Turtle and Python, ``(* ... *)``-style for Isabelle).

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
        --layer eligibility --root . --proofs-root tools/proofs \
        --reference-root tools/reference
"""

from __future__ import annotations

import argparse
import itertools
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

SPDX_TTL = "# SPDX-License-Identifier: MPL-2.0"
SPDX_THY = "(* SPDX-License-Identifier: MPL-2.0 *)"

# The closed, three-constructor domain every `isabelle-spec` `fun` block this tool
# generates Python from is over today (FM-D17: or3/and3/neg3). A layer introducing a
# different closed datatype with its own finite functions would need this generalised;
# not done speculatively ahead of a second real case (formal-methods second review, R1).
DECISION_DOMAIN: Tuple[str, ...] = ("Permitted", "Denied", "Undetermined")
DECISION_CONST = {"Permitted": "PERMITTED", "Denied": "DENIED", "Undetermined": "UNDETERMINED"}

FENCE_RE = re.compile(
    r"^```(?P<tag>turtle-spec|turtle-vocab|turtle-shapes|turtle-example|isabelle-spec)\s*$"
)
FUN_HEADER_RE = re.compile(r"^\s*fun\s+(?P<name>\w+)\s*::")
CLAUSE_LINE_RE = re.compile(r'^\s*\|?\s*"(?P<clause>[^"]*)"\s*$')
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


def parse_fun_clauses(body: str) -> Dict[str, List[Tuple[List[str], str]]]:
    """Parse every ``fun name :: "..." where "clause" | "clause" ...`` block in an
    ``isabelle-spec`` body into ``{name: [(pattern_args, result), ...]}``, each
    clause's pattern as its literal tokens (a constructor name, a bound variable,
    or ``_``), in the order Isabelle itself matches them (the first clause that
    matches wins). A ``definition`` or any other line closes the current block,
    so a later, unrelated quoted string (a different kind of statement) is never
    mistaken for one of its clauses."""
    functions: Dict[str, List[Tuple[List[str], str]]] = {}
    current: str | None = None
    for line in body.splitlines():
        header_match = FUN_HEADER_RE.match(line)
        if header_match is not None:
            current = header_match.group("name")
            functions.setdefault(current, [])
            continue
        clause_match = CLAUSE_LINE_RE.match(line) if current is not None else None
        if clause_match is not None:
            lhs, sep, rhs = clause_match.group("clause").partition(" = ")
            if not sep:
                continue  # not an equation clause; leave the block open regardless
            tokens = lhs.split()
            name, args = tokens[0], tokens[1:]
            if name == current:
                functions[current].append((args, rhs.strip()))
            continue
        if line.strip():
            current = None  # a non-clause, non-header line (datatype, end, a comment) closes it
    return {name: clauses for name, clauses in functions.items() if clauses}


def resolve_truth_table(
    clauses: Sequence[Tuple[Sequence[str], str]]
) -> Dict[Tuple[str, ...], str]:
    """Resolve one function's ordered pattern-match clauses into a complete,
    concrete truth table over the closed three-value domain: Isabelle's own
    first-clause-matches semantics, applied once here, at generation time,
    since the domain is finite and small, rather than carried into the
    generated Python as pattern matching or bound variables."""
    arity = len(clauses[0][0])
    table: Dict[Tuple[str, ...], str] = {}
    for combo in itertools.product(DECISION_DOMAIN, repeat=arity):
        for args, result in clauses:
            bindings: Dict[str, str] = {}
            matched = True
            for token, value in zip(args, combo):
                if token == "_":
                    continue
                if token in DECISION_DOMAIN:
                    if token != value:
                        matched = False
                        break
                    continue
                bindings[token] = value  # a lowercase variable, binds this position's value
            if matched:
                table[combo] = bindings.get(result, result)
                break
        else:
            raise ValueError(f"no clause of a {arity}-ary function matches {combo}")
    return table


def render_python(functions: Mapping[str, Mapping[Tuple[str, ...], str]], layer: str) -> str:
    """Render a generated Python module from each function's resolved truth table,
    a dict literal keyed by the concrete argument tuple (or value, for arity one)
    plus a thin function wrapping the lookup -- the literal table is the point: it
    is exactly as auditable against the README's own markdown table as the
    Isabelle clauses are, with no symbolic pattern matching re-derived at import
    time."""
    lines = [
        SPDX_TTL,
        '"""Eligibility\'s kernel connectives, generated from '
        f"`ontology/{layer}/README.md`'s `isabelle-spec` block by "
        "`tools/literate_extract.py` (FM-D17). Never hand-edited: edit the README "
        "and regenerate. `decision_leq` is not generated (a predicate over "
        'equality, not a finite case table) and stays hand-written in `kernel.py`."""',
        "",
        "from __future__ import annotations",
        "",
        "from ._decision import DENIED, PERMITTED, UNDETERMINED, Decision",
        "",
    ]
    for name, table in functions.items():
        arity = len(next(iter(table)))
        table_name = f"_{name.upper()}"
        key_type = "Decision" if arity == 1 else f"Tuple[{', '.join(['Decision'] * arity)}]"
        lines.append(f"{table_name}: Dict[{key_type}, Decision] = {{")
        for combo in itertools.product(DECISION_DOMAIN, repeat=arity):
            result = DECISION_CONST[table[combo]]
            key = (
                DECISION_CONST[combo[0]]
                if arity == 1
                else "(" + ", ".join(DECISION_CONST[c] for c in combo) + ")"
            )
            lines.append(f"    {key}: {result},")
        lines.append("}")
        lines.append("")
        arg_names = [chr(ord("a") + i) for i in range(arity)]
        params = ", ".join(f"{a}: Decision" for a in arg_names)
        call_key = arg_names[0] if arity == 1 else "(" + ", ".join(arg_names) + ")"
        lines.append(f"def {name}({params}) -> Decision:")
        lines.append(f"    return {table_name}[{call_key}]")
        lines.append("")
    body = "\n".join(lines).rstrip() + "\n"
    needs_typing = "Dict[" in body or "Tuple[" in body
    if needs_typing:
        body = body.replace(
            "from __future__ import annotations\n",
            "from __future__ import annotations\n\nfrom typing import Dict, Tuple\n",
            1,
        )
    return body


def plan(
    blocks: Sequence[Block],
    layer: str,
    shape_targets: Sequence[str],
    proofs_root: str | None = None,
    reference_root: str | None = None,
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
    fun_clauses = parse_fun_clauses("\n".join(isabelle_bodies))
    truth_tables = {name: resolve_truth_table(clauses) for name, clauses in fun_clauses.items()}
    if truth_tables and not reference_root:
        raise ValueError(
            "isabelle-spec fun clause(s) found but --reference-root was not given; "
            "pass --reference-root tools/reference to render their Python rendering, "
            "or move the fun block(s) out of isabelle-spec if none is wanted"
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
    if truth_tables:
        # Likewise relative to --reference-root, not --root (tools/reference/ also
        # sits outside ontology/, same reasoning as the isabelle-spec output above).
        outputs[
            f"@reference-root@/{layer}/src/reference_{layer}/_kernel_defs.py"
        ] = render_python(truth_tables, layer)
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
        "--reference-root",
        default=None,
        help=(
            "where an isabelle-spec block's fun clauses' generated Python rendering "
            "goes, e.g. tools/reference (resolved against the current working "
            "directory, independently of --root, FM-D17). Required if the README's "
            "isabelle-spec block(s) contain any fun clauses"
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
    outputs = plan(blocks, args.layer, args.shapes, args.proofs_root, args.reference_root)

    root = Path(args.root)
    proofs_root = Path(args.proofs_root) if args.proofs_root else None
    reference_root = Path(args.reference_root) if args.reference_root else None
    drifted: List[str] = []
    for relative, content in sorted(outputs.items()):
        if relative.startswith("@proofs-root@/"):
            assert proofs_root is not None  # plan() already enforced this
            target = proofs_root / relative.removeprefix("@proofs-root@/")
        elif relative.startswith("@reference-root@/"):
            assert reference_root is not None  # plan() already enforced this
            target = reference_root / relative.removeprefix("@reference-root@/")
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
