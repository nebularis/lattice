(* SPDX-License-Identifier: MPL-2.0 *)

(* Ranks on the target kernel (plan ledger, LG-20, the second group): a renaming of the keys that
   carries the ranks carries the result, distinct ranks are priority and never consult the rule for
   a tie, one rank is the rule for a tie, by rank rations and is lawful wherever the rule for a tie
   is, a request cut short leaves every later rank nothing, and where no tie arises the rule for a
   tie is never read. Hand-written on the Kernel extracted from ontology/ledger/README.md
   section 10. *)

theory Ranks
imports Predicates
begin

section \<open>Examples, before any theorem\<close>

text \<open>Requests of 5, 5 and 3 at ranks 0, 0 and 1 share 8. The first rank does not fit and shares 8
  by the proportional rule for a tie, 4 and 4, and the second rank is granted nothing. With 12 the
  first rank fits and the second takes the 2 left.\<close>

value "(map (by_rank (\<lambda>k. if k = 3 then 1 else 0) proportional {1, 2, 3::nat} (\<lambda>k. if k = 3 then 3 else 5) (8::rat)) [1, 2, 3],
        map (by_rank (\<lambda>k. if k = 3 then 1 else 0) proportional {1, 2, 3::nat} (\<lambda>k. if k = 3 then 3 else 5) (12::rat)) [1, 2, 3])"

lemma example_ranks_in_turn:
  "map (by_rank (\<lambda>k. if k = 3 then 1 else 0) proportional {1, 2, 3::nat} (\<lambda>k. if k = 3 then 3 else 5) (8::rat)) [1, 2, 3] = [4, 4, 0]
   \<and> map (by_rank (\<lambda>k. if k = 3 then 1 else 0) proportional {1, 2, 3::nat} (\<lambda>k. if k = 3 then 3 else 5) (12::rat)) [1, 2, 3] = [5, 5, 2]"
  by code_simp


section \<open>Distinct ranks are priority, and never consult the rule for a tie\<close>

(* GATE:BEGIN LK2 *)
theorem distinct_ranks_are_priority:
  assumes inj: "inj_on rank K"
  shows "by_rank rank tr K v x = by_rank rank tr' K v x"
    and "k \<in> K \<Longrightarrow> 0 \<le> v k \<Longrightarrow> by_rank rank tr K v x k = max 0 (min (v k) (x - ahead K rank v k))"
proof -
  show "by_rank rank tr K v x = by_rank rank tr' K v x"
  proof
    fix k
    show "by_rank rank tr K v x k = by_rank rank tr' K v x k"
      by (cases "k \<in> K") (simp_all add: by_rank_def Let_def beside_injective[OF inj])
  qed
  show "k \<in> K \<Longrightarrow> 0 \<le> v k \<Longrightarrow> by_rank rank tr K v x k = max 0 (min (v k) (x - ahead K rank v k))"
    by (rule by_rank_injective[OF inj])
qed
(* GATE:END *)


section \<open>Where no tie arises the rule for a tie is never read\<close>

(* GATE:BEGIN LT4 *)
theorem no_tie_no_tie_rule:
  assumes "\<not> tie_arises K rank v x"
  shows "by_rank rank tr K v x = by_rank rank tr' K v x"
proof
  fix k
  show "by_rank rank tr K v x k = by_rank rank tr' K v x k"
    using assms by (cases "k \<in> K") (auto simp: by_rank_def Let_def tie_arises_def)
qed
(* GATE:END *)


section \<open>One rank is the rule for a tie\<close>

(* GATE:BEGIN LT1 *)
theorem one_rank_is_the_tie_rule:
  assumes fin: "finite K" and one: "\<forall>k\<in>K. rank k = r" and ok: "lawful K (tr K)"
      and nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
  shows "by_rank rank tr K v x = tr K v x"
