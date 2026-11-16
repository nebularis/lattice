(* SPDX-License-Identifier: MPL-2.0 *)

(* Credits and the sum on the target kernel (plan ledger, LG-20, the sixth group): each step of a
   run moves an account by what its posting records, recorded balances are right exactly when
   each follows from the one before it, the sum of what a run posted is the balance it ends at,
   and what a credit applies and cuts depends on the path alone, with no cut negative.
   Hand-written on the Kernel extracted from ontology/ledger/README.md section 10. *)

theory Credits
imports Pots
begin

section \<open>Examples, before any theorem\<close>

text \<open>One account holding 100 under a ceiling of 100. A draw of 30, a restoration of 50, of which 30
  is applied, and a draw of 80 leave 20, and the sum of what was posted gives the same.\<close>

definition one_account :: "bool \<Rightarrow> (nat, unit, int) book" where
  "one_account r = \<lparr>parent_of = (\<lambda>_. None), stated = (\<lambda>_. 100), ceiling = (\<lambda>_. 100),
                     restores = (\<lambda>_ _. True), refusing = (\<lambda>_. r)\<rparr>"

definition three_requests :: "(nat, unit, int) request list" where
  "three_requests = [Draw 0 30, Restore 0 None 50, Draw 0 80]"

value "(case run (one_account False) three_requests (stated (one_account False)) of
          (ps, bal) \<Rightarrow> (bal 0, summed (one_account False) ps 0))"

lemma example_the_sum_is_the_balance:
  "(case run (one_account False) three_requests (stated (one_account False)) of
     (ps, bal) \<Rightarrow> (bal 0, summed (one_account False) ps 0)) = (20, 20)"
  by code_simp


section \<open>Each step moves an account by what its posting records\<close>

(* GATE:BEGIN LB1 *)
theorem the_step_agrees_with_debit_and_credit:
  "snd (post B q bal) b = bal b + (case fst (post B q bal) of None \<Rightarrow> 0 | Some p \<Rightarrow> moved B p b)"
proof (cases q)
  case (Draw a x)
  then show ?thesis by (auto simp: post_def draw_on_def debit_def moved_def)
next
  case (Restore a c x)
  then show ?thesis by (auto simp: post_def credit_def Let_def moved_def)
qed
(* GATE:END *)


section \<open>The sum of what a run posted is the balance it ends at\<close>

lemma run_sum:
  "run B qs bal = (ps, bal') \<Longrightarrow> bal' b = bal b + sum_list (map (\<lambda>p. moved B p b) ps)"
