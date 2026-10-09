<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H1.2c, witnesses for every SHACL shape

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H1.2, part c
([plan §3, H1.2](../plans/formal-methods-track-h.md), split by H-D8)
**Builds on:** [FMH-H1.2a](FMH-H1-2.md) and [FMH-H1.2b](FMH-H1-2b.md).
**Decisions:** none new. One finding needs a design decision from the human (TD-25, below).

## Invariant

Every `sh:NodeShape` in `ontology/persistence/shapes/constraints.ttl` has a fixture that makes it
report **and** a fixture whose data it applies to and accepts. A shape that reports on everything
detects nothing, so both are required, as an audit needs a violating and a clean dataset. With
this slice every refusal, warning, shape and audit has a witness, and `known-gaps.txt` is empty.

## What changed

- **13 shape witnesses**, `shape-<Name>.ttl`, one per previously unwitnessed shape. Each violates
  exactly its shape's constraint, and a drift check requires that it fires the shape it is named for.
- **A conforming-side requirement for shapes.** The first draft of this slice counted a shape as
  witnessed once any fixture made it report. A probe showed a new shape with `sh:minCount 5` passed
  that test by tripping over unrelated fixtures. A shape is now witnessed only if it also has a
  fixture with focus nodes where it reports nothing. This exposed that no shipped example uses a
  valid `dal:ShapeScope`, so `ok-ShapeScopeShape.ttl` was added. A file called `ok-X.ttl` is a
  fixture that shape `X` accepts.
- **Two known defects asserted as strict expected failures** in `tests/test_known_defects.py`, for
  TD-23 and TD-25. They are reported as `xfail` while the defect stands. When it is fixed the test
  passes, strict mode fails the suite, and the fixer removes the marker and the register entry.
- `known-gaps.txt` is empty. A new rule must arrive with its witness.
- A colour fix made earlier in the session (`6bd91a8`). `witness --verbose` prints `WITNESSED` lines
  green and `GAP` lines red on a terminal.

## Measured result

| Family | H1.2a | H1.2b | H1.2c |
|---|---|---|---|
| Refusals | 10 of 34 | 36 of 36 | 36 of 36 |
| Warnings | 3 of 11 | 11 of 11 | 11 of 11 |
| Shapes | 10 of 33 | 20 of 33 | **33 of 33** |
| Audits | 5 of 5 | 5 of 5 | 5 of 5 |
| Total | 28 of 83 | 72 of 85 | **85 of 85** |

The witness directory holds 48 files (25 refusals, 8 warnings, 13 shapes, 1 conforming fixture and
1 shared base) and the check compiles and validates 79 fixtures in all.

## Test cases

