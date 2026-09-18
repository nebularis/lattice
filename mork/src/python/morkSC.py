"""
MORK Compiler-Agent

Compiles MORK mapping graphs (ShapeMapping, RuleMapping, QueryTemplate instances)
into executable SHACL shapes, SWRL rules, and SPARQL query templates.

The compiler implements Stage 4 of the Product Definition Compilation Pipeline
(Foundations §5.4). It is deterministic: given identical MORK graph input, it
produces identical executable artefacts (Theorem 5.10).

Architecture:
    1. Load and validate the MORK mapping graph
    2. Build the precedence DAG and compute topological sort
    3. For each GenerativeMapping in precedence order:
       a. Resolve parameter bindings
       b. Instantiate template (if present)
       c. Generate the target artefact (SHACL shape / SWRL rule / SPARQL template)
    4. Assemble outputs into a named graph with provenance links
    5. Validate generated artefacts against Meta-SHACL shapes

Requirements:
    pip install rdflib pyshacl
"""

from __future__ import annotations

import hashlib
import logging
import json
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from rdflib import (
    BNode,
    Graph,
    Literal,
    Namespace,
    URIRef,
)
from rdflib.collection import Collection as RDFCollection
from rdflib.namespace import OWL, RDF, RDFS, XSD
from rdflib.term import Identifier, Node

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------

