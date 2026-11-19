<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MSA-I2: what every guard and effect reads, in Behaviour, Ledger and Eligibility

**Unit:** [`multi-store-architecture`](../../status/multi-store-architecture.md), investigation MSA-I2 of the [sketch](../../sketches/multi-store-architecture.md) §6
**Written:** 2026-11-18, on paper, against the specifications and examples of `ontology/behaviour`, `ontology/ledger` and `ontology/eligibility` on `main` at the squash of 2026-11-17, with the ledger's merge policy. **Reworked** the same day on the ledger's unit as the maintainer decided it: the owner's ledger, in the ledger plan's LG-Q44 and LG-Q37 and in ADR-A131's addendum proposed 2026-11-18, all on `docs/placement-vehicles-structure`, which this branch has not merged
**Placement:** T0, public. Substrate configuration, nothing domain-specific

## 1. The question

For every guard and effect in the three modules' examples, what it reads, in which aggregate, and whether what it reads is pinned or mutable. The falsifier is that a common guard reads mutable state that a natural placement would put in another store. The answer bears on MSA-Q1 (is the aggregate the unit of placement), MSA-Q4 (MS-Q7 narrowed to mutable copies) and the sketch's §4.1 and §4.3.

A natural placement, as the sketch's §4.3 has it, keeps versioned meaning in RDF (instruments, wordings, vocabularies, eligibility conditions, account definitions, merge policies) and may hold mutable runtime records elsewhere (Behaviour's occupancies and records, the ledger's postings, balance records, merge records and passes). Pinned means a version or a temporally scoped, evidenced fact that cannot change. Mutable means current state.

Each read that crosses aggregates is marked in one of three ways, as the maintainer's brief of 2026-11-18 asks.

- **Inside a ledger.** A read of another account of the same owner's ledger, which the ledger's one writer serialises with the write. It crosses no unit.
- **Pinned by revision.** A read of a ledger's balance from outside the ledger, naming the ledger's revision and recording it in the read set. A balance as of a revision never changes. No example carries the ledger node or its revision until the ledger's slice LG-27 lands, so each such read is marked "pinned by revision once LG-27 lands".
- **Changeable across a unit.** A read of current state outside the reader's unit that a revision does not pin.

## 2. What was read

Forty example files and four test files.

| Module | Examples (tests) | Guard kinds | Effect kinds | Files with a runtime record |
|---|---|---|---|---|
| Behaviour | 12 (2) | 9, of which 6 are declared guards in 3 files and the rest are triggers that read like guards | 9 | 11 |
| Ledger | 15 | 10, mostly shapes and the merge rule, since the ledger has no guard class | 9, 8 shown | 6 |
| Eligibility | 13 (2) | 9 condition kinds, 8 used | 2 | 3 (+2) |

The full inventory, with a citation for each row, was working material and is not committed. This note gives what it found.

## 3. Reads that cross aggregates and read mutable state

The first five columns are the census as first written. The last marks each read under the owner's ledger.

