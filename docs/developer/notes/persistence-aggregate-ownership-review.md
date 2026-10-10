<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Review: persistence aggregate ownership

**Status:** review, 2026-10-10. We agreed every leaning below on 2026-10-10, so the
answers in [§6](#6-the-twelve-questions-answered) are decisions (recorded as H-D14 in the
[Track H plan](../plans/formal-methods-track-h.md#8-decisions-for-the-maintainer)). One question is new,
AO-Q13 ([§7](#7-one-new-question-ao-q13)), answered the same day: option a (H-D15). A second, AO-Q14
([§7.1](#71-a-further-question-ao-q14)), came from tracing the design through the later phases, and
was answered the same day: option a (H-D17).
**Reviews:** the exploration note [persistence-aggregate-ownership.md](persistence-aggregate-ownership.md)
(commit `8141756`, "the note" below, cited as note §n or note:line) and its spike
[`spikes/persistence-aggregate-ownership`](../../../spikes/persistence-aggregate-ownership/README.md)
("the spike"). Also read: the feedback that prompted the note, the H-D13 walkthrough in the
[H1.4a Validation Pack](../validation/FMH-H1-4a.md), the composite and named-graph templates, `boundary.py`,
`operations.py`, `validator.py`, the [persistence README](../../../ontology/persistence/README.md) and
[`tools/persistence/README.md`](../../../tools/persistence/README.md).
**Method:** reading only. Nothing was run for this review. Every claim about the code cites the line
it rests on. Where a claim is reasoned and not demonstrated, it says so.
**Feeds:** the design sketch [persistence-aggregate-ownership.md](../sketches/persistence-aggregate-ownership.md),
which turns the decisions here into a buildable specification, and the HO slices of the
[Track H plan](../plans/formal-methods-track-h.md#35-ho-aggregate-ownership).
**Working assumption (agreed 2026-10-10):** nobody uses `persistence` except the formal-methods
stream. Breaking changes to the `dal:` vocabulary, the compiler's output, the templates, the
examples and the witnesses are allowed without deprecation or migration.

## 1. Verdict

The note's direction is right. Ownership is a property of an edge in its context, an allow-list
fails safely where a deny-list does not, and removals need care under concurrency. Five things
change the conclusions:

1. A referenced entity can be deleted **today**, not only once several properties are followed
   (F1).
2. The composite replace does work proportional to the product of the root's triples and the
   members' triples (F2). TD-39, the payload in the log graph, is confirmed and is worse than the
   note says on stores that read the union of graphs (F3).
3. Several of the spike's figures depend on answers the note asks for (S1, S2), and one
   of its two closure functions checks types where the other does not (S3).
4. Named graphs do not remove the need for the classified tree. Both strategies need it (F6).
5. Today's concurrency design (D0) never loses data. Finer units reduce false conflicts and are not
   needed for correctness, so they are deferred (S6, Q5).

## 2. What was confirmed

| Claim in the note | Evidence | Verdict |
|---|---|---|
| The composite replace inserts the payload into the log graph (note §2.3, TD-39) | [cas-replace-composite-property.mustache](../../../tools/persistence/src/persistence/templates/cas-replace-composite-property.mustache): the `DELETE` removes `?root ?p1 ?o1` and `?member ?p2 ?o2` from the default graph, and the `INSERT` puts `{{{payloadTriples}}}` inside `GRAPH ?logGraph` | confirmed |
| The walk treats every `sh:node` as owned (note §4.5) | [boundary.py:84](../../../tools/persistence/src/persistence/boundary.py:84) records any property shape with `sh:node` as a node property | confirmed |
| The compiler binds the first node property (note §2.2) | [operations.py:164](../../../tools/persistence/src/persistence/operations.py:164) | confirmed |
| No create or tombstone operation for the composite strategy (note §2.2, TD-04) | only `cas-replace-composite-property` and its dataset-guard variant exist in `templates/` | confirmed |
| Several node properties are refused (note §2.2) | `CompositeBoundaryMultipleProperties`, [validator.py:149](../../../tools/persistence/src/persistence/validator.py:149) | confirmed |

## 3. The spike: what it shows and what it assumes

Only [`payload_graph.py`](../../../spikes/persistence-aggregate-ownership/payload_graph.py) runs SPARQL that
the compiler generated. [`placement.py`](../../../spikes/persistence-aggregate-ownership/placement.py) and
[`concurrency_model.py`](../../../spikes/persistence-aggregate-ownership/concurrency_model.py) are models.

**S1. The "today" closure simulates the compiler before H1.4a.** `first_property_path`
([placement.py:115](../../../spikes/persistence-aggregate-ownership/placement.py:115)) sorts the
`Placement` entry of `OWNED_TREE` and follows the first property. The real walk collects node
properties across the whole shape tree ([boundary.py:81](../../../tools/persistence/src/persistence/boundary.py:81)),
and the compiler refuses the placement shape under H1.4a because it has several node properties.
The verdict at [note:123](persistence-aggregate-ownership.md:123) and the test
`test_the_first_property_alone_reaches_only_the_tower`
([test_spike.py:31](../../../spikes/persistence-aggregate-ownership/test_spike.py:31)) describe the
pre-H1.4a compiler. Today the shape is refused.

**S2. The figures assume an answer to Q1.** `OWNED_TREE` owns `connectsPolicy`
([placement.py:85](../../../spikes/persistence-aggregate-ownership/placement.py:85)). The "12 nodes"
([note:151](persistence-aggregate-ownership.md:151)), the policy with two owners and the inbound
quote (note §4.3) all follow from that. With Q1 answered "reference" ([§6](#6-the-twelve-questions-answered)),
the closure is 11 nodes and both §4.3 examples disappear. A single-owner check is still needed in
general, and HO0 rebuilds its example from a document owned by two layers.

**S3. The two tree closures differ.** `unrolled_paths` checks the child's `rdf:type`
([placement.py:136](../../../spikes/persistence-aggregate-ownership/placement.py:136)), taking the
first type rdflib returns, in an arbitrary order. `unrolled_sparql`
([placement.py:142](../../../spikes/persistence-aggregate-ownership/placement.py:142)) checks no type.
They agree on this graph only. The SPARQL form is what a template can carry. **Decided:** the delete
set follows paths and does not check types. The path from the root carries the context, and a
wrongly typed edge is a data error that SHACL validation of the aggregate catches.

**S4. The spike has no blank nodes or skolem IRIs.** `delete_set`
([placement.py:176](../../../spikes/persistence-aggregate-ownership/placement.py:176)) takes each
member's outgoing triples, and the share `S1` is an ordinary IRI.

**S5. The concurrency model does not cover a store that serialises writers.** `overlap`
([concurrency_model.py:229](../../../spikes/persistence-aggregate-ownership/concurrency_model.py:229))
takes both snapshots before either commits, which is snapshot isolation with real concurrency. On a
store that runs writers one at a time, a removal that computes its closure inside the update's
`WHERE` sees the concurrent write, and D1's orphan cannot happen. The spike README names stores that
detect conflicts coarsely or not at all, and should name this case too.

**S6. D0 never loses data.** `test_today_every_pair_meets_on_the_root_row_including_independent_ones`
asserts that every D0 pair conflicts or is refused, and none produces an anomaly. Today's design is
correct and over-protective.

## 4. Findings against the note and the code

**F1. A referenced entity can be deleted today.** The note says "never delete a referenced entity"
holds by accident ([note:127](persistence-aggregate-ownership.md:127)) and that the `sh:node`
problem "is limited by the one-property rule" ([note:230](persistence-aggregate-ownership.md:230)).
Neither holds. A shape whose only `sh:node` is a reference, for example
`[ sh:path ex:placedBy ; sh:node ex:CustomerShape ]`, with line items declared through `sh:class`,
is accepted by H1.4a. [operations.py:164](../../../tools/persistence/src/persistence/operations.py:164)
binds `placedBy`, and the replace sweeps `$root ex:placedBy+ ?member . ?member ?p2 ?o2`, which
deletes the customer's triples. Reasoned from the code, not run. Neither the spike nor the H1.4a
tests cover it. Registered as TD-35.

**F2. The composite replace is quadratic.** The template's two independent `OPTIONAL`s
([cas-replace-composite-property.mustache:53](../../../tools/persistence/src/persistence/templates/cas-replace-composite-property.mustache:53))
join to one solution per pair of a root triple and a member triple. A root with 20 triples and
members with 2,000 triples gives 40,000 solutions for one write. Sweeping with a single pattern
whose subject ranges over the root and the members makes it linear. Reasoned from SPARQL's join
semantics, not measured. Registered as TD-36.

**F3. TD-39 is worse on stores that read the union of graphs.** The note (§2.3) and
`payload_graph.py` show rdflib, whose default graph is separate. On a store whose default graph is
the union of all graphs, reads still find the payload, so the defect hides. The next replace deletes
only from the default graph, so earlier payloads stay in the monthly log graphs, and old and new
values are read together.

**F4. Edges from child to parent are not handled.** The walk reads `sh:path` with `graph.value`
([boundary.py:81](../../../tools/persistence/src/persistence/boundary.py:81)), so an
`sh:inversePath` is recorded as a blank-node "property" and rendered as one. LATTICE's own Instrument
layer links a child to its parent (`ins:boundIn`), so this is a common shape, not an edge case.
Registered as TD-37.

**F5. Blank nodes, revised after re-reading the contract.** The first draft of this review proposed
the W3C Concise Bounded Description, following blank-node objects of every owned node. The
persistence contract already requires payloads to be skolemised, with no blank nodes
([tools/persistence/README.md:118](../../../tools/persistence/README.md:118)), so a stored
aggregate holds skolem IRIs, not blank nodes. **Decided:** a skolem IRI is an ordinary node to the
ownership walk. It is owned only if an owned edge reaches it, so an RDF list or a quantity inside an
aggregate needs owned edges in the shape (`rdf:first`, `rdf:rest`). `rdf:rest` is self-recursive,
which the path compilation of the sketch supports.

**F6. Named graphs move the classification to write time.** Note §9.1 says named graphs give
ownership "by construction" ([note:458](persistence-aggregate-ownership.md:458)). A writer still
decides which subjects go in the graph, the same owned, reference or vocabulary question, so both
strategies need one classified tree. Separately, the named-graph templates name the graph from the
root's local name (`REPLACE(STR($root), "^.*[/#]", "")`,
[cas-replace-named-graph.mustache:36](../../../tools/persistence/src/persistence/templates/cas-replace-named-graph.mustache:36)),
and `operations.py` keeps only the text of `dal:graphIriTemplate` before `{id}`. Two roots with the
same local name share a graph, and text after `{id}` is silently dropped. Registered as TD-38. The
remedy is AO-Q13.

**F7. "Set at a node" must not replace owned edges.** As written
([note:302](persistence-aggregate-ownership.md:302)), replacing a node's outgoing triples could drop
an owned edge and leave the child's closure behind. Moot for now, since level operations are
deferred with units (Q5), but recorded in the sketch for when they return.

**F8. The vocabulary guard is too absolute.** The guard proposed at
[note:212](persistence-aggregate-ownership.md:212), and `is_vocabulary`
([placement.py:101](../../../spikes/persistence-aggregate-ownership/placement.py:101)), would stop a
concept scheme's own aggregate from deleting its concepts. **Decided:** reference data may be owned
only by an aggregate that declares it owns reference data (`dal:ownsReferenceData true`).

**F9. Ambiguous register references.** [note:493](persistence-aggregate-ownership.md:493) cites
TD-26, and the register had two TD-26 rows and two TD-28 rows from parallel work. Resolved when
`main` was merged into this branch on 2026-10-10. `main`'s rows keep their numbers, since other
branches cite them. Track H's row on a missing parameter, formerly TD-26, is TD-34, and its row on
the composite payload graph, formerly TD-32 (which `main` had also assigned), is TD-39. The
`insure-o` row was fixed on `main` and is gone.

**F10. Composite aggregates rely on the default graph, against static check S-1.** Found on
2026-10-10, after the decisions of §6, while tracing the design through the later phases. The source
review's check S-1 ([persistence-fml.md §12](rdf-engine/persistence-fml.md)) requires every graph to
be named explicitly in every guard and template quad, because stores differ on the default graph.
Some read it as the union of all graphs, and DELETE without `GRAPH` behaves differently across them.
The typed IR of H2 enforces the same rule ("every pattern carries an explicit graph role",
[specification sketch §3](../sketches/formal-methods-track-h-specification.md#3-the-typed-intermediate-representation)).
Today's composite template already sweeps the default graph, so it already breaks S-1, and the design
of [the sketch §7](../sketches/persistence-aggregate-ownership.md#7-generated-operations-ho1-ho5-ho7)
would carry that into the new operations. On a union-default store, `$root ?p ?o` would also match
the root's version-row triples in the meta graph. Registered as TD-40. The remedy is AO-Q14
([§7.1](#71-a-further-question-ao-q14)).

**F11. Encoding the root is injective within a family, not across families.** Under AO-Q13's option
a, a graph IRI is `prefix + ENCODE_FOR_URI(root) + suffix`. Within one family the prefix and suffix
are fixed, so equal graph IRIs mean equal roots. Across families they need not be. If one family's
prefix is a proper prefix of another's, say `urn:g:` and `urn:g:orders`, the extra text `orders`
uses only characters the encoding also emits, so `urn:g:` plus the encoding of a root that begins
`orders` can equal `urn:g:orders` plus the encoding of another root. A suffix that begins with such a
character has the same problem at the other end. Two rules restore injectivity: the template
prefixes of all named-graph families form an antichain, and a non-empty suffix begins with a character
`ENCODE_FOR_URI` never emits, for example `/`. HO8 adds both as refusals
([sketch §9](../sketches/persistence-aggregate-ownership.md#9-named-graph-naming-ao-q13-ho8)), and
H4's IRI-template injectivity check (Z3 strings) verifies them.

## 5. The original questions

| Question | Answer |
|---|---|
| Is persistence designed properly for this? | No, for the composite strategy (F1, F2, F4, TD-03, TD-04, TD-39). The named-graph strategy is closer, but needs the same classified tree and a graph-naming rule (F6) |
| Are the patterns suitable? | Yes, applied per aggregate. What breaks is "one property-path closure is one aggregate" |
| Does an operation need to protect several levels? | Adds and edits need their own level only. A removal must reach the units below it, and creating or removing a child is a write at the parent's level. A rule that spans levels needs its own row. All of this applies only once units exist, and they are deferred (Q5) |
| Do a root edit and a deep edit contend? | They need not, and today they do. That is safe (S6) |

## 6. The twelve questions, answered

Decided 2026-10-10, by agreeing these leanings. The [design sketch](../sketches/persistence-aggregate-ownership.md)
states each one as a buildable rule.

| # | Decision | Reason |
|---|---|---|
| AO-Q1 | **A policy is a reference.** `connectsPolicy` leaves the aggregate. The binding record is owned by its layer | Asked how contract drafting answers it: a policy is a contract with its own life, outliving the placement, with endorsements, renewals, claims and retention duties |
| AO-Q2 | **Option a.** `dal:ownership` on the SHACL property shape, values `dal:Owned`, `dal:Reference`, `dal:Vocabulary`. `sh:inversePath` is supported. Context comes from the property shape's place in the tree | Keeps the structure in SHACL. Plain `sh:node` stops meaning ownership |
| AO-Q3 | **Every edge the shape declares that leads to a node must be classified**, or the compiler refuses. An edge the shape does not declare stops at run time (the edge is deleted, the node kept). The shape is authoritative, not `rdfs:domain`. The delete set follows paths without checking types (S3) | `rdfs:domain` is an inference rule, not a list of permitted properties |
| AO-Q4 | **References from outside an aggregate target its root only.** The compiler warns when a shape in the configuration points at a non-root owned class | A deleted root keeps its tombstoned version row, so a reference to it reads as deleted |
| AO-Q5 | **Units are deferred.** One version row per root (D0) stays. D2 and D4 are specified in the sketch as a future option, not built | D0 is correct (S6). Units add several sequences, lock ordering and invariant declarations |
| AO-Q6 | **One sequence and receipt stream per root** | Follows from AO-Q5 |
| AO-Q7 | **Named graphs are the recommended default for new deployments**, in documentation. The composite strategy stays. Both use the same classified tree | LATTICE is a framework and does not impose a layout |
| AO-Q8 | **Membership is computed inside the update**, from one property path compiled from the tree. No membership index | Linear in aggregate size, and correct on a single-writer store (S5) |
| AO-Q9 | **Recursion is supported.** The shape graph may contain cycles of owned edges, compiled to `*`. `BoundaryCycleError` and `dal:maxTraversalDepth` are removed | SPARQL path evaluation terminates on cyclic data. The risk is a wrongly typed edge, which validation catches |
| AO-Q10 | **Reference data is declared per class** with `dal:ReferenceData` and `dal:coversClass`. `skos:Concept` and `skos:ConceptScheme` are reference data without declaration. An owned edge to reference data is refused unless the profile declares `dal:ownsReferenceData true` (F8) | Covers non-SKOS sets such as currency codes |
| AO-Q11 | **Track H.** H-D13 is decided now as Option 1, a stop-gap whose unchecked precondition is F1. H1.4b proceeds and reports F1, F2, F4 and TD-39. H1.5 proceeds. H2 waits only for its typing of the closure, which follows HO5 | Stable labels and the gap report do not depend on the ownership design |
| AO-Q12 | **An ADR amending A78**, numbered ADR-A122 unless taken by merge time, drafted as Proposed from the sketch on 2026-10-10 | The change alters A78's decision 4 |

## 7. One new question, AO-Q13

How should a named graph be named from its root (F6)?

| Option | Graph IRI | Consequence |
|---|---|---|
| **a. Encode the whole root IRI** | `CONCAT(prefix, ENCODE_FOR_URI(STR($root)), suffix)`, with `{id}` standing for the encoded root and text after `{id}` kept | Injective by construction, since percent-encoding is injective. Uses a SPARQL built-in. Long but readable graph IRIs |
| b. Hash the root IRI | `CONCAT(prefix, SHA256(STR($root)), suffix)` | Fixed length, unreadable, injective only up to hash collisions |
| c. Keep the local name and require unique local names | as today, plus a stated rule | Nothing can check the rule at compile time, since it concerns instance IRIs |

**Decided 2026-10-10: option a** (H-D15). We accepted it on condition that an encoded graph
IRI is very unlikely to exceed a maximum length, and otherwise preferred option c. The condition holds,
for these reasons.

- **No standard sets a maximum.** RFC 3986, RFC 3987, RDF 1.1 and SPARQL 1.1 define no IRI length
  limit. Limits are implementation limits: a store may cap a term's size, and an HTTP server caps a
  URL's length, which matters only when a graph IRI travels inside a URL (for example the Graph Store
  Protocol's `?graph=` parameter). An update sent as a request body is unaffected. No store's
  specific limit was verified for this review.
- **The growth is small for minted IRIs.** `ENCODE_FOR_URI` keeps `A-Z a-z 0-9 - . _ ~` and writes
  every other UTF-8 byte as three characters. Measured with the same rule:

  | Root IRI | Length | Encoded | Factor |
  |---|---|---|---|
  | `https://data.example.org/placements/p-7f3a9c2e` | 46 | 56 | 1.22 |
  | `urn:lattice:acme:placement:01j9x8k2m4v6n8p0q2r4s6t8v0` | 53 | 61 | 1.15 |
  | an ASCII root of 220 characters with a long local part | 220 | 228 | 1.04 |
  | `https://example.org/räksmörgås/1` (non-ASCII) | 32 | 57 | 1.78 |

  The worst cases are an IRI made only of reserved ASCII characters (three times) and non-ASCII text
  (up to nine times for a three-byte character). LATTICE's identity patterns recommend ASCII
  lowercase components with a declared maximum length ([iri-identity-patterns.md §7.1](../../architecture/iri-identity-patterns.md#71-component-token-pattern)),
  so a minted root of 100 characters gives a graph IRI of roughly 120.
- **The failure modes differ.** If a store refused an over-long graph IRI, the write would fail with
  an error and nothing would be written. Option c fails silently: two roots with one local name share
  a graph, and one aggregate's replace or delete overwrites the other's. Even where length were a
  concern, c would be the worse fallback.

A per-store limit, if one is ever found, belongs in the capability record, checked against the
longest root a deployment mints. That is not built now.

### 7.1 A further question, AO-Q14

Where does a composite aggregate live (F10)?

| Option | What it means | Consequences |
|---|---|---|
| **a. A named data graph, mandatory** | a composite profile declares `dal:dataGraph <IRI>`. Every composite operation reads and writes `GRAPH {{{dataGraph}}}` | Meets S-1 and H2's explicit-graph rule, and behaves the same on every store. Data held in the default graph must be moved into a named graph once (`MOVE DEFAULT TO <g>`), which is one graph for all aggregates, not one per root. Nobody uses `persistence`, so nothing moves today |
| b. A named data graph, optional | absent means the default graph, and the compiler emits a capability requirement that the store does not read the default graph as the union | Keeps default-graph data where it is. Breaks S-1 for that case, H2's IR needs a "default graph" role, and the composite matrix cell depends on one more capability |
| c. The default graph, as the sketch says today | no change | Breaks S-1. Correct only on stores whose default graph is separate, and nothing checks that |

**Leaning:** a. It is the only option that meets S-1, it costs an adopter one `MOVE` at most, and it
makes the composite strategy "many aggregates in one named graph", the complement of the named-graph
strategy's "one graph per aggregate".

**Decided 2026-10-10: option a** (H-D17), on condition that it is ordinary practice for RDF
deployments and not an unusual choice. The condition holds.

- **S-1 is LATTICE's own rule, not only the source review's.** The
  [patterns guide §14.3](../../architecture/rdf-sparql-patterns-guide.md#143-portability-gotchas-for-guards)
  says "some stores default to a union-of-all-graphs default graph. Always name graphs explicitly in
  guards", and its pull-request checklist requires every graph in every guard and template to be
  named, with no reliance on the default graph.
- **The standards leave the default graph to the store.** SPARQL 1.1 lets a service choose what its
  default graph contains, and the SPARQL 1.1 Service Description vocabulary has a feature,
  `sd:UnionDefaultGraph`, for a service whose default graph is the merge of its named graphs.
- **Stores differ in practice**, as their documentation describes them (not re-verified for this
  review): some read the default graph as the union of all graphs by default, some offer it as an
  option, and at least one managed service stores triples written without a graph in a named graph
  of its own. Data written to the default graph therefore means different things on different stores.
- **Named graphs are the usual way to hold application data** where provenance, access control or
  partitioning matter, and the Graph Store Protocol addresses data by graph IRI. Keeping a family's
  aggregates in one named graph, named in every query, is the portable choice. Relying on the
  default graph is the less portable one.

So HO1 is unchanged: it fixes today's template, which has no data graph yet. HO3 adds
`dal:dataGraph`, mandatory on a composite profile, with a shape. HO5 adds the refusal
`MissingDataGraph` and wraps every composite pattern and payload in `GRAPH {{{dataGraph}}}`, and HO7
does the same for create and tombstone delete.

## 8. Track H, re-sequenced

The slices themselves are in the [plan](../plans/formal-methods-track-h.md#35-ho-aggregate-ownership).
In order:

1. H-D13 decided (Option 1, stop-gap). The maintainer's merge signs off H1.4a with the rest.
2. HO0: correct the note and the spike (S1, S2, S5 and the findings).
3. HO1: fix TD-39 and TD-36 in the existing composite template.
4. H1.4b and H1.5, as planned, with the additions in AO-Q11.
5. HO2: ADR-A122, drafted 2026-10-10 and Proposed. The maintainer accepts it with the work package.
6. HO3: the vocabulary. HO4: the ownership tree and the path compiler, added beside the old walk.
   HO5: the switch-over, closing TD-03, TD-35 and TD-37. HO6: the refusals and the warning. HO7:
   composite create and tombstone delete, closing TD-04.
7. HO8 (TD-38), any time after HO3. HO9: documentation and close-out.
8. H2, whose IR then types the classified tree, the payload check and the required-parameter guard
   (TD-34).

## 9. What changes in the note and the spike

Made by HO0, specified in the plan. Summarised here so a reader of the note knows what is wrong in it.

| Where | Change |
|---|---|
| note §1, §3 row "Delete the outgoing triples" (line 123) | describes the compiler before H1.4a (S1) |
| note §3 row "Never delete a referenced entity" (line 127), §4.5 (lines 230-231) | the hazard is live today (F1) |
| note §4.1 ("12 nodes"), §4.3 | Pol1 is a reference (AO-Q1). 11 nodes. Two owners shown with a shared document |
| note §9.1 | "by construction" restated (F6) |
| note §10 | TD-26 becomes TD-34 |
| note header | points here and to the sketch, and says the questions are answered |
| spike `placement.py`, `test_spike.py` | Pol1 a reference, `first_property_path` documented as pre-H1.4a, a shared-document two-owner case |
| spike README | names the single-writer case (S5) and the pre-H1.4a simulation (S1) |
