<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Architecture principles and guidance

**Status.** Draft for the maintainer's review, 2026-10-18. Nothing here is accepted yet.

**What this is.** The standing directions that LATTICE's decisions share, stated once so that maintainers, developers and agents can judge a new design before an ADR exists for it. An ADR records one decision. A principle says which way decisions have gone and should keep going.

**Where it sits.** This is cross-layer reference material. It makes no decision of its own. Every principle cites the ADRs or normative documents it rests on. Where a principle and an accepted ADR disagree, the ADR wins, and the disagreement is a defect in this document. A principle marked **(no ADR)** is today stated only in agent guidance or a skill, and is a candidate for an ADR of its own (question AP-Q2).

**How to use it.**

- Before designing, read the principles in the groups your change touches.
- A design that departs from a principle says so in its sketch or ADR, names the principle, and argues the exception. Departure is allowed. Silent departure is not.
- A principle that keeps being argued away is a sign it is wrong. Raise it for revision rather than working around it.

Each principle has a statement, its reason, what it means in practice, and its sources. Section 8 turns them into checks by role.

## 1. Framework and scope

### F1. LATTICE is a framework

**Statement.** LATTICE offers mechanisms, options and configuration. It imposes a design choice on its users only where correctness needs it.

**Reason.** Adopters work under different markets, jurisdictions, stores and deployments. A framework that hard-codes one of them is wrong for the others, and the cost lands on every adopter.

**In practice.**

- Prefer a declared option with a documented default over a fixed behaviour, for example ADR-A96's optional single-attachment shape and ADR-A90's caller-declared sibling disjointness.
- Ship mechanisms without content. Quantification ships no units, calendars or context roles, and Foundation declares no key scheme. The deployment declares its own.
- A reference profile, edition or deployment is opt-in and never presented as a standard.

**Sources.** Skill `lattice-design`, ADR-A82, ADR-A99, ADR-A114, ADR-A115.

### F2. The substrate is domain-neutral

**Statement.** Substrate layers state mechanisms with laws that hold in any domain. Domain content lives in applied modules, at the lowest level of sharing that covers its users.

**Reason.** A mechanism shaped by one domain's habits drifts toward that domain and fails the next one. The neutral substrate is what lets lending, licensing, trials and insurance share one model.

**In practice.**

- Author substrate content in clean-room order: generic premise, at least two non-domain examples, then mechanism prose.
- Explain a substrate term from law, drafting or computing, never from "the market". Never name a downstream project in a layer README.
- Place a module at substrate, cross-domain applied or domain-shared level, and promote it only by the criteria for that level.

**Sources.** ADR-A-C2, ADR-A-C1, ADR-A98.

### F3. Dependencies point downstream to upstream, never back

**Statement.** Downstream projects depend on LATTICE's release tags. LATTICE never depends on, names or waits for a downstream project.

**Reason.** A framework that knows its consumers stops being reusable by others, and its release cadence becomes theirs.

**In practice.** A need found downstream comes back as a generic premise (F2), never as a reference to the project that raised it.

**Sources.** Skill `lattice-architecture`, ADR-A31 **(no ADR for the rule itself)**.

## 2. Modelling

### M1. Ask how the law answers, and model that

**Statement.** Before modelling a legal or contractual concept, find how law and drafting practice already treat it, and model that structure.

**Reason.** A model that mirrors reality rarely needs to change when reality is tested against it. One shaped for implementation convenience drifts at the first case it did not foresee.

**In practice.** Say in the design which legal or drafting practice the model follows. For example, a threshold that several powers use belongs in the meaning of the defined word, not on each power.

**Sources.** `AGENTS.md`, skill `lattice-ontology-authoring` **(no ADR)**.

### M2. Model reality first, then simplify

**Statement.** Simplify only a model that already reflects what it models. Never reduce complexity by leaving reality out. Record any drift forced by usability or size, with its reason.

**Reason.** A simplification made before the full model exists cannot be checked for what it loses. In RDF, merging, removing or moving a fact changes what a reasoner, a shape and a compiler can still see, in different ways.

**In practice.** Apply the checks in "Simplifying a model safely" (skill `lattice-ontology-authoring`) before removing or merging anything. An accepted ADR wins over a simplification that contradicts it.

