<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack — `persistence-compiler-iri-sync` Slice 2

**Slice:** Ordering, receipt, concurrency and aggregate-boundary extension properties, and meta-topology sharding (G5, G6)
**Plan:** [persistence-compiler-iri-sync.md](../plans/persistence-compiler-iri-sync.md#slice-2--orderingreceiptconcurrencyaggregate-boundary-extension-properties-and-meta-topology-sharding-g5-g6)
**Status:** [persistence-compiler-iri-sync.md](../status/persistence-compiler-iri-sync.md)
**Mode:** autonomous (granted 2026-09-23)

## What invariants does this slice protect?

1. **No declared extension property is dropped silently.** Each of the 13 properties is its own resolved dimension, resolved by the same precedence algorithm as the original dimensions, and recorded in the compiled profile.
2. **Absence has a documented meaning.** Six properties have explicit baseline defaults. The other seven have none, and their absence is checked where it matters.
3. **A `dal:PreCreatedRow` aggregate never gets `create-if-absent`**, and gets the `bootstrap-version-row` operation it depends on.
4. **Two configurations that produce wrong reads are refused**: bucket-any retention under an as-of floor, and a lag-window read without a positive window. The remaining discouraged configurations warn.
5. **Request-time values are standard Mustache**, and the instantiated SPARQL carries no other Mustache syntax.

## Test case table

| ID | Given / When / Then | Level | Invariant | Pass criterion | +/- |
|---|---|---|---|---|---|
| T1 | An extension property on its own `dal:DataAccessProfile` node is resolved, with provenance | L1 | 1 | `test_slice_2_extensions.py::test_property_on_its_own_profile_node_is_resolved` | + |
| T2 | An extension property on a lower-priority node than the one that wins a neighbouring dimension is resolved | L1 | 1 | `::test_property_on_a_lower_priority_node_is_still_resolved` | + |
| T3 | Two declarations at different priorities: the higher wins | L1 | 1 | `::test_higher_priority_node_wins_per_property` | + |
| T4 | Two declarations at equal priority are refused as ambiguous | L1 | 1 | `::test_two_equal_priority_declarations_are_ambiguous` | - |
| T5 | Literal-valued dimensions are emitted with `dal:resolvedLiteral`, object-valued with `dal:resolvedValue` | L1 | 1 | `::test_literal_dimensions_are_emitted_with_resolved_literal`, `::test_resolved_literal_is_rdf_literal` | + |
| T6 | Six baseline defaults, `candidate_count == 0` | L1 | 2 | `::test_baseline_default` (6 cases) | + |
| T7 | Seven properties with no default resolve to nothing | L1 | 2 | `::test_no_default_where_absence_is_meaningful` (7 cases) | + |
| T8 | `WeakEtagCas` fires with the two properties on different nodes, not on the baseline | L1 | 4 | `::test_weak_etag_with_optimistic_warns_even_across_nodes` | +/- |
| T9 | `NoGlobalRead` warning | L1 | 4 | `::test_no_global_read_warns` | +/- |
| T10 | A dataset tier without a global-read strategy warns, not once one is declared | L1 | 2, 4 | `::test_dataset_tier_without_global_read_warns` | +/- |
| T11 | `AdvisoryContiguity` warning | L1 | 4 | `::test_advisory_contiguity_warns` | +/- |
| T12 | `SortedAcquisition` warns with single-request CAS, not with `dal:LockingConcurrency` | L1 | 4 | `::test_sorted_acquisition_with_single_request_cas_warns` | +/- |
| T13 | A shard count above 1 warns `ShardingNotHonoured`, a count of 1 does not | L1 | 1 | `::test_declared_shard_count_warns_not_honoured` (3 cases) | +/- |
| T14 | Bucket-any retention with an as-of floor is refused, including across two nodes; without a floor it is allowed | L1 | 4 | `::test_bucket_any_retention_with_as_of_floor_is_refused` | +/- |
| T15 | Lag-window read without a window, or with 0, is refused; with a window it passes | L1 | 4 | `::test_lag_window_read_requires_positive_window`, `::test_lag_window_read_with_window_passes` | +/- |
| T16 | The negative fixture fails for the missing window, not for an unrelated reason | L1 | 4 | `::test_lag_window_negative_fixture_fails_for_the_right_reason` | - |
| T17 | `dal:AbsentRow` (default) keeps `create-if-absent`; `dal:PreCreatedRow` replaces it with `bootstrap-version-row`, the dataset-guard variant under `dal:DatasetLevelGuard` | L1 | 3 | `::test_absent_row_keeps_create_if_absent`, `::test_pre_created_row_gets_bootstrap_instead_of_create`, `::test_pre_created_row_under_dataset_guard_uses_guarded_bootstrap` | +/- |
| T18 | `dal:registryGraph` is bound on every audit and on nothing else; absent means no binding; an unsafe IRI fails compilation | L1 | 1 | `::test_registry_graph_is_bound_on_every_audit`, `::test_registry_graph_absent_means_no_binding`, `::test_unsafe_registry_graph_iri_fails_compile` | +/- |
| T19 | After instantiate, the only Mustache left in any template is a request-time slot | L1 | 5 | `test_template_alignment.py::test_request_time_slots_are_the_only_mustache_left_after_instantiate` | + |
| T20 | An unrendered request-time slot is a parse error | L1 | 5 | `test_template_alignment.py::test_unrendered_request_time_slot_fails_closed` | - |
| T21 | A request-time slot cannot be bound at compile time | L1 | 5 | `test_template_alignment.py::test_request_time_slot_cannot_be_bound_at_compile_time` | - |
| T22 | Every positive fixture, including `extension-properties.ttl`, compiles, instantiates, has its request-time slots rendered by a Mustache library, and parses | L4 | 1, 5 | `test_compiler_integration.py::test_end_to_end_compile_instantiate_parse` | + |
| T23 | `invalid-lagwindow-missing.ttl` fails compilation and fails SHACL (`dal:LagWindowRequiredShape`); `extension-properties.ttl` conforms | L4 | 4 | `test_compiler_integration.py::test_negative_fixture_fails_compile`, `TestShaclSelfValidation::test_does_not_conform`, `::test_conforms` | +/- |
| T24 | Resolution over all dimensions is invariant under triple order and repeat compilation | L2 | 1 | `test_determinism.py` (iterates `DIMENSIONS`, which now includes the 13) | + |

## One command to run everything

```bash
mise run check:persistence
```

## Expected artifacts

**526 passed, 0 failed** (2026-09-23, run from the repository root by `mise`, and from `tools/persistence` directly). The count before this slice was 471.

## Adversarial probes (run during this slice)

| Probe | Result |
|---|---|
| Force `pre_created_row = False` in `operations.py` | fails T17 (2 tests) |
| Disable the lag-window check in `validator.py` | fails T15, T16 and the negative-fixture test (4 tests) |
| Remove `etagForm` from `DIMENSIONS` and `_DIMENSION_SPEC` (no longer resolved on its own) | fails T1, T6 (`etagForm` case) and T8 (3 tests) |

All three were restored and the full suite re-run green.

## Contract changes (non-weakening rule)

- `#PAYLOAD#` and `#LOG_GRAPHS#` are replaced by the Mustache slots `{{{payloadTriples}}}` and `{{{logGraphs}}}`. Tests that substituted the old markers now render the slots with `chevron` through `tests/request_slots.py`. The earlier test `test_unsubstituted_markers_still_parse` asserted that a forgotten marker left a well-formed query with an empty payload. Under the new contract a forgotten slot must fail closed, so it is replaced by T20, which asserts the opposite and stronger property.
- Fixtures declaring an extension property on its own node use `dal:DataAccessProfile`, because the vocabulary's shapes require a node typed with a specific profile class to carry that class's primary value.
- The five Slice 2 SHACL shapes now also target `dal:DataAccessProfile`, so they see declarations made there. They still check one node at a time. The compiler's checks on resolved values are authoritative.

## Deliberate non-coverage

- Shard counts are recorded and warned about, not applied (plan decision 3).
- `dal:AbsentRow` with `dal:CompositePropertyBoundary` still generates no create operation: no composite create template exists. Recorded in `tools/persistence/README.md`.
- `dal:etagForm`, `dal:etagRepresentation`, `dal:deadlockPolicy`, `dal:globalReadStrategy`, `dal:lagWindowMillis`, `dal:contiguityCheckMode`, `dal:retentionMode` and `dal:asOfFloorSource` change no generated SPARQL. They are recorded for the HTTP layer, the consumer and the retention job, none of which this compiler generates.
- A pre-existing working-directory dependency in `test_determinism.py` (relative fixture paths) was fixed on the way, since it failed the suite when run from `tools/persistence`.
