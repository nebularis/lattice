# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The target ledger kernel of `Target.thy`, transliterated, and searched for a case that breaks a law it must keep or gain.

Each definition here follows the theory's by name. Where an older and independent statement of the same thing exists, a sort where the theory counts, a loop where the theory has a
closed form, the search compares the two, and it asserts each law on every case, so it stops at the first counterexample. It proves nothing. Run it with
`mise exec -- python spikes/ledger-target-kernel/model.py`, or with a divisor such as `20` for a short run."""

from __future__ import annotations

import importlib.util
import random
import sys
from fractions import Fraction
from pathlib import Path

_spec = importlib.util.spec_from_file_location("ranks_model", Path(__file__).resolve().parent.parent / "ledger-ranks-and-pots" / "model.py")
ranks_model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ranks_model)


def total(K, v):
    return sum(v[k] for k in K)


# Rules over whole units.


def floor_part(t, K, w):
    T = total(K, w)
    return {k: (t * w[k] // T if T else 0) for k in K}


def half_up_part(t, K, w):
    T = total(K, w)
    return {k: ((2 * t * w[k] + T) // (2 * T) if T else 0) for k in K}


def remainder(t, K, w):
    T = total(K, w)
    return {k: ((t * w[k]) % T if T else 0) for k in K}


def short(t, K, base):
    return t - total(K, base)


def placed(E, pref, n, k):
    return k in E and sum(1 for j in E if not pref(k, j)) <= n


def units(base, n, E, gain, L, lose):
    return {k: base[k] + (1 if n > 0 and placed(E, gain, n, k) else 0) - (1 if n < 0 and placed(L, lose, -n, k) else 0) for k in base}


def first_in(order):
    return lambda j, k: order[j] < order[k]


def then_by(p, q):
    return lambda j, k: p(j, k) or (not p(k, j) and q(j, k))


def no_order(j, k):
    return False


def to_first(order):
    return lambda E, t, K, w: units(floor_part(t, K, w), short(t, K, floor_part(t, K, w)), E, first_in(order), set(), no_order)


def largest_remainder(tiebreak):
    def rule(E, t, K, w):
        rem = remainder(t, K, w)
        return units(floor_part(t, K, w), short(t, K, floor_part(t, K, w)), E, then_by(lambda j, k: rem[k] < rem[j], tiebreak), set(), no_order)

    return rule


def to_nearest(part, gain, lose):
    def rule(t, K, w):
        base, floor, rem = part(t, K, w), floor_part(t, K, w), remainder(t, K, w)
        return units(base, short(t, K, base), {k for k in K if base[k] == floor[k] and rem[k] > 0}, gain, {k for k in K if floor[k] < base[k]}, lose)

    return rule


def unmet(t, K, w):
    floor = floor_part(t, K, w)
    return {k for k in K if floor[k] < w[k]}


def ration(U):
    return lambda v, x: U(unmet(x, set(v), v), x, set(v), v)


def apportion(U):
    return lambda w, x: U(set(w), x, set(w), w)


# Ranks.


def by_rank(rank, tie, v, x):
    out = {}
    for k in v:
        left = x - sum(v[j] for j in v if rank[j] < rank[k])
        G = [j for j in v if rank[j] == rank[k]]
        if sum(v[j] for j in G) <= left:
            out[k] = v[k]
        elif left <= 0:
            out[k] = 0
        elif G == [k]:
            out[k] = left
        else:
            out[k] = tie({j: v[j] for j in G}, left)[k]
    return out


def tie_arises(rank, v, x):
    for k in v:
        left = x - sum(v[j] for j in v if rank[j] < rank[k])
        G = [j for j in v if rank[j] == rank[k]]
        if 0 < left < sum(v[j] for j in G) and G != [k]:
            return True
    return False


def merge(refuses, ranked, tie, leaves, rank, av, v):
    x = max(0, av)
    if total(v, v) <= av:
        return ("granted", dict(v), 0)
    if refuses:
        return ("refused", "exceeds")
    if ranked and len(set(rank.values())) < len(rank):
        return ("refused", "unranked")
    if tie is None:
        if tie_arises(rank, v, x):
            return ("refused", "tied")
        g = by_rank(rank, None, v, x)
        return ("granted", g, x - total(v, g))
    g = by_rank(rank, tie, v, x)
    r = x - total(v, g)
    return ("granted", g, r) if r == 0 or leaves else ("refused", "undecided")


# Credits and histories, on a tree of accounts 0..n-1 whose parent has a lower number.


def chain(parent, a):
    out = [a]
    while parent[out[-1]] is not None:
        out.append(parent[out[-1]])
    return out


def credit(parent, cap, accepts, a, x, bal):
    applied = max(0, min(x, cap[a] - bal[a]))
    on = [b for b in chain(parent, a) if accepts(b)]
    take = {b: min(applied, cap[b] - bal[b]) for b in on}
    return applied, {b: applied - take[b] for b in on}, [bal[b] + take.get(b, 0) for b in range(len(bal))]


def credit_by_loop(parent, cap, accepts, a, x, bal):
    """The writer of the credit kinds benchmark, `settle_credit`, stated again as a loop."""
    step = list(bal)
    applied = min(x, cap[a] - step[a])
    cuts = {}
    for i in chain(parent, a):
        if accepts(i):
            take = min(applied, cap[i] - step[i])
            step[i] += take
            if take < applied:
                cuts[i] = applied - take
    return applied, cuts, step


def post(book, q, bal):
    parent, stated, cap, restores = book
    if q[0] == "draw":
        _, a, x = q
        if x >= 0 and all(x <= bal[b] for b in chain(parent, a)):
            return ("drawn", a, x), [v - x if b in chain(parent, a) else v for b, v in enumerate(bal)]
        return None, bal
    _, a, c, x = q
    applied, cuts, after = credit(parent, cap, lambda b: restores(b, c), a, x, bal)
    return ("restored", a, c, x, applied, cuts), after


def moved(book, p, b):
    parent, stated, cap, restores = book
    if p[0] == "drawn":
        return -p[2] if b in chain(parent, p[1]) else 0
    _, a, c, x, applied, cuts = p
    return applied - cuts.get(b, 0) if b in chain(parent, a) and restores(b, c) else 0


def summed(book, ps, b):
    return book[1][b] + sum(moved(book, p, b) for p in ps)


def replay(book, ps, limit):
    """The postings settled again in the order given. A debit that no longer fits is limited to what is available, or with `limit` off is charged in full, as the benchmark's reading B does."""
    parent, stated, cap, restores = book
    bal = list(stated)
    for p in ps:
        if p[0] == "drawn":
            on = chain(parent, p[1])
            y = max(0, min(p[2], min(bal[b] for b in on))) if limit else p[2]
            bal = [v - y if b in on else v for b, v in enumerate(bal)]
        else:
            bal = credit(parent, cap, lambda b: restores(b, p[2]), p[1], p[3], bal)[2]
    return bal


