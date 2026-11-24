\* SPDX-License-Identifier: MPL-2.0
----------------------------- MODULE X3_Unplaced -----------------------------
(***************************************************************************)
(* A check that X3's Spec implements its SpecUnplaced for the per-stream   *)
(* relay, so that what TLC finds of SpecUnplaced at a larger instance      *)
(* holds of Spec for a property that reads no position.                    *)
(*                                                                         *)
(* U is X3 with pos and nextPos replaced by their first values, which is   *)
(* what SpecUnplaced leaves them at. Refines says every behaviour of Spec, *)
(* seen with its positions hidden, is a behaviour of SpecUnplaced, its     *)
(* fairness included. R1 to R3 read no position, so each is the same       *)
(* formula in U, and holds of Spec where it holds of SpecUnplaced.         *)
(*                                                                         *)
(* UnplacedSteps is the step half of Refines alone. The relay by position  *)
(* reads pos, and SpecUnplaced has no step for it, so UnplacedSteps is     *)
(* expected to fail there, which shows the check can fail.                 *)
(***************************************************************************)
EXTENDS X3_ReceiptRelay

U == INSTANCE X3_ReceiptRelay
         WITH pos <- [r \in Receipts |-> 0], nextPos <- 1

Refines == U!SpecUnplaced

UnplacedSteps == [][U!NextUnplaced]_(U!vars)

=============================================================================
