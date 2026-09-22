<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# RDF/SPARQL Implementation Patterns — Status Record

**Unit:** `rdf-sparql-patterns-phase`
**Status:** Slice 1 complete. ADR-A78/A79/A80 ratified. Slice 2 complete. Slice 3 (housekeeping first cut) not started.
**Last updated:** 2026-09-22
**Owner:** Agent (autonomous execution authorised by the human; Slice 2 delivered without further pause)

---

## Executive summary

Slice 1 is complete: [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md) consolidates the four source notes into one corrected, cross-referenced reference.

ADR-A78, ADR-A79, and ADR-A80 are ratified (Status: Accepted).

**Slice 2 is complete.** `ontology/persistence` is authored (vocabulary, self-validating SHACL shapes, 14 example fixtures, two design-note documents) and `tools/persistence` is a working Python compiler: 239 tests pass under `mise run check:persistence`, covering the resolver, validator, capability self-check, boundary-shape walker, an 11-template Mustache library, a 164-case injection corpus, determinism under triple-order permutation, full compile→instantiate→parse round trips, and three Python architecture-policy checks. Doc deltas (root `README.md`, `ontology-architecture.md`, `mise.toml`) are done. Traceability matrix and validation pack are in place.

**Slice 3 (housekeeping first cut) has not been started** and remains scoped as written in the plan.

**Key findings from building Slice 2, beyond what the sketch anticipated:**

- **A class alone cannot be the unit of resolution.** The sketch's lending/credit worked example needed an actual implementation decision the sketch's prose did not spell out mechanically: a `Target` is a `(class, deployment)` pair, one per distinct `dal:GraphPatternScope` a class has (via a new `dal:coversClass` property, added during implementation), plus one unscoped/fallback target. Documented in `tools/persistence/README.md` and `ontology/persistence/docs/precedence-and-resolution.md`.
- **Two real SPARQL-validity bugs existed in the design as sketched**, both caught only by actually rendering and parsing the templates with `rdflib`'s own SPARQL parser: (1) SPARQL 1.1 permits a property path only inside `WHERE`, never inside a `DELETE`/`INSERT` template block, and has no bounded `{n,m}` repetition at all — the sketch's `CompositePropertyBoundary` worked SPARQL used both incorrectly. (2) A single SPARQL variable cannot stand in for an entire set of triples (`GRAPH ?g { $payload }` is not valid SPARQL) — every template needing to accept caller-supplied payload triples now uses a documented, non-SPARQL `#PAYLOAD#` text marker instead, which whatever eventually executes the template must splice in before submission.
- **`ontology/persistence/spec/persistence.ttl` had one property the sketch's Appendix A never declared** (`dal:aggregateBoundary`, used inconsistently against the actually-declared `dal:strategy`), found and fixed in both the ontology and the sketch itself during implementation.
- **Mustache double-brace tags must never appear inside a `{{! comment }}` block**, including when the comment is *describing* Mustache syntax for documentation purposes — chevron's comment parser ends at the first closing double-brace it finds, silently truncating the comment and corrupting everything after it. Found by the template test suite, not by inspection.
- **`pyshacl`'s `conforms` flag treats any result, including `sh:Warning` severity, as non-conformant unless `allow_warnings=True` is passed** — needed for the `SharedClassProfileWarningShape` design to work as a non-blocking warning at all.

---

## Completed artifacts

### Guide: `docs/architecture/rdf-sparql-patterns-guide.md`

**Status:** ✅ Complete.

### Sketch: `docs/developer/sketches/persistence-profile-substrate.md`

