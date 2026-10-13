<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Insurance Reference — Machines, Branches and Merges

**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Purpose:** which machine and agent builds each slice, on which branch, in which round, and who
merges what. Slice content stays in the phase plans.
**Revised 2026-10-13.** Machine S builds its slices in sequence, so they share one long-lived
branch, `air/applied-reference`, instead of one branch each. The per-slice `air/<slice>` branches
of rounds 1 to 3 were all merged into `main` and are deleted (§3). Machine R's own slices still
take their own branches.

**Revised again 2026-10-13: one trip.** Every AIR slice that does not wait on CCS or NRS is built
on S in one trip, and the branch comes to R once, when the trip is done (§4). The reasons:

- Versioning (ADR-A86) governs what is released on `main`. A branch is not a release, so the branch
  carries one bump per document whatever the number of slices that change it, and its imports stay
  pinned to the layer versions of `main` at the branch point while CCS moves on.
- An applied module is not substrate. Nothing on `main` imports the AIR modules except other AIR
  modules, so `main` loses nothing while they wait on the branch.
- Every brief for the trip is written before S starts (§1, "Brief before start"), so S needs nothing
  from R mid-trip.

R re-pins the branch to `main`'s layer versions once, at the merge (§6 step 4).

## 1. Machines and agents

| Machine | Can | Cannot | Agents | Used for |
|---|---|---|---|---|
| **R**, runtime | run `mise`, Python, Java, every check. Push to GitHub. Merge | — | **Claude Code**, **Copilot Pro+** | Claude: compiler and substrate code, ADRs, verifying design-heavy branches. Copilot Pro+: running a branch's checks and fixing simple failures |
| **S**, sandbox | edit anything, commit, pull from GitHub, run `mise` and every repository check locally (confirmed durable 2026-09-29) | push | **Copilot Business** (the largest budget) | Turtle, SHACL, examples, READMEs, and code of any complexity, since S now verifies its own work before handoff. Push, merge, catalog regeneration and release tagging stay on R regardless of what S can run |

These rules follow:

- **The maintainer runs the branching and merging.** Agents must not run the git commands this plan
  gives for creating, switching, fetching, pulling, pushing, bundling, rebasing or merging
  branches (§3, §6). They may run any other local git command their normal workflow needs, such
  as `git status`, `git diff`, `git log` or committing on the branch the maintainer has checked out.
  When a step needs one of the maintainer's commands, the agent stops and says so. The one exception:
  machine R's agent may run them when we explicitly ask it to. Machine S's agent never
  does.
- **Branches are created, pushed and merged on R only.** S pulls, works and hands its commits
  back as a bundle (§3). S's agent commits on `air/applied-reference` and nowhere else.
- **Brief before start.** S starts a slice only once its brief is on `air/applied-reference`: an
  "in detail" section in its phase plan and a Validation Pack skeleton. Every brief of the trip is
  on the branch when it is created, so S builds the whole trip without a sync. If S finds a brief
  wrong or incomplete, it stops at that slice, records the question in the slice's Validation Pack
  and its own status section, and goes on with the next slice that does not depend on the answer. Whenever machine R's agent
  reports what comes next, it ends with exactly one of these, on its own line:
  - `🔴 PLAN FIRST: AIR-x.y needs its brief drafted before the trip.` It lists every such
    slice, and R drafts them before anything else.
  - `🟢 READY TO BRANCH: create and push <branch>, …` It names a branch only when one is due, which
    is now only R's own slices (AIR-3.3, AIR-3.5, substrate). S's work needs no new branch.
- **One commit range per slice.** Each slice is a contiguous run of commits whose messages start
  `[AIR-x.y]`. The last one is the handoff commit, `[AIR-x.y] Handoff`, which carries the
  Validation Pack's Handoff section and the slice's state in the status record. Commits carry the
  trailer [GENAI_CONTRIBUTION.md](../../../GENAI_CONTRIBUTION.md) requires.
- **Bump each document once on the branch.** The release register has a row only for a document's
  current version on `main` (`tools/ontology_releases.py write`), and the trip merges whole. The
  first slice that changes a document bumps it under ADR-A86, classified by the change the whole
  trip makes to it, and later slices change its content without changing `owl:versionIRI`. A
  later slice that turns a MINOR into a MAJOR raises the one bump and says so in its Handoff. New
  documents start at `0.1.0` and stay there until the merge. Imports of LATTICE layers stay pinned
  to the versions of `main` at the branch point, and S never re-pins them.
