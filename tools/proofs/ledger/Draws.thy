(* SPDX-License-Identifier: MPL-2.0 *)

(* The account tree and its draws: a draw succeeds whole or changes nothing, availability is the
   least along the path, a credit stops at the ceiling, a purpose debits a second path in the same
   operation, draws at one position settle the same in every order of proposal, and an amount
   drawn across several accounts in turn is conserved with its residual (plan ledger, LG-7).
   Hand-written on the Kernel extracted from ontology/ledger/README.md section 10. *)

theory Draws
imports Allocation
begin

section \<open>Paths and availability\<close>

lemma path_self [simp]: "a \<in> path parent a"
  by (simp add: path_def)

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

lemma available_le:
  assumes "tree A parent" "a \<in> A" "b \<in> path parent a"
  shows "available parent bal a \<le> bal b"
proof -
  have "finite (bal ` path parent a)" using finite_path[OF assms(1,2)] by simp
  moreover have "bal b \<in> bal ` path parent a" using assms(3) by simp
  ultimately show ?thesis unfolding available_def by (rule Min_le)
qed

lemma available_attained:
  assumes "tree A parent" "a \<in> A"
  shows "\<exists>b\<in>path parent a. available parent bal a = bal b"
proof -
  have "finite (bal ` path parent a)" using finite_path[OF assms] by simp
  moreover have "bal ` path parent a \<noteq> {}" using path_self[of a parent] by blast
  ultimately have "Min (bal ` path parent a) \<in> bal ` path parent a" by (rule Min_in)
  then show ?thesis unfolding available_def by auto
qed

lemma le_available_iff:
  assumes "tree A parent" "a \<in> A"
  shows "x \<le> available parent bal a \<longleftrightarrow> (\<forall>b\<in>path parent a. x \<le> bal b)"
proof
  assume "x \<le> available parent bal a"
  then show "\<forall>b\<in>path parent a. x \<le> bal b"
    using available_le[OF assms] order_trans by blast
next
  assume all: "\<forall>b\<in>path parent a. x \<le> bal b"
  obtain b where "b \<in> path parent a" "available parent bal a = bal b"
    using available_attained[OF assms] by blast
  then show "x \<le> available parent bal a" using all by simp
qed


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

(* GATE:BEGIN LD3 *)
theorem credit_stops_at_the_ceiling:
  assumes "\<forall>b. bal b \<le> cap b"
  shows "\<forall>b. credit parent cap a x bal b \<le> cap b"
    and "draw parent counts a None x bal = (bal', True) \<Longrightarrow> credit parent cap a x bal' = bal"
proof -
  show "\<forall>b. credit parent cap a x bal b \<le> cap b" using assms by (simp add: credit_def)
next
  assume d: "draw parent counts a None x bal = (bal', True)"
  have after: "\<forall>b. bal' b = (if b \<in> path parent a then bal b - x else bal b)"
    using draw_succeeds_whole_or_changes_nothing(1)[OF d] by blast
  show "credit parent cap a x bal' = bal"
  proof
    fix b
    show "credit parent cap a x bal' b = bal b"
      using after assms by (simp add: credit_def min_absorb2)
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


section \<open>Draws at one position\<close>

lemma sum_list_filter_distinct:
  "distinct ps \<Longrightarrow> sum_list (map snd (filter (\<lambda>q. fst q = k) ps)) = (\<Sum>q\<in>{q\<in>set ps. fst q = k}. snd q)"
  by (simp add: sum_list_distinct_conv_sum_set)

lemma requested_reordered:
  "distinct ps \<Longrightarrow> distinct ps' \<Longrightarrow> set ps = set ps' \<Longrightarrow> requested ps = requested ps'"
  by (simp add: requested_def fun_eq_iff sum_list_filter_distinct)

lemma proposers_reordered: "set ps = set ps' \<Longrightarrow> proposers ps = proposers ps'"
  by (simp add: proposers_def)

(* GATE:BEGIN LO1 *)
theorem settled_the_same_in_every_order_of_proposal:
  assumes "distinct ps" "distinct ps'" "set ps = set ps'"
  shows "settle_at rule parent a ps bal = settle_at rule parent a ps' bal"
  using requested_reordered[OF assms] proposers_reordered[OF assms(3)]
  by (simp add: settle_at_def merge_def)
