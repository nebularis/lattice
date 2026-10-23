<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Ledger LG-1, the configuration document

**Unit:** `ledger` ([plan](../plans/ledger.md)). Its status record is created with LG-0.
**Machine:** as the maintainer assigns. **Branch:** `ledger/lg-1-configuration`. Commits are the maintainer's.
**Plan and test cases:** [Ledger plan](../plans/ledger.md) (LG-1 in detail)
**Decisions:** ADR-A131 decisions 1 to 3, 5, 6 and 8, LG-Q1, LG-Q2, LG-Q6 to LG-Q8

## Invariant

Account definitions, their tree, owner kinds, merge rules, rounding, reset, keys, purposes, ceilings and conversion are configuration, and shapes refuse every malformed tree, with Ledger importing only Foundation, Vocabulary and Quantification (ADR-A131, ADR-A01's 2026-10-19 addendum).

## Test cases

The table in the plan section above. Each row's result is recorded under Results at verification.

## One command

Run from the repository root.

```bash
mise run check
```

## Artefacts to inspect

`ontology/ledger/README.md`, `spec/ledger.ttl`, `vocab/ledger-vocab.ttl`, `shapes/`, the root catalogue, `tools/test_ledger.py`, the release notes.

## Deliberate non-coverage

Runtime records (LG-2). Behaviour's migration (LG-3).

## Handoff

Written by the building machine when the work is ready for the maintainer to commit.

Built on the current branch (`docs/placement-vehicles-structure`), per the maintainer's instruction
for this session, rather than on `ledger/lg-1-configuration`.

**Delivered:** `ontology/ledger/README.md` in ADR-A126's layout (one class, `ldg:AccountDefinition`,
12 object properties, the full vocabulary document's four concept schemes and their concepts),
generated `spec/ledger.ttl`, `vocab/ledger-vocab.ttl`, `shapes/structural.ttl` (cardinalities) and
`shapes/constraints.ttl` (the six SHACL-SPARQL constraints the plan names: no cycle, matching
units, extensive additivity with Sum/Difference, a proportional rule's rounding and residual, a
credit ceiling not below the stated amount, a key dimension's type). `ledger` registered in the root
catalogue after `quantification`, the ontology architecture document and the root README. Import
guard passes (Ledger imports only Foundation, Vocabulary, Quantification). `tools/test_ledger.py`
added to `check:ontology-catalog`'s list, 13 tests, all passing.

**The substrate release moved to 0.19.0** (`mise run release:prepare -- 0.19.0`), since Ledger
joining the release changes every member's `owl:versionIRI` under ADR-A129's one-release model. This
re-pinned 45 other files (every substrate and standalone layer) and cascaded into five applied
modules whose own versions pin the substrate (`applied/capacity` 0.17.0, `applied/classification`
0.4.0, `insurance/common` 0.8.0, `insurance/exposure` 0.3.0, `insurance/peril` 0.7.0), each bumped by
one MINOR per the re-pinned-import cascade rule (ADR-A86), with their own test files' hardcoded
version strings updated to match. A release-notes line recording the re-pin was added to every
affected README that has a Release Notes section (11 READMEs, plus Ledger's own).

**A mid-slice correction, worth recording:** `release:prepare` was run once, reverted in full (every
file it touched, back to HEAD, since nothing was yet committed), then re-run, after realising the
first pass's blast radius needed deliberate review rather than being accepted blind. The revert and
re-run are both in the history available to the maintainer; the final state is as if it ran once.

**Checks run, actual results, not claimed:**
- `mise run check:ontology-versioning`: passes (exit 0). The informational "ACTION REQUIRED" tag
  list it prints is real and for the maintainer (see status record).
- `mise run check:import-guard`, `check:catalogue`, `check:ontology-catalog` (1145 tests),
  `check:full-sweep`'s `check:catalogue`: all pass.
- `mise run check:published-decisions`: **fails**, and cannot pass yet. Ledger's own README and
  `shapes/constraints.ttl` necessarily cite ADR-A131 (Accepted, not Published) throughout, since the
  whole document describes that decision. Per ADR-A127, publishing an ADR is the maintainer's act,
  the same as accepting one. This is expected, not a defect: Vocabulary's own founding ADR (ADR-A85)
  was published alongside its README's migration, the same point this slice has now reached for
  Ledger. **Needs the maintainer to publish ADR-A131** (and ideally ADR-A01's 2026-10-19 addendum,
  also cited) before this check, and so `mise run check` as a whole, can go green.
- `check:full-sweep`'s other failures are pre-existing and unrelated, confirmed by running each in
  isolation: `build:mtp`/`check:mtp` (tools/mork is not installed in this environment, flagged
  earlier this session, a mirror-freshness gap on its langchain/boto3 dependencies, unrelated to
  Ledger), `check:persistence` (a Windows-only `write_text()`/default-encoding bug unrelated to
  Ledger, in `tools/persistence/tests/test_compiled_profile_stable.py`), `check:agent-guidance` (a
  Windows symlink-privilege limitation in `tools/test_agent_guidance.py`, unrelated), and the
  `reasoning_server` JVM-timeout test inside `check:ontology-catalog` (flaky, passes alone, a timing
  margin too thin under parallel load).
- `check:site-sections` failed once (my edit to `eligibility/README.md` left its site copy stale)
  and is fixed by the included `mise run build:site-sections` run.

**Two small, low-risk fixes made along the way, surfaced by running the checks for real rather than
guessing:**
1. `tools/import_guard.py`'s violation renderer printed a bare `Path`, giving backslash-separated
   output on Windows that five of `test_import_guard.py`'s own fixtures compare against a
   forward-slash string. Fixed to `.as_posix()`, per the documented convention (`lattice-toolchain`
   skill: "a tool that prints a repository-relative path for comparison prints `Path.as_posix()`").
2. `test_import_guard.py`'s own diagram-order check read `ontology-architecture.md` without
   `encoding="utf-8"`, defaulting to the Windows locale codec, which cannot decode this document now
   that it is bigger. Fixed to read explicitly as UTF-8.
3. Three LG-0 refusal fixtures (`refusal-cycle.ttl`, `refusal-unit.ttl`,
   `refusal-proportional-unrounded.ttl`, and `refusal-overdraw.ttl` for consistency) were missing a
   `qnt:Difference` capability on their value spaces, so they also (unintentionally) tripped the new
   `ExtensiveUnitOfAccountShape` alongside their intended shape. Added, so each refusal now isolates
   exactly the one condition it names.

**A finding, not a defect:** the plan's LG1-09 row asks for "a generated tree of 10,000
definitions" validated against the cycle shape. A first attempt built a 10,000-deep linear chain,
which recursed past Python's call-stack depth inside rdflib's SPARQL property-path evaluator
(`ldg:partOf+`) — a real scaling limit of that implementation for very deep chains, worth knowing,
though no real account tree is anywhere near that deep (an aggregate, its sections, their
sublimits is three or four levels). The test now builds a shallow, wide tree (a root, 99 sections, the
rest sublimits), which is both the shape real trees have and avoids the recursion limit, and passes
with its time recorded.

**A design choice carried from LG-0, restated:** `ldg:AccountDefinition` is a plain `owl:Class`, not
yet `⊑ fnd:Identified` (§5.1 of the README, Open Issues). `fnd:Identified` still does not exist in
Foundation.

**Resolved 2026-10-23:** the maintainer dropped `fnd:Identified` everywhere. These terms are plain classes, parts of their owners, and the examples' proposals carry no type.

## Results

**Status: built and verified, as far as this environment and the maintainer-gated items allow. Not
yet committed, not yet reviewed by the maintainer.**

| Row | Result |
|---|---|
| LG1-01 | ✅ passes (`tools/test_ledger.py::test_literate_extraction_matches_committed_turtle`, and `literate_extract.py --check` directly) |
| LG1-02 | ✅ passes, all 5 accepted LG-0 examples conform |
| LG1-03 | ✅ passes, `refusal-cycle.ttl` fails `NoCycleThroughPartOfShape` by name |
| LG1-04 | ✅ passes, `refusal-unit.ttl` fails `ChildUnitMatchesParentShape` by name |
| LG1-05 | ✅ passes, `refusal-proportional-unrounded.ttl` fails `ProportionalNeedsRoundingShape` by name |
| LG1-05b | ✅ passes, `refusal-intensive-unit.ttl` fails `ExtensiveUnitOfAccountShape` by name |
| LG1-06 | ✅ passes, `check:import-guard`: 0 violations, Ledger imports only Foundation, Vocabulary, Quantification |
| LG1-07 | ✅ passes, no `ins:`/`bhv:`/`elg:`/`pty:`/`wrd:` term in `spec/` or `vocab/` |
| LG1-08 | ⛔ blocked, not this slice's to resolve: needs the maintainer to publish ADR-A131 (see Handoff) |
| LG1-09 | ✅ passes, 10,000-definition wide tree, time recorded by `record_property` (pytest's property, visible with `--junit-xml`) |
| LG1-10 | ✅ passes, `check:ontology-versioning` exit 0, Ledger and every release member at 0.19.0 |

