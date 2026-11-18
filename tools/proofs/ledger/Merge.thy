(* SPDX-License-Identifier: MPL-2.0 *)

(* The merge and settlement on the target kernel (plan ledger, LG-20, the fourth group): each
   refusal arises exactly where its condition holds and changes no balance, a granted outcome has
   no residual unless the account declares one may be left, requests with no purpose settle as
   settle does, a mixed or crossing position is refused, two purposes never cross, and the
   instance of a facility with a sublimit. Hand-written on the Kernel extracted from
   ontology/ledger/README.md section 10. *)

theory Merge
imports Units
begin

section \<open>Examples, before any theorem\<close>

text \<open>A facility, account True, holds 100, and a sublimit under it, account False, holds 30 and
  counts letters of credit. A loan of 90, key 1, and a letter of credit of 40, key 2, are drawn on
  the facility at one position and shared in proportion. The letter of credit is first cut to the
  30 its sublimit holds, then the two share the facility's 100 as 75 and 25, which leaves 5 on the
  sublimit.\<close>

definition facility :: "bool \<Rightarrow> bool option" where
  "facility b = (if b then None else Some True)"

value "(case settle_purposes shared (\<lambda>_. 0) facility (\<lambda>_. {False}) True
               (\<lambda>k. if k = 2 then Some (0::nat) else None) [{2::nat}, {1, 2}] [(1, 90::rat), (2, 40)]
               (\<lambda>b. if b then 100 else 30) of
          (out, bal) \<Rightarrow> (grants [1, 2] out, bal True, bal False))"


section \<open>Refusals\<close>

lemma merge_of_never_mixed_or_crossing:
  "merge_of pol rank av K v \<noteq> Refused Mixed \<and> merge_of pol rank av K v \<noteq> Refused Crossing"
  by (auto simp: merge_of_def Let_def split: option.splits)

(* GATE:BEGIN LM1 *)
theorem each_refusal_where_its_condition_holds:
  shows "settle pol rank parent a ps bal = (Refused why, bal') \<Longrightarrow> bal' = bal"
    and "merge_of pol rank av K v = Refused Exceeds \<longleftrightarrow> \<not> total K v \<le> av \<and> refuses pol"
    and "merge_of pol rank av K v = Refused Unranked \<longleftrightarrow>
           \<not> total K v \<le> av \<and> \<not> refuses pol \<and> ranked pol \<and> \<not> inj_on rank K"
    and "merge_of pol rank av K v = Refused Tied \<longleftrightarrow>
           \<not> total K v \<le> av \<and> \<not> refuses pol \<and> \<not> (ranked pol \<and> \<not> inj_on rank K)
           \<and> tie pol = None \<and> tie_arises K rank v (max 0 av)"
    and "merge_of pol rank av K v = Refused Undecided \<longleftrightarrow>
           \<not> total K v \<le> av \<and> \<not> refuses pol \<and> \<not> (ranked pol \<and> \<not> inj_on rank K)
           \<and> (\<exists>t. tie pol = Some t \<and> max 0 av - total K (by_rank rank t K v (max 0 av)) \<noteq> 0) \<and> \<not> leaves pol"
    and "tie pol = None \<Longrightarrow> \<not> total K v \<le> av \<Longrightarrow> \<not> refuses pol \<Longrightarrow> \<not> (ranked pol \<and> \<not> inj_on rank K) \<Longrightarrow>
           (\<exists>why. merge_of pol rank av K v = Refused why) \<longleftrightarrow> tie_arises K rank v (max 0 av)"
