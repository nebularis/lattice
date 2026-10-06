(* M6's interface: a reading is admissible only if it is monotone in the information order over
   its list argument (brief §5.1, narrowed scope). The locale [monotone_reading] fixes a
   function and assumes monotonicity; [interpretation] then requires that assumption to be
   discharged as a proof obligation at the point of interpretation. Unlike Rocq's dependent
   record (a type error at construction time if the proof term is missing or ill-typed), a
   locale's obligation is a tactic failure at `interpretation`/`unfold_locales`, not a type
   error: the candidate function is perfectly well-typed on its own, and only the subsequent
   proof step rejects it. Comparing this to Rocq's point of rejection is D4's job. *)

theory Interface
imports Eligibility
begin

locale monotone_reading =
  fixes apply_fn :: "decision list \<Rightarrow> decision"
  assumes monotone: "decision_leq_list xs ys \<Longrightarrow> decision_leq (apply_fn xs) (apply_fn ys)"

(* GATE:BEGIN TR4 *)
interpretation some_value_reading: monotone_reading some_value
  by unfold_locales (rule some_value_monotone)
(* GATE:END *)

(* GATE:BEGIN TR5 *)
interpretation every_value_reading: monotone_reading every_value
  by unfold_locales (rule every_value_monotone)
(* GATE:END *)

end
