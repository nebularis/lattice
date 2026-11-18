\* SPDX-License-Identifier: MPL-2.0
-------------------------- MODULE X1_SerialisedApply --------------------------
(***************************************************************************)
(* Model X1 of MSA-I6, one serialised writer per key applying a stream     *)
(* partition to two stores, A then B.                                      *)
(*                                                                         *)
(* A stream of K commands, seq 1 to K, is published and confirmed one at a *)
(* time. A writer incarnation consumes in order. For each command it       *)
(* applies to store A, then to store B, then stores an offset. Each store  *)
(* applies command c only if its version row is c - 1. A command already   *)
(* applied is answered from its receipt (Duplicate) before the guard is    *)
(* tried, and a command whose guard fails with no receipt is answered      *)
(* Conflict and changes nothing. The writer then goes on, so a rejected    *)
(* command is never retried.                                               *)
(*                                                                         *)
(* A writer may crash at any step. The next incarnation resumes from the   *)
(* stored offset. With Zombie, the next incarnation may also start while   *)
(* the previous one is alive and still acting, which is the takeover of    *)
(* MSAI9-01 and MSAI9-02, and no fence is modelled, so the guard in each   *)
(* store is the only safety device.                                        *)
(*                                                                         *)
(* OffsetMode is "Applied" or "Received". Applied stores the seq of the    *)
(* command just applied to both stores. Received stores the highest seq    *)
(* the incarnation has received, which can be ahead of the last applied    *)
(* by up to W - 1, which is MSAI9-06.                                      *)
(*                                                                         *)
(* A reader, enabled by WithReader, reads A then B in two separate steps   *)
(* once.                                                                   *)
(*                                                                         *)
(* The model terminates, so TLC is run with -deadlock.                     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    K,           \* the number of commands in the partition
    W,           \* the window an incarnation may receive ahead of what it applied
    MaxCrashes,  \* the most crashes in a behaviour
    Zombie,      \* BOOLEAN, a successor may start while its predecessor is alive
    OffsetMode,  \* "Applied" or "Received"
    WithReader   \* BOOLEAN, the one reader of A then B is enabled

ASSUME K \in Nat \ {0}
ASSUME W \in Nat \ {0}
ASSUME MaxCrashes \in Nat
ASSUME Zombie \in BOOLEAN
ASSUME WithReader \in BOOLEAN
ASSUME OffsetMode \in {"Applied", "Received"}

\* One incarnation per possible crash and one more, so one always survives.
NW == MaxCrashes + 1
Inc == 1..NW
Stores == {"A", "B"}

VARIABLES
    confirmed,  \* the commands 1..confirmed are published and confirmed
    stored,     \* the stored offset, the last write wins
    ver,        \* per store: the version row
    rc,         \* per store: the seqs that have a receipt
    eff,        \* per store: how many times each command's effect was applied
    log,        \* per store: the seqs applied, in the order applied
    alive,      \* per incarnation
    pos,        \* per incarnation: the last command it has finished
    recv,       \* per incarnation: the highest seq it has received
    ph,         \* per incarnation: "off", "A", "B", "S" or "dead"
    started,    \* how many incarnations have started
    crashes,    \* how many crashes have happened
    rdPh,       \* the reader: "idle", "gotA" or "done"
    rdA,        \* the version the reader saw in A
    rdB         \* the version the reader saw in B

vars == <<confirmed, stored, ver, rc, eff, log, alive, pos, recv, ph,
          started, crashes, rdPh, rdA, rdB>>

TypeOK ==
    /\ confirmed \in 0..K
    /\ stored \in 0..K
    /\ ver \in [Stores -> 0..K]
    /\ rc \in [Stores -> SUBSET (1..K)]
    /\ \A s \in Stores : eff[s] \in [1..K -> Nat]
    /\ \A s \in Stores : Len(log[s]) <= K + 1
    /\ alive \in [Inc -> BOOLEAN]
    /\ pos \in [Inc -> 0..K]
    /\ recv \in [Inc -> 0..K]
    /\ ph \in [Inc -> {"off", "A", "B", "S", "dead"}]
    /\ started \in 0..NW
    /\ crashes \in 0..MaxCrashes
    /\ rdPh \in {"idle", "gotA", "done"}
    /\ rdA \in 0..K
    /\ rdB \in 0..K

Init ==
    /\ confirmed = 0
    /\ stored = 0
    /\ ver = [s \in Stores |-> 0]
    /\ rc = [s \in Stores |-> {}]
    /\ eff = [s \in Stores |-> [c \in 1..K |-> 0]]
    /\ log = [s \in Stores |-> <<>>]
    /\ alive = [i \in Inc |-> FALSE]
    /\ pos = [i \in Inc |-> 0]
    /\ recv = [i \in Inc |-> 0]
    /\ ph = [i \in Inc |-> "off"]
    /\ started = 0
    /\ crashes = 0
    /\ rdPh = "idle"
    /\ rdA = 0
    /\ rdB = 0

(***************************************************************************)
(* The guarded command in a store, the IR's reading of MSA-I4 section 3.  *)
(* The first guard that fails decides the outcome, a resend is answered    *)
(* Duplicate before the version guard is tried, and the store computes the *)
(* successor.                                                              *)
(***************************************************************************)
Outcome(s, c) ==
    IF c \in rc[s] THEN "Duplicate"
    ELSE IF ver[s] = c - 1 THEN "Applied"
    ELSE "Conflict"

\* A store with no guard and no receipt, which applies every command it is
\* given. A cfg replaces Outcome by this to show what the guard is worth.
UnguardedOutcome(s, c) == "Applied"

ApplyTo(s, c) ==
    IF Outcome(s, c) = "Applied"
      THEN /\ ver' = [ver EXCEPT ![s] = c]
           /\ rc' = [rc EXCEPT ![s] = @ \cup {c}]
           /\ eff' = [eff EXCEPT ![s][c] = @ + 1]
           /\ log' = [log EXCEPT ![s] = Append(@, c)]
      ELSE UNCHANGED <<ver, rc, eff, log>>

\* The stream.
Publish ==
    /\ confirmed < K
    /\ confirmed' = confirmed + 1
    /\ UNCHANGED <<stored, ver, rc, eff, log, alive, pos, recv, ph,
                   started, crashes, rdPh, rdA, rdB>>

\* Whether the incarnation before w is alive. The first has none.
PredAlive(w) == IF w = 1 THEN FALSE ELSE alive[w - 1]

\* A new incarnation resumes from the stored offset. Without Zombie it
\* starts only after its predecessor has crashed.
Start(w) ==
    /\ started = w - 1
    /\ \/ Zombie
       \/ ~PredAlive(w)
    /\ alive' = [alive EXCEPT ![w] = TRUE]
    /\ pos' = [pos EXCEPT ![w] = stored]
    /\ recv' = [recv EXCEPT ![w] = stored]
    /\ ph' = [ph EXCEPT ![w] = "A"]
    /\ started' = w
    /\ UNCHANGED <<confirmed, stored, ver, rc, eff, log, crashes,
                   rdPh, rdA, rdB>>

\* The incarnation receives the next confirmed command, up to W ahead of
\* the last one it finished.
Receive(w) ==
    /\ alive[w]
    /\ recv[w] < confirmed
    /\ recv[w] - pos[w] < W
    /\ recv' = [recv EXCEPT ![w] = @ + 1]
    /\ UNCHANGED <<confirmed, stored, ver, rc, eff, log, alive, pos, ph,
                   started, crashes, rdPh, rdA, rdB>>

\* The command after the last one the incarnation finished, to store A.
\* A Conflict from A means the command is rejected, so B is skipped.
ApplyA(w) ==
    /\ alive[w]
    /\ ph[w] = "A"
    /\ recv[w] > pos[w]
    /\ ApplyTo("A", pos[w] + 1)
    /\ ph' = [ph EXCEPT ![w] = IF Outcome("A", pos[w] + 1) = "Conflict"
                                 THEN "S" ELSE "B"]
    /\ UNCHANGED <<confirmed, stored, alive, pos, recv, started, crashes,
                   rdPh, rdA, rdB>>

ApplyB(w) ==
    /\ alive[w]
    /\ ph[w] = "B"
    /\ ApplyTo("B", pos[w] + 1)
    /\ ph' = [ph EXCEPT ![w] = "S"]
    /\ UNCHANGED <<confirmed, stored, alive, pos, recv, started, crashes,
                   rdPh, rdA, rdB>>

\* Store the offset, then the incarnation has finished the command. Applied
\* stores the seq just applied to both stores. Received stores the highest
\* seq received, the defect of MSAI9-06.
StoreOffset(w) ==
    /\ alive[w]
    /\ ph[w] = "S"
    /\ stored' = IF OffsetMode = "Applied" THEN pos[w] + 1 ELSE recv[w]
    /\ pos' = [pos EXCEPT ![w] = @ + 1]
    /\ ph' = [ph EXCEPT ![w] = "A"]
    /\ UNCHANGED <<confirmed, ver, rc, eff, log, alive, recv, started,
                   crashes, rdPh, rdA, rdB>>

Step(w) == Receive(w) \/ ApplyA(w) \/ ApplyB(w) \/ StoreOffset(w)

\* A crash at any step. Nothing the incarnation held in memory survives.
Crash(w) ==
    /\ alive[w]
    /\ crashes < MaxCrashes
    /\ alive' = [alive EXCEPT ![w] = FALSE]
    /\ ph' = [ph EXCEPT ![w] = "dead"]
    /\ crashes' = crashes + 1
    /\ UNCHANGED <<confirmed, stored, ver, rc, eff, log, pos, recv, started,
                   rdPh, rdA, rdB>>

\* The reader reads A, then later reads B, in two separate steps.
ReadA ==
    /\ WithReader
    /\ rdPh = "idle"
    /\ rdA' = ver["A"]
    /\ rdPh' = "gotA"
    /\ UNCHANGED <<confirmed, stored, ver, rc, eff, log, alive, pos, recv, ph,
                   started, crashes, rdB>>

ReadB ==
    /\ rdPh = "gotA"
    /\ rdB' = ver["B"]
    /\ rdPh' = "done"
    /\ UNCHANGED <<confirmed, stored, ver, rc, eff, log, alive, pos, recv, ph,
                   started, crashes, rdA>>

Next ==
    \/ Publish
    \/ ReadA
    \/ ReadB
    \/ \E w \in Inc : Start(w) \/ Step(w) \/ Crash(w)

\* Publication and each live incarnation's steps are weakly fair, and so is
\* the start of the first incarnation and of a successor after a crash. A
\* start while the predecessor is alive is not forced, and a crash is never
\* forced.
Fairness ==
    /\ WF_vars(Publish)
    /\ WF_vars(Start(1))
    /\ \A w \in 2..NW : WF_vars(Start(w) /\ ~PredAlive(w))
    /\ \A w \in Inc : WF_vars(Step(w))

Spec == Init /\ [][Next]_vars /\ Fairness

(***************************************************************************)
(* S1. Each store's state reflects each command at most once, and its      *)
(* version row is the count of commands applied, so it rises by exactly 1  *)
(* per command.                                                            *)
(***************************************************************************)
EachAppliedOnceInEffect ==
    \A s \in Stores :
        /\ \A c \in 1..K : eff[s][c] <= 1
        /\ ver[s] = Len(log[s])

VersionStepsByOne ==
    [][\A s \in Stores : ver'[s] = ver[s] \/ ver'[s] = ver[s] + 1]_vars

(***************************************************************************)
(* S2. Each store applies commands in seq order.                           *)
(***************************************************************************)
OrderPerKey ==
    \A s \in Stores :
        \A i, j \in DOMAIN log[s] : i < j => log[s][i] < log[s][j]

\* Also checked. Every writer applies A before B, so B is never ahead of A.
AThenB == ver["B"] <= ver["A"]

(***************************************************************************)
(* L1. Every confirmed command is eventually applied in both stores.       *)
(***************************************************************************)
EventuallyApplied ==
    \A c \in 1..K :
        (c <= confirmed) ~> (c \in rc["A"] /\ c \in rc["B"])

(***************************************************************************)
(* T1. A reader never sees A and B at different versions. Expected to      *)
(* fail.                                                                   *)
(***************************************************************************)
NoTornRead == rdPh = "done" => rdA = rdB

\* Also expected to fail. After a crash, with no incarnation alive, A and B
\* are at the same version. A crash between the two applies breaks it,
\* which is the sequence of section 4.2 of the sketch.
NoStrandedHalfApply ==
    ~(/\ crashes > 0
      /\ \A i \in Inc : ~alive[i]
      /\ ver["A"] # ver["B"])

=============================================================================
