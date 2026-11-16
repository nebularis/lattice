(* SPDX-License-Identifier: MPL-2.0 *)

(* Rounding over whole minor units on the target kernel (plan ledger, LG-9, restating LG-7's and
   LG-8's claims): floor division leaves a shortfall below the number of parts, the units short
   placed by a declared order make the parts sum exactly, to the first in the order and to the
   largest remainders with ties in the order, both rules rationing with no residual, the same in
   every order the requests arrive in, each part within one unit of its exact share, and an amount
   allocated across accounts in whole units taking from each account what the exact allocation
   takes. Hand-written on the Kernel extracted from ontology/ledger/README.md section 10. *)

theory Rounding
imports Draws "HOL-Library.Multiset"
begin

section \<open>Examples, before any theorem\<close>

text \<open>Rationing 7 units among requests of 6, 4 and 2. The floor parts are 3, 2 and 1, one unit is
  short, and the remainders are 6, 4 and 2 of 12. Largest remainder gives the unit to the first
  request. To the first in an order that puts the third request first gives it to the third.\<close>

value "map (ration (largest_remainder (first_in id)) {0::nat, 1, 2} (\<lambda>k. 6 - 2 * int k) 7) [0, 1, 2]"
value "map (ration (to_first (\<lambda>k. 2 - k)) {0::nat, 1, 2} (\<lambda>k. 6 - 2 * int k) 7) [0, 1, 2]"

lemma example_largest_remainder:
  "map (ration (largest_remainder (first_in id)) {0::nat, 1, 2} (\<lambda>k. 6 - 2 * int k) 7) [0, 1, 2] = [4, 2, 1]"
  by code_simp

lemma example_to_the_first_in_a_declared_order:
  "map (ration (to_first (\<lambda>k. 2 - k)) {0::nat, 1, 2} (\<lambda>k. 6 - 2 * int k) 7) [0, 1, 2] = [3, 2, 2]"
  by code_simp

text \<open>Apportioning 10 units by weights 3, 2 and 1, where the two rules differ. The floor parts are
  5, 3 and 1, one unit is short, and the remainders are 0, 2 and 4. To the first in key order gives
  the unit to key 0, so 6, 3 and 1, and largest remainder gives it to key 2, so 5, 3 and 2.\<close>

value "(map (apportion (to_first id) {0::nat, 1, 2} (\<lambda>k. 3 - int k) 10) [0, 1, 2],
        map (apportion (largest_remainder (first_in id)) {0::nat, 1, 2} (\<lambda>k. 3 - int k) 10) [0, 1, 2])"

lemma example_the_two_rules_differ:
  "map (apportion (to_first id) {0::nat, 1, 2} (\<lambda>k. 3 - int k) 10) [0, 1, 2] = [6, 3, 1]
   \<and> map (apportion (largest_remainder (first_in id)) {0::nat, 1, 2} (\<lambda>k. 3 - int k) 10) [0, 1, 2] = [5, 3, 2]"
  by code_simp

text \<open>The instance that put LG-8's hypothesis of positive weights on to the first in order, now
  told apart by the kind of split. One unit by weights 0, 3 and 3 floors to nothing. Apportioned,
  every key may take a unit and key 0, first in the order, takes it although its weight is zero.
  Rationed, a unit goes only to a request not yet met, so key 1 takes it.\<close>

lemma example_a_key_of_no_weight:
  "apportion (to_first id) {0::nat, 1, 2} (\<lambda>k. if k = 0 then 0 else 3) 1 0 = 1
   \<and> map (ration (to_first id) {0::nat, 1, 2} (\<lambda>k. if k = 0 then 0 else 3) 1) [0, 1, 2] = [0, 1, 0]"
  by code_simp


section \<open>Floor division and what it leaves short\<close>

lemma sum_floor_part:
  "(\<Sum>k\<in>K. floor_part t K w k) = (\<Sum>k\<in>K. (t * w k) div (\<Sum>j\<in>K. w j))"
  by (intro sum.cong) (simp_all add: floor_part_def)

lemma short_scaled:
  "(\<Sum>j\<in>K. w j) * short t K (floor_part t K w) = (\<Sum>k\<in>K. remainder t K w k)"
proof -
  let ?W = "\<Sum>j\<in>K. w j"
  have "(\<Sum>k\<in>K. remainder t K w k) = (\<Sum>k\<in>K. t * w k - ?W * ((t * w k) div ?W))"
    by (intro sum.cong) (simp_all add: remainder_def minus_mult_div_eq_mod)
  also have "\<dots> = (\<Sum>k\<in>K. t * w k) - (\<Sum>k\<in>K. ?W * ((t * w k) div ?W))"
    by (simp add: sum_subtractf)
  also have "\<dots> = t * ?W - ?W * (\<Sum>k\<in>K. (t * w k) div ?W)"
    by (simp add: sum_distrib_left)
  also have "\<dots> = ?W * short t K (floor_part t K w)"
    by (simp add: short_def sum_floor_part right_diff_distrib mult.commute)
  finally show ?thesis by simp
qed

lemma remainder_nonneg: "0 < (\<Sum>j\<in>K. w j) \<Longrightarrow> 0 \<le> remainder t K w k"
  by (simp add: remainder_def)

lemma remainder_bound: "0 < (\<Sum>j\<in>K. w j) \<Longrightarrow> remainder t K w k \<le> (\<Sum>j\<in>K. w j) - 1"
  using pos_mod_bound[of "\<Sum>j\<in>K. w j" "t * w k"] by (simp add: remainder_def)

(* GATE:BEGIN LR1 *)
theorem floor_split_conserves:
  assumes fin: "finite K" and W: "0 < (\<Sum>k\<in>K. w k)"
  shows "(\<Sum>k\<in>K. floor_part t K w k) + short t K (floor_part t K w) = t"
    and "0 \<le> short t K (floor_part t K w) \<and> short t K (floor_part t K w) < int (card K)"
