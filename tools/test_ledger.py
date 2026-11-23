# SPDX-License-Identifier: MPL-2.0

"""Ledger LG-1, LG-2, LG-12, LG-25, LG-26, LG-27, LG-28 and LG-29: the configuration document and the runtime document (ADR-A131). Row IDs are the plan's LG-1
and LG-2 "in detail" tables and the Validation Packs of LG-12 and LG-25 to LG-29. Validates LG-0's examples, configuration and runtime records, against
the structural shapes, the SHACL-SPARQL constraints and the runtime laws, and against Foundation's two shapes for a versioned thing
(ADR-A142), checks the import guard holds, the spec names no term
of Party, Eligibility, Wording, Instrument or Behaviour, the cycle shape finishes on a generated tree, each runtime law refuses a
record that breaks it, and the runtime shapes finish on a generated pass, both small here and at the plan's sizes in
benchmark/ledger-posting-cost/test_shape_scale.py (STD-155). LG2-01 is the owl:rational probe on rdflib, Oxigraph and Jena
(TSD-70)."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from decimal import Decimal
from functools import cache
from pathlib import Path

import pyoxigraph as ox
import pytest
from ledger_corpus import account_tree, one_pass
from pyshacl import validate
from rdflib import RDF, XSD, BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, PROV, RDFS, SH, SKOS

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology"
LEDGER = ONTOLOGY / "ledger"
LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
LDG = Namespace(LATTICE + "ledger#")
QNT = Namespace(LATTICE + "quantification#")
FND = Namespace(LATTICE + "foundation#")

sys.path.insert(0, str(ROOT / "tools"))
import literate_extract  # noqa: E402
from conftest import repo_files  # noqa: E402


def _graph(*sources) -> Graph:
    g = Graph()
    for source in sources:
        g.parse(source) if isinstance(source, Path) else g.parse(data=source, format="turtle")
    return g


@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    module = request.module
    module.MODEL = graph_cache(
        ONTOLOGY / "foundation" / "spec" / "foundation.ttl",
        ONTOLOGY / "vocabulary" / "spec" / "vocabulary.ttl",
        ONTOLOGY / "quantification" / "spec" / "quantification.ttl",
        LEDGER / "spec" / "ledger.ttl",
        LEDGER / "spec" / "ledger-runtime.ttl",
        LEDGER / "vocab" / "ledger-vocab.ttl",
    )
    module.SHAPES = graph_cache(LEDGER / "shapes" / "structural.ttl", LEDGER / "shapes" / "constraints.ttl",
                                LEDGER / "shapes" / "runtime.ttl")
    constraints = _graph(LEDGER / "shapes" / "constraints.ttl")
    module.CYCLE_SHAPE = graph_cache(_only(constraints, LDG.NoCycleThroughPartOfShape))
    module.RUNTIME_SHAPES = graph_cache(LEDGER / "shapes" / "runtime.ttl")
    foundation = _graph(ONTOLOGY / "foundation" / "shapes" / "constraints.ttl", ONTOLOGY / "foundation" / "shapes" / "structural.ttl")
    module.FOUNDATION_SHAPES = graph_cache(_only(foundation, FND.VersionedShape, FND.MeaningBearingEdgeShape))
    # what the scale test leaves to pySHACL: the shapes of LG-1, and the runtime shapes too slow on Oxigraph
    module.SCALE_SHAPES = graph_cache(LEDGER / "shapes" / "structural.ttl", LEDGER / "shapes" / "constraints.ttl",
                                      _only(_runtime_shapes(), *(URIRef(s) for s in sorted(SLOW_ON_OXIGRAPH))))
    module.validate = validated


ACCEPTED = ["licence-seats", "revolving-facility", "research-grant", "authority-aggregate", "insurance-aggregate",
            "credit-cut-at-parent", "whole-or-nothing", "supersession-raised-amount"]
REFUSALS = {
    "refusal-cycle": "NoCycleThroughPartOfShape",
    "refusal-unit": "ChildUnitMatchesParentShape",
    "refusal-proportional-unrounded": "ProportionalNeedsRoundingShape",
    "refusal-intensive-unit": "ExtensiveUnitOfAccountShape",
    "refusal-nearest-beside-residual": "NearestRoundingStatesTheDifferenceShape",
    "refusal-settled-without-excess": "SettledToNearestStatesTheExcessShape",
    "refusal-ceiling-above-stated": "CreditCeilingAboveStatedAdmittedShape",
    "refusal-discrete-without-floor": "DiscreteUnitStatesAFloorShape",
    "refusal-version-changes-parent": "VersionsKeepTheAccountsPlaceShape",
}


def _example(name: str) -> Graph:
    return _graph(LEDGER / "examples" / f"{name}.ttl")


def _violating_shapes(report: Graph) -> set[str]:
    return {str(report.value(r, SH.sourceShape)) for r in report.subjects(SH.resultSeverity, SH.Violation)}


# ---- the runtime shapes as plain SELECTs on Oxigraph (CAP-64) ------------------
#
# Each runtime shape targets its class (`sh:targetNode ldg:Posting`) and reads every instance in one query, so pySHACL
# runs it once, with `$this` the class. The SHACL-SPARQL specification defines that run as the query with `$this` replaced by
# the class, so it also runs as a plain SELECT on any engine once `$this` is out of the projection and the grouping, the only
# places it is not a term. A row is a violation and its `?value` the record. Oxigraph and pySHACL on rdflib are different
# engines (STD-176, STD-274), so every case below that runs through pySHACL also holds Oxigraph to what it finds (`_agree`), and
# `test_oxigraph_finds_what_pyshacl_finds_at_scale` does so on a generated pass.
#
# Every sum adds a value for each row it reads, zero for a row that is not a counted posting, so no term of a sum is an error
# under SPARQL 1.1 §18.5.1 and Oxigraph reads what rdflib reads (TD-158, `test_the_sums_find_on_oxigraph_what_pyshacl_finds`).
#
# SLOW_ON_OXIGRAPH holds a shape whose cost on Oxigraph is far above its cost through pySHACL on rdflib at the benchmark's size,
# which stays with pySHACL in the scale test (STD-176). A cost measured on one engine is a hypothesis for the other.
SLOW_ON_OXIGRAPH: frozenset[str] = frozenset()


@cache
def _runtime_shapes() -> Graph:
    return _graph(LEDGER / "shapes" / "runtime.ttl")


@cache
def _runtime_selects() -> tuple[tuple[str, str], ...]:
    """(shape, query) of every runtime shape and target class, in the order of the file."""
    shapes = _runtime_shapes()
    found = []
    for shape in sorted(shapes.subjects(SH.targetNode, None)):
        for target in shapes.objects(shape, SH.targetNode):
            for constraint in shapes.objects(shape, SH.sparql):
                text = str(shapes.value(constraint, SH.select))
                text = text.replace("SELECT $this ", "SELECT ").replace("GROUP BY $this ", "GROUP BY ")
                found.append((str(shape), text.replace("$this", f"<{target}>")))
    return tuple(found)


def _oxigraph_store(data: Graph) -> ox.Store:
    store = ox.Store()
    store.load(input=data.serialize(format="nt").encode("utf-8"), format=ox.RdfFormat.N_TRIPLES)
    return store


def _on_oxigraph(store: ox.Store, skip: frozenset[str] = frozenset()) -> set[tuple[str, str]]:
    """(shape, record) of every violation of the runtime shapes in a store, except the shapes in `skip`."""
    return {(shape, row["value"].value) for shape, query in _runtime_selects() if shape not in skip for row in store.query(query)}


def _runtime_violations(report: Graph, skip: frozenset[str] = frozenset()) -> set[tuple[str, str]]:
    """(shape, record) of every violation of the runtime shapes in a pySHACL report, except the shapes in `skip`."""
    runtime = {shape for shape, _ in _runtime_selects()} - skip
    found = {(str(report.value(r, SH.sourceShape)), str(report.value(r, SH.value)))
             for r in report.subjects(SH.resultSeverity, SH.Violation)}
    return {pair for pair in found if pair[0] in runtime}


def _agree(g: Graph, report: Graph) -> None:
    """Every runtime shape finds on Oxigraph what pySHACL reported for `g` (STD-274)."""
    assert _on_oxigraph(_oxigraph_store(g)) == _runtime_violations(report)


def _only(shapes: Graph, *names: URIRef) -> str:
    """Turtle of `shapes` reduced to the node shapes `names`, each with the property shapes and SPARQL constraints it holds."""
    kept = Graph()
    for name in names:
        todo = [name]
        while todo:
            node = todo.pop()
            for p, o in shapes.predicate_objects(node):
                kept.add((node, p, o))
                if isinstance(o, BNode):
                    todo.append(o)
    return kept.serialize(format="turtle")


# ---- LG1-02, LG2-02: LG-0's accepted examples, configuration and runtime records, conform

@pytest.mark.parametrize("name", ACCEPTED)
def test_accepted_examples_conform(name: str) -> None:
    g = MODEL + _example(name)
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)
    _agree(g, report)


# ---- LG1-03, LG1-04, LG1-05, LG1-05b: each refusal fails its named shape -----

@pytest.mark.parametrize("name,shape", REFUSALS.items())
def test_refusals_fail_the_named_shape(name: str, shape: str) -> None:
    g = MODEL + _example(name)
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert not conforms
    hit = {s for s in _violating_shapes(report) if s.endswith(f"#{shape}")}
    assert hit, (name, shape, _violating_shapes(report))
    _agree(g, report)



def test_a_policy_that_settles_to_the_nearest_conforms() -> None:
    """A policy that rounds to the nearest, says the difference is settled and states both directions conforms. It has no records."""
    conforms, report, _ = validate(MODEL + _example("rounding-to-the-nearest"), shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)

def _profile_admits_a_ceiling_above(g: Graph) -> None:
    g.set((_ex("refusal-ceiling-above-stated")["ledger-profile"], LDG.admitsCeilingAboveStated, Literal(True)))


def _floor_stated(g: Graph) -> None:
    ex = _ex("refusal-discrete-without-floor")
    for p, o in [(RDF.type, QNT.Quantity), (QNT.onSpace, ex.units), (QNT.numericValue, _decimal("1"))]:
        g.add((ex["units-floor"], p, o))
    g.add((ex.units, QNT.granularityFloor, ex["units-floor"]))


@pytest.mark.parametrize("name,mutate", [("refusal-ceiling-above-stated", _profile_admits_a_ceiling_above),
                                         ("refusal-discrete-without-floor", _floor_stated)],
                         ids=["a ceiling above the stated amount a profile admits", "a discrete unit with its floor stated"])
def test_the_design_time_refusal_lifts_where_its_condition_is_met(name: str, mutate: Callable[[Graph], None]) -> None:
    g = MODEL + _example(name)
    mutate(g)
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)
    _agree(g, report)


def test_every_discrete_unit_of_an_example_states_a_floor_but_the_refusal() -> None:
    for path in sorted((LEDGER / "examples").glob("*.ttl")):
        g = _graph(path)
        spaces = set(g.subjects(QNT.densityKind, QNT.Discrete))
        bare = {str(sp) for sp in spaces if g.value(sp, QNT.granularityFloor) is None}
        assert bool(bare) == (path.stem == "refusal-discrete-without-floor"), (path.name, bare)


def test_the_conversion_terms_are_gone() -> None:
    """The four terms the ledger dropped when conversion left it are declared by no document of the layer."""
    gone = {LDG.conversionMethod, LDG.amountAsDrawn, LDG.conversionUsed, LDG.ConversionTogetherShape}
    for folder in ("spec", "vocab", "shapes"):
        for path in sorted((LEDGER / folder).glob("*.ttl")):
            g = _graph(path)
            assert not {t for t in gone if (t, None, None) in g}, path.name


# A refusal by a generated structural shape, named by the property whose count is wrong, since such a shape is a blank node in the report.
STRUCTURAL_REFUSALS = {
    "refusal-no-merge-policy": "mergePolicy",
    "refusal-policy-without-rule": "mergeRule",
}


@pytest.mark.parametrize("name,missing", STRUCTURAL_REFUSALS.items())
def test_structural_refusals_miss_the_named_property(name: str, missing: str) -> None:
    conforms, report, _ = validate(MODEL + _example(name), shacl_graph=SHAPES, inference="none", advanced=True)
    assert not conforms
    paths = {str(report.value(r, SH.resultPath)) for r in report.subjects(SH.resultSeverity, SH.Violation)
             if report.value(r, SH.sourceConstraintComponent) == SH.MinCountConstraintComponent}
    assert paths == {str(LDG[missing])}, (name, missing, paths)


# ---- LG1-06: the import guard -------------------------------------------------

def test_imports_only_foundation_vocabulary_quantification() -> None:
    imports = {str(o) for o in MODEL.objects(URIRef("https://www.nebularis.org/neuro-semantic/ledger"),
                                              URIRef("http://www.w3.org/2002/07/owl#imports"))}
    assert all("/foundation/" in i or "/vocabulary/" in i or "/quantification/" in i for i in imports)


# ---- LG1-07: no term of Party, Eligibility, Wording, Instrument or Behaviour --

def test_spec_names_no_higher_layer() -> None:
    hits = repo_files(["ontology/ledger/spec", "ontology/ledger/vocab"], r"\b(ins|bhv|elg|pty|wrd):")
    assert hits == []


# ---- LG1-01: the README's extraction is consistent with the committed Turtle -

def test_literate_extraction_matches_committed_turtle() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "literate_extract.py"),
         str(LEDGER / "README.md"), "--layer", "ledger", "--root", str(ROOT),
         "--proofs-root", str(ROOT / "tools" / "proofs"), "--check"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# ---- LG1-09: the cycle shape finishes on a generated tree, small here and at 10,000 definitions in the benchmark

def test_cycle_shape_scales() -> None:
    """The cycle shape alone, on rdflib through pySHACL, on a wide tree of 1,000 definitions: the property path it walks is what
    recurses past rdflib's call depth on a deep one. The 10,000-definition tree against every shape, with its time recorded, is
    `benchmark/ledger-posting-cost/test_shape_scale.py` (STD-155), since a test that measures is a benchmark."""
    conforms, _, _ = validate(MODEL + account_tree(1_000, sections=9), shacl_graph=CYCLE_SHAPE, inference="none", advanced=True)
    assert conforms


# ==== LG-2: the runtime document ===============================================

OWL_RATIONAL = "http://www.w3.org/2002/07/owl#rational"


def _ex(name: str) -> Namespace:
    return Namespace(f"https://example.org/lattice/ledger/{name}/")


def _decimal(value: str) -> Literal:
    return Literal(Decimal(value), datatype=XSD.decimal)


def _position(value: int) -> Literal:
    return Literal(value, datatype=XSD.nonNegativeInteger)


# ---- LG2-01: the owl:rational probe (LG-Q6, TSD-70) ---------------------------

def _probe_engines() -> list[str]:
    from sparql_probes.engines import REGISTRY, available

    found = available()
    return [engine for engine in REGISTRY if found[engine]]


@pytest.mark.parametrize("engine", _probe_engines())
def test_rational_literals_round_trip_but_never_compare_by_value(engine: str) -> None:
    """Each engine keeps `"1/3"^^owl:rational` lexically, and none compares it by value: `1/3 = 2/6` is
    false and `< "1/2"` matches nothing. So a proportion a shape must compare is two integers."""
    from sparql_probes.engines import run_query

    g = _graph(f"""<urn:a> <urn:p> "1/3"^^<{OWL_RATIONAL}> .
