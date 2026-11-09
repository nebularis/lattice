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

**Bears on** LG-Q17, LG-Q12. **Ruling.** The maintainer, 2026-11-09. The order is contractual data. Reading (i) holds where the wording says requests are served in an order, for example in the order notified, and reading (ii) where it says they are served by size. Reading (iii), the combination that leaves the least residual, does not stand as a rule a contract states. Where an allocation like it arises, an allocator chooses it before the ledger sees the requests, as an arranger sizes lenders' tickets or an issuer allots shares in round lots, and the ledger merges what was chosen.

Two points of English law bear on the order and are recorded for modelling, to be checked against the judgments before any wording relies on them. Under liability insurance with a limit too small for every claim, claims exhaust the cover in the order the insured's liability is ascertained, by judgment, award or settlement, and neither the insured nor the insurer chooses another order (*Teal Assurance v W R Berkley* [2013] UKSC 57, following *Post Office v Norwich Union* [1968] and *Bradley v Eagle Star* [1989]). An insurer paying claims chronologically from a limited fund was held legitimate (*Cox v Bankside Members Agency* [1995] 2 Lloyd's Rep 437). So a contract may state an order, and where it states none the law supplies one, which the ledger needs to name as a default and not leave to identifiers. In an insurer's winding up, insurance debts rank after preferential debts and equally among themselves (the Insurers (Reorganisation and Winding Up) Regulations 2004, regulation 21), so no order applies there, and a payment chosen to favour some creditors as insolvency approaches risks being set aside as a preference (Insolvency Act 1986 section 239, *Re M C Bacon* [1990]) and engages the directors' duty to consider creditors (*BTI 2014 v Sequana* [2022] UKSC 25).

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

**Bears on** LG-Q17, and whether a floor is a rule's parameter or a guard per request. **Ruling.** The maintainer, 2026-11-09. It depends on the wording, and the ledger never decides it. Where the floor gates the lenders' obligation to pay and nothing in the wording says what follows, choosing between (i) and (iii) would be arbitrary, so the drawing is not funded, with a referral to a person who may put a remedy in place, since paying when it is unclear how lender C's obligation behaves is not defensible. Where the wording says what happens when a lender cannot pay, or when a lender's commitment falls below the minimum, that wording's stated meaning decides, bound per instrument, and (i), (ii) or (iii) may each be right. Whether (iv) differs from the others depends on how the wording defines commitment and share, which is stated meaning too.

#### A3 worked through: how an instrument can state the floor

The instrument layer states a clause as legal relations, each with one modal verb, and a relation applies to a case only when it exists, its gate is open and its scope admits the case. The table names each way the floor of A3 can be stated in those terms, and which outcomes of A3 each allows. *Yes* means the form yields that outcome by itself. *With* names what else the wording must state.

| How the floor is stated | Instrument terms | (i) C funds 0, drawing 9M | (ii) A and B take up C's share | (iii) the drawing is not funded | (iv) C funds 1M |
|---|---|---|---|---|---|
| F1. A prohibition on the lender, "no lender shall fund a participation below 2M" | `ins:Prohibition`, obligor the lender, `ins:scope` the participation below the floor | yes | with an obligation on the others to take up a shortfall | with a condition on the borrower's drawing that every lender funds | no, C must not |
| F2. The lender's obligation does not reach a small participation, "each lender shall fund its participation, if it is 2M or more" | `ins:Obligation`, `ins:scope` the participation at or above the floor | yes | with a take-up obligation | with the drawing conditioned on every lender funding | only if C chooses to, which no relation obliges, so it is C's act and not an outcome the evaluator reaches |
| F3. The lender is excused, "a lender need not fund a participation below 2M" | `ins:Exclusion`, holder the lender, `ins:excepts` its obligation | if C does not act | with a take-up obligation | with the drawing conditioned on every lender funding | if C elects to fund, an `ins:OnAct` by C |
| F4. A minimum on the obligation's amount | `ins:Qualifier` qualifying the obligation to fund | not without more, since a qualifier bounds an amount and does not say what happens below it | with a take-up obligation | the reading where an obligation whose amount cannot meet its qualifier is not performed, which the evaluator cannot choose alone | only if the qualifier bounds the commitment and not the participation, by definition |
| F5. A condition on the borrower's power to draw, "a utilisation may be requested only if every lender's participation is 2M or more" | `ins:Power` of the borrower, `ins:scope` every participation at or above the floor | no | no | yes, the drawing is never validly requested | no |
| F6. A regime with a state for a lender below the floor, "if any lender's commitment falls below 2M, no utilisation may be made until the majority lenders consent" | `ins:Regime`, `ins:OnCondition`, the borrower's power gated by `ins:appliesInState`, and a `ins:Power` of the majority lenders to consent | after consent, if the consent says so | after consent, if the consent says so | yes, while the regime is in that state | after consent, if the consent says so |
| F7. Silence, the floor stated and its effect not | any of F1 to F4, chosen by whoever binds the meaning | arbitrary | arbitrary | the maintainer's ruling, not funded with a referral | arbitrary |

