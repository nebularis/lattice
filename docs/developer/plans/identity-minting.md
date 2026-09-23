<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Identity Minting — Plan

**Unit ID:** `identity-minting`
**Status record:** [identity-minting.md](../status/identity-minting.md)
**Sketch:** [identity-minting.md](../sketches/identity-minting.md) (decisions A–E, Q1–Q7, all settled 2026-09-23)
**Governing ADRs:** ADR-A82 (point 5 amended by M0), ADR-A84 (new, M0), ADR-A79, ADR-A78, ADR-A77, ADR-A71, ADR-A29
**Depends on:** [`toolchain-jdk25-python314`](../status/toolchain-jdk25-python314.md) (✅ done), `persistence-compiler-iri-sync` Slice 3 (✅ done)
**Mode:** autonomous (granted 2026-09-23), pausing only for genuinely new design decisions

## Scope

Turn a resolved `dal:IdentityProfile` into a self-contained minting recipe, publish conformance vectors for it, and provide pure Java and Python minting libraries that pass those vectors, together with a normative specification thorough enough for an implementor who uses neither library. Out of scope: publishing artefacts, RDF canonicalization inside the libraries, key management, the shared Rust core (deferred, [sketch](../sketches/identity-minting-shared-core.md)).

## Agent design decisions taken in writing this plan (for human review)

| # | Decision | Why |
|---|---|---|
| P1 | The compiled profile stores each recipe as its **canonical JSON document**, a literal of datatype `rdf:JSON` on a `dal:MintingRecipe` node, alongside a few queryable properties (`dal:forRole`, `dal:recipeStrategy`, `dal:recipeDigest`). The sketch's §5.3 proposed mirroring every recipe field as RDF properties | One serialization instead of two that must be kept in step by hand. The TTL stays canonical and self-contained (decision C), and `export-recipes` becomes extraction plus vector generation |
| P2 | `dal:tuplePrefix` (an `rdf:List` of strings) replaces the sketch's single `dal:domainSeparationLabel` | The guide's own derived-hash example prefixes three literal components (`"iri"`, `"v1"`, `"sku"`). A list is the general form |
| P3 | New terms `dal:epochWidth` and `dal:sequenceWidth` on `dal:IdentityProfile`, both required for `dal:PositionDerivedEvent` | `iri-identity-patterns.md` §10.2 requires one exact width per profile, and the vocabulary has no term for it |
| P4 | A natural key renders into its IRI template's `{key}` slot as its normalized components, each percent-encoded (RFC 3986 unreserved characters kept, everything else `%XX` in uppercase hex, from UTF-8), joined by `/` | Reversible and unambiguous: a `/` inside a component is itself percent-encoded (`iri-identity-patterns.md` §7.2) |
| P6 | *(taken in M1)* Derived-hash and natural-key identities name their key through **`dal:keyConstraint`**, pointing at the `dal:UniquenessConstraint` whose key properties, scope and pipeline they use, just as a claimed identity uses `dal:claimsConstraint`. A key with a scope property puts the scope value first, as given | The plan listed "key properties" in the recipe without saying where they come from. Reusing the constraint makes the derived IRI and the uniqueness check normalize the key identically, and including the scope stops two tenants' identical natural keys minting one IRI |
| P5 | Recipes contain only strings, integers, booleans, `null`, arrays and objects with ASCII keys. The recipe digest is SHA-256 over RFC 8785 (JCS) canonical JSON of the recipe with `recipeDigest` removed | Under those restrictions JCS needs no number-formatting code, so every implementation, including one written from the specification alone, can compute it |

## Recipe format (normative content fixed in M0, schema `contracts/identity/recipe.schema.json`)

```text
recipe = {
  recipeFormat:   "lattice-minting-recipe/1",
  recipeDigest:   "sha256:" + lowercase hex,
  role:           a dal:ResourceRole local name,
  target:         { class: IRI, deployment: IRI | null },
  strategy:       a dal:IdentityStrategy local name,
  iriTemplate:    string with named slots,
  ... strategy-specific members (below) ...,
  callerObligations: [ { id, text } ]      (content-addressed only)
}
pipeline = { id: "NfkcTrimCasefold" | "NfkcTrimUppercase" | "NfkcTrimLowercase",
             unicodeVersion: "16.0.0",
             steps: [ "reject_unassigned", ... ] }   explicit, never implied by the id
digest   = { function: "SHA-256", widthBits: positive multiple of 8, encoding: "lowercase-hex" | "base32" | "base64url" }
mac      = { function: "HMAC-SHA-256", widthBits, encoding }
```

