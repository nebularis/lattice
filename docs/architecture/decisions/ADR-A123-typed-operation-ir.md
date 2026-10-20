<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A123: A typed operation IR for the persistence compiler

**Status:** Accepted, 2026-10-10, with the ADR-A79 addendum applied the same day, and eight addenda of its own (2026-10-12 to 2026-10-20)
**Date:** 2026-10-10
**Supersedes:** parts of [ADR-A79](ADR-A79-persistence-compiler-toolchain.md), listed under Decision 10. ADR-A79 stays Accepted for the rest
**Related:** [ADR-A78](ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md),
[ADR-A122](ADR-A122-aggregate-ownership.md) (decision 6 assigns the payload check to this work),
[ADR-A-FM4](ADR-A-FM4-persistence-formal-methods-home-and-scope.md),
[the design brief](../../developer/sketches/formal-methods-track-h-typed-ir.md) (normative detail, with the
options and their consequences),
[the specification sketch §3](../../developer/sketches/formal-methods-track-h-specification.md#3-the-typed-intermediate-representation)
(the hazard table),
[Track H plan §4](../../developer/plans/formal-methods-track-h.md#4-h2-h3-the-typed-ir-and-the-specification-registry)

## Context

`tools/persistence` turns a compiled profile into SPARQL by rendering 28 Mustache templates with
`chevron` (ADR-A79 decisions 1 and 3). Compile-time values reach a template only as encoded terms, so
configuration cannot inject SPARQL (decision 4). Three things are left outside that boundary.

- **The structure of the query is text.** The hazards of a guarded update (an unbound variable in an
  `INSERT` template, a blank node, a pattern in the default graph, a value comparison on a position that
  must compare terms, a property path in a template, `NOW()` in a guard) are found after the fact by the
  static checks S-3 and S-4 and by the witness harness. Nothing prevents them.
- **The payload is trusted text.** A caller fills `payloadTriples` with SPARQL text and computes
  `$requestDigest` separately from canonical N-Triples. Nothing checks that the two agree, that the text
  holds no blank node, that a literal cannot break out of the template, or that every subject belongs to the
  aggregate being written.
- **A missing request-time variable is silently unbound.** An update can then write part of a record (TD-34).

A third problem is cost. The composite replace builds its payload once per stored triple of the aggregate,
which is quadratic in the aggregate's size (TD-42). It is correct under every store's evaluation order for that
reason, so it is kept as it is for now.

## Decision

1. **Each operation is a typed value.** A frozen `Operation` in a new module `persistence.ir` is built by one
   builder per operation id, and one renderer produces its SPARQL. The renderer refuses what the types forbid.
   The type rules are in the table below.
2. **Type rules.** Each closes a hazard that is found after the fact today.

   | Part | Rule | Closes |
   |---|---|---|
   | parameters | `Param(name, kind, required)`, with kind one of `Iri`, `Long`, `String`, `LangString`, `Position`, `Digest`, `Payload`, `RegistryList` | a missing or misspelt parameter (H-D11) |
   | compile-time constants | the encoders of `terms.py`, unchanged | injection from configuration |
   | patterns | every triple pattern carries a graph role (data, meta, transaction, log bucket, event bucket, keys, registry). There is no default-graph constructor | S-1, TD-40 |
   | terms | a variable, a parameter or a constant. No blank-node constructor exists | a retry that is not a no-op |
   | property paths | allowed only in a `WHERE` pattern | a path in a template |
   | variables in `DELETE` and `INSERT` | tagged `Bound` or `OptionalAllowed`. An untagged variable is refused | S-3, H-D12 |
   | guards | `TermGuard` or `ValueGuard`. A position is declared term-invariant or value-compared, and the wrong guard is refused | term and value divergence |
   | clock | `Now()` appears only in a `BIND` for a receipt field or a bucket choice, never in a guard | `NOW()` in a guard |
   | required parameters | a guard generated from the parameter list (decision 5) | TD-34, H-D12 |

3. **Read and write sets are derived.** The renderer walks every pattern and yields the graphs and subjects an
   operation reads (its `WHERE`, with a composite closure read through its owned path) and writes (its `DELETE`
   and `INSERT`). They are not declared by hand.
4. **The compiled profile declares, and holds no SPARQL.** ADR-A79 decision 1 stands. `compile` emits, per
   operation, the parameter declarations, the derived read and write sets and the payload contract. They name
   **logical resources** (the aggregate with its members, its version row, the transaction claim, the receipt, a
   key claim, a log bucket), not SPARQL graph roles. The builders map each logical resource to a graph role.
   A relational realisation reads the same declarations and can be compared with this one operation by operation
   (H2-Q5, H2-Q6). The `OwnershipTree` stays in `persistence.boundary`, and the IR holds a reference to it.
5. **The required-parameter guard runs twice.** It is generated from the parameter list as `FILTER(BOUND($p))` in
   its own group at the top of `WHERE`, `{ FILTER(...) }`, with a `DATATYPE` test for `Long`, `Position` and `Digest`, so a missing parameter becomes
   no write for every caller. The Python caller also refuses a missing or mistyped parameter before sending and
   says why, since a guard that fails reads as a lost race (H2-Q4). The guard needs its own group because a `FILTER`
   applies to the solutions of its whole group, after the group's patterns have matched. As a top-level `FILTER`, a
   missing `$root` would be bound from the data by a pattern such as `$root pat:seq $expectedSeq`, and the guard would
   pass for every aggregate (found in the H2.1 review, 2026-10-10, before acceptance).
6. **The payload is typed, as ground triples bounded by the boundary shape (PL-B).** A `Payload` is a set of
   subject, predicate and object terms passed through the encoders. It renders as sorted canonical N-Triples,
   and the same lines feed `$requestDigest`. Every subject must be the root or be reached from the root within
   the payload by the owned edges of the boundary shape, in their declared direction. The slot in the rendered
   query is still written `{{{payloadTriples}}}`, so an unrendered slot is a syntax error. Its declared type is
   `dal:GroundNTriples`. `logGraphs` becomes a `RegistryList` of encoded IRIs (H2-Q1).
   - The store cannot check the payload, because a guard in an update's `WHERE` sees stored data and a property
     path cannot walk `VALUES` rows. The check runs in the caller. A caller using the Python package gets it
     inside `Payload`. A caller in another language runs a generated `payload-check` query over a local graph.
   - PL-B refuses no predicate the shape does not declare (H2-Q3).
   - A named-graph family with payload operations and no `dal:boundaryShape` gets PL-A only. The compiler reports
     an informational diagnostic by default, and a warning when `compile` is run with a warning option. The
     diagnostic model gains an `INFO` severity (H2-Q2). No `dal:` term is added for it.
7. **A composite replace keeps its current evaluation form for now.** The payload sits in the `INSERT` template,
   which is filled once per sweep solution. That is quadratic and correct on every store (TD-42). Two linear
   forms exist, and each needs a store property: request atomicity (`atomicUpdateRequest`) for two operations in
   one request, and the specification's evaluation order (`snapshotUpdateSemantics`) for one operation with the
   payload in a `UNION` branch. Both fields join the capability record of the Track H sketch, three-valued, with
   a probe each. Choosing a form per store is a `compile` selection made once that record exists, and is not
   decided here.
8. **Mustache is retired.** The templates, `render.py` and the `chevron` dependency are removed in the last slice
   of H2. Until then each ported operation is checked against its template by an equivalence harness that
   compares normalised SPARQL algebra for exact equality, with the parameter guard removed from the value and
   checked on its own. A port changes nothing, and a change ports nothing.
9. **The audit surface changes.** A template was auditable by inspection as a text file. The builder plus a
   golden `.rq` file per operation, checked in and compared on every run, replace it. An adopter who rendered the
   templates with their own Mustache library runs `instantiate` once. Its `.rq` output is plain SPARQL.
10. **What this supersedes in ADR-A79.**
    - decision 3's Mustache layer. Compile-time and request-time substitution stay apart, now as the constants
      and parameters of one typed value
    - decision 4's renderer clause. The encoders stay and the renderer refuses by type, over IR values instead
      of a Mustache context. The payload enters the injection boundary, which ADR-A79 left outside it
    - the consequence that templates stay auditable by inspection (decision 9 above)
    - `dal:templatePath` in decision 1's compiled profile. `dal:templateId` and `dal:templateVersion` stay as
      the identity of a builder

    Decisions 1 (otherwise), 2, 5 and 6 of ADR-A79 stand. The injection corpus of decision 5 runs over the
    builders.

## Consequences

- The hazards of the specification sketch become refusals by type, and S-3 and S-4 pass by construction over the
  renderer's output. S-3 then reads the parameter declarations instead of the `$name` convention.
- `compile` gains declarations and a payload contract, so the persistence vocabulary and its shapes change
  (planned as 0.4.0 in slice H2.7, with release tags owed).
- A caller in another language has two payload duties, PL-A by following the contract and PL-B by running the
  generated check. Nothing forces the second. A published client SDK that performs both is sketched in
  [persistence-client-sdk.md](../../developer/sketches/persistence-client-sdk.md) and is not planned.
- The logical resources are designed with one realisation in hand. Their fit with `lattice-sql.md` §9 is a
  paper check in slice H2.6. Two realisations generated from one contract share any misreading of it, so the
  models of H5 remain the independent oracle.
- Nothing outside `tools/persistence` and its tests calls `instantiate` or fills the slots, so no
  compatibility is owed (H-D14).
- Sharding (TD-06, TD-41), infrastructure graph names (TD-05), PL-C (SHACL conformance of the payload), the
  staged in-store payload check and the specification registry (H3) are not decided here.

## The ADR-A79 addendum

Applied to [ADR-A79](ADR-A79-persistence-compiler-toolchain.md) on 2026-10-10, when this ADR was accepted.

## Addendum, 2026-10-12: parameter guards are optional, and are type tests

Decided by the maintainer after the H2.1 review ([FMH-H2-1](../../developer/validation/FMH-H2-1.md#review-2026-10-10)).
It amends decisions 5 and 8.

1. **Guards are on by default and can be turned off.** Input checking normally belongs in the access layer, not the
   store. The compiler writes the guard by default, which shows what a correctly checked query has to do. A `compile`
   flag, `--no-parameter-guards`, leaves them out for a caller whose own code checks every parameter: LATTICE's own
   caller library, or the deployment's application code. The compiled profile records the choice, so a caller can
   tell whose job the checks are, and `compile` reports guards that are off as an `INFO` diagnostic naming that
   obligation. With guards off, a request that leaves out `$root` can write every aggregate whose version row
   matches, and preventing it is the caller's job.
2. **A guard is a type test per parameter, not `BOUND`.** `isIRI($p)` for `Iri`, `DATATYPE($p) = xsd:long` for `Long`
   and `Position`, `DATATYPE($p) = xsd:string` for `Digest` and `String`, `LANG($p) != ""` for `LangString`. An
   unbound parameter makes its test an error, which fails the filter, so the test also catches a missing parameter.
   Unlike `BOUND`, it still parses when a caller substitutes the parameter's text, which a caller with no
   initial-binding API must do. It also catches a parameter of the wrong type, such as an IRI bound to a literal.
3. **The guard stays in its own group at the top of `WHERE`**, as decision 5 says. It runs once per request, so it
   costs about nothing, where a top-level `FILTER` ran once per solution (measured on rdflib, FMH-H2-1).
4. **An operation carries the derived guard or an explicit "guards off" value**, never none. `check` refuses an
   operation without one, so a builder cannot drop it by accident. The equivalence harness of decision 8 renders with
   guards off, not with the guard removed from the value.

Where each part lands: the builders take the flag from H2.2, the `dal:` term that records it comes with the H2.7
vocabulary, and the `INFO` diagnostic, its witness and the Python caller's own check come with H2.8.

## Addendum, 2026-10-12: who names a named graph

Decided by the maintainer while planning slice H2.3 (Track H plan §4.1, H2.3-Q2).

1. **By default the query names the graph.** A named-graph operation computes `?g` from `$root` by the rule of
   [ADR-A122](ADR-A122-aggregate-ownership.md) decision 8, and a pattern `GRAPH ?g` inside an inner group, such as the
   replace's `OPTIONAL` sweep, is accepted when an earlier or enclosing group binds `?g` in every solution. SPARQL joins
   the inner group's solutions on `?g`, so the result holds only that graph's triples. A store that evaluates the inner
   group literally, before the join, reads every graph to get there. That cost is a store property, measured in H2.4.
2. **A caller may choose to name it.** An override, `caller`, declares `$g` of kind `Iri` and writes `GRAPH $g`, so a
   caller that substitutes text gives the store a constant graph. With guards on, the guard group checks `$g` against
   decision 8's rule, so the injectivity of graph names still holds in the query. With guards off as well, the caller
   alone must name the graph correctly. The choice is recorded in the compiled profile with the guards term (H2.7).

This leaves ADR-A122 decision 8's rule unchanged and moves its enforcement to the caller only when the caller turns off
both the query's naming and its guards.

## Addendum, 2026-10-12: the path is the IR's reference to the tree, and the IR is not stored yet

Decided by the maintainer while planning slice H2.4 (Track H plan §4.2, H2.4-Q1, and the status record's H2-Q7).

1. **Decision 4's "the IR holds a reference to it" is corrected.** The IR is built by the builders inside `instantiate`
   (FMH-H2-2, decision 2), which reads only the compiled profile (ADR-A79 decision 1), and the profile holds the owned path,
   not the tree (H2-Q5). So the compiled path is the IR's reference to the `OwnershipTree`. A composite operation reads it
   with `Bindings.path`, and its read set marks the sweep a closure read with the path's text. The tree stays in
   `persistence.boundary`, where `compile`, H4's language check (C10) and H5's models use it. The sentence was written in the
   typed IR brief without checking where the IR is built.
2. **H2-Q5 stands, and a stored IR is decided with PDD-06's ADR.** The IR published, if any, is the semantic SPARQL IR that
   PDD-06 proposes, so that one contract is published once. Until then the rules SI-1 to SI-6 of the
   [typed IR sketch §9.4](../../developer/sketches/formal-methods-track-h-typed-ir.md#94-rules-that-keep-a-clean-stored-ir-possible)
   keep a clean stored IR possible, and §9.5 lists what that ADR must decide. One rule does not hold today: a `Path` holds the
   path's rendered text, not its structure.

## Addendum, 2026-10-13: the datatype test calibrates itself to the store

Decided by the maintainer after slice H2.4b (FMH-H2-4b, decision 1, option D). It amends the first addendum's point 2.

1. **The test for `Long` and `Position` is `DATATYPE($p) = DATATYPE("0"^^xsd:long)`**, not `DATATYPE($p) = xsd:long`. It compares
   the parameter's datatype with what the store makes of an `xsd:long` constant. Oxigraph 0.5.11 stores every integer-derived literal as
   `xsd:integer`, in expressions as in data, so the first addendum's test could never pass there and every guarded write was refused
   ([TSD-07](../triple-store-discovery.md#tsd-07-numeric-datatypes-are-not-kept-by-oxigraph)).
2. **On a store that keeps datatypes it is the same test as before.** On rdflib only an `xsd:long` passes, so an `xsd:integer` epoch,
   which a bootstrap or create would store and no later guarded replace would match, is still refused. On a store that turns every
   integer into `xsd:integer`, any integer passes, and the mismatch cannot arise. A missing or non-numeric parameter is refused on both.
3. **No option and no capability field.** The test adapts by evaluating in the store. It rests on the store treating a constant, a
   parameter and a stored value alike, which probe P5 asserts per store. A store that fails P5 needs a decision of its own.
4. The tests for `Iri`, `Digest`, `String`, `LangString` and `IriOrLiteral` are unchanged. `Digest` and `String` keep
   `DATATYPE($p) = xsd:string`, since no probed store turns a simple literal into another datatype, and P5 asserts it per store.
5. **The Python caller's own check is strict and store-independent** (decided 2026-10-13, NQ6 of the
   [design review](../../developer/notes/track-h-feedback.md)): a `Long` or `Position` parameter must be exactly `xsd:long` on any store.
   The SPARQL guard is the store-calibrated backstop, whose acceptance set differs by store, which H5's capability record carries as
   whether a store normalises numeric datatypes. Built with the caller check in H2.8.

## Addendum, 2026-10-13: queries, sub-selects and two parameter kinds

Decided by the maintainer on the [design review](../../developer/notes/track-h-feedback.md) of slices H2.5 and H2.6 (Track H plan §4.3,
H2.5-Q1 and Q2). It extends decision 2.

1. **One `Select` value serves a query operation and a sub-select**, as a `SubSelect` pattern element. The fragment is closed: projection
   of variables and aggregates, `GROUP BY` over variables, and `HAVING`.
2. **Four further type rules**, each refused with a named rule because the form is illegal SPARQL or fails silently: an aggregate outside a
   projection or `HAVING`, a projected variable neither grouped nor aggregated, a `HAVING` term neither a group key nor an aggregate, and an
   inner variable used outside a sub-select without being projected.
3. **A projected item is bound in every solution only as the plan's boundness table says.** `COUNT` always is. `MIN`, `MAX`, `SAMPLE`,
   `SUM`, `AVG` and `GROUP_CONCAT` are only with an explicit `GROUP BY` and a bound argument that cannot raise a type error. No aggregate
   but `COUNT` is, without a `GROUP BY`.
4. **`ORDER BY`, `LIMIT`, `OFFSET`, `DISTINCT` inside a sub-select, and nested sub-selects are outside the fragment** for now. They are
   limits, not type rules, each lifted with an engine test when a template needs it.
5. **Two parameter kinds join decision 2's list**: `IriOrLiteral` (FMH-H2-2 decision 1), guarded by `isIRI($p) || isLiteral($p)`, and
   `Literal`, guarded by `isLiteral($p) && LANG($p) = ""`, which accepts any timestamp datatype and refuses an IRI or a missing value.


## Addendum, 2026-10-14: the event slots and the digest parts (accepted 2026-10-20)

Drafted in slice H2.6b (Track H plan §4.6, H-D30 and H-D32) for the maintainer to accept. It extends decision 2 and the H2.4a addendum on
request-time slots.

1. **Two request-time slots join `payloadTriples` and `logGraphs`.** `{{{eventRows}}}` holds the rows of
   `VALUES (?event ?eventType ?opSeq ?occurredAt)` and `{{{eventTriples}}}` holds the data written beside each event. The IR has a `Rows`
   slot kind and a `RowValues` element, which binds its variables. The checker does not restrict where it is placed (review note,
   2026-10-14). Like every
   slot, neither is parameter-guarded.
2. **An append takes its events from the rows.** One request still steps the seq once and writes one receipt and one claim. Each event's
   `pat:revision` is that receipt, so its position is (epoch, seq, `opSeq`). Every solution writes the same version row, claim and receipt,
   which makes the batch independent of the order in which a store applies solutions (TSD-01). `append-event` is builder version 2.
3. **The digest of an append has an event part.** One part per slot, in a fixed order. The event part has two sources, the rows slot and the
   triples slot, and covers each row's type, `pat:opSeq` and `pat:occurredAt` triples with the event triples. It leaves out `pat:revision`,
   which the store mints. This slice declares the part in the contract. H2.8 computes it.
4. **`compile` warns `ReceiptModelNotHonoured`** for a target whose receipt model is `dal:PatchLog` or `dal:SnapshotPerRevision`, as it warns
   for `ShardingNotHonoured` (TD-46).


## Addendum, 2026-10-20: the write disciplines and `append-version` (accepted 2026-10-20)

Drafted in slice H2.6c (Track H plan §4.9) for the maintainer to accept or change. It is decided at our leanings, with the history and
versioning sketch's VH-Q1 to VH-Q6, and extends the builders of decision 1.

1. **`dal:writeDiscipline` selects the write of a family.** `dal:InPlace` (absent means this) keeps every operation as it was.
   `dal:AppendVersions` selects `bootstrap-version-row` and `append-version`. `dal:AppendRecords` selects the append form of H2.6b. The
   discipline is a resolved dimension like any other, so every compiled profile now carries it.
2. **`append-version` is a builder with a dataset-guard variant,** kind `AppendVersion`, version 1. One update guards the identity's version
   row at the expected seq and the transaction claim, inserts the new version's own triples from the payload slot, links
   it to the version the row names as current with `pat:previousVersion`, never `fnd:supersededBy`, which the domain asserts under its
   own rule (amended 2026-10-20, the code follows), moves the row's seq, head and current version
   (`pat:currentVersion`), writes the receipt, and links the version to its receipt with `pat:revision`. It reads and writes the data graph
   but never deletes from it, so it has no sweep. Its parameters are those of the compare-and-set and `$newVersion`. It imports nothing
   from Foundation (ADR-A78).
3. **Which families.** A composite family, and a family with no boundary that declares a `dal:dataGraph`, under `dal:Optimistic`. Any other
   is refused with `AppendVersionsUnsupported`. A named-graph family, which would append one graph per version named from the version, is
   not built. A family that appends versions has no create, replace or tombstone.
4. **`compile` warns `VersionedClassWrittenInPlace`** when a target class is a subclass of `fnd:Version` in the loaded graphs and its
   discipline is `dal:InPlace`.
5. **`CompositeBoundaryReceiptConflict` does not apply to a family that appends versions or records,** where the history is in the data
   (VH-Q5). It still refuses `dal:InPlace` with `dal:ReceiptOnly`.
6. **The contract gains one operation kind,** `AppendVersion`. Its resources are the version row, the version (the aggregate resource, in
   the data graph), the receipt and the claim. Its digest parts are the usual four, with the payload as the content part.


## Addendum, 2026-10-20: the subjects of an event append (accepted 2026-10-20)

This addendum extends this ADR's addendum of 2026-10-14 on the event slots. It adds a rule for what an append of events may write, using the
identity grammar of [ADR-A51](ADR-A51-iri-and-identity-policy.md) (its Rule 8 and its event IRI). It changes no IRI grammar.

### Context

An append of events carries rows of `(event, type, opSeq, occurredAt)` and an `eventTriples` slot of further triples written beside them. The
slot is free text to the store. Nothing stops its triples from having an existing aggregate as their subject, so an append, whose only
protection is the transaction claim, could write into an aggregate's data without that aggregate's version guard. An event is an immutable
occurrence ([iri-identity-patterns](../iri-identity-patterns.md) §5.10). It records what happened, and it does not change the thing it concerns.

### Decision

1. **Every subject of the event triples is an event of the batch, or a node minted under one event's IRI.** Such a node uses the
   parent-relative key `{eventIri}/part/{encodedImmutableKey}` or the parent-local ordinal `{eventIri}/part/{ordinal}` of
   [iri-identity-patterns](../iri-identity-patterns.md) §5.4. The parent is always the event, and the key or ordinal is immutable within it.
2. **An event may name any other resource as an object.** For example it names the aggregate it concerns. It never names one as a subject.
   An event therefore cannot describe an aggregate, and the event slot cannot write into an aggregate's data.
3. **The caller library checks the rule before sending.** The payload check tests each subject of the event triples against the batch's event
   IRIs and the prefix `{eventIri}/part/`. A deployment may tighten the rule with SHACL shapes per event type, for example to fix which parts an
   event type may have. The store is not involved.
4. **Blank nodes in event triples are skolemised under the event IRI,** as ADR-A51 already requires, with the parent-local ordinal where no key
   exists. An existing event whose parts are blank nodes is skolemised the same way before it is accepted.

### Options considered

| Option | Verdict |
|---|---|
| (a) Any node reachable from an event may be a subject | Rejected. An event could reach an existing aggregate and describe it, which writes into the aggregate outside its guard. |
| (b) A shape per event type that lists the allowed subjects | Kept as the optional tightening of point 3. It cannot be the base rule, because a deployment would have to write a shape before an append is safe. |
| (c) Subjects are the batch's events and nodes minted under them | Chosen. It needs no shape and no store change. |

### Consequences

- Adopters mint event parts under the event. Moving a part to another event gives a new IRI, as for any parent-relative part
  (§5.4). Events are immutable, so this does not arise in practice.
- The check is a string prefix test plus a subject test. It needs no store change and no query.
- An event cannot be corrected by an append that describes it from outside. A correction is a new event that names the first as an object.
- Existing events with blank-node parts are skolemised under the event IRI, which ADR-A51 already requires.
- A reader may rely on the rule. Every triple of an event graph is about an event or a part of one.
