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


section \<open>Purposes at one position: no account a request reaches falls below zero\<close>

text \<open>Each set's merge grants at most what the set has room for, and a later merge only lowers
  what is granted, so every set ends within its room.\<close>

lemma admit_bounds:
  fixes v :: "('k, 'n::linordered_idom) amounts"
  assumes tie: "\<forall>t. tie pol = Some t \<longrightarrow> (\<forall>G. rations G (t G))"
  shows "\<forall>k. 0 \<le> v k \<Longrightarrow> \<forall>H\<in>set Hs. finite (fst H) \<Longrightarrow> admit pol rank Hs v r = Granted g s \<Longrightarrow>
           (\<forall>k. 0 \<le> g k \<and> g k \<le> v k) \<and> (\<forall>H\<in>set Hs. total (fst H) g \<le> max 0 (snd H))"
proof (induction Hs arbitrary: v r)
  case Nil
  then show ?case by simp
next
  case (Cons H rest)
  obtain G x where H: "H = (G, x)" by (cases H)
  let ?w = "\<lambda>k. if k \<in> G then v k else 0"
  have finG: "finite G" using Cons.prems(2) H by simp
  have nnw: "nonneg_on G ?w" using Cons.prems(1) by (simp add: nonneg_on_def)
  obtain g1 s1 where mo: "merge_of pol rank x G ?w = Granted g1 s1"
    using Cons.prems(3) H by (cases "merge_of pol rank x G ?w") auto
  note bd = merge_of_bounds[OF finG nnw tie mo]
  let ?v' = "\<lambda>k. if k \<in> G then g1 k else v k"
  have rec: "admit pol rank rest ?v' (r + s1) = Granted g s" using Cons.prems(3) H mo by simp
  have nn': "\<forall>k. 0 \<le> ?v' k" using bd Cons.prems(1) by (simp add: nonneg_on_def)
  have le': "\<forall>k. ?v' k \<le> v k"
  proof
    fix k
    have "g1 k \<le> (if k \<in> G then v k else 0)" using bd by (simp add: fits_in_def)
    then show "?v' k \<le> v k" by (cases "k \<in> G") simp_all
  qed
  have IH: "(\<forall>k. 0 \<le> g k \<and> g k \<le> ?v' k) \<and> (\<forall>H\<in>set rest. total (fst H) g \<le> max 0 (snd H))"
    using Cons.IH[OF nn' _ rec] Cons.prems(2) by simp
  have "total G g \<le> total G ?v'" unfolding total_def by (rule sum_mono) (use IH in blast)
  also have "total G ?v' = total G g1" unfolding total_def by (rule sum.cong) simp_all
  also have "total G g1 \<le> max 0 x" using bd by simp
  finally have tG: "total G g \<le> max 0 x" .
  have "\<forall>k. g k \<le> v k" using IH le' by (meson order_trans)
  then show ?case using IH tG H by simp
qed

text \<open>The sets a request's accounts are limited by are each in the list the merge is given and
  within the proposers, every account a request reaches is one of finitely many and holds a
  non-negative balance, every request is non-negative, and the tie rule, where there is one,
  rations on every set.\<close>

(* GATE:BEGIN LJ2 *)
theorem no_reached_account_below_zero:
  assumes fin: "\<forall>k\<in>proposers ps. finite (reach parent counts a (purpose k))"
    and sets: "\<forall>b. limited (proposers ps) (\<lambda>k. reach parent counts a (purpose k)) b \<noteq> {}
                 \<longrightarrow> limited (proposers ps) (\<lambda>k. reach parent counts a (purpose k)) b \<in> set Gs"
    and sub: "\<forall>G\<in>set Gs. G \<subseteq> proposers ps"
    and tie: "\<forall>t. tie pol = Some t \<longrightarrow> (\<forall>G. rations G (t G))"
    and nn: "\<forall>q\<in>set ps. 0 \<le> snd q"
    and b0: "\<forall>k\<in>proposers ps. \<forall>b\<in>reach parent counts a (purpose k). 0 \<le> bal b"
    and st: "settle_purposes pol rank parent counts a purpose Gs ps bal = (out, bal')"
    and k: "k \<in> proposers ps" and b: "b \<in> reach parent counts a (purpose k)"
  shows "0 \<le> bal' b"
proof -
  let ?K = "proposers ps" and ?R = "\<lambda>k. reach parent counts a (purpose k)"
  let ?Hs = "map (\<lambda>G. (G, room ?K ?R bal G)) Gs"
  have bb: "0 \<le> bal b" using b0 k b by blast
  show ?thesis
  proof (cases "admit pol rank ?Hs (requested ps) 0")
    case (Refused why)
    then have "bal' = bal" using st by (auto simp: settle_purposes_def Let_def split: if_splits)
    then show ?thesis using bb by simp
  next
    case (Granted g r)
    have "bal' = bal \<or> bal' = (\<lambda>b. bal b - total (limited ?K ?R b) g)"
      using st Granted by (auto simp: settle_purposes_def Let_def split: if_splits)
    then show ?thesis
    proof
      assume "bal' = bal"
      then show ?thesis using bb by simp
    next
      assume bal': "bal' = (\<lambda>b. bal b - total (limited ?K ?R b) g)"
      let ?G = "limited ?K ?R b"
      have kG: "k \<in> ?G" using k b by (simp add: limited_def)
      then have G: "?G \<in> set Gs" using sets by blast
      have finK: "finite ?K" by (simp add: proposers_def)
      have nnv: "\<forall>k. 0 \<le> requested ps k" using requested_nonneg[OF nn] by (simp add: nonneg_on_def)
      have finH: "\<forall>H\<in>set ?Hs. finite (fst H)" using sub finK by (auto intro: finite_subset)
      have "\<forall>H\<in>set ?Hs. total (fst H) g \<le> max 0 (snd H)" using admit_bounds[OF tie nnv finH Granted] by blast
      then have tg: "total ?G g \<le> max 0 (room ?K ?R bal ?G)" using G by fastforce
      have S: "{b'. limited ?K ?R b' = ?G} \<subseteq> ?R k" using kG by (auto simp: limited_def)
      have "room ?K ?R bal ?G \<le> bal b" unfolding room_def
        by (rule least_le) (use finite_subset[OF S] fin k in auto)
      then have mx: "max 0 (room ?K ?R bal ?G) \<le> bal b" using bb by simp
      have "total ?G g \<le> bal b" by (rule order_trans[OF tg mx])
      then show ?thesis using bal' by simp
    qed
  qed
qed
(* GATE:END *)


section \<open>Purposes at one position: any narrowest-first list gives the same outcome\<close>

text \<open>A merge refuses for one reason under one policy: refusing when it exceeds, unranked where
  ranks are required, tied with no tie rule, and undecided with one.\<close>

lemma merge_of_reason:
  assumes fin: "finite K" and nn: "nonneg_on K v" and m: "merge_of pol rank av K v = Refused w"
  shows "w = (if refuses pol then Exceeds else if ranked pol then Unranked
              else if tie pol = None then Tied else Undecided)"
