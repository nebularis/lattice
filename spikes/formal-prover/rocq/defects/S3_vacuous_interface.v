(** Defect S3: an interface assumption no instantiation can discharge (brief §3, S3; track A5's
    non-vacuity concern, surfaced at this scale). [ReadingInterface] bundles [some_value] and
    [every_value] with the assumption that they always agree — which is false in general (brief
    §2.2, the [pd] fixture), so no instantiation, real or otherwise, can discharge it. *)

Require Import Kernel.
Require Import Eligibility.
From Stdlib Require Import List.
Import ListNotations.

Record ReadingInterface := {
  ri_some : list decision -> decision;
  ri_every : list decision -> decision;
  ri_agree : forall xs, ri_some xs = ri_every xs
}.

(** The real definitions disagree on this very fixture (adequacy row pd), so the assumption is
    not merely unproved here — it is refutable, for any candidate pair of functions equal to
    these on [Permitted; Denied]. *)
Theorem real_definitions_do_not_agree :
  some_value [Permitted; Denied] <> every_value [Permitted; Denied].
Proof. simpl. discriminate. Qed.

Theorem real_definitions_cannot_satisfy_ri_agree :
  ~ (forall xs, some_value xs = every_value xs).
Proof.
  intro H. apply real_definitions_do_not_agree. apply H.
Qed.

(** The obvious instantiation fails to typecheck: no term of the needed type exists. *)
Fail Definition real_instantiation : ReadingInterface :=
  {| ri_some := some_value;
     ri_every := every_value;
     ri_agree := real_definitions_do_not_agree |}.