proof -
  show "settle pol rank parent a ps bal = (Refused why, bal') \<Longrightarrow> bal' = bal"
    by (auto simp: settle_def split: outcome.splits)
  show "merge_of pol rank av K v = Refused Exceeds \<longleftrightarrow> \<not> total K v \<le> av \<and> refuses pol"
    by (auto simp: merge_of_def Let_def split: option.splits)
  show "merge_of pol rank av K v = Refused Unranked \<longleftrightarrow>
           \<not> total K v \<le> av \<and> \<not> refuses pol \<and> ranked pol \<and> \<not> inj_on rank K"
    by (auto simp: merge_of_def Let_def split: option.splits)
  show "merge_of pol rank av K v = Refused Tied \<longleftrightarrow>
           \<not> total K v \<le> av \<and> \<not> refuses pol \<and> \<not> (ranked pol \<and> \<not> inj_on rank K)
           \<and> tie pol = None \<and> tie_arises K rank v (max 0 av)"
    by (auto simp: merge_of_def Let_def split: option.splits)
  show "merge_of pol rank av K v = Refused Undecided \<longleftrightarrow>
           \<not> total K v \<le> av \<and> \<not> refuses pol \<and> \<not> (ranked pol \<and> \<not> inj_on rank K)
           \<and> (\<exists>t. tie pol = Some t \<and> max 0 av - total K (by_rank rank t K v (max 0 av)) \<noteq> 0) \<and> \<not> leaves pol"
    by (auto simp: merge_of_def Let_def split: option.splits)
  show "tie pol = None \<Longrightarrow> \<not> total K v \<le> av \<Longrightarrow> \<not> refuses pol \<Longrightarrow> \<not> (ranked pol \<and> \<not> inj_on rank K) \<Longrightarrow>
           (\<exists>why. merge_of pol rank av K v = Refused why) \<longleftrightarrow> tie_arises K rank v (max 0 av)"
    by (auto simp: merge_of_def Let_def)
qed
(* GATE:END *)


section \<open>A residual only where the account declares one may be left\<close>

(* GATE:BEGIN LM3 *)
theorem no_residual_unless_declared:
  assumes fin: "finite K" and nn: "nonneg_on K v"
      and gr: "merge_of pol rank av K v = Granted g r" and r: "r \<noteq> 0"
  shows "leaves pol"
proof (rule ccontr)
  assume nl: "\<not> leaves pol"
  have t0: "0 \<le> total K v" by (rule total_nonneg[OF nn])
  show False
  proof (cases "total K v \<le> av")
    case True
    then show False using gr r by (simp add: merge_of_def)
  next
    case nf: False
    have x0: "0 \<le> max 0 av" by simp
    have xv: "max 0 av \<le> total K v" using nf t0 by simp
    show False
    proof (cases "tie pol")
      case None
      have nt: "\<not> tie_arises K rank v (max 0 av)" and g: "g = by_rank rank (\<lambda>_ _ _. nothing) K v (max 0 av)"
          and rr: "r = max 0 av - total K g"
        using gr nf None by (auto simp: merge_of_def Let_def split: if_splits)
      have "total K g = max 0 av" unfolding g by (rule by_rank_exact_where_no_tie[OF fin nn x0 xv nt])
      then show False using rr r by simp
    next
      case (Some t)
      then show False using gr nf nl r by (auto simp: merge_of_def Let_def split: if_splits)
    qed
  qed
qed
(* GATE:END *)


section \<open>Requests with no purpose settle as settle does\<close>

lemma requested_off: "k \<notin> proposers ps \<Longrightarrow> requested ps k = 0"
  by (induct ps) (auto simp: requested_def proposers_def)

lemma by_rank_zero_off: "k \<notin> K \<Longrightarrow> by_rank rank tr K v x k = 0"
  by (simp add: by_rank_def)

lemma merge_of_off:
  assumes gr: "merge_of pol rank av K v = Granted g r" and off: "\<forall>k. k \<notin> K \<longrightarrow> v k = 0" and k: "k \<notin> K"
  shows "g k = 0"
  using gr off k by (auto simp: merge_of_def Let_def by_rank_zero_off split: if_splits option.splits)

(* GATE:BEGIN LJ1 *)
theorem no_purpose_is_settle:
  fixes ps :: "('k \<times> 'n::linordered_idom) list" and counts :: "'p \<Rightarrow> 'a set"
  assumes ne: "ps \<noteq> []"
  shows "settle_purposes pol rank parent counts a (\<lambda>_. None) [proposers ps] ps bal = settle pol rank parent a ps bal"