(* GATE:END *)

lemma requested_nonneg:
  "\<forall>q\<in>set ps. 0 \<le> snd q \<Longrightarrow> nonneg_on (proposers ps) (requested ps)"
  unfolding nonneg_on_def requested_def proposers_def
  by (auto intro!: sum_list_nonneg) (metis (mono_tags, lifting) filter_False image_eqI list.map(1) sum_list.Nil)

lemma merge_bounded:
  assumes ok: "lawful (proposers ps) (rule (proposers ps))"
      and nn: "nonneg_on (proposers ps) (requested ps)" and av: "0 \<le> av"
  shows "total (proposers ps) (merge rule av ps) \<le> av
         \<and> fits_in (merge rule av ps) (requested ps)
         \<and> nonneg_on (proposers ps) (merge rule av ps)"
proof (cases "total (proposers ps) (requested ps) \<le> av")
  case True
  then show ?thesis using nn by (simp add: merge_def fits_in_def)
next
  case False
  then have "av \<le> total (proposers ps) (requested ps)" by simp
  then show ?thesis
    using False av lawful_exact[OF ok nn] lawful_fits_in[OF ok nn] lawful_nonneg[OF ok nn]
    by (simp add: merge_def)
qed


section \<open>An amount drawn across several accounts in turn\<close>

lemma total_sum_list:
  "finite K \<Longrightarrow> (\<Sum>k\<in>K. sum_list (map (\<lambda>q. q k) ps)) = sum_list (map (total K) ps)"
  by (induct ps) (simp_all add: total_def sum.distrib)

lemma spread_invariant:
  assumes fin: "finite K" and ok: "lawful K R"
  shows "nonneg_on K v \<Longrightarrow> spread K R parent accts bal v = (ps, r, bal') \<Longrightarrow>
           length ps = length accts
           \<and> (\<forall>k. sum_list (map (\<lambda>q. q k) ps) + r k = v k)
           \<and> nonneg_on K r \<and> fits_in r v \<and> list_all (nonneg_on K) ps
           \<and> (\<forall>b. bal b - bal' b
                  = sum_list (map (\<lambda>(c, q). if b \<in> path parent c then total K q else 0) (zip accts ps)))"
