<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Aggregate Boundary Design

Written for a reader who has not read [the legacy sketch](../../../docs/developer/sketches/persistence-profile-substrate.md)'s Part 4. The decisions are [ADR-A122](../../../docs/architecture/decisions/ADR-A122-aggregate-ownership.md), which amends [ADR-A78](../../../docs/architecture/decisions/ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md) decision 4, and the normative detail is [the design sketch](../../../docs/developer/sketches/persistence-aggregate-ownership.md). The [patterns guide](../../../docs/architecture/rdf-sparql-patterns-guide.md)'s Part V explains the write itself.

## Only the adopter can say what an aggregate is

Whether a population of triples is a unit of consistency, and if so what belongs inside it, is a fact about the adopter's own domain. Nothing in LATTICE's substrate layers can know this in advance. `dal:AggregateBoundaryProfile` lets an adopter declare it, per class and per deployment.

An aggregate is a **root** and the nodes it **owns**. Three kinds of node are reachable from a root, and the declaration says which is which.

| Kind | What it is | When the aggregate is deleted |
|---|---|---|
| Owned | a part of the aggregate, such as a milestone of a project or a task of a milestone | its triples are deleted |
| Reference | an independent entity, or another aggregate, such as the organisation a project is for | the edge to it is deleted. The node stays |
| Vocabulary | reference data, such as a concept that gives a task its status | the edge to it is deleted. The node stays, and no configuration can say otherwise unless the aggregate manages that vocabulary |

Ownership belongs to an **edge in its context**. A document attached to a task can be a part of the task, while the same property on a plan can point at a template shared by many projects. A flat list of owned properties cannot say both, so the declaration is a tree, one node shape per kind of owned node.

## Three strategies

| Strategy | Where the aggregate is | Authoring |
|---|---|---|
| `dal:NamedGraphBoundary` | one named graph per root | `dal:graphIriTemplate`, and optionally `dal:boundaryShape` |
| `dal:CompositePropertyBoundary` | the root and the nodes it owns, in one named graph shared by the family | `dal:boundaryShape` and `dal:dataGraph` |
| `dal:NoBoundary` | none. Triple-level, value-based compare and set on one property | `dal:valueGuardProperty` |

**New deployments should prefer `dal:NamedGraphBoundary`.** A graph per aggregate is the cheapest boundary to reason about, a delete is one operation, and the graph's contents are what the aggregate is. The composite strategy exists for an adopter whose data already lives in one large shared graph and cannot be repartitioned. LATTICE does not impose a layout, and the compiler's default strategy is unchanged.

## The classified boundary shape

Both strategies use the same declaration, an `sh:NodeShape` named by `dal:boundaryShape`. Every property shape in it that leads to a node carries `dal:ownership`, one of `dal:Owned`, `dal:Reference` or `dal:Vocabulary`. A property shape with `sh:datatype` or `sh:nodeKind sh:Literal` is a value property and carries none. `sh:node` alone no longer means ownership, because validation shapes commonly put it on references too.

```turtle
ex:TaskShape a sh:NodeShape ; sh:targetClass ex:Task ;
    sh:property [ sh:path ex:status ;     sh:class skos:Concept ;  dal:ownership dal:Vocabulary ] ,
                [ sh:path ex:assignee ;   sh:class ex:Person ;     dal:ownership dal:Reference ] ,
                [ sh:path ex:hasSubtask ; sh:node ex:TaskShape ;   dal:ownership dal:Owned ] ,
                [ sh:path ex:attachment ; sh:node ex:DocumentShape ; dal:ownership dal:Owned ] ,
                [ sh:path [ sh:inversePath ex:onTask ] ; sh:node ex:CommentShape ; dal:ownership dal:Owned ] .
```

The shape is the authority on which edges exist, and an edge it does not declare is not followed. The compiler refuses an edge that leads to a node and carries no classification, so "these edges are references" stays a short statement and no edge is owned by accident. The full reference fixture is [`examples/composite-project-ownership.ttl`](../examples/composite-project-ownership.ttl).

**What is deleted.** The members of an aggregate are the nodes reached from its root by a non-empty path of owned edges, each in its declared direction (`sh:path` or `[ sh:inversePath ]`). Recursion is allowed. The delete set is every triple whose subject is the root or a member, so value properties, owned edges, reference edges and vocabulary edges all go, and the nodes at the far ends of reference and vocabulary edges do not. A payload is skolemised before it is written, so a skolem IRI is an ordinary node, owned only through owned edges. A list or a quantity inside an aggregate needs owned edges for `rdf:first` and `rdf:rest`.

## What the compiler refuses

