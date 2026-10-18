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
    "owl:members", "owl:oneOf",
    "sh:targetClass", "sh:property", "sh:path", "sh:class", "sh:datatype", "sh:minCount", "sh:maxCount",
    "sh:qualifiedValueShape", "sh:qualifiedMinCount", "sh:qualifiedMaxCount", "sh:hasValue", "sh:in", "sh:message",
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


@dataclass(frozen=True)
class Compiled:
    """What a README in the layout compiles to: the opening of each document section 2 names, and the
    generated structural shapes file, if any restriction is asserted in SHACL, both by output path, and
    the README with its generated regions brought up to date."""

    documents: Dict[str, str]
    shapes: Dict[str, str]
    readme: str


def compile_layout(markdown: str, scan, layer: str) -> Compiled:
    """Compile a README in the layout."""
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
    section6 = Section6(readme, header, layer, scan.regions, tag)
    section6.compile()
    documents = {target: document.turtle(header.prefixes) for target, document in header.documents.items()}
    shapes = structural_shapes(section6.restrictions, header.prefixes)
    views = Views(header.documents.values(), section6)
    regions = {"axiom-index": views.axiom_index(), "class-diagram": views.class_diagram()}
    refreshed = refresh(markdown, scan, regions, {
        "axiom-index": section6.ranges["axiom index"], "class-diagram": readme.section("Overview"),
    })
    return Compiled(documents, {f"ontology/{layer}/shapes/structural.ttl": shapes} if shapes else {}, refreshed)


# ---- OWL Manchester syntax, the subset section 6 uses (ADR-A126 decision 4) ----------------------

TOKEN_RE = re.compile(
    r'\s*(?:(?P<paren>[()])|(?P<brace>[{}])|(?P<comma>,)|(?P<literal>"(?:[^"\\]|\\.)*"(?:@[A-Za-z][\w-]*|\^\^[A-Za-z][\w.-]*:[\w.-]*)?)'
    r"|(?P<iri><[^>\s]+>)|(?P<number>-?\d+)|(?P<curie>[A-Za-z][\w.-]*:[\w.-]*|:[\w.-]+)|(?P<word>[a-z]+)|(?P<other>\S))"
)
RESTRICTION_WORDS = ("some", "only", "value", "min", "max", "exactly")
CARDINALITY = {
    "exactly": ("owl:cardinality", "owl:qualifiedCardinality"),
    "min": ("owl:minCardinality", "owl:minQualifiedCardinality"),
    "max": ("owl:maxCardinality", "owl:maxQualifiedCardinality"),
}


