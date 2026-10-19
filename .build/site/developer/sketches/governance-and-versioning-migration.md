# Designing the Human Surface for MORK

## A thesis on reviewable semantic alignment

---

## Part 1. The central inversion

Every instinct in this problem space pulls toward building an editor for MORK graphs. Resist it completely.

The person at the keyboard is a domain expert. They know that a Layer has an attachment, a limit and a share; that Layer and Policy are disjoint; that `hasPerilScope` must range over `Peril`. They know this because they or their colleagues wrote the ontology. What they do not know — and should never need to learn — is the difference between `broaderApplicative` and `compositeBroaderMapping`, or why `intransitiveExactMatch` sits under `skos:closeMatch`.

The paper concedes the problem in its own Limitations: *"MORK is a rich vocabulary with a substantial learning curve. The property hierarchy alone requires careful study to use correctly."* And yet Stage 5 asks a human to approve MORK graphs. That is a category error. The teaching essay resolves the analogous problem for the LLM by compiling doctrine into a kernel. The human requires the opposite treatment: not compression of MORK, but **its complete disappearance**.

> **Thesis.** MORK is substrate, not interface. The human is never shown a mapping; they are shown a *claim about their domain*, expressed in their own vocabulary, with the evidence that produced it. Their judgement is captured in domain terms and projected back into MORK by the system. Every surface in the application is a projection of the mapping graph into the reviewer's language, and every interaction is a projection of the reviewer's judgement into the graph.

This is not a simplification layer bolted on top. It is the same duality the paper is built on. The source side carries implicit intent — *what it looks like and what company it keeps*. The target side carries explicit intent — *what it requires and excludes*. The human sits precisely in that gap, and the interface's job is to render both sides in their native idiom and let the human adjudicate. The MORK graph is the *record* of that adjudication, not its medium.

Two corollaries follow immediately, and both are load-bearing for everything after.

**MORK is always one keystroke away and never the default.** Integration engineers will want to see the graph, and they should — as MCN, not Turtle, because MCN is line-oriented and therefore diffable. But a `View source` affordance is not a UI; it is an escape hatch for a minority role.

**The human sees only graphs that are already machine-clean.** Lint failures, GCI violations and Meta-SHACL violations are the LLM's problem, resolved in the millisecond repair loop. A domain steward who is shown `ap without xr` learns two wrong things: that the machinery is unreliable, and that their job includes debugging it. By the time a claim reaches a human, it is well-formed, consistent, and grounded. Whether it is *true* is exactly the question the human is there to answer — and per Remark 4.2, the only question the machine cannot answer.

---

## Part 2. Who is at the keyboard

There is no generic user. Four roles with genuinely different competencies, incentives and access perimeters:

| Role | Knows | Never sees | Primary surface |
|---|---|---|---|
| **Domain Steward** | the ontology, the business | MORK vocabulary, teaching pack, lint output | Bench, Queue |
| **Integration Engineer** | source systems, schema structure | teaching pack internals | Bench, Atlas, Boundary, MCN source |
| **Ontology Owner** | ontology governance, disjointness, versioning | teaching pack | Minting review, Coverage |
| **Pack Maintainer** | MORK, MCN, the LLM stack | individual mapping decisions | Studio |

The paper already constrains agents by named-graph perimeter. The same discipline must apply to humans, and for the same reason: **Proposition 6.1's layer independence is only real if the people are separated too.** A domain steward who has read the box-match documentation will start reasoning about T-Box versus A-Box, and will begin approving on structural grounds they are not qualified to judge. An intent reviewer shown ontology IRIs will conflate Layer 1 with Layer 2 and the ontology-independence property of `IntentNode` quietly dies.

Perimeters are therefore enforced in the UI, not merely documented:

| Role | Can see | Can decide |
|---|---|---|
| Domain Steward | source fragment, ontology fragment, evidence, alternatives | confirm / retarget / decline / teach / defer |
| Integration Engineer | + full schema, sections, boundaries, MCN, templates | + reshape, section typing, template approval |
| Ontology Owner | + axiom profiles, coverage gaps, minting proposals | + accept/reject ontology change |
| Pack Maintainer | aggregated failure signatures, calibration, evals | pack release, errata, lens, cassette |

