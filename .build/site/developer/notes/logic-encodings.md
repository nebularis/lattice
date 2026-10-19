# Expressing Logics on the Wire: Datalog and the Alternatives

This follows on from the LegalRuleML mapping, the runtime pipeline and the wire protocol sketches. It covers three things: a cheaper fix for the "XML in a JSON string" problem, what Datalog can and cannot give you, and how the other logic families compare.

---

## Summary

1. **The XML-in-a-string problem has a cheap fix that keeps your LegalRuleML investment.** Normalised LegalRuleML/RuleML is a strict alternation of typed nodes and role edges, which maps deterministically to plain JSON. The missing RDF rule body is a small, known gap. SWRL's RDF syntax and the W3C *RIF in RDF* note both show how to fill it, and you only need to cover your own fragment.
2. **Datalog matches your semantics better than you fear, but only a specific dialect does.** The fit comes from encoding three-valuedness as two positive predicates, not from well-founded semantics. Under that encoding the whole Eligibility fragment compiles to **positive** Datalog. Negation is then needed only where your R2 closure licence already says it is needed. That correspondence is the strongest argument for Datalog.
3. **The recommendation:**
   - Use Datalog as the reference semantics of a JSON rule AST that extends your existing `conditions` form.
   - Keep LegalRuleML, RIF-Core, SWRL and ODRL as projections of fragments of that AST.
   - Reserve answer set programming (ASP) for the one thing Datalog cannot do, which is competing interpretations (G5).

---

## 1. First, the cheap fix for LegalRuleML

### 1.1 A JSON abstract syntax, not embedded XML

Normalised ("fully striped") LegalRuleML alternates *Node* elements (capitalised: `Rule`, `Atom`, `Obligation`) with *edge* elements (lower-case roles: `if`, `then`, `arg`, `hasTemplate`). That alternation is a JSON object model already:

| Normalised XML | JSON |
|---|---|
| Node element | object with a `kind` discriminator (no `@type`) |
| edge element | property name |
| repeated edges, or `@index` | array, order preserved |
| `@key` | `key` (document-local, per your §9) |
| `@keyref` | `ref` |
| `@iri` | `iri` (a string, not an IRI node) |

For example:

```json
{
  "kind": "PrescriptiveStatement", "key": "ps1",
  "rule": {
    "kind": "Rule", "strength": "defeasible",
    "if": { "kind": "And", "formulas": [
      { "kind": "Atom", "rel": "Risk", "args": [ { "var": "x" } ] },
      { "kind": "Neg", "formula": { "kind": "Atom", "rel": "within",
          "args": [ { "var": "x" }, { "ind": "FR-20R" } ] } }
    ] },
    "then": { "kind": "SuborderList", "items": [
      { "kind": "Permission", "bearer": { "ref": "coverholder" },
        "formula": { "kind": "Atom", "rel": "bind", "args": [ { "var": "x" } ] } }
    ] }
  }
}
```

This works well with your existing plans:

- It round-trips deterministically to normalised XML. Export and your Route B triplifier stay available: generate XML, then run the OASIS XSLTs.
- It is codegen-clean as a discriminated `oneOf` on `kind`, which OpenAPI 3.1 handles.

It also has one real cost. It is a faithful LegalRuleML skin, so it carries all of LegalRuleML's generality, including joins, `Naf`, deontic bodies and `Alternatives`. Your refiner still does all the refusing. That is acceptable for an *interchange* form. It is the wrong shape for your *default* form, which §5 addresses.

I'm not aware of a maintained normative JSON serialisation of RuleML. It is worth checking the RuleML wiki before you define your own.

### 1.2 Filling the missing RDF rule body

Two existing precedents show how:

- **SWRL's RDF concrete syntax.** It uses `swrl:Imp` with `swrl:body` and `swrl:head` as lists of `swrl:ClassAtom`, `swrl:IndividualPropertyAtom` and similar, with `swrl:Variable` nodes. You already have a SWRL backend, so this is partly known ground. It covers positive atoms only.
- **W3C "RIF in RDF" (Working Group Note, 2012).** This is a general mapping of RIF's XML abstract syntax to RDF, including `And`, `Or`, `Exists`, `Frame` and `Atom`.

