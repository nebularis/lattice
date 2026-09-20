"""
mork_communities/namespaces.py

RDF namespace declarations for MORK community and projection constructs.
"""

from rdflib import Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, SKOS, DCTERMS, SH

MORK = Namespace("http://www.nebularis.org/ontologies/Mork#")

# ── Community classes ──────────────────────────────────────────────
SEMANTIC_COMMUNITY = MORK.SemanticCommunity
COMMUNITY_MEMBERSHIP = MORK.CommunityMembership
COMMUNITY_SCHEME = MORK.CommunityScheme
SECTION_OBSERVATION = MORK.SectionObservation
COMMUNITY_MATCH = MORK.CommunityMatch

# ── Projection classes ─────────────────────────────────────────────
ONTOLOGICAL_PROJECTION = MORK.OntologicalProjection
PROPERTY_PROJECTION = MORK.PropertyProjection
DAG_TEMPLATE = MORK.DAGTemplate

# ── Shadow ontology classes ────────────────────────────────────────
OWL_AXIOM = MORK.OwlAxiom
OWL_CLASS = MORK.OwlClass
OWL_OBJECT_PROPERTY = MORK.OwlObjectProperty
OWL_DATA_PROPERTY = MORK.OwlDataProperty

# ── Core MORK classes ──────────────────────────────────────────────
DATA_CONCEPT = MORK.DataConcept
REPRESENTATION = MORK.Representation
REPRESENTATION_SCHEME = MORK.RepresentationScheme
ONTOLOGICAL_SCHEME = MORK.OntologicalScheme
MAPPING_SCHEME = MORK.MappingScheme
DATA_MAPPING = MORK.DataMapping

# ── Community object properties ────────────────────────────────────
HAS_COMMUNITY_MEMBERSHIP = MORK.hasCommunityMembership
MEMBER_CONCEPT = MORK.memberConcept
COMMUNITY_SCHEME_PROP = MORK.communityScheme
OBSERVED_IN_SECTION = MORK.observedInSection
OBSERVED_CONCEPT = MORK.observedConcept
OBSERVED_IN_SCHEME = MORK.observedInScheme
MATCHES_COMMUNITY = MORK.matchesCommunity
MATCH_SECTION = MORK.matchSection
MATCHED_CONCEPTS = MORK.matchedConcepts
DISCOVERED_FROM = MORK.discoveredFrom

# ── Projection object properties ───────────────────────────────────
HAS_ONTOLOGICAL_PROJECTION = MORK.hasOntologicalProjection
PROJECTED_CLASS = MORK.projectedClass
HAS_PROPERTY_PROJECTION = MORK.hasPropertyProjection
PROJECTED_CONCEPT = MORK.projectedConcept
PROJECTED_PROPERTY = MORK.projectedProperty
PROJECTED_PARENT_CLASS = MORK.projectedParentClass
HAS_DAG_TEMPLATE = MORK.hasDAGTemplate
DAG_TEMPLATE_ROOT = MORK.dagTemplateRoot
DAG_TEMPLATE_CHILD = MORK.dagTemplateChild
PROJECTION_TARGET_ONTOLOGY = MORK.projectionTargetOntology

# ── Shadow ontology object properties ──────────────────────────────
SHADOW_OF = MORK.shadowOf
SHADOW_SUB_CLASS_OF = MORK.shadowSubClassOf
SHADOW_SUB_PROPERTY_OF = MORK.shadowSubPropertyOf
SHADOW_DOMAIN = MORK.shadowDomain
SHADOW_RANGE = MORK.shadowRange

# ── Community data properties ──────────────────────────────────────
COMMUNITY_MEMBER_WEIGHT = MORK.communityMemberWeight
COMMUNITY_SIZE = MORK.communitySize
COMMUNITY_OBSERVATION_COUNT = MORK.communityObservationCount
COMMUNITY_COHERENCE = MORK.communityCoherence
MATCH_SCORE = MORK.matchScore
MATCH_CONFIDENCE = MORK.matchConfidence
OBSERVATION_TIMESTAMP = MORK.observationTimestamp
COMMUNITY_SCHEME_VERSION = MORK.communitySchemeVersion
DETECTION_ALGORITHM = MORK.detectionAlgorithm
DETECTION_RESOLUTION = MORK.detectionResolution

# ── Projection data properties ─────────────────────────────────────
PROJECTED_CLASS_FREQUENCY = MORK.projectedClassFrequency
PROPERTY_PROJECTION_FREQUENCY = MORK.propertyProjectionFrequency
PROPERTY_PROJECTION_CONFIDENCE = MORK.propertyProjectionConfidence
DAG_TEMPLATE_FREQUENCY = MORK.dagTemplateFrequency

# ── Existing MORK properties used ─────────────────────────────────
IRI_PROP = MORK.iri
CONCEPT_NAME = MORK.conceptName
REPRESENTATION_OF = MORK.representationOf
REPRESENTED_AS = MORK.representedAs
HAS_MAPPING = MORK.hasMapping
EXACT_TBOX_MATCH = MORK.exactTBoxMatch
EXACT_RBOX_MATCH = MORK.exactRBoxMatch
EXACT_ABOX_MATCH = MORK.exactABoxMatch
INVERSE_RBOX_MATCH = MORK.inverseRBoxMatch
COMPOSITE_BROADER_MAPPING = MORK.compositeBroaderMapping
COMPOSITE_NARROWER_MAPPING = MORK.compositeNarrowerMapping
BROADER_APPLICATIVE = MORK.broaderApplicative
MAPPING_SCHEME_PROP = MORK.mappingScheme
CONCEPT_SCHEME_PROP = MORK.conceptScheme
REPRESENTATION_SCHEME_PROP = MORK.representationScheme
ONTOLOGICAL_SCHEME_PROP = MORK.ontologicalScheme
MEMBER_PROPERTY = MORK.memberProperty
WEIGHTING = MORK.weighting