<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack - `vocabulary-temporal-binding`

**Status:** Test cases authored against a full implementation (`ontology/vocabulary/shapes/`,
`ontology/vocabulary/examples/`, `tools/vocabulary/`). Not yet executed in this
sandbox (no dependency-install access) and not yet human-reviewed. This pack
is not evidence of a passing implementation.
**Plan:** [vocabulary-temporal-fixes.md](../plans/vocabulary-temporal-fixes.md)
**Status:** [vocabulary-temporal-binding.md](../status/vocabulary-temporal-binding.md)

## Invariant

For one scheme contract, resolution is deterministic and explicit. A binding is
eligible only when its scopes and temporal validity match the supplied context.
A strict scope superset wins. Equal-specificity conflicts are rejected, and a
fallback is used only when no applicable binding exists. Historical records keep
the binding used at resolution time. Structural and SHACL validation must reject
incomplete or contradictory graphs without turning the open-world ontology into a
silent chooser.

## Test cases

| ID | Given / When / Then | Level | Pass criterion | +/- |
|---|---|---|---|---|
| VTB-01 | Given a complete binding, when structural validation runs, then it conforms | L3 | Positive fixture conforms | + |
| VTB-02 | Given a binding without `forContract`, when validation runs, then it fails | L3 | Named shape violation | - |
| VTB-03 | Given a binding without `bindsScheme`, when validation runs, then it fails | L3 | Named shape violation | - |
| VTB-04 | Given an invalid temporal interval, when validation runs, then it fails | L3 | `validTo` precedes `validFrom` is rejected | - |
| VTB-05 | Given two scopes on one binding, when context matching runs, then both scopes are required | L1 | Partial context does not match | + |
| VTB-06 | Given a more specific applicable binding, when resolving, then it wins over the strict subset | L1 | Specific scheme selected | + |
| VTB-07 | Given equal-specificity applicable bindings, when resolving, then resolution fails | L1 | Conflict error, no selected scheme | - |
| VTB-08 | Given no applicable scoped binding and a fallback, when resolving, then fallback is selected | L1 | `boundScheme` selected | + |
| VTB-09 | Given a scopeless binding disagreeing with `boundScheme`, when validating, then it fails | L3 | Fallback agreement violation | - |
| VTB-10 | Given an open-ended binding, when resolving after its start, then it remains eligible | L1 | Binding selected | + |
| VTB-11 | Given the same graph in permuted triple order, when resolving, then the result is identical | L2 | Stable result and digest | + |
| VTB-12 | Given a historical record with `resolvedUnder`, when current bindings change, then the recorded binding remains unchanged | L3 | No retroactive re-resolution | + |
| VTB-13 | Given a historical record whose binding is outside its recorded time, when validating, then it fails | L3 | Provenance-time violation | - |
| VTB-14 | Given a consumer concept-valued property, when the consumer resolves its contract, then it uses the selected binding before the scheme | L4 | Cross-layer fixture passes | + |

## One command to run everything

```bash
mise run bootstrap:vocabulary
mise run check:vocabulary
```

Equivalently, without `mise`: `python -m pip install -e ./tools/vocabulary[test]`
then `python -m pytest tools/vocabulary/tests -q`. VTB-01 through 04, 07 (the
context-independent form), 09, and 13 run in `test_shacl_fixtures.py`; VTB-05,
06, 07 (the context-dependent form), 08, and 10 in `test_resolver.py`; VTB-11
in `test_determinism.py`; VTB-12 and 14 in `test_consumer_boundary.py`.

## Expected artefacts

- The pytest run's own output: SHACL `pyshacl.validate` reports embedded in
  `test_shacl_fixtures.py`'s assertion messages for every positive and
  negative fixture on failure (pyshacl's third return value).
- A resolver decision trace for any `Resolution`: `Resolution.describe()`
  (`tools/vocabulary/src/vocabulary/model.py`) prints every candidate binding
  considered, its scope match, temporal match, applicability, and the final
  outcome — naming candidate bindings, matching scopes, temporal result, and
  precedence comparison, as required below.
- The determinism result: `test_determinism.py`'s assertions that resolving a
  triple-order-permuted copy of the same graph produces an identical scheme,
  winning binding, and candidate set.
- The cross-layer provenance fixture: `test_consumer_boundary.py` reads
  `ex:consumer-record-42`'s `voc:resolvedUnder` directly out of the graph
  after resolving the same contract at a later time, and asserts it is
  unchanged.
- Traceability rows linking VTB-01 through VTB-14 to ADR-A85 and the sketch
  invariants: see `docs/traceability/matrix.csv`.


## Deliberate non-coverage

No live RDF store, fuzzy concept resolution, scope-membership derivation,
concept-level version alignment, or backend-specific runtime behaviour is tested.

## Human mutation probe

Disable the strict-superset comparison in the resolver and rerun VTB-06. The
specific binding must no longer be accepted as the selected result. Retarget or
disable the equal-specificity SHACL-SPARQL constraint and rerun VTB-07. The
fixture must become conformant only when that constraint is genuinely inactive.
