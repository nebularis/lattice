<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MSA-I4: four operations lowered to a neutral IR and to SPARQL, SQL and GQL

**Unit:** [`multi-store-architecture`](../../status/multi-store-architecture.md), investigation MSA-I4 of the [sketch](../../sketches/multi-store-architecture.md) §6
**Written:** 2026-11-17, on paper, against the operations the persistence compiler generates for `ontology/persistence/examples/baseline-single-class.ttl` and `append-stream-dataset-guard.ttl` on `spi/sql-backend`
**Placement:** T0, public. Platform configuration, nothing domain-specific
**Builds on:** [MSA-I3](MSA-I3-dimensions-by-dialect.md), whose semantic dimensions are the only inputs here, [lattice-sql.md](../rdf-engine/lattice-sql.md) §9 and [lpg-backend-options.md](../lpg-backend-options.md) §4.3

## 1. The question

The sketch's §4.6 leans towards a neutral IR of guarded commands over logical resources, defined in Isabelle, with SPARQL, SQL and GQL as lowerings. Before the IR is mechanised (MSA-I5), four operations are lowered on paper. The falsifier is that the IR needs a construct only one dialect has, or that a resource has no relational counterpart.

The four operations, and the generated text each is read from:

| Operation | Builder | Generated from |
|---|---|---|
| a create | `create-if-absent-named-graph-patch-log` | `baseline-single-class`, `LoanApplication/create-if-absent.rq` |
| a delta replace under a patch log | `cas-replace-named-graph-delta-patch-log` | `baseline-single-class`, `LoanApplication/cas-replace.rq` |
| an event append | `append-event-dataset-guard` | `append-stream-dataset-guard`, `DecisionStream/append.rq` |
| a key claim write | `key-claim-write` | `baseline-single-class`, `LoanApplication/key-claim-write_loan-application-number-per-branch.rq` |

No ledger operation is lowered. That waits for the ledger's design (sketch §4.14).

## 2. The IR, on paper

Written in the shape it would take as an Isabelle datatype, and not mechanised.

```
resource = Agg root | VRow root | Txn txn | Rcpt target epoch seq | Patch target epoch seq dir
         | Evt stream seq op | Claim claim | DEpoch

value    = Param name | Now | Field resource field | Succ value | Fn fname (value list) | Const literal | None

guard    = Absent resource | Present resource | FieldEq resource field value
         | FlagUnset resource field | NotHeldByOther resource value

effect   = Put resource ((field × value) list)
         | Set resource ((field × value) list)
         | Retract resource facts | Assert resource facts
         | AppendRows resource (row list)

command  = { guards : (guard × outcome) list, effects : effect list }

outcome  = Applied | Duplicate | Conflict reason | Refused reason

exec : state ⇒ clock ⇒ params ⇒ command ⇒ state × outcome
```

Three rules give `exec` its meaning.

- **Guards are ordered.** The first guard that fails decides the outcome, and no effect applies. This makes outcomes total and disjoint, which is one of the laws §4.6 names.
- **Every value is read from the state before the command.** An effect never sees another effect's write. This is SPARQL Update's reading of `DELETE`/`INSERT`/`WHERE`, and the SQL lowering has to keep it (§4.2).
- **`Retract` then `Assert`.** A fact both retracted and asserted is present afterwards, as SPARQL 1.1 says of a `DELETE`/`INSERT`.

`Fn` names a pure function defined once in the theory, such as the revision IRI of a base and a sequence number. `Now` is the store's clock, given to `exec` as an input, so `exec` stays a function.

## 3. The four commands

### 3.1 Create

```
guards  = [ (Absent (Txn $txnId),  Duplicate)
          , (Absent (VRow $root),  Conflict Exists) ]
effects = [ Put (Txn $txnId)            [rev ↦ $newRev, digest ↦ $requestDigest]
          , Put (VRow $root)            [epoch ↦ $epoch, seq ↦ Const 1, head ↦ $newRev, deleted ↦ Const false]
          , Assert (Agg $root)          payload
          , Put (Rcpt $root $epoch 1)   [rev ↦ $newRev, prev ↦ None, txn ↦ $txnId, at ↦ Now]
          , Put (Patch $root $epoch 1 add) payload ]
```

