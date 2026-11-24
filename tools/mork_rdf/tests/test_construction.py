# SPDX-License-Identifier: MPL-2.0
"""A graph construction compiled from the existing cases, and the two checks it adds (README §7.9)."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path

import pytest
from rdflib import Dataset, Graph

from mork_rdf import Severity, compile_scheme, run

FIXTURES = Path(__file__).parent / "fixtures"
SCHEME = "http://example.org/mapping#Supplier"
BASE = "http://example.org/out/"
AT = datetime(2026, 11, 24, tzinfo=timezone.utc)
SRC, TGT, REC, MM = (f"http://example.org/{n}" for n in ("src#", "tgt#", "records/", "mapping#"))
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
NODE = f"{BASE}order-supplier/Supplier/"
ENGINES = ["oxigraph", "rdflib"]

PREFIXES = f"""@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix src: <{SRC}> . @prefix tgt: <{TGT}> . @prefix mm: <{MM}> . @prefix rec: <{REC}> .
"""


def fixture(name: str) -> Graph:
    return Graph().parse(FIXTURES / name)


def keyed() -> Graph:
    return fixture("supplier-mapping.ttl")


def compiled(mapping: Graph):
    return compile_scheme(mapping, SCHEME, base=BASE, at=AT)


def variant(old: str, new: str) -> Graph:
    """The keyed fixture with one piece of its text replaced, so a break is one line of Turtle."""
    text = (FIXTURES / "supplier-mapping.ttl").read_text(encoding="utf-8")
    assert old in text
    return Graph().parse(data=text.replace(old, new), format="turtle")


def per_instance() -> Graph:
    """A node for each order, named from a hash of the order's identifier and the contract's key."""
    return variant("    mork:identityTemplateMapping mm:SupplierIdentity ;\n", '    mork:conceptName "order-supplier/Supplier" ;\n')


def name_required() -> Graph:
    """The name a required value as well as the code, so an order with the code and no name is excluded."""
    return variant("sh:property [ sh:path src:supplierCode ; sh:minCount 1 ] .",
                   "sh:property [ sh:path src:supplierCode ; sh:minCount 1 ] , [ sh:path src:supplierName ; sh:minCount 1 ] .")


def evaluate(engine: str, mapping, source: Graph) -> tuple[set, set]:
    """What the constructs write and the checks report on one engine, as (subject, property, value) and (code, focus,
    value). Oxigraph is the runner, and rdflib runs the same query text."""
    if engine == "oxigraph":
        out = run(mapping, source)
        return {(str(s), str(p), str(o)) for s, p, o in out.graph}, {(f.code, f.focus, f.value) for f in out.findings}
    dataset = Dataset()
    for t in source:
        dataset.default_graph.add(t)
    written = {(str(s), str(p), str(o)) for q in mapping.constructs for s, p, o in dataset.query(q.text)}
    rows = {(q.code, str(row["focus"]), None if row["value"] is None else str(row["value"])) for q in mapping.checks for row in dataset.query(q.text)}
    return written, rows


def rows(codes, reported) -> set:
    return {r for r in reported if r[0] in codes}


NODE_QUERY = f"""BASE <{BASE}>
CONSTRUCT {{ ?t3 <{RDF_TYPE}> <{TGT}Supplier> . ?f1 <{TGT}suppliedBy> ?t3 . }}
WHERE {{
  ?f1 <{RDF_TYPE}> <{SRC}Order> .
  FILTER (((EXISTS {{ ?f1 <{SRC}supplierCode> ?any2 . }})))
  ?f1 <{SRC}supplierCode> ?v4 .
  BIND (IRI(CONCAT("order-supplier/Supplier/", ENCODE_FOR_URI(STR(?v4)))) AS ?t3)
}}"""


# --- the compiled case -----------------------------------------------------------------------------------------------

def test_a_construction_compiles_with_the_existing_cases_to_a_node_a_link_and_a_query_for_each_value():
    mapping = compiled(keyed())
    assert [(f.code, f.severity) for f in mapping.findings] == [("MappingReview", Severity.WARNING)]
    node, code, name = mapping.constructs
    assert " ".join(node.text.split()) == " ".join(NODE_QUERY.split())
    assert [q.path[-1] for q in (node, code, name)] == [f"{MM}Map_Supplier", f"{MM}Map_Code", f"{MM}Map_Name"]
    # Each value's query inherits the node's frame, the guard and the identity, whole, so it writes for no instance the node excludes.
    for q in (code, name):
        assert "FILTER (((EXISTS { ?f1 <%ssupplierCode> ?any2 . })))" % SRC in q.text
        assert 'BIND (IRI(CONCAT("order-supplier/Supplier/", ENCODE_FOR_URI(STR(?v4)))) AS ?t3)' in q.text
    assert sorted(q.code for q in mapping.checks) == ["IdentityAmbiguous", "IdentityUnbound", "InstanceExcluded", "ValueDisagrees"]


@pytest.mark.parametrize("engine", ENGINES)
def test_each_order_with_a_code_links_to_its_supplier_and_orders_with_one_code_share_it(engine):
    written, reported = evaluate(engine, compiled(keyed()), fixture("supplier-source.ttl"))
    s1, s2 = NODE + "S1", NODE + "S2"
    assert written == {
        (s1, RDF_TYPE, TGT + "Supplier"), (s1, TGT + "code", "S1"), (s1, TGT + "name", "Acme Components"),
        (s2, RDF_TYPE, TGT + "Supplier"), (s2, TGT + "code", "S2"),
        (REC + "o1", TGT + "suppliedBy", s1), (REC + "o2", TGT + "suppliedBy", s1), (REC + "o3", TGT + "suppliedBy", s2),
    }
    # The order with no code contributes nothing and is named, with the value it lacks. Agreeing on a name reports nothing.
    assert rows({"InstanceExcluded", "ValueDisagrees", "IdentityUnbound"}, reported) == {("InstanceExcluded", REC + "o4", f"<{SRC}supplierCode>")}


@pytest.mark.parametrize("engine", ENGINES)
def test_a_guard_on_the_node_keeps_an_instance_whole_or_out_even_where_another_made_the_node(engine):
    """The first thing the case shows. The order o5 holds the key and lacks a required value, and o1 has made the node
    for the same key. o5 writes no link, no type and no value of its own, and is reported with the value it lacks."""
    source = Graph().parse(data=PREFIXES + """
