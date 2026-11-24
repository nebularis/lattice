(* SPDX-License-Identifier: MPL-2.0 *)

(* The four operations of the paper lowering as values of the IR: a create, a delta replace under
   a patch log, an event append under the dataset guard, and a key claim write. Each is written as
   the paper lowering's section 3 writes it, with the maintainer's answer that the store computes a
   sequence's successor in the replace as in the append. *)

theory Commands
  imports IR
begin

text \<open>The successor of a version row's sequence, read from the state before the command.\<close>

definition next_seq :: "pname \<Rightarrow> 'a vexp" where
  "next_seq x = Succ (Field (RefVRow (KeyParam x)) Seq)"

text \<open>The revision of an append, the named function of the revision base and the new sequence.\<close>

definition stream_rev :: "'a vexp" where
  "stream_rev = Fn RevisionIri [Param RevBase, next_seq Stream]"

definition create_if_absent :: "'a command" where
  "create_if_absent = Command
    [(Absent (Txn (Param TxnId)), Duplicate),
     (Absent (VRow (Param Root)), Conflict Exists)]
    [Put (Txn (Param TxnId)) [(Rev, Param NewRev), (Digest, Param RequestDigest)],
     Put (VRow (Param Root)) [(Epoch, Param EpochP), (Seq, Const (Num 1)), (Head, Param NewRev), (Deleted, Const (Flag False))],
     Assert (Agg (Param Root)) (Param Payload),
     Put (Rcpt (Param Root) (Param EpochP) (Const (Num 1))) [(Rev, Param NewRev), (Prev, Const NoVal), (TxnOf, Param TxnId), (At, Now)],
     PutFacts (Patch (Param Root) (Param EpochP) (Const (Num 1)) Add) (Param Payload)]"

definition delta_replace :: "'a command" where
  "delta_replace = Command
    [(Absent (Txn (Param TxnId)), Duplicate),
     (Present (VRow (Param Root)), Conflict Missing),
     (FlagUnset (VRow (Param Root)) Deleted, Conflict Tombstoned),
     (FieldEq (VRow (Param Root)) Epoch (Param EpochP), Conflict Stale),
     (FieldEq (VRow (Param Root)) Seq (Param ExpectedSeq), Conflict Stale)]
    [SetFields (VRow (Param Root)) [(Seq, next_seq Root), (Head, Param NewRev)],
     Retract (Agg (Param Root)) (Param Retracted),
     Assert (Agg (Param Root)) (Param Asserted),
     Put (Txn (Param TxnId)) [(Rev, Param NewRev), (Digest, Param RequestDigest)],
     Put (Rcpt (Param Root) (Param EpochP) (next_seq Root)) [(Rev, Param NewRev), (Prev, Field (RefVRow (KeyParam Root)) Head), (TxnOf, Param TxnId), (At, Now)],
     PutFacts (Patch (Param Root) (Param EpochP) (next_seq Root) Add) (Param Asserted),
     PutFacts (Patch (Param Root) (Param EpochP) (next_seq Root) Del) (Param Retracted)]"

definition append_event :: "'a command" where
  "append_event = Command
    [(FieldEq DEpoch Epoch (Param EpochP), Refused EpochMismatch),
     (Absent (Txn (Param TxnId)), Duplicate),
     (Present (VRow (Param Stream)), Conflict Missing),
     (FlagUnset (VRow (Param Stream)) Deleted, Conflict Tombstoned)]
    [SetFields (VRow (Param Stream)) [(Epoch, Param EpochP), (Seq, next_seq Stream), (Head, stream_rev)],
     Put (Txn (Param TxnId)) [(Rev, stream_rev), (Digest, Param RequestDigest)],
     Put (Rcpt (Param Stream) (Param EpochP) (next_seq Stream)) [(Rev, stream_rev), (Prev, Field (RefVRow (KeyParam Stream)) Head), (TxnOf, Param TxnId), (At, Now)],
     AppendRows (Evt (Param Stream) (next_seq Stream)) (Param EventRows)]"

text \<open>The constraint a claim names is a value of the deployment, given when the command is built.\<close>

definition key_claim_write :: "'a \<Rightarrow> 'a command" where
  "key_claim_write c = Command
    [(NotHeldByOther (Claim (Param ClaimP)) Owner (Param OwnerP), Conflict HeldByOther)]
    [Put (Claim (Param ClaimP)) [(Constraint, Const (Atom c)), (Owner, Param OwnerP)]]"

end
