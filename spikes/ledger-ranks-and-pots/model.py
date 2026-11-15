# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""A model of ranks on a ledger account, searched for a case that breaks a law before the law is stated for proof.

It transliterates four definitions of the ledger kernel (`tools/proofs/ledger/Kernel.thy`), `available`, `debit`, `merge` and `settle_at`, and adds what the kernel does not have yet:
a rule for whole units that reads no order, ranks served as tiers of one account, and ranks held as pots under a fund. A run draws random cases from fixed seeds and asserts each law
on each case, so it stops at the first counterexample. It proves nothing. Run it with `mise exec -- python spikes/ledger-ranks-and-pots/model.py`, or with a divisor such as `20` for a
short run."""

from __future__ import annotations

import random
import sys
from fractions import Fraction

UNLIMITED = 10**9  # a pot with no amount of its own


# Rules. Each takes the requests of one rank and the amount to share, which is less than the requests in all, and returns the grants.


def proportional(reqs, x):
    """The kernel's exact rule, over rationals."""
    asked = sum(reqs.values())
    return {k: (Fraction(x) * v / asked if asked else Fraction(0)) for k, v in reqs.items()}


def largest_remainder(reqs, x):
    """The kernel's rule for whole units. It places every unit, and settles equal remainders by the order of the keys."""
    asked = sum(reqs.values())
    if asked == 0:
        return {k: 0 for k in reqs}
    floor = {k: x * v // asked for k, v in reqs.items()}
    left = x - sum(floor.values())
    order = sorted(sorted(reqs), key=lambda k: -((x * reqs[k]) % asked))
    return {k: floor[k] + (k in order[:left]) for k in reqs}


def units_with_no_order(reqs, x):
    """Whole units with no order read. A leftover unit goes to a key only where the remainders decide it, and what they do not decide is left unplaced, to be the residual."""
    asked = sum(reqs.values())
    if asked == 0:
        return {k: 0 for k in reqs}
    floor = {k: x * v // asked for k, v in reqs.items()}
    left = x - sum(floor.values())
    if left == 0:
        return floor
    rem = {k: (x * reqs[k]) % asked for k in reqs}
    cut = sorted(rem.values(), reverse=True)[left - 1]
    above = [k for k in reqs if rem[k] > cut]
    at_cut = [k for k in reqs if rem[k] == cut]
    take = set(above) | (set(at_cut) if len(above) + len(at_cut) == left else set())
    return {k: floor[k] + (k in take) for k in reqs}


# The kernel, transliterated.


def path(parent, a):
    out = [a]
    while parent.get(out[-1]) is not None:
        out.append(parent[out[-1]])
    return out


def available(parent, bal, a):
    return min(bal[b] for b in path(parent, a))


def debit(accounts, x, bal):
    return {b: (v - x if b in accounts else v) for b, v in bal.items()}


def merge(rule, av, reqs):
    return dict(reqs) if sum(reqs.values()) <= av else rule(reqs, max(0, av))


def settle_at(rule, parent, a, reqs, bal):
    grants = merge(rule, available(parent, bal, a), reqs)
    return grants, debit(path(parent, a), sum(grants.values()), bal)


def shared(av, reqs):
    """The amount a merge shares, the lesser of what was asked and what is available."""
    return min(sum(reqs.values()), max(0, av))


# Ranks as tiers of one account.


def tiers(av, ranked, rule, spill=False):
    """The ranks in order against one amount. A rank that falls short stops every rank after it, and what its rule could not place is the residual. With `spill`, a later rank may
    take what an earlier one could not place, which is the behaviour the search shows to be wrong."""
    out, left, residual = [], av, 0
    for reqs in ranked:
        grants = merge(rule, left, reqs)
        out.append(grants)
        paid = sum(grants.values())
        if spill:
            left -= paid
        else:
            residual += shared(left, reqs) - paid
            left -= shared(left, reqs)
    return out, residual


# Ranks as pots, each an account under the fund.


def pots_bare(rule, parent, pots, ranked, bal):
    """`settle_at` at each pot in rank order, and nothing else."""
    out = []
    for a, reqs in zip(pots, ranked):
        grants, bal = settle_at(rule, parent, a, reqs, bal)
        out.append(grants)
    return out, bal, 0


def pots_posted(rule, parent, pots, ranked, bal):
    """As `pots_bare`, with what a pot could not place posted out of it to a residual account."""
    out, posted = [], 0
    for a, reqs in zip(pots, ranked):
        x = shared(available(parent, bal, a), reqs)
        grants, bal = settle_at(rule, parent, a, reqs, bal)
        residual = x - sum(grants.values())
        bal = debit(path(parent, a), residual, bal)
        posted += residual
        out.append(grants)
    return out, bal, posted


def pots_held(rule, parent, pots, ranked, bal):
    """As `pots_bare`, with what a pot could not place left in the balances and withheld from what the later pots see of the fund at this position."""
    out, held = [], 0
    for a, reqs in zip(pots, ranked):
        seen = debit(["fund"], held, bal)
        x = shared(available(parent, seen, a), reqs)
        grants = merge(rule, available(parent, seen, a), reqs)
        bal = debit(path(parent, a), sum(grants.values()), bal)
        held += x - sum(grants.values())
        out.append(grants)
    return out, bal, held


# The searches.


def draw_ranks(rng):
    return [{f"r{t}k{i}": rng.randint(0, 12) for i in range(rng.randint(1, 5))} for t in range(rng.randint(1, 4))]


def equal_requests_equal_grants(grants, ranked):
    return all(r[a] != r[b] or g[a] == g[b] for g, r in zip(grants, ranked) for a in r for b in r)


def search_tiers(rule, exact, cases, seed):
    """Tiers with the residual kept: bounds, conservation, priority between ranks, equal treatment, a residual below the size of the rank that fell short, and no dependence on the keys."""
    rng = random.Random(seed)
    found = {"cases": 0, "with a residual": 0, "largest residual": 0, "spilling would differ": 0}
    for _ in range(cases):
        ranked = draw_ranks(rng)
        asked = sum(sum(r.values()) for r in ranked)
        av = rng.randint(0, asked + 5)
        grants, residual = tiers(av, ranked, rule)
        assert all(0 <= g[k] <= r[k] for g, r in zip(grants, ranked) for k in r), "a grant outside its request"
        assert sum(sum(g.values()) for g in grants) + residual == min(asked, av), "the grants and the residual are not the amount shared"
        short = [i for i, (g, r) in enumerate(zip(grants, ranked)) if any(g[k] < r[k] for k in r)]
        if short:
            assert all(v == 0 for g in grants[short[0] + 1 :] for v in g.values()), "a lower rank was paid while a higher one was short"
            assert exact or residual < len(ranked[short[0]]), "the residual is as large as the rank that fell short"
        assert not exact or residual == 0, "an exact rule left a residual"
        assert equal_requests_equal_grants(grants, ranked), "equal requests, unequal grants"
        renamed = [dict(sorted(((k[::-1], v) for k, v in r.items()), key=lambda kv: rng.random())) for r in ranked]
        again, residual_again = tiers(av, renamed, rule)
        assert [{k[::-1]: v for k, v in g.items()} for g in again] == grants and residual_again == residual, "renaming the keys changed the result"
        found["cases"] += 1
        found["with a residual"] += residual > 0
        found["largest residual"] = max(found["largest residual"], residual)
        found["spilling would differ"] += tiers(av, ranked, rule, spill=True)[0] != grants
    return found


def search_pots(rule, exact, cases, seed, capped):
    """Pots against tiers, and the laws of a pot with an amount of its own: no balance below zero, no pot paid beyond its amount, the fund down by what was paid, and a later pot paid
    only where the fund did not bind on an earlier one."""
    rng = random.Random(seed)
    found = {"cases": 0, "bare pots differ from tiers": 0, "with a residual": 0, "with a pot's own amount binding": 0}
    for _ in range(cases):
        ranked = draw_ranks(rng)
        asked = sum(sum(r.values()) for r in ranked)
        fund = rng.randint(0, asked + 5)
        pots = [f"pot{t}" for t in range(len(ranked))]
        parent = {p: "fund" for p in pots}
        cap = {p: (rng.randint(0, sum(r.values()) + 2) if capped and rng.random() < 0.5 else UNLIMITED) for p, r in zip(pots, ranked)}
        start = {"fund": fund, **cap}
        results = {name: fold(rule, parent, pots, ranked, start) for name, fold in (("bare", pots_bare), ("posted", pots_posted), ("held", pots_held))}
        for name, (grants, bal, residual) in results.items():
            paid = [sum(g.values()) for g in grants]
            assert all(v >= 0 for v in bal.values()), f"{name}: a balance below zero"
            assert all(0 <= g[k] <= r[k] for g, r in zip(grants, ranked) for k in r), f"{name}: a grant outside its request"
            assert all(p <= c for p, c in zip(paid, cap.values())), f"{name}: a pot paid more than its amount"
            assert bal["fund"] == fund - sum(paid) - (residual if name == "posted" else 0), f"{name}: the fund is not down by what was paid"
            assert equal_requests_equal_grants(grants, ranked), f"{name}: equal requests, unequal grants"
            if name == "bare":
                continue
            for i, reqs in enumerate(ranked):
                if any(paid[j] > 0 for j in range(i + 1, len(ranked))):
                    full = min(sum(reqs.values()), cap[pots[i]])
                    assert paid[i] == full or (not exact and full - paid[i] < len(reqs)), f"{name}: a later pot was paid while the fund bound on an earlier one"
        assert results["posted"][0] == results["held"][0], "posting the residual and holding it give different grants"
        if not capped:
            as_tiers = tiers(fund, ranked, rule)[0]
            assert results["held"][0] == as_tiers and results["posted"][0] == as_tiers, "pots differ from tiers"
            found["bare pots differ from tiers"] += results["bare"][0] != as_tiers
        found["cases"] += 1
        found["with a residual"] += results["posted"][2] > 0
        found["with a pot's own amount binding"] += any(c < sum(r.values()) for c, r in zip(cap.values(), ranked))
    return found


def main():
    scale = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    three = {"a": 5, "b": 5, "c": 5}
    assert largest_remainder(three, 10) == {"a": 4, "b": 3, "c": 3}
    assert units_with_no_order(three, 10) == {"a": 3, "b": 3, "c": 3}
    assert tiers(10, [three, {"d": 3}], units_with_no_order) == ([{"a": 3, "b": 3, "c": 3}, {"d": 0}], 1)
    assert tiers(10, [three, {"d": 3}], units_with_no_order, spill=True)[0][1] == {"d": 1}
    print("three requests of 5 sharing 10, by the kernel's largest remainder:", largest_remainder(three, 10))
    print("the same with no order read:", units_with_no_order(three, 10), "and 1 left")
    print("tiers, exact amounts:", search_tiers(proportional, True, 100_000 // scale, 1))
    print("tiers, whole units:", search_tiers(units_with_no_order, False, 300_000 // scale, 2))
    print("pots, exact amounts:", search_pots(proportional, True, 60_000 // scale, 11, False))
    print("pots with amounts, exact:", search_pots(proportional, True, 60_000 // scale, 12, True))
    print("pots, whole units:", search_pots(units_with_no_order, False, 200_000 // scale, 13, False))
    print("pots with amounts, whole units:", search_pots(units_with_no_order, False, 200_000 // scale, 14, True))


if __name__ == "__main__":
    main()
