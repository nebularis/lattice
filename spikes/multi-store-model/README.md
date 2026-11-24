<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# `spikes/multi-store-model/`, the multi-store model

A spike. It defines the neutral IR of guarded commands over logical resources as an Isabelle datatype, gives it one function, `exec`, proves the laws below of `exec` and of four commands written in the IR, and exports the interpreter to Scala, which is used as generated. The session is `MultiStoreModel`, `session MultiStoreModel = LatticeBase +`, with `quick_and_dirty = false`. It imports the shared session `LatticeShared` for a position, and never the ledger's session.

The four commands are a create, a delta replace under a patch log, an event append under the dataset guard, and a key claim write. Each is the IR reading of a builder of the persistence compiler: `create-if-absent-named-graph-patch-log`, `cas-replace-named-graph-delta-patch-log`, `append-event-dataset-guard` and `key-claim-write`.

## Building

| Command | What it does | A pass |
|---|---|---|
| `mise run check:proofs -- multi-store-model` | builds the prelude, the shared session and this session, and gates each | `GATE: pass` for `multi-store-model`, with 11 claims passed |
| `mise run check:multi-store-model-replay` | builds and gates the session, exports the interpreter, compiles it with `replay/Replay.scala`, replays the histories of the persistence behaviour tests through it and through the RDF realisation on Oxigraph, compares the state after every command, and times both | `CHECK: pass`, then each engine's version and the two times |

Both need Isabelle as `check:proofs` does. The generated Scala, the compiled classes and the histories file are written under `.build/formal/multi-store-model/`, which git ignores.

| File | Holds |
|---|---|
| `IR.thy` | the datatypes, `exec` and the functions it is made of |
| `Commands.thy` | the four commands as values of the IR |
| `Laws.thy` | the laws, each between gate markers |
| `Export.thy` | `exec` and `replay` at string atoms, and the export to Scala |
| `claims/` | a claim record for each law |
| `replay/histories.py` | the histories, their replay on Oxigraph and the reading of a store back into the model's resources |
| `replay/Replay.scala` | the driver that builds the model's values and calls the generated code |

## `exec`, stated so it can be written again

Everything below is what the theories define. A list of pairs is read through `map_of`: the value of a key is the second part of the first pair whose first part is the key, and a key no pair has has none.

### The names

- A **field** is one of `Epoch`, `Seq`, `Head`, `Deleted`, `Rev`, `Digest`, `Prev`, `TxnOf`, `At`, `Constraint`, `Owner`.
- A **parameter name** is one of `Root`, `Stream`, `EpochP`, `ExpectedSeq`, `NewRev`, `TxnId`, `RequestDigest`, `RevBase`, `ClaimP`, `OwnerP`, `Payload`, `Asserted`, `Retracted`, `EventRows`.
- A **function name** is `RevisionIri`. A **direction** is `Add` or `Del`.
- A **reason** is one of `Exists`, `Missing`, `Tombstoned`, `Stale`, `HeldByOther`, `EpochMismatch`. An **outcome** is `Applied`, `Duplicate`, `Conflict r` or `Refused r` for a reason `r`.

### Values, resources and the state

