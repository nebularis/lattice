<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# `tools/proofs/ledger/`: the ledger laws

The laws of [ADR-A131](../../../docs/architecture/decisions/ADR-A131-ledger-layer.md) decisions 3, 4 and 6, proved in one Isabelle/HOL session, `Ledger`, with `quick_and_dirty = false`. Built for the ledger plan's LG-7, with its [Validation Pack](../../../docs/developer/validation/LG-7.md), widened by LG-8, with [its pack](../../../docs/developer/validation/LG-8.md), and proved again by LG-9 on the [target kernel](../../../docs/developer/sketches/ledger-target-kernel.md), with [its pack](../../../docs/developer/validation/LG-9.md). The session parents on the prelude, `session Ledger = LatticeBase +` ([../base/](../base/README.md)), whose heap holds the `HOL-Library` theories. `Kernel.thy` imports `Complex_Main` alone, and `HOL-Library.Multiset` is imported by `Draws.thy` and `Rounding.thy`. Nothing here names a domain.

| File | What it holds | Edited by hand? |
|---|---|---|
| `Kernel.thy` | the definitions, extracted from [`ontology/ledger/README.md`](../../../ontology/ledger/README.md) section 10 | never. Regenerate it with the command below |
| `Allocation.thy` | rules over amount vectors: the target kernel's examples, the proportional rule and the rule by rank lawful, a split of zero, two lawful rules that disagree, attribution as an apportionment, a threshold | yes |
| `Draws.thy` | the account tree: the path as a list and its code equation, examples of `settle`, `spread`, `pots` and `credit` evaluated, draws, availability, credits, purposes, a settlement at one position, an amount allocated across accounts | yes |
| `Rounding.thy` | whole minor units: floor division and what it leaves short, the units a declared order places, to the first in order and largest remainder under rationing, both lawful, each part within one unit of its exact share, the refinement to exact amounts across accounts | yes |
| `claims/*.json` | one claim record per law, in `../claim-schema.json`'s shape | written with the theorems |
| `Predicates.thy`, `Ranks.thy`, `Units.thy`, `Merge.thy`, `Pots.thy`, `Credits.thy`, `Readings.thy` | LG-20's laws, one theory per group of definitions, in the plan's order, each with its examples first | yes |

## What is proved

Each row is a theorem between `(* GATE:BEGIN <id> *)` and `(* GATE:END *)` markers, with its claim record. Amounts are over any ordered ring (`linordered_idom`) unless the row names a type.

| Claim | Theorem | Law |
|---|---|---|
| LA1 | `Allocation.proportional_lawful` | the proportional rule is lawful on every finite key set, over any ordered field |
| LA2 | `Allocation.by_rank_lawful` | by rank, with a rank injective on the keys and any rule for a tie, is lawful. It is priority |
| LA3 | `Allocation.lawful_split_of_zero` | any lawful rule splits zero into zero parts |
| LA4 | `Allocation.lawful_rules_differ` | negative instance: on 2 and 4 with 3 to split, the proportional rule and the rule by distinct ranks, both lawful, give the first key 1 and 2 |
| LC1 | `Draws.conservation_with_residual` | for an amount allocated across any sequence of accounts by any rule, every key's parts plus what is left equal what was asked |
| LC2 | `Draws.conservation_in_total` | the same summed over the keys, and each account falls by the total of the parts granted at the accounts that charge it |
| LC3 | `Draws.nothing_posted_beyond_availability` | with a rule that rations, and accounts charged that are finite, non-empty and within a set of accounts whose balances start non-negative, no balance goes below zero, what is left is non-negative, and every part is within the least balance the earlier steps left on the accounts it charges |
| LC4 | `Allocation.attribution_conserves` | parts of non-negative total attributed among parties by a rule that apportions, each by a non-negative basis of positive total, are attributed exactly, and no party is attributed a negative amount |
| LD1 | `Draws.draw_succeeds_whole_or_changes_nothing` | a draw debits the account and every ancestor, or changes nothing |
| LD2 | `Draws.availability_is_the_least_along_the_path` | availability is the least balance along the path, and a draw succeeds exactly when it is within it |
| LD3 | `Draws.credit_stops_at_the_ceiling` | a credit never takes a balance above its ceiling, and with every account accepting it, it undoes a draw along the same path |
| LD4 | `Draws.a_purpose_debits_the_counting_path_in_the_same_draw` | a draw naming a purpose debits the path of every account counting it, in the same operation that succeeds or fails whole |
| LN1 | `Allocation.residual_falls_as_the_drawn_amount_rises` | negative instance: under a threshold of 10 the residual is 10 when 10 is drawn and 0 when 11 is |
| LO1 | `Draws.settled_the_same_in_every_order_of_proposal` | two lists of proposals at one position with the same multiset settle to the same outcome and balances, under any policy |
| LR1 | `Rounding.floor_split_conserves` | floor division of a whole total leaves a shortfall from zero to one less than the number of parts |
| LR2 | `Rounding.ration_to_first_sums_exactly`, `Rounding.ration_to_first_the_same_in_every_order` | `ldg:ToFirstInOrder` under rationing, with an order injective on the keys, sums exactly to any amount from zero to what was asked, and is the same for every proposal list with the same multiset |
| LR3 | `Rounding.ration_largest_remainder_sums_exactly`, `Rounding.ration_largest_remainder_takes_the_largest`, `Rounding.ration_largest_remainder_the_same_in_every_order` | `ldg:LargestRemainder` under rationing, ties in an order injective on the keys, sums exactly, a key it reaches has a remainder at least that of any key it does not, and it is the same for every proposal list with the same multiset |
| LR4 | `Rounding.ration_lawful` | both rules under rationing are lawful over whole units for every non-negative request, with an order injective on the keys |
| LR5 | `Rounding.rounded_part_within_one_unit`, `Rounding.rounded_spread_takes_what_the_exact_takes` | each part is within one unit of its exact share, strictly so under largest remainder, and an amount allocated across accounts by largest remainder over whole units takes from every account exactly what the exact allocation by any lawful rule takes, conserving every key exactly |
| LX1 | `Draws.chain_is_the_path` | in a tree, the walk up from an account by at most as many steps as there are accounts lists its path exactly, with no repeat |

