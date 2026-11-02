<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.8a, the caller library core

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.8a, the first half of
[plan §4.8](../plans/formal-methods-track-h.md#48-h28-the-typed-payload-and-the-caller-side-checks-planned-2026-10-14), built under
[ADR-A132](../../architecture/decisions/ADR-A132-persistence-caller-library.md) (accepted 2026-10-20). Authored and run in autonomous mode, not
committed. H2.8b, the payload checks, the caller check and the audit outcome, comes after it.

**For the maintainer:** read the decisions taken alone below, above all the digest's nesting (decision 1), which differs from the patterns guide's formula.

## Invariant

A caller holding a compiled profile and the library builds a payload and a request digest that any other implementation reproduces from the
vectors alone. A payload holds ground triples, and every term is a typed value, so no blank node and no unvalidated string reaches the slot's text.
The compiler depends on the library for the shared types and the library never depends on the compiler.

## What changed

- **`packages/persistence/python`** (`lattice-persistence`, MPL-2.0, rdflib and the standard library only).
  - `terms`, moved from `persistence.terms` without `PropertyPath`.
  - `payload`: `Lit`, `Triple`, `Payload`, `EventRow` and `Rows`. A `Payload` has `lines()` and `nt()` (canonical N-Triples, for the digest) and `sparql()` (encoded
    text, for the slot), and `Payload.from_rdflib` refuses a blank node.
  - `contract`: the contract's data classes moved from `persistence.contract` (`OperationKind`, `ParameterContract`, `EdgeContract`, `PayloadContract`, `DigestContract`
    with a new `parts()`), and `read_contracts`, which reads each operation of a compiled profile.
  - `digest`: `enc`, `request_input` and `request_digest`, which follow the profile's `partOrder`.
- **`contracts/persistence/`**: `vectors.json` (4 N-Triples vectors, 5 refusals, 9 digests), `vectors.schema.json`, `verify-vectors.py` and a README.
  `REUSE.toml` already annotates `contracts/**/*.json`.
- **`tools/persistence`** depends on the library (`pyproject.toml`). `persistence.terms` re-exports the encoders and keeps `PropertyPath`. `persistence.contract` imports the moved
  classes. `persistence.namespaces` takes `DAL` and `PAT` from the library. `contract_emit` writes the digest parts from `DigestContract.parts()`, which is the one place the
  order is declared in the compiler and the library. The emitted profiles are unchanged, which `check:persistence-expected-profiles` confirms.
- **mise**: `check:persistence-vectors`, `bootstrap:persistence-library`, `check:persistence-library` (in `check`), and the library added to `bootstrap:persistence` and the root install.
- **Catalogue**: `packages/persistence` is in the `reaches` of the persistence tool package, since its tests read the library's compiled profiles. Like `packages/minting`, the
  package has no module entry of its own, and `check:catalogue` agrees with the tree.
- **ADR-A132**: a dated note of the decisions below. **Technical debt**: TD-69.

## Decisions taken alone, for the maintainer's review

1. **The digest nests each content part.** `enc([kind, target, expected, enc(lines of part 1), enc(lines of part 2), ...])`. The guide's flat `enc([kind, target, expected, *lines])`
   cannot separate the payload, add and del parts of a replace, which H2.6b-Q5 says must be hashed with their role. An absent part still has its (empty) component. Hence a triple moved
   from the add part to the del part changes the digest, which vectors `digest-same-triple-in-add` and `-in-del` show. The guide is out of step (TD-69).
2. **`kind` is the profile's `dal:operationKind`** (`Replace`), not the template name the guide mentions (`cas-replace`). The contract has an `OperationKindPart`, and the template name
   varies with the write discipline while the kind does not.
3. **Canonical N-Triples.** Lines sort by UTF-8 bytes (vector `nt-sort-is-by-utf8-bytes` separates it from UTF-16 order), duplicates are dropped, only backslash, quote, line feed and
   carriage return are escaped, `xsd:string` is written plain, a typed literal keeps its lexical form (`"042"^^xsd:integer` is not normalised) and a language tag is lower-cased.
4. **A target is hashed as the IRI without angle brackets,** and the expected seq as a decimal string, empty where the operation has none.
5. **Two texts from one `Payload`.** The canonical N-Triples is for the digest. The slot text uses the SPARQL encoders, since a backslash before `u` in canonical N-Triples would be read as
   an escape by an engine that processes `\uXXXX` before parsing (the property `terms._escape` already guards). A test round-trips such values through rdflib.
