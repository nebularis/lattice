# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.7: the shapes over the contract of a generated operation, each rule with a positive and a negative case (formal-methods track H,
plan 4.7 step 2). The expected profiles are the positive fixtures. Each mutation of one is a negative witness for one rule, and the
rule is named by the shape and the path that report it. Validation Pack: docs/developer/validation/FMH-H2-7.md. Test IDs are H2.7-Sn."""

from __future__ import annotations

from copy import deepcopy

import pyshacl
import pytest
from rdflib import RDF, BNode, Graph, Literal, URIRef
from rdflib.namespace import SH, XSD

import expected_profiles as ep
from persistence.namespaces import DAL
from persistence.witness import SHAPES_TTL, SPEC_TTL

BASELINE = "baseline-single-class"
COMPOSITE = "composite-project-ownership"


def _shapes() -> Graph:
    return Graph().parse(SHAPES_TTL, format="turtle")


SHAPES = _shapes()
SPEC = Graph().parse(SPEC_TTL, format="turtle")
PROFILES = {name: Graph().parse(ep.OUT_DIR / f"{name}.expected.ttl", format="turtle") for name, _, _ in ep.CONFIGURATIONS}


def _local(term) -> str | None:
    return None if term is None else str(term).rsplit("#", 1)[-1]


def _owner(source):
    seen = set()
    while source is not None and not isinstance(source, URIRef) and source not in seen:
        seen.add(source)
        source = next(iter(SHAPES.subjects(SH.property, source)), None)
    return source


def _violations(data: Graph) -> set:
    """(shape, path) for every result the shapes report on ``data`` and the spec."""
    merged = Graph()
    merged.bind("dal", DAL)  # the SPARQL constraints name dal: through the graph's own bindings
    merged += SPEC
    merged += data
    _, report, _ = pyshacl.validate(merged, shacl_graph=SHAPES, inference="none", advanced=True, allow_warnings=True)
    out = set()
    for result in report.subjects(RDF.type, SH.ValidationResult):
        owner = _owner(report.value(result, SH.sourceShape))
        out.add((_local(owner), _local(report.value(result, SH.resultPath))))
    return out


def _copy(name: str) -> Graph:
    g = Graph()
    for t in PROFILES[name]:
        g.add(t)
    return g


def _op(g: Graph, operation: str):
    return next(s for s, o in g.subject_objects(DAL.forOperation) if str(o) == operation)


def _declaration(g: Graph, operation: str, predicate: URIRef, where=lambda g, n: True):
    return next(n for n in g.objects(_op(g, operation), predicate) if where(g, n))


def _set(g: Graph, node, predicate, value) -> None:
    g.set((node, predicate, value))


# ---- the positive fixtures ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(PROFILES))
def test_h2_7_s1_an_expected_profile_conforms_to_every_shape(name):
    assert _violations(PROFILES[name]) == set()


# ---- the negative witnesses ------------------------------------------------------------------------------------------------
# Each case is (name, profile, mutation, the (shape, path) that must be reported).


def _kind_of(op):
    return lambda g: _set(g, _op(g, op), DAL.operationKind, DAL.Bogus)


def _drop(subject_of, predicate):
    def mutate(g: Graph) -> None:
        g.remove((subject_of(g), predicate, None))
    return mutate


def _second(subject_of, predicate, value):
    def mutate(g: Graph) -> None:
        g.add((subject_of(g), predicate, value))
    return mutate


def _replace_with(subject_of, predicate, value):
    def mutate(g: Graph) -> None:
        g.set((subject_of(g), predicate, value))
    return mutate


def _op_node(operation: str):
    return lambda g: _op(g, operation)


def _param(operation: str, name: str):
    return lambda g: _declaration(g, operation, DAL.parameter, lambda gr, n: str(gr.value(n, DAL.parameterName)) == name)


def _access(operation: str, index: int = 0):
    return lambda g: sorted(g.objects(_op(g, operation), DAL.access), key=str)[index]


def _column(operation: str):
    return lambda g: next(iter(g.objects(_op(g, operation), DAL.resultColumn)))


def _payload(operation: str):
    return lambda g: g.value(_op(g, operation), DAL.payloadContract)


def _digest(operation: str):
    return lambda g: g.value(_op(g, operation), DAL.digestContract)


def _part(operation: str, role: str):
    return lambda g: next(n for n in g.objects(g.value(_op(g, operation), DAL.digestContract), DAL.digestPart) if _local(g.value(n, DAL.partRole)) == role)


def _blank_declaration(g: Graph) -> None:
    """Replace one parameter declaration by a blank node, wherever it appears."""
    node = _param("cas-replace", "root")(g)
    blank = BNode()
    for s, p, o in list(g.triples((node, None, None))):
        g.remove((s, p, o))
        g.add((blank, p, o))
    for s, p, o in list(g.triples((None, None, node))):
        g.remove((s, p, o))
        g.add((s, p, blank))


def _blank_link(g: Graph) -> None:
    """Hang a parameter off its operation by a blank node, as a hand-written declaration would."""
    op = _op(g, "cas-replace")
    node = BNode()
    g.add((op, DAL.parameter, node))
    g.add((node, RDF.type, DAL.ParameterDeclaration))
    g.add((node, DAL.parameterName, Literal("extra")))
    g.add((node, DAL.parameterKind, DAL.IriKind))
    g.add((node, DAL.required, Literal(False)))


def _foreign_edge(g: Graph) -> None:
    """Point a payload contract at an edge its profile does not state, as a copy made by hand would be (H2.8c)."""
    edge = URIRef("urn:x:copied-edge")
    g.add((edge, RDF.type, DAL.ReferenceEdge))
    g.add((g.value(_op(g, "cas-replace"), DAL.payloadContract), DAL.referenceEdge, edge))


CASES = [
    # the operation
    ("kind outside the enumeration", BASELINE, _replace_with(_op_node("cas-replace"), DAL.operationKind, DAL.Bogus), ("OperationContractShape", "operationKind")),
    ("kind missing", BASELINE, _drop(_op_node("cas-replace"), DAL.operationKind), ("OperationContractShape", "operationKind")),
    ("two kinds", BASELINE, _second(_op_node("cas-replace"), DAL.operationKind, DAL.Create), ("OperationContractShape", "operationKind")),
    ("version not an integer", BASELINE, _replace_with(_op_node("cas-replace"), DAL.templateVersion, Literal("one")), ("OperationContractShape", "templateVersion")),
    ("version missing", BASELINE, _drop(_op_node("cas-replace"), DAL.templateVersion), ("OperationContractShape", "templateVersion")),
    ("guard status outside the enumeration", BASELINE, _replace_with(_op_node("cas-replace"), DAL.guardStatus, DAL.Bogus), ("OperationContractShape", "guardStatus")),
    ("guard status missing", BASELINE, _drop(_op_node("cas-replace"), DAL.guardStatus), ("OperationContractShape", "guardStatus")),
    ("graph naming outside the enumeration", BASELINE, _replace_with(_op_node("cas-replace"), DAL.graphNaming, DAL.Bogus), ("OperationContractShape", "graphNaming")),
    ("declaration source outside the enumeration", BASELINE, _replace_with(_op_node("cas-replace"), DAL.declarationSource, DAL.Bogus), ("OperationContractShape", "declarationSource")),
    ("declaration source missing", BASELINE, _drop(_op_node("cas-replace"), DAL.declarationSource), ("OperationContractShape", "declarationSource")),
    ("no access", BASELINE, _drop(_op_node("cas-replace"), DAL.access), ("OperationContractShape", "access")),
    ("a parameter that is not a declaration", BASELINE, _second(_op_node("cas-replace"), DAL.parameter, URIRef("urn:x:nothing")), ("OperationContractShape", "parameter")),
    ("two payload contracts", BASELINE, _second(_op_node("cas-replace"), DAL.payloadContract, URIRef("urn:x:nothing")), ("OperationContractShape", "payloadContract")),
    ("two digest contracts", BASELINE, _second(_op_node("cas-replace"), DAL.digestContract, URIRef("urn:x:nothing")), ("OperationContractShape", "digestContract")),
    # a parameter
    ("parameter kind outside the enumeration", BASELINE, _replace_with(_param("cas-replace", "root"), DAL.parameterKind, DAL.Bogus), ("ParameterDeclarationShape", "parameterKind")),
    ("parameter kind missing", BASELINE, _drop(_param("cas-replace", "root"), DAL.parameterKind), ("ParameterDeclarationShape", "parameterKind")),
    ("parameter name missing", BASELINE, _drop(_param("cas-replace", "root"), DAL.parameterName), ("ParameterDeclarationShape", "parameterName")),
    ("required not a boolean", BASELINE, _replace_with(_param("cas-replace", "root"), DAL.required, Literal("yes")), ("ParameterDeclarationShape", "required")),
    ("rule outside the enumeration", "baseline-single-class.caller-named", _replace_with(_param("cas-replace", "g"), DAL.mustEqual, DAL.Bogus), ("ParameterDeclarationShape", "mustEqual")),
    ("rule applied to a literal", "baseline-single-class.caller-named", _replace_with(_param("cas-replace", "g"), DAL.mustEqualFor, Literal("root")), ("ParameterDeclarationShape", "mustEqualFor")),
    ("source outside the enumeration", BASELINE, _replace_with(_param("gap-scan-audit", "logGraphs"), DAL.sourcedFrom, DAL.Bogus), ("ParameterDeclarationShape", "sourcedFrom")),
    # an access
    ("resource kind outside the enumeration", BASELINE, _replace_with(_access("cas-replace"), DAL.resourceKind, DAL.Bogus), ("ResourceAccessShape", "resourceKind")),
    ("resource kind missing", BASELINE, _drop(_access("cas-replace"), DAL.resourceKind), ("ResourceAccessShape", "resourceKind")),
    ("access mode outside the enumeration", BASELINE, _replace_with(_access("cas-replace"), DAL.accessMode, DAL.Bogus), ("ResourceAccessShape", "accessMode")),
    ("access mode missing", BASELINE, _drop(_access("cas-replace"), DAL.accessMode), ("ResourceAccessShape", "accessMode")),
    ("key that is a literal", BASELINE, _second(_access("create-if-absent", 0), DAL.keyedBy, Literal("root")), ("ResourceAccessShape", "keyedBy")),
    # a result column
    ("column kind outside the enumeration", BASELINE, _replace_with(_column("gap-scan-audit"), DAL.columnKind, DAL.Bogus), ("ResultColumnShape", "columnKind")),
    ("column position below one", BASELINE, _replace_with(_column("gap-scan-audit"), DAL.columnPosition, Literal(0)), ("ResultColumnShape", "columnPosition")),
    ("column name missing", BASELINE, _drop(_column("gap-scan-audit"), DAL.columnName), ("ResultColumnShape", "columnName")),
    # a payload
    ("payload encoding outside the enumeration", BASELINE, _replace_with(_payload("cas-replace"), DAL.payloadEncoding, DAL.Bogus), ("PayloadContractShape", "payloadEncoding")),
    ("boundary shape left out", BASELINE, _drop(_payload("cas-replace"), DAL.boundaryShape), ("PayloadContractShape", "boundaryShape")),
    ("boundary shape a literal", BASELINE, _replace_with(_payload("cas-replace"), DAL.boundaryShape, Literal("shape")), ("PayloadContractShape", "boundaryShape")),
    ("payload parameter missing", BASELINE, _drop(_payload("cas-replace"), DAL.payloadParameter), ("PayloadContractShape", "payloadParameter")),
    ("an edge that is a blank node", COMPOSITE, _second(_payload("cas-replace"), DAL.referenceEdge, BNode()), ("PayloadContractShape", "referenceEdge")),
    ("an edge its own profile does not state", COMPOSITE, _foreign_edge, ("PayloadContractShape", None)),
    # a digest
    ("digest algorithm other than SHA-256", BASELINE, _replace_with(_digest("cas-replace"), DAL.digestAlgorithm, Literal("MD5")), ("DigestContractShape", "digestAlgorithm")),
    ("digest with no part", BASELINE, _drop(_digest("cas-replace"), DAL.digestPart), ("DigestContractShape", "digestPart")),
    ("part role outside the enumeration", BASELINE, _replace_with(_part("cas-replace", "TargetPart"), DAL.partRole, DAL.Bogus), ("DigestPartShape", "partRole")),
    ("part order below one", BASELINE, _replace_with(_part("cas-replace", "TargetPart"), DAL.partOrder, Literal(0)), ("DigestPartShape", "partOrder")),
    ("part source a literal", BASELINE, _replace_with(_part("cas-replace", "TargetPart"), DAL.partSource, Literal("root")), ("DigestPartShape", "partSource")),
    ("part with no source", BASELINE, _drop(_part("cas-replace", "TargetPart"), DAL.partSource), ("DigestPartShape", "partSource")),
    # no blank node in a declaration
    ("a declaration that is a blank node", BASELINE, _blank_declaration, ("ContractDeclarationIsIriShape", None)),
    ("a declaration linked by a blank node", BASELINE, _blank_link, ("OperationContractShape", "parameter")),
    # no SPARQL text in a value
    ("a query as the value of another property", BASELINE, _second(_param("cas-replace", "root"), DAL.queryText, Literal("SELECT ?s WHERE { ?s ?p ?o }")), ("ContractHoldsNoSparqlTextShape", "queryText")),
    ("a parameter name that is a query", BASELINE, _replace_with(_param("cas-replace", "root"), DAL.parameterName, Literal("?x } DELETE WHERE { ?s ?p ?o")), ("ContractHoldsNoSparqlTextShape", "parameterName")),
    ("a column name that is a query", BASELINE, _replace_with(_column("gap-scan-audit"), DAL.columnName, Literal("?x } DROP ALL")), ("ContractHoldsNoSparqlTextShape", "columnName")),
    ("a separator that is a query", BASELINE, _second(_column("fork-detection-audit"), DAL.columnSeparator, Literal("} DROP ALL {")), ("ContractHoldsNoSparqlTextShape", "columnSeparator")),
    # a required parameter is guarded unless the status says otherwise
    ("no required parameter claimed for an operation that has one", BASELINE, _replace_with(_op_node("cas-replace"), DAL.guardStatus, DAL.NoRequiredParameter), ("RequiredParametersGuardedShape", None)),
    ("guarded claimed for an operation with nothing to guard", BASELINE, _replace_with(_op_node("fork-detection-audit"), DAL.guardStatus, DAL.Guarded), ("RequiredParametersGuardedShape", None)),
]


@pytest.mark.parametrize("name,profile,mutate,expected", CASES, ids=[c[0] for c in CASES])
def test_h2_7_s2_each_rule_is_broken_by_its_witness_and_reported_by_its_shape(name, profile, mutate, expected):
    g = _copy(profile)
    mutate(g)
    assert expected in _violations(g), (name, _violations(g))


def test_h2_7_s3_the_guard_rule_lets_a_status_say_otherwise():
    """dal:GuardsOff and dal:NotGenerated promise nothing of the parameters, and a request-time slot is not guarded."""
    for status in (DAL.GuardsOff, DAL.NotGenerated):
        g = _copy(BASELINE)
        _set(g, _op(g, "cas-replace"), DAL.guardStatus, status)
        assert _violations(g) == set()
    g = _copy(BASELINE)
    slot_only = next(
        op for op in g.subjects(DAL.guardStatus, DAL.NoRequiredParameter)
        if any(g.value(p, DAL.required) == Literal(True) for p in g.objects(op, DAL.parameter))
    )
    assert slot_only is not None and _violations(g) == set()  # an audit whose only required parameter is a registry list is not guarded, and conforms


# ---- the configuration shapes of H2.6c to H2.6f ----------------------------------------------------------------------------

EX = "https://example.org/x#"


def _config(body: str) -> Graph:
    g = Graph()
    g.parse(data=f"@prefix dal: <{DAL}> . @prefix ex: <{EX}> . @prefix xsd: <{XSD}> . {body}", format="turtle")
    return g


CONFIG_CASES = [
    ("receipt model outside the enumeration", "ex:r a dal:ReceiptProfile ; dal:receiptModel ex:Other .", ("ReceiptProfileShape", "receiptModel")),
    ("write discipline outside the enumeration", "ex:w a dal:WriteDisciplineProfile ; dal:writeDiscipline ex:Other .", ("WriteDisciplineProfileShape", "writeDiscipline")),
    ("membership encoding outside the enumeration", "ex:w a dal:WriteDisciplineProfile ; dal:membershipEncoding ex:Other .", ("WriteDisciplineProfileShape", "membershipEncoding")),
    ("a checkpoint interval that is not a number", 'ex:w a dal:WriteDisciplineProfile ; dal:checkpointEvery "four" .', ("WriteDisciplineProfileShape", "checkpointEvery")),
    ("a reference mode outside the enumeration", "ex:e dal:referenceMode ex:Other .", ("ReferenceModeShape", "referenceMode")),
    ("two reference modes", "ex:e dal:referenceMode dal:Pinned , dal:ByIdentity .", ("ReferenceModeShape", "referenceMode")),
]


@pytest.mark.parametrize("name,body,expected", CONFIG_CASES, ids=[c[0] for c in CONFIG_CASES])
def test_h2_7_s4_the_discipline_encoding_and_reference_mode_values_are_closed(name, body, expected):
    assert expected in _violations(_config(body))


def test_h2_7_s5_the_closed_values_of_the_configuration_are_accepted():
    body = """
      ex:r a dal:ReceiptProfile ; dal:receiptModel dal:NoReceipt .
      ex:w a dal:WriteDisciplineProfile ; dal:writeDiscipline dal:AppendVersions ; dal:membershipEncoding dal:DeltaMembership ;
           dal:checkpointEvery "16"^^xsd:long .
      ex:e dal:referenceMode dal:Pinned .
    """
    assert _violations(_config(body)) == set()


@pytest.mark.parametrize("name", sorted(PROFILES))
def test_h2_7_s6_what_compile_emits_conforms_to_the_shapes(name):
    """The shapes check the emitted profile itself and not only the reviewed file, so an emission that wrote a blank-node declaration, a value
    outside an enumeration or a guard status that disagrees with the parameters fails here, whatever the files say."""
    _, example, options = next(c for c in ep.CONFIGURATIONS if c[0] == name)
    assert _violations(ep.emit(example, **options)) == set()
