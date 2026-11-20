<!-- SPDX-License-Identifier: MPL-2.0 -->

# A pass and a ledger's revision

An exhaustive model, in plain Python, of one question about [ADR-A131](../../../docs/architecture/decisions/ADR-A131-ledger-layer.md)'s ledger, whether a pass moves a ledger's revision once, or once for each of its postings. It is the evidence for LG-Q45 of the [Ledger plan](../../../docs/developer/plans/ledger.md), answered 2026-11-19 for once a pass.

It models the three transitions of Behaviour's [`ordered-draws.ttl`](../../../ontology/behaviour/examples/ordered-draws.ttl). One activation draws a seat while the bundle has one, draws an alert when that leaves fewer than 2 seats, and moves the licence to overage when the bundle is empty, each step seeing what the one before it left.

## What it runs

One activation against one other writer on the same two accounts, either a credit of 3 seats or a second activation, in every interleaving, with and without one crash of the first activation at any point. Twelve starting cells, the bundle at 0, 1 or 2 and the quota at 1 or 3, each with either writer. It first reproduces the example's own table for three activations run one after another.

| Check | Holds when |
|---|---|
| O1, a pass is whole | every outcome is the outcome of the two run one after the other, in some order |
| O2, a crash is safe | every outcome with a crash is an outcome without one |

| Protocol | What it does |
|---|---|
| A | a pass is evaluated from one revision and written as one request, which is refused when the ledger has moved from the revision the pass read. A replay finds the pass's write and evaluates from the revision before it |
| A' | as A, written on whatever revision is latest |
| B | each posting is a write of its own, each guard reads the latest revision, and nothing is kept for a replay |
| C | each posting is a write of its own. A later guard reads the revision an earlier posting produced, a refusal by the writer counts as the guard failing, and a replay reads from a receipt kept for each posting |
| C+ | as C, and a refusal returns the revision it was refused at, which the next guard reads |
| C++ | as C+, and the revision the pass started from is recorded |

## Run it

```bash
mise exec -- python tools/models/ledger-pass-revision/pass_revision_model.py
```

It takes a few seconds and needs nothing beyond Python. It prints each protocol's counts with one witness schedule for each check that fails, and exits non-zero when a count differs from the table below.

## Result

Run on 2026-11-19, with Python 3 on macOS.

| Protocol | O1 fails, no crash | O1 fails, one crash | O2 fails | Distinct outcomes no order gives, no crash |
|---|---|---|---|---|
| A | 0 of 12 | 0 of 12 | 0 of 12 | 0 |
| A' | 1 | 7 | 6 | 1 |
| B | 7 | 12 | 12 | 9 |
| C | 7 | 7 | 2 | 13 |
| C+ | 7 | 7 | 2 | 9 |
| C++ | 7 | 7 | 0 | 9 |

- **A holds.** Every outcome is one the passes give when run one after another, with a crash or without.
- **The refusal is what makes it hold.** Under A', two activations on a bundle of 2 are both evaluated at 2, both draw and both alert, the bundle ends at 0 and neither licence moves to overage.
- **A posting that is its own write cannot keep a pass whole.** The revision a posting returns includes whatever landed before it. With the bundle at 0 the alert is drawn, a credit of 3 lands before the alert's posting, the overage guard reads the revision that posting produced and finds 3 seats. The licence has an alert for an empty bundle and no move to overage, which no order of the two gives.
- **A refusal has to return its revision.** Under C the guard after a refused posting reads the revision before the refusal, and four more outcomes appear that no order gives.
- **A guard that fails leaves no receipt.** Under C and C+, with the bundle at 0, the seat draw's guard fails, the alert is posted, the pass stops before its Behaviour record, and a credit lands. The replay evaluates the seat draw's guard on the latest revision and draws a seat after its own alert. Recording the revision the pass started from closes it.

## What it does not show

- **Two ledgers.** Both accounts are in one ledger, which the example does not state. Where a pass writes two ledgers it makes two writes, and C+ with the start revision recorded, one write for each ledger, is what we expect to hold there. That is reasoned and not modelled.
- **Cost under contention.** Under A a pass is evaluated once more for each write that lands between its read and its write. The model counts no evaluations.
- **More than one other writer, or more than one crash.**
- **How a replay finds its pass.** The model keys a pass's receipt on its activation.

## A pass's position

A second model, `pass_position_model.py`, on the same actors and schedules. The ledger holds its passes to one order, in which a pass at an earlier position never records a greater revision. The model asks which rule for a pass's position keeps that. It is the evidence for LG-Q47 of the [Ledger plan](../../../docs/developer/plans/ledger.md).

Each actor's stimulus has a position of its own, the first actor's before the other's, after it, or the same. With the twelve starting cells and either writer that is 36 cells. The ledger starts with no pass.

| Check | Holds when |
|---|---|
| O3, positions follow revisions | in every outcome, the passes' positions never fall as their revisions rise |
| O4, never before its stimulus | in every outcome, no pass is at a position before its stimulus's |

| Rule | A pass's position is |
|---|---|
| stimulus | its stimulus's position |
| read | the later of its stimulus's position and the position of the ledger's latest pass, read with the revision the pass is evaluated from |
| writer | the later of its stimulus's position and the position of the ledger's latest pass, taken by the writer when it writes |

```bash
mise exec -- python tools/models/ledger-pass-revision/pass_position_model.py
```

It exits non-zero when a count differs from the table below. Run on 2026-11-20, with Python 3 on macOS.

| Protocol | Rule | O3 fails, one after another | O3 fails, no crash | O3 fails, one crash | O4 fails |
|---|---|---|---|---|---|
| A | stimulus | 20 of 36 | 20 | 20 | 0 |
| A | read | 0 | 0 | 0 | 0 |
| A | writer | 0 | 0 | 0 | 0 |
| A' | stimulus | 20 | 20 | 20 | 0 |
| A' | read | 0 | 10 | 10 | 0 |
| A' | writer | 0 | 0 | 0 | 0 |

- **A pass cannot take its stimulus's position.** Two stimuli written out of the order of their positions break the order with no contention at all, in every cell where both write a pass and their positions differ. A request that is turned away is one way to arrive late, and not the only one.
- **The later of the two, read with the revision, holds under A.** The request is written only while the ledger is at the revision read, so the latest pass is still the one whose position was read.
- **Without the refusal it does not.** Under A' a pass reads the latest position, another pass lands at a later one, and the first is written behind it. In four of the cells with a second activation the stale request overdraws and is evaluated again, which is why the count is 10 and not 14.
- **A position given by the writer holds under either protocol,** and has the writer read the latest pass's position, which a request under A already fixes.

The model gives every pass a stimulus position and a ledger with no earlier pass. It does not show a pass over two ledgers, where each ledger's latest pass may be at a different position.

It checks the instances it generates and proves nothing beyond them.
