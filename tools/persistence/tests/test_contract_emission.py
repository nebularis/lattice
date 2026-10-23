# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.7: `compile` emits the contract of every operation and records the run choices, the vocabulary declares and documents everything the
profile uses, `instantiate` follows the profile, and the value-based guard has a builder and a data graph (formal-methods track H, plan
4.7, steps 1, 3 and 4, questions H2.7-Q1 to Q3). Validation Pack: docs/developer/validation/FMH-H2-7.md. Test IDs are H2.7-Tn."""

from __future__ import annotations

import inspect
import warnings

import pytest
from rdflib import OWL, RDF, RDFS, BNode, Dataset, Graph, Literal, URIRef, Variable
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.namespace import SH, XSD

import engines
import expected_profiles as ep
from persistence import witness
from persistence.builders import BUILDERS
from persistence.cli import build_parser, main
from persistence.compiler import CompileError, compile_targets, compile_to_graph
from persistence.contract import (
    HAND_DECLARED, LOGICAL_KEYS, AccessMode, DeclarationSource, GraphNaming, GuardStatus, OperationKind, ResourceKind,
)
from persistence.instantiate import instantiate_by_target, instantiate_profile, instantiate_to_directory
from persistence.ir import GraphRole, IrError, Kind, Operation
from persistence.namespaces import DAL

from conftest import EXAMPLES_DIR
from test_builders import _corpus

SPEC = Graph().parse(witness.SPEC_TTL, format="turtle")
SHAPES = Graph().parse(witness.SHAPES_TTL, format="turtle")


def _local(term) -> str:
    return str(term).rsplit("#", 1)[-1]


def _individuals(cls: str) -> set[str]:
    return {_local(s) for s in SPEC.subjects(RDF.type, DAL[cls])}


# ---- the vocabulary (steps 1) -------------------------------------------------------------------------------------------------


def _terms_used(graphs) -> tuple[set, set, set]:
    predicates, classes, individuals = set(), set(), set()
    for g in graphs:
        for _, p, o in g:
            if isinstance(p, URIRef) and str(p).startswith(str(DAL)):
                predicates.add(p)
            if isinstance(o, URIRef) and str(o).startswith(str(DAL)):
                (classes if p == RDF.type else individuals).add(o)
    return predicates, classes, individuals


def test_h2_7_t1_every_term_a_compiled_profile_uses_is_declared_in_the_spec():
    """Over the profile of every fixture that compiles (the examples and the witnesses), and the expected profiles."""
    declared = {s for s in SPEC.subjects() if isinstance(s, URIRef)}
    examples = {p.name for p in EXAMPLES_DIR.glob("*.ttl")}  # a witness may set a value outside the enumeration on purpose
    graphs = [compiled for name, compiled in _corpus() if name in examples] + [ep.emit(example, **options) for _, example, options in ep.CONFIGURATIONS]
    predicates, classes, individuals = _terms_used(graphs)
    assert len(predicates) > 40
    assert not sorted(str(t) for t in (predicates | classes | individuals) - declared)
    # a predicate is a property, a class is an owl:Class, and an individual is typed by a class
    assert all(any(SPEC.triples((p, RDF.type, t)) for t in (OWL.ObjectProperty, OWL.DatatypeProperty)) for p in predicates), "not a property"
    assert all((c, RDF.type, OWL.Class) in SPEC for c in classes)


def test_h2_7_t2_the_template_path_is_gone_from_the_spec_and_from_every_profile():
    assert (DAL.templatePath, None, None) not in SPEC and not list(SPEC.objects(None, DAL.templatePath))
    assert not any((None, DAL.templatePath, None) in compiled for _, compiled in _corpus())
    ids = {str(o) for _, compiled in _corpus() for o in compiled.objects(None, DAL.templateId)}
    assert ids and not any(i.endswith(".mustache") for i in ids)
    assert ids <= set(BUILDERS), sorted(ids - set(BUILDERS))  # instantiate finds each builder by its id


ENUMERATIONS = {
    "OperationKind": {k.value for k in OperationKind},
    "ResourceKind": {k.value for k in ResourceKind},
    "AccessMode": {m.value for m in AccessMode},
    "GuardStatus": {s.value for s in GuardStatus},
    "GraphNaming": {n.value for n in GraphNaming},
    "DeclarationSource": {s.value for s in DeclarationSource},
    "ParameterKind": {f"{k.value}Kind" for k in Kind},
    "ColumnKind": {f"{n}Column" for n in ("Iri", "Position", "String", "Term", "Count", "Concatenation")},
    "DigestPartRole": {"OperationKindPart", "TargetPart", "ExpectedSeqPart", "PayloadPart", "EventPart", "AddPart", "DelPart"},
    "PayloadEncoding": {"GroundNTriples"},
    "Rule": {"GraphNameOfRoot"},
    "Source": {"RegistryGraph", "NoSource"},
    "BoundaryShapeAbsence": {"NoBoundaryShape"},
    "ReferenceMode": {"ByIdentity", "Pinned"},
    "OwnershipKind": {"Owned", "Reference", "Vocabulary"},
    "WriteDiscipline": {"InPlace", "AppendVersions", "AppendRecords"},
    "MembershipEncoding": {"FullMembership", "DeltaMembership"},
    "AuditOutcome": {"Clean", "Failed", "NothingExamined"},
    "ReceiptModel": {"ReceiptOnly", "PatchLog", "SnapshotPerRevision", "NoReceipt"},
}


@pytest.mark.parametrize("cls", sorted(ENUMERATIONS))
def test_h2_7_t3_each_enumeration_of_the_spec_is_the_set_the_code_uses(cls):
    """The enumerations moved from `kinds.expected.ttl` into the spec as individuals, and the code's enums are held to them."""
    assert _individuals(cls) == ENUMERATIONS[cls]
    assert (DAL[cls], RDF.type, OWL.Class) in SPEC


