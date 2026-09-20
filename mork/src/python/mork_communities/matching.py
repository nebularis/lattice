"""
mork_communities/matching.py

Community matching: given a set of observed concepts in a section,
find the best-matching community and compute match confidence.

Implements the community distribution presheaf (§10.7.3) and
the Bayesian community matching.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

from rdflib import URIRef

from mork_communities.communities import SemanticCommunity, CommunityScheme

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommunityMatchResult:
    """
    The result of matching a section against the community scheme.

    Attributes
    ----------
    community : SemanticCommunity
        The best-matching community.
    confidence : float
        Posterior probability P(Cⱼ | observed concepts) ∈ [0, 1].
    jaccard_score : float
        Weighted Jaccard similarity.
    matched_concepts : FrozenSet[URIRef]
        Concepts in the section that contributed to the match.
    all_matches : List[Tuple[SemanticCommunity, float]]
        All communities with their posterior probabilities, sorted descending.
    """

    community: SemanticCommunity
    confidence: float
    jaccard_score: float
    matched_concepts: FrozenSet[URIRef]
    all_matches: List[Tuple[SemanticCommunity, float]]


class CommunityMatcher:
    """
    Matches observed concept sets against the community scheme.

    Supports two matching modes:
    1. Weighted Jaccard (fast, deterministic)
    2. Bayesian posterior (probabilistic, via naive Bayes, §10.7.4)
    """

    def __init__(
        self,
        scheme: CommunityScheme,
        match_threshold: float = 0.2,
        use_bayesian: bool = True,
        smoothing: float = 0.01,
    ):
        self._scheme = scheme
        self._threshold = match_threshold
        self._use_bayesian = use_bayesian
        self._smoothing = smoothing

        # Precompute community priors
        total_obs = sum(
            c.observation_count for c in scheme.communities
        )
        self._priors: Dict[str, float] = {}
        for c in scheme.communities:
            self._priors[c.community_id] = (
                c.observation_count / total_obs if total_obs > 0 else 1.0 / len(scheme.communities)
            )

    def match(
        self, observed_concepts: FrozenSet[URIRef]
    ) -> Optional[CommunityMatchResult]:
        """
        Match a set of observed concepts against all communities.

        Parameters
        ----------
        observed_concepts : FrozenSet[URIRef]
            The DataConcepts identified in the section.

        Returns
        -------
        CommunityMatchResult or None
            The best match, or None if no community matches above threshold.
        """
        if not observed_concepts or not self._scheme.communities:
            return None

        if self._use_bayesian:
            scores = self._bayesian_match(observed_concepts)
        else:
            scores = self._jaccard_match(observed_concepts)

        if not scores:
            return None

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        best_community, best_score = scores[0]

        if best_score < self._threshold:
            return None

        # Compute Jaccard separately for the result
        jaccard = self._weighted_jaccard(
            observed_concepts, best_community
        )

        matched = observed_concepts & best_community.member_set

        return CommunityMatchResult(
            community=best_community,
            confidence=best_score,
            jaccard_score=jaccard,
            matched_concepts=frozenset(matched),
            all_matches=scores,
        )

    def _bayesian_match(
        self, observed: FrozenSet[URIRef]
    ) -> List[Tuple[SemanticCommunity, float]]:
        """
        Compute P(Cⱼ | observed) via naive Bayes (Definition 10.7.4).

        P(Cⱼ | obs) ∝ P(obs | Cⱼ) · P(Cⱼ)
        P(obs | Cⱼ) = ∏_{c ∈ obs} μⱼ(c) · ∏_{c' ∈ Cⱼ\obs} (1 - μⱼ(c'))
        """
        log_posteriors: List[Tuple[SemanticCommunity, float]] = []

        for community in self._scheme.communities:
            log_prior = math.log(
                self._priors.get(community.community_id, 1e-6)
            )

            log_likelihood = 0.0

            # Terms for observed concepts
            for c in observed:
                mu = community.members.get(c, self._smoothing)
                # Clamp to avoid log(0)
                mu = max(mu, self._smoothing)
                log_likelihood += math.log(mu)

            # Terms for community members NOT observed
            for c, mu in community.members.items():
                if c not in observed:
                    # P(not present | community) = 1 - μ
                    log_likelihood += math.log(max(1.0 - mu, self._smoothing))

            log_posteriors.append(
                (community, log_prior + log_likelihood)
            )

        # Normalise to proper probabilities via log-sum-exp
        if not log_posteriors:
            return []

        max_log = max(lp for _, lp in log_posteriors)
        exp_sum = sum(
            math.exp(lp - max_log) for _, lp in log_posteriors
        )
        log_normaliser = max_log + math.log(exp_sum)

        result = []
        for community, log_post in log_posteriors:
            prob = math.exp(log_post - log_normaliser)
            result.append((community, prob))

        return result

    def _jaccard_match(
        self, observed: FrozenSet[URIRef]
    ) -> List[Tuple[SemanticCommunity, float]]:
        """
        Compute weighted Jaccard similarity (Definition 10.5.4).
        """
        results = []
        for community in self._scheme.communities:
            score = self._weighted_jaccard(observed, community)
            results.append((community, score))
        return results

    @staticmethod
    def _weighted_jaccard(
        observed: FrozenSet[URIRef], community: SemanticCommunity
    ) -> float:
        """
        J_w(A, C, μ) = Σ_{c ∈ A ∩ C} μ(c) / Σ_{c ∈ A ∪ C} μ(c)

        For concepts in A but not in C, we assign weight 1.0 (observed but
        not a community member).
        """
        intersection_weight = 0.0
        union_weight = 0.0

        all_concepts = observed | community.member_set

        for c in all_concepts:
            if c in observed and c in community.members:
                # In both
                w = community.members[c]
                intersection_weight += w
                union_weight += w
            elif c in observed:
                # In observed only — weight 1.0
                union_weight += 1.0
            else:
                # In community only
                union_weight += community.members[c]

        if union_weight == 0:
            return 0.0

        return intersection_weight / union_weight

    def get_community_boost(
        self,
        concept_iri: URIRef,
        match_result: CommunityMatchResult,
        marginal_frequency: float = 0.1,
    ) -> float:
        """
        Compute the community boost for a candidate concept.

        boost(c) = Σⱼ P(Cⱼ|S) · max(0, ln(μⱼ(c) / P(c)))

        (Definition 10.7.9)
        """
        boost = 0.0
        for community, prob in match_result.all_matches:
            mu = community.members.get(concept_iri, 0.0)
            if mu > marginal_frequency:
                boost += prob * math.log(mu / marginal_frequency)
        return boost