"""
mork_communities/recognition.py

Multi-strategy lexical recognition engine implementing the base
recognition profunctor Π_base (§5.2 of the reference architecture,
Chapter 1 of the algorithms paper).

Provides four parallel matching strategies:
1. Edit distance (Levenshtein)
2. Abbreviation expansion
3. Token overlap (Jaccard)
4. Embedding cosine similarity (optional)
"""

from __future__ import annotations

import logging
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import (
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    Tuple,
)

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, SKOS

from mork_communities.namespaces import (
    DATA_CONCEPT,
    CONCEPT_NAME,
    CONCEPT_SCHEME_PROP,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecognitionCandidate:
    """A candidate concept from lexical recognition."""
    concept_iri: URIRef
    concept_label: str
    score: float
    best_strategy: str
    strategy_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class AbbreviationDictionary:
    """
    Domain-specific abbreviation expansion dictionary.
    Grows as mappings are confirmed (Chapter 1.3 of algorithms paper).
    """
    _expansions: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    _confirmed_count: Dict[Tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))

    # Common insurance abbreviations as seed
    SEED_ABBREVIATIONS: Dict[str, List[str]] = field(default_factory=lambda: {
        "xs": ["excess", "cross"],
        "att": ["attachment"],
        "lmt": ["limit"],
        "ccy": ["currency"],
        "pct": ["percent", "percentage"],
        "shr": ["share"],
        "eff": ["effective"],
        "dt": ["date"],
        "no": ["number"],
        "amt": ["amount"],
        "pol": ["policy"],
        "agg": ["aggregate"],
        "aal": ["annual aggregate limit"],
        "aad": ["annual aggregate deductible"],
        "ded": ["deductible"],
        "sir": ["self insured retention"],
        "occ": ["occurrence"],
        "pml": ["probable maximum loss"],
        "cat": ["catastrophe"],
        "ri": ["reinsurance"],
        "qs": ["quota share"],
        "ss": ["surplus share"],
        "xl": ["excess of loss"],
        "fac": ["facultative"],
        "trt": ["treaty"],
        "insd": ["insured"],
        "pty": ["party"],
        "prl": ["peril"],
        "terr": ["territory"],
        "lob": ["line of business"],
    })

    def __post_init__(self):
        for abbr, expansions in self.SEED_ABBREVIATIONS.items():
            for exp in expansions:
                self._expansions[abbr].add(exp)

    def expand(self, token: str) -> Set[str]:
        """Get all known expansions for a token."""
        token_lower = token.lower().strip()
        return set(self._expansions.get(token_lower, set()))

    def learn(self, abbreviation: str, expansion: str) -> None:
        """Learn a new abbreviation-expansion pair from a confirmed mapping."""
        abbr_lower = abbreviation.lower().strip()
        exp_lower = expansion.lower().strip()
        self._expansions[abbr_lower].add(exp_lower)
        self._confirmed_count[(abbr_lower, exp_lower)] += 1
        logger.debug("Learned abbreviation: %s → %s", abbr_lower, exp_lower)

    def get_confidence(self, abbreviation: str, expansion: str) -> float:
        """Get confidence of an abbreviation mapping."""
        key = (abbreviation.lower(), expansion.lower())
        count = self._confirmed_count.get(key, 0)
        total = sum(
            c for (a, _), c in self._confirmed_count.items()
            if a == abbreviation.lower()
        )
        if total == 0:
            return 0.5  # seed abbreviation, no confirmation data
        return (count + 1) / (total + 2)  # Laplace smoothing


