(* SPDX-License-Identifier: MPL-2.0 *)

(* Rules over amount vectors on the target kernel (plan ledger, LG-9, restating LG-7's claims): the
   proportional rule lawful over an ordered field, the rule by rank lawful where the rank is
   injective on the keys, a split of zero, two lawful rules that disagree, attribution as an
   apportionment, and a threshold under which the residual falls as the amount drawn rises.
   Hand-written on the Kernel extracted from ontology/ledger/README.md section 10. *)

theory Allocation
imports Evaluation
begin

section \<open>Examples, before any theorem\<close>

text \<open>The target kernel's six examples. Three requests of 5 share 10 units. With no order declared
  each takes 3 and 1 is left. With an order declared for odd units, the first in it takes the unit.\<close>

value "map (ration (largest_remainder no_order) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3]"
value "map (ration (largest_remainder (first_in (\<lambda>k. 3 - k))) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3]"
value "map (ration (to_first id) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3]"

lemma example_no_order_leaves_a_unit:
  "map (ration (largest_remainder no_order) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3] = [3, 3, 3]"
  by code_simp

lemma example_a_declared_order_places_it:
  "map (ration (largest_remainder (first_in (\<lambda>k. 3 - k))) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3] = [3, 3, 4]"
  by code_simp

lemma example_to_the_first_in_order:
  "map (ration (to_first id) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3] = [4, 3, 3]"
  by code_simp

text \<open>Two ranks, the first of three requests of 5 and the second one request of 3, with 10 units.
  The unit the first rank cannot place does not reach the second.\<close>

value "map (by_rank (\<lambda>k. if k = 4 then 1 else 0) (ration (largest_remainder no_order)) {1, 2, 3, 4::nat}
              (\<lambda>k. if k = 4 then 3 else 5) 10) [1, 2, 3, 4]"

lemma example_a_unit_reaches_no_later_rank:
  "map (by_rank (\<lambda>k. if k = 4 then 1 else 0) (ration (largest_remainder no_order)) {1, 2, 3, 4::nat}
              (\<lambda>k. if k = 4 then 3 else 5) 10) [1, 2, 3, 4] = [3, 3, 3, 0]"
  by code_simp

text \<open>Blocks. With 7 units and requests of 5 and 4 in that order, the first is granted whole, the
  second nothing, and 2 are left.\<close>

value "map (whole_each [1, 2::nat] (\<lambda>k. if k = 1 then 5 else 4) (7::int)) [1, 2]"

lemma example_blocks:
  "map (whole_each [1, 2::nat] (\<lambda>k. if k = 1 then 5 else 4) (7::int)) [1, 2] = [5, 0]"
  by code_simp

text \<open>Distinct ranks are priority. 7 units to requests of 5 and 4.\<close>

value "map (by_rank id (\<lambda>_ _ _. nothing) {1, 2::nat} (\<lambda>k. if k = 1 then 5 else 4) (7::int)) [1, 2]"

lemma example_distinct_ranks_are_priority:
  "map (by_rank id (\<lambda>_ _ _. nothing) {1, 2::nat} (\<lambda>k. if k = 1 then 5 else 4) (7::int)) [1, 2] = [5, 2]"
  by code_simp

text \<open>Two proposals at one position ask 6 and 3 of an account with 6 available. Sharing one rank by
  the proportional rule grants 4 and 2, and distinct ranks in priority grant 6 and 0, each the
  whole 6 with no residual. Where 10 is available, the requests fit and are granted as asked.\<close>

definition shared :: "('k, 'n::linordered_field) policy" where
  "shared = \<lparr>refuses = False, ranked = False, tie = Some proportional, leaves = False, unmixed = False\<rparr>"

definition in_order :: "('k, 'n::linordered_idom) policy" where
  "in_order = \<lparr>refuses = False, ranked = True, tie = None, leaves = False, unmixed = False\<rparr>"

definition grants :: "'k list \<Rightarrow> ('k, 'n::zero) outcome \<Rightarrow> 'n list \<times> 'n" where
  "grants ks out = (case out of Granted g r \<Rightarrow> (map g ks, r) | Refused why \<Rightarrow> ([], 0))"

