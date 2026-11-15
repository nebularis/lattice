<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The target ledger kernel

**Unit:** `ledger`, slice LG-21 ([plan](../plans/ledger.md), [status](../status/ledger.md)). **Status:** drafted 2026-11-15 for the maintainer's review, under LG-Q27 (b). Decisions waited for, in section 6. Nothing in `tools/proofs/ledger/` or in the ledger README's block is changed by it, and no law is proved.

## 1. What this is

The kernel as the decisions of 2026-11-09 to 2026-11-15 leave it, with each definition stated once. It replaces the plan of widening the present kernel part by part, in the order the questions were decided, which would have changed or doubled 12 of its 38 definitions over 17 parts.

The definitions are a theory, [`Target.thy`](../../../spikes/ledger-target-kernel/Target.thy), kept as a [spike](../../../spikes/ledger-target-kernel/README.md). Isabelle2025-2 type-checks it on the HOL heap and evaluates five examples on the definitions themselves. A model beside it transliterates the definitions and searches the laws of section 5 on generated cases. The definitions are stated there and not repeated here. This sketch says why each is as it is, what writing them down found, and what waits on the maintainer.

## 2. The principles, each a decision already made

| | Principle | From |
|---|---|---|
| 1 | no definition reads a key's own order. An order reaches a rule as a rank on each request, a lower rank served first, and equal ranks are a tie | TD-161, PRI-82, LG-Q18, scenario F1 |
| 2 | a rule may leave a residual. Being exact is a second property, and the four axioms of today's `lawful` are the two together | LG-Q17, MEC-109 |
| 3 | there are two kinds of split. Rationing bounds each part by its claim, apportionment does not, and they differ only in which keys may take an odd unit | LG-Q19, LG-Q15 |
| 4 | a merge returns the grants and a residual, or a refusal with its reason, never a refusal written as zero grants | LG-Q11 |
| 5 | ranks are tiers of one rule, and a rank is an account only where it holds an amount. What a rank cannot place reaches no lower rank | scenario G1, MEC-110 |
| 6 | an amount allocated across accounts charges the accounts that count its purpose, and is whole or changes nothing where the wording refuses a shortfall | LG-Q13, LG-Q12 |
| 7 | a credit is applied at the account it is posted to, each accepting ancestor takes the least of that and its room, and the posting keeps the amount offered, the amount applied and the cuts | LG-Q10, LG-Q23, MEC-106 |
| 8 | a reading by effective day is a derivation over the records, and none is the ledger's own | LG-Q26, MEC-107 |

One principle is new and is question K1 below. Every definition that only adds, subtracts and compares is stated once over any ordered ring, so it serves whole units and exact amounts alike, and only a rule names its number type.

## 3. Each definition, and what becomes of it

"Today" is `tools/proofs/ledger/Kernel.thy`. The laws named are those of [LG-7](../validation/LG-7.md) and [LG-8](../validation/LG-8.md), and the parts planned for LG-9 and LG-20.