proof -
  show "(\<Sum>k\<in>K. floor_part t K w k) + short t K (floor_part t K w) = t"
    by (simp add: short_def)
  let ?W = "\<Sum>k\<in>K. w k"
  let ?n = "short t K (floor_part t K w)"
  have scaled: "?W * ?n = (\<Sum>k\<in>K. remainder t K w k)" by (rule short_scaled)
  have lo: "0 \<le> (\<Sum>k\<in>K. remainder t K w k)"
    using W by (intro sum_nonneg) (simp add: remainder_def)
  have hi: "(\<Sum>k\<in>K. remainder t K w k) \<le> of_nat (card K) * (?W - 1)"
    by (rule sum_bounded_above) (rule remainder_bound[OF W])
  have "K \<noteq> {}" using W by auto
  then have cpos: "0 < card K" using fin by (simp add: card_gt_0_iff)
  have "0 \<le> ?W * ?n" using scaled lo by simp
  then have l0: "0 \<le> ?n" using W by (simp add: zero_le_mult_iff)
  have l1: "?n < int (card K)"
  proof (rule ccontr)
    assume "\<not> ?n < int (card K)"
    then have "int (card K) \<le> ?n" by simp
    then have "?W * int (card K) \<le> ?W * ?n" using W by (simp add: mult_left_mono)
    with scaled hi have "?W * int (card K) \<le> int (card K) * (?W - 1)" by simp
    then have "int (card K) \<le> 0" by (simp add: algebra_simps)
    with cpos show False by simp
  qed
  show "0 \<le> ?n \<and> ?n < int (card K)" using l0 l1 by simp
qed
(* GATE:END *)

lemma floor_part_mod:
  "k \<in> K \<Longrightarrow> floor_part t K w k * (\<Sum>j\<in>K. w j) + remainder t K w k = t * w k"
  using div_mult_mod_eq[of "t * w k" "\<Sum>j\<in>K. w j"] by (simp add: floor_part_def remainder_def)

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


section \<open>Placing the units a preference decides\<close>

text \<open>A preference that is a strict total order on a set of keys places exactly n of them among
  the first n, for every n from zero to their number.\<close>

definition strict_order_on :: "'k set \<Rightarrow> ('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> bool" where
  "strict_order_on E pref \<longleftrightarrow>
     (\<forall>k\<in>E. \<not> pref k k) \<and> (\<forall>i\<in>E. \<forall>j\<in>E. \<forall>k\<in>E. pref i j \<longrightarrow> pref j k \<longrightarrow> pref i k)
     \<and> (\<forall>j\<in>E. \<forall>k\<in>E. j \<noteq> k \<longrightarrow> pref j k \<or> pref k j)"

lemma placed_empty [simp]: "\<not> placed {} pref n k"
  by (simp add: placed_def)

lemma placed_in: "placed E pref n k \<Longrightarrow> k \<in> E"
  by (simp add: placed_def)

lemma one_le_card_filter: "finite E \<Longrightarrow> k \<in> E \<Longrightarrow> P k \<Longrightarrow> 1 \<le> card {j\<in>E. P j}"
proof -
  assume fin: "finite E" and k: "k \<in> E" "P k"
  have "finite {j\<in>E. P j}" using fin by simp
  moreover have "{j\<in>E. P j} \<noteq> {}" using k by blast
  ultimately have "0 < card {j\<in>E. P j}" by (simp add: card_gt_0_iff)
  then show ?thesis by linarith
qed

lemma strict_order_trans:
  "strict_order_on E pref \<Longrightarrow> i \<in> E \<Longrightarrow> j \<in> E \<Longrightarrow> k \<in> E \<Longrightarrow> pref i j \<Longrightarrow> pref j k \<Longrightarrow> pref i k"
  unfolding strict_order_on_def by blast

lemma strict_order_irr: "strict_order_on E pref \<Longrightarrow> k \<in> E \<Longrightarrow> \<not> pref k k"
  unfolding strict_order_on_def by simp

lemma strict_order_tot:
  "strict_order_on E pref \<Longrightarrow> j \<in> E \<Longrightarrow> k \<in> E \<Longrightarrow> j \<noteq> k \<Longrightarrow> pref j k \<or> pref k j"
  unfolding strict_order_on_def by simp

lemma strict_order_shorter:
  assumes so: "strict_order_on E pref" and j: "j \<in> E" and k: "k \<in> E" and jk: "pref j k"
  shows "{i\<in>E. \<not> pref j i} \<subseteq> {i\<in>E. \<not> pref k i}"
proof
  fix i
  assume "i \<in> {i\<in>E. \<not> pref j i}"
  then have i: "i \<in> E" and ji: "\<not> pref j i" by simp_all
  have "\<not> pref k i"
  proof
    assume "pref k i"
    then have "pref j i" using strict_order_trans[OF so j k i jk] by simp
    then show False using ji by simp
  qed
  then show "i \<in> {i\<in>E. \<not> pref k i}" using i by simp
qed

lemma placed_count:
  assumes fin: "finite E" and so: "strict_order_on E pref" and n0: "0 \<le> n" and nE: "n \<le> int (card E)"
  shows "card {k\<in>E. placed E pref n k} = nat n"