value "grants [1, 2] (merge shared (\<lambda>_. 0) (6::rat) [(1::nat, 6), (2, 3)])"
value "grants [1, 2] (merge in_order id (6::rat) [(1::nat, 6), (2, 3)])"
value "grants [1, 2] (merge shared (\<lambda>_. 0) (10::rat) [(1::nat, 6), (2, 3)])"

lemma example_proportional_merge:
  "grants [1, 2] (merge shared (\<lambda>_. 0) (6::rat) [(1::nat, 6), (2, 3)]) = ([4, 2], 0)"
  by code_simp

lemma example_priority_merge:
  "grants [1, 2] (merge in_order id (6::rat) [(1::nat, 6), (2, 3)]) = ([6, 0], 0)"
  by code_simp

lemma example_requests_that_fit:
  "grants [1, 2] (merge shared (\<lambda>_. 0) (10::rat) [(1::nat, 6), (2, 3)]) = ([6, 3], 0)"
  by code_simp

text \<open>The two negative instances. One arrangement, 2 and 4 with 3 to split: the proportional rule
  gives the first key 1 and the rule by distinct ranks gives it 2. Under a threshold of 10, drawing
  10 leaves a residual of 10 and drawing 11 leaves none.\<close>

value "(proportional {0::nat, 1} (\<lambda>k. if k = 0 then 2 else 4) (3::rat) 0,
        by_rank id (\<lambda>_ _ _. nothing) {0::nat, 1} (\<lambda>k. if k = 0 then 2 else 4) (3::rat) 0)"
value "((10::rat) - (if (10::rat) \<le> 10 then 0 else 10), (11::rat) - (if (11::rat) \<le> 10 then 0 else 11))"


section \<open>Amount vectors and the predicates on a rule\<close>

lemma total_nonneg: "nonneg_on K v \<Longrightarrow> 0 \<le> total K v"
  by (simp add: total_def nonneg_on_def sum_nonneg)

lemma total_less: "total K (less v w) = total K v - total K w"
  by (simp add: total_def less_def sum_subtractf)

lemma total_nothing [simp]: "total K nothing = 0"
  by (simp add: total_def nothing_def)

lemma nonneg_total_zero:
  assumes fin: "finite K" and nn: "nonneg_on K v" and z: "total K v = 0"
  shows "v = nothing"
proof
  fix k
  show "v k = nothing k"
  proof (cases "k \<in> K")
    case True
    have "\<forall>j\<in>K. v j = 0"
      using fin nn z sum_nonneg_eq_0_iff[of K v] by (simp add: total_def nonneg_on_def)
    with True show ?thesis by (simp add: nothing_def)
  next
    case False
    with nn show ?thesis by (simp add: nonneg_on_def nothing_def)
  qed
qed

lemma nonneg_less:
  "nonneg_on K v \<Longrightarrow> nonneg_on K w \<Longrightarrow> fits_in w v \<Longrightarrow> nonneg_on K (less v w)"
  by (auto simp: nonneg_on_def less_def fits_in_def)

lemma rations_parts:
  assumes "rations K R" "nonneg_on K v" "0 \<le> x" "x \<le> total K v"
  shows "nonneg_on K (R v x)" "fits_in (R v x) v" "total K (R v x) \<le> x"
  using assms by (simp_all add: rations_def)

lemma rations_whole: "rations K R \<Longrightarrow> nonneg_on K v \<Longrightarrow> R v (total K v) = v"
  by (simp add: rations_def)

lemma lawful_rations: "lawful K R \<Longrightarrow> rations K R"
  by (simp add: lawful_def)

lemma lawful_exact:
  assumes "lawful K R" "nonneg_on K v" "0 \<le> x" "x \<le> total K v"
  shows "total K (R v x) = x"
proof -
  have "residual K R v x = 0" using assms by (simp add: lawful_def exact_def)
  then show ?thesis by (simp add: residual_def)
qed