def counted(day, recording, es):
    return [e for e in es[:recording] if e[0] <= day]


# The searches.


def draw_requests(rng, low=0):
    return {f"k{i}": rng.randint(low, 12) for i in range(rng.randint(1, 6))}


def search_units(cases, seed):
    """The rules for whole units against a sort, and their laws as rationing, as apportionment and rounded to the nearest."""
    rng = random.Random(seed)
    found = {"cases": 0, "no order leaves a residual": 0, "a key of no weight takes a unit": 0, "nearest takes a unit back": 0, "nearest gives a unit": 0}
    for _ in range(cases):
        w = draw_requests(rng)
        K, T = sorted(w), sum(w.values())
        if T == 0:
            continue
        order = dict(zip(rng.sample(K, len(K)), range(len(K))))
        x = rng.randint(0, T)
        floor, rem = floor_part(x, K, w), remainder(x, K, w)
        left = x - sum(floor.values())
        eligible = [k for k in K if floor[k] < w[k]]
        # rationing, to the first in the declared order
        got = ration(to_first(order))(w, x)
        first = sorted(eligible, key=lambda k: order[k])[:left]
        assert got == {k: floor[k] + (k in first) for k in K}, "to_first is not the sort"
        assert sum(got.values()) == x and all(0 <= got[k] <= w[k] for k in K), "to_first is not exact within the claims"
        # rationing, to the largest remainders, equal remainders by the declared order
        got = ration(largest_remainder(first_in(order)))(w, x)
        by_rem = sorted(eligible, key=lambda k: (-rem[k], order[k]))[:left]
        assert got == {k: floor[k] + (k in by_rem) for k in K}, "largest_remainder is not the sort"
        assert sum(got.values()) == x and all(0 <= got[k] <= w[k] for k in K), "largest_remainder is not exact within the claims"
        assert all(abs(Fraction(x * w[k], T) - got[k]) < 1 for k in K), "largest_remainder strays a unit from the exact share"
        # rationing, with no order declared
        got = ration(largest_remainder(no_order))(w, x)
        if x < T:
            assert got == ranks_model.units_with_no_order(w, x), "largest_remainder with no order is not the rule the ranks spike tried"
        assert sum(got.values()) <= x and x - sum(got.values()) < len(K) and all(0 <= got[k] <= w[k] for k in K), "no order breaks a bound"
        assert all(w[a] != w[b] or got[a] == got[b] for a in K for b in K), "no order treats equal requests unequally"
        found["no order leaves a residual"] += sum(got.values()) < x
        # apportionment, any amount, every named key may take a unit
        t = rng.randint(0, 3 * T)
        got = apportion(to_first(order))(w, t)
        assert sum(got.values()) == t and all(v >= 0 for v in got.values()), "an apportionment to the first is not exact"
        found["a key of no weight takes a unit"] += any(w[k] == 0 and got[k] > 0 for k in K)
        got = apportion(largest_remainder(first_in(order)))(w, t)
        assert sum(got.values()) == t and all(abs(Fraction(t * w[k], T) - got[k]) < 1 for k in K), "an apportionment by remainders is not exact within a unit"
        # rounded to the nearest, a unit over taken back from the last in the order among those rounded up
        last = lambda j, k: order[k] < order[j]
        got = to_nearest(half_up_part, first_in(order), last)(t, K, w)
        base = half_up_part(t, K, w)
        over = sum(base.values()) - t
        assert sum(got.values()) == t, ("rounding to the nearest does not sum", w, t, got)
        assert all(abs(Fraction(t * w[k], T) - got[k]) < 1 for k in K), ("rounding to the nearest strays a unit", w, t, got)
        found["nearest takes a unit back"] += over > 0
        found["nearest gives a unit"] += over < 0
        found["cases"] += 1
    return found


