<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger posting scenarios, for the maintainer's rulings

**Written** 2026-11-09 on `docs/placement-vehicles-structure`, at the maintainer's request after LG-Q11 was decided, to inform the ledger's open modelling questions. **Status:** waiting on the maintainer's rulings. Each scenario is invented, with round numbers and no real party, contract or market.

## How to use this note

Each scenario states a generic premise first, then one instance from a domain, the question it raises, and the readings that are possible. Write your ruling under **Ruling**, in your own words, including "none of these" with what should happen instead. The **Bears on** line names the open question or law the ruling informs, so a ruling can be carried to the plan's row afterwards.

Terms, as the ledger uses them.

- **Account**, an amount consumed and restored, with a **stated amount**, a **parent** and a **credit ceiling**.
- **Availability**, the least remaining balance along an account's path to its root.
- **Position**, a point in the order of events. Proposals at one position are seen together and merged by the account's **merge rule**, proportional, in priority or refuse.
- **Grant**, what a merge gives a proposal. **Posting**, a debit or credit written to an account. **Residual**, what a split leaves unallocated.

The open questions these scenarios bear on, as the [ledger plan](../plans/ledger.md) states them:

| ID | In brief |
|---|---|
| LG-Q10 | how a pool that caps an aggregate's reinstatements is built, now that a credit rolls up |
| LG-Q12 | whether an allocation across several accounts commits whole, and whether the account order is declared data |
| LG-Q13 | whether an allocated amount with a purpose debits the accounts that count that purpose |
| LG-Q15 | how the first-in-order residual rule treats a key of zero weight |
| LG-Q16 | what a rounding method means beside a residual rule, and whether a residual may be negative |
| LG-Q17 | whether a rule may leave an explicit residual where requests cannot be met exactly |
| PDD-14 | where a posting effective inside a sealed period goes |

## A. Requests that cannot be split

### A1. Seats in blocks (software licensing)

**Premise.** A request is for a quantity that is useless in part.

**Instance.** A seat pool has 7 seats left. At one position, team A asks for a block of 5 seats and team B for a block of 4. Each block serves one site, so 3 seats for team A are of no use to it.

```
pool: 7 left       A asks 5 (whole or not at all)
                   B asks 4 (whole or not at all)
```

**Question.** What is granted, and what is posted?

| Reading | A | B | Residual | Note |
|---|---|---|---|---|
| (i) grant what fits, in order | 5 | 0 | 2 | your reading on 2026-11-09 |
| (ii) grant what fits, largest first | 5 | 0 | 2 | the same here, differs in A2 |
| (iii) proportional, then round down to whole blocks | 0 | 0 | 7 | 3.9 and 3.1 seats are not blocks |
| (iv) refuse both | 0 | 0 | 7 | the pool's policy is refuse |

**Bears on** LG-Q17. **Ruling.**

### A2. Blocks where the order decides who is served (software licensing)

**Instance.** As A1, with 7 seats left, but three blocks are asked for at one position: A 4, B 3, C 5, in that key order.

| Reading | Granted | Residual |
|---|---|---|
| (i) in key order, each whole if it fits | A 4, B 3, C 0 | 0 |
| (ii) largest first, each whole if it fits | C 5, then A and B do not fit | 2 |
| (iii) the combination that leaves the least residual | A 4 and B 3 | 0 |

**Question.** Is the choice of who is served a rule the account declares, and is the key order contractual data or an accident of identifiers?

**Bears on** LG-Q17, LG-Q12. **Ruling.**

### A3. A minimum participation (syndicated lending)

**Premise.** A share below a floor is not taken up at all.

**Instance.** A borrower draws 10M from a facility shared by three lenders whose remaining commitments are 6M, 3M and 1M. Pro rata gives 6M, 3M and 1M exactly. The facility agreement says no lender funds a drawing below 2M.

**Question.** Lender C's share is 1M, below the floor. What happens?

| Reading | Lender A | Lender B | Lender C | Drawing funded |
|---|---|---|---|---|
| (i) C funds nothing, the drawing is 9M | 6M | 3M | 0 | 9M, residual 1M |
| (ii) C funds nothing, A and B take C's share pro rata | 6.67M | 3.33M | 0 | 10M |
| (iii) the whole drawing is refused | 0 | 0 | 0 | 0 |
| (iv) the floor applies to the lender's commitment, not its share, so C funds 1M | 6M | 3M | 1M | 10M |

**Bears on** LG-Q17, and whether a floor is a rule's parameter or a guard per request. **Ruling.**

## B. Requests that stand or fall together

### B1. A bundle at one position (project finance)

**Premise.** Several requests must all be met or none.

**Instance.** A construction loan has 8M available. At one position the borrower requests three drawings, 4M for materials, 3M for labour and 2M for equipment, under a condition that all three fund together or none does. 9M is asked against 8M.

**Question.** Is this the account's refuse policy, or something the requests carry?

