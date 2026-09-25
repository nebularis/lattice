<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Vocabulary Temporal-Binding Consumer Hardening - Status

**Unit ID:** `temporal-binding-consumer-hardening`
**Status:** Implemented (2026-09-25), at the human's direction ("proceed with
the attached plan"), which is treated as confirmation of Finding 1's Option B
(the plan's own "Human Input" line already recorded this agreement). Not yet
executed in this sandbox — no `rdflib` here (network-restricted); statically
verified (`py_compile`, a direct AST-level mutation probe for Finding 4) and
handed off for `mise run check:vocabulary` / `python -m unittest surface.test_surface -v`.
**Last updated:** 2026-09-25
**Trigger:** Closure cross-reference of `vocabulary-temporal-binding` against
[docs/architecture/rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md)
**Plan:** [temporal-binding-consumer-hardening.md](../plans/temporal-binding-consumer-hardening.md)
**Predecessor:** [vocabulary-temporal-binding](vocabulary-temporal-binding.md) (closed)

## Current position

All four findings are implemented, in slice order (1, 2, then 3, then 4 per
the plan's dependency: 4 needed 3's resolution-instant decision).

### Slice 1 — Finding 3 (documentation)

`ontology/vocabulary/shapes/constraints.ttl`'s header and `vvp:resolvedAt`'s
`rdfs:comment`, `tools/vocabulary/README.md`'s "What this package deliberately
does not check", and the validation pack's VTB-13 row now state explicitly
that `vvp:resolvedAt` is a valid-time "as-of" query point (the same axis as
`fnd:validFrom`/`fnd:validTo` and `resolve()`'s `at` parameter), not a
transaction-time "recorded when" timestamp, and name the guide's
`recordedAt`/`occurredAt` convention as the naming precedent a real consuming
property should follow instead. No shape, resolver, or test change.

### Slice 2 — Finding 4 (test)

New `tools/vocabulary/tests/test_architecture.py`: no module under
`tools/vocabulary/src/vocabulary/` may call `datetime.now()`/`time.time()`/
`datetime.utcnow()`, or import the `time` module at all. Exemption list starts
empty (unlike persistence's HLC carve-out — nothing here needs one).
**Mutation-probed in this session**: a temporary `datetime.now()` call added
to `resolver.py` made the test fail with the exact offending module/call
named; reverting made it pass again. Both runs executed directly against the
package's stdlib-only AST-scanning logic (no `rdflib` needed for this test).

### Slice 3 — Finding 1, Option B

- `tools/surface/src/surface/cli.py` gained
  `contracts_needing_explicit_resolution_time(source, contracts)` and
  `_refuse_implicit_now_for_scoped_contracts(...)`, wired into
  `command_compile`, `command_check`, `command_parity` (the non-shared-corpus
  branch), and `command_mork`: each now refuses to call `_now()`'s wall-clock
  default when any contract in scope has a contract-bound population that
  declares `srf:activeBindingScope`, or whose scheme contract is named by any
  `voc:SchemeBinding` in the source graph at all — printing a `FAIL` line per
  contract and returning a nonzero exit code instead of silently compiling
  against an implied instant.
- **Deliberately left unguarded:** `command_parity --shared-corpus`'s call to
  `run_shared_surface_parity`, a deeper library entry point outside this
  slice's scope; no scoped fixture exists in `test/conformance/manifest.ttl`
  today, so this is a documented gap, not a known-live one.
- `compile.py`'s module docstring and `ontology/surface/README.md`'s `srf:R1`
  law text (propagated to `spec/surface.ttl`/`vocab/surface-vocab.ttl` via
  `tools/literate_extract.py`, confirmed clean beforehand and after) both now
  state the determinism guarantee precisely: it holds unconditionally for an
  unscoped population, and relative to a required, explicit resolution
  instant for a population that could resolve a scoped binding.

### Slice 4 — Finding 2

- New `srf:resolvedAt` (`xsd:dateTime`), `srf:resolvedBindingScope`
  (`voc:BindingScope`, repeatable), `srf:resolvedBinding` (`voc:SchemeBinding`,
  functional, absent under fallback), and `srf:resolvedViaFallback`
  (`xsd:boolean`) on `srf:ReadSetEntry`, added via the README's `turtle-spec`
  block and regenerated cleanly through `tools/literate_extract.py`.
  `srf:ReadSetEntry`'s class restrictions and `srf:ReadSetEntryShape`
  (`structural.ttl`) extended to match.
- New `srf:BoundSchemeSourceResolutionRecordedShape`
  (`shapes/constraints.ttl`): every `BoundSchemeSource`-kind `ReadSetEntry`
  must carry `srf:resolvedAt` — checkable without any caller context, since
  it is a property of the entry's own recorded content, not a live
  re-resolution.
- `enumerate_population` (`compile.py`) now returns
  `(members, scheme, resolution)` instead of discarding the `vocabulary.Resolution`
  object after reading `.scheme`; every call site updated
  (`_scope_members`, `_compile_index`, and `test_surface.py`'s
  `test_population_follows_the_scheme_contract`). `ReadSetRecord` gained the
  four new optional fields; `_compile_index` populates them for every
  `BoundSchemeSource` entry (scoped or unscoped-fallback alike, for uniform
  auditability); `_manifest` emits them.

## New tests added (statically verified, not yet executed)

In `tools/surface/src/surface/test_surface.py`:

- `test_population_follows_the_scheme_contract` — updated for the new
  3-tuple return; asserts the unscoped fixture's resolution used the fallback.
- `test_manifest_records_the_resolution_trace_for_a_bound_scheme_source` —
  the scoped fixture's manifest names the exact scope, binding, instant, and
  non-fallback flag.
- `test_resolution_trace_changes_when_the_context_does` — the Finding 2
  mutation probe the plan's Slice 4 gate calls for: dropping the population's
  `active_binding_scope` via `dataclasses.replace` flips the recorded trace
  from a named binding to a recorded fallback, and the minted symbols change
  to match.
- `ResolutionTimeGuardTests` (new class) — the scoped fixture needs an
  explicit resolution time; the unscoped fixture (no reachable binding at
  all) does not; a contract-bound population with a reachable binding but no
  declared scope still needs one (an unscoped caller can still match a
  scopeless binding); and regeneration of a genuinely unscoped contract is
  bit-identical across two very different `produced_at` values, the plan's
  Slice 3 gate.

All four were checked by hand against the fixture's actual IRIs
(`ex:north-binding`, `ex:region-north` under
`https://example.org/lattice/surface/employment-scoped#`) and by tracing
`enumerate_population`/`resolve()`'s logic manually, since this sandbox
cannot execute them.

## What was verified in this sandbox (no `rdflib` available)

- `py_compile` on every changed Python file: `compile.py`, `cli.py`,
  `test_surface.py`, `tools/vocabulary/tests/test_architecture.py` — all
  compile cleanly.
- `tools/literate_extract.py --check`/write-mode run on
  `ontology/surface/README.md` before and after every edit in this unit:
  clean before, a precise, reviewed diff after, clean check again.
- Finding 4's test executed directly (AST-scanning logic needs no
  third-party dependency) and mutation-probed successfully.
- Everything requiring `rdflib` (Findings 1's and 2's new `test_surface.py`
  cases, the SHACL shape, the CLI guard's actual behaviour end-to-end) is
  authored and statically reviewed, not executed. Hand off:
  `mise run check:vocabulary` and `python -m unittest surface.test_surface -v`
  from the repository root.

## Decisions made during implementation (flagged for review)

- **Finding 1's guard lives in `cli.py`, not inside `enumerate_population`/
  `SurfaceCompiler`.** The library API already requires `produced_at`
  explicitly (no default); only the CLI's `_now()` silently defaults to
  wall-clock time. Guarding at the CLI layer keeps the library's contract
  unchanged for direct callers (tests, other tools), which already supply an
  explicit instant.
- **`resolved_binding_scope` records the caller-supplied context, not the
  winning binding's own scope set** — the two coincide when a binding wins by
  exact match, but recording the *supplied* context is what lets an auditor
  reconstruct a fallback decision too (where there is no winning binding to
  read a scope set from).
- **Resolution trace is recorded uniformly**, for both a scoped population
  and an unscoped one falling back to `boundScheme` — not only when scoping
  is present — since the fallback case is exactly as auditable a decision as
  the scoped case, and a uniform rule is simpler than a conditional one.
- **`command_parity --shared-corpus` left unguarded.** Flagged above as a
  documented, deliberate gap rather than a silent one.

## Human validation gate

Not yet performed. Before closing this unit:

1. Run `mise run check:vocabulary` (Finding 3/4's package) and
   `python -m unittest surface.test_surface -v` (Findings 1/2's new cases)
   and report the result.
2. Confirm Finding 1's Option B is accepted as implemented (the plan's own
   "Human Input" line already recorded this, carried through unchanged).
3. Decide whether `command_parity --shared-corpus` needs the same guard in a
   follow-on unit, or stays a documented non-coverage.

## Blockers

None recorded against this unit's four findings — all are implemented.
Execution of the new/changed tests in an environment with `rdflib` installed
is the only remaining step before full closure.

