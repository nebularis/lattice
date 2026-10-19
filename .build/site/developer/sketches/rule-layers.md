# Integrating Logical English with an OWL 2 DL Rule Stack

## The short version

- **Logical English (LE) doesn't interpret free text.** It is a controlled natural language (CNL). It parses reliably because you declare the sentence shapes (templates) up front. It won't read an ingested contract and extract rules. What it offers is a rigorous, human-readable **intermediate representation** between messy contract wording and formal rules.
- **The best integration point** is probably: *LLM translates contract wording → LE → your rule IR → SHACL/SWRL/SPARQL*. Prolog, if used at all, stays a compile-time tool at the edge, never in your runtime.
- **Erlang isn't a meaningful head start.** The kinship is historical and syntactic, not semantic. More below.
- **The hard problem isn't parsing.** It's the semantic mismatch between LE's logic-programming semantics and OWL's. Plan for that explicitly.

---

## 1. What LE actually gives you

An LE document looks roughly like this:

```
the templates are:
*a person* is eligible.
*a person* is aged *a number*.
*a person* has a prior claim.

the knowledge base eligibility includes:
a person is eligible
if the person is aged an age
and the age >= 18
and it is not the case that
    the person has a prior claim.
```

It translates to something like:

```prolog
is_eligible(A) :- is_aged(A, B), B >= 18, \+ has_a_prior_claim(A).
```

The parts worth borrowing:

1. **The templates.** These are effectively a vocabulary declaration: predicate name, arity, and argument types. They map naturally onto ontology terms.
2. **The rule grammar.** It covers `if / and / or`, variable introduction with "a" and back-reference with "the", "it is not the case that", and comparisons and arithmetic.
3. **Scenarios and queries.** These are test cases written in the same language, which is valuable for verification (see option E).

The part you'd want to avoid depending on is SWI-Prolog as a runtime.

A caveat on LogicalEnglish2: check its current implementation language and whether it exposes an intermediate AST or JSON output. If the rewrite has moved parsing off Prolog or produces a clean AST, several of the options below get easier. I'd verify the repo's current state rather than rely on my assumptions.

---

## 2. The semantic gap

This is where integrations quietly go wrong. LE inherits Prolog's semantics:

| LE / Prolog | OWL 2 DL | SWRL | SHACL / SPARQL |
|---|---|---|---|
| Closed world, negation as failure | Open world, classical negation only | No NAF | `FILTER NOT EXISTS` and SHACL constraints are effectively closed-world |
| n-ary predicates | Unary classes and binary properties only | Unary and binary atoms | Arbitrary graph patterns |
| Recursion | Limited (property chains, transitivity) | Yes, but DL-safe only | Property paths (limited); SHACL-AF rules iterate |
| Arithmetic, dates | Datatype restrictions only | Built-ins (patchy reasoner support) | Full `FILTER` / `BIND` |
| Exceptions and defeasibility ("unless…") | No | No | Encodable, with care |

In the example above, SWRL **cannot** express the `it is not the case that` clause. Under OWL's open world, the absence of a prior claim doesn't mean there isn't one. The SPARQL/SHACL version can:

```sparql
CONSTRUCT { ?p :isEligible true }
WHERE {
  ?p :age ?a . FILTER(?a >= 18)
  FILTER NOT EXISTS { ?p :hasPriorClaim ?c }
}
```

Since you already compile to three backends, give your compiler an explicit **routing policy**:

- **SWRL** for positive, DL-safe Horn rules over unary and binary predicates.
- **SHACL-AF rules or SPARQL** for NAF, aggregation, arithmetic, and exceptions.
- **Reject or flag** constructs you can't express faithfully, rather than silently weakening them.

**n-ary templates** (e.g. `*a person* pays *an amount* to *an insurer* on *a date*`) need reification. The usual approach is the W3C n-ary relation pattern: a `Payment` class with `payer`, `amount`, `payee`, and `date` properties. That mapping belongs in your template-to-ontology alignment, not in the parser.

---

## 3. Integration options

### A. LE as the LLM's target language *(highest value)*

Instead of having the LLM map contract wording directly into OWL sub-graphs, have it produce LE:

1. **Generate LE templates from your ontology.** Use `rdfs:label`s, property domains and ranges, or an annotation property like `:leTemplate "*a person* is aged *a number*"`. The LLM can then only write rules in your vocabulary, so every parsed rule is already grounded.
2. The LLM translates a clause of the contract into LE rules.
3. The LE parser validates the output. Parse errors and unknown templates go back to the LLM in a repair loop. A CNL gives you a hard correctness gate, which LLM output badly needs.
4. A **human reviewer** (underwriter, lawyer) reads the LE. Reviewing "a person is eligible if…" is far easier than reviewing SHACL.
5. The approved LE compiles to your IR, then to your backends.

