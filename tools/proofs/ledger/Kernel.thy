(* SPDX-License-Identifier: MPL-2.0 *)

theory Kernel
imports Complex_Main
begin

type_synonym amount = rat

type_synonym 'k amounts = "'k \<Rightarrow> amount"

definition total :: "'k set \<Rightarrow> 'k amounts \<Rightarrow> amount" where
  "total K v = (\<Sum>k\<in>K. v k)"

definition nothing :: "'k amounts" where
  "nothing = (\<lambda>_. 0)"

definition less :: "'k amounts \<Rightarrow> 'k amounts \<Rightarrow> 'k amounts" where
  "less v w = (\<lambda>k. v k - w k)"

definition fits_in :: "'k amounts \<Rightarrow> 'k amounts \<Rightarrow> bool" where
  "fits_in v w \<longleftrightarrow> (\<forall>k. v k \<le> w k)"

definition nonneg_on :: "'k set \<Rightarrow> 'k amounts \<Rightarrow> bool" where
  "nonneg_on K v \<longleftrightarrow> (\<forall>k. 0 \<le> v k) \<and> (\<forall>k. k \<notin> K \<longrightarrow> v k = 0)"

type_synonym 'k rule = "'k amounts \<Rightarrow> amount \<Rightarrow> 'k amounts"

definition lawful :: "'k set \<Rightarrow> 'k rule \<Rightarrow> bool" where
  "lawful K R \<longleftrightarrow>
     (\<forall>v x. nonneg_on K v \<and> 0 \<le> x \<and> x \<le> total K v \<longrightarrow>
        total K (R v x) = x \<and> fits_in (R v x) v \<and> nonneg_on K (R v x))
     \<and> (\<forall>v. nonneg_on K v \<longrightarrow> R v (total K v) = v)"

definition proportional :: "'k set \<Rightarrow> 'k rule" where
  "proportional K v x = (\<lambda>k. if k \<notin> K \<or> total K v = 0 then 0 else x * v k / total K v)"

definition ahead :: "'k::linorder set \<Rightarrow> 'k amounts \<Rightarrow> 'k \<Rightarrow> amount" where
  "ahead K v k = (\<Sum>j\<in>{j\<in>K. j < k}. v j)"

definition in_priority :: "'k::linorder set \<Rightarrow> 'k rule" where
  "in_priority K v x = (\<lambda>k. if k \<in> K then max 0 (min (v k) (x - ahead K v k)) else 0)"

type_synonym 'a balances = "'a \<Rightarrow> amount"

definition up :: "('a \<Rightarrow> 'a option) \<Rightarrow> ('a \<times> 'a) set" where
  "up parent = {(a, b). parent a = Some b}"

definition path :: "('a \<Rightarrow> 'a option) \<Rightarrow> 'a \<Rightarrow> 'a set" where
  "path parent a = {b. (a, b) \<in> (up parent)\<^sup>*}"

definition tree :: "'a set \<Rightarrow> ('a \<Rightarrow> 'a option) \<Rightarrow> bool" where
  "tree A parent \<longleftrightarrow> finite A \<and> (\<forall>a\<in>A. \<forall>b. parent a = Some b \<longrightarrow> b \<in> A) \<and> acyclic (up parent)"

definition available :: "('a \<Rightarrow> 'a option) \<Rightarrow> 'a balances \<Rightarrow> 'a \<Rightarrow> amount" where
  "available parent bal a = Min (bal ` path parent a)"

definition debit :: "'a set \<Rightarrow> amount \<Rightarrow> 'a balances \<Rightarrow> 'a balances" where
  "debit S x bal = (\<lambda>b. if b \<in> S then bal b - x else bal b)"

definition draw_on :: "'a set \<Rightarrow> amount \<Rightarrow> 'a balances \<Rightarrow> 'a balances \<times> bool" where
  "draw_on S x bal = (if 0 \<le> x \<and> (\<forall>b\<in>S. x \<le> bal b) then (debit S x bal, True) else (bal, False))"

definition reach :: "('a \<Rightarrow> 'a option) \<Rightarrow> ('p \<Rightarrow> 'a set) \<Rightarrow> 'a \<Rightarrow> 'p option \<Rightarrow> 'a set" where
  "reach parent counts a purpose =
     path parent a \<union> (case purpose of None \<Rightarrow> {} | Some p \<Rightarrow> (\<Union>c\<in>counts p. path parent c))"

definition draw :: "('a \<Rightarrow> 'a option) \<Rightarrow> ('p \<Rightarrow> 'a set) \<Rightarrow> 'a \<Rightarrow> 'p option \<Rightarrow> amount \<Rightarrow> 'a balances \<Rightarrow> 'a balances \<times> bool" where
  "draw parent counts a purpose x bal = draw_on (reach parent counts a purpose) x bal"

definition credit :: "('a \<Rightarrow> 'a option) \<Rightarrow> 'a balances \<Rightarrow> 'a \<Rightarrow> amount \<Rightarrow> 'a balances \<Rightarrow> 'a balances" where
  "credit parent cap a x bal = (\<lambda>b. if b \<in> path parent a then min (cap b) (bal b + x) else bal b)"

