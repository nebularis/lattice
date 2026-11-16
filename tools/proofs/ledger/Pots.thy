(* SPDX-License-Identifier: MPL-2.0 *)

(* Allocation and pots on the target kernel (plan ledger, LG-20, the fifth group): an allocation
   over the reach of a purpose charges every account that counts it, an allocation that must be
   whole is whole or no result, with a rule that rations the parts and what is left are what was
   asked, and the fund and every account above it fall by the grants of its pots. Hand-written on
   the Kernel extracted from ontology/ledger/README.md section 10. *)

theory Pots
imports Merge
begin

section \<open>Examples, before any theorem\<close>

text \<open>Requests of 6 and 3 allocated across account 2 and then account 1 by the proportional rule,
  where 2 sits under 1. Whole, it is the allocation. Where account 1 holds only 1, a unit is left
  and the allocation that must be whole gives no result.\<close>

value "(case spread_whole {1::nat, 2} (proportional {1, 2}) (path (map_of [(2::nat, 1::nat)])) [2, 1]
               (\<lambda>a. if a = 1 then 10 else 6) (\<lambda>k. if k = 1 then 6 else (3::rat)) of None \<Rightarrow> False | Some _ \<Rightarrow> True,
        case spread_whole {1::nat, 2} (proportional {1, 2}) (path (map_of [(2::nat, 1::nat)])) [2, 1]
               (\<lambda>a. if a = 1 then 7 else 6) (\<lambda>k. if k = 1 then 6 else (3::rat)) of None \<Rightarrow> False | Some _ \<Rightarrow> True)"

lemma example_whole_or_nothing:
  "(case spread_whole {1::nat, 2} (proportional {1, 2}) (path (map_of [(2::nat, 1::nat)])) [2, 1]
          (\<lambda>a. if a = 1 then 10 else 6) (\<lambda>k. if k = 1 then 6 else (3::rat)) of None \<Rightarrow> False | Some _ \<Rightarrow> True)
   \<and> (case spread_whole {1::nat, 2} (proportional {1, 2}) (path (map_of [(2::nat, 1::nat)])) [2, 1]
          (\<lambda>a. if a = 1 then 7 else 6) (\<lambda>k. if k = 1 then 6 else (3::rat)) of None \<Rightarrow> True | Some _ \<Rightarrow> False)"
  by code_simp


section \<open>An allocation over the reach of a purpose\<close>

lemma sum_zip_all:
  "length ps = length as \<Longrightarrow> \<forall>c\<in>set as. P c \<Longrightarrow>
     sum_list (map (\<lambda>(c, q). if P c then f q else 0) (zip as ps)) = sum_list (map f ps)"
proof (induct as arbitrary: ps)
  case Nil
  then show ?case by simp
next
  case (Cons a as)
  then show ?case by (cases ps) simp_all
qed

(* GATE:BEGIN LC5 *)
theorem a_purpose_charges_every_account_counting_it:
  assumes sp: "spread K R (\<lambda>a. reach parent counts a (Some p)) as bal v = (ps, r, bal')"
      and c: "c \<in> counts p" and b: "b \<in> path parent c"
  shows "bal b - bal' b = sum_list (map (total K) ps)"
proof -
  have len: "length ps = length as" using spread_sums[OF sp] by blast
  have all: "\<forall>a\<in>set as. b \<in> reach parent counts a (Some p)" using c b by (auto simp: reach_def)
  have "bal b - bal' b = sum_list (map (\<lambda>(a, q). if b \<in> reach parent counts a (Some p) then total K q else 0) (zip as ps))"
    using conservation_in_total(2)[OF sp] .
  also have "\<dots> = sum_list (map (total K) ps)" by (rule sum_zip_all[OF len all])
  finally show ?thesis .
qed
(* GATE:END *)


section \<open>An allocation that must be whole\<close>

