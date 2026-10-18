# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The grammar of a README in the layout of ADR-A126, compiled to Turtle text.

``literate_extract.py`` calls ``compile_layout()`` for a README that uses the layout. It returns,
for each document the README's section 2 header table names, the text that opens the document:
its prefixes, its ontology header, the Dublin Core declarations and the statements section 6
compiles to. The extractor appends the README's fenced blocks for that document after it.

Standard library only, as the extractor is. The README authors' description of what is written
here is ``docs/architecture/literate-specifications.md``.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
from urllib.parse import urlparse

STANDARD_PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "dct": "http://purl.org/dc/terms/",
}
# ponytail: one repository's blob URL, so links in a downstream README would point here. Read it from
# the repository catalogue's conventions when downstream catalogues exist (RC4).
REPOSITORY_BLOB = "https://github.com/nebularis/lattice/blob/"
# The release tag naming of the versioning policy, as tools/ontology_releases.py applies it.
NAME_PREFIXES = (("neuro-semantic", "lattice"), ("neuro-semantic",), ("ontologies",))

LINK_RE = re.compile(r"(!?)\[(?P<text>[^\]]*)\]\((?P<url>[^)\s]+)\)")
AUTOLINK_RE = re.compile(r"<(?P<url>https?://[^>]+)>")
CODE_RE = re.compile(r"`([^`]*)`")
EMPHASIS_RE = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1|(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])|(?<![\w])_(?=\S)(.+?)(?<=\S)_(?![\w])")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(?P<text>.*)$")
TABLE_RULE_RE = re.compile(r"^\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")
IRI_RE = re.compile(r"^<?(?P<iri>https?://[^\s<>]+)>?$")
VERSION_RE = re.compile(r"/(?P<version>\d+\.\d+\.\d+)/?$")


class GrammarError(ValueError):
    """A README in the layout that the grammar cannot compile."""


# ---- terms and Turtle text -----------------------------------------------------------------


@dataclass(frozen=True)
class Node:
    """A blank node, written inline as ``[ ... ]``."""

    pairs: Tuple[Tuple[str, "Term"], ...]


@dataclass(frozen=True)
class Collection:
    """An RDF list, written ``( ... )``."""

    items: Tuple["Term", ...]


Term = Union[str, Node, Collection]

# Predicates in the order a statement lists them. Any other predicate follows, alphabetically.
PREDICATE_ORDER = (
    "rdf:type", "owl:versionIRI", "owl:imports", "rdfs:label", "skos:prefLabel", "rdfs:comment", "fnd:utility",
    "skos:scopeNote", "dct:description", "dct:creator", "dct:contributor", "rdfs:subClassOf", "owl:equivalentClass",
    "owl:disjointWith", "owl:hasKey", "rdfs:subPropertyOf", "owl:inverseOf", "rdfs:domain", "rdfs:range",
    "owl:onProperty", "owl:intersectionOf", "owl:unionOf", "owl:complementOf", "owl:someValuesFrom",
    "owl:allValuesFrom", "owl:hasValue", "owl:cardinality", "owl:minCardinality", "owl:maxCardinality",
    "owl:qualifiedCardinality", "owl:minQualifiedCardinality", "owl:maxQualifiedCardinality", "owl:onClass",
    "owl:members",
)


