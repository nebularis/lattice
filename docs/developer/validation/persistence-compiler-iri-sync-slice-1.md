<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack — `persistence-compiler-iri-sync` Slice 1

**Slice:** Dataset-level epoch guard (G1)
**Plan:** [persistence-compiler-iri-sync.md](../plans/persistence-compiler-iri-sync.md)
**Status:** [persistence-compiler-iri-sync.md](../status/persistence-compiler-iri-sync.md)

## What invariant does this slice protect?

Before this slice, every CAS-style write the compiler generates (`cas-replace-named-graph`, `tombstone-delete-named-graph`, `cas-replace-composite-property`) guarded epoch at the per-aggregate meta-graph row only — exactly the shape `ontology/persistence`'s `dal:RowLevelGuardOnlyWarningShape` now documents as unsafe: "a stale client can still match an unrestored row after a dataset-level bump that never reaches the row." This slice makes `dal:EpochProfile`'s `dal:epochGuardScope` resolvable, gives `dal:DatasetLevelGuard` a real template variant implementing `rdf-sparql-patterns-guide.md` §19.1's exact SPARQL shape, and — because absence of configuration must never mean the discouraged shape is generated silently — makes the Python-level warning fire on the platform baseline default exactly as it would on an explicit `dal:RowLevelGuardOnly` declaration.

## Test case table

| ID | Given / When / Then | Level | Invariant protected | Pass criterion | +/- |
|---|---|---|---|---|---|
| T1 | Given a target with no `dal:EpochProfile`, when `epochGuardScope` is resolved, then it returns the `RowLevelGuardOnly` baseline with `candidate_count == 0` | L1 | Baseline default is explicit, not accidental | `test_resolver.py::TestEpochGuardScope::test_baseline_default_is_row_level_guard_only` | + |
| T2 | Given a target with `dal:EpochProfile` declaring `dal:DatasetLevelGuard` + `dal:ExternalHighWaterMark`, when resolved, then the value and `epochAuthority` extra both resolve correctly | L1 | Explicit configuration is read correctly | `test_resolver.py::TestEpochGuardScope::test_explicit_dataset_level_guard_resolves_with_authority_extra` | + |
| T3 | Given a target explicitly declaring `dal:RowLevelGuardOnly` + `dal:StoreLocalEpoch`, when resolved, then both values resolve | L1 | Explicit discouraged configuration still resolves (never refused, ADR-A82) | `test_resolver.py::TestEpochGuardScope::test_explicit_row_level_guard_only_resolves` | + |
| T4 | Given the baseline default (no `EpochProfile`), when cross-axis-checked, then a `RowLevelGuardOnly` WARNING diagnostic is present | L1 | The discouraged shape is never generated silently — the core claim of this slice | `test_validator.py::test_epoch_guard_scope_warns_on_baseline_default` | + |
| T5 | Given explicit `dal:RowLevelGuardOnly` + `dal:StoreLocalEpoch`, when cross-axis-checked, then both warnings are present | L1 | Both discouraged values are flagged together, not just one | `test_validator.py::test_epoch_guard_scope_warns_on_explicit_unsafe_configuration` | + |
| T6 | Given explicit `dal:DatasetLevelGuard` + `dal:ExternalHighWaterMark`, when cross-axis-checked, then neither warning fires | L1 | No false positives on the safe configuration | `test_validator.py::test_epoch_guard_scope_does_not_warn_on_dataset_level_guard` | + |
| T7 | Given the same two fixtures, when validated against `ontology/persistence`'s own SHACL shapes, then the unsafe fixture conforms (warnings only) and names both shapes in its report, and the safe fixture's report names neither | L4 | SHACL-level defence in depth for T4–T6's invariant | `test_compiler_integration.py::TestShaclSelfValidation::test_epoch_unsafe_restore_warnings_fire`, `test_epoch_dataset_level_guard_has_no_warnings` | + |
| T8 | Given the `DatasetLevelGuard` fixture, when compiled, then the `cas-replace` operation selects `cas-replace-named-graph-dataset-guard.mustache`, not the plain variant | L1 | Resolved value actually changes which template gets selected | `test_compiler_integration.py::TestEpochGuardScopeTemplateSelection::test_dataset_level_guard_selects_dataset_guard_templates` | + |
| T9 | Given the baseline fixture, when compiled, then the `cas-replace` operation selects the original `cas-replace-named-graph.mustache`, unchanged | L1 | Non-weakening: existing behaviour for unconfigured targets is untouched | `test_compiler_integration.py::TestEpochGuardScopeTemplateSelection::test_baseline_selects_original_named_graph_template` | + |
| T10 | Given the `DatasetLevelGuard` fixture, when compiled then instantiated, then the rendered `cas-replace` SPARQL contains the dataset-level guard clause and parses as valid SPARQL Update | L1/L4 | The added clause is not just present in the template source but survives rendering and is syntactically valid — this compiler's history has real bugs in exactly this category | `test_compiler_integration.py::TestEpochGuardScopeTemplateSelection::test_dataset_level_guard_selects_dataset_guard_templates` (same test, second assertion) | + |
| T11 | Given every positive fixture including the two new ones, when compiled → instantiated → parsed, then every generated operation parses | L4 | New fixtures are exercised by the existing generic end-to-end suite, not just their own dedicated tests | `test_compiler_integration.py::test_end_to_end_compile_instantiate_parse` (parametrised, now includes `epoch-dataset-level-guard.ttl`) | + |

