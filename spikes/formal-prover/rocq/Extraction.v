(** OCaml extraction (M4): [some_value], [every_value] and [neg3] extracted to OCaml and run
    against the same reference fixtures as Adequacy.v, outside Rocq's own evaluator. *)

Require Import Kernel.
Require Import Eligibility.
From Stdlib Require Extraction.

Extraction Language OCaml.
Set Extraction Output Directory ".".
Extraction "extracted_kernel.ml" some_value every_value neg3.
