---
name: lattice-lifecycle
description: How work is run in LATTICE and projects built on it. Use when starting, continuing, handing off or closing a unit of work, an epic, a phase or a slice, when reading or updating a status record, plan, review request or Validation Pack, when preparing a commit, merge or release, and when reporting what comes next.
---

# The LATTICE development lifecycle

The always-on rules are in `AGENTS.md`. This skill is the procedure behind them. Paths are relative
to the LATTICE repository, browsable at <https://github.com/nebularis/lattice>.

## Starting a named unit of work

Read, in order:

1. the accepted ADRs it depends on, in `docs/architecture/decisions/`
2. its plan, `docs/developer/plans/<unit>.md`
3. its status record, `docs/developer/status/<unit>.md`, the one authoritative live state
4. any open review request, `docs/developer/review/<unit>-review.md`

Do not treat a plan as a status log. Do not move a path before its ADR and path manifest are
approved.

## The documents

| Document | Holds | Changes when |
|---|---|---|
| `docs/developer/sketches/<unit>.md` | the broad shape of an idea, its options and questions | freely. Usually deleted once a plan replaces it. Leave legacy sketches alone until the human reviews them |
| `docs/developer/plans/<unit>.md` | scope, dependencies, steps, decisions, planned validation | only when the plan changes |
| `docs/developer/status/<unit>.md` | live state, next action, history | after every material action, result, blocker or handoff |
| `docs/developer/review/<unit>-review.md` | the review request: scope, artefacts, exact `mise` commands, pass criteria, open questions, a link to the status record | before handoff. Closed after disposition |
| `docs/developer/validation/<slice-id>.md` | a slice's Validation Pack | written with the slice, results filled at verification |
| `docs/developer/plans/pending-design-decisions.md` | design decisions that matter but cannot be made yet, with the options known | add when raised, remove naming the ADR, sketch or plan that settles it |
| `docs/developer/plans/technical-debt.md` | debt with no planned home: a shortcut, a gap between a claim and the behaviour, a check that does not run | add when spotted, remove naming the plan that takes it on. Never features, follow-ups or deferred slices |
| `docs/developer/INDEX.md` | every unit and its documents | when a unit or slice changes state |

Never create a second status record for a unit. `docs/developer/` itself holds durable guidance only.

## Epics, phases, slices and milestones

| Unit | Is | Ends with | Documents |
|---|---|---|---|
| Epic | a large package spanning phases, marked `Unit type: Epic` | never. Only its phases end | epic plan, phase plans, epic status |
| Phase | slices that together give a demonstrable capability | a phase gate: milestone, docs updated, ADRs ratified | phase plan and status |
| Slice | one agent work package, independently reviewable and testable | the human validation gate | its Validation Pack |
| Milestone | an end-to-end outcome in the local stack | a human demo and a green end-to-end suite | the phase plan and status |

No epic-level review is created until every phase plan exists and every acceptance suite passes.

**Slice sizing.** More than about 15 test cases, or more than two modules touched, splits the slice.
Fewer than 3 merges it. Skeleton slices, with one build smoke test, are exempt.

**Every slice delivers:**

1. code in one or two modules
2. a Validation Pack with the invariant it protects (one paragraph, citing the ADRs or gaps), a test
   table (ID, Given/When/Then, level L0 to L8, invariant, pass criterion, positive or negative),
   **one command** that runs everything, the artefacts to inspect, and deliberate non-coverage with
   the slice that covers it
3. a traceability update in `docs/developer/INDEX.md`
4. the doc delta, in the same slice. No "docs later"

**The human validation gate.** The human reviews the Validation Pack before running anything, runs
the one command and inspects the artefacts. An adversarial probe follows: the human names a test, or
leaves the pick to the agent, and the agent breaks the implementation, shows the test fails, restores
it, and records each probe and its result in the status record. The human's merge is the sign-off.
There is no separate sign-off log. `docs/developer/validation/LOG.md` is retired (2026-10-10).

**Test levels.** L0 build smoke, L1 unit, L2 property and determinism, L3 contract, L4 component
integration, L5 system end-to-end, L6 UI end-to-end, L7 non-functional, L8 hostile and security.

**Non-weakening.** No slice deletes, skips or loosens an earlier slice's test without an ADR-grade
justification in its Validation Pack, countersigned at the gate.

## Building a slice

- **Brief before branch.** A slice is briefed on `main` (scene, questions, each option's
  consequences), and the human answers before a branch is due. The human creates the branch, from
  the current `main`, unless they say otherwise.
- **Examples first** (ADR-A-C2). The first phase writes the examples the model must accept, and the
  human commits them. The model phase follows.
- **Pause before commit.** The agent builds and verifies, writes the Validation Pack's handoff and
  results, updates the status record, and stops. The human commits.
- **Executing a whole plan autonomously.** The request is the go-ahead to author every slice, but do
  not ratify ADRs, record each open design decision in the status record rather than choosing
  silently, and never report a check as passed that could not run.
- **Estimates** are in tokens, not agent days, so they can be compared with actual cost afterwards.

## Merging and releasing

- **Merge before tag.** A release tag names a commit on `main`. The order is commit, merge into
  `main`, then tag. A tag on an unmerged branch can name a commit that never reaches `main`.
- **Branch from `main`**, so a branch starts from every merged release, unless the human has said
  parallel work is under way.
- **Release tags are the human's.** Whenever `mise run build:ontology-releases` adds a row, or
  `mise run check:ontology-versioning` lists pending tags, end the handoff with a notice headed
  `🔴 RELEASE TAGS REQUIRED`, listing each tag as a, b, c with the commands to create and push them
  once the change is merged. Repeat it in every handoff until the tags exist.
- Never merge, push or tag without the human's go-ahead.

## Reporting

- A handoff lists what was built, what was run and its real result, what was not run, what to check
  first, and every deviation from the plan with its reason.
- A "what next" report ends with 🔴 PLAN FIRST when something must be decided first, or
  🟢 READY TO BRANCH when a new branch is actually due.