class Manchester:
    """A recursive-descent parser for ``or``, ``and``, ``not``, parentheses, named classes and
    datatypes, and the restrictions ``some``, ``only``, ``value``, ``min``, ``max`` and ``exactly``,
    qualified or not. ``and`` binds tighter than ``or``, and ``not`` tighter than both."""

    def __init__(self, text: str, prefixes: Mapping[str, str], where: str) -> None:
        self.where = where
        self.prefixes = prefixes
        self.tokens: List[Tuple[str, str]] = []
        for match in TOKEN_RE.finditer(text.strip()):
            kind = match.lastgroup
            if kind == "other":
                raise GrammarError(f"{where}: unexpected {match.group(kind)!r} in {text!r}")
            self.tokens.append((kind, match.group(kind)))
        self.position = 0
        self.text = text

    def fail(self, message: str) -> GrammarError:
        return GrammarError(f"{self.where}: {message} in {self.text!r}")

    def peek(self) -> Tuple[str, str]:
        return self.tokens[self.position] if self.position < len(self.tokens) else ("end", "")

    def take(self) -> Tuple[str, str]:
        token = self.peek()
        self.position += 1
        return token

    def parse(self) -> Term:
        term = self.disjunction()
        if self.peek()[0] != "end":
            raise self.fail(f"unexpected {self.peek()[1]!r}")
        return term

    def disjunction(self) -> Term:
        items = [self.conjunction()]
        while self.peek() == ("word", "or"):
            self.take()
            items.append(self.conjunction())
        return items[0] if len(items) == 1 else Node((("rdf:type", "owl:Class"), ("owl:unionOf", Collection(tuple(items)))))

    def conjunction(self) -> Term:
        items = [self.unary()]
        while self.peek() == ("word", "and"):
            self.take()
            items.append(self.unary())
        if len(items) == 1:
            return items[0]
        return Node((("rdf:type", "owl:Class"), ("owl:intersectionOf", Collection(tuple(items)))))

    def unary(self) -> Term:
        kind, value = self.peek()
        if (kind, value) == ("word", "not"):
            self.take()
            return Node((("rdf:type", "owl:Class"), ("owl:complementOf", self.unary())))
        if (kind, value) == ("paren", "("):
            self.take()
            term = self.disjunction()
            if self.take() != ("paren", ")"):
                raise self.fail("a parenthesis is not closed")
            return term
        if (kind, value) == ("brace", "{"):
            return self.enumeration()
        if kind in ("curie", "iri"):
            name = self.name()
            if self.peek()[0] == "word" and self.peek()[1] in RESTRICTION_WORDS:
                return self.restriction(name)
            return name
        raise self.fail(f"expected a class, a restriction or a parenthesis, found {value or 'the end'!r}")

    def enumeration(self) -> Node:
        """``{ a, b }``: an enumerated class of individuals, or an enumerated data range of literals."""
        self.take()
        items: List[str] = []
        literals = []
        while True:
            kind, value = self.peek()
            if kind in ("literal", "number"):
                self.take()
                items.append(self.literal(value))
                literals.append(True)
            elif kind in ("curie", "iri"):
                items.append(self.name())
                literals.append(False)
            else:
                raise self.fail(f"an enumeration holds names or literals, found {value or 'the end'!r}")
            kind, value = self.take()
            if (kind, value) == ("brace", "}"):
                break
            if kind != "comma":
                raise self.fail("an enumeration separates its members with commas and ends with }")
        if len(set(literals)) > 1:
            raise self.fail("an enumeration holds names or literals, not both")
        kind_of = "rdfs:Datatype" if literals[0] else "owl:Class"
        return Node((("rdf:type", kind_of), ("owl:oneOf", Collection(tuple(items)))))

    def name(self) -> str:
        kind, value = self.take()
        if kind == "iri":
            return value
        if kind != "curie":
            raise self.fail(f"expected a name, found {value or 'the end'!r}")
        prefix = value.split(":", 1)[0]
        if prefix not in self.prefixes:
            raise self.fail(f"prefix {prefix}: is not declared in section 2")
        return value

    def restriction(self, prop: str) -> Node:
        _, word = self.take()
        pairs: List[Tuple[str, Term]] = [("rdf:type", "owl:Restriction"), ("owl:onProperty", prop)]
        if word in ("some", "only"):
            pairs.append(("owl:someValuesFrom" if word == "some" else "owl:allValuesFrom", self.unary()))
        elif word == "value":
            kind, value = self.peek()
            if kind in ("literal", "number"):
                self.take()
                pairs.append(("owl:hasValue", self.literal(value)))
            else:
                pairs.append(("owl:hasValue", self.name()))
        else:
            kind, number = self.take()
            if kind != "number" or int(number) < 0:
                raise self.fail(f"{word} needs a whole number")
            count = f'"{int(number)}"^^xsd:nonNegativeInteger'
            unqualified, qualified = CARDINALITY[word]
            if self.peek()[0] in ("curie", "iri") or self.peek() in (("paren", "("), ("word", "not")):
                pairs += [(qualified, count), ("owl:onClass", self.unary())]
            else:
                pairs.append((unqualified, count))
        return Node(tuple(pairs))

    def literal(self, value: str) -> str:
        datatype = re.search(r"\^\^([A-Za-z][\w.-]*):", value)
        if datatype and datatype.group(1) not in self.prefixes:
            raise self.fail(f"prefix {datatype.group(1)}: is not declared in section 2")
        return value


def class_expression(text: str, prefixes: Mapping[str, str], where: str) -> Term:
    return Manchester(text, prefixes, where).parse()


def split_top_level(text: str) -> List[str]:
    """``text`` split at the commas outside parentheses."""
    parts, depth, current = [], 0, []
    for char in text:
        if char in "({":
            depth += 1
        elif char in ")}":
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if "".join(current).strip():
        parts.append("".join(current).strip())
    return parts


# ---- section 6, the Description Logic Encoding --------------------------------------------------

SUBSECTIONS = ("classes", "object properties", "datatype properties", "individuals", "disjointness and keys",
               "other axioms", "axiom index")
