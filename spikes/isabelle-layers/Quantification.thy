(* SPDX-License-Identifier: MPL-2.0 *)

(* Quantification: three-valued comparison, bounds, ranges and their meet, cyclic ranges,
   granularity, truncated difference and sums of like values.
   Source: ontology/quantification/README.md sections 5.1, 6, 9 and 10 (laws Q1, Q2, Q4a, Q4b,
   Q5, Q8, Q10, Q13). A spike, not yet aligned to the formal-methods track. *)

theory Quantification
imports Temporal
begin

section \<open>Comparison outcomes\<close>

text \<open>Every comparison is True, False or Undetermined, and Undetermined carries its reason.
A function into this type cannot coerce an indeterminate case to a definite value, which is
law Q10 by construction once each evaluator below is read.\<close>

datatype reason =
  ValueAbsent | ValueMarkedUnresolved | GranularityInsufficient | ConversionContextAbsent
  | OutsideDeclaredSpace | OperationNotPermitted | NoBoundInUnit | MixedBases

datatype outcome = OTrue | OFalse | OUndetermined reason

definition definite :: "outcome \<Rightarrow> bool" where
  "definite x \<longleftrightarrow> (case x of OUndetermined _ \<Rightarrow> False | _ \<Rightarrow> True)"

lemma definite_iff: "definite x \<longleftrightarrow> x = OTrue \<or> x = OFalse"
  by (cases x) (simp_all add: definite_def)

section \<open>Bounds and ranges, law Q2\<close>

datatype closure = Open | Closed

datatype 'a bound = Bound 'a closure

record 'a range =
  lower :: "'a bound option"
  upper :: "'a bound option"

fun above :: "'a::linorder \<Rightarrow> 'a bound option \<Rightarrow> bool" where
  "above x None = True"
| "above x (Some (Bound v c)) = (v < x \<or> (v = x \<and> c = Closed))"

fun below :: "'a::linorder \<Rightarrow> 'a bound option \<Rightarrow> bool" where
  "below x None = True"
| "below x (Some (Bound v c)) = (x < v \<or> (x = v \<and> c = Closed))"

definition contains :: "'a::linorder range \<Rightarrow> 'a \<Rightarrow> bool" where
  "contains r x \<longleftrightarrow> above x (lower r) \<and> below x (upper r)"

text \<open>Closure is never cosmetic: a closed limit is in the range and an open one is not.\<close>

lemma closed_limit_included: "contains \<lparr> lower = Some (Bound v Closed), upper = None \<rparr> v"
  by (simp add: contains_def)

lemma open_limit_excluded: "\<not> contains \<lparr> lower = Some (Bound v Open), upper = None \<rparr> v"
  by (simp add: contains_def)

lemma point_range: "contains \<lparr> lower = Some (Bound v Closed), upper = Some (Bound v Closed) \<rparr> x \<longleftrightarrow> x = v"
  by (auto simp: contains_def)

lemma open_point_empty: "\<not> contains \<lparr> lower = Some (Bound v Open), upper = Some (Bound v Open) \<rparr> x"
  by (auto simp: contains_def)

lemma unbounded_contains_all: "contains \<lparr> lower = None, upper = None \<rparr> x"
  by (simp add: contains_def)

text \<open>The README's table of section 5.1.4, on integers.\<close>

lemma table_half_open:
  "\<not> contains \<lparr> lower = Some (Bound (17640::int) Closed), upper = Some (Bound 18360 Open) \<rparr> 18360"
  by (simp add: contains_def)

lemma table_closed:
  "contains \<lparr> lower = Some (Bound (17640::int) Closed), upper = Some (Bound 18360 Closed) \<rparr> 18360"
  by (simp add: contains_def)

section \<open>The meet of two ranges, laws Q4a and Q4b\<close>

text \<open>The tighter of two lower bounds is the greater value, and at equal values the open one.
Symmetrically for upper bounds.\<close>

fun tighter_lower :: "'a::linorder bound option \<Rightarrow> 'a bound option \<Rightarrow> 'a bound option" where
  "tighter_lower None b = b"
| "tighter_lower a None = a"
| "tighter_lower (Some (Bound v c)) (Some (Bound w d)) =
     (if v < w then Some (Bound w d)
      else if w < v then Some (Bound v c)
      else Some (Bound v (if c = Open \<or> d = Open then Open else Closed)))"

fun tighter_upper :: "'a::linorder bound option \<Rightarrow> 'a bound option \<Rightarrow> 'a bound option" where
  "tighter_upper None b = b"
| "tighter_upper a None = a"
| "tighter_upper (Some (Bound v c)) (Some (Bound w d)) =
     (if v < w then Some (Bound v c)
      else if w < v then Some (Bound w d)
      else Some (Bound v (if c = Open \<or> d = Open then Open else Closed)))"

