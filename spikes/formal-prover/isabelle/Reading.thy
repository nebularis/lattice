(* The MINOR change target (brief §4): a [reading] selector over the kernel's three readings,
   dispatching to [some_value]/[every_value] (track TL) or returning a single bound value
   unchanged. Step 1 of the scripted MINOR-change measure (M3): the datatype carries exactly the
   three readings in play so far. Step 2 (a later commit) adds [MostValueR] and measures the
   diff needed to repair this file. *)

theory Reading
imports Eligibility
begin

datatype reading = SingleValueR | SomeValueR | EveryValueR

fun apply_reading :: "reading \<Rightarrow> decision \<Rightarrow> decision list \<Rightarrow> decision" where
  "apply_reading SingleValueR d xs = d"
| "apply_reading SomeValueR d xs = some_value xs"
| "apply_reading EveryValueR d xs = every_value xs"

(* GATE:BEGIN TR1 *)
lemma apply_reading_some_matches_spec: "apply_reading SomeValueR d xs = some_value xs"
(* GATE:END *)
  by simp

(* GATE:BEGIN TR2 *)
lemma apply_reading_every_matches_spec: "apply_reading EveryValueR d xs = every_value xs"
(* GATE:END *)
  by simp

end
