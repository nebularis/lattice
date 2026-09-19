from lattice_workers.projection_policy import handoff_policy, review_requirement


def test_join_requires_mapping_review_and_is_staging_only():
    policy = handoff_policy("join")
    assert policy["reviewRequirement"] == "mapping_review"
    assert policy["stagingOnly"] is True
    assert policy["activationAuthority"] == "mork_governance_workflow"


def test_derivation_and_expansion_require_engineering_review():
    assert review_requirement("derivation") == "engineering_review"
    assert review_requirement("expansion") == "engineering_review"