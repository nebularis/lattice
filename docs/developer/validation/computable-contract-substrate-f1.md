<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS F1, external and natural keys

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/f1-keys`. Commits are the human's
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (F1 in detail)
**Decisions:** [ADR-A114](../../architecture/decisions/ADR-A114-external-and-natural-keys.md) (Accepted 2026-10-03, at the phase 0 gate), CC-D9, ADR-A51, ADR-A84, ADR-A86, ADR-A113

## Invariant

Any thing in a LATTICE graph can carry the names the world gives it, as key nodes with a scheme and a value, either locating it (`fnd:externalKey`) or identifying it (`fnd:naturalKey`). A natural key identifies one thing: checked by SHACL everywhere, merged by OWL only under `fnd:MergedOnNaturalKey`, enforced at write time by Persistence under `dal:PersistenceKeyed`. Identity stays ADR-A51's.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard && mise run check:persistence && mise run check:minting
```

## Artefacts to inspect

- `docs/developer/sketches/keys-impact.md`: the phase 0 analysis of Persistence, Surface and the cascade, reviewed at the gate.
- `ontology/foundation/examples/keys.ttl`, `ontology/persistence/examples/persistent-foundation-keys.ttl`, `ontology/surface/examples/keys.ttl`: written before the model.
- Foundation's spec, shapes and README section on keys. Persistence's `persistent-foundation` and its README section.
- The cascade: every re-pinned document, its release row and tag.

## Deliberate non-coverage

Normalisations outside the minting specification's three pipelines (a change to that specification), including the exact pipeline of follow-up FU-F1a. The compiler deriving the natural-key constraint from `dal:PersistenceKeyed` (FU-F1b). Both are in the plan's F1 follow-ups table. Keys on instruments, made in C6. Revising AIR-4.1's rows that name `aeo:Identifier`, done when F1 merges. Open CBAA's migration of `agr:umr`. NRS N9's Foundation change, which keeps its own window.

## Open questions

- **F1-Q1. Foundation's uniqueness shape and `fnd:MergedOnNaturalKey`.** Answered 2026-10-03:
  (b). Two different things sharing a natural key are a violation, unless both are
  `fnd:MergedOnNaturalKey`, when the pair is a warning (`fnd:MergedNaturalKeyShape`) whose message
  says a reasoner will infer `owl:sameAs` and that, if they are different things, the data is wrong.
  Foundation README §8.7 tells a reader how to interpret both severities.

## Handoff

Written by the building machine when the work is ready for the human to commit.

- **Built:**
  - Foundation 0.4.0: the keys of ADR-A114 and the G2 property chain (README §8), and Foundation's
    first shapes, `shapes/constraints.ttl` 0.2.0, with F1-Q1's warning. The README is again the
    literate source of `spec/foundation.ttl`: its ontology header became a block in §2, and the spec
    is regenerated from it (semantically unchanged before F1, two `owl:disjointWith` axioms now stated
    from the other side).
  - `persistent-foundation` 0.1.0 (`spec/persistent-foundation.ttl`, importing Foundation 0.4.0 and
    Persistence 0.2.1) and `shapes/persistent-foundation.ttl` (persistence-shapes 0.2.0): the key
    class shapes of G1, the sensitive and personal-data shapes of P5, normalisation agreement (P3),
    keys typed by their class, and natural-key constraints on every `dal:PersistenceKeyed` class.
    Persistence README §14.
  - The cascade: 24 importers re-pinned, each a MINOR, with the catalog and 28 release rows. Surface's
    compiler constant moved to 0.6.0 (S4). Tests naming a current version updated, history
    assertions kept. Release notes in the Foundation, Wording, Behaviour and capacity READMEs.
  - `tools/test_keys.py`, F1-01 to F1-15 and F1-Q1, 30 tests, added to `check:ontology-catalog`.
  - Elsewhere: the architecture doc's Foundation section, AIR-4.1's `aeo:LegalEntity` row, C6-Q2
    and the plan's Open CBAA `agr` row.
- **Not run:** the Java and frontend checks of `mise run check`, which F1 does not touch.
- **Check first:** the 28 tags `mise run check:ontology-versioning` lists, created after commit.
  The Foundation spec diff is large because it is now generated from the README.
- **Deviations from the plan:**
  - Examples (phase 1). The Foundation example locates the agreement from drawdown requests and a
    transfer certificate in place of declarations and a claim, keeping to a neutral domain
    (ADR-A-C2). The Surface example has no index contract, since the analysis found an index adds
    nothing (S1). It has two promotion contracts, not one: under `srf:NoEntailment` a step follows
    asserted triples only, so one contract ends in `fnd:naturalKey` and the other in
    `fnd:externalKey`. The Foundation example's agreement identity gains the payout account as an
    external key, so the second contract has something to promote. F1-15 added for it.
  - No default `dal:UniquenessConstraint` ships in `persistent-foundation`: the compiler reads one
    `dal:appliesTo` per constraint, so a shipped constraint could serve one class only. A shape
    requires one per `dal:PersistenceKeyed` class instead. ADR-A114's Consequences and the plan
    record it, and technical debt TD-15 the compiler's silent choice of one scope.
  - `persistent-foundation` imports Persistence as well as Foundation, since it uses `dal:` terms.
    The `dal:` ontology itself still imports nothing.

## Results

Run on machine R, 2026-10-03, against this checkout's packages. `surface`, `mork_compilers` and `mtp`
were installed from another clone on this machine, so they ran with this checkout's sources first on
`PYTHONPATH` (procedure step 8 in `.github/copilot-instructions.md`).

| Check | Result |
|---|---|
| `tools/test_keys.py` (F1-01 to F1-15, F1-Q1, reasoner rows included) | 30 passed |
| `mise run check:ontology-catalog` (all ontology tool tests, `test_keys.py` included, catalog) | 306 passed, catalog consistent |
| `mise run check:ontology-versioning` | passed, 28 tags pending |
| `mise run check:import-guard` | 0 violations |
| `mise run check:persistence` | 778 passed |
| `mise run check:python-root` (Surface, Phase 8 conformance) | 84 passed |
| `mise run check:vocabulary`, `check:mork-compilers`, `check:reasoning-isolation` | 16, 114 passed, isolated |
| `mise run build:mtp`, `check:mtp` | passed. `pins.lock.json`'s ontology hash regenerated for MORK 0.5.0 (C3), every term hash unchanged |
| literate checks: Foundation, Wording, Behaviour, Surface | consistent |
| Mermaid: the new diagrams in Foundation §8 and Persistence §14 | parse |
| adversarial probe: F1-Q1's warning severity removed | `test_f1_q1` fails, as it should |
