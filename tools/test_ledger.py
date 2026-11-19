# SPDX-License-Identifier: MPL-2.0

"""Ledger LG-1, LG-2 and LG-25: the configuration document and the runtime document (ADR-A131). Row IDs are the plan's LG-1
and LG-2 "in detail" tables and LG-25's Validation Pack. Validates LG-0's examples, configuration and runtime records, against
the structural shapes, the SHACL-SPARQL constraints and the runtime laws, checks the import guard holds, the spec names no term
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
from rdflib.namespace import PROV, SH

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology"
LEDGER = ONTOLOGY / "ledger"
LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
LDG = Namespace(LATTICE + "ledger#")
QNT = Namespace(LATTICE + "quantification#")

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
    # what the scale test leaves to pySHACL: the shapes of LG-1, and the runtime shapes too slow on Oxigraph
    module.SCALE_SHAPES = graph_cache(LEDGER / "shapes" / "structural.ttl", LEDGER / "shapes" / "constraints.ttl",
                                      _only(_runtime_shapes(), *(URIRef(s) for s in sorted(SLOW_ON_OXIGRAPH))))
    module.validate = validated


ACCEPTED = ["licence-seats", "revolving-facility", "research-grant", "authority-aggregate", "insurance-aggregate",
            "credit-cut-at-parent"]
REFUSALS = {
    "refusal-cycle": "NoCycleThroughPartOfShape",
    "refusal-unit": "ChildUnitMatchesParentShape",
    "refusal-proportional-unrounded": "ProportionalNeedsRoundingShape",
    "refusal-intensive-unit": "ExtensiveUnitOfAccountShape",
    "refusal-nearest-beside-residual": "NearestRoundingStatesTheDifferenceShape",
    "refusal-settled-without-excess": "SettledToNearestStatesTheExcessShape",
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


def _integer(value: int) -> Literal:
    return Literal(value, datatype=XSD.integer)


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
    g.set((ex["grant-1"], LDG.grantedValue, _decimal("33")))
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


def _refused_with_grant(g: Graph) -> None:
    ex = _ex("refusal-overdraw")
    grant = ex["grant-1"]
    for p, o in [(RDF.type, LDG.Grant), (LDG.forProposal, ex["proposal-1"]),
                 (LDG.requestedValue, _decimal("60")), (LDG.grantedValue, _decimal("60"))]:
        g.add((grant, p, o))
    g.add((ex["merge-1"], LDG.grant, grant))


def _grant_above_request(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["staff-spend-grant"], LDG.requestedValue, _decimal("80000")))


def _checkpoint(balance: str, name: str = "research-grant", account: str = "account-grant-budget",
                close: int = 3) -> Callable[[Graph], None]:
    def mutate(g: Graph) -> None:
        ex = _ex(name)
        checkpoint = ex[f"checkpoint-{close}"]
        for p, o in [(RDF.type, LDG.Checkpoint), (LDG.onAccount, ex[account]),
                     (LDG.closePosition, _integer(close)), (LDG.balanceValue, _decimal(balance))]:
            g.add((checkpoint, p, o))
    return mutate


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
    "a refused merge holding a grant": ("refusal-overdraw", _refused_with_grant, "RefusedMergeShape"),
    "a grant above its request": ("research-grant", _grant_above_request, "GrantWithinRequestShape"),
    "a checkpoint one minor unit off": ("research-grant", _checkpoint("110001"), "CheckpointFoldShape"),
    "a checkpoint that leaves out the cut": (
        "credit-cut-at-parent", _checkpoint("13", "credit-cut-at-parent", "account-parent"), "CheckpointFoldShape"),
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
    ("credit-cut-at-parent", _checkpoint("10", "credit-cut-at-parent", "account-parent")),
], ids=["the grant after the return", "the parent less its cut"])
def test_a_checkpoint_at_the_sum_conforms(name: str, mutate: Callable[[Graph], None]) -> None:
    g = MODEL + _example(name)
    mutate(g)
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)
    _agree(g, report)


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


# ---- LG2-07: the refusal under ldg:Refuse conforms, with no posting and a reason

def test_refused_merge_conforms_with_no_posting_and_a_reason() -> None:
    g = MODEL + _example("refusal-overdraw")
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)
    _agree(g, report)
    ex = _ex("refusal-overdraw")
    assert list(g.subjects(RDF.type, LDG.Posting)) == []
    assert g.value(ex["merge-1"], LDG.refusalReason) == ex.overdrawn
    assert g.value(ex["merge-1"], LDG.grant) is None


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