proof
  fix k
  have restrict: "(\<lambda>j. if j \<in> K then v j else 0) = v"
  proof
    fix j
    show "(if j \<in> K then v j else 0) = v j" using nn by (cases "j \<in> K") (simp_all add: nonneg_on_def)
  qed
  have ah: "ahead K rank v k = 0" if "k \<in> K" for k
  proof -
    have "{j\<in>K. rank j < rank k} = {}" using one that by auto
    then show ?thesis unfolding ahead_def by (simp only: sum.empty)
  qed
  have bs: "beside K rank k = K" if "k \<in> K" for k using one that by (auto simp: beside_def)
  show "by_rank rank tr K v x k = tr K v x k"
  proof (cases "k \<in> K")
    case False
    have "nonneg_on K (tr K v x)" by (rule lawful_nonneg[OF ok nn x0 xv])
    then show ?thesis using False by (simp add: by_rank_def nonneg_on_def)
  next
    case True
    show ?thesis
    proof (cases "total K v \<le> x")
      case True
      then have "x = total K v" using xv by simp
      then show ?thesis using \<open>k \<in> K\<close> lawful_whole[OF ok nn] by (simp add: by_rank_def Let_def ah bs)
    next
      case nf: False
      show ?thesis
      proof (cases "x \<le> 0")
        case True
        then have "x = 0" using x0 by simp
        then have "tr K v x = nothing" using lawful_split_of_zero[OF fin ok nn] by simp
        then show ?thesis using \<open>k \<in> K\<close> nf \<open>x = 0\<close> by (simp add: by_rank_def Let_def ah bs nothing_def)
      next
        case xp: False
        show ?thesis
        proof (cases "K = {k}")
          case True
          have "total K (tr K v x) = x" by (rule lawful_exact[OF ok nn x0 xv])
          then have trx: "tr K v x k = x" using True by (simp add: total_def)
          have "by_rank rank tr K v x k = x"
            using \<open>k \<in> K\<close> nf xp True unfolding by_rank_def Let_def ah[OF \<open>k \<in> K\<close>] bs[OF \<open>k \<in> K\<close>] by simp
          then show ?thesis using trx by simp
        next
          case False
          then show ?thesis using \<open>k \<in> K\<close> nf xp by (simp add: by_rank_def Let_def ah bs restrict)
        qed
      qed
    qed
  qed
qed
(* GATE:END *)


section \<open>A request cut short leaves every later rank nothing\<close>

lemma ahead_beside_le_ahead:
  assumes fin: "finite K" and nn: "\<forall>k. 0 \<le> v k" and lt: "rank k < rank j"
  shows "ahead K rank v k + total (beside K rank k) v \<le> ahead K rank v j"
proof -
  have d: "{i\<in>K. rank i < rank k} \<inter> beside K rank k = {}" by (auto simp: beside_def)
  have u: "{i\<in>K. rank i < rank k} \<union> beside K rank k \<subseteq> {i\<in>K. rank i < rank j}"
    using lt by (auto simp: beside_def)
  have "ahead K rank v k + total (beside K rank k) v = (\<Sum>i\<in>{i\<in>K. rank i < rank k} \<union> beside K rank k. v i)"
    using fin d by (simp add: ahead_def total_def beside_def sum.union_disjoint)
  also have "\<dots> \<le> (\<Sum>i\<in>{i\<in>K. rank i < rank j}. v i)"
    using fin u nn by (intro sum_mono2) auto
  finally show ?thesis by (simp add: ahead_def)
qed

lemma total_nonneg_any: "\<forall>k. 0 \<le> v k \<Longrightarrow> 0 \<le> total G v"
  by (simp add: total_def sum_nonneg)

lemma by_rank_short:
  assumes k: "k \<in> K" and less: "by_rank rank tr K v x k < v k"
  shows "x - ahead K rank v k < total (beside K rank k) v"
  using k less by (auto simp: by_rank_def Let_def split: if_splits)

lemma by_rank_left_negative:
  assumes nn: "\<forall>k. 0 \<le> v k" and left: "x - ahead K rank v j < 0"
  shows "by_rank rank tr K v x j = 0"
proof -
  have "0 \<le> total (beside K rank j) v" using nn by (rule total_nonneg_any)
  then show ?thesis using left by (auto simp: by_rank_def Let_def)
qed

(* GATE:BEGIN LT3 *)
theorem cut_short_leaves_later_ranks_nothing:
  assumes fin: "finite K" and nn: "\<forall>k. 0 \<le> v k" and k: "k \<in> K"
      and less: "by_rank rank tr K v x k < v k" and later: "rank k < rank j"
  shows "by_rank rank tr K v x j = 0"
proof -
  have "x - ahead K rank v k < total (beside K rank k) v" by (rule by_rank_short[OF k less])
  moreover have "ahead K rank v k + total (beside K rank k) v \<le> ahead K rank v j"
    by (rule ahead_beside_le_ahead[OF fin nn later])
  ultimately have "x - ahead K rank v j < 0" by simp
  then show ?thesis by (rule by_rank_left_negative[OF nn])
qed
(* GATE:END *)


section \<open>By rank rations, and is lawful, wherever the rule for a tie is\<close>

text \<open>The first rank whose requests do not fit is where by rank may differ from granting whole.
  Every earlier rank is granted whole, what the earlier ranks ask is within the amount, and every
  later rank is granted nothing.\<close>