SUBSECTION_RE = re.compile(r"^###\s+(?:\d+\.\d+\.?\s+)?(?P<title>.+?)\s*$")
ENTRY_RE = re.compile(r"^####\s+`(?P<curie>[^`]+)`\s*$")
LABEL_RE = re.compile(r"^\*\*(?P<label>[^*]+?)\.\*\*\s*(?P<rest>.*)$")
TURTLE_LITERAL_RE = re.compile(r'^"(?:[^"\\]|\\.)*"(?:@[A-Za-z][\w-]*|\^\^[A-Za-z][\w.-]*:[\w.-]*)$')
ANNOTATIONS = {
    "definition": "rdfs:comment", "utility": "fnd:utility", "label": "rdfs:label",
    "preferred label": "skos:prefLabel", "scope note": "skos:scopeNote",
}
CLASS_LABELS = {"subclass of", "equivalent to", "key", "restrictions"}
PROPERTY_LABELS = {"domain", "range", "characteristics", "inverse of", "subproperty of"}
CHARACTERISTICS = {
    "functional": "owl:FunctionalProperty", "inverse functional": "owl:InverseFunctionalProperty",
    "transitive": "owl:TransitiveProperty", "symmetric": "owl:SymmetricProperty",
}
KIND_TYPES = {"classes": "owl:Class", "object properties": "owl:ObjectProperty", "datatype properties": "owl:DatatypeProperty"}
RESTRICTION_COLUMNS = (["property", "values", "asserted in"], ["property", "values", "asserted in", "message"])


@dataclass(frozen=True)
class Restriction:
    """One row of a class's restriction table, kept for the SHACL that slice OD4 generates."""

    subject: str
    prop: str
    values: str
    asserted_in: str
    message: str
    line: int


