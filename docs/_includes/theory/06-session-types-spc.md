## 6. Session types in SPC: a type system for conversations
{: #session}

An ordinary type describes a single value — "this is an integer." A **session type** describes something structurally richer: the entire sequence of sends and receives a participant in a protocol will perform, including its branching and its recursion, before the exchange ends. SPC ("Subject-oriented Process Calculus") is built on the multiparty flavour of this idea, and its purpose is exactly the one stated in the root README: where Behaviour models what state something is in and what can cause it to change, SPC gives the *live exchange* between the agents driving those changes a formal contract to align to, rather than an ad hoc protocol.

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

SPC reifies the runtime state of a whole such system as a **configuration** (which subject is doing what, which messages are in flight, who's externally visible), and evolves it one recorded **reduction step** at a time, in deliberate lockstep with the global type itself being consumed as the choreography plays out. The property tying the two together is the standard type-theoretic guarantee called **subject reduction** (or type preservation): a well-typed configuration, once it takes a step, lands on another well-typed configuration. SPC's own specification is candid that OWL alone cannot fully enforce this, nor a handful of sibling correctness properties — the **duality** between a send-type and its matching receive-type, and **contractiveness** of a recursive type — flagging them explicitly for an external validator or a hand-written rule rather than pretending a description logic reasoner can check them unaided. That's itself a small, honest instance of [Section 1](#dl)'s lesson: pick the logic that actually has the expressive power the question needs, and say plainly when a question has stepped outside it.

### Where SPC meets a domain ontology

A session type constrains the *shape* of a conversation; it says nothing, on its own, about what a message's payload actually *means* in domain terms. SPC bridges the two through a declared **domain bridge** (mapping SPC's sorts and values onto an imported ontology's concepts and individuals) and states the relationship between its own structural layer and that imported knowledge base in a single, dense line worth unpacking:

<div class="callout quote"><strong>From <code>spc/spec/spc.ttl</code> —</strong> "Contravariant functor 𝒪: SPC^op → DL is realized by conservative extension patterns; narrowing behavior in SPC corresponds to expanding knowledge in DL."</div>

A **functor** maps one category's objects and structure-preserving arrows onto another's while preserving composition; **contravariant** means it reverses the direction of every arrow it maps. Read plainly: the more specific — the more *narrowed* — a behaviour becomes on the process-calculus side, the *more* the corresponding description-logic knowledge base has to state to characterise it, and the map between the two directions is itself built from conservative extension ([Section 3](#conservative)'s exact technique, reused at a different scale): adding domain detail on the DL side is guaranteed not to invalidate anything already established about the process-calculus side. It's the same "purely additive, never revisionist" property, doing its job at the seam between two genuinely different formal systems rather than within one ontology layer.

SPC also frames a whole subject network as an **open system** — a system with an explicit external interface that other systems can be plugged into, described formally as a **structured cospan**, a standard construction from applied category theory for composing open systems along shared boundaries: <span class="tag">S = (Σ, α, B, ι, o), L(I) → S ← L(J)</span>. The point of stating it this way, rather than as an ad hoc "system with some ports," is that composition of open systems then inherits whatever properties the underlying category-theoretic construction already guarantees, instead of needing to be proven fresh for every new way two subject networks might be wired together.