proof -
  define r where "r k = card {j\<in>E. \<not> pref k j}" for k
  have lo: "1 \<le> r k" if "k \<in> E" for k
    unfolding r_def using one_le_card_filter[OF fin that] strict_order_irr[OF so that] by simp
  have hi: "r k \<le> card E" for k
    unfolding r_def using fin by (intro card_mono) auto
  have lt: "r j < r k" if j: "j \<in> E" and k: "k \<in> E" and jk: "pref j k" for j k
  proof -
    have "{i\<in>E. \<not> pref j i} \<subset> {i\<in>E. \<not> pref k i}"
    proof
      show "{i\<in>E. \<not> pref j i} \<subseteq> {i\<in>E. \<not> pref k i}"
        by (rule strict_order_shorter[OF so j k jk])
      have "k \<in> {i\<in>E. \<not> pref k i}" using k strict_order_irr[OF so k] by simp
      moreover have "k \<notin> {i\<in>E. \<not> pref j i}" using jk by simp
      ultimately show "{i\<in>E. \<not> pref j i} \<noteq> {i\<in>E. \<not> pref k i}" by blast
    qed
    then show ?thesis unfolding r_def using fin by (intro psubset_card_mono) auto
  qed
  have inj: "inj_on r E"
  proof (rule inj_onI)
    fix j k
    assume j: "j \<in> E" and k: "k \<in> E" and eq: "r j = r k"
    show "j = k"
    proof (rule ccontr)
      assume "j \<noteq> k"
      then have "pref j k \<or> pref k j" by (rule strict_order_tot[OF so j k])
      then show False using lt[OF j k] lt[OF k j] eq by auto
    qed
  qed
  have img: "r ` E = {1..card E}"
  proof (rule card_subset_eq)
    show "finite {1..card E}" by simp
    show "r ` E \<subseteq> {1..card E}" using lo hi by auto
    show "card (r ` E) = card {1..card E}" using card_image[OF inj] by simp
  qed
  have set: "{k\<in>E. placed E pref n k} = {k\<in>E. r k \<le> nat n}"
    using n0 by (auto simp: placed_def r_def)
  have "card {k\<in>E. r k \<le> nat n} = card (r ` {k\<in>E. r k \<le> nat n})"
    by (rule card_image[symmetric]) (rule inj_on_subset[OF inj], auto)
  also have "r ` {k\<in>E. r k \<le> nat n} = {i \<in> r ` E. i \<le> nat n}" by auto
  also have "\<dots> = {1..nat n}" using img nE by auto
  finally show ?thesis using set by simp
qed

lemma placed_mono:
  assumes so: "strict_order_on E pref" and fin: "finite E"
      and j: "j \<in> E" and jk: "pref j k" and k: "placed E pref n k"
  shows "placed E pref n j"
proof -
  have kE: "k \<in> E" using k by (rule placed_in)
  have "{i\<in>E. \<not> pref j i} \<subseteq> {i\<in>E. \<not> pref k i}" by (rule strict_order_shorter[OF so j kE jk])
  then have "card {i\<in>E. \<not> pref j i} \<le> card {i\<in>E. \<not> pref k i}" using fin by (intro card_mono) auto
  then show ?thesis using k j by (simp add: placed_def)
qed

lemma placed_before:
  assumes so: "strict_order_on E pref" and fin: "finite E" and k: "placed E pref n k"
  shows "int (card {j\<in>E. pref j k}) \<le> n - 1"
proof -
  have kE: "k \<in> E" using k by (rule placed_in)
  have sub: "{j\<in>E. pref j k} \<subseteq> {i\<in>E. \<not> pref k i} - {k}"
  proof
    fix j
    assume "j \<in> {j\<in>E. pref j k}"
    then have j: "j \<in> E" and jk: "pref j k" by simp_all
    have "\<not> pref k j"
    proof
      assume "pref k j"
      then have "pref j j" using strict_order_trans[OF so j kE j jk] by simp
      then show False using strict_order_irr[OF so j] by simp
    qed
    moreover have "j \<noteq> k" using strict_order_irr[OF so kE] jk by blast
    ultimately show "j \<in> {i\<in>E. \<not> pref k i} - {k}" using j by simp
  qed
  have kin: "k \<in> {i\<in>E. \<not> pref k i}" using kE strict_order_irr[OF so kE] by simp
  have "card {j\<in>E. pref j k} \<le> card ({i\<in>E. \<not> pref k i} - {k})" using fin by (intro card_mono[OF _ sub]) simp
  also have "\<dots> = card {i\<in>E. \<not> pref k i} - 1" using kin fin by (simp add: card_Diff_singleton)
  finally have "card {j\<in>E. pref j k} \<le> card {i\<in>E. \<not> pref k i} - 1" .
  moreover have "1 \<le> card {i\<in>E. \<not> pref k i}"
    using one_le_card_filter[OF fin kE] strict_order_irr[OF so kE] by simp
  moreover have "int (card {i\<in>E. \<not> pref k i}) \<le> n" using k by (simp add: placed_def)
  ultimately show ?thesis by linarith
qed

lemma first_in_strict:
  assumes inj: "inj_on order E"
  shows "strict_order_on E (first_in order)"
  unfolding strict_order_on_def first_in_def
proof (intro conjI ballI impI)
  fix k
  show "\<not> order k < order k" by simp
next
  fix i j k
  assume "order i < order j" "order j < order k"
  then show "order i < order k" by simp
next
  fix j k
  assume j: "j \<in> E" and k: "k \<in> E" and jk: "j \<noteq> k"
  have "order j \<noteq> order k" using inj j k jk by (auto simp: inj_on_def)
  then show "order j < order k \<or> order k < order j" by linarith
qed

lemma then_by_strict:
  assumes inj: "inj_on order E"
  shows "strict_order_on E (then_by (larger_remainder t K w) (first_in order))"
  unfolding strict_order_on_def
proof (intro conjI ballI impI)
  fix k
  show "\<not> then_by (larger_remainder t K w) (first_in order) k k"
    by (simp add: then_by_def larger_remainder_def first_in_def)
next
  fix i j k
  assume "then_by (larger_remainder t K w) (first_in order) i j" "then_by (larger_remainder t K w) (first_in order) j k"
  then show "then_by (larger_remainder t K w) (first_in order) i k"
    by (auto simp: then_by_def larger_remainder_def first_in_def)
next
  fix j k
  assume j: "j \<in> E" and k: "k \<in> E" and jk: "j \<noteq> k"
  show "then_by (larger_remainder t K w) (first_in order) j k \<or> then_by (larger_remainder t K w) (first_in order) k j"
  proof (cases "remainder t K w j = remainder t K w k")
    case True
    have "order j \<noteq> order k" using inj j k jk by (auto simp: inj_on_def)
    then have "order j < order k \<or> order k < order j" by linarith
    then show ?thesis using True by (auto simp: then_by_def larger_remainder_def first_in_def)
  next
    case False
    then have "remainder t K w j < remainder t K w k \<or> remainder t K w k < remainder t K w j" by linarith
    then show ?thesis by (auto simp: then_by_def larger_remainder_def first_in_def)
  qed
