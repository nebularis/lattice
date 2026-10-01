# SPDX-License-Identifier: MPL-2.0

"""The Wording layer's spec, vocab and examples (computable-contract-substrate
C3, ADR-A112). Row IDs are the C3 Validation Pack's. Reasoner rows skip when
the ADR-A83 harness jar is not built (``mise run bootstrap:reasoning-testkit``).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SH, SKOS

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "mork_compilers" / "src"))

import literate_extract  # noqa: E402
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


def _graph(*paths: Path) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path)
    return g


def _vocab_closure() -> Graph:
    return closure(Catalog(CATALOG), VOCAB_IRI)


# ---- C3-01, C3-02, C3-03: imports, resolution, no higher layer ------------------

def test_c3_01_imports_exactly_the_layers_below() -> None:
    spec = _graph(LAYER / "spec" / "wording.ttl")
    ontology = URIRef(SPEC_IRI)
    assert spec.value(ontology, OWL.versionIRI) == URIRef(LATTICE + "wording/0.1.0")
    assert set(spec.objects(ontology, OWL.imports)) == {
        URIRef(LATTICE + "foundation/0.3.0"),
        URIRef(LATTICE + "vocabulary/0.3.0"),
        URIRef(LATTICE + "quantification/0.5.0"),
        URIRef(LATTICE + "eligibility/0.7.0"),
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
    assert graph.value(parts[1], WRD.refersToObject) == FACILITY["def-borrower"]
    assert graph.value(parts[3], WRD.refersToVariable) == FACILITY["var-margin"]


# ---- C3-05 to C3-07: the reasoner ---------------------------------------------

def _consistent(*extra: Graph) -> bool:
    graphs = [_vocab_closure(), *extra]
    return reasoning.run("consistent", graphs=graphs) is True


@pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")
@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_c3_05_examples_are_consistent(example: Path) -> None:
    assert _consistent(_graph(example))


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
                                  "--shapes", "shapes/structural.ttl", "--check"]) == 0


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

SHAPES = _graph(LAYER / "shapes" / "structural.ttl")


def _violations(data: Graph) -> set:
    """Focus-node local names of every violation, with the spec closure in the data graph."""
    _, report, _ = validate(_vocab_closure() + data, shacl_graph=SHAPES, inference="none", advanced=True)
    return {str(node).rsplit("/", 1)[-1] for node in report.objects(None, SH.focusNode)}


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_c3_14_examples_conform_to_the_shapes(example: Path) -> None:
    assert _violations(_graph(example)) == set()


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