def test_h2_7_t4_each_logical_key_of_the_code_is_the_spec_s():
    for resource, key in LOGICAL_KEYS.items():
        assert SPEC.value(DAL[resource.value], DAL.logicalKey) == Literal(", ".join(key)), resource


# which sh:in list of the shapes closes which enumeration
CLOSED_BY = {
    ("OperationContractShape", "operationKind"): "OperationKind", ("OperationContractShape", "guardStatus"): "GuardStatus",
    ("OperationContractShape", "graphNaming"): "GraphNaming", ("OperationContractShape", "declarationSource"): "DeclarationSource",
    ("ParameterDeclarationShape", "parameterKind"): "ParameterKind", ("ParameterDeclarationShape", "mustEqual"): "Rule",
    ("ParameterDeclarationShape", "sourcedFrom"): "Source", ("ResourceAccessShape", "resourceKind"): "ResourceKind",
    ("ResourceAccessShape", "accessMode"): "AccessMode", ("ResultColumnShape", "columnKind"): "ColumnKind",
    ("PayloadContractShape", "payloadEncoding"): "PayloadEncoding", ("DigestPartShape", "partRole"): "DigestPartRole",
    ("ReceiptProfileShape", "receiptModel"): "ReceiptModel", ("WriteDisciplineProfileShape", "writeDiscipline"): "WriteDiscipline",
    ("WriteDisciplineProfileShape", "membershipEncoding"): "MembershipEncoding", ("ReferenceModeShape", "referenceMode"): "ReferenceMode",
}


@pytest.mark.parametrize("shape,path", sorted(CLOSED_BY))
def test_h2_7_t5_every_closed_list_of_the_shapes_is_the_enumeration_of_the_spec(shape, path):
    """The shapes close a value with `sh:in`, so a list that drifted from the spec would accept or refuse the wrong value."""
    prop = next(
        p for p in SHAPES.objects(DAL[shape], SH.property) if SHAPES.value(p, SH.path) == DAL[path]
    )
    listed = {_local(x) for x in Collection(SHAPES, SHAPES.value(prop, SH["in"]))}
    expected = _individuals(CLOSED_BY[(shape, path)])
    if (shape, path) == ("ParameterDeclarationShape", "sourcedFrom"):
        expected -= {"NoSource"}  # a parameter has a source or none, and no source is the absence of the property
    assert listed == expected