proof -
  let ?K = "proposers ps"
  let ?R = "\<lambda>k::'k. reach parent counts a (None :: 'p option)"
  have Kne: "?K \<noteq> {}" using ne by (cases ps) (auto simp: proposers_def)
  have lim: "limited ?K ?R b = (if b \<in> path parent a then ?K else {})" for b
    by (auto simp: limited_def reach_def)
  have nc: "\<not> crossing ?K ?R" unfolding crossing_def lim by auto
  have nm: "\<not> mixed ?K (\<lambda>_. None :: 'p option)" by (simp add: mixed_def)
  have rm: "{b. limited ?K ?R b = ?K} = path parent a" using Kne by (auto simp: lim)
  have room: "room ?K ?R bal ?K = available parent bal a" by (simp add: room_def rm available_def)
  have req: "(\<lambda>k. if k \<in> ?K then requested ps k else 0) = requested ps"
    using requested_off by (auto simp: fun_eq_iff)
  have off: "\<forall>k. k \<notin> ?K \<longrightarrow> requested ps k = 0" by (simp add: requested_off)
  show ?thesis
  proof (cases "merge_of pol rank (available parent bal a) ?K (requested ps)")
    case (Granted g s)
    have gk: "(\<lambda>k. if k \<in> ?K then g k else requested ps k) = g"
      using merge_of_off[OF Granted off] requested_off by (auto simp: fun_eq_iff)
    have bal: "(\<lambda>b. bal b - total (limited ?K ?R b) g) = debit (path parent a) (total ?K g) bal"
      by (auto simp: fun_eq_iff lim debit_def total_def)
    show ?thesis
      using Granted nc nm by (simp add: settle_purposes_def settle_def merge_def room req gk bal)
  next
    case (Refused why)
    then show ?thesis using nc nm by (simp add: settle_purposes_def settle_def merge_def room req)
  qed
qed
(* GATE:END *)


section \<open>A mixed or crossing position is refused, and changes nothing\<close>

lemma admit_never_mixed_or_crossing:
  "admit pol rank Gs v r \<noteq> Refused Mixed \<and> admit pol rank Gs v r \<noteq> Refused Crossing"
proof (induct Gs arbitrary: v r)
  case Nil
  then show ?case by simp
next
  case (Cons Gx rest)
  obtain G x where Gx: "Gx = (G, x)" by (cases Gx)
  show ?case
    using Cons merge_of_never_mixed_or_crossing[of pol rank x G "\<lambda>k. if k \<in> G then v k else 0"]
    by (auto simp: Gx split: outcome.splits)
qed

(* GATE:BEGIN LJ4 *)
theorem mixed_or_crossing_refused:
  shows "fst (settle_purposes pol rank parent counts a purpose Gs ps bal) = Refused Mixed
           \<longleftrightarrow> unmixed pol \<and> mixed (proposers ps) purpose"
    and "fst (settle_purposes pol rank parent counts a purpose Gs ps bal) = Refused Crossing
           \<longleftrightarrow> \<not> (unmixed pol \<and> mixed (proposers ps) purpose)
               \<and> crossing (proposers ps) (\<lambda>k. reach parent counts a (purpose k))"
    and "fst (settle_purposes pol rank parent counts a purpose Gs ps bal) = Refused why
           \<Longrightarrow> snd (settle_purposes pol rank parent counts a purpose Gs ps bal) = bal"
proof -
  let ?A = "admit pol rank (map (\<lambda>G. (G, room (proposers ps) (\<lambda>k. reach parent counts a (purpose k)) bal G)) Gs) (requested ps) 0"
  have na: "?A \<noteq> Refused Mixed" "?A \<noteq> Refused Crossing" using admit_never_mixed_or_crossing by blast+
  show "fst (settle_purposes pol rank parent counts a purpose Gs ps bal) = Refused Mixed
           \<longleftrightarrow> unmixed pol \<and> mixed (proposers ps) purpose"
    using na by (auto simp: settle_purposes_def Let_def split: outcome.splits)
  show "fst (settle_purposes pol rank parent counts a purpose Gs ps bal) = Refused Crossing
           \<longleftrightarrow> \<not> (unmixed pol \<and> mixed (proposers ps) purpose)
               \<and> crossing (proposers ps) (\<lambda>k. reach parent counts a (purpose k))"
    using na by (auto simp: settle_purposes_def Let_def split: outcome.splits)
  show "fst (settle_purposes pol rank parent counts a purpose Gs ps bal) = Refused why
           \<Longrightarrow> snd (settle_purposes pol rank parent counts a purpose Gs ps bal) = bal"
    by (auto simp: settle_purposes_def Let_def split: outcome.splits if_splits)
