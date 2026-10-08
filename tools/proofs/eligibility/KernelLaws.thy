(* The logic kernel's connectives and laws (target TA), hand-written on top of the generated
   Kernel.thy datatype (epic principle E1, ADR-A-FM2). Restated from
   spikes/formal-prover/isabelle/Kernel.thy (track D's spike), which first proved this out and
   found the TA2 correction recorded there (negation is monotone, not order-reversing; see
   formal-methods-0.md's correction note and formal-prover-experiment.md). *)

theory KernelLaws
imports Kernel
begin

definition decision_leq :: "decision \<Rightarrow> decision \<Rightarrow> bool" where
  "decision_leq u x \<longleftrightarrow> u = Undetermined \<or> u = x"

fun or3 :: "decision \<Rightarrow> decision \<Rightarrow> decision" where
  "or3 Permitted _ = Permitted"
| "or3 Denied b = b"
| "or3 Undetermined Permitted = Permitted"
| "or3 Undetermined Denied = Undetermined"
| "or3 Undetermined Undetermined = Undetermined"

fun and3 :: "decision \<Rightarrow> decision \<Rightarrow> decision" where
  "and3 Permitted b = b"
| "and3 Denied _ = Denied"
| "and3 Undetermined Permitted = Undetermined"
| "and3 Undetermined Denied = Denied"
| "and3 Undetermined Undetermined = Undetermined"

fun neg3 :: "decision \<Rightarrow> decision" where
  "neg3 Permitted = Denied"
| "neg3 Denied = Permitted"
| "neg3 Undetermined = Undetermined"

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

lemma decision_leq_trans: "decision_leq a b \<Longrightarrow> decision_leq b c \<Longrightarrow> decision_leq a c"
  unfolding decision_leq_def by auto

lemma decision_leq_refl: "decision_leq a a"
  unfolding decision_leq_def by simp

end
