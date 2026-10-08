(* Defect S2: "negation maps Undetermined to Denied" -- neg3's third clause is weakened (brief
   §3, S2). Breaks TA2: the fixed point and the involution. *)

theory S2_broken_negation
imports FormalMethodsSpike.Kernel
begin

fun neg3_broken :: "decision \<Rightarrow> decision" where
  "neg3_broken Permitted = Denied"
| "neg3_broken Denied = Permitted"
| "neg3_broken Undetermined = Denied" (* was Undetermined *)

lemma neg3_broken_breaks_fixed_point: "neg3_broken Undetermined \<noteq> Undetermined"
  by simp

lemma neg3_broken_breaks_involution: "neg3_broken (neg3_broken Undetermined) \<noteq> Undetermined"
  by simp

end
