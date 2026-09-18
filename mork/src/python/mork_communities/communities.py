"""
mork_communities/communities.py

Semantic Community discovery via the Leiden algorithm on concept
co-occurrence graphs.

Implements §10.4, §10.5, and §10.8 of the addendum.
"""

from __future__ import annotations

import logging
import math
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import (
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    Tuple,
)

import numpy as np

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD, SKOS

from mork_communities.namespaces import *
from mork_communities.graph_client import (
    MorkGraphClient,
    SectionObservationRecord,
)

logger = logging.getLogger(__name__)

# Try to import the Leiden algorithm; fall back to Louvain via networkx
try:
    import leidenalg
    import igraph as ig

    _HAS_LEIDEN = True
except ImportError:
    _HAS_LEIDEN = False
    logger.warning(
        "leidenalg not installed; falling back to networkx Louvain. "
        "Install with: pip install leidenalg python-igraph"
    )

try:
    import networkx as nx
    from networkx.algorithms.community import louvain_communities

    _HAS_NETWORKX = True
except ImportError:
    _HAS_NETWORKX = False


@dataclass
class SemanticCommunity:
    """
    A discovered cluster of DataConcepts that co-occur in structural sections.

    Attributes
    ----------
    community_id : str
        Unique identifier.
    members : Dict[URIRef, float]
        Mapping from DataConcept IRI to membership weight μ(c) ∈ [0, 1].
    coherence : float
        Community coherence ∈ [0, 1] (Definition 10.5.2).
    observation_count : int
        Number of section observations matching this community.
    iri : Optional[URIRef]
        IRI in the MORK graph (set after materialisation).
    """

    community_id: str
    members: Dict[URIRef, float]
    coherence: float = 0.0
    observation_count: int = 0
    iri: Optional[URIRef] = None

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def member_set(self) -> FrozenSet[URIRef]:
        return frozenset(self.members.keys())


@dataclass
class CommunityScheme:
    """
    A versioned container for a set of discovered communities.

    Attributes
    ----------
    version : str
        Version identifier.
    algorithm : str
        Detection algorithm name.
    resolution : float
        Resolution parameter used.
    communities : List[SemanticCommunity]
        The discovered communities.
    iri : Optional[URIRef]
        IRI in the MORK graph.
    """

    version: str
    algorithm: str
    resolution: float
    communities: List[SemanticCommunity] = field(default_factory=list)
    iri: Optional[URIRef] = None


