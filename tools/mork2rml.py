# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
MORK-to-RML Compiler

Implements the compilation functor C: MorkDAG → RMLDAG as defined in
Mork's Foundations §10. This module takes a MORK mapping graph (as an RDF graph
queried via rdflib) and produces an RML mapping document (as an RDF graph).

The compiler implements the catamorphism over the MORK DAG structure,
producing RML TriplesMap, SubjectMap, PredicateObjectMap, and
RefObjectMap constructs according to the case analysis of Definition 10.7.

Prerequisites:
    pip install rdflib

Usage:
    from mork_to_rml import MorkToRmlCompiler

    compiler = MorkToRmlCompiler(mork_graph, base_iri="http://example.org/")
    rml_graph = compiler.compile()
    print(rml_graph.serialize(format="turtle"))
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD
from rdflib.term import Node

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Namespace declarations
# ---------------------------------------------------------------------------

MORK = Namespace("http://www.nebularis.org/ontologies/Mork#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
RR = Namespace("http://www.w3.org/ns/r2rml#")
RML = Namespace("http://semweb.mmlab.be/ns/rml#")
QL = Namespace("http://semweb.mmlab.be/ns/ql#")
FNML = Namespace("http://semweb.mmlab.be/ns/fnml#")
D2RQ = Namespace("http://www.wiwiss.fu-berlin.de/suhl/bizer/D2RQ/0.1#")
PROV = Namespace("http://www.w3.org/ns/prov#")


# ---------------------------------------------------------------------------
# Enumerations for mapping classification
# ---------------------------------------------------------------------------


class BoxStratum(Enum):
    """The ontological stratum targeted by a mapping (Foundations §2.4)."""

    TBOX = auto()
    RBOX = auto()
    ABOX = auto()
    UNKNOWN = auto()


class MappingRole(Enum):
    """
    Classification of a DataMapping node by its role in the DAG.
    Corresponds to the case analysis in Definition 10.7.
    """

    TBOX_CLASS_CREATION = auto()      # Case 1: broadTBoxCategoryMatch
    TBOX_CLASS_REFERENCE = auto()     # Case 1: exactTBoxMatch only
    DATUM_INDIVIDUATION = auto()      # Case 2: Datum with deferredMapping
    RBOX_PROPERTY_ASSERTION = auto()  # Case 3: exactRBoxMatch + dataRef
    CONTEXTUAL_APPLICATION = auto()   # Case 4: broaderApplicative
    TEMPLATE_COMPOSITION = auto()     # Case 5: templateMapping
    REFERENCE_DATA_LOOKUP = auto()    # Case 6: referenceDataMapping / Lookup
    SHAPE_MAPPING = auto()            # Not compiled to RML (§10.10)
    RULE_MAPPING = auto()             # Not compiled to RML (§10.10)
    UNCLASSIFIED = auto()


class SourceFormat(Enum):
    """Serialization format, determining the RML reference formulation."""

    JSON = auto()
    XML = auto()
    CSV = auto()
    YAML = auto()
    UNKNOWN = auto()


# ---------------------------------------------------------------------------
# Data structures for intermediate representation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MappingSpec:
    """
    The specification λ(v) for a single DataMapping node, extracted from
    the MORK graph. This captures all the information needed to compile
    the node to RML.
    """

    node: URIRef
    role: MappingRole

    # Box matches
    exact_tbox_match: Optional[URIRef] = None
    broad_tbox_category_match: Optional[URIRef] = None
    narrow_tbox_category_match: Optional[URIRef] = None
    exact_rbox_match: Optional[URIRef] = None
    inverse_rbox_match: Optional[URIRef] = None
    exact_abox_match: Optional[URIRef] = None
    broad_abox_category_match: Optional[URIRef] = None

    # Identity and naming
    concept_name: Optional[str] = None
    concept_name_template: Optional[str] = None
    concept_fq_name_template: Optional[str] = None
    concept_short_name_template: Optional[str] = None

    # Data references
    data_ref: Optional[str] = None
    data_inline: Optional[str] = None

    # Template expressions (compiled to RML template strings)
    identity_template_expression: Optional[URIRef] = None

    # Reference data
    reference_data_path: Optional[URIRef] = None

    # Structural relationships
    deferred_mapping: Optional[URIRef] = None
    broader_applicative: Optional[URIRef] = None
    template_mapping: Optional[URIRef] = None
    identity_template_mapping: Optional[URIRef] = None

    # Children (compositeNarrowerMapping targets)
    children: FrozenSet[URIRef] = field(default_factory=frozenset)

    # Confidence
    weighting: Optional[int] = None

    # Source context
    source_format: SourceFormat = SourceFormat.UNKNOWN
    source_uri: Optional[str] = None
    iterator_path: Optional[str] = None


@dataclass
class CompilationContext:
    """
    Mutable context accumulated during compilation. Tracks the mapping
    from MORK nodes to RML triples maps, enabling cross-references
    (referencing object maps / join conditions).
    """

    # Map from MORK DataMapping URI to compiled RML TriplesMap URI
    triples_map_for: Dict[URIRef, URIRef] = field(default_factory=dict)

    # Map from MORK DataMapping URI to its compiled SubjectMap template
    subject_template_for: Dict[URIRef, str] = field(default_factory=dict)

    # Map from MORK DataMapping URI to the OWL class it establishes
    class_for: Dict[URIRef, URIRef] = field(default_factory=dict)

    # Nodes that have been compiled (to detect re-entry)
    compiled: Set[URIRef] = field(default_factory=set)

    # Nodes currently being compiled (to detect cycles — should not
    # occur if SHACL acyclicity validation has passed)
    in_progress: Set[URIRef] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Graph analysis: extracting MappingSpec from the MORK graph
# ---------------------------------------------------------------------------


class MorkGraphAnalyser:
    """
    Extracts MappingSpec instances from a MORK RDF graph.

    This corresponds to the labelling function λ : V → Spec in
    Definition 10.5. For each DataMapping individual in the graph,
    we extract its box matches, data references, structural relationships,
    and source context, and classify it by MappingRole.
    """

    def __init__(self, graph: Graph):
        self.g = graph

    def extract_all_mappings(self) -> Dict[URIRef, MappingSpec]:
        """
        Extract MappingSpec for every DataMapping individual in the graph.
        Returns a dict keyed by the DataMapping URI.
        """
        mappings: Dict[URIRef, MappingSpec] = {}
        for node in self._find_data_mappings():
            spec = self._extract_spec(node)
            mappings[node] = spec
        return mappings

    def _find_data_mappings(self) -> List[URIRef]:
        """Find all individuals that are (inferred or asserted) DataMapping."""
        results = set()
        # Direct type assertions
        for s in self.g.subjects(RDF.type, MORK.DataMapping):
            if isinstance(s, URIRef):
                results.add(s)
        # Subtypes of DataMapping
        for subclass in [MORK.Datum, MORK.WeightedMatch, MORK.Lookup,
                         MORK.IndexedMapping, MORK.DeferredContext,
                         MORK.Hypothesis, MORK.UncertainMapping,
                         MORK.ShapeMapping, MORK.RuleMapping]:
            for s in self.g.subjects(RDF.type, subclass):
                if isinstance(s, URIRef):
                    results.add(s)
        # Individuals with mappingScheme (entails DataMapping by class axiom)
        for s in self.g.subjects(MORK.mappingScheme, None):
            if isinstance(s, URIRef):
                results.add(s)
        return sorted(results, key=str)

    def _extract_spec(self, node: URIRef) -> MappingSpec:
        """Extract the full specification for a single DataMapping node."""
        # Box matches
        exact_tbox = self._obj(node, MORK.exactTBoxMatch)
        broad_tbox = self._obj(node, MORK.broadTBoxCategoryMatch)
        narrow_tbox = self._obj(node, MORK.narrowTBoxCategoryMatch)
        exact_rbox = self._obj(node, MORK.exactRBoxMatch)
        inverse_rbox = self._obj(node, MORK.inverseRBoxMatch)
        exact_abox = self._obj(node, MORK.exactABoxMatch)
        broad_abox = self._obj(node, MORK.broadABoxCategoryMatch)

        # Naming and identity
        concept_name = self._lit(node, MORK.conceptName)
        concept_name_template = self._lit(node, MORK.conceptNameTemplate)
        concept_fq_name_template = self._lit(node, MORK.conceptFQNameTemplate)
        concept_short_name_template = self._lit(node, MORK.conceptShortNameTemplate)

        # Data references
        data_ref = self._lit(node, MORK.dataRef)
        data_inline = self._lit(node, MORK.dataInline)

        # Structural relationships
        deferred = self._obj(node, MORK.deferredMapping)
        applicative = self._obj(node, MORK.broaderApplicative)
        template = self._obj(node, MORK.templateMapping)
        identity_template = self._obj(node, MORK.identityTemplateMapping)
        ref_data_path = self._obj(node, MORK.referenceDataPath)

        # Children
        children = frozenset(
            o for o in self.g.objects(node, MORK.compositeNarrowerMapping)
            if isinstance(o, URIRef)
        )

        # Confidence
        weighting_lit = self._lit(node, MORK.weighting)
        weighting = int(weighting_lit) if weighting_lit is not None else None

        # Source context (derived from representation scheme)
        source_format, source_uri, iterator_path = self._derive_source_context(node)

        # Template expression for identity
        identity_expr = self._find_identity_expression(node)

        # Classify the role
        role = self._classify_role(
            node, exact_tbox, broad_tbox, exact_rbox, inverse_rbox,
            exact_abox, broad_abox, deferred, applicative, template,
            data_ref, ref_data_path
        )

        return MappingSpec(
            node=node,
            role=role,
            exact_tbox_match=exact_tbox,
            broad_tbox_category_match=broad_tbox,
            narrow_tbox_category_match=narrow_tbox,
            exact_rbox_match=exact_rbox,
            inverse_rbox_match=inverse_rbox,
            exact_abox_match=exact_abox,
            broad_abox_category_match=broad_abox,
            concept_name=concept_name,
            concept_name_template=concept_name_template,
            concept_fq_name_template=concept_fq_name_template,
            concept_short_name_template=concept_short_name_template,
            data_ref=data_ref,
            data_inline=data_inline,
            identity_template_expression=identity_expr,
            reference_data_path=ref_data_path,
            deferred_mapping=deferred,
            broader_applicative=applicative,
            template_mapping=template,
            identity_template_mapping=identity_template,
            children=children,
            weighting=weighting,
            source_format=source_format,
            source_uri=source_uri,
            iterator_path=iterator_path,
        )

    def _classify_role(
        self,
        node: URIRef,
        exact_tbox: Optional[URIRef],
        broad_tbox: Optional[URIRef],
        exact_rbox: Optional[URIRef],
        inverse_rbox: Optional[URIRef],
        exact_abox: Optional[URIRef],
        broad_abox: Optional[URIRef],
        deferred: Optional[URIRef],
        applicative: Optional[URIRef],
        template: Optional[URIRef],
        data_ref: Optional[str],
        ref_data_path: Optional[URIRef],
    ) -> MappingRole:
        """
        Classify a mapping node by its role. Corresponds to the case
        analysis in Definition 10.7.

        Priority order follows the specificity of the mapping pattern:
        more specific patterns (ShapeMapping, RuleMapping, Lookup) are
        checked before more general ones (T-Box, Datum).
        """
        # Check for non-RML compilation targets first
        if self._is_type(node, MORK.ShapeMapping):
            return MappingRole.SHAPE_MAPPING
        if self._is_type(node, MORK.RuleMapping):
            return MappingRole.RULE_MAPPING

        # Case 6: Reference data lookup
        if self._is_type(node, MORK.Lookup) or ref_data_path is not None:
            return MappingRole.REFERENCE_DATA_LOOKUP

        # Case 5: Template composition
        if template is not None:
            return MappingRole.TEMPLATE_COMPOSITION

        # Case 4: Contextual application
        if applicative is not None:
            return MappingRole.CONTEXTUAL_APPLICATION

        # Case 2: Datum individuation (has deferredMapping → is a Datum)
        if deferred is not None and self._is_type(node, MORK.Datum):
            return MappingRole.DATUM_INDIVIDUATION

        # Also check the equivalence: anything with deferredMapping to a
        # DataMapping is a Datum by the OWL equivalence axiom
        if deferred is not None:
            return MappingRole.DATUM_INDIVIDUATION

        # Case 1: T-Box class creation
        if broad_tbox is not None:
            return MappingRole.TBOX_CLASS_CREATION

        # Case 1: T-Box class reference (exact match, no creation)
        if exact_tbox is not None and broad_tbox is None:
            return MappingRole.TBOX_CLASS_REFERENCE

        # Case 3: R-Box property assertion
        if (exact_rbox is not None or inverse_rbox is not None) and data_ref is not None:
            return MappingRole.RBOX_PROPERTY_ASSERTION

        return MappingRole.UNCLASSIFIED

    def _derive_source_context(
        self, node: URIRef
    ) -> Tuple[SourceFormat, Optional[str], Optional[str]]:
        """
        Derive the logical source context for a mapping node.

        Walks up the mapping graph to find the RepresentationScheme
        (via mappingFor → representationScheme → format) and extracts
        the serialization format, source URI, and iterator path.
        """
        # Try to find the source representation via mappingFor
        for concept in self.g.objects(node, MORK.mappingFor):
            # Check if the concept has a representationScheme
            for rep_scheme in self.g.objects(concept, MORK.representationScheme):
                fmt = self._derive_format(rep_scheme)
                source_uri = self._lit(rep_scheme, MORK.identifier)
                # Iterator path from the concept's path property
                iterator = self._lit(concept, MORK.path)
                return fmt, source_uri, iterator

        # Try via hasMapping inverse
        for concept in self.g.subjects(MORK.hasMapping, node):
            for rep_scheme in self.g.objects(concept, MORK.representationScheme):
                fmt = self._derive_format(rep_scheme)
                source_uri = self._lit(rep_scheme, MORK.identifier)
                iterator = self._lit(concept, MORK.path)
                return fmt, source_uri, iterator

        # Derive from dataRef path syntax as a heuristic
        data_ref = self._lit(node, MORK.dataRef)
        if data_ref is not None:
            if "." in data_ref and "/" not in data_ref:
                return SourceFormat.JSON, None, None
            if "/" in data_ref:
                return SourceFormat.XML, None, None

        return SourceFormat.UNKNOWN, None, None

    def _derive_format(self, rep_scheme: Node) -> SourceFormat:
        """Determine the source format from a RepresentationScheme's format property."""
        for fmt_node in self.g.objects(rep_scheme, MORK.format):
            if fmt_node == MORK.JSON:
                return SourceFormat.JSON
            elif fmt_node == MORK.XML:
                return SourceFormat.XML
            elif fmt_node == MORK.YAML:
                return SourceFormat.YAML
            # Check by name if not a known individual
            name = str(fmt_node).lower()
            if "json" in name:
                return SourceFormat.JSON
            elif "xml" in name:
                return SourceFormat.XML
            elif "csv" in name:
                return SourceFormat.CSV
            elif "yaml" in name:
                return SourceFormat.YAML
        return SourceFormat.UNKNOWN

    def _find_identity_expression(self, node: URIRef) -> Optional[URIRef]:
        """
        Find the TemplateExpression used for IRI formation, if any.
        Follows identityTemplateMapping to locate the expression.
        """
        for target in self.g.objects(node, MORK.identityTemplateMapping):
            # The target mapping may have a template expression
            # associated via a TemplateExpression individual
            for expr in self.g.objects(target, MORK.concatLeft):
                return expr
            for expr in self.g.objects(target, MORK.templateString):
                return target
        return None

    def _obj(self, s: URIRef, p: URIRef) -> Optional[URIRef]:
        """Get the first object for (s, p, ?) that is a URIRef, or None."""
        for o in self.g.objects(s, p):
            if isinstance(o, URIRef):
                return o
        return None

    def _lit(self, s: URIRef, p: URIRef) -> Optional[str]:
        """Get the first literal value for (s, p, ?) as a string, or None."""
        for o in self.g.objects(s, p):
            if isinstance(o, Literal):
                return str(o)
        return None

    def _is_type(self, node: URIRef, cls: URIRef) -> bool:
        """Check if node is asserted to be of type cls."""
        return (node, RDF.type, cls) in self.g


# ---------------------------------------------------------------------------
# Topological sort: computing the execution schedule
# ---------------------------------------------------------------------------


class DependencyAnalyser:
    """
    Computes the dependency partial order and a valid topological sort
    for the MORK mapping DAG.

    This implements the precedence derivation of Foundations §2.5.
    The topological sort provides the compilation order: nodes are
    compiled bottom-up so that parent triples maps exist before
    child referencing object maps are created.
    """

    def __init__(self, specs: Dict[URIRef, MappingSpec]):
        self.specs = specs
        self.adjacency: Dict[URIRef, Set[URIRef]] = defaultdict(set)
        self.in_degree: Dict[URIRef, int] = defaultdict(int)
        self._build_dependency_graph()

    def _build_dependency_graph(self):
        """
        Build the dependency graph from structural relationships.

        Edges point from dependency to dependent (i.e., from the node
        that must be compiled first to the node that depends on it).
        This is the :precedes direction.
        """
        all_nodes = set(self.specs.keys())

        for node, spec in self.specs.items():
            self.in_degree.setdefault(node, 0)

            # P1: Parent precedes composite children
            # If node has compositeBroaderMapping to parent, parent precedes node
            for child in spec.children:
                if child in all_nodes:
                    self.adjacency[node].add(child)
                    self.in_degree[child] = self.in_degree.get(child, 0) + 1

            # P2: Applicative parent precedes child
            if spec.broader_applicative and spec.broader_applicative in all_nodes:
                self.adjacency[spec.broader_applicative].add(node)
                self.in_degree[node] = self.in_degree.get(node, 0) + 1

            # P6/P7: T-Box mapping precedes Datum (via deferredMapping)
            if spec.role == MappingRole.DATUM_INDIVIDUATION and spec.deferred_mapping:
                if spec.deferred_mapping in all_nodes:
                    deferred_spec = self.specs.get(spec.deferred_mapping)
                    if deferred_spec and deferred_spec.role in (
                        MappingRole.TBOX_CLASS_CREATION,
                        MappingRole.TBOX_CLASS_REFERENCE,
                    ):
                        self.adjacency[spec.deferred_mapping].add(node)
                        self.in_degree[node] = self.in_degree.get(node, 0) + 1

            # P8: Identity template mapping precedes datum
            if spec.identity_template_mapping and spec.identity_template_mapping in all_nodes:
                self.adjacency[spec.identity_template_mapping].add(node)
                self.in_degree[node] = self.in_degree.get(node, 0) + 1

            # P10: Template precedes instantiation
            if spec.template_mapping and spec.template_mapping in all_nodes:
                self.adjacency[spec.template_mapping].add(node)
                self.in_degree[node] = self.in_degree.get(node, 0) + 1

    def topological_sort(self) -> List[URIRef]:
        """
        Kahn's algorithm for topological sort.

        Returns nodes in dependency order: nodes with no dependencies first.
        This is the order in which the catamorphism should be evaluated
        (Theorem 4.2 guarantees termination for acyclic DAGs).

        Raises ValueError if a cycle is detected (should not occur if
        SHACL acyclicity validation has passed).
        """
        in_deg = dict(self.in_degree)
        queue = [n for n in self.specs if in_deg.get(n, 0) == 0]
        result = []

        while queue:
            # Stable sort for deterministic output
            queue.sort(key=str)
            node = queue.pop(0)
            result.append(node)

            for dependent in sorted(self.adjacency.get(node, set()), key=str):
                in_deg[dependent] -= 1
                if in_deg[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self.specs):
            compiled = set(result)
            remaining = set(self.specs.keys()) - compiled
            raise ValueError(
                f"Cycle detected in mapping DAG. "
                f"Nodes involved: {remaining}"
            )

        return result


# ---------------------------------------------------------------------------
# Template expression compiler
# ---------------------------------------------------------------------------


class TemplateExpressionCompiler:
    """
    Compiles MORK TemplateExpression individuals into RML template strings.

    Implements Definition 10.9 (IRI Template Compilation).

    The compilation is structural: each TemplateExpression subclass maps
    to a specific RML template string fragment. Lookup expressions
    cannot be compiled to template strings (Remark 10.10) and are
    flagged for compilation as referencing object maps instead.
    """

    def __init__(self, graph: Graph):
        self.g = graph

    def compile(self, expr_node: URIRef, base_iri: str = "") -> Optional[str]:
        """
        Compile a TemplateExpression to an RML template string.

        Returns None if the expression contains a LookupExpression
        (which requires a referencing object map instead).
        """
        return self._compile_node(expr_node, base_iri)

    def _compile_node(self, node: Node, base_iri: str) -> Optional[str]:
        """Recursive compilation by expression type."""
        if not isinstance(node, URIRef):
            return None

        g = self.g

        # LiteralExpression: return the dataInline value
        if (node, RDF.type, MORK.LiteralExpression) in g:
            for val in g.objects(node, MORK.dataInline):
                return str(val)
            return ""

        # RefExpression: return RML reference syntax
        if (node, RDF.type, MORK.RefExpression) in g:
            for val in g.objects(node, MORK.dataRef):
                return "{" + str(val) + "}"
            return None

        # ConcatExpression: compile both sides and concatenate
        if (node, RDF.type, MORK.ConcatExpression) in g:
            left_node = None
            right_node = None
            for o in g.objects(node, MORK.concatLeft):
                left_node = o
            for o in g.objects(node, MORK.concatRight):
                right_node = o
            if left_node is None or right_node is None:
                logger.warning(
                    "ConcatExpression %s missing operand(s)", node
                )
                return None
            left = self._compile_node(left_node, base_iri)
            right = self._compile_node(right_node, base_iri)
            if left is None or right is None:
                return None
            return left + right

        # InterpolationExpression: substitute placeholders
        if (node, RDF.type, MORK.InterpolationExpression) in g:
            template_str = None
            for val in g.objects(node, MORK.templateString):
                template_str = str(val)
            if template_str is None:
                return None
            # Collect bindings
            for binding in g.objects(node, MORK.hasBinding):
                ph_name = None
                ph_expr = None
                for val in g.objects(binding, MORK.placeholderName):
                    ph_name = str(val)
                for val in g.objects(binding, MORK.placeholderExpression):
                    ph_expr = val
                if ph_name and ph_expr:
                    compiled = self._compile_node(ph_expr, base_iri)
                    if compiled is not None:
                        template_str = template_str.replace(
                            "{" + ph_name + "}", compiled
                        )
            return template_str

        # LookupExpression: cannot compile to template string (Remark 10.10)
        if (node, RDF.type, MORK.LookupExpression) in g:
            logger.info(
                "LookupExpression %s requires referencing object map; "
                "cannot compile to template string",
                node,
            )
            return None

        # Fall back: try treating as a literal concept name or IRI
        for val in g.objects(node, MORK.conceptName):
            name = str(val)
            if name.startswith("#"):
                return base_iri + name[1:]
            return name

        for val in g.objects(node, MORK.iri):
            return str(val)

        logger.warning("Cannot compile expression node %s", node)
        return None

    def compile_from_data_ref(self, data_ref: str) -> str:
        """Compile a simple dataRef path to an RML reference."""
        return "{" + data_ref + "}"

    def compile_from_concept_name(
        self, concept_name: str, base_iri: str
    ) -> str:
        """Compile a conceptName to an IRI template."""
        if concept_name.startswith("#"):
            return base_iri + concept_name[1:]
        return base_iri + concept_name


# ---------------------------------------------------------------------------
# The compilation functor
# ---------------------------------------------------------------------------


class MorkToRmlCompiler:
    """
    The compilation functor C: MorkDAG → RMLDAG.

    Implements the catamorphism of Definition 10.13, producing an RML
    mapping document from a MORK mapping graph.

    The compilation proceeds in dependency order (topological sort of the
    MORK precedence graph) so that parent triples maps are available
    when child referencing object maps need to reference them.
    """

    def __init__(
        self,
        mork_graph: Graph,
        base_iri: str = "http://example.org/",
        rml_base: str = "http://example.org/rml/",
        default_source: Optional[str] = None,
        default_format: SourceFormat = SourceFormat.JSON,
        default_iterator: str = "$",
    ):
        """
        Args:
            mork_graph: The MORK RDF graph to compile.
            base_iri: Base IRI for generated ontological individuals.
            rml_base: Base IRI for generated RML mapping nodes.
            default_source: Default logical source URI when not derivable.
            default_format: Default serialization format.
            default_iterator: Default iterator expression.
        """
        self.mork = mork_graph
        self.base_iri = base_iri.rstrip("/") + "/"
        self.rml_base = rml_base.rstrip("/") + "/"
        self.default_source = default_source or "input.json"
        self.default_format = default_format
        self.default_iterator = default_iterator

        self.analyser = MorkGraphAnalyser(mork_graph)
        self.expr_compiler = TemplateExpressionCompiler(mork_graph)

        # Output RML graph
        self.rml = Graph()
        self._bind_namespaces()

        # Compilation context
        self.ctx = CompilationContext()

        # Extracted specs (populated during compile())
        self.specs: Dict[URIRef, MappingSpec] = {}

    def _bind_namespaces(self):
        """Bind standard namespaces for readable Turtle output."""
        self.rml.bind("rr", RR)
        self.rml.bind("rml", RML)
        self.rml.bind("ql", QL)
        self.rml.bind("rdf", RDF)
        self.rml.bind("rdfs", RDFS)
        self.rml.bind("owl", OWL)
        self.rml.bind("xsd", XSD)
        self.rml.bind("mork", MORK)
        self.rml.bind("d2rq", D2RQ)

    def compile(self) -> Graph:
        """
        Execute the compilation functor.

        Returns:
            An rdflib Graph containing the compiled RML mapping document.

        Raises:
            ValueError: If the MORK DAG contains cycles.
        """
        # Phase 1: Extract all mapping specifications (Definition 10.5)
        logger.info("Phase 1: Extracting mapping specifications")
        self.specs = self.analyser.extract_all_mappings()
        logger.info("Found %d DataMapping individuals", len(self.specs))

        # Filter out non-RML targets
        compilable = {
            uri: spec
            for uri, spec in self.specs.items()
            if spec.role not in (
                MappingRole.SHAPE_MAPPING,
                MappingRole.RULE_MAPPING,
            )
        }
        skipped = len(self.specs) - len(compilable)
        if skipped > 0:
            logger.info(
                "Skipping %d ShapeMapping/RuleMapping nodes "
                "(not compiled to RML, see Foundations §10.10)",
                skipped,
            )

        # Phase 2: Compute dependency order (Definition 10.6)
        logger.info("Phase 2: Computing dependency order")
        dep_analyser = DependencyAnalyser(compilable)
        order = dep_analyser.topological_sort()
        logger.info("Topological order: %s", [str(n).split("#")[-1] for n in order])

        # Phase 3: Compile in dependency order (catamorphism, Definition 10.13)
        logger.info("Phase 3: Compiling to RML")
        for node in order:
            spec = compilable[node]
            self._compile_node(spec)

        logger.info(
            "Compilation complete. Generated %d triples.",
            len(self.rml),
        )
        return self.rml

    # -------------------------------------------------------------------
    # Case dispatch (Definition 10.7)
    # -------------------------------------------------------------------

    def _compile_node(self, spec: MappingSpec):
        """
        Compile a single mapping node by dispatching on its role.
        This is the algebra map α of Definition 10.13.
        """
        node = spec.node

        if node in self.ctx.compiled:
            return
        if node in self.ctx.in_progress:
            raise ValueError(f"Cycle detected at {node}")

        self.ctx.in_progress.add(node)

        try:
            if spec.role == MappingRole.TBOX_CLASS_CREATION:
                self._compile_tbox_creation(spec)
            elif spec.role == MappingRole.TBOX_CLASS_REFERENCE:
                self._compile_tbox_reference(spec)
            elif spec.role == MappingRole.DATUM_INDIVIDUATION:
                self._compile_datum(spec)
            elif spec.role == MappingRole.RBOX_PROPERTY_ASSERTION:
                self._compile_property_assertion(spec)
            elif spec.role == MappingRole.CONTEXTUAL_APPLICATION:
                self._compile_contextual_application(spec)
            elif spec.role == MappingRole.TEMPLATE_COMPOSITION:
                self._compile_template_composition(spec)
            elif spec.role == MappingRole.REFERENCE_DATA_LOOKUP:
                self._compile_reference_lookup(spec)
            elif spec.role == MappingRole.UNCLASSIFIED:
                logger.warning(
                    "Node %s could not be classified; "
                    "generating pass-through triples map",
                    node,
                )
                self._compile_passthrough(spec)
            else:
                logger.warning("Skipping node %s with role %s", node, spec.role)
        finally:
            self.ctx.in_progress.discard(node)
            self.ctx.compiled.add(node)

    # -------------------------------------------------------------------
    # Case 1: T-Box class creation (broadTBoxCategoryMatch)
    # -------------------------------------------------------------------

    def _compile_tbox_creation(self, spec: MappingSpec):
        """
        Case 1a: broadTBoxCategoryMatch with conceptName.
        Generates a TriplesMap that asserts rdfs:subClassOf.
        """
        node = spec.node
        tm = self._mint_triples_map(node)
        ls = self._make_logical_source(spec)

        # Determine the new class IRI
        class_iri = self._resolve_class_iri(spec)
        if class_iri is None:
            logger.warning(
                "T-Box creation node %s has no resolvable class IRI", node
            )
            return

        # Record the class for downstream use
        self.ctx.class_for[node] = class_iri

        # Subject map: the new class
        sm = BNode()
        self.rml.add((tm, RR.subjectMap, sm))
        self.rml.add((sm, RR.constant, class_iri))
        self.rml.add((sm, RR.termType, RR.IRI))
        self.rml.add((sm, RR["class"], OWL.Class))

        self.ctx.subject_template_for[node] = str(class_iri)

        # Predicate-object map: rdfs:subClassOf → parent class
        if spec.broad_tbox_category_match:
            pom = BNode()
            om = BNode()
            self.rml.add((tm, RR.predicateObjectMap, pom))
            self.rml.add((pom, RR.predicate, RDFS.subClassOf))
            self.rml.add((pom, RR.objectMap, om))
            self.rml.add((om, RR.constant, spec.broad_tbox_category_match))
            self.rml.add((om, RR.termType, RR.IRI))

        # Compile children
        self._compile_children_as_poms(spec, tm)

    def _compile_tbox_reference(self, spec: MappingSpec):
        """
        Case 1b: exactTBoxMatch only (class already exists).
        No triples map generated; only records the class for downstream.
        """
        if spec.exact_tbox_match:
            self.ctx.class_for[spec.node] = spec.exact_tbox_match
            self.ctx.subject_template_for[spec.node] = str(spec.exact_tbox_match)

    # -------------------------------------------------------------------
    # Case 2: Datum individuation
    # -------------------------------------------------------------------

    def _compile_datum(self, spec: MappingSpec):
        """
        Case 2: Datum with deferredMapping to a T-Box mapping.
        Generates a TriplesMap that creates individuals of the deferred class.
        """
        node = spec.node
        tm = self._mint_triples_map(node)
        ls = self._make_logical_source(spec)

        # Resolve the class from the deferred mapping
        target_class = None
        if spec.deferred_mapping and spec.deferred_mapping in self.ctx.class_for:
            target_class = self.ctx.class_for[spec.deferred_mapping]
        elif spec.exact_tbox_match:
            target_class = spec.exact_tbox_match
        elif spec.broad_tbox_category_match:
            target_class = spec.broad_tbox_category_match

        # Build the subject map with IRI template
        sm = BNode()
        self.rml.add((tm, RR.subjectMap, sm))

        subject_template = self._build_subject_template(spec)
        self.rml.add((sm, RR.template, Literal(subject_template)))
        self.rml.add((sm, RR.termType, RR.IRI))

        if target_class:
            self.rml.add((sm, RR["class"], target_class))

        self.ctx.subject_template_for[node] = subject_template

        # Compile children as predicate-object maps
        self._compile_children_as_poms(spec, tm)

    # -------------------------------------------------------------------
    # Case 3: R-Box property assertion
    # -------------------------------------------------------------------

    def _compile_property_assertion(self, spec: MappingSpec):
        """
        Case 3: exactRBoxMatch + dataRef.
        Generates a PredicateObjectMap (to be embedded in a parent TriplesMap).

        If this node has no parent (is a root), a standalone TriplesMap is
        generated with a pass-through subject.
        """
        node = spec.node

        # Determine the property
        prop = spec.exact_rbox_match or spec.inverse_rbox_match
        if prop is None:
            logger.warning(
                "R-Box assertion node %s has no exactRBoxMatch", node
            )
            return

        # Find the parent triples map
        parent_tm = self._find_parent_triples_map(node)

        if parent_tm is not None:
            # Embed as a predicate-object map in the parent
            self._add_property_assertion_pom(parent_tm, spec, prop)
        else:
            # No parent found — generate a standalone triples map
            tm = self._mint_triples_map(node)
            self._make_logical_source(spec)
            sm = BNode()
            self.rml.add((tm, RR.subjectMap, sm))
            subject_template = self._build_subject_template(spec)
            self.rml.add((sm, RR.template, Literal(subject_template)))
            self.rml.add((sm, RR.termType, RR.IRI))
            self._add_property_assertion_pom(tm, spec, prop)

    def _add_property_assertion_pom(
        self, parent_tm: URIRef, spec: MappingSpec, prop: URIRef
    ):
        """Add a predicate-object map for a property assertion."""
        pom = BNode()
        om = BNode()

        self.rml.add((parent_tm, RR.predicateObjectMap, pom))
        self.rml.add((pom, RR.predicate, prop))
        self.rml.add((pom, RR.objectMap, om))

        if spec.data_ref:
            self.rml.add((om, RML.reference, Literal(spec.data_ref)))
            # Determine term type from property range
            if self._is_object_property(prop):
                self.rml.add((om, RR.termType, RR.IRI))
            else:
                self.rml.add((om, RR.termType, RR.Literal))
        elif spec.data_inline:
            self.rml.add((om, RR.constant, Literal(spec.data_inline)))
        elif spec.exact_abox_match:
            self.rml.add((om, RR.constant, spec.exact_abox_match))
            self.rml.add((om, RR.termType, RR.IRI))
        elif spec.broad_abox_category_match:
            self.rml.add((om, RR.constant, spec.broad_abox_category_match))
            self.rml.add((om, RR.termType, RR.IRI))

    # -------------------------------------------------------------------
    # Case 4: Contextual application (broaderApplicative / Kleisli)
    # -------------------------------------------------------------------

    def _compile_contextual_application(self, spec: MappingSpec):
        """
        Case 4: broaderApplicative with exactRBoxMatch.
        Generates a TriplesMap with a referencing object map to the parent.
        """
        node = spec.node
        tm = self._mint_triples_map(node)
        ls = self._make_logical_source(spec)

        # Subject map
        sm = BNode()
        self.rml.add((tm, RR.subjectMap, sm))
        subject_template = self._build_subject_template(spec)
        self.rml.add((sm, RR.template, Literal(subject_template)))
        self.rml.add((sm, RR.termType, RR.IRI))

        # Determine target class
        target_class = self._resolve_target_class(spec)
        if target_class:
            self.rml.add((sm, RR["class"], target_class))

        self.ctx.subject_template_for[node] = subject_template

        # The gluing property (Axiom 2.14a guarantees this exists)
        gluing_prop = spec.exact_rbox_match or spec.inverse_rbox_match
        is_inverse = spec.inverse_rbox_match is not None and spec.exact_rbox_match is None

        # Parent triples map
        parent_node = spec.broader_applicative
        parent_tm_uri = self.ctx.triples_map_for.get(parent_node)

        if parent_tm_uri is None:
            logger.warning(
                "Contextual application node %s references parent %s "
                "which has no compiled triples map",
                node,
                parent_node,
            )
        elif gluing_prop is not None:
            if is_inverse:
                # inverseRBoxMatch: the triple goes in the PARENT triples map
                # parent_subject --gluing_prop--> child_subject
                pom = BNode()
                rom = BNode()
                self.rml.add((parent_tm_uri, RR.predicateObjectMap, pom))
                self.rml.add((pom, RR.predicate, gluing_prop))
                self.rml.add((pom, RR.objectMap, rom))
                self.rml.add((rom, RR.parentTriplesMap, tm))
                self._add_join_condition(rom, spec, parent_node)
            else:
                # exactRBoxMatch: the triple goes in THIS triples map
                # child_subject --gluing_prop--> parent_subject
                pom = BNode()
                rom = BNode()
                self.rml.add((tm, RR.predicateObjectMap, pom))
                self.rml.add((pom, RR.predicate, gluing_prop))
                self.rml.add((pom, RR.objectMap, rom))
                self.rml.add((rom, RR.parentTriplesMap, parent_tm_uri))
                self._add_join_condition(rom, spec, parent_node)

        # Compile children
        self._compile_children_as_poms(spec, tm)

    # -------------------------------------------------------------------
    # Case 5: Template composition
    # -------------------------------------------------------------------

    def _compile_template_composition(self, spec: MappingSpec):
        """
        Case 5: templateMapping.
        Merges the template's specification with the instantiation's,
        then compiles as the resulting case (Definition 3.7).
        """
        node = spec.node
        template_node = spec.template_mapping

        if template_node is None or template_node not in self.specs:
            logger.warning(
                "Template composition node %s has no resolvable template", node
            )
            # Fall through to compile with whatever we have
            self._compile_passthrough(spec)
            return

        template_spec = self.specs[template_node]

        # Merge: instantiation overrides template (Definition 3.7)
        merged = self._merge_specs(spec, template_spec)

        # Re-classify the merged spec and compile
        if merged.role != MappingRole.TEMPLATE_COMPOSITION:
            self._compile_node(merged)
        else:
            # Avoid infinite recursion: compile as the best non-template case
            self._compile_passthrough(merged)

    def _merge_specs(
        self, instantiation: MappingSpec, template: MappingSpec
    ) -> MappingSpec:
        """
        Merge an instantiation spec with a template spec.

        The instantiation's values take priority (first strategy in
        Definition 3.7: explicit references). Template values fill
        gaps where the instantiation does not specify.
        """

        def pick(inst_val, tmpl_val):
            return inst_val if inst_val is not None else tmpl_val

        # Merge children: correlate by templateBinding, then by order
        merged_children = self._merge_children(instantiation, template)

        # Re-classify the merged spec
        merged_role = self.analyser._classify_role(
            instantiation.node,
            pick(instantiation.exact_tbox_match, template.exact_tbox_match),
            pick(instantiation.broad_tbox_category_match, template.broad_tbox_category_match),
            pick(instantiation.exact_rbox_match, template.exact_rbox_match),
            pick(instantiation.inverse_rbox_match, template.inverse_rbox_match),
            pick(instantiation.exact_abox_match, template.exact_abox_match),
            pick(instantiation.broad_abox_category_match, template.broad_abox_category_match),
            pick(instantiation.deferred_mapping, template.deferred_mapping),
            pick(instantiation.broader_applicative, template.broader_applicative),
            None,  # No further template chaining
            pick(instantiation.data_ref, template.data_ref),
            pick(instantiation.reference_data_path, template.reference_data_path),
        )

        return MappingSpec(
            node=instantiation.node,
            role=merged_role,
            exact_tbox_match=pick(instantiation.exact_tbox_match, template.exact_tbox_match),
            broad_tbox_category_match=pick(instantiation.broad_tbox_category_match, template.broad_tbox_category_match),
            narrow_tbox_category_match=pick(instantiation.narrow_tbox_category_match, template.narrow_tbox_category_match),
            exact_rbox_match=pick(instantiation.exact_rbox_match, template.exact_rbox_match),
            inverse_rbox_match=pick(instantiation.inverse_rbox_match, template.inverse_rbox_match),
            exact_abox_match=pick(instantiation.exact_abox_match, template.exact_abox_match),
            broad_abox_category_match=pick(instantiation.broad_abox_category_match, template.broad_abox_category_match),
            concept_name=pick(instantiation.concept_name, template.concept_name),
            concept_name_template=pick(instantiation.concept_name_template, template.concept_name_template),
            concept_fq_name_template=pick(instantiation.concept_fq_name_template, template.concept_fq_name_template),
            concept_short_name_template=pick(instantiation.concept_short_name_template, template.concept_short_name_template),
            data_ref=pick(instantiation.data_ref, template.data_ref),
            data_inline=pick(instantiation.data_inline, template.data_inline),
            identity_template_expression=pick(instantiation.identity_template_expression, template.identity_template_expression),
            reference_data_path=pick(instantiation.reference_data_path, template.reference_data_path),
            deferred_mapping=pick(instantiation.deferred_mapping, template.deferred_mapping),
            broader_applicative=pick(instantiation.broader_applicative, template.broader_applicative),
            template_mapping=None,  # Consumed by merge
            identity_template_mapping=pick(instantiation.identity_template_mapping, template.identity_template_mapping),
            children=merged_children,
            weighting=pick(instantiation.weighting, template.weighting),
            source_format=pick_enum(instantiation.source_format, template.source_format, SourceFormat.UNKNOWN),
            source_uri=pick(instantiation.source_uri, template.source_uri),
            iterator_path=pick(instantiation.iterator_path, template.iterator_path),
        )

    def _merge_children(
        self, instantiation: MappingSpec, template: MappingSpec
    ) -> FrozenSet[URIRef]:
        """
        Merge children between instantiation and template.

        Follows the three-strategy resolution of Definition 3.7:
        1. Explicit templateBinding references
        2. OrderedCollection ordering
        3. IndexedMapping mappingIndex correlation
        """
        # Strategy 1: Check for explicit templateBinding
        bound_children = set()
        for child in instantiation.children:
            for tmpl_child in self.mork.objects(child, MORK.templateBinding):
                if tmpl_child in template.children:
                    bound_children.add(child)

        if bound_children:
            # Include explicitly bound children plus any unbound
            # instantiation children
            return frozenset(instantiation.children | template.children)

        # Strategy 2/3: Take the union (the execution engine handles
        # correlation at runtime based on ordered collections or indexes)
        return frozenset(instantiation.children | template.children)

    # -------------------------------------------------------------------
    # Case 6: Reference data lookup
    # -------------------------------------------------------------------

    def _compile_reference_lookup(self, spec: MappingSpec):
        """
        Case 6: Lookup with referenceDataMapping.
        Generates a predicate-object map with a referencing object map
        joined to the reference concept scheme.
        """
        node = spec.node

        prop = spec.exact_rbox_match or spec.inverse_rbox_match
        if prop is None:
            logger.warning("Lookup node %s has no exactRBoxMatch", node)
            return

        # The lookup produces a referencing object map that joins
        # source data (via dataRef) to a reference scheme (via
        # referenceDataPath on a SKOS property)

        # Find or create a triples map for the reference scheme
        ref_tm = self._get_or_create_reference_scheme_tm(spec)

        # Find the parent triples map to embed this POM in
        parent_tm = self._find_parent_triples_map(node)

        if parent_tm is None:
            # Create a standalone triples map
            tm = self._mint_triples_map(node)
            self._make_logical_source(spec)
            sm = BNode()
            self.rml.add((tm, RR.subjectMap, sm))
            subject_template = self._build_subject_template(spec)
            self.rml.add((sm, RR.template, Literal(subject_template)))
            self.rml.add((sm, RR.termType, RR.IRI))
            parent_tm = tm

        if ref_tm is not None:
            pom = BNode()
            rom = BNode()
            jc = BNode()

            self.rml.add((parent_tm, RR.predicateObjectMap, pom))
            self.rml.add((pom, RR.predicate, prop))
            self.rml.add((pom, RR.objectMap, rom))
            self.rml.add((rom, RR.parentTriplesMap, ref_tm))
            self.rml.add((rom, RR.joinCondition, jc))

            # Child key: the source data path
            child_key = spec.data_ref or "id"
            self.rml.add((jc, RR.child, Literal(child_key)))

            # Parent key: the reference data path (SKOS property)
            parent_key = str(spec.reference_data_path) if spec.reference_data_path else "skos:notation"
            self.rml.add((jc, RR.parent, Literal(parent_key)))

    def _get_or_create_reference_scheme_tm(
        self, spec: MappingSpec
    ) -> Optional[URIRef]:
        """
        Get or create a TriplesMap for the reference concept scheme
        that a Lookup resolves against.
        """
        # Determine the target class from exactTBoxMatch
        target_class = spec.exact_tbox_match
        if target_class is None:
            return None

        # Create a deterministic URI for the reference scheme TM
        ref_key = f"ref_{_safe_local_name(target_class)}"
        ref_tm = URIRef(self.rml_base + ref_key)

        if (ref_tm, RDF.type, RR.TriplesMap) in self.rml:
            return ref_tm

        # Create the reference scheme triples map
        self.rml.add((ref_tm, RDF.type, RR.TriplesMap))

        # Logical source: the reference data (typically a SKOS concept scheme)
        ls = BNode()
        self.rml.add((ref_tm, RML.logicalSource, ls))
        self.rml.add((ls, RML.source, Literal(f"reference_{_safe_local_name(target_class)}.json")))
        self.rml.add((ls, RML.referenceFormulation, QL.JSONPath))
        self.rml.add((ls, RML.iterator, Literal("$.[*]")))

        # Subject map: individuals of the target class
        sm = BNode()
        self.rml.add((ref_tm, RR.subjectMap, sm))
        self.rml.add((sm, RR.template, Literal(str(target_class) + "/{identifier}")))
        self.rml.add((sm, RR.termType, RR.IRI))
        self.rml.add((sm, RR["class"], target_class))

        return ref_tm

    # -------------------------------------------------------------------
    # Pass-through / fallback
    # -------------------------------------------------------------------

    def _compile_passthrough(self, spec: MappingSpec):
        """
        Generate a minimal triples map for nodes that do not fit
        cleanly into the case analysis. Preserves the mapping's
        assertions as best-effort RML.
        """
        node = spec.node
        tm = self._mint_triples_map(node)
        self._make_logical_source(spec)

        sm = BNode()
        self.rml.add((tm, RR.subjectMap, sm))
        subject_template = self._build_subject_template(spec)
        self.rml.add((sm, RR.template, Literal(subject_template)))
        self.rml.add((sm, RR.termType, RR.IRI))

        target_class = self._resolve_target_class(spec)
        if target_class:
            self.rml.add((sm, RR["class"], target_class))

        self.ctx.subject_template_for[node] = subject_template
        self._compile_children_as_poms(spec, tm)

    # -------------------------------------------------------------------
    # Child compilation
    # -------------------------------------------------------------------

    def _compile_children_as_poms(self, spec: MappingSpec, parent_tm: URIRef):
        """
        Compile a node's compositeNarrowerMapping children.

        Property assertion children (Case 3) are embedded as predicate-object
        maps in the parent triples map. Other children generate their own
        triples maps (handled by their own _compile_node call in the
        topological traversal) and are linked via referencing object maps.
        """
        for child_uri in sorted(spec.children, key=str):
            if child_uri not in self.specs:
                logger.warning(
                    "Child %s of %s not found in mapping specs",
                    child_uri,
                    spec.node,
                )
                continue

            child_spec = self.specs[child_uri]

            if child_spec.role == MappingRole.RBOX_PROPERTY_ASSERTION:
                # Embed directly as a POM
                prop = child_spec.exact_rbox_match or child_spec.inverse_rbox_match
                if prop:
                    self._add_property_assertion_pom(parent_tm, child_spec, prop)
                    self.ctx.compiled.add(child_uri)
            elif child_spec.role == MappingRole.REFERENCE_DATA_LOOKUP:
                # Lookup children get compiled separately but their
                # POM is embedded in the parent
                self._compile_reference_lookup(child_spec)
                self.ctx.compiled.add(child_uri)
            else:
                # Other children (Datum, contextual application, etc.)
                # are compiled as separate triples maps. The link is
                # established via the child's broaderApplicative or
                # the parent-child structural relationship.
                child_tm = self.ctx.triples_map_for.get(child_uri)
                if child_tm is not None:
                    # Child already compiled — add a referencing object map
                    # if there is a connecting property
                    connecting_prop = child_spec.exact_rbox_match
                    if connecting_prop:
                        pom = BNode()
                        rom = BNode()
                        self.rml.add((parent_tm, RR.predicateObjectMap, pom))
                        self.rml.add((pom, RR.predicate, connecting_prop))
                        self.rml.add((pom, RR.objectMap, rom))
                        self.rml.add((rom, RR.parentTriplesMap, child_tm))
                        self._add_join_condition(rom, child_spec, spec.node)

    # -------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------

    def _mint_triples_map(self, mork_node: URIRef) -> URIRef:
        """
        Create a new RML TriplesMap individual for a MORK mapping node.
        Uses a deterministic IRI derived from the MORK node's IRI.
        """
        local = _safe_local_name(mork_node)
        tm_uri = URIRef(self.rml_base + "TM_" + local)
        self.rml.add((tm_uri, RDF.type, RR.TriplesMap))
        self.ctx.triples_map_for[mork_node] = tm_uri

        # Add provenance annotation linking back to the MORK node
        self.rml.add((tm_uri, RDFS.isDefinedBy, mork_node))

        # Add weighting as an annotation if present
        spec = self.specs.get(mork_node)
        if spec and spec.weighting is not None:
            self.rml.add((tm_uri, MORK.weighting, Literal(spec.weighting, datatype=XSD.integer)))

        return tm_uri

    def _make_logical_source(self, spec: MappingSpec) -> BNode:
        """
        Create and attach a logical source to the triples map for this node.
        Implements Definition 10.8 (Logical Source Derivation).
        """
        tm = self.ctx.triples_map_for.get(spec.node)
        if tm is None:
            raise ValueError(f"No triples map for {spec.node}")

        ls = BNode()
        self.rml.add((tm, RML.logicalSource, ls))

        # Source URI
        source = spec.source_uri or self.default_source
        self.rml.add((ls, RML.source, Literal(source)))

        # Reference formulation (from format)
        fmt = spec.source_format
        if fmt == SourceFormat.UNKNOWN:
            fmt = self.default_format

        ref_form = {
            SourceFormat.JSON: QL.JSONPath,
            SourceFormat.XML: QL.XPath,
            SourceFormat.CSV: QL.CSV,
            SourceFormat.YAML: QL.JSONPath,  # YAML typically parsed as JSON
        }.get(fmt, QL.JSONPath)

        self.rml.add((ls, RML.referenceFormulation, ref_form))

        # Iterator
        iterator = spec.iterator_path or self._derive_iterator(spec)
        self.rml.add((ls, RML.iterator, Literal(iterator)))

        return ls

    def _derive_iterator(self, spec: MappingSpec) -> str:
        """
        Derive the iterator expression from the mapping's data context.
        For JSON, this is typically a JSONPath expression.
        """
        if spec.data_ref:
            # Use the data_ref path, stripping the leaf element
            parts = spec.data_ref.rsplit(".", 1)
            if len(parts) > 1:
                return "$." + parts[0] + "[*]"
            return "$." + spec.data_ref

        return self.default_iterator

    def _build_subject_template(self, spec: MappingSpec) -> str:
        """
        Build the RML subject template for a mapping node.
        Implements the IRI formation logic of Definition 3.9.6.
        """
        # Try TemplateExpression first
        if spec.identity_template_expression:
            compiled = self.expr_compiler.compile(
                spec.identity_template_expression, self.base_iri
            )
            if compiled is not None:
                return compiled

        # Try conceptNameTemplate
        if spec.concept_fq_name_template:
            return self._compile_name_template(spec.concept_fq_name_template)
        if spec.concept_name_template:
            return self._compile_name_template(spec.concept_name_template)

        # Try conceptName
        if spec.concept_name:
            name = spec.concept_name
            if name.startswith("#"):
                return self.base_iri + name[1:]
            return self.base_iri + name + "/{" + (spec.data_ref or "id") + "}"

        # Fall back to a hash-based template
        if spec.data_ref:
            return self.base_iri + _safe_local_name(spec.node) + "/{" + spec.data_ref + "}"

        # Last resort: use the MORK node's local name
        return self.base_iri + _safe_local_name(spec.node) + "/{id}"

    def _compile_name_template(self, template: str) -> str:
        """
        Compile a MORK conceptNameTemplate (e.g., "Item{$name}") to
        an RML template string (e.g., "http://example.org/Item{name}").
        """
        # Replace MORK placeholder syntax ${...} or {$...} with RML {ref}
        result = re.sub(
            r'\$\{([^}]+)\}',
            lambda m: "{" + m.group(1).replace("mork:", "").replace(":", "_") + "}",
            template,
        )
        result = re.sub(
            r'\{\$([^}]+)\}',
            lambda m: "{" + m.group(1) + "}",
            result,
        )
        if not result.startswith("http"):
            result = self.base_iri + result
        return result

    def _resolve_class_iri(self, spec: MappingSpec) -> Optional[URIRef]:
        """Resolve the OWL class IRI for a T-Box creation mapping."""
        if spec.concept_name:
            name = spec.concept_name
            if name.startswith("#"):
                return URIRef(self.base_iri + name[1:])
            return URIRef(self.base_iri + name)
        if spec.concept_name_template:
            # Templates with runtime values cannot be resolved statically
            return None
        return None

    def _resolve_target_class(self, spec: MappingSpec) -> Optional[URIRef]:
        """Resolve the target class for any mapping node."""
        if spec.exact_tbox_match:
            return spec.exact_tbox_match
        if spec.broad_tbox_category_match:
            return spec.broad_tbox_category_match
        if spec.deferred_mapping and spec.deferred_mapping in self.ctx.class_for:
            return self.ctx.class_for[spec.deferred_mapping]
        return None

    def _find_parent_triples_map(self, node: URIRef) -> Optional[URIRef]:
        """
        Find the parent triples map for a node by looking up its
        compositeBroaderMapping in the compilation context.
        """
        for parent in self.mork.objects(node, MORK.compositeBroaderMapping):
            if isinstance(parent, URIRef) and parent in self.ctx.triples_map_for:
                return self.ctx.triples_map_for[parent]
        return None

    def _add_join_condition(
        self, ref_obj_map: BNode, child_spec: MappingSpec, parent_node: URIRef
    ):
        """
        Add a join condition between child and parent triples maps.
        Implements Definition 10.11 (Join Key Derivation).
        """
        jc = BNode()
        self.rml.add((ref_obj_map, RR.joinCondition, jc))

        # Determine join keys
        # Strategy: use shared identity fields or data references
        child_key = child_spec.data_ref
        parent_spec = self.specs.get(parent_node)

        if child_key and parent_spec and parent_spec.data_ref:
            # Both have data references — look for a shared prefix
            parent_key = parent_spec.data_ref
            self.rml.add((jc, RR.child, Literal(child_key)))
            self.rml.add((jc, RR.parent, Literal(parent_key)))
        elif child_spec.identity_template_mapping:
            # Identity-based join
            id_spec = self.specs.get(child_spec.identity_template_mapping)
            if id_spec and id_spec.data_ref:
                self.rml.add((jc, RR.child, Literal(id_spec.data_ref)))
                self.rml.add((jc, RR.parent, Literal(id_spec.data_ref)))
            else:
                self.rml.add((jc, RR.child, Literal("id")))
                self.rml.add((jc, RR.parent, Literal("id")))
        else:
            # Default: assume a common 'id' field
            self.rml.add((jc, RR.child, Literal("id")))
            self.rml.add((jc, RR.parent, Literal("id")))

    def _is_object_property(self, prop: URIRef) -> bool:
        """
        Heuristic check whether a property is an object property
        (IRI-valued) vs a data property (literal-valued).
        """
        # Check in the MORK graph
        if (prop, RDF.type, OWL.ObjectProperty) in self.mork:
            return True
        if (prop, RDF.type, OWL.DatatypeProperty) in self.mork:
            return False

        # Check OwlAxiom wrappers
        for axiom in self.mork.subjects(OWL.sameAs, prop):
            if (axiom, RDF.type, MORK.OwlObjectProperty) in self.mork:
                return True
            if (axiom, RDF.type, MORK.OwlDataProperty) in self.mork:
                return False

        # Default: assume object property for URIRef ranges
        return False


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def _safe_local_name(uri: URIRef) -> str:
    """Extract a filesystem/IRI-safe local name from a URI."""
    s = str(uri)
    # Try fragment
    if "#" in s:
        local = s.split("#")[-1]
    elif "/" in s:
        local = s.split("/")[-1]
    else:
        local = s
    # Sanitise
    return re.sub(r"[^a-zA-Z0-9_-]", "_", local)


def pick_enum(inst_val, tmpl_val, unknown_val):
    """Pick the more specific of two enum values."""
    if inst_val != unknown_val:
        return inst_val
    return tmpl_val


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------


def compile_mork_to_rml(
    mork_turtle: str,
    base_iri: str = "http://example.org/",
    rml_base: str = "http://example.org/rml/",
    default_source: str = "input.json",
    output_format: str = "turtle",
) -> str:
    """
    Convenience function: compile a MORK Turtle string to an RML Turtle string.

    Args:
        mork_turtle: The MORK ontology + mapping instances as a Turtle string.
        base_iri: Base IRI for generated individuals.
        rml_base: Base IRI for generated RML nodes.
        default_source: Default logical source path.
        output_format: RDF serialization format for output.

    Returns:
        The compiled RML mapping document as a string.

    Example:
        >>> rml_output = compile_mork_to_rml(open("my_mappings.ttl").read())
        >>> print(rml_output)
    """
    g = Graph()
    g.parse(data=mork_turtle, format="turtle")

    compiler = MorkToRmlCompiler(
        mork_graph=g,
        base_iri=base_iri,
        rml_base=rml_base,
        default_source=default_source,
    )
    rml_graph = compiler.compile()
    return rml_graph.serialize(format=output_format)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="MORK-to-RML Compiler (Foundations §10)"
    )
    parser.add_argument(
        "input",
        help="Path to MORK Turtle file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="-",
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--base-iri",
        default="http://example.org/",
        help="Base IRI for generated individuals",
    )
    parser.add_argument(
        "--rml-base",
        default="http://example.org/rml/",
        help="Base IRI for RML mapping nodes",
    )
    parser.add_argument(
        "--source",
        default="input.json",
        help="Default logical source path",
    )
    parser.add_argument(
        "--format",
        default="turtle",
        choices=["turtle", "xml", "n3", "nt", "json-ld"],
        help="Output format",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    with open(args.input, "r") as f:
        mork_turtle = f.read()

    result = compile_mork_to_rml(
        mork_turtle=mork_turtle,
        base_iri=args.base_iri,
        rml_base=args.rml_base,
        default_source=args.source,
        output_format=args.format,
    )

    if args.output == "-":
        sys.stdout.write(result)
    else:
        with open(args.output, "w") as f:
            f.write(result)
        logger.info("RML output written to %s", args.output)
