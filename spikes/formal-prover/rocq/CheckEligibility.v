(** Assumption audit for Eligibility.v (AR5 of assurance-records.md). *)
Require Import Eligibility.

Print Assumptions some_value_spec.
Print Assumptions every_value_spec.
Print Assumptions some_every_value_monotone.
Print Assumptions negate_after_is_every_of_negated.
Print Assumptions negate_before_same_reading_disagrees.
