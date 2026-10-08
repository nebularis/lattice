(** Defect S4: a theorem left with [Admitted] (brief §3, S4). gate.py's banned-marker scan
    finds this outside defects/ (see env/gate_selftest.py); a defect file is exempted, since the
    marker here is the defect, not a gate failure. *)

Require Import Kernel.
Require Import Eligibility.
From Stdlib Require Import List.
Import ListNotations.

(** A false claim (the real definitions do not agree, defect S3), left unproved rather than
    refuted. The assumption audit (Print Assumptions) would report this file's use of
    [left_with_admitted] as resting on an admitted obligation, and the gate's source scan finds
    the keyword directly. *)
Theorem left_with_admitted : forall xs, some_value xs = every_value xs.
Proof.
Admitted.
