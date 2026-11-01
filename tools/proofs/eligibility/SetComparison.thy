(* Eligibility's set comparisons (L18), hand-written on top of the set readings of Eligibility.thy and the
   hierarchical match of Hierarchy.thy. A tested value is decided against the reference values by a match
   predicate taken as a parameter: equality is exact match, and hier_match is hierarchical match over any
   relation a condition may name. The decision is Permitted when a reference value matches, Denied when none
   does and the reference set is closed, and Undetermined otherwise. Subset reads the decisions as every value,
   Intersects as some value, and Disjoint as some value negated. The tested set's closure licenses the reading
   (L15, L17) and the reference set's closure licenses a value's Denied. Under hierarchical match a tested value
   outside the scheme is Undetermined (L9), and over a scheme with no link of the relation a value that is not
   equal to a reference value is Undetermined whatever the closure (L14), so hier_member_decide wraps the
   generic decision. *)

theory SetComparison
imports Eligibility Hierarchy
begin

definition member_decide :: "('a \<Rightarrow> 'a \<Rightarrow> bool) \<Rightarrow> 'a list \<Rightarrow> bool \<Rightarrow> 'a \<Rightarrow> decision" where
  "member_decide match B closedB x =
     (if \<exists>b \<in> set B. match x b then Permitted else if closedB then Denied else Undetermined)"

definition subset_decide :: "('a \<Rightarrow> 'a \<Rightarrow> bool) \<Rightarrow> 'a list \<Rightarrow> bool \<Rightarrow> 'a list \<Rightarrow> bool \<Rightarrow> decision" where
  "subset_decide match A closedA B closedB = every_value closedA (map (member_decide match B closedB) A)"

definition intersects_decide :: "('a \<Rightarrow> 'a \<Rightarrow> bool) \<Rightarrow> 'a list \<Rightarrow> bool \<Rightarrow> 'a list \<Rightarrow> bool \<Rightarrow> decision" where
  "intersects_decide match A closedA B closedB = some_value closedA (map (member_decide match B closedB) A)"

definition disjoint_decide :: "('a \<Rightarrow> 'a \<Rightarrow> bool) \<Rightarrow> 'a list \<Rightarrow> bool \<Rightarrow> 'a list \<Rightarrow> bool \<Rightarrow> decision" where
  "disjoint_decide match A closedA B closedB = neg3 (intersects_decide match A closedA B closedB)"

definition hier_match :: "'a set \<Rightarrow> ('a \<times> 'a) set \<Rightarrow> 'a \<Rightarrow> 'a \<Rightarrow> bool" where
  "hier_match M R x c = (x \<in> M \<and> c \<in> M \<and> matches M R x c)"

definition hier_member_decide :: "'a set \<Rightarrow> ('a \<times> 'a) set \<Rightarrow> 'a list \<Rightarrow> bool \<Rightarrow> 'a \<Rightarrow> decision" where
  "hier_member_decide M R B closedB x =
     (if x \<notin> M then Undetermined
      else if \<exists>b \<in> set B. hier_match M R x b then Permitted
      else if \<not> has_hierarchy M R then Undetermined
      else if closedB then Denied else Undetermined)"

definition hier_subset_decide :: "'a set \<Rightarrow> ('a \<times> 'a) set \<Rightarrow> 'a list \<Rightarrow> bool \<Rightarrow> 'a list \<Rightarrow> bool \<Rightarrow> decision" where
  "hier_subset_decide M R A closedA B closedB = every_value closedA (map (hier_member_decide M R B closedB) A)"

definition hier_intersects_decide :: "'a set \<Rightarrow> ('a \<times> 'a) set \<Rightarrow> 'a list \<Rightarrow> bool \<Rightarrow> 'a list \<Rightarrow> bool \<Rightarrow> decision" where
  "hier_intersects_decide M R A closedA B closedB = some_value closedA (map (hier_member_decide M R B closedB) A)"

lemma member_decide_eq:
  "member_decide (=) B closedB x = (if x \<in> set B then Permitted else if closedB then Denied else Undetermined)"
  by (simp add: member_decide_def)

lemma member_decide_permitted_eq: "(member_decide (=) B closedB x = Permitted) \<longleftrightarrow> x \<in> set B"
  by (simp add: member_decide_eq)

lemma member_decide_denied_eq: "(member_decide (=) B closedB x = Denied) \<longleftrightarrow> x \<notin> set B \<and> closedB"
  by (simp add: member_decide_eq)

lemma member_decide_permitted_eq': "(Permitted = member_decide (=) B closedB x) \<longleftrightarrow> x \<in> set B"
  by (simp add: member_decide_eq)

lemma member_decide_denied_eq': "(Denied = member_decide (=) B closedB x) \<longleftrightarrow> x \<notin> set B \<and> closedB"
  by (simp add: member_decide_eq)

(* GATE:BEGIN TS1 *)
lemma subset_decide_permitted_eq:
  "(subset_decide (=) A closedA B closedB = Permitted) \<longleftrightarrow> closedA \<and> set A \<subseteq> set B"
