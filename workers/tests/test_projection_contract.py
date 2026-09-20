import pytest

from lattice_workers.projection_contract import InvalidProjectionContract, staging_graph_iri, validate_projection_contract


def contract():
    return {"contractId": "subscription-arr", "carrier": "https://example.test/Subscription", "projectionKind": "derivation", "roleBindings": [{"roleKind": "evaluation_subject"}, {"roleKind": "required_evidence", "property": "https://example.test/monthlyPrice"}, {"roleKind": "result_target", "property": "https://example.test/arr"}], "backendPolicy": {"allowedBackends": ["sparql", "native_ir"], "deterministicOnly": True, "llmCompletionPolicy": "no_llm_completion"}}


def test_projection_contract_requires_deterministic_no_llm_policy():
    invalid = contract() | {"backendPolicy": contract()["backendPolicy"] | {"llmCompletionPolicy": "bounded_llm"}}
    with pytest.raises(InvalidProjectionContract, match="no LLM completion"):
        validate_projection_contract(invalid)


def test_staging_graph_identity_includes_mapping_digest():
    assert staging_graph_iri("https://example.test/mork/staging", "subscription-arr", "sha256:" + "a" * 64).endswith("/subscription-arr/" + "a" * 64)