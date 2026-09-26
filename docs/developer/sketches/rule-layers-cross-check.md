# Rule Layers Research: Cross-Check Against LATTICE

**Date:** 2026-09-26
**Status:** working note in `.local/`, not a decision and not a plan
**Input:** `docs/developer/sketches/rule-layers.md` (Logical English, stratified Datalog, deontic reasoning, a normative evaluation tier)
**Checked against:** `docs/architecture/` (ADRs, ingestion vision, patterns guide, solution design, conformance ladder) and `docs/developer/` (epic v0.2, phase plans, applied-insurance epic, sketches)

---

## 1. Verdict

The research is sound, and LATTICE has already taken most of its recommended decisions. Several are stated more precisely here than in the research. Four things are missing from the roadmap, and three of them are small. One is a genuine gap in the substrate: **obligations in LATTICE have parties but no normative semantics** (modality, deadline, fulfilment, violation, reparation). No new engine, store or language is needed now.

Recommended additions, detailed in §4:

| # | Addition | Size | Lands in |
|---|---|---|---|
| R1 | Normative semantics for `ins:Obligation` (a deontic extension of Instrument) | ADR plus a MINOR Instrument bump | before applied-insurance Phase 5 (A-101) |
| R2 | Closure declarations: when absence of evidence may decide an outcome | ADR across Eligibility, Behaviour and persistence | before the Phase 3 expansion of the Behaviour engine (P3.2) |
| R3 | Scheduled triggers as positioned stimuli, so deadlines replay | one slice in P3.2 | Phase 3 expansion |
| R4 | Acyclicity of condition composition | one shape and one test | `eligibility-compiler`, now |
| R5 | Controlled-English rendering of compiled rules for reviewers | sketch | ingestion vision Phase 2, review workbench |

Everything else in the research is either covered (§3) or worth recording as a deferred option with a trigger (§5).

## 2. Where the research's premises differ from LATTICE

The research was written for open-dare's stack. Its recommendations mostly survive the translation, but the premises below change their weight.

| Research assumes | LATTICE has | Effect |
|---|---|---|
| Rules use negation as failure, so absence means false | Three-valued outcomes under strong Kleene logic. Missing evidence is `Undetermined` with a diagnostic (`exe:MissingCandidate`), never `Denied` (ADR-A24, A89, A103) | The "NAF licence" question becomes sharper: absence currently can never decide anything. See R2 |
| OWL 2 DL reasoning runs at runtime | DL reasoning is design-time and test-only (ADR-A83, A90). Runtime guards use rule-based materialisation with logged firings (epic P2.2.3) | The DL/rule layering the research asks for is already in place (§3, row F) |
| Erlang runs quote and negotiation FSMs | Erlang hosts SPC, a session-type calculus, unintegrated (deferred-scope §3, epic P4.5). The Behaviour engine (C-09) is Java | The "FSM is a projection, the evaluator is authoritative" rule applies to SPC integration, not to a quote tier |
| F# or Rust hosts a parser or evaluator | Java, Python, TypeScript and Erlang. Rust appears only in a deferred sketch (`identity-minting-shared-core`) | No language addition is justified by this research |
| A rule IR still has to be designed | A shared executable IR exists (`tools/mork_compilers/eligibility_ir.py`), feeding SPARQL, SHACL, SWRL and design-time OWL | "One IR, many lowerings" is ADR-A19 and A23, built |
| Jena is the system of record | A store SPI with a TCK (ADR-A75), TDB2/Fuseki first | Any Datalog backend enters as an SPI or backend adapter, admitted by TCK |

## 3. Recommendation-by-recommendation

