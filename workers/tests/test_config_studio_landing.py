"""Tests for the landing places of a persistence compile job (SVA-P1): where each target's data lands, read by the worker from
the compiled profile and the compiler's own code, and written as `landing-places.json`, valid against
contracts/config-studio/landing-places.schema.json. The browser draws only this file, so its fixture is written here."""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from rdflib import Graph, Namespace
from rdflib.namespace import RDFS

from lattice_workers import config_studio_jobs as jobs
from lattice_workers import config_studio_landing as landing
from lattice_workers.config_studio_jobs import SH
from test_config_studio_facility_sample import BASELINE_FILES, EX, JOB, NAMESPACES, PARTS, ROOT, SUBMITTED, findings, load, sample_part
from test_config_studio_worker import CATALOGUE, PERSISTENCE_EXAMPLES, artefacts

CONTRACT = ROOT / CATALOGUE.area("contracts") / "config-studio"
SCHEMA = Draft202012Validator(json.loads((CONTRACT / "landing-places.schema.json").read_text(encoding="utf-8")))
FIXTURE = ROOT / "apps" / "config-studio" / "e2e" / "fixtures" / "landing-places-facility.json"
DAL = Namespace(NAMESPACES["persistence"])
FND = Namespace("https://www.nebularis.org/neuro-semantic/lattice/foundation#")


def facility_config() -> Graph:
    config = Graph()
    for part in PARTS:
        config += sample_part(part)
    return config


def compile_landing(config: Graph, baseline: Graph) -> tuple[dict, dict]:
    """The job's landing places, parsed, and every artefact of it, after checking the file against the schema."""
    g = jobs.run_job(JOB, "compile", "persistence", config, baseline, ROOT, SUBMITTED)
    files = artefacts(g, JOB)
    media, text, group = files[landing.LANDING_PLACES]
    assert (media, group) == ("application/json", "profile")
    document = json.loads(text)
    assert [e.message for e in SCHEMA.iter_errors(document)] == []
    return document, files


@pytest.fixture(scope="module")
def facility() -> tuple[dict, dict]:
    return compile_landing(facility_config(), load(*BASELINE_FILES))


def target(document: dict, name: str) -> dict:
    return next(t for t in document["targets"] if t["id"] == name)