proof (induction qs arbitrary: bal ps bal')
  case Nil
  then show ?case by simp
next
  case (Cons q qs)
  obtain p bal1 where st: "post B q bal = (p, bal1)" by (cases "post B q bal")
  obtain ps1 bal2 where rec: "run B qs bal1 = (ps1, bal2)" by (cases "run B qs bal1")
  have out: "ps = (case p of None \<Rightarrow> ps1 | Some e \<Rightarrow> e # ps1)" "bal' = bal2"
    using Cons.prems st rec by simp_all
  have step: "bal1 b = bal b + (case p of None \<Rightarrow> 0 | Some e \<Rightarrow> moved B e b)"
    using the_step_agrees_with_debit_and_credit[of B q bal b] st by simp
  show ?case using Cons.IH[OF rec] step out by (cases p) simp_all
qed

(* GATE:BEGIN LU1 *)
theorem the_sum_is_the_balance:
  "run B qs (stated B) = (ps, bal') \<Longrightarrow> summed B ps b = bal' b"
  using run_sum[of B qs "stated B" ps bal' b] by (simp add: summed_def)
(* GATE:END *)


section \<open>Recorded balances are right exactly when each follows from the one before\<close>

text \<open>The balances a run passes through, the first before any request.\<close>

fun trace :: "('a, 'c, 'n::linordered_idom) book \<Rightarrow> ('a, 'c, 'n) request list \<Rightarrow> ('a, 'n) balances \<Rightarrow> ('a, 'n) balances list" where
  "trace B [] bal = [bal]"
| "trace B (q # qs) bal = bal # trace B qs (snd (post B q bal))"

(* GATE:BEGIN LB2 *)
theorem recorded_balances_follow_step_by_step:
  "bs = trace B qs bal \<longleftrightarrow>
     length bs = Suc (length qs) \<and> bs ! 0 = bal
     \<and> (\<forall>i<length qs. bs ! Suc i = snd (post B (qs ! i) (bs ! i)))"
proof (induction qs arbitrary: bs bal)
  case Nil
  show ?case
  proof
    assume "bs = trace B [] bal"
    then show "length bs = Suc (length []) \<and> bs ! 0 = bal \<and> (\<forall>i<length []. bs ! Suc i = snd (post B ([] ! i) (bs ! i)))"
      by simp
  next
    assume "length bs = Suc (length []) \<and> bs ! 0 = bal \<and> (\<forall>i<length []. bs ! Suc i = snd (post B ([] ! i) (bs ! i)))"
    then show "bs = trace B [] bal" by (cases bs) simp_all
  qed
next
  case (Cons q qs)
  show ?case
  proof
    assume e: "bs = trace B (q # qs) bal"
    have IH: "length (trace B qs (snd (post B q bal))) = Suc (length qs)
                \<and> trace B qs (snd (post B q bal)) ! 0 = snd (post B q bal)
                \<and> (\<forall>i<length qs. trace B qs (snd (post B q bal)) ! Suc i
                     = snd (post B (qs ! i) (trace B qs (snd (post B q bal)) ! i)))"
      using Cons.IH[of "trace B qs (snd (post B q bal))" "snd (post B q bal)"] by simp
    show "length bs = Suc (length (q # qs)) \<and> bs ! 0 = bal
            \<and> (\<forall>i<length (q # qs). bs ! Suc i = snd (post B ((q # qs) ! i) (bs ! i)))"
    proof (intro conjI allI impI)
      show "length bs = Suc (length (q # qs))" using e IH by simp
      show "bs ! 0 = bal" using e by simp
    next
      fix i
      assume "i < length (q # qs)"
      then show "bs ! Suc i = snd (post B ((q # qs) ! i) (bs ! i))"
        using e IH by (cases i) simp_all
    qed
  next
    assume a: "length bs = Suc (length (q # qs)) \<and> bs ! 0 = bal
                 \<and> (\<forall>i<length (q # qs). bs ! Suc i = snd (post B ((q # qs) ! i) (bs ! i)))"
    obtain c cs where bs: "bs = c # cs" using a by (cases bs) simp_all
    have c: "c = bal" using a bs by simp
    have cs: "length cs = Suc (length qs) \<and> cs ! 0 = snd (post B q bal)
                \<and> (\<forall>i<length qs. cs ! Suc i = snd (post B (qs ! i) (cs ! i)))"
    proof (intro conjI allI impI)
      show "length cs = Suc (length qs)" using a bs by simp
      have "bs ! Suc 0 = snd (post B ((q # qs) ! 0) (bs ! 0))" using a by simp
      then show "cs ! 0 = snd (post B q bal)" using bs c by simp
    next
      fix i
      assume i: "i < length qs"
      have "bs ! Suc (Suc i) = snd (post B ((q # qs) ! Suc i) (bs ! Suc i))" using a i by simp
      then show "cs ! Suc i = snd (post B (qs ! i) (cs ! i))" using bs by simp
    qed
    have "cs = trace B qs (snd (post B q bal))" using Cons.IH cs by blast
    then show "bs = trace B (q # qs) bal" using bs c by simp
  qed
qed
(* GATE:END *)


section \<open>What a credit applies and cuts\<close>

(* GATE:BEGIN LU2 *)
theorem a_credit_depends_on_its_path:
  assumes same: "\<forall>b\<in>path parent a. bal b = bal2 b"
  shows "fst (credit parent cap accepts a x bal) = fst (credit parent cap accepts a x bal2)"
    and "fst (snd (credit parent cap accepts a x bal)) = fst (snd (credit parent cap accepts a x bal2))"
    and "0 \<le> fst (snd (credit parent cap accepts a x bal)) b"
proof -
  have aa: "bal a = bal2 a" using same by simp
  show "fst (credit parent cap accepts a x bal) = fst (credit parent cap accepts a x bal2)"
    using aa by (simp add: credit_def Let_def)
  show "fst (snd (credit parent cap accepts a x bal)) = fst (snd (credit parent cap accepts a x bal2))"
    using aa same by (auto simp: credit_def Let_def fun_eq_iff)
  show "0 \<le> fst (snd (credit parent cap accepts a x bal)) b"
    by (simp add: credit_def Let_def)
qed
(* GATE:END *)


section \<open>Three instances kept on purpose\<close>

text \<open>The sketch on balances under post-once, its section 3. One account at a ceiling of 100, a debit
  of 20, a credit of 50 cut to the ceiling, and a debit of 30. Stepped, the balance is 70. The
  ceiling applied once to the whole fold gives 100.\<close>

(* GATE:BEGIN LB1n *)
theorem the_ceiling_applied_once_overstates:
  "snd (run \<lparr>parent_of = (\<lambda>_. None), stated = (\<lambda>_. 100), ceiling = (\<lambda>_. 100), restores = (\<lambda>_ _. True), refusing = (\<lambda>_. False)\<rparr>
          [Draw (0::nat) 20, Restore 0 (None :: unit option) 50, Draw 0 30] (\<lambda>_. 100 :: int)) 0 = 70
   \<and> min (100 - 20 + 50 - 30) (100::int) = 100"
  by code_simp
(* GATE:END *)

text \<open>The same sketch, its section 4.8. An annual cap of 20, account 0, accepting recoveries only,
  kind 1, an aggregate of 10, account 1, under it, and sections of 10, accounts 2 and 3, under the
  aggregate, every ceiling its stated amount. A loss of 10 at 2, a reinstatement, kind 0, at the
  aggregate, a recovery of 2 at 2 and a loss of 3 at 3. The aggregate steps to 7, the sum with its
  cuts gives 7, and the sum with no cuts gives 9.\<close>

(* GATE:BEGIN LU1n *)
theorem the_sum_with_no_cuts_overstates:
  "(case run \<lparr>parent_of = map_of [(1::nat, 0::nat), (2, 1), (3, 1)], stated = (\<lambda>a. if a = 0 then 20 else 10),
             ceiling = (\<lambda>a. if a = 0 then 20 else 10), restores = (\<lambda>b c. b \<noteq> 0 \<or> c = Some (1::nat)), refusing = (\<lambda>_. False)\<rparr>
             [Draw 2 10, Restore 1 (Some 0) 10, Restore 2 (Some 1) 2, Draw 3 3] (\<lambda>a. if a = 0 then 20 else (10::int)) of
     (ps, bal) \<Rightarrow>
       (bal 1,
        summed \<lparr>parent_of = map_of [(1::nat, 0::nat), (2, 1), (3, 1)], stated = (\<lambda>a. if a = 0 then 20 else 10),
                ceiling = (\<lambda>a. if a = 0 then 20 else 10), restores = (\<lambda>b c. b \<noteq> 0 \<or> c = Some (1::nat)), refusing = (\<lambda>_. False)\<rparr> ps 1,
        summed \<lparr>parent_of = map_of [(1::nat, 0::nat), (2, 1), (3, 1)], stated = (\<lambda>a. if a = 0 then 20 else 10),
                ceiling = (\<lambda>a. if a = 0 then 20 else 10), restores = (\<lambda>b c. b \<noteq> 0 \<or> c = Some (1::nat)), refusing = (\<lambda>_. False)\<rparr>
          (map (\<lambda>p. case p of Drawn a x \<Rightarrow> Drawn a x | Restored a c x ap cuts \<Rightarrow> Restored a c x ap (\<lambda>_. 0)) ps) 1))
   = (7, 7, 9)"
  by code_simp
(* GATE:END *)

text \<open>A counterexample to the law as the plan states it. Every ceiling equals its stated amount
  and every credit lands on a leaf, but the leaf does not accept the credit's kind and its parent
  does. Account 1, a leaf of 10 under account 0 of 10, is drawn 5 and credited 5 twice. The first
  credit restores the parent, the leaf keeps its room, and the second is applied in full at the
  leaf and cut by 5 at the parent.\<close>

(* GATE:BEGIN LU3n *)
theorem a_leaf_that_refuses_its_credit_leaves_a_cut:
  "map (\<lambda>p. case p of Drawn a x \<Rightarrow> 0 | Restored a c x ap cuts \<Rightarrow> cuts 0)
     (fst (run \<lparr>parent_of = map_of [(1::nat, 0::nat)], stated = (\<lambda>_. 10), ceiling = (\<lambda>_. 10),
                restores = (\<lambda>b (_ :: unit option). b = 0), refusing = (\<lambda>_. False)\<rparr>
           [Draw 1 5, Restore 1 None 5, Restore 1 None 5] (\<lambda>_. 10 :: int))) = [0, 0, 5]"
  by code_simp
(* GATE:END *)

end