This uses LE as a well-designed CNL, which is what it is. You're not asking it to do NLP it was never built for.

### B. Run LE's compiler as a sandboxed build-time service

Wrap SWI-Prolog and the LE translator in a container. A Python worker on RabbitMQ sends LE text and gets back the generated clauses, ideally as JSON. SWI-Prolog can emit JSON easily, so a small wrapper predicate would do it.

The output is a very restricted Horn-clause subset, so it's straightforward to walk in Python and convert to your rule IR.

- **Pros:** you get upstream LE's exact semantics and improvements for free.
- **Cons:** there's Prolog in your build pipeline, though it's stateless and isolated, like depending on any external compiler. Nobody on the team has to write Prolog beyond a thin wrapper.

This fits your stated goal well. You borrow the interpretation of text and discard the runtime.

### C. Re-implement the grammar in your own stack

LE's grammar is small. Reasonable fits:

- **F# with FParsec.** This is an excellent fit: discriminated unions for the AST, and pattern matching for the IR translation.
- **Python with Lark.** It sits closest to your compilation pipeline.
- **Elixir with NimbleParsec.** This works if you want it near your messaging tier.

Emit your rule IR directly, with no Prolog anywhere.

The risks:

- Subtle semantics such as variable scoping with "a"/"the", template matching with multi-word arguments, and how "or" and nested negation are handled.
- Drift from upstream.

To mitigate, use the LE repo's examples as a **conformance corpus**. Run both implementations (option B as an oracle) and diff their outputs in CI.

A pragmatic path is **B first, then C**. Start with B to learn what you actually need, then replace it with C once your subset stabilises. Your subset may end up smaller and more targeted than full LE.

### D. Reverse direction: OWL rules → LE for explanation

Your eligibility and calculation sub-graphs can be *verbalised* into LE-style sentences for audit, customer explanation, or regulator review. This works even for rules that never came from LE. Once you have the template alignment from option A, generation is mostly template filling.

### E. Differential testing oracle

LE scenarios and queries are executable test cases. Run the LE program through Prolog, or through s(CASP) for justification trees, and run the same scenario data through your compiled SHACL/SPARQL. Then compare the answers. This catches translation bugs, especially around negation and the open/closed-world boundary, and it keeps Prolog entirely in test infrastructure.

---

## 4. On Erlang

The connection is real but shallow:

- **What's shared:** the first Erlang interpreter was written in Prolog, and Erlang borrowed the syntax (clauses, atoms, capitalised variables, `:-`-ish heritage).
- **What's missing:** Erlang has **one-way pattern matching, not unification**, and **no backtracking or resolution**. Those are exactly what make Prolog a logic engine.

