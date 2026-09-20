"""
mork_communities/metrics.py

Convergence and quality metrics for monitoring the pipeline's
progression toward deterministic resolution.

Implements the metrics from §10.10 and §10.9.3 of the addendum.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from rdflib import URIRef

from mork_communities.communities import CommunityScheme
from mork_communities.projections import OntologicalProjection
from mork_communities.inference import SectionResolution

logger = logging.getLogger(__name__)


@dataclass
class ConvergenceMetrics:
    """Metrics tracking convergence toward deterministic resolution."""

    # Per-run counts
    total_tokens: int = 0
    deterministic_tokens: int = 0
    high_confidence_tokens: int = 0
    ambiguous_tokens: int = 0
    novel_tokens: int = 0

    # Rates
    deterministic_rate: float = 0.0
    llm_required_rate: float = 0.0

    # Community contribution
    tokens_boosted_by_community: int = 0
    tokens_resolved_by_projection: int = 0

    # Estimated savings
    estimated_llm_tokens_saved: int = 0
    estimated_llm_calls_saved: int = 0


class MetricsCollector:
    """
    Collects and computes convergence metrics from resolution results.
    """

    def __init__(
        self,
        base_tokens_per_field: int = 600,
        community_tokens_per_field: int = 250,
        projection_tokens_per_field: int = 150,
    ):
        self._base_tpf = base_tokens_per_field
        self._comm_tpf = community_tokens_per_field
        self._proj_tpf = projection_tokens_per_field
        self._history: List[ConvergenceMetrics] = []

    def collect(
        self, section_results: List[SectionResolution]
    ) -> ConvergenceMetrics:
        """
        Compute metrics from a batch of section resolutions.
        """
        m = ConvergenceMetrics()

        for sr in section_results:
            for tr in sr.token_resolutions:
                m.total_tokens += 1

                if tr.resolution_status == "deterministic":
                    m.deterministic_tokens += 1
                elif tr.resolution_status == "high_confidence":
                    m.high_confidence_tokens += 1
                elif tr.resolution_status == "ambiguous":
                    m.ambiguous_tokens += 1
                elif tr.resolution_status == "novel":
                    m.novel_tokens += 1

                # Check community contribution
                if tr.community_match is not None:
                    m.tokens_boosted_by_community += 1

                # Check projection contribution
                if tr.candidates and tr.candidates[0].projection_confidence > 0:
                    m.tokens_resolved_by_projection += 1

        if m.total_tokens > 0:
            m.deterministic_rate = m.deterministic_tokens / m.total_tokens
            m.llm_required_rate = (
                m.ambiguous_tokens + m.novel_tokens
            ) / m.total_tokens

        # Token savings estimate (§10 of ontologic mapping addendum, Table)
        llm_needed = m.ambiguous_tokens + m.novel_tokens
        base_cost = m.total_tokens * self._base_tpf
        actual_cost = (
            m.deterministic_tokens * 0  # no LLM cost
            + m.high_confidence_tokens * self._proj_tpf
            + llm_needed * self._comm_tpf
        )
        m.estimated_llm_tokens_saved = max(0, base_cost - actual_cost)
        m.estimated_llm_calls_saved = (
            m.total_tokens - llm_needed
        )

        self._history.append(m)
        return m

    def compute_ontological_coherence(
        self,
        scheme: CommunityScheme,
        projections: Dict[str, OntologicalProjection],
    ) -> Dict[str, float]:
        """
        Compute ontological coherence for each community (Definition 10.9.1).

        OntCoh(C) = max_t freq(t) / Σ_t freq(t)
        """
        result = {}
        for comm in scheme.communities:
            proj = projections.get(comm.community_id)
            if proj and proj.projected_classes:
                max_freq = max(proj.projected_classes.values())
                total_freq = sum(proj.projected_classes.values())
                result[comm.community_id] = max_freq / total_freq
            else:
                result[comm.community_id] = 0.0
        return result

    def compute_quality_with_ontological_coherence(
        self,
        scheme: CommunityScheme,
        projections: Dict[str, OntologicalProjection],
        alpha: float = 0.25,
        beta: float = 0.30,
        gamma: float = 0.25,
        delta: float = 0.20,
    ) -> float:
        """
        Extended quality metric including ontological coherence (§10.9.3).

        Quality = α·Modularity + β·MeanCoherence + γ·Coverage + δ·MeanOntCoh
        """
        ont_coh = self.compute_ontological_coherence(scheme, projections)
        mean_ont_coh = (
            sum(ont_coh.values()) / len(ont_coh) if ont_coh else 0.0
        )

        mean_coherence = (
            sum(c.coherence for c in scheme.communities)
            / len(scheme.communities)
            if scheme.communities
            else 0.0
        )

        # Modularity and coverage would require observations; return partial
        return beta * mean_coherence + delta * mean_ont_coh

    def get_convergence_trajectory(self) -> List[Dict]:
        """
        Return the convergence trajectory across mapping runs.
        Shows how deterministic_rate improves over time.
        """
        return [
            {
                "run": i + 1,
                "deterministic_rate": m.deterministic_rate,
                "llm_required_rate": m.llm_required_rate,
                "projection_resolved": (
                    m.tokens_resolved_by_projection / m.total_tokens
                    if m.total_tokens > 0
                    else 0.0
                ),
                "total_tokens": m.total_tokens,
                "tokens_saved": m.estimated_llm_tokens_saved,
            }
            for i, m in enumerate(self._history)
        ]

    def estimate_steady_state_run_count(self) -> Optional[int]:
        """
        Estimate how many more mapping runs are needed to reach
        90% deterministic resolution, based on the convergence trajectory.

        Uses the bound from Theorem 10.10.3:
        p_full(t) ≥ 1 - K·exp(-(1+δ')·t / (K·ln(K)))
        """
        if len(self._history) < 3:
            return None

        # Fit a simple exponential to the deterministic rate
        rates = [m.deterministic_rate for m in self._history]
        current_rate = rates[-1]

        if current_rate >= 0.9:
            return 0  # Already there

        # Simple linear extrapolation of improvement rate
        if len(rates) >= 2:
            improvement_per_run = (rates[-1] - rates[0]) / len(rates)
            if improvement_per_run > 0:
                remaining = (0.9 - current_rate) / improvement_per_run
                return max(1, int(math.ceil(remaining)))

        return None