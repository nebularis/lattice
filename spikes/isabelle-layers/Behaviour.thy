(* SPDX-License-Identifier: MPL-2.0 *)

(* Behaviour: nested states, well-formed configurations, default and history entry, gates and
   the termination of a pass.
   Source: ontology/behaviour/README.md section 5.3 (laws B5, B9, B10, B11), ADR-A106's addendum,
   and ontology/instrument/README.md section 11.3 (gating). A spike, not yet aligned to the formal-methods track. *)

theory Behaviour
imports Main
begin

section \<open>State trees\<close>

text \<open>A state holds regions, and a region holds states, the first of which is its initial state.
A state with no region is atomic, with one region compound, with several parallel. Names are
natural numbers. A configuration is the set of names of the states currently occupied.\<close>

datatype stt = St nat "reg list"
  and reg = Rg "stt list"

fun name :: "stt \<Rightarrow> nat" where
  "name (St n _) = n"

fun names :: "stt \<Rightarrow> nat set" and names_r :: "reg \<Rightarrow> nat set" where
  "names (St n rs) = insert n (\<Union> (names_r ` set rs))"
| "names_r (Rg ss) = \<Union> (names ` set ss)"

text \<open>Law B11. A configuration is well formed below a state when the state is occupied and each
of its regions holds exactly one occupied state, itself well formed below, with every other state
of the region and everything beneath it unoccupied. A nested state's parent is therefore
occupied, and each region of an occupied state holds exactly one current state.\<close>

fun wfc :: "stt \<Rightarrow> nat set \<Rightarrow> bool" and wfc_r :: "reg \<Rightarrow> nat set \<Rightarrow> bool" where
  "wfc (St n rs) C = (n \<in> C \<and> (\<forall>r \<in> set rs. wfc_r r C))"
| "wfc_r (Rg ss) C = (\<exists>s \<in> set ss. wfc s C \<and> (\<forall>s' \<in> set ss. s' \<noteq> s \<longrightarrow> names s' \<inter> C = {}))"

text \<open>Default entry: arriving at a composite enters each region at its initial state, all the
way down.\<close>

fun dconf :: "stt \<Rightarrow> nat set" and dconf_r :: "reg \<Rightarrow> nat set" where
  "dconf (St n rs) = insert n (\<Union> (dconf_r ` set rs))"
| "dconf_r (Rg []) = {}"
| "dconf_r (Rg (s # ss)) = dconf s"

text \<open>A tree is proper when every name is used once, every region has at least one state, and
sibling subtrees share no name.\<close>

