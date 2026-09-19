# LATTICE

A domain neutral semantic framework for representing governing instruments (contracts, protocols, agreements, etc) and the obligations, eligibility conditions, and lifecycle behaviours they define, as structured, queryable, versioned graphs.

---

## Overview

### Ontology Model

LATTICE is the middle of a three-part picture.

**MORK (Mapping Ontological & Representational Knowledge)** used to map source material — structured data (schemas, records, API specifications, etc) and unstructured wordings (documents, clauses, free text) — onto a target domain ontology's T-box & R-Box, using Formal Concept Analysis over the co-occurrence structure of previously mapped source material to propose alignment. MORK as a general-purpose mapping vocabulary, based on SKOS. 

The layers described below are one family of mapping target, but not the only possible one. The mapping mechanism itself ships inside this repository, under `mork/`, because LATTICE uses it as the reference way of populating its own layers — `mork/targets/` is a configuration that points it at LATTICE specifically.

**LATTICE (Concept Lattice of Domain Ontology Layers)** provides the semantic substrate MORK's output lands in - designed to be extended by particular subject domains in order to be used in industry-specific ways. 

**SPC (Subject-oriented Process Calculus)**  provides a formal mechanism for describing orchestration between agents (human, AI, or computational), whose data has been mapped in by MORK and whose roles, obligations, and eligibility are modelled in LATTICE. Where LATTICE's Behaviour layer models what state something is in and what can cause it to change, SPC is concerned with the live, session-typed exchange between agents that drives those changes — giving that exchange a formal contract to align to, grounded in the same ontology, rather than an ad hoc protocol. SPC has a substantial standalone ontology already authored (`spc/`), but it is not yet integrated with the layers below: it uses a placeholder namespace and declares no `projection/` contract to any of them. Treat it as a separate, pre-integration body of work rather than part of the dependency graph described below.

#### Model Layers

LATTICE is organised as seven layers, each an independent OWL/SHACL/SKOS module:

| Layer | Kind | What it models |
|---|---|---|
| **Foundation** | Substrate | Identity, versioning, provenance and evidence, governance state, temporal scoping. |
| **Vocabulary** | Substrate | The governed mechanism by which external, domain-specific concept schemes get bound into the other layers without touching their core specifications. |
| **Quantification** | Substrate | Declared value spaces, quantities, ordered values, bounds, ranges, conversion, granularity, and recurrence — the mechanism behind any magnitude, interval, or ordinal comparison the other layers need. |
| **Party** | Substrate | 	Actors, the roles they occupy, and the direction and composition of obligation between them (e.g., modelling independently capped shares, joint obligation with a right of recourse, delegated accountability, or contingent role occupancy). |
| **Eligibility** | Substrate | admissibility criteria (conditions, unresolved questions, and decisions). |
| **Behaviour** | Substrate | State, transition, trigger, and effect, including a usable `Sequential` allowance profile. `Proportional` allowance semantics and reset edge cases remain explicitly deferred. |
| **Instrument** | Applied domain ontology | A primary domain ontology built on the substrates, giving the generic shape of a governing document, e.g., Provision → Obligation → Qualifier. |

