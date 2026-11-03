---
name: lattice-lifecycle
description: How work is run in LATTICE and projects built on it. Use when picking up a slice or a unit, from your own plan or another's, before your first edit, when starting, continuing, handing off or closing a unit of work, an epic, a phase or a slice, when reading or updating a status record, plan, review request or Validation Pack, when preparing a commit, merge or release, and when reporting what comes next.
---

# The LATTICE development lifecycle

Ask the knowledge index first, as AGENTS.md's "Asking the knowledge index" says, with `mise run graph:ask -- find <the task in your own words>` and every facet value that fits the task at hand, then `read` each entry that answers. Read each row's flags and the line under it, where an entry's boundary, its successor and the debt against it are named. This skill's tasks span the activities delivery, planning-and-estimation, release-and-versioning, acceptance, regression-testing, continuous-integration, technical-debt-management, architecture-decision-making and documentation, and a task often needs several of them, named together and separated by commas. `--activity`, `--quality` and `--tech` raise matching entries and hide none, while `--kind` filters exactly, so leave `--kind` off unless only one kind of entry will do. The index finds the rules this skill does not mention, and the entries related to the ones it does.

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
| `docs/developer/sketches/<unit>.md` | the broad shape of an idea, its options and questions | freely. Usually deleted once a plan replaces it. Leave legacy sketches alone until the maintainer reviews them |
| `docs/developer/plans/<unit>.md` | scope, dependencies, steps, decisions, planned validation | only when the plan changes |
| `docs/developer/status/<unit>.md` | live state, next action, history | after every material action, result, blocker or handoff |
| `docs/developer/review/<unit>-review.md` | the review request: scope, artefacts, exact `mise` commands, pass criteria, open questions, a link to the status record | before handoff. Closed after disposition |
| `docs/developer/validation/<slice-id>.md` | a slice's Validation Pack | written with the slice, results filled at verification |
| `docs/developer/pending-design-decisions.md` | design decisions that matter but cannot be made yet, with the options known | add when raised, remove naming the ADR, sketch or plan that settles it |
| `docs/developer/technical-debt.md` | debt with no planned home: a shortcut, a gap between a claim and the behaviour, a check that does not run | add when spotted, remove naming the plan that takes it on. Never features, follow-ups or deferred slices |
| `docs/developer/INDEX.md` | the generated register of every unit and every slice, written by `mise run build:work` from the status records | never by hand. Regenerated in the same commit as the record it reads (STD-305) |

Never create a second status record for a unit. `docs/developer/` itself holds the registers and durable guidance only.

## Recording what we learn

A learning that outlives its session goes into a register in the same change that produced it, and the index is refreshed so other agents can find it ([ADR-A134](../../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md)). A learning left in a commit message is lost: 22 of this project's learnings existed only in git history when the index was built, including a Windows newline translation that silently corrupted generated SPARQL and two merge resolutions that made a task skip test modules without failing.

**Which register takes it.**

| What was learned | Goes in |
|---|---|
| what a store, tool, engine or platform actually does, found by probing or being surprised | [`docs/architecture/triple-store-discovery.md`](../../../docs/architecture/triple-store-discovery.md) as the next `TSD-`*n*, for a store. Otherwise the unit's status record until a register owns it |
| a choice made, where an ADR is warranted | an ADR, drafted as Proposed |
| a choice that matters and cannot be made yet | `pending-design-decisions.md` |
| a shortfall in something that exists, with no planned home | `technical-debt.md` |
| an answer the repository holds and no register entry does, found by falling back from the knowledge index | the register that should hold it, in the same change. Otherwise `technical-debt.md`, and tell the maintainer (STD-272) |
| a rule about how we write, name, structure or check something | the skill that an agent reads for that task, not a commit message |
| a cost measured, with numbers | the discovery record, citing the benchmark |
| a facet value an entry needs and the scheme lacks | [`docs/developer/facets.md`](../../../docs/developer/facets.md), as a row in its scheme's table with Ratified no, never in generated Turtle. Tag the entry with it in the same change |
| a rule a skill states, so the index can rank it | the standard register, as a row whose Pointer is the skill's section, with Ratified no |

**A register's header is a title, its Unit type line and at most one line of state.** A column's meaning is the `rdfs:comment` of the T-Box property it maps to, written once, so a header explaining its columns restates it. `check:knowledge` fails a register holding a table whose first column is not `ID` or `#`.