MORK = Namespace("http://www.nebularis.org/ontologies/Mork#")
SH = Namespace("http://www.w3.org/ns/shacl#")
SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
SWRLB = Namespace("http://www.w3.org/2003/11/swrlb#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
DCT = Namespace("http://purl.org/dc/terms/")


# ---------------------------------------------------------------------------
# Domain value objects
# ---------------------------------------------------------------------------

class ParamType(Enum):
    NUMERIC = "Numeric"
    CONCEPT = "Concept"
    PATH = "Path"
    STRING = "String"
    DURATION = "Duration"


class Severity(Enum):
    VIOLATION = "Violation"
    WARNING = "Warning"
    INFO = "Info"

    def to_sh(self) -> URIRef:
        return SH[self.value]


class ReviewStatus(Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    DEPRECATED = "DEPRECATED"


class TargetMode(Enum):
    TARGET_CLASS = "targetClass"
    TARGET_OBJECTS_OF = "targetObjectsOf"
    TARGET_SUBJECTS_OF = "targetSubjectsOf"
    TARGET_NODE = "targetNode"


@dataclass(frozen=True)
class ParameterBinding:
    """A resolved parameter binding from the MORK graph."""
    name: str
    param_type: ParamType
    value: Any  # URIRef, Literal, or list of URIRef (for Path)
    raw_node: URIRef  # the ParameterBinding individual in the graph

    def __repr__(self) -> str:
        return f"Param({self.name}:{self.param_type.value}={self.value})"


@dataclass(frozen=True)
class TargetingSpec:
    """Resolved targeting specification."""
    mode: TargetMode
    target: URIRef
    jurisdiction: Optional[URIRef] = None
    effective_from: Optional[Literal] = None
    effective_until: Optional[Literal] = None
    raw_node: URIRef = None


@dataclass(frozen=True)
class ProvenanceRecord:
    """Resolved provenance metadata."""
    creator: Optional[str] = None
    created: Optional[str] = None
    input_hash: Optional[str] = None
    llm_model_id: Optional[str] = None
    llm_confidence: Optional[float] = None
    review_status: Optional[ReviewStatus] = None


@dataclass
class CompilationResult:
    """The output of compiling a single GenerativeMapping."""
    source_mapping: URIRef
    artefact_graph: Graph
    artefact_root: URIRef
    artefact_type: str  # "SHACL" | "SWRL" | "SPARQL"
    provenance: Optional[ProvenanceRecord] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


@dataclass
class CompilationReport:
    """Aggregate output of compiling all mappings in a scheme."""
    results: List[CompilationResult] = field(default_factory=list)
    combined_graph: Graph = field(default_factory=Graph)
    precedence_order: List[URIRef] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return all(r.is_valid for r in self.results)

    @property
    def errors(self) -> List[Tuple[URIRef, str]]:
        out = []
        for r in self.results:
            for e in r.errors:
                out.append((r.source_mapping, e))
        return out

    @property
    def warnings(self) -> List[Tuple[URIRef, str]]:
        out = []
        for r in self.results:
            for w in r.warnings:
                out.append((r.source_mapping, w))
        return out


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CompilationError(Exception):
    """Raised when the compiler encounters an unrecoverable error."""
    pass


class PrecedenceCycleError(CompilationError):
    """Raised when a cycle is detected in the precedence graph."""
    pass


class ValidationError(CompilationError):
    """Raised when a mapping fails structural validation."""
    pass


# ---------------------------------------------------------------------------
# Graph utilities
# ---------------------------------------------------------------------------

def _str_val(g: Graph, subj: Node, pred: URIRef) -> Optional[str]:
    """Extract a single string-valued literal."""
    obj = _single(g, subj, pred)
    if obj is not None and isinstance(obj, Literal):
        return str(obj)
    return None


def _decimal_val(g: Graph, subj: Node, pred: URIRef) -> Optional[float]:
    obj = _single(g, subj, pred)
    if obj is not None and isinstance(obj, Literal):
        return float(obj)
    return None


def _single(g: Graph, subj: Node, pred: URIRef) -> Optional[Node]:
    """Return the single object for (subj, pred, ?), or None."""
    objs = list(g.objects(subj, pred))
    if len(objs) == 0:
        return None
    if len(objs) > 1:
        logger.warning(
            "Multiple values for (%s, %s); using first", subj, pred
        )
    return objs[0]


def _all(g: Graph, subj: Node, pred: URIRef) -> List[Node]:
    return list(g.objects(subj, pred))


def _is_type(g: Graph, subj: Node, cls: URIRef) -> bool:
    """Check whether subj rdf:type cls (or subclass thereof in the graph)."""
    for t in g.objects(subj, RDF.type):
        if t == cls:
            return True
        # Check one level of subclass
        if (t, RDFS.subClassOf, cls) in g:
            return True
    return False


def _rdf_list_items(g: Graph, head: Node) -> List[Node]:
    """Extract items from an RDF list (rdf:first/rdf:rest chain)."""
    items = []
    current = head
    while current and current != RDF.nil:
        first = _single(g, current, RDF.first)
        if first is not None:
            items.append(first)
        current = _single(g, current, RDF.rest)
    return items


def _deterministic_iri(
    base_ns: str,
    template_iri: Optional[URIRef],
    bindings: FrozenSet[Tuple[str, str]],
    suffix: str = "",
) -> URIRef:
    """
    Generate a deterministic IRI from a template + bindings hash.
    Ensures idempotence (Theorem 4.3, Remark 4.3a).
    """
    seed = json.dumps(
        {
            "template": str(template_iri) if template_iri else "",
            "bindings": sorted(bindings),
            "suffix": suffix,
        },
        sort_keys=True,
    )
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return URIRef(f"{base_ns}gen_{h}")


# ---------------------------------------------------------------------------
# Precedence DAG builder
# ---------------------------------------------------------------------------

class PrecedenceDAG:
    """
    Builds and topologically sorts the precedence graph over DataMapping
    individuals. Implements the execution schedule (Definition 2.19) by
    computing topological order over the quotient DAG G/~ where ~ is
    the deferredMapping equivalence.
    """

    def __init__(self, g: Graph):
        self._graph = g
        self._edges: Dict[URIRef, Set[URIRef]] = defaultdict(set)
        self._nodes: Set[URIRef] = set()
        self._build()

    def _build(self):
        """
        Derive :precedes edges from structural relationships.
        Implements Axioms P1-P5, P10 via the subproperty semantics,
        and Rules P6-P9, P11 programmatically.
        """
        g = self._graph

        # Collect all DataMapping individuals (including subtypes)
        for dm_class in [
            MORK.DataMapping,
            MORK.ShapeMapping,
            MORK.RuleMapping,
            MORK.Datum,
            MORK.GenerativeMapping,
        ]:
            for s in g.subjects(RDF.type, dm_class):
                if isinstance(s, URIRef):
                    self._nodes.add(s)

        # Also collect anything that participates in mapping relations
        for pred in [
            MORK.compositeNarrowerMapping,
            MORK.compositeBroaderMapping,
            MORK.broaderApplicative,
            MORK.dependentMapping,
            MORK.templateMapping,
            MORK.deferredMapping,
        ]:
            for s, o in g.subject_objects(pred):
                if isinstance(s, URIRef):
                    self._nodes.add(s)
                if isinstance(o, URIRef):
                    self._nodes.add(o)

        # Axiom P1: compositeBroaderMapping^{-1} ⊑ precedes
        # If child :compositeBroaderMapping parent, then parent precedes child
        for child, parent in g.subject_objects(MORK.compositeBroaderMapping):
            self._add_edge(parent, child)

        # Also handle via compositeNarrowerMapping (inverse)
        for parent, child in g.subject_objects(MORK.compositeNarrowerMapping):
            self._add_edge(parent, child)

        # Axiom P2: broaderApplicative^{-1} ⊑ precedes
        for child, parent in g.subject_objects(MORK.broaderApplicative):
            self._add_edge(parent, child)

        # Axiom P3: dependentMapping^{-1} ⊑ precedes
        for child, dep in g.subject_objects(MORK.dependentMapping):
            self._add_edge(dep, child)

        # Axiom P10: templateMapping^{-1} ⊑ precedes
        for inst, tmpl in g.subject_objects(MORK.templateMapping):
            self._add_edge(tmpl, inst)

        # Rules P6/P7: deferredMapping with T-Box match direction
        for x, y in g.subject_objects(MORK.deferredMapping):
            if not isinstance(x, URIRef) or not isinstance(y, URIRef):
                continue

            x_is_datum = _is_type(g, x, MORK.Datum)
            y_has_tbox = (
                _single(g, y, MORK.exactTBoxMatch) is not None
                or _single(g, y, MORK.broadTBoxCategoryMatch) is not None
            )

            if x_is_datum and y_has_tbox:
                self._add_edge(y, x)

            # Symmetric: check the other direction
            y_is_datum = _is_type(g, y, MORK.Datum)
            x_has_tbox = (
                _single(g, x, MORK.exactTBoxMatch) is not None
                or _single(g, x, MORK.broadTBoxCategoryMatch) is not None
            )

            if y_is_datum and x_has_tbox:
                self._add_edge(x, y)

        # Rule P8: identityTemplateMapping → resolvesIdentityFor (⊑ precedes)
        for datum, id_mapping in g.subject_objects(
            MORK.identityTemplateMapping
        ):
            self._add_edge(id_mapping, datum)

        # Rule P9: referenceDataMapping within composite structure
        for ref_mapping, lookup in g.subject_objects(
            MORK.referenceDataMapping
        ):
            for parent_datum in g.objects(
                ref_mapping, MORK.compositeBroaderMapping
            ):
                if _is_type(g, parent_datum, MORK.Datum):
                    self._add_edge(lookup, parent_datum)

        # Rule P11: template child correlation
        for inst, tmpl in g.subject_objects(MORK.templateMapping):
            for inst_child in g.objects(inst, MORK.compositeNarrowerMapping):
                for tmpl_child in g.objects(
                    tmpl, MORK.compositeNarrowerTemplate
                ):
                    if (inst_child, MORK.templateBinding, tmpl_child) in g:
                        self._add_edge(tmpl_child, inst_child)

        # Materialised :precedes edges already in the graph
        for s, o in g.subject_objects(MORK.precedes):
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                self._add_edge(s, o)

    def _add_edge(self, before: URIRef, after: URIRef):
        if before == after:
            return
        self._edges[before].add(after)
        self._nodes.add(before)
        self._nodes.add(after)

    def topological_sort(self) -> List[URIRef]:
        """
        Kahn's algorithm. Raises PrecedenceCycleError if cycle detected.
        Returns nodes in precedence order (earlier first).
        """
        in_degree: Dict[URIRef, int] = {n: 0 for n in self._nodes}
        for src, dsts in self._edges.items():
            for dst in dsts:
                in_degree[dst] = in_degree.get(dst, 0) + 1

        # Stable sort: use IRI string ordering for determinism (Theorem 4.4)
        queue = sorted(
            [n for n, d in in_degree.items() if d == 0], key=str
        )

        result: List[URIRef] = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for succ in sorted(self._edges.get(node, set()), key=str):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)
            # Re-sort queue for determinism
            queue.sort(key=str)

        if len(result) != len(self._nodes):
            remaining = self._nodes - set(result)
            raise PrecedenceCycleError(
                f"Precedence cycle detected involving: "
                f"{[str(n) for n in remaining]}"
            )

        return result

    def successors(self, node: URIRef) -> Set[URIRef]:
        return self._edges.get(node, set())

    def predecessors(self, node: URIRef) -> Set[URIRef]:
        preds = set()
        for src, dsts in self._edges.items():
            if node in dsts:
                preds.add(src)
        return preds


# ---------------------------------------------------------------------------
# Parameter resolver
# ---------------------------------------------------------------------------

class ParameterResolver:
    """Resolves ParameterBinding individuals from the MORK graph."""

    def __init__(self, g: Graph):
        self._graph = g

    def resolve(self, mapping: URIRef) -> List[ParameterBinding]:
        """Resolve all parameter bindings for a GenerativeMapping."""
        bindings = []
        for pb_node in _all(self._graph, mapping, MORK.hasParameterBinding):
            binding = self._resolve_one(pb_node)
            if binding is not None:
                bindings.append(binding)
        return bindings

    def _resolve_one(self, pb_node: Node) -> Optional[ParameterBinding]:
        g = self._graph
        name = _str_val(g, pb_node, MORK.paramName)
        type_str = _str_val(g, pb_node, MORK.paramType)
        raw_value = _single(g, pb_node, MORK.paramValue)

        if name is None:
            logger.warning("ParameterBinding %s has no paramName", pb_node)
            return None

        try:
            param_type = ParamType(type_str) if type_str else ParamType.STRING
        except ValueError:
            logger.warning(
                "Unknown paramType '%s' on %s; defaulting to STRING",
                type_str,
                pb_node,
            )
            param_type = ParamType.STRING

        value = self._coerce_value(param_type, raw_value, pb_node)

        return ParameterBinding(
            name=name,
            param_type=param_type,
            value=value,
            raw_node=pb_node if isinstance(pb_node, URIRef) else None,
        )

    def _coerce_value(
        self, param_type: ParamType, raw: Optional[Node], pb_node: Node
    ) -> Any:
        """Coerce the raw RDF value to the appropriate Python type."""
        if raw is None:
            return None

        if param_type == ParamType.NUMERIC:
            if isinstance(raw, Literal):
                return float(raw.toPython())
            return raw

        if param_type == ParamType.CONCEPT:
            if isinstance(raw, URIRef):
                return raw
            return URIRef(str(raw))

        if param_type == ParamType.PATH:
            # Path can be a single property IRI or an RDF list of properties
            if isinstance(raw, URIRef):
                return [raw]
            # Try to resolve as an RDF list
            items = _rdf_list_items(self._graph, raw)
            if items:
                return [
                    i if isinstance(i, URIRef) else URIRef(str(i))
                    for i in items
                ]
            return [URIRef(str(raw))]

        if param_type == ParamType.STRING:
            return str(raw) if raw else ""

        if param_type == ParamType.DURATION:
            return str(raw) if raw else ""

        return raw


# ---------------------------------------------------------------------------
# Targeting spec resolver
# ---------------------------------------------------------------------------

class TargetingSpecResolver:
    """Resolves TargetingSpec individuals from the MORK graph."""

    _MODE_PROPERTIES = {
        SH.targetClass: TargetMode.TARGET_CLASS,
        SH.targetObjectsOf: TargetMode.TARGET_OBJECTS_OF,
        SH.targetSubjectsOf: TargetMode.TARGET_SUBJECTS_OF,
        SH.targetNode: TargetMode.TARGET_NODE,
    }

    def __init__(self, g: Graph):
        self._graph = g

    def resolve(self, mapping: URIRef) -> Optional[TargetingSpec]:
        ts_node = _single(self._graph, mapping, MORK.hasTargetingSpec)
        if ts_node is None:
            return None
        return self._resolve_one(ts_node)

    def resolve_all(self, mapping: URIRef) -> List[TargetingSpec]:
        specs = []
        for ts_node in _all(self._graph, mapping, MORK.hasTargetingSpec):
            spec = self._resolve_one(ts_node)
            if spec is not None:
                specs.append(spec)
        return specs

    def _resolve_one(self, ts_node: Node) -> Optional[TargetingSpec]:
        g = self._graph

        for prop, mode in self._MODE_PROPERTIES.items():
            target = _single(g, ts_node, prop)
            if target is not None:
                return TargetingSpec(
                    mode=mode,
                    target=target if isinstance(target, URIRef) else URIRef(str(target)),
                    jurisdiction=_single(g, ts_node, MORK.appliesInJurisdiction),
                    effective_from=_single(g, ts_node, MORK.effectiveFrom),
                    effective_until=_single(g, ts_node, MORK.effectiveUntil),
                    raw_node=ts_node if isinstance(ts_node, URIRef) else None,
                )

        logger.warning("TargetingSpec %s has no targeting mode", ts_node)
        return None


# ---------------------------------------------------------------------------
# Provenance resolver
# ---------------------------------------------------------------------------

class ProvenanceResolver:
    """Resolves provenance records from the MORK graph."""

    def __init__(self, g: Graph):
        self._graph = g

    def resolve_constraint(self, mapping: URIRef) -> Optional[ProvenanceRecord]:
        prov_node = _single(self._graph, mapping, MORK.hasConstraintProvenance)
        if prov_node is None:
            return None
        return self._resolve_one(prov_node)

    def resolve_rule(self, mapping: URIRef) -> Optional[ProvenanceRecord]:
        prov_node = _single(self._graph, mapping, MORK.hasRuleProvenance)
        if prov_node is None:
            return None
        return self._resolve_one(prov_node)

    def _resolve_one(self, prov_node: Node) -> ProvenanceRecord:
        g = self._graph
        status_str = _str_val(g, prov_node, MORK.reviewStatus)
        try:
            status = ReviewStatus(status_str) if status_str else None
        except ValueError:
            status = None

        confidence = _decimal_val(g, prov_node, MORK.llmConfidence)

        return ProvenanceRecord(
            creator=_str_val(g, prov_node, DCT.creator),
            created=_str_val(g, prov_node, DCT.created),
            input_hash=_str_val(g, prov_node, MORK.inputHash),
            llm_model_id=_str_val(g, prov_node, MORK.llmModelId),
            llm_confidence=confidence,
            review_status=status,
        )


# ---------------------------------------------------------------------------
# SHACL Shape Compiler
# ---------------------------------------------------------------------------

class SHACLCompiler:
    """
    Compiles a ShapeMapping into a SHACL shape graph.

    Given a ShapeMapping with:
      - TargetingSpec (sh:targetClass, etc.)
      - ParameterBindings (path, minInclusive, maxInclusive, inSet, etc.)
      - Optional ShapeTemplate reference
      - Severity
      - Provenance

    Produces:
      - An sh:NodeShape (or sh:PropertyShape) with the appropriate
        SHACL constraints, ready to be applied to a data graph.
    """

    # Maps parameter names to the SHACL compiler method that handles them
    _CONSTRAINT_PARAMS = {
        "minInclusive", "maxInclusive", "minExclusive", "maxExclusive",
        "minCount", "maxCount", "datatype", "class", "hasValue",
        "pattern", "flags", "minLength", "maxLength",
        "inSet", "equals", "disjoint", "lessThan", "lessThanOrEquals",
    }

    def __init__(self, source_graph: Graph, output_namespace: str):
        self._source = source_graph
        self._ns = output_namespace
        self._param_resolver = ParameterResolver(source_graph)
        self._target_resolver = TargetingSpecResolver(source_graph)
        self._prov_resolver = ProvenanceResolver(source_graph)

    def compile(self, mapping: URIRef) -> CompilationResult:
        """Compile a single ShapeMapping into a SHACL shape."""
        result = CompilationResult(
            source_mapping=mapping,
            artefact_graph=Graph(),
            artefact_root=None,
            artefact_type="SHACL",
        )
        g = result.artefact_graph
        g.bind("sh", SH)
        g.bind("mork", MORK)
        g.bind("xsd", XSD)
        g.bind("owl", OWL)

        # Resolve inputs
        bindings = self._param_resolver.resolve(mapping)
        targeting = self._target_resolver.resolve(mapping)
        provenance = self._prov_resolver.resolve_constraint(mapping)
        result.provenance = provenance

        if targeting is None:
            result.errors.append("ShapeMapping has no TargetingSpec")
            return result

        if not bindings:
            result.errors.append("ShapeMapping has no ParameterBindings")
            return result

        # Check provenance status
        if provenance and provenance.review_status == ReviewStatus.DEPRECATED:
            result.warnings.append("ShapeMapping is DEPRECATED; skipping")
            return result

        # Build deterministic IRI for the shape
        binding_sig = frozenset(
            (b.name, str(b.value)) for b in bindings
        )
        template_iri = _single(
            self._source, mapping, MORK.hasShapeTemplate
        )
        shape_iri = _deterministic_iri(
            self._ns, template_iri, binding_sig, suffix="shape"
        )
        result.artefact_root = shape_iri

        # Determine if this should be a NodeShape or PropertyShape
        # Default to NodeShape; use PropertyShape only if the mapping
        # has a single path binding and no other structural constraints
        path_bindings = [b for b in bindings if b.param_type == ParamType.PATH]
        non_path_bindings = [b for b in bindings if b.param_type != ParamType.PATH]

        g.add((shape_iri, RDF.type, SH.NodeShape))

        # Apply targeting
        self._apply_targeting(g, shape_iri, targeting)

        # Apply severity
        severity = self._resolve_severity(mapping)
        if severity:
            g.add((shape_iri, SH.severity, severity.to_sh()))

        # Check for existing generated shape definition to preserve
        existing = _single(
            self._source, mapping, MORK.generatesShapeDefinition
        )
        if existing is not None:
            # If the mapping already carries a fully-specified generated
            # shape, copy it to the output graph
            self._copy_existing_shape(g, shape_iri, existing, result)
            return result

        # Build constraints from parameter bindings
        self._build_constraints(g, shape_iri, bindings, result)

        # Add message from template or mapping
        self._apply_message(g, shape_iri, mapping, bindings)

        # Add provenance back-link
        g.add((shape_iri, MORK.generatedBy, mapping))

        return result

    def _apply_targeting(
        self, g: Graph, shape: URIRef, spec: TargetingSpec
    ):
        """Apply the targeting specification to the shape."""
        prop_map = {
            TargetMode.TARGET_CLASS: SH.targetClass,
            TargetMode.TARGET_OBJECTS_OF: SH.targetObjectsOf,
            TargetMode.TARGET_SUBJECTS_OF: SH.targetSubjectsOf,
            TargetMode.TARGET_NODE: SH.targetNode,
        }
        g.add((shape, prop_map[spec.mode], spec.target))

    def _resolve_severity(self, mapping: URIRef) -> Optional[Severity]:
        sev_node = _single(self._source, mapping, MORK.hasSeverity)
        if sev_node is None:
            # Check template defaults
            tmpl = _single(self._source, mapping, MORK.hasShapeTemplate)
            if tmpl:
                sev_node = _single(self._source, tmpl, MORK.hasSeverity)
        if sev_node is None:
            return Severity.VIOLATION  # default

        sev_str = str(sev_node).split("#")[-1] if isinstance(sev_node, URIRef) else str(sev_node)
        try:
            return Severity(sev_str)
        except ValueError:
            return Severity.VIOLATION

    def _build_constraints(
        self,
        g: Graph,
        shape: URIRef,
        bindings: List[ParameterBinding],
        result: CompilationResult,
    ):
        """
        Build SHACL property constraints from parameter bindings.
        
        The compiler recognises the following parameter name conventions:
        
        Structural:
            path           - Property path (single IRI or list)
            
        Value constraints:
            minInclusive   - sh:minInclusive (Numeric)
            maxInclusive   - sh:maxInclusive (Numeric)
            minExclusive   - sh:minExclusive (Numeric)
            maxExclusive   - sh:maxExclusive (Numeric)
            
        Cardinality:
            minCount       - sh:minCount (Numeric, integer)
            maxCount       - sh:maxCount (Numeric, integer)
            
        Type constraints:
            datatype       - sh:datatype (Concept → xsd:* IRI)
            class          - sh:class (Concept → owl:Class IRI)
            
        Membership:
            inSet          - sh:in (list of Concept IRIs)
            hasValue       - sh:hasValue (single Concept IRI)
            
        String:
            pattern        - sh:pattern (String)
            flags          - sh:flags (String)
            
        SPARQL:
            sparqlSelect   - sh:sparql/sh:select (String)
            
        Message:
            message        - sh:message (String)
        """
        bindings_by_name = {b.name: b for b in bindings}

        # Resolve path
        path_binding = bindings_by_name.get("path")
        sparql_binding = bindings_by_name.get("sparqlSelect")

        if sparql_binding and sparql_binding.value:
            # SPARQL constraint mode
            self._build_sparql_constraint(g, shape, sparql_binding, result)
        elif path_binding:
            # Property constraint mode
            prop_shape = BNode()
            g.add((shape, SH.property, prop_shape))
            self._apply_path(g, prop_shape, path_binding)
            self._apply_value_constraints(g, prop_shape, bindings_by_name)
        else:
            # No path and no SPARQL — try to build a node-level constraint
            # from value/type bindings
            self._apply_node_level_constraints(g, shape, bindings_by_name, result)

    def _apply_path(
        self, g: Graph, prop_shape: BNode, path_binding: ParameterBinding
    ):
        """Apply sh:path to a property shape."""
        path_items = path_binding.value
        if isinstance(path_items, list) and len(path_items) == 1:
            # Single property — direct reference
            g.add((prop_shape, SH.path, path_items[0]))
        elif isinstance(path_items, list) and len(path_items) > 1:
            # Property path sequence — RDF list
            path_list = BNode()
            collection = RDFCollection(g, path_list)
            for item in path_items:
                collection.append(item)
            g.add((prop_shape, SH.path, path_list))
        elif isinstance(path_items, URIRef):
            g.add((prop_shape, SH.path, path_items))

    def _apply_value_constraints(
        self,
        g: Graph,
        prop_shape: BNode,
        bindings: Dict[str, ParameterBinding],
    ):
        """Apply value constraints to a property shape."""

        # Numeric bounds
        for name, sh_prop in [
            ("minInclusive", SH.minInclusive),
            ("maxInclusive", SH.maxInclusive),
            ("minExclusive", SH.minExclusive),
            ("maxExclusive", SH.maxExclusive),
        ]:
            b = bindings.get(name)
            if b and b.value is not None:
                g.add((
                    prop_shape,
                    sh_prop,
                    Literal(b.value, datatype=XSD.decimal),
                ))

        # Cardinality
        for name, sh_prop in [
            ("minCount", SH.minCount),
            ("maxCount", SH.maxCount),
        ]:
            b = bindings.get(name)
            if b and b.value is not None:
                g.add((
                    prop_shape,
                    sh_prop,
                    Literal(int(b.value), datatype=XSD.integer),
                ))

        # Type constraints
        b = bindings.get("datatype")
        if b and b.value:
            g.add((prop_shape, SH.datatype, b.value))

        b = bindings.get("class")
        if b and b.value:
            g.add((prop_shape, SH["class"], b.value))

        # Membership
        b = bindings.get("hasValue")
        if b and b.value:
            g.add((prop_shape, SH.hasValue, b.value))

        b = bindings.get("inSet")
        if b and b.value:
            # inSet can be a single concept or a list
            values = b.value if isinstance(b.value, list) else [b.value]
            in_list = BNode()
            collection = RDFCollection(g, in_list)
            for v in values:
                collection.append(v)
            g.add((prop_shape, SH["in"], in_list))

        # String pattern
        b = bindings.get("pattern")
        if b and b.value:
            g.add((prop_shape, SH.pattern, Literal(b.value)))
            flags = bindings.get("flags")
            if flags and flags.value:
                g.add((prop_shape, SH.flags, Literal(flags.value)))

        # Message
        b = bindings.get("message")
        if b and b.value:
            g.add((prop_shape, SH.message, Literal(b.value)))

    def _build_sparql_constraint(
        self,
        g: Graph,
        shape: URIRef,
        sparql_binding: ParameterBinding,
        result: CompilationResult,
    ):
        """Build a SPARQL-based constraint (sh:sparql)."""
        sparql_node = BNode()
        g.add((shape, SH.sparql, sparql_node))
        g.add((sparql_node, SH.select, Literal(str(sparql_binding.value))))

        # If there is a message binding, apply it to the SPARQL constraint
        # (resolved from the mapping's other bindings in the parent call)

    def _apply_node_level_constraints(
        self,
        g: Graph,
        shape: URIRef,
        bindings: Dict[str, ParameterBinding],
        result: CompilationResult,
    ):
        """Apply constraints directly on the node shape (no path)."""
        b = bindings.get("class")
        if b and b.value:
            # sh:class on the node itself
            prop_shape = BNode()
            g.add((shape, SH.property, prop_shape))
            g.add((prop_shape, SH["class"], b.value))

        # Check if there is anything to compile
        if not any(
            bindings.get(k) for k in self._CONSTRAINT_PARAMS
        ):
            result.warnings.append(
                "No recognised constraint parameters; "
                "shape may be empty"
            )

    def _apply_message(
        self,
        g: Graph,
        shape: URIRef,
        mapping: URIRef,
        bindings: List[ParameterBinding],
    ):
        """Apply a human-readable message to the shape."""
        # Check for explicit message binding
        for b in bindings:
            if b.name == "message" and b.value:
                g.add((shape, SH.message, Literal(str(b.value))))
                return

        # Fall back to template description
        tmpl = _single(self._source, mapping, MORK.hasShapeTemplate)
        if tmpl:
            desc = _str_val(self._source, tmpl, DCT.description)
            if desc:
                g.add((shape, SH.message, Literal(desc)))
                return

        # Fall back to mapping note
        note = _str_val(self._source, mapping, MORK.mappingNote)
        if note:
            g.add((shape, SH.message, Literal(note)))

    def _copy_existing_shape(
        self,
        g: Graph,
        shape_iri: URIRef,
        existing: Node,
        result: CompilationResult,
    ):
        """
        If the ShapeMapping already carries a fully specified
        generatesShapeDefinition, copy that sub-graph to the output.
        This supports the pattern where the LLM or human has authored
        the complete shape inline.
        """
        src = self._source

        # BFS/DFS copy of the existing shape sub-graph
        visited: Set[Node] = set()
        queue = [existing]

        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)

            for p, o in src.predicate_objects(node):
                # Rewrite the root node IRI to the deterministic shape IRI
                subj = shape_iri if node == existing else node
                g.add((subj, p, o))

                if isinstance(o, BNode) and o not in visited:
                    queue.append(o)

        result.artefact_root = shape_iri
        g.add((shape_iri, MORK.generatedBy, result.source_mapping))


