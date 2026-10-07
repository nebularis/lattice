
type 'a list =
| Nil
| Cons of 'a * 'a list

type decision =
| Permitted
| Denied
| Undetermined

(** val or3 : decision -> decision -> decision **)

let or3 a b =
  match a with
  | Permitted -> Permitted
  | Denied -> b
  | Undetermined -> (match b with
                     | Permitted -> Permitted
                     | _ -> Undetermined)

(** val and3 : decision -> decision -> decision **)

let and3 a b =
  match a with
  | Permitted -> b
  | Denied -> Denied
  | Undetermined -> (match b with
                     | Permitted -> Undetermined
                     | x -> x)

(** val neg3 : decision -> decision **)

let neg3 = function
| Permitted -> Denied
| Denied -> Permitted
| Undetermined -> Undetermined

(** val fold_left : ('a1 -> 'a2 -> 'a1) -> 'a2 list -> 'a1 -> 'a1 **)

let rec fold_left f l a0 =
  match l with
  | Nil -> a0
  | Cons (b, l0) -> fold_left f l0 (f a0 b)

(** val some_value : decision list -> decision **)

let some_value = function
| Nil -> Undetermined
| Cons (x, rest) -> fold_left or3 rest x

(** val every_value : decision list -> decision **)

let every_value = function
| Nil -> Undetermined
| Cons (x, rest) -> fold_left and3 rest x
