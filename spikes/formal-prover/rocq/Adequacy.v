(** Formal methods track D (the prover spike): adequacy against the reference fixture (brief
    §2.3), from tools/mork_compilers/src/mork_compilers/test_set_readings.py's MIXES data and
    ReadingTests/NegationTests. Each row is checked by [reflexivity]: if the implementation
    disagreed with the reference, these would fail to typecheck, not merely fail to prove. *)

Require Import Kernel.
Require Import Eligibility.
From Stdlib Require Import List.
Import ListNotations.

(* pd = [a;b] = [Permitted; Denied] *)
Theorem adequacy_some_pd : some_value [Permitted; Denied] = Permitted.
Proof. reflexivity. Qed.

Theorem adequacy_some_dd : some_value [Denied; Denied] = Denied.
Proof. reflexivity. Qed.

Theorem adequacy_some_du : some_value [Denied; Undetermined] = Undetermined.
Proof. reflexivity. Qed.

Theorem adequacy_some_pu : some_value [Permitted; Undetermined] = Permitted.
Proof. reflexivity. Qed.

Theorem adequacy_some_none : some_value [] = Undetermined.
Proof. reflexivity. Qed.

Theorem adequacy_every_pp : every_value [Permitted; Permitted] = Permitted.
Proof. reflexivity. Qed.

Theorem adequacy_every_pd : every_value [Permitted; Denied] = Denied.
Proof. reflexivity. Qed.

Theorem adequacy_every_pu : every_value [Permitted; Undetermined] = Undetermined.
Proof. reflexivity. Qed.

Theorem adequacy_every_du : every_value [Denied; Undetermined] = Denied.
Proof. reflexivity. Qed.

Theorem adequacy_every_none : every_value [] = Undetermined.
Proof. reflexivity. Qed.

(** NegationTests.test_negated_bound_condition_swaps_decided_outcomes: negating a SomeValue-read
    condition swaps every decided per-subject outcome, Undetermined fixed. Checked at the point
    L16 specifies: after the reading, as neg3 composed with some_value. *)
Theorem adequacy_negated_pd : neg3 (some_value [Permitted; Denied]) = Denied.
Proof. reflexivity. Qed.

Theorem adequacy_negated_dd : neg3 (some_value [Denied; Denied]) = Permitted.
Proof. reflexivity. Qed.

Theorem adequacy_negated_du : neg3 (some_value [Denied; Undetermined]) = Undetermined.
Proof. reflexivity. Qed.
