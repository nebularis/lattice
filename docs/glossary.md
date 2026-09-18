<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The LATTICE Glossary

This document provides a glossary and explanation of the terminology used throughout this repo. A handful of words get reused with different semantics depending on which part of the repository you are in. 

**"Projection"** is the main offender — it means a session-type operation in SPC, a confirmed-mapping lookup in MORK, a per-layer directory of cross-layer contracts everywhere else, and (proposed, see ADR-A17) a third Surface subsystem for declarative mapping intent that needs graph construction, derivation, joins, or expansion, alongside Surface's existing Promotion and Index.

**"OperationalProfile"** is a close second: Quantification, Eligibility, and Behaviour each declare their own class of that name, independently, for the same general purpose (naming which implementation strategy answered a question) — they are not one shared class. Where this matters, the text below says so explicitly.

---

## Part I — A primer, for readers who haven't done this before

LATTICE is built entirely out of ideas from the semantic web — RDF, OWL, SHACL, SKOS. If those are already familiar, skip to Part II. If they're not, this part explains them the way LATTICE itself leans on them, which is a reasonably gentle way in.

### Graphs, not tables

Everything in this repository is, underneath, a **graph**: a set of small statements of the form *subject – predicate – object*, called **triples**. "This Obligation has an obligor, and the obligor is this RoleOccupancy" is one triple. A whole ontology, and every fact recorded against it, is just a large pile of these — millions of tiny three-part sentences, not rows in a table with a fixed set of columns. The consequence that matters most for everything that follows: nothing requires every subject to have the same set of predicates filled in. A `Subscription` and a `Contract` can each carry whatever properties actually apply to them, and a new property can be added to the world without altering the shape of anything that already exists. This is the single biggest structural difference from a relational database, and almost everything distinctive about how LATTICE is written traces back to it.

### Names that are addresses

Every subject, predicate, and object in that graph — every class, every property, every named individual — has a name that is also a URI: an **IRI**. `fnd:Version` is shorthand (a "prefixed name") for something like `https://www.nebularis.org/neuro-semantic/lattice/foundation#Version`. Using a real, resolvable-looking address as a name, rather than a bare word like `Version`, is what lets two organisations mint a term with the same short name and never collide — their full IRIs differ, because they live under different domains. LATTICE's own layers all favour **hash namespaces** (`...#Version`) over **slash namespaces** (`.../Version`), specifically so that every term in a layer can be resolved by fetching one document — the layer's whole ontology — rather than needing a separate network request per term.

### An ontology has two boxes (three, really)

An **ontology** is a formal vocabulary for a domain: the classes and properties that exist, and the rules governing how they may combine. Ontology engineers traditionally split this into a **T-box** (terminology — the classes and properties themselves, e.g. "an `Obligation` is a kind of `Element`") and an **A-box** (assertions — the actual individuals and facts stated using that vocabulary, e.g. "this particular obligation's obligor is that particular role occupancy"). MORK's documentation names a third, the **R-box** (relations — axioms specifically about how properties themselves behave, such as one property being the inverse of another), which is really a specialised corner of the T-box but useful to call out on its own when the thing you're mapping is a relationship rather than a class or an instance.

LATTICE's own repository layout mirrors this split directly: a layer's `spec/` directory holds its T-box, its (deliberately separate) `vocab/` directory holds the specific named individuals that populate the T-box's open enumerations, and worked instances of actual data live under `examples/` or a deployment's own graphs — a rough, useful mapping onto T-box / vocabulary / A-box.

### Classes, properties, individuals — and the open-world habit of mind

In OWL (the Web Ontology Language LATTICE is written in), a **class** is a category (`bhv:State`), a **property** relates two things (an object property relates two individuals; a datatype property relates an individual to a literal like a string or a date), and an **individual** is a specific thing belonging to one or more classes. What takes longer to get used to is OWL's **open-world assumption**: the absence of a statement is never treated as evidence that the statement is false. If the graph doesn't say a particular `RoleOccupancy` has an `occupiedBy` value, OWL does not conclude nobody occupies it — only that the graph, as currently written, doesn't say who does. This is exactly the right default for a graph that's built up incrementally from many sources over time, none of which can be assumed to have said everything there is to say. But it means a genuinely closed question — "is this `GovernanceState` one of exactly four values, no others" — cannot be answered by OWL classes alone; closing that question needs a different tool.

### Entailment: conclusions the graph didn't state outright

A **reasoner** can derive new triples from the ones actually asserted, following the ontology's own rules — this is called **entailment**. If `fnd:Evidence` is declared a subclass of `prov:Entity`, then anything typed as `fnd:Evidence` is *entailed* to also be a `prov:Entity`, whether or not that second triple was ever written down. LATTICE cares about this distinction sharply, because a design choice recurring across several layers is whether a mechanism's output should be **materialised** (the entailed triples are actually written into the graph, so no reasoner is needed to see them) or left as a **definition** that depends on a reasoner running under some named **entailment regime** (`NoEntailment`, `RDFSEntailment`, `OWL2ELEntailment`, `OWL2DLEntailment` — each admitting progressively richer, but more computationally expensive, inference). Neither choice is more "correct" than the other; they're just different bets about whether a reasoner will be present at query time.

### SHACL: where the closed questions go

**SHACL** (Shapes Constraint Language) is a validation layer, not an inference layer: a SHACL **shape** states a constraint — "every `Condition` must have exactly one `matchStrategy`" — and *validating* a graph against it produces a pass/fail-with-violations report, closed-world, right now, over the graph as it stands. This is deliberately the opposite temperament from OWL: where OWL politely declines to assume the graph is complete, SHACL is happy to say "this is missing" the moment it's missing. LATTICE's recurring pattern is to let OWL's T-box stay open (a `GovernanceState` individual could in principle be anything) and push the genuinely closed question — "no, actually, it's one of exactly these four named individuals" — into a SHACL shape using `sh:in`. The same split reappears as `shapes/structural.ttl` (ordinary per-instance property shapes) versus `shapes/constraints.ttl` (SPARQL-backed, whole-graph conditions that no single-node shape could express) versus, in some layers, `shapes/rules.ttl` (SHACL rules that *materialise* derived facts rather than merely check them — SHACL borrowing OWL's job for cases where computing the derived fact ahead of time is cheaper than reasoning it out every time).

### SKOS: vocabulary that doesn't want to be logic