The pack's checks LG9-g and LG9-f are `mise run check:proofs -- ledger` and `mise run check:formal-freshness`, and have no claim record.

LG-20, with [its pack](../../../docs/developer/validation/LG-20.md), adds 36 claims. Instances kept on purpose end in `n`.

| Claim | Theorem | Law |
|---|---|---|
| LV1 | `Predicates.lawful_is_rationing_with_no_residual` | a lawful rule rations and leaves no residual |
| LS1 | `Predicates.the_rules_for_whole_units_apportion` | both rules for whole units apportion with an order injective on the keys |
| LS2 | `Predicates.a_key_of_no_weight` | rationed, a key of no weight is granted nothing, and apportioned it may take a unit |
| LV2 | `Predicates.whole_each_rations` | granting whole in a declared order over a list holding each key once rations |
| LVn | `Predicates.no_whole_or_nothing_rule_is_exact` | with 7 available and requests of 5 and 4, no rule granting whole or nothing is exact |
| LK | `Ranks.renaming_carries_the_result` | a bijection on the keys that carries the ranks, and a rule for a tie that commutes with it, carries the result |
| LK2 | `Ranks.distinct_ranks_are_priority` | with a rank injective on the keys, by rank is the priority formula and never reads the rule for a tie |
| LT1 | `Ranks.one_rank_is_the_tie_rule` | with one rank and a lawful rule for a tie, by rank is that rule |
| LT2 | `Ranks.by_rank_rations_where_the_tie_rule_does` | by rank rations where the rule for a tie does on every set of keys, and is lawful where it is |
| LT3 | `Ranks.cut_short_leaves_later_ranks_nothing` | a request granted less than it asked leaves every later rank nothing |
| LT4 | `Ranks.no_tie_no_tie_rule` | where no tie arises the result does not depend on the rule for a tie |
| LW0 | `Units.a_strict_total_order_places_exactly_n` | a strict total order places exactly n keys, n from 0 to their number |
| LW1 | `Units.no_order_rations` | largest remainder with no order declared rations |
| LW2 | `Units.equal_requests_equal_grants` | under it equal requests receive equal grants |
| LW3 | `Units.residual_below_the_number_of_keys` | its residual is from zero to less than the number of keys |
| LW5 | `Units.whole_groups_need_no_order` | where the units short reach whole groups of equal remainders, it leaves no residual and equals the rule with any declared order |
| LWn | `Units.a_declared_order_treats_equal_requests_unequally` | three requests of 5 sharing 10 are granted 4, 3 and 3 with an order declared |
| LW4 | `Units.no_order_renaming_carries_the_grants` | with no order, a renaming of the keys by any bijection carries the grants |
| LH1 | `Units.to_nearest_sums_exactly` | rounding half up or half to even, with a strict total preference to gain on the shares rounded down and one to lose on those rounded up, sums exactly |
| LH2 | `Units.to_nearest_within_one_unit` | each share rounded to the nearest is within one unit of its exact value |
| LHn | `Units.a_unit_to_the_first_among_all_keys_strays` | weights 3, 0, 11 and 11 sharing 62 round to 61, and the unit given to the first among all keys goes to the key of no weight |
| LM1 | `Merge.each_refusal_where_its_condition_holds` | each of the four reasons of a merge arises exactly where its condition holds, with no rule for a tie a merge refuses exactly where a tie arises, and a refusal changes no balance |
| LM3 | `Merge.no_residual_unless_declared` | a granted outcome has no residual unless the account declares one may be left |
| LM2 | `Merge.whole_units_settle_in_proportion` | at whole units, with one rank and largest remainder in a declared order, the grants are the lesser of what was asked and what was available, each within its request, the path is charged exactly that, no balance falls below zero, and each grant is within one unit of its exact share |
| LJ1 | `Merge.no_purpose_is_settle` | with no purpose and the one set of every proposer, settling purposes is `settle` |
| LJ4 | `Merge.mixed_or_crossing_refused` | a mixed position is refused exactly where declared and the purposes differ, a crossing one is refused, and no refusal changes a balance |
| LJ5 | `Merge.two_purposes_never_cross` | with at most two purposes among the requests no two sets cross |
| LJn | `Merge.a_facility_with_a_sublimit` | the facility of 100 with a sublimit of 30 grants 75 and 25 and leaves 5 on the sublimit |
| LC5 | `Pots.a_purpose_charges_every_account_counting_it` | an allocation over the reach of a purpose charges every account that counts it by the whole |
| LC6 | `Pots.whole_or_no_result` | an allocation that must be whole is the allocation or no result |
| LV3 | `Pots.rationing_allocation_accounts_for_what_was_asked` | with a rule that rations, parts and what is left are what was asked, and each account is charged what was granted at it |
| LP3 | `Pots.the_fund_falls_by_the_grants` | the fund and every account above it fall by the grants of its pots |
| LP2 | `Pots.pots_never_overdraw` | no account of the tree falls below zero, and no pot is paid more than its own amount |
| LP4 | `Pots.a_bound_at_the_fund_pays_no_later_pot` | where the fund or an account above it binds a pot, no later pot is paid |
| LPn | `Pots.the_unit_left_is_withheld_along_the_path` | a unit a pot leaves is taken by a later pot where nothing is carried, and where it is withheld from the fund alone and an account above the fund binds |
| LJ2 | `Pots.no_reached_account_below_zero` | settling purposes leaves no account a request reaches below zero |
| LJ3 | `Pots.narrowest_first_lists_agree` | any two narrowest-first lists of the same nested or disjoint sets give the same outcome |
| LB1 | `Credits.the_step_agrees_with_debit_and_credit` | each step of a run moves an account by what its posting records |
| LB2 | `Credits.recorded_balances_follow_step_by_step` | a list of balances is the run's exactly when each follows from the one before |
| LU1 | `Credits.the_sum_is_the_balance` | the sum of what a run posted is the balance it ends at |
| LU2 | `Credits.a_credit_depends_on_its_path` | what a credit applies and cuts depends on the balances on its path alone, and no cut is negative |
| LB1n | `Credits.the_ceiling_applied_once_overstates` | the sketch's one account: stepped, the balance is 70, and the ceiling applied once to the fold gives 100 |
| LU1n | `Credits.the_sum_with_no_cuts_overstates` | the sketch's cap, aggregate and two sections: the aggregate steps to 7, the sum with its cuts is 7, and with no cuts 9 |
| LU3 | `Credits.no_cut_where_ceilings_are_stated_and_credits_on_leaves` | where every ceiling is its stated amount and every credit is requested at a leaf, no posting of a run records a cut |
| LU3n | `Credits.a_leaf_that_refuses_its_credit_leaves_a_cut` | `credit` alone, at a leaf that does not accept the kind under a parent that does, leaves a cut of 5, and `run` refuses the credit (LG-Q29 (b)) |
| LE1 | `Readings.reading_a_from_a_recorded_balance` | reading A from a recorded balance, plus what was recorded after and effective by the day, is reading A from the start |
| LE2 | `Readings.reading_a_at_the_head` | at the head with every posting counted, reading A is the recorded balance |
| LE3 | `Readings.flows_from_recorded_totals` | the two totals of the flows split the same way |
| LE4 | `Readings.with_nothing_late_the_readings_agree` | where every posting is effective on the day it is recorded, reading B and reading A at the head are the recorded balance |
| LE5 | `Readings.reading_b_within_range` | under a tree, with stated amounts from zero to the ceiling and every draw posted non-negative, reading B is never below zero or above the ceiling |
| LEn | `Readings.a_debit_recorded_last_and_effective_second` | reading A is minus 10, reading B 50 or 100, and the recorded balance 20 |

