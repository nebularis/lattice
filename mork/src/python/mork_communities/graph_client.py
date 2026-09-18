"""
mork_communities/graph_client.py

Thin wrapper around an RDF triple store (SPARQL endpoint or in-memory rdflib
graph) providing the query primitives needed by the community and projection
machinery.

Supports both:
  - SPARQLWrapper for remote endpoints (Fuseki, Stardog, GraphDB)
  - rdflib.Graph for in-memory / testing
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, SKOS

from mork_communities.namespaces import *

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SectionObservationRecord:
    """In-memory representation of a SectionObservation."""

    section_iri: URIRef
    scheme_iri: URIRef
    concepts: FrozenSet[URIRef]
    timestamp: Optional[str] = None


@dataclass(frozen=True)
class MappingRecord:
    """In-memory representation of a DataMapping with its box matches."""

    mapping_iri: URIRef
    tbox_match: Optional[URIRef] = None
    rbox_match: Optional[URIRef] = None
    abox_match: Optional[URIRef] = None
    parent_mapping: Optional[URIRef] = None
    broader_applicative: Optional[URIRef] = None
    children: Tuple[URIRef, ...] = ()
    weighting: int = 50


class MorkGraphClient:
    """
    Client for querying the MORK knowledge graph.

    Works with either an rdflib.Graph (for in-memory / testing)
    or a remote SPARQL endpoint.
    """

    def __init__(
        self,
        graph: Optional[Graph] = None,
        endpoint_url: Optional[str] = None,
        named_graphs: Optional[Dict[str, str]] = None,
    ):
        if graph is None and endpoint_url is None:
            raise ValueError("Provide either graph or endpoint_url")
        self._graph = graph
        self._endpoint = endpoint_url
        self._named_graphs = named_graphs or {}
        self._use_local = graph is not None

    # ── Section Observation Extraction ────────────────────────────

    def extract_section_observations(self) -> List[SectionObservationRecord]:
        """
        Extract all section observations from completed mapping runs.

        For each RepresentationScheme that has a completed MappingScheme,
        for each structural section, collect the DataConcepts identified
        via representationOf links or mapping confirmations.
        """
        if self._use_local:
            return self._extract_observations_local()
        return self._extract_observations_sparql()

    def _extract_observations_local(self) -> List[SectionObservationRecord]:
        g = self._graph
        observations = []

        # Find all RepresentationSchemes
        rep_schemes = set(g.subjects(RDF.type, REPRESENTATION_SCHEME))

        for rs in rep_schemes:
            # Check if this scheme has any completed mapping
            # (a Representation in rs has hasMapping to something in a MappingScheme)
            has_mappings = False
            for rep in g.subjects(REPRESENTATION_SCHEME_PROP, rs):
                if any(g.objects(rep, HAS_MAPPING)):
                    has_mappings = True
                    break
            if not has_mappings:
                continue

            # Find structural sections: non-leaf Representation nodes
            sections = self._find_structural_sections(rs)

            for section_iri in sections:
                concepts = self._find_concepts_in_section(section_iri)
                if len(concepts) >= 2:
                    observations.append(
                        SectionObservationRecord(
                            section_iri=section_iri,
                            scheme_iri=rs,
                            concepts=frozenset(concepts),
                        )
                    )

        logger.info(
            "Extracted %d section observations from %d schemes",
            len(observations),
            len(rep_schemes),
        )
        return observations

    def _find_structural_sections(self, scheme_iri: URIRef) -> Set[URIRef]:
        """
        Find non-leaf Representation nodes in a scheme.
        A node is a structural section if it has at least one memberProperty child.
        """
        g = self._graph
        sections = set()
        for rep in g.subjects(REPRESENTATION_SCHEME_PROP, scheme_iri):
            # Check if this node has children via memberProperty
            children = list(g.subjects(MEMBER_PROPERTY, rep))
            # Actually: memberProperty goes child -> parent (memberProperty ⊑ compositeNarrower)
            # So: child memberProperty parent => parent is a section containing child
            # Let's check if rep is the *object* of any memberProperty triple
            # i.e., ∃ child : child memberProperty rep
            has_children = any(g.subjects(MEMBER_PROPERTY, rep))
            if has_children:
                # This is wrong direction. memberProperty: child -> parent
                # So: subjects of (memberProperty, rep) are children of rep
                # Wait, memberProperty ⊑ compositeNarrower, and compositeNarrower
                # is "the subject's existence is conditional upon the object's"
                # So child memberProperty parent means child is contained in parent.
                # Therefore: g.subjects(MEMBER_PROPERTY, rep) = {} means nothing points
                # to rep as parent.
                # We need: things where rep is the OBJECT of memberProperty
                # => children that are memberProperty of rep
                pass

            # Re-check: in MORK, memberProperty ⊑ compositeNarrower
            # compositeNarrower goes from container to contained? No.
            # Actually from the ontology: "memberProperty is asymmetric, irreflexive"
            # and memberProperty ⊑ compositeNarrower ⊑ associativeNarrower ⊑ skos:narrower
            # skos:narrower(A, B) means B is narrower than A, i.e., A contains B.
            # So memberProperty(parent, child): parent has member child.
            # Therefore g.objects(rep, MEMBER_PROPERTY) gives children of rep.
            member_children = set(g.objects(rep, MEMBER_PROPERTY))
            if member_children:
                sections.add(rep)

        return sections

    def _find_concepts_in_section(self, section_iri: URIRef) -> Set[URIRef]:
        """
        Find all DataConcepts identified in a section's leaf attributes.
        Traverses memberProperty to find leaves, then follows representationOf
        and hasMapping to find concepts.
        """
        g = self._graph
        concepts = set()

        # Get all descendants of this section
        leaves = self._get_leaf_descendants(section_iri)

        for leaf in leaves:
            # Direct representationOf link
            for concept in g.objects(leaf, REPRESENTATION_OF):
                if (concept, RDF.type, DATA_CONCEPT) in g or \
                   (concept, CONCEPT_SCHEME_PROP, None) in g:
                    concepts.add(concept)

            # Via hasMapping -> DataMapping -> mappingFor concept
            for mapping in g.objects(leaf, HAS_MAPPING):
                # The mapping's concept can be found via the mapping's
                # relationship to a DataConcept
                for concept in g.subjects(HAS_MAPPING, mapping):
                    if concept != leaf and (
                        (concept, RDF.type, DATA_CONCEPT) in g
                        or any(g.objects(concept, CONCEPT_SCHEME_PROP))
                    ):
                        concepts.add(concept)

        return concepts

    def _get_leaf_descendants(self, section_iri: URIRef) -> Set[URIRef]:
        """Get all leaf descendants (Attributes) of a section."""
        g = self._graph
        leaves = set()
        stack = [section_iri]
        visited = set()

        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)

            children = set(g.objects(node, MEMBER_PROPERTY))
            if not children:
                # This is a leaf (Attribute)
                if node != section_iri:
                    leaves.add(node)
            else:
                stack.extend(children)

        return leaves

    # ── Mapping Record Extraction ─────────────────────────────────

    def get_mapping_for_concept_in_section(
        self,
        concept_iri: URIRef,
        section_iri: URIRef,
    ) -> Optional[MappingRecord]:
        """
        Find the DataMapping for a concept within a section context.
        """
        g = self._graph
        leaves = self._get_leaf_descendants(section_iri)

        for leaf in leaves:
            for mapping_iri in g.objects(leaf, HAS_MAPPING):
                # Check if this mapping relates to the concept
                if self._mapping_relates_to_concept(mapping_iri, concept_iri):
                    return self._build_mapping_record(mapping_iri)

        return None

    def get_parent_mapping(
        self, section_iri: URIRef
    ) -> Optional[MappingRecord]:
        """
        Find the parent-level DataMapping for a structural section.
        The parent mapping typically has an exactTBoxMatch.
        """
        g = self._graph

        # The section itself may have a hasMapping
        for mapping_iri in g.objects(section_iri, HAS_MAPPING):
            rec = self._build_mapping_record(mapping_iri)
            if rec.tbox_match is not None:
                return rec

        # Or the section's concept may have a mapping with a TBox match
        for concept in g.objects(section_iri, REPRESENTATION_OF):
            for mapping_iri in g.objects(concept, HAS_MAPPING):
                rec = self._build_mapping_record(mapping_iri)
                if rec.tbox_match is not None:
                    return rec

        return None

    def _mapping_relates_to_concept(
        self, mapping_iri: URIRef, concept_iri: URIRef
    ) -> bool:
        """Check if a DataMapping relates to a specific concept."""
        g = self._graph
        # The concept has hasMapping to this mapping
        if (concept_iri, HAS_MAPPING, mapping_iri) in g:
            return True
        # Or a representation of the concept has hasMapping
        for rep in g.subjects(REPRESENTATION_OF, concept_iri):
            if (rep, HAS_MAPPING, mapping_iri) in g:
                return True
        return False

    def _build_mapping_record(self, mapping_iri: URIRef) -> MappingRecord:
        """Build a MappingRecord from graph data."""
        g = self._graph

        tbox = self._single_or_none(g.objects(mapping_iri, EXACT_TBOX_MATCH))
        rbox = self._single_or_none(g.objects(mapping_iri, EXACT_RBOX_MATCH))
        abox = self._single_or_none(g.objects(mapping_iri, EXACT_ABOX_MATCH))
        parent = self._single_or_none(
            g.objects(mapping_iri, COMPOSITE_BROADER_MAPPING)
        )
        applicative = self._single_or_none(
            g.objects(mapping_iri, BROADER_APPLICATIVE)
        )
        children = tuple(g.objects(mapping_iri, COMPOSITE_NARROWER_MAPPING))

        weighting_lit = self._single_or_none(
            g.objects(mapping_iri, WEIGHTING)
        )
        weighting = int(weighting_lit) if weighting_lit else 50

        return MappingRecord(
            mapping_iri=mapping_iri,
            tbox_match=tbox,
            rbox_match=rbox,
            abox_match=abox,
            parent_mapping=parent,
            broader_applicative=applicative,
            children=children,
            weighting=weighting,
        )

    # ── Shadow Ontology Queries ───────────────────────────────────

    def get_shadow_for_entity(
        self, entity_iri: URIRef
    ) -> Optional[URIRef]:
        """Find the OwlAxiom shadow individual for a domain entity."""
        g = self._graph
        for shadow in g.subjects(SHADOW_OF, entity_iri):
            return shadow
        # Fallback: look up by IRI string
        iri_str = str(entity_iri)
        for shadow in g.subjects(IRI_PROP, Literal(iri_str, datatype=XSD.string)):
            if (shadow, RDF.type, OWL_AXIOM) in g:
                return shadow
        return None

    def get_shadow_domain(
        self, property_shadow: URIRef
    ) -> Optional[URIRef]:
        """Get the shadow domain class for a property shadow."""
        return self._single_or_none(
            self._graph.objects(property_shadow, SHADOW_DOMAIN)
        )

    def get_shadow_range(
        self, property_shadow: URIRef
    ) -> Optional[URIRef]:
        """Get the shadow range class for a property shadow."""
        return self._single_or_none(
            self._graph.objects(property_shadow, SHADOW_RANGE)
        )

    # ── Utility ───────────────────────────────────────────────────

    def _extract_observations_sparql(self) -> List[SectionObservationRecord]:
        """SPARQL-based extraction for remote endpoints."""
        raise NotImplementedError(
            "Remote SPARQL extraction not yet implemented; "
            "use local graph mode."
        )

    @staticmethod
    def _single_or_none(
        iterable: Iterable,
    ) -> Optional[Any]:
        """Return the single element of an iterable, or None."""
        result = None
        for item in iterable:
            if result is not None:
                # Multiple values — return the first
                return result
            result = item
        return result