"""
mork_communities/pipeline.py

The orchestration layer: ties together community discovery, shadow ontology
building, projection extraction, and tri-stratum resolution into a coherent
pipeline that integrates with the MORK phased mapping protocol.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from mork_communities.communities import (
    CommunityDiscovery,
    CommunityMaterialiser,
    CommunityScheme,
    SemanticCommunity,
)
from mork_communities.graph_client import (
    MorkGraphClient,
    SectionObservationRecord,
)
from mork_communities.incremental import IncrementalUpdater
from mork_communities.inference import (
    SectionResolution,
    TriStratumResolver,
    ResolutionReporter,
)
from mork_communities.matching import CommunityMatcher
from mork_communities.projections import (
    OntologicalProjection,
    ProjectionExtractor,
    ProjectionMaterialiser,
)
from mork_communities.scoring import BayesianScorer, EvidenceSignal
from mork_communities.shadow import ShadowOntologyBuilder
from mork_communities.namespaces import (
    MORK,
    ONTOLOGICAL_SCHEME,
    REPRESENTATION_SCHEME,
    SECTION_OBSERVATION,
    OBSERVED_IN_SECTION,
    OBSERVED_IN_SCHEME,
    OBSERVED_CONCEPT,
    OBSERVATION_TIMESTAMP,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the community-enhanced pipeline."""

    # Community discovery
    resolution_min: float = 0.5
    resolution_max: float = 2.0
    resolution_steps: int = 10
    min_community_size: int = 2
    coherence_threshold: float = 0.3
    quality_weights: Tuple[float, float, float] = (0.3, 0.4, 0.3)

    # Matching
    community_match_threshold: float = 0.3
    use_bayesian_matching: bool = True

    # Scoring
    auto_threshold: float = 3.0
    high_confidence_threshold: float = 2.0
    moderate_threshold: float = 1.0
    estimated_property_count: int = 15

    # Projection
    projection_min_frequency: int = 2

    # Incremental updates
    redetection_threshold: int = 50
    coverage_threshold: float = 0.7
    weight_learning_rate: float = 0.1

    # Namespaces
    shadow_namespace: str = "http://www.nebularis.org/shadow/"
    community_namespace: str = "http://www.nebularis.org/communities/"
    projection_namespace: str = "http://www.nebularis.org/projections/"


@dataclass
class PipelineState:
    """Mutable state of the pipeline across mapping runs."""

    community_scheme: Optional[CommunityScheme] = None
    projections: Dict[str, OntologicalProjection] = field(
        default_factory=dict
    )
    shadow_builder: Optional[ShadowOntologyBuilder] = None
    observation_count: int = 0
    mapping_run_count: int = 0


