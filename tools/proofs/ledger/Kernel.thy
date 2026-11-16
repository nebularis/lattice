(* SPDX-License-Identifier: MPL-2.0 *)

theory Kernel
imports Complex_Main
begin

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

type_synonym ('k, 'n) rule = "('k, 'n) amounts \<Rightarrow> 'n \<Rightarrow> ('k, 'n) amounts"

definition rations :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> bool" where
  "rations K R \<longleftrightarrow>
     (\<forall>v x. nonneg_on K v \<and> 0 \<le> x \<and> x \<le> total K v \<longrightarrow>
        nonneg_on K (R v x) \<and> fits_in (R v x) v \<and> total K (R v x) \<le> x)
     \<and> (\<forall>v. nonneg_on K v \<longrightarrow> R v (total K v) = v)"

definition residual :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> ('k, 'n) amounts \<Rightarrow> 'n \<Rightarrow> 'n" where
  "residual K R v x = x - total K (R v x)"

definition exact :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> bool" where
  "exact K R \<longleftrightarrow> (\<forall>v x. nonneg_on K v \<and> 0 \<le> x \<and> x \<le> total K v \<longrightarrow> residual K R v x = 0)"

definition lawful :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> bool" where
  "lawful K R \<longleftrightarrow> rations K R \<and> exact K R"

definition apportions :: "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> bool" where
  "apportions K R \<longleftrightarrow>
     (\<forall>w x. nonneg_on K w \<and> 0 < total K w \<and> 0 \<le> x \<longrightarrow> nonneg_on K (R w x) \<and> total K (R w x) = x)
     \<and> (\<forall>w. nonneg_on K w \<longrightarrow> R w (total K w) = w)"

definition proportional :: "'k set \<Rightarrow> ('k, 'n::linordered_field) rule" where
  "proportional K v x = (\<lambda>k. if k \<notin> K \<or> total K v = 0 then 0 else x * v k / total K v)"

definition ahead :: "'k set \<Rightarrow> ('k \<Rightarrow> nat) \<Rightarrow> ('k, 'n::linordered_idom) amounts \<Rightarrow> 'k \<Rightarrow> 'n" where
  "ahead K rank v k = (\<Sum>j\<in>{j\<in>K. rank j < rank k}. v j)"

definition beside :: "'k set \<Rightarrow> ('k \<Rightarrow> nat) \<Rightarrow> 'k \<Rightarrow> 'k set" where
  "beside K rank k = {j\<in>K. rank j = rank k}"

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

fun whole_each :: "'k list \<Rightarrow> ('k, 'n::linordered_idom) amounts \<Rightarrow> 'n \<Rightarrow> ('k, 'n) amounts" where
  "whole_each [] v x = nothing"
| "whole_each (k # ks) v x =
     (if v k \<le> x then (whole_each ks v (x - v k))(k := v k) else whole_each ks v x)"

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

definition placed :: "'k set \<Rightarrow> ('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> int \<Rightarrow> 'k \<Rightarrow> bool" where
  "placed E pref n k \<longleftrightarrow> k \<in> E \<and> int (card {j\<in>E. \<not> pref k j}) \<le> n"

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

definition to_first :: "('k \<Rightarrow> nat) \<Rightarrow> 'k set \<Rightarrow> int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "to_first order E t K w = units (floor_part t K w) (short t K (floor_part t K w)) E (first_in order) {} no_order"

definition largest_remainder :: "('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> 'k set \<Rightarrow> int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "largest_remainder tiebreak E t K w =
     units (floor_part t K w) (short t K (floor_part t K w)) E (then_by (larger_remainder t K w) tiebreak) {} no_order"

definition to_nearest ::
  "(int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int) \<Rightarrow> ('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> ('k \<Rightarrow> 'k \<Rightarrow> bool) \<Rightarrow> int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "to_nearest part gain lose t K w =
     units (part t K w) (short t K (part t K w))
       {k\<in>K. part t K w k = floor_part t K w k \<and> 0 < remainder t K w k} gain
       {k\<in>K. floor_part t K w k < part t K w k} lose"

