<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal methods in LATTICE: specification, verification and generated code

**Unit:** [formal-methods](../plans/formal-methods.md) (epic). **Status:** sketch, 2026-10-06. Nothing here
is ratified. A new directory, a new vocabulary and any change to the toolchain each need an ADR.
**Prover:** open (FM-D1). This sketch's examples use Rocq. The plan's prover spike (track D) compares Rocq and
Isabelle/HOL before anything else is built, and the smaller sketches are written prover-neutral.
**Reviewed:** 2026-10-06. Dispositions and rebuttals are in the
[review response](../notes/formal-methods-review-response.md), and this sketch is revised to match.
**Reviewed again:** 2026-10-08, an implementation-level review of the evidence tracks B, C and E
had produced by then. Dispositions in
[this response](../notes/formal-methods-more-feedback-response.md); queued corrective slices are
recorded in the affected tracks' own plans and status records, not restated here.
**Smaller sketches:** [adequacy and architecture](formal-adequacy-and-architecture.md),
[assurance records](assurance-records.md), [instrument assurance](instrument-assurance.md),
[reference evaluator](reference-evaluator.md), [toolchain workers](formal-toolchain-workers.md).
**Reads with:** the [evaluation context sketch](evaluation-context.md) (the monadic evaluator),
the [nested states sketch](nested-states-and-history.md) (Behaviour's reference semantics), the
[logic encodings note](../notes/logic-encodings.md) and the
[logic encoding research](logic-encoding-research.md) (Datalog as reference semantics), the
[assembly interface sketch](wording-assembly-interface.md), and the engine notes in
[`notes/rdf-engine/`](../notes/rdf-engine/), whose formal methods sections this paper generalises:
[compiled persistence profiles](../notes/rdf-engine/compiled-persistence-profiles.md) §3 and §14,
and the [lock-free store](../notes/rdf-engine/lock-free-rdf-store.md) Appendix A.

---

## Contents

1. [Premise and goals](#1-premise-and-goals)
2. [What correct means in LATTICE](#2-what-correct-means-in-lattice)
3. [What LATTICE already has, and what it lacks](#3-what-lattice-already-has-and-what-it-lacks)
4. [Errors a formal model would have found earlier](#4-errors-a-formal-model-would-have-found-earlier)
5. [The techniques, by cost](#5-the-techniques-by-cost)
6. [The shape of the formal stack](#6-the-shape-of-the-formal-stack)
7. [Plugging a specification into the architecture](#7-plugging-a-specification-into-the-architecture)
8. [Layer by layer](#8-layer-by-layer)
9. [The monadic evaluator, specified and extracted](#9-the-monadic-evaluator-specified-and-extracted)
10. [Category theory as a design language](#10-category-theory-as-a-design-language)
11. [Guaranteeing the behaviour of instruments](#11-guaranteeing-the-behaviour-of-instruments)
12. [From specification to code](#12-from-specification-to-code)
13. [The compilation toolchains](#13-the-compilation-toolchains)
14. [The development lifecycle](#14-the-development-lifecycle)
15. [Tools](#15-tools)
16. [Where it lives](#16-where-it-lives)
17. [A phased route](#17-a-phased-route)
18. [Risks](#18-risks)
19. [Decisions for the maintainer](#19-decisions-for-the-maintainer)
20. [Open questions](#20-open-questions)

---

## 1. Premise and goals

LATTICE states its semantics in prose, in OWL axioms, in SHACL shapes and in law registers, and
checks them against examples. That has served the layers well, but it has a limit. A shape checks
that data satisfies a law. It says nothing about whether an algorithm always produces data that
satisfies it, whether two backends always agree, or whether an instrument always behaves as its
drafters intend. Each of those is a claim about every input, and examples cannot establish it.

The engine notes in `notes/rdf-engine/` already chose formal methods for one target, a proved
planner for a custom engine, with Rocq extracted to OCaml and a separately checked emitter to Rust.
This paper widens the scope to the whole of LATTICE: its models, its algorithms, its compilers, its
development lifecycle, and the instruments adopters build on it.

| # | Goal | Priority |
|---|---|---|
| G1 | **Validate the correctness of every model and algorithm LATTICE specifies**, before and after it is implemented | primary |
| G2 | **Guarantee the behaviour of instruments** to adopters: properties that hold for every instrument, for every use of a template, and for one instrument as configured | primary, built on G1 |
| G3 | **Check an algorithm against LATTICE's architecture**: its layer dependencies, its design-time and runtime separation, its determinism | primary, built on G1 |
| G4 | **Generate code reliably** from specifications, through OCaml and on to the languages and execution surfaces LATTICE targets | secondary |
| G5 | **Keep the cost proportional**: formal effort where it pays, cheap techniques everywhere else, nothing that blocks a slice that does not need it | constraint |

## 2. What correct means in LATTICE

Three kinds of artefact need three kinds of correctness.

| Artefact | Examples | Correct means |
|---|---|---|
| **Models** | each layer's T-Box, vocabularies, shapes and laws. An applied module. An adopter's configuration | consistent (it has a model), adequate (it admits exactly the intended data), its laws jointly satisfiable and independent of accidents of encoding |
| **Algorithms** | binding resolution, three-valued evaluation, match strategies, assembly, regime macrosteps, evaluation passes, projections, compilers, persistence planning, minting | total and deterministic where stated, preserving every law of its inputs in its outputs, agreeing with every other realisation of the same semantics |
| **Instruments** | one contract as configured: its relations, triggers, regimes, amounts, templates | behaving as its drafters intend over every sequence of events: invariants hold, deadlines close, no relation arises in a state that gates it, no breach rests on what was never established |

The properties fall into families that recur across the layers:

| Family | Statement | Where it recurs |
|---|---|---|
| Consistency | the axioms and laws have a model | every T-Box, every applied module |
| Adequacy | the formal model and the shapes accept the same data | every layer with a literate README |
| Determinism | equal inputs give equal outputs | binding resolution, assembly (WA5), passes (B3), compilers (ADR-A19), minting |
| Law preservation | an algorithm's output satisfies the laws its specification promises | assembly (W3 to W6), macrosteps (B9 to B11), projections (X1 to X6) |
| Refinement and parity | an implementation, or a compiled artefact, means what the specification means | compilers, backends (ADR-A28), the InsurML adapters, persistence plans |
| Monotonicity in information | more evidence never reverses a decided outcome | Eligibility, Quantification comparisons, Instrument breach (I7) |
| Stratification and termination | evaluation is well founded and ends | Instrument (I6, I12), Behaviour (B10), Datalog backends |
| Temporal properties | something always holds, or eventually happens, over a run | regimes, windows, ledgers, every instrument |
| Conservativity | a derived view adds no meaning | Surface (X1), Persistence, the lift from InsurML |

## 3. What LATTICE already has, and what it lacks

**Formal in all but name.**

| Exists | What it gives | Limit |
|---|---|---|
| OWL 2 DL axioms, checked by a reasoner in the test-only harness (ADR-A83) | consistency of each T-Box and its examples | checks the ontologies, not the algorithms over them |
| SHACL and SHACL-SPARQL law shapes per layer | each law checked on data | a check per graph, not a guarantee for every graph an algorithm can produce |
| Positive and negative examples, mutation and adversarial probes in Validation Packs | evidence that a shape rejects what it should | as strong as the examples chosen |
| The parity gate (ADR-A28) | backends agree on fixtures | agreement with each other, not with a reference, and only on fixtures |
| Design-time OWL classes (ADR-A90) and satisfiability (CCS C13a) | widening, narrowing and joint satisfiability of criteria | the reasoner's answer is trusted. No proof the encoding is faithful |
| Strong Kleene semantics, stratification, determinism (B3), design time never reading runtime (B8, DP6) | precise statements in prose | not mechanised, so a change can break one silently |
| The Datalog reference semantics recommended in the logic encodings note | a candidate definitional semantics | not written as a checked artefact |
| SPC's metatheory claims (subject reduction, deadlock freedom, session fidelity) | stated properties of protocols | asserted, not mechanised |
| Literate extraction and drift checks | README and source agree | the prose is not checked against the semantics |

**What is missing.**

| Gap | Effect |
|---|---|
| no executable reference semantics for any layer | backends can only be compared with each other, and a shared misreading passes the parity gate |
| no proofs about algorithms | an algorithm can break a law for inputs no example covers |
| no checking of temporal properties | an instrument's behaviour over time is shown by traces, never established |
| no link from a law to the evidence that it holds | nobody can say which laws are proved, which are model-checked and which are only shape-checked |
| no architectural rules checked on algorithms | B7 checks imports, but nothing checks that a design-time computation cannot read the ledger |
| no generated code | every backend is written by hand, and every one is a new chance to misread the semantics |

## 4. Errors a formal model would have found earlier

Each of these was found during CCS or the InsurML alignment by building, testing or analysing.
Each is the kind of error a small formal model finds before any code exists.

| Found | What happened | Technique that finds it first |
|---|---|---|
| TD-17 (CCS C7a) | functional properties plus `owl:hasValue` axioms let a reasoner infer that two Behaviour policies are the same individual when a value is mis-stated, so the error surfaces far from its cause | a model finder (Alloy, or an OWL reasoner run over generated instances) asked for a model in which two named policies are equal |
| HQ-4 (CCS C7b) | two unscoped scheme bindings for one contract conflict, so a deployment cannot bind context roles from several sources | a specification of binding resolution with the property "every role a layer needs resolves", checked over generated deployments |
| The union scheme (typing sketch §6.1) | the analysis proposed putting InsurML concepts in a second scheme, which InsurML's own shape forbids | the two standards' constraints conjoined in one model, checked for satisfiability |
| W1 against reuse (bridge sketch §8) | one parent per element blocks InsurML's reuse of one component in many contracts | a model of both assembly semantics, with the property "every InsurML manifest has a Wording image" |
| TD-11 (Surface shapes) | Surface's shapes never ran under a SHACL engine | an adequacy check that runs every law's formal statement and its shape over the same corpus |

None of these was costly once found. Each was found late, by someone looking in the right place.
None of them needed a proof assistant: four are design-time models and one is the adequacy harness.
The case for the prover is different in kind, and §5.1 makes it.

## 5. The techniques, by cost

The ladder of the lock-free store note's Appendix A, applied to LATTICE as a whole. Each rung is
used where it pays, and the cheap rungs apply everywhere.

| Rung | Technique | Finds | Cost | LATTICE targets |
|---|---|---|---|---|
| T0 | **Executable reference semantics**: a small definitional interpreter per layer | disagreement between backends and the meaning | low to medium | the oracle for parity, for compilers, for the InsurML adapters |
| T1 | **Property-based and metamorphic tests**, with generators derived from the shapes | law breaks, order dependence | low | every algorithm, every compiler, every lift |
| T2 | **Model finding** (Alloy 6) | inconsistent or underconstrained models, with counterexamples | low | new T-Box designs, law sets, cross-standard constraints |
| T3 | **SMT solving** (Z3, cvc5) | satisfiability, overlap, exhaustiveness, widening, with witnesses | low to medium | Eligibility conditions, slot exclusivity (C13a), clash detection (NRS N3), range sets |
| T4 | **Model checking** (TLA+ with TLC or Apalache, Quint), with inductive invariants before bounded exploration. No timed automata: durations are integer constraints over positions | temporal property violations, with traces | medium | regimes, windows, ledgers, instruments, platform protocols, **Persistence's generated-operation protocols (track H, first use of this rung, 2026-10-08)** |
| T5 | **Mechanised semantics and proof** (Rocq) | errors in specifications and algorithms, for all inputs | high | the logic kernel, binding resolution, Eligibility, the evaluation context, Behaviour macrosteps, compilers |
| T6 | **Verified code generation** (extraction, verified printers) | translation errors | high | the reference evaluator, compilers to query surfaces |
| T7 | **Runtime verification**: monitors generated from properties | violations in production, as they happen | low once T4 properties exist | live instruments |

Two cheap checks of the laws themselves belong to T2 and T3 and come first: **joint satisfiability**
(a model of all of a layer's laws exists), **independence** (for each law, a model of all the others
in which it fails, which shows it has content) and **non-vacuity** (a model in which each law's
antecedent is met). They need no theory beyond the laws, and they are track A's first deliverables.

### 5.1 Where the proof assistant earns its cost

Most of §8 is reachable by T0 to T4. The prover is justified where only a proof gives the claim:

| Claim | Why nothing cheaper gives it |
|---|---|
| a compiler's output means what its input means, for every input (§8.4) | tests and parity cover fixtures. Only a proof covers every input |
| a guarantee about every instrument (§11.1), stated to a regulator or a market body | it is universally quantified, so it is a proof obligation by definition |
| a template's guarantee for every binding of its parameters, under its rely conditions (§11.2) | model checking covers one binding at a time |
| the combinator algebra, with rounding and residual allocation (§9.2) | the arithmetic is where a tested property is most likely to be quietly weaker than its prose |
| the logic kernel and binding resolution (§8.1, §8.2) | small, stable, and every later theory rests on them |

That is the prover programme (plan track E). Everything else stays at T0 to T4 unless a measured need
appears, and Behaviour and Instrument stay there until those layers settle (FR2).

## 6. The shape of the formal stack

```mermaid
flowchart TB
    subgraph SPEC["Specification (the prover, FM-D1)"]
        K["Logic kernel<br/>three values, information order,<br/>exact arithmetic, time"]
        LF["Layer theories<br/>Foundation, Vocabulary, Quantification,<br/>Party, Eligibility, Wording, Behaviour,<br/>Instrument, Surface"]
        EC["Evaluation context<br/>monad stack, combinators,<br/>environments"]
        AR["Architecture theory<br/>layer interfaces,<br/>effect discipline"]
        TH["Theorems<br/>laws, refinement,<br/>template properties"]
        K --> LF --> EC
        AR --> LF
        LF --> TH
        EC --> TH
    end
    subgraph LIGHT["Lightweight models"]
        AL["Alloy: model designs"]
        SM["SMT: decision procedures"]
        TL["TLA+ or Quint: temporal properties"]
    end
    subgraph GEN["Generated"]
        OC["Extracted OCaml<br/>reference evaluator,<br/>compiler cores"]
        WA["WebAssembly, JavaScript"]
        QS["SPARQL, SQL, Datalog<br/>from verified printers"]
    end
    subgraph LAT["LATTICE as built"]
        ONT["Ontologies, shapes,<br/>law registers"]
        TOOLS["Python compilers,<br/>Java platform, apps"]
        RUN["Runtime evaluator,<br/>query services"]
    end
    LF <-. "adequacy:<br/>same corpus" .-> ONT
    TH --> OC --> WA
    TH --> QS
    OC -. "oracle for<br/>differential tests" .-> TOOLS
    WA --> RUN
    QS --> RUN
    LIGHT -. "counterexamples<br/>before design is fixed" .-> SPEC
```

Four principles hold the stack together.

| # | Principle |
|---|---|
| FP1 | **One normative source.** The literate README stays normative. Shapes and the theory's closed datatypes are generated from it. Laws in the theory are hand-written, and their statements are extracted back into it. Adequacy keeps the rest in step (§7.3) |
| FP2 | **Closed, validated configurations are the formal domain.** A Rocq datatype is closed-world. OWL is open-world. The formal model covers configurations after SHACL validation and compilation, which is where LATTICE already compiles rather than interprets (DP5). Open-world reasoning stays with the OWL tooling |
| FP3 | **Every claim of assurance names its method, scope, bound and assumptions**, and every statement about assurance is generated from the record (§7.4) |
| FP4 | **Statements are reviewed, proofs are opaque.** A statement is short, named and in the README. A proof body is accepted on the prover's kernel and an assumption audit, so an agent-drafted proof needs no line-by-line review |

## 7. Plugging a specification into the architecture

The request is for a mechanism through which an algorithm can be formally defined and checked
against LATTICE's architecture with little ceremony. Four pieces make it.

### 7.1 Layer interfaces as module types

Each layer becomes a Rocq module type: its datatypes (from its classes and closed vocabularies),
its operations (the algorithms its README specifies) and its laws (as propositions). A layer's
module may depend only on the module types of the layers it imports, so the Rocq dependency graph
must equal the ontology import graph. A check compares the two, as the import guard (B7) compares
imports with use today.

An algorithm is then a Rocq functor over the interfaces it reads:

```coq
(* Sketch. An assembler reads Wording and Eligibility, and nothing above them. *)
Module Type WORDING.  (* forms, elements, inclusion modes, the assembly record, laws W1 to W8 *) End WORDING.
Module Type ELIGIBILITY. (* conditions, profiles, decide : Profile -> Candidate -> K3 *) End ELIGIBILITY.

Module Assembler (W : WORDING) (E : ELIGIBILITY).
  (* assemble : Form -> Settings -> Model -> Outcome Record *)
  (* Theorem assemble_satisfies_W3_W6 : ... *)
End Assembler.
```

Reading a layer the functor does not take is a type error. That is G3 for dependencies, at no cost
beyond writing the functor's signature.

### 7.2 Effects as types

LATTICE's architectural rules about time and state become typing rules over the evaluation
context's monad stack (§9):

| Rule | Typing |
|---|---|
| B8, DP6: design time never reads runtime records | a design-time computation receives only `DesignEnv`. The evaluator's `RunEnv` extends it with positions and records, and a lemma shows a design-time computation observes nothing outside `DesignEnv`. The architecture check fails a runtime-derived field added to `DesignEnv` |
| only a lifted effect changes the ledger (evaluation context §6) | only `lift : Computation A -> Effect` produces `State Ledger` |
| B3: the engine never reads a clock | time enters only as a position in `RunEnv` |
| WA4: assembly reads the form, settings and choices only | the assembler's monad carries no runtime component |
| units never change silently | quantities are indexed by value space and unit, so adding two in different units does not typecheck without `convert` |

### 7.3 Adequacy against the ontology

Detailed in the [adequacy and architecture sketch](formal-adequacy-and-architecture.md). In short:

| Check | Rule |
|---|---|
| one source | the closed portion of the theory (datatypes for closed vocabularies and node shapes) is generated from the literate README, as the shapes are, so its drift is regeneration and a diff |
| theory to fixtures | every valid fixture decodes and satisfies the laws. Every invalid fixture fails the law its shape names |
| the RDF round trip | graph, term, graph again, equal after RDFC-1.0 canonicalisation, so a codec cannot silently drop what the shapes permit |
| unformalised commitments | OWL axioms with semantic force and no shape or theory counterpart are listed by name |

The corpus is every slice's positive and negative fixtures, which LATTICE already maintains. A law
with no negative fixture is listed.

### 7.4 Laws linked to their evidence

Each layer's laws are already named individuals (`elg:L1` to `elg:L16`, and the registers W1 to
W8, B1 to B11, I1 to I18, X1 to X6). A claim about a law is a record, profiled from W3C EARL, PROV-O,
SHACL validation reports and in-toto, and detailed in the [assurance records
sketch](assurance-records.md). Its identity is the law and the **digest of the statement**, never
the statement's name, so a weakened lemma under an old name cannot pass the gate. It records its
method and scope, its assumptions, the assumption audit of a proof, the model and abstraction of a
model check, and its assertor.

A report over these records answers which laws are proved, which are checked and to what bound, and
which only by shapes. The report is a derived artefact of each release (ADR-A92), and the release
gate refuses an unreviewed restatement, an unexplained fall in level, and any failed claim.

## 8. Layer by layer

What each layer needs, and which rung earns it (§5.1):

| Layer | T0 to T4 | Proof (track E) |
|---|---|---|
| kernel | property tests of the connectives | monotonicity, De Morgan, negation, the rounding and residual theorem |
| Foundation, Vocabulary | Alloy model of binding resolution with scheme composition | binding resolution |
| Quantification | SMT for range sets, the reference as oracle | range set normal forms |
| Eligibility | the reference, differential tests of every backend | the denotation and one compiler core |
| Wording, assembly | property tests of the assembly laws, parity as a test | parity for the shared fragment, later |
| Behaviour, Instrument | the reference evaluator, conformance kits, model checks | after these layers settle, starting with I7 once C13 is specified |
| Surface, MORK | property tests of regeneration, lattice laws, MCN's round trip | conservativity under composition, later |
| Persistence | **its own track, H**: static hygiene, a typed IR, a specification registry, exhaustive cross-axis validation, and this epic's first protocol models (TLA+/Quint, rung T4), producing a capability × strategy guarantee matrix. See [the track H sketches](formal-methods-track-h.md) | the resolver's determinism/locality/monotonicity, identity-law injectivity, outcome-classification soundness (track H's H6) |

### 8.1 The logic kernel

| Specify | Prove |
|---|---|
| `k3`, with the values Permitted, Denied and Undetermined, strong Kleene connectives, the information order (Undetermined below both decided values) | the connectives are monotone in the information order. De Morgan holds. Negation swaps decided values and fixes Undetermined (L16) |
| exact decimal arithmetic with explicit rounding and residual allocation | `split` and `proRata` conserve the whole under the declared rule. Every partial operation (division, conversion without a context) returns Undetermined or Denied with a reason, never an exception |
| positions as a total order from the stimulus log | no operation reads anything but positions |

Monotonicity is a property adopters rely on directly, so it must be stated precisely: **as
evidence grows, a decided outcome is never reversed.** It covers information increase, Undetermined
becoming decided. It does not cover revision: evidence corrected, withdrawn or superseded may
legitimately change Permitted to Denied. What retraction does to downstream records is a design
question the formal work must settle with Foundation's supersession and Instrument's breach records.
The first non-trivial kernel theorem is the rounding and residual one, since it is the most likely to
fail.

```coq
Inductive k3 := Permitted | Denied | Undetermined.

Definition le_info (a b : k3) : Prop := a = Undetermined \/ a = b.

Definition and3 (a b : k3) : k3 :=
  match a, b with
  | Denied, _ | _, Denied => Denied
  | Permitted, Permitted => Permitted
  | _, _ => Undetermined
  end.

Theorem and3_monotone : forall a a' b b',
  le_info a a' -> le_info b b' -> le_info (and3 a b) (and3 a' b').
(* Proof by case analysis on a and b. Omitted in this sketch. *)
```

### 8.2 Foundation and Vocabulary

| Specify | Prove |
|---|---|
| versions, identities, supersession, keys and key schemes | supersession is acyclic and functional. A key value names at most one identity in a scheme at a time |
| scheme contracts, bindings, scopes, validity periods, precedence (ADR-A85) | resolution is a function of context and time. A conflict is reported exactly when two applicable bindings are maximal. A resolved record never changes when later bindings are added (no retroactive re-resolution) |
| scheme composition, if IMA-D4a goes ahead | the composed membership and hierarchy are the unions, and resolution stays a function |

Binding resolution is small, central and already precisely stated. It is modelled first in Alloy,
with scheme composition, ahead of CCS C8 (HQ-4, IMA-D4a), and proved in track E.

### 8.3 Quantification

| Specify | Prove |
|---|---|
| value spaces with order and density kinds, units, conversions with contexts | conversion composes and round-trips where the space declares it, and never runs without a context (ADR-A95) |
| bounds, ranges and range sets | every range set has one normal form. Containment, overlap and union decided on normal forms agree with the set semantics |
| unresolved and context values (ADR-A115) | a comparison with an unresolved value is Undetermined, and resolving it gives a decided value consistent with the Undetermined it replaced (monotonicity, from §8.1) |
| recurrences and bins | anchor-preserving bins partition their span, with no gap or overlap |

Range sets are where an SMT encoding is cheapest (linear arithmetic over rationals). An SMT check
and the Rocq normal form can each serve as the other's oracle.

### 8.4 Eligibility

| Specify | Prove |
|---|---|
| a denotation of conditions and profiles into `K3`: exact, set membership, interval containment, hierarchical match with exclusions, flat schemes (ADR-A100), set readings (ADR-A103), negation, AllRequired and AnySufficient, evidence bindings as paths | L1 to L16. A decision is monotone in evidence. Hierarchical match over a flat scheme is Undetermined exactly where ADR-A100 says |
| the concept IR (ADR-A89) and each backend's target fragment | **compiler correctness**: for each backend, the compiled artefact evaluated under the target's semantics equals the denotation. SPARQL first, over a formal semantics of the algebra fragment the compiler emits |
| design-time questions: satisfiability, exhaustiveness, widening | the SMT encoding is faithful: a model of the encoding is a candidate the denotation decides as stated, and the reverse |

Compiler correctness for SPARQL turns the parity gate from "backends agree on fixtures" into "the
reference backend agrees with the meaning on every input", and leaves fixtures to the other
backends until each has its own proof. Three conditions keep that claim honest on real stores:

| Condition | Rule |
|---|---|
| a fragment gate | the compiler emits only a declared fragment chosen for robustness across engines: basic graph patterns, `VALUES`, `FILTER` over explicitly typed literals, no property paths, no nested `OPTIONAL`. The restriction is checked mechanically on every output |
| a cross-store suite | the fragment runs on several stores, and a store's disagreement is a finding with its own gate |
| "not a value" first | unbound variables, absent solutions and `FILTER` errors all map to Undetermined, and that mapping is the compiler's first theorem |

Hierarchical match with exclusions has a named negative fixture: evidence that an exclusion applies
may move an outcome only from Undetermined, never from Permitted.

**Datalog's normative semantics** is stratified Datalog with dual predicates for Permitted and Denied,
Undetermined being neither. A non-stratifiable program is refused with a diagnostic, as I6 and B10
already refuse cycles. Well-founded semantics is not normative, because its third value comes from
cycles through negation and is not Undetermined. An engine computing the well-founded model may run
the program, since the two coincide on stratified programs (FM-D11).

### 8.5 Wording and assembly

| Specify | Prove |
|---|---|
| forms, elements, text parts, inclusion modes, slots, transclusion, inline parts, laws W1 to W8 | the laws are jointly satisfiable, and transclusion introduces no cycle (W8) |
| assembly as a function of form, settings, choices and model (assembly sketch §8) | WA1 to WA7: every successful assembly satisfies W3 to W6, assembly is deterministic, a missing capability refuses rather than drops |
| a lowering, such as an interval condition carried as a derived governing variable | the lowered assembly includes exactly what the native one does |
| InsurML's processing model, from its normative steps | **parity for the shared fragment**: on forms that use only constructs both models read natively, the InsurML model and the baseline produce the same record |

The last row turns the InsurML parity suite of the bridge sketch §7 from a test into a theorem for
the shared fragment, with tests for the rest.

### 8.6 Behaviour

| Specify | Prove |
|---|---|
| state spaces, transitions, guards, effects, nested states, history, concurrent regions, as a labelled transition system over configurations | a macrostep preserves B9, B10 and B11. B10 makes every macrostep terminate. With distinct priorities the macrostep is deterministic |
| occasions and records, with evidence (B6) | every occupancy a macrostep creates names its execution and stimulus |
| history | entering a history state restores the configuration last exited, shallow or deep as declared (B5) |

The nested states sketch already gives a reference semantics in prose (§2 there). Writing it as an
inductive step relation is direct, and its worked cases (§9 there) become the first adequacy
corpus for Behaviour.

### 8.7 Instrument

| Specify | Prove |
|---|---|
| legal relations and their correlatives (obligation, prohibition, permission, exclusion, power), arising on legal triggers, due ranges and windows, regimes gating by state, survival, termination | I3: an occasion persists until performed, breached or ended. I9: every time is anchored. I13: only bound relations are evaluated |
| breach for achievement and maintenance obligations, exceptions established only when evidenced | **I7**: an Undetermined fulfilment never yields a breach, and a breach never rests on an unestablished exception |
| stratification over trigger and state-reading edges (I6, I12) | evaluation is well founded. Contrary-to-duty chains are stratified by breach records, so Chisholm's paradox has no model in which it arises |
| templates (CCS C8a) | each template's properties, once, for every instrument that uses it (§11.2) |

### 8.8 Surface, MORK and Persistence

| Target | Specify | Prove |
|---|---|---|
| Surface promotion and index (X1 to X6) | a promotion as a view of its source | conservativity: the view adds no fact the source does not entail (X1). Index faithfulness (X2) |
| Surface projection and stacking (ADR-A20, ADR-A21) | composition of contracts | stacked projections compose associatively and conservativity survives composition (§10) |
| regeneration (ADR-A27) | a change to a source, and its minimal regeneration | regenerating after a change equals applying the change's image to the old output (§10) |
| MORK intents | the refinement order on intent nodes | the intent graph is a join-semilattice. The co-occurrence axioms reject exactly the incomplete mappings |
| MCN | encoder and decoder | decoding is lossless: decode after encode is the identity up to graph isomorphism |
| Persistence | profiles and their compiled plans | the refinement argument of the persistence note §14.1, plus, since 2026-10-10, that a compiled closure path denotes exactly a boundary shape's owned paths ([aggregate ownership §15](persistence-aggregate-ownership.md#15-effect-on-the-later-track-h-slices)) |

### 8.9 Platform protocols

The outbox, idempotent delivery (ADR-A36), acknowledgement (ADR-A37), optimistic concurrency on
revision ledgers (ADR-A33) and the identity head pointer of the identity note are protocols.
TLA+ or Quint models check that a message is delivered at least once and applied at most once, that
a lost compare-and-set never loses a write, and that replay after failure reaches the same state.
The engine note's Appendix A covers the store itself.

## 9. The monadic evaluator, specified and extracted

The evaluation context sketch describes the evaluator as a stack of monads: an environment it
reads, a ledger it changes, a log it writes, and a three-valued outcome. That description is
already a specification. Written in Rocq, it can be proved and then extracted as the reference
implementation of CCS C12.

### 9.1 The stack

```coq
(* Sketch. Outcome carries a value, or Undetermined with a reason, or Denied. *)
Inductive outcome (A : Type) := Value (a : A) | Undet (r : reason) | Deny (r : reason).

(* Reader RunEnv, State Ledger, Writer Log, over Outcome. *)
Definition Eval (A : Type) : Type :=
  env -> ledger -> outcome (A * ledger) * log.

Definition ret {A} (a : A) : Eval A := fun _ l => (Value _ (a, l), nil).

Definition bind {A B} (m : Eval A) (k : A -> Eval B) : Eval B :=
  fun e l =>
    match m e l with
    | (Value _ (a, l'), w) => let '(r, w') := k a e l' in (r, w ++ w')
    | (Undet _ r, w) => (Undet _ r, w)
    | (Deny _ r, w) => (Deny _ r, w)
    end.
```

| Prove | Why |
|---|---|
| the monad laws for `ret` and `bind` | refactoring and compiling evaluator code is safe |
| a pass commits all its ledger changes or none | evaluation context §3: a pass is one run of the context |
| a computation given only `DesignEnv` cannot observe a record or change the ledger | B8, by construction (§7.2) |
| `Undetermined` absorbs except where the result is already decided | the combinator rule, Strong Kleene lifted to values |
| sequential and parallel environments agree when no two proposals touch one account | the choice of environment matters only under contention |
| `split`, `proRata` and proportional merge conserve the whole under the declared rounding and residual-allocation rule, and the merge is order-independent with that rule | without a residual rule, rounding makes the merge depend on order |
| no combinator mixes units without `convert` | by typing (§7.2) |
| the ledger at position p+1 is a function of the ledger at p and the pass at p+1 | determinism across positions, the Dedalus reading (evaluation context §8) |

### 9.2 Combinators as a closed algebra

The combinators (`sum`, `max`, `cap`, `percentOf`, `split`, `proRata`, `convert`, `duration`,
`basis`) are a closed set, held as data. In Rocq they are an inductive syntax with a denotation,
which gives two things at once: each combinator's laws (for example that `split` conserves the
whole), and a compiler from combinator expressions to SPARQL, SQL or Datalog whose correctness is
proved against the same denotation (§13).

### 9.3 Behaviour and the evaluator together

A pass runs Behaviour's macrostep (§8.6) inside the evaluation context: guards through Eligibility,
effects lifted onto the ledger, derived triggers read after the merge, all in the strata of the
evaluation context §8. One theorem then joins the layers: **every pass preserves the Behaviour laws
and the ledger's invariants, and its outcome is the denotation of the instrument's relations at
that position**. That theorem is what "the evaluator is correct" means.

### 9.4 The reference for C12

The reference evaluator is written by hand in Python first (plan track B), with its semantics stated
precisely in the literate READMEs, and mechanised from it later if track E proceeds. It runs in the
toolchain to generate conformance kits and to explore instance properties, never against the live
graph. The C12 runtime, in a platform language, must pass its kits. Detailed in the
[reference evaluator sketch](reference-evaluator.md).

## 10. Category theory as a design language

Category theory is useful here as the language that says which laws a construction must satisfy,
and as the source of constructions whose laws are already known. It is not a goal in itself, and
each use below ends in a concrete property to prove or test.

| Construction | LATTICE reading | Property it hands us | Verdict |
|---|---|---|---|
| **Monad, applicative** | the evaluation context: sequential composition is bind, parallel composition is applicative with a merge (§9) | the monad and applicative laws, and when the two coincide | pays |
| **Natural transformation** | incremental regeneration (ADR-A27): a source change and its image in the output commute | regenerating after a change equals applying the change's image to the old output | pays, with direct operational value. A property test now (track B), a theorem later |
| **Join-semilattice** | MORK's intent refinement | the ordering laws, and that merging two intents is the least upper bound | pays, as a property test |
| **Functor** | a Surface promotion, a MORK mapping, the lift from InsurML | identity and composition laws | pays weakly. The laws are worth testing |
| **Profunctor** | a projection between layers as a relation from source shapes to target shapes | stacked projections compose. Associativity is not the property needed: **conservativity under composition** is, and it does not follow from associativity | demoted. To be proved directly, with composition defined |
| **Profunctor optics, lenses** | where a view writes back, which AIR E3 forbids | the lens laws, if write-back is ever admitted | parked |
| **Functorial data migration** (Spivak and Wisnesky) | instances moved along a schema map, as in the SQL compiler note | correctness criteria, but only where the schema map is a functor between finitely presented categories, which an OWL layer with cardinalities and disjointness is not without heavy encoding | reading only |
| **Institutions** (Goguen and Burstall) | each execution surface as a logic, a compiler as a morphism | the satisfaction condition is the formal statement of parity (ADR-A28) | vocabulary only. Each compiler is proved directly (§8.4) |

Two definitions are owed before any categorical argument is made. **Conservativity** (X1) must be
defined, model-theoretically (every model of the source extends to a model of the view) or
proof-theoretically (the view entails no new sentence in the source's vocabulary), and under which
entailment regime. And the three-valued setting is not Boolean, so an argument about the denotation
must name the category it works in.

## 11. Guaranteeing the behaviour of instruments

This is where formal methods reach adopters, and where overclaiming would do real harm. Three
tiers of guarantee, each with its own scope and assumptions, detailed in the [instrument assurance
sketch](instrument-assurance.md).

```mermaid
flowchart TB
    G["Generic theorems<br/>every instrument<br/>(I7, determinism, monotonicity<br/>as evidence grows, gating, atomicity)"]
    T["Template theorems<br/>every binding that meets<br/>the rely conditions"]
    I["Instance properties<br/>one instrument version,<br/>with generated traces"]
    C[("Assurance record<br/>method, scope, bound,<br/>assumptions")]
    M["Monitors, as data<br/>for monitorable properties"]
    G --> C
    T --> C
    I --> C
    I --> M
    M -. "violation, with trace" .-> C
```

### 11.1 Generic theorems

True of every instrument LATTICE evaluates, with monotonicity stated as §8.1 states it.

### 11.2 Template theorems

A template's property holds only where the rest of the instrument does not interfere: another regime
gating the same state, another relation writing the same account, a termination elsewhere cutting a
run-off short. So each template theorem is stated in **rely and guarantee** form. The toolchain
discharges the rely conditions per instrument, mechanically, and the instrument's claim records each
condition and what discharged it. Where a condition cannot be discharged, the guarantee is not
claimed.

### 11.3 Instance properties

| Rule | Detail |
|---|---|
| the logic | a metric first-order temporal logic over **three-valued atoms**, with **three-valued prefix verdicts**. Undetermined (a fact), inconclusive (a prefix) and not decided (a check) are three different things |
| the model | generated from the compiled instrument by a translation validated against the reference evaluator, with any abstraction recorded. Never hand-written per instrument |
| the methods | composition from template theorems, then inductive invariants, then complete model checking of the generated model, then SMT to a bound, then bounded exploration |
| vacuity | a passing property records a witness that its antecedent is reachable |
| the drafter | sees a generated satisfying trace and a generated violating trace for every property, since a rendering generated from the property cannot show that it says the wrong thing |
| licences | only permissively licensed checkers on the adopter's path. No timed automata |

### 11.4 Runtime monitors

Monitors run as data in the platform (automaton tables, incremental queries). Safety and bounded
liveness are monitorable. Unbounded liveness is not, since no finite prefix refutes it, so the
monitor compiler refuses it or transforms it into its bounded form with the drafter's agreement.

### 11.5 Properties in controlled English

Properties render in controlled English as relations do (CCS sketch §8.1), generated from the
formula. The rendering cannot drift from the property, and the generated traces of §11.3 are what
shows whether the property says what the drafter meant.

## 12. From specification to code

### 12.1 The routes

The persistence note §3.1 distinguishes extraction, verified generators and proof-producing
translation. For LATTICE as a whole:

```mermaid
flowchart LR
    R["Rocq specification<br/>and proofs"]
    X["Extraction<br/>(MetaRocq verified<br/>where in fragment)"]
    O["OCaml<br/>reference evaluator,<br/>compiler cores"]
    J["js_of_ocaml or Melange<br/>JavaScript"]
    W["wasm_of_ocaml<br/>WebAssembly"]
    IR["Rocq-defined target IRs<br/>SPARQL, SQL, Datalog algebra"]
    P["Verified or validated<br/>printers"]
    Q["SPARQL, SQL,<br/>Datalog text"]
    H["Hosts: Python (wasmtime),<br/>Java (GraalWasm, Chicory),<br/>Rust, browsers, Node"]
    R --> X --> O
    O --> J --> H
    O --> W --> H
    R --> IR --> P --> Q
```

| Route | For | Assurance |
|---|---|---|
| **E1 extraction to OCaml, run as OCaml** | mechanised cores if track E proceeds: the kernel, binding resolution, a compiler core, the evaluation context. The first reference is hand-written (track B) | high: proved code, extraction verified or trusted, the OCaml compiler trusted |
| **E2 OCaml to WebAssembly or JavaScript** | the browser and the Word add-in (client-side validation), and in-process use in tests. Not runtime evaluation against the graph (§13.1) | as E1, plus the compiler to WebAssembly or JavaScript trusted |
| **E3 verified generators to query surfaces** | compilers from the Eligibility IR and the combinator algebra to SPARQL, SQL and Datalog: the target's algebra is defined in Rocq, compilation is proved against it, and a small printer emits text | high for the algebra. The printer is checked by translation validation: the emitted text is parsed back and compared with the algebra term |
| **E4 OCaml AST to another language** | translating the extracted OCaml's syntax into Python, Java or Rust source | low: an unverified translator. Usable only with differential testing against E1, and never for code that claims proved assurance |

**Recommendation (judgement, revised 2026-10-06).** E1 for toolchain tools run as worker jobs
(§13.1). E3 for everything the runtime executes, which reaches it as queries, plans, tables and
conformance kits, never as OCaml code. E2 for the browser, the Word add-in and tests. E4 not at all
for assured code. Where idiomatic source in a platform language is required, generate it from a
prover-defined IR (E3's method), not from OCaml's syntax tree.

### 12.2 The trusted base

| Stage | Trust | How it is earned |
|---|---|---|
| the specification | trusted, and the largest risk | adequacy against the fixture corpus (§7.3), review, differential tests against independent implementations |
| proofs | checked by Rocq's kernel | Rocq |
| extraction | verified (MetaRocq) for the supported fragment, otherwise trusted | MetaRocq where it applies |
| OCaml, WebAssembly and JavaScript compilers | trusted | as for any compiled system |
| query printers | validated per output | parse back and compare |
| hand-written shells: I/O, RDF parsing, CLI | tested | property-based tests, fuzzing |
| target engines: a SPARQL store, a SQL database, a Datalog engine | trusted | the W3C test suites and differential tests across engines |

## 13. The compilation toolchains

LATTICE's toolchains today are Python compilers (`tools/mork_compilers`, `tools/surface`,
`tools/persistence`), each producing SPARQL, SHACL, SWRL, OWL or recipes. Formal methods enter them
in three steps, none of which forces a rewrite.

| Step | Change | Effect |
|---|---|---|
| S1 oracle | the hand-written reference semantics (track B) runs beside each Python compiler in CI. Generated inputs, from the shapes, are compiled by Python and evaluated on a store, and the results compared with the reference | every compiler is tested against the meaning, not only against its peers |
| S2 proved core | where a compiler's correctness matters most (Eligibility to SPARQL first), its core is written in Rocq over the target algebra and extracted. The Python tool calls it through WebAssembly or a CLI | the reference backend is proved. Others stay tested against it |
| S3 new targets from the start | new execution surfaces (SQL, from the SQL compiler note, and Datalog, from the evaluation context §9) are built proved from the start, since each is a new compiler anyway | no new hand-written backend to misread the semantics |

Parity (ADR-A28) then has a fixed point: every backend agrees with the reference, and the reference
agrees with the specification by proof.

### 13.1 Generated tools in the toolchain, never at runtime

**The opportunity.** OCaml and Haskell compile to native code, and for CPU-bound symbolic work they
are commonly one to two orders of magnitude faster than CPython, with far less memory per term.
That is an expectation to measure, not a fact about LATTICE. It is a performance argument, separate
from the choice of prover (plan E7), and it holds only for some jobs: work bound by an SMT solver or by
the store gains nothing from a native rewrite. The [toolchain workers sketch](formal-toolchain-workers.md)
§2 decides per family, after a Python baseline is measured. The candidate jobs:

| Job | Why it is heavy | Today |
|---|---|---|
| joint satisfiability and exhaustiveness of every variation slot, for every condition kind (CCS C13a) | a solver call per slot, over every pair and every gap | intervals only, by candidate points in SHACL-SPARQL |
| configuration-space analysis of a product: question plans, dead components, specialisation (toolchain sketch §3) | exponential in the governing variables without pruning | none |
| assembly of a whole library and the parity suite over every configuration (IMA-4.2) | one assembly per configuration per model | none |
| bounded exploration of instrument properties (§11.3) | many event sequences per property, each a full evaluation | none |
| adequacy over the whole fixture corpus (§7.3) | every example decoded and checked against every law, on every change | none |
| compiling large applied modules' conditions and combinators to SPARQL, SQL and Datalog | many plans, each checked by parsing it back | Python, per condition |
| closures, normal forms and crosswalks over large schemes, such as the peril vocabulary | transitive closures and normalisation over thousands of concepts | Python and the store |
| minimal regeneration after a change (ADR-A27) | a difference over large derived graphs | Python |
| persistence planning (the persistence note) | search over physical structures | designed, not built |

**The division of labour (recommendation).**

| Part | Owns | Language |
|---|---|---|
| Python | RDF input and output (`rdflib`), shape validation, orchestration, the job protocol, provenance | Python, as now |
| generated tools | computation over typed terms: decisions, normal forms, satisfiability, assembly, exploration, compilation | OCaml generated from the prover (§13.2) |
| the store | query evaluation | as configured through the store interface |
| the runtime | execution against the live graph: Behaviour stimuli, relation plans, queries | the platform's languages, Java and Python |

**Why not at runtime.** The runtime holds the live graph through the store interface, under the
platform's authorisation checks, optimistic concurrency, persistence profiles and aggregate leases
(ADR-A59's strict per-key ordering for Behaviour stimuli). A second language at runtime would be a
second platform to operate, secure, observe and staff, and the platform's extension rule (adapters
pass the store interface's contract tests) assumes the platform's own languages. The design rule
that already governs hot paths, compile and do not interpret (DP5), gives the better answer: the
toolchain compiles, and the runtime executes what was compiled. Proved artefacts therefore reach the
runtime as **data**, never as OCaml or Haskell code:

| Reaches the runtime as | Produced by |
|---|---|
| SPARQL, SQL and Datalog text | verified printers in the toolchain (E3) |
| relation plans, state tables, monitor automata | generated tools, emitted as canonical data |
| conformance kits: event logs with expected outcomes, ledgers and records | the reference evaluator (§9), run in the toolchain |

The runtime evaluator of CCS C12 is then written in a platform language and held to the reference
by its conformance kit. This revises §9.4, where an extracted runtime was one option, and §12.1,
where WebAssembly carried extracted code into every runtime.

**How a generated tool runs.** As a job, exactly as Surface compilers run today:

| Step | Rule | Existing decision |
|---|---|---|
| 1 | the control plane enqueues a job of a closed job family (`formal.slot-check`, `formal.property-check`) carrying graph references only, with an idempotency key | ADR-A30, ADR-A36 |
| 2 | a Python worker consumes it and materialises each graph through the trusted resolver, checking its digest against the reference's revision hash | ADR-A35 |
| 3 | the worker encodes the input as canonical typed JSON, using the codec generated from the specification's datatypes, the same codec the adequacy check uses | §7.3 |
| 4 | the worker runs the tool with one fixed argument vector per job family, no network, a private work directory, and bounds on time, memory and CPU | ADR-A35 |
| 5 | the tool writes a canonical result and its diagnostics. It is deterministic, so the result's digest is a function of the input's digest and the tool's | §12 |
| 6 | the worker decodes and validates the result, records it as a derived artefact whose read set is the input revisions and the tool's image digest, publishes, then acknowledges | ADR-A92, ADR-A26, ADR-A36, ADR-A37 |
| 7 | a repeated request with the same canonical request digest (inputs, bounds, seed, tool, codec and tenant) republishes the cached result | ADR-A36 |

Three choices in that flow are deliberate:

- **Typed JSON into the tool, not RDF.** OCaml's and Haskell's RDF libraries are thin, and one RDF
  stack is enough. The codec is generated from the specification on both sides, so encoding and
  decoding are checked by the adequacy corpus like everything else. A binary encoding (CBOR) is an
  option where payloads grow large.
- **A subprocess per job, not a service.** Native start-up costs milliseconds, the sandbox is the
  process, and a crash cannot corrupt the worker. A long-lived tool process speaking a line
  protocol is the fallback if measured start-up cost dominates small jobs.
- **A bound is an outcome.** A job that reaches its time or exploration bound reports "not decided
  within the bound", never "passed", and the bound is recorded in the assurance record (FP3).

The same binary runs locally and in CI through `mise`, without RabbitMQ, so tests and production
jobs share one code path. Tools are built reproducibly from locked dependencies, shipped as
OCI images with recorded digests, and signed through ADR-A40's adapters. A worker refuses a tool
whose digest it does not know.

The design is detailed in the [formal toolchain workers sketch](formal-toolchain-workers.md).

### 13.2 One prover or two, one generated language or two

| Question | Benefit | Cost | Recommendation |
|---|---|---|---|
| **Two provers for the same artefacts** | two independent specifications might catch a specification error | every specification, proof and adequacy check twice, and two specifications to keep aligned | **no.** Independent checking of specifications comes more cheaply from the lightweight rung (Alloy, Quint, SMT) and from differential tests against independent implementations |
| **A second prover for a separate artefact** | a closer fit for that artefact | a second proof culture | **only when the artefact exists and the fit is decisive.** The custom engine's Rust kernels are the one candidate: Rocq's `hax` or Lean's Aeneas. Decide if the engine is built |
| **Several tools across the rungs** | each finds a different class of defect at a different cost | a toolchain per tool | **yes**, as designed: Alloy, SMT, TLA+ or Quint, one prover, generated monitors |
| **OCaml and Haskell generated from one specification** | N-version execution: both builds run the same inputs in CI, and any difference exposes a code generator or runtime library defect, which is the trusted part of the chain | two toolchains to pin, two images | **only as a CI check, and only if it is nearly free.** It is nearly free with Isabelle, which generates both. It is not with Rocq, whose Haskell extraction is little used. the prover spike shows whether it is |
| **Haskell as the production toolchain language** | QuickCheck and Hedgehog, parser combinators, type-level programming, Liquid Haskell for refinement types on hand-written tools | lazy evaluation risks space leaks in long batch runs, and GHC's WebAssembly and JavaScript backends are younger | **no, OCaml.** Strict evaluation gives predictable memory in heavy batch work, OCaml compiles fast, and js_of_ocaml and wasm_of_ocaml serve the browser and tests. OCaml 5's domains give in-process parallelism, though the job queue already parallelises across workers |
| **Haskell tools without writing Haskell** | pandoc for document conversion in ingestion and DOCX round trips, NASA's Copilot for monitors that compile to C | none beyond packaging | **yes, as tools**, wherever they fit the task. Using a tool written in Haskell needs no Haskell in LATTICE |

So the recommendation is **one prover, OCaml as the toolchain language, Haskell builds as an
optional N-version check, and Haskell tools used freely as tools**. FM-D1 decides the prover, and
FM-D9 and FM-D10 the rest.

## 14. The development lifecycle

```mermaid
flowchart LR
    A["ADR and sketch<br/>Alloy, Quint, SMT models,<br/>counterexamples"]
    B["Brief<br/>formal obligations<br/>per slice"]
    C["Build<br/>shapes, examples,<br/>Rocq theory, proofs"]
    D["Validation Pack<br/>adequacy, property tests,<br/>proofs, model checks"]
    E["CI<br/>proof checking,<br/>differential tests,<br/>assurance report"]
    F["Release<br/>assurance record<br/>in the provenance ledger"]
    A --> B --> C --> D --> E --> F
```

| Stage | Formal practice |
|---|---|
| **Design** (ADR, sketch) | a semantic ADR carries a small model: Alloy for structure, Quint or TLA+ for behaviour, an SMT encoding for a decision procedure. Track C supplies a skeleton per law family so the marginal cost is about an hour, without which the rule would be quietly ignored |
| **Brief** (Validation Pack skeleton) | the slice's laws are listed with their intended assurance level: proved, model-checked, solver-checked, property-tested, shape-checked |
| **Build** | the literate README states a law. The shape checks it on data. The Rocq theory states it as a proposition, and a proof or a model check establishes it for the algorithm |
| **Validation Pack** | adds four rows to the existing evidence: adequacy over the fixtures, property tests from shape-derived generators, the proofs that check, the model checks with their bounds |
| **CI** | `mise` tasks for proof checking, model checking to declared bounds, and differential tests of every compiler against the reference. Proofs are built by the prover's own dependency-aware build (dune rules, or Isabelle session images), cached as images. A kernel change rebuilds everything above it, which is a reason to prove the kernel first and then freeze it. Critical-path checking takes minutes, and deeper runs are nightly |
| **Release** | the assurance report joins the semantic release's provenance ledger (ADR-A39). The gate refuses an unreviewed restatement, an unexplained fall in level and any failed claim |
| **Agentic development** | a proof assistant is a precise critic. An agent proposes a proof, Rocq's kernel accepts or rejects it, exactly as the ingestion vision has models propose and shapes dispose. Proof attempts cost tokens, and estimates should count them |
| **Adopters** | applied ontology authors receive certified templates and a property checker for their instruments (§11) |

The cheapest practices (shape-derived property tests, small Alloy or Quint models at design time,
SMT for decision procedures) pay from the first slice that uses them and need no proof assistant.

## 15. Tools

| Need | Recommended | Alternatives | Notes |
|---|---|---|---|
| Proof assistant | **Rocq or Isabelle/HOL, or none**, decided by the prover spike (FM-D1) | Lean 4 (strong metaprogramming, mathlib, Aeneas for Rust), Isabelle/HOL (Haskell generation, the Refinement Framework), Agda (category theory), F* | Rocq gives verified extraction to OCaml (MetaRocq), a large compiler-verification ecosystem, and precedent for Datalog and SQL semantics (Benzaken, Contejean and Dumbrava) |
| Model finding | Alloy 6 | | temporal operators since version 6 |
| SMT | Z3, cvc5 | | both permissive |
| Model checking | TLA+ with TLC and Apalache, Quint | none | nuXmv is free for non-commercial use only and UPPAAL needs a commercial licence for commercial use, so neither is on a path adopters rely on. Timed automata are avoided altogether |
| Property-based testing | Hypothesis (Python), jqwik (Java) | | generators derived from shapes |
| Code generation | Rocq extraction, js_of_ocaml or Melange, wasm_of_ocaml | | |
| Runtime monitors | synthesised as data from the monitorable fragment | | |
| Heterogeneous specification | Hets and DOL, as reference | | prior art for relating OWL, first-order and other logics |

Licences: the checkers are tools, so their licences do not reach the code they check. Libraries
differ: a theory that imports an AFP entry or a Rocq library takes that library's terms, and
generated code may embed library code, so licences are checked per import, not per tool. The licence
of the normative theory and of generated code, beside the documents' CC-BY-SA-4.0, is a deliberate
decision (FM-D14).

## 16. Where it lives

The repository topology rule gives `ontology/` the semantic assets and `tools/` the executable
implementations. A mechanised semantics is both: its definitions are normative semantics, its
proofs and extraction are a build.

| Option | Layout | For | Against |
|---|---|---|---|
| **O1** | per-layer theories in `ontology/<layer>/formal/`, one Rocq project in `tools/formal/` that builds them with the proofs of algorithms, extraction and generators | each layer's formal statement sits beside its README, shapes and examples, and is reviewed with them | two places to look |
| O2 | everything in `tools/formal/` | one project, one build | the normative semantics leaves the layer it defines |
| O3 | a new top-level `formal/` root | visible and self-contained | a new root, and a third home for semantics |

**Recommendation: O1.** Rocq's build maps several directories into one logical project, so the
layout costs nothing at build time. Each option needs an ADR under the topology rule.

## 17. A phased route

Replaced by the tracks of the [formal methods plan](../plans/formal-methods.md), re-sequenced after
review so that the ledger, the adequacy harness, the hand-written reference and the design-time models
do not wait for the prover. The prover spike stays the first step, narrowed, with declared abandonment
conditions.

## 18. Risks

| # | Risk | Mitigation |
|---|---|---|
| FR1 | **The specification gap**: a proof of the wrong property proves nothing useful | statement digests, statements reviewed in the README (FP4), adequacy against the fixture corpus, differential tests against independent implementations |
| FR2 | **Proof maintenance** while layers are at major version zero and change in MINOR steps | prove the stable kernels first, keep Behaviour and Instrument at T0 to T4 until they settle, and measure proof-repair cost per release (plan §6) |
| FR3 | **Skills and continuity**: few contributors write proofs | the cheap rungs need no prover. Statements are short and reviewed, proof bodies are opaque under an assumption audit (FP4) |
| FR4 | **Toolchain weight**: opam, a prover, OCaml in a Python and Java repository | a separate `bootstrap:formal` task under `mise`, so the rest of the repository bootstraps without it. Toolchains and build outputs live outside the tracked tree, and generated tools are built in CI and published as images, never committed (plan E6). Contributors who do not touch theories never build them |
| FR5 | **Open world against closed datatypes** | FP2. Unformalised semantic commitments are listed (§7.3) |
| FR6 | **Over-formalising** | §5.1 limits the prover to the claims only it gives, and the plan's abandonment conditions stop the rest |
| FR7 | **Slow CI** | dependency-aware builds, cached images, model checks to declared bounds, deeper runs nightly |
| FR8 | **Extraction's trusted base** | MetaRocq's verified extraction where it applies, translation validation for printers, and a hand-written reference as differential partner |
| FR9 | **Overclaiming to adopters** | method, scope, bound and assumptions on every claim, every statement about assurance generated from the record, rely conditions on templates, and generated traces for drafters |
| FR10 | **Dual maintenance** of theory and ontology | one source for the closed portion (FP1), and the adjudication rate as a standing metric with an abandonment threshold |
| FR11 | **Regeneration storms** when a tool image changes | tool identity separated from semantic inputs. A tool change marks claims stale, never invalid (FM-D15) |
| FR12 | **Competition with CCS** on machine R | plan E4, and tracks scheduled in CCS gaps |

## 19. Decisions for the maintainer

Kept in one place, the [plan](../plans/formal-methods.md) §7.

## 20. Open questions

| # | Question | Leaning |
|---|---|---|
| FM-Q1 | Should the theory's datatypes be generated or written? | the closed portion generated from the README, laws written (FM-D12) |
| FM-Q2 | Which SPARQL fragment does the Eligibility compiler emit? | a declared fragment chosen for robustness across engines, enforced as a gate (§8.4) |
| FM-Q3 | Does SPC's session-type metatheory belong in this programme? | later, and outside FM-D1, since it is the one area where a second prover might fit |
| FM-Q4 | How are instance properties authored? | a property panel beside each relation, with the generated satisfying and violating traces as the primary review surface |
| FM-Q5 | Should assurance records be exchangeable? | yes, with statement digests, signatures and attestations. Proof scripts travel with templates a market body publishes |
| FM-Q6 | Is a timed model needed? | no. Durations are integer constraints over positions |
