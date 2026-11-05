(* SPDX-License-Identifier: MPL-2.0 *)

(* Ledger: a draw succeeds or fails whole, balances stay non-negative, conservation, draws at one
   position settled independently of the order of proposal, and a pro-rata split that conserves
   its total through rounding with a bounded residual.
   Source: the laws track E's plan names for E4a (docs/developer/plans/formal-methods-track-e.md
   section 1) and ADR-A131. A spike, not yet aligned to the formal-methods track. *)

theory Ledger
imports Main
begin

section \<open>Draws\<close>

text \<open>A draw names an account and an amount. It succeeds whole when the account's balance
covers it and fails whole otherwise, leaving every balance as it was. This differs from
Quantification's truncated difference, which absorbs an excess silently.\<close>

record 'a draw =
  acct :: 'a
  amount :: int

type_synonym 'a balances = "'a \<Rightarrow> int"

definition apply_draw :: "'a balances \<Rightarrow> 'a draw \<Rightarrow> 'a balances \<times> bool" where
  "apply_draw b d =
     (if 0 \<le> amount d \<and> amount d \<le> b (acct d)
      then (b(acct d := b (acct d) - amount d), True)
      else (b, False))"

lemma draw_succeeds_whole:
  "apply_draw b d = (b', True) \<Longrightarrow> b' (acct d) = b (acct d) - amount d \<and> (\<forall>a. a \<noteq> acct d \<longrightarrow> b' a = b a)"
  by (auto simp: apply_draw_def split: if_splits)

lemma draw_fails_whole:
  "apply_draw b d = (b', False) \<Longrightarrow> b' = b"
  by (auto simp: apply_draw_def split: if_splits)

lemma draw_keeps_nonneg:
  "(\<forall>a. 0 \<le> b a) \<Longrightarrow> apply_draw b d = (b', ok) \<Longrightarrow> \<forall>a. 0 \<le> b' a"
  by (auto simp: apply_draw_def split: if_splits)

section \<open>Settling a sequence of draws\<close>

fun settle :: "'a balances \<Rightarrow> 'a draw list \<Rightarrow> 'a balances \<times> 'a draw list" where
  "settle b [] = (b, [])"