<urn:b> <urn:p> "2/6"^^<{OWL_RATIONAL}> .
<urn:c> <urn:p> "1/2"^^<{OWL_RATIONAL}> .""")
    rows = run_query(g, "SELECT ?s ?o WHERE { ?s <urn:p> ?o } ORDER BY ?s", engine)
    assert [(str(r.s), str(r.o), str(r.o.datatype)) for r in rows] == [
        ("urn:a", "1/3", OWL_RATIONAL), ("urn:b", "2/6", OWL_RATIONAL), ("urn:c", "1/2", OWL_RATIONAL)]
    same = run_query(g, f'SELECT ?s WHERE {{ ?s <urn:p> ?o FILTER (?o = "1/3"^^<{OWL_RATIONAL}>) }}', engine)
    assert [str(r.s) for r in same] == ["urn:a"]
    below = run_query(g, f'SELECT ?s WHERE {{ ?s <urn:p> ?o FILTER (?o < "1/2"^^<{OWL_RATIONAL}>) }}', engine)
    assert list(below) == []


# ---- LG2-03 to LG2-09 and the further laws: each runtime shape refuses a record that breaks it

def _running_balance_off(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["staff-spend-posting"], LDG.runningBalance, _decimal("30001")))


def _credit_above_ceiling(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["equipment-return-posting"], LDG.amountValue, _decimal("55000")))
    g.set((ex["equipment-return-posting"], LDG.runningBalance, _decimal("85000")))


def _applied_above_offered(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["equipment-return-posting"], LDG.offeredValue, _decimal("45000")))


def _applied_short_of_the_room(g: Graph) -> None:
    """40,000 applied of 55,000 offered, the running balance the sum gives, though the account had room for 50,000."""
    ex = _ex("research-grant")
    g.set((ex["equipment-return-posting"], LDG.amountValue, _decimal("40000")))
    g.set((ex["equipment-return-posting"], LDG.runningBalance, _decimal("70000")))


def _debit_with_a_kind(g: Graph) -> None:
    ex = _ex("research-grant")
    g.add((ex["staff-spend-posting"], LDG.creditKind, ex["unspent-funds"]))


def _kind_not_accepted(g: Graph) -> None:
    """The aggregate restored by recoveries alone, so the reinstatement posted to it is of a kind it does not accept."""
    ex = _ex("insurance-aggregate")
    g.add((ex.aggregate, LDG.restoredBy, ex.recovery))


def _no_kind_where_kinds_are_named(g: Graph) -> None:
    """The recovery at the sublimit with no kind, on a path where the annual cap names its kinds."""
    ex = _ex("insurance-aggregate")
    g.remove((ex["recovery-2-posting"], LDG.creditKind, None))


def _cut_above_applied(g: Graph) -> None:
    ex = _ex("credit-cut-at-parent")
    g.set((ex["credit-3-cut-parent"], LDG.cutValue, _decimal("5")))


def _cut_at_its_own_account(g: Graph) -> None:
    ex = _ex("credit-cut-at-parent")
    g.set((ex["credit-3-cut-parent"], LDG.cutAt, ex["account-child"]))


def _cut_missing(g: Graph) -> None:
    """The credit at the child with no cut at the parent, which then sums to 13 against a ceiling of 10."""
    ex = _ex("credit-cut-at-parent")
    g.remove((ex["credit-3-cut-parent"], None, None))


def _cut_where_there_was_room(g: Graph) -> None:
    """A cut of 1 at the grant, which had room for the whole return, so the grant is left below its ceiling."""
    ex = _ex("research-grant")
    cut = ex["equipment-return-cut-grant"]
    for p, o in [(RDF.type, LDG.Cut), (LDG.cutOf, ex["equipment-return-posting"]), (LDG.cutAt, ex["account-grant-budget"]),
                 (LDG.cutValue, _decimal("1"))]:
        g.add((cut, p, o))


def _proportional_one_short(g: Graph) -> None:
    ex = _ex("authority-aggregate")
    g.set((ex["request-1"], LDG.grantedValue, _decimal("33")))
    g.set((ex["posting-1"], LDG.amountValue, _decimal("33")))


def _owner_kind_not_admitted(g: Graph) -> None:
    ex = _ex("research-grant")
    g.remove((ex.institution, RDF.type, ex.Grantee))


def _posting_key_shared(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["equipment-return-posting"], LDG.recordedPosition, _position(1)))


def _forward_dated(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["equipment-return-posting"], LDG.effectivePosition, _position(4)))


def _recorded_against_passes(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["equipment-spend-posting"], LDG.recordedPosition, _position(2)))
    g.set((ex["equipment-return-posting"], LDG.recordedPosition, _position(1)))


def _merge_not_cited(g: Graph) -> None:
    ex = _ex("research-grant")
    g.remove((ex["staff-spend-posting"], PROV.wasDerivedFrom, ex["staff-spend-merge"]))


def _period_key_missing(g: Graph) -> None:
    ex = _ex("licence-seats")
    g.remove((ex["account-seat-licence-london-2028"], LDG.periodKey, None))


def _parent_instance_missing(g: Graph) -> None:
    ex = _ex("research-grant")
    g.remove((ex["account-staff-budget"], LDG.partOfAccount, None))


def _account_key_shared(g: Graph) -> None:
    ex = _ex("research-grant")
    twin = ex["account-staff-budget-twin"]
    for p, o in [(RDF.type, LDG.Account), (LDG.ofDefinition, ex["staff-budget"]), (LDG.forOwner, ex.institution),
                 (LDG.partOfAccount, ex["account-grant-budget"])]:
        g.add((twin, p, o))


def _refused_with_a_granted_value(g: Graph) -> None:
    ex = _ex("refusal-overdraw")
    g.add((ex["request-1"], LDG.grantedValue, _decimal("60")))


def _refused_with_a_residual(g: Graph) -> None:
    ex = _ex("refusal-overdraw")
    g.add((ex["merge-1"], LDG.residualValue, _decimal("100")))


def _refused_for_a_reason_of_no_scheme(g: Graph) -> None:
    """The reason the example stated before the scheme was declared, a concept of its own namespace."""
    ex = _ex("refusal-overdraw")
    g.set((ex["merge-1"], LDG.refusalReason, ex.overdrawn))
    g.add((ex.overdrawn, RDF.type, SKOS.Concept))


def _refused_credit_granted(g: Graph) -> None:
    ex = _ex("refusal-credit-kind")
    g.add((ex["credit-2-request"], LDG.grantedValue, _decimal("5")))


def _granted_above_request(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["staff-spend-request"], LDG.requestedValue, _decimal("80000")))


def _granted_merge_with_a_request_ungranted(g: Graph) -> None:
    """The request of 4 with no granted value, on a merge that granted and states no reason."""
    ex = _ex("whole-or-nothing")
    g.remove((ex["request-2"], LDG.grantedValue, None))


def _posting_from_an_ungranted_request(g: Graph) -> None:
    ex = _ex("whole-or-nothing")
    g.remove((ex["request-1"], LDG.grantedValue, None))


def _residual_short(g: Graph) -> None:
    """A residual of 1, so 5, 0 and 1 sum to 6 of the 7 shared."""
    ex = _ex("whole-or-nothing")
    g.set((ex["merge-1"], LDG.residualValue, _decimal("1")))


def _residual_not_allowed(g: Graph) -> None:
    """The policy no longer allows residuals and names no residual account, and the merge still states 2 left."""
    ex = _ex("whole-or-nothing")
    g.remove((ex["blocks-whole"], LDG.allowsResiduals, None))
    g.remove((ex["blocks-whole"], LDG.residualAccount, None))


def _residual_account_without_permission(g: Graph) -> None:
    ex = _ex("whole-or-nothing")
    g.set((ex["blocks-whole"], LDG.allowsResiduals, Literal(False)))


def _rank_missing(g: Graph) -> None:
    ex = _ex("whole-or-nothing")
    g.remove((ex["request-2"], LDG.rank, None))


def _rank_with_no_criterion(g: Graph) -> None:
    ex = _ex("research-grant")
    g.add((ex["staff-spend-request"], LDG.rank, _position(1)))


def _place_missing(g: Graph) -> None:
    ex = _ex("authority-aggregate")
    g.remove((ex["request-3"], LDG.unitOrderPlace, None))


def _ranks_shared_where_distinct_required(g: Graph) -> None:
    """Both requests at rank 1 under a policy that requires distinct ranks, and the merge still granted."""
    ex = _ex("whole-or-nothing")
    g.add((ex["blocks-whole"], LDG.requiresDistinctRanks, Literal(True)))
    g.set((ex["request-2"], LDG.rank, _position(1)))


def _purposes_differ_where_one_required(g: Graph) -> None:
    """One request names a purpose and the other none, under a policy that requires them to agree, and the merge granted."""
    ex = _ex("whole-or-nothing")
    g.add((ex["blocks-whole"], LDG.requiresSamePurpose, Literal(True)))
    g.add((ex["request-1"], LDG.forPurpose, ex["working-capital"]))


def _checkpoint(balance: str, name: str = "research-grant", account: str = "account-grant-budget",
                close: int = 3, debits: str = "140000", offered: str = "55000") -> Callable[[Graph], None]:
    """A checkpoint at `close`, by default the grant's after the return: 90,000 and 50,000 drawn, 55,000 offered, and 110,000 held."""
    def mutate(g: Graph) -> None:
        ex = _ex(name)
        checkpoint = ex[f"checkpoint-{close}"]
        for p, o in [(RDF.type, LDG.Checkpoint), (LDG.onAccount, ex[account]),
                     (LDG.closePosition, _position(close)), (LDG.balanceValue, _decimal(balance)),
                     (LDG.debitsTotal, _decimal(debits)), (LDG.creditsOfferedTotal, _decimal(offered))]:
            g.add((checkpoint, p, o))
    return mutate