Note what the Pack Maintainer *cannot* see: individual mapping content. They receive typed, abstracted failure signatures and representative examples. This is the seam, and Part 10 develops it.

---

## Part 3. The unit of judgement

What does a human approve at a time? This single decision determines whether the product is usable, and it should be derived rather than guessed.

Per-node review is fatal — the paper notes a moderate JSON schema yields around 8,000 lines of MORK concept nodes. Whole-schema review is cognitively impossible. The answer is already in the theory, in four independent places:

- `q_struct` in Definition 2.1 groups by **structural section**
- community detection operates on **section signatures**
- the sheaf construction takes **sections as cells**, with obstructions on their *overlaps*
- a section corresponds to exactly one coherent domain entity — a Layer, a Party, a Clause

> **The section is the unit of judgement, and section boundaries are a separate unit of judgement.**

This is not a compromise; it is the grain at which the domain expert's knowledge is actually organised. "Is this a Layer?" is a question a reinsurance specialist answers in under a second. "Should `xs_point` map to `hasAttachment`?" is a question they answer by first reconstructing the section context in their head — work the interface should have done for them.

Four units, in descending frequency of use:

| Unit | Question asked | Who | Frequency |
|---|---|---|---|
| **Section** | "Is this a Layer, and does this mapping express a Layer correctly?" | Steward | dominant |
| **Template** | "Is this pattern right?" — approved once, applied *n* times | Engineer | rare, enormous leverage |
| **Boundary** | "These two sections disagree about a shared individual" | Engineer | occasional, high stakes |
| **Field** | "This one field resists the section consensus" | Steward | exception only |

The field is an *escalation*, never an entry point. If the queue presents fields by default it has already lost the community acceleration factor that Part 6 is built on.

---

## Part 4. Rendering what the LLM found

This is where most of the design value sits, and where the paper is unexpectedly generous. Five distinct evidence structures are available, and each deserves its own representation rather than being collapsed into a percentage.

### 4.1 The token ribbon

The paper's best worked example is the attribute `cyperTPLBIPCIDSSLmtAmt`, which the LLM decomposes into six recognisable tokens with six different kinds of evidence. A field name is a compressed sentence; the model decompressed it; **the decompression is the finding**, and hiding it behind a single score discards the richest thing the system knows.

```
 cyper      TPL        BI       PCIDSS      Lmt       Amt
 ▔▔▔▔▔      ▔▔▔        ▔▔       ▔▔▔▔▔▔      ▔▔▔       ▔▔▔
 label      acronym    acronym  no match    label     label
 LineOfCover  Liability   Peril    ?hypothesis  Limit     Amount
 :Cyber       :ThirdParty :BusInt  ⊂ RegPeril
 ●●●        ●●●        ●●●      ●○○         ●●○       ●●○
                                 ↑
                          needs your input
```

Each segment is hoverable (concept, scheme, match type, the exact label or `skos:acronym` that matched) and each *unmatched* segment is directly actionable. The hypothesis on `PCIDSS` — the model's guess that it denotes a regulatory peril and should be a subclass of one — is visually distinguished as a hypothesis, not rendered as a finding. This is the single highest-value display element in the product, because it converts an opaque score into a chain of small claims the expert can audit in seconds. It generalises directly to documents (Part 4.6) as a span ribbon over text.

### 4.2 Four distances as four reasons, never one number

The paper's `d_lex`, `d_struct`, `d_comm`, `d_type` are qualitatively different signals and Stubbe's quantaloid framing exists precisely to *stop* premature aggregation. The UI must honour that. Rendered as reasons rather than arithmetic:

| Signal | Rendered as | Example |
|---|---|---|
| lexical | the matched string, and how | `"xs_point" ≈ "Attachment Point"` (abbreviation + embedding 0.78) |
| structural | the company it keeps | "in section with `lmt`, `ccy`, `pct_share`" |
| community | prior experience | "Layer signature — seen in 7 of 9 prior schemas" |
| type | compatibility verdict | `decimal → MonetaryAmount` ✓ |

