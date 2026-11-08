# SPDX-License-Identifier: MPL-2.0

"""Ledger LG-1 and LG-2: the configuration document and the runtime document (ADR-A131). Row IDs are
the plan's LG-1 and LG-2 "in detail" tables. Validates LG-0's examples, configuration and runtime
records, against the structural shapes, the six SHACL-SPARQL constraints and the runtime laws,
checks the import guard holds, the spec names no term of Party, Eligibility, Wording, Instrument
or Behaviour, the generated cycle shape finishes on a larger generated tree, each runtime law
refuses a record that breaks it, and the runtime shapes finish on a generated pass. LG2-01 is the
owl:rational probe on rdflib, Oxigraph and Jena (TSD-70)."""

from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Callable
from decimal import Decimal
from functools import cache
from pathlib import Path

import pyoxigraph as ox
import pytest
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
    # what the scale test leaves to pySHACL: the shapes of LG-1, and the three runtime shapes that do not run on Oxigraph
    module.SCALE_SHAPES = graph_cache(LEDGER / "shapes" / "structural.ttl", LEDGER / "shapes" / "constraints.ttl",
                                      _only(_runtime_shapes(), LDG.AvailableIsLeastAlongPathShape, LDG.BalanceFoldShape,
                                            LDG.CheckpointFoldShape))
    module.validate = validated


ACCEPTED = ["licence-seats", "revolving-facility", "research-grant", "authority-aggregate", "insurance-aggregate"]
REFUSALS = {
    "refusal-cycle": "NoCycleThroughPartOfShape",
    "refusal-unit": "ChildUnitMatchesParentShape",
    "refusal-proportional-unrounded": "ProportionalNeedsRoundingShape",
    "refusal-intensive-unit": "ExtensiveUnitOfAccountShape",
}


def _example(name: str) -> Graph:
    return _graph(LEDGER / "examples" / f"{name}.ttl")


def _violating_shapes(report: Graph) -> set[str]:
    return {str(report.value(r, SH.sourceShape)) for r in report.subjects(SH.resultSeverity, SH.Violation)}


# ---- the runtime shapes as plain SELECTs on Oxigraph (CAP-64) ------------------
#
# Each runtime shape targets its class (`sh:targetNode ldg:BalanceRecord`) and reads every instance in one query, so pySHACL
# runs it once, with `$this` the class. The SHACL-SPARQL specification defines that run as the query with `$this` replaced by
# the class, so it also runs as a plain SELECT on any engine once `$this` is out of the projection and the grouping, the only
# places it is not a term. A row is a violation and its `?value` the record. Oxigraph and pySHACL on rdflib are different
# engines (STD-176, STD-274), so every case below that runs through pySHACL also holds Oxigraph to what it finds (`_agree`), and
# `test_oxigraph_finds_what_pyshacl_finds_at_scale` does so on a generated pass.

# Two kinds of shape stay with pySHACL on rdflib (STD-274 keeps the default where a result differs, STD-176 where a cost does).
#
# DIVERGES_ON_OXIGRAPH. These two sum `?signed`, which is unbound for a subject on the account that is not a posting (a balance
# record, a checkpoint) because `?posting ldg:onAccount/ldg:partOfAccount* ?account` matches any record. Under SPARQL 1.1 §18.5.1
# `SUM` over an error is an error, so Oxigraph leaves `?moved` unbound, the final `FILTER` errors, and the shape finds nothing,
# where rdflib skips the row (TSD-41, TSD-43, RDF-30 rule R9). On Oxigraph they are false negatives, so they are not run there
# (`test_the_fold_shapes_find_nothing_on_oxigraph`).
#
# SLOW_ON_OXIGRAPH. On the 10,000-record pass this query takes 38.7 s on Oxigraph 0.5.13 and 4.7 s through pySHACL on rdflib,
# where the thirteen others take 0.5 s together. A cost measured on one engine is a hypothesis for the other.
DIVERGES_ON_OXIGRAPH = frozenset({str(LDG.BalanceFoldShape), str(LDG.CheckpointFoldShape)})
SLOW_ON_OXIGRAPH = frozenset({str(LDG.AvailableIsLeastAlongPathShape)})


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


