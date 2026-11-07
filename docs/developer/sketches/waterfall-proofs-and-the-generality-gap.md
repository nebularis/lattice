<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Waterfall proofs: what they establish, and the gap to the general case

**Unit:** cross-unit. [ledger](../plans/ledger.md) at LG-2 and LG-4, [ensemble](../plans/ensemble.md) at ES-3, ES-6 and ES-8, [formal methods](../plans/formal-methods.md) at C4, E4a, E4b and E4c.
**Status:** sketch, 2026-11-07. Investigative. Nothing here changes the model until its questions are answered.
**Reads:** an Isabelle/HOL development of the reinsurance inurement waterfall, five theories, held outside this repository in a git-ignored working folder on the maintainer's machine. It is informative background and never a source of rules.
**Supersedes:** a review note of 2026-10-27 that audited an earlier, unchecked listing of the same material. That note was removed from the repository on 2026-11-05 and its figures do not hold, for the reason in §1.

Grading as in the engine papers. **Fact** means a theory text says so, or a build was run and read. **Judgement** means a reasoned reading that a check could overturn. Every claim below is marked.

---

## 1. Standing and provenance

**Fact.** The development builds. All five theories built together on 2026-11-05 with Isabelle2025-2 on Linux, `Finished Waterfall (0:00:21 elapsed time)`, with no `sorry`, `oops` or `axiomatization`, and its `ROOT` sets `quick_and_dirty = false`, which is what makes the absence of `sorry` a property of the build rather than of a text scan.

**Fact.** This replaces an earlier reading. A prose document of the same material, read on 2026-10-27, embedded a listing that described itself as a working skeleton with 17 `sorry` placeholders and roughly 900 lines outstanding. The five theories are a different artefact with none of them. Any figure from that audit is void, including its §5 count of five allocation axioms (§4, finding 2).

**It is insurance-specific, and Ledger and Ensemble are substrate.** Take shapes from it and never its terms. It is not committed here, it is not cited in anything published, and a result quoted from it is attributed as an external development that we rebuilt, never as our proof. A LATTICE claim record requires the artefact to be in `tools/proofs/` under the gate, which it is not (§7, Q4).

## 2. Why it bears on two units at once

```
     C4 (Alloy, briefed, 9 checks)
      |
      v
  ADR-A130 accepted
      |
      v
    ES-0 --> ES-1 --> ES-2 --> ES-3 --> ES-4 --> ES-8
   examples  layer    hook      |        |         ^
            (moves           needs     needs      |
            release)          LG-2     LG-2       |
                                       LG-Q3/Q4   |
  LG-2 ----> LG-3 ----> LG-4 ---------------------+
 runtime   Behaviour  allocation
 (moves    migration  + conservation
 release)
                  LG-5 --> LG-6   (no Ensemble dependency)
```

The ledger unit does not gate the ensemble unit. **One slice does, LG-2**, and LG-4 gates only ES-8. The ensemble's own head gate is C4 and the acceptance of ADR-A130, neither of which the ledger unblocks. Two slices move the substrate release and so cannot be concurrent, LG-2 and ES-1, which puts ES-1 behind LG-2's *merge* rather than behind its build.

This material bears on C4's check list, on LG-4's central shape, and on three ensemble slices. That is why it is one sketch rather than a note in each plan.

## 3. The generality gap

This is the section to read before citing anything from the development. The question is not whether the theorems hold. It is what they hold *of*.

### 3.1 What the uniqueness argument actually uses

**Judgement, and the one most worth checking.** The uniqueness proof appears to be structurally general already, and its reinsurance content sits in the instantiation rather than in the argument.

`solution` is the declarative reading: each contract applies to the loss net of what inures to it, which is the simultaneous equations the wordings assert. `solution_unique` proves two solutions equal by well-founded induction on the dependency relation, and the only property of the body it uses is a congruence lemma, `sol_body_cong`: the body at `k` depends on the other units' values **only through the units the relation declares as `k`'s predecessors**. `solution_exists` builds a solution by well-founded recursion on the same relation and uses the same congruence.

Nothing in either proof uses the contract semantics, the deduction operator, the rational carrier or the loss-vector structure. So the general theorem behind them reads:

> A finite, acyclic dependency relation, together with a body that reads only its declared predecessors, admits exactly one solution, and well-founded recursion computes it.

If that reading is right, establishing the general case is a refactoring of an existing proof — abstract the body to a parameter carrying the congruence — and not new mathematics. **That is a claim to verify, not to rely on.** It is the first thing the non-reinsurance rig should test (§6).

### 3.2 What the instantiation fixes, and is therefore not proved generally

