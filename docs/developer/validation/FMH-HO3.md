<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-HO3, the ownership vocabulary, persistence 0.3.0

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice HO3
([plan §3.5](../plans/formal-methods-track-h.md#ho3-the-vocabulary-persistence-030)).
**Source:** [ADR-A122](../../architecture/decisions/ADR-A122-aggregate-ownership.md) decisions 1, 3 and 4,
and [sketch §3](../sketches/persistence-aggregate-ownership.md#3-declaration-surface-ho3).
**Decisions needing confirmation:** none. Five small deviations from the sketch, below.

## Invariant

An adopter can declare, in a boundary shape, whether each edge is owned, a reference or vocabulary, name
the data graph a composite family lives in, and declare reference data, and the shapes refuse a malformed
declaration. The compiler does not read any of it yet (HO4 and HO5), so no behaviour changes.

## What changed

- **`ontology/persistence/spec/persistence.ttl`, 0.2.1 to 0.3.0** (breaking at major version zero, ADR-A113).
  Added `dal:ownership`, `dal:OwnershipKind` with `dal:Owned`, `dal:Reference` and `dal:Vocabulary`,
  `dal:ReferenceData`, `dal:ownsReferenceData` and `dal:dataGraph`. Removed `dal:maxTraversalDepth`.
  Reworded `dal:CompositePropertyBoundary` and `dal:boundaryShape`.
- **`shapes/constraints.ttl`, shapes 0.2.0 to 0.3.0** (the `.version` file). Added
  `dal:CompositePropertyBoundaryRequiresDataGraphShape`, `dal:BoundaryOwnershipShape` and
  `dal:ReferenceDataShape`, and `dal:dataGraph` and `dal:ownsReferenceData` on
  `dal:AggregateBoundaryProfileShape`. Removed the `dal:maxTraversalDepth` property.
- **`spec/persistent-foundation.ttl`, 0.1.0 to 0.2.0.** Its only change is the re-pinned import of
  persistence, which takes the imported change's bump level (ADR-A86).
- **Examples and witnesses.** The composite example gains `dal:dataGraph` and `dal:ownership dal:Owned`,
  and loses `dal:maxTraversalDepth`. The three other composite examples gain `dal:dataGraph`, and two gain
  `dal:ownership`. The two composite witnesses that add a node property carry `dal:ownership dal:Owned`.
- **Witnesses for the new shapes.** `shape-CompositePropertyBoundaryRequiresDataGraphShape.ttl`,
  `shape-BoundaryOwnershipShape.ttl`, `shape-ReferenceDataShape.ttl`, and `ok-ReferenceDataShape.ttl` (the
  conforming case the harness needs). The witness inventory is 90 of 90.
- **Harness.** `witness._focus_nodes` now counts `sh:targetSubjectsOf` as well as `sh:targetClass`, since
  `BoundaryOwnershipShape` is targeted that way and could not otherwise be shown to accept anything.
- **Documents.** The README table and its worked example 11.3 use the new terms, and
  `docs/aggregate-boundaries.md` loses its sentence on a depth bound. The full rewrite is HO9.
- **Catalog and register.** `mise run build:ontology-catalog` and `build:ontology-releases` ran, adding the
  three rows to `docs/architecture/ontology-releases.md`.

## Deviations from the sketch, for the maintainer

1. **`dal:coversClass` loses its `rdfs:domain dal:GraphPatternScope`.** The sketch says to widen its comment
   only. A domain would make every `dal:ReferenceData` a `dal:GraphPatternScope` for any RDFS reasoner, and the
   skill `lattice-ontology-authoring` asks for domains sparingly. The comment now says which class carries
   it in each use. No test or tool read the domain.
2. **`dal:ownership` has no `rdfs:range`-only declaration beyond `dal:OwnershipKind`, and no `owl:oneOf`.** The
   sketch's `owl:oneOf` list would close the class under OWL. The shape `BoundaryOwnershipShape` enforces the
   three values, which is where a violation is reported.
3. **The new SPARQL shape declares its `PREFIX` inside the query**, and has no `sh:prefixes`. The skill asks
   for this, and the sketch said to copy the older shape's form.
4. **HO3-T3 builds the sketch's reference configuration inline in the test.** HO4 adds it as a file
   (`composite-project-ownership.ttl`) and can switch the test to it.
5. **`dal:ownsReferenceData` and `dal:dataGraph` carry `rdfs:domain dal:AggregateBoundaryProfile`.** The sketch
   left them domain-free. They apply to nothing else, and the existing properties of that class do the same.

## 🔴 RELEASE TAGS REQUIRED

Tags can be made only on `main`, so they stay a build warning on this branch and we create none. After the
branch merges, this slice's tags are, in the order `mise run build:ontology-releases` prints them:

- r. `persistence-v0.3.0`
- s. `persistence-shapes-v0.3.0`
- t. `persistent-foundation-v0.2.0`

The same warning lists tags other merged work owes (lettered a to z).

## Test cases

In `tools/persistence/tests/test_ownership_vocabulary.py`, with pySHACL against the shapes.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO3-T1 | a property shape with `dal:ownership ex:Other` / validate / `BoundaryOwnershipShape` reports it | L3 | − |
| HO3-T2 | two `dal:ownership` values on one property shape / validate / reported | L3 | − |
| HO3-T3 | the sketch's reference configuration / validate / no `dal:` shape reports | L3 | + |
| HO3-T4 | a `dal:ReferenceData` without `dal:coversClass` / validate / `ReferenceDataShape` reports it | L3 | − |
| HO3-T5 | `ex:Currencies a dal:ReferenceData ; dal:coversClass ex:Currency` / validate / accepted | L3 | + |
| HO3-T6 | `dal:ownsReferenceData "yes"`, then `true` / validate / reported, then accepted | L3 | +/− |
| HO3-T7 | the repository / `check:ontology-versioning` / `no unbumped changes`, and the register lists every version | L0 | + |
| HO3-T8 | a composite profile with and without `dal:dataGraph`, and a named-graph profile / validate / reported only without | L3 | +/− |
| HO3-T9 | the spec / `rdfs:domain` of `dal:ownership` and `dal:coversClass` / none | L1 | + |
| HO3-T10 | the spec, the shapes and every example / text / no `maxTraversalDepth` | L1 | + |

HO3-T7 is the versioning command in the one command below, and not a pytest item. The other nine are items in
the new file.

## One command

Run from the repository root. A pass for the first is `1003 passed, 1 xfailed` (994 before the slice plus 9
items), and the others exit 0.

```bash
mise run check:persistence && mise run check:ontology-catalog && mise run check:ontology-versioning
```

`mise run check:full-sweep` ran 14 checks, all passed (5 minutes).

## Adversarial probes

Run on 2026-10-10, each restored afterwards.

| Mutation | Result |
|---|---|
| `sh:in` removed from `BoundaryOwnershipShape` | T1 fails, and the witness check reports the shape unwitnessed |
| the data graph query made to always report | T8 fails |
| `rdfs:domain` added to `dal:ownership` | T9 fails |

## Deliberate non-coverage

- That the compiler reads `dal:ownership`. HO4 and HO5.
- Refusals for an unclassified edge or an owned reference-data edge. HO6.
- `dal:maxTraversalDepth` is still read by `resolver.py` and `validator.py`, defaulting to 8. HO5 removes it.