lemma lawful_fits_in:
  "lawful K R \<Longrightarrow> nonneg_on K v \<Longrightarrow> 0 \<le> x \<Longrightarrow> x \<le> total K v \<Longrightarrow> fits_in (R v x) v"
  by (simp add: lawful_def rations_def)

lemma lawful_nonneg:
  "lawful K R \<Longrightarrow> nonneg_on K v \<Longrightarrow> 0 \<le> x \<Longrightarrow> x \<le> total K v \<Longrightarrow> nonneg_on K (R v x)"
  by (simp add: lawful_def rations_def)

lemma lawful_whole: "lawful K R \<Longrightarrow> nonneg_on K v \<Longrightarrow> R v (total K v) = v"
  by (simp add: lawful_def rations_def)

text \<open>The four axioms of the kernel before LG-9 give a lawful rule, and a lawful rule has them.\<close>

lemma lawfulI:
  assumes split: "\<And>v x. nonneg_on K v \<Longrightarrow> 0 \<le> x \<Longrightarrow> x \<le> total K v \<Longrightarrow>
                    total K (R v x) = x \<and> fits_in (R v x) v \<and> nonneg_on K (R v x)"
      and whole: "\<And>v. nonneg_on K v \<Longrightarrow> R v (total K v) = v"
  shows "lawful K R"
  unfolding lawful_def rations_def exact_def residual_def
  using split whole by auto


section \<open>The proportional rule, over an ordered field\<close>

(* GATE:BEGIN LA1 *)
theorem proportional_lawful:
  fixes K :: "'k set"
  assumes fin: "finite K"
  shows "lawful K (proportional K :: ('k, 'n::linordered_field) rule)"
proof (rule lawfulI)
  fix v :: "('k, 'n) amounts" and x :: 'n
  assume nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
  show "total K (proportional K v x) = x \<and> fits_in (proportional K v x) v
          \<and> nonneg_on K (proportional K v x)"
  proof (cases "total K v = 0")
    case True
    then have "x = 0" using x0 xv by simp
    moreover have "v = nothing" using fin nn True by (rule nonneg_total_zero)
    ultimately show ?thesis
      by (simp add: proportional_def total_def fits_in_def nonneg_on_def nothing_def)
  next
    case False
    have pos: "0 < total K v" using False total_nonneg[OF nn] by simp
    have "total K (proportional K v x) = (\<Sum>k\<in>K. proportional K v x k)"
      by (simp add: total_def)
    also have "\<dots> = (\<Sum>k\<in>K. x * v k / total K v)"
      using False by (intro sum.cong) (auto simp: proportional_def)
    also have "\<dots> = x * total K v / total K v"
      by (simp add: total_def flip: sum_divide_distrib sum_distrib_left)
    also have "\<dots> = x" using pos by simp
    finally have exact: "total K (proportional K v x) = x" .
    have bounded: "fits_in (proportional K v x) v"
      unfolding fits_in_def
    proof
      fix k
      show "proportional K v x k \<le> v k"
      proof (cases "k \<in> K")
        case True
        have vk: "0 \<le> v k" using nn by (simp add: nonneg_on_def)
        have "x * v k \<le> total K v * v k" using mult_right_mono[OF xv vk] .
        then have "x * v k / total K v \<le> v k"
          using pos by (simp add: pos_divide_le_eq mult.commute)
        with True False show ?thesis by (simp add: proportional_def)
      next
        case False
        then show ?thesis using nn by (simp add: proportional_def nonneg_on_def)
      qed
    qed
    have nonneg: "nonneg_on K (proportional K v x)"
      using nn x0 pos
      by (auto simp: nonneg_on_def proportional_def intro!: divide_nonneg_nonneg mult_nonneg_nonneg)
    from exact bounded nonneg show ?thesis by blast
  qed
