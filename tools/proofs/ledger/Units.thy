(* SPDX-License-Identifier: MPL-2.0 *)

(* Whole units on the target kernel (plan ledger, LG-20, the third group): a strict total order
   places exactly the units asked, largest remainder with no order declared rations, treats equal
   requests equally and leaves less than one unit a key, and where the units short reach whole
   groups of equal remainders it needs no order. Two instances kept on purpose. Hand-written on
   the Kernel extracted from ontology/ledger/README.md section 10. *)

theory Units
imports Ranks
begin

section \<open>Examples, before any theorem\<close>

text \<open>Three requests of 5 share 10. With an order declared the first in it is granted 4 and the
  others 3, so equal requests are treated equally only with no order, which grants 3 each and
  leaves 1.\<close>

value "(map (ration (largest_remainder (first_in id)) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3],
        map (ration (largest_remainder no_order) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3])"

text \<open>Weights of 3, 0, 11 and 11 share 62, rounded half up to 7, 0, 27 and 27, which sum to 61.
  Given to the first in an order that puts the key of no weight first, among all the keys, the
  unit short goes to that key, a whole unit from its exact share of 0. Given as rounding to the
  nearest gives it, to a share rounded down with a remainder, it goes to the first such key.\<close>

definition three_none_eleven :: "nat \<Rightarrow> int" where
  "three_none_eleven k = (if k = 0 then 3 else if k = 1 then 0 else 11)"

definition none_first :: "nat \<Rightarrow> nat" where
  "none_first k = (if k = 1 then 0 else k + 1)"

value "(map (half_up_part 62 {0::nat, 1, 2, 3} three_none_eleven) [0, 1, 2, 3],
        map (units (half_up_part 62 {0::nat, 1, 2, 3} three_none_eleven)
                   (short 62 {0::nat, 1, 2, 3} (half_up_part 62 {0::nat, 1, 2, 3} three_none_eleven))
                   {0, 1, 2, 3} (first_in none_first) {} no_order) [0, 1, 2, 3],
        map (to_nearest half_up_part (first_in none_first) (first_in none_first) 62 {0::nat, 1, 2, 3} three_none_eleven) [0, 1, 2, 3])"


section \<open>A strict total order places exactly the units asked\<close>

(* GATE:BEGIN LW0 *)
theorem a_strict_total_order_places_exactly_n:
  assumes fin: "finite E" and so: "strict_order_on E pref" and n0: "0 \<le> n" and nE: "n \<le> int (card E)"
  shows "card {k\<in>E. placed E pref n k} = nat n"
  by (rule placed_count[OF fin so n0 nE])
(* GATE:END *)


section \<open>Largest remainder with no order declared\<close>

lemma units_count:
  assumes fin: "finite K" and sub: "E \<subseteq> K"
  shows "total K (units F n E pref {} no_order)
           = (\<Sum>k\<in>K. F k) + (if 0 < n then int (card {k\<in>E. placed E pref n k}) else 0)"
proof -
  have c: "(\<Sum>k\<in>K. if 0 < n \<and> placed E pref n k then 1 else 0)
             = (if 0 < n then int (card {k\<in>E. placed E pref n k}) else (0::int))"
  proof (cases "0 < n")
    case True
    have "(\<Sum>k\<in>K. if 0 < n \<and> placed E pref n k then 1 else 0) = (\<Sum>k\<in>K. if placed E pref n k then 1 else (0::int))"
      using True by simp
    also have "\<dots> = int (card (K \<inter> {k. placed E pref n k}))" using fin by (simp add: sum.If_cases)
    also have "K \<inter> {k. placed E pref n k} = {k\<in>E. placed E pref n k}" using sub placed_in[of E pref n] by auto
    finally show ?thesis using True by simp
  next
    case False
    then show ?thesis by simp
  qed
  show ?thesis using c by (simp add: total_def units_unfold sum.distrib)
qed

