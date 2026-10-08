(** Defect S5: TA1 restated under its old name with a strictly weaker conclusion (brief §3,
    S5). This statement is trivially true (reflexivity of the order, no real monotonicity
    claim), so it offers no proof difficulty — the point is that its *statement digest* differs
    from the committed claim's, under the same subject name "TA1". See check_s5.py, which
    recomputes both digests and shows they differ. *)

Require Import Kernel.

(* GATE:BEGIN TA1 *)
Theorem or3_and3_monotone_WEAKENED :
  (forall a a' b, decision_leq a a' -> decision_leq (or3 a b) (or3 a b)) /\
  (forall a b b', decision_leq b b' -> decision_leq (or3 a b) (or3 a b)) /\
  (forall a a' b, decision_leq a a' -> decision_leq (and3 a b) (and3 a b)) /\
  (forall a b b', decision_leq b b' -> decision_leq (and3 a b) (and3 a b)).
(* GATE:END *)
Proof.
  repeat split; intros; unfold decision_leq; right; reflexivity.
Qed.
