(* SPDX-License-Identifier: MPL-2.0 *)

(* The ledger kernel as the decisions of 2026-11-09 to 2026-11-15 leave it, each definition once.
   A spike for slice LG-21: definitions and examples only, no law proved. The laws each definition
   must keep, and the laws it gains, are in docs/developer/sketches/ledger-target-kernel.md. *)

theory Target
imports Complex_Main
begin

section \<open>Amounts, in whole units or exact\<close>

text \<open>Every definition that only adds, subtracts and compares is stated once, over any ordered ring,
  so it serves whole units (int) and exact amounts (rat) alike. Only a rule names its number type.\<close>

type_synonym ('k, 'n) amounts = "'k \<Rightarrow> 'n"

definition total :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) amounts \<Rightarrow> 'n" where
  "total K v = (\<Sum>k\<in>K. v k)"

definition nothing :: "('k, 'n::linordered_idom) amounts" where
  "nothing = (\<lambda>_. 0)"

definition less :: "('k, 'n::linordered_idom) amounts \<Rightarrow> ('k, 'n) amounts \<Rightarrow> ('k, 'n) amounts" where
  "less v w = (\<lambda>k. v k - w k)"

definition fits_in :: "('k, 'n::linordered_idom) amounts \<Rightarrow> ('k, 'n) amounts \<Rightarrow> bool" where
  "fits_in v w \<longleftrightarrow> (\<forall>k. v k \<le> w k)"

definition nonneg_on :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) amounts \<Rightarrow> bool" where
  "nonneg_on K v \<longleftrightarrow> (\<forall>k. 0 \<le> v k) \<and> (\<forall>k. k \<notin> K \<longrightarrow> v k = 0)"

section \<open>What a rule must do\<close>

type_synonym ('k, 'n) rule = "('k, 'n) amounts \<Rightarrow> 'n \<Rightarrow> ('k, 'n) amounts"

text \<open>Rationing: what is available is divided among claims that exceed it. No part is negative or
  above its claim, the parts sum to no more than the amount shared, and the whole returns the whole.\<close>

definition rations :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> bool" where
  "rations K R \<longleftrightarrow>
     (\<forall>v x. nonneg_on K v \<and> 0 \<le> x \<and> x \<le> total K v \<longrightarrow>
        nonneg_on K (R v x) \<and> fits_in (R v x) v \<and> total K (R v x) \<le> x)
     \<and> (\<forall>v. nonneg_on K v \<longrightarrow> R v (total K v) = v)"

definition residual :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> ('k, 'n) amounts \<Rightarrow> 'n \<Rightarrow> 'n" where
  "residual K R v x = x - total K (R v x)"

definition exact :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> bool" where
  "exact K R \<longleftrightarrow> (\<forall>v x. nonneg_on K v \<and> 0 \<le> x \<and> x \<le> total K v \<longrightarrow> residual K R v x = 0)"

text \<open>The four axioms of the kernel as it stands are rationing with no residual.\<close>

definition lawful :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> bool" where
  "lawful K R \<longleftrightarrow> rations K R \<and> exact K R"

text \<open>Apportionment: an amount is divided into proper shares by a stated basis, with no bound of a
  part by its basis.\<close>

definition apportions :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> bool" where
  "apportions K R \<longleftrightarrow>
     (\<forall>w x. nonneg_on K w \<and> 0 < total K w \<and> 0 \<le> x \<longrightarrow> nonneg_on K (R w x) \<and> total K (R w x) = x)
     \<and> (\<forall>w. nonneg_on K w \<longrightarrow> R w (total K w) = w)"

section \<open>Rules over exact amounts\<close>

definition proportional :: "'k set \<Rightarrow> ('k, 'n::linordered_field) rule" where
  "proportional K v x = (\<lambda>k. if k \<notin> K \<or> total K v = 0 then 0 else x * v k / total K v)"

section \<open>Ranks\<close>

text \<open>An order reaches a rule as a rank on each request, derived from the criterion its account
  declares. A lower rank is served first. No rule reads anything else of a key.\<close>

