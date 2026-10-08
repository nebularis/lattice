(* Driver for the extracted kernel (M4): checks the same oracle fixtures as Adequacy.v, run as
   plain OCaml outside Rocq's evaluator. *)

open Extracted_kernel

let mk l = List.fold_right (fun x acc -> Cons (x, acc)) l Nil

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
  (* MIXES fixtures from tools/mork_compilers/src/mork_compilers/test_set_readings.py *)
  check "some(pd)" (some_value (mk [ Permitted; Denied ])) Permitted;
  check "every(pd)" (every_value (mk [ Permitted; Denied ])) Denied;
  check "some(dd)" (some_value (mk [ Denied; Denied ])) Denied;
  check "every(dd)" (every_value (mk [ Denied; Denied ])) Denied;
  check "some(du)" (some_value (mk [ Denied; Undetermined ])) Undetermined;
  check "every(du)" (every_value (mk [ Denied; Undetermined ])) Denied;
  check "some(pp)" (some_value (mk [ Permitted; Permitted ])) Permitted;
  check "every(pp)" (every_value (mk [ Permitted; Permitted ])) Permitted;
  check "some(pu)" (some_value (mk [ Permitted; Undetermined ])) Permitted;
  check "every(pu)" (every_value (mk [ Permitted; Undetermined ])) Undetermined;
  check "some(none)" (some_value Nil) Undetermined;
  check "every(none)" (every_value Nil) Undetermined;
  check "neg(some(pd))" (neg3 (some_value (mk [ Permitted; Denied ]))) Denied;
  check "neg(some(dd))" (neg3 (some_value (mk [ Denied; Denied ]))) Permitted;
  check "neg(some(du))" (neg3 (some_value (mk [ Denied; Undetermined ]))) Undetermined;
  print_endline "all oracle fixtures matched by the extracted OCaml kernel"
