(* SPDX-License-Identifier: MPL-2.0 *)

(* Persistence: the guarded write, its confirmation, dense sequences, idempotent retries, the
   epoch, key claims and profile resolution.
   Source: ontology/persistence/README.md sections 5.1, 5.3, 5.5.3, 5.6.2, 5.6.3, 5.6.6 and 5.6.8,
   and TD-118. A spike, not yet aligned to the formal-methods track. *)

theory Persistence
imports Main
begin

section \<open>The store and the guarded write\<close>

text \<open>A version row holds an aggregate's sequence, its epoch and whether it is tombstoned. The
dataset holds the current epoch. A transaction claim, keyed by the client's transaction id,
carries a digest of the request. A request names its target, the sequence it expects, the epoch
it read, its transaction id and its digest.\<close>

record row =
  seq :: nat
  row_epoch :: nat
  tomb :: bool

record ('id, 'txn, 'd) store =
  ds_epoch :: nat
  rows :: "'id \<Rightarrow> row option"
  claims :: "'txn \<Rightarrow> 'd option"

record ('id, 'txn, 'd) request =
  target :: 'id
  expected :: nat
  writer_epoch :: nat
  txn :: 'txn
  digest :: 'd

text \<open>The four guards of one compare-and-set write: the dataset epoch is the writer's, the row is
at the expected sequence, the row carries no tombstone, and the transaction id is not yet
claimed.\<close>

definition guard :: "('id, 'txn, 'd) store \<Rightarrow> ('id, 'txn, 'd) request \<Rightarrow> bool" where
  "guard s r \<longleftrightarrow>
     ds_epoch s = writer_epoch r \<and>
     (\<exists>w. rows s (target r) = Some w \<and> seq w = expected r \<and> \<not> tomb w) \<and>
     claims s (txn r) = None"

definition new_row :: "('id, 'txn, 'd) store \<Rightarrow> ('id, 'txn, 'd) request \<Rightarrow> row" where
  "new_row s r = \<lparr> seq = expected r + 1, row_epoch = ds_epoch s, tomb = False \<rparr>"

definition commit :: "('id, 'txn, 'd) store \<Rightarrow> ('id, 'txn, 'd) request \<Rightarrow> ('id, 'txn, 'd) store" where
  "commit s r =
     (if guard s r
      then s\<lparr> rows := fun_upd (rows s) (target r) (Some (new_row s r)), claims := fun_upd (claims s) (txn r) (Some (digest r)) \<rparr>
      else s)"

text \<open>The store replies 204 whether or not the update applied. The writer learns the outcome by
reading its transaction claim and, if absent, the row.\<close>

datatype outcome = Applied | IdempotencyKeyReuse | EpochChanged | Gone | PreconditionFailed

definition confirm :: "('id, 'txn, 'd) store \<Rightarrow> ('id, 'txn, 'd) request \<Rightarrow> outcome" where
  "confirm s r =
     (case claims s (txn r) of
        Some d \<Rightarrow> (if d = digest r then Applied else IdempotencyKeyReuse)
      | None \<Rightarrow>
          if ds_epoch s \<noteq> writer_epoch r then EpochChanged
          else if (\<exists>w. rows s (target r) = Some w \<and> tomb w) then Gone
          else PreconditionFailed)"

section \<open>Confirmation is sound\<close>

text \<open>A write that passed its guard confirms as Applied. A write that did not, and whose
transaction id was free, never confirms as Applied, and the outcome it reports names a guard
that really failed.\<close>

theorem applied_iff_guard:
  assumes "claims s (txn r) = None"
  shows "confirm (commit s r) r = Applied \<longleftrightarrow> guard s r"
proof
  assume "guard s r"
  then show "confirm (commit s r) r = Applied" by (simp add: commit_def new_row_def confirm_def)
next
  assume "confirm (commit s r) r = Applied"
  with assms show "guard s r" by (auto simp: commit_def new_row_def confirm_def split: option.splits if_splits)
qed

theorem outcome_names_a_failed_guard:
  assumes "claims s (txn r) = None" and "\<not> guard s r"
  shows "confirm (commit s r) r = EpochChanged \<longrightarrow> ds_epoch s \<noteq> writer_epoch r"
    and "confirm (commit s r) r = Gone \<longrightarrow> (\<exists>w. rows s (target r) = Some w \<and> tomb w)"
    and "confirm (commit s r) r = PreconditionFailed \<longrightarrow>
           ds_epoch s = writer_epoch r \<and> \<not> (\<exists>w. rows s (target r) = Some w \<and> seq w = expected r \<and> \<not> tomb w)"
  using assms by (auto simp: commit_def new_row_def confirm_def guard_def split: option.splits if_splits)

text \<open>Reusing a transaction id for a different request is reported, never mistaken for
success.\<close>

theorem reuse_reported:
  assumes "claims s (txn r) = Some d" and "d \<noteq> digest r"
  shows "confirm (commit s r) r = IdempotencyKeyReuse"
  using assms by (simp add: commit_def new_row_def confirm_def guard_def)

section \<open>Lost updates are prevented, and sequences are dense\<close>

text \<open>Two writers who both read sequence 41 cannot both move the row to 42. After the first
applies, the second's guard fails, whatever its transaction id.\<close>

theorem no_lost_update:
  assumes "guard s r1" and "target r2 = target r1" and "expected r2 = expected r1"
  shows "\<not> guard (commit s r1) r2"
  using assms by (auto simp: commit_def new_row_def guard_def)

theorem sequence_dense:
  assumes "guard s r" and "rows s (target r) = Some w"
  shows "\<exists>w'. rows (commit s r) (target r) = Some w' \<and> seq w' = seq w + 1"
  using assms by (auto simp: commit_def new_row_def guard_def)

text \<open>A write to one aggregate touches no other aggregate's row.\<close>

lemma commit_local: "a \<noteq> target r \<Longrightarrow> rows (commit s r) a = rows s a"
  by (simp add: commit_def new_row_def)

section \<open>Retries are idempotent\<close>

text \<open>Resending an identical request after an unknown outcome either applies once or is a
no-op against the claim, and then confirms as Applied in both cases.\<close>

theorem retry_no_op: "commit (commit s r) r = commit s r"
  by (auto simp: commit_def new_row_def guard_def)

theorem retry_confirms:
  assumes "guard s r"
  shows "confirm (commit (commit s r) r) r = Applied"
  using assms by (simp add: retry_no_op) (simp add: commit_def new_row_def confirm_def)

section \<open>The epoch\<close>

text \<open>A position is an epoch and a sequence. After a restore bumps the epoch, every new position
is above every old one, even though the sequence may have rewound. A consumer that remembers
(3, 91438) and sees (4, 90901) resynchronises rather than skipping.\<close>

definition pos_less :: "nat \<times> nat \<Rightarrow> nat \<times> nat \<Rightarrow> bool" where
  "pos_less p q \<longleftrightarrow> fst p < fst q \<or> (fst p = fst q \<and> snd p < snd q)"

theorem bump_orders_all_positions: "e < e' \<Longrightarrow> pos_less (e, s) (e', s')"
  by (simp add: pos_less_def)

lemma rewind_without_bump_collides: "pos_less (e, 90901) (e, 91438)"
  by (simp add: pos_less_def)

text \<open>Under the dataset-level guard a stale writer, one whose epoch is behind the dataset's,
never applies.\<close>

theorem dataset_guard_refuses_stale: "writer_epoch r < ds_epoch s \<Longrightarrow> \<not> guard s r"
  by (simp add: guard_def)

text \<open>Under a row-level guard only the row's own epoch is compared. A row not rewritten since
the bump still carries the old epoch, so a stale writer matches it. This is the hazard the README
warns of and TD-118 records: the witness below is a store at epoch 4 whose row is still at
epoch 3, and a writer that read epoch 3 passes the row-level guard and fails the dataset-level
one.\<close>

definition guard_row :: "('id, 'txn, 'd) store \<Rightarrow> ('id, 'txn, 'd) request \<Rightarrow> bool" where
  "guard_row s r \<longleftrightarrow>
     (\<exists>w. rows s (target r) = Some w \<and> row_epoch w = writer_epoch r \<and> seq w = expected r \<and> \<not> tomb w) \<and>
     claims s (txn r) = None"

definition stale_store :: "(nat, nat, nat) store" where
  "stale_store = \<lparr> ds_epoch = 4, rows = fun_upd (\<lambda>_. None) 17 (Some \<lparr> seq = 41, row_epoch = 3, tomb = False \<rparr>), claims = (\<lambda>_. None) \<rparr>"

definition stale_request :: "(nat, nat, nat) request" where
  "stale_request = \<lparr> target = 17, expected = 41, writer_epoch = 3, txn = 1, digest = 0 \<rparr>"

theorem row_level_guard_admits_stale_writer:
  "guard_row stale_store stale_request \<and> \<not> guard stale_store stale_request"
  by (simp add: guard_row_def guard_def stale_store_def stale_request_def)

text \<open>Rebasing: under the dataset guard a row keeps its older epoch until its next write
rebases it, and its sequence continues, so the receipt chain crosses the boundary unbroken.\<close>

theorem commit_rebases_row:
  assumes "guard s r"
  shows "\<exists>w'. rows (commit s r) (target r) = Some w' \<and> row_epoch w' = ds_epoch s \<and> seq w' = expected r + 1"
  using assms by (simp add: commit_def new_row_def)

section \<open>Key claims\<close>

text \<open>A key claim is a node per normalised key value, owned by at most one entity. A guarded
write claims a key only if nobody else holds it. Ownership is monotonic, since only the owner
releases a claim, so a follow-up read that sees the claim proves the write applied, and one that
sees another owner proves it did not.\<close>

type_synonym ('k, 'own) claims = "'k \<Rightarrow> 'own option"

definition claim_guard :: "('k, 'own) claims \<Rightarrow> 'k \<Rightarrow> 'own \<Rightarrow> bool" where
  "claim_guard c k own \<longleftrightarrow> c k = None \<or> c k = Some own"

definition claim :: "('k, 'own) claims \<Rightarrow> 'k \<Rightarrow> 'own \<Rightarrow> ('k, 'own) claims" where
  "claim c k own = (if claim_guard c k own then fun_upd c k (Some own) else c)"

theorem ask_after_write_is_definitive:
  "claim c k own k = Some own \<longleftrightarrow> claim_guard c k own"
  by (auto simp: claim_def claim_guard_def)

theorem at_most_one_owner:
  "claim c k own k = Some own \<Longrightarrow> claim c k own k = Some own' \<Longrightarrow> own = own'"
  by simp

theorem ownership_monotonic:
  "c k = Some own \<Longrightarrow> claim c k' own' k = Some own"
  by (auto simp: claim_def claim_guard_def)

text \<open>Two writers racing for a key nobody holds: the first claim wins and the second is refused.
This is P2's guarantee. The remaining gap, two writers whose requests the store interleaves
inside one update, is the store's isolation to close (P3, P5 or P6), and is outside this model,
which applies writes one at a time.\<close>

theorem first_claim_wins:
  assumes "c k = None" and "own \<noteq> own'"
  shows "claim (claim c k own) k own' k = Some own"
  using assms by (simp add: claim_def claim_guard_def)

section \<open>Profile resolution, section 5.5.3\<close>

text \<open>Several profiles may declare a value for one dimension at scopes that all match a target.
Candidates whose scope needs reasoning are dropped where the store supports none. The highest
priority wins. At a tie a candidate needing no reasoning is preferred. A remaining tie is a
refusal, never a guess. Scope kinds are never ranked against each other.\<close>

record 'v cand =
  prio :: int
  needs_reasoning :: bool
  val :: 'v

datatype 'c pick = Baseline | Winner 'c | Ambiguity

definition considered :: "bool \<Rightarrow> 'v cand set \<Rightarrow> 'v cand set" where
  "considered reasoning cs = (if reasoning then cs else {c \<in> cs. \<not> needs_reasoning c})"

definition top :: "'v cand set \<Rightarrow> 'v cand set" where
  "top cs = {c \<in> cs. prio c = Max (prio ` cs)}"

definition preferred :: "'v cand set \<Rightarrow> 'v cand set" where
  "preferred cs = (if \<exists>c \<in> cs. \<not> needs_reasoning c then {c \<in> cs. \<not> needs_reasoning c} else cs)"

definition resolve_dim :: "bool \<Rightarrow> 'v cand set \<Rightarrow> 'v cand pick" where
  "resolve_dim reasoning cs =
     (let cs' = considered reasoning cs in
      if cs' = {} then Baseline
      else if \<exists>c. preferred (top cs') = {c} then Winner (THE c. preferred (top cs') = {c})
      else Ambiguity)"

lemma preferred_subset: "preferred cs \<subseteq> cs"
  by (auto simp: preferred_def)

lemma top_subset: "top cs \<subseteq> cs"
  by (auto simp: top_def)

theorem winner_considered:
  assumes "resolve_dim reasoning cs = Winner c"
  shows "c \<in> considered reasoning cs"
proof -
  from assms obtain c' where c': "preferred (top (considered reasoning cs)) = {c'}"
    unfolding resolve_dim_def Let_def by (auto split: if_splits)
  have "(THE c. preferred (top (considered reasoning cs)) = {c}) = c'"
  proof (rule the_equality)
    show "preferred (top (considered reasoning cs)) = {c'}" by (rule c')
    show "\<And>x. preferred (top (considered reasoning cs)) = {x} \<Longrightarrow> x = c'" using c' by auto
  qed
  with assms c' have "c = c'" unfolding resolve_dim_def Let_def by (auto split: if_splits)
  then show ?thesis using c' preferred_subset top_subset by fastforce
qed

theorem winner_has_top_priority:
  assumes fin: "finite cs" and "resolve_dim reasoning cs = Winner c"
  shows "\<forall>c' \<in> considered reasoning cs. prio c' \<le> prio c"
proof -
  let ?cs' = "considered reasoning cs"
  from assms(2) obtain c' where c': "preferred (top ?cs') = {c'}"
    unfolding resolve_dim_def Let_def by (auto split: if_splits)
  have "(THE c. preferred (top ?cs') = {c}) = c'"
  proof (rule the_equality)
    show "preferred (top ?cs') = {c'}" by (rule c')
    show "\<And>x. preferred (top ?cs') = {x} \<Longrightarrow> x = c'" using c' by auto
  qed
  with assms(2) c' have cc: "c = c'" unfolding resolve_dim_def Let_def by (auto split: if_splits)
  have "c' \<in> top ?cs'" using c' preferred_subset by fastforce
  then have "prio c' = Max (prio ` ?cs')" by (simp add: top_def)
  moreover have "finite (prio ` ?cs')" using fin by (simp add: considered_def)
  ultimately show ?thesis using cc by (auto simp: Max_ge)
qed

theorem reasoning_dropped_when_unsupported:
  "resolve_dim False cs = Winner c \<Longrightarrow> \<not> needs_reasoning c"
  using winner_considered[of False cs c] by (simp add: considered_def)

text \<open>Two candidates at the top priority that neither need reasoning are a tie, and a tie is
Ambiguity. So are two that both need it, where no top candidate avoids it: otherwise the one
that avoids it is preferred, which is the rule, not a tie.\<close>

theorem tie_is_ambiguity:
  assumes fin: "finite cs" and "c1 \<in> cs" and "c2 \<in> cs" and "c1 \<noteq> c2"
    and "prio c1 = Max (prio ` cs)" and "prio c2 = Max (prio ` cs)"
    and "\<not> needs_reasoning c1" and "\<not> needs_reasoning c2"
  shows "resolve_dim True cs = Ambiguity"
proof -
  have cs': "considered True cs = cs" by (simp add: considered_def)
  have both: "c1 \<in> top cs" "c2 \<in> top cs" using assms by (simp_all add: top_def)
  have "c1 \<in> preferred (top cs)" "c2 \<in> preferred (top cs)"
    using both assms(7,8) by (auto simp: preferred_def)
  then have "\<not> (\<exists>c. preferred (top cs) = {c})" using assms(4) by auto
  moreover have "cs \<noteq> {}" using assms(2) by auto
  ultimately show ?thesis unfolding resolve_dim_def Let_def cs' by simp
qed

theorem reasoning_tie_is_ambiguity:
  assumes fin: "finite cs" and "c1 \<in> cs" and "c2 \<in> cs" and "c1 \<noteq> c2"
    and "prio c1 = Max (prio ` cs)" and "prio c2 = Max (prio ` cs)"
    and all_need: "\<forall>c \<in> top cs. needs_reasoning c"
  shows "resolve_dim True cs = Ambiguity"
proof -
  have cs': "considered True cs = cs" by (simp add: considered_def)
  have both: "c1 \<in> top cs" "c2 \<in> top cs" using assms by (simp_all add: top_def)
  have "preferred (top cs) = top cs" using all_need by (auto simp: preferred_def)
  then have "\<not> (\<exists>c. preferred (top cs) = {c})" using both assms(4) by auto
  moreover have "cs \<noteq> {}" using assms(2) by auto
  ultimately show ?thesis unfolding resolve_dim_def Let_def cs' by simp
qed

end