definition ahead :: "'k set \<Rightarrow> ('k \<Rightarrow> nat) \<Rightarrow> ('k, 'n::linordered_idom) amounts \<Rightarrow> 'k \<Rightarrow> 'n" where
  "ahead K rank v k = (\<Sum>j\<in>{j\<in>K. rank j < rank k}. v j)"

definition beside :: "'k set \<Rightarrow> ('k \<Rightarrow> nat) \<Rightarrow> 'k \<Rightarrow> 'k set" where
  "beside K rank k = {j\<in>K. rank j = rank k}"

text \<open>Ranks are served in order. A rank whose requests fit what is left is granted whole. The first
  that does not fit shares what is left by the rule declared for a tie, and what that rule cannot
  place reaches no later rank.\<close>

definition by_rank ::
  "('k \<Rightarrow> nat) \<Rightarrow> ('k set \<Rightarrow> ('k, 'n::linordered_idom) rule) \<Rightarrow> 'k set \<Rightarrow> ('k, 'n) rule" where
  "by_rank rank tie K v x = (\<lambda>k.
     if k \<notin> K then 0
     else (let left = x - ahead K rank v k; G = beside K rank k in
           if total G v \<le> left then v k
           else if left \<le> 0 then 0
           else if G = {k} then left
           else tie G (\<lambda>j. if j \<in> G then v j else 0) left k))"

definition tie_arises :: "'k set \<Rightarrow> ('k \<Rightarrow> nat) \<Rightarrow> ('k, 'n::linordered_idom) amounts \<Rightarrow> 'n \<Rightarrow> bool" where
  "tie_arises K rank v x \<longleftrightarrow>
     (\<exists>k\<in>K. 0 < x - ahead K rank v k \<and> x - ahead K rank v k < total (beside K rank k) v \<and> beside K rank k \<noteq> {k})"

text \<open>Requests that are of no use in part, such as blocks. In the declared order, given as a list,
  each request is granted whole where it fits what is left, and nothing otherwise. What no request
  fitted is the residual.\<close>

fun whole_each :: "'k list \<Rightarrow> ('k, 'n::linordered_idom) amounts \<Rightarrow> 'n \<Rightarrow> ('k, 'n) amounts" where
  "whole_each [] v x = nothing"
| "whole_each (k # ks) v x =
     (if v k \<le> x then (whole_each ks v (x - v k))(k := v k) else whole_each ks v x)"

section \<open>Rules over whole units\<close>

definition floor_part :: "int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "floor_part t K w k = (if k \<in> K then (t * w k) div (\<Sum>j\<in>K. w j) else 0)"

definition half_up_part :: "int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "half_up_part t K w k = (if k \<in> K then (2 * t * w k + (\<Sum>j\<in>K. w j)) div (2 * (\<Sum>j\<in>K. w j)) else 0)"

definition remainder :: "int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "remainder t K w k = (t * w k) mod (\<Sum>j\<in>K. w j)"

definition half_even_part :: "int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "half_even_part t K w k =
     (if k \<notin> K then 0
      else (let T = (\<Sum>j\<in>K. w j); q = (t * w k) div T; r = 2 * remainder t K w k in
            if r < T then q else if T < r then q + 1 else if even q then q else q + 1))"

definition short :: "int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> int" where
  "short t K base = t - (\<Sum>k\<in>K. base k)"

text \<open>A preference says which key takes a unit before which. Key k is placed among the first n of E
  where k and every key it is not preferred to number n or fewer. Keys the preference leaves level
  are placed together or not at all, so no key decides between them.\<close>

definition placed :: "'k set \<Rightarrow> ('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> int \<Rightarrow> 'k \<Rightarrow> bool" where
  "placed E pref n k \<longleftrightarrow> k \<in> E \<and> int (card {j\<in>E. \<not> pref k j}) \<le> n"

text \<open>One rule for whole units. The parts are a base, n is what the base leaves short (or over, where
  it is negative), a unit short goes to the keys placed by one preference and a unit over is taken
  from the keys placed by another. What the preference does not decide is left, and is the residual.\<close>

definition units ::
  "('k \<Rightarrow> int) \<Rightarrow> int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> 'k \<Rightarrow> int" where
  "units base n E gain L lose k =
     base k + (if 0 < n \<and> placed E gain n k then 1 else 0) - (if n < 0 \<and> placed L lose (- n) k then 1 else 0)"