def _set(name: str, subject: str, prop: URIRef, value: Literal) -> Callable[[Graph], None]:
    def mutate(g: Graph) -> None:
        g.set((_ex(name)[subject], prop, value))
    return mutate


def _pass(name: str, key: str) -> URIRef:
    """A pass of an example, named from the example's one ledger and the key of its evaluation."""
    ledger = next(_example(name).subjects(RDF.type, LDG.Ledger))
    return URIRef(f"{ledger}/pass/{key}")


def _pass_revision(name: str, key: str, revision: int) -> Callable[[Graph], None]:
    def mutate(g: Graph) -> None:
        g.set((_pass(name, key), LDG.passRevision, _position(revision)))
    return mutate


def _ledger_revision(name: str, owner: str, revision: int) -> Callable[[Graph], None]:
    def mutate(g: Graph) -> None:
        g.set((_ex(name)[f"ledger-{owner}"], LDG.revision, _position(revision)))
    return mutate


def _both(*mutations: Callable[[Graph], None]) -> Callable[[Graph], None]:
    def mutate(g: Graph) -> None:
        for m in mutations:
            m(g)
    return mutate


def _not_moved_since_the_last_close(g: Graph) -> None:
    """A checkpoint of the parent at a close after position 5, where nothing was recorded, equal to the one after position 4."""
    _checkpoint("10", "credit-cut-at-parent", "account-parent", 5, "5", "9")(g)


def _never_moved(g: Graph) -> None:
    """A checkpoint of the equipment budget after position 1, before anything was recorded on it: its stated amount, with nothing
    drawn or offered."""
    _checkpoint("80000", account="account-equipment-budget", close=1, debits="0", offered="0")(g)


def _second_ledger_for_one_owner(g: Graph) -> None:
    ex = _ex("credit-cut-at-parent")
    twin = ex["ledger-holder-twin"]
    for p, o in [(RDF.type, LDG.Ledger), (LDG.forOwner, ex.holder), (LDG.ledgerProfile, ex["ledger-profile"]),
                 (LDG.revision, _position(4))]:
        g.add((twin, p, o))


def _pass_on_two_owners(g: Graph) -> None:
    """The equipment spend's merge on the grant of a second grantee, whose own ledger is at that pass's revision."""
    ex = _ex("research-grant")
    for s, p, o in [(ex.other, RDF.type, ex.Grantee), (ex["account-grant-budget-other"], RDF.type, LDG.Account),
                    (ex["account-grant-budget-other"], LDG.ofDefinition, ex["grant-budget"]),
                    (ex["account-grant-budget-other"], LDG.forOwner, ex.other),
                    (ex["ledger-other"], RDF.type, LDG.Ledger), (ex["ledger-other"], LDG.forOwner, ex.other),
                    (ex["ledger-other"], LDG.ledgerProfile, ex["ledger-profile"]),
                    (ex["ledger-other"], LDG.revision, _position(2))]:
        g.add((s, p, o))
    g.set((ex["equipment-spend-merge"], LDG.onAccount, ex["account-grant-budget-other"]))


def _owner_without_a_ledger(g: Graph) -> None:
    g.remove((_ex("research-grant")["ledger-institution"], None, None))


def _pass_without_a_record(g: Graph) -> None:
    idle = _pass("research-grant", "idle")
    for p, o in [(RDF.type, LDG.Pass), (LDG.passPosition, _position(4)), (LDG.passRevision, _position(4))]:
        g.add((idle, p, o))


def _closing_recurrence_on_a_definition(g: Graph) -> None:
    ex = _ex("credit-cut-at-parent")
    g.add((ex.child, LDG.closingRecurrence, ex.closes))


def _kinds_with_no_edition(g: Graph) -> None:
    """The annual cap names the kinds that restore it and pins no edition."""
    ex = _ex("insurance-aggregate")
    g.remove((ex["annual-cap"], LDG.creditKindsEdition, None))


def _kind_outside_the_edition(g: Graph) -> None:
    """The recovery the parent names is no longer a concept of the edition the parent pins."""
    ex = _ex("credit-cut-at-parent")
    g.remove((ex.recovery, SKOS.inScheme, ex["credit-kinds-edition-1"]))


def _supersession_graph(g: Graph, *triples: tuple[object, URIRef, object]) -> None:
    """Adds triples to the supersession example, a subject given as a string being a node of the example."""
    ex = _ex("supersession-raised-amount")

    def node(term: object) -> object:
        return term if isinstance(term, (URIRef, Literal)) else ex[term]

    for s, p, o in triples:
        g.add((node(s), p, node(o)))


def _supersession_names_two_versions(g: Graph) -> None:
    """The aggregate's first version beside its second, two versions of one identity."""
    _supersession_graph(g, ("supersession-1", LDG.supersedingVersion, "aggregate-1"))


def _period_recurrence_stated(g: Graph, *versions: str) -> None:
    """A yearly recurrence stated by each of `versions`, which the supersession's first version did not state."""
    _supersession_graph(g, ("year", RDF.type, QNT.Recurrence), ("year", FND.hasIdentity, "year-identity"),
                        ("year-identity", RDF.type, FND.PersistentIdentity))
    for version in versions:
        _supersession_graph(g, (version, LDG.periodRecurrence, "year"))


def _recurrence_without_a_period_key(g: Graph) -> None:
    """The aggregate's second version states a recurrence and the supersession no period key."""
    _period_recurrence_stated(g, "aggregate-2")


def _period_key_without_a_recurrence(g: Graph) -> None:
    """A bin on the supersession though no version it names states a recurrence."""
    _period_recurrence_stated(g)
    _supersession_graph(g, ("year-2028", RDF.type, QNT.RecurrenceBin), ("year-2028", QNT.generatedByRecurrence, "year"),
                        ("supersession-1", LDG.periodKey, "year-2028"))


def _period_key_beside_a_version_with_no_recurrence(g: Graph) -> None:
    """The aggregate's second version states a recurrence and the supersession its bin, and the section's second version states none."""
    _period_recurrence_stated(g, "aggregate-2")
    _supersession_graph(g, ("year-2028", RDF.type, QNT.RecurrenceBin), ("year-2028", QNT.generatedByRecurrence, "year"),
                        ("supersession-1", LDG.periodKey, "year-2028"))


def _supersession_forward_dated(g: Graph) -> None:
    g.set((_ex("supersession-raised-amount")["supersession-1"], LDG.effectivePosition, _position(3)))


def _supersession_for_an_owner_with_no_ledger(g: Graph) -> None:
    """The one record of the second pass is a supersession for an owner that has no ledger."""
    ex = _ex("supersession-raised-amount")
    g.add((ex.other, RDF.type, FND.PersistentIdentity))
    g.set((ex["supersession-1"], LDG.forOwner, ex.other))


def _supersession_in_a_pass_of_another_owner(g: Graph) -> None:
    """A second supersession, for another owner, in the first pass, which writes a posting on the holder's account."""
    ex = _ex("supersession-raised-amount")
    _supersession_graph(g, ("other-supersession", RDF.type, LDG.Supersession), ("other-supersession", LDG.forOwner, "other"),
                        ("other-supersession", LDG.effectivePosition, _position(1)),
                        ("other-supersession", LDG.inPass, _pass("supersession-raised-amount", "draw-1")),
                        ("other-supersession", LDG.supersedingVersion, "aggregate-2"), ("other", RDF.type, FND.PersistentIdentity))


def _supersession_pass_revision_repeated(g: Graph) -> None:
    """The second pass records the first pass's revision, with the ledger at it."""
    _pass_revision("supersession-raised-amount", "supersession-2", 1)(g)
    _ledger_revision("supersession-raised-amount", "holder", 1)(g)


def _account_of_a_later_version(g: Graph) -> None:
    """A second account of the aggregate's identity for the holder, which opened under the later version."""
    _supersession_graph(g, ("account-aggregate-later", RDF.type, LDG.Account), ("account-aggregate-later", LDG.ofDefinition, "aggregate-2"),
                        ("account-aggregate-later", LDG.forOwner, "holder"))


