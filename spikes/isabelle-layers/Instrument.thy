(* SPDX-License-Identifier: MPL-2.0 *)

(* Instrument: Hohfeld's correlatives, one modal verb per class, anchored time (due ranges,
   windows, tolling) and gates.
   Source: ontology/instrument/README.md sections 4.4, 4.5, 11.3, 13 and 14, laws I5, I9, I10.
   A spike, not yet aligned to the formal-methods track. *)

theory Instrument
imports Quantification Behaviour
begin

section \<open>Hohfeld's legal relations\<close>

text \<open>Eight conceptions in four pairs of correlatives, the two ends of one relation between two
people. Correlation is an involution that pairs every conception with a different one, which is
why a duty and its claim are one node in this layer: nothing has to keep them consistent.\<close>

datatype hohfeld = Claim | Duty | Privilege | NoRight | PowerH | Liability | Immunity | Disability

fun correlative :: "hohfeld \<Rightarrow> hohfeld" where
  "correlative Claim = Duty" | "correlative Duty = Claim"
| "correlative Privilege = NoRight" | "correlative NoRight = Privilege"
| "correlative PowerH = Liability" | "correlative Liability = PowerH"
| "correlative Immunity = Disability" | "correlative Disability = Immunity"

lemma correlative_involutive: "correlative (correlative h) = h"
  by (cases h) simp_all

lemma correlative_pairs: "correlative h \<noteq> h"
  by (cases h) simp_all

lemma correlative_bijective: "bij correlative"
  by (rule bij_betw_byWitness[of _ correlative]) (auto simp: correlative_involutive)

text \<open>Each class reads with one modal verb, so a sentence rendered from data is consistent.\<close>

datatype relation_kind = Obligation | ContinuingObligation | Prohibition | Permission | Exclusion | Power

datatype modal = Must | MustEnsure | MustNot | May | NeedNot | MayChange

fun modal_of :: "relation_kind \<Rightarrow> modal" where
  "modal_of Obligation = Must" | "modal_of ContinuingObligation = MustEnsure"
| "modal_of Prohibition = MustNot" | "modal_of Permission = May"
| "modal_of Exclusion = NeedNot" | "modal_of Power = MayChange"