Three properties of the wording decide among the rows, each stated meaning, never the ledger's.

| Property | Where it is stated | What it does to A3 |
|---|---|---|
| what the floor is measured on, the commitment or the participation in the drawing | `ins:Definition` of each word | decides whether (iv) is a different outcome at all. Where commitment and participation are defined apart and the floor reads the commitment, C, whose commitment may be above 2M, funds its 1M participation |
| how the lenders act together, each for its own share or jointly | `ins:actingRule` on the lenders' participation group | under each for its own share, one lender's failure does not oblige the others, so (ii) needs an express obligation to take up a shortfall. Under jointly, (ii) is the default |
| which relation the floor attaches to, the lender's obligation or the borrower's power | the relation's obligor or holder | on the lender, F1 to F4, the drawing proceeds unless something else stops it. On the borrower, F5 and F6, the drawing does not proceed |

**What the matrix rules out.** No outcome is invalid under every form. (iii) is reached by F5 and F6, and by the ruling for silence. (i) is reached by F1 to F3. (ii) needs a take-up obligation or a joint acting rule. (iv) needs a definition that separates commitment from participation, or an exclusion and C's own act. So each of the four is right for some wording, which confirms the ruling: the outcome is the bound meaning's, and the ledger merges only what the instrument says applies.

**What the matrix says about the ledger.** The floor never reaches a merge rule. By the time requests reach a merge at one position, the instrument has decided which lenders' obligations apply to this drawing and for how much. A drawing the instrument leaves Undetermined, as F7 does, or gates closed, as F6 does, is never a merge's refusal, which LG-Q11 kept to the account's own refuse policy when requests exceed availability. The referral the ruling asks for is the instrument's Undetermined with its reason, and the remedy is a regime state left by an act, as F6 shows. No term in the repository names a referral as such, so whether one is needed beside Undetermined with a reason is a question for the instrument layer.


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

**Bears on** LG-Q11 as decided, and whether a bundle is ever declared on requests rather than on the account. **Ruling.** The maintainer, 2026-11-09. Reading (i) is the account's wording, since a refuse policy is stated on the account and never on a request. Reading (ii) is possible, since a request may carry terms of its own, but the mechanism needs designing, and this instance cannot tell (ii) from (i), because a drawing is asked for whole as a quote is. The answer is again the wording's, and what varies between uses is where that wording comes from. The maintainer gave a better instance, worked through below.

#### B1 worked through: a dental claim with line items

**The limits.** An annual aggregate of £5,000. An annual sub-limit for orthodontic work of £550. A per-claim limit of £500 on all authorised work together. A write-back puts 50% of treatment at a participating dentist back onto the aggregate.

**The history.** £4,300 has been paid this year, none of it orthodontic, so £700 of the aggregate remains.

