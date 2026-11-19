"""The browser fixtures of the persistence canvas (SVA-P1b). The canvas draws the `compiled-profile.ttl` artefact of a persistence compile
job, so its fake service serves the facility sample's compiled profile, and its unit tests read it. This test keeps the fixture equal to
what the compiler gives for the sample, so a change to the compiler, the sample or the worker fails here until the fixture is written again.

    LATTICE_WRITE_COMPILED_FIXTURE=1 mise exec -- python -m pytest workers/tests/test_config_studio_compiled_fixture.py -q

Beside the profile it keeps the path of every artefact the same job holds, which the browser's rule for an operation's path is tested
against."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.namespace import RDF

from lattice_workers import config_studio_jobs as jobs
from test_config_studio_facility_sample import BASELINE_FILES, JOB, NAMESPACES, PARTS, ROOT, SUBMITTED, load, sample_part
from test_config_studio_worker import artefacts

FIXTURES = ROOT / "apps" / "config-studio" / "e2e" / "fixtures"
PROFILE = FIXTURES / "compiled-profile-facility.ttl"
PATHS = FIXTURES / "compiled-profile-facility.paths.txt"
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