MUTATIONS = {
    "a running balance one minor unit off": ("research-grant", _running_balance_off, "RunningBalanceShape"),
    "LG2-05 a credit above the ceiling": ("research-grant", _credit_above_ceiling, "CreditCeilingShape"),
    "a credit applied above what it offered": ("research-grant", _applied_above_offered, "CreditAmountsShape"),
    "a credit applied short of the room": ("research-grant", _applied_short_of_the_room, "CreditAmountsShape"),
    "a debit with a kind": ("research-grant", _debit_with_a_kind, "CreditAmountsShape"),
    "a credit of a kind its account does not accept": ("insurance-aggregate", _kind_not_accepted, "CreditKindAcceptedShape"),
    "a credit with no kind where kinds are named": (
        "insurance-aggregate", _no_kind_where_kinds_are_named, "CreditKindAcceptedShape"),
    "a cut above the amount applied": ("credit-cut-at-parent", _cut_above_applied, "CutWithinTheCreditShape"),
    "a cut at its credit's own account": ("credit-cut-at-parent", _cut_at_its_own_account, "CutWithinTheCreditShape"),
    "a credit with no cut where its ancestor had less room": ("credit-cut-at-parent", _cut_missing, "CutFillsTheAncestorShape"),
    "a cut where the ancestor had room": ("research-grant", _cut_where_there_was_room, "CutFillsTheAncestorShape"),
    "LG2-06 a proportional merge one unit short": (
        "authority-aggregate", _proportional_one_short, "MergeWithinAvailabilityShape"),
    "LG2-08 an owner of a kind not admitted": ("research-grant", _owner_kind_not_admitted, "OwnerKindAdmittedShape"),
    "LG2-09 two postings with one natural key": ("research-grant", _posting_key_shared, "PostingNaturalKeyShape"),
    "a forward-dated posting (STD-294)": ("research-grant", _forward_dated, "NotForwardDatedShape"),
    "a recorded order against the passes": ("research-grant", _recorded_against_passes, "RecordedOrderFollowsPassesShape"),
    "a merged posting not citing its merge": ("research-grant", _merge_not_cited, "MergedPostingCitesMergeShape"),
    "a periodic account with no period key": ("licence-seats", _period_key_missing, "PeriodKeyFromRecurrenceShape"),
    "an instance not part of its parent's": (
        "research-grant", _parent_instance_missing, "PartOfAccountFollowsDefinitionShape"),
    "two accounts with one natural key": ("research-grant", _account_key_shared, "AccountNaturalKeyShape"),
    "two accounts of two versions of one definition": (
        "supersession-raised-amount", _account_of_a_later_version, "AccountNaturalKeyShape"),
    "a supersession naming two versions of one definition": (
        "supersession-raised-amount", _supersession_names_two_versions, "SupersessionNamesOneVersionOfEachDefinitionShape"),
    "a supersession with no period key where a version states a recurrence": (
        "supersession-raised-amount", _recurrence_without_a_period_key, "SupersessionPeriodFromRecurrenceShape"),
    "a supersession with a period key where no version states a recurrence": (
        "supersession-raised-amount", _period_key_without_a_recurrence, "SupersessionPeriodFromRecurrenceShape"),
    "a supersession with a period key that names a version of no recurrence": (
        "supersession-raised-amount", _period_key_beside_a_version_with_no_recurrence, "SupersessionPeriodFromRecurrenceShape"),
    "a forward-dated supersession": ("supersession-raised-amount", _supersession_forward_dated, "NotForwardDatedShape"),
    "a pass whose one record is a supersession for an owner with no ledger": (
        "supersession-raised-amount", _supersession_for_an_owner_with_no_ledger, "PassWritesOneLedgerShape"),
    "a pass that writes a supersession for another owner": (
        "supersession-raised-amount", _supersession_in_a_pass_of_another_owner, "PassWritesOneLedgerShape"),
    "a pass of a supersession at a revision already recorded": (
        "supersession-raised-amount", _supersession_pass_revision_repeated, "PassRevisionsInOrderShape"),
    "a refused merge granting a request": ("refusal-overdraw", _refused_with_a_granted_value, "RefusedMergeShape"),
    "a refused merge stating a residual": ("refusal-overdraw", _refused_with_a_residual, "RefusedMergeShape"),
    "a refusal whose reason is of no scheme": ("refusal-overdraw", _refused_for_a_reason_of_no_scheme, "RefusedMergeShape"),
    "a refused credit granted": ("refusal-credit-kind", _refused_credit_granted, "RefusedMergeShape"),
    "a request granted above what it asked": ("research-grant", _granted_above_request, "GrantedWithinRequestShape"),
    "a granted merge with a request ungranted": (
        "whole-or-nothing", _granted_merge_with_a_request_ungranted, "GrantedMergeShape"),
    "a posting from a request with no granted value": (
        "whole-or-nothing", _posting_from_an_ungranted_request, "MergedPostingCitesMergeShape"),
    "a residual that leaves the sum short": ("whole-or-nothing", _residual_short, "MergeWithinAvailabilityShape"),
    "a residual where none is allowed": ("whole-or-nothing", _residual_not_allowed, "ResidualPermittedShape"),
    "a rank missing where the policy states a criterion": ("whole-or-nothing", _rank_missing, "RanksAsDeclaredShape"),
    "a rank where the policy states no criterion": ("research-grant", _rank_with_no_criterion, "RanksAsDeclaredShape"),
    "a place missing where the policy orders units": ("authority-aggregate", _place_missing, "RanksAsDeclaredShape"),
    "a shared rank granted where distinct ranks are required": (
        "whole-or-nothing", _ranks_shared_where_distinct_required, "MergeGuardsShape"),
    "purposes that differ granted where one is required": (
        "whole-or-nothing", _purposes_differ_where_one_required, "MergeGuardsShape"),
    "a residual account on a policy that allows no residual": (
        "whole-or-nothing", _residual_account_without_permission, "ResidualAccountNeedsResidualsShape"),
    "a checkpoint one minor unit off": ("research-grant", _checkpoint("110001"), "CheckpointFoldShape"),
    "a checkpoint that leaves out the cut": (
        "credit-cut-at-parent", _set("credit-cut-at-parent", "checkpoint-parent-3", LDG.balanceValue, _decimal("13")),
        "CheckpointFoldShape"),
    "a checkpoint's debits one unit off": (
        "credit-cut-at-parent", _set("credit-cut-at-parent", "checkpoint-parent-3", LDG.debitsTotal, _decimal("6")),
        "CheckpointTotalsShape"),
    "a checkpoint's credits offered counted at the amount applied less the cut": (
        "credit-cut-at-parent", _set("credit-cut-at-parent", "checkpoint-parent-3", LDG.creditsOfferedTotal, _decimal("5")),
        "CheckpointTotalsShape"),
    "a checkpoint's credits offered counting a kind the account does not accept": (
        "insurance-aggregate", _checkpoint("10000000", "insurance-aggregate", "account-annual-cap", 4, "10300000", "10300000"),
        "CheckpointTotalsShape"),
    "a checkpoint for an account that did not move since its last": (
        "credit-cut-at-parent", _not_moved_since_the_last_close, "CheckpointOnlyWhereMovedShape"),
    "a checkpoint for an account that never moved": ("research-grant", _never_moved, "CheckpointOnlyWhereMovedShape"),
    "two ledgers for one owner": ("credit-cut-at-parent", _second_ledger_for_one_owner, "OneLedgerPerOwnerShape"),
    "a pass on the accounts of two owners": ("research-grant", _pass_on_two_owners, "PassWritesOneLedgerShape"),
    "a pass whose owner has no ledger": ("research-grant", _owner_without_a_ledger, "PassWritesOneLedgerShape"),
    "a pass that writes no record": ("research-grant", _pass_without_a_record, "PassWritesOneLedgerShape"),
    "two passes of one ledger at one revision": (
        "research-grant", _both(_pass_revision("research-grant", "equipment-return", 2),
                                _ledger_revision("research-grant", "institution", 2)), "PassRevisionsInOrderShape"),
    "revisions against the order of the passes": (
        "research-grant", _both(_pass_revision("research-grant", "staff-spend", 2),
                                _pass_revision("research-grant", "equipment-spend", 1)), "PassRevisionsInOrderShape"),
    "a revision skipped": (
        "research-grant", _both(_pass_revision("research-grant", "equipment-return", 4),
                                _ledger_revision("research-grant", "institution", 4)), "PassRevisionsInOrderShape"),
    "a ledger whose first pass records revision 2": (
        "whole-or-nothing", _both(_pass_revision("whole-or-nothing", "blocks-1", 2),
                                  _ledger_revision("whole-or-nothing", "issuer", 2)), "PassRevisionsInOrderShape"),
    "a ledger behind its latest pass": (
        "research-grant", _ledger_revision("research-grant", "institution", 2), "LedgerAtItsLatestPassShape"),
    "a closing recurrence on an account definition": (
        "credit-cut-at-parent", _closing_recurrence_on_a_definition, "ClosingRecurrenceOnProfileShape"),
    "a definition that names its kinds and pins no edition": (
        "insurance-aggregate", _kinds_with_no_edition, "RestoringKindsInTheirEditionShape"),
    "a kind outside the edition its definition pins": (
        "credit-cut-at-parent", _kind_outside_the_edition, "RestoringKindsInTheirEditionShape"),
}


@pytest.mark.parametrize("case", MUTATIONS)
def test_runtime_law_refuses_a_record_that_breaks_it(case: str) -> None:
    name, mutate, shape = MUTATIONS[case]
    g = MODEL + _example(name)
    mutate(g)
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert not conforms
    assert any(s.endswith(f"#{shape}") for s in _violating_shapes(report)), (shape, _violating_shapes(report))
    _agree(g, report)


@pytest.mark.parametrize("name,mutate", [
    ("research-grant", _checkpoint("110000")),
    ("insurance-aggregate", _checkpoint("10000000", "insurance-aggregate", "account-annual-cap", 4, "10300000", "300000")),
], ids=["the grant after the return", "the annual cap, which a reinstatement does not restore"])
def test_a_checkpoint_at_the_sum_conforms(name: str, mutate: Callable[[Graph], None]) -> None:
    g = MODEL + _example(name)
    mutate(g)
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)
    _agree(g, report)


def test_a_credit_cut_in_full_moves_the_account() -> None:
    """ADR-A131's addendum of 2026-11-19: the parent's balance is 10 at the closes after positions 3 and 4, and it still has a
    checkpoint at both, since the credit cut in full at it raised its credits offered. The example conforms (LG27-01)."""
    g = _example("credit-cut-at-parent")
    ex = _ex("credit-cut-at-parent")
    totals = [(g.value(c, LDG.balanceValue), g.value(c, LDG.debitsTotal), g.value(c, LDG.creditsOfferedTotal))
              for c in (ex["checkpoint-parent-3"], ex["checkpoint-parent-4"])]
    assert totals == [(_decimal("10"), _decimal("5"), _decimal("8")), (_decimal("10"), _decimal("5"), _decimal("9"))]
    assert [(g.value(c, LDG.cutAt), g.value(c, LDG.cutValue)) for c in g.subjects(LDG.cutOf, ex["credit-4-posting"])] == [
        (ex["account-parent"], _decimal("1"))]


