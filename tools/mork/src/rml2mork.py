# SPDX-License-Identifier: MPL-2.0
"""RML to MORK: an RML mapping read into a MORK mapping scheme, so a mapping written for an RML engine is viewed, edited and
reviewed in the studio's mapping mode, and compiled back with `mork2rml`.

Each logical source becomes a `mork:DataConcept` with its iterator as its path, in a `mork:RepresentationScheme` for its
source file and reference formulation. Each triples map becomes a `mork:Datum` for that concept: its subject map's class is
a class mapping it defers to, and a template `{base}{Name}/{ref}` its concept name and data reference, as `mork2rml` writes them. Each
predicate-object map becomes a `mork:DataMapping` beneath it, with its predicate as R-Box match and its object map's
reference, constant or class. A predicate-object map whose object is another triples map's subject makes that triples
map's datum a child of this one, glued by an inverse R-Box match, the parent writing the link. A triples map that names
the mapping it came from with `rdfs:isDefinedBy`, as `mork2rml` writes, keeps that mapping's IRI.

What MORK cannot say here is reported, never dropped silently: a template of another shape, a function, a graph map, a
language or datatype map, and a join whose condition is not the nesting. `read` returns the scheme and those findings."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

MORK = Namespace("http://www.nebularis.org/ontologies/Mork#")
RR = Namespace("http://www.w3.org/ns/r2rml#")
RML = Namespace("http://semweb.mmlab.be/ns/rml#")
QL = Namespace("http://semweb.mmlab.be/ns/ql#")
FNML = Namespace("http://semweb.mmlab.be/ns/fnml#")
FORMATS = {QL.JSONPath: MORK.JSON, QL.XPath: MORK.XML, QL.CSV: MORK.CSV}
_TEMPLATE = re.compile(r"^(?P<base>.*/)(?P<name>[^/{}]+)/\{(?P<ref>[^{}]+)\}$")


@dataclass
class Read:
    graph: Graph
    scheme: URIRef
    findings: list[str] = field(default_factory=list)


def _local(node) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(node).rstrip("/#").rsplit("#", 1)[-1].rsplit("/", 1)[-1]) or "x"


def template_base(rml: Graph) -> str | None:
    """The base the subject templates share, which `mork2rml` mints them under again, or None where they share none."""
    bases = {m["base"] for t in rml.objects(None, RR.template) if (m := _TEMPLATE.match(str(t)))}
    return bases.pop() if len(bases) == 1 else None


def read(rml: Graph, base: str) -> Read:
    """The MORK scheme an RML mapping says, under `base`, which ends in # or /."""
    out = Graph()
    out.bind("mork", MORK)
    scheme = URIRef(base + "Scheme")
    out.add((scheme, RDF.type, MORK.MappingScheme))
    out.add((scheme, RDFS.label, Literal("Read from an RML mapping")))
    result = Read(out, scheme)
    maps = sorted(set(rml.subjects(RDF.type, RR.TriplesMap)) | set(rml.subjects(RML.logicalSource, None)), key=str)
    datum = {tm: (rml.value(tm, RDFS.isDefinedBy) or URIRef(base + "Map_" + _local(tm))) for tm in maps}
    sources: dict = {}

    def concept(tm) -> URIRef:
        ls = rml.value(tm, RML.logicalSource)
        source, formulation, iterator = (rml.value(ls, RML.source), rml.value(ls, RML.referenceFormulation), rml.value(ls, RML.iterator)) if ls else (None, None, None)
        key = (str(source), str(formulation))
        if key not in sources:
            rep = URIRef(f"{base}Source_{len(sources) + 1}")
            out.add((rep, RDF.type, MORK.RepresentationScheme))
            if formulation in FORMATS:
                out.add((rep, MORK["format"], FORMATS[formulation]))
            elif formulation is not None:
                result.findings.append(f"{_local(tm)}: the reference formulation {formulation} has no MORK format")
            if source is not None:
                out.add((rep, MORK.identifier, Literal(str(source))))
            sources[key] = rep
        c = URIRef(f"{base}Concept_{_local(tm)}")
        out.add((c, RDF.type, MORK.DataConcept))
        out.add((c, MORK.conceptScheme, scheme))
        out.add((c, MORK.representationScheme, sources[key]))
        if iterator is not None:
            out.add((c, MORK.path, Literal(str(iterator))))
        return c

    # A triples map another one's object names is that one's child, glued by the predicate that names it.
    parent_of: dict = {}
    for tm in maps:
        for pom in rml.objects(tm, RR.predicateObjectMap):
            for om in rml.objects(pom, RR.objectMap):
                child = rml.value(om, RR.parentTriplesMap)
                if child is not None and child in datum:
                    parent_of[child] = (tm, rml.value(pom, RR.predicate))

    for tm in maps:
        m = datum[tm]
        out.add((m, RDF.type, MORK.DataMapping))
        out.add((m, RDF.type, MORK.Datum))
        out.add((m, MORK.mappingScheme, scheme))
        if tm in parent_of:
            parent, predicate = parent_of[tm]
            out.add((m, MORK.compositeBroaderMapping, datum[parent]))
            out.add((m, MORK.broaderApplicative, datum[parent]))  # mork2rml writes the join from it
            if predicate is not None:
                out.add((m, MORK.inverseRBoxMatch, predicate))
        else:
            out.add((m, MORK.mappingFor, concept(tm)))
        sm = rml.value(tm, RR.subjectMap)
        # A subject's class is a class mapping the datum defers to, which mork2rml and mork_rdf both read (README §7.5).
        for k, cls in enumerate(sorted(rml.objects(sm, RR["class"]), key=str) if sm is not None else ()):
            class_mapping = URIRef(f"{m}_Class" + (f"_{k}" if k else ""))
            out.add((class_mapping, RDF.type, MORK.DataMapping))
            out.add((class_mapping, MORK.mappingScheme, scheme))
            out.add((class_mapping, MORK.exactTBoxMatch, cls))
            out.add((m, MORK.deferredMapping, class_mapping))
        template = rml.value(sm, RR.template) if sm is not None else None
        reference = rml.value(sm, RML.reference) if sm is not None else None
        if template is not None:
            shaped = _TEMPLATE.match(str(template))
            if shaped:
                out.add((m, MORK.conceptName, Literal(shaped["name"])))
                out.add((m, MORK.dataRef, Literal(shaped["ref"])))
            else:
                result.findings.append(f"{_local(tm)}: the subject template {template} is not of the form base/Name/{{reference}}, so its name is left out")
        elif reference is not None:
            out.add((m, MORK.dataRef, Literal(str(reference))))
        for unsupported, what in ((RR.graphMap, "a graph map"), (RR.graph, "a graph")):
            if sm is not None and rml.value(sm, unsupported) is not None:
                result.findings.append(f"{_local(tm)}: {what} on the subject is not read")

        for n, pom in enumerate(sorted(rml.objects(tm, RR.predicateObjectMap), key=lambda p: (str(rml.value(p, RR.predicate)), str(p)))):
            predicate = rml.value(pom, RR.predicate)
            for om in rml.objects(pom, RR.objectMap):
                if rml.value(om, RR.parentTriplesMap) is not None:
                    join = rml.value(om, RR.joinCondition)
                    if join is not None and rml.value(join, RR.child) != rml.value(join, RR.parent):
                        result.findings.append(f"{_local(tm)}: a join on {rml.value(join, RR.child)} = {rml.value(join, RR.parent)} is read as nesting")
                    continue
                child = URIRef(f"{m}_{_local(predicate)}" + (f"_{n}" if n and (URIRef(f"{m}_{_local(predicate)}"), None, None) in out else ""))
                out.add((child, RDF.type, MORK.DataMapping))
                out.add((child, MORK.mappingScheme, scheme))
                out.add((child, MORK.compositeBroaderMapping, m))
                out.add((m, MORK.compositeNarrowerMapping, child))  # mork2rml gathers a map's predicate-object maps by it
                if predicate is not None:
                    out.add((child, MORK.exactRBoxMatch, predicate))
                if rml.value(om, RML.reference) is not None:
                    out.add((child, MORK.dataRef, Literal(str(rml.value(om, RML.reference)))))
                elif rml.value(om, RR.constant) is not None:
                    value = rml.value(om, RR.constant)
                    out.add((child, MORK.exactABoxMatch if isinstance(value, URIRef) else MORK.dataInline, value))
                elif rml.value(om, RR.template) is not None:
                    out.add((child, MORK.conceptNameTemplate, Literal(re.sub(r"\{([^{}]+)\}", r"${\1}", str(rml.value(om, RR.template))))))
                elif rml.value(om, FNML.execution) is not None:
                    result.findings.append(f"{_local(tm)}: the function on {predicate} is not read")
                for unsupported, what in ((RR.datatype, "a datatype"), (RR.language, "a language"), (RML.languageMap, "a language map")):
                    if rml.value(om, unsupported) is not None:
                        result.findings.append(f"{_local(tm)}: {what} on {predicate}'s object is not read")
            for c in rml.objects(pom, RR.object):
                child = URIRef(f"{m}_{_local(predicate)}_value")
                out.add((child, RDF.type, MORK.DataMapping))
                out.add((child, MORK.mappingScheme, scheme))
                out.add((child, MORK.compositeBroaderMapping, m))
                out.add((m, MORK.compositeNarrowerMapping, child))
                out.add((child, MORK.exactRBoxMatch, predicate))
                out.add((child, MORK.exactABoxMatch if isinstance(c, URIRef) else MORK.dataInline, c))
    if not maps:
        result.findings.append("the file holds no triples map")
    return result