Aggregate the four into a headline score if you must, but the score is never the primary display and is never shown without its decomposition adjacent.

### 4.3 Witnesses and challenges — the centre panel

The Dialectica interpretation is the finest UX primitive in the paper and appears to have been written without realising it. Challenges come from the target's axiom profile; witnesses come from the source evidence; a mapping is feasible when every challenge has a surviving witness. That is a checklist. Domain experts read checklists fluently.

```
ctr:Layer requires                        satisfied by
─────────────────────────────────────────────────────────────────────
✓ hasAttachment → MonetaryAmount          xs_point      lex .78 com .91
✓ hasLimit      → MonetaryAmount          lmt           lex .84 com .93
✓ hasShare      → xsd:decimal             pct_share     lex .71 com .88
✗ hasPerilScope → Peril                   nothing in this section
⊘ not Policy                              no conflict

unused in this section
─────────────────────────────────────────────────────────────────────
  layer_no   no candidate above threshold          → suggest a concept
  eff_dt     claimed by parent section (Contract)  → review boundary
```

Three glyphs carry the whole semantics: `✓` challenge met, `✗` challenge unmet, `⊘` exclusion confirmed clear. The `✗` on `hasPerilScope` is the *ontology's* voice — it is telling the reviewer what the source failed to supply, which is information the reviewer could not otherwise easily obtain. The `unused` block is the mirror image: source information the mapping discards.

### 4.4 The two-sided coverage meter

Those two blocks are the Galois diagnostic of Remark 2.26a made visible, and it is worth naming because it answers a question users always ask and existing tools answer badly:

- `γ(f(C)) ⊃ C` — **under-specification**: the target class demands properties nothing projects to. *Your ontology wants more than this source provides.*
- `γ(f(C)) ⊂ C` — **over-specification**: concepts in the community that contribute nothing. *This source carries information your ontology cannot express.*

```
ctr:Layer requirements satisfied   ███████▁  3 of 4
source section fields consumed     ██████▁▁  5 of 7
```

Two numbers, two different questions, both essential. A single "percent mapped" progress bar conflates them and, worse, incentivises coverage over correctness — a reviewer optimising a progress bar will force marginal mappings to make the bar move. Never ship one.

### 4.5 Absence of evidence is not evidence of absence

The three timescales — axiom intent at *t*=0, community at *t*=3–5, projection at *t*=5–10 — mean that early in a deployment most evidence channels are simply *empty*. The reviewer must be able to distinguish two radically different situations:

```
community    — no prior observations of this signature    (unavailable)
projection   — 4 prior mappings, 3 to hasAttachment, 1 to hasExcess  (contested)
```

The first says "trust the lexical and axiom evidence, we have no history." The second says "we have history and it disagrees with itself." Collapsing both to "low confidence" destroys the reviewer's ability to calibrate their own attention, and it is the most common failure of confidence displays generally. Render empty channels explicitly as empty.

### 4.6 Documents, and the third confidence channel

For contracts and submissions the left column becomes a document viewer with highlighted spans, `hasNaturalLanguageSource` carrying the exact fragment and provenance running back to page and bounding box. The token ribbon generalises to a span ribbon.

But note a genuine addition: **extraction confidence is a third channel**, distinct from both domain confidence (`weighting`) and notation confidence. "I am 60% sure the document says $25M" and "I am 60% sure $25M means `sh:maxInclusive` on this path" are different claims requiring different remedies — better OCR versus better mapping. Conflating them is the same error as R1 at one remove, and the UI must keep them visually and semantically separate.

Documents also require **two Benches**, because they cross two layer boundaries. An *Intent Bench* (text → `IntentNode`, where ontology IRIs are structurally absent from the interface, enforcing Proposition 6.1 by making violation impossible) and an *Alignment Bench* (`IntentNode` → ontology paths). Presenting these as one surface collapses the layer independence the architecture depends on.

---

## Part 5. Rendering what did *not* link

