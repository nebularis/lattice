# SPDX-License-Identifier: MPL-2.0
"""A datum made for each member of a collection, and the checks and findings it adds (README §7.12). Each case is the scheme
of `fixtures/line-mapping.ttl` with one change, run on Oxigraph and on rdflib."""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import pytest
from rdflib import Dataset, Graph

from mork_rdf import Severity, compile_scheme, run

FIXTURES = Path(__file__).parent / "fixtures"
SCHEME = "http://example.org/mapping#BundleLine"
BASE = "http://example.org/out/"
AT = datetime(2026, 11, 25, tzinfo=timezone.utc)
SRC, TGT, REC = (f"http://example.org/{n}" for n in ("src#", "tgt#", "records/"))
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
XSD = "http://www.w3.org/2001/XMLSchema#"
XSD_INTEGER = XSD + "integer"
ENGINES = ["oxigraph", "rdflib"]

PREFIXES = f"""@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix src: <{SRC}> . @prefix tgt: <{TGT}> . @prefix mm: <http://example.org/mapping#> . @prefix rec: <{REC}> .
"""

SOURCE = PREFIXES + """
rec:b1 a src:Bundle ; src:bundleCode "B1" ; src:items ( rec:i1 rec:i2 rec:i3 ) .
rec:b2 a src:Bundle ; src:bundleCode "B2" ; src:items ( rec:i3 ) .
rec:b3 a src:Bundle ; src:bundleCode "B3" ; src:items () .
rec:b4 a src:Bundle ; src:bundleCode "B4" .
rec:b5 a src:Bundle ; src:items ( rec:i1 ) .
rec:b6 a src:Bundle ; src:bundleCode "B6" ; src:items ( rec:i1 rec:i1 ) .
"""

IDENTITY = """    mork:identityTemplateMapping mm:LineIdentity ;
    mork:compositeNarrowerMapping mm:Map_OfItem , mm:Map_BundleCode ."""


def mapping_text() -> str:
    return (FIXTURES / "line-mapping.ttl").read_text(encoding="utf-8")


def variant(*changes: tuple[str, str]) -> Graph:
    text = mapping_text()
    for old, new in changes:
        assert old in text, old
        text = text.replace(old, new)
    return Graph().parse(data=text, format="turtle")


def compiled(mapping: Graph):
    return compile_scheme(mapping, SCHEME, base=BASE, at=AT)


def evaluate(engine: str, mapping, source: Graph) -> tuple[set, set]:
    """What the constructs write and the checks report on one engine, as (subject, property, value) and (code, focus, value)."""
    if engine == "oxigraph":
        out = run(mapping, source)
        return {(str(s), str(p), str(o)) for s, p, o in out.graph}, {(f.code, f.focus, f.value) for f in out.findings}
    dataset = Dataset()
    for t in source:
        dataset.default_graph.add(t)
    written = {(str(s), str(p), str(o)) for q in mapping.constructs for s, p, o in dataset.query(q.text)}
    rows = {(q.code, str(row["focus"]), None if row["value"] is None else str(row["value"])) for q in mapping.checks for row in dataset.query(q.text)}
    return written, rows


def source(extra: str = "") -> Graph:
    return Graph().parse(data=SOURCE + extra, format="turtle")


def line(code: str, member: str) -> str:
    """The node a keyed line has, the contract's stem, the bundle's code and the member, each encoded as ENCODE_FOR_URI does."""
    return f"{BASE}bundle-line/Line/{quote(code, safe='')}/{quote(member, safe='')}"


def lines(*pairs: tuple[str, str]) -> set:
    """What the lines of the given (code, member) pairs write, the type, the link from the bundle, the item and the code."""
    out = set()
    bundles = {"B1": REC + "b1", "B2": REC + "b2", "B6": REC + "b6"}
    for code, member in pairs:
        node = line(code, member)
        out |= {(node, RDF_TYPE, TGT + "Line"), (bundles[code], TGT + "hasLine", node), (node, TGT + "ofItem", member), (node, TGT + "bundleCode", code)}
    return out


