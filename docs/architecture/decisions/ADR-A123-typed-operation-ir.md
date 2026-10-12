<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A123: A typed operation IR for the persistence compiler

**Status:** Accepted, 2026-10-10, with the ADR-A79 addendum applied the same day, and two addenda of its own (2026-10-12)
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

