# SPDX-License-Identifier: MPL-2.0
"""The compiler against the catalogue example, and one small graph per refusal (README §16)."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path

import pytest
from rdflib import BNode, Dataset, Graph, Literal, URIRef

from mork_rdf import CompileError, Severity, compile_scheme, run
from mork_rdf import paths
from mork_rdf.model import REFERENCE_GRAPH
from rdflib.namespace import SH as SH_NS
RDF_TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

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
    assert (created, URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf"), URIRef(TGT + "Work")) in result.tbox
    assert (URIRef(dune), URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), created) in g


def test_the_compiler_says_what_it_left_out(compiled):
    found = {(f.code, f.mapping.rsplit("#", 1)[-1], f.severity) for f in compiled.findings}
    assert found == {
        ("BroadMatch", "Map_Ebook", Severity.WARNING),
        ("LookupLexical", "Map_Genre", Severity.INFO),
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
    assert set(out) == set(result.graph) | set(result.tbox) and any(str(s).startswith(BASE + "agent/") for s in out.subjects())


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
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> . @prefix owl: <http://www.w3.org/2002/07/owl#> .
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
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:intransitiveExactMatch tgt:unknown ; mork:dataRef \"src:p\" .", ("StratumUnknown", "A")),
    ("mm:A a mork:Lookup ; mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:exactRBoxMatch tgt:p .", ("LookupIncomplete", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:exactRBoxMatch tgt:p ; mork:dataRef \"src:p\" ; mork:placeholderMapping mm:X .", ("PlaceholderForm", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:mappingFor src:x ; mork:exactABoxMatch tgt:x .", ("CorrespondenceUnused", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:dataRef \"src:p\" .", ("Unclassified", "A")),
    ("mm:A a mork:Datum ; mork:mappingScheme mm:S ; mork:exactTBoxMatch tgt:Other .", ("NoIterator", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:precedes mm:B . mm:B mork:mappingScheme mm:S ; mork:precedes mm:A .", ("MorkShape", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:exactRBoxMatch tgt:p ; mork:dataRef \"src:p\" ; mork:assertsPropertyRanges tgt:X .", ("AxiomsOnExistingProperty", "A")),
    ("mm:A mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:exactRBoxMatch tgt:p ; mork:dataRef \"src:p\" ; mork:propertyMappingAssertions tgt:X .", ("NotCompiled", "A")),
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


# --- lookup comparisons (§7.3) ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("choice, matched, unresolved, lexical", [
    ("", 2, set(), True),                                                          # cast, with no datatype to cast to
    ("mork:lookupDatatype xsd:integer", 2, set(), False),                          # cast, the default
    ("mork:lookupComparison mork:LexicalComparison", 2, set(), False),
    ("mork:lookupComparison mork:TermComparison", 1, {"7"}, False),               # the string is not the integer
])
def test_a_lookup_compares_as_its_author_chose(choice, matched, unresolved, lexical):
    g = Graph().parse(data=HEAD + f"""mm:Code a mork:Lookup ; mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ;
        mork:exactRBoxMatch tgt:code ; mork:exactTBoxMatch tgt:Code ; mork:referenceDataPath tgt:number ;
        mork:dataRef "src:code" {'; ' + choice if choice else ''} .""", format="turtle")
    compiled = compile_scheme(g, MM + "S", base=BASE, at=AT)
    assert (("LookupLexical", MM + "Code") in {(f.code, f.mapping) for f in compiled.findings}) == lexical
    source = Graph().parse(data=f"<{REC}x> a <{SRC}Thing> ; <{SRC}code> \"7\" . <{REC}y> a <{SRC}Thing> ; <{SRC}code> 7 .", format="turtle")
    out = run(compiled, source, Graph().parse(data=f"<{TGT}Seven> a <{TGT}Code> ; <{TGT}number> 7 .", format="turtle"))
    assert len(list(out.graph.subject_objects(URIRef(TGT + "code")))) == matched
    assert {f.value for f in out.findings if f.code == "LookupUnresolved"} == unresolved


# --- deferred contexts (§7.5) ----------------------------------------------------------------------------------------

SPECIES = HEAD + """src:Species a mork:Entity . mm:SC a mork:DataConcept ; mork:representedAs src:Species .
src:Animal a mork:Entity . mm:AC a mork:DataConcept ; mork:representedAs src:Animal .
mm:GenSpecies a mork:DataMapping ; mork:mappingScheme mm:S ; mork:mappingFor mm:SC ; mork:broadTBoxCategoryMatch tgt:Animal ;
    mork:conceptNameTemplate "${src:name}" .
