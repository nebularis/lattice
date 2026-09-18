"""
mork_communities/confidence.py

Confidence propagation through mapping DAGs.

Implements §4.6 (Definition 4.13) of the foundations paper:
the derived confidence of a compositional mapping is limited
by its weakest link.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Set

from rdflib import Graph, URIRef

from mork_communities.namespaces import (
    COMPOSITE_NARROWER_MAPPING,
    WEIGHTING,
)

logger = logging.getLogger(__name__)


class ConfidencePropagator:
    """
    Propagates confidence scores through a mapping DAG.

    conf(m) = conf_local(m) × min(conf(m₁), ..., conf(mₙ))

    where m₁...mₙ are composite children of m.

    Properties:
    - Monotonicity: conf(m) ≤ conf(mᵢ) for any child mᵢ (Prop 4.14)
    - The min function reflects that a chain is limited by its weakest link
    - Multiplicative composition ensures local uncertainty compounds
    """

    def __init__(self, graph: Graph, default_weight: int = 50):
        self._graph = graph
        self._default_weight = default_weight
        self._cache: Dict[URIRef, float] = {}

    def compute_confidence(self, mapping_iri: URIRef) -> float:
        """
        Compute the derived confidence for a mapping node.

        Recursively computes through children, caching results.
        """
        if mapping_iri in self._cache:
            return self._cache[mapping_iri]

        g = self._graph

        # Local confidence from weighting
        weighting_lit = next(g.objects(mapping_iri, WEIGHTING), None)
        local_conf = (
            int(weighting_lit) / 100.0 if weighting_lit else
            self._default_weight / 100.0
        )

        # Children
        children = list(g.objects(mapping_iri, COMPOSITE_NARROWER_MAPPING))

        if not children:
            # Leaf node
            self._cache[mapping_iri] = local_conf
            return local_conf

        # Recursive: min over children
        child_confs = [self.compute_confidence(c) for c in children]
        min_child = min(child_confs) if child_confs else 1.0

        result = local_conf * min_child
        self._cache[mapping_iri] = result
        return result

    def compute_all(self, root_iris: Set[URIRef]) -> Dict[URIRef, float]:
        """Compute confidence for all mappings reachable from roots."""
        self._cache.clear()
        result = {}
        for root in root_iris:
            result[root] = self.compute_confidence(root)
            # Also include children
            self._collect_children_confidence(root, result)
        return result

    def _collect_children_confidence(
        self, mapping_iri: URIRef, result: Dict[URIRef, float]
    ) -> None:
        g = self._graph
        for child in g.objects(mapping_iri, COMPOSITE_NARROWER_MAPPING):
            if child not in result:
                result[child] = self.compute_confidence(child)
                self._collect_children_confidence(child, result)