**Sources.** `AGENTS.md`, skill `lattice-design` (KISS), skill `lattice-ontology-authoring` **(no ADR)**.

### M3. Layers state, code executes

**Statement.** Ontology layers are data. They declare what is computed and how a result is read. Evaluators count, sum, resolve and force deferred values. No layer that states meaning depends on a runtime to say what something means.

**Reason.** Meaning that needs a runtime cannot be checked, versioned or shared independently of that runtime, and every other realisation (R1) would have to agree with it by accident.

**In practice.**

- Judgements, such as whether a rule was met, an act took effect or a direction applies, are derived from facts and recorded as derived artefacts, never authored.
- A shape reports an asserted judgement that has no derivation.

**Sources.** `AGENTS.md`, ADR-A102, ADR-A106, skill `lattice-ontology-authoring`.

### M4. Three-valued evaluation, and gaps stay visible

**Statement.** An evaluation decides Permitted, Denied or Undetermined. Undetermined carries a diagnostic and never becomes a breach, a denial or a default. What a source does not say is recorded as missing, never filled by invention.

**Reason.** Contracts and data are routinely incomplete. Collapsing "not known" into "no" or "yes" produces confident wrong answers that cannot be traced back.

**In practice.**

- A set reading decides on completeness only under a declared closure.
- A conversion the context does not supply makes the comparison Undetermined, with a named reason.
- Extraction records an uncertain mapping or an unsourced marker rather than a plausible value.

**Sources.** ADR-A24, ADR-A103, ADR-A105, ADR-A94, ADR-A95, ADR-A115, ingestion vision IV10.

### M5. The open world is deliberate

**Statement.** Models assume an open world. The absence of a statement asserts nothing. Closure is declared where it is relied on, with its source.

**Reason.** Law implies terms no clause states, and registers are complete only when someone authoritative says so. A closed-world default would decide things no one decided.

**In practice.** Keep a place for implied terms (`ins:impliedBy`). Name the closure a binding relies on (`elg:closedUnder`), and let nothing infer one.

**Sources.** ADR-A105, skill `lattice-ontology-authoring`.

### M6. The words are the contract

**Statement.** An instrument version is expressed in exactly one assembled wording, and binds exactly the stated meaning of what that wording includes. A clause states its meaning once, with roles, defined words and placeholders. Bound meaning is generated per instrument by instantiation, never stored as a second source of truth.

**Reason.** Two independently maintained statements of one agreement diverge. Tying meaning to text makes every bound relation traceable to the words that justify it.

**In practice.**

- Text names what it refers to by persistent identity. The wording fixes the version.
- Store what differs from a shared form. Regenerate the rest on demand.

**Sources.** ADR-A104 and addenda, ADR-A112 and addendum.

### M7. Structure apart from state

**Statement.** A regime, state machine or declaration is stated once. Each instance's progress through it is runtime state, kept apart from the declaration.

**Reason.** Mixing the two makes every instance a copy of the declaration and every declaration change a migration of every instance.

**In practice.** Behaviour's configuration and runtime documents stay separate, and no class serves more than one of Behaviour's four tiers. Legal concepts live in Instrument. Findings and execution live in Behaviour, which stays an abstract state machine.

**Sources.** ADR-A08, ADR-A104 addendum of 2026-10-04, ADR-A106.

### M8. Reify a relation that needs identity, evidence or time

**Statement.** A relation that must carry its own evidence, time scope or history becomes a node. Otherwise it stays a direct property.

**Reason.** A direct property cannot be qualified or superseded without losing what it said before. A node for every relation multiplies the data for nothing.

**In practice.** Role occupancy, group membership, delegation and keys are nodes. A property gets `rdfs:domain` and `rdfs:range` only where the entailment is wanted. Otherwise its comment states subject and value and a shape checks use.

**Sources.** [ontology-architecture.md](ontology-architecture.md) §9, ADR-A114, skill `lattice-ontology-authoring`.

## 3. Structure and dependencies

### S1. Layers depend downward only

**Statement.** A layer never imports, or names a term of, a layer above it, a sibling or an applied module. A change to the order is an ADR.

