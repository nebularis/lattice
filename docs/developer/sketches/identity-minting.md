<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Identity Minting: Recipes, Conformance Vectors and Standalone Libraries — Sketch

**Unit ID:** `identity-minting`
**Status:** Sketch reviewed and decisions taken (2026-09-23). Promoted to [plan](../plans/identity-minting.md) and [status](../status/identity-minting.md).
**Date:** 2026-09-23
**Governing decisions:** [ADR-A82](../../architecture/decisions/ADR-A82-framework-neutral-identity-pattern-selection.md) (point 5, amended by this sketch's proposal), [ADR-A79](../../architecture/decisions/ADR-A79-persistence-compiler-toolchain.md), [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md), [ADR-A71](../../architecture/decisions/ADR-A71-platform-licence-and-spi-seam.md)
**Alternative under consideration:** [identity-minting-shared-core.md](identity-minting-shared-core.md), a shared Rust core bound into every runtime, which would replace §7 and §9 below. Deferred until `persistence-compiler-iri-sync` Slice 6 is complete, but best decided before slice M2.
**Builds on:** [`persistence-compiler-iri-sync`](../status/persistence-compiler-iri-sync.md) Slice 3 (identity profiles resolved per resource role), [iri-identity-patterns.md](../../architecture/iri-identity-patterns.md) §6–§7, §10, §14, [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md) Chapters 5, 6 and 8

---

## 1. Decisions already taken (2026-09-23)

| # | Decision |
|---|---|
| A | Minting splits three ways. The compiler produces **recipes** and **conformance vectors** at design time. **Execution** is a runtime concern. Minting never happens inside a SPARQL template. |
| B | Execution lives in **standalone minting libraries**, one for Java and one for Python, usable without any other LATTICE component. An adopter may use neither LATTICE runtime but still use a library. Publishing to Maven Central or PyPI is out of scope for now. An implementor who uses neither library must be able to reach conformance from the documentation and the vectors alone, and that documentation must be thorough. |
| C | A recipe is **fully self-contained**: a runtime needs only the recipe, never the adopter's configuration graph. |
| D | The libraries are **pure** (JDK 25 and the Python 3.14 standard library only), built as sketched in §9. The shared-core alternative ([identity-minting-shared-core.md](identity-minting-shared-core.md)) stays deferred, accepting that these libraries may be rewritten if it is adopted. |
| E | The repository moves to **JDK 25 LTS and Python 3.14** ([`toolchain-jdk25-python314`](../status/toolchain-jdk25-python314.md), done), and the tables pin **Unicode 16.0**, the version both ship. |

This sketch works out what those decisions require. §11 records how each open question was settled.

## 2. Problem

Slice 3 of `persistence-compiler-iri-sync` resolves one `dal:IdentityProfile` per resource role and records the strategy and the winning profile node in the compiled profile. That tells a runtime *which* strategy applies, not *how* to apply it. The details are spread across the adopter's graph: the uniqueness constraint's key properties and normalization pipeline, the digest scheme, the claim scheme. Two gaps make a complete recipe impossible today:

1. **Nothing says what a minted IRI looks like.** The vocabulary has no property for a minted IRI's prefix or template. `dal:iriPrefix` exists, but it belongs to `dal:NamespaceScope` and matches existing IRIs, it does not mint new ones.
2. **Nothing links a claimed identity to its key.** Slice 3's check only confirms that the target has *some* uniqueness constraint. It cannot say which one the claim is minted from.

A further gap only shows up once two languages are involved: **"the same pipeline" in Java and Python is not the same function by default.** The two languages disagree on whitespace, their Unicode versions differ, and Java has no full case folding. §7 addresses this.

## 3. Goals and non-goals

**Goals**

- A recipe per resolved identity role, emitted by the compiler, complete enough to mint or verify an IRI with no other input except the request's values and, for keyed strategies, a secret.
- A machine-readable recipe format a library can read with no RDF stack.
- Conformance vectors per deterministic recipe, including every intermediate value, plus negative vectors that must be rejected.
- A Java library and a Python library, each usable standalone, each passing the same vectors.
- A normative specification that lets anyone implement a conformant minter without our code.
- `dal:claimsConstraint`, designed properly.

**Non-goals**

- Publishing artefacts to Maven Central or PyPI.
- Minting in SPARQL, or generating minting code in other languages.
- Key management. The libraries accept a secret through a small interface and never store one.
- RDF Dataset Canonicalization (RDFC-1.0) inside the libraries, in the first cut (§11, Q6).
- Runtime alias resolution (`dal:AliasResolutionStrategy` remains a candidate term).

## 4. The three artefacts and where they live

| Artefact | Produced by | Consumed by | Location |
|---|---|---|---|
| Recipe (RDF) | `persistence compile` | anything reading the compiled profile | in the compiled profile TTL (canonical, ADR-A79 point 2) |
| Recipe (JSON) | new `persistence export-recipes` subcommand | the minting libraries and independent implementors | one JSON document per compiled profile |
| Conformance vectors | `persistence export-recipes`, using the Python minting library as its reference implementation | both libraries' test suites and independent implementors | one JSON document per recipe |
| Anchor vectors | written by hand and verified with independent tools (§8.3) | both libraries and the vector generator itself | `contracts/identity/anchor-vectors.json` |
| Recipe and vector schemas | authored with this unit | everyone | `contracts/identity/*.schema.json` |
| Minting libraries | this unit | adopters, LATTICE runtimes | `packages/minting/python`, `packages/minting/java` |
| Normative specification | this unit | independent implementors | `docs/architecture/identity-minting-specification.md` |

`compile` keeps producing TTL only. The JSON recipe is a projection of it, so it lives in a separate subcommand rather than changing `compile`'s contract.

## 5. The recipe

### 5.1 What a recipe must say, per strategy

| Strategy | Recipe content | Runtime input |
|---|---|---|
| `dal:NaturalKeyIdentity` | IRI template, key properties in order, normalization pipeline per component, component encoding | key values |
| `dal:DerivedHashIdentity` | IRI template, domain-separation label, key properties in order, pipeline, tuple encoding, digest function, width, output encoding | key values |
| `dal:SurrogateClaimedIdentity` | IRI template for the surrogate, surrogate kind (`dal:UuidV4Surrogate` or `dal:CallerSuppliedSurrogate` with its accepted pattern), **the claim recipe** (below) | key values for the claim; the surrogate itself for `dal:CallerSuppliedSurrogate` |
| claim IRI (derived from `dal:claimsConstraint` and the constraint's `dal:ClaimScheme`) | claim IRI template, constraint id, scheme version, key id (never the secret), key properties, scope property, pipeline, tuple encoding, MAC function, width, output encoding, all per scheme version | key values, scope value, secret |
| `dal:RandomSurrogateIdentity` | IRI template, surrogate kind | none (CSPRNG) |
| `dal:PositionDerivedEvent` | IRI template, occurrence-namespace derivation and its digest, epoch width, sequence width | target IRI, epoch, sequence |
| `dal:ContentAddressedIdentity` | IRI template, digest function, width, encoding, canonicalization algorithm and version, self-reference rule, and the **caller obligations** (§6a) | canonical bytes produced by the caller |
| `dal:AdoptedIdentity`, `dal:ExternalRegistryIdentity` | naming authority, accepted IRI pattern for validation | an IRI supplied by the authority, validated, never minted |

Every recipe also carries the recipe format version, the resource role, the target class and deployment, and its own **recipe digest**: SHA-256 over the recipe's canonical JSON (RFC 8785, JSON Canonicalization Scheme). Vectors name the recipe digest they were generated for, so a vector can never silently be checked against a different recipe.

### 5.2 New vocabulary (adopter-facing, `ontology/persistence` §12)

| Term | Domain | Meaning |
|---|---|---|
| `dal:mintedIriTemplate` | `dal:IdentityProfile` | the minted IRI's shape, with named slots (`{digest}`, `{surrogate}`, `{key}`, `{epoch}`, `{seq}`, `{namespace}`), for example `"urn:ex:sku:{digest}"`. Required for every strategy that mints |
| `dal:claimsConstraint` | `dal:IdentityProfile` | the `dal:UniquenessConstraint` a claimed surrogate claims, §6 |
| `dal:domainSeparationLabel` | `dal:IdentityProfile` | the fixed first tuple component of a derived hash (the guide's `"iri"`), so two recipes sharing a key never share a digest |
| `dal:claimKeyId` | `dal:ClaimScheme` | an opaque identifier of the secret a scheme version uses, resolved by the runtime's secret provider. Never the secret itself |
| `dal:claimDigestScheme` | `dal:ClaimScheme` | the `dal:DigestScheme` (MAC function, width, encoding) of this scheme version. Changing it is a rotation (Q4) |
| `dal:claimIriTemplate` | `dal:ClaimScheme` | the claim IRI's shape, for example `"urn:key:{constraint}:{version}:{mac}"`. On the scheme, so every byte of a claim IRI changes only through rotation |
| `dal:surrogateKind` | `dal:IdentityProfile` | `dal:UuidV4Surrogate` or `dal:CallerSuppliedSurrogate` (Q5). Required with `dal:SurrogateClaimedIdentity` |
| `dal:callerSuppliedPattern` | `dal:IdentityProfile` | the pattern a caller-supplied surrogate must match. Required with `dal:CallerSuppliedSurrogate` |
| `dal:unicodeVersion` | the normalization pipeline individuals | the Unicode version the pipeline's tables are generated from, §7 |

### 5.3 New vocabulary (compiled output, `ontology/persistence` §11)

A `dal:MintingRecipe` node per resolved role, linked from the compiled profile by `dal:mintingRecipe`, carrying the fields in §5.1 as properties, plus `dal:recipeDigest` and `dal:recipeFormatVersion`. This keeps the TTL canonical and complete, as decision C requires. The JSON recipe is generated from these nodes and nothing else.

## 6. `dal:claimsConstraint`

**Shape.** `dal:claimsConstraint` links a `dal:IdentityProfile` to one `dal:UniquenessConstraint`. It is required, exactly once, when `dal:identityStrategy` is `dal:SurrogateClaimedIdentity`, and forbidden otherwise.

**What it replaces.** Slice 3's check "the target has at least one uniqueness constraint" becomes "the named constraint exists, applies to the same target after resolution, and is not `dal:Merge` without a `dal:mergeRelation`". A claimed profile naming a constraint that does not apply to its target is refused at compile time, because the claim would be minted from a key the entity does not carry.

**Where the claim recipe comes from.** The claim IRI is minted from the constraint's `dal:constraintId`, `dal:keyProperty` list, `dal:scopeProperty` and `dal:normalizePipeline`, together with the constraint's `dal:claimScheme`: its version, `dal:claimKeyId`, `dal:claimDigestScheme` and `dal:claimIriTemplate`. Everything that determines a claim IRI's bytes sits on the scheme version, so none of it can change except through rotation (Q4). A claimed constraint with no scheme, or a scheme missing any of these, is refused: a claim with no declared width is exactly the "at least N bits" ambiguity the vocabulary forbids. `dal:KeyClaimRole` identity profiles play no part in claimed identity.

**More than one constraint.** A class may have several unique keys (email and national id, say). Only one can be the claim that identity is minted from, so `dal:claimsConstraint` names exactly one. The other constraints remain ordinary uniqueness claims with no identity role.

**Rotation.** During a `dal:Dual` scheme state the recipe carries both scheme versions, and the libraries mint both claim IRIs, matching guide §6.1 and `iri-identity-patterns.md` §6.4.

## 6a. Content-addressed identity: what the caller must do (Q6)

The libraries hash canonical bytes the caller supplies. They do not canonicalize RDF. That leaves the most important correctness property with the caller: two callers with different canonicalizers mint different IRIs for the same graph, and no vector can catch it. So the caller obligations are stated everywhere a user can meet this strategy, not only in the specification:

1. The bytes are the output of an RDFC-1.0 implementation that passes the W3C RDFC-1.0 test suite, serialized as canonical N-Quads, UTF-8, with the exact trailing-newline convention the specification states.
2. The self-reference placeholder rule named in the recipe is applied **before** canonicalization (`iri-identity-patterns.md` §8.3).
3. The canonicalization work budget named in the recipe is enforced, and exceeding it is a refusal, never a best-effort hash (§8.4).
4. Where full-digest verification is declared, the full digest is stored and compared on re-registration (§8.5).

Where each obligation is surfaced:

| Place | How |
|---|---|
| Recipe (TTL and JSON) | a `callerObligations` list with stable identifiers, so every consumer of a content-addressed recipe receives them with it |
| Library API | the content-addressed entry point takes canonical bytes together with an explicit statement of which canonicalizer produced them, recorded in the trace. There is no overload that takes an RDF graph |
| Library READMEs | a dedicated section, before the API reference |
| Specification | a normative section, with the reason each obligation exists and how to test for it |
| Vectors | canonical N-Quads inputs, labelled as already canonical, so no one mistakes the vectors for a canonicalization test |
| Vocabulary | the `dal:ContentAddressedIdentity` comment states the obligations |
| Compiler | a `ContentAddressedCallerObligations` warning on every target that resolves this strategy, so the obligation appears in the compile output too |

## 7. Making one pipeline mean one function in two languages

This is the hardest part of the unit. The guide already says a pipeline is identified by its implementation, not its description (§8.1). With two languages that rule has teeth:

| Step | Java | Python | Risk |
|---|---|---|---|
| NFKC_Casefold | no JDK support; ICU4J only | `unicodedata` has no NFKC_Casefold; PyICU needs a native ICU build | no portable built-in |
| full case folding | none (`toLowerCase` is not case folding) | `str.casefold()` | Java cannot match without tables |
| upper-case mapping | `toUpperCase(Locale.ROOT)` | `str.upper()` | both follow SpecialCasing, but each tied to its runtime's Unicode version |
| trim | `String.strip()` uses `Character.isWhitespace` | `str.strip()` uses Python's whitespace set | **the two sets differ** |
| NFC | `java.text.Normalizer` | `unicodedata.normalize` | stable for assigned code points across Unicode versions |
| byte length for tuple encoding | `String.length()` counts UTF-16 units | `len(str)` counts code points | both wrong: the encoding needs UTF-8 bytes |

**Decision (Q1, Q2).** Every Unicode-dependent step except NFC uses **tables generated from one pinned Unicode Character Database version**, checked into the repository with the UCD version and a digest of the source files:

- the `NFKC_Casefold` mapping from `DerivedNormalizationProps.txt`
- simple and full case mappings from `UnicodeData.txt` and `SpecialCasing.txt`, for the upper and lower pipelines
- the whitespace set for trimming, defined as the `White_Space` property from `PropList.txt`, not either language's built-in notion
- the set of code points assigned in the pinned version, **Unicode 16.0**

NFC relies on Unicode's normalization stability policy: once a character is assigned, its normalization never changes. That makes each platform's built-in NFC safe for code points assigned in the pinned version. So both libraries **reject any input containing a code point unassigned in the pinned version**, with a named error that a negative vector tests. The recipe names the pipeline and its Unicode version. Changing the version is a new pipeline version and therefore a re-key, never a silent upgrade.

This makes both libraries pure: the Java library needs only the JDK, and the Python library only the standard library. That meets decision B's "easy to use standalone" with no native dependencies. An independent implementor can use the same published tables, or their own data from the same UCD version.

## 8. Conformance vectors

### 8.1 Format

One JSON document per recipe, validated by `contracts/identity/vectors.schema.json`:

- the recipe digest it applies to, and the recipe itself, embedded, so the file is self-contained
- the test secret for keyed recipes: a published constant, named in the file, never a production secret
- **positive vectors**, each giving the raw inputs and **every intermediate value**: each component after normalization, the tuple-encoding bytes in hex, the digest or MAC bytes in hex, the encoded digest, and the final IRI
- **negative vectors**, each giving raw inputs and the named error an implementation must raise (for example `UnassignedCodePoint`, `EmptyKeyComponent`, `NonAsciiDomain`)
- **format vectors** for non-deterministic strategies (random surrogates, adopted and external identifiers): a pattern the minted or supplied IRI must match, plus examples that must be rejected

Intermediate values are what make the vectors usable by someone without our code: an implementor whose final IRI differs can find the first step where they diverge.

### 8.2 Corpus

Generated per recipe, with every category that applies to it: plain ASCII, case variants, NFC versus NFD, compatibility forms (full-width, ligatures), default-ignorable code points (zero-width space, soft hyphen, variation selectors), `ß`, non-BMP characters (which trip UTF-16 length bugs), whitespace from both languages' disagreement set, confusables (which must **not** merge), internationalized domains where the pipeline covers them, empty and whitespace-only components (negative), unassigned code points (negative), component values containing the tuple separator characters, and the longest component the recipe allows.

### 8.3 Anchor vectors: guarding against a self-consistent mistake

Vectors generated by the Python library can only prove that Java agrees with Python. If the Python library is wrong, both libraries pass and both are wrong. So a small **anchor set** is written by hand and verified with tools that share no code with ours: documented `printf … | openssl dgst -sha256 -mac HMAC …` commands, and base32 and hex by an independent encoder. It covers one vector per strategy and at least one per risky category in §7. The vector generator, both libraries and the anchor file's own verification script must all agree. The anchor file is the one place a human checks bytes by eye.

### 8.4 Verifying without our code

The specification (§10) walks through verification step by step, with no LATTICE code involved: read the vector file, check the recipe digest against the recipe you implemented, run every positive vector and compare **each intermediate value in order**, run every negative vector and confirm the named rejection, run the format vectors, and report conformance as "recipe digest *d*, vectors file digest *v*, all passed". It also explains what to do when an intermediate value differs, grouped by step.

## 9. The libraries

### 9.1 Placement and build

`packages/minting/python` and `packages/minting/java`, under the `packages/` root that ADR-A77 already reserves. Each is buildable on its own: a `pyproject.toml` with no runtime dependencies, and a standalone Maven `pom.xml` (not a child of `platform/pom.xml`) needing only JDK 21. Both are MPL-2.0, like all other code in the repository (ADR-A71), which lets an adopter embed them in a proprietary system. `mise` tasks `bootstrap:minting` and `check:minting` build and test both, and run the anchor and generated vectors. A placement ADR is required by ADR-A77 before the directories are created (§12).

### 9.2 API shape (illustrative, same concepts in both languages)

```text
Recipe      = Recipe.parse(json)                  // validates schema and recipe digest
Minter      = Minter.forRecipe(recipe, secrets)   // secrets: KeyId -> bytes, only for keyed recipes
Minted      = minter.mint(inputs)                 // IRI plus, for claimed identity, the claim IRI(s)
Trace       = minter.trace(inputs)                // every intermediate value, as in the vectors
Report      = Conformance.verify(vectorsJson)     // runs a vector file against this library
```

`trace` exists so that a library user debugging an IRI mismatch sees the same intermediate values the vectors publish. The secret interface is deliberately minimal. A LATTICE runtime adapts ADR-A71's `SecretProvider` to it, and a standalone user passes bytes.

### 9.3 Relationship to LATTICE runtimes

The ingestion gateway's `mint` step (epic P2.1.5, P2.3.1) uses the Java library, and Python workers use the Python library. Neither re-implements minting. `tools/persistence` uses the Python library at design time to generate vectors, which is a build-time dependency and does not change ADR-A79's design-time-only rule.

## 10. Documentation

| Document | Audience | Content |
|---|---|---|
| `docs/architecture/identity-minting-specification.md` | anyone implementing a minter, including without our code | normative: recipe fields one by one, the algorithm for each strategy at byte level, the pinned tables and how to obtain or regenerate them, tuple encoding, digest and MAC output encodings (base32 alphabet, case, no padding), the vector format, the step-by-step verification procedure of §8.4, a fully worked example with every intermediate byte, and a pitfalls section (UTF-16 lengths, whitespace sets, `toLowerCase` is not case folding, NFC versus NFKC, base32 padding, secrets in vectors) |
| `packages/minting/README.md` | library users | when to use a library versus the specification, and the conformance promise |
| `packages/minting/python/README.md`, `packages/minting/java/README.md` | library users | install from source, API, secrets, running the vectors |
| `contracts/identity/README.md` | everyone | the schemas and the anchor vectors |
| `iri-identity-patterns.md` §14.2 | architects | updated to say where each compilation responsibility now lives |
| `tools/persistence/README.md` | compiler users | `export-recipes` |

The specification is written so that the worked example alone lets an implementor reproduce one IRI with a hex editor and a SHA-256 tool.

## 11. Questions and how they were settled (2026-09-23)

| # | Question | Decision |
|---|---|---|
| Q1 | Normalization: pinned tables or ICU? | Pinned tables generated from the UCD, with platform NFC and rejection of unassigned code points (§7) |
| Q2 | Which Unicode version? | 16.0, after moving to JDK 25 LTS and Python 3.14 (decision E) |
| Q3 | Where do the schemas and anchor vectors live? | `contracts/identity/`, MPL-2.0, with licence tracking for `contracts/` added to the repository licensing section |
| Q4 | Where do the claim MAC's width and encoding come from? | `dal:ClaimScheme`, through `dal:claimDigestScheme`, so a change is a rotation. The claim IRI template sits there too (agent decision, same reason) |
| Q5 | What surrogate does a claimed identity use? | `dal:surrogateKind`: `dal:UuidV4Surrogate` or `dal:CallerSuppliedSurrogate`. UUIDv7 deferred |
| Q6 | Content-addressed identity: canonicalize in the libraries? | No. The caller supplies canonical bytes, and the obligations are surfaced everywhere a user can meet them (§6a) |
| Q7 | Amend ADR-A82 point 5 in place? | Yes, with a dated amendment note |

## 12. ADRs

- **ADR-A82 amendment (point 5).** From "compiles them to minting, validation, conformance fixtures, and runtime requirements" to "compiles them to minting recipes, conformance vectors, validation and runtime requirements. Executing a recipe is a runtime concern, served by standalone minting libraries and by the normative specification for anyone who uses neither."
- **ADR-A84: Standalone minting libraries.** Placement under `packages/minting/`, the standalone-build and no-runtime-dependency rules, JDK 25 and Python 3.14 as the floor, the pinned Unicode 16.0 tables, MPL-2.0, and conformance by vectors. (A81's double claim was resolved on 2026-09-23 by renumbering the eligibility plan's ADR to A83.)

## 13. Proposed slicing (for the plan)

| Slice | Scope | Depends on |
|---|---|---|
| M0 | ADR-A82 amendment, ADR-A84, the normative specification's skeleton, recipe and vector JSON schemas, anchor vectors verified with independent tools | decisions in §11 |
| M1 | Vocabulary (§5.2, §5.3, §6), compiler emission of `dal:MintingRecipe`, `dal:claimsConstraint` checks replacing Slice 3's interim check, `export-recipes` producing JSON recipes | M0 |
| M2 | Pinned Unicode tables and their generator, the Python library, vector generation in `export-recipes` using it | M0, M1 |
| M3 | The Java library, passing the anchor and generated vectors | M2 |
| M4 | The full specification, library READMEs, the worked example, and an independent walk-through: a human follows the specification alone to reproduce one vector | M2, M3 |

This is a new unit rather than a slice of `persistence-compiler-iri-sync`: it creates new packages and contracts, and it has its own ADR. `persistence-compiler-iri-sync` Slices 4–6 do not depend on it and can proceed in parallel. Slice 6's close-out should note that identity recipes moved here.
