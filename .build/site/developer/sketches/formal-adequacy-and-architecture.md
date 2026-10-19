<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal adequacy and architecture checks

**Unit:** [formal-methods](../plans/formal-methods.md), tracks A and E. **Status:** sketch,
2026-10-06, revised after review ([response](../notes/formal-methods-review-response.md)). Nothing
here is ratified.
**Parent:** [formal methods](formal-methods.md) §7, which this details. Prover-neutral: each
construct is shown in Rocq and in Isabelle/HOL until FM-D1 is decided.

---

## 1. The problem

A formal statement is useful only if it describes the layer it claims to describe, and an algorithm
is useful only if it respects LATTICE's architecture. Neither holds by accident, and keeping a theory
and an ontology in step is the cost most likely to decide whether the programme survives. This sketch
defines how that cost is kept low: one normative source, layer interfaces, an effect discipline,
adequacy in both directions, and one codec.

## 2. Layer interfaces

Each layer's theory exposes an interface: its datatypes, its operations and its laws. An algorithm is
written against the interfaces it reads, and nothing else.

| | Rocq | Isabelle/HOL |
|---|---|---|
| interface | a `Module Type` with types, operations and laws | a `locale` with fixed operations and assumptions |
| algorithm | a `Module` functor over the interfaces it reads | a locale extending the interfaces it reads |
| instantiation | applying the functor to a module that proves the interface's laws | `interpretation`, which discharges the assumptions |
| generated code | OCaml functors | code per interpretation |

```coq
(* Rocq. The law is a statement, never a placeholder. *)
Module Type ELIGIBILITY.
  Parameter profile candidate : Type.
  Parameter decide : profile -> candidate -> k3.
  Parameter more_evidence : candidate -> candidate -> Prop.
  Axiom decide_monotone : forall p c c',
    more_evidence c c' -> le_info (decide p c) (decide p c').
End ELIGIBILITY.
```

```isabelle
(* Isabelle/HOL *)
locale eligibility =
  fixes decide :: "'profile ⇒ 'candidate ⇒ k3"
    and more_evidence :: "'candidate ⇒ 'candidate ⇒ bool"
  assumes decide_monotone: "more_evidence c c' ⟹ le_info (decide p c) (decide p c')"
```

**Non-vacuity.** A theorem proved over an interface is relative to its assumptions, and worthless if
no instantiation discharges them. Every interface has at least one instantiation that does, and the
assurance record marks any claim over an unrealised interface as vacuous (assurance records AR6).

### 2.1 The dependency check

The theory dependency graph must equal the ontology import graph. A check reads both and fails on any
difference, in either direction, as the import guard (B7) does for imports and use.

## 3. Effect discipline

| Rule | Rocq | Isabelle/HOL |
|---|---|---|
| design time never reads runtime records (B8, DP6) | a design-time computation receives only **`DesignEnv`**. The evaluator's **`RunEnv`** extends it with positions and records. A projection `RunEnv -> DesignEnv` and a lemma show a design-time computation cannot observe anything outside `DesignEnv` | the same split, as two records with a projection. Without monad polymorphism, the guarantee is by definition plus a theorem rather than a typing error, which is weaker under refactoring and is scored in the spike |
| only a lifted effect changes the ledger | `lift : computation A -> effect` is the only producer of a ledger change | the same, by the definitions exported from the locale |
| the engine never reads a clock (B3) | time is a position in `RunEnv` only | the same |
| units never mix silently | quantities indexed by value space and unit, as a dependent type | phantom unit types and a type class, as the AFP's physical quantities entry does |

The architecture check covers the split: a field added to `DesignEnv` that holds runtime-derived
data fails CI, so the guarantee survives the environment growing.

## 4. One source, and adequacy in both directions

### 4.1 One normative source

The literate README stays the one normative source (FP1). From it the existing pipeline extracts the
spec, vocabulary and shapes. It is extended to generate, for the **structurally closed portion**, the
theory's datatypes as well: an inductive type for each closed vocabulary, a record for each node shape
over functional properties, and cardinalities as invariants. Generated datatypes are easy to prove
against. Laws are not generated: they are written in the theory, and their statements are extracted
back into the README (§6). Drift in the closed portion is then regeneration and a diff, with nothing
to adjudicate. FM-D12.

