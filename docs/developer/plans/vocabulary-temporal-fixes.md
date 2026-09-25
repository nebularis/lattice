<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Vocabulary scoped and temporal binding conformance

**Unit ID:** `vocabulary-temporal-binding`
**Status:** Closed (2026-09-25). Executed, verified, and ratified (ADR-A85 Accepted). Follow-on hardening items identified during closure review are tracked under a new unit, `temporal-binding-consumer-hardening` (see its plan and status).
**Trigger:** `65ac4a85e11cc1f8616e3e0c24efd59bf4ca410d`
**Sketch:** [vocabulary-temporal-binding.md](../sketches/vocabulary-temporal-binding.md)
**Status record:** [vocabulary-temporal-binding.md](../status/vocabulary-temporal-binding.md)
**Validation pack:** [vocabulary-temporal-binding.md](../validation/vocabulary-temporal-binding.md)

## Problem and corrected scope

Commit `65ac4a85e11cc1f8616e3e0c24efd59bf4ca410d` adds `voc:SchemeBinding`,
`voc:BindingScope`, four binding properties, temporal validity, historical
`voc:resolvedUnder` provenance, and a prose resolution law. The source ontology
change is present, but the repository does not yet contain the conformance
package required by its standards.

This unit therefore covers architecture synchronisation, a proposed ADR,
examples, SHACL and SHACL-SPARQL validation, a deterministic reference
resolver, executable test cases, consumer boundary checks, traceability, and
the validation pack. It is not a documentation-only sync.

## Governing decision

Author [ADR-A85](../../architecture/decisions/ADR-A85-vocabulary-scoped-temporal-binding-resolution.md)
as Proposed for human review. It records the n-ary binding model, conjunctive
scope semantics, strict-superset precedence, conflict refusal, `boundScheme`
fallback, and non-retroactive `resolvedUnder` provenance. No OWL axiom may
silently choose between competing bindings.

## Deliverables

### 1. Architecture and normative documentation

- Update `docs/architecture/ontology-architecture.md` to mirror the Vocabulary
  README. Include the implementation table line count, purpose, design
  decisions, DL encoding, disjointness, property axioms, worked pattern, and
  open validation items.
- Keep root `README.md`, the solution design, data architecture, UX design,
  deferred-scope document, `.github/copilot-instructions.md`, and
  `GENAI_CONTRIBUTION.md` unchanged unless a concrete vocabulary-specific
  contradiction is found and recorded first.
- Do not advance the ontology version IRI without an explicit release decision.

### 2. Examples and validation fixtures

Create `ontology/vocabulary/examples/` with positive and negative fixtures for:

- complete unscoped and time-bounded bindings
- conjunctive multi-scope binding
- alternative regional bindings
- temporal scheme-edition handover
- historical `voc:resolvedUnder` provenance
- missing `forContract` and missing `bindsScheme`
- invalid temporal interval
- equal-specificity overlap conflict
- disagreement between a scopeless binding and `boundScheme`
- historical provenance outside the record's time

Fixtures must remain domain-neutral and declare only the minimum Foundation and
SKOS terms needed for the check.

### 3. SHACL and structural validation

Populate the existing empty files under `ontology/vocabulary/shapes/`:

- `structural.ttl` for reusable node shapes and cardinality/type constraints
- `constraints.ttl` for temporal sanity, fallback agreement, conflict, and
  historical provenance constraints
- `rules.ttl` only where a non-selecting validation rule is necessary

Context and resolution time must be represented explicitly in the validation
profile. SHACL must report an ambiguity or contradiction, never select a
winner. Add both conforming and non-conforming assertions to the test suite.

### 4. Reference resolution and executable tests

Add a small reference resolver in the repository's established Python tooling
boundary, subject to confirmation of the exact package location. Test:

- all named scopes are required, while no scope means all contexts
- closed and open-ended temporal intervals
- strict-superset precedence
- equal-specificity conflict refusal
- fallback only when no applicable binding exists
- scopeless binding agreement with `boundScheme`
- deterministic output under triple-order permutation
- historical `resolvedUnder` preservation without re-resolution

The resolver is a conformance implementation of the Vocabulary law. It is not a
fuzzy matcher, scope-membership engine, live-store adapter, or general runtime.

### 5. Consumer and provenance boundary checks

Add the narrowest useful cross-layer fixtures or contract tests, with the
consumer selected during human review. The check must demonstrate that a
consumer resolves the applicable binding before interpreting a concept-valued
property, preserves existing unscoped `boundScheme` behaviour, and retains a
historical `resolvedUnder` assertion. Do not expand this unit into a Surface or
Eligibility semantic redesign.

### 6. Governance records

- Keep the sketch, plan, status record, ADR index, developer index, and
  validation pack cross-linked.
- Add traceability rows for ADR-A85 and all validation cases.
- Update the status record after every material implementation or validation
  action.

## Slice plan

| Slice | Scope | Test level | Gate |
|---|---|---|---|
| 1 | ADR-A85, architecture mirror, fixture and traceability skeleton | L0, L2 | Human review of semantic parity and decision record |
| 2 | Examples plus structural and SHACL-SPARQL validation | L1, L3, L4 | Positive and negative fixtures produce expected reports |
| 3 | Reference resolver and deterministic test suite | L1, L2 | Precedence and conflict mutation probes fail as intended |
| 4 | Consumer/provenance checks and documentation close-out | L3, L4 | Cross-layer contract passes and validation pack is complete |

Each slice should touch no more than two implementation modules. Split a slice
if the resolver, SHACL package, or consumer check exceeds that boundary. No
implementation slice starts until this plan, ADR-A85, and the validation
context are approved.

## Acceptance and validation

The single command is to be finalised with the resolver package location. The
planned entry point is:

```text
mise run check:vocabulary
```

The validation pack requires SHACL reports, resolver decision traces, a
triple-order determinism result, a historical provenance fixture, traceability
rows, and a human mutation probe that disables strict-superset precedence or
the equal-specificity constraint and observes the expected test failure.

## Deliberate non-coverage

- fuzzy label or natural-language concept resolution
- concept-level version alignment or deprecated-concept policy
- scope-membership derivation
- live stores, runtime scheduling, and backend-specific behaviour
- silent conflict resolution or OWL encoding of whole-graph precedence
- ontology version release mechanics

## Checked documents with no planned change

The root README, solution design specification, data architecture, UX design,
deferred-scope document, `.github/copilot-instructions.md`, and
`GENAI_CONTRIBUTION.md` were checked. They contain no Vocabulary-specific
mechanism inventory that this unit must synchronise. This remains an explicit
assumption for human review, not a claim that the files are permanently out of
scope.

## Closure (2026-09-25)

All four slices executed and verified: `mise run check:vocabulary` (14/14),
`python -m unittest surface.test_surface -q` (62/62), `mise run
check:python-root` (77/77 plus Phase 8 conformance). ADR-A85 is Accepted. A
subsequent cross-reference of this work against
[docs/architecture/rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md)
found the implementation internally consistent, with four follow-on hardening
items and one accepted non-issue, none of which block this unit's closure.
Those items are scoped under the new `temporal-binding-consumer-hardening`
unit: [plan](temporal-binding-consumer-hardening.md),
[status](../status/temporal-binding-consumer-hardening.md).
