<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Instrument assurance: guaranteeing how an instrument behaves

**Unit:** [formal-methods](../plans/formal-methods.md), phases 7 and 8. **Status:** sketch,
2026-10-06. Nothing here is ratified.
**Parent:** [formal methods](formal-methods.md) §11, which this details. Reads with the
[reference evaluator sketch](reference-evaluator.md), the [assurance records
sketch](assurance-records.md), and the CCS template library (C8a).

---

## 1. The problem

An adopter configures an instrument: relations, triggers, windows, regimes, amounts. The question
they ask is whether it does what was meant, over every sequence of events that can happen. LATTICE
can answer at three levels of generality, each cheaper to use than the one below it.

## 2. Three tiers

| Tier | Established | Cost to the adopter | Example |
|---|---|---|---|
| generic | once, in the specification, for every instrument | none | an Undetermined fulfilment never yields a breach (I7) |
| template | once per template, over its parameters | choosing the template | a notice termination never takes effect before its window closes |
| instance | per instrument version, by a checker | stating the property | this policy's payments never exceed its aggregate |

### 2.1 Generic theorems

| Theorem | Layer |
|---|---|
| more evidence never reverses a decided outcome | kernel, Eligibility, Quantification |
| evaluation is deterministic: the same records give the same outcomes | evaluation context, Behaviour |
| an Undetermined fulfilment never yields a breach, and a breach never rests on an unestablished exception (I7) | Instrument |
| no relation arises in a state whose regime gates it | Instrument, Behaviour |
| every pass is atomic, and the ledger changes only through lifted effects | evaluation context |
| every macrostep terminates, and preserves B9 to B11 | Behaviour |

### 2.2 Template theorems

A template from the C8a library is a configuration with parameters. Its theorem quantifies over
the parameters, so it holds for every binding.

| Template | Theorem |
|---|---|
| notice | a termination takes effect at or after the end of the notice window that its notice opened, and not without a notice |
| suspension | while the suspended state is occupied no gated relation arises, and on leaving it each suspended relation resumes or ends as declared |
| non-renewal | no new period begins after a non-renewal notice takes effect |
| run-off | the named relations survive termination, and no relation of a closed class arises after it |
| threshold | after every pass, the regime occupies the state whose range contains the ledger value |
| discovery period | the power to elect exists only within its window after cancellation or non-renewal, and never after cancellation for non-payment |

Market templates in the applied insurance profile, such as those of the LMA's Module 12 regimes,
are built on these and inherit their theorems. A market body can publish a template with its claims
(assurance records sketch §6).

### 2.3 Instance properties

Stated by a drafter or reviewer, for one instrument version, in the property language (§3), and
checked by the method its form allows (§4).

## 3. The property language

### 3.1 Requirements

| # | Requirement | Why |
|---|---|---|
| PL1 | three-valued | a run may leave a fact undetermined, and the answer must say so |
| PL2 | quantifies over data | "every claim notified within the window is decided" ranges over claims |
| PL3 | metric time | windows and notice periods are durations between events |
| PL4 | reads LATTICE terms only | relation states, occasions, records, ledger balances, regime states, positions |
| PL5 | renders in controlled English | drafters must be able to read what was checked |

### 3.2 Choice

| Logic | PL1 | PL2 | PL3 | Prior art |
|---|---|---|---|---|
| LTL3 | yes | no | no | three-valued runtime verification (Bauer, Leucker and Schallhart) |
| metric temporal logic | no | no | yes | widely monitored |
| **metric first-order temporal logic (MFOTL)** | by a three-valued reading over finite traces | yes | yes | MonPoly, and VeriMon, a verified monitor generated from Isabelle/HOL |

**Recommendation: MFOTL over LATTICE atoms, read three-valued.** It meets all five requirements, and
it has a verified monitor as precedent.

### 3.3 Atoms

| Atom | Reads |
|---|---|
| `arises(r, x)`, `performed(r, x)`, `breached(r, x)`, `ended(r, x)` | Instrument relation occasions |
| `in(s, regime, x)` | Behaviour occupancies |
| `balance(a) op q` | the evaluation context's ledger |
| `notice(p, kind)`, `act(p, kind)` | records of acts |
| `decided(r, x)`, `undetermined(r, x)` | Eligibility and relation outcomes |

### 3.4 Examples

| In words | Formula, sketched |
|---|---|
| payments never exceed the aggregate | `always balance(paid) <= balance(aggregate)` |
| every claim notified within the window is decided within 60 days | `always forall c. notified(c) and within(window) implies eventually[0,60d] decided(c)` |
| the insurer cancels only for non-payment, on at least 15 days' notice | `always act(insurer, cancel) implies once[15d,∞) notice(insurer, cancel) and once breached(premium, _)` |

Each formula renders in controlled English by the same rules that render relations (CCS sketch
§8.1). The rendering is generated, never written.

## 4. Checking

| Property form | Method | Result |
|---|---|---|
| follows from template and generic theorems | proof by composition, often automatic | Proof |
| finite-state abstraction exists (regime states, windows as clocks, ledger bounded to a few thresholds) | model checking, timed where windows matter | complete or bounded ModelCheck |
| ledger arithmetic within linear bounds | SMT over unrolled passes | SolverCheck to a bound |
| otherwise | bounded exploration with the reference evaluator, generating event sequences, as a worker job | bounded ModelCheck, or PropertyTest |

Every check produces an assurance record with its method, bound and result, and a counterexample
trace where it fails. The trace is an event log the reference evaluator replays, so a reviewer sees
the exact sequence that breaks the property.

## 5. Runtime monitors

The same properties watch the live instrument. The monitor is synthesised in the toolchain and
reaches the runtime as data (parent §13.1), never as toolchain code.

| Property fragment | Synthesised as | Executed by |
|---|---|---|
| propositional, with bounded windows | an automaton table: state, event, next state, verdict | a small table interpreter in the platform, as SPC's runtime interprets state machine tables |
| first-order | incremental queries, or Datalog rules over records | the store, or the runtime's query service |
| any, for audit | the verified monitor over an exported record log | a worker job, near-line |

A monitor reports Holds, Fails with the trace that led there, or Not yet decided. A failure is a
finding against the instrument, recorded as a runtime record with its evidence (B6).

## 6. Where this meets the adopter

| Adopter step | What they see |
|---|---|
| choose templates | the theorems each brings |
| write bespoke relations | the generic theorems still hold, and the instance checker is offered |
| state properties | in a panel beside each relation, in controlled English, with the formula generated |
| issue the instrument | its assurance records, in its contract package |
| run it | monitors reporting against the same properties |

## 7. Open questions

| # | Question | Leaning |
|---|---|---|
| IA-Q1 | Is a timed model needed, or do positions suffice? | positions for evaluation, timed checking only for properties stating durations |
| IA-Q2 | How is fairness of the event source stated for liveness properties? | as an explicit assumption in the property, recorded on the claim |
| IA-Q3 | Can a monitor's Fails verdict trigger a regime transition? | no. A monitor reports. Turning a finding into a consequence is the instrument's own relations |
| IA-Q4 | Who may state properties on a shared template? | the template's owner, with adopters adding instance properties only |
