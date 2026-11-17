<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MSA-I3: every persistence dimension against SPARQL, SQL and GQL

**Unit:** [`multi-store-architecture`](../../status/multi-store-architecture.md), investigation MSA-I3 of the [sketch](../../sketches/multi-store-architecture.md) §6
**Written:** 2026-11-17, against `tools/persistence/src/persistence` and `ontology/persistence/spec/persistence.ttl` 0.22.2 on `spi/sql-backend`
**Placement:** T0, public. Platform configuration, nothing domain-specific
**Builds on:** [lattice-sql.md](../rdf-engine/lattice-sql.md) §9, which gives each dimension's relational realisation, and [lpg-backend-options.md](../lpg-backend-options.md) §4.3, which gives the property-graph one. This note does not repeat their realisations. It classifies.

## 1. The question

The sketch's §4.7 leans towards selecting operations in two stages. Semantic selection reads the resolved profile and yields logical operations. Realisation selection reads the dialect and the capability record and yields a form of each. The falsifier is that no stable classification of the dimensions exists, so the two stages have no line to draw between them.

## 2. The classes and the test

Four classes, as the sketch names them.

| Class | A dimension is in it, for a dialect, when |
|---|---|
| semantic | it changes what the logical port offers. That is the set of operations, a parameter or payload of one, the outcomes one can return, or the guarantee stated for one |
| layout | it changes how the realisation arranges its records, and a caller of the port can observe nothing but cost and how often a conflict outcome occurs |
| parameter | it is a value bound into an operation or a layout, and selects nothing |
| without meaning | it has no effect in that dialect. The compiler accepts it and reports that it collapses |

A dimension is stable when it is semantic in every dialect or in none. Semantic selection reads the semantic dimensions and nothing else, and realisation selection reads the rest with the capability record.

The sketch's own test is that a dimension is semantic where any dialect's guarantee depends on it. The test above is stricter, since it asks what a caller of the port can observe. The two disagree on one dimension, `metaTopology` (§4.5), and on nothing else.

The port is the logical port of §4.8, an operation id with parameters and a payload. Under the RDF-shaped port of today a graph name is a parameter, and several layout dimensions would look semantic only because the port exposes the layout. That is §4.8's case against the current port and not a fault in the classification.

## 3. The classification

Notation. **S** semantic, **L** layout, **P** parameter, **–** without meaning. The GQL column assumes a product with explicit transactions and a key constraint on a label, which the capability record has to state because products differ ([lpg-backend-options.md](../lpg-backend-options.md) §4.3 marks each such point for verification).

### 3.1 The thirty resolved dimensions

| Dimension | SPARQL | SQL | GQL | Class | Capability fields it depends on |
|---|---|---|---|---|---|
| `aggregateBoundary`, whether there is an aggregate and its extent | S | S | S | split, see §4.1 | none |
| `aggregateBoundary`, named graph against owned path | L | – | – | split, see §4.1 | none |
| `concurrencyProfile` | S | S | S | semantic | `cas`, and for `LockingConcurrency` row locks and `multiRequestTx`, which the record lacks |
| `orderingGrain` | S | S | S | semantic | `nativeSequence` |
| `receiptModel` | S | S | S | semantic | `nativeChangeFeed`, `changeFeedDense` and `feedRetention` for a patch log served by the store, `nativeTimeTravel` for `SnapshotPerRevision` |
| `metaTopology` | L | – | – | layout, see §4.5 | `detectsWriteWriteConflict`, `statementLevelConflictDetection` |
| `epochGuardScope` | S | S | S | semantic | none |
| `firstWrite` | S | S | S | semantic, see §4.4 | `statementLevelConflictDetection` on SPARQL, a key constraint on SQL and GQL |
| `etagForm` | – | – | – | without meaning to any store, see §4.6 | `httpPreconditions` |
| `etagRepresentation` | – | – | – | without meaning to any store | none |
| `deadlockPolicy`, `PartitionedWriter` | S | S | S | split, see §4.2 | `singleWriter`, and the transport record of MSA-I9 |
| `deadlockPolicy`, `EngineDetectAndRetry` against `SortedAcquisition` | – | L | L | split, see §4.2 | `multiRequestTx` |
| `globalReadStrategy` | S | S | S | semantic | `nativeCommitPosition`, `nativeChangeFeed`, `changeFeedDense` |
| `lagWindowMillis` | P | P | P | parameter of a semantic choice | none |
| `contiguityCheckMode` | S | S | S | semantic | `nativeSequence` |
| `retentionMode` | S | S | S | semantic | `nativeTimeTravel` |
| `asOfFloorSource` | P | P | P | parameter of a semantic choice | `nativeTimeTravel` |
| `txnShards`, `logShards`, `keyShards` | P | – | – | parameter of a layout, recorded and not honoured | none |
| `registryGraph` | P | – | – | parameter of a layout. A table name would be its SQL counterpart | none |
| `epochAuthority` | S | S | S | semantic | none |
| `privacyClass` | S | S | S | semantic | `graphLevelAccessControl` |
| `erasureStrategy`, deletion against key destruction | S | S | S | split, see §4.3 | none |
| `erasureStrategy`, `PerSubjectGraphDrop` as the form of deletion | L | L | L | split, see §4.3 | none |
| `erasurePrecedence` | S | S | S | semantic, recorded and read by nothing | none |
| `perSubjectScoped` | S | S | S | semantic | none |
| `writeDiscipline` | S | S | S | semantic | none |
| `membershipEncoding` | S | S | S | semantic | none |
| `checkpointEvery` | P | P | P | parameter of a semantic choice, read by the caller | none |
| `replaceForm` | L | – | – | layout, the model case of realisation selection | `providesSnapshotUpdateSemantics` |
| `replaceEncoding` | S | S | S | semantic | none |
| `recordsStateDigest` | S | S | S | semantic | none, but the digest has to be defined over values for the realisations to agree (sketch §4.4) |

