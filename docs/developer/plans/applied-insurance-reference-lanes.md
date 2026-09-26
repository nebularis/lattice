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

Two rules follow:

- **Only R creates branches, pushes and merges.** S pulls, works and hands its commits back as a
  bundle (§3).
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
(§5). When several are ready, R merges them in sequence order. Substrate branches merge after
AIR-6.1, because each substrate bump makes every merged applied module re-pin its imports.

## 3. The round trip for an S slice

**On R**, create and push the branch:

```bash
git switch main && git pull --ff-only
```

```bash
git switch -c air/1.1-layout && git push -u origin air/1.1-layout
```

**On S**, pick it up, work, and bundle the commits:

```bash
git fetch origin && git switch air/1.1-layout
```

```bash
git bundle create air-1.1.bundle origin/air/1.1-layout..air/1.1-layout
```

Carry the bundle file to R.

**On R**, take the commits and push them:

```bash
git switch air/1.1-layout && git pull --ff-only /path/to/air-1.1.bundle air/1.1-layout && git push
```

Then verify, sign off and merge (§5). After R pushes `main`, **on S** refresh before the next
slice:

```bash
git fetch origin && git switch main && git pull --ff-only
```

Several S branches can travel in one trip: bundle each one, carry them together.

## 4. Rounds

A round is one working session on each machine, ending with R verifying and merging what both
produced. R and S work at the same time within a round. The plan assumes every verification
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

## 5. Verifying and merging on R

For each branch, in the order of the round's merge column:

1. **Rebase** onto the current `main`, then `git push --force-with-lease`.
2. **Regenerate catalogs:** `mise run build:ontology-catalog`. Commit the result on the branch.
3. **Re-bump versions if needed.** If a merge since the branch was created bumped a document
   this branch also changes, take `main`'s version, bump again under ADR-A86, and re-pin the
   importers already on `main`.
4. **Run the checks:** the Validation Pack's single command, plus `mise run
   check:ontology-catalog` and `mise run check:ontology-versioning` when the slice touches
   `ontology/`.
5. **Fix failures.** Copilot Pro+ first for simple ones. Claude when the fix needs a design
   judgement.
6. **Sign off.** The human runs the validation gate (review the pack, run the command, inspect
   the artefacts, one adversarial probe) and adds the slice to `docs/developer/validation/LOG.md`.
7. **Merge:** update the slice's rows in its phase status record and `INDEX.md` on the branch,
   then `git switch main && git merge --ff-only air/<slice>` and `git push`. Delete the branch.

## 6. Critical path

2.1 and 1.1 → 1.2 → 2.2 → 2.4 → 3.4 → 3.5 (M2), all but the last on S. Loss history (4.4) is
also on the path, because 3.5 reads `aeo:LossCause`.

## 7. Rules for shared files

| File | Rule |
|---|---|
| `ontology/catalog-v001.xml` and the stub catalogs | regenerated on R only (§5 step 2). Never edited or merged by hand |
| `owl:versionIRI` literals and `.version` files | S bumps them by hand. R checks them, and re-bumps after rebasing where §5 step 3 applies |
| `insurance/peril/vocab/peril-vocab.ttl` | AIR-2.1 creates it with one delimited region per characteristic scheme, one per cause family and a final cross-group links region. AIR-2.2 writes the characteristic regions, AIR-2.3 the N, T and E regions, AIR-2.4 the H, P, C, F and L regions and every link between the two groups. Intensity links (AIR-2.6) go in `peril-intensity.ttl` |
| `insurance/exposure/spec/exposure.ttl` and its shapes | AIR-4.1 creates one region per slice of Phase 4. Each slice writes only its region |
| `ontology/applied/README.md`, `ontology-architecture.md` §3 | one row per module, added by the slice that creates the module |
| `docs/developer/INDEX.md`, phase status records | each slice edits only its own rows, at merge (§5 step 7) |
| `docs/developer/validation/LOG.md` | the human's only |
