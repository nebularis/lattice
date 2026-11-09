(* SPDX-License-Identifier: MPL-2.0 *)

(* Rounding over whole minor units: floor division leaves a residual below the number of parts,
   allocating it to the first parts in key order makes the parts sum exactly to the total, the
   allocation is the same in every order the weights are presented, and each floor part is the
   exact rational share rounded down (plan ledger, LG-7). LG-8 adds the largest-remainder rule, the
   two rules lawful over whole units, and the rounded split of an amount across several accounts
   compared with the exact one. Hand-written on the Kernel extracted from
   ontology/ledger/README.md section 10. *)

theory Rounding
imports Draws "HOL-Library.Multiset"
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


section \<open>Largest remainder (LG-8)\<close>

text \<open>An example first, where the two rules differ. Ten minor units in weights 3, 2 and 1 give
  floor parts 5, 3 and 1, a residual of 1, and remainders 0, 2 and 4. To the first in order gives the
  unit to key 0, so 6, 3 and 1. Largest remainder gives it to key 2, so 5, 3 and 2.\<close>

value "(map (to_first 10 {0::nat, 1, 2} (\<lambda>k. 3 - int k)) [0, 1, 2],
        map (largest_remainder 10 {0::nat, 1, 2} (\<lambda>k. 3 - int k)) [0, 1, 2])"

lemma example_largest_remainder:
  "map (largest_remainder 10 {0::nat, 1, 2} (\<lambda>k. 3 - int k)) [0, 1, 2] = [5, 3, 2]"
  by code_simp

lemma example_to_first_differs:
  "map (to_first 10 {0::nat, 1, 2} (\<lambda>k. 3 - int k)) [0, 1, 2] = [6, 3, 1]"
  by code_simp

lemma card_take_distinct:
  assumes "distinct L" "set L = K"
  shows "card (set (take n L)) = min n (card K)"
proof -
  have "distinct (take n L)" using assms(1) by simp
  then have "card (set (take n L)) = length (take n L)" by (rule distinct_card)
  also have "\<dots> = min n (length L)" by simp
  also have "length L = card K" using distinct_card[OF assms(1)] assms(2) by simp
  finally show ?thesis .
qed

lemma bonus_count:
  assumes fin: "finite K" and d: "distinct L" and s: "set L = K"
      and l0: "0 \<le> l" and l1: "l \<le> int (card K)"
  shows "(\<Sum>k\<in>K. (if k \<in> set (take (nat l) L) then 1 else 0) :: int) = l"
proof -
  let ?S = "set (take (nat l) L)"
  have sub: "?S \<subseteq> K" using s set_take_subset by fast
  have "(\<Sum>k\<in>K. (if k \<in> ?S then 1 else 0) :: int) = int (card (K \<inter> ?S))"
    using fin by (simp add: sum.If_cases)
  also have "K \<inter> ?S = ?S" using sub by blast
  also have "card ?S = min (nat l) (card K)" by (rule card_take_distinct[OF d s])
  also have "int (min (nat l) (card K)) = l" using l0 l1 by (auto simp: min_def)
  finally show ?thesis .
qed

lemma sorted_take_le:
  assumes srt: "sorted (map f L)" and k: "k \<in> set (take n L)"
      and j: "j \<in> set L" and nj: "j \<notin> set (take n L)"
  shows "f k \<le> f j"
proof -
  obtain i where i: "i < length (take n L)" "take n L ! i = k"
    using k by (auto simp: in_set_conv_nth)
  obtain m where m: "m < length L" "L ! m = j"
    using j by (auto simp: in_set_conv_nth)
  have "n \<le> m"
  proof (rule ccontr)
    assume "\<not> n \<le> m"
    then have "m < length (take n L)" using m(1) by simp
    then have "take n L ! m \<in> set (take n L)" by (rule nth_mem)
    then have "j \<in> set (take n L)" using m \<open>\<not> n \<le> m\<close> by simp
    with nj show False by simp
  qed
  have ik: "L ! i = k" "i < n" "i < length L" using i by auto
  have "i \<le> m" using ik(2) \<open>n \<le> m\<close> by simp
  then have "map f L ! i \<le> map f L ! m" using sorted_nth_mono[OF srt \<open>i \<le> m\<close>] m(1) by simp
  then show ?thesis using ik m by simp
qed

lemma remainder_nonneg: "0 < (\<Sum>j\<in>K. w j) \<Longrightarrow> 0 \<le> remainder t K w k"
  by (simp add: remainder_def)

lemma remainder_bound: "0 < (\<Sum>j\<in>K. w j) \<Longrightarrow> remainder t K w k \<le> (\<Sum>j\<in>K. w j) - 1"
  using pos_mod_bound[of "\<Sum>j\<in>K. w j" "t * w k"] by (simp add: remainder_def)

lemma floor_part_mod:
  "k \<in> K \<Longrightarrow> floor_part t K w k * (\<Sum>j\<in>K. w j) + remainder t K w k = t * w k"
  using div_mult_mod_eq[of "t * w k" "\<Sum>j\<in>K. w j"] by (simp add: floor_part_def remainder_def)