6. **`PropertyPath` stays in the compiler.** It renders a compiler structure (`persistence.paths`), and moving it would pull the compiler into the library.
7. **What moved into the library:** the terms, the data classes the library reads, `DAL` and `PAT`. `OperationContract`, the resource and access classes and the builder tables stay in
   the compiler, since the library does not read them.
8. **`read_contracts` returns every operation, keyed by the builder's name and operation node,** and reads the reference edges, though nothing uses them until H2.8b.
9. **Tests the library keeps its own copy of the compiled profiles** (`tests/data`, three examples, with an SPDX header), so it needs no compiler. `test_library_contract.py` holds them to `compile`.
10. **`bootstrap:persistence` installs the library with the compiler,** because `lattice-persistence` is not on any index. `check:persistence-library` depends on `check:persistence-vectors`.
11. **Out of scope and not done:** the payload checks, the caller check, the audit outcome, the minimal SPARQL client interface (all H2.8b), the compiler README and the guide's dated note.

## Tests

| ID | Checks |
|---|---|
| H2.8a-V1 | `verify-vectors.py` recomputes 36 checks of the vectors with its own serialiser and `openssl` (and a shell `xxd \| sha256sum` of four digests agrees) |
| H2.8a-T1 | the library reproduces every N-Triples vector, refuses every refusal vector, and matches every digest's bytes and hash |
| H2.8a-T2 | the vectors cover Create, Replace, Tombstone, Append and AppendVersion and every part role. The schema validates the vectors |
| H2.8a-T3 | swapping two parts of the contract changes a digest |
| H2.8a-T4 | a blank node is refused on `from_rdflib` and when a `Triple` is built, a plain string is not a term, an IRI with a forbidden character is refused, and a literal holding `} } ; DROP ALL` stays one literal |
| H2.8a-T5 | the slot text of tricky literals round-trips through an rdflib `INSERT DATA` |
| H2.8a-T6 | `opSeq` must be an `xsd:long`, and `Rows` holds rows only |
| H2.8a-T7 | `read_contracts` reads a compiled profile, the digest parts in order, an append's event part with two sources, and the digest of a request to a profile's operation |
| H2.8a-T8 | a missing source slot is named, a bare string is not a payload, and an operation without a digest refuses |
| H2.8a-T9 | the library imports only the standard library, rdflib and itself |
| H2.8a-C1 | `tools/persistence/tests/test_library_contract.py`: for every operation of the 12 configurations the library's reading equals the compiler's derivation (kind, version, parameters, digest parts, payload parameter and root), the reference edges are read, and the library's three fixtures are isomorphic to what compile emits |

No test was removed or weakened.

## Results (run 2026-10-20)

| Command | Result |
|---|---|
| `mise run check:persistence` | 3966 passed, 1 xfailed (the expected profiles check ran and passed) |
| `mise run check:persistence-oxigraph` | 5 passed, then 363 passed, 3604 deselected |
| `mise run check:ontology-catalog` | 1136 passed, 7 skipped, and "ontology catalog consistent, 2 known defect(s) reported". It first failed `test_rc3_t17` for the persistence tool package, because its tests now read `packages/persistence`, and passed after that path was added to its `reaches` |
| `mise run check:persistence-library` | vectors 36 checks passed, 0 failed. Library 35 passed |
| `mise run check:persistence-vectors` | 36 passed, 0 failed (also run as part of the line above) |
| `mise run check:catalogue` | 19 modules and 8 tool packages agree with the tree |
| `mise run check:agent-guidance`, `mise run check:published-decisions` | 0 problems, 6 passed |
| `build:persistence-execution` | not run |

Probes:

- Digest part order. In `digest.request_input` the content parts were reversed. `test_every_digest_vector` and `test_part_order_is_hashed` failed (2 failed, 33 passed), and the code was restored (35 passed).
- Blank node. `Payload.from_rdflib` of a graph with a blank node object raised `PayloadError: a payload holds no blank node`, and so does building a `Triple` from a blank node.

## What remains

- H2.8b: the payload checks (owned path, event subjects under ADR-A123's addendum, rows), the caller check, the audit outcome, the client interface, vectors for each, and the `INFO` diagnostics.
- The guide's section 15.2 dated note (TD-69), the compiler README rewrite and the Java sibling.
- Nothing is committed.

## One command

```
mise run check:persistence-library
mise run check:persistence
mise run check:persistence-oxigraph
mise run check:ontology-catalog
mise run check:catalogue
```

From the repository root. A pass is no failed test and the vectors at 36 of 36.