class Section6:
    """Compiles section 6's entries, individuals and disjointness into the documents' statements."""

    def __init__(self, readme: Readme, header: Header, layer: str, regions: Sequence, tag: Optional[str]) -> None:
        self.readme, self.header, self.layer, self.tag = readme, header, layer, tag
        self.prefixes = header.prefixes
        self.files = [(r.start_line, r.end_line, r.value) for r in regions if r.key == "output-file"]
        last = layer.rsplit("/", 1)[-1]
        self.defaults = {"spec": f"ontology/{layer}/spec/{last}.ttl", "vocab": f"ontology/{layer}/vocab/{last}-vocab.ttl"}
        self.restrictions: List[Restriction] = []
        self.subjects: set = set()
        self.ranges: Dict[str, Tuple[int, int]] = {}
        self.table_terms: set = set()

    # -- helpers

    def document(self, line: int, kind: str) -> Document:
        """The document a statement written at ``line`` goes to: its innermost output-file region's, or
        the module's default spec or vocab document."""
        enclosing = [(start, value) for start, end, value in self.files if start < line < end]
        target = f"ontology/{self.layer}/{max(enclosing)[1]}" if enclosing else self.defaults[kind]
        if target not in self.header.documents:
            raise GrammarError(f"line {line}: section 6 writes to {target}, which section 2's header table does not name")
        return self.header.documents[target]

    def curie(self, text: str, line: int) -> str:
        term = class_expression(text, self.prefixes, f"line {line}")
        if not isinstance(term, str):
            raise GrammarError(f"line {line}: expected a name, not an expression, in {text!r}")
        return term

    def annotation(self, text: str, line: int) -> str:
        value = text.strip()
        if TURTLE_LITERAL_RE.match(value):
            return value
        return literal(plain_text([Paragraph(line, (value,))], f"ontology/{self.layer}", self.tag))

    # -- the walk

    def compile(self) -> None:
        start, end = self.readme.section("Description Logic Encoding")
        heads = [(n, SUBSECTION_RE.match(self.readme.lines[n - 1])) for n in range(start + 1, end)
                 if n in self.readme.prose and self.readme.lines[n - 1].startswith("### ")]
        titles = []
        for i, (number, match) in enumerate(heads):
            title = " ".join(match.group("title").split()).casefold()
            if title not in SUBSECTIONS:
                raise GrammarError(f"line {number}: section 6 has no subsection {match.group('title')!r}")
            titles.append(title)
            stop = heads[i + 1][0] if i + 1 < len(heads) else end
            self.ranges[title] = (number, stop)
            if title in KIND_TYPES:
                self.entries(title, number, stop)
            elif title == "individuals":
                self.individuals(number, stop)
            elif title == "disjointness and keys":
                self.disjointness(number, stop)
        missing = [t for t in SUBSECTIONS if t not in titles]
        if missing:
            raise GrammarError(f"section 6 is missing its subsection(s) {', '.join(missing)}")

    def entries(self, kind: str, start: int, end: int) -> None:
        lines = self.readme.lines
        heads = [n for n in range(start + 1, end) if n in self.readme.prose and lines[n - 1].startswith("####")]
        for i, number in enumerate(heads):
            match = ENTRY_RE.match(lines[number - 1])
            if match is None:
                raise GrammarError(f"line {number}: an entry's heading holds one CURIE in backticks")
            subject = self.curie(match.group("curie"), number)
            if subject in self.subjects:
                raise GrammarError(f"line {number}: {subject} has a second entry")
            self.subjects.add(subject)
            stop = heads[i + 1] if i + 1 < len(heads) else end
            self.entry(kind, subject, number, stop)

    def entry(self, kind: str, subject: str, start: int, end: int) -> None:
        document = self.document(start, "spec")
        document.add(subject, "rdf:type", KIND_TYPES[kind])
        paragraphs = self.readme.paragraphs(start, end)
        labels = set()
        index = 0
        while index < len(paragraphs):
            paragraph = paragraphs[index]
            match = LABEL_RE.match(paragraph.lines[0].strip())
            if match is None:
                raise GrammarError(f"line {paragraph.line}: a paragraph of an entry starts with a label, for example **Definition.**")
            label = match.group("label").strip().casefold()
            text = " ".join([match.group("rest"), *[l.strip() for l in paragraph.lines[1:]]]).strip()
            where = f"line {paragraph.line}"
            if label in labels and label != "restrictions":
                raise GrammarError(f"{where}: {subject} has a second **{match.group('label')}.**")
            labels.add(label)
            if label in ANNOTATIONS:
                document.add(subject, ANNOTATIONS[label], self.annotation(text, paragraph.line))
                self.prefix_of(ANNOTATIONS[label], where)
            elif label in CLASS_LABELS and kind != "classes" or label in PROPERTY_LABELS and kind == "classes":
                raise GrammarError(f"{where}: **{match.group('label')}.** does not apply to {kind}")
            elif label == "subclass of":
                for part in split_top_level(CODE_RE.sub(r"\1", text)):
                    document.add(subject, "rdfs:subClassOf", class_expression(part, self.prefixes, where))
            elif label == "equivalent to":
                document.add(subject, "owl:equivalentClass", class_expression(CODE_RE.sub(r"\1", text), self.prefixes, where))
            elif label == "key":
                keys = tuple(self.curie(p, paragraph.line) for p in split_top_level(CODE_RE.sub(r"\1", text)))
                document.add(subject, "owl:hasKey", Collection(keys))
            elif label == "restrictions":
                if text or index + 1 >= len(paragraphs) or not paragraphs[index + 1].is_table:
                    raise GrammarError(f"{where}: **Restrictions.** stands alone, followed by its table")
                index += 1
                self.restriction_table(document, subject, paragraphs[index])
            elif label in ("domain", "range"):
                predicate = "rdfs:domain" if label == "domain" else "rdfs:range"
                document.add(subject, predicate, class_expression(CODE_RE.sub(r"\1", text), self.prefixes, where))
            elif label == "characteristics":
                for part in split_top_level(text):
                    characteristic = " ".join(part.split()).casefold()
                    if characteristic not in CHARACTERISTICS:
                        raise GrammarError(f"{where}: {part!r} is not one of {', '.join(CHARACTERISTICS)}")
                    document.add(subject, "rdf:type", CHARACTERISTICS[characteristic])
            elif label == "inverse of":
                document.add(subject, "owl:inverseOf", self.curie(CODE_RE.sub(r"\1", text), paragraph.line))
            elif label == "subproperty of":
                for part in split_top_level(CODE_RE.sub(r"\1", text)):
                    document.add(subject, "rdfs:subPropertyOf", self.curie(part, paragraph.line))
            else:
                raise GrammarError(f"{where}: unknown label **{match.group('label')}.**")
            index += 1
        if "definition" not in labels:
            raise GrammarError(f"line {start}: {subject} has no **Definition.**")

    def prefix_of(self, curie: str, where: str) -> None:
        if curie.split(":", 1)[0] not in self.prefixes:
            raise GrammarError(f"{where}: {curie} needs the prefix {curie.split(':', 1)[0]}: declared in section 2")

    def restriction_table(self, document: Document, subject: str, paragraph: Paragraph) -> None:
        header, rows = table(paragraph)
        if header not in RESTRICTION_COLUMNS:
            raise GrammarError(f"line {paragraph.line}: a restriction table's columns are Property | Values | Asserted in | Message")
        for number, row in rows:
            row = row + [""] * (4 - len(row))
            prop = self.curie(row[0], number)
            asserted = row[2].strip().casefold()
            if asserted not in ("", "owl", "shacl"):
                raise GrammarError(f"line {number}: Asserted in is blank, OWL or SHACL, not {row[2]!r}")
            self.restrictions.append(Restriction(subject, prop, row[1], asserted or "owl and shacl", row[3], number))
            term = class_expression(f"{prop} {row[1]}", self.prefixes, f"line {number}")
            if not (isinstance(term, Node) and ("rdf:type", "owl:Restriction") in term.pairs):
                raise GrammarError(f"line {number}: the values {row[1]!r} do not make a restriction on {prop}")
            self.table_terms.add(term)
            if asserted != "shacl":
                document.add(subject, "rdfs:subClassOf", term)

    def individuals(self, start: int, end: int) -> None:
        for paragraph in self.readme.paragraphs(start, end):
            if not paragraph.is_table:
                continue
            header, rows = table(paragraph)
            if header[:2] != ["individual", "type"] or any(h not in ANNOTATIONS for h in header[2:]):
                raise GrammarError(
                    f"line {paragraph.line}: an individuals table's columns are Individual | Type, then any of "
                    f"{', '.join(a.capitalize() for a in ANNOTATIONS)}"
                )
            document = self.document(paragraph.line, "vocab")
            for number, row in rows:
                subject = self.curie(row[0], number)
                if subject in self.subjects:
                    raise GrammarError(f"line {number}: {subject} is stated twice in section 6")
                self.subjects.add(subject)
                for kind in split_top_level(row[1]):
                    document.add(subject, "rdf:type", self.curie(kind, number))
                for column, value in zip(header[2:], row[2:]):
                    if value.strip():
                        document.add(subject, ANNOTATIONS[column], self.annotation(value, number))

    def disjointness(self, start: int, end: int) -> None:
        for paragraph in self.readme.paragraphs(start, end):
            match = LABEL_RE.match(paragraph.lines[0].strip())
            if match is None:
                continue
            label = match.group("label").strip().casefold()
            text = " ".join([match.group("rest"), *[l.strip() for l in paragraph.lines[1:]]])
            names = [self.curie(p, paragraph.line) for p in split_top_level(CODE_RE.sub(r"\1", text))]
            document = self.document(paragraph.line, "spec")
            if label == "all disjoint":
                if len(names) < 2:
                    raise GrammarError(f"line {paragraph.line}: **All disjoint.** names two classes or more")
                document.anonymous.append(Node((("rdf:type", "owl:AllDisjointClasses"), ("owl:members", Collection(tuple(names))))))
            elif label == "disjoint":
                if len(names) != 2:
                    raise GrammarError(f"line {paragraph.line}: **Disjoint.** names exactly two classes")
                document.add(names[0], "owl:disjointWith", names[1])
            else:
                raise GrammarError(f"line {paragraph.line}: section 6.5 takes **All disjoint.** or **Disjoint.**, not **{match.group('label')}.**")