Instrument is a first layer building on the substrates. A different applied domain ontology (e.g., a device's operational lifecycle, access-control entitlement system, asset maintenance schedule, etc) could sit atop Instrument or even replace it, composing with the same Party, Eligibility, and Behaviour mechanisms through its own `projection/` contracts, without touching any of the core specifications.

Every mechanism in a layer's specification should be usable without knowing what industry or domain is consuming it. See `examples/` for the worked instances.

### Repository Layout

Each layer directory follows the same internal template, present in whole or in the parts that layer actually needs:

```
<layer>/
├── README.md
├── spec/          # normative T-box
├── shapes/
│   ├── structural.ttl    # SHACL property shapes — local, per-instance
│   ├── constraints.ttl   # SHACL-SPARQL — whole-graph conditions
│   └── rules.ttl         # SHACL-SPARQL rules that materialise derived facts
├── vocab/          # mechanism-intrinsic enumerations only, never including business vocabulary
├── projection/     # the layer's declared contracts to/from other layers
├── execution/      # generated runtime artefacts, where a layer needs one,
│                   #   plus the docs governing how they're regenerated
├── examples/       # single-layer worked examples
└── test/           # the layer's own shape and rule tests
```

Governance is deliberately separate from every layer it checks — `governance/` runs over the union graph rather than living inside any one module, enforcing scheme-contract compliance, deprecation posture, and cross-layer parity in CI.

Compiled artefacts live under `execution/`, being generated from `spec/`, `shapes/`, `vocab/`, and `projection/` by deterministic, reproducible processes or code (to be regenerated on source change per that layer's `invalidation-policy.md`).

The `tools/` folder holds reference implementations handling compilation. It's licensed separately from everything else in the tree — see [Licensing](#licensing).

---

## Repository layout

```
lattice/
├── README.md
├── LICENSE                  # MPL 2.0 — ontology artefacts, tools/
├── LICENSE-DOCS.md          # CC BY-SA 4.0 — documentation, specifications
├── CONTRIBUTING.md
│
├── foundation/              # Foundation Layers (provenance, versioning)
├── vocabulary/              # Inclusion of Domain-specific Vocabularies 
├── quantification/          # Value Spaces, Quantities, Ranges, Recurrence
├── party/                   # Parties, Roles, & Participation Modelling 
├── instrument/              # Governing Instrument (Upper Domain Ontology)  
├── eligibility/             # Eligibility Criteria Modelling 
├── behaviour/               # Behaviour Modelling 
├── mork/                    # Mapping Vocabulary
├── spc/                     # Orchestration calculus (standalone, unintegrated)
│
├── governance/              # Cross-layer governance
│   ├── scheme-contracts/
│   ├── parity/
│   └── shapes/
│
├── docs/
│   ├── architecture/
│   └── adr/
│
├── examples/                # Cross-layer composition scenarios
│   ├── employment.ttl
│   ├── lending-covenant.ttl
│   ├── saas-subscription.ttl
│   ├── clinical-trial.ttl
│   └── insure-o/            # Applied validation package for insurance-style substrate checks
│
├── test/                    # Whole-graph CI
│
└── tools/                   # Reference implementation
```

---

## How the layers interact

```
foundation
    └── vocabulary
            └── quantification
                    └── party
                            ├── eligibility
                            │       └── instrument
                            └── behaviour   (imports instrument, eligibility, party, quantification)

mork — targets any layer
spc  — standalone today; not yet imported by, or importing, any layer above
spc  — leverages domain ontology axioms to form session types once a separate integration effort defines the needed contracts
```

A few commmon compositions are worth noting:

- **Guard calls Eligibility.** A Behaviour transition's guard condition is, in the general case, an Eligibility decision: conditions, unresolved questions, and results.
- **Effects write into Instrument or Party.** A transition firing can create or modify an Obligation, or populate a Role Occupancy that was contingent until that moment.
- **Role Occupancy is itself stateful.** The same State/Trigger/Effect apparatus that governs an Obligation's status governs whether a Role is currently occupied at all — this is what allows a party who is not connected to an instrument be bound in later, by the instrument's own design.

---

## Licensing

Two licences govern the artefacts in the repository:

- **Ontology artefacts (`.ttl`) and the reference implementation (`tools/`)** — [Mozilla Public License 2.0](LICENSE). Derivative works, commercial or otherwise, are permitted with no obligation to share what you build. If you modify one of these files and redistribute the modified version, that modification carries the same licence forward.
- **Documentation and specifications (`.md`)** — [CC BY-SA 4.0](LICENSE-DOCS.md). Use freely, share modifications to the text itself under the same terms.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the licensing mechanics, the SPDX header convention, and where new content belongs within a layer.

## Development environment

Use [mise](https://mise.jdx.dev/) for repository toolchain setup and task orchestration. See [the toolchain guide](docs/developer/toolchain.md), [Windows and WSL guidance](docs/developer/windows-wsl.md), and the [Phase 0 and 1 validation handoff](docs/developer/phase-0-1-handoff.md).

For the current implementation boundaries and reading order, see the [platform implementation map](docs/architecture/implementation-map.md). Architecture decisions are indexed in [docs/adr](docs/adr/README.md).
