<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: ELC, the composition operation

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice ELC
([plan](../plans/improved-ontology-documentation.md#elc-the-composition-operation-2026-10-19)).
**Implements:** OD-D44, OD-D45 and OD-D46, with addenda to
[ADR-A05](../../architecture/decisions/ADR-A05-compatibility-vocabulary.md) and
[ADR-A03](../../architecture/decisions/ADR-A03-condition-taxonomy.md).
**Built autonomously**, at the maintainer's request of 2026-10-19. The decisions taken alone are listed below.

## Invariant

Only an admission profile declares a composition operation (`elg:compositionOperation`, `AllRequired` or
`AnySufficient`). Only a condition that is not a profile declares a match strategy and a wildcard policy. The
shapes report each declared in the wrong place. No graph in the repository names `elg:CompatibilityOperation`,
`elg:compatibilityOperation`, `elg:DimensionConsistent` or `elg:E6`, and every example and test graph conforms.

## What changed

- **Eligibility's README**, and the files it generates:
  - `elg:CompositionOperation` and `elg:compositionOperation` (domain `elg:AdmissionProfile`) replace the old
    terms. `elg:DimensionConsistent` and `elg:E6` are gone.
  - `elg:AdmissionProfile`'s table requires one composition operation and no match strategy or wildcard
    policy. `elg:Condition`'s table keeps only `elg:negated`.
  - Two hand-written shapes in `constraints.ttl`. `elg:SingleConditionMechanismShape` requires a match strategy
    and a wildcard policy of a condition that is not a profile, and `elg:CompositionOnProfileShape` allows a
    composition operation only on a profile.
  - L1 to L3 restated. `AllRequired` and `AnySufficient` gain definitions. E4 and E5's comments name the
    operations.
  - §5.1, §5.2, §5.4, §5.8, §7, §9, §12 and §13 follow, and §5.2 explains conditions and profiles.
- **Every other graph** naming the old terms, rewritten by one script and checked graph to graph, file by file:
  31 example files in Instrument, Eligibility, Wording, the insurance exposure module and Insure-O, four
  conformance cases, one gate case, two Eligibility fixtures and MORK's `Executable.ttl`
  (`exe:usesCompositionOperation`). The same rule was applied to Turtle inside nine Python test modules.
- **Instrument's `product-warranty.ttl`.** `ex:misuse-not-defect` composes two conditions but was typed
  `elg:Condition`. It is now an `elg:AdmissionProfile`, which the new shapes required.
- **The compilers.** They read `elg:compositionOperation` and write `exe:usesCompositionOperation`. A
  composition operation they cannot evaluate, for example one a downstream ontology adds, is still refused
  with `exe:RefusedOperation`, whose comment no longer names `DimensionConsistent`.
- **The migration check** escapes line breaks in a difference, so a changed SPARQL literal is one line of a
  reconciliation file. Before, a difference in a multi-line literal could not be reconciled.
- **Docs.** ADR-A05 and ADR-A03 addenda, the glossary, `docs/book.html`'s sample, the MORK compilers README and
  the Surface-MORK plan's Phase 5 (§9.3 of the MORK enhancements analysis recorded the retirement). ADR-A89 and ADR-A90 still say
  `DimensionConsistent` is refused, which was true when they were decided, and are left as records.
- **TD-55**, the migration check's whole-file blank node labelling.

## Decisions taken alone, for the maintainer

1. **`elg:compositionOperation`'s domain is `elg:AdmissionProfile`.** It restates what
   `elg:CompositionOnProfileShape` checks. A reasoner would infer that a condition carrying it is a profile, so
   the shape, read without a reasoner, is what reports a misplaced one.
2. **The non-profile rule is a hand-written `sh:or`** (a profile, or one match strategy and one wildcard
   policy), since the restriction table cannot target "a condition that is not a profile". Its message sits on
   the node shape, since the `sh:or` members are anonymous.
3. **`exe:RefusedOperation` stays**, for an operation a downstream ontology adds. Its test now uses such an
   operation in place of `DimensionConsistent`.
4. **`AllRequired` and `AnySufficient` gain definitions**, the strong Kleene readings ADR-A89 states. Eleven
   individuals still have none (README §13).
5. **The warranty carve-back is typed a profile**, which makes it versioned (`fnd:Versioned`), as every profile
   is. Nothing else in that example changed.
6. **The reconciliations are against `82fc2b25`**, the commit before ELC. OD6's command against `dab1c790`
   with OD6's file no longer passes on this branch, since ELC changed the graphs after it. It passed at
   `a177bda7`.

## Tests changed, for countersigning

| Test | Change | Why |
|---|---|---|
| C9b0-04, `bare-condition` probe in `tools/test_eligibility_examples.py` | owned by `elg:SingleConditionMechanismShape`, one violation in place of three | the three per-property rows moved off `elg:ConditionShape` |
| `test_dimension_consistent_is_refused`, now `test_an_unknown_composition_operation_is_refused`, in `test_profiles.py` | an unknown operation in place of `DimensionConsistent` | the individual is retired, and the refusal still holds |
| Turtle inside nine test modules | single conditions lose `compositionOperation`, profiles lose `matchStrategy` and `wildcardSemantics` | the data the tests build must conform |

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| ELC-T1 | a SPARQL literal changed in one line of three / `differences()` / two differences, each on one line | L1 | + |
| ELC-T2 | a condition that is not a profile declaring a composition operation / validate / one violation from `elg:CompositionOnProfileShape` | L3 | − |
| ELC-T3 | a profile declaring a match strategy and a wildcard policy / validate / two violations from `elg:AdmissionProfileShape` | L3 | − |
| ELC-T4 | a bare condition / validate / one violation from `elg:SingleConditionMechanismShape` | L3 | − |
| ELC-T5 | every example in the repository / validate against every layer's shapes / no violation | L4 | + |
| ELC-T6 | Eligibility's generated files / the migration check against `82fc2b25` with the reconciliations / passes | L5 | + |

ELC-T2 to ELC-T4 are probes of `test_moved_shape_fires_once_on_its_probe`. ELC-T5 is the existing example tests
of Eligibility, Instrument, Wording and the exposure module.

## Commands

Run from the repository root. A pass is each exiting 0, except the sweep, which reports only OD-D43's
unbumped files.

```bash
mise run check:literate-migration -- eligibility 82fc2b25 --reconciliations docs/developer/validation/ELC-reconciliations.txt
```

```bash
mise exec -- python -m pytest tools/test_eligibility_examples.py tools/test_closures.py tools/test_literate_migration_check.py tools/test_instrument.py tools/test_parameter_bindings.py tools/test_regimes.py -q
```

```bash
mise run check:full-sweep
```

## Results

2026-10-19, run while building, from this worktree:

- **ELC-T6:** passes, 126 reconciled differences.
- **`check:mork-compilers`:** 126 passed. **`check:reference-eligibility`:** 60 passed.
- **Fourteen layer suites** (Eligibility, closures, Instrument and its parts, extraction, catalogue, exposure,
  Wording): 693 passed after the warranty fix. **The migration check's tests:** 3 passed.
- **`mise run check:full-sweep`:** 13 of 14 checks pass, among them `check:ontology-catalog`, `check:persistence`, `check:mork-compilers` and `check:formal-freshness`. The ontology versions check reports exactly OD-D43's unbumped files, now Eligibility's spec, vocab and shapes and MORK's `Executable.ttl`.

## Deliberate non-coverage

- Versions. OD-REL releases ELC's breaking change with the migration (OD-D43).
- A reasoner run over the new domain. The reasoning tests run in the sweep where the reasoner jar is built.

## Decisions answered

2026-10-19, by the maintainer: all six decisions taken alone ratified and approved, and the changed tests
accepted.