Your importable fragment (mapping §7.3) is small: `Atom`, `Rel`, `Var`, `Ind`, `Data`, `And`, `Or`, `Neg`, licensed `Naf`, and range comparisons. A supplementary triplification of that fragment into a small internal vocabulary is a day or two of XSLT, sitting after `triplifyMerger-ids.xsl`. It never crosses the wire, so its aesthetics don't matter.

---

## 2. The yardstick: what semantics you actually need

Drawn from your three documents:

| # | Requirement | Source |
|---|---|---|
| S1 | Three outcomes, with Undetermined arising from **missing evidence**, not only from conflict | Eligibility L-laws, mapping §16.2 |
| S2 | Strong Kleene AND/OR, classical negation that preserves Undetermined | L15, L16, ADR-A103 |
| S3 | Absence decides only under a closure licence, otherwise refuse at compile time | R2, G6, G11 |
| S4 | Explicit, acyclic, sceptical priority, where incomparable conflict gives Undetermined | §9.4 Option B, N6, N7 |
| S5 | Compensation chains, where violation derives only from Permitted activation and Denied fulfilment | N3, N5 |
| S6 | Deadlines as positioned stimuli, never a wall clock | R3, N10 |
| S7 | Deterministic, order-independent, hashable results | pipeline §9 |
| S8 | Explanations, i.e. `because` and `needs` | wire §10 |
| S9 | Deterministic identity for derived nodes (violations, decisions) | ADR-A84, `DerivedHashIdentity` |
| S10 | Joins and aggregates available beyond the single-subject fragment, with a capability flag | mapping §4.2, the aggregate-cap example |
| S11 | Modality treated as data, not as a modal operator | §18.2 reifies modality as `ins:DeonticSpecification` |
| S12 | Competing interpretations, deferred | G5 |

S11 matters more than it looks. Because you reify modality as a qualifier, **you do not need a deontic logic.** You need a logic over data that happens to describe norms. That removes the main reason to reach for modal or deontic formalisms, and it favours Datalog.

---

## 3. Datalog, properly examined

### 3.1 Why the worry is reasonable

Plain Datalog, taken at face value, clashes with you in three ways:

- **Its minimal-model semantics is closed-world.** Anything not derived is false, which is the opposite of S1.
- **Its three-valued semantics answers a different question.** The well-founded semantics (WFS) gives three values, but its "undefined" arises from **cycles through negation**, not from missing evidence. Using WFS-undefined as your Undetermined would be exactly the conflation your §16.2 warns against.
- **Negation as failure is its normal mode of negation.** That is what R2 exists to prevent.

These problems come from the obvious encoding. They are not inherent to Datalog.

### 3.2 The encoding that fits: dual predicates

Represent each condition or profile outcome as two independently derived facts, `permitted(C, X)` and `denied(C, X)`. This is extended logic programming with strong negation, in Gelfond and Lifschitz's sense, equivalently Belnap's four values.

| Derived | Meaning |
|---|---|
| `permitted` only | Permitted |
| `denied` only | Denied |
| neither | **Undetermined**, the default when evidence is absent (S1) |
| both | **conflict**, a fourth value you get for free and can report as an integrity violation |

Strong Kleene combination under this encoding needs **no negation at all**:

```prolog
% AllRequired over named conditions c1..c3
permitted(p, X) :- permitted(c1, X), permitted(c2, X), permitted(c3, X).
denied(p, X)    :- denied(c1, X).
denied(p, X)    :- denied(c2, X).
denied(p, X)    :- denied(c3, X).

% AnySufficient is the dual.

% elg:negated swaps the two predicates and so preserves Undetermined (L16).
permitted(n, X) :- denied(c, X).
denied(n, X)    :- permitted(c, X).
```