lemma then_by_no_order: "then_by p no_order = p"
  by (simp add: fun_eq_iff then_by_def no_order_def)

lemma placed_larger_remainder_le:
  assumes finE: "finite E" and n0: "0 \<le> n"
  shows "card {k\<in>E. placed E (larger_remainder t K w) n k} \<le> nat n"
proof (cases "{k\<in>E. placed E (larger_remainder t K w) n k} = {}")
  case True
  then have "card {k\<in>E. placed E (larger_remainder t K w) n k} = 0" by (simp only: card.empty)
  then show ?thesis by simp
next
  case False
  let ?P = "{k\<in>E. placed E (larger_remainder t K w) n k}"
  have finP: "finite (remainder t K w ` ?P)" using finE by simp
  have neP: "remainder t K w ` ?P \<noteq> {}" using False by simp
  from Min_in[OF finP neP] obtain k where k: "k \<in> ?P" and kmin: "Min (remainder t K w ` ?P) = remainder t K w k" by blast
  have sub: "?P \<subseteq> {j\<in>E. \<not> larger_remainder t K w k j}"
  proof
    fix j
    assume j: "j \<in> ?P"
    then have "Min (remainder t K w ` ?P) \<le> remainder t K w j" using finP by (intro Min_le) auto
    then have "\<not> remainder t K w j < remainder t K w k" using kmin by simp
    then show "j \<in> {j\<in>E. \<not> larger_remainder t K w k j}" using j by (simp add: larger_remainder_def)
  qed
  have "card ?P \<le> card {j\<in>E. \<not> larger_remainder t K w k j}" using finE by (intro card_mono[OF _ sub]) simp
  moreover have "int (card {j\<in>E. \<not> larger_remainder t K w k j}) \<le> n" using k by (simp add: placed_def)
  ultimately show ?thesis by linarith
qed

lemma ration_no_order_units:
  "ration (largest_remainder no_order) K v x
     = units (floor_part x K v) (short x K (floor_part x K v)) (unmet x K v) (larger_remainder x K v) {} no_order"
  by (simp add: ration_largest_remainder_units then_by_no_order)

lemma ration_no_order_total:
  assumes fin: "finite K" and nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
  shows "total K (ration (largest_remainder no_order) K v x)
           = x - short x K (floor_part x K v)
             + (if 0 < short x K (floor_part x K v)
                then int (card {k\<in>unmet x K v. placed (unmet x K v) (larger_remainder x K v) (short x K (floor_part x K v)) k})
                else 0)"
  unfolding ration_no_order_units units_count[OF fin unmet_sub] by (simp add: short_def)

(* GATE:BEGIN LW1 *)
theorem no_order_rations:
  fixes K :: "'k set"
  assumes fin: "finite K"
  shows "rations K (ration (largest_remainder no_order) K)"
  unfolding rations_def
proof (intro conjI allI impI)
  fix v :: "('k, int) amounts" and x :: int
  assume a: "nonneg_on K v \<and> 0 \<le> x \<and> x \<le> total K v"
  then have nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v" by simp_all
  have b: "nonneg_on K (ration (largest_remainder no_order) K v x) \<and> fits_in (ration (largest_remainder no_order) K v x) v"
    unfolding ration_no_order_units by (rule floor_units_bounds[OF nn x0 xv])
  have n0: "0 \<le> short x K (floor_part x K v)" using short_within_unmet[OF fin nn x0 xv] by simp
  have finE: "finite (unmet x K v)" using fin unmet_sub[of x K v] by (simp add: finite_subset)
  have c: "card {k\<in>unmet x K v. placed (unmet x K v) (larger_remainder x K v) (short x K (floor_part x K v)) k}
             \<le> nat (short x K (floor_part x K v))"
    by (rule placed_larger_remainder_le[OF finE n0])
  have "total K (ration (largest_remainder no_order) K v x) \<le> x"
    unfolding ration_no_order_total[OF fin nn x0 xv] using c n0 by auto
  then show "nonneg_on K (ration (largest_remainder no_order) K v x)"
    and "fits_in (ration (largest_remainder no_order) K v x) v"
    and "total K (ration (largest_remainder no_order) K v x) \<le> x" using b by simp_all
