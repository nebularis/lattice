\* SPDX-License-Identifier: MPL-2.0
------------------------------ MODULE ModelC_CreateRace ------------------------------
(***************************************************************************)
(* Model C of FMH-5, the first write of an aggregate, raced by writers     *)
(* that each create it under a transaction id of its own.                  *)
(*                                                                         *)
(* The constant FirstWrite selects the operation, as dal:firstWrite does.  *)
(*                                                                         *)
(*   AbsentRow      create-if-absent. "If my transaction has no claim and *)
(*                  the root has no version row, write the row at seq 1    *)
(*                  with my revision as its head, my claim, the receipt    *)
(*                  and the payload." Answered Duplicate, then Conflict    *)
(*                  Exists. It deletes nothing.                            *)
(*   PreCreatedRow  the row was created at seq 0 when the id was           *)
(*                  allocated (bootstrap-version-row), and the first write *)
(*                  is a guarded replace expecting seq 0. Answered         *)
(*                  Duplicate, then Conflict Missing, then Conflict Stale. *)
(*                  It deletes the row's seq 0.                            *)
(*                                                                         *)
(* The constant Isolation selects what the store makes of the request, as  *)
(* in ModelB_AppendForm: Atomic, SnapshotInsertWW (inserting an identical  *)
(* statement is a write-write conflict), SnapshotDeleteWW (only a          *)
(* statement both delete is) and SnapshotNoWW (nothing is). Two creates    *)
(* insert the same type, epoch and seq statements and different heads.     *)
(*                                                                         *)
(* An aborted commit is sent again, up to Retries times. With Resend, a    *)
(* writer whose write was applied may send it once more.                   *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    Writers,     \* the writers, model values, each with a transaction id and a revision of its own
    Isolation,   \* "Atomic", "SnapshotInsertWW", "SnapshotDeleteWW" or "SnapshotNoWW"
    FirstWrite,  \* "AbsentRow" or "PreCreatedRow"
    Resend,      \* whether an applied write may be sent once more
    Retries      \* how many times an aborted commit is sent again

ASSUME Isolation \in {"Atomic", "SnapshotInsertWW", "SnapshotDeleteWW", "SnapshotNoWW"}
ASSUME FirstWrite \in {"AbsentRow", "PreCreatedRow"}
ASSUME Resend \in BOOLEAN /\ Retries \in Nat

VARIABLES
    row,        \* the root's version row, [exists, seq, heads]. In RDF a row can hold two heads
    log,        \* the applied first writes in commit order, each [w, seq], one receipt each
    txns,       \* the writers whose transaction claim the store holds
    commits,    \* the statements each committed transaction deleted and inserted, in commit order
    pc,         \* per writer: "ready", "evaluated", "replied"
    reply,      \* per writer: the outcome it was last answered, or "none"
    snap,       \* per writer: how many transactions had committed when it took its snapshot
    plan,       \* per writer: the outcome and the writes evaluated against its snapshot
    tries,      \* per writer: its aborted commits
    resent      \* per writer: whether it has sent its request again

store == <<row, log, txns>>
vars == <<row, log, txns, commits, pc, reply, snap, plan, tries, resent>>

Outcomes == {"Applied", "Duplicate", "Conflict Exists", "Conflict Missing", "Conflict Stale", "Aborted"}
NoPlan == [out |-> "none", dels |-> {}, ins |-> {}]

\* The outcome of w's first write against the row r and the claims t, its guards in order.
Outcome(w, r, t) ==
    IF w \in t THEN "Duplicate"
    ELSE IF FirstWrite = "AbsentRow"
         THEN IF r.exists THEN "Conflict Exists" ELSE "Applied"
         ELSE IF ~r.exists THEN "Conflict Missing"
              ELSE IF r.seq # 0 THEN "Conflict Stale" ELSE "Applied"

\* The statements a first write deletes and inserts, each a pair of a kind and a
\* value, a kind always taking one type. The two forms insert the same row
\* statements, the replace after deleting seq 0.
Dels == IF FirstWrite = "AbsentRow" THEN {} ELSE {<<"seq", 0>>}
Ins(w) == {<<"seq", 1>>, <<"head", w>>, <<"txn", w>>, <<"rcpt", w>>, <<"agg", w>>}
          \cup (IF FirstWrite = "AbsentRow" THEN {<<"type", 0>>, <<"epoch", 1>>} ELSE {})

Watched(c) ==
    CASE Isolation = "SnapshotInsertWW" -> c.dels \cup c.ins
      [] Isolation = "SnapshotDeleteWW" -> c.dels
      [] OTHER -> {}

Conflicts(w) == {i \in (snap[w] + 1)..Len(commits) : Watched(plan[w]) \cap Watched(commits[i]) # {}} # {}

TypeOK ==
    /\ row \in [exists : BOOLEAN, seq : 0..1, heads : SUBSET Writers]
    /\ \A i \in DOMAIN log : log[i] \in [w : Writers, seq : {1}]
    /\ txns \subseteq Writers
    /\ pc \in [Writers -> {"ready", "evaluated", "replied"}]
    /\ reply \in [Writers -> Outcomes \cup {"none"}]
    /\ tries \in [Writers -> 0..Retries]
    /\ resent \in [Writers -> BOOLEAN]

Init ==
    /\ row = [exists |-> FirstWrite = "PreCreatedRow", seq |-> 0, heads |-> {}]
    /\ log = <<>>
    /\ txns = {}
    /\ commits = <<>>
    /\ pc = [w \in Writers |-> "ready"]
    /\ reply = [w \in Writers |-> "none"]
    /\ snap = [w \in Writers |-> 0]
    /\ plan = [w \in Writers |-> NoPlan]
    /\ tries = [w \in Writers |-> 0]
    /\ resent = [w \in Writers |-> FALSE]

\* The writes of w's first write. The row reaches seq 1 with w's revision among
\* its heads, beside any head another write left there.
Apply(w) ==
    /\ row' = [exists |-> TRUE, seq |-> 1, heads |-> row.heads \cup {w}]
    /\ log' = Append(log, [w |-> w, seq |-> 1])
    /\ txns' = txns \cup {w}

Exec(w) ==
    /\ Isolation = "Atomic"
    /\ pc[w] = "ready"
    /\ LET o == Outcome(w, row, txns) IN
         /\ IF o = "Applied" THEN Apply(w) ELSE UNCHANGED store
         /\ reply' = [reply EXCEPT ![w] = o]
    /\ pc' = [pc EXCEPT ![w] = "replied"]
    /\ UNCHANGED <<commits, snap, plan, tries, resent>>

Eval(w) ==
    /\ Isolation # "Atomic"
    /\ pc[w] = "ready"
    /\ plan' = [plan EXCEPT ![w] = [out |-> Outcome(w, row, txns), dels |-> Dels, ins |-> Ins(w)]]
    /\ snap' = [snap EXCEPT ![w] = Len(commits)]
    /\ pc' = [pc EXCEPT ![w] = "evaluated"]
    /\ UNCHANGED <<store, commits, reply, tries, resent>>

Commit(w) ==
    /\ pc[w] = "evaluated"
    /\ IF plan[w].out = "Applied" THEN ~Conflicts(w) ELSE TRUE
    /\ IF plan[w].out = "Applied"
         THEN /\ Apply(w)
              /\ commits' = Append(commits, [dels |-> plan[w].dels, ins |-> plan[w].ins])
         ELSE UNCHANGED <<store, commits>>
    /\ reply' = [reply EXCEPT ![w] = plan[w].out]
    /\ pc' = [pc EXCEPT ![w] = "replied"]
    /\ plan' = [plan EXCEPT ![w] = NoPlan]
    /\ snap' = [snap EXCEPT ![w] = 0]
    /\ UNCHANGED <<tries, resent>>

Abort(w) ==
    /\ pc[w] = "evaluated"
    /\ plan[w].out = "Applied"
    /\ Conflicts(w)
    /\ tries' = [tries EXCEPT ![w] = @ + 1]
    /\ IF tries[w] < Retries
         THEN /\ pc' = [pc EXCEPT ![w] = "ready"]
              /\ UNCHANGED reply
         ELSE /\ pc' = [pc EXCEPT ![w] = "replied"]
              /\ reply' = [reply EXCEPT ![w] = "Aborted"]
    /\ plan' = [plan EXCEPT ![w] = NoPlan]
    /\ snap' = [snap EXCEPT ![w] = 0]
    /\ UNCHANGED <<store, commits, resent>>

ResendStep(w) ==
    /\ Resend
    /\ pc[w] = "replied"
    /\ reply[w] = "Applied"
    /\ ~resent[w]
    /\ resent' = [resent EXCEPT ![w] = TRUE]
    /\ pc' = [pc EXCEPT ![w] = "ready"]
    /\ UNCHANGED <<store, commits, reply, snap, plan, tries>>

Next == \E w \in Writers : Exec(w) \/ Eval(w) \/ Commit(w) \/ Abort(w) \/ ResendStep(w)

Spec == Init /\ [][Next]_vars

(***************************************************************************)
(* OneFirstWrite. At most one first write is applied, so the aggregate has *)
(* one receipt at seq 1 and one creator.                                   *)
(* OneHead. The row has at most one head.                                  *)
(***************************************************************************)
OneFirstWrite == Len(log) <= 1

OneHead == Cardinality(row.heads) <= 1

=============================================================================
