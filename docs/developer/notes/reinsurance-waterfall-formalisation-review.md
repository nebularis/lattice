<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Review: three guides on reinsurance structures and the formalisation of the inurement waterfall

**Read:** 2026-10-27, against the ledger design at ADR-A131 and its addendum of that date.
**Material:** three documents supplied by the maintainer. A guide to quota shares, a guide to reinsurance treaty structures with a deep section on inuring order, and a formal-methods document proposing an Isabelle/HOL development of the waterfall with Rocq, SMT and Alloy alongside it. All three read in full.
**Why:** a sanity check, asked as "does the inuring order or anything else in the waterfall break our design", not as a source of requirements.

The short answer is that nothing breaks, one part of the material independently reaches a separation the ledger already has, and the reading exposed three holes in our own design that are now logged. The formalisation itself carries less weight than it first appears to, and that is the first thing to say.

## 1. How much weight the formalisation can bear

**It is not machine-checked.** Its own status section says so: "This is a **working skeleton, not a checked development.** I have not run it through Isabelle." The listing holds 17 `sorry` placeholders, and the headline results depend on them. `loop_gain_criterion` carries an untagged inline `sorry`. `loop_gain_insufficient`, the result that corrects the earlier criterion, depends on unproved cycle enumeration. Roughly 900 lines are outstanding by the document's own count, concentrated in three hard obligations.

Three gaps matter to us specifically.

- **Conservation of total is not proved anywhere in the theory listing.** The word does not appear in it. The earlier prose states `conservation` and `conservation_pointwise` as theorems, but with `⟨proof⟩` sketches, and the actual theory development is a narrower one about loop gain that does not include them. The result our own design leans on hardest is the one with the least backing in the material.
- **Non-negativity of a recovery is assumed, not derived.** It is a locale axiom, `f_nneg`, discharged only for the concrete contract forms at the end.
- **`single_cycle_sccs`, the side condition that rescues the loop-gain test, is weaker in the code than in the prose.** The code requires a cycle covering the component. It does not exclude a second chord cycle, which is exactly the configuration the document's own counterexample needs. The Alloy predicate beside it, `lone c: Cycle`, is the stronger reading.

Also noted: the listing claims base HOL only but appears to use `is_interval` from HOL-Analysis, `pw_linear_xol` lacks a `0 ≤ l` hypothesis and looks false for a negative limit, and `enumeration_restricted` bounds a cardinality with no finiteness conjunct, which in Isabelle makes the bound vacuous for an infinite solution set.

**What is sound is the mathematics, and the load-bearing arithmetic checks by hand.** The three-contract counterexample resolves as claimed. Per-risk XOL 40 xs 20 and cat XOL 40 xs 20 both inuring with a 90% quota share, each in turn net of it, at a gross of 100:

| Regime | Per-risk | Quota share | Cat | Total | Net | Validity |
|---|---|---|---|---|---|---|
| A, layers exhausted | 40 | 18 | 40 | 98 | 2 | needs the fold at or above 60, holds |
| B, within layer | 12.5 | 67.5 | 12.5 | 92.5 | 7.5 | needs the cession between 40 and 80, holds |
| C, below attachment | 0 | 90 | 0 | 90 | 10 | needs the fold at or below 20, holds |

All three satisfy their own conditions, and the gain matrix has spectral radius the square root of 1.8, about 1.342, against elementary loop gains of 0.9 and 0.9. So the correction stands: **loop gain below one on every cycle does not give uniqueness**, and the side condition on component structure is doing real work.

**Use these as a design input, not as a verified result.** Where a figure or a theorem from them is quoted in our own documents, it needs attributing as an unchecked development rather than as proof.

## 2. The separation the material reaches on its own

Its §3.6 states, independently of us: "Common account is **not** a waterfall position. It is a crediting rule. Model it as a second, independent map from recovery vectors to party accounts, and prove conservation at both levels."

That is our architecture. The ordered fold computes recoveries. The ledger attributes them to parties. Two conservation obligations, one at each level. The material's own worked cases make the point structurally: where a catastrophe cover inures to a proportional reinsurer's benefit, and where the same cover is bought for the joint account, **the waterfall is identical and only the attribution differs**. That is why "the inurement was never priced" is expressible at all, and it is expressible precisely because the two levels are separate.

**So the waterfall is not Ledger's job**, and the maintainer has agreed it is not. Ledger is the attribution layer. Three consequences.

- The ordered fold belongs above Ledger, in an applied module, producing postings. ADR-A131 decision 9, which says what Ledger does not hold, should say so.
- Our account tree is containment, with ancestors derived by closure over a finite tree. A priority order is a linear order over contracts for one draw. These are different structures, and making `ldg:partOf` carry inurement order would be a category error.
- The material supports the division from the other side. Its own limits table sends non-indemnity covers, which sit outside the waterfall because they do not reduce the indemnified loss, to be "model[led] as ledger entries, not contracts". The ledger is where things outside the waterfall belong.