### 3.2 Delta replace under a patch log

```
guards  = [ (Absent (Txn $txnId),                         Duplicate)
          , (Present (VRow $root),                         Conflict Absent)
          , (FlagUnset (VRow $root) deleted,               Conflict Tombstoned)
          , (FieldEq (VRow $root) epoch $epoch,            Conflict Stale)
          , (FieldEq (VRow $root) seq $expectedSeq,        Conflict Stale) ]
effects = [ Set (VRow $root)                 [seq ↦ $nextSeq, head ↦ $newRev]
          , Retract (Agg $root)              retract
          , Assert (Agg $root)               assert
          , Put (Txn $txnId)                 [rev ↦ $newRev, digest ↦ $requestDigest]
          , Put (Rcpt $root $epoch $nextSeq) [rev ↦ $newRev, prev ↦ Field (VRow $root) head, txn ↦ $txnId, at ↦ Now]
          , Put (Patch $root $epoch $nextSeq add) assert
          , Put (Patch $root $epoch $nextSeq del) retract ]
```

### 3.3 Event append, with the dataset guard

```
let n1  = Succ (Field (VRow $stream) seq)
    rev = Fn revisionIri [$revBase, n1]
guards  = [ (FieldEq DEpoch epoch $epoch,           Refused EpochMismatch)
          , (Absent (Txn $txnId),                   Duplicate)
          , (Present (VRow $stream),                Conflict Absent)
          , (FlagUnset (VRow $stream) deleted,      Conflict Tombstoned) ]
effects = [ Set (VRow $stream)                [epoch ↦ $epoch, seq ↦ n1, head ↦ rev]
          , Put (Txn $txnId)                  [rev ↦ rev, digest ↦ $requestDigest]
          , Put (Rcpt $stream $epoch n1)      [rev ↦ rev, prev ↦ Field (VRow $stream) head, txn ↦ $txnId, at ↦ Now]
          , AppendRows (Evt $stream n1)       events ]
```

### 3.4 Key claim write

```
guards  = [ (NotHeldByOther (Claim $claim) $owner, Conflict HeldByOther) ]
effects = [ Put (Claim $claim) [constraint ↦ Const "loan-application-number-per-branch", owner ↦ $owner] ]
```

A second write by the same owner changes nothing and is `Applied`, which is the set semantics SPARQL gives the insertion of a triple already present.

## 4. The lowerings

### 4.1 Each construct in each dialect

The SQL column is PostgreSQL. The GQL column is ISO GQL in form, for a product with explicit transactions and a key constraint on a label, which the capability record has to state (MSA-I3 §5). Each GQL entry is to be checked against the chosen product.

| Construct | SPARQL 1.1 Update | SQL | GQL |
|---|---|---|---|
| a command | one request | one transaction, `BEGIN` to `COMMIT`, rolled back on the first failed guard | one transaction |
| `Absent r` | `FILTER NOT EXISTS` on `r`'s key | `INSERT … ON CONFLICT DO NOTHING` on `r`'s primary key, no row inserted means the guard failed | an insert under a key constraint on `r`'s label, a violation means the guard failed |
| `Present r`, `FieldEq r f v`, `FlagUnset r f` | a pattern in `WHERE` | `SELECT … FOR UPDATE` with the conditions, no row means the guard failed | `MATCH … FILTER …` with the write lock taken before the read ([lpg-backend-options.md](../lpg-backend-options.md) probe P-L1) |
| `NotHeldByOther` | `FILTER NOT EXISTS` with an inequality | `INSERT … ON CONFLICT DO NOTHING`, then the owner read back | an insert under a key constraint, then the owner read back |
| `Field r f` | a variable bound in `WHERE` | a column of the `SELECT … FOR UPDATE`, read before any write | a property read in the `MATCH` |
| `Succ v` | `BIND(STRDT(STR(?n + 1), xsd:long))` | `seq + 1` in the `UPDATE` | `v.seq + 1` in the `SET` |
| `Fn revisionIri` | `CONCAT` and `SUBSTR`, padded to 19 digits | not stored. The row holds the base and the sequence number, and the decode makes the IRI | as SQL |
| `Now` | `NOW()`, once per request | `now()`, once per transaction | the product's current time *(verify)* |
| `Put`, `Set` | triples in `INSERT`, and in `DELETE` for a `Set` | `INSERT`, `UPDATE` | `INSERT`, `SET` |
| `Retract`, `Assert` | `DELETE` then `INSERT` of the payload in the aggregate's graph | `DELETE` then `INSERT … ON CONFLICT DO NOTHING` on the mapped rows | delete and insert of mapped nodes and edges, set semantics kept by the version row's serialisation (§4.3) |
| `AppendRows` | the event rows by `VALUES` | `INSERT … SELECT FROM unnest(…)` | an `INSERT` per row |
| the outcome | a confirmation read after the request, since an Update returns no count | the row counts and the first failed guard | the counts returned |