proof -
  have t0: "0 \<le> total K v" by (rule total_nonneg[OF nn])
  have nf: "\<not> total K v \<le> av" using m by (auto simp: merge_of_def)
  let ?x = "max 0 av"
  have x0: "0 \<le> ?x" by simp
  have xv: "?x \<le> total K v" using nf t0 by simp
  show ?thesis
  proof (cases "refuses pol")
    case True
    then show ?thesis using m nf by (simp add: merge_of_def Let_def)
  next
    case nr: False
    show ?thesis
    proof (cases "ranked pol")
      case rk: True
      show ?thesis
      proof (cases "inj_on rank K")
        case False
        then show ?thesis using m nf nr rk by (simp add: merge_of_def Let_def)
      next
        case inj: True
        have bs: "beside K rank k = {k}" if "k \<in> K" for k
          using inj that by (auto simp: beside_def inj_on_def)
        have nt: "\<not> tie_arises K rank v ?x" using bs by (auto simp: tie_arises_def)
        have ex: "total K (by_rank rank t K v ?x) = ?x" for t :: "'a set \<Rightarrow> ('a, 'b) rule"
          by (rule by_rank_exact_where_no_tie[OF fin nn x0 xv nt])
        show ?thesis
        proof (cases "tie pol")
          case None
          then show ?thesis using m nf nr rk inj nt by (simp add: merge_of_def Let_def)
        next
          case (Some t)
          then show ?thesis using m nf nr rk inj ex[of t] by (simp add: merge_of_def Let_def)
        qed
      qed
    next
      case nk: False
      show ?thesis using m nf nr nk by (cases "tie pol") (auto simp: merge_of_def Let_def split: if_splits)
    qed
  qed
qed

