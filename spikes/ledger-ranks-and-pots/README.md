<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Spike: ranks on a ledger account, as tiers and as pots

**Status:** a spike, not production. It defines no interface and changes no tool. Nothing in `tools/`, `benchmark/` or `platform/` imports it.

**Origin:** the ruling on scenario G1 of the [posting scenarios note](../../docs/developer/notes/ledger-posting-scenarios.md) on 2026-11-15, which rested on two claims nobody had checked. The spike tried both before they were planned as proofs, in slice LG-20 of the [ledger plan](../../docs/developer/plans/ledger.md).

## What it asks, and what it found

`model.py` transliterates the kernel's `available`, `debit`, `merge` and `settle_at` from `tools/proofs/ledger/Kernel.thy`, adds a rule for whole units that reads no order, and serves ranks two ways, as tiers of one account and as pots under a fund. It draws cases from fixed seeds and asserts each law on each case.

| Claim | Found, run of 2026-11-15 |
|---|---|
| in whole units, a residual kept explicit lets requests of one rank share with no order among them | the kernel's `largest_remainder` grants three requests of 5 sharing 10 as 4, 3 and 3, by key order. The rule with no order grants 3 each and leaves 1. Over 300,000 cases it kept every law asserted, with a residual in 29,822 of them and never more than 4, one less than the largest rank |
| a rank held as a pot needs no new mechanism | with exact amounts, `settle_at` at each pot in rank order equals tiers in all 60,000 cases. In whole units it differs in 9,512 of 200,000, each a unit the higher rank could not place paid to a lower one. Withholding that unit from the later pots, or posting it out, equals tiers in all 200,000 |
| the same with an amount of its own on some pots | every law asserted held in 60,000 cases with exact amounts and 200,000 in whole units |

The laws asserted are in the two search functions: every grant within its request, the grants and the residual summing to the amount shared, no lower rank paid while a higher one is short, equal requests granted equally, the same grants under a renaming of the keys, no balance below zero, and no pot paid beyond its own amount.

## Running it

From the repository root. It needs the standard library only.

```bash
mise exec -- python spikes/ledger-ranks-and-pots/model.py
```

It prints one line a search and stops at the first case that breaks a law. Pass a divisor for a shorter run, for example `model.py 20`.

## What it does not show

It proves nothing. The cases are random, with one to four ranks of one to five requests of 0 to 12 units, and the pots sit directly under one fund. The four kernel functions are transliterated by hand into Python, so a slip there would go unseen. The proofs are LG-20's.
