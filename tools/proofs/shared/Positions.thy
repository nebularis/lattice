(* SPDX-License-Identifier: MPL-2.0 *)

(* A position, as ADR-A-FM2's addendum of 2026-11-18 states it: a natural number on a named axis,
   compared only within one axis. Hand-written, in the shared session, LatticeShared. *)

theory Positions
imports "HOL-Library.Sublist"
begin

section \<open>A position\<close>

text \<open>A position is a natural number on a named axis, and two positions are compared only within
  one axis. The axis is not a type here, so the checker does not refuse a comparison across two
  axes. Whoever states two positions keeps them on one axis.\<close>

type_synonym position = nat

text \<open>On a sequence the writer assigns each position, the next number at each write, with no gap.
  The position a sequence of writes has reached is the number of its writes, so 0 means nothing
  is written yet and position n is the n-th write.\<close>

definition reached :: "'w list \<Rightarrow> position" where
  "reached ws = length ws"


section \<open>A sequence\<close>

(* GATE:BEGIN SP1 *)
theorem nothing_written_is_position_zero:
  "reached ws = 0 \<longleftrightarrow> ws = []"
  by (simp add: reached_def)
(* GATE:END *)

(* GATE:BEGIN SP2 *)
theorem a_write_takes_the_successor:
  "reached (ws @ [w]) = Suc (reached ws)"
  by (simp add: reached_def)
(* GATE:END *)


section \<open>Positions on one axis\<close>

(* GATE:BEGIN SP3 *)
theorem positions_are_totally_ordered:
  "(p :: position) \<le> q \<or> q \<le> p"
  by (rule nat_le_linear)

theorem no_position_between_successors:
  "(p :: position) < q \<Longrightarrow> Suc p \<le> q"
  by simp
(* GATE:END *)

text \<open>A position names one state of its sequence. Two prefixes of one sequence that have reached
  the same position are the same writes, so a read pinned to a position reads a fixed fact.\<close>

(* GATE:BEGIN SP4 *)
theorem a_position_pins_one_prefix:
  assumes us: "prefix us ws" and vs: "prefix vs ws" and same: "reached us = reached vs"
  shows "us = vs"
proof -
  have len: "length us = length vs" using same by (simp add: reached_def)
  have uv: "prefix us vs" by (rule prefix_length_prefix[OF us vs]) (simp add: len)
  have vu: "prefix vs us" by (rule prefix_length_prefix[OF vs us]) (simp add: len)
  show ?thesis using uv vu by (rule prefix_order.antisym)
qed
(* GATE:END *)

end
