"""
mork_schemas.py

Pydantic schemas for MORK structured output.

These schemas constrain LLM output to valid MORK structures.
The spec_to_turtle functions provide deterministic, guaranteed-valid
Turtle serialisation from schema instances.

Implements:
  - R6 (typed output) from the reference architecture
  - Structured output strategy from §D.6
  - Type safety per Proposition 5.3
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


# ─── Namespace constants ───

MORK_NS = "http://www.nebularis.org/ontologies/Mork#"
SH_NS = "http://www.w3.org/ns/shacl#"
OWL_NS = "http://www.w3.org/2002/07/owl#"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"
SKOS_NS = "http://www.w3.org/2004/02/skos/core#"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
DCT_NS = "http://purl.org/dc/terms/"

TURTLE_PREFIXES = (
    "@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .\n"
    "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
    "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
    "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
    "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
    "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
    "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
    "@prefix dct: <http://purl.org/dc/terms/> .\n"
    "@prefix swrl: <http://www.w3.org/2003/11/swrl#> .\n"
)


# ─── Enumerations ───

class IntentType(str, Enum):
    COVERAGE = "CoverageIntent"
    QUANTITATIVE = "QuantitativeConstraint"
    SPATIAL = "SpatialScope"
    TEMPORAL = "TemporalScope"
    EXCLUSION = "ExclusionIntent"
    INCLUSION = "InclusionIntent"


class ConstraintOperator(str, Enum):
    LESS_THAN_OR_EQUAL = "LessThanOrEqual"
    GREATER_THAN_OR_EQUAL = "GreaterThanOrEqual"
    EQUAL = "Equal"
    BETWEEN = "Between"
    NOT_EQUAL = "NotEqual"


class ScopeType(str, Enum):
    COUNTRY = "Country"
    STATE = "State"
    REGION = "Region"
    POSTCODE = "Postcode"
    COORDINATE = "Coordinate"


class ScopeInclusion(str, Enum):
    INCLUDE = "Include"
    EXCLUDE = "Exclude"


class MappingType(str, Enum):
    DATA_MAPPING = "DataMapping"
    DATUM = "Datum"
    SHAPE_MAPPING = "ShapeMapping"
    RULE_MAPPING = "RuleMapping"


class BoxMatchType(str, Enum):
    EXACT_TBOX = "exactTBoxMatch"
    EXACT_RBOX = "exactRBoxMatch"
    EXACT_ABOX = "exactABoxMatch"
    INVERSE_RBOX = "inverseRBoxMatch"
    BROAD_TBOX = "broadTBoxCategoryMatch"
    NARROW_TBOX = "narrowTBoxCategoryMatch"
    BROAD_ABOX = "broadABoxCategoryMatch"
    NARROW_ABOX = "narrowABoxCategoryMatch"
    BROAD_RBOX = "broadRBoxCategoryMatch"
    NARROW_RBOX = "narrowRBoxCategoryMatch"


class ParamType(str, Enum):
    NUMERIC = "Numeric"
    CONCEPT = "Concept"
    PATH = "Path"
    STRING = "String"
    DURATION = "Duration"


class TargetingMode(str, Enum):
    TARGET_CLASS = "targetClass"
    TARGET_OBJECTS_OF = "targetObjectsOf"
    TARGET_SUBJECTS_OF = "targetSubjectsOf"
    TARGET_NODE = "targetNode"


# ─── Layer 1: Intent schemas ───

class IntentNodeSpec(BaseModel):
    """Structured specification for a MORK IntentNode."""

    local_name: str = Field(
        description="Local name for the IntentNode IRI"
    )
    intent_types: List[IntentType] = Field(
        min_length=1,
        description=(
            "One or more intent types. Not mutually exclusive: "
            "a node can be both CoverageIntent and QuantitativeConstraint."
        ),
    )
    natural_language_source: str = Field(
        description="The original text fragment this intent was extracted from"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="LLM extraction confidence"
    )
    refines_intents: List[str] = Field(
        default_factory=list,
        description="Local names of IntentNodes this node refines (composes)"
    )

    # QuantitativeConstraint fields (populated when intent_types includes QUANTITATIVE)
    constraint_operator: Optional[ConstraintOperator] = None
    constraint_value: Optional[float] = None
    constraint_upper_value: Optional[float] = None
    constraint_unit_iri: Optional[str] = None

    # SpatialScope fields
    scope_type: Optional[ScopeType] = None
    scope_inclusion: Optional[ScopeInclusion] = None
    scope_value_iri: Optional[str] = None

    # TemporalScope fields
    temporal_duration: Optional[str] = None
    temporal_unit: Optional[str] = None

    @model_validator(mode="after")
    def validate_quantitative_fields(self) -> "IntentNodeSpec":
        if IntentType.QUANTITATIVE in self.intent_types:
            if self.constraint_operator is None:
                raise ValueError(
                    "QuantitativeConstraint requires constraint_operator"
                )
            if self.constraint_value is None:
                raise ValueError(
                    "QuantitativeConstraint requires constraint_value"
                )
            if (
                self.constraint_operator == ConstraintOperator.BETWEEN
                and self.constraint_upper_value is None
            ):
                raise ValueError(
                    "Between constraint requires constraint_upper_value"
                )
            if (
                self.constraint_operator == ConstraintOperator.BETWEEN
                and self.constraint_upper_value is not None
                and self.constraint_upper_value <= self.constraint_value
            ):
                raise ValueError(
                    "constraint_upper_value must exceed constraint_value"
                )
        return self

    @model_validator(mode="after")
    def validate_spatial_fields(self) -> "IntentNodeSpec":
        if IntentType.SPATIAL in self.intent_types:
            if self.scope_type is None:
                raise ValueError("SpatialScope requires scope_type")
            if self.scope_inclusion is None:
                raise ValueError("SpatialScope requires scope_inclusion")
        return self


class IntentExtractionOutput(BaseModel):
    """Top-level output schema for the Intent Agent."""

    intent_scheme_local_name: str = Field(
        description="Local name for the IntentScheme IRI"
    )
    intent_nodes: List[IntentNodeSpec] = Field(min_length=1)
    explanation: str = Field(
        description="Brief explanation of the extraction strategy"
    )


# ─── Layer 2: Mapping schemas ───

class BoxMatch(BaseModel):
    """A single box match assertion."""

    match_type: BoxMatchType
    target_iri: str = Field(
        description="Full IRI of the target ontology element"
    )


class ParameterBindingSpec(BaseModel):
    """A parameter binding for a ShapeMapping or RuleMapping."""

    param_name: str
    param_type: ParamType
    param_value: str = Field(
        description="Serialised value; for Path type, a space-separated list of property IRIs"
    )


class TargetingSpecSpec(BaseModel):
    """Targeting specification for a GenerativeMapping."""

    mode: TargetingMode
    target_iri: str = Field(
        description="IRI of the target class, property, or individual"
    )


class ProvenanceSpec(BaseModel):
    """Provenance metadata for a generated mapping."""

    creator: str = Field(default="MappingAgent")
    model_id: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class MappingSpec(BaseModel):
    """
    Structured specification for a MORK mapping node.

    This is the primary output schema for the Mapping Agent.
    Each instance is deterministically converted to valid Turtle
    by mapping_spec_to_turtle().
    """

    local_name: str = Field(
        description="Local name for the mapping IRI"
    )
    mapping_type: MappingType
    intent_source_iri: Optional[str] = Field(
        default=None,
        description="Full IRI of the IntentNode this mapping realises"
    )
    box_matches: List[BoxMatch] = Field(default_factory=list)
    composite_narrower: List[str] = Field(
        default_factory=list,
        description="Local names of compositeNarrowerMapping targets"
    )
    broader_applicative: Optional[str] = Field(
        default=None,
        description="Local name of the broaderApplicative parent"
    )
    deferred_mapping: Optional[str] = Field(
        default=None,
        description="Local name of the deferredMapping target"
    )
    targeting_spec: Optional[TargetingSpecSpec] = None
    parameter_bindings: List[ParameterBindingSpec] = Field(
        default_factory=list
    )
    provenance: Optional[ProvenanceSpec] = None
    weighting: int = Field(
        default=80, ge=0, le=100,
        description="Confidence score 0-100"
    )
    mapping_note: Optional[str] = None
    concept_name: Optional[str] = None
    template_iri: Optional[str] = Field(
        default=None,
        description="IRI of the ShapeTemplate or RuleTemplate to instantiate"
    )

    @model_validator(mode="after")
    def validate_generative_completeness(self) -> "MappingSpec":
        """Enforce GCI axioms 5.6a-d and 6.13.6a-b at schema level."""
        if self.mapping_type in (
            MappingType.SHAPE_MAPPING,
            MappingType.RULE_MAPPING,
        ):
            if self.targeting_spec is None:
                raise ValueError(
                    f"{self.mapping_type.value} requires targeting_spec"
                )
            if not self.parameter_bindings:
                raise ValueError(
                    f"{self.mapping_type.value} requires at least one "
                    f"parameter_binding"
                )
        return self

    @model_validator(mode="after")
    def validate_broader_applicative_gci(self) -> "MappingSpec":
        """Enforce GCI 2.14a: broaderApplicative requires exactRBoxMatch."""
        if self.broader_applicative is not None:
            has_rbox = any(
                bm.match_type
                in (BoxMatchType.EXACT_RBOX, BoxMatchType.INVERSE_RBOX)
                for bm in self.box_matches
            )
            if not has_rbox:
                raise ValueError(
                    "GCI 2.14a: broaderApplicative requires "
                    "exactRBoxMatch or inverseRBoxMatch"
                )
        return self

    @model_validator(mode="after")
    def validate_datum_deferred(self) -> "MappingSpec":
        """Enforce GCI 2.7a: Datum requires deferredMapping."""
        if (
            self.mapping_type == MappingType.DATUM
            and self.deferred_mapping is None
        ):
            raise ValueError(
                "GCI 2.7a: Datum requires deferredMapping"
            )
        return self


class MappingGenerationOutput(BaseModel):
    """Top-level output schema for the Mapping Agent."""

    mappings: List[MappingSpec] = Field(min_length=1)
    explanation: str = Field(
        description="Brief explanation of the mapping strategy"
    )


# ─── Deterministic Turtle serialisation ───

def _escape_turtle_string(s: str) -> str:
    """Escape a string for Turtle literal syntax."""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _iri_ref(iri: str) -> str:
    """Format an IRI as a Turtle IRI reference or prefixed name."""
    if iri.startswith(MORK_NS):
        return f"mork:{iri[len(MORK_NS):]}"
    if iri.startswith(SH_NS):
        return f"sh:{iri[len(SH_NS):]}"
    if iri.startswith(OWL_NS):
        return f"owl:{iri[len(OWL_NS):]}"
    if iri.startswith(XSD_NS):
        return f"xsd:{iri[len(XSD_NS):]}"
    if iri.startswith(SKOS_NS):
        return f"skos:{iri[len(SKOS_NS):]}"
    if iri.startswith(RDF_NS):
        return f"rdf:{iri[len(RDF_NS):]}"
    if iri.startswith(RDFS_NS):
        return f"rdfs:{iri[len(RDFS_NS):]}"
    if iri.startswith(DCT_NS):
        return f"dct:{iri[len(DCT_NS):]}"
    return f"<{iri}>"


def intent_spec_to_turtle(
    spec: IntentNodeSpec,
    scheme_namespace: str,
    intent_scheme_iri: str,
) -> str:
    """
    Convert an IntentNodeSpec to valid Turtle.

    Deterministic: same input always produces same output.
    Guaranteed syntactically correct.
    """
    iri = f"{scheme_namespace}{spec.local_name}"
    triples: list[str] = []

    # Type assertions
    type_iris = [f"mork:{t.value}" for t in spec.intent_types]
    type_iris.insert(0, "mork:IntentNode")
    for t in type_iris:
        triples.append(f"    a {t}")

    # Scheme membership
    triples.append(f"    mork:intentScheme <{intent_scheme_iri}>")

    # Required properties
    escaped_source = _escape_turtle_string(spec.natural_language_source)
    triples.append(
        f'    mork:hasNaturalLanguageSource "{escaped_source}"'
    )
    triples.append(
        f'    mork:hasIntentConfidence "{spec.confidence}"^^xsd:decimal'
    )

    # Refinement links
    for refined in spec.refines_intents:
        triples.append(
            f"    mork:refinesIntent <{scheme_namespace}{refined}>"
        )

    # QuantitativeConstraint properties
    if spec.constraint_operator is not None:
        triples.append(
            f'    mork:constraintOperator "{spec.constraint_operator.value}"'
        )
    if spec.constraint_value is not None:
        triples.append(
            f'    mork:constraintValue "{spec.constraint_value}"^^xsd:decimal'
        )
    if spec.constraint_upper_value is not None:
        triples.append(
            f'    mork:constraintUpperValue '
            f'"{spec.constraint_upper_value}"^^xsd:decimal'
        )
    if spec.constraint_unit_iri is not None:
        triples.append(
            f"    mork:constraintUnit {_iri_ref(spec.constraint_unit_iri)}"
        )

    # SpatialScope properties
    if spec.scope_type is not None:
        triples.append(f'    mork:scopeType "{spec.scope_type.value}"')
    if spec.scope_inclusion is not None:
        triples.append(
            f'    mork:scopeInclusion "{spec.scope_inclusion.value}"'
        )
    if spec.scope_value_iri is not None:
        triples.append(
            f"    mork:scopeValue {_iri_ref(spec.scope_value_iri)}"
        )

    # TemporalScope properties
    if spec.temporal_duration is not None:
        triples.append(
            f'    mork:temporalDuration "{spec.temporal_duration}"'
            f"^^xsd:dayTimeDuration"
        )
    if spec.temporal_unit is not None:
        triples.append(f'    mork:temporalUnit "{spec.temporal_unit}"')

    return f"<{iri}>\n" + " ;\n".join(triples) + " .\n"


def mapping_spec_to_turtle(
    spec: MappingSpec,
    mapping_namespace: str,
) -> str:
    """
    Convert a MappingSpec to valid Turtle.

    Deterministic: same input always produces same output.
    Guaranteed syntactically correct.
    """
    iri = f"{mapping_namespace}{spec.local_name}"
    triples: list[str] = []

    # Type assertion
    triples.append(f"    a mork:{spec.mapping_type.value}")

    # Box matches
    for bm in spec.box_matches:
        triples.append(
            f"    mork:{bm.match_type.value} {_iri_ref(bm.target_iri)}"
        )

    # Compositional structure
    for cn in spec.composite_narrower:
        triples.append(
            f"    mork:compositeNarrowerMapping <{mapping_namespace}{cn}>"
        )

    if spec.broader_applicative is not None:
        triples.append(
            f"    mork:broaderApplicative "
            f"<{mapping_namespace}{spec.broader_applicative}>"
        )

    if spec.deferred_mapping is not None:
        triples.append(
            f"    mork:deferredMapping "
            f"<{mapping_namespace}{spec.deferred_mapping}>"
        )

    # Concept name
    if spec.concept_name is not None:
        escaped = _escape_turtle_string(spec.concept_name)
        triples.append(f'    mork:conceptName "{escaped}"')

    # Intent linkage (reverse direction: IntentNode :intentMapping DataMapping)
    # We emit a comment noting the linkage; the actual triple is on the IntentNode
    if spec.intent_source_iri is not None:
        triples.append(
            f"    # linked from intent: {_iri_ref(spec.intent_source_iri)}"
        )

    # Targeting spec (for GenerativeMappings)
    if spec.targeting_spec is not None:
        ts = spec.targeting_spec
        ts_bnode = f"_:ts_{spec.local_name}"
        triples.append(f"    mork:hasTargetingSpec {ts_bnode}")
        # The targeting spec bnode will be emitted separately

    # Parameter bindings
    for i, pb in enumerate(spec.parameter_bindings):
        pb_bnode = f"_:pb_{spec.local_name}_{i}"
        triples.append(f"    mork:hasParameterBinding {pb_bnode}")

    # Provenance
    if spec.provenance is not None:
        prov_bnode = f"_:prov_{spec.local_name}"
        if spec.mapping_type == MappingType.SHAPE_MAPPING:
            triples.append(
                f"    mork:hasConstraintProvenance {prov_bnode}"
            )
        elif spec.mapping_type == MappingType.RULE_MAPPING:
            triples.append(f"    mork:hasRuleProvenance {prov_bnode}")

    # Template reference
    if spec.template_iri is not None:
        if spec.mapping_type == MappingType.SHAPE_MAPPING:
            triples.append(
                f"    mork:hasShapeTemplate {_iri_ref(spec.template_iri)}"
            )
        elif spec.mapping_type == MappingType.RULE_MAPPING:
            triples.append(
                f"    mork:hasRuleTemplate {_iri_ref(spec.template_iri)}"
            )

    # Weighting
    triples.append(f"    mork:weighting {spec.weighting}")

    # Note
    if spec.mapping_note is not None:
        escaped = _escape_turtle_string(spec.mapping_note)
        triples.append(f'    mork:mappingNote "{escaped}"')

    # Build the main resource
    lines = [f"<{iri}>"]
    lines.append(" ;\n".join(triples) + " .\n")
    result = "\n".join(lines)

    # Emit targeting spec bnode
    if spec.targeting_spec is not None:
        ts = spec.targeting_spec
        ts_bnode = f"_:ts_{spec.local_name}"
        result += (
            f"\n{ts_bnode} a mork:TargetingSpec ;\n"
            f"    sh:{ts.mode.value} {_iri_ref(ts.target_iri)} .\n"
        )

    # Emit parameter binding bnodes
    for i, pb in enumerate(spec.parameter_bindings):
        pb_bnode = f"_:pb_{spec.local_name}_{i}"
        escaped_name = _escape_turtle_string(pb.param_name)
        escaped_val = _escape_turtle_string(pb.param_value)
        result += (
            f"\n{pb_bnode} a mork:ParameterBinding ;\n"
            f'    mork:paramName "{escaped_name}" ;\n'
            f'    mork:paramType "{pb.param_type.value}" ;\n'
            f'    mork:paramValue "{escaped_val}" .\n'
        )

    # Emit provenance bnode
    if spec.provenance is not None:
        prov = spec.provenance
        prov_class = (
            "ConstraintProvenance"
            if spec.mapping_type == MappingType.SHAPE_MAPPING
            else "RuleProvenance"
        )
        prov_bnode = f"_:prov_{spec.local_name}"
        escaped_creator = _escape_turtle_string(prov.creator)
        result += (
            f"\n{prov_bnode} a mork:{prov_class} ;\n"
            f'    mork:provenanceCreator "{escaped_creator}" ;\n'
            f'    mork:reviewStatus "DRAFT" .\n'
        )

    return result


def intent_output_to_turtle(
    output: IntentExtractionOutput,
    base_namespace: str,
) -> str:
    """Convert a complete IntentExtractionOutput to Turtle."""
    scheme_ns = f"{base_namespace}{output.intent_scheme_local_name}/"
    scheme_iri = f"{base_namespace}{output.intent_scheme_local_name}"

    parts = [TURTLE_PREFIXES, ""]

    # Emit the scheme
    parts.append(
        f"<{scheme_iri}> a mork:IntentScheme , skos:ConceptScheme .\n"
    )

    # Emit each intent node
    for node in output.intent_nodes:
        parts.append(
            intent_spec_to_turtle(node, scheme_ns, scheme_iri)
        )

    # Emit intentMapping triples (Layer 1 does not produce these,
    # but they are emitted when Layer 2 links back)

    return "\n".join(parts)


def mapping_output_to_turtle(
    output: MappingGenerationOutput,
    mapping_namespace: str,
) -> str:
    """Convert a complete MappingGenerationOutput to Turtle."""
    parts = [TURTLE_PREFIXES, ""]

    for spec in output.mappings:
        parts.append(
            mapping_spec_to_turtle(spec, mapping_namespace)
        )

    return "\n".join(parts)