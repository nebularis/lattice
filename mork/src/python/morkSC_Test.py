"""
Test suite for the MORK Compiler-Agent.

Tests cover:
  - Precedence DAG construction and topological sort
  - Parameter binding resolution
  - SHACL shape compilation from ShapeMapping
  - SWRL rule compilation from RuleMapping
  - SPARQL template compilation from QueryTemplate
  - Existing shape/rule passthrough
  - Error handling (cycles, missing bindings, deprecated mappings)
  - Idempotence (compiling twice yields identical output)
  - Determinism (IRI generation is stable)
"""

import unittest
from rdflib import Graph, URIRef, Literal, BNode, Namespace
from rdflib.collection import Collection as RDFCollection
from rdflib.namespace import RDF, RDFS, OWL, XSD

# Import the compiler
from mork_compiler import (
    MORK, SH, SWRL, SWRLB, DCT, SKOS,
    MorkCompiler,
    PrecedenceDAG,
    PrecedenceCycleError,
    ParameterResolver,
    TargetingSpecResolver,
    compile_mork_graph,
    ParamType,
    TargetMode,
)


def _make_base_graph() -> Graph:
    """Create a minimal MORK graph with namespace bindings."""
    g = Graph()
    g.bind("mork", MORK)
    g.bind("sh", SH)
    g.bind("swrl", SWRL)
    g.bind("swrlb", SWRLB)
    g.bind("skos", SKOS)
    g.bind("dct", DCT)
    g.bind("owl", OWL)
    g.bind("xsd", XSD)
    return g


# Test namespace for examples
EX = Namespace("http://example.org/test/")
ONT = Namespace("http://example.org/ontology/")
GEN = Namespace("http://www.nebularis.org/generated/")


class TestPrecedenceDAG(unittest.TestCase):
    """Test precedence DAG construction and topological sort."""

    def test_simple_composition(self):
        """P1: Parent precedes composite children."""
        g = _make_base_graph()
        g.add((EX.Parent, RDF.type, MORK.DataMapping))
        g.add((EX.Child, RDF.type, MORK.DataMapping))
        g.add((EX.Parent, MORK.compositeNarrowerMapping, EX.Child))

        dag = PrecedenceDAG(g)
        order = dag.topological_sort()
        self.assertLess(order.index(EX.Parent), order.index(EX.Child))

    def test_applicative_precedence(self):
        """P2: Applicative parent precedes child."""
        g = _make_base_graph()
        g.add((EX.Parent, RDF.type, MORK.DataMapping))
        g.add((EX.Child, RDF.type, MORK.ShapeMapping))
        g.add((EX.Child, MORK.broaderApplicative, EX.Parent))

        dag = PrecedenceDAG(g)
        order = dag.topological_sort()
        self.assertLess(order.index(EX.Parent), order.index(EX.Child))

    def test_tbox_before_abox(self):
        """P6/P7: T-Box mapping precedes Datum."""
        g = _make_base_graph()
        g.add((EX.TBoxMap, RDF.type, MORK.DataMapping))
        g.add((EX.TBoxMap, MORK.exactTBoxMatch, ONT.SomeClass))
        g.add((EX.DatumMap, RDF.type, MORK.Datum))
        g.add((EX.DatumMap, RDF.type, MORK.DataMapping))
        g.add((EX.DatumMap, MORK.deferredMapping, EX.TBoxMap))

        dag = PrecedenceDAG(g)
        order = dag.topological_sort()
        self.assertLess(order.index(EX.TBoxMap), order.index(EX.DatumMap))

    def test_cycle_detection(self):
        """Cycles raise PrecedenceCycleError."""
        g = _make_base_graph()
        g.add((EX.A, RDF.type, MORK.DataMapping))
        g.add((EX.B, RDF.type, MORK.DataMapping))
        g.add((EX.A, MORK.compositeNarrowerMapping, EX.B))
        g.add((EX.B, MORK.compositeNarrowerMapping, EX.A))

        dag = PrecedenceDAG(g)
        with self.assertRaises(PrecedenceCycleError):
            dag.topological_sort()

    def test_deterministic_ordering(self):
        """Same graph produces same order (Theorem 4.4)."""
        g = _make_base_graph()
        for name in ["C", "A", "B", "D"]:
            node = EX[name]
            g.add((node, RDF.type, MORK.DataMapping))

        g.add((EX.A, MORK.compositeNarrowerMapping, EX.B))
        g.add((EX.A, MORK.compositeNarrowerMapping, EX.C))
        g.add((EX.C, MORK.compositeNarrowerMapping, EX.D))

        order1 = PrecedenceDAG(g).topological_sort()
        order2 = PrecedenceDAG(g).topological_sort()
        self.assertEqual(order1, order2)