fun proper :: "stt \<Rightarrow> bool" and proper_r :: "reg \<Rightarrow> bool" where
  "proper (St n rs) = (n \<notin> \<Union> (names_r ` set rs) \<and> (\<forall>r \<in> set rs. proper_r r) \<and>
                       (\<forall>r \<in> set rs. \<forall>r' \<in> set rs. r \<noteq> r' \<longrightarrow> names_r r \<inter> names_r r' = {}))"
| "proper_r (Rg ss) = (ss \<noteq> [] \<and> (\<forall>s \<in> set ss. proper s) \<and>
                       (\<forall>s \<in> set ss. \<forall>s' \<in> set ss. s \<noteq> s' \<longrightarrow> names s \<inter> names s' = {}))"

lemma dconf_sub_names: "dconf t \<subseteq> names t" "dconf_r r \<subseteq> names_r r"
proof (induction t and r)
  case (Rg ss)
  then show ?case by (cases ss) auto
qed auto

lemma name_in_names: "name t \<in> names t"
  by (cases t) auto

text \<open>Well-formedness below a state depends only on the names of that state's subtree.\<close>

lemma wfc_local:
  "D \<inter> names t = C \<inter> names t \<Longrightarrow> wfc t C = wfc t D"
  "D \<inter> names_r r = C \<inter> names_r r \<Longrightarrow> wfc_r r C = wfc_r r D"
proof (induction t and r arbitrary: C D and C D)
  case (St n rs)
  have n: "n \<in> C \<longleftrightarrow> n \<in> D" using St.prems by auto
  have "wfc_r r C = wfc_r r D" if r: "r \<in> set rs" for r
  proof -
    have "names_r r \<subseteq> names (St n rs)" using r by auto
    then have "D \<inter> names_r r = C \<inter> names_r r" using St.prems by auto
    then show ?thesis using St.IH r by blast
  qed
  then show ?case using n by simp
next
  case (Rg ss)
  have sub: "names s \<subseteq> names_r (Rg ss)" if "s \<in> set ss" for s using that by auto
  have one: "wfc s C = wfc s D" if s: "s \<in> set ss" for s
  proof -
    have "D \<inter> names s = C \<inter> names s" using Rg.prems sub[OF s] by auto
    then show ?thesis using Rg.IH s by blast
  qed
  have two: "names s' \<inter> C = {} \<longleftrightarrow> names s' \<inter> D = {}" if s': "s' \<in> set ss" for s'
    using Rg.prems sub[OF s'] by auto
  show ?case using one two by auto
qed

text \<open>Default entry gives a well-formed configuration on a proper tree.\<close>

theorem default_entry_wf:
  "proper t \<Longrightarrow> wfc t (dconf t)"
  "proper_r r \<Longrightarrow> wfc_r r (dconf_r r)"
proof (induction t and r)
  case (St n rs)
  have each: "wfc_r r (dconf (St n rs))" if r: "r \<in> set rs" for r
  proof -
    have ih: "wfc_r r (dconf_r r)" using St.IH St.prems r by simp
    have "dconf (St n rs) \<inter> names_r r = dconf_r r \<inter> names_r r"
    proof -
      have "n \<notin> names_r r" using St.prems r by auto
      moreover have "dconf_r r' \<inter> names_r r = {}" if r': "r' \<in> set rs" "r' \<noteq> r" for r'
        using St.prems r r' dconf_sub_names(2)[of r'] by fastforce
      moreover have "dconf_r r \<subseteq> names_r r" by (rule dconf_sub_names)
      ultimately show ?thesis using r by auto
    qed
    then show ?thesis using wfc_local(2)[of "dconf (St n rs)" r "dconf_r r"] ih by simp
  qed
  then show ?case by simp
next
  case (Rg ss)
  then obtain s0 ss' where ss: "ss = s0 # ss'" by (cases ss) auto
  have wf0: "wfc s0 (dconf s0)" using Rg.IH Rg.prems ss by simp
  have others: "names s' \<inter> dconf s0 = {}" if "s' \<in> set ss" "s' \<noteq> s0" for s'
    using Rg.prems ss that dconf_sub_names(1)[of s0] by fastforce
  show ?case unfolding ss using wf0 others ss by auto
qed

section \<open>Composite states hold while a descendant does\<close>

text \<open>Instrument's gating rule says a composite state holds while any of its descendants is
active. In a well-formed configuration that is the same as the composite being occupied, because
a nested state's parent is occupied (B11).\<close>

fun subtrees :: "stt \<Rightarrow> stt set" and subtrees_r :: "reg \<Rightarrow> stt set" where
  "subtrees (St n rs) = insert (St n rs) (\<Union> (subtrees_r ` set rs))"
| "subtrees_r (Rg ss) = \<Union> (subtrees ` set ss)"

definition holds :: "stt \<Rightarrow> nat set \<Rightarrow> bool" where
  "holds s C \<longleftrightarrow> names s \<inter> C \<noteq> {}"

theorem holds_iff_occupied:
  "wfc t C \<Longrightarrow> s \<in> subtrees t \<Longrightarrow> holds s C \<longleftrightarrow> name s \<in> C"
  "wfc_r r C \<Longrightarrow> s \<in> subtrees_r r \<Longrightarrow> holds s C \<longleftrightarrow> name s \<in> C"
proof (induction t and r)
  case (St n rs)
  show ?case
  proof (cases "s = St n rs")
    case True
    then show ?thesis using St.prems(1) name_in_names unfolding holds_def by auto
  next
    case False
    then obtain r where r: "r \<in> set rs" "s \<in> subtrees_r r" using St.prems(2) by auto
    then show ?thesis using St.IH St.prems(1) by simp
  qed
next
  case (Rg ss)
  from Rg.prems(1) obtain s0 where s0: "s0 \<in> set ss" "wfc s0 C"
    and rest: "\<forall>s' \<in> set ss. s' \<noteq> s0 \<longrightarrow> names s' \<inter> C = {}" by auto
  from Rg.prems(2) obtain s1 where s1: "s1 \<in> set ss" "s \<in> subtrees s1" by auto
  have sub: "names s \<subseteq> names s1"
  proof -
    have "s \<in> subtrees u \<Longrightarrow> names s \<subseteq> names u" "s \<in> subtrees_r v \<Longrightarrow> names s \<subseteq> names_r v" for u v
      by (induction u and v) auto
    then show ?thesis using s1 by blast
  qed
  show ?case
  proof (cases "s1 = s0")
    case True
    then show ?thesis using Rg.IH s0 s1 by simp
  next
    case False
    then have "names s1 \<inter> C = {}" using rest s1 by simp
    then have "names s \<inter> C = {}" using sub by auto
    then show ?thesis using name_in_names[of s] unfolding holds_def by auto
  qed
qed

section \<open>Gates\<close>

text \<open>A relation's gate groups the states it names by regime. Within one regime's group any
named state admits the relation, and across regimes every group must. A relation that names no
state is not gated. Regimes never rank one another: the rule is symmetric in the groups.\<close>

definition gate :: "stt set set \<Rightarrow> nat set \<Rightarrow> bool" where
  "gate groups C \<longleftrightarrow> (\<forall>g \<in> groups. \<exists>s \<in> g. holds s C)"

lemma ungated: "gate {} C"
  by (simp add: gate_def)

lemma gate_any_within: "gate {{a, b}} C \<longleftrightarrow> holds a C \<or> holds b C"
  by (auto simp: gate_def)

lemma gate_all_across: "gate {{a}, {b}} C \<longleftrightarrow> holds a C \<and> holds b C"
  by (auto simp: gate_def)

lemma gate_closed_means_not_apply: "\<not> gate groups C \<Longrightarrow> \<exists>g \<in> groups. \<forall>s \<in> g. \<not> holds s C"
  by (auto simp: gate_def)

text \<open>The supply agreement's duty to deliver (Instrument section 11.3): in force in the
suspension regime, and unaffected in the force majeure regime. Four configurations, one of which
admits the duty.\<close>

definition in_force :: stt where "in_force = St 1 []"
definition suspended :: stt where "suspended = St 2 []"
definition unaffected :: stt where "unaffected = St 3 []"
definition affected :: stt where "affected = St 4 []"
definition duty_gate :: "stt set set" where "duty_gate = {{in_force}, {unaffected}}"

lemma duty_applies: "gate duty_gate {1, 3}"
  by (simp add: gate_def duty_gate_def holds_def in_force_def unaffected_def)

lemma duty_does_not_apply:
  "\<not> gate duty_gate {1, 4} \<and> \<not> gate duty_gate {2, 3} \<and> \<not> gate duty_gate {2, 4}"
  by (simp add: gate_def duty_gate_def holds_def in_force_def unaffected_def)

section \<open>Exit and history\<close>

text \<open>Leaving a composite leaves every state inside it. A history entry restores the
configuration below the target as it was when last exited, so what exit removed and what history
restores are the same set, and restoring a well-formed configuration gives one back.\<close>

definition exit :: "stt \<Rightarrow> nat set \<Rightarrow> nat set" where
  "exit t C = C - names t"

definition history :: "stt \<Rightarrow> nat set \<Rightarrow> nat set" where
  "history t C = C \<inter> names t"

lemma exit_clears_subtree: "names t \<inter> exit t C = {}"
  by (simp add: exit_def)

lemma exit_history_partition: "exit t C \<union> history t C = C"
  by (auto simp: exit_def history_def)

lemma history_restores: "wfc t C \<Longrightarrow> wfc t (history t C)"
  using wfc_local(1)[of "history t C" t C] by (simp add: history_def)

lemma history_restores_into: "wfc t C \<Longrightarrow> D \<inter> names t = {} \<Longrightarrow> wfc t (D \<union> history t C)"
  using wfc_local(1)[of "D \<union> history t C" t C] by (auto simp: history_def)

text \<open>An internal transition creates no occupancy, so the configuration is unchanged. That is
the whole of its effect on state, by definition.\<close>

definition internal :: "nat set \<Rightarrow> nat set" where
  "internal C = C"

lemma internal_keeps_configuration: "wfc t C \<Longrightarrow> wfc t (internal C)"
  by (simp add: internal_def)

section \<open>Law B10: a pass terminates\<close>

text \<open>Derived triggers read the new configuration and may enable further transitions at the
same position. They cannot form a cycle. A finite acyclic relation of "this transition enables
that one" has no infinite chain, so the pass repeats finitely often.\<close>

theorem pass_terminates:
  assumes "finite enables" and "acyclic enables"
  shows "\<not> (\<exists>f. \<forall>i. (f i, f (Suc i)) \<in> enables)"
proof -
  have "wf (enables\<inverse>)" using finite_acyclic_wf_converse assms by blast
  then show ?thesis unfolding wf_iff_no_infinite_down_chain by auto
qed

end
