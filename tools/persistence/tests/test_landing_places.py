# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The compiled profile states where each write lands, and the scopes its values came through (studio-visual-authoring SVA-P1a).

A write access has one `dal:landsIn`, a `dal:GraphPlace` with a role and a graph or a template, a patch log's two graphs are two accesses
told apart by `dal:patchDirection`, a key claim's access names its constraint, and the profile states the scopes that matched and the one
each resolved value won through."""

from __future__ import annotations

import pyshacl
import pytest
from rdflib import RDF, RDFS, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import SH

import expected_profiles as ep
from builder_goldens import CANONICAL_CONTEXT
from persistence.builders import BUILDERS, GRAPH_ROLES, build
from persistence.compiler import compile_targets, compile_to_graph
from persistence.contract import LOGICAL_KEYS, ResourceKind, contract_of
from persistence.contract_emit import GRAPH_ROLES as ROLE_INDIVIDUALS
from persistence.contract_emit import PROFILE_PART, mint, mint_place
from persistence.instantiate import build_operation
from persistence.ir import (
    A, Bind, Const, Func, GraphBlock, GraphRole, Kind, Operation, Param, ParamRef, Triple, Var,
)
from persistence.ir_render import term_text
from persistence.landing import PATCH_DIRECTIONS, PLACEHOLDERS, LandingError, Place, is_template_of_closed_set, write_places
from persistence.namespaces import DAL
from persistence.terms import Integer, Iri, Literal as Lit
from persistence.witness import SPEC_TTL

from conftest import EXAMPLES_DIR
from test_builders import _corpus

WRITES = {"Insert", "Delete"}
EXPECTED = {name: ep.emit(example, **options) for name, example, options in ep.CONFIGURATIONS}
SHAPES = Graph().parse(ep.OUT_DIR.parents[1] / "shapes" / "constraints.ttl", format="turtle")


def _name(term) -> str:
    return str(term).rsplit("#", 1)[-1]


def _accesses(profile: Graph):
    for node in profile.subjects(RDF.type, DAL.ResourceAccess):
        yield node, _name(profile.value(node, DAL.accessMode))


# ---- reading a graph out of an operation's expressions ---------------------------------------------------------------------------


def _operation(graph_term, *binds, params=(), role=GraphRole.DATA) -> Operation:
    """An operation that inserts one triple into one graph, which is all `write_places` reads."""
    block = GraphBlock(_graph(role, graph_term), (Triple(ParamRef("root"), A, Const(Iri.encode("urn:x:T"))),))
    return Operation(id="probe", params=(Param("root", Kind.IRI), Param("newRev", Kind.IRI), *params), where=_group(*binds), insert=_group(block))


def _graph(role, term):
    from persistence.ir import Graph as IrGraph

    return IrGraph(role, term)


def _group(*elements):
    from persistence.ir import Group

    return Group(tuple(elements))


def _place(graph_term, *binds, **kwargs) -> Place:
    op = _operation(graph_term, *binds, **kwargs)
    ((_, place),) = write_places(op, term_text).items()
    return place


def _iri(text):
    return Const(Iri.encode(text))


def _text(text):
    return Const(Lit.encode(text))


def _concat(*args):
    return Func("CONCAT", args)


ROOT_ENCODED = Func("ENCODE_FOR_URI", (Func("STR", (ParamRef("root"),)),))
MONTH = Func("SUBSTR", (Func("STR", (Func("NOW"),)), Const(Integer.encode(1)), Const(Integer.encode(7))))


def test_a_constant_graph_is_a_fixed_iri():
    assert _place(_iri("urn:g:facilities")) == Place("data", graph="urn:g:facilities")


def test_a_graph_bound_from_a_constant_prefix_and_the_root_is_a_template():
    bind = Bind(Func("IRI", (_concat(Func("STR", (_iri("urn:g:borrower/"),)), ROOT_ENCODED, _text("")),)), Var("g"))
    assert _place(Var("g"), bind) == Place("data", named="urn:g:borrower/{root}")


def test_the_new_revision_and_the_month_are_placeholders():
    add = Bind(Func("IRI", (_concat(Func("STR", (ParamRef("newRev"),)), _text("/add")),)), Var("addGraph"))
    log = Bind(Func("IRI", (_concat(Func("STR", (_iri("urn:g:txlog/"),)), MONTH),)), Var("logGraph"))
    assert _place(Var("addGraph"), add, role=GraphRole.PATCH) == Place("patch", named="{newRev}/add")
    assert _place(Var("logGraph"), log, role=GraphRole.LOG) == Place("log", named="urn:g:txlog/{month}")


def test_a_variable_bound_to_another_variable_is_followed():
    first = Bind(_iri("urn:g:txlog/2026-01"), Var("logGraph"))
    second = Bind(Var("logGraph"), Var("logGraph2"))
    assert _place(Var("logGraph2"), second, first, role=GraphRole.LOG) == Place("log", graph="urn:g:txlog/2026-01")


def test_a_caller_named_graph_is_the_rule_its_parameter_must_equal():
    rule = Func("IRI", (_concat(Func("STR", (_iri("urn:g:facility/"),)), ROOT_ENCODED, _text("")),))
    assert _place(ParamRef("g"), params=(Param("g", Kind.IRI, equals=rule),)) == Place("data", named="urn:g:facility/{root}")


@pytest.mark.parametrize(
    "term,binds,params,reason",
    [
        (ParamRef("g"), (), (Param("g", Kind.IRI),), "states no rule"),
        (Var("g"), (), (), "is not bound"),
        (Var("g"), (Bind(Func("IRI", (Func("STR", (ParamRef("root"),)),)), Var("g")),), (), "without being percent-encoded"),
        (Var("g"), (Bind(Func("IRI", (Func("ENCODE_FOR_URI", (Func("STR", (ParamRef("newRev"),)),)),)), Var("g")),), (), "only the root parameter"),
        (Var("g"), (Bind(Func("UCASE", (_text("urn:g:x"),)), Var("g")),), (), "the function UCASE"),
        (Var("g"), (Bind(Func("SUBSTR", (Func("STR", (Func("NOW"),)), Const(Lit.encode("a")), Const(Lit.encode("b")))), Var("g")),), (), "SUBSTR"),
        (Var("g"), (Bind(_text("urn:g:{x}"), Var("g")),), (), "holds a brace"),
        (Var("g"), (Bind(Func("IRI", (ParamRef("other"),)), Var("g")),), (Param("other", Kind.IRI),), "states no rule"),
    ],
    ids=["param-no-rule", "unbound-var", "unencoded-root", "encoded-new-rev", "other-function", "other-substr", "brace", "other-param"],
)
def test_a_graph_that_is_not_an_iri_or_a_template_of_the_closed_placeholders_is_refused(term, binds, params, reason):
    with pytest.raises(LandingError) as refused:
        _place(term, *binds, params=params)
    assert reason in str(refused.value) and refused.value.operation == "probe"


def test_the_placeholders_are_a_closed_set():
    assert PLACEHOLDERS == ("root", "newRev", "month")
    assert is_template_of_closed_set("urn:g:txlog/{month}") and is_template_of_closed_set("{newRev}/add") and is_template_of_closed_set("urn:g:x")
    assert not is_template_of_closed_set("urn:g:{id}") and not is_template_of_closed_set("{root, percent-encoded}")


def test_a_place_states_exactly_one_of_a_graph_and_a_template():
    with pytest.raises(ValueError):
        Place("data")
    with pytest.raises(ValueError):
        Place("data", graph="urn:g:x", named="{root}")


# ---- every builder ---------------------------------------------------------------------------------------------------------------


def test_the_directions_are_the_patch_variables_of_the_builders():
    assert set(PATCH_DIRECTIONS) == {name for name, role in GRAPH_ROLES.items() if role is GraphRole.PATCH}
    assert set(PATCH_DIRECTIONS.values()) == {"Added", "Removed"}


@pytest.mark.parametrize("stem", sorted(BUILDERS))
def test_every_write_access_of_a_builder_lands_in_a_place_and_no_read_does(stem):
    contract = contract_of(build(stem, dict(CANONICAL_CONTEXT)))
    for access in contract.accesses:
        written = access.mode in WRITES
        assert (access.place is not None) == written, (stem, access)
        assert (access.direction is not None) == (written and access.resource == ResourceKind.PATCH_CONTENT.value), (stem, access)
        if access.place is not None:
            assert is_template_of_closed_set(access.place.named) if access.place.named else True
            assert access.place.role in ROLE_INDIVIDUALS


def test_the_places_of_the_canonical_context_are_the_graphs_the_builders_name():
    named = contract_of(build("cas-replace-named-graph-delta-patch-log", dict(CANONICAL_CONTEXT)))
    assert {(a.resource, a.mode, a.place.role, a.place.text, a.direction) for a in named.accesses if a.place} == {
        ("Aggregate", "Insert", "data", "urn:g:orders/{root}/data", None),
        ("Aggregate", "Delete", "data", "urn:g:orders/{root}/data", None),
        ("PatchContent", "Insert", "patch", "{newRev}/add", "Added"),
        ("PatchContent", "Insert", "patch", "{newRev}/del", "Removed"),
        ("Receipt", "Insert", "log", "urn:g:txlog/{month}", None),
        ("TransactionClaim", "Insert", "txn", "urn:g:txn", None),
        ("VersionRow", "Insert", "meta", "urn:g:meta/17", None),
        ("VersionRow", "Delete", "meta", "urn:g:meta/17", None),
    }


def test_a_patch_log_states_its_added_and_removed_triples_as_two_accesses():
    contract = contract_of(build("cas-replace-named-graph-delta-patch-log", dict(CANONICAL_CONTEXT)))
    patches = [a for a in contract.accesses if a.resource == "PatchContent"]
    assert sorted((a.direction, a.place.named) for a in patches) == [("Added", "{newRev}/add"), ("Removed", "{newRev}/del")]
    assert "direction" in LOGICAL_KEYS[ResourceKind.PATCH_CONTENT]


# ---- the compiled profile --------------------------------------------------------------------------------------------------------


def _profile_places(profile: Graph, node):
    """The accesses of one compiled profile, with the place each lands in."""
    for op in profile.objects(node, DAL.generatedOperation):
        for access in profile.objects(op, DAL.access):
            yield access, profile.value(access, DAL.accessMode), list(profile.objects(access, DAL.landsIn))


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_each_write_access_of_a_profile_lands_in_one_place_and_each_place_is_stated_once(name):
    profile = EXPECTED[name]
    stated = set(profile.subjects(RDF.type, DAL.GraphPlace))
    used = set()
    for node in profile.subjects(RDF.type, DAL.CompiledProfile):
        target, deployment = profile.value(node, DAL.forTarget), profile.value(node, DAL.forDeployment)
        for access, mode, landed in _profile_places(profile, node):
            assert len(landed) == (1 if _name(mode) in WRITES else 0), (access, mode)
            for place in landed:
                graph, named = profile.value(place, DAL.inGraph), profile.value(place, DAL.inGraphNamed)
                role = _role_of(_name(profile.value(place, DAL.inGraphRole)))
                assert (graph is None) != (named is None)
                shape = Place(role, graph=str(graph)) if graph is not None else Place(role, named=str(named))
                assert place == mint_place(target, shape, deployment)
                used.add(place)
    assert stated and stated == used  # no place without an access, and no access in a place the profile does not state
    for place in stated:
        assert isinstance(place, URIRef) and len(list(profile.objects(place, DAL.inGraphRole))) == 1


def _role_of(individual: str) -> str:
    return next(role for role, name in ROLE_INDIVIDUALS.items() if name == individual)


def test_the_places_of_the_composite_example_are_the_ones_its_operations_name():
    profile = EXPECTED["composite-project-ownership"]
    found = {
        (_name(profile.value(p, DAL.inGraphRole)), str(profile.value(p, DAL.inGraph) or profile.value(p, DAL.inGraphNamed)), profile.value(p, DAL.inGraph) is not None)
        for p in profile.subjects(RDF.type, DAL.GraphPlace)
    }
    assert ("DataRole", "urn:g:projects", True) in found
    assert ("LogRole", "urn:g:txlog/{month}", False) in found
    assert ("TxnRole", "urn:g:txn", True) in found
    assert not any("{" in text for _, text, fixed in found if fixed)


def test_places_are_shared_by_every_access_that_lands_there():
    profile = EXPECTED["baseline-single-class"]
    by_place: dict = {}
    for node, mode in _accesses(profile):
        for place in profile.objects(node, DAL.landsIn):
            by_place.setdefault(place, []).append(node)
    log = next(p for p in by_place if str(p).endswith("place-log-urn%3Ag%3Atxlog%2F%7Bmonth%7D"))
    assert len(by_place[log]) > 3
    assert len(by_place) == len(set(profile.subjects(RDF.type, DAL.GraphPlace)))


def test_the_added_and_removed_triples_of_a_patch_log_are_two_accesses_and_two_places():
    profile = EXPECTED["baseline-single-class"]
    patch = [n for n, _ in _accesses(profile) if profile.value(n, DAL.resourceKind) == DAL.PatchContent]
    assert patch and all(profile.value(n, DAL.patchDirection) in (DAL.Added, DAL.Removed) for n in patch)
    assert {profile.value(profile.value(n, DAL.landsIn), DAL.inGraphNamed) for n in patch} == {Literal("{newRev}/add"), Literal("{newRev}/del")}
    assert not [n for n, _ in _accesses(profile) if profile.value(n, DAL.resourceKind) != DAL.PatchContent and (n, DAL.patchDirection, None) in profile]


def test_a_key_claim_access_names_the_constraint_it_serves():
    profile = EXPECTED["baseline-single-class"]
    claims = [n for n, _ in _accesses(profile) if profile.value(n, DAL.resourceKind) == DAL.KeyClaim]
    assert claims
    constraints = set(profile.objects(None, DAL.appliedUniquenessConstraint))
    assert constraints
    for node in claims:
        assert profile.value(node, DAL.forConstraint) in constraints
    assert not [n for n, _ in _accesses(profile) if profile.value(n, DAL.resourceKind) != DAL.KeyClaim and (n, DAL.forConstraint, None) in profile]


def test_a_profile_states_the_scopes_that_matched_and_the_one_each_value_won_through():
    source = _source("baseline-single-class")
    (compiled,) = [c for c in compile_targets(source) if str(c.target.cls).endswith("LoanApplication")]
    profile = EXPECTED["baseline-single-class"]
    node = next(p for p in profile.subjects(RDF.type, DAL.CompiledProfile) if str(profile.value(p, DAL.forTarget)).endswith("LoanApplication"))
    matched = set(profile.objects(node, DAL.matchedScope))
    assert matched and matched == {URIRef(s) for s in compiled.matched_scopes}
    for dim in profile.objects(node, DAL.resolvedDimension):
        through = set(profile.objects(dim, DAL.wonThrough))
        winner = profile.value(dim, DAL.wonBy)
        if winner is None:
            assert not through
            continue
        assert through and through <= matched
        assert through == set(source.objects(winner, DAL.appliesTo)) & matched


def _source(example: str) -> Graph:
    from persistence import witness

    return witness._load_fixture(EXAMPLES_DIR / f"{example}.ttl")


def test_a_scope_that_matches_and_wins_nothing_is_still_a_matched_scope():
    """`dal:matchedScope` is every scope that matched, whether or not a profile applied through it won (SVA-Q20)."""
    for name in ("baseline-single-class", "composite-project-ownership", "uniqueness-merge-policy"):
        profile = EXPECTED[name]
        for node in profile.subjects(RDF.type, DAL.CompiledProfile):
            won = {s for d in profile.objects(node, DAL.resolvedDimension) for s in profile.objects(d, DAL.wonThrough)}
            assert won <= set(profile.objects(node, DAL.matchedScope))


def test_the_same_compilation_gives_the_same_places():
    example = _source("composite-project-ownership")
    first, _ = compile_to_graph(example)
    second, _ = compile_to_graph(_source("composite-project-ownership"))
    places = lambda g: {(p, str(o)) for p in g.subjects(RDF.type, DAL.GraphPlace) for o in g.objects(p, DAL.inGraphNamed)}
    assert places(first) == places(second)
    assert set(first.subjects(RDF.type, DAL.GraphPlace)) == set(second.subjects(RDF.type, DAL.GraphPlace))


def test_mint_place_follows_the_profiles_other_declarations():
    target = URIRef("https://example.org/lending#LoanApplication")
    place = Place("log", named="urn:g:txlog/{month}")
    assert mint_place(target, place) == mint(target, PROFILE_PART, "place-log-urn%3Ag%3Atxlog%2F%7Bmonth%7D")
    deployment = URIRef("https://example.org/lending#LendingDeployment")
    assert mint_place(target, place, deployment) == mint(target, PROFILE_PART, "place-log-urn%3Ag%3Atxlog%2F%7Bmonth%7D", deployment)
    assert mint_place(target, Place("log", named="a")) != mint_place(target, Place("data", named="a"))


# ---- every compiled example, in both graph namings --------------------------------------------------------------------------------


def test_every_operation_of_every_compiling_example_has_places_a_template_or_an_iri_states():
    """The operations the corpus compiles, with the guards and the graph naming of each run, all state their places. A graph that cannot be
    stated raises `LandingError` and fails here, naming the operation and the graph."""
    seen = 0
    for _, compiled in _corpus():
        for node in compiled.subjects(RDF.type, DAL.GeneratedOperation):
            _, operation = build_operation(compiled, node)
            for place in write_places(operation, term_text).values():
                assert is_template_of_closed_set(place.named)
                seen += 1
    assert seen > 200


@pytest.mark.parametrize("graph_names", ["query", "caller"])
def test_a_caller_named_graph_is_the_same_place_as_the_query_named_one(graph_names):
    base, _ = compile_to_graph(_source("baseline-single-class"), graph_names="query")
    other, _ = compile_to_graph(_source("baseline-single-class"), graph_names=graph_names)
    assert set(base.subjects(RDF.type, DAL.GraphPlace)) == set(other.subjects(RDF.type, DAL.GraphPlace))
    assert {(p, o) for p in base.subjects(RDF.type, DAL.GraphPlace) for o in base.objects(p, DAL.inGraphNamed)} == {
        (p, o) for p in other.subjects(RDF.type, DAL.GraphPlace) for o in other.objects(p, DAL.inGraphNamed)
    }


# ---- the shapes ------------------------------------------------------------------------------------------------------------------


def _closed(shape: str, path: str) -> set[str]:
    prop = next(p for p in SHAPES.objects(DAL[shape], SH.property) if SHAPES.value(p, SH.path) == DAL[path])
    return {_name(x) for x in Collection(SHAPES, SHAPES.value(prop, SH["in"]))}


def test_the_shape_closes_a_place_s_role_to_the_eleven_roles_of_the_ir_less_derived_and_world():
    roles = {role.value for role in GraphRole} - {"derived", "world"}
    assert roles == set(ROLE_INDIVIDUALS)
    assert _closed("GraphPlaceShape", "inGraphRole") == set(ROLE_INDIVIDUALS.values())
    assert len(ROLE_INDIVIDUALS) == 11
    assert _closed("ResourceAccessShape", "patchDirection") == {"Added", "Removed"}


# ---- a place is a dal:LandingPlace, and a realisation states its own subclass -----------------------------------------------------

EX = Namespace("https://example.org/realisation#")
LANDS_IN_CLASS = "ClassConstraintComponent"


def _landing_report(place_types: str, *, with_vocabulary: bool = True) -> set[str]:
    """The local names of the components that report on the one write access, which lands in ``ex:place``.

    The data graph holds the access, the place typed as ``place_types`` says, a relational realisation's own subclass of
    ``dal:LandingPlace`` and, unless told not to, the vocabulary. SHACL's ``sh:class`` follows ``rdfs:subClassOf`` only through triples of the
    data graph, and every validation of a compiled profile here is run with ``inference="none"`` over a graph that holds the vocabulary."""
    data = Graph()
    if with_vocabulary:
        data.parse(SPEC_TTL, format="turtle")
    data.parse(
        data=f"""
        @prefix dal: <{DAL}> . @prefix ex: <{EX}> . @prefix rdfs: <{RDFS}> .
        ex:RelationalTable rdfs:subClassOf dal:LandingPlace .
        ex:Unrelated a <http://www.w3.org/2002/07/owl#Class> .
        <urn:example:access> a dal:ResourceAccess ; dal:resourceKind dal:Aggregate ; dal:accessMode dal:Insert ; dal:landsIn <urn:example:place> .
        <urn:example:place> a {place_types} .
        """,
        format="turtle",
    )
    data.bind("dal", DAL)
    _, report, _ = pyshacl.validate(data, shacl_graph=SHAPES, inference="none", advanced=True, allow_warnings=True)
    return {
        _name(report.value(result, SH.sourceConstraintComponent))
        for result in report.subjects(RDF.type, SH.ValidationResult)
        if report.value(result, SH.focusNode) == URIRef("urn:example:access")
    }


def test_a_graph_place_is_a_landing_place_through_the_vocabulary_and_passes_the_access_shape():
    assert (DAL.GraphPlace, RDFS.subClassOf, DAL.LandingPlace) in Graph().parse(SPEC_TTL, format="turtle")
    assert _landing_report("dal:GraphPlace ; dal:inGraphRole dal:DataRole ; dal:inGraph <urn:g:x>") == set()


def test_a_place_typed_by_another_subclass_of_landing_place_passes_the_access_shape_without_being_a_graph_place():
    assert _landing_report("ex:RelationalTable") == set()


def test_a_place_that_is_no_landing_place_fails_the_access_shape():
    assert _landing_report("ex:Unrelated") == {LANDS_IN_CLASS}


def test_a_place_typed_only_as_a_resource_fails_the_access_shape():
    assert _landing_report("<http://www.w3.org/2000/01/rdf-schema#Resource>") == {LANDS_IN_CLASS}


def test_the_subclass_axiom_is_carried_by_the_vocabulary_and_never_by_the_compiled_profile():
    """The compiled profile is not given a second ``rdf:type`` on each place, so a validation holds the vocabulary in its data graph."""
    assert _landing_report("dal:GraphPlace ; dal:inGraphRole dal:DataRole ; dal:inGraph <urn:g:x>", with_vocabulary=False) == {LANDS_IN_CLASS}
    for name, profile in EXPECTED.items():
        for place in profile.subjects(RDF.type, DAL.GraphPlace):
            assert set(profile.objects(place, RDF.type)) == {DAL.GraphPlace}, name
        assert (DAL.GraphPlace, RDFS.subClassOf, DAL.LandingPlace) not in profile, name