def search_ranks(cases, seed, whole):
    """`by_rank` as one closed form against the loop over tiers of the ranks spike, and its laws."""
    rng = random.Random(seed)
    found = {"cases": 0, "a tie arises": 0, "with a residual": 0, "refused for want of a tie rule": 0}
    for _ in range(cases):
        ranked = ranks_model.draw_ranks(rng)
        v = {k: a for r in ranked for k, a in r.items()}
        rank = {k: i for i, r in enumerate(ranked) for k in r}
        asked = sum(v.values())
        x = rng.randint(0, asked)
        tie = ration(largest_remainder(no_order)) if whole else (lambda g, left: ranks_model.proportional(g, left))
        got = by_rank(rank, tie, v, x)
        loop, residual = ranks_model.tiers(x, ranked, ranks_model.units_with_no_order if whole else ranks_model.proportional)
        assert got == {k: a for g in loop for k, a in g.items()}, ("by_rank is not the loop over tiers", ranked, x)
        assert all(0 <= got[k] <= v[k] for k in v) and sum(got.values()) + residual == x, "by_rank breaks a bound"
        assert by_rank(rank, tie, v, asked) == v, "the whole does not return the whole"
        assert whole or residual == 0, "an exact tie rule left a residual"
        outcome = merge(False, False, None, False, rank, x if x < asked else asked, v)
        assert (outcome[0] == "refused") == (x < asked and tie_arises(rank, v, x)), "a merge with no tie rule refuses where no tie arises, or grants where one does"
        distinct = dict(zip(v, rng.sample(range(len(v)), len(v))))
        prior = by_rank(distinct, None, v, x)
        assert prior == {k: max(0, min(v[k], x - sum(v[j] for j in v if distinct[j] < distinct[k]))) for k in v}, "distinct ranks are not priority"
        assert sum(prior.values()) == x, "priority is not exact"
        found["cases"] += 1
        found["a tie arises"] += tie_arises(rank, v, x)
        found["with a residual"] += residual > 0
        found["refused for want of a tie rule"] += outcome[0] == "refused"
    return found


