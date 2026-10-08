<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Instrument assurance: guaranteeing how an instrument behaves

**Unit:** [formal-methods](../plans/formal-methods.md), track G. **Status:** sketch, 2026-10-06,
revised after review ([response](../notes/formal-methods-review-response.md)). Nothing here is
ratified.
**Parent:** [formal methods](formal-methods.md) §11, which this details. Reads with the
[reference evaluator sketch](reference-evaluator.md), the [assurance records
sketch](assurance-records.md), and the CCS template library (C8a).

---

## 1. The problem

An adopter configures an instrument: relations, triggers, windows, regimes, amounts. The question
they ask is whether it does what was meant, over every sequence of events that can happen. LATTICE
can answer at three levels of generality, each with its own scope and its own assumptions, and must
say which it is answering.

## 2. Three tiers

| Tier | Scope | Established | Example |
|---|---|---|---|
| generic | every instrument | once, for LATTICE's semantics | an Undetermined fulfilment never yields a breach (I7) |
| template | every instrument that binds the template **and meets its rely conditions** | once per template, over its parameters | a notice termination never takes effect before its window closes |
| instance | one instrument version | per version, by a checker | this policy's payments never exceed its aggregate |

### 2.1 Generic theorems, worded precisely

| Theorem | What it does not say |
|---|---|
| **as evidence grows**, a decided outcome is never reversed. Formally, decisions are monotone in the information order of their inputs | it says nothing about evidence that is corrected, withdrawn or superseded, which may legitimately change Permitted to Denied. How retraction propagates to downstream records (supersession in Foundation, breach records in Instrument) is a design question the formal work must settle |
| evaluation is deterministic: the same records give the same outcomes | |
| an Undetermined fulfilment never yields a breach, and a breach never rests on an unestablished exception (I7) | |
| no relation arises in a state whose regime gates it | |
| every pass is atomic, and the ledger changes only through lifted effects | |
| every macrostep terminates, and preserves B9 to B11 | |

Hierarchical match with exclusions is the place where an implementation shortcut would break the
first theorem, so it has a named negative fixture: evidence that an exclusion applies must move an
outcome only from Undetermined.

### 2.2 Template theorems, in rely and guarantee form

A template's property does not hold in every instrument that binds it, because the rest of the
instrument can interfere: another regime can gate the same state, another relation can write the
same ledger account, a termination elsewhere can cut a run-off short. So each template theorem
states what it **relies** on and what it then **guarantees**:

| Template | Relies on | Guarantees |
|---|---|---|
| notice | nothing else enters the terminated state, and no other regime ends the instrument during the window | a termination takes effect at or after the end of the notice window that its notice opened, and not without a notice |
| suspension | no other regime gates the suspended relations, and the event source is fair for resumption | while suspended no gated relation arises, and each suspended relation eventually resumes or ends |
| non-renewal | no other power extends the period | no new period begins after a non-renewal notice takes effect |
| run-off | no other ending state ends the named relations | the named relations survive termination, and no relation of a closed class arises after it |
| threshold | no other effect writes the account between the pass and the transition, and boundaries are closed on a declared side | after every pass, the regime occupies the state whose range contains the ledger value |
| discovery period | no other power alters the window | the power to elect exists only within its window after cancellation or non-renewal, and never after cancellation for non-payment |

For each instrument that binds a template, the toolchain discharges the rely conditions
mechanically, by a check over the instrument's compiled configuration. The instrument's claim then
records each rely condition and the claim that discharged it (`asr:assumes`, `asr:dischargedBy`).
Where a condition cannot be discharged, the template's guarantee is not claimed for that instrument.

### 2.3 Instance properties

Stated by a drafter or reviewer, for one instrument version, in the property language (§3), and
checked by the method its form allows (§4).

## 3. Three kinds of third value

Three different third values meet here, and each keeps its own meaning:

| Third value | Means | Where |
|---|---|---|
| Undetermined | the fact is not established | an atom of the property: a relation's outcome, an occupancy |
| inconclusive | the run so far does not settle the property | a verdict over a finite prefix |
| not decided | the check did not conclude within its bound | the assurance record (`earl:cantTell`) |

### 3.1 The property language

A metric first-order temporal logic, with **three-valued atoms** and **three-valued prefix
verdicts**, a three-by-three design:

| Requirement | Met by |
|---|---|
| atoms may be Undetermined | atoms evaluate in strong Kleene logic |
| a verdict over a prefix may be inconclusive | LTL3-style verdicts (Bauer, Leucker and Schallhart), lifted to the three-valued atoms |
| quantification over claims, parties, occasions | first-order quantifiers over the run's records |
| windows and notice periods | metric operators over positions and durations, as integer constraints, so no timed automata are needed |
| controlled English | generated from the formula by the rendering rules of relations (CCS sketch §8.1) |