Your running example, hierarchical match with exclusion, shows where negation does appear:

```prolog
% below/2 is the reflexive-transitive closure of the territory scheme's broader relation.
permitted(loc, X) :- riskLocation(X, L), below(L, fr),
                     not below(L, fr20r), not below(fr20r, L).
denied(loc, X)    :- riskLocation(X, L), below(L, fr20r).
denied(loc, X)    :- riskLocation(X, L), not below(L, fr), not below(fr, L).
```

The rules give the three outcomes you expect:

- **A risk located at `fr` itself.** `below(fr20r, fr)` holds, so neither rule fires. The result is Undetermined, which is your "above exclusion" case (L11).
- **A risk with no location at all.** Nothing fires, so the result is Undetermined, which corresponds to `exe:MissingCandidate`.
- **The negations.** Every one of them is over `below`, a **scheme** predicate. Your bound scheme edition is authoritative and complete by construction. In R2's terms, that is a closure declaration the vocabulary layer already implicitly holds.

**The finding:** under the dual encoding, the single-subject Eligibility fragment compiles to positive Datalog plus negation over closed predicates only. **R2 becomes a syntactic check:** `not p(...)` is admissible if and only if `p` is in a lower stratum *and* is either derived (an IDB predicate) or is an evidence (EDB) predicate covered by a closure declaration. That check is mechanical, compile-time and explainable. It is exactly the refusal `exe:NoClosureLicence` describes.

### 3.3 A probe this surfaces

Some of your existing set readings are negation in disguise:

- **`EveryValue` Permitted** means "every value of the path is Permitted". Concluding that requires knowing the value set is complete.
- **`SingleValue`** means "exactly one value". Counting requires the same knowledge.

Written in Datalog, both need negation or aggregation over an evidence predicate, and therefore a closure licence. Either L15's current definition already assumes the value set is closed, or these readings should cite a closure too. The translation makes the question impossible to miss. It is worth settling in A-105 rather than discovering it in a parity test.

### 3.4 Priority (S4), stratified

If you precompute the override closure, as your `PriorityPlan` already proposes, sceptical priority is stratified:

```prolog
% An inferior norm is blocked unless its superior is known to be inactive.
blocked(N, X) :- overrides(M, N), opposes(M, N), not inactive(M, X).
applies(N, X) :- activated(N, X), not blocked(N, X).
conflict(N, M, X) :- applies(N, X), applies(M, X), opposes(N, M).
```

The negation here is over **derived** predicates in a lower stratum, which is sound. That gives you the distinction to state in the ADR:

> NAF over derivations is sound in a complete stratified evaluation. NAF over evidence needs a closure licence.

Two further points:

- **Why `not inactive` rather than `activated`.** Under uncertainty about whether the superior applies, the inferior is withheld rather than applied. That is the sceptical reading. `conflict` then gives N7's `exe:IncomparablePriority`.
- **The general case.** Full defeasible logic (team defeat, defeaters, ambiguity propagation) has known translations into logic programs, from the Antoniou, Billington, Governatori and Maher line of work. The general translations are not always stratified. Starting with the simple explicit-superiority form above, which is essentially §9.4 Option B, keeps you inside stratified Datalog.

### 3.5 Compensation chains (S5) and time (S6)

```prolog
violated(N, X, P) :- activated(N, X), deadlinePassed(N, X, P),
                     not fulfilledBefore(N, X, P).        % evidence, so a closure licence is required
active(M, X)      :- violated(N, X, _), compensatedBy(N, M).
```

- **N5 holds structurally.** `activated` is the Permitted side of the activation profile, so an Undetermined activation derives nothing and cannot lead to a violation.
- **N3 (acyclicity) is exactly the condition for stratification** of this recursion through negation.
- **Time.** `P` is a stream position `(epoch, seq)`, not a timestamp. This is the *Dedalus* pattern (Alvaro, Hellerstein and others): Datalog with time as an explicit, totally ordered attribute, where state change is a rule over successor positions. It matches R3's positioned stimuli almost exactly. DatalogMTL, a metric temporal extension, exists if you ever need interval reasoning in the logic rather than in Behaviour.

