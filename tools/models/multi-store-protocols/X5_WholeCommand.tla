\* SPDX-License-Identifier: MPL-2.0
------------------------------ MODULE X5_WholeCommand ------------------------------
(***************************************************************************)
(* Model X5, studio writers on one partition, and whether every state     *)
(* they reach is one that some sequence of whole commands gives.           *)
(*                                                                         *)
(* One workspace has two aggregates, its description and one document,     *)
(* each with a version row. The description lists the document. The       *)
(* partition's stream holds a deletion of the document, which writes both  *)
(* aggregates, and a save of one of them, which is a save of the         *)
(* document, a save of the description alone (a change of access, for     *)
(* example), or both.                                                      *)
(*                                                                         *)
(* A writer handles one command at a time. It reads the command's receipt, *)
(* and a command with one is answered from it. Otherwise it reads the rows *)
(* and plans the command's steps, or answers without writing where the     *)
(* command's own check fails. It then sends one request, which the store   *)
(* applies in one step, and reads the receipt back to answer.              *)
(*                                                                         *)
(* Guard selects the design.                                               *)
(*   PerStep  as built. Each step is guarded on its own row's revision and *)
(*            on its own transaction having no claim, and writes the claim *)
(*            where it applies. The receipt is guarded on one step's      *)
(*            claim, a deletion's on its description step and a save's on *)
(*            its only step. A deletion whose receipt is present after its *)
(*            request, or that is answered from its receipt, tombstones a  *)
(*            document row still live in a later request, then answers.   *)
(*   Whole    one guard over every row the command writes, so the request  *)
(*            applies every step and the receipt or nothing. A refused     *)
(*            command is planned again from fresh reads, up to Retries     *)
(*            times, and is then answered as not applied.                  *)
(*   Fenced   as Whole, and every request also carries the writer's epoch, *)
(*            which the store refuses unless it is the partition's. A      *)
(*            writer that starts on the partition sets the epoch, and a    *)
(*            writer refused for its epoch stops.                          *)
(*   FencedAnswer  as Fenced, and a command refused by its own check,     *)
(*            which sends no request, is answered from the same read as    *)
(*            its rows, which also reads the partition's epoch and the     *)
(*            command's receipt. A writer that reads another epoch stops   *)
(*            without answering, and one that reads the receipt answers    *)
(*            from it.                                                     *)
(*   WholeAnswer  as FencedAnswer with no epoch anywhere. A command refused  *)
(*            by its own check is answered from the same read as its rows, *)
(*            which also reads the command's receipt, and one that has a   *)
(*            receipt is answered from it.                                 *)
(*                                                                         *)
(* The document's patch log is a graph that exists at the start. Under     *)
(* PerStep a deletion's request removes it with no condition, whatever its *)
(* guards do (TD-180). Under every other guard the request removes it only *)
(* where the command's receipt is written.                                 *)
(*                                                                         *)
(* Delivery selects how the writers meet the commands.                     *)
(*   Stream   as in X1. Each writer takes the stream in order from the     *)
(*            offset stored when it started, and stores the offset of each *)
(*            command it finishes, as applied, the last writer winning.    *)
(*   Any      each writer takes every command once, in any order. This     *)
(*            stands for two writers that do not share one order.          *)
(*                                                                         *)
(* NWriters writers start one after another, each while the one before    *)
(* may still be alive, which is the takeover of MSAI9-01, and any may      *)
(* crash.                                                                  *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    Guard,       \* "PerStep", "Whole", "Fenced", "FencedAnswer" or "WholeAnswer"
    Delivery,    \* "Stream" or "Any"
    Saves,       \* the saves on the stream, a non-empty subset of {"SaveDoc", "SaveDesc"}
    DelFirst,    \* BOOLEAN, the deletion is first on the stream, else last
    NWriters,    \* how many writers start on the partition, one after another
    MaxCrashes,  \* the most crashes in a behaviour
    Retries      \* how many times a refused command is planned again, all but PerStep

ASSUME Guard \in {"PerStep", "Whole", "Fenced", "FencedAnswer", "WholeAnswer"}
ASSUME Delivery \in {"Stream", "Any"}
ASSUME Saves \subseteq {"SaveDoc", "SaveDesc"} /\ Saves # {}
ASSUME DelFirst \in BOOLEAN
ASSUME NWriters \in Nat \ {0}
ASSUME MaxCrashes \in Nat
ASSUME Retries \in Nat

SaveSeq == IF Saves = {"SaveDoc", "SaveDesc"} THEN <<"SaveDoc", "SaveDesc">>
           ELSE IF Saves = {"SaveDoc"} THEN <<"SaveDoc">> ELSE <<"SaveDesc">>

\* The partition's stream, command c being Stream[c].
Stream == IF DelFirst THEN <<"Del">> \o SaveSeq ELSE SaveSeq \o <<"Del">>
K == Len(Stream)
Cmd == 1..K
Name(c) == Stream[c]

Writers == 1..NWriters

\* Whether every request carries the writer's epoch.
Fence == Guard \in {"Fenced", "FencedAnswer"}
Phases == {"off", "idle", "rcpt", "plan", "commit", "finish", "offset", "fenced", "dead"}

\* What a writer read when it planned, which is the description's revision, whether
\* the description lists the document, and the document's revision as the
\* writer sees it, which is 0 where the document is not listed or its row is
\* tombstoned, since the workspace is read through its description.
NoRead == [d |-> 0, l |-> FALSE, r |-> 0]

VARIABLES
    dseq,     \* the description's revision
    listed,   \* whether the description lists the document
    docseq,   \* the document's revision
    live,     \* whether the document's row is live, FALSE once tombstoned
    claims,   \* the transactions that have a claim, as <<command, step>>
    rcpt,     \* the commands that have a receipt
    rwrote,   \* the deletions whose receipt names the document's graph
    haslog,   \* whether the document's patch log exists
    epoch,    \* the partition's epoch, read under Fenced and FencedAnswer only
    stored,   \* the stored offset, read by Stream only
    alive,    \* per writer
    ph,       \* per writer, its phase
    fin,      \* per writer, the commands it has finished
    cur,      \* per writer, the command in hand, 0 for none
    rd,       \* per writer, what it read when it planned
    tries,    \* per writer, how many times the command in hand was planned again
    started,  \* how many writers have started
    crashes,  \* how many crashes have happened
    saidNo   \* the commands answered as not applied, by any writer at any time

store == <<dseq, listed, docseq, live, claims, rcpt, rwrote, haslog, epoch, stored>>
wvars == <<alive, ph, fin, cur, rd, tries, started, crashes>>
vars == <<store, wvars, saidNo>>

TypeOK ==
    /\ dseq \in 1..(K + 1)
    /\ listed \in BOOLEAN
    /\ docseq \in 1..(K + 2)
    /\ live \in BOOLEAN
    /\ claims \subseteq (Cmd \X {1, 2})
    /\ rcpt \subseteq Cmd
    /\ rwrote \subseteq Cmd
    /\ haslog \in BOOLEAN
    /\ epoch \in 0..NWriters
    /\ stored \in 0..K
    /\ alive \in [Writers -> BOOLEAN]
    /\ ph \in [Writers -> Phases]
    /\ fin \in [Writers -> SUBSET Cmd]
    /\ cur \in [Writers -> 0..K]
    /\ tries \in [Writers -> 0..Retries]
    /\ started \in 0..NWriters
    /\ crashes \in 0..MaxCrashes
    /\ saidNo \subseteq Cmd

Init ==
    /\ dseq = 1
    /\ listed = TRUE
    /\ docseq = 1
    /\ live = TRUE
    /\ claims = {}
    /\ rcpt = {}
    /\ rwrote = {}
    /\ haslog = TRUE
    /\ epoch = 0
    /\ stored = 0
    /\ alive = [w \in Writers |-> FALSE]
    /\ ph = [w \in Writers |-> "off"]
    /\ fin = [w \in Writers |-> {}]
    /\ cur = [w \in Writers |-> 0]
    /\ rd = [w \in Writers |-> NoRead]
    /\ tries = [w \in Writers |-> 0]
    /\ started = 0
    /\ crashes = 0
    /\ saidNo = {}

(***************************************************************************)
(* The writers' lifecycle.                                                 *)
(***************************************************************************)

\* A writer starts on the partition. The next may start while the one before
\* is alive. Under Stream it resumes from the stored offset, and under Any it
\* takes every command. It sets the partition's epoch to its own number.
Start(w) ==
    /\ started = w - 1
    /\ alive' = [alive EXCEPT ![w] = TRUE]
    /\ ph' = [ph EXCEPT ![w] = "idle"]
    /\ fin' = [fin EXCEPT ![w] = IF Delivery = "Stream" THEN 1..stored ELSE {}]
    /\ epoch' = w
    /\ started' = w
    /\ UNCHANGED <<dseq, listed, docseq, live, claims, rcpt, rwrote, haslog, stored,
                   cur, rd, tries, crashes, saidNo>>

\* The commands a writer may take next.
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
    /\ UNCHANGED <<store, alive, fin, rd, tries, started, crashes, saidNo>>

\* A command is answered as not applied.
AnswerNo(w) == saidNo' = saidNo \cup {cur[w]}

\* The writer reads the command's receipt. A command with one is answered
\* from it. As built, a deletion answered from its receipt goes on to remove
\* the document's row where its receipt names the document's graph.
ReadReceipt(w) ==
    /\ alive[w]
    /\ ph[w] = "rcpt"
    /\ ph' = [ph EXCEPT ![w] =
              IF cur[w] \in rcpt
                THEN IF Guard = "PerStep" /\ Name(cur[w]) = "Del" /\ cur[w] \in rwrote
                       THEN "finish" ELSE "offset"
                ELSE "plan"]
    /\ UNCHANGED <<store, alive, fin, cur, rd, tries, started, crashes, saidNo>>

\* The document's revision as the writer reads it through the description.
DocRev == IF listed /\ live THEN docseq ELSE 0

\* The command's own check. A save of the document expects revision 1, the
\* revision its sender read, and is answered stale otherwise. A deletion of a
\* document the description does not list is answered not found.
Refused(c) ==
    \/ Name(c) = "SaveDoc" /\ DocRev # 1
    \/ Name(c) = "Del" /\ ~listed

\* The writer reads the rows and plans the command, or answers it without a
\* request where the command's own check fails. Under FencedAnswer the same
\* read takes the partition's epoch and the command's receipt, so a writer
\* that has lost the partition stops without answering, and a command applied
\* meanwhile is answered from its receipt.
Plan(w) ==
    /\ alive[w]
    /\ ph[w] = "plan"
    /\ IF Refused(cur[w])
         THEN IF Guard = "FencedAnswer" /\ epoch # w
                THEN /\ alive' = [alive EXCEPT ![w] = FALSE]
                     /\ ph' = [ph EXCEPT ![w] = "fenced"]
                     /\ UNCHANGED <<rd, saidNo>>
              ELSE IF Guard \in {"FencedAnswer", "WholeAnswer"} /\ cur[w] \in rcpt
                THEN /\ ph' = [ph EXCEPT ![w] = "offset"]
                     /\ UNCHANGED <<alive, rd, saidNo>>
              ELSE /\ AnswerNo(w)
                   /\ ph' = [ph EXCEPT ![w] = "offset"]
                   /\ UNCHANGED <<alive, rd>>
         ELSE /\ rd' = [rd EXCEPT ![w] = [d |-> dseq, l |-> listed, r |-> DocRev]]
              /\ ph' = [ph EXCEPT ![w] = "commit"]
              /\ UNCHANGED <<alive, saidNo>>
    /\ UNCHANGED <<store, fin, cur, tries, started, crashes>>

(***************************************************************************)
(* The request. Step <<c, 1>> of a deletion is its description step and    *)
(* <<c, 2>> its tombstone of the document, which it plans only where it    *)
(* read the document live. A save has one step, <<c, 1>>.                  *)
(***************************************************************************)

\* Whether each step's guard holds against the store as the request finds it.
\* The description step and the document step touch different rows, so the
\* order of the steps within the request does not change either guard.
DescOk(w) == dseq = rd[w].d /\ <<cur[w], 1>> \notin claims
DocOk(w, n) == docseq = rd[w].r /\ <<cur[w], n>> \notin claims

\* The request as built, where each step applies where its own guard holds.
CommitPerStep(w) ==
    LET c == cur[w]
        r == rd[w]
        descStep == Name(c) \in {"Del", "SaveDesc"} /\ DescOk(w)
        docStep ==
            \/ Name(c) = "SaveDoc" /\ DocOk(w, 1)
            \/ Name(c) = "Del" /\ r.r > 0 /\ DocOk(w, 2)
        docN == IF Name(c) = "Del" THEN 2 ELSE 1
        claims1 == claims \cup (IF descStep THEN {<<c, 1>>} ELSE {})
                          \cup (IF docStep THEN {<<c, docN>>} ELSE {})
        receipted == <<c, 1>> \in claims1
    IN
    /\ dseq' = IF descStep THEN dseq + 1 ELSE dseq
    /\ listed' = IF descStep THEN (IF Name(c) = "Del" THEN FALSE ELSE r.l) ELSE listed
    /\ docseq' = IF docStep THEN docseq + 1 ELSE docseq
    /\ live' = IF docStep /\ Name(c) = "Del" THEN FALSE ELSE live
    /\ claims' = claims1
    /\ rcpt' = IF receipted THEN rcpt \cup {c} ELSE rcpt
    /\ rwrote' = IF receipted /\ Name(c) = "Del" /\ r.r > 0 THEN rwrote \cup {c} ELSE rwrote
    \* The log drops carry no guard, so a deletion's request removes the log.
    /\ haslog' = IF Name(c) = "Del" THEN FALSE ELSE haslog
    \* A deletion whose receipt is present goes on to remove a row its
    \* tombstone lost, before it answers. Any other command answers now.
    /\ IF receipted
         THEN /\ ph' = [ph EXCEPT ![w] =
                        IF Name(c) = "Del" /\ r.r > 0 THEN "finish" ELSE "offset"]
              /\ UNCHANGED saidNo
         ELSE /\ AnswerNo(w)
              /\ ph' = [ph EXCEPT ![w] = "offset"]
    /\ UNCHANGED <<tries>>

\* The request under one guard, which applies every step and the receipt, or
\* nothing.
CommitWhole(w) ==
    LET c == cur[w]
        r == rd[w]
        hasDoc == Name(c) = "SaveDoc" \/ (Name(c) = "Del" /\ r.r > 0)
        hasDesc == Name(c) \in {"Del", "SaveDesc"}
        docN == IF Name(c) = "Del" THEN 2 ELSE 1
        ok == /\ (hasDesc => DescOk(w))
              /\ (hasDoc => DocOk(w, docN))
    IN
    /\ dseq' = IF ok /\ hasDesc THEN dseq + 1 ELSE dseq
    /\ listed' = IF ok /\ hasDesc THEN (IF Name(c) = "Del" THEN FALSE ELSE r.l) ELSE listed
    /\ docseq' = IF ok /\ hasDoc THEN docseq + 1 ELSE docseq
    /\ live' = IF ok /\ hasDoc /\ Name(c) = "Del" THEN FALSE ELSE live
    /\ claims' = IF ok
                   THEN claims \cup (IF hasDesc THEN {<<c, 1>>} ELSE {})
                               \cup (IF hasDoc THEN {<<c, docN>>} ELSE {})
                   ELSE claims
    /\ rcpt' = IF ok THEN rcpt \cup {c} ELSE rcpt
    /\ UNCHANGED rwrote
    \* The log drops are guarded on the receipt, which the request writes or not.
    /\ haslog' = IF ok /\ Name(c) = "Del" THEN FALSE ELSE haslog
    \* The receipt read back decides the answer. A command refused whole is
    \* planned again from fresh reads, from its receipt on, while it may.
    /\ IF c \in rcpt'
         THEN /\ ph' = [ph EXCEPT ![w] = "offset"]
              /\ UNCHANGED <<tries, saidNo>>
         ELSE IF tries[w] < Retries
                THEN /\ ph' = [ph EXCEPT ![w] = "rcpt"]
                     /\ tries' = [tries EXCEPT ![w] = @ + 1]
                     /\ UNCHANGED saidNo
                ELSE /\ AnswerNo(w)
                     /\ ph' = [ph EXCEPT ![w] = "offset"]
                     /\ UNCHANGED tries

Commit(w) ==
    /\ alive[w]
    /\ ph[w] = "commit"
    /\ IF Fence /\ epoch # w
         \* The store refuses the request for its epoch, and the writer,
         \* which has lost the partition, stops without answering.
         THEN /\ alive' = [alive EXCEPT ![w] = FALSE]
              /\ ph' = [ph EXCEPT ![w] = "fenced"]
              /\ UNCHANGED <<dseq, listed, docseq, live, claims, rcpt, rwrote, haslog, tries, saidNo>>
         ELSE /\ IF Guard = "PerStep" THEN CommitPerStep(w) ELSE CommitWhole(w)
              /\ UNCHANGED alive
    /\ UNCHANGED <<epoch, stored, fin, cur, rd, started, crashes>>

\* As built only. A later request tombstones the document's row where it is
\* still live, at the revision it then has. The rounds of the writer, each a
\* read and a request, are one step here, so the first round lands.
Finish(w) ==
    /\ alive[w]
    /\ ph[w] = "finish"
    /\ docseq' = IF live THEN docseq + 1 ELSE docseq
    /\ live' = FALSE
    /\ ph' = [ph EXCEPT ![w] = "offset"]
    /\ UNCHANGED <<dseq, listed, claims, rcpt, rwrote, haslog, epoch, stored,
                   alive, fin, cur, rd, tries, started, crashes, saidNo>>

\* The writer has finished the command. Under Stream it stores the offset.
StoreOffset(w) ==
    /\ alive[w]
    /\ ph[w] = "offset"
    /\ stored' = IF Delivery = "Stream" THEN cur[w] ELSE stored
    /\ fin' = [fin EXCEPT ![w] = @ \cup {cur[w]}]
    /\ ph' = [ph EXCEPT ![w] = "idle"]
    /\ cur' = [cur EXCEPT ![w] = 0]
    /\ rd' = [rd EXCEPT ![w] = NoRead]
    /\ tries' = [tries EXCEPT ![w] = 0]
    /\ UNCHANGED <<dseq, listed, docseq, live, claims, rcpt, rwrote, haslog, epoch,
                   alive, started, crashes, saidNo>>

\* A crash at any step. Nothing the writer held in memory survives.
Crash(w) ==
    /\ alive[w]
    /\ crashes < MaxCrashes
    /\ alive' = [alive EXCEPT ![w] = FALSE]
    /\ ph' = [ph EXCEPT ![w] = "dead"]
    /\ cur' = [cur EXCEPT ![w] = 0]
    /\ rd' = [rd EXCEPT ![w] = NoRead]
    /\ tries' = [tries EXCEPT ![w] = 0]
    /\ crashes' = crashes + 1
    /\ UNCHANGED <<store, fin, started, saidNo>>

Next ==
    \E w \in Writers :
        \/ Start(w)
        \/ Take(w)
        \/ ReadReceipt(w)
        \/ Plan(w)
        \/ Commit(w)
        \/ Finish(w)
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
        /\ WF_vars(ReadReceipt(w))
        /\ WF_vars(Plan(w))
        /\ WF_vars(Commit(w))
        /\ WF_vars(Finish(w))
        /\ WF_vars(StoreOffset(w))

FairSpec == Spec /\ Fairness

(***************************************************************************)
(* What whole commands give. A command applied whole from a state, as one *)
(* writer alone applies it.                                                *)
(***************************************************************************)
Abs == [dseq |-> dseq, listed |-> listed, docseq |-> docseq, live |-> live, rcpt |-> rcpt]

Start0 == [dseq |-> 1, listed |-> TRUE, docseq |-> 1, live |-> TRUE, rcpt |-> {}]

ApplyWhole(st, c) ==
    CASE Name(c) = "SaveDoc" ->
            IF st.listed /\ st.live /\ st.docseq = 1
              THEN [st EXCEPT !.docseq = @ + 1, !.rcpt = @ \cup {c}]
              ELSE st
      [] Name(c) = "SaveDesc" ->
            [st EXCEPT !.dseq = @ + 1, !.rcpt = @ \cup {c}]
      [] Name(c) = "Del" ->
            IF st.listed
              THEN [st EXCEPT !.dseq = @ + 1, !.listed = FALSE,
                              !.docseq = IF st.live THEN @ + 1 ELSE @,
                              !.live = FALSE, !.rcpt = @ \cup {c}]
              ELSE st

RECURSIVE Fold(_, _)
Fold(st, s) == IF s = <<>> THEN st ELSE Fold(ApplyWhole(st, Head(s)), Tail(s))

\* Every sequence of distinct commands, in every order.
Orders == {s \in UNION {[1..n -> Cmd] : n \in 0..K} :
              \A i, j \in DOMAIN s : i # j => s[i] # s[j]}

WholeStates == {Fold(Start0, s) : s \in Orders}

(***************************************************************************)
(* The requirement. Every reachable state, after any request, crash or     *)
(* redelivery, is one that some sequence of whole commands gives, in the  *)
(* revisions, the listing, the document's row and the receipts. So no      *)
(* command has a receipt while part of it is not applied, and no row has   *)
(* moved that a receipt does not account for.                              *)
(***************************************************************************)
WholeCommands == Abs \in WholeStates

\* No command answered as not applied has a receipt, then or later, so no
\* answer disowns a row the command moved.
AnswersAgree == saidNo \cap rcpt = {}

\* Whether the last writer to start has not crashed since.
LastStays == started = NWriters => alive[NWriters]

\* Every command on the stream is finished by some writer, which is where the
\* model has it answered. A writer replies and then stores the offset, and the
\* model has no variable for the reply apart from the offset.
Answered == Cmd = UNION {fin[w] : w \in Writers}

\* Where the last writer to start stays alive, every command is eventually
\* answered.
EventuallyAnswered == []LastStays => <>Answered

\* A document the description lists and that is live keeps its patch log, so a
\* deletion that applied nothing to the document leaves its history.
LogKept == (listed /\ live) => haslog

=============================================================================
