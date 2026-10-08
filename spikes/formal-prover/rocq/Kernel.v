(** Formal methods track D (the prover spike): the three-valued logic kernel, target TA
    (docs/developer/validation/formal-methods-0.md §2.1).

    GATE markers delimit the exact statement text the gate script digests (S5: an unreviewed
    restatement under the same name must be caught). *)

Inductive decision : Type :=
  | Permitted : decision
  | Denied : decision
  | Undetermined : decision.

(** Decidable equality, generated rather than hand-written, used by Eligibility.v to case-split
    constructively on list membership (no classical axiom needed, since the domain is finite). *)
Scheme Equality for decision.

(** The information order: Undetermined is below everything; otherwise a value is only below
    itself. *)
Definition decision_leq (u x : decision) : Prop :=
  u = Undetermined \/ u = x.

(** Strong Kleene disjunction and conjunction. *)
Definition or3 (a b : decision) : decision :=
  match a, b with
  | Permitted, _ => Permitted
  | _, Permitted => Permitted
  | Denied, Denied => Denied
  | _, _ => Undetermined
  end.

Definition and3 (a b : decision) : decision :=
  match a, b with
  | Denied, _ => Denied
  | _, Denied => Denied
  | Permitted, Permitted => Permitted
  | _, _ => Undetermined
  end.

Definition neg3 (a : decision) : decision :=
  match a with
  | Permitted => Denied
  | Denied => Permitted
  | Undetermined => Undetermined
  end.

(* GATE:BEGIN TA1 *)
Theorem or3_and3_monotone :
  (forall a a' b, decision_leq a a' -> decision_leq (or3 a b) (or3 a' b)) /\
  (forall a b b', decision_leq b b' -> decision_leq (or3 a b) (or3 a b')) /\
  (forall a a' b, decision_leq a a' -> decision_leq (and3 a b) (and3 a' b)) /\
  (forall a b b', decision_leq b b' -> decision_leq (and3 a b) (and3 a b')).
(* GATE:END *)
Proof.
  split; [| split; [| split]].
  - intros a a' b [Hu | Heq].
    + subst a. destruct a', b; simpl; unfold decision_leq; auto.
    + subst a'. unfold decision_leq. right. reflexivity.
  - intros a b b' [Hu | Heq].
    + subst b. destruct a, b'; simpl; unfold decision_leq; auto.
    + subst b'. unfold decision_leq. right. reflexivity.
  - intros a a' b [Hu | Heq].
    + subst a. destruct a', b; simpl; unfold decision_leq; auto.
    + subst a'. unfold decision_leq. right. reflexivity.
  - intros a b b' [Hu | Heq].
    + subst b. destruct a, b'; simpl; unfold decision_leq; auto.
    + subst b'. unfold decision_leq. right. reflexivity.
Qed.

(* GATE:BEGIN TA2 *)
Theorem neg3_laws :
  (forall a, neg3 (neg3 a) = a) /\
  (forall a a', decision_leq a a' -> decision_leq (neg3 a) (neg3 a')) /\
  neg3 Undetermined = Undetermined.
(* GATE:END *)
Proof.
  split; [| split].
  - intros a. destruct a; reflexivity.
  - intros a a' [Hu | Heq].
    + subst a. simpl. unfold decision_leq. left. reflexivity.
    + subst a'. unfold decision_leq. right. reflexivity.
  - reflexivity.
Qed.

(** decision_leq is a preorder (reflexive by its own "u=x" disjunct, transitive here), which TL2
    (Eligibility.v) needs to chain one-argument monotonicity into two-argument monotonicity. *)
Lemma decision_leq_trans : forall a b c, decision_leq a b -> decision_leq b c -> decision_leq a c.
Proof.
  unfold decision_leq. intros a b c [Ha | Ha] [Hb | Hb].
  - left. exact Ha.
  - left. exact Ha.
  - rewrite Ha. left. exact Hb.
  - rewrite Ha. right. exact Hb.
Qed.

(** Two-argument monotonicity, by chaining or3_and3_monotone's one-sided facts through
    decision_leq_trans. *)
Lemma or3_monotone2 : forall a a' b b',
  decision_leq a a' -> decision_leq b b' -> decision_leq (or3 a b) (or3 a' b').
Proof.
  intros a a' b b' Ha Hb.
  destruct or3_and3_monotone as [Mol [Mor _]].
  apply (decision_leq_trans (or3 a b) (or3 a' b) (or3 a' b')).
  - apply Mol. exact Ha.
  - apply Mor. exact Hb.
Qed.

Lemma and3_monotone2 : forall a a' b b',
  decision_leq a a' -> decision_leq b b' -> decision_leq (and3 a b) (and3 a' b').
Proof.
  intros a a' b b' Ha Hb.
  destruct or3_and3_monotone as [_ [_ [Mal Mar]]].
  apply (decision_leq_trans (and3 a b) (and3 a' b) (and3 a' b')).
  - apply Mal. exact Ha.
  - apply Mar. exact Hb.
Qed.
