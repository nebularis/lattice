(* SPDX-License-Identifier: MPL-2.0 *)

(* The code equations of the target kernel (plan ledger, LG-36): whether a rank is injective on a
   finite set of keys, and the path of an account unfolded one step. With them a split, a merge and
   a draw up an account's path evaluate on the Kernel and this theory alone, so a session that only
   evaluates copies the two and imports no library. Hand-written on the Kernel extracted from
   ontology/ledger/README.md section 10. *)

theory Evaluation
imports Kernel
begin

section \<open>The two code equations\<close>

text \<open>Whether a rank is injective on a finite set of keys, as a merge that checks its order asks,
  evaluates through the list of the keys. HOL's definition evaluates too, comparing every pair of
  keys, so this equation changes the cost and not the result.\<close>

lemma inj_on_code [code]: "inj_on f (set xs) \<longleftrightarrow> distinct (map f (remdups xs))"
  by (simp add: distinct_map)

text \<open>The path unfolded one step. It is the code equation for a path, so what reads a path
  evaluates, and the walk it gives stops where the parent function has no cycle, which a tree's
  has not. That the walk is the path is proved in Draws.\<close>

lemma path_step [code]:
  "path parent a = (case parent a of None \<Rightarrow> {a} | Some b \<Rightarrow> insert a (path parent b))"
proof (cases "parent a")
  case None
  have "x = a" if "(a, x) \<in> (up parent)\<^sup>*" for x
    using that None by (cases rule: converse_rtranclE) (auto simp: up_def)
  then show ?thesis by (auto simp: path_def None)
next
  case (Some b)
  have "(a, x) \<in> (up parent)\<^sup>* \<longleftrightarrow> x = a \<or> (b, x) \<in> (up parent)\<^sup>*" for x
  proof
    assume "(a, x) \<in> (up parent)\<^sup>*"
    then show "x = a \<or> (b, x) \<in> (up parent)\<^sup>*"
      using Some by (cases rule: converse_rtranclE) (auto simp: up_def)
  next
    assume "x = a \<or> (b, x) \<in> (up parent)\<^sup>*"
    moreover have "(a, b) \<in> up parent" using Some by (simp add: up_def)
    ultimately show "(a, x) \<in> (up parent)\<^sup>*" by (auto intro: converse_rtrancl_into_rtrancl)
  qed
  then show ?thesis by (auto simp: path_def Some)
qed


section \<open>Examples\<close>

text \<open>Each is proved by `code_simp`, so the build fails where the Kernel and this theory no longer
  evaluate it. An exact split of 10 by weights 1 and 2, over the rationals.\<close>

lemma example_an_exact_split:
  "map (proportional {1, 2::nat} (\<lambda>k. if k = 1 then 1 else 2) (10::rat)) [1, 2] = [10 / 3, 20 / 3]"
  by code_simp

text \<open>A draw of 4 on account 2, whose parent is account 1. The path is read, both accounts are
  debited, and what is available at account 2 was the least along its path.\<close>

lemma example_a_draw_up_a_path:
  "(case draw_on (path (map_of [(2::nat, 1::nat)]) 2) (4::int) (\<lambda>a. if a = 1 then 10 else 6) of
     (bal, done) \<Rightarrow> (map bal [1, 2], done)) = ([6, 2], True)"
  "available (map_of [(2::nat, 1::nat)]) (\<lambda>a. if a = 1 then 10 else 6) 2 = (6::int)"
  by code_simp+

text \<open>Two requests of 6 against 10, under a policy that checks its order, with one rank between
  them. The merge reads whether the rank is injective on the keys and refuses.\<close>

lemma example_an_order_checked:
  "(case merge_of (\<lparr>refuses = False, ranked = True, tie = None, leaves = False, unmixed = False\<rparr> :: (nat, int) policy)
            (\<lambda>_. 0) 10 {1, 2} (\<lambda>_. 6) of
      Granted _ _ \<Rightarrow> None | Refused why \<Rightarrow> Some why) = Some Unranked"
  by code_simp

end