def only(code: str, reported: set) -> set:
    return {row for row in reported if row[0] == code}


def codes(compiled_mapping) -> list:
    return sorted(q.code for q in compiled_mapping.checks)


I = {name: REC + name for name in ("i1", "i2", "i3")}
KEYED = lines(("B1", I["i1"]), ("B1", I["i2"]), ("B1", I["i3"]), ("B2", I["i3"]), ("B6", I["i1"]))


def test_the_keyed_scheme_compiles_to_the_one_construct_that_writes_the_node_and_the_link():
    mapping = compiled(variant())
    assert not mapping.errors
    node = next(q for q in mapping.constructs if q.mapping == "http://example.org/mapping#Map_Line")
    expected = f"""BASE <{BASE}>
CONSTRUCT {{ ?t6 <{RDF_TYPE}> <{TGT}Line> . ?f1 <{TGT}hasLine> ?t6 . }}
WHERE {{
  ?f1 <{RDF_TYPE}> <{SRC}Bundle> .
  FILTER (((EXISTS {{ ?f1 <{SRC}bundleCode> ?any2 . }})) && ((EXISTS {{ ?f1 <{SRC}items> ?any3 . }})))
  ?f1 <{SRC}items>/(<http://www.w3.org/1999/02/22-rdf-syntax-ns#rest>*)/<http://www.w3.org/1999/02/22-rdf-syntax-ns#first> ?m4 .
  FILTER (!(isBlank(?m4) || STRSTARTS(STR(?m4), "urn:mork-rdf:skolem:v1:")))
  BIND (IF(isLiteral(?m4) && DATATYPE(?m4) != <{XSD}string>, CONCAT(STR(?m4), "^^", STR(DATATYPE(?m4))), STR(?m4)) AS ?s5)
  ?f1 <{SRC}bundleCode> ?v7 .
  BIND (IRI(CONCAT("bundle-line/Line/", CONCAT(ENCODE_FOR_URI(STR(?v7)), CONCAT("/", ENCODE_FOR_URI(?s5))))) AS ?t6)
}}"""
    assert " ".join(node.text.split()) == " ".join(expected.split())
    assert codes(mapping) == ["ClosureCycle", "CollectionEmpty", "IdentityAmbiguous", "IdentityUnbound", "InstanceExcluded", "InstanceExcluded", "MemberUnnamed"]
    assert len(mapping.constructs) == 3


@pytest.mark.parametrize("engine", ENGINES)
def test_a_node_is_made_for_each_instance_and_member_keyed_by_the_code_and_the_member(engine):
    written, reported = evaluate(engine, compiled(variant()), source())
    assert written == KEYED
    assert only("MemberUnnamed", reported) == set() and only("ValueDisagrees", reported) == set()


@pytest.mark.parametrize("engine", ENGINES)
def test_two_bundles_that_share_a_code_and_a_member_share_the_node(engine):
    again = source("rec:b7 a src:Bundle ; src:bundleCode \"B1\" ; src:items ( rec:i2 rec:i4 ) .")
    written, _ = evaluate(engine, compiled(variant()), again)
    shared = line("B1", I["i2"])
    assert (REC + "b1", TGT + "hasLine", shared) in written and (REC + "b7", TGT + "hasLine", shared) in written
    assert len([1 for s, p, o in written if p == RDF_TYPE and o == TGT + "Line"]) == 5 + 1


@pytest.mark.parametrize("engine", ENGINES)
def test_a_bundle_without_the_code_or_the_list_is_excluded_and_an_empty_list_is_reported(engine):
    _, reported = evaluate(engine, compiled(variant()), source())
    assert only("InstanceExcluded", reported) == {("InstanceExcluded", REC + "b4", f"<{SRC}items>"), ("InstanceExcluded", REC + "b5", f"<{SRC}bundleCode>")}
    assert only("CollectionEmpty", reported) == {("CollectionEmpty", REC + "b3", "<http://example.org/src#items>/(<http://www.w3.org/1999/02/22-rdf-syntax-ns#rest>*)/<http://www.w3.org/1999/02/22-rdf-syntax-ns#first>")}


