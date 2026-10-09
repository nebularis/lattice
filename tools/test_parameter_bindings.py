# SPDX-License-Identifier: MPL-2.0

"""Instrument: values in stated meaning, and the reference instantiator (computable-contract-substrate C8,
ADR-A104 and its 2026-10-06 addendum "values in stated meaning"). Row IDs are the C8 Validation
Pack's. Reasoner rows skip when the ADR-A83 harness jar is not built. Row C8-15 (every diagram
renders) is run in a browser, and C8-16 and C8-17 by the existing tests and checks; all three are
recorded in the Validation Pack."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import BNode, Graph, Namespace, URIRef
from rdflib.compare import to_isomorphic
from rdflib.namespace import OWL, RDF, SH

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "mork_compilers" / "src"))

import instrument_instantiator  # noqa: E402
import literate_extract  # noqa: E402
from mork_compilers import reasoning  # noqa: E402

LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
INS = Namespace(LATTICE + "instrument#")
INSV = Namespace(LATTICE + "instrument/vocab#")
FND = Namespace(LATTICE + "foundation#")
WRD = Namespace(LATTICE + "wording#")
QNT = Namespace(LATTICE + "quantification#")
ONTOLOGY = ROOT / "ontology"
LAYER = ONTOLOGY / "instrument"
EXAMPLES = LAYER / "examples"
SPEC, VOCAB = LAYER / "spec" / "instrument.ttl", LAYER / "vocab" / "instrument-vocab.ttl"
NEW = ["facility-parameters", "framework-lots", "services-schedule"]
LOWER = ["foundation/spec/foundation.ttl", "vocabulary/spec/vocabulary.ttl", "quantification/spec/quantification.ttl",
         "quantification/vocab/quantification-vocab.ttl", "party/spec/party.ttl", "party/vocab/party-vocab.ttl",
         "eligibility/spec/eligibility.ttl", "eligibility/vocab/eligibility-vocab.ttl", "wording/spec/wording.ttl",
         "wording/vocab/wording-vocab.ttl", "behaviour/spec/behaviour.ttl", "behaviour/vocab/behaviour-vocab.ttl",
         "foundation/examples/keys.ttl"]
ALL_SHAPES = [ONTOLOGY / layer / "shapes" / f"{kind}.ttl"
              for layer in ("foundation", "vocabulary", "quantification", "party", "eligibility", "wording", "behaviour",
                            "instrument")
              for kind in ("structural", "constraints")]
E = "https://example.org/lattice/instrument/"
BOUND = {"facility-parameters": ("facility-parameters", "halden-v1"), "framework-lots": ("framework", "framework-v1"),
         "services-schedule": ("services-schedule", "meridian-v1"), "service-towers": ("service-towers", "meridian-v1"),
         "facility-definitions": ("facility-definitions", "fenwick-v1"), "trial-definitions": ("trial-definitions", "site-311-v1"),
         "supply-classification": ("supply-classification", "harrow-v1")}


def _graph(*sources) -> Graph:
    g = Graph()
    for source in sources:
        g.parse(source) if isinstance(source, Path) else g.parse(data=source, format="turtle")
    return g


MODEL = _graph(*[ONTOLOGY / p for p in LOWER], SPEC, VOCAB)
SHAPES = _graph(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")
EVERY_SHAPE = _graph(*ALL_SHAPES)


def _ns(name: str) -> tuple[Namespace, Namespace]:
    base = E + BOUND[name][0] + "/"
    return Namespace(base), Namespace(base + "form/")


def _instrument(name: str) -> URIRef:
    return URIRef(E + "/".join(BOUND[name]))


# Examples that are read with others, as their headers say. Every conformance test loads them together.
READ_WITH = {"facility-amendment": [ONTOLOGY / "wording" / "examples" / "facility-form.ttl",
                                    ONTOLOGY / "wording" / "examples" / "facility-amendment.ttl"],
             "facility-requests": [ONTOLOGY / "wording" / "examples" / "facility-form.ttl",
                                   ONTOLOGY / "wording" / "examples" / "facility-amendment.ttl",
                                   ONTOLOGY / "instrument" / "examples" / "facility-amendment.ttl"]}


def _example(name: str) -> Graph:
    return _graph(EXAMPLES / f"{name}.ttl")


def _prefixes(name: str) -> str:
    return "".join(line + "\n" for line in (EXAMPLES / f"{name}.ttl").read_text().splitlines()
                   if line.startswith("@prefix"))


def _split(name: str) -> tuple[Graph, Graph]:
    """The example's form and instance, and its expected generated part."""
    text = (EXAMPLES / f"{name}.ttl").read_text()
    start = text.index("# ==== Generated bound meaning")
    end = text.find("\n# ====", start + 10)
    generated = text[start:] if end < 0 else text[start:end]
    rest = text[:start] + ("" if end < 0 else text[end:])
    return _graph(rest), _graph(_prefixes(name) + generated)


