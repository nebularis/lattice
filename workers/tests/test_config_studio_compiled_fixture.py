"""The browser fixtures of the persistence canvas (SVA-P1b). The canvas draws the `compiled-profile.ttl` artefact of a persistence compile
job, so its fake service serves the facility sample's compiled profile, and its unit tests read it. This test keeps the fixture equal to
what the compiler gives for the sample, so a change to the compiler, the sample or the worker fails here until the fixture is written again.

    LATTICE_WRITE_COMPILED_FIXTURE=1 mise exec -- python -m pytest workers/tests/test_config_studio_compiled_fixture.py -q

Beside the profile it keeps the path of every artefact the same job holds, which the browser's rule for an operation's path is tested
against. It also keeps the `projections` group and the findings of the facility sample's surface compilation (SVA-S1), which the surface canvas
reads the lowered schemes from."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.namespace import RDF

from lattice_workers import config_studio_jobs as jobs
from lattice_workers.config_studio_jobs import CST, SH
from test_config_studio_facility_sample import BASELINE_FILES, JOB, NAMESPACES, PARTS, ROOT, SUBMITTED, load, sample_part
from test_config_studio_worker import artefacts, results

FIXTURES = ROOT / "apps" / "config-studio" / "e2e" / "fixtures"
PROFILE = FIXTURES / "compiled-profile-facility.ttl"
PATHS = FIXTURES / "compiled-profile-facility.paths.txt"
SURFACE = FIXTURES / "compiled-surface-facility.json"
WRITE = os.environ.get("LATTICE_WRITE_COMPILED_FIXTURE") == "1"


@pytest.fixture(scope="module")
def facility() -> dict[str, tuple[str, str, str]]:
    config = Graph()
    for part in PARTS:
        config += sample_part(part)
    return artefacts(jobs.run_job(JOB, "compile", "persistence", config, load(*BASELINE_FILES), ROOT, SUBMITTED), JOB)


def test_the_job_gives_the_compiled_profile_and_no_landing_places(facility):
    media, _, group = facility["compiled-profile.ttl"]
    assert (media, group) == ("text/turtle", "profile")
    assert "landing-places.json" not in facility


def test_the_compiled_profile_states_the_places_of_both_targets(facility):
    profile = Graph().parse(data=facility["compiled-profile.ttl"][1], format="turtle")
    dal = NAMESPACES["persistence"]
    places = {str(s) for s in profile.subjects(RDF.type, profile.resource(dal + "GraphPlace").identifier)}
    assert sum("/Facility/" in p for p in places) == 7 and sum("/Borrower/" in p for p in places) == 5


def test_the_browser_fixture_is_the_facility_sample_as_the_compiler_gives_it(facility):
    """Written with `LATTICE_WRITE_COMPILED_FIXTURE=1`. Without it the checked-in files must equal what the job gives now."""
    profile = facility["compiled-profile.ttl"][1]
    paths = "".join(f"{path}\n" for path in sorted(facility))
    if WRITE:
        PROFILE.parent.mkdir(parents=True, exist_ok=True)
        PROFILE.write_text(profile, encoding="utf-8", newline="\n")
        PATHS.write_text(paths, encoding="utf-8", newline="\n")
    assert PROFILE.read_text(encoding="utf-8") == profile
    assert PATHS.read_text(encoding="utf-8") == paths


RUN_WORKER_FIXTURES = ROOT / "platform" / "config-studio-transforms" / "src" / "test" / "resources" / "facility-job"


def test_the_run_workers_fixture_holds_the_facility_operations_as_the_compiler_gives_them(facility):
    """The simulator's tests (SVA-P3) run the facility's generated SPARQL, which the browser fixture above does not keep. They read these files
    beside the compiled profile of that fixture. Written with `LATTICE_WRITE_COMPILED_FIXTURE=1`, and without it they must equal the job."""
    wanted = {path: text for path, (_, text, group) in facility.items() if group == "Facility"}
    if WRITE:
        for path, text in wanted.items():
            target = RUN_WORKER_FIXTURES / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
    kept = {p.relative_to(RUN_WORKER_FIXTURES).as_posix(): p.read_text(encoding="utf-8") for p in RUN_WORKER_FIXTURES.rglob("*.rq")}
    assert kept == wanted


@pytest.fixture(scope="module")
def surface_job() -> Graph:
    config = Graph()
    for part in PARTS:
        config += sample_part(part)
    return jobs.run_job(JOB, "compile", "surface", config, load(*BASELINE_FILES), ROOT, SUBMITTED)


def test_the_surface_compilation_holds_a_scheme_for_each_projection_and_a_review_finding_for_most(surface_job):
    held = artefacts(surface_job, JOB)
    manifest = json.loads(held["projections/manifest.json"][1])
    assert [e["key"] for e in manifest] == ["borrower-exposure", "drawdown-schedule", "facility-branch", "facility-covenant-test", "facility-margin", "facility-refinancing"]
    assert all(held[e["path"]][2] == "projections" for e in manifest)
    codes = sorted({str(surface_job.value(r, CST.code)) for sev in (SH.Warning, SH.Info) for r in results(surface_job, JOB, sev)})
    assert {"DerivationReview", "ExpansionReview", "MappingReview"} <= set(codes)


def test_the_browser_fixture_of_the_surface_canvas_is_the_facility_surface_compilation_as_the_compiler_gives_it(surface_job):
    """The surface canvas reads each projection's lowered scheme from the `projections` group, and the review findings from the job's report.
    Written with `LATTICE_WRITE_COMPILED_FIXTURE=1`. Without it the checked-in file must equal what the job gives now."""
    held = artefacts(surface_job, JOB)
    found = sorted(
        (
            {"severity": sev.split("#")[-1], "code": str(surface_job.value(r, CST.code) or ""), "focus": str(surface_job.value(r, SH.focusNode) or ""), "message": str(surface_job.value(r, SH.resultMessage) or "")}
            for sev in (SH.Violation, SH.Warning, SH.Info)
            for r in results(surface_job, JOB, sev)
        ),
        key=lambda f: (f["focus"], f["code"], f["message"]),
    )
    fixture = {
        "conforms": str(surface_job.value(JOB, CST.conforms)) == "true",
        "artefacts": [{"path": path, "mediaType": media, "group": group, "content": text} for path, (media, text, group) in sorted(held.items()) if group == "projections"],
        "findings": found,
    }
    text = json.dumps(fixture, indent=2, ensure_ascii=False) + "\n"
    if WRITE:
        SURFACE.write_text(text, encoding="utf-8", newline="\n")
    assert SURFACE.read_text(encoding="utf-8") == text