### 3.2 Settings carried on profile nodes

| Setting | SPARQL | SQL | GQL | Class | Note |
|---|---|---|---|---|---|
| `boundaryShape` | S | S | S | semantic | it is the aggregate's extent, and the mapping of MSA-I10 is built from it |
| `graphIriTemplate` | L | – | – | layout | visible to a reader of the store through ADR-A15's direct profiles, which read the RDF realisation only |
| `dataGraph` | L | – | – | layout | |
| `ownsReferenceData` | S | S | S | semantic | a check |
| `valueGuardProperty` | S | S | S | semantic | it names the resource a `NoBoundary` family guards |
| `minConcurrencyLevel` | S | S | S | semantic | becomes `requires_cas`, and on SQL the isolation level ([lattice-sql.md](../rdf-engine/lattice-sql.md) M43) |
| `opSeqRequired`, `datasetTierModel` | S | S | S | semantic | checks |
| `metaShards` | P | – | – | parameter of a layout | |
| `priorMetaShards`, `epochBumpAcknowledged` | P | – | – | parameter of a layout's migration | |
| `epochCoordinatorBinding`, `erasureRegisterBinding` | P | P | P | parameter, recorded and read by nothing | |
| `erasureReplayOnRestore` | S | S | S | semantic, recorded and read by nothing | |

### 3.3 Uniqueness, identity, resolution and run options

| Setting | SPARQL | SQL | GQL | Class | Note |
|---|---|---|---|---|---|
| a uniqueness constraint, with `keyProperty`, `scopeProperty`, `onViolation`, `mergeRelation` | S | S | S | semantic | a key claim graph on SPARQL, a unique index on SQL, a key constraint where the GQL product has one |
| `minEnforcementLevel` | S | S | S | semantic | `Strong` needs `commitValidation` on SPARQL and is native on SQL. The record lacks a field for a native key constraint |
| `claimScheme`, `schemeState` | S | S | S | semantic | the dual claim during a scheme change |
| `constraintId` | P | P | P | parameter | |
| every identity setting of `dal:IdentityProfile` | S | S | S | semantic | a record keeps the IRI its recipe mints in every realisation (sketch §4.4) |
| `dal:priority`, the scope kinds, `dal:appliesTo` | – | – | – | resolution, before either stage | |
| `dal:requiresReasoning` with `providesReasoning` | S | S | S | unstable, see §4.6 | the one capability field semantic selection reads today |
| `--no-parameter-guards` | L | – | – | layout of the SPARQL text | |
| `--caller-graph-names` | L | – | – | layout, visible only at the RDF-shaped port | |
| `--capability-spec`, `--no-fail-on-capability`, `--warn-unbounded-payload` | – | – | – | tooling | |

## 4. Where the line needed work

Of the thirty resolved dimensions, twenty-seven are stable as they stand. Three mix classes across their values and split cleanly. One resolution input makes semantic selection read a capability. One dimension is classed differently by the sketch's test and by the port test.