lemma admit_swap:
  assumes dis: "G \<inter> H = {}" and finG: "finite G" and finH: "finite H" and nn: "\<forall>k. 0 \<le> v k"
  shows "admit pol rank ((G, x) # (H, y) # rest) v r = admit pol rank ((H, y) # (G, x) # rest) v r"
proof -
  let ?vG = "\<lambda>k. if k \<in> G then v k else 0" and ?vH = "\<lambda>k. if k \<in> H then v k else 0"
  have hG: "(\<lambda>k. if k \<in> H then (if k \<in> G then g k else v k) else 0) = ?vH" for g
    using dis by (auto simp: fun_eq_iff)
  have hH: "(\<lambda>k. if k \<in> G then (if k \<in> H then g k else v k) else 0) = ?vG" for g
    using dis by (auto simp: fun_eq_iff)
  have up: "(\<lambda>k. if k \<in> H then gH k else (if k \<in> G then gG k else v k))
              = (\<lambda>k. if k \<in> G then gG k else (if k \<in> H then gH k else v k))" for gG gH
    using dis by (auto simp: fun_eq_iff)
  have nG: "nonneg_on G ?vG" and nH: "nonneg_on H ?vH" using nn by (simp_all add: nonneg_on_def)
  show ?thesis
  proof (cases "merge_of pol rank x G ?vG")
    case (Refused wG)
    show ?thesis
    proof (cases "merge_of pol rank y H ?vH")
      case (Refused wH)
      have "wG = wH" using merge_of_reason[OF finG nG \<open>merge_of pol rank x G ?vG = Refused wG\<close>]
                          merge_of_reason[OF finH nH Refused] by simp
      then show ?thesis using \<open>merge_of pol rank x G ?vG = Refused wG\<close> Refused by simp
    next
      case (Granted gH sH)
      then show ?thesis using \<open>merge_of pol rank x G ?vG = Refused wG\<close> by (simp add: hH)
    qed
  next
    case (Granted gG sG)
    show ?thesis
    proof (cases "merge_of pol rank y H ?vH")
      case (Refused wH)
      then show ?thesis using Granted by (simp add: hG)
    next
      case gH: (Granted gH sH)
      then show ?thesis using Granted by (simp add: hG hH up add.assoc add.commute add.left_commute)
    qed
  qed
qed

