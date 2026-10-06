module Formal_Methods_Kernel : sig
  type decision = Permitted | Denied | Undetermined
  val neg3 : decision -> decision
  val some_value : decision list -> decision
  val every_value : decision list -> decision
end = struct

type decision = Permitted | Denied | Undetermined;;

let rec fold f x1 s = match f, x1, s with f, [], s -> s
               | f, x :: xs, s -> fold f xs (f x s);;

let rec or3 x0 uu = match x0, uu with Permitted, uu -> Permitted
              | Denied, b -> b
              | Undetermined, Permitted -> Permitted
              | Undetermined, Denied -> Undetermined
              | Undetermined, Undetermined -> Undetermined;;

let rec and3 x0 b = match x0, b with Permitted, b -> b
               | Denied, uu -> Denied
               | Undetermined, Permitted -> Undetermined
               | Undetermined, Denied -> Denied
               | Undetermined, Undetermined -> Undetermined;;

let rec neg3 = function Permitted -> Denied
               | Denied -> Permitted
               | Undetermined -> Undetermined;;

let rec some_value = function [] -> Undetermined
                     | x :: xs -> fold or3 xs x;;

let rec every_value = function [] -> Undetermined
                      | x :: xs -> fold and3 xs x;;

end;; (*struct Formal_Methods_Kernel*)