**The theorem a reviewer wants.** A verdict is monotone in the information order of its atoms:
resolving an Undetermined atom never reverses a verdict already reported as holding or failing.

### 3.2 Atoms

| Atom | Reads |
|---|---|
| `arises(r, x)`, `performed(r, x)`, `breached(r, x)`, `ended(r, x)` | Instrument relation occasions |
| `in(s, regime, x)` | Behaviour occupancies |
| `balance(a) op q` | the evaluation context's ledger |
| `notice(p, kind)`, `act(p, kind)` | records of acts |
| `decided(r, x)`, `undetermined(r, x)` | Eligibility and relation outcomes |

## 4. Checking

### 4.1 The model is generated, never hand-written

A model check establishes a property of a model, so the model must provably stand for the
instrument. It is generated from the compiled instrument by a translation that is itself validated:
the model and the reference evaluator run the same event logs and must agree. Where the translation
abstracts (a ledger reduced to its thresholds, positions bounded), the abstraction is named and
recorded with its own evidence (`asr:abstraction`), and the claim records the model's digest.

### 4.2 Methods, in order of preference

| Property form | Method | Scope of the result |
|---|---|---|
| follows from generic and template theorems, with rely conditions discharged | composition | every run, under the recorded assumptions |
| an invariant, possibly after strengthening | inductive invariant checking (Apalache's inductive mode, k-induction, IC3) | every run |
| a finite-state abstraction exists | complete model checking of the generated model | every run of the abstraction |
| ledger arithmetic within linear bounds | SMT over unrolled passes | to the bound |
| otherwise | bounded exploration with the reference evaluator, as a worker job | to the bound |

Ledger invariants such as "payments never exceed the aggregate" are routed to inductive checking
first. Bounded exploration is the method of last resort, and its result is recorded as bounded.

### 4.3 Vacuity

Every passing temporal property records a witness that its antecedent is reachable.
`always (notified implies eventually decided)` passes trivially if no claim is ever notified, so
without the witness the result is marked vacuity-unchecked.

### 4.4 Licences

Only permissively licensed checkers are on the path to artefacts adopters rely on: Z3, cvc5, Alloy,
TLC and Apalache. nuXmv and UPPAAL, whose licences exclude commercial use without a separate
licence, are not used.

## 5. Runtime monitors

The same properties watch the live instrument, where they can. The monitor is synthesised in the
toolchain and reaches the runtime as data, never as toolchain code.

| Property fragment | Monitorable | Synthesised as | Executed by |
|---|---|---|---|
| safety, propositional, with bounded windows | yes | an automaton table: state, event, next state, verdict | a small table interpreter in the platform |
| safety, first-order | yes | incremental queries, or Datalog rules over records | the store, or the runtime's query service |
| bounded liveness ("decided within 60 days") | yes, as its deadline-safety form | as safety | as safety |
| unbounded liveness ("eventually decided") | **no**. A finite prefix can never refute it | refused, or transformed into its bounded form with the drafter's agreement | |

The monitor compiler refuses a non-monitorable property rather than emitting a monitor that can
never fire. A monitor reports holds, fails with the trace that led there, or inconclusive. A failure
is recorded as a runtime finding with its evidence (B6).

## 6. Where this meets the adopter

The specification gap reaches adopters: a drafter's property may not say what they mean, and its
controlled-English rendering cannot reveal that, because the rendering is generated from the
property and agrees with it by construction. So, **for every instance property, the toolchain
generates a satisfying trace and a violating trace and shows both to the drafter.** Reviewing two
concrete scenarios is something an underwriter or a claims specialist can do. If no satisfying trace
with a reachable antecedent exists, the property is vacuous, and the drafter is told.

| Adopter step | What they see |
|---|---|
| choose templates | each template's guarantee and its rely conditions |
| write bespoke relations | which rely conditions their relations break, if any |
| state properties | the formula's controlled English, and the two generated traces |
| issue the instrument | its claims in its contract package, each with method, scope, bound and assumptions |
| run it | monitors reporting against the monitorable properties |

## 7. Open questions

| # | Question | Leaning |
|---|---|---|
| IA-Q1 | Is a timed model needed? | no. Durations are integer constraints over positions |
| IA-Q2 | How is fairness stated for liveness? | as an explicit assumption, recorded on the claim |
| IA-Q3 | Can a monitor's failure trigger a regime transition? | no. A monitor reports. Turning a finding into a consequence is the instrument's own relations |
| IA-Q4 | Who may state properties on a shared template? | the template's owner. Adopters add instance properties |
| IA-Q5 | Is retraction of evidence in the model? | yes, as supersession of records, with the precise monotonicity statement of §2.1 and a separate account of what retraction does downstream |