RECORDED = [*ACCEPTED, "refusal-overdraw", "refusal-credit-kind", "refusal-incompatible-draw", "refusal-unrepresentable-amount"]


@pytest.mark.parametrize("name", RECORDED)
def test_each_pass_is_named_from_its_ledger_and_moves_it_once(name: str) -> None:
    """Each example with records has one ledger for its one owner, under a profile. Each pass's IRI is the ledger's, then
    `/pass/` and the key of its evaluation (LG-Q46), and the passes in the order of their positions record 1, 2 and so on, the
    ledger at the last (LG-Q37, LG-Q45)."""
    g = _example(name)
    ledgers = list(g.subjects(RDF.type, LDG.Ledger))
    assert len(ledgers) == 1
    ledger = ledgers[0]
    assert (g.value(ledger, LDG.ledgerProfile), RDF.type, LDG.LedgerProfile) in g
    passes = sorted(g.subjects(RDF.type, LDG.Pass), key=lambda p: int(g.value(p, LDG.passPosition)))
    assert passes and all(str(p).startswith(f"{ledger}/pass/") for p in passes)
    assert [int(g.value(p, LDG.passRevision)) for p in passes] == list(range(1, len(passes) + 1))
    assert int(g.value(ledger, LDG.revision)) == len(passes)


def test_the_closing_recurrence_is_the_profiles() -> None:
    """`ldg:closingRecurrence` is on the ledger profile and no account definition restricts it (LG-Q24, MEC-105). A ledger names
    its profile by an edge that bears meaning (LG-Q37)."""
    assert MODEL.value(LDG.closingRecurrence, RDFS.domain) == LDG.LedgerProfile
    restricted = {MODEL.value(r, OWL.onProperty) for r in MODEL.objects(LDG.AccountDefinition, RDFS.subClassOf)}
    assert LDG.closingRecurrence not in restricted
    assert MODEL.value(LDG.ledgerProfile, FND.meaningBearing) == Literal(True)
    assert (LDG.LedgerProfile, RDFS.subClassOf, FND.Versioned) in MODEL


# A ledger, a pass and a checkpoint missing what they must state, each refused by a generated structural shape.
MISSING = {
    "a ledger with no profile": ("research-grant", "ledger-institution", LDG.ledgerProfile),
    "a ledger with no revision": ("research-grant", "ledger-institution", LDG.revision),
    "a checkpoint with no debits": ("credit-cut-at-parent", "checkpoint-child-3", LDG.debitsTotal),
    "a checkpoint with no credits offered": ("credit-cut-at-parent", "checkpoint-child-3", LDG.creditsOfferedTotal),
}


@pytest.mark.parametrize("case", MISSING)
def test_a_record_missing_what_it_must_state_is_refused(case: str) -> None:
    name, subject, prop = MISSING[case]
    g = MODEL + _example(name)
    g.remove((_ex(name)[subject], prop, None))
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert not conforms
    paths = {str(report.value(r, SH.resultPath)) for r in report.subjects(SH.resultSeverity, SH.Violation)
             if report.value(r, SH.sourceConstraintComponent) == SH.MinCountConstraintComponent}
    assert paths == {str(prop)}


def test_a_pass_with_no_revision_is_refused() -> None:
    g = MODEL + _example("research-grant")
    g.remove((_pass("research-grant", "staff-spend"), LDG.passRevision, None))
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert not conforms
    paths = {str(report.value(r, SH.resultPath)) for r in report.subjects(SH.resultSeverity, SH.Violation)
             if report.value(r, SH.sourceConstraintComponent) == SH.MinCountConstraintComponent}
    assert paths == {str(LDG.passRevision)}


def test_the_cut_example_records_the_addendum_case() -> None:
    """The conformance case of a cut at an ancestor (ADR-A131, its first addendum of 2026-11-16): the last credit is applied at 4
    at the child, leaving it at 9, and cut by 3 at the parent."""
    g = _example("credit-cut-at-parent")
    ex = _ex("credit-cut-at-parent")
    credit = ex["credit-3-posting"]
    assert (g.value(credit, LDG.offeredValue), g.value(credit, LDG.amountValue), g.value(credit, LDG.runningBalance)) == (
        _decimal("4"), _decimal("4"), _decimal("9"))
    assert [(g.value(c, LDG.cutAt), g.value(c, LDG.cutValue)) for c in g.subjects(LDG.cutOf, credit)] == [
        (ex["account-parent"], _decimal("3"))]


def _later_debit_at_the_parent(balance: str) -> Callable[[Graph], None]:
    """One more debit of 1 at the parent, in a fifth pass, recording `balance` after it. The parent's stated 10, less the 6 drawn in its
    subtree, plus the 9 credits applied in it, less the cuts of 4 recorded at it, is 9, and 13 where the cuts are ignored."""
    def mutate(g: Graph) -> None:
        ex = _ex("credit-cut-at-parent")
        later = _pass("credit-cut-at-parent", "debit-5")
        for p, o in [(RDF.type, LDG.Pass), (LDG.passPosition, _position(5)), (LDG.passRevision, _position(5))]:
            g.add((later, p, o))
        posting = ex["debit-5-posting"]
        for p, o in [(RDF.type, LDG.Posting), (LDG.onAccount, ex["account-parent"]), (LDG.inPass, later),
                     (LDG.effectivePosition, _position(5)), (LDG.recordedPosition, _position(2)), (LDG.microPosition, _position(0)),
                     (LDG.direction, LDG.Debit), (LDG.amountValue, _decimal("1")), (LDG.runningBalance, _decimal(balance))]:
            g.add((posting, p, o))
        g.set((ex["ledger-holder"], LDG.revision, _position(5)))
    return mutate


def test_a_running_balance_reads_the_cuts_at_its_account() -> None:
    """A debit on the parent after the cuts at it. Its balance is the stated amount less the debits plus the credits applied, less the
    cuts recorded at the parent, so one that ignores them is reported."""
    g = MODEL + _example("credit-cut-at-parent")
    _later_debit_at_the_parent("9")(g)
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)
    _agree(g, report)
    g = MODEL + _example("credit-cut-at-parent")
    _later_debit_at_the_parent("13")(g)
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert not conforms
    assert any(v.endswith("#RunningBalanceShape") for v in _violating_shapes(report)), _violating_shapes(report)
    _agree(g, report)


# ---- LG2-07: the refusal under ldg:Refuse conforms, with no posting and a reason, and keeps its requests

def test_refused_merge_conforms_with_no_posting_and_a_reason() -> None:
    g = MODEL + _example("refusal-overdraw")
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)
    _agree(g, report)
    ex = _ex("refusal-overdraw")
    assert list(g.subjects(RDF.type, LDG.Posting)) == []
    assert g.value(ex["merge-1"], LDG.refusalReason) == LDG.ExceedsAvailable
    requests = set(g.objects(ex["merge-1"], LDG.request))
    assert requests == {ex["request-1"], ex["request-2"]}
    assert {g.value(r, LDG.requestedValue) for r in requests} == {_decimal("60"), _decimal("70")}
    assert [g.value(r, LDG.grantedValue) for r in requests] == [None, None]


# ---- LG-26: requests, the residual and its account, the reasons for a refusal, requests of no use in part

def test_a_credit_refused_alone_is_a_record_with_one_request_and_a_reason() -> None:
    """The conformance case of a credit its account does not accept (ADR-A131, its fourth addendum of 2026-11-16): refused, no
    posting, and recorded as a merge record on the child with the credit as its one request and `ldg:KindNotAccepted`."""
    g = MODEL + _example("refusal-credit-kind")
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)
    _agree(g, report)
    ex = _ex("refusal-credit-kind")
    assert list(g.subjects(LDG.direction, LDG.Credit)) == []
    refusal = ex["credit-2-refusal"]
    assert g.value(refusal, LDG.refusalReason) == LDG.KindNotAccepted
    assert list(g.objects(refusal, LDG.request)) == [ex["credit-2-request"]]
    assert g.value(ex["credit-2-request"], LDG.grantedValue) is None


def test_requests_of_no_use_in_part_record_the_addendum_case() -> None:
    """The conformance case of requests of no use in part (ADR-A131, its second addendum of 2026-11-16): 5 and 4, in that order,
    share 7 each whole or not at all, so 5 and 0 are granted and 2 is left, under a policy that allows a residual."""
    g = _example("whole-or-nothing")
    ex = _ex("whole-or-nothing")
    assert g.value(ex["blocks-whole"], LDG.mergeRule) == LDG.WholeOrNothing
    granted = {g.value(r, LDG.rank): g.value(r, LDG.grantedValue) for r in g.objects(ex["merge-1"], LDG.request)}
    assert granted == {_position(1): _decimal("5"), _position(2): _decimal("0")}
    assert g.value(ex["merge-1"], LDG.residualValue) == _decimal("2")
    assert g.value(ex["blocks-whole"], LDG.residualAccount) == ex.unallocated


def _guards_met(g: Graph) -> None:
    """Both guards stated, with distinct ranks and one purpose on both requests."""
    ex = _ex("whole-or-nothing")
    g.add((ex["blocks-whole"], LDG.requiresDistinctRanks, Literal(True)))
    g.add((ex["blocks-whole"], LDG.requiresSamePurpose, Literal(True)))
    for request in (ex["request-1"], ex["request-2"]):
        g.add((request, LDG.forPurpose, ex["working-capital"]))


def _shared_rank_that_fits(g: Graph) -> None:
    """Requests of 5 and 2 that share a rank and fit the 7, so they are granted as asked whatever the policy requires."""
    ex = _ex("whole-or-nothing")
    g.add((ex["blocks-whole"], LDG.requiresDistinctRanks, Literal(True)))
    g.set((ex["request-2"], LDG.rank, _position(1)))
    g.set((ex["request-2"], LDG.requestedValue, _decimal("2")))
    g.set((ex["request-2"], LDG.grantedValue, _decimal("2")))
    g.remove((ex["merge-1"], LDG.residualValue, None))


@pytest.mark.parametrize("mutate", [_guards_met, _shared_rank_that_fits], ids=["both guards met", "a shared rank that fits"])
def test_a_merge_the_guards_admit_conforms(mutate: Callable[[Graph], None]) -> None:
    g = MODEL + _example("whole-or-nothing")
    mutate(g)
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)
    _agree(g, report)


def test_a_merge_record_holds_at_least_one_request() -> None:
    g = MODEL + _example("refusal-overdraw")
    g.remove((_ex("refusal-overdraw")["merge-1"], LDG.request, None))
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert not conforms
    paths = {str(report.value(r, SH.resultPath)) for r in report.subjects(SH.resultSeverity, SH.Violation)
             if report.value(r, SH.sourceConstraintComponent) == SH.MinCountConstraintComponent}
    assert paths == {str(LDG.request)}


