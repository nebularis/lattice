(* Defect S5: TA1 restated under its old name with a strictly weaker conclusion (brief §3, S5).
   This statement is trivially true (reflexivity of the order, no real monotonicity claim), so
   it offers no proof difficulty -- the point is that its *statement digest* differs from the
   committed claim's, under the same subject name "TA1". See check_s5.py, which recomputes both
   digests and shows they differ. *)

theory S5_weaker_restatement
imports FormalMethodsSpike.Kernel
begin

(* GATE:BEGIN TA1 *)
lemma or3_and3_monotone_WEAKENED:
  "decision_leq a a' \<Longrightarrow> decision_leq (or3 a b) (or3 a b)"
  "decision_leq b b' \<Longrightarrow> decision_leq (or3 a b) (or3 a b)"
  "decision_leq a a' \<Longrightarrow> decision_leq (and3 a b) (and3 a b)"
  "decision_leq b b' \<Longrightarrow> decision_leq (and3 a b) (and3 a b)"
(* GATE:END *)
  by (simp_all add: decision_leq_refl)

end
