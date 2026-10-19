<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: RC3, the rest of the catalogue

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice RC3
([plan](../plans/improved-ontology-documentation.md#slices)).
**Implements:** [ADR-A121](../../architecture/decisions/ADR-A121-repository-catalogue.md) decisions 1, 4, 5 and 6,
and decisions OD-D40, OD-D41, OD-D51, OD-D52 and OD-D53 of the plan.
**Built autonomously**, at the maintainer's request of 2026-10-19. The decisions taken alone are listed below,
for the maintainer to keep or overrule.

## Invariant

The root file declares every root, tool package, documentation area and generated path, and `mise run
check:catalogue` fails when a declared path is missing (unless generated) or a tool package on disk is not
declared. The "Where things are" table in `AGENTS.md` is written from those declarations and from nothing
else, and equals the table it replaced. Python under `tools/` that builds a path to a catalogued root itself
is listed with a reason, in a list that can only shrink, and its count is stated once in the technical debt
register.

## What changed

- `repository-catalogue.md`. Four new blocks with prose: `roots` (11 entries), `tools` (8 tool packages),
  `docs` (3 areas, including `.claude/skills/`) and `generated` (3 paths).
- `tools/lattice_repo_catalogue.py`.
  - The reader and schema take `[[roots]]`, `[[docs]]`, `[[tools]]` and `[generated]`, and refuse unknown keys,
    wrong types, a missing required key and a malformed group.
  - **`where_things_are()`** writes the table.
  - **`check()`** also checks declared paths and undeclared tool packages.
  - **`bypass_scan()`** is the report-only scan, wired into `check` and the `check` command.
  - `dump --json` carries the new data.
- `tools/agent_guidance.py`. `build` writes the region in `AGENTS.md` and then Copilot's file from it. `check`
  fails on a stale region. **`render_agents()`** replaces the region.
- `AGENTS.md` and `.github/copilot-instructions.md`. The table sits between `BEGIN GENERATED` and `END
  GENERATED` markers. The table's text is unchanged.
- `tools/lattice_repo_catalogue_exceptions.txt`. The 12 known files, each with a reason.
- `docs/developer/plans/technical-debt.md`. Row TD-54 names the file and gives its count.
- `docs/architecture/decisions/ADR-A121-repository-catalogue.md`. The addendum of 2026-10-19.
- `mise.toml`. Three task descriptions.
- `.claude/skills/lattice-toolchain/SKILL.md` and `docs/developer/developer-guide.md`. Where the table comes
  from and how to edit it.
- `tools/test_lattice_repo_catalogue.py`. Tests RC3-T1 to RC3-T16.

## Decisions taken alone, for the maintainer

1. **Block shapes.** `roots`, `docs` and `tools` are lists of tables (`[[roots]]`), and `generated` is one
   table with a `paths` list. Entry keys are `path`, `owns`, `adrs`, `row` and `group` for a root or a
   documentation area, and `name`, `path`, `import-names` and `reaches` for a tool package.
2. **`owns` and `row` are separate.** `owns` is one plain statement for the catalogue, and `row` is the exact
   AGENTS.md text. Both are required, except that `row` is required only on an entry with no group or the
   first entry of a group, and refused on the rest of its group. Members of a group must be next to each
   other.
3. **The table lists the roots, then the documentation areas, in file order.** `.claude/skills/` is a `docs`
   entry, as the brief said. A documentation area without a `row` is not allowed, so every area declared is in
   the table. `docs/` has more directories (`operator`, `security`, `traceability` and others) that are not
   declared, since the table would then need rows for them.
4. **`docs/` is not itself a root entry.** Its two areas are. `.claude/` is not a root.
5. **The roots in the scan** are the first path segment of each `roots` and `docs` entry: `ontology`, `tools`,
   `benchmark`, `platform`, `apps`, `packages`, `contracts`, `deployment`, `workers`, `test`, `spikes`, `docs`
   and `.claude`.
6. **What counts as a bypass.** An AST scan counting `x / "root"` (the string's first segment is a root) and
   `Path("root/...")`, `PurePath` and `PurePosixPath` with such a first argument. A bare string such as
   `ONTOLOGY_ROOT = "ontology"` is not counted. `ontology_version_check.py` and `ontology_catalog.py` hold
   such constants and are not listed.
7. **An unlisted bypass fails.** The brief says the scan reports and fails on a fixed exception. Otherwise the
   list could grow, so a file that builds a path and is not listed also fails. Only a listed file is
   report-only.
8. **The exceptions file's format** is `path | reason`, with `#` comment lines. The reader's own file
   (`tools/lattice_repo_catalogue.py`) is skipped by name.
9. **What "count" means in the debt row.** The number of files listed, written "lists N files". TD-54 gives 12.
   The scan finds exactly one row that names the file, and fails on none or two. The row is required only
   when the exceptions file exists.
10. **Directories the scan and the tool-package check skip.** Hidden directories, `node_modules`,
    `__pycache__`, `build`, `dist` and `*.egg-info`. A test is `test_*.py`, `conftest.py`, or a file under a
    `tests` directory. Packages under `tools/testing/` are scanned.
11. **`reaches` was found by reading the code and tests**, with a script that follows `/` chains and
    `parents[n]`, and then by judgement. It lists what the package's code or tests read or write, not the
    documents it cites. It is not exhaustive. `testing/oxigraph` reaches nothing.
12. **`spc/python` has no `reaches`.** Its `pipeline.sh` writes to `apps/spc_boundary/priv/`, which does not
    exist in the tree. This is a stale path, left as found.
13. **`generated`** holds `.build/`, `docs/_site/` and the reasoning harness jar
    (`platform/reasoning-testkit/target/reasoning-testkit.jar`), which `mork_compilers` reaches. A path is
    generated when it equals or lies under one of these.
14. **Region markers** are HTML comments, with a blank line between each marker and the table. They also
    appear in Copilot's file.
15. **`check` runs the scan only when roots are declared**, so a catalogue of a project with no roots (or the
    small trees of RC1's tests) is unchanged.
16. **TD-54 sits in the Documentation section**, after TD-53, and the next free number was 54.
17. **`bootstrap`** was run once in this worktree, since its `.venv` held no pytest.

## Test cases

In `tools/test_lattice_repo_catalogue.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| RC3-T1 | the real catalogue / loaded / 11 roots, 3 areas, every tool package on disk, generated paths, and no problems | L3 | + |
| RC3-T2 | an unknown key, a missing path, a wrong type, a missing row, a row on a group's follower, a split group, a table where a list belongs, a tool without import names, a reach that is not a list, an unknown key in `generated`, `paths` that is a string / loaded / each refused | L1 | − |
| RC3-T3 | a root, a tool and a reach that do not exist / checked / each named, and accepted once under `generated` | L1 | +/− |
| RC3-T4 | an undeclared `pyproject.toml` / checked / found, and one in `.venv` ignored | L1 | − |
| RC3-T5 | the real catalogue / the table written / equal to the table at 82fc2b25, and inside the markers of `AGENTS.md` | L2 | + |
| RC3-T6 | a copy with the region edited / checked, rebuilt and checked / stale, then current | L4 | +/− |
| RC3-T7 | text with no markers, swapped, or doubled / rendered / refused, and rendering twice changes nothing | L1 | − |
| RC3-T8 | an ungrouped entry, a group and a documentation area / the table written / one row each | L1 | + |
| RC3-T9 | a planted `ROOT / "ontology"` in a temp tree / checked / found, with the remedy named | L1 | − |
| RC3-T10 | eight source lines / counted / the constructions naming a root, and not a bare string or a near name | L1 | +/− |
| RC3-T11 | the bypass listed with a reason / checked / known, no failure | L1 | + |
| RC3-T12 | a listed file now clean / checked / fails until removed from the list | L1 | − |
| RC3-T13 | a debt row with the wrong count, no count, or no row / checked / each fails | L1 | − |
| RC3-T14 | an exception with no reason, or listed twice / checked / each fails | L1 | − |
| RC3-T15 | `test_*.py`, `conftest.py`, `tests/`, the reader, `.venv`, `node_modules` holding bypasses / scanned / none found | L1 | + |
| RC3-T16 | the real tree / scanned / no problems, found equals listed, 12 files, neither the reader nor a test listed | L3 | + |

## One command

Run from the repository root. A pass is every test passing and the four tasks exiting 0.

```bash
mise exec -- python -m pytest tools/test_lattice_repo_catalogue.py tools/test_agent_guidance.py -q
mise run check:catalogue
mise run build:agent-guidance
mise run check:agent-guidance
mise run check:deny-terms
```

## Results

2026-10-19, run while building, from this worktree:

- **`tools/test_lattice_repo_catalogue.py` and `tools/test_agent_guidance.py`:** 113 passed (37 of them RC3).
- **`mise run check:catalogue`:** passes. 19 modules and 8 tool packages agree with the tree, and the scan
  reports 12 known files.
- **`mise run build:agent-guidance`:** wrote the table and Copilot's file. Against commit 82fc2b25, the diff
  of `AGENTS.md` and of Copilot's file is the two markers only.
- **`mise run check:agent-guidance`:** passes, 0 problems, 9 tests.
- **`mise run check:deny-terms`:** 0 findings.
- **`tools/test_repo_files.py`, `tools/test_ontology_catalog.py` and `mise run check:python-root`:** pass.

The full `mise run check` was not run. The adversarial probes were not run.

## Adversarial probes, for the gate

| Mutation | Expected |
|---|---|
| `where_things_are()` stops joining a group into one row | RC3-T5 and RC3-T8 fail |
| `render_agents()` stops requiring both markers once | RC3-T7 fails |
| `bypass_scan()` stops failing on a listed file that no longer occurs | RC3-T12 fails |
| the debt row's count is not compared | RC3-T13 fails |
| `_is_test()` stops skipping `tests/` | RC3-T15 fails |
| `_path_problems()` stops walking `tools/` for undeclared packages | RC3-T4 fails |
| a root renamed in the tree | RC3-T1 and `check:catalogue` fail |

## Deliberate non-coverage

- The scan failing for listed files, and the scan of tests. Both wait for the tools to move to the reader
  (RC4 and after, ADR-A121 addendum of 2026-10-19).
- Downstream extension (RC4).
- Documentation areas other than `docs/architecture/`, `docs/developer/` and `.claude/skills/`, and a check
  that `reaches` is complete.
- The unlisted `tools/ontology_catalog.py` and `tools/ontology_version_check.py` constants `"ontology"`, which
  are strings and not paths.
- Windows path separators in the scan. It reads source text, and the listed paths are written with `/`.

## Decisions answered

2026-10-19, by the maintainer: every decision taken alone ratified and approved, with one change. The tool
packages' `reaches` had to be confirmed, since they came from reading the code by hand.

**The audit, the same day.** `reaches` now means the paths a package's Python code or tests read or write at
run time, named to two segments. Mentions in docstrings and comments, imports and IRIs do not count.
RC3-T17 derives each package's reaches from its code's path literals and `/` chains and compares them with
the catalogue. Two entries were wrong and are corrected:

- `reference/eligibility` reads nothing outside its tree. It cited `ontology/eligibility` and
  `tools/proofs/eligibility` because its generated module is derived from them, but `literate_extract` writes
  that module, and the package never opens either.
- `surface` never reads `ontology/mork`. Its MORK interoperation uses the namespace only.

`mork_compilers`' jar path is shortened to `platform/reasoning-testkit`, as the rule names two segments.
`tools/spc/python/pipeline.sh` writes into `apps/spc_boundary/priv/`, which does not exist. A shell script is
outside the test's reach, and the finding is TD-56.