**How to write the entry.** One bolded lead sentence stating the claim, then the detail. The index extracts that sentence as the claim and never stores a second copy, so an entry whose first sentence is a preamble indexes as a preamble. Keep it under 200 characters and state the cost as well as the benefit.

**Then refresh the index.**

```bash
mise run build:knowledge
mise run check:identifiers
```

The first derives the index again, in about two seconds, so the entry is findable. The second fails if the entry cites an identifier that resolves to nothing, which is the commonest way a new entry is wrong.

## Epics, phases, slices and milestones

| Unit | Is | Ends with | Documents |
|---|---|---|---|
| Epic | a large package spanning phases, marked `Unit type: Epic` | never. Only its phases end | epic plan, phase plans, epic status |
| Phase | slices that together give a demonstrable capability | a phase gate: milestone, docs updated, ADRs ratified | phase plan and status |
| Slice | one agent work package, independently reviewable and testable | the validation gate | its Validation Pack |
| Milestone | an end-to-end outcome in the local stack | a demo and a green end-to-end suite | the phase plan and status |

No epic-level review is created until every phase plan exists and every acceptance suite passes.

**Slice sizing.** More than about 15 test cases, or more than two modules touched, splits the slice.
Fewer than 3 merges it. Skeleton slices, with one build smoke test, are exempt.

**Every slice delivers:**

1. code in one or two modules
2. a Validation Pack with the invariant it protects (one paragraph, citing the ADRs or gaps), a test
   table (ID, Given/When/Then, level L0 to L8, invariant, pass criterion, positive or negative),
   **one command** that runs everything, the artefacts to inspect, and deliberate non-coverage with
   the slice that covers it
3. its row on the home unit's slice board moved to `built`, and `mise run build:work` run, so INDEX.md's register follows
4. the doc delta, in the same slice. No "docs later"

**The validation gate.** The maintainer reviews the Validation Pack before running anything, runs
the one command and inspects the artefacts. An adversarial probe follows: the maintainer names a
test, or leaves the pick to the agent, and the agent breaks the implementation, shows the test fails, restores
it, and records each probe and its result in the status record. The maintainer's merge is the sign-off.
There is no separate sign-off log. `docs/developer/validation/LOG.md` is retired (2026-10-10).

**Test levels.** L0 build smoke, L1 unit, L2 property and determinism, L3 contract, L4 component
integration, L5 system end-to-end, L6 UI end-to-end, L7 non-functional, L8 hostile and security.

**Non-weakening.** No slice deletes, skips or loosens an earlier slice's test without an ADR-grade
justification in its Validation Pack, countersigned at the gate.

## Picking up and finishing

The slice board of a unit's status record is the one place a slice's state is written, and `mise run work:board` reads it from the tip of every local and remote branch ([ADR-A151](../../../docs/architecture/decisions/ADR-A151-the-work-board.md), plan `work-board`). The board's shape is fixed.

```markdown
| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| CCS-9b.3b | aggregate bindings | building 2026-10-30, briefed 2026-10-27 | |
| CCS-9b.4 | qualifying rules | planned | CCS-9b.3 |
```