def _on_oxigraph(store: ox.Store, skip: frozenset[str] = DIVERGES_ON_OXIGRAPH) -> set[tuple[str, str]]:
    """(shape, record) of every violation of the runtime shapes in a store, except the shapes in `skip`."""
    return {(shape, row["value"].value) for shape, query in _runtime_selects() if shape not in skip for row in store.query(query)}


def _runtime_violations(report: Graph, skip: frozenset[str] = DIVERGES_ON_OXIGRAPH) -> set[tuple[str, str]]:
    """(shape, record) of every violation of the runtime shapes in a pySHACL report, except the shapes in `skip`."""
    runtime = {shape for shape, _ in _runtime_selects()} - skip
    found = {(str(report.value(r, SH.sourceShape)), str(report.value(r, SH.value)))
             for r in report.subjects(SH.resultSeverity, SH.Violation)}
    return {pair for pair in found if pair[0] in runtime}


def _agree(g: Graph, report: Graph) -> None:
    """The runtime shapes, but the two of DIVERGES_ON_OXIGRAPH, find on Oxigraph what pySHACL reported for `g` (STD-274)."""
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


# ---- LG1-09: the cycle shape finishes on a larger generated tree, time recorded

def _cycle_scale_graph() -> Graph:
    """10,000 account definitions in a shallow, wide tree (a root, 99 sections each part of
    it, the rest sublimits spread across the sections), the shape real account trees actually
    have (an aggregate, its sections, their sublimits), never a single 10,000-deep chain, which
    is both unrealistic and recurses past rdflib's property-path evaluator's Python call depth."""
    g = Graph()
    g += MODEL
    prefixes = f"@prefix ldg: <{LDG}> .\n@prefix qnt: <{QNT}> .\n@prefix ex: <https://example.org/lattice/ledger/scale/> .\n"
    lines = ["ex:space a qnt:ValueSpace ; qnt:spaceKey \"scale\" ; qnt:orderKind qnt:TotalOrder ; "
             "qnt:densityKind qnt:Discrete ; qnt:spaceHash \"scale-v1\" ; qnt:additivity qnt:Extensive ; "
             "qnt:hasOperationCapability ex:sum , ex:diff .",
             "ex:sum a qnt:OperationCapability ; qnt:operationKind qnt:Sum ; qnt:resultSpace ex:space .",
             "ex:diff a qnt:OperationCapability ; qnt:operationKind qnt:Difference ; qnt:resultSpace ex:space .",
             "ex:amount a qnt:Quantity ; qnt:onSpace ex:space ; qnt:numericValue \"100\"^^<http://www.w3.org/2001/XMLSchema#decimal> .",
             "ex:root a ldg:AccountDefinition ; ldg:statedAmount ex:amount ; ldg:unitOfAccount ex:space ; "
             "ldg:admitsOwnerKind qnt:ValueSpace ; ldg:mergeRule ldg:Refuse ."]
    sections = 99
    for s in range(sections):
        lines.append(f"ex:section{s} a ldg:AccountDefinition ; ldg:statedAmount ex:amount ; "
                      f"ldg:unitOfAccount ex:space ; ldg:admitsOwnerKind qnt:ValueSpace ; "
                      f"ldg:mergeRule ldg:Refuse ; ldg:partOf ex:root .")
    for i in range(10_000 - 1 - sections):
        section = i % sections
        lines.append(f"ex:sublimit{i} a ldg:AccountDefinition ; ldg:statedAmount ex:amount ; "
                      f"ldg:unitOfAccount ex:space ; ldg:admitsOwnerKind qnt:ValueSpace ; "
                      f"ldg:mergeRule ldg:Refuse ; ldg:partOf ex:section{section} .")
    g += _graph(prefixes + "\n".join(lines))
    return g