next
  fix v :: "('k, int) amounts"
  assume nn: "nonneg_on K v"
  show "ration (largest_remainder no_order) K v (total K v) = v"
    unfolding ration_no_order_units by (rule floor_units_whole[OF fin nn])
qed
(* GATE:END *)

(* GATE:BEGIN LW2 *)
theorem equal_requests_equal_grants:
  assumes j: "j \<in> K" and k: "k \<in> K" and eq: "v j = v k"
  shows "ration (largest_remainder no_order) K v x j = ration (largest_remainder no_order) K v x k"
proof -
  let ?E = "unmet x K v"
  let ?n = "short x K (floor_part x K v)"
  have F: "floor_part x K v j = floor_part x K v k" using j k eq by (simp add: floor_part_def)
  have r: "remainder x K v j = remainder x K v k" using eq by (simp add: remainder_def)
  have u: "j \<in> ?E \<longleftrightarrow> k \<in> ?E" using j k eq F by (simp add: unmet_def)
  have S: "{i\<in>?E. \<not> larger_remainder x K v j i} = {i\<in>?E. \<not> larger_remainder x K v k i}"
    using r by (simp add: larger_remainder_def)
  have pl: "placed ?E (larger_remainder x K v) ?n j \<longleftrightarrow> placed ?E (larger_remainder x K v) ?n k"
    using u S by (simp add: placed_def)
  show ?thesis unfolding ration_no_order_units units_unfold using F pl by simp
qed
(* GATE:END *)

(* GATE:BEGIN LW3 *)
theorem residual_below_the_number_of_keys:
  assumes fin: "finite K" and ne: "K \<noteq> {}" and nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
  shows "0 \<le> residual K (ration (largest_remainder no_order) K) v x
         \<and> residual K (ration (largest_remainder no_order) K) v x < int (card K)"
proof -
  let ?n = "short x K (floor_part x K v)"
  let ?c = "card {k\<in>unmet x K v. placed (unmet x K v) (larger_remainder x K v) ?n k}"
  have n0: "0 \<le> ?n" using short_within_unmet[OF fin nn x0 xv] by simp
  have finE: "finite (unmet x K v)" using fin unmet_sub[of x K v] by (simp add: finite_subset)
  have c: "?c \<le> nat ?n" by (rule placed_larger_remainder_le[OF finE n0])
  have res: "residual K (ration (largest_remainder no_order) K) v x = ?n - (if 0 < ?n then int ?c else 0)"
    unfolding residual_def ration_no_order_total[OF fin nn x0 xv] by simp
  have cpos: "0 < int (card K)" using fin ne by (simp add: card_gt_0_iff)
  have nlt: "?n < int (card K)"
  proof (cases "(\<Sum>j\<in>K. v j) = 0")
    case True
    then have "x = 0" using x0 xv by (simp add: total_def)
    then have "?n = 0" by (simp add: short_def floor_part_def)
    then show ?thesis using cpos by simp
  next
    case False
    then have W: "0 < (\<Sum>j\<in>K. v j)" using weights_sum_pos[OF nn] by blast
    show ?thesis using floor_split_conserves(2)[OF fin W] by simp
  qed
  show ?thesis using res c n0 nlt by auto
qed
(* GATE:END *)

(* GATE:BEGIN LW5 *)
theorem whole_groups_need_no_order:
  assumes fin: "finite K" and inj: "inj_on order K"
      and nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
      and groups: "card {k\<in>unmet x K v. placed (unmet x K v) (larger_remainder x K v) (short x K (floor_part x K v)) k}
                     = nat (short x K (floor_part x K v))"
  shows "ration (largest_remainder no_order) K v x = ration (largest_remainder (first_in order)) K v x"
    and "residual K (ration (largest_remainder no_order) K) v x = 0"