rec:o1 a src:Order ; src:supplierCode "S1" ; src:supplierName "Acme Components" .
rec:o5 a src:Order ; src:supplierCode "S1" .
rec:o6 a src:Order ; src:supplierCode "S9" .
""", format="turtle")
    written, reported = evaluate(engine, compiled(name_required()), source)
    s1 = NODE + "S1"
    assert written == {(s1, RDF_TYPE, TGT + "Supplier"), (s1, TGT + "code", "S1"), (s1, TGT + "name", "Acme Components"),
                       (REC + "o1", TGT + "suppliedBy", s1)}
    assert rows({"InstanceExcluded"}, reported) == {("InstanceExcluded", REC + "o5", f"<{SRC}supplierName>"),
                                                    ("InstanceExcluded", REC + "o6", f"<{SRC}supplierName>")}
    assert not [r for r in written if r[0] in (REC + "o5", REC + "o6")]
    assert not NODE + "S9" in {r[0] for r in written}


@pytest.mark.parametrize("engine", ENGINES)
def test_an_instance_lacking_two_required_values_is_reported_for_each(engine):
    source = Graph().parse(data=PREFIXES + "rec:o7 a src:Order .\n", format="turtle")
    written, reported = evaluate(engine, compiled(name_required()), source)
    assert written == set()
    assert rows({"InstanceExcluded"}, reported) == {("InstanceExcluded", REC + "o7", f"<{SRC}supplierCode>"),
                                                    ("InstanceExcluded", REC + "o7", f"<{SRC}supplierName>")}


@pytest.mark.parametrize("engine", ENGINES)
def test_a_node_whose_instances_disagree_is_named_with_each_value(engine):
    source = Graph().parse(data=PREFIXES + """
