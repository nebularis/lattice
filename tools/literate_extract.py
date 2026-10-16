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

ADR-A120 addendum (2026-10-13, AIR-2.0): the same directive is read on the
first line of a ``turtle-vocab`` block, and must name a ``.ttl`` file under the
module's ``vocab/``, for example::

    # @output-file "vocab/peril-intensity.ttl"

A module's vocabulary documents move in unison the same way its spec
documents do: they all carry one ``owl:versionIRI`` version, independent of
the spec documents' own shared version. ``--layer`` also accepts a path under
``ontology/`` rather than a single segment, for example
``applied/insurance/peril``, whose last segment names the module's default
documents (``spec/peril.ttl``, ``vocab/peril-vocab.ttl``). A single-segment
``--layer`` behaves exactly as before.

ADR-A126 (2026-10-17) adds HTML comment markers, documented for README authors in
``docs/architecture/literate-specifications.md``. The scanner skips any other fence
and any ordinary comment whole, so a tagged block or a marker shown inside one is
text. ``<!-- start: {"key": value} -->`` opens a region and ``<!-- end -->`` closes
the innermost, with one key of ``exclude``, ``output-file`` or ``generated``. An
``output-file`` region sends the spec, vocab and shapes blocks inside it to that
file. ``<!-- hidden`` or ``<!-- hidden: {"output-file": "..."}``, on its own line,
wraps one tagged block that is extracted but not rendered, and is closed by a line
holding only ``-->``. A block may name its file by one form only, the marker or its
first line, and a ``turtle-shapes`` block that names one takes no ``--shapes``
target. A README with a "Description Logic Encoding" section uses the layout, so its
top-level sections are checked by title: a missing, extra or repeated one is an
error, and a misnumbered one a warning.

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
    python3 -m tools.lattice.literate_extract ontology/applied/insurance/peril/README.md \
        --layer applied/insurance/peril --root . \
        --shapes shapes/structural.ttl shapes/constraints.ttl"""

from __future__ import annotations

import argparse
import itertools
import json
import os
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
ANY_FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
# A marker word followed by ":", "-->" or the end of the line. "<!-- end of a table -->" is an ordinary comment.
MARKER_WORD_RE = re.compile(r"^<!--\s*(start|end|hidden)\s*(:|-->|$)")
REGION_START_RE = re.compile(r"^<!--\s*start:\s*(?P<json>\{.*\})\s*-->\s*$")
REGION_END_RE = re.compile(r"^<!--\s*end\s*-->\s*$")
HIDDEN_RE = re.compile(r"^<!--\s*hidden(?::\s*(?P<json>\{.*\}))?\s*$")
SECTION_RE = re.compile(r"^## (?P<number>\d+)\.\s+(?P<title>.+?)\s*$")
REGION_KEYS: Dict[str, type] = {"exclude": bool, "output-file": str, "generated": str}
EXTRACTED_TO_ONTOLOGY = ("turtle-spec", "turtle-vocab", "turtle-shapes")
# The README layout of ADR-A126 decision 1, in order. Sections are found by title.
LAYOUT = (
    "Purpose and Scope", "Namespace and Prefixes", "Extraction Contract", "Overview", "Detailed Design",
    "Description Logic Encoding", "Shapes", "Examples", "Canonicalisation", "Formalisation", "Dependencies",
    "Release Notes", "Open Issues",
)
FUN_HEADER_RE = re.compile(r"^\s*fun\s+(?P<name>\w+)\s*::")
CLAUSE_LINE_RE = re.compile(r'^\s*\|?\s*"(?P<clause>[^"]*)"\s*$')
FENCE_END_RE = re.compile(r"^```\s*$")
OUTPUT_FILE_RE = re.compile(r'^#\s*@output-file\s+"(?P<path>[^"]+)"\s*$')
PREFIX_RE = re.compile(r"^@prefix\s.*$", re.MULTILINE)
VERSION_RE = re.compile(r"owl:versionIRI\s+<[^>]*/(?P<version>\d+\.\d+\.\d+)>")


@dataclass(frozen=True)
class Block:
    """One fenced block, with its tag, its ordinal within that tag, and its body.

    ``output_file`` is the JSON form of the directive (ADR-A126 decision 9), set by a
    hidden block's marker or by an enclosing ``output-file`` region, and ``hidden`` says
    the block sat inside a ``<!-- hidden`` comment."""

    tag: str
    ordinal: int
    body: str
    start_line: int
    output_file: str | None = None
    hidden: bool = False


@dataclass(frozen=True)
class Region:
    """A ``<!-- start: {...} -->`` ... ``<!-- end -->`` region, by its one key."""

    key: str
    value: object
    start_line: int
    end_line: int


@dataclass(frozen=True)
class Section:
    """A top-level ``## N. Title`` heading outside any fence or comment."""

    number: int
    title: str
    line: int


