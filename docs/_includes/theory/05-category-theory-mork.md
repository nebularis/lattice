## 5. Category theory in MORK: turning "which one is this" into a computable optimisation
{: #category}

MORK's job — aligning messy source material onto a target ontology — sounds like it should require judgement all the way down. Its documentation is candid that you don't need to follow the mathematics to use it, but the mathematics is what lets MORK's judgement be checked rather than just trusted:

<div class="callout quote"><strong>From MORK's own documentation —</strong> "The MORK foundations paper makes extensive reference to category theory (profunctors, Galois connections, Kan extensions, sheaf cohomology, etc), however you don't need to understand the maths to use MORK. Understanding what the maths is aiming to define or prove, might help you trust it though."</div>

### Concept lattices, and the name comes full circle

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

### The profunctor: bridging a guess and a proof

Source data and target ontology are, in MORK's own framing, two fundamentally different kinds of thing: the source side is *probabilistic* — hypotheses with varying confidence — while the target side is *logical* — an ontology's restrictions and disjointness axioms are either satisfied or they aren't. A **profunctor**, in category theory, is a structured way of relating two categories that don't share a common type of morphism — here, essentially a matrix scoring every (source hypothesis, target element) pair, so that mapping reduces to finding the lowest-cost assignment across that matrix. MORK's documentation decomposes this into three phases worth naming, because each is individually a smaller, more tractable question than "solve the whole mapping":

<div class="mermaid">
graph LR
  R["Recognition<br/><span style='font-size:11px'>which community does<br/>this field belong to?</span>"] --> P["Projection<br/><span style='font-size:11px'>which ontology elements<br/>does that community map to?</span>"] --> C["Composition<br/><span style='font-size:11px'>find the community giving<br/>the best source→target route</span>"]
</div>

### The Galois connection: from guessing to knowing

A **Galois connection** is a pairing between two ordered structures that behave as mutual, order-reversing best-approximations of each other — the textbook example relates a set of objects to a set of properties exactly the way Formal Concept Analysis does above. Once enough confirmed mappings accumulate, MORK's documentation describes a Galois connection emerging between source communities and target classes, characterised precisely: every concept in a community maps to a property the target class requires, and every required property has some concept in the community mapping to it — a perfect, checkable fit, not merely a plausible one. That's the mechanism behind MORK's central claim, its own **convergence theorem**, that the fraction of fields still needing AI or human intervention shrinks the more the system has already confirmed.

### Composing mapping context: the Writer monad

When one mapping's outcome has to feed into how a dependent mapping is interpreted — Aardvark's identity depends on Aardvark's `name` property having already been resolved — MORK needs a principled way to thread that accumulated context through a chain of otherwise-independent mapping steps. This is precisely the job of a **Writer monad** in functional programming: a computation that carries an accumulating side-channel of context alongside its main result, composed automatically at every step rather than threaded by hand. MORK's own glossary names it directly: "the mathematical mechanism that ensures axiom context accumulates correctly as mappings compose," realised concretely as a Kleisli-style composition property (`broaderApplicative`) that applies a dependent mapping within the context — the outcome — of the mapping it depends on, rather than in isolation from it.

<div class="callout quote"><strong>From <code>ontology/mork/spec/Mork.ttl</code>, on why intent nodes form more than just a list —</strong> "This property generates the morphisms of the preorder category Int(I) (Foundations §2.5a). The intent nodes under this relation form a bounded join-semilattice." Intent refinement isn't just "A is more specific than B" recorded pairwise — refine it enough times and the set of intents, ordered by refinement, has the same join-semilattice shape the layer-dependency order has in <a href="#order">Section 2</a>: a least upper bound always exists for any two intents that share a common refinement.</div>
