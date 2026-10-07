(* Code generation (M4, M5): export the kernel and set-reading functions to OCaml and Haskell,
   to compare generated code across targets (brief §5, M4/M5). *)

theory Export
imports Eligibility
begin

export_code Permitted Denied Undetermined some_value every_value neg3 in OCaml
  module_name Formal_Methods_Kernel file_prefix "export-ocaml"

export_code Permitted Denied Undetermined some_value every_value neg3 in Haskell
  module_name Formal_Methods_Kernel file_prefix "export-haskell"

end
