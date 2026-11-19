<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence Contracts

The public contract between the persistence compiler's generated operations and whoever calls them: the `lattice-persistence` library
([`packages/persistence`](../../packages/persistence/README.md)), or your own implementation ([ADR-A132](../../docs/architecture/decisions/ADR-A132-persistence-caller-library.md)).
Everything here is usable without any LATTICE code.

| File | What it is |
|---|---|
| [`vectors.schema.json`](vectors.schema.json) | JSON Schema (2020-12) for the vectors document |
| [`vectors.json`](vectors.json) | Conformance vectors for the canonical N-Triples of a payload, the payloads that are refused, the request digest of several kinds of operation, the payload check, the events of an append, the caller check, the audit outcome, the reference modes, the checkpoint list and the confirmation of a write |
| [`verify-vectors.py`](verify-vectors.py) | Recomputes every line, every digest input and every digest with `openssl`, and decides every check with its own code, the confirmation of a write included, on the Python standard library. Shares no code with any library |


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
* `kind` is the operation's kind as the compiled profile names it (`Create`, `Replace`, `DeltaReplace`, `Tombstone`, `Append`, `AppendVersion`). `target` is the IRI
  without angle brackets, and `expected` is the expected seq as a decimal string. Either is the empty string where the operation has none.
* Each content part is one component, and it is `enc` of the part's canonical lines. The parts are those the profile's digest contract declares,
  in its `partOrder`: the payload, or for an append the events, then the add part and the del part where the operation has them. An empty
  part is still a component, so a triple in the add part and the same triple in the del part give different digests.