### 4.2 Theory to fixtures

| Check | Fails when |
|---|---|
| the codec decodes every fixture in the layer's README and Validation Packs | a valid fixture fails to decode |
| every valid fixture satisfies the theory's laws | a law rejects a fixture its shape accepts |
| every invalid fixture fails the law its shape names | a fixture fails the wrong law, or passes |
| where track B's reference exists, every fixture with an expected decision is decided as expected | the reference and the expectation differ |

### 4.3 The RDF round trip

Adequacy needs more than decode after encode. The check runs **graph, validated, term, encoded,
decoded, graph again**, and the two graphs must be equal after RDF Dataset Canonicalisation
(RDFC-1.0), byte for byte. A codec that drops a property the shapes permit fails here. Literal forms
(`1.0` against `1.00`, a typed boolean against a plain one), blank nodes, language tags and triple
order are all settled by the canonical form.

### 4.4 The report

| Column | Holds |
|---|---|
| law | its IRI, such as `elg:L15` |
| shape verdict, theory verdict, reference verdict | per fixture |
| agreement | yes, or the fixtures on which they differ |
| coverage | positive and negative fixtures. A law with no negative fixture is listed |

A disagreement in the hand-written part is a defect in the shape, the theory, the reference or the
fixture, and the maintainer decides which. The adjudication rate is a standing metric (epic §6).

### 4.5 Unformalised semantic commitments

An OWL axiom with semantic force, no shape and no theory counterpart is listed by name, so the gap is
visible rather than inferred. Formalising one is done only where an algorithm relies on it (FP2). The
list is the first artefact a reviewer of the programme should read.

## 5. The typed codec

One codec, generated from the theory's datatypes, serves adequacy and the toolchain workers
([toolchain workers sketch](formal-toolchain-workers.md)).

| Property | Rule |
|---|---|
| format | canonical JSON with RFC 8785 key ordering, one JSON Schema per datatype |
| **numbers** | **every quantity, rate and amount is carried as a lexical string with its value space and unit, never as a JSON number.** RFC 8785 serialises numbers as IEEE 754 binary64, which corrupts decimal fractions and integers beyond 2⁵³. JSON numbers are used only for small counts and indices |
| identity | IRIs carried as strings, never minted by a tool |
| completeness | every field of the datatype, with absent optional values explicit |
| determinism | encoding is a function of the term |
| binary form | where payloads are large, CBOR with RFC 8949 deterministic encoding and decimal-fraction tags, proved equivalent to the JSON form on every corpus term |
| versioning | the codec's schema digest travels in every job envelope, and a worker refuses a tool built for another |

Python reads RDF with `rdflib`, validates it with the layer's shapes and encodes it. The generated or
hand-written tool decodes it. RDF never enters the tool.

## 6. Statements in the README

Each formal statement is short, named and extracted into the layer's README beside the law's prose
and its shape, by the literate pipeline. Prose, shape and statement drift then become one check, and
the semantics stays reviewable by people who do not read proofs. **Statements are reviewed. Proof
bodies are treated as opaque**, accepted on the prover's kernel and the assumption audit (assurance
records AR5). That is the trust model for agent-drafted proofs, and it is written down so that a long
generated proof does not raise the question of whether anyone reviewed it.

## 7. What it costs

| Item | Estimate (tokens) |
|---|---|
| the README generator for the closed portion, the kernel, Foundation, Vocabulary and Quantification | 0.3M to 0.5M |
| the dependency and environment checks | under 0.1M |
| the codec generator and the RDF round trip | 0.3M to 0.5M |
| adequacy over the existing corpus, first run, with fixes | 0.2M to 0.5M |

## 8. Open questions

| # | Question | Leaning |
|---|---|---|
| AD-Q1 | Which direction generates the closed portion? | from the README to both shapes and theory datatypes (§4.1, FM-D12). The review's proposal, shapes from the theory, is set aside because it would move normativity into the theory |
| AD-Q2 | Do OWL axioms with no shape need a theory counterpart? | only where an algorithm relies on them, with the rest listed (§4.5) |
| AD-Q3 | Where does the codec's Python half live? | beside the layer's Python tooling, generated, never edited |
