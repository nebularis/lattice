"""
mork_communities/inference.py

Tri-Stratum Resolver: the complete inference pipeline that combines
spectral candidates, community context, and ontological projections
for progressive deterministic resolution.

Implements §10.11 of the addendum.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import (
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    Tuple,
)

from rdflib import URIRef

from mork_communities.communities import (
    SemanticCommunity,
    CommunityScheme,
)
from mork_communities.projections import (
    OntologicalProjection,
    ProjectionExtractor,
)
from mork_communities.matching import (
    CommunityMatcher,
    CommunityMatchResult,
)
from mork_communities.scoring import (
    BayesianScorer,
    CandidateScore,
    EvidenceSignal,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenResolution:
    """
    The resolution result for a single token/field.

    Attributes
    ----------
    token_name : str
        The raw token/field name.
    representation_iri : URIRef
        The Representation node IRI.
    candidates : List[CandidateScore]
        Scored candidates, sorted by score descending.
    resolution_status : str
        'deterministic', 'high_confidence', 'moderate', 'ambiguous', 'novel'.
    community_match : Optional[CommunityMatchResult]
        The community match for this token's section.
    requires_llm : bool
        Whether LLM invocation is needed.
    """

    token_name: str
    representation_iri: URIRef
    candidates: List[CandidateScore]
    resolution_status: str
    community_match: Optional[CommunityMatchResult]
    requires_llm: bool


@dataclass
class SectionResolution:
    """
    Resolution results for an entire section.
    """

    section_iri: URIRef
    community_match: Optional[CommunityMatchResult]
    token_resolutions: List[TokenResolution] = field(default_factory=list)

    @property
    def deterministic_count(self) -> int:
        return sum(
            1
            for tr in self.token_resolutions
            if tr.resolution_status == "deterministic"
        )

    @property
    def requires_llm_count(self) -> int:
        return sum(1 for tr in self.token_resolutions if tr.requires_llm)

    @property
    def total_tokens(self) -> int:
        return len(self.token_resolutions)


class TriStratumResolver:
    """
    The complete tri-stratum inference pipeline.

    Given a set of tokens in a section, this resolver:
    1. Retrieves spectral/lexical candidates (assumed provided externally)
    2. Matches the section against the community scheme
    3. Applies community boost to candidates
    4. Looks up ontological projections for confirmed patterns
    5. Scores candidates jointly over (concept, ontology_target)
    6. Determines resolution status (deterministic vs. LLM-needed)

    Usage
    -----
    resolver = TriStratumResolver(scheme, projections)
    section_result = resolver.resolve_section(
        section_iri,
        token_candidates={
            token1_iri: [(concept1, 0.8), (concept2, 0.3), ...],
            token2_iri: [(concept3, 0.9), ...],
        },
        token_names={token1_iri: "xs_point", token2_iri: "lmt", ...},
    )
    """

    def __init__(
        self,
        community_scheme: CommunityScheme,
        projections: Dict[str, OntologicalProjection],
        scorer: Optional[BayesianScorer] = None,
        community_match_threshold: float = 0.3,
        use_bayesian_matching: bool = True,
        marginal_frequencies: Optional[Dict[URIRef, float]] = None,
    ):
        """
        Parameters
        ----------
        community_scheme : CommunityScheme
            The active community scheme.
        projections : Dict[str, OntologicalProjection]
            Mapping from community_id to its ontological projection.
        scorer : Optional[BayesianScorer]
            The Bayesian scorer. If None, uses defaults.
        community_match_threshold : float
            Minimum confidence for community matching.
        use_bayesian_matching : bool
            Whether to use Bayesian (True) or Jaccard (False) matching.
        marginal_frequencies : Optional
            Marginal concept frequencies P(c) for boost computation.
        """
        self._scheme = community_scheme
        self._projections = projections
        self._scorer = scorer or BayesianScorer()
        self._match_threshold = community_match_threshold
        self._marginals = marginal_frequencies or {}

        # Build the matcher
        self._matcher = CommunityMatcher(
            scheme=community_scheme,
            match_threshold=community_match_threshold,
            use_bayesian=use_bayesian_matching,
        )

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
        Resolve all tokens in a section.

        Parameters
        ----------
        section_iri : URIRef
            The structural section IRI.
        token_candidates : Dict[URIRef, List[Tuple[URIRef, float]]]
            For each token (Representation IRI), a list of
            (concept_iri, spectral_similarity) candidate pairs.
        token_names : Dict[URIRef, str]
            Map from token IRI to raw field name.
        recognised_concepts : Optional[FrozenSet[URIRef]]
            Concepts already confidently recognised in this section
            (for partial-signature community matching).
        base_signals : Optional
            Pre-computed base evidence signals: token_iri -> concept_iri -> signals.

        Returns
        -------
        SectionResolution
            Resolution results for the entire section.
        """
        # ── Step 2: Community Match ───────────────────────────
        # Build partial signature from high-confidence tokens
        if recognised_concepts is None:
            recognised_concepts = self._build_partial_signature(
                token_candidates
            )

        community_match = None
        if recognised_concepts:
            community_match = self._matcher.match(recognised_concepts)

        # Get projection if community matched
        projection = None
        if community_match is not None:
            comm_id = community_match.community.community_id
            projection = self._projections.get(comm_id)

        # ── Steps 3-5: Score each token ───────────────────────
        section_result = SectionResolution(
            section_iri=section_iri,
            community_match=community_match,
        )

        for token_iri, candidates in token_candidates.items():
            token_name = token_names.get(token_iri, str(token_iri))

            # Get base signals for this token if available
            token_base_signals = None
            if base_signals and token_iri in base_signals:
                token_base_signals = base_signals[token_iri]

            # Score candidates
            scored = self._scorer.score_candidates(
                candidates=candidates,
                community_match=community_match,
                projection=projection,
                base_signals=token_base_signals,
                marginal_frequencies=self._marginals,
            )

            # Determine if LLM is needed
            requires_llm = self._requires_llm(scored)

            resolution_status = (
                scored[0].resolution_status if scored else "novel"
            )

            token_result = TokenResolution(
                token_name=token_name,
                representation_iri=token_iri,
                candidates=scored,
                resolution_status=resolution_status,
                community_match=community_match,
                requires_llm=requires_llm,
            )

            section_result.token_resolutions.append(token_result)

        logger.info(
            "Section %s: %d/%d tokens deterministic, %d require LLM",
            section_iri,
            section_result.deterministic_count,
            section_result.total_tokens,
            section_result.requires_llm_count,
        )

        return section_result

    def _build_partial_signature(
        self,
        token_candidates: Dict[URIRef, List[Tuple[URIRef, float]]],
        confidence_threshold: float = 0.7,
    ) -> FrozenSet[URIRef]:
        """
        Build a partial concept signature from high-confidence candidates.
        """
        concepts = set()
        for candidates in token_candidates.values():
            if not candidates:
                continue
            # Sort by score
            sorted_cands = sorted(candidates, key=lambda x: x[1], reverse=True)
            top_score = sorted_cands[0][1]
            if top_score >= confidence_threshold:
                if len(sorted_cands) == 1 or (
                    top_score - sorted_cands[1][1] > 0.2
                ):
                    concepts.add(sorted_cands[0][0])
        return frozenset(concepts)

    @staticmethod
    def _requires_llm(scored: List[CandidateScore]) -> bool:
        """Determine if LLM invocation is needed."""
        if not scored:
            return True  # Novel concept
        status = scored[0].resolution_status
        return status in ("ambiguous", "novel")


