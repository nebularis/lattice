# Plan: Finish Gate 7 after Python becomes available

This prompt captures the remaining work after the repository-level dataset and substrate scaffolding are already in place and the environment is able to run Python/Turtle validation.

## Goal

Complete the applied validation package under `examples/insure-o/` with a real, validated graph and a deterministic validation pass, using Python-based RDF/Turtle tooling instead of editor-only checks.

## Preconditions

1. Python is available on PATH.
2. A Turtle/RDF library is installed, such as `rdflib`.
3. The repository root is the active working directory.
4. The substrate files already authored in the repo are the source of truth.

## Immediate setup

1. Confirm Python and package availability.
2. Run a quick sanity check to import `rdflib`.
3. Parse the core edited files individually to confirm they load cleanly as Turtle.
4. Build a validation command sequence for the applied package and the relevant substrate files.

## Execution plan

### 1. Validate the existing substrate additions

Run a focused Turtle parse and validation pass over:

- `eligibility/README.md`-derived semantic content as represented in `eligibility/spec/eligibility.ttl`
- `eligibility/shapes/rules.ttl`
- `eligibility/vocab/eligibility-vocab.ttl`
- `behaviour/spec/behaviour.ttl`
- `behaviour/shapes/constraints.ttl`
- `examples/insure-o/**/*.ttl`

Confirm that:

- `elg:HierarchicalMatch` is loadable and globally consistent
- `elg:L9` is present and semantically coherent
- the rule in `eligibility/shapes/rules.ttl` materialises the expected broader closure
- the example hierarchy in `examples/insure-o/projection/**/*.ttl` is valid RDF/Turtle
- the execution profile remains optional and non-semantic by design

### 2. Add missing implementation details where validation reveals gaps

If parsing or validation exposes a problem, fix only the root cause, then rerun the relevant validation pass.

Typical follow-ups:

- add missing ontology declarations for any applied-layer property or class used by the examples
- tighten the scheme contract declarations for externally bound business dimensions
- add missing `rdfs:domain` / `rdfs:range` or cardinality constraints where the repo pattern expects them
- align example vocab with repo conventions for `voc:ConceptScheme` and `skos:broader` use

### 3. Complete the actual insure-o example set

Expand the package to a fuller but still minimal set of concrete examples for:

- peril hierarchy
- territory or jurisdiction hierarchy
- line-of-business classification
- asset-class binding
- a policy/coverage example with a limit and retention
- a sequential allowance chain over multiple capacity layers
- a defect fixture for missing scheme contract
- a defect fixture for unresolved or mismatched business dimension values

The examples should remain generic and non-product-specific, while still showing realistic insurance-domain usage.

### 4. Add a real validation corpus

Create a small set of authoritative validation files under `examples/insure-o/test/` with intended pass/fail behaviour:

- positive examples that should validate successfully
- negative examples that should fail because of missing scheme contracts, malformed hierarchy membership, or invalid mixed-dimension usage
- one scenario with a claim/allowance interaction that uses `bhv:Sequential`

These tests should be kept deliberately small and readable, matching the repository’s existing gate-testing style.

### 5. Validate the applied package end-to-end

Run a focused validation pass over the entire `examples/insure-o/` tree and selected repository substrate files.

The pass should check:

- the package loads as valid Turtle
- the scheme contracts bind to concept schemes
- the hierarchy closure is materially represented
- the eligibility profiles remain structurally valid
- the capacity behaviour remains consistent with sequential absorption semantics

### 6. Fix and revalidate until the package is green

Repeat the cycle until the package passes the targeted validation set without syntax or ontology-level breakage.

Scope discipline:

- no speculative source-product modeling
- no new proprietary naming
- no change to the core substrate unless the validation reveals an actual root cause
- no compilation requirement introduced into the semantic model

## Expected final output

When complete, the repo should contain:

- a coherent `examples/insure-o/` package
- a concrete peril hierarchy and matching admission profile
- a realistic sequential allowance chain
- a small set of valid and invalid example fixtures
- a passing targeted validation run on the relevant graph files

## Completion condition

The work is done when:

1. the applied package files parse cleanly as Turtle,
2. the relevant validation suite passes,
3. the hierarchy and allowance examples remain consistent with the substrate,
4. the package is documented as an optional realisation path, not a required compiled output.

## Execution command pattern

Use commands along these lines once Python is available:

```powershell
python -m pip install rdflib
python -c "import rdflib; print(rdflib.__version__)"
python - <<'PY'
from rdflib import Graph

g = Graph()
for path in [
    'eligibility/spec/eligibility.ttl',
    'behaviour/spec/behaviour.ttl',
    'examples/insure-o/projection/bindings.ttl',
    'examples/insure-o/projection/hierarchy-example.ttl',
    'examples/insure-o/execution/shadow-profile.ttl',
]:
    g.parse(path, format='turtle')
print('all ok')
PY
```

Adapt the exact set of input files to the final validation run as the package stabilises.
