# SPDX-License-Identifier: MPL-2.0
"""Compiles a MORK mapping scheme, read by `read`, into SPARQL 1.1 queries over an RDF source (README §6 to §11).

Each mapping node that writes triples gives one CONSTRUCT, whose WHERE clause is the chain of contexts from its root
down to it, and the checks that report the focus nodes it could not map give one SELECT each. Every term is written
from a parsed path or an RDF term, never from a mapping's text (PRI-55)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import pyoxigraph as ox
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from . import paths
from .model import (MORK, REFERENCE_GRAPH, SKOS, CompiledMapping, CompiledQuery, CompileError, Finding, Severity, local)
from .read import Kind, Reading, Spec, class_of, effective_confidence, iter_roots, read

_PLACEHOLDER = re.compile(r"\$\{([^}]+)\}|\{\$([^}]+)\}")


def _term(value) -> str:
    """An RDF term as SPARQL. A literal is written by rdflib, which escapes it, and an IRI is checked absolute."""
    if isinstance(value, Literal):
        return value.n3()
    return paths.iri(str(value))


def _string(text: str) -> str:
    return Literal(text).n3()


@dataclass
class _Frame:
    """One step of a query's context: the mapping, its focus variable, its target term and what binds them."""

    spec: Spec
    focus: str
    target: str                       # a variable, or a constant IRI written for SPARQL
    match: list = field(default_factory=list)     # the patterns that find the focus node
    identity: list = field(default_factory=list)  # the patterns and BIND that form the target term
    identity_refs: list = field(default_factory=list)  # the paths the identity reads, for the IdentityUnbound check


