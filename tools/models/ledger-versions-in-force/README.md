<!-- SPDX-License-Identifier: MPL-2.0 -->

# An account under a later version of its terms

A model, in plain Python, of one question about [ADR-A131](../../../docs/architecture/decisions/ADR-A131-ledger-layer.md)'s ledger, which postings count against which version of an account's terms once an account may come under a later version. It is the evidence for LG-Q49 of the [sketch](../../../docs/developer/sketches/ledger-definition-versions-in-force.md) on an account under a later version of its definition, which is not yet answered.

It is a table of worked histories and not a search. One account, whose first version states 10, and eleven histories of draws, credits and later versions in the order they are recorded. Each of four rules decides every draw, and two invariants are read after every step.

| Rule | A draw is granted where |
|---|---|
| R1 | everything recorded and the draw are within the version the account holds when the draw is recorded |
| R2 | everything recorded and the draw are within the version in force at the draw's effective position |
| R3 | R1 holds, and for each version whose successor is in force from a position after the draw's, what took effect before that position and the draw are within that version |
| R4 | what took effect up to the draw's effective position and the draw are within the version in force there |

| Invariant | Holds when |
|---|---|
| I1 | everything recorded is within the latest version's stated amount |
| I2 | for each version that has a successor, what took effect before the successor's position is within that version's stated amount |

## Run it

```bash
mise exec -- python tools/models/ledger-versions-in-force/versions_in_force_model.py
```

It exits 0 where every verdict is the one the file records, and prints the table.

## What it shows

- **R3 agrees with our reading of the drafting on every history,** and breaks neither invariant by a draw.
- **R1 differs in three,** a draw backdated onto a spent version, a credit that took effect after a version ended, and three versions. It keeps I1 and breaks I2 in each.
- **R2 differs in three,** refusing a draw both versions have room for, and granting against a bound already used where an amount was lowered or a credit took effect late.
- **R4 differs in two,** one of them with no later version at all, where it takes a constant amount below zero.
- **A version that states less than is drawn breaks I1 under every rule,** since the version and not a draw does it. That is LG-Q53 of the sketch.

## What it leaves out

A credit's ceiling and its kind, since a credit is applied in full. A tree, since it has one account. Two accounts of one definition. Our reading of the drafting is a hypothesis, written beside each history in the file.