The user's instinct to ask about this is correct, and it is where comparable tools are weakest. "Not mapped" is not one state. It is six, with six different owners and six different affordances:

| State | Meaning | MORK | Owner | Affordance |
|---|---|---|---|---|
| **Unresolved** | no candidate above threshold | `UncertainMapping` + `mappingRecommendation` | Steward | suggest a concept; teach a synonym |
| **Contested** | candidates within δ of each other | `WeightedMatch` set | Steward | choose; evidence shown side by side |
| **Unsatisfied** | target requires something nothing supplies | `✗` challenge | Ontology Owner | accept incompleteness, or amend ontology |
| **Discarded** | source carries information ontology can't hold | over-specification | Ontology Owner | ontology extension request |
| **Impossible** | disjointness or type contradiction | `d = ∞`, pruned | — | shown as *excluded*, with the axiom that excluded it |
| **Minted** | model proposes a new subclass | `bt` + `c "#Name"` | Ontology Owner | ontology change review |

Three things follow that materially shape the product.

**`UncertainMapping` must look like good work.** The essay's key safety property is that a model which does not know has a *correct* thing to emit. If the UI renders uncertainty as red, or as an error count, or as an incomplete item blocking a progress bar, the pipeline will be tuned — by prompt engineers, by product managers, by anyone watching a dashboard — to produce fewer of them. That destroys the safety valve. Uncertain mappings are rendered in the same visual register as confident ones, marked as *open questions*, and counted as *questions asked*, never as *failures*.

**Exclusions are shown, with their reason.** When disjointness prunes a candidate, say so: "`hasPolicyNumber` excluded — `Layer` is disjoint from `Policy`." This is the reviewer's own ontology working correctly, and showing it builds more trust than any confidence score. It also occasionally reveals that the disjointness axiom is wrong, which is valuable.

**Minting is an ontology change, not a mapping.** The `PCIDSS ⊂ RegulatoryPeril` proposal is a request to modify the target ontology. It must route to the Ontology Owner, in a workflow that shows the proposed axiom, its siblings, the naming convention it would follow, and every mapping waiting on it. Per R3's emission positions, minting is legitimate and expected — but it is the one place where mapping bleeds into ontology governance, and conflating the two approval paths is how ontologies acquire near-duplicate classes.

The **Discarded** row deserves emphasis as a *feature*. Organisations rarely discover systematically that their ontology cannot represent things their sources routinely carry. The Galois over-specification diagnostic finds exactly this, for free. Surfacing it as "information you are currently discarding" turns a mapping tool into an ontology development instrument.

---

## Part 6. The queue: ordering by expected yield

This is the answer to *how the human facilitates the LLM's progress toward a complete mapping*, and it is the least obvious design decision in the thesis.

The naive queue is ordered by confidence ascending, or by schema position. Both are wrong, and the theory says why. The community acceleration factor states that recognising one member of a community provides evidence for M−1 others; the coupon-collector bound improves by (1 + d′) as a direct consequence. Therefore:

> **Order the queue by expected resolution yield: ask the question whose answer resolves the most open fields.**

And note the pleasing asymmetry — the highest-yield questions are also the *cheapest* for the human. "Is this section a Layer?" is instant for a specialist and cascades across four fields in this schema and potentially dozens across the corpus. "Does `xs_point` mean `hasAttachment`?" is slower to answer and resolves one thing.

```
QUEUE                                                     yield
─────────────────────────────────────────────────────────────────
1  Confirm section type · treaty.xsd §layers               4 + 12↗
   "Layer signature, 0.91 — 7 of 9 prior schemas agree"

2  Resolve PCIDSS · unknown token in 3 attributes             3 + 8↗
   "Model hypothesises RegulatoryPeril subclass"

3  Boundary · §layers and §sections both claim eff_dt         2
   "Cardinality conflict: =1 hasAttachment on shared indiv."

4  Retarget or confirm · xs_point → hasAttachment             1
   "Contested: hasAttachment 0.72 / hasExcessPoint 0.68"
```