def test_cycle_shape_scales(record_property) -> None:
    """The cycle shape alone, on rdflib through pySHACL: the property path it walks is what recurses past rdflib's call depth. The
    other shapes meet the same 10,000 definitions in LG2-10."""
    g = _cycle_scale_graph()
    started = time.monotonic()
    conforms, report, _ = validate(g, shacl_graph=CYCLE_SHAPE, inference="none", advanced=True)
    elapsed = time.monotonic() - started
    record_property("cycle_shape_10000_seconds", elapsed)
    assert conforms


# ==== LG-2: the runtime document ===============================================

OWL_RATIONAL = "http://www.w3.org/2002/07/owl#rational"


def _ex(name: str) -> Namespace:
    return Namespace(f"https://example.org/lattice/ledger/{name}/")


def _decimal(value: str) -> Literal:
    return Literal(Decimal(value), datatype=XSD.decimal)


def _integer(value: int) -> Literal:
    return Literal(value, datatype=XSD.integer)


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

def _fold_short(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["grant-balance-2"], LDG.remainingValue, _decimal("60001")))


def _available_above_ancestor(g: Graph) -> None:
    ex = _ex("research-grant")
    posting = ex["direct-posting"]
    for p, o in [(RDF.type, LDG.Posting), (LDG.onAccount, ex["account-grant-budget"]), (LDG.inPass, ex["pass-1"]),
                 (LDG.effectivePosition, _integer(1)), (LDG.recordedPosition, _integer(1)),
                 (LDG.microPosition, _integer(0)), (LDG.direction, LDG.Debit), (LDG.amountValue, _decimal("100000"))]:
        g.add((posting, p, o))
    g.set((ex["grant-balance-1"], LDG.remainingValue, _decimal("10000")))
    g.set((ex["grant-balance-1"], LDG.availableValue, _decimal("10000")))


def _credit_above_ceiling(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["equipment-return-posting"], LDG.amountValue, _decimal("55000")))
    g.set((ex["equipment-balance-3"], LDG.remainingValue, _decimal("85000")))
    g.set((ex["equipment-balance-3"], LDG.availableValue, _decimal("85000")))


def _proportional_one_short(g: Graph) -> None:
    ex = _ex("authority-aggregate")
    g.set((ex["grant-1"], LDG.grantedValue, _decimal("33")))
    g.set((ex["posting-1"], LDG.amountValue, _decimal("33")))


def _owner_kind_not_admitted(g: Graph) -> None:
    ex = _ex("research-grant")
    g.remove((ex.institution, RDF.type, ex.Grantee))


def _posting_key_shared(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["equipment-return-posting"], LDG.recordedPosition, _integer(1)))


def _forward_dated(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["equipment-return-posting"], LDG.effectivePosition, _integer(4)))


def _recorded_against_passes(g: Graph) -> None:
    ex = _ex("research-grant")
    g.set((ex["equipment-spend-posting"], LDG.recordedPosition, _integer(2)))
    g.set((ex["equipment-return-posting"], LDG.recordedPosition, _integer(1)))


def _merge_not_cited(g: Graph) -> None:
    ex = _ex("research-grant")
    g.remove((ex["staff-spend-posting"], PROV.wasDerivedFrom, ex["staff-spend-merge"]))


def _conversion_alone(g: Graph) -> None:
    ex = _ex("revolving-facility")
    g.remove((ex["draw-1-posting"], LDG.conversionUsed, None))


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


def _checkpoint(balance: str) -> Callable[[Graph], None]:
    def mutate(g: Graph) -> None:
        ex = _ex("research-grant")
        checkpoint = ex["grant-checkpoint-3"]
        for p, o in [(RDF.type, LDG.Checkpoint), (LDG.onAccount, ex["account-grant-budget"]),
                     (LDG.closePosition, _integer(3)), (LDG.balanceValue, _decimal(balance))]:
            g.add((checkpoint, p, o))
    return mutate


