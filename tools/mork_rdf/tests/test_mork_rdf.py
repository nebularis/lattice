# SPDX-License-Identifier: MPL-2.0
"""The compiler against the catalogue example, and one small graph per refusal (README §16)."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path

import pytest
from rdflib import Dataset, Graph, Literal, URIRef

from mork_rdf import CompileError, Severity, compile_scheme, run
from mork_rdf import paths
from mork_rdf.model import REFERENCE_GRAPH

FIXTURES = Path(__file__).parent / "fixtures"
SCHEME = "http://example.org/mapping#Catalogue"
BASE = "http://example.org/out/"
AT = datetime(2026, 10, 29, tzinfo=timezone.utc)
SRC, TGT, REC, MM = (f"http://example.org/{n}" for n in ("src#", "tgt#", "records/", "mapping#"))


def parse(name: str) -> Graph:
    return Graph().parse(FIXTURES / name)


@pytest.fixture(scope="module")
def mapping() -> Graph:
    return parse("catalogue-mapping.ttl")


@pytest.fixture(scope="module")
def vocabulary() -> Graph:
    return parse("catalogue-vocabulary.ttl")


@pytest.fixture(scope="module")
def compiled(mapping, vocabulary):
    return compile_scheme(mapping, SCHEME, base=BASE, at=AT, target_vocabulary=vocabulary)


@pytest.fixture(scope="module")
def result(compiled):
    return run(compiled, parse("catalogue-source.ttl"), parse("catalogue-reference.ttl"))


def objects(g: Graph, s: str, p: str) -> set:
    return {str(o) for o in g.objects(URIRef(s), URIRef(TGT + p))}


# --- property paths (§4.2) ------------------------------------------------------------------------------------------

PREFIXES = {"src": SRC, "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}


RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"


@pytest.mark.parametrize("text, written", [
    ("src:author", f"<{SRC}author>"),
    ("a", f"<{RDF_NS}type>"),
    ("^src:author/src:name", f"^<{SRC}author>/<{SRC}name>"),
    ("src:and/rdf:rest*/rdf:first", f"<{SRC}and>/<{RDF_NS}rest>*/<{RDF_NS}first>"),
    ("src:a|src:b", f"<{SRC}a>|<{SRC}b>"),
    ("!(src:a|^src:b)", f"!<{SRC}a>|^<{SRC}b>"),
    ("<http://example.org/x>?", "<http://example.org/x>?"),
])
def test_a_path_is_written_back_from_its_tree(text, written):
    out = paths.write(paths.parse(text, PREFIXES))
    assert paths.write(paths.parse(out, {})) == out  # what is written parses back to itself
    assert out.replace("(", "").replace(")", "") == written.replace("(", "").replace(")", "")


@pytest.mark.parametrize("text", [
    "ex:author",                    # an undeclared prefix
    "src:author } . DROP ALL #",    # text after the path
    "<not an iri>",                 # a space in an IRI
    "<relative>",                   # not absolute
    "src:a/",                       # a dangling step
    "(src:a",                       # unclosed
])
def test_a_path_that_is_not_one_is_refused(text):
    with pytest.raises(paths.PathError):
        paths.parse(text, PREFIXES)


# --- the catalogue (§15) --------------------------------------------------------------------------------------------

def test_every_construct_maps_what_its_mapping_says(result):
    g = result.graph
    dune, tract, ebook = "http://example.org/work/978-0441013593", "http://example.org/work/978-1", "http://example.org/work/978-2"
    assert objects(g, dune, "title") == {"Dune"}                       # through the label template
    assert objects(g, dune, "medium") == {TGT + "Print"}                # through the correspondence table
    assert objects(g, ebook, "medium") == {TGT + "Digital"}             # a broad correspondence
    assert objects(g, dune, "genre") == {TGT + "SF"}                    # a lookup into the reference graph
    assert objects(g, dune, "status") == {"listed"}                     # the mapping in force, not the one it supersedes
    assert objects(g, dune, "year") == {"1965"}                         # a generic match, typed by the vocabulary
    assert not objects(g, dune, "subtitle") and not objects(g, dune, "shelfmark")  # uncertain and retired
    assert (URIRef(dune), None, None) in g and not any(str(s).endswith("dune-2") for s in g.subjects())
    (author,) = objects(g, dune, "creator")                             # contextual, glued by the inverse match
    assert author.startswith(BASE + "agent/") and objects(g, author, "name") == {"Frank Herbert"}
    assert len(objects(g, tract, "creator")) == 2                       # two blank-node authors stay two
    assert not objects(g, tract, "genre") and not objects(g, tract, "medium")
    assert objects(g, TGT + "SF", "shelf") == {"3"}                     # a lookup as the whole identity
    created = URIRef(BASE + "CatalogueItem")
    assert (created, URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf"), URIRef(TGT + "Work")) in g
    assert (URIRef(dune), URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), created) in g


def test_the_compiler_says_what_it_left_out(compiled):
    found = {(f.code, f.mapping.rsplit("#", 1)[-1], f.severity) for f in compiled.findings}
    assert found == {
        ("BroadMatch", "Map_Ebook", Severity.WARNING),
        ("NotInForce", "Map_Retired", Severity.INFO),
        ("Superseded", "Map_StatusV1", Severity.INFO),
        ("Uncertain", "Map_Maybe", Severity.ERROR),
    }


def test_the_checks_name_each_focus_node_left_unmapped(result):
    rows = {(f.code, f.mapping.rsplit("#", 1)[-1], f.focus, f.value) for f in result.findings}
    assert rows == {
        ("IdentityUnbound", "Map_Item", REC + "dune-2", None),
        ("LookupUnresolved", "Map_Genre", REC + "tract", "HOR"),
        ("UnmappedValue", "Map_Medium", REC + "tract", SRC + "Audiobook"),
    }


def test_confidence_compounds_through_the_dag(compiled):
    confidence = dict(compiled.confidence)
    assert confidence[MM + "Map_Title"] == 0.8
    assert confidence[MM + "Map_Item"] == pytest.approx(0.9 * 0.8)


def test_every_query_is_traceable_to_its_mapping(compiled):
    text = compiled.text()
    for query in compiled.queries:
        assert f"for <{query.mapping}>" in text and query.path[-1] == query.mapping


# --- determinism (PRI-58) -------------------------------------------------------------------------------------------

def test_compilation_is_the_same_for_any_order_of_the_mapping_graph(mapping, vocabulary, compiled):
    triples = list(mapping)
    for seed in range(3):
        random.Random(seed).shuffle(triples)
        shuffled = Graph()
        for t in triples:
            shuffled.add(t)
        again = compile_scheme(shuffled, SCHEME, base=BASE, at=AT, target_vocabulary=vocabulary)
        assert again.text() == compiled.text() and again.mapping_digest == compiled.mapping_digest


def test_a_run_is_the_same_for_any_order_of_the_source(compiled, result):
    source = list(parse("catalogue-source.ttl"))
    for seed in range(3):
        random.Random(seed).shuffle(source)
        g = Graph()
        for t in source:
            g.add(t)
        again = run(compiled, g, parse("catalogue-reference.ttl"))
        assert set(again.graph) == set(result.graph) and again.findings == result.findings


def test_the_queries_mean_the_same_on_rdflib(compiled, result):
    """The constructs are SPARQL 1.1 with nothing engine-specific, so rdflib gives Oxigraph's triples."""
    from mork_rdf.run import skolemise

    import pyoxigraph as ox

    dataset = Dataset()
    skolemised = ox.serialize(skolemise(parse("catalogue-source.ttl")), format=ox.RdfFormat.N_TRIPLES).decode("utf-8")
    for t in Graph().parse(data=skolemised, format="nt"):
        dataset.default_graph.add(t)
    reference = dataset.graph(URIRef(REFERENCE_GRAPH))
    for t in parse("catalogue-reference.ttl"):
        reference.add(t)
    out = Graph()
    for query in compiled.constructs:
        for triple in dataset.query(query.text):
            out.add(triple)
    assert set(out) == set(result.graph) and any(str(s).startswith(BASE + "agent/") for s in out.subjects())