- **S verifies its own slice before marking it `handed over`.** Run the Validation Pack's single
  command, plus `mise run check:ontology-catalog` and `mise run check:ontology-versioning` when
  the slice touches `ontology/`, and record the result in the Validation Pack's Handoff section.
  If a specific check cannot run in S's environment (for example, a dependency that will not
  resolve even through the configured package mirror), name exactly which command and why, so R
  knows to run that one first. S still cannot regenerate catalogs or create release tags, so it
  bumps `owl:versionIRI` literals and `.version` files by hand under ADR-A86 as before.
- **R re-verifies as the merge gate, not as the first run.** Because S already ran the checks,
  R's run should confirm rather than discover. A failure at this stage that S's own run did not
  catch is worth a note in the Validation Pack — it usually means environment drift between S
  and R, not a routine defect.

## 2. Slices

S slices are commit ranges on `air/applied-reference`. R's slices take their own branches, created
from `main` when their briefs are on it.

| Seq | Slice | Where | Built on | Agent | Start after |
|---|---|---|---|---|---|
| 2 | AIR-3.1 hierarchical match over flat schemes | merged | R | Claude | 1 (merged) |
| 3 | AIR-1.1 drop legacy module, layout | merged | S | Copilot Business | 1 (merged) |
| 4 | AIR-1.2 `classification/`, `insurance/common/` | merged | S | Copilot Business | 3 |
| 5 | AIR-2.1 `prl:` spec, shapes, file regions | merged | S | Copilot Business | 1 (merged) |
| 5a | AIR-2.0 literate `common` and `peril`, extractor, documentation rule | `air/applied-reference` | S | Copilot Business | 4, 5 (merged) |
| 6 | AIR-2.2 characteristic and companion schemes | `air/applied-reference` | S | Copilot Business | 5a |
| 7 | AIR-4.1 exposure core, file regions | `air/applied-reference` | S | Copilot Business | 4 (merged) |
| 8 | AIR-3.2 set readings and negation: Eligibility, IR, SPARQL, SHACL | merged | R | Claude | 2 |
| 9 | AIR-2.3 causes N, T, E | `air/applied-reference` | S | Copilot Business | 6, 14 |
| 10 | AIR-2.4 causes H, P, C, F, L, cross-group links | `air/applied-reference` | S | Copilot Business | 9 |
| 11 | AIR-4.2 zones, pools, attributes, assessments | `air/applied-reference` | S | Copilot Business | 5, 7 |
| 12 | AIR-4.4 loss history, `aeo:LossCause`, requirements, cover | `air/applied-reference` | S | Copilot Business | 6, 7 |
| 13 | AIR-3.3 set readings and negation: SWRL, OWL | `air/3.3-readings-swrl-owl`, created from `main` after CCS HQ-6a.2 merges | R | Claude | 8, HQ-6a.2, AIR-3.3-Q1 |
| 14 | AIR-2.6 intensity measures and thresholds | `air/applied-reference` | S | Copilot Business | 6 |
| 15 | AIR-2.7 pools scheme, example edition, precedence | `air/applied-reference` | S | Copilot Business | 9, 10 |
| 16 | AIR-4.3 dependencies, peril metrics, exposure units | `air/applied-reference` | S | Copilot Business | 9, 11 |
| 17 | AIR-4.5 liability exposure | `air/applied-reference` | S | Copilot Business | 12 |
| 18 | AIR-2.5 collections, open-perils example (M1) | `air/applied-reference` | S | Copilot Business | 10 |
| 19 | AIR-3.4 crosswalk of a market list, lift at ingestion | `air/applied-reference` | S | Copilot Business | 10 |
| 20 | AIR-4.6 London and US profiles, examples (M3) | `air/applied-reference` | S | Copilot Business | 15, 16, 17 |
| 21 | AIR-3.5 lowering, list to list, M2 check | `air/applied-reference` | S | Copilot Business | 12, 19 |
| 22 | AIR-6.1 submission | `air/applied-reference` | S | Copilot Business | 20 |
| 23+ | substrate items: ADR drafts, then S1, S2, S4, S5, S7 | `air/s<n>-<slug>` | R | Claude | 1, each item's ADR |
| 23+ | substrate item S6, spatial guidance (text only) | `air/applied-reference` | S | Copilot Business | 1 |

