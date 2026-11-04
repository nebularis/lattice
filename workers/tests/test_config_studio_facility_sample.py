"""Tests for the Configuration Studio's facility agreement sample, which brings every configuration
part together over one baseline (ADR-A136). Each part is validated as the browser submits it, the
part under test with every other part beside it as context, through the worker's job logic and
without the live stack."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, SKOS

from lattice_workers import config_studio_jobs as jobs
from lattice_workers.config_studio_jobs import CST, SH
from test_config_studio_layers import contexts, rows
from test_config_studio_worker import CATALOGUE, ROOT, artefacts, results

SAMPLES = ROOT / CATALOGUE.area("contracts") / "config-studio" / "samples"
PARTS = ("vocabulary", "quantification", "eligibility", "persistence", "surface")
BASELINE_FILES = ("lending-baseline.ttl", "facility-baseline.ttl")
EX = Namespace("https://example.org/lending#")
NAMESPACES = {
    "persistence": "https://www.nebularis.org/neuro-semantic/lattice/persistence#",
    "surface": "https://www.nebularis.org/neuro-semantic/lattice/surface#",
    "eligibility": "https://www.nebularis.org/neuro-semantic/lattice/eligibility#",
    "quantification": "https://www.nebularis.org/neuro-semantic/lattice/quantification#",
    "vocabulary": "https://www.nebularis.org/neuro-semantic/lattice/vocabulary#",
}
JOB = URIRef("urn:lattice:studio:job:00000000-0000-0000-0000-0000000000f1")
SUBMITTED = "2026-10-27T10:00:00Z"


def load(*names: str) -> Graph:
    graph = Graph()
    for name in names:
        graph.parse(SAMPLES / name, format="turtle")
    return graph


def sample_part(part: str) -> Graph:
    return load(f"facility-{part}.ttl")


def run(kind: str, target: str) -> Graph:
    """The job a browser would submit: every part merged as the configuration."""
    config = Graph()
    for part in PARTS:
        config += sample_part(part)
    return jobs.run_job(JOB, kind, target, config, load(*BASELINE_FILES), ROOT, SUBMITTED)


def findings(g: Graph, severity: URIRef) -> list[tuple[str, str]]:
    return sorted((str(g.value(r, CST.code) or ""), str(g.value(r, SH.focusNode) or "")) for r in results(g, JOB, severity))


# --- the split rule of apps/config-studio/src/rdf/split.ts, ported -----------------------------------


def owners(graph: Graph) -> dict:
    """The part each named subject belongs to by the browser's split rule, and each blank node
    inherits the part of the subject that refers to it."""

    def uses(base: str, s):
        return any(str(p).startswith(base) or (p == RDF.type and str(o).startswith(base)) for p, o in graph.predicate_objects(s))

    def part_of(s) -> str:
        for part in ("persistence", "surface", "eligibility", "quantification"):
            if uses(NAMESPACES[part], s):
                return part
        voc = uses(NAMESPACES["vocabulary"], s) or any(
            p == SKOS.inScheme or (p == RDF.type and o in (SKOS.Concept, SKOS.ConceptScheme)) for p, o in graph.predicate_objects(s)
        )
        return "vocabulary" if voc else "baseline"

    named = {s for s in graph.subjects() if isinstance(s, URIRef)}
    owner = {s: part_of(s) for s in named}
    pending = list(named)
    while pending:
        s = pending.pop()
        for o in graph.objects(s, None):
            if not isinstance(o, URIRef) and not isinstance(o, Literal) and o not in owner:
                owner[o] = owner[s]
                pending.append(o)
    return owner


def test_every_triple_lands_in_the_part_its_file_is_named_for():
    # Each file is parsed once, since a blank node's identity differs between parses. The lending
    # baseline carries an outcome scheme, which the rule sends to vocabulary as in the lending
    # sample, so only the facility baseline is checked.
    files = {name: load(name) for name in ("facility-baseline.ttl", *(f"facility-{p}.ttl" for p in PARTS))}
    merged = Graph()
    for graph in files.values():
        merged += graph
    owner = owners(merged)
    for part in PARTS:
        assert {owner[s] for s in files[f"facility-{part}.ttl"].subjects()} == {part}, part
    assert {owner[s] for s in files["facility-baseline.ttl"].subjects()} == {"baseline"}


# --- vocabulary ------------------------------------------------------------------------------------


def test_the_resolution_table_shows_every_outcome():
    g = run("validate", "vocabulary")
    assert g.value(JOB, CST.conforms) == Literal(True)
    assert findings(g, SH.Violation) == []
    table = rows(g, JOB, CST.resolution)
    sector = [r for r in table if r["contract"] == "SectorContract"]
    region = [r for r in table if r["contract"] == "RegionContract"]
    assert len(sector) == 3 and len(region) == 2 * 4

    # The handover. Nothing is bound before 2026-01-01 and the contract has no fallback.
    by_edition = {(r.get("validFrom"), r.get("validTo")): r for r in sector}
    assert [r.get("scheme", r["outcome"]) for _, r in sorted(by_edition.items(), key=lambda kv: str(kv[0]))] == [
        "SectorScheme2026", "SectorScheme2027", "Unresolved",
    ]

    # Scope. A fallback, then a binding per scope, then two scopes that tie.
    after = {contexts(r): r for r in region if "validFrom" in r}
    assert after[frozenset()]["outcome"] == "Fallback" and after[frozenset()]["scheme"] == "RegionContinents"
    assert after[frozenset({"ScopeEmea"})]["scheme"] == "RegionEmea"
    assert after[frozenset({"ScopeAmericas"})]["scheme"] == "RegionAmericas"
    both = after[frozenset({"ScopeEmea", "ScopeAmericas"})]
    assert both["outcome"] == "Conflict" and both["tied"] == {"region-binding-emea", "region-binding-americas"}
    assert all(r["outcome"] == "Fallback" for r in region if "validTo" in r)

    outcomes = {r["outcome"] for r in table}
    assert outcomes == {"Resolved", "Fallback", "Unresolved", "Conflict"}


# --- quantification --------------------------------------------------------------------------------


def test_quantification_conforms():
    g = run("validate", "quantification")
    assert g.value(JOB, CST.conforms) == Literal(True)
    assert findings(g, SH.Violation) == [] and findings(g, SH.Warning) == []


# --- eligibility -----------------------------------------------------------------------------------

EXPECTED = {
    "q-sector-food-2026": "Permitted",
    "q-sector-gambling-2026": "Denied",
    "q-sector-gambling-2027": "Undetermined",
    "q-sector-renewables-2026": "Undetermined",
    "q-sector-renewables-2027": "Permitted",
    "q-sector-coal-2027": "Denied",
    "q-sector-energy-2027": "Undetermined",
    "q-region-germany-emea": "Permitted",
    "q-region-belarus-emea": "Denied",
    "q-region-canada-americas": "Undetermined",
    "q-region-us-americas": "Permitted",
    "q-amount-75m": "Permitted",
    "q-amount-400m": "Denied",
    "q-amount-60m-gbp": "Undetermined",
    "q-margin-3-25": "Permitted",
    "q-margin-8": "Denied",
    "q-margin-unpriced": "Undetermined",
}


def test_each_question_is_decided_as_expected():
    g = run("validate", "eligibility")
    assert g.value(JOB, CST.conforms) == Literal(True)
    assert findings(g, SH.Violation) == [] and findings(g, SH.Warning) == []
    tests = rows(g, JOB, CST.testResult)
    assert {t["question"]: t["decision"] for t in tests} == EXPECTED
    assert all(t["passed"] == "true" for t in tests)
    # EXPECTED covers every outcome, a time before the handover and a scope.
    assert set(EXPECTED.values()) == {"Permitted", "Denied", "Undetermined"}
    diagnostics = {t["question"]: t["diagnostic"] for t in tests if "diagnostic" in t}
    assert diagnostics["q-amount-60m-gbp"] == "NoBoundInUnit"
    assert diagnostics["q-region-canada-americas"] == "NoHierarchy"
    assert diagnostics["q-sector-gambling-2027"] == "OutsideScheme"
    assert diagnostics["q-sector-energy-2027"] == "AboveExclusion"
    assert diagnostics["q-margin-unpriced"] == "MissingCandidate"


def test_the_sector_condition_expands_over_the_edition_in_force_at_its_resolution_time():
    g = run("validate", "eligibility")
    expansion = {r["concept"]: r["decision"] for r in rows(g, JOB, CST.expansion) if r["condition"] == "FacilityAdmission-Sector"}
    assert expansion == {
        "Industrials": "Permitted", "Manufacturing": "Permitted", "FoodProcessing": "Permitted", "Textiles": "Permitted",
        "Consumer": "Permitted", "Retail": "Permitted", "Energy": "Undetermined", "Coal": "Denied", "Renewables": "Permitted",
    }
    emea = {r["concept"]: r["decision"] for r in rows(g, JOB, CST.expansion) if r["condition"] == "FacilityAdmission-Region"}
    assert emea == {
        "Emea": "Denied", "Europe": "Undetermined", "Germany": "Permitted", "UnitedKingdom": "Permitted",
        "Belarus": "Denied", "MiddleEast": "Denied",
    }


def test_a_wrong_expectation_fails_the_job(tmp_path: Path):
    config = Graph()
    for part in PARTS:
        config += sample_part(part)
    cst = URIRef(str(CST) + "expectedDecision")
    config.set((EX["q-margin-8"], cst, URIRef("https://www.nebularis.org/neuro-semantic/lattice/eligibility#Permitted")))
    g = jobs.run_job(JOB, "validate", "eligibility", config, load(*BASELINE_FILES), ROOT, SUBMITTED)
    assert g.value(JOB, CST.conforms) == Literal(False)
    assert findings(g, SH.Violation) == [("TestFailed", str(EX["q-margin-8"]))]


def test_eligibility_compiles_a_query_and_shapes_per_condition_and_profile():
    g = run("compile", "eligibility")
    assert g.value(JOB, CST.conforms) == Literal(True)
    files = artefacts(g, JOB)
    for group in ("FacilityAdmission-Sector", "FacilityAdmission-Region", "FacilityAdmission-Amount", "FacilityAdmission-Margin", "FacilityAdmission"):
        assert f"{group}/decision.rq" in files and f"{group}/shapes.ttl" in files, group


# --- persistence -----------------------------------------------------------------------------------


def test_persistence_validates_and_compiles_both_aggregates():
    g = run("validate", "persistence")
    assert g.value(JOB, CST.conforms) == Literal(True)
    assert findings(g, SH.Violation) == [] and findings(g, SH.Warning) == []
    g = run("compile", "persistence")
    assert g.value(JOB, CST.conforms) == Literal(True)
    assert findings(g, SH.Warning) == []
    files = artefacts(g, JOB)
    groups = {group for _, _, group in files.values()}
    assert {"profile", "Facility", "Borrower"} <= groups
    assert "Borrower/key-claim-write_borrower-tax-identifier-unique.rq" in files
    assert "Facility/key-claim-write_facility-reference-per-branch.rq" in files
    # The composite boundary generates the payload check, the named-graph boundary does not.
    assert "Facility/payload-check.rq" in files and "Borrower/payload-check.rq" not in files
    profile = Graph().parse(data=files["compiled-profile.ttl"][1], format="turtle")
    assert (None, None, None) in profile


def test_personal_data_without_an_erasure_path_is_refused():
    config = Graph()
    for part in PARTS:
        config += sample_part(part)
    dal = Namespace(NAMESPACES["persistence"])
    config.set((EX.BorrowerPrivacy, dal.erasureStrategy, dal.NoErasure))
    config.remove((EX.BorrowerPrivacy, dal.erasurePrecedence, None))
    g = jobs.run_job(JOB, "validate", "persistence", config, load(*BASELINE_FILES), ROOT, SUBMITTED)
    assert g.value(JOB, CST.conforms) == Literal(False)
    assert findings(g, SH.Violation)


# --- surface ---------------------------------------------------------------------------------------


def test_surface_validates_and_compiles_both_contracts():
    g = run("validate", "surface")
    assert g.value(JOB, CST.conforms) == Literal(True)
    assert findings(g, SH.Violation) == []
    g = run("compile", "surface")
    assert g.value(JOB, CST.conforms) == Literal(True)
    assert findings(g, SH.Violation) == [] and findings(g, SH.Warning) == []
    files = artefacts(g, JOB)
    assert {group for _, _, group in files.values()} == {"drawdown-sector", "borrower-sector"}
    promotion = Graph().parse(data=files["drawdown-sector/assertions.ttl"][1], format="turtle")
    exec_ns = Namespace("https://example.org/lending/exec#")
    # Both drawdowns are drawn under a facility whose borrower works in food processing.
    assert {(s, o) for s, _, o in promotion.triples((None, exec_ns.drawdownSector, None))} == {
        (EX["drawdown-1"], EX.FoodProcessing), (EX["drawdown-2"], EX.FoodProcessing),
    }
    # The index population is the edition of the sector scheme in force at the compile time.
    core = files["borrower-sector/core.ttl"][1]
    assert "Gambling" in core and "Renewables" not in core
