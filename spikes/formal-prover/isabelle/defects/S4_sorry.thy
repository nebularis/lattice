(* Defect S4: a theorem left with [sorry] (brief §3, S4). gate.py's banned-marker scan finds
   this outside defects/ (see check_s4.py); a defect file is exempted, since the marker here is
   the defect, not a gate failure. *)

theory S4_sorry
imports FormalMethodsSpike.Kernel FormalMethodsSpike.Eligibility
begin

(* A false claim (the real definitions do not agree, defect S3), left unproved rather than
   refuted. Isabelle reports this theorem's proof as resting on "sorry", visible in the theory's
   own output and found directly by the gate's source scan. *)
lemma left_with_sorry: "\<forall>xs. some_value xs = every_value xs"
  sorry

end