| Fixed in the development | A general claim would need |
|---|---|
| the step function, two contract constructors with their aggregate features | any evaluation body, with the congruence of §3.1 discharged for it |
| the deduction operator, subtracting the predecessors' recoveries | any way of combining a predecessor's output into a dependant's input |
| the carrier, a total function from claim identifiers to rationals | the outcome type LATTICE evaluates into |
| one aggregate state per contract, threaded through one run | an account drawn by several instruments, which is the whole of ES-4 |
| amounts, with no three-valued outcome | Permitted, Denied and Undetermined, per PRI-08 |

### 3.3 What is absent entirely, and matters most

**Fact. There is no Undetermined, and no information order.** The carrier is a total function into rationals. `zerov` fills out-of-range indices, which is a value and not an absence. ADR-A130 decision 5 states the semantics as "the least fixpoint of their evaluations over the facts passed between them", with "every passed fact Undetermined until the evaluation that produces it has run". That is a least fixpoint over an *information* order whose bottom is Undetermined. The development has no such order and uses no fixpoint, least or otherwise. It uses well-founded recursion, which needs neither a lattice nor monotonicity.

So the development proves uniqueness in a different setting from the one decision 5 describes. For an acyclic graph the two agree on the answer, since there is exactly one solution and "least of one" is that one. For a cyclic component they are not comparable at all, which is §4's correction.

**Fact. An account drawn by several instruments is not modelled.** Aggregate state is per contract. The Ensemble case that ES-4 exists for has no counterpart here, and ADR-A131 decision 6's propose, merge and settle has nothing in the development to check it against.

## 4. A correction to an earlier reading

**I reported on 2026-11-07 that decision 5's criterion for admitting a remaining cycle is probably unsound, on the strength of `cycles_break_uniqueness`. That was wrong, and the error is the one §3.3 names.**

The counterexample is a two-cycle between two copies of one cover on a loss of 100, with two self-consistent answers fifty apart. Both are solutions of the simultaneous equations **over determined values**. Decision 5's least fixpoint is over the information order: start every passed fact at Undetermined and iterate. In that reading neither unit can evaluate, because each one's input is Undetermined, so the least fixpoint is both-Undetermined. That is a safe answer and it is not either of the two the counterexample exhibits.

The two notions of fixpoint differ, so the counterexample does not reach decision 5's criterion. Decision 5's "every edge monotone, so that more facts never change a determined outcome" is monotonicity in the information order, which is the right notion for Kleene iteration, and the stated rule (contribution, K7) is what supplies the equation that makes an admitted component determinate.

**What the counterexample does establish**, and it is worth keeping: solving a cycle's equations over determined values, without such a rule, is indeterminate, and the theory's own conclusion is to refuse and report the cycle rather than pick a convention. That is independent support for refusing by default. It is no evidence either way about the admitted case.

**Consequence for E4c.** Its monotonicity proof is over the information order, and this development contributes nothing to it. Treating the waterfall as a head start on E4c would be a mistake.

## 5. Findings

Each is marked with the unit it lands in. Theorem names are given without line numbers, which move.

### 5.1 Ledger

**L1. Conservation has a residual, and this is the form TD-95 asks for.** `conservation_pointwise` proves, for every well-formed contract list, every state list and every allocator satisfying the axioms, that the recoveries plus the residual equal the loss, claim by claim. `conservation` is its sum form and `no_over_indemnity` its corollary. TD-95 records that a shape written as an equality over the postings alone would refuse a correct ledger wherever a ceiling binds, and that which form the shape takes had not been checked. **It is now checked, in an instance.** LG-4 states conservation with an explicit residual term. *Fact for the instance, judgement for the general case per §3.*

**L2. The allocation axioms are four, not five.** `alloc_ok` is exactness, boundedness by each part's own amount, non-negativity, and allocating the whole returns the whole. Zero at zero follows as `alloc_zero` and is not assumed. **Monotonicity is absent, because no theorem needed it.** The removed review note listed five including monotonicity. LG-4 starts from four and adds monotonicity only if one of its own laws needs it, naming that law. *Fact.*

**L3. The allocation rule must be declared data with an identity, never a default.** `allocation_rule_is_material` proves two rules, pro rata to loss and sequential fill, both satisfying every axiom, giving 3 against 5 on the same arrangement. Conservation does not pin the answer. This confirms LG-Q3's "refuse as the default" and makes it load-bearing rather than cautious, and it is why PRI-42's byte-for-byte agreement between evaluator implementations is unreachable if the rule can be defaulted in code. ES-5 is already right to state signing rules as compositions of Ledger merge rules rather than as code. **LG-4 needs a shape that refuses an account drawable by two evaluations with no declared merge rule.** *Fact.*

