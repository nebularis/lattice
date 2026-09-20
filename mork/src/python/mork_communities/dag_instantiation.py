"""
mork_communities/dag_instantiation.py

DAGTemplate instantiation: when a community has a high-confidence
DAGTemplate, the entire section can be mapped deterministically
from the template without any LLM involvement.

Implements §12.3 of the reference architecture and the DAGTemplate
matching from §6.5 of the algorithms paper.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from mork_communities.projections import (
    DAGTemplate,
    OntologicalProjection,
    PropertyProjection,
)
from mork_communities.communities import SemanticCommunity
from mork_communities.matching import CommunityMatchResult
from mork_communities.namespaces import (
    DATA_MAPPING,
    EXACT_TBOX_MATCH,
    EXACT_RBOX_MATCH,
    COMPOSITE_NARROWER_MAPPING,
    BROADER_APPLICATIVE,
    MORK,
)

logger = logging.getLogger(__name__)


@dataclass
class InstantiatedMapping:
    """A mapping node instantiated from a DAGTemplate."""
    mapping_type: str  # "tbox", "rbox", "abox"
    target_class_shadow: Optional[URIRef] = None
    target_property_shadow: Optional[URIRef] = None
    source_field_iri: Optional[URIRef] = None
    source_field_name: Optional[str] = None
    concept_iri: Optional[URIRef] = None
    parent_mapping_index: Optional[int] = None
    resolution_method: str = "deterministic"
    confidence: float = 1.0


@dataclass
class DAGInstantiationResult:
    """Result of instantiating a DAGTemplate for a section."""
    template: DAGTemplate
    community: SemanticCommunity
    community_confidence: float
    mappings: List[InstantiatedMapping] = field(default_factory=list)
    unmatched_fields: List[URIRef] = field(default_factory=list)
    coverage: float = 0.0  # Fraction of fields covered

    @property
    def is_complete(self) -> bool:
        """Whether all fields in the section are covered."""
        return len(self.unmatched_fields) == 0 and self.coverage >= 0.9


class DAGTemplateInstantiator:
    """
    Instantiates DAGTemplates for sections where the community
    and projection provide complete coverage.

    This is the primary mechanism for deterministic resolution
    at steady state (§12.3 of the reference architecture).
    """

    def __init__(
        self,
        min_template_frequency: int = 3,
        min_coverage: float = 0.8,
    ):
        self._min_freq = min_template_frequency
        self._min_coverage = min_coverage

    def try_instantiate(
        self,
        community_match: CommunityMatchResult,
        projection: OntologicalProjection,
        token_concepts: Dict[URIRef, URIRef],
        token_names: Dict[URIRef, str],
    ) -> Optional[DAGInstantiationResult]:
        """
        Try to instantiate a DAGTemplate for a section.

        Parameters
        ----------
        community_match : CommunityMatchResult
            The community match for this section.
        projection : OntologicalProjection
            The ontological projection for the matched community.
        token_concepts : Dict[URIRef, URIRef]
            Map from token IRI to best-match concept IRI.
        token_names : Dict[URIRef, str]
            Map from token IRI to field name.

        Returns
        -------
        DAGInstantiationResult or None
            The instantiated mappings, or None if template doesn't cover enough.
        """
        if not projection.dag_templates:
            return None

        # Find the best template
        best_template = None
        best_coverage = 0.0

        for template in projection.dag_templates:
            if template.frequency < self._min_freq:
                continue

            coverage = self._compute_template_coverage(
                template, projection, token_concepts
            )
            if coverage > best_coverage:
                best_coverage = coverage
                best_template = template

        if best_template is None or best_coverage < self._min_coverage:
            return None

        # Instantiate the template
        result = DAGInstantiationResult(
            template=best_template,
            community=community_match.community,
            community_confidence=community_match.confidence,
            coverage=best_coverage,
        )

        # Create parent T-Box mapping
        parent_mapping = InstantiatedMapping(
            mapping_type="tbox",
            target_class_shadow=best_template.root_class_shadow,
            resolution_method="deterministic",
            confidence=community_match.confidence,
        )
        result.mappings.append(parent_mapping)
        parent_idx = 0

        # Create child R-Box mappings
        matched_tokens = set()
        for token_iri, concept_iri in token_concepts.items():
            # Find property projection for this concept
            pp = self._find_property_projection(
                concept_iri, best_template, projection
            )
            if pp is not None:
                child_mapping = InstantiatedMapping(
                    mapping_type="rbox",
                    target_property_shadow=pp.property_shadow,
                    target_class_shadow=pp.parent_class_shadow,
                    source_field_iri=token_iri,
                    source_field_name=token_names.get(token_iri),
                    concept_iri=concept_iri,
                    parent_mapping_index=parent_idx,
                    resolution_method="deterministic",
                    confidence=pp.confidence,
                )
                result.mappings.append(child_mapping)
                matched_tokens.add(token_iri)

        # Record unmatched fields
        result.unmatched_fields = [
            t for t in token_concepts if t not in matched_tokens
        ]

        logger.info(
            "Instantiated DAGTemplate (root=%s, freq=%d): "
            "%d/%d fields covered (%.0f%%)",
            best_template.root_class_shadow,
            best_template.frequency,
            len(matched_tokens),
            len(token_concepts),
            best_coverage * 100,
        )

        return result

    def _compute_template_coverage(
        self,
        template: DAGTemplate,
        projection: OntologicalProjection,
        token_concepts: Dict[URIRef, URIRef],
    ) -> float:
        """Compute what fraction of tokens are covered by the template."""
        if not token_concepts:
            return 0.0

        covered = 0
        for concept_iri in token_concepts.values():
            pp = self._find_property_projection(concept_iri, template, projection)
            if pp is not None:
                covered += 1

        return covered / len(token_concepts)

    def _find_property_projection(
        self,
        concept_iri: URIRef,
        template: DAGTemplate,
        projection: OntologicalProjection,
    ) -> Optional[PropertyProjection]:
        """Find the property projection for a concept in a template."""
        # First check template children
        for child_pp in template.children:
            if child_pp.concept_iri == concept_iri:
                return child_pp

        # Then check projection
        for pp in projection.property_projections:
            if (pp.concept_iri == concept_iri and
                    pp.parent_class_shadow == template.root_class_shadow):
                return pp

        return None