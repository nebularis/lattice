
type 'a list =
| Nil
| Cons of 'a * 'a list

type decision =
| Permitted
| Denied
| Undetermined

val or3 : decision -> decision -> decision

val and3 : decision -> decision -> decision

val neg3 : decision -> decision

val fold_left : ('a1 -> 'a2 -> 'a1) -> 'a2 list -> 'a1 -> 'a1

val some_value : decision list -> decision

val every_value : decision list -> decision