All in `tools/persistence/tests/`. The H1.2c additions continue the numbering in
`test_witness_coverage.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| H1.2-T24 | a report with one witnessed rule and one gap / verbose lines with colour on / the first is green, the second red, the summary uncoloured | L1 | + |
| H1.2-T25 | the same report with colour off / lines / no escape codes | L1 | + |
| H1.2-T26 | terminals, pipes, `TERM=dumb`, `NO_COLOR`, `FORCE_COLOR` / `use_color` / the conventional outcome for each | L1 | +/− |
| H1.2-T27 | `FORCE_COLOR` set, then unset / the CLI / coloured, then plain | L3 | +/− |
| H1.2-T28 | the real corpus / read the gap list / empty, and every rule covered | L4 | + |
| H1.2-T29 | a `shape-Alpha.ttl` that fires `Beta` / drift check / one problem naming both | L1 | − |
| H1.2-T30 | a shape with `sh:minCount 5` over the baseline example / observe / it fires, and has no conforming fixture | L1 | − |
| H1.2-T31 | `ok-ShapeScopeShape.ttl` / observe / it is a conforming fixture for that shape | L4 | + |
| TD-23 | a class covered only by `dal:coversClass` / compile / both classes compiled (strict xfail) | L4 | expected failure |
| TD-25 | a multi-valued `dal:priority` declared in either order / compile / the same resolution (strict xfail) | L2 | expected failure |

## One command

Run from the repository root. A pass is `857 passed, 2 xfailed` with no failures. The run takes
about 45 seconds.

```bash
mise run check:persistence
```

`mise exec -- python -m persistence witness --verbose` shows `85 of 85 rule(s) witnessed, 0 listed
gap(s), 0 unlisted gap(s)`, and exits 0.

## Adversarial probes

Run by the agent on 2026-10-09, each reverted afterwards.

| Mutation | Result |
|---|---|
| `NamespaceScopeShape` made to target a class nothing has (the review's D.3 A6 class, a shape that cannot fire) | `UNWITNESSED shape:NamespaceScopeShape`, and its witness "triggers nothing". Exit 1 |
| `ClassScopeShape` stops requiring `dal:targetClass` | `UNWITNESSED shape:ClassScopeShape`. Exit 1 |
| `ProfileScopeShape` stops bounding `dal:priority` | `UNWITNESSED shape:ProfileScopeShape`, and the drift check names what its witness triggers instead. Exit 1 |
| a new shape that reports on everything (`sh:minCount 5`) | `UNWITNESSED shape:BrandNewShape`, "reports a result on every fixture it applies to". Exit 1 |

## Findings

**TD-25, needs your decision.** A scope that declares two `dal:priority` values is resolved by
triple order. With priorities 1 and 3 on one scope and 2 on a competitor, the resolved
`dal:concurrencyProfile` is `Optimistic` or `ProvidedConcurrency` according to the order the two
triples were written. That breaks law L1 (resolution is a function of the configuration, not of
triple order). `dal:ProfileScopeShape` rejects the input, but `compile` never runs the shapes and
accepts it. The same `graph.value` reading pattern is used for every functional property (TD-15 is
one instance). Options for the fix, none taken:

| Option | Consequence |
|---|---|
| the resolver refuses a multi-valued functional property | closes the hole where it is read, needs an audit of every `graph.value` call, changes compiler behaviour |
| `compile` runs the structural shapes first | one mechanism for all structural rules, adds pyshacl to the compile path (a dependency change), and the shapes then become the specification |
| a hygiene check (the H1.1 pattern) | no compiler change, but a user must run it, and `compile` stays unsafe on its own |

**Where the compiler and the shapes disagree**, seen for the first time because the harness
observes both on every fixture. This is data for H4 (review §7.3, V2), not a pass or fail.

- The compiler refuses 15 fixtures for which no violation-severity shape fires. For example
  `NoBoundaryConcurrencyConflict`, `CommitGrainOpSeqConflict`, `UniquenessOutsideBoundary`,
  `UnacknowledgedShardMigration`, `BoundaryConflict`, `ProfileAmbiguityError` and the recipe
  refusals such as `NormalizePipelineRequired`. Some are inherently compiler-side (a cycle, a
  capability check). Others read as rules a shape could state.
- Four shape violations compile without complaint: a `ConcurrencyProfile` with no strategy, an
  `AggregateBoundaryProfile` with no strategy, a `PrivacyProfile` with no class or strategy, and a
  scope with two priorities. The first three silently fall back to the baseline, which is the
  review's "a constraint that silently targeted nothing" in another form. The fourth is TD-25.
- `WeakEtagCasWarningShape` fires only when `dal:etagForm dal:WeakEtag` and
  `dal:concurrencyProfile dal:Optimistic` are on **one** node. The compiler's `WeakEtagCas`
  warning fires across nodes. The shape therefore under-reports against the compiler.

## Artefacts to inspect

- `tools/persistence/tests/witnesses/shape-*.ttl`, 13 small files, each a single violation.
  `shape-WeakEtagCasWarningShape.ttl` and `ok-ShapeScopeShape.ttl` are the two with a story.
- `tools/persistence/src/persistence/witness.py`: `observe_shapes` and `_focus_nodes`.
- `tools/persistence/tests/test_known_defects.py`, and TD-23, TD-24 and TD-25 in
  `docs/developer/plans/technical-debt.md`.
- `python -m persistence witness --verbose`.

## Deliberate non-coverage

- That a shape's message is right, or that it rejects every bad input it should. A witness shows a
  shape can fire and can accept, not that it is complete.
- Whether each refusal has a mirror shape that agrees with it. Observed above, checked
  exhaustively by H4.
- `sh:sparql` constraints with several branches. A fixture reaches one branch, and which one is not
  recorded. Mutation testing (review §16.2) would show the others.
- Shapes outside `ontology/persistence/shapes/constraints.ttl` (for example `persistent-foundation.ttl`).