rec:o1 a src:Order ; src:supplierCode "S1" ; src:supplierName "Acme Components" .
rec:o2 a src:Order ; src:supplierCode "S1" ; src:supplierName "Acme Ltd" .
rec:o3 a src:Order ; src:supplierCode "S2" ; src:supplierName "Zed" .
""", format="turtle")
    written, reported = evaluate(engine, compiled(keyed()), source)
    s1 = NODE + "S1"
    assert {(s1, TGT + "name", "Acme Components"), (s1, TGT + "name", "Acme Ltd")} <= written
    assert rows({"ValueDisagrees"}, reported) == {("ValueDisagrees", s1, "Acme Components"), ("ValueDisagrees", s1, "Acme Ltd")}


def test_the_key_itself_is_never_reported_as_a_disagreement():
    mapping = compiled(keyed())
    assert [q.mapping for q in mapping.checks if q.code == "ValueDisagrees"] == [f"{MM}Map_Name"]


# --- a node for each instance ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("engine", ENGINES)
def test_a_node_for_each_instance_merges_nothing_and_takes_no_review(engine):
    mapping = compiled(per_instance())
    assert not mapping.findings
    assert sorted(q.code for q in mapping.checks) == ["InstanceExcluded"]
    written, reported = evaluate(engine, mapping, fixture("supplier-source.ttl"))
    nodes = {s for s, p, o in written if p == RDF_TYPE}
    assert len(nodes) == 3 and all(n.startswith(BASE + "order-supplier/Supplier/") for n in nodes)
    linked = {s: o for s, p, o in written if p == TGT + "suppliedBy"}
    assert set(linked) == {REC + "o1", REC + "o2", REC + "o3"} and len(set(linked.values())) == 3
    assert reported == {("InstanceExcluded", REC + "o4", f"<{SRC}supplierCode>")}


def test_a_keyed_node_carries_the_mapping_review_and_a_node_for_each_instance_does_not():
    keyed_codes = {f.code: f for f in compiled(keyed()).findings}
    assert set(keyed_codes) == {"MappingReview"} and keyed_codes["MappingReview"].mapping == f"{MM}Map_Supplier"
    assert not any(f.code == "MappingReview" for f in compiled(per_instance()).findings)


def test_the_two_contracts_with_one_class_never_reach_one_node():
    other = variant('"order-supplier/Supplier/"', '"other-key/Supplier/"')
    source = fixture("supplier-source.ttl")
    first = {s for s, p, o in run(compiled(keyed()), source).graph if p.n3() == f"<{RDF_TYPE}>"}
    second = {s for s, p, o in run(compiled(other), source).graph if p.n3() == f"<{RDF_TYPE}>"}
    assert first and second and not {str(n) for n in first} & {str(n) for n in second}


# --- a key of several values -----------------------------------------------------------------------------------------

COMPOSITE = """mm:SupplierIdentity a mork:ConcatExpression ; mork:concatLeft mm:SupplierIdentity_l ; mork:concatRight mm:SupplierIdentity_x .
mm:SupplierIdentity_x a mork:ConcatExpression ; mork:concatLeft mm:SupplierIdentity_r ; mork:concatRight mm:SupplierIdentity_y .
mm:SupplierIdentity_l a mork:LiteralExpression ; mork:dataInline "order-supplier/Supplier/" .
mm:SupplierIdentity_r a mork:RefExpression ; mork:dataRef "<http://example.org/src#supplierCode>" .
mm:SupplierIdentity_y a mork:ConcatExpression ; mork:concatLeft mm:SupplierIdentity_s ; mork:concatRight mm:SupplierIdentity_z .
mm:SupplierIdentity_s a mork:LiteralExpression ; mork:dataInline "/" .
mm:SupplierIdentity_z a mork:RefExpression ; mork:dataRef "<http://example.org/src#supplierRegion>" .
"""


@pytest.mark.parametrize("engine", ENGINES)
def test_a_node_by_two_values_is_one_node_for_each_pair_and_a_value_with_a_slash_cannot_blur_the_pair(engine):
    text = (FIXTURES / "supplier-mapping.ttl").read_text(encoding="utf-8")
    head, _, rest = text.partition("mm:SupplierIdentity a ")
    tail = rest.split("\n\nmm:Map_Code", 1)[1]
    guard = head.replace("sh:property [ sh:path src:supplierCode ; sh:minCount 1 ] .",
                         "sh:property [ sh:path src:supplierCode ; sh:minCount 1 ] , [ sh:path src:supplierRegion ; sh:minCount 1 ] .")
    mapping = Graph().parse(data=guard + COMPOSITE + "\nmm:Map_Code" + tail, format="turtle")
    source = Graph().parse(data=PREFIXES + """
rec:a a src:Order ; src:supplierCode "A" ; src:supplierRegion "north" .
rec:b a src:Order ; src:supplierCode "A" ; src:supplierRegion "north" .
rec:c a src:Order ; src:supplierCode "A" ; src:supplierRegion "south" .
rec:d a src:Order ; src:supplierCode "A/north" ; src:supplierRegion "x" .
rec:e a src:Order ; src:supplierCode "A" .
""", format="turtle")
    written, reported = evaluate(engine, compiled(mapping), source)
    link = {s: o for s, p, o in written if p == TGT + "suppliedBy"}
    assert link[REC + "a"] == link[REC + "b"] == NODE + "A/north"
    assert len({link[REC + k] for k in "acd"}) == 3 and REC + "e" not in link
    assert ("IdentityUnbound", REC + "e", None) not in reported


# --- the same answer however the inputs are ordered ------------------------------------------------------------------

def test_a_construction_is_the_same_for_any_order_of_the_mapping_graph_and_of_the_source():
    mapping, source = keyed(), fixture("supplier-source.ttl")
    first = compiled(mapping)
    ran = run(first, source)
    triples, data = list(mapping), list(source)
    for seed in range(3):
        random.Random(seed).shuffle(triples)
        random.Random(seed).shuffle(data)
        shuffled, shuffled_source = Graph(), Graph()
        for t in triples:
            shuffled.add(t)
        for t in data:
            shuffled_source.add(t)
        again = compiled(shuffled)
        assert again.text() == first.text() and again.digest == first.digest
        assert set(run(again, shuffled_source).graph) == set(ran.graph)
        assert run(again, shuffled_source).findings == ran.findings


def test_the_dry_run_gives_each_new_finding_its_message():
    source = Graph().parse(data=PREFIXES + """
rec:o1 a src:Order ; src:supplierCode "S1" ; src:supplierName "A" .
rec:o2 a src:Order ; src:supplierCode "S1" ; src:supplierName "B" .
rec:o3 a src:Order .
""", format="turtle")
    findings = {f.code: f for f in run(compiled(keyed()), source).findings}
    assert "excludes" in findings["InstanceExcluded"].message and "different values" in findings["ValueDisagrees"].message