type_synonym position = "nat \<times> nat"

definition before :: "position \<Rightarrow> position \<Rightarrow> bool" where
  "before p q \<longleftrightarrow> fst p < fst q \<or> (fst p = fst q \<and> snd p < snd q)"

definition requested :: "('k \<times> amount) list \<Rightarrow> 'k amounts" where
  "requested ps = (\<lambda>k. sum_list (map snd (filter (\<lambda>q. fst q = k) ps)))"

definition proposers :: "('k \<times> amount) list \<Rightarrow> 'k set" where
  "proposers ps = fst ` set ps"

definition merge :: "('k set \<Rightarrow> 'k rule) \<Rightarrow> amount \<Rightarrow> ('k \<times> amount) list \<Rightarrow> 'k amounts" where
  "merge rule av ps =
     (if total (proposers ps) (requested ps) \<le> av then requested ps
      else rule (proposers ps) (requested ps) (max 0 av))"

definition settle_at ::
  "('k::linorder set \<Rightarrow> 'k rule) \<Rightarrow> ('a \<Rightarrow> 'a option) \<Rightarrow> 'a \<Rightarrow> ('k \<times> amount) list \<Rightarrow> 'a balances
     \<Rightarrow> ('k \<times> amount) list \<times> 'a balances" where
  "settle_at rule parent a ps bal =
     (let g = merge rule (available parent bal a) ps
      in (map (\<lambda>k. (k, g k)) (sorted_list_of_set (proposers ps)),
          debit (path parent a) (total (proposers ps) g) bal))"

fun spread ::
  "'k set \<Rightarrow> 'k rule \<Rightarrow> ('a \<Rightarrow> 'a option) \<Rightarrow> 'a list \<Rightarrow> 'a balances \<Rightarrow> 'k amounts
     \<Rightarrow> 'k amounts list \<times> 'k amounts \<times> 'a balances" where
  "spread K R parent [] bal v = ([], v, bal)"
| "spread K R parent (a # rest) bal v =
     (let x = min (total K v) (max 0 (available parent bal a)); p = R v x
      in case spread K R parent rest (debit (path parent a) x bal) (less v p) of
           (ps, r, bal') \<Rightarrow> (p # ps, r, bal'))"

definition shares_ok :: "'q set \<Rightarrow> nat \<Rightarrow> (nat \<Rightarrow> 'q \<Rightarrow> rat) \<Rightarrow> bool" where
  "shares_ok Q n S \<longleftrightarrow> (\<forall>i<n. (\<Sum>q\<in>Q. S i q) = 1) \<and> (\<forall>i q. 0 \<le> S i q)"

definition attributed :: "'k set \<Rightarrow> (nat \<Rightarrow> 'q \<Rightarrow> rat) \<Rightarrow> 'k amounts list \<Rightarrow> 'q \<Rightarrow> amount" where
  "attributed K S ps q = (\<Sum>i<length ps. S i q * total K (ps ! i))"

definition floor_part :: "int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "floor_part t K w k = (if k \<in> K then (t * w k) div (\<Sum>j\<in>K. w j) else 0)"

definition leftover :: "int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> int" where
  "leftover t K w = t - (\<Sum>k\<in>K. floor_part t K w k)"

definition to_first :: "int \<Rightarrow> 'k::linorder set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "to_first t K w k =
     floor_part t K w k
     + (if k \<in> set (take (nat (leftover t K w)) (sorted_list_of_set K)) then 1 else 0)"

definition weights :: "('k \<times> int) list \<Rightarrow> 'k \<Rightarrow> int" where
  "weights ps = (\<lambda>k. sum_list (map snd (filter (\<lambda>q. fst q = k) ps)))"

definition remainder :: "int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "remainder t K w k = (t * w k) mod (\<Sum>j\<in>K. w j)"

definition largest_remainder :: "int \<Rightarrow> 'k::linorder set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int" where
  "largest_remainder t K w k =
     floor_part t K w k
     + (if k \<in> set (take (nat (leftover t K w))
                       (sort_key (\<lambda>j. - remainder t K w j) (sorted_list_of_set K))) then 1 else 0)"

fun spread_int ::
  "'k set \<Rightarrow> (int \<Rightarrow> 'k set \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> 'k \<Rightarrow> int) \<Rightarrow> ('a \<Rightarrow> 'a option) \<Rightarrow> 'a list
     \<Rightarrow> ('a \<Rightarrow> int) \<Rightarrow> ('k \<Rightarrow> int) \<Rightarrow> ('k \<Rightarrow> int) list \<times> ('k \<Rightarrow> int) \<times> ('a \<Rightarrow> int)" where
  "spread_int K R parent [] bal v = ([], v, bal)"
| "spread_int K R parent (a # rest) bal v =
     (let x = min (\<Sum>k\<in>K. v k) (max 0 (Min (bal ` path parent a))); p = R x K v
      in case spread_int K R parent rest (\<lambda>b. if b \<in> path parent a then bal b - x else bal b)
                (\<lambda>k. v k - p k) of
           (ps, r, bal') \<Rightarrow> (p # ps, r, bal'))"

end
