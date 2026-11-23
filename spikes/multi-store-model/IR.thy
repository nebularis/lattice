(* SPDX-License-Identifier: MPL-2.0 *)

(* The neutral IR of guarded commands over logical resources, and its exec function, as the
   paper lowering of the four operations set it out (the IR of section 2 of that note), with the
   maintainer's three answers to it: a resend is answered before a conflict, the store computes a
   sequence's successor, and the patch log holds the delta as requested. Hand-written. It imports
   the shared session for a position, and never the ledger's session. *)

theory IR
  imports LatticeShared.Positions
begin

section \<open>Names\<close>

text \<open>The fields a resource holds, the parameters a command reads, the named functions a value
  may apply, the two directions of a patch, and the outcomes.\<close>

datatype field = Epoch | Seq | Head | Deleted | Rev | Digest | Prev | TxnOf | At | Constraint | Owner

datatype pname = Root | Stream | EpochP | ExpectedSeq | NewRev | TxnId | RequestDigest | RevBase
  | ClaimP | OwnerP | Payload | Asserted | Retracted | EventRows

datatype fname = RevisionIri

datatype dir = Add | Del

datatype reason = Exists | Missing | Tombstoned | Stale | HeldByOther | EpochMismatch

datatype outcome = Applied | Duplicate | Conflict reason | Refused reason


section \<open>Values, resources and the state\<close>

text \<open>A value is an atom of any type, a position, a flag, no value, a list of facts, or a named
  function applied to values. A named function is not computed here: its application is the
  value, and a realisation decodes it, as a relational row holds a revision's base and number.\<close>

datatype 'a val = Atom 'a | Num position | Flag bool | NoVal | Facts "'a list" | App fname "'a val list"

text \<open>A resource is named by its kind and its logical key.\<close>

datatype 'a res = KAgg "'a val" | KVRow "'a val" | KTxn "'a val" | KRcpt "'a val" "'a val" "'a val"
  | KPatch "'a val" "'a val" "'a val" dir | KEvt "'a val" "'a val" | KClaim "'a val" | KDEpoch

text \<open>Each resource holds fields and a set of facts. The state holds an entry for each resource
  written, as a list of pairs read through map_of, so two states mean the same when their map_of
  is the same.\<close>

datatype 'a entry = Entry (flds: "(field \<times> 'a val) list") (fcts: "'a set")

type_synonym 'a state = "('a res \<times> 'a entry) list"

type_synonym 'a params = "(pname \<times> 'a val) list"


section \<open>Expressions, guards, effects and commands\<close>

text \<open>A field is read only from a resource named by a parameter or a constant, which is all the
  four commands need, so expressions and resources are not mutually recursive.\<close>

datatype 'a key = KeyParam pname | KeyConst "'a val"

datatype 'a rref = RefAgg "'a key" | RefVRow "'a key" | RefTxn "'a key" | RefClaim "'a key" | RefDEpoch

datatype 'a vexp = Param pname | Now | Const "'a val" | Field "'a rref" field | Succ "'a vexp"
  | Fn fname "'a vexp list"

datatype 'a rexp = Agg "'a vexp" | VRow "'a vexp" | Txn "'a vexp" | Rcpt "'a vexp" "'a vexp" "'a vexp"
  | Patch "'a vexp" "'a vexp" "'a vexp" dir | Evt "'a vexp" "'a vexp" | Claim "'a vexp" | DEpoch

datatype 'a guard = Absent "'a rexp" | Present "'a rexp" | FieldEq "'a rexp" field "'a vexp"
  | FlagUnset "'a rexp" field | NotHeldByOther "'a rexp" field "'a vexp"

datatype 'a effect = Put "'a rexp" "(field \<times> 'a vexp) list" | PutFacts "'a rexp" "'a vexp"
  | SetFields "'a rexp" "(field \<times> 'a vexp) list" | Retract "'a rexp" "'a vexp"
  | Assert "'a rexp" "'a vexp" | AppendRows "'a rexp" "'a vexp"

datatype 'a command = Command (guards: "('a guard \<times> outcome) list") (effects: "'a effect list")


section \<open>Reading the state\<close>

definition param :: "'a params \<Rightarrow> pname \<Rightarrow> 'a val" where
  "param ps x = (case map_of ps x of Some v \<Rightarrow> v | None \<Rightarrow> NoVal)"