**L4. Rounding is deferred, not handled, and the deferral states TD-96.** Money is `rat`. The model's own note says an integer, minor-unit refinement would need a rounding residual allocated deterministically for conservation to stay exact. That is TD-96 in the same words, unproved there. `spikes/isabelle-layers/Ledger.thy`'s pro-rata split with a remainder bounded by the number of parts is the complementary half. *Fact.*

**L5. No layer above the ledger may assume a balance is monotone in its input.** `net_is_not_monotone_in_gross` has a gross rising by one and a residual falling by ten, under a franchise. `retained_mono` gives the converse with the franchise excluded, so the condition is exactly identified. Any index, shape or short-cut that assumes a growing input gives a growing balance is wrong, and this bears on the restatement read. *Fact.*

**L6. A declared ceiling belongs on the amount function.** `retention_fn f` is `0 <= f x and f x <= x` for non-negative `x`, discharged once per constructor and then carried as a hypothesis through every step and the whole fold. `apply_draw` in the layers spike floors at zero with nothing declared above it, which is TD-95's other half. **Where the ceiling lives is open**, since LF-Q22(a) already put a maximum magnitude per value space in Quantification and a per-account availability bound is a different thing (§7, Q2). *Fact for the shape, open for the placement.*

**L7. The order in which aggregates erode across events is the caller's.** Aggregate state is threaded through one run, and successive events are separate calls, so the development never fixes it. PDD-14's closure settles it for us as the order draws are settled. The development is consistent with that and is no evidence for it. *Fact.*

**L8. Attribution conserves separately from amounts.** `ledger_conservation` proves that a share matrix whose rows sum to one, with non-negative entries, conserves attribution across parties, and the theory files it under the heading that a common account is a ledger rather than a waterfall position. `case1_and_case3_share_a_waterfall` shows two arrangements with one computation differing only in who bears each amount. **Two conservation laws, each with its own shape**, rather than one folded into the other. Lands in LG-4 and in ES-5's K4. *Fact.*

### 5.2 Ensemble

**E1. The acyclic case of decision 5 is proved in an instance.** `solution_unique_if_acyclic` from finiteness and acyclicity, and `run_is_the_solution` with `run_is_determinate` for the ordered fold computing that solution. Read §3 before citing either. The theory's own sentence is the one worth lifting into the ADR: acyclicity is a property of the documents alone, decidable without arithmetic, and it is the check an engine should run before it is allowed to compute anything. *Fact for the instance.*

**E2. Uniqueness needs acyclicity. Computing by a fold needs a total order. These are two results and we conflate them.** `solution_unique_if_acyclic` needs well-foundedness alone. `run_is_the_solution` is stated over `before n`, a total order. Decision 5's independence-of-order bullet reads "an acyclic graph admits many valid orders, the outcome is the same under every one of them", and `tie_breaking_moves_money` refutes that as written: the empty relation on two covers is acyclic, admits both orders, and they give 60 and 0 against 50 and 30. `fold_is_not_the_solution_of_an_incomplete_schedule` and `silent_schedule_over_indemnifies` make the same point declaratively, the latter paying 120 against a loss of 100.

What saves us is that our graph is over pairs of a unit **and a position**, and LG-Q4(a) gives Ledger its own ordered pair while LG-Q3(c) puts draws at different positions in position order. Positions totalise, valid orders differ only in same-position ties, and decision 5's two phases settle those. **The claim holds because of the positional total order, and that dependency is nowhere stated.** Raised as ES-Q10, with the condition checked separately by C4-A10 and C4-A11. *Fact for the counterexample, judgement for the reading of why we are safe.*

**E3. The fold's correctness rests on a unit reading only its declared predecessors, which is an obligation on our evaluator and not a theorem.** §3.1's congruence lemma holds of the development's body because its deduction reads exactly the declared predecessor set. In our terms a unit that reads a fact it never declared breaks the lemma and with it both uniqueness and the fold. ES-3's read set fetched in one batch, and the passed fact's read-set digest, are the mechanisms that discharge it. **They are load-bearing for the composition law, not merely an optimisation**, and nothing currently says so. *Judgement.*

**E4. Conservation cannot detect a unit that never ran.** Where the state list is shorter than the contract list the remaining contracts are silently dropped and the loss passes through as residual. `conservation_pointwise` carries no length condition, so conservation still holds with a cover missing, while `run_is_the_solution` does assume equal lengths. The development's README calls conservation the cheapest implementation test there is, and it cannot see an omitted unit. **Agreement between evaluator cores and conservation together do not show that every scheduled unit was evaluated. The schedule needs its own completeness check**, every planned unit producing an outcome, and it belongs with the N-version gate rather than inside either core. *Fact.*

