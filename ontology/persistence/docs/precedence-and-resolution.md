<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Precedence and Resolution

Written for a reader who has not read [the sketch](../../../docs/developer/sketches/persistence-profile-substrate.md). Cross-references it and [the guide](../../../docs/architecture/rdf-sparql-patterns-guide.md) rather than repeating them.

## The problem

Two or more `dal:` profile individuals can declare a value for the same dimension at scopes that both match the same target. Something has to decide which value wins, and that decision has to be the same every time the same configuration is compiled, on any machine, in any order the underlying RDF graph happens to iterate its triples.

## The algorithm

Per target, per dimension, independently of every other dimension:

1. Collect every profile individual (a dedicated per-dimension class, or a `dal:DataAccessProfile` carrying that dimension's property) whose `dal:appliesTo` scope matches the target.
2. If the adopter supplied a `dal:CapabilitySpec` for this target, drop any candidate whose scope needs reasoning (`dal:EquivalentClassScope`) that the spec does not claim to provide, and record the drop. Without a spec, nothing is dropped here.
3. If no candidates remain, the target inherits the platform baseline default for that dimension.
4. Among the remaining candidates, the one with the highest `dal:priority` wins.
5. A tie at the highest priority is broken in favour of a non-reasoning-dependent candidate over a reasoning-dependent one.
6. A tie that survives step 5 is a compile-time refusal (`ProfileAmbiguityError`), never a guess.

This never looks at scope *kind* to break a tie. An earlier draft tried ranking `dal:ClassScope` as narrower than `dal:NamespaceScope` as narrower than `dal:GraphPatternScope`, and it does not hold up in general: a graph-pattern scope naming one exact graph can be narrower than a class scope matching millions of individuals. `dal:priority` is how an adopter says what they mean; the algorithm never infers it from vocabulary choice.

## Why a class alone is not always the right unit

Section 5's algorithm resolves "one target," but a target is not always just a class. `dal:GraphPatternScope` is how one *deployment* of a shared class is distinguished from another — lending's `beh:Behaviour` from credit's `beh:Behaviour` — and that distinction lives in which graph the data is written to, not in the class itself. `tools/persistence` therefore resolves against a `Target`, a (class, deployment) pair: one target per distinct `dal:GraphPatternScope` that names the class via `dal:coversClass`, plus one unscoped/fallback target. A class with no graph-pattern deployment at all gets exactly one target, so this never complicates the common case.

Every other scope kind (`dal:ClassScope`, `dal:NamespaceScope`, `dal:ShapeScope`, `dal:EquivalentClassScope`) matches on the class alone and applies uniformly across every deployment of it, which is why the guide's worked example has the reasoning-dependent "high value" override apply identically to lending's, credit's, and the fallback's resolution of `receiptModel`, while the graph-pattern-scoped concurrency choice differs between them.

## What "no live backend" actually buys

The algorithm above never asks a real triple store anything. Step 2's `dal:CapabilitySpec` is an adopter's own, unverified declaration, not a TCK-verified fact about a running system. This is a deliberate scope boundary (ADR-A79): a compiler that required a live backend before it could produce anything would force every adopter to expose a running database to a design-time tool just to use the ontology. The cost is that a spec can be wrong, in either direction. The compiler always also produces the unconditional `dal:CapabilityRequirement`, computed purely from the resolved profile, so an adopter without a spec still gets an explicit, honest statement of what their configuration needs, to check by eye or by their own tooling against whatever they actually run.

## Worked example

See the README's [worked example 2](../README.md#6-worked-example-2-a-shared-substrate-class-two-deployments) for the full lending/credit trace, including what changes when a `dal:CapabilitySpec` declaring no reasoning support is introduced.
