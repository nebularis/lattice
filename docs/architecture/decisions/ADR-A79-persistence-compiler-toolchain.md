---
published: true
---
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A79: Persistence compiler toolchain and template-based SPARQL generation

**Status:** Published, 2026-10-20. Accepted 2026-09-22.
**Described in:** [Persistence](../../../ontology/persistence/README.md)
**Date:** 2026-09-22
**Supersedes:** none
**Related:** ADR-A78, ADR-A80, [rdf-sparql-patterns-guide.md](../rdf-sparql-patterns-guide.md) Chapter 25

## Context

A `dal:DataAccessProfile` graph is configuration, not an executable. Something has to turn a resolved profile into the actual guarded `DELETE/INSERT … WHERE` templates, key-claim writes, tombstones, and audit queries that [rdf-sparql-patterns-guide.md](../rdf-sparql-patterns-guide.md) specifies. That something must not require an adopter to run any LATTICE Java process to get value from the ontology layer: an adopter who wants only the ontologies and the generated SPARQL, and intends to call it from their own application in their own language, must be able to do so.

Generating SPARQL from configuration by string interpolation is exactly the injection risk [Chapter 28, QP1](../rdf-sparql-patterns-guide.md#chapter-28--five-rules-and-how-they-are-enforced) forbids at the hand-written-query level, and a compiler that does it wholesale for every adopter's configuration is a worse version of the same defect, since a hostile or malformed class IRI, shard count, or tenant string in an adopter's own ontology now has one code path to corrupt every generated query rather than one query at a time.

The compiler's output must also remain distinct from two runtime concerns this ADR explicitly does not resolve: binding real request-time values (an entity IRI, an expected version, a payload) into a compiled template, and choosing, at the moment a request executes, whether a particular store's SPARQL dialect needs the template rewritten. Both require the store SPI to exist first, and the SPI's shape is not yet decided.

## Decision

1. **The compiler is a design-time-only toolchain**, `tools/persistence`, with two subcommands. `compile` consumes `ontology/persistence` individuals, the adopter's own applied-ontology class declarations, and an *optional* `dal:CapabilitySpec`, and produces a canonical `dal:CompiledProfile` graph in Turtle: per target, the fully resolved configuration with per-dimension provenance (which scope supplied the winning value), a `dal:GeneratedOperation` per operation naming a stable `dal:Template` identifier and its `dal:ParameterBinding`s, an unconditional `dal:CapabilityRequirement`, a `dal:CapabilityCheck` when a spec was supplied, and a structured diagnostics report. `compile` never produces SPARQL text, never reads a template body, and needs no live backend, so its output does not depend on knowing what backend, if any, will eventually run it. `instantiate`, entirely optional, reads a `dal:CompiledProfile` and the checked-in template library and mixes each generated operation's parameters into its named template to produce literal, portable SPARQL text. Neither subcommand performs I/O against a live triple store or requires an SPI.

2. **The compiled profile, not a SPARQL file, is the canonical output of `compile`.** It does not embed literal query text as a datatype property on any individual, a pattern `ontology/mork`'s `mrk:QueryTemplate`/`mrk:queryText` uses and this ontology deliberately does not repeat, because a query body sitting as an opaque string on an RDF node cannot be reasoned about, versioned independently, or shared across targets the way a named, referenced template can. `dal:Template` and `dal:ParameterBinding` are modelled on `mrk:QueryTemplate` and `mrk:ParameterBinding`'s reified, typed shape, diverging only on this point.

3. **Two substitution layers are kept strictly apart, one per subcommand.** `compile`-time substitution resolves configuration constants (graph-IRI patterns, property IRIs, shard counts, zero-pad width, datatypes) into `dal:ParameterBinding` individuals. `instantiate`-time substitution mixes those bindings into a named template's Mustache slots using a logic-less template engine (Mustache, via the `chevron` Python implementation). Request-time substitution proper — the genuine SPARQL variables a caller binds per call (`?entity`, `?expectedSeq`, the payload) — is left as SPARQL variables in `instantiate`'s output and is never touched by either substitution layer. A `dal:CompiledProfile`'s parameter bindings name every constant a future caller needs, so a caller in any language can bind the remaining request-time variables correctly without guessing.

4. **No adopter-supplied value reaches a template as a raw string, in either subcommand.** Every configuration value is passed through a single trusted RDF-term encoder (`encode_iri`, `encode_literal`, `encode_var`) that either produces a syntactically valid, escaped RDF term or refuses to compile. `compile` uses it to produce `dal:ParameterBinding` values. `instantiate`'s template renderer accepts only these wrapped term types, never a bare Python string, so a value that skipped the encoder is a type error, not a silent pass-through. Templates themselves are Lattice-authored and reviewed, and are treated as trusted structure. The security boundary is exactly, and only, the line between adopter-supplied configuration data and the encoder.

5. **An injection corpus is a release gate for `instantiate`**, not an aspiration, since that is the only subcommand that ever produces SPARQL text. Adversarial IRIs and literals (unbalanced braces, embedded keywords, quote and backslash sequences, bidirectional-override Unicode) are fed through the encoder and the full render pipeline, and the rendered output is parsed by an independent SPARQL parser to assert it contains exactly one intended operation. This is the guide's [QP1](../rdf-sparql-patterns-guide.md#chapter-28--five-rules-and-how-they-are-enforced) enforcement, applied to the compiler itself rather than to hand-written call sites.

6. **Out of scope for this ADR and for the plan it authorises**: the store SPI, a runtime "Request Query Mapping" library that would wire live requests to compiled templates and an SPI implementation, and a "Query Execution" component that would let a specific SPI rewrite a compiled template's syntax for its own dialect at request time. All three require the SPI's shape to be decided first. They stay open design questions.

## Consequences

- `tools/persistence` follows the existing `tools/surface` and `tools/mork` convention: an editable Python package, installed via `mise bootstrap:persistence`, exercised via `mise check:persistence`, with its own `pyproject.toml`.
- `compile` is the first of at least two consumers of a compiled profile in the ordinary sense (it produces one), and `instantiate` and the housekeeping component (ADR-A80) are the first two consumers that read one back. All read the same `dal:CompiledProfile` and `dal:CapabilityRequirement` shape, so a future third consumer (a Request Query Mapping library, once the SPI exists) need not re-implement resolution.
- Because Mustache is logic-less, any conditional structure in a generated query (for example, choosing between the `NamedGraphBoundary` and `CompositePropertyBoundary` variant of the corrected CAS pattern) is a template *selection* decision made by `compile`'s Python code, recorded as which `dal:Template` a `dal:GeneratedOperation` uses, never a control-flow construct inside a template. Templates stay auditable by inspection.
- An adopter who never runs `tools/persistence` and never adopts any LATTICE runtime library can still hand-copy a `dal:CompiledProfile` and, if they choose to run `instantiate` once, the resulting `.rq`/`.ru` files, into their own stack, which is an explicit design goal.
- This ADR does not itself deliver a Java equivalent of the compiler. If a future phase needs the compiler embedded in a JVM build pipeline, that is a new slice wrapping or reimplementing this one, not a retrofit of it.

## Addendum, 2026-10-10

[ADR-A123](ADR-A123-typed-operation-ir.md), accepted on 2026-10-10, supersedes decision 3's Mustache layer,
decision 4's renderer clause, the consequence that templates stay auditable by inspection, and `dal:templatePath`
in decision 1. Everything else here stands. The templates stay in use until they are retired.

## Addendum, 2026-10-20: `dal:templatePath` is gone (accepted 2026-10-20)

The addendum of 2026-10-10 said `dal:templatePath` is superseded. We remove it from the vocabulary and from every compiled profile.
`dal:templateId` is the identity of a builder, the operation id with no `.mustache` suffix, and `instantiate` finds the builder by it. Until the
templates are retired, a template library that overrides the built-in one is read from the file named by that id and the suffix. The compiled
profile also carries the contract of each operation and the run's choices ([ADR-A123](ADR-A123-typed-operation-ir.md), addendum of 2026-10-20),
and `compile` takes `--no-parameter-guards` and `--caller-graph-names`, which `instantiate` took before. Everything else in this ADR stands.

## Provenance

Designed in the [persistence profile substrate sketch](../../developer/sketches/persistence-profile-substrate.md). The three runtime concerns of decision 6 are open questions of the [platform development plan](../../developer/plans/lattice-platform-agentic-development-v0.2.md), Part 13, whose Part 6 was marked
pending revision because its ingestion and query-plane slices assumed ad hoc query construction. The store SPI is proposed decision
A75. The addendum of 2026-10-10 follows ADR-A123. The templates are retired by slice H2.9 of the
[formal-methods Track H plan](../../developer/plans/formal-methods-track-h.md). The addendum of 2026-10-20 was built in slice H2.7,
whose decisions taken alone are listed in [FMH-H2-7](../../developer/validation/FMH-H2-7.md). Published 2026-10-20.
