# SPDX-License-Identifier: MPL-2.0
"""The logical plan of a MORK mapping scheme over an XML or JSON source (ADR-A148 decision 1): a tree of datums, each
with the path it iterates, how its identity is formed, its types, how it is glued to its parent and what it asserts.
It is lowered from `mork_rdf`'s reading, so a mapping is classified as the SPARQL backend classifies it, and the
identity rules are the SPARQL backend's (README §6 of `tools/mork_rdf`). A form a transform cannot carry is refused
with a finding on its mapping (decision 6)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, SKOS

from mork_rdf.model import MORK, Finding, Severity, local
from mork_rdf.paths import PathError
from mork_rdf.read import Kind, Reading, Spec, iter_roots, read, resolve

from .paths import SourcePath, parse_json, parse_xml

_PLACEHOLDER = re.compile(r"\$\{([^}]+)\}|\{\$([^}]+)\}")
FORMATS = {"xml": (MORK.XML, parse_xml), "json": (MORK.JSON, parse_json)}


@dataclass(frozen=True)
class Ref:
    """The string value of what a path reaches from the focus, encoded for an IRI when `encode`."""

    path: SourcePath
    encode: bool = False


# An identity: a constant IRI, a concatenation of constant text and references, or the node's position under `prefix`.
@dataclass(frozen=True)
class Constant:
    term: Union[URIRef, Literal]


@dataclass(frozen=True)
class Template:
    pieces: tuple[Union[str, Ref], ...]


@dataclass(frozen=True)
class Positional:
    prefix: str


@dataclass(frozen=True)
class Table:
    """A value read by `path` and translated by the rows, each a source notation and the target individual."""

    path: SourcePath
    rows: tuple[tuple[str, URIRef], ...]


@dataclass(frozen=True)
class Assertion:
    mapping: str
    prop: URIRef
    inverse: bool
    value: Union[Ref, Constant, Table]


@dataclass(frozen=True)
class Datum:
    mapping: str
    path: Optional[SourcePath]       # what it iterates from its parent's focus, or from the document for a root. None is the parent's focus
    identity: Union[Constant, Template, Positional]
    types: tuple[URIRef, ...]
    glue: Optional[tuple[URIRef, bool]]  # the property joining it to its parent, and whether the parent is its subject
    assertions: tuple[Assertion, ...]
    children: tuple["Datum", ...]


@dataclass(frozen=True)
class Plan:
    scheme: str
    format: str
    base: str
    roots: tuple[Datum, ...]
    findings: tuple[Finding, ...]

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)


class _Refusal(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


class _Lowering:
    def __init__(self, g: Graph, reading: Reading, fmt: str, base: str):
        self.g, self.r, self.format, self.base = g, reading, fmt, base
        self.parse = FORMATS[fmt][1]
        self.findings: list[Finding] = []

    def named_iri(self, name: str) -> URIRef:
        if name.startswith("#"):
            return URIRef(self.base + name[1:])
        prefix, _, rest = name.partition(":")
        if rest and prefix in self.r.prefixes:
            return URIRef(self.r.prefixes[prefix] + rest)
        if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", name):
            return URIRef(name)
        return URIRef(self.base + name)

    def path(self, text: str) -> SourcePath:
        try:
            return self.parse(text, self.r.prefixes)
        except PathError as error:
            raise _Refusal("BadPath", str(error)) from error

    def constant(self, term: URIRef, own: Spec) -> URIRef:
        """A match as a constant term. A deferred reference that yields a name is that name, and one that yields data
        or another mapping's outcome is not carried."""
        found = resolve(self.g, term, own, self.r.specs)
        if found is None:
            return term
        if found.name:
            return self.named_iri(found.name)
        m = self.r.specs.get(found.outcome) if found.outcome is not None else None
        if m is not None and m.kind is Kind.CLASS_REFERENCE:
            return self.constant(m.strata.tbox["exact"], m)
        raise _Refusal("DeferredNotCarried", f"{term.n3()} yields a name read from data or another mapping's outcome, which a transform does not carry")

    def mapped_path(self, spec: Spec) -> Optional[str]:
        return next((str(p) for c in sorted(self.g.objects(spec.node, MORK.mappingFor), key=str) for p in self.g.objects(c, MORK.path)), None)

    # --- identity ------------------------------------------------------------------------------------------------------

    def expression(self, node, in_iri: bool) -> tuple:
        g = self.g
        if (node, RDF.type, MORK.LiteralExpression) in g:
            return (str(next(iter(g.objects(node, MORK.dataInline)), "")),)
        if (node, RDF.type, MORK.RefExpression) in g:
            text = next(iter(g.objects(node, MORK.dataRef)), None)
            if text is None:
                raise _Refusal("ExpressionIncomplete", f"{node.n3()} is a reference with no mork:dataRef")
            return (Ref(self.path(str(text)), in_iri),)
        if (node, RDF.type, MORK.ConcatExpression) in g:
            left, right = next(iter(g.objects(node, MORK.concatLeft)), None), next(iter(g.objects(node, MORK.concatRight)), None)
            if left is None or right is None:
                raise _Refusal("ExpressionIncomplete", f"{node.n3()} is a concatenation missing an operand")
            return self.expression(left, in_iri) + self.expression(right, in_iri)
        if (node, RDF.type, MORK.InterpolationExpression) in g:
            template = next(iter(g.objects(node, MORK.templateString)), None)
            if template is None:
                raise _Refusal("ExpressionIncomplete", f"{node.n3()} is an interpolation with no mork:templateString")
            bindings = {str(next(iter(g.objects(b, MORK.placeholderName)), "")): next(iter(g.objects(b, MORK.placeholderExpression)), None)
                        for b in g.objects(node, MORK.hasBinding)}
            pieces, at = (), 0
            for match in re.finditer(r"\{([^{}]+)\}", str(template)):
                pieces += (str(template)[at:match.start()],)
                if bindings.get(match.group(1)) is None:
                    raise _Refusal("ExpressionIncomplete", f"{node.n3()} names placeholder {match.group(1)!r} with no binding")
                pieces += self.expression(bindings[match.group(1)], in_iri)
                at = match.end()
            return pieces + (str(template)[at:],)
        if (node, RDF.type, MORK.LookupExpression) in g:
            raise _Refusal("LookupNotCarried", f"{node.n3()} looks a value up in reference data, which a transform does not carry yet")
        raise _Refusal("ExpressionUnknown", f"{node.n3()} is not a template expression the compiler knows")

    def identity(self, spec: Spec) -> Union[Constant, Template, Positional]:
        if spec.individual_iri is not None:
            return Constant(spec.individual_iri)
        if "exact" in spec.strata.abox or "broad" in spec.strata.abox:
            return Constant(self.constant(spec.strata.abox.get("exact") or spec.strata.abox.get("broad"), spec))
        if spec.identity is not None:
            whole = any((spec.identity, RDF.type, k) in self.g for k in (MORK.RefExpression, MORK.LookupExpression))
            return _template(self.expression(spec.identity, not whole))
        if spec.name_template:
            pieces, at = (self.base,), 0
            for match in _PLACEHOLDER.finditer(spec.name_template):
                pieces += (spec.name_template[at:match.start()], Ref(self.path(match.group(1) or match.group(2)), True))
                at = match.end()
            return _template(pieces + (spec.name_template[at:],))
        if spec.concept_name and spec.concept_name.startswith("#"):
            return Constant(URIRef(self.base + spec.concept_name[1:]))
        stem = self.base + (spec.concept_name or local(spec.node)) + "/"
        if spec.data_ref is not None:
            return Template((stem, Ref(spec.data_ref, True)))
        self.findings.append(Finding("PositionalIdentity", str(spec.node), "its identity is its position in the document, which changes when a node is inserted before it. Name a key with mork:dataRef or an identity template", Severity.WARNING))
        return Positional(stem)

    # --- the tree ------------------------------------------------------------------------------------------------------

    def carried(self, spec: Spec) -> None:
        if spec.guard is not None:
            raise _Refusal("GuardNotCarried", "a guard is not carried by a transform yet")

    def datum(self, spec: Spec, root: bool) -> Datum:
        self.carried(spec)
        text = self.mapped_path(spec)
        path = self.path(text) if text is not None else None
        if root and (path is None or not path.absolute):
            raise _Refusal("NoIterator", "a root datum names what it iterates with an absolute mork:path on the concept it is mork:mappingFor")
        if not root and path is not None and path.absolute:
            raise _Refusal("BadPath", f"{text!r}: a child's path starts at its parent's focus")
        glue = None
        if not root:
            prop, inverse = self.property(spec)
            if prop is not None:
                glue = (prop, inverse)
        types = tuple(self.constant(t, spec) for t in (spec.types or ((spec.deferred,) if spec.deferred is not None else ())))
        assertions, children = [], []
        for child in (self.r.specs[c] for c in spec.children if c in self.r.specs):
            try:
                if child.kind in (Kind.DATUM, Kind.CONTEXTUAL):
                    children.append(self.datum(child, False))
                elif child.kind is Kind.ASSERTION:
                    assertions.append(self.assertion(child))
                elif child.kind is Kind.LOOKUP:
                    raise _Refusal("LookupNotCarried", "a lookup in reference data is not carried by a transform yet")
                elif child.kind in (Kind.CLASS_CREATION, Kind.PROPERTY_CREATION):
                    raise _Refusal("CreationNotCarried", "a class or property made from data is not carried by a transform")
            except _Refusal as refusal:
                self.findings.append(Finding(refusal.code, str(child.node), refusal.message))
        return Datum(str(spec.node), path, self.identity(spec), types, glue, tuple(assertions), tuple(children))

    def property(self, spec: Spec) -> tuple[Optional[URIRef], bool]:
        rbox = spec.strata.rbox
        if "exact" in rbox:
            return self.constant(rbox["exact"], spec), False
        if "inverse" in rbox:
            return self.constant(rbox["inverse"], spec), True
        if "broad" in rbox:
            raise _Refusal("CreationNotCarried", "a broad R-Box match creates a property, which a transform does not carry")
        return None, False

    def assertion(self, spec: Spec) -> Assertion:
        self.carried(spec)
        prop, inverse = self.property(spec)
        rows = []
        for child in (self.r.specs.get(c) for c in spec.children):
            if child is not None and child.kind is Kind.CORRESPONDENCE:
                target = child.strata.abox.get("exact") or child.strata.abox.get("broad")
                for source in child.sources:
                    notation = next((self.g.value(source, p) for p in (SKOS.notation, MORK.conceptId, MORK.identifier) if self.g.value(source, p) is not None), None)
                    if notation is None:
                        raise _Refusal("CorrespondenceKey", f"{source.n3()} has no skos:notation, the value the source writes for it")
                    rows.append((str(notation), target))
        if spec.data_ref is not None:
            value = Table(spec.data_ref, tuple(sorted(rows, key=lambda r: (r[0], str(r[1]))))) if rows else Ref(spec.data_ref)
        elif rows:
            raise _Refusal("NoValue", "correspondences translate the values mork:dataRef reads, and this mapping has none")
        elif spec.data_inline is not None:
            value = Constant(spec.data_inline)
        else:
            value = Constant(self.constant(spec.strata.abox.get("exact") or spec.strata.abox.get("broad"), spec))
        return Assertion(str(spec.node), prop, inverse, value)

    def lower(self) -> tuple[Datum, ...]:
        roots = []
        for spec in iter_roots(self.r.specs):
            if spec.node in self.r.templates or spec.kind in (Kind.CLASS_REFERENCE, Kind.CONTEXT, Kind.CORRESPONDENCE):
                continue
            try:
                if spec.kind is not Kind.DATUM:
                    raise _Refusal("CreationNotCarried" if spec.kind in (Kind.CLASS_CREATION, Kind.PROPERTY_CREATION) else "NoParent",
                                   f"a {spec.kind.value} mapping at the root is not carried by a transform")
                roots.append(self.datum(spec, True))
            except _Refusal as refusal:
                self.findings.append(Finding(refusal.code, str(spec.node), refusal.message))
        return tuple(roots)