qed


section \<open>The floor parts with the units short placed, under rationing\<close>

lemma unmet_sub: "unmet t K w \<subseteq> K"
  by (auto simp: unmet_def)

lemma weights_sum_pos:
  "nonneg_on K v \<Longrightarrow> (\<Sum>j\<in>K. v j) \<noteq> 0 \<Longrightarrow> 0 < (\<Sum>j\<in>K. v j)"
  using sum_nonneg[of K v] by (force simp: nonneg_on_def)

lemma met_remainder_zero:
  assumes nn: "nonneg_on K v" and xv: "x \<le> total K v" and W: "0 < (\<Sum>j\<in>K. v j)"
      and k: "k \<in> K" and met: "k \<notin> unmet x K v"
  shows "remainder x K v k = 0"
proof -
  have vk: "0 \<le> v k" using nn by (simp add: nonneg_on_def)
  have le: "floor_part x K v k \<le> v k" using floor_part_le_weight[OF W _ vk] xv by (simp add: total_def)
  have ge: "v k \<le> floor_part x K v k" using met k by (simp add: unmet_def not_less)
  have eq: "floor_part x K v k = v k" using le ge by simp
  have m: "v k * (\<Sum>j\<in>K. v j) + remainder x K v k = x * v k" using floor_part_mod[OF k, of x v] eq by simp
  have "(x - (\<Sum>j\<in>K. v j)) * v k \<le> 0" using xv vk by (intro mult_nonpos_nonneg) (simp_all add: total_def)
  then have "remainder x K v k \<le> 0" using m by (simp add: algebra_simps)
  then show ?thesis using remainder_nonneg[OF W, of x k] by simp
qed

lemma short_within_unmet:
  assumes fin: "finite K" and nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
  shows "0 \<le> short x K (floor_part x K v) \<and> short x K (floor_part x K v) \<le> int (card (unmet x K v))"
proof (cases "(\<Sum>j\<in>K. v j) = 0")
  case True
  then have "x = 0" using x0 xv by (simp add: total_def)
  then show ?thesis by (simp add: short_def floor_part_def)
next
  case False
  then have W: "0 < (\<Sum>j\<in>K. v j)" using weights_sum_pos[OF nn] by blast
  let ?W = "\<Sum>j\<in>K. v j"
  let ?n = "short x K (floor_part x K v)"
  let ?E = "unmet x K v"
  have n0: "0 \<le> ?n" using floor_split_conserves(2)[OF fin W] by simp
  have "?W * ?n = (\<Sum>k\<in>K. remainder x K v k)" by (rule short_scaled)
  also have "\<dots> = (\<Sum>k\<in>?E. remainder x K v k)"
  proof (rule sum.mono_neutral_right[OF fin unmet_sub])
    show "\<forall>i\<in>K - ?E. remainder x K v i = 0" using met_remainder_zero[OF nn xv W] by blast
  qed
  also have "\<dots> \<le> of_nat (card ?E) * (?W - 1)"
    by (rule sum_bounded_above) (rule remainder_bound[OF W])
  finally have b: "?W * ?n \<le> int (card ?E) * (?W - 1)" by simp
  have "?n \<le> int (card ?E)"
  proof (rule ccontr)
    assume "\<not> ?n \<le> int (card ?E)"
    then have "int (card ?E) + 1 \<le> ?n" by linarith
    then have "?W * (int (card ?E) + 1) \<le> ?W * ?n" using W by (simp add: mult_left_mono)
    with b have "?W * (int (card ?E) + 1) \<le> int (card ?E) * (?W - 1)" by linarith
    then have "?W + int (card ?E) \<le> 0" by (simp add: algebra_simps)
    then show False using W by simp
  qed
  then show ?thesis using n0 by simp
qed

lemma units_unfold:
  "units base n E pref {} no_order k = base k + (if 0 < n \<and> placed E pref n k then 1 else 0)"
  by (simp add: units_def)

lemma floor_units_total:
  assumes fin: "finite K" and nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
      and so: "strict_order_on (unmet x K v) pref"
  shows "total K (units (floor_part x K v) (short x K (floor_part x K v)) (unmet x K v) pref {} no_order) = x"
proof -
  define F where "F = floor_part x K v"
  define n where "n = short x K F"
  define E where "E = unmet x K v"
  have finE: "finite E" using fin unmet_sub[of x K v] by (simp add: E_def finite_subset)
  have nE: "0 \<le> n \<and> n \<le> int (card E)" using short_within_unmet[OF fin nn x0 xv] by (simp add: n_def F_def E_def)
  have soE: "strict_order_on E pref" using so by (simp add: E_def)
  have cnt: "(\<Sum>k\<in>K. if 0 < n \<and> placed E pref n k then 1 else 0) = (n::int)"
  proof (cases "0 < n")
    case True
    have "(\<Sum>k\<in>K. if 0 < n \<and> placed E pref n k then 1 else 0) = (\<Sum>k\<in>K. if placed E pref n k then 1 else (0::int))"
      using True by simp
    also have "\<dots> = int (card (K \<inter> {k. placed E pref n k}))"
      using fin by (simp add: sum.If_cases)
    also have "K \<inter> {k. placed E pref n k} = {k\<in>E. placed E pref n k}"
      using unmet_sub[of x K v] placed_in[of E pref n] by (auto simp: E_def)
    also have "card {k\<in>E. placed E pref n k} = nat n" using placed_count[OF finE soE] nE by simp
    finally show ?thesis using nE by simp
  next
    case False
    then show ?thesis using nE by simp
  qed
  have "total K (units F n E pref {} no_order) = (\<Sum>k\<in>K. F k) + (\<Sum>k\<in>K. if 0 < n \<and> placed E pref n k then 1 else 0)"
    by (simp add: total_def units_unfold sum.distrib)
  also have "\<dots> = x" using cnt by (simp add: n_def short_def)
  finally show ?thesis by (simp add: F_def n_def E_def)
qed

lemma floor_part_nonneg:
  assumes nn: "nonneg_on K v" and x0: "0 \<le> x"
  shows "0 \<le> floor_part x K v k"