| Reading | Outcome |
|---|---|
| (i) the account's policy is refuse, so the merge is refused | nothing funds, the reason is that requests exceed availability |
| (ii) the bundle is a property of these requests, the account otherwise splits proportionally | nothing funds, because the bundle cannot be met whole |
| (iii) the account splits proportionally, and the bundle condition is the borrower's problem | 3.56M, 2.67M and 1.78M fund |

**Bears on** LG-Q11 as decided, and whether a bundle is ever declared on requests rather than on the account. **Ruling.**

### B2. A bundle across positions (project finance)

**Instance.** As B1, but the materials drawing is at position 1 and the labour drawing at position 2, under the same condition that both fund or neither. At position 1 there is room for materials. At position 2, after another borrower's drawing at position 1.5, there is not room for labour.

**Question.** Is the materials drawing at position 1 posted, and if so, is it reversed at position 2?

| Reading | Outcome |
|---|---|
| (i) out of scope, each position merges alone | materials funds, labour is refused |
| (ii) materials is held unposted until labour is decided | a pending state the ledger does not have |
| (iii) materials funds, and a reversal is posted at position 2 | two postings and a reversal |

**Bears on** a bundle across positions, which you placed out of scope on 2026-11-09. Ruling only if you want it recorded. **Ruling.**

### B3. Matched funding (research grants)

**Premise.** One account may be debited only if another account is debited by a stated proportion at the same time.

**Instance.** A grant pays 50% of equipment costs, the institution's own fund pays the other 50%. A 400k purchase draws 200k from the grant and 200k from the institution's fund. The grant has 200k left, the institution's fund 150k.

| Reading | Grant | Institution | Purchase |
|---|---|---|---|
| (i) both or neither | 0 | 0 | refused |
| (ii) scale both to what the smaller allows | 150k | 150k | 300k |
| (iii) each takes what it can | 200k | 150k | 350k, the match broken |

**Bears on** LG-Q12, an allocation across accounts that commits whole. **Ruling.**

## C. Rounding and the residual

### C1. Three equal claims on an odd amount (insurance, an aggregate)

**Premise.** An amount does not divide evenly in whole minor units.

**Instance.** An aggregate limit has 100.00 left, in cents 10,000. Three losses of equal size reach it at one position, and its merge rule is proportional. Each exact share is 3,333.33 cents.

| Reading | Loss 1 | Loss 2 | Loss 3 |
|---|---|---|---|
| (i) the odd cent to the first in order | 3,334 | 3,333 | 3,333 |
| (ii) the odd cent to the largest remainder, ties in key order | 3,334 | 3,333 | 3,333 |
| (iii) the odd cent stays unallocated | 3,333 | 3,333 | 3,333, residual 1 |

**Question.** Is (iii) ever right, and is the key order of losses their order of notification, of occurrence, or of identifier?

**Bears on** LG-Q15, LG-Q12. **Ruling.**

### C2. A participant with nothing at stake (syndicated lending)

**Premise.** A key whose weight is zero is present in the split.

**Instance.** A 1-unit fee is shared among three lenders by their outstanding loans, 0, 300 and 300. The lender with nothing outstanding is first in key order.

| Reading | Lender 1 (0) | Lender 2 (300) | Lender 3 (300) |
|---|---|---|---|
| (i) first in order, whatever the weight | 1 | 0 | 0 |
| (ii) first in order among those with a stake | 0 | 1 | 0 |
| (iii) largest remainder | 0 | 1 | 0 |

**Bears on** LG-Q15. **Ruling.**

### C3. Rounding to the nearest overshoots (insurance, a quota share)

**Premise.** Rounding each share to the nearest unit can sum to more than the whole.

**Instance.** A loss of 200 units is shared among three participants of equal share. Each exact share is 66.67. Rounded half-even, each is 67, and the three sum to 201.

| Reading | Outcome |
|---|---|
| (i) the rounding method applies only to how a share is shown, and the split is floor then residual | 67, 67, 66 by largest remainder |
| (ii) round to nearest, then take one unit back, from the last in order | 67, 67, 66 |
| (iii) round to nearest, then take one unit back, from the share rounded up the most | 67, 67, 66, the tie broken by key order |
| (iv) refuse a half-even method beside a residual rule | the configuration is invalid |

**Bears on** LG-Q16. **Ruling.**

### C4. A drawing in another currency (multi-currency lending)

**Premise.** A request in one unit draws on an account in another.

**Instance.** A revolving facility of 10M in one currency is drawn for 1M in another, at a rate that gives 1,234,567.891 in the facility's unit. The facility's unit has two decimal places.

**Question.** Which rounding applies, the conversion's or the facility's, and where does any difference go, to the borrower, the facility, or a residual account?

**Bears on** LG-Q16, and LG-Q8 on conversion. **Ruling.**

## D. Allocation across several accounts

### D1. A waterfall with a frozen tranche (insolvency)

**Premise.** An amount is distributed down a sequence of accounts in order, and one account cannot take its part.

