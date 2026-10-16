<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H1.2, witness coverage (harness and audits)

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H1.2, part a
([plan §3, H1.2](../plans/formal-methods-track-h.md))
**Source finding:** [review](../notes/rdf-engine/persistence-fml.md) §7.4 and the calibration defects
D.3 A6 (a shape that could never fire) and D.1 (a constraint that silently targeted nothing).
**Decisions:** none ratified. The split of H1.2 into a, b and c is recorded in the status record as
H-D8, and the rule inventory's source as H-D9.

## Scope of this slice

H1.2 as the plan words it covers four families of rule, and the first run found 55 of 83 without a
witness. Closing all of them in one slice would break the slice-sizing rule, so H1.2 is delivered in
three parts.

| Part | Delivers |
|---|---|
| H1.2a (this slice) | the harness and its report, the witnesses for all five audits, and `known-gaps.txt` recording the measured starting state |
| H1.2b | witness fixtures for the 24 unwitnessed refusals and 8 warnings. Six refusals are named by no test, so each must be triggered or reported unreachable |
| H1.2c | witness fixtures for the 23 unwitnessed shapes |

## Invariant

Every rule that can refuse or warn, every SHACL shape and every always-on audit query has at least
one fixture that **triggers** it, or is listed with a reason in
`tools/persistence/tests/witnesses/known-gaps.txt`. A rule that is neither is a failure, and so is a
listed gap that has since gained a witness, so the list can only shrink. An audit counts as
witnessed only when a violating dataset makes it return rows **and** a clean dataset makes it
return none, since a query that always fires detects nothing. The inventory is read from the
package's own source and shapes, so a new rule cannot be added without a witness or a gap entry.

## Test cases

All in `tools/persistence/tests/test_witness_coverage.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| H1.2-T1 | the real package / enumerate / refusals (both `kind` and class-named), warnings (both call styles), shapes and 5 audits are all present | L1 | + |
| H1.2-T2 | a source file containing a new `CrossAxisViolation`, `_warning` and `BoundaryConflict` / enumerate / all three join the inventory | L1 | + |
| H1.2-T3 | a rule with no witness and no gap entry / report / uncovered, not ok, named in the output | L1 | − |
| H1.2-T4 | a deliberately vacuous refusal seeded into the real inventory / report against the real observation / reported uncovered | L2 | − |
| H1.2-T5 | a listed gap that has a witness / report / stale, not ok | L1 | − |
| H1.2-T6 | a listed gap naming no rule / report / unknown, not ok | L1 | − |
| H1.2-T7 | a listed gap with no witness / report / ok, and shown as a gap | L1 | + |
| H1.2-T8 | two shipped examples / compile / the refusal and the warning they raise are witnessed | L4 | + |
| H1.2-T9 | a shipped refusal example / validate against the shapes / the shape that fires is witnessed | L4 | + |
| H1.2-T10 | a property shape (a blank node) / resolve its owner / credited to the named parent | L1 | + |
| H1.2-T11 | each of the 5 audits / run its violating and clean dataset / at least one row, and none (one test per audit) | L4 | +/− |
| H1.2-T12 | an audit with only a violating dataset / observe / not witnessed, and a problem reported | L1 | − |
| H1.2-T13 | an audit whose "clean" dataset is really a violating one / observe / not witnessed, and a problem reported | L1 | − |
| H1.2-T14 | an audit slot with no `# bind:` line / run / refused, naming `logGraphs` | L1 | − |
| H1.2-T15 | the real corpus / full check / no unlisted gap, no stale gap, no unknown gap | L4 | + |
| H1.2-T16 | the real corpus, then with the gap list emptied / `witness` CLI / exit 0, then exit 1 naming `UNWITNESSED` | L3 | +/− |

## One command

Run from the repository root. A pass is `842 passed` with no failures (the 822 from before H1.2,
plus 20 here).

```bash
mise run check:persistence
```

The harness is also available directly, and `--verbose` lists every witnessed rule with its fixture
and every known gap with its reason. It exits 1 on any failure.

```bash
mise exec -- python -m persistence witness --verbose
```

At this slice it prints `witness coverage: 28 of 83 rule(s) witnessed, 55 listed gap(s), 0 unlisted gap(s)`,
with `refusal 10/34`, `warning 3/11`, `shape 10/33` and `audit 5/5`.

## Adversarial probes

Run on 2026-10-09, each reverted afterwards.

| Mutation | Result |
|---|---|
| `fork-detection-audit` threshold `> 1` changed to `> 2`, so a two-way fork is missed | T11 (fork), T15 and T16 fail. T13 also fails, because it borrows the violating dataset |
| `key-claim-duplicate-audit` loses its `HAVING`, so it fires on good data | T11 (key claim), T15 and T16 fail |
| `gap-scan-audit` stops reading the retention low-water mark | T11 (gap scan), T15 and T16 fail |
| the `LagWindowMissing` check made unreachable in `validator.py` | the CLI prints `UNWITNESSED refusal:LagWindowMissing` and exits 1 |
| the `WeakEtagCas` entry removed from `known-gaps.txt` | the CLI prints `UNWITNESSED warning:WeakEtagCas` and exits 1 |

One probe did not detect a change, correctly. Renaming a refusal consistently in the validator keeps
it witnessed, because the inventory and the observation both follow the new name. The maintainer is
invited to pick another mutation, for example swapping the violating and clean datasets of one audit.

## Artefacts to inspect

- `tools/persistence/src/persistence/witness.py`, the harness (the inventory, the three observers
  and the report).
- `tools/persistence/tests/witnesses/audits/`, ten small TriG datasets. The `# bind:` lines fill the
  audit's request-time slot, `logGraphs`.
- `tools/persistence/tests/witnesses/known-gaps.txt`, the measured starting state. Six refusals read
  "named by no test, so possibly unreachable".
- `python -m persistence witness --verbose`, to see which example witnesses each rule.

## Deliberate non-coverage

- The 24 refusals, 8 warnings and 23 shapes listed as gaps. Parts H1.2b and H1.2c.
- Whether each audit detects what the **write** operations produce. The witnesses use graph IRIs and
  predicates the compiler binds today, but the datasets are hand-written. Checking that the templates
  that write receipts and claims produce data these audits can see belongs with the detection work in
  H9.
- `SparqlTermError` and the identity digest `ValueError`, which are input-encoding failures covered by
  the injection corpus and are not compile-time rules.
- Mutation testing of the compiler. Review §16.2, later.
