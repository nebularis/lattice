(* SPDX-License-Identifier: MPL-2.0 *)

(* Rounding over whole minor units: floor division leaves a residual below the number of parts,
   allocating it to the first parts in key order makes the parts sum exactly to the total, the
   allocation is the same in every order the weights are presented, and each floor part is the
   exact rational share rounded down (plan ledger, LG-7). Hand-written on the Kernel extracted
   from ontology/ledger/README.md section 10. *)

theory Rounding
imports Kernel
begin

text \<open>An example first. Ten minor units split three ways in equal weights: floor division gives
  3 each and leaves 1, which goes to the first key, so the parts are 4, 3 and 3.\<close>

value "(map (floor_part 10 {0::nat, 1, 2} (\<lambda>_. 1)) [0, 1, 2], leftover 10 {0::nat, 1, 2} (\<lambda>_. 1),
        map (to_first 10 {0::nat, 1, 2} (\<lambda>_. 1)) [0, 1, 2])"

lemma example_ten_in_three:
  "map (to_first 10 {0::nat, 1, 2} (\<lambda>_. 1)) [0, 1, 2] = [4, 3, 3]"
proof -
  have l: "leftover 10 {0::nat, 1, 2} (\<lambda>_. 1) = 1"
    by (simp add: leftover_def floor_part_def)
  have s: "sorted_list_of_set {0::nat, 1, 2} = [0, 1, 2]"
    using sorted_list_of_set_sort_remdups[of "[0::nat, 1, 2]"] by simp
  show ?thesis using l s by (simp add: to_first_def floor_part_def)
qed

lemma sum_floor_part:
  "(\<Sum>k\<in>K. floor_part t K w k) = (\<Sum>k\<in>K. (t * w k) div (\<Sum>j\<in>K. w j))"
  by (intro sum.cong) (simp_all add: floor_part_def)

lemma leftover_scaled:
  assumes fin: "finite K"
  shows "(\<Sum>j\<in>K. w j) * leftover t K w = (\<Sum>k\<in>K. (t * w k) mod (\<Sum>j\<in>K. w j))"
proof -
  let ?W = "\<Sum>j\<in>K. w j"
  have "(\<Sum>k\<in>K. (t * w k) mod ?W) = (\<Sum>k\<in>K. t * w k - ?W * ((t * w k) div ?W))"
    by (intro sum.cong) (simp_all add: minus_mult_div_eq_mod)
  also have "\<dots> = (\<Sum>k\<in>K. t * w k) - (\<Sum>k\<in>K. ?W * ((t * w k) div ?W))"
    by (simp add: sum_subtractf)
  also have "\<dots> = t * ?W - ?W * (\<Sum>k\<in>K. (t * w k) div ?W)"
    by (simp add: sum_distrib_left)
  also have "\<dots> = ?W * leftover t K w"
    by (simp add: leftover_def sum_floor_part right_diff_distrib mult.commute)
  finally show ?thesis by simp
qed

(* GATE:BEGIN LR1 *)
theorem floor_split_conserves:
  assumes fin: "finite K" and W: "0 < (\<Sum>k\<in>K. w k)"
  shows "(\<Sum>k\<in>K. floor_part t K w k) + leftover t K w = t"
    and "0 \<le> leftover t K w \<and> leftover t K w < int (card K)"
proof -
  show "(\<Sum>k\<in>K. floor_part t K w k) + leftover t K w = t"
    by (simp add: leftover_def)
  let ?W = "\<Sum>k\<in>K. w k"
  have scaled: "?W * leftover t K w = (\<Sum>k\<in>K. (t * w k) mod ?W)"
    by (rule leftover_scaled[OF fin])
  have lo: "0 \<le> (\<Sum>k\<in>K. (t * w k) mod ?W)"
    using W by (intro sum_nonneg) simp
  have hi: "(\<Sum>k\<in>K. (t * w k) mod ?W) \<le> of_nat (card K) * (?W - 1)"
  proof (rule sum_bounded_above)
    fix k
    show "(t * w k) mod ?W \<le> ?W - 1" using pos_mod_bound[OF W, of "t * w k"] by linarith
  qed
  have "K \<noteq> {}" using W by auto
  then have cpos: "0 < card K" using fin by (simp add: card_gt_0_iff)
  have "0 \<le> ?W * leftover t K w" using scaled lo by simp
  then have l0: "0 \<le> leftover t K w" using W by (simp add: zero_le_mult_iff)
  have l1: "leftover t K w < int (card K)"
  proof (rule ccontr)
    assume "\<not> leftover t K w < int (card K)"
    then have "int (card K) \<le> leftover t K w" by simp
    then have "?W * int (card K) \<le> ?W * leftover t K w" using W by (simp add: mult_left_mono)
    with scaled hi have "?W * int (card K) \<le> int (card K) * (?W - 1)" by simp
    then have "int (card K) \<le> 0" by (simp add: algebra_simps)
    with cpos show False by simp
  qed
  show "0 \<le> leftover t K w \<and> leftover t K w < int (card K)" using l0 l1 by simp
