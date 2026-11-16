# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Writes `Cases.thy`, which has Isabelle evaluate the definitions of `Target.thy` on generated inputs and compare each result with what `model.py` computes for the same input.

The model is a transliteration by hand, so a slip in it and in a law's statement together would go unseen. This ties the two: where the theory and the model disagree on any case, the
theory's build fails at that lemma. Run it with `mise exec -- python spikes/ledger-target-kernel/cases.py`, then build the session. The seeds are fixed, so the file it writes is the
file that is committed."""

from __future__ import annotations

import random
from fractions import Fraction
from pathlib import Path

import model as m

HERE = Path(__file__).resolve().parent
CHUNK = 10  # cases a lemma, since Isabelle reads one long term far more slowly than several short ones
REASON = {"exceeds": "Exceeds", "unranked": "Unranked", "tied": "Tied", "undecided": "Undecided", "mixed": "Mixed", "crossing": "Crossing"}


def num(x):
    if isinstance(x, Fraction) and x.denominator != 1:
        return f"({x.numerator} / {x.denominator})" if x >= 0 else f"(- {-x.numerator} / {x.denominator})"
    x = int(x)
    return str(x) if x >= 0 else f"(- {-x})"


def lst(items, of=num):
    return "[" + ", ".join(of(i) for i in items) + "]"


def fn(pairs, key, value, of=num, key_of=str):
    """A function given by its table, zero elsewhere."""
    return f"(fn ({lst(pairs, lambda kv: f'({key_of(kv[0])}, {of(kv[1])})')} :: (({key}) * ({value})) list))"


def table(pairs, key, value, of, key_of=str):
    return f"(map_of ({lst(pairs, lambda kv: f'({key_of(kv[0])}, {of(kv[1])})')} :: (({key}) * ({value})) list))"


def keyset(ks):
    return f"(set ({lst(ks, str)} :: nat list))"


def shown(outcome, keys):
    if outcome[0] == "refused":
        return f"([], 0, Some {REASON[outcome[1]]})"
    return f"({lst([outcome[1][k] for k in keys])}, {num(outcome[2])}, None)"


def policy(refuses, ranked, tie, leaves, unmixed, n):
    rule = {None: "None", "units": "Some (ration (largest_remainder no_order))", "exact": "Some proportional"}[tie]
    return f"((| refuses = {refuses}, ranked = {ranked}, tie = {rule}, leaves = {leaves}, unmixed = {unmixed} |) :: (nat, {n}) policy)"


TIE = {None: None, "units": m.ration(m.largest_remainder(m.no_order)), "exact": lambda g, left: m.ranks_model.proportional(g, left)}


def requests(rng, low=0, most=5):
    return {k: rng.randint(low, 12) for k in range(rng.randint(1, most))}


def tree(rng, most=6):
    n = rng.randint(1, most)
    return [None] + [rng.randrange(i) for i in range(1, n)]


def parents(parent, key="nat", key_of=str):
    return table([(i, p) for i, p in enumerate(parent) if p is not None], key, key, key_of, key_of)


def units(rng, cases):
    left, right = [], []
    while len(left) < cases:
        w = requests(rng)
        K, T = sorted(w), sum(w.values())
        if T == 0:
            continue
        order = dict(zip(K, rng.sample(range(len(K)), len(K))))
        x, t = rng.randint(0, T), rng.randint(0, 3 * T)
        ks, kset, W, O = lst(K, str), keyset(K), fn(w.items(), "nat", "int"), fn(order.items(), "nat", "nat")
        last = lambda j, k: order[k] < order[j]
        got = [
            m.ration(m.to_first(order))(w, x),
            m.ration(m.largest_remainder(m.first_in(order)))(w, x),
            m.ration(m.largest_remainder(m.no_order))(w, x),
            m.apportion(m.to_first(order))(w, t),
            m.apportion(m.largest_remainder(m.first_in(order)))(w, t),
            m.to_nearest(m.half_up_part, m.first_in(order), last)(t, K, w),
            m.to_nearest(m.half_even_part, m.first_in(order), last)(t, K, w),
        ]
        back = f"(%j k. {O} k < {O} j)"
        terms = [
            f"map (ration (to_first {O}) {kset} {W} {x}) {ks}",
            f"map (ration (largest_remainder (first_in {O})) {kset} {W} {x}) {ks}",
            f"map (ration (largest_remainder no_order) {kset} {W} {x}) {ks}",
            f"map (apportion (to_first {O}) {kset} {W} {t}) {ks}",
            f"map (apportion (largest_remainder (first_in {O})) {kset} {W} {t}) {ks}",
            f"map (to_nearest half_up_part (first_in {O}) {back} {t} {kset} {W}) {ks}",
            f"map (to_nearest half_even_part (first_in {O}) {back} {t} {kset} {W}) {ks}",
        ]
        left.append("[" + ", ".join(terms) + "]")
        right.append(lst([lst([g[k] for k in K]) for g in got], str))
    return left, right, "int list list"


def ranks(rng, cases, exact):
    left, right, n = [], [], "rat" if exact else "int"
    for _ in range(cases):
        v = requests(rng)
        K = sorted(v)
        rank = {k: rng.randint(0, 2) for k in K}
        x = rng.randint(0, sum(v.values()))
        tie = TIE["exact" if exact else "units"]
        rule = "proportional" if exact else "(ration (largest_remainder no_order))"
        V, R, ks, kset = fn(v.items(), "nat", n), fn(rank.items(), "nat", "nat"), lst(K, str), keyset(K)
        got = m.by_rank(rank, tie, v, x)
        order = rng.sample(K, len(K))
        whole = m.whole_each(order, v, x)
        left.append(f"(map (by_rank {R} {rule} {kset} {V} {x}) {ks}, tie_arises {kset} {R} {V} {x}, map (whole_each ({lst(order, str)} :: nat list) {V} {x}) {ks})")
        right.append(f"({lst([got[k] for k in K])}, {m.tie_arises(rank, v, x)}, {lst([whole[k] for k in K])})")
    return left, right, f"{n} list * bool * {n} list"


def merges(rng, cases, exact):
    """`merge_of`, and `settle` on a tree, under every declaration a policy makes."""
    left, right, n = [], [], "rat" if exact else "int"
    for _ in range(cases):
        parent = tree(rng)
        bal = [rng.randint(0, 40) for _ in parent]
        a = rng.randrange(len(parent))
        v = requests(rng)
        K = sorted(v)
        rank = {k: rng.randint(0, 2) for k in K}
        tie = None if rng.random() < 0.3 else ("exact" if exact else "units")
        refuses, ranked, leaves = rng.random() < 0.2, rng.random() < 0.2, rng.random() < 0.6
        pol = (refuses, ranked, TIE[tie], leaves)
        outcome, after = m.settle(pol, rank, parent, a, v, bal)
        accounts = list(range(len(parent)))
        P = policy(refuses, ranked, tie, leaves, False, n)
        V, R, B = fn(v.items(), "nat", n), fn(rank.items(), "nat", "nat"), fn(enumerate(bal), "nat", n)
        ps = f"({lst(v.items(), lambda kv: f'({kv[0]}, {kv[1]})')} :: (nat * {n}) list)"
        left.append(f"(shown {lst(K, str)} (merge_of {P} {R} {m.available(parent, bal, a)} {keyset(K)} {V}), "
                    f"(case settle {P} {R} {parents(parent)} {a} {ps} {B} of (out, bal) => (shown {lst(K, str)} out, map bal {lst(accounts, str)})))")
        right.append(f"({shown(outcome, K)}, ({shown(outcome, K)}, {lst(after)}))")
    return left, right, f"({n} list * {n} * reason option) * (({n} list * {n} * reason option) * {n} list)"


def pots(rng, cases):
    left, right = [], []
    for _ in range(cases):
        groups = [{10 * t + i: rng.randint(0, 12) for i in range(rng.randint(1, 4))} for t in range(rng.randint(1, 3))]
        above = rng.randint(0, 2)
        asked = sum(sum(g.values()) for g in groups)
        parent = [None] + list(range(above)) + [above] * len(groups)
        bal = [rng.randint(0, asked + 5) for _ in range(above + 1)] + [rng.randint(0, sum(g.values()) + 2) if rng.random() < 0.4 else 1000 for g in groups]
        ids = list(range(above + 1, above + 1 + len(groups)))
        tie = None if rng.random() < 0.2 else "units"
        refuses, leaves = rng.random() < 0.1, rng.random() < 0.7
        rank = {k: 0 for g in groups for k in g}
        result = m.pots((refuses, False, TIE[tie], leaves), rank, parent, above, list(zip(ids, groups)), bal)
        accounts = list(range(len(parent)))
        each = lst(zip(ids, groups), lambda ag: f"({ag[0]}, ({lst(ag[1].items(), lambda kv: f'({kv[0]}, {kv[1]})')} :: (nat * int) list))")
        keys = lst([lst(sorted(g), str) for g in groups], str)
        left.append(f"(case pots {policy(refuses, False, tie, leaves, False, 'int')} (%k. 0) {parents(parent)} {above} {each} 0 {fn(enumerate(bal), 'nat', 'int')} of "
                    f"None => None | Some (gs, h, bal) => Some (map (%(g, ks). map g ks) (zip gs ({keys} :: nat list list)), h, map bal {lst(accounts, str)}))")
        right.append("None" if result is None else f"Some ({lst([lst([g[k] for k in sorted(g)]) for g in result[0]], str)}, {num(result[1])}, {lst(result[2])})")
    return left, right, "(int list list * int * int list) option"


def spreads(rng, cases):
    left, right = [], []
    for _ in range(cases):
        parent = tree(rng)
        n = len(parent)
        bal = [rng.randint(0, 40) for _ in parent]
        counting = set(rng.sample(range(n), rng.randint(0, min(2, n)))) if rng.random() < 0.5 else set()
        charged = lambda a: set(m.chain(parent, a)) | {b for c in counting for b in m.chain(parent, c)}
        accounts = rng.sample(range(n), rng.randint(1, min(4, n)))
        v = requests(rng)
        K = sorted(v)
        order = dict(zip(K, rng.sample(range(len(K)), len(K))))
        pick = rng.randrange(3)
        O = fn(order.items(), "nat", "nat")
        if pick == 0:
            rule, text = (lambda w, x: m.ration(m.largest_remainder(m.first_in(order)))(w, x)), f"(ration (largest_remainder (first_in {O})) {keyset(K)})"
        elif pick == 1:
            rule, text = (lambda w, x: m.by_rank(order, None, w, x)), f"(by_rank {O} (%_ _ _. nothing) {keyset(K)})"
        else:
            rule, text = (lambda w, x: m.ration(m.largest_remainder(m.no_order))(w, x)), f"(ration (largest_remainder no_order) {keyset(K)})"
        parts, rest, after = m.spread(rule, charged, accounts, bal, v)
        whole = m.spread_whole(rule, charged, accounts, bal, v)
        C = f"(%a. case {table([(a, sorted(charged(a))) for a in range(n)], 'nat', 'nat list', lambda s: lst(s, str))} a of Some s => set s | None => {{}})"
        args = f"{keyset(K)} {text} {C} ({lst(accounts, str)} :: nat list) {fn(enumerate(bal), 'nat', 'int')} {fn(v.items(), 'nat', 'int')}"
        every = lst(range(n), str)
        left.append(f"((case spread {args} of (ps, r, bal) => (map (%p. map p {lst(K, str)}) ps, map r {lst(K, str)}, map bal {every})), "
                    f"(case spread_whole {args} of None => None | Some (ps, bal) => Some (map (%p. map p {lst(K, str)}) ps, map bal {every})))")
        shown_parts = lst([lst([p[k] for k in K]) for p in parts], str)
        right.append(f"(({shown_parts}, {lst([rest[k] for k in K])}, {lst(after)}), " + ("None" if whole is None else f"Some ({shown_parts}, {lst(after)})") + ")")
    return left, right, "(int list list * int list * int list) * (int list list * int list) option"


def histories(rng, cases):
    """`credit`, `run`, `summed`, the three readings and `chain`, on one book and one list of requests a case."""
    left, right = [], []
    for _ in range(cases):
        parent = tree(rng, 5)
        n = len(parent)
        stated = [rng.randint(5, 40) for _ in range(n)]
        cap = [s + (rng.randint(1, 10) if rng.random() < 0.2 else 0) for s in stated]
        only = [sorted(rng.sample(range(3), rng.randint(1, 2))) if rng.random() < 0.3 else None for _ in range(n)]
        refusing = [rng.random() < 0.5 for _ in range(n)]
        restores = lambda b, c: only[b] is None or c in only[b]
        book = (parent, stated, cap, restores, lambda b: refusing[b])
        qs, bal, posted = [], list(stated), []
        for _ in range(rng.randint(1, 10)):
            a = rng.randrange(n)
            q = ("draw", a, rng.randint(1, 15)) if rng.random() < 0.6 else ("restore", a, rng.randrange(3), rng.randint(1, 25))
            qs.append(q)
            p, bal = m.post(book, q, bal)
            if p is not None:
                posted.append(p)
        days = [max(0, i + 1 - (rng.randint(1, 3) if rng.random() < 0.25 else 0)) for i in range(len(posted))]
        es = list(zip(days, posted))
        asks = [(rng.randint(0, len(posted) + 1), rng.randint(0, len(posted))) for _ in range(3)]
        accounts = list(range(n))
        B = (f"((| parent_of = {parents(parent)}, stated = {fn(enumerate(stated), 'nat', 'int')}, ceiling = {fn(enumerate(cap), 'nat', 'int')}, "
             f"restores = (%b c. case {table([(b, o) for b, o in enumerate(only) if o is not None], 'nat', 'nat option list', lambda o: lst(o, lambda c: f'Some {c}'))} b of None => True | Some ks => c : set ks), "
             f"refusing = (%b. b : set ({lst([b for b in accounts if refusing[b]], str)} :: nat list)) |) :: (nat, nat, int) book)")
        Q = lst(qs, lambda q: f"Draw {q[1]} {q[2]}" if q[0] == "draw" else f"Restore {q[1]} (Some {q[2]}) {q[3]}")
        every, D, A = lst(accounts, str), f"({lst(days, str)} :: nat list)", f"({lst(asks, lambda dn: f'({dn[0]}, {dn[1]})')} :: (nat * nat) list)"
        left.append(f"(let B = {B} in case run B ({Q} :: (nat, nat, int) request list) (stated B) of (ps, bal) => "
                    f"(let es = zip {D} ps in (map (posting {every}) ps, map bal {every}, map (summed B ps) {every}, "
                    f"map (%(d, n). map (reading_a B d n es) {every}) {A}, map (%(d, n). map (reading_b B d n es) {every}) {A}, map (%(d, n). map (flows B d n es) {every}) {A}, "
                    f"map (chain {n} (parent_of B)) {every})))")
        def shown_posting(p):
            if p[0] == "drawn":
                return f"({p[1]}, {p[2]}, 0, [])"
            return f"({p[1]}, {p[3]}, {p[4]}, {lst([p[5].get(b, 0) for b in accounts])})"
        def reads(of):
            return lst([lst([of(b, m.counted(d, r, es)) for b in accounts], str) for d, r in asks], str)
        right.append("(" + ", ".join([
            lst(posted, shown_posting), lst(bal), lst([m.summed(book, posted, b) for b in accounts]),
            reads(lambda b, picked: num(m.summed(book, [e[1] for e in picked], b))),
            reads(lambda b, picked: num(m.replay(book, [e[1] for e in sorted(picked, key=lambda e: e[0])], True)[b])),
            reads(lambda b, picked: "({}, {})".format(*m.flows(book, [e[1] for e in picked], b))),
            lst([lst(m.chain(parent, a), str) for a in accounts], str)]) + ")")
    return left, right, "(nat * int * int * int list) list * int list * int list * int list list * int list list * (int * int) list list * nat list list"


def purposes(rng, cases, exact):
    """`settle_purposes`, on accounts that are triples of truth values, since `room` and `crossing` range over every account of the type."""
    left, right, n = [], [], "rat" if exact else "int"
    acc = lambda i: "({}, {}, {})".format(*[str(bool(i >> s & 1)) for s in (2, 1, 0)])
    A = "bool * bool * bool"
    for _ in range(cases):
        parent = tree(rng, 7)
        size = len(parent)
        bal = [rng.randint(0, 40) for _ in parent]
        a = rng.randrange(size)
        counts = {p: rng.sample(range(size), rng.randint(1, min(2, size))) for p in range(3)}
        v = requests(rng, low=1, most=4)
        K = sorted(v)
        purpose = {k: rng.choice([None, 0, 1, 2]) for k in K}
        tie = "exact" if exact else rng.choice([None, "units"])
        rank = {k: rng.randint(0, 1) for k in K} if tie else dict(zip(K, rng.sample(range(len(K)), len(K))))
        refuses, leaves, unmixed = rng.random() < 0.1, rng.random() < 0.8, rng.random() < 0.15
        pol = (refuses, False, TIE[tie], leaves)
        result = m.settle_purposes(pol, unmixed, rank, parent, a, v, purpose, counts, bal)
        common = m.chain(parent, a)
        reach = {k: set(common) | {b for c in counts.get(purpose[k], ()) for b in m.chain(parent, c)} for k in K}
        groups = sorted({frozenset(k for k in K if b in reach[k]) for k in K for b in reach[k]}, key=len)
        G = lst(groups, lambda g: keyset(sorted(g)))
        counted = f"(%p. case {table(counts.items(), 'nat', f'({A}) list', lambda cs: lst(cs, acc))} p of Some s => set s | None => {{}})"
        P = policy(refuses, False, tie, leaves, unmixed, n)
        ps = f"({lst(v.items(), lambda kv: f'({kv[0]}, {kv[1]})')} :: (nat * {n}) list)"
        every = lst(range(size), acc)
        left.append(f"(case settle_purposes {P} {fn(rank.items(), 'nat', 'nat')} {parents(parent, A, acc)} {counted} {acc(a)} "
                    f"{table([(k, p) for k, p in purpose.items() if p is not None], 'nat', 'nat', str)} {G} {ps} {fn(enumerate(bal), A, n, key_of=acc)} of "
                    f"(out, bal) => (shown {lst(K, str)} out, map bal {every}))")
        after = bal if result[0] == "refused" else result[3]
        right.append(f"({shown(result, K)}, {lst(after)})")
    return left, right, f"({n} list * {n} * reason option) * {n} list"


HEAD = '''(* SPDX-License-Identifier: MPL-2.0 *)

(* Generated by cases.py from model.py with fixed seeds. Do not edit: change cases.py and run it.
   Each lemma has Isabelle evaluate the definitions of Target.thy on generated inputs and compares
   the results with what the model computed for the same inputs. It proves no law. *)

theory Cases
imports Target
begin

text \\<open>The path of an account, unfolded one step, so that what reads a path evaluates. It is a code
  equation for these cases alone. That a list by a bounded walk is the path is a law, and is LG-9's.\\<close>

lemma path_code [code]:
  "path parent a = (case parent a of None \\<Rightarrow> {a} | Some b \\<Rightarrow> insert a (path parent b))"
proof (cases "parent a")
  case None
  have "x = a" if "(a, x) \\<in> (up parent)\\<^sup>*" for x
    using that None by (cases rule: converse_rtranclE) (auto simp: up_def)
  then show ?thesis by (auto simp: path_def None)
next
  case (Some b)
  have "(a, x) \\<in> (up parent)\\<^sup>* \\<longleftrightarrow> x = a \\<or> (b, x) \\<in> (up parent)\\<^sup>*" for x
  proof
    assume "(a, x) \\<in> (up parent)\\<^sup>*"
    then show "x = a \\<or> (b, x) \\<in> (up parent)\\<^sup>*"
      using Some by (cases rule: converse_rtranclE) (auto simp: up_def)
  next
    assume "x = a \\<or> (b, x) \\<in> (up parent)\\<^sup>*"
    moreover have "(a, b) \\<in> up parent" using Some by (simp add: up_def)
    ultimately show "(a, x) \\<in> (up parent)\\<^sup>*" by (auto intro: converse_rtrancl_into_rtrancl)
  qed
  then show ?thesis by (auto simp: path_def Some)
qed

lemma inj_on_code [code]: "inj_on f (set xs) \\<longleftrightarrow> distinct (map f (remdups xs))"
  by (simp add: distinct_map)

definition fn :: "('a \\<times> 'b) list \\<Rightarrow> 'a \\<Rightarrow> 'b::zero" where
  "fn xs k = (case map_of xs k of Some v \\<Rightarrow> v | None \\<Rightarrow> 0)"

definition shown :: "'k list \\<Rightarrow> ('k, 'n::zero) outcome \\<Rightarrow> 'n list \\<times> 'n \\<times> reason option" where
  "shown ks out = (case out of Granted g r \\<Rightarrow> (map g ks, r, None) | Refused why \\<Rightarrow> ([], 0, Some why))"

definition posting :: "'a list \\<Rightarrow> ('a, 'c, 'n::zero) posted \\<Rightarrow> 'a \\<times> 'n \\<times> 'n \\<times> 'n list" where
  "posting accounts p =
     (case p of Drawn a x \\<Rightarrow> (a, x, 0, []) | Restored a c x applied cuts \\<Rightarrow> (a, x, applied, map cuts accounts))"

'''


def main():
    groups = [
        ("whole_units", units(random.Random(101), 60)),
        ("ranks_in_whole_units", ranks(random.Random(102), 60, False)),
        ("ranks_exact", ranks(random.Random(103), 60, True)),
        ("merge_and_settle_in_whole_units", merges(random.Random(104), 60, False)),
        ("merge_and_settle_exact", merges(random.Random(105), 60, True)),
        ("pots_under_a_fund", pots(random.Random(106), 60)),
        ("allocation_across_accounts", spreads(random.Random(107), 60)),
        ("credits_sums_and_readings", histories(random.Random(108), 60)),
        ("purposes_in_whole_units", purposes(random.Random(109), 60, False)),
        ("purposes_exact", purposes(random.Random(110), 60, True)),
    ]
    out, count, lemmas, join = [HEAD], 0, 0, "," + chr(10) + "     "
    for name, (left, right, kind) in groups:
        count += len(left)
        for i in range(0, len(left), CHUNK):
            lemmas += 1
            out.append(f"lemma {name}_{i // CHUNK + 1}:\n  \"([{join.join(left[i : i + CHUNK])}]\n     :: ({kind}) list) =\n    [{join.join(right[i : i + CHUNK])}]\"\n  by eval\n\n")
    out.append("end\n")
    (HERE / "Cases.thy").write_text("".join(out), encoding="utf-8", newline="\n")
    print(f"wrote Cases.thy with {lemmas} lemmas over {count} cases")


if __name__ == "__main__":
    main()
