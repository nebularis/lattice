(* Adequacy against the reference fixture, from
   tools/mork_compilers/src/mork_compilers/test_set_readings.py's MIXES data and
   ReadingTests/NegationTests. Each row is checked by [simp], Isabelle's own kernel-checked
   simplifier, unfolding the fun equations directly: if the implementation disagreed with the
   reference, these would fail to prove, inside the kernel, not merely fail to typecheck.
   Previously checked by [eval] (E1.4, the formal-methods epic's second review \u00a72.4): that
   method is a code-generator shortcut, not the kernel, and gate.py's assumption audit now flags
   it specifically for that reason. For a three-constructor finite domain [simp] establishes the
   same facts inside the kernel at no extra cost. Restated from
   spikes/formal-prover/isabelle/Adequacy.thy (track D). *)

theory Adequacy
imports Eligibility
begin

(* GATE:BEGIN AQ *)
lemma adequacy_some_pd: "some_value [Permitted, Denied] = Permitted" by simp
lemma adequacy_every_pd: "every_value [Permitted, Denied] = Denied" by simp
lemma adequacy_some_dd: "some_value [Denied, Denied] = Denied" by simp
lemma adequacy_every_dd: "every_value [Denied, Denied] = Denied" by simp
lemma adequacy_some_du: "some_value [Denied, Undetermined] = Undetermined" by simp
lemma adequacy_every_du: "every_value [Denied, Undetermined] = Denied" by simp
lemma adequacy_some_pp: "some_value [Permitted, Permitted] = Permitted" by simp
lemma adequacy_every_pp: "every_value [Permitted, Permitted] = Permitted" by simp
lemma adequacy_some_pu: "some_value [Permitted, Undetermined] = Permitted" by simp
lemma adequacy_every_pu: "every_value [Permitted, Undetermined] = Undetermined" by simp
lemma adequacy_some_none: "some_value [] = Undetermined" by simp
lemma adequacy_every_none: "every_value [] = Undetermined" by simp
lemma adequacy_negated_pd: "neg3 (some_value [Permitted, Denied]) = Denied" by simp
lemma adequacy_negated_dd: "neg3 (some_value [Denied, Denied]) = Permitted" by simp
lemma adequacy_negated_du: "neg3 (some_value [Denied, Undetermined]) = Undetermined" by simp
(* GATE:END *)

end
