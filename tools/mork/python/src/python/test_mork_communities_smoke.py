#!/usr/bin/env python3
"""
Strict smoke tests for the migrated mork_communities package.

What this script does:
1. Runs functional checks for core algorithm modules.
2. Exercises pipeline-level module imports.
3. Reports missing optional and required dependencies clearly.

Run from tools/mork/python/src/python:
  python3 test_mork_communities_smoke.py
"""

from __future__ import annotations

import importlib
import importlib.util
import traceback
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD


OPTIONAL_DEPENDENCIES = {
    "leidenalg": "Community detection acceleration. Falls back to networkx Louvain if absent",
    "igraph": "Used by leidenalg-backed clustering",
    "SPARQLWrapper": "Needed for validate_iris_exist against remote SPARQL endpoints",
}

REQUIRED_DEPENDENCIES = {
    "rdflib": "RDF graph APIs used throughout MORK",
    "numpy": "Used by community discovery module",
    "networkx": "Fallback graph algorithms",
    "pydantic": "Schemas for pipeline structured IO",
    "langchain_core": "Pipeline/agent message and tool interfaces",
    "langgraph": "Pipeline state graph orchestration",
}

PIPELINE_LEVEL_MODULES = [
    "mork_communities.pipeline",
    "mork_agents",
    "mork_tools",
    "mork_poc",
]


@dataclass
class DependencyReport:
    missing_required: List[str]
    missing_optional: List[str]
    available_required: List[str]
    available_optional: List[str]


