📋 **HISTORICAL REFERENCE** — This document is retained as part of the decision analysis record.

**Status:** Analysis document (2026-09-18), referenced by ADR-A21 for X6 signature scope decision context.

**Note:** This is historical reference material and is not part of the active documentation migration.

---

# X6 decision analysis — signature scope, promoted properties, and projecting into FBO

## What decision is actually on the table

The live Surface design already distinguishes two kinds of promotion:

1. **Local-signature promotion**
   - Surface mints its own property in its own namespace.
   - The output is visibly generated.
   - This stays conservative in the strong sense.

2. **Source-signature promotion**
   - Surface writes to a property that another layer already declares.
   - In your current example, that means writing to something like `fbo:hasLineOfBusiness`.
   - The output is convenient for consumers, but it is no longer visibly separate from authored A-box.

X6 exists to constrain the second case rather than banning it.

---

## The two consequences in plain English

### 1. A lossy promotion may not target an authored property

This is the rule that says:

- if the promoted value is only an approximation, derivation, heuristic, or inexact crosswalk,
- then Surface must **not** write it onto a property the domain already owns,
- because after emission it would look like a normal authored fact.

### What “lossy” really means

A promotion is lossy when the generated value is not guaranteed to preserve the exact meaning of the source value.

Typical cases:
- a broader-category crosswalk
- a many-to-one mapping that throws away distinctions
- a derived label or bucket
- a promotion that crossed an inexact mapping relation

#### Example
Suppose the source graph says:

- `cso:RetailPropertyPackage` is in scope
- a crosswalk maps that to `fbo:Property`

If that crosswalk is only approximate, then writing:

- `ex:termApp1 fbo:hasLineOfBusiness fbo:Property`

would make the result look like an authored FBO fact. A downstream consumer would have no way to tell whether FBO was asserting `Property`, or whether Surface inferred it by flattening a more specific CSO notion.

So under X6, Surface would instead have to write something visibly generated, for example:

- `ex:termApp1 srfgen:projectedLineOfBusiness fbo:Property`

or another property in the contract's own generated namespace.

That preserves the ability to query the projected value, but avoids pretending the result is native FBO truth.

### Why this consequence exists

Without it, the system quietly upgrades a weak or approximate mapping into a first-class domain fact.
That would blur three things that should remain distinct:

- authored facts
- exact restatements
- approximations or derived summaries

This is mostly a governance and semantics problem, not a syntax problem.

---

### 2. A definition-only promotion may not place an authored property-chain axiom onto an authored property

This is the rule that says:

- if the output is `DefinitionOnly`, Surface is not emitting asserted facts
- it is emitting axioms that allow a reasoner to infer facts
- if those axioms conclude an authored property, then Surface has changed what follows in the authored signature

In plain language, this means Surface would no longer be “just a cache” or “just an acceleration layer”. It would be extending the meaning-bearing theory of the authored model.

### What “definition-only” means here

A definition-only surface does not say:

- `ex:termApp1 fbo:hasLineOfBusiness fbo:Marine`

Instead it says something like:

- if a term application has some chain of relations to a value,
- then a reasoner may infer `fbo:hasLineOfBusiness`.

That is often encoded using an OWL property chain, rule, or another definitional mechanism.

#### Concrete intuition
If Surface emits a property chain like:

- `cso:hasPerilScope o someCrosswalk o ... -> fbo:hasLineOfBusiness`

then every graph loaded with those axioms now has **new FBO facts entailed over the FBO signature**, even when no explicit FBO assertion was authored.

That is stronger than materialising a generated cache. It changes what the combined theory says about FBO itself.

### Why this consequence exists

A materialised source-signature promotion is already a controlled compromise. It emits authored-signature-looking assertions, but at least those assertions are explicitly generated artefacts, separately tracked, separately invalidated, and separately removable.

A definition-only source-signature promotion is harder to contain:

- the result appears by inference rather than by explicit generated assertion
- it is easier for downstream users to miss that the fact is generated
- it weakens the idea that Surface is optional and discardable
- it makes conservativity fail at the level of entailment, not just at the level of emitted triples

That is why X6 says source-signature promotion must be `Materialised`, not `DefinitionOnly`.

---

## What this means for projecting into FBO

The short version is:

**X6 does not remove your ability to project into FBO.**
It preserves that ability, but only under stricter conditions.

You can still project into FBO when all of the following hold:

1. the target property really is an FBO-authored property
2. the promoted value is exact, or exact modulo a declared exact crosswalk
3. the projection is materialised as generated assertions
4. the generated surface is recorded as `SourceSignature`
5. the surface remains authority-capped and separately invalidatable

That is exactly the design route that protects your FBO use case.

### So what would you lose if you keep X6

You would lose only these two things:

1. the ability to write approximate or lossy projections directly onto authored FBO properties
2. the ability to define authored FBO properties by inference rules or property chains coming from Surface

If your FBO port depends mainly on exact restatement for queryability, X6 does **not** block it.
If your FBO port depends on approximate normalization being written as if it were native FBO truth, X6 blocks that deliberately.

---

## Why this does not fit naturally into MORK

Your instinct is reasonable. This does **not** fit naturally into MORK in the same way.

### Why MORK is not the natural home

MORK is primarily about:

- alignment
- mapping intent
- source-to-target correspondence
- proposal, validation, and provenance of mapping decisions

Surface is about:

- deterministic restatement
- generated acceleration artefacts
- freshness and invalidation
- query-time convenience over an already governed graph

Those are different jobs.

### The practical distinction

If MORK says:

- “source field X corresponds to ontology concept Y”

