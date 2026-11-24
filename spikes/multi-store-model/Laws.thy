(* SPDX-License-Identifier: MPL-2.0 *)

(* The laws of exec and of the four commands. Each law the README states is a theorem between
   GATE markers, with a claim record under claims/. *)

theory Laws
  imports Commands
begin

section \<open>The state, one resource at a time\<close>

lemma map_of_filter_key: "map_of (filter (\<lambda>p. fst p \<noteq> k) xs) = (map_of xs)(k := None)"
  by (induct xs) (auto simp: fun_eq_iff)

lemma map_of_upd [simp]: "map_of (upd k v xs) = (map_of xs)(k \<mapsto> v)"
  by (simp add: upd_def map_of_filter_key)

lemma step_None: "step a eo = None \<Longrightarrow> eo = None"
  by (cases a) (auto split: option.splits)

lemma step_Some: "\<not> is_retract a \<Longrightarrow> step a eo \<noteq> None"
  by (cases a) auto

text \<open>An action changes the entry of its own resource and no other.\<close>

lemma map_of_apply_act:
  "map_of (apply_act a s) k = (if k = act_res a then step a (map_of s k) else map_of s k)"
  using step_None[of a "map_of s (act_res a)"] by (auto simp: apply_act_def split: option.split)

lemma map_of_fold:
  "map_of (fold apply_act as s) k = fold step (filter (\<lambda>a. act_res a = k) as) (map_of s k)"
  by (induct as arbitrary: s) (auto simp: map_of_apply_act)

lemma map_of_run:
  "map_of (run as s) k =
     fold step (filter (\<lambda>a. \<not> is_retract a \<and> act_res a = k) as)
       (fold step (filter (\<lambda>a. is_retract a \<and> act_res a = k) as) (map_of s k))"
  by (simp add: run_def map_of_fold)

lemma map_of_filter_notin:
  "map_of (filter (\<lambda>p. fst p \<notin> A) xs) f = (if f \<in> A then None else map_of xs f)"
  by (induct xs) auto

lemma map_of_merge_flds:
  "map_of (merge_flds old new) f = (case map_of new f of Some v \<Rightarrow> Some v | None \<Rightarrow> map_of old f)"
proof (cases "map_of new f")
  case None
  then have "f \<notin> fst ` set new" by (simp add: map_of_eq_None_iff)
  then show ?thesis using None by (simp add: merge_flds_def map_add_def map_of_filter_notin)
next
  case (Some v)
  then show ?thesis by (simp add: merge_flds_def map_add_def)
qed

lemma mem_concretised:
  "a \<in> set (map (concretise s t ps) effs) \<Longrightarrow> \<exists>e \<in> set effs. a = concretise s t ps e"
  by auto


section \<open>The guards\<close>

lemma first_fail_None:
  "first_fail s t ps gs = None \<longleftrightarrow> (\<forall>(g, out) \<in> set gs. holds s t ps g)"
  by (induct s t ps gs rule: first_fail.induct) auto

lemma first_fail_SomeD:
  "first_fail s t ps gs = Some out \<Longrightarrow>
     \<exists>xs g ys. gs = xs @ (g, out) # ys \<and> (\<forall>(g', o') \<in> set xs. holds s t ps g') \<and> \<not> holds s t ps g"
proof (induct s t ps gs rule: first_fail.induct)
  case (1 s t ps)
  then show ?case by simp