text \<open>A key the residual reaches had a positive remainder. Were its remainder zero, every key
  with a positive remainder would be reached before it, so fewer keys would have positive
  remainders than the residual has units, though the remainders sum to the residual times the
  sum of the weights and each is below that sum.\<close>

lemma largest_remainder_reaches_a_positive_remainder:
  fixes K :: "'k::linorder set"
  assumes fin: "finite K" and W: "0 < (\<Sum>j\<in>K. w j)"
      and c: "k \<in> set (take (nat (leftover t K w)) (sort_key (\<lambda>j. - remainder t K w j) (sorted_list_of_set K)))"
  shows "0 < remainder t K w k"
proof (rule ccontr)
  let ?W = "\<Sum>j\<in>K. w j"
  let ?f = "\<lambda>j. - remainder t K w j"
  let ?L = "sort_key ?f (sorted_list_of_set K)"
  let ?n = "nat (leftover t K w)"
  let ?S = "set (take ?n ?L)"
  assume "\<not> 0 < remainder t K w k"
  then have r0: "remainder t K w k = 0" using remainder_nonneg[OF W, of t k] by simp
  have l: "0 \<le> leftover t K w \<and> leftover t K w < int (card K)"
    using floor_split_conserves(2)[OF fin W] .
  have d: "distinct ?L" by simp
  have s: "set ?L = K" using fin by simp
  have nle: "?n \<le> card K" using l by (simp add: nat_le_iff)
  have cardS: "card ?S = ?n" using card_take_distinct[OF d s, of ?n] nle by (simp add: min_def)
  have srt: "sorted (map ?f ?L)" by simp
  define P where "P = {j\<in>K. 0 < remainder t K w j}"
  have PS: "P \<subseteq> ?S - {k}"
  proof
    fix j
    assume "j \<in> P"
    then have jK: "j \<in> K" and jpos: "0 < remainder t K w j" by (auto simp: P_def)
    have "j \<in> ?S"
    proof (rule ccontr)
      assume nj: "j \<notin> ?S"
      have "j \<in> set ?L" using s jK by simp
      then have "?f k \<le> ?f j" using sorted_take_le[OF srt c _ nj] by blast
      then show False using r0 jpos by simp
    qed
    moreover have "j \<noteq> k" using jpos r0 by auto
    ultimately show "j \<in> ?S - {k}" by simp
  qed
  have "card P \<le> card (?S - {k})" by (rule card_mono) (simp_all add: PS)
  also have "card (?S - {k}) = ?n - 1" using c cardS by simp
  finally have cP: "card P \<le> ?n - 1" .
  have npos: "0 < ?n" using c cardS by (metis card_gt_0_iff empty_iff finite_set)
  have scaled: "?W * leftover t K w = (\<Sum>j\<in>K. remainder t K w j)"
    using leftover_scaled[OF fin] by (simp add: remainder_def)
  have "(\<Sum>j\<in>K. remainder t K w j) = (\<Sum>j\<in>P. remainder t K w j)"
  proof (rule sum.mono_neutral_right[OF fin])
    show "P \<subseteq> K" by (auto simp: P_def)
    show "\<forall>i\<in>K - P. remainder t K w i = 0"
    proof
      fix i
      assume "i \<in> K - P"
      then have "\<not> 0 < remainder t K w i" by (simp add: P_def)
      with remainder_nonneg[OF W, of t i] show "remainder t K w i = 0" by simp
    qed
  qed
  also have "\<dots> \<le> of_nat (card P) * (?W - 1)"
    by (rule sum_bounded_above) (rule remainder_bound[OF W])
  finally have bound: "?W * leftover t K w \<le> of_nat (card P) * (?W - 1)" using scaled by simp
  have ln: "leftover t K w = int ?n" using l by simp
  have "int (card P) \<le> int ?n - 1" using cP npos by linarith
  then have "of_nat (card P) * (?W - 1) \<le> (int ?n - 1) * (?W - 1)"
    using W by (intro mult_right_mono) simp_all
  with bound ln have "?W * int ?n \<le> (int ?n - 1) * (?W - 1)" by simp
  then have "?W + int ?n \<le> 1" by (simp add: algebra_simps)
  then show False using W npos by linarith
qed

lemma weights_mset: "mset ps = mset ps' \<Longrightarrow> weights ps = weights ps'"
proof -
  assume eq: "mset ps = mset ps'"
  show "weights ps = weights ps'"
  proof
    fix k
    have "mset (map snd (filter (\<lambda>q. fst q = k) ps)) = mset (map snd (filter (\<lambda>q. fst q = k) ps'))"
      using eq by simp
    then show "weights ps k = weights ps' k" by (metis sum_mset_sum_list weights_def)
  qed
qed

(* GATE:BEGIN LR3 *)
theorem largest_remainder_sums_exactly:
  fixes K :: "'k::linorder set"
  assumes fin: "finite K" and W: "0 < (\<Sum>k\<in>K. w k)"
  shows "(\<Sum>k\<in>K. largest_remainder t K w k) = t"
