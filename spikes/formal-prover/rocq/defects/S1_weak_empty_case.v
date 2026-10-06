(** Defect S1: "every value returns Permitted when there is no value" — some_value's empty
    case is weakened from Undetermined to Permitted (brief §3, S1). Shows what breaks: TL1's
    third clause for the empty list, and the adequacy oracle's "none" row. *)

Require Import Kernel.
From Stdlib Require Import List.
Import ListNotations.

Definition some_value_broken (xs : list decision) : decision :=
  match xs with
  | [] => Permitted (* was Undetermined *)
  | x :: rest => fold_left or3 rest x
  end.

(** Detection 1: the adequacy oracle's "no value" row no longer holds. A concrete, provable
    refutation, not merely a failed tactic. *)
Theorem adequacy_some_none_breaks : some_value_broken [] <> Undetermined.
Proof. simpl. discriminate. Qed.

(** Detection 2: TL1's own statement (every xs, including xs = []) is false for the broken
    definition — not merely hard to prove, but refutable. *)
Theorem some_value_broken_breaks_TL1 :
  ~ (forall xs,
       some_value_broken xs = Undetermined <->
       xs = [] \/ (~ In Permitted xs /\ In Undetermined xs)).
Proof.
  intro H. specialize (H []).
  destruct H as [_ H2].
  assert (Htrue : ([] : list decision) = [] \/ (~ In Permitted [] /\ In Undetermined [])) by (left; reflexivity).
  apply H2 in Htrue. discriminate Htrue.
Qed.
