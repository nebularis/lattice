<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-HO9, documentation and close-out

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice HO9
([plan §3.5](../plans/formal-methods-track-h.md#ho9-documentation-and-close-out)). Documents only.
**Decisions needing confirmation:** accepting ADR-A122, which is the maintainer's.

## Invariant

The documents describe the aggregate model that is built, and say nothing about the model it replaced.

## What changed

- `ontology/persistence/docs/aggregate-boundaries.md` is rewritten from the sketch (§1, §2, §5, §7, §8, §11). It
  explains the three kinds of node, ownership as a property of an edge in its context, the classified shape, the
  delete set, every refusal and the warning, reference data, what the composite strategy generates, graph naming
  and concurrency. It recommends a named graph per aggregate for new deployments. Its examples are domain-neutral
  (projects, milestones, tasks, documents and comments), as substrate documentation must be.
- `ontology/persistence/README.md`: §7.1 says what is in an aggregate, which strategy to prefer and why a shape,
  §9's operation table and §11.3's worked example use the classified shape, and the example list names the larger
  fixture. The composite example file gains a reference edge, `ex:customer`, so the worked example is the file, and `test_boundary.py` asserts that the customer is declared and not owned.
- `tools/persistence/README.md`: the `gaps` subcommand, the owned path and data graph slots, the composite
  limitation entry (rewritten), graph naming, and the new test files.
- `docs/developer/sketches/persistence-profile-substrate.md`: Part 4 now begins with a note that ADR-A122
  supersedes it in part. It is not rewritten.
- `docs/developer/INDEX.md` and the status record: every HO row is closed, with its pack.
- `persistence gaps` over the composite and named-graph examples lists no composite and no graph-naming entry.
  What it still lists is not part of this work: fixed infrastructure graph IRIs, the housekeeping duties, and the
  caller's version row.
- ADR-A122's number was rechecked against `origin/main` and every remote branch. It is the same file on `main`, and no
  other branch has an A121 or A122. `docs/traceability/matrix.csv` names no removed term.

## One command

Run from the repository root.

```bash
mise run check:persistence && mise exec -- python -m pytest spikes/persistence-aggregate-ownership -q
```

A pass is `1356 passed, 1 xfailed` and `18 passed`. `mise run check:full-sweep` runs the other checks.

## Deliberate non-coverage

- That a reader finds the explanation clear. That is the maintainer's reading.
- `docs/developer/notes/persistence-aggregate-ownership.md` and the review stay as the record of how the design
  was reached, and are not rewritten.
- ADR-A122's status. It stays Proposed until the maintainer accepts it with the work package.
