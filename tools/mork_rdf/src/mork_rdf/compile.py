# SPDX-License-Identifier: MPL-2.0
"""Compiles a MORK mapping scheme, read by `read`, into SPARQL 1.1 queries over an RDF source (README §6 to §11).

Each mapping node that writes triples gives one CONSTRUCT, whose WHERE clause is the chain of contexts from its root
down to it, and the checks that report the focus nodes it could not map give one SELECT each. Every term is written
from a parsed path or an RDF term, never from a mapping's text (PRI-55)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Optional

import pyoxigraph as ox
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from . import paths
from .guards import GuardError, compile_guard
from .model import (MORK, REFERENCE_GRAPH, SKOS, CompiledMapping, CompiledQuery, CompileError, Finding, Severity, local)
from .read import Kind, Reading, Spec, Yielded, _named, effective_confidence, iter_roots, read, resolve

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

    def named_iri(self, name: str) -> str:
        """The IRI a name gives: `#name` under the base, a prefixed name the scheme declares, an absolute IRI as it is,
        and any other name under the base."""
        if name.startswith("#"):
            return self.base + name[1:]
        prefix, _, rest = name.partition(":")
        if rest and prefix in self.r.prefixes:
            return self.r.prefixes[prefix] + rest
        if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", name):
            return name
        return self.base + name

    def created_iri(self, spec: Spec) -> Optional[str]:
        """The constant IRI a class or property creation names, from `mork:individualIRI` or `mork:conceptName`."""
        if spec.individual_iri is not None:
            return str(spec.individual_iri)
        if spec.concept_name:
            return self.named_iri(spec.concept_name)
        return None

    # --- deferred references (§7.5) ----------------------------------------------------------------------------------

    def term_for(self, term: URIRef, own: Spec, chain: list, patterns: list) -> str:
        """The SPARQL term a match stands for where `own` is compiled in `chain`. A deferred reference resolves to a
        constant IRI, to a name template evaluated over the focus (its patterns appended to `patterns`), or to the
        target of the mapping on the chain whose outcome it yields."""
        found = resolve(self.g, term, own, self.r.specs)
        if found is None:
            return _term(term)
        return self._yielded(found, term, own, chain, patterns)

    def _yielded(self, found: Yielded, term: URIRef, own: Spec, chain: list, patterns: list) -> str:
        if found.name:
            return _term(self.named_iri(found.name))
        if found.template:
            if not chain:
                raise _Refusal("DeferredTemplate", f"{term.n3()} yields a name template, which needs a focus node to read, and {own.node.n3()} has none")
            var = self.var("named")
            patterns.append(f"BIND (IRI({self._name_template(found.template, chain[-1].focus, patterns, [])}) AS {var})")
            return var
        if found.outcome is not None:
            for frame in reversed(chain):
                if frame.spec.node == found.outcome:
                    return frame.target
            m = self.r.specs.get(found.outcome)
            if m is not None and m.kind is Kind.CLASS_REFERENCE:
                return self.term_for(m.strata.tbox["exact"], m, chain, patterns)
            if m is not None and (m.kind in (Kind.CLASS_CREATION, Kind.PROPERTY_CREATION, Kind.CONTEXT)
                                  or m.individual_iri is not None or (m.concept_name or "").startswith("#")):
                named = _named(m)
                if named is not None:
                    return self._yielded(named, term, own, chain, patterns)
            raise _Refusal("DeferredOutcome", f"{term.n3()} yields the outcome of {found.outcome.n3()}, which is not on this mapping's context chain and is no named creation. Join to it with a lookup")
        raise _Refusal("DeferredUnresolved", f"{term.n3()} yields nothing: name it with mork:conceptName or yield a mapping with mork:yieldConcept")

    def guard(self, spec: Spec, focus: str) -> list[str]:
        """The filter a mapping's guard puts on its focus node (§7.7), none when it has no guard."""
        if spec.guard is None:
            return []
        try:
            return [f"FILTER ({compile_guard(self.g, spec.guard, focus, _term, self.var)})"]
        except GuardError as error:
            raise _Refusal("GuardUnsupported", str(error)) from error

    def outputs(self, values: tuple, own: Spec) -> tuple[list[str], list[URIRef]]:
        """The classes `values` name for an axiom: constant terms, and the class creations whose classes are made from
        data, which are known only once those mappings have run."""
        constants, created = [], []
        for value in values:
            found = resolve(self.g, value, own, self.r.specs)
            m = self.r.specs.get(found.outcome) if found is not None and found.outcome is not None else None
            if m is not None and m.kind is Kind.CLASS_CREATION and self.created_iri(m) is None:
                created.append(m.node)
            else:
                constants.append(self.term_for(value, own, [], []))
        return sorted(set(constants)), sorted(set(created), key=str)

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
            frame.target = self.term_for(spec.strata.abox.get("exact") or spec.strata.abox.get("broad"), spec, [frame], frame.identity)
            return
        target = self.var("t")
        if spec.identity is not None:
            # A reference or lookup that is the whole identity is taken as it is, and one inside a concatenation or an
            # interpolation is encoded for an IRI, as RML treats a column and a template (README §6).
            whole = any((spec.identity, RDF.type, k) in self.g for k in (MORK.RefExpression, MORK.LookupExpression))
            expression = self.expression(spec.identity, frame.focus, frame.identity, frame.identity_refs, not whole)
        elif spec.name_template:
            expression = self._name_template(spec.name_template, frame.focus, frame.identity, frame.identity_refs)
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

    def _name_template(self, template: str, focus: str, patterns: list, refs: list) -> str:
        pieces, at = [_string(self.base)], 0
        for match in _PLACEHOLDER.finditer(template):
            if match.start() > at:
                pieces.append(_string(template[at:match.start()]))
            pieces.append(self._ref(match.group(1) or match.group(2), focus, patterns, refs, True))
            at = match.end()
        if at < len(template):
            pieces.append(_string(template[at:]))
        return f"CONCAT({', '.join(pieces)})"

    # --- frames (§5.3) -----------------------------------------------------------------------------------------------

    def root_frame(self, spec: Spec) -> _Frame:
        focus = self.var("f")
        sources = [s for s in spec.sources]
        frame = _Frame(spec, focus, "")
        if not sources:
            # A root that names one individual is made once, from nothing in the source.
            if spec.guard is not None:
                raise _Refusal("GuardUnsupported", "a guard tests a focus node, and a root that names one individual has none")
            self.identity(spec, frame)
            if frame.target.startswith("?") or frame.identity:
                raise _Refusal("NoIterator", "a root datum names the source classes it iterates with mork:mappingFor and mork:representedAs")
            return frame
        if len(sources) == 1:
            frame.match.append(f"{focus} {_term(RDF.type)} {_term(sources[0])} .")
        else:
            kind = self.var("source")
            frame.match.append(f"VALUES {kind} {{ {' '.join(_term(s) for s in sources)} }}")
            frame.match.append(f"{focus} {_term(RDF.type)} {kind} .")
        frame.match += self.guard(spec, focus)
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
        frame.match += self.guard(spec, frame.focus)
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

    def construct(self, chain: list[_Frame], template: list[str], extra: list | None = None, node: Optional[Spec] = None,
                  box: str = "abox", reads: tuple = ()) -> None:
        body = " ".join(template)
        query = f"{self.prologue}CONSTRUCT {{ {body} }}\nWHERE {{\n  {self.where(chain, extra)}\n}}"
        mapping = node or chain[-1].spec
        path = tuple(str(f.spec.node) for f in chain) + ((str(node.node),) if node is not None and node is not chain[-1].spec else ())
        self.queries.append(CompiledQuery(str(mapping.node), path, "construct", None, query, box, tuple(str(r) for r in reads)))

    def tbox(self, spec: Spec, template: str, where: str = "", reads: tuple = (), kind: str = "construct",
             head: Optional[tuple] = None) -> None:
        """A query that writes T-Box triples, once, or once per row of `where`."""
        text = (f"{self.prologue}SELECT DISTINCT ?member\nWHERE {{\n  {where}\n}}\nORDER BY ?member" if kind == "closure"
                else f"{self.prologue}CONSTRUCT {{ {template} }}\nWHERE {{ {where} }}")
        query = CompiledQuery(str(spec.node), (str(spec.node),), kind, None, text, "tbox", tuple(str(r) for r in reads), head=head)
        if query not in self.queries:
            self.queries.append(query)

    def check(self, chain: list[_Frame], code: str, select: str, where: str, tail: str = "", node: Optional[Spec] = None,
              reads: tuple = ()) -> None:
        query = f"{self.prologue}SELECT DISTINCT {select}\nWHERE {{\n  {where}\n}}{tail}"
        mapping = node or chain[-1].spec
        self.queries.append(CompiledQuery(str(mapping.node), tuple(str(f.spec.node) for f in chain) + ((str(node.node),) if node is not None and node is not chain[-1].spec else ()), "check", code, query,
                                          reads=tuple(str(r) for r in reads)))

    # --- the walk ----------------------------------------------------------------------------------------------------

    def compile(self) -> None:
        specs = self.r.specs
        for spec in iter_roots(specs):
            if spec.node in self.r.templates:
                continue
            try:
                if spec.kind is Kind.CLASS_CREATION:
                    self.class_creation(spec)
                elif spec.kind is Kind.PROPERTY_CREATION:
                    self._property(spec)
                elif spec.kind in (Kind.CLASS_REFERENCE, Kind.CONTEXT):
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
        self.stratify()

    def stratify(self) -> None:
        """Each query's stratum: 0 when it reads only the source and reference data, else one more than the last
        stratum of any mapping whose output it reads. A cycle of reads cannot be ordered and refuses the mapping."""
        level: dict[str, int] = {}

        def of(mapping: str, seen: tuple) -> int:
            if mapping in seen:
                raise _Refusal("DeferredCycle", "the mappings read each other's output: " + " > ".join(f"<{m}>" for m in seen + (mapping,)))
            if mapping not in level:
                reads = {r for q in self.queries if q.mapping == mapping for r in q.reads}
                level[mapping] = 1 + max(of(r, seen + (mapping,)) for r in reads) if reads else 0
            return level[mapping]

        out = []
        for q in self.queries:
            try:
                stratum = 1 + max(of(r, (q.mapping,)) for r in q.reads) if q.reads else 0
            except _Refusal as refusal:
                self.findings.append(Finding(refusal.code, q.mapping, refusal.message))
                continue
            out.append(replace(q, stratum=stratum))
        self.queries = sorted(out, key=lambda q: q.stratum)  # stable, so each stratum keeps the walk's order

    def coverage(self) -> None:
        """A check naming each source node typed with a declared `mork:Entity` that no compiled root iterates, because
        its root is absent, dropped or refused (§10.3)."""
        iterated = {s for spec in iter_roots(self.r.specs) if spec.kind in (Kind.DATUM, Kind.CLASS_CREATION) for s in spec.sources}
        uncovered = sorted((e for e in self.g.subjects(RDF.type, MORK.Entity) if isinstance(e, URIRef) and e not in iterated), key=str)
        if uncovered:
            text = (f"{self.prologue}SELECT DISTINCT ?focus ?value\nWHERE {{\n  VALUES ?value {{ {' '.join(_term(e) for e in uncovered)} }}\n"
                    f"  ?focus {_term(RDF.type)} ?value .\n}}")
            self.queries.append(CompiledQuery(str(self.r.scheme), (str(self.r.scheme),), "check", "Uncovered", text))

    def class_creation(self, spec: Spec) -> None:
        iri = self.created_iri(spec)
        if iri is not None:
            broader = [self.term_for(b, spec, [], []) for b in spec.broader]
            self.tbox(spec, f"{_term(iri)} {_term(RDF.type)} {_term(OWL.Class)} ; {_term(RDFS.subClassOf)} {', '.join(broader)} .")
            return
        frame = self.root_frame(spec)
        extra: list = []
        broader = [self.term_for(b, spec, [frame], extra) for b in spec.broader]
        self.construct([frame], [f"{frame.target} {_term(RDF.type)} {_term(OWL.Class)} ; {_term(RDFS.subClassOf)} {', '.join(broader)} ."], extra, box="tbox")
        self.findings.append(Finding("BroadMatch", str(spec.node), f"creates classes beneath {', '.join(b.n3() for b in spec.broader)} from the source's values", Severity.WARNING))

    def datum(self, chain: list[_Frame]) -> None:
        frame = chain[-1]
        spec = frame.spec
        template = []
        for typing in spec.types or ((spec.deferred,) if spec.deferred is not None else ()):
            patterns: list = []
            cls = self.term_for(typing, spec, chain, patterns)
            if patterns:
                # A class named from data types the node in a query of its own, so a focus node without the value
                # the name reads is still made, untyped by that class.
                self.construct(chain, [f"{frame.target} {_term(RDF.type)} {cls} ."], patterns)
            else:
                template.append(f"{frame.target} {_term(RDF.type)} {cls} .")
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
        self.unguarded(chain, spec)

    def unguarded(self, chain: list[_Frame], spec: Spec) -> None:
        """A check naming each node that guarded siblings on one path share and that no guard of theirs admits, since such
        siblings divide their path's nodes, and a node none of them takes is mapped by none (§7.7)."""
        def path_of(child: Spec) -> Optional[str]:
            return next((str(p) for c in sorted(self.g.objects(child.node, MORK.mappingFor), key=str) for p in self.g.objects(c, MORK.path)), None)

        groups: dict = {}
        for child in (self.r.specs[c] for c in spec.children if c in self.r.specs):
            if child.kind in (Kind.DATUM, Kind.CONTEXTUAL):
                groups.setdefault(path_of(child), []).append(child)
        for path_text, siblings in sorted(groups.items(), key=lambda kv: str(kv[0])):
            if len(siblings) < 2 or any(s_.guard is None for s_ in siblings):
                continue
            parent = chain[-1]
            focus, patterns = parent.focus, []
            if path_text is not None:
                focus = self.var("f")
                patterns.append(f"{parent.focus} {paths.write(paths.parse(path_text, self.r.prefixes))} {focus} .")
            try:
                tests = [compile_guard(self.g, s_.guard, focus, _term, self.var) for s_ in siblings]
            except GuardError:
                continue  # each sibling's own refusal says why
            patterns.append(f"FILTER (!({' || '.join(f'({t})' for t in tests)}))")
            self.check(chain, "Unguarded", f"({focus} AS ?focus)", self.where(chain, patterns))

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
            if not any(q.mapping == str(spec.node) and q.box == "tbox" for q in self.queries):
                self.tbox(spec, f"{_term(iri)} {_term(RDFS.subPropertyOf)} {self.term_for(broad, spec, [], [])} .")
                self.axioms(spec, _term(iri))
                self.findings.append(Finding("BroadMatch", str(spec.node), f"asserts a new property beneath {broad.n3()}", Severity.WARNING))
            return _term(iri)
        return self.term_for(spec.strata.rbox.get("exact") or spec.strata.rbox.get("inverse"), spec, [], [])

    def axioms(self, spec: Spec, prop: str) -> None:
        """The domain and range axioms a created property's mapping asks for, in each `mork:axiomForm` it names
        (README §7.6). Classes created from data are known only after their creations run, so an axiom over them is
        written in a later stratum: a global axiom combining them at the closure, a restriction once per class."""
        if not spec.domains and not spec.ranges:
            return
        combination = OWL.unionOf if spec.combination == MORK.UnionOfClasses else OWL.intersectionOf

        def combined(terms: list[str]) -> str:
            return terms[0] if len(terms) == 1 else f"[ {_term(combination)} ( {' '.join(terms)} ) ]"

        domains, domain_data = self.outputs(spec.domains, spec)
        ranges, range_data = self.outputs(spec.ranges, spec)

        def member_query(constants: list[str], created: list[URIRef]) -> str:
            parts = ([f"{{ VALUES ?member {{ {' '.join(constants)} }} }}"] if constants else [])
            parts += [f"{{ GRAPH {_term(m)} {{ ?member {_term(RDF.type)} {_term(OWL.Class)} }} }}" for m in created]
            return " UNION ".join(parts)

        for form in spec.axiom_forms:
            if form == MORK.GlobalAxioms:
                for axiom, constants, created in ((RDFS.domain, domains, domain_data), (RDFS.range, ranges, range_data)):
                    if created:
                        self.tbox(spec, "", member_query(constants, created), tuple(created), "closure", (prop.strip("<>"), str(axiom), str(combination)))
                    elif constants:
                        self.tbox(spec, f"{prop} {_term(axiom)} {combined(constants)} .")
                continue
            restriction = {MORK.UniversalRestriction: OWL.allValuesFrom}.get(form, OWL.someValuesFrom)
            relation = OWL.equivalentClass if form == MORK.DefiningRestriction else RDFS.subClassOf
            if form not in (MORK.UniversalRestriction, MORK.ExistentialRestriction, MORK.DefiningRestriction):
                self.findings.append(Finding("AxiomFormUnknown", str(spec.node), f"{form.n3()} is not an axiom form"))
                continue
            if range_data:
                self.findings.append(Finding("RangeFromData", str(spec.node), "a restriction's range is a class combination, and these classes are made from data. Use mork:GlobalAxioms"))
                continue
            if not domains and not domain_data:
                self.findings.append(Finding("NoDomain", str(spec.node), f"{form.n3()} restricts the domain classes, and the mapping names none"))
                continue
            filler = combined(ranges) if ranges else _term(OWL.Thing)
            body = f"{_term(relation)} [ {_term(RDF.type)} {_term(OWL.Restriction)} ; {_term(OWL.onProperty)} {prop} ; {_term(restriction)} {filler} ] ."
            if combination == OWL.unionOf and form != MORK.DefiningRestriction:
                # (D1 ⊔ D2) ⊑ R holds exactly when D1 ⊑ R and D2 ⊑ R, so each class is restricted on its own.
                for d in domains:
                    self.tbox(spec, f"{d} {body}")
                for m in domain_data:
                    self.tbox(spec, f"?member {body}", f"GRAPH {_term(m)} {{ ?member {_term(RDF.type)} {_term(OWL.Class)} }}", (m,))
            elif domain_data:
                # ponytail: a combined subject over classes made from data needs the closure to write a restriction, not
                # only a list. Add a restriction head to the closure when an author needs it.
                self.findings.append(Finding("CombinationFromData", str(spec.node), f"{form.n3()} over a combination of classes made from data is not compiled. Use mork:UnionOfClasses with a subclass restriction, or mork:GlobalAxioms"))
            else:
                self.tbox(spec, f"{combined(domains)} {body}")

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
        guarded = self.guard(spec, parent.focus)
        rows = []
        for child in spec.children:
            corr = self.r.specs.get(child)
            if corr is not None and corr.kind is Kind.CORRESPONDENCE:
                target = corr.strata.abox.get("exact") or corr.strata.abox.get("broad")
                rows += [(source, target) for source in corr.sources]
                if "broad" in corr.strata.abox and "exact" not in corr.strata.abox:
                    self.findings.append(Finding("BroadMatch", str(corr.node), f"maps to the broader individual {target.n3()}", Severity.WARNING))
        patterns: list[str] = list(guarded)
        if spec.data_ref is not None:
            raw = self.var("v")
            patterns.append(f"{parent.focus} {paths.write(spec.data_ref)} {raw} .")
            value = raw
            if rows:
                value = self.var("mapped")
                table = " ".join(f"({_term(s)} {_term(t)})" for s, t in sorted(rows, key=lambda r: (str(r[0]), str(r[1]))))
                patterns.append(f"VALUES ({raw} {value}) {{ {table} }}")
                where = self.where(chain, guarded + [f"{parent.focus} {paths.write(spec.data_ref)} {raw} .", f"FILTER ({raw} NOT IN ({', '.join(_term(s) for s, _ in sorted(rows, key=lambda r: str(r[0])))}))"])
                self.check(chain, "UnmappedValue", f"({parent.focus} AS ?focus) ({raw} AS ?value)", where, node=spec)
            else:
                self._kind_check(chain, spec, prop_iri, raw, list(patterns))
        elif rows:
            raise _Refusal("NoValue", "correspondences translate the values mork:dataRef reads, and this mapping has none")
        elif spec.data_inline is not None:
            value = _term(spec.data_inline)
        else:
            value = self.term_for(spec.strata.abox.get("exact") or spec.strata.abox.get("broad"), spec, chain, patterns)
            if "broad" in spec.strata.abox and "exact" not in spec.strata.abox:
                self.findings.append(Finding("BroadMatch", str(spec.node), "asserts a broader individual than the source names", Severity.WARNING))
        triple = f"{value} {prop} {parent.target} ." if inverse else f"{parent.target} {prop} {value} ."
        self.construct(chain, [triple], patterns, node=spec)

    def lookup(self, chain: list[_Frame], spec: Spec) -> None:
        """A property whose value is the reference node matching the value `mork:dataRef` reads (README §7.3). The
        reference nodes are the reference data's, or the output of an earlier mapping when the T-Box match yields one."""
        parent = chain[-1]
        prop = self._property(spec)
        inverse = "inverse" in spec.strata.rbox and "exact" not in spec.strata.rbox
        key, found, code = self.var("key"), self.var("found"), self.var("code")
        follow = self.guard(spec, parent.focus) + [f"{parent.focus} {paths.write(spec.data_ref)} {key} ."]
        reference = spec.strata.tbox["exact"]
        yielded = resolve(self.g, reference, spec, self.r.specs)
        reads: tuple = ()
        if yielded is not None and yielded.outcome is not None and not any(f.spec.node == yielded.outcome for f in chain) \
                and (m := self.r.specs.get(yielded.outcome)) is not None and m.kind in (Kind.CLASS_CREATION, Kind.DATUM, Kind.CONTEXTUAL) \
                and not (m.kind is Kind.CLASS_CREATION and self.created_iri(m) is not None):
            # The nodes an earlier mapping made, which the run keeps in a graph named for that mapping (README §12).
            graph, typed, reads = _term(m.node), f"{found} {_term(RDF.type)} {self.var('any')} .", (m.node,)
        else:
            graph, typed = f"<{REFERENCE_GRAPH}>", f"{found} {_term(RDF.type)} {self.term_for(reference, spec, [], [])} ."
        name = spec.lookup_path is None and spec.data_inline is not None
        comparison = spec.comparison
        if name:
            if comparison != MORK.LexicalComparison and (spec.node, MORK.lookupComparison, None) in self.g:
                self.findings.append(Finding("LookupLexical", str(spec.node), "compared lexically, since a match on the reference node's name compares text", Severity.INFO))
            comparison = MORK.LexicalComparison
        elif comparison == MORK.CastComparison and spec.lookup_datatype is None:
            self.findings.append(Finding("LookupLexical", str(spec.node), "compared lexically, since no mork:lookupDatatype names the type to cast to", Severity.INFO))
            comparison = MORK.LexicalComparison
        if name:
            # dataInline "" matches on the reference node's name, its IRI after the last / or #
            match = f"GRAPH {graph} {{ {typed} }} FILTER (REPLACE(STR({found}), \"^.*[/#]\", \"\") = STR({key}))"
        else:
            # on the predicate mork:referenceDataPath names, or else on the reference node's own mork:dataInline
            predicate = _term(spec.lookup_path if spec.lookup_path is not None else MORK.dataInline)
            if comparison == MORK.LexicalComparison:
                match = f"GRAPH {graph} {{ {found} {predicate} {code} . {typed} }} FILTER (STR({code}) = STR({key}))"
            elif comparison == MORK.TermComparison:
                match = f"GRAPH {graph} {{ {found} {predicate} {key} . {typed} }}"
            elif comparison == MORK.CastComparison:
                cast = self.var("cast")
                follow.append(f"BIND (IF(isIRI({key}), {key}, STRDT(STR({key}), {_term(spec.lookup_datatype)})) AS {cast})")
                match = f"GRAPH {graph} {{ {found} {predicate} {cast} . {typed} }}"
            else:
                raise _Refusal("LookupComparisonUnknown", f"{comparison.n3()} is not a lookup comparison")
        triple = f"{found} {prop} {parent.target} ." if inverse else f"{parent.target} {prop} {found} ."
        self.construct(chain, [triple], follow + [match], node=spec, reads=reads)
        self.check(chain, "LookupUnresolved", f"({parent.focus} AS ?focus) ({key} AS ?value)",
                   self.where(chain, follow + [f"FILTER NOT EXISTS {{ {match} }}"]), node=spec, reads=reads)
        self.check(chain, "LookupAmbiguous", f"({parent.focus} AS ?focus) ({key} AS ?value)", self.where(chain, follow + [match]),
                   f"\nGROUP BY {parent.focus} {key}\nHAVING (COUNT(DISTINCT {found}) > 1)", node=spec, reads=reads)


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
