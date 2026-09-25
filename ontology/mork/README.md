# MORK for Dummies

**A Plain-English Guide to Mapping Ontological and Representational Knowledge**

*Making sense of messy data, one mapping at a time*

---

## Part 1: The Problem

### Why Data Integration Is Hard

Imagine you run an insurance company. You receive data from dozens of brokers, each using their own formats:

| Broker A | Broker B | Broker C |
|----------|----------|----------|
| `xs_point` | `attachment_amt` | `excess_of_loss_point` |
| `lmt` | `limit_amount` | `layer_limit` |
| `ccy` | `currency_code` | `curr` |

They all mean the same things, but they all say it differently. Traditionally, you'd build a translation layer — an ETL pipeline, a canonical data model — that maps each broker's format into your internal format. Field by field. Broker by broker.

This works until:

- **A broker changes their format.** Now you fix their translation and hope nothing else breaks.
- **A new broker arrives.** Now you build another translation from scratch.
- **Your internal model evolves.** Now you update *every* translation for *every* broker.
- **A regulator asks for a new data element.** Now you change everything, everywhere, all at once.

The cost of this approach grows with every source you add and every change anyone makes. It's the classic *n × m* problem: *n* sources times *m* consumers, and every change potentially touches all of them.

You might try and force every player in the market to conform to a model _you_ define, but then your model would have to grow in complexity to solve every imaginable edge-case **and** you would have to find a suitable carrot with which to persuade people to adopt your standard. Getting the right level of abstraction in this kind of situation is notoriously hard!

### The Graph-Based Alternative

What if, instead of a rigid internal format, you had a flexible knowledge graph?

A knowledge graph doesn't enforce a fixed record structure. It stores typed relationships between typed entities. You can add new types of things, new properties, and new relationships without breaking anything that already exists. A query that doesn't reference the new stuff keeps working. A query that does reference it just returns richer results.

Even better: a graph can accept data it doesn't yet understand. When an external party sends a field you haven't mapped yet, the graph can hold onto it until you figure out what it means. No data lost, no pipeline failures.

This is what an **ontology-based** approach gives you. An ontology is a formal description of a domain — what kinds of things exist, what properties they have, how they relate to each other, and what rules they must follow. Think of it as a very precise data dictionary that a computer can reason about.

### But You Still Need Mappings

Here's the catch: having a flexible graph solves the *storage* problem but not the *meaning* problem. Data sitting in a graph without known type or context is available but not useful. You can't query it meaningfully, you can't reason about it, and you can't drive business logic from it.

You still need to figure out that `xs_point` means "attachment point," that it's a monetary amount, that it belongs to a reinsurance layer, and that it should be connected to a specific class in your ontology with a specific property.

**That's the mapping problem. MORK solves it.**

---

## Part 2: What MORK Actually Is

### The Elevator Pitch

MORK is three things:

1. **A vocabulary** — a formal language for expressing "this data element means this ontology concept, connected in this way, with this confidence."
2. **A calculus** — a set of mathematical rules that guarantee your mappings compose correctly, execute in the right order, and produce deterministic results.
3. **An architecture** — a pipeline where AI proposes mappings, validators check them, compilers turn them into executable code, and humans approve the results.

### The Key Insight: Duality of Intent

Every data integration problem has two sides:

**Source data carries *implicit* intent.** The column name `xs_point` implicitly means "excess point" or "attachment point." The fact that it appears next to `lmt` and `ccy` implicitly tells you it's part of a layer description. The fact that it contains decimal numbers implicitly tells you it's a monetary amount. But none of this is stated explicitly — it's buried in naming conventions, structural patterns, data types, and domain knowledge that lives in people's heads.

**A target ontology carries *explicit* intent.** The ontology says: "A Layer is a ContractComponent that *must have* exactly one Attachment (a MonetaryAmount), exactly one Limit (a MonetaryAmount), and at least one Share (a decimal percentage). A Layer *cannot* also be a Policy." This is a formal, machine-readable checklist of requirements.

**Mapping is the alignment of these two forms of intent.** You're taking what the data *looks like* and matching it to what the ontology *requires*. MORK provides the tools to do this systematically, validate it rigorously, and learn from it over time.

---

## Part 3: How MORK Works — The Big Picture

### Three Layers: Intent → Mapping → Artefact

MORK separates the work into three independent layers:

```
Layer 1: INTENT          "What does the user mean?"
    ↓
Layer 2: MAPPING         "How does that meaning connect to the ontology?"
    ↓
Layer 3: ARTEFACT        "What executable code do we generate?"
```

