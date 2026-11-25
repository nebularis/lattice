\* SPDX-License-Identifier: MPL-2.0
------------------------------ MODULE X7_WorkspaceBatch ------------------------------
(***************************************************************************)
(* Model X7, studio writers on one partition taking batches of commands on *)
(* one workspace, and whether the answers agree with what was applied and  *)
(* the commands take effect in the partition's order (MSA-I14, MSA-Q22 and *)
(* MSA-Q23). It adds to X5 a creation, a deletion of the workspace, a      *)
(* batch of several commands planned together, a sender's resend, and what *)
(* a deletion does to the workspace's receipts.                            *)
(*                                                                         *)
(* The workspace is one aggregate, its description, with a version row.    *)
(* Every command writes that aggregate alone, so each is whole under any   *)
(* guard, and X5 is where a command over two aggregates is checked.        *)
(*   Create  applies where the workspace has no row.                       *)
(*   Set     stands for a command that carries no expected revision, a     *)
(*           change of access for example. It applies where the workspace  *)
(*           is live.                                                      *)
(*   DelWs   tombstones the workspace where it is live.                    *)
(*                                                                         *)
(* A writer takes up to BatchMax commands in stream order, reads their     *)
(* receipts, reads the row and plans each command in turn against the      *)
(* state the commands before it in the batch leave. A command with a       *)
(* receipt is skipped, one its own check refuses is answered as not        *)
(* applied, and the rest go in one request, each guarded on the revision   *)
(* it was planned from and on having no receipt. The store applies the     *)
(* request in one step. The writer reads the batch's receipts back, and a  *)
(* command with none is planned again, up to Retries times.                *)
(*                                                                         *)
(* Receipts selects what a deletion of the workspace does to its receipts. *)
(*   Cleared     as built. It removes every receipt of the workspace, and  *)
(*               then writes its own.                                      *)
(*   SpareBatch  it leaves the receipts of the commands in its own batch.  *)
(*   Kept        it removes none.                                          *)
(*                                                                         *)
(* Guard selects the writer's token, as in X5.                             *)
(*   Whole         no token.                                               *)
(*   WholeAnswer   no token, and the read a batch is planned from also     *)
(*                 reads the batch's receipts.                             *)
(*   Fenced        every request carries the writer's epoch, and the store *)
(*                 refuses one that is not the partition's.                *)
(*   FencedAnswer  as Fenced, and the read a batch is planned from also    *)
(*                 reads the epoch and the receipts, so a writer that lost *)
(*                 the partition stops without answering.                  *)
(*                                                                         *)
(* Delivery selects where a writer that starts takes the stream from.     *)
(*   Stream  from the position after the stored offset, as in X1.          *)
(*   Any     from any position, which stands for a broker that redelivers *)
(*           from an offset the store did not give. Batches stay           *)
(*           contiguous.                                                   *)
(*                                                                         *)
(* With Resend the stream ends with a second delivery of command 1 under   *)
(* the same id, as a sender that did not hear the answer sends it.         *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    Guard,       \* "Whole", "WholeAnswer", "Fenced" or "FencedAnswer"
    Delivery,    \* "Stream" or "Any"
    Receipts,    \* "Cleared", "SpareBatch" or "Kept"
    Script,      \* the commands on the stream, "CreateDel", "CreateSetDel", "Sets" or "SetCreate"
    Resend,      \* BOOLEAN, the stream ends with a second delivery of command 1
    Live0,       \* BOOLEAN, the workspace is live at the start, else it has no row
    BatchMax,    \* the most commands in a batch
    NWriters,    \* how many writers start on the partition, one after another
    MaxCrashes,  \* the most crashes in a behaviour
    Retries      \* how many times a batch with a command refused is planned again

ASSUME Guard \in {"Whole", "WholeAnswer", "Fenced", "FencedAnswer"}
ASSUME Delivery \in {"Stream", "Any"}
ASSUME Receipts \in {"Cleared", "SpareBatch", "Kept"}
ASSUME Script \in {"CreateDel", "CreateSetDel", "Sets", "SetCreate"}
ASSUME Resend \in BOOLEAN
ASSUME Live0 \in BOOLEAN
ASSUME BatchMax \in Nat \ {0}
ASSUME NWriters \in Nat \ {0}
ASSUME MaxCrashes \in Nat
ASSUME Retries \in Nat

\* The stream, command c being Commands[c]. A configuration file cannot hold
\* a sequence, so it names one of these.
Commands == CASE Script = "CreateDel" -> <<"Create", "DelWs">>
              [] Script = "CreateSetDel" -> <<"Create", "Set", "DelWs">>
              [] Script = "Sets" -> <<"Set", "Set", "Set">>
              [] Script = "SetCreate" -> <<"Set", "Create">>
K == Len(Commands)
Cmd == 1..K                          \* the command ids
P == IF Resend THEN K + 1 ELSE K     \* the stream's positions
Id(p) == IF p > K THEN 1 ELSE p      \* the command at a position
Name(c) == Commands[c]

Writers == 1..NWriters
Fence == Guard \in {"Fenced", "FencedAnswer"}
Phases == {"off", "idle", "rcpt", "plan", "commit", "offset", "fenced", "dead"}
States == {"absent", "live", "gone"}

VARIABLES
    ws,       \* the workspace, "absent" with no row, "live", or "gone" once tombstoned
    wseq,     \* its row's revision, 0 with no row
    rcpt,     \* the commands that have a receipt
    epoch,    \* the partition's epoch, read under Fenced and FencedAnswer only
    stored,   \* the stored offset
    applied,  \* the commands applied, in the order they took effect. Not in the store
    saidYes,  \* the commands answered as applied, by any writer at any time
    saidNo,   \* the commands answered as not applied
    alive,    \* per writer
    ph,       \* per writer, its phase
    lo,       \* per writer, the first position of the batch in hand, or the next to take
    hi,       \* per writer, the last position of the batch in hand
    has,      \* per writer, the commands of the batch it read a receipt for
    plan,     \* per writer, the batch as planned
    tries,    \* per writer, how many times the batch in hand was planned again
    started,  \* how many writers have started
    crashes   \* how many crashes have happened

store == <<ws, wseq, rcpt, epoch, stored, applied>>
wvars == <<alive, ph, lo, hi, has, plan, tries, started, crashes>>
vars == <<store, wvars, saidYes, saidNo>>

\* A command is planned from a revision the row may never reach, where a
\* writer plans a batch another writer has applied meanwhile.
Entry == [c : Cmd, k : {"skip", "no", "do"}, e : 0..(2 * K + 1)]

TypeOK ==
    /\ ws \in States
    /\ wseq \in 0..(K + 1)
    /\ rcpt \subseteq Cmd
    /\ epoch \in 0..NWriters
    /\ stored \in 0..P
    /\ applied \in Seq(Cmd)
    /\ saidYes \subseteq Cmd
    /\ saidNo \subseteq Cmd
    /\ alive \in [Writers -> BOOLEAN]
    /\ ph \in [Writers -> Phases]
    /\ lo \in [Writers -> 1..(P + 1)]
    /\ hi \in [Writers -> 0..P]
    /\ has \in [Writers -> SUBSET Cmd]
    /\ plan \in [Writers -> Seq(Entry)]
    /\ tries \in [Writers -> 0..Retries]
    /\ started \in 0..NWriters
    /\ crashes \in 0..MaxCrashes

Init ==
    /\ ws = IF Live0 THEN "live" ELSE "absent"
    /\ wseq = IF Live0 THEN 1 ELSE 0
    /\ rcpt = {}
    /\ epoch = 0
    /\ stored = 0
    /\ applied = <<>>
    /\ saidYes = {}
    /\ saidNo = {}
    /\ alive = [w \in Writers |-> FALSE]
    /\ ph = [w \in Writers |-> "off"]
    /\ lo = [w \in Writers |-> 1]
    /\ hi = [w \in Writers |-> 0]
    /\ has = [w \in Writers |-> {}]
    /\ plan = [w \in Writers |-> <<>>]
    /\ tries = [w \in Writers |-> 0]
    /\ started = 0
    /\ crashes = 0

\* The batch in hand, as command ids in stream order, and as a set.
Batch(w) == [i \in 1..(hi[w] - lo[w] + 1) |-> Id(lo[w] + i - 1)]
BatchSet(w) == {Id(p) : p \in lo[w]..hi[w]}

(***************************************************************************)
(* Planning. Each command is planned against the state the commands before *)
(* it in the batch leave, as the writer's own maps give it.                *)
(***************************************************************************)
Allowed(n, st) == IF n = "Create" THEN st = "absent" ELSE st = "live"
After(n, st) == IF n = "Create" THEN "live" ELSE IF n = "DelWs" THEN "gone" ELSE st

RECURSIVE PlanFrom(_, _, _, _)
PlanFrom(s, H, st, rev) ==
    IF s = <<>> THEN <<>>
    ELSE LET c == Head(s) IN
         IF c \in H
           THEN <<[c |-> c, k |-> "skip", e |-> 0]>> \o PlanFrom(Tail(s), H, st, rev)
         ELSE IF ~Allowed(Name(c), st)
           THEN <<[c |-> c, k |-> "no", e |-> 0]>> \o PlanFrom(Tail(s), H, st, rev)
         ELSE <<[c |-> c, k |-> "do", e |-> rev]>>
                  \o PlanFrom(Tail(s), H \cup {c}, After(Name(c), st), rev + 1)

(***************************************************************************)
(* The request. Each planned command applies where the row is at the       *)
(* revision it was planned from and it has no receipt, and writes its      *)
(* receipt with its change.                                                *)
(***************************************************************************)
Effect(c, st, B) ==
    LET moved == [st EXCEPT !.wseq = @ + 1, !.applied = Append(@, c)]
    IN CASE Name(c) = "Create" -> [moved EXCEPT !.ws = "live", !.rcpt = @ \cup {c}]
         [] Name(c) = "Set" -> [moved EXCEPT !.rcpt = @ \cup {c}]
         [] Name(c) = "DelWs" ->
              [moved EXCEPT !.ws = "gone",
                            !.rcpt = CASE Receipts = "Cleared" -> {c}
                                       [] Receipts = "SpareBatch" -> (@ \cap B) \cup {c}
                                       [] Receipts = "Kept" -> @ \cup {c}]

RECURSIVE Apply(_, _, _)
Apply(pl, st, B) ==
    IF pl = <<>> THEN st
    ELSE LET x == Head(pl) IN
         IF x.k = "do" /\ st.wseq = x.e /\ x.c \notin st.rcpt
           THEN Apply(Tail(pl), Effect(x.c, st, B), B)
           ELSE Apply(Tail(pl), st, B)

Kind(pl, k) == {pl[i].c : i \in {j \in DOMAIN pl : pl[j].k = k}}

(***************************************************************************)
(* The writers.                                                            *)
(***************************************************************************)
Start(w) ==
    /\ started = w - 1
    /\ alive' = [alive EXCEPT ![w] = TRUE]
    /\ ph' = [ph EXCEPT ![w] = "idle"]
    /\ \E p \in IF Delivery = "Stream" THEN {stored + 1} ELSE 1..P :
          lo' = [lo EXCEPT ![w] = p]
    /\ epoch' = w
    /\ started' = w
    /\ UNCHANGED <<ws, wseq, rcpt, stored, applied, saidYes, saidNo,
                   hi, has, plan, tries, crashes>>

Take(w) ==
    /\ alive[w]
    /\ ph[w] = "idle"
    /\ lo[w] <= P
    /\ \E n \in 1..BatchMax :
          hi' = [hi EXCEPT ![w] = IF lo[w] + n - 1 > P THEN P ELSE lo[w] + n - 1]
    /\ ph' = [ph EXCEPT ![w] = "rcpt"]
    /\ UNCHANGED <<store, saidYes, saidNo, alive, lo, has, plan, tries, started, crashes>>

ReadReceipts(w) ==
    /\ alive[w]
    /\ ph[w] = "rcpt"
    /\ has' = [has EXCEPT ![w] = rcpt \cap BatchSet(w)]
    /\ ph' = [ph EXCEPT ![w] = "plan"]
    /\ UNCHANGED <<store, saidYes, saidNo, alive, lo, hi, plan, tries, started, crashes>>

\* The writer reads the row and plans the batch. A batch with nothing to
\* write is answered from this read and the receipts read before it. Under
\* WholeAnswer this read takes the receipts as well, and under FencedAnswer
\* the epoch too.
Plan(w) ==
    LET H == IF Guard \in {"WholeAnswer", "FencedAnswer"} THEN rcpt \cap BatchSet(w) ELSE has[w]
        pl == PlanFrom(Batch(w), H, ws, wseq)
    IN
    /\ alive[w]
    /\ ph[w] = "plan"
    /\ IF Guard = "FencedAnswer" /\ epoch # w
         THEN /\ alive' = [alive EXCEPT ![w] = FALSE]
              /\ ph' = [ph EXCEPT ![w] = "fenced"]
              /\ UNCHANGED <<plan, saidYes, saidNo>>
         ELSE IF Kind(pl, "do") = {}
           THEN /\ saidYes' = saidYes \cup Kind(pl, "skip")
                /\ saidNo' = saidNo \cup Kind(pl, "no")
                /\ ph' = [ph EXCEPT ![w] = "offset"]
                /\ UNCHANGED <<alive, plan>>
           ELSE /\ plan' = [plan EXCEPT ![w] = pl]
                /\ ph' = [ph EXCEPT ![w] = "commit"]
                /\ UNCHANGED <<alive, saidYes, saidNo>>
    /\ UNCHANGED <<store, lo, hi, has, tries, started, crashes>>

\* The request and the read of the batch's receipts after it, in one step.
\* A command planned or skipped that has no receipt then makes the writer
\* plan the batch again while it may, and is answered as not applied after.
Commit(w) ==
    LET now == [ws |-> ws, wseq |-> wseq, rcpt |-> rcpt, applied |-> applied]
        st == Apply(plan[w], now, BatchSet(w))
        wanted == Kind(plan[w], "do") \cup Kind(plan[w], "skip")
        missing == wanted \ st.rcpt
    IN
    /\ alive[w]
    /\ ph[w] = "commit"
    /\ IF Fence /\ epoch # w
         THEN /\ alive' = [alive EXCEPT ![w] = FALSE]
              /\ ph' = [ph EXCEPT ![w] = "fenced"]
              /\ UNCHANGED <<ws, wseq, rcpt, applied, saidYes, saidNo, tries>>
         ELSE /\ ws' = st.ws
              /\ wseq' = st.wseq
              /\ rcpt' = st.rcpt
              /\ applied' = st.applied
              /\ UNCHANGED alive
              /\ IF missing # {} /\ tries[w] < Retries
                   THEN /\ ph' = [ph EXCEPT ![w] = "rcpt"]
                        /\ tries' = [tries EXCEPT ![w] = @ + 1]
                        /\ UNCHANGED <<saidYes, saidNo>>
                   ELSE /\ saidYes' = saidYes \cup (wanted \ missing)
                        /\ saidNo' = saidNo \cup Kind(plan[w], "no") \cup missing
                        /\ ph' = [ph EXCEPT ![w] = "offset"]
                        /\ UNCHANGED tries
    /\ UNCHANGED <<epoch, stored, lo, hi, has, plan, started, crashes>>

StoreOffset(w) ==
    /\ alive[w]
    /\ ph[w] = "offset"
    /\ stored' = hi[w]
    /\ lo' = [lo EXCEPT ![w] = hi[w] + 1]
    /\ ph' = [ph EXCEPT ![w] = "idle"]
    /\ has' = [has EXCEPT ![w] = {}]
    /\ plan' = [plan EXCEPT ![w] = <<>>]
    /\ tries' = [tries EXCEPT ![w] = 0]
    /\ UNCHANGED <<ws, wseq, rcpt, epoch, applied, saidYes, saidNo,
                   alive, hi, started, crashes>>

Crash(w) ==
    /\ alive[w]
    /\ crashes < MaxCrashes
    /\ alive' = [alive EXCEPT ![w] = FALSE]
    /\ ph' = [ph EXCEPT ![w] = "dead"]
    /\ has' = [has EXCEPT ![w] = {}]
    /\ plan' = [plan EXCEPT ![w] = <<>>]
    /\ tries' = [tries EXCEPT ![w] = 0]
    /\ crashes' = crashes + 1
    /\ UNCHANGED <<store, saidYes, saidNo, lo, hi, started>>

Next ==
    \E w \in Writers :
        \/ Start(w)
        \/ Take(w)
        \/ ReadReceipts(w)
        \/ Plan(w)
        \/ Commit(w)
        \/ StoreOffset(w)
        \/ Crash(w)

Spec == Init /\ [][Next]_vars

(***************************************************************************)
(* Liveness, for Delivery = "Stream". Weak fairness on each writer's        *)
(* actions but its crash.                                                  *)
(***************************************************************************)
Fairness ==
    \A w \in Writers :
        /\ WF_vars(Start(w))
        /\ WF_vars(Take(w))
        /\ WF_vars(ReadReceipts(w))
        /\ WF_vars(Plan(w))
        /\ WF_vars(Commit(w))
        /\ WF_vars(StoreOffset(w))

FairSpec == Spec /\ Fairness

(***************************************************************************)
(* The requirement.                                                        *)
(***************************************************************************)
Applied == {applied[i] : i \in DOMAIN applied}

\* No command takes effect twice.
AppliedOnce == \A i, j \in DOMAIN applied : i # j => applied[i] # applied[j]

\* R2. A command answered as applied was applied, one answered as not
\* applied was not, then or later, and so no command is answered both ways.
AnswersAgree == saidYes \subseteq Applied /\ saidNo \cap Applied = {}

\* R2 as option (a) of MSA-Q29 restates it. Only an answer of applied is
\* final. A command answered as applied was applied, and none is answered as
\* not applied once it has applied. One answered as not applied may apply
\* later, on a resend.
AppliedIsFinal == saidYes \subseteq Applied
NoRefusalAfterApplied == [][(saidNo' \ saidNo) \cap Applied' = {}]_vars

\* R4. The commands take effect in the order the partition gives them.
PartitionOrder == \A i, j \in DOMAIN applied : i < j => applied[i] < applied[j]

\* Whether the last writer to start has not crashed since.
LastStays == started = NWriters => alive[NWriters]

\* Every command on the stream is answered by someone, as applied or not.
Answered == (saidYes \cup saidNo) = Cmd

\* Where the last writer to start stays alive, every command is eventually
\* answered.
EventuallyAnswered == []LastStays => <>Answered

=============================================================================
