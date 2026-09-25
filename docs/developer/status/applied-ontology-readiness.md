<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Ontology Readiness - Status

**Unit ID:** `applied-ontology-readiness`
**Status:** Phase A committed (`6e36586`). Phase B through AOR-9 implemented
and self-validated in autonomous mode, uncommitted (2026-09-25). AOR-10
onwards paused for decisions and one dependency. ADRs remain Proposed.
**Last updated:** 2026-09-25
**Trigger:** human request, 2026-09-25
**Plan:** [applied-ontology-readiness.md](../plans/applied-ontology-readiness.md)
**Sketch:** [applied-ontology-readiness.md](../sketches/applied-ontology-readiness.md)
**Review request:** [applied-ontology-readiness-review.md](../review/applied-ontology-readiness-review.md)
**ADRs:** A-87 to A-92 and the A-86 addendum, all Proposed

## Current position

The human directed autonomous execution of the committed plan (2026-09-25).
As with `ontology-semantic-versioning`, that instruction is treated as
confirmation of each ADR's recommended default and of the sketch's
recommended answers to open questions 1 and 2. Ratification stays a separate
human action. Execution stopped where the next slice needs a decision this
unit's ADRs do not make, or a dependency that does not exist.

## Slices

| Slice | State | Validation Pack |
|---|---|---|
| AOR-1 | Done (commit `6b2a577`) | n/a |
| AOR-2 | Implemented, self-validated, committed `6e36586` | [aor-2](../validation/applied-ontology-readiness-aor-2.md) |
| AOR-3 | Implemented, self-validated, committed `6e36586`, job-family regeneration deferred | [aor-3](../validation/applied-ontology-readiness-aor-3.md) |
| AOR-4 | Implemented, self-validated, committed `6e36586`, Protégé step for the human | [aor-4](../validation/applied-ontology-readiness-aor-4.md) |
| AOR-5 | Implemented, self-validated | [aor-5](../validation/applied-ontology-readiness-aor-5.md) |
| AOR-6 | Implemented, self-validated | [aor-6](../validation/applied-ontology-readiness-aor-6.md) |
| AOR-7 | Implemented, self-validated | [aor-7](../validation/applied-ontology-readiness-aor-7.md) |
| AOR-8 | Implemented, self-validated | [aor-8](../validation/applied-ontology-readiness-aor-8.md) |
| AOR-9 | Implemented, self-validated | [aor-9](../validation/applied-ontology-readiness-aor-9.md) |
| AOR-10, AOR-11 | Paused: ADR-A83 harness missing, and an encoding decision (below) | |
| AOR-12 to AOR-17 | Paused: decisions (below) | |

"Self-validated" means the agent ran each slice's command and adversarial
probe. The human validation gate (VP review, command, artefacts, probe,
`docs/developer/validation/LOG.md` sign-off) has not been performed.

## Outcome by gap

| Gap | Outcome |
|---|---|
| AO1, AO2 | Examples conform with no results. The declaration warning skips profiles. ADR-A87 records the semantics |
| AO3 | `elg:candidateConcept` |
| AO4 | Generated root catalog, 19 stubs, resolution check, closure loader, consumer paragraph in `ontology-architecture.md` §2 |
| AO5 | Missing version IRIs flagged, check in CI, policy corrected. Job-family regeneration deferred |
| AO6 | Exact, set and hierarchical match, inclusion and exclusion, and profiles on SPARQL, SHACL and SWRL, with diagnostics and corpus parity |
| AO7 | `elg:EvidenceBinding`, on all three backends |
| AO8 to AO13 | Not started |

## Versions

| Documents | Change | Slices | Why |
|---|---|---|---|
| Eligibility spec and vocab, Instrument spec and vocab, Behaviour spec and vocab, applied capacity execution | 0.3.0 → 0.3.1, committed `6e36586` | AOR-2 | Eligibility shape PATCH, propagated by the proposed addendum's rule |
| same seven documents | 0.3.1 → 0.4.0, uncommitted | AOR-5, AOR-9 | Eligibility MINOR (new terms), propagated |
| Executable | 0.2.0 → 0.3.0, uncommitted | AOR-5 to AOR-9 | MINOR (new classes, properties, diagnostics) |

## Decisions awaiting the human

1. **Ratification** of ADRs A-87 to A-92 and the A-86 addendum. A-89 and A-91
   gained consequences and implementation notes during AOR-7 and AOR-9.
