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


section \<open>A renaming of the keys carries the grants with no order\<close>

lemma lw4_parts:
  assumes bij: "bij \<sigma>"
  shows "floor_part x (\<sigma> ` K) (\<lambda>j. v (inv \<sigma> j)) = (\<lambda>j. floor_part x K v (inv \<sigma> j))"
    and "remainder x (\<sigma> ` K) (\<lambda>j. v (inv \<sigma> j)) = (\<lambda>j. remainder x K v (inv \<sigma> j))"
    and "unmet x (\<sigma> ` K) (\<lambda>j. v (inv \<sigma> j)) = \<sigma> ` unmet x K v"
    and "short x (\<sigma> ` K) (floor_part x (\<sigma> ` K) (\<lambda>j. v (inv \<sigma> j))) = short x K (floor_part x K v)"
proof -
  have inj: "inj \<sigma>" using bij by (simp add: bij_def)
  have memb: "j \<in> \<sigma> ` S \<longleftrightarrow> inv \<sigma> j \<in> S" for j S
  proof -
    have sj: "\<sigma> (inv \<sigma> j) = j" using bij by (simp add: bij_def surj_f_inv_f)
    have "j \<in> \<sigma> ` S \<longleftrightarrow> \<sigma> (inv \<sigma> j) \<in> \<sigma> ` S" using sj by simp
    also have "\<dots> \<longleftrightarrow> inv \<sigma> j \<in> S" by (rule inj_image_mem_iff[OF inj])
    finally show ?thesis .
  qed
  have T: "(\<Sum>j\<in>\<sigma> ` K. v (inv \<sigma> j)) = (\<Sum>j\<in>K. v j)" by (rule renamed_sum[OF bij])
  show f: "floor_part x (\<sigma> ` K) (\<lambda>j. v (inv \<sigma> j)) = (\<lambda>j. floor_part x K v (inv \<sigma> j))"
    by (rule ext) (simp add: floor_part_def T memb)
  show "remainder x (\<sigma> ` K) (\<lambda>j. v (inv \<sigma> j)) = (\<lambda>j. remainder x K v (inv \<sigma> j))"
    by (rule ext) (simp add: remainder_def T)
  show "unmet x (\<sigma> ` K) (\<lambda>j. v (inv \<sigma> j)) = \<sigma> ` unmet x K v"
    unfolding unmet_def f by (rule renamed_filter[OF bij])
  show "short x (\<sigma> ` K) (floor_part x (\<sigma> ` K) (\<lambda>j. v (inv \<sigma> j))) = short x K (floor_part x K v)"
    unfolding short_def f using renamed_sum[OF bij, of "floor_part x K v" K] by simp
qed

(* GATE:BEGIN LW4 *)
theorem no_order_renaming_carries_the_grants:
  assumes bij: "bij \<sigma>"
  shows "ration (largest_remainder no_order) (\<sigma> ` K) (\<lambda>j. v (inv \<sigma> j)) x (\<sigma> k)
           = ration (largest_remainder no_order) K v x k"
proof -
  have inj: "inj \<sigma>" using bij by (simp add: bij_def)
  have bk: "inv \<sigma> (\<sigma> j) = j" for j using inj by (simp add: inv_f_f)
  note p = lw4_parts[OF bij, of x K v]
  have pl: "placed (\<sigma> ` U) (larger_remainder x (\<sigma> ` K) (\<lambda>j. v (inv \<sigma> j))) n (\<sigma> k)
              \<longleftrightarrow> placed U (larger_remainder x K v) n k" for U n
  proof -
    have s: "{j \<in> \<sigma> ` U. \<not> larger_remainder x (\<sigma> ` K) (\<lambda>j. v (inv \<sigma> j)) (\<sigma> k) j}
               = \<sigma> ` {j\<in>U. \<not> larger_remainder x K v k j}"
      unfolding larger_remainder_def p(2) bk by (rule renamed_filter[OF bij])
    have c: "card (\<sigma> ` S) = card S" for S by (rule card_image) (rule inj_on_subset[OF inj subset_UNIV])
    have m: "\<sigma> k \<in> \<sigma> ` U \<longleftrightarrow> k \<in> U" using inj by (simp add: inj_image_mem_iff)
    show ?thesis unfolding placed_def s c m ..
  qed
  show ?thesis unfolding ration_no_order_units units_def p(3,4) pl by (simp add: p(1) bk)