definition first_in :: "('k \<Rightarrow> nat) \<Rightarrow> 'k \<Rightarrow> 'k \<Rightarrow> bool" where
  "first_in order j k \<longleftrightarrow> order j < order k"

definition larger_remainder :: "int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> 'k \<Rightarrow> bool" where
  "larger_remainder t K w j k \<longleftrightarrow> remainder t K w k < remainder t K w j"

definition then_by :: "('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> ('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> 'k \<Rightarrow> 'k \<Rightarrow> bool" where
  "then_by p q j k \<longleftrightarrow> p j k \<or> (\<not> p k j \<and> q j k)"

definition no_order :: "'k \<Rightarrow> 'k \<Rightarrow> bool" where
  "no_order j k \<longleftrightarrow> False"

text \<open>The two rules the vocabulary names. Each takes the keys that may take a unit, E, and the order
  the account declares for odd units. With no order declared, largest_remainder leaves the units
  that equal remainders do not decide.\<close>

definition to_first :: "('k \<Rightarrow> nat) \<Rightarrow> 'k set \<Rightarrow> int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "to_first order E t K w = units (floor_part t K w) (short t K (floor_part t K w)) E (first_in order) {} no_order"

definition largest_remainder :: "('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> 'k set \<Rightarrow> int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "largest_remainder tiebreak E t K w =
     units (floor_part t K w) (short t K (floor_part t K w)) E (then_by (larger_remainder t K w) tiebreak) {} no_order"

text \<open>Rounding to the nearest, where the wording says how the difference is settled. The rounded
  shares can sum to more than the amount or to less. A unit over is taken from a share rounded up,
  and a unit short goes to a share rounded down, so no share strays a whole unit from its exact value.\<close>

definition to_nearest ::
  "(int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int) \<Rightarrow> ('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> ('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "to_nearest part gain lose t K w =
     units (part t K w) (short t K (part t K w))
       {k\<in>K. part t K w k = floor_part t K w k \<and> 0 < remainder t K w k} gain
       {k\<in>K. floor_part t K w k < part t K w k} lose"

text \<open>In rationing a unit goes only to a claim not yet met in full. In apportionment every key the
  wording names may take one.\<close>

definition unmet :: "int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k set" where
  "unmet t K w = {k\<in>K. floor_part t K w k < w k}"

definition ration :: "('k set \<Rightarrow> int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int) \<Rightarrow> 'k set \<Rightarrow> ('k, int) rule" where
  "ration U K v x = U (unmet x K v) x K v"

definition apportion :: "('k set \<Rightarrow> int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int) \<Rightarrow> 'k set \<Rightarrow> ('k, int) rule" where
  "apportion U K w x = U K x K w"

section \<open>Accounts\<close>

type_synonym ('a, 'n) balances = "'a \<Rightarrow> 'n"

definition up :: "('a \<Rightarrow> 'a option) \<Rightarrow> ('a \<times> 'a) set" where
  "up parent = {(a, b). parent a = Some b}"

definition path :: "('a \<Rightarrow> 'a option) \<Rightarrow> 'a \<Rightarrow> 'a set" where
  "path parent a = {b. (a, b) \<in> (up parent)\<^sup>*}"

definition tree :: "'a set \<Rightarrow> ('a \<Rightarrow> 'a option) \<Rightarrow> bool" where
  "tree A parent \<longleftrightarrow> finite A \<and> (\<forall>a\<in>A. \<forall>b. parent a = Some b \<longrightarrow> b \<in> A) \<and> acyclic (up parent)"

text \<open>The path as a list, by following the parent at most n times, so what reads a path evaluates.\<close>

fun chain :: "nat \<Rightarrow> ('a \<Rightarrow> 'a option) \<Rightarrow> 'a \<Rightarrow> 'a list" where
  "chain 0 parent a = [a]"
| "chain (Suc n) parent a = (case parent a of None \<Rightarrow> [a] | Some b \<Rightarrow> a # chain n parent b)"