def test_the_grant_is_retired_and_the_eight_reasons_are_one_scheme() -> None:
    """No `ldg:Grant` or `ldg:grant` is declared (LG-Q38), and `ldg:RefusalReasons` holds eight reasons, six for a merge, one for a
    credit and one for a supersession (LG-Q31, LG-Q56)."""
    assert (LDG.Grant, None, None) not in MODEL and (LDG.grant, None, None) not in MODEL
    reasons = set(MODEL.subjects(SKOS.inScheme, LDG.RefusalReasons))
    assert reasons == {LDG.ExceedsAvailable, LDG.RanksNotDistinct, LDG.TieWithoutRule, LDG.ResidualNotPermitted,
                       LDG.MixedPurposes, LDG.CrossingSets, LDG.KindNotAccepted, LDG.StatedBelowDrawn}
    assert all((reason, RDF.type, SKOS.Concept) in MODEL for reason in reasons)


# ---- LG-28: the account definition versioned, its edges that bear meaning, and the edition of its kinds

EXAMPLES = sorted(path.stem for path in (LEDGER / "examples").glob("*.ttl"))
MEANING_BEARING = {LDG.statedAmount, LDG.creditCeiling, LDG.unitOfAccount, LDG.partOf, LDG.mergePolicy, LDG.periodRecurrence,
                   LDG.restoredBy, LDG.creditKindsEdition, LDG.residualAccount, LDG.ledgerProfile}


def _foundation_findings(g: Graph) -> set[tuple[str, str, str]]:
    """(shape, focus node, message) of every result of Foundation's `fnd:MeaningBearingEdgeShape` on `g`, and of its
    `fnd:VersionedShape` on the ledger's own versioned classes, violations and warnings alike. The message of a meaning-bearing edge
    names the edge. Quantification's operation capabilities are versioned too and carry no identity in any module's example, which
    is Quantification's to answer, so the ledger's tests leave them out."""
    _, report, _ = validate(g, shacl_graph=FOUNDATION_SHAPES, inference="none", advanced=True)
    ours = {LDG.AccountDefinition, LDG.MergePolicy, LDG.LedgerProfile}
    found = set()
    for r in report.subjects(RDF.type, SH.ValidationResult):
        shape, focus = str(report.value(r, SH.sourceShape)).rsplit("#", 1)[-1], report.value(r, SH.focusNode)
        if shape == "VersionedShape" and not ours & set(g.objects(focus, RDF.type)):
            continue
        found.add((shape, str(focus), str(report.value(r, SH.resultMessage))))
    return found


def test_the_account_definition_is_versioned_and_its_edges_bear_meaning() -> None:
    """`ldg:AccountDefinition` is a `fnd:Versioned` (LG-Q40, TD-102). The ledger marks exactly these edges `fnd:meaningBearing`
    (ADR-A142 decision 2), and `ldg:creditKindsEdition` is the pin LG-Q22 (a) decided, at most one on a definition."""
    assert (LDG.AccountDefinition, RDFS.subClassOf, FND.Versioned) in MODEL
    marked = {p for p in MODEL.subjects(FND.meaningBearing, Literal(True)) if str(p).startswith(str(LDG))}
    assert marked == MEANING_BEARING
    assert (MODEL.value(LDG.creditKindsEdition, RDFS.domain), MODEL.value(LDG.creditKindsEdition, RDFS.range)) == (
        LDG.AccountDefinition, SKOS.ConceptScheme)
    assert (LDG.creditKindsEdition, RDF.type, OWL.FunctionalProperty) in MODEL


@pytest.mark.parametrize("name", EXAMPLES)
def test_foundation_finds_every_example_versioned_and_its_parts_pinned(name: str) -> None:
    """Every example, accepted or refused: each versioned thing has one identity, and no edge that bears meaning leads to a node that
    is neither versioned, minted under its subject nor a published term, so Foundation's check warns on no quantity (LG-Q40 (a))."""
    assert len(EXAMPLES) == 24
    g = MODEL + _example(name)
    assert _foundation_findings(g) == set()
    definitions = list(g.subjects(RDF.type, LDG.AccountDefinition))
    assert definitions and all(len(list(g.objects(d, FND.hasIdentity))) == 1 for d in definitions)


def _no_identity(name: str, subject: str) -> Callable[[Graph], None]:
    def mutate(g: Graph) -> None:
        g.remove((_ex(name)[subject], FND.hasIdentity, None))
    return mutate


def _shared_stated_amount(g: Graph) -> None:
    """The staff budget's stated amount is a quantity of the example's own, minted under no definition."""
    ex = _ex("research-grant")
    for p, o in [(RDF.type, QNT.Quantity), (QNT.onSpace, ex.funds), (QNT.numericValue, _decimal("120000"))]:
        g.add((ex["q-120000"], p, o))
    g.set((ex["staff-budget"], LDG.statedAmount, ex["q-120000"]))


def _ceiling_of_another_definition(g: Graph) -> None:
    """The equipment budget's ceiling is the grant's stated amount, minted under the grant and not under it."""
    ex = _ex("research-grant")
    g.set((ex["equipment-budget"], LDG.creditCeiling, ex["grant-budget/stated-amount"]))


def _kind_not_published(g: Graph) -> None:
    g.remove((_ex("insurance-aggregate").recovery, RDFS.isDefinedBy, None))


FOUNDATION_MUTATIONS = {
    "a definition with no identity": ("insurance-aggregate", _no_identity("insurance-aggregate", "aggregate"),
                                      "VersionedShape", "aggregate", None),
    "a parent with no identity": ("insurance-aggregate", _no_identity("insurance-aggregate", "aggregate"),
                                  "MeaningBearingEdgeShape", "section-a", LDG.partOf),
    "a stated amount minted under no definition": ("research-grant", _shared_stated_amount, "MeaningBearingEdgeShape",
                                                   "staff-budget", LDG.statedAmount),
    "a ceiling minted under another definition": ("research-grant", _ceiling_of_another_definition, "MeaningBearingEdgeShape",
                                                  "equipment-budget", LDG.creditCeiling),
    "a unit of account with no identity": ("research-grant", _no_identity("research-grant", "funds"), "MeaningBearingEdgeShape",
                                           "grant-budget", LDG.unitOfAccount),
    "a merge policy with no identity": ("research-grant", _no_identity("research-grant", "refused-when-exceeded"),
                                        "MeaningBearingEdgeShape", "grant-budget", LDG.mergePolicy),
    "a period recurrence with no identity": ("licence-seats", _no_identity("licence-seats", "licence-year"),
                                             "MeaningBearingEdgeShape", "seat-licence", LDG.periodRecurrence),
    "a kind that is not a published term": ("insurance-aggregate", _kind_not_published, "MeaningBearingEdgeShape", "annual-cap",
                                            LDG.restoredBy),
    "an edition with no identity": ("insurance-aggregate", _no_identity("insurance-aggregate", "credit-kinds-edition-1"),
                                    "MeaningBearingEdgeShape", "annual-cap", LDG.creditKindsEdition),
    "a residual account with no identity": ("whole-or-nothing", _no_identity("whole-or-nothing", "unallocated"),
                                            "MeaningBearingEdgeShape", "blocks-whole", LDG.residualAccount),
}


@pytest.mark.parametrize("case", FOUNDATION_MUTATIONS)
def test_foundation_reports_a_part_that_can_change_under_a_version(case: str) -> None:
    """Each mutation leaves a versioned thing, or what one of its edges that bear meaning leads to, open to an edit that would change
    what a past version meant. Foundation's shape reports it, a violation for a missing identity and a warning for an edge."""
    name, mutate, shape, focus, edge = FOUNDATION_MUTATIONS[case]
    g = MODEL + _example(name)
    mutate(g)
    found = {(s, f) for s, f, message in _foundation_findings(g) if edge is None or str(edge) in message}
    assert (shape, str(_ex(name)[focus])) in found, found


def test_the_corpus_is_versioned_as_foundation_asks() -> None:
    """The generated tree and pass give every definition an identity and a stated amount minted under it."""
    assert _foundation_findings(MODEL + account_tree(50, sections=4)) == set()
    assert _foundation_findings(MODEL + one_pass(20)) == set()


def test_a_definition_pins_at_most_one_edition() -> None:
    g = MODEL + _example("insurance-aggregate")
    ex = _ex("insurance-aggregate")
    g.add((ex["annual-cap"], LDG.creditKindsEdition, ex["credit-kinds-edition-2"]))
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert not conforms
    paths = {str(report.value(r, SH.resultPath)) for r in report.subjects(SH.resultSeverity, SH.Violation)
             if report.value(r, SH.sourceConstraintComponent) == SH.MaxCountConstraintComponent}
    assert paths == {str(LDG.creditKindsEdition)}


# ---- LG-29: a later version of a definition keeps the account's place, and a supersession brings it into force

SUPERSESSION = "supersession-raised-amount"


def _second_unit(g: Graph) -> None:
    """The aggregate's second version in a unit of account of another identity."""
    _supersession_graph(g, ("units-2", RDF.type, QNT.ValueSpace), ("units-2", FND.hasIdentity, "units-2-identity"),
                        ("units-2-identity", RDF.type, FND.PersistentIdentity))
    g.set((_ex(SUPERSESSION)["aggregate-2"], LDG.unitOfAccount, _ex(SUPERSESSION)["units-2"]))


def _unit_with_no_identity(g: Graph) -> None:
    """The aggregate's second version in a unit of account that has no identity, another node than the first version's."""
    _supersession_graph(g, ("units-3", RDF.type, QNT.ValueSpace))
    g.set((_ex(SUPERSESSION)["aggregate-2"], LDG.unitOfAccount, _ex(SUPERSESSION)["units-3"]))


def _recurrence_on_one_version(g: Graph) -> None:
    _period_recurrence_stated(g, "aggregate-2")


def _second_recurrence(g: Graph) -> None:
    """A recurrence on each version, of two identities."""
    _period_recurrence_stated(g, "aggregate-1")
    _supersession_graph(g, ("quarter", RDF.type, QNT.Recurrence), ("quarter", FND.hasIdentity, "quarter-identity"),
                        ("quarter-identity", RDF.type, FND.PersistentIdentity), ("aggregate-2", LDG.periodRecurrence, "quarter"))


def _key_dimension_on_one_version(g: Graph) -> None:
    _supersession_graph(g, ("sites", RDF.type, SKOS.ConceptScheme), ("section-2", LDG.keyDimension, "sites"))


def _other_key_dimension(g: Graph) -> None:
    _supersession_graph(g, ("sites", RDF.type, SKOS.ConceptScheme), ("regions", RDF.type, SKOS.ConceptScheme),
                        ("section-1", LDG.keyDimension, "sites"), ("section-2", LDG.keyDimension, "regions"))


def _purpose_on_one_version(g: Graph) -> None:
    _supersession_graph(g, ("flood", RDF.type, SKOS.Concept), ("aggregate-2", LDG.countsPurpose, "flood"))