| ID | Where | What reads what | Natural placement | Strength | Under the owner's ledger |
|---|---|---|---|---|---|
| R1 | Behaviour, `ordered-draws.ttl` | Three transition guards of a licence's regime read the seat bundle's balance, an account, through `bhv:requiresEligibility`. The alert guard reads the bundle as the seat draw in the same pass left it, and the state change reads it after both draws | the regime's state and the accounts are separate aggregates of one owner (ADR-A106 decision 5, ADR-A131 decision 5), and the sketch lets Behaviour's runtime be held in SQL or memory while the ledger stays in RDF | firm on the text, in one example | **pinned by revision once LG-27 lands.** The seat draw's guard reads the revision the pass starts from, and the alert's and the state change's read the revision the seat draw moved the ledger to. Covered under C1 and C2 of §5 |
| R2 | the same pass | One pass changes two accounts and a regime state, each step reading what the last wrote | as R1. This is the case the sketch's §4.1 names as its falsifier, one atomic change to two families a deployment might place apart | firm on the text, in one example | the two draws are **inside a ledger**, the seat bundle's and the alert quota's, if both are the licensee's accounts, which the example's Behaviour allowance terms do not state. The state change is a write outside the ledger after them, covered under C3 of §5 |
| R3 | Ledger, `research-grant.ttl`, `insurance-aggregate.ttl` | A draw's availability is the least balance along its account's path, a fold over each ancestor's subtree | cross-aggregate only if an account is the aggregate, see §5 | depends on §5 | **inside a ledger.** `ldg:partOf` names "the parent definition's instance for the same owner" (the ledger README), so a path never leaves one owner's ledger |
| R4 | Ledger, `insurance-aggregate.ttl` | A pass writes two accounts, a purpose-counting account outside the drawn account's tree, and a credit with a debit at the capacity pool | as R3 | depends on §5 | **inside a ledger.** The programme owns every account of the example, the purpose-counting account included |
| R5 | Eligibility, the bound examples | An evidence binding reads the applied ontology's data, a protocol's prohibited list in another aggregate from the participant, a set of consents still arriving | the applied data's placement is not stated. A closure makes the read as of the deciding record's time | open | no ledger read. Unchanged, open |
| R6 | Behaviour, derived triggers | "No premium remains due on any policy bound under the authority" reads a balance on other aggregates | what a derived trigger reads is the layer above's to declare, and no example declares it | open | **changeable across a unit, in part.** Each policy's premium due, if a ledger holds it, is pinned by revision. Which policies are bound under the authority is not a ledger fact, and no revision pins it. The candidate of §5 |
| R7 | Behaviour, occasions | An occasion's state is derived from act records `forCase` and breach records `ofOccasion`, which may sit in two aggregates | not stated | open | no ledger read. Unchanged, open |
| R8 | Behaviour, breach by silence | A breach relies on the completeness of an external register at the window's close | an external source with no watermark | open | no ledger read. Unchanged, open |

## 4. Reads that cross aggregates and read a pinned version

