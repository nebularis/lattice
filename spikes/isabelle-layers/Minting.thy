(* SPDX-License-Identifier: MPL-2.0 *)

(* Identity minting: the self-delimiting tuple encoding, percent-encoding and its decoding, the
   dot-segment hazard, fixed-width positions, and the null and empty scope.
   Source: docs/architecture/identity-minting-specification.md sections 3, 4, 5 and 6, and the
   five rules the ontology-remediation unit added. A spike, not yet aligned to the formal-methods track. *)

theory Minting
imports Main
begin

section \<open>The tuple encoding, section 4.1\<close>

text \<open>A tuple of strings encodes as, for each component, its byte length in decimal, a colon,
and the bytes. The encoding is self-delimiting, so no component value can make two different
tuples encode alike. The proof needs two facts about the length rendering: it is injective
(decimal with no leading zeros) and it contains no colon. Both hold of decimal, shown below.\<close>

locale length_prefix =
  fixes lenstr :: "nat \<Rightarrow> string"
  assumes lenstr_inj: "lenstr n = lenstr m \<Longrightarrow> n = m"
    and lenstr_no_colon: "CHR '':'' \<notin> set (lenstr n)"
begin

fun enc :: "string list \<Rightarrow> string" where
  "enc [] = []"
| "enc (c # cs) = lenstr (length c) @ CHR '':'' # c @ enc cs"

lemma prefix_unique:
  assumes "lenstr n @ CHR '':'' # r = lenstr m @ CHR '':'' # r'"
  shows "n = m \<and> r = r'"
proof -
  let ?P = "\<lambda>ch. ch \<noteq> CHR '':''"
  have t1: "takeWhile ?P (lenstr n @ CHR '':'' # r) = lenstr n"
    using lenstr_no_colon[of n] by (auto simp: takeWhile_tail takeWhile_eq_all_conv)
  have t2: "takeWhile ?P (lenstr m @ CHR '':'' # r') = lenstr m"
    using lenstr_no_colon[of m] by (auto simp: takeWhile_tail takeWhile_eq_all_conv)
  from assms t1 t2 have "lenstr n = lenstr m" by simp
  then have "n = m" by (rule lenstr_inj)
  moreover from assms \<open>lenstr n = lenstr m\<close> have "r = r'" by simp
  ultimately show ?thesis by simp
qed

theorem enc_injective: "enc xs = enc ys \<Longrightarrow> xs = ys"
proof (induction xs arbitrary: ys)
  case Nil
  then show ?case by (cases ys) auto
next
  case (Cons c cs)
  show ?case
  proof (cases ys)
    case Nil
    with Cons.prems show ?thesis by simp
  next
    case (Cons d ds)
    with Cons.prems have "lenstr (length c) @ CHR '':'' # (c @ enc cs) = lenstr (length d) @ CHR '':'' # (d @ enc ds)"
      by simp
    then have "length c = length d" and "c @ enc cs = d @ enc ds" using prefix_unique by blast+
    then have "c = d" and "enc cs = enc ds" by (simp_all add: append_eq_append_conv)
    with Cons.IH Cons show ?thesis by simp
  qed
qed

end

text \<open>Decimal rendering, most significant digit first, no leading zeros.\<close>

function digits :: "nat \<Rightarrow> nat list" where
  "digits n = (if n < 10 then [n] else digits (n div 10) @ [n mod 10])"
  by pat_completeness auto
termination by (relation "measure id") auto

declare digits.simps [simp del]

lemma digits_nonempty: "digits n \<noteq> []"
  by (subst digits.simps) auto

lemma digits_small: "n < 10 \<Longrightarrow> digits n = [n]"
  by (subst digits.simps) simp

lemma digits_large: "\<not> n < 10 \<Longrightarrow> digits n = digits (n div 10) @ [n mod 10]"
  by (subst digits.simps) simp

lemma digits_bound: "d \<in> set (digits n) \<Longrightarrow> d < 10"
proof (induction n rule: digits.induct)
  case (1 n)
  then show ?case by (cases "n < 10") (auto simp: digits_small digits_large)
qed

lemma digits_length_large: "\<not> n < 10 \<Longrightarrow> 2 \<le> length (digits n)"
  using digits_nonempty[of "n div 10"] by (simp add: digits_large Suc_le_eq)