### 3.6 Identity, aggregates and explanations (S7 to S10)

| Need | Datalog mechanism |
|---|---|
| determinism (S7) | intrinsic. The least fixpoint is order-independent, which is ideal for hashing |
| explanations (S8) | proof trees and why-provenance are well studied, and several engines can emit them. A proof tree of the dual predicates *is* your `because` structure. `needs` falls out of the rule whose missing premise blocked a `permitted` |
| derived identity (S9) | a restricted function symbol `h(N, X, P)` in rule heads, non-recursive so termination is kept, is exactly `DerivedHashIdentity` |
| joins and aggregates (S10) | native joins, plus stratified aggregation (sum, count, min, max). Aggregation over evidence needs a closure licence, which is correct: "total sum insured across the insured's policies" is meaningless without knowing you have all the policies |

### 3.7 Where Datalog genuinely does not match

| Gap | Why | Answer |
|---|---|---|
| competing interpretations (S12, G5) | Datalog has one model. Alternatives are several | ASP (§4) |
| unstratified defeasibility | general defeasible theories need WFS or stable models | keep priority explicit and precompiled |
| OWL/Surface backends | joins and aggregates exceed them | capability flags, per ADR-A24. The rules tier refuses on those backends |
| open-world OWL entailment in rule bodies | Datalog reads asserted and derived facts, not full DL entailment | OWL 2 RL is Datalog-implementable. Reading OWL 2 RL closure as EDB is the standard answer, and ADR-A83 keeps the reasoner out of evaluation anyway |
| deontic logic proper | none | not needed, per S11 |

**Verdict:** the dialect that fits is *stratified Datalog with strong (dual) negation, evidence-NAF only under closure licence, stratified aggregation, non-recursive hash-Skolem identity, and positions as time*. Your `rule-layers.md` already points at stratified Datalog. This makes it precise.

---

## 4. The other logic families, against the yardstick