MUTATIONS = {
    "LG2-03 a balance record one minor unit off": ("research-grant", _fold_short, "BalanceFoldShape"),
    "LG2-04 an available value above an ancestor's remaining": (
        "research-grant", _available_above_ancestor, "AvailableIsLeastAlongPathShape"),
    "LG2-05 a credit above the ceiling": ("research-grant", _credit_above_ceiling, "CreditCeilingShape"),
    "LG2-06 a proportional merge one unit short": (
        "authority-aggregate", _proportional_one_short, "MergeWithinAvailabilityShape"),
    "LG2-08 an owner of a kind not admitted": ("research-grant", _owner_kind_not_admitted, "OwnerKindAdmittedShape"),
    "LG2-09 two postings with one natural key": ("research-grant", _posting_key_shared, "PostingNaturalKeyShape"),
    "a forward-dated posting (STD-294)": ("research-grant", _forward_dated, "NotForwardDatedShape"),
    "a recorded order against the passes": ("research-grant", _recorded_against_passes, "RecordedOrderFollowsPassesShape"),
    "a merged posting not citing its merge": ("research-grant", _merge_not_cited, "MergedPostingCitesMergeShape"),
    "a conversion stated alone": ("revolving-facility", _conversion_alone, "ConversionTogetherShape"),
    "a periodic account with no period key": ("licence-seats", _period_key_missing, "PeriodKeyFromRecurrenceShape"),
    "an instance not part of its parent's": (
        "research-grant", _parent_instance_missing, "PartOfAccountFollowsDefinitionShape"),
    "two accounts with one natural key": ("research-grant", _account_key_shared, "AccountNaturalKeyShape"),
    "a refused merge holding a grant": ("refusal-overdraw", _refused_with_grant, "RefusedMergeShape"),
    "a grant above its request": ("research-grant", _grant_above_request, "GrantWithinRequestShape"),
    "a checkpoint one minor unit off": ("research-grant", _checkpoint("110001"), "CheckpointFoldShape"),
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


def test_a_checkpoint_at_the_fold_conforms() -> None:
    g = MODEL + _example("research-grant")
    _checkpoint("110000")(g)
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)
    _agree(g, report)


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


# ---- LG2-10: a generated pass of 5,000 postings and 10,000 balance records ------