lemma one_verb_per_class: "modal_of k = modal_of k' \<Longrightarrow> k = k'"
  by (cases k; cases k') simp_all

text \<open>Law I5. An obligation has at most one due range, and a continuing obligation or a
prohibition has none, because each is kept throughout rather than performed by a time.\<close>

definition may_have_due :: "relation_kind \<Rightarrow> bool" where
  "may_have_due k \<longleftrightarrow> k = Obligation"

lemma i5_continuing_has_no_due: "\<not> may_have_due ContinuingObligation" "\<not> may_have_due Prohibition"
  by (simp_all add: may_have_due_def)

section \<open>Anchored time, law I9\<close>

text \<open>A due range names its anchor's role, never a date and never the time of evaluation. One
stated range serves every occasion because each resolves the role to its own instant. The
resolved range is the stated offsets translated by the anchor, so containment is translation
invariant: evaluating the stated range at the occasion's instant relative to its anchor is the
same as evaluating the resolved range at the absolute instant.\<close>

definition resolve_range :: "instant \<Rightarrow> int \<Rightarrow> int \<Rightarrow> instant range" where
  "resolve_range anchor lo hi = \<lparr> lower = Some (Bound (anchor + lo) Closed), upper = Some (Bound (anchor + hi) Closed) \<rparr>"

theorem stated_once_resolved_per_occasion:
  "contains (resolve_range anchor lo hi) t \<longleftrightarrow> contains (resolve_range 0 lo hi) (t - anchor)"
  by (simp add: resolve_range_def contains_def) arith

lemma resolve_range_contains: "contains (resolve_range a lo hi) t \<longleftrightarrow> a + lo \<le> t \<and> t \<le> a + hi"
  by (auto simp: resolve_range_def contains_def)

text \<open>An unbound role gives Undetermined, naming the reason, never a date.\<close>

definition due_at :: "instant option \<Rightarrow> int \<Rightarrow> int \<Rightarrow> instant \<Rightarrow> outcome" where
  "due_at anchor lo hi t =
     (case anchor of None \<Rightarrow> OUndetermined ValueAbsent
      | Some a \<Rightarrow> if contains (resolve_range a lo hi) t then OTrue else OFalse)"

lemma unbound_role_undetermined: "due_at None lo hi t = OUndetermined ValueAbsent"
  by (simp add: due_at_def)

lemma bound_role_definite: "definite (due_at (Some a) lo hi t)"
  by (simp add: due_at_def definite_iff)

text \<open>The README's table: "within 24 hours of becoming aware" is arising plus 0 to 24 hours,
so with arising at hour 100 the due range is 100 to 124.\<close>

lemma within_24_hours:
  "contains (resolve_range 100 0 24) 124 \<and> \<not> contains (resolve_range 100 0 24) 125 \<and> contains (resolve_range 100 0 24) 100"
  by (simp add: resolve_range_contains)

section \<open>Windows, law I10\<close>

text \<open>A power exercised outside its window has no effect. Once the window has closed no later
exercise has effect, which is what it means for an offer or option to lapse. The lapse needs no
modelling of its own.\<close>

datatype effect = Effective | NoEffect

definition exercise :: "instant range \<Rightarrow> instant \<Rightarrow> effect" where
  "exercise w t = (if contains w t then Effective else NoEffect)"

lemma i10_outside_window: "\<not> contains w t \<Longrightarrow> exercise w t = NoEffect"
  by (simp add: exercise_def)

lemma lapse:
  assumes "upper w = Some (Bound e c)" and "e < t"
  shows "exercise w t = NoEffect"
  using assms by (auto simp: exercise_def contains_def)

text \<open>The lease's break: no start, closing six months before the break date. With the break
date at month 600, notice at month 593 is effective and notice at month 595 is too late.\<close>

definition break_window :: "instant range" where
  "break_window = \<lparr> lower = None, upper = Some (Bound (600 - 6) Closed) \<rparr>"

lemma break_notice: "exercise break_window 593 = Effective \<and> exercise break_window 595 = NoEffect"
  by (simp add: exercise_def break_window_def contains_def)

section \<open>Tolling\<close>

text \<open>A due range's end moves later by the time the subject spends in the states that toll it.
Time spent is never negative, so tolling never brings a deadline forward, and tolling periods
add up.\<close>

definition tolled_end :: "instant \<Rightarrow> int list \<Rightarrow> instant" where
  "tolled_end e spent = e + sum_list spent"

lemma tolling_never_advances: "(\<forall>s \<in> set spent. 0 \<le> s) \<Longrightarrow> e \<le> tolled_end e spent"
  by (induction spent) (auto simp: tolled_end_def)

lemma tolling_adds_up: "tolled_end e (spent @ spent') = tolled_end (tolled_end e spent) spent'"
  by (simp add: tolled_end_def)

lemma no_tolling_no_change: "tolled_end e [] = e"
  by (simp add: tolled_end_def)

section \<open>Gates read state, structure stays apart\<close>

text \<open>A relation's gate is evaluated against a configuration (Behaviour.gate). A design-time
comparison of two relations reads their structure and never their gate, so two relations whose
structure is equal compare equal whatever regime either is in. The theorem says only that such a
comparison is a function of structure alone, which is design principle DP6 by construction.\<close>

record ('act, 'party) relation_structure =
  kind :: relation_kind
  activity :: 'act
  parties :: "'party set"

record ('act, 'party) relation =
  content :: "('act, 'party) relation_structure"
  gates :: "stt set set"

definition compare :: "('act, 'party) relation \<Rightarrow> ('act, 'party) relation \<Rightarrow> bool" where
  "compare r s \<longleftrightarrow> content r = content s"

lemma dp6_gate_never_compared:
  "compare (r\<lparr> gates := g \<rparr>) (s\<lparr> gates := g' \<rparr>) \<longleftrightarrow> compare r s"
  by (simp add: compare_def)

lemma gated_relation_applies:
  "gate (gates r) C \<longleftrightarrow> (\<forall>g \<in> gates r. \<exists>s \<in> g. holds s C)"
  by (simp add: gate_def)

end