proof -
  let ?L = "sort_key (\<lambda>j. - remainder t K w j) (sorted_list_of_set K)"
  have l: "0 \<le> leftover t K w \<and> leftover t K w < int (card K)"
    using floor_split_conserves(2)[OF fin W] .
  have d: "distinct ?L" by simp
  have s: "set ?L = K" using fin by simp
  have "(\<Sum>k\<in>K. largest_remainder t K w k)
          = (\<Sum>k\<in>K. floor_part t K w k)
            + (\<Sum>k\<in>K. (if k \<in> set (take (nat (leftover t K w)) ?L) then 1 else 0) :: int)"
    by (simp add: largest_remainder_def sum.distrib)
  also have "\<dots> = (\<Sum>k\<in>K. floor_part t K w k) + leftover t K w"
    using bonus_count[OF fin d s] l by simp
  also have "\<dots> = t" by (rule floor_split_conserves(1)[OF fin W])
  finally show ?thesis .
qed

theorem largest_remainder_takes_the_largest:
  fixes K :: "'k::linorder set"
  assumes fin: "finite K" and j: "j \<in> K"
      and k_reached: "largest_remainder t K w k = floor_part t K w k + 1"
      and j_not: "largest_remainder t K w j = floor_part t K w j"
  shows "remainder t K w j \<le> remainder t K w k"
proof -
  let ?f = "\<lambda>j. - remainder t K w j"
  let ?L = "sort_key ?f (sorted_list_of_set K)"
  let ?S = "set (take (nat (leftover t K w)) ?L)"
  have "k \<in> ?S" using k_reached by (simp add: largest_remainder_def split: if_splits)
  moreover have "j \<notin> ?S" using j_not by (simp add: largest_remainder_def split: if_splits)
  moreover have "j \<in> set ?L" using fin j by simp
  moreover have "sorted (map ?f ?L)" by simp
  ultimately have "?f k \<le> ?f j" using sorted_take_le by metis
  then show ?thesis by simp
qed

theorem largest_remainder_is_the_same_in_every_order:
  assumes "mset ps = mset ps'"
  shows "largest_remainder t (fst ` set ps) (weights ps) = largest_remainder t (fst ` set ps') (weights ps')"
  using weights_mset[OF assms] mset_eq_setD[OF assms] by simp
(* GATE:END *)


section \<open>The two rules lawful over whole units (LG-8)\<close>

text \<open>The four axioms of a lawful rule, over whole minor units: the parts sum to the total, each
  part lies between zero and its own weight, a key outside the key set gets nothing, and splitting
  the whole sum of the weights returns the weights. A total is at most the sum of the weights.\<close>

definition int_lawful :: "'k set \<Rightarrow> (int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int) \<Rightarrow> bool" where
  "int_lawful K R \<longleftrightarrow>
     (\<forall>w t. (\<forall>k\<in>K. 0 \<le> w k) \<and> 0 \<le> t \<and> t \<le> (\<Sum>k\<in>K. w k) \<longrightarrow>
        (\<Sum>k\<in>K. R t K w k) = t \<and> (\<forall>k\<in>K. 0 \<le> R t K w k \<and> R t K w k \<le> w k)
        \<and> (\<forall>k. k \<notin> K \<longrightarrow> R t K w k = 0))
     \<and> (\<forall>w. (\<forall>k\<in>K. 0 \<le> w k) \<longrightarrow> (\<forall>k\<in>K. R (\<Sum>j\<in>K. w j) K w k = w k))"

text \<open>The negative instance first. To the first in order gives a residual unit to the first key
  whatever its weight, so a key of weight zero can receive one: one unit in weights 0, 3 and 3
  floors to nothing and goes to key 0.\<close>

lemma to_first_can_exceed_a_zero_weight:
  "to_first 1 {0::nat, 1, 2} (\<lambda>k. if k = 0 then 0 else 3) 0 = 1"
  by code_simp

lemma floor_part_nonneg:
  "0 < (\<Sum>j\<in>K. w j) \<Longrightarrow> 0 \<le> t \<Longrightarrow> 0 \<le> w k \<Longrightarrow> 0 \<le> floor_part t K w k"
  by (simp add: floor_part_def pos_imp_zdiv_nonneg_iff)

lemma floor_part_le_weight:
  assumes W: "0 < (\<Sum>j\<in>K. w j)" and t: "t \<le> (\<Sum>j\<in>K. w j)" and w: "0 \<le> w k"
  shows "floor_part t K w k \<le> w k"
proof (cases "k \<in> K")
  case True
  have "t * w k \<le> (\<Sum>j\<in>K. w j) * w k" using t w by (rule mult_right_mono)
  then have "(t * w k) div (\<Sum>j\<in>K. w j) \<le> ((\<Sum>j\<in>K. w j) * w k) div (\<Sum>j\<in>K. w j)"
    using W by (rule zdiv_mono1)
  then show ?thesis using True W by (simp add: floor_part_def)
next
  case False
  then show ?thesis using w by (simp add: floor_part_def)
qed