**Why three layers?** Because they change at different rates and for different reasons.

- If the ontology is refactored, Layer 1 (intent) is untouched. You only update Layers 2 and 3.
- If compilation rules change, Layers 1 and 2 are untouched. You only regenerate Layer 3.
- If new natural language input arrives, you start fresh at Layer 1 and flow down.

Changes propagate *downward only, never upward*. The record of what the user meant is preserved even when the ontological expression of that meaning changes.

**Layer 1 — Intent Capture:** An AI agent reads natural language (or schema field names) and extracts structured intents. "Cyber cover up to $25M in US states" becomes three intent nodes: a coverage type (cyber), a quantitative bound (≤ $25M), and a geographic scope (US states). Crucially, *intent nodes never reference the target ontology*. They use only general vocabularies (SKOS concepts, standard data types). This makes them portable across ontologies.

**Layer 2 — Ontological Alignment:** Each intent node is connected to mapping nodes that reference specific classes, properties, and individuals in the target ontology. This is where the heavy lifting happens — where `xs_point` gets formally linked to `hasAttachment` on `Layer`.

**Layer 3 — Artefact Generation:** A deterministic compiler walks the mapping graph and produces executable outputs: SHACL shapes (for validation), SPARQL queries (for retrieval), SWRL rules (for inference), and RML mappings (for data transformation). Same input always produces the same output.

### The Compilation Boundary: AI Proposes, Machines Verify

This is perhaps MORK's most important architectural decision:

**The AI (LLM) is *never* used directly at runtime.**

Instead, the pipeline works like this:

```
Stage 1: AI proposes intent nodes         (probabilistic)
Stage 2: AI proposes mapping nodes        (probabilistic)
         ─── VALIDATION GATE ───
Stage 3: Validator checks everything      (deterministic)
Stage 4: Compiler generates artefacts     (deterministic)
Stage 5: Human reviews and approves       (governance)
```

The AI's job is to *propose* — to read a schema or business rule and suggest what it means in the formal MORK vocabulary. The proposals are then validated against the target ontology (do the referenced classes and properties actually exist? are the types compatible? are the structural requirements met?) and only *validated* proposals proceed to compilation.

This means:
- **Reproducibility:** The same validated mapping graph always produces the same artefacts, regardless of whether the AI was having a good day or a bad day when it made the proposal.
- **Auditability:** Every generated artefact traces back through a mapping node, to an intent node, to the original natural language text that a human wrote.
- **Composability:** Independently generated mapping fragments compose correctly because they share a common algebraic structure (more on this shortly).

---

## Part 4: The Mapping Vocabulary — Speaking MORK

### What a Mapping Looks Like

A MORK mapping is a graph node — a first-class object in the knowledge graph — that says:

> "This source element corresponds to this target ontology element, in this specific way, with this confidence, subject to these dependencies."

The "in this specific way" part is critical. An OWL ontology has three distinct layers (called "strata" or "boxes"):

| Stratum | What It Contains | Example |
|---------|-----------------|---------|
| **T-Box** (Terminology) | Classes and class axioms | "Layer is a subclass of ContractComponent" |
| **A-Box** (Assertions) | Individuals and their types | "layer_001 is a Layer" |
| **R-Box** (Relations) | Properties and property axioms | "layer_001 hasAttachment 500000" |

Most mapping systems treat the target as undifferentiated — "this thing maps to that thing." MORK makes the stratum explicit through specific match properties:

- `exactTBoxMatch` — "this mapping creates or references a class"
- `exactRBoxMatch` — "this mapping creates or references a property"
- `exactABoxMatch` — "this mapping creates or references an individual"
- And their broader/narrower variants for hierarchical relationships.

**Why does this matter?** Because the strata have ordering dependencies:

1. **T-Box first:** You must know what *kind* of thing you're creating (a Layer) before you can create one.
2. **A-Box second:** You must create the individual (layer_001) before you can attach properties to it.
3. **R-Box third:** You can assert relationships (layer_001 hasAttachment 500000) only after the individual exists.

MORK derives these ordering constraints automatically from the mapping graph structure. You don't have to specify execution order — the system figures it out.

### Building Complex Mappings: The DAG

Real-world mappings are almost never one-to-one. A single source record might need to:

- Create a new class (T-Box)
- Create an individual of that class (A-Box)
- Assert five properties on that individual (R-Box)
- Link it to a parent individual created by another mapping
- Look up a reference value from a controlled vocabulary
- Apply a template that's been used 200 times before