theorem digits_injective: "digits n = digits m \<Longrightarrow> n = m"
proof (induction n arbitrary: m rule: digits.induct)
  case (1 n)
  show ?case
  proof (cases "n < 10")
    case True
    show ?thesis
    proof (cases "m < 10")
      case True
      with \<open>n < 10\<close> "1.prems" show ?thesis by (simp add: digits_small)
    next
      case False
      have "digits m = [n]" using "1.prems" \<open>n < 10\<close> by (simp add: digits_small)
      then have "length (digits m) = 1" by simp
      with digits_length_large[OF False] show ?thesis by simp
    qed
  next
    case False
    show ?thesis
    proof (cases "m < 10")
      case True
      have "digits n = [m]" using "1.prems" True by (simp add: digits_small)
      then have "length (digits n) = 1" by simp
      with digits_length_large[OF \<open>\<not> n < 10\<close>] show ?thesis by simp
    next
      case False
      with \<open>\<not> n < 10\<close> "1.prems" have "digits (n div 10) = digits (m div 10)" and "n mod 10 = m mod 10"
        by (simp_all add: digits_large)
      then have "n div 10 = m div 10" using "1.IH" \<open>\<not> n < 10\<close> by simp
      with \<open>n mod 10 = m mod 10\<close> show ?thesis by (metis mult_div_mod_eq)
    qed
  qed
qed

definition decimal :: "nat \<Rightarrow> string" where
  "decimal n = map (\<lambda>d. char_of (48 + d)) (digits n)"

lemma decimal_injective: "decimal n = decimal m \<Longrightarrow> n = m"
proof -
  assume eq: "decimal n = decimal m"
  have inj: "inj_on (\<lambda>d :: nat. char_of (48 + d) :: char) {d. d < 10}"
  proof (rule inj_onI, goal_cases)
    case (1 a b)
    have "of_char (char_of (48 + a) :: char) = (of_char (char_of (48 + b) :: char) :: nat)"
      by (rule arg_cong[OF 1(3)])
    then show ?case using 1(1,2) by (simp add: of_char_of mod_less)
  qed
  have sub: "set (digits n) \<union> set (digits m) \<subseteq> {d. d < 10}" using digits_bound by auto
  have "map (\<lambda>d :: nat. char_of (48 + d) :: char) (digits n) = map (\<lambda>d :: nat. char_of (48 + d)) (digits m)"
    using eq by (simp add: decimal_def)
  then have "digits n = digits m"
    using inj_on_map_eq_map[OF inj_on_subset[OF inj sub]] by simp
  then show ?thesis by (rule digits_injective)
qed

lemma decimal_no_colon: "CHR '':'' \<notin> set (decimal n)"
proof
  assume "CHR '':'' \<in> set (decimal n)"
  then obtain d where d: "d \<in> set (digits n)" and eq: "char_of (48 + d) = CHR '':''"
    unfolding decimal_def by auto
  have "of_char (char_of (48 + d) :: char) = (48 + d) mod 256" by (simp add: of_char_of)
  with eq digits_bound[OF d] show False by simp
qed

interpretation decimal_prefix: length_prefix decimal
proof
  fix n m assume "decimal n = decimal m"
  then show "n = m" by (rule decimal_injective)
next
  fix n show "CHR '':'' \<notin> set (decimal n)" by (rule decimal_no_colon)
qed

text \<open>The specification's example, 2:v119:person-email-unique4:acme15:ada@example.org, is one
instance of a now proved general fact: the tuple's encoding is injective.\<close>

corollary tuple_encoding_injective: "decimal_prefix.enc xs = decimal_prefix.enc ys \<Longrightarrow> xs = ys"
  by (rule decimal_prefix.enc_injective)

section \<open>Percent-encoding, section 6.2\<close>

text \<open>Bytes are natural numbers below 256. RFC 3986's unreserved characters are kept, and every
other byte is written as a percent sign and two uppercase hex digits. Decoding inverts it, so the
encoding is injective, and a slash never appears in the output, so the components joined by
slashes can be told apart.\<close>