**Reason.** The order is what lets each layer be released, reasoned over and replaced on its own. One upward edge couples every layer in between.

**In practice.**

- An upward reference lives in the higher layer's own projection.
- `mise run check:import-guard` enforces the order. A change to it updates the guard's table and the diagram in [ontology-architecture.md](ontology-architecture.md) together.

**Sources.** ADR-A01 and addendum, ADR-A106, ADR-A112.

### S2. Optional backends sit behind interfaces we own

**Statement.** A reasoner, store, model provider or agent framework is reached through an interface LATTICE owns, with a working default and contract tests. No core path requires a particular one.

**Reason.** Backends change faster than the model, and licences differ. An interface keeps the choice with the adopter and keeps a backend's licence and failure modes out of the core.

**In practice.**

- Reasoners are declared only in `platform/reasoning-testkit`, reached by a CLI contract.
- Domain logic uses the Core store tier only. Extended capabilities are declared and gated, and Native ones stay inside adapters.
- Test-support packages are used only by tests, checks and benchmarks.

**Sources.** ADR-A83, ADR-A125, ADR-A71 (Proposed), ADR-A75 (Proposed), ingestion vision IV12.

### S3. New structure needs a decision

**Statement.** A new repository root, a new kind of directory or a new edge between modules is decided in an accepted ADR before it is built.

**Reason.** Structure is cheap to add and costly to remove. A decision makes its owner, scope and reason findable later.

**In practice.** Place work inside the existing roots. A proof of concept states that it is one and that nothing may depend on it.

**Sources.** ADR-A77, ADR-A118, ADR-A124, ADR-A125, `AGENTS.md`.

## 4. Identity, versions and provenance

### I1. One identity, immutable versions

**Statement.** A versioned thing keeps one persistent identity across versions. A version is never edited. A change is a new version linked by `fnd:supersededBy`.

**Reason.** Contracts, decisions and audits refer to what was true at a time. In-place edits destroy the state a past decision rested on.

**In practice.** Corrections are new versions with evidence of their cause. A content revision and the event that promoted it have separate identities.

**Sources.** ADR-A07b (carried into ADR-A104), ADR-A67 (Proposed), ADR-A82 (Proposed), [iri-identity-patterns.md](iri-identity-patterns.md).

### I2. Distinct identities are never conflated

**Statement.** Semantic content, generation profile, build artefact and runtime state each have their own identity. A derived product is valid for reuse only when both its semantic content hash and its generation identity match.

**Reason.** One digest for several questions answers none of them reliably. It either invalidates caches needlessly or reuses a product built under a different profile.

**In practice.** Detect reuse of unchanged content, such as a standard clause, by its semantic content hash. Never infer interchangeability from a build hash alone.

**Sources.** ADR-A12, [ontology-architecture.md](ontology-architecture.md) §10.

### I3. Semantic versions, with the cascade

**Statement.** Every changed ontology document bumps its semantic version, and its importers re-pin in the same change. At major version zero a breaking change takes a MINOR bump and is marked breaking.

**Reason.** Consumers pin versions. A silent change under a pinned version breaks them without warning, and an unrepinned importer is a document that no longer says what it imports.

**Sources.** ADR-A86 and addendum, ADR-A113, ADR-A120.

### I4. Everything derived records how it was derived

**Statement.** A generated, inferred, compiled or materialised artefact records its derivation run, its read set and its authority. It is regenerated within minimal scope, from its read set.

**Reason.** An artefact without provenance cannot be trusted, reproduced or invalidated precisely. Broad regeneration hides which inputs mattered.

**In practice.**

- Use PROV-O through `fnd:DerivedArtefact` and `fnd:DerivationRun`.
- A derived artefact's authority never exceeds the declaration it came from. A surface is Advisory or CachedReproducible.
- The provenance chain is complete at every stage the pipeline adds.

**Sources.** ADR-A12, ADR-A16, ADR-A26, ADR-A27, ADR-A92.

## 5. Realisation and runtime

### R1. Semantics are independent of how they run

**Statement.** A mechanism's meaning is defined so that SPARQL, SHACL, a reasoner, a compiled evaluator or materialisation can each realise it. Compilation is one realisation among several.

