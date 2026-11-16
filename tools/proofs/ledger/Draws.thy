(* SPDX-License-Identifier: MPL-2.0 *)

(* The account tree and its draws on the target kernel (plan ledger, LG-9, restating LG-7's and
   LG-8's claims): the path as a list, so what reads a path evaluates, a draw succeeds whole or
   changes nothing, availability is the least along the path, a credit never lifts a balance above
   its ceiling, a purpose debits a second path in the same operation, a settlement is the same in
   every order of proposal, and an amount allocated across accounts in turn is conserved with its
   residual and charges each account what was granted at it. Hand-written on the Kernel extracted
   from ontology/ledger/README.md section 10. *)

theory Draws
imports Allocation "HOL-Library.Multiset"
begin

section \<open>The path as a list (R1, was LX1)\<close>

lemma path_self [simp]: "a \<in> path parent a"
  by (simp add: path_def)

text \<open>The path unfolded one step. It is the code equation for a path, so what reads a path
  evaluates, and the walk it gives stops where the parent function has no cycle, which a tree's
  has not. That the walk is the path is LX1 below.\<close>

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

lemma path_in_tree:
  assumes tr: "tree A parent" and a: "a \<in> A"
  shows "path parent a \<subseteq> A"
proof
  fix b
  assume "b \<in> path parent a"
  then have "(a, b) \<in> (up parent)\<^sup>*" by (simp add: path_def)
  then show "b \<in> A"
  proof (induction rule: rtrancl_induct)
    case base
    then show ?case using a .
  next
    case (step c d)
    then show ?case using tr by (auto simp: tree_def up_def)
  qed
qed

lemma finite_path: "tree A parent \<Longrightarrow> a \<in> A \<Longrightarrow> finite (path parent a)"
  by (meson finite_subset path_in_tree tree_def)

lemma tree_no_return:
  assumes tr: "tree A parent" and pb: "parent a = Some b"
  shows "a \<notin> path parent b"
proof
  assume "a \<in> path parent b"
  then have ba: "(b, a) \<in> (up parent)\<^sup>*" by (simp add: path_def)
  have ab: "(a, b) \<in> up parent" using pb by (simp add: up_def)
  have "(a, a) \<in> (up parent)\<^sup>+" using ab ba by (rule rtrancl_into_trancl2)
  then show False using tr by (simp add: tree_def acyclic_def)
qed

lemma chain_lists_path:
  assumes tr: "tree A parent"
  shows "a \<in> A \<Longrightarrow> card (path parent a) \<le> Suc n \<Longrightarrow>
           set (chain n parent a) = path parent a \<and> distinct (chain n parent a)"
proof (induction n arbitrary: a)
  case 0
  have fin: "finite (path parent a)" using finite_path[OF tr 0(1)] .
  have "\<forall>x\<in>path parent a. \<forall>y\<in>path parent a. x = y" using 0(2) card_le_Suc0_iff_eq[OF fin] by simp
  then have "path parent a = {a}" using path_self[of a parent] by blast
  then show ?case by simp
next
  case (Suc n)
  show ?case
  proof (cases "parent a")
    case None
    then have "path parent a = {a}" using path_step[of parent a] by simp
    then show ?thesis using None by simp
  next
    case (Some b)
    have bA: "b \<in> A" using tr Suc.prems(1) Some by (auto simp: tree_def)
    have pa: "path parent a = insert a (path parent b)" using path_step[of parent a] Some by simp
    have nb: "a \<notin> path parent b" by (rule tree_no_return[OF tr Some])
    have "card (path parent a) = Suc (card (path parent b))"
      using pa nb finite_path[OF tr bA] by simp
    then have "card (path parent b) \<le> Suc n" using Suc.prems(2) by simp
    then have IH: "set (chain n parent b) = path parent b \<and> distinct (chain n parent b)"
      using Suc.IH[OF bA] by blast
    show ?thesis using IH pa nb Some by simp
  qed
qed

(* GATE:BEGIN LX1 *)
theorem chain_is_the_path:
  assumes tr: "tree A parent" and a: "a \<in> A"
  shows "set (chain (card A) parent a) = path parent a \<and> distinct (chain (card A) parent a)"
proof -
  have "card (path parent a) \<le> card A"
    using tr path_in_tree[OF tr a] by (simp add: tree_def card_mono)
  then show ?thesis using chain_lists_path[OF tr a] by simp
qed
(* GATE:END *)


section \<open>The least balance over a set of accounts, and availability\<close>

lemma least_le: "finite S \<Longrightarrow> b \<in> S \<Longrightarrow> least bal S \<le> bal b"
  by (simp add: least_def)

lemma least_attained: "finite S \<Longrightarrow> S \<noteq> {} \<Longrightarrow> \<exists>b\<in>S. least bal S = bal b"
proof -
  assume "finite S" "S \<noteq> {}"
  then have "Min (bal ` S) \<in> bal ` S" by simp
  then show ?thesis unfolding least_def by auto
qed

lemma le_least_iff: "finite S \<Longrightarrow> S \<noteq> {} \<Longrightarrow> x \<le> least bal S \<longleftrightarrow> (\<forall>b\<in>S. x \<le> bal b)"
  by (simp add: least_def)

lemma least_nonneg:
  "finite S \<Longrightarrow> S \<noteq> {} \<Longrightarrow> S \<subseteq> A \<Longrightarrow> \<forall>b\<in>A. 0 \<le> bal b \<Longrightarrow> 0 \<le> least bal S"
  by (auto simp: le_least_iff)

corollary available_by_chain:
  assumes "tree A parent" "a \<in> A"
  shows "available parent bal a = least bal (set (chain (card A) parent a))"
  using chain_is_the_path[OF assms] by (simp add: available_def)

lemma available_le:
  assumes "tree A parent" "a \<in> A" "b \<in> path parent a"
  shows "available parent bal a \<le> bal b"
  using finite_path[OF assms(1,2)] assms(3) by (simp add: available_def least_le)

lemma path_nonempty [simp]: "path parent a \<noteq> {}"
  using path_self[of a parent] by blast

lemma available_attained:
  assumes "tree A parent" "a \<in> A"
  shows "\<exists>b\<in>path parent a. available parent bal a = bal b"
  unfolding available_def by (rule least_attained[OF finite_path[OF assms] path_nonempty])

lemma le_available_iff:
  assumes "tree A parent" "a \<in> A"
  shows "x \<le> available parent bal a \<longleftrightarrow> (\<forall>b\<in>path parent a. x \<le> bal b)"
  unfolding available_def by (rule le_least_iff[OF finite_path[OF assms] path_nonempty])

text \<open>Under a tree every account's path is a finite set of accounts that holds the account, which
  is what an allocation across accounts needs of the accounts it charges.\<close>

lemma path_charged:
  assumes tr: "tree A parent" and sub: "set as \<subseteq> A"
  shows "\<forall>a\<in>set as. finite (path parent a) \<and> path parent a \<noteq> {} \<and> path parent a \<subseteq> A"
proof
  fix a
  assume "a \<in> set as"
  then have a: "a \<in> A" using sub by blast
  show "finite (path parent a) \<and> path parent a \<noteq> {} \<and> path parent a \<subseteq> A"
    using finite_path[OF tr a] path_in_tree[OF tr a] by simp
qed


section \<open>Examples, evaluated through the path\<close>

text \<open>Account 2 sits under account 1, with 6 left at 2 and 10 at 1. Two proposals at one position
  ask 6 and 3 of account 2. What is available there is 6, the proportional rule grants 4 and 2, and
  the path falls by 6, to 4 at account 1 and 0 at account 2.\<close>

value "(case settle shared (\<lambda>_. 0) (map_of [(2::nat, 1::nat)]) 2 [(1::nat, 6::rat), (2, 3)]
               (\<lambda>a. if a = 1 then 10 else 6) of
          (out, bal) \<Rightarrow> (grants [1, 2] out, map bal [1, 2]))"

