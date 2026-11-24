<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MSA-I11: the logical port, with the studio's writes moved onto it

**Unit:** [`multi-store-architecture`](../../status/multi-store-architecture.md), investigation MSA-I11 of the [sketch](../../sketches/multi-store-architecture.md) §6
**Written:** 2026-11-17, on paper, against the Configuration Studio's writer and the persistence caller library on `spi/sql-backend`
**Placement:** T0, public. Platform configuration, nothing domain-specific
**Builds on:** [MSA-I3](MSA-I3-dimensions-by-dialect.md) for what the port may expose, [MSA-I4](MSA-I4-four-operations-lowered.md) for the commands under it, and the patterns guide §25.1 for the port it replaces

## 1. The question

The sketch's §4.8 leans towards a logical port, defined as a contract with an executor as the adapter's internal seam, in place of the guide's RDF-shaped `ConditionalRdfStore`. This note writes the port out, moves the studio's create, replace and tombstone onto it, and sets the outcome classification of each realisation side by side. The falsifier is that the studio needs something the port cannot say.

## 2. What the studio does today

Read from `platform/config-studio-core`, `platform/config-studio-writer` and `packages/persistence/java`.

- **No port.** `Writer` builds Jena `UpdateRequest`s through `StudioOperations` and sends them with `RDFConnection.update`. `ScopedDataset` cannot address the studio's graphs, since `GraphReference` requires an `http` or `https` IRI and the studio's are `urn:lattice:studio:…`.
- **Four generated operations.** `create-if-absent`, `cas-replace`, `replace-whole` and `tombstone-delete`, over six named-graph families under `dal:Optimistic` (`contracts/config-studio/persistence-profile.ttl`). Parts and documents are written as deltas under a patch log, and the rest whole.
- **The caller chooses every infrastructure value.** The transaction id is `urn:txn:{command id}/{n}`, the revision IRI is formatted from the root, epoch and sequence, `nextSeq` is `expect + 1`, and the epoch is the process setting `LATTICE_STUDIO_EPOCH`.
- **One request per batch.** Up to 64 commands become one SPARQL Update request, for one commit (TSD-44). A command may write several aggregates, each in its own operation, and ends with a `cst:Receipt` guarded on the claim of its last operation.
- **Writes no operation generates.** Job graphs and their receipts, the `cst:Receipt` of every command, `DROP SILENT GRAPH` of a retired document's patch graphs, and promotion maintenance appended to the same request.
- **Outcomes by a second read.** The update returns nothing. The writer reads the commands' receipts by id afterwards, and a command with none is answered by a supplier that reads the state again. The statuses are 200, 400, 403, 404, 412 and 503.

## 3. The port

Written in Java form, since the studio is the first caller. Every name in it is logical. None names a graph, a table or a label.

```java
record Root(String iri) {}
record Version(long epoch, long seq) {}

sealed interface Expect permits Expect.Absent, Expect.At, Expect.Any {
  record Absent() implements Expect {}
  record At(Version v) implements Expect {}
  record Any() implements Expect {}
}

sealed interface Payload permits Payload.Whole, Payload.Delta, Payload.Events, Payload.None {
  record Whole(Facts next) implements Payload {}
  record Delta(Facts assert_, Facts retract) implements Payload {}
  record Events(List<EventRow> rows) implements Payload {}
  record None() implements Payload {}
}

// One operation of the compiled profile, by logical id, on one aggregate.
record Op(String operation, Root root, Expect expect, Payload payload, Map<String, Value> params) {}

// A business precondition, named in the compiled profile and never written by the caller as a pattern.
record Guard(String guard, Root root, Map<String, Value> params) {}

// Several operations in one store, applied all or nothing, recorded under the unit's id.
record Unit(String id, List<Guard> guards, List<Op> ops) {}

sealed interface Outcome {
  record Applied(Map<Root, Version> versions) implements Outcome {}
  record Duplicate(Map<Root, Version> versions) implements Outcome {}       // the same id and request, answered from the receipt
  record KeyReuse(String id) implements Outcome {}                          // the same id, a different request
  record Stale(Root root, Version actual) implements Outcome {}
  record Absent(Root root) implements Outcome {}
  record Gone(Root root) implements Outcome {}
  record EpochChanged() implements Outcome {}
  record Refused(String guard, Root root) implements Outcome {}             // a business guard failed
  record Unknown(String id) implements Outcome {}                           // only a transport failure, settled by resolve
}

interface LogicalStore {
  Capabilities capabilities();
  List<Outcome> apply(List<Unit> batch);              // independent units, in one commit where the store allows it
  Outcome resolve(String unitId);
  Optional<Snapshot> read(Root root);                 // the aggregate's facts and its version
  Optional<Snapshot> readAt(Root root, Version at);   // where the receipt model keeps history
  void housekeep(Housekeeping task);                  // retention of receipts and patch content
}
```

