(* Adequacy against the reference fixture, each row for a closed and an open binding (ADR-A105,
   L15 as restated, L17), from
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
lemma adequacy_some_pd_closed: "some_value True [Permitted, Denied] = Permitted" by simp
lemma adequacy_every_pd_closed: "every_value True [Permitted, Denied] = Denied" by simp
lemma adequacy_some_pd_open: "some_value False [Permitted, Denied] = Permitted" by simp
lemma adequacy_every_pd_open: "every_value False [Permitted, Denied] = Denied" by simp
lemma adequacy_some_dd_closed: "some_value True [Denied, Denied] = Denied" by simp
lemma adequacy_every_dd_closed: "every_value True [Denied, Denied] = Denied" by simp
lemma adequacy_some_dd_open: "some_value False [Denied, Denied] = Undetermined" by simp
lemma adequacy_every_dd_open: "every_value False [Denied, Denied] = Denied" by simp
lemma adequacy_some_du_closed: "some_value True [Denied, Undetermined] = Undetermined" by simp
lemma adequacy_every_du_closed: "every_value True [Denied, Undetermined] = Denied" by simp
lemma adequacy_some_du_open: "some_value False [Denied, Undetermined] = Undetermined" by simp
lemma adequacy_every_du_open: "every_value False [Denied, Undetermined] = Denied" by simp
lemma adequacy_some_pp_closed: "some_value True [Permitted, Permitted] = Permitted" by simp
lemma adequacy_every_pp_closed: "every_value True [Permitted, Permitted] = Permitted" by simp
lemma adequacy_some_pp_open: "some_value False [Permitted, Permitted] = Permitted" by simp
lemma adequacy_every_pp_open: "every_value False [Permitted, Permitted] = Undetermined" by simp
lemma adequacy_some_pu_closed: "some_value True [Permitted, Undetermined] = Permitted" by simp
lemma adequacy_every_pu_closed: "every_value True [Permitted, Undetermined] = Undetermined" by simp
lemma adequacy_some_pu_open: "some_value False [Permitted, Undetermined] = Permitted" by simp
lemma adequacy_every_pu_open: "every_value False [Permitted, Undetermined] = Undetermined" by simp
lemma adequacy_some_none_closed: "some_value True [] = Denied" by simp
lemma adequacy_every_none_closed: "every_value True [] = Permitted" by simp
lemma adequacy_some_none_open: "some_value False [] = Undetermined" by simp
lemma adequacy_every_none_open: "every_value False [] = Undetermined" by simp
lemma adequacy_negated_pd: "neg3 (some_value True [Permitted, Denied]) = Denied" by simp
lemma adequacy_negated_dd: "neg3 (some_value True [Denied, Denied]) = Permitted" by simp
lemma adequacy_negated_du: "neg3 (some_value True [Denied, Undetermined]) = Undetermined" by simp
lemma adequacy_negated_dd_open: "neg3 (some_value False [Denied, Denied]) = Undetermined" by simp
lemma adequacy_negated_none: "neg3 (some_value True []) = Permitted" by simp
lemma adequacy_negated_none_open: "neg3 (some_value False []) = Undetermined" by simp
(* GATE:END *)

end
