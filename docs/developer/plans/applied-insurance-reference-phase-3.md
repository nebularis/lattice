<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 3, Eligibility Readings and Crosswalks

**Unit ID:** `applied-insurance-reference-phase-3`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Rolling-wave outline. AIR-3.1 to AIR-3.3 are substrate slices, detailed when their
ADRs are accepted. AIR-3.4 and AIR-3.5 need the cause scheme and are detailed at AIR-2.4.
**Decisions:** [ADR-A100](../../architecture/decisions/ADR-A100-hierarchical-match-over-flat-schemes.md) (D11), [ADR-A103](../../architecture/decisions/ADR-A103-eligibility-set-readings.md) (D12)
**Sketches:** [mork-bridge.md](../sketches/mork-bridge.md), [peril-vocabulary.md](../sketches/peril-vocabulary.md) §6.8

## Scope

Make Eligibility decide correctly when a peril list is flat (A-100) and when a path reaches
several values (A-103), then let reviewed crosswalks carry a flat or simply taxonomic list to the
reference. Milestone M2 is a check across cause, agency and mechanism, run against the reference,
a flat list and a crosswalked list.

AIR-3.1 to AIR-3.3 change substrate. Each follows ADR-A-C2: the ADR's non-insurance examples are
authored as fixtures before the README prose, and no insurance term enters either layer.

## Slices

| Slice | Content | Modules |
|---|---|---|
| AIR-3.1 | A-100: the law beside L11 in the Eligibility README, its two example fixtures, `exe:NoHierarchy` (Executable PATCH), the rule in the IR's expansion and in the SPARQL backend, and the OWL backend's refusal | `ontology/eligibility` (README, examples), `tools/mork_compilers`. `Executable.ttl` gains one individual, a stated deviation from the two-module rule |
| AIR-3.2 | A-103: `elg:ValueReading`, its three individuals, `elg:valueReading` and `elg:negated` (Eligibility MINOR, cascade), fixtures, the IR, SPARQL and SHACL | `ontology/eligibility`, `tools/mork_compilers` |
| AIR-3.3 | A-103 in the SWRL (sound subset, swapped heads under negation) and OWL (`∃`, `∀ ⊓ ∃`, complement) backends | `tools/mork_compilers` |
| AIR-3.4 | crosswalk format: reviewed SKOS triples plus characteristic values on codes that name several things, as a `fnd:DerivedArtefact`. A crosswalk of one market list, and the lookup that lifts codes to reference concepts at ingestion | `insurance/peril/crosswalk/`, `ontology/mork` examples |
| AIR-3.5 | lowering to a market list, list-to-list through the reference, and milestone M2 | as 3.4, `insurance/exposure/examples/` |

Tests at L1 and L2:

- 3.1: on a flat scheme, a required code matches, an excluded code is excluded, every other member
  is Undetermined with `exe:NoHierarchy`, and a hierarchical scheme evaluates as before. SPARQL,
  SHACL and SWRL agree. The OWL backend refuses
- 3.2: each reading over zero, one and several values, including an exclusion read `EveryValue`,
  and a binding without a reading behaving as today. A negated condition swaps Permitted and
  Denied and keeps Undetermined with its diagnostic. SPARQL and SHACL agree
- 3.3: SWRL derives only the sound subset. OWL classes stand in the expected subsumptions
- 3.4: a crosswalk is stale when either edition changes. An inexact mapping never decides
- 3.5 (M2): the cyber write-back profile of peril vocabulary §6.8 decides on the reference,
  is Undetermined with a reason on a flat list, and decides exactly mapped codes of a crosswalked
  list. A risk whose perils are all of sudden onset is Permitted under `EveryValue`

Order and lanes: [machines, branches and merges](applied-insurance-reference-lanes.md). Substrate item
S2 also changes Eligibility, and rebases onto AIR-3.2.

## Documentation deltas

| Document | Change | Slice |
|---|---|---|
| `ontology/eligibility/README.md`, examples | the A-100 law, the A-103 readings | 3.1, 3.2 |
| `tools/mork_compilers/README.md` | both laws in every backend | 3.1 to 3.3 |
| `docs/architecture/ontology-architecture.md` | Eligibility section, and the MORK section on proposals that end as crosswalks | 3.2, 3.4 |
| `docs/architecture/solution-design-specification.md` | set readings as an evaluation feature | 3.2 |

## Exit gate

A-100 and A-103 Accepted and implemented. M2 demonstrated. MB-Q2 answered.
