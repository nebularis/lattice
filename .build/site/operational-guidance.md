<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Operational Guidance

This document records how the current LATTICE substrate is expected to be used operationally before any compiled surface exists.

## 1. Realisation posture

Per [ADR-A15](architecture/decisions/ADR-A15-realisation-strategy-neutrality.md), direct SPARQL, SHACL, reasoning, materialisation, and projection are peer strategies. At the current repo state, Eligibility and Behaviour are operationally grounded through:

- authored ontology declarations in each layer `spec/*.ttl`
- mechanism vocabularies in `vocab/*-vocab.ttl`
- structural and constraint checks in `shapes/*.ttl`
- reference fixtures in layer `test/` folders and the root [test/gate4/](../test/gate4/) corpus

## 2. Derived artefact discipline

Per [ADR-A12](architecture/decisions/ADR-A12-identity-and-derivation-model.md), any derived product for Eligibility or Behaviour should record, at minimum:

- the source declaration artefacts it depends on
- the operational profile that produced it
- the graph role it belongs to, per [ADR-A13](architecture/decisions/ADR-A13-dataset-graph-role-model.md)
- semantic content hash and generation/profile identity, where the implementation can compute them

The repository does not yet define `fnd:DerivedArtefact`, so Gate 4 records the discipline as operational guidance and fixture design rather than as a new Foundation schema change.

## 3. Static validation reference pattern

Every static declaration rule should have at least one reference realisation:

- SHACL, using the layer-local `shapes/*.ttl`
- SPARQL, using root-level query files under [test/gate4/queries/](../test/gate4/queries/)

A rule is not considered grounded by prose alone. The reference realisations may remain documented and file-based until CI automation is introduced.

## 4. Targeted invalidation guidance

Invalidation is dependency-scoped, not layer-global.

Example: changing an Eligibility interval declaration in [ontology/eligibility/test/E2-interval-containment.ttl](../ontology/eligibility/test/E2-interval-containment.ttl) should invalidate:

- the derived admissibility result for the affected `elg:Question`
- any cached Eligibility decision computed under `elg:E2`
- any Behaviour guard evaluation depending on that Eligibility profile

It should not invalidate:

- unrelated Party occupancies
- unrelated Instrument elements
- Behaviour allowance balances that do not depend on that Eligibility profile
- Quantification declarations outside the changed value-space lineage

Example: changing a Behaviour allowance definition in [ontology/behaviour/test/B-P2-sequential-allowance.ttl](../ontology/behaviour/test/B-P2-sequential-allowance.ttl) should invalidate:

- derived allowance-account balances for accounts tracking that definition
- transition executions whose effects consume that allowance
- any materialised views summarising those balances

It should not invalidate:

- Eligibility exact-match fixtures
- Instrument obligation structure unrelated to the allowance
- unrelated transition definitions in other state spaces

## 5. Current practical workflow

1. Author or amend substrate declarations.
2. Re-run relevant SHACL and SPARQL reference checks for the changed declaration family only.
3. Recompute only the derived products named by the dependency chain above.
4. Preserve prior results and reports for unaffected declarations.

This is the targeted-invalidation posture Gate 4 adopts until an automated derivation engine exists.

## 6. Deferred scope posture

Operational consumers should treat the current Behaviour extent surface as:

- supported for `bhv:Sequential`
- declared-but-unusable for `bhv:Proportional`
- unspecified for reset edge cases beyond the fixtures already authored

That means an implementation should fail fast, reject, or explicitly mark unsupported when asked to execute proportional absorption or any reset policy whose ordering law is not declared. It should not guess a policy from prose or deployment convention.

The boundary for reopening those features is recorded in [architecture/deferred-scope-and-boundaries.md](architecture/deferred-scope-and-boundaries.md).