@pytest.mark.parametrize("engine", ENGINES)
def test_a_list_that_repeats_a_member_gives_one_node_for_it(engine):
    written, _ = evaluate(engine, compiled(variant()), source())
    assert [s for s, p, o in written if p == RDF_TYPE and s.startswith(f"{BASE}bundle-line/Line/B6/")] == [line("B6", I["i1"])]


def test_a_keyed_node_carries_the_mapping_review_and_the_expansion_review():
    findings = compiled(variant()).findings
    assert [(f.code, f.severity) for f in findings] == [("ExpansionReview", Severity.WARNING), ("MappingReview", Severity.WARNING)]
    assert {f.mapping for f in findings} == {"http://example.org/mapping#Map_Line"}
    assert "http://example.org/src#items" in findings[0].message


# --- a node for each instance and member ---------------------------------------------------------------------------------

PER_INSTANCE = [("mork:identityTemplateMapping mm:LineIdentity ;", 'mork:conceptName "bundle-line/Line" ;')]


def per_instance(instance: str, member: str) -> str:
    return f"{BASE}bundle-line/Line/{hashlib.sha256(instance.encode()).hexdigest()}/{quote(member, safe='')}"


@pytest.mark.parametrize("engine", ENGINES)
def test_a_node_for_each_instance_and_member_names_the_pair_and_takes_no_mapping_review(engine):
    mapping = compiled(variant(*PER_INSTANCE))
    assert [f.code for f in mapping.findings] == ["ExpansionReview"]
    written, _ = evaluate(engine, mapping, source())
    nodes = {s for s, p, o in written if p == RDF_TYPE}
    pairs = [(REC + "b1", I["i1"]), (REC + "b1", I["i2"]), (REC + "b1", I["i3"]), (REC + "b2", I["i3"]), (REC + "b6", I["i1"])]
    assert nodes == {per_instance(b, m) for b, m in pairs}
    assert (per_instance(REC + "b2", I["i3"]), TGT + "ofItem", I["i3"]) in written and (REC + "b2", TGT + "hasLine", per_instance(REC + "b2", I["i3"])) in written


@pytest.mark.parametrize("engine", ENGINES)
def test_a_member_two_bundles_hold_gives_two_nodes_when_a_node_is_for_each_instance(engine):
    written, _ = evaluate(engine, compiled(variant(*PER_INSTANCE)), source())
    assert per_instance(REC + "b1", I["i3"]) != per_instance(REC + "b2", I["i3"])
    assert {per_instance(REC + "b1", I["i3"]), per_instance(REC + "b2", I["i3"])} <= {s for s, p, o in written if p == RDF_TYPE}


# --- a key without the member, and the member alone ----------------------------------------------------------------------

WITHOUT_MEMBER = [("mork:concatRight mm:Id_Rest .\nmm:Id_Rest a mork:ConcatExpression ; mork:concatLeft mm:Id_Code ; mork:concatRight mm:Id_Tail .\nmm:Id_Tail a mork:ConcatExpression ; mork:concatLeft mm:Id_Slash ; mork:concatRight mm:Id_Member .",
                    "mork:concatRight mm:Id_Code .")]
MEMBER_ALONE = [("mork:concatLeft mm:Id_Stem ; mork:concatRight mm:Id_Rest .\nmm:Id_Rest a mork:ConcatExpression ; mork:concatLeft mm:Id_Code ; mork:concatRight mm:Id_Tail .\nmm:Id_Tail a mork:ConcatExpression ; mork:concatLeft mm:Id_Slash ; mork:concatRight mm:Id_Member .",
                  "mork:concatLeft mm:Id_Stem ; mork:concatRight mm:Id_Member .")]


@pytest.mark.parametrize("engine", ENGINES)
def test_a_key_without_the_member_gives_one_node_for_each_code_that_every_member_is_written_on(engine):
    mapping = compiled(variant(*WITHOUT_MEMBER))
    written, _ = evaluate(engine, mapping, source())
    b1 = f"{BASE}bundle-line/Line/B1"
    assert {(b1, TGT + "ofItem", m) for m in I.values()} <= written
    assert {s for s, p, o in written if p == RDF_TYPE} == {f"{BASE}bundle-line/Line/{c}" for c in ("B1", "B2", "B6")}
    assert [f.code for f in mapping.findings] == ["ExpansionReview", "MappingReview"]


