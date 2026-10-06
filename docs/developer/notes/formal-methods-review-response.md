<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Response to the review of the formal methods programme

**Status:** note, 2026-10-06. **Review:** an agentic evaluation of the
[formal methods sketch](../sketches/formal-methods.md) and its child sketches, kept outside version
control (`.local/fml-review.md`). Its section numbers are cited as "review §n". **Plan:** the
[formal methods epic](../plans/formal-methods.md), re-sequenced in response.

---

## 1. Summary

The review is right on its five headline points, and the plan and sketches are remediated for each.
The programme is re-sequenced into tracks so that the assurance ledger, the adequacy harness, the
hand-written reference semantics and the design-time models no longer wait for the prover. The prover
spike stays the first step, as decided on 2026-10-06, but narrowed, with declared abandonment
conditions. Six points are rebutted or refined (§3). Four of them need the human's decision before
the spike starts (§4).

## 2. Dispositions

| Review | Finding | Disposition | Remediated in |
|---|---|---|---|
| S1, §3.1 | the evidence of §4 justifies T0 to T4, not the prover | **agree**. The prover's case is now made on its own terms: compiler correctness, universally quantified adopter guarantees, template theorems, the combinator algebra with rounding, and the kernel | sketch §5.1, §8 |
| S2, §3.2 coupling A | the reference semantics waits on the prover | **agree**. A hand-written reference in Python comes first (track B) and becomes the specification any mechanisation formalises | plan track B, reference evaluator sketch, FM-D5 |
| S2, §3.2 coupling B | native tooling is a performance decision, not a verification one | **agree**. Decided per job family on measurement against a Python baseline (track F). Solver-bound families stay Python | plan track F, workers sketch §2, FM-D9 |
| S4, §3.3 | dual maintenance is uncosted, and one option is missing | **agree on the goal, refine the direction** (R1) | adequacy sketch §4, FM-D12 |
| §3.3 | theorem statements extracted into the literate README | **agree** | adequacy sketch §6, FM-D2 |
| S5, §3.4 | no kill criteria, no cost per law, no end-to-end law | **agree**. Kill criteria, standing metrics and an end-to-end law in the spike. **The law chosen differs** (R2) | plan §5, §6, phase 0 |
| §4.1 | claim identity, assumption audit, non-vacuous interfaces, assumptions, scope, model, assertor, the ordering of levels, the gate's incentive | **agree, all** | assurance records sketch |
| §4.2 | profile EARL, PROV-O, SHACL reports and in-toto rather than mint a vocabulary. The parent and child sketches disagree on the claim model | **agree**. EARL is a W3C Note no longer maintained, which a profile tolerates. The parent now uses the child's reified claims | assurance records sketch, sketch §7.4 |
| §4.3 | `Env` leaks runtime data into design time | **agree**. `DesignEnv` and `RunEnv`, with a projection and a lemma, checked by the architecture check | sketch §7.2, adequacy sketch §3, reference evaluator sketch |
| §4.4 | abstraction soundness, model digests, inductive invariants first, vacuity, monitorability | **agree, all** | instrument assurance sketch §4, §5 |
| §4.5 | template theorems need rely and guarantee | **agree**. A correction that matters directly to adopters | instrument assurance sketch §2.2, sketch §11.2 |
| §4.6 | monotonicity covers information increase, not revision | **agree**. The public guarantee is restated precisely, and retraction is a design question the formal work must settle | sketch §8.1, instrument assurance sketch §2.1 |
| §4.7 | three different third values are conflated | **agree**. A three-by-three semantics: three-valued atoms, prefix verdicts, and a separate check outcome | instrument assurance sketch §3 |
| §4.8 | real stores deviate from formal SPARQL | **agree**. A fragment gate, a cross-store conformance suite, and the mapping of "not a value" to Undetermined as the first compiler theorem | sketch §8.4 |
| §4.8 | well-founded semantics as normative for Datalog | **rebut** (R4) | sketch §8.4, FM-D11 |
| §4.9 | RFC 8785 numbers are binary floating point. Rounding breaks order independence. Partial operations | **agree**. The codec carries quantities as lexical strings. The rounding and residual theorem is the first non-trivial kernel result. Partiality maps to reasons | adequacy sketch §5, sketch §8.1, §9.1 |
| §4.10 | reproducibility of solver results, the cache key, `NotDecided` caching, resource envelopes, tool identity in the read set | **agree, all**. The cache key omitting bounds is a real defect. Separating tool identity from semantic inputs needs an ADR-A27 addendum (the invalidation rule), with the two kinds of read-set entry stated in ADR-A92's terms | workers sketch, assurance records sketch, FM-D15 |
| §4.11 | the RDF round trip, RDFC-1.0, unformalised semantic commitments | **agree**, with one refinement on MCN (R5) | adequacy sketch §4, §5 |
| §4.12 | joint satisfiability, independence and non-vacuity of each layer's laws | **agree**, promoted to track A's first deliverables | plan track A |
| §5 | category theory rows are not of equal value | **agree**. Profunctors demoted, regeneration naturality made a property test now, institutions kept as vocabulary, conservativity to be defined | sketch §10 |
| §6, W1 to W11 | worker defects | **agree, all eleven** | workers sketch |
| §7 | Phase 0's criteria are never stated | **rebut in part** (R3). They were declared in the phase 0 plan, which the review did not read. Its additions and its reduction are adopted | phase 0 |
| §7 | Lean 4 dismissed too quickly | **agree**. The decisive argument is now stated | phase 0 §1 |
| §7 | tool versions as names | **agree**. Digests are normative, names are labels | assurance records sketch |
| §8 | licences of nuXmv and UPPAAL, library licence inheritance, CI caching, proof review | **agree, all**. Timed automata are avoided. Statements are reviewed and proofs treated as opaque, with an assumption audit | sketch §6 FP4, §15 |
| §9 | the specification gap reaches adopters. Structural controls against overclaiming. Exchange needs signatures. A regulatory crosswalk | **agree, all** | instrument assurance sketch §6, §7, assurance records sketch §7 |
| §10 | responses to FM-D1 to FM-D10 and the open questions | **agree**, except where R1 to R6 apply | plan §7 |
| §11 | re-sequence into tracks, with kill criteria | **agree, with one constraint** (R6) | plan |

