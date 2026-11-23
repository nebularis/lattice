(* SPDX-License-Identifier: MPL-2.0 *)

(* The interpreter exported to Scala, used as generated. An atom is a string literal, which the
   Scala target writes as a String, and a position is a natural number, which
   Code_Target_Numeral writes over the target's integers. The export goes to the session's export
   area, never into the tree, and is retrieved with isabelle export. *)

theory Export
  imports Laws "HOL-Library.Code_Target_Numeral"
begin

text \<open>exec and replay at one atom type, so the generated code carries the instance of equality it
  needs and a caller supplies none.\<close>

definition exec_literal :: "String.literal state \<Rightarrow> String.literal val \<Rightarrow> String.literal params \<Rightarrow>
    String.literal command \<Rightarrow> String.literal state \<times> outcome" where
  "exec_literal = exec"

definition replay_literal :: "String.literal state \<Rightarrow>
    (String.literal val \<times> String.literal params \<times> String.literal command) list \<Rightarrow> String.literal state" where
  "replay_literal = replay"

text \<open>Scala compiles each class to a file named after it, so two names that differ only in case
  overwrite each other on a case-insensitive filesystem, Windows's and macOS's default. The
  target's case_insensitive option renames every such pair.\<close>

export_code open
  exec_literal replay_literal create_if_absent delta_replace append_event key_claim_write
  nat_of_integer integer_of_nat
  in Scala module_name MultiStoreModel file_prefix multi_store_model (case_insensitive)

end