def _changed(name: str, add: str = "", remove: tuple = (), graph: Graph | None = None) -> Graph:
    g = graph if graph is not None else _example(name)
    for s, p, o in remove:
        assert (s, p, o) in g, (s, p, o)
        g.remove((s, p, o))
    if add:
        g.parse(data=_prefixes(name) + add, format="turtle")
    return g


def _results(data: Graph, shapes: Graph = SHAPES, severity=SH.Violation) -> list[tuple[str, str]]:
    _, report, _ = validate(MODEL + data, shacl_graph=shapes, inference="none", advanced=True)
    return [(str(report.value(r, SH.focusNode)), str(report.value(r, SH.resultMessage)))
            for r in report.subjects(SH.resultSeverity, severity)]


def _reported(data: Graph, focus: str, fragment: str, severity=SH.Violation) -> bool:
    return any(f.endswith(focus) and fragment in m for f, m in _results(data, SHAPES, severity))


def _bnodified(g: Graph, known: set) -> Graph:
    names, out = {}, Graph()
    rename = lambda n: names.setdefault(n, BNode()) if isinstance(n, URIRef) and n not in known else n
    for s, p, o in g:
        out.add((rename(s), p, rename(o)))
    return out


needs_reasoner = pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")
FP_EX, FP = _ns("facility-parameters")
FW_EX, FW = _ns("framework-lots")
SS_EX, SS = _ns("services-schedule")


# ---- C8-01: the spec ---------------------------------------------------------

def test_c8_01_version_imports_and_new_terms() -> None:
    spec = _graph(SPEC)
    ontology = URIRef("https://www.nebularis.org/neuro-semantic/instrument")
    assert spec.value(ontology, OWL.versionIRI) == URIRef(LATTICE + "instrument/0.16.0")
    assert {str(i) for i in spec.objects(ontology, OWL.imports)} == {LATTICE + v for v in (
        "foundation/0.4.0", "vocabulary/0.4.0", "quantification/0.7.0", "party/0.8.0", "eligibility/0.10.0",
        "wording/0.7.0", "behaviour/0.14.0")}
    for name in ("valueFrom", "encodingStatus"):
        utility = str(spec.value(INS[name], FND.utility))
        assert "Subject:" in utility and "Value:" in utility, name
    vocab = _graph(VOCAB)
    assert {c for c in vocab.subjects(URIRef("http://www.w3.org/2004/02/skos/core#inScheme"), INSV.EncodingStatuses)} \
        == {INSV.NoMeaning}


# ---- C8-02, C8-03: the examples ----------------------------------------------

@pytest.mark.parametrize("name", NEW)
def test_c8_02_examples_conform_to_every_layer(name: str) -> None:
    assert _results(_example(name), EVERY_SHAPE) == []


def test_c8_02_every_instrument_example_conforms() -> None:
    for path in sorted(EXAMPLES.glob("*.ttl")):
        assert _results(_graph(path, *READ_WITH.get(path.stem, [])), EVERY_SHAPE) == [], path.name


@needs_reasoner
@pytest.mark.parametrize("name", NEW)
def test_c8_03_examples_are_consistent(name: str) -> None:
    assert reasoning.run("consistent", graphs=[MODEL, _example(name)]) is True