lemma example_settle:
  "(case settle shared (\<lambda>_. 0) (map_of [(2::nat, 1::nat)]) 2 [(1::nat, 6::rat), (2, 3)]
          (\<lambda>a. if a = 1 then 10 else 6) of
     (out, bal) \<Rightarrow> (grants [1, 2] out, map bal [1, 2])) = (([4, 2], 0), [4, 0])"
  by code_simp

text \<open>The same requests, 6 and 3, allocated across account 2 and then account 1, each charging
  its path. Account 2 grants 4 and 2 of what its path holds, 6, and account 1 the remaining 2 and 1
  of the 4 left on it, so nothing is left over and account 1 ends at 1.\<close>

value "(case spread {1::nat, 2} (proportional {1, 2}) (path (map_of [(2::nat, 1::nat)])) [2, 1]
               (\<lambda>a. if a = 1 then 10 else 6) (\<lambda>k. if k = 1 then 6 else (3::rat)) of
          (ps, r, bal) \<Rightarrow> (map (\<lambda>p. map p [1, 2]) ps, map r [1, 2], map bal [1, 2]))"

lemma example_spread:
  "(case spread {1::nat, 2} (proportional {1, 2}) (path (map_of [(2::nat, 1::nat)])) [2, 1]
          (\<lambda>a. if a = 1 then 10 else 6) (\<lambda>k. if k = 1 then 6 else (3::rat)) of
     (ps, r, bal) \<Rightarrow> (map (\<lambda>p. map p [1, 2]) ps, map r [1, 2], map bal [1, 2]))
   = ([[4, 2], [2, 1]], [0, 0], [1, 0])"
  by code_simp