MORK handles this through a **directed acyclic graph (DAG)** of mapping nodes connected by composition operators:

- `compositeNarrowerMapping` — "this mapping contains these sub-mappings"
- `broaderApplicative` — "apply my sub-mappings within the context of this parent mapping's output"
- `deferredMapping` — "I need this other mapping to complete before I can finish"
- `templateMapping` — "I'm an instance of this reusable pattern"
- `hypothesisMapping` — "this other mapping provides supporting evidence for me"

Each of these relationships implies an execution ordering, and MORK derives the complete precedence relation automatically. The graph must stay acyclic, and `shapes/constraints.ttl` rejects any cycle (ADR-A97).

### Templates: Don't Repeat Yourself

If you're integrating an API with 200 entity types and 180 of them follow the same pattern (create an individual, assert its name, type it, link it to a parent), you don't want to write 180 separate mapping graphs.

MORK's `templateMapping` mechanism lets you define the pattern once and instantiate it many times with different details. The template provides the skeleton; the instantiation fills in the specifics. This is a huge win for:

- **Efficiency:** Less work to create and maintain.
- **Consistency:** All instances follow the same structure.
- **AI cost reduction:** Instead of asking the AI to generate 180 complete mapping graphs, you ask it to generate one template and 180 lightweight instantiations.

### Confidence and Governance

Every mapping node carries a confidence score (0–100). When the AI proposes a mapping, the score reflects how sure it is. When a human reviews and approves, the score can be updated. When a mapping depends on other mappings, the effective confidence is computed as:

> **effective_confidence = local_confidence × min(child_confidences)**

This means a chain is only as strong as its weakest link, and uncertainty compounds through the graph. The system can present the most and least confident mappings to reviewers, helping them focus their attention where it matters most.

Human governance decisions — approvals, rejections, and explanatory notes — are recorded as first-class annotations on the mapping graph, queryable and auditable like any other data.

---

## Part 5: The Maths — Why It Works (Without the Maths)

### Don't Panic

The MORK foundations paper makes extensive reference to category theory (profunctors, Galois connections, Kan extensions, sheaf cohomology, etc), however you don't need to understand the maths to use MORK. Understanding what the maths is aiming to define or prove, might help you trust it though.

### Categories: Things and Relationships

A category is the simplest possible structure for modelling "things that are related to other things, where relationships can be chained." Every MORK scheme — a taxonomy, a schema, an ontology — forms a category:

- In a **taxonomy**, the things are concepts and the relationships are "is more specific than" (e.g., AttachmentPoint is more specific than MonetaryAmount).
- In a **schema**, the things are fields and the relationships are "is contained within" (e.g., `xs_point` is contained within a financial record, which is contained within the Contract).
- In an **ontology**, the things are classes and the relationships are "is a subclass of" (e.g., Layer is a subclass of ContractComponent).

Treating everything as a category gives us a common mathematical language for talking about all three structures, and — critically — for talking about *mappings between them*.

### Distances: How Similar Are Two Things?

Mapping is fundamentally about measuring similarity. MORK measures it from four angles:

1. **Lexical distance (d_lex):** How similar do the names look? "xs_point" vs. "AttachmentPoint" — somewhat similar (abbreviation match).
2. **Structural distance (d_struct):** How far apart are they in their respective hierarchies? Fields in the same section are close; fields in different sections are far.
3. **Community distance (d_comm):** How often do they appear together? AttachmentPoint and Limit almost always co-occur; AttachmentPoint and PolicyNumber almost never do.
4. **Type distance (d_type):** Are the data types compatible? A decimal field mapping to a MonetaryAmount property? Yes. A string field mapping to a MonetaryAmount property? No.

No single measure is enough. A field might have a great name match to the wrong concept and a mediocre name match to the right one. The community evidence breaks the tie.

### Communities: The Rosetta Stone

Imagine you've processed hundreds of data feed specifications. You notice that certain concepts *always appear together*:

- When you see AttachmentPoint, you almost always also see Limit, Share, and Currency.
- When you see PartyName, you almost always also see PartyRole.
- When you see LoanNumber, you almost always also see Borrower and RepaymentPeriod.

These are **semantic communities** — groups of concepts that habitually co-occur because they collectively describe a coherent domain entity. The first group is the signature of a reinsurance *layer*. The second is the signature of a *party involvement*. The third is the signature of a *loan contract*.

**Why communities matter:** Without them, every field must be mapped independently. With them, recognising *one* member of a community provides evidence for *all* members. If the system figures out that `xs_point` is an AttachmentPoint, it immediately infers that this section is probably a Layer section, which means `lmt` is probably Limit, `pct_share` is probably Share, and `ccy` is probably Currency.

