<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# lattice-minting (Java)

Mints IRIs from a LATTICE minting recipe, as the [identity minting specification](../../../docs/architecture/identity-minting-specification.md) defines. JDK 25 or later, no runtime dependencies, Unicode 16.0.0. Package `org.nebularis.lattice.minting`, with the same concepts and names as the [Python library](../python/README.md).

It is not published to a Maven repository, and it is not a module of `platform/pom.xml`. Build and install it from this directory:

```bash
mvn -f packages/minting/java/pom.xml install
```

## Minting

```java
Recipe recipe = Recipe.parse(Files.readString(Path.of("Product-EntityRole-38ce5a73f929.recipe.json")));
Minter minter = new Minter(recipe);
Minted minted = minter.mint(Map.of("key", List.of(" Widget-9 ")));
minted.iri();    // urn:ex:sku:XARXQP2R47P6MPFLTVC422KYQSO6EFWM
minted.trace();  // every intermediate value, in the vectors' trace format
```

`Recipe.parse` verifies the recipe's format, digest and Unicode version before anything is minted. The request's inputs are the members listed in [§6 of the specification](../../../docs/architecture/identity-minting-specification.md#6-strategies): strings, lists of strings, and `Long` for `epoch` and `seq`. A refusal throws `MintException`, whose `kind()` is one of the `MintError` constants named in §9:

```java
try {
    minter.mint(Map.of("key", List.of("   ")));
} catch (MintException e) {
    e.kind();    // MintError.EmptyKeyComponent
}
```

### Claimed identity

Pass the claim secrets as bytes, keyed by the recipe's `keyId`. The minter copies them at construction, and never returns, logs or persists them. Fetching and rotating secrets is yours to do ([§8](../../../docs/architecture/identity-minting-specification.md#8-secrets)).

```java
Minter minter = new Minter(recipe, Map.of("example-key-v1", secretBytes));
Minted minted = minter.mint(Map.of("key", List.of("Ada@Example.org"), "scope", "acme",
        "surrogate", "8f2c1b7e-3e4a-4f7c-9a6d-2b1e0c5d7f90"));
minted.iri();
minted.claimIris();
```

### Content-addressed identity

> **The minter hashes the bytes you give it. It does not canonicalize RDF.** You must meet the caller's obligations CA-1 to CA-4 in [§7 of the specification](../../../docs/architecture/identity-minting-specification.md#7-content-addressed-identity-the-callers-obligations): a conformant RDFC-1.0 implementation, the self-reference rule applied first, the work budget enforced, and the full digest verified where the recipe says so. Two callers who canonicalize differently mint different IRIs, and nothing here can detect it.

The request must name its canonicalizer, or the minter refuses with `CanonicalizerNotDeclared`:

```java
minter.mint(Map.of("canonicalNQuads", nquads, "canonicalizer", "your RDFC-1.0 implementation and version"));
```

### Random surrogates

`new Minter(recipe)` uses `SecureRandom`. The `randomHex` input and the `IntFunction<byte[]>` constructor argument exist so that vectors and tests can fix the randomness. Never use either in production.

## What this library does not borrow from the JDK

The JDK's own Unicode handling differs from the specification in ways that change IRIs, so the library does not use it for anything but NFC and NFKC:

| JDK behaviour | Why the library avoids it |
|---|---|
| `String.length()` counts UTF-16 code units | the tuple encoding counts UTF-8 bytes |
| `String.strip()` and `Character.isWhitespace` | they exclude U+00A0, U+2007, U+202F and U+0085, which are `White_Space`, and include U+001C–U+001F, which are not |
| `String.toLowerCase` and `toUpperCase` | locale-sensitive unless given `Locale.ROOT`, and tied to the JDK's Unicode version |
| no NFKC_Casefold | `nfkc_casefold` reads the pinned `NFKC_CF` table |

Case mapping, whitespace and assignment come from the tables in `src/main/resources/org/nebularis/lattice/minting/ucd/16.0.0`, identical to the Python library's. The runtime check refuses a JDK whose Unicode data predates 16.0 (it tests whether U+1C89, first assigned in 16.0, is defined), because NFC and NFKC come from `java.text.Normalizer`. JDK 24 was the first release on Unicode 16.0.

The JDK has no JSON API, so the library carries a small reader (`Json`) restricted to what recipes and vectors contain: integers only, unique member names, well-formed strings.

## Conformance

```bash
java -jar packages/minting/java/target/lattice-minting-0.1.0-SNAPSHOT.jar verify contracts/identity/anchor-vectors.json packages/minting/testdata/*.vectors.json
```

Or from Java, `Conformance.verify(path)` returns a report with `passed()` and `failures()`. Each failure names the first trace step that differs.

## Tests

```bash
mise run check:minting-java
```

The suite runs the anchors and every generated vectors file, cross-checks the tables over all code points against the JDK where the two define the same thing, checks the idempotence of all three pipelines, UTF-8 byte counting with non-BMP input, the JSON reader's restrictions, and every refusal.

## Licence

MPL-2.0. The Unicode tables are derived from the Unicode Character Database under the [Unicode License v3](https://www.unicode.org/license.txt).
