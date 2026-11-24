# SPDX-License-Identifier: MPL-2.0
"""A join datum, the case that takes a node of a second class from the source by equality, and the checks it adds (README §7.10)."""

from __future__ import annotations

import random
import re
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
  {{ SELECT ?f1 ?v3 WHERE {{ ?f1 <{SRC}customerCode> ?v3 . FILTER (((EXISTS {{ ?f1 <{SRC}customerCode> ?any6 . }}))) ?f5 <{RDF_TYPE}> <{SRC}Customer> . ?f5 <{SRC}code> ?v3 . }} GROUP BY ?f1 ?v3 HAVING (COUNT(DISTINCT ?f5) = 1) }}
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


# --- what a candidate join reports, as information ---------------------------------------------------------------------

def candidate_info() -> Graph:
    """The join on candidate evidence, with no guard, that reports a parent holding the value and finding no node as information."""
    return variant(
        "    mork:appliesWhen mm:CustomerGuard ;\n    mork:joinsOn mm:CustomerCode ;\n    mork:joinCardinality mork:AtMostOneMatch ;\n    mork:reportsUnmatched true ;",
        "    mork:joinsOn mm:CustomerCode ;\n    mork:joinCardinality mork:AtMostOneMatch ;\n    mork:reportsUnmatched true ;\n    mork:unmatchedSeverity mork:InfoFinding ;")


@pytest.mark.parametrize("engine", ENGINES)
def test_a_candidate_join_reports_a_parent_with_a_value_and_no_match_as_information_and_a_parent_without_a_value_not_at_all(engine):
    mapping = compiled(candidate_info())
    (unmatched,) = [q for q in mapping.checks if q.code == "JoinUnmatched"]
    assert unmatched.severity is Severity.INFO
    assert "# each row is reported as info" in mapping.text()
    written, reported = evaluate(engine, mapping, fixture("customer-source.ttl"))
    assert written == {(REC + "o1", LINK, REC + "c1"), (REC + "o2", LINK, REC + "c1")}
    # o3 holds a code no customer has, so it is reported. o4 holds no code and says nothing.
    assert rows({"JoinUnmatched"}, reported) == {("JoinUnmatched", REC + "o3", "C9")}
    assert not [r for r in reported if r[1] == REC + "o4"]


def test_the_information_is_the_severity_of_the_finding_a_run_returns_and_a_warning_stays_a_warning():
    info = {f.code: f.severity for f in run(compiled(candidate_info()), fixture("customer-source.ttl")).findings}
    assert info["JoinUnmatched"] is Severity.INFO and info["JoinAmbiguous"] is Severity.WARNING
    warning = {f.code: f.severity for f in run(compiled(joined()), fixture("customer-source.ttl")).findings}
    assert warning["JoinUnmatched"] is Severity.WARNING
    stated = variant("    mork:reportsUnmatched true ;", "    mork:reportsUnmatched true ;\n    mork:unmatchedSeverity mork:WarningFinding ;")
    assert [q.text for q in compiled(stated).queries] == [q.text for q in compiled(joined()).queries]


# --- how many matches a value names, and how many links a parent may have --------------------------------------------

ORDERS = PREFIXES + """
rec:k1 a src:Customer ; src:code "A" .
rec:k2 a src:Customer ; src:code "B" .
rec:d1 a src:Customer ; src:code "D" .
rec:d2 a src:Customer ; src:code "D" .
rec:o1 a src:Order ; src:customerCode "A" , "B" .
rec:o2 a src:Order ; src:customerCode "A" , "D" .
rec:o3 a src:Order ; src:customerCode "A" .
"""


def counted(value: str = "AtMostOneMatch", link: str = "") -> Graph:
    """The join with how many nodes a value finds, and how many a parent finds in all where `link` names it."""
    extra = f"    mork:linkCardinality mork:{link} ;\n" if link else ""
    return variant("    mork:joinCardinality mork:AtMostOneMatch ;\n", f"    mork:joinCardinality mork:{value} ;\n{extra}")


