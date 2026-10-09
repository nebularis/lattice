(* The logic kernel's connectives and laws (target TA), hand-written on top of the generated
   Kernel.thy (epic principle E1, ADR-A-FM2, FM-D17): the closed datatype and or3/and3/neg3's
   defining equations are generated from ontology/eligibility/README.md \u00a710, since they are a
   finite, exhaustive case table over a closed domain, not a law. decision_leq is a predicate
   over equality, not a finite case table, and stays hand-written here, as does every lemma. *)

theory KernelLaws
imports Kernel
begin

definition decision_leq :: "decision \<Rightarrow> decision \<Rightarrow> bool" where
  "decision_leq u x \<longleftrightarrow> u = Undetermined \<or> u = x"

(* GATE:BEGIN TA1 *)
lemma or3_monotone_left: "decision_leq a a' \<Longrightarrow> decision_leq (or3 a b) (or3 a' b)"
  by (cases a; cases a'; cases b; simp add: decision_leq_def)

lemma or3_monotone_right: "decision_leq b b' \<Longrightarrow> decision_leq (or3 a b) (or3 a b')"
  by (cases a; cases b; cases b'; simp add: decision_leq_def)

lemma and3_monotone_left: "decision_leq a a' \<Longrightarrow> decision_leq (and3 a b) (and3 a' b)"
  by (cases a; cases a'; cases b; simp add: decision_leq_def)

lemma and3_monotone_right: "decision_leq b b' \<Longrightarrow> decision_leq (and3 a b) (and3 a b')"
  by (cases a; cases b; cases b'; simp add: decision_leq_def)
(* GATE:END *)

(* GATE:BEGIN TA2 *)
lemma neg3_involutive: "neg3 (neg3 a) = a"
  by (cases a; simp)

lemma neg3_monotone: "decision_leq a a' \<Longrightarrow> decision_leq (neg3 a) (neg3 a')"
  by (cases a; cases a'; simp add: decision_leq_def)

lemma neg3_fixes_undetermined: "neg3 Undetermined = Undetermined"
  by simp
(* GATE:END *)

(* Characterising lemmas (TA3-TA5), added by E1.4 (the formal-methods epic's second review
   \u00a72.2): TA1 and TA2 alone are satisfiable by degenerate stand-ins for or3/and3/neg3 (a
   constant function satisfies TA1's monotonicity, the identity function satisfies TA2's three
   lemmas), so neither pins down the actual strong Kleene semantics on its own. These do. *)

(* GATE:BEGIN TA3 *)
lemma or3_truth_table:
  "or3 Permitted Permitted = Permitted" "or3 Permitted Denied = Permitted" "or3 Permitted Undetermined = Permitted"
  "or3 Denied Permitted = Permitted" "or3 Denied Denied = Denied" "or3 Denied Undetermined = Undetermined"
  "or3 Undetermined Permitted = Permitted" "or3 Undetermined Denied = Undetermined" "or3 Undetermined Undetermined = Undetermined"
  by simp_all

lemma and3_truth_table:
  "and3 Permitted Permitted = Permitted" "and3 Permitted Denied = Denied" "and3 Permitted Undetermined = Undetermined"
  "and3 Denied Permitted = Denied" "and3 Denied Denied = Denied" "and3 Denied Undetermined = Denied"
  "and3 Undetermined Permitted = Undetermined" "and3 Undetermined Denied = Denied" "and3 Undetermined Undetermined = Undetermined"
  by simp_all

lemma neg3_truth_table:
  "neg3 Permitted = Denied" "neg3 Denied = Permitted" "neg3 Undetermined = Undetermined"
  by simp_all
(* GATE:END *)

(* GATE:BEGIN TA4 *)
lemma or3_commute: "or3 a b = or3 b a"
  by (cases a; cases b; simp)

lemma or3_assoc: "or3 (or3 a b) c = or3 a (or3 b c)"
  by (cases a; cases b; cases c; simp)

lemma or3_idempotent: "or3 a a = a"
  by (cases a; simp)

lemma or3_identity: "or3 a Denied = a"
  by (cases a; simp)

lemma or3_absorb: "or3 a Permitted = Permitted"
  by (cases a; simp)

lemma and3_commute: "and3 a b = and3 b a"
  by (cases a; cases b; simp)

lemma and3_assoc: "and3 (and3 a b) c = and3 a (and3 b c)"
  by (cases a; cases b; cases c; simp)

lemma and3_idempotent: "and3 a a = a"
  by (cases a; simp)

lemma and3_identity: "and3 a Permitted = a"
  by (cases a; simp)

lemma and3_absorb: "and3 a Denied = Denied"
  by (cases a; simp)
(* GATE:END *)

(* GATE:BEGIN TA5 *)
lemma neg3_or3_demorgan: "neg3 (or3 a b) = and3 (neg3 a) (neg3 b)"
  by (cases a; cases b; simp)

lemma neg3_and3_demorgan: "neg3 (and3 a b) = or3 (neg3 a) (neg3 b)"
  by (cases a; cases b; simp)
(* GATE:END *)

lemma decision_leq_trans: "decision_leq a b \<Longrightarrow> decision_leq b c \<Longrightarrow> decision_leq a c"
  unfolding decision_leq_def by auto

lemma decision_leq_refl: "decision_leq a a"
  unfolding decision_leq_def by simp

end
