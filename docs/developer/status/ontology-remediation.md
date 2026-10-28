<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ontology remediation: status

**Unit ID:** `ontology-remediation`
**Plan:** [ontology-remediation.md](../plans/ontology-remediation.md)
**Review:** [ontology-design-review.md](../review/ontology-design-review.md)
**Branch:** `main`, from `52686215`
**Mode:** autonomous, at the maintainer's request on 2026-10-28. Each slice is committed to `main`. Nothing is pushed and no branch is merged by this unit.

## Position

| Slice | State |
|---|---|
| OR-0 | placed: the plan, this record, the review, TD-101 to TD-113 |
| OR-1 | built: `identifiers.py` reports a duplicate definition with both sites and their commit dates, the hooks run it at a commit and a merge, `post-merge` rebuilds the index, ADR-A133 addendum, 4 tests |
| OR-2 | built: the skill `lattice-branching`, listed in `AGENTS.md` and the Copilot copy |
| OR-4 | built: `fnd:Version` is `fnd:Versioned` in 100 files, ADR-A136 (Proposed), the Foundation release note, TD-20 closed, PDD-13 raised for the ADR-A113 and ADR-A127 conflict |
| OR-3 | built: twelve deprecated Surface documents, three duplicates and the stale migration index deleted, links rehomed, the misnamed execution README renamed, 25 working-document references out of user-facing text, the names outside the project reworded in 14 files, prompt residue and the vendor identifier removed |
| OR-5 | built: the overview retired (TD-114 for the table the import guard reads), the version lines in three READMEs, the versioning policy's two regimes scoped, Party's unused import, MORK's unmeasured figures and unproven claims reworded, the SPC companion marked non-normative. Not done: the release register's ledger row, which the maintainer's bump regenerates |
| OR-7 | part built, OR-7a: `fnd:meaningBearing`, the Foundation shape, the compiler refusal `MeaningBearingEdgeByIdentity` with 3 tests, ADR-A137 (Proposed), STD-284. Pending: the four instances in Eligibility, Behaviour, Vocabulary (the closure record) and Party, and Foundation's governance state |
| OR-6 | built: SPC and the store vocabulary under the lattice root, `persistence-store` published with 43 terms, the applied insurance root gains the lattice segment, ADR-A62 executed |
| OR-8, OR-14 | built: supersession acyclic, validity periods half-open and zoned, `fnd:estimatedStart`, Q14 |
| OR-9 | built: ADR-A138, Surface, Quantification and MCN name their content and rule |
| OR-12 | built: the allowance classes deprecated with warning shapes, TD-115 |
| OR-18 | built: the Instrument README pruned by a subagent, 6,342 to 5,512 lines |
| OR-7b | built: the closure record in Vocabulary with its resolver and shape, meaning-bearing edges in Behaviour and Eligibility, the versioned fill of an occupancy in Party, the governance state in Foundation. Ledger's definition is LG-2's (TD-102) |
| OR-10 | built in part: the uniqueness and concurrency claims reworded, the closing patterns marked as not generated, the vacuous namespace comparison fixed. The dataset-level baseline was tried and reverted, TD-118 |
| OR-11 | built: laws as individuals, Q8's operation, Q13's shape, Q14, Surface's X5 and X6 wording, SPC's three uniqueness shapes. Discharges of Q1 to Q8 remain (TD-116) |
| OR-13 | built by a subagent: five rules, four named errors, vectors in both libraries and the anchors |
| OR-15 | built in part: `check:owl-profile` with its baseline (TD-117). The placement of the three-way names waits on OR-Q12 |
| OR-16 | built: Capacity withdrawn from release, its performance note routed through Persistence. The file rename waits for the bump |
| OR-17 | built in part: Foundation's structural shapes, six empty files deleted, Eligibility's AllDifferent, Persistence's namespace comparison. Quantification's twelve obligations and the Wording and Vocabulary shape defects remain (TD-110) |
| OR-19 | the release notes are written in every changed README. The bump and the tags are the maintainer's |

## History

- 2026-10-28: the review, in `.local` first, then placed. The maintainer ruled on §2.1 (remove and reword, no history rewrite), §2.2, §2.4, §2.5, §2.6 and the mutable parts, chose the identifier uniqueness check as a hook with first in wins, declined versioning for `voc:SchemeBinding`, and asked for the rename of `fnd:Version`. OR-0 placed.
- 2026-10-28: the maintainer answered OR-Q1 to OR-Q11 and OR-Q14 to OR-Q16 as recommended, fixed the namespaces (decision 12) and kept the release bump (decision 13). OR-Q12 and OR-Q13 open. Autonomous mode on `main` begins with OR-1.
- 2026-10-28: OR-1 and OR-2 built and committed. `check:identifiers` (12 tests), `check:hooks` (32) and `check:agent-guidance` (9) pass.
- 2026-10-28: OR-4 built and committed. Ran and passed: `check:persistence` (3976), `check:mork` (361), `check:reference-eligibility` (60), `check:identifiers` (12), `check:knowledge` (117), the literate grammar tests (183), the commit hook. `check:ontology-versioning` reports UNBUMPED for the 12 changed release members, which is the expected state until the maintainer runs `release:prepare` (decision 13). `check:ontology-catalog` has two failures that predate this unit, `test_reasoning_isolation` and the shared-specifier test, both from the agent worktrees under `.claude/worktrees/` that the tests walk.
- 2026-10-28: OR-3 (with one Sonnet subagent on the mechanical part), OR-5 and OR-7a built and committed. Ran and passed: the commit hook on each commit, `check:published-decisions` (0 failures), `check:catalogue`, `check:site-sections`, the persistence reference-mode tests (22), `check:identifiers`, `check:knowledge`. Open for the maintainer: OR-Q12 and OR-Q13, the acronyms of the private source in five sketches and the legacy MORK pipeline, and ADR-A106 and a few other decisions that still link working documents.
- 2026-10-28: the maintainer deferred OR-Q12 to the end of the unit, chose the organisation as creator (OR-Q13, applied in every spec and vocab document), and confirmed one bump at the end of the unit.
- 2026-10-28: OR-6 (one Sonnet subagent on the store vocabulary), OR-8, OR-9, OR-12, OR-14 and OR-18 (a second subagent) built and committed. TD-101, TD-106, TD-107 and TD-109 close. The OR-7a refusal gained its witness.
- 2026-10-28, end of the session: OR-7b, OR-10, OR-11, OR-13, OR-15, OR-16, OR-17 and OR-19's notes built. The dataset-level epoch baseline was reverted after it left the no-receipt builders without a template (TD-118). Open for the maintainer: OR-Q12, the release bump, ADR-A136 to ADR-A138 to accept, the acronyms of the private source still in five sketches and the legacy MORK pipeline, ADR-A106 and a few decisions linking working documents, the NFC question from OR-13, the applied exposure example's key schemes that fail Foundation's shape, and three applied modules needing a minor bump for their new root.
