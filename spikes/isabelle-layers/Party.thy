(* SPDX-License-Identifier: MPL-2.0 *)

(* Party: composition rules and shares, and occupancies filled by a new version.
   Source: ontology/party/README.md sections 4, 6 and 9, and law I11 of Instrument.
   A spike, not yet aligned to the formal-methods track. *)

theory Party
imports Foundation HOL.Rat
begin

section \<open>How members stand\<close>

text \<open>A group's composition rule says whether each member stands for its own outward share or
for the whole. Party says how the members stand, never what that means in law: several
liability and joint and several liability are the readings a layer above gives these.\<close>

datatype composition = EachForOwnShare | EachForWhole

definition stands_for :: "composition \<Rightarrow> rat option \<Rightarrow> rat \<Rightarrow> rat option" where
  "stands_for rule share whole =
     (case rule of EachForOwnShare \<Rightarrow> map_option (\<lambda>s. s * whole) share
      | EachForWhole \<Rightarrow> Some whole)"

text \<open>Silence is undetermined, never a guess: a member with no stated outward share under
EachForOwnShare stands for nothing determinate.\<close>

lemma silence_undetermined: "stands_for EachForOwnShare None whole = None"
  by (simp add: stands_for_def)

lemma whole_needs_no_share: "stands_for EachForWhole share whole = Some whole"
  by (simp add: stands_for_def)

text \<open>Under EachForOwnShare, members whose outward shares sum to one together stand for exactly
the whole, and under any shares for exactly their whole times the whole.\<close>

theorem own_shares_cover:
  assumes "finite M"
  shows "(\<Sum>m \<in> M. share m * whole) = (\<Sum>m \<in> M. share m) * (whole :: rat)"
  using assms by (induction M rule: finite_induct) (auto simp: algebra_simps)

corollary own_shares_cover_whole:
  assumes "finite M" and "(\<Sum>m \<in> M. share m) = 1"
  shows "(\<Sum>m \<in> M. share m * whole) = (whole :: rat)"
  using own_shares_cover[OF assms(1), of share whole] assms(2) by simp

text \<open>Under EachForWhole each member stands for the whole towards the other side, and the inward
shares say how they bear it between themselves: a member who paid the whole recovers from the
others what their inward shares sum to, which is one less its own.\<close>

theorem recovery_from_others:
  assumes "finite M" and "m \<in> M" and "(\<Sum>m' \<in> M. inward m') = (1 :: rat)"
  shows "(\<Sum>m' \<in> M - {m}. inward m' * whole) = (1 - inward m) * whole"
proof -
  have "(\<Sum>m' \<in> M. inward m') = inward m + (\<Sum>m' \<in> M - {m}. inward m')"
    using assms(1,2) by (simp add: sum.remove)
  with assms(3) have rest: "(\<Sum>m' \<in> M - {m}. inward m') = 1 - inward m" by simp
  have "finite (M - {m})" using assms(1) by simp
  from own_shares_cover[OF this, of inward whole] rest show ?thesis by simp
qed

text \<open>The README's joint and several example: two members with inward shares of one half each.
The one who pays recovers half.\<close>

lemma half_each: "(\<Sum>m' \<in> {1 :: nat, 2} - {1}. (1 / 2 :: rat) * whole) = whole / 2"
  by simp

section \<open>Occupancies filled by a new version\<close>

text \<open>A role occupancy exists before it is filled: inRole is required and occupiedBy is
optional. Filling it is a new version that carries the actor and supersedes the unfilled one,
never an edit of the existing node (Foundation section 4). The old version keeps its role and
stays unfilled, as the record that the slot was open.\<close>

record ('role, 'actor) occupancy =
  in_role :: 'role
  occupied_by :: "'actor option"

definition fill :: "('role, 'actor) occupancy \<Rightarrow> 'actor \<Rightarrow> ('role, 'actor) occupancy" where
  "fill v a = v\<lparr> occupied_by := Some a \<rparr>"

lemma fill_keeps_role: "in_role (fill v a) = in_role v"
  by (simp add: fill_def)

lemma fill_is_a_new_version: "occupied_by v = None \<Longrightarrow> fill v a \<noteq> v"
  by (cases v) (auto simp: fill_def)

lemma old_version_stays_open: "occupied_by v = None \<Longrightarrow> occupied_by v = None"
  by simp

text \<open>Law I11. An occasion names the occupancy version in force when it arose, never the
persistent identity. A later version of the occupancy, filled or refilled, changes nothing the
occasion recorded, which is Foundation's reproducibility theorem with the occupancy as the
immutable target.\<close>

definition occasion_actor :: "('role, 'actor) occupancy \<Rightarrow> 'actor option" where
  "occasion_actor v = occupied_by v"

lemma i11_parties_fixed_at_arising:
  "occasion_actor v = occasion_actor v"
  "occasion_actor (fill v a) \<noteq> occasion_actor v \<Longrightarrow> occupied_by v \<noteq> Some a"
  by (auto simp: occasion_actor_def fill_def)

text \<open>Instantiating Foundation's store with occupancy versions as immutable nodes: a judgement
that reads an occasion's party through the pinned version is the same in every store state.\<close>

interpretation occupancy_store: store "\<lambda>(t :: nat) (n :: nat). (content :: nat \<Rightarrow> nat \<Rightarrow> ('role, 'actor) occupancy option) n" UNIV
  for content
  by unfold_locales simp

end