| "settle b (d # ds) =
     (let (b1, ok) = apply_draw b d; (b2, succ) = settle b1 ds
      in (b2, if ok then d # succ else succ))"

lemma settle_nonneg:
  "(\<forall>a. 0 \<le> b a) \<Longrightarrow> settle b ds = (b', succ) \<Longrightarrow> \<forall>a. 0 \<le> b' a"
proof (induction ds arbitrary: b b' succ)
  case Nil
  then show ?case by simp
next
  case (Cons d ds)
  obtain b1 ok where s1: "apply_draw b d = (b1, ok)" by (cases "apply_draw b d")
  obtain b2 succ2 where s2: "settle b1 ds = (b2, succ2)" by (cases "settle b1 ds")
  have "\<forall>a. 0 \<le> b1 a" using draw_keeps_nonneg[OF Cons.prems(1) s1] .
  then have "\<forall>a. 0 \<le> b2 a" using Cons.IH s2 by blast
  moreover have "b' = b2" using Cons.prems(2) s1 s2 by simp
  ultimately show ?case by simp
qed

text \<open>Conservation: what an account lost is exactly the sum of the draws that succeeded against
it. A failed draw moved nothing.\<close>

definition drawn :: "'a \<Rightarrow> 'a draw list \<Rightarrow> int" where
  "drawn a ds = sum_list (map amount (filter (\<lambda>d. acct d = a) ds))"

theorem settle_conserves:
  "settle b ds = (b', succ) \<Longrightarrow> b a - b' a = drawn a succ"
proof (induction ds arbitrary: b b' succ)
  case Nil
  then show ?case by (simp add: drawn_def)
next
  case (Cons d ds)
  obtain b1 ok where s1: "apply_draw b d = (b1, ok)" by (cases "apply_draw b d")
  obtain b2 succ2 where s2: "settle b1 ds = (b2, succ2)" by (cases "settle b1 ds")
  have out: "b' = b2" "succ = (if ok then d # succ2 else succ2)" using Cons.prems s1 s2 by simp_all
  have ih: "b1 a - b2 a = drawn a succ2" using Cons.IH s2 by blast
  show ?case
  proof (cases ok)
    case True
    have ds: "b1 (acct d) = b (acct d) - amount d \<and> (\<forall>x. x \<noteq> acct d \<longrightarrow> b1 x = b x)"
      using draw_succeeds_whole[of b d b1] s1 True by simp
    then show ?thesis using ih out True by (cases "a = acct d") (auto simp: drawn_def)
  next
    case False
    have "b1 = b" using draw_fails_whole[of b d b1] s1 False by simp
    then show ?thesis using ih out False by (simp add: drawn_def)
  qed
qed

text \<open>The succeeded draws are a sub-sequence of the proposed ones.\<close>

lemma settle_done_subset: "settle b ds = (b', succ) \<Longrightarrow> set succ \<subseteq> set ds"
proof (induction ds arbitrary: b b' succ)
  case Nil
  then show ?case by simp
next
  case (Cons d ds)
  obtain b1 ok where s1: "apply_draw b d = (b1, ok)" by (cases "apply_draw b d")
  obtain b2 succ2 where s2: "settle b1 ds = (b2, succ2)" by (cases "settle b1 ds")
  show ?case using Cons.prems Cons.IH[OF s2] s1 s2 by (auto split: if_splits)
qed

section \<open>Draws at one position, independent of the order of proposal\<close>

text \<open>Draws proposed at one position are settled in the order of their keys, never in the order
they arrived. Two proposals of the same draws in any order settle to the same balances and the
same set of successes.\<close>

definition settle_at_position :: "'a balances \<Rightarrow> (nat \<Rightarrow> 'a draw) \<Rightarrow> nat list \<Rightarrow> 'a balances \<times> 'a draw list" where
  "settle_at_position b draw_of keys = settle b (map draw_of (sort keys))"

theorem order_independent:
  assumes "distinct keys" and "distinct keys'" and "set keys = set keys'"
  shows "settle_at_position b draw_of keys = settle_at_position b draw_of keys'"
proof -
  have "sort keys = sort keys'"
    using assms by (intro sorted_distinct_set_unique) simp_all
  then show ?thesis unfolding settle_at_position_def by simp
qed

section \<open>Pro-rata split: conservation after rounding\<close>

text \<open>A total is split across weights by integer division, each part rounded down, and the
residual is what the rounding left. The parts and the residual sum to the total, and the residual
is less than the number of parts, so it can be allocated to one of them without exceeding its
exact share by a whole unit.\<close>

definition parts :: "int \<Rightarrow> int list \<Rightarrow> int list" where
  "parts t ws = map (\<lambda>w. (t * w) div sum_list ws) ws"

definition residual :: "int \<Rightarrow> int list \<Rightarrow> int" where
  "residual t ws = t - sum_list (parts t ws)"

lemma split_conserves: "sum_list (parts t ws) + residual t ws = t"
  by (simp add: residual_def)

lemma mods_identity:
  fixes W :: int
  shows "sum_list (map (\<lambda>w. (t * w) mod W) ws) = t * sum_list ws - W * sum_list (map (\<lambda>w. (t * w) div W) ws)"
proof (induction ws)
  case Nil
  then show ?case by simp
next
  case (Cons w ws)
  have "(t * w) mod W = t * w - W * ((t * w) div W)"
    by (simp add: minus_mult_div_eq_mod[symmetric])
  then show ?case using Cons by (simp add: algebra_simps)
qed

lemma mods_nonneg:
  fixes W :: int
  assumes "0 < W"
  shows "0 \<le> sum_list (map (\<lambda>w. (t * w) mod W) ws)"
  using assms by (induction ws) (auto simp: pos_mod_sign)

lemma mods_bound:
  fixes W :: int
  assumes "0 < W"
  shows "sum_list (map (\<lambda>w. (t * w) mod W) ws) \<le> int (length ws) * (W - 1)"
  using assms
proof (induction ws)
  case Nil
  then show ?case by simp
next
  case (Cons w ws)
  have "(t * w) mod W \<le> W - 1" using Cons.prems pos_mod_bound[of W "t * w"] by simp
  then show ?case using Cons by (simp add: algebra_simps)
qed

theorem residual_bounds:
  assumes W: "0 < sum_list ws"
  shows "0 \<le> residual t ws \<and> residual t ws < int (length ws)"
proof -
  let ?W = "sum_list ws"
  have ident: "?W * residual t ws = sum_list (map (\<lambda>w. (t * w) mod ?W) ws)"
    unfolding residual_def parts_def using mods_identity[of t ?W ws] by (simp add: algebra_simps)
  have lo: "0 \<le> ?W * residual t ws" using ident mods_nonneg[OF W] by simp
  have hi: "?W * residual t ws \<le> int (length ws) * (?W - 1)" using ident mods_bound[OF W] by simp
  have "0 \<le> residual t ws" using lo W by (simp add: zero_le_mult_iff)
  moreover have "residual t ws < int (length ws)"
  proof (rule ccontr)
    assume "\<not> residual t ws < int (length ws)"
    then have "int (length ws) \<le> residual t ws" by simp
    then have "?W * int (length ws) \<le> ?W * residual t ws" using W by (simp add: mult_left_mono)
    with hi have "?W * int (length ws) \<le> int (length ws) * (?W - 1)" by simp
    then have "int (length ws) \<le> 0" by (simp add: algebra_simps)
    moreover have "0 < length ws" using W by (cases ws) auto
    ultimately show False by simp
  qed
  ultimately show ?thesis by simp
qed

end
