---
name: lattice-architecture
description: LATTICE's structure and the principles behind it. Use when a design or change crosses layers or modules, adds a dependency or an import, places a new concept in a layer, or needs to know what a layer may and may not depend on, in LATTICE or a project built on it.
---

# LATTICE's architecture

This skill points to the architecture rather than restating it. The canonical sources are
[ontology-architecture.md](https://github.com/nebularis/lattice/blob/main/docs/architecture/ontology-architecture.md),
[solution-design-specification.md](https://github.com/nebularis/lattice/blob/main/docs/architecture/solution-design-specification.md)
and the [ADR catalogue](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/README.md).
Read the relevant one before deciding anything.

## The layers

```text
foundation
    └── vocabulary
            └── quantification
                    └── party
                            └── eligibility
                                    ├── wording
                                    │       └── instrument   (also imports behaviour configuration)
                                    └── behaviour configuration
                                            └── behaviour runtime
```

- Foundation to Behaviour are **substrate**, for any domain. Instrument is the first applied
  ontology on them, and applied domains (`ontology/applied/`) sit above.
- **A layer never imports or names a layer above it, a sibling, or an applied module.**
  `mise run check:import-guard` enforces this for the substrate (ADR-A01 and its addendum). A change
  to the order changes the guard's table and the diagram in `ontology-architecture.md` together.
- A layer's README is its normative source. Substrate and layer READMEs stay domain-neutral, and
  never name a downstream project.
- Downstream projects, such as Open CBAA, depend on LATTICE's release tags, never the reverse.

## Principles that most designs meet

| Principle | Says | Where decided |
|---|---|---|
| LATTICE is a framework | offer options and configuration, impose nothing correctness does not need | the design skill |
| Identity and versions | a versioned thing keeps one persistent identity across immutable versions, linked by `fnd:supersededBy`. A version is never edited | Foundation, ADR-A07b, ADR-A51 |
| Semantic versioning of ontologies | every changed document bumps its version, and importers re-pin in a cascade. Breaking changes at 0.x are MINOR, marked breaking | ADR-A86, ADR-A113 |
| The words are the contract | an instrument version is expressed in exactly one assembled wording, and binds exactly the stated meaning of what that wording includes | ADR-A104, ADR-A112 |
| Stated and bound meaning | a clause states meaning once, with roles, words and placeholders. Bound meaning, with parties and values, is generated per instrument, never stored with it | ADR-A104 and its addenda |
| References by identity | text names what it refers to by persistent identity, and the wording fixes the version | ADR-A112 addendum |
| Structure apart from state | a regime is stated once, and each instrument's progress through it is runtime state | ADR-A104 addendum of 2026-10-04, ADR-A106 |
| Three-valued evaluation | Eligibility decides Permitted, Denied or Undetermined, and Undetermined never becomes a breach | ADR-A104 |
| Scheme binding | concept schemes are bound to properties per scope and resolved by valid time | ADR-A85 |
| Derived artefacts | anything generated is recorded with its derivation run, and regenerated within minimal scope | ADR-A27, ADR-A92 |
| Repository topology | semantic assets in `ontology/`, executables in `tools/`, `mise` as the entry point | ADR-A77, ADR-A29 |
| Agent guidance | an always-on `AGENTS.md` and skills loaded by task | ADR-A117 |

## Before changing a dependency

- Read the architectural quanta the change touches, and ask whether it adds an import, an edge
  between modules, or a runtime dependency that did not exist.
- An edge that crosses the layer order is an ADR, not a change.
- A reasoner is declared only in `platform/reasoning-testkit` (ADR-A83,
  `mise run check:reasoning-isolation`).
