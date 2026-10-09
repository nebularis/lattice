# SPDX-License-Identifier: MPL-2.0

"""The Wording layer's spec, vocab, examples and laws (computable-contract-substrate
C3, C4 and C5, ADR-A112). Row IDs are the slices' Validation Packs'. Reasoner rows skip when
the ADR-A83 harness jar is not built (``mise run bootstrap:reasoning-testkit``).
"""

from __future__ import annotations

import functools
import re
import sys
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, PROV, RDF, RDFS, SH, SKOS

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "mork_compilers" / "src"))

import literate_extract  # noqa: E402
from conftest import repo_files  # noqa: E402
from mork_compilers import reasoning  # noqa: E402
from ontology_catalog import Catalog, closure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "ontology" / "wording"
CATALOG = ROOT / "ontology" / "catalog-v001.xml"
LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
SPEC_IRI = "https://www.nebularis.org/neuro-semantic/wording"
VOCAB_IRI = "https://www.nebularis.org/neuro-semantic/wording-vocab"

WRD = Namespace(LATTICE + "wording#")
WRD_VOC = Namespace(LATTICE + "wording/vocab#")
VOC = Namespace(LATTICE + "vocabulary#")
FND = Namespace(LATTICE + "foundation#")
FACILITY = Namespace("https://example.org/lattice/wording/facility/")

EXAMPLES = sorted((LAYER / "examples").glob("*.ttl"))
FORMS = (WRD.partText, WRD.refersToVariable, WRD.refersToObject)
READ_WITH = {"facility-amendment": "facility-form"}  # an example that amends another is read with it


def _graph(*paths: Path) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path)
    return g


def _example(path: Path) -> Graph:
    other = READ_WITH.get(path.stem)
    return _graph(path, *([LAYER / "examples" / f"{other}.ttl"] if other else []))


@functools.lru_cache(maxsize=None)
def _vocab_closure() -> Graph:
    """TM1: used to rebuild the catalog closure on every call (python-test-melting
    sketch); cached since every caller only ever reads it or combines it with `+`
    (a new graph), never mutates it in place."""
    return closure(Catalog(CATALOG), VOCAB_IRI)


# ---- C3-01, C3-02, C3-03: imports, resolution, no higher layer ------------------

def test_c3_01_imports_exactly_the_layers_below() -> None:
    spec = _graph(LAYER / "spec" / "wording.ttl")
    ontology = URIRef(SPEC_IRI)
    assert spec.value(ontology, OWL.versionIRI) == URIRef(LATTICE + "wording/0.7.0")  # C4-01, C5, C8b
    assert set(spec.objects(ontology, OWL.imports)) == {
        URIRef(LATTICE + "foundation/0.4.0"),
        URIRef(LATTICE + "vocabulary/0.4.0"),
        URIRef(LATTICE + "quantification/0.7.0"),
        URIRef(LATTICE + "eligibility/0.10.0"),
    }


@pytest.mark.parametrize("iri", [SPEC_IRI, VOCAB_IRI])
def test_c3_02_closure_resolves(iri: str) -> None:
    assert len(closure(Catalog(CATALOG), iri)) > 0


def test_c3_03_names_no_higher_layer() -> None:
    files = [p for p in LAYER.rglob("*") if p.suffix in {".ttl", ".md"}]
    assert files
    for path in files:
        text = path.read_text()
        for higher in ("lattice/instrument", "lattice/behaviour", "ins:", "bhv:"):
            assert higher not in text, f"{path.relative_to(ROOT)} names {higher}"


# ---- C3-04: text parts --------------------------------------------------------

def _parts(graph: Graph, text: URIRef) -> list:
    return sorted(graph.objects(text, WRD.hasTextPart), key=lambda p: int(graph.value(p, WRD.partIndex)))


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_c3_04_every_text_is_indexed_parts_of_one_form(example: Path) -> None:
    graph = _graph(example)
    texts = set(graph.subjects(RDF.type, WRD.Text))
    assert texts
    for text in texts:
        parts = _parts(graph, text)
        assert [int(graph.value(p, WRD.partIndex)) for p in parts] == list(range(len(parts))), text
        for part in parts:
            assert sum(1 for form in FORMS if graph.value(part, form) is not None) == 1, part


def test_c3_04_clause_4_1_is_five_parts() -> None:
    graph = _graph(LAYER / "examples" / "facility-agreement.ttl")
    parts = _parts(graph, FACILITY["cl-4-1"])
    assert [graph.value(p, WRD.partText) for p in parts] == [
        Literal("The "), None, Literal(" shall pay interest at "), None, Literal(" per annum.")]
    assert graph.value(parts[1], WRD.refersToObject) == FACILITY["def-borrower-identity"]  # C8b: identities
    assert graph.value(parts[3], WRD.refersToVariable) == FACILITY["var-margin-identity"]


# ---- C3-05 to C3-07: the reasoner ---------------------------------------------

def _consistent(*extra: Graph) -> bool:
    graphs = [_vocab_closure(), *extra]
    return reasoning.run("consistent", graphs=graphs) is True


@pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")
@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_c3_05_examples_are_consistent(example: Path) -> None:
    assert _consistent(_example(example))


PREFIXES = f"@prefix wrd: <{WRD}> .\n@prefix ex: <https://example.org/w/> .\n"


@pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")
@pytest.mark.parametrize("data", [
    "ex:a a wrd:Element ; wrd:directlyComprises ex:a .",                                      # C3-06
    "ex:a a wrd:Element ; wrd:directlyComprises ex:b . ex:b wrd:directlyComprises ex:a .",    # C3-06
    "ex:a a wrd:Wording , wrd:Element .",                                                     # C3-07
    "ex:a a wrd:Text , wrd:Table .",                                                          # C3-07
    "ex:a a wrd:EmbeddedVariable , wrd:GoverningVariable .",                                  # C3-07
], ids=["self-comprising", "cycle-of-two", "wording-and-element", "text-and-table", "embedded-and-governing"])
def test_c3_06_07_ill_formed_trees_and_types_are_inconsistent(data: str) -> None:
    assert not _consistent(Graph().parse(data=PREFIXES + data, format="turtle"))


# ---- C3-08: the vocab ---------------------------------------------------------

def test_c3_08_three_contracts_each_constraining_its_property() -> None:
    vocab = _graph(LAYER / "vocab" / "wording-vocab.ttl")
    contracts = {
        WRD_VOC.ElementTypeContract: WRD.elementType,
        WRD_VOC.ClassificationContract: WRD.classification,
        WRD_VOC.DocumentKindContract: WRD.documentKind,
    }
    assert set(vocab.subjects(RDF.type, VOC.SchemeContract)) == set(contracts)
    for contract, prop in contracts.items():
        assert vocab.value(contract, VOC.constrainsProperty) == prop
        assert vocab.value(contract, FND.hasIdentity) is not None
        assert vocab.value(contract, FND.hasGovernanceState) is not None
    shapes = _graph(*(ROOT / "ontology" / "vocabulary" / "shapes").glob("*.ttl"))
    conforms, _, text = validate(_vocab_closure(), shacl_graph=shapes, advanced=True, inference="none")
    assert conforms, text


# ---- C3-09, C3-10: literate source and releases -------------------------------

def test_c3_09_readme_blocks_equal_the_files() -> None:
    assert literate_extract.main([str(LAYER / "README.md"), "--layer", "wording", "--root", str(ROOT),
                                  "--shapes", "shapes/structural.ttl", "shapes/constraints.ttl", "--check"]) == 0


def test_c3_10_both_versions_have_release_rows() -> None:
    register = (ROOT / "docs" / "architecture" / "ontology-releases.md").read_text()
    for tag in ("wording-v0.1.0", "wording-vocab-v0.1.0", "wording-shapes-v0.1.0"):
        assert f"| {tag} |" in register


# ---- C3-13: the baseline scheme covers every element type used ------------------

def test_c3_13_every_element_type_used_is_in_the_baseline_scheme() -> None:
    vocab = _graph(LAYER / "vocab" / "wording-vocab.ttl")
    baseline = set(vocab.subjects(SKOS.inScheme, WRD_VOC.ElementTypes))
    used = set()
    for example in EXAMPLES:
        used |= set(_graph(example).objects(None, WRD.elementType))
    readme = (LAYER / "README.md").read_text()
    for block in re.findall(r"```turtle-example\n(.*?)```", readme, re.S):
        used |= set(Graph().parse(data=f"@prefix wrd: <{WRD}> .\n@prefix wrd-voc: <{WRD_VOC}> .\n@prefix ex: <https://example.org/w/> .\n" + block,
                                  format="turtle").objects(None, WRD.elementType))
    assert used
    assert used <= baseline, used - baseline


# ---- C3-14 to C3-17: shapes, named unions, comments -----------------------------

