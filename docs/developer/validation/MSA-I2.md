<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I2, the read-set census

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I2
**Machine:** paper, against the Behaviour, Ledger and Eligibility specifications and examples on `spi/multi-store-architecture` at 2026-11-18. **Placement:** T0, public. Substrate configuration, nothing domain-specific.
**Status:** built 2026-11-18, not verified. One question for the maintainer.

## Scope

- The note [MSA-I2-read-set-census.md](../notes/multi-store/MSA-I2-read-set-census.md), which classifies what each guard and effect of the forty examples and four tests reads, by aggregate and by pinned or mutable, and gives the verdict against the falsifier.
- An inventory with a file and line for each row, gathered with a sub-agent and not committed. The passages the verdict rests on were read again in the source: the premise of `ontology/behaviour/examples/ordered-draws.ttl`, ADR-A131 decision 5 and its addendum on one writer for each owner's ledger.
- Out of scope. Any change to the three modules.

## Result in one paragraph

The falsifier fires on the text of one example and is not shown to be common. In `ordered-draws.ttl` a regime's guards read a seat bundle's balance that an earlier draw in the same pass wrote, and the pass changes two accounts and the regime's state. The example is written in Behaviour's deprecated allowance terms, but those give way to ledger accounts, so the pattern is the ordinary form of a guard on an amount once Behaviour imports Ledger. The sketch's §4.1 survives with a placement rule it does not state, that an identity's Behaviour state and the ledger it guards on are placed together. Every other cross-aggregate read is of a pinned version, or of evidence pinned as of a closure's cut. The census also finds that ADR-A131 states two units for the ledger, the account in decision 5 and the owner's ledger in the single-writer addendum.

## Checks

| Claim | Checked against |
|---|---|
| the alert guard reads the bundle as the first draw left it, and the state change follows in the same pass | `ordered-draws.ttl`, its premise comment |
| an account and its postings form an aggregate | ADR-A131 decision 5 |
| one writer and one revision for each owner's ledger | ADR-A131's addendum, "One writer at a time for each owner's ledger" |
| the notes the sketch cites exist | `docs/developer/sketches/ledger-folds-and-stores.md` and `multi-store-runtime.md`. The inventory had looked for them under `notes/`, and its claim that they were missing is not carried into the note |

| Command | Result |
|---|---|
| `mise exec -- python tools/writing_rules.py docs/developer/notes/multi-store/MSA-I2-read-set-census.md` | 0 failures |

## Adversarial probes

1. The census looked for a guard reading mutable state in another aggregate in every Behaviour example, not only those with declared guards, and counted scheduled, derived and external triggers as guard-like reads. Only `ordered-draws.ttl` reads such state firmly.
2. The ledger's tree draws were read under both units ADR-A131 states, and the verdict for them is given for each.

## Open matters

- **For the maintainer: the ledger's aggregate.** The note proposes the owner's ledger as the unit, since the addendum serialises a write on it. MSA-Q1's answer needs the unit stated once.
- The placement rule of the verdict, an identity's Behaviour state with its ledger, goes to MSA-Q1 and MSA-Q10 with this evidence.
- The gaps of the note's §7 are for the modules' owners.