class ResolutionReporter:
    """
    Formats resolution results for the LLM bundle or human review.
    """

    @staticmethod
    def format_token_bundle(
        resolution: TokenResolution, max_candidates: int = 5
    ) -> str:
        """
        Format a token resolution as a text bundle for the LLM.
        Implements §8.3 of the ontologic mapping addendum.
        """
        lines = []
        lines.append(f'Token: "{resolution.token_name}"')

        if resolution.community_match:
            cm = resolution.community_match
            lines.append(
                f"Section community: {cm.community.community_id} "
                f"(confidence {cm.confidence:.2f})"
            )

        lines.append("")
        lines.append("Candidates (ranked by Bayesian score):")
        lines.append(
            "┌──┬────────────────────┬───────┬──────┬───────────────────┐"
        )
        lines.append(
            "│# │ Concept            │ Score │ Proj │ Key Evidence      │"
        )
        lines.append(
            "├──┼────────────────────┼───────┼──────┼───────────────────┤"
        )

        for idx, cs in enumerate(resolution.candidates[:max_candidates]):
            concept_local = str(cs.concept_iri).split("/")[-1].split("#")[-1]
            proj_str = (
                f"{cs.projection_confidence:.2f}"
                if cs.projection_confidence > 0
                else "—"
            )

            # Best evidence signal
            best_signal = ""
            if cs.signals:
                proj_signals = [
                    s
                    for s in cs.signals
                    if s.signal_type == "ontological_projection"
                ]
                if proj_signals:
                    best_signal = proj_signals[0].description[:30]
                else:
                    best_signal = cs.signals[0].description[:30]

            lines.append(
                f"│{idx+1:2}│ {concept_local:18s} │{cs.log_posterior:6.2f} "
                f"│{proj_str:5s} │ {best_signal:17s} │"
            )

        lines.append(
            "└──┴────────────────────┴───────┴──────┴───────────────────┘"
        )

        # Resolution recommendation
        if resolution.resolution_status == "deterministic":
            top = resolution.candidates[0]
            lines.append("")
            lines.append(
                f"DETERMINISTIC: Accept candidate 1 "
                f"(projection confidence {top.projection_confidence:.2f})"
            )
        elif resolution.resolution_status == "high_confidence":
            lines.append("")
            lines.append("HIGH CONFIDENCE: Verify candidate 1")

        return "\n".join(lines)

    @staticmethod
    def format_section_summary(resolution: SectionResolution) -> str:
        """Format a section-level summary."""
        lines = [
            f"Section: {resolution.section_iri}",
            f"  Community: {resolution.community_match.community.community_id if resolution.community_match else 'none'}"
            f" (conf: {resolution.community_match.confidence:.2f})"
            if resolution.community_match
            else "  Community: none",
            f"  Tokens: {resolution.total_tokens}",
            f"  Deterministic: {resolution.deterministic_count}",
            f"  Require LLM: {resolution.requires_llm_count}",
        ]
        return "\n".join(lines)