- **A slice's state is written once, on the board of its home unit**, the unit whose plan defines it (STD-300). An agent that builds a CCS slice on a formal-methods branch sets the row in the CCS record, on that branch. The adopting unit's record says so in its history and never carries a second row.
- **Mark before you touch.** Picking up is one edit, and it is the first edit: set the row to `building <day>`, add a history line, run `mise run build:work`, and commit the mark alone, so the board sees the claim from the first push (STD-301). An agent caught editing unmarked stops, marks and commits the mark before going on. A unit or a plan picked up whole is its record's `**Status:**` line changed the same way.
- **A state is a word of the ladder and the day it was reached.** `planned`, `briefed`, `building`, `built`, `verified`, `merged`, `tagged`, with `blocked` and `dropped` aside, dated from `building` on, newest first in the cell, so the cell is its own trail (STD-302). The day is the fact written. The commit is read from git by `mise run work:board -- --commits`, never written.
- **A unit's state is its board's roll-up** (STD-317). Where a record has a board, its `**Status:**` word and day are what the rows give: building while any row is building, dated by the earliest, else the lowest word of the rows at built or later, dated by the latest, else blocked if any row is, else the highest of planned and briefed. Dropped rows count only when every row is dropped. `mise run work:normalise -- --apply` sets the word, and the `work` check refuses one that disagrees. `work:board` shows `main`'s state and each branch further on.
- **Handing off is one edit**, the row to `built <day>` in the commit that carries the Validation Pack's handoff. The maintainer's verification is `verified`, and the merge into `main` flips the rows it delivers to `merged <day>` in the merge commit.
- **A slice id is `PREFIX-segment(.segment)*`**, a segment being optional capitals, digits and one lowercase letter, and the prefix declared on the unit's plan's `**Prefix:**` line (STD-303). `CCS-9b.3b`, `FMH-2.6d`, `AIR-S1` and `OD-DOC1` are ids. A slice is defined by its row, and a slice a plan names with no row fails `check:identifiers`.
- **No plan and no status record names a branch** (STD-304). The board derives the branch from where it finds the row, and plans move between branches.
- **The register is regenerated in the same commit** (STD-305). The `work` hook check refuses a commit whose touched records and INDEX.md's region disagree, or whose touched board is malformed, and names the task that fixes it.
- **Before the first edit in any checkout, run `mise run work:here`** (STD-306). It writes your presence, `--role build`, `review` or `read` with `--model`, into the worktree's git-ignored `.local/agents/`, and lists the sessions touched in the last twelve hours. Where another live session is building there, or you were asked to review, say who is here and ask the maintainer before writing. A reviewer's findings go to the review request or to chat, never into a file another live session is building.

**ROADMAP.md is kept whole, section by section** (STD-307). It is the maintainer's summary, and every section is current or says why not.

| Section | Kept by | When |
|---|---|---|
| 1 the programme at a glance, 7 branches, 9 decisions waiting, 11 completed units | generated by `mise run build:roadmap`, which the post-merge hook runs on `main` | after every merge into `main`, and on demand. Never edited by hand |
| 2 how the epics depend on one another, 8 the critical path | the planner, as diagrams | when a plan's Dependencies section gains or loses a dependency between units, or a blocker on the board changes the longest chain |
| 3 the layers | the ontology author, as a diagram | when an ADR changes the substrate's import order or proposes a layer |
| 4 active epics, 6 the platform programme | the agent handing an epic or a phase off, one subsection per epic | at each handoff and each merge that moves the epic: its documents, its ADRs, what moved and what is next, in the same commit as the status record |
| 5 smaller units | nobody. It points at section 1 | never |
| 10 the maintainer's queue | the agent proposes an order at each handoff, the maintainer orders | at each handoff that changes what unblocks the most work |
| 12 observations | the agent that refreshes the roadmap | at each refresh, every observation checked and a stale one removed |

A handoff that changes a unit's state says in its report which roadmap sections it refreshed and which it left, and why. Where a hand-written section disagrees with section 1, section 1 is right and the section is refreshed.

Ask the board before reading branches. `mise run work:board` answers where every unit and slice is, with `--all` for every row, `--fetch` to fetch every remote first, `--measure` for each branch's content share on `main`, and `--commits` for the commit that set each printed row. INDEX.md holds the state of the tree it was built from, and `graph:ask -- read <slice id>` prints a slice's row.

## Building a slice

- **Brief before branch.** A slice is briefed on `main` (scene, questions, each option's
  consequences), and the maintainer answers before a branch is due. The maintainer creates the
  branch, from the current `main`, unless they say otherwise.
- **Examples first** (ADR-A-C2). The first phase writes the examples the model must accept, and the
  maintainer commits them. The model phase follows.
- **Pause before commit.** The agent builds and verifies, writes the Validation Pack's handoff and
  results, updates the status record, and stops. The maintainer commits.
- **Report on the knowledge index at every handoff.** List the questions it answered weakly or not at all, the near answers and the gaps recorded while reading (`mise run graph:ask -- misses --near`). Say which entry, facet value, column or edge would have carried each, such as a Does not cover cell, a Distinguished from or Bears on id, or an addendum's Reverses lead, and add any answer the fallback found to its register in the same change (STD-272). A gap is recorded with `graph:ask -- gap` when it is found, not remembered at the end, and closed with `graph:ask -- close <ID>` in the change that writes its signpost.
- **Executing a whole plan autonomously.** The request is the go-ahead to author every slice, but do
  not ratify ADRs, record each open design decision in the status record rather than choosing
  silently, and never report a check as passed that could not run.