# ---- C8-04, C8-05: bound meaning names values, and encoding status -----------

def test_c8_04_a_bound_node_naming_a_variable_or_a_word_is_reported() -> None:
    data = _changed("facility-parameters", "ex:leverage-ceiling-halden ins:valueFrom ex:var-leverage-identity .")
    assert _reported(data, "/term-7-1", "still holds a placeholder")
    data = _changed("services-schedule", "ex:in-territory-meridian elg:requiredConcept ex:Territory .")
    assert _reported(data, "/term-3-1", "still names the word")


def test_c8_04_a_placeholder_with_two_sources_is_reported() -> None:
    data = _changed("facility-parameters", "ex:leverage-ceiling qnt:boundValue [ a qnt:Quantity ; "
                                            "ins:valueFrom ex:var-leverage-identity , ex:var-repay-days-identity ] .")
    assert any("one source" in m for _, m in _results(data))


def test_c8_05_text_marked_no_meaning_with_stated_meaning_is_reported() -> None:
    data = _changed("facility-parameters", "ex:cl-6-1 ins:encodingStatus ins-voc:NoMeaning .")
    assert _reported(data, "/cl-6-1", "expresses no stated meaning")


# ---- C8-06, C8-07: law I17 --------------------------------------------------

def test_c8_06_a_bound_term_from_text_not_included_is_reported() -> None:
    data = _changed("facility-parameters", "", ((FP_EX["halden-wording-v1"], WRD.includes, FP_EX["cl-7-2"]),))
    assert _reported(data, "/term-7-2", "does not include")


def test_c8_06_an_included_stated_term_left_unbound_is_reported() -> None:
    data = _changed("facility-parameters", "", ((FP_EX["term-7-2"], INS.boundIn, FP_EX["halden-v1"]),))
    assert _reported(data, "/halden-v1", "is not bound")


def test_c8_07_coverage_warns_for_an_unassessed_leaf_only() -> None:
    warnings = _results(_example("services-schedule"), SHAPES, SH.Warning)
    assert [m.split(" is a leaf")[0].rsplit("/", 1)[-1] for _, m in warnings if "not yet assessed" in m] == ["cl-6-1"]
    marked = _changed("services-schedule", "ex:cl-6-1 ins:encodingStatus ins-voc:NoMeaning .")
    assert not [m for _, m in _results(marked, SHAPES, SH.Warning) if "not yet assessed" in m]


# ---- C8-08, C8-09: C7c's open checks, on the form ---------------------------

def test_c8_08_overlapping_definitions_on_the_form_are_a_warning() -> None:
    assert _reported(_example("framework-lots"), "form/def-s1-1", "On the form", SH.Warning)
    data = _changed("framework-lots", "tmpl:def-s1-2 ins:prevailsOver tmpl:def-s1-1 .")
    assert not _reported(data, "form/def-s1-1", "On the form", SH.Warning)


def test_c8_09_a_word_with_no_definition_in_a_section_is_reported() -> None:
    data = _changed("framework-lots", "tmpl:term-s1-4 ins:appliesWithin ex:lot-3-identity .",
                    ((FW["term-s1-4"], INS.appliesWithin, FW_EX["lot-4-identity"]),))
    assert _reported(data, "form/term-l4-1", "no definition of it applies")


# ---- C8-10 to C8-13: the instantiator ----------------------------------------------

@pytest.mark.parametrize("name", sorted(BOUND))
def test_c8_10_the_instantiator_regenerates_the_expected_part(name: str) -> None:
    given, expected = _split(name)
    generated, _ = instrument_instantiator.instantiate(given, _instrument(name))
    known = set(given.all_nodes())
    assert to_isomorphic(_bnodified(generated, known)) == to_isomorphic(_bnodified(expected, known))


@pytest.mark.parametrize("name", NEW)
def test_c8_10_the_instantiator_s_output_conforms(name: str) -> None:
    given, _ = _split(name)
    generated, _ = instrument_instantiator.instantiate(given, _instrument(name))
    assert _results(given + generated, EVERY_SHAPE) == []


