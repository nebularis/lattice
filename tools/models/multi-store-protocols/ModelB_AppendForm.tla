\* SPDX-License-Identifier: MPL-2.0
------------------------------ MODULE ModelB_AppendForm ------------------------------
(***************************************************************************)
(* Model B of FMH-5, the append form: an event appended to a stream under  *)
(* the dataset guard, as the persistence compiler generates                *)
(* append-event-dataset-guard.                                             *)
(*                                                                         *)
(* Each writer reads the dataset epoch, then sends one request meaning     *)
(* "if the dataset epoch is the one I read, and my transaction has no      *)
(* claim, set the stream's row to its sequence plus one under my epoch,    *)
(* write my claim, the receipt at that position and my event". The guards  *)
(* are ordered as the IR orders them: the epoch first, answered Refused    *)
(* EpochMismatch, then the claim, answered Duplicate. The stream's row     *)
(* exists and is never tombstoned here, so its two guards always hold.     *)
(* The request names no expected sequence. The store computes the next.    *)
(*                                                                         *)
(* The constant Isolation selects what the store makes of the request.     *)
(*                                                                         *)
(*   Atomic            the guards and the writes are one atomic step.      *)
(*   SnapshotInsertWW  the guards are evaluated against a snapshot and the *)
(*                     writes commit in a later step. The commit is        *)
(*                     aborted where a transaction committed since the     *)
(*                     snapshot wrote a statement this one writes,         *)
(*                     inserting an identical statement counting as a      *)
(*                     write.                                              *)
(*   SnapshotDeleteWW  as SnapshotInsertWW, but only a statement both      *)
(*                     delete is a conflict. Inserting an identical        *)
(*                     statement is not.                                   *)
(*   SnapshotNoWW      as SnapshotInsertWW, with no conflict detected.     *)
(*                                                                         *)
(* An aborted commit is sent again, up to Retries times, as a caller does  *)
(* with a failure it cannot classify. With Resend, a writer whose append   *)
(* was applied may send the identical request once more, as after a lost   *)
(* reply. With Bump, the dataset epoch is bumped once while writers are    *)
(* live, a transaction of its own.                                         *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    Writers,     \* the writers, model values, each with a transaction id of its own
    Isolation,   \* "Atomic", "SnapshotInsertWW", "SnapshotDeleteWW" or "SnapshotNoWW"
    Bump,        \* whether the dataset epoch is bumped once
    Resend,      \* whether an applied append may be sent once more
    Retries      \* how many times an aborted commit is sent again

ASSUME Isolation \in {"Atomic", "SnapshotInsertWW", "SnapshotDeleteWW", "SnapshotNoWW"}
ASSUME Bump \in BOOLEAN /\ Resend \in BOOLEAN /\ Retries \in Nat

VARIABLES
    dEpoch,     \* the dataset epoch
    row,        \* the stream's version row, [epoch, seq]
    log,        \* the applied appends in commit order, each [w, pos, epoch, at], at the dataset epoch when it applied
    txns,       \* the writers whose transaction claim the store holds
    commits,    \* the statements each committed transaction deleted and inserted, in commit order
    bumped,     \* whether the bump has happened
    pc,         \* per writer: "start", "ready", "evaluated", "replied"
    epochOf,    \* per writer: the dataset epoch it read
    reply,      \* per writer: the outcome it was last answered, or "none"
    snap,       \* per writer: how many transactions had committed when it took its snapshot
    plan,       \* per writer: the outcome and the writes evaluated against its snapshot
    tries,      \* per writer: its aborted commits
    resent      \* per writer: whether it has sent its request again

store == <<dEpoch, row, log, txns>>
vars == <<dEpoch, row, log, txns, commits, bumped, pc, epochOf, reply, snap, plan, tries, resent>>

Outcomes == {"Applied", "Duplicate", "Refused EpochMismatch", "Aborted"}
NoPlan == [out |-> "none", pos |-> 0, dels |-> {}, ins |-> {}]

\* The outcome of w's append against a store at dataset epoch d holding the claims t.
Outcome(w, d, t) ==
    IF d # epochOf[w] THEN "Refused EpochMismatch"
    ELSE IF w \in t THEN "Duplicate"
    ELSE "Applied"

\* The statements an append deletes and inserts, read from the row it found.
\* Each is a pair of a kind and a value, and a kind always takes one type.
Dels(r) == {<<"rowEpoch", r.epoch>>, <<"seq", r.seq>>} \cup (IF r.seq > 0 THEN {<<"head", r.seq>>} ELSE {})
Ins(w, r) == {<<"rowEpoch", epochOf[w]>>, <<"seq", r.seq + 1>>, <<"head", r.seq + 1>>,
              <<"rcpt", r.seq + 1>>, <<"txn", w>>, <<"evt", w>>}

\* The part of a transaction's writes the store compares for a conflict.
Watched(c) ==
    CASE Isolation = "SnapshotInsertWW" -> c.dels \cup c.ins
      [] Isolation = "SnapshotDeleteWW" -> c.dels
      [] OTHER -> {}

Conflicts(w) == {i \in (snap[w] + 1)..Len(commits) : Watched(plan[w]) \cap Watched(commits[i]) # {}} # {}

N == Cardinality(Writers)

TypeOK ==
    /\ dEpoch \in 1..2
    /\ row \in [epoch : 1..2, seq : 0..(2 * N)]
    /\ \A i \in DOMAIN log : log[i] \in [w : Writers, pos : 1..(2 * N), epoch : 1..2, at : 1..2]
    /\ txns \subseteq Writers
    /\ bumped \in BOOLEAN
    /\ pc \in [Writers -> {"start", "ready", "evaluated", "replied"}]
    /\ epochOf \in [Writers -> 0..2]
    /\ reply \in [Writers -> Outcomes \cup {"none"}]
    /\ tries \in [Writers -> 0..Retries]
    /\ resent \in [Writers -> BOOLEAN]

Init ==
    /\ dEpoch = 1
    /\ row = [epoch |-> 1, seq |-> 0]
    /\ log = <<>>
    /\ txns = {}
    /\ commits = <<>>
    /\ bumped = FALSE
    /\ pc = [w \in Writers |-> "start"]
    /\ epochOf = [w \in Writers |-> 0]
    /\ reply = [w \in Writers |-> "none"]
    /\ snap = [w \in Writers |-> 0]
    /\ plan = [w \in Writers |-> NoPlan]
    /\ tries = [w \in Writers |-> 0]
    /\ resent = [w \in Writers |-> FALSE]

\* The writes of w's append taking the position pos.
Apply(w, pos) ==
    /\ row' = [epoch |-> epochOf[w], seq |-> pos]
    /\ log' = Append(log, [w |-> w, pos |-> pos, epoch |-> epochOf[w], at |-> dEpoch])
    /\ txns' = txns \cup {w}

\* The writer reads the dataset epoch it will send.
Read(w) ==
    /\ pc[w] = "start"
    /\ epochOf' = [epochOf EXCEPT ![w] = dEpoch]
    /\ pc' = [pc EXCEPT ![w] = "ready"]
    /\ UNCHANGED <<store, commits, bumped, reply, snap, plan, tries, resent>>

\* Atomic: the guards and the writes in one step.
Exec(w) ==
    /\ Isolation = "Atomic"
    /\ pc[w] = "ready"
    /\ LET o == Outcome(w, dEpoch, txns) IN
         /\ IF o = "Applied" THEN Apply(w, row.seq + 1) ELSE UNCHANGED <<row, log, txns>>
         /\ reply' = [reply EXCEPT ![w] = o]
    /\ pc' = [pc EXCEPT ![w] = "replied"]
    /\ UNCHANGED <<dEpoch, commits, bumped, epochOf, snap, plan, tries, resent>>

\* A snapshot store, first step: the guards and the writes evaluated against the snapshot.
Eval(w) ==
    /\ Isolation # "Atomic"
    /\ pc[w] = "ready"
    /\ plan' = [plan EXCEPT ![w] = [out |-> Outcome(w, dEpoch, txns), pos |-> row.seq + 1,
                                    dels |-> Dels(row), ins |-> Ins(w, row)]]
    /\ snap' = [snap EXCEPT ![w] = Len(commits)]
    /\ pc' = [pc EXCEPT ![w] = "evaluated"]
    /\ UNCHANGED <<store, commits, bumped, epochOf, reply, tries, resent>>

\* Second step: the commit, where no conflict is detected. The writes are those
\* evaluated against the snapshot, whatever the row has become since. A request
\* whose guards failed writes nothing.
Commit(w) ==
    /\ pc[w] = "evaluated"
    /\ IF plan[w].out = "Applied" THEN ~Conflicts(w) ELSE TRUE
    /\ IF plan[w].out = "Applied"
         THEN /\ Apply(w, plan[w].pos)
              /\ commits' = Append(commits, [dels |-> plan[w].dels, ins |-> plan[w].ins])
         ELSE UNCHANGED <<row, log, txns, commits>>
    /\ reply' = [reply EXCEPT ![w] = plan[w].out]
    /\ pc' = [pc EXCEPT ![w] = "replied"]
    /\ plan' = [plan EXCEPT ![w] = NoPlan]
    /\ snap' = [snap EXCEPT ![w] = 0]
    /\ UNCHANGED <<dEpoch, bumped, epochOf, tries, resent>>

\* Second step, where a conflict is detected: the store aborts the commit and
\* writes nothing. The writer sends the same request again, or gives up.
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
    /\ UNCHANGED <<store, commits, bumped, epochOf, resent>>

\* A writer whose append was applied sends the identical request once more.
ResendStep(w) ==
    /\ Resend
    /\ pc[w] = "replied"
    /\ reply[w] = "Applied"
    /\ ~resent[w]
    /\ resent' = [resent EXCEPT ![w] = TRUE]
    /\ pc' = [pc EXCEPT ![w] = "ready"]
    /\ UNCHANGED <<store, commits, bumped, epochOf, reply, snap, plan, tries>>

\* The dataset epoch is bumped, in a transaction of its own.
BumpStep ==
    /\ Bump
    /\ ~bumped
    /\ bumped' = TRUE
    /\ dEpoch' = dEpoch + 1
    /\ commits' = IF Isolation = "Atomic" THEN commits
                  ELSE Append(commits, [dels |-> {<<"depoch", dEpoch>>}, ins |-> {<<"depoch", dEpoch + 1>>}])
    /\ UNCHANGED <<row, log, txns, pc, epochOf, reply, snap, plan, tries, resent>>

Next ==
    \/ BumpStep
    \/ \E w \in Writers : Read(w) \/ Exec(w) \/ Eval(w) \/ Commit(w) \/ Abort(w) \/ ResendStep(w)

Spec == Init /\ [][Next]_vars

(***************************************************************************)
(* OnePerPosition. No two applied appends take one position, so the        *)
(* stream has one receipt for each position.                               *)
(* NoLostAppend. The row's sequence counts the applied appends.            *)
(* FencedAppends. Every applied append carries the dataset epoch in force *)
(* when it applied, so no write sent before a bump lands after it.         *)
(***************************************************************************)
OnePerPosition == \A i, j \in DOMAIN log : i # j => log[i].pos # log[j].pos

NoLostAppend == row.seq = Len(log)

FencedAppends == \A i \in DOMAIN log : log[i].epoch = log[i].at

=============================================================================
