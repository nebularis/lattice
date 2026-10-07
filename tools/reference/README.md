<!-- SPDX-License-Identifier: MPL-2.0 -->

# `tools/reference/`

Hand-written, test-verified reference semantics for the formal-methods epic's track B
(`docs/developer/plans/formal-methods-track-b.md`, [ADR-A-FM3](../../docs/architecture/decisions/ADR-A-FM3-reference-evaluator-home-and-scope.md)).
One subdirectory per layer with a reference, mirroring `ontology/<layer>/`'s own names, the same
convention `tools/proofs/<layer>/` (mechanised theories, ADR-A-FM2) and `tools/models/<name>/`
(design-time models, track C) already use.

A reference here restates an **already-accepted** law independently enough that a mistake shared
by every compiler backend reading the same law has something else to disagree with. It is not
generated (unlike `tools/proofs/`'s datatypes) and it does not propose a law not yet accepted
(unlike `tools/models/`'s design-time models) — it is hand-written from the layer's own literate
README, verified by differential and property test, never proved and never run against the live
graph (ADR-A-FM3, restating epic principles E1 and E3).

## Subdirectories

- `eligibility/` — track B1/B2: the logic kernel and Eligibility's denotation (laws L9-L16),
  checked against `tools/proofs/eligibility/`'s own Isabelle statements (B1) and differentially
  tested against `tools/mork_compilers`' SPARQL and SHACL backends (B2).