lemma above_tighter: "above x (tighter_lower a b) \<longleftrightarrow> above x a \<and> above x b"
proof (cases a)
  case None
  then show ?thesis by simp
next
  case (Some ba)
  obtain v c where ba: "ba = Bound v c" by (cases ba)
  show ?thesis
  proof (cases b)
    case None
    then show ?thesis using Some by simp
  next
    case (Some bb)
    obtain w d where bb: "bb = Bound w d" by (cases bb)
    show ?thesis
      using \<open>a = Some ba\<close> Some ba bb by (cases c; cases d) auto
  qed
qed

lemma below_tighter: "below x (tighter_upper a b) \<longleftrightarrow> below x a \<and> below x b"
proof (cases a)
  case None
  then show ?thesis by simp
next
  case (Some ba)
  obtain v c where ba: "ba = Bound v c" by (cases ba)
  show ?thesis
  proof (cases b)
    case None
    then show ?thesis using Some by simp
  next
    case (Some bb)
    obtain w d where bb: "bb = Bound w d" by (cases bb)
    show ?thesis
      using \<open>a = Some ba\<close> Some ba bb by (cases c; cases d) auto
  qed
qed

definition meet :: "'a::linorder range \<Rightarrow> 'a range \<Rightarrow> 'a range" where
  "meet r s = \<lparr> lower = tighter_lower (lower r) (lower s), upper = tighter_upper (upper r) (upper s) \<rparr>"

text \<open>Exact range semantics: a value is in the meet exactly when it is in both ranges. The
left-to-right direction is Q4a, soundness, and the right-to-left direction is Q4b,
completeness.\<close>

theorem meet_exact: "contains (meet r s) x \<longleftrightarrow> contains r x \<and> contains s x"
  unfolding meet_def contains_def by (auto simp: above_tighter below_tighter)

corollary q4a_meet_sound: "contains (meet r s) x \<Longrightarrow> contains r x \<and> contains s x"
  by (simp add: meet_exact)

corollary q4b_meet_complete: "contains r x \<Longrightarrow> contains s x \<Longrightarrow> contains (meet r s) x"
  by (simp add: meet_exact)

lemma meet_commute: "contains (meet r s) x \<longleftrightarrow> contains (meet s r) x"
  by (auto simp: meet_exact)

lemma meet_idempotent: "contains (meet r r) x \<longleftrightarrow> contains r x"
  by (simp add: meet_exact)

section \<open>Overlap screens, it does not decide: law Q5\<close>

definition overlaps_r :: "'a::linorder range \<Rightarrow> 'a range \<Rightarrow> bool" where
  "overlaps_r r s \<longleftrightarrow> (\<exists>x. contains r x \<and> contains s x)"

text \<open>Overlap satisfies the soundness half of Q4: whatever overlaps the meet overlaps both.\<close>

lemma overlap_screens: "overlaps_r c (meet a b) \<Longrightarrow> overlaps_r c a \<and> overlaps_r c b"
  unfolding overlaps_r_def by (auto simp: meet_exact)

text \<open>It fails the completeness half. The README's example of section 5.1.9: A from 1 to 10,
B from 20 to 30, and a candidate C from 5 to 25 overlaps each of A and B separately while
overlapping nothing in their meet. Two overlap tests taken one at a time therefore never show
that something satisfies both ranges, which is why overlap is ScreeningRangeSemantics.\<close>

definition closed_range :: "int \<Rightarrow> int \<Rightarrow> int range" where
  "closed_range l u = \<lparr> lower = Some (Bound l Closed), upper = Some (Bound u Closed) \<rparr>"

lemma closed_range_contains: "contains (closed_range l u) x \<longleftrightarrow> l \<le> x \<and> x \<le> u"
  by (auto simp: closed_range_def contains_def)

theorem q5_overlap_not_complete:
  "overlaps_r (closed_range 5 25) (closed_range 1 10) \<and>
   overlaps_r (closed_range 5 25) (closed_range 20 30) \<and>
   \<not> overlaps_r (closed_range 5 25) (meet (closed_range 1 10) (closed_range 20 30))"
proof (intro conjI)
  show "overlaps_r (closed_range 5 25) (closed_range 1 10)"
    unfolding overlaps_r_def by (rule exI[of _ 5]) (simp add: closed_range_contains)
  show "overlaps_r (closed_range 5 25) (closed_range 20 30)"
    unfolding overlaps_r_def by (rule exI[of _ 20]) (simp add: closed_range_contains)
  show "\<not> overlaps_r (closed_range 5 25) (meet (closed_range 1 10) (closed_range 20 30))"
    unfolding overlaps_r_def by (auto simp: meet_exact closed_range_contains)
