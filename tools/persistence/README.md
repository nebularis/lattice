<!-- SPDX-License-Identifier: MPL-2.0 -->

# Persistence Compiler

Design-time toolchain for the LATTICE persistence profile substrate (`ontology/persistence`), per [ADR-A78](../../docs/architecture/decisions/ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md) and [ADR-A79](../../docs/architecture/decisions/ADR-A79-persistence-compiler-toolchain.md). Turns an adopter's `dal:` configuration into a canonical `dal:CompiledProfile` graph, and optionally that graph into portable SPARQL text. Requires no live backend and no store SPI anywhere in the pipeline.

Full design: [persistence-profile-substrate.md](../../docs/developer/sketches/persistence-profile-substrate.md) and [rdf-sparql-patterns-guide.md](../../docs/architecture/rdf-sparql-patterns-guide.md).

## Install

```bash
mise exec -- python -m pip install -e ./tools/persistence[test]
```

## Two stages, two subcommands

**`compile`** loads `ontology/persistence` graphs plus an adopter's applied ontology, resolves every discovered target, validates it, selects operations, and emits a `dal:CompiledProfile` graph in Turtle. It never produces SPARQL text, never reads a template body, and needs no live backend, so its output does not depend on knowing what backend, if any, will eventually run it.

```bash
python -m persistence compile \
    ontology/persistence/spec/persistence.ttl \
    path/to/your-config.ttl \
    [--capability-spec path/to/your-capability-spec.ttl] \
    --out compiled-profile.ttl
```

**`instantiate`** is entirely optional. It reads a compiled profile and the checked-in template library, and mixes each generated operation's parameters into its named template to produce generic, portable SPARQL text.

```bash
python -m persistence instantiate compiled-profile.ttl --out ./rq
```

Neither subcommand assumes you will ever run the other, or run any further LATTICE component at all. An adopter who wants only the ontology and the generated SPARQL can run both once and walk away with the `.rq` files.

## What `compile` actually does

| Stage | Input | Output | Failure mode |
|---|---|---|---|
| Load | ontology graphs, an optional `dal:CapabilitySpec` | an in-memory RDF graph | malformed Turtle |
| Resolve | the loaded graph | one resolved profile per target, seven dimensions each, with provenance | `ProfileAmbiguityError` |
| Validate | resolved profiles | a diagnostics list | `CrossAxisViolation`, `BoundaryConflict`, `MissingBoundaryShapeError` |
| Select | validated profiles | one named template per generated operation | none — a lookup table |
| Emit | selected templates + reified parameter bindings | a `dal:CompiledProfile` graph | an encoder rejection (see below) |

Every one of these is a real, tested Python module: [`persistence.resolver`](src/persistence/resolver.py) (the precedence algorithm, sketch §3.4), [`persistence.scopes`](src/persistence/scopes.py) (scope matching and the `Target` = class + deployment model, sketch §3.4.3), [`persistence.boundary`](src/persistence/boundary.py) (walking a `dal:boundaryShape` closure, sketch §4.3), [`persistence.validator`](src/persistence/validator.py) (every cross-axis check in sketch §3.5 plus boundary conflicts in §4.6, each a named exception type), [`persistence.capability`](src/persistence/capability.py) (the requirement/spec/check triad, sketch §3.6), [`persistence.operations`](src/persistence/operations.py) (template selection), [`persistence.compiler`](src/persistence/compiler.py) (orchestration and RDF emission).

## A `Target` is a class, plus a deployment when there is more than one

