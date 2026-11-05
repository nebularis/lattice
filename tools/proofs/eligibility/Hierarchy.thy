(* Eligibility's hierarchical match over a hierarchy relation taken as a parameter (L9, L10, L14), hand-written
   on top of the generated Kernel. The relation is any set of (narrower, broader) pairs, so what is proved holds
   for every relation a condition may name, skos:broader or a sub-property of it. The decision reads the relation
   only through its links between members of the scheme (ordering), so a link of another relation, or a link
   to a concept outside the scheme, cannot change it. The scheme is resolved: the case of no resolved scheme is
   Undetermined for every candidate, and Resolution models it. *)

theory Hierarchy
imports Kernel
begin

definition ordering :: "'a set \<Rightarrow> ('a \<times> 'a) set \<Rightarrow> ('a \<times> 'a) set" where
  "ordering M R = R \<inter> (M \<times> M)"

definition has_hierarchy :: "'a set \<Rightarrow> ('a \<times> 'a) set \<Rightarrow> bool" where
  "has_hierarchy M R = (ordering M R \<noteq> {})"

definition matches :: "'a set \<Rightarrow> ('a \<times> 'a) set \<Rightarrow> 'a \<Rightarrow> 'a \<Rightarrow> bool" where
  "matches M R x c = ((x, c) \<in> rtrancl (ordering M R))"

definition hier_decide :: "'a set \<Rightarrow> ('a \<times> 'a) set \<Rightarrow> 'a set \<Rightarrow> 'a set \<Rightarrow> 'a \<Rightarrow> decision" where
  "hier_decide M R req exc x =
     (if x \<notin> M then Undetermined
      else if (\<exists>c \<in> exc. matches M R x c) then Denied
      else if \<not> has_hierarchy M R then (if x \<in> req then Permitted else Undetermined)
      else if req \<noteq> {} \<and> \<not> (\<exists>c \<in> req. matches M R x c) then Denied
      else if (\<exists>c \<in> exc. c \<in> M \<and> matches M R c x \<and> c \<noteq> x) then Undetermined
      else Permitted)"

lemma matches_empty: "ordering M R = {} \<Longrightarrow> matches M R x c = (x = c)"
  by (simp add: matches_def)

(* GATE:BEGIN TH1 *)
lemma hier_decide_reads_only_the_ordering:
  assumes o: "ordering M R = ordering M R'"
  shows "hier_decide M R req exc x = hier_decide M R' req exc x"
(* GATE:END *)
  unfolding hier_decide_def has_hierarchy_def matches_def by (simp only: o)

(* GATE:BEGIN TH2 *)
lemma hier_decide_no_hierarchy_undetermined:
  assumes h: "\<not> has_hierarchy M R" and m: "x \<in> M" and r: "x \<notin> req" and e: "x \<notin> exc"
  shows "hier_decide M R req exc x = Undetermined"
(* GATE:END *)
proof -
  from h have o: "ordering M R = {}" by (simp add: has_hierarchy_def)
  show ?thesis using m r e by (auto simp: hier_decide_def h matches_empty[OF o])
qed

(* GATE:BEGIN TH3 *)
lemma hier_decide_exclusion_denied:
  "\<lbrakk> x \<in> M; c \<in> exc; matches M R x c \<rbrakk> \<Longrightarrow> hier_decide M R req exc x = Denied"
(* GATE:END *)
  by (auto simp: hier_decide_def)

(* GATE:BEGIN TH4 *)
lemma hier_decide_empty_relation_is_flat:
  "\<lbrakk> \<not> has_hierarchy M R; x \<in> M \<rbrakk> \<Longrightarrow> hier_decide M R req exc x = hier_decide M {} req exc x"
(* GATE:END *)
  by (rule hier_decide_reads_only_the_ordering) (simp add: has_hierarchy_def ordering_def)

(* Adequacy on one scheme carrying two relations: members 0 (a tumour), 1 (a carcinoma, a kind of 0) and 2 (a
   margin, part of 0). A condition requiring 0 walks the kind links, the part links, or both (skos:broader,
   which states each link too). *)

lemma matches_step: "\<lbrakk> x \<in> M; c \<in> M; (x, c) \<in> R \<rbrakk> \<Longrightarrow> matches M R x c"
  by (auto simp: matches_def ordering_def)

lemma matches_no_out:
  assumes "\<forall>b. (x, b) \<notin> ordering M R"
  shows "matches M R x c = (x = c)"
  using assms unfolding matches_def by (auto elim: converse_rtranclE)

(* GATE:BEGIN AQH *)
lemma adequacy_kind_carcinoma: "hier_decide {0, 1, 2::nat} {(1, 0)} {0} {} 1 = Permitted"
  and adequacy_kind_margin: "hier_decide {0, 1, 2::nat} {(1, 0)} {0} {} 2 = Denied"
  and adequacy_part_carcinoma: "hier_decide {0, 1, 2::nat} {(2, 0)} {0} {} 1 = Denied"
  and adequacy_part_margin: "hier_decide {0, 1, 2::nat} {(2, 0)} {0} {} 2 = Permitted"
  and adequacy_either_margin: "hier_decide {0, 1, 2::nat} {(1, 0), (2, 0)} {0} {} 2 = Permitted"
(* GATE:END *)
  by (auto simp: hier_decide_def has_hierarchy_def matches_no_out ordering_def intro: matches_step)

end
