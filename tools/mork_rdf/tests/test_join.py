# SPDX-License-Identifier: MPL-2.0
"""A join datum, the case that takes a node of a second class from the source by equality, and the checks it adds (README §7.10)."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path

import pytest
from rdflib import Dataset, Graph

from mork_rdf import Severity, compile_scheme, run

FIXTURES = Path(__file__).parent / "fixtures"
SCHEME = "http://example.org/mapping#OrderCustomer"
BASE = "http://example.org/out/"
AT = datetime(2026, 11, 24, tzinfo=timezone.utc)
SRC, TGT, REC, MM = (f"http://example.org/{n}" for n in ("src#", "tgt#", "records/", "mapping#"))
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
LINK = TGT + "placedFor"
ENGINES = ["oxigraph", "rdflib"]

PREFIXES = f"""@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix src: <{SRC}> . @prefix tgt: <{TGT}> . @prefix mm: <{MM}> . @prefix rec: <{REC}> .
"""


def fixture(name: str) -> Graph:
    return Graph().parse(FIXTURES / name)


def joined() -> Graph:
    return fixture("customer-mapping.ttl")


def variant(old: str, new: str) -> Graph:
    """The fixture with one piece of its text replaced, so a break is one line of Turtle."""
    text = (FIXTURES / "customer-mapping.ttl").read_text(encoding="utf-8")
    assert old in text
    return Graph().parse(data=text.replace(old, new), format="turtle")


def variants(*changes: tuple) -> Graph:
    """The fixture with several pieces of its text replaced."""
    text = (FIXTURES / "customer-mapping.ttl").read_text(encoding="utf-8")
    for old, new in changes:
        assert old in text
        text = text.replace(old, new)
    return Graph().parse(data=text, format="turtle")


def compiled(mapping: Graph):
    return compile_scheme(mapping, SCHEME, base=BASE, at=AT)


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


JOIN_CODES = {"InstanceExcluded", "JoinUnmatched", "JoinAmbiguous"}

JOIN_QUERY = f"""BASE <{BASE}>
CONSTRUCT {{ ?f1 <{LINK}> ?f2 . }}
WHERE {{
  ?f1 <{RDF_TYPE}> <{SRC}Order> .
  ?f1 <{SRC}customerCode> ?v3 .
  FILTER (((EXISTS {{ ?f1 <{SRC}customerCode> ?any4 . }})))
  ?f2 <{RDF_TYPE}> <{SRC}Customer> .
  ?f2 <{SRC}code> ?v3 .
  {{ SELECT ?f1 WHERE {{ ?f1 <{SRC}customerCode> ?v6 . FILTER (((EXISTS {{ ?f1 <{SRC}customerCode> ?any7 . }}))) ?f5 <{RDF_TYPE}> <{SRC}Customer> . ?f5 <{SRC}code> ?v6 . }} GROUP BY ?f1 HAVING (COUNT(DISTINCT ?f5) = 1) }}
}}"""


# --- the compiled case -----------------------------------------------------------------------------------------------

def test_a_join_compiles_to_one_construct_for_the_link_and_a_check_for_each_way_a_parent_can_miss():
    mapping = compiled(joined())
    assert [(f.code, f.severity) for f in mapping.findings] == [("MappingReview", Severity.WARNING)]
    (link,) = mapping.constructs
    assert " ".join(link.text.split()) == " ".join(JOIN_QUERY.split())
    assert link.path == (f"{MM}Map_Order", f"{MM}Map_Customer")
    assert sorted(q.code for q in mapping.checks) == ["InstanceExcluded", "JoinAmbiguous", "JoinUnmatched"]


def test_the_join_joins_on_a_shared_variable_so_an_engine_can_serve_it_from_an_index():
    text = compiled(joined()).constructs[0].text
    assert "FILTER (sameTerm" not in text and "?f2 <%scode> ?v3 ." % SRC in text


@pytest.mark.parametrize("engine", ENGINES)
def test_an_order_links_to_the_customer_its_code_names_and_each_way_to_miss_is_reported(engine):
    written, reported = evaluate(engine, compiled(joined()), fixture("customer-source.ttl"))
    # o1 and o2 name C1. Nothing else is written, no type and no value, since the customer is the source's own node.
    assert written == {(REC + "o1", LINK, REC + "c1"), (REC + "o2", LINK, REC + "c1")}
    assert rows(JOIN_CODES, reported) == {
        ("InstanceExcluded", REC + "o4", f"<{SRC}customerCode>"),  # holds no code, so it contributed nothing
        ("JoinUnmatched", REC + "o3", "C9"),                        # a code no customer holds, with the value
        ("JoinAmbiguous", REC + "o5", REC + "c3"),                  # a code two customers hold, each named
        ("JoinAmbiguous", REC + "o5", REC + "c4"),
    }


@pytest.mark.parametrize("engine", ENGINES)
def test_under_any_number_a_parent_links_to_each_match_and_nothing_is_ambiguous(engine):
    mapping = compiled(variant("mork:AtMostOneMatch", "mork:AnyNumberOfMatches"))
    assert sorted(q.code for q in mapping.checks) == ["InstanceExcluded", "JoinUnmatched"]
    written, reported = evaluate(engine, mapping, fixture("customer-source.ttl"))
    assert written == {(REC + "o1", LINK, REC + "c1"), (REC + "o2", LINK, REC + "c1"),
                       (REC + "o5", LINK, REC + "c3"), (REC + "o5", LINK, REC + "c4")}
    assert rows(JOIN_CODES, reported) == {("InstanceExcluded", REC + "o4", f"<{SRC}customerCode>"), ("JoinUnmatched", REC + "o3", "C9")}


@pytest.mark.parametrize("engine", ENGINES)
def test_on_candidate_evidence_a_parent_with_no_match_writes_nothing_and_is_not_reported(engine):
    mapping = compiled(variant(
        "    mork:appliesWhen mm:CustomerGuard ;\n    mork:joinsOn mm:CustomerCode ;\n    mork:joinCardinality mork:AtMostOneMatch ;\n    mork:reportsUnmatched true ;",
        "    mork:joinsOn mm:CustomerCode ;\n    mork:joinCardinality mork:AtMostOneMatch ;\n    mork:reportsUnmatched false ;"))
    assert sorted(q.code for q in mapping.checks) == ["JoinAmbiguous"]
    written, reported = evaluate(engine, mapping, fixture("customer-source.ttl"))
    assert written == {(REC + "o1", LINK, REC + "c1"), (REC + "o2", LINK, REC + "c1")}
    # The order with a code no customer holds and the order with no code are silent. A code two customers hold is still named.
    assert reported == {("JoinAmbiguous", REC + "o5", REC + "c3"), ("JoinAmbiguous", REC + "o5", REC + "c4")}


@pytest.mark.parametrize("cardinality", ["AtMostOneMatch", "AnyNumberOfMatches"])
@pytest.mark.parametrize("engine", ENGINES)
def test_a_parent_the_guard_excludes_writes_no_link_even_where_a_customer_matches(engine, cardinality):
    """A guard is tested on the parent. An order that names a code and lacks another required value contributes nothing,
    under either cardinality, since the limit of at most one is not what keeps it out."""
    mapping = compiled(variants(
        ("sh:property [ sh:path src:customerCode ; sh:minCount 1 ] .",
         "sh:property [ sh:path src:customerCode ; sh:minCount 1 ] , [ sh:path src:channel ; sh:minCount 1 ] ."),
        ("mork:AtMostOneMatch", f"mork:{cardinality}")))
    source = Graph().parse(data=PREFIXES + """