lemma floor_part_below_weight:
  assumes k: "k \<in> K" and W: "0 < (\<Sum>j\<in>K. w j)" and lt: "floor_part t K w k * (\<Sum>j\<in>K. w j) < (\<Sum>j\<in>K. w j) * w k"
  shows "floor_part t K w k + 1 \<le> w k"
proof -
  have "floor_part t K w k * (\<Sum>j\<in>K. w j) < w k * (\<Sum>j\<in>K. w j)" using lt by (simp add: mult.commute)
  then have "floor_part t K w k < w k" using W by (simp add: mult_less_cancel_right)
  then show ?thesis by simp
qed

lemma whole_floor_part:
  "k \<in> K \<Longrightarrow> 0 < (\<Sum>j\<in>K. w j) \<Longrightarrow> floor_part (\<Sum>j\<in>K. w j) K w k = w k"
  by (simp add: floor_part_def)

lemma whole_leftover:
  assumes "finite K" and W: "0 < (\<Sum>j\<in>K. w j)"
  shows "leftover (\<Sum>j\<in>K. w j) K w = 0"
proof -
  have "(\<Sum>k\<in>K. floor_part (\<Sum>j\<in>K. w j) K w k) = (\<Sum>k\<in>K. w k)"
    by (rule sum.cong) (simp_all add: whole_floor_part[OF _ W])
  then show ?thesis by (simp add: leftover_def)
qed

lemma zero_weights:
  fixes w :: "'k \<Rightarrow> int"
  assumes fin: "finite K" and nn: "\<forall>k\<in>K. 0 \<le> w k" and z: "(\<Sum>k\<in>K. w k) = 0"
  shows "\<forall>k\<in>K. w k = 0"
proof
  fix k
  assume k: "k \<in> K"
  have "w k \<le> (\<Sum>j\<in>K. w j)" using member_le_sum[of k K w] fin nn k by simp
  then show "w k = 0" using z nn k by (simp add: order_antisym)
qed

lemma largest_remainder_zero_sum:
  assumes z: "(\<Sum>k\<in>K. w k) = 0"
  shows "largest_remainder 0 K w k = 0"
proof -
  have f: "floor_part 0 K w j = 0" for j by (simp add: floor_part_def)
  have "leftover 0 K w = 0" by (simp add: leftover_def f)
  then show ?thesis by (simp add: largest_remainder_def f)
qed

lemma largest_remainder_off:
  assumes k: "k \<notin> K" and fin: "finite K"
  shows "largest_remainder t K w k = 0"
proof -
  let ?S = "set (take (nat (leftover t K w)) (sort_key (\<lambda>j. - remainder t K w j) (sorted_list_of_set K)))"
  have "?S \<subseteq> set (sort_key (\<lambda>j. - remainder t K w j) (sorted_list_of_set K))" by (rule set_take_subset)
  also have "\<dots> = K" using fin by simp
  finally have "k \<notin> ?S" using k by blast
  moreover have "floor_part t K w k = 0" using k by (simp add: floor_part_def)
  ultimately show ?thesis by (simp add: largest_remainder_def)
qed

lemma to_first_off:
  assumes k: "k \<notin> K" and fin: "finite K"
  shows "to_first t K w k = 0"
proof -
  have "k \<notin> set (take (nat (leftover t K w)) (sorted_list_of_set K))"
    using take_sorted_subset[OF fin] k by blast
  moreover have "floor_part t K w k = 0" using k by (simp add: floor_part_def)
  ultimately show ?thesis by (simp add: to_first_def)
qed

(* GATE:BEGIN LR4 *)
theorem largest_remainder_lawful:
  fixes K :: "'k::linorder set"
  assumes fin: "finite K"
  shows "int_lawful K largest_remainder"
  unfolding int_lawful_def
