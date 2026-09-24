<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack — `identity-minting` M3

**Slice:** The Java library, and vector coverage of every recipe feature
**Plan:** [identity-minting.md](../plans/identity-minting.md#m3--java-library)
**Status:** [identity-minting.md](../status/identity-minting.md)
**Mode:** autonomous (granted 2026-09-23)

## What invariants does this slice protect?

1. **Two independent implementations agree byte for byte.** The Java library passes every anchor and every vector the Python library generates, compared trace step by trace step.
2. **Every recipe feature has vectors.** Each pipeline, output encoding, surrogate kind, namespace derivation, rotation state and strategy appears in at least one generated vectors file.
3. **The Java library takes nothing from the JDK that differs from the specification.** Case mapping, whitespace and assignment come from the shared tables, lengths are UTF-8 bytes, and the JDK's Unicode version is checked.
4. **The Java library stands alone.** Its own `pom.xml`, JDK 25 only, JUnit at test scope.

## Test case table

| ID | Given / When / Then | Level | Pass criterion | +/- |
|---|---|---|---|---|
| T1 | All seven anchor sets | L3 | `ConformanceTest.anchorsPass` | +/- |
| T2 | All eleven generated vectors files | L3 | `ConformanceTest.generatedVectorsPass` (11), `elevenGeneratedVectorFiles` | +/- |
| T3 | A changed trace step is reported by step number | L1 | `ConformanceTest.aChangedTraceStepIsNamed` | - |
| T4 | The command line exits 0, 2 on bad usage, 1 on a failing file | L4 | `ConformanceTest.cli` | +/- |
| T5 | Java and Python table copies are byte-identical | L1 | `UcdTest.tablesAreTheCopiesThePythonLibraryReads` | + |
| T6 | Assigned set equals `Character.isDefined` over every code point | L2 | `UcdTest.assignedMatchesTheJdk` | + |
| T7 | Full case mappings equal the JDK's under `Locale.ROOT` for every assigned code point, and `Final_Sigma` in context | L2 | `UcdTest.fullCaseMappingsMatchTheJdkRootLocale`, `finalSigmaInContext` | + |
| T8 | `White_Space` differs from `Character.isWhitespace` at exactly U+001C–U+001F, U+0085, U+00A0, U+2007, U+202F | L2 | `UcdTest.whiteSpaceIsNotJavaWhitespace` | + |
| T9 | Recipes use the specification's pipelines, and all three are idempotent on every assigned code point | L2 | `UcdTest.recipesUseThePipelinesOfTheSpecification`, `everyPipelineIsIdempotent` | + |
| T10 | UTF-8 byte counts, percent-encoding and base32 (RFC 4648 §10) | L1 | `UcdTest.tupleLengthsAreUtf8Bytes`, `percentEncodingIsPerUtf8Byte`, `base32MatchesRfc4648` | + |
| T11 | JSON: canonical form, exact large integers, surrogate pairs, nine refused inputs | L1 | `JsonTest` (6) | +/- |
| T12 | Recipe, runtime, secret, canonicalizer and randomness refusals | L1 | `RefusalTest` (11) | +/- |
| T13 | Python: the two parity cases below, and all three pipelines from the specification | L1 | `test_refusals.py::test_an_empty_secret_is_no_secret`, `::test_a_blank_canonicalizer_is_judged_by_white_space`, `test_unicode.py::test_recipes_use_the_pipelines_of_the_specification` | +/- |
| T14 | The coverage fixture compiles, instantiates and conforms to SHACL | L4 | `test_compiler_integration.py` suites | + |

## Commands

```bash
mise run check:minting            # anchors 187 checks, Python 66 passed, Java 43 passed
mise run check:persistence        # 669 passed
mise run check:minting-tables     # 16 tables current
```

All green on 2026-09-24: JDK 25.0.2, Maven 3.9.16, Python 3.14.7.

## Adversarial probes (Java)

| Probe | Result |
|---|---|
| `Final_Sigma` disabled | 1 failure before the coverage vectors, 3 after |
| `String.strip()` in place of `trimWhiteSpace` | 6 failures |
| `String.length()` in the tuple encoding | 6 failures |
| Truncation keeps the last bytes | 5 failures |
| Lowercase hex in percent-encoding | 4 failures |

All restored, suite green.

## Contract changes (non-weakening rule)

- **An empty secret is refused** with `MissingSecret`, in both libraries (specification §8, §9). Python accepted it and Java's `SecretKeySpec` cannot represent it, so the two would otherwise have differed.
- **A blank canonicalizer is judged by `White_Space`** in both libraries (§6.6). Python used `str.strip()` and Java would have used `isBlank()`, which disagree on U+00A0 and U+001C–U+001F.
- **Four coverage recipes** from the new positive fixture `identity-minting-coverage.ttl` join the testdata: eleven vectors files, up from seven. The anchor tests now check that the anchor recipes are a subset of the compiled ones.
- **`check` runs `check:minting`**, which aggregates the anchors, Python and Java checks.

## Found on the way

- **No vector exercised `lowercase_full`, base64url, `validate-token`, a generated claimed surrogate, a `Dual` rotation or `ExternalRegistryIdentity`.** The anchor fixture needs only one recipe per strategy, and the M2 idempotence test read its pipelines from the testdata, so it missed the lowercase pipeline too. The Java final-sigma probe exposed the gap. Fixed by the coverage fixture and by taking the pipelines from the specification's table.
- **A registry-token event profile must declare a digest scheme it never uses.** The Slice 3 identity check requires `dal:digestScheme` on every `dal:DerivedHashIdentity` profile, including position-derived events whose namespace is a registry token. The coverage fixture carries an unused scheme with a comment. Recorded in the status record for `persistence-compiler-iri-sync`.
- **`AdoptedIdentity` and `ExternalRegistryIdentity` vectors are negative only.** The generator cannot invent an identifier that matches an arbitrary pattern. The adopted anchor set holds positive vectors for `validate-iri`.
