(* SPDX-License-Identifier: MPL-2.0 *)

(* Foundation: supersession chains, keys, and meaning-bearing edges.
   Source: ontology/foundation/README.md sections 4, 6, 7 and 8, and ADR-A137.
   A spike, not yet aligned to the formal-methods track. *)

theory Foundation
imports Main
begin

section \<open>Supersession chains\<close>

text \<open>A versioned thing is modelled by its versions. Each version has exactly one persistent
identity (fnd:hasIdentity, cardinality 1), and direct succession (fnd:supersededBy) stays within
one identity and has no cycle (fnd:SupersessionAcyclicShape). The README states asymmetry and
irreflexivity as OWL characteristics and acyclicity as a shape. Here acyclicity is the one
assumption, and the other two are derived from it.\<close>

locale version_chain =
  fixes versions :: "'v set"
    and identity_of :: "'v \<Rightarrow> 'i"
    and superseded_by :: "'v \<Rightarrow> 'v \<Rightarrow> bool"
  assumes finite_versions: "finite versions"
    and closed: "superseded_by a b \<Longrightarrow> a \<in> versions \<and> b \<in> versions"
    and same_identity: "superseded_by a b \<Longrightarrow> identity_of a = identity_of b"
    and acyclic: "acyclic {(a, b). superseded_by a b}"
begin

definition succ_rel :: "('v \<times> 'v) set" where
  "succ_rel = {(a, b). superseded_by a b}"

lemma succ_rel_finite: "finite succ_rel"
proof -
  have "succ_rel \<subseteq> versions \<times> versions"
    unfolding succ_rel_def using closed by auto
  then show ?thesis
    using finite_versions finite_subset by blast
qed

lemma irreflexive: "\<not> superseded_by a a"
proof
  assume "superseded_by a a"
  then have "(a, a) \<in> {(a, b). superseded_by a b}" by simp
  then have "(a, a) \<in> {(a, b). superseded_by a b}\<^sup>+" by (rule r_into_trancl)
  with acyclic show False by (simp add: acyclic_def)
qed

lemma asymmetric: "superseded_by a b \<Longrightarrow> \<not> superseded_by b a"
proof
  assume ab: "superseded_by a b" and ba: "superseded_by b a"
  let ?r = "{(a, b). superseded_by a b}"
  have "(a, b) \<in> ?r\<^sup>+" using ab by (auto intro: r_into_trancl)
  moreover have "(b, a) \<in> ?r\<^sup>+" using ba by (auto intro: r_into_trancl)
  ultimately have "(a, a) \<in> ?r\<^sup>+" by (rule trancl_trans)
  with acyclic show False by (simp add: acyclic_def)
qed

text \<open>Identity is preserved along a chain, however long.\<close>

lemma chain_same_identity: "(a, b) \<in> succ_rel\<^sup>* \<Longrightarrow> identity_of a = identity_of b"
  by (induction rule: rtrancl_induct) (auto simp: succ_rel_def same_identity)

