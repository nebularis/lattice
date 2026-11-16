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


section \<open>No cut where every ceiling is its stated amount and every credit is on a leaf\<close>

text \<open>The room of an account is its ceiling less its balance. Under a tree, the invariant is that
  every account has at least the rooms of the leaves below it together, and no room is negative.
  A draw adds to the rooms on its path, and a leaf is on a path only at its foot. A credit at a
  leaf that accepts its kind applies at most the leaf's room, which every account above has, so
  each accepting account takes all of it. `credit` alone needs the leaf to accept the kind, and
  `post` refuses a credit whose account does not (LG-Q29 (b)), so `run` needs nothing of it.\<close>

lemma lu3_draw_step:
  assumes tr: "tree A P" and d: "d \<in> A" and x0: "0 \<le> x"
    and inv: "\<forall>b\<in>A. (\<Sum>a\<in>{a\<in>A. (\<forall>e\<in>A. a \<in> path P e \<longrightarrow> e = a) \<and> b \<in> path P a}. cap a - bal a) \<le> cap b - bal b"
  shows "\<forall>b\<in>A. (\<Sum>a\<in>{a\<in>A. (\<forall>e\<in>A. a \<in> path P e \<longrightarrow> e = a) \<and> b \<in> path P a}. cap a - debit (path P d) x bal a)
               \<le> cap b - debit (path P d) x bal b"
proof
  fix b
  assume b: "b \<in> A"
  let ?S = "{a\<in>A. (\<forall>e\<in>A. a \<in> path P e \<longrightarrow> e = a) \<and> b \<in> path P a}"
  have fin: "finite ?S" by (rule finite_subset[of _ A]) (use tr in \<open>auto simp: tree_def\<close>)
  have pt: "cap a - debit (path P d) x bal a = (cap a - bal a) + (if a = d then x else 0)" if "a \<in> ?S" for a
  proof -
    have "a \<in> path P d \<longleftrightarrow> a = d" using that d by auto
    then show ?thesis by (simp add: debit_def)
  qed
  have s1: "(\<Sum>a\<in>?S. cap a - debit (path P d) x bal a) = (\<Sum>a\<in>?S. (cap a - bal a) + (if a = d then x else 0))"
    by (rule sum.cong[OF refl]) (erule pt)
  have s2: "(\<Sum>a\<in>?S. (cap a - bal a) + (if a = d then x else 0)) = (\<Sum>a\<in>?S. cap a - bal a) + (if d \<in> ?S then x else 0)"
    using fin by (simp add: sum.distrib sum.delta)
  have dS: "d \<in> ?S \<Longrightarrow> b \<in> path P d" by simp
  have rb: "cap b - debit (path P d) x bal b = (cap b - bal b) + (if b \<in> path P d then x else 0)"
    by (simp add: debit_def)
  have "(\<Sum>a\<in>?S. cap a - bal a) \<le> cap b - bal b" using inv b by blast
  then show "(\<Sum>a\<in>?S. cap a - debit (path P d) x bal a) \<le> cap b - debit (path P d) x bal b"
    using s1 s2 dS rb x0 by (auto split: if_splits)
qed

