## 7. Determinism and content-addressing: proof by re-computation
{: #determinism}

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

Concretely: the compiler's own determinism law is discharged by compiling twice and comparing artefact hashes byte-for-byte — not by an argument that the code *should* be deterministic, but by actually checking, every time, that it was. Underneath that check sits **content-addressing**: identity is computed from a canonical form of what something actually contains, not from an arbitrary label. LATTICE goes further than a single hash, though, because "has this changed" turns out to be at least four genuinely different questions, and collapsing them into one hash throws away distinctions a real deployment needs:

| Hash | Answers |
|---|---|
| Semantic content hash | Has the *meaning* of the declaration changed? |
| Generation / profile identity | Would two correctly-configured implementations have produced an interchangeable result? |
| Build artefact hash | Is this exact file byte-identical to what regenerating it right now would produce? |
| Runtime state hash | Can a specific replay of a computation be trusted? |

The same discipline shows up in how a batch of MORK mappings gets ordered before compilation — dependency edges are visited in a fixed, IRI-lexicographic order specifically so the same batch always orders the same way regardless of which order triples happened to arrive in — and in why a generated surface has to record exactly what it read to produce itself, one entry per source with a content hash, so staleness reduces to "does any recorded hash still match reality" instead of a question anyone has to reason about by hand.