class TestParameterResolver(unittest.TestCase):
    """Test parameter binding resolution."""

    def test_numeric_binding(self):
        g = _make_base_graph()
        g.add((EX.Map, RDF.type, MORK.ShapeMapping))

        pb = BNode()
        g.add((EX.Map, MORK.hasParameterBinding, pb))
        g.add((pb, MORK.paramName, Literal("minInclusive")))
        g.add((pb, MORK.paramType, Literal("Numeric")))
        g.add((pb, MORK.paramValue, Literal(10000000, datatype=XSD.decimal)))

        resolver = ParameterResolver(g)
        bindings = resolver.resolve(EX.Map)

        self.assertEqual(len(bindings), 1)
        self.assertEqual(bindings[0].name, "minInclusive")
        self.assertEqual(bindings[0].param_type, ParamType.NUMERIC)
        self.assertAlmostEqual(bindings[0].value, 10000000.0)

    def test_concept_binding(self):
        g = _make_base_graph()
        g.add((EX.Map, RDF.type, MORK.ShapeMapping))

        pb = BNode()
        g.add((EX.Map, MORK.hasParameterBinding, pb))
        g.add((pb, MORK.paramName, Literal("inSet")))
        g.add((pb, MORK.paramType, Literal("Concept")))
        g.add((pb, MORK.paramValue, ONT.FirstParty))

        resolver = ParameterResolver(g)
        bindings = resolver.resolve(EX.Map)

        self.assertEqual(len(bindings), 1)
        self.assertEqual(bindings[0].value, ONT.FirstParty)

    def test_path_binding_as_list(self):
        g = _make_base_graph()
        g.add((EX.Map, RDF.type, MORK.ShapeMapping))

        pb = BNode()
        g.add((EX.Map, MORK.hasParameterBinding, pb))
        g.add((pb, MORK.paramName, Literal("path")))
        g.add((pb, MORK.paramType, Literal("Path")))

        # Build RDF list for path
        path_list = BNode()
        coll = RDFCollection(g, path_list)
        coll.append(ONT.hasLimit)
        coll.append(ONT.hasExtent)
        coll.append(ONT.hasNumericValue)
        g.add((pb, MORK.paramValue, path_list))

        resolver = ParameterResolver(g)
        bindings = resolver.resolve(EX.Map)

        self.assertEqual(len(bindings), 1)
        self.assertEqual(bindings[0].param_type, ParamType.PATH)
        self.assertEqual(
            bindings[0].value,
            [ONT.hasLimit, ONT.hasExtent, ONT.hasNumericValue],
        )


