(* SPDX-License-Identifier: MPL-2.0 *)

(* Code generation spike: which of the layer models are executable as written, which need a code
   equation, and what Isabelle's code generator makes of them. Every value below is evaluated by
   the code generator (the value command), so a printed result is the generated program's
   result, not the kernel's. The export_code commands at the end write Haskell and SML into the
   session's export area, retrieved with isabelle export. *)

theory CodeGen
imports Quantification Vocabulary Behaviour Ledger Instrument Party Persistence Minting Surface EligibilityConditions
begin

section \<open>Executable as written\<close>

text \<open>Ranges and their meet, on integers. The README's half-open mass band, and the Q5 example.\<close>

value "contains (closed_range 1 10) (5 :: int)"
value "contains (meet (closed_range 1 10) (closed_range 20 30)) (5 :: int)"
value "meet (closed_range 1 10) (closed_range 5 30)"

text \<open>Q14, evaluated rather than proved: 31 January plus one and plus two months.\<close>

value "add_months (jan31 2027) 1"
value "add_months (jan31 2027) 2"

text \<open>The wrapping window, and a sum of like and unlike values.\<close>

value "ccontains 24 off_peak 2"
value "sum_like True [\<lparr> amt = 1, in_unit = ''kg'', on_base = Some ''a'' \<rparr>, \<lparr> amt = 2, in_unit = ''kg'', on_base = Some ''a'' \<rparr>]"
value "sum_like True [\<lparr> amt = 1, in_unit = ''kg'', on_base = Some ''a'' \<rparr>, \<lparr> amt = 2, in_unit = ''kg'', on_base = Some ''b'' \<rparr>]"

text \<open>The minting specification's own tuple example, section 4.1, byte for byte.\<close>

value "decimal_prefix.enc [''v1'', ''person-email-unique'', ''acme'', ''ada@example.org'']"

text \<open>Percent-encoding of the bytes of "a/b", decoded again, and the dot-segment collision.\<close>

value "pct [97, 47, 98]"
value "dec (pct [97, 47, 98])"
value "norm_path [''a'', ''..'', ''b'']"

text \<open>Fixed-width positions.\<close>

value "dp 19 (91438 :: nat)"
value "lexlt (dp 2 3) (dp 2 10)"

text \<open>A pro-rata split of 100 across weights 1, 1, 1, with its residual.\<close>

value "parts 100 [1, 1, 1]"
value "residual 100 [1, 1, 1]"

text \<open>Draws settled at one position by key order, whatever the order of proposal.\<close>

value "snd (settle_at_position (\<lambda>_. 5 :: int) (\<lambda>k. \<lparr> acct = (0 :: nat), amount = int k \<rparr>) [4, 3])"
value "snd (settle_at_position (\<lambda>_. 5 :: int) (\<lambda>k. \<lparr> acct = (0 :: nat), amount = int k \<rparr>) [3, 4])"

text \<open>A state tree: the default configuration of a state with two regions, and the gate.\<close>

definition two_regions :: stt where
  "two_regions = St 0 [Rg [St 1 [], St 2 []], Rg [St 3 [], St 4 []]]"

value "dconf two_regions"
value "wfc two_regions (dconf two_regions)"
value "gate duty_gate {1, 3}"
value "gate duty_gate {2, 3}"

text \<open>Anchored time and a window.\<close>

value "due_at (Some 100) 0 24 124"
value "due_at None 0 24 124"
value "exercise break_window 595"

text \<open>Profile composition over the committed kernel.\<close>

value "compose AllRequired [Permitted, Undetermined]"
value "compose AnySufficient [Denied, Undetermined, Permitted]"

text \<open>Key claims.\<close>

value "claim (claim (\<lambda>_. None) (1 :: nat) (10 :: nat)) 1 11 1"

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

text \<open>The TD-118 witness, run: the stale writer's request against the stale store.\<close>

value "guard stale_store stale_request"
value "guard_row stale_store stale_request"
value "confirm (commit stale_store stale_request) stale_request"

text \<open>A healthy write and its retry.\<close>

definition fresh_request :: "(nat, nat, nat) request" where
  "fresh_request = \<lparr> target = 17, expected = 41, writer_epoch = 4, txn = 2, digest = 7 \<rparr>"

value "confirm (commit stale_store fresh_request) fresh_request"
value "confirm (commit (commit stale_store fresh_request) fresh_request) fresh_request"
value "rows (commit stale_store fresh_request) 17"

section \<open>Not executable as written\<close>

text \<open>Vocabulary's resolution quantifies over a set of bindings with THE, and Persistence's
profile resolution takes Max over a set. Both execute once the set is a list, which is how a
caller holds them anyway. Eligibility's hierarchical match is a reflexive-transitive closure of
a relation given as a predicate, so it needs the relation as a finite list of pairs before
rtrancl's own code equations apply. Membership and the tuple encoding sit in locales over a
function, and execute through an interpretation, as decimal_prefix.enc above shows.\<close>

section \<open>Export\<close>

export_code
  contains meet closed_range add_months jan31 ccontains off_peak sum_like
  length_prefix.enc decimal pct dec norm_path dp lexlt val
  parts residual settle_at_position
  dconf wfc gate holds exit history
  due_at exercise tolled_end
  compose
  guard commit confirm claim stale_store stale_request fresh_request
  in Haskell module_name Lattice file_prefix lattice_haskell

export_code
  contains meet closed_range add_months jan31 length_prefix.enc decimal pct dec dp lexlt val
  guard commit confirm
  in SML module_name Lattice file_prefix lattice_sml

end