qed
(* GATE:END *)


section \<open>Rounding to the nearest\<close>

text \<open>Rounded half up or half to even, a share is its floor or one more, and one more only where
  twice its remainder reaches the sum of the weights.\<close>

lemma nearest_part:
  assumes pos: "0 < (\<Sum>j\<in>K. w j)" and k: "k \<in> K" and pt: "part = half_up_part \<or> part = half_even_part"
  shows "(part t K w k = floor_part t K w k \<and> 2 * remainder t K w k \<le> (\<Sum>j\<in>K. w j))
         \<or> (part t K w k = floor_part t K w k + 1 \<and> (\<Sum>j\<in>K. w j) \<le> 2 * remainder t K w k)"
proof -
  define T where "T = (\<Sum>j\<in>K. w j)"
  define F where "F = (t * w k) div T"
  define r where "r = (t * w k) mod T"
  have Tp: "0 < T" using pos by (simp add: T_def)
  have r0: "0 \<le> r" "r < T" using Tp by (simp_all add: r_def)
  have fl: "floor_part t K w k = F" using k by (simp add: floor_part_def F_def T_def)
  have rm: "remainder t K w k = r" by (simp add: remainder_def r_def T_def)
  have eq: "t * w k = F * T + r" unfolding F_def r_def by (rule div_mult_mod_eq[symmetric])
  from pt show ?thesis
  proof
    assume hu: "part = half_up_part"
    have "part t K w k = (2 * t * w k + T) div (2 * T)" using k hu by (simp add: half_up_part_def T_def)
    also have "2 * t * w k + T = (2 * r + T) + F * (2 * T)" using eq by (simp add: algebra_simps)
    also have "((2 * r + T) + F * (2 * T)) div (2 * T) = F + (2 * r + T) div (2 * T)"
      by (rule div_mult_self1) (use Tp in simp)
    finally have hp: "part t K w k = F + (2 * r + T) div (2 * T)" .
    show ?thesis
    proof (cases "2 * r < T")
      case True
      then have "(2 * r + T) div (2 * T) = 0" using r0 by (intro div_pos_pos_trivial) auto
      then show ?thesis using hp fl rm True by (simp add: T_def)
    next
      case False
      have "(2 * r + T) div (2 * T) = ((2 * r - T) + 1 * (2 * T)) div (2 * T)" by (simp add: algebra_simps)
      also have "\<dots> = 1 + (2 * r - T) div (2 * T)" by (rule div_mult_self1) (use Tp in simp)
      also have "(2 * r - T) div (2 * T) = 0" using False r0 by (intro div_pos_pos_trivial) auto
      finally have "(2 * r + T) div (2 * T) = 1" by simp
      then show ?thesis using hp fl rm False by (simp add: T_def)
    qed
  next
    assume he: "part = half_even_part"
    have "part t K w k = (if 2 * r < T then F else if T < 2 * r then F + 1 else if even F then F else F + 1)"
      using k he by (simp add: half_even_part_def Let_def T_def F_def r_def remainder_def)
    then show ?thesis using fl rm by (auto simp: T_def[symmetric] split: if_splits)
  qed
qed

lemma count_placed:
  assumes fin: "finite K" and sub: "E \<subseteq> K"
  shows "(\<Sum>k\<in>K. if c \<and> placed E p m k then 1 else 0) = (if c then int (card {k\<in>E. placed E p m k}) else (0::int))"
proof (cases c)
  case True
  have "(\<Sum>k\<in>K. if c \<and> placed E p m k then 1 else 0) = (\<Sum>k\<in>K. if placed E p m k then 1 else (0::int))"
    using True by simp
  also have "\<dots> = int (card (K \<inter> {k. placed E p m k}))" using fin by (simp add: sum.If_cases)
  also have "K \<inter> {k. placed E p m k} = {k\<in>E. placed E p m k}" using sub placed_in[of E p m] by auto
  finally show ?thesis using True by simp
next
  case False
  then show ?thesis by simp
qed

