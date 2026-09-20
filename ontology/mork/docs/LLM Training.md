# Teaching MORK to LLMs: a compiled curriculum, not a document

## 1. Reframe the problem

The instinct is "compress the ontology." That is the wrong target. `Mork.ttl` is ~45k tokens of *definitions*, and definitions are the least useful thing you can give a model: a model that has read the definition of `broaderApplicative` still cannot tell you when to use it. What it needs is the **decision procedure** and the **failure it prevents**.

Two properties of the MORK stack change what teaching has to achieve:

1. **There is a deterministic checker downstream.** MCN decoding, the §14.2 lint set, OWL DL checking, and `constraints.ttl` mean a wrong graph is *caught*, not shipped. So the model does not need recall-level mastery. It needs to be **reliably repairable**: produce something structurally close, then converge under typed feedback. Teaching recognition + repair is an order of magnitude cheaper than teaching recall.
2. **MORK has first-class uncertainty.** `UncertainMapping`, `hypothesisMapping`, `mappingRecommendation`, `weighting`, `DeferredContext`. A model that doesn't know something has a *correct* thing to emit: a low-weighted uncertain mapping with a note. This converts hallucination into a reviewable artefact. That single habit is worth more than 20k tokens of vocabulary.

So: **teach a small kernel, enforce form mechanically, route nuance just-in-time, and make uncertainty the default escape.**

Third structural move: **split form from judgement.**

| Concern | Mechanism | Teaching cost |
|---|---|---|
| Syntax, codes, arity, datatypes | Grammar-constrained decoding / tool schema (MCN §19 EBNF → GBNF or structured-output schema) | ~0 |
| Which code, which direction, which box, what precedence | Taught | the real budget |

Where the API supports constrained decoding, the codebook stops being something to learn and becomes something the sampler cannot violate. Where it doesn't, the same codebook file renders as a prompt table. Either way it is generated from `Mork.ttl`, so it never drifts.

---

## 2. The artefact: a MORK Teaching Pack (MTP)

A versioned, hash-pinned **build artefact of the ontology**, not a hand-written guide. Layered, with hard token budgets, and only L0 is always resident.

| Tier | Content | Budget | Residency |
|---|---|---|---|
| **L0 Kernel** | What MORK is; 7 invariants; the decision ladder; 14 hot codes; uncertainty escape; output contract | 700–900 | always |
| **L1 Hot codebook** | Top ~40 codes by measured frequency + the 4 positional inline forms | 600–800 | always (or replaced by grammar) |
| **L2 Lenses** | 9 self-contained doctrine units (see §4) | 300–800 each | task-routed, 1–3 loaded |
| **L3 Cassettes** | Minimal-pair exemplars, NL → MCN → decoded delta | 150–400 each | task-routed, 2–4 loaded |
| **L4 Errata card** | Deployment-learned corrections + naming/ID policy | ≤600 | always |
| **L5 Full codebook / spec / ontology prose** | MCN §8, §10, `Mork.ttl` scope notes | large | on demand only (attachment, tool call, or RAG if available) |

Typical working prompt: **L0 + L1 + L4 + 2 lenses + 3 cassettes ≈ 3.5–4.5k tokens**, against ~45k for the ontology and ~15k for the full MCN spec. Critically, the resident part (L0+L1+L4 ≈ 2k) is *byte-stable*, which matters for §6.

### L0 kernel, drafted

This is the whole of what must be unconditionally known:

