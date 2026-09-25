<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Ontology Readiness - Status

**Unit ID:** `applied-ontology-readiness`
**Status:** Phases A and B through AOR-9 committed (`6e36586`, `6e9acb1`). AOR-3b,
AOR-12 and AOR-13 implemented and self-validated, uncommitted (2026-09-25).
AOR-10 and AOR-11 wait on ADR-A83 and a path-encoding decision. AOR-14 to
AOR-17 wait on ADRs A-93 to A-96.
**Last updated:** 2026-09-25
**Trigger:** human request, 2026-09-25
**Plan:** [applied-ontology-readiness.md](../plans/applied-ontology-readiness.md)
**Sketch:** [applied-ontology-readiness.md](../sketches/applied-ontology-readiness.md)
**Review request:** [applied-ontology-readiness-review.md](../review/applied-ontology-readiness-review.md)
**ADRs:** A-87 to A-92 Accepted (2026-09-25). A-83, A-93 to A-96 and the A-86
addendum Proposed.

## Current position

On 2026-09-25 the human reported every AOR-2 to AOR-9 command passing, accepted
ADRs A-87 to A-92, chose content-hash version IRIs for generated documents,
asked for Executable to align directly to PROV-O if that imposes no functional
restriction, and asked for the Phase C ADRs and ADR-A83 to be drafted. The
`LOG.md` sign-offs are the human's to record.

## Slices

| Slice | State | Validation Pack |
|---|---|---|
| AOR-1 | Done (`6b2a577`) | n/a |
| AOR-2 to AOR-4 | Committed (`6e36586`), commands passed | [aor-2](../validation/applied-ontology-readiness-aor-2.md), [aor-3](../validation/applied-ontology-readiness-aor-3.md), [aor-4](../validation/applied-ontology-readiness-aor-4.md) |
| AOR-5 to AOR-9 | Committed (`6e9acb1`), commands passed | [aor-5](../validation/applied-ontology-readiness-aor-5.md) to [aor-9](../validation/applied-ontology-readiness-aor-9.md) |
| AOR-3b | Implemented, self-validated | [aor-3b](../validation/applied-ontology-readiness-aor-3b.md) |
| AOR-12 | Implemented, self-validated | [aor-12](../validation/applied-ontology-readiness-aor-12.md) |
| AOR-13 | Implemented, self-validated | [aor-13](../validation/applied-ontology-readiness-aor-13.md) |
| AOR-10, AOR-11 | Waiting: ADR-A83 (drafted, Proposed) and the path-encoding decision | |
| AOR-14 to AOR-17 | Waiting: ADRs A-93 to A-96 (drafted, Proposed) | |

AOR-4's Protégé step has a walkthrough:
[Loading LATTICE in Protégé](../protege-import-walkthrough.md).

## Versions in the uncommitted change set (against `6e9acb1`)

All MINOR. Foundation and its vocab, Vocabulary, MORK: 0.2.0 → 0.3.0.
Quantification, Party and its vocab, Surface and its vocab: 0.3.0 → 0.4.0.
Eligibility, Instrument, Behaviour (spec and vocab each) and the applied
capacity execution spec: 0.4.0 → 0.5.0. Executable: 0.3.0 → 0.4.0.
`applied/insurance` is a sketch and untouched, by instruction.

## Decisions awaiting the human

1. **ADR-A83** (test-only reasoning harness): ratify, then deliver it as its
   own slices (skeleton and guardrail, HermiT adapter, Python subprocess use).
2. **Path encoding for the OWL backend (AOR-10).** Options A to C, recommending
   B, are in ADR-A90's open question of 2026-09-25.
3. **ADRs A-93 to A-96**: ratify or amend.
4. **ADR-A86 and its addendum** remain Proposed.
5. **MTP pins**: whether `build` should stop rewriting `pins.lock.json` (an MTP
   decision that `mork-teaching-pack.md` reserves for an ADR).

## Discovered, outside this unit

- Link repair is planned as [`documentation-link-repair`](../plans/documentation-link-repair.md),
  pending. Its first slice fixes the checker scanning ignored `docs/_site/`.
- `ontology/applied/insurance` and the two MORK examples stay in
  `KNOWN_DEFECTS`, by instruction.
- Both GitHub workflows are manual-only (`workflow_dispatch`).
- rdflib: the `MIN` aggregate fails on two unbound values, and a grouped
  subquery is evaluated under the outer binding (AOR-8 VP).

## Token record

| Slices | Estimate | Actual |
|---|---|---|
| AOR-1 | 150k | not measured |
| AOR-2 to AOR-4 | 310k | not measured |
| AOR-5 to AOR-9 | 820k | not measured |
| AOR-3b, AOR-12, AOR-13, ADRs A-83 and A-93 to A-96 | 330k | not measured |

## Blockers

- AOR-10, AOR-11: decisions 1 and 2.
- AOR-14 to AOR-17: decision 3.