qed

section \<open>Granularity, law Q10\<close>

text \<open>A value known to granularity g stands for the region from p up to but excluding p + g.
Asking whether the value is before a boundary b is definite only when the whole region is on
one side. A boundary inside the region gives Undetermined with GranularityInsufficient, never a
definite value invented to fill the gap.\<close>

definition before_boundary :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> outcome" where
  "before_boundary p g b =
     (if p + g \<le> b then OTrue
      else if b \<le> p then OFalse
      else OUndetermined GranularityInsufficient)"

lemma q10_no_coercion: "p < b \<Longrightarrow> b < p + g \<Longrightarrow> before_boundary p g b = OUndetermined GranularityInsufficient"
  by (simp add: before_boundary_def)

lemma definite_before_boundary: "definite (before_boundary p g b) \<longleftrightarrow> p + g \<le> b \<or> b \<le> p"
  by (simp add: before_boundary_def definite_iff)

lemma exact_value_definite: "definite (before_boundary p 1 b)"
  unfolding definite_before_boundary by presburger

text \<open>Refining the granularity never loses or flips a definite answer: a non-empty finer region
inside a coarser one that already decided the question decides it the same way. Refinement
moves up the information order, as decision_leq does for Eligibility.\<close>

lemma refinement_keeps_definite:
  assumes "p \<le> p'" and "p' + g' \<le> p + g" and "0 < g'" and "definite (before_boundary p g b)"
  shows "before_boundary p' g' b = before_boundary p g b"
proof -
  have cases: "p + g \<le> b \<or> b \<le> p" using assms(4) unfolding definite_before_boundary .
  show ?thesis
  proof (cases "p + g \<le> b")
    case True
    then have "p' + g' \<le> b" using assms(2) by simp
    with True show ?thesis unfolding before_boundary_def by simp
  next
    case False
    then have bp: "b \<le> p" using cases by simp
    then have "b \<le> p'" and "\<not> p' + g' \<le> b" using assms(1,3) by simp_all
    with False bp show ?thesis unfolding before_boundary_def by simp
  qed
qed

section \<open>Cyclic ranges\<close>

text \<open>A cyclic range on a space of cycle length L is a start and an extent measured forward,
each end with its own closure. Membership is by forward distance from the start.\<close>

record cyclic =
  cstart :: int
  cextent :: int
  sclosure :: closure
  eclosure :: closure

definition fdist :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int" where
  "fdist L s p = (p - s) mod L"

definition ccontains :: "int \<Rightarrow> cyclic \<Rightarrow> int \<Rightarrow> bool" where
  "ccontains L c p \<longleftrightarrow>
     (let d = fdist L (cstart c) p in
        (0 < d \<or> sclosure c = Closed) \<and> (d < cextent c \<or> (d = cextent c \<and> eclosure c = Closed)))"

lemma fdist_periodic: "0 < L \<Longrightarrow> fdist L s (p + L) = fdist L s p"
proof -
  have "p + L - s = (p - s) + L" by simp
  then show ?thesis unfolding fdist_def by (simp only: mod_add_self2)
qed

lemma ccontains_periodic: "0 < L \<Longrightarrow> ccontains L c (p + L) \<longleftrightarrow> ccontains L c p"
  unfolding ccontains_def by (simp add: fdist_periodic)

text \<open>The degenerate cases the README states once so that implementations agree: an extent of
zero with closed ends is a single point, and an extent equal to the cycle length with a closed
start is the whole cycle.\<close>

lemma zero_extent_is_point:
  assumes "0 < L" and "sclosure c = Closed" and "eclosure c = Closed" and "cextent c = 0"
  shows "ccontains L c p \<longleftrightarrow> (p - cstart c) mod L = 0"
proof -
  define d where "d = (p - cstart c) mod L"
  have nonneg: "0 \<le> d" using assms(1) unfolding d_def by simp
  have "ccontains L c p \<longleftrightarrow> (0 < d \<or> sclosure c = Closed) \<and> (d < cextent c \<or> (d = cextent c \<and> eclosure c = Closed))"
    unfolding ccontains_def fdist_def Let_def d_def by simp
  then show ?thesis using assms(2,3,4) nonneg unfolding d_def[symmetric] by auto
qed

lemma whole_cycle:
  assumes "0 < L" and "sclosure c = Closed" and "cextent c = L"
  shows "ccontains L c p"
proof -
  define d where "d = (p - cstart c) mod L"
  have lt: "d < L" using assms(1) unfolding d_def by simp
  have "ccontains L c p \<longleftrightarrow> (0 < d \<or> sclosure c = Closed) \<and> (d < cextent c \<or> (d = cextent c \<and> eclosure c = Closed))"
    unfolding ccontains_def fdist_def Let_def d_def by simp
  then show ?thesis using assms(2,3) lt by auto