def test_c8_11_a_variable_with_no_value_is_reported() -> None:
    given, _ = _split("facility-parameters")
    given.remove((FP_EX["halden-wording-v1"], WRD.hasValue, FP_EX["v-repay-days"]))
    _, reports = instrument_instantiator.instantiate(given, _instrument("facility-parameters"))
    assert [r.message for r in reports if r.kind == "no-value"] == ["no value for the variable var-repay-days-identity"]


def test_c8_12_schedule_values_reach_each_lot_and_lots_1_and_2_share_3_1() -> None:
    given, _ = _split("framework-lots")
    generated, _ = instrument_instantiator.instantiate(given, _instrument("framework-lots"))
    bound = list(generated.subjects(INS.boundFrom, FW["term-3-1"]))
    assert len(bound) == 2
    by_cover = {frozenset(generated.objects(t, INS.boundWithin)): t for t in bound}
    lots_1_2 = frozenset({FW_EX["lot-1-identity"], FW_EX["lot-2-identity"]})
    assert set(by_cover) == {lots_1_2, frozenset({FW_EX["lot-3-identity"]})}
    duty = generated.value(None, INS.arisesUnder, by_cover[lots_1_2])
    assert generated.value(duty, INS.obligor) == FW_EX["ash-occ"]
    award = generated.value(None, INS.boundFrom, FW["award-lot-3"])
    assert generated.value(award, INS.counterparty) == FW_EX["lot-3-suppliers"]


def test_c8_13_the_instantiator_names_generated_nodes_deterministically() -> None:
    given, _ = _split("facility-parameters")
    first, _ = instrument_instantiator.instantiate(given, _instrument("facility-parameters"))
    second, _ = instrument_instantiator.instantiate(given, _instrument("facility-parameters"))
    iris = lambda g: {n for n in g.all_nodes() if isinstance(n, URIRef)}
    assert iris(first) == iris(second)
    assert to_isomorphic(first) == to_isomorphic(second)


# ---- C8-14: literate source and release notes --------------------------------

def test_c8_14_readme_is_the_source_and_releases_are_recorded() -> None:
    assert literate_extract.main([str(LAYER / "README.md"), "--layer", "instrument", "--root", str(ROOT), "--shapes",
                                  "shapes/structural.ttl", "shapes/constraints.ttl", "shapes/single-expression.ttl",
                                  "--check"]) == 0
    readme = (LAYER / "README.md").read_text()
    assert "0.13.0 (additive, CCS C8" in readme and "Shapes 0.6.0 (breaking" in readme
    assert (LAYER / "shapes" / ".version").read_text().strip() == "0.8.0"
    register = (ROOT / "docs" / "architecture" / "ontology-releases.md").read_text()
    for tag in ("instrument-v0.13.0", "instrument-shapes-v0.6.0", "instrument-vocab-v0.13.0"):
        assert tag in register, tag


# ---- C8-18, C8-19: cycles -----------------------------------------------------

def _cycle_reports(given: Graph, name: str) -> list:
    _, reports = instrument_instantiator.instantiate(given, _instrument(name))
    return [r for r in reports if r.kind == "cycle"]


def test_c8_18_a_word_taking_its_value_from_itself_is_a_cycle() -> None:
    given, _ = _split("facility-parameters")
    placeholder = given.value(FP["def-commitment"], INS.means)
    given.remove((placeholder, INS.valueFrom, FP_EX["var-commitment-identity"]))
    given.add((placeholder, INS.valueFrom, FP_EX.Commitment))
    assert _reported(given, "form/def-commitment", "Cycle: ")
    cycles = _cycle_reports(given, "facility-parameters")
    assert cycles and cycles[0].hops == ["Commitment (defined in cl-1-1)", "Commitment"]


