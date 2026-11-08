(* SPDX-License-Identifier: MPL-2.0 *)

(* Merge rules over amount vectors: the four axioms of a lawful rule, the proportional and the
   priority rule, a split of zero, two lawful rules that disagree, attribution across parties, and
   a threshold under which the residual falls as the amount drawn rises (plan ledger, LG-7).
   Hand-written on the Kernel extracted from ontology/ledger/README.md section 10. *)

theory Allocation
imports Kernel
begin

section \<open>Examples, before any theorem\<close>

text \<open>Two proposals at one position ask 6 and 3 of an account with 6 available. The
  proportional rule grants 4 and 2, the priority rule 6 and 0, and both grant the whole 6.\<close>

value "(merge proportional 6 [(1::nat, 6), (2, 3)] 1, merge proportional 6 [(1::nat, 6), (2, 3)] 2)"
value "(merge in_priority 6 [(1::nat, 6), (2, 3)] 1, merge in_priority 6 [(1::nat, 6), (2, 3)] 2)"

text \<open>Requests that fit are granted as asked, whatever the rule.\<close>

value "(merge proportional 10 [(1::nat, 6), (2, 3)] 1, merge proportional 10 [(1::nat, 6), (2, 3)] 2)"

text \<open>The two negative instances. One arrangement, 2 and 4 with 3 to split: the proportional rule
  gives the first key 1 and the priority rule gives it 2. Under a threshold of 10, drawing 10
  leaves a residual of 10 and drawing 11 leaves none.\<close>

value "(proportional {0::nat, 1} (\<lambda>k. if k = 0 then 2 else 4) 3 0,
        in_priority {0::nat, 1} (\<lambda>k. if k = 0 then 2 else 4) 3 0)"
value "((10::rat) - (if (10::rat) \<le> 10 then 0 else 10), (11::rat) - (if (11::rat) \<le> 10 then 0 else 11))"

text \<open>The positive instances again, as lemmas the kernel proves rather than values it prints.\<close>

lemma example_proportional_merge:
  "merge proportional 6 [(1::nat, 6), (2, 3)] 1 = 4 \<and> merge proportional 6 [(1::nat, 6), (2, 3)] 2 = 2"
  by (simp add: merge_def proposers_def requested_def total_def proportional_def)

lemma example_priority_merge:
  "merge in_priority 6 [(1::nat, 6), (2, 3)] 1 = 6 \<and> merge in_priority 6 [(1::nat, 6), (2, 3)] 2 = 0"
proof -
  have "{j::nat. (j = Suc 0 \<or> j = 2) \<and> j < 2} = {Suc 0}" by auto
  then show ?thesis
    by (simp add: merge_def proposers_def requested_def total_def in_priority_def ahead_def)
qed

lemma example_requests_that_fit:
  "merge proportional 10 [(1::nat, 6), (2, 3)] 1 = 6 \<and> merge proportional 10 [(1::nat, 6), (2, 3)] 2 = 3"
  by (simp add: merge_def proposers_def requested_def total_def)

section \<open>Amount vectors\<close>

lemma total_nonneg: "nonneg_on K v \<Longrightarrow> 0 \<le> total K v"
  by (simp add: total_def nonneg_on_def sum_nonneg)

lemma total_less: "finite K \<Longrightarrow> total K (less v w) = total K v - total K w"
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

lemma lawful_exact:
  "lawful K R \<Longrightarrow> nonneg_on K v \<Longrightarrow> 0 \<le> x \<Longrightarrow> x \<le> total K v \<Longrightarrow> total K (R v x) = x"
  by (simp add: lawful_def)

lemma lawful_fits_in:
  "lawful K R \<Longrightarrow> nonneg_on K v \<Longrightarrow> 0 \<le> x \<Longrightarrow> x \<le> total K v \<Longrightarrow> fits_in (R v x) v"
  by (simp add: lawful_def)

lemma lawful_nonneg:
  "lawful K R \<Longrightarrow> nonneg_on K v \<Longrightarrow> 0 \<le> x \<Longrightarrow> x \<le> total K v \<Longrightarrow> nonneg_on K (R v x)"
  by (simp add: lawful_def)