rec:c1 a src:Customer ; src:code "C1" .
rec:o1 a src:Order ; src:customerCode "C1" ; src:channel "web" .
rec:o2 a src:Order ; src:customerCode "C1" .
""", format="turtle")
    written, reported = evaluate(engine, mapping, source)
    assert written == {(REC + "o1", LINK, REC + "c1")}
    assert rows(JOIN_CODES, reported) == {("InstanceExcluded", REC + "o2", f"<{SRC}channel>")}


# --- a key of several values -----------------------------------------------------------------------------------------

def composite() -> Graph:
    return variant("    mork:joinsOn mm:CustomerCode ;", "    mork:joinsOn mm:CustomerCode , mm:CustomerRegion ;").parse(data=PREFIXES + """
mm:CustomerRegion a mork:JoinCondition ; mork:parentRef "<http://example.org/src#customerRegion>" ; mork:ownRef "<http://example.org/src#region>" .
""", format="turtle")


@pytest.mark.parametrize("engine", ENGINES)
def test_a_join_on_two_values_needs_both_to_hold(engine):
    source = Graph().parse(data=PREFIXES + """
rec:c1 a src:Customer ; src:code "C1" ; src:region "north" .
rec:c2 a src:Customer ; src:code "C1" ; src:region "south" .
rec:a a src:Order ; src:customerCode "C1" ; src:customerRegion "south" .
rec:b a src:Order ; src:customerCode "C1" ; src:customerRegion "east" .
rec:c a src:Order ; src:customerCode "C1" .
""", format="turtle")
    mapping = compiled(composite())
    written, reported = evaluate(engine, mapping, source)
    # The code alone names two customers, and the code with the region names one. The unmatched value is both, joined by a slash.
    assert written == {(REC + "a", LINK, REC + "c2")}
    assert rows({"JoinUnmatched", "JoinAmbiguous"}, reported) == {("JoinUnmatched", REC + "b", "C1/east")}
    # An order with a code and no region has no pair to compare, so it is neither matched nor unmatched.
    assert not [r for r in reported if r[1] == REC + "c" and r[0] != "InstanceExcluded"]


def test_the_conditions_are_read_in_the_order_of_their_paths_and_not_the_order_they_were_named_in():
    """Swapping which condition node holds which pair gives the same two conditions, and so the same query."""
    first = composite()
    text = (FIXTURES / "customer-mapping.ttl").read_text(encoding="utf-8").replace("mork:joinsOn mm:CustomerCode ;", "mork:joinsOn mm:CustomerCode , mm:CustomerRegion ;")
    text = text.replace('mork:parentRef "<http://example.org/src#customerCode>" ;\n    mork:ownRef "<http://example.org/src#code>"',
                        'mork:parentRef "<http://example.org/src#customerRegion>" ;\n    mork:ownRef "<http://example.org/src#region>"')
    other = Graph().parse(data=text + PREFIXES + """
