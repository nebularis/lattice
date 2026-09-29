<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Logic encoding: research items

Version 0.1. A register of questions raised by the
[logic encodings note](../notes/logic-encodings.md) that are worth investigating and **should not be
adopted without that investigation**. Each item states what would be gained, what must be verified,
what it would cost to be wrong, and what evidence would close it.

This is not a plan and nothing here is scheduled. Items that graduate become slices in
[normative-rule-substrate](../plans/normative-rule-substrate.md) or ADR amendments.

**What was adopted rather than researched**, and so does not appear here:

| Adopted | Where | Why it needed no research |
|---|---|---|
| Dual-predicate encoding as the reference semantics | [mapping §16.5](legalruleml-mapping.md) | checked against L10, L11, L12 and `MissingCandidate` and reproduces all four. Verifiable by inspection |
| NAF over derivations sound, NAF over evidence licensed | mapping §16.5 | follows from stratification. Makes A-105 simpler, not harder |
| LegalRuleML JSON AST replacing the escaped string | [wire §8.0](normative-wire-protocol.md) | strictly better on every axis. No trade to study |
| `rules` tier with named closures | wire §8.0.1 | a superset of a form already designed |
| `capabilities` on the wire | wire §8.2 | ADR-A24's declared non-capability, made visible |

---

## Contents

