<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H1.4b, the declaration/implementation gap report

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H1.4b, the second half
of [plan §3, H1.4](../plans/formal-methods-track-h.md), as redefined in the plan's section "H1.4b and
H1.5 after the aggregate-ownership review".
**Source finding:** the main sketch's L6 gap, and the review's findings F1, F2, F4 and F10.
**Decisions needing confirmation:** the shape of the report, below. Nothing blocks.

## Invariant

A configuration can declare more than the generated SPARQL implements, and nothing said so. After this
slice, `persistence gaps` lists each such gap per target, with whose obligation it is and the register
row and slice that remove it, so a reader of a compiled profile is not told a dimension is honoured
when it is not.

## What was built

`persistence/gaps.py`, a `gaps` subcommand (text, and `--json`), and `tests/test_gaps.py`. Eleven rules,
each a function over one compiled target, kept in `persistence.gaps.RULES`.

| Rule | Obligation | Reference | Closes in |
|---|---|---|---|
| `CompositeOwnershipAssumed` | unimplemented | TD-35 | HO5 |
| `CompositeInversePathMisread` | unimplemented | TD-37 | HO5 |
| `CompositeUsesDefaultGraph` | unimplemented | TD-40 | HO5 |
| `CompositeNoLifecycleOperations` | unimplemented | TD-04 | HO7 |
| `NamedGraphNamedFromLocalName` | unimplemented | TD-38 | HO8 |
| `UnconditionalWriteNamedGraphOnly` | unimplemented | TD-02 | not planned |
| `ShardCountNotHonoured` | unimplemented | TD-06 | not planned |
| `InfrastructureGraphsFixed` | unimplemented | TD-05 | not planned |
| `RetentionAndEpochBumpNotGenerated` | housekeeping | ADR-A80 | not planned |
| `RestoreRunbookBindingsUnread` | housekeeping | TD-08 | not planned |
| `VersionRowCreatedByCaller` | caller | README obligation 1 | not planned |

The composite entries are the ones the plan lists, except two it said to omit after HO1: the payload in
the log graph (TD-39) and the quadratic sweep (TD-36). Those are closed.

## Choices made, for the maintainer

- **A separate subcommand, `gaps`, and not part of `compile` or `hygiene`.** The plan says "generated per
  compile". The report needs compiled targets and never fails a compile, and `hygiene` fails on
  violations, which a gap is not. If you want it on the compile output as well, it is one call to
  `find_gaps`.
- **Informational.** It exits 0 once the configuration compiles. A gap is a fact about the tool, not
  about the configuration.
- **Declared-but-ignored dimensions are limited to those with a rule.** The plan's examples were shard
  counts, infrastructure graph IRIs, housekeeping duties and the composite binding, and each has a rule.
  Others can be added as rules.
- **The register rows are cited, not read.** A row removed from the register without its rule removed
  here goes unnoticed. Each closing slice removes both (the plan says so).

## Test cases

In `tools/persistence/tests/test_gaps.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| H1.4b-T1 | the shipped composite example / report / the three composite gaps and the two every-target gaps, the first naming the shape (`OrderAggregateShape`) and the property (`lineItem`) | L4 | + |
| H1.4b-T2 | the baseline named-graph example / report / the graph-naming gap and no composite gap | L4 | + |
| H1.4b-T3 | a graph template with text after `{id}` / report / the text is named as dropped | L3 | + |
| H1.4b-T4 | a composite shape with an `sh:inversePath` property / report / `CompositeInversePathMisread` | L3 | + |
| H1.4b-T5 | `dal:txnShards 4` / report / `ShardCountNotHonoured` | L3 | + |
| H1.4b-T6 | `ProvidedConcurrency` on a no-boundary target / report / `UnconditionalWriteNamedGraphOnly` | L3 | + |
| H1.4b-T7 | an append stream, an identity and epoch profile, a baseline / report / the caller and housekeeping entries | L4 | + |
| H1.4b-T8 | the fixtures above / union of the rules fired / every rule in `RULES` | L2 | + |
| H1.4b-T9 | a graph and the same graph with its triples reordered / report / identical and sorted | L2 | + |
| H1.4b-T10 | the composite example / CLI, text and `--json` / the entries and the data fields | L5 | + |
| H1.4b-T11 | a configuration that does not compile / CLI / exit 1 and a message | L5 | − |

## One command

Run from the repository root. A pass is `930 passed, 1 xfailed` (917 before the slice plus 13 test
items), with no new skip. The expected failure is TD-23.

```bash
mise run check:persistence
```

To see the report on the composite example:

```bash
mise exec -- python -m persistence gaps ontology/persistence/spec/persistence.ttl ontology/persistence/examples/composite-property-boundary-shacl.ttl
```

## Adversarial probes

Run on 2026-10-10, each restored afterwards.

| Mutation | Result |
|---|---|
| the `CompositeOwnershipAssumed` rule removed from `RULES` | T1 and T10 fail |
| the rule's condition made always false | T1, T8 and T10 fail |
| the dropped-suffix text removed from the graph-naming message | T3 fails |

## Deliberate non-coverage

- A gap rule is not checked against the register, so a rule can outlive its row.
- Gaps in the SPARQL that no declaration mentions. That is the audit and witness work of H1.2 and H9.
- Entries for slices that change the output. HO5, HO7 and HO8 remove their rules and expectations in
  the same commit as the change.
