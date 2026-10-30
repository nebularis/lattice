(* SPDX-License-Identifier: MPL-2.0 *)

(* Code generation spike, part one: the code equations a model needs before it executes, and a
   Haskell export under the code generator's default representations, where nat is a Peano
   datatype, int is built on it, and char is a datatype of eight booleans. CodeGen imports this
   theory, adds the HOL-Library adaptations to target integers, and evaluates and exports again.
   Generated code is retrieved with isabelle export and never enters git. *)

theory CodeGenPlain
imports Quantification Vocabulary Behaviour Ledger Instrument Party Persistence Minting Surface EligibilityConditions
begin

section \<open>Executable with a code equation\<close>

text \<open>The guarded write's guard and confirmation quantify over the row option. That is not
executable as an existential, but it is as a case split, and the two are equal, so the case
split is given to the code generator as the implementation.\<close>

lemma guard_code [code]:
  "guard s r \<longleftrightarrow>
     ds_epoch s = writer_epoch r \<and>
     (case rows s (target r) of None \<Rightarrow> False | Some w \<Rightarrow> seq w = expected r \<and> \<not> tomb w) \<and>
     claims s (txn r) = None"
  unfolding guard_def by (auto split: option.splits)

lemma confirm_code [code]:
  "confirm s r =
     (case claims s (txn r) of
        Some d \<Rightarrow> (if d = digest r then Applied else IdempotencyKeyReuse)
      | None \<Rightarrow>
          if ds_epoch s \<noteq> writer_epoch r then EpochChanged
          else if (case rows s (target r) of None \<Rightarrow> False | Some w \<Rightarrow> tomb w) then Gone
          else PreconditionFailed)"
  unfolding confirm_def by (auto split: option.splits)

lemma guard_row_code [code]:
  "guard_row s r \<longleftrightarrow>
     (case rows s (target r) of None \<Rightarrow> False
      | Some w \<Rightarrow> row_epoch w = writer_epoch r \<and> seq w = expected r \<and> \<not> tomb w) \<and>
     claims s (txn r) = None"
  unfolding guard_row_def by (auto split: option.splits)

text \<open>Vocabulary's resolution and Persistence's profile resolution ask whether a set of winners
is a singleton by an existential, and name its element with THE. Neither executes as written,
since the code generator would have to enumerate the element type. HOL's is_singleton and
the_elem state the same thing and execute on a finite set, so the definitions are restated over
them.\<close>

lemma resolve_code [code]:
  "resolve B ctx t fb =
     (if candidates B ctx t = {} then (case fb of None \<Rightarrow> Unbound | Some e \<Rightarrow> Fallback e)
      else if is_singleton (winners (candidates B ctx t))
      then Resolved (the_elem (winners (candidates B ctx t)))
      else Conflict)"
  by (simp add: resolve_def is_singleton_def the_elem_def)

lemma resolve_dim_code [code]:
  "resolve_dim reasoning cs =
     (let cs' = considered reasoning cs in
      if cs' = {} then Baseline
      else if is_singleton (preferred (top cs')) then Winner (the_elem (preferred (top cs')))
      else Ambiguity)"
  unfolding resolve_dim_def is_singleton_def the_elem_def ..

section \<open>Export under the default representations\<close>

text \<open>The conversions between the target's Integer and String and the model's nat, char
and string are exported so a driver can build arguments and read results.\<close>

export_code
  contains meet closed_range add_months jan31 ccontains off_peak sum_like
  enc decimal pct dec norm_path dp lexlt val
  parts residual settle_at_position
  dconf wfc gate holds exit history
  due_at exercise tolled_end
  compose
  guard guard_row commit confirm claim stale_store stale_request resolve resolve_dim
  nat_of_integer integer_of_nat char_of_integer integer_of_char String.explode String.implode
  in Haskell module_name Lattice file_prefix lattice_haskell_plain

end