# ---- section 6 to SHACL (ADR-A126 decision 5) ------------------------------------------------------

SHACL_NAMESPACE = "http://www.w3.org/ns/shacl#"
DATATYPE_NAMES = {"rdfs:Literal", "rdf:langString", "rdf:PlainLiteral"}


def _count(literal_text: str) -> str:
    return literal_text.split('"')[1]


def _named(term: Term, row: Restriction, form: str) -> str:
    if not isinstance(term, str):
        raise GrammarError(
            f"line {row.line}: {form} a nested expression is not checked in SHACL. Mark the row OWL, or state the "
            f"shape in section 7"
        )
    return term


def shacl_constraints(row: Restriction, term: Node) -> List[Tuple[str, Term]]:
    """The SHACL that one restriction row's flat form maps to. A qualified restriction maps to SHACL's
    qualified form, never to ``sh:class`` with counts, since the two say different things."""
    pairs = dict(term.pairs)
    if "owl:allValuesFrom" in pairs:
        enumerated = pairs["owl:allValuesFrom"]
        if isinstance(enumerated, Node) and "owl:oneOf" in dict(enumerated.pairs):
            return [("sh:in", dict(enumerated.pairs)["owl:oneOf"])]
        filler = _named(pairs["owl:allValuesFrom"], row, "only with")
        datatype = filler.startswith("xsd:") or filler in DATATYPE_NAMES
        return [("sh:datatype" if datatype else "sh:class", filler)]
    if "owl:someValuesFrom" in pairs:
        filler = _named(pairs["owl:someValuesFrom"], row, "some with")
        return [("sh:qualifiedValueShape", Node((("sh:class", filler),))), ("sh:qualifiedMinCount", "1")]
    if "owl:hasValue" in pairs:
        return [("sh:hasValue", pairs["owl:hasValue"])]
    for word, (unqualified, qualified) in CARDINALITY.items():
        if unqualified in pairs:
            n = _count(pairs[unqualified])
            return {"exactly": [("sh:minCount", n), ("sh:maxCount", n)], "min": [("sh:minCount", n)],
                    "max": [("sh:maxCount", n)]}[word]
        if qualified in pairs:
            n = _count(pairs[qualified])
            shape = ("sh:qualifiedValueShape", Node((("sh:class", _named(pairs["owl:onClass"], row, word + " of")),)))
            return [shape] + {"exactly": [("sh:qualifiedMinCount", n), ("sh:qualifiedMaxCount", n)],
                              "min": [("sh:qualifiedMinCount", n)], "max": [("sh:qualifiedMaxCount", n)]}[word]
    raise GrammarError(f"line {row.line}: the values {row.values!r} have no SHACL form")


