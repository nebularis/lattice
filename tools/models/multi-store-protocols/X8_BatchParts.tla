\* SPDX-License-Identifier: MPL-2.0
------------------------------ MODULE X8_BatchParts ------------------------------
(***************************************************************************)
(* Model X8, studio writers on one partition taking batches of commands on *)
(* a workspace of two aggregates, and whether the answers agree with what  *)
(* was applied, the commands take effect in the partition's order, and     *)
(* every command is whole (MSA-I14). It is X7 with a second aggregate, one *)
(* part, beside the workspace's description, each with a row state and a   *)
(* revision.                                                               *)
(*   Create    writes the part and the description. It applies where       *)
(*             neither has a row.                                          *)
(*   Set       writes the description alone, where the workspace is live.  *)
(*   SavePart  writes the part alone, where the workspace and the part are *)
(*             live. It carries no expected revision of its own, so its    *)
(*             guard is the part's revision as the plan read it.           *)
(*   DelWs     tombstones the description and the part, where the         *)
(*             workspace is live.                                          *)
(*                                                                         *)
(* A writer takes up to BatchMax commands in stream order, reads their     *)
(* receipts, reads the rows and plans each command in turn against the     *)
(* state and revisions the commands before it in the batch leave. A       *)
(* command with a receipt is skipped, one its own check refuses is         *)
(* answered as not applied, and the rest go in one request. One guard for  *)
(* each command applies it where every aggregate it writes is at the       *)
(* revision the plan gave it and it has no receipt, and it then writes all *)
(* its aggregates and its receipt in the one step. The store applies the   *)
(* request in one step. The writer reads the batch's receipts back, and a *)
(* command with none is planned again, up to Retries times. The per-step   *)
(* guards of the code as built are X5's.                                   *)
(*                                                                         *)
(* Receipts, Guard, Delivery and Resend are as in X7.                      *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    Guard,       \* "Whole", "WholeAnswer", "Fenced" or "FencedAnswer"
    Delivery,    \* "Stream" or "Any"
    Receipts,    \* "Cleared", "SpareBatch" or "Kept"
    Script,      \* the commands on the stream, "CreateSaveDel", "CreateSetSaveDel", "SetSave" or "Sets"
    Resend,      \* BOOLEAN, the stream ends with a second delivery of command 1
    Live0,       \* BOOLEAN, the workspace is live at the start, else it has no row
    BatchMax,    \* the most commands in a batch
    NWriters,    \* how many writers start on the partition, one after another
    MaxCrashes,  \* the most crashes in a behaviour
    Retries      \* how many times a batch with a command refused is planned again

ASSUME Guard \in {"Whole", "WholeAnswer", "Fenced", "FencedAnswer"}
ASSUME Delivery \in {"Stream", "Any"}
ASSUME Receipts \in {"Cleared", "SpareBatch", "Kept"}
ASSUME Script \in {"CreateSaveDel", "CreateSetSaveDel", "SetSave", "Sets"}
ASSUME Resend \in BOOLEAN
ASSUME Live0 \in BOOLEAN
ASSUME BatchMax \in Nat \ {0}
ASSUME NWriters \in Nat \ {0}
ASSUME MaxCrashes \in Nat
ASSUME Retries \in Nat

\* The stream, command c being Commands[c]. A configuration file cannot hold
\* a sequence, so it names one of these.
Commands == CASE Script = "CreateSaveDel" -> <<"Create", "SavePart", "DelWs">>
              [] Script = "CreateSetSaveDel" -> <<"Create", "Set", "SavePart", "DelWs">>
              [] Script = "SetSave" -> <<"Set", "SavePart", "Set">>
              [] Script = "Sets" -> <<"Set", "Set", "SavePart", "Set">>
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
    ws,       \* the description, "absent" with no row, "live", or "gone" once tombstoned
    wseq,     \* its row's revision, 0 with no row
    pt,       \* the part, with the same states
    pseq,     \* its row's revision, 0 with no row
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

store == <<ws, wseq, pt, pseq, rcpt, epoch, stored, applied>>
wvars == <<alive, ph, lo, hi, has, plan, tries, started, crashes>>
vars == <<store, wvars, saidYes, saidNo>>

\* A command is planned from a revision the row may never reach, where a
\* writer plans a batch another writer has applied meanwhile.
Entry == [c : Cmd, k : {"skip", "no", "do"}, e : 0..(2 * K + 1), q : 0..(2 * K + 1)]

TypeOK ==
    /\ ws \in States
    /\ wseq \in 0..(2 * K + 1)
    /\ pt \in States
    /\ pseq \in 0..(2 * K + 1)
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
    /\ pt = IF Live0 THEN "live" ELSE "absent"
    /\ pseq = IF Live0 THEN 1 ELSE 0
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
\* The description and the part are created and tombstoned together, so a plan
\* tracks one state for the workspace and a revision for each aggregate.
Allowed(n, st) == IF n = "Create" THEN st = "absent" ELSE st = "live"
After(n, st) == IF n = "Create" THEN "live" ELSE IF n = "DelWs" THEN "gone" ELSE st
WritesDesc(n) == n \in {"Create", "Set", "DelWs"}
WritesPart(n) == n \in {"Create", "SavePart", "DelWs"}

RECURSIVE PlanFrom(_, _, _, _, _)
PlanFrom(s, H, st, rev, prev) ==
    IF s = <<>> THEN <<>>
    ELSE LET c == Head(s)
             n == Name(c)
         IN
         IF c \in H
           THEN <<[c |-> c, k |-> "skip", e |-> 0, q |-> 0]>> \o PlanFrom(Tail(s), H, st, rev, prev)
         ELSE IF ~Allowed(n, st)
           THEN <<[c |-> c, k |-> "no", e |-> 0, q |-> 0]>> \o PlanFrom(Tail(s), H, st, rev, prev)
         ELSE <<[c |-> c, k |-> "do", e |-> rev, q |-> prev]>>
                  \o PlanFrom(Tail(s), H \cup {c}, After(n, st),
                              IF WritesDesc(n) THEN rev + 1 ELSE rev,
                              IF WritesPart(n) THEN prev + 1 ELSE prev)

(***************************************************************************)
(* The request. Each planned command applies where every aggregate it      *)
(* writes is at the revision it was planned from and it has no receipt,    *)
(* and writes all its aggregates and its receipt in that one step.         *)
(***************************************************************************)
Guarded(x, st) ==
    LET n == Name(x.c) IN
    /\ (WritesDesc(n) => st.wseq = x.e)
    /\ (WritesPart(n) => st.pseq = x.q)
    /\ x.c \notin st.rcpt

Effect(c, st, B) ==
    LET n == Name(c)
        moved == [st EXCEPT !.applied = Append(@, c), !.rcpt = @ \cup {c},
                            !.wseq = IF WritesDesc(n) THEN @ + 1 ELSE @,
                            !.pseq = IF WritesPart(n) THEN @ + 1 ELSE @]
    IN CASE n = "Create" -> [moved EXCEPT !.ws = "live", !.pt = "live"]
         [] n = "Set" -> moved
         [] n = "SavePart" -> moved
         [] n = "DelWs" ->
              [moved EXCEPT !.ws = "gone", !.pt = "gone",
                            !.rcpt = CASE Receipts = "Cleared" -> {c}
                                       [] Receipts = "SpareBatch" -> (st.rcpt \cap B) \cup {c}
                                       [] Receipts = "Kept" -> st.rcpt \cup {c}]

RECURSIVE Apply(_, _, _)
Apply(pl, st, B) ==
    IF pl = <<>> THEN st
    ELSE LET x == Head(pl) IN
         IF x.k = "do" /\ Guarded(x, st)
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
    /\ UNCHANGED <<ws, wseq, pt, pseq, rcpt, stored, applied, saidYes, saidNo,
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
        pl == PlanFrom(Batch(w), H, ws, wseq, pseq)
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
    LET now == [ws |-> ws, wseq |-> wseq, pt |-> pt, pseq |-> pseq, rcpt |-> rcpt, applied |-> applied]
        st == Apply(plan[w], now, BatchSet(w))
        wanted == Kind(plan[w], "do") \cup Kind(plan[w], "skip")
        missing == wanted \ st.rcpt
    IN
    /\ alive[w]
    /\ ph[w] = "commit"
    /\ IF Fence /\ epoch # w
         THEN /\ alive' = [alive EXCEPT ![w] = FALSE]
              /\ ph' = [ph EXCEPT ![w] = "fenced"]
              /\ UNCHANGED <<ws, wseq, pt, pseq, rcpt, applied, saidYes, saidNo, tries>>
         ELSE /\ ws' = st.ws
              /\ wseq' = st.wseq
              /\ pt' = st.pt
              /\ pseq' = st.pseq
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
    /\ UNCHANGED <<ws, wseq, pt, pseq, rcpt, epoch, applied, saidYes, saidNo,
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

\* Every command is whole. The description and the part are both absent, both
\* live or both gone.
WholeCommands == ws = pt

\* The part's revision moved with the deletion, so a save of the part planned
\* before the deletion does not apply after it.
NoSaveAfterDel ==
    \A i, j \in DOMAIN applied :
        i < j => ~(Name(applied[i]) = "DelWs" /\ Name(applied[j]) = "SavePart")

\* R4. The commands take effect in the order the partition gives them.
PartitionOrder == \A i, j \in DOMAIN applied : i < j => applied[i] < applied[j]

=============================================================================
