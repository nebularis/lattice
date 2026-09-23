<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack — `identity-minting` M1

**Slice:** Vocabulary and compiler recipe emission
**Plan:** [identity-minting.md](../plans/identity-minting.md#m1--vocabulary-and-compiler-emission)
**Status:** [identity-minting.md](../status/identity-minting.md)
**Mode:** autonomous (granted 2026-09-23)

## What invariants does this slice protect?

1. **The compiler's recipes are the anchors' recipes.** A configuration written from the vocabulary compiles to exactly the six hand-authored recipes in `contracts/identity/anchor-vectors.json`, digests included. Compiler, contracts and specification cannot drift apart without a test failing.
2. **Every emitted recipe satisfies the published schema.**
3. **A recipe is complete or it is refused, by name.** No member a minter needs is ever defaulted silently.
4. **The recipe in the TTL and the recipe on disk are the same bytes.** The compiled profile stores canonical JSON, and export re-checks the digest.
5. **Rotation is carried through:** two claims during `Dual`, and a `Retiring` scheme never minted.

## Test case table

| ID | Given / When / Then | Level | Pass criterion | +/- |
|---|---|---|---|---|
| T1 | `identity-minting-anchors.ttl` compiles to recipes equal to the six anchor recipes | L2 | `test_identity_minting_m1.py::test_compiled_recipes_equal_the_hand_authored_anchor_recipes` | + |
| T2 | Every recipe from two fixtures validates against `recipe.schema.json` | L3 | `::test_every_emitted_recipe_satisfies_the_published_schema` | + |
| T3 | Recipe digests recomputed with the standard library match | L1 | `::test_recipe_digest_recomputed_independently` | + |
| T4 | Digests are identical under three triple shuffles | L2 | `::test_recipe_digests_are_invariant_under_triple_order` | + |
| T5 | Six `dal:MintingRecipe` nodes, each with an `rdf:JSON` document whose digest and role match its properties | L1 | `::test_recipes_are_emitted_as_canonical_json_literals` | + |
| T6 | `export_recipes` writes the six recipes unchanged, and refuses a tampered document | L1 | `::test_export_recipes_writes_each_recipe_and_refuses_a_tampered_one` | +/- |
| T7 | `persistence compile` then `persistence export-recipes` on the command line | L4 | `::test_export_recipes_cli` | + |
| T8 | A content-addressed recipe carries CA-1 to CA-4 and raises the warning | L1 | `::test_content_addressed_recipes_carry_and_warn_the_caller_obligations` | + |
| T9 | Two `Dual` schemes give two claims in version order; a `Retiring` scheme is omitted | L1 | `::test_dual_rotation_emits_both_claims_in_version_order`, `::test_retiring_scheme_is_not_minted` | + |
| T10 | 21 incomplete configurations, one per missing or wrong member, each refused with its named kind | L1 | `::test_incomplete_recipe_is_refused` (21 cases) | - |
| T11 | An adopted identity yields a validation-only recipe, and is refused without its pattern | L1 | `::test_adopted_identity_recipe_validates_only`, `::test_adopted_identity_without_pattern_is_refused` | +/- |
| T12 | Every fixture's SHACL validation runs without an engine error | L4 | `test_compiler_integration.py::TestShaclSelfValidation::test_shapes_run_without_engine_errors` | + |
| T13 | The new fixture compiles, instantiates and parses end to end, and conforms to SHACL; `invalid-claimed-identity-without-key.ttl` now fails SHACL too | L4 | `test_compiler_integration.py` suites | +/- |

## One command

```bash
mise run check:persistence
```

**629 passed, 0 failed** (2026-09-23). Before this slice: 570.

## Adversarial probes

| Probe | Result |
|---|---|
| Canonical JSON without sorted keys | 3 failures (T1, T3, T6) |
| Constraint applicability check removed | 2 failures (the two `KeyConstraintNotApplicable` refusals) |
| `Retiring` schemes minted | 1 failure (T9) |

All restored, suite green.

## Contract changes (non-weakening rule)

- **Slice 3's claimed-key check is replaced by an exact one.** Slice 3 required "at least one uniqueness constraint on the target", for entity and aggregate-root roles only. M1 requires `dal:claimsConstraint` to name a constraint that applies to the target and has a complete claim scheme, for every role using a claimed surrogate, because the recipe cannot be built otherwise. `test_slice_3_identity.py::test_claimed_identity_requires_a_key` and `::test_claimed_identity_on_other_roles_is_not_checked_for_a_key` are replaced by `::test_claimed_identity_requires_a_named_key`, which is strictly stronger. The check moved from `validator.check_identity` to `persistence.recipes`.
- **Identity profiles that mint must be complete.** The Worked Example 4 fixture and `test_identity_generates_no_operations` gained the members a recipe needs (template, surrogate kind, claim scheme, position widths).
- **`invalid-claimed-identity-without-key.ttl` is now a SHACL negative as well**, through `dal:MintingRecipeMembersShape`.

## Found on the way

- **A SHACL constraint that cannot run makes a graph "not conform".** My first version of the new shapes used `VALUES` inside `sh:select`, which SHACL-SPARQL forbids. The negative fixture then failed SHACL for the engine error, not the rule. Fixed with `FILTER (?s IN …)`. T12 now guards every fixture against this, and the negative fixtures were confirmed to fire their intended shape messages.
- **Derived-hash and natural-key identities had no source for their key.** Resolved as plan decision P6, `dal:keyConstraint`, with the scope value first.
- **The content-addressed recipe needed vocabulary the plan did not list:** `dal:selfReferenceRule` (three individuals) and `dal:canonicalizationWorkBudget`.
