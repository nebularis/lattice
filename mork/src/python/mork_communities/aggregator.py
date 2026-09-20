"""
mork_communities/aggregator.py

Full 8-signal Bayesian Aggregator implementing §5.5 of the reference
architecture, Chapter 6 of the algorithms paper, and Definition 3.10
of the foundations paper.

Combines all eight evidence signals into a joint (concept, ontology_target)
score via the profunctor composition formula:

    Π_full(ρ, o) = inf_c [Π_𝒞(ρ, c) + Π_proj(c, o | C_j)]

Which in probability space is Bayesian marginalisation:

    P_full(ρ, c, o) = Σ_j P_𝒞(ρ, c | C_j) · P_proj(C_j, o) · P(C_j)
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rdflib import URIRef

from mork_communities.scoring import (
    BayesianScorer,
    CandidateScore,
    EvidenceSignal,
)
from mork_communities.matching import CommunityMatchResult
from mork_communities.projections import OntologicalProjection
from mork_communities.recognition import RecognitionCandidate
from mork_communities.axiom_intent import AxiomAlignmentScorer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FullEvidenceBundle:
    """Complete evidence bundle for a candidate mapping."""
    # Signal 1: Name match (lexical similarity)
    name_match_score: float = 0.0
    # Signal 2: Embedding similarity (spectral distance)
    embedding_score: float = 0.0
    # Signal 3: Type compatibility
    type_compatibility: float = 1.0  # 1.0 = perfect, 0.0 = incompatible
    # Signal 4: Distortion evidence (jargon/abbreviation detection)
    distortion_score: float = 0.0
    # Signal 5: Structural position
    structural_score: float = 0.0
    # Signal 6: Prior frequency (concept base rate)
    prior_frequency: float = 0.1
    # Signal 7: Community boost
    community_boost: float = 0.0
    # Signal 8: Ontological projection confidence
    projection_confidence: float = 0.0


class FullBayesianAggregator:
    """
    Combines all 8 evidence signals into a posterior score.

    The full score is (§5.5 of reference architecture):

    ln P(c, o | e, S) = ln P(c)                    [Signal 6: prior]
                       + λ₁(name match)             [Signal 1]
                       + λ₂(embedding)              [Signal 2]
                       + λ₃(type compatibility)     [Signal 3]
                       + λ₄(distortion)             [Signal 4]
                       + λ₅(structural position)    [Signal 5]
                       + λ_community(c, S)           [Signal 7]
                       + λ_proj(c, o, S)             [Signal 8]
                       + const

    Signal strengths (nats) from §5.5 table:
      1. Name match:           1.0–2.0
      2. Embedding similarity: 0.5–1.5
      3. Type compatibility:   0.3–0.8
      4. Distortion evidence:  0.5–1.0
      5. Structural position:  0.2–0.5
      6. Prior frequency:      0.1–0.3
      7. Community boost:      0.5–2.2
      8. Ontological projection: 0.0–2.7
    """

    # Signal weight coefficients
    SIGNAL_WEIGHTS = {
        "name_match": 1.5,
        "embedding": 1.0,
        "type_compatibility": 0.8,
        "distortion": 0.7,
        "structural": 0.3,
        "prior": 0.2,
        "community": 1.8,
        "projection": 2.5,
    }

    def __init__(
        self,
        axiom_scorer: Optional[AxiomAlignmentScorer] = None,
        signal_weights: Optional[Dict[str, float]] = None,
        auto_threshold: float = 3.0,
        high_confidence_threshold: float = 2.0,
        moderate_threshold: float = 1.0,
    ):
        self._axiom_scorer = axiom_scorer
        self._weights = signal_weights or self.SIGNAL_WEIGHTS
        self._auto_thresh = auto_threshold
        self._high_thresh = high_confidence_threshold
        self._mod_thresh = moderate_threshold

    def score_candidate(
        self,
        concept_iri: URIRef,
        evidence: FullEvidenceBundle,
        target_property: Optional[URIRef] = None,
        target_class: Optional[URIRef] = None,
    ) -> CandidateScore:
        """
        Score a single candidate with all 8 signals.

        Returns
        -------
        CandidateScore
            The scored candidate with signal breakdown.
        """
        score = CandidateScore(concept_iri=concept_iri)

        # Signal 1: Name match
        if evidence.name_match_score > 0:
            lambda_1 = self._weights["name_match"] * math.log(
                max(evidence.name_match_score, 1e-10)
            )
            score.log_posterior += lambda_1
            score.signals.append(EvidenceSignal(
                signal_type="name_match",
                log_likelihood_ratio=lambda_1,
                raw_value=evidence.name_match_score,
                description=f"Name match: {evidence.name_match_score:.3f}",
            ))

        # Signal 2: Embedding similarity
        if evidence.embedding_score > 0:
            lambda_2 = self._weights["embedding"] * math.log(
                max(evidence.embedding_score, 1e-10)
            )
            score.log_posterior += lambda_2
            score.signals.append(EvidenceSignal(
                signal_type="embedding_similarity",
                log_likelihood_ratio=lambda_2,
                raw_value=evidence.embedding_score,
                description=f"Embedding: {evidence.embedding_score:.3f}",
            ))

        # Signal 3: Type compatibility
        if evidence.type_compatibility < 1.0:
            if evidence.type_compatibility <= 0:
                # Incompatible — hard gate (∞ distance)
                score.log_posterior = -1000.0
                score.is_feasible = False
                score.signals.append(EvidenceSignal(
                    signal_type="type_incompatible",
                    log_likelihood_ratio=-1000.0,
                    raw_value=0.0,
                    description="TYPE INCOMPATIBLE — eliminated",
                ))
                return score
            else:
                lambda_3 = self._weights["type_compatibility"] * math.log(
                    evidence.type_compatibility
                )
                score.log_posterior += lambda_3
                score.signals.append(EvidenceSignal(
                    signal_type="type_compatibility",
                    log_likelihood_ratio=lambda_3,
                    raw_value=evidence.type_compatibility,
                    description=f"Type compat: {evidence.type_compatibility:.3f}",
                ))

        # Signal 4: Distortion evidence
        if evidence.distortion_score > 0:
            lambda_4 = self._weights["distortion"] * evidence.distortion_score
            score.log_posterior += lambda_4
            score.signals.append(EvidenceSignal(
                signal_type="distortion",
                log_likelihood_ratio=lambda_4,
                raw_value=evidence.distortion_score,
                description=f"Distortion: {evidence.distortion_score:.3f}",
            ))

        # Signal 5: Structural position
        if evidence.structural_score > 0:
            lambda_5 = self._weights["structural"] * evidence.structural_score
            score.log_posterior += lambda_5
            score.signals.append(EvidenceSignal(
                signal_type="structural_position",
                log_likelihood_ratio=lambda_5,
                raw_value=evidence.structural_score,
                description=f"Structural: {evidence.structural_score:.3f}",
            ))

        # Signal 6: Prior frequency
        lambda_6 = self._weights["prior"] * math.log(
            max(evidence.prior_frequency, 1e-10)
        )
        score.log_posterior += lambda_6
        score.signals.append(EvidenceSignal(
            signal_type="prior_frequency",
            log_likelihood_ratio=lambda_6,
            raw_value=evidence.prior_frequency,
            description=f"Prior: {evidence.prior_frequency:.3f}",
        ))

        # Signal 7: Community boost
        if evidence.community_boost > 0:
            lambda_7 = self._weights["community"] * evidence.community_boost
            score.log_posterior += lambda_7
            score.signals.append(EvidenceSignal(
                signal_type="community_boost",
                log_likelihood_ratio=lambda_7,
                raw_value=evidence.community_boost,
                description=f"Community: boost={evidence.community_boost:.3f}",
            ))

        # Signal 8: Ontological projection
        if evidence.projection_confidence > 0:
            # λ_proj = ln(confidence) - ln(1/|properties|)
            lambda_8 = self._weights["projection"] * (
                math.log(max(evidence.projection_confidence, 1e-10))
                - math.log(1.0 / 15)  # assume ~15 candidate properties
            )
            score.log_posterior += lambda_8
            score.projection_confidence = evidence.projection_confidence
            score.signals.append(EvidenceSignal(
                signal_type="ontological_projection",
                log_likelihood_ratio=lambda_8,
                raw_value=evidence.projection_confidence,
                description=f"Projection: conf={evidence.projection_confidence:.3f}",
            ))

        # Axiom alignment (part of Signal 8 / feasibility)
        if self._axiom_scorer and target_property and target_class:
            axiom_score, is_feasible, explanation = (
                self._axiom_scorer.score_alignment(
                    concept_iri, target_property, target_class
                )
            )
            if not is_feasible:
                score.log_posterior = -1000.0
                score.is_feasible = False
                score.signals.append(EvidenceSignal(
                    signal_type="axiom_infeasible",
                    log_likelihood_ratio=-1000.0,
                    raw_value=0.0,
                    description=f"INFEASIBLE: {explanation}",
                ))
            elif axiom_score > 0:
                lambda_axiom = math.log(axiom_score)
                score.log_posterior += lambda_axiom
                score.signals.append(EvidenceSignal(
                    signal_type="axiom_alignment",
                    log_likelihood_ratio=lambda_axiom,
                    raw_value=axiom_score,
                    description=explanation,
                ))

        score.ontology_target = target_property
        score.parent_class = target_class

        return score

    def score_all_candidates(
        self,
        candidates: List[Tuple[URIRef, FullEvidenceBundle]],
        target_property_map: Optional[Dict[URIRef, URIRef]] = None,
        target_class: Optional[URIRef] = None,
    ) -> List[CandidateScore]:
        """
        Score all candidates and assign resolution status.
        Implements the superposition assessment (§5.6).
        """
        scores = []
        for concept_iri, evidence in candidates:
            target_prop = (
                target_property_map.get(concept_iri) if target_property_map else None
            )
            score = self.score_candidate(
                concept_iri, evidence, target_prop, target_class
            )
            scores.append(score)

        # Sort by score descending
        scores.sort(key=lambda s: s.log_posterior, reverse=True)

        # Filter infeasible
        feasible = [s for s in scores if s.is_feasible]
        infeasible = [s for s in scores if not s.is_feasible]
        for s in infeasible:
            s.resolution_status = "infeasible"

        # Assign resolution status (§5.6 Superposition Assessment)
        self._assign_resolution_status(feasible)

        return feasible + infeasible

    def _assign_resolution_status(self, scores: List[CandidateScore]) -> None:
        """
        Assign resolution status based on score distribution.
        Implements the superposition assessment flowchart (§5.6).
        """
        if not scores:
            return

        if len(scores) == 1:
            if scores[0].log_posterior > self._auto_thresh:
                scores[0].resolution_status = "deterministic"
            elif scores[0].log_posterior > self._mod_thresh:
                scores[0].resolution_status = "verification"
            else:
                scores[0].resolution_status = "ambiguous"
            return

        gap = scores[0].log_posterior - scores[1].log_posterior

        if gap > self._auto_thresh and scores[0].projection_confidence >= 0.9:
            scores[0].resolution_status = "deterministic"
        elif gap > self._high_thresh:
            scores[0].resolution_status = "high_confidence"
        elif gap > self._mod_thresh:
            scores[0].resolution_status = "moderate"
        else:
            scores[0].resolution_status = "ambiguous"

        for s in scores[1:]:
            s.resolution_status = "alternative"