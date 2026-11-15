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
    parent, stated, cap, restores = book[:4]
    if q[0] == "draw":
        _, a, x = q
        if x >= 0 and all(x <= bal[b] for b in chain(parent, a)):
            return ("drawn", a, x), [v - x if b in chain(parent, a) else v for b, v in enumerate(bal)]
        return None, bal
    _, a, c, x = q
    applied, cuts, after = credit(parent, cap, lambda b: restores(b, c), a, x, bal)
    return ("restored", a, c, x, applied, cuts), after


def moved(book, p, b):
    parent, stated, cap, restores = book[:4]
    if p[0] == "drawn":
        return -p[2] if b in chain(parent, p[1]) else 0
    _, a, c, x, applied, cuts = p
    return applied - cuts.get(b, 0) if b in chain(parent, a) and restores(b, c) else 0


def summed(book, ps, b):
    return book[1][b] + sum(moved(book, p, b) for p in ps)


def replay(book, ps, by_policy):
    """The postings settled again in the order given. A debit that no longer fits is settled by its account's own policy, refused where the account refuses and cut to what is available
    where it rations. With `by_policy` off it is charged in full, as the benchmark's reading B does."""
    parent, stated, cap, restores = book[:4]
    bal = list(stated)
    for p in ps:
        if p[0] == "drawn":
            on = chain(parent, p[1])
            av = min(bal[b] for b in on)
            y = p[2] if p[2] <= av or not by_policy else (0 if book[4](p[1]) else max(0, av))
            bal = [v - y if b in on else v for b, v in enumerate(bal)]
        else:
            bal = credit(parent, cap, lambda b: restores(b, p[2]), p[1], p[3], bal)[2]
    return bal


def counted(day, recording, es):
    return [e for e in es[:recording] if e[0] <= day]


# Settlement, pots and allocation across accounts.


def available(parent, bal, a):
    return min(bal[b] for b in chain(parent, a))


def debit(accounts, x, bal):
    return [v - x if b in accounts else v for b, v in enumerate(bal)]


def settle(policy, rank, parent, a, v, bal):
    outcome = merge(*policy, rank, available(parent, bal, a), v)
    if outcome[0] == "refused":
        return outcome, bal
    return outcome, debit(chain(parent, a), total(v, outcome[1]), bal)


def pots(policy, rank, parent, fund, pot_requests, bal):
    out, held = [], 0
    for a, v in pot_requests:
        outcome = merge(*policy, rank, available(parent, debit(chain(parent, fund), held, bal), a), v)
        if outcome[0] == "refused":
            return None
        out.append(outcome[1])
        held += outcome[2]
        bal = debit(chain(parent, a), total(v, outcome[1]), bal)
    return out, held, bal


def spread(rule, charged, accounts, bal, v):
    parts = []
    for a in accounts:
        p = rule(v, min(total(v, v), max(0, min(bal[b] for b in charged(a)))))
        parts.append(p)
        bal = debit(charged(a), total(v, p), bal)
        v = {k: v[k] - p[k] for k in v}
    return parts, v, bal


def spread_whole(rule, charged, accounts, bal, v):
    parts, left, after = spread(rule, charged, accounts, bal, v)
    return (parts, after) if total(left, left) == 0 else None


# A proposal for question K3, purposes at one position, not yet in the theory.


def settle_purposes(rank, tie, parent, a, v, purpose, counts, bal, shuffle=None):
    """Requests at account `a`, some with a purpose that other accounts count. Each account a request reaches limits the set of requests that reach it, and what is available to a set
    is the least its accounts hold. The sets are settled from the narrowest to the widest, which is the path of `a` and holds every request, each cutting its requests by the rule to
    what is available to it. So a request is cut to its own limits before it competes. Two sets that overlap with neither inside the other have no such order, and the position is
    refused. Every account is charged what was granted to the requests that reach it."""
    common = chain(parent, a)
    reach = {k: set(common) | {b for c in counts.get(purpose[k], ()) for b in chain(parent, c)} for k in v}
    limit = {}
    for b in {b for k in v for b in reach[k]}:
        group = frozenset(k for k in v if b in reach[k])
        limit[group] = min(limit.get(group, bal[b]), bal[b])
    groups = sorted(limit, key=len)
    if any(x & y and not x <= y and not y <= x for x in groups for y in groups):
        return None
    if shuffle is not None:
        groups = sorted(shuffle(groups), key=len)
    claim = dict(v)
    for group in groups:
        asked = {k: claim[k] for k in v if k in group}
        if total(asked, asked) > limit[group]:
            claim.update(by_rank(rank, tie, asked, max(0, limit[group])))
    return claim, [bal[b] - sum(claim[k] for k in v if b in reach[k]) for b in range(len(bal))]


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
    refusing = [rng.random() < 0.5 for _ in range(n)]
    return (parent, stated, cap, lambda b, c: only[b] is None or c in only[b], lambda b: refusing[b]), kinds


