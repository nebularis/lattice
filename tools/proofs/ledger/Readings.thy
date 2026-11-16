(* SPDX-License-Identifier: MPL-2.0 *)

(* Readings by effective day on the target kernel (plan ledger, LG-20, the seventh group): reading
   A from a recorded balance plus what was recorded after it is reading A from the start, at the
   head with every posting counted it is the recorded balance, the two totals of the flows split
   the same way, and the instance of a debit recorded last and effective second. Hand-written on
   the Kernel extracted from ontology/ledger/README.md section 10. *)

theory Readings
imports Credits
begin

section \<open>Examples, before any theorem\<close>

text \<open>One account at a ceiling of 100. A debit of 30 effective on day 1, a credit of 50 effective on
  day 3, of which 30 was applied, and a debit of 80 recorded last and effective on day 2. The
  recorded balance is 20. Reading A at day 2 is minus 10. Reading B ends at 50 where the account
  rations and at 100 where it refuses.\<close>

definition late_debit :: "(nat \<times> (nat, unit, int) posted) list" where
  "late_debit = [(1, Drawn 0 30), (3, Restored 0 None 50 30 (\<lambda>_. 0)), (2, Drawn 0 80)]"

value "(reading_a (one_account False) 2 3 late_debit 0,
        reading_b (one_account False) 3 3 late_debit 0,
        reading_b (one_account True) 3 3 late_debit 0,
        snd (run (one_account False) (map (asked \<circ> snd) late_debit) (stated (one_account False))) 0)"


section \<open>Reading A from a recorded balance\<close>

lemma counted_split:
  assumes "r \<le> n"
  shows "counted day n es = counted day r es @ counted day (n - r) (drop r es)"
proof -
  have "take n es = take r es @ take (n - r) (drop r es)" using assms take_add[of r "n - r" es] by simp
  then show ?thesis by (simp add: counted_def)
qed

lemma counted_all:
  "\<forall>e\<in>set (take r es). fst e \<le> day \<Longrightarrow> counted day r es = take r es"
  by (simp add: counted_def filter_id_conv)

(* GATE:BEGIN LE1 *)
theorem reading_a_from_a_recorded_balance:
  assumes r: "r \<le> n" and eff: "\<forall>e\<in>set (take r es). fst e \<le> day"
  shows "reading_a B day n es b
           = summed B (map snd (take r es)) b
             + sum_list (map (\<lambda>p. moved B p b) (map snd (counted day (n - r) (drop r es))))"
  using counted_split[OF r, of day es] counted_all[OF eff]
  by (simp add: reading_a_def summed_def)
(* GATE:END *)

(* GATE:BEGIN LE2 *)
theorem reading_a_at_the_head:
  assumes ran: "run B qs (stated B) = (map snd es, bal')" and eff: "\<forall>e\<in>set es. fst e \<le> day"
  shows "reading_a B day (length es) es b = bal' b"
proof -
  have "counted day (length es) es = es" using eff by (simp add: counted_def filter_id_conv)
  then show ?thesis using the_sum_is_the_balance[OF ran, of b] by (simp add: reading_a_def)
qed
(* GATE:END *)

(* GATE:BEGIN LE3 *)
theorem flows_from_recorded_totals:
  assumes r: "r \<le> n" and eff: "\<forall>e\<in>set (take r es). fst e \<le> day"
  shows "flows B day n es b = (fst (flows B day r es b) + fst (flows B day (n - r) (drop r es) b),
                               snd (flows B day r es b) + snd (flows B day (n - r) (drop r es) b))"
    and "counted day r es = take r es"
  using counted_split[OF r, of day es] counted_all[OF eff] by (simp_all add: flows_def Let_def)
(* GATE:END *)


section \<open>Reading B where nothing is late, and its range\<close>

text \<open>Settling again what a run posted, in the order it was posted, gives the run's balances: a
  draw the run refused was never posted, and a draw it posted fits again.\<close>

lemma asked_simps [simp]:
  "asked (Drawn a x) = Draw a x" "asked (Restored a c x applied cuts) = Restore a c x"
  by (simp_all add: asked_def)

