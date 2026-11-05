## Design first

The knowledge index is asked as AGENTS.md's "Asking the knowledge index" says. The design specification is `docs/architecture/solution-design-specification.md`.

- `docs/architecture/ontology-architecture.md`, `solution-design-specification.md`, `data-architecture.md` and `ux-design.md`

## Standards for a design

Free text drifted into variants as the decisions' status lines drifted into fifteen shapes. Two records of one thing diverged as the two copies of the MORK-to-RML compiler did until one was removed.

## Standards for structure

In the data view the substrate layers are one quantum, and MORK, Persistence, SPC, Surface and each applied module are their own, depending on the substrate one way. `mise run build:knowledge` derives the data and software quanta. The term is distinct from the claims ontology's `clm:Quantum`.

Derived artefacts follow ADR-A126 and ADR-A134. The ontology Turtle documents extracted from their READMEs are committed, so a tagged version can be fetched by a stable URL, and so are the XML catalogs and the release register. Nothing a build writes into `.build` is tracked.

A measured read-only open of 24 ms is why the knowledge index has no server (TSD-38). This governs a component justified by speed. How data is spread across stores and graphs is a design of its own, set by the multi-store runtime, and this rule does not decide it.

## Writing a sketch or a plan

`graph:ask -- reaches <ID>` names what an entry touches. A plan's header declares the unit's slice prefix, `**Prefix:** CCS` (STD-303, STD-304). A design that depends on how a triple store evaluates SPARQL cites the finding in [docs/architecture/triple-store-discovery.md](../../../docs/architecture/triple-store-discovery.md) it rests on (skill `lattice-probing`). A design that generates a query states its cost in the terms of [docs/architecture/efficient-queries-and-shapes.md](../../../docs/architecture/efficient-queries-and-shapes.md).

## Presenting a question to the maintainer

The four drivers are in the skill `lattice-ontology-modelling`: defensible history, storage, retrieval and throughput. Name each question with the slice's prefix (C9-Q1, MQ3).

A question raised by a bold lead, `**LG-Q7. <question>**`, is promoted as `Answered 2026-10-19, (a), now MEC-nn.` (STD-283). The build reports an answer of that kind left unpromoted for 30 days.

## Decisions

Epic-scoped blocks (`A-FM`, `A-CAP`) are reserved for their epics. An addendum that reverses or narrows is STD-282, and a whole decision replaced says `Superseded by ADR-Ann` in its Status line.

## Links and paths

- Never `docs/adr/`.

## LATTICE is a framework

It imposes no design decision on its users unless correctness needs it. It offers options, and where it can, configuration and capabilities that work on the user's chosen settings. A design that hard-codes one domain's practice as the only way is wrong at the substrate.
