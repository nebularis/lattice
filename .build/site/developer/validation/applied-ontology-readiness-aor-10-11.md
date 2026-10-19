<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-10 and AOR-11, design-time OWL classes and checks

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Decisions:** [ADR-A90](../../architecture/decisions/ADR-A90-eligibility-design-time-owl-class-backend.md)
(addendum option B), [ADR-A83](../../architecture/decisions/ADR-A83-test-only-reasoning-engine-isolation.md), Accepted

## Invariant

A bound condition with a claimed single-valued path compiles to an OWL class
whose design-time answers agree with the reference backend's reading of one
value per subject. A path without the claim is refused, and the claim is
checked on data.

## Test cases

`tools/mork_compilers/src/mork_compilers/test_owl_backend.py`, over
`ontology/eligibility/examples/evidence-binding.ttl`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR10-01 | a profile / compiled / an `exe:OwlArtefact` declared DL, produced by the profile plan and its two condition plans | L1 | + |
| AOR10-02 | the same profile / compiled twice / isomorphic modules | L1 | + |
| AOR10-03 | a binding without `elg:singleValued` / compiled / refused | L1 | - |
| AOR10-04 | an unbound condition / compiled / refused | L1 | - |
| AOR10-05 | the single-valued shape / employees, one with two roles / only that employee reported | L1 | - |
| AOR11-01 | a revision that also admits contractors / subsumption / not subsumed, and the original is subsumed by it | L4 | - and + |
| AOR11-02 | tenure of five or more against two or more / subsumption / subsumed one way only | L4 | + and - |
| AOR11-03 | an exclusion above the only inclusion / satisfiability / unsatisfiable, the original profile satisfiable | L4 | - and + |
| AOR11-04 | two sibling job families / overlap / overlap, none with `disjoint_siblings`, and a parent still overlaps its child | L4 | + and - |

Mutation probes, run on 2026-09-25: removing the per-step `≤1` restriction,
or always omitting sibling disjointness, fails AOR11-04.

## Commands

```bash
mise run bootstrap:reasoning-testkit
mise run check:mork-compilers
mise run check:ontology-versioning
mise run check:ontology-catalog
```

Check that `test_owl_backend.py` reports 9 passed, with none skipped.

## Artefacts to inspect

- `owl_backend.py` and the `check-classes` command in `cli.py`.
- `elg:singleValued` in the Eligibility README, spec and structural shape,
  and on both bindings of `evidence-binding.ttl`.
- `exe:OwlArtefact`, `exe:DesignTimeCheck` and its three kinds in
  `ontology/mork/spec/Executable.ttl`.
- ADR-A90's implementation notes.
