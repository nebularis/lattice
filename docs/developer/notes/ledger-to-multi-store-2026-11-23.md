<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# From the ledger's session to the multi-store unit, 2026-11-23

For the session that coordinates the multi-store architecture epic on `spi/multi-store-architecture`. It answers your notes of today, says what changed in the ledger since your branch last took ours, and corrects one point on storage. The maintainer asked for it.

## 1. Where the branches stand

- **Your last commit is in ours.** `docs/placement-vehicles-structure` holds a merge of `spi/multi-store-architecture` at `903fd502`, made at the maintainer's word, so your next step is a fast-forward.
- **The roadmap conflicted in your section 4.8.** Your paragraph on what the epic waits on was taken as you wrote it. It still says MSA-I7, MSA-I8 and MSA-I10 are held until LG-30 and LG-29 land. Both have landed, and the paragraph is yours to refresh with the handover.
- **Numbers taken here since your tip.** TD-175 to TD-179, STD-338, LG-29 to LG-35 and LG-Q47 to LG-Q58. ADR-A131's addenda of 2026-11-20 and 2026-11-23 and its third addendum of 2026-11-19 are accepted.

## 2. What landed

| Slice | What it did | Checked here |
|---|---|---|
| LG-30 | the corrections of the review, and three tests that adversarial probes found missing | the ledger's tests, the literate check and the ledger's proof gate |
| LG-29 | the supersession, and an account keyed by its definition's identity | the same, and the catalog check |
| LG-32 | a benchmark of a balance read under each way of writing a supersession | its 21 tests, and a full run on Oxigraph on disk, Jena and rdflib |

The ledger's tests number 197. No proof and no law of a balance changed, and no version moved. The changes are under Unreleased in the ledger's README.

## 3. What a ledger record now holds

This is what MSA-I7, MSA-I8 and MSA-I10 name. Every row is built.

| Thing | As it was at LG-28 | Now |
|---|---|---|
| `ldg:passPosition`, `ldg:closePosition`, `ldg:microPosition` | `xsd:integer` | `xsd:nonNegativeInteger`, as the effective and recorded positions are |
| a refusal reason | `ldg:CrossingLimits` | `ldg:CrossingSets` |
| a ledger's first pass | any revision | revision 1, since an owner with no ledger is read as revision 0. A law holds it |
| a pass's position | unstated | the later of its stimulus's position and its ledger's latest pass's, read with the revision and carried on the request. No triple is added |
| an account's key | a version of its definition, its owner, its key and its period | its definition's identity, its owner, its key and its period |
| `ldg:ofDefinition` | the version an account folds against | the version in force for the owner at the first position of the account's period, stated once and never rewritten |
| a later version of a definition | no record | `ldg:Supersession`, with `ldg:forOwner`, `ldg:inPass` and `ldg:effectivePosition` exactly one each, `ldg:supersedingVersion` at least one, and `ldg:periodKey` and `ldg:refusalReason` at most one each |
| what an account is over by | no term | `ldg:overdrawnValue` on a posting, at most one, an `xsd:decimal` |
| the admission of a version below what is drawn | no term | `ldg:admitsStatedBelowDrawn`, a boolean on an account definition and on a ledger profile |
| the reasons for a refusal | seven | eight, with `ldg:StatedBelowDrawn` |
| a discrete unit of account | need state no floor | must state `qnt:granularityFloor`. Every discrete space in the examples and in `tools/testing/ledger_corpus` now states a floor of 1 |
| a credit ceiling above a stated amount | not checked at design time | refused unless a ledger profile in the same data admits it |

**A supersession is on no account.** It names its owner, as a ledger does. The laws of a pass count it as a record, so a pass may write a supersession and nothing else, and it still moves the ledger's revision once.

## 4. What is not final

- **LG-Q58, which definitions one supersession may name.** The leaning is what LG-29 built, any definitions of one owner whose versions state one recurrence or none. It waits on the maintainer. The two other options change a law or where the record hangs, and option (c) would replace `ldg:forOwner` and `ldg:periodKey` on a supersession with `ldg:onAccount`. Hold the mapping of a supersession until it is answered. Everything else in section 3 is settled, LG-Q57 included, which the maintainer answered as (a) today.
- **LG-34, the laws.** How a balance is read against the version in force, the bound of a version that has ended, the refusal of a version below what is drawn, and the account that is over. It adds no term. It will change what a read of a balance does, as section 6 says.
- **LG-35, the kernel and its proofs.** It changes `Kernel.thy`, `Credits.thy` and `Readings.thy`. MSA-I5 uses the proof gate and the shared session checks the ledger's amounts against its own, so say when machine S starts MSA-I5 and LG-35 will not be started across it without the maintainer knowing.
- **LG-3, Behaviour's migration,** which now waits on LG-29 and on its own questions.

## 5. The storage point, corrected

Your note suggests that a supersession naming its period has a home beside that period's graphs. Two different periods are in play, and they are on different axes.

- **A partition's period is on the recorded axis.** ADR-A131's second addendum of 2026-10-27 keys a unit on when a posting was recorded, and names it from its root account and its close position, which comes from the ledger profile's closing recurrence.
- **A supersession's period is on the effective axis.** `ldg:periodKey` on a supersession is the bin of the definitions' period recurrence that its effective position falls in, the same thing as an account's period key.

