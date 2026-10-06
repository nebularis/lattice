(* Defect S3: an interface assumption no instantiation can discharge (brief §3, S3; track A5's
   non-vacuity concern, surfaced at this scale). The locale [reading_interface] assumes
   [some_value] and [every_value] always agree -- which is false in general (the [pd] fixture),
   so no interpretation, real or otherwise, can discharge it. *)

theory S3_vacuous_interface
imports FormalMethodsSpike.Kernel FormalMethodsSpike.Eligibility
begin

locale reading_interface =
  fixes ri_some :: "decision list \<Rightarrow> decision"
    and ri_every :: "decision list \<Rightarrow> decision"
  assumes ri_agree: "ri_some xs = ri_every xs"

(* The real definitions disagree on this very fixture (adequacy row pd), so the assumption is
   not merely unproved here -- it is refutable, for any candidate pair of functions equal to
   these on [Permitted, Denied]. *)
lemma real_definitions_do_not_agree:
  "some_value [Permitted, Denied] \<noteq> every_value [Permitted, Denied]"
  by eval

lemma real_definitions_cannot_satisfy_ri_agree:
  "\<not> (\<forall>xs. some_value xs = every_value xs)"
  using real_definitions_do_not_agree by blast

(* The obvious interpretation fails: no proof of [ri_agree] exists for the real functions. The
   attempt below is commented out, since an actually-failing command would abort this theory's
   (and the whole session's) build; [real_definitions_cannot_satisfy_ri_agree] above proves,
   independently, that no such proof could ever be supplied.

   interpretation real_instantiation: reading_interface some_value every_value
     by unfold_locales (metis real_definitions_do_not_agree)
*)

end
