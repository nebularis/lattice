"""Validation helpers for typed Surface Projection contract DTOs."""

from __future__ import annotations

from typing import Any, Mapping


class InvalidProjectionContract(ValueError):
    """Raised when a Projection DTO violates deterministic lowering policy."""


def validate_projection_contract(contract: Mapping[str, Any]) -> None:
    required = {"contractId", "carrier", "projectionKind", "roleBindings", "backendPolicy"}
    if set(contract) != required or not isinstance(contract["roleBindings"], list):
        raise InvalidProjectionContract("Projection contract fields do not match projection-contract 1.0.0")
    roles = contract["roleBindings"]
    kinds = [role.get("roleKind") for role in roles if isinstance(role, dict)]
    if kinds.count("evaluation_subject") != 1 or kinds.count("result_target") != 1:
        raise InvalidProjectionContract("Projection requires exactly one evaluation subject and result target role")
    if not any(kind in {"required_evidence", "candidate_evidence"} for kind in kinds):
        raise InvalidProjectionContract("Projection requires evidence role bindings")
    for role in roles:
        if not isinstance(role, dict) or set(role) - {"roleKind", "property", "carrier"}:
            raise InvalidProjectionContract("Projection role binding contains unsupported fields")
        if role.get("roleKind") != "evaluation_subject" and not role.get("property"):
            raise InvalidProjectionContract("non-subject Projection roles require a bound property")
    policy = contract["backendPolicy"]
    if not isinstance(policy, dict) or policy.get("deterministicOnly") is not True or policy.get("llmCompletionPolicy") != "no_llm_completion":
        raise InvalidProjectionContract("Projection backend policy must be deterministic-only with no LLM completion")


def staging_graph_iri(namespace: str, contract_id: str, mapping_digest: str) -> str:
    if not namespace.startswith(("http://", "https://")) or not mapping_digest.startswith("sha256:"):
        raise InvalidProjectionContract("staging namespace and mapping digest must be immutable identifiers")
    return namespace.rstrip("/") + "/" + contract_id + "/" + mapping_digest.removeprefix("sha256:")