| # | Item | Class | If wrong |
|---|---|---|---|
| [R1](#r1-does-a-normative-json-ruleml-serialisation-exist) | A maintained JSON RuleML serialisation | verification | we ship a competing dialect |
| [R2](#r2-datalog-as-reference-semantics-how-far-to-take-it) | Datalog as reference semantics, how far | design | over-commit to a formalism, or under-use a free proof |
| [R3](#r3-set-readings-and-the-closed-value-set) | Set readings and the closed value set | **defect probe** | a law is unsound and parity tests disagree |
| [R4](#r4-odrl-as-the-wire-shape-rather-than-a-projection) | ODRL as the wire shape | design | adopt a standard that cannot carry chains or priority |
| [R5](#r5-scasp-for-justifications-and-controlled-english) | s(CASP) for justifications | capability | build a bespoke renderer where one exists |
| [R6](#r6-what-the-ingress-pipeline-stores-for-a-payload) | What ingress stores for a payload | design | egress parses untrusted text unnecessarily |
| [R7](#r7-answer-set-programming-for-competing-interpretations) | ASP for competing interpretations | capability | force G5 into a formalism that cannot hold it |
| [R8](#r8-shacl-12-rules) | SHACL 1.2 rules | **watch** | miss a standard home, or bet on one that does not land |
| [R9](#r9-defeasible-logic-translations-and-what-n7-means) | Defeasible translations and N7's intent | **soundness** | claim a semantics we do not implement |
| [R10](#r10-engine-selection-if-and-when) | Engine selection | deferred | premature dependency |
| [R11](#r11-prior-art-on-three-valued-expressions) | Prior art: FEEL, CEL, Cedar, Rego | survey | repeat a known mistake |
| [R12](#r12-symboleo-and-obligation-lifecycle) | Symboleo and obligation lifecycle | design input | reinvent a studied state model |

---

## R1. Does a normative JSON RuleML serialisation exist?

**Class:** verification. Cheap, and blocking for the wire sketch's §8.0.

**Why it matters.** The wire sketch defines a JSON abstract syntax for LegalRuleML derived from the
node/edge alternation of the normalised XML. If RuleML or OASIS already publish one, defining our
own creates a competing dialect with the same purpose, which is the specific failure the
"checklist, not dependency" ruling exists to avoid.

**To verify.**
- The RuleML wiki and its specification set, for a JSON or JSON-LD serialisation at any maturity.
- Whether the LegalRuleML TC has published or drafted one since the 2021 standard.
- Whether the RuleML metamodel (referenced as under development in LRML §3.9) has landed, since a
  metamodel implies a canonical RDF form and possibly a JSON one.

**Closing evidence.** A citation either way. If one exists, adopt it and delete our dialect. If one
exists but is unmaintained or partial, record why we diverge.

**Cost of being wrong.** Low to fix early, high to fix late: a published `lrml-json-1.0` dialect
that turns out to duplicate a standard is an interoperability embarrassment and a deprecation.

---

## R2. Datalog as reference semantics: how far to take it?

**Class:** design. The single largest question in the note.

**What is already settled.** The dual-predicate encoding reproduces the Eligibility laws
(mapping §16.5). That is not in doubt.

**What is not settled** is which of three roles Datalog takes.

| Role | Commitment | Gain | Risk |
|---|---|---|---|
| **A. Documentation only.** The translation appears in an ADR as an explanatory device | none | precision in prose | drifts from the implementation, becomes decorative |
| **B. Reference semantics with property tests.** The translation is executable, and "Datalog outcome equals evaluator outcome" is a test over every conformance fixture | a test-only Datalog engine, ADR-A83-shaped | **a second independent implementation of the laws.** Catches evaluator defects that a single implementation cannot | test-suite weight. A second thing to keep current |
| **C. A production backend.** Datalog joins SPARQL, SHACL, SWRL and OWL as a compile target | an engine on the runtime path, ADR-A24 amendment | performance, incremental maintenance, native aggregates | a whole dependency and semantics on the hot path |

**The note recommends B**, and B looks right, but it should be argued rather than assumed. The
argument for B is the same one that justifies `platform/reasoning-testkit`: an independent checker
of a semantics we otherwise verify only against ourselves.

**To verify before choosing B.**
- Whether a test-only Datalog engine can be isolated as cleanly as the reasoner. `reasoning_isolation_check.py`
  matches `hermit|openllet|pellet|drools|owlapi|owlready|jpype|py4j|pyjnius`, so a Datalog engine
  does **not** currently trip it. Whether it *should* is an ADR-A83 question, and the answer is
  probably yes: the same argument applies.
- Licence of any candidate engine, since ADR-A83 already has to isolate an AGPL reasoner.
- Whether the property test can run without the engine present, skipping as the reasoning tests do.

**Cost of being wrong.** Choosing A wastes a genuinely free correctness proof. Choosing C puts a
formalism on the runtime path before any measurement justifies it, which the cross-check already
deferred with triggers.

---

## R3. Set readings and the closed value set

**Class:** defect probe. **The highest-value item here**, and the only one that may already be
wrong in shipped code.

**The probe.** Written in Datalog, two of the three set readings need negation or aggregation over
an evidence path:

| Reading | Statement | Needs closure? |
|---|---|---|
| `SomeValue` | Permitted if **any** value is Permitted | **no.** Positive |
| `EveryValue` | Permitted if **all** values are Permitted | **yes.** Requires that no unseen value exists |
| `SingleValue` | exactly one value, else Undetermined | **yes.** Counting requires a complete set |

So one of three things is true, and it matters which:

1. **L15 already assumes a closed value set** and does not say so. Then the law needs a sentence,
   and evidence bindings need a way to assert closure.
2. **L15 is unsound as stated.** Then `EveryValue` can return Permitted where the truth is
   Undetermined, which is the dangerous direction: it admits what should be referred.
3. **The distinction is immaterial in practice** because evidence paths within one aggregate are
   always complete. Then that needs stating as an assumption, with the aggregate boundary named.

**To verify.**
- Read ADR-A103's text for any closure assumption, explicit or implied.
- Read `eligibility_ir.py`'s handling of `EveryValue` and `SingleValue` to see what the
  implementation actually assumes.
- Construct a fixture where a path has values in two named graphs and only one is in scope, then
  check whether `EveryValue` returns Permitted.

**Closing evidence.** Either a citation showing closure is assumed and documented, or a failing
fixture. **A failing fixture makes this a defect, not research**, and it moves to a slice.

**Cost of being wrong.** Case 2 is a soundness defect in a shipped law, of the kind that produces a
wrong Permitted. Cheap to settle now, expensive to discover in a SPARQL-versus-Datalog parity test,
and worst to discover in an audit.

---

## R4. ODRL as the wire shape rather than a projection

**Class:** design. Attractive, and easy to over-commit to.

**The attraction.** ODRL 2.2 is a W3C recommendation, natively JSON-LD, with `Duty`, `Permission`
and `Prohibition`, constraints as operator-plus-operand over a left operand, and a `consequence`.
Its constraint shape matches the single-subject fragment closely, and its deontic-as-data stance
matches the decision to reify modality. With a well-built context it is close to `@`-free. Adopting
it would mean the Market Profile *is* a standard rather than resembling one.

**What must be verified before going further than projection.**

| Question | Why it decides the matter |
|---|---|
| Can ODRL express a **multi-step** compensation chain? | `odrl:consequence` appears to be one step. A suborder list is *n* steps. If it cannot, an ODRL-shaped wire cannot carry `ins:compensatedBy` |
| Can ODRL express **priority between policies**? | ODRL has conflict strategies (`perm`, `prohibit`, `invalid`) at policy level, not a norm-to-norm override relation. If those are not equivalent, N6 and N7 have no ODRL form |
| Can ODRL constraints express **hierarchical match with exclusion**? | L10 and L11 are the hardest existing semantics. An `odrl:Constraint` with `isAnyOf` may not carry the above-exclusion Undetermined |
| Does ODRL have a **third truth value**? | if not, the whole Undetermined apparatus has no ODRL representation, which is disqualifying for the default form |
| What are the **profile mechanics**? | ODRL profiles extend vocabulary. Whether they can extend *structure* determines whether our additions are conformant or merely adjacent |

**The likely answer, to be tested rather than assumed:** ODRL is the right **projection** of the
`conditions` form and the wrong **shape** for the wire, because the last two rows probably fail. An
ODRL-shaped wire that silently drops chains, priority and Undetermined would be worse than a
non-standard one that carries them.

**Cost of being wrong.** High in the adopting direction. Claiming ODRL compatibility and then
diverging is more damaging than never claiming it.

---

## R5. s(CASP) for justifications and controlled English

**Class:** capability. Bears on R5 of the cross-check (controlled-English rendering) and on the
wire sketch's `because` structure.

**The claim to test.** s(CASP) is goal-directed ASP that produces **natural-language
justifications** for its answers, and is used by Blawx and as a Logical English target. If its
justification output is good enough, it supplies both the rendering capability and the explanation
structure, rather than either being built bespoke.

**What must be verified.**
- Justification quality on a fragment resembling a contract term, not on a textbook example.
- Whether justifications can be **templated per predicate**, so `riskLocation` renders as "the
  risk's location" rather than as a predicate name.
- Whether a `needs` field (what would have to be true) falls out, or only a `because` (what was
  true). The wire sketch's referral design depends on `needs`, which is the harder one.
- Maintenance status and licence.
- Whether it can run design-time only, as a rendering generator, rather than on the decision path.

**The alternative it is competing with.** Proof trees from the dual-predicate translation are
already a `because` structure, and the rule whose missing premise blocked `permitted` is already a
`needs`. So s(CASP) must beat *a thing we get for free from R2*, which is a higher bar than it
first appears.

**Cost of being wrong.** Low. This is additive and can be abandoned.

---

## R6. What the ingress pipeline stores for a payload

**Class:** design. Small, and it has a security consequence.

**The question.** A LegalRuleML statement outside the importable fragment is retained rather than
lifted. Three options for what is retained:

| Option | Egress | Security | Fidelity |
|---|---|---|---|
| **Verbatim XML literal** | `parse-xml()` at egress | parses untrusted text on **every** egress | byte-faithful to what arrived |
| **Lifted JSON AST in the graph** | reconstruct by templates | no parsing at egress | normalised, not byte-faithful |
| **Both** | prefer AST, fall back to literal | parsing only when the AST is absent | both available |

**The security argument favours the AST.** Parsing caller-supplied XML once at ingress, under
controlled conditions, is a bounded exposure. Parsing it again on every egress request multiplies
that exposure and puts it on a read path that may be more widely reachable than the write path.

**The audit argument favours the verbatim literal.** "This is exactly what the counterparty sent"
is a question a dispute will ask, and a normalised reconstruction cannot answer it.

**To verify.**
- Whether byte-faithful retention is a legal or regulatory requirement in the target markets, or
  merely desirable. This is a question for a domain expert, not a technical one.
- Storage cost of both, which is probably negligible and should be confirmed rather than assumed.
- Whether a hash of the verbatim form plus the AST satisfies the audit need without retaining the
  bytes, which would be the cheapest answer if it does.

**Cost of being wrong.** Moderate. Storing only the AST and later needing the bytes is
unrecoverable for documents already ingested.

---

## R7. Answer set programming for competing interpretations

**Class:** capability, and firmly deferred.

**The fit.** G5 (competing interpretations, `lrml:Alternatives`) is the one requirement Datalog
structurally cannot meet, because Datalog has one model and alternatives are several. ASP's
**several answer sets are several interpretations**, which is a genuine structural match rather
than an analogy.

**Why it is not adopted.** G5 is deferred in the mapping sketch, A-110 is unscheduled, and the
mechanism is a generalisation of `voc:BindingScope` that should be designed when a second use case
appears. Adopting an ASP engine before the requirement is scheduled would be the clearest possible
case of a solution preceding a problem.

**What to record now**, so the option stays open:
- That the interpretation parameter, if built, is an **answer-set selector**, which keeps the
  Datalog tier stratified and puts the non-determinism in one declared place.
- That a design-time use exists independently: "is this contract self-consistent under **all**
  readings" is an ASP question and a stronger check than the pairwise contradiction check of
  mapping §19.3.

**Trigger to reopen.** G5 is scheduled, or a second context-selection requirement appears beside
`voc:BindingScope`.

---

## R8. SHACL 1.2 rules

**Class:** watch. No action, periodic re-check.

**Why it matters.** The note reports that the W3C Data Shapes WG is working on rules for SHACL 1.2,
reportedly Datalog-like with stratified negation. If that lands in that shape, it is a **standard
home for internal rule graphs** over RDF, which is exactly the tier this work needs, and it would
be better than anything bespoke.

**What must be verified, and re-verified.**
- Current status and expected shape. Working drafts change.
- Whether negation is stratified and whether the semantics is a minimal model or something else.
- Whether it composes with SHACL-AF, which the repo already uses.
- Whether it carries a third truth value, or whether Undetermined would again need the dual encoding
  on top.

**The trap.** Betting on an unfinished standard. SHACL-AF rules have been available for years and
the repo uses them narrowly. A 1.2 rules layer that does not land, or lands differently, would strand
anything built against a draft.

**Recommended posture.** Re-check at each ADR that touches the rules tier. Do not design against it.

---

## R9. Defeasible logic translations, and what N7 actually means

**Class:** soundness. The most conceptually delicate item.

**The concern.** §9.4 Option B adopts explicit, acyclic priority. The note shows the
explicit-superiority encoding is stratified. But **full defeasible logic is a family**, and the
translations of Antoniou, Billington, Governatori and Maher into logic programs are not uniformly
stratified. The variants differ on:

- **Team defeat**, whether several weaker rules can jointly defeat a stronger one.
- **Ambiguity propagation versus blocking**, whether an unresolved conflict poisons downstream
  conclusions or is merely withheld locally.
- **Defeaters**, which block a conclusion without supporting the opposite.

These are not academic distinctions. They produce different answers on real contract structures,
and LegalRuleML carries `lrml:Defeater` as a first-class strength, so an importer must decide what
it means.

**The specific question to settle.** What does N7 intend?

> N7: Two specifications with opposing modality over the same content, with no path between them in
> the override closure, yield Undetermined with `exe:IncomparablePriority`.

That is **ambiguity blocking**, locally. Whether the resulting Undetermined then propagates through
a compensation chain or a nested profile is unstated, and the two readings differ observably.

**To verify.**
- Which defeasible variant the stratified encoding actually implements.
- Whether that variant is the one N7 intends, or merely the one that was easy to encode.
- What `lrml:Defeater` maps to, given LATTICE has no rule that supports a conclusion without
  asserting it.
- Whether ambiguity propagates in LATTICE, by constructing a case and checking the existing
  aggregation laws.

**Cost of being wrong.** High and subtle. Claiming a defeasible semantics while implementing a
different one is the kind of defect that survives every test written by the person who wrote the
implementation, and surfaces in a dispute.

---

## R10. Engine selection, if and when

**Class:** deferred, with triggers already set by the cross-check.

Recorded only so the candidates are not re-derived. **No evaluation until a trigger fires.**

| Candidate | Shape | What to check when the time comes |
|---|---|---|
| **Soufflé** | C++, stratified negation, aggregates, provenance | maintenance status. Provenance output format, since it feeds `because` |
| **Nemo** | Rust, RDF in and out, existential rules | maturity. RDF-native input would remove a conversion hop |
| **RDFox** | commercial, incremental, OWL 2 RL plus NAF | licence and cost. Incremental maintenance is its distinguishing feature |
| **clingo / DLV** | ASP | only relevant under R7 |
| **In-process, via iterated `CONSTRUCT`** | no new dependency | **the default.** Each stratum is a CONSTRUCT run in order |

**The default deserves emphasis**, because it is easy to skip past. A stratified program without
recursion is a sequence of `CONSTRUCT` queries run in stratum order, which the existing SPARQL
backend plus a scheduler already provides. Recursion is bounded: scheme closure is a property path,
and compensation chains are acyclic by N3. **No engine is needed to start**, and that removes the
main argument for evaluating one now.

---

## R11. Prior art on three-valued expressions

**Class:** survey. Cheap, and useful for avoiding known mistakes.

Four systems have solved an adjacent problem, and each carries a lesson.

| System | Lesson | To verify |
|---|---|---|
| **DMN / FEEL** | FEEL booleans are three-valued with `null`: `false and null = false`, `true and null = null`. That is strong Kleene, in a mainstream business-rules standard. Hit policies are a fixed priority vocabulary worth borrowing names from | the exact `and`/`or` tables in the DMN version cited. **And the mistake to avoid:** FEEL expressions live in XML string attributes, recreating the problem §8.0 just fixed |
| **Cedar** (AWS) | an official JSON policy format for a formally analysed logic, which is the exact pattern being proposed. Forbid-overrides is a fixed priority | **the error semantics.** Reportedly a policy that errors is *skipped*, which is a silent-absence hazard of precisely the kind Undetermined exists to prevent. Confirm, because if true it is a worked example of the failure mode |
| **CEL** | partial evaluation with **unknowns**, where `&&` and `\|\|` absorb unknowns and errors. Mainstream, and close to Kleene | whether unknown-absorption matches strong Kleene exactly or only approximately. Implementations reportedly vary |
| **Rego / OPA** | proof that Datalog-over-JSON is industrially acceptable | the `default` keyword, which supplies a value on absence. That is the opposite of the closure discipline, and is the specific thing not to copy |

**Why this is worth an hour.** Three of the four have a documented failure mode that this design is
currently avoiding by reasoning rather than by evidence. Confirming them turns "we think silent
absence is dangerous" into "here are three systems where it bit".

---

## R12. Symboleo and obligation lifecycle

**Class:** design input for A-106, not a wire format.

**The fit.** Symboleo is a contract specification language with obligations and powers carrying
lifecycle states over an event calculus. The obligation state model — created, in effect,
discharged, violated, suspended — is exactly what R1 places in Behaviour as a derived state space,
and it has been studied rather than invented.

**What to extract.**
- The state set and the transitions between them, against the proposed
  pending / active / fulfilled / violated / discharged.
- How suspension is handled, which the proposal currently does not address and which real contracts
  need.
- How powers are modelled, which bears on where `stm:Power` lands (mapping Q11).
- Whether the event calculus framing conflicts with positioned stimuli, or is a presentation of the
  same thing.

**What not to extract.** Its syntax, and its runtime. This is a source of design pressure on A-106's
state model, nothing more.

**Cost of not doing it.** Moderate. Inventing a lifecycle that a studied language already got right,
and discovering the missing state later.

---

## Priority, if any of this is picked up

Ordered by expected value rather than by number.

| Order | Item | Why first |
|---|---|---|
| 1 | **R3** set readings | may be a live soundness defect. Hours to settle |
| 2 | **R1** JSON RuleML | blocks a wire decision. Hours to settle |
| 3 | **R9** defeasible variant | must be settled before A-107 is drafted, not after |
| 4 | **R11** prior art | an hour, and it de-risks three design choices |
| 5 | **R6** payload storage | blocks the ingress slice, and has a security consequence |
| 6 | **R2** Datalog role | a decision, and the answer is probably B |
| 7 | **R4** ODRL | only if a consumer asks for ODRL |
| 8 | **R12** Symboleo | before A-106's state model is fixed |
| 9 | R5, R7, R8, R10 | deferred with triggers already stated |

Items 1 to 4 are collectively under a day and settle three questions that would otherwise be decided
by assumption. Nothing below item 6 should be started before the normative-rule-substrate plan's
decision D2 is taken, since most of it is downstream of whether the deontic extension happens at
all.