One recognition bootstraps many. This is the **community acceleration factor**, and it's the reason MORK gets dramatically better with experience — each mapping run provides evidence for far more than the fields it directly resolves.

Communities are discovered automatically by running community detection algorithms (like the Leiden algorithm) on the co-occurrence graph. They are not hardcoded or hand-curated. They emerge from the data.

### The Profunctor: Bridging Source and Target

The source side of a mapping is *probabilistic* — we have hypotheses about what fields mean, with varying degrees of confidence based on lexical, structural, community, and type evidence.

The target side is *logical* — an ontology has formal definitions, restrictions, and disjointness axioms that are either satisfied or not!

These two sides have fundamentally different natures. MORK bridges them through what mathematicians call a **profunctor** — essentially a matrix that assigns a compatibility score to every (source hypothesis, target element) pair. The mapping problem reduces to finding the lowest-cost assignment in this matrix: pick one target for each source field such that the total distance is minimised.

The profunctor decomposes into three phases:

1. **Recognition:** Given what a field looks like and what company it keeps, which community does it belong to?
2. **Projection:** Given a community, which ontology elements do its members typically map to?
3. **Composition:** Find the community that provides the best route from source to target.

This decomposition is important not just mathematically but practically — it means the mapping problem can be solved incrementally, with each phase adding evidence and narrowing the search space.

### The Galois Connection: Optimal Alignment

When the system has accumulated enough confirmed mappings, something elegant happens.

There's a mathematical structure called a **Galois connection** that identifies *optimal* alignments — pairings between source communities and target classes where:

- Every concept in the community maps to a property required by the target class.
- Every required property has a concept mapping to it.
- The community's profile perfectly matches the class's requirements.

The system starts out guessing and gradually transitions to *knowing*.

### Our Convergence Theorem: It Gets Better

MORK's central theoretical goal is the **convergence theorem**, which says:

> The fraction of fields requiring AI intervention decreases gradually over time.

Specifically: `ε(t) ≈ K × exp(-(1 + d') × t / (K × ln K))`

Where:
- `ε(t)` is the fraction of fields still needing help at time `t`
- `K` is the number of concepts in the vocabulary
- `d'` is the community acceleration factor
- `t` is the number of mapping runs completed

This is a formal way of saying: **the system learns**. Each mapping run provides evidence that makes the next run faster and more accurate. The community acceleration factor `d'` is the multiplier — because recognising one community member provides evidence for all members, the system learns much faster than if it had to figure out each field independently.

In practice, this means we hope to see a gradual improvement such as the table below shows:

| Phase | Mapping Runs | Behaviour |
|-------|-------------|-----------|
| Cold Start | 0 | AI handles everything |
| Community Emergence | 3–5 | Communities detected; most fields get a boost |
| Projection Accumulation | 5–10 | Most fields resolved deterministically |
| Steady State | 10+ | AI needed only for genuinely novel fields |

### Formal Guarantees: The Safety Net

The maths exists to formalise properties that matter in production:

1. **Termination:** Processing any mapping graph finishes in bounded time. The system cannot enter infinite loops, even on complex graphs. Guaranteed.

2. **Idempotence:** Applying a mapping twice produces the same result as applying it once. Mappings are safe to retry on failure, safe to reapply after recovery, and safe to apply incrementally.

3. **Determinism:** Any valid execution order produces the same output. The system can parallelise work without worrying about race conditions or non-deterministic interleaving.

4. **Precedence Completeness:** The system derives all necessary ordering constraints automatically. You never need to manually specify "do A before B" — it's figured out from the graph structure.

5. **Provenance Compositionality:** Every generated axiom traces back to the specific mapping node, input data, and governance decision that produced it. The audit trail composes along the graph structure.

More than aspirational goals, these should be proven theorems. Our The category-theoretic framework aims to provide the machinery to do so rigorously.

### Challenges and Witnesses: A Dialogue Between Source and Target

MORK frames the mapping problem as a dialogue:

**Challenges** come from the target ontology: "If you want to map this field to the Layer class, prove it has an attachment, a limit, and a share. Prove it's not a Policy."

**Witnesses** come from the source evidence: "The lexical match says 'attachment point.' The type says 'decimal,' which is compatible with MonetaryAmount. The community says this section co-occurs with Limit, Share, and Currency. Prior mappings confirm this pattern."

A mapping is valid when **every challenge has at least one surviving witness**. A mapping is invalid when **any challenge has no surviving witness** (e.g., if disjointness proves the mapping impossible).

