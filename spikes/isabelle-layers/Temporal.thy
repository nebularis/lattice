(* SPDX-License-Identifier: MPL-2.0 *)

(* Temporal scope, half-open and zoned, and month arithmetic.
   Source: ontology/foundation/README.md section 7 (fnd:validFrom, fnd:validTo) and
   ontology/quantification/README.md law Q14. A spike, not yet aligned to the formal-methods track. *)

theory Temporal
imports Main
begin

section \<open>Validity periods\<close>

text \<open>Instants on one zoned axis, as integers. A validity period is half-open: the start is in it
and the end is not. An absent end is open-ended validity, never a sentinel.\<close>

type_synonym instant = int

record scope =
  valid_from :: instant
  valid_to :: "instant option"

definition within :: "instant \<Rightarrow> scope \<Rightarrow> bool" where
  "within t s \<longleftrightarrow> valid_from s \<le> t \<and> (case valid_to s of None \<Rightarrow> True | Some e \<Rightarrow> t < e)"

definition nonempty :: "scope \<Rightarrow> bool" where
  "nonempty s \<longleftrightarrow> (case valid_to s of None \<Rightarrow> True | Some e \<Rightarrow> valid_from s < e)"

text \<open>A period ending at an instant and one starting at it do not overlap.\<close>

lemma abutting_disjoint:
  assumes "valid_to a = Some e" and "valid_from b = e"
  shows "\<not> (within t a \<and> within t b)"
  using assms unfolding within_def by auto

text \<open>A period whose ends coincide is empty: a state entered and left at one instant.\<close>

lemma empty_scope: "valid_to s = Some (valid_from s) \<Longrightarrow> \<not> within t s"
  unfolding within_def by auto

lemma start_included: "nonempty s \<Longrightarrow> within (valid_from s) s"
  unfolding within_def nonempty_def by (auto split: option.splits)

lemma end_excluded: "valid_to s = Some e \<Longrightarrow> \<not> within e s"
  unfolding within_def by auto

lemma open_ended_upward_closed: "valid_to s = None \<Longrightarrow> within t s \<Longrightarrow> t \<le> t' \<Longrightarrow> within t' s"
  unfolding within_def by auto

definition overlaps :: "scope \<Rightarrow> scope \<Rightarrow> bool" where
  "overlaps a b \<longleftrightarrow> (\<exists>t. within t a \<and> within t b)"

text \<open>Two non-empty periods overlap exactly when each starts before the other ends. This is the
condition Vocabulary's EqualSpecificityScopeConflictShape writes as two FILTERs, so the shape
tests exactly overlap, provided the periods are non-empty.\<close>

lemma overlaps_iff:
  assumes "nonempty a" and "nonempty b"
  shows "overlaps a b \<longleftrightarrow>
         (case valid_to a of None \<Rightarrow> True | Some ea \<Rightarrow> valid_from b < ea) \<and>
         (case valid_to b of None \<Rightarrow> True | Some eb \<Rightarrow> valid_from a < eb)"
proof
  assume "overlaps a b"
  then show "(case valid_to a of None \<Rightarrow> True | Some ea \<Rightarrow> valid_from b < ea) \<and>
             (case valid_to b of None \<Rightarrow> True | Some eb \<Rightarrow> valid_from a < eb)"
    unfolding overlaps_def within_def by (auto split: option.splits)
next
  assume rhs: "(case valid_to a of None \<Rightarrow> True | Some ea \<Rightarrow> valid_from b < ea) \<and>
               (case valid_to b of None \<Rightarrow> True | Some eb \<Rightarrow> valid_from a < eb)"
  let ?t = "max (valid_from a) (valid_from b)"
  have "within ?t a \<and> within ?t b"
    using rhs assms unfolding within_def nonempty_def by (auto split: option.splits)
  then show "overlaps a b" unfolding overlaps_def by blast
qed

text \<open>The shape's condition is not exact for an empty period: an empty period overlaps nothing,
yet the condition can hold.\<close>

lemma overlaps_iff_needs_nonempty:
  "\<not> overlaps \<lparr> valid_from = 5, valid_to = Some 5 \<rparr> \<lparr> valid_from = 4, valid_to = Some 6 \<rparr> \<and>
   (case valid_to \<lparr> valid_from = 5, valid_to = Some 5 \<rparr> of None \<Rightarrow> True | Some ea \<Rightarrow> valid_from \<lparr> valid_from = 4, valid_to = Some 6 \<rparr> < ea) \<and>
   (case valid_to \<lparr> valid_from = 4, valid_to = Some 6 \<rparr> of None \<Rightarrow> True | Some eb \<Rightarrow> valid_from \<lparr> valid_from = 5, valid_to = Some 5 \<rparr> < eb)"
  unfolding overlaps_def within_def by auto