| Step | Claim | Lines | Outcome | Aggregate left | Orthodontic left |
|---|---|---|---|---|---|
| 1 | £700 | orthodontic £200, other treatment £300, hygiene £200 | refused, over the per-claim limit, although it fits the aggregate and the orthodontic sub-limit | £700 | £550 |
| 2 | £500, resubmitted without the hygiene line | orthodontic £200, other treatment £300 | paid | £700 − £500 = £200 | £350 |
| 3 | write-back of 50% of the £500 | | credited to the aggregate | £200 + £250 = £450 | £350 |
| 4 | £400 | orthodontic £400 | refused, or £350 paid, as the wording or a rule imposed on such instruments says | £450, or £100 | £350, or £0 |

**What each step exercises in the ledger.**

- **The claim is the bundle.** Its lines are drawn at one position, each on its own path, the orthodontic line through the orthodontic sub-limit to the aggregate, and every line through the claim's own per-claim account, an account per claim by a key dimension (LG-Q7). Step 1 refuses the whole claim because one account on one path cannot take it, which is a draw that succeeds whole or changes nothing (LD1), applied to every line of the claim together. That is an allocation across accounts that commits whole, LG-Q12's (a), with the commitment declared by the claim's terms.
- **Pay up to, or refuse, is the account's rule even for one request.** At step 4 one request exceeds availability. The kernel's merge already treats one request exactly as several: a proportional or in-priority rule grants what is available, £350, and the refuse policy refuses. So the choice the maintainer describes is the merge rule declared on the orthodontic sub-limit, and it needs no new mechanism. Under pay up to, which lines of a bundle are paid first is the declared order of A2's ruling.
- **The write-back is a credit with a kind.** It restores the aggregate by a stated share of treatment, not by reversing a draw, and the credit ceiling stops it at the aggregate's stated amount. It is LG-Q10's question from another side, a credit that carries its kind, here a benefit and not a reinstatement, and it rolls up or stays as its kind says.
- **The rule can come from two places.** The wording, "we will pay any claim for orthodontic work up to …" as an obligation to pay up to the limit, or "we will not pay any claim that exceeds the limits", as a refusal bound from the instrument. Or a rule imposed on every instrument of a kind, by the institution that uses the platform, for example in ODRL, that a claim exceeding any limit is always refused at first, or that an account always pays as much of a valid claim as it can. Either way the ledger reads one declared rule on the account. Where it came from is instantiation's, and which prevails where a wording and an imposed rule disagree is precedence between provisions, a question for the normative rule substrate and Ensemble, not the ledger. How a rule imposed on instruments is stated, from wordings or configured directly, is open.

**Reading (iii) of B1, scaling every request by the same ratio**, is wrong here because it ignores the condition the requests carry. Where nothing on a request or the account forbids it, scaling by one ratio is the right behaviour in several real settings, all across requests from different parties: an insolvent estate's dividend paid pari passu to creditors, an oversubscribed share issue scaled back pro rata, and a capped grant scheme that scales back every approved award when the fund is oversubscribed. Within one party's request, the nearest real case is an insurer's condition of average, which scales every line of a claim by the ratio of the sum insured to the value at risk, but its ratio comes from underinsurance and not from what is left on an account, so it belongs to the instrument's meaning and not to a merge.


### B2. A bundle across positions (project finance)

**Instance.** As B1, but the materials drawing is at position 1 and the labour drawing at position 2, under the same condition that both fund or neither. At position 1 there is room for materials. At position 2, after another borrower's drawing at position 1.5, there is not room for labour.

**Question.** Is the materials drawing at position 1 posted, and if so, is it reversed at position 2?

| Reading | Outcome |
|---|---|
| (i) out of scope, each position merges alone | materials funds, labour is refused |
| (ii) materials is held unposted until labour is decided | a pending state the ledger does not have |
| (iii) materials funds, and a reversal is posted at position 2 | two postings and a reversal |

**Bears on** a bundle across positions, which you placed out of scope on 2026-11-09. Ruling only if you want it recorded. **Ruling.** The maintainer, 2026-11-09. Reading (i) depends on the wording, as B1's does. Reading (ii) is a different kind of behaviour, an alternative state in which some postings are held until another state is entered, and how the instrument states it is open. Reading (iii) is a recovery, which is common, but the account is not at its centre: new terms govern it, under a regime or an obligation of its own, and the money may come back in part, late, or only after a judgment. Out of scope, sketched in the [sketch on requests across positions](../sketches/ledger-bundles-across-positions.md), with BL-20 to proceed or drop it.

