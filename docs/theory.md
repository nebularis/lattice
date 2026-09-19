---
layout: none
title: Theoretical Foundations — LATTICE
---
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Theoretical Foundations — LATTICE</title>
  <meta name="description" content="The mathematics underneath LATTICE: description logic, order theory, conservative extension, three-valued logic, category theory, session types, and determinism — and why each one is there.">
  <style>
    :root {
      color-scheme: dark;
      --bg: #05070d;
      --panel: #101a2d;
      --panel-2: #14223a;
      --text: #f4f7ff;
      --muted: #bdc8da;
      --soft: #8d9bb2;
      --line: #2a3a56;
      --mint: #9df7d7;
      --blue: #9bbcff;
      --purple: #d4a8ff;
      --amber: #f3cf8e;
      --max: 1120px;
    }
    * { box-sizing: border-box; }
    html { background: var(--bg) !important; }
    body {
      margin: 0 !important;
      min-width: 320px;
      background: var(--bg) !important;
      color: var(--text) !important;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.7;
    }
    a { color: var(--mint); }
    a:hover { color: #fff; }
    .topbar {
      position: sticky; top: 0; z-index: 5;
      border-bottom: 1px solid var(--line);
      background: rgba(5, 7, 13, .96);
      backdrop-filter: blur(18px);
    }
    .topbar-inner, .book { width: min(calc(100% - 2rem), var(--max)); margin: 0 auto; }
    .topbar-inner { min-height: 4rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
    .brand { color: var(--text); font-weight: 850; letter-spacing: .08em; text-decoration: none; }
    .back { color: var(--muted); text-decoration: none; font-size: .92rem; }
    .book { padding: 3.6rem 0 6rem; }
    .hero { padding-bottom: 3rem; border-bottom: 1px solid var(--line); }
    .eyebrow { color: var(--mint); font-size: .78rem; font-weight: 850; letter-spacing: .14em; text-transform: uppercase; }
    h1, h2, h3, h4 { line-height: 1.15; }
    h1 { max-width: 900px; margin: .7rem 0 1rem; font-size: clamp(2.6rem, 7vw, 5.6rem); letter-spacing: -.06em; background: linear-gradient(120deg, #fff, var(--mint) 42%, var(--blue) 78%, var(--purple)); -webkit-background-clip: text; background-clip: text; color: transparent; }
    h2 { margin: 4rem 0 1rem; padding-top: 1rem; border-top: 1px solid var(--line); color: var(--text); font-size: 2.1rem; }
    h3 { margin-top: 2.2rem; color: var(--mint); font-size: 1.25rem; }
    h4 { margin-top: 1.4rem; color: var(--blue); font-size: 1rem; }
    p, li, td { color: var(--muted); }
    .dek { max-width: 800px; font-size: 1.2rem; }
    .small { color: var(--soft); font-size: .92rem; }
    .toc { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: .7rem; margin: 2rem 0 3rem; }
    .toc a { padding: .8rem 1rem; border: 1px solid var(--line); border-radius: 12px; background: var(--panel); text-decoration: none; display: block; }
    .callout { margin: 1.4rem 0; padding: 1rem 1.2rem; border: 1px solid #386052; border-radius: 12px; background: #102a2a; color: var(--muted); }
    .callout strong { color: var(--text); }
    .callout.quote { border-color: #3a3a5a; background: #12122a; font-style: italic; }
    .callout.quote strong { color: var(--purple); font-style: normal; }
    pre { overflow-x: auto; padding: 1.1rem 1.2rem; border: 1px solid var(--line); border-radius: 12px; background: #07101d; color: #dbe8ff; }
    code { color: #dbe8ff; }
    :not(pre) > code { background: #0d1728; padding: .1rem .4rem; border-radius: 6px; }
    table { width: 100%; margin: 1.2rem 0; border: 1px solid var(--line); border-spacing: 0; border-radius: 12px; overflow: hidden; background: var(--panel); }
    th, td { padding: .75rem .85rem; text-align: left; vertical-align: top; border-bottom: 1px solid var(--line); }
    th { color: var(--mint); background: var(--panel-2); }
    tr:last-child td { border-bottom: 0; }
    blockquote { margin: 1.4rem 0; padding: .8rem 1.2rem; border-left: 3px solid var(--mint); color: var(--muted); }
    .mermaid { margin: 1.6rem 0; padding: 1.2rem; border: 1px solid var(--line); border-radius: 12px; background: #07101d; text-align: center; }
    .tag { display: inline-block; font-size: .72rem; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; padding: .18rem .55rem; border-radius: 999px; margin-left: .4rem; vertical-align: middle; color: #241c0d; background: var(--amber); }
    footer { padding: 2rem 1rem 3rem; border-top: 1px solid var(--line); color: var(--soft); text-align: center; }
    @media (max-width: 720px) { .book { padding-top: 2rem; } h2 { font-size: 1.7rem; } table { display: block; overflow-x: auto; } }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="topbar-inner">
      <a class="brand" href="./index.html">LATTICE / THEORY</a>
      <a class="back" href="./index.html">Back to home</a>
    </div>
  </header>
  <main class="book">
    <header class="hero">
      <div class="eyebrow">Why the substrate is shaped this way</div>
      <h1>Theoretical Foundations</h1>
      <p class="dek">LATTICE borrows one specific, named piece of mathematics or formal-methods theory at almost every layer — and it's always borrowed for the same reason: so that something derived can <em>prove</em> a safety property about itself, rather than asking a reader to trust it.</p>
      <p class="small">This page assumes no background in any of the theories it covers. Each section explains the idea in plain terms before showing exactly where LATTICE uses it and what it buys.</p>
    </header>

    <nav class="toc" aria-label="Contents">
      <a href="#thesis">0. The thesis</a><a href="#dl">1. Description logic</a><a href="#order">2. Order theory</a><a href="#conservative">3. Conservative extension</a><a href="#threeval">4. Three-valued logic</a><a href="#category">5. Category theory in MORK</a><a href="#session">6. Session types in SPC</a><a href="#determinism">7. Determinism &amp; content-addressing</a><a href="#thread">8. One thread</a><a href="#more">9. Further reading</a>
    </nav>

<div class="wrap" markdown="1">

<h2 id="thesis">0. The thesis</h2>

Every non-trivial system that lets you *derive* things from a source of truth faces the same question sooner or later: how far can you trust the derived thing? LATTICE's answer, repeated at every layer in a different mathematical costume, is: **only as far as something has been mechanically proven, and not one inch further.**

That single sentence is the thread running through this whole page. What changes from layer to layer is *which* branch of logic or theoretical computer science supplies the proof:

<table>
<tr><th>Where</th><th>What's being trusted</th><th>The theory that bounds the trust</th></tr>
<tr><td>The graph itself</td><td>What can be concluded from a possibly-incomplete set of facts</td><td>Description logic and the open-world assumption</td></tr>
<tr><td>Layers, hierarchies, closures</td><td>That a dependency order or an ancestor relation is well-behaved</td><td>Order theory — partial orders, closure operators, well-foundedness</td></tr>
<tr><td>Surface's generated content</td><td>That restating a fact doesn't silently change what it means</td><td>Conservative extension, from model theory</td></tr>
<tr><td>Eligibility's decisions</td><td>What "we don't know yet" is allowed to mean</td><td>Three-valued logic</td></tr>
<tr><td>MORK's mapping proposals</td><td>That an automatically-proposed alignment is actually the best one</td><td>Category theory — profunctors, Galois connections, Formal Concept Analysis</td></tr>
<tr><td>SPC's live conversations</td><td>That a multi-party exchange can't deadlock or desynchronise</td><td>Session types, a type theory for communication protocols</td></tr>
<tr><td>Every compiled artefact</td><td>That regenerating something produces the same thing, not almost the same thing</td><td>Determinism and content-addressing</td></tr>
</table>

None of this is decoration. Read on, and by the end each row above should read as an obvious consequence of the theory next to it, not as jargon bolted on afterward.

<h2 id="dl">1. Description logic and the open-world graph</h2>

Everything in LATTICE sits on top of a **description logic** — the family of decidable logics that OWL (the Web Ontology Language) is built from. A description logic is, deliberately, a *restricted* fragment of first-order predicate logic: it gives up some expressive power in exchange for a guarantee that a machine can always finish checking what follows from what you've asserted, in finite time. Full first-order logic doesn't promise that. Description logics are engineered specifically so a reasoner never has to say "I don't know if this terminates."

<div class="mermaid">
graph TD
  RDFS["RDFS<br/><span style='font-size:11px'>subclass, subproperty,<br/>domain, range</span>"] --> EL["OWL 2 EL<br/><span style='font-size:11px'>existential restrictions,<br/>owl:hasValue — polynomial-time</span>"] --> DL["OWL 2 DL<br/><span style='font-size:11px'>full class expressions,<br/>cardinality, disjointness</span>"]
  EL --- usedByA["Surface's nominal index form<br/>σ(v) ≡ Carrier ⊓ ∃R.{v}<br/>deliberately stays inside EL"]
  DL --- usedByB["SPC's structural layer:<br/>sorts, behaviours, session types"]
  RDFS --- usedByC["SPC's domain-refinement predicates<br/>target EL++, a further-restricted fragment"]
  classDef base fill:#101a2d,stroke:#2a3a56,color:#f4f7ff;
  classDef usage fill:transparent,stroke:#9df7d7,color:#9df7d7,stroke-dasharray: 3 3;
  class RDFS,EL,DL base;
  class usedByA,usedByB,usedByC usage;
</div>

Two consequences of choosing a description logic show up constantly once you start reading LATTICE's specifications:

<h4>The open-world assumption</h4>

A description-logic reasoner never treats the absence of a statement as evidence that the statement is false. If nothing in the graph says who occupies a `RoleOccupancy`, the reasoner concludes nothing about who occupies it — not "nobody," just "unstated." This is the right default for a graph assembled incrementally from many sources, but it has a sharp consequence: a genuinely *closed* question ("is this `GovernanceState` one of exactly four values, and no others") cannot be answered by OWL classes alone, because OWL can never conclude a class extent is exhaustive. LATTICE's answer, used throughout, is to keep the OWL class open and push the closed question into a SHACL shape (`sh:in` over named individuals) — SHACL validates a graph as it stands, right now, closed-world, which is precisely the complementary tool OWL's semantics deliberately withholds.

<h4>Picking the right fragment, on purpose</h4>

Not every part of LATTICE needs the same amount of logical horsepower, and asking for more than you need has a real cost: OWL 2 DL is decidable but can be expensive to reason over; OWL 2 EL is deliberately restricted so that classification stays polynomial-time even over very large ontologies. Surface's nominal-class index form is a direct, stated example of choosing EL on purpose — a generated class is defined as <code>Carrier ⊓ ∃R.{v}</code>, using <code>owl:hasValue</code>, specifically because that construct is inside OWL 2 EL. A form requiring more expressive power than EL would need its own index kind; the design note is explicit that this was a deliberate tractability trade, not an oversight. SPC makes the identical trade at a larger scale: its structural layer (sorts, behaviours, session types) is written in full OWL 2 DL, because the structural questions genuinely need that expressiveness, while its domain-refinement predicates — the part that reaches into an imported ontology to constrain a message payload — are recommended to stay inside the tractable **EL++** fragment specifically so a reasoner checking those constraints doesn't inherit DL's worst-case cost.

<h2 id="order">2. Order theory, and why it's called LATTICE</h2>

A **lattice**, in the mathematical sense the project takes its name from, is a partially ordered set in which every pair of elements has both a unique greatest lower bound (a *meet*) and a unique least upper bound (a *join*). That's a more specific claim than "things are ordered" — it's a claim about *structure*: given any two elements, there's always a well-defined "most specific thing both fit under" and "least specific thing that covers both." Concept hierarchies have exactly this shape, which is why lattice theory turns up wherever ontologies, taxonomies, or type systems are involved.

LATTICE leans on order theory at three distinct scales, and it's worth seeing them side by side, because they're the same mathematics doing three different jobs.

<h3>The layer dependency order is a strict partial order</h3>

The rule "a lower layer never names a term belonging to a higher one" defines a strict partial order over the layers — some pairs are directly comparable (Foundation precedes Vocabulary), some are only comparable through a chain (Foundation precedes Behaviour, via several intermediate steps), and a few are simply incomparable (Eligibility and Instrument's shared dependency on Party doesn't make Eligibility and Instrument comparable to each other). Drawing that order as a diagram is exactly a **Hasse diagram** — the standard way order theory visualises a partial order, where an edge means direct precedence and nothing implied by transitivity is drawn twice.

<div class="mermaid">
graph TD
  fnd["Foundation"] --> voc["Vocabulary"]
  voc --> qnt["Quantification"]
  qnt --> pty["Party"]
  qnt --> srf["Surface<br/><span style='font-size:11px'>(imports Foundation, Vocabulary,<br/>Quantification only — nothing<br/>above imports it back)</span>"]
  pty --> elg["Eligibility"]
  pty --> bhv["Behaviour"]
  elg --> ins["Instrument"]
  ins --> bhv
  elg --> bhv
  classDef surf fill:#14223a,stroke:#d4a8ff,color:#f4f7ff;
  class srf surf;
</div>

This order is exactly what makes an automated import-closure check meaningful in CI: with an unambiguous partial order, "did anything import upward" becomes a single well-formed question instead of a matter of convention.

<h3>Closure operators, appearing three times under three names</h3>

A **closure operator** takes a relation and extends it to include everything reachable by following that relation any number of times (its reflexive-transitive closure), and a relation only supports a *well-defined* closure if it's acyclic — otherwise "everything reachable" is either infinite or ill-defined. LATTICE needs exactly this operation in three unrelated-looking places, and it's worth naming them together because the repository itself never quite says "these are the same mathematical operation" in one place — but they are:

<table>
<tr><th>Where</th><th>The relation being closed over</th><th>What "well-founded" buys</th></tr>
<tr><td>Eligibility's <code>HierarchicalMatch</code></td><td>A concept scheme's <code>skos:broader</code> ordering</td><td>A candidate satisfies a condition exactly when it's in the reflexive-transitive closure of the bound scheme's ordering, restricted to that scheme's members — and a scheme with a cycle simply isn't evaluable under this strategy at all.</td></tr>
<tr><td>Surface's <code>ClosureRelation</code> index form</td><td>A declared closure basis (often also <code>skos:broader</code>, but stated explicitly, never assumed)</td><td>Every carrier instance gets a generated relation to every in-scope ancestor of its value, so a query never walks the taxonomy live — but only after the generator itself has traversed the basis and confirmed it's acyclic, since no fixed SHACL shape can check that for an arbitrary declared relation.</td></tr>
<tr><td>Quantification's ordering machinery</td><td>An <code>OrderingBasis</code>'s priority-ordered components</td><td>A deterministic tie-break, so two events sharing a timestamp resolve the same way everywhere, rather than however a database's insertion order happens to land.</td></tr>
</table>

<div class="mermaid">
graph BT
  leaf["industrial-fire"] -->|broader| mid["fire"] -->|broader| top["peril"]
  leaf -.->|closure: matches self| leaf
  leaf -.->|closure: matches ancestor| mid
  leaf -.->|closure: matches ancestor| top
  classDef base fill:#101a2d,stroke:#2a3a56,color:#f4f7ff;
  classDef closure fill:transparent,stroke:#9df7d7,color:#9df7d7,stroke-dasharray: 4 3;
  class leaf,mid,top base;
</div>

Well-foundedness (no cycles) is stated in LATTICE as a **runtime claim, not a static one** — SPARQL cannot express a property path over a *variable* predicate, so no fixed SHACL shape can verify acyclicity for a relation that's only known at declaration time. The generator has to actually walk the graph and check, and it records the result as evidence (a discharged law) rather than a proof anyone could have derived by inspection alone.

<h3>Ordered value spaces</h3>

Quantification generalises the same theme one level further down, into raw values: every `ValueSpace` states, explicitly, which order theory shape it has — a **total order** (every pair comparable, like a number line), a **cyclic order** (like clock positions, where "which is lower" has no consistent answer without picking an arbitrary cut point), or **no order** (equality-only, comparable but not rankable). Getting this declaration right is what makes a bounded region — a `Range` for a total order, a `CyclicRange` for a cyclic one — a well-defined concept in the first place, rather than a guess about what "between" ought to mean for a particular kind of value.

<h2 id="conservative">3. Conservative extension: the safety property underneath Surface</h2>

Model theory has a precise name for a very useful idea: a theory <em>T′</em> is a **conservative extension** of a theory <em>T</em> if every consequence of <em>T′</em> that's expressible purely in <em>T</em>'s own vocabulary was already a consequence of <em>T</em> — in other words, extending the theory added new things you can say, but proved nothing new about the things you could already say. It's the formal way of saying "this addition is purely additive, never revisionist."

That's exactly the property Surface is built to guarantee, and it's exactly why the layer's name for restating a value as a retrievable symbol — **indexing** — is safe to regenerate or throw away at will: an index always mints its own, brand-new terms, so by construction it can never prove anything new about a term that already existed. Adding one entails nothing new about source terms; removing one loses no fact anyone actually authored. That conservativity, not the speed gain, is the entire reason a generated index is allowed to be treated as disposable cache.

<div class="mermaid">
graph LR
  subgraph src["Source signature (authored)"]
    a["ins:Obligation"]
    b["saas:subscriptionCurrency"]
  end
  subgraph gen["Generated namespace (Surface's own)"]
    c["srf_generated_JobFamily_Engineering"]
  end
  idx["Index"] -->|mints only| c
  promo["Promotion<br/>(exact fidelity, materialised)"] -.->|"may restate onto,<br/>under law X6"| b
  lossy["Promotion<br/>(lossy / crosswalk-inexact)"] -->|"forbidden here — X5"| b
  lossy -->|"must land here instead"| gen
  classDef forbidden stroke:#f3cf8e,stroke-dasharray: 5 4,color:#f3cf8e;
  class lossy forbidden;
</div>

**Promotion** is the one mechanism in Surface that isn't automatically conservative, and the design note treats that honestly rather than hiding it. A promotion restates a value onto a property that may belong to Surface's own namespace, or may be a property some other, consuming layer already declares. In the second case, the emitted triples are literally indistinguishable from facts a person authored by hand — no annotation on the record changes that, because the assertion carries the authored property, not a generated one. Rather than weaken conservativity to pretend this case doesn't exist, Surface names it: every generated surface records a `signatureScope` — `LocalSignature` or `SourceSignature` — and a specific law (`X6`) constrains the dangerous case precisely: a promotion reaching an authored property must preserve the source value's exact meaning and must be written out directly rather than left as a bare, reasoner-dependent definition. A lossy promotion is barred from an authored property altogether (`X5`) — it's confined to Surface's own namespace, where its derived nature stays visible in the identifier itself.

This is conservative extension used as an engineering discipline, not just a proof technique: instead of asking every consumer to somehow know, by convention, which generated facts are "real" and which are restatements, the theory gives a mechanical test — does this cross the signature boundary, and if so, was the crossing exact — and the law is enforced by the compiler, not by trust.

<h2 id="threeval">4. Three-valued logic: living with "we don't know yet"</h2>

Classical logic assumes every proposition is either true or false, and nothing else. That's a convenient fiction for pure mathematics, but it's a bad fit for a graph that's frequently, legitimately incomplete — and LATTICE deliberately doesn't force the fit. Eligibility's decisions, and Quantification's comparisons, both resolve to one of **three** values, not two:

<table>
<tr><th>Value</th><th>Eligibility's reading</th><th>Quantification's reading</th></tr>
<tr><td><strong>True</strong> / <strong>Permitted</strong></td><td>Evidence demonstrates satisfaction.</td><td>The comparison holds.</td></tr>
<tr><td><strong>False</strong> / <strong>Denied</strong></td><td>Evidence demonstrates failure.</td><td>The comparison does not hold.</td></tr>
<tr><td><strong>Undetermined</strong></td><td>Evidence is missing, malformed, incompatible, or insufficient.</td><td>A value is absent, unresolved, insufficiently granular, or an operation isn't permitted for the spaces involved.</td></tr>
</table>

This is the same move logicians make with **Kleene's strong three-valued logic**: rather than defaulting an unknown input to either true or false, "unknown" is treated as its own value that propagates honestly through a computation instead of silently resolving to a guess. Concretely: if a candidate range's lower bound is present but its upper bound is missing, the right answer to "is this contained in the required interval" isn't a coin-flip between Permitted and Denied — it's a distinct, first-class Undetermined, with its own recorded reason (missing value, insufficient granularity, an absent conversion context, and so on), because those different reasons call for different remediation.

There's a quiet but important reason this pairs naturally with the open-world assumption from §1: an open-world reasoner already refuses to treat "the graph doesn't say X" as "X is false," so a two-valued decision procedure built on top of it would have to invent a default somewhere — and any invented default is a policy decision masquerading as a logical one. Three-valued evaluation removes the need to invent anything: "don't know" stays "don't know," all the way out to whoever has to act on the answer.

<h2 id="category">5. Category theory in MORK: turning "which one is this" into a computable optimisation</h2>

MORK's job — aligning messy source material onto a target ontology — sounds like it should require judgement all the way down. Its documentation is candid that you don't need to follow the mathematics to use it, but the mathematics is what lets MORK's judgement be checked rather than just trusted:

<div class="callout quote"><strong>From MORK's own documentation —</strong> "The MORK foundations paper makes extensive reference to category theory (profunctors, Galois connections, Kan extensions, sheaf cohomology, etc), however you don't need to understand the maths to use MORK. Understanding what the maths is aiming to define or prove, might help you trust it though."</div>

<h3>Concept lattices, and the name comes full circle</h3>

The cheapest, always-available layer of MORK's inference is spotting that certain source fields habitually travel together — an attachment point, a limit, and a share appearing together signals a reinsurance "layer," say. This is a textbook application of **Formal Concept Analysis**: given a table of objects and the attributes each one has, FCA finds every maximal group of objects sharing a maximal set of attributes — a "formal concept" — and orders those concepts by which ones' object-sets contain which others'. That ordering always forms a complete lattice. It's a fully deterministic, purely combinatorial technique — no training, no probability — which is exactly why MORK's own comparison table lists it opposite "community detection" with a confidence of 100%, in contrast to every probabilistic alternative listed alongside it.

<div class="mermaid">
graph TB
  subgraph objects["Objects: prior mapping instances"]
    o1["record A"]
    o2["record B"]
    o3["record C"]
  end
  subgraph attrs["Attributes: fields present"]
    a1["AttachmentPoint"]
    a2["Limit"]
    a3["Share"]
    a4["Currency"]
  end
  o1 --> a1
  o1 --> a2
  o1 --> a3
  o2 --> a1
  o2 --> a2
  o2 --> a3
  o2 --> a4
  o3 --> a1
  o3 --> a2
  o3 --> a3
  concept["Formal concept:<br/>extent {A,B,C} × intent {AttachmentPoint, Limit, Share}<br/>— the discovered &quot;Layer&quot; community"]
  o1 -.-> concept
  o2 -.-> concept
  o3 -.-> concept
</div>

<h3>The profunctor: bridging a guess and a proof</h3>

Source data and target ontology are, in MORK's own framing, two fundamentally different kinds of thing: the source side is *probabilistic* — hypotheses with varying confidence — while the target side is *logical* — an ontology's restrictions and disjointness axioms are either satisfied or they aren't. A **profunctor**, in category theory, is a structured way of relating two categories that don't share a common type of morphism — here, essentially a matrix scoring every (source hypothesis, target element) pair, so that mapping reduces to finding the lowest-cost assignment across that matrix. MORK's documentation decomposes this into three phases worth naming, because each is individually a smaller, more tractable question than "solve the whole mapping":

<div class="mermaid">
graph LR
  R["Recognition<br/><span style='font-size:11px'>which community does<br/>this field belong to?</span>"] --> P["Projection<br/><span style='font-size:11px'>which ontology elements<br/>does that community map to?</span>"] --> C["Composition<br/><span style='font-size:11px'>find the community giving<br/>the best source→target route</span>"]
</div>

<h3>The Galois connection: from guessing to knowing</h3>

A **Galois connection** is a pairing between two ordered structures that behave as mutual, order-reversing best-approximations of each other — the textbook example relates a set of objects to a set of properties exactly the way Formal Concept Analysis does above. Once enough confirmed mappings accumulate, MORK's documentation describes a Galois connection emerging between source communities and target classes, characterised precisely: every concept in a community maps to a property the target class requires, and every required property has some concept in the community mapping to it — a perfect, checkable fit, not merely a plausible one. That's the mechanism behind MORK's central claim, its own **convergence theorem**, that the fraction of fields still needing AI or human intervention shrinks the more the system has already confirmed.

<h3>Composing mapping context: the Writer monad</h3>

When one mapping's outcome has to feed into how a dependent mapping is interpreted — Aardvark's identity depends on Aardvark's <code>name</code> property having already been resolved — MORK needs a principled way to thread that accumulated context through a chain of otherwise-independent mapping steps. This is precisely the job of a **Writer monad** in functional programming: a computation that carries an accumulating side-channel of context alongside its main result, composed automatically at every step rather than threaded by hand. MORK's own glossary names it directly: "the mathematical mechanism that ensures axiom context accumulates correctly as mappings compose," realised concretely as a Kleisli-style composition property (`broaderApplicative`) that applies a dependent mapping within the context — the outcome — of the mapping it depends on, rather than in isolation from it.

<div class="callout quote"><strong>From <code>mork/spec/Mork.ttl</code>, on why intent nodes form more than just a list —</strong> "This property generates the morphisms of the preorder category Int(I) (Foundations §2.5a). The intent nodes under this relation form a bounded join-semilattice." Intent refinement isn't just "A is more specific than B" recorded pairwise — refine it enough times and the set of intents, ordered by refinement, has the same join-semilattice shape the layer-dependency order has in §2: a least upper bound always exists for any two intents that share a common refinement.</div>

<h2 id="session">6. Session types in SPC: a type system for conversations</h2>

An ordinary type describes a single value — "this is an integer." A **session type** describes something structurally richer: the entire sequence of sends and receives a participant in a protocol will perform, including its branching and its recursion, before the exchange ends. SPC ("Subject-oriented Process Calculus") is built on the multiparty flavour of this idea, and its purpose is exactly the one stated in the root README: where Behaviour models what state something is in and what can cause it to change, SPC gives the <em>live exchange</em> between the agents driving those changes a formal contract to align to, rather than an ad hoc protocol.

<div class="mermaid">
sequenceDiagram
  participant Buyer
  participant Seller
  participant Bank
  Note over Buyer,Bank: Global type G describes the whole choreography
  Buyer->>Seller: quote(item)
  Seller->>Buyer: price(amount)
  Buyer->>Bank: authorise(amount)
  Bank->>Seller: confirm()
  Note over Buyer,Bank: Projecting G onto each participant<br/>yields that participant's Local type
</div>

A single **global type** describes the whole choreography — who sends what to whom, in what order, across every participant at once. Each participant's **local type** is obtained by *projecting* that global type down onto just their own point of view, discarding everything they can't see. A participant that behaves exactly according to its own local type is, by the standard theory this style of session typing is drawn from, guaranteed free of certain classes of miscommunication by construction — not by testing every possible interleaving by hand.

SPC reifies the runtime state of a whole such system as a **configuration** (which subject is doing what, which messages are in flight, who's externally visible), and evolves it one recorded **reduction step** at a time, in deliberate lockstep with the global type itself being consumed as the choreography plays out. The property tying the two together is the standard type-theoretic guarantee called **subject reduction** (or type preservation): a well-typed configuration, once it takes a step, lands on another well-typed configuration. SPC's own specification is candid that OWL alone cannot fully enforce this, nor a handful of sibling correctness properties — the **duality** between a send-type and its matching receive-type, and **contractiveness** of a recursive type — flagging them explicitly for an external validator or a hand-written rule rather than pretending a description logic reasoner can check them unaided. That's itself a small, honest instance of §1's lesson: pick the logic that actually has the expressive power the question needs, and say plainly when a question has stepped outside it.

<h3>Where SPC meets a domain ontology</h3>

A session type constrains the *shape* of a conversation; it says nothing, on its own, about what a message's payload actually *means* in domain terms. SPC bridges the two through a declared **domain bridge** (mapping SPC's sorts and values onto an imported ontology's concepts and individuals) and states the relationship between its own structural layer and that imported knowledge base in a single, dense line worth unpacking:

<div class="callout quote"><strong>From <code>spc/spec/spc.ttl</code> —</strong> "Contravariant functor 𝒪: SPC^op → DL is realized by conservative extension patterns; narrowing behavior in SPC corresponds to expanding knowledge in DL."</div>

A **functor** maps one category's objects and structure-preserving arrows onto another's while preserving composition; **contravariant** means it reverses the direction of every arrow it maps. Read plainly: the more specific — the more <em>narrowed</em> — a behaviour becomes on the process-calculus side, the <em>more</em> the corresponding description-logic knowledge base has to state to characterise it, and the map between the two directions is itself built from conservative extension (§3's exact technique, reused at a different scale): adding domain detail on the DL side is guaranteed not to invalidate anything already established about the process-calculus side. It's the same "purely additive, never revisionist" property, doing its job at the seam between two genuinely different formal systems rather than within one ontology layer.

SPC also frames a whole subject network as an **open system** — a system with an explicit external interface that other systems can be plugged into, described formally as a **structured cospan**, a standard construction from applied category theory for composing open systems along shared boundaries: <span class="tag">S = (Σ, α, B, ι, o), L(I) → S ← L(J)</span>. The point of stating it this way, rather than as an ad hoc "system with some ports," is that composition of open systems then inherits whatever properties the underlying category-theoretic construction already guarantees, instead of needing to be proven fresh for every new way two subject networks might be wired together.

<h2 id="determinism">7. Determinism and content-addressing: proof by re-computation</h2>

Not every guarantee in LATTICE comes from a branch of logic — one of the load-bearing ones is closer to a discipline from functional programming and reproducible builds: **if a computation is deterministic, you can verify a claim about its output by simply running it again and comparing**, rather than reasoning about the computation's correctness in the abstract. This is the idea underneath the whole staged compiler pipeline that turns a Surface contract, or an Eligibility condition, into an executable SPARQL query, SHACL shape, or SWRL rule.

<div class="mermaid">
graph LR
  A["Declaration graph<br/>+ generation profile"] --> B["Compile once"]
  A --> C["Compile again"]
  B --> H1["artefact hash₁"]
  C --> H2["artefact hash₂"]
  H1 --> CMP{"identical?"}
  H2 --> CMP
  CMP -->|yes| PASS["Law discharged:<br/>regeneration is deterministic"]
  CMP -->|no| FAIL["Generator defect —<br/>not a source change"]
</div>

Concretely: the compiler's own determinism law is discharged by compiling twice and comparing artefact hashes byte-for-byte — not by an argument that the code <em>should</em> be deterministic, but by actually checking, every time, that it was. Underneath that check sits **content-addressing**: identity is computed from a canonical form of what something actually contains, not from an arbitrary label. LATTICE goes further than a single hash, though, because "has this changed" turns out to be at least four genuinely different questions, and collapsing them into one hash throws away distinctions a real deployment needs:

<table>
<tr><th>Hash</th><th>Answers</th></tr>
<tr><td>Semantic content hash</td><td>Has the <em>meaning</em> of the declaration changed?</td></tr>
<tr><td>Generation / profile identity</td><td>Would two correctly-configured implementations have produced an interchangeable result?</td></tr>
<tr><td>Build artefact hash</td><td>Is this exact file byte-identical to what regenerating it right now would produce?</td></tr>
<tr><td>Runtime state hash</td><td>Can a specific replay of a computation be trusted?</td></tr>
</table>

The same discipline shows up in how a batch of MORK mappings gets ordered before compilation — dependency edges are visited in a fixed, IRI-lexicographic order specifically so the same batch always orders the same way regardless of which order triples happened to arrive in — and in why a generated surface has to record exactly what it read to produce itself, one entry per source with a content hash, so staleness reduces to "does any recorded hash still match reality" instead of a question anyone has to reason about by hand.

<h2 id="thread">8. One thread</h2>

Pull the thread all the way through and every section above turns out to be one recurring move, dressed in the mathematics that fits the specific question being asked:

- Description logic bounds what can be concluded from an incomplete graph, and SHACL is reached for exactly where that bound would otherwise be too weak.
- Order theory gives layering, hierarchies, and closures a precise shape — and a precise notion of when that shape is broken (a cycle) rather than a vague sense that something's off.
- Conservative extension is the mechanical test that decides whether a generated fact is safe to discard, applied literally, not just invoked as a slogan.
- Three-valued logic refuses to let "we don't know" collapse into a guess dressed up as an answer.
- Category theory turns "which mapping is correct" from a matter of taste into an optimisation with a checkable, provably-optimal solution once enough evidence exists.
- Session types turn "will this conversation go wrong" from a testing question into a typing question, decidable before anything runs.
- Determinism and content-addressing turn "do I trust this artefact" into "did recomputing it produce the same bytes," which anyone — human or CI job — can just go and check.

And the practical, cross-cutting expression of all of it is the authority ceiling repeated at nearly every layer that generates anything: a derived artefact may declare itself <code>Advisory</code> or, at most, <code>CachedReproducible</code> — trustworthy <em>because</em> it's provably reproducible from its source, and never higher, because a derived thing outranking the declaration it came from would invert the entire relationship this page has been describing. Every theory above exists to make that one sentence something a compiler can enforce, rather than something a README merely asks you to believe.

<h2 id="more">9. Further reading</h2>

This page stays deliberately at the level of "why," with just enough of "what" to make the why concrete. For the fuller vocabulary and the mechanics each layer actually declares, see <a href="./glossary.md">the LATTICE glossary</a>. For the worked, running-code version of everything Surface, Eligibility, and MORK do, see <a href="./book.html">the Field Guide</a>. For the record of each individual decision named above, see the <a href="./adr/">ADR index</a> — in particular ADR-A16 through ADR-A20 for Surface's conservativity laws, and the root <code>mork/README.md</code> and <code>spc/README.md</code> for the fuller mathematical treatments this page has only summarised.

</div>
  </main>
  <footer>LATTICE · Theoretical Foundations · <a href="./index.html">Return to home</a></footer>

  <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({
      startOnLoad: true,
      theme: 'dark',
      themeVariables: {
        background: '#07101d',
        primaryColor: '#14223a',
        primaryTextColor: '#f4f7ff',
        primaryBorderColor: '#2a3a56',
        lineColor: '#8d9bb2',
        secondaryColor: '#101a2d',
        tertiaryColor: '#0d1728',
        fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif'
      },
      securityLevel: 'loose'
    });
  </script>
</body>
</html>