next
  fix v :: "('k, 'n) amounts"
  assume nn: "nonneg_on K v"
  show "proportional K v (total K v) = v"
  proof
    fix k
    show "proportional K v (total K v) k = v k"
    proof (cases "k \<in> K")
      case True
      show ?thesis
      proof (cases "total K v = 0")
        case True
        have "v = nothing" using fin nn True by (rule nonneg_total_zero)
        then show ?thesis by (simp add: proportional_def nothing_def)
      next
        case False
        with \<open>k \<in> K\<close> show ?thesis by (simp add: proportional_def)
      qed
    next
      case False
      then show ?thesis using nn by (simp add: proportional_def nonneg_on_def)
    qed
  qed
qed
(* GATE:END *)


section \<open>By rank, with a rank injective on the keys, which is priority\<close>

lemma beside_injective: "inj_on rank K \<Longrightarrow> k \<in> K \<Longrightarrow> beside K rank k = {k}"
  by (auto simp: beside_def inj_on_def)

lemma by_rank_injective:
  assumes inj: "inj_on rank K" and k: "k \<in> K" and vk: "0 \<le> v k"
  shows "by_rank rank tr K v x k = max 0 (min (v k) (x - ahead K rank v k))"
  using k vk beside_injective[OF inj k]
  by (auto simp: by_rank_def Let_def total_def min_def max_def)

lemma by_rank_off: "k \<notin> K \<Longrightarrow> by_rank rank tr K v x k = 0"
  by (simp add: by_rank_def)

lemma by_rank_sum:
  fixes v :: "('k, 'n::linordered_idom) amounts"
  assumes nn: "\<forall>k. 0 \<le> v k" and x0: "0 \<le> x" and fin: "finite K" and inj: "inj_on rank K"
  shows "(\<Sum>k\<in>K. max 0 (min (v k) (x - ahead K rank v k))) = min x (\<Sum>k\<in>K. v k)"
  using fin inj
proof (induct K rule: finite_ranking_induct[where f = rank])
  case empty
  then show ?case using x0 by (simp add: ahead_def)
next
  case (insert b A)
  show ?case
  proof (cases "b \<in> A")
    case True
    then show ?thesis using insert by (simp add: insert_absorb)
  next
    case bA: False
    have injA: "inj_on rank A" using insert.prems by (rule inj_on_subset) auto
    have lower: "rank k < rank b" if "k \<in> A" for k
    proof -
      have "rank k \<le> rank b" using insert.hyps(2) that by blast
      moreover have "rank k \<noteq> rank b"
        using insert.prems that bA by (auto simp: inj_on_def)
      ultimately show ?thesis by simp
    qed
    have aheadA: "ahead (insert b A) rank v k = ahead A rank v k" if "k \<in> A" for k
    proof -
      have "{j \<in> insert b A. rank j < rank k} = {j \<in> A. rank j < rank k}"
        using lower[OF that] by auto
      then show ?thesis by (simp add: ahead_def)
    qed
    have aheadb: "ahead (insert b A) rank v b = (\<Sum>k\<in>A. v k)"
    proof -
      have "{j \<in> insert b A. rank j < rank b} = A" using lower by auto
      then show ?thesis by (simp add: ahead_def)
    qed
    let ?S = "\<Sum>k\<in>A. v k"
    have IH: "(\<Sum>k\<in>A. max 0 (min (v k) (x - ahead A rank v k))) = min x ?S"
      using insert.hyps(3) injA by blast
    have sumA: "(\<Sum>k\<in>A. max 0 (min (v k) (x - ahead (insert b A) rank v k))) = min x ?S"
      using IH aheadA by (simp cong: sum.cong)
    have "(\<Sum>k\<in>insert b A. max 0 (min (v k) (x - ahead (insert b A) rank v k)))
            = max 0 (min (v b) (x - ahead (insert b A) rank v b))
              + (\<Sum>k\<in>A. max 0 (min (v k) (x - ahead (insert b A) rank v k)))"
      using insert.hyps(1) bA by simp
    also have "\<dots> = max 0 (min (v b) (x - ?S)) + min x ?S"
      using sumA aheadb by simp
    also have "\<dots> = min x (?S + v b)"
    proof -
      have "0 \<le> ?S" using nn by (simp add: sum_nonneg)
      moreover have "0 \<le> v b" using nn by simp
      ultimately show ?thesis using x0 by (simp add: min_def max_def)
    qed
    also have "\<dots> = min x (\<Sum>k\<in>insert b A. v k)"
      using insert.hyps(1) bA by (simp add: add.commute)
    finally show ?thesis .
  qed
