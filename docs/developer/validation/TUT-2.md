<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: TUT-2, chapters 4 to 6

**Unit:** [`lattice-tutorial`](../status/lattice-tutorial.md)
**Plan:** [lattice-tutorial.md](../plans/lattice-tutorial.md) §3 to §5, decisions TUT-D1 to TUT-D5

## Invariant

Chapters 4 to 6 add Foundation, Wording, Instrument and Party to the running facility, in the voice
and depth TUT-1 set. Each idea is introduced through its data-architecture counterpart, every
excerpt is a verbatim copy of its source, and every claim about a layer is checked against that
layer's README, spec, shapes or examples.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| TUT2-01 | chapters 0 to 6 / `check:tutorial-snippets` / `OK 25 excerpts and 10 repository links match the checkout` | L0 | + |
| TUT2-02 | the page / served at 375 px / two Mermaid SVGs (12 and 5 nodes), no syntax error, no horizontal page scroll | L6 | + |
| TUT2-03 | the page / served / 25 Turtle blocks highlighted | L6 | + |
| TUT2-04 | the maintainer, as the intended reader / reads chapters 4 to 6 / no term used before it is explained, no claim that does not match the repository | review | + |

## One command

```bash
mise run check:tutorial-snippets
```

Pass: `OK 25 excerpts and 10 repository links match the checkout`, then `10 passed`. To read the
chapters as published, `mise run serve:jekyll` and open `http://127.0.0.1:4000/tutorial.html#identity`.

## Artefacts to inspect

- `docs/_includes/tutorial/04-identity-and-keys.md`, `05-text-and-meaning.md`, `06-who-owes-what.md`

| Chapter | Sources re-read |
|---|---|
| 4 | `ontology/foundation/examples/keys.ttl`, `ontology/foundation/README.md` §6 to §8, `ontology/foundation/shapes/constraints.ttl`, `ontology/foundation/vocab/` |
| 5 | `ontology/wording/examples/facility-agreement.ttl`, `ontology/wording/README.md` (rank keys, reliance), `ontology/wording/examples/reused-clause.ttl`, `ontology/instrument/examples/facility-agreement.ttl`, `ontology/instrument/examples/facility-parameters.ttl`, `ontology/instrument/README.md` §5.1 and §5.2 |
| 6 | `ontology/instrument/examples/facility-agreement.ttl`, `facility-definitions.ttl`, `ontology/instrument/README.md` §4.4 and §4.5, `ontology/instrument/shapes/constraints.ttl` (law I8), `ontology/party/spec/party.ttl`, `ontology/party/vocab/party-vocab.ttl` |

## Deliberate non-coverage

- Instrument's time, regimes, triggers, survival and amendment are left to chapter 9, and its
  conditions to chapters 7 and 8.
- Party's delegation is not covered. No facility example uses it.
- The plan's chapter 7 source for Vocabulary, `vocabulary/examples/temporal-handover.ttl`, is
  unchanged. Chapter 5 mentions reliance "as amended" without an excerpt.

## Results

Run 2026-10-15 on Windows 11.

| Check | Result |
|---|---|
| TUT2-01 | passed on the first run |
| TUT2-02 | passed |
| TUT2-03 | passed |
| TUT2-04 | awaiting the maintainer |

One claim was removed while checking sources. A first draft said a transfer of a lender's
participation replaces an occupancy without changing the relations. No example or README shows
that, so chapter 6 now says only what the example does.

## Adversarial probe

Not run for this slice. The check's behaviour on a mismatched excerpt was shown in TUT-1.