def search_history(cases, seed):
    """A credit's closed form against the benchmark writer's loop, the balance as a sum less its cuts against the stepped balance, and the readings by effective day."""
    rng = random.Random(seed)
    found = {"cases": 0, "postings": 0, "credits cut at an ancestor": 0, "draws refused": 0, "histories with a late posting": 0, "B differs from the ledger": 0,
             "A below zero or above the ceiling": 0, "B charged in full below zero": 0}
    for _ in range(cases):
        book, kinds = draw_book(rng)
        parent, stated, cap, restores = book[:4]
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
        assert all(0 <= v <= cap[b] for b, v in enumerate(b_head)), "reading B, settled by the accounts' policies, left the range"
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


def draw_policy(rng, whole):
    tie = None if rng.random() < 0.3 else (ration(largest_remainder(no_order)) if whole else (lambda g, left: ranks_model.proportional(g, left)))
    return (rng.random() < 0.2, rng.random() < 0.2, tie, rng.random() < 0.6)


def search_merge(cases, seed, whole):
    """Every refusal of `merge` against its statement, and the laws of a settlement that grants or refuses."""
    rng = random.Random(seed)
    found = {"cases": 0, "granted": 0, "exceeds": 0, "unranked": 0, "tied": 0, "undecided": 0}
    for _ in range(cases):
        book, _ = draw_book(rng)
        parent, stated = book[0], book[1]
        a = rng.randrange(len(stated))
        v = draw_requests(rng)
        rank = {k: rng.randint(0, 2) for k in v}
        policy = draw_policy(rng, whole)
        refuses, ranked, tie, leaves = policy
        av, asked, x = available(parent, stated, a), total(v, v), max(0, available(parent, stated, a))
        outcome, after = settle(policy, rank, parent, a, v, stated)
        if asked <= av:
            want = "granted"
        elif refuses:
            want = "exceeds"
        elif ranked and len(set(rank.values())) < len(rank):
            want = "unranked"
        elif tie is None:
            want = "tied" if tie_arises(rank, v, x) else "granted"
        else:
            want = "granted" if leaves or sum(by_rank(rank, tie, v, x).values()) == x else "undecided"
        got = outcome[0] if outcome[0] == "granted" else outcome[1]
        assert got == want, ("a merge's outcome is not its statement", policy, rank, v, av)
        if outcome[0] == "refused":
            assert after == stated, "a refused merge changed a balance"
        else:
            _, g, r = outcome
            assert all(0 <= g[k] <= v[k] for k in v) and total(v, g) + r == min(asked, x) and r >= 0, "a granted merge breaks a bound"
            assert all(u >= 0 for u in after) and after == debit(chain(parent, a), total(v, g), stated), "a settlement did not charge the path what was granted"
            assert leaves or tie is None or r == 0, "a residual was left where none may be"
            keys = sorted(v)
            again = dict(zip([k[::-1] for k in keys], [0] * len(keys)))
            renamed = {k[::-1]: v[k] for k in rng.sample(keys, len(keys))}
            other = merge(*policy, {k[::-1]: rank[k] for k in keys}, av, renamed)
            assert other[0] == "granted" and {k[::-1]: u for k, u in other[1].items()} == g and set(again) == set(other[1]), "renaming the keys or reordering the proposals changed the grants"
        found["cases"] += 1
        found[got] += 1
    return found


