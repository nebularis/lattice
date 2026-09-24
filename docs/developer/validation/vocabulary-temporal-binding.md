<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack - `vocabulary-temporal-binding`

**Status:** Draft for human review. This pack defines implementation acceptance
criteria. It is not evidence of a passing implementation.
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

To be finalised when the resolver package and task entry point are selected.
The planned command is `mise run check:vocabulary` from the repository root.

## Expected artefacts

- SHACL report for every positive and negative fixture.
- Resolver decision trace naming candidate bindings, matching scopes, temporal
  result, precedence comparison, and final outcome or conflict.
- Determinism result for permuted triple order.
- Cross-layer provenance fixture showing `resolvedUnder` retained.
- Traceability rows linking VTB-01 through VTB-14 to ADR-A85 and the sketch
  invariants.

## Deliberate non-coverage

No live RDF store, fuzzy concept resolution, scope-membership derivation,
concept-level version alignment, or backend-specific runtime behaviour is tested.

## Human mutation probe

Disable the strict-superset comparison in the resolver and rerun VTB-06. The
specific binding must no longer be accepted as the selected result. Retarget or
disable the equal-specificity SHACL-SPARQL constraint and rerun VTB-07. The
fixture must become conformant only when that constraint is genuinely inactive.