text \<open>Two pots, accounts 2 and 3 under a fund, account 1, which holds 10, each pot holding 6. The
  first pot's proposals of 6 and 3 are granted 4 and 2, which leaves the fund 4, so the second pot's
  proposal of 5 is granted 4.\<close>

value "(case pots shared (\<lambda>_. 0) (map_of [(2::nat, 1::nat), (3, 1)]) 1
               [(2, [(1::nat, 6::rat), (2, 3)]), (3, [(3, 5)])] 0 (\<lambda>a. if a = 1 then 10 else 6) of
          None \<Rightarrow> None
        | Some (gs, h, bal) \<Rightarrow> Some (map (\<lambda>g. map g [1, 2, 3]) gs, h, map bal [1, 2, 3]))"

lemma example_pots:
  "(case pots shared (\<lambda>_. 0) (map_of [(2::nat, 1::nat), (3, 1)]) 1
          [(2, [(1::nat, 6::rat), (2, 3)]), (3, [(3, 5)])] 0 (\<lambda>a. if a = 1 then 10 else 6) of
     None \<Rightarrow> None
   | Some (gs, h, bal) \<Rightarrow> Some (map (\<lambda>g. map g [1, 2, 3]) gs, h, map bal [1, 2, 3]))
   = Some ([[4, 2, 0], [0, 0, 4]], 0, [0, 0, 2])"
  by code_simp

text \<open>A credit of 5 posted to account 2, which holds 2 under a ceiling of 6, below account 1, which
  holds 7 under a ceiling of 10. Account 2 takes 4, account 1 takes 3 of those 4, so the cut at
  account 1 is 1 and both end at their ceilings.\<close>

value "(case credit (map_of [(2::nat, 1::nat)]) (\<lambda>a. if a = 1 then 10 else 6) (\<lambda>_. True) 2 (5::int)
               (\<lambda>a. if a = 1 then 7 else 2) of
          (applied, cuts, bal) \<Rightarrow> (applied, map cuts [1, 2], map bal [1, 2]))"

lemma example_credit:
  "(case credit (map_of [(2::nat, 1::nat)]) (\<lambda>a. if a = 1 then 10 else 6) (\<lambda>_. True) 2 (5::int)
          (\<lambda>a. if a = 1 then 7 else 2) of
     (applied, cuts, bal) \<Rightarrow> (applied, map cuts [1, 2], map bal [1, 2])) = (4, [1, 0], [10, 6])"
  by code_simp


section \<open>A draw, a credit and a purpose\<close>

