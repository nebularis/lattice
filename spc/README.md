<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# SPC — Subject-oriented Process Calculus

SPC is the orchestration layer that sits alongside LATTICE's domain modelling layers. Where LATTICE models parties, obligations, eligibility, and behaviour state, SPC models the session-typed exchange between subjects that drives those states forward.

In this repository, SPC is currently centred on the ontology in `spec/spc.ttl`. The surrounding `shapes/`, `vocab/`, `projection/`, `execution/`, `examples/`, and `test/` directories reserve the same layer structure used elsewhere in LATTICE, but are not yet populated.

---

## 1. Purpose and Scope

The SPC layer captures the structural parts of a subject-oriented process calculus in RDF/OWL so they can be described, queried, and related to the rest of the LATTICE model.

The current ontology covers:

- value sorts, including base, product, sum, and recursive sorts
- subject behaviours such as send, receive, do, choice, conditional, recursion, and call
- global and local session types, including branching, projection, parallel composition, and duality
- runtime configurations, message pools, interfaces, and open subject systems
- typing assertions for behaviours and configurations
- the bridge from SPC refinements into imported OWL domain ontologies
- reified reduction steps, reduction rules, and selected metatheoretic constraints

This keeps protocol structure inside SPC while leaving business vocabulary and domain axioms in imported ontologies.

## 2. Repository Layout

```text
spc/
├── README.md
├── spec/
│   └── spc.ttl              # Current SPC ontology
├── shapes/
│   ├── structural.ttl       # Reserved for SHACL property shapes
│   ├── constraints.ttl      # Reserved for whole-graph constraints
│   └── rules.ttl            # Reserved for derived facts and materialisation rules
├── vocab/
│   └── spc-vocab.ttl        # Reserved for SPC-intrinsic named individuals
├── projection/              # Reserved for declared contracts to other layers
├── execution/
│   ├── manifest.ttl         # Reserved for generated/runtime artefacts
│   ├── benchmark-pack.md
│   ├── invalidation-policy.md
│   └── split-plan.md
├── examples/                # Reserved for worked SPC examples
└── test/                    # Reserved for layer-local validation
```

## 3. What `spec/spc.ttl` Defines

### Core structural vocabulary

The ontology starts by defining the basic identifiers SPC needs to talk about subjects, labels, variables, expressions, protocol names, and runtime values.

### Sorts

`spc:Sort` is partitioned into `BaseSort`, `ProductSort`, `SumSort`, and `RecursiveSort`. The ontology provides named base sorts for `unit`, `bool`, `int`, and `string`, and uses qualified cardinalities to enforce structural exactness for composite sorts.

### Behaviours

`spc:Behavior` is partitioned into the expected process constructs, including send, receive, do, choice, conditional, recursive binders, recursion variables, calls, and termination. Receive branches are reified so labels, variables, and bodies can be constrained explicitly.

### Session types

The ontology models both global and local session types.

- **Global types** capture participant-to-participant communication, message options, recursion, and parallel composition.
- **Local types** capture per-participant views as input and output protocols, with reified options and an explicit `dualOf` relation.
- **Projection** is represented through `spc:ProjectionAssertion`, linking a global type, a participant, and the resulting local type.

Participant propagation is modelled with property chains so the participants of continuations and parallel components remain queryable from the enclosing global type.

### Runtime configurations and open systems

The ontology includes runtime configuration structures such as actor mappings, actor states, message pools, in-transit messages, and receptionist sets. It also defines interfaces, typed ports, internal subjects, wiring entries, and `spc:OpenSubjectSystem` so protocols can be described as typed, externally visible systems rather than only as isolated behaviours.

### Domain bridge and refinement layer

`spc:Predicate` and its subclasses provide the refinement side of the model. `spc:OntologyBridge` links SPC to imported OWL ontologies through sort-to-concept and value-to-individual mappings, letting session types carry domain-grounded predicates without moving domain semantics into SPC itself.

### Operational and metatheoretic structures

The ontology reifies reduction steps, actions, reduction rules, and global type reductions. It also introduces markers for deadlock approximation and type preservation, making those concerns visible in the model even where full checking must happen outside OWL.

## 4. Design Posture

The current SPC ontology follows a few clear design commitments.

- The structural layer targets **OWL 2 DL**, using qualified cardinalities, keys, and property chains where needed.
- The domain refinement side is intended to stay in a more tractable fragment, noted in the file as **EL++** plus arithmetic-style constraints.
- Several important invariants are only partially representable in OWL and are therefore left to external validation, including recursion contractiveness, binder matching, parallel participant disjointness, duality involution, full deadlock detection, and full subject-reduction checking.
- The namespace in `spec/spc.ttl` is currently the provisional `http://example.org/spc#`, which signals that namespace harmonisation with the rest of LATTICE is still pending.

## 5. Relationship to LATTICE

SPC is where protocol structure meets the ontologies LATTICE already uses for domain meaning.

- LATTICE provides the domain concepts, roles, obligations, eligibility conditions, and stateful entities that a subject system may talk about.
- SPC provides the typed interaction structure that governs how those subjects exchange values and coordinate work.
- The ontology bridge allows SPC refinements to refer to imported OWL concepts and roles, so process constraints can stay aligned with the same semantic substrate used elsewhere in the repository.

## 6. Current Status

At present, `spec/spc.ttl` is the only populated SPC artefact in this repository. The empty `shapes/`, `vocab/`, `projection/`, `execution/`, `examples/`, and `test/` locations mark the intended structure for the rest of the layer once validation rules, derived vocabularies, compiled artefacts, and worked examples are added.