**SKOS** (Simple Knowledge Organization System) is a W3C vocabulary for representing controlled lists, thesauri, and taxonomies — a **concept scheme** containing **concepts** related by loose, intentionally non-logical relations like `skos:broader` ("payroll tax" is broader than "withholding tax", without either being formally defined as a set). SKOS exists because most real vocabularies — job codes, peril types, jurisdiction lists — are editorial and evolving, not amenable to OWL's kind of rigorous class definition, and forcing them into OWL classes would be both wrong and brittle. LATTICE leans on SKOS specifically for exactly this kind of externally governed, domain-specific vocabulary, and builds its own governance machinery (see `voc:ConceptScheme`, Part III) as a wrapper *around* SKOS rather than a replacement for it.

### Punning: one name, two hats

Because everything is a graph, and because a graph can make a statement about anything with a name, OWL allows the unusual move of using the same IRI both as a class or property (playing its normal role in the T-box) and, in a different triple, as an individual — an ordinary subject or object that other triples point at. This is called **punning**. LATTICE uses it specifically so that one layer can *refer to* a class or property declared in a completely different layer — pointing at it, describing it, constraining it — without formally `owl:imports`-ing that other layer's ontology. Vocabulary's `voc:constrainsProperty` (which points at an `rdf:Property` defined anywhere) and Surface's whole mechanism (which names carriers and read-path properties belonging to other layers without importing them) both depend on this trick. The tradeoff: some OWL tooling refuses to accept a single IRI wearing two hats at once, which is why a handful of mechanisms in this repository offer an alternative "wrapped" mode that puts a separate, plain individual next to the class instead of punning it.

### Disjointness: keeping composable pieces from collapsing into each other

An `owl:disjointWith` axiom states that nothing may ever be classified as both of two classes at once. LATTICE uses this constantly, and for a specific reason beyond ordinary error-catching: several layers are built from small, deliberately *composable* mixin classes (see Foundation, Part III) that a domain class can adopt freely in combination — but each mixin has a companion "value" class it points at (a `Governable` thing points at a `GovernanceState`), and without an explicit disjointness axiom between the mixin and its own value class, nothing would stop an individual from accidentally being classified as both the role and the thing the role points at. Disjointness, here, is less about catching mistakes and more about making a composable architecture safe to compose.

### Versioning and identity: an edit versus a new thing

A recurring problem: how do you say "this is the same Obligation, just edited" rather than "this is an unrelated Obligation that happens to look similar"? The generic answer, used throughout LATTICE, is to split the two roles into separate classes — a **persistent identity** for the thing that survives across edits, and a **version** for each individual edited state, linked back to that one identity. Direct succession between versions is recorded as a single, non-transitive hop ("this version supersedes that one") rather than a maintained running total, so that finding the latest version in a chain means following that hop repeatedly rather than trusting a cached answer. This pattern is native to Foundation and gets reused, unmodified, by essentially every layer above it.

---

## Part II — The shape of LATTICE

### Three projects, one picture

The repository actually holds three related but separable pieces of work, and the name "LATTICE" strictly refers to only the middle one.

**MORK** ("Mapping Ontological & Representational Knowledge") is a general-purpose vocabulary and pipeline for getting messy source material — database schemas, API payloads, free-text clauses — aligned onto a formal target ontology. **LATTICE** is the semantic substrate that alignment lands in: a stack of domain-neutral ontology layers that give governing instruments (contracts, policies, protocols) a shared, queryable shape. **SPC** ("Subject-oriented Process Calculus") is a formal model of session-typed orchestration between agents — a way of giving a live exchange between parties (human, AI, or computational) a checkable protocol to follow. SPC ships a substantial ontology of its own but is not yet wired into the layers below it — it still uses a placeholder namespace rather than the shared LATTICE namespace scheme, and integrating it is explicitly future work rather than an oversight.

The three read, in one sentence each: MORK gets messy things *in*; LATTICE gives them a *shape* once they're in; SPC governs the *live exchange* between the agents that act on that shape.

### Layers, and why they only ever point one way

LATTICE itself is not one ontology but several, called **layers**, each its own independent OWL/SHACL/SKOS module. The layers are strictly ordered, and the rule governing that order is simple to state and easy to underestimate the importance of: **a lower layer never names a term belonging to a higher one.** Foundation knows nothing of Party; Party knows nothing of Instrument. Where a higher layer genuinely needs to compose with a lower one — Instrument needing to say who is obligated, Behaviour needing to say what changes when a transition fires — the *higher* layer declares that composition, from its own side, typically in a `projection/` directory reserved for exactly this. Nothing about the lower layer's own specification ever has to change to make that composition possible.

This discipline is what makes the whole stack checkable by machine rather than by convention: with a single, agreed order, an automated import-closure check has one unambiguous thing to verify, and — just as importantly — it's what lets Foundation, Vocabulary, and Quantification stay genuinely domain-neutral. Nothing in their own specifications can ever be forced to know what industry is consuming them, because nothing above them is allowed to leak downward.

The settled order is:

```
foundation
    └── vocabulary
            └── quantification
                    └── party
                            ├── eligibility
                            │       └── instrument
                            └── behaviour
```

**Surface** sits slightly apart from this chain: it imports Foundation, Vocabulary, and Quantification, but nothing above imports it back, and it reaches the *other* layers' terms by punning rather than by import — it can be introduced to, or removed from, a deployment without any other layer's own specification changing at all. **MORK** and **SPC** sit outside the chain entirely; MORK can target any layer as a mapping destination, and SPC — as already noted — is not yet connected to any of it.

### The anatomy of a layer

Every layer follows the same internal template, in whole or in the parts it actually needs, and knowing the template is most of what's needed to navigate any of them cold:

