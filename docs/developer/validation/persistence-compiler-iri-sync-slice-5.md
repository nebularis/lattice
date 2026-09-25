<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack — `persistence-compiler-iri-sync` Slice 5

**Slice:** Uniqueness `onViolation` reconciler operations, `mergeRelation`, `dal:ClaimScheme` `dal:Dual` rotation, registry-token digest-scheme relaxation (G7)
**Plan:** [persistence-compiler-iri-sync.md](../plans/persistence-compiler-iri-sync.md#slice-5--uniqueness-onviolation-branching-mergerelation-claimscheme-rotation-g7)
**Status:** [persistence-compiler-iri-sync.md](../status/persistence-compiler-iri-sync.md)
**Mode:** fully autonomous (granted 2026-09-25)
**Decisions:** taken by the human 2026-09-25, recorded in the status record's "Slice 5 decisions" section — Option A for `dal:onViolation` semantics, the registry-token digest relaxation, and autonomous mode with no install/test-run this tranche.

## Validated (2026-09-25)

The human ran the suite and confirmed **774 passed**, after one fix found by the run itself (see "Found on the way" below). This slice is **complete**.

## What invariants does this slice protect?

1. **The guarded write never branches on `dal:onViolation`.** `key-claim-write`/`key-claim-write-dual` guard and insert identically regardless of policy; only the reconciler operation generated alongside them differs (Decision 1, Option A — guide §7.5, not §6).
2. **Every uniqueness constraint gets exactly one reconciler operation**, selected by `dal:onViolation`, defaulting to `dal:Reject` when undeclared (the same explicit-baseline-default convention as every other dimension in this compiler).
3. **`dal:onViolation dal:Merge` always has a relation to write.** Mirrors `dal:MergeRelationRequiredShape`: a merge policy naming no relation is refused, never silently generated with an undefined term.
4. **A claim-secret rotation in `dal:Dual` state guards both scheme versions in one operation.** `dualClaimScheme` mirrors `persistence.recipes`' own active-scheme filter (`Accepting`/`Dual`) rather than introducing a second, potentially divergent rule.
5. **A digest scheme is required exactly where one is used.** `dal:PositionDerivedEvent` + `dal:RegistryTokenDerivation` is the sole exemption from `dal:DigestSchemeRequiredShape`, narrowly scoped: `dal:HashedTargetDerivation` still requires one, and a scheme declared anyway under the exemption is still checked for well-formedness, never merely ignored.

## Test case table

| ID | Given / When / Then | Level | Invariant | Pass criterion | +/- |
|---|---|---|---|---|---|
| T1 | `dal:onViolation`/`dal:mergeRelation` are read by `resolve_uniqueness()` | L1 | 1, 2, 3 | `test_slice_5_uniqueness.py::test_on_violation_and_merge_relation_are_read`, `::test_merge_relation_is_none_when_undeclared`, `::test_on_violation_is_none_when_undeclared` | + |
| T2 | `dualClaimScheme` is true only when exactly two `dal:claimScheme`s are `Accepting`/`Dual` | L1 | 4 | `::test_dual_claim_scheme_mirrors_recipes_active_scheme_count` (4 cases), `::test_no_claim_scheme_is_not_dual` | +/- |
| T3 | `dal:onViolation dal:Merge` without `dal:mergeRelation` is refused; with it, passes | L1 | 3 | `::test_merge_without_relation_is_refused`, `::test_merge_with_relation_passes` | +/- |
| T4 | `dal:Reject` and undeclared `dal:onViolation` need no `dal:mergeRelation` | L1 | 2, 3 | `::test_reject_needs_no_merge_relation`, `::test_undeclared_on_violation_needs_no_merge_relation` | + |
| T5 | A `dal:PositionDerivedEvent` + `dal:RegistryTokenDerivation` profile needs no `dal:digestScheme` | L1 | 5 | `::test_registry_token_position_event_needs_no_digest_scheme` | + |
| T6 | The same profile with `dal:HashedTargetDerivation` still requires one | L1 | 5 | `::test_hashed_target_position_event_still_needs_a_digest_scheme` | - |
| T7 | A `dal:RegistryTokenDerivation` profile that declares a digest scheme anyway is still checked for well-formedness | L1 | 5 | `::test_registry_token_position_event_with_a_declared_digest_is_still_checked_for_well_formedness`, `::test_registry_token_position_event_with_a_well_formed_declared_digest_passes` | +/- |
| T8 | Explicit `dal:Reject` and entirely undeclared `dal:onViolation` both generate `key-claim-duplicate-audit`, end to end | L1/L4 | 1, 2 | `::test_explicit_reject_generates_the_duplicate_audit`, `::test_undeclared_on_violation_also_defaults_to_the_duplicate_audit` | + |
| T9 | `dal:Merge` generates `key-claim-merge-rewrite` with `mergeRelation` bound as an `Iri`, end to end | L4 | 1, 3 | `::test_merge_policy_generates_the_merge_rewrite_operation_with_the_relation_bound` | + |
| T10 | `dal:Quarantine` generates `key-claim-quarantine`, end to end | L4 | 1 | `::test_quarantine_policy_generates_the_quarantine_operation` | + |
| T11 | Two active claim schemes select `key-claim-write-dual`; one selects the plain write, end to end | L4 | 4 | `::test_dual_claim_scheme_selects_the_dual_write_template`, `::test_single_claim_scheme_selects_the_plain_write_template` | +/- |
| T12 | The merge-rewrite template uses `MIN(?owner)` for the canonical choice and guards idempotently | L1 | 3 | `::test_merge_rewrite_uses_min_owner_as_canonical_and_guards_idempotently` | + |
| T13 | The quarantine template writes only to the quarantine graph and deletes nothing | L1 | 1 | `::test_quarantine_writes_to_the_quarantine_graph_and_deletes_nothing` | + |
| T14 | The dual-write template guards both claim IRIs independently | L1 | 4 | `::test_dual_write_guards_both_claim_iris_independently` | + |
| T15 | Every new template parses with a complete context, and the four new key-claim templates all read from `keysGraph`, never `txnGraph` | L1 | 1, 3, 4 | `test_template_alignment.py::test_every_template_parses_with_a_complete_context`, `::test_key_claims_live_in_the_keys_graph` (extended list) | + |
| T16 | The four new example fixtures compile/parse/instantiate (positive) or fail compilation (negative), and conform/fail SHACL as expected | L4 | 1–5 | `test_compiler_integration.py`'s `POSITIVE_FIXTURES`, `NEGATIVE_FIXTURES`, `SHACL_NEGATIVE_FIXTURES`, `test_every_fixture_parses_as_turtle` | +/- |

## One command to run everything

```bash
mise run check:persistence
```

## Expected artifacts

Confirmed: **774 passed** (2026-09-25 run). All previously-passing tests still pass, plus the new cases in `test_slice_5_uniqueness.py` and the extended parametrisations in `test_template_alignment.py` and `test_compiler_integration.py`.

## Found on the way

`key-claim-merge-rewrite.mustache`'s `{{! ... }}` header comment originally repeated the literal tag text `{{{mergeRelation}}}` inline, as prose, inside the comment. Mustache comments do not suppress tag parsing of their own content in this compiler's rendering path (`chevron`), so the literal braces inside the comment were treated as a second, spurious tag occurrence and failed to render/parse correctly. Fixed by rephrasing the comment to describe the slot in words ("the merge relation is the adopter-named relation…") rather than quoting its Mustache syntax. This is the same class of gotcha already recorded for this compiler in `docs/developer/INDEX.md`'s Key Findings ("Mustache parsing gotcha: Comments cannot contain bare `}}` without breaking parsing") — confirmed here to extend to a full `{{{name}}}` tag quoted inside a comment, not only a bare `}}`.

## Artefacts to inspect

- `tools/persistence/src/persistence/resolver.py`: `_MINTING_ACTIVE_STATES`, `resolve_uniqueness()`'s `mergeRelation`/`dualClaimScheme` fields.
- `tools/persistence/src/persistence/validator.py`: `_check_slice_5`, and `check_identity`'s `digest_unused` exemption.
- `tools/persistence/src/persistence/operations.py`: the rewritten uniqueness loop, `keyQuarantineGraph`.
- The four new templates under `tools/persistence/src/persistence/templates/`.
- `ontology/persistence/shapes/constraints.ttl`'s narrowed `dal:DigestSchemeRequiredShape`, and `spec/persistence.ttl`'s `dal:DigestScheme` comment and version bump (0.2.0 → 0.2.1).
- `ontology/persistence/examples/identity-minting-coverage.ttl`'s `ex:ShipmentEvents`, now without `dal:digestScheme`/`ex:ShipmentDigest`.

## Adversarial probes (designed, ready for a mutation-check pass)

| Probe | Mutation | Expected failure |
|---|---|---|
| Make the guarded write branch on policy after all | In `operations.py`, change the `write_template` selection to also vary by `on_violation` | No test currently pins this negatively (by design, Decision 1 says it must *not* vary by policy); a reviewer should confirm `test_single_claim_scheme_selects_the_plain_write_template` and `test_explicit_reject_generates_the_duplicate_audit` still name `key-claim-write.mustache`, unaffected by policy |
| Disable `MergeRelationRequired` | In `validator._check_slice_5`, change the `if` condition to `if False:` | `test_merge_without_relation_is_refused` and the `test_negative_fixture_fails_compile[invalid-merge-policy-no-relation.ttl]` case fail; `TestShaclSelfValidation::test_does_not_conform[invalid-merge-policy-no-relation.ttl]` still fails independently (SHACL is unaffected), confirming the Python check is the one broken |
| Remove the digest exemption | In `validator.check_identity`, change `digest_unused = (...)` to `digest_unused = False` | `test_registry_token_position_event_needs_no_digest_scheme` fails, and the positive fixture `identity-minting-coverage.ttl` fails compilation (breaking `test_end_to_end_compile_instantiate_parse[identity-minting-coverage.ttl-...]`) |
| Widen the exemption to any position-derived event | Drop the `occurrenceNamespaceDerivation` condition from `digest_unused` | `test_hashed_target_position_event_still_needs_a_digest_scheme` fails |
| Break the dual-scheme count rule | In `resolver.resolve_uniqueness`, change `len(active_schemes) == 2` to `len(active_schemes) >= 1` | `test_dual_claim_scheme_mirrors_recipes_active_scheme_count[dal:Accepting-None-False]` fails, and `test_single_claim_scheme_selects_the_plain_write_template` fails |

## Deliberate non-coverage

- **`key-claim-merge-rewrite` never retires the losing claim or rewrites payload references.** It records the merge relation only, per Decision 1's framing: a background reconciler cannot legitimately act with a claim owner's authority (guide §6.2), and rewriting arbitrary payload references needs domain knowledge this compiler does not have.
- **`urn:g:key-quarantine` is a fixed constant**, matching every other infrastructure graph IRI this compiler already treats as fixed (`tools/persistence/README.md` "Known limitations"). No `dal:` property names it yet.
- **Declared shard counts (`dal:keyShards`) are still not honoured** by any key-claim template, including the four new ones, unchanged from Slice 2's own non-coverage.