# ---------------------------------------------------------------------------
# SWRL Rule Compiler
# ---------------------------------------------------------------------------

class SWRLCompiler:
    """
    Compiles a RuleMapping into a SWRL rule graph (swrl:Imp).

    Given a RuleMapping with:
      - TargetingSpec (scoping)
      - ParameterBindings (variables, thresholds, class/property refs)
      - Optional RuleTemplate reference
      - Provenance

    Produces:
      - A swrl:Imp individual with swrl:body and swrl:head atom lists,
        ready to be loaded into a rule engine.
    """

    def __init__(self, source_graph: Graph, output_namespace: str):
        self._source = source_graph
        self._ns = output_namespace
        self._param_resolver = ParameterResolver(source_graph)
        self._target_resolver = TargetingSpecResolver(source_graph)
        self._prov_resolver = ProvenanceResolver(source_graph)

    def compile(self, mapping: URIRef) -> CompilationResult:
        """Compile a single RuleMapping into a SWRL rule."""
        result = CompilationResult(
            source_mapping=mapping,
            artefact_graph=Graph(),
            artefact_root=None,
            artefact_type="SWRL",
        )
        g = result.artefact_graph
        g.bind("swrl", SWRL)
        g.bind("swrlb", SWRLB)
        g.bind("mork", MORK)
        g.bind("xsd", XSD)
        g.bind("owl", OWL)

        provenance = self._prov_resolver.resolve_rule(mapping)
        result.provenance = provenance

        if provenance and provenance.review_status == ReviewStatus.DEPRECATED:
            result.warnings.append("RuleMapping is DEPRECATED; skipping")
            return result

        # Check for existing generated rule definition
        existing = _single(
            self._source, mapping, MORK.generatesRuleDefinition
        )

        if existing is not None:
            # Copy the existing swrl:Imp sub-graph
            return self._copy_existing_rule(g, mapping, existing, result)

        # Resolve bindings and build from template
        bindings = self._param_resolver.resolve(mapping)

        binding_sig = frozenset(
            (b.name, str(b.value)) for b in bindings
        )
        template_iri = _single(
            self._source, mapping, MORK.hasRuleTemplate
        )
        rule_iri = _deterministic_iri(
            self._ns, template_iri, binding_sig, suffix="rule"
        )
        result.artefact_root = rule_iri

        if template_iri is not None:
            return self._compile_from_template(
                g, rule_iri, mapping, template_iri, bindings, result
            )

        # No template and no existing definition — cannot compile
        result.errors.append(
            "RuleMapping has neither generatesRuleDefinition nor "
            "hasRuleTemplate; cannot compile"
        )
        return result

    def _compile_from_template(
        self,
        g: Graph,
        rule_iri: URIRef,
        mapping: URIRef,
        template_iri: URIRef,
        bindings: List[ParameterBinding],
        result: CompilationResult,
    ) -> CompilationResult:
        """
        Compile a rule from a RuleTemplate + parameter bindings.

        The RuleTemplate is expected to carry a generatesRuleDefinition
        with swrl:body and swrl:head containing atoms with placeholder
        variables. The compiler substitutes concrete values from the
        bindings.
        """
        src = self._source
        bindings_map = {b.name: b for b in bindings}

        # Check if the template has an inline rule definition
        tmpl_rule = _single(src, template_iri, MORK.generatesRuleDefinition)
        if tmpl_rule is not None:
            # Copy template rule and substitute parameters
            self._copy_and_substitute(
                g, rule_iri, tmpl_rule, bindings_map, result
            )
        else:
            # Build rule structure from template metadata
            g.add((rule_iri, RDF.type, SWRL.Imp))

            # Build body and head from template annotations
            self._build_atoms_from_bindings(
                g, rule_iri, bindings_map, result
            )

        g.add((rule_iri, MORK.generatedBy, mapping))
        return result

    def _build_atoms_from_bindings(
        self,
        g: Graph,
        rule_iri: URIRef,
        bindings: Dict[str, ParameterBinding],
        result: CompilationResult,
    ):
        """
        Build SWRL atoms from well-known parameter binding names.

        Recognised binding names:
            subjectClass      - ClassAtom on the subject variable
            predicateProperty - PropertyAtom's property predicate
            objectClass       - ClassAtom on the object variable  
            builtinOperator   - BuiltinAtom's built-in IRI
            thresholdValue    - Literal value for built-in comparison
            consequentProperty - Property for the head atom
            consequentValue    - Value for the head property atom
        """
        body_atoms = []
        head_atoms = []

        # Subject variable
        var_x = URIRef(f"{self._ns}var_x")

        # Body: ClassAtom for subject
        subj_class = bindings.get("subjectClass")
        if subj_class and subj_class.value:
            atom = BNode()
            g.add((atom, RDF.type, SWRL.ClassAtom))
            g.add((atom, SWRL.classPredicate, subj_class.value))
            g.add((atom, SWRL.argument1, var_x))
            body_atoms.append(atom)

        # Body: PropertyAtom
        pred_prop = bindings.get("predicateProperty")
        if pred_prop and pred_prop.value:
            var_y = URIRef(f"{self._ns}var_y")
            atom = BNode()
            g.add((atom, RDF.type, SWRL.IndividualPropertyAtom))
            g.add((atom, SWRL.propertyPredicate, pred_prop.value))
            g.add((atom, SWRL.argument1, var_x))
            g.add((atom, SWRL.argument2, var_y))
            body_atoms.append(atom)

        # Body: BuiltinAtom for threshold comparison
        builtin_op = bindings.get("builtinOperator")
        threshold = bindings.get("thresholdValue")
        if builtin_op and threshold and threshold.value is not None:
            var_val = URIRef(f"{self._ns}var_val")
            atom = BNode()
            g.add((atom, RDF.type, SWRL.BuiltinAtom))
            g.add((atom, SWRL.builtin, builtin_op.value))

            # Build arguments list
            args_head = BNode()
            args_collection = RDFCollection(g, args_head)
            args_collection.append(var_val)
            args_collection.append(
                Literal(threshold.value, datatype=XSD.decimal)
                if isinstance(threshold.value, (int, float))
                else Literal(str(threshold.value))
            )
            g.add((atom, SWRL.arguments, args_head))
            body_atoms.append(atom)

        # Head: consequent PropertyAtom
        conseq_prop = bindings.get("consequentProperty")
        conseq_val = bindings.get("consequentValue")
        if conseq_prop and conseq_prop.value:
            atom = BNode()
            g.add((atom, RDF.type, SWRL.IndividualPropertyAtom))
            g.add((atom, SWRL.propertyPredicate, conseq_prop.value))
            g.add((atom, SWRL.argument1, var_x))
            if conseq_val and conseq_val.value is not None:
                if isinstance(conseq_val.value, URIRef):
                    g.add((atom, SWRL.argument2, conseq_val.value))
                else:
                    g.add((
                        atom,
                        SWRL.argument2,
                        Literal(conseq_val.value),
                    ))
            head_atoms.append(atom)

        # Assemble body and head as RDF lists
        if body_atoms:
            body_list = BNode()
            coll = RDFCollection(g, body_list)
            for a in body_atoms:
                coll.append(a)
            g.add((rule_iri, SWRL.body, body_list))
        else:
            result.warnings.append("Rule has no body atoms")

        if head_atoms:
            head_list = BNode()
            coll = RDFCollection(g, head_list)
            for a in head_atoms:
                coll.append(a)
            g.add((rule_iri, SWRL.head, head_list))
        else:
            result.warnings.append("Rule has no head atoms")

        g.add((rule_iri, RDF.type, SWRL.Imp))

    def _copy_and_substitute(
        self,
        g: Graph,
        rule_iri: URIRef,
        template_rule: Node,
        bindings: Dict[str, ParameterBinding],
        result: CompilationResult,
    ):
        """
        Copy a template rule definition and substitute parameter
        placeholders with concrete values.
        """
        src = self._source
        visited: Set[Node] = set()
        node_map: Dict[Node, Node] = {template_rule: rule_iri}
        queue = [template_rule]

        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)

            mapped_node = node_map.get(node, node)
            if isinstance(node, BNode) and node not in node_map:
                node_map[node] = BNode()
                mapped_node = node_map[node]

            for p, o in src.predicate_objects(node):
                mapped_o = o
                if isinstance(o, BNode):
                    if o not in node_map:
                        node_map[o] = BNode()
                    mapped_o = node_map[o]
                    if o not in visited:
                        queue.append(o)

                # Substitute parameter values
                mapped_o = self._substitute(mapped_o, bindings)

                g.add((mapped_node, p, mapped_o))

    def _substitute(
        self, node: Node, bindings: Dict[str, ParameterBinding]
    ) -> Node:
        """
        If a node is a placeholder (e.g., a Literal whose value
        matches a binding name pattern), substitute the concrete value.
        """
        if isinstance(node, Literal):
            val = str(node)
            # Check for ${paramName} pattern
            for name, binding in bindings.items():
                placeholder = f"${{{name}}}"
                if placeholder in val:
                    replacement = str(binding.value)
                    val = val.replace(placeholder, replacement)
            if val != str(node):
                return Literal(val, datatype=node.datatype, lang=node.language)
        return node

    def _copy_existing_rule(
        self,
        g: Graph,
        mapping: URIRef,
        existing: Node,
        result: CompilationResult,
    ) -> CompilationResult:
        """Copy an existing swrl:Imp sub-graph to the output."""
        bindings = self._param_resolver.resolve(mapping)
        binding_sig = frozenset(
            (b.name, str(b.value)) for b in bindings
        )
        template_iri = _single(
            self._source, mapping, MORK.hasRuleTemplate
        )
        rule_iri = _deterministic_iri(
            self._ns, template_iri, binding_sig, suffix="rule"
        )
        result.artefact_root = rule_iri

        src = self._source
        visited: Set[Node] = set()
        queue = [existing]

        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)

            for p, o in src.predicate_objects(node):
                subj = rule_iri if node == existing else node
                g.add((subj, p, o))
                if isinstance(o, BNode) and o not in visited:
                    queue.append(o)

        g.add((rule_iri, MORK.generatedBy, mapping))
        return result


