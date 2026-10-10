<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Response to the implementation-level review of the formal methods programme

**Status:** note, 2026-10-08. **Review:** an independent AI review of a synthesis brief prepared
for cross-model inspection, kept outside version control
(`.local/formal-methods-review-brief.md`, and the review itself at
`.local/formal-methods-more-feedback.md`). Its section numbers are cited as "review §n", its
open-question answers as "review Qn". **Plan:** the [formal methods epic](../plans/formal-methods.md)
and its track plans (B, C, E). **First review:** this is the second review of this programme; the
first is answered in [formal-methods-review-response.md](formal-methods-review-response.md), whose
dispositions stand unchanged.

---

## 1. Summary

The review was given only a compressed synthesis document, not the repository, and says so. Most
of its findings are correct as findings *about that document*: the brief overclaimed independence,
overclaimed coverage, and in a few places described a result the underlying artefact does not
actually establish. Separating what is wrong with the brief from what is wrong with the actual
plan and code matters, because the two are not the same list, and this response keeps them apart
(§2's disposition table has a column for it).

**Three findings are real defects in the committed artefacts, not just in how they were
described, and are the priority of this response:**

1. **The gate's statement digest does not cover the definitions a gated statement depends on**
   (review §2.1). A redefinition of `or3`, `neg3` or `decision_leq` changes what every gated
   lemma means without changing any digest. Confirmed against `tools/proofs/eligibility/gate.py`
   directly: true as described.
2. **The gated claims underdetermine the semantics they are meant to protect** (review §2.2).
   The TA2 lemmas hold of the identity function in place of `neg3`; the TA1 lemmas hold of a
   constant function in place of `or3`/`and3`. Confirmed: true as described.
3. **The Alloy model's first counterexample was degenerate** (review §4.2): `Scheme`'s signature
   never excluded a concept from being recorded as its own `skos:broader` parent, so the
   counterexample Alloy reported first relied on a self-loop. **Checked directly this session**
   (not merely conceded): two well-formedness facts were added
   (`tools/models/vocabulary-scheme-composition/SchemeComposition.als`, irreflexive and acyclic
   `broader`), and `NoOverlapDisagreement` was re-run at the same scope. **It still returns SAT**,
   with a new, non-degenerate witness (two schemes sharing one concept, each recording a different,
   distinct concept as its parent). The finding the model was built to support survives; its first
   piece of evidence for it did not. Recorded in
   [the model's own README](../../../tools/models/vocabulary-scheme-composition/README.md).

Everything else is either **already correctly scoped in the actual track plans and sketches**
(the brief overclaimed what the plans themselves never claimed — §3), **a genuine gap worth a
queued corrective slice** (§4), or **a rebuttal** where the review's reasoning does not hold up
(§5). None of it changes FM-D1 (Isabelle) or any other closed decision. One new open decision is
added (FM-D17, §6).

## 2. Disposition, by review section

| Review | Finding | Disposition | Remediated in |
|---|---|---|---|
| §1.1 | the brief's §3 implies Isabelle covers L9-L16; only L15/L16 (set readings, negation) are mechanised today, not L9-L12/L14 (concept matching) | **agree, about the brief; not a plan gap.** Concept matching is track E's E2, already scoped, not yet started (epic plan §4) | this note only; no plan change needed |
| §1.2 | "seven seeded mutations across all three modes" overclaims; no mutation was made in the proof or model modes | **agree.** No mutation testing has been done of `tools/proofs/` or the Alloy model | track E's E1.4, track C's C2 log (§4 below) |
| §1.4 | T1 (property testing) is called "not started" elsewhere while B2/B3 already are property tests in practice | **agree, labelling only.** The epic sketch's rung table never actually claims T1 is unstarted (it is a capability description, not a status report); only the compressed brief said so. Track B's B2/B3 are T1 in substance | this note; track B plan gets an explicit T1 line (§4) |
| §1.5, §3.3 | "every compiler backend" overclaims; only SPARQL and SHACL are differentially tested | **rebut as a plan finding, agree as a brief error.** Track B's own sketch (§3) already scopes B2 to SPARQL and SHACL by name, with a stated reason (SWRL and OWL are tested only where they do not already refuse the input). The brief dropped that scoping when it compressed the material | track B plan gets an explicit per-backend projection statement (§4) |
| §1.6, §3.4, §2.5 | `kernel.py` is a port of `KernelLaws.thy`, not an independent derivation, so proof mode and reference mode share one hand-written truth table as their only source of the semantics | **agree, this is real.** Track B's own sketch already says B1 is "a faithful port... not an independent re-derivation" (§2) — so the brief's claim of independence was its own error, not the plan's — but the underlying risk (one hand-written table, two consumers, no independent check of the table itself) is real and worth closing | a new decision, FM-D17 (§6): generate the truth-table equations from one README source into both tools |
| §1.7 | "the other direction of De Morgan" is the wrong name for the refuted equation | **agree**, terminology only, no artefact affected | this note only |
| §1.8 | the brief elides code it quotes | **agree**, acceptable for a compressed brief, not a plan defect | none |
| §1.9 | scoring margins have no stated scale | **agree**, a brief clarity issue. [ADR-A-FM1](../../architecture/decisions/ADR-A-FM1-formal-methods-prover-choice.md) and [the D4 report](../notes/formal-prover-experiment.md) already state the full scale (0-100) and running total; the brief should have cited them instead of restating a bare number | none |
| §2.1 | the gate digest does not cover transitive definitions | **agree, major, confirmed.** | track E's E1.4 (§4) |
| §2.2 | gated lemmas underdetermine the semantics (TA1/TA2 satisfied by degenerate functions) | **agree, major, confirmed by inspection of `KernelLaws.thy`** | track E's E1.4 (§4) |
| §2.3 | set-reading permutation/duplication invariance and empty-list base cases are neither stated nor gated | **agree** | track E's E1.4 (§4) |
| §2.4 | `by eval` is oracle-tagged, not kernel-checked; the brief's account of how it fails is wrong (a failed proof method, not a type error) | **agree on both counts.** The technical correction is accepted as stated: a false proposition under `by eval` fails as a tactic, it does not fail to typecheck | track E's E1.4 (§4) |
| §2.5 | the generation boundary (closed datatype only) sits where it adds least value; the real normative content (the truth tables) is hand-written twice | **agree, refine the direction, do not reverse FM-D12.** FM-D12 ("the literate README is the one source, generating shapes and the theory's closed datatypes") is not wrong, it is incomplete: a truth table is also closed, tabular, generatable data, not a law, so generating it does not touch E1's rule that laws stay hand-written and reviewed | FM-D17 (§6) |
| §2.6 | the "assumption audit" named in the epic sketch (§3) is never described for track E | **agree.** No description of what the audit checks (`sorry`, `quick_and_dirty`, `axiomatization`, oracle tags via `thm_oracles`) exists anywhere in track E's documents | track E's E1.4 (§4) |
| §2.7 | verification is a local, undated event: no pinned Isabelle version recorded per claim, the CI job is `continue-on-error` and untested, the link between `gate.py` passing and the build having actually succeeded is not stated | **agree, and already partly tracked.** The image-route gap for Isabelle is already a named, deliberate deferral (epic E9, FM-D16, track E's own status record: "deferred... to conserve tokens"). What is new here is the narrower point that even the *native* route's claim records do not state which build they followed from | track E's E1.4 (§4) |
| §2.8 | a 3×3 finite truth table does not need a prover on its own terms | **rebut.** The epic sketch states this explicitly already (§5.1): the kernel is in the prover programme "small, stable, and every later theory rests on it," not because its own lemmas are individually hard. The review's own §2.8 is really a complaint about the brief's framing, which did present the kernel lemmas as if they were the interesting result. The plan never made that claim | none; the brief's framing was the only thing at fault |
| §2.9 | `can`/`Goal.prove` shows a tactic failed, not that a definition was rejected by the system; weaker evidence than Rocq's `Fail Definition` | **agree.** This is a real, specific epistemic gap in M6's resolution (`formal-prover-experiment.md`) | an addendum to ADR-A-FM1 (§4) |
| §3.1 | mode 3's core rationale (catching a bug shared through `_expand`) has never been tested; both found bugs were in the reference, not the compiler | **agree, major, and the single most valuable action item in the whole review** | track B's new B2.1 (§4) |
| §3.2 | correcting the reference by reading the compiler's own template erodes independence over time | **agree.** The fix is process, not code: every disagreement needs a recorded adjudication naming which side was wrong and its normative citation, never settled by "the compiler says so" alone | track B's new B2.1 (§4) |
| §3.3 | only SPARQL/SHACL tested; the per-backend projection of the three-valued domain is never stated, especially for two-valued SHACL | **agree the projection should be stated explicitly** (the scoping to SPARQL/SHACL itself was already correct, see §1.5 row above) | track B's new B2.1 (§4) |
| §3.5(a) | `decide_concept_match` with `hierarchical=True` and no `scheme` returns `Denied` when `required` is non-empty, where the same reasoning that fixed bug 1 (L9's scheme-membership precondition) suggests `Undetermined` | **agree, confirmed by re-reading `tools/reference/eligibility/.../denotation.py` directly this session. This is a credible, unverified defect, same class as the already-fixed bug 1.** Not fixed in this session (fixing it needs a new fixture and a judgement call against the README's exact wording of L9, which is a test-writing task, not a documentation one) | flagged explicitly in track B's status record as the next concrete defect to verify and, if confirmed, fix |
| §3.5(b) | empty `required` under a hierarchical, non-flat scheme falls through to `PERMITTED` (L12's default), while the same empty `required` under a flat scheme (L14) gives `UNDETERMINED` | **rebut, most likely intended, not a defect.** L14 is specifically the flat-scheme precondition; a non-flat scheme is not subject to it and L12's default inclusion is exactly Eligibility's stated behaviour for "exclusions only, or nothing required". Worth a one-line confirmation against the README, not a code change | track B's status record, as a thing to confirm, not fix |
| §3.5(c) | the required-but-unmatched → `Denied` branch carries no law-ID comment | **agree**, a traceability gap matching the freshness checker's own discipline | track B's new B2.1 (§4) |
| §3.5(d) | `ancestors()`'s reflexivity is implicit | **rebut, already documented.** The method's own docstring says "the concept and everything above it, reflexive-transitive," read directly this session | none |
| §3.5(e) | cycle behaviour of `ancestors()` is unspecified | **rebut, already documented.** The docstring states it directly: "safe over a cyclic ordering (visited members are never requeued), though L9 itself requires the bound scheme's ordering to be acyclic for hierarchical match to have a truth condition at all" | none |
| §3.5(f) | L13, L15, L16 "missing" from `decide_concept_match` | **rebut, by design, not a gap.** L15 (set readings) and L16 (negation) are deliberately in `decide_condition`, the function one layer up, exactly as its own docstring says: "composed over L9-L12/L14's single-candidate decision." L13's coverage was not checked this session (the law register was not re-read) and is listed as open, not conceded | L13's coverage: track B's status record, to confirm |
| §3.6 | 14 fixed differential fixtures is thin; the input space is bounded and exhaustible | **agree** | track B's new B2.1 (§4) |
| §3.7 | the differential harness's SPARQL engine is unnamed | **agree**, should be stated explicitly (it is rdflib, via `tools/mork_compilers`' own test helpers) | track B's new B2.1, documentation only |
| §3.8 | 63 total tests is accurate, but should be stated as exhaustive where it is | **agree, confirmed this session** (28 kernel + 21 denotation + 14 differential = 63, re-counted directly via `pytest --collect-only`, not taken from memory) | this note; wording only |
| §4.1 | `EverySourceResolves` is true by construction, not a result | **rebut as a plan finding, agree as a brief error.** Track C's own status record already says exactly this ("a self-consistency check on the model's own definition... not a deep claim, and recorded as such") | none, the plan was already right |
| §4.2 | the counterexample is degenerate (a self-loop) | **agree, confirmed and fixed this session** (summary, §1 above) | `SchemeComposition.als`, its README, track C status (§4) |
| §4.3 | the model never builds a composed scheme or checks a decision-level property; it only shows two relations over shared nodes can differ | **agree, major.** This is the correct next step, not yet done | track C's new C2.2 (§4) |
| §4.4 | ADR-A116's actual accepted rule (forbid overlap) was never modelled; the motivating cases (HQ-4, IMA-D4a) were never run against it to check it isn't over-strict | **agree, major, and should happen before or alongside ADR-A116's acceptance**, not after | track C's new C2.3 (§4), flagged to the maintainer as a pre-acceptance recommendation |
| §4.5 | no non-vacuity `run`, no pinned Alloy version, no re-run cadence tied to ADR changes | **agree, minor-moderate** | track C plan, process note (§4) |
| §5.1 | the mutation evidence is a spot check (4 mutations), not a measured mutation score; "not applicable" for the proof/model modes was itself avoidable | **agree** | track B's new B5 (mutation score tooling), track E's E1.4 (§4) |
| §5.2 | M9 was removed for rewarding an unacted-on decision, but M5's Scala credit rests on an equally unexercised capability, without the same scrutiny; no sensitivity analysis of the scoring exists | **agree, this is a real and fair point about consistency of method** | an addendum to ADR-A-FM1 (§4); does not reopen FM-D1 |
| §6 | track selection was readiness-driven, and the highest-value open item (protocol verification, T4) has no stated trigger | **agree, and already in motion**: this is exactly what the Persistence formal-methods plan (`formal-methods-track-h.md`, drafted alongside this response) is for — see §7 | track H |
| review Q1 | T1's absence as a named discipline is a real, cheap-to-close gap; proved Isabelle lemmas should be run as properties against compiled backends | **agree, adopt directly** | track B plan, new explicit T1 statement (§4) |
| review Q2 | ADR-A116's no-overlap rule may be too strict for its own motivating cases | **agree, this is the right question and it is still open** | track C's new C2.3 (§4) |
| review Q3 | the Scala `export_code` claim behind part of M5's score has never been exercised | **agree.** Already named as a near-term follow-up in FM-D10's own decided text ("documented, not yet exercised"); this review raises its priority, it does not introduce a new gap | ADR-A-FM1 addendum (§4), restates the existing follow-up with the priority this review gives it |
| review Q4 | the proof side needs the same freshness discipline as the reference side; a law-name comment satisfies a text check without testing anything | **agree, adopt directly** | FM-D17 (§6), track E's E1.4 (§4) |
| review Q5 | one layer's evidence (Eligibility) is not enough to justify the trajectory; pilot a structurally different layer before expanding further | **agree with the reasoning; already in motion with a stronger pilot than the one proposed.** The review suggests Quantification (arithmetic, rounding). The maintainer has instead directed the next pilot to Persistence (`persistence-fml.md`), which is structurally different in a stronger sense than Quantification would have been: it is the first layer needing protocol/concurrency verification (T4) at all, not just a different T0/T5 domain. See §7 | track H |

## 3. What this review's own §1 gets right, and the limit of that

Section 1 of the review is itself careful, graded work: it separates what is wrong with the
*document* from what is wrong with the *artefacts*, states severities, and in several places
(§3.5(d), §3.5(e), §4.1) credits the brief with a claim the actual repository already supports
more carefully. That discipline is followed here too: of the review's roughly forty numbered
findings, six are rebutted as describing the brief rather than the plan (§2's "rebut as a plan
finding, agree as a brief error" rows), two are rebutted outright (§2.8, §3.5(d)/(e) — already
documented), and the rest are either agreed and queued, or already correctly scoped.

## 4. Corrective slices queued

None of these are executed in this session beyond what §1 already reports as done. Each is now a
named, findable slice in the owning track's plan and status record, so the next session does not
have to rediscover them from this note.

| Track | New slice | Addresses | State |
|---|---|---|---|
| E | **E1.4**: harden the gate and the kernel theory — digest transitive definitions (review §2.1), add characterising lemmas (full truth table, both De Morgan forms, algebraic laws) so TA1/TA2 cannot be satisfied by a degenerate function (§2.2), state and gate permutation/duplication invariance and the empty-list base cases for `some_value`/`every_value` (§2.3), replace `by eval` with `simp`/`code_simp`/`normalization` (§2.4), describe and implement the assumption audit via `thm_oracles` (§2.6), record the Isabelle build identity each claim depends on (§2.7), run a mutation set over `KernelLaws.thy`/`Eligibility.thy` equivalent in spirit to B1's own (§5.1) | review §2.1-§2.7, §5.1 | not started |
| B | **B2.1**: seed a fault directly into `tools/mork_compilers`' `_expand` and into one SPARQL/SHACL template, confirm the differential tests fail (review §3.1, the single highest-value item in the whole review); establish the adjudication-record process for every reference/compiler disagreement (§3.2); state the per-backend projection of {Permitted, Denied, Undetermined} explicitly for SPARQL and SHACL (§3.3); name the differential harness's SPARQL engine (rdflib) explicitly (§3.7); extend the fixed 14-case differential suite to bounded-exhaustive generation over schemes up to 3-4 concepts (§3.6); add the missing law-ID comment on the required-but-unmatched branch (§3.5(c)); confirm L13's coverage against the README (§3.5(f)) | review §3.1-§3.3, §3.5-§3.7 | not started |
| B | **B2.2** (verify, and fix if confirmed): `decide_concept_match` with `hierarchical=True` and `scheme=None` returns `Denied` rather than `Undetermined` when `required` is non-empty — same bug class as B2's already-fixed scheme-membership defect, re-read and confirmed plausible this session but not test-driven or fixed | review §3.5(a) | not started, flagged as the next concrete defect |
| B | **B5**: run an automated mutation-testing tool (for example `mutmut`) over `tools/reference/eligibility` and report a measured mutation score, rather than the four hand-picked spot checks recorded so far | review §5.1 | not started |
| C | **C2.1**: add irreflexivity and acyclicity well-formedness facts to `Scheme.broader` and re-run `NoOverlapDisagreement` | review §4.2 | **done this session** — see §1 above and the model's README |
| C | **C2.2**: extend the Alloy model to construct the composed scheme directly (not just show two source relations can differ) and check a decision-level property against Eligibility's L9-L11 (does a decision under the composed scheme ever disagree with a decision under any one source scheme alone) | review §4.3 | not started |
| C | **C2.3**: model ADR-A116's actual accepted rule (forbid overlapping membership) as a fact, and `run` the real HQ-4 and IMA-D4a configurations to confirm they are admitted, not rejected by a too-strict rule | review §4.4, review Q2 | not started, **recommended before or alongside `ADR-A116`'s acceptance**, not after |

## 5. Rebuttals, stated once

### R1. The kernel does not need to earn its own cost (review §2.8)

The epic sketch already states, in its own words, why the kernel is in the prover programme: "the
kernel and binding resolution... small, stable, and every later theory rests on it" (sketch
§5.1), not because `or3`/`and3`/`neg3`'s individual lemmas are hard to establish by other means.
Every later Eligibility theorem (L9-L16, the eventual compiler-correctness proof, E2-E5) is stated
over this kernel. A cheaper technique could establish the kernel's own finite properties alone,
and nothing in the plan claims otherwise; the review's complaint is accurate only against the
compressed brief, which did present the kernel lemmas as though they were the interesting result.

### R2. `ancestors()`'s reflexivity and cycle-safety are already stated (review §3.5(d), §3.5(e))

Both properties are in the function's own docstring, read directly this session:
"`concept` and everything above it, reflexive-transitive... Safe over a cyclic ordering (visited
members are never requeued), though L9 itself requires the bound scheme's ordering to be acyclic
for hierarchical match to have a truth condition at all." The review's uncertainty here is
reasonable given it worked from a brief rather than the code, and is resolved by the code itself,
not by a change to it.

### R3. `EverySourceResolves` was already correctly characterised (review §4.1)

Track C's own status record already says: "a self-consistency check on the model's own
definition of `composed`... rather than a deep claim, and recorded as such." The review's
criticism is entirely fair against the compressed brief, which dropped that qualification; it was
never the plan's own position.

## 6. New decision: FM-D17

| # | Decision | Recommendation | State |
|---|---|---|---|
| FM-D17 | whether to widen FM-D12's generation direction from "closed datatypes only" to "closed datatypes and closed truth-table equations", generated from one README source into both `tools/proofs/<layer>/*.thy` and `tools/reference/<layer>/*.py`, so the kernel's semantics has exactly one hand-written statement instead of two independently fallible ones | **recommended: yes.** It closes review §1.6/§2.5/§3.4/Q4 at the design level rather than by documentation alone, and it does not touch E1's rule that laws (as opposed to definitions) stay hand-written: a truth table is data, not a theorem | open, for the maintainer |

## 7. Relationship to the Persistence pilot

Review §6 and review Q5 both recommend the same thing from different directions: pilot the
three-mode template on a layer structurally unlike Eligibility before investing further, and name
protocol/concurrency verification (rung T4, never yet used anywhere in this programme) as the
highest-expected-value item still untouched. `docs/developer/plans/formal-methods-track-h.md` and
its sketch, drafted alongside this response from `docs/developer/notes/rdf-engine/persistence-fml.md`,
are exactly that: Persistence is not a finite three-valued kernel, it needs TLA+/Quint protocol
models from its first slice, and its own calibration set (three recorded remediation passes,
Appendix D of the persistence engine notes) gives it the same kind of "what would a cheap
technique have found" evidence track D used to justify the prover. See track H's plan §1 for the
full argument.