**Instance.** A recovery of 1M is distributed to senior creditors owed 600k, then mezzanine owed 300k, then junior owed 500k. The mezzanine account is frozen by a court order at the moment of distribution.

| Reading | Senior | Mezzanine | Junior | Held |
|---|---|---|---|---|
| (i) the whole distribution waits | 0 | 0 | 0 | 1M |
| (ii) mezzanine's part is held, the rest flows | 600k | 0 | 100k | 300k |
| (iii) mezzanine is skipped, junior takes its place | 600k | 0 | 400k | 0 |

**Bears on** LG-Q12. **Ruling.**

### D2. A sublimit that counts a purpose (trade finance)

**Premise.** An account counts a purpose, so any draw for that purpose also debits it, wherever the draw lands.

**Instance.** A facility of 20M has a letters-of-credit sublimit of 5M that counts every draw made for letters of credit. A single drawing of 3M is split across two lenders' commitment accounts for the purpose of a letter of credit.

| Reading | Lenders' accounts | Letters-of-credit sublimit |
|---|---|---|
| (i) the allocation honours the purpose, as a single draw does | 3M in all | debited 3M |
| (ii) a purpose belongs to a draw, never to an allocation | 3M in all | untouched |
| (iii) a purpose on an allocation is Undetermined | refused | untouched |

**Bears on** LG-Q13. **Ruling.**

### D3. Allocation that runs out mid-sequence (research grants)

**Instance.** A 90k purchase is charged first to a project budget with 50k left, then to a department budget with 30k left. The last 10k has nowhere to go.

| Reading | Project | Department | Outcome |
|---|---|---|---|
| (i) charge what fits, 10k unallocated | 50k | 30k | residual 10k, the purchase partly funded |
| (ii) refuse the whole purchase | 0 | 0 | refused |

**Bears on** LG-Q12, LG-Q17. **Ruling.**

## E. Restoring and recovering

### E1. A reinstatement under a pool (insurance)

**Premise.** Restoring a child account restores its parent too, because a credit rolls up, and the parent may be a cap that should not be restored.

**Instance.** An aggregate of 10M allows one reinstatement and sits under a pool of 20M that caps the total paid across the aggregate and its reinstatement. A loss exhausts the aggregate, and the pool has 10M left. The reinstatement restores the aggregate to 10M.

```
pool 20M         after the loss: 10M left
  aggregate 10M  after the loss: 0 left, then reinstated to 10M
```

| Reading | Aggregate after | Pool after |
|---|---|---|
| (i) the credit rolls up as any credit does | 10M | 20M, the cap lost |
| (ii) a reinstatement credits its own account only | 10M | 10M |
| (iii) a credit at the aggregate that rolls up, and a debit at the pool that takes it back, as the insurance example does today | 10M | 10M, right in sum, with a posting in the pool's own book |

**Bears on** LG-Q10, leaning a credit that carries its kind. **Ruling.**

### E2. A recovery larger than the period's payments (insurance, salvage)

**Premise.** A credit arrives that would lift an account above what it was stated to hold.

**Instance.** A sublimit of 1M paid 400k this period. Salvage on a loss paid last period recovers 700k.

| Reading | Sublimit after | Where the 300k beyond the ceiling goes |
|---|---|---|
| (i) stopped at the ceiling, the excess is a residual | 1M | a residual account |
| (ii) stopped at the ceiling, the excess goes to the parent | 1M | the parent, if it has room |
| (iii) the recovery is credited to the period of the original loss | 1M this period | last period, which is sealed |

**Bears on** the running balance LG-9 proves, PDD-14. **Ruling.**

### E3. A loss reported after its year closed (insurance)

**Premise.** A posting is effective inside a sealed period.

**Instance.** A loss that occurred in a year whose books closed is reported three months into the next year. The year's aggregate had 2M left at its close.

| Reading | Outcome |
|---|---|
| (i) posted to the sealed year, which is reopened and resealed | the year's book changes, its digest is reissued |
| (ii) posted to the current year with its effective position in the old year | the old year's checkpoint is stale, a correction posting follows it |
| (iii) posted to a late-posting graph of the old year, read beside its sealed book | the sealed book stays sealed |

**Bears on** PDD-14. **Ruling.**

## F. Order and time

### F1. Ties broken by key order (any domain)

**Premise.** Two requests are equal in every respect the rule reads.

**Instance.** Two requests of 50 each reach an account with 75 left, merged in priority. Neither has a stated priority, and their identifiers are a random token.

**Question.** Is key order, which here is the order of random tokens, an acceptable tie-break, or must every account that can tie declare an order that means something?

**Bears on** LG-Q12. **Ruling.**

### F2. Two positions that are the same moment (payments)

**Premise.** Events stamped at the same time arrive in different passes.

**Instance.** Two card authorisations stamped to the same millisecond reach a spending limit with room for one of them. They are recorded in different passes, because they arrived at different nodes.

**Question.** Is this one position, merged, or two, the first recorded winning?

**Bears on** the pass-wide order rule of LG-Q9 (a), pass position then micro-position. **Ruling.**