definition unreserved :: "nat \<Rightarrow> bool" where
  "unreserved b \<longleftrightarrow> (65 \<le> b \<and> b \<le> 90) \<or> (97 \<le> b \<and> b \<le> 122) \<or> (48 \<le> b \<and> b \<le> 57) \<or> b = 45 \<or> b = 46 \<or> b = 95 \<or> b = 126"

definition hexdigit :: "nat \<Rightarrow> nat" where
  "hexdigit d = (if d < 10 then 48 + d else 55 + d)"

definition hexval :: "nat \<Rightarrow> nat" where
  "hexval c = (if 65 \<le> c then c - 55 else c - 48)"

lemma hexval_hexdigit: "d < 16 \<Longrightarrow> hexval (hexdigit d) = d"
  by (auto simp: hexdigit_def hexval_def)

lemma hexdigit_not_percent: "d < 16 \<Longrightarrow> hexdigit d \<noteq> 37"
  by (auto simp: hexdigit_def)

lemma hexdigit_not_slash: "d < 16 \<Longrightarrow> hexdigit d \<noteq> 47"
  by (auto simp: hexdigit_def)

fun pct :: "nat list \<Rightarrow> nat list" where
  "pct [] = []"
| "pct (b # bs) = (if unreserved b then b # pct bs else 37 # hexdigit (b div 16) # hexdigit (b mod 16) # pct bs)"

fun dec :: "nat list \<Rightarrow> nat list" where
  "dec [] = []"
| "dec (c # rest) = (if c = 37 then (case rest of h # l # rest' \<Rightarrow> (hexval h * 16 + hexval l) # dec rest' | _ \<Rightarrow> [])
                     else c # dec rest)"

lemma unreserved_not_percent: "unreserved b \<Longrightarrow> b \<noteq> 37"
  by (auto simp: unreserved_def)

lemma unreserved_not_slash: "unreserved b \<Longrightarrow> b \<noteq> 47"
  by (auto simp: unreserved_def)

theorem dec_pct: "\<forall>b \<in> set bs. b < 256 \<Longrightarrow> dec (pct bs) = bs"
proof (induction bs)
  case Nil
  then show ?case by simp
next
  case (Cons b bs)
  have b: "b < 256" using Cons.prems by simp
  show ?case
  proof (cases "unreserved b")
    case True
    then show ?thesis using Cons unreserved_not_percent by simp
  next
    case False
    have "b div 16 < 16" and "b mod 16 < 16" using b by auto
    then have "hexval (hexdigit (b div 16)) * 16 + hexval (hexdigit (b mod 16)) = b"
      using hexval_hexdigit by (simp add: mult_div_mod_eq mult.commute)
    with False Cons show ?thesis by simp
  qed
qed

corollary pct_injective:
  "\<forall>b \<in> set bs. b < 256 \<Longrightarrow> \<forall>b \<in> set bs'. b < 256 \<Longrightarrow> pct bs = pct bs' \<Longrightarrow> bs = bs'"
  using dec_pct by metis

theorem pct_no_slash: "\<forall>b \<in> set bs. b < 256 \<Longrightarrow> 47 \<notin> set (pct bs)"
proof (induction bs)
  case Nil
  then show ?case by simp
next
  case (Cons b bs)
  have "b div 16 < 16" "b mod 16 < 16" using Cons.prems by auto
  then show ?case using Cons unreserved_not_slash hexdigit_not_slash by auto
qed

section \<open>Dot segments, section 6.2 step 2\<close>

text \<open>A natural key's components become path segments. RFC 3986 removes the segments "." and
"..", so without the DotSegment refusal two different keys mint one IRI, and a key can escape
its parent. The normaliser below is the specification's remove_dot_segments over segments. With
no dot segment present it is the identity, and so injective.\<close>

fun remove_dots :: "string list \<Rightarrow> string list \<Rightarrow> string list" where
  "remove_dots acc [] = rev acc"