What the port takes from the guide, and what it changes.

| Guide §25.1 | This port | Why |
|---|---|---|
| `AggregateId(graphIri)` | `Root(iri)` | the graph is a layout (MSA-I3 §4.1) |
| `Version(token)`, opaque | `Version(epoch, seq)` | every realisation keeps both, and the studio's 412 reports the current one |
| `CasCommand` with `deletes` and `inserts` as triples | `Op` with a logical operation id and a `Payload` of facts | §4.8's case against an RDF-shaped port. Facts are decoded by the mapping, or held in a fact table where the shape is open (MSA-I4 §4.4) |
| `guards` as patterns | `Guard` by name from the compiled profile | a pattern is SPARQL. A named guard is lowered like an operation |
| `txnId` from the caller | the unit's id, with each operation's transaction id derived by the adapter | the studio derives them already, and nothing else reads them |
| `beginUnitOfWork`, gated on `multiAggregateAtomicity` | `Unit`, always | every realisation here can do it in one store (§5) |
| `compareAndSet` returns one result | `apply` of a batch returns one outcome per unit | TSD-44's batching is the studio's throughput |
| `CasResult.Conflict` | none | MSA-I4's guards make every non-application definite. An engine's own abort is retried by the adapter, and reported as `Unknown` if it persists |
| `resolve(txnId)` | `resolve(unitId)` | the unit is what the caller sent |
| none | `housekeep` | retention is housekeeping and today a hand-built `DROP` |

## 4. The studio's writes on the port

| Studio command | Today | On the port |
|---|---|---|
| `create` | a part's `create-if-absent`, the description's `create-if-absent`, a receipt guarded on the second | `Unit(id, [], [Op("create", part, Absent, Whole(baseline)), Op("create", workspace, Absent, Whole(description))])` |
| `save` | the writer compares `expect`, computes the delta against the stored graph, runs `cas-replace` (delta) or `replace-whole` | `Unit(id, [], [Op("replace", part, At(expect), Delta(asserted, retracted))])`, and `Stale` carries the current version the 412 needs |
| `save-document` | a document's write, and the description's whole replace when its title changed | one unit of two ops |
| `delete-document` | the description's replace, the document's `tombstone-delete`, then `DROP SILENT GRAPH` of its patch graphs | one unit of the replace and `Op("tombstone", doc, At(v), None(), {cause, actor})`, then `housekeep` for the patch content |
| `import` | a `create-if-absent` per part and document and the description's | one unit of all of them |
| `publish` | the version's `create-if-absent` and the lineage's create or replace | one unit. The lineage changing meanwhile is `Stale` on the lineage, which the studio answers as "publish again" |
| `set-access`, `set-dependencies`, `release`, `fence` | a whole replace of the description, and for `fence` a create of the import | one unit each |
| `submit-job`, `job-update`, `delete-job` | hand-built updates on job graphs, outside any family | not on the port until jobs are a family (§6) |

What the studio stops choosing. The transaction ids, the revision IRI, `nextSeq` and the request digest move into the adapter. The epoch becomes the store's dataset epoch, which `EpochChanged` reports, rather than a process setting checked only against each version row, since the studio's families use `RowLevelGuardOnly`.

What the studio keeps. Computing a delta against the state it read is the caller's, because the payload's form is semantic (`replaceEncoding`, MSA-I3). Access control stays above the port, so 403 never reaches it.

## 5. Outcome classification by realisation

| Outcome | SPARQL on Fuseki | SQL on PostgreSQL | GQL | the exported interpreter |
|---|---|---|---|---|
| how it is known | a read after the request, since an Update returns no count: the unit's receipt with its digest, then each root's version row, then the dataset epoch (guide §15.2) | within the transaction, each guard's row count in MSA-I4's order | within the transaction, each statement's count and any key-constraint violation | `exec` returns it |
| `Applied` | the receipt exists with this request's digest, written in this request | `COMMIT` returned | commit returned | returned |
| `Duplicate` | the receipt existed before, with the same digest | the transaction claim's insert found the id, and the digests agree | as SQL | returned |
| `KeyReuse` | the receipt existed, with another digest | the claim found the id, and the digests differ | as SQL | returned |
| `Stale`, `Absent`, `Gone` | no receipt, then the version row read | the `SELECT … FOR UPDATE` of the row | the `MATCH` of the row | returned |
| `EpochChanged` | the dataset epoch read | the dataset row read in the transaction | as SQL | returned |
| `Refused` | the named guard read again | the guard's query in the transaction | as SQL | returned |
| `Unknown` | the request or the read failed in transport | `COMMIT`'s answer was lost | the commit's answer was lost | never |
| a batch of units | one request, each unit's receipt written first under the joint guard of its operations, and each operation applied only where that receipt was written, so one unit's failure leaves the others | one transaction with a savepoint per unit, rolled back to it on a failed guard | one transaction per unit unless the product has savepoints *(verify)* | one call per unit |

