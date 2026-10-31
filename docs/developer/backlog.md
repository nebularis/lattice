<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Backlog

**Unit type:** Register, not a unit. It has no status record, no slices and no completion gate.
**Sibling:** the [pending design decisions](pending-design-decisions.md) and the [technical debt register](technical-debt.md).
**State:** collated 2026-10-30. Seven ideas, none planned. BL-03 left for the `mork-transforms` plan the same day.

## Purpose

Things we want built that no plan owns yet. Each is an idea with no sketch, or a sketch at a high level with no plan. Without a register they sit in a sketch's last section or a chat, and an agent designing something that depends on one cannot tell the dependency is unbuilt.

**What goes in.** A feature or capability we want, that is not built and has no plan. The idea, why we want it, what exists of it, and what it waits for or would unblock. Status is `Idea` when nothing is written and `Sketched` when a high-level sketch exists.

**What does not.** A shortfall in something that exists, which is technical debt. A design question that must be answered first, which is a pending design decision. Work a plan already owns, which stays in its plan.

**When a plan is written for an item, it leaves the backlog.** The row is removed in the commit that adds the plan, naming it, like the other two removable registers. A row is not a commitment. The maintainer decides what is planned.

`mise run graph:ask` finds a row by its idea like any entry, kind `backlog`. `find` flags with `BL` an entry that a row's Bears on names, so an agent reading a capability or decision learns that an unbuilt idea bears on it.

## Register

| ID | Idea | Raised | Why we want it | What exists | Status | Waits for | Bears on |
|---|---|---|---|---|---|---|---|
| BL-01 | **A platform-wide configuration layer for LATTICE, so every service, worker and tool reads its settings the same way and a named provider supplies them.** | 2026-10-30, the maintainer | each service and worker reads its settings its own way today, so an operator learns several conventions and a provider cannot be swapped once | a sketch is being written at [platform-configuration](sketches/platform-configuration.md). Nothing is built | Sketched | ADR-A71 | ADR-A136 |
| BL-02 | **A native HashiCorp Vault adapter for the `SecretProvider` seam.** | 2026-10-30, the maintainer | an operator who keeps secrets in Vault cannot use the studio without copying them into files or the environment | the seam is in ADR-A71. Only environment and file secrets exist, in `workers/src/lattice_workers/config_studio_secrets.py` and `platform/config-studio-core/src/main/java/org/nebularis/lattice/studio/settings/Secrets.java` | Idea | ADR-A71, BL-01 | ADR-A71, ADR-A136 |
| BL-04 | **An `ask_target` tool for the MORK mapping proposer, so the model asks about a target term interactively.** | 2026-10-30, [mapping proposer review](notes/mapping-proposer-review.md) | the knowledge index ranks a term by meaning where BM25 over labels cannot, for example `ins:Power` at 0.82 for a legal relation whose holder changes a position by an act | the review names it as a further option. `describe_term` and the translation cards (R1 to R3) are built | Idea | CAP-100 | CAP-100 |
| BL-05 | **A SHACL shape that holds a quantity's literal to its space's `qnt:valueDatatype`.** | 2026-10-30, the second ODRL proposal trial | a proposal or a configuration can hold a value its space's datatype refuses, and nothing says so | TD-125 records the gap and the likely shape. No shape exists | Idea |  | TD-125 |
| BL-06 | **A published client SDK for the generated persistence operations, with generated code per language.** | 2026-10-10, H2-Q1 of the typed IR sketch | an adopter in another language would call the persistence operations without writing the typed payload by hand | the [sketch](sketches/persistence-client-sdk.md), held for the end of Track H. ADR-A132 builds the in-repository caller library only | Sketched | ADR-A132 | ADR-A132, ADR-A79 |
| BL-07 | **The knowledge index in projects built on LATTICE, with a private project's own registers beside LATTICE's.** | 2026-10-25, KC-Q1 to KC-Q7 | a project built on LATTICE would ask the same questions of its own decisions and registers and of LATTICE's | the [sketch](sketches/knowledge-index-for-consumers.md). The consumer distribution plan does not cover it | Sketched | ADR-A134 | ADR-A134 |
| BL-08 | **Storing a workspace's uploaded files that are not graph data, such as an XML or JSON sample source, beside its graphs.** | 2026-10-31, the maintainer | a sample or a source document a user uploads is lost when the browser closes, and a mapping's dry run cannot be repeated by anyone else | the studio stores RDF only, and a sample lives in the browser's memory. The [publication sketch](sketches/studio-publication.md) fences imports that are graph data | Idea | ADR-A149 | ADR-A136, ADR-A149 |