### B3. Matched funding (research grants)

**Premise.** One account may be debited only if another account is debited by a stated proportion at the same time.

**Instance.** A grant pays 50% of equipment costs, the institution's own fund pays the other 50%. A 400k purchase draws 200k from the grant and 200k from the institution's fund. The grant has 200k left, the institution's fund 150k.

| Reading | Grant | Institution | Purchase |
|---|---|---|---|
| (i) both or neither | 0 | 0 | refused |
| (ii) scale both to what the smaller allows | 150k | 150k | 300k |
| (iii) each takes what it can | 200k | 150k | 350k, the match broken |

**Bears on** LG-Q12, an allocation across accounts that commits whole. **Ruling.** The maintainer, 2026-11-09. Entirely the wording's. Any of (i), (ii) or (iii) can be right, depending on how the stated meaning of the matching rule is defined.

What each reading asks of the ledger, if a wording states it.

| Reading | How a wording states it | What the ledger needs |
|---|---|---|
| (i) both or neither | the grant's obligation to pay arises only where the institution's matching amount is paid at the same time, an `ins:OnCondition` on the match | an allocation across the two accounts that commits whole or changes nothing, LG-Q12's (a) |
| (ii) both scaled to what the smaller allows | the grant pays its stated share of what is actually matched, a qualifier tying the grant's amount to the match | the two amounts drawn in a fixed ratio, the larger cut to keep it, which is a rule across accounts that no merge rule on one account states |
| (iii) each takes what it can | the grant and the institution each owe their share separately, with no condition between them | two independent draws, which the ledger does now |

So the ledger has to support all three where a wording asks for them. (iii) is there now, (i) is LG-Q12's allocation that commits whole, and (ii) is the one that needs something new, two accounts drawn in a stated ratio.


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

**Bears on** LG-Q15, LG-Q12. **Ruling.** The maintainer, 2026-11-09. The order of the losses depends on legislation, the wording and its stated meaning, never on the identifiers the platform gives them, and the kernel's use of the keys' own order is a defect (TD-161). The law's order, the order of ascertainment, is a jurisdiction's Behaviour state machine over the event stream asserting the facts the ledger's rule reads, which is why the law sits outside the contract and the layering matters (PRI-82, LG-Q18). Reading (iii), leaving the odd cent unallocated, is not right unless law says otherwise, and none was found that does for this case.

The law recorded for it, to be checked against the judgments. Where claims exceed a limit, English law meets them in the order the insured's liability is ascertained (*Teal Assurance v W R Berkley* [2013] UKSC 57), and paying chronologically from a limited fund was held legitimate (*Cox v Bankside Members Agency* [1995]). Absent a rateable proportion clause, there is no rule of law sharing a shortfall pro rata between insurers, which suggests the wording, not the law, supplies a proportional split. No authority was found for losses ascertained at the same moment, which is this scenario, so the order among them falls to the wording. Leaving a cent unpaid where the losses exceed the limit leaves the insurer short of a limit it owes in full, so (iii) underpays. The one place a residual is kept by law is a rights issue's fractions worth £5 or less, sold for the company's benefit (G2), which is not this case.


### C2. A participant with nothing at stake (syndicated lending)

**Premise.** A key whose weight is zero is present in the split.

**Instance.** A 1-unit fee is shared among three lenders by their outstanding loans, 0, 300 and 300. The lender with nothing outstanding is first in key order.

| Reading | Lender 1 (0) | Lender 2 (300) | Lender 3 (300) |
|---|---|---|---|
| (i) first in order, whatever the weight | 1 | 0 | 0 |
| (ii) first in order among those with a stake | 0 | 1 | 0 |
| (iii) largest remainder | 0 | 1 | 0 |