definition reach :: "('a \<Rightarrow> 'a option) \<Rightarrow> ('p \<Rightarrow> 'a set) \<Rightarrow> 'a \<Rightarrow> 'p option \<Rightarrow> 'a set" where
  "reach parent counts a purpose =
     path parent a \<union> (case purpose of None \<Rightarrow> {} | Some p \<Rightarrow> (\<Union>c\<in>counts p. path parent c))"

text \<open>What is available over a set of accounts, the path of one or the reach of a purpose.\<close>

definition least :: "('a, 'n::linordered_idom) balances \<Rightarrow> 'a set \<Rightarrow> 'n" where
  "least bal S = Min (bal ` S)"

definition available :: "('a \<Rightarrow> 'a option) \<Rightarrow> ('a, 'n::linordered_idom) balances \<Rightarrow> 'a \<Rightarrow> 'n" where
  "available parent bal a = least bal (path parent a)"

definition debit :: "'a set \<Rightarrow> 'n::linordered_idom \<Rightarrow> ('a, 'n) balances \<Rightarrow> ('a, 'n) balances" where
  "debit S x bal = (\<lambda>b. if b \<in> S then bal b - x else bal b)"

definition draw_on :: "'a set \<Rightarrow> 'n::linordered_idom \<Rightarrow> ('a, 'n) balances \<Rightarrow> ('a, 'n) balances \<times> bool" where
  "draw_on S x bal = (if 0 \<le> x \<and> (\<forall>b\<in>S. x \<le> bal b) then (debit S x bal, True) else (bal, False))"

definition draw ::
  "('a \<Rightarrow> 'a option) \<Rightarrow> ('p \<Rightarrow> 'a set) \<Rightarrow> 'a \<Rightarrow> 'p option \<Rightarrow> 'n::linordered_idom \<Rightarrow> ('a, 'n) balances \<Rightarrow> ('a, 'n) balances \<times> bool" where
  "draw parent counts a purpose x bal = draw_on (reach parent counts a purpose) x bal"

section \<open>A merge at one position\<close>

definition requested :: "('k \<times> 'n::linordered_idom) list \<Rightarrow> ('k, 'n) amounts" where
  "requested ps = (\<lambda>k. sum_list (map snd (filter (\<lambda>q. fst q = k) ps)))"

definition proposers :: "('k \<times> 'n) list \<Rightarrow> 'k set" where
  "proposers ps = fst ` set ps"

text \<open>What an account declares for a merge: whether requests beyond what is available are refused
  whole, whether the order is checked before any rule runs, the rule for requests of one rank, and
  whether a residual may be left.\<close>

record ('k, 'n) policy =
  refuses :: bool
  ranked :: bool
  tie :: "('k set \<Rightarrow> ('k, 'n) rule) option"
  leaves :: bool
  unmixed :: bool

datatype reason = Exceeds | Unranked | Tied | Undecided | Mixed | Crossing

datatype ('k, 'n) outcome = Granted "('k, 'n) amounts" 'n | Refused reason

definition merge_of ::
  "('k, 'n::linordered_idom) policy \<Rightarrow> ('k \<Rightarrow> nat) \<Rightarrow> 'n \<Rightarrow> 'k set \<Rightarrow> ('k, 'n) amounts \<Rightarrow> ('k, 'n) outcome" where
  "merge_of pol rank av K v =
     (let x = max 0 av in
      if total K v \<le> av then Granted v 0
      else if refuses pol then Refused Exceeds
      else if ranked pol \<and> \<not> inj_on rank K then Refused Unranked
      else (case tie pol of
              None \<Rightarrow>
                if tie_arises K rank v x then Refused Tied
                else (let g = by_rank rank (\<lambda>_ _ _. nothing) K v x in Granted g (x - total K g))
            | Some t \<Rightarrow>
                (let g = by_rank rank t K v x; r = x - total K g in
                 if r = 0 \<or> leaves pol then Granted g r else Refused Undecided)))"

definition merge ::
  "('k, 'n::linordered_idom) policy \<Rightarrow> ('k \<Rightarrow> nat) \<Rightarrow> 'n \<Rightarrow> ('k \<times> 'n) list \<Rightarrow> ('k, 'n) outcome" where
  "merge pol rank av ps = merge_of pol rank av (proposers ps) (requested ps)"