next
  case (2 s t ps g out' gs)
  show ?case
  proof (cases "holds s t ps g")
    case True
    then have "first_fail s t ps gs = Some out" using "2.prems" by simp
    then obtain xs g'' ys where "gs = xs @ (g'', out) # ys" "\<forall>(g', o') \<in> set xs. holds s t ps g'"
        "\<not> holds s t ps g''"
      using "2.hyps" True by blast
    then show ?thesis using True by (intro exI[of _ "(g, out') # xs"] exI[of _ g''] exI[of _ ys]) auto
  next
    case False
    then have "out' = out" using "2.prems" by simp
    then show ?thesis using False by (intro exI[of _ "[]"] exI[of _ g] exI[of _ gs]) auto
  qed
qed

lemma first_fail_mem: "first_fail s t ps gs = Some out \<Longrightarrow> \<exists>g. (g, out) \<in> set gs"
  by (drule first_fail_SomeD) auto

definition well_formed :: "'a command \<Rightarrow> bool" where
  "well_formed c \<longleftrightarrow> (\<forall>(g, out) \<in> set (guards c). out \<noteq> Applied)"

lemma exec_applied:
  assumes "well_formed c" "exec s t ps c = (s', Applied)"
  shows "first_fail s t ps (guards c) = None" and "s' = run (map (concretise s t ps) (effects c)) s"
proof -
  show ff: "first_fail s t ps (guards c) = None"
  proof (cases "first_fail s t ps (guards c)")
    case (Some out)
    then have "out = Applied" using assms(2) by (simp add: exec_def)
    then show ?thesis using Some first_fail_mem[OF Some] assms(1) by (auto simp: well_formed_def)
  qed
  show "s' = run (map (concretise s t ps) (effects c)) s" using assms(2) ff by (simp add: exec_def)
qed

lemma commands_are_well_formed:
  "well_formed create_if_absent" "well_formed delta_replace" "well_formed append_event"
  "well_formed (key_claim_write k)"
  by (simp_all add: well_formed_def create_if_absent_def delta_replace_def append_event_def key_claim_write_def)


section \<open>Outcomes\<close>

text \<open>Outcomes are total and disjoint. A well-formed command is applied exactly when every guard
  holds, and otherwise its outcome is the outcome of the first guard that fails.\<close>

(* GATE:BEGIN MM1 *)
theorem applied_exactly_when_every_guard_holds:
  assumes "well_formed c"
  shows "snd (exec s t ps c) = Applied \<longleftrightarrow> (\<forall>(g, out) \<in> set (guards c). holds s t ps g)"
proof (cases "first_fail s t ps (guards c)")
  case None
  then have "\<forall>(g, out) \<in> set (guards c). holds s t ps g" using first_fail_None[of s t ps "guards c"] by simp
  then show ?thesis using None by (simp add: exec_def)
next
  case (Some out)
  then have "out \<noteq> Applied" using first_fail_mem[OF Some] assms by (auto simp: well_formed_def)
  moreover have "\<not> (\<forall>(g, out) \<in> set (guards c). holds s t ps g)"
    using Some first_fail_None[of s t ps "guards c"] by auto
  ultimately show ?thesis using Some by (simp add: exec_def)
qed

theorem otherwise_the_first_failed_guard_decides:
  assumes "snd (exec s t ps c) \<noteq> Applied"
  shows "\<exists>xs g ys. guards c = xs @ (g, snd (exec s t ps c)) # ys
    \<and> (\<forall>(g', o') \<in> set xs. holds s t ps g') \<and> \<not> holds s t ps g"
proof (cases "first_fail s t ps (guards c)")
  case None
  then show ?thesis using assms by (simp add: exec_def)
next
  case (Some out)
  then show ?thesis using first_fail_SomeD[OF Some] by (simp add: exec_def)
qed
(* GATE:END *)

text \<open>A command that is not applied changes nothing.\<close>

(* GATE:BEGIN MM2 *)
theorem a_command_not_applied_changes_nothing:
  "snd (exec s t ps c) \<noteq> Applied \<Longrightarrow> fst (exec s t ps c) = s"
  by (auto simp: exec_def split: option.splits)
(* GATE:END *)

text \<open>Every value is read from the state before the command, so an effect never sees another
  effect's write.\<close>

(* GATE:BEGIN MM3 *)
theorem every_value_is_read_before_any_write:
  "well_formed c \<Longrightarrow> snd (exec s t ps c) = Applied \<Longrightarrow>
     fst (exec s t ps c) = run (map (concretise s t ps) (effects c)) s"
  using exec_applied[of c s t ps "fst (exec s t ps c)"] by (cases "exec s t ps c") auto
(* GATE:END *)


section \<open>Retract, then assert\<close>

fun keeps :: "'a act \<Rightarrow> bool" where
  "keeps (ASet _ _) = True"
| "keeps (AAssert _ _) = True"
| "keeps _ = False"

lemma step_keeps_fact:
  "keeps a \<Longrightarrow> x \<in> fcts (entry_or_empty eo) \<Longrightarrow> x \<in> fcts (entry_or_empty (step a eo))"
  by (cases a) (auto simp: entry_or_empty_def)

lemma fold_keeps_fact:
  "\<forall>a \<in> set as. keeps a \<Longrightarrow> x \<in> fcts (entry_or_empty eo) \<Longrightarrow> x \<in> fcts (entry_or_empty (fold step as eo))"
  by (induct as arbitrary: eo) (auto intro: step_keeps_fact)

lemma fold_asserts_fact:
  "\<forall>a \<in> set as. keeps a \<Longrightarrow> AAssert r F \<in> set as \<Longrightarrow> x \<in> F \<Longrightarrow>
     x \<in> fcts (entry_or_empty (fold step as eo))"
proof (induct as arbitrary: eo)
  case Nil
  then show ?case by simp
next
  case (Cons a as)
  show ?case
  proof (cases "a = AAssert r F")
    case True
    then have "x \<in> fcts (entry_or_empty (step a eo))" using Cons.prems(3) by (simp add: entry_or_empty_def)
    then show ?thesis using Cons.prems(1) fold_keeps_fact[of as x "step a eo"] by simp
  next
    case False
    then show ?thesis using Cons by simp
  qed
qed

text \<open>A fact a command asserts on a resource is present afterwards, whatever the command
  retracts from it, unless the command also puts that resource whole.\<close>

(* GATE:BEGIN MM4 *)
theorem an_asserted_fact_is_present_whatever_is_retracted:
  assumes wf: "well_formed c" and applied: "snd (exec s t ps c) = Applied"
    and asserted: "Assert r e \<in> set (effects c)" and x: "x \<in> facts_of (eval s t ps e)"
    and no_put: "\<forall>r' fs. Put r' fs \<in> set (effects c) \<longrightarrow> eval_r s t ps r' \<noteq> eval_r s t ps r"
    and no_put_facts: "\<forall>r' e'. PutFacts r' e' \<in> set (effects c) \<longrightarrow> eval_r s t ps r' \<noteq> eval_r s t ps r"
  shows "x \<in> fcts (entry_or_empty (map_of (fst (exec s t ps c)) (eval_r s t ps r)))"
proof -
  let ?K = "eval_r s t ps r"
  let ?as = "map (concretise s t ps) (effects c)"
  let ?late = "filter (\<lambda>a. \<not> is_retract a \<and> act_res a = ?K) ?as"
  have all_keep: "\<forall>a \<in> set ?late. keeps a"
  proof
    fix a assume "a \<in> set ?late"
    then have in_as: "a \<in> set ?as" and nr: "\<not> is_retract a" and at: "act_res a = ?K" by simp_all
    from in_as obtain e' where e': "e' \<in> set (effects c)" and a: "a = concretise s t ps e'" by auto
    show "keeps a"
    proof (cases e')
      case (Put r' fs)
      then have "eval_r s t ps r' = ?K" using a at by simp
      then show ?thesis using no_put e' Put by blast
    next
      case (PutFacts r' e'')
      then have "eval_r s t ps r' = ?K" using a at by simp
      then show ?thesis using no_put_facts e' PutFacts by blast
    next
      case (SetFields r' fs)
      then show ?thesis using a by simp
    next
      case (Retract r' e'')
      then show ?thesis using a nr by simp
    next
      case (Assert r' e'')
      then show ?thesis using a by simp
    next
      case (AppendRows r' e'')
      then show ?thesis using a by simp
    qed
  qed
  have "concretise s t ps (Assert r e) \<in> set ?as" using imageI[OF asserted, of "concretise s t ps"] by simp
  then have "AAssert ?K (facts_of (eval s t ps e)) \<in> set ?late" by simp
  then have "x \<in> fcts (entry_or_empty (fold step ?late
      (fold step (filter (\<lambda>a. is_retract a \<and> act_res a = ?K) ?as) (map_of s ?K))))"
    using fold_asserts_fact[OF all_keep _ x] by blast
  moreover have "fst (exec s t ps c) = run ?as s" by (rule every_value_is_read_before_any_write[OF wf applied])
  then have "map_of (fst (exec s t ps c)) ?K = fold step ?late
      (fold step (filter (\<lambda>a. is_retract a \<and> act_res a = ?K) ?as) (map_of s ?K))"
    by (simp only: map_of_run)
  ultimately show ?thesis by simp
qed
(* GATE:END *)


section \<open>A resend\<close>

lemma run_frame: "k \<notin> act_res ` set as \<Longrightarrow> map_of (run as s) k = map_of s k"
proof -
  assume k: "k \<notin> act_res ` set as"
  then have "filter (\<lambda>a. \<not> is_retract a \<and> act_res a = k) as = []"
    and "filter (\<lambda>a. is_retract a \<and> act_res a = k) as = []"
    by (auto simp: filter_empty_conv)
  then show ?thesis by (simp add: map_of_run)
qed

lemma txn_guard_first:
  "guards c = (Absent (Txn (Param TxnId)), Duplicate) # gs \<Longrightarrow> map_of s (KTxn (param ps TxnId)) \<noteq> None \<Longrightarrow>
     exec s t ps c = (s, Duplicate)"
  by (cases "map_of s (KTxn (param ps TxnId))") (simp_all add: exec_def)

lemma applied_writes_txn:
  assumes c: "c \<in> {create_if_absent, delta_replace}" and applied: "exec s t ps c = (s1, Applied)"
  shows "map_of s1 (KTxn (param ps TxnId)) \<noteq> None"
proof -
  have wf: "well_formed c" using c commands_are_well_formed by auto
  have s1: "s1 = run (map (concretise s t ps) (effects c)) s" using exec_applied(2)[OF wf applied] .
  show ?thesis using c unfolding s1 by (auto simp: map_of_run create_if_absent_def delta_replace_def)
qed

text \<open>A resend is answered before any conflict. Once a create or a delta replace is applied, any
  create or delta replace that names its transaction is answered as a duplicate and changes
  nothing, whatever else it names.\<close>

(* GATE:BEGIN MM5 *)
theorem a_resend_is_answered_duplicate_before_any_conflict:
  assumes "c \<in> {create_if_absent, delta_replace}" and "c' \<in> {create_if_absent, delta_replace}"
    and "exec s t ps c = (s1, Applied)" and "param ps' TxnId = param ps TxnId"
  shows "exec s1 t' ps' c' = (s1, Duplicate)"
proof -
  have "map_of s1 (KTxn (param ps' TxnId)) \<noteq> None" using applied_writes_txn[OF assms(1,3)] assms(4) by simp
  moreover have "\<exists>gs. guards c' = (Absent (Txn (Param TxnId)), Duplicate) # gs"
    using assms(2) by (auto simp: create_if_absent_def delta_replace_def)
  ultimately show ?thesis using txn_guard_first by blast
qed

theorem an_append_sent_again_is_answered_duplicate:
  assumes applied: "exec s t ps append_event = (s1, Applied)"
  shows "exec s1 t' ps append_event = (s1, Duplicate)"
proof -
  have wf: "well_formed (append_event :: 'a command)" by (rule commands_are_well_formed)
  have ff: "first_fail s t ps (guards append_event) = None" using exec_applied(1)[OF wf applied] .
  have s1: "s1 = run (map (concretise s t ps) (effects append_event)) s" using exec_applied(2)[OF wf applied] .
  have dep: "map_of s1 KDEpoch = map_of s KDEpoch" unfolding s1 by (simp add: map_of_run append_event_def)
  have txn: "map_of s1 (KTxn (param ps TxnId)) \<noteq> None" unfolding s1 by (simp add: map_of_run append_event_def)
  have "holds s t ps (FieldEq DEpoch Epoch (Param EpochP))" using ff by (simp add: append_event_def split: if_splits)
  then have "holds s1 t' ps (FieldEq DEpoch Epoch (Param EpochP))" using dep by (simp add: field_of_def)
  then show ?thesis using txn by (simp add: exec_def append_event_def)
qed

theorem a_claim_written_again_by_its_owner_changes_nothing:
  assumes applied: "exec s t ps (key_claim_write k) = (s1, Applied)"
  shows "snd (exec s1 t' ps (key_claim_write k)) = Applied"
    and "map_of (fst (exec s1 t' ps (key_claim_write k))) = map_of s1"
proof -
  let ?r = "KClaim (param ps ClaimP)" and ?e = "Entry [(Constraint, Atom k), (Owner, param ps OwnerP)] {}"
  have wf: "well_formed (key_claim_write k)" by (rule commands_are_well_formed)
  have s1: "s1 = upd ?r ?e s"
    using exec_applied(2)[OF wf applied] by (simp add: key_claim_write_def run_def apply_act_def)
  have held: "map_of s1 ?r = Some ?e" by (simp add: s1)
  then have "first_fail s1 t' ps (guards (key_claim_write k)) = None" by (simp add: key_claim_write_def field_of_def)
  then have "exec s1 t' ps (key_claim_write k) = (upd ?r ?e s1, Applied)"
    by (simp add: exec_def key_claim_write_def run_def apply_act_def)
  then show "snd (exec s1 t' ps (key_claim_write k)) = Applied"
    and "map_of (fst (exec s1 t' ps (key_claim_write k))) = map_of s1"
    using held by auto
qed
(* GATE:END *)


section \<open>A claim has one owner\<close>

(* GATE:BEGIN MM6 *)
theorem a_claim_held_by_another_is_refused_and_changes_nothing:
  "field_of s (KClaim (param ps ClaimP)) Owner \<noteq> NoVal \<Longrightarrow>
   field_of s (KClaim (param ps ClaimP)) Owner \<noteq> param ps OwnerP \<Longrightarrow>
     exec s t ps (key_claim_write k) = (s, Conflict HeldByOther)"
  by (simp add: exec_def key_claim_write_def)

theorem an_applied_claim_names_its_owner:
  assumes applied: "exec s t ps (key_claim_write k) = (s', Applied)"
  shows "field_of s' (KClaim (param ps ClaimP)) Owner = param ps OwnerP"
proof -
  have wf: "well_formed (key_claim_write k)" by (rule commands_are_well_formed)
  have "s' = upd (KClaim (param ps ClaimP)) (Entry [(Constraint, Atom k), (Owner, param ps OwnerP)] {}) s"
    using exec_applied(2)[OF wf applied] by (simp add: key_claim_write_def run_def apply_act_def)
  then show ?thesis by (simp add: field_of_def)
qed
(* GATE:END *)


section \<open>A tombstoned row\<close>

(* GATE:BEGIN MM7 *)
theorem a_tombstoned_row_refuses_a_replace_and_changes_nothing:
  "map_of s (KTxn (param ps TxnId)) = None \<Longrightarrow> field_of s (KVRow (param ps Root)) Deleted = Flag True \<Longrightarrow>
     exec s t ps delta_replace = (s, Conflict Tombstoned)"
  by (simp add: exec_def delta_replace_def field_of_def split: option.splits)
(* GATE:END *)


section \<open>What an applied command writes\<close>

lemma field_of_frame: "map_of s' r = map_of s r \<Longrightarrow> field_of s' r f = field_of s r f"
  by (simp add: field_of_def)

lemma create_present:
  assumes "exec s t ps create_if_absent = (s', Applied)"
  shows "map_of s (KVRow (param ps Root)) = None"
  using exec_applied(1)[OF commands_are_well_formed(1) assms] by (simp add: create_if_absent_def split: if_splits)

lemma create_effects:
  assumes "exec s t ps create_if_absent = (s', Applied)"
  shows "s' = run
    [APut (KTxn (param ps TxnId)) [(Rev, param ps NewRev), (Digest, param ps RequestDigest)],
     APut (KVRow (param ps Root)) [(Epoch, param ps EpochP), (Seq, Num 1), (Head, param ps NewRev), (Deleted, Flag False)],
     AAssert (KAgg (param ps Root)) (facts_of (param ps Payload)),
     APut (KRcpt (param ps Root) (param ps EpochP) (Num 1)) [(Rev, param ps NewRev), (Prev, NoVal), (TxnOf, param ps TxnId), (At, t)],
     APutFacts (KPatch (param ps Root) (param ps EpochP) (Num 1) Add) (facts_of (param ps Payload))] s"
  using exec_applied(2)[OF commands_are_well_formed(1) assms] by (simp add: create_if_absent_def)

lemma replace_present:
  assumes "exec s t ps delta_replace = (s', Applied)"
  shows "map_of s (KVRow (param ps Root)) \<noteq> None"
  using exec_applied(1)[OF commands_are_well_formed(2) assms] by (simp add: delta_replace_def split: if_splits)

lemma replace_effects:
  assumes "exec s t ps delta_replace = (s', Applied)" and seq: "field_of s (KVRow (param ps Root)) Seq = Num m"
  shows "s' = run
    [ASet (KVRow (param ps Root)) [(Seq, Num (Suc m)), (Head, param ps NewRev)],
     ARetract (KAgg (param ps Root)) (facts_of (param ps Retracted)),
     AAssert (KAgg (param ps Root)) (facts_of (param ps Asserted)),
     APut (KTxn (param ps TxnId)) [(Rev, param ps NewRev), (Digest, param ps RequestDigest)],
     APut (KRcpt (param ps Root) (param ps EpochP) (Num (Suc m)))
       [(Rev, param ps NewRev), (Prev, field_of s (KVRow (param ps Root)) Head), (TxnOf, param ps TxnId), (At, t)],
     APutFacts (KPatch (param ps Root) (param ps EpochP) (Num (Suc m)) Add) (facts_of (param ps Asserted)),
     APutFacts (KPatch (param ps Root) (param ps EpochP) (Num (Suc m)) Del) (facts_of (param ps Retracted))] s"
  using exec_applied(2)[OF commands_are_well_formed(2) assms(1)] seq by (simp add: delta_replace_def next_seq_def)

lemma append_present:
  assumes "exec s t ps append_event = (s', Applied)"
  shows "map_of s (KVRow (param ps Stream)) \<noteq> None"
  using exec_applied(1)[OF commands_are_well_formed(3) assms] by (simp add: append_event_def split: if_splits)

lemma append_effects:
  assumes "exec s t ps append_event = (s', Applied)" and seq: "field_of s (KVRow (param ps Stream)) Seq = Num m"
  shows "s' = run
    [ASet (KVRow (param ps Stream)) [(Epoch, param ps EpochP), (Seq, Num (Suc m)), (Head, App RevisionIri [param ps RevBase, Num (Suc m)])],
     APut (KTxn (param ps TxnId)) [(Rev, App RevisionIri [param ps RevBase, Num (Suc m)]), (Digest, param ps RequestDigest)],
     APut (KRcpt (param ps Stream) (param ps EpochP) (Num (Suc m)))
       [(Rev, App RevisionIri [param ps RevBase, Num (Suc m)]), (Prev, field_of s (KVRow (param ps Stream)) Head), (TxnOf, param ps TxnId), (At, t)],
     AAssert (KEvt (param ps Stream) (Num (Suc m))) (facts_of (param ps EventRows))] s"
  using exec_applied(2)[OF commands_are_well_formed(3) assms(1)] seq
  by (simp add: append_event_def next_seq_def stream_rev_def)

lemma claim_effects:
  assumes "exec s t ps (key_claim_write k) = (s', Applied)"
  shows "s' = run [APut (KClaim (param ps ClaimP)) [(Constraint, Atom k), (Owner, param ps OwnerP)]] s"
  using exec_applied(2)[OF commands_are_well_formed(4) assms] by (simp add: key_claim_write_def)


section \<open>A sequence advances by one, and the patch log holds the delta as requested\<close>

text \<open>The store computes a sequence's successor. An applied create starts its row at position 1,
  and an applied replace or append moves its row from position m to the successor of m.\<close>

(* GATE:BEGIN MM8 *)
theorem a_create_starts_the_sequence_at_one:
  "exec s t ps create_if_absent = (s', Applied) \<Longrightarrow> field_of s' (KVRow (param ps Root)) Seq = Num 1"
  by (drule create_effects) (simp add: field_of_def map_of_run)

theorem a_replace_moves_the_sequence_to_its_successor:
  "exec s t ps delta_replace = (s', Applied) \<Longrightarrow> field_of s (KVRow (param ps Root)) Seq = Num m \<Longrightarrow>
     field_of s' (KVRow (param ps Root)) Seq = Num (Suc m)"
  by (drule (1) replace_effects) (simp add: field_of_def map_of_run map_of_merge_flds entry_or_empty_def)

theorem an_append_moves_the_sequence_to_its_successor:
  "exec s t ps append_event = (s', Applied) \<Longrightarrow> field_of s (KVRow (param ps Stream)) Seq = Num m \<Longrightarrow>
     field_of s' (KVRow (param ps Stream)) Seq = Num (Suc m)"
  by (drule (1) append_effects) (simp add: field_of_def map_of_run map_of_merge_flds entry_or_empty_def)
(* GATE:END *)

text \<open>The patch log holds the delta as the caller requested it, the facts asserted and the facts
  retracted, keyed by the row's new position.\<close>

(* GATE:BEGIN MM9 *)
theorem the_patch_log_holds_the_delta_as_requested:
  assumes "exec s t ps delta_replace = (s', Applied)" and "field_of s (KVRow (param ps Root)) Seq = Num m"
  shows "map_of s' (KPatch (param ps Root) (param ps EpochP) (Num (Suc m)) Add) = Some (Entry [] (facts_of (param ps Asserted)))"
    and "map_of s' (KPatch (param ps Root) (param ps EpochP) (Num (Suc m)) Del) = Some (Entry [] (facts_of (param ps Retracted)))"
  using replace_effects[OF assms] by (simp_all add: map_of_run)
(* GATE:END *)


section \<open>One receipt for each target, epoch and sequence\<close>

text \<open>Every receipt of a target sits at a position no later than its row's sequence, and every
  row holds a position as its sequence.\<close>

definition receipts_below :: "'a state \<Rightarrow> bool" where
  "receipts_below s \<longleftrightarrow>
     (\<forall>tg e k. map_of s (KRcpt tg e k) \<noteq> None \<longrightarrow> (\<exists>n m. k = Num n \<and> field_of s (KVRow tg) Seq = Num m \<and> n \<le> m))
   \<and> (\<forall>tg. map_of s (KVRow tg) \<noteq> None \<longrightarrow> (\<exists>m. field_of s (KVRow tg) Seq = Num m))"

lemma receipts_below_preserved:
  assumes inv: "receipts_below s"
    and frame: "\<And>k. k \<notin> W \<Longrightarrow> map_of s' k = map_of s k"
    and rcpt: "\<And>tg e k. KRcpt tg e k \<in> W \<Longrightarrow> tg = root \<and> k = Num n1"
    and vrow: "\<And>tg. KVRow tg \<in> W \<Longrightarrow> tg = root"
    and seq': "field_of s' (KVRow root) Seq = Num n1"
    and below: "\<And>e n. map_of s (KRcpt root e (Num n)) \<noteq> None \<Longrightarrow> n < n1"
  shows "receipts_below s'"
proof -
  have R: "\<exists>n m. k = Num n \<and> field_of s' (KVRow tg) Seq = Num m \<and> n \<le> m"
    if old: "map_of s' (KRcpt tg e k) \<noteq> None" for tg e k
  proof (cases "KRcpt tg e k \<in> W")
    case True
    then show ?thesis using rcpt[OF True] seq' by auto
  next
    case False
    then have was: "map_of s (KRcpt tg e k) \<noteq> None" using frame[OF False] old by simp
    then obtain n m where nm: "k = Num n" "field_of s (KVRow tg) Seq = Num m" "n \<le> m"
      using inv unfolding receipts_below_def by blast
    show ?thesis
    proof (cases "tg = root")
      case True
      then have "n < n1" using below was nm(1) by blast
      then show ?thesis using True nm(1) seq' by auto
    next
      case False
      then have "KVRow tg \<notin> W" using vrow by blast
      then have "field_of s' (KVRow tg) Seq = field_of s (KVRow tg) Seq" using frame field_of_frame by blast
      then show ?thesis using nm by auto
    qed
  qed
  have V: "\<exists>m. field_of s' (KVRow tg) Seq = Num m" if row: "map_of s' (KVRow tg) \<noteq> None" for tg
  proof (cases "tg = root")
    case True
    then show ?thesis using seq' by auto
  next
    case False
    then have nw: "KVRow tg \<notin> W" using vrow by blast
    then have "map_of s (KVRow tg) \<noteq> None" using frame[OF nw] row by simp
    then obtain m where "field_of s (KVRow tg) Seq = Num m" using inv unfolding receipts_below_def by blast
    then show ?thesis using frame[OF nw] field_of_frame by metis
  qed
  show ?thesis unfolding receipts_below_def using R V by blast
qed

lemma receipt_kept:
  assumes frame: "\<And>k. k \<notin> W \<Longrightarrow> map_of s' k = map_of s k"
    and rcpt: "\<And>tg e k. KRcpt tg e k \<in> W \<Longrightarrow> tg = root \<and> k = Num n1"
    and below: "\<And>e n. map_of s (KRcpt root e (Num n)) \<noteq> None \<Longrightarrow> n < n1"
    and old: "map_of s (KRcpt tg e k) = Some x"
  shows "map_of s' (KRcpt tg e k) = Some x"
proof (cases "KRcpt tg e k \<in> W")
  case True
  then have "tg = root" "k = Num n1" using rcpt by auto
  then have "n1 < n1" using below old by auto
  then show ?thesis by simp
next
  case False
  then show ?thesis using frame old by simp
qed

lemma receipts_of_row_below:
  "receipts_below s \<Longrightarrow> field_of s (KVRow tg) Seq = Num m \<Longrightarrow> map_of s (KRcpt tg e (Num n)) \<noteq> None \<Longrightarrow> n < Suc m"
  unfolding receipts_below_def by fastforce

lemma no_receipt_without_row:
  "receipts_below s \<Longrightarrow> map_of s (KVRow tg) = None \<Longrightarrow> map_of s (KRcpt tg e k) = None"
  unfolding receipts_below_def field_of_def by fastforce

lemma seq_of_row:
  "receipts_below s \<Longrightarrow> map_of s (KVRow tg) \<noteq> None \<Longrightarrow> \<exists>m. field_of s (KVRow tg) Seq = Num m"
  unfolding receipts_below_def by blast

text \<open>Each of the four commands, applied or not, keeps every receipt at or below its row's
  sequence, and never changes a receipt already written. So there is one receipt for each target,
  epoch and sequence.\<close>

lemma create_keeps:
  assumes inv: "receipts_below s" and applied: "exec s t ps create_if_absent = (s', Applied)"
  shows "receipts_below s'" and "map_of s (KRcpt tg e k) = Some x \<Longrightarrow> map_of s' (KRcpt tg e k) = Some x"
proof -
  let ?W = "{KTxn (param ps TxnId), KVRow (param ps Root), KAgg (param ps Root), KRcpt (param ps Root) (param ps EpochP) (Num 1),
             KPatch (param ps Root) (param ps EpochP) (Num 1) Add}"
  note s' = create_effects[OF applied]
  have frame: "map_of s' k = map_of s k" if "k \<notin> ?W" for k using that by (simp add: s' run_frame)
  have rcpt: "tg = param ps Root \<and> k = Num 1" if "KRcpt tg e k \<in> ?W" for tg e k using that by auto
  have vrow: "tg = param ps Root" if "KVRow tg \<in> ?W" for tg using that by auto
  have seq': "field_of s' (KVRow (param ps Root)) Seq = Num 1" by (rule a_create_starts_the_sequence_at_one[OF applied])
  have below: "n < 1" if "map_of s (KRcpt (param ps Root) e (Num n)) \<noteq> None" for e n
    using that no_receipt_without_row[OF inv create_present[OF applied]] by simp
  show "receipts_below s'" by (rule receipts_below_preserved[OF inv frame rcpt vrow seq' below])
  show "map_of s (KRcpt tg e k) = Some x \<Longrightarrow> map_of s' (KRcpt tg e k) = Some x"
    by (rule receipt_kept[OF frame rcpt below])
qed

lemma replace_keeps:
  assumes inv: "receipts_below s" and applied: "exec s t ps delta_replace = (s', Applied)"
  shows "receipts_below s'" and "map_of s (KRcpt tg e k) = Some x \<Longrightarrow> map_of s' (KRcpt tg e k) = Some x"
proof -
  obtain m where seq: "field_of s (KVRow (param ps Root)) Seq = Num m"
    using seq_of_row[OF inv replace_present[OF applied]] by blast
  let ?W = "{KVRow (param ps Root), KAgg (param ps Root), KTxn (param ps TxnId), KRcpt (param ps Root) (param ps EpochP) (Num (Suc m)),
             KPatch (param ps Root) (param ps EpochP) (Num (Suc m)) Add, KPatch (param ps Root) (param ps EpochP) (Num (Suc m)) Del}"
  note s' = replace_effects[OF applied seq]
  have frame: "map_of s' k = map_of s k" if "k \<notin> ?W" for k using that by (simp add: s' run_frame)
  have rcpt: "tg = param ps Root \<and> k = Num (Suc m)" if "KRcpt tg e k \<in> ?W" for tg e k using that by auto
  have vrow: "tg = param ps Root" if "KVRow tg \<in> ?W" for tg using that by auto
  have seq': "field_of s' (KVRow (param ps Root)) Seq = Num (Suc m)"
    by (rule a_replace_moves_the_sequence_to_its_successor[OF applied seq])
  have below: "n < Suc m" if "map_of s (KRcpt (param ps Root) e (Num n)) \<noteq> None" for e n
    by (rule receipts_of_row_below[OF inv seq that])
  show "receipts_below s'" by (rule receipts_below_preserved[OF inv frame rcpt vrow seq' below])
  show "map_of s (KRcpt tg e k) = Some x \<Longrightarrow> map_of s' (KRcpt tg e k) = Some x"
    by (rule receipt_kept[OF frame rcpt below])
qed

lemma append_keeps:
  assumes inv: "receipts_below s" and applied: "exec s t ps append_event = (s', Applied)"
  shows "receipts_below s'" and "map_of s (KRcpt tg e k) = Some x \<Longrightarrow> map_of s' (KRcpt tg e k) = Some x"
proof -
  obtain m where seq: "field_of s (KVRow (param ps Stream)) Seq = Num m"
    using seq_of_row[OF inv append_present[OF applied]] by blast
  let ?W = "{KVRow (param ps Stream), KTxn (param ps TxnId), KRcpt (param ps Stream) (param ps EpochP) (Num (Suc m)),
             KEvt (param ps Stream) (Num (Suc m))}"
  note s' = append_effects[OF applied seq]
  have frame: "map_of s' k = map_of s k" if "k \<notin> ?W" for k using that by (simp add: s' run_frame)
  have rcpt: "tg = param ps Stream \<and> k = Num (Suc m)" if "KRcpt tg e k \<in> ?W" for tg e k using that by auto
  have vrow: "tg = param ps Stream" if "KVRow tg \<in> ?W" for tg using that by auto
  have seq': "field_of s' (KVRow (param ps Stream)) Seq = Num (Suc m)"
    by (rule an_append_moves_the_sequence_to_its_successor[OF applied seq])
  have below: "n < Suc m" if "map_of s (KRcpt (param ps Stream) e (Num n)) \<noteq> None" for e n
    by (rule receipts_of_row_below[OF inv seq that])
  show "receipts_below s'" by (rule receipts_below_preserved[OF inv frame rcpt vrow seq' below])
  show "map_of s (KRcpt tg e k) = Some x \<Longrightarrow> map_of s' (KRcpt tg e k) = Some x"
    by (rule receipt_kept[OF frame rcpt below])
qed

lemma claim_frame:
  assumes applied: "exec s t ps (key_claim_write c) = (s', Applied)" and k: "k \<noteq> KClaim (param ps ClaimP)"
  shows "map_of s' k = map_of s k"
  using k by (simp add: claim_effects[OF applied] run_frame)

lemma claim_keeps:
  assumes inv: "receipts_below s" and applied: "exec s t ps (key_claim_write c) = (s', Applied)"
  shows "receipts_below s'" and "map_of s (KRcpt tg e k) = Some x \<Longrightarrow> map_of s' (KRcpt tg e k) = Some x"
proof -
  have r: "map_of s' (KRcpt tg' e' k') = map_of s (KRcpt tg' e' k')" for tg' e' k' by (rule claim_frame[OF applied]) simp
  have v: "map_of s' (KVRow tg') = map_of s (KVRow tg')" for tg' by (rule claim_frame[OF applied]) simp
  have f: "field_of s' (KVRow tg') Seq = field_of s (KVRow tg') Seq" for tg' using v field_of_frame by blast
  show "receipts_below s'" using inv unfolding receipts_below_def r v f by blast
  show "map_of s (KRcpt tg e k) = Some x \<Longrightarrow> map_of s' (KRcpt tg e k) = Some x" using r by simp
qed

definition the_commands :: "'a \<Rightarrow> 'a command set" where
  "the_commands c = {create_if_absent, delta_replace, append_event, key_claim_write c}"

(* GATE:BEGIN MM10 *)
theorem every_receipt_stays_at_or_below_its_rows_sequence:
  assumes inv: "receipts_below s" and cmd: "cmd \<in> the_commands c"
  shows "receipts_below (fst (exec s t ps cmd))"
proof (cases "snd (exec s t ps cmd) = Applied")
  case False
  then show ?thesis using inv a_command_not_applied_changes_nothing by metis
next
  case True
  then have applied: "exec s t ps cmd = (fst (exec s t ps cmd), Applied)" by (cases "exec s t ps cmd") simp
  show ?thesis using cmd create_keeps(1)[OF inv] replace_keeps(1)[OF inv] append_keeps(1)[OF inv] claim_keeps(1)[OF inv] applied
    unfolding the_commands_def by blast
qed

theorem a_receipt_once_written_is_never_replaced:
  assumes inv: "receipts_below s" and cmd: "cmd \<in> the_commands c" and old: "map_of s (KRcpt tg e k) = Some x"
  shows "map_of (fst (exec s t ps cmd)) (KRcpt tg e k) = Some x"
proof (cases "snd (exec s t ps cmd) = Applied")
  case False
  then show ?thesis using old a_command_not_applied_changes_nothing by metis
next
  case True
  then have applied: "exec s t ps cmd = (fst (exec s t ps cmd), Applied)" by (cases "exec s t ps cmd") simp
  from cmd have "cmd = create_if_absent \<or> cmd = delta_replace \<or> cmd = append_event \<or> cmd = key_claim_write c"
    by (simp add: the_commands_def)
  then show ?thesis
  proof (elim disjE)
    assume c1: "cmd = create_if_absent"
    show ?thesis using create_keeps(2)[OF inv applied[unfolded c1] old] c1 by simp
  next
    assume c1: "cmd = delta_replace"
    show ?thesis using replace_keeps(2)[OF inv applied[unfolded c1] old] c1 by simp
  next
    assume c1: "cmd = append_event"
    show ?thesis using append_keeps(2)[OF inv applied[unfolded c1] old] c1 by simp
  next
    assume c1: "cmd = key_claim_write c"
    show ?thesis using claim_keeps(2)[OF inv applied[unfolded c1] old] c1 by simp
  qed
qed

theorem the_empty_state_has_its_receipts_below: "receipts_below []"
  by (simp add: receipts_below_def)
(* GATE:END *)


section \<open>No gap\<close>

text \<open>From the empty state, a row's receipts are exactly at the positions from 1 to its sequence,
  so position n is the n-th write, as a position on a sequence is defined in the shared session.\<close>

definition dense :: "'a state \<Rightarrow> bool" where
  "dense s \<longleftrightarrow>
     (\<forall>tg e k. map_of s (KRcpt tg e k) \<noteq> None \<longrightarrow> (\<exists>n. k = Num n) \<and> map_of s (KVRow tg) \<noteq> None)
   \<and> (\<forall>tg. map_of s (KVRow tg) \<noteq> None \<longrightarrow> (\<exists>m. field_of s (KVRow tg) Seq = Num m
        \<and> (\<forall>n. (\<exists>e. map_of s (KRcpt tg e (Num n)) \<noteq> None) \<longleftrightarrow> 1 \<le> n \<and> n \<le> m)))"

lemma field_of_present: "field_of s r f = Num n \<Longrightarrow> map_of s r \<noteq> None"
  by (auto simp: field_of_def split: option.splits)

lemma dense_preserved:
  assumes inv: "dense s"
    and frame: "\<And>k. k \<notin> W \<Longrightarrow> map_of s' k = map_of s k"
    and rcpt: "\<And>tg e k. KRcpt tg e k \<in> W \<Longrightarrow> tg = root \<and> e = ep \<and> k = Num n1"
    and vrow: "\<And>tg. KVRow tg \<in> W \<Longrightarrow> tg = root"
    and seq': "field_of s' (KVRow root) Seq = Num n1"
    and new: "map_of s' (KRcpt root ep (Num n1)) \<noteq> None"
    and before: "\<And>n. (\<exists>e. map_of s (KRcpt root e (Num n)) \<noteq> None) \<longleftrightarrow> 1 \<le> n \<and> n < n1"
    and pos: "1 \<le> n1"
  shows "dense s'"
proof -
  have row: "map_of s' (KVRow root) \<noteq> None" using field_of_present[OF seq'] .
  have P1: "(\<exists>n. k = Num n) \<and> map_of s' (KVRow tg) \<noteq> None" if r: "map_of s' (KRcpt tg e k) \<noteq> None" for tg e k
  proof (cases "KRcpt tg e k \<in> W")
    case True
    then show ?thesis using rcpt[OF True] row by auto
  next
    case False
    then have "map_of s (KRcpt tg e k) \<noteq> None" using frame[OF False] r by simp
    then have k: "\<exists>n. k = Num n" and v: "map_of s (KVRow tg) \<noteq> None" using inv unfolding dense_def by blast+
    show ?thesis
    proof (cases "tg = root")
      case True
      then show ?thesis using k row by simp
    next
      case False
      then have "KVRow tg \<notin> W" using vrow by blast
      then show ?thesis using k v frame by simp
    qed
  qed
  have root_iff: "(\<exists>e. map_of s' (KRcpt root e (Num n)) \<noteq> None) \<longleftrightarrow> 1 \<le> n \<and> n \<le> n1" for n
  proof
    assume "\<exists>e. map_of s' (KRcpt root e (Num n)) \<noteq> None"
    then obtain e where e: "map_of s' (KRcpt root e (Num n)) \<noteq> None" by blast
    show "1 \<le> n \<and> n \<le> n1"
    proof (cases "KRcpt root e (Num n) \<in> W")
      case True
      then show ?thesis using rcpt[OF True] pos by simp
    next
      case False
      then have "map_of s (KRcpt root e (Num n)) \<noteq> None" using frame[OF False] e by simp
      then show ?thesis using before[of n] by auto
    qed
  next
    assume n: "1 \<le> n \<and> n \<le> n1"
    show "\<exists>e. map_of s' (KRcpt root e (Num n)) \<noteq> None"
    proof (cases "n = n1")
      case True
      then show ?thesis using new by blast
    next
      case False
      then have "n < n1" using n by simp
      then obtain e where e: "map_of s (KRcpt root e (Num n)) \<noteq> None" using before[of n] n by blast
      have "KRcpt root e (Num n) \<notin> W" using rcpt False by blast
      then show ?thesis using frame e by metis
    qed
  qed
  have P2: "\<exists>m. field_of s' (KVRow tg) Seq = Num m \<and> (\<forall>n. (\<exists>e. map_of s' (KRcpt tg e (Num n)) \<noteq> None) \<longleftrightarrow> 1 \<le> n \<and> n \<le> m)"
    if v: "map_of s' (KVRow tg) \<noteq> None" for tg
  proof (cases "tg = root")
    case True
    then show ?thesis using seq' root_iff by blast
  next
    case False
    then have nw: "KVRow tg \<notin> W" using vrow by blast
    then have "map_of s (KVRow tg) \<noteq> None" using frame[OF nw] v by simp
    then obtain m where m: "field_of s (KVRow tg) Seq = Num m"
        and iff: "\<forall>n. (\<exists>e. map_of s (KRcpt tg e (Num n)) \<noteq> None) \<longleftrightarrow> 1 \<le> n \<and> n \<le> m"
      using inv unfolding dense_def by blast
    have f: "field_of s' (KVRow tg) Seq = Num m" using m frame[OF nw] field_of_frame by metis
    have "map_of s' (KRcpt tg e (Num n)) = map_of s (KRcpt tg e (Num n))" for e n
      using False rcpt frame by blast
    then show ?thesis using f iff by auto
  qed
  show ?thesis unfolding dense_def using P1 P2 by blast
qed

lemma create_dense:
  assumes inv: "dense s" and applied: "exec s t ps create_if_absent = (s', Applied)"
  shows "dense s'"
proof -
  let ?W = "{KTxn (param ps TxnId), KVRow (param ps Root), KAgg (param ps Root), KRcpt (param ps Root) (param ps EpochP) (Num 1),
             KPatch (param ps Root) (param ps EpochP) (Num 1) Add}"
  note s' = create_effects[OF applied]
  have frame: "map_of s' k = map_of s k" if "k \<notin> ?W" for k using that by (simp add: s' run_frame)
  have rcpt: "tg = param ps Root \<and> e = param ps EpochP \<and> k = Num 1" if "KRcpt tg e k \<in> ?W" for tg e k using that by auto
  have vrow: "tg = param ps Root" if "KVRow tg \<in> ?W" for tg using that by auto
  have seq': "field_of s' (KVRow (param ps Root)) Seq = Num 1" by (rule a_create_starts_the_sequence_at_one[OF applied])
  have new: "map_of s' (KRcpt (param ps Root) (param ps EpochP) (Num 1)) \<noteq> None" by (simp add: s' map_of_run)
  have none: "map_of s (KRcpt (param ps Root) e k) = None" for e k
    using inv create_present[OF applied] unfolding dense_def by blast
  have before: "(\<exists>e. map_of s (KRcpt (param ps Root) e (Num n)) \<noteq> None) \<longleftrightarrow> 1 \<le> n \<and> n < 1" for n
    using none by simp
  show ?thesis by (rule dense_preserved[where W = ?W, OF inv frame rcpt vrow seq' new before]) (assumption | simp)+
qed

lemma replace_dense:
  assumes inv: "dense s" and applied: "exec s t ps delta_replace = (s', Applied)"
  shows "dense s'"
proof -
  obtain m where seq: "field_of s (KVRow (param ps Root)) Seq = Num m"
      and iff: "\<forall>n. (\<exists>e. map_of s (KRcpt (param ps Root) e (Num n)) \<noteq> None) \<longleftrightarrow> 1 \<le> n \<and> n \<le> m"
    using inv replace_present[OF applied] unfolding dense_def by blast
  let ?W = "{KVRow (param ps Root), KAgg (param ps Root), KTxn (param ps TxnId), KRcpt (param ps Root) (param ps EpochP) (Num (Suc m)),
             KPatch (param ps Root) (param ps EpochP) (Num (Suc m)) Add, KPatch (param ps Root) (param ps EpochP) (Num (Suc m)) Del}"
  note s' = replace_effects[OF applied seq]
  have frame: "map_of s' k = map_of s k" if "k \<notin> ?W" for k using that by (simp add: s' run_frame)
  have rcpt: "tg = param ps Root \<and> e = param ps EpochP \<and> k = Num (Suc m)" if "KRcpt tg e k \<in> ?W" for tg e k using that by auto
  have vrow: "tg = param ps Root" if "KVRow tg \<in> ?W" for tg using that by auto
  have seq': "field_of s' (KVRow (param ps Root)) Seq = Num (Suc m)"
    by (rule a_replace_moves_the_sequence_to_its_successor[OF applied seq])
  have new: "map_of s' (KRcpt (param ps Root) (param ps EpochP) (Num (Suc m))) \<noteq> None" by (simp add: s' map_of_run)
  have before: "(\<exists>e. map_of s (KRcpt (param ps Root) e (Num n)) \<noteq> None) \<longleftrightarrow> 1 \<le> n \<and> n < Suc m" for n
    using iff by auto
  show ?thesis by (rule dense_preserved[where W = ?W, OF inv frame rcpt vrow seq' new before]) (assumption | simp)+
qed

lemma append_dense:
  assumes inv: "dense s" and applied: "exec s t ps append_event = (s', Applied)"
  shows "dense s'"
proof -
  obtain m where seq: "field_of s (KVRow (param ps Stream)) Seq = Num m"
      and iff: "\<forall>n. (\<exists>e. map_of s (KRcpt (param ps Stream) e (Num n)) \<noteq> None) \<longleftrightarrow> 1 \<le> n \<and> n \<le> m"
    using inv append_present[OF applied] unfolding dense_def by blast
  let ?W = "{KVRow (param ps Stream), KTxn (param ps TxnId), KRcpt (param ps Stream) (param ps EpochP) (Num (Suc m)),
             KEvt (param ps Stream) (Num (Suc m))}"
  note s' = append_effects[OF applied seq]
  have frame: "map_of s' k = map_of s k" if "k \<notin> ?W" for k using that by (simp add: s' run_frame)
  have rcpt: "tg = param ps Stream \<and> e = param ps EpochP \<and> k = Num (Suc m)" if "KRcpt tg e k \<in> ?W" for tg e k using that by auto
  have vrow: "tg = param ps Stream" if "KVRow tg \<in> ?W" for tg using that by auto
  have seq': "field_of s' (KVRow (param ps Stream)) Seq = Num (Suc m)"
    by (rule an_append_moves_the_sequence_to_its_successor[OF applied seq])
  have new: "map_of s' (KRcpt (param ps Stream) (param ps EpochP) (Num (Suc m))) \<noteq> None" by (simp add: s' map_of_run)
  have before: "(\<exists>e. map_of s (KRcpt (param ps Stream) e (Num n)) \<noteq> None) \<longleftrightarrow> 1 \<le> n \<and> n < Suc m" for n
    using iff by auto
  show ?thesis by (rule dense_preserved[where W = ?W, OF inv frame rcpt vrow seq' new before]) (assumption | simp)+
qed

lemma claim_dense:
  assumes inv: "dense s" and applied: "exec s t ps (key_claim_write c) = (s', Applied)"
  shows "dense s'"
proof -
  have r: "map_of s' (KRcpt tg' e' k') = map_of s (KRcpt tg' e' k')" for tg' e' k' by (rule claim_frame[OF applied]) simp
  have v: "map_of s' (KVRow tg') = map_of s (KVRow tg')" for tg' by (rule claim_frame[OF applied]) simp
  have f: "field_of s' (KVRow tg') Seq = field_of s (KVRow tg') Seq" for tg' using v field_of_frame by blast
  show ?thesis using inv unfolding dense_def r v f by blast
qed

lemma exec_dense:
  assumes inv: "dense s" and cmd: "cmd \<in> the_commands c"
  shows "dense (fst (exec s t ps cmd))"
proof (cases "snd (exec s t ps cmd) = Applied")
  case False
  then show ?thesis using inv a_command_not_applied_changes_nothing by metis
next
  case True
  then have applied: "exec s t ps cmd = (fst (exec s t ps cmd), Applied)" by (cases "exec s t ps cmd") simp
  from cmd have "cmd = create_if_absent \<or> cmd = delta_replace \<or> cmd = append_event \<or> cmd = key_claim_write c"
    by (simp add: the_commands_def)
  then show ?thesis
  proof (elim disjE)
    assume c1: "cmd = create_if_absent"
    show ?thesis using create_dense[OF inv applied[unfolded c1]] c1 by simp
  next
    assume c1: "cmd = delta_replace"
    show ?thesis using replace_dense[OF inv applied[unfolded c1]] c1 by simp
  next
    assume c1: "cmd = append_event"
    show ?thesis using append_dense[OF inv applied[unfolded c1]] c1 by simp
  next
    assume c1: "cmd = key_claim_write c"
    show ?thesis using claim_dense[OF inv applied[unfolded c1]] c1 by simp
  qed
qed

text \<open>A history is a list of commands, each with its clock and its parameters, replayed in order.\<close>

fun replay :: "'a state \<Rightarrow> ('a val \<times> 'a params \<times> 'a command) list \<Rightarrow> 'a state" where
  "replay s [] = s"
| "replay s ((t, ps, cmd) # h) = replay (fst (exec s t ps cmd)) h"

(* GATE:BEGIN MM11 *)
theorem from_nothing_a_rows_receipts_are_its_positions_one_to_its_sequence:
  assumes "\<forall>(t, ps, cmd) \<in> set h. cmd \<in> the_commands c"
  shows "dense (replay [] h)"
proof -
  have "dense s \<Longrightarrow> \<forall>(t, ps, cmd) \<in> set h. cmd \<in> the_commands c \<Longrightarrow> dense (replay s h)" for s
  proof (induct s h rule: replay.induct)
    case (1 s)
    then show ?case by simp
  next
    case (2 s t ps cmd h)
    then show ?case using exec_dense[of s cmd c t ps] by simp
  qed
  moreover have "dense ([] :: 'a state)" by (simp add: dense_def)
  ultimately show ?thesis using assms by blast
qed
(* GATE:END *)

end
