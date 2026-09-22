<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Aggregate Boundary Design

Written for a reader who has not read [the sketch](../../../docs/developer/sketches/persistence-profile-substrate.md)'s Part 4. Cross-references it and [the guide](../../../docs/architecture/rdf-sparql-patterns-guide.md)'s Part V rather than repeating them.

## Only the adopter can say what an aggregate is

Whether a population of triples is a unit of consistency, and if so what belongs inside it, is a fact about the adopter's own domain. Nothing in LATTICE's substrate layers can know this in advance. `dal:AggregateBoundaryProfile` exists to let an adopter declare it, per class, per deployment.

## Two mechanisms, one of them behind two authoring surfaces

| Strategy | Mechanism | Authoring |
|---|---|---|
| `dal:NamedGraphBoundary` | the aggregate root's IRI names a dedicated graph | `dal:graphIriTemplate` |
| `dal:CompositePropertyBoundary` | a bounded, cycle-checked closure computed by walking a SHACL shape | `dal:boundaryShape` |
| `dal:NoBoundary` | none: triple-level, value-based CAS on one property | `dal:valueGuardProperty` |

An earlier design considered a *third* authoring surface for the logical mechanism: letting an applied ontology mark a domain property as `rdfs:subPropertyOf dal:isCompositeOf`. It was dropped, not merely deprecated, and `ontology/persistence` declares no such vocabulary at all. Two reasons, both concrete:

1. **Entailment leaks.** `rdfs:subPropertyOf` is not decoration. Anything inferable through `dal:isCompositeOf`'s own characteristics, present now or added to this ontology later, becomes inferable through every domain property some adopter made a sub-property of it. Two unrelated applied ontologies each doing this can produce reasoning artefacts neither author intended, depending on the reasoner in use and on what this ontology asserts about `dal:isCompositeOf` in a future revision neither of them controls.
2. **It creates the exact import dependency this ontology otherwise avoids.** `ontology/persistence` targets everything by IRI reference so that no domain ontology needs to import it (§3.1 of the sketch, ADR-A78's opening decision). Asserting a domain property as a sub-property of a `dal:` term needs that term to already exist with stable semantics, reversing the dependency direction for exactly the one relationship this design worked hardest to keep one-way.

A SHACL shape says the same thing — "`ex:lineItem` is part of the aggregate" — by pointing at the domain property **by IRI**, the identical non-invasive mechanism every other scope kind in this ontology already uses, and touches nothing in the domain ontology's own axioms.

## The shape is read, never executed

`tools/persistence` walks a `dal:boundaryShape`'s `sh:property`/`sh:node` recursion once, offline, at compile time, into an internal closure: a set of properties considered composite, and a cycle check over the shape graph itself. No target backend is ever asked to run SHACL to determine where a write's boundary lies — by the time anything reaches generated SPARQL, the shape has already been fully consumed. A backend with no SHACL support at all still receives ordinary, portable SPARQL.

This also means the same shape can serve two purposes without conflict. An adopter who already maintains a shape for ordinary data validation loses nothing by pointing `dal:boundaryShape` at it: the compiler interprets only the `sh:property`/`sh:node` tree, and every other SHACL construct in the same shape (`sh:datatype`, `sh:pattern`, `sh:minCount`, and so on) is left untouched for the adopter's own validation tooling.

## What actually changes in the generated SPARQL

The guide's whole-graph replace primitive (Chapter 19) deletes and re-inserts everything in one named graph in a single DELETE/INSERT template. `dal:CompositePropertyBoundary` has no single graph to name, so the generated template differs in a way worth knowing about before choosing this strategy:

- **The property path lives only in `WHERE`.** SPARQL 1.1 permits a property path inside a `WHERE` clause's graph pattern, never inside a `DELETE` or `INSERT` template block (a template's predicate position accepts a single, fixed predicate — a `Verb` — never a path expression). The generated template therefore binds the closure's members in `WHERE` (`$root (ex:lineItem)+ ?member`) and deletes/inserts using the resulting plain-variable bindings, never re-stating the path in the template block itself.
- **No bounded repetition.** SPARQL 1.1 property paths support `*`, `+`, and `?`, and nothing resembling regex-style `{n,m}` bounded repetition — there is no such grammar production. Depth is enforced once, at compile time, by the shape walk's own cycle detection and `dal:maxTraversalDepth`, not by a runtime bound in the generated query.
- **The version row's subject is the root instance IRI, never a graph IRI.** There is no graph to key a meta shard on.

## Boundary conflicts

Two structural checks run before any SPARQL is generated, both in `persistence.validator`:

- A resource cannot be a composite member of one target's `dal:CompositePropertyBoundary` closure while also declaring its own, different, non-`dal:NoBoundary` strategy. Two aggregates cannot coherently share one member.
- A `dal:CompositePropertyBoundary`'s closure must resolve to one coherent stream identity for versioning purposes.

Both are `BoundaryConflict` exceptions, named and structured, never a silent pick.