def _other_purposes(g: Graph) -> None:
    """Each version counts a purpose the other does not."""
    _supersession_graph(g, ("flood", RDF.type, SKOS.Concept), ("wind", RDF.type, SKOS.Concept),
                        ("aggregate-1", LDG.countsPurpose, "flood"), ("aggregate-2", LDG.countsPurpose, "wind"))


def _parent_dropped(g: Graph) -> None:
    g.remove((_ex(SUPERSESSION)["section-2"], LDG.partOf, None))


def _parent_of_another_identity(g: Graph) -> None:
    """The section's second version part of a second aggregate of another identity."""
    ex = _ex(SUPERSESSION)
    _supersession_graph(g, ("aggregate-3", RDF.type, LDG.AccountDefinition), ("aggregate-3", FND.hasIdentity, "aggregate-3-identity"),
                        ("aggregate-3-identity", RDF.type, FND.PersistentIdentity), ("aggregate-3", LDG.unitOfAccount, "units"))
    g.set((ex["section-2"], LDG.partOf, ex["aggregate-3"]))


VERSION_CHANGES = {
    "the unit of account": _second_unit,
    "a unit of account with no identity": _unit_with_no_identity,
    "a period recurrence stated by one version only": _recurrence_on_one_version,
    "another period recurrence": _second_recurrence,
    "a key dimension stated by one version only": _key_dimension_on_one_version,
    "another key dimension": _other_key_dimension,
    "a purpose counted by one version only": _purpose_on_one_version,
    "other purposes counted": _other_purposes,
    "a parent dropped": _parent_dropped,
    "a parent of another identity": _parent_of_another_identity,
}


@pytest.mark.parametrize("case", VERSION_CHANGES)
def test_a_version_that_changes_the_accounts_place_is_refused(case: str) -> None:
    """Two versions of one identity that differ in the unit of account, the period recurrence, the key dimension, the purposes they
    count or the parent are reported, each version from its own side."""
    g = MODEL + _example(SUPERSESSION)
    VERSION_CHANGES[case](g)
    _, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    hit = {str(report.value(r, SH.value)) for r in report.subjects(SH.resultSeverity, SH.Violation)
           if str(report.value(r, SH.sourceShape)).endswith("#VersionsKeepTheAccountsPlaceShape")}
    assert len(hit) == 2 and hit <= {str(_ex(SUPERSESSION)[v]) for v in ("aggregate-1", "aggregate-2", "section-1", "section-2")}, hit


def _differences_that_are_allowed(g: Graph) -> None:
    """The aggregate's second version differs in what bounds or arbitrates later postings: its amount, a credit ceiling, the kinds that
    restore it with their edition, a merge policy of another identity, another kind of owner, and the admission of a stated amount
    below what is drawn."""
    ex = _ex(SUPERSESSION)
    _supersession_graph(
        g, ("aggregate-2/credit-ceiling", RDF.type, QNT.Quantity), ("aggregate-2/credit-ceiling", QNT.onSpace, "units"),
        ("aggregate-2/credit-ceiling", QNT.numericValue, _decimal("15")), ("aggregate-2", LDG.creditCeiling, "aggregate-2/credit-ceiling"),
        ("edition-1", RDF.type, SKOS.ConceptScheme), ("edition-1", FND.hasIdentity, "edition-identity"),
        ("edition-identity", RDF.type, FND.PersistentIdentity), ("recovery", RDF.type, SKOS.Concept),
        ("recovery", SKOS.inScheme, LDG.CreditKinds), ("recovery", SKOS.inScheme, "edition-1"),
        ("aggregate-2", LDG.restoredBy, "recovery"), ("aggregate-2", LDG.creditKindsEdition, "edition-1"),
        ("policy-2", RDF.type, LDG.MergePolicy), ("policy-2", FND.hasIdentity, "policy-2-identity"),
        ("policy-2-identity", RDF.type, FND.PersistentIdentity), ("policy-2", LDG.mergeRule, LDG.Refuse),
        ("aggregate-2", LDG.admitsOwnerKind, "Partner"), ("Partner", RDF.type, OWL.Class))
    g.set((ex["aggregate-2"], LDG.mergePolicy, ex["policy-2"]))
    g.set((ex["aggregate-2"], LDG.admitsStatedBelowDrawn, Literal(True)))


def test_versions_may_differ_in_what_bounds_or_arbitrates_later_postings() -> None:
    """The example's own versions differ in the stated amount, and a later version of the parent is no change of parent. Nothing the
    constraint does not read is reported when it also differs in a ceiling, its kinds, its merge policy, its owner kinds and its
    admission."""
    g = MODEL + _example(SUPERSESSION)
    _differences_that_are_allowed(g)
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)
    _agree(g, report)


def test_a_supersession_is_a_record_a_pass_writes() -> None:
    """The supersession of the example names its owner, its pass, its effective position and both later versions, which are of two
    identities, and the pass that writes only it is a pass with a record of a ledger at its revision."""
    g = _example(SUPERSESSION)
    ex = _ex(SUPERSESSION)
    record = ex["supersession-1"]
    assert set(g.objects(record, LDG.supersedingVersion)) == {ex["aggregate-2"], ex["section-2"]}
    assert {g.value(v, FND.hasIdentity) for v in g.objects(record, LDG.supersedingVersion)} == {
        ex["aggregate-identity"], ex["section-identity"]}
    assert (g.value(record, LDG.forOwner), g.value(record, LDG.effectivePosition)) == (ex.holder, _position(2))
    assert g.value(record, LDG.inPass) == _pass(SUPERSESSION, "supersession-2")
    assert [g.value(a, LDG.ofDefinition) for a in (ex["account-aggregate"], ex["account-section"])] == [ex["aggregate-1"], ex["section-1"]]
    assert list(g.subjects(LDG.inPass, _pass(SUPERSESSION, "supersession-2"))) == [record]
    assert g.value(record, LDG.periodKey) is None


def test_the_supersession_and_its_terms_are_declared() -> None:
    """`ldg:Supersession` is a derived artefact disjoint with the other runtime classes, with the restrictions of its terms, the three
    properties it shares have it in their domain, and the admission and the overdrawn value are functional with the ranges named."""
    assert (LDG.Supersession, RDFS.subClassOf, FND.DerivedArtefact) in MODEL
    restricted = {(MODEL.value(r, OWL.onProperty), MODEL.value(r, OWL.cardinality) or MODEL.value(r, OWL.minCardinality)
                   or MODEL.value(r, OWL.maxCardinality), (r, OWL.cardinality, None) in MODEL, (r, OWL.minCardinality, None) in MODEL)
                  for r in MODEL.objects(LDG.Supersession, RDFS.subClassOf) if isinstance(r, BNode)}
    assert restricted == {(LDG.forOwner, _position(1), True, False), (LDG.inPass, _position(1), True, False),
                          (LDG.effectivePosition, _position(1), True, False), (LDG.supersedingVersion, _position(1), False, True),
                          (LDG.periodKey, _position(1), False, False), (LDG.refusalReason, _position(1), False, False)}
    disjoint = {c for axiom in MODEL.subjects(RDF.type, OWL.AllDisjointClasses) for c in MODEL.items(MODEL.value(axiom, OWL.members))}
    assert LDG.Supersession in disjoint
    assert (MODEL.value(LDG.supersedingVersion, RDFS.domain), MODEL.value(LDG.supersedingVersion, RDFS.range)) == (
        LDG.Supersession, LDG.AccountDefinition)
    assert (LDG.supersedingVersion, RDF.type, OWL.FunctionalProperty) not in MODEL
    for prop in (LDG.forOwner, LDG.inPass, LDG.effectivePosition, LDG.periodKey, LDG.refusalReason):
        union = MODEL.value(prop, RDFS.domain)
        assert LDG.Supersession in set(MODEL.items(MODEL.value(union, OWL.unionOf))), prop
    for prop, domain in ((LDG.admitsStatedBelowDrawn, {LDG.AccountDefinition, LDG.LedgerProfile}), (LDG.overdrawnValue, {LDG.Posting})):
        union = MODEL.value(prop, RDFS.domain)
        found = set(MODEL.items(MODEL.value(union, OWL.unionOf))) if isinstance(union, BNode) else {union}
        assert found == domain, prop
        assert (prop, RDF.type, OWL.FunctionalProperty) in MODEL
    assert MODEL.value(LDG.admitsStatedBelowDrawn, RDFS.range) == XSD.boolean
    assert MODEL.value(LDG.overdrawnValue, RDFS.range) == XSD.decimal
    assert (LDG.admitsStatedBelowDrawn, FND.meaningBearing, None) not in MODEL
    for cls in (LDG.AccountDefinition, LDG.LedgerProfile, LDG.Posting):
        prop = LDG.overdrawnValue if cls == LDG.Posting else LDG.admitsStatedBelowDrawn
        assert any(MODEL.value(r, OWL.onProperty) == prop and (r, OWL.maxCardinality, None) in MODEL
                   for r in MODEL.objects(cls, RDFS.subClassOf) if isinstance(r, BNode)), (cls, prop)
    assert MODEL.value(LDG.StatedBelowDrawn, SKOS.inScheme) == LDG.RefusalReasons


@pytest.mark.parametrize("subject,prop", [("supersession-1", LDG.supersedingVersion), ("supersession-1", LDG.effectivePosition),
                                          ("supersession-1", LDG.forOwner), ("supersession-1", LDG.inPass)])
def test_a_supersession_missing_what_it_must_state_is_refused(subject: str, prop: URIRef) -> None:
    g = MODEL + _example(SUPERSESSION)
    g.remove((_ex(SUPERSESSION)[subject], prop, None))
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert not conforms
    paths = {str(report.value(r, SH.resultPath)) for r in report.subjects(SH.resultSeverity, SH.Violation)
             if report.value(r, SH.sourceConstraintComponent) == SH.MinCountConstraintComponent}
    assert paths == {str(prop)}


def test_a_supersession_states_a_period_key_where_its_versions_state_a_recurrence() -> None:
    """Both later versions state a yearly recurrence and the supersession states the bin of it its position falls in. The two
    supersession shapes find nothing, though the versions now differ from the first in a recurrence, which another constraint reports."""
    g = MODEL + _example(SUPERSESSION)
    _period_recurrence_stated(g, "aggregate-2", "section-2")
    _supersession_graph(g, ("year-2028", RDF.type, QNT.RecurrenceBin), ("year-2028", QNT.generatedByRecurrence, "year"),
                        ("supersession-1", LDG.periodKey, "year-2028"))
    _, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    found = {s.rsplit("#", 1)[-1] for s in _violating_shapes(report)}
    assert not {name for name in found if name.startswith("Supersession")}, found


# ---- LG-12: which draws an account accepts (LG-Q20 (a), ADR-A131's second addendum of 2026-11-09)
#
# A draw is a debit posting, and a request on a merge. Its amount is a literal in its account's unit of account, so what can
# arrive in another space or unit is a quantity named in its read set. Each refusal is by one new shape and no other.