CONTRACT_TERMS = [
    "operationKind", "templateVersion", "guardStatus", "graphNaming", "declarationSource", "parameter", "access", "resultColumn",
    "payloadContract", "digestContract", "ParameterDeclaration", "parameterName", "parameterKind", "required", "mustEqual", "mustEqualFor",
    "sourcedFrom", "ResourceAccess", "resourceKind", "accessMode", "keyedBy", "ResultColumn", "columnName", "columnPosition", "columnKind",
    "columnSeparator", "PayloadContract", "payloadParameter", "payloadRoot", "payloadEncoding", "DigestContract", "digestAlgorithm",
    "digestPart", "DigestPart", "partOrder", "partRole", "partSource", "logicalKey",
    # H2.6c to H2.6f
    "WriteDisciplineProfile", "writeDiscipline", "WriteDiscipline", "membershipEncoding", "MembershipEncoding", "checkpointEvery",
    "referenceMode", "ReferenceMode", "ReceiptModel",
    # H2.8b
    "edgeTargetShape", "AuditOutcome", "reportsOutcome", "examinedParameter",
]


def test_h2_7_t6_every_term_of_the_contract_and_of_the_disciplines_is_documented():
    terms = set(CONTRACT_TERMS)
    for cls, names in ENUMERATIONS.items():
        terms.add(cls)
        terms |= names
    undocumented = sorted(t for t in terms if not SPEC.value(DAL[t], RDFS.comment))
    assert not undocumented


# ---- the payload check kind (Q3) --------------------------------------------------------------------------------------------


def test_h2_7_t8_payload_check_is_a_kind_and_h2_8b_emits_the_operation():
    assert OperationKind.PAYLOAD_CHECK.value == "PayloadCheck" and "PayloadCheck" in _individuals("OperationKind")
    from persistence.contract import OPERATION_KINDS

    assert OperationKind.PAYLOAD_CHECK in set(OPERATION_KINDS.values())  # H2.8b emits the operation
    kinds = {_local(o) for _, compiled in _corpus() for o in compiled.objects(None, DAL.operationKind)}
    assert "PayloadCheck" in kinds


# ---- minted IRIs ------------------------------------------------------------------------------------------------------------


def test_h2_7_t9_each_declaration_node_belongs_to_one_operation_so_two_deployments_of_one_class_do_not_share_them():
    compiled, _ = compile_to_graph(witness._load_fixture(EXAMPLES_DIR / "lending-credit-shared-class.ttl"))
    deployments = {compiled.value(p, DAL.forDeployment) for p in compiled.subjects(RDF.type, DAL.CompiledProfile)}
    assert len(deployments) >= 2
    owners: dict = {}
    for op, node in compiled.subject_objects(DAL.parameter):
        owners.setdefault(node, set()).add(op)
    assert owners and all(len(ops) == 1 for ops in owners.values())
    assert all(isinstance(n, URIRef) for n in owners)


@pytest.mark.parametrize("name", ["baseline-single-class", "composite-project-ownership", "uniqueness-merge-policy"])
def test_h2_7_t9b_two_compiles_give_the_same_profile_whatever_order_the_configuration_was_loaded_in(name):
    """Every node of a declaration is an IRI minted from names, so the declarations are the same set each time, and the profile is
    isomorphic, since the blank nodes of the base profile have stable labels (H1.5)."""
    import random

    source = witness._load_fixture(EXAMPLES_DIR / f"{name}.ttl")
    triples = sorted(source, key=str)

    def shuffled(seed: int) -> Graph:
        order = list(triples)
        random.Random(seed).shuffle(order)
        g = Graph()
        for t in order:
            g.add(t)
        return g

    graphs = [compile_to_graph(shuffled(seed))[0] for seed in (1, 2)] + [compile_to_graph(source)[0]]
    declarations = [{t for t in g if ep.is_declaration(t[0])} for g in graphs]
    assert declarations[0] and declarations[0] == declarations[1] == declarations[2]
    assert isomorphic(graphs[0], graphs[1]) and isomorphic(graphs[1], graphs[2])
    assert not any(isinstance(o, BNode) for g in graphs for s, p, o in g if ep.is_declaration(s) or p in ep.NEW_PREDICATES)


