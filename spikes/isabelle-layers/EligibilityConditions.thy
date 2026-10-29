(* SPDX-License-Identifier: MPL-2.0 *)

(* Eligibility: a condition's decision table, exclusion precedence, hierarchical matching and
   profile composition, on top of the committed kernel (tools/proofs/eligibility).
   Source: ontology/eligibility/README.md section 5.1 (laws L9 to L14) and section 5.2.
   A spike, not yet aligned to the formal-methods track. *)

theory EligibilityConditions
imports "Eligibility.Eligibility"
begin

section \<open>Strategies and conditions\<close>

datatype strategy = ExactMatch | SetMembership | IntervalContainment | HierarchicalMatch | Wildcard

record 'c condition =
  required :: "'c set"
  excluded :: "'c set"
  strat :: strategy

text \<open>A scheme is its members and a broader relation within it. A candidate matches a concept
by equality, or under HierarchicalMatch by standing at or below it.\<close>

locale scheme =
  fixes members :: "'c set"
    and broader :: "'c \<Rightarrow> 'c \<Rightarrow> bool"
begin

definition below_eq :: "'c \<Rightarrow> 'c \<Rightarrow> bool" where
  "below_eq x c \<longleftrightarrow> (x, c) \<in> {(a, b). broader a b}\<^sup>*"

definition strictly_above :: "'c \<Rightarrow> 'c \<Rightarrow> bool" where
  "strictly_above x e \<longleftrightarrow> (e, x) \<in> {(a, b). broader a b}\<^sup>+"

definition flat :: bool where
  "flat \<longleftrightarrow> (\<forall>a \<in> members. \<forall>b. \<not> broader a b)"

definition matches :: "strategy \<Rightarrow> 'c \<Rightarrow> 'c \<Rightarrow> bool" where
  "matches st x c \<longleftrightarrow> (if st = HierarchicalMatch then below_eq x c else x = c)"

text \<open>The decision table of section 5.1, read as a decision flow, each row a condition on the
way to a leaf.\<close>

definition decide :: "'c condition \<Rightarrow> 'c option \<Rightarrow> decision" where
  "decide cond cand =
     (case cand of
        None \<Rightarrow> Undetermined
      | Some x \<Rightarrow>
          if x \<notin> members then Undetermined
          else if \<exists>e \<in> excluded cond. matches (strat cond) x e then Denied
          else if strat cond = HierarchicalMatch \<and> (\<exists>e \<in> excluded cond. strictly_above x e) then Undetermined
          else if strat cond = HierarchicalMatch \<and> flat \<and> x \<notin> required cond \<and> x \<notin> excluded cond then Undetermined
          else if (\<exists>r \<in> required cond. matches (strat cond) x r) \<or> (required cond = {} \<and> excluded cond \<noteq> {}) then Permitted
          else Denied)"

text \<open>An absent candidate, or one outside the bound scheme, is Undetermined.\<close>

lemma absent_undetermined: "decide cond None = Undetermined"
  by (simp add: decide_def)

lemma outside_scheme_undetermined: "x \<notin> members \<Longrightarrow> decide cond (Some x) = Undetermined"
  by (simp add: decide_def)

text \<open>Law L10, exclusion precedence: a candidate that matches an excluded concept is Denied,
whether or not it also matches a required one.\<close>

theorem l10_exclusion_precedence:
  assumes "x \<in> members" and "e \<in> excluded cond" and "matches (strat cond) x e"
  shows "decide cond (Some x) = Denied"
proof -
  have c: "\<exists>e \<in> excluded cond. matches (strat cond) x e" using assms(2,3) by blast
  show ?thesis using assms(1) c by (simp add: decide_def)
qed

text \<open>Law L11, exclusion granularity: under HierarchicalMatch a candidate strictly above an
excluded concept, and not itself excluded, is Undetermined, since its true value may fall under
the exclusion.\<close>

theorem l11_above_exclusion:
  assumes "x \<in> members" and "strat cond = HierarchicalMatch"
    and "\<not> (\<exists>e \<in> excluded cond. matches (strat cond) x e)"
    and "e \<in> excluded cond" and "strictly_above x e"
  shows "decide cond (Some x) = Undetermined"
proof -
  have c: "\<exists>e \<in> excluded cond. strictly_above x e" using assms(4,5) by blast
  show ?thesis using assms(1,2,3) c by (simp add: decide_def)
qed

text \<open>Law L12, default inclusion: a condition that declares exclusions only admits every member
of the scheme it does not exclude, under a non-hierarchical strategy.\<close>

theorem l12_default_inclusion:
  assumes "x \<in> members" and "strat cond \<noteq> HierarchicalMatch"
    and "required cond = {}" and "excluded cond \<noteq> {}" and "x \<notin> excluded cond"
  shows "decide cond (Some x) = Permitted"
proof -
  have nex: "\<not> (\<exists>e \<in> excluded cond. matches (strat cond) x e)"
    using assms(2,5) by (simp add: matches_def)
  show ?thesis using assms(1,2,3,4) nex by (simp add: decide_def)
qed

text \<open>Law L14, hierarchy precondition: where no member of the resolved scheme has a broader
concept within it, a hierarchical condition decides only the concepts it names, and a candidate
it does not name is Undetermined.\<close>

