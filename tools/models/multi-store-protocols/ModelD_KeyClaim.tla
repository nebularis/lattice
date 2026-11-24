\* SPDX-License-Identifier: MPL-2.0
------------------------------ MODULE ModelD_KeyClaim ------------------------------
(***************************************************************************)
(* Model D of FMH-5, the key claim: owners racing for one claim node, as   *)
(* the persistence compiler generates key-claim-write.                     *)
(*                                                                         *)
(* Each owner sends one request meaning "if the claim is held by no owner *)
(* but me, insert the claim's type, its constraint and me as its owner".   *)
(* It is answered Conflict HeldByOther where another owner holds the       *)
(* claim. The request has no transaction claim, so an owner that sends it  *)
(* again is applied again and changes nothing. In RDF a claim can hold two *)
(* owners, and the claim's type and constraint are the same statements     *)
(* whoever inserts them.                                                   *)
(*                                                                         *)
(* The constant Isolation selects what the store makes of the request, as  *)
(* in ModelB_AppendForm. With Sentinel, each claim also rewrites one       *)
(* pre-created counter statement, deleting its value and inserting the     *)
(* next, so that racing claims delete a statement in common. That is the   *)
(* patterns guide's P3, which the generated key-claim-write does not do.   *)
(*                                                                         *)
(* An aborted commit is sent again, up to Retries times. With Resend, an   *)
(* owner whose claim was applied may send it once more.                    *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    Owners,      \* the owners racing for the claim, model values, one request each
    Isolation,   \* "Atomic", "SnapshotInsertWW", "SnapshotDeleteWW" or "SnapshotNoWW"
    Sentinel,    \* whether a claim also rewrites the pre-created counter statement
    Resend,      \* whether an applied claim may be sent once more
    Retries      \* how many times an aborted commit is sent again

ASSUME Isolation \in {"Atomic", "SnapshotInsertWW", "SnapshotDeleteWW", "SnapshotNoWW"}
ASSUME Sentinel \in BOOLEAN /\ Resend \in BOOLEAN /\ Retries \in Nat

VARIABLES
    owners,     \* the owners the claim names. In RDF it can name two
    counter,    \* the sentinel's counter, moved only with Sentinel
    commits,    \* the statements each committed transaction deleted and inserted, in commit order
    pc,         \* per owner: "ready", "evaluated", "replied"
    reply,      \* per owner: the outcome it was last answered, or "none"
    snap,       \* per owner: how many transactions had committed when it took its snapshot
    plan,       \* per owner: the outcome and the writes evaluated against its snapshot
    tries,      \* per owner: its aborted commits
    resent      \* per owner: whether it has sent its request again

store == <<owners, counter>>
vars == <<owners, counter, commits, pc, reply, snap, plan, tries, resent>>

Outcomes == {"Applied", "Conflict HeldByOther", "Aborted"}
NoPlan == [out |-> "none", next |-> 0, dels |-> {}, ins |-> {}]

\* The outcome of o's claim against a claim naming the owners h.
Outcome(o, h) == IF h \subseteq {o} THEN "Applied" ELSE "Conflict HeldByOther"

\* The statements a claim deletes and inserts, with the counter read as n. Each
\* is a pair of a kind and a value, a kind always taking one type.
Dels(n) == IF Sentinel THEN {<<"counter", n>>} ELSE {}
Ins(o, n) == {<<"type", 0>>, <<"constraint", 0>>} \cup {<<"owner", o>>}
             \cup (IF Sentinel THEN {<<"counter", n + 1>>} ELSE {})

Watched(c) ==
    CASE Isolation = "SnapshotInsertWW" -> c.dels \cup c.ins
      [] Isolation = "SnapshotDeleteWW" -> c.dels
      [] OTHER -> {}

Conflicts(o) == {i \in (snap[o] + 1)..Len(commits) : Watched(plan[o]) \cap Watched(commits[i]) # {}} # {}

N == Cardinality(Owners)

TypeOK ==
    /\ owners \subseteq Owners
    /\ counter \in 0..(2 * N)
    /\ pc \in [Owners -> {"ready", "evaluated", "replied"}]
    /\ reply \in [Owners -> Outcomes \cup {"none"}]
    /\ tries \in [Owners -> 0..Retries]
    /\ resent \in [Owners -> BOOLEAN]

Init ==
    /\ owners = {}
    /\ counter = 0
    /\ commits = <<>>
    /\ pc = [o \in Owners |-> "ready"]
    /\ reply = [o \in Owners |-> "none"]
    /\ snap = [o \in Owners |-> 0]
    /\ plan = [o \in Owners |-> NoPlan]
    /\ tries = [o \in Owners |-> 0]
    /\ resent = [o \in Owners |-> FALSE]

\* The writes of o's claim, the counter set to next where there is a sentinel.
Apply(o, next) ==
    /\ owners' = owners \cup {o}
    /\ counter' = IF Sentinel THEN next ELSE counter

Exec(o) ==
    /\ Isolation = "Atomic"
    /\ pc[o] = "ready"
    /\ LET out == Outcome(o, owners) IN
         /\ IF out = "Applied" THEN Apply(o, counter + 1) ELSE UNCHANGED store
         /\ reply' = [reply EXCEPT ![o] = out]
    /\ pc' = [pc EXCEPT ![o] = "replied"]
    /\ UNCHANGED <<commits, snap, plan, tries, resent>>

Eval(o) ==
    /\ Isolation # "Atomic"
    /\ pc[o] = "ready"
    /\ plan' = [plan EXCEPT ![o] = [out |-> Outcome(o, owners), next |-> counter + 1,
                                    dels |-> Dels(counter), ins |-> Ins(o, counter)]]
    /\ snap' = [snap EXCEPT ![o] = Len(commits)]
    /\ pc' = [pc EXCEPT ![o] = "evaluated"]
    /\ UNCHANGED <<store, commits, reply, tries, resent>>

Commit(o) ==
    /\ pc[o] = "evaluated"
    /\ IF plan[o].out = "Applied" THEN ~Conflicts(o) ELSE TRUE
    /\ IF plan[o].out = "Applied"
         THEN /\ Apply(o, plan[o].next)
              /\ commits' = Append(commits, [dels |-> plan[o].dels, ins |-> plan[o].ins])
         ELSE UNCHANGED <<store, commits>>
    /\ reply' = [reply EXCEPT ![o] = plan[o].out]
    /\ pc' = [pc EXCEPT ![o] = "replied"]
    /\ plan' = [plan EXCEPT ![o] = NoPlan]
    /\ snap' = [snap EXCEPT ![o] = 0]
    /\ UNCHANGED <<tries, resent>>

Abort(o) ==
    /\ pc[o] = "evaluated"
    /\ plan[o].out = "Applied"
    /\ Conflicts(o)
    /\ tries' = [tries EXCEPT ![o] = @ + 1]
    /\ IF tries[o] < Retries
         THEN /\ pc' = [pc EXCEPT ![o] = "ready"]
              /\ UNCHANGED reply
         ELSE /\ pc' = [pc EXCEPT ![o] = "replied"]
              /\ reply' = [reply EXCEPT ![o] = "Aborted"]
    /\ plan' = [plan EXCEPT ![o] = NoPlan]
    /\ snap' = [snap EXCEPT ![o] = 0]
    /\ UNCHANGED <<store, commits, resent>>

ResendStep(o) ==
    /\ Resend
    /\ pc[o] = "replied"
    /\ reply[o] = "Applied"
    /\ ~resent[o]
    /\ resent' = [resent EXCEPT ![o] = TRUE]
    /\ pc' = [pc EXCEPT ![o] = "ready"]
    /\ UNCHANGED <<store, commits, reply, snap, plan, tries>>

Next == \E o \in Owners : Exec(o) \/ Eval(o) \/ Commit(o) \/ Abort(o) \/ ResendStep(o)

Spec == Init /\ [][Next]_vars

(***************************************************************************)
(* OneOwner. The claim names at most one owner, so the key is unique.      *)
(***************************************************************************)
OneOwner == Cardinality(owners) <= 1

=============================================================================