that is a mapping/alignment claim.

If Surface says:

- “given an already accepted graph, copy this reachable value onto this subject for lookup efficiency”

that is not really a mapping claim. It is a controlled projection or cache over a graph whose semantics were already accepted elsewhere.

### Why forcing this into MORK is awkward

If you move source-signature projection entirely into MORK, then MORK would have to own concerns that currently belong to Surface:

- read-set capture
- stale-surface invalidation
- materialised vs definition-only realisation
- signature-scope classification
- local naming policies
- estate-wide regeneration under profile changes

Those are not impossible to add to MORK, but they are not especially natural there. They are compiler and derivative-artefact concerns more than mapping concerns.

### Where MORK *does* fit well

MORK fits well when the issue is:

- “is this correspondence exact or inexact?”
- “what crosswalk relation was used?”
- “what evidence supports targeting FBO property P?”

So MORK is a good upstream source of fidelity claims and crosswalk provenance.
Surface is still the more natural home for the actual deterministic projection mechanism.

---

## The trade-off, stated directly

### Option A — keep X6 in Surface

#### Benefits
- You keep the ability to project into FBO.
- Exact restatements onto FBO properties remain allowed.
- Approximate results remain visibly generated instead of masquerading as authored facts.
- Surface remains the home of invalidation, regeneration, and runtime lookup optimisation.
- MORK stays focused on mapping rather than cache mechanics.

#### Costs
- Surface is no longer purely conservative in the strongest sense.
- You need users to understand `SourceSignature` as a special case.
- Some promotions you may want for convenience must target generated properties instead of authored FBO ones.
- You must materialise source-signature promotions rather than define them axiomatically.

### Option B — move source-signature projection out of Surface and into MORK or another mapping tier

#### Benefits
- Surface becomes cleaner and more purely conservative.
- Authored-signature restatement is no longer Surface's problem.
- The line between generated cache and authored ontology stays sharper.

#### Costs
- You lose a simple, governed way to restate exact reachable values directly into FBO for consumers.
- You push derivative-artefact concerns into MORK that do not sit there naturally.
- The FBO dimension-sourcing use case becomes more awkward operationally.
- You risk splitting one practical workflow across two mechanisms: MORK for mapping semantics, Surface for every other acceleration shape.

---

## Use cases

### Use case 1 — exact FBO projection from accepted domain facts

**Scenario**
A term application already carries an exact chain that determines one line of business, and the business wants a direct FBO predicate for query convenience.

**Example outcome**
Surface materialises:
- `ex:termApp1 fbo:hasLineOfBusiness fbo:Marine`

**Assessment**
Allowed under X6.
This is probably the core case you want to preserve.

### Use case 2 — approximate crosswalk into FBO

**Scenario**
A source code system maps imperfectly into FBO. Several source values collapse into one FBO class.

**Example outcome wanted**
- `ex:termApp1 fbo:hasLineOfBusiness fbo:Property`

**Assessment**
Blocked under X6 if the mapping is inexact.
Recommended alternative:
- emit a generated property in the surface namespace
- or keep the approximate relation in MORK/crosswalk artefacts and require downstream consumers to opt into it explicitly

### Use case 3 — reasoner-based projection to avoid materialised writes

**Scenario**
You want to avoid storing projected FBO assertions and instead let a property chain derive them.

**Assessment**
Blocked for source-signature targets.
Allowed only if the promoted property is in the generated namespace, not the authored FBO namespace.

### Use case 4 — internal analytics property, not authored FBO

**Scenario**
You want a convenient projection for internal reporting, but the property does not need to look native to FBO.

**Example outcome**
- `ex:termApp1 surfbo:projectedLineOfBusiness fbo:Marine`

**Assessment**
Safe, flexible, and compatible with lossy derivations.
This is the escape hatch when exactness is not available.

---

## Decision guidance

If your primary goal is:

- **preserve direct projection into FBO for exact cases**
- **avoid forcing projection machinery into MORK**
- **keep approximations visibly separate from authored truth**

then the strongest current choice is:

## Recommended direction

**Keep X6 in Surface.**

More precisely:

- keep `SourceSignature` promotions
- allow them only for `ExactSource` and `CrosswalkExact`
- require them to be `Materialised`
- require separate provenance, invalidation, and authority capping
- require lossy or heuristic outputs to land on generated properties instead

That keeps your FBO projection path open while preventing the most dangerous semantic blur.

---

## A possible refinement if you want a narrower rule

If X6 feels too broad, a narrower formulation would be:

- exact and crosswalk-exact promotions may target authored properties, but only as materialised generated assertions
- lossy promotions may never target authored properties
- definition-only promotion may target only generated properties, never authored properties

This is very close to the current intent, but stated as an operational policy rather than a single compact law sentence.

---

## Questions to settle before final sign-off

1. In the FBO port, which promoted properties are truly exact?
2. Do any required FBO projections depend on heuristic or many-to-one crosswalks?
3. Do consumers need those projections to look like native FBO facts, or is a generated namespace acceptable?
4. Is there any real deployment need for definition-only source-signature promotion, or is materialisation acceptable everywhere this matters?
5. Should MORK supply the fidelity evidence while Surface remains the mechanism of projection?

---

## Bottom line

X6 is not really an anti-FBO rule.
It is an anti-ambiguity rule.

It says:

- exact restatement into FBO is allowed
- approximate restatement into FBO must not masquerade as authored truth
- inferential restatement into FBO from Surface must not silently change the authored theory

That is why it preserves the useful part of the FBO projection story without making Surface indistinguishable from ontology authoring.