definition settle ::
  "('k, 'n::linordered_idom) policy \<Rightarrow> ('k \<Rightarrow> nat) \<Rightarrow> ('a \<Rightarrow> 'a option) \<Rightarrow> 'a \<Rightarrow> ('k \<times> 'n) list \<Rightarrow> ('a, 'n) balances
     \<Rightarrow> ('k, 'n) outcome \<times> ('a, 'n) balances" where
  "settle pol rank parent a ps bal =
     (case merge pol rank (available parent bal a) ps of
        Granted g r \<Rightarrow> (Granted g r, debit (path parent a) (total (proposers ps) g) bal)
      | Refused why \<Rightarrow> (Refused why, bal))"

section \<open>Requests with a purpose at one position\<close>

text \<open>A request may carry a purpose that accounts off the path count. Each account a request
  reaches limits the set of requests that reach it, and what is available to a set is the least its
  accounts hold. The sets are settled from the narrowest to the widest, each a merge of its requests
  as they then stand, so a request is cut to its own limits before it competes. The widest set is
  the path of the account drawn on, which every request reaches. A refusal at any set refuses the
  position. Two sets that overlap with neither inside the other have no such order, and the
  position is refused, as it is where the wording refuses a position of more than one purpose.\<close>

definition limited :: "'k set \<Rightarrow> ('k \<Rightarrow> 'a set) \<Rightarrow> 'a \<Rightarrow> 'k set" where
  "limited K R b = {k\<in>K. b \<in> R k}"

definition room :: "'k set \<Rightarrow> ('k \<Rightarrow> 'a set) \<Rightarrow> ('a, 'n::linordered_idom) balances \<Rightarrow> 'k set \<Rightarrow> 'n" where
  "room K R bal G = least bal {b. limited K R b = G}"

definition crossing :: "'k set \<Rightarrow> ('k \<Rightarrow> 'a set) \<Rightarrow> bool" where
  "crossing K R \<longleftrightarrow>
     (\<exists>b c. limited K R b \<inter> limited K R c \<noteq> {}
            \<and> \<not> limited K R b \<subseteq> limited K R c \<and> \<not> limited K R c \<subseteq> limited K R b)"

definition mixed :: "'k set \<Rightarrow> ('k \<Rightarrow> 'p option) \<Rightarrow> bool" where
  "mixed K purpose \<longleftrightarrow> (\<exists>j\<in>K. \<exists>k\<in>K. purpose j \<noteq> purpose k)"

definition narrowest_first :: "'k set list \<Rightarrow> bool" where
  "narrowest_first Gs \<longleftrightarrow> distinct Gs \<and> (\<forall>i<length Gs. \<forall>j<length Gs. Gs ! i \<subset> Gs ! j \<longrightarrow> i < j)"

fun admit ::
  "('k, 'n::linordered_idom) policy \<Rightarrow> ('k \<Rightarrow> nat) \<Rightarrow> ('k set \<times> 'n) list \<Rightarrow> ('k, 'n) amounts \<Rightarrow> 'n \<Rightarrow> ('k, 'n) outcome" where
  "admit pol rank [] v r = Granted v r"
| "admit pol rank ((G, x) # rest) v r =
     (case merge_of pol rank x G (\<lambda>k. if k \<in> G then v k else 0) of
        Refused why \<Rightarrow> Refused why
      | Granted g s \<Rightarrow> admit pol rank rest (\<lambda>k. if k \<in> G then g k else v k) (r + s))"

definition settle_purposes ::
  "('k, 'n::linordered_idom) policy \<Rightarrow> ('k \<Rightarrow> nat) \<Rightarrow> ('a \<Rightarrow> 'a option) \<Rightarrow> ('p \<Rightarrow> 'a set) \<Rightarrow> 'a \<Rightarrow> ('k \<Rightarrow> 'p option)
     \<Rightarrow> 'k set list \<Rightarrow> ('k \<times> 'n) list \<Rightarrow> ('a, 'n) balances \<Rightarrow> ('k, 'n) outcome \<times> ('a, 'n) balances" where
  "settle_purposes pol rank parent counts a purpose Gs ps bal =
     (let K = proposers ps; R = (\<lambda>k. reach parent counts a (purpose k)) in
      if unmixed pol \<and> mixed K purpose then (Refused Mixed, bal)
      else if crossing K R then (Refused Crossing, bal)
      else (case admit pol rank (map (\<lambda>G. (G, room K R bal G)) Gs) (requested ps) 0 of
              Refused why \<Rightarrow> (Refused why, bal)
            | Granted g r \<Rightarrow> (Granted g r, (\<lambda>b. bal b - total (limited K R b) g))))"