def orders() -> Graph:
    return Graph().parse(data=ORDERS, format="turtle")


@pytest.mark.parametrize("engine", ENGINES)
def test_a_value_is_counted_for_itself_so_two_codes_that_each_name_one_customer_give_two_links(engine):
    mapping = compiled(counted())
    assert sorted(q.code for q in mapping.checks) == ["InstanceExcluded", "JoinAmbiguous", "JoinUnmatched"]
    written, reported = evaluate(engine, mapping, orders())
    # o1 holds two codes and each names one customer. o2's code A names one, and its code D names two, so D writes no link and A does.
    assert written == {(REC + "o1", LINK, REC + "k1"), (REC + "o1", LINK, REC + "k2"), (REC + "o2", LINK, REC + "k1"), (REC + "o3", LINK, REC + "k1")}
    assert rows(JOIN_CODES | {"JoinManyMatches"}, reported) == {("JoinAmbiguous", REC + "o2", REC + "d1"), ("JoinAmbiguous", REC + "o2", REC + "d2")}


@pytest.mark.parametrize("engine", ENGINES)
def test_under_at_most_one_link_a_parent_whose_values_together_find_several_writes_no_link_and_names_each(engine):
    mapping = compiled(counted(link="AtMostOneMatch"))
    assert sorted(q.code for q in mapping.checks) == ["InstanceExcluded", "JoinAmbiguous", "JoinManyMatches", "JoinUnmatched"]
    written, reported = evaluate(engine, mapping, orders())
    # The order with two codes, the same one that gave two links, now gives none and names both customers. o2 finds three in all.
    assert written == {(REC + "o3", LINK, REC + "k1")}
    assert rows({"JoinManyMatches"}, reported) == {
        ("JoinManyMatches", REC + "o1", REC + "k1"), ("JoinManyMatches", REC + "o1", REC + "k2"),
        ("JoinManyMatches", REC + "o2", REC + "k1"), ("JoinManyMatches", REC + "o2", REC + "d1"), ("JoinManyMatches", REC + "o2", REC + "d2")}
    assert rows({"JoinAmbiguous"}, reported) == {("JoinAmbiguous", REC + "o2", REC + "d1"), ("JoinAmbiguous", REC + "o2", REC + "d2")}


@pytest.mark.parametrize("engine", ENGINES)
def test_the_two_rules_are_separate_so_any_number_of_matches_for_a_value_can_still_limit_the_links(engine):
    mapping = compiled(counted("AnyNumberOfMatches", "AtMostOneMatch"))
    assert sorted(q.code for q in mapping.checks) == ["InstanceExcluded", "JoinManyMatches", "JoinUnmatched"]
    written, reported = evaluate(engine, mapping, orders())
    assert written == {(REC + "o3", LINK, REC + "k1")}
    assert {r[1] for r in rows({"JoinManyMatches"}, reported)} == {REC + "o1", REC + "o2"}
    # With any number for both, nothing is limited and each match is linked.
    written, reported = evaluate(engine, compiled(counted("AnyNumberOfMatches")), orders())
    assert len(written) == 6 and not rows({"JoinAmbiguous", "JoinManyMatches"}, reported)


@pytest.mark.parametrize("engine", ENGINES)
def test_a_parent_that_finds_one_node_in_all_keeps_its_link_and_one_that_finds_two_loses_it_under_at_most_one_link(engine):
    written, reported = evaluate(engine, compiled(counted(link="AtMostOneMatch")), fixture("customer-source.ttl"))
    # o1 and o2 find the one customer, so they keep their links. o5's code names two, which the limit on a value reports as well.
    assert written == {(REC + "o1", LINK, REC + "c1"), (REC + "o2", LINK, REC + "c1")}
    assert rows({"JoinManyMatches"}, reported) == {("JoinManyMatches", REC + "o5", REC + "c3"), ("JoinManyMatches", REC + "o5", REC + "c4")}