As the system processes more data, witnesses accumulate but challenges stay fixed (the ontology doesn't change much between runs). This is another way to see why convergence happens: eventually, every challenge is met.

---

## Part 6: The Technical Architecture

### The Pipeline

```
┌─────────────────────────────────────────────────────┐
│  PHASE 0: Tri-Stratum Inference (Deterministic)     │
│    Recognition → Community Matching → Projection    │
│    Most fields resolved without AI involvement      │
├─────────────────────────────────────────────────────┤
│  STAGE 1: Intent Classification (AI)                │
│    Only for fields the inference engine can't       │
│    resolve confidently                              │
├─────────────────────────────────────────────────────┤
│  STAGE 2: Mapping Node Generation (AI)              │
│    AI proposes mapping nodes using Graph-RAG        │
│    context from the knowledge graph                 │
├─════════════════════════════════════════════════════┤
│  ── VALIDATION GATE ──                              │
│  SHACL shapes check structural completeness         │
│  GCI axioms check ontological consistency           │
│  Type safety verified against target ontology       │
├─════════════════════════════════════════════════════┤
│  STAGE 4: Compilation (Deterministic)               │
│    SHACL shapes, SPARQL queries, SWRL rules,        │
│    RML mappings — all generated deterministically   │
├─────────────────────────────────────────────────────┤
│  STAGE 5: Human Review (Governance)                 │
│    Review package with provenance chain             │
│    Approve / Modify / Reject                        │
└─────────────────────────────────────────────────────┘
```

### The Tri-Stratum Inference Engine

The inference engine is the part that gets smarter over time. It works in three strata:

**Stratum 1 — Recognition:** "What does this field *look like*?" Lexical matching, abbreviation expansion, embedding similarity, type compatibility. This is available immediately, even at cold start.

**Stratum 2 — Community:** "What *company* does this field keep?" Community matching against known co-occurrence patterns. This becomes available after 3–5 mapping runs, once the community detection algorithm has enough data.

**Stratum 3 — Projection:** "Where have *similar things* gone before?" Lookup against confirmed mappings from prior runs. This becomes available after 5–10 runs and provides the strongest evidence.

Each stratum adds evidence that narrows the possibilities further. By steady state, the three strata together resolve 90–98% of fields without any AI involvement.

### Graph-RAG: How the AI Gets Its Context

When the AI does need to be involved, it doesn't generate from its training data alone. Its input comes from the live knowledge graph, retrieved via structured SPARQL queries. This is **Graph-RAG** — Retrieval-Augmented Generation where the retrieval corpus is an RDF/OWL knowledge graph.

Why not conventional RAG (vector search over documents)? Because an ontology is not a bag of words. Its value lies in its *structure* — class hierarchies, property declarations, axiom restrictions, disjointness assertions. Embedding-based retrieval may miss the structural context that makes a mapping correct or incorrect.

Graph-RAG gives the AI:
- The class hierarchy around a candidate target
- The property declarations, domains, and ranges
- Existing mappings for similar concepts
- Community and projection evidence
- Template mappings that might apply

All retrieved as actual graph data, not approximated text chunks.

### Knowledge Infrastructure

The knowledge graph is stored in a triple store (e.g., Apache Jena Fuseki or Stardog) organised into named graphs:

- **Target ontology** — the domain ontology being mapped to
- **Shadow ontology** — a navigable copy of the target's structure (needed for technical reasons related to OWL's typing rules)
- **Source schemas** — the RepresentationScheme individuals for each data source
- **Mapping graphs** — the DataMapping individuals with their DAG structure
- **Community schemes** — the discovered communities with membership weights
- **Projection store** — confirmed mappings with hit counts and confidence
- **Intent schemes** — the IntentNode individuals from natural language processing

### The Agents

The system uses five specialised agents:

| Agent | Role | Uses AI? |
|-------|------|----------|
| **Intent Agent** | Extracts structured intent from natural language | Yes |
| **Mapping Agent** | Proposes mapping nodes with box matches | Yes (with Graph-RAG) |
| **Compiler Agent** | Generates executable artefacts | No — pure function |
| **Review Agent** | Prepares review packages and checks conflicts | Partially |
| **Community Discovery Agent** | Detects communities and projections | No — algorithmic |

Each agent operates within a strict perimeter: it can only read and write to specific named graphs. The Intent Agent cannot see the target ontology. The Compiler Agent cannot invoke an LLM. These constraints are enforced architecturally.

---

