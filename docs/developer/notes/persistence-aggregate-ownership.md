<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence: aggregate ownership, deletion, updates and concurrency

**Reviewed 2026-10-10:** [persistence-aggregate-ownership-review.md](persistence-aggregate-ownership-review.md)
corrects and extends this note, and records our answers to the questions of §11. The design
is the sketch [persistence-aggregate-ownership.md](../sketches/persistence-aggregate-ownership.md).
Where this note and the review disagree, the review holds. Slice HO0 corrects the body.

**Status:** note, 2026-10-10. Exploration only. Nothing here is decided, no tool is changed, and no
ADR is proposed yet. Hypotheses are marked as such. **Prompted by:** our observation that
`persistence` handles aggregates wrongly, with a placement example of a size the order and line item
example never reached. **Experiments:** [`spikes/persistence-aggregate-ownership`](../../../spikes/persistence-aggregate-ownership/README.md),
read-only, rdflib only. **Tracks affected:** formal-methods Track H, slices H1.4b, H1.5, H2 and the
protocol models of H5 onward ([§10](#10-what-this-does-to-track-h)).

## 1. Summary

1. **The composite boundary does not fit the model.** It follows one property from the root, writes
   no create or tombstone operation, and treats `sh:node` as the sole sign of ownership. The placement
   example needs several owned relations, owned relations that differ by context, references that must
   survive, and vocabulary nodes that must never be touched ([§3](#3-fit-against-the-model)).
2. **Our instinct on ownership is right, and two refinements are proposed.** Ownership is a
   property of an edge in its context, so a flat list of properties is not enough. And listing the
   references (a deny-list) is the more ergonomic declaration but the more dangerous one, because
   forgetting an entry deletes someone else's data. The proposal is to classify every edge as owned,
   reference or vocabulary, with a compile-time check that none is left unclassified ([§4](#4-ownership)).
3. **Vocabulary nodes can be detected only in part.** `skos:Concept` typing and `skos:inScheme` find
   them in data, and a declared property range finds them at compile time. Neither finds an ordinary
   entity such as a carrier. That needs configuration ([§4.4](#44-can-vocabulary-nodes-be-detected)).
4. **SHACL is the right vehicle for the structure, and needs one addition.** A shape tree is already
   context sensitive. But `sh:node` also appears on references in validation shapes, so reading it as
   ownership is unsafe. An explicit ownership marker on the property shape fixes that ([§4.5](#45-should-the-boundary-be-a-shacl-shape)).
5. **Our two concurrency claims hold for additive edits and fail for removals.** Edits at
   different levels need not contend, and today they do (a false conflict by design). But a removal of
   a subtree conflicts with a concurrent write beneath it, and under snapshot isolation nothing makes
   them meet unless the design makes them meet. The experiment loses data in exactly that case
   ([§7](#7-concurrency)).
6. **A cross-level invariant overrides the "immediate level only" rule** for the writers it covers
   ([§7.4](#74-cross-level-invariants)).
7. **Two defects found on the way.** The composite replace writes the new payload to the receipt log
   graph and not to the graph it deleted from ([§2.3](#23-a-defect-the-composite-replace-writes-the-payload-to-the-log-graph)).
   And the composite boundary has no create or tombstone-delete (TD-04, known).
8. **Recommendation.** Hold H-D13, H1.4b and H1.5. Keep the H1.4a refusal as a stop-gap. Settle the
   questions in [§11](#11-questions-for-the-maintainer) before H2 types the closure.

## 2. What persistence does today

### 2.1 The three strategies

[ADR-A78](../../architecture/decisions/ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md)
and [sketch §4](../sketches/persistence-profile-substrate.md) give an aggregate three mechanisms.

| Strategy | Where the aggregate is | Operations generated |
|---|---|---|
| `NamedGraphBoundary` | one graph per root, named by `dal:graphIriTemplate` | create, replace, tombstone delete |
| `CompositePropertyBoundary` | the root plus nodes found by walking a SHACL shape | replace, and a bootstrap row if the version row is pre-created |
| `NoBoundary` | none | value-guard compare and set |

Every strategy keeps one version row per root in a metadata graph (`pat:epoch`, `pat:seq`,
`pat:head`, and `pat:deleted` as the tombstone). A write is a guarded `DELETE/INSERT ... WHERE` that
checks the expected sequence, so two writers on one root collide on one statement
([guide ch. 17](../../architecture/rdf-sparql-patterns-guide.md#chapter-17--what-separating-metadata-from-payload-buys-and-what-it-does-not)).
A delete does not remove the row. It sets the tombstone, so counters never restart
([guide §24.1](../../architecture/rdf-sparql-patterns-guide.md#241-tombstones-f10)).

### 2.2 How the composite boundary works

`tools/persistence/src/persistence/boundary.py` walks `sh:property`/`sh:node` from the boundary
shape and records which paths were reached (`composite_properties`) and which led to another node
(`node_properties`). `operations.py` binds the first node property, in path order, into
`cas-replace-composite-property.mustache`, whose sweep is

```sparql
OPTIONAL { $root ?p1 ?o1 }
OPTIONAL { $root {{{compositeProperty}}}+ ?member . ?member ?p2 ?o2 }
```

and whose `DELETE` removes `?root ?p1 ?o1` and `?member ?p2 ?o2`. The caller supplies the whole new
payload, so every write is a replace of the root and of everything reached. The version row is
keyed by the root, and nothing else has one.

Related facts, all from the code and documents named.

- The sketch's own query used `ex:lineItem*` with a depth bound of the form `{0,8}`. SPARQL 1.1 has
  no bounded repetition, so the compile-time depth and the run-time path can differ
  ([persistence-fml §8.4](rdf-engine/persistence-fml.md)). The template relies on the compile-time
  cycle check alone.
- `validator.py` refuses a class that is both a composite member and a boundary in its own right
  (`BoundaryConflict`, nested boundaries). It does not, as far as I can read, compare two
  composite roots whose shapes reach the same class, which persistence-fml §8.4 named as an unstated
  precondition (closures are disjoint).
- Several node properties are refused (`CompositeBoundaryMultipleProperties`, H1.4a), because a
  replace that follows one of them leaves the others' members behind. This is a stop-gap and not a
  capability.
- There is no create-if-absent and no tombstone delete for this strategy (TD-04). A composite
  aggregate has no operation that deletes it as a whole.

### 2.3 A defect: the composite replace writes the payload to the log graph

The template inserts the caller's payload into `GRAPH ?logGraph { ... }`, which is the monthly
receipt graph (`urn:g:txlog/YYYY-MM`). The sweep deletes from the default graph. After one replace
on rdflib, the old `status "open"` is gone from the default graph and the new `status "paid"` is
found only in `urn:g:txlog/2026-10`. A reader of the default graph sees the aggregate disappear.
The named-graph template writes the payload to `GRAPH ?g`, the aggregate's own graph, which is
what the composite one should do for its destination. Run `spikes/persistence-aggregate-ownership/payload_graph.py`.
This went unseen because the H1.4a tests inspect what is left behind, and not where the new
payload lands. Proposed as a technical debt row, not fixed here.

## 3. Fit against the model

The model, in our terms. The aggregate root is the entry point. Every object property
assertion inside the aggregate is part of it, so deleting the root deletes the assertions from the
root to its children. Whether a child node is deleted too depends on whether the aggregate owns it.
Three kinds of node are reachable.

| Kind | Example | On delete of the root |
|---|---|---|
| Owned | contacted market record, tower, layer, binding, share | the node's triples go |
| Referenced entity | client, carrier (`Axa`), the shared library wording | the edge to it goes, the node stays |
| Vocabulary | market type, policy status | the edge to it goes, the node stays, and no configuration may say otherwise |

For any node in scope, every datatype property is deleted, every object property assertion is
deleted, and the node at the far end is deleted only if owned.

| Requirement | Today | Verdict |
|---|---|---|
| Delete the outgoing triples of the root and of every owned node | the root, and members reached along one property | partial. On the placement graph the update reaches only the tower node itself, since `definedProgramme` sorts first and `hasLayer` is not followed ([spike](../../../spikes/persistence-aggregate-ownership/README.md)) |
| Follow several owned relations | refused since H1.4a | not supported |
| Ownership differs by context | the shape tree can express it, the walk flattens it to a list of paths, the template follows one | not supported |
| Never delete a vocabulary node | nothing | not supported, and not guarded |
| Never delete a referenced entity | holds only because only the bound property is followed | holds by accident |
| One owner per node | class-level refusal for nested boundaries only | partial |
| Delete the aggregate as a whole | none (TD-04) | not supported |
| Handle references into the aggregate from outside | nothing | not supported |
| Independent edits at different levels do not contend | one version row per root, whole-replace payload | not supported, by design |
| New payload lands where the old one was removed | lands in the log graph | defect ([§2.3](#23-a-defect-the-composite-replace-writes-the-payload-to-the-log-graph)) |

So the answer to "is persistence designed properly for this" is no, for the composite strategy.
The named-graph strategy is a different case and is taken up in [§9](#9-alternative-designs).

## 4. Ownership

### 4.1 Ownership belongs to an edge in its context

Our example has the same word doing two jobs. In the spike graph, `attachment` is owned from
a `Layer` (a layer slip) and a reference from a `LayerContractBinding` (library wording shared across
placements). A flat list of owned properties cannot hold both. It takes the shared wording with the
tower (the spike's flat alternation deletes `DocShared`), or leaves the layer slip behind.

The same holds one level up. A `Policy` is owned by its binding in the example, yet a policy often has its
own lifecycle. Whether `connectsPolicy` is an owned edge or a reference to
a separate aggregate is a modelling question the sketch does not answer ([§11](#11-questions-for-the-maintainer), Q1).

The structure that fits is a tree from class to the edges it owns, which is what a SHACL shape tree
is. The spike's `OWNED_TREE` is that tree, and walking it gives the expected 12 nodes. The same tree
written as SPARQL sequence paths (a `UNION` of `placement/definedProgramme/hasLayer/...`) returns the
same 12. The tree form needs no `+` and so no cycle problem, at the price of query size growing with
the number of paths.

### 4.2 An allow-list or a deny-list

Our guess is that it is easier to name the external references than every owned node.
That is likely true as authoring effort, and the two failure modes differ in cost.

| | Forget an entry in an allow-list of owned edges | Forget an entry in a deny-list of references |
|---|---|---|
| Effect on a delete | owned data is left behind | shared data is deleted |
| Recoverable | yes, orphans can be found by an audit and removed | no |
| Visible | an audit finds them | nothing flags it |
| Spike | the flat list and the tree both leave nothing important behind | forgetting `contactedMarket` adds `Axa` and `Chubb` to the delete set |

With the deny-list, a new property added to an owned class is owned by default, so a future
modelling change silently widens deletes. The spike also shows a forgotten vocabulary link reaching
the concept and then its scheme (15 nodes).

**Hypothesis.** Require both lists and make them exhaustive. Every object property that can leave an
owned class is classified as `owned`, `reference` or `vocabulary`, and the compiler refuses a
boundary with an unclassified property. This keeps the allow-list's safety and gives the authoring
we want, since "these are external" is still a short statement. The class-to-property
relation can come from the shape's `sh:property` entries and from the applied ontology's domains. The
exhaustiveness check would need a decision on which source is authoritative (Q3).

### 4.3 One owner per node, and references into the aggregate

Two statements are checkable.

- **Single owner (compile time).** For every pair of roots, the classes owned in their trees are
  disjoint. This is the check persistence-fml §8.4 recommended, and it can be a refusal.
- **Single owner (run time).** A node is in at most one closure. The spike builds a second placement
  whose binding connects `Pol1` and finds it in both closures. Without a check, the later writer's
  replace sweeps `Pol1` while the other aggregate still points at it, and the version rows differ, so
  the two writers never collide.

Separately, an owned node can be referenced from outside, as with a quote that points at `Pol1`.
Deleting the placement removes `Pol1`'s triples and leaves the quote's edge dangling. The spike lists
both outside references. What a delete does about them is a policy choice. Options are refuse,
accept the dangling edge, or require the referencing aggregate to drop it first. Q4.

### 4.4 Can vocabulary nodes be detected

Three signals exist, with different reach.

| Signal | Available | Finds |
|---|---|---|
| Node typed `skos:Concept`, or `skos:inScheme` present | at run time, in data | concepts and schemes, and nothing else |
| Declared range of the property is a concept class, for example `sh:class skos:Concept` or an `rdfs:range` that is a `skos:Concept` subclass | at compile time, in the ontology and shapes | every edge to a concept, without reading data |
| Node lives in a vocabulary graph | at run time, if the deployment separates them | whatever the deployment placed there |

The Vocabulary layer already builds on SKOS (`voc:ConceptScheme` is a `skos:ConceptScheme`), so the
first two signals cover LATTICE's own vocabularies. They do not cover `Axa`, `Chubb` or the client,
which are ordinary entities and not vocabulary. Our own example makes that distinction:
carrier types are vocabulary, carriers are entities. The latter must be classified `reference` by
hand.

**Hypothesis.** Use the compile-time signal to refuse an `owned` classification on any edge whose
range is a concept class, and use the run-time signal as a guard on the computed delete set, refusing
if it contains a concept or scheme. The spike's guard catches both forgotten vocabulary links in a
deny-list and has no effect on `Axa`, as it should not. Reference data that is not SKOS (currency
codes as individuals, say) is outside both signals. Q10.

### 4.5 Should the boundary be a SHACL shape

Yes for the structure, and the shape needs one addition. The reasons for a shape are the ones the
sketch gave ([§4.1](../sketches/persistence-profile-substrate.md)). It points at domain properties by
IRI, adds nothing to the domain ontology, and a shape tree is already a tree from class to the edges
that leave it, which is the structure [§4.1](#41-ownership-belongs-to-an-edge-in-its-context) needs. The
alternative, a bespoke path vocabulary, would reinvent a subset of SHACL.

The addition is needed because of what the compiler reads today. `boundary.py` treats every
`sh:node` as a child to sweep. In SHACL, `sh:node` says a value must conform to a shape. It is
common on references in validation shapes, for example `forClient` with `sh:node ex:ClientShape`
so the client is checked. If an adopter points `dal:boundaryShape` at such a shape, which the sketch
explicitly allows ([§4.4](../sketches/persistence-profile-substrate.md)), the client becomes a
member and the replace sweeps the client's triples. Today this is limited by the one-property rule,
and it stops being limited the moment several properties are followed.

| Option | Description | Consequence |
|---|---|---|
| a. Annotate the property shape | `sh:property [ sh:path ex:attachment ; sh:node ex:DocShape ; dal:ownership dal:Owned ]`, with `dal:Reference` and `dal:Vocabulary` as the other values | structure stays in SHACL, ownership is explicit, the shape remains valid SHACL because extra triples are allowed |
| b. A dedicated boundary shape | a shape used only for the boundary, with `sh:node` meaning owned | no annotation, but a validation shape can no longer double as the boundary, which the sketch valued |
| c. Keep `sh:node` as ownership | as today | unsafe, as above |

Recommended as a hypothesis, option a. A shape also cannot say "every property except these", so the
deny-list reading of our suggestion has no natural SHACL form. This is a further reason to
keep the allow-list as the definition and the exhaustiveness check as the aid.

## 5. Deleting

### 5.1 What a delete removes

For the root and every owned node, all outgoing triples. That covers datatype properties, edges to
owned children, and edges to references and vocabulary. The nodes at the ends of reference and
vocabulary edges are not subjects of any removed triple, so they stay. The spike's delete set for the
placement contains `P forClient C` and no triple with `C`, `Axa`, `TypeCarrier` or `PolBound` as
subject.

Triples whose subject is outside and whose object is inside (inbound edges, [§4.3](#43-one-owner-per-node-and-references-into-the-aggregate))
are not in this set, which is why they need a policy.

### 5.2 How the owned set is computed

| Approach | How | Cost | Weakness |
|---|---|---|---|
| A. Flat alternation | `$root (p1\|p2\|...)+ ?m` | one query | cannot express context ([§4.1](#41-ownership-belongs-to-an-edge-in-its-context)) |
| B. Per-class sequence paths | a `UNION` of explicit paths from the tree | one query, size grows with the tree | recursion needs `*` and a bound the language cannot state |
| C. Typed walk by the caller or SPI | read the closure, then delete that exact set | several round trips | the set can go stale between read and write, so it needs the version row to guard it |
| D. Membership index | at write time, record `node pat:ownedBy root` (or in the meta graph) | O(1) lookup per delete, extra triples per node | the index can drift, and every owned insert must maintain it |
| E. Graph per aggregate | members are the graph's contents | no computation | needs data laid out in graphs ([§9](#9-alternative-designs)) |

D deserves attention beyond cost. If `ownedBy` is a single-valued property per node, two roots
claiming one node make two writers insert different values of a functional property, and
statement-level conflict detection can turn the single-owner rule into a run-time guarantee. This is
the key-claim pattern ([guide ch. 6](../../architecture/rdf-sparql-patterns-guide.md#chapter-6--p1-and-p2-the-key-claim-registry-and-the-guarded-write))
applied to ownership. It costs write amplification and a second source of truth, which the guide's
finding F4 warned about for the etag and sequence.

### 5.3 Tombstone and purge

The version row survives a delete ([guide §24.1](../../architecture/rdf-sparql-patterns-guide.md#241-tombstones-f10)).
For the composite strategy a delete would need to: check the expected sequence, remove the owned
triples, set `pat:deleted`, and write a receipt. None of that exists (TD-04). Erasure of personal
data is a different procedure and can include references, so it should not reuse this path
([guide §24.5](../../architecture/rdf-sparql-patterns-guide.md#245-erasure-of-personal-data)).

## 6. Updating

Today an update is a replace of the root's closure with a caller-supplied payload. In the placement
model that has four consequences.

1. **Every edit rewrites the tower.** Adding one policy to one binding deletes and reinserts every
   owned triple. The receipt model records assert and retract graphs ([guide ch. 20](../../architecture/rdf-sparql-patterns-guide.md#chapter-20--receipts-patches-or-snapshots-f9)),
   so each receipt is the size of the aggregate.
2. **The payload must be the whole owned set.** An omitted owned node is deleted. That is how a
   removal is expressed, and also how a stale client silently removes nodes it never loaded.
3. **The payload must stay inside the boundary.** A payload with triples about `Axa` writes outside
   the aggregate, since the sweep never deletes `Axa`'s triples and the insert adds to them. A payload
   check is needed, such as "every payload subject is the root or an owned node". It is a run-time
   check, and the IR of H2 is the place to state it.
4. **A replace needs a rule for dropped owned edges.** If the new payload drops `L1 hasPolicyBinding
   LCB3`, then `LCB3` and everything it owns must go too. Whole-replace gets this by deleting the
   whole closure and writing the new one. A level operation has to compute it.

Our view is that deeper levels do not matter to an update. I think that holds for edits that
add or change values at one level, and the proposal below is built on it. A level operation would be

- **set at a node**, replacing that node's own outgoing triples, with children left alone,
- **add child**, inserting an owned edge and the child's triples,
- **remove child**, deleting the edge and the child's closure (the delete of [§5](#5-deleting) applied to a subtree).

Remove child is where depth matters again, since it takes everything below. [§7](#7-concurrency)
shows why that matters for concurrency. Level operations also shrink the receipts to the size of the
change, which suits the assert and retract model.

## 7. Concurrency

### 7.1 Two relations that the word "aggregate" joins

Domain-driven design uses the aggregate for two things. One is the lifecycle, meaning what is created
and deleted together. The other is the consistency boundary, meaning what a single transaction
protects. The sketch and the code join them. The root's version row protects the whole closure.

Our model separates them. The tower is owned by the placement for deletion. Whether the
tower must be consistent with the placement under concurrent edits is a separate question, answered
by which invariants span them. The rest of this section keeps the two apart. The ownership tree
decides what a delete takes. A set of **units**, nodes that carry a version row, decides what a
writer contends with. Units sit inside the ownership tree and are chosen by the author.

### 7.2 What our claims need

> only the immediate level needs to be protected, and an edit at the root level need not contend with
> an edit at a lower level.

Under snapshot isolation with first-committer-wins at statement level (capabilities
`detectsWriteWriteConflict` and `statementLevelConflictDetection`), two transactions conflict only if
they write the same statement. A version row is the statement they are made to share. So the claim
reduces to which operations should share a row.

- Two additive or value edits at different units share nothing and need not conflict. The claim holds.
- A removal of a subtree reads, in its snapshot, the set of nodes below. A concurrent writer adds a
  triple about a node in that set. Their write sets do not overlap, both commit, and a triple about a
  removed node remains. The claim fails here unless something forces a shared statement.

### 7.3 The experiment

[`concurrency_model.py`](../../../spikes/persistence-aggregate-ownership/concurrency_model.py) models
two overlapping writers, each taking a snapshot before either commits, in both commit orders, and
reports the worse. The aggregate has units `P`, `L1`, `L2` and `B1` (`L1`'s binding), and five
disciplines.

| Discipline | Version rows | Removal | Writers |
|---|---|---|---|
| D0 | one at the root (today) | bumps the root row | bump the root row |
| D1 | one per unit | bumps its own and its parent's row, sets its tombstone | bump their own row |
| D2 | as D1 | also bumps and tombstones every unit below | as D1 |
| D3 | as D1 | as D1 | also bump every ancestor |
| D4 | as D2 | as D2 | as D2, plus bump a row for a declared cross-level invariant |

Result. "False" marks a conflict between operations that are logically independent.

| Pair | D0 | D1 | D2 | D3 | D4 |
|---|---|---|---|---|---|
| root edit and deep edit | conflict (false) | both commit | both commit | conflict (false) | both commit |
| deep edits, different branches | conflict (false) | both commit | both commit | conflict (false) | both commit |
| deep edits, same unit | conflict | conflict | conflict | conflict | conflict |
| remove `L1` and edit in `L2` | conflict (false) | both commit | both commit | conflict (false) | both commit |
| remove `L1` and edit below `L1` | conflict | **orphan data** | conflict | conflict | conflict |
| delete root and deep edit | conflict | **orphan data** | conflict | conflict | conflict |
| remove `L1` and add a binding under `L1` | conflict | conflict | conflict | conflict | conflict |
| two bindings with a limit of three | conflict | **limit broken** | **limit broken** | conflict | conflict |

Reading it.

- **D0 is today's design.** Every pair meets on the root row, so the independent pairs conflict. We
  were right that this contention is unnecessary. It follows from whole-replace and one row, not
  from the data.
- **D1 is our proposal taken literally.** The independent pairs commit. The removal pairs lose
  data, because nothing makes a removal and a writer beneath it share a statement.
- **D3 repairs D1 by making every pair meet at the root.** That recreates D0's false conflicts, so it
  defeats the purpose.
- **D2 repairs D1 where it fails and nowhere else.** The removal writes to the rows of the units below
  it, so a writer beneath meets it on its own row. Independent pairs stay free.
- **D4 adds a row for a cross-level invariant** ([§7.4](#74-cross-level-invariants)).

A removal under D2 writes one row per unit below, so its cost is the number of units and not the
number of nodes. A unit created concurrently with a removal would be missing from the removal's
snapshot. The model handles it by having the creator also bump its parent's row, which the removal
bumps too, and the "add a binding under `L1`" row is that case. So the rule is: **creating
or removing a child unit is a write at the parent's level.** That is the immediate-level rule we
described, applied to structure.

### 7.4 Cross-level invariants

Some rules span units. In the placement, shares across the layers of a tower summing to one, or a
programme limit at least equal to the sum of its layer limits, are of this kind. A writer at one layer
reads the other layers to check the rule and writes only its own. Under snapshot isolation that is
write skew. Two such writers each pass the check and together break the rule (the last row of the
table, D1 and D2).

The pattern for this is already in the guide, which calls it materialising the write conflict (P3).
The invariant gets a row, and each writer the invariant covers bumps it (D4). Only those writers
contend. D4's other pairs still commit freely.

So the claim "only the immediate level" is accurate for operations that carry no cross-level
invariant, and a covered writer's read set is wider than its level. This is a property of the domain
model and cannot be derived from the ontology. The author has to declare the invariants and the
levels they read. Q5.

### 7.5 Dependence on the store

D1 to D4 all rely on conflict detection on the shared statement, so the capability record's claim is
load-bearing and the TCK must verify it (guide QP5). On a store that detects conflicts per graph or
page, as guide F12 warns, the unit rows should live in separate graphs or the conflicts coarsen
(more false conflicts, still correct). On a serializable store, D1 would suffice, since the removal's
read of the subtree would conflict with the concurrent write. The model does not distinguish those
cases and cannot show them.

### 7.6 Effect on ordering and receipts

With version rows per unit, `pat:seq` is per unit and so are the receipt chains. There is no single
sequence for the placement. A reader who wants the placement as of a moment reads several streams,
and the as-of read needs a rule for that. The guide's cross-aggregate section
([§19.6](../../architecture/rdf-sparql-patterns-guide.md#196-multi-aggregate-writes)) already asks
for lock-ordering discipline whenever a write bumps more than one row, and a removal under D2 does.
Q6.

## 8. Does the pattern set suit the model

| Pattern | Verdict |
|---|---|
| Version row with epoch, sequence and head | suits, and moves from "per root" to "per unit" |
| Guarded `DELETE/INSERT ... WHERE` | suits, with guards on the unit's row |
| Tombstone, so counters never restart | suits, one per unit, and a removed unit keeps its row |
| Whole-graph or whole-closure replace | does not suit deep aggregates ([§6](#6-updating)), and is the source of D0's false conflicts |
| Receipts with asserts and retracts graphs | suits, and improves under level operations |
| Key-claim registry for uniqueness | unaffected, claims are scoped to a class, though a unit moves under a new root only by an explicit operation |
| Dense per-stream sequence and gap scan | needs a decision on stream identity per unit (Q6) |
| Value-guard compare and set (`NoBoundary`) | suits attribute-level state changes inside a unit |
| Property-path sweep of a closure | does not suit, because of context ([§4.1](#41-ownership-belongs-to-an-edge-in-its-context)) and the missing bounded repetition |

The patterns hold at the level of a unit. What does not hold is the assumption that a unit equals an
aggregate equals a closure.

## 9. Alternative designs

These differ in where ownership comes from. They are not exclusive of the concurrency structure in
[§7](#7-concurrency), which applies to any of them.

### 9.1 Named-graph placement as ownership

Each owned node's triples live in the aggregate's graph. A delete clears the graph. Referenced
entities and vocabulary live elsewhere, so they cannot be deleted by accident, and no closure is
computed. `NamedGraphBoundary` already has create, replace and tombstone delete, and its
payload lands where the delete happens.

For the placement example the units become graphs: one for the placement, one per tower or layer as
the author chooses. Prefix nesting, which H1.1 refuses for scopes that share a class, is then the
natural shape of the layout, so the antichain check would need to distinguish a graph that is
deliberately nested under another from an overlap.

| Pro | Con |
|---|---|
| ownership by construction, no closure query, vocabulary and references outside by placement | graph proliferation, the cost sketch §4.1 names |
| existing operations cover it | an adopter with one large shared graph has to move data |
| delete is one operation | a node in two graphs is a duplicate and not a share, so the single-owner rule becomes a data layout rule that nothing enforces |

### 9.2 Declared ownership tree over a shared graph

The design of [§4](#4-ownership) to [§7](#7-concurrency) on the composite strategy: classified shape
tree, delete set by sequence paths or typed walk, units with version rows, the vocabulary guard and
the single-owner check. This is the work that makes the composite strategy fit the model.

### 9.3 Ownership recorded as data

The membership index of [§5.2](#52-how-the-owned-set-is-computed), approach D. The shape tree is then
a validator of the index and not the thing a delete executes. It trades write cost and a second
source of truth for a delete that does not depend on the ontology's shape at all, and for a run-time
single-owner guarantee.

### 9.4 Leave the composite strategy as it is and add a rule

Refuse any composite boundary deeper than one level, and send deep aggregates to named graphs. It is
the cheapest option and it keeps the strategy honest about what it can do. It does not serve an
adopter who cannot repartition.

**Hypothesis on a combination.** Named graphs are the default for deep aggregates, as the sketch
already says. The composite strategy is rebuilt as 9.2, with 9.3 as an option when delete cost or the
run-time single-owner guarantee matters. Q7 and Q8 decide this.

## 10. What this does to Track H

| Item | Effect |
|---|---|
| H1.4a refusal | stays as a stop-gap. It stops a silent partial delete today, and is superseded if 9.2 is adopted |
| H-D13 (what the compiler binds, and how) | mostly moot. The "first property" binding disappears under 9.2, and what remains is how the closure is stated in the IR |
| H1.4b (declaration and implementation gap report) | hold. It would report today's closure as the implementation, and the gap list should include ownership, units and the vocabulary guard |
| H1.5 (stable labels for compiled profiles) | hold. The compiled profile's shape changes if boundaries carry classified edges and units |
| H2 (typed IR) | the closure becomes a tree of classified edges and the units a set of nodes in it. The payload check ([§6](#6-updating)) and the required-parameter guard of TD-26 belong in the same IR |
| H5 and later (protocol models, Isabelle theories) | the models of the version row and of conflict detection should be extended with units, the removal rule and the invariant row. The spike's table is a small candidate for the first model |
| Static checks | new ones follow: every edge classified, no `owned` edge to a concept class, owned trees disjoint across roots |
| Witnesses | each new refusal and warning needs a fixture, per the H1.2 harness |
| Technical debt | add the payload-graph defect ([§2.3](#23-a-defect-the-composite-replace-writes-the-payload-to-the-log-graph)) |

## 11. Questions for the maintainer

1. **`Pol1`.** In the placement, is a policy owned by its binding, or a referenced aggregate with its
   own lifecycle? The answer changes what a tower delete takes, and it recurs for every
   "connects to a thing that also exists on its own" edge.
2. **Declaration surface.** Annotated SHACL shape (option a of [§4.5](#45-should-the-boundary-be-a-shacl-shape)),
   a dedicated boundary shape (b), or something else?
3. **Exhaustive classification.** Is it acceptable that every edge leaving an owned class must be
   classified as owned, reference or vocabulary, with an unclassified edge a compile error? Which source says what
   edges exist, the shape or the applied ontology's domains?
4. **Inbound references.** When something outside points at an owned node, should a delete refuse,
   leave the edge dangling, or require it to be cleared first? Per class or global?
5. **Units and invariants.** Which nodes in the placement need their own version row, and which
   rules span levels (shares summing to one, programme limits)? Can the list be made now, or does it
   come from real usage?
6. **Streams.** Should receipts and sequences be per unit, per root, or both? What is the as-of read
   of a whole placement to return?
7. **Role of named graphs.** Should named-graph placement be the recommended default for deep
   aggregates, with the composite strategy kept for adopters who cannot repartition?
8. **Computed or recorded membership.** Are expected aggregate sizes small enough for sequence paths
   (a placement of a few hundred nodes), or is a membership index worth its cost?
9. **Recursion.** Do real structures recurse (a layer containing layers, a clause amending a clause)?
   If so, closure needs `*` and the cycle check has to become a runtime guard.
10. **Reference data that is not SKOS.** Are there such sets (currency codes, country codes as
    individuals) that need the same protection as concepts?
11. **Track H.** Do you agree to hold H-D13, H1.4b and H1.5 until the above is settled, and to keep
    H1.4a as it stands?
12. **ADR.** The sketch and ADR-A78 describe the composite strategy as it is built. A change of this
    size probably needs an ADR amending A78. Do you want that drafted once Q1 to Q8 are answered?

## Appendix. What the experiments do and do not show

The spike prints the closure comparison, the two-writer table and the payload location. Seventeen
checks in `test_spike.py` assert the figures quoted above. The limits are in the
[spike README](../../../spikes/persistence-aggregate-ownership/README.md). In short, the concurrency
table is a model of a rule and not a store, it covers pairs and not larger sets of writers, and every
experiment runs on rdflib alone. The closure experiments use one hand-built graph, so they show that
a strategy can fail, and nothing about how often.
