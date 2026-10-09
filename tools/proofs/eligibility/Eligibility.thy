(* Eligibility's set readings and negation (target TL, ADR-A103, L15/L16), hand-written on top
   of KernelLaws. Restated from spikes/formal-prover/isabelle/Eligibility.thy (track D's spike),
   re-pointed at this layer's own KernelLaws rather than a self-contained Kernel. *)

theory Eligibility
imports KernelLaws
begin

fun some_value :: "decision list \<Rightarrow> decision" where
  "some_value [] = Undetermined"
| "some_value (x # xs) = fold or3 xs x"

fun every_value :: "decision list \<Rightarrow> decision" where
  "every_value [] = Undetermined"
| "every_value (x # xs) = fold and3 xs x"

(* GATE:BEGIN TL1-some *)
lemma some_value_spec_permitted: "(some_value xs = Permitted) \<longleftrightarrow> Permitted \<in> set xs"
  and some_value_spec_denied: "(some_value xs = Denied) \<longleftrightarrow> xs \<noteq> [] \<and> (\<forall>x \<in> set xs. x = Denied)"
  and some_value_spec_undetermined: "(some_value xs = Undetermined) \<longleftrightarrow>
        xs = [] \<or> (Permitted \<notin> set xs \<and> Undetermined \<in> set xs)"
(* GATE:END *)
proof -
  have fold_or3_permitted: "\<And>x xs. (fold or3 xs x = Permitted) \<longleftrightarrow> (Permitted \<in> set (x # xs))"
  proof -
    fix x xs show "(fold or3 xs x = Permitted) \<longleftrightarrow> (Permitted \<in> set (x # xs))"
    proof (induct xs arbitrary: x)
      case Nil then show ?case by (cases x; simp)
    next
      case (Cons y ys x) then show ?case by (cases x; cases y; simp)
    qed
  qed
  have fold_or3_denied: "\<And>x xs. (fold or3 xs x = Denied) \<longleftrightarrow> (\<forall>z \<in> set (x # xs). z = Denied)"
  proof -
    fix x xs show "(fold or3 xs x = Denied) \<longleftrightarrow> (\<forall>z \<in> set (x # xs). z = Denied)"
    proof (induct xs arbitrary: x)
      case Nil then show ?case by (cases x; simp)
    next
      case (Cons y ys x) then show ?case by (cases x; cases y; simp)
    qed
  qed
  have fold_or3_undetermined: "\<And>x xs. (fold or3 xs x = Undetermined) \<longleftrightarrow>
         (Permitted \<notin> set (x # xs) \<and> Undetermined \<in> set (x # xs))"
  proof -
    fix x xs show "(fold or3 xs x = Undetermined) \<longleftrightarrow>
         (Permitted \<notin> set (x # xs) \<and> Undetermined \<in> set (x # xs))"
    proof (induct xs arbitrary: x)
      case Nil then show ?case by (cases x; simp)
    next
      case (Cons y ys x) then show ?case by (cases x; cases y; simp)
    qed
  qed
  show "(some_value xs = Permitted) \<longleftrightarrow> Permitted \<in> set xs"
    by (cases xs; simp add: fold_or3_permitted)
  show "(some_value xs = Denied) \<longleftrightarrow> xs \<noteq> [] \<and> (\<forall>x \<in> set xs. x = Denied)"
    by (cases xs; simp add: fold_or3_denied)
  show "(some_value xs = Undetermined) \<longleftrightarrow>
        xs = [] \<or> (Permitted \<notin> set xs \<and> Undetermined \<in> set xs)"
    by (cases xs; simp add: fold_or3_undetermined)
qed

(* GATE:BEGIN TL1-every *)
lemma every_value_spec_denied: "(every_value xs = Denied) \<longleftrightarrow> Denied \<in> set xs"
  and every_value_spec_permitted: "(every_value xs = Permitted) \<longleftrightarrow> xs \<noteq> [] \<and> (\<forall>x \<in> set xs. x = Permitted)"
  and every_value_spec_undetermined: "(every_value xs = Undetermined) \<longleftrightarrow>
        xs = [] \<or> (Denied \<notin> set xs \<and> Undetermined \<in> set xs)"
(* GATE:END *)
proof -
  have fold_and3_denied: "\<And>x xs. (fold and3 xs x = Denied) \<longleftrightarrow> (Denied \<in> set (x # xs))"
  proof -
    fix x xs show "(fold and3 xs x = Denied) \<longleftrightarrow> (Denied \<in> set (x # xs))"
    proof (induct xs arbitrary: x)
      case Nil then show ?case by (cases x; simp)
    next
      case (Cons y ys x) then show ?case by (cases x; cases y; simp)
    qed
  qed
  have fold_and3_permitted: "\<And>x xs. (fold and3 xs x = Permitted) \<longleftrightarrow> (\<forall>z \<in> set (x # xs). z = Permitted)"
  proof -
    fix x xs show "(fold and3 xs x = Permitted) \<longleftrightarrow> (\<forall>z \<in> set (x # xs). z = Permitted)"
    proof (induct xs arbitrary: x)
      case Nil then show ?case by (cases x; simp)
    next
      case (Cons y ys x) then show ?case by (cases x; cases y; simp)
    qed
  qed
  have fold_and3_undetermined: "\<And>x xs. (fold and3 xs x = Undetermined) \<longleftrightarrow>
         (Denied \<notin> set (x # xs) \<and> Undetermined \<in> set (x # xs))"
  proof -
    fix x xs show "(fold and3 xs x = Undetermined) \<longleftrightarrow>
         (Denied \<notin> set (x # xs) \<and> Undetermined \<in> set (x # xs))"
    proof (induct xs arbitrary: x)
      case Nil then show ?case by (cases x; simp)
    next
      case (Cons y ys x) then show ?case by (cases x; cases y; simp)
    qed
  qed
  show "(every_value xs = Denied) \<longleftrightarrow> Denied \<in> set xs"
    by (cases xs; simp add: fold_and3_denied)
  show "(every_value xs = Permitted) \<longleftrightarrow> xs \<noteq> [] \<and> (\<forall>x \<in> set xs. x = Permitted)"
    by (cases xs; simp add: fold_and3_permitted)
  show "(every_value xs = Undetermined) \<longleftrightarrow>
        xs = [] \<or> (Denied \<notin> set xs \<and> Undetermined \<in> set xs)"
    by (cases xs; simp add: fold_and3_undetermined)
qed

definition decision_leq_list :: "decision list \<Rightarrow> decision list \<Rightarrow> bool" where
  "decision_leq_list xs ys \<longleftrightarrow> list_all2 decision_leq xs ys"

(* GATE:BEGIN TL2 *)
lemma some_value_monotone: "decision_leq_list xs ys \<Longrightarrow> decision_leq (some_value xs) (some_value ys)"
  and every_value_monotone: "decision_leq_list xs ys \<Longrightarrow> decision_leq (every_value xs) (every_value ys)"
(* GATE:END *)
proof -
  have fold_or3_mono: "\<And>ys x y. list_all2 decision_leq xs ys \<Longrightarrow> decision_leq x y \<Longrightarrow>
                        decision_leq (fold or3 xs x) (fold or3 ys y)" for xs
  proof (induct xs)
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
  have fold_and3_mono: "\<And>ys x y. list_all2 decision_leq xs ys \<Longrightarrow> decision_leq x y \<Longrightarrow>
                        decision_leq (fold and3 xs x) (fold and3 ys y)" for xs
  proof (induct xs)
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
  show "decision_leq_list xs ys \<Longrightarrow> decision_leq (some_value xs) (some_value ys)"
    unfolding decision_leq_list_def
  proof (induct xs ys rule: list_all2_induct)
    case Nil then show ?case by (simp add: decision_leq_refl)
  next
    case (Cons x xs' y ys')
    then show ?case using fold_or3_mono by simp
  qed
  show "decision_leq_list xs ys \<Longrightarrow> decision_leq (every_value xs) (every_value ys)"
    unfolding decision_leq_list_def
  proof (induct xs ys rule: list_all2_induct)
    case Nil then show ?case by (simp add: decision_leq_refl)
  next
    case (Cons x xs' y ys')
    then show ?case using fold_and3_mono by simp
  qed
qed

(* GATE:BEGIN TL3a *)
lemma negate_after_is_every_of_negated: "neg3 (some_value xs) = every_value (map neg3 xs)"
(* GATE:END *)
proof (induct xs)
  case Nil then show ?case by simp
next
  case (Cons x xs)
  have "neg3 (fold or3 xs x) = fold and3 (map neg3 xs) (neg3 x)"
  proof (induct xs arbitrary: x)
    case Nil then show ?case by simp
  next
    case (Cons y ys x)
    then show ?case by (cases x; cases y; simp)
  qed
  then show ?case by simp
qed

(* GATE:BEGIN TL3b *)
lemma negate_before_same_reading_disagrees:
  "\<exists>xs. neg3 (some_value xs) \<noteq> some_value (map neg3 xs)"
(* GATE:END *)
  by (rule exI [of _ "[Permitted, Denied]"]) simp

(* E1.4 (the formal-methods epic's second review \u00a72.3): the empty-list base cases, stated and
   gated explicitly, and set invariance (permutation and duplication do not change the result,
   since both readings fold a commutative, associative, idempotent connective, TA4), derived
   directly from the already-proved TL1 characterisations rather than by fresh induction. *)

(* GATE:BEGIN TL4a *)
lemma some_value_empty: "some_value [] = Undetermined"
  by simp

lemma every_value_empty: "every_value [] = Undetermined"
  by simp
(* GATE:END *)

(* GATE:BEGIN TL4b *)
lemma some_value_set_invariant: "set xs = set ys \<Longrightarrow> some_value xs = some_value ys"
proof (cases "some_value xs")
  case Permitted
  then have "Permitted \<in> set xs" using some_value_spec_permitted by blast
  moreover assume "set xs = set ys"
  ultimately have "Permitted \<in> set ys" by simp
  then show ?thesis using Permitted some_value_spec_permitted by metis
next
  case Denied
  then have h: "xs \<noteq> [] \<and> (\<forall>x \<in> set xs. x = Denied)" using some_value_spec_denied by blast
  assume eq: "set xs = set ys"
  have ys_ne: "ys \<noteq> []"
  proof
    assume "ys = []"
    then have "set xs = {}" using eq by simp
    then show False using h by simp
  qed
  have "\<forall>x \<in> set ys. x = Denied" using h eq by simp
  then show ?thesis using ys_ne Denied some_value_spec_denied by metis
next
  case Undetermined
  then have u: "xs = [] \<or> (Permitted \<notin> set xs \<and> Undetermined \<in> set xs)"
    using some_value_spec_undetermined by blast
  assume eq: "set xs = set ys"
  show ?thesis
  proof (cases "xs = []")
    case True
    then have "set ys = {}" using eq by simp
    then have "ys = []" by simp
    then show ?thesis using True Undetermined some_value_spec_undetermined by simp
  next
    case False
    then have h: "Permitted \<notin> set xs \<and> Undetermined \<in> set xs" using u by blast
    then have "Permitted \<notin> set ys \<and> Undetermined \<in> set ys" using eq by simp
    then show ?thesis using Undetermined some_value_spec_undetermined by metis
  qed
qed

lemma every_value_set_invariant: "set xs = set ys \<Longrightarrow> every_value xs = every_value ys"
proof (cases "every_value xs")
  case Denied
  then have "Denied \<in> set xs" using every_value_spec_denied by blast
  moreover assume "set xs = set ys"
  ultimately have "Denied \<in> set ys" by simp
  then show ?thesis using Denied every_value_spec_denied by metis
next
  case Permitted
  then have h: "xs \<noteq> [] \<and> (\<forall>x \<in> set xs. x = Permitted)" using every_value_spec_permitted by blast
  assume eq: "set xs = set ys"
  have ys_ne: "ys \<noteq> []"
  proof
    assume "ys = []"
    then have "set xs = {}" using eq by simp
    then show False using h by simp
  qed
  have "\<forall>x \<in> set ys. x = Permitted" using h eq by simp
  then show ?thesis using ys_ne Permitted every_value_spec_permitted by metis
next
  case Undetermined
  then have u: "xs = [] \<or> (Denied \<notin> set xs \<and> Undetermined \<in> set xs)"
    using every_value_spec_undetermined by blast
  assume eq: "set xs = set ys"
  show ?thesis
  proof (cases "xs = []")
    case True
    then have "set ys = {}" using eq by simp
    then have "ys = []" by simp
    then show ?thesis using True Undetermined every_value_spec_undetermined by simp
  next
    case False
    then have h: "Denied \<notin> set xs \<and> Undetermined \<in> set xs" using u by blast
    then have "Denied \<notin> set ys \<and> Undetermined \<in> set ys" using eq by simp
    then show ?thesis using Undetermined every_value_spec_undetermined by metis
  qed
qed
(* GATE:END *)

end