SPACE, UNIT, REPRESENTABLE = LDG.DrawInItsAccountsSpaceShape, LDG.DrawInItsAccountsUnitShape, LDG.DrawRepresentableShape
REASONS = {SPACE: "qnt:OutsideDeclaredSpace", UNIT: "no permitted conversion", REPRESENTABLE: "qnt:OutsideDeclaredSpace"}


def _draws_refused(g: Graph) -> set[tuple[str, str]]:
    """(shape, record) of every violation in `g`, which must all be of the three draw shapes, each message giving the reason
    Quantification gives. Oxigraph finds the same."""
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    _agree(g, report)
    found = set()
    for r in report.subjects(SH.resultSeverity, SH.Violation):
        shape = report.value(r, SH.sourceShape)
        assert shape in REASONS, _violating_shapes(report)
        assert REASONS[shape] in str(report.value(r, SH.resultMessage))
        found.add((str(shape), str(report.value(r, SH.value))))
    assert conforms == (found == set())
    return found


def test_a_draw_in_another_unit_or_space_is_refused_and_a_converted_one_is_not() -> None:
    """The conformance case: the euros converted before the ledger conform, the euros taken as sterling and the dollars do not."""
    ex = _ex("refusal-incompatible-draw")
    assert _draws_refused(MODEL + _example("refusal-incompatible-draw")) == {
        (str(UNIT), str(ex["draw-2-posting"])), (str(SPACE), str(ex["draw-3-posting"]))}


def test_an_unrepresentable_draw_is_refused_with_its_request() -> None:
    """The conformance case: half of 10 licences, 5, conforms, and 33%, 3.3, is refused on its posting and its request."""
    ex = _ex("refusal-unrepresentable-amount")
    assert _draws_refused(MODEL + _example("refusal-unrepresentable-amount")) == {
        (str(REPRESENTABLE), str(ex["share-33-posting"])), (str(REPRESENTABLE), str(ex["share-33-request"]))}


def _reads(name: str, draw: str, quantity: str) -> Callable[[Graph], None]:
    def mutate(g: Graph) -> None:
        g.add((_ex(name)[draw], PROV.wasDerivedFrom, _ex(name)[quantity]))
    return mutate


def _reads_another_space(g: Graph) -> None:
    """The first drawing reads a count of seats, on a space that is not the facility's."""
    ex = _ex("revolving-facility")
    for p, o in [(RDF.type, QNT.ValueSpace), (QNT.densityKind, QNT.Discrete), (QNT.additivity, QNT.Extensive)]:
        g.add((ex.seats, p, o))
    for p, o in [(RDF.type, QNT.Quantity), (QNT.onSpace, ex.seats), (QNT.numericValue, _decimal("3"))]:
        g.add((ex["q-seats"], p, o))
    g.add((ex["draw-1-posting"], PROV.wasDerivedFrom, ex["q-seats"]))


def _space(name: str, space: str, prop: URIRef, value: URIRef | str) -> Callable[[Graph], None]:
    """States a datatype, or a granularity floor of `value` units, on an example's space."""
    def mutate(g: Graph) -> None:
        ex = _ex(name)
        stated = value
        if prop == QNT.granularityFloor:
            stated = ex[f"floor-{value}"]
            for p, o in [(RDF.type, QNT.Quantity), (QNT.onSpace, ex[space]), (QNT.numericValue, _decimal(str(value)))]:
                g.add((stated, p, o))
        g.set((ex[space], prop, stated))
    return mutate


def _share_resolved_to_three(g: Graph) -> None:
    """The 33% draw resolved to 3 licences, so the request, the posting and its balance say 3."""
    ex = _ex("refusal-unrepresentable-amount")
    g.set((ex["share-33-request"], LDG.requestedValue, _decimal("3")))
    g.set((ex["share-33-request"], LDG.grantedValue, _decimal("3")))
    g.set((ex["share-33-posting"], LDG.amountValue, _decimal("3")))
    g.set((ex["share-33-posting"], LDG.runningBalance, _decimal("2")))


def _floor_dropped_for_integers(g: Graph) -> None:
    """The pool's space is dense with no floor and its datatype is `xsd:integer`, so 3.3 is refused by the datatype alone. A discrete
    space with no floor is refused by its own constraint."""
    ex = _ex("refusal-unrepresentable-amount")
    g.remove((ex.licences, QNT.granularityFloor, None))
    g.set((ex.licences, QNT.densityKind, QNT.Dense))
    g.add((ex.licences, QNT.valueDatatype, XSD.integer))


def _amount_a_double(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["staff-spend-posting"], LDG.amountValue, Literal("90000", datatype=XSD.double)))


GRANT, SEATS = "research-grant", "licence-seats"
DRAWS = {
    "a draw that reads a quantity in its account's space and unit": (
        "revolving-facility", _reads("revolving-facility", "draw-1-posting", "facility/stated-amount"), None),
    "a draw that reads the euros it was asked for": (
        "revolving-facility", _reads("revolving-facility", "draw-1-posting", "q-draw-1-eur"), {(UNIT, "draw-1-posting")}),
    "a request that reads the euros it was asked for": (
        "revolving-facility", _reads("revolving-facility", "draw-1-request", "q-draw-1-eur"), {(UNIT, "draw-1-request")}),
    "a credit that reads the euros it was paid in": (
        "revolving-facility", _reads("revolving-facility", "repayment-posting", "q-repayment-eur"), None),
    "a draw that reads a quantity on another space": ("revolving-facility", _reads_another_space, {(SPACE, "draw-1-posting")}),
    "whole seats on a floor of 10": (SEATS, _space(SEATS, "seats", QNT.granularityFloor, 10), None),
    "seats that are not whole multiples of a floor of 50": (
        SEATS, _space(SEATS, "seats", QNT.granularityFloor, 50),
        {(REPRESENTABLE, r) for r in ("london-draw-posting", "london-draw-request", "porto-draw-posting", "porto-draw-request")}),
    "33% of 10 licences resolved to 3": ("refusal-unrepresentable-amount", _share_resolved_to_three, None),
    "3.3 licences on a space of integers": (
        "refusal-unrepresentable-amount", _floor_dropped_for_integers,
        {(REPRESENTABLE, "share-33-posting"), (REPRESENTABLE, "share-33-request")}),
    "amounts within xsd:int": (GRANT, _space(GRANT, "funds", QNT.valueDatatype, XSD.int), None),
    "amounts beyond xsd:short": (
        GRANT, _space(GRANT, "funds", QNT.valueDatatype, XSD.short),
        {(REPRESENTABLE, r) for r in ("staff-spend-posting", "staff-spend-request", "equipment-spend-posting",
                                      "equipment-spend-request")}),
    "a space whose datatype holds no decimal": (
        GRANT, _space(GRANT, "funds", QNT.valueDatatype, XSD.double),
        {(REPRESENTABLE, r) for r in ("staff-spend-posting", "staff-spend-request", "equipment-spend-posting",
                                      "equipment-spend-request")}),
    "a draw's amount stated as a double": (GRANT, _amount_a_double, {(REPRESENTABLE, "staff-spend-posting")}),
}


@pytest.mark.parametrize("case", DRAWS)
def test_an_account_accepts_a_draw_only_in_its_space_and_unit_and_representable(case: str) -> None:
    """A positive case where nothing is expected, and otherwise a mutation each of the three shapes alone refuses. A credit is not a
    draw, so one that reads euros is not refused here."""
    name, mutate, expected = DRAWS[case]
    g = MODEL + _example(name)
    mutate(g)
    assert _draws_refused(g) == {(str(shape), str(_ex(name)[record])) for shape, record in expected or set()}


# ---- LG2-10: a generated pass, 200 leaves here and 5,000 postings with 5,000 checkpoints in the benchmark

def test_runtime_shapes_scale() -> None:
    """The runtime shapes run on Oxigraph, but any of SLOW_ON_OXIGRAPH, and pySHACL runs those and the shapes of LG-1
    (`SCALE_SHAPES`) on a pass of 200 leaves. A broken record is then found on Oxigraph, so the empty result is not an empty query.
    The 5,000-leaf pass with its times recorded is `benchmark/ledger-posting-cost/test_shape_scale.py` (STD-155)."""
    g = MODEL + one_pass(200)
    store = _oxigraph_store(g)
    found = _on_oxigraph(store, skip=SLOW_ON_OXIGRAPH)
    conforms, report, _ = validate(g, shacl_graph=SCALE_SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)
    assert found == set()
    leaf = ox.NamedNode("https://example.org/lattice/ledger/runtime-scale/posting0")
    effective = ox.NamedNode(str(LDG.effectivePosition))
    for quad in list(store.quads_for_pattern(leaf, effective, None, None)):
        store.remove(quad)
    store.add(ox.Quad(leaf, effective, ox.Literal("2", datatype=ox.NamedNode(str(XSD.nonNegativeInteger))), ox.DefaultGraph()))
    assert _on_oxigraph(store, skip=SLOW_ON_OXIGRAPH) == {(str(LDG.NotForwardDatedShape), leaf.value)}


def test_oxigraph_finds_what_pyshacl_finds_at_scale() -> None:
    """200 leaves, clean and then with a running balance one unit off and a section's checkpoint one unit off. Every runtime shape
    finds the same records on Oxigraph and through pySHACL (STD-274)."""
    g = MODEL + one_pass(200)
    ex = Namespace("https://example.org/lattice/ledger/runtime-scale/")
    _, report, _ = validate(g, shacl_graph=RUNTIME_SHAPES, inference="none", advanced=True)
    assert _runtime_violations(report) == _on_oxigraph(_oxigraph_store(g)) == set()
    g.set((ex["posting3"], LDG.runningBalance, _decimal("8")))
    g.set((ex["checkpoint-section7"], LDG.balanceValue, _decimal("10")))
    _, report, _ = validate(g, shacl_graph=RUNTIME_SHAPES, inference="none", advanced=True)
    found = _runtime_violations(report)
    assert found == _on_oxigraph(_oxigraph_store(g))
    assert found == {(str(LDG.RunningBalanceShape), str(ex["posting3"])),
                     (str(LDG.CheckpointFoldShape), str(ex["checkpoint-section7"]))}


def test_the_sums_find_on_oxigraph_what_pyshacl_finds() -> None:
    """A running balance and a checkpoint each one minor unit off, and a credit with no cut where its ancestor had less room: pySHACL
    and Oxigraph each report the three sums that break, since no term of a sum is an error (TD-158)."""
    g = MODEL + _example("research-grant") + _example("credit-cut-at-parent")
    _running_balance_off(g)
    _checkpoint("110001")(g)
    _cut_missing(g)
    _, report, _ = validate(g, shacl_graph=RUNTIME_SHAPES, inference="none", advanced=True)
    found = _runtime_violations(report)
    assert found == _on_oxigraph(_oxigraph_store(g))
    research, cut = _ex("research-grant"), _ex("credit-cut-at-parent")
    assert found >= {(str(LDG.RunningBalanceShape), str(research["staff-spend-posting"])),
                     (str(LDG.CheckpointFoldShape), str(research["checkpoint-3"])),
                     (str(LDG.CutFillsTheAncestorShape), str(cut["credit-3-posting"]))}