| Today | In the target | Why | Laws it must keep | Laws it gains |
|---|---|---|---|---|
| `total`, `nothing`, `less`, `fits_in`, `nonneg_on`, `up`, `path`, `tree`, `reach`, `debit`, `draw_on`, `draw`, `requested`, `proposers`, `floor_part`, `remainder` | the same, over an ordered ring where they were over the rationals | principle of K1 | every law as stated, LD1, LD2 and LD4 among them | none |
| `lawful`, with two further predicates planned beside it | `rations`, `exact`, `residual`, and `lawful` defined as `rations` and `exact`. `apportions` for the second kind | principles 2 and 3 | the four axioms, as `lawful` | a `lawful` rule rations with no residual (LV1). `apportions` needs a positive total basis, which today's statement leaves out |
| `ahead`, `in_priority`, both by key order | `ahead` by rank, and `by_rank`, one rule for ranks with the tie rule as an argument. Priority is `by_rank` with distinct ranks and has no definition of its own | principles 1 and 5 | priority is `lawful` (LA2), and a settlement is the same in every order of the proposal list (LO1) | the result is unchanged by a renaming of keys that keeps the ranks. With one rank it is the tie rule. A request falls short only where every later rank is granted nothing (the planned LK, LK2 and LT) |
| `to_first`, `largest_remainder`, both by key order, with a no-order rule and rounding to the nearest planned beside them | `placed` and `units`, one rule for whole units, of which `to_first`, `largest_remainder` and `to_nearest` are instances. `first_in`, `larger_remainder`, `then_by` and `no_order` state a preference. `unmet`, `ration` and `apportion` say which keys may take a unit | principles 1 and 3, LG-Q16 | the floor split conserves (LR1), and each instance with a declared order sums exactly, stays within its claims under rationing, and is within a unit of the exact share (LR2 to LR5) | with no order declared, equal requests get equal grants and the residual is below the number of keys (the planned LW). A key of no weight takes a unit only under apportionment |
| `merge`, with a refusal, whole units and ranks each planned as a change to it | `policy`, `reason`, `outcome`, `tie_arises` and one `merge` | principle 4 | a merge that grants is the rule's split, and the result is the same for every proposal list with the same multiset (LO1) | a refusal grants nothing. A merge with no tie rule refuses exactly where a tie arises |
| `settle_at`, which lists its grants in key order | `settle`, which returns the outcome | principle 1 | the same in every order of the proposal list (LO1) | the path is debited by what was granted, no balance falls below zero, and a refused merge changes no balance |
| `spread` and `spread_int`, twins, charging a path | one `spread` over the accounts charged, `spread_whole`, and `least` | principle 6, K1 | conservation with what is left over, and nothing posted beyond availability (LC1 to LC3) | it charges what was granted and not what was shared, which differ once a rule leaves a residual. `spread_whole` is the whole allocation or no change |
| nothing | `pots` | principle 5 | | where no pot's amount binds, the grants are `by_rank`'s (the planned LP) |
| `credit`, which clamps every account against the amount offered | `credit` by kind, returning the amount applied, the cuts and the balances | principle 7 | a credit never lifts an account above its ceiling (LD3) | the cuts are never negative, and are a function of the balances and the credit (the planned LU2) |
| nothing | `book`, `request`, `posted`, `post`, `run`, `moved`, `summed` | principle 7 | | the sum less the cuts is the stepped balance, for every account and history (the planned LB and LU1) |
| `position`, `before` | `counted`, `reading_a`, `asked`, `replay`, `reading_b`, `flows` | principle 8 | | the planned LE1 to LE4 |
| `path`, which nothing can evaluate | `path` kept as the statement, and `chain`, the path as a list | the planned LX1 | | under `tree`, `chain` lists exactly `path` |
| `shares_ok`, `attributed` | not yet restated. They become an apportionment, as LG-9's LS planned | principle 3 | LC4 | |

The target has 69 definitions against 38 today, since it holds what the 17 parts would have added. None takes a key's order.

## 4. What writing it down found

1. **The rule for whole units with no order is not a new rule.** It is `largest_remainder` with no order declared for odd units. So the part planned as LW is a law about an instance and adds no definition.
2. **Seven rules are two.** Priority is `by_rank` with distinct ranks, and the rules for whole units are one `units` with a preference. Each named rule of the vocabulary is an instance, and a law proved of `units` or `by_rank` holds of each.
3. **Rounding to the nearest can fall short as well as over.** LG-Q16 speaks only of units rounded over and taken back. Shares of 7.44, 0, 27.28 and 27.28 round to 61 where 62 is shared. Giving the unit to the first in the declared order gave it to the key of no weight, a whole unit from its exact share. In the target a unit short goes only to a share rounded down, and the search then holds every share within a unit. Question K6.
4. **Reading B is stated two ways.** The [balances sketch](ledger-balances-under-post-once.md) §4.9 limits a debit that no longer fits to what is available, so its example reads 70, 0 and 50. The benchmark's reading B charges it in full and reads 70, minus 10 and 40. That difference is the whole of the impossible readings LG-19 counted for B. Question K2.
5. **A merge at one position knows no purpose.** `settle` charges the path of the account, as `settle_at` does today, while a single draw charges the reach of its purpose. Requests with different purposes at one position are not stated anywhere. The present kernel has the same gap. Question K3.
6. **`spread` charged the amount shared.** That equals what was granted only while every rule is exact. The target charges what was granted.
7. **A residual needs a declaration.** Scenario C1 holds that a unit left unpaid underpays an insurance limit, and LG-Q17 that a rule may leave one. So the policy carries whether a residual may be left, and where it may not a merge that would leave one is refused. Question K5.
8. **A pot's refusal.** Where one pot's merge refuses, the target refuses every pot at that position. Question K4.

## 5. What was tried

Run of 2026-11-15, the model's seeds fixed. The theory type-checks and its five examples evaluate, among them the two faults the [spike on ranks](../../../spikes/ledger-ranks-and-pots/README.md) found.

