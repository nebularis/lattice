<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-HO0, correct the ownership note and its spike

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice HO0
([plan §3.5](../plans/formal-methods-track-h.md#ho0-correct-the-note-and-the-spike)).
**Source:** [the review](../notes/persistence-aggregate-ownership-review.md), findings S1, S2, S5, F1 and F6.
**Decisions needing confirmation:** none.

## Invariant

The exploration note and its spike must not state, as the current behaviour, what the review showed
to be wrong or superseded. Documents only, no tool changes.

## What changed

- **Spike `placement.py`.** A policy is a reference (AO-Q1): the binding owns only its share,
  `connectsPolicy` leaves the flat list and joins the references. `placement_graph` gains
  `shared_document`, a second placement whose layer attaches the first placement's owned document.
  `first_property_path` is documented as the compiler before H1.4a (S1).
- **Spike `test_spike.py`.** Seventeen checks become eighteen. The tree closure is 11 nodes. The
  shared-policy test is renamed and now asserts no second owner and no inbound edge. A new test
  shows a document with two owners.
- **Spike README.** Names the pre-H1.4a simulation (S1) and the single-writer store (S5).
- **Note.** The "today" verdicts describe the compiler before H1.4a (S1), a sweep of a reference is a
  live hazard (F1, TD-35), 11 nodes, the single-owner example uses a shared document, named graphs
  still need the classified tree (F6), TD-26 reads TD-34, the payload defect is TD-39, the questions
  are marked answered, and the recommendation that H1.4b and H1.5 wait is marked superseded.

## Test cases

In `spikes/persistence-aggregate-ownership/test_spike.py`. The spike is not part of any `mise` task.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO0-T1 | the placement graph / tree closure / 11 nodes, no policy, no vocabulary, no shared wording | L1 | + |
| HO0-T2 | a second placement referencing the same policy, and a quote / owners and inbound edges / none | L1 | − |
| HO0-T3 | a second placement attaching the owned document / owners / the document has both | L1 | + |
| HO0-T4 | the vocabulary guard, with `connectsPolicy` also forgotten / run / catches both concepts | L1 | + |

The other fourteen checks are unchanged.

## One command

From the repository root. A pass is `18 passed`.

```bash
python -m pytest spikes/persistence-aggregate-ownership -q
```

## Adversarial probe

Run on 2026-10-10 and restored. `connectsPolicy` was put back into the tree under the binding. The
11-node check and the shared-policy check failed (2 failed, 16 passed). After restoring, 18 passed.

## Deliberate non-coverage

- The compiler. HO0 changes no tool. HO1 changes two templates.
- A second engine. The spike uses rdflib only.