def test_a_join_that_states_no_link_cardinality_means_any_number_of_links():
    unstated, stated = compiled(counted()), compiled(counted(link="AnyNumberOfMatches"))
    assert [q.text for q in unstated.queries] == [q.text for q in stated.queries]
    assert "JoinManyMatches" not in {q.code for q in unstated.checks}


def test_a_sub_select_counts_the_matches_in_a_variable_of_its_own_and_shares_only_what_it_projects():
    """TSD-79. The count is over a node variable no outer pattern names. Each sub-select projects the parent, and the one
    that counts for each value projects the value too, so the two engines give the specification's answer."""
    text = compiled(counted(link="AtMostOneMatch")).constructs[0].text
    parts = text.split("{ SELECT ")[1:]
    assert len(parts) == 2
    assert parts[0].startswith("?f1 ?v3 WHERE") and parts[1].startswith("?f1 WHERE")
    counted_nodes = [re.search(r"COUNT\(DISTINCT (\?f\d+)\)", part).group(1) for part in parts]
    assert len(set(counted_nodes)) == 2 and "?f2" not in counted_nodes


# --- a comparison and a datatype for each pair -------------------------------------------------------------------------

MIXED_SOURCE = PREFIXES + """
rec:c1 a src:Customer ; src:code "C1" ; src:number 42 .
rec:c2 a src:Customer ; src:code "C1" ; src:number 7 .
rec:a a src:Order ; src:customerCode "C1" ; src:customerNumber "42" .
rec:b a src:Order ; src:customerCode "C1" ; src:customerNumber 7 .
rec:c a src:Order ; src:customerCode "C1" ; src:customerNumber "9" .
"""

NUMBER = PREFIXES + """
mm:CustomerNumber a mork:JoinCondition ; mork:parentRef "<http://example.org/src#customerNumber>" ; mork:ownRef "<http://example.org/src#number>" %s.
"""
CODE_OWN = 'mork:ownRef "<http://example.org/src#code>" .'
TWO_CONDITIONS = ("    mork:joinsOn mm:CustomerCode ;", "    mork:joinsOn mm:CustomerCode , mm:CustomerNumber ;")
CODE_AS_TERM = (CODE_OWN, 'mork:ownRef "<http://example.org/src#code>" ; mork:lookupComparison mork:TermComparison .')


def mixed(own_comparisons: bool) -> Graph:
    """A key of a string pair and an integer pair. Each condition states its own comparison, as the lowering writes them
    and the datum states none, or the datum casts to integer and the string pair states a term comparison beside it."""
    if own_comparisons:
        graph = variants(TWO_CONDITIONS, ("    mork:reportsUnmatched true ;\n    mork:lookupComparison mork:TermComparison .", "    mork:reportsUnmatched true ."), CODE_AS_TERM)
        return graph.parse(data=NUMBER % "; mork:lookupComparison mork:CastComparison ; mork:lookupDatatype xsd:integer ", format="turtle")
    graph = variants(TWO_CONDITIONS, ("    mork:lookupComparison mork:TermComparison .", "    mork:lookupComparison mork:CastComparison ;\n    mork:lookupDatatype xsd:integer ."), CODE_AS_TERM)
    return graph.parse(data=NUMBER % "", format="turtle")


@pytest.mark.parametrize("own", [True, False])
@pytest.mark.parametrize("engine", ENGINES)
def test_a_composite_key_compares_a_string_pair_and_an_integer_pair_each_as_it_says(engine, own):
    """Both ways give one answer. The code is compared as the same term, and the order's number, a string where the customer
    holds an integer, is cast to integer. An order whose number is already an integer joins too."""
    mapping = compiled(mixed(own))
    assert not [f for f in mapping.findings if f.code == "JoinLexical"]
    # Only the number is cast, in the query and in the count beneath it, and always to integer.
    assert re.findall(r"STRDT\(STR\(\?v\d+\), <([^>]+)>\)", mapping.constructs[0].text) == ["http://www.w3.org/2001/XMLSchema#integer"] * 2
    written, reported = evaluate(engine, mapping, Graph().parse(data=MIXED_SOURCE, format="turtle"))
    assert written == {(REC + "a", LINK, REC + "c1"), (REC + "b", LINK, REC + "c2")}
    assert rows({"JoinUnmatched", "JoinAmbiguous"}, reported) == {("JoinUnmatched", REC + "c", "C1/9")}


