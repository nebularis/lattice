"""
mork_communities/scoring.py

Bayesian scoring with community and projection evidence.

Implements §10.9 of the addendum: Signal 8 (ontological projection evidence)
and the joint concept-ontology scoring.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rdflib import URIRef

from mork_communities.communities import SemanticCommunity
from mork_communities.projections import OntologicalProjection, PropertyProjection
from mork_communities.matching import CommunityMatcher, CommunityMatchResult

logger = logging.getLogger(__name__)


@dataclass
class EvidenceSignal:
    """A single evidence signal contribution."""

    signal_type: str
    log_likelihood_ratio: float
    raw_value: float
    description: str = ""


@dataclass
class CandidateScore:
    """
    Joint (concept, ontology_target) score with all evidence.

    Attributes
    ----------
    concept_iri : URIRef
        The candidate DataConcept.
    ontology_target : Optional[URIRef]
        The projected ontology target (OwlAxiom shadow), if available.
    parent_class : Optional[URIRef]
        The projected parent class shadow.
    log_posterior : float
        The composite log-posterior score.
    signals : List[EvidenceSignal]
        Individual signal contributions.
    projection_confidence : float
        Confidence from ontological projection (0 if none).
    is_feasible : bool
        Whether feasibility checks pass.
    resolution_status : str
        One of: 'deterministic', 'high_confidence', 'moderate', 'ambiguous', 'novel'.
    """

    concept_iri: URIRef
    ontology_target: Optional[URIRef] = None
    parent_class: Optional[URIRef] = None
    log_posterior: float = 0.0
    signals: List[EvidenceSignal] = field(default_factory=list)
    projection_confidence: float = 0.0
    is_feasible: bool = True
    resolution_status: str = "ambiguous"


class BayesianScorer:
    """
    Computes Bayesian scores for candidate (concept, ontology_target) pairs,
    incorporating community boost and ontological projection evidence.

    The full score is:

    ln P(c, o | e, S) = ln P(c)
                       + Σᵢ λᵢ(eᵢ, c)         [base signals]
                       + λ_community(c, S)      [community boost]
                       + λ_proj(c, o, S)        [projection evidence]
                       + const

    See §10.9 of the addendum.
    """

    def __init__(
        self,
        auto_threshold: float = 3.0,
        high_confidence_threshold: float = 2.0,
        moderate_threshold: float = 1.0,
        estimated_property_count: int = 15,
        negative_projection_penalty: float = -0.5,
    ):
        self._auto_thresh = auto_threshold
        self._high_thresh = high_confidence_threshold
        self._mod_thresh = moderate_threshold
        self._est_props = estimated_property_count
        self._neg_penalty = negative_projection_penalty

    def score_candidates(
        self,
        candidates: List[Tuple[URIRef, float]],
        community_match: Optional[CommunityMatchResult],
        projection: Optional[OntologicalProjection],
        base_signals: Optional[Dict[URIRef, List[EvidenceSignal]]] = None,
        marginal_frequencies: Optional[Dict[URIRef, float]] = None,
    ) -> List[CandidateScore]:
        """
        Score a list of candidate concepts with all evidence sources.

        Parameters
        ----------
        candidates : List[Tuple[URIRef, float]]
            (concept_iri, spectral_prior) pairs.
        community_match : Optional[CommunityMatchResult]
            The community match for the section.
        projection : Optional[OntologicalProjection]
            The ontological projection for the matched community.
        base_signals : Optional
            Pre-computed base evidence signals per concept.
        marginal_frequencies : Optional
            Marginal concept frequencies P(c).

        Returns
        -------
        List[CandidateScore]
            Scored candidates, sorted by log_posterior descending.
        """
        scores = []
        marginals = marginal_frequencies or {}

        for concept_iri, spectral_prior in candidates:
            score = CandidateScore(concept_iri=concept_iri)

            # ── Prior ─────────────────────────────────────────
            log_prior = math.log(max(spectral_prior, 1e-10))
            score.log_posterior = log_prior
            score.signals.append(
                EvidenceSignal(
                    signal_type="spectral_prior",
                    log_likelihood_ratio=log_prior,
                    raw_value=spectral_prior,
                    description=f"Spectral prior: {spectral_prior:.4f}",
                )
            )

            # ── Base signals ──────────────────────────────────
            if base_signals and concept_iri in base_signals:
                for signal in base_signals[concept_iri]:
                    score.log_posterior += signal.log_likelihood_ratio
                    score.signals.append(signal)

            # ── Community boost ────────────────────────────────
            if community_match is not None:
                community = community_match.community
                comm_confidence = community_match.confidence

                mu = community.members.get(concept_iri, 0.0)
                marginal = marginals.get(concept_iri, 0.1)

                if mu > marginal:
                    boost = comm_confidence * math.log(mu / marginal)
                    score.log_posterior += boost
                    score.signals.append(
                        EvidenceSignal(
                            signal_type="community_boost",
                            log_likelihood_ratio=boost,
                            raw_value=mu,
                            description=(
                                f"Community '{community.community_id}': "
                                f"μ={mu:.3f}, P(c)={marginal:.3f}, "
                                f"conf={comm_confidence:.3f}"
                            ),
                        )
                    )
                elif mu == 0.0 and comm_confidence > 0.5:
                    # Concept is NOT in the matched community —
                    # mild negative evidence
                    penalty = -0.3 * comm_confidence
                    score.log_posterior += penalty
                    score.signals.append(
                        EvidenceSignal(
                            signal_type="community_absence",
                            log_likelihood_ratio=penalty,
                            raw_value=0.0,
                            description=(
                                f"Not in community "
                                f"'{community.community_id}'"
                            ),
                        )
                    )

            # ── Ontological projection evidence (Signal 8) ────
            if projection is not None and community_match is not None:
                self._add_projection_evidence(
                    score, concept_iri, projection, community_match.confidence
                )

            scores.append(score)

        # Sort by score descending
        scores.sort(key=lambda s: s.log_posterior, reverse=True)

        # Assign resolution status
        self._assign_resolution_status(scores)

        return scores

    def _add_projection_evidence(
        self,
        score: CandidateScore,
        concept_iri: URIRef,
        projection: OntologicalProjection,
        community_confidence: float,
    ) -> None:
        """
        Add ontological projection evidence (Signal 8, §10.9.1).

        λ_proj = ln(confidence(c, o | C)) - ln(1 / |candidate_properties|)
        """
        # Find property projections for this concept
        matching_pps = [
            pp
            for pp in projection.property_projections
            if pp.concept_iri == concept_iri
        ]

        if matching_pps:
            best_pp = max(matching_pps, key=lambda pp: pp.confidence)

            # Log-likelihood ratio
            lambda_proj = math.log(max(best_pp.confidence, 1e-10)) - math.log(
                1.0 / self._est_props
            )

            # Weight by community confidence
            weighted_lambda = community_confidence * lambda_proj

            score.log_posterior += weighted_lambda
            score.projection_confidence = best_pp.confidence
            score.ontology_target = best_pp.property_shadow
            score.parent_class = best_pp.parent_class_shadow

            # Mark feasibility as confirmed by prior mapping
            score.is_feasible = True

            score.signals.append(
                EvidenceSignal(
                    signal_type="ontological_projection",
                    log_likelihood_ratio=weighted_lambda,
                    raw_value=best_pp.confidence,
                    description=(
                        f"Projection: {best_pp.property_shadow} on "
                        f"{best_pp.parent_class_shadow} "
                        f"(conf={best_pp.confidence:.3f}, "
                        f"freq={best_pp.frequency})"
                    ),
                )
            )
        else:
            # Concept has no projection in this community
            score.log_posterior += self._neg_penalty
            score.signals.append(
                EvidenceSignal(
                    signal_type="no_projection",
                    log_likelihood_ratio=self._neg_penalty,
                    raw_value=0.0,
                    description="No projection in matched community",
                )
            )

    def _assign_resolution_status(
        self, scores: List[CandidateScore]
    ) -> None:
        """
        Assign resolution status based on score gaps.

        - deterministic: single candidate, score > auto_threshold
        - high_confidence: top >> second
        - moderate: clear ordering
        - ambiguous: close scores
        - novel: no candidates
        """
        if not scores:
            return

        if len(scores) == 1:
            if scores[0].log_posterior > self._auto_thresh:
                scores[0].resolution_status = "deterministic"
            else:
                scores[0].resolution_status = "moderate"
            return

        gap = scores[0].log_posterior - scores[1].log_posterior

        if gap > self._auto_thresh:
            scores[0].resolution_status = "deterministic"
        elif gap > self._high_thresh:
            scores[0].resolution_status = "high_confidence"
        elif gap > self._mod_thresh:
            scores[0].resolution_status = "moderate"
        else:
            scores[0].resolution_status = "ambiguous"

        for s in scores[1:]:
            s.resolution_status = "alternative"