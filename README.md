# LATTICE

A domain-neutral semantic framework for representing governing instruments — contracts, protocols, agreements, and the obligations, eligibility conditions, and lifecycle behaviour they define — as structured, queryable, versioned graphs.

---

## What LATTICE is

### From an ontological perspective

The core move is reification: taking the structure of a governing document, the actors and roles bound to it, the conditions that gate a decision, and the states those things move through, and turning each into a first-class individual in a graph rather than a flat field or a paragraph of prose. Once something is reified, it can be queried, versioned, validated, and reasoned over.

LATTICE is organised as seven layers, each an independent OWL/SHACL/SKOS module:

| Layer | What it models |
|---|---|
| **Foundation** | Identity, versioning, provenance and evidence, governance state, temporal scoping. Imported by everything else. |
| **Vocabulary** | Not vocabulary content itself — the governed mechanism by which external, domain-specific concept schemes get bound into the other layers without touching their core specifications. |
| **Party** | Actors, the roles they occupy, and the direction and composition of liability between them — several liability, joint-and-several liability, delegated accountability, and contingent role occupancy are all instances of the same small set of primitives. |
| **Instrument** | The generic shape of a governing document: Provision → Obligation → Qualifier. |
| **Eligibility** | Compiling admissibility criteria — conditions, unresolved questions, a decision — from natural-language business rules into a testable shape. |
| **Behaviour** | State, transition, trigger, guard, and effect, layered over Instrument and Party. |
| **Mapping (MORK)** | Compiles external schemas and natural-language source material onto any of the above. Targets the other layers rather than sitting in their dependency chain. |

Every mechanism in Foundation through Behaviour has been tested against worked examples with no shared domain — an employment contract, a secured lending covenant, a SaaS subscription agreement, and a clinical trial protocol all exercise the same seven core mechanisms in Behaviour (State, State space, Trigger, Guard, Effect, Authority, Reversibility) without modification. That cross-domain validation is a design discipline, not an afterthought: nothing in a layer's specification should require knowing what industry is consuming it. See `examples/` for the worked instances.

### From a software engineering perspective

Each layer directory follows the same internal template, present in whole or in the parts that layer actually needs:

```
<layer>/
├── README.md
├── spec/          # the normative T-box
├── shapes/
│   ├── structural.ttl    # SHACL property shapes — local, per-instance
│   ├── constraints.ttl   # SHACL-SPARQL — whole-graph conditions
│   └── rules.ttl         # SHACL-SPARQL rules that materialise derived facts
├── vocab/          # mechanism-intrinsic enumerations only, never business
│                   #   vocabulary — see the note on `vocabulary/` above
├── projection/     # this layer's declared contracts to/from other layers
├── execution/      # generated runtime artefacts, where a layer needs one,
│                   #   plus the docs governing how they're regenerated
├── examples/       # single-layer worked examples
└── test/           # that layer's own shape and rule tests
```

Governance is deliberately separate from every layer it checks — `governance/` runs over the union graph rather than living inside any one module, enforcing scheme-contract compliance, deprecation posture, and cross-layer parity in CI.

Anything under `execution/` is a compiled artefact, never hand-authored, produced from `spec/`, `shapes/`, `vocab/`, and `projection/` by a deterministic, reproducible process — regenerated on source change per that layer's `invalidation-policy.md`, never hand-edited in place.

`tools/` holds the reference implementation that does that compilation. It's licensed separately from everything else in the tree — see [Licensing](#licensing).

---

## Repository layout

```
lattice/
├── README.md
├── LICENSE                 # MPL 2.0 — ontology artefacts, tools/
├── LICENSE-DOCS.md          # CC BY-SA 4.0 — documentation, specifications
├── CONTRIBUTING.md
│
├── foundation/
├── vocabulary/
├── party/
├── instrument/
├── eligibility/
├── behaviour/
├── mork/                    # Mapping — kept as its own established name
│
├── governance/              # cross-layer, runs over the union graph
│   ├── scheme-contracts/
│   ├── parity/
│   └── shapes/
│
├── docs/
│   ├── architecture/
│   └── adr/
│
├── examples/                # cross-layer composition scenarios
│   ├── employment.ttl
│   ├── lending-covenant.ttl
│   ├── saas-subscription.ttl
│   └── clinical-trial.ttl
│
├── test/                    # whole-graph CI
│
└── tools/                   # reference implementation
```

---

## How the layers interact

```
foundation
    └── vocabulary
            └── party
                    ├── instrument
                    ├── eligibility
                    └── behaviour   (imports instrument, eligibility, party)

mork — targets any of the above; not part of their import chain
```

Foundation sits underneath everything because provenance and versioning are its job wherever they're needed — nothing above it reimplements history-tracking; Behaviour's transitions are recorded through Foundation's existing evidence mechanism rather than a parallel one. Vocabulary sits directly above Foundation because the inclusion mechanism has to exist before any other layer's enumerations can be declared open to substitution. Party sits below Instrument, Eligibility and Behaviour rather than inside any one of them, because all three reference it directly: Instrument's obligations carry a directional obligor and obligee through a Role Occupancy, Eligibility can test a specific occupancy's standing as a Guard, and Behaviour can populate a contingent occupancy as an Effect.

A few compositions recur across every worked example and are treated as load-bearing rather than incidental:

- **Guard calls Eligibility.** A Behaviour transition's guard condition is, in the general case, an Eligibility decision — conditions, unresolved questions, a result — reused rather than reimplemented.
- **Effect writes into Instrument or Party.** A transition firing can create or modify an Obligation, or populate a Role Occupancy that was contingent until that moment.
- **Role Occupancy is itself stateful.** The same State/Trigger/Effect apparatus that governs an Obligation's status governs whether a Role is currently occupied at all — this is what lets a beneficiary or claimant who isn't a party to an instrument at the outset be bound in later, by the instrument's own design.

MORK's relationship to the rest of the stack is different in kind. It doesn't get imported by the other layers; it targets them, compiling external schemas and natural-language source material onto whichever layer's T-box a given mapping run is aimed at.

---

## Status

Foundation through Behaviour are under active specification. MORK's existing content predates the shared per-layer template and is being migrated into it as a separate pass. The reference implementation in `tools/` — the compiler that produces `execution/` artefacts from source layers — has not yet been built.

---

## Licensing

Two licences, split by content type, not by directory ownership:

- **Ontology artefacts (`.ttl`) and the reference implementation (`tools/`)** — [Mozilla Public License 2.0](LICENSE). Build anything on this, commercially or otherwise, with no obligation to share what you build. If you modify one of these files and redistribute the modified version, that modification carries the same licence forward.
- **Documentation and specifications (`.md`)** — [CC BY-SA 4.0](LICENSE-DOCS.md). Same shape: use freely, share modifications to the text itself under the same terms.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how this is applied per file.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the licensing mechanics, the SPDX header convention, and where new content belongs within a layer.