Supporting lemmas with no claim of their own: the examples of each theory, proved by `code_simp` before any theorem, among them the target kernel's six, `Draws.example_settle`, `example_spread`, `example_pots` and `example_credit`, which evaluate through the path, and `Rounding.example_a_key_of_no_weight`, where apportioning gives a key of weight zero a unit and rationing does not. `Allocation.lawfulI`, the four axioms before LG-9 giving `lawful`, `Allocation.by_rank_injective`, by rank with an injective rank as the priority formula, `Draws.path_step`, the path unfolded one step and its code equation, `Draws.spread_sums`, `Draws.spread_rations` and `Draws.spread_step`, `Rounding.placed_count`, a strict total order placing exactly n keys, `Rounding.short_within_unmet`, the shortfall at most the requests not yet met, `Rounding.floor_units_total`, `Rounding.placed_remainder_positive` and `Rounding.spread_refines`.

## What is assumed

Every hypothesis is in the theorem's statement, and nothing is assumed outside them.

- **A key set is finite**, and an amount vector is non-negative and zero off its key set (`nonneg_on`).
- **A rule is lawful**, rationing with no residual, where a theorem asks it, or **rations** for LC3, or **apportions** for LC4.
- **A rank or an order is injective on the keys** for LA2, LR2, LR3, LR4 and LR5's strict bound, so the keys are never ordered by their names (TD-161).
- **Under rationing the amount is from zero to what was asked** for LR2 and LR3, and the requests are non-negative.
- **A tree is a finite set of accounts closed under the parent function**, with no cycle (`tree`), for LD2 and LX1. LD1, LD3 and LD4 hold of any parent function.
- **The accounts an allocation charges are finite and non-empty** for LC3 and LR5, and within a set whose balances start non-negative for LC3. A path in a tree is (`Draws.path_charged`).
- **A part attributed has a non-negative total** for LC4.

