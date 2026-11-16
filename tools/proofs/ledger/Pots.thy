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

end
