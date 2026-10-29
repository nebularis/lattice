(* A concept condition's decision when its contract may resolve to no scheme at the resolution time (L9, L12),
   hand-written on top of Hierarchy. Only hierarchical match and a condition with exclusions only read the bound
   scheme. With no scheme, either is Undetermined for every candidate, and that is the only answer no scheme that
   could have resolved contradicts (TR4). A condition with a required concept and no hierarchy reads no scheme,
   so it decides without one as it does under any scheme holding the candidate (TR3). *)

theory Resolution
imports Hierarchy KernelLaws
begin

definition flat_decide :: "'a set \<Rightarrow> 'a set \<Rightarrow> 'a set \<Rightarrow> 'a \<Rightarrow> decision" where
  "flat_decide M req exc x =
     (if x \<notin> M then Undetermined
      else if x \<in> exc then Denied
      else if req \<noteq> {} \<and> x \<notin> req then Denied
      else Permitted)"

definition unscoped_decide :: "'a set \<Rightarrow> 'a set \<Rightarrow> 'a \<Rightarrow> decision" where
  "unscoped_decide req exc x = (if x \<in> exc then Denied else if x \<in> req then Permitted else Denied)"

definition decide_resolved :: "bool \<Rightarrow> ('a set \<times> ('a \<times> 'a) set) option \<Rightarrow> 'a set \<Rightarrow> 'a set \<Rightarrow> 'a \<Rightarrow> decision" where
  "decide_resolved h s req exc x =
     (case s of
        None \<Rightarrow> (if h \<or> req = {} then Undetermined else unscoped_decide req exc x)
      | Some (M, R) \<Rightarrow> (if h then hier_decide M R req exc x else flat_decide M req exc x))"

(* GATE:BEGIN TR1 *)
lemma no_scheme_undetermined:
  "h \<or> req = {} \<Longrightarrow> decide_resolved h None req exc x = Undetermined"
(* GATE:END *)
  by (simp add: decide_resolved_def)

(* GATE:BEGIN TR2 *)
lemma no_scheme_is_sound:
  "h \<or> req = {} \<Longrightarrow> decision_leq (decide_resolved h None req exc x) (decide_resolved h s req exc x)"
(* GATE:END *)
  by (simp add: decide_resolved_def decision_leq_def)

(* GATE:BEGIN TR3 *)
lemma required_reads_no_scheme:
  "\<lbrakk> \<not> h; req \<noteq> {}; x \<in> M \<rbrakk> \<Longrightarrow> decide_resolved h None req exc x = decide_resolved h (Some (M, R)) req exc x"
(* GATE:END *)
  by (simp add: decide_resolved_def unscoped_decide_def flat_decide_def)

(* GATE:BEGIN TR4 *)
lemma undetermined_is_the_only_answer_every_scheme_allows:
  "(\<forall>s. decision_leq d (decide_resolved h (Some s) req exc x)) \<Longrightarrow> d = Undetermined"
(* GATE:END *)
proof -
  assume all: "\<forall>s. decision_leq d (decide_resolved h (Some s) req exc x)"
  have "decide_resolved h (Some ({}, {})) req exc x = Undetermined"
    by (simp add: decide_resolved_def hier_decide_def flat_decide_def)
  with all show "d = Undetermined"
    by (metis decision_leq_def)
qed

end
