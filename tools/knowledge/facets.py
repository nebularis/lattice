# SPDX-License-Identifier: MPL-2.0
"""Generate the facet schemes as Turtle from the facet register (ADR-A134 decisions 24 and 26).

The register, ``docs/developer/facets.md``, is the source. Its first table lists the three schemes,
and each scheme's own section lists its values, one row each. This writes them as SKOS concept
schemes into ``.build/knowledge/facets.ttl``, which ``extract.py`` loads and nothing commits, as
STD-003 requires of anything a tool can derive.

A column maps to the SKOS property that states its meaning, so the meaning is written once, by SKOS.
A value with no broader value is a top concept of its scheme. ``Group`` yes is the editorial note
"group", a value that organises others and is never tagged. ``Ratified`` no is the editorial note
"proposed". Broader and related values are slugs separated by spaces, and a related value may sit in
another scheme.

The output is deterministic: rows are written in the register's order, and the values in a cell
sorted, so the same register always gives the same bytes.

Usage::

    python tools/knowledge/facets.py            # write .build/knowledge/facets.ttl
    python tools/knowledge/facets.py --check    # parse and report, write nothing
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lattice_repo_catalogue  # noqa: E402

# The register sits with the other registers, in the area the catalogue names developer (ADR-A121).
_CATALOGUE = lattice_repo_catalogue.load()
ROOT = _CATALOGUE.root
SOURCE_PATH = ROOT / _CATALOGUE.area("developer") / "facets.md"
OUTPUT_PATH = ROOT / ".build" / "knowledge" / "facets.ttl"
NS = "https://www.nebularis.org/neuro-semantic/lattice/dev/facets#"
ONTOLOGY = "https://www.nebularis.org/neuro-semantic/lattice/dev/facets"
SCHEMES = ("Activity", "Quality", "Technology")

SCHEME_COLUMNS = ["ID", "Label", "Definition"]
VALUE_COLUMNS = ["ID", "Label", "Broader", "Related", "Group", "Definition", "Scope note", "Ratified"]
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9.+-]*$")
SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|?$")
HEADING_RE = re.compile(r"^##\s+(?P<name>.+?)\s*$")


class RegisterError(ValueError):
    """The register cannot be read as the schemes, with every problem found listed."""


@dataclass
class Scheme:
    slug: str
    label: str
    definition: str


@dataclass
class Value:
    slug: str
    scheme: str
    label: str
    definition: str
    broader: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    group: bool = False
    scope_note: str = ""
    ratified: bool = True
    line: int = 0


def _cells(line: str) -> list[str]:
    cells = line.strip().split("|")[1:]
    if cells and not cells[-1].strip():
        cells.pop()
    return [c.strip() for c in cells]


def _flag(cell: str, name: str, where: str, problems: list[str], *, blank: bool) -> bool:
    if cell == "yes":
        return True
    if cell == "no" or (blank and cell == ""):
        return False
    problems.append(f"{where}: {name} is {cell!r}, not yes or no{' or empty' if blank else ''}")
    return False


def parse(text: str) -> tuple[list[Scheme], list[Value]]:
    """The schemes and values of the register, in its order, or every problem found."""
    problems: list[str] = []
    schemes: list[Scheme] = []
    values: list[Value] = []
    section: str | None = None
    headers: list[str] | None = None
    rejected = False
    lines = text.splitlines()
    for number, line in enumerate(lines, 1):
        where = f"{SOURCE_PATH.name}:{number}"
        heading = HEADING_RE.match(line)
        if heading:
            section, headers = heading["name"], None
            continue
        if not line.strip().startswith("|"):
            headers = None
            continue
        if headers is None:
            headers = _cells(line)
            wanted = SCHEME_COLUMNS if section == "Schemes" else VALUE_COLUMNS
            rejected = True
            if section not in ("Schemes", *SCHEMES):
                problems.append(f"{where}: a table under {section!r}, which is neither Schemes nor a scheme")
            elif headers != wanted:
                problems.append(f"{where}: the columns are {headers}, not {wanted}")
            else:
                rejected = False
            continue
        if SEPARATOR_RE.match(line.strip()) or rejected:
            continue
        row = dict(zip(headers, _cells(line)))
        if len(_cells(line)) != len(headers):
            problems.append(f"{where}: {len(_cells(line))} cells under {len(headers)} columns")
            continue
        if section == "Schemes":
            schemes.append(Scheme(row["ID"], row["Label"], row["Definition"]))
        elif section in SCHEMES:
            values.append(
                Value(
                    slug=row["ID"],
                    scheme=section,
                    label=row["Label"],
                    definition=row["Definition"],
                    broader=sorted(row["Broader"].split()),
                    related=sorted(row["Related"].split()),
                    group=_flag(row["Group"], "Group", where, problems, blank=True),
                    scope_note=row["Scope note"],
                    ratified=_flag(row["Ratified"], "Ratified", where, problems, blank=False),
                    line=number,
                )
            )

    if [s.slug for s in schemes] != list(SCHEMES):
        problems.append(f"the Schemes table lists {[s.slug for s in schemes]}, not {list(SCHEMES)}")
    seen: dict[str, Value] = {}
    for value in values:
        where = f"{SOURCE_PATH.name}:{value.line}"
        if not SLUG_RE.match(value.slug):
            problems.append(f"{where}: {value.slug!r} is not a slug of lower-case letters, digits and hyphens")
        if value.slug in seen:
            problems.append(f"{where}: {value.slug} is already defined at line {seen[value.slug].line}")
        seen[value.slug] = value
        for name, text_ in (("Label", value.label), ("Definition", value.definition)):
            if not text_:
                problems.append(f"{where}: {value.slug} has no {name}")
    for value in values:
        where = f"{SOURCE_PATH.name}:{value.line}"
        for broader in value.broader:
            if broader not in seen:
                problems.append(f"{where}: {value.slug}'s broader value {broader} is defined nowhere")
            elif seen[broader].scheme != value.scheme:
                problems.append(f"{where}: {value.slug}'s broader value {broader} is in {seen[broader].scheme}, not {value.scheme}")
        for related in value.related:
            if related not in seen:
                problems.append(f"{where}: {value.slug}'s related value {related} is defined nowhere")
    if problems:
        raise RegisterError("\n".join(problems))
    return schemes, values


def _literal(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def turtle(schemes: list[Scheme], values: list[Value]) -> str:
    """The schemes as Turtle, the same bytes for the same register."""
    out = [
        "# SPDX-License-Identifier: CC-BY-SA-4.0",
        "#",
        f"# Generated from {SOURCE_PATH.relative_to(ROOT).as_posix()} by tools/knowledge/facets.py on every",
        "# build of the knowledge index (ADR-A134). Never committed and never edited: change the register.",
        "",
        "@prefix fct:  <" + NS + "> .",
        "@prefix owl:  <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "",
        f"<{ONTOLOGY}>",
        "    rdf:type owl:Ontology ;",
        '    rdfs:label "LATTICE knowledge-index facets" .',
        "",
    ]
    for scheme in schemes:
        out += [
            f"fct:{scheme.slug} rdf:type skos:ConceptScheme ;",
            f"    skos:prefLabel {_literal(scheme.label)} ;",
            f"    skos:definition {_literal(scheme.definition)} .",
            "",
        ]
    for value in values:
        lines = [f"fct:{value.slug} rdf:type skos:Concept ; skos:inScheme fct:{value.scheme}"]
        if value.broader:
            lines.append("skos:broader " + " , ".join(f"fct:{b}" for b in value.broader))
        else:
            lines.append(f"skos:topConceptOf fct:{value.scheme}")
        if value.related:
            lines.append("skos:related " + " , ".join(f"fct:{r}" for r in value.related))
        lines.append(f"skos:prefLabel {_literal(value.label)}")
        lines.append(f"skos:definition {_literal(value.definition)}")
        if value.scope_note:
            lines.append(f"skos:scopeNote {_literal(value.scope_note)}")
        if value.group:
            lines.append('skos:editorialNote "group"')
        if not value.ratified:
            lines.append('skos:editorialNote "proposed"')
        out.append(" ;\n    ".join(lines) + " .")
        out.append("")
    return "\n".join(out)


def generate(source: Path = SOURCE_PATH, output: Path = OUTPUT_PATH) -> Path:
    """Write the schemes from ``source`` to ``output``, and return ``output``.

    Rewritten only when the bytes differ, so a build that changes nothing leaves its time alone."""
    text = turtle(*parse(source.read_text(encoding="utf-8")))
    if not output.exists() or output.read_text(encoding="utf-8") != text:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8", newline="\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="parse the register and report, writing nothing")
    arguments = parser.parse_args()
    try:
        if arguments.check:
            schemes, values = parse(SOURCE_PATH.read_text(encoding="utf-8"))
            print(f"{SOURCE_PATH.relative_to(ROOT).as_posix()}: {len(schemes)} schemes, {len(values)} values")
        else:
            print(f"wrote {generate().relative_to(ROOT).as_posix()}")
    except RegisterError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