# ---------------------------------------------------------------------------
# SPARQL Template Compiler
# ---------------------------------------------------------------------------

class SPARQLCompiler:
    """
    Compiles a QueryTemplate into a parameterised SPARQL string
    with bindings resolved from the MORK graph.
    """

    def __init__(self, source_graph: Graph, output_namespace: str):
        self._source = source_graph
        self._ns = output_namespace

    def compile(self, template: URIRef) -> CompilationResult:
        result = CompilationResult(
            source_mapping=template,
            artefact_graph=Graph(),
            artefact_root=template,
            artefact_type="SPARQL",
        )
        g = result.artefact_graph
        g.bind("mork", MORK)

        query_text = _str_val(self._source, template, MORK.queryText)
        if not query_text:
            result.errors.append("QueryTemplate has no queryText")
            return result

        query_lang = _str_val(
            self._source, template, MORK.queryLanguage
        ) or "SPARQL"

        # Resolve parameter bindings via paramBinding
        resolved_text = query_text
        for pb_node in _all(self._source, template, MORK.paramBinding):
            name = _str_val(self._source, pb_node, MORK.paramName)
            value = _single(self._source, pb_node, MORK.paramValue)
            if name and value:
                placeholder = f"${{{name}}}"
                resolved_text = resolved_text.replace(
                    placeholder, str(value)
                )

        # Store the resolved query as a literal on the output graph
        g.add((
            template,
            MORK.compiledQueryText,
            Literal(resolved_text, datatype=XSD.string),
        ))
        g.add((
            template,
            MORK.queryLanguage,
            Literal(query_lang, datatype=XSD.string),
        ))
        g.add((template, MORK.generatedBy, template))

        return result