qed
(* GATE:END *)


section \<open>Two purposes never cross\<close>

(* GATE:BEGIN LJ5 *)
theorem two_purposes_never_cross:
  assumes fin: "finite K" and two: "card {p. \<exists>k\<in>K. purpose k = Some p} \<le> 2"
  shows "\<not> crossing K (\<lambda>k. reach parent counts a (purpose k))"
proof
  let ?R = "\<lambda>k. reach parent counts a (purpose k)"
  let ?P = "{p. \<exists>k\<in>K. purpose k = Some p}"
  define C where "C p = (\<Union>c\<in>counts p. path parent c)" for p
  assume "crossing K ?R"
  then obtain b c where I: "limited K ?R b \<inter> limited K ?R c \<noteq> {}"
      and N1: "\<not> limited K ?R b \<subseteq> limited K ?R c" and N2: "\<not> limited K ?R c \<subseteq> limited K ?R b"
    by (auto simp: crossing_def)
  have all: "limited K ?R d = K" if "d \<in> path parent a" for d using that by (auto simp: limited_def reach_def)
  have sub: "limited K ?R d \<subseteq> K" for d by (auto simp: limited_def)
  have bp: "b \<notin> path parent a" using N2 all sub by blast
  have cp: "c \<notin> path parent a" using N1 all sub by blast
  have mem: "k \<in> limited K ?R d \<longleftrightarrow> k \<in> K \<and> (\<exists>p. purpose k = Some p \<and> d \<in> C p)" if "d \<notin> path parent a" for k d
    using that by (auto simp: limited_def reach_def C_def split: option.splits)
  obtain k where kb: "k \<in> limited K ?R b" and kc: "k \<in> limited K ?R c" using I by blast
  from kb obtain p where kK: "k \<in> K" and p: "purpose k = Some p" "b \<in> C p" using mem[OF bp] by blast
  from kc obtain p' where "purpose k = Some p'" "c \<in> C p'" using mem[OF cp] by blast
  then have pc: "c \<in> C p" using p by simp
  obtain k1 where k1b: "k1 \<in> limited K ?R b" and k1c: "k1 \<notin> limited K ?R c" using N1 by blast
  from k1b obtain p1 where k1K: "k1 \<in> K" and p1: "purpose k1 = Some p1" "b \<in> C p1" using mem[OF bp] by blast
  have p1c: "c \<notin> C p1" using k1c k1K p1 mem[OF cp] by blast
  obtain k2 where k2c: "k2 \<in> limited K ?R c" and k2b: "k2 \<notin> limited K ?R b" using N2 by blast
  from k2c obtain p2 where k2K: "k2 \<in> K" and p2: "purpose k2 = Some p2" "c \<in> C p2" using mem[OF cp] by blast
  have p2b: "b \<notin> C p2" using k2b k2K p2 mem[OF bp] by blast
  have d: "p \<noteq> p1" "p \<noteq> p2" "p1 \<noteq> p2" using p pc p1 p1c p2 p2b by auto
  have three: "{p, p1, p2} \<subseteq> ?P" using kK k1K k2K p p1 p2 by auto
  have finP: "finite ?P"
  proof -
    have "?P \<subseteq> the ` purpose ` K" using kK by (force simp: image_iff)
    then show ?thesis by (rule finite_subset) (simp add: fin)
  qed
  have "card {p, p1, p2} \<le> card ?P" using three finP by (rule card_mono[rotated])
  then show False using d two by simp
qed
(* GATE:END *)


section \<open>The instance kept on purpose\<close>