lemma admit_to_front:
  assumes tie: "\<forall>t. tie pol = Some t \<longrightarrow> (\<forall>G. rations G (t G))" and finG: "finite G"
  shows "\<forall>H\<in>set ys. G \<inter> fst H = {} \<and> finite (fst H) \<Longrightarrow> \<forall>k. 0 \<le> v k \<Longrightarrow>
           admit pol rank (ys @ (G, x) # zs) v r = admit pol rank ((G, x) # ys @ zs) v r"
proof (induction ys arbitrary: v r)
  case Nil
  then show ?case by simp
next
  case (Cons Hy ys')
  obtain H y where Hy: "Hy = (H, y)" by (cases Hy)
  have dis: "G \<inter> H = {}" and finH: "finite H" using Cons.prems(1) Hy by simp_all
  have rest: "\<forall>H\<in>set ys'. G \<inter> fst H = {} \<and> finite (fst H)" using Cons.prems(1) by simp
  have sw: "admit pol rank ((H, y) # (G, x) # ys' @ zs) v r = admit pol rank ((G, x) # (H, y) # ys' @ zs) v r"
    by (rule admit_swap[OF dis finG finH Cons.prems(2), symmetric])
  let ?vH = "\<lambda>k. if k \<in> H then v k else 0"
  show ?case
  proof (cases "merge_of pol rank y H ?vH")
    case (Refused w)
    have l: "admit pol rank ((H, y) # ys' @ (G, x) # zs) v r = Refused w" using Refused by simp
    have rr: "admit pol rank ((H, y) # (G, x) # ys' @ zs) v r = Refused w" using Refused by simp
    show ?thesis using l rr sw Hy by (simp del: admit.simps)
  next
    case (Granted gH sH)
    have nH: "nonneg_on H ?vH" using Cons.prems(2) by (simp add: nonneg_on_def)
    have "nonneg_on H gH" using merge_of_bounds[OF finH nH tie Granted] by blast
    then have nn': "\<forall>k. 0 \<le> (if k \<in> H then gH k else v k)" using Cons.prems(2) by (simp add: nonneg_on_def)
    have "admit pol rank (ys' @ (G, x) # zs) (\<lambda>k. if k \<in> H then gH k else v k) (r + sH)
            = admit pol rank ((G, x) # ys' @ zs) (\<lambda>k. if k \<in> H then gH k else v k) (r + sH)"
      by (rule Cons.IH[OF rest nn'])
    then show ?thesis using sw Hy Granted by simp
  qed
qed

lemma narrowest_first_sorted:
  assumes nf: "narrowest_first Gs"
  shows "distinct Gs \<and> sorted_wrt (\<lambda>A B. \<not> B \<subset> A) Gs"
proof -
  have d: "distinct Gs" using nf by (simp add: narrowest_first_def)
  have h: "\<forall>i<length Gs. \<forall>j<length Gs. Gs ! i \<subset> Gs ! j \<longrightarrow> i < j" using nf by (simp add: narrowest_first_def)
  have "\<forall>i j. i < j \<longrightarrow> j < length Gs \<longrightarrow> \<not> Gs ! j \<subset> Gs ! i"
  proof (intro allI impI)
    fix i j
    assume ij: "i < j" "j < length Gs"
    show "\<not> Gs ! j \<subset> Gs ! i"
    proof
      assume p: "Gs ! j \<subset> Gs ! i"
      have il: "i < length Gs" using ij by simp
      have "j < i" using h[rule_format, OF ij(2) il p] .
      then show False using ij by simp
    qed
  qed
  then show ?thesis by (simp add: d sorted_wrt_iff_nth_less)
qed

lemma admit_narrowest_first:
  fixes f :: "'k set \<Rightarrow> 'n::linordered_idom"
  assumes tie: "\<forall>t. tie pol = Some t \<longrightarrow> (\<forall>G. rations G (t G))"
    and lam: "\<forall>G\<in>S. \<forall>H\<in>S. G \<subseteq> H \<or> H \<subseteq> G \<or> G \<inter> H = {}" and fin: "\<forall>G\<in>S. finite G"
  shows "set Ls \<subseteq> S \<Longrightarrow> distinct Ls \<Longrightarrow> sorted_wrt (\<lambda>A B. \<not> B \<subset> A) Ls
         \<Longrightarrow> distinct Ms \<Longrightarrow> sorted_wrt (\<lambda>A B. \<not> B \<subset> A) Ms \<Longrightarrow> set Ls = set Ms \<Longrightarrow> \<forall>k. 0 \<le> v k
         \<Longrightarrow> admit pol rank (map (\<lambda>G. (G, f G)) Ls) v r = admit pol rank (map (\<lambda>G. (G, f G)) Ms) v r"
proof (induction Ls arbitrary: Ms v r)
  case Nil
  then show ?case by simp
next
  case (Cons G Ls')
  have GM: "G \<in> set Ms" using Cons.prems(6) by auto
  obtain ys zs where Ms: "Ms = ys @ G # zs" using split_list[OF GM] by blast
  have GS: "G \<in> S" using Cons.prems(1) by simp
  have finG: "finite G" using fin GS by blast
  have dM: "G \<notin> set ys" "G \<notin> set zs" "distinct (ys @ zs)" using Cons.prems(4) Ms by auto
  have dL: "G \<notin> set Ls'" using Cons.prems(2) by simp
  have below: "\<forall>H\<in>set Ls'. \<not> H \<subset> G" using Cons.prems(3) by simp
  have above: "\<forall>H\<in>set ys. \<not> G \<subset> H" using Cons.prems(5) Ms by (simp add: sorted_wrt_append)
  have setys: "set ys \<subseteq> S" using Cons.prems(1,6) Ms by auto
  have disj: "\<forall>H\<in>set (map (\<lambda>G. (G, f G)) ys). G \<inter> fst H = {} \<and> finite (fst H)"
  proof
    fix Hp
    assume "Hp \<in> set (map (\<lambda>G. (G, f G)) ys)"
    then obtain H where H: "H \<in> set ys" and Hp: "Hp = (H, f H)" by auto
    have HS: "H \<in> S" using setys H by blast
    have HG: "H \<noteq> G" using H dM(1) by blast
    have HL: "H \<in> set Ls'" using H Cons.prems(6) Ms HG by auto
    have "\<not> H \<subset> G" using below HL by blast
    moreover have "\<not> G \<subset> H" using above H by blast
    ultimately have "G \<inter> H = {}" using lam GS HS HG by blast
    then show "G \<inter> fst Hp = {} \<and> finite (fst Hp)" using Hp fin HS by simp
  qed
  have front: "admit pol rank (map (\<lambda>G. (G, f G)) Ms) v r
                 = admit pol rank ((G, f G) # map (\<lambda>G. (G, f G)) (ys @ zs)) v r"
    using admit_to_front[OF tie finG disj Cons.prems(7), where x = "f G" and zs = "map (\<lambda>G. (G, f G)) zs"
                                                       and r = r and rank = rank] Ms by simp
  have sM: "sorted_wrt (\<lambda>A B. \<not> B \<subset> A) (ys @ zs)" using Cons.prems(5) Ms by (simp add: sorted_wrt_append)
  have setL: "set Ls' = set (ys @ zs)" using Cons.prems(6) Ms dL dM by auto
  have sL: "set Ls' \<subseteq> S" using Cons.prems(1) by simp
  have dL': "distinct Ls'" and sL': "sorted_wrt (\<lambda>A B. \<not> B \<subset> A) Ls'" using Cons.prems(2,3) by simp_all
  let ?vG = "\<lambda>k. if k \<in> G then v k else 0"
  show ?case
  proof (cases "merge_of pol rank (f G) G ?vG")
    case (Refused w)
    then show ?thesis using front by simp
  next
    case (Granted gG sG)
    have nG: "nonneg_on G ?vG" using Cons.prems(7) by (simp add: nonneg_on_def)
    have "nonneg_on G gG" using merge_of_bounds[OF finG nG tie Granted] by blast
    then have nn': "\<forall>k. 0 \<le> (if k \<in> G then gG k else v k)" using Cons.prems(7) by (simp add: nonneg_on_def)
    have "admit pol rank (map (\<lambda>G. (G, f G)) Ls') (\<lambda>k. if k \<in> G then gG k else v k) (r + sG)
            = admit pol rank (map (\<lambda>G. (G, f G)) (ys @ zs)) (\<lambda>k. if k \<in> G then gG k else v k) (r + sG)"
      by (rule Cons.IH[OF sL dL' sL' dM(3) sM setL nn'])
    then show ?thesis using front Granted by simp
  qed
qed

text \<open>The sets given are pairwise nested or apart, which the refusal of crossing sets secures
  where they are the sets the requests' accounts are limited by, and each is within the proposers.\<close>

(* GATE:BEGIN LJ3 *)
theorem narrowest_first_lists_agree:
  assumes nf1: "narrowest_first Gs1" and nf2: "narrowest_first Gs2" and same: "set Gs1 = set Gs2"
    and lam: "\<forall>G\<in>set Gs1. \<forall>H\<in>set Gs1. G \<subseteq> H \<or> H \<subseteq> G \<or> G \<inter> H = {}"
    and sub: "\<forall>G\<in>set Gs1. G \<subseteq> proposers ps"
    and tie: "\<forall>t. tie pol = Some t \<longrightarrow> (\<forall>G. rations G (t G))"
    and nn: "\<forall>q\<in>set ps. 0 \<le> snd q"
  shows "settle_purposes pol rank parent counts a purpose Gs1 ps bal
           = settle_purposes pol rank parent counts a purpose Gs2 ps bal"
proof -
  let ?K = "proposers ps" and ?R = "\<lambda>k. reach parent counts a (purpose k)"
  have finK: "finite ?K" by (simp add: proposers_def)
  have fin: "\<forall>G\<in>set Gs1. finite G" using sub finK by (auto intro: finite_subset)
  have nnv: "\<forall>k. 0 \<le> requested ps k" using requested_nonneg[OF nn] by (simp add: nonneg_on_def)
  have s1: "distinct Gs1 \<and> sorted_wrt (\<lambda>A B. \<not> B \<subset> A) Gs1" by (rule narrowest_first_sorted[OF nf1])
  have s2: "distinct Gs2 \<and> sorted_wrt (\<lambda>A B. \<not> B \<subset> A) Gs2" by (rule narrowest_first_sorted[OF nf2])
  have "admit pol rank (map (\<lambda>G. (G, room ?K ?R bal G)) Gs1) (requested ps) 0
          = admit pol rank (map (\<lambda>G. (G, room ?K ?R bal G)) Gs2) (requested ps) 0"
    using admit_narrowest_first[OF tie lam fin, where Ls = Gs1 and Ms = Gs2 and v = "requested ps"
                                and f = "room ?K ?R bal" and rank = rank and r = 0] s1 s2 same nnv by simp
  then show ?thesis by (simp add: settle_purposes_def Let_def)
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
