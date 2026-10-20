# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.1: the IR renders to SPARQL that parses as exactly one operation, from any valid value and any
adversarial constant (formal-methods track H, ADR-A123). Validation Pack: docs/developer/validation/FMH-H2-1.md.
Test IDs are H2.1-Tn."""

from __future__ import annotations

import random
from dataclasses import replace
import pathlib

import pytest
from rdflib import XSD, Dataset, Literal as RdfLiteral, URIRef
from rdflib.plugins.sparql.algebra import translateQuery, translateUpdate
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate

from persistence.ir import (
    GUARDS_OFF, A, Bind, Binding, Compare, Const, Filter, Func, Graph, GraphBlock, GraphRole, Group, Kind, Not, NotExists, Op,
    Operation, Optional_, Param, ParamRef, PayloadSlot, Path, Projected, RegistrySlot, Select, TermGuard, Triple,
    Union_, ValueGuard, Values, Var,
)
from persistence.ir_render import AGGREGATES, FUNCTIONS, access_sets, render
from persistence.paths import Alt, Star, Step
from persistence.terms import Iri, Literal, PropertyPath, SparqlTermError
from persistence.templatecheck import _SLOT_STAND_INS

from ir_fixtures import (
    DATA, EPOCH, EXPECTED, META, NEXT, PARAMS, REV, ROOT, TXN, TXN_ID, XSD_LONG, delete, insert, integer, iri, pat,
    string, true, valid, where,
)

GOLDEN = pathlib.Path(__file__).parent / "fixtures" / "ir" / "base-operation.rq"
P = lambda name: pat(name)
PATH = Path(PropertyPath.encode(Star(Alt((Step(URIRef("urn:p:owns")), Step(URIRef("urn:p:has"), inverse=True))))))


def filled(text: str) -> str:
    """Fill the request-time slots with stand-ins, so the text is SPARQL."""
    for name, stand_in in _SLOT_STAND_INS.items():
        text = text.replace("{{{" + name + "}}}", stand_in)
    return text


def parsed(text: str) -> int:
    """Parse and translate ``text``. Returns the number of top-level operations of an update, and 1 for a query."""
    text = filled(text)
    if text.lstrip().startswith(("SELECT", "PREFIX")) and "\nSELECT" in "\n" + text:
        translateQuery(parseQuery(text))
        return 1
    request = parseUpdate(text)
    translateUpdate(request)
    return len(request.request)


# ---- every renderable form parses -----------------------------------------------------------------


def _registry_audit() -> Operation:
    log = Var("log")
    return Operation.build(
        "audit-registry",
        (Param("logGraphs", Kind.REGISTRY_LIST),),
        Group((
            Values(log, (iri("urn:g:pinned"), RegistrySlot("logGraphs"))),
            GraphBlock(Graph(GraphRole.LOG, log), (Triple(Var("rev"), A, P("Revision")), Triple(Var("rev"), P("txn"), Var("t")))),
        )),
        select=Select(
            (Var("t"), Projected(Func("COUNT", (Var("rev"),), distinct=True), Var("n")), Projected(Func("GROUP_CONCAT", (Func("STR", (Var("rev"),)),), separator=" "), Var("revs")),
             Projected(Func("MIN", (Var("rev"),)), Var("first")), Projected(Func("MAX", (Var("rev"),)), Var("last")),
             Projected(Func("SAMPLE", (Var("rev"),)), Var("any_rev"))),
            (Var("t"),),
            (ValueGuard(">", Func("COUNT", (Var("rev"),), distinct=True), integer(1)),),
        ),
    )


def _value_audit() -> Operation:
    seq, low, high = (Var(n, Kind.LONG, Compare.VALUE) for n in ("seq", "L", "S"))
    return Operation.build(
        "audit-values", (),
        Group((
            GraphBlock(META, (Triple(Var("target"), A, P("VersionRow")), Triple(Var("target"), P("seq"), high))),
            Optional_(Group((GraphBlock(graph_(GraphRole.RETENTION, "retention"), (Triple(Var("target"), P("lwm"), Var("lwm")),)),))),
            Bind(Func("COALESCE", (Var("lwm"), Const(Literal.encode("1", datatype=XSD_LONG)))), low),
            Optional_(Group((GraphBlock(graph_(GraphRole.LOG, "log"), (Triple(Var("r"), P("seq"), seq),)), Filter(Op("&&", ValueGuard(">=", seq, low), ValueGuard("<=", seq, high))))))
        )),
        select=Select(
            (Var("target"), Projected(Func("COUNT", (seq,), distinct=True), Var("n"))),
            (Var("target"), high, low),
            (ValueGuard("!=", Func("COUNT", (seq,), distinct=True), Op("+", Op("-", high, low), integer(1))),),
        ),
    )


def graph_(role: GraphRole, name: str) -> Graph:
    return Graph(role, iri(f"urn:g:{name}"))


def _functions() -> Operation:
    r = ROOT
    arguments = {
        "IRI": (Func("STR", (r,)),), "CONCAT": (string("a"), string("b")), "STR": (r,), "ENCODE_FOR_URI": (Func("STR", (r,)),),
        "SUBSTR": (string("abc"), integer(1), integer(2)), "STRLEN": (string("abc"),),
        "STRDT": (string("1"), Const(Iri.encode(XSD_LONG))), "COALESCE": (Var("missing"), string("d")),
        "BOUND": (Var("missing"),), "DATATYPE": (string("a"),), "NOW": (), "ISIRI": (r,), "ISLITERAL": (string("a"),), "LANG": (string("a"),),
    }
    assert set(arguments) == set(FUNCTIONS)
    binds = tuple(Bind(Func(name, args), Var(f"f_{name.lower()}")) for name, args in arguments.items())
    return Operation.build("functions", (Param("root", Kind.IRI),), Group((GraphBlock(META, (Triple(r, P("p"), Var("missing")),)), *binds)), select=Select((Var("f_str"),)))


FORMS: dict[str, Operation] = {
    "replace-shape": valid(),
    "no-guard": replace(valid(), guard=GUARDS_OFF),
    "insert-only": Operation.build("ins", (Param("t", Kind.IRI),), Group((NotExists(Group((GraphBlock(META, (Triple(ParamRef("t"), P("seq"), Var("any")),)),))),)), insert=(GraphBlock(META, (Triple(ParamRef("t"), A, P("VersionRow")),)),)),
    "no-required-parameter": Operation.build("ins0", (Param("t", Kind.IRI, required=False),), Group(()), insert=(GraphBlock(META, (Triple(ParamRef("t"), A, P("VersionRow")),)),)),
    "property-path": Operation.build("path", (Param("root", Kind.IRI),), Group((GraphBlock(DATA, (Triple(ParamRef("root"), PATH, Var("s")), Triple(Var("s"), Var("p"), Var("o")))),)), delete=(GraphBlock(DATA, (Triple(Var("s", binding=Binding.BOUND), Var("p", binding=Binding.BOUND), Var("o", binding=Binding.BOUND)),)),)),
    "union": Operation.build("union", (Param("root", Kind.IRI),), Group((Union_((Group((GraphBlock(META, (Triple(ParamRef("root"), P("a"), Var("x")),)),)), Group((GraphBlock(META, (Triple(ParamRef("root"), P("b"), Var("x")),)),)))),)), select=Select((Var("x"),))),
    "nested-group": Operation.build("group", (Param("root", Kind.IRI),), Group((Group((GraphBlock(META, (Triple(ParamRef("root"), P("a"), Var("x")),)),)),)), select=Select((Var("x"),))),
    "term-and-value-guards": valid(where_=(*where(), Filter(Op("&&", TermGuard(EXPECTED, NEXT), Not(TermGuard(EXPECTED, NEXT, negated=True)))), Filter(ValueGuard("!=", ROOT, REV)))),
    "registry-audit": _registry_audit(),
    "value-audit": _value_audit(),
    "every-function": _functions(),
}


@pytest.mark.parametrize("name", sorted(FORMS))
def test_h2_1_t10_every_renderable_form_parses_as_one_operation(name):
    assert parsed(render(FORMS[name])) == 1


def test_h2_1_t11_the_forms_cover_every_function_and_aggregate():
    text = "".join(render(op) for op in FORMS.values())
    for name in (*FUNCTIONS, *AGGREGATES):
        assert name + "(" in text, name


# ---- the shape of the text ------------------------------------------------------------------------


def test_h2_1_t12_slots_render_as_plain_text_markers_and_variables_as_dollar_names():
    text = render(valid())
    assert "{{{payloadTriples}}}" in text
    assert "$root" in text and "?root" not in text


def test_h2_1_t13_the_rendering_of_the_base_operation_is_pinned():
    assert render(valid()) == GOLDEN.read_text(encoding="utf-8")


def test_h2_1_t14_two_renderings_are_byte_identical_and_prefixes_are_declared_once():
    assert render(valid()) == render(valid())
    assert render(valid()).count("PREFIX pat:") == 1


def test_h2_1_t15_the_guard_is_exactly_one_group_holding_one_filter_at_the_top_of_where():
    with_guard = render(valid()).splitlines()
    without = render(replace(valid(), guard=GUARDS_OFF)).splitlines()
    top = with_guard.index("WHERE {") + 1
    added = with_guard[top:top + 3]
    assert added[0] == "  {" and added[1].startswith("    FILTER(ISIRI($root)") and added[2] == "  }"
    assert with_guard[:top] + with_guard[top + 3:] == without


# ---- the guard does what it says (TD-34) ------------------------------------------------------------

_TARGET = URIRef("urn:test:target")


def _bootstrap() -> Operation:
    t = ParamRef("target")
    return Operation.build(
        "bootstrap",
        (Param("target", Kind.IRI), Param("epoch", Kind.LONG)),
        Group((NotExists(Group((GraphBlock(META, (Triple(t, P("seq"), Var("any")),)),))),)),
        insert=(GraphBlock(META, (Triple(t, A, P("VersionRow")), Triple(t, P("epoch"), ParamRef("epoch")), Triple(t, P("seq"), Const(Literal.encode("0", datatype=XSD_LONG))))),),
    )


def _run(op: Operation, **bindings) -> set:
    ds = Dataset()
    ds.update(render(op), initBindings=bindings)
    return {(str(s), str(p), str(o)) for s, p, o, _ in ds.quads((None, None, None, URIRef("urn:g:meta")))}


def test_h2_1_t16_with_every_parameter_bound_the_operation_writes_the_whole_record():
    rows = _run(_bootstrap(), target=_TARGET, epoch=RdfLiteral(3, datatype=XSD.long))
    assert len(rows) == 3


@pytest.mark.parametrize("bindings", [
    {"epoch": RdfLiteral(3, datatype=XSD.long)},
    {"target": _TARGET},
    {"target": _TARGET, "epoch": RdfLiteral(3)},
    {"target": _TARGET, "epoch": RdfLiteral("3")},
    {"target": RdfLiteral("urn:test:target"), "epoch": RdfLiteral(3, datatype=XSD.long)},
], ids=["no target", "no epoch", "epoch as xsd:integer", "epoch as a string", "target as a literal"])
def test_h2_1_t17_a_missing_or_mistyped_parameter_writes_nothing(bindings):
    assert _run(_bootstrap(), **bindings) == set()


def test_h2_1_t18_without_the_guard_a_missing_parameter_writes_part_of_the_record():
    rows = _run(replace(_bootstrap(), guard=GUARDS_OFF), target=_TARGET)
    assert 0 < len(rows) < 3  # the partial write TD-34 records


# A parameter that WHERE also matches. Left unbound, `$root pat:seq $expectedSeq` binds ?root from the data, so
# a guard written as a top-level FILTER, which applies after the group's patterns, would pass for every root.


def _replace_shaped() -> Operation:
    root, expected, nxt = ParamRef("root"), ParamRef("expectedSeq"), ParamRef("nextSeq")
    return Operation.build(
        "replace-shaped",
        (Param("root", Kind.IRI), Param("expectedSeq", Kind.POSITION), Param("nextSeq", Kind.POSITION)),
        Group((GraphBlock(META, (Triple(root, P("seq"), expected),)),)),
        delete=(GraphBlock(META, (Triple(root, P("seq"), expected),)),),
        insert=(GraphBlock(META, (Triple(root, P("seq"), nxt),)),),
    )


def _two_aggregates(op: Operation, **bindings) -> dict:
    ds = Dataset()
    for root in ("urn:test:a", "urn:test:b"):
        ds.graph(URIRef("urn:g:meta")).add((URIRef(root), URIRef(str(P("seq").term)[1:-1]), RdfLiteral(0, datatype=XSD.long)))
    ds.update(render(op), initBindings=bindings)
    return {str(s): int(o) for s, _, o, _ in ds.quads((None, None, None, URIRef("urn:g:meta")))}


_SEQS = {"expectedSeq": RdfLiteral(0, datatype=XSD.long), "nextSeq": RdfLiteral(1, datatype=XSD.long)}


def test_h2_1_t25_a_missing_parameter_that_where_matches_writes_nothing():
    assert _two_aggregates(_replace_shaped(), **_SEQS) == {"urn:test:a": 0, "urn:test:b": 0}
    assert _two_aggregates(_replace_shaped(), root=URIRef("urn:test:a"), **_SEQS) == {"urn:test:a": 1, "urn:test:b": 0}


def test_h2_1_t25b_without_the_guard_a_missing_root_writes_every_aggregate():
    assert _two_aggregates(replace(_replace_shaped(), guard=GUARDS_OFF), **_SEQS) == {"urn:test:a": 1, "urn:test:b": 1}


# ---- derived read and write sets ----------------------------------------------------------------------


def test_h2_1_t19_read_and_write_sets_are_derived_from_the_patterns():
    sets = access_sets(valid())
    reads = {(a.role, a.subject) for a in sets.reads}
    writes = {(a.role, a.subject, a.predicate) for a in sets.writes}
    assert ("meta", "$root") in reads and ("txn", "$txnId") in reads
    assert ("data", "{payload}", "*") in writes
    assert ("log", "$newRev", "a") in writes
    assert not any(a.role == "log" for a in sets.reads)
    assert access_sets(valid()) == access_sets(replace(valid(), guard=GUARDS_OFF))


# ---- properties ------------------------------------------------------------------------------------------


def _random_operation(rng: random.Random) -> Operation:
    """A valid operation, valid by construction. Every snippet binds names of its own."""
    where_: list = []
    definite: list[str] = []
    possible: list[str] = []
    for k in range(rng.randint(0, 6)):
        choice = rng.choice(("triple", "optional", "not-exists", "bind", "filter", "path", "union", "values"))
        if choice == "triple":
            where_.append(GraphBlock(META, (Triple(ROOT, P(f"p{k}"), Var(f"v{k}")),)))
            definite.append(f"v{k}")
        elif choice == "optional":
            where_.append(GraphBlock(META, (Triple(ROOT, P(f"q{k}"), Var(f"w{k}")), Optional_(Group((Triple(ROOT, P(f"o{k}"), Var(f"o{k}")),))))))
            definite.append(f"w{k}")
            possible.append(f"o{k}")
        elif choice == "not-exists":
            where_.append(NotExists(Group((GraphBlock(TXN, (Triple(TXN_ID, P(f"n{k}"), Var(f"n{k}")),)),))))
        elif choice == "bind":
            fn = rng.choice(("STR", "IRI", "STRLEN", "ENCODE_FOR_URI"))
            arg = ROOT if fn != "IRI" else Func("STR", (ROOT,))
            where_.append(Bind(Func(fn, (Func("STR", (arg,)) if fn in ("STRLEN", "ENCODE_FOR_URI") else arg,)), Var(f"b{k}")))
            definite.append(f"b{k}")
        elif choice == "filter":
            where_.append(Filter(rng.choice((ValueGuard("!=", ROOT, REV), TermGuard(EXPECTED, NEXT), Op("||", TermGuard(EXPECTED, NEXT), ValueGuard("=", ROOT, REV))))))
        elif choice == "path":
            where_.append(GraphBlock(DATA, (Triple(ROOT, PATH, Var(f"s{k}")), Triple(Var(f"s{k}"), Var(f"p{k}"), Var(f"o{k}x")))))
            definite += [f"s{k}", f"p{k}", f"o{k}x"]
        elif choice == "union":
            where_.append(Union_((Group((GraphBlock(META, (Triple(ROOT, P(f"a{k}"), Var(f"u{k}")),)),)), Group((GraphBlock(META, (Triple(ROOT, P(f"b{k}"), Var(f"u{k}")),)),)))))
            definite.append(f"u{k}")
        else:
            where_.append(Values(Var(f"g{k}"), (iri(f"urn:g:v{k}"),)))
            where_.append(GraphBlock(Graph(GraphRole.LOG, Var(f"g{k}")), (Triple(ROOT, P(f"l{k}"), Var(f"l{k}")),)))
            definite += [f"g{k}", f"l{k}"]
    graphs = (META, TXN, DATA)
    template: list = []
    for name in definite:
        if rng.random() < 0.5:
            template.append(GraphBlock(rng.choice(graphs), (Triple(ROOT, P(f"t_{name}"), Var(name, binding=Binding.BOUND)),)))
    for name in possible:
        if rng.random() < 0.5:
            template.append(GraphBlock(rng.choice(graphs), (Triple(ROOT, P(f"t_{name}"), Var(name, binding=Binding.OPTIONAL_ALLOWED)),)))
    if rng.random() < 0.5:
        template.append(GraphBlock(DATA, (PayloadSlot("payloadTriples"),)))
    template.append(GraphBlock(META, (Triple(ROOT, P("seq"), NEXT),)))
    params = tuple(p for p in PARAMS if p.name in {"root", "expectedSeq", "nextSeq", "newRev", "txnId", "payloadTriples", "epoch"})
    extra = (GraphBlock(META, (Triple(ROOT, P("epoch"), EPOCH), Triple(ROOT, P("seq"), EXPECTED))),
             NotExists(Group((GraphBlock(TXN, (Triple(TXN_ID, P("rev"), REV),)),))),
             GraphBlock(META, (Triple(ROOT, P("head"), REV),)))
    payload_used = any(isinstance(e, PayloadSlot) for b in template for e in b.elements)
    if not payload_used:
        params = tuple(p for p in params if p.name != "payloadTriples")
    delete_ = (GraphBlock(META, (Triple(ROOT, P("seq"), NEXT),)),) if rng.random() < 0.5 else ()
    return Operation.build("random", params, Group((*extra, *where_)), insert=tuple(template), delete=delete_)


@pytest.mark.parametrize("seed", range(150))
def test_h2_1_t20_a_valid_operation_renders_deterministically_to_exactly_one_operation(seed):
    operation = _random_operation(random.Random(seed))
    text = render(operation)
    assert parsed(text) == 1
    assert render(operation) == text


_ALPHABET = list('"\'\\{}<>;.#?$ \n\t\r‮​%') + ["DROP ALL", "}; DROP ALL; INSERT {", "\\u0041", "\"\"\"", "# ", "<urn:x>", "{{{", "}}}"]


def _adversarial(rng: random.Random) -> str:
    return "".join(rng.choice(_ALPHABET + list("abc")) for _ in range(rng.randint(1, 12)))


@pytest.mark.parametrize("seed", range(100))
def test_h2_1_t21_an_adversarial_literal_stays_a_literal(seed):
    value = _adversarial(random.Random(seed))
    op = Operation.build(
        "label", (Param("root", Kind.IRI),), Group(()),
        insert=(GraphBlock(META, (Triple(ParamRef("root"), P("label"), Const(Literal.encode(value))),)),),
    )
    text = render(op)
    assert parsed(text) == 1
    ds = Dataset()
    ds.update(text, initBindings={"root": _TARGET})
    objects = [o for _, _, o, _ in ds.quads((None, None, None, URIRef("urn:g:meta")))]
    assert objects == [RdfLiteral(value)]


@pytest.mark.parametrize("seed", range(100))
def test_h2_1_t22_an_adversarial_iri_is_refused_or_stays_an_iri(seed):
    value = "urn:x:" + _adversarial(random.Random(seed))
    try:
        constant = Const(Iri.encode(value))
    except SparqlTermError:
        return
    op = Operation.build(
        "iri", (Param("root", Kind.IRI),), Group(()),
        insert=(GraphBlock(META, (Triple(ParamRef("root"), P("see"), constant),)),),
    )
    text = render(op)
    assert parsed(text) == 1
    ds = Dataset()
    ds.update(text, initBindings={"root": _TARGET})
    assert [o for _, _, o, _ in ds.quads((None, None, None, URIRef("urn:g:meta")))] == [URIRef(value)]



# ---- review fixes (2026-10-10) ---------------------------------------------------------------------------


def test_h2_1_t26_a_literal_that_looks_like_an_iri_is_rendered_unchanged():
    value = "<https://example.org/lattice/patterns#seq>"
    op = Operation.build(
        "label", (Param("root", Kind.IRI),), Group(()),
        insert=(GraphBlock(META, (Triple(ParamRef("root"), P("label"), Const(Literal.encode(value))),)),),
    )
    ds = Dataset()
    ds.update(render(op), initBindings={"root": _TARGET})
    assert [o for _, _, o, _ in ds.quads((None, None, None, URIRef("urn:g:meta")))] == [RdfLiteral(value)]
    typed = Const(Literal.encode("3", datatype=XSD_LONG))
    op = Operation.build(
        "typed", (Param("root", Kind.IRI),), Group(()),
        insert=(GraphBlock(META, (Triple(ParamRef("root"), P("n"), typed),)),),
    )
    assert '"3"^^xsd:long' in render(op)


def test_h2_1_t28_the_guard_survives_a_caller_that_substitutes_parameter_text():
    text = render(_replace_shaped())
    seqs = {"$expectedSeq": '"0"^^<http://www.w3.org/2001/XMLSchema#long>', "$nextSeq": '"1"^^<http://www.w3.org/2001/XMLSchema#long>'}
    substituted = text
    for name, term in seqs.items():
        substituted = substituted.replace(name, term)
    assert parsed(substituted.replace("$root", "<urn:test:a>")) == 1
    for root, expected in (("<urn:test:a>", {"urn:test:a": 1, "urn:test:b": 0}), (None, {"urn:test:a": 0, "urn:test:b": 0})):
        ds = Dataset()
        for r in ("urn:test:a", "urn:test:b"):
            ds.graph(URIRef("urn:g:meta")).add((URIRef(r), URIRef(str(P("seq").term)[1:-1]), RdfLiteral(0, datatype=XSD.long)))
        ds.update(substituted if root is None else substituted.replace("$root", root))
        assert {str(s): int(o) for s, _, o, _ in ds.quads((None, None, None, URIRef("urn:g:meta")))} == expected


def test_h2_1_t30_guards_can_be_turned_off_and_the_operation_says_so():
    op = Operation.build("off", (Param("root", Kind.IRI),), Group(()),
                         insert=(GraphBlock(META, (Triple(ParamRef("root"), A, P("VersionRow")),)),), guards=False)
    assert op.guard == GUARDS_OFF
    assert "FILTER" not in render(op) and parsed(render(op)) == 1


# ---- the scope the checker models is the scope an engine applies (review F4, corrected) ------------------
# SPARQL evaluates an inner group on its own and joins it afterwards. Only NOT EXISTS sees the enclosing group's
# values. Run on rdflib, so the checker's model of scope is tested against an engine.

_SCOPE = {
    "nested group": ("SELECT ?a ?b WHERE { BIND(1 AS ?a) { BIND(?a + 1 AS ?b) } }", [None]),
    "GRAPH block": ("SELECT ?a ?b WHERE { BIND(1 AS ?a) GRAPH <urn:g> { ?s ?p ?o BIND(?a + 1 AS ?b) } }", [None]),
    "OPTIONAL": ("SELECT ?a ?b WHERE { BIND(1 AS ?a) OPTIONAL { BIND(?a + 1 AS ?b) } }", [None]),
    "UNION branch": ("SELECT ?a ?b WHERE { BIND(1 AS ?a) { BIND(?a + 1 AS ?b) } UNION { BIND(5 AS ?b) } }", [None, 5]),
    "same group": ("SELECT ?a ?b WHERE { BIND(1 AS ?a) BIND(?a + 1 AS ?b) }", [2]),
}


@pytest.mark.parametrize("kind", sorted(_SCOPE))
def test_h2_1_t29_a_bind_sees_only_its_own_group_on_rdflib(kind):
    query, expected = _SCOPE[kind]
    ds = Dataset()
    ds.graph(URIRef("urn:g")).add((URIRef("urn:s"), URIRef("urn:p"), RdfLiteral(0)))
    assert sorted((None if row[1] is None else int(row[1]) for row in ds.query(query)), key=lambda v: (v is not None, v)) == expected


def test_h2_1_t29b_not_exists_sees_the_enclosing_group_on_rdflib():
    assert list(Dataset().query("SELECT ?a WHERE { BIND(1 AS ?a) FILTER NOT EXISTS { FILTER(?a = 1) } }")) == []



# ---- H2.3-Q2: a GRAPH ?g in an inner group, with ?g bound by an enclosing group -------------------------------
# The join restricts the result to ?g's triples. Run on rdflib, as the scope rule is (plan 5.1).

_JOIN = {
    "OPTIONAL": "OPTIONAL { GRAPH ?g { ?s ?p ?o } }",
    "nested group": "{ GRAPH ?g { ?s ?p ?o } }",
    "UNION branch": "{ GRAPH ?g { ?s ?p ?o } } UNION { GRAPH ?g { ?s ?p ?o } }",
}


@pytest.mark.parametrize("shape", sorted(_JOIN))
def test_h2_3_t2_a_graph_variable_bound_outside_restricts_an_inner_group_to_that_graph_on_rdflib(shape):
    ds = Dataset()
    ds.graph(URIRef("urn:g1")).add((URIRef("urn:s1"), URIRef("urn:p"), RdfLiteral(1)))
    ds.graph(URIRef("urn:g2")).add((URIRef("urn:s2"), URIRef("urn:p"), RdfLiteral(2)))
    rows = {str(row[0]) for row in ds.query("SELECT ?s WHERE { BIND(<urn:g1> AS ?g) " + _JOIN[shape] + " }") if row[0] is not None}
    assert rows == {"urn:s1"}
