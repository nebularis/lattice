<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MSA-I2: what every guard and effect reads, in Behaviour, Ledger and Eligibility

**Unit:** [`multi-store-architecture`](../../status/multi-store-architecture.md), investigation MSA-I2 of the [sketch](../../sketches/multi-store-architecture.md) §6
**Written:** 2026-11-18, on paper, against the specifications and examples of `ontology/behaviour`, `ontology/ledger` and `ontology/eligibility` on `main` at the squash of 2026-11-17, with the ledger's merge policy
**Placement:** T0, public. Substrate configuration, nothing domain-specific

## 1. The question

For every guard and effect in the three modules' examples, what it reads, in which aggregate, and whether what it reads is pinned or mutable. The falsifier is that a common guard reads mutable state that a natural placement would put in another store. The answer bears on MSA-Q1 (is the aggregate the unit of placement), MSA-Q4 (MS-Q7 narrowed to mutable copies) and the sketch's §4.1 and §4.3.

A natural placement, as the sketch's §4.3 has it, keeps versioned meaning in RDF (instruments, wordings, vocabularies, eligibility conditions, account definitions, merge policies) and may hold mutable runtime records elsewhere (Behaviour's occupancies and records, the ledger's postings, balance records, merge records and passes). Pinned means a version or a temporally scoped, evidenced fact that cannot change. Mutable means current state.

## 2. What was read

Forty example files and four test files.

| Module | Examples (tests) | Guard kinds | Effect kinds | Files with a runtime record |
|---|---|---|---|---|
| Behaviour | 12 (2) | 9, of which 6 are declared guards in 3 files and the rest are triggers that read like guards | 9 | 11 |
| Ledger | 15 | 10, mostly shapes and the merge rule, since the ledger has no guard class | 9, 8 shown | 6 |
| Eligibility | 13 (2) | 9 condition kinds, 8 used | 2 | 3 (+2) |

The full inventory, with a citation for each row, was working material and is not committed. This note gives what it found.

## 3. Reads that cross aggregates and read mutable state

| ID | Where | What reads what | Natural placement | Strength |
|---|---|---|---|---|
| R1 | Behaviour, `ordered-draws.ttl` | Three transition guards of a licence's regime read the seat bundle's balance, an account, through `bhv:requiresEligibility`. The alert guard reads the bundle as the seat draw in the same pass left it, and the state change reads it after both draws | the regime's state and the accounts are separate aggregates of one owner (ADR-A106 decision 5, ADR-A131 decision 5), and the sketch lets Behaviour's runtime be held in SQL or memory while the ledger stays in RDF | firm on the text, in one example |
| R2 | the same pass | One pass changes two accounts and a regime state, each step reading what the last wrote | as R1. This is the case the sketch's §4.1 names as its falsifier, one atomic change to two families a deployment might place apart | firm on the text, in one example |
| R3 | Ledger, `research-grant.ttl`, `insurance-aggregate.ttl` | A draw's availability is the least balance along its account's path, a fold over each ancestor's subtree | cross-aggregate only if an account is the aggregate, see §5 | depends on §5 |
| R4 | Ledger, `insurance-aggregate.ttl` | A pass writes two accounts, a purpose-counting account outside the drawn account's tree, and a credit with a debit at the capacity pool | as R3 | depends on §5 |
| R5 | Eligibility, the bound examples | An evidence binding reads the applied ontology's data, a protocol's prohibited list in another aggregate from the participant, a set of consents still arriving | the applied data's placement is not stated. A closure makes the read as of the deciding record's time | open |
| R6 | Behaviour, derived triggers | "No premium remains due on any policy bound under the authority" reads a balance on other aggregates | what a derived trigger reads is the layer above's to declare, and no example declares it | open |
| R7 | Behaviour, occasions | An occasion's state is derived from act records `forCase` and breach records `ofOccasion`, which may sit in two aggregates | not stated | open |
| R8 | Behaviour, breach by silence | A breach relies on the completeness of an external register at the window's close | an external source with no watermark | open |

## 4. Reads that cross aggregates and read a pinned version

Nine. A Behaviour guard reads an admission profile's version, an Eligibility condition reads the scheme its contract resolves to at the resolution time, a ledger account reads its definition and the merge policy that definition names, an account reads its owner's kind, an occasion reads its parties' role occupancy versions, a Behaviour record reads the layer above's act, a decision reads its operational profile and closure, a posting reads a dated conversion rate, and an occupancy names its subject's persistent identity. Each may be copied to another store and stay on the correctness path, as the sketch's MS-Q7 narrowed allows. The merge policy is a version the definition names (ADR-A131's addendum), and no example shows the version node, so the pin rests on the text.

Two of them are pinned only in part. A concept scheme's membership resolved at a time is pinned, and its governance state, which every example asserts as active, is mutable, though no Eligibility law reads it. A closure makes evidence pinned as of its cut, with no source watermark to gate on.

## 5. A question the census raises, the ledger's aggregate

ADR-A131 decision 5 makes an account and its postings an aggregate. Its addendum of 2026-11-16 has one writer for each owner's ledger, moving one revision for the owner's ledger in the request that writes a posting. A draw reads its ancestors' balances and can write two accounts of one owner, so under decision 5 every tree draw is a cross-aggregate read of mutable state, and under the addendum none is. The consistency unit the addendum states is the owner's ledger. MSA-Q1's answer, the aggregate as the unit of placement, needs the unit stated once, and this note proposes the owner's ledger, since it is what a write is serialised on.

## 6. Verdict

The falsifier fires on the text of one example and is not shown to be common. The only Behaviour guards that read anything outside their own subject's state are the three of `ordered-draws.ttl`, which read a balance written earlier in the same pass and change two accounts and a regime state in one pass (R1, R2). Three things qualify it. The example uses Behaviour's deprecated allowance terms, its guards' admission profiles are comments, and Behaviour does not yet import Ledger. But the qualification cuts the other way for the future. The ledger's README has Behaviour's allowances give way to accounts, and threshold regimes are what Ledger serves Behaviour for, so once Behaviour imports Ledger this pattern is the ordinary form of a guard on an amount.

What follows for the leanings.

- **§4.1, an aggregate never spans stores.** It survives with a placement rule the sketch does not yet state. A persistent identity's Behaviour state and the ledger it guards on are placed in one store, or the pass that reads and writes both is a serialised writer over both, with the torn read MSA-I6's model X1 shows. A deployment cannot place them apart and keep a read-your-writes pass atomic.
- **§4.3, evaluation in a pure core.** A pass that reads what it wrote needs the core to carry the pass's own writes forward between steps, which the sequential environment already does in memory. The core needs no store read between steps, only the records it read at the start and the writes it made.
- **§4.4 and MSA-Q4.** Every cross-aggregate read in Eligibility and in the ledger's configuration is of a pinned version, or of evidence pinned as of a closure's cut. The narrowed MS-Q7 holds for them.
- **The watermark row of §4.2.** No source states a watermark. An Eligibility decision over bound evidence can take only the best-known row today, and records no read set (§7).

## 7. Gaps found on the way

- **A bound evaluation writes no record.** A decision needs at least one question (law L7), and an evaluation from evidence bindings has none, so the seven bound examples write no decision and their read set has nowhere to go.
- **The ledger's conversion terms outlive their removal.** ADR-A131 removes the conversion method and the amount as drawn, and the README, the runtime shapes and `revolving-facility.ttl` still carry them.
- **What a derived trigger reads is undeclared** in every example that uses one.
- **Two terms have no example**, `bhv:EffectApplication` and `elg:subjectRoleOccupancy`, so their reads cannot be counted.