proof (rule conjI; intro allI impI)
  fix w :: "'k \<Rightarrow> int" and t :: int
  assume a: "(\<forall>k\<in>K. 0 \<le> w k) \<and> 0 \<le> t \<and> t \<le> (\<Sum>k\<in>K. w k)"
  then have nn: "\<forall>k\<in>K. 0 \<le> w k" and t0: "0 \<le> t" and tW: "t \<le> (\<Sum>k\<in>K. w k)" by simp_all
  have off: "\<forall>k. k \<notin> K \<longrightarrow> largest_remainder t K w k = 0"
    using largest_remainder_off[OF _ fin] by blast
  show "(\<Sum>k\<in>K. largest_remainder t K w k) = t
        \<and> (\<forall>k\<in>K. 0 \<le> largest_remainder t K w k \<and> largest_remainder t K w k \<le> w k)
        \<and> (\<forall>k. k \<notin> K \<longrightarrow> largest_remainder t K w k = 0)"
  proof (cases "(\<Sum>k\<in>K. w k) = 0")
    case True
    then have t: "t = 0" using t0 tW by simp
    have z: "\<forall>k\<in>K. w k = 0" by (rule zero_weights[OF fin nn True])
    have "\<forall>k. largest_remainder t K w k = 0" using largest_remainder_zero_sum[OF True] t by simp
    then show ?thesis using t z by simp
  next
    case False
    then have W: "0 < (\<Sum>k\<in>K. w k)" using sum_nonneg[of K w] nn by simp
    have bounds: "0 \<le> largest_remainder t K w k \<and> largest_remainder t K w k \<le> w k" if k: "k \<in> K" for k
    proof (cases "largest_remainder t K w k = floor_part t K w k")
      case True
      then show ?thesis using floor_part_nonneg[OF W t0] floor_part_le_weight[OF W tW] nn k by simp
    next
      case False
      let ?L = "sort_key (\<lambda>j. - remainder t K w j) (sorted_list_of_set K)"
      have c: "k \<in> set (take (nat (leftover t K w)) ?L)"
        using False by (simp add: largest_remainder_def split: if_splits)
      have plus: "largest_remainder t K w k = floor_part t K w k + 1"
        using c by (simp add: largest_remainder_def)
      have rpos: "0 < remainder t K w k" by (rule largest_remainder_reaches_a_positive_remainder[OF fin W c])
      have "floor_part t K w k * (\<Sum>j\<in>K. w j) < t * w k" using floor_part_mod[OF k, of t w] rpos by linarith
      also have "\<dots> \<le> (\<Sum>j\<in>K. w j) * w k" using mult_right_mono[OF tW, of "w k"] nn k by simp
      finally have "floor_part t K w k + 1 \<le> w k" by (rule floor_part_below_weight[OF k W])
      then show ?thesis using plus floor_part_nonneg[OF W t0] nn k by simp
    qed
    show ?thesis using largest_remainder_sums_exactly[OF fin W] bounds off by blast
  qed
next
  fix w :: "'k \<Rightarrow> int"
  assume nn: "\<forall>k\<in>K. 0 \<le> w k"
  show "\<forall>k\<in>K. largest_remainder (\<Sum>j\<in>K. w j) K w k = w k"
  proof (cases "(\<Sum>k\<in>K. w k) = 0")
    case True
    then show ?thesis using zero_weights[OF fin nn True] largest_remainder_zero_sum[OF True] by simp
  next
    case False
    then have W: "0 < (\<Sum>k\<in>K. w k)" using sum_nonneg[of K w] nn by simp
    show ?thesis using whole_leftover[OF fin W] whole_floor_part[OF _ W]
      by (simp add: largest_remainder_def)
  qed
qed

theorem to_first_lawful_on_positive_weights:
  fixes K :: "'k::linorder set"
  assumes fin: "finite K" and pos: "\<forall>k\<in>K. 0 < w k"
  shows "0 \<le> t \<Longrightarrow> t \<le> (\<Sum>k\<in>K. w k) \<Longrightarrow>
           (\<Sum>k\<in>K. to_first t K w k) = t \<and> (\<forall>k\<in>K. 0 \<le> to_first t K w k \<and> to_first t K w k \<le> w k)
           \<and> (\<forall>k. k \<notin> K \<longrightarrow> to_first t K w k = 0)"
    and "\<forall>k\<in>K. to_first (\<Sum>j\<in>K. w j) K w k = w k"
proof -
  have nn: "\<forall>k\<in>K. 0 \<le> w k" using pos by (simp add: less_imp_le)
  have off: "\<forall>k. k \<notin> K \<longrightarrow> to_first t K w k = 0" for t using to_first_off[OF _ fin] by blast
  show "\<forall>k\<in>K. to_first (\<Sum>j\<in>K. w j) K w k = w k"
  proof (cases "K = {}")
    case True
    then show ?thesis by simp
  next
    case False
    then have W: "0 < (\<Sum>k\<in>K. w k)" using fin pos by (simp add: sum_pos)
    show ?thesis using whole_leftover[OF fin W] whole_floor_part[OF _ W] by (simp add: to_first_def)
  qed
  assume t0: "0 \<le> t" and tW: "t \<le> (\<Sum>k\<in>K. w k)"
  show "(\<Sum>k\<in>K. to_first t K w k) = t \<and> (\<forall>k\<in>K. 0 \<le> to_first t K w k \<and> to_first t K w k \<le> w k)
          \<and> (\<forall>k. k \<notin> K \<longrightarrow> to_first t K w k = 0)"
  proof (cases "K = {}")
    case True
    then show ?thesis using t0 tW off by simp
  next
    case False
    then have W: "0 < (\<Sum>k\<in>K. w k)" using fin pos by (simp add: sum_pos)
    have bounds: "0 \<le> to_first t K w k \<and> to_first t K w k \<le> w k" if k: "k \<in> K" for k
    proof (cases "to_first t K w k = floor_part t K w k")
      case True
      then show ?thesis using floor_part_nonneg[OF W t0] floor_part_le_weight[OF W tW] nn k by simp
    next
      case False
      then have plus: "to_first t K w k = floor_part t K w k + 1" by (simp add: to_first_def split: if_splits)
      have "t \<noteq> (\<Sum>k\<in>K. w k)"
      proof
        assume "t = (\<Sum>k\<in>K. w k)"
        then have "leftover t K w = 0" using whole_leftover[OF fin W] by simp
        then show False using False by (simp add: to_first_def)
      qed
      then have tlt: "t < (\<Sum>k\<in>K. w k)" using tW by simp
      have "floor_part t K w k * (\<Sum>j\<in>K. w j) \<le> t * w k"
        using floor_part_mod[OF k, of t w] remainder_nonneg[OF W, of t k] by linarith
      also have "\<dots> < (\<Sum>j\<in>K. w j) * w k" using mult_strict_right_mono[OF tlt, of "w k"] pos k by simp
      finally have "floor_part t K w k + 1 \<le> w k" by (rule floor_part_below_weight[OF k W])
      then show ?thesis using plus floor_part_nonneg[OF W t0] nn k by simp
    qed
    show ?thesis using to_first_sums_exactly[OF fin W] bounds off by blast
  qed