- **`spec/`** — the normative T-box: the classes, properties, and cardinality restrictions, in Turtle.
- **`shapes/`** — SHACL validation, itself conventionally split into `structural.ttl` (ordinary per-instance property shapes), `constraints.ttl` (SPARQL-backed whole-graph conditions a single-node shape can't express), and, where a layer needs it, `rules.ttl` (SHACL rules that materialise derived facts rather than merely checking them).
- **`vocab/`** — mechanism-intrinsic enumerations *only* — the specific named individuals an open T-box class needs (a `GovernanceState`'s `Draft`/`Reviewed`/`Active`/`Superseded`) — and never business or domain vocabulary. That distinction is a hard line the whole framework depends on to stay domain-neutral.
- **`projection/`** — the layer's own declared contracts to and from other layers; this is where upward composition actually lives, per the layering rule above.
- **`execution/`** — generated runtime artefacts, for layers that produce any, plus the documentation governing when and how they're regenerated.
- **`examples/`** — worked instances scoped to that one layer.
- **`test/`** — the layer's own shape and rule tests.

### Literate specification: the document is the source, not a description of it

Every layer's `README.md` is not prose written *about* the ontology; it is the ontology's authoring surface. Fenced code blocks inside the README — tagged `turtle-spec`, `turtle-vocab`, `turtle-shapes` — are mechanically extracted, in document order, into the actual `spec/`, `vocab/`, and `shapes/` files a tool or reasoner would load. A separate `turtle-example` tag marks illustrative snippets that are deliberately *never* extracted, so a README can show a worked case without that case leaking into the compiled ontology. Because the prose *between* those blocks is explaining code that's about to be extracted verbatim, and each declared term carries its own explanatory annotations (`rdfs:comment` for a one-line formal definition, and a repository-specific `fnd:utility` annotation for the longer explanation of what a term is for), an ordinary edit to a term's definition and an edit to the document's prose about that term are much harder to let drift apart than they would be if the two lived in separate files maintained by hand. A small drift-checking tool (`tools/literate_extract.py`) exists specifically to catch the cases where they drift anyway.

### Conformance levels: not one gate, but a ladder

"Does this graph conform to LATTICE" is not a single yes-or-no question, and treating it as one produces a false failure every time a graph is correctly, legitimately mid-way through being built up. LATTICE instead recognises an eight-rung ladder, **L0 through L7**, each rung naming a distinct stage of trust a graph can sit at, indefinitely, without needing to reach a higher one:

| Level | Name | Needed for |
|---|---|---|
| L0 | RDF ingestible | Storage and discovery |
| L1 | Mapped / mapping-pending | MORK-style integration |
| L2 | Semantically classified | Exploratory query |
| L3 | Declaration-conformant | Declaration-level governance |
| L4 | Analysis-ready | Candidate detection, gap analysis |
| L5 | Operationally evaluable | Eligibility decisions |
| L6 | Authoritative execution-ready | Behaviour's authoritative execution |
| L7 | Projection-conformant | Integration with an external system |

A graph freshly ingested and awaiting mapping sits happily at L0 or L1 — that is not brokenness, it's the graph being exactly as far along as it actually is. Because the levels aren't one monolithic check, LATTICE organises its SHACL shapes *by* level rather than as one shape graph, and an L2 fixture failing an L6-level shape is expected, not a defect to be fixed. **L7** deserves its own note, because it's easy to over-read: a surface or projection reaching L7 does not raise the conformance level of whatever it was built from — "surfaces accelerate; they do not admit." A projection is never itself the evidence cited by an admissibility decision or an execution record; those always cite the underlying declaration.

### Realisation-strategy neutrality: the definition doesn't care how you answer it

A second cross-cutting rule, easy to violate by accident when writing a specification: what a mechanism *means* must never depend on how a particular deployment happens to evaluate it. Whether an admissibility question is answered by live SPARQL, by SHACL validation, by a reasoner, by a pre-computed materialised graph, by an external projection, or by a bespoke compiled evaluator is a deployment choice, not a fact about the mechanism's semantics — and a specification that reads as though compilation were mandatory for a mechanism to be usable at all has quietly smuggled an implementation detail into a definition. Concretely, this shows up as a **realisation mode** wherever a layer generates content: `DefinitionOnly` (axioms are emitted, and a reasoner running under some declared entailment regime is what makes them visible) versus `Materialised` (the entailed assertions are written out directly, and no reasoner is needed). Both are first-class; neither is a fallback path toward the other. Several layers name specific, tested combinations of "which strategy, for which mechanism" as **operational profiles** — Eligibility's E1 through E6, Behaviour's B-P1 and onward — which is also exactly why "OperationalProfile" recurs as an independently-declared class name in more than one layer: each layer is tracking its *own* certified strategy combinations, not sharing one global list.

### Derived artefacts versus authored facts

Not everything in a LATTICE graph was put there by a person asserting it. Some of it is *derived*: computed, compiled, materialised, or indexed from something else that was authored. Telling the two apart matters, because a derived thing can be safely regenerated or discarded — an authored fact cannot be, without losing information nobody else recorded. A derived artefact accordingly self-declares an **authority** it may claim, capped well below "authoritative": `Advisory` (informative only) or `CachedReproducible` (trustworthy specifically *because* it's provably reproducible from its source, and only for as long as that stays true) — never higher, because a derived thing outranking the declaration it was computed from would invert the whole relationship. Four genuinely different questions get asked about a derived artefact, and LATTICE is careful not to let one hash try to answer all of them: has the *meaning* of the source declaration changed (a **semantic content hash**); would two different tools, correctly configured, have produced an interchangeable result (a **generation** or **profile identity**); is this exact file byte-identical to what regenerating it right now would produce (a **build artefact hash**); and can a specific replay of a computation be trusted (a **runtime state hash**). Collapsing these into a single "hash changed, therefore invalidate everything" check throws away distinctions a real deployment needs — extending a declaration with a dimension nobody's using yet, for instance, shouldn't have to bust every cache downstream of it.

### Governance, and how disagreements between documents get resolved

**Governance** is the checking that has to run over the *union* of every layer's graph at once, because no single layer can see both sides of a cross-layer relationship on its own — whether a `voc:SchemeContract` some layer declared has actually been satisfied by a bound scheme in the right governance state; whether a generated index still matches the source it was built from; whether a deprecated term is quietly still in use somewhere. This is why governance is deliberately not folded into any one layer's own `shapes/` directory. As of this writing the `governance/` directory itself is largely scaffolding — the checks it's meant to run are described in the architecture decision records rather than implemented yet — but the role it's reserved for is real and load-bearing: it's the thing that would eventually make a claim like "this surface is still fresh" or "this scheme contract is satisfied" actually checkable, rather than merely asserted.

Because a repository this layered inevitably accumulates documents that describe the same decision from different angles — and occasionally disagree — there's a settled order of authority for resolving that: **Architecture Decision Records outrank layer READMEs, which outrank `docs/GOVERNANCE.md` and `docs/architecture/`, which outrank informal design notes and worked-example commentary.** An ADR is where a cross-cutting decision (a new layer, a new cross-cutting rule, a resolved ambiguity in the dependency order) gets recorded once it's actually settled, and the `docs/adr/` index is the place to check what's been decided and why.

---

## Part III — The substrate, one layer at a time

What follows walks the dependency chain from the bottom, because each layer genuinely only makes sense once its foundations are in view.

### Foundation — the four capabilities nothing else can do without

Foundation is the bedrock every other layer builds on, and its central design decision is to *not* be one thing. An earlier draft offered a single `Governed` superclass carrying every capability a domain class might want — identity, evidence, temporal scoping, governance status — all at once, and it was rejected precisely because adopting any one of those capabilities would have forced adopting all four. What Foundation offers instead is four small, independent **mixins**, each freely combinable with the others, each adoptable on its own: `fnd:Version` (this individual is a specific, identified state of some persistent thing), `fnd:Evidenced` (this individual can carry evidence for why it holds), `fnd:TemporallyScoped` (this individual has a period during which it's valid, distinct from when anyone happened to record that), and `fnd:Governable` (this individual moves through a review lifecycle before it's trusted). Each mixin has a companion class holding the actual data it points at — `fnd:PersistentIdentity`, `fnd:Evidence`, `fnd:TemporalScope`, `fnd:GovernanceState` respectively — and each mixin is explicitly disjoint from its own companion, so the role and the thing the role points at can never be conflated.

A few of Foundation's specific choices are worth understanding on their own, because they recur as patterns throughout the rest of the repository. **Evidence** is modelled as a real graph node (aligned with the external PROV-O provenance vocabulary) that must support at least one thing and carries its own recording timestamp — deliberately kept separate from *validity* time, because when a fact was recorded and when it was actually true are different questions with different answers. Having *no* evidence yet is treated as an entirely normal starting state, not an error — a fact can be true before anyone has written down why. **Temporal scoping** deliberately stays simple: rather than modelling time itself as structured individuals (the way the W3C's OWL-Time vocabulary does), a validity period is just a start and an optional end, expressed as plain literals — a considered, reversible trade of temporal-reasoning power for everyday simplicity. And **governance state** is left as a bare current value — `Draft`, `Reviewed`, `Active`, `Superseded` — with no built-in notion of a state *machine* governing how one moves to another. That's a genuinely deliberate omission: Foundation gives you the noun, and leaves the verb — the transitions, triggers, and guards around that value — to a layer built for exactly that job. It's a pattern that reappears almost verbatim in Party (a role occupancy is a bare fact, with no opinion about what causes an actor to start or stop occupying it) and again in Behaviour (a guard can only read, never write — see below).

*Terms introduced here:* `fnd:Version`, `fnd:PersistentIdentity`, `fnd:Evidenced`, `fnd:Evidence`, `fnd:TemporallyScoped`, `fnd:TemporalScope`, `fnd:Governable`, `fnd:GovernanceState`, `fnd:hasIdentity`/`fnd:hasVersion`, `fnd:supersededBy`, `fnd:hasEvidence`/`fnd:supports`, `fnd:recordedAt`, `fnd:hasTemporalScope`, `fnd:validFrom`/`fnd:validTo`, `fnd:hasGovernanceState`, `fnd:utility` (the annotation property carrying each term's longer explanation).

### Vocabulary — binding an outside word list without ever naming it

Vocabulary solves one narrow, recurring problem: some property, declared in some other layer, genuinely needs to take its values from an external, domain-specific, editorially-governed list — peril codes, jurisdictions, currencies — but nothing about that other layer's own specification should ever have to name, or even know about, that particular list. The mechanism is a deliberate two-class split. A `voc:SchemeContract` is a purely *structural* declaration — "this property must eventually be bound to some scheme meeting these criteria" — that says nothing whatsoever about what the scheme is actually *about*; that part is left entirely to prose and to whichever domain ontology owns the constrained property. A `voc:ConceptScheme` is the other half: a governed, versioned wrapper around an ordinary SKOS `skos:ConceptScheme`, adding exactly the identity and review-lifecycle machinery Foundation already provides everywhere else. The two are connected by a property (`voc:boundScheme`) that starts out deliberately unset — an unbound contract is the normal starting state, not a mistake — and can be filled in later, by a completely different party, once an actual scheme exists to satisfy it. This is what lets a contract be authored months before the vocabulary it will eventually govern is even chosen: declaration and binding are two independent acts, and the whole point of splitting them is that neither one has to wait for the other.

*Terms introduced here:* `voc:ConceptScheme`, `voc:SchemeContract`, `voc:constrainsProperty`, `voc:requiresGovernanceState`, `voc:boundScheme`.

### Quantification — one mechanism for everything that can be ordered, bounded, or repeated

Quantification is the layer that gives every other layer a shared, principled way to talk about magnitude, order, and repetition — deliberately named after the *mechanism*, not after any one kind of value it might hold, because a layer named "Quantity" would either exclude grades and tiers or admit them under a name that misdescribes what it actually is. Its central object is the **value space**: a declared, ordered set with a stated density (are its members discrete, like integers, or dense, like real numbers) and a stated, explicit list of which operations are actually permitted over it. That last point is asserted repeatedly throughout the layer's own design notes because it's easy to get backwards: holding numeric-looking literals never, by itself, grants permission to do arithmetic on them. Whether a space may be compared, summed, differenced, or averaged is a separate, explicit declaration — "can I average these grades" is meant to be a question the graph can answer before anyone runs the calculation, not a plausible-looking number nobody checked.

A handful of Quantification's own distinctions are worth carrying forward, because they resolve confusions that would otherwise surface everywhere above it. A **position** (a point on an ordered space) and an **extent** (a magnitude or duration along it) are treated as two genuinely separate declared spaces, not two readings of one space — because a position minus a position is meaningful (it yields an extent), an extent plus an extent is meaningful (it yields another extent), but a position plus a position is not meaningful at all, and keeping the two spaces separate makes that nonsensical combination structurally unwritable rather than merely discouraged. This is also *why* temporal modelling (positions in time, intervals, recurring schedules) doesn't need its own peer layer: a moment in time is simply a position on a totally-ordered, unit-bearing space, and a recurring schedule is simply a generator of canonically identified ranges over it — Quantification already has everything that needs. A second distinction: **granularity** and **unresolvedness** can both produce an "I can't answer that" result, but for different reasons that need different remedies — a value known only to the month *is* known, just not to arbitrary precision, whereas a genuinely unresolved value's required content is missing, disputed, or pending, and conflating the two (an earlier draft of this layer did) loses information a consumer actually needs. A third: comparing whether one range **overlaps** another is not the same question as whether one range **contains** another, and a range semantics that only guarantees soundness for the meet of two ranges (screening) must not be mistaken for one that guarantees both soundness and completeness (exact) — using the weaker one where the stronger one is required silently produces wrong answers rather than an error.

Quantification also gives the rest of the framework its shared idea of a **recurrence** — a deterministic generator of stable, independently reproducible bins over time or any other extent space, built so that two separately running processes will always agree on which bin a given position falls into — and a shared, declared **ordering basis** for breaking ties deterministically when two things would otherwise sort equally (two events sharing a timestamp, for instance), rather than leaving the tie-break to whatever a database's insertion order happens to produce.

*Terms introduced here:* `qnt:ValueSpace`, `qnt:Value` (and its three disjoint kinds: `qnt:Quantity`, `qnt:OrdinalValue`, `qnt:UnresolvedValue`), `qnt:Bound`, `qnt:Range`, `qnt:CyclicRange`, `qnt:RangeSet`, `qnt:AnchorBinding`, `qnt:UnitContract`, `qnt:Unit`/`qnt:UnitFamily`, `qnt:Conversion`, `qnt:ConversionFunction`, `qnt:ConversionContext`, `qnt:OperationCapability`, `qnt:OperationOperand`, `qnt:Recurrence`/`qnt:RecurrenceBin`, `qnt:OrderingBasis`/`qnt:OrderingComponent`, `qnt:Comparison`, `qnt:OperationalProfile`/`qnt:OperationRequest`, `qnt:Law`/`qnt:LawDischarge` (semantic, static, and runtime-conformance registers).

### Surface — restating what's already true, so it's cheaper to ask about

Surface is a mechanism layer rather than a substrate layer in the ordinary sense: it sits low in the dependency order (importing only Foundation, Vocabulary, and Quantification) but nothing above it imports it back, because it doesn't add meaning to the graph at all — it only *restates* meaning that's already there, in a form that's cheaper to query. The problem it answers: a declaration graph states what's true, but answering a particular question against it sometimes means traversing relations that are expensive, remote, or governed somewhere else entirely — and doing that traversal live, every time, at query time, isn't always practical. Surface declares exactly two operations for restating part of a graph locally, and only two. **Promotion** restates a value that's reachable from some subject by a multi-hop chain of relations (a *read path*) as a single, direct property on that subject — turning "follow the plan, then the pricing, then the currency" into one property read. **Indexing** restates a value asserted of many subjects as a symbol those subjects can be retrieved *by* — turning "which of these belong to Engineering, or anything under it" into a type check instead of a graph traversal.

The reason Surface bothers to distinguish these carefully, and to record so much bookkeeping about each one, ties straight back to Part II's distinction between derived artefacts and authored facts. An index is unconditionally safe: it always mints brand-new terms of its own, so adding one entails nothing new about anything else, and removing one loses no fact anyone actually authored — that conservativity, not the speed gain, is what licenses treating a generated index as freely disposable, regenerable cache. A promotion is the one case where that safety isn't automatic, because the property it restates a value onto might belong to Surface's own generated namespace, or might be a property some other, consuming layer already declared — and in that second case, the resulting triples are genuinely indistinguishable from facts someone authored by hand. Surface handles this by recording, on every surface it generates, which of the two situations it's in (its **signature scope**), and by a hard rule: a promotion reaching into another layer's authored vocabulary must preserve the source value's exact meaning and must be written out directly rather than left as a bare definition — a promotion that's lossy, or reached through anything weaker than an exact correspondence, is not permitted to land on an authored property at all. Every surface, in turn, is required to record what it actually read to produce itself — one entry per source, each carrying a content hash — so that staleness becomes a simple comparison ("does any recorded hash still match what's actually there now") rather than a question anyone has to reason about by hand.

Surface also gives Eligibility's `HierarchicalMatch` (see below) a second way to answer the same question: a hierarchy's closure can be computed live, by traversing `skos:broader` at query time, or it can be answered against a Surface-generated closure index instead — both are valid, as long as they agree, which is exactly the realisation-strategy neutrality principle from Part II showing up concretely. And MORK (Part IV) can *propose* a Surface contract as part of a mapping — recording, in its own vocabulary, that a mapping suggests a lookup surface be generated, and letting a compiled surface be lifted back into that same record for review before it's promoted to a governed contract.

A third operation, **Projection**, is proposed (ADR-A17) alongside Promotion and Index, for intent that neither restatement form covers — constructing new graph structure, deriving a value, joining across carriers, or expanding one relation into several. Unlike Promotion and Index, which can emit their generated artefact directly, a `srf:ProjectionContract` lowers into MORK's mapping graph (ADR-A18) rather than emitting SHACL, SPARQL, or SWRL itself — MORK stays the machine-facing mapping graph, and Surface stays the authoring surface. Projection gets its own law register (ADR-A20), distinct from Promotion and Index's X1–X6, though a Projection stacked over a Promotion or Index still composes under the same signature-scope rule (ADR-A21).

*Terms introduced here:* `srf:SurfaceContract` (`srf:PromotionContract`, `srf:IndexContract`, and proposed `srf:ProjectionContract`), carrier, read path, `srf:PathStep`, `srf:ValuePopulation` (and its kinds), `srf:SurfaceProfile`, index forms (`NominalClass`, `MembershipAssertion`, `ClosureRelation`, `DirectProperty`), `srf:GeneratedSurface`/`srf:GeneratedSymbol`/`srf:ReadSetEntry`, `srf:signatureScope`, `srf:derivationAuthority` (`Advisory`, `CachedReproducible`).

### Party — who is standing in which capacity, and how obligation flows between them

Party answers a narrow, mechanical question, and deliberately nothing else: who is participating, in what capacity, for how long, and how does responsibility divide or transfer between participants — never *what* the obligation actually is, which stays one layer up, in Instrument. Its central move is to never connect an actor directly to a role. Instead, every occupancy of a role is its own separate, timestamped, evidenced individual — a `pty:RoleOccupancy` — which is precisely what allows a role to exist in a design from the very start while genuinely nobody occupies it yet: the occupancy's role is required, but the actor filling it is optional, left unset until some later event fills it in. If the occupant ever changes, that isn't an edit to the existing occupancy — Party mints a new one, sharing the old one's persistent identity, linked forward by supersession, exactly the way Foundation's versioning works everywhere else.

Two further mechanisms sit on top of that one idea. A **participation group** lets several role occupancies share responsibility for one obligation under a declared **composition rule** — the same underlying machinery (a group, its members, each member's individually recorded share) expresses both "everyone is capped independently at their own share" and "any one member can be called for the full amount, with a right of recourse against the others"; only the named composition rule differs. A **delegation** is a separate, narrower idea: it records that one occupancy is *performing* what a different occupancy remains *accountable* for, without ever transferring the accountability itself — a sponsor stays answerable even while a contract research organisation does the actual work. Deliberately, delegation carries no property describing what scope that performance is limited to; whether a particular act falls within scope is a question for Eligibility to answer, one layer up, the same way a lower layer never carries logic that properly belongs to a layer built for it. And, matching a discipline that shows up throughout this repository, Party never references anything from the layers above it — no property pointing back at "the instrument this occupancy belongs to." Instrument points down at Party; Party never points up.

*Terms introduced here:* `pty:Actor`, `pty:Role`, `pty:RoleOccupancy`, `pty:ParticipationGroup`, `pty:CompositionRule`, `pty:GroupMembership`, `pty:Delegation`.

### Eligibility — a small, closed algebra for a three-valued answer

Eligibility exists to turn a declared admissibility question into one of exactly three answers — **Permitted**, **Denied**, or **Undetermined** — and it's built as a genuinely small, closed algebra rather than an open-ended rules engine. At the bottom sit atomic **conditions**: exact-value matches, set-membership tests, interval containment, hierarchical matches against a governed concept scheme, and wildcards. Every condition, regardless of which of those it is, separately declares three independent things — which **match strategy** it uses, which **compatibility operation** combines it with sibling conditions (require all, require any, or require dimension-by-dimension consistency), and which **wildcard policy** governs it — because these are three genuinely orthogonal axes, not properties baked into a condition's subtype. Conditions compose into a reusable, versioned **admission profile**; a profile is evaluated against one or more **questions**, each carrying the actual candidate value being checked; and the outcome is a recorded, evidenced **eligibility decision**.

The layer is conspicuously conservative about which strategies it's willing to admit at all, and that conservatism is itself worth understanding as a design stance: interval *overlap* is explicitly excluded as an admissibility strategy (only interval *containment* is admitted, because overlap's semantics are subtler than they look — two ranges can each overlap a third separately while having no three-way intersection at all), and hierarchical matching is admitted only under a formally pinned-down definition: a candidate satisfies a hierarchically-matched condition exactly when it stands in the reflexive-transitive closure of the bound scheme's ordering relation, restricted to that scheme's own members — and a scheme whose ordering relation contains a cycle simply isn't evaluable under this strategy at all, rather than producing an undefined or looping answer. That closure can be computed by live traversal or answered from a generated Surface index (Part III, above) — Eligibility doesn't care which, as long as the two agree.

*Terms introduced here:* `elg:Condition` (and its subtypes `ExactCondition`, `SetMembershipCondition`, `IntervalCondition`, `WildcardCondition`), `elg:AdmissionProfile`, `elg:Question`, `elg:EligibilityDecision`, `elg:MatchStrategy`, `elg:CompatibilityOperation`, `elg:WildcardSemantics`, `elg:Decision` (`Permitted`/`Denied`/`Undetermined`).

### Behaviour — state, and the strict line between reading it and changing it

Behaviour is a state-machine layer, stacked on top of Eligibility (to gate transitions) and Instrument and Party (to actually change something), organised into four tiers that are worth keeping distinct in your head: **declaration** (the rules themselves — states, transitions, triggers, guards, effects, allowances), **occurrence** (an actual observed event that might cause something to fire), **execution** (an evidenced record that a declared transition genuinely fired, or that a declared effect was genuinely applied), and **state record** (the durable, current answer to "what state is this subject actually in right now", and "how much of this allowance is left").

The single most important structural decision in the whole layer is the strict separation between a **guard** and an **effect**, and it's worth dwelling on because it's a recurring shape in this repository, not a one-off. A guard is purely a read: its only substantive property points into Eligibility, asking whether a transition is admissible, and nothing in the guard's own vocabulary is even capable of describing a write — there is no property path from "evaluate this guard" to "change something," because the classes a guard can point at and the classes an effect can point at are kept structurally disjoint. An effect, conversely, is the write side — it targets an element in Instrument, a role occupancy in Party, or a balance in Behaviour's own allowance ledger — and every transition is required to declare at least one. The consequence: a failed or undetermined guard cannot partially mutate anything, because the mechanism that reads eligibility has no vocabulary for mutation at all to begin with, and a write only becomes possible once a transition has already passed whatever guards it declares. This is the same underlying instinct Foundation showed by refusing to bundle a lifecycle machine onto `GovernanceState`, and Party showed by never letting a role occupancy reach upward — here it shows up as "make the wrong kind of action literally unwritable in the model," rather than merely discouraged by convention.

Behaviour is also unusually candid about what it deliberately hasn't finished. `Sequential` absorption — consuming an allowance directly against its balance — is real and usable today; `Proportional` absorption, and the exact edge-case behaviour of an allowance resetting partway through a consumption, are both declared in the vocabulary and explicitly, deliberately left unusable, pending formal conservation laws and cross-profile test coverage that don't exist yet. The layer would rather ship an inert, clearly-marked placeholder than let unproven behaviour be inferred from a declaration that looks complete but isn't.

*Terms introduced here:* `bhv:StateSpace`/`bhv:State`, `bhv:TransitionDefinition`, `bhv:TriggerDefinition`, `bhv:GuardDefinition`, `bhv:EffectDefinition`, `bhv:AllowanceDefinition`, `bhv:SelectionPolicy`/`bhv:ActivationPolicy`, `bhv:Stimulus`, `bhv:TransitionExecution`/`bhv:EffectApplication`, `bhv:StateOccupancy`, `bhv:AllowanceAccount`, `bhv:AbsorptionPolicy` (`Sequential`, and the deferred `Proportional`).

### Instrument — the generic shape of a governing document

Instrument is the shallowest layer in the substrate, deliberately: it exists to give "a governing document" — a contract, a policy, a statute, any structured agreement — its most generic possible shape, without committing to what any particular document actually says. Everything hangs off one root class, `Element`, of which every other Instrument class is a disjoint kind: a **provision** is a structural grouping (a clause, a section); an **obligation** is a duty living inside a provision, requiring at least one party who owes it and at least one party who's owed it (reaching straight into Party's role occupancies for both); and a **qualifier** is a constraint or refinement that can attach to any element at all, including another qualifier. Nothing here is business content — Instrument borrows Party for *who*, Eligibility for *under what condition*, and Quantification for *how much or by when*, and its own vocabulary stays confined to the structural skeleton those pieces hang on. A different applied domain ontology could in principle sit alongside or even replace Instrument, composing with the same Party, Eligibility, and Behaviour mechanisms through its own `projection/` contracts, without touching any of those lower layers at all — which is exactly the kind of substitution the layering discipline in Part II exists to make possible.

*Terms introduced here:* `ins:Element`, `ins:Provision`, `ins:Obligation`, `ins:Qualifier`.

---

## Part IV — MORK: bringing the outside in

MORK's job is to take source material that was never written with any ontology in mind — a database schema, an API response, a clause of free text — and align it onto a target ontology's vocabulary, doing as much of that work deterministically as it possibly can, and asking an AI model to *propose* an answer only for the residue that's genuinely still ambiguous. Every proposed correspondence becomes a first-class graph object, a **data mapping**, rather than an opaque script — which is what lets mappings be queried, composed, scored, and audited back to whatever evidence justified them, instead of disappearing into a one-off transformation nobody can inspect afterwards.

MORK's own internal layering deliberately separates three things that change at different speeds. An **intent** captures what a piece of source text or data actually *means*, described only in terms of natural language, SKOS concepts, and datatypes — never in terms of the target ontology's own classes and properties — specifically so that a later refactor of the target ontology doesn't invalidate the intent it was built from. A **mapping** is the ontological alignment proper: intent, matched to a specific class or property. And a **generative mapping** is a mapping whose evaluation actually produces a compiled artefact — a SHACL shape, a SWRL rule, an RML/R2RML triples map for structured data transformation, or (the newest addition, and the one that connects directly back to Surface in Part III) a **projection mapping**, which records a lookup-surface class definition that a Surface-style compiler minted for it. Keeping "what it means" and "how it compiles" as genuinely separate tiers is the same underlying discipline as Part II's realisation-strategy neutrality, applied to the mapping problem specifically: a mapping's meaning shouldn't be tangled up with which artefact format happens to realise it.

Underneath the mapping vocabulary sits a fairly serious piece of applied mathematics, described narratively in MORK's own documentation as an evolving "tri-stratum inference engine." The cheapest, always-available stratum is straightforward lexical and type matching. The second stratum leans on **Formal Concept Analysis** — a classical, fully deterministic technique from lattice theory for turning a table of *objects* and the *attributes* they share into a hierarchy of "formal concepts" (a maximal group of objects, paired with the maximal set of attributes they all share) that always forms a well-behaved lattice. MORK uses this (or an equivalent graph-community-detection pass) to notice that certain source fields habitually co-occur — an attachment point, a limit, and a share appearing together, say — and to treat "recognising one member of that group" as evidence for inferring the rest, without any model having to be asked about each field individually. The third stratum is simply **lookup**: once a mapping has been confirmed once, in a prior run, the same correspondence is retrieved rather than re-derived. As confirmed mappings and discovered co-occurrence groups accumulate, this third stratum handles a growing share of the total work, and the explicit design goal is that the system needs *less* AI assistance the longer it's been run against a given domain, not more.

*Terms introduced here:* `mrk:DataMapping`, `mrk:GenerativeMapping` (`ShapeMapping`, `RuleMapping`, `TransformMapping`, `ProjectionMapping`), intent node, formal concept analysis, community, projection (MORK's sense — a confirmed prior mapping, retrieved rather than re-derived; see the warning at the top of this document about the word's other senses).

---

## Part V — SPC: giving a live exchange a protocol to follow

Where Behaviour (Part III) models what state something is in and what can cause it to change, SPC is concerned with the live conversation between the agents driving those changes — and it gives that conversation a formal contract to check itself against, rather than an ad hoc protocol assembled by convention. The central idea it's built from is the **session type**, borrowed from formal methods for communicating systems: an ordinary type describes a value ("this is an integer"), but a session type describes a *conversation* — the order in which a participant will send and receive messages, including its branching and its recursion, before the conversation ends. In the multiparty flavour SPC models, a single **global type** describes an entire choreography — who sends what to whom, in what order, across every participant at once — and each individual participant's **local type** is obtained by *projecting* that global choreography down onto just their own point of view, discarding everything they can't see. (This is SPC's own, third sense of the word "projection" — see the warning at the top of this document.) A participant that behaves exactly according to its own local type, across a whole system built this way, is meant to be guaranteed free of certain classes of miscommunication by construction, rather than by testing.

SPC also formally reifies the actual runtime state of such a system as a **configuration** — which subject is doing what, which messages are currently in flight, who's currently externally visible — and evolves that configuration one step at a time through recorded **reduction steps**, in deliberate lockstep with a parallel notion of the *global type itself* evolving as the choreography is consumed. The property that ties the two together — that a well-typed configuration, once it takes a step, lands on another well-typed configuration — is the standard type-theoretic guarantee called **subject reduction**, and SPC's own documentation is candid that OWL alone cannot fully enforce it (nor several of its sibling correctness properties, like the duality between a send-type and its matching receive-type); those are explicitly flagged as needing an external validator or a hand-written rule rather than pretending OWL can check them unaided.

SPC has a substantial ontology already authored, but — as noted in Part II — it isn't integrated with the rest of this repository yet: it still uses a provisional, placeholder namespace rather than LATTICE's shared one, and no `projection/` contract connects it to Behaviour or to any layer below. It's best read, for now, as a serious, separate body of work rather than another rung on the dependency ladder.

*Terms introduced here:* session type, global type / local type, `spc:Behavior`, `spc:Configuration`, `spc:ReductionStep`, `spc:ProjectionAssertion` (SPC's own sense of "projection"), subject reduction.

---

## Part VI — Applied domains and worked examples

Everything in Parts III through V is deliberately domain-neutral: nothing in it should require knowing what industry or use case is actually consuming it. Two separate places in the repository exist specifically to test that neutrality by putting real domain content on top of it, and they answer two different questions.

`examples/` holds small, single- or cross-layer worked instances — an employment scenario, a lending covenant, a SaaS subscription, a clinical trial — built across genuinely unrelated domains on purpose, precisely so that no one mechanism can be accidentally shaped around the assumptions of just one of them. `applied/` is a newer, different thing: a home for entire ported domain ontologies, at whatever level of maturity they've reached, each following the same internal layer template described in Part II. The first of these is an insurance contract-structure ontology, staged there while it's being hand-ported and reconciled with the substrate beneath it — a reminder that "applied to a domain" and "already composed with Party, Eligibility, and Behaviour through a declared `projection/` contract" are two different milestones, and a domain can sit under `applied/` having reached only the first one.

---

## Appendix — Alphabetical index

A quick-reference index, grouped by namespace prefix, of every term introduced above. Each entry is a pointer back into the narrative, not a substitute for it — follow the part heading for the reasoning behind the term, not just its name.

### `fnd:` — Foundation
- **Evidence** — a discrete, evidenced item supporting some other fact; see Part III, Foundation.
- **Evidenced** — mixin: can carry evidence.
- **GovernanceState** — the current review-lifecycle status of a `Governable` thing (bare value, no lifecycle machinery).
- **Governable** — mixin: moves through a review lifecycle.
- **PersistentIdentity** — the stable identifier shared by all versions of one thing.
- **TemporalScope** — a validity period (start, optional end).
- **TemporallyScoped** — mixin: has a validity period distinct from recording time.
- **utility** — the annotation property carrying a term's fuller "what it's for" explanation, alongside `rdfs:comment`'s one-line definition.
- **Version** — mixin: this individual is a specific, identified state of some persistent thing.

### `voc:` — Vocabulary
- **boundScheme** — the concrete scheme, if any, satisfying a `SchemeContract`.
- **ConceptScheme** — a governed, versioned wrapper around a `skos:ConceptScheme`.
- **constrainsProperty** — names the property a `SchemeContract` governs.
- **requiresGovernanceState** — the governance state(s) a bound scheme must hold.
- **SchemeContract** — a structural requirement binding some property to a scheme meeting stated criteria, without naming what the scheme is about.

### `qnt:` — Quantification
- **AnchorBinding** — a range's bounds, kept derived from a stated anchor and offset rather than only their computed endpoints.
- **Bound** — a single open-or-closed limit on one value space.
- **Comparison** — a recorded result of comparing values under a stated profile.
- **Conversion** / **ConversionFunction** / **ConversionContext** — a declared unit transformation, its registered function (if non-linear), and the evidenced context a contextual conversion needs.
- **CyclicRange** — a bounded region on a cyclic space, expressed as start-plus-extent rather than lower/upper endpoints.
- **Law** / **LawDischarge** — a stated obligation, and evidence discharging it (semantic, static, or runtime-conformance).
- **OperationCapability** / **OperationOperand** — a declared permission and signature for an operation over a value space.
- **OperationalProfile** / **OperationRequest** — (Quantification's own class of this name; see the warning at the top of this document) the implementation strategy that evaluated an operation, and a recorded request to apply one.
- **OrderingBasis** / **OrderingComponent** — a declared, deterministic tie-break ordering.
- **Quantity** / **OrdinalValue** / **UnresolvedValue** — the three disjoint kinds of `Value`: a literal magnitude, a value from an ordered scheme, and a value whose content isn't currently available.
- **Range** / **RangeSet** — a bounded region of a non-cyclic space, and a union of such regions.
- **Recurrence** / **RecurrenceBin** — a deterministic generator of stable, reproducible bins, and one bin it produces.
- **Unit** / **UnitFamily** / **UnitContract** — a measure designation, a group of mutually-convertible units, and the governance contract over them.
- **ValueSpace** — an ordered set with declared density and declared permitted operations.

### `srf:` — Surface
- **carrier** — the class or entity type a surface contract is about.
- **DerivedArtefact** family (`GeneratedSurface`, `GeneratedSymbol`, `ReadSetEntry`) — the recorded provenance of one generation run: what was produced, from what inputs, under what profile.
- **derivationAuthority** — how far a generated surface may be trusted (`Advisory` or `CachedReproducible`, never higher).
- **IndexContract** — a surface contract restating a carrier's values as retrievable symbols.
- **index forms** (`NominalClass`, `MembershipAssertion`, `ClosureRelation`, `DirectProperty`) — the concrete shapes an index can take.
- **PathStep** — one positioned hop in a multi-hop read path.
- **ProjectionContract** (proposed, ADR-A17) — a surface contract for mapping intent that needs graph construction, derivation, joins, or expansion, lowered into MORK rather than emitted directly.
- **PromotionContract** — a surface contract restating a reachable value as a direct assertion on the carrier.
- **read path** — the chain of relations from a carrier to the value being restated.
- **signatureScope** — whether a generated surface stays within its own minted terms, or reaches an authored property in another layer.
- **SurfaceContract** — the declaration that a relationship reachable from a carrier may be restated locally.
- **SurfaceProfile** — the declared generation configuration (naming, symbol mode, entailment regime, stack depth) a surface is produced under.
- **ValuePopulation** — the declared set of values a per-value index form mints symbols for.

### `pty:` — Party
- **Actor** — a real-world party capable of occupying a role.
- **CompositionRule** — how members' shares relate to a shared obligation (e.g. independently capped, or joint-and-several).
- **Delegation** — the record that one occupancy performs what another remains accountable for.
- **GroupMembership** — the reified fact of one occupancy participating in one group, carrying that participation's share.
- **ParticipationGroup** — a set of role occupancies sharing responsibility under a composition rule.
- **Role** — a capacity a role occupancy fills, independent of who fills it.
- **RoleOccupancy** — the reified, evidenced, time-scoped fact of one actor occupying one role — occupant optional, role required.

### `elg:` — Eligibility
- **AdmissionProfile** — a reusable, versioned bundle of composed conditions.
- **CompatibilityOperation** — how multiple conditions combine into one outcome.
- **Condition** (and its subtypes `ExactCondition`, `SetMembershipCondition`, `IntervalCondition`, `WildcardCondition`) — a declared admissibility condition.
- **Decision** — the three-valued outcome vocabulary: `Permitted`, `Denied`, `Undetermined`.
- **EligibilityDecision** — the recorded, evidenced outcome of evaluating a profile against one or more questions.
- **MatchStrategy** — how a candidate value is compared against a condition (exact, set-membership, interval, hierarchical, wildcard).
- **Question** — an evaluation question posed against exactly one condition.
- **WildcardSemantics** — the policy governing wildcard use across a condition's dimensions.

### `bhv:` — Behaviour
- **AbsorptionPolicy** — how consumption is applied against an allowance (`Sequential`, usable now; `Proportional`, declared but deferred).
- **AllowanceAccount** / **AllowanceDefinition** — the runtime balance record, and the declared quota rule it tracks.
- **EffectDefinition** / **EffectApplication** — a declared cross-layer write instruction, and the evidenced record that it was actually applied.
- **GuardDefinition** — a declared, read-only precondition on a transition, reading Eligibility and never writing anything.
- **SelectionPolicy** / **ActivationPolicy** — how to choose among several matching transitions, and when a chosen one actually takes effect.
- **State** / **StateSpace** — a declared position in a machine, and the space of states it belongs to.
- **StateOccupancy** — a durable record of which state a subject actually (or hypothetically) occupies.
- **Stimulus** — an observed, evidenced event that can cause a trigger to fire.
- **TransitionDefinition** — a declared rule for moving from one state to another, bundling its triggers, guard(s), and effects.
- **TransitionExecution** — the evidenced record that a declared transition actually fired.
- **TriggerDefinition** — a declared condition that can cause a transition to fire.

### `ins:` — Instrument
- **Element** — the root class of every Instrument-layer thing; a versioned artefact.
- **Obligation** — a duty within a provision, requiring at least one obligor and one obligee.
- **Provision** — a structural grouping of obligations.
- **Qualifier** — a constraint or refinement attached to any element.

### `mrk:` — MORK
- **DataMapping** — a graph node asserting a correspondence between a source element and a target ontology element.
- **GenerativeMapping** (`ShapeMapping`, `RuleMapping`, `TransformMapping`, `ProjectionMapping`) — a mapping whose evaluation produces a compiled artefact.
- **intent** — what a piece of source material means, described without reference to any target ontology term.
- **MappingScheme** — the SKOS scheme container grouping a set of data mappings.

### `spc:` — SPC
- **Behavior** — a subject's local process grammar (send, receive, choice, recursion, call).
- **Configuration** — the reified runtime state of a whole system of subjects.
- **GlobalType** / **LocalType** — a full choreography, and one participant's projected view of it.
- **ProjectionAssertion** — the record that projecting a global type onto one participant yields a stated local type (SPC's own sense of "projection").
- **ReductionStep** — one recorded step of a configuration evolving.
