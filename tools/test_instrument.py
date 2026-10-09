# SPDX-License-Identifier: MPL-2.0

"""Instrument: terms and legal relations (computable-contract-substrate C6,
ADR-A104). Row IDs are the C6 Validation Pack's. Reasoner rows skip when the
ADR-A83 harness jar is not built."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "mork_compilers" / "src"))
from test_parameter_bindings import READ_WITH  # noqa: E402

import literate_extract  # noqa: E402
from conftest import repo_files  # noqa: E402
from mork_compilers import reasoning  # noqa: E402

LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
INS = Namespace(LATTICE + "instrument#")
INSV = Namespace(LATTICE + "instrument/vocab#")
VOC = Namespace(LATTICE + "vocabulary#")
BHV = Namespace(LATTICE + "behaviour#")
LAYER = ROOT / "ontology" / "instrument"
SPEC, VOCAB = LAYER / "spec" / "instrument.ttl", LAYER / "vocab" / "instrument-vocab.ttl"
EXAMPLES = sorted((LAYER / "examples").glob("*.ttl"))
LOWER = ["foundation/spec/foundation.ttl", "vocabulary/spec/vocabulary.ttl", "quantification/spec/quantification.ttl",
         "party/spec/party.ttl", "party/vocab/party-vocab.ttl", "eligibility/spec/eligibility.ttl",
         "eligibility/vocab/eligibility-vocab.ttl", "wording/spec/wording.ttl", "wording/vocab/wording-vocab.ttl",
         "behaviour/spec/behaviour.ttl", "foundation/examples/keys.ttl"]
RETIRED = ("Element", "Provision", "hasProvision", "partOfInstrument", "hasObligation", "inProvision",
           "hasQualifier", "hasCondition", "fulfilledBy")


def _graph(*sources) -> Graph:
    g = Graph()
    for source in sources:
        if isinstance(source, Path):
            g.parse(source)
        else:
            g.parse(data=source, format="turtle")
    return g


@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    """TM1/TM2: shared, session-scoped graphs and validation cache
    (python-test-melting)."""
    module = request.module
    module.MODEL = graph_cache(*[ROOT / "ontology" / p for p in LOWER], SPEC, VOCAB)
    module.SHAPES = graph_cache(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")
    module.FACILITY = graph_cache(LAYER / "examples" / "facility-agreement.ttl")
    module.validate = validated


PREFIXES = (f"@prefix ins: <{INS}> .\n@prefix fnd: <{LATTICE}foundation#> .\n@prefix pty: <{LATTICE}party#> .\n"
            f"@prefix elg: <{LATTICE}eligibility#> .\n@prefix ex: <https://example.org/lattice/instrument/facility/> .\n"
            "@prefix tmpl: <https://example.org/lattice/instrument/facility/form/> .\n")


def _messages(data: Graph) -> list[tuple[str, str]]:
    _, report, _ = validate(MODEL + data, shacl_graph=SHAPES, inference="none", advanced=True)
    return [(str(report.value(r, SH.focusNode)), str(report.value(r, SH.resultMessage)))
            for r in report.subjects(SH.resultSeverity, SH.Violation)]


def _reported(data: Graph, focus: str, fragment: str) -> bool:
    return any(f.endswith(focus) and fragment in m for f, m in _messages(data))


def _facility(add: str = "", remove: tuple = ()) -> Graph:
    g = Graph()
    g += FACILITY
    for triple in remove:
        g.remove(triple)
    if add:
        g.parse(data=PREFIXES + add, format="turtle")
    return g


EX = Namespace("https://example.org/lattice/instrument/facility/")
TMPL = Namespace("https://example.org/lattice/instrument/facility/form/")


# ---- C6-01: the spec --------------------------------------------------------

def test_c6_01_version_and_imports() -> None:
    spec = _graph(SPEC)
    ontology = URIRef("https://www.nebularis.org/neuro-semantic/instrument")
    assert spec.value(ontology, OWL.versionIRI) == URIRef(LATTICE + "instrument/0.16.0")
    assert set(spec.objects(ontology, OWL.imports)) == {URIRef(LATTICE + v) for v in (
        "foundation/0.4.0", "vocabulary/0.4.0", "quantification/0.8.0", "party/0.9.0", "eligibility/0.11.0",
        "wording/0.8.0", "behaviour/0.14.0")}
    assert "behaviour-runtime" not in SPEC.read_text()


def test_c6_01_import_guard_passes() -> None:
    assert subprocess.run([sys.executable, str(ROOT / "tools" / "import_guard.py")], cwd=ROOT).returncode == 0


# ---- C6-02, C6-03: the examples ---------------------------------------------

@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_c6_02_examples_conform(example: Path) -> None:
    assert _messages(_graph(example, *READ_WITH.get(example.stem, []))) == []


needs_reasoner = pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")


@needs_reasoner
@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_c6_03_examples_are_consistent(example: Path) -> None:
    assert reasoning.run("consistent", graphs=[MODEL, _graph(example)]) is True


# ---- C6-04: content and cardinality -----------------------------------------

@pytest.mark.parametrize("add, remove, focus, message", [
    ("ex:repay ins:arisesUnder ex:term-7-1 .", (), "/repay", "exactly one term"),
    ("", ((EX.repay, INS.arisesUnder, EX["term-6-1"]),), "/repay", "exactly one term"),
    ("ex:repay ins:obligor ex:lender-1-occ .", (), "/repay", "exactly one obligor"),
    ("", ((EX.leverage, INS.maintains, EX["leverage-ok"]),), "/leverage", "ins:maintains"),
    ("", ((EX["permitted-liens"], INS.excepts, EX["negative-pledge"]),), "/permitted-liens", "excepts exactly one prohibition"),
    ("ex:x a ins:Exclusion ; ins:arisesUnder ex:term-8-1 ; ins:boundFrom tmpl:permitted-liens ; ins:holder ex:borrower-occ ; ins:counterparty ex:lenders .",
     (), "/x", "excepts exactly one obligation or power"),
    ("", ((EX["permitted-liens"], INS.excepts, EX["negative-pledge"]),), "/permitted-liens", "prohibition"),
    ("ex:permitted-liens ins:scope ex:repay .", ((EX["permitted-liens"], INS.scope, EX["lien-by-law"]),),
     "/permitted-liens", "an Eligibility condition"),
])
def test_c6_04_content_shapes_report(add: str, remove: tuple, focus: str, message: str) -> None:
    assert _reported(_facility(add, remove), focus, message)


def test_c6_04_permission_excepting_a_non_prohibition() -> None:
    data = _facility("ex:permitted-liens ins:excepts ex:repay .",
                     ((EX["permitted-liens"], INS.excepts, EX["negative-pledge"]),))
    assert _reported(data, "/permitted-liens", "excepts exactly one prohibition")


# ---- C6-05: disjointness ----------------------------------------------------

@needs_reasoner
@pytest.mark.parametrize("types", [("Obligation", "Power"), ("ContinuingObligation", "Prohibition")])
def test_c6_05_disjoint_relations_are_inconsistent(types: tuple[str, str]) -> None:
    data = _graph(PREFIXES + f"ex:both a ins:{types[0]} , ins:{types[1]} .")
    assert reasoning.run("consistent", graphs=[MODEL, data]) is False


# ---- C6-06: law I8 ----------------------------------------------------------

def test_c6_06_permission_holder_and_activity() -> None:
    other_holder = _facility("ex:permitted-liens ins:holder ex:lender-1-occ .",
                             ((EX["permitted-liens"], INS.holder, EX["borrower-occ"]),))
    assert _reported(other_holder, "/permitted-liens", "is not the obligor of the prohibition")
    ins_voc = URIRef(LATTICE + "instrument/vocab#Repay")
    other_activity = _facility(f"ex:permitted-liens ins:activity <{ins_voc}> .",
                               ((EX["permitted-liens"], INS.activity, INSV.CreateSecurity),))
    assert _reported(other_activity, "/permitted-liens", "is not the activity of the prohibition")


def test_c6_06_exclusion_of_a_power_by_its_holder() -> None:
    data = _facility("ex:immunity a ins:Exclusion ; ins:arisesUnder ex:term-10-1 ; ins:boundFrom tmpl:accelerate ; "
                     "ins:holder ex:lenders ; ins:counterparty ex:borrower-occ ; ins:excepts ex:accelerate .")
    assert _reported(data, "/immunity", "is not a counterparty of the power")


def test_c6_06_exclusion_of_an_obligation_by_another_party() -> None:
    data = _facility("ex:waiver a ins:Exclusion ; ins:arisesUnder ex:term-6-1 ; ins:boundFrom tmpl:repay ; "
                     "ins:holder ex:lenders ; ins:counterparty ex:borrower-occ ; ins:excepts ex:repay .")
    assert _reported(data, "/waiver", "is not the obligor of the obligation")


# ---- C6-07: the two tiers (law I2, I13) -------------------------------------

@pytest.mark.parametrize("add, remove, focus, message", [
    ("tmpl:term-6-1 ins:expressedIn ex:cl-7-1 .", (), "/term-6-1", "law I2"),
    ("ex:facility-v2 a ins:Instrument . ex:term-6-1 ins:boundIn ex:facility-v2 .", (), "/term-6-1", "law I2"),
    ("ex:term-6-1 ins:boundFrom tmpl:term-7-1 .", (), "/term-6-1", "law I2"),
    ("", ((EX["term-6-1"], INS.boundFrom, TMPL["term-6-1"]),), "/term-6-1", "law I2"),
    ("ex:repay a fnd:Version .", (), "/repay", "never a version"),
    ("ex:repay ins:boundIn ex:facility-v1 .", (), "/repay", "carries no ins:boundIn"),
    ("ex:repay ins:obligor ex:Borrower .", ((EX.repay, INS.obligor, EX["borrower-occ"]),), "/repay", "laws I2, I13"),
    ("tmpl:repay ins:obligor ex:borrower-occ .", ((TMPL.repay, INS.obligor, EX.Borrower),), "/repay", "laws I2, I13"),
    ("", ((EX.repay, INS.boundFrom, TMPL.repay),), "/repay", "laws I2, I13"),
])
def test_c6_07_tier_shapes_report(add: str, remove: tuple, focus: str, message: str) -> None:
    assert _reported(_facility(add, remove), focus, message)


def test_c6_07_implied_term_conforms() -> None:
    data = _facility("ex:implied a ins:Term ; ins:boundIn ex:facility-v1 ; ins:impliedBy ex:sale-of-goods-act .")
    assert not [m for f, m in _messages(data) if f.endswith("/implied")]


# ---- C6-08, C6-09: unions and comments --------------------------------------

def test_c6_08_unions_named_once_with_explicit_members() -> None:
    spec = _graph(SPEC)
    for union, members in ((INS.LegalRelation, (INS.Obligation, INS.Permission, INS.Exclusion, INS.Power)),
                           (INS.RelationParty, tuple(URIRef(LATTICE + "party#" + c) for c in ("RoleOccupancy", "ParticipationGroup", "Role")))):
        assert len(list(spec.objects(union, OWL.equivalentClass))) == 1
        for member in members:
            assert (member, RDFS.subClassOf, union) in spec
    assert len(list(spec.subjects(OWL.unionOf, None))) == 2


def test_c6_09_every_property_states_subject_and_value() -> None:
    spec = _graph(SPEC)
    text = SPEC.read_text()
    for prop in set(spec.subjects(RDF.type, OWL.ObjectProperty)) | set(spec.subjects(RDF.type, OWL.DatatypeProperty)):
        utility = str(spec.value(prop, URIRef(LATTICE + "foundation#utility")))
        assert "Subject:" in utility and "Value:" in utility, prop
    for layer in ("behaviour-runtime", "/applied/", "insurance"):
        assert layer not in text, layer


# ---- C6-10: retired terms ---------------------------------------------------

def test_c6_10_no_retired_term_outside_history() -> None:
    # [^A-Za-z0-9_] behaves the same as \b on every platform (POSIX ERE has no \b).
    pattern = "ins:(" + "|".join(RETIRED) + ")([^A-Za-z0-9_]|$)"
    found = repo_files(("ontology", "tools", "test", "docs/architecture/ontology-architecture.md"), pattern)
    # Release notes, this list, and test_repo_files.py's own fixture data for repo_files() itself.
    allowed = {"ontology/instrument/README.md", "tools/test_instrument.py", "tools/test_repo_files.py"}
    assert [f for f in found if f not in allowed and "/decisions/" not in f] == []


# ---- C6-11: the vocab -------------------------------------------------------

def test_c6_11_vocab() -> None:
    vocab = _graph(VOCAB)
    assert (INSV.ActivityContract, VOC.constrainsProperty, INS.activity) in vocab
    assert (INSV.LocationContract, VOC.constrainsProperty, INS.operatesAt) in vocab
    baseline = set(vocab.subjects(URIRef("http://www.w3.org/2004/02/skos/core#inScheme"), INSV.Activities))
    used = set()
    for example in EXAMPLES:
        used |= set(_graph(example).objects(None, INS.activity))
    assert used <= baseline, used - baseline
    assert (INS.InstrumentTarget, RDF.type, BHV.TargetKind) in vocab


# ---- C6-12: supersession ----------------------------------------------------

def test_c6_12_supersession_across_identities() -> None:
    data = _graph(ROOT / "test" / "gate4" / "instrument-supersession-identity-mismatch.ttl")
    assert _reported(data, "/old-version", "same instrument")
    query = (ROOT / "test" / "gate4" / "queries" / "instrument-supersession-identity-mismatch.rq").read_text()
    assert len(list(data.query(query))) == 1


# ---- C6-13: one term in two languages ---------------------------------------

def test_c6_13_second_expression_conforms_except_to_the_optional_shape() -> None:
    data = _facility("ex:cl-6-1-fr a <https://www.nebularis.org/neuro-semantic/lattice/wording#Element> . "
                     "tmpl:term-6-1 ins:alsoExpressedIn ex:cl-6-1-fr .")
    assert not [m for f, m in _messages(data) if f.endswith("/term-6-1")]
    optional = _graph(LAYER / "shapes" / "single-expression.ttl")
    assert validate(MODEL + data, shacl_graph=optional, inference="none")[0] is False


# ---- C6-14: literate source and release notes -------------------------------

def test_c6_14_readme_is_the_source_and_releases_are_recorded() -> None:
    assert literate_extract.main([str(LAYER / "README.md"), "--layer", "instrument", "--root", str(ROOT), "--shapes",
                                  "shapes/structural.ttl", "shapes/constraints.ttl", "shapes/single-expression.ttl",
                                  "--check"]) == 0
    readme = (LAYER / "README.md").read_text()
    assert "0.9.0 (breaking, CCS C6" in readme and "Shapes 0.2.0\n  (breaking)" in readme
    assert (LAYER / "shapes" / ".version").read_text().strip() == "0.8.0"
    assert not (LAYER / "projection").exists()