class _Compiler:
    def __init__(self, g: Graph, reading: Reading, base: str, target_vocabulary: Graph):
        self.g, self.r, self.base, self.vocab = g, reading, base, target_vocabulary
        self.queries: list[CompiledQuery] = []
        self.findings: list[Finding] = []
        self._var = 0
        # A relative IRI an identity forms resolves against the base (SPARQL 1.1 §17.4.2.8).
        self.prologue = f"BASE {paths.iri(base)}\n"

    # --- variables ---------------------------------------------------------------------------------------------------

    def var(self, stem: str) -> str:
        self._var += 1
        return f"?{stem}{self._var}"

    # --- identity (§6) -----------------------------------------------------------------------------------------------

    def created_iri(self, spec: Spec) -> Optional[str]:
        """The constant IRI a class or property creation names, from `mork:individualIRI` or `mork:conceptName`."""
        if spec.individual_iri is not None:
            return str(spec.individual_iri)
        if spec.concept_name:
            name = spec.concept_name[1:] if spec.concept_name.startswith("#") else spec.concept_name
            return self.base + name
        return None

    def expression(self, node, focus: str, patterns: list, refs: list, in_iri: bool) -> str:
        """A template expression as a SPARQL string expression (Foundations §3.9), its patterns appended to `patterns`."""
        g = self.g
        if (node, RDF.type, MORK.LiteralExpression) in g:
            value = next(iter(g.objects(node, MORK.dataInline)), Literal(""))
            return _string(str(value))
        if (node, RDF.type, MORK.RefExpression) in g:
            text = next(iter(g.objects(node, MORK.dataRef)), None)
            if text is None:
                raise _Refusal("ExpressionIncomplete", f"{node.n3()} is a reference with no mork:dataRef")
            return self._ref(str(text), focus, patterns, refs, in_iri)
        if (node, RDF.type, MORK.ConcatExpression) in g:
            left, right = next(iter(g.objects(node, MORK.concatLeft)), None), next(iter(g.objects(node, MORK.concatRight)), None)
            if left is None or right is None:
                raise _Refusal("ExpressionIncomplete", f"{node.n3()} is a concatenation missing an operand")
            return f"CONCAT({self.expression(left, focus, patterns, refs, in_iri)}, {self.expression(right, focus, patterns, refs, in_iri)})"
        if (node, RDF.type, MORK.InterpolationExpression) in g:
            template = next(iter(g.objects(node, MORK.templateString)), None)
            if template is None:
                raise _Refusal("ExpressionIncomplete", f"{node.n3()} is an interpolation with no mork:templateString")
            bindings = {}
            for binding in g.objects(node, MORK.hasBinding):
                name, value = next(iter(g.objects(binding, MORK.placeholderName)), None), next(iter(g.objects(binding, MORK.placeholderExpression)), None)
                if name is None or value is None:
                    raise _Refusal("ExpressionIncomplete", f"{node.n3()} has a binding with no name or expression")
                bindings[str(name)] = value
            pieces, at = [], 0
            for match in re.finditer(r"\{([^{}]+)\}", str(template)):
                if match.start() > at:
                    pieces.append(_string(str(template)[at:match.start()]))
                name = match.group(1)
                if name not in bindings:
                    raise _Refusal("ExpressionIncomplete", f"{node.n3()} names placeholder {name!r} with no binding")
                pieces.append(self.expression(bindings[name], focus, patterns, refs, in_iri))
                at = match.end()
            if at < len(str(template)):
                pieces.append(_string(str(template)[at:]))
            return pieces[0] if len(pieces) == 1 else f"CONCAT({', '.join(pieces)})"
        if (node, RDF.type, MORK.LookupExpression) in g:
            scheme, prop, source = (next(iter(g.objects(node, p)), None) for p in (MORK.lookupScheme, MORK.lookupProperty, MORK.lookupSource))
            if scheme is None or prop is None or source is None:
                raise _Refusal("ExpressionIncomplete", f"{node.n3()} is a lookup missing its scheme, property or source")
            key = self.expression(source, focus, patterns, refs, False)
            concept, code = self.var("lookup"), self.var("code")
            patterns.append(f"GRAPH <{REFERENCE_GRAPH}> {{ {concept} {_term(SKOS.inScheme)} {_term(scheme)} ; {_term(prop)} {code} . }} FILTER (STR({code}) = {key})")
            return f"STR({concept})"
        raise _Refusal("ExpressionUnknown", f"{node.n3()} is not a template expression the compiler knows")

    def _ref(self, text: str, focus: str, patterns: list, refs: list, in_iri: bool) -> str:
        try:
            path = paths.parse(text, self.r.prefixes)
        except paths.PathError as error:
            raise _Refusal("BadPath", str(error)) from error
        value = self.var("v")
        patterns.append(f"{focus} {paths.write(path)} {value} .")
        refs.append(paths.write(path))
        return f"ENCODE_FOR_URI(STR({value}))" if in_iri else f"STR({value})"

    def identity(self, spec: Spec, frame: _Frame) -> None:
        """Sets the frame's target: a constant individual, or a variable bound from the identity rules of README §6."""
        if spec.individual_iri is not None:
            frame.target = _term(spec.individual_iri)
            return
        if "exact" in spec.strata.abox or "broad" in spec.strata.abox:
            frame.target = _term(spec.strata.abox.get("exact") or spec.strata.abox.get("broad"))
            return
        target = self.var("t")
        if spec.identity is not None:
            # A reference or lookup that is the whole identity is taken as it is, and one inside a concatenation or an
            # interpolation is encoded for an IRI, as RML treats a column and a template (README §6).
            whole = any((spec.identity, RDF.type, k) in self.g for k in (MORK.RefExpression, MORK.LookupExpression))
            expression = self.expression(spec.identity, frame.focus, frame.identity, frame.identity_refs, not whole)
        elif spec.name_template:
            expression = self._name_template(spec.name_template, frame)
        elif spec.concept_name and spec.concept_name.startswith("#"):
            frame.target = _term(self.base + spec.concept_name[1:])
            return
        else:
            stem = spec.concept_name or local(spec.node)
            if spec.data_ref is not None:
                key = self._ref(spec.data_ref_text, frame.focus, frame.identity, frame.identity_refs, True)
            else:
                key = f"SHA256(STR({frame.focus}))"
            expression = f"CONCAT({_string(self.base + stem + '/')}, {key})"
        frame.identity.append(f"BIND (IRI({expression}) AS {target})")
        frame.target = target

    def _name_template(self, template: str, frame: _Frame) -> str:
        pieces, at = [_string(self.base)], 0
        for match in _PLACEHOLDER.finditer(template):
            if match.start() > at:
                pieces.append(_string(template[at:match.start()]))
            pieces.append(self._ref(match.group(1) or match.group(2), frame.focus, frame.identity, frame.identity_refs, True))
            at = match.end()
        if at < len(template):
            pieces.append(_string(template[at:]))
        return f"CONCAT({', '.join(pieces)})"

    # --- frames (§5.3) -----------------------------------------------------------------------------------------------

    def root_frame(self, spec: Spec) -> _Frame:
        focus = self.var("f")
        sources = [s for s in spec.sources]
        if not sources:
            raise _Refusal("NoIterator", "a root datum names the source classes it iterates with mork:mappingFor and mork:representedAs")
        frame = _Frame(spec, focus, "")
        if len(sources) == 1:
            frame.match.append(f"{focus} {_term(RDF.type)} {_term(sources[0])} .")
        else:
            kind = self.var("source")
            frame.match.append(f"VALUES {kind} {{ {' '.join(_term(s) for s in sources)} }}")
            frame.match.append(f"{focus} {_term(RDF.type)} {kind} .")
        for concept in self.g.objects(spec.node, MORK.mappingFor):
            if next(iter(self.g.objects(concept, MORK.path)), None) is not None:
                self.findings.append(Finding("RootPathIgnored", str(spec.node), "a root iterates its source classes, so its concept's mork:path is not read", Severity.WARNING))
        self.identity(spec, frame)
        return frame

    def child_frame(self, spec: Spec, parent: _Frame) -> _Frame:
        """A contextual datum's frame: the parent's focus, followed along its concept's `mork:path` when it names one."""
        path_text = next((str(p) for c in sorted(self.g.objects(spec.node, MORK.mappingFor), key=str) for p in self.g.objects(c, MORK.path)), None)
        frame = _Frame(spec, parent.focus, "")
        if path_text is not None:
            try:
                path = paths.parse(path_text, self.r.prefixes)
            except paths.PathError as error:
                raise _Refusal("BadPath", str(error)) from error
            frame.focus = self.var("f")
            frame.match.append(f"{parent.focus} {paths.write(path)} {frame.focus} .")
        self.identity(spec, frame)
        return frame

    @staticmethod
    def where(chain: list[_Frame], extra: list | None = None, *, last_identity: bool = True) -> str:
        lines = []
        for i, frame in enumerate(chain):
            lines += frame.match
            if last_identity or i < len(chain) - 1:
                lines += frame.identity
        lines += extra or []
        return "\n  ".join(lines)

    # --- emitting ----------------------------------------------------------------------------------------------------

    def emit(self, chain: list[_Frame], kind: str, text: str, code: Optional[str] = None) -> None:
        spec = chain[-1].spec
        self.queries.append(CompiledQuery(str(spec.node), tuple(str(f.spec.node) for f in chain), kind, code, text))

    def construct(self, chain: list[_Frame], template: list[str], extra: list | None = None, node: Optional[Spec] = None) -> None:
        body = " ".join(template)
        query = f"{self.prologue}CONSTRUCT {{ {body} }}\nWHERE {{\n  {self.where(chain, extra)}\n}}"
        if node is not None and node is not chain[-1].spec:
            self.queries.append(CompiledQuery(str(node.node), tuple(str(f.spec.node) for f in chain) + (str(node.node),), "construct", None, query))
        else:
            self.emit(chain, "construct", query)

    def check(self, chain: list[_Frame], code: str, select: str, where: str, tail: str = "", node: Optional[Spec] = None) -> None:
        query = f"{self.prologue}SELECT DISTINCT {select}\nWHERE {{\n  {where}\n}}{tail}"
        mapping = node or chain[-1].spec
        self.queries.append(CompiledQuery(str(mapping.node), tuple(str(f.spec.node) for f in chain) + ((str(node.node),) if node is not None and node is not chain[-1].spec else ()), "check", code, query))

    # --- the walk ----------------------------------------------------------------------------------------------------

    def compile(self) -> None:
        specs = self.r.specs
        for spec in iter_roots(specs):
            if spec.node in self.r.templates:
                continue
            try:
                if spec.kind is Kind.CLASS_CREATION:
                    self.class_creation(spec)
                elif spec.kind is Kind.CLASS_REFERENCE:
                    continue
                elif spec.kind is Kind.DATUM:
                    frame = self.root_frame(spec)
                    self.datum([frame])
                elif spec.kind is Kind.CORRESPONDENCE:
                    continue
                else:
                    raise _Refusal("NoParent", f"a {spec.kind.value} mapping needs a parent")
            except _Refusal as refusal:
                self.findings.append(Finding(refusal.code, str(spec.node), refusal.message))
        self.coverage()

    def coverage(self) -> None:
        """A check naming each source node typed with a declared `mork:Entity` that no compiled root iterates, because
        its root is absent, dropped or refused (§10.3)."""
        iterated = {s for spec in iter_roots(self.r.specs) if spec.kind is Kind.DATUM for s in spec.sources}
        uncovered = sorted((e for e in self.g.subjects(RDF.type, MORK.Entity) if isinstance(e, URIRef) and e not in iterated), key=str)
        if uncovered:
            text = (f"{self.prologue}SELECT DISTINCT ?focus ?value\nWHERE {{\n  VALUES ?value {{ {' '.join(_term(e) for e in uncovered)} }}\n"
                    f"  ?focus {_term(RDF.type)} ?value .\n}}")
            self.queries.append(CompiledQuery(str(self.r.scheme), (str(self.r.scheme),), "check", "Uncovered", text))

    def class_creation(self, spec: Spec) -> None:
        broad = spec.strata.tbox["broad"]
        iri = self.created_iri(spec)
        if iri is not None:
            text = f"{self.prologue}CONSTRUCT {{ {_term(iri)} {_term(RDF.type)} {_term(OWL.Class)} ; {_term(RDFS.subClassOf)} {_term(broad)} . }}\nWHERE {{ }}"
            self.queries.append(CompiledQuery(str(spec.node), (str(spec.node),), "construct", None, text))
            return
        frame = self.root_frame(spec)
        self.construct([frame], [f"{frame.target} {_term(RDF.type)} {_term(OWL.Class)} ; {_term(RDFS.subClassOf)} {_term(broad)} ."])
        self.findings.append(Finding("BroadMatch", str(spec.node), f"creates classes beneath {broad.n3()} from the source's values", Severity.WARNING))

    def datum(self, chain: list[_Frame]) -> None:
        frame = chain[-1]
        spec = frame.spec
        template = []
        cls = class_of(self.g, spec, self.r.specs)
        if cls == URIRef("urn:mork-rdf:created"):
            created = self.r.specs[spec.deferred]
            iri = self.created_iri(created)
            if iri is None:
                raise _Refusal("TemplatedClassAsType", f"defers to {created.node.n3()}, which creates classes from data, so no one class types its nodes")
            cls = URIRef(iri)
        if cls is not None:
            template.append(f"{frame.target} {_term(RDF.type)} {_term(cls)} .")
        if len(chain) > 1:
            glue = spec.strata.rbox.get("exact") or spec.strata.rbox.get("inverse") or spec.strata.rbox.get("broad")
            if glue is not None:
                prop = self._property(spec)
                parent = chain[-2].target
                template.append(f"{parent} {prop} {frame.target} ." if "inverse" in spec.strata.rbox and "exact" not in spec.strata.rbox else f"{frame.target} {prop} {parent} .")
        if template:
            self.construct(chain, template)
        if frame.identity_refs:
            refs = " ".join(f"{frame.focus} {r} ?any_{i} ." for i, r in enumerate(frame.identity_refs))
            self.check(chain, "IdentityUnbound", f"({frame.focus} AS ?focus)", self.where(chain, [f"FILTER NOT EXISTS {{ {refs} }}"], last_identity=False))
            if frame.target.startswith("?"):
                self.check(chain, "IdentityAmbiguous", f"({frame.focus} AS ?focus)", self.where(chain), f"\nGROUP BY {frame.focus}\nHAVING (COUNT(DISTINCT {frame.target}) > 1)")
        for child in spec.children:
            if child not in self.r.specs:
                continue
            self.child(chain, self.r.specs[child])

    def child(self, chain: list[_Frame], spec: Spec) -> None:
        try:
            if spec.kind in (Kind.CONTEXTUAL, Kind.DATUM):
                self.datum(chain + [self.child_frame(spec, chain[-1])])
            elif spec.kind is Kind.ASSERTION:
                self.assertion(chain, spec)
            elif spec.kind is Kind.LOOKUP:
                self.lookup(chain, spec)
            elif spec.kind is Kind.CLASS_CREATION:
                self.class_creation(spec)
        except _Refusal as refusal:
            self.findings.append(Finding(refusal.code, str(spec.node), refusal.message))

    def _property(self, spec: Spec) -> str:
        """The property a mapping asserts, creating a subproperty for a broad R-Box match."""
        if "broad" in spec.strata.rbox and "exact" not in spec.strata.rbox and "inverse" not in spec.strata.rbox:
            iri = self.created_iri(spec)
            if iri is None:
                raise _Refusal("NoName", "a broad R-Box match creates a property, which needs mork:conceptName or mork:individualIRI")
            broad = spec.strata.rbox["broad"]
            text = f"{self.prologue}CONSTRUCT {{ {_term(iri)} {_term(RDFS.subPropertyOf)} {_term(broad)} . }}\nWHERE {{ }}"
            created = CompiledQuery(str(spec.node), (str(spec.node),), "construct", None, text)
            if created not in self.queries:
                self.queries.append(created)
                self.findings.append(Finding("BroadMatch", str(spec.node), f"asserts a new property beneath {broad.n3()}", Severity.WARNING))
            return _term(iri)
        return _term(spec.strata.rbox.get("exact") or spec.strata.rbox.get("inverse"))

    def _kind_check(self, chain: list[_Frame], spec: Spec, prop_iri: Optional[URIRef], value: str, patterns: list) -> None:
        if prop_iri is None:
            return
        types = set(self.vocab.objects(prop_iri, RDF.type))
        test = "isLiteral" if OWL.ObjectProperty in types else "!isLiteral" if OWL.DatatypeProperty in types else None
        if test is not None:
            self.check(chain, "TermKind", f"({chain[-1].focus} AS ?focus) ({value} AS ?value)", self.where(chain, patterns + [f"FILTER ({test}({value}))"]), node=spec)

    def assertion(self, chain: list[_Frame], spec: Spec) -> None:
        parent = chain[-1]
        prop = self._property(spec)
        prop_iri = spec.strata.rbox.get("exact") or spec.strata.rbox.get("inverse")
        inverse = "inverse" in spec.strata.rbox and "exact" not in spec.strata.rbox
        rows = []
        for child in spec.children:
            corr = self.r.specs.get(child)
            if corr is not None and corr.kind is Kind.CORRESPONDENCE:
                target = corr.strata.abox.get("exact") or corr.strata.abox.get("broad")
                rows += [(source, target) for source in corr.sources]
                if "broad" in corr.strata.abox and "exact" not in corr.strata.abox:
                    self.findings.append(Finding("BroadMatch", str(corr.node), f"maps to the broader individual {target.n3()}", Severity.WARNING))
        patterns: list[str] = []
        if spec.data_ref is not None:
            raw = self.var("v")
            patterns.append(f"{parent.focus} {paths.write(spec.data_ref)} {raw} .")
            value = raw
            if rows:
                value = self.var("mapped")
                table = " ".join(f"({_term(s)} {_term(t)})" for s, t in sorted(rows, key=lambda r: (str(r[0]), str(r[1]))))
                patterns.append(f"VALUES ({raw} {value}) {{ {table} }}")
                where = self.where(chain, [f"{parent.focus} {paths.write(spec.data_ref)} {raw} .", f"FILTER ({raw} NOT IN ({', '.join(_term(s) for s, _ in sorted(rows, key=lambda r: str(r[0])))}))"])
                self.check(chain, "UnmappedValue", f"({parent.focus} AS ?focus) ({raw} AS ?value)", where, node=spec)
            else:
                self._kind_check(chain, spec, prop_iri, raw, list(patterns))
        elif rows:
            raise _Refusal("NoValue", "correspondences translate the values mork:dataRef reads, and this mapping has none")
        elif spec.data_inline is not None:
            value = _term(spec.data_inline)
        else:
            value = _term(spec.strata.abox.get("exact") or spec.strata.abox.get("broad"))
            if "broad" in spec.strata.abox and "exact" not in spec.strata.abox:
                self.findings.append(Finding("BroadMatch", str(spec.node), "asserts a broader individual than the source names", Severity.WARNING))
        triple = f"{value} {prop} {parent.target} ." if inverse else f"{parent.target} {prop} {value} ."
        self.construct(chain, [triple], patterns, node=spec)

    def lookup(self, chain: list[_Frame], spec: Spec) -> None:
        parent = chain[-1]
        prop = self._property(spec)
        inverse = "inverse" in spec.strata.rbox and "exact" not in spec.strata.rbox
        key, found, code = self.var("key"), self.var("found"), self.var("code")
        follow = f"{parent.focus} {paths.write(spec.data_ref)} {key} ."
        typed = f"{found} {_term(RDF.type)} {_term(spec.strata.tbox['exact'])} ."
        if spec.lookup_path is None and spec.data_inline is not None:
            # dataInline "" matches on the reference individual's name, its IRI after the last / or #
            match = f"GRAPH <{REFERENCE_GRAPH}> {{ {typed} }} FILTER (REPLACE(STR({found}), \"^.*[/#]\", \"\") = STR({key}))"
        else:
            # on the predicate mork:referenceDataPath names, or else on the reference individual's own mork:dataInline
            predicate = spec.lookup_path if spec.lookup_path is not None else MORK.dataInline
            match = f"GRAPH <{REFERENCE_GRAPH}> {{ {found} {_term(predicate)} {code} . {typed} }} FILTER (STR({code}) = STR({key}))"
        triple = f"{found} {prop} {parent.target} ." if inverse else f"{parent.target} {prop} {found} ."
        self.construct(chain, [triple], [follow, match], node=spec)
        self.check(chain, "LookupUnresolved", f"({parent.focus} AS ?focus) ({key} AS ?value)",
                   self.where(chain, [follow, f"FILTER NOT EXISTS {{ {match} }}"]), node=spec)
        self.check(chain, "LookupAmbiguous", f"({parent.focus} AS ?focus) ({key} AS ?value)", self.where(chain, [follow, match]),
                   f"\nGROUP BY {parent.focus} {key}\nHAVING (COUNT(DISTINCT {found}) > 1)", node=spec)


