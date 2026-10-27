<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Ledger LG-0, examples first

**Unit:** `ledger` ([plan](../plans/ledger.md)). Its status record is created with LG-0.
**Machine:** as the maintainer assigns. **Branch:** `ledger/lg-0-examples`. Commits are the maintainer's.
**Plan and test cases:** [Ledger plan](../plans/ledger.md) (LG-0 in detail)
**Decisions:** ADR-A131 (decisions 3 to 6), LG-Q1 to LG-Q8

## Invariant

The Ledger model accepts licensing, lending, grants, delegated authority and insurance arrangements of amounts consumed and restored, and refuses a cyclic tree, a unit mismatch, an unrounded proportional rule and an overdraw under the refuse rule, as examples written before any term enters a spec (ADR-A-C2, ADR-A131).

## Test cases

The table in the plan section above. Each row's result is recorded under Results at verification.

## One command

Run from the repository root.

```bash
mise run check
```

## Artefacts to inspect

`ontology/ledger/examples/`: ten files, each with its hand-computed table.

## Deliberate non-coverage

The spec and shapes (LG-1, LG-2). Computing the records (B4a, CCS C12).

## Handoff

Written by the building machine when the work is ready for the maintainer to commit.

Built on the current branch (`docs/placement-vehicles-structure`), by the maintainer's instruction
for this session, rather than on a dedicated `ledger/lg-0-examples` branch as the plan names. Ten
files written under `ontology/ledger/examples/`, one per row of the plan's table.

**LG0-01 (parse with rdflib): authored, not yet run.** `mise run bootstrap` fails in this
environment with an HTTP 403 from the configured package mirror while installing build dependencies
(`setuptools>=68`), so `rdflib` is not available to this checkout's `.venv`. Per `lattice-toolchain`,
this is handed to the maintainer rather than retried or routed around. Command to run once the
environment is repaired:

```bash
mise exec -- python -c "import rdflib, glob
for f in sorted(glob.glob('ontology/ledger/examples/*.ttl')):
    rdflib.Graph().parse(f, format='turtle')
    print(f, 'OK')"
```

**LG0-02 (hand tables agree with records): checked by hand**, file by file, when each was written.
Not machine-verified (no compiler exists before LG-1/LG-2).

**LG0-03 (ADR-A-C2 ordering): passes.** The plan's own table order is licensing, lending, grants,
delegated authority, then insurance last, so four non-insurance examples precede the one insurance
example.

**LG0-04 (no `ins:`, `bhv:`, `elg:`, `pty:`, `wrd:` term): passes.**
`grep -rE "\b(ins|bhv|elg|pty|wrd):" ontology/ledger/examples/` returns nothing.

**LG0-05 (refusals name their shape or rule): passes.** Each of the five refusal files' leading
comment names the shape or merge rule that refuses it (the no-cycle shape, the equal-unit shape, the
`ldg:Refuse` rule, the proportional-rounding shape, the extensive-additivity shape).

**LG0-06 (no semicolons, no client names): passes.**
`grep -rE "^#.*;" ontology/ledger/examples/` returns nothing, and every party, institution and
amount is invented.

**A gap found, not this slice's to close:** `ldg:AccountDefinition` and `ldg:Grant` are declared
`⊑ fnd:Identified` in the plan's vocabulary table (as are terms in the Ensemble plan and the
instrument-relations sketch), but `fnd:Identified` does not yet exist in `ontology/foundation`. The
examples use it as a forward reference, as LG-0 is examples only. Whoever builds LG-1 (or Foundation
first) needs to add it.

**Resolved 2026-10-23:** the maintainer dropped `fnd:Identified` everywhere. These terms are plain classes, parts of their owners, and the examples' proposals carry no type.

**A modelling choice for the maintainer:** `insurance-aggregate.ttl`'s reinstatement (position 4)
restores the aggregate alone and does not credit the reinstatement pool, on the reading that the
pool's balance measures total capacity ever available across the original cover and the
reinstatement, which a reinstatement does not raise. Worth confirming before LG-1 writes the shapes.

## Results

**Status: built, hand-checked, machine parse-check blocked on environment (see Handoff).** Not yet
committed, not yet reviewed by the maintainer.
