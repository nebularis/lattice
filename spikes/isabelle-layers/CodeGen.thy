(* SPDX-License-Identifier: MPL-2.0 *)

(* Code generation spike, part two: which of the layer models are executable as written, which
   need a code equation, and what Isabelle's code generator makes of them. The code equations are
   in CodeGenPlain, with an export under the default representations. This theory adds the
   HOL-Library adaptations, so nat and int become target integers and char an abstract type over
   them. Every value below is evaluated by the code generator, so a printed result is the
   generated program's result, not the kernel's. The export_code commands at the end write
   Haskell and SML into the session's export area, retrieved with isabelle export. *)

theory CodeGen
imports CodeGenPlain "HOL-Library.Code_Target_Numeral" "HOL-Library.Code_Abstract_Char"
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

value "enc decimal [''v1'', ''person-email-unique'', ''acme'', ''ada@example.org'']"

text \<open>Percent-encoding of the bytes of "a/b", decoded again, and the dot-segment collision.\<close>

value "pct [97, 47, 98]"
value "dec (pct [97, 47, 98])"
value "norm_path [''a'', ''..'', ''b'']"

text \<open>Fixed-width positions. Under the default representation of nat, dp 19 computes ten to the
eighteenth in unary and does not finish, so this is the value the adaptations make evaluable.\<close>

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

text \<open>The guard, the row-level guard and the confirmation execute through the code equations
in CodeGenPlain. The TD-118 witness, run: the stale writer's request against the stale store.\<close>

value "guard stale_store stale_request"
value "guard_row stale_store stale_request"
value "confirm (commit stale_store stale_request) stale_request"

text \<open>A healthy write and its retry.\<close>

definition fresh_request :: "(nat, nat, nat) request" where
  "fresh_request = \<lparr> target = 17, expected = 41, writer_epoch = 4, txn = 2, digest = 7 \<rparr>"

value "confirm (commit stale_store fresh_request) fresh_request"
value "confirm (commit (commit stale_store fresh_request) fresh_request) fresh_request"
value "rows (commit stale_store fresh_request) 17"

text \<open>Vocabulary's resolution, through its code equation: a binding scoped to 1 dominates an
unscoped one, so it wins in context {1}, and two bindings with incomparable scopes conflict.\<close>

value "resolve {\<lparr> scopes = {}, validity = \<lparr> valid_from = 0, valid_to = None \<rparr>, scheme = 1 :: nat \<rparr>,
               \<lparr> scopes = {1 :: nat}, validity = \<lparr> valid_from = 0, valid_to = None \<rparr>, scheme = 2 \<rparr>} {1} 5 None"
value "resolve {\<lparr> scopes = {1 :: nat}, validity = \<lparr> valid_from = 0, valid_to = None \<rparr>, scheme = 2 :: nat \<rparr>,
               \<lparr> scopes = {2}, validity = \<lparr> valid_from = 0, valid_to = None \<rparr>, scheme = 3 \<rparr>} {1, 2} 5 None"

text \<open>Profile resolution, through its code equation: at a priority tie the candidate needing no
reasoning wins, and two such candidates are Ambiguity.\<close>

value "resolve_dim True {\<lparr> prio = 2, needs_reasoning = False, cand.val = 10 :: nat \<rparr>,
                         \<lparr> prio = 2, needs_reasoning = True, cand.val = 20 \<rparr>,
                         \<lparr> prio = 1, needs_reasoning = False, cand.val = 30 \<rparr>}"
value "resolve_dim True {\<lparr> prio = 2, needs_reasoning = False, cand.val = 10 :: nat \<rparr>,
                         \<lparr> prio = 2, needs_reasoning = False, cand.val = 40 \<rparr>}"

text \<open>Eligibility's decision table, through decide_rel. A small scheme of vehicles: a car and a
van are each a motor vehicle, an electric car is a car, and a boat stands alone.\<close>

definition vehicles :: "string set" where
  "vehicles = {''motor'', ''car'', ''van'', ''ecar'', ''boat''}"

