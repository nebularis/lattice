(* SPDX-License-Identifier: MPL-2.0 *)

(* Membership encoding: a version's members read back from a delta chain equal the full list,
   and no chain is longer than the checkpoint interval.
   Source: ontology/persistence/README.md section 5.6.11, ADR-A132. A spike, not yet aligned to the formal-methods track. *)

theory Membership
imports Main
begin

text \<open>A family that appends versions and lists many members per root version may store, for
each version, only what changed: the members added and dropped since the version before, with
a full list at every checkpoint. The first version is a checkpoint, and so is every version whose
sequence is a multiple of the interval. The members of a version are those listed at a version of
the chain back to the nearest checkpoint, by the property or by addsMember, and not dropped by a
later version of that chain. A member dropped and added again is a member.\<close>

locale membership =
  fixes full :: "nat \<Rightarrow> 'm set"
    and k :: nat
  assumes k_pos: "0 < k"
begin

definition is_checkpoint :: "nat \<Rightarrow> bool" where
  "is_checkpoint i \<longleftrightarrow> i mod k = 0"

definition adds :: "nat \<Rightarrow> 'm set" where
  "adds i = full i - full (i - 1)"

definition drops :: "nat \<Rightarrow> 'm set" where
  "drops i = full (i - 1) - full i"

text \<open>What the generated members query computes, walking the chain.\<close>

fun members :: "nat \<Rightarrow> 'm set" where
  "members 0 = full 0"
| "members (Suc i) = (if is_checkpoint (Suc i) then full (Suc i) else (members i - drops (Suc i)) \<union> adds (Suc i))"

lemma first_is_checkpoint: "is_checkpoint 0"
  by (simp add: is_checkpoint_def)

text \<open>The delta encoding loses nothing: every version's members read back exactly.\<close>

theorem members_exact: "members i = full i"
proof (induction i)
  case 0
  then show ?case by simp
next
  case (Suc i)
  show ?case
  proof (cases "is_checkpoint (Suc i)")
    case True
    then show ?thesis by simp
  next
    case False
    have "(full i - drops (Suc i)) \<union> adds (Suc i) = full (Suc i)"
      unfolding drops_def adds_def by auto
    with False Suc.IH show ?thesis by simp
  qed
qed

text \<open>A member dropped and added again is a member, as a corollary of exactness.\<close>

corollary dropped_then_added:
  assumes "m \<in> full (i - 2)" and "m \<notin> full (i - 1)" and "m \<in> full i"
  shows "m \<in> members i"
  using assms members_exact by simp

section \<open>The chain is bounded by the interval\<close>

definition nearest_checkpoint :: "nat \<Rightarrow> nat" where
  "nearest_checkpoint i = i - i mod k"

lemma nearest_is_checkpoint: "is_checkpoint (nearest_checkpoint i)"
  unfolding is_checkpoint_def nearest_checkpoint_def
  by (simp add: minus_mod_eq_mult_div)

lemma nearest_le: "nearest_checkpoint i \<le> i"
  by (simp add: nearest_checkpoint_def)

lemma no_checkpoint_between:
  "nearest_checkpoint i < j \<Longrightarrow> j \<le> i \<Longrightarrow> \<not> is_checkpoint j"
proof
  assume lt: "nearest_checkpoint i < j" and le: "j \<le> i" and cp: "is_checkpoint j"
  have "j mod k = 0" using cp by (simp add: is_checkpoint_def)
  have ni: "nearest_checkpoint i = k * (i div k)" unfolding nearest_checkpoint_def by (simp add: minus_mod_eq_mult_div)
  have "j = k * (j div k)" using \<open>j mod k = 0\<close> by (metis add_cancel_right_right mult_div_mod_eq)
  with lt ni have "k * (i div k) < k * (j div k)" by simp
  then have "i div k < j div k" by simp
  then have "i < j" using k_pos by (meson div_le_mono leD not_le)
  with le show False by simp
qed

theorem chain_length_bounded: "i - nearest_checkpoint i < k"
  unfolding nearest_checkpoint_def using k_pos by (simp add: mod_less_divisor)

end

end