mm:CustomerRegion a mork:JoinCondition ; mork:parentRef "<http://example.org/src#customerCode>" ; mork:ownRef "<http://example.org/src#code>" .
""", format="turtle")
    assert [q.text for q in compiled(first).queries] == [q.text for q in compiled(other).queries]


# --- how the two values are compared ---------------------------------------------------------------------------------

COMPARISON_SOURCE = PREFIXES + """
rec:c1 a src:Customer ; src:code 1 .
rec:o1 a src:Order ; src:customerCode "1" .
rec:o2 a src:Order ; src:customerCode 1 .
"""


def comparison(kind: str, datatype: str = "") -> Graph:
    extra = f"    mork:lookupDatatype {datatype} ;\n" if datatype else ""
    return variant("    mork:lookupComparison mork:TermComparison .", f"{extra}    mork:lookupComparison mork:{kind} .")


@pytest.mark.parametrize("engine", ENGINES)
def test_a_cast_comparison_casts_the_orders_value_to_the_datatype_and_joins_the_same_term(engine):
    source = Graph().parse(data=COMPARISON_SOURCE, format="turtle")
    written, reported = evaluate(engine, compiled(comparison("CastComparison", "xsd:integer")), source)
    assert written == {(REC + "o1", LINK, REC + "c1"), (REC + "o2", LINK, REC + "c1")}
    assert not rows({"JoinUnmatched"}, reported)


@pytest.mark.parametrize("engine", ENGINES)
def test_a_term_comparison_joins_only_the_same_term_so_a_string_never_meets_an_integer(engine):
    source = Graph().parse(data=COMPARISON_SOURCE, format="turtle")
    written, reported = evaluate(engine, compiled(comparison("TermComparison")), source)
    assert written == {(REC + "o2", LINK, REC + "c1")}
    assert rows({"JoinUnmatched"}, reported) == {("JoinUnmatched", REC + "o1", "1")}


@pytest.mark.parametrize("engine", ENGINES)
def test_a_lexical_comparison_joins_on_the_text_whatever_the_datatype(engine):
    source = Graph().parse(data=COMPARISON_SOURCE, format="turtle")
    mapping = compiled(comparison("LexicalComparison"))
    assert "STR(?v3) = STR(" in mapping.constructs[0].text
    written, _ = evaluate(engine, mapping, source)
    assert written == {(REC + "o1", LINK, REC + "c1"), (REC + "o2", LINK, REC + "c1")}


def test_a_cast_with_no_datatype_is_read_as_lexical_and_says_so():
    mapping = compiled(comparison("CastComparison"))
    assert [(f.code, f.severity) for f in mapping.findings if f.code == "JoinLexical"] == [("JoinLexical", Severity.INFO)]
    assert "STR(?v3) = STR(" in mapping.constructs[0].text


def test_a_comparison_a_join_does_not_know_is_refused_by_name():
    mapping = compiled(comparison("Neither"))
    assert "JoinComparisonUnknown" in {f.code for f in mapping.errors}


# --- a join reads the source and never the reference data ------------------------------------------------------------

def test_a_node_in_the_reference_data_is_never_a_match_but_one_in_the_source_is():
    source = fixture("customer-source.ttl")
    reference = Graph().parse(data=PREFIXES + 'rec:c9 a src:Customer ; src:code "C9" .\n', format="turtle")
    out = run(compiled(joined()), source, reference)
    assert (REC + "o3") not in {str(s) for s, _, _ in out.graph}
    assert ("JoinUnmatched", REC + "o3", "C9") in {(f.code, f.focus, f.value) for f in out.findings}
    source.parse(data=PREFIXES + 'rec:c9 a src:Customer ; src:code "C9" .\n', format="turtle")
    assert (REC + "o3", LINK, REC + "c9") in {(str(s), str(p), str(o)) for s, p, o in run(compiled(joined()), source).graph}


# --- what a join datum may not be ------------------------------------------------------------------------------------

@pytest.mark.parametrize("old,new", [
    ("    mork:joinCardinality mork:AtMostOneMatch ;\n", ""),
    ("    mork:reportsUnmatched true ;\n", ""),
    ("    mork:inverseRBoxMatch tgt:placedFor ;\n", ""),
    ("    mork:mappingFor mm:Concept_Customer ;\n", ""),
    ('    mork:ownRef "<http://example.org/src#code>" .', "    mork:parentRef \"<http://example.org/src#customerCode>\" ."),
    ("    mork:identityRule mork:SourceNodeIdentity ;\n    mork:inverseRBoxMatch", "    mork:inverseRBoxMatch"),
])
def test_a_join_that_leaves_out_a_part_is_refused_and_writes_nothing(old, new):
    text = (FIXTURES / "customer-mapping.ttl").read_text(encoding="utf-8")
    if old.endswith("SourceNodeIdentity ;\n    mork:inverseRBoxMatch"):
        text = text.replace("    mork:identityRule mork:SourceNodeIdentity ;\n    mork:inverseRBoxMatch", new, 1)
    else:
        assert old in text
        text = text.replace(old, new, 1)
    mapping = compiled(Graph().parse(data=text, format="turtle"))
    assert "JoinIncomplete" in {f.code for f in mapping.errors}
    assert not mapping.constructs


def test_a_mapping_beneath_a_join_is_refused_since_a_join_writes_its_link_and_nothing_else():
    mapping = compiled(joined().parse(data=PREFIXES + """
