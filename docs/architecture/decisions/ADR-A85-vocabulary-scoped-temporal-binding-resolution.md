<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A85: Vocabulary scoped and temporal binding resolution

**Status:** Proposed
**Date:** 2026-09-24

## Context

Vocabulary commit `65ac4a85e11cc1f8616e3e0c24efd59bf4ca410d` adds
`voc:SchemeBinding`, `voc:BindingScope`, binding properties, temporal validity,
and historical `voc:resolvedUnder` provenance. The ontology must support
multiple scheme editions across contexts and time without changing the meaning
of previously resolved records. OWL cardinality and open-world semantics cannot
choose between overlapping bindings or express the complete context/time
comparison safely.

## Decision

A binding is an n-ary relation between one `voc:SchemeContract`, one
`voc:ConceptScheme` edition, zero or more conjunctive `voc:BindingScope` values,
and one Foundation temporal scope. Resolution receives the active context and
resolution time from its caller.

For one contract, applicable bindings are those whose every named scope holds
and whose temporal scope contains the resolution time. A binding whose scope set
is a strict superset of another applicable binding takes precedence. If multiple
applicable bindings remain at equal specificity, resolution fails as a
conflict. If no binding applies, `voc:boundScheme` is the fallback. A scopeless
binding and `boundScheme` must agree when both are present. A resolved record
stores the selected binding with `voc:resolvedUnder` and is not retroactively
re-resolved.

Structural validity belongs in SHACL. Whole-graph precedence and context/time
resolution belong in an explicit reference resolver or equivalent consuming
implementation. No OWL axiom silently selects a binding.

## Consequences

- Multiple bindings are represented by multiple individuals, not multiple values
  of a functional property.
- Consumers must resolve a binding before interpreting concept-valued data when
  scoped or temporal binding is in use.
- Examples, negative fixtures, SHACL-SPARQL constraints, deterministic tests,
  and historical provenance tests are required conformance artefacts.
- Scope membership and fuzzy label resolution remain caller responsibilities.
- Existing unscoped `boundScheme` consumers remain valid for inputs with no
  scoped bindings.
- The ontology version IRI remains an explicit release decision, not an
  automatic consequence of adding the ADR.