lemma replay_run:
  assumes tr: "tree A (parent_of B)" and inA: "\<forall>a x. Draw a x \<in> set qs \<longrightarrow> a \<in> A"
  shows "replay B (map asked (fst (run B qs bal))) bal = snd (run B qs bal)"
  using inA
proof (induction qs arbitrary: bal)
  case Nil
  then show ?case by simp
next
  case (Cons q qs)
  have rest: "\<forall>a x. Draw a x \<in> set qs \<longrightarrow> a \<in> A" using Cons.prems by simp
  note IH = Cons.IH[OF rest]
  show ?case
  proof (cases q)
    case (Draw a x)
    then have a: "a \<in> A" using Cons.prems by simp
    show ?thesis
    proof (cases "0 \<le> x \<and> (\<forall>b\<in>path (parent_of B) a. x \<le> bal b)")
      case True
      then have "x \<le> available (parent_of B) bal a" using le_available_iff[OF tr a, of x bal] by blast
      then show ?thesis using True IH[of "debit (path (parent_of B) a) x bal"] Draw
        by (simp add: post_def draw_on_def prod.case_eq_if)
    next
      case False
      then have "post B q bal = (None, bal)" using Draw by (simp add: post_def draw_on_def)
      then show ?thesis using IH[of bal] by simp
    qed
  next
    case (Restore a c x)
    obtain ap cuts bal1 where cr: "credit (parent_of B) (ceiling B) (\<lambda>b. restores B b c) a x bal = (ap, cuts, bal1)"
      by (cases "credit (parent_of B) (ceiling B) (\<lambda>b. restores B b c) a x bal") auto
    then have "post B q bal = (Some (Restored a c x ap cuts), bal1)" using Restore by (simp add: post_def)
    then show ?thesis using IH[of bal1] cr Restore by (simp add: prod.case_eq_if)
  qed
qed

text \<open>Every posting is effective on the day it is recorded, its position.\<close>

(* GATE:BEGIN LE4 *)
theorem with_nothing_late_the_readings_agree:
  assumes tr: "tree A (parent_of B)" and inA: "\<forall>a x. Draw a x \<in> set qs \<longrightarrow> a \<in> A"
    and ran: "run B qs (stated B) = (map snd es, bal')" and now: "map fst es = [Suc 0..<Suc (length es)]"
  shows "reading_b B (length es) (length es) es b = bal' b \<and> reading_a B (length es) (length es) es b = bal' b"
proof -
  have eff: "\<forall>e\<in>set es. fst e \<le> length es"
  proof
    fix e
    assume "e \<in> set es"
    then have "fst e \<in> set (map fst es)" by simp
    then show "fst e \<le> length es" using now by (auto simp del: upt_Suc)
  qed
  have c: "counted (length es) (length es) es = es" using eff by (simp add: counted_def filter_id_conv)
  have s: "sort_key fst es = es" by (rule sort_key_id_if_sorted) (simp add: now del: upt_Suc)
  have "replay B (map asked (map snd es)) (stated B) = bal'"
    using replay_run[OF tr inA, of "stated B"] ran by simp
  then have "reading_b B (length es) (length es) es b = bal' b" by (simp add: reading_b_def c s)
  then show ?thesis using reading_a_at_the_head[OF ran eff] by simp
qed
(* GATE:END *)

lemma replay_in_range:
  assumes tr: "tree A (parent_of B)" and qs: "\<forall>a x. Draw a x \<in> set qs \<longrightarrow> a \<in> A \<and> 0 \<le> x"
    and inv: "\<forall>b. 0 \<le> bal b \<and> bal b \<le> ceiling B b"
  shows "0 \<le> replay B qs bal b \<and> replay B qs bal b \<le> ceiling B b"
  using qs inv
proof (induction qs arbitrary: bal)
  case Nil
  then show ?case by simp