proof (cases "(\<Sum>j\<in>K. v j) = 0")
  case True
  then show ?thesis by (simp add: floor_part_def)
next
  case False
  then have W: "0 < (\<Sum>j\<in>K. v j)" using weights_sum_pos[OF nn] by blast
  have "0 \<le> x * v k" using nn x0 by (simp add: nonneg_on_def)
  then show ?thesis using W by (simp add: floor_part_def pos_imp_zdiv_nonneg_iff)
qed

lemma floor_part_within:
  assumes nn: "nonneg_on K v" and xv: "x \<le> total K v"
  shows "floor_part x K v k \<le> v k"
proof (cases "(\<Sum>j\<in>K. v j) = 0")
  case True
  then show ?thesis using nn by (simp add: floor_part_def nonneg_on_def)
next
  case False
  then have W: "0 < (\<Sum>j\<in>K. v j)" using weights_sum_pos[OF nn] by blast
  show ?thesis using floor_part_le_weight[OF W _, of x k] xv nn by (simp add: total_def nonneg_on_def)
qed

lemma floor_units_bounds:
  assumes nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
  shows "nonneg_on K (units (floor_part x K v) (short x K (floor_part x K v)) (unmet x K v) pref {} no_order)
         \<and> fits_in (units (floor_part x K v) (short x K (floor_part x K v)) (unmet x K v) pref {} no_order) v"
proof -
  let ?n = "short x K (floor_part x K v)"
  let ?G = "units (floor_part x K v) ?n (unmet x K v) pref {} no_order"
  have unit: "floor_part x K v k + 1 \<le> v k" if "placed (unmet x K v) pref ?n k" for k
    using placed_in[OF that] by (simp add: unmet_def)
  have lo: "0 \<le> ?G k" for k using floor_part_nonneg[OF nn x0, of k] by (simp add: units_unfold)
  have off: "?G k = 0" if "k \<notin> K" for k
    using that placed_in[of "unmet x K v" pref ?n k] unmet_sub[of x K v] by (auto simp: units_unfold floor_part_def)
  have hi: "?G k \<le> v k" for k
    using floor_part_within[OF nn xv, of k] unit[of k] by (auto simp: units_unfold)
  show ?thesis using lo off hi by (simp add: nonneg_on_def fits_in_def)
qed

lemma floor_units_whole:
  assumes fin: "finite K" and nn: "nonneg_on K v"
  shows "units (floor_part (total K v) K v) (short (total K v) K (floor_part (total K v) K v)) (unmet (total K v) K v) pref {} no_order = v"
proof -
  have F: "floor_part (total K v) K v k = v k" for k
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
  have "short (total K v) K (floor_part (total K v) K v) = 0" unfolding short_def F by (simp add: total_def)
  then show ?thesis by (simp add: fun_eq_iff units_unfold F)
qed

lemma ration_to_first_units:
  "ration (to_first order) K v x = units (floor_part x K v) (short x K (floor_part x K v)) (unmet x K v) (first_in order) {} no_order"
  by (simp add: ration_def to_first_def)

lemma ration_largest_remainder_units:
  "ration (largest_remainder tb) K v x
     = units (floor_part x K v) (short x K (floor_part x K v)) (unmet x K v) (then_by (larger_remainder x K v) tb) {} no_order"
  by (simp add: ration_def largest_remainder_def)

lemma ration_the_same_in_every_order:
  assumes "mset ps = mset ps'"
  shows "ration U (proposers ps) (requested ps) = ration U (proposers ps') (requested ps')"
  using requested_mset[OF assms] proposers_reordered[OF mset_eq_setD[OF assms]] by simp


section \<open>To the first in a declared order\<close>

(* GATE:BEGIN LR2 *)
theorem ration_to_first_sums_exactly:
  assumes fin: "finite K" and inj: "inj_on order K"
      and nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
  shows "total K (ration (to_first order) K v x) = x"
proof -
  have "strict_order_on (unmet x K v) (first_in order)"
    using first_in_strict inj_on_subset[OF inj unmet_sub] by blast
  then show ?thesis unfolding ration_to_first_units by (rule floor_units_total[OF fin nn x0 xv])
qed

theorem ration_to_first_the_same_in_every_order:
  assumes "mset ps = mset ps'"
  shows "ration (to_first order) (proposers ps) (requested ps) = ration (to_first order) (proposers ps') (requested ps')"
  by (rule ration_the_same_in_every_order[OF assms])
(* GATE:END *)


section \<open>Largest remainder, ties in a declared order\<close>

lemma placed_remainder_positive:
  assumes fin: "finite K" and inj: "inj_on order K"
      and nn: "nonneg_on K v" and xv: "x \<le> total K v" and W: "0 < (\<Sum>j\<in>K. v j)"
      and pl: "placed (unmet x K v) (then_by (larger_remainder x K v) (first_in order)) (short x K (floor_part x K v)) k"
  shows "0 < remainder x K v k"
