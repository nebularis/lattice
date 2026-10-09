<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H1.2b, witnesses for every refusal and warning

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H1.2, part b
([plan §3, H1.2](../plans/formal-methods-track-h.md), split by H-D8)
**Builds on:** [FMH-H1.2a](FMH-H1-2.md), the harness and the audit witnesses.
**Decisions:** none new. The patch fixture format is described below for the human to confirm.

## Invariant

Every refusal and every warning the compiler can emit has a fixture that triggers it, and each
fixture triggers the rule it is named for and no other. The 13 shapes still unwitnessed are the
subject of H1.2c.

## What changed

- **33 witness fixtures** (25 refusals and 8 warnings) and one shared base, in
  `tools/persistence/tests/witnesses/`, named `refusal-<Kind>.ttl` and `warning-<Kind>.ttl`. The
  shipped examples already witnessed 11 refusals and 3 warnings, so together they cover all 36
  refusals and all 11 warnings.
- **A patch format for fixtures.** A witness may name a shipped example as its base, remove triples
  from it and add its own, so it is a small difference from the example and follows the example when
  it changes. A `remove:` that matches nothing is an error, so a patch cannot quietly do nothing.
  Files whose name starts with `_` are shared bases, not witnesses.
- **A drift check.** A file called `refusal-X.ttl` or `warning-X.ttl` must trigger `X`. If an earlier
  check starts refusing it first, the harness reports what it triggers instead.
- **A correction to the H1.2a harness.** The rule inventory missed two refusals, `KeyConstraintRequired`
  and `ClaimedIdentityWithoutKey`, because the recipe builder passes a kind to a helper
  (`self.constraint(..., "KeyConstraintRequired")`) that hands it to `fail` as a variable. The scan now
  follows a kind parameter back to the constants passed at its call sites, and a kind it cannot
  determine is reported as a problem and never skipped. The inventory grew from 83 to 85 rules.

## Measured result

| Family | Before (H1.2a) | After |
|---|---|---|
| Refusals | 10 of 34 | **36 of 36** |
| Warnings | 3 of 11 | **11 of 11** |
| Shapes | 10 of 33 | 20 of 33 (a side effect, the new fixtures also trip their mirror shapes) |
| Audits | 5 of 5 | 5 of 5 |
| Total | 28 of 83 | **72 of 85** |

Vacancy closed: 42 of the 55 starting gaps, plus the two the corrected inventory added. The six
refusals no test named (`BoundaryConflict`, `CapabilityCheckFailed`, `IdentityStrategyUnsupported`,
`KeyPropertiesRequired`, `MissingBoundaryShapeError`, `UnsupportedUnicodeVersion`) are all reachable,
so none is dead code. `IdentityStrategyUnsupported` is reachable only with a strategy IRI the
ontology does not declare, so it is a defensive check against invalid input.

## Test cases

All in `tools/persistence/tests/test_witness_coverage.py`, continuing from H1.2a's T1 to T16.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| H1.2-T17 | a helper that passes a kind to `fail` via a parameter, positionally and by keyword / scan / both kinds found | L1 | + |
| H1.2-T18 | a kind taken from a dictionary lookup / scan / reported as a problem with its line, not skipped | L1 | − |
| H1.2-T19 | the real source / scan / no undeterminable kind, and the two previously missed refusals present | L4 | + |
| H1.2-T20 | a fixture with `base:` and `remove:` / load / the triple is gone, the added triples are present | L1 | + |
| H1.2-T21 | a `remove:` that matches nothing / load / refused, naming the line | L1 | − |
| H1.2-T22 | a `refusal-X.ttl` that triggers a different rule, and a `_base` file / drift check / one problem, the base ignored | L1 | − |
| H1.2-T23 | the real corpus / full check / ok, only shapes remain as gaps, and `MixedReceiptModel` and `IdentityStrategyUnsupported` are covered | L4 | + |

## One command

Run from the repository root. A pass is `849 passed` with no failures (842 after H1.2a, plus 7).
The run takes about 45 seconds, 19 of them shape validation, which pyshacl performs against the
whole spec for each of the 65 fixtures.

```bash
mise run check:persistence
```

`mise exec -- python -m persistence witness --verbose` prints, for every rule, the fixtures that
witness it. It exits 0 and shows `72 of 85 rule(s) witnessed, 13 listed gap(s), 0 unlisted gap(s)`.

## Adversarial probes

Run by the agent on 2026-10-09, each reverted afterwards.

| Mutation | Result |
|---|---|
| the `UniquenessWitnessRequired` check made unreachable | `UNWITNESSED refusal:UniquenessWitnessRequired`, and the drift check reports that its fixture now triggers `MintedIriTemplateRequired`. Exit 1 |
| a shipped base example drifts (`ex:PolicyIdentity` renamed) | `FIXTURE ERROR refusal-KeyConstraintNotApplicable.ttl: 'remove: ...' matches nothing in the base`. Exit 1 |
| one refusal's kind made opaque to the scan (`str("...")`) | `PROBLEM validator.py:48: cannot determine the kind passed to CrossAxisViolation()`. Exit 1 |
| the `KeyPropertiesRequired` witness patched to remove the wrong triple | `UNWITNESSED refusal:KeyPropertiesRequired` and a drift problem naming `NormalizePipelineRequired`. Exit 1 |

## Findings

- **TD-23** (technical debt register). A class named only by a graph-pattern scope's `dal:coversClass`
  is never compiled, because target discovery reads `dal:targetClass` alone. The README says such a
  scope covers those classes. The shipped `warning-mixed-receipt-model.ttl` therefore compiles only
  `Gadget`, and its `MixedReceiptModel` warning cannot leave `compile`. The existing test hides this by
  passing `classes=` explicitly. The new witness adds the missing `dal:targetClass` scope for `Widget`.
- **TD-24.** `persistence compile` advises `--target-class` when it finds no target, but there is
  no such option.
- `RowLevelGuardOnly` is a baseline default warning and appears on 24 of the 65 fixtures. That is by design, but a reader scanning diagnostics will learn to ignore it.
- The first drift-free state exposed that `examples/invalid-compositeboundary-missing-shape.ttl` does
  not witness `MissingBoundaryShapeError` (TD-10 already records this). A new witness does.

## Artefacts to inspect

- `tools/persistence/tests/witnesses/*.ttl`, 34 small files. Start with `refusal-KeyPropertiesRequired.ttl`
  (a one-line patch), `warning-MixedReceiptModel.ttl` (the TD-23 case) and `_base-thing.ttl`.
- `tools/persistence/src/persistence/witness.py`: `scan_source`, `_load_fixture`, `named_witness_problems`.
- `python -m persistence witness --verbose`.

## Deliberate non-coverage

- The 13 unwitnessed shapes. H1.2c.
- That each refusal's **message** is correct or that its trigger is the *minimal* cause. A witness
  shows the rule can fire, not that it fires for the right reason in every case.
- That the compile-time refusals and their mirror SHACL shapes agree. A rule that refuses without its
  shape firing, or the reverse, is the shape/compiler disagreement review §7.3 calls V2. H1.2c lists
  the cases it sees, and H4 checks them exhaustively.
- Mutation testing of the compiler (review §16.2).
