# SPDX-License-Identifier: MPL-2.0
"""An assertion that writes onto the source node itself with a path that reaches a collection, which is an expansion, and the
checks it adds (README §7.11)."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path

import pytest
from rdflib import Dataset, Graph

from mork_rdf import Severity, compile_scheme, run

FIXTURES = Path(__file__).parent / "fixtures"
SCHEME = "http://example.org/mapping#BundleItems"
BASE = "http://example.org/out/"
AT = datetime(2026, 11, 25, tzinfo=timezone.utc)
SRC, TGT, REC = (f"http://example.org/{n}" for n in ("src#", "tgt#", "records/"))
CONTAINS = TGT + "contains"
ENGINES = ["oxigraph", "rdflib"]
LIST = "<http://example.org/src#items>/<http://www.w3.org/1999/02/22-rdf-syntax-ns#rest>*/<http://www.w3.org/1999/02/22-rdf-syntax-ns#first>"

#: The path as the compiler writes it back, which is what a check names.
WRITTEN = "<http://example.org/src#items>/(<http://www.w3.org/1999/02/22-rdf-syntax-ns#rest>*)/<http://www.w3.org/1999/02/22-rdf-syntax-ns#first>"

PREFIXES = f"""@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix src: <{SRC}> . @prefix tgt: <{TGT}> . @prefix mm: <http://example.org/mapping#> . @prefix rec: <{REC}> .
"""

SOURCE = PREFIXES + """
rec:b1 a src:Bundle ; src:items ( rec:i1 rec:i2 rec:i3 ) .
rec:b2 a src:Bundle ; src:items ( rec:i3 ) .
rec:b3 a src:Bundle ; src:items () .
rec:b4 a src:Bundle .
"""


def mapping_text() -> str:
    return (FIXTURES / "bundle-mapping.ttl").read_text(encoding="utf-8")


def variant(old: str, new: str) -> Graph:
    text = mapping_text()
    assert old in text
    return Graph().parse(data=text.replace(old, new), format="turtle")


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


def bundle() -> Graph:
    return Graph().parse(FIXTURES / "bundle-mapping.ttl")


def source() -> Graph:
    return Graph().parse(data=SOURCE, format="turtle")


def test_the_list_compiles_to_one_construct_and_the_checks_the_case_adds():
    mapping = compiled(bundle())
    (construct,) = mapping.constructs
    expected = f"""BASE <{BASE}>
