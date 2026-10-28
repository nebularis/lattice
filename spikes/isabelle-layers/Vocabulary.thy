(* SPDX-License-Identifier: MPL-2.0 *)

(* Vocabulary: scheme binding resolution, its precedence, conflicts, fallback and closures.
   Source: ontology/vocabulary/README.md sections 4, 5.1 and 7.2, ADR-A85, and the
   voc:BindingClosure of the ontology-remediation unit. A spike, not yet aligned to the formal-methods track. *)

theory Vocabulary
imports Temporal
begin

section \<open>Bindings and applicability\<close>

text \<open>A scheme binding names the scopes it applies within, a validity period and the scheme
edition it supplies. It is applicable in a context at a time when every scope it names holds
in that context and the time falls within its validity. A binding naming no scope applies in
every context.\<close>

record ('sc, 'e) binding =
  scopes :: "'sc set"
  validity :: scope
  scheme :: 'e

definition applicable :: "('sc, 'e) binding \<Rightarrow> 'sc set \<Rightarrow> instant \<Rightarrow> bool" where
  "applicable b ctx t \<longleftrightarrow> scopes b \<subseteq> ctx \<and> within t (validity b)"

definition candidates :: "('sc, 'e) binding set \<Rightarrow> 'sc set \<Rightarrow> instant \<Rightarrow> ('sc, 'e) binding set" where
  "candidates B ctx t = {b \<in> B. applicable b ctx t}"

section \<open>Precedence\<close>

text \<open>Among applicable bindings a binding whose scopes are a strict superset of another's takes
precedence. What remains after removing every dominated binding is the set of winners. One
winner resolves. More than one is a conflict, a governance error, never a silent choice. None
falls back to the contract's boundScheme where there is one.\<close>

definition dominated :: "('sc, 'e) binding set \<Rightarrow> ('sc, 'e) binding \<Rightarrow> bool" where
  "dominated C b \<longleftrightarrow> (\<exists>b' \<in> C. scopes b \<subset> scopes b')"

definition winners :: "('sc, 'e) binding set \<Rightarrow> ('sc, 'e) binding set" where
  "winners C = {b \<in> C. \<not> dominated C b}"

datatype ('sc, 'e) resolution =
  Resolved "('sc, 'e) binding" | Fallback 'e | Conflict | Unbound

definition resolve :: "('sc, 'e) binding set \<Rightarrow> 'sc set \<Rightarrow> instant \<Rightarrow> 'e option \<Rightarrow> ('sc, 'e) resolution" where
  "resolve B ctx t fb =
     (if candidates B ctx t = {} then (case fb of None \<Rightarrow> Unbound | Some e \<Rightarrow> Fallback e)
      else if \<exists>w. winners (candidates B ctx t) = {w}
      then Resolved (THE w. winners (candidates B ctx t) = {w})
      else Conflict)"

definition resolved_scheme :: "('sc, 'e) resolution \<Rightarrow> 'e option" where
  "resolved_scheme r = (case r of Resolved b \<Rightarrow> Some (scheme b) | Fallback e \<Rightarrow> Some e | _ \<Rightarrow> None)"

text \<open>Resolution is local: it depends on the applicable bindings only, so a binding that does
not apply in a context, or at a time, can never change the answer there.\<close>

theorem locality:
  "candidates B ctx t = candidates B' ctx t \<Longrightarrow> resolve B ctx t fb = resolve B' ctx t fb"
  unfolding resolve_def by simp

lemma winners_subset: "winners C \<subseteq> C"
  unfolding winners_def by auto

lemma resolved_is_winner:
  assumes "resolve B ctx t fb = Resolved w"
  shows "winners (candidates B ctx t) = {w}"
