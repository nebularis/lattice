"""
mork_communities/precedence.py

Precedence Derivation and DAG Evaluation (Catamorphism).

Implements §2.5 (Definition 2.16-2.19), §5.1-5.2, Chapter 10 of the
algorithms paper, and §12.1 of the reference architecture.

Derives the precedence partial order from structural relationships
and evaluates the mapping DAG via topological sort.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from mork_communities.namespaces import (
    DATA_MAPPING,
    EXACT_TBOX_MATCH,
    EXACT_RBOX_MATCH,
    EXACT_ABOX_MATCH,
    INVERSE_RBOX_MATCH,
    COMPOSITE_BROADER_MAPPING,
    COMPOSITE_NARROWER_MAPPING,
    BROADER_APPLICATIVE,
    HAS_MAPPING,
)

logger = logging.getLogger(__name__)

# MORK-specific namespace for deferred/dependent/precedes
MORK_NS = "http://www.nebularis.org/ontologies/Mork#"
DEFERRED_MAPPING = URIRef(MORK_NS + "deferredMapping")
DEPENDENT_MAPPING = URIRef(MORK_NS + "dependentMapping")
PRECEDES = URIRef(MORK_NS + "precedes")
IDENTITY_TEMPLATE = URIRef(MORK_NS + "identityTemplate")
IDENTITY_TEMPLATE_MAPPING = URIRef(MORK_NS + "identityTemplateMapping")


@dataclass
class MappingNode:
    """A node in the precedence DAG."""
    mapping_iri: URIRef
    tbox_match: Optional[URIRef] = None
    rbox_match: Optional[URIRef] = None
    abox_match: Optional[URIRef] = None
    inverse_rbox: Optional[URIRef] = None
    parent_mapping: Optional[URIRef] = None
    applicative_parent: Optional[URIRef] = None
    children: List[URIRef] = field(default_factory=list)
    deferred: List[URIRef] = field(default_factory=list)
    dependent_on: List[URIRef] = field(default_factory=list)
    identity_template: Optional[str] = None
    data_reference: Optional[str] = None
    resolution_method: str = "unknown"

    @property
    def is_tbox(self) -> bool:
        return self.tbox_match is not None

    @property
    def is_rbox(self) -> bool:
        return self.rbox_match is not None or self.inverse_rbox is not None

    @property
    def is_abox(self) -> bool:
        return self.abox_match is not None


@dataclass
class EvaluationResult:
    """Result of evaluating a single mapping node."""
    mapping_iri: URIRef
    axioms: List[Tuple[URIRef, URIRef, Any]]  # (subject, predicate, object) triples
    individual_iri: Optional[URIRef] = None  # For A-Box: the created individual
    context: Dict[str, Any] = field(default_factory=dict)


class PrecedenceDeriver:
    """
    Derives the precedence partial order from structural relationships.

    Implements Definition 2.16-2.19 of the foundations paper and
    Chapter 10 of the algorithms paper.

    Precedence rules:
    P1: compositeNarrowerMapping⁻¹ ⊑ precedes  (parent before children)
    P2: broaderApplicative⁻¹ ⊑ precedes  (context before application)
    P3: dependentMapping⁻¹ ⊑ precedes  (dependency before dependent)
    P6-P7: T-Box before A-Box (SWRL rule equivalent)
    P8: Identity resolution before use
    """

    def __init__(self, graph: Graph):
        self._graph = graph

    def derive_precedence(
        self, mapping_iris: Set[URIRef]
    ) -> Dict[URIRef, Set[URIRef]]:
        """
        Derive the precedence relation over a set of mappings.

        Returns a dict: mapping_iri -> set of mappings that must come BEFORE it.
        """
        g = self._graph
        precedes: Dict[URIRef, Set[URIRef]] = defaultdict(set)

        for m in mapping_iris:
            # P1: compositional — parent precedes children
            parent = next(g.objects(m, COMPOSITE_BROADER_MAPPING), None)
            if parent and parent in mapping_iris:
                precedes[m].add(parent)

            # P2: applicative — context parent precedes child
            app_parent = next(g.objects(m, BROADER_APPLICATIVE), None)
            if app_parent and app_parent in mapping_iris:
                precedes[m].add(app_parent)

            # P3: dependency — strict precedence
            for dep in g.objects(m, DEPENDENT_MAPPING):
                if dep in mapping_iris:
                    precedes[m].add(dep)

            # P6-P7: T-Box before A-Box
            # If m is a Datum-like mapping that defers to a T-Box mapping
            for deferred in g.objects(m, DEFERRED_MAPPING):
                if deferred in mapping_iris:
                    # Check if deferred has T-Box match
                    if any(g.objects(deferred, EXACT_TBOX_MATCH)):
                        precedes[m].add(deferred)

            # P8: Identity template resolution
            for ident in g.objects(m, IDENTITY_TEMPLATE_MAPPING):
                if ident in mapping_iris:
                    precedes[m].add(ident)

        # Transitive closure (P4)
        changed = True
        while changed:
            changed = False
            for m in mapping_iris:
                predecessors = set(precedes[m])
                for pred in predecessors:
                    for pred_pred in precedes[pred]:
                        if pred_pred not in precedes[m]:
                            precedes[m].add(pred_pred)
                            changed = True

        return dict(precedes)

    def topological_sort(
        self,
        mapping_iris: Set[URIRef],
        precedence: Dict[URIRef, Set[URIRef]],
    ) -> List[URIRef]:
        """
        Kahn's algorithm for topological sort with stable IRI-string ordering.

        Implements Definition 2.19 (Execution Schedule) and Chapter 10.3
        of the algorithms paper.

        Raises ValueError if a cycle is detected (SHACL Shape M7 violation).
        """
        # Compute in-degrees
        in_degree: Dict[URIRef, int] = {m: 0 for m in mapping_iris}
        for m, preds in precedence.items():
            in_degree[m] = len(preds & mapping_iris)

        # Initialise queue with nodes that have no predecessors
        # Use sorted IRI strings for deterministic ordering
        queue = sorted(
            [m for m in mapping_iris if in_degree.get(m, 0) == 0],
            key=str,
        )
        result = []
        visited = set()

        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            result.append(node)

            # Find nodes whose last predecessor was just processed
            for m in mapping_iris:
                if m in visited:
                    continue
                preds = precedence.get(m, set()) & mapping_iris
                if preds <= visited:
                    if m not in queue:
                        queue.append(m)
                        queue.sort(key=str)

        if len(result) != len(mapping_iris):
            unvisited = mapping_iris - visited
            raise ValueError(
                f"Cycle detected in precedence graph. "
                f"Unresolvable mappings: {unvisited}"
            )

        return result


class DAGEvaluator:
    """
    Evaluates a mapping DAG via catamorphism (structural fold).

    Implements §5.1 (Definition 5.1) and Chapter 11 of the algorithms paper.
    Processes nodes in topological order, ensuring every dependency
    is resolved before the dependent node is evaluated.
    """

    def __init__(
        self,
        graph: Graph,
        identity_resolver: Optional[IdentityTemplateResolver] = None,
    ):
        self._graph = graph
        self._identity_resolver = identity_resolver or IdentityTemplateResolver()
        self._deriver = PrecedenceDeriver(graph)

    def evaluate(
        self,
        mapping_iris: Set[URIRef],
        input_data: Dict[str, Any],
    ) -> List[EvaluationResult]:
        """
        Evaluate all mappings in topological order.

        Parameters
        ----------
        mapping_iris : Set[URIRef]
            The set of mapping IRIs to evaluate.
        input_data : Dict[str, Any]
            The source data, keyed by field name or path.

        Returns
        -------
        List[EvaluationResult]
            Results in evaluation order, with generated axioms.
        """
        # Derive precedence
        precedence = self._deriver.derive_precedence(mapping_iris)

        # Topological sort
        evaluation_order = self._deriver.topological_sort(mapping_iris, precedence)

        # Evaluate in order
        results: Dict[URIRef, EvaluationResult] = {}
        for mapping_iri in evaluation_order:
            result = self._evaluate_node(mapping_iri, input_data, results)
            results[mapping_iri] = result

        return [results[m] for m in evaluation_order]

    def _evaluate_node(
        self,
        mapping_iri: URIRef,
        input_data: Dict[str, Any],
        prior_results: Dict[URIRef, EvaluationResult],
    ) -> EvaluationResult:
        """
        Evaluate a single mapping node.

        Implements the catamorphism step (§5.1, Chapter 11).
        """
        g = self._graph
        result = EvaluationResult(mapping_iri=mapping_iri, axioms=[])

        # Determine mapping type
        tbox = next(g.objects(mapping_iri, EXACT_TBOX_MATCH), None)
        rbox = next(g.objects(mapping_iri, EXACT_RBOX_MATCH), None)
        inv_rbox = next(g.objects(mapping_iri, INVERSE_RBOX_MATCH), None)
        abox = next(g.objects(mapping_iri, EXACT_ABOX_MATCH), None)

        # Get parent context (for broaderApplicative — Kleisli composition)
        app_parent = next(g.objects(mapping_iri, BROADER_APPLICATIVE), None)
        parent_result = prior_results.get(app_parent) if app_parent else None

        if tbox is not None:
            # T-Box evaluation: class axiom
            result.axioms.append((tbox, RDF.type, URIRef(str(RDFS.Class))))
            # If there's a deferred mapping, create subclass axiom
            for deferred in g.subjects(DEFERRED_MAPPING, mapping_iri):
                deferred_tbox = next(g.objects(deferred, EXACT_TBOX_MATCH), None)
                if deferred_tbox:
                    result.axioms.append((tbox, RDFS.subClassOf, deferred_tbox))

        elif abox is not None or (parent_result and tbox is None and rbox is None):
            # A-Box evaluation: individual creation
            # Resolve identity template
            individual_iri = self._resolve_identity(mapping_iri, input_data, parent_result)
            result.individual_iri = individual_iri

            if tbox is None and parent_result:
                # Datum-like: type from deferred T-Box mapping
                for deferred in g.objects(mapping_iri, DEFERRED_MAPPING):
                    d_tbox = next(g.objects(deferred, EXACT_TBOX_MATCH), None)
                    if d_tbox:
                        result.axioms.append((individual_iri, RDF.type, d_tbox))

            if abox is not None:
                result.axioms.append((individual_iri, RDF.type, abox))

        if rbox is not None or inv_rbox is not None:
            # R-Box evaluation: property assertion (Contextual gluing — §2.4)
            property_iri = rbox or inv_rbox
            is_inverse = inv_rbox is not None

            # Get subject from parent context
            subject = None
            if parent_result and parent_result.individual_iri:
                subject = parent_result.individual_iri
            elif parent_result:
                # Look for individual in parent's axioms
                for s, p, o in parent_result.axioms:
                    if p == RDF.type:
                        subject = s
                        break

            # Get value from input data
            data_ref = self._get_data_reference(mapping_iri)
            value = input_data.get(data_ref) if data_ref else None

            if subject and value is not None:
                if is_inverse:
                    result.axioms.append((value, property_iri, subject))
                else:
                    obj = self._coerce_value(value, property_iri)
                    result.axioms.append((subject, property_iri, obj))

            result.context["parent_individual"] = subject

        return result

    def _resolve_identity(
        self,
        mapping_iri: URIRef,
        input_data: Dict[str, Any],
        parent_result: Optional[EvaluationResult],
    ) -> URIRef:
        """
        Resolve the identity template to produce an individual IRI.
        Implements Chapter 11.2 of the algorithms paper.
        """
        g = self._graph

        # Look for identity template
        template_str = None
        for tmpl in g.objects(mapping_iri, IDENTITY_TEMPLATE):
            template_str = str(tmpl)
            break

        if template_str:
            return self._identity_resolver.resolve(template_str, input_data)

        # Fallback: generate from mapping IRI + input hash
        data_hash = hashlib.sha256(
            str(sorted(input_data.items())).encode()
        ).hexdigest()[:12]
        local = str(mapping_iri).split("/")[-1].split("#")[-1]
        return URIRef(f"http://www.nebularis.org/instances/{local}_{data_hash}")

    def _get_data_reference(self, mapping_iri: URIRef) -> Optional[str]:
        """Get the data reference (source field path) for a mapping."""
        g = self._graph
        # Look for sourceRef or dataReference property
        for pred in [
            URIRef(MORK_NS + "sourceRef"),
            URIRef(MORK_NS + "dataReference"),
        ]:
            ref = next(g.objects(mapping_iri, pred), None)
            if ref:
                return str(ref)
        return None

    def _coerce_value(self, value: Any, property_iri: URIRef) -> Any:
        """Coerce a value to the appropriate RDF representation."""
        if isinstance(value, (int, float)):
            return Literal(value, datatype=XSD.decimal)
        elif isinstance(value, str):
            return Literal(value, datatype=XSD.string)
        elif isinstance(value, URIRef):
            return value
        return Literal(str(value))


class IdentityTemplateResolver:
    """
    Resolves identity templates to produce individual IRIs.

    Implements §4.5 (Definition 4.11) and Chapter 11.2 of the
    algorithms paper.

    Template format: "prefix_{placeholder1}_{placeholder2}"
    Placeholders are replaced with input values.
    """

    def __init__(
        self,
        base_namespace: str = "http://www.nebularis.org/instances/",
    ):
        self._base_ns = base_namespace
        self._cache: Dict[str, URIRef] = {}

    def resolve(
        self,
        template: str,
        input_data: Dict[str, Any],
    ) -> URIRef:
        """
        Resolve a template string with input data.

        Parameters
        ----------
        template : str
            Template like "tank_{layer_no}_{attachment}_{capacity}"
        input_data : Dict[str, Any]
            Input values keyed by field name.

        Returns
        -------
        URIRef
            The resolved individual IRI.
        """
        resolved = template
        for match in re.finditer(r'\{(\w+)\}', template):
            placeholder = match.group(1)
            value = input_data.get(placeholder, "unknown")
            resolved = resolved.replace(match.group(0), str(value))

        # Construct IRI
        iri_str = f"{self._base_ns}{resolved}"

        # Check cache for idempotence (Theorem 5.3)
        if iri_str in self._cache:
            return self._cache[iri_str]

        iri = URIRef(iri_str)
        self._cache[iri_str] = iri
        return iri