lemma lu3_credit_step:
  assumes tr: "tree A P" and a0: "a0 \<in> A" and leaf: "\<forall>e\<in>A. a0 \<in> path P e \<longrightarrow> e = a0" and acc: "acc a0"
    and le: "\<forall>z. bal z \<le> cap z"
    and inv: "\<forall>b\<in>A. (\<Sum>a\<in>{a\<in>A. (\<forall>e\<in>A. a \<in> path P e \<longrightarrow> e = a) \<and> b \<in> path P a}. cap a - bal a) \<le> cap b - bal b"
    and cr: "credit P cap acc a0 x bal = (ap, cuts, bal')"
  shows "(\<forall>b. cuts b = 0) \<and> (\<forall>z. bal' z \<le> cap z)
         \<and> (\<forall>b\<in>A. (\<Sum>a\<in>{a\<in>A. (\<forall>e\<in>A. a \<in> path P e \<longrightarrow> e = a) \<and> b \<in> path P a}. cap a - bal' a) \<le> cap b - bal' b)"
proof -
  have ap: "ap = max 0 (min x (cap a0 - bal a0))" using cr by (simp add: credit_def Let_def)
  have ap0: "0 \<le> ap" and ap_le: "ap \<le> cap a0 - bal a0" using ap le by auto
  have room_ge: "cap a0 - bal a0 \<le> cap z - bal z" if z: "z \<in> path P a0" for z
  proof -
    have zA: "z \<in> A" using path_in_tree[OF tr a0] z by blast
    let ?S = "{a\<in>A. (\<forall>e\<in>A. a \<in> path P e \<longrightarrow> e = a) \<and> z \<in> path P a}"
    have fin: "finite ?S" by (rule finite_subset[of _ A]) (use tr in \<open>auto simp: tree_def\<close>)
    have mem: "a0 \<in> ?S" using a0 leaf z by simp
    have "cap a0 - bal a0 \<le> (\<Sum>a\<in>?S. cap a - bal a)"
      by (rule member_le_sum[OF mem _ fin]) (use le in auto)
    also have "\<dots> \<le> cap z - bal z" using inv zA by blast
    finally show ?thesis .
  qed
  have take: "min ap (cap z - bal z) = ap" if "z \<in> path P a0" for z
    using order_trans[OF ap_le room_ge[OF that]] by (rule min.absorb1)
  have cr': "cuts = (\<lambda>b. if b \<in> path P a0 \<and> acc b then ap - min ap (cap b - bal b) else 0)"
            "bal' = (\<lambda>b. bal b + (if b \<in> path P a0 \<and> acc b then min ap (cap b - bal b) else 0))"
    using cr ap by (auto simp: credit_def Let_def)
  have cut0: "\<forall>b. cuts b = 0" using cr'(1) take by auto
  have bal': "bal' z = bal z + (if z \<in> path P a0 \<and> acc z then ap else 0)" for z
    using cr'(2) take by auto
  have le': "\<forall>z. bal' z \<le> cap z"
  proof
    fix z
    show "bal' z \<le> cap z"
    proof (cases "z \<in> path P a0 \<and> acc z")
      case True
      then show ?thesis using bal'[of z] room_ge[of z] ap_le by auto
    next
      case False
      then show ?thesis using bal'[of z] le by auto
    qed
  qed
  have inv': "\<forall>b\<in>A. (\<Sum>a\<in>{a\<in>A. (\<forall>e\<in>A. a \<in> path P e \<longrightarrow> e = a) \<and> b \<in> path P a}. cap a - bal' a) \<le> cap b - bal' b"
  proof
    fix b
    assume b: "b \<in> A"
    let ?S = "{a\<in>A. (\<forall>e\<in>A. a \<in> path P e \<longrightarrow> e = a) \<and> b \<in> path P a}"
    have fin: "finite ?S" by (rule finite_subset[of _ A]) (use tr in \<open>auto simp: tree_def\<close>)
    have pt: "cap a - bal' a = (cap a - bal a) - (if a = a0 then ap else 0)" if "a \<in> ?S" for a
    proof -
      have "(a \<in> path P a0 \<and> acc a) \<longleftrightarrow> a = a0" using that a0 acc by auto
      then show ?thesis using bal'[of a] by auto
    qed
    have s1: "(\<Sum>a\<in>?S. cap a - bal' a) = (\<Sum>a\<in>?S. (cap a - bal a) - (if a = a0 then ap else 0))"
      by (rule sum.cong[OF refl]) (erule pt)
    have s2: "(\<Sum>a\<in>?S. (cap a - bal a) - (if a = a0 then ap else 0)) = (\<Sum>a\<in>?S. cap a - bal a) - (if a0 \<in> ?S then ap else 0)"
      using fin by (simp add: sum_subtractf sum.delta)
    have mem: "a0 \<in> ?S \<longleftrightarrow> b \<in> path P a0" using a0 leaf by auto
    have rb: "cap b - bal' b = (cap b - bal b) - (if b \<in> path P a0 \<and> acc b then ap else 0)"
      using bal'[of b] by simp
    have "(\<Sum>a\<in>?S. cap a - bal a) \<le> cap b - bal b" using inv b by blast
    then show "(\<Sum>a\<in>?S. cap a - bal' a) \<le> cap b - bal' b"
      using s1 s2 mem rb ap0 by (auto split: if_splits)
  qed
  show ?thesis using cut0 le' inv' by blast