qed
(* GATE:END *)


section \<open>The refinement beyond one part (LG-8)\<close>

text \<open>Each rounded part is within one minor unit of the exact share, and the split of an amount
  across several accounts in turn, rounded by largest remainder, takes from every account exactly
  what the exact split takes, so rounding moves amounts between keys and never between accounts.\<close>

lemma of_int_min_rat: "(of_int (min a b) :: rat) = min (of_int a) (of_int b)"
  by (simp add: min_def)

lemma of_int_max_rat: "(of_int (max a b) :: rat) = max (of_int a) (of_int b)"
  by (simp add: max_def)

lemma available_of_int:
  assumes tr: "tree A parent" and a: "a \<in> A" and e: "\<forall>b. balr b = of_int (bali b)"
  shows "available parent balr a = of_int (Min (bali ` path parent a))"
proof -
  have fin: "finite (bali ` path parent a)" using finite_path[OF tr a] by simp
  have ne: "bali ` path parent a \<noteq> {}" using path_self[of a parent] by blast
  have mono: "mono (of_int :: int \<Rightarrow> rat)" by (simp add: mono_def)
  have "balr ` path parent a = of_int ` (bali ` path parent a)" using e by (simp add: image_image)
  then show ?thesis unfolding available_def using mono_Min_commute[OF mono fin ne] by simp
qed