- **Estimates** are in tokens, not agent days, so they can be compared with actual cost afterwards.

## Merging and releasing

- **Merge before tag.** A release tag names a commit on `main`. The order is commit, merge into
  `main`, then tag. A tag on an unmerged branch can name a commit that never reaches `main`.
- **Branch from `main`**, so a branch starts from every merged release, unless the maintainer has said
  parallel work is under way.
- **Know how each changed module is released before any bump.** The substrate, the kinds in the catalogue's `[conventions.release]`, is one release, moved by `mise run release:prepare -- <X.Y.Z>` and tagged once as `ontologies-vX.Y.Z` (ADR-A129). A standalone module (MORK, SPC, Surface, Persistence) and an applied module are each released on their own, by bumping only the documents and shape or projection directories that changed, each by its own change, and tagging each document that moved as `<name>-vX.Y.Z` (ADR-A86, ADR-A129's addendum of 2026-10-26). `mise run check:ontology-versioning -- --base-ref main` prints a `HOW` line for each module it flags, saying which. `release:prepare` for a standalone module's change moves every substrate layer for nothing. The per-module substrate tags from before release 0.18.0 are history.
- **Ontology version bumps happen once, at merge, never mid-branch.** For a substrate change, `mise run release:prepare` moves every release member's shared version number forward (ADR-A129) and cascades into every applied module that pins it. A standalone or applied module's own bump is made the same once, at the merge. Nobody consumes a branch's version numbers before it merges, so bumping per-slice re-pins dozens of files for no reader and still has to happen again at the merge. A branch's new or changed ontology documents keep citing the version `main` was pinned to at the branch point throughout the branch's life (skill `lattice-ontology-authoring`). Expect `check:ontology-versioning` to report a pending bump for a branch's own changed content until the actual merge-time bump, which is the correct state of a branch mid-flight, not a defect to work around.
- **Versions on a working branch.** Where the maintainer has agreed that a branch defers versioning, the branch makes no bump, its status record says so, and `check:ontology-versioning`'s `UNBUMPED` is expected there. The branch writes each change's release note when it makes the change, under `- **Unreleased**.` in the layer's README, classed as the versioning policy says (STD-293). The bump is made once, before the merge into `main`, by `mise run release:prepare` for the substrate or by hand for a module released on its own, as the check's `HOW` line says, and the tags follow the merge.
- **Release tags are the maintainer's.** Whenever `mise run build:ontology-releases` adds a row, or `mise run check:ontology-versioning` lists pending tags, end the handoff with a notice headed `🔴 RELEASE TAGS REQUIRED`, listing each tag as a, b, c with the commands to create and push them once the change is merged. Repeat it in every handoff until the tags exist.
- **Conformance before a merge.** Before a branch is merged into `main`, every conformance task of a suite the branch touched runs
  and passes, for example `mise run check:persistence-conformance`, which runs the generated SPARQL on every engine we have. They are
  not part of `check` (skill `lattice-testing`), so the handoff that asks for the merge lists each one with its result, or says it
  was not run and why. A failure on one engine is recorded in the triple-store record and is fixed or accepted before the merge.
- **The merge gate.** A merge into `main` runs the hooks' merge checks, published decisions over the whole tree and ontology versioning among them (ADR-A133). Before merging on GitHub, where no local hook runs, run `mise run hooks:merge`. No hook ever blocks a push, so a branch always reaches the maintainer for review. A README migrated to the ADR-A126 layout may cite only a published decision (ADR-A127), and the published-decisions check fails the merge on a citation of a Proposed one, so the handoff before a merge lists every Proposed decision such a README cites under 🔴 PLAN FIRST, for the maintainer to accept first (PDD-16).
- Never merge, push or tag without the maintainer's go-ahead.

## Reporting

- A handoff lists what was built, what was run and its real result, what was not run, what to check
  first, and every deviation from the plan with its reason.
- A handoff names the ROADMAP.md sections it refreshed and the ones it checked and left, since every handoff attends to the roadmap (STD-307). The generated ones are `mise run build:roadmap -- --fetch`, and the hand-written ones follow the table in Picking up and finishing.
- A "what next" report ends with 🔴 PLAN FIRST when something must be decided first, or
  🟢 READY TO BRANCH when a new branch is actually due.