# --- time, governance and confidence (§9) ----------------------------------------------------------------------------

def test_before_the_successor_takes_effect_the_older_mapping_is_in_force(mapping, vocabulary):
    earlier = compile_scheme(mapping, SCHEME, base=BASE, at=datetime(2025, 6, 1, tzinfo=timezone.utc), target_vocabulary=vocabulary)
    g = run(earlier, parse("catalogue-source.ttl"), parse("catalogue-reference.ttl")).graph
    assert objects(g, "http://example.org/work/978-0441013593", "status") == {"catalogued"}


def test_below_the_confidence_floor_a_mapping_and_its_children_drop(mapping, vocabulary):
    floor = compile_scheme(mapping, SCHEME, base=BASE, at=AT, target_vocabulary=vocabulary, min_confidence=0.85)
    codes = {(f.code, f.mapping.rsplit("#", 1)[-1]) for f in floor.findings}
    assert ("BelowConfidence", "Map_Item") in codes and ("ParentNotCompiled", "Map_Author") in codes


def test_a_production_scheme_with_an_error_does_not_compile(mapping, vocabulary):
    production = Graph() + mapping
    production.remove((URIRef(SCHEME), URIRef("http://www.nebularis.org/ontologies/Mork#compilationMode"), None))
    production.add((URIRef(SCHEME), URIRef("http://www.nebularis.org/ontologies/Mork#compilationMode"), URIRef("http://www.nebularis.org/ontologies/Mork#ProductionMode")))
    with pytest.raises(CompileError) as raised:
        compile_scheme(production, SCHEME, base=BASE, at=AT, target_vocabulary=vocabulary)
    assert {f.code for f in raised.value.findings if f.severity is Severity.ERROR} == {"Uncertain"}