### 4.1 `aggregateBoundary` holds two things

Its three values answer two questions. Whether there is an aggregate at all is semantic in every dialect, since `NoBoundary` yields a value-guarded replace of one property, a different resource (`PropertyValue`) with a different guarantee. Whether an aggregate is a named graph or a tree along owned properties in a shared graph is a SPARQL layout, and both become the same root row and child rows in SQL and the same owned subgraph in GQL.

The two are equal at the port only where the family declares a boundary shape. A named-graph family without one has an extent defined by its graph, which is whatever was written into it. That has no relational counterpart except an opaque value keyed by the root, and it is the same gap MSA-I1 measured, where no shape in the estate is closed. So the split is into a semantic `boundary` (an aggregate with an ownership tree, an aggregate defined by its graph, or none) and a SPARQL layout (named graph or owned path). The middle value is the one a second realisation cannot take.

### 4.2 `deadlockPolicy` names a crossing mechanism beside two retry strategies

`PartitionedWriter` is the serialised-writer row of §4.2's catalogue, a guarantee a crossing declares, and is semantic. `EngineDetectAndRetry` and `SortedAcquisition` choose how a multi-statement transaction avoids or survives a deadlock. They have no meaning on SPARQL, where one operation is one request (the validator already warns, `SortedAcquisitionIneffective`), and they are a realisation choice on SQL and GQL. The first value moves to the crossing declaration and the other two stay as a realisation setting.

### 4.3 `erasureStrategy` names a layout among its methods

Erasing by deletion and erasing by destroying a key differ in what a backup still holds, which is semantic. `PerSubjectGraphDrop` is deletion in the form of a SPARQL layout. On SQL it is a cascade delete on a subject key and on GQL a delete of what carries the subject's partition key ([lattice-sql.md](../rdf-engine/lattice-sql.md) M50, [lpg-backend-options.md](../lpg-backend-options.md) §4.3). The method is semantic and its form is a realisation choice.

### 4.4 `firstWrite` is stable, and its motive is one dialect's

`PreCreatedRow` replaces `create-if-absent` with a `bootstrap-version-row` the caller runs when it allocates an id (`operations.py`, `select_operations`). That changes the operation set in every dialect, so the dimension is semantic everywhere and the line holds. Its reason to exist is SPARQL's. An insert-if-absent is atomic on SQL under a primary key, so both values are safe there and the choice is the caller's convenience. On a SPARQL store an absent row is safe only where the store detects a conflict on what a statement read, which is what `providesStatementLevelConflictDetection` declares, and that field is read by nothing (§5).

### 4.5 `metaTopology`, where the two tests disagree

The sketch calls the meta topology a layout choice that changes the guarantee on a store whose conflict detection is coarser than a statement. Read against the operations, the shard changes which graph holds a family's version rows, and a version-row compare-and-set is safe or unsafe by whether the store detects a write-write conflict on that row. Sharing a graph with other families' rows makes a store that detects conflicts per graph report conflicts between families that did not touch each other. That raises how often a write sees a conflict and retries. It does not let two writes of one aggregate both commit, since they touch the same row in either topology.

So under the port test `metaTopology` is a layout with a cost on coarse stores, and under the sketch's test it is semantic. This note takes the port test and records the disagreement as a claim for MSA-I6 to check, with a model of a store that detects conflicts per graph. The compiler agrees with the port test today, since the dimension's value is read by nothing and only `metaShards` changes the output.

### 4.6 `requiresReasoning` makes semantic selection read a capability

Resolution drops every candidate profile whose scope needs reasoning when the capability record says the store does not reason (`resolver.py`, `_select`). The same configuration then resolves to a different profile on a store without reasoning, so the semantic contract depends on the store, without a refusal. That is the one place where the line between the stages does not hold today.

Two repairs keep it. Membership of a scope can be settled where the types are known, which for SQL and GQL is the mapping, since a row's class is its table and a node's its label, and for SPARQL is ADR-A83's compile-time reasoner. Or the requirement can be checked after semantic selection, refusing a store that cannot meet it rather than selecting another profile. The second is smaller and keeps today's behaviour visible. This is put to the maintainer as part of MSA-Q11.

`etagForm` and `etagRepresentation` are without meaning to every store because they are read at the HTTP surface, from the version the port returns. They belong to the surface's declaration, and the persistence profile carries them by history.