proof (rule ccontr)
  let ?W = "\<Sum>j\<in>K. v j"
  let ?n = "short x K (floor_part x K v)"
  let ?E = "unmet x K v"
  let ?p = "then_by (larger_remainder x K v) (first_in order)"
  assume "\<not> 0 < remainder x K v k"
  then have r0: "remainder x K v k = 0" using remainder_nonneg[OF W, of x k] by simp
  have finE: "finite ?E" using fin unmet_sub[of x K v] by (simp add: finite_subset)
  have so: "strict_order_on ?E ?p" using then_by_strict inj_on_subset[OF inj unmet_sub] by blast
  define P where "P = {j\<in>K. 0 < remainder x K v j}"
  have PE: "P \<subseteq> {j\<in>?E. ?p j k}"
  proof
    fix j
    assume "j \<in> P"
    then have jK: "j \<in> K" and jpos: "0 < remainder x K v j" by (simp_all add: P_def)
    have "j \<in> ?E" using met_remainder_zero[OF nn xv W jK] jpos by auto
    moreover have "?p j k" using jpos r0 by (simp add: then_by_def larger_remainder_def)
    ultimately show "j \<in> {j\<in>?E. ?p j k}" by simp
  qed
  have "card P \<le> card {j\<in>?E. ?p j k}" using finE by (intro card_mono[OF _ PE]) simp
  then have cP: "int (card P) \<le> ?n - 1" using placed_before[OF so finE pl] by linarith
  have "1 \<le> ?n"
  proof -
    have "k \<in> ?E" using pl by (rule placed_in)
    then have "1 \<le> card {j\<in>?E. \<not> ?p k j}"
      using one_le_card_filter[OF finE] by (simp add: then_by_def larger_remainder_def first_in_def)
    then show ?thesis using pl by (simp add: placed_def)
  qed
  have "?W * ?n = (\<Sum>j\<in>K. remainder x K v j)" by (rule short_scaled)
  also have "\<dots> = (\<Sum>j\<in>P. remainder x K v j)"
  proof (rule sum.mono_neutral_right[OF fin])
    show "P \<subseteq> K" by (auto simp: P_def)
    show "\<forall>i\<in>K - P. remainder x K v i = 0"
    proof
      fix i
      assume "i \<in> K - P"
      then have "\<not> 0 < remainder x K v i" by (simp add: P_def)
      then show "remainder x K v i = 0" using remainder_nonneg[OF W, of x i] by simp
    qed
  qed
  also have "\<dots> \<le> of_nat (card P) * (?W - 1)"
    by (rule sum_bounded_above) (rule remainder_bound[OF W])
  also have "\<dots> \<le> (?n - 1) * (?W - 1)"
    using cP W by (intro mult_right_mono) simp_all
  finally have "?W * ?n \<le> (?n - 1) * (?W - 1)" .
  then have "?W + ?n \<le> 1" by (simp add: algebra_simps)
  then show False using W \<open>1 \<le> ?n\<close> by simp
qed

(* GATE:BEGIN LR3 *)
theorem ration_largest_remainder_sums_exactly:
  assumes fin: "finite K" and inj: "inj_on order K"
      and nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
  shows "total K (ration (largest_remainder (first_in order)) K v x) = x"
proof -
  have "strict_order_on (unmet x K v) (then_by (larger_remainder x K v) (first_in order))"
    using then_by_strict inj_on_subset[OF inj unmet_sub] by blast
  then show ?thesis unfolding ration_largest_remainder_units by (rule floor_units_total[OF fin nn x0 xv])
qed

theorem ration_largest_remainder_takes_the_largest:
  assumes fin: "finite K" and inj: "inj_on order K"
      and nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v" and j: "j \<in> K"
      and k_reached: "ration (largest_remainder (first_in order)) K v x k = floor_part x K v k + 1"
      and j_not: "ration (largest_remainder (first_in order)) K v x j = floor_part x K v j"
  shows "remainder x K v j \<le> remainder x K v k"
proof -
  let ?n = "short x K (floor_part x K v)"
  let ?E = "unmet x K v"
  let ?p = "then_by (larger_remainder x K v) (first_in order)"
  have kp: "0 < ?n \<and> placed ?E ?p ?n k"
    using k_reached by (simp add: ration_largest_remainder_units units_unfold split: if_splits)
  have jn: "\<not> placed ?E ?p ?n j"
    using j_not kp by (simp add: ration_largest_remainder_units units_unfold split: if_splits)
  have W: "0 < (\<Sum>j\<in>K. v j)"
  proof (rule ccontr)
    assume "\<not> 0 < (\<Sum>j\<in>K. v j)"
    then have "(\<Sum>j\<in>K. v j) = 0" using sum_nonneg[of K v] nn by (force simp: nonneg_on_def)
    then have "?n = x" by (simp add: short_def floor_part_def)
    moreover have "x = 0" using x0 xv \<open>(\<Sum>j\<in>K. v j) = 0\<close> by (simp add: total_def)
    ultimately show False using kp by simp
  qed
  show ?thesis
  proof (cases "j \<in> ?E")
    case True
    have finE: "finite ?E" using fin unmet_sub[of x K v] by (simp add: finite_subset)
    have so: "strict_order_on ?E ?p" using then_by_strict inj_on_subset[OF inj unmet_sub] by blast
    have "\<not> ?p j k" using placed_mono[OF so finE True _ conjunct2[OF kp]] jn by blast
    then show ?thesis by (simp add: then_by_def larger_remainder_def)
  next
    case False
    then have "remainder x K v j = 0" by (rule met_remainder_zero[OF nn xv W j])
    then show ?thesis using remainder_nonneg[OF W, of x k] by simp
  qed
qed

theorem ration_largest_remainder_the_same_in_every_order:
  assumes "mset ps = mset ps'"
  shows "ration (largest_remainder (first_in order)) (proposers ps) (requested ps)
         = ration (largest_remainder (first_in order)) (proposers ps') (requested ps')"
  by (rule ration_the_same_in_every_order[OF assms])
(* GATE:END *)


section \<open>Both rules ration with no residual\<close>

(* GATE:BEGIN LR4 *)
theorem ration_lawful:
  fixes K :: "'k set"
  assumes fin: "finite K" and inj: "inj_on order K"
  shows "lawful K (ration (to_first order) K)"
    and "lawful K (ration (largest_remainder (first_in order)) K)"
proof -
  show "lawful K (ration (to_first order) K)"
  proof (rule lawfulI)
    fix v :: "('k, int) amounts" and x :: int
    assume nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
    show "total K (ration (to_first order) K v x) = x \<and> fits_in (ration (to_first order) K v x) v
            \<and> nonneg_on K (ration (to_first order) K v x)"
      using ration_to_first_sums_exactly[OF fin inj nn x0 xv] floor_units_bounds[OF nn x0 xv]
      by (simp add: ration_to_first_units)
  next
    fix v :: "('k, int) amounts"
    assume nn: "nonneg_on K v"
    show "ration (to_first order) K v (total K v) = v"
      unfolding ration_to_first_units by (rule floor_units_whole[OF fin nn])
  qed
  show "lawful K (ration (largest_remainder (first_in order)) K)"
  proof (rule lawfulI)
    fix v :: "('k, int) amounts" and x :: int
    assume nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
    show "total K (ration (largest_remainder (first_in order)) K v x) = x
            \<and> fits_in (ration (largest_remainder (first_in order)) K v x) v
            \<and> nonneg_on K (ration (largest_remainder (first_in order)) K v x)"
      using ration_largest_remainder_sums_exactly[OF fin inj nn x0 xv] floor_units_bounds[OF nn x0 xv]
      by (simp add: ration_largest_remainder_units)
  next
    fix v :: "('k, int) amounts"
    assume nn: "nonneg_on K v"
    show "ration (largest_remainder (first_in order)) K v (total K v) = v"
      unfolding ration_largest_remainder_units by (rule floor_units_whole[OF fin nn])
  qed