**E5. An account shared by several instruments is outside the model.** Per §3.3. ES-4 gets no support from this material, and ADR-A131 decision 6 gets none either. *Fact.*

## 6. The gap between the encodings, the proofs and the runtime

Three artefacts describe the same laws and none of them is derived from another. The OWL and SHACL encodings under `ontology/`, the Isabelle theories, and the runtime components we have yet to build. A law can hold in all three and still be a different law in each.

A code-generation spike on `fml/isabelle-layers` exercised the proof-to-runtime edge from the layers theories and found three things that bear on the evaluator's interface. They are uncommitted at the time of writing and recorded here so they are not lost.

**R1. Generated code cannot represent a cofinite set, and the failure is silent in one target.** HOL's set type has a cofinite constructor that the generated `Bex`, `Ball`, `card` and `trancl` do not handle. Scala warns, six times, all tracing to this one gap. Haskell gives no warning and fails at runtime with a pattern-match error. **The evaluator's interface has to accept finite sets only, stated as a precondition rather than discovered by a caller.** This is the clearest instance of the gap: the law is true in Isabelle, the generated code is a partial function, and nothing in the OWL encoding says a set must be finite. *Fact.*

**R2. A generated target needs type-class instances its caller must supply.** The generator emits only the instances the exported code uses, so a Scala caller passing strings had to provide equality itself. A host language binding is not complete merely because the export compiles. *Fact.*

**R3. Automatic renaming makes the generated API unreadable.** Scala's case-insensitive option resolves collisions and produces names of the shape `Nata`, `seta` and `condition_exta`. Acceptable for a differential oracle, not for an API anyone reads, so the choice between automatic renaming and explicit per-datatype renames follows from whether the target is an oracle or a published binding. *Fact.*

**What the spike established on the positive side.** Eligibility now executes from the generated code. Ten results agree across Isabelle's `value`, a Haskell driver and a Scala driver, covering hierarchical closure, exclusion, Undetermined under an excluded candidate, default inclusion, a flat scheme, and the two composition kinds. Both Haskell builds compile under GHC with no warnings.

## 7. Questions

**WPG-Q1. Is the uniqueness argument general, as §3.1 reads it?** (a) verify by abstracting the body to a parameter carrying the congruence and checking the proof goes through, in a scratch session, before any of this is cited. (b) take the reading on trust and let the non-reinsurance rig find out. (c) treat the instance as the only claim and make no general statement. *Leaning (a), because it is cheap, it is the premise under E1, E2 and E3, and a general theorem is what C4 and E4b both want.*

**WPG-Q2. Where does the declared ceiling live?** (a) on `ldg:AccountDefinition`, as a per-account availability bound beside the existing ceiling. (b) on the draw term. (c) in Quantification beside LF-Q22(a)'s maximum magnitude per value space. *Leaning (a), since the bound is a property of the account and not of one draw on it, and LF-Q22's bound is about a value space rather than about availability. (c) conflates two different things that happen to be upper bounds.*

**WPG-Q3. What does the schedule-completeness check of E4 check against, and where does it live?** (a) the plan's own output, every unit the planning entry point returned producing an outcome, checked in the N-version gate. (b) inside each evaluator core, which makes every core carry it and still cannot see a core that skipped a unit. (c) as a conformance case in ES-3's kit only. *Leaning (a), with (c) as well, since a conformance case proves the check works and the gate is what runs it on real passes.*

**WPG-Q4. Where does an applied proof live, and does this material migrate?** (a) stay outside the repository as background, cite nothing from it. (b) open `tools/proofs/ledger/` beside `tools/proofs/eligibility`, seeded from the general core of §3.1 rather than from the reinsurance instantiation, serving LG-2's three obligations and E4b. (c) extend `spikes/isabelle-layers`, which has no claim records and no gate markers, so neither track can cite it. *Leaning (b) for the general core and (a) for the reinsurance instance, which keeps the applied, insurance-specific development out of the substrate's proofs while letting both tracks cite the part that is substrate. This is a decision for the maintainer and is not mine to take.*

## 8. What this sketch does not settle

- Whether §3.1's reading is right. WPG-Q1.
- Anything about decision 5's admitted cyclic components. §4 withdraws the claim and supplies no replacement.
- Whether our step function has the locality of E3. That is an obligation to discharge, and this material only shows what breaks without it.
- Rounding. L4 states the obligation and neither artefact discharges it.