lemma spread_int_refines:
  fixes K :: "'k::linorder set"
  assumes fin: "finite K" and ok: "lawful K R" and tr: "tree A parent"
  shows "set accts \<subseteq> A \<Longrightarrow> nonneg_on K vr \<Longrightarrow> (\<forall>k\<in>K. 0 \<le> vi k) \<Longrightarrow> (\<forall>k. k \<notin> K \<longrightarrow> vi k = 0)
    \<Longrightarrow> total K vr = of_int (\<Sum>k\<in>K. vi k) \<Longrightarrow> (\<forall>b. balr b = of_int (bali b))
    \<Longrightarrow> spread K R parent accts balr vr = (ps, r, balr')
    \<Longrightarrow> spread_int K largest_remainder parent accts bali vi = (qs, s, bali')
    \<Longrightarrow> (\<forall>b. balr' b = of_int (bali' b))
        \<and> map (total K) ps = map (\<lambda>q. of_int (\<Sum>k\<in>K. q k)) qs
        \<and> (\<forall>k. sum_list (map (\<lambda>q. q k) qs) + s k = vi k)"
proof (induction accts arbitrary: balr vr bali vi ps r balr' qs s bali')
  case Nil
  then show ?case by auto
next
  case (Cons a rest)
  have vrnn: "nonneg_on K vr" and vinn: "\<forall>k\<in>K. 0 \<le> vi k" and vioff: "\<forall>k. k \<notin> K \<longrightarrow> vi k = 0"
    and tot: "total K vr = of_int (\<Sum>k\<in>K. vi k)" and bal: "\<forall>b. balr b = of_int (bali b)"
    using Cons.prems(2-6) by simp_all
  have aA: "a \<in> A" using Cons.prems(1) by simp
  define xi where "xi = min (\<Sum>k\<in>K. vi k) (max 0 (Min (bali ` path parent a)))"
  define pi where "pi = largest_remainder xi K vi"
  define xr where "xr = min (total K vr) (max 0 (available parent balr a))"
  define pr where "pr = R vr xr"
  define balr1 where "balr1 = debit (path parent a) xr balr"
  define bali1 where "bali1 = (\<lambda>b. if b \<in> path parent a then bali b - xi else bali b)"
  define vr1 where "vr1 = less vr pr"
  define vi1 where "vi1 = (\<lambda>k. vi k - pi k)"
  have av: "available parent balr a = of_int (Min (bali ` path parent a))"
    by (rule available_of_int[OF tr aA bal])
  have xrxi: "xr = of_int xi" by (simp add: xr_def xi_def tot av of_int_min_rat of_int_max_rat)
  have vsum0: "0 \<le> (\<Sum>k\<in>K. vi k)" using vinn by (simp add: sum_nonneg)
  have xi0: "0 \<le> xi" using vsum0 by (simp add: xi_def)
  have xiv: "xi \<le> (\<Sum>k\<in>K. vi k)" by (simp add: xi_def)
  have lr: "(\<Sum>k\<in>K. pi k) = xi \<and> (\<forall>k\<in>K. 0 \<le> pi k \<and> pi k \<le> vi k) \<and> (\<forall>k. k \<notin> K \<longrightarrow> pi k = 0)"
    using largest_remainder_lawful[OF fin] vinn xi0 xiv unfolding int_lawful_def pi_def by blast
  have xr0: "0 \<le> xr" using xi0 by (simp add: xrxi)
  have xrv: "xr \<le> total K vr" by (simp add: xr_def)
  have prt: "total K pr = xr" unfolding pr_def by (rule lawful_exact[OF ok vrnn xr0 xrv])
  have prfit: "fits_in pr vr" unfolding pr_def by (rule lawful_fits_in[OF ok vrnn xr0 xrv])
  have prnn: "nonneg_on K pr" unfolding pr_def by (rule lawful_nonneg[OF ok vrnn xr0 xrv])
  obtain ps1 r1 balr2 where recr: "spread K R parent rest balr1 vr1 = (ps1, r1, balr2)"
    by (metis prod_cases3)
  obtain qs1 s1 bali2 where reci: "spread_int K largest_remainder parent rest bali1 vi1 = (qs1, s1, bali2)"
    by (metis prod_cases3)
  have outr: "ps = pr # ps1" "r = r1" "balr' = balr2"
    using Cons.prems(7) recr by (simp_all add: xr_def pr_def balr1_def vr1_def Let_def)
  have stepi: "spread_int K largest_remainder parent (a # rest) bali vi = (pi # qs1, s1, bali2)"
    using reci unfolding bali1_def vi1_def by (simp add: Let_def flip: xi_def pi_def)
  have outi: "qs = pi # qs1" "s = s1" "bali' = bali2"
    using Cons.prems(8) stepi by simp_all
  have sub1: "set rest \<subseteq> A" using Cons.prems(1) by simp
  have vr1nn: "nonneg_on K vr1" unfolding vr1_def by (rule nonneg_less[OF vrnn prnn prfit])
  have vi1nn: "\<forall>k\<in>K. 0 \<le> vi1 k" using lr by (simp add: vi1_def)
  have vi1off: "\<forall>k. k \<notin> K \<longrightarrow> vi1 k = 0" using lr vioff by (simp add: vi1_def)
  have tot1: "total K vr1 = of_int (\<Sum>k\<in>K. vi1 k)"
  proof -
    have "total K vr1 = total K vr - total K pr" unfolding vr1_def by (rule total_less[OF fin])
    also have "\<dots> = of_int (\<Sum>k\<in>K. vi k) - of_int xi" using tot prt xrxi by simp
    also have "\<dots> = of_int ((\<Sum>k\<in>K. vi k) - (\<Sum>k\<in>K. pi k))" using lr by simp
    also have "\<dots> = of_int (\<Sum>k\<in>K. vi1 k)" by (simp add: vi1_def sum_subtractf)
    finally show ?thesis .
  qed
  have bal1: "\<forall>b. balr1 b = of_int (bali1 b)" by (simp add: balr1_def bali1_def debit_def bal xrxi)
  have IH: "(\<forall>b. balr2 b = of_int (bali2 b))
        \<and> map (total K) ps1 = map (\<lambda>q. of_int (\<Sum>k\<in>K. q k)) qs1
        \<and> (\<forall>k. sum_list (map (\<lambda>q. q k) qs1) + s1 k = vi1 k)"
    by (rule Cons.IH[OF sub1 vr1nn vi1nn vi1off tot1 bal1 recr reci])
  have head: "total K pr = of_int (\<Sum>k\<in>K. pi k)" using prt xrxi lr by simp
  have keys: "\<forall>k. sum_list (map (\<lambda>q. q k) qs) + s k = vi k"
  proof
    fix k
    have "sum_list (map (\<lambda>q. q k) qs1) + s1 k = vi k - pi k" using IH by (simp add: vi1_def)
    then show "sum_list (map (\<lambda>q. q k) qs) + s k = vi k" by (simp add: outi algebra_simps)
  qed
  show ?case using IH head keys by (simp add: outr outi)
qed

(* GATE:BEGIN LR5 *)
theorem rounded_part_within_one_unit:
  fixes K :: "'k::linorder set"
  assumes fin: "finite K" and k: "k \<in> K" and W: "0 < (\<Sum>j\<in>K. w j)"
  shows "\<bar>of_int (to_first t K w k) - of_int (t * w k) / of_int (\<Sum>j\<in>K. w j)\<bar> \<le> (1::rat)"
    and "\<bar>of_int (largest_remainder t K w k) - of_int (t * w k) / of_int (\<Sum>j\<in>K. w j)\<bar> < (1::rat)"
proof -
  define q where "q = (of_int (t * w k) / of_int (\<Sum>j\<in>K. w j) :: rat)"
  define f where "f = (of_int (floor_part t K w k) :: rat)"
  have fq: "f \<le> q \<and> q < f + 1" using floor_part_refines[OF k W] by (simp add: q_def f_def)
  have "\<bar>of_int (to_first t K w k) - q\<bar> \<le> 1"
  proof (cases "to_first t K w k = floor_part t K w k")
    case True
    then have e: "(of_int (to_first t K w k) :: rat) = f" by (simp add: f_def)
    show ?thesis using fq unfolding e abs_le_iff by linarith
  next
    case False
    then have "to_first t K w k = floor_part t K w k + 1" by (simp add: to_first_def split: if_splits)
    then have e: "(of_int (to_first t K w k) :: rat) = f + 1" by (simp add: f_def)
    show ?thesis using fq unfolding e abs_le_iff by linarith
  qed
  then show "\<bar>of_int (to_first t K w k) - of_int (t * w k) / of_int (\<Sum>j\<in>K. w j)\<bar> \<le> (1::rat)"
    by (simp add: q_def)
  have "\<bar>of_int (largest_remainder t K w k) - q\<bar> < 1"
  proof (cases "largest_remainder t K w k = floor_part t K w k")
    case True
    then have e: "(of_int (largest_remainder t K w k) :: rat) = f" by (simp add: f_def)
    show ?thesis using fq unfolding e abs_less_iff by linarith
  next
    case False
    let ?L = "sort_key (\<lambda>j. - remainder t K w j) (sorted_list_of_set K)"
    have c: "k \<in> set (take (nat (leftover t K w)) ?L)"
      using False by (simp add: largest_remainder_def split: if_splits)
    then have "largest_remainder t K w k = floor_part t K w k + 1" by (simp add: largest_remainder_def)
    then have e: "(of_int (largest_remainder t K w k) :: rat) = f + 1" by (simp add: f_def)
    have rpos: "0 < remainder t K w k" by (rule largest_remainder_reaches_a_positive_remainder[OF fin W c])
    have "floor_part t K w k * (\<Sum>j\<in>K. w j) < t * w k" using floor_part_mod[OF k, of t w] rpos by linarith
    then have prev: "(of_int (floor_part t K w k) :: rat) * of_int (\<Sum>j\<in>K. w j) < of_int (t * w k)"
      by (metis of_int_less_iff of_int_mult)
    have Wq: "(0::rat) < of_int (\<Sum>j\<in>K. w j)" by (subst of_int_0_less_iff) (rule W)
    have "f < q" unfolding q_def f_def by (subst pos_less_divide_eq[OF Wq]) (rule prev)
    then show ?thesis using fq unfolding e abs_less_iff by linarith
  qed
  then show "\<bar>of_int (largest_remainder t K w k) - of_int (t * w k) / of_int (\<Sum>j\<in>K. w j)\<bar> < (1::rat)"
    by (simp add: q_def)
qed

theorem rounded_spread_takes_what_the_exact_takes:
  fixes K :: "'k::linorder set"
  assumes fin: "finite K" and ok: "lawful K R" and tr: "tree A parent" and sub: "set accts \<subseteq> A"
      and nn: "\<forall>k\<in>K. 0 \<le> v k" and off: "\<forall>k. k \<notin> K \<longrightarrow> v k = 0"
      and sr: "spread K R parent accts (\<lambda>b. of_int (bal b)) (\<lambda>k. of_int (v k)) = (ps, r, bal_r)"
      and si: "spread_int K largest_remainder parent accts bal v = (qs, s, bal_i)"
  shows "\<forall>b. bal_r b = of_int (bal_i b)"
    and "map (total K) ps = map (\<lambda>q. of_int (\<Sum>k\<in>K. q k)) qs"
    and "\<forall>k. sum_list (map (\<lambda>q. q k) qs) + s k = v k"
proof -
  have vrnn: "nonneg_on K (\<lambda>k. of_int (v k))"
    unfolding nonneg_on_def
  proof (intro conjI allI impI)
    fix k
    show "(0::rat) \<le> of_int (v k)" using nn off by (cases "k \<in> K") simp_all
  next
    fix k
    assume "k \<notin> K"
    then show "(of_int (v k) :: rat) = 0" using off by simp
  qed
  have tot: "total K (\<lambda>k. of_int (v k)) = of_int (\<Sum>k\<in>K. v k)" by (simp add: total_def)
  have bal: "\<forall>b. (of_int (bal b) :: rat) = of_int (bal b)" by simp
  have all: "(\<forall>b. bal_r b = of_int (bal_i b))
        \<and> map (total K) ps = map (\<lambda>q. of_int (\<Sum>k\<in>K. q k)) qs
        \<and> (\<forall>k. sum_list (map (\<lambda>q. q k) qs) + s k = v k)"
    by (rule spread_int_refines[OF fin ok tr sub vrnn nn off tot bal sr si])
  then show "\<forall>b. bal_r b = of_int (bal_i b)"
    and "map (total K) ps = map (\<lambda>q. of_int (\<Sum>k\<in>K. q k)) qs"
    and "\<forall>k. sum_list (map (\<lambda>q. q k) qs) + s k = v k"
    by simp_all
qed
(* GATE:END *)

end