qed

lemma ahead_plus_le:
  assumes fin: "finite K" and nn: "nonneg_on K v" and k: "k \<in> K"
  shows "ahead K rank v k + v k \<le> total K v"
proof -
  have "ahead K rank v k + v k = (\<Sum>j\<in>insert k {j \<in> K. rank j < rank k}. v j)"
    using fin by (simp add: ahead_def add.commute)
  also have "\<dots> \<le> (\<Sum>j\<in>K. v j)"
    using fin k nn by (intro sum_mono2) (auto simp: nonneg_on_def)
  finally show ?thesis by (simp add: total_def)
qed

(* GATE:BEGIN LA2 *)
theorem by_rank_lawful:
  fixes tr :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule"
  assumes fin: "finite K" and inj: "inj_on rank K"
  shows "lawful K (by_rank rank tr K)"
proof (rule lawfulI)
  fix v :: "('k, 'n) amounts" and x :: 'n
  assume nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
  have nnv: "\<forall>k. 0 \<le> v k" using nn by (simp add: nonneg_on_def)
  have pt: "by_rank rank tr K v x k = max 0 (min (v k) (x - ahead K rank v k))" if "k \<in> K" for k
    using by_rank_injective[OF inj that] nnv by blast
  have "total K (by_rank rank tr K v x) = (\<Sum>k\<in>K. max 0 (min (v k) (x - ahead K rank v k)))"
    unfolding total_def by (intro sum.cong) (simp_all add: pt)
  also have "\<dots> = min x (total K v)"
    using by_rank_sum[OF nnv x0 fin inj] by (simp add: total_def)
  also have "\<dots> = x" using xv by simp
  finally have exact: "total K (by_rank rank tr K v x) = x" .
  have bounded: "fits_in (by_rank rank tr K v x) v"
    unfolding fits_in_def
  proof
    fix k
    show "by_rank rank tr K v x k \<le> v k"
    proof (cases "k \<in> K")
      case True
      then show ?thesis using pt[OF True] nnv by (simp add: max_def min_def)
    next
      case False
      then show ?thesis using nnv by (simp add: by_rank_off)
    qed
  qed
  have nonneg: "nonneg_on K (by_rank rank tr K v x)"
    unfolding nonneg_on_def
  proof (intro conjI allI impI)
    fix k
    show "0 \<le> by_rank rank tr K v x k"
    proof (cases "k \<in> K")
      case True
      then show ?thesis using pt[OF True] by simp
    next
      case False
      then show ?thesis by (simp add: by_rank_off)
    qed
  next
    fix k
    assume "k \<notin> K"
    then show "by_rank rank tr K v x k = 0" by (rule by_rank_off)
  qed
  from exact bounded nonneg
  show "total K (by_rank rank tr K v x) = x \<and> fits_in (by_rank rank tr K v x) v
          \<and> nonneg_on K (by_rank rank tr K v x)" by blast
next
  fix v :: "('k, 'n) amounts"
  assume nn: "nonneg_on K v"
  show "by_rank rank tr K v (total K v) = v"
  proof
    fix k
    show "by_rank rank tr K v (total K v) k = v k"
    proof (cases "k \<in> K")
      case True
      have "v k \<le> total K v - ahead K rank v k" using ahead_plus_le[OF fin nn True, of rank] by simp
      moreover have "0 \<le> v k" using nn by (simp add: nonneg_on_def)
      ultimately show ?thesis using by_rank_injective[OF inj True, of v tr "total K v"] by simp
    next
      case False
      then show ?thesis using nn by (simp add: by_rank_off nonneg_on_def)
    qed
  qed
qed
(* GATE:END *)


section \<open>A split of zero\<close>

(* GATE:BEGIN LA3 *)
theorem lawful_split_of_zero:
  assumes fin: "finite K" and ok: "lawful K R" and nn: "nonneg_on K v"
  shows "R v 0 = nothing"
