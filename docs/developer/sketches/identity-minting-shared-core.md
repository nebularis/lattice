<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Identity Minting: A Shared Rust Core — Sketch

**Unit ID:** `identity-minting-shared-core`
**Status:** Sketch, deferred. Lower priority than completing [`persistence-compiler-iri-sync`](../status/persistence-compiler-iri-sync.md) through Slice 6. Not to be planned before then.
**Date:** 2026-09-23
**Alternative to:** §7 and §9 of [identity-minting.md](identity-minting.md), which propose separate pure-Java and pure-Python minters. If this sketch is adopted, it replaces those sections. Everything else in that sketch (recipes, `dal:claimsConstraint`, vectors, anchor vectors, the normative specification) stands unchanged.

---

## 1. Why

LATTICE will add runtimes: Erlang and Elixir already exist in `tools/spc`, and an F# project (`MorkSharp`) is expected. Under [identity-minting.md](identity-minting.md), every runtime reimplements the minting engine: pinned Unicode tables, trimming, case mapping, tuple encoding, digests and MACs, output encodings, and the trace of intermediate values. That is one to two thousand lines of careful code per language. It also carries the risk the conformance vectors exist to catch, two languages disagreeing on one input (§7 of that sketch). Two languages make that affordable. Five do not.

A single minting engine in Rust, bound into each runtime, solves the hardest part once.

## 2. Proposal

1. **One Rust core** holds the whole minting engine: recipe parsing and digest checking, the pinned Unicode tables, normalization, tuple encoding, digests and MACs, output encodings, the trace, and vector generation and verification. Its interface is deliberately plain: a recipe (JSON) and inputs in, an IRI and a trace out, with named errors.
2. **Delivered as WebAssembly by default.** The core compiles once to a `wasm32` module, hosted in each language by that ecosystem's published WebAssembly runtime.
3. **Native bindings as a later option, per language,** only where profiling shows WebAssembly overhead matters. The same core and interface serve both.
4. **A command-line tool from the same core** (`lattice-mint`), for verifying vectors and batch minting. It gives every language, including ones never bound, a zero-interop route. `tools/persistence export-recipes` calls it to generate vectors, so the vector generator and every minter are one implementation.

## 3. Why WebAssembly first

| | Native bindings | WebAssembly |
|---|---|---|
| Build from source needs | Rust plus a system linker (Xcode CLT, `gcc`, or MSVC Build Tools), per OS and architecture | Rust only: the `wasm32` target uses Rust's bundled linker. One artefact for every OS |
| Java | JNI on JDK 21 (the Foreign Function API is final only from JDK 22). A core bug can crash the JVM | Chicory, a pure-Java runtime: the library stays a plain jar |
| Python | PyO3 and maturin, mature | `wasmtime-py`, prebuilt wheels |
| Erlang / Elixir | Rustler NIFs. Native code runs inside the VM, so calls must stay short or use dirty schedulers | Wasmex (Elixir), callable from Erlang |
| F# / .NET | P/Invoke over a C ABI | `wasmtime-dotnet` |
| Failure isolation | a core bug can take down the host process | sandboxed: a core bug is an error, not a crash |
| Cost of publishing prebuilt artefacts later | a build matrix of OS × architecture × language | one `.wasm` file |
| Per-call overhead | lowest | small, irrelevant at minting's call rates |

The repository's toolchain manager already covers what this needs: `mise` has `rust` and `maturin` as registry tools, and `erlang`, `elixir` and `dotnet` as core tools. A `rust-toolchain.toml` pins the compiler. No Makefile is involved: Cargo drives the build, and `mise` tasks wrap it, as ADR-A29 requires.

## 4. What changes relative to identity-minting.md

| Area | Change |
|---|---|
| Decision B | "No runtime dependencies" becomes "no native dependencies": each language depends on its ecosystem's published WebAssembly runtime |
| §7 (one pipeline, one function) | Solved once, in Rust. The pinned tables are generated there, or taken from ICU4X, the Rust-native ICU. Host Unicode versions stop mattering, so Q2's dependency on Python 3.11's Unicode 14.0 disappears |
| §8 (vectors) | Cross-language agreement comes for free. Vectors now guard each binding's glue (string conversion bugs live there) and serve independent implementors. The **anchor vectors** become the only check that shares no code with the engine, so they matter more |
| §9 (libraries) | `packages/minting/core` (Rust crate and CLI), plus thin per-language packages (`java`, `python`, later `elixir`, `dotnet`), each a few hundred lines of glue and one CI job that runs the vectors |
| §12 (ADRs) | The placement ADR widens to bring Rust into the toolchain under ADR-A29 |
| Independent implementors | Unchanged: the specification and vectors alone still suffice, and anyone may reject our code |

## 5. Costs, stated plainly

- **Rust enters the repository.** A new toolchain, a new language for reviewers, and an ADR.
- **Glue discipline.** Strings cross the boundary as UTF-8 bytes. Results come back as structured data. Every binding needs care at exactly the place the vectors now guard.
- **A runtime dependency per language.** Chicory, `wasmtime-py`, Wasmex and `wasmtime-dotnet` are third-party projects. Their licences need the same compatibility check as any dependency, against MPL-2.0 distribution.
- **One more build step for from-source users.** Building the `.wasm` needs Rust, once, on any OS.

Against those: each new runtime costs glue and a CI job, not a reimplementation of §7, and every minter is the same engine.

## 6. Questions needing a human decision (when this is picked up)

| # | Question | Recommendation |
|---|---|---|
| R1 | WebAssembly first, or native first? | WebAssembly first, native per language only on measured need |
| R2 | Which languages in the first cut? | Java and Python. Erlang/Elixir and F# as later slices |
| R3 | Stay on JDK 21, or move to JDK 25 LTS? | Irrelevant under WebAssembly (Chicory runs on 21). It matters only if a native Java binding is ever needed, where 22+ gives the Foreign Function API |
| R4 | Pinned tables: generated in Rust from the UCD, or ICU4X? | Evaluate ICU4X's NFKC_Casefold and case-mapping coverage first. Generated tables if it falls short |
| R5 | Licence check of the four WebAssembly runtimes | Required before planning. Chicory and Wasmtime are Apache-2.0, which should be compatible, but this must be verified, not assumed |

## 7. Sequencing

Deferred until `persistence-compiler-iri-sync` Slice 6 is complete. It is best decided before [identity-minting.md](identity-minting.md)'s slice M2 (the Python library), because adopting it after M2 and M3 would discard both pure implementations. M0 and M1 of that sketch (ADRs, schemas, anchor vectors, vocabulary, recipe emission) are unaffected either way.
