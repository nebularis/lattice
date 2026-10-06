(* The MINOR change target (brief §4): a [reading] selector over the kernel's readings,
   dispatching to [some_value]/[every_value] (track TL), [most_value] (majority rule, added in
   step 2 of the scripted MINOR-change measure, M3), or returning a single bound value
   unchanged. *)

theory Reading
imports Eligibility
begin

datatype reading = SingleValueR | SomeValueR | EveryValueR | MostValueR

fun count_eq :: "decision \<Rightarrow> decision list \<Rightarrow> nat" where
  "count_eq d xs = length (filter (\<lambda>x. x = d) xs)"

fun most_value :: "decision list \<Rightarrow> decision" where
  "most_value xs = (let p = count_eq Permitted xs; d = count_eq Denied xs in
                     if d < p then Permitted else if p < d then Denied else Undetermined)"

fun apply_reading :: "reading \<Rightarrow> decision \<Rightarrow> decision list \<Rightarrow> decision" where
  "apply_reading SingleValueR d xs = d"
| "apply_reading SomeValueR d xs = some_value xs"
| "apply_reading EveryValueR d xs = every_value xs"
| "apply_reading MostValueR d xs = most_value xs"

(* GATE:BEGIN TR1 *)
lemma apply_reading_some_matches_spec: "apply_reading SomeValueR d xs = some_value xs"
(* GATE:END *)
  by simp

(* GATE:BEGIN TR2 *)
lemma apply_reading_every_matches_spec: "apply_reading EveryValueR d xs = every_value xs"
(* GATE:END *)
  by simp

(* GATE:BEGIN TR3 *)
lemma apply_reading_most_matches_spec: "apply_reading MostValueR d xs = most_value xs"
(* GATE:END *)
  by simp

end