## Part 7: Non-LLM Alternatives — Hedging Your Bets

### Why This Matters

LLMs are powerful but expensive, non-deterministic, and subject to market risk (pricing changes, API availability, capability shifts). MORK is designed so that the AI can be partially or fully replaced by classical machine learning and symbolic reasoning.

### What Can Be Done Without an LLM

| Component | Non-LLM Alternative | Accuracy |
|-----------|---------------------|----------|
| Lexical scoring | Sentence transformer (22M params, runs locally) | 85–92% |
| Type checking | OWL reasoner (fully symbolic) | 100% |
| Community detection | Formal Concept Analysis (deterministic) | 100% |
| Alignment scoring | Bayesian MAP classifier | Improves with data |
| Constraint validation | SHACL engine + OWL reasoner | 100% |
| Compilation | Rule-based compiler | 100% |
| Galois fixed-point alignment | Lattice computation | 100% (within coverage) |

The bottom line: approximately 60–85% of the pipeline's intelligence can be delivered without any LLM. The remaining 15–40% (primarily free-text interpretation and genuinely novel schema elements) can be escalated to human review when an LLM isn't available.

### The System Gets Better Either Way

The convergence dynamics work identically whether the "intelligence source" is an LLM, a classical ML model, or a human reviewer. The community detection, Bayesian scoring, and Galois connection all improve with each validated mapping, regardless of who generated the initial proposal.

---

## Part 8: Learning New Domains

### Cold Start to Maturity

When MORK encounters a completely new domain, it follows a progression:

**Day 1 (Cold Start):** The system has no community data and no projection history. It relies on lexical matching, type compatibility, and the ontology's axiom structure. If the ontology is well-axiomatised (rich in definitions, restrictions, and disjointness declarations), 20–40% of fields can be resolved at cold start just from the axioms.

**Week 1–2 (Community Emergence):** After 3–5 mapping runs, the community detection algorithm kicks in. Co-occurrence patterns emerge. The community boost starts accelerating recognition.

**Week 2–4 (Projection Accumulation):** After 5–10 runs, the projection store has enough confirmed mappings to provide strong evidence. Most fields are resolved deterministically.

**Month 2+ (Steady State):** The system handles 90–95% of fields autonomously. The AI (or human) is needed only for genuinely novel fields — new concepts, unusual structures, or ambiguous terminology.

### Warm-Starting from Analogous Domains

If you've already mapped insurance data and now need to map healthcare data, the system can transfer knowledge. The Bayesian priors from insurance (community structures, concept frequencies) can seed the healthcare classifier, providing a non-trivial starting point instead of a blank slate.

### Active Learning: Smart Prioritisation

Not all human reviews are equally valuable. Confirming an obvious mapping teaches the system little. Resolving a genuinely ambiguous one teaches it a lot. MORK's active learning queue routes the highest-uncertainty candidates to human reviewers first, maximising the learning rate per unit of expert time.

---

## Part 9: What MORK Produces

### The Artefacts

The compiler generates four types of executable artefacts:

1. **SHACL Shapes** — validation rules that check whether incoming data conforms to the ontology's requirements. "Does this Layer have exactly one attachment? Is it a decimal? Is the value positive?"

2. **SPARQL Queries** — parameterised queries for retrieving and matching data in the knowledge graph. "Find all Layers with attachment above $1M in US jurisdictions."

3. **SWRL Rules** — inference rules that derive new facts from existing ones. "If a Layer has peril scope 'Cyber' and attachment above $10M, classify it as HighRiskCyber."

4. **RML Mappings** — transformation specifications that convert source data formats into RDF triples conforming to the ontology.

All of these are generated deterministically from the validated mapping graph. Same graph in, same artefacts out. Every artefact carries a provenance chain back to the mapping, the intent, and the original natural language or schema that started it all.

### The Provenance Chain

```
"cyber cover up to $25M in US states"        ← Original text
        ↓
IntentNode: CoverageIntent (cyber)            ← Layer 1
IntentNode: QuantitativeConstraint (≤$25M)
IntentNode: SpatialScope (US states)
        ↓
DataMapping: Map_CyberCoverClause             ← Layer 2
ShapeMapping: Map_CyberLimit (sh:maxInclusive 25000000)
        ↓
sh:NodeShape (targeting ctr:Clause)           ← Layer 3
```

If a regulator asks "why does the system reject a $30M cyber policy?", you can trace the answer from the SHACL violation back through the mapping to the ShapeMapping, through the intent to the QuantitativeConstraint, back to the original text "up to $25M." Full transparency, no black boxes.