Two rows need more than the studio has. On SPARQL a unit of several aggregates is all or nothing only when its operations' guards are evaluated together. They cannot share one `WHERE`, since a whole replace and a tombstone each end theirs with a sweep that gives one solution for each stored triple, and two sweeps in one `WHERE` multiply. The unit's receipt is instead its first operation, guarded on every row the unit writes, and each later operation keeps its own `WHERE` with one more pattern, the receipt (corrected 2026-11-24, [MSA-I14](MSA-I14-whole-commands.md) section 5). The studio's operations are separate, and its receipt is guarded on one operation's claim, so an earlier operation can apply while a later one does not. The studio makes that safe for readers by the order of its operations ([ADR-A149](../../../architecture/decisions/ADR-A149-publication-from-the-studio.md) decision 13), and a unit on the port makes it unnecessary, since the unit's operations take one guard. On SQL the unit is one transaction with a savepoint and needs nothing more.

## 6. Verdict

The falsifier does not fire for the port written here. Every write the studio makes through a generated operation moves onto it, each command as one unit, and the studio stops choosing infrastructure values it chooses today. The port had to gain five things the guide's lacks for this to hold. A unit of several operations as its basic write, a batch of units in one commit, named business guards, a `Version` the caller can report, and housekeeping for retention.

It fires against the guide's port, which cannot say a batch, ties atomicity across aggregates to a capability, and leaves retention to hand-built writes.

Two needs of the studio are not met by any port that holds only generated operations, and are recorded rather than answered.

- **Jobs.** They are coordination data with no family (PRI-52), written by hand with a business rule (a succeeded job ignores a later failure). They go onto the port once they are a family with a named guard, or they stay outside it as a declared exception.
- **Promotion maintenance in the same request.** A derived family kept by the write that changes its source needs the `DERIVED` graph role to map to a resource, and today it maps to none (`contract.py`). Under D2 a derived tier in another store is a crossing, and in the same store it is part of the unit.

## 7. Findings

| ID | Finding | Consequence |
|---|---|---|
| MSAI11-01 | A studio command that writes several aggregates runs them as separate operations in one request, with its receipt guarded on one operation's claim, the last by default (`Writer.Steps.commit`). An earlier operation can apply while a later one does not. This is by design: [ADR-A149](../../../architecture/decisions/ADR-A149-publication-from-the-studio.md) decision 13 orders a command's operations so that a guard failing part way leaves nothing a reader acts on, a version before its lineage, the parts before the description on creation, the description first on deletion | on the port a unit is all or nothing, so a studio command moved onto the port gives its operations one guard, and on SPARQL its receipt is written first under that guard and every operation requires the receipt. MSA-F6 tested decision 13 on six commands: nothing a reader acts on remains in each, and a resend completes a publication and a new document's save but not a deletion whose later tombstone failed, which leaves a graph no reader reaches ([MSA-F6](../../validation/MSA-F6.md)) |
| MSAI11-02 | A resend of a command id with a different body is answered 200 from the receipt. The writer reads receipts by id and never compares the request digest it writes into the claim | the port's `KeyReuse`. The studio has the digest in the store already |
| MSAI11-03 | The epoch is a process setting, `LATTICE_STUDIO_EPOCH`, checked against each version row and never against the dataset | `EpochChanged`, with the dataset epoch as the source |
| MSAI11-04 | `GraphReference` accepts only `http` and `https` IRIs, so `ScopedDataset` cannot read the studio's graphs | `Root` replaces it |
| MSAI11-05 | `StreamWriter` retries a batch forever on any `RuntimeException`, including one the store will raise again for the same request | a poison batch holds its partition. On the port, a `Refused` or a malformed unit is answered and the batch continues |
| MSAI11-06 | `DERIVED` has no resource kind in `contract.py` | the unit cannot name promotion maintenance until it does |

## 8. What follows

- **For MSA-I5.** A unit is one command of MSA-I4's IR whose guards are the union of its operations' guards, so the laws cover units without a construct of their own.
- **For MSA-I6.** Model X3, a relay reading receipts, reads unit receipts.
- **For MSA-I8.** The family run on PostgreSQL goes behind `LogicalStore`, with the savepoint batch of §5.
- **For the maintainer.** MSAI11-02 and MSAI11-05 were defects in running code, fixed by MSA-F3 and MSA-F2. MSAI11-01 is decision 13's design, tested by MSA-F6.
