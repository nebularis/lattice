"""
mork_communities/shadow.py

Shadow Ontology Builder: creates OwlAxiom shadow individuals for domain
ontology constructs, enabling DL-safe reasoning about mapping patterns.

Implements §10.3 of the addendum.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Dict, Optional, Set

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, SKOS

from mork_communities.namespaces import *

logger = logging.getLogger(__name__)


class ShadowOntologyBuilder:
    """
    Builds a shadow ontology σ(O) for a domain ontology O.

    Each named class, object property, and data property in O
    gets an OwlAxiom shadow individual in the MORK graph, carrying
    the IRI, label, type classification, and structural hierarchy
    (shadowSubClassOf, shadowDomain, shadowRange).

    All references from community projections point to these shadow
    individuals, not to the domain entities, ensuring OWL 2 DL safety.
    """

    def __init__(
        self,
        mork_graph: Graph,
        ontological_scheme_iri: URIRef,
        shadow_namespace: str = "http://www.nebularis.org/shadow/",
    ):
        self._graph = mork_graph
        self._scheme_iri = ontological_scheme_iri
        self._ns = shadow_namespace
        self._shadow_map: Dict[URIRef, URIRef] = {}  # entity -> shadow

    @property
    def shadow_map(self) -> Dict[URIRef, URIRef]:
        """Mapping from domain entity IRIs to their shadow individuals."""
        return dict(self._shadow_map)

    def build_shadow(self, domain_ontology: Graph) -> Graph:
        """
        Build the complete shadow ontology for a domain ontology.

        Parameters
        ----------
        domain_ontology : Graph
            The domain ontology to shadow.

        Returns
        -------
        Graph
            The shadow triples (also added to self._graph).
        """
        shadow_graph = Graph()

        # Phase 1: Create shadow individuals for all named classes
        classes = self._extract_named_classes(domain_ontology)
        for cls_iri in classes:
            shadow_iri = self._get_or_create_shadow(
                cls_iri, OWL_CLASS, domain_ontology, shadow_graph
            )

        # Phase 2: Create shadow individuals for all named object properties
        obj_props = self._extract_named_properties(
            domain_ontology, OWL.ObjectProperty
        )
        for prop_iri in obj_props:
            shadow_iri = self._get_or_create_shadow(
                prop_iri, OWL_OBJECT_PROPERTY, domain_ontology, shadow_graph
            )

        # Phase 3: Create shadow individuals for all named data properties
        data_props = self._extract_named_properties(
            domain_ontology, OWL.DatatypeProperty
        )
        for prop_iri in data_props:
            shadow_iri = self._get_or_create_shadow(
                prop_iri, OWL_DATA_PROPERTY, domain_ontology, shadow_graph
            )

        # Phase 4: Build shadow hierarchy (subClassOf, subPropertyOf)
        self._build_class_hierarchy(domain_ontology, shadow_graph)
        self._build_property_hierarchy(domain_ontology, shadow_graph)

        # Phase 5: Build domain/range shadow links
        self._build_domain_range(domain_ontology, shadow_graph)

        # Merge into main graph
        for triple in shadow_graph:
            self._graph.add(triple)

        logger.info(
            "Built shadow ontology: %d classes, %d object properties, "
            "%d data properties, %d total shadow triples",
            len(classes),
            len(obj_props),
            len(data_props),
            len(shadow_graph),
        )

        return shadow_graph

    def get_shadow(self, entity_iri: URIRef) -> Optional[URIRef]:
        """
        Get the shadow individual for a domain entity, if it exists.
        """
        return self._shadow_map.get(entity_iri)

    def get_or_create_shadow_for_entity(
        self,
        entity_iri: URIRef,
        entity_type: URIRef,
        domain_ontology: Graph,
    ) -> URIRef:
        """
        Get or create a shadow for a specific entity.
        Useful for incremental shadow building.
        """
        shadow_graph = Graph()
        shadow = self._get_or_create_shadow(
            entity_iri, entity_type, domain_ontology, shadow_graph
        )
        for triple in shadow_graph:
            self._graph.add(triple)
        return shadow

    # ── Internal ──────────────────────────────────────────────────

    def _mint_shadow_iri(self, entity_iri: URIRef) -> URIRef:
        """
        Create a deterministic shadow IRI for a domain entity.
        Uses a hash to avoid IRI length issues.
        """
        local = str(entity_iri).split("#")[-1].split("/")[-1]
        # Include full IRI hash for uniqueness
        h = hashlib.sha256(str(entity_iri).encode()).hexdigest()[:12]
        return URIRef(f"{self._ns}{local}_{h}")

    def _get_or_create_shadow(
        self,
        entity_iri: URIRef,
        shadow_type: URIRef,
        domain_ontology: Graph,
        shadow_graph: Graph,
    ) -> URIRef:
        """Get existing or create new shadow individual."""
        if entity_iri in self._shadow_map:
            return self._shadow_map[entity_iri]

        shadow_iri = self._mint_shadow_iri(entity_iri)
        self._shadow_map[entity_iri] = shadow_iri

        # Type assertions
        shadow_graph.add((shadow_iri, RDF.type, OWL_AXIOM))
        shadow_graph.add((shadow_iri, RDF.type, shadow_type))

        # IRI and name
        shadow_graph.add(
            (shadow_iri, IRI_PROP, Literal(str(entity_iri), datatype=XSD.string))
        )
        local_name = str(entity_iri).split("#")[-1].split("/")[-1]
        shadow_graph.add(
            (shadow_iri, CONCEPT_NAME, Literal(local_name, datatype=XSD.string))
        )

        # Labels from domain ontology
        for label in domain_ontology.objects(entity_iri, RDFS.label):
            shadow_graph.add((shadow_iri, SKOS.prefLabel, label))

        # Scheme membership
        shadow_graph.add(
            (shadow_iri, SKOS.inScheme, self._scheme_iri)
        )
        shadow_graph.add(
            (shadow_iri, ONTOLOGICAL_SCHEME_PROP, self._scheme_iri)
        )

        # Referential link (NOT owl:sameAs — see §10.3.3)
        shadow_graph.add((shadow_iri, SHADOW_OF, entity_iri))

        return shadow_iri

    def _extract_named_classes(self, ontology: Graph) -> Set[URIRef]:
        """Extract all named OWL classes from an ontology."""
        classes = set()
        for cls in ontology.subjects(RDF.type, OWL.Class):
            if isinstance(cls, URIRef):
                classes.add(cls)
        return classes

    def _extract_named_properties(
        self, ontology: Graph, prop_type: URIRef
    ) -> Set[URIRef]:
        """Extract all named properties of a given type."""
        props = set()
        for prop in ontology.subjects(RDF.type, prop_type):
            if isinstance(prop, URIRef):
                props.add(prop)
        return props

    def _build_class_hierarchy(
        self, domain_ontology: Graph, shadow_graph: Graph
    ) -> None:
        """
        Build shadowSubClassOf links mirroring rdfs:subClassOf.
        Only direct (non-inferred) subclass assertions are mirrored.
        """
        for sub, _, sup in domain_ontology.triples(
            (None, RDFS.subClassOf, None)
        ):
            if isinstance(sub, URIRef) and isinstance(sup, URIRef):
                sub_shadow = self._shadow_map.get(sub)
                sup_shadow = self._shadow_map.get(sup)
                if sub_shadow and sup_shadow:
                    shadow_graph.add(
                        (sub_shadow, SHADOW_SUB_CLASS_OF, sup_shadow)
                    )

    def _build_property_hierarchy(
        self, domain_ontology: Graph, shadow_graph: Graph
    ) -> None:
        """Build shadowSubPropertyOf links."""
        for sub, _, sup in domain_ontology.triples(
            (None, RDFS.subPropertyOf, None)
        ):
            if isinstance(sub, URIRef) and isinstance(sup, URIRef):
                sub_shadow = self._shadow_map.get(sub)
                sup_shadow = self._shadow_map.get(sup)
                if sub_shadow and sup_shadow:
                    shadow_graph.add(
                        (sub_shadow, SHADOW_SUB_PROPERTY_OF, sup_shadow)
                    )

    def _build_domain_range(
        self, domain_ontology: Graph, shadow_graph: Graph
    ) -> None:
        """Build shadowDomain and shadowRange links."""
        # Domain
        for prop, _, domain_cls in domain_ontology.triples(
            (None, RDFS.domain, None)
        ):
            if isinstance(prop, URIRef) and isinstance(domain_cls, URIRef):
                prop_shadow = self._shadow_map.get(prop)
                cls_shadow = self._shadow_map.get(domain_cls)
                if prop_shadow and cls_shadow:
                    shadow_graph.add(
                        (prop_shadow, SHADOW_DOMAIN, cls_shadow)
                    )

        # Range
        for prop, _, range_cls in domain_ontology.triples(
            (None, RDFS.range, None)
        ):
            if isinstance(prop, URIRef) and isinstance(range_cls, URIRef):
                prop_shadow = self._shadow_map.get(prop)
                cls_shadow = self._shadow_map.get(range_cls)
                if prop_shadow and cls_shadow:
                    shadow_graph.add(
                        (prop_shadow, SHADOW_RANGE, cls_shadow)
                    )