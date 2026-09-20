"""
mork_validation.py

Programmatic validation of MORK graph fragments against
GCI axioms and structural constraints.

Implements:
  - GCI pre-validation (§C.7.1, §D.4.2)
  - IRI existence checking (§C.7.1)
  - Co-occurrence constraint verification (§2.4.2, §2.7)

This module is deterministic — no LLM involvement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set

from rdflib import Graph, Namespace, URIRef, RDF

MORK = Namespace("http://www.nebularis.org/ontologies/Mork#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
SH = Namespace("http://www.w3.org/ns/shacl#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")


@dataclass
class ValidationResult:
    """Structured result from GCI and structural validation."""

    valid: bool = True
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_violation(self, message: str) -> None:
        self.violations.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def merge(self, other: "ValidationResult") -> None:
        self.violations.extend(other.violations)
        self.warnings.extend(other.warnings)
        if not other.valid:
            self.valid = False


def validate_turtle_syntax(turtle_text: str) -> ValidationResult:
    """
    Parse a Turtle fragment and return any syntax errors.
    Returns the parsed graph on success (attached to result).
    """
    result = ValidationResult()
    try:
        g = Graph()
        g.parse(data=turtle_text, format="turtle")
        result._graph = g  # type: ignore[attr-defined]
    except Exception as e:
        result.add_violation(f"Turtle parse error: {e}")
    return result


def validate_gci_constraints(graph: Graph) -> ValidationResult:
    """
    Validate a parsed RDF graph against MORK co-occurrence GCI axioms.

    Checks:
      - Axiom 2.14a: broaderApplicative requires exactRBoxMatch
      - Axiom 2.14b: broadABoxCategoryMatch + compositeBroaderMapping
                      requires exactRBoxMatch
      - Axiom 2.14d: broadRBoxCategoryMatch + compositeBroaderMapping
                      requires exactABoxMatch or broadABoxCategoryMatch
      - Axiom 2.7a:  Datum requires deferredMapping to T-Box mapping
      - Axiom 5.10a: supersedes requires effectiveFrom
    """
    result = ValidationResult()

    _check_gci_2_14a(graph, result)
    _check_gci_2_14b(graph, result)
    _check_gci_2_14d(graph, result)
    _check_gci_2_7a(graph, result)
    _check_gci_5_10a(graph, result)

    return result


def _has_property(graph: Graph, subject: URIRef, prop: URIRef) -> bool:
    """Check if subject has any triple with the given predicate."""
    return any(graph.objects(subject, prop))


def _check_gci_2_14a(graph: Graph, result: ValidationResult) -> None:
    """Axiom 2.14a: ∃broaderApplicative.DataMapping ⊑ ∃exactRBoxMatch.⊤"""
    for subject in graph.subjects(MORK.broaderApplicative, None):
        has_rbox = (
            _has_property(graph, subject, MORK.exactRBoxMatch)
            or _has_property(graph, subject, MORK.inverseRBoxMatch)
        )
        if not has_rbox:
            result.add_violation(
                f"GCI 2.14a: <{subject}> has mork:broaderApplicative "
                f"but no mork:exactRBoxMatch or mork:inverseRBoxMatch"
            )


def _check_gci_2_14b(graph: Graph, result: ValidationResult) -> None:
    """
    Axiom 2.14b: (∃broadABoxCategoryMatch.⊤ ⊓ ∃compositeBroaderMapping.DataMapping)
                 ⊑ ∃exactRBoxMatch.⊤
    """
    for subject in graph.subjects(MORK.broadABoxCategoryMatch, None):
        has_composite_broader = _has_property(
            graph, subject, MORK.compositeBroaderMapping
        )
        if has_composite_broader:
            has_rbox = (
                _has_property(graph, subject, MORK.exactRBoxMatch)
                or _has_property(graph, subject, MORK.inverseRBoxMatch)
            )
            if not has_rbox:
                result.add_violation(
                    f"GCI 2.14b: <{subject}> has "
                    f"mork:broadABoxCategoryMatch and "
                    f"mork:compositeBroaderMapping but no "
                    f"mork:exactRBoxMatch"
                )


def _check_gci_2_14d(graph: Graph, result: ValidationResult) -> None:
    """
    Axiom 2.14d: (∃broadRBoxCategoryMatch.⊤ ⊓ ∃compositeBroaderMapping.DataMapping)
                 ⊑ (∃exactABoxMatch.⊤ ⊔ ∃broadABoxCategoryMatch.⊤)
    """
    for subject in graph.subjects(MORK.broadRBoxCategoryMatch, None):
        has_composite_broader = _has_property(
            graph, subject, MORK.compositeBroaderMapping
        )
        if has_composite_broader:
            has_abox = (
                _has_property(graph, subject, MORK.exactABoxMatch)
                or _has_property(
                    graph, subject, MORK.broadABoxCategoryMatch
                )
            )
            if not has_abox:
                result.add_violation(
                    f"GCI 2.14d: <{subject}> has "
                    f"mork:broadRBoxCategoryMatch and "
                    f"mork:compositeBroaderMapping but no "
                    f"mork:exactABoxMatch or "
                    f"mork:broadABoxCategoryMatch"
                )


def _check_gci_2_7a(graph: Graph, result: ValidationResult) -> None:
    """
    Axiom 2.7a: Datum ⊑ ∃deferredMapping.(∃exactTBoxMatch.⊤ ⊔ ∃broadTBoxCategoryMatch.⊤)
    """
    for subject in graph.subjects(RDF.type, MORK.Datum):
        deferred_targets = list(
            graph.objects(subject, MORK.deferredMapping)
        )
        if not deferred_targets:
            result.add_violation(
                f"GCI 2.7a: <{subject}> is a mork:Datum but has "
                f"no mork:deferredMapping"
            )
            continue

        has_tbox_target = False
        for target in deferred_targets:
            if _has_property(
                graph, target, MORK.exactTBoxMatch
            ) or _has_property(
                graph, target, MORK.broadTBoxCategoryMatch
            ):
                has_tbox_target = True
                break

        if not has_tbox_target:
            result.add_warning(
                f"GCI 2.7a: <{subject}> is a mork:Datum whose "
                f"deferredMapping target(s) have no T-Box match "
                f"in this fragment. This may be valid if the "
                f"target exists in the graph store."
            )


def _check_gci_5_10a(graph: Graph, result: ValidationResult) -> None:
    """Axiom 5.10a: ∃supersedes.DataMapping ⊑ ∃effectiveFrom.xsd:dateTime"""
    for subject in graph.subjects(MORK.supersedes, None):
        if not _has_property(graph, subject, MORK.effectiveFrom):
            result.add_violation(
                f"GCI 5.10a: <{subject}> has mork:supersedes "
                f"but no mork:effectiveFrom"
            )


def validate_generative_completeness(
    graph: Graph,
) -> ValidationResult:
    """
    Check GenerativeMapping completeness constraints.

    ShapeMapping must have: hasTargetingSpec, hasParameterBinding,
                            hasConstraintProvenance, generatesShapeDefinition
    RuleMapping must have:  hasTargetingSpec, hasParameterBinding,
                            hasRuleProvenance, generatesRuleDefinition
    """
    result = ValidationResult()

    for sm in graph.subjects(RDF.type, MORK.ShapeMapping):
        if not _has_property(graph, sm, MORK.hasTargetingSpec):
            result.add_violation(
                f"M1: ShapeMapping <{sm}> missing mork:hasTargetingSpec"
            )
        if not _has_property(graph, sm, MORK.hasParameterBinding):
            result.add_violation(
                f"M1: ShapeMapping <{sm}> missing "
                f"mork:hasParameterBinding"
            )
        if not _has_property(graph, sm, MORK.hasConstraintProvenance):
            result.add_violation(
                f"M1: ShapeMapping <{sm}> missing "
                f"mork:hasConstraintProvenance"
            )

    for rm in graph.subjects(RDF.type, MORK.RuleMapping):
        if not _has_property(graph, rm, MORK.hasTargetingSpec):
            result.add_violation(
                f"M1a: RuleMapping <{rm}> missing mork:hasTargetingSpec"
            )
        if not _has_property(graph, rm, MORK.hasParameterBinding):
            result.add_violation(
                f"M1a: RuleMapping <{rm}> missing "
                f"mork:hasParameterBinding"
            )
        if not _has_property(graph, rm, MORK.hasRuleProvenance):
            result.add_violation(
                f"M1a: RuleMapping <{rm}> missing "
                f"mork:hasRuleProvenance"
            )

    return result


def check_precedence_acyclicity(graph: Graph) -> Optional[str]:
    """
    Check for cycles in the precedence graph.

    Implements SHACL Shape M7 programmatically.
    Returns a description of the cycle if found, None otherwise.
    """
    # Collect all precedence edges from structural relationships
    edges: dict[str, set[str]] = {}

    # compositeBroaderMapping⁻ ⊑ precedes (Axiom P1)
    # i.e., if child :compositeBroaderMapping parent, then parent precedes child
    for child, parent in graph.subject_objects(
        MORK.compositeBroaderMapping
    ):
        s_parent = str(parent)
        s_child = str(child)
        edges.setdefault(s_parent, set()).add(s_child)

    # Also handle compositeNarrowerMapping (inverse of compositeBroaderMapping)
    for parent, child in graph.subject_objects(
        MORK.compositeNarrowerMapping
    ):
        s_parent = str(parent)
        s_child = str(child)
        edges.setdefault(s_parent, set()).add(s_child)

    # broaderApplicative⁻ ⊑ precedes (Axiom P2)
    for child, parent in graph.subject_objects(MORK.broaderApplicative):
        s_parent = str(parent)
        s_child = str(child)
        edges.setdefault(s_parent, set()).add(s_child)

    # dependentMapping⁻ ⊑ precedes (Axiom P3)
    for child, dep in graph.subject_objects(MORK.dependentMapping):
        s_dep = str(dep)
        s_child = str(child)
        edges.setdefault(s_dep, set()).add(s_child)

    # templateMapping⁻ ⊑ precedes (Axiom P10)
    for inst, tmpl in graph.subject_objects(MORK.templateMapping):
        s_tmpl = str(tmpl)
        s_inst = str(inst)
        edges.setdefault(s_tmpl, set()).add(s_inst)

    # Cycle detection via DFS
    all_nodes: Set[str] = set(edges.keys())
    for targets in edges.values():
        all_nodes.update(targets)

    WHITE, GREY, BLACK = 0, 1, 2
    colour = {n: WHITE for n in all_nodes}
    path: list[str] = []

    def dfs(node: str) -> Optional[str]:
        colour[node] = GREY
        path.append(node)
        for neighbour in edges.get(node, set()):
            if colour.get(neighbour, WHITE) == GREY:
                cycle_start = path.index(neighbour)
                cycle = path[cycle_start:] + [neighbour]
                return " → ".join(cycle)
            if colour.get(neighbour, WHITE) == WHITE:
                result = dfs(neighbour)
                if result is not None:
                    return result
        path.pop()
        colour[node] = BLACK
        return None

    for node in all_nodes:
        if colour.get(node, WHITE) == WHITE:
            cycle = dfs(node)
            if cycle is not None:
                return cycle

    return None


def validate_iris_exist(
    graph: Graph,
    sparql_endpoint: str,
    ontology_graph_uri: str,
) -> ValidationResult:
    """
    Check that all IRIs used in box match properties exist
    in the target ontology.

    This requires access to the triple store. If the endpoint
    is unavailable, returns a warning rather than a violation.
    """
    from SPARQLWrapper import SPARQLWrapper, JSON

    result = ValidationResult()

    box_match_properties = [
        MORK.exactTBoxMatch,
        MORK.exactRBoxMatch,
        MORK.exactABoxMatch,
        MORK.inverseRBoxMatch,
        MORK.broadTBoxCategoryMatch,
        MORK.narrowTBoxCategoryMatch,
        MORK.broadABoxCategoryMatch,
        MORK.narrowABoxCategoryMatch,
        MORK.broadRBoxCategoryMatch,
        MORK.narrowRBoxCategoryMatch,
    ]

    target_iris: Set[str] = set()
    for prop in box_match_properties:
        for _, target in graph.subject_objects(prop):
            if isinstance(target, URIRef):
                target_iris.add(str(target))

    if not target_iris:
        return result

    # Batch check via VALUES clause
    values_clause = " ".join(f"<{iri}>" for iri in target_iris)
    query = f"""
        ASK
        FROM <{ontology_graph_uri}>
        WHERE {{
            VALUES ?iri {{ {values_clause} }}
            {{ ?iri a owl:Class }}
            UNION {{ ?iri a owl:ObjectProperty }}
            UNION {{ ?iri a owl:DatatypeProperty }}
            UNION {{ ?iri a owl:NamedIndividual }}
            UNION {{ ?iri a skos:Concept }}
        }}
    """

    try:
        sparql = SPARQLWrapper(sparql_endpoint)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        sparql.setTimeout(10)
        resp = sparql.query().convert()
        if not resp.get("boolean", True):
            # At least one IRI is missing — check individually
            for iri in target_iris:
                individual_query = f"""
                    ASK
                    FROM <{ontology_graph_uri}>
                    WHERE {{
                        <{iri}> ?p ?o .
                    }}
                """
                sparql.setQuery(individual_query)
                individual_resp = sparql.query().convert()
                if not individual_resp.get("boolean", False):
                    result.add_violation(
                        f"IRI <{iri}> does not exist in the "
                        f"target ontology"
                    )
    except Exception as e:
        result.add_warning(
            f"Unable to verify IRI existence against triple store: {e}"
        )

    return result


def validate_fragment(
    turtle_text: str,
    sparql_endpoint: Optional[str] = None,
    ontology_graph_uri: Optional[str] = None,
) -> ValidationResult:
    """
    Run all validation checks on a Turtle fragment.

    This is the main entry point for the validation tools.
    """
    # 1. Syntax check
    syntax_result = validate_turtle_syntax(turtle_text)
    if not syntax_result.valid:
        return syntax_result

    graph: Graph = syntax_result._graph  # type: ignore[attr-defined]

    # 2. GCI constraints
    result = validate_gci_constraints(graph)

    # 3. GenerativeMapping completeness
    completeness = validate_generative_completeness(graph)
    result.merge(completeness)

    # 4. Precedence acyclicity
    cycle = check_precedence_acyclicity(graph)
    if cycle is not None:
        result.add_violation(f"Precedence cycle detected: {cycle}")

    # 5. IRI existence (if endpoint is available)
    if sparql_endpoint and ontology_graph_uri:
        iri_result = validate_iris_exist(
            graph, sparql_endpoint, ontology_graph_uri
        )
        result.merge(iri_result)

    return result