definition fits_at :: "'k set \<Rightarrow> ('k \<Rightarrow> nat) \<Rightarrow> ('k, 'n::linordered_idom) amounts \<Rightarrow> 'n \<Rightarrow> 'k \<Rightarrow> bool" where
  "fits_at K rank v x k \<longleftrightarrow> total (beside K rank k) v \<le> x - ahead K rank v k"

lemma by_rank_fits: "k \<in> K \<Longrightarrow> fits_at K rank v x k \<Longrightarrow> by_rank rank tr K v x k = v k"
  by (simp add: by_rank_def Let_def fits_at_def)

lemma ahead_split:
  assumes fin: "finite K" and j: "j \<in> K" and between: "\<forall>i\<in>K. rank i < rank k \<longrightarrow> rank i \<le> rank j"
      and lt: "rank j < rank k"
  shows "ahead K rank v k = ahead K rank v j + total (beside K rank j) v"
proof -
  have e: "{i\<in>K. rank i < rank k} = {i\<in>K. rank i < rank j} \<union> beside K rank j"
    using between lt by (auto simp: beside_def)
  have d: "{i\<in>K. rank i < rank j} \<inter> beside K rank j = {}" by (auto simp: beside_def)
  show ?thesis unfolding ahead_def total_def e using fin d by (simp add: beside_def sum.union_disjoint)
qed

lemma first_misfit:
  assumes fin: "finite K" and nn: "\<forall>k. 0 \<le> v k" and x0: "0 \<le> x"
      and k0: "k0 \<in> K" and least: "\<forall>j\<in>K. rank j < rank k0 \<longrightarrow> fits_at K rank v x j"
  shows "ahead K rank v k0 \<le> x"
proof (cases "{j\<in>K. rank j < rank k0} = {}")
  case True
  then have "ahead K rank v k0 = 0" unfolding ahead_def by (simp only: sum.empty)
  then show ?thesis using x0 by simp
next
  case False
  let ?L = "{j\<in>K. rank j < rank k0}"
  have finL: "finite (rank ` ?L)" using fin by simp
  have ne: "rank ` ?L \<noteq> {}" using False by simp
  obtain j where j: "j \<in> ?L" and jmax: "rank j = Max (rank ` ?L)"
    using Max_in[OF finL ne] by auto
  have between: "\<forall>i\<in>K. rank i < rank k0 \<longrightarrow> rank i \<le> rank j"
    using jmax finL by (auto intro: Max_ge)
  have jK: "j \<in> K" and lt: "rank j < rank k0" using j by simp_all
  have "ahead K rank v k0 = ahead K rank v j + total (beside K rank j) v"
    by (rule ahead_split[OF fin jK between lt])
  also have "\<dots> \<le> x"
  proof -
    have "fits_at K rank v x j" using least jK lt by blast
    then have "total (beside K rank j) v \<le> x - ahead K rank v j" by (simp add: fits_at_def)
    then show ?thesis by simp
  qed
  finally show ?thesis .
qed

lemma by_rank_sum_split:
  assumes fin: "finite K" and nn: "\<forall>k. 0 \<le> v k" and x0: "0 \<le> x"
      and k0: "k0 \<in> K" and bad: "\<not> fits_at K rank v x k0"
      and least: "\<forall>j\<in>K. rank j < rank k0 \<longrightarrow> fits_at K rank v x j"
  shows "total K (by_rank rank tr K v x) = ahead K rank v k0 + total (beside K rank k0) (by_rank rank tr K v x)"
proof -
  let ?g = "by_rank rank tr K v x"
  let ?L = "{j\<in>K. rank j < rank k0}"
  let ?G = "beside K rank k0"
  let ?H = "{j\<in>K. rank k0 < rank j}"
  have part: "K = ?L \<union> ?G \<union> ?H" by (auto simp: beside_def)
  have d1: "?L \<inter> ?G = {}" and d2: "(?L \<union> ?G) \<inter> ?H = {}" by (auto simp: beside_def)
  have L: "(\<Sum>j\<in>?L. ?g j) = ahead K rank v k0"
    unfolding ahead_def using least by (intro sum.cong) (auto intro: by_rank_fits)
  have H: "(\<Sum>j\<in>?H. ?g j) = 0"
  proof (rule sum.neutral, rule ballI)
    fix j
    assume "j \<in> ?H"
    then have jK: "j \<in> K" and lt: "rank k0 < rank j" by simp_all
    have "x - ahead K rank v k0 < total ?G v" using bad by (simp add: fits_at_def)
    moreover have "ahead K rank v k0 + total ?G v \<le> ahead K rank v j"
      by (rule ahead_beside_le_ahead[OF fin nn lt])
    ultimately have "x - ahead K rank v j < 0" by simp
    then show "?g j = 0" by (rule by_rank_left_negative[OF nn])
  qed
  have finL: "finite ?L" and finG: "finite ?G" and finH: "finite ?H" using fin by (simp_all add: beside_def)
  have "total K ?g = (\<Sum>j\<in>?L \<union> ?G \<union> ?H. ?g j)" using part by (simp add: total_def)
  also have "\<dots> = (\<Sum>j\<in>?L. ?g j) + (\<Sum>j\<in>?G. ?g j) + (\<Sum>j\<in>?H. ?g j)"
    using finL finG finH d1 d2 by (simp add: sum.union_disjoint)
  finally show ?thesis using L H by (simp add: total_def)