def literal(text: str) -> str:
    """A Turtle string literal, long-quoted where the text spans lines."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    if "\n" in text:
        return f'"""{escaped}"""'
    return f'"{escaped}"'


def _predicate_key(predicate: str) -> Tuple[int, str]:
    return (PREDICATE_ORDER.index(predicate) if predicate in PREDICATE_ORDER else len(PREDICATE_ORDER), predicate)


def render(term: Term) -> str:
    if isinstance(term, Node):
        return "[ " + _pairs(term.pairs, " ; ") + " ]"
    if isinstance(term, Collection):
        return "( " + " ".join(render(item) for item in term.items) + " )"
    return term


def _pairs(pairs: Iterable[Tuple[str, Term]], separator: str) -> str:
    grouped: Dict[str, List[str]] = {}
    for predicate, obj in pairs:
        grouped.setdefault(predicate, []).append(render(obj))
    parts = []
    for predicate in sorted(grouped, key=_predicate_key):
        name = "a" if predicate == "rdf:type" else predicate
        parts.append(f"{name} {', '.join(sorted(set(grouped[predicate])))}")
    return separator.join(parts)


@dataclass
class Document:
    """One generated document: its header row and the statements compiled for it."""

    target: str
    ontology_iri: str
    version_iri: str
    imports: Tuple[str, ...]
    statements: Dict[str, List[Tuple[str, Term]]] = field(default_factory=dict)
    anonymous: List[Node] = field(default_factory=list)

    def add(self, subject: str, predicate: str, obj: Term) -> None:
        self.statements.setdefault(subject, []).append((predicate, obj))

    def turtle(self, prefixes: Mapping[str, str]) -> str:
        """The document's opening text: prefixes, the ontology header, then every other statement
        sorted by subject, and anonymous statements last, sorted by their text."""
        lines = [f"@prefix {p}: <{ns}> ." for p, ns in sorted(prefixes.items())]
        head = f"<{self.ontology_iri}>"
        lines += ["", f"{head} " + _pairs(self.statements.get(head, []), " ;\n    ") + " ."]
        for subject in sorted(s for s in self.statements if s != head):
            lines += ["", f"{subject} " + _pairs(self.statements[subject], " ;\n    ") + " ."]
        for node in sorted(self.anonymous, key=render):
            lines += ["", render(node) + " ."]
        return "\n".join(lines) + "\n"


def version_of(version_iri: str) -> str:
    match = VERSION_RE.search(version_iri)
    if match is None:
        raise GrammarError(f"version IRI {version_iri} does not end in a version X.Y.Z")
    return match.group("version")


def release_tag(version_iri: str) -> str:
    """The release tag of a version IRI, by the versioning policy's naming rule."""
    *segments, version = urlparse(version_iri).path.strip("/").split("/")
    for prefix in NAME_PREFIXES:
        if tuple(segments[: len(prefix)]) == prefix:
            segments = segments[len(prefix):]
            break
    return f"{'-'.join(segments).lower()}-v{version}"


# ---- reading the README ----------------------------------------------------------------------


@dataclass(frozen=True)
class Paragraph:
    """Consecutive non-blank prose lines, with the number of the first."""

    line: int
    lines: Tuple[str, ...]

    @property
    def is_table(self) -> bool:
        return all(text.lstrip().startswith("|") for text in self.lines)


def cells(row: str) -> List[str]:
    """A markdown table row's cells, stripped, with code spans unwrapped."""
    text = row.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [CODE_RE.sub(r"\1", cell.strip()) for cell in text.split("|")]


def table(paragraph: Paragraph) -> Tuple[List[str], List[Tuple[int, List[str]]]]:
    """A table's header, normalised to lower case, and its rows with their line numbers."""
    if len(paragraph.lines) < 2 or not TABLE_RULE_RE.match(paragraph.lines[1].strip()):
        raise GrammarError(f"line {paragraph.line}: a table needs a header row and a rule row")
    header = [c.casefold() for c in cells(paragraph.lines[0])]
    rows = [(paragraph.line + 2 + i, cells(r)) for i, r in enumerate(paragraph.lines[2:])]
    return header, rows