lemma lawful_whole: "lawful K R \<Longrightarrow> nonneg_on K v \<Longrightarrow> R v (total K v) = v"
  by (simp add: lawful_def)


section \<open>The proportional rule\<close>

(* GATE:BEGIN LA1 *)
theorem proportional_lawful:
  assumes fin: "finite K"
  shows "lawful K (proportional K)"
proof -
  have split: "total K (proportional K v x) = x \<and> fits_in (proportional K v x) v
                 \<and> nonneg_on K (proportional K v x)"
    if nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v" for v x
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
  have whole: "proportional K v (total K v) = v" if nn: "nonneg_on K v" for v
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
  show ?thesis unfolding lawful_def using split whole by blast
qed
(* GATE:END *)


section \<open>The priority rule\<close>

lemma in_priority_sum:
  fixes v :: "'k::linorder amounts"
  assumes nn: "\<forall>k. 0 \<le> v k" and x0: "0 \<le> x" and fin: "finite K"
  shows "(\<Sum>k\<in>K. max 0 (min (v k) (x - ahead K v k))) = min x (\<Sum>k\<in>K. v k)"
  using fin
proof (induct rule: finite_linorder_max_induct)
  case empty
  then show ?case using x0 by simp
next
  case (insert b A)
  have bA: "b \<notin> A" using insert.hyps(2) by auto
  have aheadA: "ahead (insert b A) v k = ahead A v k" if "k \<in> A" for k
  proof -
    have "k < b" using that insert.hyps(2) by auto
    then have "{j \<in> insert b A. j < k} = {j \<in> A. j < k}" by auto
    then show ?thesis by (simp add: ahead_def)
  qed
  have aheadb: "ahead (insert b A) v b = (\<Sum>k\<in>A. v k)"
  proof -
    have "{j \<in> insert b A. j < b} = A" using insert.hyps(2) by auto
    then show ?thesis by (simp add: ahead_def)
  qed
  let ?S = "\<Sum>k\<in>A. v k"
  have sumA: "(\<Sum>k\<in>A. max 0 (min (v k) (x - ahead (insert b A) v k))) = min x ?S"
    using aheadA insert.hyps(3) by (simp cong: sum.cong)
  have "(\<Sum>k\<in>insert b A. max 0 (min (v k) (x - ahead (insert b A) v k)))
          = max 0 (min (v b) (x - ahead (insert b A) v b))
            + (\<Sum>k\<in>A. max 0 (min (v k) (x - ahead (insert b A) v k)))"
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
  finally show ?case .
qed

lemma ahead_plus_le:
  assumes fin: "finite K" and nn: "nonneg_on K v" and k: "k \<in> K"
  shows "ahead K v k + v k \<le> total K v"
proof -
  have "ahead K v k + v k = (\<Sum>j\<in>insert k {j \<in> K. j < k}. v j)"
    using fin by (simp add: ahead_def add.commute)
  also have "\<dots> \<le> (\<Sum>j\<in>K. v j)"
    using fin k nn by (intro sum_mono2) (auto simp: nonneg_on_def)
  finally show ?thesis by (simp add: total_def)
qed

(* GATE:BEGIN LA2 *)
theorem in_priority_lawful:
  fixes K :: "'k::linorder set"
  assumes fin: "finite K"
  shows "lawful K (in_priority K)"
