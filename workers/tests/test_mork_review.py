import pytest

from lattice_workers.mork_review import decision_effect, validate_snapshot_scope


def test_reshape_never_changes_projection_statistics():
    effect = decision_effect("reshape")
    assert effect.mapping_effect == "request_mapping_structure_change"
    assert effect.changes_projection_statistics is False


def test_each_decision_has_a_distinct_effect():
    effects = {decision: decision_effect(decision) for decision in ("confirm", "retarget", "reshape", "decline", "teach", "defer")}
    assert len({effect.mapping_effect for effect in effects.values()}) == 6


def test_snapshot_scope_rejects_cross_tenant_access():
    with pytest.raises(PermissionError, match="outside"):
        validate_snapshot_scope({"tenantId": "other", "projectId": "project"}, "tenant", "project")