Nine. A Behaviour guard reads an admission profile's version, an Eligibility condition reads the scheme its contract resolves to at the resolution time, a ledger account reads its definition and the merge policy that definition names, an account reads its owner's kind, an occasion reads its parties' role occupancy versions, a Behaviour record reads the layer above's act, a decision reads its operational profile and closure, a posting reads a dated conversion rate, and an occupancy names its subject's persistent identity. Each may be copied to another store and stay on the correctness path, as the sketch's MS-Q7 narrowed allows. The merge policy is a version the definition names (ADR-A131's addendum), and no example shows the version node, so the pin rests on the text.

Two of them are pinned only in part. A concept scheme's membership resolved at a time is pinned, and its governance state, which every example asserts as active, is mutable, though no Eligibility law reads it. A closure makes evidence pinned as of its cut, with no source watermark to gate on.

## 5. The ledger's unit, and what a read by revision does not cover

**The question this census raised, and its answer.** ADR-A131 decision 5 made an account and its postings an aggregate, and its third addendum of 2026-11-16 serialised the owner's ledger. This note proposed the owner's ledger. The maintainer decided it on 2026-11-18. An account still owns its postings, a period's unit is still the partition, and the owner's ledger is what a write must see unchanged, what one writer serialises, and what a deployment places in one store. A ledger is a node holding the revision, and each pass records the revision it moved the ledger to. The rule this note proposed, placing an identity's Behaviour state with its ledger, was not taken, since a guard outside the ledger can read a balance as of a revision, which never changes.

**Firm reads that a read by revision does not cover.** None. R3 and R4 are inside a ledger. R1's three guards read the seat bundle from outside it, and each is pinned by revision once LG-27 lands. The decision rests on three conditions the census finds in `ordered-draws.ttl`, none of which the texts state yet.

| ID | Condition | Why the example needs it |
|---|---|---|
| C1 | The ledger's writer returns, with each posting, the revision it moved the ledger to, and a pass's later guard names that revision, never the latest | the alert's guard reads "the bundle as the first draw left it". A credit to the bundle posted by another pass between the seat draw and the guard moves the latest revision, and a guard reading it sees a balance the seat draw did not leave |
| C2 | A guard outside the ledger that states the ledger's own refusal is decided again by the writer, and the transition takes the writer's refusal as its guard failing | the seat draw's guard, "while a seat remains", is the bundle's refusal at zero. Read at the revision the pass starts from, it can hold while the writer, at a later revision, refuses the draw. The transition must then not be recorded as fired |
| C3 | A pass's postings are answered from receipts keyed on the pass, its stimulus and its transition, with the revision each moved the ledger to, and a replay of the pass reads by those revisions | the state change of pass 3 is a Behaviour record written after the postings, so a crash between them leaves the postings and no record. The brief's reason that the posting is the fact and the occasion follows covers an occasion's derived state. The licence's occupancy here is a record the pass writes, and a replay completes it only under this condition. A replay that read the latest revision would read its own seat draw: the bundle at 0, so the seat draw's guard fails, and the replay records no seat draw while its posting stands, then the alert and the state change as before |

C1 and C3 are what MSA-I6's model X1 calls a torn read and a torn crash, met here without a second store, since the pass's own postings and its Behaviour records are already two units.

**One candidate, on a comment.** R6, `ontology/behaviour/examples/run-off.ttl`, the derived trigger `ex:on-premium-collected`: "No premium remains due on any policy bound under the authority." Each policy's premium due, if a ledger holds it, is pinned by that ledger's revision. Which policies are bound under the authority is not a ledger fact, and no revision pins it, so a read by revision covers the amounts and not the set they are read over. In run-off the authority binds no new policy, which closes the set in this example. In general the set needs a version of its own, the authority's, named in the read set beside each ledger's revision. The example states the trigger as a comment and declares neither the accounts nor their owner, so it is a candidate and not a finding.

## 6. Verdict

As first written, before the unit was decided, the census read the falsifier as firing on the text of one example, `ordered-draws.ttl`, and proposed a placement rule. Under the owner's ledger it does not fire. No common guard reads changeable state that a natural placement would put in another store. The ledger's own reads across accounts are inside one ledger, and the one firm read from outside a ledger, R1, is of a balance pinned by revision once LG-27 lands, under C1 to C3. Three things qualify the example still. It uses Behaviour's deprecated allowance terms, its guards' admission profiles are comments, and Behaviour does not yet import Ledger. Once it does, R1 is the ordinary form of a guard on an amount, so C1 to C3 are what every such guard needs.

What follows for the leanings.

- **§4.1, an aggregate never spans stores.** It survives with no placement rule. A persistent identity's Behaviour state and the ledger it guards on may be placed apart, and placing them together is a deployment's choice. What the sketch needs to state is C1 to C3: the revision returned with each posting and named by the guard, the writer's refusal read as the guard failing, and a pass completed by a replay from its receipts.
- **§4.3, evaluation in a pure core.** A pass that reads what it wrote needs the core to carry forward between steps its own writes and the revisions the writer returned for them. It needs no store read between steps.
- **§4.4 and MSA-Q4.** Every cross-aggregate read in Eligibility and in the ledger's configuration is of a pinned version, or of evidence pinned as of a closure's cut. A read of a balance by revision joins them. The narrowed MS-Q7 holds for them.
- **The watermark row of §4.2.** No source states a watermark. An Eligibility decision over bound evidence can take only the best-known row today, and records no read set (§7).

## 7. Gaps found on the way

- **A bound evaluation writes no record.** A decision needs at least one question (law L7), and an evaluation from evidence bindings has none, so the seven bound examples write no decision and their read set has nowhere to go.
- **The ledger's conversion terms outlive their removal.** ADR-A131 removes the conversion method and the amount as drawn, and the README, the runtime shapes and `revolving-facility.ttl` still carry them.
- **What a derived trigger reads is undeclared** in every example that uses one.
- **Two terms have no example**, `bhv:EffectApplication` and `elg:subjectRoleOccupancy`, so their reads cannot be counted.
- **`ordered-draws.ttl` names no owner for its allowances**, so that its two draws are inside one ledger is read from the regime's subject, the licence, and not from the text.
- **No example names a ledger node or a revision**, which LG-27 adds, so every read marked pinned by revision rests on the decision's text until then.
