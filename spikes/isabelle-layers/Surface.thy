(* SPDX-License-Identifier: MPL-2.0 *)

(* Surface: minted names and their collisions, staleness by read set, closure relations,
   materialisation idempotence and conservativity over a signature.
   Source: ontology/surface/README.md sections 8, 9 (laws X1, X3, R1, R4, R5, S6) and 11.
   A spike, not yet aligned to the formal-methods track. *)

theory Surface
imports Main
begin

section \<open>Naming, section 8\<close>

text \<open>A nominal class for a value is named from the family class and the value's local name,
the fragment after the hash or after the final slash. Injectivity is not assumed: two values in
different namespaces with one local name collide, which is a hard failure, and DigestLocalName
is the escape hatch, injective for any population given an injective digest.\<close>

definition local_name :: "string \<Rightarrow> string" where
  "local_name iri =
     (if CHR ''#'' \<in> set iri then rev (takeWhile (\<lambda>c. c \<noteq> CHR ''#'') (rev iri))
      else rev (takeWhile (\<lambda>c. c \<noteq> CHR ''/'') (rev iri)))"

lemma local_name_fragment: "local_name ''http://a#x'' = ''x''"
  by (simp add: local_name_def)

lemma local_name_last_segment: "local_name ''http://a/b/y'' = ''y''"
  by (simp add: local_name_def)

definition mint_nominal_local :: "string \<Rightarrow> string \<Rightarrow> string" where
  "mint_nominal_local family v = family @ ''_'' @ local_name v"

theorem local_name_policy_collides:
  "mint_nominal_local fam ''http://a#x'' = mint_nominal_local fam ''http://b#x'' \<and> ''http://a#x'' \<noteq> ''http://b#x''"
  by (simp add: mint_nominal_local_def local_name_def)

locale digest_naming =
  fixes digest :: "string \<Rightarrow> string"
  assumes digest_inj: "digest v = digest v' \<Longrightarrow> v = v'"
begin

definition mint_nominal_digest :: "string \<Rightarrow> string \<Rightarrow> string" where
  "mint_nominal_digest family v = family @ ''_'' @ digest v"

theorem digest_policy_injective:
  "mint_nominal_digest fam v = mint_nominal_digest fam v' \<Longrightarrow> v = v'"
  unfolding mint_nominal_digest_def by (simp add: digest_inj)

end

text \<open>Qualified local names separate namespaces that the bare local name conflates, as long as
the prefix is a function of the namespace.\<close>

definition mint_nominal_qualified :: "string \<Rightarrow> string \<Rightarrow> string \<Rightarrow> string" where
  "mint_nominal_qualified family prefix v = family @ ''_'' @ prefix @ ''_'' @ local_name v"

lemma qualified_separates:
  "mint_nominal_qualified fam ''a'' ''http://a#x'' \<noteq> mint_nominal_qualified fam ''b'' ''http://b#x''"
  by (simp add: mint_nominal_qualified_def local_name_def)

section \<open>Staleness by read set, section 11\<close>

text \<open>A generation run records what it read: each entry names one input and the hash of its
canonical content when read. A surface is stale exactly when any entry's current hash differs
from the recorded one. That is the whole rule, and no classification of changes is needed to
decide it.\<close>

record entry =
  input :: nat
  recorded :: nat

definition stale :: "entry set \<Rightarrow> (nat \<Rightarrow> nat) \<Rightarrow> bool" where
  "stale readset current \<longleftrightarrow> (\<exists>e \<in> readset. current (input e) \<noteq> recorded e)"

lemma fresh_when_unchanged: "(\<forall>e \<in> readset. current (input e) = recorded e) \<Longrightarrow> \<not> stale readset current"
  by (simp add: stale_def)

lemma stale_when_any_changed: "e \<in> readset \<Longrightarrow> current (input e) \<noteq> recorded e \<Longrightarrow> stale readset current"
  by (auto simp: stale_def)

lemma unread_inputs_irrelevant:
  assumes "\<forall>e \<in> readset. current (input e) = current' (input e)"
  shows "stale readset current \<longleftrightarrow> stale readset current'"
  using assms by (auto simp: stale_def)

text \<open>Reuse of a surface needs both a matching semantic content hash and a matching profile
identity. An artefact hash that changes while both hold is a generator defect, not a source
change.\<close>

record surface =
  semantic_hash :: nat
  profile :: nat
  artefact_hash :: nat

definition reusable :: "surface \<Rightarrow> surface \<Rightarrow> bool" where
  "reusable old new \<longleftrightarrow> semantic_hash old = semantic_hash new \<and> profile old = profile new"