def structural_shapes(restrictions: Sequence[Restriction], prefixes: Mapping[str, str]) -> str:
    """The structural shapes file: one ``<Class>Shape`` per class with a row asserted in SHACL, and one
    property shape per property and message, merging the constraints of that property's rows."""
    merged: Dict[Tuple[str, str, str], List[Tuple[str, Term]]] = {}
    for row in restrictions:
        if row.asserted_in == "owl":
            continue
        term = class_expression(f"{row.prop} {row.values}", prefixes, f"line {row.line}")
        key = (row.subject, row.prop, row.message)
        pairs = merged.setdefault(key, [])
        for predicate, obj in shacl_constraints(row, term):
            if any(p == predicate for p, _ in pairs):
                raise GrammarError(
                    f"line {row.line}: {row.subject}'s rows for {row.prop} state {predicate} twice. Give one of them its own message"
                )
            pairs.append((predicate, obj))
    if not merged:
        return ""
    if prefixes.get("sh", SHACL_NAMESPACE) != SHACL_NAMESPACE:
        raise GrammarError(f"prefix sh: is bound to {prefixes['sh']}, not the SHACL namespace")
    shapes: Dict[str, List[Tuple[str, Term]]] = {}
    for (subject, prop, message), pairs in merged.items():
        if ":" not in subject or subject.startswith("<"):
            raise GrammarError(f"{subject} needs a CURIE to name its shape")
        name = f"{subject}Shape"
        shape = shapes.setdefault(name, [("rdf:type", "sh:NodeShape"), ("sh:targetClass", subject)])
        constraint = [("sh:path", prop), *pairs] + ([("sh:message", literal(message))] if message else [])
        shape.append(("sh:property", Node(tuple(constraint))))
    lines = [f"@prefix {p}: <{ns}> ." for p, ns in sorted({**prefixes, "sh": SHACL_NAMESPACE}.items())]
    for name in sorted(shapes):
        lines += ["", f"{name} " + _pairs(shapes[name], " ;\n    ") + " ."]
    return "\n".join(lines) + "\n"



# ---- generated views: the Axiom Index and the class diagram (ADR-A126 decision 7) --------------------

KIND_NAMES = {"owl:Class": "Class", "owl:ObjectProperty": "Object property", "owl:DatatypeProperty": "Datatype property"}
KIND_ORDER = ("Class", "Object property", "Datatype property", "Individual")
NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
CHARACTERISTIC_NAMES = {v: k for k, v in CHARACTERISTICS.items()}
COMPOUND = ("owl:unionOf", "owl:intersectionOf", "owl:complementOf")


def manchester(term: Term, code: bool = True, nested: bool = False) -> str:
    """A term written back in Manchester syntax, names in backticks when ``code``."""
    if isinstance(term, str):
        return f"`{term}`" if code and not term.startswith(('"', "<")) and not term[:1].isdigit() else term
    if isinstance(term, Collection):
        return ", ".join(manchester(item, code) for item in term.items)
    pairs = dict(term.pairs)
    if "owl:onProperty" in pairs:
        prop = manchester(pairs["owl:onProperty"], code)
        for key, word in (("owl:someValuesFrom", "some"), ("owl:allValuesFrom", "only"), ("owl:hasValue", "value")):
            if key in pairs:
                text = f"{prop} {word} {manchester(pairs[key], code, True)}"
                break
        else:
            for word, (unqualified, qualified) in CARDINALITY.items():
                if unqualified in pairs:
                    text = f"{prop} {word} {_count(pairs[unqualified])}"
                elif qualified in pairs:
                    text = f"{prop} {word} {_count(pairs[qualified])} {manchester(pairs['owl:onClass'], code, True)}"
                else:
                    continue
                break
    elif "owl:oneOf" in pairs:
        return "{" + ", ".join(manchester(item, code) for item in pairs["owl:oneOf"].items) + "}"
    elif "owl:complementOf" in pairs:
        text = f"not {manchester(pairs['owl:complementOf'], code, True)}"
    else:
        key, word = ("owl:unionOf", " or ") if "owl:unionOf" in pairs else ("owl:intersectionOf", " and ")
        text = word.join(manchester(item, code, True) for item in pairs[key].items)
    return f"({text})" if nested else text


