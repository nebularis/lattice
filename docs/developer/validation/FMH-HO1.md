<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-HO1, fix the composite replace (TD-39, TD-36)

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice HO1
([plan §3.5](../plans/formal-methods-track-h.md#ho1-fix-the-composite-replace-td-39-td-36)).
**Source:** [the review](../notes/persistence-aggregate-ownership-review.md), findings F2 and F3, and
[sketch §7.1](../sketches/persistence-aggregate-ownership.md#71-replace-cas-replace-composite-property-and-its-dataset-guard-variant).
**Decisions needing confirmation:** none. One deviation from the plan, below.

## Invariant

A replace of a composite aggregate removes the triples it sweeps and writes the new payload to the same
place, and does work in proportion to the aggregate's size. Before this slice the payload went to the
monthly receipt graph (TD-39), and the sweep joined two independent `OPTIONAL`s into one solution per
pair of a root triple and a member triple (TD-36).

## What changed

- `cas-replace-composite-property.mustache` and its `-dataset-guard` variant. `DELETE` takes
  `?s ?p ?o`, the payload is inserted without a `GRAPH` wrapper (the default graph, where the sweep
  deletes from), and one `OPTIONAL { $root <p>* ?s . ?s ?p ?o }` replaces the two. `*` brings in the
  root itself. Only the receipt records are written to the log graph. Header comments updated.
- `tools/persistence/README.md`: the known-limitations entry says `*` and where the payload goes.
- Register: TD-39 and TD-36 removed.
- Spikes. `spikes/persistence-aggregate-ownership` asserts the payload is in the default graph.
  `spikes/persistence-oxigraph` removes the payload stand-in from the update it runs (same reason as
  the deviation below).

## Deviation from the plan, for the maintainer

The plan said H1.4a-T10 and T11 must pass unchanged, and to explain a failure before editing.
**We predicted the failure before running anything**, from reading the helper. Its update text carries
`templatecheck`'s stand-in for the payload slot (`<urn:x-check:s> <urn:x-check:p> <urn:x-check:o> .`),
which went to the log graph and so never showed in the default graph. After this slice it lands in the
default graph. Run, T10 and the two T11 cases failed for that reason and no other.

The change is to the **test input and not to the expected results**. The helper deletes the stand-in
from the rendered text, taking the string from `templatecheck._SLOT_STAND_INS` so it cannot drift, and
the replace runs with an empty payload, which is what the tests always meant. Their assertions are
unchanged (T10 gives `[]`, T11 gives `urn:pay:1` or `urn:li:1`) and still cover the whole default
graph. Filtering the stand-in's subject from the result was rejected, because it makes the assertion
skip something. T10 and T11 never covered where the payload lands. HO1-T1 to T3 do. HO5 rewrites T10 and
T11 for the ownership tree and the data graph.

## Test cases

In `tools/persistence/tests/test_composite_sweep.py`, on rdflib's `Dataset`, with the payload slot
filled in place of the stand-in.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO1-T1 | an order (`status "open"`, two line items), a version row at sequence 1 / replace with `status "paid"` / `"paid"` is in the default graph and in no other | L5 | + |
| HO1-T2 | as T1 / after the replace / `"open"` is in no graph, and no domain triple is in a `urn:g:txlog/` graph | L5 | + |
| HO1-T3 | as T1 / after the replace / one `pat:Revision` for sequence 2, in a `urn:g:txlog/` graph | L5 | + |
| HO1-T4 | the dataset-guard variant, with the dataset epoch row / as T1 and T2 and T3 / as those | L5 | + |
| HO1-T5 | a root of 5 triples and 3 line items of 4 triples each, both variants / the `WHERE` run as a `COUNT` / 17, not 60 | L2 | + |
| HO1-T6 | as T1 with `expectedSeq` 7 / replace / the dataset is unchanged, quad for quad | L5 | − |
| HO1-T7 | both variants / S-3 and S-4 over the compiled profile, and `persistence hygiene` on the example / no finding | L1 | + |

T5 and T7 run for both variants, so there are nine test items. H1.4a-T10 and T11 pass with the
assertions unchanged.

## One command

Run from the repository root. A pass is `917 passed, 1 xfailed` (908 before this slice plus the nine
new items), with no new skip. The expected failure is TD-23.

```bash
mise run check:persistence && mise exec -- python -m pytest spikes/persistence-aggregate-ownership -q
```

The second command passes with `18 passed`.

## Adversarial probes

Run on 2026-10-10, each restored afterwards.

| Mutation | Result |
|---|---|
| the plain template put back to its previous text | T1, T2 and T5 (plain) fail |
| the dataset-guard template put back to its previous text | T4 and T5 (dataset guard) fail |
| `*` changed to `+` in the plain template (the root's own triples no longer swept) | T2 and T5 fail, and H1.4a-T10 and both T11 cases fail, which also shows those tests still guard the sweep |
| the sequence guard in the plain template replaced by a free variable | T6 fails |

## Not run

`spikes/persistence-oxigraph/rdflib_comparison.py` and its tests, which need `pyoxigraph`. It is not
installed here, and the available wheel does not match this Python. We decided on 2026-10-10 that this
run is **not mandatory** (the plan now says so). Its two scenario files were edited to remove the
stand-in and pass a syntax check only. The next run on a machine with `pyoxigraph` should confirm the
composite counts still read `[]`, `["urn:pay:1"]` and `["urn:li:1"]`.

## Deliberate non-coverage

- Which property the update follows, and several owned properties. HO4 and HO5.
- The default graph against static check S-1 (TD-40). HO5 moves the composite family to a named data graph.
- Create and tombstone delete for the composite strategy (TD-04). HO7.
