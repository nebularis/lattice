<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H1.4c, a declaration the compiler cannot honour is not a gap

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), a follow-up to H1.4b
([FMH-H1-4b](FMH-H1-4b.md)), decided with the maintainer on 2026-10-10 (option C of the question whether
`compile` should fail on gaps).
**Decisions needing confirmation:** one, below.

## Invariant

A configuration that asks for something the compiler cannot honour never produces a profile that quietly drops
it. It is a compile warning or a refusal. The gap report lists only what is true of nearly every configuration,
so it is never a gate.

## What changed

- The gap rule `UnconditionalWriteNamedGraphOnly` is replaced by the refusal `UnconditionalWriteRequiresNamedGraph`
  (TD-02). Provided or locking concurrency, outside event grain, with a boundary that is not a named graph, used to
  compile and then fail to render at instantiate. It is now refused by `compile`. The check runs last among the
  cross-axis rows, so a fixture written to isolate another row still reaches that row first.
- The gap rule `ShardCountNotHonoured` is removed. It duplicated the existing compile warning `ShardingNotHonoured`.
- `RestoreRunbookBindingsUnread` stays, now read as a housekeeping obligation. Those bindings describe a restore
  runbook that housekeeping reads (ADR-A80), so they are not ignored, and a warning on them would be noise for a
  legitimate declaration.
- Seven gap rules become four: `InfrastructureGraphsFixed`, `RetentionAndEpochBumpNotGenerated`,
  `RestoreRunbookBindingsUnread` and `VersionRowCreatedByCaller`. The module docstring and the README say why
  the report is informational.
- A witness, `refusal-UnconditionalWriteRequiresNamedGraph.ttl` (99 of 99). TD-02 is reworded: such a target is
  refused, and still cannot be declared.

## Decision for the maintainer

We did not turn `ShardingNotHonoured` into a refusal. It is a loud warning today and no shipped example trips it.
Making it a refusal is one line in `validator.py`, and we can do it if you want a declared shard count to stop the
compile.

## Test cases

In `tools/persistence/tests/test_unconditional_write.py` and `test_gaps.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| TD02-T1 | provided or locking concurrency with no boundary / compile / `UnconditionalWriteRequiresNamedGraph` naming the boundary | L3 | − |
| TD02-T2 | the same with a named-graph boundary / compile / the `unconditional-write` operation | L3 | + |
| TD02-T3 | optimistic concurrency / compile / not affected | L3 | + |
| TD02-T4 | the witness / the witness check / triggers exactly this refusal | L4 | + |
| H1.4b-T12 | the rule list / names / no rule for a shard count or an unconditional write | L1 | + |

## One command

Run from the repository root. In a checkout whose `.venv` is new, run `mise run bootstrap` first. A pass is
`1360 passed, 1 xfailed`.

```bash
mise run check:persistence
```

## Adversarial probe

Run on 2026-10-10, restored afterwards.

| Mutation | Result |
|---|---|
| the new refusal moved to the first cross-axis row | the receipt-only and uniqueness negative fixtures raise it instead of their own rows, and four items fail. That is why it runs last |

## Deliberate non-coverage

- A gate over the standing gaps. Every one holds for nearly every configuration, so a gate would always be red.
- A second variant of `unconditional-write` for composite or no boundary (TD-02).