The `↗` figure is cross-schema yield: how many fields in *other* registered sources the answer would also resolve. This is the single most motivating number the interface can show a reviewer, because it makes their leverage legible. It is the difference between "you have 400 fields to review" and "answer these 12 questions and 340 fields resolve themselves."

Two refinements:

**Escalate, don't enumerate.** Present the section question first. Only if section confirmation fails to resolve a field does that field appear individually. A queue that lists 400 fields has thrown away the acceleration factor before the reviewer even sits down.

**Boundary obstructions jump the queue.** A cardinality conflict or disjointness contradiction across a section overlap is a non-trivial H¹ obstruction: locally everything is feasible, globally nothing is. These cannot be resolved by accumulating more field-level evidence, and they block completion of every section they touch. Treat them as blockers, not as low-confidence items.

---

## Part 7. The interaction vocabulary

What can the human *say*? Six verbs, disjoint, each a single keystroke, each with distinct consequences in both learning loops:

| Verb | Key | Human means | MORK | Domain loop | Notation loop |
|---|---|---|---|---|---|
| **Confirm** | `↵` | this is right | approve → `:active` | projection +1; cassette candidate | — |
| **Retarget** | `t` | right idea, wrong target | `WRONG_TARGET` + new target | −1 old, +1 new | — |
| **Reshape** | `s` | right target, wrong structure | `WRONG_STRUCTURE` | **no change** | errata signature |
| **Decline** | `x` | shouldn't be mapped | `OUT_OF_SCOPE` | suppression | — |
| **Teach** | `k` | here's a domain fact | new concept / synonym / acronym | recognition only | — |
| **Defer** | `d` | not my call | route to owner/engineer | — | — |

**This table is where R1's remediation actually lives.** The rejection taxonomy is not a data-model nicety; it is unreachable without a UI affordance. Given only *approve* and *reject*, a reviewer who sees a correct target wrapped in a malformed DAG has exactly one button, and pressing it teaches the projection matrix that a correct `(concept, property)` pairing was wrong — inverting the premise of Theorem 4.1(ii) and corrupting the convergence evidence stream in the direction the monotonicity proof explicitly excludes. The **Reshape** verb is the fix, and it must exist at the interaction layer or the separation is theatre.

Two notes on **Teach**, which is the most underrated verb. It covers "in our house `xs_point` always means attachment," "`PCIDSS` is the payment card standard," "`ccy` is our abbreviation for currency." These facts feed recognition (`q_lex`, acronym labels, the taxonomy) without touching projection statistics. They are cheap for the expert, permanent, and compound. A reviewer who teaches three abbreviations on Monday has improved every subsequent schema from the same vendor.

**No modals.** Decisions are made in place, with the full evidence panel visible. A modal that covers the witnesses-and-challenges panel at the moment of judgement is actively harmful. Retargeting opens an inline picker over the ontology tree, filtered by type compatibility and ranked by the same alignment scoring, with disjointness-excluded candidates shown greyed *with their exclusion reason* rather than hidden.

---

## Part 8. The surfaces

Six linked views, one persistent selection propagating across all of them — the model is a debugger's current frame or an IDE's active symbol, not a series of pages.

### Atlas — orientation and triage

A treemap of the source, sections as rectangles sized by field count, coloured by resolution state (resolved / contested / unresolved / blocked). Boundary obstructions drawn as edges between rectangles. One glance answers: where is the work, and what is blocking. This is the only view where a graph-like rendering earns its place, and only because the node count is sections (tens) rather than mapping nodes (thousands).

### Bench — the primary working surface, ~80% of session time

The layout *is* the duality of intent. Left: implicit intent. Right: explicit intent. Centre: the bridge and its evidence.

