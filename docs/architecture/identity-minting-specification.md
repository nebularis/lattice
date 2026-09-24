<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Identity Minting Specification

**Status:** Draft, normative once [ADR-A84](decisions/ADR-A84-standalone-minting-libraries.md) and the amended [ADR-A82](decisions/ADR-A82-framework-neutral-identity-pattern-selection.md) are ratified. Sections marked *(M4)* are completed in slice M4 of the [`identity-minting`](../developer/plans/identity-minting.md) unit.
**Version:** recipe format `lattice-minting-recipe/1`, vectors format `lattice-minting-vectors/1`, Unicode 16.0.0
**Contracts:** [`contracts/identity/`](../../contracts/identity/README.md) (JSON schemas, anchor vectors, independent verifier)

This document defines how an IRI is minted from a LATTICE minting recipe, precisely enough that two independent implementations produce the same bytes. It is written for three readers: someone using the LATTICE Java or Python minting library, someone implementing their own minter without any LATTICE code, and someone checking either against the conformance vectors. The last two need nothing but this document, the schemas and the vectors.

"Must" is a requirement for conformance. Anything not stated here is not required.

---

## 1. Where a recipe comes from, and what a minter does

An adopter configures identity in `ontology/persistence` (`dal:IdentityProfile`, [iri-identity-patterns.md](iri-identity-patterns.md)). The LATTICE persistence compiler resolves that configuration per target class and resource role and emits one **recipe** per role: a JSON document that says everything needed to mint that role's IRIs, and nothing about where it came from. `persistence export-recipes` writes the recipes to files, together with conformance vectors for each.

A **minter** takes a recipe and a request's inputs, and returns an IRI (and, for claimed identity, one or two claim IRIs), or a named error. A minter never reads the adopter's configuration, never stores a secret, and never calls a network service.

## 2. Recipe documents