class CommunityEnhancedPipeline:
    """
    Main orchestration class for the community-enhanced mapping pipeline.
    See module docstring and §10.11 of the addendum for architecture.
    """

    def __init__(
        self,
        mork_graph: Graph,
        config: Optional[PipelineConfig] = None,
    ):
        self._graph = mork_graph
        self._config = config or PipelineConfig()
        self._client = MorkGraphClient(graph=mork_graph)
        self._state = PipelineState()
        self._resolver: Optional[TriStratumResolver] = None
        self._updater: Optional[IncrementalUpdater] = None

    @property
    def state(self) -> PipelineState:
        return self._state

    @property
    def has_communities(self) -> bool:
        return (
            self._state.community_scheme is not None
            and len(self._state.community_scheme.communities) > 0
        )

    # ── Initialisation ────────────────────────────────────────────

    def initialise(
        self,
        domain_ontology: Graph,
        ontological_scheme_iri: URIRef,
    ) -> None:
        """
        Initialise the pipeline with a domain ontology.
        Builds shadow ontology, discovers communities, extracts projections.
        """
        logger.info("Initialising community-enhanced pipeline")

        # Step 1: Build shadow ontology
        self._state.shadow_builder = ShadowOntologyBuilder(
            mork_graph=self._graph,
            ontological_scheme_iri=ontological_scheme_iri,
            shadow_namespace=self._config.shadow_namespace,
        )
        shadow_graph = self._state.shadow_builder.build_shadow(domain_ontology)
        logger.info(
            "Shadow ontology: %d triples, %d shadows",
            len(shadow_graph),
            len(self._state.shadow_builder.shadow_map),
        )

        # Step 2: Discover communities (if sufficient data)
        self._discover_communities()

        # Step 3: Extract projections (if communities exist)
        if self.has_communities:
            self._extract_all_projections(ontological_scheme_iri)

        # Step 4: Build resolver
        self._build_resolver()

        logger.info(
            "Pipeline initialised: %d communities, %d projections",
            len(self._state.community_scheme.communities)
            if self._state.community_scheme
            else 0,
            len(self._state.projections),
        )

    # ── Resolution (Phase 0 Enhancement) ──────────────────────────

    def resolve_section(
        self,
        section_iri: URIRef,
        token_candidates: Dict[URIRef, List[Tuple[URIRef, float]]],
        token_names: Dict[URIRef, str],
        recognised_concepts: Optional[FrozenSet[URIRef]] = None,
        base_signals: Optional[
            Dict[URIRef, Dict[URIRef, List[EvidenceSignal]]]
        ] = None,
    ) -> SectionResolution:
        """
        Resolve all tokens in a section using the tri-stratum pipeline.
        Called during Phase 0 of the mapping protocol.
        """
        if self._resolver is None:
            self._build_resolver()

        return self._resolver.resolve_section(
            section_iri=section_iri,
            token_candidates=token_candidates,
            token_names=token_names,
            recognised_concepts=recognised_concepts,
            base_signals=base_signals,
        )

    # ── Post-Mapping Update ───────────────────────────────────────

    def post_mapping_update(
        self,
        new_observations: List[SectionObservationRecord],
        confirmed_mappings: Optional[
            List[Tuple[URIRef, URIRef, URIRef, str]]
        ] = None,
        ontological_scheme_iri: Optional[URIRef] = None,
    ) -> None:
        """
        Update communities and projections after a validated mapping run.
        """
        self._state.mapping_run_count += 1
        self._state.observation_count += len(new_observations)

        logger.info(
            "Post-mapping update: run #%d, %d new observations",
            self._state.mapping_run_count,
            len(new_observations),
        )

        # Update projections with confirmed mappings
        if confirmed_mappings and self._state.shadow_builder:
            for concept, prop_entity, parent_entity, comm_id in confirmed_mappings:
                prop_shadow = self._state.shadow_builder.get_shadow(prop_entity)
                parent_shadow = self._state.shadow_builder.get_shadow(parent_entity)

                if prop_shadow and parent_shadow and self._updater:
                    community = None
                    if self._state.community_scheme:
                        for c in self._state.community_scheme.communities:
                            if c.community_id == comm_id:
                                community = c
                                break
                    if community:
                        self._updater.update_projection(
                            community, concept, prop_shadow, parent_shadow
                        )

        # Incremental community update
        if self._updater:
            needs_redetect, _ = self._updater.process_new_observations(
                new_observations
            )
            if needs_redetect:
                self._discover_communities()
                if ontological_scheme_iri and self.has_communities:
                    self._extract_all_projections(ontological_scheme_iri)
                self._build_resolver()

        # Materialise observations
        self._materialise_observations(new_observations)

    # ── Internal ──────────────────────────────────────────────────

    def _discover_communities(self) -> None:
        """Run community discovery on accumulated observations."""
        discovery = CommunityDiscovery(
            graph_client=self._client,
            resolution_min=self._config.resolution_min,
            resolution_max=self._config.resolution_max,
            resolution_steps=self._config.resolution_steps,
            min_community_size=self._config.min_community_size,
            coherence_threshold=self._config.coherence_threshold,
            quality_weights=self._config.quality_weights,
            match_threshold=self._config.community_match_threshold,
        )

        observations = self._client.extract_section_observations()
        scheme = discovery.discover(observations)
        self._state.community_scheme = scheme

        if scheme.communities:
            materialiser = CommunityMaterialiser(
                self._graph,
                base_namespace=self._config.community_namespace,
            )
            materialiser.materialise_scheme(scheme)

        self._updater = IncrementalUpdater(
            graph_client=self._client,
            current_scheme=scheme,
            current_projections=self._state.projections,
            redetection_threshold=self._config.redetection_threshold,
            coverage_threshold=self._config.coverage_threshold,
            weight_learning_rate=self._config.weight_learning_rate,
        )

    def _extract_all_projections(
        self, ontological_scheme_iri: URIRef
    ) -> None:
        """Extract ontological projections for all communities."""
        if not self.has_communities or self._state.shadow_builder is None:
            return

        scheme = self._state.community_scheme
        observations = self._client.extract_section_observations()

        matcher = CommunityMatcher(
            scheme=scheme,
            match_threshold=self._config.community_match_threshold,
            use_bayesian=self._config.use_bayesian_matching,
        )

        extractor = ProjectionExtractor(
            graph_client=self._client,
            shadow_builder=self._state.shadow_builder,
            match_threshold=self._config.community_match_threshold,
            min_frequency=self._config.projection_min_frequency,
        )

        proj_materialiser = ProjectionMaterialiser(
            self._graph,
            base_namespace=self._config.projection_namespace,
        )

        self._state.projections.clear()

        for community in scheme.communities:
            projection = extractor.extract_projection(
                community=community,
                matcher=matcher,
                observations=observations,
                target_ontology_iri=ontological_scheme_iri,
            )

            if projection.projected_classes or projection.property_projections:
                self._state.projections[community.community_id] = projection
                proj_materialiser.materialise(community, projection)

        logger.info(
            "Extracted projections for %d / %d communities",
            len(self._state.projections),
            len(scheme.communities),
        )

    def _build_resolver(self) -> None:
        """Build or rebuild the TriStratumResolver."""
        scheme = self._state.community_scheme
        if scheme is None:
            scheme = CommunityScheme(
                version="empty", algorithm="none", resolution=0.0
            )

        scorer = BayesianScorer(
            auto_threshold=self._config.auto_threshold,
            high_confidence_threshold=self._config.high_confidence_threshold,
            moderate_threshold=self._config.moderate_threshold,
            estimated_property_count=self._config.estimated_property_count,
        )

        self._resolver = TriStratumResolver(
            community_scheme=scheme,
            projections=self._state.projections,
            scorer=scorer,
            community_match_threshold=self._config.community_match_threshold,
            use_bayesian_matching=self._config.use_bayesian_matching,
        )

    def _materialise_observations(
        self, observations: List[SectionObservationRecord]
    ) -> None:
        """Write SectionObservation individuals to the graph."""
        for obs in observations:
            obs_iri = URIRef(
                f"{self._config.community_namespace}observation/"
                f"{str(obs.section_iri).split('/')[-1].split('#')[-1]}_"
                f"{self._state.mapping_run_count}"
            )

            self._graph.add((obs_iri, RDF.type, SECTION_OBSERVATION))
            self._graph.add((obs_iri, OBSERVED_IN_SECTION, obs.section_iri))
            self._graph.add((obs_iri, OBSERVED_IN_SCHEME, obs.scheme_iri))
            for concept in obs.concepts:
                self._graph.add((obs_iri, OBSERVED_CONCEPT, concept))
            self._graph.add(
                (
                    obs_iri,
                    OBSERVATION_TIMESTAMP,
                    Literal(
                        datetime.now(timezone.utc).isoformat(),
                        datatype=XSD.dateTime,
                    ),
                )
            )

    # ── Diagnostics ───────────────────────────────────────────────

    def get_diagnostics(self) -> Dict:
        """Return pipeline diagnostics for monitoring."""
        scheme = self._state.community_scheme
        diag = {
            "mapping_run_count": self._state.mapping_run_count,
            "total_observations": self._state.observation_count,
            "has_communities": self.has_communities,
            "community_count": len(scheme.communities) if scheme else 0,
            "projection_count": len(self._state.projections),
            "shadow_entity_count": (
                len(self._state.shadow_builder.shadow_map)
                if self._state.shadow_builder
                else 0
            ),
        }

        if scheme and scheme.communities:
            coherences = [c.coherence for c in scheme.communities]
            diag["mean_coherence"] = sum(coherences) / len(coherences)
            diag["max_coherence"] = max(coherences)
            diag["min_coherence"] = min(coherences)
            diag["algorithm"] = scheme.algorithm
            diag["resolution"] = scheme.resolution

            communities_with_proj = sum(
                1
                for c in scheme.communities
                if c.community_id in self._state.projections
            )
            diag["projection_coverage"] = (
                communities_with_proj / len(scheme.communities)
            )

            all_confs = []
            for proj in self._state.projections.values():
                for pp in proj.property_projections:
                    all_confs.append(pp.confidence)
            if all_confs:
                diag["mean_projection_confidence"] = (
                    sum(all_confs) / len(all_confs)
                )
                diag["high_confidence_projections"] = sum(
                    1 for c in all_confs if c >= 0.9
                )
                diag["total_property_projections"] = len(all_confs)

        return diag

    def get_community_summary(self) -> List[Dict]:
        """Return a summary of all communities for reporting."""
        if not self.has_communities:
            return []

        summaries = []
        for comm in self._state.community_scheme.communities:
            proj = self._state.projections.get(comm.community_id)

            top_members = sorted(
                comm.members.items(), key=lambda x: x[1], reverse=True
            )[:10]

            summary = {
                "community_id": comm.community_id,
                "size": comm.size,
                "coherence": round(comm.coherence, 4),
                "observation_count": comm.observation_count,
                "top_members": [
                    {
                        "concept": str(c).split("/")[-1].split("#")[-1],
                        "weight": round(w, 4),
                    }
                    for c, w in top_members
                ],
                "has_projection": proj is not None,
            }

            if proj:
                summary["projected_classes"] = len(proj.projected_classes)
                summary["property_projections"] = len(proj.property_projections)
                summary["dag_templates"] = len(proj.dag_templates)

                if proj.projected_classes:
                    max_freq = max(proj.projected_classes.values())
                    total_freq = sum(proj.projected_classes.values())
                    summary["ontological_coherence"] = round(
                        max_freq / total_freq, 4
                    )

            summaries.append(summary)

        return summaries