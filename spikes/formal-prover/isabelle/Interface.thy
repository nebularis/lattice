(* M6's interface: a reading is admissible only if it is monotone in the information order over
   its list argument (brief §5.1, narrowed scope). The locale [monotone_reading] fixes a
   function and assumes monotonicity; [interpretation] then requires that assumption to be
   discharged as a proof obligation at the point of interpretation. Unlike Rocq's dependent
   record (a type error at construction time if the proof term is missing or ill-typed), a
   locale's obligation is a tactic failure at `interpretation`/`unfold_locales`, not a type
   error: the candidate function is perfectly well-typed on its own, and only the subsequent
   proof step rejects it.

   Isar has no plain top-level keyword that wraps a whole command and asserts it fails the way
   Rocq's `Fail` does (a failing `interpretation` aborts the theory). The ML layer does have an
   equivalent, though: `can` (a standard ML combinator, `can f x` is true iff `f x` does not
   raise) wrapping `Goal.prove` lets an `ML_command` attempt exactly the obligation a bad
   candidate would face, and assert that the attempt fails, without aborting the build -- the
   same "attempt, assert rejection, keep going" shape as Rocq's `Fail`, one layer down from the
   Isar surface syntax. Demonstrated below for [inverted_reading], confirmed empirically to
   print "ok" and let the theory finish; see the formal-prover-experiment.md report, M6, for the
   comparison this was written to settle. *)

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

(* A deliberately non-monotone candidate: "Permitted if the list contains an Undetermined
   entry, else Denied" looks at its argument's values, but the wrong way round -- refining an
   Undetermined entry to something more informative can only ever *remove* an Undetermined, so a
   well-behaved reading could only move towards Denied as information increases, never away from
   it. [inverted_reading] does the opposite, so [monotone_reading]'s obligation is unprovable for
   it: attempted and confirmed to fail below, the same shape of evidence Rocq's `Fail Definition`
   gives in `Interface.v`, by `can`/`Goal.prove` instead of a top-level keyword. *)
definition inverted_reading :: "decision list \<Rightarrow> decision" where
  "inverted_reading xs = (if Undetermined \<in> set xs then Permitted else Denied)"

ML \<open>
  val inverted_reading_obligation =
    @{prop "decision_leq_list xs ys \<longrightarrow> decision_leq (inverted_reading xs) (inverted_reading ys)"}
  val _ =
    if can (fn () =>
      Goal.prove @{context} ["xs", "ys"] [] inverted_reading_obligation
        (fn {context, ...} => auto_tac context)) ()
    then error "inverted_reading's monotonicity obligation proved: it should not have"
    else writeln
      "rejected, as expected: inverted_reading cannot satisfy monotone_reading's obligation \
      \(can/Goal.prove reports failure; a real `interpretation monotone_reading inverted_reading` \
      \would abort the theory the same way Rocq's Fail Definition is wrapped to expect)"
\<close>

end
