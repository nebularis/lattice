<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: RC2, the tools read the repository catalogue

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice RC2
([plan](../plans/improved-ontology-documentation.md#slices)).
**Implements:** [ADR-A121](../../architecture/decisions/ADR-A121-repository-catalogue.md)'s first two
consequences, for the five tools the plan names.
**Decisions needing confirmation:** two implementation choices, below.

## Invariant

Each fact the five tools held as a constant or took as an argument is now read from the catalogue, and the
tools behave as before. Every extraction yields the same files, the import guard judges the same layers by
the same order, the versioning check reads the same directories, and the freshness check compares the same
Isabelle output.

## What changed

| Tool | Before | Now |
|---|---|---|
| `literate_extract.py` | shape targets from `--shapes` | from the module's catalogue entry (`contract_shapes()`). `--shapes` is removed |
| `import_guard.py` | `SUBSTRATE` and `ALLOWED` written out | `ALLOWED` from the substrate entries, the layer directory from the entry's path, `ROOT` from the catalogue |
| `ontology_version_check.py` | `VERSIONED_DIRECTORIES`, `ARTEFACT_DIRECTORIES` written out | from the catalogue's conventions, `ROOT` from the catalogue |
| `check_formal_freshness.py` | placeholder shape targets, `ontology/<layer>/README.md` | the entry's shape files and README path, `ROOT` from the catalogue |
| the per-layer tests (ten call sites in nine files) | each repeated its layer's shape list | none passes one |

Also:

- RC1-T4 now compares the substrate entries with ADR-A01's order written out in the test, and with the
  import guard, which reads them. Comparing the catalogue with the guard alone would compare it with itself.
- Every command for the extractor written for people or for continuous integration drops `--shapes` and goes
  through `mise exec`:
  - the two workflows that check Surface's extraction
  - `tools/README.md` and `tools/proofs/README.md`
  - the developer guide, whose Eligibility command also gains the `--reference-root` it needs
  - the Field Guide page and the ontology authoring skill
  - eight module READMEs
  - the conventions document's table
- `ontology-versioning-policy.md`'s paragraph about `--shapes` is a dated account of 2026-09-25 and is left as
  it was.

## Implementation choices, for the maintainer

1. **The extractor finds the catalogue from the working directory or `LATTICE_ROOT`, never from `--root`.**
   `--root` keeps meaning where outputs are written or compared, so a test that copies a layer into a
   temporary directory and checks it there still works (Eligibility's hand-edit test does).
2. **The catalogue is read only when a shape block names no file.** A README outside the catalogue with no
   such block still extracts, which keeps OD1's temporary-README tests and any downstream use working
   without an entry.

## Test cases

In `tools/test_lattice_repo_catalogue.py`, after RC1's.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| RC2-T1 | the extractor / called with `--shapes` / refused by its argument parser | L1 | − |
| RC2-T2 | Instrument's README / `contract_shapes()` / its three shape files, in order | L3 | + |
| RC2-T3 | a shape block that names its file, then one that names none for a module outside the catalogue, from a directory with no catalogue / extract / no catalogue needed, then exit 1 naming the catalogue | L1 | +/− |
| RC2-T4 | the versioning check / its two constants / equal the conventions | L3 | + |
| RC2-T5 | the freshness check / Eligibility, then a directory named after no module / no drift, then a message | L3 | +/− |
| RC2-T6 | every document that gives an extractor command, CI included / scanned / none passes `--shapes` | L1 | + |
| RC2-T7 | the extractor run from a directory outside the repository, with no `LATTICE_ROOT` / extract Wording / it finds the catalogue above the README and passes (RC2-C1, added 2026-10-18) | L4 | + |

The existing per-layer extraction tests now run without shape lists, so each also tests that its layer's
entry is right.

## One command

Run from the repository root. A pass is every test passing, with no skip, and the suite otherwise passing
as before:

```bash
mise run check:ontology-catalog
```

Then the four tools' own checks. A pass is each passing as before:

```bash
mise run check:import-guard && mise run check:ontology-versioning && mise run check:formal-freshness && mise run check:catalogue
```

## Adversarial probes, for the gate

| Mutation | Expected |
|---|---|
| swap the first two shape files in Instrument's entry | the four Instrument extraction tests and RC2-T2 fail |
| give Wording `behaviour` among its imports in its entry | `check:import-guard` still passes on the tree, RC1-T4 fails |
| `contract_shapes()` returns `[]` always | the per-layer extraction tests fail on the shape count |

## Deliberate non-coverage

- `PROOFS_ROOT` and `REFERENCE_ROOT` in the freshness check, and other tool-to-tool paths. Tool packages and
  their paths enter the catalogue in RC3.
- Other tests that load a layer's shape files to validate graphs (for example `LAYER / "shapes" /
  "structural.ttl"`). They read files and do not state the extraction contract. The bypass scan of RC3
  lists them.
- The import guard still judges only the substrate. Applied entries can state imports when a later change
  extends the guard to them.

## Results

2026-10-18, after merging `main`: the four tools' checks pass. The import guard finds no violation across 8
substrate layers, the versioning check finds no unbumped change and no missing release row, the freshness
check finds 2 artefacts consistent, and `check:catalogue` finds 19 modules agreeing with the tree.
`check:ontology-catalog` then passed, 974 passed and 7 skipped in 47.49s, with the XML catalog consistent and its
2 known defects reported. Neither RC2's tests nor OD1's carry a skip marker, so the 7 skips are the reasoning
tests that need the reasoning-testkit jar (ADR-A83), which is not built in this worktree. The two implementation
choices await the maintainer's confirmation.

## Implementation choices, answered

2026-10-18, by the maintainer.

- **RC2-C1, option (c).** The extractor reads the catalogue nearest above the README, passed to the reader as
  its explicit root, and falls back to `LATTICE_ROOT` and the working directory only when there is none above
  it. Implemented the same day as `lattice_repo_catalogue.root_above()` and `contract_shapes(..., readme)`,
  with test RC2-T7 (the extractor run from a directory outside the repository). Choice 1 above is superseded.
- **RC2-C2, option (a)**, as implemented. The move to option (b), every extraction reading the catalogue and
  failing when a README's generated files differ from its entry, is planned for after RC4, when every
  extracted README belongs to some catalogue. It is recorded in RC4's row of the plan and in the extractor's
  `contract_shapes()` docstring.

RC2-T7 is authored, not yet run.