definition field_of :: "'a state \<Rightarrow> 'a res \<Rightarrow> field \<Rightarrow> 'a val" where
  "field_of s r f = (case map_of s r of
      Some e \<Rightarrow> (case map_of (flds e) f of Some v \<Rightarrow> v | None \<Rightarrow> NoVal)
    | None \<Rightarrow> NoVal)"

definition facts_of :: "'a val \<Rightarrow> 'a set" where
  "facts_of v = (case v of Facts xs \<Rightarrow> set xs | _ \<Rightarrow> {})"

fun key_val :: "'a params \<Rightarrow> 'a key \<Rightarrow> 'a val" where
  "key_val ps (KeyParam x) = param ps x"
| "key_val ps (KeyConst v) = v"

fun ref_res :: "'a params \<Rightarrow> 'a rref \<Rightarrow> 'a res" where
  "ref_res ps (RefAgg k) = KAgg (key_val ps k)"
| "ref_res ps (RefVRow k) = KVRow (key_val ps k)"
| "ref_res ps (RefTxn k) = KTxn (key_val ps k)"
| "ref_res ps (RefClaim k) = KClaim (key_val ps k)"
| "ref_res ps RefDEpoch = KDEpoch"

fun succ_val :: "'a val \<Rightarrow> 'a val" where
  "succ_val (Num n) = Num (Suc n)"
| "succ_val _ = NoVal"

text \<open>Every expression is evaluated in the state before the command, with the clock and the
  parameters as inputs.\<close>

fun eval :: "'a state \<Rightarrow> 'a val \<Rightarrow> 'a params \<Rightarrow> 'a vexp \<Rightarrow> 'a val" where
  "eval s t ps (Param x) = param ps x"
| "eval s t ps Now = t"
| "eval s t ps (Const v) = v"
| "eval s t ps (Field r f) = field_of s (ref_res ps r) f"
| "eval s t ps (Succ e) = succ_val (eval s t ps e)"
| "eval s t ps (Fn g es) = App g (map (eval s t ps) es)"

fun eval_r :: "'a state \<Rightarrow> 'a val \<Rightarrow> 'a params \<Rightarrow> 'a rexp \<Rightarrow> 'a res" where
  "eval_r s t ps (Agg a) = KAgg (eval s t ps a)"
| "eval_r s t ps (VRow a) = KVRow (eval s t ps a)"
| "eval_r s t ps (Txn a) = KTxn (eval s t ps a)"
| "eval_r s t ps (Rcpt a b c) = KRcpt (eval s t ps a) (eval s t ps b) (eval s t ps c)"
| "eval_r s t ps (Patch a b c d) = KPatch (eval s t ps a) (eval s t ps b) (eval s t ps c) d"
| "eval_r s t ps (Evt a b) = KEvt (eval s t ps a) (eval s t ps b)"
| "eval_r s t ps (Claim a) = KClaim (eval s t ps a)"
| "eval_r s t ps DEpoch = KDEpoch"

fun holds :: "'a state \<Rightarrow> 'a val \<Rightarrow> 'a params \<Rightarrow> 'a guard \<Rightarrow> bool" where
  "holds s t ps (Absent r) = (map_of s (eval_r s t ps r) = None)"
| "holds s t ps (Present r) = (map_of s (eval_r s t ps r) \<noteq> None)"
| "holds s t ps (FieldEq r f e) = (field_of s (eval_r s t ps r) f = eval s t ps e)"
| "holds s t ps (FlagUnset r f) = (field_of s (eval_r s t ps r) f \<noteq> Flag True)"
| "holds s t ps (NotHeldByOther r f e) =
     (field_of s (eval_r s t ps r) f = NoVal \<or> field_of s (eval_r s t ps r) f = eval s t ps e)"

text \<open>The guards are ordered, and the first that fails decides the outcome.\<close>

fun first_fail :: "'a state \<Rightarrow> 'a val \<Rightarrow> 'a params \<Rightarrow> ('a guard \<times> outcome) list \<Rightarrow> outcome option" where
  "first_fail s t ps [] = None"
| "first_fail s t ps ((g, out) # gs) = (if holds s t ps g then first_fail s t ps gs else Some out)"


section \<open>Writing the state\<close>

text \<open>An effect evaluated in the state before the command is an action on one resource.\<close>