def _module_exists(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def check_dependencies() -> DependencyReport:
    missing_required = [m for m in REQUIRED_DEPENDENCIES if not _module_exists(m)]
    missing_optional = [m for m in OPTIONAL_DEPENDENCIES if not _module_exists(m)]
    available_required = [m for m in REQUIRED_DEPENDENCIES if m not in missing_required]
    available_optional = [m for m in OPTIONAL_DEPENDENCIES if m not in missing_optional]
    return DependencyReport(
        missing_required=missing_required,
        missing_optional=missing_optional,
        available_required=available_required,
        available_optional=available_optional,
    )


def print_dependency_report(report: DependencyReport) -> None:
    print("\nDependency report")
    print("-----------------")

    print(f"Required available: {len(report.available_required)}/{len(REQUIRED_DEPENDENCIES)}")
    for mod in report.available_required:
        print(f"  OK  {mod}")

    if report.missing_required:
        print("Required missing:")
        for mod in report.missing_required:
            print(f"  MISSING {mod}  -> {REQUIRED_DEPENDENCIES[mod]}")

    print(f"Optional available: {len(report.available_optional)}/{len(OPTIONAL_DEPENDENCIES)}")
    for mod in report.available_optional:
        print(f"  OK  {mod}")

    if report.missing_optional:
        print("Optional missing:")
        for mod in report.missing_optional:
            print(f"  MISSING {mod}  -> {OPTIONAL_DEPENDENCIES[mod]}")


def _import_module(module_name: str):
    return importlib.import_module(module_name)


def test_recognition_engine() -> None:
    recognition = _import_module("mork_communities.recognition")
    namespaces = _import_module("mork_communities.namespaces")

    RecognitionEngine = recognition.RecognitionEngine
    DATA_CONCEPT = namespaces.DATA_CONCEPT
    CONCEPT_NAME = namespaces.CONCEPT_NAME

    g = Graph()
    concept_limit = URIRef("http://example.org/concept/Limit")
    g.add((concept_limit, RDF.type, DATA_CONCEPT))
    g.add((concept_limit, SKOS.prefLabel, Literal("limit")))
    g.add((concept_limit, CONCEPT_NAME, Literal("Limit")))

    engine = RecognitionEngine(g, min_score=0.0, max_candidates=5)
    results = engine.recognise("lmt")

    assert results, "Recognition returned no candidates"
    assert any(r.concept_iri == concept_limit for r in results), "Expected concept not recognised"


def test_type_compatibility_engine() -> None:
    type_compatibility = _import_module("mork_communities.type_compatibility")
    TypeCompatibilityEngine = type_compatibility.TypeCompatibilityEngine

    MORK = _import_module("mork_communities.namespaces").MORK

    g = Graph()

    prop = URIRef("http://example.org/hasAmount")
    prop_shadow = URIRef("http://example.org/shadow/hasAmount")
    range_shadow = URIRef("http://example.org/shadow/decimal")

    g.add((prop_shadow, RDF.type, MORK.OwlDataProperty))
    g.add((prop_shadow, MORK.iri, Literal(str(prop), datatype=XSD.string)))
    g.add((prop_shadow, MORK.shadowRange, range_shadow))
    g.add((range_shadow, MORK.iri, Literal(str(XSD.decimal), datatype=XSD.string)))

    engine = TypeCompatibilityEngine(g)
    engine.build_type_profiles()

    ok_distance = engine.compute_type_distance("decimal", prop)
    bad_distance = engine.compute_type_distance("date", prop)

    assert ok_distance == 0.0, f"Expected exact type distance 0.0, got {ok_distance}"
    assert bad_distance == float("inf"), f"Expected incompatible type distance inf, got {bad_distance}"


def test_axiom_profiler_and_alignment() -> None:
    axiom_intent = _import_module("mork_communities.axiom_intent")
    AxiomIntentProfiler = axiom_intent.AxiomIntentProfiler
    AxiomAlignmentScorer = axiom_intent.AxiomAlignmentScorer

    onto = Graph()

    layer = URIRef("http://example.org/Layer")
    has_limit = URIRef("http://example.org/hasLimit")

    onto.add((layer, RDF.type, OWL.Class))
    onto.add((has_limit, RDF.type, OWL.DatatypeProperty))
    onto.add((has_limit, RDFS.domain, layer))

    restriction = BNode()
    onto.add((restriction, RDF.type, OWL.Restriction))
    onto.add((restriction, OWL.onProperty, has_limit))
    onto.add((restriction, OWL.someValuesFrom, XSD.decimal))
    onto.add((layer, RDFS.subClassOf, restriction))

    profiler = AxiomIntentProfiler(onto)
    profiler.extract_all_profiles()

    scorer = AxiomAlignmentScorer(profiler, onto)
    score, feasible, explanation = scorer.score_alignment(
        concept_iri=URIRef("http://example.org/concept/Limit"),
        target_property_iri=has_limit,
        target_class_iri=layer,
    )

    assert feasible, f"Expected feasible alignment, got infeasible: {explanation}"
    assert score > 0.0, f"Expected positive alignment score, got {score}"


def test_precedence_topological_sort() -> None:
    precedence_module = _import_module("mork_communities.precedence")
    namespaces = _import_module("mork_communities.namespaces")

    PrecedenceDeriver = precedence_module.PrecedenceDeriver
    COMPOSITE_BROADER_MAPPING = namespaces.COMPOSITE_BROADER_MAPPING

    g = Graph()

    parent = URIRef("http://example.org/mapping/parent")
    child = URIRef("http://example.org/mapping/child")

    g.add((child, COMPOSITE_BROADER_MAPPING, parent))

    deriver = PrecedenceDeriver(g)
    mapping_set = {parent, child}
    precedence = deriver.derive_precedence(mapping_set)
    order = deriver.topological_sort(mapping_set, precedence)

    assert order.index(parent) < order.index(child), "Expected parent to precede child"


def test_confidence_propagation() -> None:
    confidence_module = _import_module("mork_communities.confidence")
    namespaces = _import_module("mork_communities.namespaces")

    ConfidencePropagator = confidence_module.ConfidencePropagator
    COMPOSITE_NARROWER_MAPPING = namespaces.COMPOSITE_NARROWER_MAPPING
    WEIGHTING = namespaces.WEIGHTING

    g = Graph()

    root = URIRef("http://example.org/mapping/root")
    child = URIRef("http://example.org/mapping/child")

    g.add((root, WEIGHTING, Literal(80)))
    g.add((child, WEIGHTING, Literal(50)))
    g.add((root, COMPOSITE_NARROWER_MAPPING, child))

    cp = ConfidencePropagator(g)
    confidence = cp.compute_confidence(root)

    expected = 0.8 * 0.5
    assert abs(confidence - expected) < 1e-9, f"Expected {expected}, got {confidence}"


def test_full_bayesian_aggregator() -> None:
    aggregator_module = _import_module("mork_communities.aggregator")
    FullBayesianAggregator = aggregator_module.FullBayesianAggregator
    FullEvidenceBundle = aggregator_module.FullEvidenceBundle

    agg = FullBayesianAggregator()

    evidence = FullEvidenceBundle(
        name_match_score=0.9,
        embedding_score=0.8,
        type_compatibility=1.0,
        distortion_score=0.2,
        structural_score=0.1,
        prior_frequency=0.2,
        community_boost=0.4,
        projection_confidence=0.85,
    )

    result = agg.score_candidate(
        concept_iri=URIRef("http://example.org/concept/Limit"),
        evidence=evidence,
        target_property=URIRef("http://example.org/hasLimit"),
        target_class=URIRef("http://example.org/Layer"),
    )

    assert result.is_feasible, "Expected feasible candidate"
    assert len(result.signals) >= 5, "Expected multiple evidence signals to be recorded"


def test_dag_instantiator_constructs() -> None:
    dag_module = _import_module("mork_communities.dag_instantiation")
    DAGTemplateInstantiator = dag_module.DAGTemplateInstantiator
    _ = DAGTemplateInstantiator(min_template_frequency=2, min_coverage=0.7)


def test_pipeline_level_imports() -> None:
    failures: Dict[str, str] = {}
    for mod in PIPELINE_LEVEL_MODULES:
        try:
            _import_module(mod)
        except Exception as exc:
            failures[mod] = f"{type(exc).__name__}: {exc}"

    if failures:
        details = " | ".join(f"{m} -> {e}" for m, e in failures.items())
        raise AssertionError(f"Pipeline-level import failures: {details}")


TESTS: List[Tuple[str, Callable[[], None]]] = [
    ("recognition engine", test_recognition_engine),
    ("type compatibility", test_type_compatibility_engine),
    ("axiom profiler and alignment", test_axiom_profiler_and_alignment),
    ("precedence sort", test_precedence_topological_sort),
    ("confidence propagation", test_confidence_propagation),
    ("full bayesian aggregator", test_full_bayesian_aggregator),
    ("dag instantiator construct", test_dag_instantiator_constructs),
    ("pipeline-level imports", test_pipeline_level_imports),
]


def main() -> int:
    failures: List[str] = []

    print("Running strict MORK communities smoke tests")

    dep_report = check_dependencies()
    print_dependency_report(dep_report)

    if dep_report.missing_required:
        print("\nSummary: FAIL")
        print("Required dependencies are missing. Install them before rerunning.")
        return 2

    for name, test_fn in TESTS:
        try:
            test_fn()
            print(f"PASS: {name}")
        except Exception as exc:
            failures.append(name)
            print(f"FAIL: {name}")
            print(f"  {exc}")
            traceback.print_exc()

    if failures:
        print("\nSummary: FAIL")
        print(f"Failed tests: {', '.join(failures)}")
        if dep_report.missing_optional:
            print("Optional dependencies are still missing. Core tests can pass without them.")
        return 1

    if dep_report.missing_optional:
        print("\nSummary: PASS WITH OPTIONAL MISSING")
        print(f"Missing optional deps: {', '.join(dep_report.missing_optional)}")
        return 0

    print("\nSummary: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