@pytest.mark.parametrize("engine", ENGINES)
def test_a_pair_that_is_compared_as_a_term_does_not_join_a_string_and_an_integer(engine):
    graph = variants(TWO_CONDITIONS, ("    mork:lookupComparison mork:TermComparison .", "    mork:lookupComparison mork:TermComparison ."), CODE_AS_TERM)
    graph.parse(data=NUMBER % "", format="turtle")
    written, _ = evaluate(engine, compiled(graph), Graph().parse(data=MIXED_SOURCE, format="turtle"))
    assert written == {(REC + "b", LINK, REC + "c2")}


def test_a_cast_with_no_datatype_is_read_as_lexical_for_its_condition_only_and_says_which():
    graph = variants(TWO_CONDITIONS, CODE_AS_TERM).parse(data=NUMBER % "; mork:lookupComparison mork:CastComparison ", format="turtle")
    mapping = compiled(graph)
    (finding,) = [f for f in mapping.findings if f.code == "JoinLexical"]
    assert finding.severity is Severity.INFO and "customerNumber" in finding.message
    text = mapping.constructs[0].text
    # Only the number is a filter, in the query and in the count beneath it, and the code still shares its variable.
    assert text.count("FILTER (STR(?v") == 2 and "sameTerm" not in text and "?f2 <http://example.org/src#code> ?v3 ." in text


# --- the shapes refuse a breach -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("old,new", [
    ("    mork:reportsUnmatched true ;", "    mork:reportsUnmatched true ;\n    mork:linkCardinality mork:Neither ;"),
    ("    mork:reportsUnmatched true ;", "    mork:reportsUnmatched true ;\n    mork:linkCardinality mork:AtMostOneMatch , mork:AnyNumberOfMatches ;"),
    ("    mork:reportsUnmatched true ;", "    mork:reportsUnmatched true ;\n    mork:unmatchedSeverity mork:ErrorFinding ;"),
    ("    mork:reportsUnmatched true ;", "    mork:reportsUnmatched true ;\n    mork:unmatchedSeverity mork:InfoFinding , mork:WarningFinding ;"),
    ('    mork:ownRef "<http://example.org/src#code>" .', '    mork:ownRef "<http://example.org/src#code>" ;\n    mork:lookupComparison mork:Neither .'),
    ('    mork:ownRef "<http://example.org/src#code>" .', '    mork:ownRef "<http://example.org/src#code>" ;\n    mork:lookupDatatype xsd:integer , xsd:string .'),
])
def test_the_shapes_of_mork_refuse_a_breach_of_a_limit_a_severity_or_a_condition_comparison(old, new):
    assert "MorkShape" in {f.code for f in compiled(variant(old, new)).findings}


def test_a_link_cardinality_or_a_severity_with_no_condition_is_refused_since_it_is_no_join():
    for line in ("mm:Map_Order mork:linkCardinality mork:AtMostOneMatch .", "mm:Map_Order mork:unmatchedSeverity mork:InfoFinding ."):
        assert "MorkShape" in {f.code for f in compiled(joined().parse(data=PREFIXES + line, format="turtle")).findings}


@pytest.mark.parametrize("line", ["mork:linkCardinality mork:Neither ;", "mork:unmatchedSeverity mork:ErrorFinding ;"])
def test_a_link_cardinality_or_a_severity_the_compiler_does_not_know_is_refused_and_writes_nothing(line):
    mapping = compiled(variant("    mork:reportsUnmatched true ;", "    mork:reportsUnmatched true ;\n    " + line))
    assert "JoinIncomplete" in {f.code for f in mapping.errors} and not mapping.constructs


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