@dataclass(frozen=True)
class Scan:
    blocks: List[Block]
    regions: List[Region]
    sections: List[Section]


def parse_blocks(markdown: str) -> List[Block]:
    """Collect every recognised fenced block from a literate specification."""
    return scan(markdown).blocks


def scan(markdown: str) -> Scan:
    """Read a README once: its recognised blocks, its marker regions and its sections.

    A fence of any other kind, and an ordinary HTML comment, are skipped whole, so a
    tagged block or a marker shown inside one is text (ADR-A126 decision 8)."""
    lines = markdown.splitlines()
    blocks: List[Block] = []
    regions: List[Region] = []
    sections: List[Section] = []
    counters: Dict[str, int] = {}
    open_regions: List[Tuple[str, object, int]] = []

    def read_block(at: int, tag: str, output_file: str | None, hidden: bool) -> int:
        end = at + 1
        while end < len(lines) and not FENCE_END_RE.match(lines[end]):
            if hidden and "-->" in lines[end]:
                raise ValueError(f"line {end + 1}: '-->' inside a hidden block would end its comment early")
            end += 1
        if end >= len(lines):
            raise ValueError(f"Unterminated {tag} block opened at line {at + 1}")
        ordinal = counters.get(tag, 0)
        counters[tag] = ordinal + 1
        body = "\n".join(lines[at + 1:end]).rstrip() + "\n"
        blocks.append(Block(tag, ordinal, body, at + 1, output_file, hidden))
        return end + 1

    def region_file(tag: str) -> str | None:
        if tag not in EXTRACTED_TO_ONTOLOGY:
            return None
        return next((v for k, v, _ in reversed(open_regions) if k == "output-file"), None)

    index = 0
    while index < len(lines):
        line = lines[index]
        tagged = FENCE_RE.match(line)
        if tagged:
            index = read_block(index, tagged.group("tag"), region_file(tagged.group("tag")), False)
            continue
        fence = ANY_FENCE_RE.match(line)
        if fence:
            index = _skip_fence(lines, index, fence.group("fence"))
            continue
        if line.startswith("<!--"):
            if not MARKER_WORD_RE.match(line):
                index = _skip_comment(lines, index)
                continue
            if REGION_END_RE.match(line):
                if not open_regions:
                    raise ValueError(f"line {index + 1}: <!-- end --> closes no region")
                key, value, opened = open_regions.pop()
                regions.append(Region(key, value, opened, index + 1))
                index += 1
                continue
            start = REGION_START_RE.match(line)
            if start:
                key, value = _marker_json(start.group("json"), index, REGION_KEYS)
                open_regions.append((key, value, index + 1))
                index += 1
                continue
            hidden = HIDDEN_RE.match(line)
            if hidden is None:
                raise ValueError(f"line {index + 1}: malformed marker {line.strip()!r} (ADR-A126)")
            output_file = None
            if hidden.group("json"):
                _, output_file = _marker_json(hidden.group("json"), index, {"output-file": str})
            index += 1
            while index < len(lines) and not lines[index].strip():
                index += 1
            inner = FENCE_RE.match(lines[index]) if index < len(lines) else None
            if inner is None:
                other = ANY_FENCE_RE.match(lines[index]) if index < len(lines) else None
                if other and other.group("info").strip().startswith("mermaid"):
                    raise ValueError(f"line {index + 1}: a mermaid diagram is never hidden (ADR-A126)")
                raise ValueError(f"line {index + 1}: a hidden block holds one extracted fenced block (ADR-A126)")
            tag = inner.group("tag")
            if output_file is not None and tag not in EXTRACTED_TO_ONTOLOGY:
                raise ValueError(f"line {index + 1}: a {tag} block takes no output-file (ADR-A126)")
            enclosing = region_file(tag)
            if output_file is not None and enclosing is not None:
                raise ValueError(
                    f"line {index + 1}: output-file is given twice, by the hidden block and by its region (ADR-A126)"
                )
            index = read_block(index, tag, output_file or enclosing, True)
            while index < len(lines) and not lines[index].strip():
                index += 1
            if index >= len(lines) or lines[index].strip() != "-->":
                raise ValueError(f"line {index + 1}: a hidden block ends with a line holding only '-->'")
            index += 1
            continue
        section = SECTION_RE.match(line)
        if section:
            sections.append(Section(int(section.group("number")), section.group("title"), index + 1))
        index += 1
    if open_regions:
        raise ValueError(f"the region opened at line {open_regions[-1][2]} is never closed")
    return Scan(blocks, regions, sections)


