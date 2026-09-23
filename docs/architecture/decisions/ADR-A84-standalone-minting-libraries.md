<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A84: Standalone Minting Libraries

**Status:** Proposed
**Date:** 2026-09-23
**Supersedes:** none
**Related:** [ADR-A82](ADR-A82-framework-neutral-identity-pattern-selection.md) (point 5, as amended), ADR-A77, ADR-A79, ADR-A71, ADR-A29, [identity minting specification](../identity-minting-specification.md), [iri-identity-patterns.md](../iri-identity-patterns.md)
**Drafted by:** Agent, following decisions taken with the human while scoping the `identity-minting` unit ([sketch](../../developer/sketches/identity-minting.md), [plan](../../developer/plans/identity-minting.md)). Pending human ratification.

## Context

ADR-A82, as amended, has the persistence compiler produce minting recipes and conformance vectors, and leaves executing a recipe to runtime code. That code runs in more than one language: the Control Plane is Java, the workers are Python, and other runtimes are expected. An adopter may use neither LATTICE runtime and still want to mint identifiers exactly as LATTICE would. Every implementation must produce byte-identical IRIs for the same recipe and input, or one key gets two identities.

Two languages disagree by default on the operations minting depends on. Java has no NFKC_Casefold and no full case folding. The two languages define whitespace differently. Java measures strings in UTF-16 units. Each runtime ships its own Unicode version.

## Decision

1. **Minting libraries live under `packages/minting/`**: `packages/minting/python` and `packages/minting/java`. `packages/` is a top-level root that ADR-A77 already reserves. They are libraries meant to be embedded, so they belong neither in `tools/` (design-time toolchains) nor in `platform/` (the LATTICE runtime).
2. **Each library builds and runs standalone.** The Python library depends only on the Python 3.14 standard library, and the Java library only on JDK 25, with test-scope dependencies alone. The Java library has its own `pom.xml`, not a child of `platform/pom.xml`. No native code, no network access and no other LATTICE component is needed at build or run time. `mise` tasks build and test both (ADR-A29).
3. **Recipes are the only configuration input.** A library reads a recipe document (`contracts/identity/recipe.schema.json`), verifies its digest, and mints from it. It never reads the adopter's configuration graph.
4. **Unicode behaviour comes from pinned tables, not from the runtime.** Every Unicode-dependent step except NFC uses tables generated from the Unicode Character Database, version 16.0.0, recorded with the source files' digests. NFC uses the runtime's implementation, which is safe because Unicode's normalization stability policy fixes the normalization of assigned code points. Both libraries reject code points unassigned in 16.0.0, and refuse to start on a runtime whose Unicode data is older than 16.0.0. Moving to a newer Unicode version is a new pipeline version, and so a re-key.
5. **Conformance is defined by vectors, not by our code.** Both libraries must pass the anchor vectors in `contracts/identity/anchor-vectors.json`, which are verified with independent tools, and the vectors the compiler generates per recipe. An implementation written from the specification alone is conformant on exactly the same terms.
6. **Secrets never enter a recipe or a library's state.** A recipe names a key identifier. The caller supplies the key's bytes per call, through a minimal interface. A LATTICE runtime adapts ADR-A71's `SecretProvider` to it.
7. **The libraries are MPL-2.0** (ADR-A71), so adopters can embed them in proprietary systems. Publishing to Maven Central or PyPI is out of scope until decided separately.

## Consequences

- The repository moves to JDK 25 LTS and Python 3.14, which both ship Unicode 16.0 (done: `toolchain-jdk25-python314`).
- Minting logic exists twice, in Java and Python, kept in step by the vectors. A single shared engine is recorded as a deferred alternative ([identity-minting-shared-core.md](../../developer/sketches/identity-minting-shared-core.md)). Adopting it would replace both libraries' internals, not their contract.
- The Java library needs a small, schema-restricted JSON reader, because the JDK has none.
- `contracts/identity/` becomes a public contract. Its schemas, anchor vectors and verification script are MPL-2.0, tracked through `REUSE.toml`, because JSON cannot carry a licence header.
- Content-addressed identity takes canonical bytes from the caller. The libraries do not canonicalize RDF. The caller's obligations are stated in the specification, the recipe, the library APIs and documentation, and the compiler's output.
