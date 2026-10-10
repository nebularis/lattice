<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H1.5, stable compiled-profile labels

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H1.5
([plan §3, H1.5](../plans/formal-methods-track-h.md)).
**Source finding:** the source review §16.4, and TD-09 (removed from the register by this slice).
**Decisions needing confirmation:** none.

## Invariant

Compiling the same configuration twice must produce byte-identical Turtle. Before this slice the blank
nodes of a compiled profile took a fresh label per run, so the output was isomorphic between runs and
never identical, and a compiled profile could not be committed and diffed as generated SPARQL can.

## What changed

- `compiler.py`: every blank node `emit_compiled_profile` makes is labelled from a stem, a digest of the
  target and deployment (`p` plus 12 hex digits), and a suffix naming its role (`-dim-<dimension>`,
  `-op-<index>`, `-op-<index>-binding-<name>`, `-requirement`, `-check`, `-diagnostic-<index>`, and so
  on). The reasoning-requirement list is written by hand, since rdflib's `Collection` mints a new blank
  node for each cell.
- Measured before the change: with `PYTHONHASHSEED` 1 and 2, `persistence compile` wrote different bytes
  for all four examples tried. After: identical.
- A stale comment in `test_determinism.py` is replaced. Its isomorphism assertion is unchanged.
- TD-09 removed from the register. `tools/persistence/README.md` lists the new test file.
- No golden compiled profile is committed. The plan said HO slices regenerate H1.5's golden files "if it
  has any". It has none, so the byte-identity is asserted by comparing two runs. Adding a golden file would
  make every later change to compiled output regenerate it, and we left that choice open.

## Test cases

In `tools/persistence/tests/test_compiled_profile_stable.py`. `EXAMPLES` is every shipped example that
compiles, which at the time of writing is 19, found at collection time.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| H1.5-T0 | the example list / count / at least 15 | L1 | + |
| H1.5-T1 | each example / compile twice, serialise / byte-identical | L2 | + |
| H1.5-T2 | each example, its triples loaded in two shuffled orders / compile, serialise / byte-identical | L2 | + |
| H1.5-T3 | each example / every blank node's label / derived from a target stem | L1 | + |
| H1.5-T4 | the minting anchors example (7 targets) / label stems / 7 distinct | L1 | + |
| H1.5-T5 | three examples / `persistence compile` in two processes with different hash seeds / identical bytes | L5 | + |
| H1.5-T5b | the baseline with a capability spec / compile twice / identical, and a `-check` node exists | L2 | + |
| H1.5-T6 | the composite example's compiled profile / reread and instantiated / the operations are written | L4 | + |

T1 to T3 run once per example, so there are 64 test items.

## One command

Run from the repository root. A pass is `994 passed, 1 xfailed` (930 before this slice plus 64), with no
new skip. The expected failure is TD-23.

```bash
mise run check:persistence
```

## Adversarial probes

Run on 2026-10-10, each restored afterwards.

| Mutation | Result |
|---|---|
| the compiler put back to its previous text | 61 of the 63 then-existing items fail (T0 and T4 hold) |
| the capability check node given a fresh label again | no item failed at first, since no example compiles with a capability spec. T5b was added and fails under this mutation |
| the reasoning-requirement cells given fresh labels | one item fails |

The second row is a coverage gap the probe found in the first draft of the tests.

## Deliberate non-coverage

- A committed golden compiled profile (above).
- Labels across a change to what a compiled profile contains. A new dimension or operation changes
  the output, as it should.
- Determinism of the generated SPARQL text, which `instantiate` already has tests for.