proof -
  from assms obtain w' where w': "winners (candidates B ctx t) = {w'}"
    unfolding resolve_def by (auto split: if_splits option.splits)
  have "(THE w. winners (candidates B ctx t) = {w}) = w'"
  proof (rule the_equality)
    show "winners (candidates B ctx t) = {w'}" by (rule w')
    show "\<And>x. winners (candidates B ctx t) = {x} \<Longrightarrow> x = w'" using w' by auto
  qed
  with assms w' show ?thesis
    unfolding resolve_def by (auto split: if_splits option.splits)
qed

lemma resolve_single_winner:
  assumes "winners (candidates B ctx t) = {w}"
  shows "resolve B ctx t fb = Resolved w"
proof -
  have "(THE w'. winners (candidates B ctx t) = {w'}) = w"
  proof (rule the_equality)
    show "winners (candidates B ctx t) = {w}" by (rule assms)
    show "\<And>x. winners (candidates B ctx t) = {x} \<Longrightarrow> x = w" using assms by auto
  qed
  moreover have "candidates B ctx t \<noteq> {}"
    using assms winners_subset by fastforce
  ultimately show ?thesis using assms unfolding resolve_def by auto
qed

text \<open>Historical provenance (invariant 7): the binding a record was resolved under was valid at
the record's own resolution time, because only an applicable binding can win.\<close>

theorem resolved_applicable:
  "resolve B ctx t fb = Resolved w \<Longrightarrow> w \<in> B \<and> applicable w ctx t"
  using resolved_is_winner winners_subset unfolding candidates_def by fastforce

corollary resolved_valid_at_time:
  "resolve B ctx t fb = Resolved w \<Longrightarrow> within t (validity w)"
  using resolved_applicable unfolding applicable_def by blast

section \<open>Winner dominance\<close>

text \<open>The one winner's scopes include every applicable binding's scopes. In a finite set every
binding is dominated by, or is, a maximal one, and the winner is the only maximal one.\<close>

theorem winner_dominates:
  assumes fin: "finite B" and res: "resolve B ctx t fb = Resolved w"
  shows "\<forall>b \<in> candidates B ctx t. scopes b \<subseteq> scopes w"
proof
  fix b assume b: "b \<in> candidates B ctx t"
  let ?C = "candidates B ctx t"
  let ?U = "{b' \<in> ?C. scopes b \<subseteq> scopes b'}"
  have finC: "finite ?C" using fin unfolding candidates_def by simp
  have finU: "finite (scopes ` ?U)" using finC by simp
  have "b \<in> ?U" using b by simp
  then have neU: "scopes ` ?U \<noteq> {}" by blast
  obtain m where mU: "m \<in> scopes ` ?U" and mmax: "\<forall>s \<in> scopes ` ?U. m \<subseteq> s \<longrightarrow> m = s"
    using finite_has_maximal[OF finU neU] by blast
  from mU obtain b'' where b'': "b'' \<in> ?U" and m: "m = scopes b''" by blast
  have "\<not> dominated ?C b''"
  proof
    assume "dominated ?C b''"
    then obtain b3 where b3: "b3 \<in> ?C" and sub: "scopes b'' \<subset> scopes b3"
      unfolding dominated_def by blast
    have "scopes b \<subseteq> scopes b3" using b'' sub by auto
    then have "b3 \<in> ?U" using b3 by simp
    then have "scopes b3 \<in> scopes ` ?U" by blast
    with mmax m sub show False by blast
  qed
  then have "b'' \<in> winners ?C" using b'' unfolding winners_def by auto
  then have "b'' = w" using resolved_is_winner[OF res] by auto
  then show "scopes b \<subseteq> scopes w" using b'' by auto
qed

section \<open>Equal specificity is a conflict\<close>

text \<open>Two bindings for one contract that name exactly the same scopes and are both applicable
can never be told apart by precedence, so neither wins. This is what
voc:EqualSpecificityScopeConflictShape reports, and by overlaps_iff its two FILTERs are exactly
the condition under which such a moment exists.\<close>

theorem equal_specificity_never_wins:
  assumes "b1 \<noteq> b2" and "scopes b1 = scopes b2"
    and "b1 \<in> candidates B ctx t" and "b2 \<in> candidates B ctx t"
  shows "resolve B ctx t fb \<noteq> Resolved b1"
proof
  assume "resolve B ctx t fb = Resolved b1"
  then have win: "winners (candidates B ctx t) = {b1}" by (rule resolved_is_winner)
  with assms(1,4) have "b2 \<notin> winners (candidates B ctx t)" by auto
  with assms(4) obtain b3 where b3: "b3 \<in> candidates B ctx t" and "scopes b2 \<subset> scopes b3"
    unfolding winners_def dominated_def by auto
  then have "dominated (candidates B ctx t) b1"
    using assms(2) unfolding dominated_def by auto
  with win show False unfolding winners_def by auto
qed

theorem equal_specificity_shape:
  assumes "b1 \<in> B" and "b2 \<in> B" and "b1 \<noteq> b2" and "scopes b1 = scopes b2"
    and "overlaps (validity b1) (validity b2)"
  shows "\<exists>ctx t. resolve B ctx t fb \<notin> {Resolved b1, Resolved b2}"
proof -
  from assms(5) obtain t where t: "within t (validity b1)" "within t (validity b2)"
    unfolding overlaps_def by blast
  let ?ctx = "scopes b1"
  have c1: "b1 \<in> candidates B ?ctx t" and c2: "b2 \<in> candidates B ?ctx t"
    using assms t unfolding candidates_def applicable_def by auto
  have "resolve B ?ctx t fb \<noteq> Resolved b1"
    using equal_specificity_never_wins[OF assms(3) assms(4) c1 c2] .
  moreover have "resolve B ?ctx t fb \<noteq> Resolved b2"
    using equal_specificity_never_wins[OF assms(3)[symmetric] assms(4)[symmetric] c2 c1] .
  ultimately show ?thesis by blast
qed

section \<open>Fallback agreement\<close>

text \<open>A binding naming no scope is the time-bounded counterpart of boundScheme, and where both
exist for one contract they must name the same scheme (invariant 6, voc:FallbackAgreementShape).
The invariant makes the resolved scheme the same on both sides of the binding's validity when
nothing else applies: within it the binding wins, outside it the fallback is used, and the
scheme is one and the same.\<close>

definition fallback_agreement :: "('sc, 'e) binding set \<Rightarrow> 'e option \<Rightarrow> bool" where
  "fallback_agreement B fb \<longleftrightarrow> (\<forall>b \<in> B. scopes b = {} \<longrightarrow> (case fb of None \<Rightarrow> True | Some e \<Rightarrow> scheme b = e))"

theorem fallback_agrees:
  assumes "fallback_agreement B (Some e)"
    and "b0 \<in> B" and "scopes b0 = {}"
    and "candidates B ctx t \<subseteq> {b0}"
  shows "resolved_scheme (resolve B ctx t (Some e)) = Some e"
proof (cases "candidates B ctx t = {}")
  case True
  then show ?thesis unfolding resolve_def resolved_scheme_def by simp
next
  case False
  with assms(4) have C: "candidates B ctx t = {b0}" by auto
  then have "winners (candidates B ctx t) = {b0}"
    unfolding winners_def dominated_def by auto
  then have "resolve B ctx t (Some e) = Resolved b0"
    by (rule resolve_single_winner)
  moreover have "scheme b0 = e"
    using assms(1,2,3) unfolding fallback_agreement_def by auto
  ultimately show ?thesis unfolding resolved_scheme_def by simp
qed

section \<open>Closures\<close>

text \<open>A binding ends by a closure record rather than by a mutable end date (ADR-A137, applied to
voc:SchemeBinding). Where several closures exist the earliest ends it. Closing never extends a
binding's validity, and a closed binding is not valid at the instant of its earliest closure.\<close>

definition stated_end :: "('sc, 'e) binding \<Rightarrow> instant set" where
  "stated_end b = {e. valid_to (validity b) = Some e}"

lemma stated_end_finite: "finite (stated_end b)"
  unfolding stated_end_def by (cases "valid_to (validity b)") auto

definition effective_validity :: "('sc, 'e) binding \<Rightarrow> instant set \<Rightarrow> scope" where
  "effective_validity b C =
     \<lparr> valid_from = valid_from (validity b),
       valid_to = (if C \<union> stated_end b = {} then None else Some (Min (C \<union> stated_end b))) \<rparr>"

lemma effective_validity_no_closure: "effective_validity b {} = validity b"
proof (cases "valid_to (validity b)")
  case None
  then show ?thesis unfolding effective_validity_def stated_end_def by simp
next
  case (Some e)
  then show ?thesis unfolding effective_validity_def stated_end_def by simp
qed

theorem closing_never_extends:
  assumes "finite C" and "within t (effective_validity b (insert c C))"
  shows "within t (effective_validity b C)"
proof -
  have finC: "finite (C \<union> stated_end b)" using assms(1) stated_end_finite by simp
  show ?thesis
  proof (cases "C \<union> stated_end b = {}")
    case True
    then show ?thesis using assms(2) unfolding effective_validity_def within_def by auto
  next
    case False
    let ?S = "C \<union> stated_end b"
    have "Min ?S \<in> insert c ?S" using Min_in[OF finC False] by simp
    then have le: "Min (insert c ?S) \<le> Min ?S" using finC by (simp add: Min_le)
    have eq: "insert c C \<union> stated_end b = insert c ?S" by auto
    from assms(2) have "valid_from (validity b) \<le> t \<and> t < Min (insert c ?S)"
      unfolding effective_validity_def within_def eq by simp
    with le False show ?thesis
      unfolding effective_validity_def within_def by auto
  qed
qed

theorem earliest_closure_ends:
  assumes "finite C" and "c \<in> C"
  shows "\<not> within c (effective_validity b C)"
proof -
  have finC: "finite (C \<union> stated_end b)" using assms(1) stated_end_finite by simp
  have "Min (C \<union> stated_end b) \<le> c" using assms(2) finC by (simp add: Min_le)
  moreover have "C \<union> stated_end b \<noteq> {}" using assms(2) by auto
  ultimately show ?thesis unfolding effective_validity_def within_def by auto
qed

end