@dataclass(frozen=True)
class Readme:
    """A README's lines, which of them are prose, and its regions and sections."""

    lines: Tuple[str, ...]
    prose: frozenset
    excluded: frozenset
    sections: Mapping[str, Tuple[int, int]]

    @classmethod
    def read(cls, markdown: str, scan) -> "Readme":
        lines = tuple(markdown.splitlines())
        excluded = set()
        for region in scan.regions:
            if region.key in ("exclude", "generated"):
                excluded.update(range(region.start_line, region.end_line + 1))
        bounds: Dict[str, Tuple[int, int]] = {}
        heads = sorted(scan.sections, key=lambda s: s.line)
        for i, section in enumerate(heads):
            end = heads[i + 1].line if i + 1 < len(heads) else len(lines) + 1
            bounds[" ".join(section.title.split()).casefold()] = (section.line, end)
        return cls(lines, scan.prose, frozenset(excluded), bounds)

    def section(self, title: str) -> Tuple[int, int]:
        key = title.casefold()
        if key not in self.sections:
            raise GrammarError(f"the README has no section {title!r}")
        return self.sections[key]

    def paragraphs(self, start: int, end: int) -> List[Paragraph]:
        """The prose paragraphs strictly after line ``start`` and before line ``end``, without
        excluded or generated regions."""
        found: List[Paragraph] = []
        current: List[str] = []
        first = 0
        for number in range(start + 1, end):
            text = self.lines[number - 1]
            usable = number in self.prose and number not in self.excluded and text.strip()
            if usable:
                if not current:
                    first = number
                current.append(text)
            elif current:
                found.append(Paragraph(first, tuple(current)))
                current = []
        if current:
            found.append(Paragraph(first, tuple(current)))
        return found


def plain_text(paragraphs: Sequence[Paragraph], base: str, tag: Optional[str]) -> str:
    """Markdown paragraphs as plain text (ADR-A126 decision 10). Code spans and emphasis lose their
    marks, list items stay one to a line, and a link becomes its text and an absolute URL, at the
    release tag ``tag`` for a link into the repository. ``base`` is the README's directory."""
    out: List[str] = []
    for paragraph in paragraphs:
        if paragraph.is_table:
            raise GrammarError(f"line {paragraph.line}: a table cannot be extracted as text, exclude it")
        texts: List[str] = []
        for offset, raw in enumerate(paragraph.lines):
            number = paragraph.line + offset
            if raw.lstrip().startswith("#"):
                raise GrammarError(f"line {number}: a heading cannot be extracted as text")
            item = LIST_ITEM_RE.match(raw)
            text = _inline(item.group("text") if item else raw.strip(), base, tag, number)
            if item:
                texts.append(f"- {text}")
            elif texts:
                texts[-1] += " " + text  # the paragraph, or a list item, continued
            else:
                texts.append(text)
        out.append("\n".join(texts))
    return "\n\n".join(out)


def _inline(text: str, base: str, tag: Optional[str], number: int) -> str:
    def link(match: re.Match) -> str:
        if match.group(1):
            raise GrammarError(f"line {number}: an image cannot be extracted as text, exclude it")
        return f"{match.group('text')} ({_absolute(match.group('url'), base, tag, number)})"

    text = LINK_RE.sub(link, text)
    text = AUTOLINK_RE.sub(r"\g<url>", text)
    text = CODE_RE.sub(r"\1", text)
    previous = None
    while previous != text:
        previous = text
        text = EMPHASIS_RE.sub(lambda m: next(g for g in m.groups()[1:] if g is not None), text)
    return text


def _absolute(url: str, base: str, tag: Optional[str], number: int) -> str:
    if re.match(r"^[a-z][a-z0-9+.-]*:", url):
        return url
    if tag is None:
        raise GrammarError(f"line {number}: a relative link needs the section 2 version to name its release tag")
    target, _, anchor = url.partition("#")
    path = posixpath.normpath(posixpath.join(base, target)) if target else posixpath.join(base, "README.md")
    if path.startswith(".."):
        raise GrammarError(f"line {number}: the link {url!r} leaves the repository")
    return f"{REPOSITORY_BLOB}{tag}/{path}" + (f"#{anchor}" if anchor else "")


# ---- sections 1 and 2 ---------------------------------------------------------------------------


HEADER_COLUMNS = ["document", "ontology iri", "version iri", "imports"]
PREFIX_COLUMNS = ["prefix", "namespace"]
PEOPLE_COLUMNS = ["identifier", "role", "display name"]
ROLES = {"creator": "dct:creator", "contributor": "dct:contributor"}


def _iri(text: str, number: int, what: str) -> str:
    match = IRI_RE.match(text.strip())
    if match is None:
        raise GrammarError(f"line {number}: {what} {text!r} is not an absolute IRI")
    return match.group("iri")