| Option | What it is | Semantics fit | Encoding | Role for you |
|---|---|---|---|---|
| **RIF-Core / RIF-BLD** (W3C) | Horn rules designed to work alongside RDF and OWL, with a formal RDF+OWL compatibility spec | Datalog-like, positive. No negation in Core or BLD | XML. RIF in RDF (note) | an interchange **projection** of your positive fragment. Unlikely any client wants it |
| **SWRL** | OWL plus Horn rules, DL-safe | positive only, unary/binary atoms | RDF, OWL/XML | already a backend. Its RDF syntax is a template for internal rule bodies |
| **SHACL-AF rules / SHACL 1.2 rules** | triple and SPARQL rules attached to shapes. The W3C Data Shapes WG is working on rules for SHACL 1.2, reportedly Datalog-like with stratified negation (check its status) | depends on the final spec | Turtle | watch it. If it lands as stratified Datalog over RDF, it is a standard home for your internal rule graphs |
| **Notation3 (N3)** | rules as quoted graphs, with the EYE reasoner | scoped NAF, open-ended builtins | Turtle superset. Quoted graphs do not fit JSON-LD | not suitable for the wire |
| **Answer Set Programming** (clingo, DLV) | stable models, strong negation, choice, constraints | the dual encoding is native (`-p`). **Several answer sets correspond to competing interpretations** | text. JSON output only | the G5 engine, when G5 is built. Also useful at design time for "is this contract self-consistent under all readings" |
| **s(CASP)** | goal-directed ASP with **natural-language justifications**. Used by Blawx and as a Logical English target | as ASP | Prolog-like text | worth prototyping for R5 and `because` rendering |
| **Defeasible deontic logic / Formal Contract Logic** (Governatori), engines such as SPINdle and Turnip | the logic LegalRuleML was designed around. FCL's ⊗ operator is the suborder list | **closest semantic match** to LegalRuleML | engine-specific text or XML | a semantic reference and test oracle for N6 to N9, not a wire format |
| **Flora-2 / ErgoAI (Rulelog)** | higher-order logic programming with defeasibility via argumentation theories | very expressive, WFS-based | text | too powerful. Its undefined is WFS-undefined, so the §3.1 caveat applies |
| **Symboleo** | a contract specification language: obligations and powers with lifecycle states, over an event calculus | strong match for your Behaviour-side obligation *states* | text | design input for A-106, not a wire format |
| **ODRL 2.2** | W3C policy language: Duty, Permission, Prohibition, constraints, consequence, remedy | deontic-as-data (S11), and constraints match your single-subject fragment | **JSON-LD native**, and `@`-free with a good context | the natural *projection* of your `conditions` form. Consider making the Market Profile an ODRL-compatible profile, where a published context turns it into ODRL |
| **DMN decision tables + FEEL** (OMG) | decision tables with **hit policies**. FEEL booleans are **three-valued with `null`** (`false and null = false`, `true and null = null`) | a surprisingly good match for S1/S2 over the fragment. Hit policies are a fixed priority vocabulary | XML. FEEL expressions are **strings** | recreates the string problem. Borrow the hit-policy vocabulary and FEEL's null semantics as prior art |
| **Cedar** (AWS) | authorisation policies: permit/forbid, forbid overrides, formally analysed | fixed deny-overrides priority. Errors cause the policy to be **skipped**, a silent-absence hazard | **official JSON policy format** | precedent for a JSON AST of a logic with a formal semantics. Not your semantics |
| **Rego / OPA** | Datalog-derived, JSON-native policy language | closed-world, `default` keyword, NAF | text, plus a JSON AST | proof that Datalog-over-JSON is industrially acceptable, and a warning about defaults |
| **CEL** | expression language with a protobuf AST (JSON via the protobuf mapping). Partial evaluation with **unknowns**, and `&&`/`\|\|` absorb unknowns and errors | Kleene-like over expressions, no rules | AST as JSON | prior art for Undetermined in a mainstream expression engine |
| **JsonLogic** | tiny JSON expression AST | two-valued, no variables across rules | JSON | too weak, but shows the ergonomic target |

**The pattern:** everything that matches your semantics well has a text or XML syntax, and everything with a clean JSON syntax has weaker or different semantics. Cedar and CEL show the way out. **Pick the semantics, then define a JSON abstract syntax for it.** Don't adopt someone else's concrete syntax.

---

## 5. The proposal: one JSON rule AST, Datalog-defined

### 5.1 A strict superset of your `conditions` form

Your `conditions` form (wire §7) is already a Datalog-compilable AST over the single-subject fragment. Add a `rules` tier that introduces variables, joins and aggregates, sharing the same lift, the same refusals and the same term table:

```json
{
  "key": "aggregate-cap",
  "form": "rules",
  "dialect": "lattice-rules-0.1",
  "modality": "prohibition",
  "bearer": "coverholder",
  "activity": "bind",
  "activatedBy": {
    "let": { "i": { "read": "insured" } },
    "all": [
      { "aggregate": "sum",
        "over": { "var": "p", "read": "i.policies", "closure": "policy-register" },
        "of": "p.sumInsured", "as": "total" },
      { "read": "total", "atLeast": [ { "amount": 10000000, "unit": "GBP" } ] }
    ]
  }
}
```

It has these properties:

- **No `@` keys and no strings of logic.** Every node is a typed object, so codegen stays clean.
- **Variables appear only through `let` and `over`, and are always rooted in a path from the subject or another variable.** That keeps queries safe in the Datalog sense (every variable bound by a positive atom) and keeps explanations readable.
- **Closure is explicit and named.** `"closure": "policy-register"` names the closure declaration licensing the aggregate. Omitting it gives a submission-time refusal:

  ```json
  { "key": "aggregate-cap", "form": "rules", "lifted": "none", "decidable": false,
    "refusals": [ { "diagnostic": "noClosureLicence",
      "message": "Aggregating over insured.policies needs a closure declaration for the policy register." } ] }
  ```