A recipe is a JSON object validated by [`recipe.schema.json`](../../contracts/identity/recipe.schema.json). Its members, per strategy, are listed in [§6](#6-strategies). Every recipe has:

| Member | Meaning |
|---|---|
| `recipeFormat` | exactly `"lattice-minting-recipe/1"`. Any other value: `UnsupportedRecipeFormat` |
| `recipeDigest` | `"sha256:"` followed by 64 lowercase hex digits (§2.1) |
| `role` | the resource role, a local name from `dal:ResourceRole` |
| `target` | `{ "class": IRI, "deployment": IRI or null }`, for traceability only. A minter does not use it |
| `strategy` | selects the algorithm in §6 |
| `iriTemplate` | the minted IRI's shape (§5) |

### 2.1 The recipe digest

A minter must verify the digest before using a recipe, and refuse a mismatch with `RecipeDigestMismatch`. The digest is SHA-256 over the recipe's **canonical JSON** with the `recipeDigest` member removed, written as `"sha256:"` plus lowercase hex.

Canonical JSON is RFC 8785 (JSON Canonicalization Scheme). Recipes are restricted so that RFC 8785 needs no number formatting: they contain only strings, integers, `true`, `false`, `null`, arrays, and objects whose keys are ASCII. Under that restriction the canonical form is:

- no insignificant whitespace;
- object members sorted by key, comparing keys as sequences of code units (for ASCII keys, byte order);
- integers written in plain decimal with no leading zeros, no exponent, no plus sign;
- strings in double quotes, escaping only `"` as `\"`, `\` as `\\`, U+0008, U+0009, U+000A, U+000C and U+000D as `\b`, `\t`, `\n`, `\f`, `\r`, and every other code point below U+0020 as `\u` followed by four lowercase hex digits. Every other character, including non-ASCII, is written as itself;
- the result encoded as UTF-8.

## 3. Unicode

### 3.1 The pinned version

Every Unicode-dependent step uses the Unicode Character Database **16.0.0**, from `https://www.unicode.org/Public/16.0.0/ucd/`. A recipe's pipeline states its `unicodeVersion`, and this version of the specification accepts only `"16.0.0"`. Moving to another Unicode version is a new pipeline, and so a re-key: an IRI minted under one version is never silently reinterpreted under another.

The steps use these files: `UnicodeData.txt` (assignment, simple case mappings), `SpecialCasing.txt` (full case mappings), `DerivedNormalizationProps.txt` (the `NFKC_CF` mapping), `PropList.txt` (`White_Space`).

NFC and NFKC may use the runtime's own implementation, because Unicode's normalization stability policy fixes the normalization of every assigned code point for all later versions. That is safe only if the runtime's Unicode data is at least 16.0.0 and every code point is assigned in 16.0.0, which is why a minter must refuse to run on older Unicode data (`RuntimeUnicodeTooOld`) and why every pipeline starts with `reject_unassigned`.

### 3.2 Pipeline steps

A pipeline is a list of steps applied in order to one key component. The recipe lists the steps explicitly: a minter must follow the list, never infer steps from the pipeline's `id`.

| Step | Definition |
|---|---|
| `reject_unassigned` | If any code point's General_Category is `Cn` in `UnicodeData.txt` 16.0.0 (that is, it is not listed, individually or in a `First`/`Last` range), fail with `UnassignedCodePoint`. Always the first step |
| `nfc` | Unicode Normalization Form C (UAX #15) |
| `nfkc` | Unicode Normalization Form KC (UAX #15) |
| `nfkc_casefold` | Map every code point through its `NFKC_CF` value in `DerivedNormalizationProps.txt` (a code point with no `NFKC_CF` entry maps to itself; an entry with an empty value maps to nothing), then apply NFC. This is Unicode's `toNFKC_Casefold`. It removes every default-ignorable code point, and it is not the same as lowercasing, nor as casefolding plus NFKC in a language library |
| `trim_white_space` | Remove code points with the `White_Space` property (`PropList.txt`) from both ends. Not a language's own notion of whitespace: see [§11](#11-pitfalls-m4) |
| `uppercase_full` | Unicode default full uppercase mapping: the unconditional mappings in `SpecialCasing.txt`, otherwise the simple uppercase in `UnicodeData.txt`, otherwise the code point itself. No language-specific (for example Turkish) mappings |
| `lowercase_full` | Unicode default full lowercase mapping, the same way, including the `Final_Sigma` context from `SpecialCasing.txt` and no language-specific mappings |

After the last step, an empty component fails with `EmptyKeyComponent`.

The three pipelines a recipe can name expand to:

| `id` | `steps` |
|---|---|
| `NfkcTrimCasefold` | `reject_unassigned`, `nfkc_casefold`, `trim_white_space` |
| `NfkcTrimUppercase` | `reject_unassigned`, `nfkc`, `trim_white_space`, `uppercase_full`, `nfkc` |
| `NfkcTrimLowercase` | `reject_unassigned`, `nfkc`, `trim_white_space`, `lowercase_full`, `nfkc` |

Case mapping can produce a sequence that is not in NFKC, which is why the upper- and lowercase pipelines end with a second `nfkc`.

## 4. Bytes

### 4.1 Tuple encoding `length-prefixed-utf8/1`

A tuple of strings `[c1, c2, …]` encodes as, for each component in order: the number of **UTF-8 bytes** in the component, written in ASCII decimal with no leading zeros (`0` for an empty component), then `:` (0x3A), then the component's UTF-8 bytes. There is no separator between components and no terminator. The encoding is self-delimiting, so no component value can make two different tuples encode alike.

Example: `["v1", "person-email-unique", "acme", "ada@example.org"]` encodes as the ASCII text `2:v119:person-email-unique4:acme15:ada@example.org`.

### 4.2 Digests, MACs and truncation

`SHA-256` is FIPS 180-4. `HMAC-SHA-256` is RFC 2104 with SHA-256, keyed with the secret's bytes exactly as supplied. A recipe's `widthBits` is a multiple of 8, and truncation keeps the **first** `widthBits / 8` bytes of the digest or MAC.

### 4.3 Output encodings

| `encoding` | Definition |
|---|---|
| `lowercase-hex` | two lowercase hex digits per byte |
| `base32` | RFC 4648 §6, the standard alphabet `A`–`Z`, `2`–`7`, uppercase, with trailing `=` padding removed |
| `base64url` | RFC 4648 §5, `-` and `_`, with trailing `=` padding removed |

## 5. IRI templates

A template is a string with named slots written `{name}`, where the name is ASCII letters. Rendering replaces each slot with its value and leaves every other character unchanged. Slot values are inserted as they are, with no further escaping, because every slot value is already restricted to IRI-safe characters by the step that produces it. The slots available depend on the strategy (§6). A template may contain a slot more than once.

## 6. Strategies

A request's inputs are a JSON object, the `inputs` member of a vector. Its members:

| Member | Strategies | Value |
|---|---|---|
| `key` | natural key, derived hash, claimed | array of strings, the values for `key.properties` in that order |
| `scope` | the same, when `key.scopeProperty` is not `null` | string |
| `surrogate` | claimed, `CallerSuppliedSurrogate` | string |
| `randomHex` | random, claimed `UuidV4Surrogate` | 32 hex digits used in place of fresh randomness. **For conformance vectors only.** A production minter must ignore it or refuse it |
| `target` | position-derived, `HashedTargetDerivation` | the target IRI as a string |
| `namespaceToken` | position-derived, `RegistryTokenDerivation` | string |
| `epoch`, `seq` | position-derived | JSON integers |
| `canonicalNQuads` | content-addressed | string, the canonical N-Quads |
| `canonicalizer` | content-addressed | string naming the RDFC-1.0 implementation that produced `canonicalNQuads` (§7) |
| `iri` | adopted, external registry | string |

In every algorithm below, a key's components are the request's values for the recipe's `key.properties`, in that order. A missing value fails with `MissingKeyComponent`. Each component goes through the key's pipeline (§3.2).

When `key.scopeProperty` is not `null`, the request's value for that property (its IRI, or a literal's lexical form) is the **scope value**. It is placed before the normalized components, and it is used exactly as given: it is not normalized, because a scope is an identifier, not a key someone types. A missing scope value fails with `MissingKeyComponent`. Scope matters for identity: two tenants' identical natural keys must not mint the same IRI.

### 6.1 `DerivedHashIdentity`

1. Normalize each key component.
2. Encode the tuple `tuplePrefix + [scope value, if any] + normalized components` (§4.1).
3. SHA-256, truncate to `digest.widthBits`, encode with `digest.encoding`.
4. Render `iriTemplate` with `{digest}`.

### 6.2 `NaturalKeyIdentity`

1. Normalize each key component.
2. Percent-encode the scope value, if any, and each normalized component, from their UTF-8 bytes: the RFC 3986 unreserved characters `A`–`Z`, `a`–`z`, `0`–`9`, `-`, `.`, `_`, `~` are kept, and every other byte is written `%` followed by two **uppercase** hex digits. A `/` inside a component becomes `%2F`.
3. Join the encoded values with `/` and render `iriTemplate` with `{key}`.

### 6.3 `SurrogateClaimedIdentity`

The entity IRI is a surrogate. The recipe's `claims` are minted alongside it: one claim, or two during a claim-scheme rotation in the `Dual` state, in the order listed.

1. **Surrogate.** For `UuidV4Surrogate`, generate a random version 4 UUID (RFC 9562): take 16 bytes `b` from a cryptographically secure random source, set `b[6] = (b[6] & 0x0F) | 0x40` and `b[8] = (b[8] & 0x3F) | 0x80`, and write the bytes as lowercase hex grouped 8-4-4-4-12 with `-`. Vectors supply the 16 bytes as `randomHex` so that this step can be tested. For `CallerSuppliedSurrogate`, take the request's surrogate and check it matches `surrogate.pattern` in full (§6.8), or fail with `PatternMismatch`.
2. Render `iriTemplate` with `{surrogate}`.
3. **Each claim.** Every claim in a recipe carries the same `key` (a recipe whose claims differ is refused with `UnsupportedRecipeFormat`), so the key components are normalized once, with that key's pipeline. Encode the tuple `[schemeVersion, constraintId, scope value, …normalized components]`, where the scope value is the request's value for `key.scopeProperty`, or the empty string when `scopeProperty` is `null`. Compute HMAC-SHA-256 with the secret identified by `keyId` (§8), or fail with `MissingSecret`. Truncate to `mac.widthBits`, encode with `mac.encoding`, and render the claim's `iriTemplate` with `{constraintId}`, `{schemeVersion}` and `{mac}`.

### 6.4 `RandomSurrogateIdentity`

Generate a version 4 UUID as in §6.3 step 1 and render `iriTemplate` with `{surrogate}`. Only the IRI's format can be conformance-tested.

### 6.5 `PositionDerivedEvent`

1. **Namespace.** For `HashedTargetDerivation`, a missing target fails with `MissingKeyComponent`. Encode the tuple `["occurrence-namespace/1", target IRI]`, SHA-256 it, truncate to `namespace.digest.widthBits`, and encode with `namespace.digest.encoding`. For `RegistryTokenDerivation`, the namespace is the token the request supplies, which must match `^[A-Za-z0-9._~-]+$`, or fail with `PatternMismatch`.
2. **Position.** A missing or non-integer epoch or sequence fails with `MissingKeyComponent`. Each must be from 0 to 9223372036854775807, or fail with `PositionOutOfRange`. Each is written in decimal, left-padded with zeros to `epochWidth` and `sequenceWidth`.
3. Render `iriTemplate` with `{namespace}`, `{epoch}` and `{seq}`.

### 6.6 `ContentAddressedIdentity`

**A minter hashes bytes. It does not canonicalize RDF.** The request supplies canonical N-Quads that the caller has already produced, and the correctness of the resulting identity rests on the caller's obligations in [§7](#7-content-addressed-identity-the-callers-obligations).

1. The request must name the RDFC-1.0 implementation that produced the bytes in `canonicalizer`, a string containing at least one code point without the `White_Space` property, or the minter fails with `CanonicalizerNotDeclared`. "Blank" is judged by `White_Space`, never by a language's own whitespace test (§11). The minter cannot check the statement. It exists so that every content-addressed call records who is answerable for CA-1, and so that no caller reaches a digest without meeting §7.
2. SHA-256 the UTF-8 bytes of `canonicalNQuads` (missing: `MissingKeyComponent`), truncate to `digest.widthBits`, encode with `digest.encoding`.
3. Render `iriTemplate` with `{digest}`.

### 6.7 `AdoptedIdentity` and `ExternalRegistryIdentity`

Nothing is minted. The minter validates an IRI supplied by the naming authority against `acceptedPattern` (§6.8), or fails with `PatternMismatch`.

### 6.8 Patterns

Patterns are ASCII regular expressions matched against the **whole** value. They may use literals, `.`, character classes with ranges and negation, the quantifiers `*`, `+`, `?`, `{n}`, `{n,m}`, anchors `^` and `$`, alternation and groups. They must not use `\d`, `\w`, `\s`, lookaround, backreferences or flags, because those differ between regular-expression engines (Python's `\d` matches every Unicode digit, Java's does not).

## 7. Content-addressed identity: the caller's obligations

Two parties who canonicalize the same graph differently mint different IRIs for it, and no conformance vector can detect that, because the vectors start from bytes that are already canonical. Every content-addressed recipe carries these obligations in its `callerObligations` member. A caller must meet all of them:

| Id | Obligation | Why |
|---|---|---|
| CA-1 | The bytes are the output of an RDFC-1.0 implementation that passes the W3C RDFC-1.0 test suite, serialized as canonical N-Quads in UTF-8, one line per quad, each terminated by a single LF, with no other bytes | Any other canonicalization, or a byte-level difference such as CRLF line endings or a byte-order mark, changes the digest |
| CA-2 | The recipe's self-reference rule is applied **before** canonicalization | A graph that contains its own identifier cannot be hashed directly: the identifier would depend on itself ([iri-identity-patterns.md §8.3](iri-identity-patterns.md#83-self-reference-pattern)) |
| CA-3 | Canonicalization stops at the recipe's `workBudget`, and the graph is refused, never hashed on a best-effort basis | Adversarial blank-node structures make RDFC-1.0 expensive. A best-effort hash is a different identity ([§8.4](iri-identity-patterns.md#84-complexity-and-blank-node-cost)) |
| CA-4 | Where `verifyFullDigest` is true, the full digest is stored and compared on every re-registration of the identifier | A truncated digest in an IRI is not collision protection on its own ([§8.5](iri-identity-patterns.md#85-registration-verification)) |

## 8. Secrets

A recipe names a claim secret by `keyId` and never contains it. A minter receives the secret's bytes from its caller and does not return, log or persist them. A secret of zero bytes is treated as no secret (`MissingSecret`). The vectors publish a **test secret** (`testSecrets`), clearly labelled: it exists so that anyone can reproduce the claim vectors, and must never be used in production.

## 9. Named errors

| Error | Raised when |
|---|---|
| `UnsupportedRecipeFormat` | `recipeFormat` is not `lattice-minting-recipe/1`, the strategy is unknown, a pipeline's `unicodeVersion` is not `16.0.0`, a pipeline does not start with `reject_unassigned` or names an unknown step, or a recipe's claims carry different keys |
| `RecipeDigestMismatch` | the recomputed digest differs from `recipeDigest` |
| `RuntimeUnicodeTooOld` | the runtime's Unicode data is older than 16.0.0 |
| `MissingKeyComponent` | a request lacks a key value, the scope value, the target IRI, an integer epoch or sequence, or the canonical N-Quads |
| `UnassignedCodePoint` | a key component contains a code point unassigned in Unicode 16.0.0 |
| `EmptyKeyComponent` | a key component is empty after its pipeline |
| `MissingSecret` | no secret, or an empty one, is supplied for a claim's `keyId` |
| `PatternMismatch` | a caller-supplied surrogate, registry token or adopted IRI does not match its pattern |
| `PositionOutOfRange` | an epoch or sequence is negative or above 9223372036854775807 |
| `CanonicalizerNotDeclared` | a content-addressed request does not name its RDFC-1.0 implementation (§6.6) |

The checks run in the order of the algorithms in §6, so a request with two faults raises the first one its strategy reaches. A vector never depends on that order: each negative vector has exactly one fault.

## 10. Conformance vectors

### 10.1 Format

A vectors document ([`vectors.schema.json`](../../contracts/identity/vectors.schema.json)) embeds the recipe it tests, any test secrets, and three lists:

- **Positive vectors:** `inputs` (§6), the final `iri` (and `claimIris` for claimed identity), and a `trace` of every intermediate value in order. Steps belonging to a claim carry its index as `claim`.
- **Negative vectors:** `inputs` and the named `error` that must be raised. An `inputs` member `omitSecret` is a directive to the test harness, not a request input: run the vector without the secret for that key id.
- **Format vectors:** for non-deterministic strategies, a pattern and example IRIs to `accept` and `reject`.

Trace steps, in the order a strategy produces them:

| `step` | Members | Produced by |
|---|---|---|
| `normalize` | `component` (index), `pipeline` (id), `input`, `after` (`{step, output}` per pipeline step), `output`, and in anchors `ucd` (citations, not compared) | each key component |
| `tuple` | `components`, `hex` (the encoded bytes) | §4.1 |
| `digest` | `function` (`SHA-256`), `hex` (full digest) | §4.2 |
| `mac` | `function` (`HMAC-SHA-256`), `keyId`, `hex` (full MAC) | §6.3 |
| `truncate` | `widthBits`, `hex` | always after `digest` or `mac`, even when `widthBits` is 256 |
| `encode` | `encoding`, `value` | §4.3 |
| `percent-encode` | `components` (encoded) | §6.2 |
| `validate-surrogate` | `pattern`, `value` | §6.3, caller-supplied |
| `generate-surrogate` | `randomHex`, `value` | §6.3 and §6.4 |
| `validate-token` | `pattern`, `value` | §6.5, registry token |
| `pad` | `epoch`, `seq` (padded strings) | §6.5 |
| `validate-iri` | `pattern`, `value` | §6.7 |
| `render` | `iri` | every rendered template |

Test secrets in generated vectors are SHA-256 of the UTF-8 text `lattice-minting-test-secret/` followed by the key id. Vector files write every non-ASCII character as a JSON `\u` escape, so that invisible characters in the inputs can be read in review. Any JSON parser restores them.

### 10.2 Anchor vectors

Generated vectors cover the seven anchor recipes and four coverage recipes ([`identity-minting-coverage.ttl`](../../ontology/persistence/examples/identity-minting-coverage.ttl)) that exercise what the anchors leave out: the lowercase pipeline, base64url, a generated surrogate with two claims in rotation, a registry-token namespace and an external registry identifier. The coverage recipes have no anchors.

[`anchor-vectors.json`](../../contracts/identity/anchor-vectors.json) holds hand-authored vector sets, one per deterministic strategy, whose every byte is recomputed by [`verify-anchors.py`](../../contracts/identity/verify-anchors.py) with `openssl` and the Python standard library, sharing no code with any minting library. Vectors generated from a library can only show that other implementations agree with it; the anchors are what show that it is right. A conformant implementation passes the anchors **and** the generated vectors for every recipe it serves.

### 10.3 Verifying an implementation without LATTICE code

1. Implement §2–§9 for the strategies you need.
2. For each vectors file: check the embedded recipe's digest (§2.1) and confirm it is the recipe you serve.
3. For each positive vector, run your minter on `inputs` and compare **each trace step in order**, not only the final IRI. The first step that differs tells you where your implementation diverges: see [§11](#11-pitfalls-m4) for the usual causes, by step.
4. For each negative vector, confirm your minter raises the named error, and produces no IRI.
5. For each format vector, confirm your minted or accepted IRIs match its pattern, and that the `reject` examples are rejected.
6. Do all of this for `anchor-vectors.json` as well as your recipes' generated vectors.
7. Record conformance as: recipe digest, vectors file SHA-256, all passed.

## 11. Pitfalls *(M4)*

To be completed in M4 with an explanation and a detecting vector for each. Already known:

- **String length is not byte length.** Java's `String.length()` counts UTF-16 code units and Python's `len()` counts code points. The tuple encoding needs UTF-8 bytes.
- **Language trims are not `White_Space`.** Python's `str.strip()` removes U+001C–U+001F, which are not `White_Space`. Java's `String.strip()` keeps U+00A0 NO-BREAK SPACE, which is. The anchor `cl-control-not-trimmed` catches the first.
- **Lowercasing is not case folding.** `toLowerCase` leaves `ß` as `ß`, where `nfkc_casefold` gives `ss` (anchor `cl-sharp-s`).
- **Default-ignorable code points survive NFKC.** Zero-width space and soft hyphen are removed only by `nfkc_casefold` (anchors `cl-zero-width`, `cl-soft-hyphen`). Under `NfkcTrimUppercase` and `NfkcTrimLowercase` they stay in the key, so a key made of nothing else mints an IRI rather than failing with `EmptyKeyComponent` (generated vector `key-default-ignorable-only-survives`).
- **base32 padding and case.** Output is uppercase with no `=`.
- **Regular-expression classes differ between engines** (§6.8).

## 12. Worked example: a derived-hash SKU

The recipe (anchor set 0) derives a product IRI from its SKU: pipeline `NfkcTrimUppercase`, `tuplePrefix` `["iri", "v1", "sku"]`, SHA-256 truncated to 160 bits, base32, template `urn:ex:sku:{digest}`. Input: ` Widget-9 ` (with a leading and a trailing space).

| Step | Value |
|---|---|
| `reject_unassigned` | all assigned, unchanged |
| `nfkc` | ` Widget-9 ` |
| `trim_white_space` | `Widget-9` |
| `uppercase_full` | `WIDGET-9` |
| `nfkc` | `WIDGET-9` |
| tuple text | `3:iri2:v13:sku8:WIDGET-9` |
| tuple bytes (hex), one group per component | `333a697269` `323a7631` `333a736b75` `383a5749444745542d39` |
| SHA-256 (hex) | `b823783f51e7dfe63cab9d45cd6958849de216ccda6bf467e5c7c753ec1bb0f5` |
| first 20 bytes (hex) | `b823783f51e7dfe63cab9d45cd6958849de216cc` |
| base32 | `XARXQP2R47P6MPFLTVC422KYQSO6EFWM` |
| IRI | `urn:ex:sku:XARXQP2R47P6MPFLTVC422KYQSO6EFWM` |

Reproduce it without any LATTICE code:

```bash
printf '3:iri2:v13:sku8:WIDGET-9' | openssl dgst -sha256
python3 -c "import base64; print(base64.b32encode(bytes.fromhex('b823783f51e7dfe63cab9d45cd6958849de216cc')).decode().rstrip('='))"
```

A worked example for every other strategy, including a claim with its MAC, is added in M4.