def _template(pieces: tuple) -> Union[Constant, Template]:
    merged: list = []
    for piece in pieces:
        if isinstance(piece, str) and merged and isinstance(merged[-1], str):
            merged[-1] += piece
        elif piece != "":
            merged.append(piece)
    return Template(tuple(merged))


def plan(g: Graph, scheme: URIRef | str, fmt: str, *, base: str, at: datetime, target_vocabulary: Optional[Graph] = None) -> Plan:
    """The plan of one scheme whose source is `fmt`, "xml" or "json". `at` is the instant the mappings in force are read
    at, an input and never the clock (PRI-56), and `base` the namespace minted IRIs fall under."""
    if fmt not in FORMATS:
        raise ValueError(f"no transform reads {fmt!r}")
    if not re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", base) or not base.endswith(("/", "#")):
        raise ValueError(f"`base` must be an absolute IRI ending in / or #: {base!r}")
    scheme = URIRef(scheme)
    reading = read(g, scheme, at, target_vocabulary, source_format=FORMATS[fmt][0], parse_path=FORMATS[fmt][1])
    lowering = _Lowering(g, reading, fmt, base)
    roots = lowering.lower()
    return Plan(str(scheme), fmt, base, roots, tuple(sorted(set(reading.findings + lowering.findings))))