proof -
  have split: "total K (in_priority K v x) = x \<and> fits_in (in_priority K v x) v
                 \<and> nonneg_on K (in_priority K v x)"
    if nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v" for v x
  proof -
    have nnv: "\<forall>k. 0 \<le> v k" using nn by (simp add: nonneg_on_def)
    have "total K (in_priority K v x) = (\<Sum>k\<in>K. max 0 (min (v k) (x - ahead K v k)))"
      unfolding total_def in_priority_def by (intro sum.cong) simp_all
    also have "\<dots> = min x (total K v)"
      using in_priority_sum[OF nnv x0 fin] by (simp add: total_def)
    also have "\<dots> = x" using xv by simp
    finally have exact: "total K (in_priority K v x) = x" .
    have bounded: "fits_in (in_priority K v x) v"
      using nnv by (auto simp: fits_in_def in_priority_def)
    have nonneg: "nonneg_on K (in_priority K v x)"
      by (auto simp: nonneg_on_def in_priority_def)
    from exact bounded nonneg show ?thesis by blast
  qed
  have whole: "in_priority K v (total K v) = v" if nn: "nonneg_on K v" for v
  proof
    fix k
    show "in_priority K v (total K v) k = v k"
    proof (cases "k \<in> K")
      case True
      have "v k \<le> total K v - ahead K v k" using ahead_plus_le[OF fin nn True] by simp
      moreover have "0 \<le> v k" using nn by (simp add: nonneg_on_def)
      ultimately show ?thesis using True by (simp add: in_priority_def)
    next
      case False
      then show ?thesis using nn by (simp add: in_priority_def nonneg_on_def)
    qed
  qed
  show ?thesis unfolding lawful_def using split whole by blast
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

definition two_and_four :: "nat amounts" where
  "two_and_four = (\<lambda>k. if k = 0 then 2 else if k = 1 then 4 else 0)"

(* GATE:BEGIN LA4 *)
theorem lawful_rules_differ:
  "lawful {0, 1} (proportional {0::nat, 1}) \<and> lawful {0, 1} (in_priority {0::nat, 1})
   \<and> proportional {0, 1} two_and_four 3 0 = 1 \<and> in_priority {0, 1} two_and_four 3 0 = 2"
proof -
  have t: "total {0::nat, 1} two_and_four = 6" by (simp add: total_def two_and_four_def)
  have a: "ahead {0::nat, 1} two_and_four 0 = 0" by (simp add: ahead_def)
  show ?thesis
    using proportional_lawful[of "{0::nat, 1}"] in_priority_lawful[of "{0::nat, 1}"] t a
    by (simp add: proportional_def in_priority_def two_and_four_def)
qed
(* GATE:END *)


section \<open>Attribution across parties\<close>

(* GATE:BEGIN LC4 *)
theorem attribution_conserves:
  assumes finQ: "finite Q" and shares: "shares_ok Q (length ps) S"
  shows "(\<Sum>q\<in>Q. attributed K S ps q) = (\<Sum>i<length ps. total K (ps ! i))"
    and "(\<forall>i<length ps. 0 \<le> total K (ps ! i)) \<Longrightarrow> 0 \<le> attributed K S ps q"
proof -
  have "(\<Sum>q\<in>Q. attributed K S ps q) = (\<Sum>i<length ps. \<Sum>q\<in>Q. S i q * total K (ps ! i))"
    unfolding attributed_def by (rule sum.swap)
  also have "\<dots> = (\<Sum>i<length ps. (\<Sum>q\<in>Q. S i q) * total K (ps ! i))"
    by (simp add: sum_distrib_right)
  also have "\<dots> = (\<Sum>i<length ps. total K (ps ! i))"
    using shares by (intro sum.cong) (simp_all add: shares_ok_def)
  finally show "(\<Sum>q\<in>Q. attributed K S ps q) = (\<Sum>i<length ps. total K (ps ! i))" .
next
  assume "\<forall>i<length ps. 0 \<le> total K (ps ! i)"
  then show "0 \<le> attributed K S ps q"
    using shares unfolding attributed_def shares_ok_def
    by (auto intro!: sum_nonneg mult_nonneg_nonneg)
qed
(* GATE:END *)


section \<open>A threshold makes the residual fall as the amount drawn rises\<close>

definition threshold :: "amount \<Rightarrow> amount \<Rightarrow> amount" where
  "threshold t x = (if x \<le> t then 0 else x)"

(* GATE:BEGIN LN1 *)
theorem residual_falls_as_the_drawn_amount_rises:
  "(\<forall>x. 0 \<le> x \<longrightarrow> 0 \<le> threshold 10 x \<and> threshold 10 x \<le> x)
   \<and> 11 - threshold 10 11 < 10 - threshold 10 (10::amount)"
  by (simp add: threshold_def)
(* GATE:END *)

end
