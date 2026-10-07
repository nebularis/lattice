(* Driver for the exported OCaml kernel (M4): checks the same reference fixtures as
   Adequacy.thy, run as plain OCaml outside Isabelle entirely. *)

open Formal_methods_kernel.Formal_Methods_Kernel

let show = function
  | Permitted -> "Permitted"
  | Denied -> "Denied"
  | Undetermined -> "Undetermined"

let check name actual expected =
  if actual = expected then Printf.printf "ok   %s = %s\n" name (show actual)
  else (
    Printf.printf "FAIL %s = %s, expected %s\n" name (show actual) (show expected);
    exit 1)

let () =
  check "some(pd)" (some_value [ Permitted; Denied ]) Permitted;
  check "every(pd)" (every_value [ Permitted; Denied ]) Denied;
  check "some(dd)" (some_value [ Denied; Denied ]) Denied;
  check "every(dd)" (every_value [ Denied; Denied ]) Denied;
  check "some(du)" (some_value [ Denied; Undetermined ]) Undetermined;
  check "every(du)" (every_value [ Denied; Undetermined ]) Denied;
  check "some(pp)" (some_value [ Permitted; Permitted ]) Permitted;
  check "every(pp)" (every_value [ Permitted; Permitted ]) Permitted;
  check "some(pu)" (some_value [ Permitted; Undetermined ]) Permitted;
  check "every(pu)" (every_value [ Permitted; Undetermined ]) Undetermined;
  check "some(none)" (some_value []) Undetermined;
  check "every(none)" (every_value []) Undetermined;
  check "neg(some(pd))" (neg3 (some_value [ Permitted; Denied ])) Denied;
  check "neg(some(dd))" (neg3 (some_value [ Denied; Denied ])) Permitted;
  check "neg(some(du))" (neg3 (some_value [ Denied; Undetermined ])) Undetermined;
  print_endline "all reference fixtures matched by the exported OCaml kernel"
