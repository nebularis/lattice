\* SPDX-License-Identifier: MPL-2.0
------------------------ MODULE X2_EvidenceAcrossStores ------------------------
(***************************************************************************)
(* Model X2 of MSA-I6, a core reading evidence in a source store S and     *)
(* committing a decision with its read set to a records store R.           *)
(*                                                                         *)
(* S commits at positions 1, 2, 3 and so on, one position at a time, and   *)
(* each position holds the value of the evidence after that commit. A      *)
(* commit may leave the value as it was. S keeps every version, so the     *)
(* value S held at position p is hist[p]. The watermark wm is the highest  *)
(* committed position. Position 0 holds the initial value.                 *)
(*                                                                         *)
(* A core evaluates a decision at a decision position p. It reads the      *)
(* evidence from S in one step and in a later step commits a decision to   *)
(* R carrying its read set, the value read and the position it read at. S  *)
(* moves between the two steps. Each position in DecPositions has one      *)
(* core.                                                                   *)
(*                                                                         *)
(* Row is "Watermark" or "BestKnown", the last two rows of section 4.2.    *)
(*                                                                         *)
(*   Watermark  the core reads only once wm >= p and reads the value S     *)
(*              held at p. The position recorded is p.                     *)
(*   BestKnown  the core reads S's current value at once and records wm    *)
(*              as the position read at.                                   *)
(*                                                                         *)
(* An audit is computable from the read set and S's versions. A decision   *)
(* is Superseded if S committed a change at a position between the         *)
(* position read at and p, in either order. A decision whose p is above wm *)
(* cannot be audited yet, since S has not reached p.                       *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    Row,           \* "Watermark" or "BestKnown"
    MaxPos,        \* the highest position S reaches
    Values,        \* the values the evidence can take
    Holder0,       \* the value at position 0, one of Values
    DecPositions   \* the decision positions, a subset of 1..MaxPos

ASSUME Row \in {"Watermark", "BestKnown"}
ASSUME MaxPos \in Nat \ {0}
ASSUME Holder0 \in Values
ASSUME DecPositions \subseteq 1..MaxPos

NONE == "none"
ASSUME NONE \notin Values

Positions == 0..MaxPos

VARIABLES
    wm,      \* the watermark of S, the highest committed position
    hist,    \* the value S held at each position up to wm, NONE above
    ph,      \* per decision position: "idle", "read" or "done"
    rv,      \* per decision position: the value the core read
    rp,      \* per decision position: the position the core read at
    recs     \* the decisions committed to R, each with its read set

vars == <<wm, hist, ph, rv, rp, recs>>

TypeOK ==
    /\ wm \in Positions
    /\ hist \in [Positions -> Values \cup {NONE}]
    /\ \A q \in Positions : (q <= wm) <=> (hist[q] \in Values)
    /\ ph \in [DecPositions -> {"idle", "read", "done"}]
    /\ rv \in [DecPositions -> Values \cup {NONE}]
    /\ rp \in [DecPositions -> Positions]
    /\ recs \subseteq [p : DecPositions, val : Values, at : Positions]

Init ==
    /\ wm = 0
    /\ hist = [q \in Positions |-> IF q = 0 THEN Holder0 ELSE NONE]
    /\ ph = [p \in DecPositions |-> "idle"]
    /\ rv = [p \in DecPositions |-> NONE]
    /\ rp = [p \in DecPositions |-> 0]
    /\ recs = {}

\* Another writer commits at the next position, with any value. The value
\* may be the one already held, a commit that changes nothing.
Advance ==
    /\ wm < MaxPos
    /\ \E v \in Values :
         /\ wm' = wm + 1
         /\ hist' = [hist EXCEPT ![wm + 1] = v]
    /\ UNCHANGED <<ph, rv, rp, recs>>

\* The core reads S. Under Watermark it waits for the watermark to reach p
\* and reads the version at p. Under BestKnown it reads the current value.
Read(p) ==
    /\ ph[p] = "idle"
    /\ Row = "Watermark" => wm >= p
    /\ rv' = [rv EXCEPT ![p] = IF Row = "Watermark" THEN hist[p] ELSE hist[wm]]
    /\ rp' = [rp EXCEPT ![p] = IF Row = "Watermark" THEN p ELSE wm]
    /\ ph' = [ph EXCEPT ![p] = "read"]
    /\ UNCHANGED <<wm, hist, recs>>

\* The core commits the decision with its read set to R.
Commit(p) ==
    /\ ph[p] = "read"
    /\ recs' = recs \cup {[p |-> p, val |-> rv[p], at |-> rp[p]]}
    /\ ph' = [ph EXCEPT ![p] = "done"]
    /\ UNCHANGED <<wm, hist, rv, rp>>

Next ==
    \/ Advance
    \/ \E p \in DecPositions : Read(p) \/ Commit(p)

CoreFair == \A p \in DecPositions : WF_vars(Read(p)) /\ WF_vars(Commit(p))

\* S keeps advancing until MaxPos, so its watermark is live.
Spec == Init /\ [][Next]_vars /\ CoreFair /\ WF_vars(Advance)

\* S may stop advancing at any point, the partition. The core stays fair.
SpecStalled == Init /\ [][Next]_vars /\ CoreFair

(***************************************************************************)
(* The audit. A change at position q is hist[q] # hist[q - 1]. A decision  *)
(* is Superseded if there is a change at a position above the lower of the *)
(* position read at and p, and at or below the higher. The audit reads     *)
(* the decision's read set and S's versions only.                          *)
(***************************************************************************)
Lo(d) == IF d.at < d.p THEN d.at ELSE d.p
Hi(d) == IF d.at < d.p THEN d.p ELSE d.at
Superseded(d) == \E q \in (Lo(d) + 1)..Hi(d) : hist[q] # hist[q - 1]

(***************************************************************************)
(* The core only commits once S has passed p. Holds under Watermark.       *)
(***************************************************************************)
CommitOnlyPastWatermark == \A d \in recs : d.p <= wm

(***************************************************************************)
(* W. Once S has reached p, a committed decision's evidence equals what S  *)
(* held at p. Expected to hold under Watermark and to fail under BestKnown.*)
(***************************************************************************)
EvidenceAsOfP == \A d \in recs : d.p <= wm => d.val = hist[d.p]

(***************************************************************************)
(* A. Every decision whose evidence differs from what S held at p is       *)
(* flagged by the audit, once S has reached p. The audit may also flag a   *)
(* decision whose evidence happens to be right.                            *)
(***************************************************************************)
AuditFindsStale ==
    \A d \in recs : (d.p <= wm /\ d.val # hist[d.p]) => Superseded(d)

\* A check that the audit is not vacuous. No auditable decision is flagged.
\* Expected to fail under BestKnown.
NoneSuperseded == \A d \in recs : d.p <= wm => ~Superseded(d)

\* The read set tells the truth, the recorded position holds the recorded
\* value.
ReadSetTrue == \A d \in recs : d.val = hist[d.at]

(***************************************************************************)
(* L. Every evaluation eventually commits.                                 *)
(***************************************************************************)
AllDecided == \A p \in DecPositions : <>(ph[p] = "done")

=============================================================================