# ---- the run choices (Q2) ---------------------------------------------------------------------------------------------------


def _compile(example: str = "baseline-single-class", **choices) -> Graph:
    return compile_to_graph(witness._load_fixture(EXAMPLES_DIR / f"{example}.ttl"), **choices)[0]


def test_h2_7_t10_compile_records_the_guard_status_of_every_operation_and_who_names_a_graph():
    guarded, off = _compile(), _compile(guards=False)
    statuses = lambda g: {_local(o) for o in g.objects(None, DAL.guardStatus)}
    assert statuses(guarded) <= {"Guarded", "NoRequiredParameter"} and "Guarded" in statuses(guarded)
    assert statuses(off) == {"GuardsOff"}
    assert {_local(o) for o in guarded.objects(None, DAL.graphNaming)} == {"QueryNamed"}
    caller = _compile(graph_names="caller")
    assert {_local(o) for o in caller.objects(None, DAL.graphNaming)} == {"CallerNamed"}
    assert not (None, DAL.graphNaming, DAL.QueryNamed) in caller


def test_h2_7_t11_an_unknown_graph_naming_is_refused():
    with pytest.raises(ValueError):
        _compile(graph_names="whoever")


def test_h2_7_t12_instantiate_renders_what_the_profile_says_and_takes_no_flag_of_its_own():
    guarded, off = instantiate_profile(_compile()), instantiate_profile(_compile(guards=False))
    assert "ISIRI($root)" in guarded["cas-replace"] and "ISIRI(" not in off["cas-replace"]
    caller = instantiate_profile(_compile(graph_names="caller"))
    assert "GRAPH $g" in caller["cas-replace"] and "GRAPH $g" not in guarded["cas-replace"]
    for function in (instantiate_by_target, instantiate_profile, instantiate_to_directory):
        assert not {"guards", "graph_names"} & set(inspect.signature(function).parameters)


def test_h2_7_t13_a_rendering_cannot_disagree_with_its_profile():
    """Flip one operation's status in the profile, and its rendering follows. A profile read back from Turtle renders the same."""
    profile = _compile()
    node = next(s for s, o in profile.subject_objects(DAL.forOperation) if str(o) == "cas-replace")
    assert "ISIRI($root)" in instantiate_profile(profile)["cas-replace"]
    profile.set((node, DAL.guardStatus, DAL.GuardsOff))
    assert "ISIRI(" not in instantiate_profile(profile)["cas-replace"]
    reread = Graph().parse(data=profile.serialize(format="turtle"), format="turtle")
    assert instantiate_profile(reread) == instantiate_profile(profile)


def test_h2_7_t14_the_command_line_flags_move_from_instantiate_to_compile(tmp_path):
    parser = build_parser()
    for flag in ("--no-parameter-guards", "--caller-graph-names"):
        with pytest.raises(SystemExit):
            parser.parse_args(["instantiate", "p.ttl", "--out", "o", flag])
        assert parser.parse_args(["compile", "c.ttl", "--out", "o", flag]).command == "compile"
    spec, example = str(witness.SPEC_TTL), str(EXAMPLES_DIR / "baseline-single-class.ttl")
    assert main(["compile", spec, example, "--out", str(tmp_path / "p.ttl"), "--no-parameter-guards", "--caller-graph-names"]) == 0
    assert main(["instantiate", str(tmp_path / "p.ttl"), "--out", str(tmp_path / "rq")]) == 0
    text = next((tmp_path / "rq").rglob("cas-replace.rq")).read_text(encoding="utf-8")
    assert "GRAPH $g" in text and "ISIRI(" not in text


# ---- TD-43 (Q1) --------------------------------------------------------------------------------------------------------------


def _value_based() -> Graph:
    return witness._load_fixture(EXAMPLES_DIR / "value-based-cas.ttl")


def test_h2_7_t15_a_family_with_no_boundary_and_a_value_guard_needs_a_data_graph():
    graph = _value_based()
    graph.remove((None, DAL.dataGraph, None))
    with pytest.raises(CompileError) as error:
        compile_targets(graph)
    assert error.value.cause.kind == "MissingDataGraph" and "NoBoundary" in str(error.value.cause)
    assert compile_targets(_value_based())