def test_c8_18_a_cycle_through_two_words_names_every_hop() -> None:
    given, _ = _split("facility-parameters")
    placeholder = given.value(FP["def-commitment"], INS.means)
    given.remove((placeholder, INS.valueFrom, FP_EX["var-commitment-identity"]))
    given.add((placeholder, INS.valueFrom, FP_EX.FacilityLimit))
    given.parse(data=_prefixes("facility-parameters") + """
        ex:FacilityLimit a skos:Concept ; rdfs:label "Facility Limit" .
        tmpl:term-1-2 a ins:Term , ins:Template ; ins:expressedIn ex:cl-1-1 .
        tmpl:def-facility-limit a ins:Definition , ins:Template ;
            ins:arisesUnder tmpl:term-1-2 ; ins:defines ex:FacilityLimit ;
            ins:means [ a qnt:Quantity ; qnt:onSpace ex:money ; ins:valueFrom ex:Commitment ] .
        """, format="turtle")
    messages = [m for _, m in _results(given) if m.startswith("Cycle: ")]
    assert any("Commitment" in m and "FacilityLimit" in m for m in messages) and len(messages) >= 2
    cycles = _cycle_reports(given, "facility-parameters")
    assert cycles
    hops = cycles[0].hops
    assert len(hops) == 3 and hops[0].split(" ")[0] == hops[-1] and "defined in" in hops[1]


def test_c8_18_a_cycle_through_variables_is_reported() -> None:
    given, _ = _split("facility-parameters")
    given.remove((FP_EX["halden-wording-v1"], WRD.hasValue, FP_EX["v-commitment"]))
    given.parse(data=_prefixes("facility-parameters") + """
        ex:var-limit a wrd:EmbeddedVariable ; fnd:hasIdentity ex:var-limit-identity ; wrd:populatedFrom ex:var-commitment .
        ex:var-commitment wrd:populatedFrom ex:var-limit .
        """, format="turtle")
    assert _reported(given, "/var-commitment", "Cycle: the variable")
    cycles = _cycle_reports(given, "facility-parameters")
    assert cycles and cycles[0].message.startswith("variable cycle: var-commitment-identity → var-limit-identity")


def test_c8_19_a_cycle_closing_in_one_section_spares_the_others() -> None:
    given, _ = _split("framework-lots")
    placeholder = given.value(FW["def-s1-2"], INS.means)
    given.remove((placeholder, INS.valueFrom, FW_EX["var-s1-2-supplier-identity"]))
    given.add((placeholder, INS.valueFrom, FW_EX.Supplier))
    generated, reports = instrument_instantiator.instantiate(given, _instrument("framework-lots"))
    cycles = [r for r in reports if r.kind == "cycle"]
    assert cycles and all(r.section == FW_EX["lot-2-identity"] for r in cycles)
    award = generated.value(None, INS.boundFrom, FW["award-lot-1"])
    assert generated.value(award, INS.counterparty) == FW_EX["ash-occ"]


# ---- C8-20: concept words in Eligibility's concept slots ----------------------

def test_c8_20_a_word_also_in_its_condition_s_scheme_is_reported() -> None:
    data = _changed("services-schedule", "ex:Territory skos:inScheme ex:territories .")
    assert _reported(data, "/in-territory", "the condition is ambiguous")


def test_c8_20_a_word_meaning_a_condition_in_a_concept_slot_is_reported() -> None:
    data = _changed("services-schedule", """
        ex:Fault a skos:Concept .
        tmpl:def-fault a ins:Definition , ins:Template ; ins:arisesUnder tmpl:term-s-1 ;
            ins:defines ex:Fault ; ins:means ex:fault-reported .
        ex:in-territory elg:excludedConcept ex:Fault .""")
    assert _reported(data, "form/def-fault", "which is not a concept")


# ---- C8-21: the cycle rule, wherever it may come up --------------------------

@pytest.mark.parametrize("path", [
    "ontology/instrument/README.md", "ontology/wording/README.md", "ontology/quantification/README.md",
    "ontology/eligibility/README.md", "tools/README.md",
    "docs/architecture/decisions/ADR-A104-instrument-terms-and-legal-relations.md"])
def test_c8_21_the_cycle_rule_is_documented(path: str) -> None:
    text = (ROOT / path).read_text()
    assert "loop" in text and ("§18.4" in text or "cycle" in text.lower()), path