| Refusal | When |
|---|---|
| `MissingDataGraph` | a composite profile names no `dal:dataGraph` |
| `MissingBoundaryShapeError` | a composite profile names no `dal:boundaryShape` |
| `ComplexBoundaryPath` | a property shape's `sh:path` is neither an IRI nor `[ sh:inversePath IRI ]` |
| `UnclassifiedBoundaryEdge` | an edge leads to a node and carries no `dal:ownership` |
| `OwnershipOnValueProperty` | a value property carries `dal:ownership` |
| `CompositeBoundaryWithoutOwnedEdges` | a composite shape owns no edge, so the aggregate would be its root alone |
| `OwnedReferenceData` | an owned edge leads to reference data (`skos:Concept`, `skos:ConceptScheme`, a class a `dal:ReferenceData` declaration covers, or a subclass), and the profile does not declare `dal:ownsReferenceData true` |
| `UniquenessOutsideBoundary` | a uniqueness key is not a property of the root or of an owned shape |
| `BoundaryConflict` | a member class, at any depth, declares a boundary strategy of its own |
| `OverlappingOwnership` | two composite aggregates own one class, or one owns the other's root |
| `GraphIriTemplateInvalid`, `GraphIriTemplateOverlap` | a named-graph template is not injective, within a family or across families |

One warning, `ReferenceToOwnedClass`, says that a property shape outside an aggregate points at a member class that is not its root. A deleted member leaves such a reference dangling, so references from outside should name the root, which keeps a tombstoned version row.

Reference data is declared per class, so non-SKOS sets such as currency codes get the same protection:

```turtle
ex:Currencies a dal:ReferenceData ; dal:coversClass ex:Currency .
```

## The shape is read, never executed

`tools/persistence` walks a `dal:boundaryShape` once, offline, at compile time, into a classified tree, and compiles the owned edges to **one SPARQL property path** by state elimination. No target backend is ever asked to run SHACL to find where a write's boundary lies. A backend with no SHACL support at all receives ordinary, portable SPARQL. The same shape can still serve the adopter's own validation: the compiler interprets only `sh:property`, `sh:path`, `sh:node`, `sh:class`, `dal:ownership`, `sh:datatype` and `sh:nodeKind`, and leaves every other construct alone.

A SHACL shape points at the domain's properties by IRI and touches nothing in the domain ontology's axioms. The alternatives were worse. Asserting a domain property `rdfs:subPropertyOf` a `dal:` term would leak the term's entailments into every applied ontology that did so, and would make that ontology import this one, reversing the dependency this design keeps one-way. A bespoke path vocabulary would reinvent a subset of SHACL.

## What the composite strategy generates

For a composite family, the compiler generates three operations beside the audits, each reading and writing the family's **data graph** and never the default graph, whose contents differ between stores.

| Operation | What it does |
|---|---|
| create | writes the payload and a version row, provided no version row exists and nothing of the root is already in the data graph |
| replace | deletes the delete set and writes the new payload, guarded by the version row |
| tombstone delete | deletes the delete set, keeps the version row and tombstones it, and writes a deletion revision |

The sweep is one pattern, `$root <owned path> ?s . ?s ?p ?o`, which is linear in the aggregate's size. SPARQL permits a property path in a `WHERE` clause and never in a `DELETE` or `INSERT` template, so the path binds `?s` there and the template consumes it. A path has no bounded repetition, and none is needed: recursion is `*`, an edge from child to parent is an inverse step, and SPARQL's path semantics terminate on cyclic data. The version row's subject is the root instance IRI, never a graph IRI.

## Naming a named graph

A named graph is `dal:graphIriTemplate` with `{id}` replaced by the whole root IRI, percent-encoded as SPARQL's `ENCODE_FOR_URI` does, so two roots that share a local name no longer share a graph. A template holds `{id}` exactly once, and any text after it begins with a character the encoding never emits. Across families the text before `{id}` forms an antichain, so a graph IRI names one family and one root. No standard limits an IRI's length, and a minted ASCII root grows by about a fifth when encoded.

## Concurrency

Every write to an aggregate meets every other on the root's version row. That is correct, and it conflicts more than strictly necessary: a deep edit and a root edit need not contend. Finer version rows per owned node, and edits below the root, were considered and are not built. The rules they would need are recorded in [the design sketch](../../../docs/developer/sketches/persistence-aggregate-ownership.md#11-deferred-units-and-level-operations). They return if contention on a root's row is measured, or a domain invariant needs per-level edits.

## Boundary conflicts

Three structural checks run before any SPARQL is generated, all in `persistence.validator`, and each is a named exception.

- A resource cannot be a member of one target's composite aggregate while also declaring its own non-`dal:NoBoundary` strategy.
- A class belongs to at most one composite aggregate, and an owned class is not another aggregate's root.
- A composite aggregate's closure resolves to one coherent stream identity for versioning.
