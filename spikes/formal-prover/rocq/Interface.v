(** M6's interface: a reading is admissible only if it is monotone in the information order over
    its list argument (brief §5.1, narrowed scope). [MonotoneReading] bundles a function with a
    proof of that property, so an attempt to register a non-monotone candidate is a type error
    at construction time, not a separate proof obligation discovered later. Rocq's dependent
    records give this for free; comparing this to how the same requirement is expressed in
    Isabelle (a locale assumption, discharged at `interpretation` time) is D3/D4's job. *)

Require Import Kernel.
Require Import Eligibility.
From Stdlib Require Import List.
Import ListNotations.

Definition monotone_on_lists (f : list decision -> decision) : Prop :=
  forall xs ys, decision_leq_list xs ys -> decision_leq (f xs) (f ys).

Record MonotoneReading := {
  mr_apply : list decision -> decision;
  mr_monotone : monotone_on_lists mr_apply
}.

(* GATE:BEGIN TR4 *)
Definition some_value_reading : MonotoneReading :=
  {| mr_apply := some_value; mr_monotone := proj1 some_every_value_monotone |}.
(* GATE:END *)

(* GATE:BEGIN TR5 *)
Definition every_value_reading : MonotoneReading :=
  {| mr_apply := every_value; mr_monotone := proj2 some_every_value_monotone |}.
(* GATE:END *)

(** A deliberately non-monotone candidate: "Permitted if the list contains an Undetermined
    entry, else Denied" looks at its argument's values, but the wrong way round — refining an
    Undetermined entry to something more informative can only ever *remove* an Undetermined, so
    a well-behaved reading could only move towards Denied as information increases, never away
    from it. [inverted_reading] does the opposite on [Undetermined] vs [Permitted], so it cannot
    be registered: the attempt fails to typecheck, since no term of type
    [monotone_on_lists inverted_reading] exists. *)
Definition has_undetermined (xs : list decision) : bool :=
  existsb (fun x => match x with Undetermined => true | _ => false end) xs.

Definition inverted_reading (xs : list decision) : decision :=
  if has_undetermined xs then Permitted else Denied.

Theorem inverted_reading_not_monotone : ~ monotone_on_lists inverted_reading.
Proof.
  intro H.
  specialize (H [Undetermined] [Permitted]).
  assert (Hrel : decision_leq_list [Undetermined] [Permitted]).
  { apply Forall2_cons; [left; reflexivity | apply Forall2_nil]. }
  apply H in Hrel. simpl in Hrel. unfold decision_leq in Hrel. destruct Hrel; discriminate.
Qed.

Fail Definition inverted_value_reading : MonotoneReading :=
  {| mr_apply := inverted_reading; mr_monotone := inverted_reading_not_monotone |}.