def _runtime_scale_graph(leaves: int = 5_000) -> Graph:
    """One pass over a root, `leaves - 1` sections and `leaves` leaves (4,999 and 5,000 by default), each leaf its own
    definition, as the cycle test's tree has. Each leaf takes one debit of 1, and every account moved has a balance record:
    5,000 leaves, 4,999 sections and the root, 10,000 in all."""
    sections = leaves - 1
    lines = [f"@prefix ldg: <{LDG}> .", f"@prefix qnt: <{QNT}> .", f"@prefix xsd: <{XSD}> .",
             "@prefix ex: <https://example.org/lattice/ledger/runtime-scale/> .",
             "ex:space a qnt:ValueSpace ; qnt:spaceKey \"runtime-scale\" ; qnt:orderKind qnt:TotalOrder ; "
             "qnt:densityKind qnt:Discrete ; qnt:spaceHash \"runtime-scale-v1\" ; qnt:additivity qnt:Extensive ; "
             "qnt:hasOperationCapability ex:sum , ex:diff .",
             "ex:sum a qnt:OperationCapability ; qnt:operationKind qnt:Sum ; qnt:resultSpace ex:space .",
             "ex:diff a qnt:OperationCapability ; qnt:operationKind qnt:Difference ; qnt:resultSpace ex:space .",
             "ex:big a qnt:Quantity ; qnt:onSpace ex:space ; qnt:numericValue \"10000\"^^xsd:decimal .",
             "ex:small a qnt:Quantity ; qnt:onSpace ex:space ; qnt:numericValue \"10\"^^xsd:decimal .",
             "ex:Owner a <http://www.w3.org/2002/07/owl#Class> . ex:owner a ex:Owner .",
             "ex:pass a ldg:Pass ; ldg:passPosition \"1\"^^xsd:integer .",
             "ex:root a ldg:AccountDefinition ; ldg:statedAmount ex:big ; ldg:unitOfAccount ex:space ; "
             "ldg:admitsOwnerKind ex:Owner ; ldg:mergeRule ldg:Refuse .",
             "ex:account-root a ldg:Account ; ldg:ofDefinition ex:root ; ldg:forOwner ex:owner .",
             f"ex:balance-root a ldg:BalanceRecord ; ldg:onAccount ex:account-root ; ldg:inPass ex:pass ; "
             f"ldg:remainingValue \"{10_000 - leaves}\"^^xsd:decimal ; ldg:availableValue \"{10_000 - leaves}\"^^xsd:decimal ."]
    drawn = {}
    for i in range(leaves):
        drawn[i % sections] = drawn.get(i % sections, 0) + 1
    for s in range(sections):
        remaining = 10 - drawn[s]
        lines += [f"ex:section{s} a ldg:AccountDefinition ; ldg:statedAmount ex:small ; ldg:unitOfAccount ex:space ; "
                  f"ldg:admitsOwnerKind ex:Owner ; ldg:mergeRule ldg:Refuse ; ldg:partOf ex:root .",
                  f"ex:account-section{s} a ldg:Account ; ldg:ofDefinition ex:section{s} ; ldg:forOwner ex:owner ; "
                  f"ldg:partOfAccount ex:account-root .",
                  f"ex:balance-section{s} a ldg:BalanceRecord ; ldg:onAccount ex:account-section{s} ; ldg:inPass ex:pass ; "
                  f"ldg:remainingValue \"{remaining}\"^^xsd:decimal ; ldg:availableValue \"{remaining}\"^^xsd:decimal ."]
    for i in range(leaves):
        lines += [f"ex:leaf{i} a ldg:AccountDefinition ; ldg:statedAmount ex:small ; ldg:unitOfAccount ex:space ; "
                  f"ldg:admitsOwnerKind ex:Owner ; ldg:mergeRule ldg:Refuse ; ldg:partOf ex:section{i % sections} .",
                  f"ex:account-leaf{i} a ldg:Account ; ldg:ofDefinition ex:leaf{i} ; ldg:forOwner ex:owner ; "
                  f"ldg:partOfAccount ex:account-section{i % sections} .",
                  f"ex:posting{i} a ldg:Posting ; ldg:onAccount ex:account-leaf{i} ; ldg:inPass ex:pass ; "
                  f"ldg:effectivePosition \"1\"^^xsd:integer ; ldg:recordedPosition \"1\"^^xsd:integer ; "
                  f"ldg:microPosition \"0\"^^xsd:integer ; ldg:direction ldg:Debit ; ldg:amountValue \"1\"^^xsd:decimal .",
                  f"ex:balance-leaf{i} a ldg:BalanceRecord ; ldg:onAccount ex:account-leaf{i} ; ldg:inPass ex:pass ; "
                  f"ldg:remainingValue \"9\"^^xsd:decimal ; ldg:availableValue \"{min(9, 10 - drawn[i % sections])}\"^^xsd:decimal ."]
    g = MODEL + _graph("\n".join(lines))
    assert len(list(g.subjects(RDF.type, LDG.Posting))) == leaves
    assert len(list(g.subjects(RDF.type, LDG.BalanceRecord))) == 2 * leaves
    return g


