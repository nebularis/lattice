\* SPDX-License-Identifier: MPL-2.0
--------------------------- MODULE X3_ReceiptRelay ---------------------------
(***************************************************************************)
(* Model X3 of MSA-I6, a relay publishing receipts that writers commit     *)
(* into one store.                                                         *)
(*                                                                         *)
(* Each stream has N receipts, seq 1 to N. The writer of a stream is       *)
(* serialised, so it begins receipt q + 1 only after receipt q has         *)
(* committed. Beginning a receipt takes the next position from a global    *)
(* counter, and committing is a later step. Receipts of different streams  *)
(* therefore commit in an order that differs from their positions, which   *)
(* is the late arrival of a transaction that took its position before it   *)
(* committed.                                                              *)
(*                                                                         *)
(* The relay reads committed receipts from the store and publishes them    *)
(* downstream. Relay is "ByCommitPosition" or "PerStreamContiguous".       *)
(*                                                                         *)
(*   ByCommitPosition     the relay keeps a high-water mark and publishes  *)
(*                        the committed receipt with the lowest position   *)
(*                        above it, then moves the mark to that position.  *)
(*   PerStreamContiguous  the relay keeps for each stream the next seq it  *)
(*                        expects and publishes a stream's receipt only    *)
(*                        when it is that one.                             *)
(*                                                                         *)
(* The relay's progress is checkpointed in a separate step. A restart, at  *)
(* most MaxRestarts of them, returns the relay to its last checkpoint, so  *)
(* receipts after it are published again, which is at-least-once.          *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    Relay,         \* "ByCommitPosition" or "PerStreamContiguous"
    Streams,       \* the streams, a set of strings
    N,             \* the number of receipts in each stream
    MaxRestarts    \* the most relay restarts in a behaviour

ASSUME Relay \in {"ByCommitPosition", "PerStreamContiguous"}
ASSUME N \in Nat \ {0}
ASSUME MaxRestarts \in Nat

\* A receipt is the pair <<stream, seq>>.
Receipts == Streams \X (1..N)

VARIABLES
    ph,        \* per receipt: "new", "begun" or "committed"
    pos,       \* per receipt: the position it took, 0 until it begins
    nextPos,   \* the next position to hand out
    pub,       \* the receipts published, in order, duplicates included
    rs,        \* the relay's progress, the high-water mark and the next seqs
    ckpt,      \* the last checkpoint of the relay's progress
    restarts   \* how many times the relay has restarted

vars == <<ph, pos, nextPos, pub, rs, ckpt, restarts>>

Progress0 == [hwm |-> 0, nxt |-> [s \in Streams |-> 1]]

TypeOK ==
    /\ ph \in [Receipts -> {"new", "begun", "committed"}]
    /\ pos \in [Receipts -> 0..(Cardinality(Receipts))]
    /\ nextPos \in 1..(Cardinality(Receipts) + 1)
    /\ pub \in Seq(Receipts)
    /\ rs \in [hwm : 0..(Cardinality(Receipts)),
               nxt : [Streams -> 1..(N + 1)]]
    /\ ckpt \in [hwm : 0..(Cardinality(Receipts)),
                 nxt : [Streams -> 1..(N + 1)]]
    /\ restarts \in 0..MaxRestarts

Init ==
    /\ ph = [r \in Receipts |-> "new"]
    /\ pos = [r \in Receipts |-> 0]
    /\ nextPos = 1
    /\ pub = <<>>
    /\ rs = Progress0
    /\ ckpt = Progress0
    /\ restarts = 0

Committed == {r \in Receipts : ph[r] = "committed"}
Published == {pub[i] : i \in DOMAIN pub}

\* A writer takes a position for the next receipt of its stream. The writer
\* of the stream is serialised, so the previous receipt has committed.
Begin(r) ==
    /\ ph[r] = "new"
    /\ IF r[2] = 1 THEN TRUE ELSE ph[<<r[1], r[2] - 1>>] = "committed"
    /\ ph' = [ph EXCEPT ![r] = "begun"]
    /\ pos' = [pos EXCEPT ![r] = nextPos]
    /\ nextPos' = nextPos + 1
    /\ UNCHANGED <<pub, rs, ckpt, restarts>>

\* The receipt commits into the store, at some time after it took its
\* position.
Commit(r) ==
    /\ ph[r] = "begun"
    /\ ph' = [ph EXCEPT ![r] = "committed"]
    /\ UNCHANGED <<pos, nextPos, pub, rs, ckpt, restarts>>

\* The relay reads the committed receipts above its high-water mark and
\* publishes the one with the lowest position.
RelayByPosition ==
    /\ Relay = "ByCommitPosition"
    /\ LET cand == {r \in Committed : pos[r] > rs.hwm}
       IN /\ cand # {}
          /\ LET r == CHOOSE r \in cand : \A r2 \in cand : pos[r] <= pos[r2]
             IN /\ pub' = Append(pub, r)
                /\ rs' = [rs EXCEPT !.hwm = pos[r]]
    /\ UNCHANGED <<ph, pos, nextPos, ckpt, restarts>>

\* The relay publishes the receipt it expects next for a stream, if it has
\* committed.
RelayPerStream(s) ==
    /\ Relay = "PerStreamContiguous"
    /\ rs.nxt[s] <= N
    /\ ph[<<s, rs.nxt[s]>>] = "committed"
    /\ pub' = Append(pub, <<s, rs.nxt[s]>>)
    /\ rs' = [rs EXCEPT !.nxt[s] = @ + 1]
    /\ UNCHANGED <<ph, pos, nextPos, ckpt, restarts>>

\* The relay stores its progress.
Checkpoint ==
    /\ ckpt # rs
    /\ ckpt' = rs
    /\ UNCHANGED <<ph, pos, nextPos, pub, rs, restarts>>

\* The relay restarts from its last checkpoint, and republishes what it
\* published after it.
Restart ==
    /\ restarts < MaxRestarts
    /\ rs # ckpt
    /\ rs' = ckpt
    /\ restarts' = restarts + 1
    /\ UNCHANGED <<ph, pos, nextPos, pub, ckpt>>

Next ==
    \/ \E r \in Receipts : Begin(r) \/ Commit(r)
    \/ RelayByPosition
    \/ \E s \in Streams : RelayPerStream(s)
    \/ Checkpoint
    \/ Restart

\* Writers and the relay are weakly fair. A checkpoint is not forced, and a
\* restart is never forced.
Fairness ==
    /\ \A r \in Receipts : WF_vars(Begin(r)) /\ WF_vars(Commit(r))
    /\ WF_vars(RelayByPosition)
    /\ \A s \in Streams : WF_vars(RelayPerStream(s))

Spec == Init /\ [][Next]_vars /\ Fairness

(***************************************************************************)
(* The same writers and the per-stream relay, with no position taken. The  *)
(* per-stream relay and R1 to R3 read neither pos nor nextPos, so a        *)
(* behaviour of SpecUnplaced is a behaviour of Spec with the two left at   *)
(* their first values, and the order in which receipts of different        *)
(* streams commit is still free. It has fewer states, since the order in   *)
(* which positions were taken no longer tells two states apart. It is for  *)
(* Relay = "PerStreamContiguous" only. The relay by position reads pos.    *)
(***************************************************************************)
BeginUnplaced(r) ==
    /\ ph[r] = "new"
    /\ IF r[2] = 1 THEN TRUE ELSE ph[<<r[1], r[2] - 1>>] = "committed"
    /\ ph' = [ph EXCEPT ![r] = "begun"]
    /\ UNCHANGED <<pos, nextPos, pub, rs, ckpt, restarts>>

NextUnplaced ==
    \/ \E r \in Receipts : BeginUnplaced(r) \/ Commit(r)
    \/ \E s \in Streams : RelayPerStream(s)
    \/ Checkpoint
    \/ Restart

FairnessUnplaced ==
    /\ \A r \in Receipts : WF_vars(BeginUnplaced(r)) /\ WF_vars(Commit(r))
    /\ \A s \in Streams : WF_vars(RelayPerStream(s))

SpecUnplaced == Init /\ [][NextUnplaced]_vars /\ FairnessUnplaced

(***************************************************************************)
(* R1. Every committed receipt is eventually published.                    *)
(***************************************************************************)
AllPublished ==
    \A r \in Receipts : (ph[r] = "committed") ~> (r \in Published)

(***************************************************************************)
(* R2. Per stream, a receipt is published only after every lower seq of    *)
(* its stream has been, so the first publications of a stream are in seq   *)
(* order with no gap. A second publication of a receipt is allowed.        *)
(***************************************************************************)
PerStreamOrder ==
    \A i \in DOMAIN pub :
        \A q \in 1..(pub[i][2] - 1) :
            \E j \in 1..(i - 1) : pub[j] = <<pub[i][1], q>>

(***************************************************************************)
(* R3. Duplicates are allowed, and nothing uncommitted is published.       *)
(***************************************************************************)
NoUncommittedPublished == Published \subseteq Committed

\* A check that the restart does republish. No receipt is published twice.
\* Expected to fail when MaxRestarts > 0.
NoDuplicate ==
    \A i, j \in DOMAIN pub : pub[i] = pub[j] => i = j

=============================================================================
