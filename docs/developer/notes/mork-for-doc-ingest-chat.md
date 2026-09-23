# Comparative Analysis: Document Ingestion Architectures — Lattice/MORK vs. Knwler, TrustGraph, Semantica

This is an analysis to inform an ADR, not a design decision — per the contract, I'm laying out the option space and trade-offs; the actual "which way do we go" call is yours.

---

## 1. The Four Architectures, Side by Side

| | **Knwler** | **TrustGraph** | **Semantica** | **Lattice/MORK** (current) |
|---|---|---|---|---|
| **Ingestion unit of work** | One document → one LLM-driven extraction pass | One document → ontology-grounded ingest pipeline | One document → NER/relation/event extraction pass | N/A yet — MORK targets *schema onboarding*, not document ingestion |
| **What the LLM is shown** | Raw chunk text + an auto-discovered or supplied schema | Raw chunk text + OWL ontology constraints | Raw chunk text (extractors can be classical or LLM) | The **target ontology framed as a MORK mapping vocabulary**, plus prior mapping graph context via Graph RAG |
| **What the LLM produces** | Entities + relations + topics, directly as graph nodes | Ontology-typed triples (RDF), grounded to an existing T-Box | Entities/relations/events as typed dicts | **Mapping nodes** — i.e. not the data itself, but a *rule* for how to derive ontology instances from a schema/shape |
| **Repetition model** | Per-document, every run re-extracts from scratch (cached only for identical input) | Per-document, grounded against a persistent ontology so repeated concepts reuse T-Box classes | Per-document; conflict detection/dedup handles cross-document merge | **Once per schema/source**, not once per document. The mapping graph is reused indefinitely across every document instance of that schema |
| **Human role** | None built in (batch/report-review only) | Ontology Workbench for post-hoc curation | Entity Resolution workspace for merge review | **Mandatory validation gate** before a mapping is trusted — human-in-the-loop is structural, not optional |
| **Backend graph model** | JSON property graph (exports to many formats) | RDF 1.2 named graphs (quads) | Polyglot: RDF or LPG | RDF/OWL 2 DL (via MORK's target ontology assumption) |
| **Reduction of repeated cost** | LLM response caching (same input → same output, free) | Ontology grounding reduces re-derivation of already-known classes | Standard extractor caching | **MCN token-compressed notation + MTP training** — architecturally aimed at reducing the *cost of describing the vocabulary itself*, not just caching repeated inputs |

**The structural difference that matters most:** Knwler, TrustGraph, and Semantica all treat ingestion as "turn *this document's* text into graph facts, every time, for every document." MORK was built to solve a different problem: "turn *this schema/source shape* into a reusable, human-validated mapping rule, once." That's a fundamentally different cost curve — amortized-per-schema vs. paid-per-document.

This is the single most important thing to reconcile before deciding whether MORK is "overkill" for document ingestion — it depends on which cost curve document ingestion actually needs.

---

## 2. Is document ingestion actually a schema-mapping problem?

There are two very different sub-problems hiding inside "document ingestion," and the three OSS tools conflate them (which is fine for their use case, but worth separating for yours):

**(a) Structure discovery** — segmenting a document into sections, tables, headers, footnotes; identifying what *kind* of document it roughly is. This is a one-time-per-document-type problem, closer to a schema than to content. A 40-page 10-K filing has a recognizable *shape* that recurs across thousands of other 10-Ks.

**(b) Fact extraction** — pulling entities/relations/events out of the *specific* prose of *this* document. This genuinely varies per document instance and can't be cached the way a schema mapping can.

Knwler/TrustGraph/Semantica largely blur these into one LLM pass per chunk. Your instinct — "doc processing tools break the doc up and identify structure... then run *that* over an LLM + ontology for structural analysis, then do non-LLM word matching" — is effectively proposing to split (a) out and treat it the way MORK treats schema mapping: a reusable, validated, once-per-document-type mapping, while treating (b) as the part that must run per-document.

That reframing is coherent with MORK's actual design center. The open design question is **whether (a) needs MORK's full intent-node vocabulary, or something lighter that borrows only its validation/reuse/compression machinery.**

---

## 3. Is the "intent layer" between text and ontology overkill?

Worth being precise about what that layer buys you in the *schema-mapping* case, so you can judge whether the same justification holds for *documents*:

- **Ambiguity resolution before commitment.** MORK's `MappingRole` case analysis (TBox creation vs. reference, Datum individuation, RBox assertion, contextual application, template composition, reference lookup) exists because schema fields are frequently *structurally* ambiguous relative to the ontology — the same field might be a class-creating assertion or a property assertion depending on context elsewhere in the schema. Free text is ambiguous in a completely different way (referential, not structural) — "this pronoun refers to which entity," not "is this a class or a property."
- **Reusability and auditability of the mapping itself**, independent of any one instance of data. This matters enormously for a schema, which is stable and reused across millions of records. It matters much less for a single document's specific factual claims, which are exactly the "child" data that gets plugged into an already-established mapping template.
- **Compilation to a deterministic executable artifact** (the RML compiler you've shown — MORK mapping graph → RML → repeatable ETL). This is precisely the payoff of investing in an intent layer: you pay the LLM+human cost once, then run a cheap deterministic compiler forever after. Document *fact* extraction has no equivalent "compile once, execute forever" property — each document's facts are novel data, not a novel rule.

**Conclusion of this thread:** the intent-node abstraction earns its cost when the artifact being produced is a *reusable rule*. It has diminishing returns when the artifact is *one-shot factual content*. That maps cleanly onto your structure/fact split in §2: structure discovery (a) is rule-like and could genuinely benefit from a MORK-style mapping-and-validation loop (with a lighter vocabulary); fact extraction (b) probably shouldn't go through an intent-node detour at all — it should target ontology instances fairly directly, the way Knwler/TrustGraph/Semantica do, but *grounded by* whatever structural mapping was already validated for that document type.

So "full MORK as the document-ingestion target" does look like overkill for stage (b), and plausibly right-sized (with a lighter, extraction-specific vocabulary) for stage (a).

---

## 4. What a hybrid pipeline could look like

Combining your sketch with what's demonstrated by the three tools and the non-LLM addendum:

```
Document → [Structural Parser: non-LLM] → sections/tables/blocks + doc-type fingerprint
              │
              ▼
    Doc-type fingerprint seen before?
         │                    │
        Yes                   No
         │                    │
   Reuse validated       [LLM + ontology: structural mapping proposal]
   structural mapping    (MORK-lite intent vocabulary, scoped to
   (deterministic,       document *structure* not document *facts*)
    no LLM)                    │
         │               Human validates/corrects → stored in mapping graph
         │                    │
         └────────┬───────────┘
                   ▼
      [Per-section fact extraction]
      Tier 1 (non-LLM): entity/relation candidates via
        - sentence-transformer lexical match against ontology intent profiles
        - FCA/community detection reusing MORK's existing community machinery
        - OWL reasoner constraint filtering (type/disjointness pre-filter)
                   │
      Tier 2 (LLM, only for what survives filtering / low confidence):
        free-text decomposition, novel entity typing, disambiguation
                   │
                   ▼
        Ontology instances (facts), with provenance back to source spans
                   ▼
        Human spot-check / correction (lighter-touch than schema validation,
        since facts are numerous and lower-stakes per-item than a mapping rule)
```

Notes on how this reuses what you already have:

- **Structural mapping reuse is exactly MORK's convergence property**, just applied to document *shape* fingerprints instead of API schemas. The same "validated-once, compiled-and-reused-forever" argument applies, and the RML-style compiler pattern (compile the mapping DAG to a deterministic executable) is directly reusable if you define a comparable compilation target for "parse this document type into typed blocks."
- **Tier 1 fact-extraction filtering is literally what the addendum recommends for Stage 1/2 of the existing MORK pipeline** — sentence-transformer lexical scoring, OWL reasoner disjointness pre-filtering, FCA community detection. Nothing about applying those to document fact extraction requires them to be MORK-specific; they're general neuro-symbolic techniques that both pipelines can share as infrastructure, which is efficient given you're building it once either way.
- **Graph RAG over previous mapping runs**, which you already use for schema onboarding, has a direct analog for document ingestion: Graph RAG over previously validated structural mappings *and* previously extracted facts from similar documents, to prime the LLM's Stage 2/Tier 2 prompts and cut token spend, similar in spirit to Knwler's schema auto-discovery-from-sample and TrustGraph's ontology grounding (both avoid re-deriving what's already known).

---

## 5. MCN/MTP relevance to document ingestion

You noted MCN/MTP currently target MORK nodes, not ontology nodes, and are "somewhat incomplete." Two observations:

1. If stage (a) — structural mapping — ends up using a MORK-derived (even if lighter) vocabulary, MCN/MTP's compression work is directly reusable there with no conceptual gap, since it's the same class of artifact (a mapping-graph description) that just happens to describe document structure rather than API schema structure.
2. If stage (b) — fact extraction — targets ontology instances directly (bypassing an intent layer, per §3's conclusion), then MCN/MTP's *current* design doesn't help there at all, because it compresses mapping-node vocabulary, not instance/fact vocabulary. If token cost during fact extraction turns out to be a real problem, that would need a parallel compression scheme for *ontology instance assertions*, which is a new, separate piece of work rather than an extension of MCN.

---

## 6. Cross-tool takeaways worth stealing regardless of which path you pick

- **Knwler's cheap local-first defaults (Ollama, aggressive caching, resumable batch)** — worth adopting as a baseline expectation for whatever Lattice's ingestion CLI ends up looking like, since local-first is already a stated value in your other repos' READMEs.
- **TrustGraph's "ingestion produces ontology-typed knowledge, not just entities/relations"** — this is the closest existing-tool analog to what you're describing for stage (b): grounding extraction against a target ontology rather than an ad hoc auto-discovered schema (which is Knwler's weaker point — its schema is inferred per-document-run and not guaranteed consistent across documents).
- **Semantica's conflict detection / entity resolution as first-class pipeline stages**, not afterthoughts — relevant once you're running fact extraction across many documents that reference overlapping entities; MORK's human correction-storage precedent (corrections become graph data) generalizes naturally to "conflicting facts flagged and resolved, resolution stored," so this is likely a small extension rather than new architecture.
- **The non-LLM addendum's Tier 1/Tier 2/Tier 3 framing** transfers almost unchanged to document fact extraction: Tier 1 (lexical/symbolic, always non-LLM) and Tier 2 (statistical, mostly non-LLM) can absorb the "which ontology class/property does this span correspond to" work; Tier 3 (LLM-preferred, human-escalatable) stays reserved for genuinely novel phrasing or ambiguous relations — same shape as recommended for schema mapping, just re-pointed at document spans instead of schema fields.

---

## 7. Open questions to resolve before this becomes an ADR

1. Do you want **one shared mapping-graph vocabulary** across schema-onboarding and document-structure-discovery (i.e., MORK proper, possibly lightly extended), or a **second, sibling vocabulary** purpose-built for document structure that reuses MORK's compilation/validation *pattern* but not its node types? This is the crux of the "is MORK overkill" question and probably deserves its own ADR framing rather than being folded into a general ingestion-pipeline ADR.
2. Should fact-extraction outputs (ontology instances) go through *any* intermediate validation gate before commit, or is the plan to trust Tier 1/Tier 2 confidence scores and only human-review low-confidence Tier 3 outputs? This affects whether "corrections become graph data" (MORK's current human-loop pattern) extends to facts or stays scoped to mapping rules only.
3. Where does document-type fingerprinting/reuse get evaluated — is "have we seen this shape before" itself a MORK-style community-detection problem (reusing FCA/Leiden machinery already scoped for schema communities), or does it need its own similarity model?
4. Given `tools/mork` and `ontology/mork` already exist per the repo topology rules, would a document-ingestion vocabulary extension live as `ontology/mork` additions, or does it warrant its own `ontology/<name>` + `tools/<name>` pair as a sibling system, per the repository topology conventions in your instructions?

None of these need answering in this message — flagging them so the next step can be a properly scoped ADR (and, if useful, a design sketch in `docs/architecture/solution-design-specification.md`) rather than jumping straight to implementation.