def verbalise(term: Node) -> str:
    """A restriction in the class diagram's words, for example "exactly one" or "at least two Item"."""
    pairs = dict(term.pairs)
    for word, phrase in (("exactly", "exactly"), ("min", "at least"), ("max", "at most")):
        unqualified, qualified = CARDINALITY[word]
        for key in (unqualified, qualified):
            if key in pairs:
                n = int(_count(pairs[key]))
                count = NUMBER_WORDS[n] if n < len(NUMBER_WORDS) else str(n)
                filler = f" {_local(pairs['owl:onClass'])}" if key == qualified else ""
                return f"{phrase} {count}{filler}"
    for key, word in (("owl:someValuesFrom", "some"), ("owl:allValuesFrom", "only"), ("owl:hasValue", "value")):
        if key in pairs:
            filler = pairs[key]
            if isinstance(filler, Node) and "owl:oneOf" in dict(filler.pairs):
                return f"{word} one of {', '.join(_local(i) for i in dict(filler.pairs)['owl:oneOf'].items)}"
            return f"{word} {_local(filler)}"
    return manchester(term, code=False)


def _local(term: Term) -> str:
    if isinstance(term, str) and ":" in term and not term.startswith(('"', "<")):
        return term.split(":", 1)[1]
    return manchester(term, code=False)


