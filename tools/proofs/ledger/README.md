<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# `tools/proofs/ledger/`: the ledger laws

The laws of [ADR-A131](../../../docs/architecture/decisions/ADR-A131-ledger-layer.md) decisions 3, 4 and 6, proved in one Isabelle/HOL session, `Ledger`, with `quick_and_dirty = false`. Built for the ledger plan's LG-7, with its [Validation Pack](../../../docs/developer/validation/LG-7.md), and widened by LG-8, with [its pack](../../../docs/developer/validation/LG-8.md). The session parents on the prelude, `session Ledger = LatticeBase +` ([../base/](../base/README.md)), whose heap holds the `HOL-Library` theories. `Kernel.thy` imports `Complex_Main` alone, and `HOL-Library.Multiset` is imported by `Draws.thy` and `Rounding.thy`. Nothing here names a domain.

| File | What it holds | Edited by hand? |
|---|---|---|
| `Kernel.thy` | the definitions, extracted from [`ontology/ledger/README.md`](../../../ontology/ledger/README.md) section 10 | never. Regenerate it with the command below |
| `Allocation.thy` | merge rules: the two lawful rules, a split of zero, two lawful rules that disagree, attribution, a threshold | yes |
| `Draws.thy` | the account tree: draws, availability, credits, purposes, one position, an amount drawn across several accounts | yes |
| `Rounding.thy` | whole minor units: floor division, the residual, its allocation to the first in order and to the largest remainders, both rules lawful over whole units, the refinement to exact amounts | yes |
| `claims/*.json` | one claim record per law, in `../claim-schema.json`'s shape | written with the theorems |

## What is proved

Each row is a theorem between `(* GATE:BEGIN <id> *)` and `(* GATE:END *)` markers, with its claim record.

| Claim | Theorem | Law |
|---|---|---|
| LA1 | `Allocation.proportional_lawful` | the proportional rule satisfies the four axioms on every finite key set |
| LA2 | `Allocation.in_priority_lawful` | the priority rule, filling keys in their order, satisfies the four axioms |
| LA3 | `Allocation.lawful_split_of_zero` | any lawful rule splits zero into zero parts, derived from the axioms |
| LA4 | `Allocation.lawful_rules_differ` | negative instance: on 2 and 4 with 3 to split, the two lawful rules give the first key 1 and 2 |
| LC1 | `Draws.conservation_with_residual` | for an amount drawn across any sequence of accounts by any lawful rule, every key's postings plus its residual equal what was drawn |
| LC2 | `Draws.conservation_in_total` | the same summed over the keys, and each account's fall in balance is the total of the postings whose path reaches it |
| LC3 | `Draws.nothing_posted_beyond_availability` | no balance in the tree goes below zero, the residual is non-negative, and at every step the posting is within its account's availability in the balances the earlier steps left |
| LC4 | `Allocation.attribution_conserves` | a share matrix whose rows sum to one attributes exactly the postings across the parties, and no party is attributed a negative amount |
| LD1 | `Draws.draw_succeeds_whole_or_changes_nothing` | a draw debits the account and every ancestor, or changes nothing |
| LD2 | `Draws.availability_is_the_least_along_the_path` | availability is the least balance along the path, and a draw succeeds exactly when it is within it |
| LD3 | `Draws.credit_stops_at_the_ceiling` | a credit never takes a balance above its ceiling, and it undoes a draw along the same path |
| LD4 | `Draws.a_purpose_debits_the_counting_path_in_the_same_draw` | a draw naming a purpose debits the path of every account counting it, in the same operation that succeeds or fails whole |
| LO1 | `Draws.settled_the_same_in_every_order_of_proposal` | two lists of proposals at one position with the same multiset give the same postings in key order and the same balances |
| LR1 | `Rounding.floor_split_conserves` | floor division of a whole total leaves a residual from zero to one less than the number of parts |
| LR2 | `Rounding.to_first_sums_exactly`, `Rounding.to_first_is_the_same_in_every_order` | the residual given one unit at a time to the first keys in order makes the parts sum exactly to the total, whatever the order the weights arrived in |
| LR3 | `Rounding.largest_remainder_sums_exactly`, `Rounding.largest_remainder_takes_the_largest`, `Rounding.largest_remainder_is_the_same_in_every_order` | `ldg:LargestRemainder`: the residual given one unit at a time to the keys with the largest remainders, ties in key order, makes the parts sum exactly to the total, a key it reaches has a remainder at least that of any key it does not, and it is a function of the weights alone, whatever the order they arrived in |
| LR4 | `Rounding.largest_remainder_lawful`, `Rounding.to_first_lawful_on_positive_weights` | both rules satisfy the four axioms over whole units, `int_lawful`, for a total from zero to the sum of the weights: largest remainder for every non-negative weight, to the first in order only where every weight is positive |
| LR5 | `Rounding.rounded_part_within_one_unit`, `Rounding.rounded_spread_takes_what_the_exact_takes` | each rounded part is within one unit of its exact share, strictly so under largest remainder, and an amount drawn across several accounts in turn, split over whole units by largest remainder (`spread_int`), takes from every account exactly what the exact split by any lawful rule takes, conserving every key exactly |
| LN1 | `Allocation.residual_falls_as_the_drawn_amount_rises` | negative instance: under a threshold of 10 the residual is 10 when 10 is drawn and 0 when 11 is |

