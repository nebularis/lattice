<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I2, the read-set census

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I2
**Machine:** paper, against the Behaviour, Ledger and Eligibility specifications and examples on `spi/multi-store-architecture` at 2026-11-18. **Placement:** T0, public. Substrate configuration, nothing domain-specific.
**Status:** built 2026-11-18, not verified. Reworked the same day on the ledger's unit as the maintainer decided it, the owner's ledger.

## Scope

- The note [MSA-I2-read-set-census.md](../notes/multi-store/MSA-I2-read-set-census.md), which classifies what each guard and effect of the forty examples and four tests reads, by aggregate and by pinned or mutable, and gives the verdict against the falsifier.
- An inventory with a file and line for each row, gathered with a sub-agent and not committed. The passages the verdict rests on were read again in the source: the premise of `ontology/behaviour/examples/ordered-draws.ttl`, ADR-A131 decision 5 and its addendum on one writer for each owner's ledger.
- The rework reads each cross-aggregate read again under the owner's ledger, against the maintainer's brief of 2026-11-18 and the texts it names, ADR-A131's addendum proposed that day and the ledger plan's LG-Q37 and LG-Q44, read on `docs/placement-vehicles-structure` and not copied here. Each read is marked inside a ledger, pinned by revision once LG-27 lands, or changeable across a unit.
- Out of scope. Any change to the three modules.

## Result in one paragraph

Under the owner's ledger the falsifier does not fire. The ledger's own reads across accounts, a draw's path and a purpose counted outside it, are inside one ledger (R3, R4). The one firm read from outside a ledger, the three guards of `ordered-draws.ttl` on a seat bundle's balance (R1), is of a balance pinned by revision once LG-27 lands. No firm guard is left that a read by revision does not cover, on three conditions the example needs and no text states yet: the writer returns the revision each posting moved the ledger to and a later guard names it (C1), a guard outside the ledger that states the ledger's own refusal takes the writer's refusal as its failing (C2), and a pass's postings are answered from receipts keyed on the pass, so a replay by those revisions completes the Behaviour record written after them (C3). One candidate, on a comment: `run-off.ttl`'s derived trigger reads premium due over the policies bound under an authority, and no revision pins which policies those are. The sketch's §4.1 survives with no placement rule. As first written the census read the falsifier as firing on `ordered-draws.ttl` and proposed placing an identity's Behaviour state with its ledger, which the maintainer did not take.

## Checks

| Claim | Checked against |
|---|---|
| the alert guard reads the bundle as the first draw left it, and the state change follows in the same pass | `ordered-draws.ttl`, its premise comment |
| an account and its postings form an aggregate | ADR-A131 decision 5 |
| one writer and one revision for each owner's ledger | ADR-A131's addendum, "One writer at a time for each owner's ledger" |
| the notes the sketch cites exist | `docs/developer/sketches/ledger-folds-and-stores.md` and `multi-store-runtime.md`. The inventory had looked for them under `notes/`, and its claim that they were missing is not carried into the note |
| a path never leaves one owner's ledger | the ledger README's `ldg:partOf`, "the parent definition's instance for the same owner" |
| one owner holds every account of `insurance-aggregate.ttl` and of `research-grant.ttl` | `ex:programme`, "owner of every account in this example", and `ex:institution`, named by `ldg:forOwner` |
| the state change of `ordered-draws.ttl` is a record the pass writes | `ex:occ-on-overage`, a `bhv:StateOccupancy` entered by `ex:p3-move-to-overage` |
| R6's trigger is a comment and names no account | `run-off.ttl`, `ex:on-premium-collected` |

| Command | Result |
|---|---|
| `mise exec -- python tools/writing_rules.py docs/developer/notes/multi-store/MSA-I2-read-set-census.md` | 0 failures |

## Adversarial probes

1. The census looked for a guard reading mutable state in another aggregate in every Behaviour example, not only those with declared guards, and counted scheduled, derived and external triggers as guard-like reads. Only `ordered-draws.ttl` reads such state firmly.
2. The ledger's tree draws were read under both units ADR-A131 stated, and under the one decided.
3. Each of R1's guards was replayed in pass 3 against a crash between the seat posting and the Behaviour record, reading the latest revision and reading by the revision recorded. Only the second gives the original pass, which is C3.

## Open matters

- **For the maintainer: C1 to C3.** The decision rests on them, and they are stated nowhere yet. They belong to the ledger's runtime document, to Behaviour's pass, or to the sketch's §4.1, which the maintainer places.
- **For the maintainer: R6.** Whether a derived trigger's read over a set of ledgers names the version of what chose the set.
- The gaps of the note's §7 are for the modules' owners.