class CommunityDiscovery:
    """
    Discovers semantic communities from accumulated mapping runs.

    Implements Algorithm CommunityDiscovery (§10.8.2 of the addendum).
    """

    def __init__(
        self,
        graph_client: MorkGraphClient,
        resolution_min: float = 0.5,
        resolution_max: float = 2.0,
        resolution_steps: int = 10,
        min_community_size: int = 2,
        coherence_threshold: float = 0.3,
        quality_weights: Tuple[float, float, float] = (0.3, 0.4, 0.3),
        match_threshold: float = 0.3,
    ):
        self._client = graph_client
        self._res_min = resolution_min
        self._res_max = resolution_max
        self._res_steps = resolution_steps
        self._min_size = min_community_size
        self._coh_threshold = coherence_threshold
        self._alpha, self._beta, self._gamma = quality_weights
        self._match_threshold = match_threshold

    def discover(
        self,
        observations: Optional[List[SectionObservationRecord]] = None,
    ) -> CommunityScheme:
        """
        Run the full community discovery pipeline.

        Parameters
        ----------
        observations : optional
            Pre-extracted section observations. If None, extracts from graph.

        Returns
        -------
        CommunityScheme
            The discovered community scheme with all communities.
        """
        # Step 1: Extract section observations
        if observations is None:
            observations = self._client.extract_section_observations()

        if len(observations) < 3:
            logger.warning(
                "Only %d observations; need ≥3 for meaningful communities",
                len(observations),
            )
            return CommunityScheme(
                version=self._generate_version(),
                algorithm="none",
                resolution=0.0,
            )

        # Step 2: Build co-occurrence graph
        concepts, adj_matrix, degree = self._build_cooccurrence_graph(
            observations
        )

        if len(concepts) < self._min_size:
            logger.warning("Only %d concepts; too few for communities", len(concepts))
            return CommunityScheme(
                version=self._generate_version(),
                algorithm="none",
                resolution=0.0,
            )

        # Step 3: Multi-resolution community detection
        best_partition, best_resolution, best_quality = (
            self._multi_resolution_detection(
                concepts, adj_matrix, degree, observations
            )
        )

        if best_partition is None:
            logger.warning("No valid partition found")
            return CommunityScheme(
                version=self._generate_version(),
                algorithm="none",
                resolution=0.0,
            )

        # Step 4: Compute community profiles
        communities = self._compute_profiles(
            best_partition, concepts, observations, adj_matrix, degree
        )

        algorithm = "Leiden" if _HAS_LEIDEN else "Louvain"
        scheme = CommunityScheme(
            version=self._generate_version(),
            algorithm=algorithm,
            resolution=best_resolution,
            communities=communities,
        )

        logger.info(
            "Discovered %d communities (algorithm=%s, resolution=%.3f, "
            "quality=%.4f)",
            len(communities),
            algorithm,
            best_resolution,
            best_quality,
        )

        return scheme

    # ── Step 2: Co-occurrence Graph ──────────────────────────────

    def _build_cooccurrence_graph(
        self, observations: List[SectionObservationRecord]
    ) -> Tuple[List[URIRef], np.ndarray, np.ndarray]:
        """
        Build the weighted, normalised co-occurrence graph.

        Returns (concept_list, adjacency_matrix, degree_vector).
        """
        # Collect all concepts
        all_concepts: Set[URIRef] = set()
        for obs in observations:
            all_concepts.update(obs.concepts)

        concept_list = sorted(all_concepts, key=str)
        concept_idx = {c: i for i, c in enumerate(concept_list)}
        n = len(concept_list)

        # Build raw co-occurrence matrix and degree vector
        W = np.zeros((n, n), dtype=np.float64)
        degree = np.zeros(n, dtype=np.float64)

        for obs in observations:
            concepts = [c for c in obs.concepts if c in concept_idx]
            for c in concepts:
                degree[concept_idx[c]] += 1
            for i in range(len(concepts)):
                for j in range(i + 1, len(concepts)):
                    ci = concept_idx[concepts[i]]
                    cj = concept_idx[concepts[j]]
                    W[ci, cj] += 1
                    W[cj, ci] += 1

        # Normalise: overlap coefficient
        A = np.zeros((n, n), dtype=np.float64)
        for i in range(n):
            for j in range(i + 1, n):
                if W[i, j] > 0 and degree[i] > 0 and degree[j] > 0:
                    A[i, j] = W[i, j] / min(degree[i], degree[j])
                    A[j, i] = A[i, j]

        return concept_list, A, degree

    # ── Step 3: Multi-Resolution Detection ───────────────────────

    def _multi_resolution_detection(
        self,
        concepts: List[URIRef],
        adj_matrix: np.ndarray,
        degree: np.ndarray,
        observations: List[SectionObservationRecord],
    ) -> Tuple[Optional[Dict[int, Set[int]]], float, float]:
        """
        Run community detection at multiple resolutions and pick the best.
        """
        n = len(concepts)
        resolutions = np.linspace(
            self._res_min, self._res_max, self._res_steps
        )

        best_partition = None
        best_quality = -math.inf
        best_res = self._res_min

        for gamma in resolutions:
            partition = self._detect_communities(adj_matrix, gamma)

            # Filter small communities
            partition = {
                k: v
                for k, v in partition.items()
                if len(v) >= self._min_size
            }

            if not partition:
                continue

            quality = self._compute_quality(
                partition, concepts, adj_matrix, degree, observations
            )

            if quality > best_quality:
                best_quality = quality
                best_partition = partition
                best_res = gamma

        return best_partition, best_res, best_quality

    def _detect_communities(
        self, adj_matrix: np.ndarray, resolution: float
    ) -> Dict[int, Set[int]]:
        """
        Run community detection at a given resolution.
        Uses Leiden if available, otherwise Louvain via networkx.
        """
        n = adj_matrix.shape[0]

        if _HAS_LEIDEN:
            return self._detect_leiden(adj_matrix, resolution)
        elif _HAS_NETWORKX:
            return self._detect_louvain_nx(adj_matrix, resolution)
        else:
            # Fallback: simple connected-component-like clustering
            return self._detect_simple(adj_matrix, resolution)

    def _detect_leiden(
        self, adj_matrix: np.ndarray, resolution: float
    ) -> Dict[int, Set[int]]:
        """Leiden algorithm via python-igraph + leidenalg."""
        n = adj_matrix.shape[0]

        # Build igraph from adjacency matrix
        edges = []
        weights = []
        for i in range(n):
            for j in range(i + 1, n):
                if adj_matrix[i, j] > 0:
                    edges.append((i, j))
                    weights.append(adj_matrix[i, j])

        if not edges:
            return {}

        g = ig.Graph(n=n, edges=edges, directed=False)
        g.es["weight"] = weights

        partition = leidenalg.find_partition(
            g,
            leidenalg.RBConfigurationVertexPartition,
            weights="weight",
            resolution_parameter=resolution,
        )

        result: Dict[int, Set[int]] = defaultdict(set)
        for node_idx, comm_idx in enumerate(partition.membership):
            result[comm_idx].add(node_idx)

        return dict(result)

    def _detect_louvain_nx(
        self, adj_matrix: np.ndarray, resolution: float
    ) -> Dict[int, Set[int]]:
        """Louvain algorithm via networkx."""
        n = adj_matrix.shape[0]
        G = nx.Graph()
        G.add_nodes_from(range(n))

        for i in range(n):
            for j in range(i + 1, n):
                if adj_matrix[i, j] > 0:
                    G.add_edge(i, j, weight=adj_matrix[i, j])

        if G.number_of_edges() == 0:
            return {}

        communities_gen = louvain_communities(
            G, weight="weight", resolution=resolution, seed=42
        )

        result: Dict[int, Set[int]] = {}
        for idx, comm in enumerate(communities_gen):
            result[idx] = set(comm)

        return result

    def _detect_simple(
        self, adj_matrix: np.ndarray, resolution: float
    ) -> Dict[int, Set[int]]:
        """Simple threshold-based clustering fallback."""
        n = adj_matrix.shape[0]
        threshold = 1.0 / resolution  # Higher resolution → lower threshold
        visited = set()
        communities: Dict[int, Set[int]] = {}
        comm_id = 0

        for i in range(n):
            if i in visited:
                continue
            # BFS from i
            cluster = set()
            queue = [i]
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                cluster.add(node)
                for j in range(n):
                    if j not in visited and adj_matrix[node, j] >= threshold:
                        queue.append(j)
            if cluster:
                communities[comm_id] = cluster
                comm_id += 1

        return communities

    # ── Quality Metric ────────────────────────────────────────────

    def _compute_quality(
        self,
        partition: Dict[int, Set[int]],
        concepts: List[URIRef],
        adj_matrix: np.ndarray,
        degree: np.ndarray,
        observations: List[SectionObservationRecord],
    ) -> float:
        """
        Compute the quality metric (Definition 10.8.1):
        Quality = α·Modularity + β·MeanCoherence + γ·Coverage
        """
        mod = self._compute_modularity(partition, adj_matrix, degree)
        coh = self._compute_mean_coherence(partition, adj_matrix)
        cov = self._compute_coverage(partition, concepts, observations)

        return self._alpha * mod + self._beta * coh + self._gamma * cov

    def _compute_modularity(
        self,
        partition: Dict[int, Set[int]],
        adj_matrix: np.ndarray,
        degree: np.ndarray,
    ) -> float:
        """Standard Newman-Girvan modularity."""
        n = adj_matrix.shape[0]
        m = np.sum(adj_matrix) / 2.0
        if m == 0:
            return 0.0

        # Build membership array
        membership = np.zeros(n, dtype=int)
        for comm_id, members in partition.items():
            for node in members:
                membership[node] = comm_id

        Q = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if membership[i] == membership[j]:
                    ki = np.sum(adj_matrix[i, :])
                    kj = np.sum(adj_matrix[j, :])
                    Q += adj_matrix[i, j] - (ki * kj) / (2.0 * m)
        Q /= m  # 1/(2m) for the pair, but we sum i<j so factor is 1/m

        return Q

    def _compute_mean_coherence(
        self,
        partition: Dict[int, Set[int]],
        adj_matrix: np.ndarray,
    ) -> float:
        """Mean coherence across communities."""
        if not partition:
            return 0.0

        coherences = []
        for members in partition.values():
            member_list = sorted(members)
            if len(member_list) < 2:
                continue

            numerator = 0.0
            denominator = 0.0
            for i in range(len(member_list)):
                for j in range(i + 1, len(member_list)):
                    ci, cj = member_list[i], member_list[j]
                    numerator += adj_matrix[ci, cj]
                    denominator += 1.0

            if denominator > 0:
                coherences.append(numerator / denominator)

        return np.mean(coherences) if coherences else 0.0

    def _compute_coverage(
        self,
        partition: Dict[int, Set[int]],
        concepts: List[URIRef],
        observations: List[SectionObservationRecord],
    ) -> float:
        """
        Fraction of observations matched by at least one community.
        """
        if not observations:
            return 0.0

        # Build community concept sets
        community_sets = []
        for members in partition.values():
            community_sets.append(
                frozenset(concepts[i] for i in members)
            )

        matched = 0
        for obs in observations:
            for comm_concepts in community_sets:
                intersection = obs.concepts & comm_concepts
                union_size = len(obs.concepts | comm_concepts)
                if union_size > 0:
                    jaccard = len(intersection) / union_size
                    if jaccard >= self._match_threshold:
                        matched += 1
                        break

        return matched / len(observations)

    # ── Step 4: Community Profiles ────────────────────────────────

    def _compute_profiles(
        self,
        partition: Dict[int, Set[int]],
        concepts: List[URIRef],
        observations: List[SectionObservationRecord],
        adj_matrix: np.ndarray,
        degree: np.ndarray,
    ) -> List[SemanticCommunity]:
        """
        Compute membership weights and coherence for each community.
        """
        communities = []

        for comm_id, member_indices in partition.items():
            member_concepts = frozenset(concepts[i] for i in member_indices)

            # Find matching observations
            matching_obs = []
            for obs in observations:
                overlap = obs.concepts & member_concepts
                if len(overlap) >= len(obs.concepts) / 2:
                    matching_obs.append(obs)

            total_matching = len(matching_obs)
            if total_matching == 0:
                continue

            # Compute membership weights
            concept_counts: Counter = Counter()
            for obs in matching_obs:
                for c in member_concepts:
                    if c in obs.concepts:
                        concept_counts[c] += 1

            members: Dict[URIRef, float] = {}
            for c in member_concepts:
                members[c] = concept_counts[c] / total_matching

            # Compute coherence (Definition 10.5.2)
            member_list = sorted(member_indices)
            numerator = 0.0
            denominator = 0.0
            for i in range(len(member_list)):
                for j in range(i + 1, len(member_list)):
                    ci, cj = member_list[i], member_list[j]
                    wi = members.get(concepts[ci], 0.0)
                    wj = members.get(concepts[cj], 0.0)
                    numerator += wi * wj * adj_matrix[ci, cj]
                    denominator += wi * wj

            coherence = numerator / denominator if denominator > 0 else 0.0

            if coherence < self._coh_threshold:
                continue

            community = SemanticCommunity(
                community_id=f"comm_{comm_id}",
                members=members,
                coherence=coherence,
                observation_count=total_matching,
            )
            communities.append(community)

        return communities

    @staticmethod
    def _generate_version() -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        short_uuid = uuid.uuid4().hex[:8]
        return f"v_{ts}_{short_uuid}"