SHAPES = _graph(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")


@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    """TM1/TM2: shared, session-scoped graphs and validation cache
    (python-test-melting)."""
    module = request.module
    module.SHAPES = graph_cache(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")
    module.validate = validated


def _violations(data: Graph, severity: URIRef = SH.Violation) -> set:
    """Focus-node local names of every result of one severity, with the spec closure in the data graph."""
    _, report, _ = validate(_vocab_closure() + data, shacl_graph=SHAPES, inference="none", advanced=True)
    return {str(report.value(result, SH.focusNode)).rsplit("/", 1)[-1]
            for result in report.subjects(SH.resultSeverity, severity)}


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_c3_14_examples_conform_to_the_shapes(example: Path) -> None:
    assert _violations(_example(example)) == set()


SHAPE_PREFIXES = PREFIXES + f"@prefix wrd-voc: <{WRD_VOC}> .\n@prefix qnt: <{LATTICE}quantification#> .\n"


@pytest.mark.parametrize("data, focus", [
    ("ex:t a wrd:Text ; wrd:hasTextPart ex:p . ex:p a wrd:TextPart ; wrd:partIndex 0 ; wrd:elementType wrd-voc:Clause .", "p"),
    ("ex:t a wrd:Text ; wrd:hasTextPart ex:p . ex:v a wrd:EmbeddedVariable . "
     "ex:p a wrd:TextPart ; wrd:partIndex 0 ; wrd:partText \"x\" ; wrd:refersToVariable ex:v .", "p"),
    ("ex:t a wrd:Text ; wrd:hasTextPart ex:p . ex:p a wrd:TextPart ; wrd:partIndex 0 .", "p"),
    ("ex:t a wrd:Text ; wrd:hasTextPart ex:p . ex:u a wrd:Text ; wrd:hasTextPart ex:p . "
     "ex:p a wrd:TextPart ; wrd:partIndex 0 ; wrd:partText \"x\" .", "p"),
    ("ex:t a wrd:Text ; wrd:hasTextPart ex:p . ex:p a wrd:TextPart ; wrd:partIndex -1 ; wrd:partText \"x\" .", "p"),
    ("ex:w a wrd:Wording ; wrd:rankKey \"a0\" .", "w"),
    ("ex:t a wrd:Text ; wrd:linksTo ex:d . ex:d a wrd:ExternalDocument .", "t"),
    ("ex:w a wrd:Wording ; wrd:directlyComprises ex:p . ex:p a wrd:TextPart .", "w"),
    ("ex:e a wrd:Element ; wrd:elementType wrd-voc:Clause , wrd-voc:Section .", "e"),
    ("ex:v a wrd:EmbeddedVariable ; wrd:valueSpace ex:not-a-space .", "v"),
], ids=["type-on-a-part", "two-forms", "no-form", "two-texts", "negative-index",
        "rank-key-on-a-wording", "links-from-a-text", "part-is-not-an-element", "two-types", "space-not-a-space"])
def test_c3_15_ill_formed_data_is_reported(data: str, focus: str) -> None:
    assert focus in _violations(Graph().parse(data=SHAPE_PREFIXES + data, format="turtle"))


@pytest.mark.parametrize("name, members", [
    ("WordingNode", ["Wording", "Element"]),
    ("LinkedDocument", ["DocumentObject", "ExternalDocument"]),
    ("ReferenceTarget", ["WordingNode", "LinkedDocument"]),
])
def test_c3_16_each_union_is_named_once_with_explicit_subclasses(name: str, members: list) -> None:
    spec = _graph(LAYER / "spec" / "wording.ttl")
    union = spec.value(WRD[name], OWL.equivalentClass)
    assert union is not None
    assert set(Collection(spec, spec.value(union, OWL.unionOf))) == {WRD[m] for m in members}
    for member in members:
        assert (WRD[member], RDFS.subClassOf, WRD[name]) in spec
    assert not [u for u in spec.objects(None, OWL.unionOf) if spec.value(predicate=OWL.unionOf, object=u) not in
                set(spec.objects(None, OWL.equivalentClass))]


def test_c3_17_every_property_states_its_subject_and_value() -> None:
    spec = _graph(LAYER / "spec" / "wording.ttl")
    props = set(spec.subjects(RDF.type, OWL.ObjectProperty)) | set(spec.subjects(RDF.type, OWL.DatatypeProperty))
    assert len(props) > 20
    for prop in props:
        comment = str(spec.value(prop, RDFS.comment) or "")
        assert "Subject:" in comment and "Value:" in comment, prop


# ---- C4-02 to C4-09: tables, assembly, variable values -------------------------

ASSEMBLY_PREFIXES = SHAPE_PREFIXES + f"@prefix elg: <{LATTICE}eligibility#> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
TRIAL = Namespace("https://example.org/lattice/wording/trial/")


def test_c4_02_c5_01_every_example_conforms() -> None:
    assert len(EXAMPLES) == 5  # C8b adds reused-clause.ttl
    for example in EXAMPLES:
        assert _violations(_example(example)) == set(), example.name


@pytest.mark.parametrize("data, focus", [
    ("ex:t a wrd:Table ; wrd:directlyComprises ex:r . ex:r a wrd:Field ; wrd:fieldKey \"x\" .", "r"),
    ("ex:w a wrd:AssembledWording ; wrd:hasValue ex:v . ex:v a wrd:VariableValue ; wrd:literalValue 1 .", "v"),
    ("ex:w a wrd:AssembledWording ; wrd:hasValue ex:v . ex:a a wrd:EmbeddedVariable . ex:b a wrd:EmbeddedVariable . "
     "ex:v a wrd:VariableValue ; wrd:forVariable ex:a , ex:b ; wrd:literalValue 1 .", "v"),
    ("ex:w a wrd:AssembledWording ; wrd:hasValue ex:v . ex:a a wrd:EmbeddedVariable . "
     "ex:v a wrd:VariableValue ; wrd:forVariable ex:a .", "v"),
    ("ex:e a wrd:Element ; wrd:inclusionMode ex:Sometimes .", "e"),
    ("ex:s a wrd:VariationSlot ; wrd:hasVariant ex:e . ex:t a wrd:VariationSlot ; wrd:hasVariant ex:e . "
     "ex:e a wrd:Element ; wrd:inclusionMode wrd-voc:Variation .", "e"),
    ("ex:w a wrd:AssembledWording ; wrd:hasValue ex:v . ex:a a wrd:EmbeddedVariable . "
     "ex:v a wrd:VariableValue ; wrd:forVariable ex:a ; wrd:forEntry ex:col ; wrd:literalValue 1 .", "v"),
    ("ex:v a wrd:VariableValue ; wrd:forVariable ex:a ; wrd:literalValue 1 . ex:a a wrd:EmbeddedVariable .", "v"),
], ids=["field-without-variable", "value-for-no-variable", "value-for-two-variables", "value-with-no-value",
        "mode-outside-the-four", "variant-of-two-slots", "entry-for-a-non-field-variable", "value-in-no-wording"])
def test_c4_04_ill_formed_tables_and_assembly_are_reported(data: str, focus: str) -> None:
    assert focus in _violations(Graph().parse(data=ASSEMBLY_PREFIXES + data, format="turtle"))


def _fields(graph: Graph, version: URIRef, table: URIRef) -> set:
    """The fields of a table that an assembled version includes, the instance's own among them."""
    return {f for f in graph.objects(version, WRD.includes) if (f, RDF.type, WRD.Field) in graph
            and ((table, WRD.directlyComprises, f) in graph or (f, WRD.placedUnder, table) in graph)}


def _cells(graph: Graph, version: URIRef) -> dict:
    cells = {}
    for record in graph.objects(version, WRD.hasValue):
        if (entry := graph.value(record, WRD.forEntry)) is not None:
            key = (graph.value(record, WRD.forVariable), entry)
            assert key not in cells, key
            cells[key] = graph.value(record, WRD.literalValue)
    return cells


@pytest.mark.parametrize("version, fields", [("protocol-trial-7", 3), ("protocol-trial-7-v2", 4)])
def test_c4_05_one_cell_per_field_and_arm_in_each_version(version: str, fields: int) -> None:
    graph = _graph(LAYER / "examples" / "trial-protocol.ttl")
    cells = _cells(graph, TRIAL[version])
    included = _fields(graph, TRIAL[version], TRIAL.soa)
    assert len(included) == fields
    for field in included:
        variable = graph.value(field, WRD.fieldVariable)
        assert {arm for (v, arm) in cells if v == variable} == {TRIAL["arm-a"], TRIAL["arm-b"]}, field


@pytest.mark.parametrize("version", ["protocol-trial-7", "protocol-trial-7-v2"])
def test_c5_16_one_cell_per_declared_field_and_entry(version: str) -> None:
    graph = _graph(LAYER / "examples" / "trial-protocol.ttl")
    cells = _cells(graph, TRIAL[version])
    entries = {e for e in graph.objects(TRIAL.responsibilities, WRD.directlyComprises) if (e, RDF.type, WRD.Entry) in graph}
    fields = _fields(graph, TRIAL[version], TRIAL.responsibilities)
    assert len(entries) == 2 and len(fields) == 2
    for field in fields:
        for entry in entries:
            assert cells.get((graph.value(field, WRD.fieldVariable), entry)) is not None, (field, entry)


def test_c4_07_closed_vocab_sets() -> None:
    vocab = _graph(LAYER / "vocab" / "wording-vocab.ttl")
    modes = set(vocab.subjects(RDF.type, WRD.InclusionMode))
    methods = set(vocab.subjects(RDF.type, WRD.PopulationMethod))
    assert {m.split("#")[-1] for m in modes} == {"Mandatory", "Variation", "Optional", "Conditional"}
    assert len(methods) == 8
    for members in (modes, methods):
        different = [set(Collection(vocab, vocab.value(n, OWL.distinctMembers))) for n in vocab.subjects(RDF.type, OWL.AllDifferent)]
        assert members in different


def test_c4_09_new_versions_have_release_rows() -> None:
    register = (ROOT / "docs" / "architecture" / "ontology-releases.md").read_text()
    for tag in ("wording-v0.2.0", "wording-vocab-v0.2.0", "wording-shapes-v0.2.0"):
        assert f"| {tag} |" in register, tag


# ---- C5: laws, slot conditions, amendments ---------------------------------------

FORM = Namespace("https://example.org/lattice/wording/facility-form/")
AMENDMENT = Namespace("https://example.org/lattice/wording/facility-amendment/")
LAW_PREFIXES = ASSEMBLY_PREFIXES + f"@prefix fnd: <{FND}> .\n@prefix voc: <{VOC}> .\n@prefix skos: <{SKOS}> .\n@prefix prov: <{PROV}> .\n"


def _reported(data: str, focus: str, message: str) -> bool:
    """Whether a violation on the focus node carries a message starting with the given text."""
    _, report, _ = validate(_vocab_closure() + Graph().parse(data=LAW_PREFIXES + data, format="turtle"),
                            shacl_graph=SHAPES, inference="none", advanced=True)
    return any(str(report.value(result, SH.focusNode)).endswith("/" + focus)
               and str(report.value(result, SH.resultMessage)).startswith(message)
               for result in report.subjects(SH.resultSeverity, SH.Violation))


@pytest.mark.parametrize("data, focus, law", [
    ("ex:w1 a wrd:Wording ; wrd:directlyComprises ex:e . ex:w2 a wrd:Wording ; wrd:directlyComprises ex:e . "
     "ex:e a wrd:Element .", "e", "W1"),                                                                         # C5-02
    ("ex:a a wrd:Element ; wrd:directlyComprises ex:b . ex:b a wrd:Element ; wrd:directlyComprises ex:a .", "a", "W1"),
    ("ex:e a wrd:Element .", "e", "W1"),
    ("ex:t a wrd:Text ; wrd:hasTextPart ex:p0 , ex:p1 , ex:p3 . "
     "ex:p0 a wrd:TextPart ; wrd:partIndex 0 ; wrd:partText \"a\" . ex:p1 a wrd:TextPart ; wrd:partIndex 1 ; wrd:partText \"b\" . "
     "ex:p3 a wrd:TextPart ; wrd:partIndex 3 ; wrd:partText \"c\" .", "t", "W2"),                                  # C5-03
    ("ex:t a wrd:Text ; wrd:hasTextPart ex:p0 , ex:p1 , ex:p2 . ex:p0 a wrd:TextPart ; wrd:partIndex 0 ; wrd:partText \"a\" . "
     "ex:p1 a wrd:TextPart ; wrd:partIndex 1 ; wrd:partText \"b\" . ex:p2 a wrd:TextPart ; wrd:partIndex 1 ; wrd:partText \"c\" .", "t", "W2"),
    ("ex:s a wrd:VariationSlot ; wrd:hasVariant ex:v . ex:v a wrd:Element ; wrd:inclusionMode wrd-voc:Optional .", "v", "W3"),  # C5-04
    ("ex:v a wrd:Element ; wrd:inclusionMode wrd-voc:Variation .", "v", "W3"),
    ("ex:w a wrd:AssembledWording ; wrd:includes ex:s . ex:s a wrd:VariationSlot ; wrd:hasVariant ex:a , ex:b . "
     "ex:a a wrd:Element ; wrd:inclusionMode wrd-voc:Variation . ex:b a wrd:Element ; wrd:inclusionMode wrd-voc:Variation .", "w", "W3"),
    ("ex:w a wrd:AssembledWording ; wrd:includes ex:s , ex:a , ex:b . ex:s a wrd:VariationSlot ; wrd:hasVariant ex:a , ex:b . "
     "ex:a a wrd:Element ; wrd:inclusionMode wrd-voc:Variation . ex:b a wrd:Element ; wrd:inclusionMode wrd-voc:Variation .", "w", "W3"),
    ("ex:e a wrd:Element ; wrd:includedWhen ex:p . ex:p a elg:AdmissionProfile .", "e", "W4"),                    # C5-05
    ("ex:e a wrd:Element ; wrd:inclusionMode wrd-voc:Conditional ; wrd:includedWhen ex:p . ex:p a elg:AdmissionProfile ; "
     "elg:hasCondition ex:c . ex:c a elg:IntervalCondition ; wrd:readsVariable ex:v . ex:v a wrd:EmbeddedVariable .", "e", "W4"),
    ("ex:w a wrd:AssembledWording ; wrd:includes ex:s . ex:s a wrd:Element ; wrd:directlyComprises ex:a , ex:b . "
     "ex:a a wrd:Element . ex:b a wrd:Element ; wrd:inclusionMode wrd-voc:Optional .", "w", "W5"),                 # C5-06
], ids=["two-trees", "cycle", "no-wording", "index-gap", "index-repeat", "variant-not-variation",
        "variation-not-variant", "slot-without-variant", "slot-with-two-variants", "condition-on-mandatory",
        "condition-reads-embedded", "mandatory-child-missing"])
def test_c5_02_to_06_laws_w1_to_w5_are_reported(data: str, focus: str, law: str) -> None:
    assert _reported(data, focus, law)


def test_c5_06_a_revision_or_a_delete_stands_for_a_mandatory_child() -> None:
    form = ("ex:w a wrd:AssembledWording ; wrd:includes ex:s , {} . ex:s a wrd:Element ; wrd:directlyComprises ex:a . "
            "ex:a a wrd:Element . ex:r a wrd:Element ; prov:wasRevisionOf ex:a . ")
    assert not _reported(form.format("ex:r"), "w", "W5")
    assert not _reported(form.format("ex:s") + "ex:d a wrd:Amendment ; wrd:operation wrd-voc:Delete ; "
                                      "wrd:amendsElement ex:a ; prov:generated ex:w .", "w", "W5")


SPACE = "ex:sp a qnt:ValueSpace ; qnt:densityKind qnt:{} . "


@pytest.mark.parametrize("data", [
    "ex:var a wrd:EmbeddedVariable ; wrd:valueContract ex:k . ex:k voc:boundScheme ex:s1 . ex:c skos:inScheme ex:s2 . "
    "ex:v a wrd:VariableValue ; wrd:forVariable ex:var ; wrd:value ex:c .",
    "ex:var a wrd:EmbeddedVariable ; wrd:valueSpace ex:sp . ex:q a qnt:Quantity ; qnt:onSpace ex:other . "
    "ex:v a wrd:VariableValue ; wrd:forVariable ex:var ; wrd:value ex:q .",
    "ex:var a wrd:EmbeddedVariable ; wrd:admissibleValues ex:set . ex:set qnt:hasRange ex:r . ex:r qnt:lowerBound ex:lb . "
    "ex:lb qnt:boundValue [ qnt:numericValue 1 ] ; qnt:boundClosure qnt:Closed . "
    "ex:v a wrd:VariableValue ; wrd:forVariable ex:var ; wrd:literalValue 0 .",
    "ex:var a wrd:EmbeddedVariable . ex:v a wrd:VariableValue ; wrd:forVariable ex:var ; wrd:literalValue 1 , 2 .",
], ids=["concept-outside-scheme", "quantity-on-another-space", "value-outside-range", "two-values-single-valued"])
def test_c5_07_values_must_match_their_variable(data: str) -> None:
    assert _reported("ex:w a wrd:AssembledWording ; wrd:hasValue ex:v . " + data, "v", "W6")


def _bound(name: str, sense: str, value, closed: bool) -> str:
    closure = "qnt:Closed" if closed else "qnt:Open"
    return f"ex:{name} qnt:boundValue [ qnt:numericValue {value} ] ; qnt:boundClosure {closure} . "


def _range(name: str, lower=None, upper=None) -> str:
    """A range with optional (value, closed) bounds."""
    text = f"ex:{name} a qnt:Range "
    for sense, bound in (("lower", lower), ("upper", upper)):
        if bound is not None:
            text += f"; qnt:{sense}Bound ex:{name}-{sense} "
    text += ". "
    for sense, bound in (("lower", lower), ("upper", upper)):
        if bound is not None:
            text += _bound(f"{name}-{sense}", sense, *bound)
    return text


def _slot(a: tuple, b: tuple, density: str = "Dense", admissible: tuple | None = None) -> str:
    text = ("ex:w a wrd:Wording ; wrd:directlyComprises ex:s , ex:g . "
            "ex:s a wrd:VariationSlot ; wrd:hasVariant ex:a , ex:b . ex:g a wrd:GoverningVariable ; wrd:valueSpace ex:sp . "
            + SPACE.format(density))
    if admissible:
        text += "ex:g wrd:admissibleValues ex:adm . ex:adm qnt:hasRange ex:adm-r . " + _range("adm-r", *admissible)
    for variant, bounds in (("a", a), ("b", b)):
        text += (f"ex:{variant} a wrd:Element ; wrd:inclusionMode wrd-voc:Variation ; wrd:includedWhen ex:{variant}-p . "
                 f"ex:{variant}-p a elg:AdmissionProfile ; elg:hasCondition ex:{variant}-c . "
                 f"ex:{variant}-c a elg:IntervalCondition ; wrd:readsVariable ex:g ; elg:requiredRangeSet ex:{variant}-set . "
                 f"ex:{variant}-set qnt:hasRange ex:{variant}-r . " + _range(f"{variant}-r", *bounds))
    return text


FROM_ZERO = ((0, True), None)


@pytest.mark.parametrize("data, reported", [
    (_slot(((0, True), (5, False)), ((5, True), None), admissible=FROM_ZERO), False),
    (_slot(((1, True), (1, True)), ((2, True), None), "Discrete", admissible=((1, True), None)), False),
    (_slot(((0, True), (10, True)), ((5, True), None), admissible=FROM_ZERO), True),
    (_slot(((0, True), (5, True)), ((5, True), None), admissible=FROM_ZERO), True),
    (_slot(((0, True), (5, False)), ((5, False), None), admissible=FROM_ZERO), True),
    (_slot(((1, True), (1, True)), ((2, True), None), admissible=((1, True), None)), True),
    (_slot(((0, True), (5, False)), ((5, True), None)), True),
], ids=["disjoint-covering", "discrete-adjacent", "overlap", "touching-closed", "gap-at-a-point",
        "dense-gap-between-integers", "gap-below-unrestricted"])
def test_c5_08_slot_ranges_are_disjoint_and_cover(data: str, reported: bool) -> None:
    assert (_reported(data, "s", "Two variants") or _reported(data, "s", "No variant")) is reported


def test_c5_08_other_slots_are_checked_for_shared_variables_and_listed_as_unchecked() -> None:
    concept = ("ex:w a wrd:Wording ; wrd:directlyComprises ex:s , ex:g . "
               "ex:s a wrd:VariationSlot ; wrd:hasVariant ex:a , ex:b . ex:g a wrd:GoverningVariable . "
               "ex:a a wrd:Element ; wrd:inclusionMode wrd-voc:Variation ; wrd:includedWhen ex:a-p . "
               "ex:a-p a elg:AdmissionProfile ; elg:hasCondition ex:a-c . ex:a-c a elg:Condition ; wrd:readsVariable ex:g . ")
    graph = Graph().parse(data=LAW_PREFIXES + concept + "ex:b a wrd:Element ; wrd:inclusionMode wrd-voc:Variation .",
                          format="turtle")
    assert _reported(concept + "ex:b a wrd:Element ; wrd:inclusionMode wrd-voc:Variation .", "s", "A slot's variants")
    assert "s" in _violations(graph, SH.Info)


AMEND = "ex:e a wrd:Element . ex:n a wrd:Element . ex:x a wrd:Text . ex:a a wrd:Amendment ; wrd:amendsElement ex:e ; wrd:expressedIn ex:x ; "


@pytest.mark.parametrize("data, message", [
    (AMEND + "wrd:operation wrd-voc:Insert ; prov:generated ex:n .", "An insert"),
    (AMEND + "wrd:operation wrd-voc:StrikeAndSubstitute ; wrd:struckText \"x\" ; prov:generated ex:n .", "A strike"),
    (AMEND + "wrd:operation wrd-voc:Delete ; wrd:replacement ex:n .", "A delete"),
    (AMEND + "wrd:operation wrd-voc:Replace ; wrd:replacement ex:n ; wrd:struckText \"x\" .", "A strike"),
    (AMEND + "wrd:operation wrd-voc:Delete .", "An amendment generates"),
    ("ex:a a wrd:Amendment ; wrd:operation wrd-voc:Replace ; wrd:replacement ex:n .", "An amendment changes"),
], ids=["insert-without-replacement", "strike-without-substitute", "delete-with-replacement",
        "replace-with-struck-text", "generates-nothing", "states-no-element"])
def test_c5_09_each_operation_has_what_it_needs(data: str, message: str) -> None:
    assert _reported(data, "a", message)


def test_c5_10_the_second_facility_replaces_and_supersedes() -> None:
    graph = _example(LAYER / "examples" / "facility-amendment.ttl")
    v2 = set(graph.objects(AMENDMENT["acme-facility-v2"], WRD.includes))
    assert {AMENDMENT["acme-cl-5-2"], AMENDMENT["acme-cl-5-1"], AMENDMENT["acme-cl-12-2"]} <= v2
    assert not {FORM["cl-5-2b"], FORM["cl-5-1"]} & v2
    assert (FORM["acme-facility-v1"], FND.supersededBy, AMENDMENT["acme-facility-v2"]) in graph
    assert len(set(graph.subjects(PROV.generated, AMENDMENT["acme-cl-5-1"]))) == 2


def test_c5_11_release_notes_mark_0_3_0_breaking() -> None:
    assert "- 0.3.0 (breaking)" in (LAYER / "README.md").read_text()


def test_c5_13_an_instance_never_versions_a_library_element() -> None:
    data = ("ex:form a wrd:Wording ; wrd:directlyComprises ex:e . ex:e a wrd:Element ; fnd:hasIdentity ex:e-id . "
            "ex:inst a wrd:AssembledWording ; wrd:directlyComprises ex:e2 . ex:e2 a wrd:Element ; fnd:hasIdentity ex:e-id . "
            "ex:x a wrd:Text . ex:a a wrd:Amendment ; wrd:operation wrd-voc:Replace ; wrd:amendsElement ex:e ; "
            "wrd:replacement ex:e2 ; wrd:expressedIn ex:x .")
    assert _reported(data, "a", "An instance's amendment")


def test_c5_14_the_draft_release_derives_from_the_bespoke_revision() -> None:
    graph = _example(LAYER / "examples" / "facility-amendment.ttl")
    assert FORM["cl-5-2c"] in set(graph.objects(FORM["slot-5-2-v2"], WRD.hasVariant))
    assert graph.value(FORM["cl-5-2c"], FND.hasGovernanceState) == FND.Draft
    assert graph.value(FORM["cl-5-2c"], PROV.wasDerivedFrom) == AMENDMENT["acme-cl-5-2"]
    assert graph.value(AMENDMENT["acme-cl-5-2"], PROV.wasRevisionOf) == FORM["cl-5-2b"]


@pytest.mark.parametrize("data, message", [
    ("ex:t1 a wrd:Table ; wrd:directlyComprises ex:f . ex:t2 a wrd:Table ; wrd:directlyComprises ex:en . "
    "ex:f a wrd:Field ; wrd:fieldVariable ex:var . ex:var a wrd:EmbeddedVariable . ex:en a wrd:Entry . "
    "ex:w a wrd:AssembledWording ; wrd:hasValue ex:v . "
    "ex:v a wrd:VariableValue ; wrd:forVariable ex:var ; wrd:forEntry ex:en ; wrd:literalValue 1 .", "A cell's"),
    ("ex:v a wrd:Table ; wrd:fieldsAs ex:Diagonally .", "A table draws"),
], ids=["entry-of-another-table", "orientation-outside-the-two"])
def test_c5_15_cells_and_orientations(data: str, message: str) -> None:
    assert _reported(data, "v", message)


def test_c5_vocab_closed_sets_and_endorsement() -> None:
    vocab = _graph(LAYER / "vocab" / "wording-vocab.ttl")
    different = [set(Collection(vocab, vocab.value(n, OWL.distinctMembers))) for n in vocab.subjects(RDF.type, OWL.AllDifferent)]
    assert {WRD_VOC[o] for o in ("Insert", "Append", "Replace", "StrikeAndSubstitute", "Delete")} in different
    assert {WRD_VOC.Rows, WRD_VOC.Columns} in different
    assert (WRD_VOC.Endorsement, SKOS.inScheme, WRD_VOC.ElementTypes) in vocab


def test_c5_new_versions_have_release_rows() -> None:
    register = (ROOT / "docs" / "architecture" / "ontology-releases.md").read_text()
    for tag in ("wording-v0.3.0", "wording-vocab-v0.3.0", "wording-shapes-v0.3.0"):
        assert f"| {tag} |" in register, tag


# ---- C8b: references by identity (the ADR-A112 addendum of 2026-10-06) -------------

REUSED = Namespace("https://example.org/lattice/wording/reused-clause/")
INSTRUMENT_EXAMPLES = ROOT / "ontology" / "instrument" / "examples"
MODEL_FILES = [ROOT / "ontology" / p for p in (
    "foundation/spec/foundation.ttl", "vocabulary/spec/vocabulary.ttl", "quantification/spec/quantification.ttl",
    "eligibility/spec/eligibility.ttl", "wording/spec/wording.ttl", "wording/vocab/wording-vocab.ttl")]
SHAPE_FILES = [ROOT / "ontology" / layer / "shapes" / f"{kind}.ttl"
               for layer in ("foundation", "vocabulary", "quantification", "eligibility", "wording")
               for kind in ("structural", "constraints")]


def _c8b_violations(data: Graph) -> list[tuple[str, str]]:
    _, report, _ = validate(_graph(*MODEL_FILES) + data, shacl_graph=_graph(*SHAPE_FILES), inference="none",
                            advanced=True)
    return [(str(report.value(r, SH.focusNode)), str(report.value(r, SH.resultMessage)))
            for r in report.subjects(SH.resultSeverity, SH.Violation)]


def _reused(add: str = "", remove: tuple = ()) -> Graph:
    g = _graph(LAYER / "examples" / "reused-clause.ttl")
    for triple in remove:
        assert triple in g, triple
        g.remove(triple)
    if add:
        prefixes = "".join(l + "\n" for l in (LAYER / "examples" / "reused-clause.ttl").read_text().splitlines()
                           if l.startswith("@prefix"))
        g.parse(data=prefixes + add, format="turtle")
    return g


def test_c8b_01_spec_version_ranges_and_display_text() -> None:
    spec = _graph(LAYER / "spec" / "wording.ttl")
    assert spec.value(URIRef(SPEC_IRI), OWL.versionIRI) == URIRef(LATTICE + "wording/0.7.0")
    for p in (WRD.refersToObject, WRD.refersToVariable, WRD.linksTo, WRD.reliesAsAmended):
        assert spec.value(p, RDFS.range) == FND.PersistentIdentity, p
    assert spec.value(WRD.reliesOnEdition, RDFS.range) == WRD.LinkedDocument
    assert (WRD.displayText, RDF.type, OWL.DatatypeProperty) in spec
    for c in (WRD.DocumentObject, WRD.ExternalDocument):
        assert (c, RDFS.subClassOf, FND.Version) in spec, c


@pytest.mark.parametrize("path", sorted((LAYER / "examples").glob("*.ttl")) + [
    INSTRUMENT_EXAMPLES / f"{n}.ttl" for n in ("facility-parameters", "framework-lots", "services-schedule")],
    ids=lambda p: p.stem)
def test_c8b_02_examples_conform(path: Path) -> None:
    data = _example(path) if path.parent == LAYER / "examples" else _graph(path)
    assert [m for _, m in _c8b_violations(data) if "W8" in m or "identity" in m or "reliance" in m.lower()] == []


def test_c8b_03_a_reference_naming_a_version_is_reported() -> None:
    g = _reused()
    part = next(p for p in g.subjects(WRD.refersToVariable, REUSED["var-days-identity"]))
    g.remove((part, WRD.refersToVariable, REUSED["var-days-identity"]))
    g.add((part, WRD.refersToVariable, REUSED["var-days-v2"]))
    assert any("never a version" in m for _, m in _c8b_violations(g))
    g = _reused()
    part = next(p for p in g.subjects(WRD.refersToObject, REUSED["def-equipment-identity"]))
    g.remove((part, WRD.refersToObject, REUSED["def-equipment-identity"]))
    g.add((part, WRD.refersToObject, REUSED["def-equipment-v1"]))
    assert any("never a version" in m for _, m in _c8b_violations(g))


def test_c8b_04_an_identity_finding_no_version_or_two_is_reported() -> None:
    none_in_form = _reused("", ((REUSED["sec-1-v1"], WRD.directlyComprises, REUSED["def-equipment-v1"]),))
    assert any(f.endswith("/form-v1") and "comprises no version" in m for f, m in _c8b_violations(none_in_form))
    two_in_form = _reused("ex:sec-6 wrd:directlyComprises ex:def-equipment-v2 .")
    assert any(f.endswith("/form-v1") and "two versions" in m for f, m in _c8b_violations(two_in_form))
    none_included = _reused("", ((REUSED["lease-0193"], WRD.includes, REUSED["def-equipment-v2"]),))
    assert any(f.endswith("/lease-0193") and "no version" in m for f, m in _c8b_violations(none_included))
    two_included = _reused("ex:lease-0193 wrd:includes ex:def-equipment-v1 .")
    assert any(f.endswith("/lease-0193") and "two versions" in m for f, m in _c8b_violations(two_included))


def test_c8b_05_one_clause_version_in_both_editions_resolving_differently() -> None:
    g = _reused()
    for form in (REUSED["form-v1"], REUSED["form-v2"]):
        assert (form, WRD.directlyComprises, REUSED["sec-5"]) in g
    assert (REUSED["sec-5"], WRD.directlyComprises, REUSED["cl-5-1"]) in g
    resolved = {}
    for form in (REUSED["form-v1"], REUSED["form-v2"]):
        rows = g.query(f"""SELECT ?v WHERE {{ <{form}> <{WRD.directlyComprises}>+ ?v .
                                              ?v <{FND.hasIdentity}> <{REUSED["var-days-identity"]}> }}""")
        resolved[form] = [r.v for r in rows]
    assert resolved == {REUSED["form-v1"]: [REUSED["var-days-v1"]], REUSED["form-v2"]: [REUSED["var-days-v2"]]}
    assert _c8b_violations(g) == []


def test_c8b_06_an_outside_document_with_no_reliance_or_two_is_reported() -> None:
    none = _reused("", ((REUSED["form-v2"], WRD.reliesAsAmended, REUSED["data-protection-identity"]),))
    assert any(f.endswith("/form-v2") and "does not rely on" in m for f, m in _c8b_violations(none))
    two = _reused("ex:form-v2 wrd:reliesOnEdition ex:safety-regs-2025 .")
    assert any(f.endswith("/form-v2") and "twice" in m for f, m in _c8b_violations(two))
    both = _reused("ex:form-v2 wrd:reliesOnEdition ex:data-protection-2024 .")
    assert any(f.endswith("/form-v2") and "twice" in m for f, m in _c8b_violations(both))


def test_c8b_06_a_static_reliance_names_an_edition_and_an_ambulatory_one_an_identity() -> None:
    assert any("names an edition" in m for _, m in _c8b_violations(
        _reused("ex:form-v2 wrd:reliesOnEdition ex:safety-regs-identity .")))
    assert any("never an edition" in m for _, m in _c8b_violations(
        _reused("ex:form-v2 wrd:reliesAsAmended ex:safety-regs-2027 .")))


def test_c8b_06_an_assembled_wording_inherits_its_form_s_reliances() -> None:
    g = _graph(LAYER / "examples" / "trial-protocol.ttl")
    assert (TRIAL["protocol-wording"], WRD.reliesAsAmended, TRIAL["gcp-regulation-identity"]) in g
    assert not [m for _, m in _c8b_violations(g) if "does not rely on" in m]


def test_c8b_01_display_text_only_on_a_reference_part() -> None:
    g = _reused()
    literal = next(p for p in g.subjects(WRD.partText, Literal("The ")))
    g.add((literal, WRD.displayText, Literal("The")))
    assert any("Only a reference part has display text" in m for _, m in _c8b_violations(g))


def test_c8b_06a_a_revised_definition_leaves_the_clause_mentioning_it_alone() -> None:
    g = _reused()
    assert (REUSED["def-equipment-v2"], PROV.wasRevisionOf, REUSED["def-equipment-v1"]) in g
    part = next(g.subjects(WRD.refersToObject, REUSED["def-equipment-identity"]))
    assert (REUSED["cl-5-1"], WRD.hasTextPart, part) in g
    for form in (REUSED["form-v1"], REUSED["form-v2"]):
        assert REUSED["cl-5-1"] in set(g.transitive_objects(form, WRD.directlyComprises)), form


def test_c8b_08_instrument_imports_wording_0_7_0_and_nothing_names_0_6_0() -> None:
    spec = _graph(ROOT / "ontology" / "instrument" / "spec" / "instrument.ttl")
    assert URIRef(LATTICE + "wording/0.7.0") in set(spec.objects(None, OWL.imports))
    found = repo_files(("ontology", "tools"), LATTICE + "wording/0.6.0", fixed=True)
    assert [f for f in found if not f.endswith("catalog-v001.xml") and "fixtures/import_guard" not in f] == []


def test_c8b_09_readme_release_notes() -> None:
    readme = (LAYER / "README.md").read_text()
    assert "- 0.7.0 (`wording` and `wording-vocab`, breaking, CCS C8b" in readme
    assert (LAYER / "shapes" / ".version").read_text().strip() == "0.4.0"
    assert "0.14.0 (breaking, CCS C8b)" in (ROOT / "ontology" / "instrument" / "README.md").read_text()
