(* SPDX-License-Identifier: MPL-2.0 *)

(* The ledger's kernel and the shared session agree on what an amount is (ADR-A-FM2's addendum of
   2026-11-18). The kernel, generated from ontology/ledger/README.md section 10, states its own
   amount and imports Complex_Main alone. This theory states that amount at the shared session's
   type too, so a drift between the two fails the build here. Hand-written. *)

theory Agreement
imports Kernel LatticeShared.Amounts
begin

text \<open>One amount, read at the kernel's type and at the shared session's. The statement type-checks
  only while both name the same type, so it is checked when the build reads it, and the proof
  is reflexivity.\<close>

lemma amounts_agree:
  "(v :: ('k, 'n) Kernel.amounts) = (v :: ('k, 'n) Amounts.amounts)"
  by (rule refl)

end