## 5. The capability record this needs

| Field | State today | Needed by |
|---|---|---|
| `providesSnapshotUpdateSemantics` | read, selects `-rows` | `replaceForm` |
| `providesCas`, `providesCommitValidation` | read by the requirement check | `concurrencyProfile`, `minEnforcementLevel` |
| `providesReasoning` | read by resolution | §4.6, to be read after semantic selection or not at all |
| `providesSingleWriter` | loaded, read by nothing | `deadlockPolicy` `PartitionedWriter`, and the crossing declaration |
| `providesStatementLevelConflictDetection` | loaded, read by nothing | `firstWrite` `AbsentRow` on SPARQL |
| a native key constraint | absent | uniqueness at `Strong`, `firstWrite` on SQL and GQL |
| `detectsWriteWriteConflict`, `maxIsolation`, `multiRequestTx` | in the guide's §25.2 only | `concurrencyProfile` on SQL and GQL, `deadlockPolicy` |
| `reportsAffectedRows` | in the guide's §25.2 only | outcome classification without a confirmation read (sketch §4.8) |
| `nativeSequence`, `nativeCommitPosition`, `nativeChangeFeed`, `changeFeedDense`, `feedRetention`, `nativeTimeTravel` | in the guide's §25.2 only | `orderingGrain`, `globalReadStrategy`, `contiguityCheckMode`, `receiptModel`, `retentionMode` |
| `graphLevelAccessControl` | in the guide's §25.2 only | `privacyClass`, and keeping key claims and transaction claims from payload readers |
| a transport record | absent | the serialised-writer row. MSA-I9 found the fields it needs, among them that a single active consumer is not a fence, whether producers are deduplicated, and how offsets are stored |

Realisation selection reads every field in this table except `providesReasoning`. Semantic selection reads none of them once §4.6 is repaired, and the requirement check compares the semantic result with the record afterwards, as it does for `requires_cas` today.

## 6. Verdict

The falsifier does not fire. A stable line exists for every dimension once three of them are split by value (§4.1 to §4.3) and resolution stops dropping candidates for want of reasoning (§4.6). With those changes, of the thirty resolved dimensions sixteen are semantic in every dialect, two are layouts with no meaning outside SPARQL (`metaTopology` and `replaceForm`), seven are parameters and two are without meaning to any store. The three that split fall on each side, and the layout half of `aggregateBoundary` is a third SPARQL layout. No dimension is semantic in one dialect and a layout in another. The nearest case is `firstWrite`, which is semantic everywhere and has a safety motive only on SPARQL.

The line has a cost the sketch did not count. Most of the SPARQL-specific machinery sits below the line, in layouts and parameters that SQL and GQL drop, as [lattice-sql.md](../rdf-engine/lattice-sql.md) §9 found. Above it the semantic dimensions are what the persistence layer is for, where a transaction ends, how a conflict is found, what history is kept, what must be unique, how an identity is formed and how data is erased.

## 7. What follows

- **For MSA-I4.** The four operations take only semantic dimensions as input, with the boundary as split in §4.1. The `-rows`, `-dataset-guard` and receipt suffixes become a semantic choice (receipt model and epoch guard) and a layout (rows form), and only the first reaches the neutral IR.
- **For MSA-Q11.** Holding the rules as data in one registry would carry this table as data, with a class and a dialect column per dimension. The splits of §4 and the repair of §4.6 are ontology changes under ADR-A86 and are proposed with MSA-Q11, not made here.
- **For MSA-I6.** The claim of §4.5, that a shared meta shard costs retries and not safety on a store that detects conflicts per graph.

## 8. Observations outside the question

Recorded for the maintainer, and changed nowhere by this note.

- `providesSingleWriter` and `providesStatementLevelConflictDetection` are loaded by `load_capability_spec` and read by nothing.
- The value of `metaTopology` is read by nothing. `SharedSharded` and `PerAggregate` generate the same operations.
- `DatasetLevelGuard` adds no guard to `unconditional-write`, `cas-replace-value-guard`, the key-claim operations or the audits, and no diagnostic says so.
- TD-118 says the no-receipt builder families have no dataset-guard variant, and `_receipt_variants` in `builders.py` now builds one for each of the six. The debt's blocker may be gone, and whether its witnesses and goldens exist was not checked.
- `dal:recordsStateDigest` is declared an object property and is read as a boolean literal.