(* GATE:BEGIN LD1 *)
theorem draw_succeeds_whole_or_changes_nothing:
  shows "draw parent counts a None x bal = (bal', True) \<Longrightarrow>
           0 \<le> x \<and> (\<forall>b. bal' b = (if b \<in> path parent a then bal b - x else bal b))"
    and "draw parent counts a None x bal = (bal', False) \<Longrightarrow> bal' = bal"
  by (auto simp: draw_def draw_on_def reach_def debit_def split: if_splits)
(* GATE:END *)

(* GATE:BEGIN LD2 *)
theorem availability_is_the_least_along_the_path:
  assumes "tree A parent" "a \<in> A"
  shows "(\<forall>b\<in>path parent a. available parent bal a \<le> bal b)
         \<and> (\<exists>b\<in>path parent a. available parent bal a = bal b)"
    and "snd (draw parent counts a None x bal) \<longleftrightarrow> 0 \<le> x \<and> x \<le> available parent bal a"
proof -
  show "(\<forall>b\<in>path parent a. available parent bal a \<le> bal b)
         \<and> (\<exists>b\<in>path parent a. available parent bal a = bal b)"
    using available_le[OF assms] available_attained[OF assms] by blast
  show "snd (draw parent counts a None x bal) \<longleftrightarrow> 0 \<le> x \<and> x \<le> available parent bal a"
    by (auto simp: draw_def draw_on_def reach_def le_available_iff[OF assms])
qed
(* GATE:END *)

text \<open>A credit takes each account it reaches no further than its ceiling. With every account
  accepting it, a credit of what a draw took undoes the draw.\<close>

(* GATE:BEGIN LD3 *)
theorem credit_stops_at_the_ceiling:
  assumes cap: "\<forall>b. bal b \<le> cap b"
  shows "\<forall>b. snd (snd (credit parent cap accepts a x bal)) b \<le> cap b"
    and "draw parent counts a None x bal = (bal', True) \<Longrightarrow>
           snd (snd (credit parent cap (\<lambda>_. True) a x bal')) = bal"
proof -
  show "\<forall>b. snd (snd (credit parent cap accepts a x bal)) b \<le> cap b"
  proof
    fix b
    have m: "min (max 0 (min x (cap a - bal a))) (cap b - bal b) \<le> cap b - bal b" by (rule min.cobounded2)
    have "bal b + (if b \<in> path parent a \<and> accepts b then min (max 0 (min x (cap a - bal a))) (cap b - bal b) else 0)
            \<le> cap b"
      using cap m by (cases "b \<in> path parent a \<and> accepts b") auto
    then show "snd (snd (credit parent cap accepts a x bal)) b \<le> cap b"
      by (simp add: credit_def Let_def)
  qed
next
  assume d: "draw parent counts a None x bal = (bal', True)"
  have x0: "0 \<le> x" and after: "\<forall>b. bal' b = (if b \<in> path parent a then bal b - x else bal b)"
    using draw_succeeds_whole_or_changes_nothing(1)[OF d] by blast+
  have applied: "max 0 (min x (cap a - (bal a - x))) = x"
    using x0 cap[rule_format, of a] by (simp add: min_def max_def)
  show "snd (snd (credit parent cap (\<lambda>_. True) a x bal')) = bal"
  proof
    fix b
    show "snd (snd (credit parent cap (\<lambda>_. True) a x bal')) b = bal b"
    proof (cases "b \<in> path parent a")
      case True
      have "min x (cap b - bal' b) = x" using True after cap[rule_format, of b] by (simp add: min_def)
      then show ?thesis using True after by (simp add: credit_def Let_def applied)
    next
      case False
      then show ?thesis using after by (simp add: credit_def Let_def)
    qed
  qed
qed
(* GATE:END *)

(* GATE:BEGIN LD4 *)
theorem a_purpose_debits_the_counting_path_in_the_same_draw:
  assumes "c \<in> counts p" "b \<in> path parent c"
  shows "draw parent counts a (Some p) x bal = (bal', True) \<Longrightarrow> bal' b = bal b - x"
    and "draw parent counts a (Some p) x bal = (bal', True) \<Longrightarrow> (\<forall>d\<in>path parent a. bal' d = bal d - x)"
    and "draw parent counts a (Some p) x bal = (bal', False) \<Longrightarrow> bal' = bal"
    and "snd (draw parent counts a (Some p) x bal)
           \<longleftrightarrow> 0 \<le> x \<and> (\<forall>d\<in>reach parent counts a (Some p). x \<le> bal d)"
  using assms by (auto simp: draw_def draw_on_def reach_def debit_def split: if_splits)
(* GATE:END *)


section \<open>A settlement at one position\<close>

lemma proposers_reordered: "set ps = set ps' \<Longrightarrow> proposers ps = proposers ps'"
  by (simp add: proposers_def)

lemma requested_mset: "mset ps = mset ps' \<Longrightarrow> requested ps = requested ps'"
proof -
  assume eq: "mset ps = mset ps'"
  show "requested ps = requested ps'"
  proof
    fix k
    have "mset (map snd (filter (\<lambda>q. fst q = k) ps)) = mset (map snd (filter (\<lambda>q. fst q = k) ps'))"
      using eq by simp
    then have "sum_list (map snd (filter (\<lambda>q. fst q = k) ps))
               = sum_list (map snd (filter (\<lambda>q. fst q = k) ps'))"
      by (metis sum_mset_sum_list)
    then show "requested ps k = requested ps' k" by (simp add: requested_def)
  qed
qed

(* GATE:BEGIN LO1 *)
theorem settled_the_same_in_every_order_of_proposal:
  assumes "mset ps = mset ps'"
  shows "settle pol rank parent a ps bal = settle pol rank parent a ps' bal"
proof -
  have r: "requested ps = requested ps'" by (rule requested_mset[OF assms])
  have p: "proposers ps = proposers ps'" by (rule proposers_reordered[OF mset_eq_setD[OF assms]])
  show ?thesis unfolding settle_def merge_def r p ..
qed
(* GATE:END *)

lemma requested_nonneg:
  "\<forall>q\<in>set ps. 0 \<le> snd q \<Longrightarrow> nonneg_on (proposers ps) (requested ps)"
  unfolding nonneg_on_def requested_def proposers_def
  by (auto intro!: sum_list_nonneg) (metis (mono_tags, lifting) filter_False image_eqI list.map(1) sum_list.Nil)


section \<open>One amount allocated across accounts in turn\<close>

lemma total_sum_list:
  "(\<Sum>k\<in>K. sum_list (map (\<lambda>q. q k) ps)) = sum_list (map (total K) ps)"
  by (induct ps) (simp_all add: total_def sum.distrib)

text \<open>Whatever the rule, the parts and what is left are what was asked, key by key, and each
  account falls by the total of the parts granted at the accounts that charge it.\<close>

lemma spread_sums:
  "spread K R charged as bal v = (ps, r, bal') \<Longrightarrow>
     length ps = length as
     \<and> (\<forall>k. sum_list (map (\<lambda>q. q k) ps) + r k = v k)
     \<and> (\<forall>b. bal b - bal' b = sum_list (map (\<lambda>(c, q). if b \<in> charged c then total K q else 0) (zip as ps)))"
proof (induction as arbitrary: bal v ps r bal')
  case Nil
  then show ?case by auto
next
  case (Cons a rest)
  define p where "p = R v (min (total K v) (max 0 (least bal (charged a))))"
  define bal1 where "bal1 = debit (charged a) (total K p) bal"
  obtain ps1 r1 bal2 where rec: "spread K R charged rest bal1 (less v p) = (ps1, r1, bal2)"
    by (metis prod_cases3)
  have out: "ps = p # ps1" "r = r1" "bal' = bal2"
    using Cons.prems rec by (simp_all add: p_def bal1_def Let_def)
  have IH: "length ps1 = length rest
     \<and> (\<forall>k. sum_list (map (\<lambda>q. q k) ps1) + r1 k = less v p k)
     \<and> (\<forall>b. bal1 b - bal2 b = sum_list (map (\<lambda>(c, q). if b \<in> charged c then total K q else 0) (zip rest ps1)))"
    by (rule Cons.IH[OF rec])
  have pointwise: "\<forall>k. sum_list (map (\<lambda>q. q k) ps) + r k = v k"
  proof
    fix k
    have "sum_list (map (\<lambda>q. q k) ps1) + r1 k = v k - p k" using IH by (simp add: less_def)
    then show "sum_list (map (\<lambda>q. q k) ps) + r k = v k" by (simp add: out algebra_simps)
  qed
  have balances: "\<forall>b. bal b - bal' b
                  = sum_list (map (\<lambda>(c, q). if b \<in> charged c then total K q else 0) (zip (a # rest) ps))"
  proof
    fix b
    have later: "bal1 b - bal2 b
                  = sum_list (map (\<lambda>(c, q). if b \<in> charged c then total K q else 0) (zip rest ps1))"
      using IH by blast
    have now: "bal b - bal1 b = (if b \<in> charged a then total K p else 0)"
      by (simp add: bal1_def debit_def)
    show "bal b - bal' b
            = sum_list (map (\<lambda>(c, q). if b \<in> charged c then total K q else 0) (zip (a # rest) ps))"
      using later now by (simp add: out algebra_simps)
  qed
  show ?case using IH pointwise balances by (simp add: out)
qed

(* GATE:BEGIN LC1 *)
theorem conservation_with_residual:
  assumes "spread K R charged as bal v = (ps, r, bal')"
  shows "sum_list (map (\<lambda>q. q k) ps) + r k = v k"
  using spread_sums[OF assms] by blast
(* GATE:END *)

(* GATE:BEGIN LC2 *)
theorem conservation_in_total:
  assumes "spread K R charged as bal v = (ps, r, bal')"
  shows "total K v = sum_list (map (total K) ps) + total K r"
    and "bal b - bal' b = sum_list (map (\<lambda>(c, q). if b \<in> charged c then total K q else 0) (zip as ps))"
proof -
  have pointwise: "\<forall>k. sum_list (map (\<lambda>q. q k) ps) + r k = v k"
    using spread_sums[OF assms] by blast
  have "total K v = (\<Sum>k\<in>K. sum_list (map (\<lambda>q. q k) ps) + r k)"
    using pointwise by (simp add: total_def)
  also have "\<dots> = sum_list (map (total K) ps) + total K r"
    using total_sum_list[where K = K and ps = ps] by (simp add: sum.distrib total_def)
  finally show "total K v = sum_list (map (total K) ps) + total K r" .
  show "bal b - bal' b = sum_list (map (\<lambda>(c, q). if b \<in> charged c then total K q else 0) (zip as ps))"
    using spread_sums[OF assms] by blast
qed
(* GATE:END *)

lemma spread_rations:
  assumes ok: "rations K R"
  shows "\<forall>a\<in>set as. finite (charged a) \<and> charged a \<noteq> {} \<and> charged a \<subseteq> A \<Longrightarrow>
           nonneg_on K v \<Longrightarrow> (\<forall>b\<in>A. 0 \<le> bal b) \<Longrightarrow> spread K R charged as bal v = (ps, r, bal') \<Longrightarrow>
           (\<forall>b\<in>A. 0 \<le> bal' b) \<and> nonneg_on K r \<and> list_all (nonneg_on K) ps"
proof (induction as arbitrary: bal v ps r bal')
  case Nil
  then show ?case by simp
next
  case (Cons a rest)
  have ch: "finite (charged a)" "charged a \<noteq> {}" "charged a \<subseteq> A" using Cons.prems(1) by simp_all
  define x where "x = min (total K v) (max 0 (least bal (charged a)))"
  define p where "p = R v x"
  define bal1 where "bal1 = debit (charged a) (total K p) bal"
  obtain ps1 r1 bal2 where rec: "spread K R charged rest bal1 (less v p) = (ps1, r1, bal2)"
    by (metis prod_cases3)
  have out: "ps = p # ps1" "r = r1" "bal' = bal2"
    using Cons.prems(4) rec by (simp_all add: x_def p_def bal1_def Let_def)
  have x0: "0 \<le> x" using total_nonneg[OF Cons.prems(2)] by (simp add: x_def)
  have xv: "x \<le> total K v" by (simp add: x_def)
  have l0: "0 \<le> least bal (charged a)" using least_nonneg[OF ch Cons.prems(3)] .
  have xl: "x \<le> least bal (charged a)" using l0 by (simp add: x_def)
  have pnn: "nonneg_on K p" and pfit: "fits_in p v" and ple: "total K p \<le> x"
    using rations_parts[OF ok Cons.prems(2) x0 xv] by (simp_all add: p_def)
  have bal1nn: "\<forall>b\<in>A. 0 \<le> bal1 b"
  proof
    fix b
    assume bA: "b \<in> A"
    show "0 \<le> bal1 b"
    proof (cases "b \<in> charged a")
      case True
      have "least bal (charged a) \<le> bal b" using least_le[OF ch(1) True] .
      then show ?thesis using True ple xl by (simp add: bal1_def debit_def)
    next
      case False
      then show ?thesis using Cons.prems(3) bA by (simp add: bal1_def debit_def)
    qed
  qed
  have v1nn: "nonneg_on K (less v p)" using Cons.prems(2) pnn pfit by (rule nonneg_less)
  have "\<forall>a\<in>set rest. finite (charged a) \<and> charged a \<noteq> {} \<and> charged a \<subseteq> A" using Cons.prems(1) by simp
  then have IH: "(\<forall>b\<in>A. 0 \<le> bal2 b) \<and> nonneg_on K r1 \<and> list_all (nonneg_on K) ps1"
    using Cons.IH[OF _ v1nn bal1nn rec] by blast
  show ?case using IH pnn by (simp add: out)
qed

text \<open>The part granted at step \<open>i\<close> is the rule applied to what is still asked after the first
  \<open>i\<close> accounts, at the least balance the first \<open>i\<close> accounts left on the accounts charged.\<close>

lemma spread_step:
  "i < length as \<Longrightarrow> spread K R charged as bal v = (ps, r, bal') \<Longrightarrow>
     spread K R charged (take i as) bal v = (qs, ri, bi) \<Longrightarrow>
     ps ! i = R ri (min (total K ri) (max 0 (least bi (charged (as ! i)))))"
proof (induction as arbitrary: i bal v ps r bal' qs ri bi)
  case Nil
  then show ?case by simp
next
  case (Cons a rest)
  define p where "p = R v (min (total K v) (max 0 (least bal (charged a))))"
  define bal1 where "bal1 = debit (charged a) (total K p) bal"
  obtain ps1 r1 bal2 where rec: "spread K R charged rest bal1 (less v p) = (ps1, r1, bal2)"
    by (metis prod_cases3)
  have out: "ps = p # ps1"
    using Cons.prems(2) rec by (simp add: p_def bal1_def Let_def)
  show ?case
  proof (cases i)
    case 0
    then have "ri = v" "bi = bal" using Cons.prems(3) by simp_all
    then show ?thesis using out 0 by (simp add: p_def)
  next
    case (Suc j)
    have j: "j < length rest" using Cons.prems(1) Suc by simp
    obtain qs1 rj bj where pre: "spread K R charged (take j rest) bal1 (less v p) = (qs1, rj, bj)"
      by (metis prod_cases3)
    have "spread K R charged (take i (a # rest)) bal v = (p # qs1, rj, bj)"
      using pre Suc by (simp add: p_def bal1_def Let_def)
    then have "ri = rj" "bi = bj" using Cons.prems(3) by simp_all
    moreover have "ps1 ! j = R rj (min (total K rj) (max 0 (least bj (charged (rest ! j)))))"
      by (rule Cons.IH[OF j rec pre])
    ultimately show ?thesis using out Suc by simp
  qed
qed

(* GATE:BEGIN LC3 *)
theorem nothing_posted_beyond_availability:
  assumes ok: "rations K R"
      and ch: "\<forall>a\<in>set as. finite (charged a) \<and> charged a \<noteq> {} \<and> charged a \<subseteq> A"
      and nn: "nonneg_on K v" and bal0: "\<forall>b\<in>A. 0 \<le> bal b"
      and sp: "spread K R charged as bal v = (ps, r, bal')"
  shows "(\<forall>b\<in>A. 0 \<le> bal' b) \<and> nonneg_on K r"
    and "i < length as \<Longrightarrow>
           total K (ps ! i) \<le> least (snd (snd (spread K R charged (take i as) bal v))) (charged (as ! i))"
proof -
  show "(\<forall>b\<in>A. 0 \<le> bal' b) \<and> nonneg_on K r"
    using spread_rations[OF ok ch nn bal0 sp] by blast
next
  assume i: "i < length as"
  obtain qs ri bi where pre: "spread K R charged (take i as) bal v = (qs, ri, bi)"
    by (metis prod_cases3)
  have chi: "\<forall>a\<in>set (take i as). finite (charged a) \<and> charged a \<noteq> {} \<and> charged a \<subseteq> A"
    using ch set_take_subset by fast
  have prefix: "(\<forall>b\<in>A. 0 \<le> bi b) \<and> nonneg_on K ri"
    using spread_rations[OF ok chi nn bal0 pre] by blast
  have ai: "as ! i \<in> set as" using i by simp
  have l0: "0 \<le> least bi (charged (as ! i))"
    using ch ai prefix by (intro least_nonneg[of _ A]) auto
  define x where "x = min (total K ri) (max 0 (least bi (charged (as ! i))))"
  have x0: "0 \<le> x" using total_nonneg[of K ri] prefix by (simp add: x_def)
  have xr: "x \<le> total K ri" by (simp add: x_def)
  have "ps ! i = R ri x" unfolding x_def by (rule spread_step[OF i sp pre])
  then have "total K (ps ! i) \<le> x" using rations_parts(3)[OF ok _ x0 xr] prefix by simp
  then show "total K (ps ! i) \<le> least (snd (snd (spread K R charged (take i as) bal v))) (charged (as ! i))"
    using l0 pre by (simp add: x_def)
qed
(* GATE:END *)

end