| Search | Cases | Compared with | Laws asserted on every case |
|---|---|---|---|
| whole units | 197,159 | a sort, and the rule the ranks spike tried | `to_first` and `largest_remainder` with a declared order are the sort, sum exactly and stay within the claims. With no order the grants stay in bounds, treat equal requests equally and leave less than the number of keys, which they did in 22,522 cases. An apportionment sums exactly for any amount, and a key of no weight took a unit in 14,146. Rounded to the nearest, the parts sum exactly and stay within a unit, a unit taken back in 32,226 cases and given in 22,213 |
| ranks, exact | 100,000 | the loop over tiers of the ranks spike | `by_rank` is the loop, within bounds, the whole returns the whole, no residual, distinct ranks are priority, and a merge with no tie rule refuses exactly where a tie arises, in 80,307 cases |
| ranks, whole units | 200,000 | the same loop | the same, with a residual in 22,133 |
| credits, sums and readings | 60,000 histories, 561,036 postings | the benchmark writer's loop | a credit's closed form is the loop. Every balance stays from zero to its ceiling. The sum less the cuts is the stepped balance after every posting, with a credit cut at an ancestor 21,510 times. Reading A at the head is the ledger's balance. With nothing late, reading B and reading A for each day are the balance. Reading B with a debit limited never leaves the range |

The last search also counted, without asserting, that reading A left the range at 14,079 readings, that reading B charged in full fell below zero at 8,568, and that reading B differed from the ledger at the head in 10,897 of the 41,418 histories with a late posting.

**What it does not show.** No law is proved. The cases are small, up to six requests, four ranks and seven accounts. `pots`, `spread`, `settle` and the refusals of `merge` are exercised by examples and by the ranks spike's search and have no search of their own here. The model is a second transliteration by hand, so a slip in both would go unseen, which the five examples evaluated in Isabelle narrow and do not remove.

## 6. Questions for the maintainer

| | Question | Options | Leaning |
|---|---|---|---|
| **K1** | Whether settlement is stated once for whole units and exact amounts | (a) once, over an ordered ring, as the target has it. (b) twice, over the rationals and the integers, as today | (a). `spread_int` and the planned merge over whole units leave the kernel, and each law is proved once. The cost is that the 19 claims are restated more generally, and how much proof that moves is not known until machine S tries. A law that needs division stays over a field |
| **K2** | What reading B does with a debit that no longer fits when the postings are settled again in effective order | (i) limits it to what is available, as the sketch's example does. (ii) charges it in full, as the benchmark does, so a reading can fall below zero. (iii) settles it by the account's own policy, refused where the account refuses and cut where it rations | (iii), offered as a hypothesis. A restatement asks what the ledger would have held, and the ledger would have applied the account's policy. (i) is its rationing case. (ii) shows a balance no account could hold, which the decision of 2026-11-13 on debits rules out for the ledger itself. Whichever is chosen, the reading reports what it refused or cut |
| **K3** | How requests with different purposes are merged at one position | (a) a position's requests share one purpose, and a mixed position is refused. (b) each request is bounded by the least over its own reach, which makes the merge an allocation under several limits and no longer one rule. (c) the purposes are settled one after another in a declared order | none yet. It needs a scenario of its own, and the target states (a)'s case only |
| **K4** | What a refusal at one pot does to the others at that position | (a) refuses them all. (b) the later pots are still settled | (a), as an allocation across accounts commits whole (STD-332) |
| **K5** | Whether leaving a residual is something an account declares, with a merge that would leave one refused where it does not | (a) declared, off by default. (b) always allowed | (a). It is what C1, F1 and LG-Q17 say together |
| **K6** | Where rounding to the nearest leaves the total short, which key takes the unit | (a) a share rounded down, by the declared order. (b) the wording must say, and silence is refused, as LG-Q16 holds for a unit over | (a) with (b)'s refusal where no order is declared, since it is the same question as a unit over |

## 7. After the review

1. The definitions move into the ledger README's block, from which `Kernel.thy` is extracted, in one reviewed change.
2. LG-9's and LG-20's 17 parts are reordered by definition, in eight groups: the predicates, ranks, whole units, the merge and settlement, accounts and the path as a list, allocation and pots, credits and the sum, and the readings.
3. Machine S's brief is rewritten on that order, and is handed over.

## 8. What this sketch asks for

- The maintainer's review of `Target.thy` against section 3.
- A decision on K1 to K6.
- Nothing is handed to machine S before both.
