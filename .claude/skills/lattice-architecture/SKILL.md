---
name: lattice-architecture
description: LATTICE's structure and the principles behind it. Use when a design or change crosses layers or modules, adds a dependency or an import, places a new concept in a layer, or needs to know what a layer may and may not depend on, in LATTICE or a project built on it.
---

# LATTICE's architecture

Ask the knowledge index first, as AGENTS.md's "Asking the knowledge index" says, with `mise run graph:ask -- find <the task in your own words>` and every facet value that fits the task at hand, then `read` each entry that answers. This skill's tasks span the activities cross-layer-design, solution-architecture, dependency-analysis, architecture-decision-making, quality-attribute-analysis and technology-selection, and a task often needs several of them, named together and separated by commas. `--activity`, `--quality` and `--tech` raise matching entries and hide none, while `--kind` filters exactly, so leave `--kind` off unless only one kind of entry will do. The index finds the rules this skill does not mention, and the entries related to the ones it does.

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
| Identity and versions | a thing whose content changes while it must stay the same thing, such as an instrument, a wording or a governed scheme, keeps one persistent identity across immutable versions, linked by `fnd:supersededBy`, and a version is never edited. Data that is never revised, such as an event or a measurement, needs neither | Foundation, ADR-A07b, ADR-A82 |
| Versioning of ontologies | the substrate and standalone modules are one release with one number and one tag, `ontologies-vX.Y.Z`. Applied modules and examples keep their own versions and pin a release. Breaking changes at 0.x are MINOR, marked breaking | ADR-A129, ADR-A86, ADR-A113 |
| The words are the contract | an instrument version is expressed in exactly one assembled wording, and binds exactly the stated meaning of what that wording includes | ADR-A104, ADR-A112 |
| Stated and bound meaning | a clause states meaning once, with roles, words and placeholders. Bound meaning, with parties and values, is generated per instrument, never stored with it | ADR-A104 and its addenda |
| References by identity | text names what it refers to by persistent identity, and the wording fixes the version | ADR-A112 addendum |
| Structure apart from state | a regime is stated once, and each instrument's progress through it is runtime state | ADR-A104 addendum of 2026-10-04, ADR-A106 |
| Three-valued evaluation | Eligibility decides Permitted, Denied or Undetermined, and Undetermined never becomes a breach | ADR-A104 |
| Scheme binding | concept schemes are bound to properties per scope and resolved by valid time | ADR-A85 |
| Derived artefacts | anything generated is recorded with its derivation run, and regenerated within minimal scope | ADR-A27, ADR-A92 |
| Repository topology | semantic assets in `ontology/`, executables in `tools/`, `mise` as the entry point | ADR-A77, ADR-A29 |
| Model the law, then make it usable | Instrument is an accurate model of what an agreement means, to which wording connects and onto which data arrives. Users write words or assemble components, which are interpreted into an instrument, and rarely populate it directly. Performance comes after, from Surface's projections, sharing generated meaning, or materialising per deployment | ADR-A104, the Surface ADRs |
| Layers state, code executes | ontology layers, Behaviour's runtime included, are data. The evaluator counts, sums and forces deferred values. No layer that states meaning depends on a runtime | the ontology authoring skill |
| Behaviour is abstract | a state machine that applied ontologies use, implemented differently by deployment, market or jurisdiction. Legal concepts live in Instrument, findings and execution in Behaviour | ADR-A106 |
| Agent guidance | an always-on `AGENTS.md` and skills loaded by task | ADR-A117 |

## Standards for structure

- **An architectural quantum is the smallest set that must change and be released together because of its coupling, so its size is the lower bound on incremental change.** It grows with every dependency, and is kept small by isolating change, refusing an unnecessary dependency, and insulating a boundary behind a pinned contract, an abstraction or a gate. A quantum is derived from coupling, never declared, and in each view separately. In the data view the substrate layers are one quantum, and MORK, Persistence, SPC, Surface and each applied module are their own, depending on the substrate one way. In the software view a quantum is per deployment: components sharing a store, or calling one another synchronously, are one quantum, and a broker separates them only where nothing else couples them, so one deployment of the same code can form different quanta from another. The process view is the third. `mise run build:knowledge` derives the data and software quanta. The term is distinct from the claims ontology's `clm:Quantum`.
- **Every architectural and design standard has a check that fails when it is broken, or a recorded reason it cannot.** A standard nothing checks holds only while an agent remembers it, and the knowledge index lists the ones nothing enforces.
- **Whatever a tool can derive is derived and never edited by hand, and committed only where a consumer fetches it from the repository, with a check that it regenerates unchanged.** A fact keeps one source, and an edited copy of a derived one becomes a second source that drifts (ADR-A126, ADR-A134). The ontology Turtle documents extracted from their READMEs are committed, so a tagged version can be fetched by a stable URL, and so are the XML catalogs and the release register. Nothing a build writes into `.build` is tracked.
- **A component added to remove a cost, such as a resident server or a cache, is added only once that cost is measured and recorded.** A measured read-only open of 24 ms is why the knowledge index has no server (TSD-38). This governs a component justified by speed. How data is spread across stores and graphs is a design of its own, set by the multi-store runtime, and this rule does not decide it.

## Before changing a dependency

- Read the architectural quanta the change touches, and ask whether it adds an import, an edge
  between modules, or a runtime dependency that did not exist.
- An edge that crosses the layer order is an ADR, not a change.
- A reasoner is declared only in `platform/reasoning-testkit` (ADR-A83,
  `mise run check:reasoning-isolation`).