qed
(* GATE:END *)


section \<open>The refinement beyond one part\<close>

text \<open>Each rounded part is within one minor unit of the exact share, strictly so under largest
  remainder, and an amount allocated across accounts in turn, rationed over whole units by largest
  remainder, takes from every account exactly what the exact allocation by any lawful rule takes,
  so rounding moves amounts between keys and never between accounts.\<close>

lemma least_of_int:
  assumes fin: "finite S" and ne: "S \<noteq> {}"
  shows "least (\<lambda>b. of_int (bal b) :: rat) S = of_int (least bal S)"
proof -
  have mono: "mono (of_int :: int \<Rightarrow> rat)" by (simp add: mono_def)
  have "(\<lambda>b. of_int (bal b) :: rat) ` S = of_int ` (bal ` S)" by (simp add: image_image)
  then show ?thesis unfolding least_def using mono_Min_commute[OF mono, of "bal ` S"] fin ne by simp
qed

lemma spread_refines:
  fixes Ri :: "('k, int) rule" and Rr :: "('k, rat) rule"
  assumes oki: "lawful K Ri" and okr: "lawful K Rr"
  shows "\<forall>a\<in>set as. finite (charged a) \<and> charged a \<noteq> {} \<Longrightarrow> nonneg_on K vi \<Longrightarrow> nonneg_on K vr
    \<Longrightarrow> total K vr = of_int (total K vi) \<Longrightarrow> (\<forall>b. balr b = of_int (bali b))
    \<Longrightarrow> spread K Rr charged as balr vr = (ps, r, balr')
    \<Longrightarrow> spread K Ri charged as bali vi = (qs, s, bali')
    \<Longrightarrow> (\<forall>b. balr' b = of_int (bali' b)) \<and> map (total K) ps = map (\<lambda>q. of_int (total K q)) qs"
proof (induction as arbitrary: balr vr bali vi ps r balr' qs s bali')
  case Nil
  then show ?case by auto
next
  case (Cons a rest)
  have ch: "finite (charged a)" "charged a \<noteq> {}" using Cons.prems(1) by simp_all
  have vinn: "nonneg_on K vi" and vrnn: "nonneg_on K vr" and tot: "total K vr = of_int (total K vi)"
    and bal: "\<forall>b. balr b = of_int (bali b)" using Cons.prems(2-5) by simp_all
  have balr: "balr = (\<lambda>b. of_int (bali b))" using bal by (simp add: fun_eq_iff)
  define xi where "xi = min (total K vi) (max 0 (least bali (charged a)))"
  define xr where "xr = min (total K vr) (max 0 (least balr (charged a)))"
  define pi where "pi = Ri vi xi"
  define pr where "pr = Rr vr xr"
  have xrxi: "xr = of_int xi"
    using least_of_int[OF ch, of bali] by (simp add: xr_def xi_def tot balr min_def max_def)
  have xi0: "0 \<le> xi" using total_nonneg[OF vinn] by (simp add: xi_def)
  have xiv: "xi \<le> total K vi" by (simp add: xi_def)
  have xr0: "0 \<le> xr" using xi0 by (simp add: xrxi)
  have xrv: "xr \<le> total K vr" by (simp add: xr_def)
  have pit: "total K pi = xi" unfolding pi_def by (rule lawful_exact[OF oki vinn xi0 xiv])
  have prt: "total K pr = xr" unfolding pr_def by (rule lawful_exact[OF okr vrnn xr0 xrv])
  obtain ps1 r1 balr2 where recr: "spread K Rr charged rest (debit (charged a) (total K pr) balr) (less vr pr) = (ps1, r1, balr2)"
    by (metis prod_cases3)
  obtain qs1 s1 bali2 where reci: "spread K Ri charged rest (debit (charged a) (total K pi) bali) (less vi pi) = (qs1, s1, bali2)"
    by (metis prod_cases3)
  have outr: "ps = pr # ps1" "balr' = balr2"
    using Cons.prems(6) recr by (simp_all add: xr_def pr_def Let_def)
  have outi: "qs = pi # qs1" "bali' = bali2"
    using Cons.prems(7) reci by (simp_all add: xi_def pi_def Let_def)
  have vr1nn: "nonneg_on K (less vr pr)"
    using nonneg_less[OF vrnn lawful_nonneg[OF okr vrnn xr0 xrv] lawful_fits_in[OF okr vrnn xr0 xrv]] by (simp add: pr_def)
  have vi1nn: "nonneg_on K (less vi pi)"
    using nonneg_less[OF vinn lawful_nonneg[OF oki vinn xi0 xiv] lawful_fits_in[OF oki vinn xi0 xiv]] by (simp add: pi_def)
  have tot1: "total K (less vr pr) = of_int (total K (less vi pi))"
    using tot prt pit xrxi by (simp add: total_less)
  have bal1: "\<forall>b. debit (charged a) (total K pr) balr b = of_int (debit (charged a) (total K pi) bali b)"
    using bal prt pit xrxi by (simp add: debit_def)
  have "\<forall>a\<in>set rest. finite (charged a) \<and> charged a \<noteq> {}" using Cons.prems(1) by simp
  then have IH: "(\<forall>b. balr2 b = of_int (bali2 b)) \<and> map (total K) ps1 = map (\<lambda>q. of_int (total K q)) qs1"
    using Cons.IH[OF _ vi1nn vr1nn tot1 bal1 recr reci] by blast
  show ?case using IH prt pit xrxi by (simp add: outr outi)
qed

(* GATE:BEGIN LR5 *)
theorem rounded_part_within_one_unit:
  assumes k: "k \<in> K" and W: "0 < (\<Sum>j\<in>K. v j)"
  shows "\<bar>of_int (ration (to_first order) K v x k) - of_int (x * v k) / of_int (\<Sum>j\<in>K. v j)\<bar> \<le> (1::rat)"
    and "finite K \<Longrightarrow> inj_on order K \<Longrightarrow> nonneg_on K v \<Longrightarrow> 0 \<le> x \<Longrightarrow> x \<le> total K v \<Longrightarrow>
           \<bar>of_int (ration (largest_remainder (first_in order)) K v x k) - of_int (x * v k) / of_int (\<Sum>j\<in>K. v j)\<bar> < (1::rat)"
proof -
  define q where "q = (of_int (x * v k) / of_int (\<Sum>j\<in>K. v j) :: rat)"
  define f where "f = (of_int (floor_part x K v k) :: rat)"
  have fq: "f \<le> q \<and> q < f + 1" using floor_part_refines[OF k W] by (simp add: q_def f_def)
  have "\<bar>of_int (ration (to_first order) K v x k) - q\<bar> \<le> 1"
  proof (cases "ration (to_first order) K v x k = floor_part x K v k")
    case True
    then have e: "(of_int (ration (to_first order) K v x k) :: rat) = f" by (simp add: f_def)
    show ?thesis using fq unfolding e abs_le_iff by linarith
  next
    case False
    then have "ration (to_first order) K v x k = floor_part x K v k + 1"
      by (simp add: ration_to_first_units units_unfold split: if_splits)
    then have e: "(of_int (ration (to_first order) K v x k) :: rat) = f + 1" by (simp add: f_def)
    show ?thesis using fq unfolding e abs_le_iff by linarith
  qed
  then show "\<bar>of_int (ration (to_first order) K v x k) - of_int (x * v k) / of_int (\<Sum>j\<in>K. v j)\<bar> \<le> (1::rat)"
    by (simp add: q_def)
next
  assume fin: "finite K" and inj: "inj_on order K" and nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
  define q where "q = (of_int (x * v k) / of_int (\<Sum>j\<in>K. v j) :: rat)"
  define f where "f = (of_int (floor_part x K v k) :: rat)"
  have fq: "f \<le> q \<and> q < f + 1" using floor_part_refines[OF k W] by (simp add: q_def f_def)
  let ?R = "ration (largest_remainder (first_in order)) K v x k"
  have "\<bar>of_int ?R - q\<bar> < 1"
  proof (cases "?R = floor_part x K v k")
    case True
    then have e: "(of_int ?R :: rat) = f" by (simp add: f_def)
    show ?thesis using fq unfolding e abs_less_iff by linarith
  next
    case False
    then have pl: "placed (unmet x K v) (then_by (larger_remainder x K v) (first_in order)) (short x K (floor_part x K v)) k"
      and plus: "?R = floor_part x K v k + 1"
      by (simp_all add: ration_largest_remainder_units units_unfold split: if_splits)
    have e: "(of_int ?R :: rat) = f + 1" using plus by (simp add: f_def)
    have rpos: "0 < remainder x K v k" by (rule placed_remainder_positive[OF fin inj nn xv W pl])
    have "floor_part x K v k * (\<Sum>j\<in>K. v j) < x * v k" using floor_part_mod[OF k, of x v] rpos by linarith
    then have prev: "(of_int (floor_part x K v k) :: rat) * of_int (\<Sum>j\<in>K. v j) < of_int (x * v k)"
      by (metis of_int_less_iff of_int_mult)
    have Wq: "(0::rat) < of_int (\<Sum>j\<in>K. v j)" by (subst of_int_0_less_iff) (rule W)
    have "f < q" unfolding q_def f_def by (subst pos_less_divide_eq[OF Wq]) (rule prev)
    then show ?thesis using fq unfolding e abs_less_iff by linarith
  qed
  then show "\<bar>of_int ?R - of_int (x * v k) / of_int (\<Sum>j\<in>K. v j)\<bar> < (1::rat)" by (simp add: q_def)
qed

theorem rounded_spread_takes_what_the_exact_takes:
  fixes K :: "'k set" and R :: "('k, rat) rule"
  assumes fin: "finite K" and inj: "inj_on order K" and ok: "lawful K R"
      and ch: "\<forall>a\<in>set as. finite (charged a) \<and> charged a \<noteq> {}"
      and nn: "nonneg_on K v"
      and sr: "spread K R charged as (\<lambda>b. of_int (bal b)) (\<lambda>k. of_int (v k)) = (ps, r, bal_r)"
      and si: "spread K (ration (largest_remainder (first_in order)) K) charged as bal v = (qs, s, bal_i)"
  shows "\<forall>b. bal_r b = of_int (bal_i b)"
    and "map (total K) ps = map (\<lambda>q. of_int (total K q)) qs"
    and "\<forall>k. sum_list (map (\<lambda>q. q k) qs) + s k = v k"
proof -
  have vrnn: "nonneg_on K (\<lambda>k. of_int (v k) :: rat)" using nn by (simp add: nonneg_on_def)
  have tot: "total K (\<lambda>k. of_int (v k) :: rat) = of_int (total K v)" by (simp add: total_def)
  have all: "(\<forall>b. bal_r b = of_int (bal_i b)) \<and> map (total K) ps = map (\<lambda>q. of_int (total K q)) qs"
    by (rule spread_refines[OF ration_lawful(2)[OF fin inj] ok ch nn vrnn tot _ sr si]) simp
  then show "\<forall>b. bal_r b = of_int (bal_i b)" and "map (total K) ps = map (\<lambda>q. of_int (total K q)) qs"
    by simp_all
  show "\<forall>k. sum_list (map (\<lambda>q. q k) qs) + s k = v k"
    using conservation_with_residual[OF si] by blast
qed
(* GATE:END *)

end
