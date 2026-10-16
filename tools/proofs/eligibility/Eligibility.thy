(* Eligibility's set readings and negation (target TL, ADR-A103, L15/L16), hand-written on top
   of KernelLaws. Restated from spikes/formal-prover/isabelle/Eligibility.thy (track D's spike),
   re-pointed at this layer's own KernelLaws rather than a self-contained Kernel.

   Restated for closures (ADR-A105, L15 as restated, L17, CCS HQ-6a.1): each reading takes
   whether the binding is closed. Closed, some_value folds or3 from Denied and every_value folds
   and3 from Permitted, each its connective's identity (or3_identity, and3_identity), so the
   empty case decides. Open, a reading decides only what a record proves: some_value is
   Permitted when a value is Permitted, every_value Denied when a value is Denied, and each is
   otherwise Undetermined. *)

theory Eligibility
imports KernelLaws
begin

fun some_value :: "bool \<Rightarrow> decision list \<Rightarrow> decision" where
  "some_value closed xs = (if closed then fold or3 xs Denied
                           else if Permitted \<in> set xs then Permitted else Undetermined)"

fun every_value :: "bool \<Rightarrow> decision list \<Rightarrow> decision" where
  "every_value closed xs = (if closed then fold and3 xs Permitted
                            else if Denied \<in> set xs then Denied else Undetermined)"

lemma fold_or3_permitted: "(fold or3 xs x = Permitted) \<longleftrightarrow> (Permitted \<in> set (x # xs))"
proof (induct xs arbitrary: x)
  case Nil then show ?case by (cases x; simp)
next
  case (Cons y ys x) then show ?case by (cases x; cases y; simp)
qed

lemma fold_or3_denied: "(fold or3 xs x = Denied) \<longleftrightarrow> (\<forall>z \<in> set (x # xs). z = Denied)"
proof (induct xs arbitrary: x)
  case Nil then show ?case by (cases x; simp)
next
  case (Cons y ys x) then show ?case by (cases x; cases y; simp)
qed

