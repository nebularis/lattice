# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.5, gate 2: the closed `SELECT` fragment of the typed IR, a sub-select as a pattern element, and what each engine does
with one (ADR-A123, addendum of 2026-10-13, and the plan 4.3). The refusals themselves are in `test_ir.py`, one per rule.
Validation Pack: docs/developer/validation/FMH-H2-5.md. Test IDs are H2.5-Tn."""

from __future__ import annotations

import random

import pytest
from rdflib import Literal as RdfLiteral, URIRef
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate

import engines
from persistence.builders import build
from persistence.ir import (
    A, Binding, Compare, Filter, Func, Graph, GraphBlock, GraphRole, Group, IrError, Kind, NotExists, Operation, Optional_,
    Param, ParamRef, Projected, Select, SubSelect, Triple, ValueGuard, Values, Var,
)
from persistence.ir_render import access_sets, check, render

from ir_fixtures import integer, iri, pat
from request_slots import fill_request_slots

U = URIRef
KEYS_GRAPH = Graph(GraphRole.KEYS, iri("urn:g:keys"))
CLAIM, OWNER, OTHER, N = Var("claim"), Var("owner"), Var("other"), Var("n")
CLAIMED = GraphBlock(KEYS_GRAPH, (Triple(CLAIM, pat("claimedBy"), OWNER),))


# ---- the boundness table (plan 4.3) ----------------------------------------------------------------------------------


def _count(alias: str = "n") -> Projected:
    return Projected(Func("COUNT", (OWNER,)), Var(alias))


def _inner(*, owner_possible: bool = False) -> Group:
    if owner_possible:
        return Group((
            GraphBlock(KEYS_GRAPH, (Triple(CLAIM, A, pat("KeyClaim")),)),
            Optional_(Group((CLAIMED,))),
        ))
    return Group((CLAIMED,))


def _writes(item_var: str, tag: Binding, select: Select, inner: Group) -> Operation:
    """An update whose template uses ``?item_var`` of a sub-select, so the checker decides whether the tag is right."""
    return Operation.build(
        "bound",
        (),
        Group((SubSelect(select, inner),)),
        insert=(GraphBlock(KEYS_GRAPH, (Triple(iri("urn:s"), pat("p"), Var(item_var, binding=tag)),)),),
    )


MIN = Projected(Func("MIN", (OWNER,)), Var("lowest"))
BY_CLAIM = (CLAIM,)

# (label, projected item and its name, group by, owner possibly unbound, bound in every solution)
_TABLE = [
    ("COUNT over a group", _count(), "n", BY_CLAIM, False, True),
    ("COUNT with no GROUP BY", _count(), "n", (), False, True),
    ("COUNT over a possibly unbound argument", _count(), "n", BY_CLAIM, True, True),
    ("MIN with a GROUP BY and a bound argument", MIN, "lowest", BY_CLAIM, False, True),
    ("MIN with no GROUP BY", MIN, "lowest", (), False, False),
    ("MIN with a GROUP BY and a possibly unbound argument", MIN, "lowest", BY_CLAIM, True, False),
    ("a scalar function of MIN with a GROUP BY", Projected(Func("IRI", (Func("MIN", (Func("STR", (OWNER,)),)),)), Var("lowest")), "lowest", BY_CLAIM, False, True),
    ("a scalar function of MIN with no GROUP BY", Projected(Func("IRI", (Func("MIN", (Func("STR", (OWNER,)),)),)), Var("lowest")), "lowest", (), False, False),
    ("a GROUP BY key bound by the pattern", CLAIM, "claim", BY_CLAIM, False, True),
    ("an expression over bound variables", Projected(Func("STR", (OWNER,)), Var("text")), "text", (), False, True),
    ("an expression over a possibly unbound variable", Projected(Func("STR", (OWNER,)), Var("text")), "text", (), True, False),
]


@pytest.mark.parametrize("label, item, name, group_by, possible, always", _TABLE, ids=[row[0] for row in _TABLE])
def test_h2_5_t5_a_projected_item_is_bound_in_every_solution_only_as_the_boundness_table_says(label, item, name, group_by, possible, always):
    select = Select((item,), group_by=group_by) if group_by or not isinstance(item, Var) else Select((item,))
    inner = _inner(owner_possible=possible)
    tagged_bound = _writes(name, Binding.BOUND, select, inner)
    tagged_optional = _writes(name, Binding.OPTIONAL_ALLOWED, select, inner)
    if always:
        check(tagged_bound)
        with pytest.raises(IrError) as caught:
            check(tagged_optional)
        assert caught.value.rule == "OptionalTagOnBoundVariable"
    else:
        with pytest.raises(IrError) as caught:
            check(tagged_bound)
        assert caught.value.rule == "UnboundTemplateVariable"
        check(tagged_optional)


def test_h2_5_t6_a_sub_select_starts_with_nothing_in_scope_so_a_graph_variable_bound_outside_is_refused_inside():
    """`GRAPH ?g` inside a sub-select cannot see a `?g` the enclosing group binds, since the sub-select is evaluated on its own."""
    inside = SubSelect(Select((CLAIM,), group_by=BY_CLAIM), Group((GraphBlock(Graph(GraphRole.LOG, Var("g")), (Triple(CLAIM, pat("p"), OWNER),)),)))
    operation = Operation.build(
        "scope", (), Group((Values(Var("g"), (iri("urn:g:x"),)), inside)),
        insert=(GraphBlock(KEYS_GRAPH, (Triple(Var("claim", binding=Binding.BOUND), pat("p"), iri("urn:o")),)),),
    )
    with pytest.raises(IrError) as caught:
        check(operation)
    assert caught.value.rule == "UnboundGraphVariable"


# ---- the walks enter a sub-select ------------------------------------------------------------------------------------


def test_h2_5_t7_the_read_and_write_sets_include_what_a_sub_select_reads_and_the_roles_hold_inside_it():
    from test_key_claims_and_audits import CONTEXT

    operation = build("key-claim-merge-rewrite", CONTEXT)
    sets = access_sets(operation)
    claimed = [a for a in sets.reads if a.predicate.endswith("claimedBy>")]
    assert {a.role for a in claimed} == {"keys"} and {a.subject for a in claimed} == {"?claim"}
    constraint = [a for a in sets.reads if a.predicate.endswith("constraint>")]
    assert constraint and all(a.role == "keys" for a in constraint)  # read only inside the sub-select
    assert {a.role for a in sets.writes} == {"keys"}
    quarantine = access_sets(build("key-claim-quarantine", CONTEXT))
    assert {a.role for a in quarantine.writes} == {"quarantine"} and {a.role for a in quarantine.reads} == {"keys", "quarantine"}


def test_h2_5_t8_the_guard_group_is_first_in_the_outer_where_and_never_inside_a_sub_select():
    inner = Group((CLAIMED, Filter(ValueGuard("!=", Var("owner", Kind.IRI), ParamRef("who")))))
    operation = Operation.build(
        "guarded", (Param("who", Kind.IRI),),
        Group((SubSelect(Select((CLAIM,), group_by=BY_CLAIM), inner),)),
        insert=(GraphBlock(KEYS_GRAPH, (Triple(Var("claim", binding=Binding.BOUND), pat("p"), ParamRef("who")),)),),
    )
    lines = render(operation).splitlines()
    where = lines.index("WHERE {")
    assert lines[where + 1].strip().startswith("{ FILTER(ISIRI($who))")
    assert sum("ISIRI($who)" in line for line in lines) == 1
    assert lines[where + 2].strip() == "{"
    assert lines[where + 3].strip() == "SELECT ?claim"


def test_h2_5_t9_a_query_operation_without_parameters_renders_no_guard():
    text = render(build("key-claim-duplicate-audit", __import__("test_key_claims_and_audits").CONTEXT))
    assert "FILTER(ISIRI" not in text and text.startswith("PREFIX pat:")


# ---- queries and sub-selects render and parse, whatever the shape (property test) ------------------------------------


def _random_select(rng: random.Random) -> Operation:
    """A valid `SELECT` or an update with a sub-select, valid by construction."""
    claim, owner = Var("claim"), Var("owner")
    extra = []
    for k in range(rng.randint(0, 3)):
        choice = rng.choice(("optional", "not-exists", "filter", "bind"))
        if choice == "optional":
            extra.append(Optional_(Group((GraphBlock(KEYS_GRAPH, (Triple(claim, pat(f"o{k}"), Var(f"o{k}")),)),))))
        elif choice == "not-exists":
            extra.append(NotExists(Group((GraphBlock(KEYS_GRAPH, (Triple(claim, pat(f"n{k}"), Var(f"n{k}")),)),))))
        elif choice == "filter":
            extra.append(Filter(ValueGuard("!=", Var("owner", Kind.IRI), iri("urn:o:1"))))
        else:
            extra.append(Filter(ValueGuard("=", Var("owner", Kind.IRI), iri(f"urn:o:{k}"))))
    keys_pattern = GraphBlock(KEYS_GRAPH, (Triple(claim, A, pat("KeyClaim")), Triple(claim, pat("claimedBy"), owner)))
    aggregate = rng.choice(("COUNT", "MIN", "MAX", "SAMPLE"))
    distinct = rng.random() < 0.5
    item = Projected(Func(aggregate, (owner,), distinct=distinct and aggregate == "COUNT"), Var("agg"))
    having = (ValueGuard(">", Func("COUNT", (owner,)), integer(rng.randint(0, 3))),) if rng.random() < 0.7 else ()
    select = Select((claim, item), group_by=(claim,), having=having, distinct=False)
    if rng.random() < 0.5:
        return Operation.build("random-query", (), Group((keys_pattern, *extra)), select=Select(
            (claim, item), group_by=(claim,), having=having, distinct=rng.random() < 0.3))
    sub = SubSelect(select, Group((keys_pattern, *extra)))
    bound_item = Var("agg", binding=Binding.BOUND) if aggregate == "COUNT" else Var("agg", binding=Binding.OPTIONAL_ALLOWED)
    if aggregate != "COUNT":
        bound_item = Var("agg", binding=Binding.BOUND)  # MIN, MAX and SAMPLE with a GROUP BY over a bound argument are bound
    return Operation.build(
        "random-sub-select", (), Group((sub, GraphBlock(KEYS_GRAPH, (Triple(claim, pat("claimedBy"), Var("other")),)))),
        insert=(GraphBlock(KEYS_GRAPH, (Triple(Var("claim", binding=Binding.BOUND), pat("seen"), bound_item),
                                         Triple(Var("claim", binding=Binding.BOUND), pat("with"), Var("other", binding=Binding.BOUND)))),),
    )


@pytest.mark.parametrize("seed", range(150))
def test_h2_5_t10_a_valid_query_or_sub_select_renders_deterministically_to_exactly_one_operation_that_parses(seed):
    operation = _random_select(random.Random(seed))
    text = fill_request_slots(render(operation))
    assert fill_request_slots(render(operation)) == text
    if operation.select is not None:
        assert len(parseQuery(text)) == 2  # the prologue and one query
        assert translateQuery(parseQuery(text)).algebra is not None
    else:
        assert len(parseUpdate(text).request) == 1


def test_h2_5_t11_the_property_test_generates_both_kinds_and_a_group_by_with_a_having():
    kinds = [(_random_select(random.Random(s)).select is not None) for s in range(150)]
    assert 40 < sum(kinds) < 110
    texts = [render(_random_select(random.Random(s))) for s in range(150)]
    assert any("HAVING" in t for t in texts) and any("GROUP BY" in t for t in texts) and any("SELECT DISTINCT" in t for t in texts)


# ---- what each engine does with a sub-select (TSD-Q8, TSD-Q9) ------------------------------------------------------------


def _scoped_dataset():
    ds = engines.dataset()
    ds.update(
        "INSERT DATA { GRAPH <urn:g1> { <urn:s1> <urn:p> 1 . <urn:s2> <urn:p> 2 } "
        "GRAPH <urn:g2> { <urn:s1> <urn:p> 1 . <urn:s2> <urn:p> 2 . <urn:s3> <urn:p> 3 } }"
    )
    return ds


def _count(ds, text: str, **bindings) -> int:
    return int(str(list(ds.query(text, initBindings=bindings))[0][0]))


@engines.each_engine
def test_h2_5_t12_what_a_sub_select_sees_of_the_variables_around_it():
    """SPARQL 1.1 evaluates a sub-select on its own, so `?s` inside it is a different variable from the `?s` the `VALUES`
    binds, and the count is of every subject (3). rdflib lets the outer binding in (1). That is why the `SubSelectLeak` rule
    refuses an inner variable that is also used outside without being projected, so no valid operation depends on it
    (TSD-15)."""
    ds = _scoped_dataset()
    text = "SELECT ?c WHERE { VALUES ?s { <urn:s1> } { SELECT (COUNT(*) AS ?c) WHERE { GRAPH <urn:g2> { ?s <urn:p> ?o } } } }"
    assert _count(ds, text) == (1 if engines.CURRENT == "rdflib" else 3)


@engines.each_engine
def test_h2_5_t13_a_sub_select_inside_a_graph_block_reads_that_graph_on_both_engines():
    """TSD-Q9. The checker passes the enclosing graph to the sub-select's patterns, so this must hold."""
    ds = _scoped_dataset()
    assert _count(ds, "SELECT ?c WHERE { GRAPH <urn:g1> { { SELECT (COUNT(*) AS ?c) WHERE { ?s ?p ?o } } } }") == 2
    assert _count(ds, "SELECT ?c WHERE { GRAPH <urn:g2> { { SELECT (COUNT(*) AS ?c) WHERE { ?s ?p ?o } } } }") == 3