def test_h2_7_t16_the_value_guard_has_a_builder_and_no_operation_is_declared_by_hand():
    assert "cas-replace-value-guard" in BUILDERS and HAND_DECLARED == {}
    profile = _compile("value-based-cas")
    node = next(s for s, o in profile.subject_objects(DAL.forOperation) if str(o) == "cas-replace")
    bindings = {str(profile.value(b, DAL.paramName)): str(profile.value(b, DAL.paramValue)) for b in profile.objects(node, DAL.hasParameterBinding)}
    assert bindings["dataGraph"] == "<urn:g:order-status>"
    assert profile.value(node, DAL.declarationSource) == DAL.BuilderDerived and profile.value(node, DAL.guardStatus) == DAL.Guarded


def test_h2_7_t17_every_pattern_of_the_value_guard_is_in_the_data_graph():
    text = instantiate_profile(_compile("value-based-cas"))["cas-replace"]
    assert text.count("GRAPH <urn:g:order-status>") == 3  # the delete, the insert and the where
    assert "DELETE {\n  GRAPH" in text and "INSERT {\n  GRAPH" in text and "WHERE {\n  " in text


def test_h2_7_t18_a_value_guard_pattern_in_the_default_graph_is_refused_by_the_renderer():
    from persistence.builders import Bindings, _value_guard
    from persistence.ir import Group, Triple, ParamRef, Const
    from persistence.ir_render import render
    from persistence.terms import Iri
    import dataclasses

    _, _, _, context = next(op for op in __import__("test_builders")._ported() if op[2] == "cas-replace-value-guard")
    good = _value_guard(Bindings(context), guards=True)
    assert render(good)
    bare = Triple(ParamRef("root"), Const(Iri.encode("urn:p")), ParamRef("oldValue"))
    with pytest.raises(IrError, match="DefaultGraphPattern"):
        render(dataclasses.replace(good, where=Group((bare,))))


# ---- the value guard runs --------------------------------------------------------------------------------------------------

ORDER = URIRef("https://example.org/lending#order1")
STATUS = URIRef("https://example.org/lending#status")
DATA = URIRef("urn:g:order-status")


def _graphs(ds) -> dict:
    out: dict = {}
    for s, p, o, g in ds.quads((None, None, None, None)):
        out.setdefault(str(getattr(g, "identifier", g)), set()).add((s, p, o))
    return out


def _run_value_guard(old, new, *, stored="open", bind=("root", "oldValue", "newValue")):
    text = instantiate_profile(_compile("value-based-cas", guards=engines.guards()))["cas-replace"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds = engines.dataset()
        ds.graph(DATA).add((ORDER, STATUS, Literal(stored)))
        ds.default_context.add((ORDER, STATUS, Literal(stored)))  # a copy in the default graph, which the update must leave alone
        values = {"root": ORDER, "oldValue": old, "newValue": new}
        ds.update(text, initBindings={Variable(k): v for k, v in values.items() if k in bind})
    return _graphs(ds)


@engines.each_engine_and_guards
def test_h2_7_t19_the_value_guard_replaces_the_old_value_in_the_data_graph_and_leaves_the_default_graph_alone():
    graphs = _run_value_guard(Literal("open"), Literal("closed"))
    assert graphs[str(DATA)] == {(ORDER, STATUS, Literal("closed"))}
    default = next(v for k, v in graphs.items() if k != str(DATA))
    assert default == {(ORDER, STATUS, Literal("open"))}


@engines.each_engine_and_guards
def test_h2_7_t20_a_stale_old_value_writes_nothing():
    graphs = _run_value_guard(Literal("pending"), Literal("closed"))
    assert graphs[str(DATA)] == {(ORDER, STATUS, Literal("open"))}


@engines.each_engine
def test_h2_7_t21_with_the_guard_on_a_missing_parameter_writes_nothing():
    """The new value left out: without the guard the old value would be deleted and nothing inserted, which the guard prevents."""
    graphs = _run_value_guard(Literal("open"), None, bind=("root", "oldValue"))
    assert graphs[str(DATA)] == {(ORDER, STATUS, Literal("open"))}
