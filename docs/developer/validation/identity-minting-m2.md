<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack — `identity-minting` M2

**Slice:** Pinned Unicode 16.0.0 tables, the Python library, vector generation
**Plan:** [identity-minting.md](../plans/identity-minting.md)
**Status:** [identity-minting.md](../status/identity-minting.md)
**Mode:** autonomous (granted 2026-09-23)

## What invariants does this slice protect?

1. **The library mints what the anchors say.** Every anchor vector, verified independently with `openssl`, passes trace step by trace step.
2. **The committed vectors are what the library generates today.** A behaviour change cannot land without regenerating `packages/minting/testdata` and showing the diff.
3. **Unicode behaviour comes from the pinned tables, and the tables are right.** Both libraries carry byte-identical tables, the tables match the UCD 16.0.0 files, and over every code point they agree with CPython's own 16.0.0 data wherever the two define the same thing.
4. **Every refusal is named.** Recipe faults, runtime faults and request faults each raise their §9 error.
5. **The library stands alone.** No dependency outside the Python standard library, and no import of any other LATTICE package.

## Test case table

| ID | Given / When / Then | Level | Pass criterion | +/- |
|---|---|---|---|---|
| T1 | All seven anchor sets | L3 | `test_conformance.py::test_anchors_pass` | +/- |
| T2 | All seven generated vectors files | L3 | `::test_generated_vectors_pass` (7) | +/- |
| T3 | Regenerating each file's vectors from its embedded recipe gives the committed document | L2 | `::test_generated_vectors_are_current` (7) | + |
| T4 | Each `.recipe.json` equals the recipe embedded in its vectors, and parses | L1 | `::test_recipe_files_match_vectors` (7) | + |
| T5 | The compiled recipes are the anchor recipes | L2 | `::test_anchor_recipes_equal_compiled_recipes` | + |
| T6 | A key of default-ignorables only is refused under `NfkcTrimCasefold` and mints under `NfkcTrimUppercase` | L1 | `::test_default_ignorable_only_depends_on_pipeline` | +/- |
| T7 | A changed expected IRI, and a changed trace step, are reported, the second by step number | L1 | `::test_a_changed_expectation_is_reported`, `::test_a_changed_trace_step_names_the_step` | - |
| T8 | `lattice-mint verify` exits 0, 2 on bad usage, 1 on a failing file | L4 | `::test_cli` | +/- |
| T9 | Python and Java table copies are byte-identical | L1 | `test_unicode.py::test_both_libraries_carry_identical_tables` | + |
| T10 | Assigned set equals General_Category not `Cn`, over all 1,114,112 code points | L2 | `::test_assigned_matches_general_category` | + |
| T11 | Full upper and lower mappings equal `str.upper` and `str.lower` for every assigned code point, and `Final_Sigma` in context | L2 | `::test_full_case_mappings_match_python`, `::test_final_sigma_matches_python` (7) | + |
| T12 | `nfkc_casefold` equals the NFKC and case folding composition where it keeps a character, and removes only format, mark, letter-other or control characters | L2 | `::test_nfkc_casefold_agrees_with_the_casefold_composition` | + |
| T13 | `White_Space` differs from `str.isspace` only at U+001C–U+001F | L2 | `::test_white_space_differs_from_isspace_only_at_the_information_separators` | + |
| T14 | All three pipelines are idempotent on every assigned code point | L2 | `::test_every_pipeline_is_idempotent` | + |
| T15 | Wrong format, unknown strategy, changed content, another Unicode version, claims with different keys | L1 | `test_refusals.py` (5 cases) | - |
| T16 | Digest ignores whitespace and member order | L1 | `::test_whitespace_and_member_order_do_not_affect_the_digest` | + |
| T17 | Unicode data older than 16.0.0 is refused | L1 | `::test_older_runtime_unicode_is_refused` | - |
| T18 | Error kinds are closed, random surrogates use the supplied source and are well formed, secrets are copied | L1 | `::test_error_kinds_are_closed`, `::test_random_surrogates_use_the_supplied_source`, `::test_minter_does_not_share_secrets_with_the_caller` | +/- |

## Commands

```bash
mise run bootstrap:minting-python
mise run check:minting-python     # 51 passed
mise run check:minting-anchors    # 187 checks passed
mise run check:minting-tables     # 16 tables current
mise run check:persistence        # 629 passed
```

All four green on 2026-09-24, Python 3.14.7 (Unicode data 16.0.0).

## Adversarial probes

| Probe | Result |
|---|---|
| `Final_Sigma` disabled | 5 failures |
| `str.strip()` in place of `trim_white_space` | 8 failures |
| Truncation keeps the last bytes | 8 failures |
| `NFKC(casefold(s))` in place of `nfkc_casefold` | 5 failures |

All restored, suite green.

## Contract changes (non-weakening rule)

- **Generated vector files escape non-ASCII.** `export-recipes --vectors` writes JSON with `\u` escapes, and `anchor-vectors.json` was rewritten the same way, so invisible characters in inputs can be read in review. The parsed content is unchanged (the anchor verifier and both suites pass unchanged).
- **A recipe's claims must share one key** (`UnsupportedRecipeFormat` otherwise, specification §6.3). The compiler has always emitted them that way.
- **Specification brought up to the library:** request inputs table (§6), `randomHex`, `validate-token`, `generate-surrogate`, `validate-iri`, `CanonicalizerNotDeclared`, which faults raise `MissingKeyComponent`, `truncate` present even at full width, the `omitSecret` harness directive, and the test secret derivation (§10.1).

## Found on the way

- **Default-ignorable code points under the upper- and lowercase pipelines.** NFKC keeps zero-width space and soft hyphen, and only `nfkc_casefold` removes them. A key made of nothing else is refused as empty under `NfkcTrimCasefold` but mints under the other two pipelines. The generator now emits the vector each pipeline actually implies. Whether those pipelines should remove default-ignorables is a design question, recorded in the status record.
- **Tool input turned `\u` escapes into real characters.** Invisible characters reached `vectors.py`. Every non-ASCII literal in the library source is now written with `chr()`, and all changed files were scanned for format, control and non-ASCII space characters.
