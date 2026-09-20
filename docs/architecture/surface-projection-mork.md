<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface Projection to MORK

Projection authoring uses typed role bindings and a deterministic backend policy. The Phase 4 contract permits derivation, join, and expansion kinds. Each declares an evaluation subject, evidence roles, and a result target. The backend policy must set deterministic-only and `no_llm_completion`.

`projection_contract.py` validates the transport DTO before lowering: exactly one evaluation subject and result target are required, at least one evidence role is required, non-subject roles must bind a property, and unknown role fields are rejected. The staging graph IRI incorporates the mapping SHA-256 digest, so repeated deterministic lowering receives a stable, content-addressed destination.

The lowering worker accepts immutable contract and profile graph references plus a staging namespace. It delegates trusted materialization and the existing `surface lower` semantics to a deployment adapter, then returns only an immutable MORK staging graph reference, diagnostics, and backend capabilities. It rejects active mapping targets and never exposes an activation command.

The ARR fixture at `ontology/surface/examples/saas-subscription-arr-projection.ttl` is the reference derivation. The Studio Technical Inspector exposes its staged mapping identity, MCN status, dependencies, capabilities, and review route. MORK governance owns the next activation transition.

Joins route to mapping review. Derivations and expansions route to engineering review. These routes are handoff requirements, not activation permissions. Phase 4 does not grant a Surface author any MORK active-mapping write capability.