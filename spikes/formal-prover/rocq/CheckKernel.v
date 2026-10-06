(** Assumption audit for Kernel.v (AR5 of assurance-records.md): confirms no axiom, no
    admitted obligation, closes under the global context for TA1 and TA2. *)
Require Import Kernel.

Print Assumptions or3_and3_monotone.
Print Assumptions neg3_laws.
