\* SPDX-License-Identifier: MPL-2.0
--------------------------- MODULE PA_PassRevision ---------------------------
(***************************************************************************)
(* Protocol A in one ledger, for MSA-I6. A pass is every record one        *)
(* evaluation writes. It is written as one request that names the revision *)
(* of the ledger it was evaluated from, and the writer writes it only      *)
(* while the ledger is at that revision. Where the ledger has moved, the   *)
(* writer writes nothing and answers with the revision it found, and the   *)
(* evaluation is made again from that revision. The request moves the      *)
(* revision once. A pass takes the later of its stimulus's position and    *)
(* the position of the ledger's latest pass at the revision it was         *)
(* evaluated from. Written from ADR-A131's second addendum of 2026-11-19,  *)
(* its addendum of 2026-11-20, and Behaviour's example ordered-draws.ttl.  *)
(*                                                                         *)
(* One owner's ledger holds a seat bundle and an alert quota, and the      *)
(* licence is within its bundle or on overage. An activation's pass makes, *)
(* in this order, a draw of one seat while the bundle has one, a draw of   *)
(* one alert when the bundle as that draw left it is below 2, and a move   *)
(* to overage when the bundle as the draws left it is empty. From overage  *)
(* an activation makes nothing and writes no pass. An alert drawn from an  *)
(* empty quota is refused, and the refusal is a record of the pass, unless *)
(* AlertNeedsQuota puts the quota in the alert's guard. A credit's pass    *)
(* restores CreditSeats seats, and is cut at the stated amount.            *)
(*                                                                         *)
(* Two actors. A is an activation. O is a credit or a second activation,   *)
(* of the same licence or, with Licences = "PerActor", of a licence of its *)
(* own on the same accounts. Each evaluates from the ledger as it reads it *)
(* and sends its request. An actor in StopActors may stop while it holds a *)
(* plan, and loses it. It then looks for its own pass, which is named from *)
(* the ledger and its evaluation, and finding none evaluates again from    *)
(* the latest revision.                                                    *)
(*                                                                         *)
(* The variant is chosen in the initial state from the constant sets, so   *)
(* one run can cover several, as the census configurations do.            *)
(*                                                                         *)
(*   OnRead      Protocol A, the request guarded on the revision read.     *)
(*   OnLatest    the request written on whatever revision is latest. Each  *)
(*               draw is applied by the ledger's own arithmetic, so one    *)
(*               that no longer fits is refused, and nothing evaluates the *)
(*               pass again.                                               *)
(*   PerPosting  each posting a request of its own, guarded on the         *)
(*               revision the previous one returned, the first on the      *)
(*               revision read. A refused posting returns the revision it  *)
(*               found, and the transitions not yet written are evaluated  *)
(*               again from it. After a stop, the transitions whose        *)
(*               records are found are left out and the rest evaluated     *)
(*               again from the latest revision.                           *)
(*                                                                         *)
(*   Stimulus    a pass takes its stimulus's position.                     *)
(*   LaterOf     a pass takes the later of its stimulus's position and the *)
(*               ledger's latest pass's, read with the revision.           *)
(*                                                                         *)
(*   Concurrent       the actors interleave freely.                        *)
(*   OneAfterAnother  an actor evaluates only while the other is not in    *)
(*                    the middle of a pass.                                *)
(*                                                                         *)
(* Each step is a function of the state record, so the outcomes reachable  *)
(* with no stop can be computed inside the model, which O2 needs.          *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    Protocols,        \* a non-empty subset of {"OnRead", "OnLatest", "PerPosting"}
    Rules,            \* a non-empty subset of {"Stimulus", "LaterOf"}
    Others,           \* a non-empty subset of {"Credit", "Activation"}
    Modes,            \* a non-empty subset of {"Concurrent", "OneAfterAnother"}
    MaxStops,         \* the most stops in a behaviour
    StopActors,       \* the actors that may stop, a subset of {"A", "O"}
    Bundles,          \* the seat bundle's starting balances
    Quotas,           \* the alert quota's starting balances
    Orders,           \* a non-empty subset of {"AFirst", "OFirst", "Same"}
    Stated,           \* the bundle's stated amount, the most a credit restores it to
    CreditSeats,      \* the seats a credit restores
    Licences,         \* "One", or "PerActor" where O has a licence of its own
    AlertNeedsQuota   \* whether the alert's guard also asks for a unit in the quota

ASSUME Protocols # {} /\ Protocols \subseteq {"OnRead", "OnLatest", "PerPosting"}
ASSUME Rules # {} /\ Rules \subseteq {"Stimulus", "LaterOf"}
ASSUME Others # {} /\ Others \subseteq {"Credit", "Activation"}
ASSUME Modes # {} /\ Modes \subseteq {"Concurrent", "OneAfterAnother"}
ASSUME MaxStops \in Nat /\ StopActors \subseteq {"A", "O"}
ASSUME Stated \in Nat /\ Bundles \subseteq 0..Stated /\ Quotas \subseteq Nat
ASSUME Orders # {} /\ Orders \subseteq {"AFirst", "OFirst", "Same"}
ASSUME CreditSeats \in Nat \ {0}
ASSUME Licences \in {"One", "PerActor"} /\ AlertNeedsQuota \in BOOLEAN

Actors == {"A", "O"}
Labels == {"seat", "seatRefused", "alert", "alertRefused", "move", "credit", "creditCut"}

\* The stimulus positions of A and O. AFirst puts A's at 1 and O's at 2,
\* OFirst the reverse, and Same both at 1.
PositionsOf(o) == CASE o = "AFirst" -> <<1, 2>> [] o = "OFirst" -> <<2, 1>> [] o = "Same" -> <<1, 1>>

VARIABLES
    proto,   \* the protocol of this behaviour
    rule,    \* the position rule of this behaviour
    other,   \* what O is in this behaviour
    mode,    \* whether the actors interleave
    stim,    \* each actor's stimulus position
    hist,    \* the ledger's state at each revision, hist[r + 1] at revision r
    log,     \* the passes, log[r] the pass that moved the ledger to revision r
    pc,      \* each actor: "start", "ready" or "done"
    plan,    \* each actor: the transitions it will write, in order
    view,    \* each actor: the revision its next request names
    stops    \* the stops so far

vars == <<proto, rule, other, mode, stim, hist, log, pc, plan, view, stops>>

State == [proto |-> proto, rule |-> rule, other |-> other, mode |-> mode, stim |-> stim,
          hist |-> hist, log |-> log, pc |-> pc, plan |-> plan, view |-> view, stops |-> stops]

Max(x, y) == IF x >= y THEN x ELSE y
Min(x, y) == IF x <= y THEN x ELSE y
Peer(a) == IF a = "A" THEN "O" ELSE "A"
Kind(t, a) == IF a = "A" THEN "Activation" ELSE t.other
RevOf(t) == Len(t.hist) - 1
CurOf(t) == t.hist[Len(t.hist)]

\* The records an actor's passes hold. A pass is found by its name, which is
\* derived from the ledger and the evaluation, so this is what a stopped
\* actor finds.
WrittenOf(t, a) == UNION {t.log[i].recs : i \in {j \in DOMAIN t.log : t.log[j].actor = a}}

(***************************************************************************)
(* The transitions a pass of kind k for actor a makes from ledger state s, *)
(* in order, leaving out those whose records W already holds. Each guard   *)
(* reads the state as the transitions before it in the pass left it.      *)
(***************************************************************************)
Plan(k, a, s, W) ==
    IF k = "Credit"
    THEN IF W \cap {"credit", "creditCut"} # {} THEN <<>>
         ELSE <<IF s.b + CreditSeats <= Stated THEN "credit" ELSE "creditCut">>
    ELSE IF s.lic[a] = "overage" THEN <<>>
    ELSE LET seat  == "seat" \notin W /\ s.b >= 1
             b1    == IF seat THEN s.b - 1 ELSE s.b
             alert == W \cap {"alert", "alertRefused"} = {} /\ b1 < 2 /\ (AlertNeedsQuota => s.q >= 1)
             move  == b1 = 0
         IN  (IF seat THEN <<"seat">> ELSE <<>>)
             \o (IF alert THEN <<IF s.q >= 1 THEN "alert" ELSE "alertRefused">> ELSE <<>>)
             \o (IF move THEN <<"move">> ELSE <<>>)

\* One transition of actor a applied by the ledger's own arithmetic. A draw
\* that no longer fits is refused and a credit is cut at the stated amount.
ApplyOne(s, l, a) ==
    CASE l \in {"seat", "seatRefused"} ->
            IF s.b >= 1 THEN [st |-> [s EXCEPT !.b = s.b - 1], rec |-> "seat"]
            ELSE [st |-> s, rec |-> "seatRefused"]
      [] l \in {"alert", "alertRefused"} ->
            IF s.q >= 1 THEN [st |-> [s EXCEPT !.q = s.q - 1], rec |-> "alert"]
            ELSE [st |-> s, rec |-> "alertRefused"]
      [] l = "move" ->
            [st |-> [s EXCEPT !.lic = [x \in Actors |-> IF Licences = "One" \/ x = a THEN "overage" ELSE s.lic[x]]],
             rec |-> "move"]
      [] l \in {"credit", "creditCut"} ->
            LET n == Min(CreditSeats, Stated - s.b) IN
            [st |-> [s EXCEPT !.b = s.b + n], rec |-> IF n = CreditSeats THEN "credit" ELSE "creditCut"]

RECURSIVE ApplyAll(_, _, _)
ApplyAll(s, ls, a) ==
    IF ls = <<>> THEN [st |-> s, recs |-> {}]
    ELSE LET one  == ApplyOne(s, Head(ls), a)
             rest == ApplyAll(one.st, Tail(ls), a)
         IN  [st |-> rest.st, recs |-> {one.rec} \cup rest.recs]

\* The position a pass of a evaluated from revision r takes.
PosOf(t, a, r) == IF t.rule = "Stimulus" THEN t.stim[a] ELSE Max(t.stim[a], t.hist[r + 1].lp)

(***************************************************************************)
(* The steps, each the set of states it leads to from t, empty where it is *)
(* not enabled.                                                            *)
(***************************************************************************)

\* The actor reads the ledger at its latest revision and evaluates. An
\* evaluation that makes no transition writes no pass.
ReadS(t, a) ==
    IF t.pc[a] = "start" /\ (t.mode = "OneAfterAnother" => t.pc[Peer(a)] \in {"start", "done"})
    THEN LET p == Plan(Kind(t, a), a, CurOf(t), WrittenOf(t, a)) IN
         {[t EXCEPT !.pc[a] = IF p = <<>> THEN "done" ELSE "ready", !.plan[a] = p, !.view[a] = RevOf(t)]}
    ELSE {}

\* The writer takes the actor's request. Under OnRead and PerPosting it is
\* written only while the ledger is at the revision named, and otherwise
\* refused with the revision found, from which the actor evaluates again.
WriteS(t, a) ==
    IF t.pc[a] # "ready" THEN {}
    ELSE IF t.proto = "OnLatest" \/ RevOf(t) = t.view[a]
    THEN LET part == IF t.proto = "PerPosting" THEN <<Head(t.plan[a])>> ELSE t.plan[a]
             rest == IF t.proto = "PerPosting" THEN Tail(t.plan[a]) ELSE <<>>
             res  == ApplyAll(CurOf(t), part, a)
             pos  == PosOf(t, a, t.view[a])
         IN  {[t EXCEPT !.hist = Append(t.hist, [res.st EXCEPT !.lp = pos]),
                        !.log = Append(t.log, [actor |-> a, pos |-> pos, recs |-> res.recs]),
                        !.plan[a] = rest,
                        !.view[a] = RevOf(t) + 1,
                        !.pc[a] = IF rest = <<>> THEN "done" ELSE "ready"]}
    ELSE LET p == Plan(Kind(t, a), a, CurOf(t), WrittenOf(t, a)) IN
         {[t EXCEPT !.plan[a] = p, !.view[a] = RevOf(t), !.pc[a] = IF p = <<>> THEN "done" ELSE "ready"]}

\* The actor stops and loses its plan. A pass written whole is found by its
\* name and the actor is done. Otherwise it starts again from the latest
\* revision, and under PerPosting leaves out the transitions it finds.
StopS(t, a) ==
    IF t.stops < MaxStops /\ a \in StopActors /\ t.pc[a] = "ready"
    THEN {[t EXCEPT !.stops = t.stops + 1,
                    !.pc[a] = IF t.proto # "PerPosting" /\ WrittenOf(t, a) # {} THEN "done" ELSE "start",
                    !.plan[a] = <<>>]}
    ELSE {}

NoStopSucc(t) == UNION {ReadS(t, a) \cup WriteS(t, a) : a \in Actors}
Succ(t) == NoStopSucc(t) \cup UNION {StopS(t, a) : a \in Actors}

TypeOK ==
    /\ proto \in {"OnRead", "OnLatest", "PerPosting"}
    /\ rule \in {"Stimulus", "LaterOf"}
    /\ other \in {"Credit", "Activation"}
    /\ mode \in {"Concurrent", "OneAfterAnother"}
    /\ \A r \in DOMAIN hist : /\ hist[r].b \in 0..Stated /\ hist[r].q \in Nat /\ hist[r].lp \in Nat
                              /\ hist[r].lic \in [Actors -> {"within", "overage"}]
    /\ \A i \in DOMAIN log : log[i].actor \in Actors /\ log[i].recs \subseteq Labels /\ log[i].recs # {}
    /\ pc \in [Actors -> {"start", "ready", "done"}]
    /\ \A a \in Actors : pc[a] = "ready" => plan[a] # <<>>
    /\ stops \in 0..MaxStops

Init ==
    /\ proto \in Protocols
    /\ rule \in Rules
    /\ other \in Others
    /\ mode \in Modes
    /\ \E b \in Bundles, q \in Quotas, o \in Orders :
         /\ hist = <<[b |-> b, q |-> q, lic |-> [x \in Actors |-> "within"], lp |-> 0]>>
         /\ stim = [x \in Actors |-> IF x = "A" THEN PositionsOf(o)[1] ELSE PositionsOf(o)[2]]
    /\ log = <<>>
    /\ pc = [x \in Actors |-> "start"]
    /\ plan = [x \in Actors |-> <<>>]
    /\ view = [x \in Actors |-> 0]
    /\ stops = 0

Next ==
    \E t \in Succ(State) :
        /\ proto' = t.proto /\ rule' = t.rule /\ other' = t.other /\ mode' = t.mode /\ stim' = t.stim
        /\ hist' = t.hist /\ log' = t.log /\ pc' = t.pc /\ plan' = t.plan /\ view' = t.view /\ stops' = t.stops

Spec == Init /\ [][Next]_vars

AllDone == \A a \in Actors : pc[a] = "done"

(***************************************************************************)
(* O1, a pass is whole. Once both actors are done, the bundle, the quota,  *)
(* the licences' states and the records of each actor are those that the  *)
(* two evaluations give when made whole one after the other, in one order *)
(* or the other, from the starting state.                                  *)
(***************************************************************************)
Whole(k, a, s) == ApplyAll(s, Plan(k, a, s, {}), a)

SerialOutcome(t, first) ==
    LET r1 == Whole(Kind(t, first), first, t.hist[1])
        r2 == Whole(Kind(t, Peer(first)), Peer(first), r1.st)
    IN  [b |-> r2.st.b, q |-> r2.st.q, lic |-> r2.st.lic,
         recs |-> [x \in Actors |-> IF x = first THEN r1.recs ELSE r2.recs]]

OutcomeOf(t) == [b |-> CurOf(t).b, q |-> CurOf(t).q, lic |-> CurOf(t).lic,
                 recs |-> [x \in Actors |-> WrittenOf(t, x)]]

O1Holds == OutcomeOf(State) \in {SerialOutcome(State, "A"), SerialOutcome(State, "O")}

SerialOutcomes == AllDone => O1Holds

(***************************************************************************)
(* O2, a stop is safe. Once both actors are done in a behaviour with a     *)
(* stop, the outcome is one that some behaviour with no stop reaches from  *)
(* the same starting state.                                                *)
(***************************************************************************)
RECURSIVE EndsFrom(_)
EndsFrom(t) ==
    LET n == NoStopSucc(t) IN
    IF n = {} THEN {OutcomeOf(t)} ELSE UNION {EndsFrom(u) : u \in n}

StartOf(t) ==
    [t EXCEPT !.hist = <<t.hist[1]>>, !.log = <<>>, !.pc = [x \in Actors |-> "start"],
              !.plan = [x \in Actors |-> <<>>], !.view = [x \in Actors |-> 0], !.stops = 0]

O2Holds == OutcomeOf(State) \in EndsFrom(StartOf(State))

StopSafe == (AllDone /\ stops > 0) => O2Holds

(***************************************************************************)
(* O3. The ledger's passes, in the order of the revisions they moved it    *)
(* to, are in the order of their positions.                                *)
(***************************************************************************)
PassOrder == \A i, j \in DOMAIN log : i < j => log[i].pos <= log[j].pos

\* O4. No pass takes a position before its stimulus's.
NotBeforeStimulus == \A i \in DOMAIN log : log[i].pos >= stim[log[i].actor]

(***************************************************************************)
(* The census. An invariant that always holds, and that prints one line    *)
(* for each state where both actors are done: the variant, the starting    *)
(* cell, the stops taken, whether O1 to O4 hold there, and the outcome.    *)
(* The cells a variant breaks are read from these lines.                   *)
(***************************************************************************)
Census ==
    IF AllDone
    THEN PrintT(<<"End", proto, rule, other, mode, hist[1].b, hist[1].q, stim["A"], stim["O"], stops,
                  O1Holds, IF stops > 0 THEN O2Holds ELSE TRUE, PassOrder, NotBeforeStimulus,
                  OutcomeOf(State)>>)
    ELSE TRUE

=============================================================================