lemma units_total:
  assumes fin: "finite K" and E: "E \<subseteq> K" and L: "L \<subseteq> K"
  shows "total K (units base n E gain L lose)
           = (\<Sum>k\<in>K. base k) + (if 0 < n then int (card {k\<in>E. placed E gain n k}) else 0)
             - (if n < 0 then int (card {k\<in>L. placed L lose (- n) k}) else 0)"
  using count_placed[OF fin E, of "0 < n" gain n] count_placed[OF fin L, of "n < 0" lose "- n"]
  by (simp add: total_def units_def sum.distrib sum_subtractf)

lemma strict_order_on_subset: "strict_order_on E p \<Longrightarrow> D \<subseteq> E \<Longrightarrow> strict_order_on D p"
  unfolding strict_order_on_def by blast

(* GATE:BEGIN LH1 *)
theorem to_nearest_sums_exactly:
  assumes fin: "finite K" and pos: "0 < (\<Sum>j\<in>K. w j)" and pt: "part = half_up_part \<or> part = half_even_part"
    and gain: "strict_order_on {k\<in>K. part t K w k = floor_part t K w k} gain"
    and lose: "strict_order_on {k\<in>K. floor_part t K w k < part t K w k} lose"
  shows "total K (to_nearest part gain lose t K w) = t"