```
┌─ SOURCE ─────────────┬─ ALIGNMENT ──────────────────┬─ TARGET ──────────────┐
│ treaty.xsd           │                              │ ctr: reinsurance v4.2 │
│ └ Contract           │  section §layers             │ ├ ContractComponent   │
│   ├ Metadata         │  ▸ hypothesis: ctr:Layer     │ │ └ Layer          ◀  │
│   └ layers [ ]  ◀    │    community .91 · axiom .84 │ │   ├ SurplusLayer    │
│     ├ xs_point   ◀   │    7 of 9 prior schemas      │ │   └ QuotaShareLayer │
│     ├ lmt            │                              │ ├ MonetaryAmount      │
│     ├ ccy            │  REQUIRES          SATISFIED │ └ Policy ⊘ disjoint   │
│     ├ pct_share      │  ✓ hasAttachment   xs_point  │                       │
│     ├ layer_no   ⚠   │  ✓ hasLimit        lmt       │ Layer requires:       │
│     └ eff_dt     ↔   │  ✓ hasShare        pct_share │  ≡ hasAttachment      │
│                      │  ✗ hasPerilScope   —         │    → MonetaryAmount   │
│ xs_point             │  ⊘ not Policy      clear     │  ≡ hasLimit           │
│ ─────────            │                              │    → MonetaryAmount   │
│ xsd:decimal          │  UNUSED                      │  ≡ =1 hasShare        │
│ "Excess point"       │  ⚠ layer_no  no candidate    │    → xsd:decimal      │
│ siblings: lmt, ccy,  │  ↔ eff_dt    parent section  │  ∀ hasPerilScope      │
│   pct_share, layer_no│                              │    → Peril            │
│                      │  ███████▁ 3 of 4 required    │  ⊥ Policy             │
│ ribbon: xs · point   │  ██████▁▁ 5 of 7 consumed    │                       │
│         ●●○   ●●●    │                              │                       │
└──────────────────────┴──────────────────────────────┴───────────────────────┘
 ↵ confirm   t retarget   s reshape   x decline   k teach   d defer   ⌥m MCN
```

Everything the reviewer needs to adjudicate is simultaneously visible: what the source looks like, what company it keeps, what the target demands, what is satisfied, what is not, and both coverage figures. No scrolling, no modals, no navigation required to reach a decision.

### Dossier — single-claim deep dive

Reached on demand from the Bench. Full witness list, ranked alternatives with margins, the evidence decomposition in full, the three-timescale availability display, prior decisions on similar fields, and the complete provenance chain rendered in domain language. Used perhaps one time in twenty, but essential when it is needed.

### Boundary — obstruction resolution

Two sections side by side with the shared individual in the middle, and the specific obstruction named: which axiom is violated, which two local choices conflict, what the resolution options are. Engineer-facing. Rare and high-stakes.

### Ledger — audit

Provenance chains, `supersedes` history, `userDeclined` records with reasons, effective periods, the retrospective-reopen log. Queryable. The paper's Principle 5 rendered for humans rather than for SPARQL, which means the chain must be readable by someone who has never heard of `ConstraintProvenance`.

### Studio — the other side of the fence

Pack Maintainer only. Part 10.

**Reference class.** The correct visual and interaction references are IDEs, diff tools, DAWs, CAD and clinical review systems: dense, keyboard-driven, multi-pane, persistent selection, no modals. The *incorrect* references are modern web application conventions — cards, dialogs, infinite scroll, generous whitespace, one-thing-per-screen. A beautiful, contemporary-looking application will be a materially worse tool here, and the pressure to build one will be constant.

---

## Part 9. Bulk action without recklessness

An API with 200 entity types where 180 follow one pattern must not generate 180 reviews. The paper's `templateMapping` already exists to solve this for token economy; the same lever solves it for human attention.

**Pattern-by-exception.** Approve the template once. Subsequent instantiations present as: *"47th instance of pattern `P_Entity`, approved 12 March by A. Steward. Differs only in: class `ctr:Cedant`, identity path `party.id`."* The reviewer reads a two-line diff, not a mapping. Confirm is one keystroke, and a divergence beyond a configured threshold escalates to full Bench review automatically.

**Bulk actions are gated on calibration.** This is R5's calibration gate at the interaction layer. Plot asserted `weighting` against actual approval rate. If the curve is flat or non-monotone, confidence carries no information and the projection matrix is being fed noise — Proposition 2.12's monotonicity premise fails empirically while holding formally. While calibration is broken, *disable* bulk confirm and require per-item review. This is the single most important control in the product, because it is the only thing standing between "the system appears to be converging" and "the system is converging."