qed

lemma tie_group_grants:
  fixes tr :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule"
  assumes fin: "finite K" and nn: "\<forall>k. 0 \<le> v k" and k0: "k0 \<in> K" and bad: "\<not> fits_at K rank v x k0"
      and left0: "0 \<le> x - ahead K rank v k0"
  shows "rations (beside K rank k0) (tr (beside K rank k0)) \<Longrightarrow>
           total (beside K rank k0) (by_rank rank tr K v x) \<le> x - ahead K rank v k0"
    and "exact (beside K rank k0) (tr (beside K rank k0)) \<Longrightarrow>
           total (beside K rank k0) (by_rank rank tr K v x) = x - ahead K rank v k0"
    and "\<not> tie_arises K rank v x \<Longrightarrow>
           total (beside K rank k0) (by_rank rank tr K v x) = x - ahead K rank v k0"
proof -
  let ?G = "beside K rank k0"
  let ?l = "x - ahead K rank v k0"
  let ?w = "\<lambda>j. if j \<in> ?G then v j else 0"
  have same: "ahead K rank v j = ahead K rank v k0" "beside K rank j = ?G" if "j \<in> ?G" for j
    using that by (auto simp: ahead_def beside_def)
  have k0G: "k0 \<in> ?G" using k0 by (simp add: beside_def)
  have nf: "\<not> total ?G v \<le> ?l" using bad by (simp add: fits_at_def)
  have finG: "finite ?G" using fin by (simp add: beside_def)
  have Gsub: "?G \<subseteq> K" by (auto simp: beside_def)
  have on: "\<forall>j\<in>?G. by_rank rank tr K v x j
              = (if ?l \<le> 0 then 0 else if ?G = {j} then ?l else tr ?G ?w ?l j)"
    using same nf Gsub by (auto simp: by_rank_def Let_def)
  have wnn: "nonneg_on ?G ?w" using nn by (simp add: nonneg_on_def)
  have wt: "total ?G ?w = total ?G v" by (simp add: total_def)
  have lw: "?l \<le> total ?G ?w" using nf wt by simp
  have zero: "total ?G (by_rank rank tr K v x) = 0" if "?l \<le> 0"
    using on that by (simp add: total_def)
  have single: "total ?G (by_rank rank tr K v x) = ?l" if "\<not> ?l \<le> 0" "?G = {k0}"
    using on that k0G by (simp add: total_def)
  have tie: "total ?G (by_rank rank tr K v x) = total ?G (tr ?G ?w ?l)" if "\<not> ?l \<le> 0" "?G \<noteq> {k0}"
  proof -
    have "?G \<noteq> {j}" if "j \<in> ?G" for j
    proof
      assume "?G = {j}"
      then have "j = k0" using k0G by auto
      then show False using \<open>?G = {j}\<close> \<open>?G \<noteq> {k0}\<close> by simp
    qed
    then show ?thesis using on \<open>\<not> ?l \<le> 0\<close> unfolding total_def by (intro sum.cong) auto
  qed
  show "rations ?G (tr ?G) \<Longrightarrow> total ?G (by_rank rank tr K v x) \<le> ?l"
  proof -
    assume ok: "rations ?G (tr ?G)"
    have le_tie: "total ?G (tr ?G ?w ?l) \<le> ?l" using rations_parts(3)[OF ok wnn left0 lw] .
    show ?thesis using zero single tie le_tie left0 by (cases "?l \<le> 0"; cases "?G = {k0}") auto
  qed
  show "exact ?G (tr ?G) \<Longrightarrow> total ?G (by_rank rank tr K v x) = ?l"
  proof -
    assume ex: "exact ?G (tr ?G)"
    have "residual ?G (tr ?G) ?w ?l = 0" using ex wnn left0 lw by (simp add: exact_def)
    then have "total ?G (tr ?G ?w ?l) = ?l" by (simp add: residual_def)
    then show ?thesis using zero single tie left0 by (cases "?l \<le> 0"; cases "?G = {k0}") auto
  qed
  show "\<not> tie_arises K rank v x \<Longrightarrow> total ?G (by_rank rank tr K v x) = ?l"
  proof -
    assume nt: "\<not> tie_arises K rank v x"
    have "\<not> (0 < ?l \<and> ?l < total ?G v \<and> ?G \<noteq> {k0})" using nt k0 unfolding tie_arises_def by blast
    then have disj: "?l \<le> 0 \<or> ?G = {k0}" using nf by auto
    show ?thesis
    proof (cases "?l \<le> 0")
      case True
      then have "?l = 0" using left0 by simp
      then show ?thesis using zero True by simp
    next
      case False
      then show ?thesis using single disj by simp
    qed
  qed