next
  case (Cons q qs)
  have rest: "\<forall>a x. Draw a x \<in> set qs \<longrightarrow> a \<in> A \<and> 0 \<le> x" using Cons.prems(1) by simp
  show ?case
  proof (cases q)
    case (Draw a x)
    have a: "a \<in> A" and x0: "0 \<le> x" using Cons.prems(1) Draw by auto
    define bal1 where "bal1 =
      (if x \<le> available (parent_of B) bal a then debit (path (parent_of B) a) x bal
       else if refusing B a then bal else debit (path (parent_of B) a) (max 0 (available (parent_of B) bal a)) bal)"
    have "\<forall>b. 0 \<le> bal1 b \<and> bal1 b \<le> ceiling B b"
    proof
      fix b
      have le: "b \<in> path (parent_of B) a \<Longrightarrow> available (parent_of B) bal a \<le> bal b"
        using available_le[OF tr a] by blast
      have r: "0 \<le> bal b" "bal b \<le> ceiling B b" using Cons.prems(2) by auto
      show "0 \<le> bal1 b \<and> bal1 b \<le> ceiling B b"
        using r x0 le unfolding bal1_def debit_def by (auto simp: max_def)
    qed
    note step = Cons.IH[OF rest this]
    have "replay B (q # qs) bal = replay B qs bal1" using Draw by (simp add: bal1_def)
    then show ?thesis using step by simp
  next
    case (Restore a c x)
    define bal1 where "bal1 = snd (snd (credit (parent_of B) (ceiling B) (\<lambda>b. restores B b c) a x bal))"
    have "\<forall>b. 0 \<le> bal1 b \<and> bal1 b \<le> ceiling B b"
    proof
      fix b
      have r: "0 \<le> bal b" "bal b \<le> ceiling B b" "0 \<le> bal a" "bal a \<le> ceiling B a" using Cons.prems(2) by auto
      show "0 \<le> bal1 b \<and> bal1 b \<le> ceiling B b"
        using r unfolding bal1_def credit_def Let_def by (auto simp: min_def max_def)
    qed
    note step = Cons.IH[OF rest this]
    have "replay B (q # qs) bal = replay B qs bal1" using Restore by (simp add: bal1_def)
    then show ?thesis using step by simp
  qed
qed

(* GATE:BEGIN LE5 *)
theorem reading_b_within_range:
  assumes tr: "tree A (parent_of B)" and ps: "\<forall>a x. Drawn a x \<in> snd ` set es \<longrightarrow> a \<in> A \<and> 0 \<le> x"
    and st: "\<forall>b. 0 \<le> stated B b \<and> stated B b \<le> ceiling B b"
  shows "0 \<le> reading_b B day r es b \<and> reading_b B day r es b \<le> ceiling B b"
proof -
  let ?qs = "map (asked \<circ> snd) (sort_key fst (counted day r es))"
  have "\<forall>a x. Draw a x \<in> set ?qs \<longrightarrow> a \<in> A \<and> 0 \<le> x"
  proof (intro allI impI)
    fix a x
    assume "Draw a x \<in> set ?qs"
    then obtain e where e: "e \<in> set es" "asked (snd e) = Draw a x"
      by (auto simp: counted_def dest: in_set_takeD)
    then have "snd e = Drawn a x" by (cases "snd e") (simp_all add: asked_def)
    then have "Drawn a x \<in> snd ` set es" using e(1) by force
    then show "a \<in> A \<and> 0 \<le> x" using ps by simp
  qed
  then show ?thesis using replay_in_range[OF tr _ st] by (simp add: reading_b_def)
qed
(* GATE:END *)


section \<open>The instance kept on purpose\<close>

(* GATE:BEGIN LEn *)
theorem a_debit_recorded_last_and_effective_second:
  "reading_a (one_account False) 2 3 late_debit 0 = -10
   \<and> reading_b (one_account False) 3 3 late_debit 0 = 50
   \<and> reading_b (one_account True) 3 3 late_debit 0 = 100
   \<and> snd (run (one_account False) (map (asked \<circ> snd) late_debit) (stated (one_account False))) 0 = 20"
  by code_simp
(* GATE:END *)

end