lemma fold_or3_undetermined: "(fold or3 xs x = Undetermined) \<longleftrightarrow>
         (Permitted \<notin> set (x # xs) \<and> Undetermined \<in> set (x # xs))"
proof (induct xs arbitrary: x)
  case Nil then show ?case by (cases x; simp)
next
  case (Cons y ys x) then show ?case by (cases x; cases y; simp)
qed

lemma fold_and3_denied: "(fold and3 xs x = Denied) \<longleftrightarrow> (Denied \<in> set (x # xs))"
proof (induct xs arbitrary: x)
  case Nil then show ?case by (cases x; simp)
next
  case (Cons y ys x) then show ?case by (cases x; cases y; simp)
qed

lemma fold_and3_permitted: "(fold and3 xs x = Permitted) \<longleftrightarrow> (\<forall>z \<in> set (x # xs). z = Permitted)"
proof (induct xs arbitrary: x)
  case Nil then show ?case by (cases x; simp)
next
  case (Cons y ys x) then show ?case by (cases x; cases y; simp)
qed

lemma fold_and3_undetermined: "(fold and3 xs x = Undetermined) \<longleftrightarrow>
         (Denied \<notin> set (x # xs) \<and> Undetermined \<in> set (x # xs))"
proof (induct xs arbitrary: x)
  case Nil then show ?case by (cases x; simp)
next
  case (Cons y ys x) then show ?case by (cases x; cases y; simp)
qed

(* GATE:BEGIN TL1-some *)
lemma some_value_spec_permitted: "(some_value closed xs = Permitted) \<longleftrightarrow> Permitted \<in> set xs"
  and some_value_spec_denied: "(some_value closed xs = Denied) \<longleftrightarrow> closed \<and> (\<forall>x \<in> set xs. x = Denied)"
  and some_value_spec_undetermined: "(some_value closed xs = Undetermined) \<longleftrightarrow>
        Permitted \<notin> set xs \<and> (\<not> closed \<or> Undetermined \<in> set xs)"
(* GATE:END *)
proof -
  show "(some_value closed xs = Permitted) \<longleftrightarrow> Permitted \<in> set xs"
    by (cases closed; simp add: fold_or3_permitted)
  show "(some_value closed xs = Denied) \<longleftrightarrow> closed \<and> (\<forall>x \<in> set xs. x = Denied)"
    by (cases closed; simp add: fold_or3_denied)
  show "(some_value closed xs = Undetermined) \<longleftrightarrow>
        Permitted \<notin> set xs \<and> (\<not> closed \<or> Undetermined \<in> set xs)"
    by (cases closed; simp add: fold_or3_undetermined)
qed

(* GATE:BEGIN TL1-every *)
lemma every_value_spec_denied: "(every_value closed xs = Denied) \<longleftrightarrow> Denied \<in> set xs"
  and every_value_spec_permitted: "(every_value closed xs = Permitted) \<longleftrightarrow> closed \<and> (\<forall>x \<in> set xs. x = Permitted)"
  and every_value_spec_undetermined: "(every_value closed xs = Undetermined) \<longleftrightarrow>
        Denied \<notin> set xs \<and> (\<not> closed \<or> Undetermined \<in> set xs)"
(* GATE:END *)
proof -
  show "(every_value closed xs = Denied) \<longleftrightarrow> Denied \<in> set xs"
    by (cases closed; simp add: fold_and3_denied)
  show "(every_value closed xs = Permitted) \<longleftrightarrow> closed \<and> (\<forall>x \<in> set xs. x = Permitted)"
    by (cases closed; simp add: fold_and3_permitted)
  show "(every_value closed xs = Undetermined) \<longleftrightarrow>
        Denied \<notin> set xs \<and> (\<not> closed \<or> Undetermined \<in> set xs)"
    by (cases closed; simp add: fold_and3_undetermined)
qed

definition decision_leq_list :: "decision list \<Rightarrow> decision list \<Rightarrow> bool" where
  "decision_leq_list xs ys \<longleftrightarrow> list_all2 decision_leq xs ys"

lemma fold_or3_mono: "list_all2 decision_leq xs ys \<Longrightarrow> decision_leq x y \<Longrightarrow>
                      decision_leq (fold or3 xs x) (fold or3 ys y)"
proof (induct xs arbitrary: ys x y)
  case Nil then show ?case by simp
next
  case (Cons x' xs' ys x y)
  from Cons.prems(1) obtain y' ys' where ys_def: "ys = y' # ys'"
    and hd: "decision_leq x' y'" and tl: "list_all2 decision_leq xs' ys'"
    by (cases ys) auto
  have step: "decision_leq (or3 x' x) (or3 y' y)"
    using hd Cons.prems(2) by (metis decision_leq_trans or3_monotone_left or3_monotone_right)
  show ?case using Cons.hyps[OF tl step] ys_def by simp
qed

lemma fold_and3_mono: "list_all2 decision_leq xs ys \<Longrightarrow> decision_leq x y \<Longrightarrow>
                       decision_leq (fold and3 xs x) (fold and3 ys y)"
proof (induct xs arbitrary: ys x y)
  case Nil then show ?case by simp
next
  case (Cons x' xs' ys x y)
  from Cons.prems(1) obtain y' ys' where ys_def: "ys = y' # ys'"
    and hd: "decision_leq x' y'" and tl: "list_all2 decision_leq xs' ys'"
    by (cases ys) auto
  have step: "decision_leq (and3 x' x) (and3 y' y)"
    using hd Cons.prems(2) by (metis decision_leq_trans and3_monotone_left and3_monotone_right)
  show ?case using Cons.hyps[OF tl step] ys_def by simp
qed

(* A defined value only ever refines to itself: if xs refines pointwise to ys, a value d that
   is not Undetermined in xs is in ys too. *)
lemma leq_list_keeps_defined: "list_all2 decision_leq xs ys \<Longrightarrow> d \<noteq> Undetermined \<Longrightarrow>
                               d \<in> set xs \<Longrightarrow> d \<in> set ys"
proof (induct rule: list_all2_induct)
  case Nil then show ?case by simp
next
  case (Cons x xs y ys) then show ?case by (auto simp: decision_leq_def)
qed

(* GATE:BEGIN TL2 *)
lemma some_value_monotone: "decision_leq_list xs ys \<Longrightarrow> decision_leq (some_value closed xs) (some_value closed ys)"
  and every_value_monotone: "decision_leq_list xs ys \<Longrightarrow> decision_leq (every_value closed xs) (every_value closed ys)"
(* GATE:END *)
proof -
  show "decision_leq_list xs ys \<Longrightarrow> decision_leq (some_value closed xs) (some_value closed ys)"
  proof -
    assume h: "decision_leq_list xs ys"
    then have l: "list_all2 decision_leq xs ys" by (simp add: decision_leq_list_def)
    show ?thesis
    proof (cases closed)
      case True then show ?thesis using fold_or3_mono[OF l decision_leq_refl] by simp
    next
      case False
      have "Permitted \<in> set xs \<Longrightarrow> Permitted \<in> set ys" using leq_list_keeps_defined[OF l] by simp
      then show ?thesis using False by (auto simp: decision_leq_def)
    qed
  qed
  show "decision_leq_list xs ys \<Longrightarrow> decision_leq (every_value closed xs) (every_value closed ys)"
  proof -
    assume h: "decision_leq_list xs ys"
    then have l: "list_all2 decision_leq xs ys" by (simp add: decision_leq_list_def)
    show ?thesis
    proof (cases closed)
      case True then show ?thesis using fold_and3_mono[OF l decision_leq_refl] by simp
    next
      case False
      have "Denied \<in> set xs \<Longrightarrow> Denied \<in> set ys" using leq_list_keeps_defined[OF l] by simp
      then show ?thesis using False by (auto simp: decision_leq_def)
    qed
  qed
qed

lemma neg3_fold_or3: "neg3 (fold or3 xs x) = fold and3 (map neg3 xs) (neg3 x)"
proof (induct xs arbitrary: x)
  case Nil then show ?case by simp
next
  case (Cons y ys x) then show ?case by (cases x; cases y; simp)
qed

lemma neg3_eq_denied: "(neg3 x = Denied) \<longleftrightarrow> x = Permitted"
  by (cases x; simp)

(* GATE:BEGIN TL3a *)
lemma negate_after_is_every_of_negated: "neg3 (some_value closed xs) = every_value closed (map neg3 xs)"
(* GATE:END *)
proof (cases closed)
  case True then show ?thesis using neg3_fold_or3[of xs Denied] by simp
next
  case False
  have "(Denied \<in> set (map neg3 xs)) \<longleftrightarrow> Permitted \<in> set xs"
  proof
    assume "Denied \<in> set (map neg3 xs)"
    then obtain x where x_in: "x \<in> set xs" and x_neg: "neg3 x = Denied" by auto
    then have "x = Permitted" by (simp add: neg3_eq_denied)
    then show "Permitted \<in> set xs" using x_in by simp
  next
    assume "Permitted \<in> set xs"
    then have "neg3 Permitted \<in> neg3 ` set xs" by (rule imageI)
    then show "Denied \<in> set (map neg3 xs)" by simp
  qed
  then show ?thesis using False by simp
qed

(* GATE:BEGIN TL3b *)
lemma negate_before_same_reading_disagrees:
  "\<exists>xs. neg3 (some_value closed xs) \<noteq> some_value closed (map neg3 xs)"
(* GATE:END *)
  by (rule exI [of _ "[Permitted, Denied]"]) (cases closed; simp)

(* E1.4 (the formal-methods epic's second review §2.3): the empty-list base cases, stated and
   gated explicitly, and set invariance (permutation and duplication do not change the result),
   derived directly from the already-proved TL1 characterisations rather than by fresh
   induction. Under a closure the empty case decides (L17). *)

(* GATE:BEGIN TL4a *)
lemma some_value_empty: "some_value closed [] = (if closed then Denied else Undetermined)"
  by simp

lemma every_value_empty: "every_value closed [] = (if closed then Permitted else Undetermined)"
  by simp
(* GATE:END *)

(* GATE:BEGIN TL4b *)
lemma some_value_set_invariant: "set xs = set ys \<Longrightarrow> some_value closed xs = some_value closed ys"
proof -
  assume eq: "set xs = set ys"
  show ?thesis
  proof (cases "some_value closed xs")
    case Permitted
    then show ?thesis using eq some_value_spec_permitted by metis
  next
    case Denied
    then show ?thesis using eq some_value_spec_denied by metis
  next
    case Undetermined
    then show ?thesis using eq some_value_spec_undetermined by metis
  qed
qed

lemma every_value_set_invariant: "set xs = set ys \<Longrightarrow> every_value closed xs = every_value closed ys"
proof -
  assume eq: "set xs = set ys"
  show ?thesis
  proof (cases "every_value closed xs")
    case Permitted
    then show ?thesis using eq every_value_spec_permitted by metis
  next
    case Denied
    then show ?thesis using eq every_value_spec_denied by metis
  next
    case Undetermined
    then show ?thesis using eq every_value_spec_undetermined by metis
  qed
qed
(* GATE:END *)

end
