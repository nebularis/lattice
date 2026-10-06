(** The MINOR change target (brief §4): a [reading] selector over the kernel's three readings,
    dispatching to [some_value]/[every_value] (track TL) or returning a single bound value
    unchanged. Step 1 of the scripted MINOR-change measure (M3): the inductive carries exactly
    the three readings in play so far. Step 2 (a later commit) adds [MostValueR] and measures
    the diff needed to repair this file. *)

Require Import Kernel.
Require Import Eligibility.
From Stdlib Require Import List.
Import ListNotations.

Inductive reading := SingleValueR | SomeValueR | EveryValueR.

Definition apply_reading (r : reading) (d : decision) (xs : list decision) : decision :=
  match r with
  | SingleValueR => d
  | SomeValueR => some_value xs
  | EveryValueR => every_value xs
  end.

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