def draw_book(rng):
    n = rng.randint(1, 7)
    parent = [None] + [rng.randrange(i) for i in range(1, n)]
    stated = [rng.randint(5, 60) for _ in range(n)]
    cap = [s + (rng.randint(1, 20) if rng.random() < 0.2 else 0) for s in stated]
    kinds = ["recovery", "reinstatement", "write-back"]
    only = [set(rng.sample(kinds, rng.randint(1, 2))) if rng.random() < 0.3 else None for _ in range(n)]
    return (parent, stated, cap, lambda b, c: only[b] is None or c in only[b]), kinds


def search_history(cases, seed):
    """A credit's closed form against the benchmark writer's loop, the balance as a sum less its cuts against the stepped balance, and the readings by effective day."""
    rng = random.Random(seed)
    found = {"cases": 0, "postings": 0, "credits cut at an ancestor": 0, "draws refused": 0, "histories with a late posting": 0, "B differs from the ledger": 0,
             "A below zero or above the ceiling": 0, "B charged in full below zero": 0}
    for _ in range(cases):
        book, kinds = draw_book(rng)
        parent, stated, cap, restores = book
        n, bal, posted, es = len(stated), list(stated), [], []
        for step in range(rng.randint(1, 25)):
            a = rng.randrange(n)
            if rng.random() < 0.6:
                q = ("draw", a, rng.randint(1, 15))
            else:
                c = rng.choice(kinds)
                if not restores(a, c):
                    continue
                q = ("restore", a, c, rng.randint(1, 25))
                applied, cuts, after = credit(parent, cap, lambda b: restores(b, c), a, q[3], bal)
                assert (applied, {b: x for b, x in cuts.items() if x}, after) == credit_by_loop(parent, cap, lambda b: restores(b, c), a, q[3], bal), "a credit's closed form is not the writer's loop"
                assert all(x >= 0 for x in cuts.values()), "a cut below zero"
            p, bal = post(book, q, bal)
            if p is None:
                found["draws refused"] += 1
                continue
            posted.append(p)
            es.append((len(posted) - (rng.randint(1, 4) if rng.random() < 0.15 else 0), p))
            found["credits cut at an ancestor"] += p[0] == "restored" and any(p[5].values())
            assert all(0 <= bal[b] <= cap[b] for b in range(n)), "a balance left the range from zero to its ceiling"
            assert all(summed(book, posted, b) == bal[b] for b in range(n)), "the sum less the cuts is not the stepped balance"
        late = any(e[0] < i + 1 for i, e in enumerate(es))
        head, last = len(es), max((e[0] for e in es), default=0)
        every = [e[1] for e in counted(last, head, es)]
        a_head = [summed(book, every, b) for b in range(n)]
        b_head = replay(book, [e[1] for e in sorted(counted(last, head, es), key=lambda e: e[0])], True)
        assert a_head == bal, "reading A at the head is not the ledger's balance"
        assert late or b_head == bal, "with nothing late, reading B is not the ledger's balance"
        assert all(0 <= v <= cap[b] for b, v in enumerate(b_head)), "reading B, with a debit limited, left the range"
        for day in range(1, last + 1):
            picked = counted(day, head, es)
            a_day = [summed(book, [e[1] for e in picked], b) for b in range(n)]
            full = replay(book, [e[1] for e in sorted(picked, key=lambda e: e[0])], False)
            assert late or a_day == replay(book, [e[1] for e in picked], True), "with nothing late, reading A for a day is not the balance of that day"
            found["A below zero or above the ceiling"] += any(not 0 <= v <= cap[b] for b, v in enumerate(a_day))
            found["B charged in full below zero"] += any(v < 0 for v in full)
        found["cases"] += 1
        found["postings"] += len(posted)
        found["histories with a late posting"] += late
        found["B differs from the ledger"] += b_head != bal
    return found