| Strategy | Strategy-specific members |
|---|---|
| NaturalKeyIdentity | `key: { properties: [IRI…], scopeProperty: IRI \| null, pipeline }` from `dal:keyConstraint` (P6), slot `{key}` rendered per P4 |
| DerivedHashIdentity | `key`, `tuplePrefix: [string…]`, `tupleEncoding: "length-prefixed-utf8/1"`, `digest`, slot `{digest}` |
| SurrogateClaimedIdentity | `surrogate: { kind: "UuidV4Surrogate" } \| { kind: "CallerSuppliedSurrogate", pattern }`, slot `{surrogate}`, and `claims: [claimRecipe…]` (two during a `dal:Dual` rotation) |
| claimRecipe | `constraintId`, `schemeVersion`, `keyId`, `schemeState`, `key: { properties, scopeProperty \| null, pipeline }`, `tupleEncoding`, `mac`, `iriTemplate` with slots `{constraintId}`, `{schemeVersion}`, `{mac}`. MAC input: `enc([schemeVersion, constraintId, scopeValue or "", ...normalized key components])` |
| RandomSurrogateIdentity | `surrogate: { kind: "UuidV4Surrogate" }`, slot `{surrogate}` |
| PositionDerivedEvent (event strategy on any role) | `namespace: { derivation: "HashedTargetDerivation", digest } \| { derivation: "RegistryTokenDerivation" }`, `epochWidth`, `sequenceWidth`, slots `{namespace}`, `{epoch}`, `{seq}` |
| ContentAddressedIdentity | `digest`, `canonicalization: { algorithm: "RDFC-1.0", serialization: "canonical-n-quads-utf8" }`, `selfReference`, `workBudget`, `verifyFullDigest`, `callerObligations`, slot `{digest}` |
| AdoptedIdentity, ExternalRegistryIdentity | `namingAuthority`, `acceptedPattern` (validation only, never minted) |

