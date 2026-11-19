(* SPDX-License-Identifier: MPL-2.0 *)

(* An amount, as ADR-A-FM2's addendum of 2026-11-18 states it: a number for each key, over a
   number type left generic. Each law names the weakest class it needs. Hand-written, in the
   shared session, LatticeShared. *)

theory Amounts
imports Main
begin

section \<open>An amount\<close>

text \<open>An amount gives a number for each key. The number type stays generic. A development that
  stores an amount and computes nothing with it reads it at any type. What adds and subtracts
  names a group, and what also compares names an ordered group.\<close>

type_synonym ('k, 'n) amounts = "'k \<Rightarrow> 'n"

definition amount_zero :: "('k, 'n::zero) amounts" where
  "amount_zero = (\<lambda>_. 0)"

definition amount_add :: "('k, 'n::plus) amounts \<Rightarrow> ('k, 'n) amounts \<Rightarrow> ('k, 'n) amounts" where
  "amount_add v w = (\<lambda>k. v k + w k)"

definition amount_diff :: "('k, 'n::minus) amounts \<Rightarrow> ('k, 'n) amounts \<Rightarrow> ('k, 'n) amounts" where
  "amount_diff v w = (\<lambda>k. v k - w k)"

definition amount_le :: "('k, 'n::ord) amounts \<Rightarrow> ('k, 'n) amounts \<Rightarrow> bool" where
  "amount_le v w \<longleftrightarrow> (\<forall>k. v k \<le> w k)"

definition amount_sum :: "'k set \<Rightarrow> ('k, 'n::comm_monoid_add) amounts \<Rightarrow> 'n" where
  "amount_sum K v = (\<Sum>k\<in>K. v k)"


section \<open>Adding and subtracting\<close>

(* GATE:BEGIN SA1 *)
theorem adding_amounts_is_a_commutative_monoid:
  fixes u v w :: "('k, 'n::comm_monoid_add) amounts"
  shows "amount_add v w = amount_add w v"
    and "amount_add (amount_add u v) w = amount_add u (amount_add v w)"
    and "amount_add amount_zero v = v"
  by (simp_all add: amount_add_def amount_zero_def ac_simps)
(* GATE:END *)

(* GATE:BEGIN SA2 *)
theorem subtracting_undoes_adding:
  fixes v w :: "('k, 'n::ab_group_add) amounts"
  shows "amount_diff (amount_add v w) w = v"
    and "amount_add (amount_diff v w) w = v"
    and "amount_diff v v = amount_zero"
  by (simp_all add: amount_add_def amount_diff_def amount_zero_def)
(* GATE:END *)


section \<open>Comparing\<close>

text \<open>Amounts are compared key by key. That order is partial, unlike the order of positions.\<close>

(* GATE:BEGIN SA3 *)
theorem amounts_are_partially_ordered:
  fixes u v w :: "('k, 'n::order) amounts"
  shows "amount_le v v"
    and "amount_le u v \<Longrightarrow> amount_le v w \<Longrightarrow> amount_le u w"
    and "amount_le v w \<Longrightarrow> amount_le w v \<Longrightarrow> v = w"
proof -
  show "amount_le v v" by (simp add: amount_le_def)
  show "amount_le u w" if uv: "amount_le u v" and vw: "amount_le v w"
    unfolding amount_le_def
  proof (intro allI)
    fix k
    have "u k \<le> v k" using uv by (simp add: amount_le_def)
    moreover have "v k \<le> w k" using vw by (simp add: amount_le_def)
    ultimately show "u k \<le> w k" by (rule order_trans)
  qed
  show "v = w" if vw: "amount_le v w" and wv: "amount_le w v"
  proof (rule ext)
    fix k
    have "v k \<le> w k" using vw by (simp add: amount_le_def)
    moreover have "w k \<le> v k" using wv by (simp add: amount_le_def)
    ultimately show "v k = w k" by (rule order_antisym)
  qed
qed
(* GATE:END *)

(* GATE:BEGIN SAn *)
theorem amounts_are_not_totally_ordered:
  "\<not> amount_le (\<lambda>k. if k then 1 else 0) (\<lambda>k. if k then 0 else (1::int))
   \<and> \<not> amount_le (\<lambda>k. if k then 0 else 1) (\<lambda>k. if k then 1 else (0::int))"
  by (simp add: amount_le_def all_bool_eq)
(* GATE:END *)

(* GATE:BEGIN SA4 *)
theorem adding_keeps_the_order:
  fixes u v w :: "('k, 'n::ordered_ab_semigroup_add) amounts"
  assumes "amount_le v w"
  shows "amount_le (amount_add v u) (amount_add w u)"
proof -
  have "v k \<le> w k" for k using assms by (simp add: amount_le_def)
  then show ?thesis by (simp add: amount_le_def amount_add_def add_right_mono)
qed

theorem within_is_a_difference_of_at_least_zero:
  fixes v w :: "('k, 'n::ordered_ab_group_add) amounts"
  shows "amount_le v w \<longleftrightarrow> amount_le amount_zero (amount_diff w v)"
  by (simp add: amount_le_def amount_diff_def amount_zero_def)
(* GATE:END *)


section \<open>A sum over a set of keys\<close>

(* GATE:BEGIN SA5 *)
theorem the_sum_adds:
  fixes v w :: "('k, 'n::comm_monoid_add) amounts"
  shows "amount_sum K (amount_add v w) = amount_sum K v + amount_sum K w"
    and "amount_sum K amount_zero = 0"
  by (simp_all add: amount_sum_def amount_add_def amount_zero_def sum.distrib)

theorem the_sum_keeps_the_order:
  fixes v w :: "('k, 'n::ordered_comm_monoid_add) amounts"
  assumes "amount_le v w"
  shows "amount_sum K v \<le> amount_sum K w"
proof -
  have "v k \<le> w k" for k using assms by (simp add: amount_le_def)
  then show ?thesis unfolding amount_sum_def by (intro sum_mono)
qed
(* GATE:END *)

end