@dataclass
class Header:
    """What section 2 states: prefixes, documents, and creators and contributors."""

    prefixes: Dict[str, str]
    documents: Dict[str, Document]
    people: List[Tuple[str, str]]


def read_section_2(readme: Readme, layer: str) -> Header:
    start, end = readme.section("Namespace and Prefixes")
    prefixes: Dict[str, str] = {}
    documents: Dict[str, Document] = {}
    people: List[Tuple[str, str]] = []
    seen = set()
    for paragraph in readme.paragraphs(start, end):
        if not paragraph.is_table:
            continue
        header, rows = table(paragraph)
        if header == PREFIX_COLUMNS:
            kind = "prefixes"
            for number, row in rows:
                name = row[0].rstrip(":")
                if not re.match(r"^[A-Za-z][\w.-]*$|^$", name) or name in prefixes:
                    raise GrammarError(f"line {number}: prefix {row[0]!r} is not a new prefix name")
                prefixes[name] = _iri(row[1], number, "namespace")
        elif header == HEADER_COLUMNS:
            kind = "documents"
            for number, row in rows:
                path = row[0]
                if not re.match(r"^(spec|vocab)/[\w./-]+\.ttl$", path) or ".." in path.split("/"):
                    raise GrammarError(f"line {number}: document {path!r} is not a .ttl file under spec/ or vocab/")
                imports = tuple(
                    _iri(i, number, "import") for i in re.split(r"[\s,]+", row[3]) if i and i.casefold() != "none"
                )
                target = f"ontology/{layer}/{path}"
                documents[target] = Document(target, _iri(row[1], number, "ontology IRI"),
                                             _iri(row[2], number, "version IRI"), imports)
                version_of(documents[target].version_iri)
        elif header in (PEOPLE_COLUMNS, PEOPLE_COLUMNS[:2]):
            kind = "people"
            for number, row in rows:
                role = row[1].casefold()
                if role not in ROLES:
                    raise GrammarError(f"line {number}: role {row[1]!r} is not creator or contributor")
                people.append((ROLES[role], _iri(row[0], number, "identifier")))
        else:
            raise GrammarError(
                f"line {paragraph.line}: section 2 holds only the header, prefix and contributor tables, not "
                f"one headed {' | '.join(header)}"
            )
        if kind in seen:
            raise GrammarError(f"line {paragraph.line}: section 2 has two {kind} tables")
        seen.add(kind)
    if "documents" not in seen:
        raise GrammarError("section 2 has no header table (Document | Ontology IRI | Version IRI | Imports)")
    for name, namespace in STANDARD_PREFIXES.items():
        if prefixes.setdefault(name, namespace) != namespace:
            raise GrammarError(f"prefix {name}: is bound to {prefixes[name]}, not its standard namespace {namespace}")
    return Header(prefixes, documents, people)


def compile_layout(markdown: str, scan, layer: str) -> Dict[str, str]:
    """The opening text of every document a README in the layout names, by output path."""
    readme = Readme.read(markdown, scan)
    header = read_section_2(readme, layer)
    last = layer.rsplit("/", 1)[-1]
    default_spec = f"ontology/{layer}/spec/{last}.ttl"
    tag = release_tag(header.documents[default_spec].version_iri) if default_spec in header.documents else None
    start, end = readme.section("Purpose and Scope")
    description = plain_text(readme.paragraphs(start, end), f"ontology/{layer}", tag)
    for document in header.documents.values():
        head = f"<{document.ontology_iri}>"
        document.add(head, "rdf:type", "owl:Ontology")
        document.add(head, "owl:versionIRI", f"<{document.version_iri}>")
        for imported in document.imports:
            document.add(head, "owl:imports", f"<{imported}>")
        used = []
        if description:
            document.add(head, "dct:description", literal(description))
            used.append("dct:description")
        for predicate, person in header.people:
            document.add(head, predicate, f"<{person}>")
            used.append(predicate)
        for predicate in sorted(set(used)):
            document.add(predicate, "rdf:type", "owl:AnnotationProperty")
    return {target: document.turtle(header.prefixes) for target, document in header.documents.items()}
