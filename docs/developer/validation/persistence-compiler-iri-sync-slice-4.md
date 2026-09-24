<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack — `persistence-compiler-iri-sync` Slice 4

**Slice:** Privacy/erasure profile + cross-profile compatibility (G3 partial, G4)
**Plan:** [persistence-compiler-iri-sync.md](../plans/persistence-compiler-iri-sync.md#slice-4--privacyerasure-profile-and-cross-profile-compatibility-g3-partial-g4)
**Status:** [persistence-compiler-iri-sync.md](../status/persistence-compiler-iri-sync.md)
**Mode:** autonomous (granted 2026-09-23)

## Not yet run in this environment

This sandbox has no system Python, no `mise` on `PATH`, and no PyPI (`files.pythonhosted.org`) access: every package download is 307-redirected to a block-notice page, confirmed with `uv pip install -v` showing the exact redirect target and `CATEGORY_DENIED` reason. This is a deliberate network policy, not a transient fault, and the code in this Validation Pack was not executed against it — only checked for syntax and import errors via the editor's static diagnostics (`get_errors`), which found none, across every new and modified file. Every "Pass criterion" below names the test that must be run to actually confirm the row; none of them have been confirmed yet. See the status record's Blockers section.

## What invariants does this slice protect?

1. **`dal:epochAuthority` resolves like every other extension property** (Slice 2's own rule): a value declared on a node other than the one that wins `dal:epochGuardScope` is still resolved, not silently dropped. This is a correctness fix to Slice 1's original design, not new functionality.
2. **`dal:PrivacyProfile`'s three properties, and `dal:ReceiptProfile`'s `dal:perSubjectScoped`, each resolve independently**, matching the extension-property model rather than identity's whole-node-wins model, because this is a new profile class in the same shape as `dal:EpochProfile`, not a resource-role situation.
3. **`dal:PersonalData` always has a lawful erasure path.** `dal:NoErasure` combined with `dal:PersonalData` is refused outright, mirroring `dal:PersonalDataRequiresErasureShape`'s default (unmarked) `sh:Violation` severity.
4. **A replay-capable receipt model never defeats per-subject erasure silently.** `dal:PatchLog`/`dal:SnapshotPerRevision` combined with `dal:PersonalData` requires `dal:perSubjectScoped true` or `dal:erasureStrategy dal:CryptoShred`, mirroring `dal:PersonalDataReceiptCompatibilityShape`, and the check runs on resolved values so it also catches the two profile classes declared on separate individuals that only share a `dal:appliesTo` scope.
5. **No privacy dimension defaults silently.** An undeclared `dal:PrivacyProfile` means "this scope makes no privacy declaration", not `dal:PublicData` by default, so nothing is checked unless a profile actually exists.

## Test case table

| ID | Given / When / Then | Level | Invariant | Pass criterion | +/- |
|---|---|---|---|---|---|
| T1 | `dal:epochAuthority` resolves from its own `dal:EpochProfile` node, independently of `dal:epochGuardScope` | L1 | 1 | `test_slice_4_privacy.py::test_epoch_authority_resolves_from_its_own_epoch_profile_node`, `::test_epoch_authority_and_epoch_guard_scope_resolve_independently` | + |
| T2 | `dal:epochAuthority` has no default when undeclared | L1 | 1, 5 | `::test_epoch_authority_is_absent_with_no_default_when_undeclared` | + |
| T3 | The two rewritten `test_resolver.py` epoch tests assert the promoted dimension, not the old extra | L1 | 1 | `test_resolver.py::TestEpochGuardScope::test_explicit_dataset_level_guard_resolves_with_authority_extra`, `::test_explicit_row_level_guard_only_resolves` | + |
| T4 | Each of `privacyClass`, `erasureStrategy`, `erasurePrecedence` resolves on its own `dal:PrivacyProfile` node | L1 | 2 | `test_slice_4_privacy.py::test_privacy_property_resolves_on_its_own_node` (3 cases) | + |
| T5 | `perSubjectScoped` resolves from a `dal:ReceiptProfile` node | L1 | 2 | `::test_per_subject_scoped_resolves_from_receipt_profile_node` | + |
| T6 | A privacy property declared on a lower-priority node than the node winning an unrelated dimension is still resolved | L1 | 2 | `::test_privacy_property_on_a_lower_priority_node_is_still_resolved` | + |
| T7 | None of the five Slice 4 dimensions has a baseline default | L1 | 5 | `::test_no_default_for_any_slice_4_privacy_dimension` | + |
| T8 | `dal:PersonalData` + `dal:NoErasure` is refused; `dal:PerSubjectGraphDrop`/`dal:CryptoShred` pass | L1 | 3 | `::test_personal_data_with_no_erasure_is_refused`, `::test_personal_data_with_a_lawful_erasure_strategy_passes` (2 cases) | +/- |
| T9 | `dal:NoErasure` is not checked without `dal:PersonalData` | L1 | 3, 5 | `::test_no_erasure_is_not_checked_without_personal_data` | + |
| T10 | `dal:PersonalData` + `dal:PatchLog`/`dal:SnapshotPerRevision` with neither scoping nor shred is refused | L1 | 4 | `::test_personal_data_with_replay_receipts_and_no_scoping_or_shred_is_refused` (2 cases) | - |
| T11 | The same combination with `dal:perSubjectScoped true`, or with `dal:CryptoShred`, passes | L1 | 4 | `::test_personal_data_with_replay_receipts_and_per_subject_scoping_passes`, `::test_personal_data_with_replay_receipts_and_crypto_shred_passes` | + |
| T12 | `dal:ReceiptOnly` is never checked by the receipt-compatibility rule | L1 | 4, 5 | `::test_personal_data_with_receipt_only_model_is_never_checked` | + |
| T13 | The privacy and receipt profiles declared on two separate individuals sharing one scope are still joined | L1 | 4 | `::test_privacy_and_receipts_declared_on_separate_nodes_are_still_joined` | - |
| T14 | The two new negative fixtures fail compilation for their named `CrossAxisViolation.kind` | L1 | 3, 4 | `::test_negative_fixtures_fail_for_the_right_reason` (2 cases) | - |
| T15 | The positive fixture compiles with neither privacy diagnostic present | L1 | 3, 4 | `::test_positive_fixture_compiles_cleanly` | + |
| T16 | `perSubjectScoped` is emitted with `dal:resolvedLiteral`, never `dal:resolvedValue` | L1 | 2 | `::test_per_subject_scoped_is_emitted_with_resolved_literal` | + |
| T17 | Worked example 4's privacy profile resolves and is emitted with no diagnostics | L1 | 2, 3, 4 | `::test_worked_example_4_privacy_profile_resolves_and_is_emitted` | + |
| T18 | The three new fixtures compile/parse/instantiate (positive) or fail compilation (negative), and conform/fail SHACL as expected | L4 | 3, 4 | `test_compiler_integration.py`'s `POSITIVE_FIXTURES`, `NEGATIVE_FIXTURES`, `SHACL_NEGATIVE_FIXTURES`, `test_every_fixture_parses_as_turtle` | +/- |

## One command to run everything

```bash
mise run check:persistence
```

## Expected artifacts

Not yet produced. Expected: all of Slice 3's 570 tests still pass, plus 24 new dedicated cases in `test_slice_4_privacy.py` (counting parametrisation) and the additional parametrised cases the three new fixtures add to `test_compiler_integration.py`'s existing suites. The exact total is arithmetic, not a confirmed count — see the status record's test tracker.

## Adversarial probes (designed, not yet run — see "Not yet run" above)

These are the exact, minimal, one-line mutations that should make the named test fail. Whoever runs the suite for the first time should apply one, confirm the named test (and only that test, or that test plus its direct dependents) fails, then revert it, per the human validation gate's mutation-check step.

| Probe | Mutation | Expected failure |
|---|---|---|
| Disable the `NoErasure` refusal | In `validator._check_slice_4`, change `if erasure_strategy == "NoErasure":` to `if False:` | `test_personal_data_with_no_erasure_is_refused` and `test_negative_fixtures_fail_for_the_right_reason[invalid-personaldata-no-erasure.ttl-...]` fail; `TestShaclSelfValidation::test_does_not_conform[invalid-personaldata-no-erasure.ttl]` still fails independently (SHACL is unaffected by a Python bug), confirming the Python check is the one actually broken |
| Disable the receipt-conflict refusal | In the same function, change `if not per_subject_scoped and erasure_strategy != "CryptoShred":` to `if False:` | `test_personal_data_with_replay_receipts_and_no_scoping_or_shred_is_refused` (both parametrised cases), `test_privacy_and_receipts_declared_on_separate_nodes_are_still_joined`, and the matching `test_negative_fixtures_fail_for_the_right_reason` case fail |
| Reintroduce `epochAuthority` as an extra instead of its own dimension | In `resolver._DIMENSION_SPEC`, move `DAL.epochAuthority` back into `epochGuardScope`'s extras tuple and delete the `"epochAuthority"` entry | `test_epoch_authority_resolves_from_its_own_epoch_profile_node` and both rewritten `test_resolver.py` cases raise `KeyError` (missing dimension) |
| Give `perSubjectScoped` a baseline default of `False` | Add `"perSubjectScoped": False` to `model.BASELINE_DEFAULTS` | `test_no_default_for_any_slice_4_privacy_dimension` fails (`candidate_count == 0` still holds, but `value is None` no longer does) |

## Deliberate non-coverage

- **`dal:erasurePrecedence` has no dedicated cross-axis check.** It resolves and is emitted, matching `dal:namingAuthority`'s treatment in Slice 3: a declared, adopter-facing choice a runtime component reads, not something this compiler validates. The plan named only the two SHACL-mirrored checks; it did not ask for a new rule joining `erasurePrecedence` with identity's claimed-surrogate strategy, and none was added.
- **`dal:epochCoordinatorBinding`, `dal:erasureRegisterBinding`, `dal:erasureReplayOnRestore`** resolve as extras of `dal:epochAuthority` and are emitted, but carry no check. They describe the restore runbook (guide §24.4) and housekeeping (ADR-A80), which this compiler does not generate or execute.
- **No SPARQL is generated from any Slice 4 dimension**, matching Slice 3's identity precedent: this is adopter-facing configuration a runtime component reads from the compiled profile, not a template input.
- **This test run itself.** Per the "Not yet run" section above, the human must run `mise run check:persistence` and report the result before this slice is complete, and should perform at least one of the adversarial probes above interactively, per the human validation gate.