The pack's LG1 and LG2 are checks rather than theorems, so they have no claim record. LG1 is `mise run check:proofs -- ledger`, and LG2 is `mise run check:formal-freshness`.

Supporting lemmas with no claim of their own: the examples of `Allocation.thy` and `Rounding.thy`, proved before any theorem, among them `Rounding.example_largest_remainder` and `Rounding.example_to_first_differs`, where the two rules give one arrangement different parts, and `Rounding.to_first_can_exceed_a_zero_weight`, the instance that puts LR4's positive-weight hypothesis on to the first in order. `Draws.merge_bounded`, which bounds a merge's grants by the availability it was given and each grant by its request, `Draws.spread_step`, which gives the posting at each step, `Rounding.largest_remainder_reaches_a_positive_remainder`, `Rounding.spread_int_refines`, `Draws.before_is_a_strict_total_order` for positions, and `Rounding.floor_part_refines`, which puts each floor part within one minor unit below the exact rational share.

## What is assumed

Every hypothesis is in the theorem's statement, and nothing is assumed outside them.

- **A key set is finite**, and an amount vector is non-negative and zero off its key set (`nonneg_on`).
- **A rule is lawful**, satisfying the four axioms of `lawful`. Monotonicity is not one of them, and no theorem here needed it.
- **A tree is a finite set of accounts closed under the parent function**, with no cycle (`tree`). LD1, LD3 and LD4 hold of any parent function, a tree or not.
- **Proposals at one position are a list without repeats** for LR2's order independence, which is what a second order of the same proposals is. LO1 and LR3 need only the same multiset.
- **Balances start non-negative** for LC3.
- **Weights are non-negative**, and for to the first in order **positive**, for LR4, since to the first in order can give a residual unit to a key of weight zero.
- **Amounts are exact rationals**, and rounding is over integers. LR5 joins the two for each part and for an amount drawn across several accounts, where the balances are whole minor units.

## What is not covered

- The composition law, the uniqueness of a solution and the least fixpoint over the information order, which are ADR-A130 decision 5's and the formal-methods plan's E4b.
- The runtime terms, postings and balance records as records with natural keys, which LG-2 writes against these theorems.
- Conversion between value spaces (LG-Q8), and the derivation of one account per key value (LG-Q7).
- Largest-remainder allocation within a merge at one position. `merge` takes a rule over exact amounts, and `ldg:LargestRemainder` is proved as a rule over whole units and inside `spread_int`.
- How a merge refuses (LG-Q11), so LM1, a refused merge grants nothing and changes nothing, is not stated.
- Code export of `spread_int` and `draw`. `path` is a set defined by a transitive closure and is not executable, so `spread_int` has no `value` example.
- Draws at different positions, beyond positions being a strict total order.
- Any insurance structure, which is applied content.

## Provenance

The amount vector, the rule type and its four axioms, the proportional and priority rules with their proofs, conservation with a residual in its pointwise and total forms, and the share matrix of attribution follow the domain-neutral core of an external Isabelle development of ours, read as background. That core was renamed to the ledger's terms and proved again in this session, and the external development is not part of this repository and is not cited as a proof of ours. Nothing specific to the domain it was written for was taken. The draws, the settlement in key order and the floor division with its bounded residual generalise `spikes/isabelle-layers/Ledger.thy` from one flat map of balances to the account tree.

## Building

```bash
mise run check:proofs -- ledger
mise run check:formal-freshness
```

After the README's `isabelle-spec` block changes, regenerate `Kernel.thy` and then the claim digests, which cover every definition in the session:

```bash
mise exec -- python tools/literate_extract.py ontology/ledger/README.md --layer ledger --root . --proofs-root tools/proofs
```
