<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A16: Surface Projection Mechanism

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A01 (layer conventions), ADR-A12 (derived artefacts and canonicalisation), ADR-A15 (realisation neutrality)

## Context

A declaration graph states what is true. Answering a question against it may require traversing relations that are expensive, remote, or governed elsewhere. Implementations have repeatedly solved this the same way and each time locally: generate a class per vocabulary member so that retrieval becomes a type check, or copy a value up a chain of relations so that a consumer can read it directly. The pattern is stable enough to name and general enough that building it once per domain is waste.

The immediate driver is a behaviour ontology whose execution shadows generate one class per concept per dimension, with hierarchical closure over the scheme's broader relation, and a separate set of rules promoting values from an upper ontology into that behaviour layer. Both are instances of one operation family. Neither has, on its own, a statement of what the generated content is allowed to mean, what authority it carries, when it goes stale, or what happens when two schemes mint the same local name.

Three options were open:

1. Port the shadow mechanism as-is into a domain layer. Cheapest, and wrong: it fixes the per-value class as the only form, so the first unbounded value space needs a second mechanism.
2. Add the mechanism to Foundation. Every layer could use it without an import, but Foundation would acquire generation concepts it has no need of, and the substrate would carry machinery for a realisation strategy.
3. A separate layer low in the dependency order, naming terms in other layers by punning rather than by import.

## Decision

**A new layer, `surface`, importing Foundation, Vocabulary, and Quantification, and imported by nothing in the substrate.** It declares two operations and only two:

- **Promotion** — a value reachable from a subject by a declared read path is restated as a direct assertion on that subject.
- **Indexing** — a value asserted of subjects is restated as a symbol those subjects can be retrieved by.

The generalisation that makes one mechanism sufficient is to separate the **read path** from the **surface form**. The shadow-class pattern is then the case where the path has length one and the form is a nominal class. Promotion is the case where the path has length greater than one and the form is a direct property. Nothing else was needed to cover both drivers.

### Three tiers

The **declaration tier** is authored and governed: a contract naming a carrier, a read path, a realisation mode, a target namespace, and a generation profile. The **generation tier** is not modelled — it is a compiler, and the layer takes no position on which one. The **derived-record tier** is generated alongside the symbols it describes: what was generated, from which exact inputs at which hashes, under which profile, with what authority.

### Conservativity, and the one place it does not hold

An index mints its own terms, so adding one entails nothing new about source terms and removing one loses no authored fact. That property — not the performance gain — is what licenses regenerating a surface at will, discarding it without loss, and capping its authority.

A promotion is not automatically conservative. It restates a value onto a property, and that property may be one the contract mints in its own target namespace, or one a consuming layer already declares. The second case produces statements over the authored signature, indistinguishable from authored facts; no annotation on the surface record changes that. Rather than hide the distinction, it is recorded as `srf:signatureScope` on every generated surface, and constrained: a promotion onto an authored property must be materialised rather than definitional, and a lossy promotion — derived, or reached across a weaker-than-exact match — may not target an authored property at all. This is law `srf:X6`, and it is the reason a crosswalk lands on a generated property whose identifier shows what it is.

### Authority is capped

A surface declares `Advisory` or `CachedReproducible` and nothing higher. An index that outranked the declaration it was built from would invert the derivation order. Where an external store is genuinely the system of record and accepts writes, that is a synchronisation contract and needs its own treatment; it is not a surface.

### Realisation neutrality (ADR-A15)

Both realisations are supported and the choice is declared, not assumed. `DefinitionOnly` emits axioms and depends on the profile's declared entailment regime; `Materialised` emits assertions and needs none. The default for new contracts is to ship assertions, because the most common deployment has no reasoner in the query path. Because the two land in different emitted modules, the choice also decides invalidation scope: a change to the carrier instance graph can leave the definitional module untouched.

### Stacking

A surface may be generated over another surface. The read set records this as a `SurfaceSource` entry and the resulting depth is checked against the profile's `permittedStackDepth`. The model supports arbitrary depth; this release constrains the permitted depth to one, because a deeper chain turns the read set into a hash-chained directed graph and the composition of the determinism and conservativity laws across that graph has not yet been stated.

## Consequences

**Accepted.**

- One more layer, and one more thing to keep domain-neutral. The layer ships no vocabularies, no dimensions, and no contracts; every contract is authored by a deployment in its own `execution/` directory.
- Punning. Surface names classes and properties in other layers without importing them, following the device Vocabulary already established for `voc:constrainsProperty`. Deployments whose tooling rejects punning use `WrappedSymbols`, in which provenance sits on a separate individual.
- Naming injectivity must be checked, not assumed, and a collision is a hard failure. `LocalNameFromValue` stops being injective the moment two schemes bind one dimension.
- A profile change is an estate-wide regeneration. This is the cost of being able to say that two artefacts are interchangeable.

**Conformance (L7).** A conformant surface does not raise the conformance level of the graph it indexes: a surface over an analysis-ready graph does not make that graph operationally evaluable. Surfaces accelerate; they do not admit. A surface is never the evidence for an admissibility decision or an execution record — those cite declarations. That an implementation reached an answer through a surface is a realisation-profile fact recorded on the decision, not a change in what the decision rests on.

**Deferred, deliberately.** `RangePartitionPopulation` and the `ExternalIndex` form are declared and rejected by this release's constraints, so that their absence is visible in the model rather than silent. Both are tracked in the outstanding-items note.

## Addendum/Decision: X6 stands as designed (sign-off)

Source-signature promotion stays in Surface, constrained as already stated — materialised rather than definitional, and never lossy onto an authored property. Pushing it to MORK would keep Surface strictly conservative in theory but costs the ability to express dimension-sourcing contracts (the CSO→FBO case that motivated X6) as Surface contracts at all, and Surface's whole purpose is to spare authors from writing MORK mapping detail by hand. ADR-A21 states how this composes once a surface stacks over another.

## Addendum (2026-09-18): a third operation

ADR-A17 extends this ADR's "two operations and only two" decision with a third, Projection, for mapping intent neither promotion nor indexing covers. This does not reopen or weaken anything decided here: Promotion and Indexing keep their laws, their direct-emit path, and this ADR's rationale unchanged. Projection is additive, gets its own law register (ADR-A20), and — unlike Promotion and Indexing — lowers into MORK rather than emitting an artefact itself (ADR-A18).