text \<open>Following supersededBy from any version ends at a latest version, one with no successor.
The README says so in words ("following it ends at the latest version, the one with no
successor"). It holds because the chain is finite and acyclic.\<close>

lemma succ_wf: "wf (succ_rel\<inverse>)"
  using finite_acyclic_wf_converse[OF succ_rel_finite] acyclic
  unfolding succ_rel_def by simp

theorem reaches_latest:
  assumes "v \<in> versions"
  shows "\<exists>w. (v, w) \<in> succ_rel\<^sup>* \<and> (\<forall>u. \<not> superseded_by w u)"
proof -
  define S where "S = {w. (v, w) \<in> succ_rel\<^sup>*}"
  have "v \<in> S" by (simp add: S_def)
  then obtain z where zS: "z \<in> S" and zmin: "\<And>y. (y, z) \<in> succ_rel\<inverse> \<Longrightarrow> y \<notin> S"
    using succ_wf unfolding wf_eq_minimal by blast
  have "\<not> superseded_by z u" for u
  proof
    assume "superseded_by z u"
    then have zu: "(z, u) \<in> succ_rel" by (simp add: succ_rel_def)
    with zS have "u \<in> S" unfolding S_def by (auto intro: rtrancl_into_rtrancl)
    moreover from zu have "(u, z) \<in> succ_rel\<inverse>" by simp
    ultimately show False using zmin by blast
  qed
  with zS show ?thesis unfolding S_def by blast
qed

text \<open>The latest version is unique when succession is functional, which is how the README reads
it (one version "directly replaced" another). Without functionality a chain may fork, and then
each fork has its own latest version.\<close>

lemma last_stays: "(a, b) \<in> succ_rel\<^sup>* \<Longrightarrow> (\<forall>u. \<not> superseded_by a u) \<Longrightarrow> a = b"
proof (induction rule: rtrancl_induct)
  case base
  show ?case by simp
next
  case (step y z)
  have "a = y" using step.IH step.prems by simp
  with step.hyps(2) step.prems show ?case by (auto simp: succ_rel_def)
qed

lemma latest_unique_when_functional:
  assumes functional: "\<And>a b c. superseded_by a b \<Longrightarrow> superseded_by a c \<Longrightarrow> b = c"
    and w1: "(v, w) \<in> succ_rel\<^sup>*" and w1_last: "\<forall>u. \<not> superseded_by w u"
    and w2: "(v, w') \<in> succ_rel\<^sup>*" and w2_last: "\<forall>u. \<not> superseded_by w' u"
  shows "w = w'"
proof -
  have sv: "single_valued succ_rel"
    using functional unfolding single_valued_def succ_rel_def by auto
  from single_valued_confluent[OF sv w1 w2]
  have "(w, w') \<in> succ_rel\<^sup>* \<or> (w', w) \<in> succ_rel\<^sup>*" .
  then show ?thesis
    using last_stays[OF _ w1_last] last_stays[OF _ w2_last] by auto
qed

end

section \<open>Keys\<close>

text \<open>A key is a node with exactly one value and exactly one scheme, and its IRI is minted from
the two, so one value of one scheme is one node wherever it is recorded (README section 8.1).
The minting specification makes the function injective. The consequence is stated here.\<close>

record ('s, 'val) key =
  key_scheme :: 's
  key_value :: 'val

locale key_minting =
  fixes mint :: "('s, 'val) key \<Rightarrow> 'iri"
  assumes mint_inj: "inj mint"
begin

lemma one_node_per_value: "mint k1 = mint k2 \<Longrightarrow> key_scheme k1 = key_scheme k2 \<and> key_value k1 = key_value k2"
  using injD[OF mint_inj] by fastforce

end

text \<open>Keys belong to what persists (section 8.2). A version locates by every key of its identity
through the chain externalKey \<squnion> hasIdentity \<circ> externalKey. The chain infers only externalKey, so a
version never acquires a natural key of its own: natural keys stay exactly as asserted.\<close>

locale keyed_graph =
  fixes identity :: "'n \<Rightarrow> 'n option"
    and external_key :: "'n \<Rightarrow> 'k set"
    and natural_key :: "'n \<Rightarrow> 'k set"
  assumes natural_sub_external: "natural_key n \<subseteq> external_key n"
begin

definition external_key_entailed :: "'n \<Rightarrow> 'k set" where
  "external_key_entailed n = external_key n \<union> (case identity n of None \<Rightarrow> {} | Some i \<Rightarrow> external_key i)"

lemma version_locates_by_identity_keys:
  "identity v = Some i \<Longrightarrow> external_key i \<subseteq> external_key_entailed v"
  unfolding external_key_entailed_def by auto

lemma version_locates_by_identity_natural_keys:
  "identity v = Some i \<Longrightarrow> natural_key i \<subseteq> external_key_entailed v"
  using version_locates_by_identity_keys natural_sub_external by blast

lemma asserted_keys_kept: "external_key n \<subseteq> external_key_entailed n"
  unfolding external_key_entailed_def by auto

text \<open>The entailment is a fixpoint: applying the chain to an already entailed graph adds
nothing, because an identity has no identity of its own.\<close>

lemma entailment_idempotent:
  assumes "identity v = Some i" and "identity i = None"
  shows "external_key_entailed v \<union> (case identity v of None \<Rightarrow> {} | Some j \<Rightarrow> external_key_entailed j)
         = external_key_entailed v"
  using assms unfolding external_key_entailed_def by auto

end

section \<open>Meaning-bearing edges\<close>

text \<open>A judgement reproduced from a version reads the version's own content and the content of
the nodes at the ends of its meaning-bearing edges. Foundation section 4 and ADR-A137 say such an
edge must lead to a node that is versioned, content-addressed or minted under the subject: a node
that is never rewritten. The theorem is the reason for the rule. If the version and every target
are immutable, the judgement is the same in every store state. The counterexample after it shows
one mutable target rewriting a past judgement.\<close>

definition judgement :: "('t \<Rightarrow> 'n \<Rightarrow> 'c) \<Rightarrow> ('c \<Rightarrow> ('n \<Rightarrow> 'c option) \<Rightarrow> 'j) \<Rightarrow> ('n \<Rightarrow> 'n set) \<Rightarrow> 't \<Rightarrow> 'n \<Rightarrow> 'j" where
  "judgement content f targets t v =
     f (content t v) (\<lambda>n. if n \<in> targets v then Some (content t n) else None)"

locale store =
  fixes content :: "'t \<Rightarrow> 'n \<Rightarrow> 'c"
    and immutable :: "'n set"
  assumes immutable_fixed: "n \<in> immutable \<Longrightarrow> content t n = content t' n"
begin

theorem reproducible:
  assumes "v \<in> immutable" and "targets v \<subseteq> immutable"
  shows "judgement content f targets t v = judgement content f targets t' v"
proof -
  have own: "content t v = content t' v"
    using assms(1) immutable_fixed by blast
  have eq: "\<And>n. n \<in> targets v \<Longrightarrow> content t n = content t' n"
    using assms(2) immutable_fixed by blast
  have "(\<lambda>n. if n \<in> targets v then Some (content t n) else None)
      = (\<lambda>n. if n \<in> targets v then Some (content t' n) else None)"
    by (rule ext) (auto simp: eq)
  with own show ?thesis unfolding judgement_def by simp
qed

end

text \<open>Node 0 is the version and never changes. Node 1 is a target held by identity, true in
state 0 and false in state 1. The judgement "the target is true" reads differently in the two
states, so the past judgement made from the version is no longer reproducible.\<close>

lemma mutable_target_rewrites_judgement:
  fixes content :: "nat \<Rightarrow> nat \<Rightarrow> bool"
  defines "content \<equiv> \<lambda>t n. n = 1 \<and> t = 0"
  shows "judgement content (\<lambda>_ m. m 1 = Some True) (\<lambda>_. {1}) 0 0
       \<noteq> judgement content (\<lambda>_ m. m 1 = Some True) (\<lambda>_. {1}) 1 0"
  unfolding judgement_def content_def by simp

end