qed

lemma lu3_run:
  assumes tr: "tree A (parent_of B)"
    and qs: "\<forall>q\<in>set qs. case q of Draw d x \<Rightarrow> d \<in> A
                          | Restore a c x \<Rightarrow> a \<in> A \<and> (\<forall>e\<in>A. a \<in> path (parent_of B) e \<longrightarrow> e = a)"
    and le: "\<forall>z. bal z \<le> ceiling B z"
    and inv: "\<forall>b\<in>A. (\<Sum>a\<in>{a\<in>A. (\<forall>e\<in>A. a \<in> path (parent_of B) e \<longrightarrow> e = a) \<and> b \<in> path (parent_of B) a}.
                      ceiling B a - bal a) \<le> ceiling B b - bal b"
  shows "\<forall>p\<in>set (fst (run B qs bal)). case p of Drawn d x \<Rightarrow> True | Restored a c x applied cuts \<Rightarrow> (\<forall>b. cuts b = 0)"
  using qs le inv
proof (induction qs arbitrary: bal)
  case Nil
  then show ?case by simp
next
  case (Cons q qs)
  have rest: "\<forall>q\<in>set qs. case q of Draw d x \<Rightarrow> d \<in> A
                          | Restore a c x \<Rightarrow> a \<in> A \<and> (\<forall>e\<in>A. a \<in> path (parent_of B) e \<longrightarrow> e = a)"
    using Cons.prems(1) by simp
  obtain p bal1 where st: "post B q bal = (p, bal1)" by (cases "post B q bal")
  have fst_run: "fst (run B (q # qs) bal) = (case p of None \<Rightarrow> fst (run B qs bal1) | Some e \<Rightarrow> e # fst (run B qs bal1))"
    using st by (simp add: prod.case_eq_if)
  have step: "(case p of None \<Rightarrow> True | Some e \<Rightarrow> (case e of Drawn d x \<Rightarrow> True | Restored a c x ap cuts \<Rightarrow> (\<forall>b. cuts b = 0)))
              \<and> (\<forall>z. bal1 z \<le> ceiling B z)
              \<and> (\<forall>b\<in>A. (\<Sum>a\<in>{a\<in>A. (\<forall>e\<in>A. a \<in> path (parent_of B) e \<longrightarrow> e = a) \<and> b \<in> path (parent_of B) a}.
                      ceiling B a - bal1 a) \<le> ceiling B b - bal1 b)"
  proof (cases q)
    case (Draw d x)
    have d: "d \<in> A" using Cons.prems(1) Draw by simp
    show ?thesis
    proof (cases "0 \<le> x \<and> (\<forall>b\<in>path (parent_of B) d. x \<le> bal b)")
      case True
      have pb: "p = Some (Drawn d x)" "bal1 = debit (path (parent_of B) d) x bal"
        using st Draw True by (simp_all add: post_def draw_on_def)
      have "\<forall>z. debit (path (parent_of B) d) x bal z \<le> ceiling B z"
      proof
        fix z
        have "bal z \<le> ceiling B z" using Cons.prems(2) by blast
        then show "debit (path (parent_of B) d) x bal z \<le> ceiling B z" using True by (auto simp: debit_def)
      qed
      then show ?thesis using pb lu3_draw_step[OF tr d conjunct1[OF True] Cons.prems(3)] by simp
    next
      case False
      have "p = None" "bal1 = bal" using st Draw by (simp_all add: post_def draw_on_def False)
      then show ?thesis using Cons.prems(2,3) by simp
    qed
  next
    case (Restore a c x)
    show ?thesis
    proof (cases "restores B a c")
      case True
      obtain ap cuts bal' where cr: "credit (parent_of B) (ceiling B) (\<lambda>b. restores B b c) a x bal = (ap, cuts, bal')"
        by (cases "credit (parent_of B) (ceiling B) (\<lambda>b. restores B b c) a x bal") auto
      have pb: "p = Some (Restored a c x ap cuts)" "bal1 = bal'" using st Restore True cr by (simp_all add: post_def)
      have a: "a \<in> A" "\<forall>e\<in>A. a \<in> path (parent_of B) e \<longrightarrow> e = a" using Cons.prems(1) Restore by simp_all
      have "(\<lambda>b. restores B b c) a" using True by simp
      note one = lu3_credit_step[OF tr a(1) a(2) this Cons.prems(2) Cons.prems(3) cr]
      then show ?thesis using pb by simp
    next
      case False
      then have "p = None" "bal1 = bal" using st Restore by (simp_all add: post_def)
      then show ?thesis using Cons.prems(2,3) by simp
    qed
  qed
  have IH: "\<forall>p\<in>set (fst (run B qs bal1)). case p of Drawn d x \<Rightarrow> True | Restored a c x applied cuts \<Rightarrow> (\<forall>b. cuts b = 0)"
    using Cons.IH[OF rest] step by blast
  show ?case using fst_run step IH by (cases p) auto