definition unmet :: "int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k set" where
  "unmet t K w = {k\<in>K. floor_part t K w k < w k}"

definition ration :: "('k set \<Rightarrow> int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int) \<Rightarrow> 'k set \<Rightarrow> ('k, int) rule" where
  "ration U K v x = U (unmet x K v) x K v"

definition apportion :: "('k set \<Rightarrow> int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int) \<Rightarrow> 'k set \<Rightarrow> ('k, int) rule" where
  "apportion U K w x = U K x K w"

type_synonym ('a, 'n) balances = "'a \<Rightarrow> 'n"

definition up :: "('a \<Rightarrow> 'a option) \<Rightarrow> ('a \<times> 'a) set" where
  "up parent = {(a, b). parent a = Some b}"

definition path :: "('a \<Rightarrow> 'a option) \<Rightarrow> 'a \<Rightarrow> 'a set" where
  "path parent a = {b. (a, b) \<in> (up parent)\<^sup>*}"

definition tree :: "'a set \<Rightarrow> ('a \<Rightarrow> 'a option) \<Rightarrow> bool" where
  "tree A parent \<longleftrightarrow> finite A \<and> (\<forall>a\<in>A. \<forall>b. parent a = Some b \<longrightarrow> b \<in> A) \<and> acyclic (up parent)"

fun chain :: "nat \<Rightarrow> ('a \<Rightarrow> 'a option) \<Rightarrow> 'a \<Rightarrow> 'a list" where
  "chain 0 parent a = [a]"
| "chain (Suc n) parent a = (case parent a of None \<Rightarrow> [a] | Some b \<Rightarrow> a # chain n parent b)"

definition reach :: "('a \<Rightarrow> 'a option) \<Rightarrow> ('p \<Rightarrow> 'a set) \<Rightarrow> 'a \<Rightarrow> 'p option \<Rightarrow> 'a set" where
  "reach parent counts a purpose =
     path parent a \<union> (case purpose of None \<Rightarrow> {} | Some p \<Rightarrow> (\<Union>c\<in>counts p. path parent c))"

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

definition requested :: "('k \<times> 'n::linordered_idom) list \<Rightarrow> ('k, 'n) amounts" where
  "requested ps = (\<lambda>k. sum_list (map snd (filter (\<lambda>q. fst q = k) ps)))"

definition proposers :: "('k \<times> 'n) list \<Rightarrow> 'k set" where
  "proposers ps = fst ` set ps"

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

fun spread ::
  "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> ('a \<Rightarrow> 'a set) \<Rightarrow> 'a list \<Rightarrow> ('a, 'n) balances \<Rightarrow> ('k, 'n) amounts
     \<Rightarrow> ('k, 'n) amounts list \<times> ('k, 'n) amounts \<times> ('a, 'n) balances" where
  "spread K R charged [] bal v = ([], v, bal)"
| "spread K R charged (a # rest) bal v =
     (let p = R v (min (total K v) (max 0 (least bal (charged a))))
      in case spread K R charged rest (debit (charged a) (total K p) bal) (less v p) of
           (ps, r, bal') \<Rightarrow> (p # ps, r, bal'))"

definition spread_whole ::
  "'k set \<Rightarrow> ('k, 'n::linordered_idom) rule \<Rightarrow> ('a \<Rightarrow> 'a set) \<Rightarrow> 'a list \<Rightarrow> ('a, 'n) balances \<Rightarrow> ('k, 'n) amounts
     \<Rightarrow> (('k, 'n) amounts list \<times> ('a, 'n) balances) option" where
  "spread_whole K R charged as bal v =
     (case spread K R charged as bal v of (ps, r, bal') \<Rightarrow> if total K r = 0 then Some (ps, bal') else None)"

definition shares_ok :: "'q set \<Rightarrow> nat \<Rightarrow> (nat \<Rightarrow> ('q, 'n::linordered_idom) amounts) \<Rightarrow> bool" where
  "shares_ok Q n basis \<longleftrightarrow> (\<forall>i<n. nonneg_on Q (basis i) \<and> 0 < total Q (basis i))"