* The add and del parts mean different things for the two kinds of operation that have them. Under `dal:DeltaMembership` they hold the members a new version adds and drops, as `<v> pat:addsMember <m>` and `<v> pat:dropsMember <m>` (for example `<urn:quote:1/v5> pat:addsMember <urn:quote:1/line7>`). Under a patch log they hold the triples of the aggregate a write adds and removes (for example a renamed project's new `<urn:project:1> <urn:ex:title> "Beta"` in the add part and its old title in the del part). The digest treats both alike. A `DeltaReplace` has the add part and the del part and no payload part, since its request carries the change and not the state (`digest-delta-replace`).
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

## The confirmation

A `204` from the store does not say whether a write's guards matched, so after every write the caller reads what the store holds and classifies the write (STD-312, obligation 3 of [the compiler's README](../../tools/persistence/README.md#obligations-the-sparql-cannot-enforce-for-you)). The libraries give the read and the classification (`confirm_query`, `classify` and `confirm` in Python, `Confirmation.query`, `classify` and `run` in Java), and the vectors fix the classification. It follows section 15.2 of the [patterns guide](../../docs/architecture/rdf-sparql-patterns-guide.md#152-the-receipt-then-the-txn-claim), and where the guide has no row for a guard that a generated operation has, this section does.

**What it confirms.** An operation of kind `Create`, `Replace`, `DeltaReplace`, `Tombstone`, `Append` or `AppendVersion`, which records a transaction claim, and `KeyClaimWrite` and `KeyClaimWriteDual`, which record none and have a read of their own. Any other operation is not confirmed by this read, and a library refuses to build it (`ConfirmationError`, `ConfirmationException`).

**The read.** One `SELECT` of `?fact` and `?value`, run on the writer and never on a replica, since a replica that has not applied the write reports a fact absent. A row is one fact the store holds, and a fact the store does not hold has no row. The graphs and the node of the dataset are the operation's compile-time bindings, and every other term is an IRI of the request, rendered by the library from a typed IRI, so no value is read as SPARQL (PRI-55). The request's epoch, position and digest are never sent. They are compared in the classification, so the read cannot be fooled by the datatype of a stored number. The target is the request's `root`, or its `stream` for an `Append`.

| Fact | The objects of | In graph | Asked when |
|---|---|---|---|
| `claimRev` | `pat:rev` of `$txnId` | `txnGraph` | always |
| `claimDigest` | `pat:requestDigest` of `$txnId` | `txnGraph` | always |
| `datasetEpoch` | `pat:epoch` of `datasetNode` | `datasetGraph` | the template id ends in `-dataset-guard` |
| `rowSeq` | `pat:seq` of the target | `metaGraphPrefix` | always |
| `rowEpoch` | `pat:epoch` of the target | `metaGraphPrefix` | the kind is not `Create` |
| `rowDeleted` | `pat:deleted` of the target | `metaGraphPrefix` | the kind is not `Create` |
| `dataPresent` | one predicate of any triple of the target | `dataGraph` | the kind is `Create` and the operation has a `dataGraph` binding, which a composite family's has |
| `claimOwner`, `claimNextOwner` | `pat:claimedBy` of `$claim`, or of `$claimCurrent` and `$claimNext` | `keysGraph` | a key-claim write |

A value is an IRI as its text without angle brackets, and a literal as its lexical form. A number is compared by value, so `3` and `"3"^^xsd:long` are the same position.

**The classification.** The result is the outcome (`applied`, `refused` or `lostRace`), the classification, the revision the transaction's claim names (null where there is none) and a reason in words. For a lost race the classification is its cause, and each cause answers one guard of the generated operations in [`builders.py`](../../tools/persistence/src/persistence/builders.py). The first rule that holds decides.

| # | Holds when | Outcome | Classification | The guard it answers |
|---|---|---|---|---|
| 1 | the transaction has a claim (`claimRev` has a row) and `claimDigest` is the request's digest and no other | `applied` | `Applied` | `FILTER NOT EXISTS` on the claim, which makes a retry of an applied write a no-op. The write applied, on this attempt or an earlier one, whatever the store holds since |
| 2 | the transaction has a claim and `claimDigest` is anything else, or nothing | `refused` | `IdempotencyKeyReuse` | the same guard, for a transaction id that an earlier request already used. It is never reported as success |
| 3 | no claim, and the epoch guard in force failed (see below) | `lostRace` | `EpochChanged` | the guard on the epoch |
| 4 | no claim, the kind is not `Create`, and a `rowDeleted` is `true` | `lostRace` | `Gone` | `FILTER NOT EXISTS { target pat:deleted true }` of a replace, a delta replace, a tombstone, an append and an append of a version |
| 5 | no claim, the kind is not `Create`, and the version row is not as the guard needs it (see the position guard) | `lostRace` | `PreconditionFailed` | the pattern `target pat:seq $expectedSeq`, which is the optimistic guard, and for an append the pattern that the stream's row exists |
| 6 | no claim, the kind is `Create`, and a `rowSeq` has a row or `dataPresent` does | `lostRace` | `AlreadyExists` | the create's `FILTER NOT EXISTS` on the version row, and a composite create's on any triple of the root in the data graph |
| 7 | no claim, a key-claim write, and a `claimOwner` or `claimNextOwner` is an owner other than `$owner` | `lostRace` | `KeyClaimHeld` | `FILTER NOT EXISTS { claim pat:claimedBy ?other . FILTER(?other != $owner) }` |
| 8 | none of the above and the transaction has no claim | `lostRace` | `NotApplied` | the guards that leave no trace in the store (see the last item of the causes the guide does not have) |

A key-claim write has no transaction claim, so rules 1 and 2 do not apply to it. It is `Applied` when each claim it writes is held by `$owner` and by no other (rules 7 and 8 otherwise). A write that failed more than one guard is classified by the first rule, which is the order of the guide's table, so for example a tombstoned row whose position also moved is `Gone`.

**The epoch guard in force.** A template id that ends in `-dataset-guard` guards on the dataset's epoch, so rule 3 holds when no `datasetEpoch` equals the request's epoch, and a dataset that states none has none to match. Any other template of a kind that is not `Create` guards on the version row's own epoch (`dal:RowLevelGuardOnly`, the weaker scope that the profile validator warns about), so rule 3 holds when the row has an epoch and none equals the request's, and the dataset's epoch is not read. A `Create` or a key-claim write with no dataset guard has no epoch guard. The guide's table speaks of the dataset's epoch alone, since it describes the strong profile.

**The position guard.** Rule 5 holds for an operation that takes `$expectedSeq` when no `rowSeq` equals it, which is a row at another position or no row. For an `Append`, which takes none, it holds when the stream has no `rowSeq`, since `bootstrap-version-row` was not run (obligation 1).

**The causes the guide does not have.**

* `AlreadyExists` is the create's own guard. A create is not a compare-and-set, so no position can have moved, and the guide's `PreconditionFailed` would name a guard the create does not have. A version row that exists, a tombstoned one included, is a row, and a composite family's create also refuses a root that has data in the data graph and no version row.
* `KeyClaimHeld` is the key-claim write's guard, which the guide's Chapter 6 confirms with an `ASK` on `pat:claimedBy`.
* `NotApplied` is what no fact explains. A parameter guard, the group of type tests at the top of every guarded `WHERE`, writes nothing and leaves nothing to read, and a request that was never sent, or is still in flight, is the same to the read. A caller treats it as unknown and resends the identical request, as for a transport failure (obligation 4), then confirms again. It is the only classification of a lost race that is not a guard's.

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