**Reason.** Adopters run different stacks. Meaning tied to one realisation cannot be checked against another, and so cannot be checked at all for parity.

**In practice.**

- Reified declarations are usable RDF as authored, with no generation step needed at modest volume.
- Every backend compiles from one shared IR, and parity across backends is a gate.
- A backend that cannot express part of the meaning refuses the plan rather than approximating it.

**Sources.** ADR-A15, ADR-A19, ADR-A24, ADR-A28, ADR-A100.

### R2. Portable first, then fast, and every speed claim names its scope

**Statement.** A query or shape is correct on every conforming engine. Speed on one engine is an optimisation of a portable form, never a reason for a non-portable one. A performance claim names the engine, harness or machine it holds for.

**Reason.** Engines differ from the specification and from each other. An unscoped speed claim travels to engines where it is false.

**In practice.** Follow [efficient-queries-and-shapes.md](efficient-queries-and-shapes.md). Rely on store behaviour only as recorded in [triple-store-discovery.md](triple-store-discovery.md). A rewrite for speed is replayed against the old shapes before it is committed. Benchmarks fail on a wrong result, never on time.

**Sources.** ADR-A128 (Proposed), ADR-A124, ADR-A75 (Proposed).

### R3. Proposals are not assertions, and production is deterministic

**Statement.** Output from a model, an extraction or any non-deterministic source is proposal-grade. It is held as distinguishable nodes and reaches a compiled artefact only through governance. After that gate, decoding, validation, compilation and provenance are deterministic.

**Reason.** A production artefact must be reproducible and attributable. A proposal that silently becomes an assertion is neither.

**In practice.** A person accepts proposals. Bulk acceptance needs a passing calibration for the exact pack, profile and model. A deterministic-only mode always exists.

**Sources.** ADR-A25, ADR-A22, ADR-A43, ingestion vision IV2, IV3, IV9.

### R4. Meaning lives in the graph

**Statement.** Meaning-bearing facts, and governance and provenance about them, live in the graph. Coordination state, metering and opaque bytes live in their own realms and are never authoritative for meaning.

**Reason.** A fact outside the graph cannot be queried, reasoned over or versioned with the model it describes.

**Sources.** ADR-A74 (Proposed), ADR-A13, ADR-A33.

### R5. Trust is enforced by the server, and every write is safe to repeat

**Statement.** Scoping, redaction and permission checks happen on the server, from a principal derived there. Writes are idempotent, guarded by optimistic concurrency, and every multi-store operation is a transaction, an outbox or a named saga with compensation.

**Reason.** Clients and networks retry, reorder and lie. A design that is safe only on the happy path fails at the first retry.

**In practice.** No adopter-supplied value reaches a query template as a raw string. Conflicts are shown, never silently retried or dropped.

**Sources.** ADR-A35, ADR-A36, ADR-A79, ADR-A123, ADR-A48 (Proposed), ADR-A66 (Proposed), [ux-design.md](ux-design.md) §3.

## 6. Assurance

### A1. Conformance is stated by level

**Statement.** Whether a graph conforms is always stated at a named level, from ingestible to projection-conformant. Shapes are organised by profile, never as one monolithic gate.

**Reason.** Ingested and mapped data is correctly incomplete for a long time. A single pass or fail either rejects legitimate work in progress or accepts what is not ready to execute.

**Sources.** ADR-A14, [conformance-levels.md](conformance-levels.md).

### A2. Laws are stated, then checked more than one way

**Statement.** A mechanism's behaviour is stated as numbered laws. Laws are checked by negative and positive fixtures, by parity across backends and, where the formal-methods programme covers the layer, by proof.

**Reason.** A law checked one way inherits that way's blind spots. Agreement between independent checks is the evidence that the statement is right.

**In practice.** Every constraint has a negative test. A layer's proofs and reference evaluator are generated from, or checked against, the same literate source as its Turtle.

**Sources.** ADR-A20, ADR-A28, ADR-A-FM1, ADR-A-FM2, ADR-A-FM3.

### A3. The README is the source, and the rest is extracted

**Statement.** A layer's README is its normative, literate source. Its Turtle, vocabulary and shapes are extracted from it, never edited independently.