def search_pots(cases, seed, whole):
    """`pots` over the target's `merge`, on a fund that has accounts above it, with an amount of its own on some pots."""
    rng = random.Random(seed)
    found = {"cases": 0, "refused": 0, "with a residual": 0, "an account above the fund binds": 0, "a pot's own amount binds": 0, "equal to by_rank": 0}
    for _ in range(cases):
        ranked = ranks_model.draw_ranks(rng)
        above = rng.randint(0, 2)
        asked = sum(sum(r.values()) for r in ranked)
        parent = [None] + list(range(above)) + [above] * len(ranked)
        fund = above
        bal = [rng.randint(0, asked + 5) for _ in range(above + 1)]
        caps = [rng.randint(0, sum(r.values()) + 2) if rng.random() < 0.4 else ranks_model.UNLIMITED for r in ranked]
        bal += caps
        pot_ids = list(range(above + 1, above + 1 + len(ranked)))
        rank = {k: 0 for r in ranked for k in r}
        policy = draw_policy(rng, whole)
        result = pots(policy, rank, parent, fund, list(zip(pot_ids, ranked)), bal)
        if result is None:
            found["refused"] += 1
            found["cases"] += 1
            continue
        grants, held, after = result
        paid = [sum(g.values()) for g in grants]
        assert all(u >= 0 for u in after), "a balance below zero"
        assert all(0 <= g[k] <= r[k] for g, r in zip(grants, ranked) for k in r) and all(p <= c for p, c in zip(paid, caps)), "a pot breaks a bound"
        assert all(after[b] == bal[b] - sum(paid) for b in range(above + 1)), "the fund and the accounts above it are not down by what was paid"
        assert all(r[x] != r[y] or g[x] == g[y] for g, r in zip(grants, ranked) for x in r for y in r), "equal requests, unequal grants"
        for i, reqs in enumerate(ranked):
            if any(paid[j] > 0 for j in range(i + 1, len(ranked))):
                full = min(sum(reqs.values()), caps[i])
                assert paid[i] == full or (whole and full - paid[i] < len(reqs)), "a later pot was paid while an account above bound on an earlier one"
        if all(c == ranks_model.UNLIMITED for c in caps) and policy[2] is not None:
            v = {k: x for r in ranked for k, x in r.items()}
            tiers_rank = {k: i for i, r in enumerate(ranked) for k in r}
            assert {k: x for g in grants for k, x in g.items()} == by_rank(tiers_rank, policy[2], v, min(sum(v.values()), min(bal[: above + 1]))), "pots with no amounts are not by_rank"
            found["equal to by_rank"] += 1
        found["cases"] += 1
        found["with a residual"] += held > 0
        found["an account above the fund binds"] += min(bal[: above + 1]) < min(asked, bal[fund]) if above else 0
        found["a pot's own amount binds"] += any(c < sum(r.values()) for c, r in zip(caps, ranked))
    return found


def search_spread(cases, seed, whole):
    """One amount allocated across accounts, charging the reach of its purpose, by an exact rule, by priority and by a rule that leaves a residual."""
    rng = random.Random(seed)
    found = {"cases": 0, "allocated whole": 0, "left over": 0, "charged beyond a path": 0, "by a rule that may leave a residual": 0}
    for _ in range(cases):
        book, _ = draw_book(rng)
        parent, stated = book[0], book[1]
        n = len(stated)
        counting = set(rng.sample(range(n), rng.randint(0, min(2, n)))) if rng.random() < 0.5 else set()
        charged = lambda a: set(chain(parent, a)) | {b for c in counting for b in chain(parent, c)}
        accounts = rng.sample(range(n), rng.randint(1, min(4, n)))
        v = draw_requests(rng)
        order = dict(zip(v, rng.sample(range(len(v)), len(v))))
        pick = rng.randrange(3)
        if pick == 0:
            rule = (lambda w, x: ration(largest_remainder(first_in(order)))(w, x)) if whole else (lambda w, x: ranks_model.proportional(w, x))
        elif pick == 1:
            rule = lambda w, x: by_rank(order, None, w, x)
        else:
            rule = lambda w, x: ration(largest_remainder(no_order))(w, x)
        if pick == 2 and not whole:
            continue
        parts, left, after = spread(rule, charged, accounts, stated, v)
        assert all(u >= 0 for u in after), "an allocation left a balance below zero"
        assert all(sum(p[k] for p in parts) + left[k] == v[k] and left[k] >= 0 and all(p[k] >= 0 for p in parts) for k in v), "the parts and what is left are not what was asked"
        want = list(stated)
        for a, p in zip(accounts, parts):
            want = debit(charged(a), total(v, p), want)
        assert after == want, "an account was not charged what was granted at it"
        whole_result = spread_whole(rule, charged, accounts, stated, v)
        assert (whole_result is None) == (total(left, left) > 0) and (whole_result is None or whole_result == (parts, after)), "the whole allocation is neither the allocation nor nothing"
        found["cases"] += 1
        found["allocated whole"] += whole_result is not None
        found["left over"] += whole_result is None
        found["charged beyond a path"] += bool(counting)
        found["by a rule that may leave a residual"] += pick == 2
    return found


