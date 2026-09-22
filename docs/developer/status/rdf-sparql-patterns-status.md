<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# RDF/SPARQL Implementation Patterns — Status Record

**Unit:** `rdf-sparql-patterns-phase`
**Status:** Slice 1 complete. Slice 2 and Slice 3 scoped and ready, blocked on ADR-A78/A79/A80 ratification.
**Last updated:** 2026-09-22
**Owner:** Agent (pending human review and ratification)

---

## Executive summary

Slice 1 of this plan is complete: [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md) consolidates the four source notes (Uniqueness, Ordering, Optimistic concurrency, Combined) into a single, corrected, cross-referenced reference, replacing the five fragmented pattern documents the original Slice 1 scoped.

The plan itself has been rewritten. The previous Slice 2 ("Store-specific adapters and policy") is removed. Its replacement, scoped from a follow-up commissioning conversation, is the `ontology/persistence` substrate and the `tools/persistence` compiler that turns an adopter's own configuration choices into generated SPARQL. The previous Slice 3 ("Proposed ADRs") is superseded: its three governing ADRs (A78, A79, A80) are delivered now, alongside the rewritten plan, per the Design First rule, rather than scheduled as a future slice. A new Slice 3, housekeeping first cut, takes its slot number.

**Key findings from the follow-up design pass:**
- The guide is a menu of patterns, not a configuration mechanism. An adopter needs a way to select among them, per class or per deployment, which the guide itself does not provide.
- Each of the guide's six configurable concerns (aggregate boundary, concurrency, ordering, receipts, meta topology, uniqueness) resolves independently, at a scope the adopter chooses, never uniformly across an ontology.
- Aggregate boundaries reduce to two runtime mechanisms (named graph, SHACL-shape-derived closure) behind two authoring surfaces. A third, hand-declared property-path surface was considered and dropped, because making a domain property a sub-property of a `dal:` term has real OWL entailment consequences and creates an import dependency the rest of this design avoids. A SHACL boundary is walked once at compile time, never requiring runtime SHACL support from the backend.
- The compiler is design-time only, needs no live backend at all: its canonical output is a `dal:CompiledProfile` graph naming a template and its parameters, never embedded SPARQL text. An optional, separate `instantiate` step, kept safe from injection by a mandatory RDF-term encoder and a type-enforced template renderer, verified by an adversarial corpus as a release gate, turns that into portable SPARQL text for an adopter who wants it.
- A backend's capability is never assumed known. The compiler always emits an unconditional `dal:CapabilityRequirement`, and an adopter may optionally supply a self-authored, unverified `dal:CapabilitySpec` for a self-consistency check. Neither depends on a live SPI or a TCK run.
- Two components the commissioning conversation initially described as in-scope (a runtime Request Query Mapping library, a Query Execution component) are explicitly deferred, because both depend on the store SPI, which does not exist yet. This is recorded as an open design question in the epic plan, not silently dropped.

**Blockers:** Slice 2 and Slice 3 execution wait on ratification of:
- ADR-A78 (persistence profile substrate and aggregate boundaries)
- ADR-A79 (persistence compiler toolchain)
- ADR-A80 (housekeeping component boundary)

---

## Completed artifacts

### Guide: `docs/architecture/rdf-sparql-patterns-guide.md`

**Scope:** consolidates Uniqueness, Ordering, Optimistic concurrency, and Combined concurrency-and-ordering into one narrative, correcting the divergences the `docs/developer/notes/misalignment.md` review identified in an earlier summary attempt.

**Status:** ✅ Complete. Fulfils the original plan's Slice 1 in full, exceeding its scope (30 chapters plus five appendices, versus the five 2–4 page documents originally planned).

### Sketch: `docs/developer/sketches/persistence-profile-substrate.md`

**Scope:** the `ontology/persistence` substrate (six dimensions, five scope kinds, the precedence algorithm, cross-axis validation, reasoning-dependency warnings, shared-substrate-class conventions), the aggregate-boundary design (two mechanisms, three authoring surfaces), and the software architecture (the compiler, and the deferred Request Query Mapping and Query Execution components, and the in-scope housekeeping first cut).

**Status:** ✅ Complete, ready for review. Governs Slice 2 and Slice 3 of this plan, in place of the original sketch, which continues to govern Slice 1's historical record.

### ADRs (Proposed, awaiting ratification)

| ADR | Decision | Status |
|---|---|---|
| [A78](../../architecture/decisions/ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md) | Persistence profile substrate and configurable aggregate boundaries | Proposed |
| [A79](../../architecture/decisions/ADR-A79-persistence-compiler-toolchain.md) | Persistence compiler toolchain and template-based SPARQL generation | Proposed |
| [A80](../../architecture/decisions/ADR-A80-housekeeping-component-boundary.md) | Housekeeping component boundary | Proposed |