class TestSHACLCompilation(unittest.TestCase):
    """Test SHACL shape compilation from ShapeMapping."""

    def _make_revenue_band_mapping(self) -> Graph:
        """Create the revenue band ShapeMapping from the whitepaper example."""
        g = _make_base_graph()

        # Target ontology class
        g.add((ONT.InsuredParty, RDF.type, OWL.Class))
        g.add((ONT.providesFinancialDetails, RDF.type, OWL.ObjectProperty))
        g.add((ONT.hasMetricValue, RDF.type, OWL.DatatypeProperty))

        # ShapeMapping
        g.add((EX.Map_RevenueBand, RDF.type, MORK.ShapeMapping))
        g.add((EX.Map_RevenueBand, RDF.type, MORK.DataMapping))
        g.add((EX.Map_RevenueBand, MORK.mappingScheme, EX.TestScheme))
        g.add((EX.TestScheme, RDF.type, MORK.MappingScheme))

        # TargetingSpec
        ts = BNode()
        g.add((EX.Map_RevenueBand, MORK.hasTargetingSpec, ts))
        g.add((ts, SH.targetClass, ONT.InsuredParty))

        # Parameter bindings
        pb_path = BNode()
        g.add((EX.Map_RevenueBand, MORK.hasParameterBinding, pb_path))
        g.add((pb_path, MORK.paramName, Literal("path")))
        g.add((pb_path, MORK.paramType, Literal("Path")))

        path_list = BNode()
        coll = RDFCollection(g, path_list)
        coll.append(ONT.providesFinancialDetails)
        coll.append(ONT.hasMetricValue)
        g.add((pb_path, MORK.paramValue, path_list))

        pb_min = BNode()
        g.add((EX.Map_RevenueBand, MORK.hasParameterBinding, pb_min))
        g.add((pb_min, MORK.paramName, Literal("minInclusive")))
        g.add((pb_min, MORK.paramType, Literal("Numeric")))
        g.add((pb_min, MORK.paramValue, Literal(10000000, datatype=XSD.decimal)))

        pb_max = BNode()
        g.add((EX.Map_RevenueBand, MORK.hasParameterBinding, pb_max))
        g.add((pb_max, MORK.paramName, Literal("maxInclusive")))
        g.add((pb_max, MORK.paramType, Literal("Numeric")))
        g.add((pb_max, MORK.paramValue, Literal(100000000, datatype=XSD.decimal)))

        pb_msg = BNode()
        g.add((EX.Map_RevenueBand, MORK.hasParameterBinding, pb_msg))
        g.add((pb_msg, MORK.paramName, Literal("message")))
        g.add((pb_msg, MORK.paramType, Literal("String")))
        g.add((pb_msg, MORK.paramValue, Literal("Revenue must be between $10M and $100M")))

        # Provenance
        prov = BNode()
        g.add((EX.Map_RevenueBand, MORK.hasConstraintProvenance, prov))
        g.add((prov, DCT.creator, Literal("Product Builder")))
        g.add((prov, DCT.created, Literal("2026-01-20", datatype=XSD.date)))
        g.add((prov, MORK.llmModelId, Literal("pb-llm-2026.01")))
        g.add((prov, MORK.llmConfidence, Literal(0.91, datatype=XSD.decimal)))
        g.add((prov, MORK.reviewStatus, Literal("APPROVED")))

        return g

    def test_revenue_band_compiles(self):
        """The revenue band example produces a valid SHACL shape."""
        g = self._make_revenue_band_mapping()
        compiler = MorkCompiler(g, str(GEN), validate_output=False)
        report = compiler.compile()

        self.assertTrue(report.is_valid, f"Errors: {report.errors}")
        self.assertEqual(len(report.results), 1)

        result = report.results[0]
        self.assertEqual(result.artefact_type, "SHACL")

        # Check the generated graph
        ag = result.artefact_graph
        shapes = list(ag.subjects(RDF.type, SH.NodeShape))
        self.assertEqual(len(shapes), 1, "Expected one NodeShape")

        shape = shapes[0]

        # Check targeting
        tc = list(ag.objects(shape, SH.targetClass))
        self.assertEqual(tc, [ONT.InsuredParty])

        # Check property constraints exist
        props = list(ag.objects(shape, SH.property))
        self.assertGreaterEqual(len(props), 1)

    def test_idempotence(self):
        """Compiling the same mapping twice yields identical IRIs (Theorem 4.3)."""
        g = self._make_revenue_band_mapping()

        r1 = MorkCompiler(g, str(GEN), validate_output=False).compile()
        r2 = MorkCompiler(g, str(GEN), validate_output=False).compile()

        self.assertEqual(
            r1.results[0].artefact_root,
            r2.results[0].artefact_root,
        )

    def test_deprecated_mapping_skipped(self):
        """A DEPRECATED ShapeMapping produces no artefact."""
        g = self._make_revenue_band_mapping()

        # Change provenance to DEPRECATED
        for prov in g.objects(EX.Map_RevenueBand, MORK.hasConstraintProvenance):
            g.set((prov, MORK.reviewStatus, Literal("DEPRECATED")))

        compiler = MorkCompiler(g, str(GEN), validate_output=False)
        report = compiler.compile()

        self.assertEqual(len(report.results), 1)
        result = report.results[0]
        self.assertIn("DEPRECATED", result.warnings[0])

    def test_missing_targeting_spec_errors(self):
        """ShapeMapping without TargetingSpec produces an error."""
        g = _make_base_graph()
        g.add((EX.BadMap, RDF.type, MORK.ShapeMapping))

        pb = BNode()
        g.add((EX.BadMap, MORK.hasParameterBinding, pb))
        g.add((pb, MORK.paramName, Literal("x")))
        g.add((pb, MORK.paramType, Literal("String")))
        g.add((pb, MORK.paramValue, Literal("y")))

        compiler = MorkCompiler(g, str(GEN), validate_output=False)
        report = compiler.compile()

        self.assertFalse(report.is_valid)
        self.assertTrue(
            any("TargetingSpec" in e for _, e in report.errors)
        )