def examples():
    three = {"a": 5, "b": 5, "c": 5}
    assert ration(largest_remainder(no_order))(three, 10) == {"a": 3, "b": 3, "c": 3}
    assert ration(largest_remainder(first_in({"a": 2, "b": 1, "c": 0})))(three, 10) == {"a": 3, "b": 3, "c": 4}
    assert ration(to_first({"a": 0, "b": 1, "c": 2}))(three, 10) == {"a": 4, "b": 3, "c": 3}
    assert by_rank({"a": 0, "b": 0, "c": 0, "d": 1}, ration(largest_remainder(no_order)), {**three, "d": 3}, 10) == {"a": 3, "b": 3, "c": 3, "d": 0}
    assert merge(False, False, ration(largest_remainder(no_order)), False, {"a": 0, "b": 0, "c": 0}, 10, three) == ("refused", "undecided")
    assert merge(False, False, ration(largest_remainder(no_order)), True, {"a": 0, "b": 0, "c": 0}, 10, three) == ("granted", {"a": 3, "b": 3, "c": 3}, 1)
    assert merge(True, False, None, False, {"a": 0, "b": 1, "c": 2}, 10, three) == ("refused", "exceeds")
    assert merge(False, True, None, False, {"a": 0, "b": 0, "c": 2}, 10, three) == ("refused", "unranked")
    assert merge(False, False, None, False, {"a": 0, "b": 0, "c": 2}, 7, three) == ("refused", "tied")
    assert merge(False, False, None, False, {"a": 0, "b": 0, "c": 2}, 12, three) == ("granted", {"a": 5, "b": 5, "c": 2}, 0)
    # the worked example of the sketch on balances under post-once, section 4.9
    book = ([None], [100], [100], lambda b, c: True)
    bal, es = [100], []
    for day, q in ((1, ("draw", 0, 30)), (4, ("restore", 0, "recovery", 50)), (2, ("draw", 0, 80))):
        p, bal = post(book, q, bal)
        es.append((day, p))
    assert bal == [20] and es[1][1][4] == 30
    reading_a = lambda day: summed(book, [e[1] for e in counted(day, 3, es)], 0)
    reading_b = lambda day, limit: replay(book, [e[1] for e in sorted(counted(day, 3, es), key=lambda e: e[0])], limit)[0]
    assert [reading_a(d) for d in (1, 2, 4)] == [70, -10, 20]
    assert [reading_b(d, True) for d in (1, 2, 4)] == [70, 0, 50]
    assert [reading_b(d, False) for d in (1, 2, 4)] == [70, -10, 40]
    print("the sketch's example: reading A", [reading_a(d) for d in (1, 2, 4)], "reading B with the debit limited", [reading_b(d, True) for d in (1, 2, 4)],
          "and charged in full", [reading_b(d, False) for d in (1, 2, 4)])


def main():
    scale = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    examples()
    print("whole units:", search_units(200_000 // scale, 21))
    print("ranks, exact amounts:", search_ranks(100_000 // scale, 22, False))
    print("ranks, whole units:", search_ranks(200_000 // scale, 23, True))
    print("credits, sums and readings:", search_history(60_000 // scale, 24))


if __name__ == "__main__":
    main()