CONSTRUCT {{ ?f1 <{CONTAINS}> ?v3 . }}
WHERE {{
  ?f1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <{SRC}Bundle> .
  FILTER (((EXISTS {{ ?f1 <{SRC}items> ?any2 . }})))
  ?f1 <{SRC}items>/(<http://www.w3.org/1999/02/22-rdf-syntax-ns#rest>*)/<http://www.w3.org/1999/02/22-rdf-syntax-ns#first> ?v3 .
}}"""
    assert " ".join(construct.text.split()) == " ".join(expected.split())
    assert sorted(q.code for q in mapping.checks) == ["ClosureCycle", "CollectionEmpty", "InstanceExcluded"]
    assert [(f.code, f.severity) for f in mapping.findings] == [("ExpansionReview", Severity.WARNING)]
    assert not mapping.errors


@pytest.mark.parametrize("engine", ENGINES)
def test_each_member_is_a_statement_on_the_bundle_and_nothing_is_minted(engine):
    written, _ = evaluate(engine, compiled(bundle()), source())
    assert written == {(REC + "b1", CONTAINS, REC + m) for m in ("i1", "i2", "i3")} | {(REC + "b2", CONTAINS, REC + "i3")}


@pytest.mark.parametrize("engine", ENGINES)
def test_a_bundle_without_a_list_is_excluded_and_an_empty_list_is_reported_as_information(engine):
    mapping = compiled(bundle())
    written, reported = evaluate(engine, mapping, source())
    assert not {s for s, _, _ in written} & {REC + "b3", REC + "b4"}
    assert reported == {("InstanceExcluded", REC + "b4", f"<{SRC}items>"), ("CollectionEmpty", REC + "b3", WRITTEN)}
    assert {q.code: q.severity for q in mapping.checks} == {"InstanceExcluded": Severity.WARNING, "CollectionEmpty": Severity.INFO, "ClosureCycle": Severity.WARNING}
    out = run(mapping, source())
    assert {(f.code, f.focus): f.severity for f in out.findings} == {("InstanceExcluded", REC + "b4"): Severity.WARNING, ("CollectionEmpty", REC + "b3"): Severity.INFO}


@pytest.mark.parametrize("engine", ENGINES)
def test_a_list_keeps_a_repeated_member_once_since_the_construct_writes_a_set(engine):
    again = Graph().parse(data=PREFIXES + "rec:b5 a src:Bundle ; src:items ( rec:i1 rec:i1 ) .", format="turtle")
    written, _ = evaluate(engine, compiled(bundle()), again)
    assert written == {(REC + "b5", CONTAINS, REC + "i1")}


def test_the_expansion_review_names_the_source_and_every_expansion_takes_one():
    (review,) = [f for f in compiled(bundle()).findings if f.code == "ExpansionReview"]
    assert "http://example.org/src#items" in review.message and review.severity is Severity.WARNING


CLOSURE = "<http://example.org/src#broader>+"
LIST_LINE = f'mork:dataRef "{LIST}" ;\n    mork:appliesWhen mm:BundleGuard .'


HIERARCHY = PREFIXES + """
rec:c1 a src:Category .
rec:c2 a src:Category ; src:broader rec:c1 .
rec:c3 a src:Category ; src:broader rec:c2 .
"""


@pytest.mark.parametrize("engine", ENGINES)
def test_a_transitive_closure_gives_a_statement_for_each_ancestor_and_the_top_is_silent(engine):
    mapping = compiled(variant(LIST_LINE, f'mork:dataRef "{CLOSURE}" .').parse(data=PREFIXES + "mm:Concept_Bundle mork:representedAs src:Category .", format="turtle"))
    hierarchy = Graph().parse(data=HIERARCHY, format="turtle")
    written, reported = evaluate(engine, mapping, hierarchy)
    assert written == {(REC + "c2", CONTAINS, REC + "c1"), (REC + "c3", CONTAINS, REC + "c2"), (REC + "c3", CONTAINS, REC + "c1")}
    assert reported == set()
    assert sorted(q.code for q in mapping.checks) == ["ClosureCycle", "CollectionEmpty"]



def test_the_same_scheme_compiles_to_the_same_text_whatever_the_order_of_its_triples():
    reference = compiled(bundle()).text()
    triples = sorted(bundle())
    for seed in range(3):
        shuffled = list(triples)
        random.Random(seed).shuffle(shuffled)
        graph = Graph()
        for triple in shuffled:
            graph.add(triple)
        assert compiled(graph).text() == reference


def test_an_assertion_that_is_not_beneath_a_source_node_datum_is_not_an_expansion():
    """A datum that mints its node, with an assertion beneath it, takes no expansion review and no empty-collection check."""
    plain = Graph().parse(data=PREFIXES + """
mm:Plain a mork:MappingScheme .
src:Bundle a mork:Entity .
mm:Concept_Plain a mork:DataConcept ; mork:representedAs src:Bundle .
mm:Map_Plain a mork:DataMapping , mork:Datum ; mork:mappingScheme mm:Plain ; mork:mappingFor mm:Concept_Plain ;
    mork:conceptName "Plain" ; mork:exactTBoxMatch tgt:Plain ; mork:compositeNarrowerMapping mm:Map_Label .
mm:Map_Label a mork:DataMapping ; mork:mappingScheme mm:Plain ; mork:exactRBoxMatch tgt:label ; mork:dataRef "<http://example.org/src#label>" .
""", format="turtle")
    mapping = compile_scheme(plain, "http://example.org/mapping#Plain", base=BASE, at=AT)
    assert not mapping.errors
    assert not [f for f in mapping.findings if f.code == "ExpansionReview"]
    assert "CollectionEmpty" not in {q.code for q in mapping.checks}


CANDIDATE = f'mork:dataRef "{LIST}" .'


@pytest.mark.parametrize("engine", ENGINES)
def test_on_candidate_evidence_a_bundle_without_the_property_is_silent_and_an_empty_list_is_reported(engine):
    """With no guard, a node that lacks the property the path starts from says nothing, and one that holds it, as an empty
    list does, and reaches no member is reported."""
    mapping = compiled(variant(LIST_LINE, CANDIDATE))
    written, reported = evaluate(engine, mapping, source())
    assert written == {(REC + "b1", CONTAINS, REC + m) for m in ("i1", "i2", "i3")} | {(REC + "b2", CONTAINS, REC + "i3")}
    assert reported == {("CollectionEmpty", REC + "b3", WRITTEN)}
    assert sorted(q.code for q in mapping.checks) == ["ClosureCycle", "CollectionEmpty"]


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("path, reported_nodes", [
    ("<http://example.org/src#items>/<http://example.org/src#next>|<http://example.org/src#extra>/<http://example.org/src#next>", {"b-alt", "b-seq"}),
    ("^(<http://example.org/src#member>/<http://example.org/src#tail>)", {"b-inv"}),
    ("<http://example.org/src#items>?/<http://example.org/src#next>/<http://example.org/src#next>", {"b-seq"}),
])
def test_the_property_a_path_starts_from_is_read_from_the_path_whatever_its_form(engine, path, reported_nodes):
    """An alternative starts at any of its parts, an inverse at the inverse of the property the sequence ends in, and a
    sequence at its first part and past a part that may take no step. A node that holds it and reaches nothing is reported, and
    a node that holds nothing at the start is silent."""
    mapping = compiled(variant(LIST_LINE, f'mork:dataRef "{path}" .'))
    data = Graph().parse(data=PREFIXES + """
rec:b-alt a src:Bundle ; src:extra rec:x .
rec:b-inv a src:Bundle .
rec:y src:tail rec:b-inv .
rec:b-seq a src:Bundle ; src:items rec:p ; src:next rec:q .
rec:b-none a src:Bundle .
""", format="turtle")
    _, reported = evaluate(engine, mapping, data)
    subjects = {focus for code, focus, _ in reported if code == "CollectionEmpty"}
    assert subjects == {REC + node for node in reported_nodes}


@pytest.mark.parametrize("engine", ENGINES)
def test_a_closure_that_reaches_itself_is_reported_by_node_and_an_acyclic_one_reports_nothing(engine):
    mapping = compiled(variant(LIST_LINE, f'mork:dataRef "{CLOSURE}" .').parse(data=PREFIXES + "mm:Concept_Bundle mork:representedAs src:Category .", format="turtle"))
    cyclic = Graph().parse(data=PREFIXES + """
rec:a a src:Category ; src:broader rec:b .
rec:b a src:Category ; src:broader rec:c .
rec:c a src:Category ; src:broader rec:a .
rec:d a src:Category ; src:broader rec:a .
rec:e a src:Category .
""", format="turtle")
    _, reported = evaluate(engine, mapping, cyclic)
    cycles = {focus for code, focus, _ in reported if code == "ClosureCycle"}
    assert cycles == {REC + n for n in ("a", "b", "c")}
    assert {value for code, _, value in reported if code == "ClosureCycle"} == {CLOSURE}
    _, quiet = evaluate(engine, mapping, Graph().parse(data=HIERARCHY, format="turtle"))
    assert not [row for row in quiet if row[0] == "ClosureCycle"]


@pytest.mark.parametrize("engine", ENGINES)
def test_a_list_that_loops_back_is_reported_by_the_cell_that_reaches_itself(engine):
    mapping = compiled(bundle())
    looped = Graph().parse(data=PREFIXES + """
rec:b6 a src:Bundle ; src:items _:c1 .
_:c1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#first> rec:i1 ; <http://www.w3.org/1999/02/22-rdf-syntax-ns#rest> _:c1 .
""", format="turtle")
    _, reported = evaluate(engine, mapping, looped)
    assert [row for row in reported if row[0] == "ClosureCycle"] and not [row for row in evaluate(engine, mapping, source())[1] if row[0] == "ClosureCycle"]