class _Refusal(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def digest(g: Graph) -> str:
    """SHA-256 of the graph's RDFC-1.0 canonical N-Quads, in lowercase hex (ADR-A143)."""
    import hashlib

    dataset = ox.Dataset(ox.Quad(t.subject, t.predicate, t.object) for t in ox.parse(g.serialize(format="nt"), format=ox.RdfFormat.N_TRIPLES))
    dataset.canonicalize(ox.CanonicalizationAlgorithm.RDFC_1_0)
    lines = sorted(str(q) + " .\n" for q in dataset)
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def compile_scheme(
    g: Graph,
    scheme: URIRef | str,
    *,
    base: str,
    at: datetime,
    target_vocabulary: Optional[Graph] = None,
    shapes: Optional["MorkLayer"] = None,
    min_confidence: Optional[float] = None,
) -> CompiledMapping:
    """Compiles one mapping scheme of `g` for an RDF source (README §4).

    `base` is the namespace minted IRIs fall under, `at` the instant the mappings in force are read at, which is an
    input and never the clock (PRI-56), and `target_vocabulary` types the target terms, for generic matches and the
    term-kind checks. `shapes` validates the graph against MORK's own shapes first, `layer.load()` by default. In
    production mode any error refuses the whole compilation with `CompileError`."""
    from .layer import load, validate

    if at.tzinfo is None:
        raise CompileError("`at` needs a timezone")
    if not re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", base) or not base.endswith(("/", "#")):
        raise CompileError(f"`base` must be an absolute IRI ending in / or #: {base!r}")
    scheme = URIRef(scheme)
    vocab = target_vocabulary if target_vocabulary is not None else Graph()
    shape_findings = validate(g, shapes if shapes is not None else load())
    reading = read(g, scheme, at, vocab, min_confidence)
    compiler = _Compiler(g, reading, base, vocab)
    compiler.compile()
    findings = tuple(sorted(set(shape_findings + reading.findings + compiler.findings)))
    confidence = effective_confidence(reading.specs)
    compiled = CompiledMapping(
        scheme=str(scheme),
        mapping_digest=digest(g),
        at=at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        base=base,
        mode=reading.mode,
        queries=tuple(compiler.queries),
        findings=findings,
        confidence=tuple(sorted((str(k), round(v, 6)) for k, v in confidence.items())),
    )
    if reading.mode == "production" and compiled.errors:
        raise CompileError(f"{len(compiled.errors)} error(s) in a production scheme", compiled.findings)
    return compiled