definition generator_defect :: "surface \<Rightarrow> surface \<Rightarrow> bool" where
  "generator_defect old new \<longleftrightarrow> reusable old new \<and> artefact_hash old \<noteq> artefact_hash new"

lemma defect_is_not_a_source_change:
  "generator_defect old new \<Longrightarrow> semantic_hash old = semantic_hash new"
  by (simp add: generator_defect_def reusable_def)

section \<open>Materialisation, law R4\<close>

text \<open>Re-running a materialisation over an unchanged read set adds no triples.\<close>

definition materialise :: "'t set \<Rightarrow> 't set \<Rightarrow> 't set" where
  "materialise graph generated = graph \<union> generated"

theorem r4_idempotent: "materialise (materialise g s) s = materialise g s"
  by (auto simp: materialise_def)

section \<open>Closure relations, laws X3 and R5\<close>

text \<open>A generated closure relation holds between a carrier instance and a value exactly when
the read path relates the instance to some value standing in the reflexive-transitive closure of
the declared basis, restricted to the declared scope.\<close>

definition closure_rel :: "('i \<times> 'v) set \<Rightarrow> ('v \<times> 'v) set \<Rightarrow> 'v set \<Rightarrow> ('i \<times> 'v) set" where
  "closure_rel readpath basis scope = {(i, v). \<exists>v0. (i, v0) \<in> readpath \<and> (v0, v) \<in> (basis \<inter> scope \<times> scope)\<^sup>*}"

lemma closure_reflexive: "(i, v) \<in> readpath \<Longrightarrow> (i, v) \<in> closure_rel readpath basis scope"
  unfolding closure_rel_def by auto

lemma closure_step:
  "(i, v) \<in> closure_rel readpath basis scope \<Longrightarrow> (v, v') \<in> basis \<Longrightarrow> v \<in> scope \<Longrightarrow> v' \<in> scope \<Longrightarrow>
   (i, v') \<in> closure_rel readpath basis scope"
  unfolding closure_rel_def by (auto intro: rtrancl_into_rtrancl)

lemma closure_respects_scope:
  "(i, v) \<in> closure_rel readpath basis scope \<Longrightarrow> (i, v) \<in> readpath \<or> v \<in> scope"
  unfolding closure_rel_def by (auto elim: rtranclE)

text \<open>Law R5: the basis is acyclic over the scope, so the traversal that establishes it
terminates. Finite and acyclic gives well-foundedness of the reverse, which is the absence of
an infinite ascending chain.\<close>

theorem r5_traversal_terminates:
  assumes "finite basis" and "acyclic (basis \<inter> scope \<times> scope)"
  shows "\<not> (\<exists>f. \<forall>i. (f i, f (Suc i)) \<in> basis \<inter> scope \<times> scope)"
proof -
  have "finite (basis \<inter> scope \<times> scope)" using assms(1) by simp
  then have "wf ((basis \<inter> scope \<times> scope)\<inverse>)" using finite_acyclic_wf_converse assms(2) by blast
  then show ?thesis unfolding wf_iff_no_infinite_down_chain by auto
qed

section \<open>Conservativity over a signature, law X1\<close>

text \<open>A local-signature surface asserts only about terms it minted itself. Over asserted
triples, adding such a surface changes nothing a question over the source signature can see:
the source-signature part of the graph is the same with and without it.\<close>

definition restrict :: "('t \<Rightarrow> 'sym set) \<Rightarrow> 'sym set \<Rightarrow> 't set \<Rightarrow> 't set" where
  "restrict symbols sigma graph = {t \<in> graph. symbols t \<subseteq> sigma}"

definition local_signature :: "('t \<Rightarrow> 'sym set) \<Rightarrow> 'sym set \<Rightarrow> 't set \<Rightarrow> bool" where
  "local_signature symbols sigma surface \<longleftrightarrow> (\<forall>t \<in> surface. \<not> symbols t \<subseteq> sigma)"

theorem x1_conservative:
  assumes "local_signature symbols sigma surface"
  shows "restrict symbols sigma (graph \<union> surface) = restrict symbols sigma graph"
  using assms unfolding restrict_def local_signature_def by auto

corollary x1_questions_agree:
  assumes "local_signature symbols sigma surface"
  shows "question (restrict symbols sigma (graph \<union> surface)) = question (restrict symbols sigma graph)"
  using x1_conservative[OF assms] by simp

text \<open>Composition: a stack of local-signature surfaces is local-signature, so conservativity
composes.\<close>

lemma local_signature_union:
  "local_signature symbols sigma s1 \<Longrightarrow> local_signature symbols sigma s2 \<Longrightarrow> local_signature symbols sigma (s1 \<union> s2)"
  by (auto simp: local_signature_def)

end