qed

text \<open>The README's wrapping window: 22:00 for eight hours, start closed, end open, on a
24-hour cycle. It holds 22:00 and 02:00, and not 06:00 or 10:00.\<close>

definition off_peak :: cyclic where
  "off_peak = \<lparr> cstart = 22, cextent = 8, sclosure = Closed, eclosure = Open \<rparr>"

lemma wrapping_window:
  "ccontains 24 off_peak 22 \<and> ccontains 24 off_peak 2 \<and> \<not> ccontains 24 off_peak 6 \<and> \<not> ccontains 24 off_peak 10"
  by (simp add: ccontains_def fdist_def off_peak_def Let_def)

section \<open>Truncated difference, law Q8\<close>

text \<open>A space with a zero lower bound depletes by truncated subtraction and stays non-negative.
Truncation absorbs an excess silently, which is why a draw that must succeed or fail whole is a
different operation (Ledger).\<close>

definition tdiff :: "int \<Rightarrow> int \<Rightarrow> int" where
  "tdiff a b = max 0 (a - b)"

lemma tdiff_nonneg: "0 \<le> tdiff a b"
  by (simp add: tdiff_def)

lemma tdiff_le: "0 \<le> a \<Longrightarrow> 0 \<le> b \<Longrightarrow> tdiff a b \<le> a"
  by (simp add: tdiff_def)

lemma tdiff_exact: "b \<le> a \<Longrightarrow> tdiff a b = a - b"
  by (simp add: tdiff_def)

lemma tdiff_absorbs_excess: "a < b \<Longrightarrow> tdiff a b = 0"
  by (simp add: tdiff_def)

theorem q8_depletion_nonneg: "0 \<le> bal \<Longrightarrow> 0 \<le> fold (\<lambda>d acc. tdiff acc d) ds bal"
  by (induction ds arbitrary: bal) (auto simp: tdiff_def)

section \<open>Sums of like values, law Q13\<close>

text \<open>A sum is evaluated only over values in one unit and, where the space names a base role, of
one base. Otherwise it is Undetermined, with ConversionContextAbsent for unlike units that no
conversion has made alike and MixedBases for unlike bases, never a total of unlike values.\<close>

record ('u, 'b) measured =
  amt :: int
  in_unit :: 'u
  on_base :: "'b option"

datatype 'v result = Result 'v | Undet reason

definition like_units :: "('u, 'b) measured list \<Rightarrow> bool" where
  "like_units vs \<longleftrightarrow> (\<forall>v \<in> set vs. \<forall>w \<in> set vs. in_unit v = in_unit w)"

definition like_bases :: "('u, 'b) measured list \<Rightarrow> bool" where
  "like_bases vs \<longleftrightarrow> (\<forall>v \<in> set vs. on_base v \<noteq> None \<and> (\<forall>w \<in> set vs. on_base v = on_base w))"

definition sum_like :: "bool \<Rightarrow> ('u, 'b) measured list \<Rightarrow> int result" where
  "sum_like needs_base vs =
     (if \<not> like_units vs then Undet ConversionContextAbsent
      else if needs_base \<and> \<not> like_bases vs then Undet MixedBases
      else Result (sum_list (map amt vs)))"

theorem q13_sum_definite_iff:
  "(\<exists>n. sum_like nb vs = Result n) \<longleftrightarrow> like_units vs \<and> (nb \<longrightarrow> like_bases vs)"
  by (simp add: sum_like_def)

lemma q13_mixed_units: "\<not> like_units vs \<Longrightarrow> sum_like nb vs = Undet ConversionContextAbsent"
  by (simp add: sum_like_def)

lemma q13_unbound_role: "nb \<Longrightarrow> like_units vs \<Longrightarrow> \<not> like_bases vs \<Longrightarrow> sum_like nb vs = Undet MixedBases"
  by (simp add: sum_like_def)

lemma q13_never_a_total_of_unlike_values:
  "sum_like nb vs = Result n \<Longrightarrow> like_units vs"
  by (simp add: sum_like_def split: if_splits)

text \<open>Kilograms and pounds are unlike until a conversion has made them alike.\<close>

lemma unlike_units_example:
  "\<not> like_units [\<lparr> amt = 1, in_unit = ''kg'', on_base = None \<rparr>, \<lparr> amt = 2, in_unit = ''lb'', on_base = None \<rparr>]"
  by (simp add: like_units_def)

text \<open>A count needs neither a unit nor a base.\<close>

definition count_values :: "('u, 'b) measured list \<Rightarrow> int result" where
  "count_values vs = Result (int (length vs))"

lemma count_always_definite: "\<exists>n. count_values vs = Result n"
  by (simp add: count_values_def)

end
