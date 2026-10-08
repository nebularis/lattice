(* Defect S1: "every value returns Permitted when there is no value" -- some_value's empty case
   is weakened from Undetermined to Permitted (brief §3, S1). Shows what breaks: TL1's third
   clause for the empty list, and the adequacy oracle's "none" row. *)

theory S1_weak_empty_case
imports FormalMethodsSpike.Kernel
begin

fun some_value_broken :: "decision list \<Rightarrow> decision" where
  "some_value_broken [] = Permitted" (* was Undetermined *)
| "some_value_broken (x # xs) = fold or3 xs x"

(* Detection 1: the adequacy oracle's "no value" row no longer holds. A concrete, provable
   refutation, not merely a failed tactic. *)
lemma adequacy_some_none_breaks: "some_value_broken [] \<noteq> Undetermined"
  by simp

(* Detection 2: TL1's own statement (every xs, including xs = []) is false for the broken
   definition -- not merely hard to prove, but refutable. *)
lemma some_value_broken_breaks_TL1:
  "\<not> (\<forall>xs. (some_value_broken xs = Undetermined) \<longleftrightarrow>
        (xs = [] \<or> (Permitted \<notin> set xs \<and> Undetermined \<in> set xs)))"
proof
  assume H: "\<forall>xs. (some_value_broken xs = Undetermined) \<longleftrightarrow>
        (xs = [] \<or> (Permitted \<notin> set xs \<and> Undetermined \<in> set xs))"
  have "(some_value_broken ([] :: decision list) = Undetermined) \<longleftrightarrow>
        (([] :: decision list) = [] \<or> (Permitted \<notin> set [] \<and> Undetermined \<in> set []))" using H by blast
  then show False by simp
qed

end
