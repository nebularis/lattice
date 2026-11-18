(* SPDX-License-Identifier: MPL-2.0 *)

(* The predicates of the target kernel (plan ledger, LG-20, the first group): a lawful rule rations
   and leaves no residual, the two rules for whole units apportion with a declared order, a key of
   no weight under rationing and under apportionment, granting whole in a declared order rations,
   and no rule that grants each request whole or not at all is exact. Hand-written on the Kernel
   extracted from ontology/ledger/README.md section 10. *)

theory Predicates
imports Rounding
begin

section \<open>Examples, before any theorem\<close>

text \<open>With 7 available and requests of 5 and 4, granting whole in that order grants 5 and leaves
  2, and in the other order grants 4 and leaves 3. Neither grants 7.\<close>

value "(map (whole_each [1, 2::nat] (\<lambda>k. if k = 1 then 5 else 4) (7::int)) [1, 2],
        map (whole_each [2, 1::nat] (\<lambda>k. if k = 1 then 5 else 4) (7::int)) [1, 2])"

lemma example_whole_in_either_order:
  "map (whole_each [1, 2::nat] (\<lambda>k. if k = 1 then 5 else 4) (7::int)) [1, 2] = [5, 0]
   \<and> map (whole_each [2, 1::nat] (\<lambda>k. if k = 1 then 5 else 4) (7::int)) [1, 2] = [0, 4]"
  by code_simp

text \<open>Apportioning 10 units by weights 3, 2 and 1 with either rule gives shares summing to 10.\<close>

lemma example_apportioned_shares_sum:
  "sum_list (map (apportion (to_first id) {0::nat, 1, 2} (\<lambda>k. 3 - int k) 10) [0, 1, 2]) = 10
   \<and> sum_list (map (apportion (largest_remainder (first_in id)) {0::nat, 1, 2} (\<lambda>k. 3 - int k) 10) [0, 1, 2]) = 10"
  by code_simp


section \<open>A lawful rule rations and leaves no residual\<close>

(* GATE:BEGIN LV1 *)
theorem lawful_is_rationing_with_no_residual:
  "lawful K R \<longleftrightarrow>
     rations K R \<and> (\<forall>v x. nonneg_on K v \<and> 0 \<le> x \<and> x \<le> total K v \<longrightarrow> residual K R v x = 0)"
  by (simp add: lawful_def exact_def)
(* GATE:END *)


section \<open>The two rules for whole units apportion\<close>

lemma units_total:
  assumes fin: "finite K" and sub: "E \<subseteq> K" and so: "strict_order_on E pref"
      and n0: "0 \<le> n" and nE: "n \<le> int (card E)"
  shows "total K (units F n E pref {} no_order) = (\<Sum>k\<in>K. F k) + n"
proof -
  have finE: "finite E" using fin sub by (rule finite_subset[rotated])
  have cnt: "(\<Sum>k\<in>K. if 0 < n \<and> placed E pref n k then 1 else 0) = (n::int)"
  proof (cases "0 < n")
    case True
    have "(\<Sum>k\<in>K. if 0 < n \<and> placed E pref n k then 1 else 0) = (\<Sum>k\<in>K. if placed E pref n k then 1 else (0::int))"
      using True by simp
    also have "\<dots> = int (card (K \<inter> {k. placed E pref n k}))"
      using fin by (simp add: sum.If_cases)
    also have "K \<inter> {k. placed E pref n k} = {k\<in>E. placed E pref n k}"
      using sub placed_in[of E pref n] by auto
    also have "card {k\<in>E. placed E pref n k} = nat n" using placed_count[OF finE so n0 nE] .
    finally show ?thesis using n0 by simp
  next
    case False
    then show ?thesis using n0 by simp
  qed
  show ?thesis using cnt by (simp add: total_def units_unfold sum.distrib)
qed

lemma whole_parts:
  assumes fin: "finite K" and nn: "nonneg_on K v"
  shows "floor_part (total K v) K v = v" and "short (total K v) K (floor_part (total K v) K v) = 0"