class TestSWRLCompilation(unittest.TestCase):
    """Test SWRL rule compilation from RuleMapping."""

    def _make_waiting_period_rule(self) -> Graph:
        """Create the BI waiting period rule from the whitepaper."""
        g = _make_base_graph()

        # Target ontology
        g.add((ONT.Clause, RDF.type, OWL.Class))
        g.add((ONT.hasPeril, RDF.type, OWL.ObjectProperty))
        g.add((ONT.hasWaitingPeriod, RDF.type, OWL.DatatypeProperty))
        g.add((ONT.requiresReferralApproval, RDF.type, OWL.DatatypeProperty))
        g.add((ONT.BusinessInterruption, RDF.type, OWL.NamedIndividual))

        # RuleMapping with existing generatesRuleDefinition
        g.add((EX.RM_WaitingPeriod, RDF.type, MORK.RuleMapping))
        g.add((EX.RM_WaitingPeriod, RDF.type, MORK.DataMapping))
        g.add((EX.RM_WaitingPeriod, MORK.mappingScheme, EX.TestScheme))
        g.add((EX.TestScheme, RDF.type, MORK.MappingScheme))

        # TargetingSpec
        ts = BNode()
        g.add((EX.RM_WaitingPeriod, MORK.hasTargetingSpec, ts))
        g.add((ts, SH.targetClass, ONT.Clause))

        # Parameter binding
        pb = BNode()
        g.add((EX.RM_WaitingPeriod, MORK.hasParameterBinding, pb))
        g.add((pb, MORK.paramName, Literal("thresholdHours")))
        g.add((pb, MORK.paramType, Literal("Numeric")))
        g.add((pb, MORK.paramValue, Literal(72, datatype=XSD.integer)))

        # Inline swrl:Imp definition
        rule = BNode()
        g.add((EX.RM_WaitingPeriod, MORK.generatesRuleDefinition, rule))
        g.add((rule, RDF.type, SWRL.Imp))

        # Body atoms
        body_atom1 = BNode()
        g.add((body_atom1, RDF.type, SWRL.ClassAtom))
        g.add((body_atom1, SWRL.classPredicate, ONT.Clause))
        g.add((body_atom1, SWRL.argument1, EX.var_c))

        body_atom2 = BNode()
        g.add((body_atom2, RDF.type, SWRL.IndividualPropertyAtom))
        g.add((body_atom2, SWRL.propertyPredicate, ONT.hasPeril))
        g.add((body_atom2, SWRL.argument1, EX.var_c))
        g.add((body_atom2, SWRL.argument2, ONT.BusinessInterruption))

        body_atom3 = BNode()
        g.add((body_atom3, RDF.type, SWRL.DatavaluedPropertyAtom))
        g.add((body_atom3, SWRL.propertyPredicate, ONT.hasWaitingPeriod))
        g.add((body_atom3, SWRL.argument1, EX.var_c))
        g.add((body_atom3, SWRL.argument2, EX.var_wp))

        body_atom4 = BNode()
        g.add((body_atom4, RDF.type, SWRL.BuiltinAtom))
        g.add((body_atom4, SWRL.builtin, SWRLB.greaterThan))
        args = BNode()
        args_coll = RDFCollection(g, args)
        args_coll.append(EX.var_wp)
        args_coll.append(Literal("PT72H", datatype=XSD.duration))
        g.add((body_atom4, SWRL.arguments, args))

        body_list = BNode()
        body_coll = RDFCollection(g, body_list)
        body_coll.append(body_atom1)
        body_coll.append(body_atom2)
        body_coll.append(body_atom3)
        body_coll.append(body_atom4)
        g.add((rule, SWRL.body, body_list))

        # Head atom
        head_atom = BNode()
        g.add((head_atom, RDF.type, SWRL.DatavaluedPropertyAtom))
        g.add((head_atom, SWRL.propertyPredicate, ONT.requiresReferralApproval))
        g.add((head_atom, SWRL.argument1, EX.var_c))
        g.add((head_atom, SWRL.argument2, Literal(True)))

        head_list = BNode()
        head_coll = RDFCollection(g, head_list)
        head_coll.append(head_atom)
        g.add((rule, SWRL.head, head_list))

        # Provenance
        prov = BNode()
        g.add((EX.RM_WaitingPeriod, MORK.hasRuleProvenance, prov))
        g.add((prov, DCT.creator, Literal("Product Builder")))
        g.add((prov, MORK.reviewStatus, Literal("APPROVED")))

        return g

    def test_existing_rule_passthrough(self):
        """RuleMapping with existing generatesRuleDefinition is copied."""
        g = self._make_waiting_period_rule()
        compiler = MorkCompiler(g, str(GEN), validate_output=False)
        report = compiler.compile()

        self.assertTrue(report.is_valid, f"Errors: {report.errors}")
        self.assertEqual(len(report.results), 1)

        result = report.results[0]
        self.assertEqual(result.artefact_type, "SWRL")

        ag = result.artefact_graph
        rules = list(ag.subjects(RDF.type, SWRL.Imp))
        self.assertEqual(len(rules), 1)

        # Verify body and head exist
        rule = rules[0]
        body = list(ag.objects(rule, SWRL.body))
        head = list(ag.objects(rule, SWRL.head))
        self.assertEqual(len(body), 1)
        self.assertEqual(len(head), 1)


