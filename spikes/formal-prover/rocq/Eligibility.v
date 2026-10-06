(** Formal methods track D (the prover spike): Eligibility's set readings and negation,
    target TL (docs/developer/validation/formal-methods-0.md §2.2), elg:L15 and elg:L16. *)

Require Import Kernel.
From Stdlib Require Import List.
Import ListNotations.

(** [some_value]/[every_value] read a nonempty fold (the per-value decisions have already been
    decided elsewhere; this is the combination step L15 governs), with the empty case stated
    directly, matching the law's own words ("Undetermined ... when there is no value"). *)
Definition some_value (xs : list decision) : decision :=
  match xs with
  | [] => Undetermined
  | x :: rest => fold_left or3 rest x
  end.

Definition every_value (xs : list decision) : decision :=
  match xs with
  | [] => Undetermined
  | x :: rest => fold_left and3 rest x
  end.

(** 1. Finite facts about or3/and3, read off their definitions. *)

Lemma or3_eq_permitted_iff : forall a b, or3 a b = Permitted <-> a = Permitted \/ b = Permitted.
Proof. intros a b. destruct a, b; simpl; intuition congruence. Qed.

Lemma or3_eq_denied_iff : forall a b, or3 a b = Denied <-> a = Denied /\ b = Denied.
Proof. intros a b. destruct a, b; simpl; intuition congruence. Qed.

Lemma and3_eq_denied_iff : forall a b, and3 a b = Denied <-> a = Denied \/ b = Denied.
Proof. intros a b. destruct a, b; simpl; intuition congruence. Qed.

Lemma and3_eq_permitted_iff : forall a b, and3 a b = Permitted <-> a = Permitted /\ b = Permitted.
Proof. intros a b. destruct a, b; simpl; intuition congruence. Qed.

(** 2. The fold, generalised over its accumulator, so induction on the list is routine. *)

Lemma fold_or3_permitted : forall rest acc,
  fold_left or3 rest acc = Permitted <-> acc = Permitted \/ In Permitted rest.
Proof.
  induction rest as [| y rest IH]; intros acc; simpl.
  - split; [intros H; left; exact H | intros [H | []]; exact H].
  - rewrite IH, or3_eq_permitted_iff. intuition congruence.
Qed.

Lemma fold_or3_denied : forall rest acc,
  fold_left or3 rest acc = Denied <-> acc = Denied /\ Forall (eq Denied) rest.
Proof.
  induction rest as [| y rest IH]; intros acc; simpl.
  - split.
    + intros H. split; [exact H | constructor].
    + intros [H _]. exact H.
  - rewrite IH, or3_eq_denied_iff. split.
    + intros [[Ha Hy] HF]. split; [exact Ha | constructor; [symmetry; exact Hy | exact HF]].
    + intros [Ha HF]. split; [split | apply (Forall_inv_tail HF)].
      * exact Ha.
      * symmetry. exact (Forall_inv HF).
Qed.

Lemma fold_and3_denied : forall rest acc,
  fold_left and3 rest acc = Denied <-> acc = Denied \/ In Denied rest.
Proof.
  induction rest as [| y rest IH]; intros acc; simpl.
  - split; [intros H; left; exact H | intros [H | []]; exact H].
  - rewrite IH, and3_eq_denied_iff. intuition congruence.
Qed.

Lemma fold_and3_permitted : forall rest acc,
  fold_left and3 rest acc = Permitted <-> acc = Permitted /\ Forall (eq Permitted) rest.
Proof.
  induction rest as [| y rest IH]; intros acc; simpl.
  - split.
    + intros H. split; [exact H | constructor].
    + intros [H _]. exact H.
  - rewrite IH, and3_eq_permitted_iff. split.
    + intros [[Ha Hy] HF]. split; [exact Ha | constructor; [symmetry; exact Hy | exact HF]].
    + intros [Ha HF]. split; [split | apply (Forall_inv_tail HF)].
      * exact Ha.
      * symmetry. exact (Forall_inv HF).
Qed.

(** A list over this 3-constructor type, with neither of two excluded values anywhere, holds
    only the third throughout: a plain structural induction, no decidable equality needed. *)
Lemma all_the_third : forall xs,
  ~ In Permitted xs -> ~ In Undetermined xs -> Forall (eq Denied) xs.
Proof.
  induction xs as [| x xs IH]; intros Hnp Hnu.
  - constructor.
  - destruct x.
    + exfalso. apply Hnp. left. reflexivity.
    + constructor.
      * reflexivity.
      * apply IH.
        -- intro H. apply Hnp. right. exact H.
        -- intro H. apply Hnu. right. exact H.
    + exfalso. apply Hnu. left. reflexivity.
Qed.

Lemma all_the_third' : forall xs,
  ~ In Denied xs -> ~ In Undetermined xs -> Forall (eq Permitted) xs.
Proof.
  induction xs as [| x xs IH]; intros Hnd Hnu.
  - constructor.
  - destruct x.
    + constructor.
      * reflexivity.
      * apply IH.
        -- intro H. apply Hnd. right. exact H.
        -- intro H. apply Hnu. right. exact H.
    + exfalso. apply Hnd. left. reflexivity.
    + exfalso. apply Hnu. left. reflexivity.
Qed.

(** 3. TL1: L15's statement, in the law's own terms, independent of the fold. One combined
    theorem per reading (three clauses each), matching the brief's "and the dual for
    EveryValue". *)

(* GATE:BEGIN TL1-some *)
Theorem some_value_spec : forall xs,
  (some_value xs = Permitted <-> In Permitted xs) /\
  (some_value xs = Denied <-> xs <> [] /\ Forall (eq Denied) xs) /\
  (some_value xs = Undetermined <->
     xs = [] \/ (~ In Permitted xs /\ In Undetermined xs)).
(* GATE:END *)
Proof.
  intros xs. destruct xs as [| x rest].
  - unfold some_value. split; [| split].
    + split; [intro H; discriminate H | intro H; destruct H].
    + split; [intro H; discriminate H | intros [Hne _]; exfalso; apply Hne; reflexivity].
    + split; [intros _; left; reflexivity | intros _; reflexivity].
  - unfold some_value.
    assert (Hp : fold_left or3 rest x = Permitted <-> In Permitted (x :: rest)).
    { rewrite fold_or3_permitted. simpl. tauto. }
    assert (Hd : fold_left or3 rest x = Denied <->
                 (x :: rest) <> [] /\ Forall (eq Denied) (x :: rest)).
    { rewrite fold_or3_denied. split.
      - intros [Hx HF]. split; [discriminate | constructor; [symmetry; exact Hx | exact HF]].
      - intros [_ HF]. split; [symmetry; exact (Forall_inv HF) | exact (Forall_inv_tail HF)]. }
    split; [exact Hp |]. split; [exact Hd |]. split.
    + intros H. right. split.
      * intro Hin. apply Hp in Hin. rewrite H in Hin. discriminate.
      * destruct (in_dec decision_eq_dec Undetermined (x :: rest)) as [Hin | Hnin].
        -- exact Hin.
        -- exfalso.
           assert (Hnp : ~ In Permitted (x :: rest)).
           { intro Hin. apply Hp in Hin. rewrite H in Hin. discriminate. }
           assert (HF : Forall (eq Denied) (x :: rest)) by (apply all_the_third; assumption).
           assert (HD : fold_left or3 rest x = Denied) by (apply Hd; split; [discriminate | exact HF]).
           rewrite H in HD. discriminate.
    + intros [Heq | [Hnp Hu]]; [discriminate Heq |].
      assert (Hnotp : fold_left or3 rest x <> Permitted).
      { intro Hc. apply Hnp. apply Hp. exact Hc. }
      assert (Hnotd : fold_left or3 rest x <> Denied).
      { intro Hc. apply Hd in Hc as [_ HF]. rewrite Forall_forall in HF.
        specialize (HF Undetermined Hu). discriminate HF. }
      destruct (fold_left or3 rest x) eqn:Hsv.
      * exfalso. apply Hnotp. reflexivity.
      * exfalso. apply Hnotd. reflexivity.
      * reflexivity.
Qed.

(* GATE:BEGIN TL1-every *)
Theorem every_value_spec : forall xs,
  (every_value xs = Denied <-> In Denied xs) /\
  (every_value xs = Permitted <-> xs <> [] /\ Forall (eq Permitted) xs) /\
  (every_value xs = Undetermined <->
     xs = [] \/ (~ In Denied xs /\ In Undetermined xs)).
(* GATE:END *)
Proof.
  intros xs. destruct xs as [| x rest].
  - unfold every_value. split; [| split].
    + split; [intro H; discriminate H | intro H; destruct H].
    + split; [intro H; discriminate H | intros [Hne _]; exfalso; apply Hne; reflexivity].
    + split; [intros _; left; reflexivity | intros _; reflexivity].
  - unfold every_value.
    assert (Hd : fold_left and3 rest x = Denied <-> In Denied (x :: rest)).
    { rewrite fold_and3_denied. simpl. tauto. }
    assert (Hp : fold_left and3 rest x = Permitted <->
                 (x :: rest) <> [] /\ Forall (eq Permitted) (x :: rest)).
    { rewrite fold_and3_permitted. split.
      - intros [Hx HF]. split; [discriminate | constructor; [symmetry; exact Hx | exact HF]].
      - intros [_ HF]. split; [symmetry; exact (Forall_inv HF) | exact (Forall_inv_tail HF)]. }
    split; [exact Hd |]. split; [exact Hp |]. split.
    + intros H. right. split.
      * intro Hin. apply Hd in Hin. rewrite H in Hin. discriminate.
      * destruct (in_dec decision_eq_dec Undetermined (x :: rest)) as [Hin | Hnin].
        -- exact Hin.
        -- exfalso.
           assert (Hnd : ~ In Denied (x :: rest)).
           { intro Hin. apply Hd in Hin. rewrite H in Hin. discriminate. }
           assert (HF : Forall (eq Permitted) (x :: rest)) by (apply all_the_third'; assumption).
           assert (HP : fold_left and3 rest x = Permitted) by (apply Hp; split; [discriminate | exact HF]).
           rewrite H in HP. discriminate.
    + intros [Heq | [Hnd Hu]]; [discriminate Heq |].
      assert (Hnotd : fold_left and3 rest x <> Denied).
      { intro Hc. apply Hnd. apply Hd. exact Hc. }
      assert (Hnotp : fold_left and3 rest x <> Permitted).
      { intro Hc. apply Hp in Hc as [_ HF]. rewrite Forall_forall in HF.
        specialize (HF Undetermined Hu). discriminate HF. }
      destruct (fold_left and3 rest x) eqn:Hsv.
      * exfalso. apply Hnotp. reflexivity.
      * exfalso. apply Hnotd. reflexivity.
      * reflexivity.
Qed.

(** TL2: monotonicity, lifted from TA1 by induction (plan's architectural point: L15 composes
    the kernel's own monotonicity rather than needing a fresh argument). *)

Definition decision_leq_list := Forall2 decision_leq.

(* GATE:BEGIN TL2 *)
Theorem some_every_value_monotone :
  (forall xs ys, decision_leq_list xs ys -> decision_leq (some_value xs) (some_value ys)) /\
  (forall xs ys, decision_leq_list xs ys -> decision_leq (every_value xs) (every_value ys)).
(* GATE:END *)
Proof.
  split.
  - intros xs ys H. destruct H as [| x y rest rest' Hxy Hrest].
    + simpl. unfold decision_leq. right. reflexivity.
    + simpl. revert x y Hxy.
      induction Hrest as [| a b rest rest' Hab Hrest IH]; intros x y Hxy; simpl.
      * exact Hxy.
      * apply IH. apply or3_monotone2; assumption.
  - intros xs ys H. destruct H as [| x y rest rest' Hxy Hrest].
    + simpl. unfold decision_leq. right. reflexivity.
    + simpl. revert x y Hxy.
      induction Hrest as [| a b rest rest' Hab Hrest IH]; intros x y Hxy; simpl.
      * exact Hxy.
      * apply IH. apply and3_monotone2; assumption.
Qed.

(** TL3(a): De Morgan duality holds always. *)
(* GATE:BEGIN TL3a *)
Theorem negate_after_is_every_of_negated : forall xs,
  neg3 (some_value xs) = every_value (map neg3 xs).
(* GATE:END *)
Proof.
  intros xs. destruct xs as [| x rest]; [reflexivity |].
  unfold some_value, every_value. simpl.
  revert x. induction rest as [| y rest IH]; intros x; simpl; [reflexivity |].
  rewrite IH. f_equal. destruct x, y; reflexivity.
Qed.

(** TL3(b): negating each value first and keeping the SAME reading disagrees in general — the
    wrong alternative L16's "evaluated as it stands ... and then" rules out. Disproved with the
    brief's witness. *)
(* GATE:BEGIN TL3b *)
Theorem negate_before_same_reading_disagrees :
  exists xs, neg3 (some_value xs) <> some_value (map neg3 xs).
(* GATE:END *)
Proof.
  exists [Permitted; Denied].
  simpl. discriminate.
Qed.