proof -
  have t0: "0 \<le> total K v" using nn by (rule total_nonneg)
  have "total K (R v 0) = 0" using lawful_exact[OF ok nn order_refl t0] .
  moreover have "nonneg_on K (R v 0)" using lawful_nonneg[OF ok nn order_refl t0] .
  ultimately show ?thesis using fin nonneg_total_zero by blast
qed
(* GATE:END *)


section \<open>Two lawful rules move different amounts\<close>

definition two_and_four :: "(nat, rat) amounts" where
  "two_and_four = (\<lambda>k. if k = 0 then 2 else if k = 1 then 4 else 0)"

(* GATE:BEGIN LA4 *)
theorem lawful_rules_differ:
  "lawful {0, 1} (proportional {0::nat, 1} :: (nat, rat) rule) \<and> lawful {0, 1} (by_rank id tr {0::nat, 1})
   \<and> proportional {0, 1} two_and_four 3 0 = 1 \<and> by_rank id tr {0, 1} two_and_four 3 0 = 2"
proof -
  have t: "total {0::nat, 1} two_and_four = 6" by (simp add: total_def two_and_four_def)
  have a: "ahead {0::nat, 1} id two_and_four 0 = 0" by (simp add: ahead_def)
  have r: "by_rank id tr {0::nat, 1} two_and_four 3 0 = 2"
    using by_rank_injective[of id "{0::nat, 1}" 0 two_and_four tr 3] a
    by (simp add: two_and_four_def)
  show ?thesis
    using proportional_lawful[of "{0::nat, 1}"] by_rank_lawful[of "{0::nat, 1}" id tr] t r
    by (simp add: proportional_def two_and_four_def)
qed
(* GATE:END *)


section \<open>Attribution across parties, as an apportionment\<close>

text \<open>Each part's total is apportioned among the parties by a basis for that part. A share matrix
  whose rows sum to one is the proportional rule with the rows as the bases.\<close>

(* GATE:BEGIN LC4 *)
theorem attribution_conserves:
  assumes ap: "apportions Q R" and shares: "shares_ok Q (length ps) basis"
      and parts: "\<forall>i<length ps. 0 \<le> total K (ps ! i)"
  shows "(\<Sum>q\<in>Q. attributed K R basis ps q) = (\<Sum>i<length ps. total K (ps ! i))"
    and "0 \<le> attributed K R basis ps q"
proof -
  have each: "nonneg_on Q (R (basis i) (total K (ps ! i))) \<and> total Q (R (basis i) (total K (ps ! i))) = total K (ps ! i)"
    if "i < length ps" for i
    using ap shares parts that unfolding apportions_def shares_ok_def by blast
  have "(\<Sum>q\<in>Q. attributed K R basis ps q) = (\<Sum>i<length ps. \<Sum>q\<in>Q. R (basis i) (total K (ps ! i)) q)"
    unfolding attributed_def by (rule sum.swap)
  also have "\<dots> = (\<Sum>i<length ps. total K (ps ! i))"
    using each by (intro sum.cong) (simp_all add: total_def)
  finally show "(\<Sum>q\<in>Q. attributed K R basis ps q) = (\<Sum>i<length ps. total K (ps ! i))" .
  show "0 \<le> attributed K R basis ps q"
    unfolding attributed_def using each by (intro sum_nonneg) (simp add: nonneg_on_def)
qed
(* GATE:END *)


section \<open>A threshold makes the residual fall as the amount drawn rises\<close>

definition threshold :: "rat \<Rightarrow> rat \<Rightarrow> rat" where
  "threshold t x = (if x \<le> t then 0 else x)"

(* GATE:BEGIN LN1 *)
theorem residual_falls_as_the_drawn_amount_rises:
  "(\<forall>x. 0 \<le> x \<longrightarrow> 0 \<le> threshold 10 x \<and> threshold 10 x \<le> x)
   \<and> 11 - threshold 10 11 < 10 - threshold 10 (10::rat)"
  by (simp add: threshold_def)
(* GATE:END *)

end