## 3. What the reading validated

**The two orderings.** The material lists indexation and stability clauses among the things outside its theory: an attachment that moves at settlement, years after the loss, changing the loss presented upward, retrospectively. That is exactly the case ADR-A131's 2026-10-27 addendum answers with an effective position and a recorded position, and the consequence the addendum states, that a reading is reproducible only when paired with the recorded position at which it was taken, is the correct treatment of it. The addendum was written before this material was read, so this is confirmation rather than influence.

**Non-monotonicity does not hurt us.** The material shows net loss is not a monotone transform of gross, because a franchise deductible pays from the ground up once pierced and a corridor returns a band to the cedent. Its warning is that stochastic-order arguments and "stress the gross by twenty percent" exercises become invalid. A running balance along the recorded ordering records what happened rather than assuming a direction, so the ledger is indifferent. What the result does bear on is any future capital or projection work above the ledger, which should not assume monotonicity without the restricted condition.

**Indeterminacy does not hurt us either, and the substrate already has the right shape.** Where the inurement digraph is cyclic, recoveries may have one solution, three, or a continuum. The material's engineering rule is blunt and we should adopt it: **refuse, never iterate.** An engine that iterates to a tolerance can return a vector satisfying no contract in the programme, and the document demonstrates it: iteration from zero enters a two-cycle whose elements are fixed points of the squared operator and are not solutions. Our substrate already decides Permitted, Denied or Undetermined rather than forcing a verdict, so refusal has a home. Worth stating explicitly that **the ledger deliberately cannot represent an indeterminate amount**, so an applied layer refuses rather than posting a guess.

**Aggregate state across time.** The material holds everything per occurrence with aggregate state frozen, and warns that multiplicity compounds multiplicatively across events, so three events each with three solutions give up to twenty-seven consistent annual paths. Our checkpoints at closings are the mechanism that carries aggregate state, and the match is good. The warning only bites under indeterminacy, which refusal upstream prevents.

## 4. What the reading broke

Three holes in our design, now logged.

**PDD-14, the one to read first.** The two orderings make "recorded after it takes effect" ordinary rather than exceptional, so a posting whose effective position falls inside a period that has already closed is an expected case. That period's book is sealed, registered for immutable identity, and its checkpoint is derived from the close position. Writing into the sealed book falsifies the registered hash. Writing into the current book puts the posting at an effective position that book's period does not contain. Neither ledger benchmark generates one, because both streams are append-only, so it is unmeasured as well as unmodelled. The addendum of 2026-10-27 made this hole larger rather than smaller.

**TD-95, the cap-gap.** `ldg:AccountDefinition` carries a ceiling. The material proves that where a cap binds, the amount left to the drawer is the gross less the cap rather than the gross scaled by the complement of the cession, with an explicit side condition saying when to worry. In ledger terms the postings do not sum to the amount drawn and a residual reverts to the drawer, so a conservation shape written as a plain equality over the postings would refuse a correct ledger. LG-4 owns conservation and is now briefed with it.

**TD-96, rounding.** Exact conservation under a proportional split requires the rounding residual to be allocated by a stated deterministic rule, not left to the rounding mode. Three equal shares of a unit-granular amount do not sum back under half-even. We exercise half-even in one example and refuse an unrounded split in another, so both halves of the question are present, and nothing asserts that the postings sum to the draw.

## 5. Things worth taking, beyond the sanity check

- **The inuring order is a good working example for the ledger**, and the maintainer has asked for it. It exercises ordered application producing attributions, which is the thing the design does well, and it has to be stated domain-neutrally: an ordered sequence of accounts each seeing the residual of the previous, with the attribution of each recovery a separate map. The arithmetic of the three cases is small enough to be a worked example and sharp enough to show why the order matters.
- **The loss-granularity rule.** The material's single most common production error is carrying scalars where the finest unit of loss in the programme is finer, which loses the ability to compute a per-unit cover above a per-aggregate one. Our postings are per account and an allocation across accounts is LG-4's business, so we are not exposed today, but the rule is the right shape for LG-4's brief.
- **Allocation as a parameter rather than a hard-coded rule.** Where the contracts are silent, the material makes the allocation rule an explicit parameter with axioms and proves the theory for any rule satisfying them, then shows the answers differ. Our merge rules are already data, which is the same move, and the axioms are a good checklist for the conservation shape: exactness, boundedness by the amount, non-negativity, monotonicity in the amount allocated, and zero at zero.
- **"Find numerically, verify exactly."** The material's division of labour, where a solver proposes and the kernel disposes so the solver stays out of the trusted base, is the right pattern for our own formal work and matches what the formal-methods tracks already do.

## 6. What this note does not do

It takes no decision. It does not propose a reinsurance module, and nothing here is a requirement on the ledger. The insurance-specific content of the source material is handled as the maintainer directs, and the points carried into our own documents from it are the domain-neutral ones: ordered application, attribution as a separate map, conservation at both levels, refusal rather than iteration, and the allocation axioms.