**Bears on** LG-Q15. **Ruling.** The maintainer, 2026-11-09. Answered by the ruling on C1: the keys' order is never the right choice, so reading (i), first in key order whatever the weight, is wrong (TD-161). With the order declared, the scenario still asks whether the first lender in the declared order, who has nothing outstanding, takes the unit, which is LG-Q15's zero-weight question and is open.

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

## G. Scaling every request by one ratio

Added 2026-11-09, after the ruling on B1, as the settings where reading (iii) of B1 is the right behaviour. In each, requests from different parties exceed what is available at one position, and every request is scaled by the same ratio, which is the ledger's proportional merge rule. Each also has a complication that a bare proportional split does not carry, and that is what to rule on.

### G1. An insolvent estate's dividend (insolvency)

**Premise.** Creditors of one rank share a fund in proportion to what each is owed.

**Instance.** An estate has £1,000,000 for its unsecured creditors. Three creditors have proved, for £1,200,000, £600,000 and £200,000, £2,000,000 in all, so the dividend is 50p in the pound.

| Creditor | Proved | Dividend at 50p |
|---|---|---|
| A | £1,200,000 | £600,000 |
| B | £600,000 | £300,000 |
| C | £200,000 | £100,000 |

**What a bare proportional split does not carry.**

- **Ranks.** Secured and preferential creditors are paid before the unsecured, and creditors of one rank share equally. That is a priority between ranks and a proportional split within each, a rule over a tree of accounts or a rule of two levels.
- **Several dividends over time.** An estate often pays an interim dividend and later a final one. A creditor who proves after an interim dividend is commonly paid first out of the next one, to catch up with the others, before the rest is shared. Each dividend is a merge at its own position, and the catch-up reads what earlier positions paid.
- **Rounding.** A dividend to the penny over thousands of creditors leaves a residual, and which creditors take the odd pennies is LG-Q15's question.

**The law, in England and Wales.** Statute supplies the terms, not the parties. Classes are paid in a fixed order, each in full before the next: fixed-charge holders, the expenses of the insolvency, ordinary preferential creditors, secondary preferential creditors (since December 2020, HMRC for certain taxes), the prescribed part set aside from floating-charge realisations for the unsecured, floating-charge holders, unsecured creditors, statutory interest, then members (Insolvency Act 1986 sections 175, 176A and 176ZA, and the Insolvency (England and Wales) Rules 2016). Within a class, debts rank equally and abate in equal proportion where the fund falls short, which is pari passu. A dividend is declared by the office-holder, not paid automatically. A creditor who proves late cannot disturb a dividend already paid, and is entitled to be paid what it missed out of money available for a further dividend before that money goes to the next dividend (the Rules, rule 14.40, read from a partial extract and to be checked). Mutual dealings are set off before anything is proved, so the amounts that are divided are already net. The Rules state no rounding rule, so the treatment of odd pennies is the office-holder's practice.

**How an instrument states it.**

| What | Instrument terms |
|---|---|
| the scheme of distribution | implied terms, `ins:Term` supplied by statute, with no clause and so no stated meaning of the parties' own, bound from a statutory source |
| declaring a dividend | an `ins:Power` held by the office-holder's role, whose exercise (`ins:OnExercise`) is the position at which the fund is merged |
| the payment of each creditor's dividend | an `ins:Obligation`, obligor the estate through the office-holder, obligee each proving creditor, arising on the declaration, its amount the creditor's share |
| ranks | an order of classes, so a fund drawn across rank accounts in order, each rank's account merging its creditors proportionally, which is the allocation across accounts of LG-4 with a proportional merge at each |
| the late prover's catch-up | at the next declaration, the missed amounts drawn first in priority, then the rest proportionally, a priority tier then a proportional split |
| set-off | applied by the instrument before the proved amount is a request, never by the ledger |

**What it means for the ledger.** No new mechanism, if ranks are accounts drawn in order and each rank merges proportionally. A catch-up and G2's first lot both put a priority tier before a proportional split at one account, which is a rule of two levels or a sub-account drawn first. That is the choice G1 and G2 ask you to make.