section \<open>Month arithmetic, law Q14\<close>

text \<open>Adding a month-denominated extent to a date clamps the day to the last day of the target
month, so 31 January plus one month is the last day of February, and plus two months the last
day of March. The offset is applied whole: it is not two additions of one month, as the last
lemma shows.\<close>

definition is_leap :: "int \<Rightarrow> bool" where
  "is_leap y \<longleftrightarrow> (y mod 4 = 0 \<and> y mod 100 \<noteq> 0) \<or> y mod 400 = 0"

definition days_in_month :: "int \<Rightarrow> int \<Rightarrow> int" where
  "days_in_month y m =
     (if m = 2 then (if is_leap y then 29 else 28)
      else if m = 4 \<or> m = 6 \<or> m = 9 \<or> m = 11 then 30 else 31)"

record date =
  year :: int
  month :: int
  day :: int

definition valid_date :: "date \<Rightarrow> bool" where
  "valid_date d \<longleftrightarrow> 1 \<le> month d \<and> month d \<le> 12 \<and> 1 \<le> day d \<and> day d \<le> days_in_month (year d) (month d)"

definition add_months :: "date \<Rightarrow> int \<Rightarrow> date" where
  "add_months d n =
     (let k = month d - 1 + n; y = year d + k div 12; m = k mod 12 + 1
      in \<lparr> year = y, month = m, day = min (day d) (days_in_month y m) \<rparr>)"

lemma days_in_month_pos: "1 \<le> days_in_month y m"
  unfolding days_in_month_def by auto

lemma add_months_valid:
  assumes "valid_date d"
  shows "valid_date (add_months d n)"
proof -
  have m1: "0 \<le> (month d - 1 + n) mod 12" and m2: "(month d - 1 + n) mod 12 < 12"
    by simp_all
  show ?thesis
    using assms m1 m2 days_in_month_pos[of "year d + (month d - 1 + n) div 12" "(month d - 1 + n) mod 12 + 1"]
    unfolding valid_date_def add_months_def Let_def by auto
qed

definition jan31 :: "int \<Rightarrow> date" where
  "jan31 y = \<lparr> year = y, month = 1, day = 31 \<rparr>"

lemma q14_one_month: "add_months (jan31 2027) 1 = \<lparr> year = 2027, month = 2, day = 28 \<rparr>"
  by (simp add: add_months_def jan31_def days_in_month_def is_leap_def Let_def)

lemma q14_two_months: "add_months (jan31 2027) 2 = \<lparr> year = 2027, month = 3, day = 31 \<rparr>"
  by (simp add: add_months_def jan31_def days_in_month_def is_leap_def Let_def)

lemma q14_leap_year: "add_months (jan31 2028) 1 = \<lparr> year = 2028, month = 2, day = 29 \<rparr>"
  by (simp add: add_months_def jan31_def days_in_month_def is_leap_def Let_def)

lemma q14_year_boundary: "add_months \<lparr> year = 2027, month = 11, day = 30 \<rparr> 3 = \<lparr> year = 2028, month = 2, day = 29 \<rparr>"
  by (simp add: add_months_def days_in_month_def is_leap_def Let_def)

text \<open>Iterating one month twice loses the day: 31 January, then 28 February, then 28 March. The
law adds the whole extent, giving 31 March. An implementation that loops over months is wrong
by this lemma.\<close>

lemma months_do_not_iterate:
  "add_months (add_months (jan31 2027) 1) 1 \<noteq> add_months (jan31 2027) 2"
  by (simp add: add_months_def jan31_def days_in_month_def is_leap_def Let_def)

text \<open>Clamping is monotone in the day: an earlier day in the month never lands later.\<close>

lemma add_months_day_mono:
  "day d \<le> day e \<Longrightarrow> year d = year e \<Longrightarrow> month d = month e \<Longrightarrow>
   day (add_months d n) \<le> day (add_months e n)"
  unfolding add_months_def Let_def by (auto simp: min_def)

lemma add_months_month_in_range:
  "1 \<le> month (add_months d n) \<and> month (add_months d n) \<le> 12"
  unfolding add_months_def Let_def by simp

end
