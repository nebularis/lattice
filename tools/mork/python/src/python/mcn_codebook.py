"""
mcn_codebook.py

The codebook for MCN (MORK Compact Notation): the complete mapping between
MCN's short codes and the MORK/SKOS/SHACL/SWRL/R2RML/Foundation vocabulary
terms they stand for.

This module is data, not logic. It exists as a separate module (rather than
inline in mcn_decoder.py) so that:

  - the codebook can be unit-tested for internal consistency (no duplicate
    codes, every polymorphic code has a resolution table, etc.) independently
    of the decoder that consumes it;
  - the codebook's *coverage* of mork/spec/Mork.ttl can be checked
    mechanically (see test_mcn_decoder.py::TestCodebookCoverage), which is
    the "codebook governance" mechanism called for in §20 of the spec; and
  - a future encoder (RDF -> MCN, spec §15) can import the same tables the
    decoder does, so the two directions can never disagree about what a code
    means.

Normative reference: docs/architecture/mork-compact-notation.md §3.4, §4,
§5, §7, §8. Every table below corresponds to a table in that document; the
section number is noted on each. If you change a mapping here, update the
spec's table too (and vice versa) -- they are supposed to be the same data
rendered twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

# ---------------------------------------------------------------------------
# Predeclared prefixes (spec §3.4) -- never need an "@p" directive.
# ---------------------------------------------------------------------------

MORK_NS = "http://www.nebularis.org/ontologies/Mork#"

PREDECLARED_PREFIXES: Dict[str, str] = {
    "mork": MORK_NS,
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "sh": "http://www.w3.org/ns/shacl#",
    "swrl": "http://www.w3.org/2003/11/swrl#",
    "swrlb": "http://www.w3.org/2003/11/swrlb#",
    "rr": "http://www.w3.org/ns/r2rml#",
    "rml": "http://semweb.mmlab.be/ns/rml#",
    "fnd": "https://www.nebularis.org/neuro-semantic/lattice/foundation#",
    "dct": "http://purl.org/dc/terms/",
}


# ---------------------------------------------------------------------------
# §8.1 Type codes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TypeSpec:
    """One row of a §8.1 type-code table."""

    curie: str
    family: str
    note: str = ""


# Kept in the same family groupings and order as the spec's tables so a
# human comparing this file to the document can do so line by line.
TYPES: Dict[str, TypeSpec] = {}


def _type(code: str, curie: str, family: str, note: str = "") -> None:
    if code in TYPES:
        raise ValueError(f"duplicate type code {code!r}")
    TYPES[code] = TypeSpec(curie=curie, family=family, note=note)


# -- Mapping --
_type("M", "mork:DataMapping", "Mapping", "default type inside %M")
_type("MD", "mork:Datum", "Mapping")
_type("MU", "mork:UncertainMapping", "Mapping")
_type("MX", "mork:DeferredContext", "Mapping")
_type("ML", "mork:Lookup", "Mapping")
_type("MW", "mork:WeightedMatch", "Mapping")
_type("MI", "mork:Interpolation", "Mapping", "a skos:OrderedCollection, not a DataMapping")
_type("MH", "mork:Hypothesis", "Mapping", "normally inferred; rarely asserted")
_type("MN", "mork:IndexedMapping", "Mapping")
_type("MG", "mork:GenerativeMapping", "Mapping", "abstract; prefer MS/MR/MT/MP")
_type("MS", "mork:ShapeMapping", "Mapping", "implied by gs")
_type("MR", "mork:RuleMapping", "Mapping", "implied by gr")
_type("MT", "mork:TransformMapping", "Mapping", "implied by gt")
_type("MP", "mork:ProjectionMapping", "Mapping", "implied by gc")

# -- Concept --
_type("C", "mork:DataConcept", "Concept", "default type inside %T")
_type("CO", "mork:Objectification", "Concept")

# -- Representation --
_type("R", "mork:Representation", "Representation", "default type inside %R")
_type("RE", "mork:Entity", "Representation")
_type("RA", "mork:Attribute", "Representation")
_type("RY", "mork:Array", "Representation")
_type("RS", "mork:Association", "Representation")
_type("RC", "mork:Composition", "Representation")
_type("RH", "mork:Chaining", "Representation")
_type("RL", "mork:Collection", "Representation")
_type("RO", "mork:OrderedCollection", "Representation")
_type("RU", "mork:UnorderedCollection", "Representation")
_type("RT", "mork:SetListing", "Representation")
_type("RM", "mork:Membership", "Representation", "abstract by convention")
_type("RN", "mork:AnonymousElement", "Representation")
_type("RV", "mork:ScalarValueElement", "Representation")
_type("RX", "mork:CollectionElement", "Representation")
_type("RF", "mork:Referencing", "Representation")
_type("RI", "mork:IdentifiableElement", "Representation")

# -- Ontology proxy --
_type("X", "mork:OwlAxiom", "OntologyProxy", "default type inside %O")
_type("XC", "mork:OwlClass", "OntologyProxy")
_type("XO", "mork:OwlObjectProperty", "OntologyProxy")
_type("XD", "mork:OwlDataProperty", "OntologyProxy")
_type("XG", "mork:Digraph", "OntologyProxy", "deprecated in Mork.ttl")
_type("XI", "mork:DeferredConceptIRI", "OntologyProxy", "class punned with the .dci individual")

# -- Intent --
_type("I", "mork:IntentNode", "Intent", "default type inside %I")
_type("IQ", "mork:QualitativeIntent", "Intent")
_type("IN", "mork:QuantitativeConstraint", "Intent")
_type("IS", "mork:SpatialScope", "Intent")
_type("IT", "mork:TemporalScope", "Intent")
_type("IX", "mork:ExclusionIntent", "Intent")
_type("II", "mork:InclusionIntent", "Intent")
_type("IR", "mork:NormativeReferenceItent", "Intent", "spelling preserved exactly as in Mork.ttl")

# -- Generative support --
_type("GT", "mork:TargetingSpec", "Generative", "positional form [mode target]")
_type("GP", "mork:ParameterBinding", "Generative", "positional form [name type value]")
_type("GC", "mork:ConstraintProvenance", "Generative", "positional form [creator model conf status]")
_type("GR", "mork:RuleProvenance", "Generative", "positional form [creator model conf status]")
_type("GF", "mork:TransformProvenance", "Generative", "positional form [creator model conf status]")
_type("GJ", "mork:ProjectionProvenance", "Generative", "positional form [creator model conf status]")
_type("GS", "mork:ShapeTemplate", "Generative")
_type("GU", "mork:RuleTemplate", "Generative")
_type("GQ", "mork:QueryTemplate", "Generative")

# -- Template expression --
_type("E", "mork:TemplateExpression", "Expression", "normally produced by `id = expr` lines")
_type("EL", "mork:LiteralExpression", "Expression")
_type("ER", "mork:RefExpression", "Expression")
_type("EC", "mork:ConcatExpression", "Expression")
_type("EI", "mork:InterpolationExpression", "Expression")
_type("EK", "mork:LookupExpression", "Expression")
_type("EB", "mork:TemplateBinding", "Expression", "positional form [name expr]")

# -- Scheme --
_type("SM", "mork:MappingScheme", "Scheme", "block header %M")
_type("ST", "mork:TaxonomyScheme", "Scheme", "block header %T")
_type("SR", "mork:RepresentationScheme", "Scheme", "block header %R")
_type("SO", "mork:OntologicalScheme", "Scheme", "block header %O")
_type("SI", "mork:IntentScheme", "Scheme", "block header %I")
_type("SK", "mork:ConstraintScheme", "Scheme", "block header %K")
_type("SU", "mork:RuleScheme", "Scheme", "block header %U")

# -- Misc / external artefact types --
_type("CM", "mork:CompilationMode", "Misc")
_type("SF", "mork:SerializationFormat", "Misc")
_type("SH", "sh:NodeShape", "Artefact", 'payload form: SH "<shacl-compact>"')
_type("SP", "sh:PropertyShape", "Artefact")
_type("SW", "swrl:Imp", "Artefact", 'payload form: SW "<swrl-compact>"')
_type("TM", "rr:TriplesMap", "Artefact", 'payload form: TM "<rml-compact>"')
_type("PI", "fnd:PersistentIdentity", "Artefact")


# ---------------------------------------------------------------------------
# §8.2 Property codes
# ---------------------------------------------------------------------------

# kind: "object"      -- value resolves to an IRI/inline node/payload node
#       "data"         -- value is a literal
#       "polymorphic"  -- resolved by subject type, see POLYMORPHIC below
KIND_OBJECT = "object"
KIND_DATA = "data"
KIND_POLYMORPHIC = "polymorphic"


@dataclass(frozen=True)
class PropertySpec:
    """One row of a §8.2 property-code table.

    ``curie`` holds a single CURIE for object/data codes. For a polymorphic
    code it holds the '/'-joined union of the CURIEs it may resolve to
    (informational only -- POLYMORPHIC is what the decoder actually
    consults). ``datatype`` is None (no fixed datatype -> xsd:string
    default), a CURIE string (a fixed datatype), or ``"*"`` (the code's
    datatype is inferred per spec §3.5).
    """

    curie: str
    kind: str
    datatype: Optional[str] = None
    group: str = ""


PROPERTIES: Dict[str, PropertySpec] = {}


def _prop(
    code: str,
    curie: str,
    *,
    kind: str = KIND_OBJECT,
    datatype: Optional[str] = None,
    group: str = "",
) -> None:
    if code in PROPERTIES:
        raise ValueError(f"duplicate property code {code!r}")
    PROPERTIES[code] = PropertySpec(curie=curie, kind=kind, datatype=datatype, group=group)


# -- Scheme membership (normally implicit via block headers) --
_prop("ms", "mork:mappingScheme", group="Scheme membership")
_prop("cs", "mork:conceptScheme", group="Scheme membership")
_prop("rs", "mork:representationScheme", group="Scheme membership")
_prop("os", "mork:ontologicalScheme", group="Scheme membership")
_prop("is", "mork:intentScheme", group="Scheme membership")
_prop("in", "skos:inScheme", group="Scheme membership")

# -- Mapping selection --
_prop("f", "mork:mappingFor", group="Mapping selection")
_prop("hm", "mork:hasMapping", group="Mapping selection")
_prop("iv", "mork:indicativeMapping", group="Mapping selection")

# -- Exact match --
_prop("xt", "mork:exactTBoxMatch", group="Exact match")
_prop("xr", "mork:exactRBoxMatch", group="Exact match")
_prop("xa", "mork:exactABoxMatch", group="Exact match")
_prop("xi", "mork:inverseRBoxMatch", group="Exact match")
_prop("xm", "mork:intransitiveExactMatch", group="Exact match")

# -- Category match --
_prop("bt", "mork:broadTBoxCategoryMatch", group="Category match")
_prop("br", "mork:broadRBoxCategoryMatch", group="Category match")
_prop("ba", "mork:broadABoxCategoryMatch", group="Category match")
_prop("nt", "mork:narrowTBoxCategoryMatch", group="Category match")
_prop("nr", "mork:narrowRBoxCategoryMatch", group="Category match")
_prop("na", "mork:narrowABoxCategoryMatch", group="Category match")
_prop("bc", "mork:broadCategoryMatch", group="Category match")
_prop("nc", "mork:narrowCategoryMatch", group="Category match")

# -- Possible match --
_prop("px", "mork:possibleMatch", group="Possible match")
_prop("lx", "mork:lexicalMatch", group="Possible match")
_prop("sx", "mork:semanticMatch", group="Possible match")
_prop("tx", "mork:structuralMatch", group="Possible match")
_prop("pt", "mork:pathMatch", group="Possible match")
_prop("rp", "mork:referenceDataPath", group="Possible match")
_prop("pm", "mork:partialMatch", group="Possible match")
_prop("mum", "mork:missingOrUnrelatedMatch", group="Possible match")
_prop("dgm", "mork:digraphMatch", group="Possible match")
_prop("dgo", "mork:digraphOf", group="Possible match")

# -- Mapping composition --
_prop("cn", "mork:compositeNarrowerMapping", group="Mapping composition")
_prop("cb", "mork:compositeBroaderMapping", group="Mapping composition")
_prop("cnt", "mork:compositeNarrowerTemplate", group="Mapping composition")
_prop("cbt", "mork:compositeBroaderTemplate", group="Mapping composition")
_prop("nrm", "mork:narrowerMapping", group="Mapping composition")
_prop("brm", "mork:broaderMapping", group="Mapping composition")
_prop("wn", "mork:weightedNarrower", group="Mapping composition")
_prop("wb", "mork:weightedBroader", group="Mapping composition")
_prop("ap", "mork:broaderApplicative", group="Mapping composition")

# -- Mapping relation --
_prop("rm", "mork:relatedMapping", group="Mapping relation")
_prop("cm", "mork:closeMapping", group="Mapping relation")
_prop("em", "mork:exactMapping", group="Mapping relation")
_prop("sg", "mork:siblingMapping", group="Mapping relation")

# -- Deferral and templates --
_prop("df", "mork:deferredMapping", group="Deferral")
_prop("dp", "mork:dependentMapping", group="Deferral")
_prop("hy", "mork:hypothesisMapping", group="Deferral")
_prop("tp", "mork:templateMapping", group="Deferral")
_prop("it", "mork:identityTemplateMapping", group="Deferral")
_prop("rd", "mork:referenceDataMapping", group="Deferral")
_prop("tc", "mork:templateClassMapping", group="Deferral")
_prop("y", "mork:yieldConcept", group="Deferral")

# -- Placeholder --
_prop("ph", "mork:placeholderMapping", group="Placeholder")
_prop("cc", "mork:concatenation", group="Placeholder")
_prop("ic", "mork:interpolationComponent", group="Placeholder")

# -- Property assertion --
_prop("ad", "mork:assertsPropertyDomains", group="Property assertion")
_prop("ar", "mork:assertsPropertyRanges", group="Property assertion")
_prop("pma", "mork:propertyMappingAssertions", group="Property assertion")

# -- Concept and representation structure --
_prop("kn", "mork:compositeNarrower", group="Concept structure")
_prop("kb", "mork:compositeBroader", group="Concept structure")
_prop("an", "mork:associativeNarrower", group="Concept structure")
_prop("ab", "mork:associativeBroader", group="Concept structure")
_prop("brl", "mork:broadConceptRole", group="Concept structure")
_prop("nrl", "mork:narrowConceptRole", group="Concept structure")
_prop("bnr", "mork:broadNavigableConceptRole", group="Concept structure")
_prop("nnr", "mork:narrowNavigableConceptRole", group="Concept structure")
_prop("mp", "mork:memberProperty", group="Concept structure")
_prop("mo", "mork:memberOf", group="Concept structure")
_prop("et", "mork:elementType", group="Concept structure")
_prop("rl", "mork:relatedProperty", group="Concept structure")
_prop("ro", "mork:representationOf", group="Concept structure")
_prop("ra", "mork:representedAs", group="Concept structure")
_prop("hc", "mork:hasConcept", group="Concept structure")
_prop("fm", "mork:format", group="Concept structure")

# -- SKOS --
_prop(">", "skos:broader", group="SKOS")
_prop("<", "skos:narrower", group="SKOS")
_prop("~", "skos:related", group="SKOS")
_prop("s=", "skos:exactMatch", group="SKOS")
_prop("s~", "skos:closeMatch", group="SKOS")
_prop("s>", "skos:broadMatch", group="SKOS")
_prop("s<", "skos:narrowMatch", group="SKOS")
_prop("s-", "skos:relatedMatch", group="SKOS")
_prop("sm", "skos:member", group="SKOS")

# -- Precedence (normally derived, not asserted) --
_prop("pr", "mork:precedes", group="Precedence")
_prop("sp", "mork:softPrecedes", group="Precedence")
_prop("rif", "mork:resolvesIdentityFor", group="Precedence")
_prop("tb", "mork:templateBinding", group="Precedence")

# -- Intent --
_prop("ri", "mork:refinesIntent", group="Intent")
_prop("im", "mork:intentMapping", group="Intent")
_prop("sv", "mork:scopeValue", group="Intent")
_prop("cu", "mork:constraintUnit", group="Intent")
_prop("cd", "mork:constraintDimension", group="Intent")
_prop("src", "mork:hasNaturalLanguageSource", kind=KIND_DATA, group="Intent")
_prop("cf", "mork:hasIntentConfidence", kind=KIND_DATA, datatype="xsd:decimal", group="Intent")
_prop("op", "mork:constraintOperator", kind=KIND_DATA, group="Intent")
_prop("cv", "mork:constraintValue", kind=KIND_DATA, datatype="xsd:decimal", group="Intent")
_prop("cuv", "mork:constraintUpperValue", kind=KIND_DATA, datatype="xsd:decimal", group="Intent")
_prop("sty", "mork:scopeType", kind=KIND_DATA, group="Intent")
_prop("sin", "mork:scopeInclusion", kind=KIND_DATA, group="Intent")
_prop("td", "mork:temporalDuration", kind=KIND_DATA, datatype="xsd:dayTimeDuration", group="Intent")
_prop("tu", "mork:temporalUnit", kind=KIND_DATA, group="Intent")
_prop("rid", "mork:referenceIdentifier", kind=KIND_DATA, group="Intent")

# -- Template expression (normally produced by expression lines) --
_prop("cl", "mork:concatLeft", group="Template expression")
_prop("cr", "mork:concatRight", group="Template expression")
_prop("hb", "mork:hasBinding", group="Template expression")
_prop("ls", "mork:lookupSource", group="Template expression")
_prop("lk", "mork:lookupScheme", group="Template expression")
_prop("lp", "mork:lookupProperty", group="Template expression")
_prop("pe", "mork:placeholderExpression", group="Template expression")
_prop("ts", "mork:templateString", kind=KIND_DATA, group="Template expression")
_prop("phn", "mork:placeholderName", kind=KIND_DATA, group="Template expression")

# -- Generative --
_prop("tg", "mork:hasTargetingSpec", group="Generative")
_prop(
    "pb",
    "mork:hasParameterBinding/mork:paramBinding",
    kind=KIND_POLYMORPHIC,
    group="Generative",
)
_prop("do", "mork:dependsOnMapping", group="Generative")
_prop("gs", "mork:generatesShapeDefinition", group="Generative")
_prop("gr", "mork:generatesRuleDefinition", group="Generative")
_prop("gt", "mork:generatesTransformDefinition", group="Generative")
_prop("gc", "mork:generatesClassDefinition", group="Generative")
_prop(
    "tl",
    "mork:hasShapeTemplate/mork:hasRuleTemplate",
    kind=KIND_POLYMORPHIC,
    group="Generative",
)
_prop("st", "mork:hasShapeTemplate", group="Generative")
_prop("rt", "mork:hasRuleTemplate", group="Generative")
_prop(
    "pv",
    "mork:hasConstraintProvenance/mork:hasRuleProvenance/"
    "mork:hasTransformProvenance/mork:hasProjectionProvenance",
    kind=KIND_POLYMORPHIC,
    group="Generative",
)
_prop("pvc", "mork:hasConstraintProvenance", group="Generative")
_prop("pvr", "mork:hasRuleProvenance", group="Generative")
_prop("pvt", "mork:hasTransformProvenance", group="Generative")
_prop("pvp", "mork:hasProjectionProvenance", group="Generative")
_prop("se", "mork:hasSeverity", group="Generative")
_prop("aj", "mork:appliesInJurisdiction", group="Generative")
_prop("bq", "mork:bindsToCriteria", group="Generative")
_prop("ju", "mork:jurisdiction", kind=KIND_DATA, group="Generative")
_prop("ef", "mork:effectiveFrom", kind=KIND_DATA, datatype="xsd:dateTime", group="Generative")
_prop("eu", "mork:effectiveUntil", kind=KIND_DATA, datatype="xsd:dateTime", group="Generative")
_prop("kv", "mork:constraintVersion", kind=KIND_DATA, group="Generative")
_prop("mv", "mork:mappingVersion", kind=KIND_DATA, group="Generative")
_prop("dr", "mork:deprecationReason", kind=KIND_DATA, group="Generative")
_prop("pnm", "mork:paramName", kind=KIND_DATA, group="Generative")
_prop("pty", "mork:paramType", kind=KIND_DATA, group="Generative")
_prop("pvl", "mork:paramValue", kind=KIND_DATA, datatype="*", group="Generative")
_prop("ql", "mork:queryLanguage", kind=KIND_DATA, group="Generative")
_prop("qt", "mork:queryText", kind=KIND_DATA, group="Generative")
_prop("swt", "mork:swrlText", kind=KIND_DATA, group="Generative")
_prop("to", "mork:targetsOntology", kind=KIND_DATA, datatype="xsd:anyURI", group="Generative")
_prop("ih", "mork:inputHash", kind=KIND_DATA, group="Generative")
_prop("mid", "mork:llmModelId", kind=KIND_DATA, group="Generative")
_prop("lc", "mork:llmConfidence", kind=KIND_DATA, datatype="xsd:decimal", group="Generative")
_prop("rv", "mork:reviewStatus", kind=KIND_DATA, group="Generative")
_prop("pc", "mork:provenanceCreator", kind=KIND_DATA, group="Generative")
_prop("pd", "mork:provenanceCreated", kind=KIND_DATA, datatype="xsd:dateTime", group="Generative")
_prop("isc", "mork:impactScope", kind=KIND_DATA, group="Generative")

# -- Versioning and Foundation --
_prop("ss", "mork:supersedes", group="Versioning")
_prop("eg", "mork:egressProjection", group="Versioning")
_prop("md", "mork:compilationMode", group="Versioning")
_prop("gv", "fnd:hasGovernanceState", group="Versioning")
_prop("fi", "fnd:hasIdentity", group="Versioning")
_prop("sby", "fnd:supersededBy", group="Versioning")

# -- Core data --
_prop("w", "mork:weighting", kind=KIND_DATA, datatype="xsd:integer", group="Core data")
_prop("n", "mork:mappingNote", kind=KIND_DATA, group="Core data")
_prop("c", "mork:conceptName", kind=KIND_DATA, group="Core data")
_prop("ci", "mork:conceptIRI", kind=KIND_DATA, datatype="xsd:anyURI", group="Core data")
_prop("cid", "mork:conceptId", kind=KIND_DATA, group="Core data")
_prop("i", "mork:individualName", kind=KIND_DATA, group="Core data")
_prop("ii", "mork:individualIRI", kind=KIND_DATA, datatype="xsd:anyURI", group="Core data")
_prop("id", "mork:identifier", kind=KIND_DATA, group="Core data")
_prop("p", "mork:path", kind=KIND_DATA, group="Core data")
_prop("rf", "mork:reference", kind=KIND_DATA, group="Core data")
_prop("r", "mork:dataRef", kind=KIND_DATA, group="Core data")
_prop("v", "mork:dataInline", kind=KIND_DATA, datatype="*", group="Core data")
_prop("dt", "mork:data", kind=KIND_DATA, datatype="*", group="Core data")
_prop("ix", "mork:mappingIndex", kind=KIND_DATA, datatype="xsd:integer", group="Core data")
_prop("mr", "mork:mappingRecommendation", kind=KIND_DATA, group="Core data")
_prop("nme", "mork:name", kind=KIND_DATA, group="Core data")
_prop("tt", "mork:template", kind=KIND_DATA, group="Core data")
_prop("ct", "mork:conceptNameTemplate", kind=KIND_DATA, group="Core data")
_prop("cft", "mork:conceptFQNameTemplate", kind=KIND_DATA, group="Core data")
_prop("cst", "mork:conceptShortNameTemplate", kind=KIND_DATA, group="Core data")
_prop("ip", "mork:interpolationTemplate", kind=KIND_DATA, group="Core data")
_prop("inc", "mork:incompleteMapping", kind=KIND_DATA, datatype="xsd:boolean", group="Core data")
_prop("icn", "mork:itemsConstrained", kind=KIND_DATA, datatype="xsd:boolean", group="Core data")
_prop("ord", "mork:orderedItems", kind=KIND_DATA, datatype="xsd:boolean", group="Core data")
_prop("unq", "mork:uniqueItems", kind=KIND_DATA, datatype="xsd:boolean", group="Core data")
_prop("iri", "mork:iri", kind=KIND_DATA, group="Core data")
_prop("ud", "mork:userDeclined", kind=KIND_DATA, group="Core data")
_prop("sw", "mork:swrlCompactSyntax", kind=KIND_DATA, group="Core data")
_prop("cev", "mork:collectionElementScalarValue", kind=KIND_DATA, datatype="*", group="Core data")
_prop("epv", "mork:externalPropertyValue", kind=KIND_DATA, datatype="*", group="Core data")

# -- Annotation --
_prop("nn", "skos:note", kind=KIND_DATA, group="Annotation")
_prop("sd", "skos:definition", kind=KIND_DATA, group="Annotation")
_prop("lb", "rdfs:label", kind=KIND_DATA, group="Annotation")
_prop("rc", "rdfs:comment", kind=KIND_DATA, group="Annotation")
_prop("ex", "skos:example", kind=KIND_DATA, group="Annotation")
_prop("sco", "skos:scopeNote", kind=KIND_DATA, group="Annotation")
_prop("al", "skos:altLabel", kind=KIND_DATA, group="Annotation")
_prop("en", "skos:editorialNote", kind=KIND_DATA, group="Annotation")
_prop("hn", "skos:historyNote", kind=KIND_DATA, group="Annotation")
_prop("sa", "rdfs:seeAlso", group="Annotation")
_prop("db", "rdfs:isDefinedBy", kind=KIND_DATA, group="Annotation")
_prop("sas", "owl:sameAs", group="Annotation")
_prop("dep", "owl:deprecated", kind=KIND_DATA, datatype="xsd:boolean", group="Annotation")
_prop("dcc", "dct:creator", kind=KIND_DATA, group="Annotation")
_prop("dct", "dct:title", kind=KIND_DATA, group="Annotation")
_prop("dcd", "dct:description", kind=KIND_DATA, group="Annotation")
_prop("dco", "dct:contributor", kind=KIND_DATA, group="Annotation")

# -- SHACL targeting (on GT nodes; usually written positionally) --
_prop("tcl", "sh:targetClass", group="SHACL targeting")
_prop("tob", "sh:targetObjectsOf", group="SHACL targeting")
_prop("tsb", "sh:targetSubjectsOf", group="SHACL targeting")
_prop("tnd", "sh:targetNode", group="SHACL targeting")


# ---------------------------------------------------------------------------
# §8.3 Polymorphic code resolution
# ---------------------------------------------------------------------------

# code -> {subject-type-curie: resolved-property-curie, ...}; a "*" key is
# the fallback used when no listed type matches.
POLYMORPHIC: Dict[str, Dict[str, str]] = {
    "pb": {
        "mork:QueryTemplate": "mork:paramBinding",
        "*": "mork:hasParameterBinding",
    },
    "tl": {
        "mork:ShapeMapping": "mork:hasShapeTemplate",
        "mork:RuleMapping": "mork:hasRuleTemplate",
    },
    "pv": {
        "mork:ShapeMapping": "mork:hasConstraintProvenance",
        "mork:RuleMapping": "mork:hasRuleProvenance",
        "mork:TransformMapping": "mork:hasTransformProvenance",
        "mork:ProjectionMapping": "mork:hasProjectionProvenance",
    },
}

# For `pv`, the inline provenance node's *type* also depends on the
# subject's generative type (spec §8.3): code -> class code from TYPES.
PV_PROVENANCE_TYPE: Dict[str, str] = {
    "mork:ShapeMapping": "GC",
    "mork:RuleMapping": "GR",
    "mork:TransformMapping": "GF",
    "mork:ProjectionMapping": "GJ",
}


# ---------------------------------------------------------------------------
# §5 / §8.1 Implied generative types
# ---------------------------------------------------------------------------

# A subject carrying this property code is implicitly also this type,
# mirroring the owl:equivalentClass definitions in Mork.ttl.
IMPLIED_TYPE_FOR_CODE: Dict[str, str] = {
    "gs": "MS",
    "gr": "MR",
    "gt": "MT",
    "gc": "MP",
}


# ---------------------------------------------------------------------------
# §9.6 Positional inline forms
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PositionalForm:
    """A code that accepts a positional (un-typed) inline node.

    ``type_code`` is None for `pv`, whose node type is resolved from the
    parent subject's generative type via PV_PROVENANCE_TYPE instead of
    being fixed.
    """

    type_code: Optional[str]
    slots: tuple


POSITIONAL_FORMS: Dict[str, PositionalForm] = {
    "tg": PositionalForm("GT", ("mode", "target")),
    "pb": PositionalForm("GP", ("pnm", "pty", "pvl")),
    "pv": PositionalForm(None, ("pc", "mid", "lc", "rv")),
    "hb": PositionalForm("EB", ("phn", "pe")),
}

# `tg` mode letter -> the SHACL targeting property code it stands for.
TARGETING_MODE_CODE: Dict[str, str] = {
    "c": "tcl",
    "o": "tob",
    "s": "tsb",
    "n": "tnd",
}

# `pb` type letter/word -> the mork:paramType string value.
PARAM_TYPE_WORD: Dict[str, str] = {
    "N": "Numeric",
    "C": "Concept",
    "P": "Path",
    "S": "String",
    "D": "Duration",
    "Numeric": "Numeric",
    "Concept": "Concept",
    "Path": "Path",
    "String": "String",
    "Duration": "Duration",
}


# ---------------------------------------------------------------------------
# §7 Blocks
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BlockSpec:
    """One row of the §7 block table."""

    scheme_type_code: Optional[str]
    membership_property: Optional[str]  # CURIE, or None for %X
    default_type_code: Optional[str]


BLOCKS: Dict[str, BlockSpec] = {
    "%M": BlockSpec("SM", "mork:mappingScheme", "M"),
    "%T": BlockSpec("ST", "mork:conceptScheme", "C"),
    "%R": BlockSpec("SR", "mork:representationScheme", "R"),
    "%O": BlockSpec("SO", "mork:ontologicalScheme", "X"),
    "%I": BlockSpec("SI", "mork:intentScheme", "I"),
    "%K": BlockSpec("SK", "skos:inScheme", "SH"),
    "%U": BlockSpec("SU", "skos:inScheme", "SW"),
    "%X": BlockSpec(None, None, None),
}

# Reserved format tokens accepted right after the id in a %R header.
REPRESENTATION_FORMATS = {".json", ".xml", ".yaml"}


# ---------------------------------------------------------------------------
# §8.4 Reserved value tokens
# ---------------------------------------------------------------------------

RESERVED: Dict[str, str] = {
    ".T": "owl:Thing",
    ".N": "owl:Nothing",
    ".top": "owl:topObjectProperty",
    ".dtop": "owl:topDataProperty",
    ".dci": "mork:DeferredConceptIRI",
    ".dcd": "mork:DeferredClassDefinition",
    ".dop": "mork:DeferredObjectPropertyDefinition",
    ".ddp": "mork:DeferredDataPropertyDefinition",
    ".did": "mork:DeferredIndividualDefinition",
    ".dab": "mork:DeferredABoxReference",
    ".mos": "mork:MorkOntologyScheme",
    ".bot": "mork:Bottom",
    ".nothing": "mork:OwlNothing",
    ".json": "mork:JSON",
    ".xml": "mork:XML",
    ".yaml": "mork:YAML",
    ".draft": "mork:DraftMode",
    ".review": "mork:ReviewMode",
    ".prod": "mork:ProductionMode",
    ".viol": "sh:Violation",
    ".warn": "sh:Warning",
    ".info": "sh:Info",
    ".gD": "fnd:Draft",
    ".gR": "fnd:Reviewed",
    ".gA": "fnd:Active",
    ".gS": "fnd:Superseded",
}


# ---------------------------------------------------------------------------
# §4 / §13.1 -- OWL object properties in Mork.ttl that have a declared
# owl:inverseOf, used by the "@opt inv" decoder option (spec §5, §13 D8).
# Keyed and valued by property CURIE (not by code, since a document may
# reach a property via a CURIE rather than a code).
# ---------------------------------------------------------------------------

INVERSE_OF: Dict[str, str] = {
    "mork:hasMapping": "mork:mappingFor",
    "mork:mappingFor": "mork:hasMapping",
    "mork:associativeBroader": "mork:associativeNarrower",
    "mork:associativeNarrower": "mork:associativeBroader",
    "mork:broadABoxCategoryMatch": "mork:narrowABoxCategoryMatch",
    "mork:narrowABoxCategoryMatch": "mork:broadABoxCategoryMatch",
    "mork:broadCategoryMatch": "mork:narrowCategoryMatch",
    "mork:narrowCategoryMatch": "mork:broadCategoryMatch",
    "mork:broadRBoxCategoryMatch": "mork:narrowRBoxCategoryMatch",
    "mork:narrowRBoxCategoryMatch": "mork:broadRBoxCategoryMatch",
    "mork:broadTBoxCategoryMatch": "mork:narrowTBoxCategoryMatch",
    "mork:narrowTBoxCategoryMatch": "mork:broadTBoxCategoryMatch",
    "mork:broaderMapping": "mork:narrowerMapping",
    "mork:narrowerMapping": "mork:broaderMapping",
    "mork:compositeBroader": "mork:compositeNarrower",
    "mork:compositeNarrower": "mork:compositeBroader",
    "mork:compositeBroaderMapping": "mork:compositeNarrowerMapping",
    "mork:compositeNarrowerMapping": "mork:compositeBroaderMapping",
    "mork:compositeBroaderTemplate": "mork:compositeNarrowerTemplate",
    "mork:compositeNarrowerTemplate": "mork:compositeBroaderTemplate",
    "mork:broadNavigableConceptRole": "mork:narrowNavigableConceptRole",
    "mork:narrowNavigableConceptRole": "mork:broadNavigableConceptRole",
    "mork:digraphMatch": "mork:digraphOf",
    "mork:digraphOf": "mork:digraphMatch",
    "mork:hasConcept": "skos:inScheme",
    "mork:memberOf": "mork:memberProperty",
    "mork:memberProperty": "mork:memberOf",
    "mork:representationOf": "mork:representedAs",
    "mork:representedAs": "mork:representationOf",
    "mork:weightedBroader": "mork:weightedNarrower",
    "mork:weightedNarrower": "mork:weightedBroader",
}


def _expand(curie: str) -> str:
    """CURIE (or bare IRI) -> full IRI, using the predeclared prefix table.
    Only meaningful for CURIEs whose prefix is one of PREDECLARED_PREFIXES;
    the codebook never references any other prefix."""
    if curie.startswith("http"):
        return curie
    prefix, _, local = curie.partition(":")
    return PREDECLARED_PREFIXES[prefix] + local


def _build_reverse_index() -> Dict[str, str]:
    """iri -> code, first-code-wins under sorted iteration (deterministic).
    Skips a polymorphic property's own '/'-joined union entry (no single
    IRI to key on) but still indexes each of its constituent properties,
    since those are real, individually addressable predicates."""
    rev: Dict[str, str] = {}
    for code in sorted(TYPES):
        rev.setdefault(_expand(TYPES[code].curie), code)
    for code in sorted(PROPERTIES):
        spec = PROPERTIES[code]
        for part in spec.curie.split("/"):
            rev.setdefault(_expand(part), code)
    for token in sorted(RESERVED):
        rev.setdefault(_expand(RESERVED[token]), token)
    return rev


_REVERSE_INDEX: Dict[str, str] = _build_reverse_index()


def code_for(iri: str) -> Optional[str]:
    """The MCN code (or reserved token) for a full IRI, or None if the
    ontology term has no code -- e.g. for a TestCodebookCoverage failure,
    or for a term outside Mork.ttl entirely (SKOS/SHACL/SWRL/Foundation
    terms MCN references by CURIE, not by code)."""
    return _REVERSE_INDEX.get(iri)


def codes_for(iris: Iterable[str]) -> List[str]:
    """codes_for(iterable_of_iris) -> the codes that exist, in input order,
    dropping any IRI with no code. Convenience for building doctrine
    fragments and prompt tables that list "the codes for this family of
    properties" (spec-external tooling; not used by the decoder itself)."""
    return [c for c in (code_for(i) for i in iris) if c is not None]


def is_annotation_property_code(code: str) -> bool:
    """Whether ``code`` names one of the annotation properties Mork.ttl
    declares (spec §13.1 table): informational only -- it changes nothing
    about how the decoder emits the triple, but downstream OWL structural
    tooling interprets these assertions as AnnotationAssertion rather than
    DataPropertyAssertion axioms.
    """
    return code in {
        "n", "nn", "sd", "lb", "rc", "ex", "sco", "al", "en", "hn",
        "sa", "db", "dep", "dcc", "dct", "dcd", "dco", "ud", "sw",
    }