| | Research recommendation | LATTICE today | Verdict |
|---|---|---|---|
| A | Logical English as a controlled-language route from text to rules | Ingestion vision §3 names Logical English and InsurLE as the controlled-language route beside machine extraction. Q6 leaves open whether it needs its own translator | **Covered as vision.** The research's option A (LE as the LLM's output format) differs from the vision, which uses MCN intent nodes as the wire format (§7). Keep MCN. LE's value here is reviewer readability, which R5 captures without changing the wire format |
| B, C | Run the LE compiler in a container, or reimplement its grammar | Not planned (Q6 open) | **Defer** until a source drafted in a controlled language exists (§5) |
| — | Routing policy: SWRL for positive DL-safe rules, SPARQL or SHACL for the rest, refuse what cannot be expressed | ADR-A24: SWRL only for positive monotonic outcomes, never `Undetermined`, never absence. ADR-A89, A100, A103 apply it per backend. Unsupported semantics yield `Undetermined` with a diagnostic, never a silent denial | **Covered**, and stricter than the research |
| — | Reify n-ary relations | `pty:RoleOccupancy`, `ins:Obligation` with `ins:obligor`/`ins:obligee`, evidence bindings (ADR-A91) | **Covered** |
| E | Formalise stratification: dependency graph, strata, reject cycles through negation | Eligibility composes conditions as a tree (a profile is a condition, ADR-A03) with negation (ADR-A103), evaluated bottom-up. Nothing checks that composition is acyclic. Behaviour orders evaluation by stimulus position per aggregate (P3.2.2, P3.2.9), which sidesteps logical strata | **Small gap: R4** |
| F | DL results flow up into rules, rule results never flow back into DL | Reasoner test-only (A83), OWL classes design-time only (A90), every materialised triple carries its authority (P2.2.4), inference never silently becomes an authored assertion (A13) | **Covered.** One sentence in `solution-design-specification.md` would state the rule explicitly: no DL reasoner reads rule-derived graphs |
| G | Deontic concepts: obligation, permission, prohibition, power, deadlines, violation, reparation | `ins:Obligation` has direction (obligor, obligee), `ins:fulfilledBy`, `ins:hasCondition`. Behaviour supplies lifecycle machinery. No modality, deadline anchor, fulfilment test, violation state or reparation link. ADR-A07b chose a minimal shape deliberately | **Gap: R1** |
| H | NAF licence: absence decides only where the source is declared authoritative and dense | Conformance level L5 requires "closure assumptions" (ADR-A14) but no vocabulary defines one. The patterns guide provides the mechanism (dense per-stream sequences, the gap scan, receipts) but nothing connects it to Eligibility or Behaviour | **Gap: R2.** A central idea of the research, and a bridge between two parts of LATTICE that do not yet meet |
| I | Deadlines anchored to valid time, time as an input, never the wall clock | ADR-A67 (bi-temporal, `decisionTime` on stimuli), ADR-A94 (business days as calendar units), P3.2.3 (`now()` banned in guards and effects), the `NOW()` rules in the patterns guide Chapter 28 | **Covered for evaluation.** How a scheduled deadline becomes a replayable input is not specified: **R3** |
| J | Defeasibility and priority: exception, exception to the exception, *lex specialis* | Transition priority (ADR-A09), exclusion precedence (L10, ADR-A87), term relations with "override" and an acyclicity shape (term-parameters sketch §4.3) | **Partial.** Enough for current scope. Contract wording ("subject to…, except where…") will need rule priority in Eligibility. Fold the question into R1 and A-101 rather than a separate unit |
| K | Evaluation is a pure function, with deterministic identity, supersession and provenance on decision records | Decision/Explain API with `indeterminate` first-class (P2.4.4), decision records with a re-derivation test (P2.4.10), idempotency by position (P3.2.8), deterministic replay including backdated claims (P3.2.11), supersession never mutation (A67, R-B7) | **Covered**, in more detail than the research |
| L | The FSM schedules and runs side effects, the evaluator decides | C-09 is authoritative. SPC integration (P4.5) lifts documented state machines into session types | **Covered.** Carry the research's F4 warning into P4.5: an SPC session projects Behaviour state, never holds a second copy |
| M | A rule-backend conformance suite, the counterpart of the store TCK | Parity gate (ADR-A28), shared corpus (ADR-A15), per-rule-family SHACL and SPARQL parity (derivation-and-validation.md) | **Covered** |
| N | "Why not" explanations | Witness and challenge sets (P2.4.4), not-fired reasons as durable records (P3.2.5), diagnostics on every `Undetermined` (A89) | **Covered** |
| O | Admission constraints at ingress | Admission gate with severity policy (P2.3.5) | **Covered** |
| P | Invalidate derived decisions when a contract revision changes | Read-set-scoped invalidation (ADR-A27), `INVALIDATION_PLAN` family | **Covered** |
| Q | Compile to plans, not per-contract source code | Artefacts keyed by semantic hash and generation profile, never per-instance code (SDS compilation boundary) | **Covered** |
| D | Verbalise compiled rules into controlled English | Ingestion vision §10.1 wants stewards to see evidence, not notation. Nothing renders a rule as text | **Addition: R5** |
| — | LE scenarios as differential tests (option E) | — | **Defer** with the LE route |
| — | A Datalog sidecar (Nemo, RDFox) or an own engine | Ingestion vision §11 already lists "graph stores with SPARQL, Datalog and explanation support" as a candidate backend under the ADR-A83 isolation rule | **Defer** with triggers (§5) |

