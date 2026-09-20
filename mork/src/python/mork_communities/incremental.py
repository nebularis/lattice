"""
mork_communities/incremental.py

Incremental community and projection updates after each mapping run.

Implements §6.2 of the communities paper (incremental update) and
handles the learning loop described in §12 of the superposition theory.
"""

from __future__ import annotations

import logging
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from rdflib import URIRef

from mork_communities.communities import (
    SemanticCommunity,
    CommunityScheme,
    CommunityDiscovery,
    CommunityMaterialiser,
)
from mork_communities.projections import (
    OntologicalProjection,
    PropertyProjection,
    ProjectionExtractor,
    ProjectionMaterialiser,
)
from mork_communities.matching import CommunityMatcher
from mork_communities.graph_client import (
    MorkGraphClient,
    SectionObservationRecord,
)

logger = logging.getLogger(__name__)


class IncrementalUpdater:
    """
    Handles incremental updates to communities and projections
    after each completed mapping run.

    Decides whether to:
    1. Incrementally update existing community weights (fast)
    2. Trigger a full community re-detection (expensive but thorough)
    3. Update ontological projections with new confirmed patterns
    """

    def __init__(
        self,
        graph_client: MorkGraphClient,
        current_scheme: CommunityScheme,
        current_projections: Dict[str, OntologicalProjection],
        redetection_threshold: int = 50,
        coverage_threshold: float = 0.7,
        weight_learning_rate: float = 0.1,
        new_member_threshold: float = 0.3,
    ):
        self._client = graph_client
        self._scheme = current_scheme
        self._projections = current_projections
        self._redetect_thresh = redetection_threshold
        self._coverage_thresh = coverage_threshold
        self._eta = weight_learning_rate
        self._new_member_thresh = new_member_threshold
        self._new_obs_count = 0
        self._unmatched_observations: List[SectionObservationRecord] = []

    def process_new_observations(
        self,
        new_observations: List[SectionObservationRecord],
    ) -> Tuple[bool, Optional[CommunityScheme]]:
        """
        Process new section observations from a completed mapping run.

        Returns
        -------
        (needs_redetection, updated_scheme)
            If needs_redetection is True, the scheme was rebuilt from scratch.
            Otherwise, weights were updated incrementally.
        """
        self._new_obs_count += len(new_observations)

        matcher = CommunityMatcher(self._scheme, use_bayesian=True)

        for obs in new_observations:
            match = matcher.match(obs.concepts)

            if match is not None and match.confidence >= self._coverage_thresh:
                # Incrementally update the matched community
                self._update_community_weights(match.community, obs)
            else:
                # Observation doesn't match well
                self._unmatched_observations.append(obs)

                # Check for novel concepts
                all_known = set()
                for comm in self._scheme.communities:
                    all_known.update(comm.member_set)
                novel = obs.concepts - all_known
                if novel:
                    logger.info(
                        "Novel concepts detected: %s",
                        [str(c).split("/")[-1] for c in novel],
                    )

        # Check if full re-detection is needed
        needs_redetect = self._should_redetect()

        if needs_redetect:
            logger.info(
                "Triggering full community re-detection "
                "(%d new observations, %d unmatched)",
                self._new_obs_count,
                len(self._unmatched_observations),
            )
            # Caller should run CommunityDiscovery.discover()
            return True, None

        return False, self._scheme

    def _update_community_weights(
        self,
        community: SemanticCommunity,
        observation: SectionObservationRecord,
    ) -> None:
        """
        Incrementally update community membership weights
        using exponential moving average.
        """
        community.observation_count += 1

        for concept_iri in list(community.members.keys()):
            old_weight = community.members[concept_iri]
            present = 1.0 if concept_iri in observation.concepts else 0.0
            new_weight = (1 - self._eta) * old_weight + self._eta * present
            community.members[concept_iri] = new_weight

        # Check for new members
        for concept_iri in observation.concepts:
            if concept_iri not in community.members:
                # Compute co-occurrence with existing members
                co_occurrence = self._compute_cooccurrence_with_community(
                    concept_iri, community, observation
                )
                if co_occurrence >= self._new_member_thresh:
                    community.members[concept_iri] = self._eta
                    logger.debug(
                        "Added new member %s to community %s",
                        concept_iri,
                        community.community_id,
                    )

    def _compute_cooccurrence_with_community(
        self,
        concept_iri: URIRef,
        community: SemanticCommunity,
        observation: SectionObservationRecord,
    ) -> float:
        """
        Compute how well a new concept co-occurs with the community.
        Returns the fraction of community core members present in the
        same observation.
        """
        core_members = {
            c for c, w in community.members.items() if w >= 0.5
        }
        if not core_members:
            return 0.0

        present_core = core_members & observation.concepts
        return len(present_core) / len(core_members)

    def _should_redetect(self) -> bool:
        """Check if full re-detection is needed."""
        # Condition 1: Too many new observations
        if self._new_obs_count >= self._redetect_thresh:
            return True

        # Condition 2: Too many unmatched observations
        if self._new_obs_count > 0:
            unmatched_rate = len(self._unmatched_observations) / self._new_obs_count
            if unmatched_rate > (1 - self._coverage_thresh):
                return True

        return False

    def update_projection(
        self,
        community: SemanticCommunity,
        concept_iri: URIRef,
        property_shadow: URIRef,
        parent_class_shadow: URIRef,
    ) -> None:
        """
        Update a community's ontological projection with a new
        confirmed mapping.

        Called after a mapping run is validated.
        """
        comm_id = community.community_id
        projection = self._projections.get(comm_id)

        if projection is None:
            logger.warning(
                "No projection for community %s; skipping update", comm_id
            )
            return

        # Update projected class frequency
        if parent_class_shadow in projection.projected_classes:
            projection.projected_classes[parent_class_shadow] += 1
        else:
            projection.projected_classes[parent_class_shadow] = 1

        # Update or add property projection
        existing_pp = None
        for pp in projection.property_projections:
            if (
                pp.concept_iri == concept_iri
                and pp.property_shadow == property_shadow
                and pp.parent_class_shadow == parent_class_shadow
            ):
                existing_pp = pp
                break

        if existing_pp:
            existing_pp.frequency += 1
            # Recompute confidence
            total = sum(
                pp.frequency
                for pp in projection.property_projections
                if pp.concept_iri == concept_iri
            )
            existing_pp.confidence = existing_pp.frequency / total
        else:
            # New property projection
            total = (
                sum(
                    pp.frequency
                    for pp in projection.property_projections
                    if pp.concept_iri == concept_iri
                )
                + 1
            )
            pp = PropertyProjection(
                concept_iri=concept_iri,
                property_shadow=property_shadow,
                parent_class_shadow=parent_class_shadow,
                frequency=1,
                confidence=1.0 / total,
            )
            projection.property_projections.append(pp)

            # Recompute all confidences for this concept
            for existing in projection.property_projections:
                if existing.concept_iri == concept_iri:
                    existing.confidence = existing.frequency / total

        logger.debug(
            "Updated projection for %s in community %s: "
            "%s on %s (freq=%d)",
            concept_iri,
            comm_id,
            property_shadow,
            parent_class_shadow,
            existing_pp.frequency if existing_pp else 1,
        )