def test_runtime_shapes_scale(record_property) -> None:
    """Thirteen of the sixteen runtime shapes run on Oxigraph, and pySHACL runs the rest and the shapes of LG-1 (`SCALE_SHAPES`),
    as the engines differ in result (`DIVERGES_ON_OXIGRAPH`) and in cost (`SLOW_ON_OXIGRAPH`). A broken record is then found on
    Oxigraph, so the empty result is not an empty query."""
    g = _runtime_scale_graph()
    started = time.monotonic()
    store = _oxigraph_store(g)
    found = _on_oxigraph(store, skip=SLOW_ON_OXIGRAPH | DIVERGES_ON_OXIGRAPH)
    oxigraph_elapsed = time.monotonic() - started
    started = time.monotonic()
    conforms, report, _ = validate(g, shacl_graph=SCALE_SHAPES, inference="none", advanced=True)
    pyshacl_elapsed = time.monotonic() - started
    record_property("runtime_shapes_5000_postings_10000_balances_oxigraph_seconds", oxigraph_elapsed)
    record_property("runtime_shapes_5000_postings_10000_balances_pyshacl_seconds", pyshacl_elapsed)
    assert conforms, _violating_shapes(report)
    assert found == set()
    leaf = ox.NamedNode("https://example.org/lattice/ledger/runtime-scale/posting0")
    amount = ox.NamedNode(str(LDG.effectivePosition))
    for quad in list(store.quads_for_pattern(leaf, amount, None, None)):
        store.remove(quad)
    store.add(ox.Quad(leaf, amount, ox.Literal("2", datatype=ox.NamedNode(str(XSD.integer))), ox.DefaultGraph()))
    assert _on_oxigraph(store, skip=SLOW_ON_OXIGRAPH | DIVERGES_ON_OXIGRAPH) == {(str(LDG.NotForwardDatedShape), leaf.value)}


def test_oxigraph_finds_what_pyshacl_finds_at_scale() -> None:
    """200 leaves, clean and then with a balance one unit off and an available value above its own remaining one. The runtime shapes but
    the two of DIVERGES_ON_OXIGRAPH, the slow one among them, find the same records on Oxigraph and through pySHACL (STD-274)."""
    g = _runtime_scale_graph(200)
    ex = Namespace("https://example.org/lattice/ledger/runtime-scale/")
    _, report, _ = validate(g, shacl_graph=RUNTIME_SHAPES, inference="none", advanced=True)
    assert _runtime_violations(report) == _on_oxigraph(_oxigraph_store(g)) == set()
    g.set((ex["balance-leaf3"], LDG.remainingValue, _decimal("8")))
    g.set((ex["balance-section7"], LDG.availableValue, _decimal("11")))
    _, report, _ = validate(g, shacl_graph=RUNTIME_SHAPES, inference="none", advanced=True)
    found = _runtime_violations(report)
    assert found == _on_oxigraph(_oxigraph_store(g))
    assert {shape for shape, _ in found} == {str(LDG.AvailableIsLeastAlongPathShape)}


def test_the_fold_shapes_find_nothing_on_oxigraph() -> None:
    """LG2-03's record and a checkpoint, each one minor unit off: pySHACL reports BalanceFoldShape and CheckpointFoldShape, and
    Oxigraph reports neither (TSD-41, RDF-30 rule R9). When the two shapes stop summing an expression that can error, this fails,
    and DIVERGES_ON_OXIGRAPH is emptied."""
    g = MODEL + _example("research-grant")
    _fold_short(g)
    _checkpoint("110001")(g)
    _, report, _ = validate(g, shacl_graph=RUNTIME_SHAPES, inference="none", advanced=True)
    assert _runtime_violations(report, skip=frozenset()) >= {
        (str(LDG.BalanceFoldShape), str(_ex("research-grant")["grant-balance-2"])),
        (str(LDG.CheckpointFoldShape), str(_ex("research-grant")["grant-checkpoint-3"]))}
    assert {shape for shape, _ in _on_oxigraph(_oxigraph_store(g), skip=frozenset())}.isdisjoint(DIVERGES_ON_OXIGRAPH)