## One command to run everything

```bash
mise run check:persistence
```

## Expected artifacts

- All test cases above pass, alongside the pre-existing suite: **confirmed, 290 passed, 0 failed** (`mise run check:persistence`, 2026-09-23).
- `python3 -c "..."` scratch verification (not part of the committed suite, run during authoring): compiling `baseline-single-class.ttl` yields `epochGuardScope -> RowLevelGuardOnly` with a `RowLevelGuardOnly` warning present and `cas-replace-named-graph.mustache` selected; compiling `epoch-dataset-level-guard.ttl` yields `DatasetLevelGuard` with no warnings and `cas-replace-named-graph-dataset-guard.mustache` selected.

## Fixture bug found by the human's first run, fixed under autonomous mode

The first human-run pass failed T8 (`test_dataset_level_guard_selects_dataset_guard_templates`): `epoch-dataset-level-guard.ttl` declared only a `dal:EpochProfile`, no concurrency/boundary profile, so `concurrencyProfile` resolved to the platform baseline (`ProvidedConcurrency`) rather than `Optimistic`, and `select_operations()` never entered the CAS branch at all — `cas_ops` was empty. Not a defect in the epoch-guard resolution or template logic itself; the fixture was not a complete, self-contained positive example the way every other fixture in `ontology/persistence/examples/` is (each is loaded alone, never layered with another). Fixed by giving the fixture its own full `dal:DataAccessProfile` matching `baseline-single-class.ttl`'s shape. Re-run after the fix: 290/290 passing.

## Deliberate non-coverage

- **`unconditional-write`, `cas-replace-value-guard`, `append-event`** do not gain a dataset-level guard variant in this slice. The first two have no per-aggregate epoch row to guard in the first place; extending them is a judgement call the plan scoped out of Slice 1 — see `tools/persistence/README.md`'s "Known limitations."
- **`dal:epochCoordinatorBinding`, `dal:erasureRegisterBinding`, `dal:erasureReplayOnRestore`** are not read or resolved. Deferred to Slice 4 per the plan.
- **The dataset graph/node IRI (`urn:g:dataset`) is a fixed constant**, not sourced from any `dal:` property, because `EpochProfile` does not declare one. Documented as a known limitation, not silently worked around.

## Adversarial probe (for the human validation gate)

Temporarily change `validator.py`'s new epoch-guard-scope check to only fire when `epoch_guard.candidate_count > 0` (i.e., skip the warning on the baseline-default path) and re-run `test_epoch_guard_scope_warns_on_baseline_default`. Expected: it fails, because the whole point of this slice is that the baseline default is not exempt from the warning. This demonstrates the test is not vacuous — it would catch exactly the regression this slice exists to prevent (the compiler quietly reverting to "unsafe by default, no signal").