@pytest.mark.parametrize("engine", ENGINES)
def test_a_key_of_the_member_alone_merges_the_bundles_that_hold_it_and_reports_the_values_that_disagree(engine):
    mapping = compiled(variant(*MEMBER_ALONE))
    written, reported = evaluate(engine, mapping, source())
    shared = f"{BASE}bundle-line/Line/{quote(I['i3'], safe='')}"
    assert {(shared, TGT + "bundleCode", "B1"), (shared, TGT + "bundleCode", "B2")} <= written
    first = f"{BASE}bundle-line/Line/{quote(I['i1'], safe='')}"
    assert only("ValueDisagrees", reported) == {("ValueDisagrees", shared, "B1"), ("ValueDisagrees", shared, "B2"), ("ValueDisagrees", first, "B1"), ("ValueDisagrees", first, "B6")}
    assert [f.code for f in mapping.findings] == ["ExpansionReview", "MappingReview"]


# --- the member is the node ----------------------------------------------------------------------------------------------

MEMBER_NODE = [("    mork:identityTemplateMapping mm:LineIdentity ;\n", "    mork:identityRule mork:MemberIdentity ;\n")]


@pytest.mark.parametrize("engine", ENGINES)
def test_the_member_as_the_node_is_typed_and_written_on_and_nothing_is_minted(engine):
    mapping = compiled(variant(*MEMBER_NODE))
    assert not mapping.errors
    written, _ = evaluate(engine, mapping, source())
    typed = {s for s, p, o in written if p == RDF_TYPE}
    assert typed == set(I.values()) | {I["i1"]}
    assert (REC + "b1", TGT + "hasLine", I["i2"]) in written and (REC + "b2", TGT + "hasLine", I["i3"]) in written
    assert (I["i3"], TGT + "ofItem", I["i3"]) in written
    assert not [s for s, _, _ in written if s.startswith(BASE)]


@pytest.mark.parametrize("engine", ENGINES)
def test_the_member_as_the_node_reports_a_literal_and_a_blank_member_and_skips_them(engine):
    mapping = compiled(variant(*MEMBER_NODE))
    odd = source('rec:b8 a src:Bundle ; src:bundleCode "B8" ; src:items ( rec:i1 7 [ a src:Item ] ) .')
    written, reported = evaluate(engine, mapping, odd)
    rows = only("MemberNotIri", reported)
    assert {(f, v) for _, f, v in rows if f == REC + "b8" and v == "7"} == {(REC + "b8", "7")}
    assert len([r for r in rows if r[1] == REC + "b8"]) == 2
    assert (REC + "b8", TGT + "hasLine", I["i1"]) in written
    assert len([1 for s, p, o in written if s == REC + "b8"]) == 1
    assert [f.code for f in mapping.findings] == ["ExpansionReview", "MappingReview"]


# --- a stable name -------------------------------------------------------------------------------------------------------

NAMED = [("mork:memberRef", "mork:memberName src:sku ;\n    mork:memberRef")]
NAMES = """
rec:i1 src:sku "A1" . rec:i2 src:sku "A 2" . rec:i3 src:sku "A3" .
"""


@pytest.mark.parametrize("engine", ENGINES)
def test_a_stable_name_is_spelled_in_place_of_the_member(engine):
    mapping = compiled(variant(*NAMED))
    written, reported = evaluate(engine, mapping, source(NAMES))
    nodes = {s for s, p, o in written if p == RDF_TYPE}
    assert nodes == {line("B1", "A1"), line("B1", "A 2"), line("B1", "A3"), line("B2", "A3"), line("B6", "A1")}
    assert (line("B1", "A 2"), TGT + "ofItem", I["i2"]) in written
    assert line("B1", "A 2").endswith("B1/A%202")
    assert only("MemberUnnamed", reported) == set()