def _skip_fence(lines: Sequence[str], at: int, fence: str) -> int:
    closing = re.compile(rf"^ {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}\s*$")
    for index in range(at + 1, len(lines)):
        if closing.match(lines[index]):
            return index + 1
    raise ValueError(f"Unterminated fence opened at line {at + 1}")


def _skip_comment(lines: Sequence[str], at: int) -> int:
    if "-->" in lines[at][4:]:
        return at + 1
    for index in range(at + 1, len(lines)):
        if "-->" in lines[index]:
            return index + 1
    raise ValueError(f"Unterminated HTML comment opened at line {at + 1}")


def _marker_json(text: str, at: int, allowed: Mapping[str, type]) -> Tuple[str, object]:
    """A marker's JSON: one key from ``allowed``, with a value of that key's type."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"line {at + 1}: marker JSON does not parse ({error.msg})") from None
    if not isinstance(data, dict) or len(data) != 1:
        raise ValueError(f"line {at + 1}: a marker holds exactly one key, one of {', '.join(allowed)}")
    ((key, value),) = data.items()
    if key not in allowed:
        raise ValueError(f"line {at + 1}: unknown marker key {key!r}, expected one of {', '.join(allowed)}")
    if type(value) is not allowed[key]:
        raise ValueError(f"line {at + 1}: marker key {key!r} takes a {allowed[key].__name__}")
    return key, value


def _norm(title: str) -> str:
    return " ".join(title.split()).casefold()


def layout_problems(sections: Sequence[Section]) -> Tuple[List[str], List[str]]:
    """The errors and warnings of a README in the ADR-A126 layout. A README with no
    "Description Logic Encoding" section is not yet migrated, and has neither."""
    if not any(_norm(s.title) == _norm(LAYOUT[5]) for s in sections):
        return [], []
    expected = {_norm(title): (number, title) for number, title in enumerate(LAYOUT, 1)}
    errors: List[str] = []
    warnings: List[str] = []
    seen: Dict[str, Section] = {}
    for section in sections:
        key = _norm(section.title)
        if key not in expected:
            errors.append(f"line {section.line}: section {section.title!r} is not in the layout (ADR-A126)")
        elif key in seen:
            errors.append(f"line {section.line}: section {section.title!r} appears twice")
        else:
            seen[key] = section
            number = expected[key][0]
            if section.number != number:
                warnings.append(
                    f"line {section.line}: {section.title!r} is numbered {section.number}, the layout numbers it {number}"
                )
    errors += [f"section {number}, {title!r}, is missing" for key, (number, title) in expected.items() if key not in seen]
    return errors, warnings


def _warn(message: str) -> None:
    """A warning on stderr, in yellow where the stream is a terminal (and NO_COLOR is unset)."""
    if sys.stderr.isatty() and not os.environ.get("NO_COLOR"):
        sys.stderr.write(f"\033[33mWARNING {message}\033[0m\n")
    else:
        sys.stderr.write(f"WARNING {message}\n")


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
    entirely (ADR-A-FM2). ``layer`` may itself be a nested module path (for
    example ``applied/insurance/peril``, ADR-A120 addendum): its last segment
    names the module's default spec and vocabulary documents.
    """
    last_segment = layer.rsplit("/", 1)[-1]
    default_spec = f"ontology/{layer}/spec/{last_segment}.ttl"
    default_vocab = f"ontology/{layer}/vocab/{last_segment}-vocab.ttl"
    spec_docs: Dict[str, List[str]] = {}
    for block in blocks:
        if block.tag == "turtle-spec":
            target, body = _target(block, layer, default_spec)
            spec_docs.setdefault(target, []).append(body)
    vocab_docs: Dict[str, List[str]] = {}
    for block in blocks:
        if block.tag == "turtle-vocab":
            target, body = _target(block, layer, default_vocab, under="vocab/")
            vocab_docs.setdefault(target, []).append(body)
    shape_docs: Dict[str, List[str]] = {}
    positional: List[str] = []
    for block in blocks:
        if block.tag == "turtle-shapes":
            target, body = _target(block, layer, None, under="shapes/")
            if target is None:
                positional.append(body)
            else:
                shape_docs.setdefault(target, []).append(body)
    isabelle_bodies = [b.body for b in blocks if b.tag == "isabelle-spec"]

    if len(positional) != len(shape_targets):
        raise ValueError(
            f"{len(positional)} turtle-shapes block(s) without an output-file found but "
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
    vocab_prefixes = PREFIX_RE.findall("\n".join(vocab_docs.get(default_vocab, [])))
    for target, bodies in vocab_docs.items():
        if target != default_vocab and vocab_prefixes:
            bodies = ["\n".join(vocab_prefixes) + "\n"] + bodies
        outputs[target] = render(bodies)
    vocab_versions = {t: VERSION_RE.search(outputs[t]) for t in vocab_docs}
    vocab_found = {m.group("version") for m in vocab_versions.values() if m}
    if len(vocab_docs) > 1 and len(vocab_found) > 1:
        raise ValueError(
            f"{layer}'s vocabulary documents carry different versions "
            f"({', '.join(f'{t}: {m.group(1) if m else None}' for t, m in sorted(vocab_versions.items()))}); "
            f"a module's vocabulary documents move in unison (ADR-A120 addendum)"
        )
    for body, target in zip(positional, shape_targets):
        path = f"ontology/{layer}/{target}"
        if path in shape_docs:
            raise ValueError(f"{path} is named both by --shapes and by a block's output-file")
        outputs[path] = render([body])
    for path, bodies in shape_docs.items():
        outputs[path] = render(bodies)
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


def _target(block: Block, layer: str, default: str | None, under: str = "") -> tuple[str | None, str]:
    """The document a block goes to, and its body without the directive. The directive
    has two forms, a ``# @output-file`` first line (ADR-A120) and the JSON key of a marker
    (``block.output_file``, ADR-A126 decision 9), and a block may carry only one. A block
    with neither goes to ``default``."""
    first, _, rest = block.body.partition("\n")
    match = OUTPUT_FILE_RE.match(first)
    if match and block.output_file:
        raise ValueError(
            f"{block.tag} block at line {block.start_line}: output-file is given twice, by a marker "
            f"and by the block's first line (ADR-A126)"
        )
    if match:
        path, body = match.group("path"), rest.lstrip("\n")
    elif block.output_file:
        path, body = block.output_file, block.body
    else:
        return default, block.body
    if _escapes_layer(path) or not path.endswith(".ttl") or not path.startswith(under):
        where = f"under the module's {under}" if under else "inside the layer directory"
        raise ValueError(
            f"{block.tag} block at line {block.start_line}: @output-file must name a .ttl "
            f"file {where}, not {path!r}"
        )
    return f"ontology/{layer}/{path}", body


def _escapes_layer(path: str) -> bool:
    """Whether a directive's path would resolve outside its module directory: an
    absolute path (POSIX-style, since Windows' ``Path.is_absolute()`` does not
    recognise ``/tmp/x.ttl`` as absolute without a drive letter) or a ``..`` segment."""
    return path.startswith("/") or Path(path).is_absolute() or ".." in Path(path).parts


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
    result = scan(readme_path.read_text(encoding="utf-8"))
    errors, warnings = layout_problems(result.sections)
    for message in warnings:
        _warn(f"{readme_path}: {message}")
    if errors:
        for message in errors:
            print(f"LAYOUT {readme_path}: {message}", file=sys.stderr)
        return 1
    outputs = plan(result.blocks, args.layer, args.shapes, args.proofs_root, args.reference_root)

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
        # newline="\n" pins the line ending to LF regardless of platform: without it,
        # Path.write_text() translates embedded "\n" to the OS separator, which turns
        # into CRLF inside a multi-line SPARQL string literal on Windows, silently
        # changing that literal's value (not just insignificant whitespace) and
        # producing CRLF noise against the repository's LF-committed .ttl files.
        target.write_text(content, encoding="utf-8", newline="\n")
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