2. **How generated ontology documents are versioned.** The Surface compiler
   stamps every generated module `owl:versionIRI <module>/0.0.1`, so the
   job-family modules cannot be regenerated (to drop the retired
   `surface/0.0.1` import) without breaking the version check. Options:
   A. content-addressed version IRIs (`<module>/<artefact-hash prefix>`),
   recommended, matching ADR-A12's build-artefact hash. B. exempt `execution/`
   from the version check. C. the caller supplies the version.
3. **OWL encoding of exclusions over paths (AOR-10).** ADR-A90 encodes a
   condition over one dimension property. With evidence bindings a path may
   have several steps and several values. An exclusion can be read as "no
   value is excluded" (`¬∃path.Within(e)`) or "some value is not excluded"
   (`∃path.¬Within(e)`). The SPARQL reference treats several values as
   `Undetermined`, which neither form reproduces. Recommended: restrict the OWL
   backend to paths declared functional, refuse others, and state it in
   ADR-A90.
4. **Executable importing Foundation (AOR-13).** `Executable.ttl` states that
   it avoids importing substrate layers. ADR-A92 has it import Foundation.
   Alternative: align directly to `prov:` terms without the import.
5. **The Foundation change (AOR-12).** ADR-A92 asks other pending Foundation
   additions to ride in the same bump. ADR-A91 chose not to lift the
   evidence-step pattern to Foundation. Confirm that nothing else rides.
6. **Phase C ADRs** for AOR-14 to AOR-17 (derived rates, calendar binding,
   per-unit alternative bounds, provision attachment) are not drafted.
7. **Readings introduced during implementation**, each stated in the
   Eligibility README §4 and flagged here: a question with several candidate
   concepts is `Undetermined`, and a candidate outside the resolved scheme,
   where the decision needs that scheme, is `Undetermined`.
8. **Protégé and relative `nextCatalog`**, the manual step in the AOR-4 VP.
9. Sketch open question 3: one unit, or an epic with one plan per phase.

## Discovered, outside this unit

- `ontology/mork/mtp/data/pins.lock.json` is stale against `Mork.ttl` since
  `53eb210`. `mise run build:mtp` rewrites its `ontology` hash, and the
  `platform` workflow's `git diff --exit-code` would fail. Not changed here.
- Four `ontology/applied/insurance` files do not parse. `contract.ttl` is in
  `KNOWN_DEFECTS`. The other three declare no ontology.
- Two MORK examples import `…/Mork#`, with a stray fragment. In
  `KNOWN_DEFECTS`.
- `tools/surface` depends on the unpublished `lattice-vocabulary-resolver`,
  but neither `bootstrap:surface` nor the workflows installed it first. Fixed
  here, since `tools/mork_compilers` needed the same.
- Both GitHub workflows are manual-only (`workflow_dispatch`).
- `mise run topology:links` fails on 341 links that are broken at `HEAD` too,
  none in a file this unit wrote. `tools/literate_extract.py --check` reports
  Surface drift at `HEAD` too, already recorded by `ontology-semantic-versioning`.
- rdflib: the `MIN` aggregate fails on two unbound values, and a grouped
  subquery is evaluated under the outer binding, producing an empty row. The
  profile query works around both (see the AOR-8 VP and `profile_select`).

## Baseline evidence (2026-09-25, commit `9a12da4`)

| Example | Warnings | Violations |
|---|---|---|
| `hierarchical-match.ttl` | declaration warning on `ex:hierarchical-condition` | three `elg:ConditionShape` violations on `ex:hierarchical-profile`, one L8 violation on `ex:decision` |
| `condition-taxonomy.ttl` | declaration warnings on `ex:exact-condition` and `ex:set-condition` | none |
| `interval-containment.ttl` | declaration warning on `ex:profile-a`, an admission profile | one L8 violation on `ex:decision-1` |

## Token record

| Slices | Estimate | Actual |
|---|---|---|
| AOR-1 | 150k | not measured |
| AOR-2 to AOR-4 | 310k | not measured |
| AOR-5 to AOR-9 | 820k | not measured |

## Blockers

- AOR-10 and AOR-11: the ADR-A83 reasoning harness (`eligibility-compiler`
  Part B) and decision 3.
- AOR-12 and AOR-13: decisions 4 and 5.
- AOR-14 to AOR-17: decision 6.