- **Backend capability is surfaced.** The disposition says a term is decidable at runtime (SPARQL, Datalog) but excluded from OWL design-time checks:

  ```json
  "capabilities": { "runtime": true, "designTime": false }
  ```

  This is the declared non-capability pattern from ADR-A24, made visible on the wire.

### 5.2 The semantics is the translation

The ADR specifies:

- the translation from the AST to the dual-predicate Datalog dialect of §3;
- that Eligibility's L-laws and N1 to N10 become **property tests of the translation**, for example "for every `conditions` document, the Datalog outcome equals the existing evaluator's outcome".

That gives you a semantic reference with decades of theory behind it, without committing to a new runtime.

### 5.3 You do not need a new engine to start

Each stratum of a stratified program without recursion is a `CONSTRUCT` (or `INSERT`) run in stratum order. That is your existing SPARQL reference backend with a scheduler. Recursion is limited to scheme closure (property paths already handle it) and compensation chains (bounded by N3's acyclicity), so iterated `CONSTRUCT` to fixpoint is enough.

A dedicated engine becomes worth it only if volume demands. Candidates, whose current status you should check:

- **Soufflé:** C++, stratified negation, aggregates, provenance.
- **Nemo:** Rust, from TU Dresden, RDF input and output, existential rules.
- **RDFox:** commercial, incremental Datalog over RDF.

### 5.4 Interchange becomes projection

| Target | What projects | Losses |
|---|---|---|
| LegalRuleML (JSON AST ↔ normalised XML, §1.1) | everything in the fragment, plus modality, chains and overrides | evidence, read sets, closure licences, occupancy scoping |
| ODRL JSON-LD | `conditions` form plus modality and one-step consequence | multi-step chains, priority, aggregates |
| RIF-Core / SWRL | the positive dual-predicate rules | negation, aggregates |
| s(CASP) / ASP | the entire dialect, plus alternatives later | none, for reasoning |

Import runs the other way through the same refiner. A LegalRuleML statement in the fragment lifts into the rules AST, and anything outside it is refused, as in pipeline §6.

---

## 6. Decisions and probes this raises

| # | Question | Why it matters |
|---|---|---|
| D1 | Adopt dual-predicate Datalog as the **reference semantics** of the IR (an amendment to ADR-A89) rather than as a new backend? | makes the semantics precise without adding a runtime |
| D2 | Does L15 (`EveryValue`, `SingleValue`) implicitly assume a closed value set? (§3.3) | the translation forces a closure citation or an Undetermined |
| D3 | Is the "both derived" state a reportable integrity violation, or impossible by construction for well-formed profiles? | the fourth value is free. Decide whether to expose it |
| D4 | Sceptical priority under uncertainty: should an inferior norm be withheld when its superior's activation is Undetermined (§3.4)? | the conservative reading is proposed, and it should be a law, not an accident |
| D5 | Should the rules tier be JSON-only, with LegalRuleML JSON (§1.1) as a separate interchange form? Or should the LegalRuleML JSON skin *be* the rules tier? | the recommendation is to keep them separate: your AST is the fragment, LegalRuleML is the interchange |
| D6 | Should ASP be adopted for G5 when it is built, with the interpretation as the answer-set selector? | keeps Datalog stratified and puts the non-determinism where it belongs |

---

## 7. Claims to verify before relying on them

- whether a maintained JSON serialisation of RuleML exists;
- the status and exact semantics of rules in SHACL 1.2;
- the details of FEEL's three-valued `and`/`or` in the DMN version you would cite;
- the Cedar JSON policy format and its error semantics;
- CEL partial evaluation with unknowns (behaviour varies by implementation);
- the current maintenance status of Soufflé, Nemo, RDFox and s(CASP);
- whether the Antoniou/Governatori logic-program translations of defeasible logic are stratified for the explicit-superiority subset you would adopt. The simple encoding in §3.4 is, but verify that it matches the defeasible semantics you intend N7 to have.