def test_time_is_an_input_with_a_timezone(mapping):
    with pytest.raises(CompileError):
        compile_scheme(mapping, SCHEME, base=BASE, at=datetime(2026, 10, 29))


# --- refusals (§10) -------------------------------------------------------------------------------------------------

HEAD = f"""@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix mm: <{MM}> . @prefix src: <{SRC}> . @prefix tgt: <{TGT}> .
mm:S a mork:MappingScheme ; sh:declare [ sh:prefix "src" ; sh:namespace "{SRC}"^^xsd:anyURI ] .
src:Thing a mork:Entity . mm:C a mork:DataConcept ; mork:representedAs src:Thing .
mm:Root a mork:Datum ; mork:mappingScheme mm:S ; mork:mappingFor mm:C ; mork:exactTBoxMatch tgt:Thing .
"""


def refusals(body: str, vocabulary: Graph | None = None) -> set:
    g = Graph().parse(data=HEAD + body, format="turtle")
    compiled = compile_scheme(g, MM + "S", base=BASE, at=AT, target_vocabulary=vocabulary)
    return {(f.code, (f.mapping or "").rsplit("#", 1)[-1]) for f in compiled.findings if f.severity is not Severity.INFO}


@pytest.mark.parametrize("body, expected", [
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:narrowRBoxCategoryMatch tgt:p ; mork:dataRef \"src:p\" .", ("NarrowMatch", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:exactRBoxMatch tgt:p ; mork:dataRef \"ex:p\" .", ("BadPath", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:exactRBoxMatch tgt:p .", ("NoValue", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:exactRBoxMatch tgt:p ; mork:dataRef \"src:p\" .", ("NoParent", "A")),
    ("mm:Two a mork:Datum ; mork:mappingScheme mm:S ; mork:mappingFor mm:C .\n"
     "mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root , mm:Two ; mork:exactRBoxMatch tgt:p ; mork:dataRef \"src:p\" .", ("SeveralParents", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:intransitiveExactMatch tgt:unknown ; mork:dataRef \"src:p\" .", ("StratumUnknown", "A")),
    ("mm:A a mork:Lookup ; mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:exactRBoxMatch tgt:p .", ("LookupIncomplete", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:exactRBoxMatch tgt:p ; mork:dataRef \"src:p\" ; mork:placeholderMapping mm:X .", ("PlaceholderForm", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:mappingFor src:x ; mork:exactABoxMatch tgt:x .", ("CorrespondenceUnused", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:dataRef \"src:p\" .", ("Unclassified", "A")),
    ("mm:A a mork:Datum ; mork:mappingScheme mm:S ; mork:exactTBoxMatch tgt:Other .", ("NoIterator", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:precedes mm:B . mm:B mork:mappingScheme mm:S ; mork:precedes mm:A .", ("MorkShape", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:exactRBoxMatch tgt:p ; mork:dataRef \"src:p\" ; mork:assertsPropertyRanges tgt:X .", ("NotCompiled", "A")),
    ("mm:A a mork:Lookup ; mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:exactRBoxMatch tgt:p ; mork:exactTBoxMatch tgt:G ; mork:dataRef \"src:p\" ; mork:dataInline \"fixed\" .", ("LookupInline", "A")),
])
def test_a_mapping_the_compiler_cannot_honour_is_refused_by_name(body, expected):
    assert expected in refusals(body)


def test_a_literal_for_an_object_property_is_reported_on_the_run():
    vocabulary = Graph().parse(data=f"<{TGT}p> a <http://www.w3.org/2002/07/owl#ObjectProperty> .", format="turtle")
    g = Graph().parse(data=HEAD + 'mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:exactRBoxMatch tgt:p ; mork:dataRef "src:p" .', format="turtle")
    compiled = compile_scheme(g, MM + "S", base=BASE, at=AT, target_vocabulary=vocabulary)
    source = Graph().parse(data=f"<{REC}x> a <{SRC}Thing> ; <{SRC}p> \"text\" .", format="turtle")
    assert {(f.code, f.value) for f in run(compiled, source).findings} == {("TermKind", "text")}


def test_an_ambiguous_lookup_is_reported_and_every_match_asserted():
    g = Graph().parse(data=HEAD + """mm:A a mork:Lookup ; mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ;
        mork:exactRBoxMatch tgt:genre ; mork:exactTBoxMatch tgt:Genre ;
        mork:referenceDataPath tgt:code ; mork:dataRef "src:genre" .""", format="turtle")
    compiled = compile_scheme(g, MM + "S", base=BASE, at=AT)
    source = Graph().parse(data=f"<{REC}x> a <{SRC}Thing> ; <{SRC}genre> \"G\" .", format="turtle")
    reference = Graph().parse(data=f"<{TGT}g1> a <{TGT}Genre> ; <{TGT}code> \"G\" . <{TGT}g2> a <{TGT}Genre> ; <{TGT}code> \"G\" .", format="turtle")
    out = run(compiled, source, reference)
    assert {f.code for f in out.findings} == {"LookupAmbiguous"}
    assert len(list(out.graph.objects(None, URIRef(TGT + "genre")))) == 2


def test_source_data_cannot_answer_a_lookup():
    """Lookups read only the reference graph, so a source that declares its own codes changes nothing (§13)."""
    g = Graph().parse(data=HEAD + """mm:A a mork:Lookup ; mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ;
        mork:exactRBoxMatch tgt:genre ; mork:exactTBoxMatch tgt:Genre ;
        mork:referenceDataPath tgt:code ; mork:dataRef "src:genre" .""", format="turtle")
    compiled = compile_scheme(g, MM + "S", base=BASE, at=AT)
    source = Graph().parse(data=f"<{REC}x> a <{SRC}Thing> ; <{SRC}genre> \"G\" . <{TGT}forged> a <{TGT}Genre> ; <{TGT}code> \"G\" .", format="turtle")
    out = run(compiled, source)
    assert not list(out.graph.objects(None, URIRef(TGT + "genre"))) and {f.code for f in out.findings} == {"LookupUnresolved"}


@pytest.mark.parametrize("match, reference", [
    ("mork:referenceDataPath tgt:code", "<{t}lob1> a <{t}LineOfBusiness> ; <{t}code> \"MAR\" ."),
    ("", "<{t}lob1> a <{t}LineOfBusiness> ; <http://www.nebularis.org/ontologies/Mork#dataInline> \"MAR\" ."),
    ('mork:dataInline ""', "<{t}MAR> a <{t}LineOfBusiness> ."),
])
def test_a_lookup_named_by_reference_data_mapping_matches_each_way_mork_allows(match, reference):
    """MORK's own example: a datum names its lookup with mork:referenceDataMapping, and the lookup matches on a
    predicate, on the reference individual's mork:dataInline, or with dataInline "" on its name (§7.3)."""
    g = Graph().parse(data=HEAD.replace("mork:exactTBoxMatch tgt:Thing .", "mork:exactTBoxMatch tgt:Thing ; mork:referenceDataMapping mm:Lob .")
                      + f"""mm:Lob a mork:Lookup ; mork:mappingScheme mm:S ; mork:exactRBoxMatch tgt:lob ;
        mork:exactTBoxMatch tgt:LineOfBusiness ; mork:dataRef "src:lineOfBusiness" {'; ' + match if match else ''} .""", format="turtle")
    compiled = compile_scheme(g, MM + "S", base=BASE, at=AT)
    assert not compiled.errors
    source = Graph().parse(data=f"<{REC}x> a <{SRC}Thing> ; <{SRC}lineOfBusiness> \"MAR\" . <{REC}y> a <{SRC}Thing> ; <{SRC}lineOfBusiness> \"AVN\" .", format="turtle")
    out = run(compiled, source, Graph().parse(data=reference.format(t=TGT), format="turtle"))
    assert len(list(out.graph.subject_objects(URIRef(TGT + "lob")))) == 1
    assert {(f.code, f.value) for f in out.findings} == {("LookupUnresolved", "AVN")}


def test_a_declared_entity_no_root_iterates_is_reported_on_the_run():
    g = Graph().parse(data=HEAD + "src:Orphan a mork:Entity .", format="turtle")
    compiled = compile_scheme(g, MM + "S", base=BASE, at=AT)
    source = Graph().parse(data=f"<{REC}x> a <{SRC}Thing> . <{REC}o> a <{SRC}Orphan> .", format="turtle")
    assert {(f.code, f.focus, f.value) for f in run(compiled, source).findings} == {("Uncovered", REC + "o", SRC + "Orphan")}


def test_a_mapping_whose_source_is_another_format_is_left_to_its_backend():
    g = Graph().parse(data=HEAD + """@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
        mm:Json a mork:RepresentationScheme ; mork:format mork:JSON . mm:J a mork:DataConcept ; skos:inScheme mm:Json .
        mm:A a mork:Datum ; mork:mappingScheme mm:S ; mork:mappingFor mm:J ; mork:exactTBoxMatch tgt:Other .""", format="turtle")
    compiled = compile_scheme(g, MM + "S", base=BASE, at=AT)
    assert ("OtherBackend", MM + "A") in {(f.code, f.mapping) for f in compiled.findings} and not compiled.errors