**Questions for a ruling.** Is a rank a parent account, or a rule of two levels on one account? Is the catch-up a priority the rule reads from earlier grants, or a request of its own at the later position?

**Ruling.**

### G2. An oversubscribed share issue (capital markets)

**Premise.** Applications for a fixed quantity exceed it, and each is scaled back by the same ratio.

**Instance.** An issuer offers 10,000,000 shares. Applications total 25,000,000, so each is scaled back to 40% of what was applied for. Shares are allotted in lots of 100.

| Applicant | Applied for | 40% exactly | In whole lots of 100 |
|---|---|---|---|
| D | 12,000,000 | 4,800,000 | 4,800,000 |
| E | 8,000,050 | 3,200,020 | 3,200,000, 20 shares to the residual |
| F | 4,999,950 | 1,999,980 | 1,999,900, 80 shares to the residual |
| in all | 25,000,000 | 10,000,000 | 9,999,900, a residual of 100, one lot |

**What a bare proportional split does not carry.**

- **The unit is the lot.** The account's unit of account is a lot of 100 shares, so rounding is in lots, and the residual of 100 shares goes to one applicant by the declared residual rule.
- **A minimum allocation first.** Issues often give every applicant a first lot, or give retail applicants a set amount, before scaling the rest. That is a priority tier then a proportional split, as G1's ranks are.
- **A ballot.** Where even one lot each is more than the issue holds, lots are allotted by ballot, which is random and not a rule over the requests. A ballot is a party's act whose result the ledger records, as A2's ruling put the least-residual choice.

**The law, in England and Wales.** A prospectus invites applications, an application is the applicant's offer, and allotment is the issuer's acceptance, so an applicant has no right to any shares until allotted. Offer documents reserve the issuer's right to scale back and to choose the basis of allocation, and brokers' published policies say an applicant may receive less than applied for, by pro rata or first come first served. The basis is announced with the results, so it is often a discretion exercised once rather than a formula fixed in advance. The Royal Mail sale of 2013 gave every retail applicant for up to £10,000 the same fixed allotment and turned larger applications away, which shows a tier and a cut-off instead of a ratio. Section 578 of the Companies Act 2006 governs the other side, an issue not fully subscribed, which may be allotted only if the offer's terms say so, with application monies repaid if not. Money for shares not allotted is returned to the applicant.

A rights issue is different and closer to a fixed rule. Shareholders are entitled to new shares in proportion to what they hold, under the pre-emption rights of the Companies Act 2006 and the listing rules. Fractions are rounded down, aggregated and sold, and the proceeds go to the holder unless worth £5 or less net of expenses, when they may be sold for the company's benefit (UKLR 9.4). That is a residual rule of a kind the ledger does not yet have: the residual goes to neither key nor stays unallocated, but is turned into a sale whose proceeds are distributed or kept.

**How an instrument states it.**

| What | Instrument terms |
|---|---|
| the right to allot and to scale back | an `ins:Power` of the issuer, its exercise the allotment |
| the basis of allocation, where fixed in advance | a qualifier or a stated rule on that power, read as the merge rule of the shares account |
| the basis, where exercised as a discretion | the issuer's act, whose result reaches the ledger already sized, as A2's ruling put an allocator's choice |
| a ballot | an act recorded with its provenance, never a merge rule |
| returning money for shares not allotted | an `ins:Obligation` of the issuer to each applicant, arising on the allotment, its amount the application less what was allotted |
| a rights issue's entitlement | an `ins:Obligation` to offer each holder its proportion, a proportional rule with the residual sold |

**What it means for the ledger.** The lot as the unit of account works as it stands. The rights issue's fractions are a fourth treatment of a residual beside giving it to keys in order, to the largest remainders, or leaving it explicit (LG-Q17): sending it to a declared account whose own rule says what becomes of it. That bears on LG-Q15 to LG-Q17 together.

**Questions for a ruling.** Is a minimum first lot a tier of the rule, or a separate account drawn first? Is a ballot always an act recorded upstream, never a merge rule?

**Ruling.**

### G3. A capped grant scheme (research grants)