### 4.2 The SQL text of the delta replace

The one of the four where the order matters. SQL runs statements in order and each sees the last one's writes, so the lowering reads everything the IR reads before writing anything.

```sql
BEGIN;
INSERT INTO txn_claim (txn_id, rev, request_digest)
  VALUES ($txnId, $newRev, $requestDigest) ON CONFLICT (txn_id) DO NOTHING;
-- no row: ROLLBACK, Duplicate
SELECT epoch, seq, head, deleted FROM version_row WHERE root = $root FOR UPDATE;
-- no row: Conflict Absent. deleted: Conflict Tombstoned. epoch or seq differs: Conflict Stale. Each a ROLLBACK
UPDATE version_row SET seq = $nextSeq, head = $newRev WHERE root = $root;
DELETE FROM loan_application_fact WHERE (root, s, p, o) IN (SELECT $root, s, p, o FROM retract_rows);
INSERT INTO loan_application_fact SELECT $root, s, p, o FROM assert_rows ON CONFLICT DO NOTHING;
INSERT INTO receipt (target, epoch, seq, rev, prev_rev, txn_id, recorded_at)
  VALUES ($root, $epoch, $nextSeq, $newRev, :head_read_above, $txnId, now());
INSERT INTO patch (target, epoch, seq, direction, s, p, o)
  SELECT $root, $epoch, $nextSeq, 'add', s, p, o FROM assert_rows
  UNION ALL SELECT $root, $epoch, $nextSeq, 'del', s, p, o FROM retract_rows;
COMMIT;
```

`loan_application_fact` is the fallback of §4.4, a table of the aggregate's facts. Where the family's shape is closed the mapping replaces it with the family's own tables.

### 4.3 The same command in GQL

```
START TRANSACTION
INSERT (:TxnClaim {txn: $txnId, rev: $newRev, digest: $requestDigest})
  -- a violation of the key on TxnClaim.txn: ROLLBACK, Duplicate
MATCH (v:VersionRow {root: $root})
  -- no match: Conflict Absent. Otherwise the guards on deleted, epoch and seq as in SQL
LET prev = v.head
SET v.seq = $nextSeq, v.head = $newRev
  -- the retracted facts deleted, then the asserted ones inserted, by the mapping of G4
INSERT (:Receipt {target: $root, epoch: $epoch, seq: $nextSeq, rev: $newRev, prev: prev, txn: $txnId})
  -- and the patch rows
COMMIT
```

Edges have identity in a property graph and two parallel edges of one type are allowed, so set semantics is a rule the lowering keeps. Within an aggregate it needs no store constraint, because every write to the aggregate passes the version row's guard and so runs one at a time. A read before each insert is enough.

### 4.4 Each resource's relational counterpart

| Resource | Logical key (`contract.py`) | Relational counterpart | Property-graph counterpart |
|---|---|---|---|
| `Aggregate` | root | the family's mapped tables where its shape is closed, otherwise a fact table keyed by root and fact | mapped nodes and edges, or fact nodes |
| `VersionRow` | root | a row keyed by root | properties on a `VersionRow` node keyed by root |
| `TransactionClaim` | transaction id | a row with the id as primary key | a node under a key constraint |
| `Receipt` | target, epoch, seq | a row with that primary key | a node |
| `PatchContent` | target, epoch, seq, direction | rows under that key and the fact | nodes |
| `Event` | stream, seq | a row, whose key needs more than the contract gives (finding MSAI4-04) | a node |
| `KeyClaim` | claim | a row with the claim as primary key | a node under a key constraint |
| `DatasetEpoch` | dataset | one row | one node |