proof -
  let ?E = "unmet x K v"
  let ?n = "short x K (floor_part x K v)"
  let ?p = "larger_remainder x K v"
  let ?q = "then_by (larger_remainder x K v) (first_in order)"
  let ?P = "{k\<in>?E. placed ?E ?p ?n k}"
  let ?Q = "{k\<in>?E. placed ?E ?q ?n k}"
  have finE: "finite ?E" using fin unmet_sub[of x K v] by (simp add: finite_subset)
  have nE: "0 \<le> ?n \<and> ?n \<le> int (card ?E)" by (rule short_within_unmet[OF fin nn x0 xv])
  have so: "strict_order_on ?E ?q" using then_by_strict inj_on_subset[OF inj unmet_sub] by blast
  have sub: "?P \<subseteq> ?Q"
  proof
    fix k
    assume "k \<in> ?P"
    then have kE: "k \<in> ?E" and pk: "int (card {j\<in>?E. \<not> ?p k j}) \<le> ?n" by (simp_all add: placed_def)
    have "{j\<in>?E. \<not> ?q k j} \<subseteq> {j\<in>?E. \<not> ?p k j}" by (auto simp: then_by_def)
    then have "card {j\<in>?E. \<not> ?q k j} \<le> card {j\<in>?E. \<not> ?p k j}" using finE by (intro card_mono) auto
    then show "k \<in> ?Q" using kE pk by (simp add: placed_def)
  qed
  have cQ: "card ?Q = nat ?n" using placed_count[OF finE so] nE by simp
  have PQ: "?P = ?Q" using sub cQ groups finE by (intro card_subset_eq) auto
  have same: "placed ?E ?p ?n k \<longleftrightarrow> placed ?E ?q ?n k" for k
    using PQ placed_in[of ?E ?p ?n k] placed_in[of ?E ?q ?n k] by blast
  show eq: "ration (largest_remainder no_order) K v x = ration (largest_remainder (first_in order)) K v x"
    unfolding ration_no_order_units ration_largest_remainder_units by (simp add: fun_eq_iff units_unfold same then_by_no_order)
  show "residual K (ration (largest_remainder no_order) K) v x = 0"
    using ration_largest_remainder_sums_exactly[OF fin inj nn x0 xv] eq by (simp add: residual_def)
qed
(* GATE:END *)


section \<open>Two instances kept on purpose\<close>

text \<open>Equal treatment holds only with no order declared.\<close>

(* GATE:BEGIN LWn *)
theorem a_declared_order_treats_equal_requests_unequally:
  "map (ration (largest_remainder (first_in id)) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3] = [4, 3, 3]
   \<and> map (ration (largest_remainder no_order) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3] = [3, 3, 3]"
  by code_simp
(* GATE:END *)

text \<open>A unit given to the first in an order among all the keys can go to a key of no weight, a
  whole unit from its exact share, where rounding to the nearest gives it to a share rounded down
  with a remainder.\<close>

(* GATE:BEGIN LHn *)
theorem a_unit_to_the_first_among_all_keys_strays:
  "sum_list (map (half_up_part 62 {0::nat, 1, 2, 3} three_none_eleven) [0, 1, 2, 3]) = 61
   \<and> map (units (half_up_part 62 {0::nat, 1, 2, 3} three_none_eleven)
                (short 62 {0::nat, 1, 2, 3} (half_up_part 62 {0::nat, 1, 2, 3} three_none_eleven))
                {0, 1, 2, 3} (first_in none_first) {} no_order) [0, 1, 2, 3] = [7, 1, 27, 27]
   \<and> map (to_nearest half_up_part (first_in none_first) (first_in none_first) 62 {0::nat, 1, 2, 3} three_none_eleven)
         [0, 1, 2, 3] = [8, 0, 27, 27]"
  by code_simp
(* GATE:END *)

end