class RecognitionEngine:
    """
    Multi-strategy lexical recognition engine.

    Implements the base recognition profunctor Π_base from §5.2
    of the reference architecture and Chapter 1 of the algorithms paper.
    """

    def __init__(
        self,
        graph: Graph,
        abbreviation_dict: Optional[AbbreviationDictionary] = None,
        embedding_fn=None,
        min_score: float = 0.1,
        max_candidates: int = 10,
    ):
        self._graph = graph
        self._abbr_dict = abbreviation_dict or AbbreviationDictionary()
        self._embedding_fn = embedding_fn
        self._min_score = min_score
        self._max_candidates = max_candidates
        self._concept_labels: Dict[URIRef, List[str]] = {}
        self._load_concept_labels()

    def _load_concept_labels(self) -> None:
        """Load all concept labels from the graph."""
        g = self._graph
        for concept in g.subjects(RDF.type, DATA_CONCEPT):
            if not isinstance(concept, URIRef):
                continue
            labels = []
            # skos:prefLabel
            for label in g.objects(concept, SKOS.prefLabel):
                labels.append(str(label))
            # mork:conceptName
            for name in g.objects(concept, CONCEPT_NAME):
                labels.append(str(name))
            # Local name from IRI
            local = str(concept).split("/")[-1].split("#")[-1]
            if local not in labels:
                labels.append(local)
            self._concept_labels[concept] = labels

    def recognise(
        self, field_name: str
    ) -> List[RecognitionCandidate]:
        """
        Recognise a field name against all known DataConcepts.

        Runs four strategies in parallel and takes the best score
        per concept (Chapter 1.2 of algorithms paper).

        Parameters
        ----------
        field_name : str
            The raw field name (e.g., "xs_point", "lmt", "ccy").

        Returns
        -------
        List[RecognitionCandidate]
            Ranked candidates, best first.
        """
        candidates: Dict[URIRef, RecognitionCandidate] = {}

        for concept_iri, labels in self._concept_labels.items():
            best_score = 0.0
            best_strategy = "none"
            strategy_scores: Dict[str, float] = {}

            for label in labels:
                # Strategy 1: Normalised edit distance
                ed_score = self._edit_distance_score(field_name, label)
                strategy_scores["edit_distance"] = max(
                    strategy_scores.get("edit_distance", 0.0), ed_score
                )

                # Strategy 2: Abbreviation expansion
                abbr_score = self._abbreviation_score(field_name, label)
                strategy_scores["abbreviation"] = max(
                    strategy_scores.get("abbreviation", 0.0), abbr_score
                )

                # Strategy 3: Token overlap (Jaccard)
                token_score = self._token_overlap_score(field_name, label)
                strategy_scores["token_overlap"] = max(
                    strategy_scores.get("token_overlap", 0.0), token_score
                )

                # Strategy 4: Embedding cosine (if available)
                if self._embedding_fn is not None:
                    embed_score = self._embedding_score(field_name, label)
                    strategy_scores["embedding"] = max(
                        strategy_scores.get("embedding", 0.0), embed_score
                    )

            # Take maximum across strategies
            if strategy_scores:
                best_strategy = max(strategy_scores, key=strategy_scores.get)
                best_score = strategy_scores[best_strategy]

            if best_score >= self._min_score:
                best_label = labels[0] if labels else str(concept_iri)
                candidates[concept_iri] = RecognitionCandidate(
                    concept_iri=concept_iri,
                    concept_label=best_label,
                    score=best_score,
                    best_strategy=best_strategy,
                    strategy_scores=dict(strategy_scores),
                )

        # Sort by score descending, take top N
        ranked = sorted(
            candidates.values(), key=lambda c: c.score, reverse=True
        )
        return ranked[: self._max_candidates]

    def recognise_batch(
        self, field_names: Dict[URIRef, str]
    ) -> Dict[URIRef, List[RecognitionCandidate]]:
        """Recognise multiple fields."""
        return {
            token_iri: self.recognise(name)
            for token_iri, name in field_names.items()
        }

    # ── Strategy Implementations ──────────────────────────────────

    def _edit_distance_score(self, field_name: str, label: str) -> float:
        """Normalised Levenshtein distance score."""
        fn = self._normalise_name(field_name)
        lb = self._normalise_name(label)
        if not fn or not lb:
            return 0.0
        dist = self._levenshtein(fn, lb)
        max_len = max(len(fn), len(lb))
        if max_len == 0:
            return 1.0
        return max(0.0, 1.0 - dist / max_len)

    def _abbreviation_score(self, field_name: str, label: str) -> float:
        """
        Score based on abbreviation expansion.
        Split field name into tokens, expand each, compare to label.
        """
        tokens = self._tokenise(field_name)
        label_tokens = self._tokenise(label)

        if not tokens or not label_tokens:
            return 0.0

        # Expand each token
        expanded_variants = [[t] for t in tokens]
        for i, token in enumerate(tokens):
            expansions = self._abbr_dict.expand(token)
            if expansions:
                expanded_variants[i] = list(expansions) + [token]

        # Try all combinations (limit to avoid explosion)
        best_score = 0.0
        import itertools
        variants = list(itertools.islice(
            itertools.product(*expanded_variants), 50
        ))

        for variant in variants:
            expanded_str = " ".join(variant)
            label_str = " ".join(label_tokens)
            score = self._edit_distance_score(expanded_str, label_str)
            best_score = max(best_score, score)

            # Also try token overlap on expanded form
            expanded_set = set(v.lower() for v in variant)
            label_set = set(t.lower() for t in label_tokens)
            if expanded_set and label_set:
                intersection = expanded_set & label_set
                union = expanded_set | label_set
                jaccard = len(intersection) / len(union) if union else 0.0
                best_score = max(best_score, jaccard)

        return best_score

    def _token_overlap_score(self, field_name: str, label: str) -> float:
        """Token-level Jaccard similarity."""
        fn_tokens = set(self._tokenise(field_name))
        lb_tokens = set(self._tokenise(label))

        if not fn_tokens or not lb_tokens:
            return 0.0

        fn_lower = {t.lower() for t in fn_tokens}
        lb_lower = {t.lower() for t in lb_tokens}

        intersection = fn_lower & lb_lower
        union = fn_lower | lb_lower

        return len(intersection) / len(union) if union else 0.0

    def _embedding_score(self, field_name: str, label: str) -> float:
        """Embedding cosine similarity (requires embedding function)."""
        if self._embedding_fn is None:
            return 0.0
        try:
            e1 = self._embedding_fn(field_name)
            e2 = self._embedding_fn(label)
            # Cosine similarity
            dot = sum(a * b for a, b in zip(e1, e2))
            norm1 = math.sqrt(sum(a * a for a in e1))
            norm2 = math.sqrt(sum(b * b for b in e2))
            if norm1 == 0 or norm2 == 0:
                return 0.0
            cosine = dot / (norm1 * norm2)
            return max(0.0, (cosine + 1.0) / 2.0)  # Map [-1,1] to [0,1]
        except Exception:
            return 0.0

    # ── String Utilities ──────────────────────────────────────────

    @staticmethod
    def _normalise_name(name: str) -> str:
        """Normalise a field name or label for comparison."""
        # Split camelCase
        s = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        # Replace separators with spaces
        s = re.sub(r'[_\-./]', ' ', s)
        return s.lower().strip()

    @staticmethod
    def _tokenise(name: str) -> List[str]:
        """Tokenise a name into constituent parts."""
        # Split on camelCase boundaries
        s = re.sub(r'([a-z])([A-Z])', r'\1_\2', name)
        # Split on separators
        tokens = re.split(r'[_\-\s./]+', s)
        return [t.lower() for t in tokens if t]

    @staticmethod
    def _levenshtein(s1: str, s2: str) -> int:
        """Compute Levenshtein edit distance."""
        if len(s1) < len(s2):
            return RecognitionEngine._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)

        prev_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (c1 != c2)
                curr_row.append(min(insertions, deletions, substitutions))
            prev_row = curr_row

        return prev_row[-1]

    # ── Learning Interface ────────────────────────────────────────

    def learn_from_confirmed_mapping(
        self,
        field_name: str,
        concept_label: str,
    ) -> None:
        """
        Learn abbreviation mappings from a confirmed field-concept mapping.
        Implements the feedback loop from Chapter 12.3 of algorithms paper.
        """
        field_tokens = self._tokenise(field_name)
        label_tokens = self._tokenise(concept_label)

        # Find token-level correspondences
        for ft in field_tokens:
            for lt in label_tokens:
                # If field token is shorter than label token
                # and label token starts with field token, it's likely
                # an abbreviation
                if len(ft) < len(lt) and lt.startswith(ft[:2]):
                    self._abbr_dict.learn(ft, lt)
                elif len(ft) < len(lt) and self._levenshtein(ft, lt) > 2:
                    # Significant difference suggests abbreviation
                    self._abbr_dict.learn(ft, lt)

    @property
    def abbreviation_dict(self) -> AbbreviationDictionary:
        return self._abbr_dict