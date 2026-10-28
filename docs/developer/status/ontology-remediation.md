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
| OR-3, OR-5 to OR-19 | pending |

## History

- 2026-10-28: the review, in `.local` first, then placed. The maintainer ruled on §2.1 (remove and reword, no history rewrite), §2.2, §2.4, §2.5, §2.6 and the mutable parts, chose the identifier uniqueness check as a hook with first in wins, declined versioning for `voc:SchemeBinding`, and asked for the rename of `fnd:Version`. OR-0 placed.
- 2026-10-28: the maintainer answered OR-Q1 to OR-Q11 and OR-Q14 to OR-Q16 as recommended, fixed the namespaces (decision 12) and kept the release bump (decision 13). OR-Q12 and OR-Q13 open. Autonomous mode on `main` begins with OR-1.
- 2026-10-28: OR-1 and OR-2 built and committed. `check:identifiers` (12 tests), `check:hooks` (32) and `check:agent-guidance` (9) pass.
- 2026-10-28: OR-4 built and committed. Ran and passed: `check:persistence` (3976), `check:mork` (361), `check:reference-eligibility` (60), `check:identifiers` (12), `check:knowledge` (117), the literate grammar tests (183), the commit hook. `check:ontology-versioning` reports UNBUMPED for the 12 changed release members, which is the expected state until the maintainer runs `release:prepare` (decision 13). `check:ontology-catalog` has two failures that predate this unit, `test_reasoning_isolation` and the shared-specifier test, both from the agent worktrees under `.claude/worktrees/` that the tests walk.
