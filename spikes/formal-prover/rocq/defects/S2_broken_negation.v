(** Defect S2: "negation maps Undetermined to Denied" — neg3's third clause is weakened
    (brief §3, S2). Breaks TA2: the involution and the Undetermined fixed point. *)

Require Import Kernel.

Definition neg3_broken (a : decision) : decision :=
  match a with
  | Permitted => Denied
  | Denied => Permitted
  | Undetermined => Denied (* was Undetermined *)
  end.

Theorem neg3_broken_breaks_fixed_point : neg3_broken Undetermined <> Undetermined.
Proof. simpl. discriminate. Qed.

Theorem neg3_broken_breaks_involution : neg3_broken (neg3_broken Undetermined) <> Undetermined.
Proof. simpl. discriminate. Qed.