**Session hygiene, because rubber-stamping is worse than no review.** A fatigued reviewer clicking Confirm inflates the confident tail that calibration monitoring depends on, producing a system that looks trustworthy and is not. Cap batch sizes. Cap session length. Measure per-reviewer agreement against peers on overlapping items. Consider seeding occasional known-difficult items as calibration samples — a technique standard in radiology and security screening — but frame them honestly as calibration, never as tests, or you will lose the reviewers.

---

## Part 10. The seam: both sides of the fence

The user's question about engaging with materials on both sides has a clean answer, and it is a restriction rather than an integration.

> **Only two things cross the fence, in opposite directions. Typed failures travel from domain to pedagogy. Approved exemplars travel from pedagogy's perspective back as corpus. Nothing else crosses, and no human works on both sides in the same session.**

**Left to right — typed failures.** A `WRONG_STRUCTURE` or `WRONG_NOTATION` rejection is not a mapping fact; it is a fact about the model's grasp of MORK. It carries no domain content and must not, per R1's projection-update contract, touch any projection count or community weight. It flows to the Studio as an abstracted signature — *"`ap` asserted without `xr` in applicative context, 14 occurrences, 3 deployments"* — with one representative example. The Pack Maintainer never reviews a mapping; they review a failure pattern.

**Right to left — exemplars.** Confirmed mappings with high weighting and clean provenance are cassette candidates. Pedagogy becomes downstream of practice: the teaching corpus is generated from work the domain experts have already approved, without those experts ever knowing they are authoring curriculum. The one discipline to preserve is the essay's own: cassettes are hash-pinned and frozen for reproducibility, templates are retrieved live. A frozen cassette must never be mistaken for current practice, or the model will confidently reproduce structure that `supersedes` chains retired six months ago.

### Studio

The Pack Maintainer's surface, structurally analogous to the Bench but one level up:

| Panel | Content |
|---|---|
| **Failure signatures** | Ranked by frequency × cost. Each: lint code, occurrences, deployments affected, example, current doctrine fragment, proposed amendment |
| **Errata queue** | Candidate L4 entries, budget consumed against the ≤600 token cap, review status, `supersedes` chain to prior errata |
| **Lens coverage** | FCA diagnostic over the repair log. `γ(f(L)) ⊃ L` → lens missing terms that co-fail with it; `γ(f(L)) ⊂ L` → lens carrying terms nothing needs from it. Turns the essay's CI gate from a hand-maintained partition into a checked one |
| **Cassette corpus** | Candidates promoted from confirmed mappings, round-trip proofs, frequency-ordered by real corpus statistics |
| **Calibration** | Confidence versus approval curve; silent-error rate; confident-tail approval rate |
| **Eval & release** | Held-out suite results per pack version *and per model version*. Diff against previous. Pack release with manifest hash |

The errata card is itself a governed MORK artefact — provenance, review status, `supersedes`, named graph, no writes to `:active` without approval. This costs nothing to implement (the vocabulary exists) and means the pedagogy inherits the framework's own audit guarantees. When a cohort of bad mappings surfaces eighteen months later, "which teaching configuration produced these?" is answerable with the same SPARQL used for mappings.

---

## Part 11. Instrumenting trust

Three displays that determine whether the reviewer believes the system, and whether that belief is warranted.

**Convergence, honestly stratified.** The declining-work curve is the product's main value proposition, and per R4 it is uninterpretable unless held within a fixed `(pack hash, profile hash, model id)` stratum. Render pack releases and model bumps as explicit stratum boundaries — vertical rules with annotations — rather than allowing them to appear as discontinuities in a single misleading series. A dashboard that shows a smooth curve across a model upgrade is lying.

**Calibration, shown to reviewers, not only to maintainers.** A confidence figure is meaningless until the reviewer knows what it has historically predicted. *"Mappings scored 90+ were approved 94% of the time in your deployment"* converts an arbitrary number into a usable prior. Without it, reviewers learn — correctly — to ignore confidence entirely, and the entire uncertainty apparatus becomes decoration.