**Reason.** One source cannot disagree with itself. Separate prose and code drift.

**Sources.** ADR-A07, ADR-A120.

## 7. Delivery

### D1. Design before code, and decisions are written down

**Statement.** A change that crosses layers or modules starts from a sketch or a design specification entry and, where it decides something, an ADR. The maintainer accepts decisions.

**Reason.** Code written ahead of the design encodes a decision nobody reviewed. A design written down can be checked against the roadmap before it is built.

**In practice.** Check a design against the epic plans and held questions, as well as against the code. A design that works now and makes a roadmap item harder is wrong.

**Sources.** Skill `lattice-design`, ADR-A117, `AGENTS.md`.

### D2. One entry point for every task

**Statement.** Every build, test and check runs through `mise`, which CI runs too. Package managers remain the authorities for their own dependencies.

**Reason.** One entry point makes a local result and a CI result the same claim.

**Sources.** ADR-A29, ADR-A77.

### D3. Everything is public

**Statement.** The repository and everything it publishes are public. Nothing identifies a person or a client the project does not itself name. AI-assisted contributions are disclosed as required.

**Sources.** `AGENTS.md`, [GENAI_CONTRIBUTION.md](../../GENAI_CONTRIBUTION.md), skill `lattice-publication-hygiene` **(no ADR)**.

## 8. Guidance by role

### For anyone changing a design

Before proposing, answer:

1. Which layers and modules does it touch, and does it add an import, an edge or a runtime dependency (S1, S2)?
2. Is anything domain-specific entering the substrate (F2)?
3. Does it hard-code a choice an adopter could reasonably make differently (F1)?
4. Does it author a judgement that should be derived, or compute in a layer that should only state (M3)?
5. What happens when a value is missing, and does the answer stay Undetermined (M4, M5)?
6. What new identity, version or derived artefact does it create, and how is it invalidated (I1 to I4)?
7. Does it hold on every engine, and is every speed claim scoped (R1, R2)?
8. Which principle, if any, does it depart from, and is the departure argued (How to use it)?

### For maintainers

- Review against the principles named in the design, and ask for the ones it does not name.
- When accepting an ADR that departs from a principle, decide whether the principle changes, and update this document in the same change.
- Promote a **(no ADR)** principle to an ADR when it is cited as the reason for rejecting a design.

### For developers

- Read the principle groups for the area before starting, and cite them in the sketch or plan.
- Treat a check that encodes a principle (`check:import-guard`, `check:reasoning-isolation`, the parity gates) as the principle itself. Do not weaken the check to land a change.

### For agents

- `AGENTS.md` and the skills carry the operating rules. This document carries the direction behind them.
- When a design question arises, name the principles involved in the options presented to the maintainer, and say which option departs from which (skill `lattice-design`).
- Never resolve a conflict between a principle and an accepted ADR alone. Report it.

## 9. Open questions for review

| Question | Options | Leaning |
|---|---|---|
| AP-Q1. Where does this live? | (a) here, in `docs/architecture/` (b) beside the ADRs in `decisions/` | (a). It is reference material under GOVERNANCE.md, and the ADR catalogue stays decisions only |
| AP-Q2. Does it need its own ADR? | (a) no, every principle cites ADRs (b) one ADR adopting the document and the **(no ADR)** principles (c) one ADR per **(no ADR)** principle | (b). F3, M1, M2 and D3 would otherwise rest on agent guidance alone |
| AP-Q3. Principles resting on Proposed ADRs (S2, R2, R4, R5 in part) | (a) keep, marked (b) drop until accepted | (a). The direction is already followed in code, and the marking keeps the status honest |
| AP-Q4. Relation to the `lattice-architecture` skill's principle table | (a) the skill links here and drops its table (b) both kept | (a). Say it once (`AGENTS.md`, Writing) |
| AP-Q5. Scope of the platform principles (R4, R5) | (a) keep in this document (b) a separate platform principles document | (a) for now. Split if the platform section grows past the ontology sections |
| AP-Q6. Identifiers | group letters (F, M, S, I, R, A, D) as drafted, or a flat sequence | group letters. They survive insertion within a group |