qed
(* GATE:END *)

lemma card_take_sorted:
  assumes "finite K"
  shows "card (set (take n (sorted_list_of_set K))) = min n (card K)"
proof -
  have "distinct (take n (sorted_list_of_set K))" by simp
  then have "card (set (take n (sorted_list_of_set K))) = length (take n (sorted_list_of_set K))"
    by (rule distinct_card)
  also have "\<dots> = min n (card K)" using assms by simp
  finally show ?thesis .
qed

lemma take_sorted_subset: "finite K \<Longrightarrow> set (take n (sorted_list_of_set K)) \<subseteq> K"
  by (metis set_sorted_list_of_set set_take_subset)

lemma weights_reordered:
  "distinct ps \<Longrightarrow> distinct ps' \<Longrightarrow> set ps = set ps' \<Longrightarrow> weights ps = weights ps'"
  by (simp add: weights_def fun_eq_iff sum_list_distinct_conv_sum_set)

(* GATE:BEGIN LR2 *)
theorem to_first_sums_exactly:
  fixes K :: "'k::linorder set"
  assumes fin: "finite K" and W: "0 < (\<Sum>k\<in>K. w k)"
  shows "(\<Sum>k\<in>K. to_first t K w k) = t"
proof -
  let ?S = "set (take (nat (leftover t K w)) (sorted_list_of_set K))"
  have l: "0 \<le> leftover t K w \<and> leftover t K w < int (card K)"
    using floor_split_conserves(2)[OF fin W] .
  have sub: "?S \<subseteq> K" by (rule take_sorted_subset[OF fin])
  have count: "(\<Sum>k\<in>K. (if k \<in> ?S then 1 else 0) :: int) = leftover t K w"
  proof -
    have "(\<Sum>k\<in>K. (if k \<in> ?S then 1 else 0) :: int) = int (card (K \<inter> ?S))"
      using fin by (simp add: sum.If_cases)
    also have "K \<inter> ?S = ?S" using sub by blast
    also have "card ?S = min (nat (leftover t K w)) (card K)" by (rule card_take_sorted[OF fin])
    also have "int (min (nat (leftover t K w)) (card K)) = leftover t K w"
      using l by (auto simp: min_def)
    finally show ?thesis .
  qed
  have "(\<Sum>k\<in>K. to_first t K w k)
          = (\<Sum>k\<in>K. floor_part t K w k) + (\<Sum>k\<in>K. (if k \<in> ?S then 1 else 0) :: int)"
    by (simp add: to_first_def sum.distrib)
  also have "\<dots> = t" using count floor_split_conserves(1)[OF fin W] by simp
  finally show ?thesis .
qed

theorem to_first_is_the_same_in_every_order:
  assumes "distinct ps" "distinct ps'" "set ps = set ps'"
  shows "to_first t (fst ` set ps) (weights ps) = to_first t (fst ` set ps') (weights ps')"
  using weights_reordered[OF assms] assms(3) by simp
(* GATE:END *)

lemma floor_part_refines:
  assumes "k \<in> K" "0 < (\<Sum>j\<in>K. w j)"
  shows "of_int (floor_part t K w k) \<le> (of_int (t * w k) / of_int (\<Sum>j\<in>K. w j) :: rat)
         \<and> (of_int (t * w k) / of_int (\<Sum>j\<in>K. w j) :: rat) < of_int (floor_part t K w k) + 1"
proof -
  define W where "W = (\<Sum>j\<in>K. w j)"
  define q where "q = (of_int (t * w k) / of_int W :: rat)"
  have "floor_part t K w k = (t * w k) div W" using assms(1) by (simp add: floor_part_def W_def)
  also have "\<dots> = \<lfloor>q\<rfloor>" unfolding q_def by (rule floor_divide_of_int_eq[symmetric])
  finally have fl: "floor_part t K w k = \<lfloor>q\<rfloor>" .
  have "of_int \<lfloor>q\<rfloor> \<le> q \<and> q < of_int \<lfloor>q\<rfloor> + 1" using floor_correct[of q] by simp
  then show ?thesis unfolding fl q_def W_def .
qed

end
