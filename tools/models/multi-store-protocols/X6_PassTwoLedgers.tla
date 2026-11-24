\* SPDX-License-Identifier: MPL-2.0
-------------------------- MODULE X6_PassTwoLedgers --------------------------
(***************************************************************************)
(* A pass over two ledgers, the ledger's case of the named saga row, for   *)
(* MSA-I6. It starts from model X1's torn read and torn crash, with two    *)
(* ledgers in place of two stores, and each ledger keeping Protocol A of   *)
(* PA_PassRevision.tla for its own request.                                *)
(*                                                                         *)
(* A claim on a contract erodes the programme's aggregate. The contract's  *)
(* account is in the contract's ledger C and the aggregate in the          *)
(* programme's ledger P, which have different owners, so the claim's      *)
(* evaluation writes a pass to each and each ledger takes a request of its *)
(* own. A claim is paid one unit where the contract's account and the      *)
(* aggregate each have one. It reads C, then P, decides, and writes C      *)
(* first and P second, each request guarded on the revision of that ledger *)
(* the decision was evaluated from. A claim that is not paid writes        *)
(* nothing, and one whose C pass is written and that is then not paid      *)
(* writes a compensating pass that restores what it drew, the saga's       *)
(* compensation. Two claims, E1 and E2, on the same contract.              *)
(*                                                                         *)
(* The two gaps of a pass over two ledgers.                                *)
(*                                                                         *)
(*   RefusalReturnsRevision  TRUE closes the first. A refused request      *)
(*       returns the revision the ledger was at, and the decision is made  *)
(*       again with that ledger read as of it, the other ledger as of the  *)
(*       revision the decision already held. FALSE leaves it open. A       *)
(*       refusal returns nothing, the decision is made again from the      *)
(*       revisions held, the request names the same revision again, and   *)
(*       after Retries such refusals the evaluation gives up.             *)
(*   RecordStart  TRUE closes the second. The C pass records the revisions *)
(*       of both ledgers its decision was evaluated from, and a replay     *)
(*       after a stop makes the decision again from them. FALSE leaves it  *)
(*       open. A replay finds the passes it wrote by their names, and      *)
(*       evaluates from the latest revision of each ledger.                *)
(*                                                                         *)
(* A claim may stop at any point after its first read, and loses what it   *)
(* held in memory. With WithReader, one reader reads C and later P, as     *)
(* X1's reader reads A and then B.                                         *)
(*                                                                         *)
(* A pass's position is the later of its claim's stimulus's position and   *)
(* the position of its ledger's latest pass at the revision it names.      *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Integers, Sequences, FiniteSets

CONSTANTS
    RefusalReturnsRevision,  \* BOOLEAN, the first gap closed
    RecordStart,             \* BOOLEAN, the second gap closed
    Retries,                 \* refusals taken again before giving up, where none returns a revision
    MaxStops,                \* the most stops in a behaviour
    WithReader,              \* BOOLEAN, whether the reader of C then P runs
    Contracts,               \* the contract's account's starting balances
    Aggregates,              \* the aggregate's starting balances
    Orders                   \* a non-empty subset of {"E1First", "E2First", "Same"}

ASSUME RefusalReturnsRevision \in BOOLEAN /\ RecordStart \in BOOLEAN /\ WithReader \in BOOLEAN
ASSUME Retries \in Nat /\ MaxStops \in Nat
ASSUME Contracts \subseteq Nat /\ Aggregates \subseteq Nat
ASSUME Orders # {} /\ Orders \subseteq {"E1First", "E2First", "Same"}

Claims == {"E1", "E2"}
Ledgers == {"C", "P"}
NoStart == [L \in Ledgers |-> -1]
NoReq == [l |-> "none", k |-> "none"]

PositionsOf(o) == CASE o = "E1First" -> <<1, 2>> [] o = "E2First" -> <<2, 1>> [] o = "Same" -> <<1, 1>>

VARIABLES
    stim,      \* each claim's stimulus position
    hist,      \* each ledger's state at each revision, hist[L][r + 1] at revision r
    log,       \* each ledger's passes, log[L][r] the pass that moved L to revision r
    pc,        \* each claim: "start", "readC", "act", "replay" or "done"
    view,      \* each claim: the revision of each ledger its decision was evaluated from
    dec,       \* each claim: "pay", "nopay" or "none"
    known,     \* each claim: the revision of each ledger a compensation names
    start,     \* each claim: the revisions its C pass recorded, or NoStart
    refusals,  \* each claim: refusals taken with no revision returned
    stops,     \* the stops so far
    rd,        \* the reader: "idle", "readC" or "done"
    rdC,       \* what the reader read of C, each claim's net units drawn
    rdP        \* what the reader read of P

vars == <<stim, hist, log, pc, view, dec, known, start, refusals, stops, rd, rdC, rdP>>

Max(x, y) == IF x >= y THEN x ELSE y
Rev(L) == Len(hist[L]) - 1
Cur(L) == hist[L][Len(hist[L])]
At(L, r) == hist[L][r + 1]
Zero == [L \in Ledgers |-> 0]

Passes(L, a, k) == {i \in DOMAIN log[L] : log[L][i].claim = a /\ log[L][i].kind = k}
Drawn(L, a) == Passes(L, a, "draw") # {}
Restored(L, a) == Passes(L, a, "restore") # {}
Net(L, a) == (IF Drawn(L, a) THEN 1 ELSE 0) - (IF Restored(L, a) THEN 1 ELSE 0)

\* The claim's rule. It is paid where the contract's account and the
\* aggregate, read as of the revisions v, each have a unit.
Decide(v) == IF At("C", v["C"]).bal >= 1 /\ At("P", v["P"]).bal >= 1 THEN "pay" ELSE "nopay"

\* The claim's next request. A claim that is not paid, or one already
\* compensated, restores what it drew. One that is paid draws on C, then on P.
NextReq(a) ==
    IF dec[a] = "nopay" \/ Restored("C", a) \/ Restored("P", a)
    THEN IF Drawn("C", a) /\ ~Restored("C", a) THEN [l |-> "C", k |-> "restore"]
         ELSE IF Drawn("P", a) /\ ~Restored("P", a) THEN [l |-> "P", k |-> "restore"]
         ELSE NoReq
    ELSE IF ~Drawn("C", a) THEN [l |-> "C", k |-> "draw"]
         ELSE IF ~Drawn("P", a) THEN [l |-> "P", k |-> "draw"]
         ELSE NoReq

TypeOK ==
    /\ \A L \in Ledgers : \A r \in DOMAIN hist[L] : hist[L][r].bal \in Nat /\ hist[L][r].lp \in Nat
    /\ \A L \in Ledgers : \A i \in DOMAIN log[L] :
         log[L][i].claim \in Claims /\ log[L][i].kind \in {"draw", "restore"} /\ log[L][i].pos \in Nat
    /\ pc \in [Claims -> {"start", "readC", "act", "replay", "done"}]
    /\ dec \in [Claims -> {"pay", "nopay", "none"}]
    /\ \A a \in Claims : \A L \in Ledgers : Net(L, a) \in {0, 1}
    /\ stops \in 0..MaxStops

Init ==
    /\ \E c \in Contracts, g \in Aggregates, o \in Orders :
         /\ hist = [L \in Ledgers |-> <<[bal |-> IF L = "C" THEN c ELSE g, lp |-> 0]>>]
         /\ stim = [a \in Claims |-> IF a = "E1" THEN PositionsOf(o)[1] ELSE PositionsOf(o)[2]]
    /\ log = [L \in Ledgers |-> <<>>]
    /\ pc = [a \in Claims |-> "start"]
    /\ view = [a \in Claims |-> Zero]
    /\ dec = [a \in Claims |-> "none"]
    /\ known = [a \in Claims |-> Zero]
    /\ start = [a \in Claims |-> NoStart]
    /\ refusals = [a \in Claims |-> 0]
    /\ stops = 0
    /\ rd = "idle"
    /\ rdC = [a \in Claims |-> 0]
    /\ rdP = [a \in Claims |-> 0]

\* The claim reads C at its latest revision.
ReadC(a) ==
    /\ pc[a] = "start"
    /\ view' = [view EXCEPT ![a]["C"] = Rev("C")]
    /\ pc' = [pc EXCEPT ![a] = "readC"]
    /\ UNCHANGED <<stim, hist, log, dec, known, start, refusals, stops, rd, rdC, rdP>>

\* The claim reads P at its latest revision, in a later step, and decides.
ReadP(a) ==
    /\ pc[a] = "readC"
    /\ LET v == [view[a] EXCEPT !["P"] = Rev("P")] IN
         /\ view' = [view EXCEPT ![a] = v]
         /\ dec' = [dec EXCEPT ![a] = Decide(v)]
         /\ known' = [known EXCEPT ![a] = v]
    /\ pc' = [pc EXCEPT ![a] = "act"]
    /\ UNCHANGED <<stim, hist, log, start, refusals, stops, rd, rdC, rdP>>

\* The claim sends its next request, which the ledger's writer takes. A
\* draw names the revision its decision was evaluated from, a restore the
\* latest revision the claim knows. The writer writes the request only
\* while the ledger is at the revision named.
Act(a) ==
    /\ pc[a] = "act"
    /\ LET q == NextReq(a) IN
       IF q.k = "none"
       THEN /\ pc' = [pc EXCEPT ![a] = "done"]
            /\ UNCHANGED <<hist, log, view, dec, known, start, refusals>>
       ELSE LET L == q.l
                r == IF q.k = "draw" THEN view[a][L] ELSE known[a][L]
            IN  IF Rev(L) = r
                THEN LET pos == Max(stim[a], At(L, r).lp)
                         bal == IF q.k = "draw" THEN Cur(L).bal - 1 ELSE Cur(L).bal + 1
                     IN  /\ hist' = [hist EXCEPT ![L] = Append(@, [bal |-> bal, lp |-> pos])]
                         /\ log' = [log EXCEPT ![L] = Append(@, [claim |-> a, kind |-> q.k, pos |-> pos])]
                         /\ known' = [known EXCEPT ![a][L] = r + 1]
                         /\ start' = IF RecordStart /\ L = "C" /\ q.k = "draw"
                                     THEN [start EXCEPT ![a] = view[a]] ELSE start
                         /\ UNCHANGED <<pc, view, dec, refusals>>
                ELSE IF RefusalReturnsRevision
                THEN IF q.k = "draw"
                     THEN LET v == [view[a] EXCEPT ![L] = Rev(L)] IN
                          /\ view' = [view EXCEPT ![a] = v]
                          /\ dec' = [dec EXCEPT ![a] = Decide(v)]
                          /\ known' = [known EXCEPT ![a][L] = Rev(L)]
                          /\ UNCHANGED <<pc, hist, log, start, refusals>>
                     ELSE /\ known' = [known EXCEPT ![a][L] = Rev(L)]
                          /\ UNCHANGED <<pc, hist, log, view, dec, start, refusals>>
                ELSE /\ refusals' = [refusals EXCEPT ![a] = @ + 1]
                     /\ pc' = [pc EXCEPT ![a] = IF refusals[a] < Retries THEN "act" ELSE "done"]
                     /\ UNCHANGED <<hist, log, view, dec, known, start>>
    /\ UNCHANGED <<stim, stops, rd, rdC, rdP>>

\* The claim stops and loses what it held in memory.
Stop(a) ==
    /\ stops < MaxStops
    /\ pc[a] \in {"readC", "act"}
    /\ stops' = stops + 1
    /\ pc' = [pc EXCEPT ![a] = "replay"]
    /\ view' = [view EXCEPT ![a] = Zero]
    /\ dec' = [dec EXCEPT ![a] = "none"]
    /\ known' = [known EXCEPT ![a] = Zero]
    /\ refusals' = [refusals EXCEPT ![a] = 0]
    /\ UNCHANGED <<stim, hist, log, start, rd, rdC, rdP>>

\* The claim starts again. With the start recorded on its C pass it makes
\* its decision again from the revisions recorded. Otherwise it reads both
\* ledgers again at their latest revisions.
Replay(a) ==
    /\ pc[a] = "replay"
    /\ IF RecordStart /\ start[a] # NoStart
       THEN /\ view' = [view EXCEPT ![a] = start[a]]
            /\ dec' = [dec EXCEPT ![a] = Decide(start[a])]
            /\ known' = [known EXCEPT ![a] = start[a]]
            /\ pc' = [pc EXCEPT ![a] = "act"]
       ELSE /\ pc' = [pc EXCEPT ![a] = "start"]
            /\ UNCHANGED <<view, dec, known>>
    /\ UNCHANGED <<stim, hist, log, start, refusals, stops, rd, rdC, rdP>>

ReadRC ==
    /\ WithReader /\ rd = "idle"
    /\ rdC' = [a \in Claims |-> Net("C", a)]
    /\ rd' = "readC"
    /\ UNCHANGED <<stim, hist, log, pc, view, dec, known, start, refusals, stops, rdP>>

ReadRP ==
    /\ rd = "readC"
    /\ rdP' = [a \in Claims |-> Net("P", a)]
    /\ rd' = "done"
    /\ UNCHANGED <<stim, hist, log, pc, view, dec, known, start, refusals, stops, rdC>>

Next ==
    \/ \E a \in Claims : ReadC(a) \/ ReadP(a) \/ Act(a) \/ Stop(a) \/ Replay(a)
    \/ ReadRC \/ ReadRP

Spec == Init /\ [][Next]_vars

AllDone == \A a \in Claims : pc[a] = "done"
Paid(a) == Net("C", a) = 1 /\ Net("P", a) = 1

(***************************************************************************)
(* Every claim whole. Once both claims are done, the contract's account,   *)
(* the aggregate and the claims paid are those the two claims give when    *)
(* evaluated whole one after the other, in one order or the other.         *)
(***************************************************************************)
SerialPaid(first) ==
    LET second == IF first = "E1" THEN "E2" ELSE "E1"
        c0 == hist["C"][1].bal
        g0 == hist["P"][1].bal
        p1 == c0 >= 1 /\ g0 >= 1
        c1 == IF p1 THEN c0 - 1 ELSE c0
        g1 == IF p1 THEN g0 - 1 ELSE g0
        p2 == c1 >= 1 /\ g1 >= 1
    IN  [c |-> IF p2 THEN c1 - 1 ELSE c1, g |-> IF p2 THEN g1 - 1 ELSE g1,
         paid |-> (IF p1 THEN {first} ELSE {}) \cup (IF p2 THEN {second} ELSE {})]

SerialClaims ==
    AllDone => [c |-> Cur("C").bal, g |-> Cur("P").bal, paid |-> {a \in Claims : Paid(a)}]
               \in {SerialPaid("E1"), SerialPaid("E2")}

\* Once both claims are done, each is drawn in both ledgers or in neither,
\* counting a compensation.
NoHalfClaim == AllDone => \A a \in Claims : Net("C", a) = Net("P", a)

\* X1's torn crash. A claim that has stopped and not started again has
\* drawn in both ledgers or in neither.
NoStrandedHalf == \A a \in Claims : pc[a] = "replay" => Net("C", a) = Net("P", a)

\* X1's torn read. The reader saw each claim in both ledgers or in neither.
NoTornRead == rd = "done" => rdC = rdP

\* Each ledger's passes are in the order of their positions.
PassOrderEach == \A L \in Ledgers : \A i, j \in DOMAIN log[L] : i < j => log[L][i].pos <= log[L][j].pos

\* No pass takes a position before its claim's stimulus.
NotBeforeStimulus == \A L \in Ledgers : \A i \in DOMAIN log[L] : log[L][i].pos >= stim[log[L][i].claim]

\* A claim's draw takes the same position in both ledgers.
OnePosition ==
    \A a \in Claims : \A i \in Passes("C", a, "draw"), j \in Passes("P", a, "draw") :
        log["C"][i].pos = log["P"][j].pos

=============================================================================