qed

lemma by_rank_bounds:
  fixes tr :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule"
  assumes fin: "finite K" and nn: "nonneg_on K v" and x0: "0 \<le> x"
      and ok: "\<forall>G\<subseteq>K. rations G (tr G)"
  shows "nonneg_on K (by_rank rank tr K v x) \<and> fits_in (by_rank rank tr K v x) v"
proof -
  have nnv: "\<forall>k. 0 \<le> v k" using nn by (simp add: nonneg_on_def)
  have each: "0 \<le> by_rank rank tr K v x k \<and> by_rank rank tr K v x k \<le> v k" for k
  proof (cases "k \<in> K")
    case False
    then show ?thesis using nnv by (simp add: by_rank_def)
  next
    case True
    let ?G = "beside K rank k"
    let ?l = "x - ahead K rank v k"
    let ?w = "\<lambda>j. if j \<in> ?G then v j else 0"
    show ?thesis
    proof (cases "total ?G v \<le> ?l")
      case True
      then show ?thesis using \<open>k \<in> K\<close> nnv by (simp add: by_rank_def Let_def)
    next
      case nf: False
      show ?thesis
      proof (cases "?l \<le> 0")
        case True
        then show ?thesis using \<open>k \<in> K\<close> nf nnv by (simp add: by_rank_def Let_def)
      next
        case lp: False
        show ?thesis
        proof (cases "?G = {k}")
          case True
          then have "total ?G v = v k" by (simp add: total_def)
          then show ?thesis using \<open>k \<in> K\<close> nf lp True by (simp add: by_rank_def Let_def)
        next
          case False
          have Gs: "?G \<subseteq> K" by (auto simp: beside_def)
          have kG: "k \<in> ?G" using \<open>k \<in> K\<close> by (simp add: beside_def)
          have wnn: "nonneg_on ?G ?w" using nnv by (simp add: nonneg_on_def)
          have lw: "?l \<le> total ?G ?w" using nf by (simp add: total_def)
          have t: "nonneg_on ?G (tr ?G ?w ?l) \<and> fits_in (tr ?G ?w ?l) ?w"
            using rations_parts[OF ok[rule_format, OF Gs] wnn _ lw] lp by simp
          have "by_rank rank tr K v x k = tr ?G ?w ?l k" using \<open>k \<in> K\<close> nf lp False by (simp add: by_rank_def Let_def)
          moreover have "0 \<le> tr ?G ?w ?l k" using t by (simp add: nonneg_on_def)
          moreover have "tr ?G ?w ?l k \<le> ?w k" using t by (simp add: fits_in_def)
          moreover have "?w k = v k" using kG by simp
          ultimately show ?thesis by simp
        qed
      qed
    qed
  qed
  have off: "by_rank rank tr K v x k = 0" if "k \<notin> K" for k using that by (simp add: by_rank_def)
  show ?thesis using each off by (simp add: nonneg_on_def fits_in_def)
qed

lemma by_rank_all_fit:
  assumes fin: "finite K" and nn: "nonneg_on K v"
      and all: "\<forall>j\<in>K. fits_at K rank v x j" and ne: "K \<noteq> {}"
  shows "by_rank rank tr K v x = v" and "total K v \<le> x"