class CommunityMaterialiser:
    """
    Materialises SemanticCommunity and CommunityScheme instances
    into the MORK RDF graph.
    """

    def __init__(
        self,
        graph: Graph,
        base_namespace: str = "http://www.nebularis.org/communities/",
    ):
        self._graph = graph
        self._ns = base_namespace

    def materialise_scheme(self, scheme: CommunityScheme) -> URIRef:
        """
        Write a CommunityScheme and all its communities to the graph.
        Returns the scheme IRI.
        """
        g = self._graph

        # Create scheme IRI
        scheme_iri = URIRef(f"{self._ns}scheme/{scheme.version}")
        scheme.iri = scheme_iri

        g.add((scheme_iri, RDF.type, COMMUNITY_SCHEME))
        g.add((scheme_iri, RDF.type, SKOS.ConceptScheme))
        g.add(
            (
                scheme_iri,
                COMMUNITY_SCHEME_VERSION,
                Literal(scheme.version, datatype=XSD.string),
            )
        )
        g.add(
            (
                scheme_iri,
                DETECTION_ALGORITHM,
                Literal(scheme.algorithm, datatype=XSD.string),
            )
        )
        g.add(
            (
                scheme_iri,
                DETECTION_RESOLUTION,
                Literal(scheme.resolution, datatype=XSD.decimal),
            )
        )

        # Materialise each community
        for community in scheme.communities:
            comm_iri = self._materialise_community(community, scheme_iri)

        logger.info(
            "Materialised scheme %s with %d communities",
            scheme_iri,
            len(scheme.communities),
        )

        return scheme_iri

    def _materialise_community(
        self, community: SemanticCommunity, scheme_iri: URIRef
    ) -> URIRef:
        """Write a single SemanticCommunity to the graph."""
        g = self._graph

        comm_iri = URIRef(
            f"{self._ns}community/{community.community_id}"
        )
        community.iri = comm_iri

        g.add((comm_iri, RDF.type, SEMANTIC_COMMUNITY))
        g.add((comm_iri, RDF.type, SKOS.Collection))
        g.add((comm_iri, COMMUNITY_SCHEME_PROP, scheme_iri))
        g.add((comm_iri, SKOS.inScheme, scheme_iri))
        g.add(
            (
                comm_iri,
                COMMUNITY_SIZE,
                Literal(community.size, datatype=XSD.integer),
            )
        )
        g.add(
            (
                comm_iri,
                COMMUNITY_OBSERVATION_COUNT,
                Literal(community.observation_count, datatype=XSD.integer),
            )
        )
        g.add(
            (
                comm_iri,
                COMMUNITY_COHERENCE,
                Literal(community.coherence, datatype=XSD.decimal),
            )
        )

        # Materialise memberships
        for concept_iri, weight in community.members.items():
            membership_iri = URIRef(
                f"{comm_iri}/membership/{str(concept_iri).split('/')[-1].split('#')[-1]}"
            )
            g.add((membership_iri, RDF.type, COMMUNITY_MEMBERSHIP))
            g.add((comm_iri, HAS_COMMUNITY_MEMBERSHIP, membership_iri))
            g.add((membership_iri, MEMBER_CONCEPT, concept_iri))
            g.add(
                (
                    membership_iri,
                    COMMUNITY_MEMBER_WEIGHT,
                    Literal(round(weight, 4), datatype=XSD.decimal),
                )
            )
            # Also add concept as skos:member of the collection
            g.add((comm_iri, SKOS.member, concept_iri))

        return comm_iri