proof -
  show F: "floor_part (total K v) K v = v"
  proof
    fix k
    show "floor_part (total K v) K v k = v k"
    proof (cases "k \<in> K")
      case True
      show ?thesis
      proof (cases "(\<Sum>j\<in>K. v j) = 0")
        case z: True
        have "v k = 0" using zero_weights[OF fin _ z] nn True by (simp add: nonneg_on_def)
        then show ?thesis using z by (simp add: floor_part_def total_def)
      next
        case False
        then show ?thesis using True by (simp add: floor_part_def total_def)
      qed
    next
      case False
      then show ?thesis using nn by (simp add: floor_part_def nonneg_on_def)
    qed
  qed
  show "short (total K v) K (floor_part (total K v) K v) = 0" unfolding short_def F by (simp add: total_def)
qed

lemma apportion_units:
  assumes fin: "finite K" and so: "strict_order_on K pref"
      and nn: "nonneg_on K w" and W: "0 < total K w" and x0: "0 \<le> x"
  shows "nonneg_on K (units (floor_part x K w) (short x K (floor_part x K w)) K pref {} no_order)
         \<and> total K (units (floor_part x K w) (short x K (floor_part x K w)) K pref {} no_order) = x"
proof -
  have Wp: "0 < (\<Sum>j\<in>K. w j)" using W by (simp add: total_def)
  have n: "0 \<le> short x K (floor_part x K w) \<and> short x K (floor_part x K w) < int (card K)"
    using floor_split_conserves(2)[OF fin Wp] .
  have tot: "total K (units (floor_part x K w) (short x K (floor_part x K w)) K pref {} no_order) = x"
    using units_total[OF fin order_refl so] n floor_split_conserves(1)[OF fin Wp, of x] by simp
  have lo: "0 \<le> units (floor_part x K w) (short x K (floor_part x K w)) K pref {} no_order k" for k
    using floor_part_nonneg[OF nn x0, of k] by (simp add: units_unfold)
  have off: "units (floor_part x K w) (short x K (floor_part x K w)) K pref {} no_order k = 0" if "k \<notin> K" for k
    using that placed_in[of K pref _ k] by (auto simp: units_unfold floor_part_def)
  show ?thesis using tot lo off by (simp add: nonneg_on_def)
qed

lemma apportion_whole:
  assumes fin: "finite K" and nn: "nonneg_on K w"
  shows "units (floor_part (total K w) K w) (short (total K w) K (floor_part (total K w) K w)) K pref {} no_order = w"
  using whole_parts[OF fin nn] by (simp add: fun_eq_iff units_unfold)

(* GATE:BEGIN LS1 *)
theorem the_rules_for_whole_units_apportion:
  assumes fin: "finite K" and inj: "inj_on order K"
  shows "apportions K (apportion (to_first order) K)"
    and "apportions K (apportion (largest_remainder (first_in order)) K)"
proof -
  have s1: "strict_order_on K (first_in order)" by (rule first_in_strict[OF inj])
  show "apportions K (apportion (to_first order) K)"
    unfolding apportions_def apportion_def to_first_def
    using apportion_units[OF fin s1] apportion_whole[OF fin] by blast
  have s2: "strict_order_on K (then_by (larger_remainder x K w) (first_in order))" for x w
    by (rule then_by_strict[OF inj])
  show "apportions K (apportion (largest_remainder (first_in order)) K)"
    unfolding apportions_def apportion_def largest_remainder_def
    using apportion_units[OF fin s2] apportion_whole[OF fin] by blast
qed
(* GATE:END *)


section \<open>A key of no weight\<close>

text \<open>Rationed, a request of no weight is granted nothing whatever the order, since it is met.
  Apportioned, every key may take a unit, so a key of no weight first in the order takes one.\<close>

(* GATE:BEGIN LS2 *)
theorem a_key_of_no_weight:
  assumes nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v" and k: "v k = 0"
  shows "ration (to_first order) K v x k = 0"
    and "ration (largest_remainder tb) K v x k = 0"
    and "apportion (to_first id) {0::nat, 1, 2} (\<lambda>k. if k = 0 then 0 else 3) 1 0 = 1"
