\* SPDX-License-Identifier: MPL-2.0
-------------------------- MODULE X4_AuthorityCutover --------------------------
(***************************************************************************)
(* Model X4 of MSA-I6, moving a family's authority from store A to store B *)
(* while writers are live.                                                 *)
(*                                                                         *)
(* A router holds the current authority. Each writer keeps a cached view   *)
(* of it and refreshes the view in a separate step. A writer has           *)
(* PerWriter writes to make, one after another. For its current write it   *)
(* sends a request to the store its view names, waits, and moves on when   *)
(* a store acknowledges. A store handles a request in one step. A store    *)
(* that is not fenced applies the write to its state and acknowledges. A   *)
(* fenced store refuses with an epoch error, and the writer, which is      *)
(* waiting, goes back to sending, and refreshes its view in the meantime.  *)
(* A request may stay in flight while the writer does other things.        *)
(*                                                                         *)
(* A migrator moves the authority from A to B. Protocol is "Naive" or      *)
(* "Fenced".                                                               *)
(*                                                                         *)
(*   Naive   copy A's state to B, then flip the router. Writers keep       *)
(*           writing to A until they see the flip.                         *)
(*   Fenced  fence A, then copy, then flip. A fenced store refuses writes. *)
(*                                                                         *)
(* The copy is one step, taking a snapshot of A, so a write that A applies *)
(* after the copy is not in B.                                             *)
(*                                                                         *)
(* Timeouts lets a waiting writer give up on its request without the       *)
(* request being withdrawn, and send again, to wherever its view then      *)
(* points. A request that is still in flight is then applied later.        *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    Protocol,    \* "Naive" or "Fenced"
    Timeouts,    \* BOOLEAN, a waiting writer may give up and send again
    Writers,     \* the writers, a set
    PerWriter    \* the number of writes each writer makes

ASSUME Protocol \in {"Naive", "Fenced"}
ASSUME Timeouts \in BOOLEAN
ASSUME PerWriter \in Nat \ {0}

Stores == {"A", "B"}

\* A write is the pair <<writer, k>>, the k-th write of the writer.
WriteIds == Writers \X (1..PerWriter)

VARIABLES
    auth,      \* the router's authority, "A" or "B"
    fenced,    \* per store: whether it refuses writes
    st,        \* per store: the writes applied
    mig,       \* the migrator: "init", "fenced", "copied" or "flipped"
    view,      \* per writer: the authority it last read from the router
    pend,      \* per writer: the k of its current write
    wph,       \* per writer: "idle" or "wait"
    reqs,      \* the requests in flight, pairs <<write, store>>
    ackedBy    \* per write: the stores that acknowledged it

vars == <<auth, fenced, st, mig, view, pend, wph, reqs, ackedBy>>

TypeOK ==
    /\ auth \in Stores
    /\ fenced \in [Stores -> BOOLEAN]
    /\ st \in [Stores -> SUBSET WriteIds]
    /\ mig \in {"init", "fenced", "copied", "flipped"}
    /\ view \in [Writers -> Stores]
    /\ pend \in [Writers -> 1..(PerWriter + 1)]
    /\ wph \in [Writers -> {"idle", "wait"}]
    /\ reqs \subseteq (WriteIds \X Stores)
    /\ ackedBy \in [WriteIds -> SUBSET Stores]

Init ==
    /\ auth = "A"
    /\ fenced = [s \in Stores |-> FALSE]
    /\ st = [s \in Stores |-> {}]
    /\ mig = "init"
    /\ view = [w \in Writers |-> "A"]
    /\ pend = [w \in Writers |-> 1]
    /\ wph = [w \in Writers |-> "idle"]
    /\ reqs = {}
    /\ ackedBy = [id \in WriteIds |-> {}]

(***************************************************************************)
(* Writers.                                                                *)
(***************************************************************************)

\* The writer reads the router.
Refresh(w) ==
    /\ view[w] # auth
    /\ view' = [view EXCEPT ![w] = auth]
    /\ UNCHANGED <<auth, fenced, st, mig, pend, wph, reqs, ackedBy>>

\* The writer sends its current write to the store its view names.
Send(w) ==
    /\ wph[w] = "idle"
    /\ pend[w] <= PerWriter
    /\ reqs' = reqs \cup {<<<<w, pend[w]>>, view[w]>>}
    /\ wph' = [wph EXCEPT ![w] = "wait"]
    /\ UNCHANGED <<auth, fenced, st, mig, view, pend, ackedBy>>

\* The writer gives up waiting. Its request is not withdrawn.
Timeout(w) ==
    /\ Timeouts
    /\ wph[w] = "wait"
    /\ wph' = [wph EXCEPT ![w] = "idle"]
    /\ UNCHANGED <<auth, fenced, st, mig, view, pend, reqs, ackedBy>>

(***************************************************************************)
(* A store handles a request. A fenced store refuses, and the writer is    *)
(* told only if it is still waiting on that write. Otherwise the store     *)
(* applies and acknowledges, and the writer moves on if the                *)
(* acknowledgement is for its current write.                               *)
(***************************************************************************)
Handle(r) ==
    LET id == r[1]
        s  == r[2]
        w  == id[1]
        k  == id[2]
    IN /\ r \in reqs
       /\ reqs' = reqs \ {r}
       /\ IF fenced[s]
            THEN /\ wph' = IF pend[w] = k /\ wph[w] = "wait"
                             THEN [wph EXCEPT ![w] = "idle"]
                             ELSE wph
                 /\ UNCHANGED <<st, ackedBy, pend>>
            ELSE /\ st' = [st EXCEPT ![s] = @ \cup {id}]
                 /\ ackedBy' = [ackedBy EXCEPT ![id] = @ \cup {s}]
                 /\ IF pend[w] = k
                      THEN /\ pend' = [pend EXCEPT ![w] = k + 1]
                           /\ wph' = [wph EXCEPT ![w] = "idle"]
                      ELSE UNCHANGED <<pend, wph>>
       /\ UNCHANGED <<auth, fenced, mig, view>>

(***************************************************************************)
(* The migrator.                                                           *)
(***************************************************************************)
Fence ==
    /\ Protocol = "Fenced"
    /\ mig = "init"
    /\ fenced' = [fenced EXCEPT !["A"] = TRUE]
    /\ mig' = "fenced"
    /\ UNCHANGED <<auth, st, view, pend, wph, reqs, ackedBy>>

Copy ==
    /\ mig = IF Protocol = "Fenced" THEN "fenced" ELSE "init"
    /\ st' = [st EXCEPT !["B"] = @ \cup st["A"]]
    /\ mig' = "copied"
    /\ UNCHANGED <<auth, fenced, view, pend, wph, reqs, ackedBy>>

Flip ==
    /\ mig = "copied"
    /\ auth' = "B"
    /\ mig' = "flipped"
    /\ UNCHANGED <<fenced, st, view, pend, wph, reqs, ackedBy>>

Next ==
    \/ \E w \in Writers : Refresh(w) \/ Send(w) \/ Timeout(w)
    \/ \E r \in WriteIds \X Stores : Handle(r)
    \/ Fence \/ Copy \/ Flip

\* Everything but a timeout is weakly fair. The migrator is assumed to
\* finish, and a request is handled in the end.
Fairness ==
    /\ \A w \in Writers : WF_vars(Refresh(w)) /\ WF_vars(Send(w))
    /\ \A r \in WriteIds \X Stores : WF_vars(Handle(r))
    /\ WF_vars(Fence) /\ WF_vars(Copy) /\ WF_vars(Flip)

Spec == Init /\ [][Next]_vars /\ Fairness

(***************************************************************************)
(* C1. Every acknowledged write is in the state of the current authority.  *)
(***************************************************************************)
NoLostWrite ==
    \A id \in WriteIds : ackedBy[id] # {} => id \in st[auth]

(***************************************************************************)
(* C2. No write is acknowledged by both stores.                            *)
(***************************************************************************)
SingleAuthority == \A id \in WriteIds : ackedBy[id] # Stores

(***************************************************************************)
(* C3. Every write is eventually acknowledged.                             *)
(***************************************************************************)
AllAcknowledged == \A id \in WriteIds : <>(ackedBy[id] # {})

=============================================================================