### Plan: `docs/developer/plans/rdf-sparql-patterns-phase-plan.md`

**Scope:** rewritten in place. Slice 1 marked complete (fulfilled by the guide). Slice 2 redefined as the substrate-and-compiler build. Slice 3 redefined as the housekeeping first cut. Store adapter documentation and any SPI, Request Query Mapping, or Query Execution work removed and recorded as out of scope, with pointers to the epic plan's open questions.

**Status:** ✅ Complete, ready for execution once ADR-A78/A79/A80 are ratified.

---

## Slice status

| Slice | Identifier | Status |
|---|---|---|
| 1. Core patterns | `rdf-sparql-core-patterns` | ✅ Complete (fulfilled by the guide) |
| 2. Substrate and compiler | `persistence-substrate-and-compiler` | Scoped, not started. Blocked on ADR-A78/A79 ratification |
| 3. Housekeeping first cut | `housekeeping-first-cut` | Scoped, not started. Blocked on Slice 2 and ADR-A80 ratification |

---

## Open questions

Carried from [the sketch, Part 7](../sketches/persistence-profile-substrate.md#part-7--open-questions-resolved-vs-deferred), restated here as plan-level tracking, plus the two items explicitly pushed into the epic plan.

| # | Question | Where tracked |
|---|---|---|
| 1 | Request Query Mapping library design | [lattice-platform-agentic-development-v0.2.md](../plans/lattice-platform-agentic-development-v0.2.md) Part 13, row 11 |
| 2 | Query Execution component design | [lattice-platform-agentic-development-v0.2.md](../plans/lattice-platform-agentic-development-v0.2.md) Part 13, row 12 |
| 3 | Store SPI shape (proposed A75) | Not yet an ADR. Both items above depend on it |
| 4 | Whether `dal:Revision`/`dal:recordedAt` align to `fnd:Evidence`/`fnd:recordedAt` | Sketch [§3.1](../sketches/persistence-profile-substrate.md#31-namespace-and-position-in-the-layer-model), deferred to Slice 2 authoring |
| 5 | Whether a Java equivalent of `tools/persistence` is ever needed for JVM-embedded build pipelines | [ADR-A79](../../architecture/decisions/ADR-A79-persistence-compiler-toolchain.md) consequences, not scheduled |

---

## Blockers and dependencies

### Blockers (human decision required)

- ADR-A78, ADR-A79, ADR-A80 ratification, before Slice 2 or Slice 3 execution begins.

### Dependencies (internal)

- Guide ✅ complete
- Sketch ✅ complete
- Slice 2 must complete before Slice 3 begins (the housekeeping module's generated queries come from the Slice 2 compiler)

### Blocking other work

- [lattice-platform-agentic-development-v0.2.md](../plans/lattice-platform-agentic-development-v0.2.md) Part 6 (Phase 2, ingestion and query planes) carries a note that several of its slices assume ad hoc SPARQL construction this plan's compiler is meant to replace, and need revision once Slice 2 lands. That revision is not scoped by this plan or this status record.

---

## Traceability

### Links to the guide

| Sketch section | Guide chapter |
|---|---|
| Precedence algorithm | Chapter 25 (capabilities, strategies, planners) |
| Aggregate boundary mechanisms | Part V, Chapter 19 |
| Receipt model dimension | Chapter 20 |
| Ordering grain and dataset tier | Chapter 21, Chapter 22 |
| Uniqueness constraint | Chapter 8 |
| Housekeeping job taxonomy | §7.5 (P7), S3, F5, §24.2 |
| Injection safety | Chapter 28 (QP1) |

### Links to ADRs

- **A78:** substrate and boundaries (blocks Slice 2)
- **A79:** compiler toolchain (blocks Slice 2)
- **A80:** housekeeping boundary (blocks Slice 3)

---

## Next steps and timeline

1. **Human review:** sketch, rewritten plan, and ADR-A78/A79/A80 reviewed together, since the ADRs assume the sketch's vocabulary throughout.
2. **Decision gate:** A78, A79, A80 ratified, rejected, or amended.
3. **Execution:** Slice 2 begins, per its validation pack in the rewritten plan.
4. **Slice 3** begins once Slice 2's generated queries are available to consume.

---

## Appendix: Validation pack locations

- Slice 2: `docs/developer/validation/persistence-substrate-and-compiler.md` (to be created at slice start)
- Slice 3: `docs/developer/validation/housekeeping-first-cut.md` (to be created at slice start)
- Sign-off log: `docs/developer/validation/LOG.md`