class Views:
    """The Axiom Index and the class diagram, read from the compiled statements and restriction rows."""

    def __init__(self, documents: Iterable[Document], section6: "Section6") -> None:
        self.facts: Dict[str, List[Tuple[str, Term]]] = {}
        self.anonymous: List[Node] = []
        for document in documents:
            heads = {f"<{document.ontology_iri}>"}
            for subject, pairs in document.statements.items():
                types = {o for p, o in pairs if p == "rdf:type"}
                if subject in heads or "owl:AnnotationProperty" in types:
                    continue
                self.facts.setdefault(subject, []).extend(pairs)
            self.anonymous.extend(document.anonymous)
        self.rows = section6.restrictions
        self.table_terms = section6.table_terms
        self.prefixes = section6.prefixes

    def kind(self, subject: str) -> str:
        types = {o for p, o in self.facts[subject] if p == "rdf:type"}
        return next((KIND_NAMES[t] for t in KIND_NAMES if t in types), "Individual" if types else "")

    def values(self, subject: str, predicate: str) -> List[Term]:
        return [o for p, o in self.facts.get(subject, []) if p == predicate]

    def axiom_index(self) -> str:
        rows = []
        for subject in sorted(self.facts, key=lambda s: (KIND_ORDER.index(self.kind(s)) if self.kind(s) in KIND_ORDER else 9, s)):
            kind = self.kind(subject)
            if not kind:
                continue
            rows.append(f"| `{subject}` | {kind} | {' '.join(self.summary(subject, kind))} |")
        if not rows:
            return "None."
        return "\n".join(["| Term | Kind | Summary |", "|---|---|---|", *rows])

    def summary(self, subject: str, kind: str) -> List[str]:
        parts: List[str] = []

        def sentence(label: str, terms: Sequence[Term]) -> None:
            if terms:
                parts.append(f"{label} {', '.join(manchester(term) for term in terms)}.")

        if kind == "Class":
            sentence("Subclass of", sorted((t for t in self.values(subject, "rdfs:subClassOf") if t not in self.table_terms), key=render))
            sentence("Equivalent to", self.values(subject, "owl:equivalentClass"))
            sentence("Key", self.values(subject, "owl:hasKey"))
            disjoint = self.values(subject, "owl:disjointWith") + [
                d for node in self.anonymous for d in dict(node.pairs)["owl:members"].items
                if subject in dict(node.pairs)["owl:members"].items and d != subject
            ] + [s for s in self.facts if subject in self.values(s, "owl:disjointWith")]
            sentence("Disjoint with", sorted(set(disjoint)))
            restrictions = []
            for row in self.rows:
                if row.subject == subject:
                    note = {"owl": " (OWL only)", "shacl": " (SHACL only)"}.get(row.asserted_in, "")
                    term = class_expression(f"{row.prop} {row.values}", self.prefixes, f"line {row.line}")
                    restrictions.append(manchester(term) + note)
            if restrictions:
                parts.append(f"Restrictions {', '.join(sorted(restrictions))}.")
        elif kind == "Individual":
            sentence("Type", sorted(t for t in self.values(subject, "rdf:type")))
        else:
            sentence("Domain", self.values(subject, "rdfs:domain"))
            sentence("Range", self.values(subject, "rdfs:range"))
            characteristics = sorted(CHARACTERISTIC_NAMES[t] for t in self.values(subject, "rdf:type") if t in CHARACTERISTIC_NAMES)
            if characteristics:
                parts.append(", ".join(characteristics).capitalize() + ".")
            sentence("Inverse of", self.values(subject, "owl:inverseOf"))
            sentence("Subproperty of", self.values(subject, "rdfs:subPropertyOf"))
        return parts

    def class_diagram(self) -> str:
        classes = sorted(s for s in self.facts if self.kind(s) == "Class")
        properties = sorted(s for s in self.facts if self.kind(s) in ("Object property", "Datatype property"))
        if not classes and not properties:
            return "None."
        named = set(classes)
        for subject in classes:
            named.update(t for t in self.values(subject, "rdfs:subClassOf") if isinstance(t, str))
        for prop in properties:
            named.update(t for p in ("rdfs:domain", "rdfs:range") for t in self.values(prop, p)
                         if isinstance(t, str) and self.kind(prop) == "Object property")
        ids = self._identifiers(named)
        members: Dict[str, List[str]] = {c: [] for c in sorted(named)}
        links: List[str] = []
        boxes: List[str] = []
        for row in self.rows:
            term = class_expression(f"{row.prop} {row.values}", self.prefixes, f"line {row.line}")
            members.setdefault(row.subject, []).append(f"{_local(row.prop)}, {verbalise(term)}")
        for subject in classes:
            for parent in sorted(t for t in self.values(subject, "rdfs:subClassOf") if isinstance(t, str)):
                links.append(f"{ids[parent]} <|-- {ids[subject]}")
        for prop in properties:
            domains = [t for t in self.values(prop, "rdfs:domain") if isinstance(t, str)]
            ranges = [t for t in self.values(prop, "rdfs:range") if isinstance(t, str)]
            local = _local(prop)
            if self.kind(prop) == "Object property" and domains and ranges:
                links += [f"{ids[d]} --> {ids[r]} : {local}" for d in domains for r in ranges]
            elif domains:
                suffix = f" ({ranges[0]})" if self.kind(prop) == "Datatype property" and ranges else ""
                for d in domains:
                    if not any(m.startswith(f"{local},") for m in members.get(d, [])):
                        members.setdefault(d, []).append(f"{local}{suffix}")
            else:
                kind = self.kind(prop).replace("property", "Property")
                identifier = re.sub(r"[^A-Za-z0-9_]", "_", f"{kind.replace(' ', '')}_{local}")
                boxes.append(f'    class {identifier}["{kind} - {local}"]')
        lines = ["```mermaid", "classDiagram"]
        for subject in sorted(members, key=lambda c: ids.get(c, c)):
            if subject not in ids:
                continue
            if members[subject]:
                lines += [f"    class {ids[subject]} {{", *[f"        {m}" for m in sorted(members[subject])], "    }"]
            else:
                lines.append(f"    class {ids[subject]}")
        lines += [f"    {link}" for link in sorted(set(links))] + boxes + ["```"]
        return "\n".join(lines)

    @staticmethod
    def _identifiers(names: Iterable[str]) -> Dict[str, str]:
        """Each class's identifier in the diagram: its local name, qualified by its prefix where two
        classes would otherwise share one."""
        names = sorted(names)
        locals_ = [_local(n) for n in names]
        out = {}
        for name, local in zip(names, locals_):
            text = local if locals_.count(local) == 1 else name.replace(":", "_")
            out[name] = re.sub(r"[^A-Za-z0-9_]", "_", text)
        return out


def refresh(markdown: str, scan, contents: Mapping[str, str], places: Mapping[str, Tuple[int, int]]) -> str:
    """The README with each generated region's content replaced by ``contents``. Each region is required,
    once, inside its place (a range of line numbers), and an unknown region is refused."""
    lines = markdown.split("\n")
    regions = [r for r in scan.regions if r.key == "generated"]
    for region in regions:
        if region.value not in contents:
            raise GrammarError(f"line {region.start_line}: no generated region is named {region.value!r}")
    for name, (start, end) in places.items():
        found = [r for r in regions if r.value == name]
        if len(found) != 1 or not start < found[0].start_line < end:
            raise GrammarError(f"the README needs one generated region {name!r}, in its place (found {len(found)})")
    for region in sorted(regions, key=lambda r: r.start_line, reverse=True):
        lines[region.start_line:region.end_line - 1] = ["", *contents[region.value].split("\n"), ""]
    return "\n".join(lines)
