"""
mork_communities/projections.py

Ontological Projections: confirmed mapping patterns extracted from
validated mapping runs.

Implements §10.6 of the addendum.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD, SKOS

from mork_communities.namespaces import *
from mork_communities.communities import SemanticCommunity, CommunityScheme
from mork_communities.matching import CommunityMatcher, CommunityMatchResult
from mork_communities.graph_client import (
    MorkGraphClient,
    SectionObservationRecord,
)
from mork_communities.shadow import ShadowOntologyBuilder

logger = logging.getLogger(__name__)


@dataclass
class PropertyProjection:
    """
    A confirmed concept-to-property mapping pattern.

    Attributes
    ----------
    concept_iri : URIRef
        The DataConcept.
    property_shadow : URIRef
        The OwlAxiom shadow of the R-Box property.
    parent_class_shadow : URIRef
        The OwlAxiom shadow of the parent T-Box class.
    frequency : int
        How many times this pattern was observed.
    confidence : float
        frequency / total observations for this concept in this community.
    iri : Optional[URIRef]
        IRI in the MORK graph after materialisation.
    """

    concept_iri: URIRef
    property_shadow: URIRef
    parent_class_shadow: URIRef
    frequency: int = 0
    confidence: float = 0.0
    iri: Optional[URIRef] = None


@dataclass
class DAGTemplate:
    """
    A normalised compositional mapping pattern.
    """

    root_class_shadow: URIRef
    children: List[PropertyProjection] = field(default_factory=list)
    frequency: int = 0
    signature: str = ""
    iri: Optional[URIRef] = None


@dataclass
class OntologicalProjection:
    """
    The confirmed mapping pattern for a community.

    T_C: projected classes with frequencies
    R_C: property projections per concept
    D_C: DAG templates
    """

    target_ontology: URIRef
    projected_classes: Dict[URIRef, int] = field(default_factory=dict)
    property_projections: List[PropertyProjection] = field(
        default_factory=list
    )
    dag_templates: List[DAGTemplate] = field(default_factory=list)
    iri: Optional[URIRef] = None


class ProjectionExtractor:
    """
    Extracts ontological projections from confirmed mapping runs.

    Implements the ExtractOntologicalProjection algorithm (§2.2 of the
    ontologic mapping addendum).
    """

    def __init__(
        self,
        graph_client: MorkGraphClient,
        shadow_builder: ShadowOntologyBuilder,
        match_threshold: float = 0.3,
        min_frequency: int = 2,
    ):
        self._client = graph_client
        self._shadow = shadow_builder
        self._match_threshold = match_threshold
        self._min_freq = min_frequency

    def extract_projection(
        self,
        community: SemanticCommunity,
        matcher: CommunityMatcher,
        observations: List[SectionObservationRecord],
        target_ontology_iri: URIRef,
    ) -> OntologicalProjection:
        """
        Extract the ontological projection for a community.

        For each section observation matching the community, extract:
        - The parent T-Box class (via exactTBoxMatch on the parent mapping)
        - The R-Box property for each concept (via exactRBoxMatch)
        - The DAG shape
        """
        tbox_counter: Counter = Counter()
        rbox_data: Dict[
            URIRef, Counter
        ] = defaultdict(Counter)  # concept -> {(prop_shadow, class_shadow): count}
        dag_signatures: Counter = Counter()
        concept_total_obs: Counter = Counter()

        for obs in observations:
            # Check if this observation matches the community
            match = matcher.match(obs.concepts)
            if match is None or match.confidence < self._match_threshold:
                continue
            if match.community.community_id != community.community_id:
                continue

            # Find the parent mapping for this section
            parent_mapping = self._client.get_parent_mapping(obs.section_iri)
            if parent_mapping is None:
                continue

            # Extract T-Box class
            if parent_mapping.tbox_match is not None:
                tbox_shadow = self._shadow.get_shadow(
                    parent_mapping.tbox_match
                )
                if tbox_shadow is not None:
                    tbox_counter[tbox_shadow] += 1

                    # Extract R-Box mappings for each concept
                    for concept_iri in obs.concepts:
                        if concept_iri not in community.members:
                            continue

                        concept_total_obs[concept_iri] += 1

                        field_mapping = (
                            self._client.get_mapping_for_concept_in_section(
                                concept_iri, obs.section_iri
                            )
                        )
                        if field_mapping is None:
                            continue

                        rbox_target = field_mapping.rbox_match
                        if rbox_target is not None:
                            rbox_shadow = self._shadow.get_shadow(rbox_target)
                            if rbox_shadow is not None:
                                rbox_data[concept_iri][
                                    (rbox_shadow, tbox_shadow)
                                ] += 1

                    # Extract DAG signature
                    sig = self._extract_dag_signature(
                        parent_mapping, tbox_shadow
                    )
                    if sig:
                        dag_signatures[sig] += 1

        # Build the projection
        projection = OntologicalProjection(
            target_ontology=target_ontology_iri
        )

        # Projected classes (filter by min frequency)
        for cls_shadow, count in tbox_counter.items():
            if count >= self._min_freq:
                projection.projected_classes[cls_shadow] = count

        # Property projections
        for concept_iri, counter in rbox_data.items():
            total_for_concept = concept_total_obs[concept_iri]
            for (prop_shadow, parent_shadow), count in counter.items():
                if count >= self._min_freq:
                    confidence = (
                        count / total_for_concept
                        if total_for_concept > 0
                        else 0.0
                    )
                    pp = PropertyProjection(
                        concept_iri=concept_iri,
                        property_shadow=prop_shadow,
                        parent_class_shadow=parent_shadow,
                        frequency=count,
                        confidence=confidence,
                    )
                    projection.property_projections.append(pp)

        # DAG templates (top 3)
        for sig, count in dag_signatures.most_common(3):
            if count >= self._min_freq:
                template = self._build_dag_template_from_signature(
                    sig, count, projection.property_projections
                )
                if template:
                    projection.dag_templates.append(template)

        logger.info(
            "Extracted projection for community %s: %d classes, "
            "%d property projections, %d DAG templates",
            community.community_id,
            len(projection.projected_classes),
            len(projection.property_projections),
            len(projection.dag_templates),
        )

        return projection

    def _extract_dag_signature(
        self,
        parent_mapping,
        tbox_shadow: URIRef,
    ) -> Optional[str]:
        """
        Extract a normalised DAG signature from a parent mapping.
        Signature format: "root:IRI|child1_prop:IRI|child2_prop:IRI|..."
        """
        parts = [f"root:{tbox_shadow}"]

        for child_iri in parent_mapping.children:
            child_rec = self._client._build_mapping_record(child_iri)
            if child_rec.rbox_match is not None:
                rbox_shadow = self._shadow.get_shadow(child_rec.rbox_match)
                if rbox_shadow:
                    parts.append(f"child:{rbox_shadow}")

        if len(parts) <= 1:
            return None

        # Sort children for normalisation
        parts[1:] = sorted(parts[1:])
        return "|".join(parts)

    def _build_dag_template_from_signature(
        self,
        signature: str,
        frequency: int,
        property_projections: List[PropertyProjection],
    ) -> Optional[DAGTemplate]:
        """Build a DAGTemplate from a normalised signature."""
        parts = signature.split("|")
        if not parts:
            return None

        root_part = parts[0]
        if not root_part.startswith("root:"):
            return None

        root_shadow = URIRef(root_part[5:])

        # Find matching property projections for children
        child_shadows = set()
        for part in parts[1:]:
            if part.startswith("child:"):
                child_shadows.add(URIRef(part[6:]))

        matching_children = [
            pp
            for pp in property_projections
            if pp.property_shadow in child_shadows
            and pp.parent_class_shadow == root_shadow
        ]

        return DAGTemplate(
            root_class_shadow=root_shadow,
            children=matching_children,
            frequency=frequency,
            signature=signature,
        )


class ProjectionMaterialiser:
    """
    Materialises OntologicalProjection instances into the MORK RDF graph.
    """

    def __init__(
        self,
        graph: Graph,
        base_namespace: str = "http://www.nebularis.org/projections/",
    ):
        self._graph = graph
        self._ns = base_namespace

    def materialise(
        self,
        community: SemanticCommunity,
        projection: OntologicalProjection,
    ) -> URIRef:
        """
        Write an OntologicalProjection to the graph and link it
        to its community.
        """
        g = self._graph

        # Create projection IRI
        proj_iri = URIRef(
            f"{self._ns}projection/{community.community_id}"
        )
        projection.iri = proj_iri

        g.add((proj_iri, RDF.type, ONTOLOGICAL_PROJECTION))
        g.add(
            (proj_iri, PROJECTION_TARGET_ONTOLOGY, projection.target_ontology)
        )

        # Link community to projection
        if community.iri:
            g.add((community.iri, HAS_ONTOLOGICAL_PROJECTION, proj_iri))

        # Projected classes
        for cls_shadow, freq in projection.projected_classes.items():
            g.add((proj_iri, PROJECTED_CLASS, cls_shadow))
        # Store the frequency of the most common class
        if projection.projected_classes:
            max_freq = max(projection.projected_classes.values())
            g.add(
                (
                    proj_iri,
                    PROJECTED_CLASS_FREQUENCY,
                    Literal(max_freq, datatype=XSD.integer),
                )
            )

        # Property projections
        for idx, pp in enumerate(projection.property_projections):
            pp_iri = URIRef(f"{proj_iri}/pp/{idx}")
            pp.iri = pp_iri

            g.add((pp_iri, RDF.type, PROPERTY_PROJECTION))
            g.add((proj_iri, HAS_PROPERTY_PROJECTION, pp_iri))
            g.add((pp_iri, PROJECTED_CONCEPT, pp.concept_iri))
            g.add((pp_iri, PROJECTED_PROPERTY, pp.property_shadow))
            g.add((pp_iri, PROJECTED_PARENT_CLASS, pp.parent_class_shadow))
            g.add(
                (
                    pp_iri,
                    PROPERTY_PROJECTION_FREQUENCY,
                    Literal(pp.frequency, datatype=XSD.integer),
                )
            )
            g.add(
                (
                    pp_iri,
                    PROPERTY_PROJECTION_CONFIDENCE,
                    Literal(
                        round(pp.confidence, 4), datatype=XSD.decimal
                    ),
                )
            )

        # DAG templates
        for idx, dt in enumerate(projection.dag_templates):
            dt_iri = URIRef(f"{proj_iri}/dag/{idx}")
            dt.iri = dt_iri

            g.add((dt_iri, RDF.type, DAG_TEMPLATE))
            g.add((dt_iri, RDF.type, SKOS.Collection))
            g.add((proj_iri, HAS_DAG_TEMPLATE, dt_iri))
            g.add((dt_iri, DAG_TEMPLATE_ROOT, dt.root_class_shadow))
            g.add(
                (
                    dt_iri,
                    DAG_TEMPLATE_FREQUENCY,
                    Literal(dt.frequency, datatype=XSD.integer),
                )
            )

            for child_pp in dt.children:
                if child_pp.iri:
                    g.add((dt_iri, DAG_TEMPLATE_CHILD, child_pp.iri))

        logger.info(
            "Materialised projection %s for community %s",
            proj_iri,
            community.community_id,
        )

        return proj_iri