def search_purposes(cases, seed, family):
    """The proposal for question K3: no account overdrawn, the grants within the requests, plain settlement where no request has a purpose, and no dependence on the order in which
    sets of one size are settled. It counts the positions refused because two sets cross, and those where cutting at the account first would have granted otherwise."""
    rng = random.Random(seed)
    found = {"cases": 0, "refused, two sets cross": 0, "a purpose's account binds": 0, "differs from cutting at the account first": 0}
    for _ in range(cases):
        book, _ = draw_book(rng)
        parent, stated = book[0], book[1]
        n = len(stated)
        a = rng.randrange(n)
        counts = {p: rng.sample(range(n), rng.randint(1, min(2, n))) for p in ("p", "q", "r")}
        v = draw_requests(rng, low=1)
        purpose = {k: rng.choice([None, "p", "q", "r"]) for k in v}
        if family == "exact":
            rank, tie = {k: 0 for k in v}, (lambda g, left: ranks_model.proportional(g, left))
        elif family == "priority":
            rank, tie = dict(zip(v, rng.sample(range(len(v)), len(v)))), None
        else:
            rank, tie = {k: rng.randint(0, 1) for k in v}, ration(largest_remainder(no_order))
        found["cases"] += 1
        result = settle_purposes(rank, tie, parent, a, v, purpose, counts, stated)
        if result is None:
            found["refused, two sets cross"] += 1
            continue
        grants, after = result
        assert all(u >= 0 for u in after), ("a purpose's account was overdrawn", parent, stated, a, v, purpose, counts)
        assert all(0 <= grants[k] <= v[k] for k in v), "a grant outside its request"
        av = available(parent, stated, a)
        plain = dict(v) if total(v, v) <= av else by_rank(rank, tie, v, max(0, av))
        assert any(purpose.values()) or plain == grants, "with no purpose it is not the plain merge"
        assert settle_purposes(rank, tie, parent, a, v, purpose, counts, stated, shuffle=lambda g: rng.sample(g, len(g)))[0] == grants, "the order of sets of one size changed the grants"
        # the alternative: every request competes at the account on what it asked, and a purpose's accounts then cut what its requests were granted
        alt = settle_purposes(rank, tie, parent, a, plain, purpose, counts, [10**9 if b in chain(parent, a) else u for b, u in enumerate(stated)])[0]
        found["a purpose's account binds"] += grants != plain
        found["differs from cutting at the account first"] += alt != grants
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
    book = ([None], [100], [100], lambda b, c: True, lambda b: False)
    refuser = book[:4] + (lambda b: True,)
    bal, es = [100], []
    for day, q in ((1, ("draw", 0, 30)), (4, ("restore", 0, "recovery", 50)), (2, ("draw", 0, 80))):
        p, bal = post(book, q, bal)
        es.append((day, p))
    assert bal == [20] and es[1][1][4] == 30
    reading_a = lambda day: summed(book, [e[1] for e in counted(day, 3, es)], 0)
    reading_b = lambda day, by_policy, b=book: replay(b, [e[1] for e in sorted(counted(day, 3, es), key=lambda e: e[0])], by_policy)[0]
    assert [reading_a(d) for d in (1, 2, 4)] == [70, -10, 20]
    assert [reading_b(d, True) for d in (1, 2, 4)] == [70, 0, 50]
    assert [reading_b(d, True, refuser) for d in (1, 2, 4)] == [70, 70, 100]
    assert [reading_b(d, False) for d in (1, 2, 4)] == [70, -10, 40]
    # a facility of 100 with a sublimit of 30 that counts letters of credit: a loan of 90 and a letter of credit of 40 at one position, shared in proportion
    parent, bal = [None, 0], [100, 30]
    share = lambda g, left: ranks_model.proportional(g, left)
    k3, after = settle_purposes({"loan": 0, "lc": 0}, share, parent, 0, {"loan": 90, "lc": 40}, {"loan": None, "lc": "lc"}, {"lc": [1]}, bal)
    assert k3 == {"loan": 75, "lc": 25} and after == [0, 5]
    print("a loan of 90 and a letter of credit of 40, facility 100, sublimit 30:", {k: str(x) for k, x in k3.items()}, "balances after", after)
    print("the sketch's example: reading A", [reading_a(d) for d in (1, 2, 4)], "reading B where the account rations", [reading_b(d, True) for d in (1, 2, 4)],
          "where it refuses", [reading_b(d, True, refuser) for d in (1, 2, 4)], "and charged in full", [reading_b(d, False) for d in (1, 2, 4)])


def main():
    scale = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    examples()
    print("whole units:", search_units(200_000 // scale, 21))
    print("ranks, exact amounts:", search_ranks(100_000 // scale, 22, False))
    print("ranks, whole units:", search_ranks(200_000 // scale, 23, True))
    print("credits, sums and readings:", search_history(60_000 // scale, 24))
    print("merge and its refusals, exact amounts:", search_merge(100_000 // scale, 25, False))
    print("merge and its refusals, whole units:", search_merge(100_000 // scale, 26, True))
    print("pots, exact amounts:", search_pots(60_000 // scale, 27, False))
    print("pots, whole units:", search_pots(100_000 // scale, 28, True))
    print("allocation across accounts, exact amounts:", search_spread(60_000 // scale, 29, False))
    print("allocation across accounts, whole units:", search_spread(100_000 // scale, 30, True))
    for family in ("exact", "priority", "units"):
        print(f"purposes at one position, {family}:", search_purposes(60_000 // scale, 31, family))


if __name__ == "__main__":
    main()