@pytest.mark.parametrize("engine", ENGINES)
def test_a_member_without_the_name_is_reported_and_skipped_while_the_others_are_written(engine):
    mapping = compiled(variant(*NAMED))
    written, reported = evaluate(engine, mapping, source('rec:i1 src:sku "A1" . rec:i3 src:sku "A3" .'))
    assert only("MemberUnnamed", reported) == {("MemberUnnamed", REC + "b1", I["i2"])}
    nodes = {s for s, p, o in written if p == RDF_TYPE and s.startswith(f"{BASE}bundle-line/Line/B1/")}
    assert nodes == {line("B1", "A1"), line("B1", "A3")}


@pytest.mark.parametrize("engine", ENGINES)
def test_a_blank_member_with_a_name_is_named_by_it(engine):
    odd = source('rec:b8 a src:Bundle ; src:bundleCode "B8" ; src:items ( [ src:sku "Z9" ] ) .')
    written, reported = evaluate(engine, compiled(variant(*NAMED)), odd)
    assert line("B8", "Z9") in {s for s, p, o in written}
    assert not [r for r in only("MemberUnnamed", reported) if r[1] == REC + "b8"]


@pytest.mark.parametrize("engine", ENGINES)
def test_a_blank_member_with_a_name_is_written_as_the_name_and_never_as_a_blank_node(engine):
    odd = source('rec:b8 a src:Bundle ; src:bundleCode "B8" ; src:items ( [ src:sku "Z9" ] rec:i1 ) .' + NAMES)
    written, _ = evaluate(engine, compiled(variant(*NAMED)), odd)
    assert (line("B8", "Z9"), TGT + "ofItem", "Z9") in written
    assert (line("B8", "A1"), TGT + "ofItem", I["i1"]) in written
    values = {o for s, p, o in written if p == TGT + "ofItem" and s.startswith(f"{BASE}bundle-line/Line/B8/")}
    assert values == {"Z9", I["i1"]}
    assert not [o for _, _, o in written if "skolem" in o]


def test_a_compiled_node_for_each_member_reads_back_with_the_severity_each_check_reports_its_rows_as():
    """A check of information is part of the text the digest reads, so a description that dropped its severity could not be read back."""
    from mork_rdf import from_rdf, to_rdf

    mapping = compiled(variant())
    assert {q.severity for q in mapping.checks} == {Severity.INFO, Severity.WARNING}
    again = from_rdf(Graph().parse(data=to_rdf(mapping).serialize(format="turtle"), format="turtle"))
    assert again == mapping and again.digest == mapping.digest


# --- a member that has no name -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("engine", ENGINES)
def test_a_blank_member_is_reported_and_skipped_while_the_other_members_are_written(engine):
    odd = source('rec:b8 a src:Bundle ; src:bundleCode "B8" ; src:items ( rec:i1 [ a src:Item ] rec:i2 ) .')
    written, reported = evaluate(engine, compiled(variant()), odd)
    nodes = {s for s, p, o in written if p == RDF_TYPE and s.startswith(f"{BASE}bundle-line/Line/B8/")}
    assert nodes == {line("B8", I["i1"]), line("B8", I["i2"])}
    assert [r[1] for r in only("MemberUnnamed", reported)] == [REC + "b8"]


@pytest.mark.parametrize("engine", ENGINES)
def test_a_literal_member_is_spelled_with_its_lexical_form_and_a_datatype_other_than_a_string(engine):
    odd = source('rec:b8 a src:Bundle ; src:bundleCode "B8" ; src:items ( 7 "x y" "7" ) .')
    written, _ = evaluate(engine, compiled(variant()), odd)
    nodes = {s for s, p, o in written if p == RDF_TYPE and s.startswith(f"{BASE}bundle-line/Line/B8/")}
    assert nodes == {line("B8", f"7^^{XSD_INTEGER}"), line("B8", "x y"), line("B8", "7")}
    assert line("B8", "7") != line("B8", f"7^^{XSD_INTEGER}")