A class alone cannot distinguish "`beh:Behaviour` as lending deploys it" from "`beh:Behaviour` as credit deploys it" (sketch §3.4.3's worked conflict): that distinction lives in which graph the instances are written to, which is exactly what a `dal:GraphPatternScope` declares via `dal:coversClass`. `discover_targets()` therefore yields one `Target` per distinct `GraphPatternScope` deployment a class has, plus one unscoped/fallback target — a class with no graph-pattern deployment at all gets exactly one target. This is an implementation-level refinement not spelled out explicitly in the sketch's prose; see `persistence.scopes.Target`'s docstring for the full reasoning.

## `#PAYLOAD#`: a documented non-SPARQL marker

A generated operation's INSERT block that writes application data (`create-if-absent`, `cas-replace`, `tombstone-delete`'s implicit clear, `unconditional-write`) contains the literal text `#PAYLOAD#` where the payload triples belong. This is **not** a bindable SPARQL variable: SPARQL has no way to bind an entire set of triples through one variable (`GRAPH ?g { $payload }` is not valid SPARQL — a single variable cannot stand in for a `TriplesBlock`). Whatever executes an instantiated template — a future Request Query Mapping library, or an adopter's own code — must splice in the caller's already-serialised, trusted Turtle before submitting the request text to a SPARQL endpoint. This mirrors how the guide's own worked examples embed payload directly rather than through a variable.

## Known limitations (first cut, honestly scoped)

- **`unconditional-write`** only knows how to target a `dal:NamedGraphBoundary`'s graph. A target combining `dal:ProvidedConcurrency`/`dal:LockingConcurrency` with `dal:CompositePropertyBoundary` or `dal:NoBoundary` will fail to render (a missing `graphPrefix` binding) until a second variant is added.
- **`cas-replace-composite-property`** uses only the *first* composite property found by walking a target's `dal:boundaryShape`, with `+` (one-or-more) traversal. A shape with several sibling composite properties at the same level needs a property-path alternation (`p1|p2|...`) this first cut does not yet generate.
- **`dal:EquivalentClassScope` matching** is a syntactic approximation (does the target class appear inside the equivalence expression's `owl:intersectionOf`), not full OWL entailment. No reasoner dependency is introduced anywhere in this compiler, by design (sketch non-goals).
- **The log-bucket month** (`urn:g:txlog/{month}`) is computed at request time via `NOW()`, inside the generated `WHERE` clause, not baked in as a compile-time constant — this differs from an earlier, since-corrected version of the worked example in the sketch, which would have hard-coded a single month into a template meant to be reused across many months.
- **`dal:epochGuardScope`'s dataset-level guard graph and node are a fixed constant, not per-deployment configurable** (`persistence-compiler-iri-sync` Slice 1, 2026-09-23). `dal:EpochProfile` (`ontology/persistence` commit `c276afb`) does not declare a property naming which graph or resource IRI holds a deployment's dataset-level epoch value, so `datasetGraph`/`datasetNode` are both hard-coded to `urn:g:dataset`, matching `rdf-sparql-patterns-guide.md` §19.1's worked example exactly, the same way `urn:g:txn`/`urn:g:txlog/` already are. Only `cas-replace-named-graph`, `tombstone-delete-named-graph`, and `cas-replace-composite-property` have a `dal:DatasetLevelGuard` template variant; `unconditional-write`, `cas-replace-value-guard`, and `append-event` do not guard on epoch at all (no per-aggregate version row exists for the first, no meta-graph stamping exists for the others), and adding one to them was judged out of this slice's scope — see [`docs/developer/status/persistence-compiler-iri-sync.md`](../../docs/developer/status/persistence-compiler-iri-sync.md).

## Development

```bash
mise exec -- python -m pytest tools/persistence/tests -v
```

The test suite includes:

- **`test_terms.py`** — the injection corpus (ADR-A79 point 5): adversarial IRIs and literals fed through every encoder and every checked-in template, parsed by `rdflib`'s own SPARQL parser to assert exactly one operation ever results.
- **`test_resolver.py`**, **`test_validator.py`**, **`test_capability.py`**, **`test_boundary.py`** — unit coverage for each module, including the lending/credit worked conflict from the sketch, reproduced as an executable test.
- **`test_determinism.py`** — compiling the same configuration twice (including with triples loaded in shuffled order) produces isomorphic output.
- **`test_compiler_integration.py`** — full compile → instantiate → parse round trips for every positive example fixture, `CompileError` assertions for every negative one, and SHACL self-validation of `ontology/persistence`'s own shapes against every fixture.
- **`test_architecture.py`** — the Python equivalent of an ArchUnit rule: only `persistence.render` may import `chevron`, no wall-clock call exists in any resolution-critical module, and `chevron.render`'s template argument is never dynamically assembled.