**Copy discipline.** Remark 4.2's `p_val > 0` must be reflected in vocabulary, or the interface will make a claim the architecture cannot support:

| Never | Always |
|---|---|
| Valid ✓ | Well-formed |
| Verified | Consistent |
| Correct | Approved *(human action only)* |
| Validated | In force |

Reserve *approved* for human decisions exclusively. Never raise `weighting` because validation passed — that is the mechanical form of the inference R5's eighth kernel invariant forbids, and it inflates precisely the tail that calibration monitoring exists to watch.

**The reopened queue.** When the retrospective challenge sweep fires — a new disjointness axiom arrives and previously-approved mappings now fail — the reviewer must be told clearly *why now*. This is the most trust-fragile moment in the product: the system previously said something was fine and now says otherwise. Frame it as new information rather than as prior error, name the specific axiom, and show what changed. Handled well it increases trust, because it demonstrates the system is still watching. Handled badly it reads as unreliability.

---

## Part 12. Anti-patterns

Each of these is a plausible, well-intentioned design decision that would do real damage.

| Anti-pattern | Why it is tempting | What it costs |
|---|---|---|
| Node-link graph as primary view | demos beautifully; the DAG is *right there* | unusable past ~50 nodes; the DAG is machine-facing |
| Single confidence number | clean, familiar | reviewers learn to ignore it; evidence structure discarded |
| Approve / reject only | simplest possible affordance | **forces taxonomy collapse; poisons the projection matrix** |
| Lint errors shown to stewards | "transparency" | trains distrust; not their job; not their competence |
| `UncertainMapping` styled as error | it *is* incomplete | suppresses the safety valve; drives hallucination back up |
| Field-ordered queue | obvious, exhaustive | discards community acceleration entirely |
| "% mapped" progress bar | every tool has one | optimises coverage over correctness |
| Hiding empty evidence channels | reduces clutter | conflates *contested* with *never observed* |
| Uncapped review sessions | throughput | rubber-stamping inflates the confident tail and breaks calibration |
| Unified pack + mapping UI | "one place for everything" | breaks role perimeters; stewards try to fix the LLM |
| Modals for decisions | standard web pattern | occludes evidence at the moment of judgement |
| Modern web aesthetic | looks credible to buyers | low density defeats the task; wrong reference class |

---

## Part 13. Build order

The thin slice is smaller than it appears, because the Bench alone is a product.

1. **Bench for a single section** — three columns, witnesses and challenges, two-sided coverage, six verbs, keyboard-first. Against a *real* schema and a *real* ontology from day one; synthetic data hides exactly the density problems that will kill the design.
2. **Typed rejections wired end to end** — including the projection-update filter. Without this the domain loop is corrupting itself from the first session, and no later fix recovers the lost signal.
3. **Token ribbon** — highest value-per-pixel in the product.
4. **Atlas plus yield-ordered queue** — converts a pile of fields into a short list of high-leverage questions, and makes the reviewer's leverage visible.
5. **Template-by-exception** — the difference between 180 reviews and 1 review plus 179 confirmations.
6. **Calibration display and bulk gate** — required before bulk actions are enabled at all.
7. **Boundary view** — once obstruction rates justify it.
8. **Ledger, then Studio** — Studio last; it has one user, and its input signal only becomes meaningful once steps 2 and 6 are producing clean, typed, calibrated data.

---

## Coda

The framework's own thesis is that mapping is the alignment of two dual forms of intent across a structural and semantic gap. The interface's thesis should be read as its direct corollary: **the human occupies that gap, and the interface's only job is to render both forms of intent in their native idiom, make the gap and its obstructions legible, and capture the human's adjudication cleanly enough that both learning loops can consume it without contaminating each other.**

Everything else — the graph, the vocabulary, the codes, the precedence derivation, the compilation — is plumbing that should remain invisible to the person whose judgement the entire apparatus exists to capture, amplify, and eventually render largely unnecessary.

