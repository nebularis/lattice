# SPDX-License-Identifier: MPL-2.0
"""The check a proposing agent runs on its proposal before a person reviews it: decode the MCN with the reference
decoder, validate the graph against MORK's shapes, compile each mapping scheme it holds with `tools/mork_rdf`, and,
given a sample source, run it and validate what it wrote against the target layers' shapes, each result reported on the
mapping that wrote its focus node. Every failure is a finding the agent can act on, never an exception."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from rdflib import Graph
from rdflib.namespace import RDF

MORK_NS = "http://www.nebularis.org/ontologies/Mork#"


@dataclass
class Checked:
    graph: Optional[Graph]
    findings: list = field(default_factory=list)   # (stage, severity, code, about, message)
    schemes: list = field(default_factory=list)    # (scheme, queries, strata)
    output: Optional[Graph] = None

    def summary(self) -> dict:
        return {
            "decoded": self.graph is not None,
            "triples": len(self.graph) if self.graph is not None else 0,
            "schemes": [{"scheme": s, "queries": q, "strata": n} for s, q, n in self.schemes],
            "findings": [{"stage": st, "severity": sv, "code": c, "about": a, "message": m} for st, sv, c, a, m in self.findings],
            "errors": sum(1 for f in self.findings if f[1] == "error"),
            "output_triples": len(self.output) if self.output is not None else None,
        }


def check(mcn: str, *, base: str = "urn:mork-propose:out/", at: Optional[datetime] = None,
          sample: Optional[Graph] = None, target_vocabulary: Optional[Graph] = None, target_shapes: Optional[Graph] = None) -> Checked:
    """`at` is the instant the mappings in force are read at, an input and never the clock (PRI-56), the epoch of the
    proposal when none is given."""
    import mcn_decoder
    from mork_rdf import CompileError, compile_scheme, run

    at = at or datetime(2000, 1, 1, tzinfo=timezone.utc)
    try:
        g = mcn_decoder.decode(mcn)
    except mcn_decoder.McnSyntaxError as error:
        return Checked(None, [("decode", "error", getattr(error, "code", "syntax"), f"line {getattr(error, 'line_no', '?')}", str(error))])
    return check_graph(g, base=base, at=at, sample=sample, target_vocabulary=target_vocabulary, target_shapes=target_shapes)


TARGETS = ("exactTBoxMatch", "exactRBoxMatch", "inverseRBoxMatch", "exactABoxMatch")


# RDF's own vocabularies, whose terms a layer may mention without declaring them all.
META = {"http://www.w3.org/1999/02/22-rdf-syntax-ns#", "http://www.w3.org/2000/01/rdf-schema#", "http://www.w3.org/2002/07/owl#",
        "http://www.w3.org/2001/XMLSchema#"}


def _namespace(iri: str) -> str:
    return iri[: max(iri.rfind("#"), iri.rfind("/")) + 1]


def unknown_targets(g: Graph, vocabulary: Graph) -> list:
    """A target term in a namespace the target vocabulary declares terms in, which it does not declare, such as a
    misspelt class. A term of any other namespace, such as RDF's own or a source's, is left alone."""
    from rdflib import URIRef

    declared = {s for s in vocabulary.subjects() if isinstance(s, URIRef)}
    namespaces = {_namespace(str(s)) for s in declared} - META
    out = []
    for name in TARGETS:
        for mapping, term in sorted(g.subject_objects(URIRef(MORK_NS + name)), key=str):
            if isinstance(term, URIRef) and term not in declared and _namespace(str(term)) in namespaces:
                out.append(("validate", "error", "UnknownTarget", mapping, f"mork:{name} names {term}, which the target vocabulary does not declare"))
    return out


class _Recorder:
    """A run's sink that keeps every triple and which mapping wrote it."""

    def __init__(self) -> None:
        self.triples: set = set()
        self.typed_by: dict = {}

    def write(self, query, triples) -> None:
        for t in triples:
            self.triples.add(t)
            if t.predicate.value == str(RDF.type):
                self.typed_by.setdefault(t.subject.value, query.mapping)

    def close(self) -> None:
        pass

    def graph(self) -> Graph:
        import pyoxigraph as ox

        out = Graph()
        if self.triples:
            out.parse(data=ox.serialize(sorted(self.triples, key=str), format=ox.RdfFormat.N_TRIPLES).decode("utf-8"), format="nt")
        return out


_LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
# What a mapping cannot write, since it is supplied where the meaning is written: by the result path, or by the shape.
# ponytail: ins:TermShape is downgraded whole, so a term missing ins:Template is information too. Supplying the clause
# as context before validating would keep the rest of the shape an error.
_CONTEXT = {
    _LATTICE + "foundation#hasIdentity": "identity is minted when the meaning is persisted, not by a mapping",
    # Foundation's shape for a versioned thing states the identity rule as a node-level sh:or, which has no result path.
    _LATTICE + "foundation#VersionedShape": "identity is minted when the meaning is persisted, not by a mapping",
    _LATTICE + "instrument#TermShape": "a stated term's clause is chosen where the meaning is written, such as at an import",
}


def meaning_findings(output: Graph, typed_by: dict, vocabulary: Graph, shapes: Graph) -> list:
    """What the target layers' shapes say of a run's output, each on the mapping that typed its focus node, read with
    OWL RL entailment as a reasoner would. A result about a node the run did not type, such as one of the vocabulary's
    own, is not the proposal's and is left out, and one about what the context supplies (`_CONTEXT`) is information."""
    import pyshacl
    from rdflib.namespace import SH

    _, report, _ = pyshacl.validate(output + vocabulary, shacl_graph=shapes, inference="owlrl", advanced=True, allow_warnings=True)
    severity = {SH.Violation: "error", SH.Warning: "warning"}
    out = set()
    for r in report.subjects(RDF.type, SH.ValidationResult):
        focus = report.value(r, SH.focusNode)
        if str(focus) not in typed_by:
            continue
        message = " ".join(str(report.value(r, SH.resultMessage) or "a shape of the target layers is not met").split())
        context = _CONTEXT.get(str(report.value(r, SH.resultPath))) or _CONTEXT.get(str(report.value(r, SH.sourceShape)))
        if context:
            out.add(("meaning", "info", "ContextShape", typed_by[str(focus)], f"{message} Left to the context: {context}. (on {focus})"))
        else:
            out.add(("meaning", severity.get(report.value(r, SH.resultSeverity), "info"), "TargetShape", typed_by[str(focus)],
                     f"{message} (on {focus})"))
    return sorted(out, key=lambda f: (f[3] or "", f[4]))


def check_graph(g: Graph, *, base: str = "urn:mork-propose:out/", at: Optional[datetime] = None,
                sample: Optional[Graph] = None, target_vocabulary: Optional[Graph] = None, compiled_out: Optional[list] = None,
                target_shapes: Optional[Graph] = None) -> Checked:
    """The check of a mapping graph already decoded or parsed, such as the LangGraph pipeline's Turtle. Each compiled
    mapping is appended to `compiled_out` when it is given. With a sample and `target_shapes`, what the run writes is
    validated against them, read with `target_vocabulary`."""
    from mork_rdf import CompileError, compile_scheme, run

    at = at or datetime(2000, 1, 1, tzinfo=timezone.utc)
    result = Checked(g)
    schemes = sorted(g.subjects(RDF.type, __import__("rdflib").URIRef(MORK_NS + "MappingScheme")), key=str)
    if not schemes:
        result.findings.append(("compile", "error", "NoScheme", None, "the proposal declares no mork:MappingScheme, so nothing compiles"))
    if target_vocabulary is not None:
        result.findings.extend(unknown_targets(g, target_vocabulary))
    for scheme in schemes:
        try:
            compiled = compile_scheme(g, scheme, base=base, at=at, target_vocabulary=target_vocabulary)
        except CompileError as error:
            for f in error.findings:
                result.findings.append(("compile", f.severity.value, f.code, f.mapping, f.message))
            continue
        result.schemes.append((str(scheme), len(compiled.queries), compiled.strata))
        if compiled_out is not None:
            compiled_out.append(compiled)
        for f in compiled.findings:
            # An uncertain mapping is never compiled, which in a proposal is what it is for: a question a reviewer
            # answers. So the check reports it for review and never counts it an error.
            severity = "review" if f.code == "Uncertain" else f.severity.value
            result.findings.append(("validate" if f.code == "MorkShape" else "compile", severity, f.code, f.mapping, f.message))
        if sample is not None:
            recorder = _Recorder()
            ran = run(compiled, sample, sink=recorder)
            written = recorder.graph()
            result.output = (result.output or Graph()) + written
            for f in ran.findings:
                result.findings.append(("run", f.severity.value, f.code, f.focus, f"{f.message} ({f.value})" if f.value else f.message))
            if target_shapes is not None:
                result.findings.extend(meaning_findings(written, recorder.typed_by, target_vocabulary or Graph(), target_shapes))
    return result