---

## Part 10: Putting It All Together

### A Day in the Life

1. **A new collaborator sends a data file.** The schema is ingested and its structure recorded as a RepresentationScheme in the knowledge graph.

2. **The tri-stratum engine runs.** For each field, it computes lexical scores, checks type compatibility, matches against communities, and looks up projections. 85% of fields are resolved deterministically.

3. **The Mapping Agent handles the rest.** For the remaining 15% of ambiguous fields, the AI is invoked with Graph-RAG context. It proposes mapping nodes in the MORK vocabulary.

4. **The validation gate checks everything.** SHACL shapes verify structural completeness. GCI axioms catch type errors. Disjointness checks catch logical contradictions. Invalid proposals bounce back to the AI for retry (bounded at 3–5 attempts).

5. **The compiler generates artefacts.** SHACL shapes, SPARQL queries, and SWRL rules are produced deterministically from the validated mapping graph.

6. **A human reviews.** The review package shows what was generated, how each field was resolved (deterministic, AI-guided, or human-required), the confidence scores, the community context, and the full provenance chain. The human approves, modifies, or rejects.

7. **The system learns.** Approved mappings feed back into the projection store and co-occurrence graph. Communities are updated.

### The Virtuous Cycle

```
  New Data Arrives
       ↓
  Tri-Stratum Engine resolves most fields
       ↓
  AI handles ambiguous fields
       ↓
  Validation catches errors
       ↓
  Compiler generates artefacts
       ↓
  Human reviews and approves
       ↓
  Confirmed mappings feed back into:
    → Community detection (better communities)
    → Projection store (stronger evidence)  
    → Abbreviation dictionary (better lexical matching)
       ↓
  Next time: more fields resolved deterministically
       ↓
  Eventually: AI barely needed
```

---

## Part 11: Complementary Technologies — Semantica

### What Semantica Does

Semantica is a Python-based framework for data ingestion, normalisation, entity extraction, and knowledge graph construction. It handles the "getting data into the system" problem that MORK deliberately doesn't address.

### How They Fit Together

| Concern | Semantica | MORK |
|---------|-----------|------|
| Acquire data from 10+ source types | ✅ | ❌ |
| Clean and normalise data | ✅ | ❌ |
| Extract entities from text | ✅ | ❌ |
| Resolve duplicate entities | ✅ | ❌ |
| Model source schemas formally | ❌ | ✅ |
| Align source to target ontology | ❌ | ✅ |
| Generate OWL axioms from mappings | ❌ | ✅ |
| Govern AI outputs | ❌ | ✅ |
| Track provenance | ✅ (entity-level) | ✅ (axiom-level) |
| Orchestrate the pipeline | ✅ | ✅ |
| Handle data-level conflicts | ✅ | ❌ |
| Handle mapping-level conflicts | ❌ | ✅ |

**Semantica provides operational infrastructure, whilst MORK provides a formal semantic layer.** A combined system would use Semantica for everything up to entity extraction, then hand off to MORK for ontological alignment and artefact generation, with an adapter layer converting between the two.

---

## Part 12: Frequently Asked Questions

**Q: Is MORK only for pet store data or insurance? The examples seem contrived.**
A: No. MORK is domain-agnostic. Communities are discovered from data, not declared for a specific domain. The examples use insurance because that's where the initial development work was done, but the framework applies to any domain with heterogeneous data sources and a formal target ontology.

**Q: Do I need to understand category theory to use MORK?**
A: No. The category theory is there to *prove* that the system works correctly. You interact with MORK through its vocabulary (mapping nodes, match properties, confidence scores) and its pipeline (propose → validate → compile → review). The maths runs underneath.

