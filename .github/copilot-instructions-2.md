# Proposed Copilot Instructions: Repository Topology and Documentation Governance

**Status:** Proposed companion. This file is not authoritative until it is reviewed and explicitly renamed to replace or merge with `.github/copilot-instructions.md`.

## Authority and Reading Order

Before changing a unit of work, read:

1. The relevant accepted architecture decision in `docs/architecture/decisions/`.
2. The unit plan in `docs/developer/plans/<unit>.md`.
3. The unit status record in `docs/developer/status/<unit>.md`.
4. Any active human review request in `docs/developer/review/<unit>-review.md`.

Do not treat a plan as a status log. Do not begin a physical path move before the applicable ADR and path manifest are approved.

## Repository Topology

- `ontology/` owns semantic assets only: normative ontology sources, shapes, vocabularies, projections, semantic examples, semantic fixtures, and semantic documentation.
- `tools/` owns executable reference implementations and developer-facing toolchains.
- MORK and SPC semantic assets live under `ontology/mork` and `ontology/spc`. Their executable projects live under `tools/mork` and `tools/spc`.
- `workers/` is a deployable asynchronous runtime package and remains a top-level root.
- `platform/`, `apps/`, `packages/`, `contracts/`, `deployment/`, and `test/` remain top-level roots unless an accepted ADR says otherwise.
- Never introduce a new top-level root or place executable implementation code under `ontology/` without an accepted architecture decision.
- Never place normative semantic Turtle, shapes, or semantic fixtures under `tools/`.

## Documentation Lifecycle

Each active unit has one stable identifier, such as `iri-policy-p013`.

- `docs/developer/plans/<unit>.md` defines scope, dependencies, steps, decisions, and planned validation. Change it only when the plan changes.
- `docs/developer/status/<unit>.md` is the sole authoritative live state. Update it after every material implementation action, validation result, blocker, or handoff.
- `docs/developer/review/<unit>-review.md` is the human review request. It contains scope, artifacts, exact `mise` commands, pass criteria, open questions, and a link to the matching status record. Create or refresh it before handoff. Archive or close it after disposition.
- Never create a second active status record for a unit.
- Every active review record must name an existing matching status record.
- `docs/developer/` root holds durable guidance only. Do not create a new `current/` directory.

## Decisions and Links

- Architecture decisions live only in `docs/architecture/decisions/`.
- New or updated links must use canonical paths. Do not introduce `docs/adr/` references.
- When moving files, use `git mv` and update all source, configuration, CI, documentation, and website references in the same migration unit.
- Historical records may describe old paths only when needed for context. Add a relocation note and link to the canonical path.

## Toolchain

- `mise` is the only task-orchestration entry point unless ADR-A29 is superseded.
- Maven, Yarn 4, Python project tooling, and Mix remain their own dependency authorities.
- Do not introduce Gradle, pnpm, Make, or Just as competing build or task authorities.

## Human Gates

The default validation arrangement remains write then hand off. Do not run broad build, test, integration, Compose, or migration commands unless the human explicitly authorizes autonomous execution. End implementation work with an up-to-date status record and a review record containing the exact `mise` commands the human should run.
