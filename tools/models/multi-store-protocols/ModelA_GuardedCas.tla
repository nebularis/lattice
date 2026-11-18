\* SPDX-License-Identifier: MPL-2.0
------------------------------ MODULE ModelA_GuardedCas ------------------------------
(***************************************************************************)
(* Model A of FMH-5, a guarded compare-and-set on one version row.         *)
(*                                                                         *)
(* Each writer reads the version row (seq), then issues one request that   *)
(* means "if seq = expected then seq := expected + 1, apply the payload,   *)
(* write the receipt keyed (target, seq)". The constant Isolation selects  *)
(* what the store makes of that request.                                   *)
(*                                                                         *)
(*   Atomic             the guard and the write are one atomic step, as a  *)
(*                      SPARQL request on a serialisable store or an SQL   *)
(*                      row lock gives.                                    *)
(*   SnapshotNoWWDetect the guard is read from a snapshot in one step and  *)
(*                      the write is committed in a later step, and the    *)
(*                      store does not detect a write-write conflict, so   *)
(*                      the commit is unconditional.                       *)
(*                                                                         *)
(* Each writer makes one attempt. A request whose guard fails changes      *)
(* nothing and its writer is done. The model terminates, so TLC is run     *)
(* with -deadlock.                                                         *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    Writers,     \* the set of writers, model values
    Target,      \* the one target the receipts are keyed on, a model value
    Isolation    \* "Atomic" or "SnapshotNoWWDetect"

ASSUME Isolation \in {"Atomic", "SnapshotNoWWDetect"}

VARIABLES
    seq,        \* the version row
    pc,         \* per writer: "start", "issue", "evaluated", "done"
    expected,   \* per writer: the seq it read before issuing the request
    snapOk,     \* per writer: whether the guard held in its snapshot
    log         \* every applied write in order, each with its receipt key

vars == <<seq, pc, expected, snapOk, log>>

\* The applied write and its receipt, keyed (target, new seq).
Entry(w) == [target |-> Target, writer |-> w,
             exp |-> expected[w], new |-> expected[w] + 1]

TypeOK ==
    /\ seq \in 0..Cardinality(Writers)
    /\ pc \in [Writers -> {"start", "issue", "evaluated", "done"}]
    /\ expected \in [Writers -> 0..Cardinality(Writers)]
    /\ snapOk \in [Writers -> BOOLEAN]
    /\ Len(log) <= Cardinality(Writers)

Init ==
    /\ seq = 0
    /\ pc = [w \in Writers |-> "start"]
    /\ expected = [w \in Writers |-> 0]
    /\ snapOk = [w \in Writers |-> FALSE]
    /\ log = <<>>

\* The client reads the version row in an earlier request.
Read(w) ==
    /\ pc[w] = "start"
    /\ expected' = [expected EXCEPT ![w] = seq]
    /\ pc' = [pc EXCEPT ![w] = "issue"]
    /\ UNCHANGED <<seq, snapOk, log>>

\* Atomic: guard and write in one step.
Cas(w) ==
    /\ Isolation = "Atomic"
    /\ pc[w] = "issue"
    /\ IF seq = expected[w]
         THEN /\ seq' = expected[w] + 1
              /\ log' = Append(log, Entry(w))
         ELSE UNCHANGED <<seq, log>>
    /\ pc' = [pc EXCEPT ![w] = "done"]
    /\ UNCHANGED <<expected, snapOk>>

\* SnapshotNoWWDetect, first step: evaluate the guard against the snapshot.
Eval(w) ==
    /\ Isolation = "SnapshotNoWWDetect"
    /\ pc[w] = "issue"
    /\ snapOk' = [snapOk EXCEPT ![w] = (seq = expected[w])]
    /\ pc' = [pc EXCEPT ![w] = "evaluated"]
    /\ UNCHANGED <<seq, expected, log>>

\* SnapshotNoWWDetect, second step: commit. No write-write conflict is
\* detected, so a request whose snapshot guard held writes whatever the
\* version row has become since.
Commit(w) ==
    /\ pc[w] = "evaluated"
    /\ IF snapOk[w]
         THEN /\ seq' = expected[w] + 1
              /\ log' = Append(log, Entry(w))
         ELSE UNCHANGED <<seq, log>>
    /\ pc' = [pc EXCEPT ![w] = "done"]
    /\ UNCHANGED <<expected, snapOk>>

Next == \E w \in Writers : Read(w) \/ Cas(w) \/ Eval(w) \/ Commit(w)

Spec == Init /\ [][Next]_vars

(***************************************************************************)
(* NoLostUpdate. No two applied writes share an expected seq, and no two   *)
(* receipts share the key (target, seq).                                   *)
(***************************************************************************)
NoLostUpdate ==
    /\ \A i, j \in DOMAIN log :
         i # j => log[i].exp # log[j].exp
    /\ \A i, j \in DOMAIN log :
         i # j => <<log[i].target, log[i].new>> # <<log[j].target, log[j].new>>

=============================================================================