**Premise.** Approved awards exceed a fund, and every award is scaled back by the same ratio.

**Instance.** A scheme has £2,000,000. A panel approves awards totalling £2,500,000, so each is scaled to 80%. The scheme's terms say no award is made below £50,000, since a smaller one cannot fund the project.

| Award | Approved | 80% | Note |
|---|---|---|---|
| G | £1,500,000 | £1,200,000 | |
| H | £940,000 | £752,000 | |
| J | £60,000 | £48,000 | below the £50,000 floor |

**What a bare proportional split does not carry.**

- **A floor on the scaled award.** J falls below the floor. The award can be withdrawn and the £48,000 shared between G and H, or J paid £50,000 and the others scaled a little further, or the scaling done again without J. That is A3's floor met in a proportional split, and the same matrix of how the terms state the floor applies.
- **Commitment over time.** A grant is often awarded now and paid in instalments later, so the fund is drawn at the award and the account of each award is drawn at each instalment. The scaling happens once, at the award.

**The law, in England and Wales.** A grant scheme's published rules govern the funder, and an award becomes binding when the award letter or grant agreement is made, or by statute for a grant determination to a public body. The government's grants functional standard (GovS 015) expects competitions assessed against published criteria with the reasons for decisions documented. Scaling back is safe where the published rules reserve it. Where they do not, a funder that departs from its published scheme risks a judicial review argument of legitimate expectation, which needs a clear and unambiguous representation, and courts have found such expectations defeated in some grant schemes and not arising in others. *R (Knot Builders) v Construction Industry Training Board* [2024] EWHC 115 (Admin) raised the argument against a departure from a published grant scheme, and its outcome was not read here. So the scheme's own words decide whether scaling back is allowed, whether a floor applies, and what happens to an award that falls below it.

**How an instrument states it.**

| What | Instrument terms |
|---|---|
| the scheme rules | a rule imposed on every award of the scheme, the case the maintainer named in the ruling on B1, stated from the scheme's wording or configured directly, and bound into each award |
| approving and awarding | an `ins:Power` of the funder, its exercise the award, at which the fund is merged |
| scaling back | the merge rule of the fund, proportional, where the rules reserve it, and no scaling where they do not, so an oversubscribed fund refuses or the panel approves less |
| the floor | the matrix of A3, with the scheme rules choosing among withdrawing the award, paying the floor, or rescaling without it |
| paying in instalments | an `ins:Obligation` of the funder with `ins:due` and `ins:recurrence`, each instalment a draw on the award's own account, conditions of payment as its scope, and clawback a regime entered on breach |

**What it means for the ledger.** The scaling happens once, at the award, and the instalments draw on accounts already sized. A floor met inside a proportional split is A3's question again, and LG-Q17's if the answer is to withdraw the award and leave its share as a residual.

**Questions for a ruling.** Where scaling leaves an award below a floor, which of the three treatments does the scheme's wording need to say, and is any of them the default?

**Ruling.**

### Sources for section G

Read from search summaries, statute extracts and practitioners' notes, not full judgments or the full current text of every rule, so each point is to be checked before any wording relies on it.

- Insolvency (England and Wales) Rules 2016, rule 14.40, legislation.gov.uk/uksi/2016/1024/rule/14.40/made
- R3, creditor order of priority, r3.org.uk/about-r3-insolvency-restructuring/about-insolvency-and-restructuring/the-insolvency-framework/creditor-order-of-priority/
- Clifford Chance, the partial restoration of crown preference from 1 December 2020
- Companies Act 2006 section 578, legislation.gov.uk/ukpga/2006/46/section/578
- FCA Handbook, UKLR 9.4, handbook.fca.org.uk/handbook/UKLR/9/4.html
- Barclays, allocation policy for IPOs and new share issues, and Redmayne Bentley, allocation
- City AM on the Royal Mail allotment of 2013
- Government Functional Standard GovS 015, guidance for general grants, gov.uk
- *R (Knot Builders) v CITB* [2024] EWHC 115 (Admin), caselaw.nationalarchives.gov.uk/ewhc/admin/2024/115