def places(t: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for place in t["places"]:
        out.setdefault(place["kind"], []).append(place)
    return out


# --- the facility sample -----------------------------------------------------------------------------------------------------


def test_the_facility_sample_gives_each_target_its_places(facility):
    document, _ = facility
    assert [t["id"] for t in document["targets"]] == ["Borrower", "Facility"]
    graphs = {t["id"]: {(p["kind"], p["graph"]) for p in t["places"]} for t in document["targets"]}
    assert graphs["Facility"] == {
        ("data-graph", "urn:g:facilities"),
        ("version-row", "urn:g:meta/6"),
        ("receipt", "urn:g:txlog/{year and month of the write, as YYYY-MM}"),
        ("transaction-claim", "urn:g:txn"),
        ("patch-log-add", "{newRev}/add"),
        ("patch-log-del", "{newRev}/del"),
        ("key-claim", "urn:g:keys"),
    }
    assert graphs["Borrower"] == {
        ("data-graph", "urn:g:borrower/{root, percent-encoded}"),
        ("version-row", "urn:g:meta/52"),
        ("receipt", "urn:g:txlog/{year and month of the write, as YYYY-MM}"),
        ("transaction-claim", "urn:g:txn"),
        ("key-claim", "urn:g:keys"),
    }


def test_a_graph_is_the_one_the_operations_bindings_give(facility):
    """The graph of a place is the binding of the operations that write it, never a pattern read from an IRI."""
    document, files = facility
    for t in document["targets"]:
        text = {o["operation"]: files[o["path"]][1] for o in t["operations"]}
        for place in t["places"]:
            for operation in place["operations"]:
                if "{" not in place["graph"]:
                    assert f"<{place['graph']}>" in text[operation], (t["id"], place["kind"], operation)
    borrower = target(document, "Borrower")
    assert 'CONCAT("urn:g:borrower/", ENCODE_FOR_URI(STR($root)), "")' in files["Borrower/create-if-absent.rq"][1]
    assert places(borrower)["data-graph"][0]["graph"] == "urn:g:borrower/{root, percent-encoded}"


def test_each_place_names_the_operations_that_write_it_and_each_has_its_sparql(facility):
    document, files = facility
    for t in document["targets"]:
        by_name = {o["operation"]: o for o in t["operations"]}
        for o in t["operations"]:
            assert o["path"] in files, o
        for place in t["places"]:
            assert place["from"] and place["operations"]
            assert place["from"] == sorted({by_name[n]["templateId"] for n in place["operations"]})
    facility_target = target(document, "Facility")
    kinds = places(facility_target)
    # Only an operation that inserts or deletes in a graph writes it. A read, such as an audit's, does not.
    assert not any(o.startswith(("gap-scan", "fork-detection", "revision-multi", "txn-multi", "payload-check")) for p in facility_target["places"] for o in p["operations"])
    assert kinds["patch-log-add"][0]["operations"] == ["cas-replace", "create-if-absent", "replace-whole"]
    assert kinds["patch-log-del"][0]["operations"] == ["cas-replace", "replace-whole", "tombstone-delete"]


def test_the_profiles_and_scopes_a_target_resolved_from(facility):
    document, _ = facility
    assert target(document, "Facility")["profiles"] == [
        str(EX.FacilityBoundaryProfile), str(EX.FacilityConcurrencyProfile), str(EX.FacilityEpoch), str(EX.FacilityReceiptProfile),
    ]
    assert target(document, "Facility")["scopes"] == [str(EX.FacilityClass)]
    assert target(document, "Facility")["matchedScopes"] == [str(EX.FacilityClass)]
    assert target(document, "Borrower")["profiles"] == [str(EX.BorrowerAccessProfile), str(EX.BorrowerEpoch), str(EX.BorrowerIdentity), str(EX.BorrowerPrivacy)]
    assert target(document, "Borrower")["scopes"] == [str(EX.BorrowerEntity)]


def test_the_boundary_nests_as_the_shape_does(facility):
    document, _ = facility
    aggregate = target(document, "Facility")["aggregate"]
    assert (aggregate["strategy"], aggregate["rootClass"], aggregate["rootShape"]) == ("CompositePropertyBoundary", str(EX.Facility), str(EX.FacilityShape))
    assert [(e["property"], e["class"], e["shape"]) for e in aggregate["owned"]] == [(str(EX.hasDrawdown), str(EX.Drawdown), str(EX.DrawdownShape))]
    assert [(r["property"], r["class"], r["mode"]) for r in aggregate["references"]] == [
        (str(EX.arrangedBy), str(EX.Branch), "ByIdentity"), (str(EX.borrower), str(EX.Borrower), "ByIdentity"), (str(EX.lender), str(EX.Lender), "ByIdentity"),
    ]
    named = target(document, "Borrower")["aggregate"]
    assert (named["strategy"], named["rootShape"], named["owned"], named["references"]) == ("NamedGraphBoundary", None, [], [])


def test_a_boundary_nests_below_the_first_owned_edge():
    baseline = load(*BASELINE_FILES)
    baseline.add((EX.DrawdownShape, SH.property, EX.DrawdownFeeEdge))
    baseline.add((EX.DrawdownFeeEdge, SH.path, EX.hasFee))
    baseline.add((EX.DrawdownFeeEdge, SH.node, EX.FeeShape))
    baseline.add((EX.DrawdownFeeEdge, DAL.ownership, DAL.Owned))
    baseline.add((EX.FeeShape, SH.targetClass, EX.Fee))
    baseline.add((EX.DrawdownShape, SH.property, EX.DrawdownLenderEdge))
    baseline.add((EX.DrawdownLenderEdge, SH.path, EX.fundedBy))
    baseline.add((EX.DrawdownLenderEdge, DAL.ownership, DAL.Reference))
    baseline.add((EX.DrawdownLenderEdge, SH["class"], EX.Lender))
    document, _ = compile_landing(facility_config(), baseline)
    (drawdown,) = target(document, "Facility")["aggregate"]["owned"]
    assert [(e["property"], e["shape"]) for e in drawdown["owned"]] == [(str(EX.hasFee), str(EX.FeeShape))]
    assert [(r["property"], r["class"]) for r in drawdown["references"]] == [(str(EX.fundedBy), str(EX.Lender))]


# --- a patch log, a key claim and a reference mode -----------------------------------------------------------------------------------


def test_a_target_under_a_patch_log_has_its_places_and_one_without_has_neither(facility):
    document, _ = facility
    assert {"patch-log-add", "patch-log-del"} <= set(places(target(document, "Facility")))
    assert not {"patch-log-add", "patch-log-del"} & set(places(target(document, "Borrower")))
    # The same holds across the examples: a receipt-only family writes no patch log.
    refused_without = Graph().parse(PERSISTENCE_EXAMPLES / "privacy-receipt-compatible.ttl")
    document, _ = compile_landing(refused_without, Graph())
    assert {"patch-log-add", "patch-log-del"} <= {p["kind"] for t in document["targets"] for p in t["places"]}


def test_a_uniqueness_constraint_gives_a_key_claim_for_each_constraint(facility):
    document, _ = facility
    (claim,) = places(target(document, "Facility"))["key-claim"]
    assert claim["graph"] == "urn:g:keys" and "facility-reference-per-branch" in claim["label"]
    assert claim["from"] == ["key-claim-retire", "key-claim-write"]
    assert claim["operations"] == ["key-claim-retire:facility-reference-per-branch", "key-claim-write:facility-reference-per-branch"]
    config = facility_config()
    config.remove((EX.FacilityReferencePerBranch, None, None))
    document, _ = compile_landing(config, load(*BASELINE_FILES))
    assert "key-claim" not in places(target(document, "Facility"))
    assert "key-claim" in places(target(document, "Borrower"))


def test_a_referenced_edge_is_pinned_or_by_identity_as_configured():
    baseline = load(*BASELINE_FILES)
    baseline.add((EX.Lender, RDFS.subClassOf, FND.Versioned))
    for shape in baseline.subjects(SH.path, EX.lender):
        baseline.add((shape, DAL.referenceMode, DAL.Pinned))
    document, _ = compile_landing(facility_config(), baseline)
    modes = {r["property"]: r["mode"] for r in target(document, "Facility")["aggregate"]["references"]}
    assert modes == {str(EX.arrangedBy): "ByIdentity", str(EX.borrower): "ByIdentity", str(EX.lender): "Pinned"}


# --- every kind of place, over the persistence examples --------------------------------------------------------------------------


def test_every_example_gives_a_document_valid_against_the_schema_and_the_kinds_the_operations_name():
    kinds: set[str] = set()
    for path in sorted(PERSISTENCE_EXAMPLES.glob("*.ttl")):
        g = jobs.run_job(JOB, "compile", "persistence", Graph().parse(path), Graph(), ROOT, SUBMITTED)
        files = artefacts(g, JOB)
        if landing.LANDING_PLACES not in files:
            assert findings(g, SH.Violation), path.name  # a refusal gives no artefact at all
            continue
        document = json.loads(files[landing.LANDING_PLACES][1])
        assert [e.message for e in SCHEMA.iter_errors(document)] == [], path.name
        assert all(o["path"] in files for t in document["targets"] for o in t["operations"]), path.name
        kinds |= {p["kind"] for t in document["targets"] for p in t["places"]}
    assert {"data-graph", "version", "events", "version-row", "receipt", "transaction-claim", "patch-log-add", "patch-log-del", "key-claim", "merge-record", "key-quarantine"} <= kinds
    assert kinds <= set(landing.KINDS)


def test_a_class_deployed_twice_has_a_target_for_each_deployment():
    document, _ = compile_landing(Graph().parse(PERSISTENCE_EXAMPLES / "lending-credit-shared-class.ttl"), Graph())
    deployed = [t for t in document["targets"] if t["deployment"] is not None]
    assert len(deployed) == 2 and all(t["id"].count(".") == 1 for t in deployed)
    assert len({t["id"] for t in document["targets"]}) == len(document["targets"])


# --- determinism ---------------------------------------------------------------------------------------------------------------------


def shuffled(graph: Graph, seed: int) -> Graph:
    triples = sorted(graph)
    random.Random(seed).shuffle(triples)
    out = Graph()
    for triple in triples:
        out.add(triple)
    return out


def test_the_same_configuration_in_any_order_of_triples_gives_the_same_json(facility):
    _, files = facility
    expected = files[landing.LANDING_PLACES][1]
    for seed in (1, 2, 3):
        _, again = compile_landing(shuffled(facility_config(), seed), shuffled(load(*BASELINE_FILES), seed + 10))
        assert again[landing.LANDING_PLACES][1] == expected, seed
    _, repeat = compile_landing(facility_config(), load(*BASELINE_FILES))
    assert repeat[landing.LANDING_PLACES][1] == expected


# --- the fixture the browser tests draw ---------------------------------------------------------------------------------------------


def test_the_browser_fixture_is_the_facility_sample_as_the_worker_gives_it(facility):
    """Written with `LATTICE_WRITE_LANDING_FIXTURE=1`. Without it the checked-in file must equal what the worker gives now."""
    _, files = facility
    text = files[landing.LANDING_PLACES][1]
    if os.environ.get("LATTICE_WRITE_LANDING_FIXTURE") == "1":
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(text, encoding="utf-8", newline="\n")
    assert FIXTURE.read_text(encoding="utf-8") == text


def test_a_refused_compilation_gives_no_landing_places():
    config = facility_config()
    config.set((EX.BorrowerPrivacy, DAL.erasureStrategy, DAL.NoErasure))
    config.remove((EX.BorrowerPrivacy, DAL.erasurePrecedence, None))
    g = jobs.run_job(JOB, "compile", "persistence", config, load(*BASELINE_FILES), ROOT, SUBMITTED)
    assert landing.LANDING_PLACES not in artefacts(g, JOB)
