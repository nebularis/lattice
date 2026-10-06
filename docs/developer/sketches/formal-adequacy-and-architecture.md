<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal adequacy and architecture checks

**Unit:** [formal-methods](../plans/formal-methods.md), phase 3. **Status:** sketch, 2026-10-06.
Nothing here is ratified.
**Parent:** [formal methods](formal-methods.md) §7, which this details. Prover-neutral: each
construct is shown in Rocq and in Isabelle/HOL until FM-D1 is decided.

---

## 1. The problem

A formal theory is useful only if it describes the layer it claims to describe, and an algorithm
specified in it is useful only if it respects LATTICE's architecture. Neither holds by accident.
This sketch defines the three mechanisms that make both checkable: layer interfaces, effect
discipline and adequacy against the fixture corpus. It also defines the typed codec that adequacy
and the toolchain workers share.

## 2. Layer interfaces

Each layer's theory exposes an interface: its datatypes, its operations and its laws. An
algorithm is written against the interfaces it reads, and nothing else.

| | Rocq | Isabelle/HOL |
|---|---|---|
| Interface | a `Module Type` with types, operations and laws as `Parameter`s and `Axiom`s of the signature | a `locale` with fixed operations and assumptions |
| Algorithm | a `Module` functor over the interfaces it reads | a locale extending the interfaces it reads, or a definition inside it |
| Instantiation | applying the functor to the layer's module, which must prove the interface's laws | `interpretation`, which discharges the assumptions as proof obligations |
| Generated code | OCaml functors | code per interpretation |

```coq
(* Rocq *)
Module Type ELIGIBILITY.
  Parameter profile candidate : Type.
  Parameter decide : profile -> candidate -> k3.
  Axiom decide_monotone : (* more evidence never reverses a decided outcome *) True.
End ELIGIBILITY.
```

```isabelle
(* Isabelle/HOL *)
locale eligibility =
  fixes decide :: "'profile ⇒ 'candidate ⇒ k3"
  assumes decide_monotone: "..."
```

### 2.1 The dependency check

The theory dependency graph must equal the ontology import graph. A check reads both and fails on
any difference, in either direction:

| Difference | Meaning |
|---|---|
| a theory imports a theory whose layer the ontology does not import | the algorithm reads a layer it may not |
| an ontology import has no theory dependency | the theory is incomplete, or the import is unused |

This is the import guard (B7) applied to theories. It runs in the same `mise` task.

## 3. Effect discipline

LATTICE's rules about state and time become types in the evaluation context's monad stack
([reference evaluator sketch](reference-evaluator.md)).

| Rule | Rocq | Isabelle/HOL |
|---|---|---|
| design time never reads runtime records (B8, DP6) | a design-time computation has type `env -> A`, a Reader. It cannot name the ledger | the same, as a function from the environment. HOL has no generic monad class, so each monad is a concrete type with its own laws |
| only a lifted effect changes the ledger | `lift : computation A -> effect` is the only producer of a ledger change | the same, by the definitions exported from the locale |
| the engine never reads a clock (B3) | time is only the position in `env` | the same |
| units never mix silently | quantities indexed by value space and unit, as a dependent type | quantities with phantom unit types and a type class, as the AFP's physical quantities entry does |

The Isabelle column states the rule by construction in definitions and proves it as a theorem,
where Rocq can also make it a typing error. Both give the guarantee. Phase 0 shows which costs less.

## 4. Adequacy

### 4.1 Two directions

| Direction | Check | Fails when |
|---|---|---|
| ontology to theory | a generator reads each layer's node shapes and closed vocabularies and checks the theory's datatypes against them: a closed set of named individuals is an inductive type with the same constructors, a functional property a field, any other property a finite set | a constructor, field or set is missing or extra |
| theory to ontology | the codec decodes every fixture in the layer's README and Validation Packs. Every valid fixture must decode and satisfy the theory's laws. Every invalid fixture must fail the law its shape names | a fixture decodes when it should not, fails the wrong law, or passes a law its shape rejects |

### 4.2 The corpus

The corpus already exists: every slice's positive and negative fixtures, and every README's worked
examples. Each invalid fixture names the law it breaks, as InsurML's invalid fixtures name their
assertion. The adequacy report lists, per law, the fixtures that exercise it, so a law with no
negative fixture is visible.

### 4.3 The report

| Column | Holds |
|---|---|
| law | its IRI, such as `elg:L15` |
| shape verdict | per fixture |
| theory verdict | per fixture |
| agreement | yes, or the fixtures on which they differ |
| coverage | the number of positive and negative fixtures |

A disagreement is a defect in the shape, the theory or the fixture, and the report never decides
which. A human does.

## 5. The typed codec

One codec, generated from the theory's datatypes, serves adequacy and the toolchain workers
([toolchain workers sketch](formal-toolchain-workers.md)).

| Property | Rule |
|---|---|
| format | canonical JSON (RFC 8785 ordering), one schema per layer datatype, generated as JSON Schema |
| identity | IRIs carried as strings, never minted by the tool |
| completeness | every field of the datatype, with absent optional values explicit |
| determinism | encoding is a function of the term, so equal terms have equal bytes |
| checked | decode after encode is the identity on every corpus term, in both the Python and the generated implementations |

Python reads RDF with `rdflib`, validates it with the layer's shapes, and encodes it. The generated
tool decodes it. RDF never enters the tool.

## 6. What it costs

| Item | Estimate (tokens) |
|---|---|
| interfaces for the kernel, Foundation, Vocabulary and Quantification | 0.2M to 0.4M |
| the dependency check | under 0.1M |
| the shape-to-datatype check and the codec generator | 0.3M to 0.5M |
| adequacy over the existing corpus, first run, with fixes | 0.2M to 0.5M |

## 7. Open questions

| # | Question | Leaning |
|---|---|---|
| AD-Q1 | Generate the theory's datatypes from the shapes, or write them and check? | write and check, since generated theories are hard to prove against (parent FM-Q1) |
| AD-Q2 | Do OWL axioms with no shape need a theory counterpart? | only where an algorithm relies on them. Open-world entailment stays with OWL tooling (parent FP2) |
| AD-Q3 | Where does the codec's Python half live? | beside the layer's existing Python tooling, generated, never edited |