proof -
  show "by_rank rank tr K v x = v"
  proof
    fix k
    show "by_rank rank tr K v x k = v k"
    proof (cases "k \<in> K")
      case True
      then show ?thesis using all by (intro by_rank_fits) auto
    next
      case False
      then show ?thesis using nn by (simp add: by_rank_def nonneg_on_def)
    qed
  qed
  have finR: "finite (rank ` K)" using fin by simp
  have neR: "rank ` K \<noteq> {}" using ne by simp
  from Max_in[OF finR neR] obtain j where j: "j \<in> K" and jmax: "Max (rank ` K) = rank j" by blast
  have top: "\<forall>i\<in>K. rank i \<le> rank j"
  proof
    fix i
    assume "i \<in> K"
    then have "rank i \<le> Max (rank ` K)" using finR by (intro Max_ge) auto
    then show "rank i \<le> rank j" using jmax by simp
  qed
  have e: "K = {i\<in>K. rank i < rank j} \<union> beside K rank j" using top by (auto simp: beside_def)
  have d: "{i\<in>K. rank i < rank j} \<inter> beside K rank j = {}" by (auto simp: beside_def)
  have "total K v = ahead K rank v j + total (beside K rank j) v"
    unfolding total_def ahead_def using fin d by (subst e) (simp add: beside_def sum.union_disjoint)
  also have "\<dots> \<le> x"
  proof -
    have "total (beside K rank j) v \<le> x - ahead K rank v j" using all j by (simp add: fits_at_def)
    then show ?thesis by simp
  qed
  finally show "total K v \<le> x" .
qed

lemma first_misfit_exists:
  assumes fin: "finite K" and some: "\<exists>k\<in>K. \<not> fits_at K rank v x k"
  obtains k0 where "k0 \<in> K" "\<not> fits_at K rank v x k0" "\<forall>j\<in>K. rank j < rank k0 \<longrightarrow> fits_at K rank v x j"
proof -
  let ?B = "{k\<in>K. \<not> fits_at K rank v x k}"
  have finB: "finite (rank ` ?B)" using fin by simp
  have ne: "rank ` ?B \<noteq> {}" using some by auto
  obtain k0 where k0: "k0 \<in> ?B" and kmin: "rank k0 = Min (rank ` ?B)" using Min_in[OF finB ne] by auto
  have "\<forall>j\<in>K. rank j < rank k0 \<longrightarrow> fits_at K rank v x j"
  proof (intro ballI impI)
    fix j
    assume "j \<in> K" "rank j < rank k0"
    show "fits_at K rank v x j"
    proof (rule ccontr)
      assume "\<not> fits_at K rank v x j"
      then have "rank k0 \<le> rank j" using kmin finB \<open>j \<in> K\<close> by (auto intro: Min_le)
      then show False using \<open>rank j < rank k0\<close> by simp
    qed
  qed
  then show ?thesis using that k0 by blast
qed

(* GATE:BEGIN LT2 *)
theorem by_rank_rations_where_the_tie_rule_does:
  fixes tr :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule"
  assumes fin: "finite K" and ok: "\<forall>G\<subseteq>K. rations G (tr G)"
  shows "rations K (by_rank rank tr K)"
    and "\<forall>G\<subseteq>K. lawful G (tr G) \<Longrightarrow> lawful K (by_rank rank tr K)"