You could embed a Prolog-in-Erlang (Robert Virding's Erlog exists), but you'd be running a logic engine inside the tier whose job is managing quote and negotiation FSMs. That's the blending you said you want to avoid, and it buys nothing over the options above.

Keep Erlang doing what it's good at. If rule evaluation needs to happen near the FSMs, have them call out over RabbitMQ to whatever evaluates your SHACL/SPARQL.

Of your languages, the parser and translator work suits F# or Python best.

---

## 5. Other things worth looking at

- **Attempto Controlled English (ACE).** This is the most directly relevant alternative. It is another CNL, and its tooling (the APE parser, the OWL verbaliser) maps a subset of ACE **directly to OWL/SWRL and back**. Its semantics are first-order and classical, so it aligns with OWL much better than LE does. LE is more legal-drafting-oriented and has rule/NAF semantics. You might use ACE-style constructs for the ontological parts ("every policy has exactly one policyholder") and LE-style for the rules.
- **LegalRuleML.** An OASIS XML standard for legal rules. It handles deontic operators (obligation, permission, prohibition), defeasibility, and provenance back to source text. It's useful as an interchange or annotation format even if it's not your primary IR. Contract obligations will eventually push you toward deontic concepts that neither LE nor OWL handles natively.
- **Catala.** A language for encoding legislation with first-class default and exception logic, designed around the "general rule, unless…" structure that contracts are full of. It's worth reading for how it models exceptions.
- **Blawx.** A legal rules tool built on s(CASP), useful for seeing how explanations and justifications can be surfaced to non-technical users.
- **Datalog engines with RDF support** (e.g. RDFox). These are relevant if the routing policy in section 2 keeps pushing rules out of SWRL. Datalog with stratified negation is close to LE's semantics while staying native to RDF.

---

## Suggested architecture

```
contract text
   │  LLM (constrained by templates generated from your ontology)
   ▼
LE rules  ──► parse / validate ──► (repair loop back to LLM)
   │           [Option B: SWI-Prolog container, later Option C: F#/Python parser]
   ▼
human review of the LE text
   ▼
Rule IR (your existing OWL sub-graph representation)
   │  routing policy: SWRL | SHACL-AF | SPARQL | reject
   ▼
compiled rules ──► runtime (Jena etc.)

side channels:
  • LE scenarios → differential tests against the compiled rules (Option E)
  • IR → LE verbalisation for explanations (Option D)
```

Prolog never enters your runtime, Erlang stays focused on lifecycle FSMs, and the parts of LE you'd be borrowing, the CNL design and the template discipline, end up doing the most work.

---

# Stratified Datalog, Deontic Reasoning, and Whether You Need a New Engine

This has three parts:

1. Why Datalog with stratified negation matches LE's semantics, and how it can sit alongside OWL.
2. Why insurance contracts are full of deontic concepts, and the specific ways OWL fails on them.
3. The build-versus-adopt question.

The conclusion of part 3, up front: the compelling story is **not** "replace RDF and OWL." It is "OWL answers a different question than the one contracts ask once you get past eligibility." You probably don't need a new storage layer. You probably do need a formally layered rule tier.

---

## Part 1: Datalog with stratified negation and LE

### What an LE program is, semantically

LE compiles to *normal logic programs*: Horn clauses plus negation as failure (NAF). Nearly all of LE's legal examples share three properties:

- **No function symbols in practice.** Arguments are constants, numbers, and dates, not nested terms.
- **Finite data.** The facts come from a scenario.
- **No recursion through negation.**

A normal logic program with those properties **is** a Datalog program with stratified negation. For stratified programs the main semantics of logic programming agree: the perfect model, the well-founded model, and the unique stable model are all the same model. Whatever SWI-Prolog answers for your eligibility rules, a Datalog engine computes the same answer, just by a different method:

| | Prolog (how LE runs today) | Datalog |
|---|---|---|
| Evaluation | Top-down, goal-directed (SLDNF resolution) | Bottom-up, computes all consequences to a fixpoint |
| Clause order | Matters, and left recursion can loop | Irrelevant |
| Termination | Not guaranteed | Guaranteed on finite data |
| Output | Answers to one query | A *materialised* set of derived facts |

The bottom-up style matters for you. Materialising derived facts is what you already do when SHACL-AF or SPARQL `CONSTRUCT` rules write triples back into Jena.

### Stratification in one example

Build a dependency graph: predicate `p` depends on `q` if `q` appears in the body of a rule for `p`. Mark the edge *negative* if `q` appears under negation. A program is stratifiable if no cycle passes through a negative edge.

```prolog
% generic Datalog syntax
excluded(C)  :- claim(C), cause(C, flood), in_flood_zone(C).
excluded(C)  :- claim(C), late_notification(C).
reinstated(C):- excluded(C), waiver_endorsement(C).
covered(C)   :- claim(C), within_period(C), not excluded(C).
covered(C)   :- reinstated(C).
payable(C)   :- covered(C), not fraud_flag(C).
```

This splits into strata, and the engine evaluates each one completely before the next begins:

- **Stratum 0:** base facts such as `claim`, `cause`, and `fraud_flag`.
- **Stratum 1:** `excluded` and `reinstated`, which use only positive dependencies.
- **Stratum 2:** `covered`, which negates `excluded`. That is safe because `excluded` is finished.
- **Stratum 3:** `payable`.

The key idea is **local closed-world reasoning**. `not excluded(C)` means "`excluded(C)` is not in the completed lower stratum." Negation is never applied to something still being computed. That is why the answer is unique and doesn't depend on evaluation order.

### Where LE goes beyond stratified Datalog

| LE feature | Datalog status |
|---|---|
| Arithmetic and date comparisons | Supported as built-ins. Rules must be *safe*: every variable bound by a positive atom. |
| Aggregation ("the total of all claims…") | Supported in most engines, as *stratified* aggregation. |
| Lists and nested terms | Not supported in pure Datalog. It rarely matters for contracts. |
| Mutual exceptions (A unless B, B unless A) | Not stratifiable. Needs well-founded semantics (a three-valued answer: "undefined") or stable models (answer set programming, as in s(CASP)). |

The last row is realistic in contracts, for example two clauses that each carve an exception out of the other. For this, stratification also works as a **diagnostic**. A cycle through negation in extracted rules usually means either a genuine ambiguity in the contract or an extraction error. Either one should go to a human rather than to a clever solver.

### Why this sits well with OWL

**OWL 2 RL is Datalog.** The OWL 2 RL profile is defined by a set of Datalog rules over triples. A Datalog engine can therefore materialise OWL 2 RL entailments and your NAF rules in a single fixpoint computation. RDFox does exactly this.

If you rely on full OWL 2 DL reasoning (HermiT, Pellet, and so on), a Datalog engine can't reproduce it. Disjunction and existentials fall outside Datalog. The principled combination is **layering**:

```
Stratum 0:  OWL 2 DL entailment (classification, realisation) → materialised types and properties
Stratum 1+: stratified rules, where NAF means "not entailed by the layers below"
```

This works well if you respect one constraint: **rule-derived facts must not feed back into DL reasoning**. Once they do, NAF over an open-world theory that is still changing becomes semantically slippery. The formal treatments of that territory are dl-programs (Eiter et al.) and Hybrid MKNF (Motik and Rosati). The practical guidance from that literature: DL results flow up into rules, rules never flow down into DL, and your compiler enforces this.

**Your existing stack already stratifies, informally.** If rule B's SPARQL uses `FILTER NOT EXISTS` over triples rule A writes, then A must run first. The cheapest high-value step available to you is to make this formal:

- Have your compiler build the predicate dependency graph over your rule IR.
- Compute the strata, and order SHACL-AF and SPARQL execution by stratum.
- Reject or flag cycles through negation.

That gives you LE-equivalent semantics without a new engine.

---

## Part 2: Deontic concepts in insurance contracts

### Why they're everywhere

Your eligibility and calculation layers encode **constitutive** rules. These define what counts as what: "a person counts as eligible if…" or "the premium is computed as…". Contracts consist mostly of **regulative** rules instead. These allocate duties and entitlements between parties, and they can be broken.

In an insurance policy:

| Deontic concept | Example |
|---|---|
| Obligation (insured) | Pay the premium. Notify a claim within 30 days. Disclose material facts. Mitigate loss. Cooperate with investigation. |
| Obligation (insurer) | Indemnify covered losses. Respond to a claim within N days. Give notice before cancellation. |
| Prohibition | The insured must not admit liability or settle with a third party without the insurer's consent. |
| Permission | The insured may cancel within a 14-day cooling-off period. The insurer may inspect the premises. |
| Power (Hohfeld) | The insurer may cancel for non-payment, which *changes* the normative state. Subrogation rights arise on payment. |
| Contrary-to-duty obligation | If notification is late, the insured must explain why, and the insurer may reduce payment to the extent prejudiced. |

Loan agreements are even more heavily deontic: positive and negative covenants, reporting duties, events of default, cure periods, and acceleration powers.

Two structural points:

- **The obligations are directed.** Each has a *bearer* and a *counterparty*. It is not just "X ought to happen" but "A owes B that X happens by T."
- **Violation is normal operating data, not an error.** Late notifications happen every day, and the contract says what follows from them. The logic has to keep working in the presence of breaches.

### Where OWL fails, concretely

**1. OWL describes what is. Obligations describe what ought to be.**

Suppose you encode "claims must be notified within 30 days" as an axiom:

```turtle
:Claim rdfs:subClassOf [ a owl:Restriction ;
    owl:onProperty :hasTimelyNotification ;
    owl:someValuesFrom :Notification ] .

:claim42 a :Claim ; :hasNotification :n1 .   # n1 arrived on day 45
```

There are two outcomes, and both are wrong:

- **Open world (the default):** the reasoner concludes that `:claim42` has *some* timely notification you don't know about. You have invented compliance rather than detecting a violation.
- **Closing the world** (asserting that `n1` is the only notification and that it isn't timely): the ontology becomes **inconsistent**. In classical logic an inconsistent theory entails everything, so one late claim poisons reasoning about every policy in the graph.

Deontic logic avoids this by separating the ideal from the actual. "It is obligatory that p" and "not p" can hold together consistently, and their combination is exactly what defines a violation.

**2. Detecting a violation is inherently closed-world and temporal.**

"The obligation is violated if **no** notification occurred **before** the deadline" requires two things:

- **NAF over events.** OWL has no NAF.
- **Time.** Deadlines are computed relative to trigger events ("within 30 days *of the loss*"), and obligation states change as the clock runs.

OWL has no temporal semantics. Dates are just literals.

**3. Defeasibility and priority.**

Consider a typical clause chain: "The insurer shall pay… subject to exclusion 4(b)… except where waived by endorsement." That is a general rule, an exception, and an exception to the exception, with an explicit priority between them. Legal reasoning also applies general precedence principles: *lex specialis* (the specific rule beats the general one) and *lex posterior* (the later rule beats the earlier one).

OWL is **monotonic**. Adding an exclusion can never withdraw an entailment. It can only add entailments or cause inconsistency. Your stratified NAF handles the simple cases, but explicit priorities between conflicting rules need a defeasible formalism.

**4. Modality isn't part of OWL.**

Modal description logics exist, but OWL 2 has no "obligatory" operator. The usual workaround is to *reify* obligations as individuals. That works, but it means OWL stores the structure of an obligation while the meaning (when it becomes active, when it is fulfilled or violated) has to be computed somewhere else.

A related subtlety: is "permitted" the same as "not prohibited"? Legal theory distinguishes **weak permission** (nothing forbids it) from **strong permission** (explicitly granted). Weak permission is, once again, a closed-world question.

### The workable pattern

Reify obligations in RDF, and compute their state with stratified rules:

```turtle
:ob-claim42-notify a :Obligation ;
    :bearer :insured7 ; :counterparty :insurerA ;
    :requiredAction :NotifyClaim ; :about :claim42 ;
    :triggeredBy :loss42 ; :deadline "2025-03-31"^^xsd:date ;
    :sourceClause :policy7-clause-9.2 ;   # provenance back to the contract text
    :reparation :ob-claim42-explainDelay .
```

```prolog
fulfilled(O) :- obligation(O), action_done(O, E), event_date(E, D),
                deadline(O, DL), D <= DL.
violated(O)  :- obligation(O), deadline(O, DL), now(T), T > DL,
                not fulfilled(O).
active(R)    :- reparation(O, R), violated(O).   % contrary-to-duty obligation
```

OWL still does valuable work in this pattern. It types parties, actions, and events, and classifies them (a `:FloodLoss` is a `:Loss`). It also integrates contract data with everything else in your graph. The rules then do the normative bookkeeping.

**A note on your Erlang tier.** An obligation's lifecycle (pending, active, fulfilled, violated, discharged) is a finite-state machine with timers. The rule layer derives which obligations exist and what their conditions are. Deadline tracking and state transitions are exactly what `gen_statem` supervision is good at. This isn't blending logic into Erlang. It's using Erlang for lifecycle management, which it already does for quotes.

### LegalRuleML, and ODRL

**LegalRuleML** (an OASIS standard, built on RuleML) is best read as a checklist of what a legal rule IR needs:

- **Deontic operators:** Obligation, Permission, Prohibition, and Right, each with bearer and auxiliary party roles.
- **Defeasibility:** rule strength (strict, defeasible, or defeater) and an explicit `overrides` relation between rules.
- **Reparation and penalty chains:** first-class support for contrary-to-duty structures.
- **Multiple time dimensions:** when a rule is in force, when it is efficacious, and when it applies to events. This matters for endorsements and mid-term changes.
- **Provenance and authority:** links from each rule to its source text fragment and the jurisdiction it applies in. This is directly useful for your ingestion pipeline.
- **An RDFS metamodel,** so it can be aligned with your ontology.

It is a representation, not an engine. Its co-authors' reasoning work on defeasible deontic logic (Governatori's Formal Contract Logic, and implementations such as SPINdle) shows what execution looks like. My recommendation is to borrow its concepts for your IR rather than adopting its XML syntax.

**ODRL** (a W3C policy language, natively RDF) has Duty, Permission, and Prohibition, with constraints and consequences. It is less expressive than LegalRuleML, but it sits much closer to your stack and is worth checking before you invent your own vocabulary.

---

## Part 3: Do you need a native engine?

### What's actually hard

You're right that storage isn't the obstacle. Oxigraph, a Rust SPARQL engine built on RocksDB, shows that a triple store over a key-value store is well-understood engineering. The difficult parts of a reasoning engine are elsewhere:

1. **Incremental maintenance with negation.** When a notification event arrives, you want to update the derived facts, not recompute everything. Deleting facts under NAF is subtle, and it needs algorithms like DRed or Backward/Forward.
2. **Explanations.** Regulators and complaints handlers will ask two questions: "why was this claim reduced?" and "why *wasn't* it covered?" Provenance is manageable. "Why not" explanations are much harder.
3. **Time.** Obligation states change as the clock advances. That is a stream-processing problem as much as a logic problem.
4. **Defeasible priorities** beyond what stratification handles.

### Options in increasing cost

| Tier | What | When it's enough |
|---|---|---|
| **0** | Formalise stratification in your existing compiler (Part 1). Add the obligation reification pattern and violation rules as SHACL-AF or SPARQL. | Quote-time eligibility and pricing, plus batch compliance checks. **Do this regardless.** |
| **1** | Add a Datalog-over-RDF sidecar that reads from and writes back to your store: **Nemo** (Rust, reads RDF, stratified negation, aggregates, existential rules), **RDFox** (commercial, incremental, OWL 2 RL plus NAF plus aggregates, SPARQL endpoint), or **Soufflé** (C++, very fast, not RDF-native). | Many rules, performance problems with chained SPARQL, or a need for incremental materialisation. |
| **2** | Build your own engine, for example Oxigraph-style storage plus an incremental Datalog core (Rust crates such as `ascent` or `crepe`, or differential-dataflow or DBSP-style incremental computation), with defeasible and temporal extensions. | Continuous, event-driven normative monitoring at scale, with explanations, across a large book of policies or loans. |

Tier 2 is realistically a multi-person-year effort. Tier 1 gets you most of the capability while keeping RDF, OWL, and Jena as the system of record.

### The compelling story, and its limits

OWL is not the wrong tool. It is the right tool for vocabulary, classification, and integration, and those remain central to your architecture. The argument for a rule tier with LE-like semantics rests on a category difference:

- OWL answers **"what follows necessarily from what we know?"** It is monotonic, open-world, and timeless.
- Contracts ask **"given what has happened by now, who owes what to whom, what's been breached, and what follows from the breach?"** That question is non-monotonic, locally closed-world, temporal, and has to tolerate violations.

No amount of OWL modelling closes that gap. The late-notification example shows why: OWL either invents compliance or becomes inconsistent.

Whether this justifies *new infrastructure* depends on the scope of your product:

- **If your system stays at quote, eligibility, and pricing,** Tier 0 is sufficient, and the deontic material is mostly future-proofing.
- **If it moves into policy administration, claims handling, or covenant monitoring,** you will hit the deontic wall. Once you are there, Tier 1 is the smallest change that handles it properly.

One final point connects back to your LE question. Stratified Datalog is the formalism that makes LE, OWL 2 RL, and your SHACL/SPARQL rules semantically consistent with each other. If you design your rule IR around it, adding deontic and defeasible extensions later means extending that IR rather than replacing it.

---- 

# The Missing Layer: a Compiled Normative Evaluation Tier

Yes, there is a missing layer. I'd adjust the framing, though. It probably shouldn't sit **before** the data gets into OWL, acting as a filter that transforms data on its way in. It should sit **beside** the graph: it reads positioned snapshots from the store, evaluates compiled rules, and writes its conclusions back as decision records with provenance. The graph stays the system of record for both the inputs and the conclusions. The tier holds what OWL cannot: the semantics of change, time and obligation.

Your patterns guide already contains most of the hard infrastructure this tier needs. You built it for concurrency and ordering, but it turns out to be exactly what makes non-monotonic reasoning sound.

## 1. Your guide already solves the hardest part: when closed-world reasoning is justified

The deontic example from before was "violated if no notification arrived before the deadline." That inference is only sound if you can prove you have seen every notification up to some point. Otherwise negation as failure is guessing.

Your persistence patterns provide exactly that proof:

| What the normative tier needs | What LATTICE already has |
|---|---|
| **A licence for negation as failure**: "I have seen everything up to here" | Dense per-stream `(epoch, seq)` positions and the S3 gap audit. With sparse ordering, NAF is never provably safe. With dense ordering and a clean gap scan, it is. |
| **Reproducible decisions**: "what did we know when we declared this claim late?" | Decision records that must cite an exact `snapshotHash` (data-architecture §5 rule 4, value-based CAS). Extend this so they cite input positions. |
| **Deadlines evaluated against the right clock** | The three-clock separation: valid time `occurredAt`, transaction time, and logical time. Deadlines are valid-time questions. |
| **Deterministic evaluation** | The `NOW()` policy and QP4 determinism tests. Rules must never read the wall clock (see §4). |
| **Handling late or backfilled data**, which retracts earlier conclusions | Append-only decision records, patch-log receipts and `fnd:supersededBy`, plus epoch bumps when history is rewritten |
| **Idempotent re-evaluation** | P0 deterministic IRIs. An evaluation's inputs are immutable, so its identity can be derived from them. |
| **Choosing an execution backend per rule** | The capability planner, `min_level` fail-fast, and TCK approach. Reuse the same idiom for rule backends. |

Judging from the names, you also already have a **lowering** concept: the `LOWERING_RECORD`, `GENERATED_OUTPUT` and `INVALIDATION_PLAN` families. A compiled ruleset is another lowering target, content-addressed by the contract revision it came from. An invalidation plan is what tells you which derived decisions to recompute when a contract revision or a ruleset changes.

So the specialist layer is mostly a **compiler plus an evaluator contract** on top of what you have.

## 2. What the layer consists of

```
contract text ──LLM/LE──► Rule IR (per contract revision, content-addressed)
                              │
                     ┌────────┴────────┐
                     │  static checks  │  stratification, safety, NAF licence,
                     │                 │  temporal anchoring, priority acyclicity,
                     │                 │  DL/rule boundary
                     └────────┬────────┘
                              ▼
                    lowering planner (capability-driven, like the store SPI)
          ┌───────────────┬───────────────┬────────────────┐
          ▼               ▼               ▼                ▼
   SHACL/SPARQL     stratified plan   obligation        ingress
   (constitutive,   (derivations      lifecycle spec    validators
    stateless)       with NAF, aggs)  (params for FSM)  (admission)
          │               │               │                │
          └──────► evaluator reads positioned inputs ◄─────┘
                          │
                          ▼
             decision records (append-only, with provenance) ──► RDF
```

### Compile to plans, not to source code

Contracts are ingested continuously. You don't want to generate, build and deploy a binary for every insurance policy or loan agreement. So the lowering should produce a **plan artifact**: data describing a stratified relational program, a condition graph, or obligation parameters. A small, generic, well-tested runtime then executes that plan.

- **Soufflé-style codegen**, which compiles Datalog to C++ per program, only makes sense if profiling forces it.
- **Catala** compiles to OCaml, Python and C, but that suits legislation, which changes rarely. Contracts arrive daily.

This is the same principle as your normalization pipelines: *identified by implementation, not description*. A plan is identified by its digest. That identity includes the compiler version, not just the source rule text.

### Lowering targets by rule class

| Rule class | Example | Target | Runs where |
|---|---|---|---|
| Constitutive and stateless | eligibility, premium calculation | SHACL / SPARQL / SWRL, as today | your existing path |
| Derivations with negation and aggregation | "covered unless excluded, unless reinstated" | stratified Datalog plan | Rust evaluator (embedding Nemo, or your own over DBSP/differential dataflow) |
| Obligation lifecycles | "notify within 30 days of the loss; if late, explain the delay" | lifecycle *parameters*: trigger, deadline anchor, fulfilment condition, reparation | derived by the evaluator; timers and side effects in Erlang (§5) |
| Admission constraints | "a loss event must have a valid-time date and a policy reference" | compiled validators | ingress, at the edge, before the write |

The last row is the one place "before the data gets in" is genuinely right. It covers admission control, not reasoning.

**Defeasibility** doesn't need a separate engine. Acyclic priorities between rules compile into stratified negation: "r1 applies unless a higher-priority rule that conflicts with it applies." There is standard literature on translating defeasible logic into logic programs. So the evaluator stays stratified Datalog, and priority cycles become compile errors routed to a human.

## 3. Static checks: where the compiler earns its keep

Most of this layer's value comes from what the compiler **refuses** to compile. Six checks matter most:

1. **Stratification.** Reject any rule set with a cycle through negation. It usually indicates ambiguous contract wording or an extraction error.
2. **Safety.** Every variable in a rule must be bound by a positive atom.
3. **NAF licence.** This one is new, and it ties directly to your guide. A rule may use `not p(...)` only if the stream that supplies `p` is declared **authoritative** and **dense**. In your family-declaration style:

   ```yaml
   closed_world:
     - predicate: ex:ClaimNotification
       authoritative_source: urn:g:claims/{claimId}   # the only channel notifications arrive by
       requires: { ordering: PER_STREAM_DENSE, gap_audit: blocking }
   ```

   If notifications can also arrive by an unmodelled route (email into a mailroom system, for example), the compiler rejects the rule. Otherwise it would conclude "violated" from missing data. This check turns the open-world versus closed-world question from a philosophical problem into a declared, checkable property.
4. **Temporal anchoring.** Every deadline must reference a valid-time anchor event ("30 days from `loss.occurredAt`"), never "30 days from now."
5. **The DL/rule boundary.** OWL entailments flow up into rules. Rule-derived facts never flow back into DL reasoning (the layering from the previous answer). The compiler enforces this by keeping rule-derived predicates in a separate namespace or graph family that the DL reasoner never reads.
6. **Backend fit.** If a rule needs a feature the chosen target lacks (aggregation, well-founded semantics, incremental evaluation), compilation fails. This is the `min_level` principle again: never silently downgrade.

## 4. The evaluator contract

The core rule is that **evaluation is a pure function**:

```
derive(plan@digest, inputs@positions, ontologySnapshot@revision, evalTime) → conclusions
```

Four consequences follow:

- **Time is an input, never read from a clock.** Either `evalTime` is an explicit parameter recorded on the output, or, more elegantly, time is data: a dense "tick" stream (for example, business-day boundaries) that the evaluator consumes like any other stream. "Deadline passed" then becomes derivable from events at a position, so every past decision can be replayed exactly.
- **Evaluation identity is deterministic** (P0). The IRI is derived as `hash(enc([planDigest, positions..., ontologyRevision, evalTime]))`. Re-running an evaluation converges on the same record. Two workers racing produce one result, with no locking needed.
- **Conclusions are superseded, never mutated.** A backfilled notification with an earlier `occurredAt` produces a new determination at a later input position, which supersedes the old one. Both are kept. That matters in insurance: "we declined on day 45 based on what we knew, then reversed on day 47 when the broker's notice surfaced" is precisely the history a complaints handler or regulator will ask for.
- **The decision record carries its provenance:**

```turtle
<urn:decision:obst/Q2B7…>                         # IRI = hash of the evaluation inputs (P0)
    a norm:ObligationStateDetermination ;
    norm:obligation      <urn:ob:policy7/claim42/notify> ;
    norm:state           norm:Violated ;
    norm:sourceClause    <urn:contract:policy7/rev-9f3a/clause-9.2> ;
    norm:plan            <urn:plan:policy7/rev-9f3a/sha256-…> ;   # compiled ruleset + compiler version
    norm:ontologyRevision <urn:rev:ontology/e…3/…118> ;
    norm:input  [ norm:stream <urn:g:claims/42> ; pat:epoch "3"^^xsd:long ; pat:seq "17"^^xsd:long ] ,
                [ norm:stream <urn:g:ticks/business-day> ; pat:epoch "3"^^xsd:long ; pat:seq "812"^^xsd:long ] ;
    norm:justification   <urn:g:justification/Q2B7…> ;            # derivation tree, for "why?"
    fnd:supersededBy     <urn:decision:obst/K9Z1…> .              # if later evidence changed the answer
```

These records form an append-only family with a patch-log or snapshot receipt model. Your guide already requires that for decision records.

## 5. Where Erlang fits, and the trap to avoid

An obligation's lifecycle (pending → active → fulfilled, violated, or discharged, possibly followed by a reparation obligation) is a state machine with timers. That's your Erlang tier's home ground.

Use **one generic, parameterised `gen_statem`**, not generated Erlang per obligation. But be deliberate about which component is authoritative. Your guide's F4 finding (never keep two sources of truth for version state) applies directly:

- **The evaluator is authoritative** for normative state. It derives "violated."
- **The FSM is a projection plus a scheduler.** It arms timers for deadlines the evaluator has derived. When a timer fires, it publishes a tick or re-evaluation request rather than deciding anything itself. It also runs the side effects: notifying the broker, opening a claims-handler task, or starting a cure-period workflow.

If the FSM decides violations on its own, you'll eventually have an FSM saying "violated" and a derived record saying "fulfilled," with no principled way to tell which is right.

## 6. The main risk: two semantics drifting apart

Once rules run in both SHACL/SPARQL and a Datalog evaluator, they can disagree. Mitigate this the way you already handle stores:

- **One IR, many lowerings.** Never hand-write a rule for a single backend.
- **A rule-backend conformance suite**, the counterpart of your store TCK. It covers stratified negation cases, aggregation edge cases, the `xsd:long`/`xsd:integer` equality traps, timezone handling on deadlines, and backfill supersession. Every lowering target must pass it.
- **LE scenarios as differential tests.** The same scenario data runs through each lowering, and the answers must match.
- **QP4-style determinism tests** on plan compilation. The same IR must produce a byte-identical plan digest.

## 7. A first slice

Pick one obligation end to end: **claim notification within N days of the loss, with a reparation duty if late.** It exercises everything:

1. An LE template and rule, lowered to IR.
2. A NAF-licence declaration on the claims stream.
3. A business-day tick stream.
4. A stratified plan run by a small Rust evaluator over positioned inputs.
5. A determination record with provenance.
6. A backfill test: a late-arriving notification with an earlier `occurredAt` triggers supersession.
7. An Erlang FSM arming the deadline timer, and later triggering the reparation workflow.

If that slice comes out clean, you have a strong case for the tier. If the NAF-licence check keeps rejecting rules because your streams aren't authoritative for the facts contracts care about, that tells you something just as valuable: the gap is in data provenance at ingestion, not in the reasoning engine.
