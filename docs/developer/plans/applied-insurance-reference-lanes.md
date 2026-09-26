<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Insurance Reference — Machines, Branches and Merges

**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Purpose:** which machine and agent builds each slice, on which branch, in which round, and who
merges what. Slice content stays in the phase plans.

## 1. Machines and agents

| Machine | Can | Cannot | Agents | Used for |
|---|---|---|---|---|
| **R**, runtime | run `mise`, Python, Java, every check. Push to GitHub. Merge | — | **Claude Code**, **Copilot Pro+** | Claude: compiler and substrate code, ADRs, verifying design-heavy branches. Copilot Pro+: running a branch's checks and fixing simple failures |
| **S**, sandbox | edit anything, commit, pull from GitHub | run tests or checks, push | **Copilot Business** (the largest budget) | Turtle, SHACL, examples, READMEs, and simple code edits. Never complex code, since it cannot be tested there |

Three rules follow:

- **The human runs the branching and merging.** Agents must not run the git commands this plan
  gives for creating, switching, fetching, pulling, pushing, bundling, rebasing or merging
  branches (§3, §6). They may run any other local git command their normal workflow needs, such
  as `git status`, `git diff`, `git log` or committing on the branch the human has checked out.
  When a step needs one of the human's commands, the agent stops and says so. The one exception:
  machine R's agent may run them when the human explicitly asks it to. Machine S's agent never
  does.
- **Branches are created, pushed and merged on R only.** S pulls, works and hands its commits
  back as a bundle (§3).
- **Brief before branch.** A slice's branch is created only once its brief is written: an "in
  detail" section in its phase plan and a Validation Pack skeleton, both on `main`. Rolling-wave
  slices are outlines until R drafts them. Whenever machine R's agent reports what comes next, it
  ends with exactly one of these, on its own line:
  - `🔴 PLAN FIRST: AIR-x.y needs its brief drafted on main before you branch.` It lists every
    such slice, and R drafts them before anything else.
  - `🟢 READY TO BRANCH: create and push air/<slice>, …` It names every branch whose brief is
    on `main` and whose "Branch after" slices have merged.
- **Every S branch is verified on R before it merges.** S cannot regenerate catalogs or run the
  versioning check, so it bumps `owl:versionIRI` literals and `.version` files by hand under
  ADR-A86, and R checks them.

## 2. Slices

Branch names are fixed here, so both machines use the same ones.

| Seq | Slice | Branch | Built on | Agent | Branch after |
|---|---|---|---|---|---|
| 2 | AIR-3.1 hierarchical match over flat schemes | `air/3.1-flat-hierarchy` | R | Claude | 1 (merged) |
| 3 | AIR-1.1 drop legacy module, layout | `air/1.1-layout` | S | Copilot Business | 1 (merged) |
| 4 | AIR-1.2 `classification/`, `insurance/common/` | `air/1.2-shared-contracts` | S | Copilot Business | 3 |
| 5 | AIR-2.1 `prl:` spec, shapes, file regions | `air/2.1-peril-spec` | S | Copilot Business | 1 (merged) |
| 6 | AIR-2.2 characteristic and companion schemes | `air/2.2-characteristics` | S | Copilot Business | 4, 5 |
| 7 | AIR-4.1 exposure core, file regions | `air/4.1-exposure-core` | S | Copilot Business | 4 |
| 8 | AIR-3.2 set readings and negation: Eligibility, IR, SPARQL, SHACL | `air/3.2-set-readings` | R | Claude | 2 |
| 9 | AIR-2.3 causes N, T, E | `air/2.3-causes-n-t-e` | S | Copilot Business | 6 |
| 10 | AIR-2.4 causes H, P, C, F, L, cross-group links | `air/2.4-causes-h-p-c-f-l` | S | Copilot Business | 6 |
| 11 | AIR-4.2 zones, pools, attributes, assessments | `air/4.2-zones-attributes` | S | Copilot Business | 5, 7 |
| 12 | AIR-4.4 loss history, `aeo:LossCause`, requirements, cover | `air/4.4-loss-history` | S | Copilot Business | 6, 7 |
| 13 | AIR-3.3 set readings and negation: SWRL, OWL | `air/3.3-readings-swrl-owl` | R | Claude | 8 |
| 14 | AIR-2.6 intensity measures and thresholds | `air/2.6-intensity` | S | Copilot Business | 9 |
| 15 | AIR-2.7 pools scheme, example edition, precedence | `air/2.7-pools-editions` | S | Copilot Business | 9, 10 |
| 16 | AIR-4.3 dependencies, peril metrics, exposure units | `air/4.3-exposure-units` | S | Copilot Business | 9, 11 |
| 17 | AIR-4.5 liability exposure | `air/4.5-liability` | S | Copilot Business | 12 |
| 18 | AIR-2.5 collections, open-perils example (M1) | `air/2.5-collections` | S | Copilot Business | 10 |
| 19 | AIR-3.4 crosswalk of a market list, lift at ingestion | `air/3.4-crosswalk` | S | Copilot Business | 10 |
| 20 | AIR-4.6 London and US profiles, examples (M3) | `air/4.6-market-profiles` | S | Copilot Business | 15, 16, 17 |
| 21 | AIR-3.5 lowering, list to list, M2 check | `air/3.5-m2-check` | R | Claude | 12, 19 |
| 22 | AIR-6.1 submission | `air/6.1-submission` | S | Copilot Business | 20 |
| 23+ | substrate items: ADR drafts, then S1, S2, S4, S5, S7 | `air/s<n>-<slug>` | R | Claude | 1, each item's ADR |
| 23+ | substrate item S6, spatial guidance (text only) | `air/s6-spatial-guidance` | S | Copilot Business | 1 |

