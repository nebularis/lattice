(* Formal methods track D: adequacy against the reference fixture (brief §2.3), from
   tools/mork_compilers/src/mork_compilers/test_set_readings.py's MIXES data and
   ReadingTests/NegationTests. Each row is checked by [eval], Isabelle's ML-level normalisation:
   if the implementation disagreed with the reference, these would fail to typecheck, not
   merely fail to prove. *)

theory Adequacy
imports Eligibility
begin

(* GATE:BEGIN AQ *)
lemma adequacy_some_pd: "some_value [Permitted, Denied] = Permitted" by eval
lemma adequacy_every_pd: "every_value [Permitted, Denied] = Denied" by eval
lemma adequacy_some_dd: "some_value [Denied, Denied] = Denied" by eval
lemma adequacy_every_dd: "every_value [Denied, Denied] = Denied" by eval
lemma adequacy_some_du: "some_value [Denied, Undetermined] = Undetermined" by eval
lemma adequacy_every_du: "every_value [Denied, Undetermined] = Denied" by eval
lemma adequacy_some_pp: "some_value [Permitted, Permitted] = Permitted" by eval
lemma adequacy_every_pp: "every_value [Permitted, Permitted] = Permitted" by eval
lemma adequacy_some_pu: "some_value [Permitted, Undetermined] = Permitted" by eval
lemma adequacy_every_pu: "every_value [Permitted, Undetermined] = Undetermined" by eval
lemma adequacy_some_none: "some_value [] = Undetermined" by eval
lemma adequacy_every_none: "every_value [] = Undetermined" by eval
lemma adequacy_negated_pd: "neg3 (some_value [Permitted, Denied]) = Denied" by eval
lemma adequacy_negated_dd: "neg3 (some_value [Denied, Denied]) = Permitted" by eval
lemma adequacy_negated_du: "neg3 (some_value [Denied, Undetermined]) = Undetermined" by eval
(* GATE:END *)

end