## 4. Proposed additions

### R1. Normative semantics for obligations

**What.** Extend Instrument so an obligation says what it requires and when, and so its state can be derived:

- **Modality:** obligation, permission, prohibition and power, as a small closed-by-default vocabulary. Power is the one that changes normative state (cancellation for non-payment), so it relates to Behaviour effects rather than to Eligibility outcomes. Decide whether strong permission (explicitly granted) and weak permission (nothing forbids it) both need representing. Weak permission is an absence question, so it depends on R2.
- **Trigger and deadline:** an anchor event (valid time, ADR-A67) plus a duration as a `qnt:Quantity`, including calendar units (ADR-A94).
- **Fulfilment:** an `elg:Condition` over the events that count as performance.
- **Reparation:** a link from an obligation to the obligation that becomes active when it is violated (contrary-to-duty).
- **State:** pending, active, fulfilled, violated, discharged, as a Behaviour state space whose occupancies are derived artefacts (ADR-A92), never asserted. The same pattern as liability direction in ADR-A102: derived, with a read set, and a shape that reports a state without a derivation.

**Why now.** Every LATTICE domain is regulative, not only insurance: lending covenants, trial protocols, employment terms. ADR-A07b kept Instrument minimal on purpose, and the minimal shape is now the limiting factor. Applied-insurance Phase 5 (contract module, A-101) and Phase 6 (claims) will need notification duties, cure periods and cooperation duties. If Instrument does not provide them, the insurance module will invent them locally, which ADR-A-C1's applied-layer boundary exists to prevent.

**Checklists, not dependencies.** Use LegalRuleML (deontic operators, reparation chains, defeasibility, time dimensions, source provenance) and ODRL (Duty, Permission, Prohibition in RDF) to check coverage. Adopt neither syntax. Align with ODRL terms where the meaning is equal, so policies expressed in ODRL can be mapped through MORK.

**First artefact.** A sketch with two non-domain examples first (ADR-A-C2): a lending covenant's reporting duty with a cure period, and a trial's adverse-event reporting duty. Then an ADR, then Instrument 0.x MINOR. It precedes A-101, which currently expects to draft term parameters on `ins:Qualifier` without a normative model of the obligation they qualify.

### R2. Closure declarations

**What.** A declaration that a fact family is authoritative and complete for a scope up to a position, so that absence may decide an outcome. For example: "claim notifications for this policy arrive only through this stream, and the stream is complete through position (e, s)". Without one, absence stays `Undetermined`, as today. With one, a compiled check may return `Denied`, or a violation, and its record cites the declaration and the position it relied on.