**Status:** ✅ Complete, remediated per human review (concurrency renamed for what it provides, the capability model rebuilt as an unconditional-requirement-plus-optional-self-check with no live-backend dependency, the compiler's canonical output made TTL rather than SPARQL text, and the hand-declared composition-property authoring surface dropped in favour of SHACL only). Governs Slice 2 and Slice 3.

### ADRs: A78, A79, A80

**Status:** ✅ Accepted.

### Plan: `docs/developer/plans/rdf-sparql-patterns-phase-plan.md`

**Status:** ✅ Complete. Slice 2 executed as scoped; Slice 3 unchanged.

### `ontology/persistence`

| Path | Contents |
|---|---|
| `README.md` | purpose, the `dal:` prefix, three worked examples (single class, shared-class deployments, SHACL-declared composite boundary) |
| `spec/persistence.ttl` | the vocabulary, ~300 triples, all eleven sections (scopes, six dimensions, capability triad, templates/operations, compiled output) |
| `shapes/constraints.ttl` | self-validating SHACL shapes, including the mandatory-`boundaryShape` check and the `SharedClassProfileWarningShape` |
| `examples/` | 14 fixtures: 5 positive (including the lending/credit conflict and the SHACL-declared composite boundary), 5 cross-axis negative fixtures (one per sketch §3.5 row), 1 mixed-receipt-model warning fixture, 1 shared-class-profile warning fixture, 1 SHACL-level negative fixture (missing `boundaryShape`), 1 value-based-CAS positive fixture |
| `docs/precedence-and-resolution.md`, `docs/aggregate-boundaries.md` | the two design notes the plan required |

### `tools/persistence`

Python package (`persistence`), `pyproject.toml`, installable via `mise run bootstrap:persistence`. Modules: `terms` (the injection-safety encoder hierarchy), `render` (the type-enforced Mustache renderer), `namespaces`, `scopes` (including the `Target` model), `resolver` (the precedence algorithm), `boundary` (the SHACL closure walker), `capability` (requirement/spec/check), `validator` (every cross-axis check, named exception types), `operations` (template selection), `compiler` (orchestration and RDF emission), `instantiate` (the optional SPARQL-rendering stage), `cli`. 11 Mustache templates. 239 tests across 7 test modules, all passing.

**Validation pack:** [`docs/developer/validation/persistence-substrate-and-compiler.md`](../validation/persistence-substrate-and-compiler.md).
**Traceability:** [`docs/traceability/matrix.csv`](../../traceability/matrix.csv).

### Doc deltas

- `docs/architecture/ontology-architecture.md` — new §8a (Persistence), plus an Implementation Status table row.
- Root `README.md` — a new paragraph in "Ontology Layers", a tree entry, a repository-structure check entry, and a "Validate the persistence compiler" section.
- `mise.toml` — `bootstrap:persistence` and `check:persistence` tasks, wired into the aggregate `bootstrap` and `check` tasks.
- `.gitignore` — `*.egg-info/` added (missing before this slice).

---

## Slice status

| Slice | Identifier | Status |
|---|---|---|
| 1. Core patterns | `rdf-sparql-core-patterns` | ✅ Complete (fulfilled by the guide) |
| 2. Substrate and compiler | `persistence-substrate-and-compiler` | ✅ Complete |
| 3. Housekeeping first cut | `housekeeping-first-cut` | Scoped, not started |

---

## Open questions

Unchanged from before Slice 2 began. Building the compiler did not resolve any of these; it also did not need to.

| # | Question | Where tracked |
|---|---|---|
| 1 | Request Query Mapping library design | [lattice-platform-agentic-development-v0.2.md](../plans/lattice-platform-agentic-development-v0.2.md) Part 13, row 11 |
| 2 | Query Execution component design | [lattice-platform-agentic-development-v0.2.md](../plans/lattice-platform-agentic-development-v0.2.md) Part 13, row 12 |
| 3 | Store SPI shape (proposed A75) | Not yet an ADR. Both items above depend on it |
| 4 | Whether `dal:` receipt/capability terms align to `fnd:Evidence`/`fnd:recordedAt` | Sketch [§3.1](../sketches/persistence-profile-substrate.md#31-namespace-and-position-in-the-layer-model), not settled by Slice 2 |
| 5 | Whether a Java equivalent of `tools/persistence` is ever needed for JVM-embedded build pipelines | [ADR-A79](../../architecture/decisions/ADR-A79-persistence-compiler-toolchain.md) consequences, not scheduled |

**New, found during Slice 2 (not previously tracked):**

| # | Question | Notes |
|---|---|---|
| 6 | `unconditional-write`'s missing variants | Only handles `dal:NamedGraphBoundary`. A target combining `dal:ProvidedConcurrency`/`dal:LockingConcurrency` with `dal:CompositePropertyBoundary` or `dal:NoBoundary` needs a second template variant, not yet built. |
| 7 | Multi-property `CompositePropertyBoundary` closures | `cas-replace-composite-property` uses only the first composite property found, with `+` traversal. A shape with several sibling composite properties at one level needs a property-path alternation this first cut does not generate. |

---

## Blocking other work

- [lattice-platform-agentic-development-v0.2.md](../plans/lattice-platform-agentic-development-v0.2.md) Part 6 is still marked pending revision once this plan's Slice 2 lands. **Slice 2 has now landed.** That revision itself remains out of scope for this plan and is not scheduled here.
- Slice 3 (housekeeping) depends on Slice 2's generated queries, which now exist and are consumable via `python -m persistence instantiate`.

---

## Traceability

### Links to the guide

| Sketch/implementation section | Guide chapter |
|---|---|
| Precedence algorithm | Chapter 25 (capabilities, strategies, planners) |
| Aggregate boundary mechanisms | Part V, Chapter 19; §24.1 (tombstones) |
| Receipt model dimension | Chapter 20 |
| Ordering grain and dataset tier | Chapter 21, Chapter 22 |
| Uniqueness constraint | Chapter 8, §6.2 (key-claim write/retire) |
| Housekeeping job taxonomy (Slice 3, not yet built) | §7.5 (P7), S3, F5, §24.2 |
| Injection safety | Chapter 28 (QP1) |

### Links to ADRs

- **A78:** substrate and boundaries — implemented in `ontology/persistence` and `persistence.{scopes,resolver,boundary}`.
- **A79:** compiler toolchain — implemented in `tools/persistence` in full (both `compile` and `instantiate` subcommands).
- **A80:** housekeeping boundary — not yet implemented (Slice 3).

### Full requirement-to-test mapping

See [`docs/traceability/matrix.csv`](../../traceability/matrix.csv).

---

## Next steps

1. **Slice 3 (housekeeping first cut)**, per the plan: `platform/housekeeping` Maven module, job contracts, configuration model split, generated queries via `persistence instantiate`, README, and `docs/architecture/platform-housekeeping.md`.
2. Resolve or continue deferring the two new open questions found during Slice 2 (items 6 and 7 above) before Slice 3 generates housekeeping job queries against `CompositePropertyBoundary` targets, if any exist.

---

## Appendix: Validation pack locations

- Slice 2: [`docs/developer/validation/persistence-substrate-and-compiler.md`](../validation/persistence-substrate-and-compiler.md) ✅ complete.
- Slice 3: `docs/developer/validation/housekeeping-first-cut.md` (to be created at slice start).
- Sign-off log: `docs/developer/validation/LOG.md` (not yet created; human sign-off per the plan's Part 3 five-step gate is still pending).