datatype 'a act = APut "'a res" "(field \<times> 'a val) list" | APutFacts "'a res" "'a set"
  | ASet "'a res" "(field \<times> 'a val) list" | ARetract "'a res" "'a set" | AAssert "'a res" "'a set"

fun concretise :: "'a state \<Rightarrow> 'a val \<Rightarrow> 'a params \<Rightarrow> 'a effect \<Rightarrow> 'a act" where
  "concretise s t ps (Put r fs) = APut (eval_r s t ps r) (map (\<lambda>(f, e). (f, eval s t ps e)) fs)"
| "concretise s t ps (PutFacts r e) = APutFacts (eval_r s t ps r) (facts_of (eval s t ps e))"
| "concretise s t ps (SetFields r fs) = ASet (eval_r s t ps r) (map (\<lambda>(f, e). (f, eval s t ps e)) fs)"
| "concretise s t ps (Retract r e) = ARetract (eval_r s t ps r) (facts_of (eval s t ps e))"
| "concretise s t ps (Assert r e) = AAssert (eval_r s t ps r) (facts_of (eval s t ps e))"
| "concretise s t ps (AppendRows r e) = AAssert (eval_r s t ps r) (facts_of (eval s t ps e))"

fun act_res :: "'a act \<Rightarrow> 'a res" where
  "act_res (APut r _) = r"
| "act_res (APutFacts r _) = r"
| "act_res (ASet r _) = r"
| "act_res (ARetract r _) = r"
| "act_res (AAssert r _) = r"

fun is_retract :: "'a act \<Rightarrow> bool" where
  "is_retract (ARetract _ _) = True"
| "is_retract _ = False"

definition merge_flds :: "(field \<times> 'a val) list \<Rightarrow> (field \<times> 'a val) list \<Rightarrow> (field \<times> 'a val) list" where
  "merge_flds old new = new @ filter (\<lambda>p. fst p \<notin> fst ` set new) old"

definition entry_or_empty :: "'a entry option \<Rightarrow> 'a entry" where
  "entry_or_empty eo = (case eo of Some e \<Rightarrow> e | None \<Rightarrow> Entry [] {})"

text \<open>What an action does to the entry of its own resource. A put writes the entry whole, a set
  of fields overrides the fields it names, a retraction removes facts from an entry that exists,
  and an assertion adds facts.\<close>

fun step :: "'a act \<Rightarrow> 'a entry option \<Rightarrow> 'a entry option" where
  "step (APut _ fs) eo = Some (Entry fs {})"
| "step (APutFacts _ F) eo = Some (Entry [] F)"
| "step (ASet _ fs) eo = Some (Entry (merge_flds (flds (entry_or_empty eo)) fs) (fcts (entry_or_empty eo)))"
| "step (ARetract _ F) eo = (case eo of None \<Rightarrow> None | Some e \<Rightarrow> Some (Entry (flds e) (fcts e - F)))"
| "step (AAssert _ F) eo = Some (Entry (flds (entry_or_empty eo)) (fcts (entry_or_empty eo) \<union> F))"

definition upd :: "'k \<Rightarrow> 'v \<Rightarrow> ('k \<times> 'v) list \<Rightarrow> ('k \<times> 'v) list" where
  "upd k v xs = (k, v) # filter (\<lambda>p. fst p \<noteq> k) xs"

definition apply_act :: "'a act \<Rightarrow> 'a state \<Rightarrow> 'a state" where
  "apply_act a s = (case step a (map_of s (act_res a)) of None \<Rightarrow> s | Some e \<Rightarrow> upd (act_res a) e s)"

text \<open>The retractions run first and every other action after them, each in the command's order,
  so a fact both retracted and asserted is present afterwards.\<close>

definition run :: "'a act list \<Rightarrow> 'a state \<Rightarrow> 'a state" where
  "run as s = fold apply_act (filter (\<lambda>a. \<not> is_retract a) as) (fold apply_act (filter is_retract as) s)"


section \<open>exec\<close>

definition exec :: "'a state \<Rightarrow> 'a val \<Rightarrow> 'a params \<Rightarrow> 'a command \<Rightarrow> 'a state \<times> outcome" where
  "exec s t ps c = (case first_fail s t ps (guards c) of
      Some out \<Rightarrow> (s, out)
    | None \<Rightarrow> (run (map (concretise s t ps) (effects c)) s, Applied))"

end