mm:Yield_Species a mork:DeferredContext ; mork:mappingScheme mm:S ; mork:yieldConcept mm:GenSpecies .
"""
SPECIES_SOURCE = f"""<{REC}s1> a <{SRC}Species> ; <{SRC}name> "Falcon" . <{REC}s2> a <{SRC}Species> ; <{SRC}name> "Owl" .
<{REC}a7> a <{SRC}Animal> ; <{SRC}species> "Falcon" . <{REC}a8> a <{SRC}Animal> ; <{SRC}species> "Dodo" .
<{REC}t> a <{SRC}Thing> ."""
TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")


def species(body: str):
    compiled = compile_scheme(Graph().parse(data=SPECIES + body, format="turtle"), MM + "S", base=BASE, at=AT)
    return compiled, run(compiled, Graph().parse(data=SPECIES_SOURCE, format="turtle"))


def test_a_class_named_from_data_types_a_node_made_from_the_same_record():
    """The datum reads the creation's name template over its own focus node, the common case."""
    compiled, out = species("mm:Specimen a mork:Datum ; mork:mappingScheme mm:S ; mork:mappingFor mm:SC ; mork:conceptName \"specimen\" ; "
                            "mork:dataRef \"src:name\" ; mork:exactTBoxMatch mm:Yield_Species .")
    assert not compiled.errors
    assert (URIRef(BASE + "Falcon"), URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf"), URIRef(TGT + "Animal")) in out.tbox
    assert (URIRef(BASE + "specimen/Falcon"), TYPE, URIRef(BASE + "Falcon")) in out.graph


def test_a_class_named_from_other_records_is_found_by_a_lookup_over_what_its_mapping_made():
    """Animal records name their species by text, so a lookup matches that text with the classes the species
    creation made, which the run has kept since an earlier stratum."""
    compiled, out = species("""mm:Animal a mork:Datum ; mork:mappingScheme mm:S ; mork:mappingFor mm:AC ; mork:conceptName "animal" ;
        mork:exactTBoxMatch tgt:Animal ; mork:referenceDataMapping mm:AnimalSpecies .
        mm:AnimalSpecies a mork:Lookup ; mork:mappingScheme mm:S ; mork:exactRBoxMatch rdf:type ;
        mork:exactTBoxMatch mm:Yield_Species ; mork:dataRef "src:species" ; mork:dataInline "" .""")
    assert not compiled.errors and compiled.strata == 2
    falcon = next(s for s in out.graph.subjects(TYPE, URIRef(BASE + "Falcon")))
    assert (falcon, TYPE, URIRef(TGT + "Animal")) in out.graph
    assert {(f.code, f.value) for f in out.findings} == {("LookupUnresolved", "Dodo")}


def test_a_deferred_context_yields_the_name_it_gives():
    compiled, out = species("""mm:Yield_Bird a mork:DeferredContext ; mork:mappingScheme mm:S ; mork:conceptName "#Bird" ;
        mork:yieldConcept mork:DeferredConceptIRI .
        mm:Item a mork:Datum ; mork:mappingScheme mm:S ; mork:mappingFor mm:C ; mork:conceptName "item" ;
        mork:exactTBoxMatch mm:Yield_Bird , tgt:Thing .""")
    assert not compiled.errors
    assert {o for o in out.graph.objects(None, TYPE)} == {URIRef(BASE + "Bird"), URIRef(TGT + "Thing")}


# --- domain and range axioms (§7.6) ----------------------------------------------------------------------------------

def _class_expression(g: Graph, node) -> object:
    """A class, or (combination, members) for an owl:unionOf or owl:intersectionOf."""
    from rdflib.collection import Collection
    from rdflib.namespace import OWL
    for combination in (OWL.unionOf, OWL.intersectionOf):
        items = g.value(node, combination)
        if items is not None:
            return (str(combination).rsplit("#", 1)[-1], frozenset(str(m) for m in Collection(g, items)))
    return str(node)


def axioms(body: str):
    compiled, out = species("mm:Knows a mork:DataMapping ; mork:mappingScheme mm:S ; mork:broadRBoxCategoryMatch owl:topObjectProperty ; "
                            "mork:conceptName \"#knows\" ; " + body + " .")
    assert not compiled.errors, compiled.errors
    knows = URIRef(BASE + "knows")
    from rdflib.namespace import OWL, RDFS
    found = set()
    for axiom in (RDFS.domain, RDFS.range):
        found |= {(axiom.rsplit("#", 1)[-1], _class_expression(out.tbox, o)) for o in out.tbox.objects(knows, axiom)}
    for restriction in out.tbox.subjects(OWL.onProperty, knows):
        for relation in (RDFS.subClassOf, OWL.equivalentClass):
            for subject in out.tbox.subjects(relation, restriction):
                for kind in (OWL.allValuesFrom, OWL.someValuesFrom):
                    filler = out.tbox.value(restriction, kind)
                    if filler is not None:
                        found.add((relation.rsplit("#", 1)[-1], _class_expression(out.tbox, subject), kind.rsplit("#", 1)[-1], _class_expression(out.tbox, filler)))
    assert (knows, RDFS.subPropertyOf, OWL.topObjectProperty) in out.tbox
    return found


A, B, C = (TGT + n for n in "ABC")


@pytest.mark.parametrize("body, expected", [
    ("mork:assertsPropertyDomains tgt:A , tgt:B ; mork:assertsPropertyRanges tgt:C",
     {("domain", ("unionOf", frozenset({A, B}))), ("range", C)}),
    ("mork:assertsPropertyDomains tgt:A , tgt:B ; mork:classCombination mork:IntersectionOfClasses",
     {("domain", ("intersectionOf", frozenset({A, B})))}),
    ("mork:assertsPropertyDomains tgt:A , tgt:B ; mork:assertsPropertyRanges tgt:C ; mork:axiomForm mork:UniversalRestriction",
     {("subClassOf", A, "allValuesFrom", C), ("subClassOf", B, "allValuesFrom", C)}),
    ("mork:assertsPropertyDomains tgt:A ; mork:axiomForm mork:ExistentialRestriction , mork:GlobalAxioms",
     {("subClassOf", A, "someValuesFrom", "http://www.w3.org/2002/07/owl#Thing"), ("domain", A)}),
    ("mork:assertsPropertyDomains tgt:A , tgt:B ; mork:assertsPropertyRanges tgt:C ; mork:axiomForm mork:DefiningRestriction",
     {("equivalentClass", ("unionOf", frozenset({A, B})), "someValuesFrom", C)}),
    # classes made from data: combined at the closure, or restricted one by one
    ("mork:assertsPropertyDomains mm:Yield_Species , tgt:A", {("domain", ("unionOf", frozenset({A, BASE + "Falcon", BASE + "Owl"})))}),
    ("mork:assertsPropertyDomains mm:Yield_Species ; mork:assertsPropertyRanges tgt:C ; mork:axiomForm mork:UniversalRestriction",
     {("subClassOf", BASE + "Falcon", "allValuesFrom", C), ("subClassOf", BASE + "Owl", "allValuesFrom", C)}),
])
def test_a_created_property_gets_the_axioms_its_mapping_asks_for(body, expected):
    assert axioms(body) == expected


def test_a_restriction_whose_range_is_made_from_data_is_refused():
    compiled, _ = species("mm:Knows a mork:DataMapping ; mork:mappingScheme mm:S ; mork:broadRBoxCategoryMatch owl:topObjectProperty ; "
                          "mork:conceptName \"#knows\" ; mork:assertsPropertyDomains tgt:A ; mork:assertsPropertyRanges mm:Yield_Species ; "
                          "mork:axiomForm mork:UniversalRestriction .")
    assert ("RangeFromData", MM + "Knows") in {(f.code, f.mapping) for f in compiled.errors}


# --- MORK's own examples (README §16) --------------------------------------------------------------------------------

def _example(name: str):
    import lattice_repo_catalogue as reader
    catalogue = reader.load()
    return catalogue.root / catalogue.module("mork").directory("examples") / name


ZOO = "http://www.nebularis.org/ontologies/Zoo#"
OUT = "http://example.org/zoo#"


def zoo(name: str, scheme: str):
    g = Graph().parse(_example(name))
    compiled = compile_scheme(g, scheme, base=OUT, at=AT, target_vocabulary=Graph().parse(_example("Zoo/Zoo.ttl")))
    out = run(compiled, Graph())
    pairs = lambda graph: {(str(s).replace(OUT, ":").replace(ZOO, "zoo:"), str(p).rsplit("#", 1)[-1], str(o).replace(OUT, ":").replace(ZOO, "zoo:"))
                           for s, p, o in graph if not isinstance(o, BNode) and not isinstance(s, BNode)}
    return compiled, pairs(out.graph), pairs(out.tbox)


def test_the_property_generation_example_creates_what_its_notes_say():
    compiled, abox, tbox = zoo("Zoo/PropertyGeneration.ttl", "http://www.nebularis.org/ontologies/Zoo/PropertyGeneration#Mappings")
    assert not compiled.errors, compiled.errors
    assert abox == {(":Owl", "type", ":Species"), (":Owl", "isSpeciesOf", ":Bird"), (":Bird", "type", "zoo:Animal")}
    assert tbox == {(":Species", "type", "http://www.w3.org/2002/07/owl#Class"), (":Species", "subClassOf", "http://www.w3.org/2002/07/owl#Thing"),
                    (":isSpeciesOf", "subPropertyOf", "http://www.w3.org/2002/07/owl#topObjectProperty"),
                    (":isSpeciesOf", "domain", ":Species"), (":isSpeciesOf", "range", "zoo:Animal")}


def test_the_uncertain_mappings_example_types_each_hypothesis_with_classes_that_do_not_exist_yet():
    compiled, abox, tbox = zoo("Zoo/UncertainMappings.ttl", "http://www.nebularis.org/ontologies/UncertainMappings#Mappings")
    assert {(f.code, f.mapping.rsplit("#", 1)[-1]) for f in compiled.errors} == {
        ("Uncertain", "Map_EggSize"), ("Uncertain", "Map_Eggs"), ("Uncertain", "Map_Falcon"), ("Uncertain", "Map_Platypus"),
    }
    assert abox == {
        (":Falcon", "type", ":Bird"), (":Falcon", "type", ":Oviparous"), (":Falcon", "type", ":Pet"),
        (":Platypus", "type", ":Monotreme"), (":Platypus", "type", ":Oviparous"), (":Platypus", "type", ":Pet"),
        (":Falcon", "laysEggs", "true"), (":Platypus", "laysEggs", "true"),  # one assertion beneath two parents
    }
    subclass = {(s, o) for s, p, o in tbox if p == "subClassOf"}
    assert subclass == {(":Bird", ":Oviparous"), (":Bird", "zoo:Animal"), (":Monotreme", ":Oviparous"), (":Monotreme", "zoo:Mammal"),
                        (":Oviparous", "http://www.w3.org/2002/07/owl#Thing"), (":Eggs", "http://www.w3.org/2002/07/owl#Thing")}
    assert (":eggSize", "domain", ":Oviparous") in tbox


# --- sinks (§12.1) ---------------------------------------------------------------------------------------------------

def _streamed(compiled, source, reference=None):
    import io
    from mork_rdf import NTriplesSink
    abox, tbox = io.StringIO(), io.StringIO()
    result = run(compiled, source, reference, sink=NTriplesSink(abox, tbox))
    parse_nt = lambda text: Graph().parse(data=text, format="nt")
    return result, parse_nt(abox.getvalue()), parse_nt(tbox.getvalue())


def test_a_streamed_run_writes_what_a_run_in_memory_returns(compiled, result):
    streamed, abox, tbox = _streamed(compiled, parse("catalogue-source.ttl"), parse("catalogue-reference.ttl"))
    assert streamed.graph is None and streamed.findings == result.findings
    assert set(abox) == set(result.graph) and set(tbox) == set(result.tbox)


def test_a_streamed_run_still_reads_an_earlier_stratum():
    """The species classes are kept in the store for the lookup that reads them, though they also went to the sink."""
    from rdflib.compare import isomorphic
    compiled, out = species("""mm:Animal a mork:Datum ; mork:mappingScheme mm:S ; mork:mappingFor mm:AC ; mork:conceptName "animal" ;
        mork:exactTBoxMatch tgt:Animal ; mork:referenceDataMapping mm:AnimalSpecies .
        mm:AnimalSpecies a mork:Lookup ; mork:mappingScheme mm:S ; mork:exactRBoxMatch rdf:type ;
        mork:exactTBoxMatch mm:Yield_Species ; mork:dataRef "src:species" ; mork:dataInline "" .
        mm:Knows a mork:DataMapping ; mork:mappingScheme mm:S ; mork:broadRBoxCategoryMatch owl:topObjectProperty ;
        mork:conceptName "#knows" ; mork:assertsPropertyDomains mm:Yield_Species , tgt:A .""")
    streamed, abox, tbox = _streamed(compiled, Graph().parse(data=SPECIES_SOURCE, format="turtle"))
    assert set(abox) == set(out.graph) and isomorphic(tbox, out.tbox) and streamed.findings == out.findings


# --- the compiled mapping as RDF (§11.1) -----------------------------------------------------------------------------

def test_a_compiled_mapping_described_in_rdf_reads_back_as_the_same_compilation(compiled):
    from mork_rdf import from_rdf, to_rdf
    g = to_rdf(compiled)
    again = from_rdf(Graph().parse(data=g.serialize(format="turtle"), format="turtle"))
    assert again == compiled and str(g.identifier).endswith(compiled.digest)


def test_a_stratified_compilation_keeps_its_strata_reads_and_closures_in_rdf():
    from mork_rdf import from_rdf, to_rdf
    compiled, _ = species("""mm:Knows a mork:DataMapping ; mork:mappingScheme mm:S ; mork:broadRBoxCategoryMatch owl:topObjectProperty ;
        mork:conceptName "#knows" ; mork:assertsPropertyDomains mm:Yield_Species , tgt:A .""")
    assert compiled.closures and from_rdf(to_rdf(compiled)) == compiled


def test_a_description_whose_query_was_changed_is_refused(compiled):
    from mork_rdf import from_rdf, to_rdf
    from mork_rdf.model import SH
    g = to_rdf(compiled)
    query, text = next(g.subject_objects(SH.construct))
    g.set((query, SH.construct, Literal(str(text) + " ")))
    with pytest.raises(ValueError):
        from_rdf(g)


# --- the skolem rule, version 1 (§12.2) ------------------------------------------------------------------------------

VECTORS = FIXTURES.parent / "skolem-vectors"


def _skolemised(text: str, seed: int | None = None):
    import pyoxigraph as ox
    from mork_rdf.skolem import skolemise_with_report
    triples = list(ox.parse(text.encode(), format=ox.RdfFormat.TURTLE))
    if seed is not None:
        random.Random(seed).shuffle(triples)
    report = skolemise_with_report(triples)
    return {f"{t} ." for t in report.triples}, report.components


@pytest.mark.parametrize("name", ["tree", "irregular"])
def test_each_skolem_vector_gives_exactly_its_expected_triples(name):
    """The vectors pin the rule. A change to any IRI they hold is a change of rule, and needs a new version."""
    got, _ = _skolemised((VECTORS / f"{name}.ttl").read_text())
    expected = {line for line in (VECTORS / f"{name}.expected.nt").read_text().splitlines() if line}
    assert got == expected


def test_a_tree_node_is_named_as_the_rule_says():
    """The README's rule, computed by hand: the description hash, then the name from the parent, predicate and
    description, terms written as N-Triples."""
    import hashlib
    sha = lambda text: hashlib.sha256(text.encode("utf-8")).hexdigest()
    s = "http://example.org/src#"
    address = sha(f'<{s}city> "Tacoma"')
    author = sha("\n".join(sorted([f"<{s}address> _:{address}", f'<{s}name> "Frank Herbert"'])))
    author_name = sha(f"v1\n<http://example.org/records/dune>\n<{s}author>\n{author}")
    address_name = sha(f"v1\n<urn:mork-rdf:skolem:v1:{author_name}>\n<{s}address>\n{address}")
    got, _ = _skolemised((VECTORS / "tree.ttl").read_text())
    assert f'<urn:mork-rdf:skolem:v1:{author_name}> <{s}name> "Frank Herbert" .' in got
    assert f'<urn:mork-rdf:skolem:v1:{address_name}> <{s}city> "Tacoma" .' in got


def test_skolem_names_do_not_depend_on_the_order_of_the_triples():
    text = (VECTORS / "tree.ttl").read_text() + (VECTORS / "irregular.ttl").read_text().split("@prefix s: <http://example.org/src#> .")[1]
    first, _ = _skolemised(text, 0)
    assert all(_skolemised(text, seed)[0] == first for seed in (1, 2, 3))


def test_a_skolem_name_survives_unrelated_additions_and_changes_with_its_own_description():
    head = "@prefix s: <http://example.org/src#> .\n"
    dune = '<http://example.org/records/dune> s:author [ s:name "Frank Herbert" ] .\n'
    alone, _ = _skolemised(head + dune)
    beside, _ = _skolemised(head + dune + '<http://example.org/records/x> s:author [ s:name "Someone" ] .\n')
    renamed, _ = _skolemised(head + dune.replace("Frank Herbert", "F. Herbert"))
    assert alone <= beside
    assert not ({t.split()[0] for t in alone if "#name" in t} & {t.split()[0] for t in renamed if "#name" in t})


def test_identical_siblings_stay_distinct_and_irregular_components_are_reported():
    got, components = _skolemised((VECTORS / "tree.ttl").read_text())
    assert len({t.split()[0] for t in got if '"Anon"' in t}) == 2
    _, components = _skolemised((VECTORS / "irregular.ttl").read_text())
    assert sorted(n for _, n in components) == [1, 1, 2]  # the shared node, the orphan, and the cycle of two


def test_a_run_reports_the_blank_nodes_named_by_their_component():
    compiled = compile_scheme(Graph().parse(data=HEAD, format="turtle"), MM + "S", base=BASE, at=AT)
    source = Graph().parse(data=f"<{REC}x> a <{SRC}Thing> . _:a <{SRC}knows> _:b . _:b <{SRC}knows> _:a .", format="turtle")
    found = [f for f in run(compiled, source).findings if f.code == "SkolemCanonical"]
    assert len(found) == 1 and found[0].value == "2" and found[0].severity is Severity.WARNING


# --- validation before compiling (§4.3) ------------------------------------------------------------------------------

def _shape_graphs():
    yield "catalogue", parse("catalogue-mapping.ttl")
    yield "property generation", Graph().parse(_example("Zoo/PropertyGeneration.ttl"))
    yield "uncertain mappings", Graph().parse(_example("Zoo/UncertainMappings.ttl"))
    import lattice_repo_catalogue as reader
    cat = reader.load()
    yield "odrl", Graph().parse(cat.root / cat.area("contracts") / "config-studio" / "odrl" / "odrl-instrument.mork.ttl")
    yield "a precedence cycle", Graph().parse(data=HEAD + "mm:A mork:mappingScheme mm:S ; mork:precedes mm:B . mm:B mork:mappingScheme mm:S ; mork:precedes mm:A .", format="turtle")


@pytest.mark.parametrize("name, g", list(_shape_graphs()), ids=lambda x: x if isinstance(x, str) else "")
def test_validating_against_the_closed_specification_finds_what_full_inference_finds(name, g):
    """The compiler closes MORK's specification once and entails only the mapping graph's own triples, which must find
    exactly what pySHACL's RDFS inference over the mapping and the whole specification finds."""
    import pyshacl
    from mork_rdf.layer import entail, load, validate

    layer = load()
    assert entail(g, layer) is not None or name == "uncertain mappings", "only a graph stating schema takes the full closure"
    conforms, report, _ = pyshacl.validate(g, shacl_graph=layer.shapes, ont_graph=layer.spec, inference="rdfs", advanced=True, allow_warnings=True)
    full = set()
    if not conforms:
        from rdflib.namespace import SH
        for result in report.subjects(SH.resultSeverity, None):
            full.add((str(report.value(result, SH.focusNode)), str(report.value(result, SH.resultMessage)), str(report.value(result, SH.resultSeverity))))
    fast = {(f.mapping, f.message, {"error": str(SH_NS.Violation), "warning": str(SH_NS.Warning), "info": str(SH_NS.Info)}[f.severity.value]) for f in validate(g, layer)}
    assert fast == full
    assert name != "a precedence cycle" or fast, "the cycle breaks a shape, so the comparison is not vacuous"


# --- guards (§7.7) ---------------------------------------------------------------------------------------------------

GUARD_DATA = f"""@prefix src: <{SRC}> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
src:Sub <http://www.w3.org/2000/01/rdf-schema#subClassOf> src:Kind .
src:n1 a src:Thing ; src:op src:lt ; src:value 1 ; src:tag src:red .
src:n2 a src:Thing ; src:op src:eq ; src:value "1"^^xsd:integer , "01"^^xsd:integer ; src:tag src:red , src:blue .
src:n3 a src:Thing ; src:value "x" .
src:n4 a src:Thing ; src:op src:lteq ; src:tag src:green ; src:kind src:k1 .
src:n5 a src:Thing ; src:op src:lt , src:gt ; src:value 7 .
src:k1 a src:Sub . src:k2 a src:Other .
src:n6 a src:Thing ; src:kind src:k2 ; src:tag "red" .
src:pointer src:points src:n4 .
"""
GUARD_SHAPES = {
    "in, no value conforms": "sh:property [ sh:path src:op ; sh:in ( src:lt src:lteq ) ]",
    "in, required": "sh:property [ sh:path src:op ; sh:minCount 1 ; sh:in ( src:lt src:lteq ) ]",
    "has value on a path": "sh:property [ sh:path src:tag ; sh:hasValue src:red ]",
    "at most one": "sh:property [ sh:path src:value ; sh:maxCount 1 ]",
    "none": "sh:property [ sh:path src:op ; sh:maxCount 0 ]",
    "class through a subclass": "sh:property [ sh:path src:kind ; sh:class src:Kind ]",
    "datatype": "sh:property [ sh:path src:value ; sh:datatype xsd:integer ]",
    "node kind": "sh:property [ sh:path src:tag ; sh:nodeKind sh:IRI ]",
    "the node itself": "sh:in ( src:n1 src:n3 )",
    "the node's own value": "sh:hasValue src:n2",
    "a literal by term": "sh:property [ sh:path src:value ; sh:in ( 1 ) ]",
    "not": "sh:not [ sh:property [ sh:path src:tag ; sh:hasValue src:red ] ]",
    "and": "sh:and ( [ sh:property [ sh:path src:op ; sh:minCount 1 ] ] [ sh:property [ sh:path src:value ; sh:maxCount 1 ] ] )",
    "or": "sh:or ( [ sh:property [ sh:path src:op ; sh:hasValue src:eq ] ] [ sh:property [ sh:path src:kind ; sh:minCount 1 ] ] )",
    "an inverse path": "sh:property [ sh:path [ sh:inversePath src:points ] ; sh:minCount 1 ]",
}
SHAPE_HEAD = f"@prefix sh: <http://www.w3.org/ns/shacl#> . @prefix src: <{SRC}> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"


@pytest.fixture(scope="module")
def guard_data() -> Graph:
    return Graph().parse(data=GUARD_DATA, format="turtle")


@pytest.mark.parametrize("name", list(GUARD_SHAPES))
def test_a_compiled_guard_admits_exactly_the_nodes_that_conform_to_its_shape(name, guard_data):
    """pySHACL is the oracle: one validation of every node against the shape, and the compiled guard run over the same
    graph, must agree node for node."""
    import pyoxigraph as ox
    import pyshacl
    from mork_rdf.compile import _term
    from mork_rdf.guards import compile_guard

    shapes = Graph().parse(data=SHAPE_HEAD + f"src:Guard a sh:NodeShape ; {GUARD_SHAPES[name]} .", format="turtle")
    things = set(guard_data.subjects(RDF_TYPE, URIRef(SRC + "Thing")))
    targeted = Graph() + shapes  # a guard names no target, since its mapping gives the focus, so the oracle adds one
    targeted.add((URIRef(SRC + "Guard"), SH_NS.targetClass, URIRef(SRC + "Thing")))
    _, report, _ = pyshacl.validate(guard_data, shacl_graph=targeted, inference="none", advanced=False)
    failing = {report.value(r, SH_NS.focusNode) for r in report.subjects(RDF_TYPE, SH_NS.ValidationResult)}
    counter = iter(range(10_000))
    expression = compile_guard(shapes, URIRef(SRC + "Guard"), "?f", _term, lambda stem: f"?{stem}{next(counter)}")
    store = ox.Store()
    store.load(guard_data.serialize(format="nt").encode(), ox.RdfFormat.N_TRIPLES)
    admitted = {URIRef(row["f"].value) for row in store.query(f"SELECT ?f WHERE {{ ?f a <{SRC}Thing> FILTER ({expression}) }}")}
    assert admitted == things - failing


@pytest.mark.parametrize("shape, said", [
    ("sh:property [ sh:path src:op ; sh:pattern \"^l\" ]", "shacl#pattern"),
    ("sh:property [ sh:path src:op ; sh:minCount 2 ]", "0 or 1"),
    ("sh:property [ sh:path ( src:op src:value ) ; sh:minCount 1 ]", "sh:path"),
])
def test_a_guard_the_compiler_cannot_compile_refuses_its_mapping(shape, said):
    g = Graph().parse(data=HEAD + SHAPE_HEAD.split(" . ", 1)[0] + " .\n" + f"""mm:A a mork:Datum ; mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ;
        mork:exactTBoxMatch tgt:Other ; mork:appliesWhen [ a sh:NodeShape ; {shape} ] .""", format="turtle")
    refused = [f for f in compile_scheme(g, MM + "S", base=BASE, at=AT).errors if f.code == "GuardUnsupported"]
    assert refused and said in refused[0].message


def test_guarded_siblings_divide_the_nodes_of_their_path():
    g = Graph().parse(data=HEAD + SHAPE_HEAD.split(" . ", 1)[0] + " .\n" + """
        mm:Low a mork:DataMapping ; mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ;
            mork:exactRBoxMatch tgt:low ; mork:dataRef "src:value" ;
            mork:appliesWhen [ a sh:NodeShape ; sh:property [ sh:path src:op ; sh:minCount 1 ; sh:in ( src:lt ) ] ] .
        mm:High a mork:DataMapping ; mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ;
            mork:exactRBoxMatch tgt:high ; mork:dataRef "src:value" ;
            mork:appliesWhen [ a sh:NodeShape ; sh:property [ sh:path src:op ; sh:minCount 1 ; sh:in ( src:gt ) ] ] .""", format="turtle")
    compiled = compile_scheme(g, MM + "S", base=BASE, at=AT)
    assert not compiled.errors
    source = Graph().parse(data=f"<{REC}a> a <{SRC}Thing> ; <{SRC}op> <{SRC}lt> ; <{SRC}value> 1 . <{REC}b> a <{SRC}Thing> ; <{SRC}op> <{SRC}gt> ; <{SRC}value> 9 .", format="turtle")
    out = run(compiled, source).graph
    assert {(str(p).rsplit("#", 1)[-1], str(o)) for _, p, o in out if str(p).startswith(TGT)} == {("low", "1"), ("high", "9")}


def test_a_node_no_guarded_sibling_admits_is_reported():
    g = Graph().parse(data=HEAD + SHAPE_HEAD.split(" . ", 1)[0] + " .\n" + """
        mm:Item a mork:DataConcept ; mork:path "src:item" .
        mm:Lt a mork:Datum ; mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:mappingFor mm:Item ;
            mork:exactTBoxMatch tgt:Low ; mork:inverseRBoxMatch tgt:has ;
            mork:appliesWhen [ a sh:NodeShape ; sh:property [ sh:path src:op ; sh:minCount 1 ; sh:in ( src:lt ) ] ] .
        mm:Gt a mork:Datum ; mork:mappingScheme mm:S ; mork:compositeBroaderMapping mm:Root ; mork:mappingFor mm:Item ;
            mork:exactTBoxMatch tgt:High ; mork:inverseRBoxMatch tgt:has ;
            mork:appliesWhen [ a sh:NodeShape ; sh:property [ sh:path src:op ; sh:minCount 1 ; sh:in ( src:gt ) ] ] .""", format="turtle")
    compiled = compile_scheme(g, MM + "S", base=BASE, at=AT)
    assert not compiled.errors
    source = Graph().parse(data=f"""<{REC}t> a <{SRC}Thing> ; <{SRC}item> <{REC}i1> , <{REC}i2> , <{REC}i3> .
        <{REC}i1> <{SRC}op> <{SRC}lt> . <{REC}i2> <{SRC}op> <{SRC}gt> . <{REC}i3> <{SRC}op> <{SRC}eq> .""", format="turtle")
    out = run(compiled, source)
    assert {(f.code, f.focus) for f in out.findings} == {("Unguarded", REC + "i3")}
    assert len(set(out.graph.subjects(RDF_TYPE, None))) == 3  # the root and the two admitted items


def test_a_concept_placed_by_mork_representation_scheme_in_another_format_is_left_to_its_backend():
    """MCN places a concept in its representation scheme with mork:representationScheme, not skos:inScheme."""
    g = Graph().parse(data=HEAD + """mm:Json a mork:RepresentationScheme ; mork:format mork:JSON .
        mm:J a mork:DataConcept ; mork:representationScheme mm:Json .
        mm:A a mork:Datum ; mork:mappingScheme mm:S ; mork:mappingFor mm:J ; mork:dataRef "loanId" ; mork:exactTBoxMatch tgt:Other .""", format="turtle")
    compiled = compile_scheme(g, MM + "S", base=BASE, at=AT)
    assert ("OtherBackend", MM + "A") in {(f.code, f.mapping) for f in compiled.findings} and not compiled.errors