class TestSPARQLCompilation(unittest.TestCase):
    """Test SPARQL template compilation."""

    def test_simple_query_template(self):
        g = _make_base_graph()

        g.add((EX.QT_Revenue, RDF.type, MORK.QueryTemplate))
        g.add((EX.QT_Revenue, MORK.queryLanguage, Literal("SPARQL")))
        g.add((EX.QT_Revenue, MORK.queryText, Literal(
            "SELECT ?ip WHERE { ?ip a ${targetClass} . "
            "?ip :revenue ?rev . FILTER(?rev >= ${minRev}) }"
        )))

        pb1 = BNode()
        g.add((EX.QT_Revenue, MORK.paramBinding, pb1))
        g.add((pb1, MORK.paramName, Literal("targetClass")))
        g.add((pb1, MORK.paramValue, Literal("ont:InsuredParty")))

        pb2 = BNode()
        g.add((EX.QT_Revenue, MORK.paramBinding, pb2))
        g.add((pb2, MORK.paramName, Literal("minRev")))
        g.add((pb2, MORK.paramValue, Literal("10000000")))

        compiler = MorkCompiler(g, str(GEN), validate_output=False)
        report = compiler.compile()

        self.assertTrue(report.is_valid)
        result = report.results[0]
        self.assertEqual(result.artefact_type, "SPARQL")

        # Check parameter substitution occurred
        ag = result.artefact_graph
        compiled = list(ag.objects(EX.QT_Revenue, MORK.compiledQueryText))
        self.assertEqual(len(compiled), 1)
        text = str(compiled[0])
        self.assertIn("ont:InsuredParty", text)
        self.assertIn("10000000", text)
        self.assertNotIn("${", text)


class TestEndToEnd(unittest.TestCase):
    """End-to-end compilation tests with multiple mapping types."""

    def test_mixed_scheme(self):
        """Compile a scheme with ShapeMappings and QueryTemplates."""
        g = _make_base_graph()

        g.add((ONT.Clause, RDF.type, OWL.Class))
        g.add((ONT.hasPeril, RDF.type, OWL.ObjectProperty))
        g.add((ONT.hasLimit, RDF.type, OWL.ObjectProperty))

        # ShapeMapping
        g.add((EX.SM_Limit, RDF.type, MORK.ShapeMapping))

        ts = BNode()
        g.add((EX.SM_Limit, MORK.hasTargetingSpec, ts))
        g.add((ts, SH.targetClass, ONT.Clause))

        pb = BNode()
        g.add((EX.SM_Limit, MORK.hasParameterBinding, pb))
        g.add((pb, MORK.paramName, Literal("path")))
        g.add((pb, MORK.paramType, Literal("Path")))
        g.add((pb, MORK.paramValue, ONT.hasLimit))

        pb2 = BNode()
        g.add((EX.SM_Limit, MORK.hasParameterBinding, pb2))
        g.add((pb2, MORK.paramName, Literal("maxInclusive")))
        g.add((pb2, MORK.paramType, Literal("Numeric")))
        g.add((pb2, MORK.paramValue, Literal(15000000, datatype=XSD.decimal)))

        prov = BNode()
        g.add((EX.SM_Limit, MORK.hasConstraintProvenance, prov))
        g.add((prov, MORK.reviewStatus, Literal("APPROVED")))

        # QueryTemplate
        g.add((EX.QT_Check, RDF.type, MORK.QueryTemplate))
        g.add((EX.QT_Check, MORK.queryText, Literal("SELECT ?x WHERE { ?x a ont:Clause }")))
        g.add((EX.QT_Check, MORK.queryLanguage, Literal("SPARQL")))

        compiler = MorkCompiler(g, str(GEN), validate_output=False)
        report = compiler.compile()

        self.assertTrue(report.is_valid)
        self.assertEqual(len(report.results), 2)

        types = {r.artefact_type for r in report.results}
        self.assertIn("SHACL", types)
        self.assertIn("SPARQL", types)


if __name__ == "__main__":
    unittest.main()