theorem l14_flat_scheme:
  assumes "x \<in> members" and "strat cond = HierarchicalMatch" and flat
    and "x \<notin> required cond" and "x \<notin> excluded cond"
  shows "decide cond (Some x) = Undetermined"
proof -
  have no_up: "\<And>c. below_eq x c \<Longrightarrow> x = c"
  proof -
    fix c assume "below_eq x c"
    then have "(x, c) \<in> {(a, b). broader a b}\<^sup>*" by (simp add: below_eq_def)
    then show "x = c"
    proof (cases rule: converse_rtranclE)
      case base
      then show ?thesis by simp
    next
      case (step y)
      then have "broader x y" by simp
      with \<open>flat\<close> assms(1) show ?thesis by (simp add: flat_def)
    qed
  qed
  have "\<not> (\<exists>e \<in> excluded cond. matches (strat cond) x e)"
    using assms(2,5) no_up by (auto simp: matches_def)
  then show ?thesis using assms by (simp add: decide_def)
qed

text \<open>On a flat scheme, below_eq is equality: the closure decides only named concepts (L9's
last clause).\<close>

lemma flat_closure_is_equality:
  assumes flat and "x \<in> members"
  shows "below_eq x c \<longleftrightarrow> x = c"
proof
  assume "below_eq x c"
  then have "(x, c) \<in> {(a, b). broader a b}\<^sup>*" by (simp add: below_eq_def)
  then show "x = c"
  proof (cases rule: converse_rtranclE)
    case base
    then show ?thesis by simp
  next
    case (step y)
    then show ?thesis using assms by (simp add: flat_def)
  qed
next
  assume "x = c"
  then show "below_eq x c" by (simp add: below_eq_def)
qed

text \<open>Adding an exclusion to a condition that already has one never turns Denied into
Permitted.\<close>

theorem exclusions_only_narrow:
  assumes "excluded cond \<noteq> {}" and "decide cond (Some x) = Denied"
  shows "decide (cond\<lparr> excluded := excluded cond \<union> E \<rparr>) (Some x) \<noteq> Permitted"
proof (cases "\<exists>e \<in> excluded cond. matches (strat cond) x e")
  case True
  then have "\<exists>e \<in> excluded cond \<union> E. matches (strat cond) x e" by blast
  then show ?thesis by (simp add: decide_def)
next
  case False
  have nreq: "\<not> (\<exists>r \<in> required cond. matches (strat cond) x r)" and req: "required cond \<noteq> {}"
    using assms False by (simp_all add: decide_def split: if_splits)
  show ?thesis using nreq req by (simp add: decide_def)
qed

end

section \<open>Composition, section 5.2\<close>

text \<open>An admission profile combines its conditions' decisions by AllRequired or AnySufficient,
which are the kernel's closed set readings: every_value and some_value over a closed list. The
kernel's characterisations carry over.\<close>

datatype composition = AllRequired | AnySufficient

definition compose :: "composition \<Rightarrow> decision list \<Rightarrow> decision" where
  "compose op ds = (case op of AllRequired \<Rightarrow> every_value True ds | AnySufficient \<Rightarrow> some_value True ds)"

theorem all_required_denied_iff: "compose AllRequired ds = Denied \<longleftrightarrow> Denied \<in> set ds"
  by (simp add: compose_def every_value_spec_denied del: every_value.simps)

theorem all_required_permitted_iff: "compose AllRequired ds = Permitted \<longleftrightarrow> (\<forall>d \<in> set ds. d = Permitted)"
  by (simp add: compose_def every_value_spec_permitted del: every_value.simps)

theorem any_sufficient_permitted_iff: "compose AnySufficient ds = Permitted \<longleftrightarrow> Permitted \<in> set ds"
  by (simp add: compose_def some_value_spec_permitted del: some_value.simps)

theorem any_sufficient_denied_iff: "compose AnySufficient ds = Denied \<longleftrightarrow> (\<forall>d \<in> set ds. d = Denied)"
  by (simp add: compose_def some_value_spec_denied del: some_value.simps)

text \<open>A profile with no condition admits under AllRequired and denies under AnySufficient: the
empty case decides, as the closed readings say.\<close>

lemma empty_profile: "compose AllRequired [] = Permitted \<and> compose AnySufficient [] = Denied"
  by (simp add: compose_def)

text \<open>Composition is monotone in the information order: refining a condition's decision never
flips the profile's.\<close>

theorem compose_monotone:
  assumes "decision_leq_list ds ds'"
  shows "decision_leq (compose op ds) (compose op ds')"
proof (cases op)
  case AllRequired
  then show ?thesis using every_value_monotone[OF assms] by (simp add: compose_def del: every_value.simps)
next
  case AnySufficient
  then show ?thesis using some_value_monotone[OF assms] by (simp add: compose_def del: some_value.simps)
qed

text \<open>A profile's decision does not depend on the order of its conditions, nor on a condition
being listed twice.\<close>

theorem compose_set_invariant:
  assumes "set ds = set ds'"
  shows "compose op ds = compose op ds'"
proof (cases op)
  case AllRequired
  then show ?thesis using every_value_set_invariant[OF assms] by (simp add: compose_def del: every_value.simps)
next
  case AnySufficient
  then show ?thesis using some_value_set_invariant[OF assms] by (simp add: compose_def del: some_value.simps)
qed

end