definition attributed ::
  "'k set \<Rightarrow> ('q, 'n::linordered_idom) rule \<Rightarrow> (nat \<Rightarrow> ('q, 'n) amounts) \<Rightarrow> ('k, 'n) amounts list \<Rightarrow> 'q \<Rightarrow> 'n" where
  "attributed K R basis ps q = (\<Sum>i<length ps. R (basis i) (total K (ps ! i)) q)"

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

datatype ('a, 'c, 'n) posted = Drawn 'a 'n | Restored 'a "'c option" 'n 'n "('a, 'n) amounts"

definition post ::
  "('a, 'c, 'n::linordered_idom) book \<Rightarrow> ('a, 'c, 'n) request \<Rightarrow> ('a, 'n) balances
     \<Rightarrow> ('a, 'c, 'n) posted option \<times> ('a, 'n) balances" where
  "post B q bal =
     (case q of
        Draw a x \<Rightarrow>
          (case draw_on (path (parent_of B) a) x bal of (bal', ok) \<Rightarrow> (if ok then Some (Drawn a x) else None, bal'))
      | Restore a c x \<Rightarrow>
          (case credit (parent_of B) (ceiling B) (\<lambda>b. restores B b c) a x bal of
             (applied, cuts, bal') \<Rightarrow> (Some (Restored a c x applied cuts), bal')))"

fun run ::
  "('a, 'c, 'n::linordered_idom) book \<Rightarrow> ('a, 'c, 'n) request list \<Rightarrow> ('a, 'n) balances
     \<Rightarrow> ('a, 'c, 'n) posted list \<times> ('a, 'n) balances" where
  "run B [] bal = ([], bal)"
| "run B (q # qs) bal =
     (case post B q bal of
        (p, bal') \<Rightarrow> (case run B qs bal' of (ps, bal'') \<Rightarrow> ((case p of None \<Rightarrow> ps | Some e \<Rightarrow> e # ps), bal'')))"

definition moved :: "('a, 'c, 'n::linordered_idom) book \<Rightarrow> ('a, 'c, 'n) posted \<Rightarrow> 'a \<Rightarrow> 'n" where
  "moved B p b =
     (case p of
        Drawn a x \<Rightarrow> (if b \<in> path (parent_of B) a then - x else 0)
      | Restored a c x applied cuts \<Rightarrow> (if b \<in> path (parent_of B) a \<and> restores B b c then applied - cuts b else 0))"

definition summed :: "('a, 'c, 'n::linordered_idom) book \<Rightarrow> ('a, 'c, 'n) posted list \<Rightarrow> 'a \<Rightarrow> 'n" where
  "summed B ps b = stated B b + sum_list (map (\<lambda>p. moved B p b) ps)"

definition counted :: "nat \<Rightarrow> nat \<Rightarrow> (nat \<times> 'e) list \<Rightarrow> (nat \<times> 'e) list" where
  "counted day recording es = filter (\<lambda>e. fst e \<le> day) (take recording es)"

definition reading_a ::
  "('a, 'c, 'n::linordered_idom) book \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> (nat \<times> ('a, 'c, 'n) posted) list \<Rightarrow> 'a \<Rightarrow> 'n" where
  "reading_a B day recording es b = summed B (map snd (counted day recording es)) b"

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

definition flows ::
  "('a, 'c, 'n::linordered_idom) book \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> (nat \<times> ('a, 'c, 'n) posted) list \<Rightarrow> 'a \<Rightarrow> 'n \<times> 'n" where
  "flows B day recording es b =
     (let ps = map snd (counted day recording es) in
      (sum_list (map (\<lambda>p. case p of Drawn a x \<Rightarrow> (if b \<in> path (parent_of B) a then x else 0) | Restored a c x applied cuts \<Rightarrow> 0) ps),
       sum_list (map (\<lambda>p. case p of Drawn a x \<Rightarrow> 0
                              | Restored a c x applied cuts \<Rightarrow> (if b \<in> path (parent_of B) a \<and> restores B b c then x else 0)) ps)))"

end