Pipeline steps: `reject_unassigned` (always first), `nfc`, `nfkc`, `nfkc_casefold`, `trim_white_space` (the Unicode `White_Space` property, not a language's own notion), `uppercase_full`, `lowercase_full`. The three pipeline ids expand to: `NfkcTrimCasefold` = reject_unassigned, nfkc_casefold, trim_white_space; `NfkcTrimUppercase` = reject_unassigned, nfkc, trim_white_space, uppercase_full, nfkc; `NfkcTrimLowercase` = reject_unassigned, nfkc, trim_white_space, lowercase_full, nfkc.

Tuple encoding `length-prefixed-utf8/1`: for each component, the decimal count of its UTF-8 **bytes** in ASCII, `:`, then the bytes. Output encodings: `lowercase-hex`, RFC 4648 `base32` in its standard uppercase alphabet with padding removed, RFC 4648 `base64url` with padding removed. Truncation keeps the first `widthBits / 8` bytes. UUIDv4 renders lowercase, 8-4-4-4-12.

Named errors (the negative vectors use them): `UnassignedCodePoint`, `EmptyKeyComponent`, `MissingKeyComponent`, `MissingSecret`, `PatternMismatch`, `PositionOutOfRange`, `RecipeDigestMismatch`, `UnsupportedRecipeFormat`, `RuntimeUnicodeTooOld`.

## Slices

### M0 — Decisions, contracts and anchors

1. **ADR-A82**: amend point 5 in place, with a dated amendment note: "compiles them to minting recipes, conformance vectors, validation and runtime requirements. Executing a recipe is a runtime concern, served by the standalone minting libraries (ADR-A84) and by the normative specification for implementors who use neither."
2. **ADR-A84** (Proposed): standalone minting libraries. Placement `packages/minting/{java,python}`. Standalone builds with no runtime dependency beyond JDK 25 or the Python 3.14 standard library. Pinned Unicode 16.0 tables. MPL-2.0. Conformance by vectors and anchors. Recipes as the only input. The shared-core alternative recorded as deferred.
3. **Licence tracking**: `REUSE.toml` annotating `contracts/**` as MPL-2.0 (JSON files cannot carry comment headers); `README.md` Licensing and `CONTRIBUTING.md`'s licence table extended to cover `contracts/`, `packages/` and `platform/` (MPL-2.0, the last per ADR-A71).
4. **`contracts/identity/`**: `README.md`; `recipe.schema.json` and `vectors.schema.json` (JSON Schema 2020-12, following `contracts/events` conventions); `anchors.schema.json`; `anchor-vectors.json`; `verify-anchors.py` (Python standard library plus the `openssl` command line tool), which recomputes every anchor byte and reports each failure, sharing no code with the libraries.
5. **Anchor corpus**: one recipe per deterministic strategy (derived hash, claim, natural key, position-derived event, content-addressed on given bytes), plus pipeline anchors whose expected normalized strings each cite the UCD 16.0 line that justifies them (for example `FB01; NFKC_CF; 0066 0069`).
6. **Specification skeleton**: `docs/architecture/identity-minting-specification.md` with the normative sections M0 can already fix (recipe format, pipelines and steps, tuple encoding, output encodings, templates, named errors, vector format, verification procedure, caller obligations for content-addressed identity). The worked example and pitfalls are completed in M4.
7. **`mise` task** `check:minting-anchors` running `verify-anchors.py`, included in the aggregate `check` task.

Validation: the schemas validate the anchor file; `verify-anchors.py` passes with OpenSSL 3 and with LibreSSL; corrupted anchors fail it (probes).

### M1 — Vocabulary and compiler emission

1. **Vocabulary** (`ontology/persistence/spec/persistence.ttl` §12 and §11): `dal:mintedIriTemplate`, `dal:claimsConstraint`, `dal:tuplePrefix`, `dal:surrogateKind` with `dal:UuidV4Surrogate` and `dal:CallerSuppliedSurrogate`, `dal:callerSuppliedPattern`, `dal:acceptedIriPattern`, `dal:epochWidth`, `dal:sequenceWidth`, `dal:unicodeVersion` on the three pipeline individuals (all `"16.0.0"`), and on `dal:ClaimScheme`: `dal:claimKeyId`, `dal:claimDigestScheme`, `dal:claimIriTemplate`. Compiled output: `dal:MintingRecipe`, `dal:mintingRecipe`, `dal:recipeDocument`, `dal:recipeDigest`, `dal:forRole`, `dal:recipeStrategy`. The `dal:ContentAddressedIdentity` comment states the caller obligations.
2. **Shapes**: required members per strategy (template; tuple prefix and digest for derived hash; surrogate kind for claimed; pattern for caller-supplied; widths for position-derived; claim scheme completeness).
3. **Compiler**: build a recipe per resolved identity role; compute its JCS digest; emit `dal:MintingRecipe`. `dal:claimsConstraint` checks replace Slice 3's interim "at least one constraint" check (named constraint exists, applies to the same target, has a complete claim scheme). A `ContentAddressedCallerObligations` warning on every target resolving that strategy.
4. **`persistence export-recipes <compiled.ttl> --out <dir>`**: writes one JSON recipe per `dal:MintingRecipe`. Vector generation is added in M2.
5. **Fixtures and tests**: one positive fixture per strategy; negatives for each new refusal; recipe JSON validated against `contracts/identity/recipe.schema.json`; recipe digest recomputed independently in the test; determinism under triple reordering.

### M2 — Python library and vector generation

1. **`packages/minting/python`**: `pyproject.toml` with no dependencies, package `lattice_minting`: recipe parsing and digest check, the steps, tuple encoding, digest and MAC, output encodings, templates, `mint`, `trace`, `Conformance.verify`, a start-up check that the runtime's `unicodedata` is at least 16.0.0 (`RuntimeUnicodeTooOld`).
2. **Pinned tables**: a generator script fetching UCD 16.0.0 (`DerivedNormalizationProps.txt`, `UnicodeData.txt`, `SpecialCasing.txt`, `PropList.txt`, `DerivedAge.txt` or equivalent for assignment), recording source URLs and SHA-256 of each file, and emitting data modules for Python and data resources for Java from the same run.
3. **Vectors**: `export-recipes` gains vector generation, using `lattice_minting` as the reference implementation, covering the sketch's §8.2 corpus per recipe.
4. **Tests**: anchors, generated vectors, negative vectors, and a property test that every pipeline is idempotent.
5. **`mise` tasks** `bootstrap:minting-python`, `check:minting-python`.

### M3 — Java library

1. **`packages/minting/java`**: standalone `pom.xml` (not a child of `platform/pom.xml`), JDK 25, no runtime dependencies, JUnit test-scope only. Package `org.nebularis.lattice.minting`, same concepts and names as Python. Tables loaded from the resources M2 generated. A minimal JSON reader inside the library, since there is no JDK JSON API.
2. **Tests**: the same anchor and generated vector files, run through a JUnit harness, and UTF-8 byte-length tests with non-BMP input.
3. **`mise` tasks** `check:minting-java`; an aggregate `check:minting`.

### M4 — Specification completion and walk-through

1. Complete `identity-minting-specification.md`: a fully worked example per deterministic strategy with every intermediate byte, the pitfalls section (UTF-16 lengths, whitespace sets, `toLowerCase` is not case folding, NFC versus NFKC, base32 padding and case, secrets in vectors, canonicalization obligations), and "implementing without our code" as a step-by-step procedure.
2. READMEs: `packages/minting/README.md`, one per library, `contracts/identity/README.md`, each with the content-addressed obligations section before the API.
3. `iri-identity-patterns.md` §14.2 and `tools/persistence/README.md` updated.
4. **Human walk-through** (cannot be done by the agent): a person follows the specification alone, with a hex editor and an SHA-256 tool, and reproduces one derived-hash IRI and one claim IRI from the anchor file. Findings feed a final revision.

## Validation approach

Each slice has a validation pack at `docs/developer/validation/identity-minting-<slice>.md`, with positive and negative cases, the `mise` command, and at least one adversarial probe. `mise run check:persistence` stays green throughout.

## Risks

| Risk | Mitigation |
|---|---|
| Both libraries share a mistake because vectors come from one of them | Anchors verified with `openssl` and UCD citations (M0) |
| Platform NFC differs from the pinned tables for a newly assigned code point | Unicode 16.0 pinned, runtimes verified at 16.0; unassigned code points rejected; start-up version check |
| A hand-written JSON reader in Java mis-parses a recipe | Recipes are schema-restricted (P5); the reader is tested against every recipe the compiler emits, and the digest check catches any change |
| Content-addressed callers canonicalize differently | Obligations surfaced in seven places (sketch §6a); vectors labelled as already canonical |
