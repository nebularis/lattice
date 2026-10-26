---
name: lattice-design
description: How to design in LATTICE and projects built on it. Use when writing or revising a sketch, a plan or slice brief, an ADR, or design questions for the maintainer, and whenever presenting options for an architecture or modelling decision.
---

# Designing in LATTICE

## Design first

Ask the knowledge index first, as AGENTS.md's "Asking the knowledge index" says, with `--kind decision,mechanism,pattern,principle,standard` and the phase the design runs in. Where it answers weakly, read the documents as before, and report any answer they hold that no register entry does.

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

## Standards for a design

- **A class, column, status or classification is added only when some query or check answers differently because of it.** A distinction that changes no answer is one more thing to keep consistent, for nothing.
- **A fact a query or check compares is a value from a closed set, never free text.** Free text cannot be compared and drifts into variants, as the decisions' status lines drifted into fifteen shapes.
- **A section, row or definition is referred to by a name that survives an edit, never by its position.** A line number or a column index is right until the next edit, then silently wrong.
- **A thing is recorded once, however many documents mention it, and every other mention points at that record, but a node is never shared across an aggregate boundary or where concurrent writers would contend for it.** Two records of one thing diverge, as the two copies of the MORK-to-RML compiler have (TD-79). A derived restatement, such as a new version, a projection to a lower layer or a promoted value, is not a second record, since it is derived and never edited.

## Writing a sketch or a plan

- Re-read the latest version of everything the design touches. Never work from memory, and above
  all never describe an ontology's behaviour without re-reading it.
- Check each modelling consequence against the ontologies themselves.
- Check the design against the roadmap: the epic plans, the held design questions, and the slices
  waiting on this one. A design that works now and makes a roadmap item harder is wrong.
- Say a design decision once, and cross-reference it.
- A design that depends on how a triple store evaluates SPARQL cites the finding in
  [docs/architecture/triple-store-discovery.md](../../../docs/architecture/triple-store-discovery.md) it rests on, or probes the
  store and adds one first (skill `lattice-triple-stores`). The specification and a store often differ.
- A design that generates a query, or adds a SHACL-SPARQL constraint, states its cost in the terms of
  [docs/architecture/efficient-queries-and-shapes.md](../../../docs/architecture/efficient-queries-and-shapes.md): how many focus nodes or
  solutions it runs over, and which of that record's rules it relies on. Say which engine each speed claim is for.

## Presenting a question to the maintainer

1. **Set the scene.** What exists today, what is missing, and why it matters. State the facts about
   the current model that constrain the options, each checked against the source.
2. **Draw pictures, by default.** Several, one per view the option changes: the data flow (where each
   value comes from, for example compile, the caller or the query, and which graph or file it lands in), the state
   before and after, a timeline of the failure cases (a race, a partial write, a retry), and the options
   side by side. Show them inline when presenting, and put the ones that last into the plan or sketch as
   mermaid, which renders on GitHub. Check every diagram renders before handing off, for example by
   loading it with mermaid in a browser. Three rules, each found the hard way. Labels are ASCII only, because non-ASCII punctuation such as an em dash, and HTML entities, fail in some renderers. An edge targets a node, never a subgraph's own container ID, which breaks rendering. In a `classDiagram` a relation is `A --> B : label`, never `A : label --> B`, which silently declares a member instead.
3. **Each option, then its consequences**, compared on:
   - *design overheads*: is it hard to reason about, easy to model incorrectly, hard to assure or
     govern, or brittle under likely change
   - *runtime overheads*: does it explode the data, invite inconsistency, block common traversals or processing, or make common operations, such as aggregating or summing a measure, behave in surprising ways. Where the option writes terms at runtime, compare it on all four drivers of the skill `lattice-ontology-authoring`: defensible history, storage, retrieval and throughput
   - *space and time, quantified*: the order of each cost (triples stored per write, template fills
     or solutions per update, round trips, reads to reconstruct), then a worked example with stated
     numbers in a table. Name where an option's cost crosses another's
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
- The agent drafts as Proposed. Only the maintainer accepts.

## Links and paths

- New links use canonical paths. Never `docs/adr/`.
- Move files with `git mv`, and update every source, configuration, CI, documentation and website
  reference in the same change. A historical record may keep an old path only with a relocation
  note.