```
MORK records mapping INTENT as reviewable graph objects. You emit MCN
(compact notation); a deterministic decoder produces RDF; OWL+SHACL judge it.
You are not writing a script. You are proposing a mapping that a human will review.

INVARIANTS
1. Three worlds: Representation (the wire format), Taxonomy (concepts), Ontology
   (the target). Mappings live in a 4th: MappingScheme. Never mix them on one node.
2. Target side has three boxes. Class => T-Box (xt/bt). Property/relation => R-Box
   (xr/xi/br). Named individual => A-Box (xa/ba).
3. Order is structure, not instruction. Express "X before Y" by deferral
   (df/dp), composition (cb/cn) or applicative context (ap). Never by line order.
4. One direction per inverse pair. Write cb from the child OR cn from the parent.
5. Nothing exists until asserted. To reference an axiom you are also creating,
   go through a DeferredContext (MX) that yields it (y .dci).
6. Uncertainty is expressible. If unsure: MU + w <100 + mr "recommendation"
   + n "evidence". Never invent a target IRI to look complete.
7. Notes carry EVIDENCE, not restatement. `lx :laysEggs{n "..."}` already says
   "lexical match"; the note says why you believed it.

DECISION LADDER (ask in order, stop when answered)
Q1 What am I describing — wire shape (%R), concept (%T), or a mapping (%M)?
Q2 Does the target already exist? yes -> exact match (xt/xr/xa)
   no  -> category match (bt/br/ba) + name it (c "#Name")
Q3 Must a datum become an individual? yes -> MD, and df to whatever
   establishes its class.
Q4 Is this node a part of a larger mapping? yes -> cb <parent>.
   Does it operate INSIDE the parent's result? yes -> ap <parent> + xr/xi.
Q5 Does this produce an artefact (shape/rule/transform/class)?
   yes -> load the Generative lens. It has mandatory co-occurring parts.
Q6 How confident am I? <100 -> w, and if guessing, MU.

OUTPUT CONTRACT
Emit only MCN. Header, blocks, node lines. No commentary outside `#` comments.
Prefer MD over M+MD. Prefer structure over prose. Name nodes, don't number them.
If you need a term you don't have a code for, use a CURIE in code position and
flag it in a note — do not approximate with a code that means something else.
```

That last clause is load-bearing: the CURIE escape (MCN §4) makes **partial vocabulary knowledge safe**. A model that knows 40 codes and escapes the rest is correct and reviewable. A model that knows 200 codes badly is not.

---

## 3. Minimal pairs: the highest-density teaching object

Nuance lives almost entirely in ~12 confusable distinctions. Each is a one-line contrast plus the lint code it prevents — far cheaper and stickier than prose:

| Confusion | Use A when | Use B when | Caught by |
|---|---|---|---|
| `xt` vs `bt` | class exists in target | you are minting a subclass | — |
| `df` vs `dp` | you consume the parent's output as context | it must merely run first; you reach its result via `y` | — |
| `cb` vs `ap` | this node is a *part* of the parent | this node operates *within* the parent's outcome | `ap` w/o `xr` → GCI 2.14a |
| `xr` vs `xi` | property points subject→object | you need the property's inverse | — |
| `ba` vs `xa` | subject maps to a broader A-Box category via a relation | plain exact individual match | 2.14b / 2.14d |
| `hy` vs `df` | evidential support, may be absent (soft) | hard prerequisite | — |
| `MU` vs `MW` | target missing/unknown | target known, confidence scored | MU equivalence |
| `MS` vs `MR` | validation (SHACL) | inference (SWRL) | disjointness |
| `tp` vs `cbt/cnt` | partial template mapping | template's *children* | — |
| `kn/kb` vs `cn/cb` | between concepts/representations | between **mappings** | domain/range |
| `I*` intent vs `M*` mapping | pre-ontological meaning | ontological commitment | — |

Ship this table in L0. It is ~250 tokens and removes most of the observed error surface.

---

## 4. Lenses: doctrine units, not chapters

Nine units, each written to a fixed template so it compresses well and reads uniformly: **Question it answers → Rules → Mandatory co-occurrences → Smell tests → Lint codes it prevents → one cassette pointer.**

`L-REP` representation & collections · `L-TAX` taxonomy, objectification, roles · `L-IND` individuation, deferral, precedence · `L-GEN` generative mappings + governance/production gate · `L-TPL` template expression algebra · `L-INT` intent algebra · `L-EGR` egress/projection · `L-UNC` uncertainty & weighting · `L-TBX` axiom lines & shadow declarations.

**Routing without RAG.** A static table, shipped in the pack, keyed on task type and cheap input signals — not a vector search:

```
task=ingest-json-schema        -> L-REP, L-IND   cassettes: C1,C2
task=map-concepts              -> L-TAX, L-UNC   cassettes: C3
task=eligibility-from-prose    -> L-INT, L-GEN   cassettes: C6,C7
signal: numbers+units+currency -> +L-INT
signal: "must/shall/validate"  -> +L-GEN (shape)
signal: "if...then/implies"    -> +L-GEN (rule)
signal: target IRI absent      -> +L-UNC, +L-TBX
```

Deterministic, auditable, diffable, and it degrades to "load all lenses" (~5k) if the router is unavailable. If Graph RAG *is* available, lens boundaries are exactly the chunk boundaries — retrieval returns doctrinally complete units instead of severed prose.

---

## 5. The repair loop is the real teacher

The cheapest and most effective teaching happens at the moment of error, and costs only the failing fragment.

```
model emits MCN → decode (§13) → lint (§14.2) → SHACL/OWL
   ↳ on failure: return {line, lint code, 1–3 line doctrine fragment, 1 corrected micro-example}
