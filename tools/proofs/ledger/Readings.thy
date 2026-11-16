(* SPDX-License-Identifier: MPL-2.0 *)

(* Readings by effective day on the target kernel (plan ledger, LG-20, the seventh group): reading
   A from a recorded balance plus what was recorded after it is reading A from the start, at the
   head with every posting counted it is the recorded balance, the two totals of the flows split
   the same way, and the instance of a debit recorded last and effective second. Hand-written on
   the Kernel extracted from ontology/ledger/README.md section 10. *)

theory Readings
imports Credits
begin

section \<open>Examples, before any theorem\<close>

text \<open>One account at a ceiling of 100. A debit of 30 effective on day 1, a credit of 50 effective on
  day 3, of which 30 was applied, and a debit of 80 recorded last and effective on day 2. The
  recorded balance is 20. Reading A at day 2 is minus 10. Reading B ends at 50 where the account
  rations and at 100 where it refuses.\<close>

definition late_debit :: "(nat \<times> (nat, unit, int) posted) list" where
  "late_debit = [(1, Drawn 0 30), (3, Restored 0 None 50 30 (\<lambda>_. 0)), (2, Drawn 0 80)]"

value "(reading_a (one_account False) 2 3 late_debit 0,
        reading_b (one_account False) 3 3 late_debit 0,
        reading_b (one_account True) 3 3 late_debit 0,
        snd (run (one_account False) (map (asked \<circ> snd) late_debit) (stated (one_account False))) 0)"


section \<open>Reading A from a recorded balance\<close>

lemma counted_split:
  assumes "r \<le> n"
  shows "counted day n es = counted day r es @ counted day (n - r) (drop r es)"
proof -
  have "take n es = take r es @ take (n - r) (drop r es)" using assms take_add[of r "n - r" es] by simp
  then show ?thesis by (simp add: counted_def)
qed

lemma counted_all:
  "\<forall>e\<in>set (take r es). fst e \<le> day \<Longrightarrow> counted day r es = take r es"
  by (simp add: counted_def filter_id_conv)

(* GATE:BEGIN LE1 *)
theorem reading_a_from_a_recorded_balance:
  assumes r: "r \<le> n" and eff: "\<forall>e\<in>set (take r es). fst e \<le> day"
  shows "reading_a B day n es b
           = summed B (map snd (take r es)) b
             + sum_list (map (\<lambda>p. moved B p b) (map snd (counted day (n - r) (drop r es))))"
  using counted_split[OF r, of day es] counted_all[OF eff]
  by (simp add: reading_a_def summed_def)
(* GATE:END *)

(* GATE:BEGIN LE2 *)
theorem reading_a_at_the_head:
  assumes ran: "run B qs (stated B) = (map snd es, bal')" and eff: "\<forall>e\<in>set es. fst e \<le> day"
  shows "reading_a B day (length es) es b = bal' b"
proof -
  have "counted day (length es) es = es" using eff by (simp add: counted_def filter_id_conv)
  then show ?thesis using the_sum_is_the_balance[OF ran, of b] by (simp add: reading_a_def)
qed
(* GATE:END *)

(* GATE:BEGIN LE3 *)
theorem flows_from_recorded_totals:
  assumes r: "r \<le> n" and eff: "\<forall>e\<in>set (take r es). fst e \<le> day"
  shows "flows B day n es b = (fst (flows B day r es b) + fst (flows B day (n - r) (drop r es) b),
                               snd (flows B day r es b) + snd (flows B day (n - r) (drop r es) b))"
    and "counted day r es = take r es"
  using counted_split[OF r, of day es] counted_all[OF eff] by (simp_all add: flows_def Let_def)
(* GATE:END *)


section \<open>The instance kept on purpose\<close>

(* GATE:BEGIN LEn *)
theorem a_debit_recorded_last_and_effective_second:
  "reading_a (one_account False) 2 3 late_debit 0 = -10
   \<and> reading_b (one_account False) 3 3 late_debit 0 = 50
   \<and> reading_b (one_account True) 3 3 late_debit 0 = 100
   \<and> snd (run (one_account False) (map (asked \<circ> snd) late_debit) (stated (one_account False))) 0 = 20"
  by code_simp
(* GATE:END *)

end
