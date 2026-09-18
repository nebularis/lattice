---
layout: default
title: "The LATTICE Field Guide"
description: "A practical guide to Surface, Eligibility, MORK, and governed compilation."
---

<style>
:root {
  color-scheme: dark;
  --book-bg: #070a12;
  --book-panel: rgba(17, 25, 43, 0.78);
  --book-text: #eef4ff;
  --book-muted: #a7b4ca;
  --book-line: rgba(169, 190, 230, 0.18);
  --book-accent: #9df7d7;
  --book-blue: #8fb7ff;
  --book-purple: #d9a6ff;
}
html, body {
  background:
    radial-gradient(circle at 12% 0%, rgba(157,247,215,.13), transparent 28rem),
    radial-gradient(circle at 88% 8%, rgba(143,183,255,.14), transparent 26rem),
    linear-gradient(135deg, #05070d 0%, #09101c 48%, #0b0f1a 100%);
  color: var(--book-text);
}
.book::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(to bottom, black, transparent 82%);
}
.book {
  max-width: 1120px;
  margin: 0 auto;
  padding: 3rem 1.25rem 6rem;
  color: var(--book-text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.7;
}
.book a { color: var(--book-accent); }
.book .book-hero {
  padding: 3.5rem 0 3rem;
  border-bottom: 1px solid var(--book-line);
}
.book .eyebrow {
  color: var(--book-accent);
  font-size: .8rem;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}
.book h1, .book h2, .book h3 { line-height: 1.1; }
.book h1 {
  max-width: 900px;
  margin: .8rem 0 1.2rem;
  font-size: clamp(2.8rem, 7vw, 6.5rem);
  letter-spacing: -.06em;
  background: linear-gradient(120deg, #fff, var(--book-accent) 42%, var(--book-blue) 78%, var(--book-purple));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.book .dek { max-width: 760px; color: var(--book-muted); font-size: 1.25rem; }
.book .book-nav {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: .7rem;
  margin: 2rem 0 3rem;
}
.book .book-nav a, .book .callout, .book table, .book pre {
  border: 1px solid var(--book-line);
  background: var(--book-panel);
  border-radius: 14px;
}
.book .book-nav a { padding: .85rem 1rem; text-decoration: none; }
.book .book-nav a:hover { border-color: rgba(157,247,215,.55); }
.book h2 { margin-top: 4rem; padding-top: 1rem; border-top: 1px solid var(--book-line); font-size: 2.1rem; }
.book h3 { margin-top: 2.2rem; color: var(--book-accent); }
.book .callout { padding: 1rem 1.2rem; margin: 1.4rem 0; color: var(--book-muted); }
.book .callout strong { color: var(--book-text); }
.book pre { padding: 1rem 1.2rem; overflow-x: auto; color: #d9e7ff; }
.book code { color: #d9e7ff; }
.book table { width: 100%; border-collapse: separate; border-spacing: 0; overflow: hidden; margin: 1.2rem 0; }
.book th, .book td { padding: .75rem .85rem; text-align: left; vertical-align: top; border-bottom: 1px solid var(--book-line); }
.book th { color: var(--book-accent); background: rgba(157,247,215,.06); }
.book tr:last-child td { border-bottom: 0; }
.book blockquote { margin: 1.4rem 0; padding: .8rem 1.2rem; border-left: 3px solid var(--book-accent); color: var(--book-muted); }
.book .chapter { color: var(--book-blue); font-size: .78rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.book .small { color: var(--book-muted); font-size: .92rem; }
@media (max-width: 720px) {
  .book { padding-top: 1.5rem; }
  .book h2 { font-size: 1.75rem; }
  .book table { display: block; overflow-x: auto; }
}
</style>

<article class="book">
  <header class="book-hero">
    <div class="eyebrow">A field guide to governed semantics</div>
    <h1>The LATTICE Field Guide</h1>
    <p class="dek">
      How to move from declarations to trusted execution using Surface, Eligibility,
      MORK, and deterministic compiler backends.
    </p>
    <p class="small">A practical user guide for authors, compiler builders, reviewers, and operators.</p>
  </header>

  <nav class="book-nav" aria-label="Book contents">
    <a href="#orientation">1. Orientation</a>
    <a href="#foundations">2. The semantic stack</a>
    <a href="#surface">3. Surface</a>
    <a href="#eligibility">4. Eligibility</a>
    <a href="#mork">5. MORK</a>
    <a href="#compilation">6. Compilation</a>
    <a href="#worked">7. Worked examples</a>
    <a href="#operations">8. Operating the system</a>
    <a href="#architecture">9. Boundaries and choices</a>
    <a href="#roadmap">10. Where next</a>
  </nav>

  <section id="orientation">
    <div class="chapter">Chapter 1</div>
    <h2>Orientation</h2>
    <p>
      LATTICE is a semantic substrate for governed systems. It is designed for situations
      where a document, policy, contract, protocol, or operational rule must become more
      than text. It must become a graph that can be inspected, validated, transformed,
      queried, and eventually executed without losing the thread back to its source.
    </p>
    <p>
      The central move is simple:
    </p>
    <pre><code>meaningful declarations
        |
        v
validated graph
        |
        v
compiled mode of operation
        |
        v
runtime answers with provenance</code></pre>
    <p>
      The framework deliberately separates semantic authority from computational convenience.
      A source declaration remains the thing that says what is true. A generated surface,
      query, shape, rule, or runtime plan is a derived way of asking questions about it.
    </p>
    <div class="callout">
      <strong>The guiding question:</strong> can a reviewer explain what the system believes,
      why it believes it, which compiler produced the operational form, and what must be
      regenerated when an input changes?
    </div>
    <h3>Who this guide is for</h3>
    <ul>
      <li><strong>Ontology authors</strong> who declare concepts, constraints, conditions, and behaviours.</li>
      <li><strong>Projection authors</strong> who need efficient or transformed views of an existing graph.</li>
      <li><strong>Compiler authors</strong> who lower validated mapping graphs into executable targets.</li>
      <li><strong>Operators</strong> who need freshness, invalidation, provenance, and release gates.</li>
    </ul>
    <h3>The shortest useful vocabulary</h3>
    <table>
      <thead><tr><th>Term</th><th>Meaning</th></tr></thead>
      <tbody>
        <tr><td>Declaration</td><td>An authored graph statement that defines domain meaning.</td></tr>
        <tr><td>Surface</td><td>A generated, query-facing restatement of declared graph facts.</td></tr>
        <tr><td>Eligibility</td><td>A declarative model for conditions, questions, and decisions.</td></tr>
        <tr><td>MORK</td><td>A machine-facing mapping graph that records how mappings should compile.</td></tr>
        <tr><td>Artefact</td><td>A generated output such as a SHACL shape, SPARQL query, SWRL rule, or RML map.</td></tr>
        <tr><td>Profile</td><td>The versioned policy under which a generated product is produced.</td></tr>
      </tbody>
    </table>
  </section>

  <section id="foundations">
    <div class="chapter">Chapter 2</div>
    <h2>The semantic stack</h2>
    <p>
      LATTICE is layered because different kinds of meaning have different owners.
      Foundation handles identity, provenance, governance, and versioning. Vocabulary binds
      domain-owned concept schemes into reusable contracts. Quantification handles values,
      ranges, bounds, units, and recurrence. Party, Instrument, Eligibility, and Behaviour
      add progressively more applied semantics.
    </p>
    <table>
      <thead><tr><th>Layer</th><th>Question</th><th>Typical output</th></tr></thead>
      <tbody>
        <tr><td>Foundation</td><td>What is this artefact and who governs it?</td><td>Identity, version, evidence, governance state.</td></tr>
        <tr><td>Vocabulary</td><td>Which concepts are available?</td><td>Scheme contracts and implementation-owned SKOS schemes.</td></tr>
        <tr><td>Quantification</td><td>What does a value mean numerically?</td><td>Quantities, bounds, ranges, value spaces.</td></tr>
        <tr><td>Party</td><td>Who participates and in what role?</td><td>Actors, roles, participation, obligation direction.</td></tr>
        <tr><td>Eligibility</td><td>Does the evidence satisfy the condition?</td><td>Questions, decisions, permitted, denied, undetermined.</td></tr>
        <tr><td>Behaviour</td><td>How does a governed system change state?</td><td>Triggers, guards, transitions, effects, allowances.</td></tr>
        <tr><td>Instrument</td><td>Which applied domain object carries the rules?</td><td>Contracts, clauses, obligations, applied structures.</td></tr>
      </tbody>
    </table>
    <h3>Declaration versus realisation</h3>
    <p>
      A declaration tells the system what a thing means. A realisation decides how to answer
      a question efficiently or how to compile a semantic graph into another formalism.
      Direct SPARQL, SHACL, reasoning, materialisation, and generated surfaces are peer
      realisation strategies. None becomes the source of truth merely because it is faster.
    </p>
    <blockquote>
      A generated product can make a question easier to answer. It must not silently become
      the evidence for a decision that belongs to the authored declaration.
    </blockquote>
    <h3>Literate specifications</h3>
    <p>
      Layer READMEs are literate specifications. Their Turtle blocks are extracted into
      `spec/`, `vocab/`, and `shapes/` artefacts. This gives the prose and machine-readable
      files one source of truth.
    </p>
    <pre><code>python3 tools/literate_extract.py surface/README.md \
  --layer surface --root . \
  --shapes shapes/structural.ttl shapes/constraints.ttl --check</code></pre>
    <p>
      Run this check whenever a README, ontology, vocabulary, or shape changes. Extraction
      drift is a semantic defect, not a formatting problem.
    </p>
  </section>

  <section id="surface">
    <div class="chapter">Chapter 3</div>
    <h2>Surface: making graph questions cheap</h2>
    <p>
      Surface exists because a correct graph can still be an awkward graph to query. A
      consumer may need to traverse a remote vocabulary, walk a hierarchy, follow a long
      structural path, or repeat the same derivation at a hot runtime boundary.
    </p>
    <p>
      A surface is a generated local restatement. It adds symbols and assertions that make
      a declared class of question answerable by direct lookup, while preserving the source
      as the semantic authority.
    </p>
    <h3>Promotion</h3>
    <p>
      Promotion reads a value at the end of a declared path and puts it directly on the
      carrier. It is the right tool for an unbounded value space such as currency, dates,
      identifiers, or a computed property that has already been produced by another stage.
    </p>
    <pre><code>Subscription
  --hasPlan--&gt; Plan
  --hasPricing--&gt; Pricing
  --inCurrency--&gt; EUR

becomes a generated direct assertion:

Subscription --subscriptionCurrency--&gt; EUR</code></pre>
    <p>
      A promotion contract names the carrier, path, target property, fidelity, realisation
      mode, namespace, and profile.
    </p>
    <pre><code>ex:subscription-currency a srf:PromotionContract ;
    srf:contractKey "subscription-currency" ;
    srf:carrier saas:Subscription ;
    srf:hasPathStep ex:step-0, ex:step-1, ex:step-2 ;
    srf:promotesTo saas:subscriptionCurrency ;
    srf:sourceFidelity srf:ExactSource ;
    srf:realisationMode srf:Materialised ;
    srf:targetNamespace &lt;https://example.org/saas/generated/&gt; ;
    srf:surfaceProfile ex:default-profile .</code></pre>
    <h3>Indexing</h3>
    <p>
      Indexing answers the inverse question: which carriers have this value? It may create
      nominal classes, materialised membership assertions, direct properties, or closure
      relations over a declared hierarchy.
    </p>
    <table>
      <thead><tr><th>Form</th><th>Use it when</th><th>Runtime shape</th></tr></thead>
      <tbody>
        <tr><td>NominalClass</td><td>The population is bounded and enumerable.</td><td>`?carrier a generated:ValueClass`</td></tr>
        <tr><td>MembershipAssertion</td><td>You need answers without a reasoner.</td><td>Materialised `rdf:type` assertions.</td></tr>
        <tr><td>ClosureRelation</td><td>Ancestor retrieval is a real query pattern.</td><td>`?carrier generated:matches ?ancestor`</td></tr>
        <tr><td>DirectProperty</td><td>The value space is open-ended or large.</td><td>`?carrier generated:property ?value`</td></tr>
      </tbody>
    </table>
    <h3>Hierarchical closure</h3>
    <p>
      Closure is never assumed. A contract declares its basis, such as `skos:broader`, and
      its scope. The generator checks for cycles, includes the value itself, and emits only
      ancestors within the declared population scope.
    </p>
    <pre><code>SiteReliability --skos:broader--&gt; Engineering --skos:broader--&gt; Technical

Generated retrieval:
RoleAssignment --matchesJobFamily--&gt; SiteReliability
RoleAssignment --matchesJobFamily--&gt; Engineering
RoleAssignment --matchesJobFamily--&gt; Technical</code></pre>
    <h3>Fidelity and X6</h3>
    <p>
      Surface distinguishes exact restatement from approximation. `ExactSource` and
      `CrosswalkExact` may be materialised onto an authored property. A lossy or inexact
      result must land on a generated property so it cannot masquerade as native domain
      truth. Definition-only property chains may not target authored properties.
    </p>
    <div class="callout">
      <strong>Practical rule:</strong> exact into the authored signature may be useful.
      Approximate into the authored signature is misleading. X6 keeps those cases apart.
    </div>
    <h3>Projection</h3>
    <p>
      Promotion and Index are direct restatements. Projection is for intent that needs
      construction, derivation, joins, or expansion. A Projection contract does not emit
      SPARQL or SHACL itself. It lowers into MORK, where a backend compiler can produce the
      target artefact.
    </p>
    <pre><code>ex:subscription-arr a srf:ProjectionContract ;
    srf:projectionKind srf:DerivationProjection ;
    srf:carrier saas:Subscription ;
    srf:hasRoleBinding ex:price, ex:frequency, ex:target ;
    srf:backendPolicy ex:deterministic-policy .</code></pre>
    <h3>Surface profiles</h3>
    <p>
      A profile fixes generator version, canonicalisation version, entailment regime,
      naming normalisation, symbol mode, population budget, and permitted stack depth.
      Changing a profile changes what an artefact means or how it is named, so it is a
      regeneration event.
    </p>
  </section>

  <section id="eligibility">
    <div class="chapter">Chapter 4</div>
    <h2>Eligibility: from conditions to decisions</h2>
    <p>
      Eligibility is declarative. It describes the condition, the evidence to inspect, the
      matching strategy, the required ranges or concepts, and the decision vocabulary. It
      does not pretend that OWL entailment alone can perform interval arithmetic or decide
      what missing evidence means.
    </p>
    <h3>The basic shape</h3>
    <pre><code>Condition
  --matchStrategy--&gt; IntervalContainment
  --requiredRangeSet--&gt; [700, 850]

Question
  --forCondition--&gt; Condition
  --candidateRangeSet--&gt; [720, 810]

EligibilityDecision
  --hasQuestion--&gt; Question
  --decisionValue--&gt; Permitted</code></pre>
    <h3>Three-valued outcomes</h3>
    <table>
      <thead><tr><th>Outcome</th><th>Meaning</th></tr></thead>
      <tbody>
        <tr><td>Permitted</td><td>The available evidence demonstrates satisfaction.</td></tr>
        <tr><td>Denied</td><td>The available evidence demonstrates failure.</td></tr>
        <tr><td>Undetermined</td><td>Evidence is missing, malformed, incompatible, or insufficient.</td></tr>
      </tbody>
    </table>
    <p>
      Never collapse Undetermined into Denied by accident. Missing evidence is a semantic
      state that downstream policy may interpret later.
    </p>
    <h3>Interval containment</h3>
    <p>
      The current executable slice supports linear interval containment in one value space.
      A candidate range is permitted when every candidate range is contained by at least
      one required range. Open and closed endpoints are respected.
    </p>
    <pre><code>Required:  [700, 850]
Candidate: [720, 810]   =&gt; Permitted
Candidate: [650, 810]   =&gt; Denied
Candidate: missing      =&gt; Undetermined</code></pre>
    <h3>Eligibility and Surface together</h3>
    <p>
      Eligibility says what must be decided. Surface can make the evidence easier to reach,
      or can build a governed query-facing form around the result. A surface is a
      realisation detail recorded on the decision. It does not become the decision's
      authority.
    </p>
  </section>

  <section id="mork">
    <div class="chapter">Chapter 5</div>
    <h2>MORK: the machine-facing mapping graph</h2>
    <p>
      MORK is designed for machines, including mapping agents and LLMs. It is where the
      maximum useful information about a mapping is captured for review, versioning,
      governance, and deterministic compilation.
    </p>
    <p>
      A MORK mapping can record its target, parameter bindings, dependencies, templates,
      provenance, jurisdiction, effective period, confidence, and governance state. This
      is more detail than most domain authors should have to write by hand. Surface is the
      author-facing layer that lowers into it.
    </p>
    <h3>Mapping families</h3>
    <table>
      <thead><tr><th>Mapping</th><th>Produces</th></tr></thead>
      <tbody>
        <tr><td>DataMapping</td><td>General mapping intent and dependency anchor.</td></tr>
        <tr><td>ShapeMapping</td><td>Structured SHACL definitions.</td></tr>
        <tr><td>RuleMapping</td><td>Structured SWRL implications.</td></tr>
        <tr><td>TransformMapping</td><td>RML or R2RML graph transformations.</td></tr>
        <tr><td>ProjectionMapping</td><td>Generated projection class definitions and provenance.</td></tr>
        <tr><td>QueryTemplate</td><td>Parameterized query text with mapping metadata.</td></tr>
      </tbody>
    </table>
    <h3>Why the graph matters</h3>
    <p>
      A serialized rule is difficult to govern. A structured mapping graph can be queried:
      which source caused this rule, what target class does it address, which other mapping
      must run first, what confidence was assigned, and when does it become effective?
    </p>
    <h3>Governance states</h3>
    <p>
      Draft mappings may be proposed. Reviewed mappings have passed human or policy
      review. Active mappings may compile for production. Superseded mappings remain useful
      historical records but should not silently become current.
    </p>
    <p>
      The MORK governance model is Foundation-aligned. Mapping version, identity,
      governance state, supersession, and effective dates are part of the compilation
      boundary, not comments hidden outside the graph.
    </p>
  </section>

  <section id="compilation">
    <div class="chapter">Chapter 6</div>
    <h2>Compilation: one semantic core, many targets</h2>
    <p>
      The compiler pipeline is deliberately staged:
    </p>
    <pre><code>validate
  - structural shapes
  - governance state
  - dependencies
        |
        v
normalise
  - resolve parameters
  - build executable IR
        |
        v
lower
  - Surface contracts to MORK
        |
        v
compile
  - target-specific backend
        |
        v
emit
  - structured artefact and provenance
        |
        v
verify
  - parser, SHACL, parity, determinism</code></pre>
    <h3>Shared executable IR</h3>
    <p>
      Eligibility backends must not each reinterpret `IntervalContainment`. The shared IR
      captures the operation once. SPARQL, SHACL, and SWRL then become backend projections
      of the same semantic plan.
    </p>
    <h3>SPARQL</h3>
    <p>
      SPARQL is the best first backend for complete decisions and diagnostics. It can
      distinguish missing evidence from known failure and aggregate multiple conditions.
    </p>
    <h3>SHACL</h3>
    <p>
      SHACL is excellent for readiness and validation reports. A SHACL report is not by
      itself an Eligibility decision, so an adapter must map validation results to the
      three-valued decision vocabulary.
    </p>
    <h3>SWRL</h3>
    <p>
      SWRL is useful for positive monotonic classification. It cannot safely infer denial
      or indeterminacy from absence of evidence under open-world semantics. The current
      backend therefore emits positive `Permitted` rules only.
    </p>
    <h3>RML</h3>
    <p>
      RML is the graph-ingestion side of the same story. A MORK mapping can describe how
      JSON, CSV, XML, or another representation becomes RDF aligned with a target ontology.
      The mapping remains inspectable before the transformation runs.
    </p>
    <h3>Determinism and provenance</h3>
    <p>
      Same validated graph plus same compiler profile must produce the same identifiers,
      dependency order, semantic hashes, and artefact content. Every generated plan or
      artefact should point back to its source contract, mapping, and declaration nodes.
    </p>
  </section>

  <section id="worked">
    <div class="chapter">Chapter 7</div>
    <h2>Worked examples</h2>
    <h3>Example A: hierarchical job families</h3>
    <p>
      Start with a scheme contract bound to a job-family scheme. The scheme contains
      `Technical`, `Engineering`, `SiteReliability`, and a wildcard. A role assignment
      points to `SiteReliability`.
    </p>
    <p>
      An Index contract declares `NominalClass`, `MembershipAssertion`, and
      `ClosureRelation`, with `skos:broader` as its basis. The compiler emits a local
      family of generated classes, direct membership assertions, and ancestor matches.
    </p>
    <pre><code>python3 -m tools.surface compile \
  --contracts surface/examples/employment-job-family.ttl \
  --out surface/execution \
  --verify-determinism --parity</code></pre>
    <p>
      This is the model for hierarchical retrieval. The query can use the generated
      closure relation instead of walking the vocabulary hierarchy at runtime.
    </p>
    <h3>Example B: multi-hop currency promotion</h3>
    <p>
      A subscription reaches its currency through plan and pricing nodes. The promotion
      is exact and materialised. It does not enumerate currencies or mint one class per
      currency. It emits a direct property suitable for lookup.
    </p>
    <pre><code>python3 -m tools.surface parity \
  --contracts surface/examples/saas-subscription-currency.ttl</code></pre>
    <p>
      This is the pattern to use for open-ended values, long paths, and exact convenience
      properties.
    </p>
    <h3>Example C: inexact crosswalk</h3>
    <p>
      The clinical trial example crosses a mapping relation whose fidelity is inexact.
      The generated result remains queryable, but it is advisory and does not pretend to
      be an authored fact in the target vocabulary.
    </p>
    <h3>Example D: a richer Projection contract</h3>
    <p>
      The SaaS annual recurring revenue example binds multiple evidence properties to a
      derivation projection. Surface lowers the intent into MORK. A later backend can
      choose SPARQL or another target according to the backend policy.
    </p>
    <pre><code>python3 -m tools.surface lower \
  --contracts surface/examples/saas-subscription-arr-projection.ttl \
  --out /tmp/subscription-arr-mapping.ttl</code></pre>
    <h3>Example E: Eligibility interval</h3>
    <p>
      The current compiler reads the interval declaration, creates a shared plan, and
      emits SPARQL, SHACL, or SWRL artefacts.
    </p>
    <pre><code>python3 -m tools.mork_compilers.cli compile-condition \
  --declarations eligibility/examples/interval-containment.ttl \
  --condition https://example.org/lattice/eligibility/minimum-credit-condition \
  --backend sparql \
  --out /tmp/eligibility-sparql.ttl</code></pre>
  </section>

  <section id="operations">
    <div class="chapter">Chapter 8</div>
    <h2>Operating the system</h2>
    <h3>Install the environment</h3>
    <pre><code>python3 -m venv .venv
. .venv/bin/activate
python -m pip install -c requirements-lock.txt ".[reasoning]"</code></pre>
    <h3>Run the core checks</h3>
    <pre><code>python3 -m unittest tools.surface.test_surface tools.mork_compilers.test_mork_compilers -q
python3 tools/literate_extract.py surface/README.md \
  --layer surface --root . \
  --shapes shapes/structural.ttl shapes/constraints.ttl --check
python3 -m tools.phase8_conformance</code></pre>
    <h3>Check freshness</h3>
    <p>
      A generated surface is stale when any read-set digest differs from the current
      source. The Phase 7 planner computes minimal impact for source changes, MORK mapping
      changes, generated artefacts, profile changes, and canonicalisation changes.
    </p>
    <pre><code>python3 -m tools.surface check \
  --manifest surface/execution/job-family/manifest.ttl \
  --contracts surface/examples/employment-job-family.ttl</code></pre>
    <h3>Regeneration policy</h3>
    <table>
      <thead><tr><th>Change</th><th>Regeneration scope</th></tr></thead>
      <tbody>
        <tr><td>Instance assertion</td><td>Affected materialised assertions.</td></tr>
        <tr><td>Scheme membership</td><td>Contract symbol inventory and dependent closure.</td></tr>
        <tr><td>Hierarchy basis</td><td>Closure outputs and dependent matches.</td></tr>
        <tr><td>Projection contract</td><td>Lowered mapping and dependent MORK mappings.</td></tr>
        <tr><td>Profile</td><td>All surfaces and artefacts using that profile.</td></tr>
        <tr><td>Canonicalisation</td><td>Full estate rehash and regeneration.</td></tr>
      </tbody>
    </table>
    <h3>Reading failures</h3>
    <ul>
      <li><strong>Parity failure:</strong> the generated surface disagrees with its source.</li>
      <li><strong>Governance failure:</strong> a mapping lacks the state, identity, or effective metadata required for its mode.</li>
      <li><strong>Undetermined:</strong> Eligibility lacks enough compatible evidence. Do not silently translate this to denial.</li>
      <li><strong>Unsupported entailment:</strong> the compiler refuses a regime it does not execute rather than emitting an under-entailed result.</li>
      <li><strong>Collision:</strong> two values would mint the same generated identifier. Change the naming policy or use digest naming.</li>
    </ul>
  </section>

  <section id="architecture">
    <div class="chapter">Chapter 9</div>
    <h2>Boundaries and design choices</h2>
    <h3>What Surface does not do</h3>
    <p>
      Surface is not a replacement for a full semantic compiler. It does not, by itself,
      create arbitrary domain nodes, perform unrestricted multi-source derivation, resolve
      datatype literals through concept joins, or expand one source node into several
      coordinated behavioural nodes.
    </p>
    <p>
      Those are MORK-backed Projection and backend compiler concerns. Surface makes them
      easier to author by recording the high-level intent and role bindings.
    </p>
    <h3>CSO to FBO</h3>
    <p>
      A full CSO to FBO compiler must create behavioural entities such as tanks, actions,
      qualifiers, claims, and spans. It must perform structural derivation, value
      resolution, one-to-many expansion, and completeness checks.
    </p>
    <p>
      Once those FBO entities exist, Surface is a strong fit for exact restatement,
      hierarchical indexing, closure materialisation, governed acceleration, and freshness.
      This separation preserves X6 instead of weakening it to compensate for a different
      compiler's missing capabilities.
    </p>
    <h3>What remains intentionally deferred</h3>
    <ul>
      <li>Range partition semantics and bucket faithfulness.</li>
      <li>Surface stacking beyond depth one.</li>
      <li>External index admission and freshness semantics.</li>
      <li>Reasoned entailment regimes beyond asserted `NoEntailment`.</li>
      <li>Profile-level Eligibility artefacts and runtime result tracking.</li>
      <li>Full CSO-to-FBO semantic compilation.</li>
    </ul>
  </section>

  <section id="roadmap">
    <div class="chapter">Chapter 10</div>
    <h2>Where next</h2>
    <p>
      The next work should deepen the verified system rather than multiply its vocabulary.
    </p>
    <ol>
      <li>Resolve the Foundation boundary for generic derived artefact primitives.</li>
      <li>Decide whether to adopt the domain-facing Executable Projection Contract.</li>
      <li>Confirm MORK namespace and toolchain assumptions.</li>
      <li>Add profile identity materialisation if the Foundation decision permits it.</li>
      <li>Implement Eligibility profile aggregation and runtime result tracking.</li>
      <li>Add broader Projection and Behaviour conformance cases.</li>
      <li>Add declared SWRL and OWL reasoner validation.</li>
      <li>Begin a pilot migration for one domain-bound Eligibility projection and one CSO-to-FBO Projection scenario.</li>
    </ol>
    <div class="callout">
      <strong>Definition of done:</strong> an author can declare projection intent without
      writing raw MORK internals, the system can lower and govern that intent, generated
      artefacts can be validated and traced back to source declarations, and stale outputs
      can be regenerated without rebuilding unrelated parts of the estate.
    </div>
    <p class="small">
      Further reference: <a href="./GOVERNANCE.md">Governance</a>,
      <a href="./architecture/">Architecture</a>,
      <a href="./adr/">ADRs</a>,
      <a href="../surface/docs/current_plan.md">Current projection plan</a>,
      and the <a href="https://github.com/nebularis/lattice">source repository</a>.
    </p>
  </section>
</article>