section \<open>Ranks that hold an amount of their own\<close>

text \<open>Pots under one fund, settled in rank order. What a pot could not place is carried down the
  list and withheld from what the later pots see of the fund and of every account above it, since
  any of them may be the one that binds. A refusal at any pot refuses them all.\<close>

fun pots ::
  "('k, 'n::linordered_idom) policy \<Rightarrow> ('k \<Rightarrow> nat) \<Rightarrow> ('a \<Rightarrow> 'a option) \<Rightarrow> 'a \<Rightarrow> ('a \<times> ('k \<times> 'n) list) list \<Rightarrow> 'n
     \<Rightarrow> ('a, 'n) balances \<Rightarrow> (('k, 'n) amounts list \<times> 'n \<times> ('a, 'n) balances) option" where
  "pots pol rank parent fund [] held bal = Some ([], held, bal)"
| "pots pol rank parent fund ((a, ps) # rest) held bal =
     (case merge pol rank (available parent (debit (path parent fund) held bal) a) ps of
        Refused why \<Rightarrow> None
      | Granted g r \<Rightarrow>
          (case pots pol rank parent fund rest (held + r) (debit (path parent a) (total (proposers ps) g) bal) of
             None \<Rightarrow> None
           | Some (gs, h, bal') \<Rightarrow> Some (g # gs, h, bal')))"

section \<open>One amount allocated across accounts\<close>

text \<open>Each account in turn is charged what its rule grants of what is still asked. The accounts
  charged for an account are its path, or the reach of the amount's purpose.\<close>

fun spread ::
  "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> ('a \<Rightarrow> 'a set) \<Rightarrow> 'a list \<Rightarrow> ('a, 'n) balances \<Rightarrow> ('k, 'n) amounts
     \<Rightarrow> ('k, 'n) amounts list \<times> ('k, 'n) amounts \<times> ('a, 'n) balances" where
  "spread K R charged [] bal v = ([], v, bal)"
| "spread K R charged (a # rest) bal v =
     (let p = R v (min (total K v) (max 0 (least bal (charged a))))
      in case spread K R charged rest (debit (charged a) (total K p) bal) (less v p) of
           (ps, r, bal') \<Rightarrow> (p # ps, r, bal'))"

text \<open>Where the wording refuses a shortfall, the allocation is whole or it changes nothing.\<close>

definition spread_whole ::
  "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> ('a \<Rightarrow> 'a set) \<Rightarrow> 'a list \<Rightarrow> ('a, 'n) balances \<Rightarrow> ('k, 'n) amounts
     \<Rightarrow> (('k, 'n) amounts list \<times> ('a, 'n) balances) option" where
  "spread_whole K R charged as bal v =
     (case spread K R charged as bal v of (ps, r, bal') \<Rightarrow> if total K r = 0 then Some (ps, bal') else None)"

section \<open>Credits, and what a posting records\<close>

text \<open>A credit is applied at the account it is posted to, up to that account's room. Each ancestor
  that accepts its kind takes the least of the amount applied and its own room, and where it takes
  less the difference is a cut at that ancestor.\<close>

definition credit ::
  "('a \<Rightarrow> 'a option) \<Rightarrow> ('a, 'n::linordered_idom) balances \<Rightarrow> ('a \<Rightarrow> bool) \<Rightarrow> 'a \<Rightarrow> 'n \<Rightarrow> ('a, 'n) balances
     \<Rightarrow> 'n \<times> ('a, 'n) amounts \<times> ('a, 'n) balances" where
  "credit parent cap accepts a x bal =
     (let applied = max 0 (min x (cap a - bal a));
          take = (\<lambda>b. if b \<in> path parent a \<and> accepts b then min applied (cap b - bal b) else 0)
      in (applied,
          (\<lambda>b. if b \<in> path parent a \<and> accepts b then applied - take b else 0),
          (\<lambda>b. bal b + take b)))"

record ('a, 'c, 'n) book =
  parent_of :: "'a \<Rightarrow> 'a option"
  stated :: "'a \<Rightarrow> 'n"
  ceiling :: "'a \<Rightarrow> 'n"
  restores :: "'a \<Rightarrow> 'c option \<Rightarrow> bool"
  refusing :: "'a \<Rightarrow> bool"

datatype ('a, 'c, 'n) request = Draw 'a 'n | Restore 'a "'c option" 'n

text \<open>A posting keeps what was offered, what was applied and the cuts.\<close>

datatype ('a, 'c, 'n) posted = Drawn 'a 'n | Restored 'a "'c option" 'n 'n "('a, 'n) amounts"

definition post ::
  "('a, 'c, 'n::linordered_idom) book \<Rightarrow> ('a, 'c, 'n) request \<Rightarrow> ('a, 'n) balances
     \<Rightarrow> ('a, 'c, 'n) posted option \<times> ('a, 'n) balances" where
  "post B q bal =
     (case q of
        Draw a x \<Rightarrow>
          (case draw_on (path (parent_of B) a) x bal of (bal', ok) \<Rightarrow> (if ok then Some (Drawn a x) else None, bal'))
      | Restore a c x \<Rightarrow>
          (if restores B a c then
             (case credit (parent_of B) (ceiling B) (\<lambda>b. restores B b c) a x bal of
                (applied, cuts, bal') \<Rightarrow> (Some (Restored a c x applied cuts), bal'))
           else (None, bal)))"

fun run ::
  "('a, 'c, 'n::linordered_idom) book \<Rightarrow> ('a, 'c, 'n) request list \<Rightarrow> ('a, 'n) balances
     \<Rightarrow> ('a, 'c, 'n) posted list \<times> ('a, 'n) balances" where
  "run B [] bal = ([], bal)"
| "run B (q # qs) bal =
     (case post B q bal of
        (p, bal') \<Rightarrow> (case run B qs bal' of (ps, bal'') \<Rightarrow> ((case p of None \<Rightarrow> ps | Some e \<Rightarrow> e # ps), bal'')))"

text \<open>What one posting moves an account by, read from what the posting records.\<close>

definition moved :: "('a, 'c, 'n::linordered_idom) book \<Rightarrow> ('a, 'c, 'n) posted \<Rightarrow> 'a \<Rightarrow> 'n" where
  "moved B p b =
     (case p of
        Drawn a x \<Rightarrow> (if b \<in> path (parent_of B) a then - x else 0)
      | Restored a c x applied cuts \<Rightarrow> (if b \<in> path (parent_of B) a \<and> restores B b c then applied - cuts b else 0))"

text \<open>A balance as a sum: the stated amount, less the debits, plus the credits applied, less the cuts.\<close>

definition summed :: "('a, 'c, 'n::linordered_idom) book \<Rightarrow> ('a, 'c, 'n) posted list \<Rightarrow> 'a \<Rightarrow> 'n" where
  "summed B ps b = stated B b + sum_list (map (\<lambda>p. moved B p b) ps)"

section \<open>Readings by effective day\<close>

text \<open>A history is the postings in recorded order, each with its effective day. A recording is a
  length of that list. The postings counted for a day and a recording are those recorded by the
  recording and effective by the day.\<close>

definition counted :: "nat \<Rightarrow> nat \<Rightarrow> (nat \<times> 'e) list \<Rightarrow> (nat \<times> 'e) list" where
  "counted day recording es = filter (\<lambda>e. fst e \<le> day) (take recording es)"

text \<open>Reading A, the recorded amounts placed on their effective days.\<close>

definition reading_a ::
  "('a, 'c, 'n::linordered_idom) book \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> (nat \<times> ('a, 'c, 'n) posted) list \<Rightarrow> 'a \<Rightarrow> 'n" where
  "reading_a B day recording es b = summed B (map snd (counted day recording es)) b"

text \<open>Reading B, the same postings settled again in effective order, by each account's own policy.
  A debit that no longer fits is refused where its account refuses and cut to what is available
  where it rations, so the reading never shows a balance an account could not hold.\<close>

definition asked :: "('a, 'c, 'n) posted \<Rightarrow> ('a, 'c, 'n) request" where
  "asked p = (case p of Drawn a x \<Rightarrow> Draw a x | Restored a c x applied cuts \<Rightarrow> Restore a c x)"

fun replay ::
  "('a, 'c, 'n::linordered_idom) book \<Rightarrow> ('a, 'c, 'n) request list \<Rightarrow> ('a, 'n) balances \<Rightarrow> ('a, 'n) balances" where
  "replay B [] bal = bal"
| "replay B (Draw a x # qs) bal =
     replay B qs
       (if x \<le> available (parent_of B) bal a then debit (path (parent_of B) a) x bal
        else if refusing B a then bal
        else debit (path (parent_of B) a) (max 0 (available (parent_of B) bal a)) bal)"
| "replay B (Restore a c x # qs) bal =
     replay B qs (snd (snd (credit (parent_of B) (ceiling B) (\<lambda>b. restores B b c) a x bal)))"

definition reading_b ::
  "('a, 'c, 'n::linordered_idom) book \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> (nat \<times> ('a, 'c, 'n) posted) list \<Rightarrow> 'a \<Rightarrow> 'n" where
  "reading_b B day recording es b =
     replay B (map (asked \<circ> snd) (sort_key fst (counted day recording es))) (stated B) b"

text \<open>Reading C, the flows: what was drawn, and what was offered in credits the account accepts.\<close>

definition flows ::
  "('a, 'c, 'n::linordered_idom) book \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> (nat \<times> ('a, 'c, 'n) posted) list \<Rightarrow> 'a \<Rightarrow> 'n \<times> 'n" where
  "flows B day recording es b =
     (let ps = map snd (counted day recording es) in
      (sum_list (map (\<lambda>p. case p of Drawn a x \<Rightarrow> (if b \<in> path (parent_of B) a then x else 0) | Restored a c x applied cuts \<Rightarrow> 0) ps),
       sum_list (map (\<lambda>p. case p of Drawn a x \<Rightarrow> 0
                              | Restored a c x applied cuts \<Rightarrow> (if b \<in> path (parent_of B) a \<and> restores B b c then x else 0)) ps)))"

section \<open>Examples, evaluated\<close>

text \<open>Three requests of 5 share 10 units. With no order declared each takes 3 and 1 is left. With an
  order declared for odd units, the first in it takes the unit.\<close>

lemma "map (ration (largest_remainder no_order) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3] = [3, 3, 3]"
  by eval

lemma "map (ration (largest_remainder (first_in (\<lambda>k. 3 - k))) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3] = [3, 3, 4]"
  by eval

lemma "map (ration (to_first id) {1, 2, 3::nat} (\<lambda>_. 5) 10) [1, 2, 3] = [4, 3, 3]"
  by eval

text \<open>Two ranks, the first of three requests of 5 and the second one request of 3, with 10 units.
  The unit the first rank cannot place does not reach the second.\<close>

lemma "map (by_rank (\<lambda>k. if k = 4 then 1 else 0) (ration (largest_remainder no_order)) {1, 2, 3, 4::nat}
              (\<lambda>k. if k = 4 then 3 else 5) 10) [1, 2, 3, 4] = [3, 3, 3, 0]"
  by eval

text \<open>Blocks: with 7 units and requests of 5 and 4 in that order, the first is granted whole, the
  second nothing, and 2 are left.\<close>

lemma "map (whole_each [1, 2::nat] (\<lambda>k. if k = 1 then 5 else 4) (7::int)) [1, 2] = [5, 0]"
  by eval

text \<open>Distinct ranks are priority: 7 units to requests of 5 and 4.\<close>

lemma "map (by_rank id (\<lambda>_ _ _. nothing) {1, 2::nat} (\<lambda>k. if k = 1 then 5 else 4) (7::int)) [1, 2] = [5, 2]"
  by eval

end
