---
name: lattice-design
description: How to design in LATTICE and projects built on it. Use when writing or revising a sketch, a plan or slice brief, an ADR, or design questions for the human, and whenever presenting options for an architecture or modelling decision.
---

# Designing in LATTICE

## Design first

Before planning code, consult the architecture and the ADRs, and propose an ADR with either a
design sketch or a detailed entry in `docs/architecture/solution-design-specification.md`. Keep
these current with every change they cover:

- the root `README.md` (new structure, folders or projects) and each project's `README.md`
- the ADR catalogue, `docs/architecture/decisions/README.md`
- `docs/architecture/ontology-architecture.md`, `solution-design-specification.md`,
  `data-architecture.md` and `ux-design.md`

A plan for code is detailed enough to check its alignment with the architecture and the design
specification.

## LATTICE is a framework

It imposes no design decision on its users unless correctness needs it. It offers options, and
where it can, configuration and capabilities that work on the user's chosen settings. A design that
hard-codes one domain's practice as the only way is wrong at the substrate.

## Writing a sketch or a plan

- Re-read the latest version of everything the design touches. Never work from memory, and above
  all never describe an ontology's behaviour without re-reading it.
- Check each modelling consequence against the ontologies themselves.
- Check the design against the roadmap: the epic plans, the held design questions, and the slices
  waiting on this one. A design that works now and makes a roadmap item harder is wrong.
- Say a design decision once, and cross-reference it.

## Presenting a question to the human

1. **Set the scene.** What exists today, what is missing, and why it matters. State the facts about
   the current model that constrain the options, each checked against the source.
2. **Draw a picture** where the subject is structural or has more than two parts. Mermaid renders
   on GitHub. Check every diagram renders before handing off, for example by loading it with
   mermaid in a browser.
3. **Each option, then its consequences**, compared on:
   - *design overheads*: is it hard to reason about, easy to model incorrectly, hard to assure or
     govern, or brittle under likely change
   - *runtime overheads*: does it explode the data, invite inconsistency, block common traversals or
     processing, or make common operations, such as aggregating or summing a measure, behave in
     surprising ways
4. **KISS,** applied to a model that already reflects reality, never by waving reality away. Is it needed now? If not, is it needed at all? If later, can it wait, or is there value
   in doing it now? Is it as simple as it can be? KISS never overrides architectural conformance,
   non-functional requirements or standards in force.
5. **A leaning**, with its reason. Then wait for the answer.

Name each question with the slice's prefix (C9-Q1, MQ3) so answers can be recorded against it.
Record the answers in the plan or sketch, and in the status record's history.

## ADRs

- ADRs live only in `docs/architecture/decisions/`, and are listed in its `README.md`. Take the next
  free number from that catalogue, and re-check it before merging, since parallel work can claim
  the same number. Epic-scoped blocks (`A-FM`, `A-CAP`) are reserved for their epics.
- An ADR states context, decision and consequences. A decision found while building is recorded as
  an addendum, dated, rather than by rewriting the accepted text.
- The agent drafts as Proposed. Only the human accepts.

## Links and paths

- New links use canonical paths. Never `docs/adr/`.
- Move files with `git mv`, and update every source, configuration, CI, documentation and website
  reference in the same change. A historical record may keep an old path only with a relocation
  note.
