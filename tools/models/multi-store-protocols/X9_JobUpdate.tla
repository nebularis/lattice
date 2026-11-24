\* SPDX-License-Identifier: MPL-2.0
------------------------------ MODULE X9_JobUpdate ------------------------------
(***************************************************************************)
(* Model X9, the rule that a job which succeeded stays succeeded, and      *)
(* where it is decided (MSA-I14, TD-181).                                  *)
(*                                                                         *)
(* Read from platform/config-studio-core, in                               *)
(* org/nebularis/lattice/studio/writes/Writer.java, on 2026-11-24.         *)
(* jobUpdate reads the job (line 957) and, where the job as read has the   *)
(* status Succeeded and the update does not, returns an ok reply and       *)
(* plans no write, so the update gets no receipt (line 970). Otherwise it  *)
(* plans the receipt first, guarded on the job's owner alone (line 990),   *)
(* and every other operation, which clears the job's graph and inserts the *)
(* update's, is conditional on the command's own receipt (mine, line       *)
(* 1176). Nothing in the request tests the job's status. The comment on    *)
(* the method says a workspace's writes are applied in order, so the check *)
(* cannot race.                                                            *)
(*                                                                         *)
(* One job has a status of queued, running, succeeded or failed, and it    *)
(* starts as running. The partition's stream holds two updates, one to     *)
(* succeeded and one to failed, in the order Order gives. A writer handles *)
(* one command at a time. It reads the command's receipt and a command     *)
(* with one is answered from it. Otherwise it reads the job and plans the  *)
(* update, then sends one request, which the store applies in one step.    *)
(*                                                                         *)
(* Rule selects where the rule is decided.                                 *)
(*   Read   as built. The writer drops an update that would move a         *)
(*          succeeded job to failed, from the job as it read it, and the   *)
(*          request it sends carries no such condition.                    *)
(*   Guard  the condition is in the request's guard as well, so the store  *)
(*          applies an update to failed only where the job is not          *)
(*          succeeded when the request lands.                              *)
(*                                                                         *)
(* Delivery selects how the writers meet the updates, as in X5. Stream     *)
(* takes the stream in order from the stored offset, the last writer's     *)
(* offset winning, and Any takes every update once in any order.           *)
(*                                                                         *)
(* NWriters writers start one after another, each while the one before     *)
(* may still be alive, and any may crash.                                  *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    Rule,        \* "Read" or "Guard"
    Delivery,    \* "Stream" or "Any"
    Order,       \* "SucceedFirst" or "FailFirst", the stream's order
    NWriters,    \* how many writers start on the partition, one after another
    MaxCrashes   \* the most crashes in a behaviour

ASSUME Rule \in {"Read", "Guard"}
ASSUME Delivery \in {"Stream", "Any"}
ASSUME Order \in {"SucceedFirst", "FailFirst"}
ASSUME NWriters \in Nat \ {0}
ASSUME MaxCrashes \in Nat

\* The updates on the stream, update c being Stream[c].
Stream == IF Order = "SucceedFirst" THEN <<"ToSucceeded", "ToFailed">>
          ELSE <<"ToFailed", "ToSucceeded">>
K == Len(Stream)
Cmd == 1..K
Name(c) == Stream[c]
Target(c) == IF Name(c) = "ToSucceeded" THEN "succeeded" ELSE "failed"

Writers == 1..NWriters
Phases == {"off", "idle", "rcpt", "plan", "commit", "offset", "dead"}
Statuses == {"queued", "running", "succeeded", "failed"}

VARIABLES
    status,   \* the job's status
    ever,     \* ghost, whether the job has ever been succeeded. Not in the store
    rcpt,     \* the updates that have a receipt
    stored,   \* the stored offset, read by Stream only
    alive,    \* per writer
    ph,       \* per writer, its phase
    fin,      \* per writer, the updates it has finished
    cur,      \* per writer, the update in hand, 0 for none
    rd,       \* per writer, the status it read when it planned
    started,  \* how many writers have started
    crashes   \* how many crashes have happened

store == <<status, ever, rcpt, stored>>
wvars == <<alive, ph, fin, cur, rd, started, crashes>>
vars == <<store, wvars>>

TypeOK ==
    /\ status \in Statuses
    /\ ever \in BOOLEAN
    /\ rcpt \subseteq Cmd
    /\ stored \in 0..K
    /\ alive \in [Writers -> BOOLEAN]
    /\ ph \in [Writers -> Phases]
    /\ fin \in [Writers -> SUBSET Cmd]
    /\ cur \in [Writers -> 0..K]
    /\ rd \in [Writers -> Statuses]
    /\ started \in 0..NWriters
    /\ crashes \in 0..MaxCrashes

Init ==
    /\ status = "running"
    /\ ever = FALSE
    /\ rcpt = {}
    /\ stored = 0
    /\ alive = [w \in Writers |-> FALSE]
    /\ ph = [w \in Writers |-> "off"]
    /\ fin = [w \in Writers |-> {}]
    /\ cur = [w \in Writers |-> 0]
    /\ rd = [w \in Writers |-> "running"]
    /\ started = 0
    /\ crashes = 0

Start(w) ==
    /\ started = w - 1
    /\ alive' = [alive EXCEPT ![w] = TRUE]
    /\ ph' = [ph EXCEPT ![w] = "idle"]
    /\ fin' = [fin EXCEPT ![w] = IF Delivery = "Stream" THEN 1..stored ELSE {}]
    /\ started' = w
    /\ UNCHANGED <<store, cur, rd, crashes>>

Ready(w) ==
    IF Delivery = "Stream"
      THEN {c \in Cmd \ fin[w] : \A d \in Cmd \ fin[w] : c <= d}
      ELSE Cmd \ fin[w]

Take(w) ==
    /\ alive[w]
    /\ ph[w] = "idle"
    /\ \E c \in Ready(w) :
          /\ cur' = [cur EXCEPT ![w] = c]
          /\ ph' = [ph EXCEPT ![w] = "rcpt"]
    /\ UNCHANGED <<store, alive, fin, rd, started, crashes>>

\* The writer reads the update's receipt. An update with one is answered
\* from it.
ReadReceipt(w) ==
    /\ alive[w]
    /\ ph[w] = "rcpt"
    /\ ph' = [ph EXCEPT ![w] = IF cur[w] \in rcpt THEN "offset" ELSE "plan"]
    /\ UNCHANGED <<store, alive, fin, cur, rd, started, crashes>>

\* The writer reads the job. Where the job as read has succeeded and the
\* update would move it to failed, the update is dropped, with no request and
\* no receipt, as built. Otherwise the update is planned.
Plan(w) ==
    /\ alive[w]
    /\ ph[w] = "plan"
    /\ rd' = [rd EXCEPT ![w] = status]
    /\ ph' = [ph EXCEPT ![w] =
              IF status = "succeeded" /\ Name(cur[w]) = "ToFailed" THEN "offset" ELSE "commit"]
    /\ UNCHANGED <<store, alive, fin, cur, started, crashes>>

\* The request. It applies where the update has no receipt, and under Guard
\* where the update does not move a succeeded job to failed, and it then
\* writes the receipt and the update's status. The writer answers either way.
Commit(w) ==
    LET c == cur[w]
        ok == /\ c \notin rcpt
              /\ (Rule = "Guard" => ~(status = "succeeded" /\ Name(c) = "ToFailed"))
    IN
    /\ alive[w]
    /\ ph[w] = "commit"
    /\ status' = IF ok THEN Target(c) ELSE status
    /\ ever' = (ever \/ (ok /\ Target(c) = "succeeded"))
    /\ rcpt' = IF ok THEN rcpt \cup {c} ELSE rcpt
    /\ ph' = [ph EXCEPT ![w] = "offset"]
    /\ UNCHANGED <<stored, alive, fin, cur, rd, started, crashes>>

\* The writer has finished the update. Under Stream it stores the offset.
StoreOffset(w) ==
    /\ alive[w]
    /\ ph[w] = "offset"
    /\ stored' = IF Delivery = "Stream" THEN cur[w] ELSE stored
    /\ fin' = [fin EXCEPT ![w] = @ \cup {cur[w]}]
    /\ ph' = [ph EXCEPT ![w] = "idle"]
    /\ cur' = [cur EXCEPT ![w] = 0]
    /\ rd' = [rd EXCEPT ![w] = "running"]
    /\ UNCHANGED <<status, ever, rcpt, alive, started, crashes>>

Crash(w) ==
    /\ alive[w]
    /\ crashes < MaxCrashes
    /\ alive' = [alive EXCEPT ![w] = FALSE]
    /\ ph' = [ph EXCEPT ![w] = "dead"]
    /\ cur' = [cur EXCEPT ![w] = 0]
    /\ rd' = [rd EXCEPT ![w] = "running"]
    /\ crashes' = crashes + 1
    /\ UNCHANGED <<store, fin, started>>

Next ==
    \E w \in Writers :
        \/ Start(w)
        \/ Take(w)
        \/ ReadReceipt(w)
        \/ Plan(w)
        \/ Commit(w)
        \/ StoreOffset(w)
        \/ Crash(w)

Spec == Init /\ [][Next]_vars

(***************************************************************************)
(* The requirement. A job that was ever succeeded is never failed.         *)
(***************************************************************************)
SucceededStays == ever => status # "failed"

=============================================================================