```

Maintain a **diagnostic → doctrine** table (one row per lint code and per SHACL shape), because a lint code already localises the misunderstanding precisely:

| Signal | Injected fragment (≈40 tokens) |
|---|---|
| `ap` without `xr`/`xi` | "Applicative context needs the relation joining parent result to child. Add `xr <prop>` or `xi <prop>`." + example |
| `MD` without `df` | "A Datum must defer to whatever establishes its class: `df Map_X_Class`." |
| `MS` missing `pv` | "Shape mappings are governed: `pv [creator model conf DRAFT pd <ts>]` is mandatory." |
| both `cn` and `ap` to same node | "Choose one: part-of (`cb`) or within-context (`ap`). Both double-counts the edge." |

Two consequences: (a) initial prompts can be *smaller*, because the loop covers the tail; (b) every repair is a labelled training pair — see §7.

Streaming lint (MCN §20) lets this fire mid-generation where the API allows it.

---

## 6. Persistence across runs without fine-tuning or RAG

"Understanding preserved across runs" is achieved by **making the instruction immutable and the environment corrective** — never by hoping the weights remember.

**(a) Hash-pinned frozen pack.** MTP releases are immutable and versioned (`mtp-1.4.0`, manifest SHA). Every run loads the same bytes; the hash goes into the run record alongside model id, exactly as `mork:inputHash` and `ConstraintProvenance` already do for artefacts. Same input ⇒ same instruction ⇒ reproducible competence. This is the whole answer to "preserved across runs": the *artefact* is the memory.

**(b) Prompt caching.** Because L0+L1+L4 are byte-stable and ordered first, they sit in the provider's prefix cache. Resident teaching becomes near-free after the first call, which removes the usual pressure to under-specify. Order the prompt: `[frozen pack] [deployment profile] [lenses] [cassettes] [task]` — most stable first.

**(c) Deployment profile = cross-run identity memory.** MCN `@u` profiles (§6.1) already remove prefix tokens; extend the same file with a **naming policy** (id conventions, minted-name patterns, chosen `@t`). This is what keeps `Map_Loan` called `Map_Loan` across runs — essential for `supersedes` chains and `fnd:hasIdentity` to mean anything. Consistency of *names* across sessions is a real requirement that no amount of model memory would satisfy; it must be externalised.

**(d) Errata card: learning without weights.** Lint/SHACL telemetry is aggregated per deployment; recurring failure signatures are compacted (by a human or an offline LLM pass, reviewed, capped at ~600 tokens) into L4. The system genuinely gets better run over run, and the improvement is **inspectable and revertible** — which is more than a fine-tune offers. Treat L4 like any governed artefact: provenance, review status, version.

**(e) Optional accelerants, never dependencies.** Same source, four compilation targets — deliberately mirroring the staged-compiler/backend-fanout pattern of ADR-A19:

```
MTP source (generated from Mork.ttl + example corpus + repair log)
  ├─> prompt bundle        (baseline; required)
  ├─> grammar / tool schema (removes syntax teaching where supported)
  ├─> retrieval index       (optional: lens- and cassette-granular)
  └─> SFT/LoRA corpus       (optional: cassettes + repair pairs)
```

Capability ladder, each rung strictly better but none required:

| Available | Resident tokens | Expected first-pass lint-clean |
|---|---|---|
| Prompt only | ~4.5k | baseline |
| \+ prompt caching | ~4.5k (cheap) | baseline |
| \+ constrained decoding | ~3.5k | syntax errors → 0 |
| \+ retrieval | ~2.5k | tail coverage ↑ |
| \+ fine-tune | ~1.2k (kernel only) | highest |

---

## 7. Governing the curriculum

The pack must be a **build product**, tested like code, or it will drift from `Mork.ttl` within one release.

- **Generation.** Codebook from the ontology (already the case per §20); lenses hand-written but their *term coverage* machine-checked; cassettes are real repository examples with round-trip proofs.
- **CI gates.** Every declared term in `Mork.ttl` has a code *and* appears in exactly one lens. Every cassette's MCN decodes and is graph-isomorphic to its gold Turtle. Every lint code has a doctrine fragment. Every GCI has a minimal-pair row or a cassette. Budgets enforced (L0 ≤ 900 tokens, etc.).
- **Eval harness = the drift detector.** A held-out suite of ~30 tasks with gold graphs, scored on: first-pass lint-clean rate, repair rounds to green, tokens per decoded triple, semantic F1 against gold (predicate-level), and *unsafe-confidence rate* (mappings asserted exactly where an `MU` was warranted). Run on every pack change **and every model version bump** — the latter is how you detect that a frontier upgrade silently changed behaviour, the genuine threat to "understanding preserved across runs."
- **Provenance.** Each proposal records `mtp-version`, `profile-hash`, `model-id`, `lenses-loaded`. Then when a class of bad mappings is discovered six months later, you can query which teaching configuration produced them — the same audit guarantee MORK gives mappings, applied to the thing that generated them.

---

## 8. What to build first

1. L0 kernel + minimal-pair table + output contract (~1.2k tokens). Highest value per token by a wide margin.
2. Codebook generator → prompt table **and** grammar (kills the syntax error class outright).
3. Decode→lint→repair harness with the diagnostic→doctrine table.
4. Eval suite of 30 tasks with gold graphs. Without this, every later decision is guesswork.
5. Lenses + cassettes, written in frequency order from real corpus statistics.
6. Errata pipeline and profile/naming policy.
7. Only then consider retrieval indexing and fine-tuning — both as compilation targets of the same source.

The essential claim: **stop trying to make the model know MORK, and make the environment make MORK unmistakable.** A 2k-token immutable kernel, a grammar that forbids malformed output, a lint loop that teaches at the point of error, and an errata card that accumulates institutional memory will outperform a 45k-token ontology dump — and unlike a fine-tune, you can read it, diff it, version it, and revert it.
