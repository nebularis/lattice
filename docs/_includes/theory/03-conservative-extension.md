## 3. Conservative extension: the safety property underneath Surface
{: #conservative}

Model theory has a precise name for a very useful idea: a theory *T′* is a **conservative extension** of a theory *T* if every consequence of *T′* that's expressible purely in *T*'s own vocabulary was already a consequence of *T* — in other words, extending the theory added new things you can say, but proved nothing new about the things you could already say. It's the formal way of saying "this addition is purely additive, never revisionist."

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
