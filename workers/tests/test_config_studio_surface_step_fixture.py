"""The expectation of the surface simulator's tests (the run worker's `SurfaceStepTest`), written by the surface compiler and kept equal to it.

The simulator runs the writer's maintenance in Jena over a sample world, and the compiler is what says what its rows and read sets should be.
This test reads each facility surface step of `contracts/config-studio/samples/facility-surface-step-*.trig`, applies its edit to its world, and
gives for each promotion the rows the compiler's own rebuild gives for the world after, which compiles the contract over the declarations and
the merged world, each row kept in the source that types its carrier, and the contracts the compiler's invalidation names for the edit, by
comparing the read set recorded for the world before with the digests the world after gives (`surface.invalidation.compare_read_set`). The
sources are the graphs the edit changes and those it reaches, which are the others whose rows it changes. It also keeps the operations the
facility's surface compile job holds, which the run worker's tests read in place of a compiler.

    LATTICE_WRITE_SURFACE_STEP_FIXTURE=1 mise exec -- python -m pytest workers/tests/test_config_studio_surface_step_fixture.py -q

Without the switch the checked-in files must equal what the compiler gives now, so a change to the compiler, the sample or the worker fails
here until they are written again."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import unquote

import pytest
from rdflib import BNode, Dataset, Graph, URIRef
from rdflib.namespace import RDF, RDFS, SKOS
from surface.compile import SurfaceCompiler, compile_contract
from surface.invalidation import compare_read_set, instance_graph_query, read_set_key
from surface.model import read_contracts

from lattice_workers import config_studio_jobs as jobs
from test_config_studio_facility_sample import BASELINE_FILES, EX, JOB, PARTS, ROOT, SAMPLES, SUBMITTED, load, sample_part
from test_config_studio_worker import artefacts

RESOURCES = ROOT / "platform" / "config-studio-transforms" / "src" / "test" / "resources"
JOB_FIXTURE = RESOURCES / "surface-job"
EXPECTED = RESOURCES / "surface-steps" / "expected.json"
WRITE = os.environ.get("LATTICE_WRITE_SURFACE_STEP_FIXTURE") == "1"

STEP = "urn:lattice:studio:step"
PROMOTED = "urn:lattice:studio:promoted:"
STEPS = sorted(p.name for p in SAMPLES.glob("facility-surface-step-*.trig"))
INSTANCE_CLASSES = {EX.Branch, EX.Borrower, EX.Lender, EX.Facility, EX.Drawdown}


@pytest.fixture(scope="module")
def surface_job() -> dict[str, tuple[str, str, str]]:
    config = Graph()
    for part in PARTS:
        config += sample_part(part)
    return artefacts(jobs.run_job(JOB, "compile", "surface", config, load(*BASELINE_FILES), ROOT, SUBMITTED), JOB)


@pytest.fixture(scope="module")
def declarations() -> Graph:
    return sample_part("surface")


@pytest.fixture(scope="module")
def base() -> Graph:
    """What the compile job reads beside the world: the configuration, the baseline without its carrier data, and the substrate's vocabulary."""
    config = Graph()
    for part in PARTS:
        config += sample_part(part)
    baseline = load(*BASELINE_FILES)
    data = {s for s in baseline.subjects(RDF.type, None) if any(o in INSTANCE_CLASSES for o in baseline.objects(s, RDF.type))}
    for subject in data:
        baseline.remove((subject, None, None))
    return jobs._merge(config, baseline, jobs._spec(str(ROOT), "vocabulary"))


def read_step(name: str) -> tuple[dict[str, Graph], dict[str, Graph], dict[str, Graph]]:
    """The world before, and the quads added and removed, each by graph. A reserved graph is read as the contract says."""
    dataset = Dataset()
    dataset.parse(SAMPLES / name, format="trig")
    world: dict[str, Graph] = {}
    added: dict[str, Graph] = {}
    removed: dict[str, Graph] = {}
    for graph in dataset.graphs():
        identifier = str(graph.identifier)
        if not len(graph) or identifier == STEP:
            continue
        side, target = world, identifier
        for prefix, kept in ((STEP + "/added/", added), (STEP + "/removed/", removed)):
            if identifier.startswith(prefix):
                side, target = kept, unquote(identifier[len(prefix):])
        side.setdefault(target, Graph())
        side[target] += graph
    return world, added, removed