(* GATE:BEGIN LJn *)
theorem a_facility_with_a_sublimit:
  "(case settle_purposes shared (\<lambda>_. 0) facility (\<lambda>_. {False}) True
          (\<lambda>k. if k = 2 then Some (0::nat) else None) [{2::nat}, {1, 2}] [(1, 90::rat), (2, 40)]
          (\<lambda>b. if b then 100 else 30) of
     (out, bal) \<Rightarrow> (grants [1, 2] out, bal True, bal False)) = (([75, 25], 0), 0, 5)"
  by code_simp
(* GATE:END *)


section \<open>Settlement at whole units, in proportion\<close>

text \<open>One rank, so the tie rule decides, and the tie rule is largest remainder with a declared
  order injective on the proposers. Every request is non-negative and every account on the path
  holds a non-negative balance.\<close>

(* GATE:BEGIN LM2 *)
theorem whole_units_settle_in_proportion:
  fixes ps :: "('k \<times> int) list" and parent :: "'a \<Rightarrow> 'a option"
  assumes tr: "tree A parent" and a: "a \<in> A" and inj: "inj_on order (proposers ps)"
    and nr: "\<not> refuses pol" and nk: "\<not> ranked pol" and t: "tie pol = Some (ration (largest_remainder (first_in order)))"
    and nn: "\<forall>q\<in>set ps. 0 \<le> snd q" and b0: "\<forall>b\<in>path parent a. 0 \<le> bal b"
    and st: "settle pol (\<lambda>_. 0) parent a ps bal = (out, bal')"
  shows "\<exists>g. out = Granted g 0
           \<and> total (proposers ps) g = min (total (proposers ps) (requested ps)) (available parent bal a)
           \<and> (\<forall>k\<in>proposers ps. 0 \<le> g k \<and> g k \<le> requested ps k)
           \<and> bal' = debit (path parent a) (total (proposers ps) g) bal
           \<and> (\<forall>b\<in>path parent a. 0 \<le> bal' b)
           \<and> (0 < total (proposers ps) (requested ps) \<longrightarrow>
                (\<forall>k\<in>proposers ps. \<bar>total (proposers ps) (requested ps) * g k
                     - min (total (proposers ps) (requested ps)) (available parent bal a) * requested ps k\<bar>
                   < total (proposers ps) (requested ps)))"
proof -
  let ?K = "proposers ps" and ?v = "requested ps" and ?av = "available parent bal a"
  let ?t = "ration (largest_remainder (first_in order))"
  have fin: "finite ?K" by (simp add: proposers_def)
  have nnv: "nonneg_on ?K ?v" by (rule requested_nonneg[OF nn])
  have av0: "0 \<le> ?av" using available_attained[OF tr a, of bal] b0 by auto
  have avb: "?av \<le> bal b" if "b \<in> path parent a" for b using available_le[OF tr a that] .
  have mg: "merge pol (\<lambda>_. 0) ?av ps = merge_of pol (\<lambda>_. 0) ?av ?K ?v" by (simp add: merge_def)
  obtain g where gdef: "merge_of pol (\<lambda>_. 0) ?av ?K ?v = Granted g 0"
     and gt: "total ?K g = min (total ?K ?v) ?av"
     and gb: "\<forall>k\<in>?K. 0 \<le> g k \<and> g k \<le> ?v k"
     and gu: "0 < total ?K ?v \<longrightarrow> (\<forall>k\<in>?K. \<bar>total ?K ?v * g k - min (total ?K ?v) ?av * ?v k\<bar> < total ?K ?v)"
  proof (cases "total ?K ?v \<le> ?av")
    case True
    have "merge_of pol (\<lambda>_. 0) ?av ?K ?v = Granted ?v 0" using True by (simp add: merge_of_def Let_def)
    moreover have "total ?K ?v = min (total ?K ?v) ?av" using True by simp
    moreover have "\<forall>k\<in>?K. 0 \<le> ?v k \<and> ?v k \<le> ?v k" using nnv by (simp add: nonneg_on_def)
    moreover have "0 < total ?K ?v \<longrightarrow> (\<forall>k\<in>?K. \<bar>total ?K ?v * ?v k - min (total ?K ?v) ?av * ?v k\<bar> < total ?K ?v)"
      using True by simp
    ultimately show ?thesis by (rule that)
  next
    case False
    have x: "max 0 ?av = ?av" using av0 by simp
    have xv: "?av \<le> total ?K ?v" using False by simp
    have law: "lawful ?K (?t ?K)" by (rule ration_lawful(2)[OF fin inj])
    have br: "by_rank (\<lambda>_. 0) ?t ?K ?v ?av = ?t ?K ?v ?av"
      by (rule one_rank_is_the_tie_rule[where rank = "\<lambda>_. 0" and r = 0 and tr = ?t, OF fin _ law nnv av0 xv]) simp
    have ex: "total ?K (?t ?K ?v ?av) = ?av" by (rule ration_largest_remainder_sums_exactly[OF fin inj nnv av0 xv])
    let ?g = "?t ?K ?v ?av"
    have "merge_of pol (\<lambda>_. 0) ?av ?K ?v = Granted ?g 0"
      using False nr nk t x br ex by (simp add: merge_of_def Let_def)
    moreover have "total ?K ?g = min (total ?K ?v) ?av" using ex xv by simp
    moreover have "\<forall>k\<in>?K. 0 \<le> ?g k \<and> ?g k \<le> ?v k"
    proof -
      have "nonneg_on ?K ?g \<and> fits_in ?g ?v" using law nnv av0 xv by (simp add: lawful_def rations_def)
      then show ?thesis by (simp add: nonneg_on_def fits_in_def)
    qed
    moreover have "0 < total ?K ?v \<longrightarrow> (\<forall>k\<in>?K. \<bar>total ?K ?v * ?g k - min (total ?K ?v) ?av * ?v k\<bar> < total ?K ?v)"
    proof (intro impI ballI)
      fix k
      assume Tp: "0 < total ?K ?v" and k: "k \<in> ?K"
      define T where "T = (\<Sum>j\<in>?K. ?v j)"
      have W: "0 < (\<Sum>j\<in>?K. ?v j)" using Tp by (simp add: total_def)
      have h: "\<bar>of_int (?g k) - of_int (?av * ?v k) / of_int T\<bar> < (1::rat)"
        unfolding T_def by (rule rounded_part_within_one_unit(2)[OF k W fin inj nnv av0 xv])
      have Tq: "(0::rat) < of_int T" using W unfolding T_def by (simp only: of_int_0_less_iff)
      have e: "(of_int (T * ?g k - ?av * ?v k) :: rat) = of_int T * (of_int (?g k) - of_int (?av * ?v k) / of_int T)"
        using Tq by (simp add: field_simps)
      have "\<bar>(of_int (T * ?g k - ?av * ?v k) :: rat)\<bar> = of_int T * \<bar>of_int (?g k) - of_int (?av * ?v k) / of_int T\<bar>"
        by (subst e) (use Tq in \<open>simp add: abs_mult\<close>)
      also have "\<dots> < of_int T" using mult_strict_left_mono[OF h Tq] by simp
      finally have "(of_int \<bar>T * ?g k - ?av * ?v k\<bar> :: rat) < of_int T" by (simp only: of_int_abs)
      then have "\<bar>T * ?g k - ?av * ?v k\<bar> < T" by (simp only: of_int_less_iff)
      then show "\<bar>total ?K ?v * ?g k - min (total ?K ?v) ?av * ?v k\<bar> < total ?K ?v"
        using xv by (simp add: T_def total_def)
    qed
    ultimately show ?thesis by (rule that)
  qed
  have so: "out = Granted g 0" "bal' = debit (path parent a) (total ?K g) bal"
    using st gdef mg by (simp_all add: settle_def)
  have nb: "\<forall>b\<in>path parent a. 0 \<le> bal' b"
  proof
    fix b
    assume b: "b \<in> path parent a"
    have "total ?K g \<le> ?av" using gt by simp
    then show "0 \<le> bal' b" using so(2) avb[OF b] b by (simp add: debit_def)
  qed
  show ?thesis using so gt gb nb gu by blast
qed
(* GATE:END *)

end