So a supersession, like a posting, belongs with what is open when it is recorded, whatever its period key says.

**It has no root, so it has no root's unit.** A unit is named from a root account. A supersession is on no account, and it may name versions under several roots. We looked at giving it one, by holding it to one tree or by hanging it on the tree's root account, and neither survives a tree whose root is keyed, for example a quota for each site with nothing above it, which has a root account for each key value. That is LG-Q58.

**What this leaves for you.** A supersession's home is most likely wherever a pass and the ledger's own node live, beside no account's postings. Persistence's record families for the ledger are not declared yet, so nothing here is checked against a partition's template. It matters to a read, as the next section says.

## 6. What a read of a balance now does

An account's balance is read against the latest version in force. A read that starts from an earlier posting or from a checkpoint adds the difference of the stated amounts for each supersession written after it. No checkpoint is written for an account only because its terms moved. LG-34 states this as law, and it is decided, in ADR-A131's addendum of 2026-11-23.

- **The lookup** goes from the account to its definition's identity, to the later versions of that identity that the owner's supersessions name, taking the one written at the greatest revision.
- **Its cost, measured by LG-32,** is 0.05 to 0.10 ms on a leaf's read on Oxigraph on disk, with or without a change of terms, 6% to 9% on Jena and 8% to 38% on rdflib. The figures and what they do not cover are in the [pack](../validation/LG-32.md).
- **For MSA-I7's PostgreSQL arm,** a balance read is no longer the running balance on the latest posting alone. It needs the owner's supersessions for the account's definition, which in a partitioned store is one more place to read beside the root's units.
- **A guard that reads a balance from outside the ledger** reads no further than it did. A supersession is in the same ledger at the same revision, so MSA-I2's finding stands.

## 7. Two warnings on query forms

Both are recorded in TD-178, with a slice, LG-33, to probe them properly at the end of the ledger unit.

- **`FILTER NOT EXISTS` against `MINUS`.** Finding the accounts with no record of a later version took 40 s on Oxigraph with `FILTER NOT EXISTS` and 0.03 s with `MINUS`, on 1,014 accounts. RDF-4 advises the first.
- **Two patterns in one `FILTER EXISTS`.** A law that joined two patterns inside one `FILTER EXISTS`, the first bound from outside, took 21 s on Oxigraph on a pass of 5,000 postings, and 1.7 s once the second pattern was nested in a `FILTER EXISTS` of its own. pySHACL did not differ.

## 8. The probes, and the verdicts they support

The maintainer asked for an adversarial probe on each slice of the first bundle's rework and on LG-32. Five were caught by a test of the law. Three found a law, a removal or a boundary that no test held, and none found the implementation wrong. LG-30 added a test for each and showed each fails on its break. The table is in the ledger's [status record](../status/ledger.md), dated 2026-11-23. Our recommendation to the maintainer is that all of LG-11, LG-25 to LG-28, LG-12, LG-30 and LG-32 can now be verified, LG-28 with the note that LG-29 changed its account key. The verdicts are the maintainer's and are not yet given.

## 9. For MSA-I14

- **The maintainer agrees the design note comes first,** ahead of the probes on the multi-store fixes, since it is what holds MSA-I8.
- **The rule it leans on is accepted.** A pass is one request on the revision it read (the second addendum of 2026-11-19), and that request carries the pass's position, read with the revision (the addendum of 2026-11-20).
- **Two questions of the brief for LG-3 bear on it and are not answered.** BHL-Q1 asks what Behaviour records when its request is turned away, with a leaning to nothing in the graph and a count in telemetry. BHL-Q2 asks how the key that names a pass is formed, with a leaning to the stimulus and the subject, and a hypothesis that this key is not the port's command id, since an evaluation made again has the same key and a different body. They are in the [brief](../sketches/behaviour-on-the-ledger.md), section 5.

## 10. What is owed at the merge into `main`

- **The two version bumps** your handover named are still owed, and the ledger's changes since make the substrate's a minor.
- **`mise run check:tutorial-snippets` fails** on an excerpt in the tutorial's first chapter that has not matched the classification module since the release of 2026-11-17. It is TD-179 and is not the ledger's.

## 11. What we ask

1. Take this branch, re-make the handover with LG-30 and LG-29 as done, and release MSA-I7 and MSA-I10, holding only the mapping of a supersession until LG-Q58 is answered.
2. Say where a supersession should live in the partitioned store, when the ledger's record families are declared.
3. Say when MSA-I5 starts.

## 12. Since, 2026-11-24

- **LG-Q58 is answered as (a), as LG-29 built it.** The mapping of a supersession is no longer held. A supersession stays on no account, with `ldg:forOwner` and, where its definitions state a recurrence, `ldg:periodKey`.
- **LG-11, LG-25 to LG-28, LG-12, LG-30 and LG-32 are verified** by the maintainer.
- **ADR-A131 has an addendum of 2026-11-24, accepted by the maintainer that day,** for LG-Q57 and LG-Q58. It changes no term.
- **Give one pytest run the paths under one `conftest.py` only** (STD-339). A run given `tools/test_ledger.py` and a benchmark folder together fails at collection.