@pytest.mark.parametrize("engine", ENGINES)
def test_the_member_is_written_as_itself_a_literal_too(engine):
    odd = source('rec:b8 a src:Bundle ; src:bundleCode "B8" ; src:items ( 7 ) .')
    written, _ = evaluate(engine, compiled(variant()), odd)
    assert (line("B8", f"7^^{XSD_INTEGER}"), TGT + "ofItem", "7") in written


# --- determinism, and what the compiler refuses --------------------------------------------------------------------------


def test_the_same_scheme_compiles_to_the_same_text_whatever_the_order_of_its_triples():
    reference = compiled(variant()).text()
    triples = sorted(variant())
    for seed in range(3):
        shuffled = list(triples)
        random.Random(seed).shuffle(shuffled)
        graph = Graph()
        for triple in shuffled:
            graph.add(triple)
        assert compiled(graph).text() == reference


@pytest.mark.parametrize("engine", ENGINES)
def test_the_same_graph_comes_back_on_a_repeat_and_with_the_source_triples_permuted(engine):
    mapping = compiled(variant())
    first, _ = evaluate(engine, mapping, source())
    triples = sorted(source())
    for seed in range(2):
        shuffled = list(triples)
        random.Random(seed).shuffle(shuffled)
        graph = Graph()
        for triple in shuffled:
            graph.add(triple)
        assert evaluate(engine, mapping, graph)[0] == first


@pytest.mark.parametrize("change, code", [
    ([("mork:inverseRBoxMatch tgt:hasLine ;", "")], "NoGluingProperty"),
    ([("mork:mappingFor mm:Concept_Bundle ;\n    mork:identityRule mork:SourceNodeIdentity ;", "mork:mappingFor mm:Concept_Bundle ; mork:conceptName \"Root\" ; mork:exactTBoxMatch tgt:Root ;")], "MemberIncomplete"),
    ([("    mork:identityTemplateMapping mm:LineIdentity ;\n", "    mork:identityRule mork:MemberIdentity ;\n    mork:conceptName \"x\" ;\n")], "MemberIncomplete"),
    ([("mork:identityTemplateMapping mm:LineIdentity ;", "mork:identityRule mork:SourceNodeIdentity ;")], "IdentityRuleUnknown"),
    ([("mm:Id_Member a mork:MemberExpression .", "mm:Id_Member a mork:MemberExpression .\nmm:Plain a mork:DataMapping ; mork:mappingScheme mm:BundleLine ; mork:exactRBoxMatch tgt:x ; mork:dataMember true .")], "MemberValueIncomplete"),
], ids=["no link", "root mints", "member node that names itself", "source node rule on a member datum", "member value with no parent"])
def test_a_datum_made_for_each_member_that_is_incomplete_is_refused_by_name(change, code):
    mapping = compiled(variant(*change))
    assert code in {f.code for f in mapping.findings}


def test_a_member_expression_outside_the_identity_of_a_datum_made_for_each_member_is_refused():
    plain = Graph().parse(data=PREFIXES + """
mm:Plain a mork:MappingScheme .
src:Bundle a mork:Entity .
mm:Concept_Plain a mork:DataConcept ; mork:representedAs src:Bundle .
mm:Map_Plain a mork:DataMapping , mork:Datum ; mork:mappingScheme mm:Plain ; mork:mappingFor mm:Concept_Plain ;
    mork:identityTemplateMapping mm:Id ; mork:exactTBoxMatch tgt:Plain .
mm:Id a mork:MemberExpression .
""", format="turtle")
    mapping = compile_scheme(plain, "http://example.org/mapping#Plain", base=BASE, at=AT)
    assert "MemberOutside" in {f.code for f in mapping.findings}


def test_the_dry_run_gives_each_new_check_its_message():
    odd = source('rec:b8 a src:Bundle ; src:bundleCode "B8" ; src:items ( [ a src:Item ] ) .')
    findings = {f.code: f for f in run(compiled(variant()), odd).findings}
    assert "no name" in findings["MemberUnnamed"].message
    node = {f.code: f for f in run(compiled(variant(*MEMBER_NODE)), odd).findings}
    assert "no node" in node["MemberNotIri"].message