proof -
  define T where "T = (\<Sum>j\<in>K. w j)"
  have Tp: "0 < T" using pos by (simp add: T_def)
  let ?F = "floor_part t K w" and ?P = "part t K w" and ?r = "remainder t K w"
  let ?U = "{k\<in>K. ?F k < ?P k}" and ?E = "{k\<in>K. ?P k = ?F k \<and> 0 < ?r k}"
  have finU: "finite ?U" and finE: "finite ?E" using fin by simp_all
  have each: "?P k = ?F k + (if k \<in> ?U then 1 else 0)" if k: "k \<in> K" for k
  proof (cases "?P k = ?F k")
    case True
    then show ?thesis by simp
  next
    case False
    then have "?P k = ?F k + 1" using nearest_part[OF pos k pt, of t] by blast
    then show ?thesis using k by simp
  qed
  have rb: "0 \<le> ?r k" "?r k < T" for k using Tp by (simp_all add: remainder_def T_def)
  have tw: "t * w k = ?F k * T + ?r k" if "k \<in> K" for k
    using that div_mult_mod_eq[of "t * w k" T] by (simp add: floor_part_def remainder_def T_def)
  define m where "m = t - (\<Sum>k\<in>K. ?F k)"
  have sumr: "(\<Sum>k\<in>K. ?r k) = m * T"
  proof -
    have "t * T = (\<Sum>k\<in>K. t * w k)" by (simp add: T_def sum_distrib_left)
    also have "\<dots> = (\<Sum>k\<in>K. ?F k * T + ?r k)" by (rule sum.cong) (simp_all add: tw)
    also have "\<dots> = (\<Sum>k\<in>K. ?F k) * T + (\<Sum>k\<in>K. ?r k)" by (simp add: sum.distrib sum_distrib_right)
    finally show ?thesis by (simp add: m_def algebra_simps)
  qed
  have sumP: "(\<Sum>k\<in>K. ?P k) = (\<Sum>k\<in>K. ?F k) + int (card ?U)"
  proof -
    have "(\<Sum>k\<in>K. ?P k) = (\<Sum>k\<in>K. ?F k + (if k \<in> ?U then 1 else 0))" by (rule sum.cong) (simp_all add: each)
    also have "\<dots> = (\<Sum>k\<in>K. ?F k) + (\<Sum>k\<in>K. if k \<in> ?U then 1 else 0)" by (rule sum.distrib)
    finally have s: "(\<Sum>k\<in>K. ?P k) = (\<Sum>k\<in>K. ?F k) + (\<Sum>k\<in>K. if k \<in> ?U then 1 else 0)" .
    have "(\<Sum>k\<in>K. if k \<in> ?U then 1 else (0::int)) = (\<Sum>k\<in>K \<inter> ?U. 1)"
      by (rule sum.inter_restrict[OF fin, symmetric])
    also have "K \<inter> ?U = ?U" by blast
    finally have "(\<Sum>k\<in>K. if k \<in> ?U then 1 else (0::int)) = int (card ?U)" by simp
    then show ?thesis using s by simp
  qed
  have m0: "0 \<le> m"
  proof -
    have "0 \<le> (\<Sum>k\<in>K. ?r k)" by (rule sum_nonneg) (simp add: rb)
    then show ?thesis using sumr Tp by (simp add: zero_le_mult_iff)
  qed
  have mbound: "m \<le> int (card ?U) + int (card ?E)"
  proof -
    have dis: "?U \<inter> ?E = {}" by auto
    have "(\<Sum>k\<in>K. ?r k) \<le> (\<Sum>k\<in>K. if k \<in> ?U \<union> ?E then T else 0)"
    proof (rule sum_mono)
      fix k
      assume k: "k \<in> K"
      show "?r k \<le> (if k \<in> ?U \<union> ?E then T else 0)"
      proof (cases "k \<in> ?U \<union> ?E")
        case True
        then show ?thesis using rb[of k] by simp
      next
        case False
        then have nU: "k \<notin> ?U" and nE: "k \<notin> ?E" by simp_all
        have "?P k = ?F k" using each[OF k] nU k by simp
        then have "\<not> 0 < ?r k" using nE k by simp
        then show ?thesis using False rb[of k] by simp
      qed
    qed
    also have "(\<Sum>k\<in>K. if k \<in> ?U \<union> ?E then T else 0) = (\<Sum>k\<in>K \<inter> (?U \<union> ?E). T)"
      by (rule sum.inter_restrict[OF fin, symmetric])
    also have "K \<inter> (?U \<union> ?E) = ?U \<union> ?E" by blast
    finally have le: "(\<Sum>k\<in>K. ?r k) \<le> (\<Sum>k\<in>?U \<union> ?E. T)" .
    have "(\<Sum>k\<in>?U \<union> ?E. T) = T * int (card (?U \<union> ?E))" by simp
    moreover have "card (?U \<union> ?E) = card ?U + card ?E" by (rule card_Un_disjoint[OF finU finE dis])
    ultimately have "T * m \<le> T * (int (card ?U) + int (card ?E))" using le sumr by (simp add: mult.commute)
    then show ?thesis by (rule mult_left_le_imp_le) (rule Tp)
  qed
  have n: "short t K ?P = m - int (card ?U)" by (simp add: short_def sumP m_def)
  have gE: "strict_order_on ?E gain" by (rule strict_order_on_subset[OF gain]) auto
  have tot: "total K (to_nearest part gain lose t K w)
               = (\<Sum>k\<in>K. ?P k) + (if 0 < short t K ?P then int (card {k\<in>?E. placed ?E gain (short t K ?P) k}) else 0)
                 - (if short t K ?P < 0 then int (card {k\<in>?U. placed ?U lose (- short t K ?P) k}) else 0)"
    unfolding to_nearest_def by (rule units_total[OF fin]) auto
  show ?thesis
  proof (cases "0 < short t K ?P")
    case True
    have "card {k\<in>?E. placed ?E gain (short t K ?P) k} = nat (short t K ?P)"
      by (rule placed_count[OF finE gE]) (use True n mbound in simp_all)
    then show ?thesis using tot True n sumP m_def by simp
  next
    case False
    show ?thesis
    proof (cases "short t K ?P < 0")
      case True
      have "card {k\<in>?U. placed ?U lose (- short t K ?P) k} = nat (- short t K ?P)"
        by (rule placed_count[OF finU lose]) (use True n m0 in simp_all)
      then show ?thesis using tot True n sumP m_def by simp
    next
      case False': False
      then have "short t K ?P = 0" using False by simp
      then show ?thesis using tot by (simp add: short_def)
    qed
  qed
qed
(* GATE:END *)

(* GATE:BEGIN LH2 *)
theorem to_nearest_within_one_unit:
  assumes pos: "0 < (\<Sum>j\<in>K. w j)" and k: "k \<in> K" and pt: "part = half_up_part \<or> part = half_even_part"
  shows "\<bar>(\<Sum>j\<in>K. w j) * to_nearest part gain lose t K w k - t * w k\<bar> < (\<Sum>j\<in>K. w j)"