def apply(world: dict[str, Graph], added: dict[str, Graph], removed: dict[str, Graph]) -> dict[str, Graph]:
    out = {name: Graph() + graph for name, graph in world.items()}
    for name, graph in removed.items():
        for triple in graph:
            out.setdefault(name, Graph()).remove(triple)
    for name, graph in added.items():
        target = out.setdefault(name, Graph())
        for triple in graph:
            target.add(triple)
    return out


def union(world: dict[str, Graph]) -> Graph:
    merged = Graph()
    for graph in world.values():
        merged += graph
    return merged


def lines(rows: set, partition: str) -> list[str]:
    return sorted(f"{s.n3()} {p.n3()} {o.n3()} <{partition}> ." for s, p, o in rows)


def rebuilt(contract, declarations: Graph, world: Graph) -> set:
    """The rows of the compiler's own rebuild: the contract compiled over the declarations and the merged world."""
    assertions = compile_contract(contract, declarations + world, SUBMITTED).modules["assertions"]
    return {t for t in assertions.triples((None, contract.promotes_to, None)) if not isinstance(t[0], BNode) and not isinstance(t[2], BNode)}


def rows_by_source(contract, declarations: Graph, world: dict[str, Graph]) -> dict[str, set]:
    """The rows of the rebuild over the merged world, each in the source that types its carrier by the contract's carrier or a class below it."""
    merged = union(world)
    rows = rebuilt(contract, declarations, merged)
    below = {contract.carrier} | {c for c in set(merged.subjects(RDFS.subClassOf, None)) if contract.carrier in set(merged.transitive_objects(c, RDFS.subClassOf))}
    return {name: {row for row in rows if any((row[0], RDF.type, k) in graph for k in below)} for name, graph in world.items()}


def expectation(name: str, declarations: Graph, base: Graph) -> dict:
    world, added, removed = read_step(name)
    after = apply(world, added, removed)
    edited = sorted({*added, *removed} - {"urn:x-rdflib:default"}, key=lambda s: s.encode())
    contracts = read_contracts(declarations)
    kept = sorted((c for c in contracts if not c.is_index and c.emits_assertions), key=lambda c: c.key)
    before_rows = {c.key: rows_by_source(c, declarations, world) for c in kept}
    after_rows = {c.key: rows_by_source(c, declarations, {**{n: Graph() for n in world}, **after}) for c in kept}
    names = {*world, *after}
    # the sources the edit reaches are the others whose rows it changes
    reached = sorted((n for n in names - set(edited) if any(before_rows[c.key].get(n, set()) != after_rows[c.key].get(n, set()) for c in kept)), key=lambda s: s.encode())
    sources = sorted({*edited, *reached}, key=lambda s: s.encode())
    out: dict = {"sources": edited, "reached": reached, "contracts": {}}
    for contract in kept:
        entry = {"before": [], "after": [], "asserted": [], "retracted": []}
        for source in sources:
            partition = PROMOTED + source
            was, now = before_rows[contract.key].get(source, set()), after_rows[contract.key].get(source, set())
            entry["before"] += lines(was, partition)
            entry["after"] += lines(now, partition)
            entry["asserted"] += lines(now - was, partition)
            entry["retracted"] += lines(was - now, partition)
        out["contracts"][contract.key] = {k: sorted(v) for k, v in entry.items()}
    # the contracts the compiler's invalidation names: the read set recorded for the world before against the digests the world after gives
    touched = []
    for contract in sorted(contracts, key=lambda c: c.key):
        recorded = SurfaceCompiler(contract, base + union(world), SUBMITTED).compile().read_set
        current = {read_set_key(e.kind, e.source): e.digest for e in SurfaceCompiler(contract, base + union(after), SUBMITTED).compile().read_set}
        if not compare_read_set(recorded, current).fresh:
            touched.append(contract.key)
    out["touched"] = touched
    return out


@pytest.mark.parametrize("name", STEPS)
def test_the_facility_samples_read_across_graphs_so_a_fill_that_read_one_source_would_miss_rows(name, declarations):
    """The borrowers sit in graphs of their own, as the facility profile places them, so the rows of the facilities source hold a sector that a
    rebuild of that source alone does not reach. A step that kept the source's rows from its own graph would not give the compiler's rows."""
    world, added, removed = read_step(name)
    after = apply(world, added, removed)
    contract = next(c for c in read_contracts(declarations) if c.key == "drawdown-sector")
    differs = False
    for state in (world, after):
        merged_rows = rows_by_source(contract, declarations, state)["urn:g:facilities"]
        differs = differs or merged_rows != rebuilt(contract, declarations, state["urn:g:facilities"])
    assert differs, name