(* GATE:BEGIN LC6 *)
theorem whole_or_no_result:
  shows "spread_whole K R charged as bal v = Some (ps, bal') \<longleftrightarrow>
           (\<exists>r. spread K R charged as bal v = (ps, r, bal') \<and> total K r = 0)"
    and "spread_whole K R charged as bal v = None \<longleftrightarrow>
           total K (fst (snd (spread K R charged as bal v))) \<noteq> 0"
  by (auto simp: spread_whole_def split: prod.splits)
(* GATE:END *)


section \<open>With a rule that rations, the parts and what is left are what was asked\<close>

lemma spread_parts_nonneg:
  assumes ok: "rations K R"
  shows "nonneg_on K v \<Longrightarrow> spread K R charged as bal v = (ps, r, bal') \<Longrightarrow>
           nonneg_on K r \<and> list_all (nonneg_on K) ps"
proof (induction as arbitrary: bal v ps r bal')
  case Nil
  then show ?case by simp
next
  case (Cons a rest)
  define x where "x = min (total K v) (max 0 (least bal (charged a)))"
  define p where "p = R v x"
  obtain ps1 r1 bal2 where rec: "spread K R charged rest (debit (charged a) (total K p) bal) (less v p) = (ps1, r1, bal2)"
    by (metis prod_cases3)
  have out: "ps = p # ps1" "r = r1"
    using Cons.prems(2) rec by (simp_all add: x_def p_def Let_def)
  have x0: "0 \<le> x" using total_nonneg[OF Cons.prems(1)] by (simp add: x_def)
  have xv: "x \<le> total K v" by (simp add: x_def)
  have pnn: "nonneg_on K p" and pfit: "fits_in p v"
    using rations_parts[OF ok Cons.prems(1) x0 xv] by (simp_all add: p_def)
  have "nonneg_on K (less v p)" using Cons.prems(1) pnn pfit by (rule nonneg_less)
  then show ?case using Cons.IH[OF _ rec] pnn by (simp add: out)
qed

(* GATE:BEGIN LV3 *)
theorem rationing_allocation_accounts_for_what_was_asked:
  assumes ok: "rations K R" and nn: "nonneg_on K v"
      and sp: "spread K R charged as bal v = (ps, r, bal')"
  shows "\<forall>k. sum_list (map (\<lambda>q. q k) ps) + r k = v k"
    and "nonneg_on K r \<and> fits_in r v \<and> list_all (nonneg_on K) ps"
    and "\<forall>b. bal b - bal' b = sum_list (map (\<lambda>(c, q). if b \<in> charged c then total K q else 0) (zip as ps))"
proof -
  show sums: "\<forall>k. sum_list (map (\<lambda>q. q k) ps) + r k = v k" using spread_sums[OF sp] by blast
  have parts: "nonneg_on K r \<and> list_all (nonneg_on K) ps" by (rule spread_parts_nonneg[OF ok nn sp])
  have "r k \<le> v k" for k
  proof -
    have "0 \<le> sum_list (map (\<lambda>q. q k) ps)"
      using parts by (intro sum_list_nonneg) (auto simp: list_all_iff nonneg_on_def)
    then show ?thesis using sums[rule_format, of k] by linarith
  qed
  then show "nonneg_on K r \<and> fits_in r v \<and> list_all (nonneg_on K) ps" using parts by (simp add: fits_in_def)
  show "\<forall>b. bal b - bal' b = sum_list (map (\<lambda>(c, q). if b \<in> charged c then total K q else 0) (zip as ps))"
    using spread_sums[OF sp] by blast
qed
(* GATE:END *)


section \<open>The fund and every account above it fall by the grants of its pots\<close>

lemma path_trans: "c \<in> path parent a \<Longrightarrow> path parent c \<subseteq> path parent a"
  by (auto simp: path_def)

(* GATE:BEGIN LP3 *)
theorem the_fund_falls_by_the_grants:
  shows "pots pol rank parent fund qs held bal = Some (gs, h, bal') \<Longrightarrow>
           \<forall>(a, ps)\<in>set qs. fund \<in> path parent a \<Longrightarrow> b \<in> path parent fund \<Longrightarrow>
           bal b - bal' b = sum_list (map2 (\<lambda>(a, ps) g. total (proposers ps) g) qs gs)"
proof (induction qs arbitrary: held bal gs h bal')
  case Nil
  then show ?case by simp
next
  case (Cons q rest)
  obtain a ps where q: "q = (a, ps)" by (cases q)
  have fa: "fund \<in> path parent a" using Cons.prems(2) q by simp
  have ba: "b \<in> path parent a" using path_trans[OF fa] Cons.prems(3) by blast
  show ?case
  proof (cases "merge pol rank (available parent (debit (path parent fund) held bal) a) ps")
    case (Refused why)
    then show ?thesis using Cons.prems(1) q by simp
  next
    case (Granted g r)
    define bal1 where "bal1 = debit (path parent a) (total (proposers ps) g) bal"
    obtain gs1 h1 bal2 where rec: "pots pol rank parent fund rest (held + r) bal1 = Some (gs1, h1, bal2)"
      using Cons.prems(1) q Granted by (auto simp: bal1_def split: option.splits)
    have out: "gs = g # gs1" "bal' = bal2" using Cons.prems(1) q Granted rec by (simp_all add: bal1_def)
    have IH: "bal1 b - bal2 b = sum_list (map2 (\<lambda>(a, ps) g. total (proposers ps) g) rest gs1)"
      using Cons.IH[OF rec _ Cons.prems(3)] Cons.prems(2) by simp
    have now: "bal b - bal1 b = total (proposers ps) g" using ba by (simp add: bal1_def debit_def)
    show ?thesis using IH now q by (simp add: out algebra_simps)
  qed
qed
(* GATE:END *)


section \<open>What a merge grants and holds back\<close>

text \<open>Where the tie rule rations on every set, a merge that grants gives each request no more
  than it asked and nothing negative, holds back a non-negative residual, and grants with the
  residual no more than is available. Where the requests do not all fit, the grants and the
  residual together are what is available.\<close>

lemma merge_of_bounds:
  fixes v :: "('k, 'n::linordered_idom) amounts"
  assumes fin: "finite K" and nn: "nonneg_on K v"
    and tie: "\<forall>t. tie pol = Some t \<longrightarrow> (\<forall>G. rations G (t G))"
    and gr: "merge_of pol rank av K v = Granted g r"
  shows "nonneg_on K g \<and> fits_in g v \<and> 0 \<le> r \<and> total K g + r \<le> max 0 av
         \<and> (\<not> total K v \<le> av \<longrightarrow> total K g + r = max 0 av)"
proof -
  have nnv: "\<forall>k. 0 \<le> v k" and off: "\<forall>k. k \<notin> K \<longrightarrow> v k = 0" using nn by (simp_all add: nonneg_on_def)
  have t0: "0 \<le> total K v" by (rule total_nonneg[OF nn])
  show ?thesis
  proof (cases "total K v \<le> av")
    case True
    then have "g = v" "r = 0" using gr by (simp_all add: merge_of_def Let_def)
    then show ?thesis using True nn by (simp add: fits_in_def)
  next
    case nf: False
    let ?x = "max 0 av"
    have x0: "0 \<le> ?x" by simp
    have xv: "?x \<le> total K v" using nf t0 by simp
    show ?thesis
    proof (cases "tie pol")
      case None
      have nt: "\<not> tie_arises K rank v ?x" and g: "g = by_rank rank (\<lambda>_ _ _. nothing) K v ?x"
          and rr: "r = ?x - total K g"
        using gr nf None by (auto simp: merge_of_def Let_def split: if_splits)
      have tg: "total K g = ?x" unfolding g by (rule by_rank_exact_where_no_tie[OF fin nn x0 xv nt])
      have each: "0 \<le> g k \<and> g k \<le> v k" for k
      proof (cases "k \<in> K")
        case False
        then show ?thesis using off by (simp add: g by_rank_def)
      next
        case kK: True
        let ?left = "?x - ahead K rank v k" and ?G = "beside K rank k"
        have notie: "\<not> (0 < ?left \<and> ?left < total ?G v \<and> ?G \<noteq> {k})" using nt kK by (auto simp: tie_arises_def)
        show ?thesis
        proof (cases "total ?G v \<le> ?left")
          case True
          then show ?thesis using kK nnv by (simp add: g by_rank_def Let_def)
        next
          case F1: False
          show ?thesis
          proof (cases "?left \<le> 0")
            case True
            then show ?thesis using kK F1 nnv by (simp add: g by_rank_def Let_def)
          next
            case F2: False
            then have single: "?G = {k}" using notie F1 by auto
            have "total ?G v = v k" using single by (simp add: total_def)
            then show ?thesis using kK F1 F2 single nnv by (auto simp: g by_rank_def Let_def max_def split: if_splits)
          qed
        qed
      qed
      have "nonneg_on K g \<and> fits_in g v"
        using each by (auto simp: nonneg_on_def fits_in_def g by_rank_zero_off)
      then show ?thesis using tg rr by simp
    next
      case (Some t)
      have ok: "\<forall>G\<subseteq>K. rations G (t G)" using tie Some by blast
      have g: "g = by_rank rank t K v ?x" and rr: "r = ?x - total K g"
        using gr nf Some by (auto simp: merge_of_def Let_def split: if_splits)
      have "nonneg_on K g \<and> fits_in g v \<and> total K g \<le> ?x"
        using by_rank_rations_where_the_tie_rule_does(1)[OF fin ok] nn x0 xv by (simp add: rations_def g)
      then show ?thesis using rr by simp
    qed
  qed
qed


section \<open>No balance below zero, and no pot paid more than its own amount\<close>

lemma pots_in_range:
  fixes qs :: "('a \<times> ('k \<times> 'n::linordered_idom) list) list"
  assumes tr: "tree A parent"
    and tie: "\<forall>t. tie pol = Some t \<longrightarrow> (\<forall>G. rations G (t G))"
  shows "\<forall>q\<in>set qs. fst q \<in> A \<Longrightarrow> \<forall>q\<in>set qs. \<forall>p\<in>set (snd q). 0 \<le> snd p \<Longrightarrow>
         0 \<le> held \<Longrightarrow> \<forall>b\<in>A. 0 \<le> bal b \<Longrightarrow> pots pol rank parent fund qs held bal = Some (gs, h, bal') \<Longrightarrow>
           (\<forall>b\<in>A. 0 \<le> bal' b) \<and> (\<forall>b. bal' b \<le> bal b)
           \<and> list_all2 (\<lambda>q g. 0 \<le> total (proposers (snd q)) g \<and> total (proposers (snd q)) g \<le> bal (fst q)) qs gs"
proof (induction qs arbitrary: held bal gs h bal')
  case Nil
  then show ?case by simp
next
  case (Cons q rest)
  obtain a ps where q: "q = (a, ps)" by (cases q)
  have a: "a \<in> A" using Cons.prems(1) q by simp
  let ?balh = "debit (path parent fund) held bal"
  let ?av = "available parent ?balh a"
  show ?case
  proof (cases "merge pol rank ?av ps")
    case (Refused why)
    then show ?thesis using Cons.prems(5) q by simp
  next
    case (Granted g r)
    let ?K = "proposers ps" and ?v = "requested ps"
    have fin: "finite ?K" by (simp add: proposers_def)
    have nnv: "nonneg_on ?K ?v" using Cons.prems(2) q by (intro requested_nonneg) simp
    have mo: "merge_of pol rank ?av ?K ?v = Granted g r" using Granted by (simp add: merge_def)
    note bd = merge_of_bounds[OF fin nnv tie mo]
    have tg0: "0 \<le> total ?K g" using bd total_nonneg by blast
    have r0: "0 \<le> r" and tgr: "total ?K g + r \<le> max 0 ?av" using bd by simp_all
    have tgb: "total ?K g \<le> bal b" if b: "b \<in> path parent a" for b
    proof -
      have "?av \<le> ?balh b" by (rule available_le[OF tr a b])
      also have "\<dots> \<le> bal b" using Cons.prems(3) by (simp add: debit_def)
      finally have avb: "?av \<le> bal b" .
      have "0 \<le> bal b" using Cons.prems(4) path_in_tree[OF tr a] b by blast
      then have "max 0 ?av \<le> bal b" using avb by (rule max.boundedI)
      then show ?thesis using tgr r0 by linarith
    qed
    define bal1 where "bal1 = debit (path parent a) (total ?K g) bal"
    obtain gs1 h1 bal2 where rec: "pots pol rank parent fund rest (held + r) bal1 = Some (gs1, h1, bal2)"
      using Cons.prems(5) q Granted by (auto simp: bal1_def split: option.splits)
    have out: "gs = g # gs1" "bal' = bal2" using Cons.prems(5) q Granted rec by (simp_all add: bal1_def)
    have h1: "0 \<le> held + r" using Cons.prems(3) r0 by simp
    have b1: "\<forall>b\<in>A. 0 \<le> bal1 b"
    proof
      fix b
      assume b: "b \<in> A"
      show "0 \<le> bal1 b"
      proof (cases "b \<in> path parent a")
        case True
        then show ?thesis using tgb[OF True] by (simp add: bal1_def debit_def)
      next
        case False
        then show ?thesis using Cons.prems(4) b by (simp add: bal1_def debit_def)
      qed
    qed
    have le1: "\<forall>b. bal1 b \<le> bal b" using tg0 by (simp add: bal1_def debit_def)
    have IH: "(\<forall>b\<in>A. 0 \<le> bal2 b) \<and> (\<forall>b. bal2 b \<le> bal1 b)
              \<and> list_all2 (\<lambda>q g. 0 \<le> total (proposers (snd q)) g \<and> total (proposers (snd q)) g \<le> bal1 (fst q)) rest gs1"
      using Cons.IH[OF _ _ h1 b1 rec] Cons.prems(1,2) by simp
    have le2: "\<forall>b. bal2 b \<le> bal b" using IH le1 by (meson order_trans)
    have mono: "list_all2 (\<lambda>q g. 0 \<le> total (proposers (snd q)) g \<and> total (proposers (snd q)) g \<le> bal (fst q)) rest gs1"
    proof (rule list_all2_mono[OF conjunct2[OF conjunct2[OF IH]]])
      fix x y
      assume "0 \<le> total (proposers (snd x)) y \<and> total (proposers (snd x)) y \<le> bal1 (fst x)"
      then show "0 \<le> total (proposers (snd x)) y \<and> total (proposers (snd x)) y \<le> bal (fst x)"
        using le1[rule_format, of "fst x"] by simp
    qed
    show ?thesis using IH le2 mono tgb[of a] tg0 by (simp add: out q)
  qed
qed

text \<open>Every pot is an account of the tree, every request is non-negative, nothing is held back
  at the start, and the tie rule, where there is one, rations on every set.\<close>

(* GATE:BEGIN LP2 *)
theorem pots_never_overdraw:
  assumes tr: "tree A parent" and inA: "\<forall>q\<in>set qs. fst q \<in> A"
    and tie: "\<forall>t. tie pol = Some t \<longrightarrow> (\<forall>G. rations G (t G))"
    and nn: "\<forall>q\<in>set qs. \<forall>p\<in>set (snd q). 0 \<le> snd p" and b0: "\<forall>b\<in>A. 0 \<le> bal b"
    and po: "pots pol rank parent fund qs 0 bal = Some (gs, h, bal')"
  shows "\<forall>b\<in>A. 0 \<le> bal' b"
    and "list_all2 (\<lambda>q g. 0 \<le> total (proposers (snd q)) g \<and> total (proposers (snd q)) g \<le> bal (fst q)) qs gs"
  using pots_in_range[OF tr tie inA nn _ b0 po] by simp_all
(* GATE:END *)


section \<open>Where the fund binds a pot, no later pot is paid\<close>

lemma pots_after_the_fund_is_spent:
  fixes qs :: "('a \<times> ('k \<times> 'n::linordered_idom) list) list"
  assumes tr: "tree A parent" and fA: "fund \<in> A"
    and tie: "\<forall>t. tie pol = Some t \<longrightarrow> (\<forall>G. rations G (t G))"
  shows "\<forall>q\<in>set qs. fst q \<in> A \<and> fund \<in> path parent (fst q) \<Longrightarrow> \<forall>q\<in>set qs. \<forall>p\<in>set (snd q). 0 \<le> snd p \<Longrightarrow>
         available parent (debit (path parent fund) held bal) fund \<le> 0 \<Longrightarrow>
         pots pol rank parent fund qs held bal = Some (gs, h, bal') \<Longrightarrow>
           list_all2 (\<lambda>q g. total (proposers (snd q)) g = 0) qs gs"
proof (induction qs arbitrary: gs h bal')
  case Nil
  then show ?case by simp
next
  case (Cons q rest)
  obtain a ps where q: "q = (a, ps)" by (cases q)
  have a: "a \<in> A" and fa: "fund \<in> path parent a" using Cons.prems(1) q by simp_all
  let ?balh = "debit (path parent fund) held bal"
  let ?av = "available parent ?balh a"
  show ?case
  proof (cases "merge pol rank ?av ps")
    case (Refused why)
    then show ?thesis using Cons.prems(4) q by simp
  next
    case (Granted g r)
    let ?K = "proposers ps" and ?v = "requested ps"
    have fin: "finite ?K" by (simp add: proposers_def)
    have nnv: "nonneg_on ?K ?v" using Cons.prems(2) q by (intro requested_nonneg) simp
    have mo: "merge_of pol rank ?av ?K ?v = Granted g r" using Granted by (simp add: merge_def)
    note bd = merge_of_bounds[OF fin nnv tie mo]
    have tg0: "0 \<le> total ?K g" using bd total_nonneg by blast
    obtain c where c: "c \<in> path parent fund" and cf: "available parent ?balh fund = ?balh c"
      using available_attained[OF tr fA] by blast
    have ca: "c \<in> path parent a" using path_trans[OF fa] c by blast
    have "?av \<le> ?balh c" by (rule available_le[OF tr a ca])
    then have av0: "?av \<le> 0" using Cons.prems(3) cf by simp
    have m0: "max 0 ?av = 0" using av0 by simp
    have "0 \<le> r" "total ?K g + r \<le> 0" using bd m0 by simp_all
    then have zero: "total ?K g = 0" "r = 0" using tg0 by simp_all
    have bal1: "debit (path parent a) (total ?K g) bal = bal" using zero by (simp add: debit_def fun_eq_iff)
    obtain gs1 h1 bal2 where rec: "pots pol rank parent fund rest held bal = Some (gs1, h1, bal2)"
      using Cons.prems(4) q Granted zero bal1 by (auto split: option.splits)
    have out: "gs = g # gs1" using Cons.prems(4) q Granted rec zero bal1 by simp
    have "list_all2 (\<lambda>q g. total (proposers (snd q)) g = 0) rest gs1"
      using Cons.IH[OF _ _ Cons.prems(3) rec] Cons.prems(1,2) by simp
    then show ?thesis using zero q out by simp
  qed
qed

text \<open>Read for each pot in turn, since every pot heads the pots that follow it. The fund is in the
  tree and above every pot, and the first pot is bound at or above the fund: what was asked there
  exceeds what is available, and what is available there is the fund's.\<close>

(* GATE:BEGIN LP4 *)
theorem a_bound_at_the_fund_pays_no_later_pot:
  assumes tr: "tree A parent" and fA: "fund \<in> A"
    and qs: "\<forall>q\<in>set ((a, ps) # rest). fst q \<in> A \<and> fund \<in> path parent (fst q)"
    and tie: "\<forall>t. tie pol = Some t \<longrightarrow> (\<forall>G. rations G (t G))"
    and nn: "\<forall>q\<in>set ((a, ps) # rest). \<forall>p\<in>set (snd q). 0 \<le> snd p" and h0: "0 \<le> held"
    and bound: "\<not> total (proposers ps) (requested ps) \<le> available parent (debit (path parent fund) held bal) a"
    and above: "available parent (debit (path parent fund) held bal) a
                  = available parent (debit (path parent fund) held bal) fund"
    and po: "pots pol rank parent fund ((a, ps) # rest) held bal = Some (gs, h, bal')"
  shows "list_all2 (\<lambda>q g. total (proposers (snd q)) g = 0) rest (tl gs)"
proof -
  let ?balh = "debit (path parent fund) held bal"
  let ?av = "available parent ?balh a"
  have a: "a \<in> A" and fa: "fund \<in> path parent a" using qs by simp_all
  obtain g r where Granted: "merge pol rank ?av ps = Granted g r"
    using po by (cases "merge pol rank ?av ps") auto
  let ?K = "proposers ps" and ?v = "requested ps"
  have fin: "finite ?K" by (simp add: proposers_def)
  have nnv: "nonneg_on ?K ?v" using nn by (intro requested_nonneg) simp
  have mo: "merge_of pol rank ?av ?K ?v = Granted g r" using Granted by (simp add: merge_def)
  note bd = merge_of_bounds[OF fin nnv tie mo]
  have sum: "total ?K g + r = max 0 ?av" using bd bound by blast
  define bal1 where "bal1 = debit (path parent a) (total ?K g) bal"
  obtain gs1 h1 bal2 where rec: "pots pol rank parent fund rest (held + r) bal1 = Some (gs1, h1, bal2)"
    using po Granted by (auto simp: bal1_def split: option.splits)
  have out: "gs = g # gs1" using po Granted rec by (simp add: bal1_def)
  obtain c where c: "c \<in> path parent fund" and cf: "available parent ?balh fund = ?balh c"
    using available_attained[OF tr fA] by blast
  have ca: "c \<in> path parent a" using path_trans[OF fa] c by blast
  have "debit (path parent fund) (held + r) bal1 c = ?balh c - (total ?K g + r)"
    using c ca by (simp add: bal1_def debit_def algebra_simps)
  also have "\<dots> = ?av - max 0 ?av" using above cf sum by simp
  also have "\<dots> \<le> 0" by simp
  finally have c0: "debit (path parent fund) (held + r) bal1 c \<le> 0" .
  have "available parent (debit (path parent fund) (held + r) bal1) fund \<le> debit (path parent fund) (held + r) bal1 c"
    by (rule available_le[OF tr fA c])
  then have "available parent (debit (path parent fund) (held + r) bal1) fund \<le> 0" using c0 by simp
  then have "list_all2 (\<lambda>q g. total (proposers (snd q)) g = 0) rest gs1"
    using pots_after_the_fund_is_spent[OF tr fA tie _ _ _ rec] qs nn by simp
  then show ?thesis using out by simp
qed
(* GATE:END *)


section \<open>Two instances kept on purpose\<close>

text \<open>A fund, account 1, with two pots under it, accounts 2 and 3, and account 0 above the fund. A
  merge grants each request whole or not at all and may leave a residual. The first pot's requests
  of 5 and 4 meet 7 available: 5 is granted and 2 left. In the first book the fund holds 7 and
  account 0 holds 100. Settled at each pot in turn with nothing carried, the second pot's request
  of 2 takes the 2 the first pot left, and `pots` withholds them. In the second book account 0
  holds 7 and the fund 100. With the 2 withheld from the fund alone, the second pot still takes
  them, since account 0 is the one that binds, and `pots` withholds them along the fund's path.\<close>

(* GATE:BEGIN LPn *)
theorem the_unit_left_is_withheld_along_the_path:
  "(case settle \<lparr>refuses = False, ranked = False, tie = Some (\<lambda>_. whole_each [1, 2]), leaves = True, unmixed = False\<rparr>
           (\<lambda>_. 0) (map_of [(1::nat, 0::nat), (2, 1), (3, 1)]) 2 [(1::nat, 5), (2, 4)]
           (\<lambda>a. if a = 0 then 100 else if a = 1 then 7 else if a = 2 then 7 else 10 :: int) of
      (out, bal1) \<Rightarrow>
        (grants [1, 2] out,
         grants [3] (fst (settle \<lparr>refuses = False, ranked = False, tie = Some (\<lambda>_. whole_each [1, 2]), leaves = True, unmixed = False\<rparr>
                          (\<lambda>_. 0) (map_of [(1::nat, 0::nat), (2, 1), (3, 1)]) 3 [(3::nat, 2)] bal1))))
   = (([5, 0], 2), ([2], 0))
   \<and> (case pots \<lparr>refuses = False, ranked = False, tie = Some (\<lambda>_. whole_each [1, 2]), leaves = True, unmixed = False\<rparr>
            (\<lambda>_. 0) (map_of [(1::nat, 0::nat), (2, 1), (3, 1)]) 1 [(2, [(1::nat, 5), (2, 4)]), (3, [(3, 2)])] 0
            (\<lambda>a. if a = 0 then 100 else if a = 1 then 7 else if a = 2 then 7 else 10 :: int) of
        None \<Rightarrow> None
      | Some (gs, h, bal) \<Rightarrow> Some (map (\<lambda>g. map g [1, 2, 3]) gs, h))
     = Some ([[5, 0, 0], [0, 0, 0]], 2)
   \<and> (case settle \<lparr>refuses = False, ranked = False, tie = Some (\<lambda>_. whole_each [1, 2]), leaves = True, unmixed = False\<rparr>
           (\<lambda>_. 0) (map_of [(1::nat, 0::nat), (2, 1), (3, 1)]) 2 [(1::nat, 5), (2, 4)]
           (\<lambda>a. if a = 0 then 7 else if a = 1 then 100 else if a = 2 then 7 else 10 :: int) of
      (out, bal1) \<Rightarrow>
        grants [3] (merge \<lparr>refuses = False, ranked = False, tie = Some (\<lambda>_. whole_each [1, 2]), leaves = True, unmixed = False\<rparr>
                     (\<lambda>_. 0) (available (map_of [(1::nat, 0::nat), (2, 1), (3, 1)]) (debit {1} 2 bal1) 3) [(3::nat, 2)]))
     = ([2], 0)
   \<and> (case pots \<lparr>refuses = False, ranked = False, tie = Some (\<lambda>_. whole_each [1, 2]), leaves = True, unmixed = False\<rparr>
            (\<lambda>_. 0) (map_of [(1::nat, 0::nat), (2, 1), (3, 1)]) 1 [(2, [(1::nat, 5), (2, 4)]), (3, [(3, 2)])] 0
            (\<lambda>a. if a = 0 then 7 else if a = 1 then 100 else if a = 2 then 7 else 10 :: int) of
        None \<Rightarrow> None
      | Some (gs, h, bal) \<Rightarrow> Some (map (\<lambda>g. map g [1, 2, 3]) gs, h))
     = Some ([[5, 0, 0], [0, 0, 0]], 2)"
  by code_simp
(* GATE:END *)

end
