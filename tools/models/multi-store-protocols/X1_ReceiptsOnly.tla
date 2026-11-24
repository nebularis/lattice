\* SPDX-License-Identifier: MPL-2.0
---------------------------- MODULE X1_ReceiptsOnly ----------------------------
(***************************************************************************)
(* Model X1 with the stores the studio has, which keep a receipt for each  *)
(* command id and no version row for the partition.                        *)
(*                                                                         *)
(* The writer, the stream, the offsets, the crashes and the zombie are     *)
(* X1's, unchanged. A configuration replaces X1's Outcome by               *)
(* ReceiptOutcome, so a store answers a command that has a receipt         *)
(* Duplicate and applies every other command it is given. Each command     *)
(* writes an aggregate of its own, so an aggregate's revision never        *)
(* refuses it, and the partition's order is guarded by nothing in the      *)
(* store.                                                                  *)
(*                                                                         *)
(* X1's variable ver then holds the seq of the last command a store        *)
(* applied, which is what X1's version row would hold. X1's S1 states that *)
(* it equals the count of commands applied, so S1 is read here as "no      *)
(* command was skipped". AtMostOnce and NoGap state the two halves on      *)
(* their own.                                                              *)
(***************************************************************************)
EXTENDS X1_SerialisedApply

\* A store with receipts and no partition row. A command already applied is
\* answered from its receipt, and any other command is applied.
ReceiptOutcome(s, c) ==
    IF c \in rc[s] THEN "Duplicate" ELSE "Applied"

\* The first half of S1, that no command's effect is applied twice to a store.
AtMostOnce ==
    \A s \in Stores : \A c \in 1..K : eff[s][c] <= 1

\* A store holds no command after one it lacks.
NoGap ==
    \A s \in Stores : \A c \in rc[s] : \A d \in 1..(c - 1) : d \in rc[s]

\* Store B holds no command after one that A holds and B lacks, the gap of
\* the second store alone.
NoGapBehindA ==
    \A c \in rc["B"] : \A d \in rc["A"] : d < c => d \in rc["B"]

=============================================================================
