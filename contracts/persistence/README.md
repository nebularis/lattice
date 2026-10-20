<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence Contracts

The public contract between the persistence compiler's generated operations and whoever calls them: the `lattice-persistence` library
([`packages/persistence`](../../packages/persistence/README.md)), or your own implementation ([ADR-A132](../../docs/architecture/decisions/ADR-A132-persistence-caller-library.md)).
Everything here is usable without any LATTICE code.

| File | What it is |
|---|---|
| [`vectors.schema.json`](vectors.schema.json) | JSON Schema (2020-12) for the vectors document |
| [`vectors.json`](vectors.json) | Conformance vectors for the canonical N-Triples of a payload, the payloads that are refused, and the request digest of several kinds of operation |
| [`verify-vectors.py`](verify-vectors.py) | Recomputes every line, every digest input and every digest with `openssl` and the Python standard library. Shares no code with any library |

The payload checks, the caller check and the audit outcome have their vectors here when H2.8b adds them.

## What the vectors fix

**Canonical N-Triples.** One line per triple, `<s> <p> o .`, sorted by the UTF-8 bytes of the line, with no duplicate line.

* A literal escapes backslash, quote, line feed and carriage return as `\\`, `\"`, `\n` and `\r`, and nothing else. A tab, a non-ASCII
  character and an astral character are written as themselves, and a backslash before `u` stays two backslashes.
* A literal of `xsd:string` is written plain. Any other datatype is kept, with its lexical form as given. A language tag is lower case.
* A payload holds no blank node. A subject or a predicate is an IRI, an IRI holds none of the characters `< > " { } | \ ^` and a grave accent, and no space or control character.

**The request digest.**

```
requestDigest = hex(SHA-256(enc([kind, target, expected, part1, part2, ...])))
```

* `enc` is the tuple encoding of the patterns guide's Chapter 5. Each component is its UTF-8 length in decimal, a colon and its bytes.
* `kind` is the operation's kind as the compiled profile names it (`Create`, `Replace`, `Tombstone`, `Append`, `AppendVersion`). `target` is the IRI
  without angle brackets, and `expected` is the expected seq as a decimal string. Either is the empty string where the operation has none.
* Each content part is one component, and it is `enc` of the part's canonical lines. The parts are those the profile's digest contract declares,
  in its `partOrder`: the payload, or for an append the events, then the add part and the del part where the operation has them. An empty
  part is still a component, so a triple in the add part and the same triple in the del part give different digests.
* The event part is the lines of each row's `rdf:type`, `pat:opSeq` (`xsd:long`) and `pat:occurredAt` triples together with the event triples,
  sorted and de-duplicated as one list. It leaves out `pat:revision`, which the store mints.

## Checking

```bash
mise run check:persistence-vectors
```

Or, without `mise`, from this directory with any Python 3 and any `openssl`:

```bash
python3 verify-vectors.py
```

Any one digest can also be checked in a shell from its `encodedHex`:

```bash
echo "<encodedHex>" | xxd -r -p | sha256sum
```

A conformant implementation passes the vectors with its own code. The library's tests run every vector.

## Licence

MPL-2.0. JSON cannot carry a licence header, so `vectors.json` and the schema are annotated in the repository's [`REUSE.toml`](../../REUSE.toml). `verify-vectors.py` carries its own header.