Sequence 1 is AIR-0.1, merged as `3377a71`. "Branch after" lists the sequence numbers that must
be on `main` before R creates the branch. A branch merges once it is verified and signed off
(§6). When several are ready, R merges them in sequence order. Substrate branches merge after
AIR-6.1, because each substrate bump makes every merged applied module re-pin its imports.

## 3. The round trip for an S slice

Every command in this section is run by the human. Machine R pushes to the `origin-ssh` remote
(SSH avoids GitHub's HTTP authentication). Machine S only fetches, from `origin`.

**On R**, create and push the branch:

```bash
git switch main && git pull --ff-only
```

```bash
git switch -c air/1.1-layout && git push -u origin-ssh air/1.1-layout
```

**On S**, pick it up, let the agent work, and bundle the commits:

```bash
git fetch origin && git switch air/1.1-layout
```

```bash
git bundle create air-1.1.bundle origin/air/1.1-layout..air/1.1-layout
```

Carry the bundle file to R.

**On R**, take the commits and push them:

```bash
git switch air/1.1-layout && git pull --ff-only /path/to/air-1.1.bundle air/1.1-layout && git push origin-ssh
```

Then verify, sign off and merge (§6). After R pushes `main`, **on S** refresh before the next
slice:

```bash
git fetch origin && git switch main && git pull --ff-only
```

Several S branches can travel in one trip: bundle each one, carry them together.

## 4. Rounds

A round is one working session on each machine, ending with R verifying and merging what both
produced. A round's last step is R's 🔴 or 🟢 announcement (§1) for the branches
in its last column. R and S work at the same time within a round. The plan assumes every verification
passes. A failed one moves that branch's merge to the next round.

| Round | R builds (Claude) | S builds (Copilot Business) | R verifies, then merges in this order | R then creates and pushes |
|---|---|---|---|---|
| 0 | — | — | — | `air/3.1-flat-hierarchy`, `air/1.1-layout`, `air/2.1-peril-spec` |
| 1 | 3.1 | 1.1, then 2.1 | 3.1, 1.1, 2.1 | `air/1.2-shared-contracts`, `air/3.2-set-readings` |
| 2 | 3.2 | 1.2 | 1.2, 3.2 | `air/2.2-characteristics`, `air/4.1-exposure-core`, `air/3.3-readings-swrl-owl` |
| 3 | 3.3 | 2.2, then 4.1 | 2.2, 4.1, 3.3 | `air/2.3-causes-n-t-e`, `air/2.4-causes-h-p-c-f-l`, `air/4.2-zones-attributes`, `air/4.4-loss-history` |
| 4 | substrate ADRs (S1, S2, S4, S5, S7) | 2.3, then 2.4 | 2.3, 2.4 | `air/2.5-collections`, `air/2.6-intensity`, `air/2.7-pools-editions`, `air/3.4-crosswalk` |
| 5 | substrate S2 | 4.2, 4.4, then 3.4 | 4.2, 4.4, 3.4 | `air/4.3-exposure-units`, `air/4.5-liability`, `air/3.5-m2-check` |
| 6 | 3.5 | 2.6, 2.7, then 2.5 | 2.6, 2.7, 2.5 (M1), 3.5 (M2) | — |
| 7 | substrate S1, S7 | 4.3, then 4.5 | 4.3, 4.5 | `air/4.6-market-profiles` |
| 8 | substrate S5, S4 | 4.6, then S6 | 4.6 (M3) | `air/6.1-submission` |
| 9 | verification | 6.1 | 6.1, then S6, S1, S7, S2, S5, S4 | — |

S is the bottleneck, carrying 17 slices to R's 4 plus the substrate. In rounds 4 to 8, R's spare
capacity goes to substrate work, which is off the critical path. If S falls behind, move 4.4 and
4.5 to R: they are Turtle and examples, which Claude or Copilot Pro+ can build.

## 5. Tracking progress: the status record

The [status record](../status/applied-insurance-reference.md) is the single record for the epic.
No per-phase status records are created. It has one section per machine, so the two machines'
edits never touch the same lines:

| Section | Written by | Content |
|---|---|---|
| Round | R | the current round, and the branches ready to work on |
| Machine R | R | position, blockers, R's slice board, the queue of S branches awaiting verification |
| Machine S | S | position, blockers, S's slice board |
| Merge log, Phases | R | one row per merge, and each phase's state |

A slice moves through these states. The machine named in the last column sets each one:

| State | Meaning | Set by |
|---|---|---|
| `waiting` | its "Branch after" slices are not all on `main` | — |
| `waiting for branch` | it may start once the human creates its branch | R, at the end of a round |
| `in progress` | the agent is building it on its branch | the building machine |
| `handed over` | S's work is committed and the human has bundled it to R | S |
| `built` | R's own work is committed and ready to verify | R |
| `verifying` | R is running its checks (§6) | R |
| `signed off` | the human has recorded it in `LOG.md` | R |
| `merged` | it is on `main`, with a row in the merge log | R |

**Handoff notes go in the Validation Pack**, `docs/developer/validation/applied-insurance-reference-<slice>.md`,
which each slice creates. The building machine adds a "Handoff" section: what it built, what it
could not run, and anything R should check first. On S that section is required, since nothing
there was tested. Keeping these notes out of the status record means two branches never edit
the same lines of it.

**At the start of a session**, an agent reads the status record on its checked-out branch, then
its slice's phase plan and Validation Pack. **At the end**, it updates its own section (position,
the slice's state, blockers) in the same commit as its work. Machine S never edits the Round,
Machine R, Merge log or Phases sections. When a rebase conflicts in the status record, keep each
section's newest version: the sections are disjoint, so this never loses information.

## 6. Verifying and merging on R

For each branch, in the order of the round's merge column:

1. **Rebase (human).** `git rebase main` on the branch, then `git push --force-with-lease origin-ssh air/<slice>`. The
   agent may help resolve conflicting files, and the human continues the rebase.
2. **Regenerate catalogs and release rows (agent):** `mise run build:ontology-catalog`, and after
   any version bump `mise run build:ontology-releases`, which adds a row to
   `docs/architecture/ontology-releases.md` for each new version and lists the tags to create.
   Commit the result on the branch.
3. **Re-bump versions if needed (agent).** If a merge since the branch was created bumped a document
   this branch also changes, take `main`'s version, bump again under ADR-A86, and re-pin the
   importers already on `main`.
4. **Run the checks (agent):** the Validation Pack's single command, plus `mise run
   check:ontology-catalog` and `mise run check:ontology-versioning` when the slice touches
   `ontology/`.
5. **Fix failures (agent).** Copilot Pro+ first for simple ones. Claude when the fix needs a design
   judgement.
6. **Sign off (human).** The human runs the validation gate (review the pack, run the command, inspect
   the artefacts, one adversarial probe) and adds the slice to `docs/developer/validation/LOG.md`.
7. **Record (agent).** On the branch: the slice's state becomes `merged` in its machine's
   section, a merge log row is added, and at a round's last merge the Round section and the
   epic's `INDEX.md` entry are updated.
8. **Merge (human).** `git switch main && git merge --ff-only air/<slice>`, then `git push origin-ssh main`.
   Create the release tags step 2 listed and push them to `origin-ssh`. Delete the branch.

## 7. Critical path

2.1 and 1.1 → 1.2 → 2.2 → 2.4 → 3.4 → 3.5 (M2), all but the last on S. Loss history (4.4) is
also on the path, because 3.5 reads `aeo:LossCause`.

## 8. Rules for shared files

| File | Rule |
|---|---|
| `ontology/catalog-v001.xml` and the stub catalogs | regenerated on R only (§6 step 2). Never edited or merged by hand |
| `owl:versionIRI` literals and `.version` files | S bumps them by hand. R checks them, and re-bumps after rebasing where §6 step 3 applies |
| `insurance/peril/vocab/peril-vocab.ttl` | AIR-2.1 creates it with one delimited region per characteristic scheme, one per cause family and a final cross-group links region. AIR-2.2 writes the characteristic regions, AIR-2.3 the N, T and E regions, AIR-2.4 the H, P, C, F and L regions and every link between the two groups. Intensity links (AIR-2.6) go in `peril-intensity.ttl` |
| `insurance/exposure/spec/exposure.ttl` and its shapes | AIR-4.1 creates one region per slice of Phase 4. Each slice writes only its region |
| `ontology/applied/README.md`, `ontology-architecture.md` §3 | one row per module, added by the slice that creates the module |
| the status record | each machine edits only its own section (§5) |
| `docs/developer/INDEX.md` | R updates the epic's entry at each round's last merge (§6 step 7) |
| `docs/developer/validation/LOG.md` | the human's only |