qed

text \<open>The plan's law for what a run posts. Every request's account is in the tree, and every
  credit is requested at a leaf, an account no other account of the tree lies below.\<close>

(* GATE:BEGIN LU3 *)
theorem no_cut_where_ceilings_are_stated_and_credits_on_leaves:
  assumes tr: "tree A (parent_of B)" and cap: "ceiling B = stated B"
    and qs: "\<forall>q\<in>set qs. case q of Draw d x \<Rightarrow> d \<in> A
                          | Restore a c x \<Rightarrow> a \<in> A \<and> (\<forall>e\<in>A. a \<in> path (parent_of B) e \<longrightarrow> e = a)"
  shows "\<forall>p\<in>set (fst (run B qs (stated B))). case p of Drawn d x \<Rightarrow> True | Restored a c x applied cuts \<Rightarrow> (\<forall>b. cuts b = 0)"
  by (rule lu3_run[OF tr qs]) (simp_all add: cap)
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

text \<open>Why `post` refuses a credit at an account that does not accept its kind (LG-Q29 (b)).
  Account 1, a leaf of 10 that does not accept the kind, under account 0 of 10 that does, holds 5
  and its parent 10, as after a draw of 5 and a first credit of 5. `credit` alone, which stays
  total, applies a second credit of 5 in full at the leaf and cuts it by 5 at the parent. `run`
  posts the draw and refuses both credits.\<close>

(* GATE:BEGIN LU3n *)
theorem a_leaf_that_refuses_its_credit_leaves_a_cut:
  "(case credit (map_of [(1::nat, 0::nat)]) (\<lambda>_. 10 :: int) (\<lambda>b. b = 0) 1 5 (\<lambda>a. if a = 0 then 10 else 5) of
      (applied, cuts, bal) \<Rightarrow> (applied, cuts 0, bal 0, bal 1)) = (5, 5, 10, 5)
   \<and> map (\<lambda>p. case p of Drawn a x \<Rightarrow> (a, x) | Restored a c x applied cuts \<Rightarrow> (a, - x))
       (fst (run \<lparr>parent_of = map_of [(1::nat, 0::nat)], stated = (\<lambda>_. 10), ceiling = (\<lambda>_. 10),
                  restores = (\<lambda>b (_ :: unit option). b = 0), refusing = (\<lambda>_. False)\<rparr>
             [Draw 1 5, Restore 1 None 5, Restore 1 None 5] (\<lambda>_. 10 :: int))) = [(1, 5)]"
  by code_simp
(* GATE:END *)

end