proof -
  have split: "nonneg_on K (by_rank rank tr K v x) \<and> fits_in (by_rank rank tr K v x) v
                 \<and> total K (by_rank rank tr K v x) \<le> x
                 \<and> ((\<forall>G\<subseteq>K. lawful G (tr G)) \<longrightarrow> total K (by_rank rank tr K v x) = x)"
    if nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v" for v x
  proof -
    have nnv: "\<forall>k. 0 \<le> v k" using nn by (simp add: nonneg_on_def)
    have b: "nonneg_on K (by_rank rank tr K v x) \<and> fits_in (by_rank rank tr K v x) v"
      by (rule by_rank_bounds[OF fin nn x0 ok])
    show ?thesis
    proof (cases "\<exists>k\<in>K. \<not> fits_at K rank v x k")
      case True
      obtain k0 where k0: "k0 \<in> K" and bad: "\<not> fits_at K rank v x k0"
          and least: "\<forall>j\<in>K. rank j < rank k0 \<longrightarrow> fits_at K rank v x j"
        using first_misfit_exists[OF fin True] by blast
      have a0: "ahead K rank v k0 \<le> x" by (rule first_misfit[OF fin nnv x0 k0 least])
      have Gs: "beside K rank k0 \<subseteq> K" by (auto simp: beside_def)
      have l0: "0 \<le> x - ahead K rank v k0" using a0 by simp
      have tsplit: "total K (by_rank rank tr K v x)
                      = ahead K rank v k0 + total (beside K rank k0) (by_rank rank tr K v x)"
        by (rule by_rank_sum_split[OF fin nnv x0 k0 bad least])
      have le: "total (beside K rank k0) (by_rank rank tr K v x) \<le> x - ahead K rank v k0"
        by (rule tie_group_grants(1)[where tr = tr, OF fin nnv k0 bad l0 ok[rule_format, OF Gs]])
      have eq: "total (beside K rank k0) (by_rank rank tr K v x) = x - ahead K rank v k0"
        if "\<forall>G\<subseteq>K. lawful G (tr G)"
      proof -
        have "exact (beside K rank k0) (tr (beside K rank k0))" using that Gs by (simp add: lawful_def)
        then show ?thesis by (rule tie_group_grants(2)[where tr = tr, OF fin nnv k0 bad l0])
      qed
      show ?thesis using b tsplit le eq by simp
    next
      case False
      show ?thesis
      proof (cases "K = {}")
        case True
        then show ?thesis using b x0 xv by (simp add: total_def)
      next
        case ne: False
        have all: "\<forall>j\<in>K. fits_at K rank v x j" using False by blast
        have g: "by_rank rank tr K v x = v" and tv: "total K v \<le> x"
          using by_rank_all_fit[OF fin nn all ne] by simp_all
        show ?thesis using b g tv xv by simp
      qed
    qed
  qed
  have whole: "by_rank rank tr K v (total K v) = v" if nn: "nonneg_on K v" for v
  proof (cases "K = {}")
    case True
    then show ?thesis using nn by (auto simp: by_rank_def nonneg_on_def)
  next
    case ne: False
    have nnv: "\<forall>k. 0 \<le> v k" using nn by (simp add: nonneg_on_def)
    have "fits_at K rank v (total K v) j" if "j \<in> K" for j
    proof -
      have d: "{i\<in>K. rank i < rank j} \<inter> beside K rank j = {}" by (auto simp: beside_def)
      have "ahead K rank v j + total (beside K rank j) v = (\<Sum>i\<in>{i\<in>K. rank i < rank j} \<union> beside K rank j. v i)"
        using fin d by (simp add: ahead_def total_def beside_def sum.union_disjoint)
      also have "\<dots> \<le> total K v"
        unfolding total_def using fin nnv by (intro sum_mono2) (auto simp: beside_def)
      finally show ?thesis by (simp add: fits_at_def)
    qed
    then show ?thesis using by_rank_all_fit(1)[OF fin nn _ ne] by blast
  qed
  show "rations K (by_rank rank tr K)" unfolding rations_def using split whole by blast
  show "\<forall>G\<subseteq>K. lawful G (tr G) \<Longrightarrow> lawful K (by_rank rank tr K)"
  proof -
    assume lw: "\<forall>G\<subseteq>K. lawful G (tr G)"
    show "lawful K (by_rank rank tr K)"
    proof (rule lawfulI)
      fix v :: "('k, 'n) amounts" and x :: 'n
      assume "nonneg_on K v" "0 \<le> x" "x \<le> total K v"
      then have s: "nonneg_on K (by_rank rank tr K v x) \<and> fits_in (by_rank rank tr K v x) v
                 \<and> total K (by_rank rank tr K v x) \<le> x
                 \<and> ((\<forall>G\<subseteq>K. lawful G (tr G)) \<longrightarrow> total K (by_rank rank tr K v x) = x)"
        by (rule split)
      show "total K (by_rank rank tr K v x) = x \<and> fits_in (by_rank rank tr K v x) v
              \<and> nonneg_on K (by_rank rank tr K v x)"
        using s lw by simp
    next
      fix v :: "('k, 'n) amounts"
      assume "nonneg_on K v"
      then show "by_rank rank tr K v (total K v) = v" by (rule whole)
    qed
  qed
qed
(* GATE:END *)

text \<open>A merge with no rule for a tie, where no tie arises, leaves no residual.\<close>

lemma by_rank_exact_where_no_tie:
  fixes tr :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule"
  assumes fin: "finite K" and nn: "nonneg_on K v" and x0: "0 \<le> x" and xv: "x \<le> total K v"
      and nt: "\<not> tie_arises K rank v x"
  shows "total K (by_rank rank tr K v x) = x"
proof (cases "\<exists>k\<in>K. \<not> fits_at K rank v x k")
  case True
  have nnv: "\<forall>k. 0 \<le> v k" using nn by (simp add: nonneg_on_def)
  obtain k0 where k0: "k0 \<in> K" and bad: "\<not> fits_at K rank v x k0"
      and least: "\<forall>j\<in>K. rank j < rank k0 \<longrightarrow> fits_at K rank v x j"
    using first_misfit_exists[OF fin True] by blast
  have l0: "0 \<le> x - ahead K rank v k0" using first_misfit[OF fin nnv x0 k0 least] by simp
  have "total (beside K rank k0) (by_rank rank (\<lambda>_ _ _. nothing) K v x) = x - ahead K rank v k0"
    by (rule tie_group_grants(3)[where tr = "\<lambda>_ _ _. nothing", OF fin nnv k0 bad l0 nt])
  moreover have "by_rank rank tr K v x = by_rank rank (\<lambda>_ _ _. nothing) K v x"
    by (rule no_tie_no_tie_rule[OF nt])
  moreover have "total K (by_rank rank tr K v x)
                   = ahead K rank v k0 + total (beside K rank k0) (by_rank rank tr K v x)"
    by (rule by_rank_sum_split[OF fin nnv x0 k0 bad least])
  ultimately show ?thesis by simp