(* GATE:END *)
  unfolding subset_decide_def by (simp only: every_value_spec_permitted) (auto simp: member_decide_permitted_eq member_decide_permitted_eq')

(* GATE:BEGIN TS2 *)
lemma subset_decide_denied_eq:
  "(subset_decide (=) A closedA B closedB = Denied) \<longleftrightarrow> closedB \<and> \<not> set A \<subseteq> set B"
(* GATE:END *)
  unfolding subset_decide_def by (simp only: every_value_spec_denied) (auto simp: member_decide_denied_eq member_decide_denied_eq')

(* GATE:BEGIN TS3 *)
lemma intersects_decide_permitted_eq:
  "(intersects_decide (=) A closedA B closedB = Permitted) \<longleftrightarrow> set A \<inter> set B \<noteq> {}"
(* GATE:END *)
  unfolding intersects_decide_def by (simp only: some_value_spec_permitted) (auto simp: member_decide_permitted_eq member_decide_permitted_eq')

(* GATE:BEGIN TS4 *)
lemma intersects_decide_denied_eq:
  "(intersects_decide (=) A closedA B closedB = Denied) \<longleftrightarrow>
     closedA \<and> set A \<inter> set B = {} \<and> (A = [] \<or> closedB)"
(* GATE:END *)
proof -
  have "(intersects_decide (=) A closedA B closedB = Denied) \<longleftrightarrow>
        closedA \<and> (\<forall>x \<in> set A. x \<notin> set B \<and> closedB)"
    unfolding intersects_decide_def by (simp only: some_value_spec_denied) (auto simp: member_decide_denied_eq member_decide_denied_eq')
  also have "\<dots> \<longleftrightarrow> closedA \<and> set A \<inter> set B = {} \<and> (A = [] \<or> closedB)"
    by (cases A) auto
  finally show ?thesis .
qed

(* GATE:BEGIN TS5 *)
lemma intersects_decide_no_opposite_outcomes:
  "\<not> (intersects_decide (=) A closedA B closedB = Permitted \<and> intersects_decide (=) B closedB A closedA = Denied)"
  "\<not> (intersects_decide (=) A closedA B closedB = Denied \<and> intersects_decide (=) B closedB A closedA = Permitted)"
(* GATE:END *)
  by (auto simp: intersects_decide_permitted_eq intersects_decide_denied_eq Int_commute)

lemma intersects_both_closed:
  "intersects_decide (=) X True Y True = (if set X \<inter> set Y = {} then Denied else Permitted)"
proof (cases "set X \<inter> set Y = {}")
  case True
  then have "intersects_decide (=) X True Y True = Denied" by (simp add: intersects_decide_denied_eq)
  with True show ?thesis by simp
next
  case False
  then have "intersects_decide (=) X True Y True = Permitted" by (simp add: intersects_decide_permitted_eq)
  with False show ?thesis by simp
qed

(* GATE:BEGIN TS6 *)
lemma intersects_decide_symmetric_when_closed:
  "intersects_decide (=) A True B True = intersects_decide (=) B True A True"
(* GATE:END *)
  by (simp only: intersects_both_closed Int_commute)

(* GATE:BEGIN TS7 *)
lemma disjoint_decide_is_intersects_negated:
  "(disjoint_decide match A closedA B closedB = Permitted) \<longleftrightarrow> intersects_decide match A closedA B closedB = Denied"
  "(disjoint_decide match A closedA B closedB = Denied) \<longleftrightarrow> intersects_decide match A closedA B closedB = Permitted"
  "(disjoint_decide match A closedA B closedB = Undetermined) \<longleftrightarrow> intersects_decide match A closedA B closedB = Undetermined"
(* GATE:END *)
  by (cases "intersects_decide match A closedA B closedB"; simp add: disjoint_decide_def)+

(* GATE:BEGIN TS8 *)
lemma hier_member_decide_outside_scheme_undetermined:
  "x \<notin> M \<Longrightarrow> hier_member_decide M R B closedB x = Undetermined"
  "b \<notin> M \<Longrightarrow> \<not> hier_match M R x b"
(* GATE:END *)
  by (simp_all add: hier_member_decide_def hier_match_def)

(* GATE:BEGIN TS9 *)
lemma hier_member_decide_no_hierarchy:
  assumes h: "\<not> has_hierarchy M R" and m: "x \<in> M"
  shows "hier_member_decide M R B closedB x = (if x \<in> set B then Permitted else Undetermined)"
(* GATE:END *)
proof -
  from h have o: "ordering M R = {}" by (simp add: has_hierarchy_def)
  show ?thesis using m h by (auto simp: hier_member_decide_def hier_match_def matches_empty[OF o])
qed

(* GATE:BEGIN TS10 *)
lemma hier_member_decide_with_hierarchy:
  "\<lbrakk> has_hierarchy M R; x \<in> M \<rbrakk> \<Longrightarrow> hier_member_decide M R B closedB x = member_decide (hier_match M R) B closedB x"
(* GATE:END *)
  by (simp add: hier_member_decide_def member_decide_def)

(* Adequacy on a territory fixture: Europe, France (part of Europe), Paris (part of France) and Canada (apart),
   tested sets against reference sets, each comparison, closed and open, equality and the part-of relation. The
   same rows as ontology/eligibility/examples/set-comparison-*.ttl. *)

datatype terr = Europe | France | Paris | Canada | Atlantis

definition terr_members :: "terr set" where
  "terr_members = {Europe, France, Paris, Canada}"

definition terr_part_of :: "(terr \<times> terr) set" where
  "terr_part_of = {(France, Europe), (Paris, France)}"

lemma terr_france_europe: "hier_match terr_members terr_part_of France Europe"
  and terr_paris_france: "hier_match terr_members terr_part_of Paris France"
  by (auto simp: hier_match_def matches_def ordering_def terr_members_def terr_part_of_def)

lemma terr_paris_europe: "hier_match terr_members terr_part_of Paris Europe"
  using terr_france_europe terr_paris_france
  by (auto simp: hier_match_def matches_def ordering_def terr_members_def terr_part_of_def intro: rtrancl_into_rtrancl)

lemma terr_members_facts: "Europe \<in> terr_members" "France \<in> terr_members" "Paris \<in> terr_members"
  "Canada \<in> terr_members" "Atlantis \<notin> terr_members"
  by (simp_all add: terr_members_def)

lemma terr_canada_atlantis: "\<not> hier_match terr_members terr_part_of Canada Atlantis"
  by (rule hier_member_decide_outside_scheme_undetermined(2)) (simp add: terr_members_def)

lemma terr_has_hierarchy: "has_hierarchy terr_members terr_part_of"
  by (auto simp: has_hierarchy_def ordering_def terr_members_def terr_part_of_def)

lemma terr_flat_has_no_hierarchy: "\<not> has_hierarchy terr_members {}"
  by (simp add: has_hierarchy_def ordering_def)

lemma terr_flat_paris: "hier_match terr_members {} Paris Paris"
  and terr_flat_france_paris: "\<not> hier_match terr_members {} France Paris"
  by (auto simp: hier_match_def matches_def ordering_def terr_members_def)

lemma terr_canada_alone: "\<forall>b. (Canada, b) \<notin> ordering terr_members terr_part_of"
  by (auto simp: ordering_def terr_members_def terr_part_of_def)

lemma terr_canada_europe: "\<not> hier_match terr_members terr_part_of Canada Europe"
proof -
  have "matches terr_members terr_part_of Canada Europe = (Canada = Europe)" by (rule matches_no_out[OF terr_canada_alone])
  then show ?thesis by (simp add: hier_match_def)
qed

(* GATE:BEGIN ASC *)
lemma adequacy_subset_inside: "hier_subset_decide terr_members terr_part_of [Paris, France] True [Europe] True = Permitted"
  and adequacy_subset_outside_closed: "hier_subset_decide terr_members terr_part_of [Paris, Canada] True [Europe] True = Denied"
  and adequacy_subset_outside_open: "hier_subset_decide terr_members terr_part_of [Paris, Canada] True [Europe] False = Undetermined"
  and adequacy_subset_unplaced: "hier_subset_decide terr_members terr_part_of [Paris, Atlantis] True [Europe] True = Undetermined"
  and adequacy_subset_flat_found: "hier_subset_decide terr_members {} [Paris] True [Paris] True = Permitted"
  and adequacy_subset_flat_unfound: "hier_subset_decide terr_members {} [France] True [Paris] True = Undetermined"
  and adequacy_intersects_unplaced_reference: "hier_intersects_decide terr_members terr_part_of [Canada] True [Atlantis] True = Denied"
  and adequacy_subset_empty: "subset_decide (=) ([] :: nat list) True [0] False = Permitted"
  and adequacy_subset_open_tested: "subset_decide (=) [0::nat] False [0] True = Undetermined"
  and adequacy_intersects_found: "intersects_decide (=) [0, 1::nat] False [1] False = Permitted"
  and adequacy_intersects_none_closed: "intersects_decide (=) [0::nat] True [1] True = Denied"
  and adequacy_intersects_none_open_reference: "intersects_decide (=) [0::nat] True [1] False = Undetermined"
  and adequacy_intersects_empty: "intersects_decide (=) ([] :: nat list) True [1] False = Denied"
  and adequacy_disjoint_clear: "disjoint_decide (=) [0::nat] True [1] True = Permitted"
  and adequacy_disjoint_shared: "disjoint_decide (=) [0, 1::nat] True [1] True = Denied"
  and adequacy_disjoint_empty: "disjoint_decide (=) ([] :: nat list) True [1] False = Permitted"
(* GATE:END *)
  by (simp_all add: hier_subset_decide_def hier_intersects_decide_def subset_decide_def intersects_decide_def
      disjoint_decide_def member_decide_def hier_member_decide_def terr_members_facts terr_has_hierarchy
      terr_flat_has_no_hierarchy terr_flat_paris terr_flat_france_paris terr_france_europe terr_paris_france
      terr_paris_europe terr_canada_europe terr_canada_atlantis)

end
