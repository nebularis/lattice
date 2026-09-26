<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-1.2, shared contracts

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/1.2-shared-contracts`
**Plan and test cases:** [Phase 1 plan](../plans/applied-insurance-reference-phase-1.md) (AIR-1.2)
**Decisions:** ADR-A98 (decisions 1, 5, 6), ADR-A102

## Invariant

Every classification the epic needs has one `voc:SchemeContract` at the lowest level of sharing that covers its users, the liability role types exist as `pty:Role` individuals, and the cross-domain module imports nothing from a domain.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, after `mise run build:ontology-catalog` and `mise run build:ontology-releases`.

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- `ontology/applied/classification/` and `ontology/applied/insurance/common/`: both documents of each, and their READMEs.
- `tools/test_applied_shared_contracts.py`.

## Deliberate non-coverage

No reference editions are bound (AIR-2.2 onwards). The loss event (AIR-4.4) and the liability direction scheme (Phase 5) come later.

## Handoff

Written by the building machine when the work is committed. S could not run the tests, so R runs them first.

- **Built:** `ontology/applied/classification/{spec/classification.ttl,vocab/classification-vocab.ttl,README.md}` (three no-domain properties, three scheme contracts, no `voc:boundScheme`). `ontology/applied/insurance/common/{spec/common.ttl,vocab/common-vocab.ttl,README.md}` (six properties, six contracts, the four ADR-A102 liability roles as `pty:Role` `owl:NamedIndividual`s declared the same way `ontology/party/vocab/party-vocab.ttl` declares `pty:Obligor`/`pty:Obligee`). `tools/test_applied_shared_contracts.py` (one test per plan row, AIR12-01 to AIR12-06). Edited `ontology/applied/README.md` (`classification/` now present) and `ontology/applied/insurance/domain-README.md` (`common/` now built) and the applied-insurance row of `docs/architecture/ontology-architecture.md` §3, all per the plan's own edit list. Neither module has a `shapes/` directory: neither has a shape of its own, per ADR-A98 decision 3 and the plan's own note that Vocabulary's and Party's shapes already cover the contracts and roles.
- **Not run:** `mise run check:ontology-catalog` (which runs `tools/test_applied_shared_contracts.py`) and `mise run check:ontology-versioning` — no runtime on this machine. AIR12-01 as written asks for import-closure loading through `tools/ontology_catalog.py`; the test instead checks each document's own `owl:imports` set against the pinned versions, the same proxy AIR-2.1's test used before its catalog stubs existed, since the root catalog doesn't know about these four new documents until `mise run build:ontology-catalog` runs.
- **Check first:** a sequencing gap, discovered while writing `common/`'s README, not fixed here since it's outside this slice's edit list: ADR-A98 decision 5 says `peril/` imports `common/`, but `peril/`'s spec was built in AIR-2.1, before `common/` existed, so it does not import it yet. Recorded as a note in `common/README.md`'s "Dependencies" section and in the applied-insurance row of `ontology-architecture.md`. Whoever builds AIR-2.2 (or an earlier fix-up slice) needs to add the import to `ontology/applied/insurance/peril/spec/peril.ttl` and decide whether any `icm:` property gets a `prl:`-prefixed specialising sub-property at that point.
- **Deviations from the plan:** none identified.

## Results

Written on machine R at verification.