**Why.** R1 without R2 cannot detect a single violation. "No notification by the deadline" is always `Undetermined` under current semantics, which is correct but useless for regulative rules. Conformance level L5 already requires closure assumptions and does not define them. The patterns guide already provides the proof obligation: dense per-stream ordering and the gap scan are the only way to show nothing was missed, and a sparse clock can never show it (guide §3.3 and the gap scan). This ADR connects the persistence profile to the rule semantics.

**Shape of the rule.**
- A closure declaration names a fact family, an authoritative source (a stream or graph family), a scope and a required persistence profile (dense per-stream ordering, gap audit blocking).
- The compiler refuses a check that decides on absence unless a closure covers the fact family. The refusal is a diagnostic, not a silent `Undetermined`.
- At evaluation, the check reads the closure's position. Absence beyond that position is still `Undetermined`.
- A decision that relied on absence records the closure and position, so a late fact at an earlier valid time supersedes it (P2.4.10, A67).

**Where it lands.** An ADR across Eligibility (a new outcome path and diagnostic), Behaviour (guards and violations) and `ontology/persistence` (the declaration's required profile, compiled by `tools/persistence`). Sequence it before the Phase 3 expansion at P2.11.4, because P3.2 guard evaluation will otherwise be specified without it.

**A useful failure mode.** As the research notes, if closure declarations keep being refused because streams are not authoritative for the facts contracts care about, that finding is about provenance at ingestion, and it belongs to the ingestion vision (S6 entity resolution and the admission gate).

### R3. Scheduled triggers as positioned stimuli

**What.** Specify that `bhv:ScheduledTrigger` and `bhv:DeferredActivation` fire through stimuli written to the stimulus log by a scheduler, carrying the valid time they represent. The engine never reads a clock (P3.2.3 already requires this). A deadline passing is then an input at a position, so deterministic replay (P3.2.11) covers deadlines, and a backdated fact that arrives after a deadline stimulus is ordered by the same rules as any other.

**Why.** P3.2 bans `now()` but does not say where time-driven transitions come from. Without this, the first obligation deadline will reintroduce the wall clock into the engine or a side channel outside the log.

**Where.** One slice in the P3.2 expansion. The scheduler also covers ADR-A10's deferred activations and allowance resets (`bhv:resetRecurrence`), which have the same problem.

### R4. Acyclicity of condition composition

**What.** A SHACL shape and a compiler refusal for a cycle through `elg:hasCondition` across profiles. With negation (ADR-A103) a cycle has no well-founded outcome. Record the evaluation-order rule in the Eligibility README: a condition is evaluated after every condition it composes. That is the stratification the research asks for, and today it holds only because no fixture builds a cycle.

**Where.** `eligibility-compiler`, as a small slice. Hierarchical match already has an analogous acyclicity rule for scheme ordering (`rules.ttl`, elg:L9), so the shape follows an existing pattern.

### R5. Controlled-English rendering of compiled rules

**What.** Render an Eligibility plan, and later an R1 obligation, as template-filled English in the Logical English style: "a facility is admitted if its amount is between EUR 1m and EUR 25m and its borrower is incorporated in the EU but not in Cyprus". Generated from the IR, deterministic, and marked as a rendering, never a source.

**Why.** The review workbench's stewards should see meaning, not notation (ingestion vision §10.1), and the Explain API (P2.4.4) needs text for its witnesses. It also makes the controlled-language input route (ingestion vision Q6) cheaper later: once LATTICE can render rules in LE's style, a translator in the other direction has a round-trip test.

**Where.** A sketch attached to ingestion vision Phase 2, consumed by the review workbench and the Explain API.

## 5. Deferred options, with triggers

| Option | Why not now | Trigger to reopen |
|---|---|---|
| Logical English input route (research options B and C), LE scenarios as differential tests | No source text is drafted in a controlled language yet. Ingestion vision Q6 already holds the question | A drafter or partner supplies LE or InsurLE text, or R5 produces renderings worth round-tripping |
| Datalog sidecar (Nemo, RDFox) behind the backend interface | Rule-based materialisation over SPARQL has not been measured against the guard budget (P2.2.2) | P3.6 baseline shows guard or materialisation budgets missed, or incremental maintenance is needed for a book of obligations |
| An own evaluation engine (the research's Tier 2) | Multi-person-year effort. Phase 3 has not measured the need | Continuous normative monitoring at scale with Tier 1 exhausted. Revisit alongside `identity-minting-shared-core`, since both argue for a Rust core |
| Well-founded or stable-model semantics for mutual exceptions | A cycle through negation in contract rules is a drafting ambiguity or an extraction error. R4 routes it to a person | Real contracts show recurring mutual exceptions that people resolve the same way each time |
| Prolog or Erlog in any runtime | Contradicts the deterministic compilation boundary and adds a second logic semantics | none |
| SWRL for anything involving absence or `Undetermined` | ADR-A24 excludes it | none |

## 6. Sequencing against the current roadmap

| When | Addition | Blocking |
|---|---|---|
| Now | R4 | nothing |
| Now, as a sketch | R1 sketch with non-domain examples | nothing. The ADR must land before A-101 |
| Before P2.11.4 (Phase 3 expansion) | R2 ADR, R3 slice written into the P3.2 expansion | P3.2 specification |
| Ingestion vision Phase 2 | R5 | review workbench design |
| Applied-insurance Phase 5 start | R1 accepted and Instrument bumped | A-101, the contract module, and claims in Phase 6 |
| P3.6 measurement | decide on a Datalog sidecar | measured guard and materialisation budgets |
| P4.5 | carry the F4 rule into SPC integration: SPC sessions project Behaviour state | SPC integration |

## 7. Questions for you

1. **R1's home.** Instrument (substrate) or a new layer? My reading is Instrument, because obligations are already there and the four target domains are all regulative. A new layer would only be justified if normative state needed its own dependency position.
2. **ODRL alignment.** Align R1's terms with ODRL where meanings match, or keep LATTICE's vocabulary independent and bridge through MORK only?
3. **R2's default.** Should a check that could decide on absence, but has no closure, be refused at compile time (my recommendation) or compiled to always return `Undetermined` with a diagnostic?
4. **Priority for Phase 5.** Applied-insurance D2 defers Phase 5 until Open CBAA integration. Does R1 wait with it, or proceed as substrate work now so that Phase 5 starts with it in place?

## Appendix: sources consulted

Architecture: `ingestion-vision.md` (§3, §5, §8, §11, §13–§15), `conformance-levels.md`, `derivation-and-validation.md`, `deferred-scope-and-boundaries.md`, `semantic-platform.md`, `implementation-map.md`, `ontology-architecture.md`, `rdf-sparql-patterns-guide.md` (Parts III, V, Chapter 28), `data-architecture.md` (graph families), `solution-design-specification.md` (compilation boundary, components), `ontology/spc/docs/architecture.md` (the Erlang, Prolog and Logical English note).

ADRs: A03, A07b, A08, A09, A10, A11, A13, A14, A15, A19, A23, A24, A25, A27, A28, A67, A75, A83, A87, A89, A90, A91, A92, A94, A96, A100, A102, A103, A-C1, A-C2.

Ontology: `instrument/spec/instrument.ttl`, `behaviour/spec/behaviour.ttl` and its vocabulary, `party/spec/party.ttl`, `mork/spec/Executable.ttl` (diagnostics), `eligibility/shapes/rules.ttl`.

Plans: `lattice-platform-agentic-development-v0.2.md` (P2.2, P2.3, P2.4, P3.2, P4), `applied-insurance-reference.md` and its Phase 5 plan, `sketches/term-parameters.md`, `docs/developer/INDEX.md`.