@pytest.mark.parametrize("name", STEPS)
def test_the_vocabulary_graph_of_a_step_holds_its_concepts_as_the_configuration_states_them(name, base):
    """The compiler reads the triples of the value a read path ends at from the vocabulary, and a step reads only its own world. So a step's
    world holds those concepts, and holds them as the sample does, or the simulator and the compiler would read different graphs."""
    world, _, _ = read_step(name)
    vocabulary = world["urn:g:vocabulary"]
    assert len(vocabulary)
    for concept in set(vocabulary.subjects(RDF.type, SKOS.Concept)):
        assert set(vocabulary.triples((concept, None, None))) == set(base.triples((concept, None, None))), concept


def test_the_steps_are_the_eight_the_tests_name():
    assert STEPS == [f"facility-surface-step-{n}.trig" for n in ("borrower", "drawdown", "first", "projection", "repay", "sector", "subtype", "vocabulary")]


def test_the_invalidation_names_the_contract_for_the_first_instance_of_its_carrier(declarations, base):
    """A contract records its instance graph whether or not the source holds an instance of its carrier, with the empty graph's digest where it
    holds none, so the first drawdown asserts a row and names the contract, as the same edit made to a world that has a drawdown does."""
    expected = {name: expectation(name, declarations, base) for name in STEPS}
    first = expected["facility-surface-step-first.trig"]
    assert first["contracts"]["drawdown-sector"]["asserted"] and first["touched"] == ["drawdown-sector"]
    assert expected["facility-surface-step-drawdown.trig"]["touched"] == ["drawdown-sector"]
    assert expected["facility-surface-step-repay.trig"]["touched"] == ["drawdown-sector"], "a contract whose instances all went is stale, as its digest is now the empty graph's"
    sector = expected["facility-surface-step-sector.trig"]
    assert sector["touched"] == ["borrower-sector", "drawdown-sector"], "the index reads the borrower, and the promotion the sector's triples at the path's end"


def test_the_instance_graph_query_names_the_contracts_the_invalidation_names(declarations, base):
    """The query the job holds, run over the world before and after, gives the compiler's answer for each step, an empty result being the entry of a class with no instance."""
    for name in STEPS:
        world, added, removed = read_step(name)
        after = apply(world, added, removed)
        names = []
        for contract in sorted(read_contracts(declarations), key=lambda c: c.key):
            query = instance_graph_query(contract)
            recorded = {tuple(t) for t in (base + union(world)).query(query)}
            now = {tuple(t) for t in (base + union(after)).query(query)}
            if recorded != now:
                names.append(contract.key)
        assert names == expectation(name, declarations, base)["touched"], name


def test_the_job_holds_the_writers_operations_and_a_manifest_that_names_them(surface_job):
    media, manifest, group = surface_job["maintenance/manifest.json"]
    assert (media, group) == ("application/json", "maintenance")
    entries = json.loads(manifest)
    assert [e["key"] for e in entries] == ["borrower-sector", "drawdown-sector"]
    assert "fill" not in entries[0] and "reason" in entries[0] and entries[0]["readSet"] == "borrower-sector-read-set.rq"
    assert entries[1]["fill"] == "drawdown-sector-fill-all.rq" and entries[1]["readSet"] == "drawdown-sector-read-set.rq"
    for path in ("maintenance/partition-clear.rq", "maintenance/drawdown-sector-fill-all.rq", "maintenance/drawdown-sector-read-set.rq"):
        assert surface_job[path][2] == "maintenance"
    assert {group for _, _, group in surface_job.values()} == {"drawdown-sector", "borrower-sector", "maintenance", "projections"}


def test_the_run_workers_fixtures_are_what_the_compiler_gives(surface_job, declarations, base):
    """Written with `LATTICE_WRITE_SURFACE_STEP_FIXTURE=1`. Without it the checked-in files must equal what the compiler gives now."""
    wanted = {path: text for path, (_, text, group) in surface_job.items() if group == "maintenance"}
    expected = json.dumps({name: expectation(name, declarations, base) for name in STEPS}, indent=2, sort_keys=True) + "\n"
    if WRITE:
        for path, text in wanted.items():
            target = JOB_FIXTURE / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
        EXPECTED.parent.mkdir(parents=True, exist_ok=True)
        EXPECTED.write_text(expected, encoding="utf-8", newline="\n")
    kept = {p.relative_to(JOB_FIXTURE).as_posix(): p.read_text(encoding="utf-8") for p in JOB_FIXTURE.rglob("*") if p.is_file()}
    assert kept == wanted
    assert EXPECTED.read_text(encoding="utf-8") == expected