proof (induction accts arbitrary: bal v ps r bal')
  case Nil
  then show ?case by (auto simp: fits_in_def)
next
  case (Cons a rest)
  define x where "x = min (total K v) (max 0 (available parent bal a))"
  define p where "p = R v x"
  define bal1 where "bal1 = debit (path parent a) x bal"
  define v1 where "v1 = less v p"
  obtain ps1 r1 bal2 where rec: "spread K R parent rest bal1 v1 = (ps1, r1, bal2)"
    by (metis prod_cases3)
  have out: "ps = p # ps1" "r = r1" "bal' = bal2"
    using Cons.prems(2) rec by (simp_all add: x_def p_def bal1_def v1_def Let_def)
  have x0: "0 \<le> x" using total_nonneg[OF Cons.prems(1)] by (simp add: x_def)
  have xv: "x \<le> total K v" by (simp add: x_def)
  have pex: "total K p = x" unfolding p_def using lawful_exact[OF ok Cons.prems(1) x0 xv] .
  have pfit: "fits_in p v" unfolding p_def using lawful_fits_in[OF ok Cons.prems(1) x0 xv] .
  have pnn: "nonneg_on K p" unfolding p_def using lawful_nonneg[OF ok Cons.prems(1) x0 xv] .
  have v1nn: "nonneg_on K v1" unfolding v1_def using Cons.prems(1) pnn pfit by (rule nonneg_less)
  have IH: "length ps1 = length rest
           \<and> (\<forall>k. sum_list (map (\<lambda>q. q k) ps1) + r1 k = v1 k)
           \<and> nonneg_on K r1 \<and> fits_in r1 v1 \<and> list_all (nonneg_on K) ps1
           \<and> (\<forall>b. bal1 b - bal2 b
                  = sum_list (map (\<lambda>(c, q). if b \<in> path parent c then total K q else 0) (zip rest ps1)))"
    by (rule Cons.IH[OF v1nn rec])
  have len: "length ps = length (a # rest)" using IH by (simp add: out)
  have pointwise: "\<forall>k. sum_list (map (\<lambda>q. q k) ps) + r k = v k"
  proof
    fix k
    have "sum_list (map (\<lambda>q. q k) ps1) + r1 k = v1 k" using IH by blast
    then show "sum_list (map (\<lambda>q. q k) ps) + r k = v k"
      by (simp add: out v1_def less_def algebra_simps)
  qed
  have rnn: "nonneg_on K r" using IH by (simp add: out)
  have rfit: "fits_in r v"
    unfolding fits_in_def
  proof
    fix k
    have "r1 k \<le> v k - p k" using IH by (simp add: fits_in_def v1_def less_def)
    moreover have "0 \<le> p k" using pnn by (simp add: nonneg_on_def)
    ultimately show "r k \<le> v k" unfolding out(2) by linarith
  qed
  have psnn: "list_all (nonneg_on K) ps" using IH pnn by (simp add: out)
  have balances: "\<forall>b. bal b - bal' b
                  = sum_list (map (\<lambda>(c, q). if b \<in> path parent c then total K q else 0) (zip (a # rest) ps))"
  proof
    fix b
    have later: "bal1 b - bal2 b
                  = sum_list (map (\<lambda>(c, q). if b \<in> path parent c then total K q else 0) (zip rest ps1))"
      using IH by blast
    have now: "bal b - bal1 b = (if b \<in> path parent a then total K p else 0)"
      by (simp add: bal1_def debit_def pex)
    show "bal b - bal' b
            = sum_list (map (\<lambda>(c, q). if b \<in> path parent c then total K q else 0) (zip (a # rest) ps))"
      using later now by (simp add: out algebra_simps)
  qed
  show ?case using len pointwise rnn rfit psnn balances by blast
qed

(* GATE:BEGIN LC1 *)
theorem conservation_with_residual:
  assumes "finite K" "lawful K R" "nonneg_on K v"
      and "spread K R parent accts bal v = (ps, r, bal')"
  shows "sum_list (map (\<lambda>q. q k) ps) + r k = v k"
  using spread_invariant[OF assms(1,2) assms(3,4)] by blast
(* GATE:END *)

(* GATE:BEGIN LC2 *)
theorem conservation_in_total:
  assumes "finite K" "lawful K R" "nonneg_on K v"
      and "spread K R parent accts bal v = (ps, r, bal')"
  shows "total K v = sum_list (map (total K) ps) + total K r"
    and "bal b - bal' b
           = sum_list (map (\<lambda>(c, q). if b \<in> path parent c then total K q else 0) (zip accts ps))"
proof -
  have pointwise: "\<forall>k. sum_list (map (\<lambda>q. q k) ps) + r k = v k"
    using spread_invariant[OF assms(1,2) assms(3,4)] by blast
  have "total K v = (\<Sum>k\<in>K. sum_list (map (\<lambda>q. q k) ps) + r k)"
    using pointwise by (simp add: total_def)
  also have "\<dots> = sum_list (map (total K) ps) + total K r"
    using total_sum_list[OF assms(1), of ps] by (simp add: sum.distrib total_def)
  finally show "total K v = sum_list (map (total K) ps) + total K r" .
  show "bal b - bal' b
          = sum_list (map (\<lambda>(c, q). if b \<in> path parent c then total K q else 0) (zip accts ps))"
    using spread_invariant[OF assms(1,2) assms(3,4)] by blast
qed
(* GATE:END *)

lemma spread_keeps_balances:
  assumes fin: "finite K" and ok: "lawful K R" and tr: "tree A parent"
  shows "set accts \<subseteq> A \<Longrightarrow> nonneg_on K v \<Longrightarrow> (\<forall>b\<in>A. 0 \<le> bal b)
           \<Longrightarrow> spread K R parent accts bal v = (ps, r, bal') \<Longrightarrow> \<forall>b\<in>A. 0 \<le> bal' b"
proof (induction accts arbitrary: bal v ps r bal')
  case Nil
  then show ?case by simp
next
  case (Cons a rest)
  define x where "x = min (total K v) (max 0 (available parent bal a))"
  define p where "p = R v x"
  define bal1 where "bal1 = debit (path parent a) x bal"
  define v1 where "v1 = less v p"
  obtain ps1 r1 bal2 where rec: "spread K R parent rest bal1 v1 = (ps1, r1, bal2)"
    by (metis prod_cases3)
  have out: "bal' = bal2"
    using Cons.prems(4) rec by (simp add: x_def p_def bal1_def v1_def Let_def)
  have aA: "a \<in> A" using Cons.prems(1) by simp
  have x0: "0 \<le> x" using total_nonneg[OF Cons.prems(2)] by (simp add: x_def)
  have xv: "x \<le> total K v" by (simp add: x_def)
  have av0: "0 \<le> available parent bal a"
  proof -
    obtain b where "b \<in> path parent a" "available parent bal a = bal b"
      using available_attained[OF tr aA] by blast
    moreover have "b \<in> A" using path_in_tree[OF tr aA] \<open>b \<in> path parent a\<close> by blast
    ultimately show ?thesis using Cons.prems(3) by simp
  qed
  have xav: "x \<le> available parent bal a" using av0 by (simp add: x_def)
  have bal1nn: "\<forall>b\<in>A. 0 \<le> bal1 b"
  proof
    fix b
    assume bA: "b \<in> A"
    show "0 \<le> bal1 b"
    proof (cases "b \<in> path parent a")
      case True
      have "x \<le> bal b" using order_trans[OF xav available_le[OF tr aA True]] .
      then show ?thesis using True by (simp add: bal1_def debit_def)
    next
      case False
      then show ?thesis using Cons.prems(3) bA by (simp add: bal1_def debit_def)
    qed
  qed
  have pfit: "fits_in p v" unfolding p_def using lawful_fits_in[OF ok Cons.prems(2) x0 xv] .
  have pnn: "nonneg_on K p" unfolding p_def using lawful_nonneg[OF ok Cons.prems(2) x0 xv] .
  have v1nn: "nonneg_on K v1" unfolding v1_def using Cons.prems(2) pnn pfit by (rule nonneg_less)
  have "set rest \<subseteq> A" using Cons.prems(1) by simp
  then show ?case using Cons.IH[OF _ v1nn bal1nn rec] out by simp
qed

(* GATE:BEGIN LC3 *)
theorem nothing_posted_beyond_availability:
  assumes fin: "finite K" and ok: "lawful K R" and tr: "tree A parent"
      and sub: "set accts \<subseteq> A" and nn: "nonneg_on K v" and bal0: "\<forall>b\<in>A. 0 \<le> bal b"
      and sp: "spread K R parent accts bal v = (ps, r, bal')"
  shows "(\<forall>b\<in>A. 0 \<le> bal' b) \<and> nonneg_on K r"
    and "accts = a # rest \<Longrightarrow> total K (hd ps) \<le> available parent bal a"
proof -
  show "(\<forall>b\<in>A. 0 \<le> bal' b) \<and> nonneg_on K r"
    using spread_keeps_balances[OF fin ok tr sub nn bal0 sp] spread_invariant[OF fin ok nn sp]
    by blast
next
  assume ac: "accts = a # rest"
  define x where "x = min (total K v) (max 0 (available parent bal a))"
  have aA: "a \<in> A" using sub ac by simp
  have x0: "0 \<le> x" using total_nonneg[OF nn] by (simp add: x_def)
  have xv: "x \<le> total K v" by (simp add: x_def)
  obtain ps1 r1 bal2
    where rec: "spread K R parent rest (debit (path parent a) x bal) (less v (R v x)) = (ps1, r1, bal2)"
    by (metis prod_cases3)
  have hd: "hd ps = R v x"
    using sp ac rec by (auto simp: x_def Let_def)
  have av0: "0 \<le> available parent bal a"
  proof -
    obtain b where "b \<in> path parent a" "available parent bal a = bal b"
      using available_attained[OF tr aA] by blast
    moreover have "b \<in> A" using path_in_tree[OF tr aA] \<open>b \<in> path parent a\<close> by blast
    ultimately show ?thesis using bal0 by simp
  qed
  show "total K (hd ps) \<le> available parent bal a"
    using lawful_exact[OF ok nn x0 xv] av0 by (simp add: hd x_def)
qed
(* GATE:END *)


section \<open>Positions\<close>

lemma before_is_a_strict_total_order:
  "\<not> before p p"
  "before p q \<Longrightarrow> before q s \<Longrightarrow> before p s"
  "p \<noteq> q \<Longrightarrow> before p q \<or> before q p"
  by (auto simp: before_def prod_eq_iff)

end