Sequence 1 is AIR-0.1, merged as `3377a71`. "Start after" lists the sequence numbers that must be
built before S starts the slice. For S slices that means present on `air/applied-reference`, since
S builds in sequence order. R's slices need their predecessors on `main`. The trip merges once
every slice in it has passed its gate (§6). Substrate branches merge after the trip, because each
substrate bump makes every merged applied module re-pin its imports. AIR-3.5 moved from R to S on
2026-10-13: it changes only the crosswalk and the exposure examples, and keeping it on R would
need a second bundle.

The old round 3 branches `air/2.2-characteristics`, `air/4.1-exposure-core` and
`air/3.3-readings-swrl-owl` held only brief commits that `main` already contains. They are not
reused. AIR-3.3 is rebuilt from `main` once CCS slice HQ-6a.2 has merged, because it changes the
set readings that slice extends (status record, Concurrent work).

## 3. The round trip for the S branch

Every command in this section is run by a maintainer. Machine R pushes to the `origin-ssh` remote
(SSH avoids GitHub's HTTP authentication). Machine S only fetches, from `origin`.

### Once: create the branch and delete the old ones

**On R**, from a `main` that holds the plan documents of this revision:

```bash
git switch main && git pull --ff-only
```

```bash
git switch -c air/applied-reference && git push -u origin-ssh air/applied-reference
```

The eight per-slice branches of rounds 1 to 3 are all ancestors of `main`, so `-d` deletes them
and refuses anything that is not:

```bash
git branch -d air/1.1-layout air/1.2-shared-contracts air/2.1-peril-spec air/2.2-characteristics air/3.1-flat-hierarchy air/3.2-set-readings air/3.3-readings-swrl-owl air/4.1-exposure-core
```

```bash
git push origin-ssh --delete air/1.1-layout air/1.2-shared-contracts air/2.1-peril-spec air/2.2-characteristics air/3.1-flat-hierarchy air/3.2-set-readings air/3.3-readings-swrl-owl air/4.1-exposure-core
```

The branch is pushed before S starts, so S can fetch it.

### The trip

**On S**, the first time, take the branch:

```bash
git fetch origin && git switch -c air/applied-reference --track origin/air/applied-reference
```

The agent reads the status record, then builds every slice of the trip in sequence order (§4,
§5). It verifies each slice before its handoff commit: the Validation Pack's single command, plus
the ontology catalog and versioning checks if the slice touches `ontology/`. It records the result
in the Validation Pack's Handoff section. A pass here means R's later verification confirms rather
than discovers. A slice blocked on a question is skipped as §1 says, and the agent comes back to it
when the question is answered.

S never fetches `main` during the trip and never merges it into the branch. The branch is
self-consistent at its branch point, and R brings it up to date once, at the merge (§6).

The trip is long, so S may write a backup bundle whenever it likes, with the bundle command below.
A backup stays on S. It is not carried to R and nothing is merged from it.

**On S**, bundle the trip:

```bash
git fetch origin && git bundle create air-trip.bundle origin/air/applied-reference..air/applied-reference
```

Carry the file to R. One bundle holds every slice of the trip, so the physical handoff happens once.

**On R**, take the commits and push them:

```bash
git switch air/applied-reference && git pull --ff-only /path/to/air-trip.bundle air/applied-reference && git push origin-ssh
```

Then verify each slice in order, and merge the trip (§6). S makes no commit on the branch after it
bundles. If R returns slices that failed their gate (§6 step 2), the maintainer refreshes S with
`git fetch origin && git merge --ff-only origin/air/applied-reference` and S fixes them on the
branch as a short second trip.

## 4. The trip

One trip on S holds every slice that does not wait on CCS or NRS. R builds AIR-3.3 and the
substrate ADRs meanwhile, beside the CCS and FML epics. The plan assumes every verification
passes. A failed slice, and every slice after it that depends on it, goes back to S as a short
second trip (§3), unless R can merge a verified prefix (§6).

| Order | Slice | Milestone |
|---|---|---|
| 0 | AIR-2.0 literate modules, extractor, documentation rule | |
| 1 | AIR-2.2 characteristic and companion schemes | |
| 2 | AIR-4.1 exposure core | |
| 3 | AIR-2.6 intensity measures and thresholds | |
| 4 | AIR-2.3 causes N, T, E | |
| 5 | AIR-2.4 causes H, P, C, F, L, cross-group links | |
| 6 | AIR-4.2 zones, pools participation, attributes, assessments | |
| 7 | AIR-4.3 dependencies, peril metrics, exposure units | |
| 8 | AIR-4.4 loss experience, `aeo:LossCause`, requirements, cover | |
| 9 | AIR-2.7 pools scheme, example edition, precedence | |
| 10 | AIR-4.5 liability exposure | |
| 11 | AIR-2.5 collections, open-perils example | M1 |
| 12 | AIR-3.4 crosswalk of a market list, lift at ingestion | |
| 13 | AIR-3.5 lowering, list to list, M2 check | M2 |
| 14 | AIR-4.6 London and US profiles, examples | M3 |
| 15 | AIR-6.1 submission | |
| 16 | S6 spatial guidance (text only) | |

AIR-4.3 precedes AIR-4.4 (revised 2026-10-13, at the AIR-4.4 brief): a requirement's scope is an
admission profile over exposure units, which AIR-4.3 declares.

AIR-2.6 precedes the cause families (revised 2026-10-13): the threshold shape requires every
concept with basis Threshold to have a `prl:definingThreshold`, so the thresholds must exist when
AIR-2.3 assigns that basis. AIR-2.6 writes the threshold range sets and every link from a cause
concept to its intensity measures and threshold, naming cause concepts by IRI before AIR-2.3
declares them.

Not in the trip, and why:

| Work | Waits on |
|---|---|
| AIR-3.3 | CCS HQ-6a.2 and AIR-3.3-Q1. Built on R on its own branch |
| Phase 5, AIR-6.2 onward | CCS C9 and the Open CBAA integration of Phases 1 to 4 (D2) |
| Substrate S2, S7 | CCS C9b3 and NRS N10 |
| Substrate S1, S4, S5 | change layers CCS is still bumping. Merged after the trip |

Round numbers are kept from the earlier plan so the status record's history still reads. The trip
is round 3.

## 5. Tracking progress: the status record

The [status record](../status/applied-insurance-reference.md) is the single record for the epic.
No per-phase status records are created. It has one section per machine, so the two machines'
edits never touch the same lines:

| Section | Written by | Content |
|---|---|---|
| Round | R | the current round, the trip's slice order, and the briefs on the branch |
| Machine R | R | position, blockers, R's slice board, the queue of S slices awaiting verification |
| Machine S | S | position, blockers, S's slice board |
| Merge log, Phases | R | one row per merged slice, and each phase's state |

A slice moves through these states. The machine named in the last column sets each one:

| State | Meaning | Set by |
|---|---|---|
| `waiting` | a slice it starts after is not yet built | — |
| `waiting for brief` | its brief is not yet on the branch | R, when it drafts the brief |
| `ready` | its brief is on the branch and the slices it starts after are built | R, when it writes the brief, or S, when it finishes the slices it starts after |
| `in progress` | the agent is building it | the building machine |
| `handed over` | S's handoff commit exists and we have bundled it to R | S |
| `built` | R's own work is committed and ready to verify | R |
| `verifying` | R is running its checks (§6) | R |
| `gate passed` | the maintainer has run the validation gate and recorded the adversarial probe in the status record | R |
| `merged` | it is on `main`, with a row in the merge log | R |

**Handoff notes go in the Validation Pack**, `docs/developer/validation/applied-insurance-reference-<slice>.md`,
which each slice creates. The building machine adds a "Handoff" section: what it built, what it
ran and could not run, and anything R should check first. Keeping these notes out of the status
record keeps S's commits and R's apart.

**At the start of a session**, an agent reads the status record on its checked-out branch, then
its slice's phase plan and Validation Pack. **At the end of each slice**, it updates its own
section (position, the slice's state, blockers) in the slice's handoff commit. Machine S never
edits the Round, Machine R, Merge log or Phases sections. R edits them on the branch after taking
S's bundle, so the two machines' commits never touch the same lines. When a merge of `main`
conflicts in the status record, keep each section's newest version. The sections are disjoint, so
this never loses information.

## 6. Verifying and merging on R

For the trip, once S's bundle is on the branch (§3):

1. **Verify each slice at its handoff commit (agent).** Check out the slice's `[AIR-x.y] Handoff`
   commit and run the same commands S already ran: the Validation Pack's single command, plus
   `mise run check:ontology-catalog` and `mise run check:ontology-versioning` when the slice touches
   `ontology/`. This confirms S's recorded result, unless S's Handoff section named a check it could
   not run, in which case R runs that one for the first time here. Then run the same commands at the
   branch tail.
2. **Fix failures (agent).** Copilot Pro+ first for simple ones. Claude when the fix needs a design
   judgement. Fixes are new commits on the tail, `[AIR-x.y] Fix …`, and every slice a fix touches
   is verified again. A failure that S's own self-verification passed is worth flagging as
   environment drift. If a failed slice cannot be fixed in the trip, R merges the verified prefix of
   the trip and returns the rest, re-bumping versions where step 4 applies.
3. **Sync with `main` (maintainer, then agent).** The maintainer runs
   `git switch main && git pull --ff-only && git switch air/applied-reference && git merge main`.
   The branch is never rebased and never force-pushed, because S fast-forwards to it. The agent helps
   resolve conflicting files. This happens once, after the trip's slices are verified at their
   handoff commits.
4. **Re-pin once (agent).** The branch's imports are pinned to the layer versions of `main` at the
   branch point (§1). Re-pin every applied module the trip changes to the current versions on
   `main`, and if `main` has bumped a document the trip also changes, take `main`'s version and bump
   once more under ADR-A86. Run each slice's Validation Pack command again at the tail, since the
   newer layers may break a test. Commit it as `[AIR] Re-pin …`.
5. **Regenerate catalogs and release rows (agent).** `mise run build:ontology-catalog`, and after
   any version bump `mise run build:ontology-releases`, which adds a row to
   `docs/architecture/ontology-releases.md` for each new version and lists the tags to create.
   Commit the result on the branch, then run the trip's checks once more.
6. **The validation gate (maintainer).** For each slice, in order, the maintainer reviews the pack,
   runs its command, inspects the artefacts and sets one adversarial probe. The agent breaks the
   implementation, shows the test fails, restores it, and records each probe and its result in the
   status record. The maintainer's merge is the sign-off.
7. **Record (agent).** On the branch: each slice's state becomes `merged`, a merge log row is added
   per slice, and the epic's `INDEX.md` entry is updated.
8. **Merge (maintainer).** `git switch main && git merge --ff-only air/applied-reference`, then
   `git push origin-ssh main`. Create the release tags step 5 listed and push them to `origin-ssh`.
   The branch is deleted after the merge, unless a second trip is due (§3).

The handoff ends with `🔴 RELEASE TAGS REQUIRED` while tags remain to create (the lifecycle skill).

## 7. Critical path

All on S: 2.0 → 2.2 → 2.6 → 2.3 → 2.4 → 3.4 → 3.5 (M2). Loss history (4.4) is on it too, because 3.5 reads
`aeo:LossCause`. The trip's length is the sum of S's slices, since S builds in sequence.

## 8. Rules for shared files

| File | Rule |
|---|---|
| `ontology/catalog-v001.xml` and the stub catalogs | regenerated on R only (§6 step 5). Never edited or merged by hand |
| `owl:versionIRI` literals and `.version` files | S bumps them by hand, once per document on the branch (§1). R checks them, and re-bumps where §6 step 4 applies |
| `insurance/peril/vocab/peril-vocab.ttl` | AIR-2.1 creates it with one delimited region per characteristic scheme, one per cause family and a final cross-group links region. AIR-2.2 writes the characteristic regions, AIR-2.3 the N, T and E regions, AIR-2.4 the H, P, C, F and L regions and every link between the two groups. Intensity links (AIR-2.6) go in `peril-intensity.ttl` |
| `insurance/exposure/spec/exposure.ttl` and its shapes | AIR-4.1 creates one region per slice of Phase 4. Each slice writes only its region |
| `ontology/applied/README.md`, `ontology-architecture.md` §3 | one row per module, added by the slice that creates the module |
| the status record | each machine edits only its own section (§5) |
| `docs/developer/INDEX.md` | R updates the epic's entry at the trip's merge (§6 step 7) |