## What is not covered

- LG-20's laws not yet built: LW4, LH1, LH2, LM2, LJ2, LJ3, LP1, LP2, LP4, LPn, LB1n, LU1n, LU3, LE4 and LE5 (its pack says why).
- The composition law, the uniqueness of a solution and the least fixpoint over the information order, which are ADR-A130 decision 5's and the formal-methods plan's E4b.
- The runtime terms, postings and balance records as records with natural keys, which LG-2 writes against these theorems.
- Conversion between value spaces (LG-Q8), and the derivation of one account per key value (LG-Q7).
- Code export. `path` evaluates through its one-step unfolding, which ends where the parent function has no cycle, so `value` and `code_simp` reach `settle`, `spread`, `pots` and `credit`, and no `export_code` is run.
- Positions. The target kernel orders a merge by ranks and readings by effective day, and has no position type.
- Any insurance structure, which is applied content.

## Provenance

The amount vector, the rule type and its four axioms, the proportional and priority rules with their proofs, conservation with a residual in its pointwise and total forms, and attribution follow the domain-neutral core of an external Isabelle development of ours, read as background. That core was renamed to the ledger's terms and proved again in this session, and the external development is not part of this repository and is not cited as a proof of ours. Nothing specific to the domain it was written for was taken. The draws and the floor division generalise `spikes/isabelle-layers/Ledger.thy` from one flat map of balances to the account tree. The definitions are the [target kernel spike's](../../../spikes/ledger-target-kernel/README.md), moved into the README by LG-9.

## Building

```bash
mise run check:proofs -- ledger
mise run check:formal-freshness
```

After the README's `isabelle-spec` blocks change, regenerate `Kernel.thy` and then the claim digests, which cover every definition and record in the session:

```bash
mise exec -- python tools/literate_extract.py ontology/ledger/README.md --layer ledger --root . --proofs-root tools/proofs
```