mm:Map_Customer mork:compositeNarrowerMapping mm:Map_Region .
mm:Map_Region a mork:DataMapping ; mork:mappingScheme mm:OrderCustomer ; mork:exactRBoxMatch tgt:region ; mork:dataRef "<http://example.org/src#region>" .
""", format="turtle"))
    assert "JoinWrites" in {f.code for f in mapping.errors}


def test_the_shapes_of_mork_refuse_a_join_that_leaves_out_a_part():
    for old, new in [("    mork:joinCardinality mork:AtMostOneMatch ;\n", ""), ("    mork:reportsUnmatched true ;\n", ""),
                     ("    mork:inverseRBoxMatch tgt:placedFor ;\n", "")]:
        text = (FIXTURES / "customer-mapping.ttl").read_text(encoding="utf-8").replace(old, new, 1)
        assert "MorkShape" in {f.code for f in compiled(Graph().parse(data=text, format="turtle")).findings}
    assert "MorkShape" not in {f.code for f in compiled(joined()).findings}


# --- the same answer however the inputs are ordered ------------------------------------------------------------------

def test_a_join_is_the_same_for_any_order_of_the_mapping_graph_and_of_the_source():
    mapping, source = composite(), fixture("customer-source.ttl")
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
    findings = {f.code: f for f in run(compiled(joined()), fixture("customer-source.ttl")).findings}
    assert "no node of the second class" in findings["JoinUnmatched"].message and "at most one" in findings["JoinAmbiguous"].message