Every resource the four commands touch has a counterpart. The fallback for an aggregate without a closed shape is a fact table, which MSA-I1 found is every family today. It is a counterpart, so the second limb of the falsifier does not fire, and such a family gains little from SQL beyond the version row and the claims.

## 5. Findings

| ID | Finding | Consequence |
|---|---|---|
| MSAI4-01 | Every construct of §2 lowers to all three dialects. GQL's `Absent` needs a key constraint on the label, and its compare-and-set needs the write lock before the read | the capability record gains a key-constraint field (MSA-I3 §5). No construct belongs to one dialect |
| MSAI4-02 | SPARQL reads every value from the state before the request. SQL reads its own writes. The IR states the first, and the SQL lowering reads every needed value with `SELECT … FOR UPDATE` before its first write, and deletes before it inserts | a rule of the SQL lowering, tested by reading the state back into the model after each operation (sketch §4.6) |
| MSAI4-03 | The SPARQL text evaluates its guards together. When two fail, nothing says which outcome it is, and the caller's confirmation read decides | the IR orders its guards, with a resend (`Duplicate`) before a conflict. The SPARQL confirmation read has to follow the same order |
| MSAI4-04 | The `Event` resource's logical key is stream and seq, and one append writes several events under one seq, each with its own `opSeq` and IRI | the key names the append and not an event. A relational primary key needs the event IRI, or `opSeq` where `opSeqRequired` holds. Proposed as a change to `LOGICAL_KEYS` |
| MSAI4-05 | The delta replace takes `$nextSeq` from the caller and checks only its datatype. The append computes its successor in the store | a law that a version row's sequence advances by one cannot be proved of the replace as written. The IR computes `Succ (Field (VRow $root) seq)` or guards that `$nextSeq` is it, a choice for MSA-I5 |
| MSAI4-06 | The patch log records the delta as requested, including a retraction of a fact that was absent and an assertion of one already present | applying the requested delta to the same prior state gives the same result, so a replica stays right. An audit reading the log sees requests, not effects. The IR records the request and says so |
| MSAI4-07 | The revision IRI, the aggregate's graph IRI and the patch graphs' IRIs are computed in the store by SPARQL, because a triple has to hold the IRI | the IR carries them as named functions. SQL and GQL hold the parts and the decode makes the IRI |
| MSAI4-08 | The receipt's time and the month bucket of the log and event graphs come from the store's clock | the time is an input of `exec`. The bucket is a layout (MSA-I3) |
| MSAI4-09 | A native unique index on the aggregate's key columns would enforce the key in the create itself and remove the separate claim | that changes the operation set, so it is not a lowering of `key-claim-write`. The faithful lowering is a claim table, and folding the claim into the create is a semantic choice for later |

## 6. Verdict

The falsifier does not fire. The IR of §2 needs no construct that only one dialect has. Its one requirement beyond the SPARQL fragment in use is a key constraint for GQL, and SQL has its counterpart natively. Every resource has a relational counterpart, with a fact table as the counterpart for an aggregate whose shape is not closed.

The paper exercise found three things the SPARQL text leaves implicit and an IR has to state, the order of the guards (MSAI4-03), whether the patch log holds requests or effects (MSAI4-06) and whether the store or the caller advances the sequence (MSAI4-05). It found one defect in the contract, the event's logical key (MSAI4-04). MSA-I5 mechanises these four commands, and the three choices are put to the maintainer before it does.

## 7. What follows

- **For MSA-I5.** The four commands of §3 with `exec` as §2 defines it, the laws of §4.6 (one receipt for each target, epoch and sequence, a resend that changes nothing, outcomes total and disjoint), and the choice of MSAI4-05.
- **For MSA-I11.** The port's operation is a command id with parameters and a payload of facts, and the outcome is one of §2's four. The confirmation read SPARQL needs is the SPARQL adapter's business.
- **For the maintainer.** MSAI4-03, MSAI4-05 and MSAI4-06 are choices. MSAI4-04 is a defect in `contract.py`'s `LOGICAL_KEYS`, and this note changes no code.
