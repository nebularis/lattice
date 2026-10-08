(** The MINOR change target (brief §4): a [reading] selector over the kernel's readings,
    dispatching to [some_value]/[every_value] (track TL), [most_value] (majority rule, added in
    step 2 of the scripted MINOR-change measure, M3), or returning a single bound value
    unchanged. *)

Require Import Kernel.
Require Import Eligibility.
From Stdlib Require Import List Arith.
Import ListNotations.

Inductive reading := SingleValueR | SomeValueR | EveryValueR | MostValueR.

Definition count_eq (d : decision) (xs : list decision) : nat :=
  length (filter (fun x => if decision_eq_dec x d then true else false) xs).

Definition most_value (xs : list decision) : decision :=
  let p := count_eq Permitted xs in
  let d := count_eq Denied xs in
  if Nat.ltb d p then Permitted else if Nat.ltb p d then Denied else Undetermined.

Definition apply_reading (r : reading) (d : decision) (xs : list decision) : decision :=
  match r with
  | SingleValueR => d
  | SomeValueR => some_value xs
  | EveryValueR => every_value xs
  | MostValueR => most_value xs
  end.

(* GATE:BEGIN TR3 *)
Theorem apply_reading_most_matches_spec : forall d xs,
  apply_reading MostValueR d xs = most_value xs.
(* GATE:END *)
Proof. reflexivity. Qed.

(* GATE:BEGIN TR1 *)
Theorem apply_reading_some_matches_spec : forall d xs,
  apply_reading SomeValueR d xs = some_value xs.
(* GATE:END *)
Proof. reflexivity. Qed.

(* GATE:BEGIN TR2 *)
Theorem apply_reading_every_matches_spec : forall d xs,
  apply_reading EveryValueR d xs = every_value xs.
(* GATE:END *)
Proof. reflexivity. Qed.
