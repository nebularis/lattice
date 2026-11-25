"""The projection policy reads the reviews a compilation records, as the compile job holds them for each projection of the facility sample."""

import pytest
from rdflib import Graph

from lattice_workers.config_studio_jobs import CST, SH
from lattice_workers.projection_policy import REVIEWS, handoff_policy, review_requirements
from test_config_studio_facility_sample import PARTS, JOB, ROOT, SUBMITTED, BASELINE_FILES, load, sample_part
from lattice_workers import config_studio_jobs as jobs
from surface.model import read_projection_contracts

KINDS = {
    "facility-margin": ("derivation", ["DerivationReview"]),
    "drawdown-schedule": ("graph_construction", []),
    "borrower-exposure": ("graph_construction", ["MappingReview"]),
    "facility-branch": ("join", ["MappingReview"]),
    "facility-refinancing": ("expansion", ["ExpansionReview"]),
    "facility-covenant-test": ("expansion", ["ExpansionReview", "MappingReview"]),
}


@pytest.fixture(scope="module")
def codes_by_key() -> dict[str, list[str]]:
    """The code of each finding the compile job records on a projection of the facility sample, by the projection's key."""
    config = Graph()
    for part in PARTS:
        config += sample_part(part)
    job = jobs.run_job(JOB, "compile", "surface", config, load(*BASELINE_FILES), ROOT, SUBMITTED)
    keys = {c.iri: c.key for c in read_projection_contracts(config)}
    report = job.value(JOB, CST.report)
    out: dict[str, list[str]] = {key: [] for key in keys.values()}
    for result in job.objects(report, SH.result):
        focus = job.value(result, SH.focusNode)
        if focus in keys:
            out[keys[focus]].append(str(job.value(result, CST.code)))
    return out


@pytest.mark.parametrize("key", sorted(KINDS))
def test_each_kind_asks_the_review_its_compilation_records(key, codes_by_key):
    kind, expected = KINDS[key]
    policy = handoff_policy(kind, codes_by_key[key])
    assert policy["reviewRequirements"] == expected
    assert policy["stagingOnly"] is True
    assert policy["activationAuthority"] == "mork_governance_workflow"


def test_a_derivation_takes_its_review_a_construction_for_each_instance_none_and_a_join_the_mapping_review(codes_by_key):
    assert review_requirements(codes_by_key["facility-margin"]) == ("DerivationReview",)
    assert review_requirements(codes_by_key["drawdown-schedule"]) == ()
    assert review_requirements(codes_by_key["facility-branch"]) == ("MappingReview",)


def test_the_requirement_follows_the_findings_and_never_the_kind():
    assert review_requirements(["ExpansionReview", "MappingReview", "MappingReview", "InstanceExcluded"]) == ("ExpansionReview", "MappingReview")
    assert review_requirements([]) == ()
    assert handoff_policy("join", [])["reviewRequirements"] == []


def test_a_finding_object_is_read_by_its_code():
    class Found:
        def __init__(self, code):
            self.code = code

    assert review_requirements([Found("DerivationReview"), Found("CollectionEmpty")]) == ("DerivationReview",)


def test_the_old_names_are_gone_and_an_unknown_kind_is_refused():
    assert set(REVIEWS) == {"DerivationReview", "ExpansionReview", "MappingReview"}
    with pytest.raises(ValueError, match="unsupported"):
        handoff_policy("aggregation", [])
