<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Ontology Readiness - Status

**Unit ID:** `applied-ontology-readiness`
**Status:** Phase A implemented and self-validated in autonomous mode
(2026-09-25). Phase B in progress. ADRs remain Proposed.
**Last updated:** 2026-09-25
**Trigger:** human request, 2026-09-25
**Plan:** [applied-ontology-readiness.md](../plans/applied-ontology-readiness.md)
**Sketch:** [applied-ontology-readiness.md](../sketches/applied-ontology-readiness.md)
**ADRs:** A-87 to A-92 and the A-86 addendum, all Proposed

## Current position

The human directed autonomous execution of the committed plan (2026-09-25).
As with `ontology-semantic-versioning`, that instruction is treated as
confirmation of each ADR's recommended default, and of the sketch's
recommended answers to open questions 1 and 2. Ratification stays a separate
human action. Design decisions not covered by an ADR are paused and listed
below.

## Slices

| Slice | State |
|---|---|
| AOR-1 | Done (commit `6b2a577`) |
| AOR-2 | Implemented, self-validated. [VP](../validation/applied-ontology-readiness-aor-2.md) |
| AOR-3 | Implemented, self-validated, one item deferred. [VP](../validation/applied-ontology-readiness-aor-3.md) |
| AOR-4 | Implemented, self-validated, Protégé step pending. [VP](../validation/applied-ontology-readiness-aor-4.md) |
| AOR-5 to AOR-17 | Not started |

### AOR-2

Examples declare concepts with the requested comment, the declaration warning
skips admission profiles, and the older L8 and profile violations are fixed.
`hierarchical-match.ttl` is bound to a scheme contract (open question 2).
PATCH cascade: Eligibility spec and vocab, Instrument spec and vocab,
Behaviour spec and vocab, and the applied capacity execution spec move
0.3.0 → 0.3.1, classified by the proposed addendum's propagation rule.

### AOR-3

The version check fails a `spec/` or `vocab/` document with no version IRI,
has its own tests, and runs in the `platform` workflow. The root package gains
a `test` extra declaring `pytest`. The policy now applies the cascade to every
bump and states the propagation rule.

### AOR-4

`tools/ontology_catalog.py` generates the root catalog and 19 stubs, checks
resolution, and loads closures through catalog chains. `.gitignore` ignored
every `catalog*.xml` as a Protégé temp file. Three negation rules now track
the generated catalogs, which ADR-A88 requires.

## Decisions awaiting the human

1. **Ratification** of ADRs A-87 to A-92 and the A-86 addendum.
2. **How generated ontology documents are versioned.** The Surface compiler
   stamps every generated module `owl:versionIRI <module>/0.0.1`. Regenerating
   the job-family modules (to drop the retired `surface/0.0.1` import) would
   change their content under the same version IRI, which the version check
   rejects. Options:
   - A. Content-addressed version IRIs (`<module>/<artefact-hash prefix>`), so
     every regeneration that changes content changes the IRI. Recommended. It
     matches ADR-A12's build-artefact hash.
   - B. Exempt generated modules (under `execution/`) from the version check,
     relying on the manifest's hashes.
   - C. The compiler takes a version from the caller.
   The four modules stay listed in `KNOWN_DEFECTS` until this is decided.
3. **Protégé and relative `nextCatalog`**, the manual step in the AOR-4 VP.
4. Sketch open question 3: one unit, or an epic with one plan per phase.

## Discovered, outside this unit

- `ontology/mork/mtp/data/pins.lock.json` is stale against `Mork.ttl` since
  `53eb210` (the semantic-versioning baseline reset added its version IRI).
  `mise run build:mtp` rewrites the `ontology` hash, and the `platform`
  workflow's `git diff --exit-code` would fail. Not changed here.
- Four `ontology/applied/insurance` files do not parse (unbound `ctr:` and
  `skos:` prefixes, a newline inside a string literal). `contract.ttl` is
  listed in `KNOWN_DEFECTS`. The other three declare no ontology.
- Two MORK examples import `http://www.nebularis.org/ontologies/Mork#`, with
  a stray fragment. Listed in `KNOWN_DEFECTS`.
- Both GitHub workflows are manual-only (`workflow_dispatch`).

## Baseline evidence (2026-09-25, commit `9a12da4`)

A read-only pySHACL run of each Eligibility example before AOR-2:

| Example | Warnings | Violations |
|---|---|---|
| `hierarchical-match.ttl` | declaration warning on `ex:hierarchical-condition` | three `elg:ConditionShape` violations on `ex:hierarchical-profile`, one L8 violation on `ex:decision` |
| `condition-taxonomy.ttl` | declaration warnings on `ex:exact-condition` and `ex:set-condition` | none |
| `interval-containment.ttl` | declaration warning on `ex:profile-a`, an admission profile | one L8 violation on `ex:decision-1` |

## Token record

| Slice | Estimate | Actual |
|---|---|---|
| AOR-1 | 150k | not measured |
| AOR-2 to AOR-4 | 310k | not measured |

## Blockers

- AOR-10 and AOR-11 need the ADR-A83 reasoning harness (`eligibility-compiler`
  Part B), which does not exist.
- Phase C slices each need an ADR drafted and agreed first.
