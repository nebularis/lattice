<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack — `persistence-substrate-and-compiler`

**Slice:** `persistence-substrate-and-compiler` (Slice 2 of the `rdf-sparql-patterns-phase` plan)
**Plan:** [rdf-sparql-patterns-phase-plan.md](../plans/rdf-sparql-patterns-phase-plan.md)
**Status:** [rdf-sparql-patterns-status.md](../status/rdf-sparql-patterns-status.md)

## What invariant does this slice protect?

An adopter of LATTICE must be able to declare, per class or per deployment of their own applied ontology, which of the portable RDF/SPARQL patterns in [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md) apply, and get back generated SPARQL, without hand-writing it and without requiring any LATTICE runtime component or store SPI (ADR-A78, ADR-A79). The resolution of that declaration must be deterministic (the same configuration compiles to the same profile every time, regardless of triple order), must never silently accept an internally inconsistent configuration (sketch §3.5's cross-axis checks), must never assume a live backend's capabilities (sketch §3.6's requirement/spec/check triad), and the compiler's own template-instantiation step must never let an adversarial value in the loaded configuration escape into a second, unintended SPARQL operation (ADR-A79 point 5).

## Test case table

| ID | Given / When / Then | Level | Invariant protected | Pass criterion | +/- |
|---|---|---|---|---|---|
| T1 | Given the sketch's minimal single-class example, when every dimension is resolved, then each resolves to the declared value with the declaring profile as provenance | L1 | Basic resolution (§3.4) | `test_resolver.py::TestSingleClassResolution` | + |
| T2 | Given a class with no matching scope, when a dimension is resolved, then it inherits the documented platform baseline with `candidate_count == 0` | L1 | Baseline defaults (§3.4.1) | `test_resolver.py::TestBaselineDefaults` | + |
| T3 | Given the lending/credit shared-class fixture, when targets are discovered, then exactly three (lending, credit, fallback) exist for `beh:Behaviour` | L1 | Target = class + deployment (§3.4.3) | `test_resolver.py::TestSharedClassDeployments::test_discovers_one_target_per_deployment_plus_fallback` | + |
| T4 | Given the same fixture, when concurrency is resolved per deployment, then lending gets `Optimistic`, credit gets `ProvidedConcurrency`, the fallback also gets `ProvidedConcurrency` | L1 | Graph-pattern-over-class precedence (ADR-A78 point 5) | `test_resolver.py::TestSharedClassDeployments::test_lending_deployment_gets_optimistic_credit_gets_provided` | + |
| T5 | Given the same fixture with no `CapabilitySpec`, when receipt model is resolved, then the reasoning-dependent `EquivalentClassScope` candidate wins | L1 | Absence of a spec never drops a candidate (§3.6) | `test_resolver.py::TestSharedClassDeployments::test_reasoning_dependent_scope_wins_receipt_model_without_a_spec` | + |
| T6 | Given the same fixture with a `CapabilitySpec` declaring no reasoning, when receipt model is resolved, then the reasoning-dependent candidate is dropped and the next-highest wins | L1 | Capability self-check (§3.6) | `test_resolver.py::TestSharedClassDeployments::test_capability_spec_without_reasoning_drops_the_equivalent_class_candidate` | + |
| T7 | Given two candidates at equal priority, neither reasoning-dependent, when resolved, then `ProfileAmbiguityError` is raised, never a silent pick | L1 | Never silently downgrade | `test_resolver.py::TestAmbiguity` | - |
| T8 | Given each of the five negative fixtures (one per §3.5 cross-axis row), when validated, then the exact named `CrossAxisViolation` kind is raised | L1 | Cross-axis consistency (§3.5) | `test_validator.py::test_cross_axis_negative_fixture_raises_named_violation` (5 cases) | - |
| T9 | Given three positive fixtures, when validated, then no exception is raised | L1 | No false positives | `test_validator.py::test_positive_fixture_raises_nothing` (3 cases) | + |
| T10 | Given the mixed-receipt-model fixture, when checked, then exactly one `WARNING`-severity diagnostic is produced, compile does not fail | L1 | Warning, not error (§3.5 row 6) | `test_validator.py::test_mixed_receipt_model_is_a_warning_not_an_error` | + |
| T11 | Given a nested SHACL shape, when walked, then composite properties include only shape-declared properties, never `ex:customer` | L1 | Boundary closure correctness (§4.3) | `test_boundary.py::test_walks_nested_shape_into_composite_properties` | + |
| T12 | Given a shape whose `sh:node` recursion cycles back to an ancestor, when walked, then `BoundaryCycleError` is raised | L1 | Cycle safety | `test_boundary.py::test_detects_cycles` | - |
| T13 | Given a resolved profile with no `CapabilitySpec`, when compared against one with a maximally generous spec, then resolution is identical | L1 | Absence changes nothing (§3.6) | `test_capability.py::test_absence_of_spec_never_changes_resolution` | + |
| T14 | Given ~170 adversarial IRIs and literals (unbalanced braces, embedded keywords, quote/backslash sequences, bidirectional-override and zero-width Unicode), when encoded and rendered against every template, then each either is rejected or renders into exactly one parseable operation | L8 | Injection safety (ADR-A79 point 5) | `test_terms.py` (164 parametrised cases) | - |
| T15 | Given the same configuration compiled twice (once with triples loaded in shuffled order), when compared, then the outputs are graph-isomorphic | L2 | Determinism (guide QP4) | `test_determinism.py` | + |
| T16 | Given every positive example fixture, when compiled then instantiated, then every generated `.rq` parses as valid SPARQL (with `#PAYLOAD#` substituted by a minimal ground triple) | L4 | End-to-end correctness | `test_compiler_integration.py::test_end_to_end_compile_instantiate_parse` (4 fixtures) | + |
| T17 | Given every negative fixture, when compiled, then `CompileError` wraps the underlying named violation | L4 | Compiler surfaces validator failures | `test_compiler_integration.py::test_negative_fixture_fails_compile` (5 fixtures) | - |
| T18 | Given `ontology/persistence`'s own SHACL shapes, when run against every non-SHACL-negative example fixture, then all conform (warnings allowed) | L4 | Ontology self-validation (sketch §3.9) | `test_compiler_integration.py::TestShaclSelfValidation::test_conforms` (12 fixtures) | + |
| T19 | Given the one SHACL-negative fixture (`CompositePropertyBoundary` with no `boundaryShape`), when validated, then it does not conform | L4 | Defence in depth alongside the Python validator | `test_compiler_integration.py::TestShaclSelfValidation::test_does_not_conform` | - |
| T20 | Given the codebase, when scanned via AST, then only `persistence.render` imports `chevron`, no resolution-critical module calls a wall-clock function, and `chevron.render`'s template argument is never dynamically assembled | L1 | Trust-boundary enforcement (ADR-A79 point 4) | `test_architecture.py` (3 checks) | - |

## One command to run everything

```bash
mise run check:persistence
```

Equivalent to `python -m pytest tools/persistence/tests -q` from the repository root, after `mise run bootstrap:persistence`.

## Expected artefacts

- Test run output: 239 passed (as of this slice's completion), zero skipped, zero xfail.
- A sample compiled profile and its instantiated templates, reproducible via:
  ```bash
  python -m persistence compile ontology/persistence/spec/persistence.ttl \
      ontology/persistence/examples/baseline-single-class.ttl --out /tmp/compiled.ttl
  python -m persistence instantiate /tmp/compiled.ttl --out /tmp/rq
  ```
- `docs/traceability/matrix.csv` rows for A-78, A-79, and every named cross-axis/capability/injection/determinism requirement above.

## Deliberate non-coverage

- **No live SPARQL execution against any store.** No store SPI exists in this plan to execute against (out of scope, proposed A75).
- **No runtime parameter binding.** The genuine SPARQL variables (`$root`, `$expectedSeq`, the payload) in instantiated templates are never bound here; that is Request Query Mapping, explicitly deferred (see [lattice-platform-agentic-development-v0.2.md](../plans/lattice-platform-agentic-development-v0.2.md) Part 13, rows 11-12).
- **No store-specific dialect rewriting.** Query Execution is explicitly deferred alongside the SPI.
- **`platform/housekeeping` (Slice 3).** Not built in this slice. Its contracts and configuration model are designed in ADR-A80 but not yet implemented.
- **Multi-property, multi-level `CompositePropertyBoundary` closures.** The `cas-replace-composite-property` template uses only the first composite property found, with `+` traversal. A shape with several sibling composite properties at one level needs a property-path alternation this first cut does not generate (documented in `tools/persistence/README.md`, "Known limitations").
- **`unconditional-write` for non-`NamedGraphBoundary` targets.** Documented as a known limitation; not covered by a passing test because no fixture currently exercises that combination.

## Adversarial probe (for the human validation gate)

Two suggested probes:

1. Temporarily replace `Iri.encode`'s forbidden-character check body with `pass` (drop the rejection) and re-run `test_terms.py`. Verified: 8 of 164 cases fail, each on an adversarial value that previously raised `SparqlTermError` and now raises a raw `pyparsing.ParseException` deep inside the SPARQL parser instead of being cleanly refused at the encoder boundary, demonstrating the corpus is not vacuous.
2. Temporarily retarget `dal:CompositePropertyBoundaryRequiresShapeShape`'s `sh:targetClass` away from `dal:AggregateBoundaryProfile` (to a class nothing matches) in `shapes/constraints.ttl`, and re-run `test_compiler_integration.py::TestShaclSelfValidation::test_does_not_conform`. Verified: it fails (`assert not True`, the fixture now conforms when it should not), demonstrating the SHACL-level defence-in-depth is load-bearing, not decorative. (A naive line-by-line comment-out of the shape corrupts the embedded multi-line SPARQL string literal instead of disabling the shape; retargeting `sh:targetClass` is the clean way to disable one shape for this probe.)