proof -
  have "0 \<le> ration (to_first order) K v x k \<and> ration (to_first order) K v x k \<le> v k"
    using floor_units_bounds[OF nn x0 xv, of "first_in order"]
    by (simp add: ration_to_first_units nonneg_on_def fits_in_def)
  then show "ration (to_first order) K v x k = 0" using k by simp
  have "0 \<le> ration (largest_remainder tb) K v x k \<and> ration (largest_remainder tb) K v x k \<le> v k"
    using floor_units_bounds[OF nn x0 xv, of "then_by (larger_remainder x K v) tb"]
    by (simp add: ration_largest_remainder_units nonneg_on_def fits_in_def)
  then show "ration (largest_remainder tb) K v x k = 0" using k by simp
  show "apportion (to_first id) {0::nat, 1, 2} (\<lambda>k. if k = 0 then 0 else 3) 1 0 = 1"
    by code_simp
qed
(* GATE:END *)


section \<open>Granting whole in a declared order rations\<close>

lemma whole_each_off: "k \<notin> set ks \<Longrightarrow> whole_each ks v x k = 0"
  by (induct ks arbitrary: x) (simp_all add: nothing_def)

lemma whole_each_cases: "whole_each ks v x k = v k \<or> whole_each ks v x k = 0"
  by (induct ks arbitrary: x) (auto simp: nothing_def)

lemma whole_each_sum:
  assumes nn: "\<forall>k. 0 \<le> v k"
  shows "distinct ks \<Longrightarrow> 0 \<le> x \<Longrightarrow> (\<Sum>k\<in>set ks. whole_each ks v x k) \<le> x"
proof (induct ks arbitrary: x)
  case Nil
  then show ?case by simp
next
  case (Cons j ks)
  have jn: "j \<notin> set ks" and d: "distinct ks" using Cons.prems(1) by simp_all
  show ?case
  proof (cases "v j \<le> x")
    case True
    have x1: "0 \<le> x - v j" using True by simp
    have rest: "(\<Sum>k\<in>set ks. ((whole_each ks v (x - v j))(j := v j)) k) = (\<Sum>k\<in>set ks. whole_each ks v (x - v j) k)"
      using jn by (intro sum.cong) auto
    have "(\<Sum>k\<in>set (j # ks). whole_each (j # ks) v x k) = v j + (\<Sum>k\<in>set ks. whole_each ks v (x - v j) k)"
      using True jn rest by simp
    also have "\<dots> \<le> v j + (x - v j)" using Cons.hyps[OF d x1] by simp
    finally show ?thesis by simp
  next
    case False
    have "(\<Sum>k\<in>set (j # ks). whole_each (j # ks) v x k) = whole_each ks v x j + (\<Sum>k\<in>set ks. whole_each ks v x k)"
      using False jn by simp
    also have "whole_each ks v x j = 0" using jn by (rule whole_each_off)
    finally show ?thesis using Cons.hyps[OF d Cons.prems(2)] by simp
  qed
qed

lemma whole_each_all:
  assumes nn: "\<forall>k. 0 \<le> v k"
  shows "distinct ks \<Longrightarrow> (\<Sum>k\<in>set ks. v k) \<le> x \<Longrightarrow> k \<in> set ks \<Longrightarrow> whole_each ks v x k = v k"
proof (induct ks arbitrary: x)
  case Nil
  then show ?case by simp
next
  case (Cons j ks)
  have jn: "j \<notin> set ks" and d: "distinct ks" using Cons.prems(1) by simp_all
  have s: "(\<Sum>k\<in>set (j # ks). v k) = v j + (\<Sum>k\<in>set ks. v k)" using jn by simp
  have rest0: "0 \<le> (\<Sum>k\<in>set ks. v k)" using nn by (simp add: sum_nonneg)
  have vj: "v j \<le> x" using Cons.prems(2) s rest0 by simp
  show ?case
  proof (cases "k = j")
    case True
    then show ?thesis using vj by simp
  next
    case False
    then have kin: "k \<in> set ks" using Cons.prems(3) by simp
    have "(\<Sum>k\<in>set ks. v k) \<le> x - v j" using Cons.prems(2) s by simp
    then show ?thesis using Cons.hyps[OF d _ kin] vj False by simp
  qed
