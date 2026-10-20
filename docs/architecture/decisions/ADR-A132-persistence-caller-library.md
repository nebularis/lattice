<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A132: A caller library for the generated persistence operations

**Status:** Proposed, 2026-10-20
**Date:** 2026-10-20
**Supersedes:** none
**Related:** [ADR-A123](ADR-A123-typed-operation-ir.md) (the typed IR, its contract and its addenda),
[ADR-A122](ADR-A122-aggregate-ownership.md) (the payload check),
[ADR-A84](ADR-A84-standalone-minting-libraries.md) (the precedent for libraries under `packages/`),
[ADR-A77](ADR-A77-repository-topology-and-documentation-governance.md) (the `packages/` root),
[ADR-A79](ADR-A79-persistence-compiler-toolchain.md) (the injection boundary),
[ADR-A71](ADR-A71-platform-licence-and-spi-seam.md) (MPL-2.0 for embeddable code),
[ADR-A29](ADR-A29-repository-toolchain-and-environment-boundary.md) (`mise`)

## Context

The persistence compiler turns a compiled profile into guarded SPARQL operations. A caller runs them with values the store cannot
check. The payload is ground triples placed in an update, the request digest is hashed over those triples and other parts, the
parameters have declared kinds, and `logGraphs` names the graphs an audit reads. A caller that gets one of these wrong writes
data outside the aggregate, computes a digest no other caller reproduces, or runs an audit that examines nothing and reports
clean.

Today the code for these steps sits in `tools/persistence`, a design-time toolchain. An adopter on another runtime, or one that
does not want the compiler and its dependencies, has to rewrite each step from the README. The Control Plane (Java) and the
workers (Python) will each need the same steps, and a payload text that is built differently in each can change a guard, not only
the data written, because the event rows sit in an update's `WHERE`.

ADR-A123 fixes what the generated operations expect. It leaves the caller's half open: the typed `Payload` and `Rows`, the digest
(declared in its fifth addendum, computed by nothing), the payload checks, the caller check and the audit outcome.

## Decision

1. **Location.** The caller library lives under `packages/persistence/python`. Java follows as a sibling,
   `packages/persistence/java`, when a Java caller needs it, as `packages/minting` does. It is a library meant to be embedded, so
   it belongs neither in `tools/` nor in `platform/` (ADR-A84 decision 1).
2. **Shape.** The library is a runtime library with nothing generated per profile (option S-A). It reads a compiled profile (RDF)
   at start-up and offers the following.
   - **The typed `Payload`.** Ground triples, each term a typed value, rendered as sorted canonical N-Triples with no blank node.
     One type serves every payload slot. A typed `Rows` type does the same for the event rows.
   - **The digest.** Computed from the digest contract, one part per slot in the contract's order, each part the sorted canonical
     N-Triples of its slot. Conformance vectors for it live in `contracts/persistence/`.
   - **The payload checks.** For a payload, every subject is the root or is reached from it by the owned path. For events, every
     subject is an event of the batch or a node minted under one event's IRI, so an event may link to an aggregate and never
     describe it. Deployment shapes, where a deployment declares them, tighten either check and are optional.
   - **The caller check.** Every declared parameter is present and of its kind. An `xsd:long` is exactly `xsd:long`, on any store,
     and an ill-typed literal that keeps its datatype is refused. `logGraphs` is non-empty and holds IRIs.
   - **The audit outcome.** Three values: clean, failed and nothing examined. An audit over no graph reports the third, never
     clean.
3. **Dependencies.** The Python library depends on the Python standard library and rdflib only. `tools/persistence` depends on
   the library for the shared types (the terms, the `Payload` and `Rows` types, the contract's data classes the library reads),
   and the library never depends on `tools/persistence`. The SPARQL client is the adopter's, behind a minimal interface the
   library defines and does not implement.
4. **Conformance is by vectors, not by our code.** The vectors in `contracts/persistence/` cover the canonical N-Triples, the
   digest, the payload checks and the caller check and the audit outcome. They are verified with independent tools, as
   `contracts/identity/` is (ADR-A84 decision 5). An implementation written from the specification alone is conformant on the
   same terms.
5. **Licence and publishing.** The library is MPL-2.0 (ADR-A71). The vectors and schemas are annotated in `REUSE.toml`. Publishing
   to PyPI is out of scope until decided separately.
6. **What it is not.** It makes no store call of its own. It does not generate bindings per language (option S-B, later). It is not
   extracted from proofs (option S-D, later). Either later option replaces the library's internals or adds to it, and neither
   changes the contract in decision 4.

## Options considered

| Option | Consequences |
|---|---|
| **S-A, a runtime library, nothing generated (chosen)** | Small to build. Needs no regeneration step in an adopter's build. A misspelt parameter is a run-time error, which the caller check reports with the operation and parameter named. One implementation per language, kept in step by the vectors |
| **S-B, S-A plus generated bindings** | A typed function and payload builder per profile, so a misspelt parameter fails at compile time in the caller's language. An adopter must run the generator on every profile or shape change. It needs S-A beneath it, so S-A is not wasted, and it is chosen later where an adopter asks |
| **S-D, the core extracted from proofs** | The strongest assurance for the outcome and payload-check parts. It covers two languages through code export, the rest would still be S-A or S-B, and it waits for the outcome theory. It is later, and the vectors are what it would be checked against |
| **Keep the code in `tools/persistence`** | No new root, no new contract. An adopter takes the compiler, its templates and its dependencies to reach a payload type. The Java side gets no shared source, only a README to follow. A toolchain's internal API becomes an embedded library's contract without being declared one |

## Consequences

- `packages/persistence/` is a new directory below an existing root (ADR-A77 decision 4). It needs a `README.md`, a `pyproject.toml`
  of its own and `mise` tasks to build and test it (ADR-A29).
- `contracts/persistence/` becomes a public contract, MPL-2.0, tracked through `REUSE.toml`.
- Payload and digest code is written once in Python. Java gets it later and is held to the same vectors.
- `tools/persistence` imports the library for the shared types, so a change to those types is a change to a library with a public
  contract. The library's version and the vectors' version move together.
- The `INFO` diagnostic the compiler gains for a profile whose guards are off is the compiler's, and is not part of this library.
- A caller who skips the library is still checked by the store's guards. The library adds the checks the store cannot make, and
  does not replace the guards.
- A payload remains trusted text relative to ADR-A79's injection boundary. The library narrows the risk by building the slot's
  text from typed terms only, and a caller that bypasses `Payload` leaves that boundary.

## Provenance

Raised in the Track H plan's slice H2.8, where the maintainer decided on 2026-10-20 that the caller-side code is usable library
code under `packages/` with its own ADR (H2.8-Q1 (b)), that an event's triples are bounded by the event's own IRI space
(H2.8-Q2 (c)), and that an audit over no graph reports "nothing examined" (H2.8-Q3 (c)). The options are those of the
[client SDK sketch](../../developer/sketches/persistence-client-sdk.md), and the slice is in
[the Track H plan, section 4.8](../../developer/plans/formal-methods-track-h.md#48-h28-the-typed-payload-and-the-caller-side-checks-planned-2026-10-14).
The IR slots, digest parts and payload contract are in the
[typed IR sketch](../../developer/sketches/formal-methods-track-h-typed-ir.md).
