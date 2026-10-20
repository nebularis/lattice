# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.6: the expected compiled profiles are held to the builders and to today's compiler (formal-methods track H, plan 4.4).
The files are under ontology/persistence/test/expected-profiles/ and are produced by `expected_profiles.py`. Validation Pack:
docs/developer/validation/FMH-H2-6.md. Test IDs are H2.6-Tn."""

from __future__ import annotations

import dataclasses
import random
import re
from pathlib import Path

import pytest
from rdflib import RDF, RDFS, BNode, Graph, Literal, URIRef
from rdflib.compare import isomorphic

import expected_profiles as ep
from persistence import witness
from persistence.builders import BUILDERS, build
from persistence.compiler import compile_to_graph
from persistence.contract import (
    DATASET_GUARD_SUFFIX, HAND_DECLARED, AccessContract, DeclarationSource, DigestContract, GraphNaming, GuardStatus,
    OperationContract, OperationKind, ParameterContract, PayloadContract, ResultColumn, contract_of, stem_of,
)
from persistence.ir import SLOT_KINDS, Kind
from persistence.namespaces import DAL
from persistence.render import load_template, render as _mustache  # noqa: F401 (load_template is used below)

from test_builders import _first

FILES = sorted(ep.OUT_DIR.glob("*.expected.ttl"))
PROFILES = [p for p in FILES if p.name != f"{ep.KINDS_FILE}.expected.ttl"]
CONFIG = {name: (example, options) for name, example, options in ep.CONFIGURATIONS}


def _name(path: Path) -> str:
    return path.name.removesuffix(".expected.ttl")


@pytest.fixture(scope="module")
def parsed() -> dict:
    return {_name(p): Graph().parse(p, format="turtle") for p in FILES}


# ---- parse and no SPARQL text --------------------------------------------------------------------------------------------


def test_h2_6_t1_the_expected_profiles_and_the_enumerations_exist_and_parse(parsed):
    assert len(PROFILES) == len(ep.CONFIGURATIONS) == 11 and set(parsed) == {name for name, _, _ in ep.CONFIGURATIONS} | {ep.KINDS_FILE}
    assert all(len(g) > 0 for g in parsed.values())
    assert not any(DAL.templatePath in {p for _, p, _ in g} for g in parsed.values())  # without dal:templatePath
    ids = [str(o) for g in parsed.values() for o in g.objects(None, DAL.templateId)]
    assert ids and not any(i.endswith(".mustache") for i in ids)  # the builder's identity, not a file name


def _declaration_triples(graph: Graph):
    return [t for t in graph if ep.is_declaration(t[0]) or t[1] in ep.NEW_PREDICATES]


def test_h2_6_t2_no_new_part_holds_a_blank_node_or_sparql_text(parsed):
    checked = 0
    for name, graph in parsed.items():
        if name == ep.KINDS_FILE:
            continue
        for s, p, o in _declaration_triples(graph):
            if ep.is_declaration(s) or p in ep.NEW_PREDICATES:
                assert not isinstance(o, BNode), (name, s, p)
            if ep.is_declaration(s):
                assert isinstance(s, URIRef)
            if isinstance(o, Literal):
                assert re.fullmatch(r"[A-Za-z0-9 ._-]*", str(o)), (name, s, p, str(o))  # a name, a number or a separator, never a query
            checked += 1
    assert checked > 1000


# ---- the base profile ----------------------------------------------------------------------------------------------------


def _without_new(graph: Graph) -> Graph:
    base = Graph()
    for s, p, o in graph:
        if ep.is_declaration(s) or p in ep.NEW_PREDICATES:
            continue
        base.add((s, p, o))
    return base


def _compiled_base(example: str) -> Graph:
    compiled, _ = compile_to_graph(witness._load_fixture(ep.EXAMPLES / f"{example}.ttl"))
    return ep.as_expected(compiled)


@pytest.mark.parametrize("path", PROFILES, ids=_name)
def test_h2_6_t3_an_expected_profile_without_the_new_terms_is_todays_compiled_profile_apart_from_the_two_listed_base_changes(path, parsed):
    """The two base changes are no `dal:templatePath` and a `dal:templateId` without the `.mustache` suffix (`expected_profiles.as_expected`).
    Isomorphic and not byte identical, since parsing gives a blank node a fresh label. A change to `compile` output regenerates
    the files in the same commit."""
    example, _ = CONFIG[_name(path)]
    assert isomorphic(_without_new(parsed[_name(path)]), _compiled_base(example))


# ---- the agreement test --------------------------------------------------------------------------------------------------


def _facts(c: OperationContract, shape: str | None) -> set:
    facts = {
        ("kind", c.kind.value), ("version", c.version), ("guard", c.guard_status.value),
        ("naming", c.graph_naming.value if c.graph_naming else None), ("source", c.source.value),
    }
    for p in c.parameters:
        facts |= {
            ("param", p.name, "kind", p.kind), ("param", p.name, "required", p.required),
            ("param", p.name, "equals-graph-name", p.equals_graph_name), ("param", p.name, "registry", p.sourced_from_registry),
        }
    facts |= {("access", a.resource, a.mode, a.keyed_by) for a in c.accesses}
    facts |= {("result", i, r.name, r.kind, r.separator) for i, r in enumerate(c.results, 1)}
    if c.payload:
        facts.add(("payload", c.payload.parameter, c.payload.root, shape or "NoBoundaryShape"))
    if c.digest:
        facts.add(("digest", c.digest.target, c.digest.expected, c.digest.payload, c.digest.event, c.digest.add, c.digest.delete))
    return facts


def _local(term) -> str | None:
    return None if term is None else str(term).rsplit("#", 1)[-1]


def _read_contract(g: Graph, node) -> tuple[OperationContract, str | None]:
    """The contract an expected profile states for one generated operation, read back from the file."""
    naming = g.value(node, DAL.graphNaming)
    param_names = {}
    parameters = []
    for pn in g.objects(node, DAL.parameter):
        name = str(g.value(pn, DAL.parameterName))
        param_names[pn] = name
        parameters.append(ParameterContract(
            name, _local(g.value(pn, DAL.parameterKind)).removesuffix("Kind"), bool(g.value(pn, DAL.required).toPython()),
            g.value(pn, DAL.mustEqual) is not None, g.value(pn, DAL.sourcedFrom) is not None,
        ))
    accesses = []
    for an in g.objects(node, DAL.access):
        keyed = g.value(an, DAL.keyedBy)
        accesses.append(AccessContract(_local(g.value(an, DAL.resourceKind)), _local(g.value(an, DAL.accessMode)), param_names.get(keyed)))
    results = sorted(
        ((int(g.value(rn, DAL.columnPosition)), ResultColumn(
            str(g.value(rn, DAL.columnName)), _local(g.value(rn, DAL.columnKind)).removesuffix("Column"),
            None if g.value(rn, DAL.columnSeparator) is None else str(g.value(rn, DAL.columnSeparator)),
        )) for rn in g.objects(node, DAL.resultColumn)), key=lambda x: x[0],
    )
    payload, shape = None, None
    pc = g.value(node, DAL.payloadContract)
    if pc is not None:
        root = g.value(pc, DAL.payloadRoot)
        payload = PayloadContract(param_names[g.value(pc, DAL.payloadParameter)], param_names.get(root))
        shape = _local(g.value(pc, DAL.boundaryShape)) if g.value(pc, DAL.boundaryShape) == DAL.NoBoundaryShape else str(g.value(pc, DAL.boundaryShape))
    digest = None
    dc = g.value(node, DAL.digestContract)
    if dc is not None:
        parts = {str(_local(g.value(dp, DAL.partRole))): set(g.objects(dp, DAL.partSource)) for dp in g.objects(dc, DAL.digestPart)}

        def names(role):
            return tuple(sorted(param_names[o] for o in parts.get(role, ()) if o != DAL.NoSource))

        single = lambda role: (names(role) or (None,))[0]
        digest = DigestContract(single("TargetPart"), single("ExpectedSeqPart"), single("PayloadPart"), names("EventPart"), single("AddPart"), single("DelPart"))
    contract = OperationContract(
        id=str(g.value(node, DAL.forOperation)), kind=OperationKind(_local(g.value(node, DAL.operationKind))),
        version=int(g.value(node, DAL.templateVersion)), guard_status=GuardStatus(_local(g.value(node, DAL.guardStatus))),
        graph_naming=GraphNaming(_local(naming)) if naming is not None else None, parameters=tuple(sorted(parameters)),
        accesses=tuple(sorted(accesses)), results=tuple(r for _, r in results), payload=payload, digest=digest,
        source=DeclarationSource(_local(g.value(node, DAL.declarationSource))),
    )
    return contract, shape


@dataclasses.dataclass(frozen=True)
class Intended:
    """A difference between an expected profile and the builders that is H2.7's design and not today's code."""

    stems: frozenset
    expected: frozenset
    builder: frozenset
    reason: str
    closes: str


INTENDED: tuple = ()
"""Empty since H2.6d, which closed the last intended difference (`$assertGraph` and `$retractGraph` under `dal:PatchLog`)."""


def _operations(example: str, options: dict):
    """(target, forOperation, node of the fresh compile, the builder's contract with its shape) for every generated operation."""
    compiled, targets = compile_to_graph(witness._load_fixture(ep.EXAMPLES / f"{example}.ttl"))
    by_target = {URIRef(str(t.target.cls)): t for t in targets}
    for profile in compiled.subjects(RDF.type, DAL.CompiledProfile):
        target = compiled.value(profile, DAL.forTarget)
        receipt_model = _local(by_target[target].dimensions["receiptModel"].value)
        shape = ep._shape_of(by_target[target])
        for node in compiled.objects(profile, DAL.generatedOperation):
            contract = ep.contract_for(compiled, node, guards=options.get("guards", True), graph_names=options.get("graph_names", "query"))
            yield target, str(compiled.value(node, DAL.forOperation)), compiled.value(compiled.value(node, DAL.usesTemplate), DAL.templateId), ep.designed(contract, receipt_model), contract, shape


def _differences(path: Path, parsed: dict):
    """(operation key, template stem, facts only in the file, facts only from the builder) for every operation."""
    name = _name(path)
    example, options = CONFIG[name]
    g = parsed[name]
    nodes = {(g.value(p, DAL.forTarget), str(g.value(n, DAL.forOperation))): n for p in g.subjects(RDF.type, DAL.CompiledProfile) for n in g.objects(p, DAL.generatedOperation)}
    seen = 0
    for target, operation, template_id, designed, builder, shape in _operations(example, options):
        file_contract, file_shape = _read_contract(g, nodes[(target, operation)])
        stem = str(template_id).removesuffix(".mustache")
        # the file states the designed contract, so the outcomes are: equal to the designed contract, and the designed one is
        # equal to or intentionally different from the builder
        assert _facts(file_contract, file_shape) == _facts(designed, str(shape) if shape else None), (name, operation)
        only_file = _facts(designed, str(shape) if shape else None) - _facts(builder, str(shape) if shape else None)
        only_builder = _facts(builder, str(shape) if shape else None) - _facts(designed, str(shape) if shape else None)
        seen += 1
        yield (target, operation), stem, only_file, only_builder
    assert seen == len(nodes), (name, seen, len(nodes))


@pytest.mark.parametrize("path", PROFILES, ids=_name)
def test_h2_6_t4_every_operation_of_an_expected_profile_equals_what_the_builder_gives_or_is_listed_as_intended(path, parsed):
    """Three outcomes: equal, an intended difference (listed with its reason and the slice that closes it), or a failure."""
    outcomes = {"equal": 0, "intended": 0}
    for key, stem, only_file, only_builder in _differences(path, parsed):
        if not only_file and not only_builder:
            outcomes["equal"] += 1
            continue
        row = next((r for r in INTENDED if stem_of(stem) in r.stems and r.expected == only_file and r.builder == only_builder), None)
        assert row is not None, f"{key}: only in the file {sorted(only_file, key=str)}, only from the builder {sorted(only_builder, key=str)}"
        outcomes["intended"] += 1
    assert outcomes["equal"] > 0


def test_h2_6_t5_every_intended_difference_is_used_and_the_value_guard_is_declared_by_hand(parsed):
    used = set()
    for path in PROFILES:
        for _, stem, only_file, only_builder in _differences(path, parsed):
            for row in INTENDED:
                if stem_of(stem) in row.stems and row.expected == only_file and row.builder == only_builder:
                    used.add(row.reason)
    assert used == {row.reason for row in INTENDED}  # a row nothing uses is removed, and H2.7 empties the table
    g = parsed["value-based-cas"]
    sources = {_local(o) for o in g.objects(None, DAL.declarationSource)}
    assert "HandDeclared" in sources and "BuilderDerived" in sources
    hand = [n for n in g.subjects(DAL.declarationSource, DAL.HandDeclared)]
    assert len(hand) == 1 and _local(g.value(hand[0], DAL.guardStatus)) == "NotGenerated"
    assert all(HAND_DECLARED[k].source is DeclarationSource.HAND_DECLARED for k in HAND_DECLARED)


@pytest.mark.parametrize("stem", ["create-if-absent-composite", "cas-replace-composite-property", "tombstone-delete-composite"])
def test_h2_6_t6_a_composite_dataset_guard_variant_differs_from_its_base_by_the_dataset_read_alone(stem):
    """The expected profiles have no composite dataset-guard variant, so this is the claim that makes the omission acceptable."""
    _, _, _, context = _first(stem)
    base = contract_of(build(stem, context))
    variant = contract_of(build(stem + DATASET_GUARD_SUFFIX, context))
    assert set(variant.accesses) - set(base.accesses) == {AccessContract("DatasetEpoch", "PointRead", None)}
    assert set(base.accesses) <= set(variant.accesses)
    assert dataclasses.replace(variant, id=base.id, accesses=base.accesses) == base


# ---- the names ------------------------------------------------------------------------------------------------------------

_DOLLAR = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


@pytest.mark.parametrize("graph_names", ["query", "caller"])
@pytest.mark.parametrize("stem", sorted(BUILDERS))
def test_h2_6_t7_the_declared_parameter_names_are_the_dollar_names_of_the_rendered_query(stem, graph_names):
    from persistence.ir_render import render

    _, _, _, context = _first(stem)
    operation = build(stem, context, graph_names=graph_names)
    declared = {p.name for p in operation.params if p.kind not in SLOT_KINDS}
    text = re.sub(r"\{\{\{.*?\}\}\}", "", render(operation))
    assert declared == set(_DOLLAR.findall(text))
    assert {p.name for p in contract_of(operation).parameters} == {p.name for p in operation.params}


def test_h2_6_t8_the_value_guards_declared_names_are_the_dollar_names_of_its_template():
    """The H-D11 convention, kept until TD-43 gives the operation a builder."""
    text = re.sub(r"\{\{!.*?\}\}", "", load_template("cas-replace-value-guard.mustache"), flags=re.S)
    assert {p.name for p in HAND_DECLARED["cas-replace-value-guard"].parameters} == set(_DOLLAR.findall(re.sub(r"\{\{\{.*?\}\}\}", "", text)))


# ---- minted IRIs -----------------------------------------------------------------------------------------------------------


def _declaration_nodes(graph: Graph) -> set:
    return {s for s in graph.subjects() if ep.is_declaration(s)}


def _new_triples(graph: Graph, example: str) -> set:
    """The triples an expected profile has beyond today's compiled profile (with its template paths, which the file drops)."""
    compiled, _ = compile_to_graph(witness._load_fixture(ep.EXAMPLES / f"{example}.ttl"))
    return {t for t in graph if t not in compiled and t[1] != DAL.templatePath}


@pytest.mark.parametrize("name", ["baseline-single-class", "composite-project-ownership", "uniqueness-merge-policy"])
def test_h2_6_t9_two_compiles_give_the_same_new_triples_whatever_order_the_configuration_was_loaded_in(name):
    """Every node of a new part is an IRI, so the new triples are the same set each time. The only blank nodes among them are
    the operation nodes of the base profile, whose labels H1.5 made stable."""
    example, options = CONFIG[name]
    source = witness._load_fixture(ep.EXAMPLES / f"{example}.ttl")
    triples = sorted(source, key=str)

    def shuffled(seed: int) -> Graph:
        order = list(triples)
        random.Random(seed).shuffle(order)
        g = Graph()
        for t in order:
            g.add(t)
        return g

    graphs = [ep.emit(example, source=s, **options) for s in (shuffled(1), shuffled(2), None)]
    news = [_new_triples(g, example) for g in graphs]
    assert news[0] and news[0] == news[1] == news[2]
    compiled, _ = compile_to_graph(witness._load_fixture(ep.EXAMPLES / f"{example}.ttl"))
    base_nodes = {n for t in compiled for n in t if isinstance(n, BNode)}
    for s, p, o in news[0]:
        assert not isinstance(o, BNode), (s, p, o)
        assert isinstance(s, URIRef) or s in base_nodes, (s, p, o)
    assert _declaration_nodes(graphs[0]) == _declaration_nodes(graphs[1]) == _declaration_nodes(graphs[2])


def test_h2_6_t10_a_declaration_node_added_as_a_blank_node_is_caught_by_the_minting_rule(parsed):
    """The rule of test_h2_6_t2 fails a blank-node object, so a builder that wrote one would not pass."""
    g = Graph()
    for t in parsed["baseline-single-class"]:
        g.add(t)
    op = next(g.objects(None, DAL.operationKind) and g.subjects(DAL.operationKind, None))
    g.add((op, DAL.parameter, BNode()))
    assert any(isinstance(o, BNode) for s, p, o in g if p in ep.NEW_PREDICATES)


# ---- the enumerations ------------------------------------------------------------------------------------------------------


def test_h2_6_t11_every_class_and_individual_a_profile_names_is_declared_in_the_enumerations_file(parsed):
    kinds = parsed[ep.KINDS_FILE]
    classes = set(kinds.subjects(RDF.type, RDFS.Class))
    individuals = {s for s, c in kinds.subject_objects(RDF.type) if c != RDFS.Class}
    used_classes, used = set(), set()
    for name in CONFIG:
        for s, p, o in parsed[name]:
            if (ep.is_declaration(s) or p in ep.NEW_PREDICATES) and isinstance(o, URIRef) and str(o).startswith(str(DAL)):
                (used_classes if p == RDF.type else used).add(o)
    assert used_classes and used_classes <= classes, sorted(str(u) for u in used_classes - classes)
    assert used and used <= individuals, sorted(str(u) for u in used - individuals)
    for resource in ep.ResourceKind:
        assert (DAL[resource.value], DAL.logicalKey, None) in kinds