## 3. Rebuttals and refinements

### R1. The direction of generation (review §3.3)

The review proposes generating shapes from the theory for the structurally closed portion. That
removes a maintenance stream, but it moves normativity into the theory for that portion, against
FP1, and it puts the prover on the path of every structural change. LATTICE already has a single
normative source: the literate README, from which the spec, vocabulary and shapes are extracted.

**Position.** Extend the literate pipeline: the README remains the one source, and from it are
generated the shapes (as today) and the theory's closed datatypes (inductive types for closed
vocabularies, records for node shapes over functional properties, cardinalities as invariants).
AD-Q1's objection does not apply here, because generated *datatypes* are easy to prove against. Only
generated *laws* are hard. Laws stay hand-written, with their statements extracted back into the
README. Drift becomes regeneration plus a diff, as the review wants, without a second normative
source. FM-D12.

### R2. The end-to-end law for the spike (review §3.4)

The review proposes carrying `ins:I7` end to end. I7 has no shape (its register is "semantic,
mandatory adversarial probe"), no fixtures, and its breach derivation (CCS sketch §6.1) is specified
for C13, which is not built. Carrying it in the spike would first require specifying breach
derivation precisely, which recreates the coupling the review warns against in §3.2. The chain
prose, shape, fixtures, statement, proof, adequacy, record, report and gate cannot be exercised
when two of its links do not exist.

**Position.** Carry Eligibility's L15 (set readings) and L16 (negation) end to end. They have prose,
structural shapes, examples with expected decisions in `tools/test_eligibility_examples.py`, and
compiled backends in `tools/mork_compilers`. So the spike also exercises the differential check of a
compiled backend against the formal statement, which I7 cannot. I7 becomes the first Instrument
target once C13's breach derivation is specified. FM-D13.

### R3. Phase 0's criteria (review §7)

The review says the criteria are never stated and that the result "will be decided by whoever
writes the comparison". The phase 0 plan declared seven weighted measures (§4), a decision rule and a
tie-break (§6), and fairness rules (§8), including proof-repair cost under a scripted change (M3). The
review read the sketches, not the plan. Its additions are still right and adopted: cost to carry one
law end to end, the agent's proof success rate, library fit and consistency with the earlier Rocq
choice. Its reduction is adopted too: binding resolution is no longer formalised twice, and moves to
track C's design models.

### R4. Datalog's normative semantics (review §4.8)

The review proposes well-founded semantics as normative, with stratifiable emission and an agreement
theorem. Well-founded semantics' third value, "undefined", arises from cycles through negation. It is
not Undetermined, which means the evidence does not establish the fact. Making it normative adds a
fourth kind of third value, the conflation the review itself warns against in §4.7. LATTICE's laws
already refuse such cycles at design time (I6, B10), so a well-founded model would only ever be
computed for programs the laws forbid.

**Position.** Normative semantics is stratified Datalog with dual predicates for Permitted and
Denied, as the logic encodings note recommends. Undetermined is neither predicate holding. The
compiler refuses a non-stratifiable program with a diagnostic, which is the laws' own position. The
theorem to prove is that on the emitted fragment, the dual-predicate model equals the Kleene
denotation. An engine computing the well-founded model may run the program, since on stratified
programs the two coincide. FM-D11.

### R5. MCN and graph isomorphism (review §4.11)

The review calls graph isomorphism "the wrong tool" for MCN's losslessness. RDFC-1.0 is itself a
canonical labelling, which decides isomorphism, so the two are the same check. The existing MCN
tests' use of `rdflib`'s isomorphism is sound. The refinement adopted is to state comparisons against
RDFC-1.0 canonical form, which is standard and byte-comparable, for the codec and adequacy checks.

### R6. Re-sequencing and the first step (review §11)

The review's tracks are adopted. The human decided on 2026-10-06 that the cheap decisive experiment
is the plan's first step, so the narrowed spike (track D) stays first. Tracks A, B and C do not
depend on it and start alongside it, each after its own ADR. Track E starts only if D passes its
abandonment conditions.

## 4. Decisions for the human

| # | Decision | Recommendation |
|---|---|---|
| FM-D11 | Datalog's normative semantics | stratified, with dual predicates (R4). **Decided 2026-10-06** |
| FM-D12 | the direction of generation for the closed portion | from the literate README to both shapes and theory datatypes (R1). **Decided 2026-10-06** |
| FM-D13 | the law carried end to end in the spike | L15 and L16, with I7 first after C13 (R2). **Decided 2026-10-06** |
| FM-D15 | tool identity in derived artefacts' read sets | separate semantic inputs from tool identity, with tool changes marking records stale, through an ADR-A27 addendum (the invalidation rule), with the two kinds of read-set entry stated in ADR-A92's terms **Decided 2026-10-06**, with a suspect state for known soundness fixes |
| the tracks | whether A, B and C start alongside the spike | **Decided 2026-10-06: staggered.** C1, C2, B1 and B2 alongside the spike, A1 to A4 after gate D, B4 with C11a and C12, C3 with C13a (plan §3) |
