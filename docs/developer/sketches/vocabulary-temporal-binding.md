<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Vocabulary Temporal Binding - Design Sketch

**Unit ID:** `vocabulary-temporal-binding`
**Status:** Design sketch for human review. No implementation is claimed.
**Trigger:** commit `65ac4a85e11cc1f8616e3e0c24efd59bf4ca410d` (`[vocabulary] time-bound binding`)
**Source of truth:** `ontology/vocabulary/README.md` and the extracted `spec/vocabulary.ttl`.

## Problem

Vocabulary now supports more than one permanently unscoped scheme per contract. A
`voc:SchemeBinding` reifies the relationship between a `voc:SchemeContract` and a
specific `voc:ConceptScheme` edition. A binding is temporally scoped through
`fnd:TemporallyScoped`, may apply in one or more opaque `voc:BindingScope`
contexts, and can be recorded on a versioned record with `voc:resolvedUnder`.

The ontology states the resolution law in prose but the repository does not yet
provide the artefacts needed to make that law reviewable or executable. In
particular, there are no vocabulary examples, SHACL constraints, resolution
fixtures, executable tests, or cross-layer provenance checks.

## Invariants to protect

1. A binding names exactly one contract and one scheme edition.
2. Multiple `voc:bindingScope` values are conjunctive. Separate binding nodes
   express alternatives. No scope means all contexts.
3. A binding is applicable only when every named scope holds and its temporal
   scope contains the resolution time.
4. Among applicable bindings for one contract, a strict superset of scopes wins.
   Equal-specificity survivors are a conflict and must never be selected
   silently.
5. If no scoped or time-applicable binding wins, `voc:boundScheme` is the
   unscoped fallback where present.
6. A scopeless binding and `voc:boundScheme` for the same contract must name the
   same scheme.
7. `voc:resolvedUnder` preserves the binding that gave historical concept values
   their meaning. It must not be re-resolved against today's bindings.
8. The mechanism remains domain-neutral. Scope membership, fuzzy label
   resolution, and concept-level version alignment remain outside Vocabulary.

## Proposed deliverables

### Normative documentation and decision record

- Synchronise `docs/architecture/ontology-architecture.md` with the layer
  README, including the implementation table, DL encoding, axiom index, worked
  pattern, and deferred work.
- Add proposed ADR-A85 for the binding model, precedence law, conflict policy,
  fallback rule, and historical provenance boundary.
- Keep the root README and runtime architecture documents unchanged unless a
  concrete vocabulary-specific inconsistency is found.

### Examples and fixtures

Add a small, domain-neutral fixture set under `ontology/vocabulary/examples/`:

- one valid unscoped time-bounded binding
- one valid two-scope conjunctive binding
- one valid pair of alternative regional bindings
- one valid temporal edition handover
- one valid historical record using `voc:resolvedUnder`
- one invalid binding missing `forContract`
- one invalid binding missing `bindsScheme`
- one invalid temporal scope
- one overlapping equal-specificity conflict
- one scopeless binding that disagrees with `boundScheme`
- one historical record whose asserted binding is outside its record time

Fixtures should include the minimum Foundation and SKOS terms needed to validate
meaning, without inventing a Vocabulary-owned business scheme or scope catalogue.

### SHACL validation

Populate `ontology/vocabulary/shapes/constraints.ttl` with structural and
SHACL-SPARQL constraints for cardinality, temporal interval sanity, fallback
agreement, equal-specificity conflicts, and historical provenance. Keep the
constraints explicit about the input graph and resolution context. A static
ontology graph cannot by itself infer an arbitrary runtime context or time, so
context/time-dependent checks may use fixture metadata or a documented validation
profile rather than pretending to be OWL axioms.

Use `structural.ttl` for reusable node shapes and `rules.ttl` only if a rule is
needed for validation. Do not add a rule that silently chooses a winning binding.

### Executable resolution and tests

Add a small reference resolver in the repository's established tooling area,
with tests covering:

- scope conjunction and no-scope fallback
- temporal boundary inclusivity and open-ended validity
- strict-superset precedence
- equal-specificity conflict refusal
- fallback only when no applicable binding wins
- agreement between a scopeless binding and `boundScheme`
- deterministic results under triple-order permutation
- preservation of `resolvedUnder` without current-state re-resolution

The resolver is a conformance/reference implementation for the law in the layer
README. It must not become a domain-specific runtime or a fuzzy concept matcher.

### Cross-layer consumer checks

Add fixtures or contract checks showing how a consumer such as Surface or
Eligibility resolves a concept-valued property before reading the selected
scheme. Check that existing `boundScheme` behaviour remains valid for unscoped
inputs and that a historical `resolvedUnder` assertion is retained through a
versioned record path. Do not change Surface or Eligibility semantics in this
unit beyond the smallest adapter or fixture needed to prove the boundary.

### Traceability and handoff

- Add a slice validation pack under `docs/developer/validation/`.
- Add traceability rows for ADR-A85 and each invariant above.
- Update `docs/developer/status/vocabulary-temporal-binding.md` after every
  material action.
- Update `docs/developer/INDEX.md` when the plan, fixtures, tests, or validation
  pack changes state.

## Proposed slice boundaries

| Slice | Scope | Validation level | Completion gate |
|---|---|---|---|
| 1 | ADR-A85, architecture sync, fixture vocabulary and traceability skeleton | L0, L2 | Human review of semantic parity and ADR |
| 2 | Examples and structural/SHACL-SPARQL validation | L1, L3, L4 | Positive and negative fixtures produce expected conformance |
| 3 | Reference resolver and deterministic test suite | L1, L2 | Conflict and precedence mutations fail the tests |
| 4 | Consumer and historical provenance integration checks, final docs | L3, L4 | Cross-layer contract passes and validation pack is complete |

Each slice should stay within one or two implementation modules. If the resolver,
SHACL work, or consumer checks exceed that boundary, split the slice before
implementation rather than weakening the validation.

## Deliberate non-coverage

- No fuzzy label or natural-language concept resolution.
- No concept-level version alignment or deprecated-concept policy.
- No scope-membership algorithm. Vocabulary receives applicable scopes from its
  caller.
- No live store, runtime scheduler, or backend-specific integration.
- No silent conflict resolution or OWL encoding of whole-graph precedence.
- No advance of the ontology version IRI until the import and release policy is
  explicitly decided.
