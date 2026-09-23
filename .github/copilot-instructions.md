# Instructions for Copilot

## Agentic Development Contract

This governs how implemented code is validated. It exists to conserve tokens and keep the human in control of what runs.

The general approach is that we work iteratively together, with the agent suggesting what we should build next, and the human verifying the approach along the way.

### Design First

Before we even sketch a plan for implementing/coding, we must consult the architecture and design records and produce a proposed Architecture Decision Record, which should also include either a design sketch OR be linked to a detailed design entry in the `docs/architecture/solution-design-specification.md' file. 

At all times, the following files MUST be kept up to date with changes:

- the root directory `README.md` (any new structure/folders/projects must be documented here)
- the project-level `README.md` files (significant changes must be documented appropriately)
- the ADR catalogue in `docs/architecture/decisions`
- the ontology architecture `docs/architecture/ontology-architecture.md'
- the platform specification `docs/architecture/solution-design-specification.md'
- the data architecture `docs/architecture/data-architecture.md'
- the ux design `docs/architecture/ux-design.md'

### Planning Mode

When writing a plan for coding, the plan must be VERY detailed. This allows us to ensure alignment between the architecture, the design specification, and the plan.

Lattice is a framework. It should not impose design decisions on its users unless they are materially vital for correctness. Instead, Lattice should provide the user with options and, where possible, configuration and capabilities that operate on the user's chosen configuration set.

### Two Agentic Execution Modes: Default and Autonomous

In both modes, the Agentic Development Contract still applies. The agent should not run off and build multiple sub-systems, but should follow the `Agentic Development Approach` instead.

The two modes are explained next.

#### Default Mode - use this unless other instructed

- **Default** mode is write, then hand off. After implementing a change, do not run build, test, compile, or integration commands yourself to validate it. Cheap static diagnostics (language-server error checks, lint-on-save) are fine, they produce no large log output.
- End every implementation turn with an explicit "Commands to run" block: exact commands, the directory to run them from, and what a pass looks like.
- Wait for the human to run those commands and report the result before assuming success or making further changes on that assumption.
- If the human reports a failure, diagnose from the pasted output. Do not re-run the command yourself to reproduce it, ask for more output if what was pasted is insufficient. The human in the loop is key to this mode.
- This applies to every ecosystem in this repository: Maven/Java, Python/pytest, Yarn/Playwright, Docker Compose, database migrations, and any future build or test tooling.
- Only run a command yourself when the human explicitly asks you to, or when a single-file syntax check is faster than an explanation and stays within the current tool call's scope.
- Never state a change "passed," "works," or "is validated" unless the human reported that the commands succeeded, or you ran them because the human explicitly asked you to.

#### Autonomous Mode - use this only when explicitly instructed

- **Autonomous** mode allows the agent to run build, test, compile, or integration commands itself to validate changes. Use this mode only when explicitly allowed by the human.
- The human trusts your judgment and expects accurate self-validation, testing, and verification in this mode.
- NB: **THIS MODE DOES NOT OVERRIDE THE Agentic Development Contract**: you must still check in with the human when making design decisions.

### Pause For Architectural Guidance

In BOTH **Default** and **Autonomous** modes, do not make design decisions unilaterally without consulting the human for architectural guidance. In this way, we will work together on alignment and ensure that ADR logs are available to you and other agents, that help shape our understanding as we work together.

## Repository Topology and Documentation Governance

If your user requests a named "unit of work", read:

1. Any relevant accepted architecture decision in `docs/architecture/decisions/`
2. The unit plan in `docs/developer/plans/<unit>.md`
3. The unit status record in `docs/developer/status/<unit>.md`
4. Any active human review request in `docs/developer/review/<unit>-review.md`

Do not treat a plan as a status log. Do not begin a physical path move before the applicable ADR and path manifest are approved.

When trying to estimate scope, the measure should not be `agent days`, but rather, aim to estimate the cost in `tokens` or `ai-credits`. We can validate this after implementation and the record of estimated and actual might help with future planning.

### Repository Topology

- `ontology/` owns semantic assets only: normative ontology sources, shapes, vocabularies, projections, semantic examples, semantic fixtures, and semantic documentation.
- `tools/` owns executable reference implementations and developer-facing toolchains.
- MORK and SPC semantic assets live under `ontology/mork` and `ontology/spc`. Their executable projects live under `tools/mork` and `tools/spc`.
- `workers/` is a deployable asynchronous runtime package and remains a top-level root.
- `platform/`, `apps/`, `packages/`, `contracts/`, `deployment/`, and `test/` remain top-level roots unless an accepted ADR says otherwise.
- DO NOT introduce new directory structure, especially at the repo root, without an accepted architecture decision.

### Documentation Lifecycle

Most ideas start out life as `sketches`. Some may be captured as a plan rather than a sketch. Each active unit has one stable identifier, such as `iri-policy-p013`.

- `docs/developer/sketches/<unit>.md` defines the broad shape of an idea. Sketches can become plans. A sketch can be updated freely. Once a sketch becomes a plan, it will typically be deleted. Some legacy sketches may still exist and should be left alone until the user has reviewed them with you.
- `docs/developer/plans/<unit>.md` defines scope, dependencies, steps, decisions, and planned validation. Change it only when the plan changes. 
- `docs/developer/status/<unit>.md` is the sole authoritative live state. Update it after every material implementation action, validation result, blocker, or handoff.
- `docs/developer/review/<unit>-review.md` is the human review request. It contains scope, artifacts, exact `mise` commands, pass criteria, open questions, and a link to the matching status record. Create or refresh it before handoff. Archive or close it after disposition.
- Never create a second active status record for a unit.
- Every active review record must name an existing matching status record.
- `docs/developer/` root holds durable guidance only. Do not create a new `current/` directory.

### Epic Decomposition Model

An **epic** is a large work package spanning multiple phases, teams, or quarters with complex interdependencies. Epics are broken down into smaller, manageable units.

**Hierarchy:** Epic ⇒ Phase ⇒ Slice ⇒ Milestone

| Unit | Meaning | Ends with | Documentation |
|---|---|---|---|
| **Epic** | A large cross-phase work package with a stable owner (e.g. "LATTICE platform delivery", "Store SPI", "Ingestion pipeline") | Never; only the implementation phases end. Epic itself has no completion gate, only status tracking | `docs/developer/plans/<epic>.md` (marked `Unit type: Epic`) + individual phase plans + epic status file |
| **Phase** | A cohort of slices that together produce a demonstrable capability (e.g. "Phase 0: Decisions and foundations") | Phase gate: integration milestone + docs updated + ADRs ratified. **Status file created.** | `docs/developer/plans/<phase>.md` + `docs/developer/status/<phase>.md` |
| **Slice** | One agent work package (0.5–4 agent-days). A single coherent change, independently reviewable and testable | **Human validation gate.** Status file updated. | `docs/developer/validation/<slice-id>.md` (Validation Pack) |
| **Milestone (Mn)** | Cross-component demonstrable outcome, exercised end-to-end in the local stack (e.g. "M0: Walking skeleton") | Human demo + E2E suite green. Recorded in phase status. | Phase plan and phase status |

**Epic-specific governance:**

- The epic plan document (e.g. `lattice-platform-agentic-development-v0.2.md`) outlines phases, tracks, dependencies, and milestones at a high level.
- The epic plan is marked explicitly as `Unit type: Epic` and states that it will be decomposed into individual phase plans.
- **No epic-level review is created until all phase plans are authored and all acceptance test suites pass.** The epic remains in status-tracking mode, referencing phase-level status and review documents.
- Each phase gets its own plan (`phase-0-plan.md`, `phase-1-plan.md`, etc.) with scope, hard orderings, slice boundaries, and test taxonomy.
- Each phase gets its own status file (`phase-0-status.md`, etc.) updated at the phase gate.
- Each phase may get a review file only once that phase's acceptance tests are ready.

**Slice sizing rule:** If a slice's Validation Pack contains more than ~15 test cases or touches more than two modules, split it. If it contains fewer than 3, merge it. Skeleton slices are exempt (they contain 1 test: the build smokes).

**The mandatory shape of every slice:**

Every slice, without exception, delivers:

1. **Code** in one or two modules only.
2. **Validation Pack (VP)** — a single markdown file at `docs/developer/validation/<slice-id>.md` containing:
   - *What invariant does this slice protect?* (1 paragraph, in architecture language, citing G-nn/A-nn)
   - *Test case table*: ID, Given/When/Then in plain language, test level (L0–L8), the invariant it protects, pass criterion, and whether it is a positive or negative case.
   - *One command to run everything*: e.g. `mise module:check` or `mvn clean:verify`. If it is not one command, the slice is rejected on process grounds.
   - *Expected artifacts* the human should inspect (golden files, capability report, canonicalisation trace, screenshots).
   - *Deliberate non-coverage*: what this slice does **not** test and which later slice covers it.
3. **Traceability update** — Update `docs/developer/INDEX.md` to record the slice's completion status and link to its validation pack. Optionally maintain `docs/traceability/matrix.csv` rows linking slice ⇒ G-nn/C-nn/A-nn ⇒ test IDs if this slice addresses a gap. See `docs/developer/INDEX.md` for current traceability model.
4. **Doc delta** — if the slice contradicts or extends a normative document, the document is edited *in the same slice*. No "docs later".

**Human validation gate protocol:**

- **Step 1 — Review the VP before running anything.** The human judges whether the test cases are the *right* tests: do they actually pin the invariant? Are the negative cases the ones that matter? Is anything important listed under "deliberate non-coverage" that should not be?
- **Step 2 — Run the single command.** If it is not one command, the slice is rejected on process grounds.
- **Step 3 — Inspect named artifacts.** Golden files, traces, reports, screenshots.
- **Step 4 — Adversarial probe.** The human picks one test case and asks the agent to demonstrate it *fails* when the implementation is deliberately broken (mutation check). This catches vacuous tests, which is the dominant failure mode of agent-authored suites.
- **Step 5 — Sign off** in `docs/developer/validation/LOG.md` with slice ID, date, name, and any accepted deviations.

**Test taxonomy (L0–L8):**

The level of testing discipline for a slice should be verified during planning.

| Level | Name | Runs where |
|---|---|---|
| **L0** | Build smoke (compiles, runs, no-op test passes) | Local + CI |
| **L1** | Unit / pure-function | Local + CI |
| **L2** | Property & determinism (same input → same digest; permutation invariance; law checks) | Local + CI |
| **L3** | Contract (JSON Schema validation both directions; cross-runtime fixtures; OpenAPI conformance) | CI |
| **L4** | Component integration with real infrastructure (Testcontainers: databases, brokers, stores) | CI |
| **L5** | System E2E over the local compose stack via HTTP/AMQP only | CI nightly + on demand |
| **L6** | UI E2E (Playwright) against the compose stack | CI nightly |
| **L7** | Non-functional: SLO benchmark, capability/benchmark report, load profile | CI weekly + gated releases |
| **L8** | Hostile / security suites: cross-tenant probe, injection corpus, scoping escape | CI nightly |

**Non-weakening rule:** No slice may delete, skip, `@Disabled`, or loosen a test from a previous slice without an ADR-grade justification recorded in the VP and countersigned at the gate.

### Decisions and Links

- Architecture decisions live only in `docs/architecture/decisions/`.
- New or updated links must use canonical paths. Do not introduce `docs/adr/` references.
- When moving files, prefer using `git mv` if possible, and update all source, configuration, CI, documentation, and website references in the same migration unit.
- Historical records may describe old paths only when needed for context. Add a relocation note and link to the canonical path.

### Toolchain

- `mise` is the only task-orchestration entry point unless ADR-A29 is superseded.
- Maven, Yarn 4, Python project tooling, and Mix remain their own dependency authorities.

## General Guidelines

- Do not use semi-colons in English text. Use periods or commas instead.
- Be concise, do not repeat yourself. Avoid unnecessary verbosity.
- Avoid over-explaining. Say things once and cross-reference if really needed.
- Avoid superlatives.

### Documenting DL/OWL/TTL Ontologies

Try not to explain your design decisions in multiple places. Avoid explaining why you did not use a certain pattern or construct, especially if you've just explained why you did use a different one. If you feel the need to explain your design decisions, do so in a single place and cross-reference it from other places.

### Thinking / Reasoning for Coding

Your user may present design collateral, architectural guidance, and coding standards. These must be adhered to at all times. Readability and clarity of intent is as important as working code that passes tests.

Always consider the architectural quanta of the code you are writing and carefully consider whether your code might implicitly or explicitly change the dependencies within the codebase. If in chat mode (as opposed to agentic / co-work), prefer to clarify impacts with your user before making them.

### Thinking / Reasoning for Writing

Your primary mode of operation should be critical thinking - looking for logical consistency and challenging logical errors, gaps, or misunderstandings.

You should consider whether to present your own arguments as hypotheses or determined facts, generally adopting a stance of curiosity rather than dogmatism. This must be balanced against the need to maintain a clear and concise writing style (see below).

### Writing Style / Voice 

Regardless of the style your user has requested (formal, informal, etc), try to be concise and avoid unnecessary verbosity. Where your user has requested that you provide output that is "comprehensive" and "detailed", this refers to the depth of subject matter understanding and analysis required, not the number of words used.

### What To Avoid

The following MUST be avoided if at all possible, breaking these rules only under exceptional circumstances.

- Do not use semi-colons in English text. Use periods or commas instead.
- Be concise, do not repeat yourself. Avoid unnecessary verbosity.
- Avoid over-explaining. Say things once and cross-reference if really needed.
- Avoid superlative adjectives. These must be reserved for factual extremes (e.g., "the tallest building") and are banned from use for emphasis (e.g., "the best solution," "the ultimate guide"). 
- Try to avoid "It's not X, it's Y" binary reframes, replace them with direct statements. 
- Avoid formulaic transitions such as "Furthermore," "Moreover," "Additionally," and "In conclusion" at the start of sentences. 
- Avoid vague meta-commentary like "It is important to note that," "In today's digital age," and "This serves as a testament to." Keep it short and succinct.

### What To Reduce

The following styles should be kept to a minimum.

- Rhetorical questions that are followed immediately by an answer. In general, do not pose rhetorical questions and, if you choose to, do not give their answer (as doing so ruins the rhetoric)
- Emphasis via short sentences, e.g., "Short sentences. For Emphasis. Often in threes."
- Excessive use of metaphores, e.g., "A symphony of the unnecessary tapestry of metaphores".