| "remove_dots acc (s # ss) =
     (if s = ''.'' then remove_dots acc ss
      else if s = ''..'' then remove_dots (tl acc) ss
      else remove_dots (s # acc) ss)"

definition norm_path :: "string list \<Rightarrow> string list" where
  "norm_path = remove_dots []"

theorem dot_segment_collision: "norm_path [''a'', ''..'', ''b''] = norm_path [''b'']"
  by (simp add: norm_path_def)

theorem dot_segment_escape: "norm_path [''..'', ''b''] = norm_path [''b'']"
  by (simp add: norm_path_def)

theorem single_dot_vanishes: "norm_path [''a'', ''.'', ''b''] = norm_path [''a'', ''b'']"
  by (simp add: norm_path_def)

lemma remove_dots_identity:
  "(\<forall>s \<in> set ss. s \<noteq> ''.'' \<and> s \<noteq> ''..'') \<Longrightarrow> remove_dots acc ss = rev acc @ ss"
  by (induction ss arbitrary: acc) auto

theorem no_dot_segments_injective:
  assumes "\<forall>s \<in> set ss. s \<noteq> ''.'' \<and> s \<noteq> ''..''" and "\<forall>s \<in> set ss'. s \<noteq> ''.'' \<and> s \<noteq> ''..''"
    and "norm_path ss = norm_path ss'"
  shows "ss = ss'"
  using assms unfolding norm_path_def by (simp add: remove_dots_identity)

text \<open>Three dots, or a dot inside a value, are not dot segments and are kept.\<close>

lemma not_a_dot_segment: "norm_path [''...'', ''a.b''] = [''...'', ''a.b'']"
  by (simp add: norm_path_def)

section \<open>Fixed-width positions, section 6.5\<close>

text \<open>An epoch and a sequence are written left-padded with zeros to a declared width. Digit
strings of one width order lexicographically exactly as the numbers they denote, so an IRI that
embeds them sorts by position. A value with more digits than the width is refused with
PositionWidthOverflow, because the padded string would no longer read back as the value.\<close>

fun dp :: "nat \<Rightarrow> nat \<Rightarrow> nat list" where
  "dp 0 n = []"
| "dp (Suc w) n = (n div 10 ^ w) # dp w (n mod 10 ^ w)"

fun lexlt :: "nat list \<Rightarrow> nat list \<Rightarrow> bool" where
  "lexlt (a # as) (b # bs) = (a < b \<or> (a = b \<and> lexlt as bs))"
| "lexlt _ _ = False"

fun val :: "nat list \<Rightarrow> nat" where
  "val [] = 0"
| "val (d # ds) = d * 10 ^ length ds + val ds"

lemma dp_length: "length (dp w n) = w"
  by (induction w arbitrary: n) simp_all

lemma val_dp: "n < 10 ^ w \<Longrightarrow> val (dp w n) = n"
proof (induction w arbitrary: n)
  case 0
  then show ?case by simp
next
  case (Suc w)
  have "n mod 10 ^ w < 10 ^ w" by simp
  then have ih: "val (dp w (n mod 10 ^ w)) = n mod 10 ^ w" by (rule Suc.IH)
  have "val (dp (Suc w) n) = n div 10 ^ w * 10 ^ w + n mod 10 ^ w"
    unfolding dp.simps val.simps dp_length ih ..
  also have "... = n" by (metis mod_div_mult_eq add.commute)
  finally show ?case .
qed

text \<open>Width zero reads nothing back, and more generally a value that does not fit its width is
not what the padded digits denote. That is why PositionWidthOverflow is a refusal.\<close>

lemma width_zero_reads_nothing: "val (dp 0 n) = 0"
  by simp

lemma dp_digits_ok: "n < 10 ^ w \<Longrightarrow> \<forall>d \<in> set (dp w n). d < 10"
proof (induction w arbitrary: n)
  case 0
  then show ?case by simp
next
  case (Suc w)
  have hd: "n div 10 ^ w < 10" using Suc.prems by (simp add: less_mult_imp_div_less)
  have "n mod 10 ^ w < 10 ^ w" by simp
  from Suc.IH[OF this] hd show ?case by simp
qed

theorem overflow_breaks_readback:
  "0 < w \<Longrightarrow> \<not> n < 10 ^ w \<Longrightarrow> \<exists>d \<in> set (dp w n). \<not> d < 10"
proof -
  assume "0 < w" and big: "\<not> n < 10 ^ w"
  then obtain w' where w: "w = Suc w'" by (cases w) auto
  have "10 \<le> n div 10 ^ w'"
  proof -
    have "10 * 10 ^ w' \<le> n" using big w by simp
    then have "(10 * 10 ^ w') div 10 ^ w' \<le> n div 10 ^ w'" by (rule div_le_mono)
    then show ?thesis by simp
  qed
  then show ?thesis using w by simp
qed

lemma div_lt_imp_lt: "0 < P \<Longrightarrow> n div P < m div P \<Longrightarrow> n < (m :: nat)"
  by (meson div_le_mono leD not_le)

theorem padded_order_agrees:
  "n < 10 ^ w \<Longrightarrow> m < 10 ^ w \<Longrightarrow> lexlt (dp w n) (dp w m) \<longleftrightarrow> n < m"
proof (induction w arbitrary: n m)
  case 0
  then show ?case by simp
next
  case (Suc w)
  let ?P = "(10 :: nat) ^ w"
  have P: "0 < ?P" by simp
  have IH: "lexlt (dp w (n mod ?P)) (dp w (m mod ?P)) \<longleftrightarrow> n mod ?P < m mod ?P"
    using Suc.IH by simp
  have n_eq: "n = ?P * (n div ?P) + n mod ?P" and m_eq: "m = ?P * (m div ?P) + m mod ?P"
    by (simp_all add: mult_div_mod_eq)
  show ?case
  proof
    assume "lexlt (dp (Suc w) n) (dp (Suc w) m)"
    then have h: "n div ?P < m div ?P \<or> (n div ?P = m div ?P \<and> n mod ?P < m mod ?P)"
      using IH by simp
    show "n < m"
    proof (cases "n div ?P < m div ?P")
      case True
      then show "n < m" using div_lt_imp_lt[OF P] by blast
    next
      case False
      with h have eq: "n div ?P = m div ?P" and lt: "n mod ?P < m mod ?P" by simp_all
      have "n = ?P * (m div ?P) + n mod ?P" using n_eq eq by simp
      with m_eq lt show "n < m" by linarith
    qed
  next
    assume "n < m"
    then have le: "n div ?P \<le> m div ?P" by (simp add: div_le_mono)
    show "lexlt (dp (Suc w) n) (dp (Suc w) m)"
    proof (cases "n div ?P = m div ?P")
      case True
      have "n = ?P * (m div ?P) + n mod ?P" using n_eq True by simp
      with m_eq \<open>n < m\<close> have "n mod ?P < m mod ?P" by linarith
      then show ?thesis using True IH by simp
    next
      case False
      with le have "n div ?P < m div ?P" by simp
      then show ?thesis by simp
    qed
  qed
qed

corollary padded_injective:
  "n < 10 ^ w \<Longrightarrow> m < 10 ^ w \<Longrightarrow> dp w n = dp w m \<Longrightarrow> n = m"
  by (metis val_dp)

text \<open>The specification's own motivating case: unpadded, 10 sorts before 3. Padded to two
digits, 03 sorts before 10.\<close>

lemma dp_two: "dp 2 n = [n div 10, n mod 10]"
  by (simp add: numeral_2_eq_2)

lemma unpadded_misorders: "lexlt (dp 2 10) (dp 2 3) = False \<and> lexlt (dp 2 3) (dp 2 10) = True"
  by (simp add: dp_two)

section \<open>Null scope and empty scope, section 6\<close>

text \<open>A claim tuple writes an absent scope as the empty string. An empty scope value would then
mint like no scope, so it is refused with EmptyScope, and on the admitted inputs the scope
component is injective.\<close>

definition scope_component :: "string option \<Rightarrow> string" where
  "scope_component s = (case s of None \<Rightarrow> '''' | Some x \<Rightarrow> x)"

definition admitted :: "string option \<Rightarrow> bool" where
  "admitted s \<longleftrightarrow> (case s of None \<Rightarrow> True | Some x \<Rightarrow> x \<noteq> '''')"

lemma scope_hazard: "scope_component None = scope_component (Some '''')"
  by (simp add: scope_component_def)

theorem scope_injective_on_admitted:
  "admitted s \<Longrightarrow> admitted s' \<Longrightarrow> scope_component s = scope_component s' \<Longrightarrow> s = s'"
  by (auto simp: scope_component_def admitted_def split: option.splits)

end