- A **value** over atoms of a type `a` is `Atom x` for an atom, `Num n` for a position (a natural number, the shared session's `position`), `Flag b` for a boolean, `NoVal`, `Facts xs` for a list of atoms, or `App g vs` for a function name and a list of values. `App` is not computed: the application is the value.
- A **resource** is one of `KAgg v`, `KVRow v`, `KTxn v`, `KRcpt target epoch seq`, `KPatch target epoch seq d`, `KEvt stream seq`, `KClaim v`, `KDEpoch`, each argument a value and `d` a direction. Two resources are equal when their kinds and all their arguments are equal.
- An **entry** is `Entry fields facts`, a list of pairs of a field and a value, and a set of atoms.
- A **state** is a list of pairs of a resource and an entry. **Parameters** are a list of pairs of a parameter name and a value. Two states are the same state when their `map_of` is the same.

### Expressions, guards, effects and commands

- A **key** is `KeyParam x` for a parameter name or `KeyConst v` for a value. A **resource reference** is `RefAgg k`, `RefVRow k`, `RefTxn k`, `RefClaim k` or `RefDEpoch`.
- A **value expression** is `Param x`, `Now`, `Const v`, `Field ref f` for a resource reference and a field, `Succ e`, or `Fn g es` for a function name and a list of value expressions.
- A **resource expression** is `Agg e`, `VRow e`, `Txn e`, `Rcpt e1 e2 e3`, `Patch e1 e2 e3 d`, `Evt e1 e2`, `Claim e` or `DEpoch`, each `e` a value expression.
- A **guard** is `Absent r`, `Present r`, `FieldEq r f e`, `FlagUnset r f` or `NotHeldByOther r f e`, each `r` a resource expression.
- An **effect** is `Put r fs`, `PutFacts r e`, `SetFields r fs`, `Retract r e`, `Assert r e` or `AppendRows r e`, where `fs` is a list of pairs of a field and a value expression.
- A **command** is `Command gs es`, a list of pairs of a guard and an outcome, and a list of effects.

### Reading

Each function takes the state `s` before the command, the clock `t`, a value, and the parameters `ps`.

- `param ps x` is the value of `x` in `ps`, or `NoVal` where `ps` has none.
- `field_of s r f` is the value of `f` in the fields of the entry of `r` in `s`, or `NoVal` where `s` has no entry for `r` or the entry has no `f`.
- `facts_of v` is the set of the atoms of `xs` when `v` is `Facts xs`, and the empty set otherwise.
- A key's value is `param ps x` for `KeyParam x` and `v` for `KeyConst v`. A resource reference names the resource of its kind at its key's value, and `RefDEpoch` names `KDEpoch`.
- `succ_val (Num n)` is `Num (n + 1)`, and `succ_val` of any other value is `NoVal`.
- `eval s t ps e` evaluates a value expression: `Param x` to `param ps x`, `Now` to `t`, `Const v` to `v`, `Field ref f` to `field_of s` of the resource `ref` names and `f`, `Succ e` to `succ_val` of `e`'s value, and `Fn g es` to `App g` of the values of `es` in order.
- `eval_r s t ps r` evaluates a resource expression to the resource of the same kind whose arguments are the values of its value expressions, with a patch keeping its direction.

### Guards

`holds s t ps g`, with `R` the resource `g`'s resource expression evaluates to:

| Guard | Holds when |
|---|---|
| `Absent r` | `s` has no entry for `R` |
| `Present r` | `s` has an entry for `R` |
| `FieldEq r f e` | `field_of s R f` equals the value of `e` |
| `FlagUnset r f` | `field_of s R f` is not `Flag True` |
| `NotHeldByOther r f e` | `field_of s R f` is `NoVal` or equals the value of `e` |

`first_fail s t ps gs` goes through the pairs of `gs` in order and returns the outcome of the first pair whose guard does not hold, or nothing when every guard holds.

### Writing

An effect is evaluated in the state before the command into an **action** on one resource. With `R` its resource expression's value:

| Effect | Action |
|---|---|
| `Put r fs` | put `R` with the fields `fs`, each value expression evaluated |
| `PutFacts r e` | put `R` with the facts `facts_of` of `e`'s value |
| `SetFields r fs` | set the fields `fs` of `R`, each value expression evaluated |
| `Retract r e` | retract `facts_of` of `e`'s value from `R` |
| `Assert r e` | assert `facts_of` of `e`'s value on `R` |
| `AppendRows r e` | the same action as `Assert r e` |

What an action does to the entry of its own resource, `eo` being that entry or nothing, and an absent entry read as `Entry [] {}` where a case needs one:

| Action | The entry afterwards |
|---|---|
| put with fields `fs` | `Entry fs {}` |
| put with facts `F` | `Entry [] F` |
| set fields `fs` | the old fields overridden by `fs`: `fs` followed by every old pair whose field `fs` does not name, and the old facts |
| retract `F` | nothing where there was no entry, otherwise the old fields and the old facts less `F` |
| assert `F` | the old fields, and the old facts with `F` added |

Applying an action to a state changes only the entry of its resource: where the new entry is nothing the state is unchanged, otherwise the state is the pair of the resource and the new entry followed by every other pair of the old state.

`run as s` applies every retraction of `as` in order, then every other action of `as` in order, to `s`.

`exec s t ps c` is, with `c = Command gs es`:

- `(s, o)` when `first_fail s t ps gs` returns `o`,
- `(run as s, Applied)` otherwise, where `as` is each effect of `es` evaluated in `s` with `t` and `ps`, in order.

So every value an effect writes is read from the state before the command, and no effect sees another's write.

`replay s h` runs a history, a list of triples of a clock, parameters and a command, by `exec` in order from `s`, keeping each state and dropping each outcome.

### The four commands

`next_seq x` is `Succ (Field (RefVRow (KeyParam x)) Seq)`, the successor of the sequence of the row the parameter `x` names. `stream_rev` is `Fn RevisionIri [Param RevBase, next_seq Stream]`.

| Command | Guards, in order, each with its outcome | Effects, in order |
|---|---|---|
| `create_if_absent` | `Absent (Txn (Param TxnId))`, `Duplicate`. `Absent (VRow (Param Root))`, `Conflict Exists` | `Put (Txn (Param TxnId))` with `Rev` the parameter `NewRev` and `Digest` the parameter `RequestDigest`. `Put (VRow (Param Root))` with `Epoch` the parameter `EpochP`, `Seq` the constant `Num 1`, `Head` the parameter `NewRev` and `Deleted` the constant `Flag False`. `Assert (Agg (Param Root)) (Param Payload)`. `Put (Rcpt (Param Root) (Param EpochP) (Const (Num 1)))` with `Rev` the parameter `NewRev`, `Prev` the constant `NoVal`, `TxnOf` the parameter `TxnId` and `At` the clock. `PutFacts (Patch (Param Root) (Param EpochP) (Const (Num 1)) Add) (Param Payload)` |
| `delta_replace` | `Absent (Txn (Param TxnId))`, `Duplicate`. `Present (VRow (Param Root))`, `Conflict Missing`. `FlagUnset (VRow (Param Root)) Deleted`, `Conflict Tombstoned`. `FieldEq (VRow (Param Root)) Epoch (Param EpochP)`, `Conflict Stale`. `FieldEq (VRow (Param Root)) Seq (Param ExpectedSeq)`, `Conflict Stale` | `SetFields (VRow (Param Root))` with `Seq` the expression `next_seq Root` and `Head` the parameter `NewRev`. `Retract (Agg (Param Root)) (Param Retracted)`. `Assert (Agg (Param Root)) (Param Asserted)`. `Put (Txn (Param TxnId))` with `Rev` and `Digest` as the create's. `Put (Rcpt (Param Root) (Param EpochP) (next_seq Root))` with `Rev` the parameter `NewRev`, `Prev` the expression `Field (RefVRow (KeyParam Root)) Head`, `TxnOf` the parameter `TxnId` and `At` the clock. `PutFacts (Patch (Param Root) (Param EpochP) (next_seq Root) Add) (Param Asserted)`. `PutFacts (Patch (Param Root) (Param EpochP) (next_seq Root) Del) (Param Retracted)` |
| `append_event` | `FieldEq DEpoch Epoch (Param EpochP)`, `Refused EpochMismatch`. `Absent (Txn (Param TxnId))`, `Duplicate`. `Present (VRow (Param Stream))`, `Conflict Missing`. `FlagUnset (VRow (Param Stream)) Deleted`, `Conflict Tombstoned` | `SetFields (VRow (Param Stream))` with `Epoch` the parameter `EpochP`, `Seq` the expression `next_seq Stream` and `Head` the expression `stream_rev`. `Put (Txn (Param TxnId))` with `Rev` the expression `stream_rev` and `Digest` the parameter `RequestDigest`. `Put (Rcpt (Param Stream) (Param EpochP) (next_seq Stream))` with `Rev` the expression `stream_rev`, `Prev` the expression `Field (RefVRow (KeyParam Stream)) Head`, `TxnOf` the parameter `TxnId` and `At` the clock. `AppendRows (Evt (Param Stream) (next_seq Stream)) (Param EventRows)` |
| `key_claim_write c`, for an atom `c` the deployment gives | `NotHeldByOther (Claim (Param ClaimP)) Owner (Param OwnerP)`, `Conflict HeldByOther` | `Put (Claim (Param ClaimP))` with `Constraint` the constant `Atom c` and `Owner` the parameter `OwnerP` |

A command is **well formed** when no guard's outcome is `Applied`. The four are. `the_commands c` is the set of the four, with `c` for the claim's constraint.

## The laws

Each law is a theorem of `Laws.thy` between gate markers, with its claim record. Every one is proved. `s'` is the state `exec` returns.

| Claim | Theorems | Law |
|---|---|---|
| MM1 | `applied_exactly_when_every_guard_holds`, `otherwise_the_first_failed_guard_decides` | outcomes are total and disjoint. A well-formed command is `Applied` exactly when every guard holds. For any command whose outcome is not `Applied`, the guards split into a prefix whose guards all hold, then a pair whose guard does not hold and whose outcome is the outcome returned, then the rest |
| MM2 | `a_command_not_applied_changes_nothing` | when the outcome is not `Applied`, `s'` is `s` |
| MM3 | `every_value_is_read_before_any_write` | when a well-formed command is `Applied`, `s'` is `run` of its effects each evaluated in `s`, so no effect reads another's write |
| MM4 | `an_asserted_fact_is_present_whatever_is_retracted` | when a well-formed command is `Applied` and has an effect `Assert r e`, every atom of `facts_of` of `e`'s value is in the facts of `r`'s entry in `s'`, whatever the command retracts, provided no `Put` or `PutFacts` of the command evaluates to the same resource as `r` |
| MM5 | `a_resend_is_answered_duplicate_before_any_conflict`, `an_append_sent_again_is_answered_duplicate`, `a_claim_written_again_by_its_owner_changes_nothing` | a resend changes nothing. Once a create or a delta replace is `Applied` with parameters `ps`, a create or a delta replace with any parameters whose `TxnId` is the same, run on `s'` with any clock, returns `s'` and `Duplicate`, whatever row it names. An append `Applied` and run again with the same parameters returns `s'` and `Duplicate`. A claim `Applied` and written again with the same parameters is `Applied` and leaves the same state |
| MM6 | `a_claim_held_by_another_is_refused_and_changes_nothing`, `an_applied_claim_names_its_owner` | a claim has one owner. Where the claim's `Owner` is neither `NoVal` nor the parameter `OwnerP`, the claim write returns `s` and `Conflict HeldByOther`. After an `Applied` claim write, the claim's `Owner` is the parameter `OwnerP` |
| MM7 | `a_tombstoned_row_refuses_a_replace_and_changes_nothing` | where `s` has no entry for the transaction and the row's `Deleted` is `Flag True`, a delta replace returns `s` and `Conflict Tombstoned` |
| MM8 | `a_create_starts_the_sequence_at_one`, `a_replace_moves_the_sequence_to_its_successor`, `an_append_moves_the_sequence_to_its_successor` | the store computes a sequence's successor. After an `Applied` create the row's `Seq` is `Num 1`. Where the row's `Seq` is `Num m` before an `Applied` replace or append, it is `Num (m + 1)` after |
| MM9 | `the_patch_log_holds_the_delta_as_requested` | where the row's `Seq` is `Num m` before an `Applied` delta replace, the entry of `KPatch root epoch (Num (m + 1)) Add` in `s'` is `Entry [] (facts_of (param ps Asserted))`, and that of the same patch with `Del` is `Entry [] (facts_of (param ps Retracted))`, with `root` and `epoch` the parameters `Root` and `EpochP`. The patch log holds the delta as requested, not its effect |
| MM10 | `every_receipt_stays_at_or_below_its_rows_sequence`, `a_receipt_once_written_is_never_replaced`, `the_empty_state_has_its_receipts_below` | one receipt for each target, epoch and sequence. Say a state has its receipts below when every receipt `KRcpt target epoch k` it holds has `k = Num n` with the row of `target` holding `Seq` `Num m` and `n <= m`, and every row it holds has a `Seq` of `Num m` for some `m`. The empty state has its receipts below. Each of the four commands, applied or not, keeps a state's receipts below, and never changes the entry of a receipt the state already holds |
| MM11 | `from_nothing_a_rows_receipts_are_its_positions_one_to_its_sequence` | no gap. Say a state is dense when every receipt it holds is at `Num n` for some `n` and its target has a row, and every row it holds has a `Seq` of `Num m` such that a receipt of that row at `Num n`, at any epoch, exists exactly when `1 <= n <= m`. Every history of the four commands replayed from the empty state ends in a dense state, so position `n` of a row is its `n`-th write |

## What the export is

`Export.thy` defines `exec_literal` and `replay_literal`, `exec` and `replay` with string literals as atoms, and exports them, the four commands, their datatypes with their constructors, and the conversions between natural numbers and the target's integers, with `export_code open ... in Scala (case_insensitive)`. `HOL-Library.Code_Target_Numeral` writes a natural number over the target's integers. `case_insensitive` renames the classes whose names differ only in case, which overwrite each other on a case-insensitive file system, so for example `EpochMismatch` becomes `Epochmismatch` and the datatype `val` becomes `vala`. The driver uses the generated code with no edit. The compiler gives three warnings, all in generated code: two cases of a match on two booleans it cannot reach, and a match on a set that has no case for a cofinite set, which no command writes.

## What the model leaves out

- **A field is read only from a resource named by a parameter or a constant.** The four commands need no more, and it keeps value expressions and resource expressions apart, so neither is defined through the other.
- **Who checks a parameter's datatype.** The generated text checks each parameter's datatype first. The model reads a missing parameter as `NoVal` and checks nothing else.
- **An append of no rows.** On Oxigraph an empty rows slot gives no solution and writes nothing. In the model it moves the sequence and writes a receipt. The caller refuses an empty slot before sending, so no history has one.
- **A receipt's links to its patches.** The RDF receipt names its add and delete graphs, which the model derives from the receipt's key. The time a receipt was recorded and the month of its bucket come from the clock and are not compared.
- **Concurrency.** `exec` is one atomic step. The protocol models check interleavings.

## Design decisions

- The model's proofs are built with no abandonment condition, and the exported interpreter stays plain and is used as generated, as the [multi-store sketch](../../docs/developer/sketches/multi-store-architecture.md) section 3 records.
- A resend is answered before a conflict, the store computes a sequence's successor in both the replace and the append, with the caller's expected value as the guard, and the patch log holds the delta as requested, as the [multi-store plan](../../docs/developer/plans/multi-store-architecture.md) records for 2026-11-18.
- A position is the shared session's, a natural number on a named axis, as [ADR-A-FM2](../../docs/architecture/decisions/ADR-A-FM2-formal-methods-theory-home.md)'s addendum of 2026-11-18 states.