# ---------------------------------------------------------------------------
# Main Compiler orchestrator
# ---------------------------------------------------------------------------

class MorkCompiler:
    """
    The top-level MORK Compiler-Agent.

    Orchestrates the compilation of all GenerativeMapping and QueryTemplate
    individuals in a MORK graph into executable artefacts.

    Usage:
        compiler = MorkCompiler(
            source_graph=mork_graph,
            output_namespace="http://example.org/generated/",
        )
        report = compiler.compile()

        if report.is_valid:
            # report.combined_graph contains all generated artefacts
            report.combined_graph.serialize("output.ttl", format="turtle")
        else:
            for mapping_iri, error in report.errors:
                print(f"ERROR in {mapping_iri}: {error}")
    """

    def __init__(
        self,
        source_graph: Graph,
        output_namespace: str = "http://www.nebularis.org/generated/",
        validate_output: bool = True,
    ):
        self._source = source_graph
        self._ns = output_namespace
        self._validate = validate_output
        self._shacl_compiler = SHACLCompiler(source_graph, output_namespace)
        self._swrl_compiler = SWRLCompiler(source_graph, output_namespace)
        self._sparql_compiler = SPARQLCompiler(source_graph, output_namespace)

    def compile(
        self,
        constraint_scheme: Optional[URIRef] = None,
        rule_scheme: Optional[URIRef] = None,
    ) -> CompilationReport:
        """
        Compile all GenerativeMapping and QueryTemplate individuals.

        If constraint_scheme or rule_scheme is provided, only mappings
        belonging to those schemes are compiled. Otherwise, all
        ShapeMapping, RuleMapping, and QueryTemplate individuals in
        the graph are compiled.

        Returns a CompilationReport containing:
          - Individual results for each compiled mapping
          - A combined graph of all generated artefacts
          - The precedence order used for compilation
          - Aggregate errors and warnings
        """
        report = CompilationReport()
        report.combined_graph.bind("sh", SH)
        report.combined_graph.bind("swrl", SWRL)
        report.combined_graph.bind("swrlb", SWRLB)
        report.combined_graph.bind("mork", MORK)
        report.combined_graph.bind("xsd", XSD)
        report.combined_graph.bind("owl", OWL)

        # Phase 1: Build precedence DAG and topological sort
        logger.info("Phase 1: Building precedence DAG")
        try:
            dag = PrecedenceDAG(self._source)
            precedence_order = dag.topological_sort()
            report.precedence_order = precedence_order
        except PrecedenceCycleError as e:
            logger.error("Precedence cycle detected: %s", e)
            result = CompilationResult(
                source_mapping=URIRef("urn:mork:compiler:precedence"),
                artefact_graph=Graph(),
                artefact_root=None,
                artefact_type="ERROR",
            )
            result.errors.append(str(e))
            report.results.append(result)
            return report

        # Phase 2: Identify compilable mappings
        logger.info("Phase 2: Identifying compilable mappings")
        shape_mappings = self._collect_mappings(
            MORK.ShapeMapping, constraint_scheme, MORK.mappingScheme
        )
        rule_mappings = self._collect_mappings(
            MORK.RuleMapping, rule_scheme, MORK.mappingScheme
        )
        query_templates = set(
            s for s in self._source.subjects(RDF.type, MORK.QueryTemplate)
            if isinstance(s, URIRef)
        )

        # Also detect ShapeMappings/RuleMappings by equivalence axiom
        # (any DataMapping with generatesShapeDefinition)
        for s in self._source.subjects(MORK.generatesShapeDefinition, None):
            if isinstance(s, URIRef):
                shape_mappings.add(s)
        for s in self._source.subjects(MORK.generatesRuleDefinition, None):
            if isinstance(s, URIRef):
                rule_mappings.add(s)

        all_compilable = shape_mappings | rule_mappings | query_templates

        logger.info(
            "Found %d ShapeMappings, %d RuleMappings, %d QueryTemplates",
            len(shape_mappings),
            len(rule_mappings),
            len(query_templates),
        )

        # Phase 3: Compile in precedence order
        logger.info("Phase 3: Compiling in precedence order")
        compiled: Set[URIRef] = set()

        for node in precedence_order:
            if node not in all_compilable:
                continue
            result = self._compile_one(
                node, shape_mappings, rule_mappings, query_templates
            )
            report.results.append(result)
            compiled.add(node)

            # Merge into combined graph
            if result.is_valid:
                for triple in result.artefact_graph:
                    report.combined_graph.add(triple)

        # Compile any mappings not in the precedence DAG
        # (e.g., standalone QueryTemplates with no dependencies)
        for node in sorted(all_compilable - compiled, key=str):
            result = self._compile_one(
                node, shape_mappings, rule_mappings, query_templates
            )
            report.results.append(result)

            if result.is_valid:
                for triple in result.artefact_graph:
                    report.combined_graph.add(triple)

        # Phase 4: Validate generated artefacts
        if self._validate and report.is_valid:
            logger.info("Phase 4: Validating generated artefacts")
            self._validate_output(report)

        logger.info(
            "Compilation complete: %d artefacts, %d errors, %d warnings",
            len(report.results),
            len(report.errors),
            len(report.warnings),
        )

        return report

    def _collect_mappings(
        self,
        mapping_class: URIRef,
        scheme_filter: Optional[URIRef],
        scheme_property: URIRef,
    ) -> Set[URIRef]:
        """Collect all mappings of a given type, optionally filtered by scheme."""
        mappings = set()
        for s in self._source.subjects(RDF.type, mapping_class):
            if not isinstance(s, URIRef):
                continue
            if scheme_filter is not None:
                scheme = _single(self._source, s, scheme_property)
                if scheme != scheme_filter:
                    continue
            mappings.add(s)
        return mappings

    def _compile_one(
        self,
        node: URIRef,
        shape_mappings: Set[URIRef],
        rule_mappings: Set[URIRef],
        query_templates: Set[URIRef],
    ) -> CompilationResult:
        """Compile a single mapping node."""
        if node in shape_mappings:
            logger.debug("Compiling ShapeMapping: %s", node)
            return self._shacl_compiler.compile(node)
        elif node in rule_mappings:
            logger.debug("Compiling RuleMapping: %s", node)
            return self._swrl_compiler.compile(node)
        elif node in query_templates:
            logger.debug("Compiling QueryTemplate: %s", node)
            return self._sparql_compiler.compile(node)
        else:
            result = CompilationResult(
                source_mapping=node,
                artefact_graph=Graph(),
                artefact_root=None,
                artefact_type="UNKNOWN",
            )
            result.errors.append(
                f"Node {node} is not a recognised compilable type"
            )
            return result

    def _validate_output(self, report: CompilationReport):
        """
        Run Meta-SHACL validation on the generated artefact graph.
        Implements Shapes G1-G4 and R1-R6 programmatically.
        """
        g = report.combined_graph

        # G1 / R1: Check that all target classes exist
        for shape in g.subjects(RDF.type, SH.NodeShape):
            for tc in g.objects(shape, SH.targetClass):
                if not self._entity_exists(tc, OWL.Class):
                    self._add_validation_warning(
                        report, shape,
                        f"Generated shape targets non-existent class {tc}"
                    )

        # G2: Check that property path elements exist
        for shape in g.subjects(RDF.type, SH.NodeShape):
            for prop_shape in g.objects(shape, SH.property):
                path = _single(g, prop_shape, SH.path)
                if path is not None:
                    self._validate_path(g, report, shape, path)

        # G3: Numeric constraint consistency
        for shape in g.subjects(RDF.type, SH.NodeShape):
            for prop_shape in g.objects(shape, SH.property):
                min_val = _single(g, prop_shape, SH.minInclusive)
                max_val = _single(g, prop_shape, SH.maxInclusive)
                if min_val is not None and max_val is not None:
                    try:
                        if float(min_val) > float(max_val):
                            self._add_validation_error(
                                report, shape,
                                f"minInclusive ({min_val}) > "
                                f"maxInclusive ({max_val})"
                            )
                    except (ValueError, TypeError):
                        pass

        # R1: Check SWRL class predicates
        for rule in g.subjects(RDF.type, SWRL.Imp):
            self._validate_swrl_references(g, report, rule)

        # R6: Check non-empty body and head
        for rule in g.subjects(RDF.type, SWRL.Imp):
            body = _single(g, rule, SWRL.body)
            head = _single(g, rule, SWRL.head)
            if body is None or body == RDF.nil:
                self._add_validation_warning(
                    report, rule, "SWRL rule has empty body"
                )
            if head is None or head == RDF.nil:
                self._add_validation_warning(
                    report, rule, "SWRL rule has empty head"
                )

    def _entity_exists(self, iri: Node, expected_type: URIRef) -> bool:
        """Check if an entity exists in the source graph."""
        if not isinstance(iri, URIRef):
            return True  # BNodes, literals — not checkable
        # Check in source graph
        if (iri, RDF.type, expected_type) in self._source:
            return True
        # Check RDFS subclass chain
        for t in self._source.objects(iri, RDF.type):
            if (t, RDFS.subClassOf, expected_type) in self._source:
                return True
        # Permissive: if the IRI is from an external namespace, assume it exists
        mork_ns = str(MORK)
        if not str(iri).startswith(mork_ns):
            return True
        return False

    def _validate_path(
        self,
        g: Graph,
        report: CompilationReport,
        shape: Node,
        path: Node,
    ):
        """Validate that path elements reference existing properties."""
        if isinstance(path, URIRef):
            if not self._property_exists(path):
                self._add_validation_warning(
                    report, shape,
                    f"Path references non-existent property {path}"
                )
        elif isinstance(path, BNode):
            # RDF list — check each element
            items = _rdf_list_items(g, path)
            for item in items:
                if isinstance(item, URIRef) and not self._property_exists(item):
                    self._add_validation_warning(
                        report, shape,
                        f"Path references non-existent property {item}"
                    )

    def _property_exists(self, iri: URIRef) -> bool:
        """Check if a property exists in the source graph."""
        if (iri, RDF.type, OWL.ObjectProperty) in self._source:
            return True
        if (iri, RDF.type, OWL.DatatypeProperty) in self._source:
            return True
        # Permissive for external namespaces
        mork_ns = str(MORK)
        if not str(iri).startswith(mork_ns):
            return True
        return False

    def _validate_swrl_references(
        self,
        g: Graph,
        report: CompilationReport,
        rule: Node,
    ):
        """Validate SWRL atom references (R1, R2, R3)."""
        # Collect all atoms from body and head
        atoms = []
        for list_prop in [SWRL.body, SWRL.head]:
            atom_list = _single(g, rule, list_prop)
            if atom_list:
                atoms.extend(_rdf_list_items(g, atom_list))

        for atom in atoms:
            # R1: ClassAtom class predicates
            if _is_type(g, atom, SWRL.ClassAtom):
                cls = _single(g, atom, SWRL.classPredicate)
                if cls and isinstance(cls, URIRef):
                    if not self._entity_exists(cls, OWL.Class):
                        self._add_validation_warning(
                            report, rule,
                            f"SWRL ClassAtom references non-existent "
                            f"class {cls}"
                        )

            # R2: PropertyAtom property predicates
            for atom_type in [
                SWRL.IndividualPropertyAtom,
                SWRL.DatavaluedPropertyAtom,
            ]:
                if _is_type(g, atom, atom_type):
                    prop = _single(g, atom, SWRL.propertyPredicate)
                    if prop and isinstance(prop, URIRef):
                        if not self._property_exists(prop):
                            self._add_validation_warning(
                                report, rule,
                                f"SWRL PropertyAtom references "
                                f"non-existent property {prop}"
                            )

            # R3: BuiltinAtom built-in references
            if _is_type(g, atom, SWRL.BuiltinAtom):
                bi = _single(g, atom, SWRL.builtin)
                if bi and isinstance(bi, URIRef):
                    if not str(bi).startswith(str(SWRLB)):
                        self._add_validation_warning(
                            report, rule,
                            f"SWRL BuiltinAtom references "
                            f"unrecognised built-in {bi}"
                        )

    @staticmethod
    def _add_validation_error(
        report: CompilationReport, node: Node, message: str
    ):
        for r in report.results:
            if r.artefact_root == node:
                r.errors.append(f"[VALIDATION] {message}")
                return
        logger.error("Validation error for unknown node %s: %s", node, message)

    @staticmethod
    def _add_validation_warning(
        report: CompilationReport, node: Node, message: str
    ):
        for r in report.results:
            if r.artefact_root == node:
                r.warnings.append(f"[VALIDATION] {message}")
                return
        logger.warning(
            "Validation warning for unknown node %s: %s", node, message
        )