proof -
  define T where "T = (\<Sum>j\<in>K. w j)"
  define F where "F = floor_part t K w k"
  define r where "r = remainder t K w k"
  have Tp: "0 < T" using pos by (simp add: T_def)
  have r0: "0 \<le> r" "r < T" using Tp by (simp_all add: r_def remainder_def T_def)
  have eq: "t * w k = F * T + r"
    using k div_mult_mod_eq[of "t * w k" T] by (simp add: F_def r_def floor_part_def remainder_def T_def)
  have np: "(part t K w k = F \<and> 2 * r \<le> T) \<or> (part t K w k = F + 1 \<and> T \<le> 2 * r)"
    using nearest_part[OF pos k pt, of t] by (simp add: F_def r_def T_def)
  let ?n = "short t K (part t K w)"
  let ?E = "{k\<in>K. part t K w k = floor_part t K w k \<and> 0 < remainder t K w k}"
  let ?L = "{k\<in>K. floor_part t K w k < part t K w k}"
  have u: "to_nearest part gain lose t K w k
             = part t K w k + (if 0 < ?n \<and> placed ?E gain ?n k then 1 else 0) - (if ?n < 0 \<and> placed ?L lose (- ?n) k then 1 else 0)"
    unfolding to_nearest_def units_def ..
  have pE: "placed ?E gain ?n k \<Longrightarrow> part t K w k = F \<and> 0 < r" by (simp add: placed_def F_def r_def)
  have pL: "placed ?L lose (- ?n) k \<Longrightarrow> F < part t K w k" by (simp add: placed_def F_def)
  have g: "to_nearest part gain lose t K w k = F \<or> (to_nearest part gain lose t K w k = F + 1 \<and> 0 < r)"
  proof (cases "0 < ?n \<and> placed ?E gain ?n k")
    case True
    then show ?thesis using u pE by simp
  next
    case False
    then have u': "to_nearest part gain lose t K w k = part t K w k - (if ?n < 0 \<and> placed ?L lose (- ?n) k then 1 else 0)"
      using u by simp
    show ?thesis
    proof (cases "?n < 0 \<and> placed ?L lose (- ?n) k")
      case True
      then show ?thesis using u' pL np by auto
    next
      case False
      then show ?thesis using u' np Tp by auto
    qed
  qed
  then show ?thesis
    using r0 by (auto simp: eq T_def[symmetric] distrib_left abs_less_iff algebra_simps)
qed
(* GATE:END *)

lemma first_in_strict_order: "inj_on order E \<Longrightarrow> strict_order_on E (first_in order)"
  unfolding strict_order_on_def first_in_def
  by (auto simp: linorder_not_less order_le_less) (metis inj_onD)

lemma larger_remainder_then_order_strict:
  "inj_on order E \<Longrightarrow> strict_order_on E (then_by (larger_remainder t K w) (first_in order))"
  unfolding strict_order_on_def first_in_def then_by_def larger_remainder_def
  by (auto dest: inj_onD) (metis less_trans nat_neq_iff inj_onD)+

lemma smaller_remainder_then_order_strict:
  "inj_on order E \<Longrightarrow> strict_order_on E (then_by (\<lambda>j k. larger_remainder t K w k j) (first_in order))"
  unfolding strict_order_on_def first_in_def then_by_def larger_remainder_def
  by (auto dest: inj_onD) (metis less_trans nat_neq_iff inj_onD)+

(* GATE:BEGIN LH3 *)
theorem every_stated_way_settles_to_the_nearest_exactly:
  assumes fin: "finite K" and pos: "0 < (\<Sum>j\<in>K. w j)" and pt: "part = half_up_part \<or> part = half_even_part"
    and inj: "inj_on order K"
    and gain: "gain = first_in order \<or> gain = then_by (larger_remainder t K w) (first_in order)"
    and lose: "lose = first_in order \<or> lose = then_by (\<lambda>j k. larger_remainder t K w k j) (first_in order)"
  shows "total K (to_nearest part gain lose t K w) = t"
proof -
  have g: "strict_order_on K gain"
    using gain first_in_strict_order[OF inj] larger_remainder_then_order_strict[OF inj] by blast
  have l: "strict_order_on K lose"
    using lose first_in_strict_order[OF inj] smaller_remainder_then_order_strict[OF inj] by blast
  show ?thesis
    by (rule to_nearest_sums_exactly[OF fin pos pt strict_order_on_subset[OF g] strict_order_on_subset[OF l]]) blast+
qed
(* GATE:END *)

end
