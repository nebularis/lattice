<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack — `persistence-compiler-iri-sync` Slice 3

**Slice:** Identity minting profile resolution (G2)
**Plan:** [persistence-compiler-iri-sync.md](../plans/persistence-compiler-iri-sync.md#slice-3--identity-minting-profile-resolution-g2)
**Status:** [persistence-compiler-iri-sync.md](../status/persistence-compiler-iri-sync.md)
**Mode:** autonomous (granted 2026-09-23)

## What invariants does this slice protect?

1. **Identity is chosen per resource role, never once per class.** Each role resolves as its own dimension by the standard precedence rules, so a class-level profile overrides a namespace default for one role without touching the others.
2. **A strategy and its parameters come from the same profile node.** A digest scheme or event setting never attaches to a strategy declared elsewhere.
3. **No identity strategy is assumed.** An undeclared role is absent from the compiled profile (ADR-A82).
4. **The compiler generates no minting SPARQL** (plan decision 2). The operation set is unchanged by an identity profile.
5. **A configuration that cannot mint a correct IRI is refused**, and a position-derived identity under an unsafe epoch is warned.

## Test case table

| ID | Given / When / Then | Level | Invariant | Pass criterion | +/- |
|---|---|---|---|---|---|
| T1 | Each of the eight roles resolves as `identity:<Role>` | L1 | 1 | `test_slice_3_identity.py::test_every_role_resolves_as_its_own_dimension` (8 cases) | + |
| T2 | One class resolves different strategies for two roles | L1 | 1 | `::test_one_class_resolves_different_strategies_per_role` | + |
| T3 | A class profile overrides a namespace default for one role only | L1 | 1 | `::test_class_profile_overrides_namespace_default_per_role_only` | + |
| T4 | Two equal-priority profiles for one role are refused as ambiguous; for two different roles they are not | L1 | 1 | `::test_equal_priority_within_one_role_is_ambiguous`, `::test_equal_priority_across_roles_is_not_ambiguous` | +/- |
| T5 | The winning node's digest scheme is used, never a losing node's | L1 | 2 | `::test_winning_node_carries_its_own_digest_scheme` | + |
| T6 | No profile, no identity dimension | L1 | 3 | `::test_undeclared_role_has_no_default` | + |
| T7 | Identity dimensions appear in the compiled profile with strategy and winner; undeclared roles do not | L1 | 1, 3 | `::test_identity_dimensions_are_emitted_to_the_compiled_profile` | + |
| T8 | An identity profile changes no generated operation | L1 | 4 | `::test_identity_generates_no_operations` | + |
| T9 | Derived-hash and content-addressed identity require a digest scheme | L1 | 5 | `::test_digest_scheme_required` (2 cases) | +/- |
| T10 | Width not a positive multiple of 8, or an unknown encoding (case-sensitive), is refused | L1 | 5 | `::test_digest_scheme_malformed` (4 cases) | - |
| T11 | Position-derived occurrence identity requires a uniqueness witness and a namespace derivation | L1 | 5 | `::test_position_derived_event_requires_witness`, `::test_position_derived_event_requires_namespace_derivation` | - |
| T12 | A complete position-derived profile under a safe epoch raises nothing; under the baseline row-level guard or a store-local epoch it warns | L1 | 5 | `::test_complete_position_derived_event_under_safe_epoch_passes_cleanly`, `::test_position_derived_event_warns_under_unsafe_epoch` (2 cases) | +/- |
| T13 | A claimed surrogate for the entity or aggregate-root role requires a uniqueness constraint; other roles are not checked | L1 | 5 | `::test_claimed_identity_requires_a_key` (2 cases), `::test_claimed_identity_on_other_roles_is_not_checked_for_a_key` | +/- |
| T14 | The two negative fixtures fail for their named reasons | L1 | 5 | `::test_negative_fixtures_fail_for_the_right_reason` (2 cases) | - |
| T15 | `dal:DigestSchemeWellFormedShape` accepts a 128-bit base32 scheme and rejects a 100-bit or `hex` one | L4 | 5 | `::test_digest_scheme_well_formed_shape` (3 cases) | +/- |
| T16 | Worked example 4 (`identity-epoch-privacy-profile.ttl`) compiles, instantiates, parses and conforms to SHACL; `invalid-position-event-without-derivation.ttl` fails SHACL; both negative fixtures fail compilation | L4 | 1–5 | `test_compiler_integration.py` (end-to-end, negative-fixture and SHACL suites) | +/- |

## One command to run everything

```bash
mise run check:persistence
```

## Expected artifacts

**570 passed, 0 failed** (2026-09-23, from the repository root by `mise`, and from `tools/persistence` directly). The count before this slice was 526.

## Adversarial probes (run during this slice)

| Probe | Result |
|---|---|
| Collapse every profile into one role bucket in `resolver.resolve_identity` | 14 failures |
| Disable the claimed-surrogate key check | fails T13 and T14 and the negative-fixture test (4 tests) |
| Weaken the digest-width rule from a multiple of 8 to a multiple of 4 | fails T10 (the 100-bit case) |

All three were restored and the full suite re-run green.

## Deliberate non-coverage

- **No minting is generated** (plan decision 2). `iri-identity-patterns.md` §14.2 now records which of its compilation responsibilities are implemented.
- **The alias-policy check** from §14.2 item 2 is not implemented: `dal:AliasResolutionStrategy` is still a candidate term with no vocabulary.
- **`dal:AdoptedIdentity` and `dal:ExternalRegistryIdentity`** resolve and are emitted but have no checks: nothing in the vocabulary yet names the external authority's binding.
- **Worked example 4's privacy profile** is validated by SHACL only. The compiler resolves it from Slice 4.
- **The claimed-key check** requires at least one uniqueness constraint on the target. It does not check that a constraint's key is the one the claim is minted from, because the vocabulary does not link an identity profile to a specific constraint.