# ---------------------------------------------------------------------------
# Convenience: Compile and serialize
# ---------------------------------------------------------------------------

def compile_mork_graph(
    source: Union[str, Graph],
    output_path: str = None,
    output_format: str = "turtle",
    output_namespace: str = "http://www.nebularis.org/generated/",
    constraint_scheme: Optional[URIRef] = None,
    rule_scheme: Optional[URIRef] = None,
) -> CompilationReport:
    """
    Convenience function to compile a MORK graph to executable artefacts.

    Args:
        source: Path to a Turtle file, or an rdflib.Graph.
        output_path: Path to write the combined output graph. 
                     If None, output is not written to file.
        output_format: RDF serialization format (turtle, xml, json-ld, etc.).
        output_namespace: Base namespace for generated artefact IRIs.
        constraint_scheme: Optional filter to compile only ShapeMappings
                          in this ConstraintScheme.
        rule_scheme: Optional filter to compile only RuleMappings
                    in this RuleScheme.

    Returns:
        CompilationReport with individual results, combined graph,
        and aggregate errors/warnings.

    Example:
        >>> report = compile_mork_graph("my_mappings.ttl", "output.ttl")
        >>> if report.is_valid:
        ...     print(f"Generated {len(report.results)} artefacts")
        ... else:
        ...     for iri, err in report.errors:
        ...         print(f"ERROR: {iri}: {err}")
    """
    if isinstance(source, str):
        g = Graph()
        g.parse(source, format="turtle")
    else:
        g = source

    compiler = MorkCompiler(
        source_graph=g,
        output_namespace=output_namespace,
    )

    report = compiler.compile(
        constraint_scheme=constraint_scheme,
        rule_scheme=rule_scheme,
    )

    if output_path and report.is_valid:
        report.combined_graph.serialize(
            output_path, format=output_format
        )
        logger.info("Output written to %s", output_path)

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print(
            "Usage: python mork_compiler.py <input.ttl> [output.ttl]",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    report = compile_mork_graph(input_path, output_path)

    print(f"\n{'='*60}")
    print(f"MORK Compiler Report")
    print(f"{'='*60}")
    print(f"Artefacts compiled: {len(report.results)}")
    print(f"  SHACL shapes:    {sum(1 for r in report.results if r.artefact_type == 'SHACL')}")
    print(f"  SWRL rules:      {sum(1 for r in report.results if r.artefact_type == 'SWRL')}")
    print(f"  SPARQL queries:  {sum(1 for r in report.results if r.artefact_type == 'SPARQL')}")
    print(f"Precedence order:  {len(report.precedence_order)} nodes")
    print(f"Errors:            {len(report.errors)}")
    print(f"Warnings:          {len(report.warnings)}")
    print(f"Valid:             {report.is_valid}")

    if report.errors:
        print(f"\nErrors:")
        for iri, err in report.errors:
            print(f"  {iri}: {err}")

    if report.warnings:
        print(f"\nWarnings:")
        for iri, warn in report.warnings:
            print(f"  {iri}: {warn}")

    if output_path and report.is_valid:
        print(f"\nOutput written to: {output_path}")
    elif not report.is_valid:
        print(f"\nCompilation failed; no output written.")
        sys.exit(2)