qed

(* GATE:BEGIN LV2 *)
theorem whole_each_rations:
  fixes ks :: "'k list"
  assumes d: "distinct ks" and K: "set ks = K"
  shows "rations K (whole_each ks :: ('k, 'n::linordered_idom) rule)"
  unfolding rations_def
proof (intro conjI allI impI)
  fix v :: "('k, 'n) amounts" and x :: 'n
  assume a: "nonneg_on K v \<and> 0 \<le> x \<and> x \<le> total K v"
  then have nn: "\<forall>k. 0 \<le> v k" and x0: "0 \<le> x" by (simp_all add: nonneg_on_def)
  have each: "whole_each ks v x k = v k \<or> whole_each ks v x k = 0" for k by (rule whole_each_cases)
  show "nonneg_on K (whole_each ks v x)"
    unfolding nonneg_on_def
  proof (intro conjI allI impI)
    fix k
    show "0 \<le> whole_each ks v x k" using each[of k] nn by auto
  next
    fix k
    assume "k \<notin> K"
    then show "whole_each ks v x k = 0" using whole_each_off[of k ks v x] K by simp
  qed
  show "fits_in (whole_each ks v x) v"
    unfolding fits_in_def
  proof
    fix k
    show "whole_each ks v x k \<le> v k" using each[of k] nn by auto
  qed
  show "total K (whole_each ks v x) \<le> x"
    using whole_each_sum[OF nn d x0] K by (simp add: total_def)
next
  fix v :: "('k, 'n) amounts"
  assume nn0: "nonneg_on K v"
  then have nn: "\<forall>k. 0 \<le> v k" by (simp add: nonneg_on_def)
  show "whole_each ks v (total K v) = v"
  proof
    fix k
    show "whole_each ks v (total K v) k = v k"
    proof (cases "k \<in> K")
      case True
      then show ?thesis using whole_each_all[OF nn d, of "total K v" k] K by (simp add: total_def)
    next
      case False
      then show ?thesis using whole_each_off[of k ks] K nn0 by (simp add: nonneg_on_def)
    qed
  qed
qed
(* GATE:END *)


section \<open>Granting whole or not at all is never exact\<close>

definition five_and_four :: "(nat, int) amounts" where
  "five_and_four = (\<lambda>k. if k = 1 then 5 else if k = 2 then 4 else 0)"

(* GATE:BEGIN LVn *)
theorem no_whole_or_nothing_rule_is_exact:
  assumes whole: "\<forall>w x k. R w x k = w k \<or> R w x k = 0"
  shows "\<not> exact {1::nat, 2} (R :: (nat, int) rule)"
proof
  assume ex: "exact {1::nat, 2} R"
  have nn: "nonneg_on {1::nat, 2} five_and_four" by (simp add: nonneg_on_def five_and_four_def)
  have t: "total {1::nat, 2} five_and_four = 9" by (simp add: total_def five_and_four_def)
  have "residual {1::nat, 2} R five_and_four 7 = 0" using ex nn t by (simp add: exact_def)
  then have s: "R five_and_four 7 1 + R five_and_four 7 2 = 7" by (simp add: residual_def total_def)
  have f1: "five_and_four 1 = 5" and f2: "five_and_four 2 = 4" by (simp_all add: five_and_four_def)
  have "R five_and_four 7 1 = 5 \<or> R five_and_four 7 1 = 0" using whole[rule_format, of five_and_four 7 1] f1 by simp
  moreover have "R five_and_four 7 2 = 4 \<or> R five_and_four 7 2 = 0" using whole[rule_format, of five_and_four 7 2] f2 by simp
  ultimately show False using s by auto
qed
(* GATE:END *)

end