definition vehicle_broader :: "(string \<times> string) set" where
  "vehicle_broader = {(''car'', ''motor''), (''van'', ''motor''), (''ecar'', ''car'')}"

definition motor_cond :: "string set \<Rightarrow> string condition" where
  "motor_cond E = \<lparr> required = {''motor''}, excluded = E, strat = HierarchicalMatch \<rparr>"

text \<open>An electric car stands below a motor vehicle by two steps, so it is Permitted. A van that
is excluded is Denied, though it also stands below the required concept (L10). A motor vehicle,
when cars are excluded, may be a car, so it is Undetermined (L11). A boat matches nothing
required and is Denied, a plane is outside the scheme and Undetermined, and so is an absent
candidate.\<close>

value "decide_rel vehicles vehicle_broader (motor_cond {}) (Some ''ecar'')"
value "decide_rel vehicles vehicle_broader (motor_cond {''van''}) (Some ''van'')"
value "decide_rel vehicles vehicle_broader (motor_cond {''car''}) (Some ''motor'')"
value "decide_rel vehicles vehicle_broader (motor_cond {}) (Some ''boat'')"
value "decide_rel vehicles vehicle_broader (motor_cond {}) (Some ''plane'')"
value "decide_rel vehicles vehicle_broader (motor_cond {}) None"

text \<open>Default inclusion under exact matching admits every member not excluded (L12). On a flat
scheme a hierarchical condition decides only the concepts it names (L14).\<close>

value "decide_rel vehicles vehicle_broader \<lparr> required = {}, excluded = {''van''}, strat = ExactMatch \<rparr> (Some ''car'')"
value "decide_rel vehicles {} (motor_cond {}) (Some ''car'')"

text \<open>A profile of two conditions, composed.\<close>

value "compose AllRequired [decide_rel vehicles vehicle_broader (motor_cond {}) (Some ''ecar''),
                            decide_rel vehicles vehicle_broader (motor_cond {''car''}) (Some ''ecar'')]"
value "compose AnySufficient [decide_rel vehicles vehicle_broader (motor_cond {}) (Some ''ecar''),
                              decide_rel vehicles vehicle_broader (motor_cond {''car''}) (Some ''ecar'')]"

section \<open>Not executable as written\<close>

text \<open>Membership's definitions sit in a locale with no interpretation, so they have no constant
to export until one is given, or until they take their parameters as arguments, as the tuple
encoder and Eligibility's decide_rel do.\<close>

section \<open>Export\<close>

text \<open>Each export is open, so the generated module exports its datatypes' constructors and a
caller can build arguments and read results. The conversions between the target's Integer and
String and the model's nat, char and string are exported for the same reason.\<close>

export_code open
  contains meet closed_range add_months jan31 ccontains off_peak sum_like
  enc decimal pct dec norm_path dp lexlt val
  parts residual settle_at_position
  dconf wfc gate holds exit history
  due_at exercise tolled_end
  compose decide_rel
  guard guard_row commit confirm claim stale_store stale_request fresh_request resolve resolve_dim
  nat_of_integer integer_of_nat char_of_integer integer_of_char String.explode String.implode
  in Haskell module_name Lattice file_prefix lattice_haskell

export_code open
  contains meet closed_range add_months jan31 enc decimal pct dec dp lexlt val
  guard guard_row commit confirm compose decide_rel
  in SML module_name Lattice file_prefix lattice_sml

text \<open>Scala compiles each class to a file named after it, so a type and a constructor whose names
differ only in case, such as nat and Nat, overwrite each other on a case-insensitive filesystem,
which is macOS's default. The target's case_insensitive option renames every such pair.\<close>

export_code open
  contains meet closed_range add_months jan31 enc decimal pct dec dp lexlt val
  guard guard_row commit confirm stale_store stale_request compose decide_rel
  nat_of_integer integer_of_nat String.explode String.implode
  in Scala module_name Lattice file_prefix lattice_scala (case_insensitive)

end