next
  case False
  show ?thesis
  proof (cases "K = {}")
    case True
    then show ?thesis using x0 xv by (simp add: total_def)
  next
    case ne: False
    have "by_rank rank tr K v x = v" and "total K v \<le> x"
      using by_rank_all_fit[OF fin nn _ ne] False by blast+
    then show ?thesis using xv by simp
  qed
qed


section \<open>A renaming of the keys that carries the ranks carries the result\<close>

lemma renamed_filter:
  assumes bij: "bij \<sigma>"
  shows "{j \<in> \<sigma> ` K. P (inv \<sigma> j)} = \<sigma> ` {j\<in>K. P j}"
proof -
  have inj: "inj \<sigma>" using bij by (simp add: bij_def)
  show ?thesis by (auto simp: inv_f_f[OF inj])
qed

lemma renamed_sum:
  assumes bij: "bij \<sigma>"
  shows "(\<Sum>j\<in>\<sigma> ` S. v (inv \<sigma> j)) = (\<Sum>j\<in>S. v j)"
proof -
  have inj: "inj_on \<sigma> S" by (rule inj_on_subset[OF bij_is_inj[OF bij]]) simp
  show ?thesis using sum.reindex[OF inj, of "\<lambda>j. v (inv \<sigma> j)"] bij by (simp add: bij_def inv_f_f)
qed

(* GATE:BEGIN LK *)
theorem renaming_carries_the_result:
  assumes bij: "bij \<sigma>"
      and eq: "\<forall>G w y k. tr' (\<sigma> ` G) (\<lambda>j. w (inv \<sigma> j)) y (\<sigma> k) = tr G w y k"
  shows "by_rank (\<lambda>j. rank (inv \<sigma> j)) tr' (\<sigma> ` K) (\<lambda>j. v (inv \<sigma> j)) x (\<sigma> k) = by_rank rank tr K v x k"
proof -
  have inj: "inj \<sigma>" using bij by (simp add: bij_def)
  have bk: "inv \<sigma> (\<sigma> j) = j" for j using inj by (simp add: inv_f_f)
  have mem: "\<sigma> k \<in> \<sigma> ` S \<longleftrightarrow> k \<in> S" for S using inj by (simp add: inj_image_mem_iff)
  have ah: "ahead (\<sigma> ` K) (\<lambda>j. rank (inv \<sigma> j)) (\<lambda>j. v (inv \<sigma> j)) (\<sigma> k) = ahead K rank v k"
    unfolding ahead_def bk renamed_filter[OF bij, of K "\<lambda>j. rank j < rank k"] by (rule renamed_sum[OF bij])
  have bs: "beside (\<sigma> ` K) (\<lambda>j. rank (inv \<sigma> j)) (\<sigma> k) = \<sigma> ` beside K rank k"
    unfolding beside_def bk by (rule renamed_filter[OF bij])
  have tot: "total (\<sigma> ` G) (\<lambda>j. v (inv \<sigma> j)) = total G v" for G
    unfolding total_def by (rule renamed_sum[OF bij])
  have single: "\<sigma> ` G = {\<sigma> k} \<longleftrightarrow> G = {k}" for G
    using inj_image_eq_iff[OF inj, of G "{k}"] by simp
  have memb: "j \<in> \<sigma> ` S \<longleftrightarrow> inv \<sigma> j \<in> S" for j S
  proof -
    have sj: "\<sigma> (inv \<sigma> j) = j" using bij by (simp add: bij_def surj_f_inv_f)
    have "j \<in> \<sigma> ` S \<longleftrightarrow> \<sigma> (inv \<sigma> j) \<in> \<sigma> ` S" using sj by simp
    also have "\<dots> \<longleftrightarrow> inv \<sigma> j \<in> S" by (rule inj_image_mem_iff[OF inj])
    finally show ?thesis .
  qed
  show ?thesis
    using eq[rule_format, of "beside K rank k" "\<lambda>i. if i \<in> beside K rank k then v i else 0" "x - ahead K rank v k" k]
    by (simp add: by_rank_def Let_def ah bs tot single bk memb)
qed
(* GATE:END *)

end