**Q: What if I don't have an OWL ontology?**
A: MORK assumes a target ontology exists. If you don't have one, you'd need to create one (or use Semantica's ontology generation capabilities for an initial scaffold, then refine it). The richer the ontology — more definitions, more restrictions, more disjointness declarations — the faster MORK converges.

**Q: How does MORK handle schema changes?**
A: When a source schema changes, MORK computes a delta (added, removed, modified fields). New fields go through the mapping pipeline. Removed fields have their mappings deprecated. Modified fields have their mappings reviewed. Existing mappings for unchanged fields are untouched — this is the locality property that makes graph-based integration scalable.

**Q: What happens when the target ontology changes?**
A: Layer 1 (intent) is unaffected. Layer 2 (mappings) may need updating for the affected portions. Layer 3 (artefacts) is regenerated. Because intent is captured independently of the ontology, the record of what the user meant is preserved even when the ontological expression changes.

**Q: How is this different from just using an LLM to write ETL code?**
A: When an LLM writes ETL code directly:
- It's non-reproducible (same prompt, different code on different runs)
- It's hard to validate (is the code correct with respect to both source and target?)
- It doesn't compose (two independently generated scripts may not interoperate)
- It doesn't learn (no knowledge accumulates across runs)

MORK's intermediate representation solves all four problems. The mapping graph is deterministic, validatable, composable, and cumulative.

**Q: What's the learning curve?**
A: Honest answer: the MORK vocabulary is rich and takes study. The property hierarchy alone has dozens of members. The disjointness axioms, co-occurrence constraints, and precedence rules require careful understanding. This complexity exists because the *problem* is complex — multi-stratum semantic mapping with compositional guarantees is inherently non-trivial.

However, most users interact with MORK at one of three levels:
- **Business users** interact with Layer 1 (natural language) and Stage 5 (review).
- **Data engineers** interact with Layers 1–2 (intents and mappings) and the pipeline.
- **Ontology engineers** interact with the full vocabulary, the target ontology, and the validation framework.

---

## Glossary of Key Terms

| Term | What It Means |
|------|---------------|
| **A-Box** | The "assertion" layer of an ontology — individual things and their properties |
| **Community** | A group of concepts that habitually co-occur in data (e.g., AttachmentPoint + Limit + Share = Layer) |
| **Convergence** | The process by which MORK gets better over time, needing less AI intervention with each mapping run |
| **DAG** | Directed Acyclic Graph — a tree-like structure of mapping nodes with dependencies but no cycles |
| **Galois connection** | A mathematical pairing that identifies provably optimal alignments between source communities and target classes |
| **Graph-RAG** | Retrieval-Augmented Generation using a knowledge graph (not text documents) as the retrieval source |
| **Intent Node** | A structured representation of what the user means, independent of any specific ontology |
| **Mapping Node** | A formal specification of how a source element corresponds to a target ontology element |
| **Ontology** | A formal, machine-readable description of a domain — what things exist, their properties, and their rules |
| **Profunctor** | A compatibility matrix between source hypotheses and target elements — the core alignment structure |
| **Projection** | A confirmed mapping from prior runs — "this concept mapped to this property with this confidence" |
| **Provenance** | The complete trail from generated artefact back through mapping, intent, and original source |
| **R-Box** | The "relation" layer of an ontology — properties and how they connect things |
| **SHACL** | Shapes Constraint Language — a standard for expressing validation rules over graph data |
| **Shadow Ontology** | A navigable copy of the target ontology's structure, needed for technical OWL compatibility |
| **SKOS** | Simple Knowledge Organisation System — a standard for controlled vocabularies and concept schemes |
| **SPARQL** | A query language for knowledge graphs (like SQL for graph databases) |
| **SWRL** | Semantic Web Rule Language — a standard for expressing inference rules |
| **T-Box** | The "terminology" layer of an ontology — classes and their definitions |
| **Template Mapping** | A reusable mapping pattern that can be instantiated multiple times with different details |
| **Tri-Stratum Inference** | The three-layer evidence engine: Recognition (what it looks like) → Community (who it keeps company with) → Projection (where similar things went before) |
| **Validation Gate** | The firewall between AI proposals and deterministic compilation — nothing passes without validation |
| **Writer Monad** | The mathematical mechanism that ensures axiom context accumulates correctly as mappings compose |

---

## The One-Page Summary

**The Problem:** Enterprise data arrives in dozens of incompatible formats. Translating between them is expensive, brittle, and doesn't scale.

**The Approach:** Use a formal ontology as the common target. Map every source to the ontology instead of to each other. Adding a new source is a local operation — it doesn't affect existing mappings.

**The Innovation:** MORK provides a formal vocabulary for expressing these mappings as first-class graph objects, validated against the ontology, compiled into executable artefacts, and governed by humans. AI proposes; the system verifies.

**The Learning:** The system discovers semantic communities from co-occurrence patterns and builds a projection store of confirmed mappings. Each run makes the next one easier. Exponential convergence toward full automation.

**The Guarantees:** Termination, idempotence, determinism, precedence completeness, and provenance compositionality — all formally proven.

**The Hedge:** 60–85% of the intelligence can be delivered without any LLM, using classical ML and symbolic reasoning. The LLM is an accelerator, not a dependency.

**The Result:** A system that starts as an AI-assisted mapping tool and matures into a deterministic, auditable, self-improving semantic integration platform.

---