_NOT_EXISTS = (
    "SELECT ?claim WHERE {{ {{ SELECT ?claim WHERE {{ GRAPH <urn:g:keys> {{ ?claim <urn:p> ?x }} }} GROUP BY ?claim }} "
    "FILTER NOT EXISTS {{ GRAPH <urn:g:keys> {{ ?claim <urn:claimedBy> ?other . FILTER(?other != {owner}) }} }} }}"
)


def _claims_not_held_by_another(ds, owner: str, *, substitute: bool) -> set:
    text = _NOT_EXISTS.format(owner=f"<{owner}>" if substitute else "$owner")
    bindings = {} if substitute else {"owner": U(owner)}
    return {str(row[0]) for row in ds.query(text, initBindings=bindings)}


@engines.each_engine
@pytest.mark.parametrize("substitute", [True, False], ids=["text", "initial binding"])
def test_h2_5_t14_a_filter_inside_not_exists_sees_a_parameter_and_a_sub_selects_projection(substitute):
    """TSD-Q8. `key-claim-write` and merge-rewrite rely on it. A claim held by someone else is excluded, one held by the owner
    or by nobody is kept, whether the parameter is put in the text or bound before the query runs."""
    ds = engines.dataset()
    keys = ds.graph(U("urn:g:keys"))
    for claim, owner in (("urn:c:mine", "urn:o:1"), ("urn:c:theirs", "urn:o:2"), ("urn:c:free", None)):
        keys.add((U(claim), U("urn:p"), RdfLiteral("x")))
        if owner:
            keys.add((U(claim), U("urn:claimedBy"), U(owner)))
    assert _claims_not_held_by_another(ds, "urn:o:1", substitute=substitute) == {"urn:c:mine", "urn:c:free"}
