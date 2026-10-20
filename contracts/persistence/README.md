<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence Contracts

The public contract between the persistence compiler's generated operations and whoever calls them: the `lattice-persistence` library
([`packages/persistence`](../../packages/persistence/README.md)), or your own implementation ([ADR-A132](../../docs/architecture/decisions/ADR-A132-persistence-caller-library.md)).
Everything here is usable without any LATTICE code.

| File | What it is |
|---|---|
| [`vectors.schema.json`](vectors.schema.json) | JSON Schema (2020-12) for the vectors document |
| [`vectors.json`](vectors.json) | Conformance vectors for the canonical N-Triples of a payload, the payloads that are refused, the request digest of several kinds of operation, the payload check, the events of an append, the caller check, the audit outcome, the reference modes and the checkpoint list |
| [`verify-vectors.py`](verify-vectors.py) | Recomputes every line, every digest input and every digest with `openssl`, and decides every check with its own code, on the Python standard library. Shares no code with any library |


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

**The payload check.** A vector gives the root, the boundary shape, the edges of the shape and the payload, and states the subjects that are outside.
Start at the state (root, shape). From a state (node, shape), follow each edge whose source is the shape and whose ownership is `Owned`, forward
from the node (`s p o` with the node as `s`) or backward for an inverse edge, to the state (the other end, the edge's target shape). The root and
every node of a reached state are inside. A subject that is not inside is outside. An edge that names no target shape leads to a member that owns
nothing further. A family with a null shape bounds nothing. Reference and vocabulary edges are not followed, so a node reached only by one is
outside. The shape of the source matters, so `hasSubtask` owned from a task does not make a milestone own a subtask.

**The events of an append.** Every subject of the event triples is an event of the batch or starts with `{event}/part/`. The batch has at least one event, each event IRI and each `opSeq` are distinct, and a row has all four values. The codes are `EventOutsideBound`, `NoEvents`, `DuplicateEvent`, `DuplicateOpSeq` and `UndefInRow`.

**The caller check.** The codes are `MissingParameter`, `UnknownParameter`, `WrongKind`, `NotXsdLong` (a literal whose datatype is not exactly `xsd:long`, including `xsd:integer` and no datatype), `IllTypedLiteral` (`xsd:long` with a lexical form that is not an integer in range), `GraphNameMismatch` (a caller-named graph is not the prefix, the root encoded as `ENCODE_FOR_URI` does, and the suffix), `EmptyLogGraphs` and `LogGraphNotIri`. Each vector states the full set of codes for its request, sorted.

**The audit outcome.** `Failed` if the audit returned a row. Otherwise `NothingExamined` if the caller listed no graph for an audit that lists graphs, or counted no receipt in the graphs it listed. Otherwise `Clean`.

**Reference modes.** For every node the owned walk reaches, every edge of its shape, owned or not, is read. An object on a `Pinned` edge must be a version, and an object on a `ByIdentity` edge must not be one. What the caller does not know to be a version is not one.

**A checkpoint.** A version that is a checkpoint states `pat:checkpoint true` and lists exactly its members under the domain's membership property. A version that is not lists none and states no mark.

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
