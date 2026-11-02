<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: writing only what changed, as a persistence mode

**Unit ID:** `persistence-delta-replace` (DR)
**Prefix:** DR
**Unit type:** multi-slice unit, validation gate per slice
**Status:** planned 2026-11-02 from the [sketch](../sketches/persistence-delta-replace.md), DR-Q1 to DR-Q11 decided. The studio line built its own delta replace on 2026-11-01 (§9), and the two lines merged on 2026-11-02 with this plan's design as the base
**Status record:** [persistence-delta-replace.md](../status/persistence-delta-replace.md)
**Depends on:** slice H2.12 of track H ([plan §4.20](formal-methods-track-h.md#420-h212-the-rows-replace-selected-by-capability-planned-2026-11-01)), whose rows form, encoding and diagnostics this unit builds on. Built on the branch `claude/persistence-delta-replace`, off `claude/persistence-linear-replace`, and merged into `realign/config-authoring-studio`
**Touches:** `ontology/persistence/` (the README as the literate source, its spec, shapes, examples and expected profiles), `tools/persistence` (the compiler), `packages/persistence/python` and `packages/persistence/java` (the callers), `benchmark/persistence-replace-forms`, `contracts/config-studio/persistence-profile.ttl`, ADR-A123

## 1. Goal and acceptance

A family written in place under optimistic concurrency replaces an aggregate by writing the triples that changed, guarded on the version row, unless its profile chose the whole-state replace. The generated delta replace is linear in the size of the change on every store, the two caller libraries build and check it, and the studio's writer moves its parts and documents back onto the generated operation, which closes TD-136. Accepted when every slice's Validation Pack passes, the conformance run passes on every engine, and the maintainer has re-approved the expected profiles that change.

## 2. Decisions, from the sketch

| Decided | Answer |
|---|---|
| how a profile chooses (DR-Q1) | a new axis, `dal:replaceEncoding`, with the values `dal:ChangedTriples` and `dal:WholeState`, declared beside `dal:membershipEncoding` and resolved like any dimension. One replace per family, no choice per call. Beside it, for imports and repairs, `replace-whole` under its own id with the whole-state builder, and `load-whole` (DR-Q10) |
| the default (DR-Q2) | `dal:ChangedTriples` under `dal:Optimistic`, with `dal:WholeState` named where it is wanted. A family with no guard writes whole state unconditionally, and a declared `dal:ChangedTriples` there is refused until a merge model is named. Every in-place family under `dal:Optimistic` regenerates onto the delta, and every vector and expectation of a replace with it |
| the digest (DR-Q3) | the delta alone, the asserted lines sorted then the retracted lines sorted, as the add and del parts the digest already has, with no payload part. It identifies the change, and the receipt's previous sequence pins it to a state. (c) is a family's opt-in, `dal:recordsStateDigest`, which records the digest of the state each write leaves on the version row, with an audit read that finds a graph changed outside the family's operations at O(N) a write |
| a family without a patch log (DR-Q4) | takes the same two slots, `assertTriples` and `retractTriples`, and writes them to the aggregate only |
| the slot encoding (DR-Q5) | `dal:GroundNTriples`. A delta replace has no sweep, so its `WHERE` yields one solution and its template is filled once, which is linear on every store, rdflib and RDF4J included. The rows form, `dal:providesSnapshotUpdateSemantics` and `dal:replaceForm` bear on `dal:WholeState` families alone |
| the form on a delta family (DR-Q6) | `dal:replaceForm` declared on a `dal:ChangedTriples` family is warned `ReplaceFormNotApplicable` |
| the composite boundary (DR-Q7) | the caller checks the next state it holds against the boundary shape, with `payload-check` or the library's check, and sends the delta. A caller obligation, written as a standard with the six of TD-139 |
| where the delta is computed (DR-Q9) | both, a patch where the client has one and the whole state otherwise, from which the writer computes the delta |
| the bulk load (DR-Q10) | `load-whole`, many aggregates' whole states in one request, each guarded on its own row, a create where there is none and `replace-whole` where there is one, composed by the caller |
| a client's patch (DR-Q11) | two Turtle documents, what is added and what is removed, with the base revision in a header, and RDF Patch later if a client writes it |
| the slices (DR-Q8) | three. DR-1 and DR-2 here, DR-3 in the studio agent's session with a brief, and the studio's deployment declares `dal:providesSnapshotUpdateSemantics` in DR-3 and not before |

## 3. Design, settled here

**The dimension.** `replaceEncoding` is a dimension with no baseline default, since its default depends on the concurrency profile. `compile` takes the declared value, and otherwise `dal:ChangedTriples` for an optimistic family and `dal:WholeState` for any other, and the resolved dimension in the compiled profile records a declared value and its winner, or no value, as `replaceForm` does. The operation's `dal:templateId` says which replace was selected either way.

**The builders.** `cas-replace-named-graph-delta` and `cas-replace-composite-property-delta`, each with the receipt variants its family has and a dataset-guard variant, ten in all, at version 1. Their `WHERE` is the template replace's without the sweep, so the guard alone, one solution. Their `DELETE` removes the retracted triples from the aggregate's graph through the `retractTriples` slot, and the version row's triples, and their `INSERT` writes the asserted triples through the `assertTriples` slot, under a patch log the two slots again into the add and del graphs the receipt names, the row, the claim and the receipt. A delta's deletions and insertions are disjoint by construction, so the order a store applies them in does not matter. There is no `payloadTriples` slot. Create and tombstone do not change.

**The IR.** A `PayloadSlot` may stand in a `DELETE` template, recorded as a delete access of the aggregate. The checker refused it until now because no operation deleted a caller's triples, and the delta replace is the operation that does. ADR-A123 gains an addendum.

**The contract.** The operation kind is `dal:DeltaReplace`, a new member of `dal:OperationKind`, so a caller, a relational realisation and a model know that the request carries a change and not a state. The payload contract names `assertTriples` as its parameter, so that the shape over a payload contract holds and the family keeps its `payload-check`, with the root and the boundary shape as before. A caller runs the bound and shape checks over the next state it holds and not over the slot, which the kind tells it (DR-Q7). The digest contract has the kind, target and expected-sequence parts and the add and del parts, and no payload part, which is the one digest whose payload part is dropped, since no existing operation has add and del parts without a payload or an event.

**The selection.** Under `dal:ChangedTriples` the replace is the delta builder of the family, and `dal:replaceForm` and the capability field are not consulted. Under `dal:WholeState` the selection of H2.12 stands, the rows form by capability or opt-in and the template form otherwise.

**The diagnostics.** `ReplaceEncodingUnknown` refuses a value outside the two. `ChangedTriplesNeedsOptimistic` refuses a declared `dal:ChangedTriples` on a family whose concurrency is not `dal:Optimistic`, since a delta applied to a state its caller never read merges triple by triple, which is a model of concurrency with no name yet. `ReplaceEncodingNotApplicable` warns an encoding declared on a family that has no replace of an aggregate to encode, an append discipline, an append-only concurrency or a value-guarded family. `ReplaceFormNotApplicable` now also fires for a form declared on a delta family.

**The callers.** `OperationKind.DeltaReplace` in both libraries. The check refuses a delta whose two slots overlap (`DeltaOverlap`) or are both empty (`EmptyDelta`, STD-309), and, given the next state, an asserted triple that is not in it, a retracted triple that is, and a next state outside the bound, through the checks the whole payload has today. Without the next state the check says so in its result and the standard names the obligation. The digest follows the contract, so no library code is special to the kind beyond the omitted payload part.

**The studio, in the meantime.** `contracts/config-studio/persistence-profile.ttl` declares `dal:WholeState` on each of its six profiles in DR-1, with the reason, so that the studio's generated operations do not change under the new default before its writer moves in DR-3, which removes the declarations.

## 4. Slices

| Slice | What | Done when | Estimate |
|---|---|---|---|
| DR-1 | the vocabulary, the dimension, the ten builders, the kind, the selection, the diagnostics, the example `replace-encoding.ttl` and its expected profile, the witnesses, the goldens, the regenerated expected profiles, the benchmark's delta form, the studio's interim declaration, and the Persistence README's narrative and diagrams for the encoding and the form together | `mise run check:persistence` passes, the delta replace leaves the right state on rdflib, Oxigraph and Jena for both families under each receipt model and guard, and the README explains and draws both choices | 350k tokens |
| DR-2 | both caller libraries, their checks and vectors, the conformance run, the compiler README, and the seven caller obligations as standards (TD-139 and DR-Q7) | both library suites and `check:persistence-conformance` pass, and the obligations are register entries | 250k tokens |
| DR-4 | carried over from the studio line at the merge (§9): `replace-whole` beside the delta replace, `load-whole`, the opt-in state digest with `record-state-digest` and `state-digest-audit`, `compose` and `state_digest` in both libraries | `mise run check:persistence` and `check:persistence-conformance` pass with the studio line's tests of the three ported onto this design | the merge |
| DR-3 | the studio's writer moves its parts and documents onto the generated delta replace, the interim declarations go, the deployment declares `dal:providesSnapshotUpdateSemantics`, and TD-136 closes | the studio's integration and benchmark runs pass with no hand-written replace | 150k tokens, in the studio agent's session |

## 5. The README deliverables of DR-1

The maintainer asked on 2026-11-02 that every change of H2.12 and of this unit reach the Persistence README as narrative and diagrams, and not only as section 6 entries, so a user understands how the options work and how they behave at runtime. DR-1 writes a section 5.6.12, "Replace encoding", holding the question, the two encodings side by side, a data-flow diagram from the caller's two states to the graphs each encoding writes, a sequence diagram of one save under each encoding on a store, showing the sweep's one solution per stored triple against the delta's one solution, a decision diagram of how `compile` selects the replace from the encoding, the form, the capability field and the opt-in, a timeline of a stale delta refused by the guard and retried, a cost table at stated sizes, the caller's obligations, and what works best when. Section 5.6.2's paragraph on the form of the replace then points at it, the running case of section 5.13 shows the delta replace the project family now gets, and section 5.14's costs gain the choice.

## 6. Validation

One Validation Pack per slice, `DR-1` and `DR-2` in [docs/developer/validation/persistence-delta-replace.md](../validation/persistence-delta-replace.md), DR-3's in the studio unit's. DR-1's one command is `mise run check:persistence`, and its conformance is `mise run check:persistence-conformance` on the three engines. Every expected profile that changes is listed for re-approval, and most do, since the default moves every optimistic in-place family onto the delta.

## 7. Deliberate non-coverage

A merge model for a delta under a family with no guard. Healing a graph changed outside the family's operations, which is a whole replace under an operation of its own. A delta of a `dal:NoBoundary` family, whose value guard already writes one property. RDF4J, beyond the observation that the delta has no path (TSD-Q36).

## 8. DR-3, the brief for the studio slice

For the studio agent's session, on the studio's branch once this unit's branch is in it. Done when the studio's integration and benchmark runs pass with no hand-written replace and TD-136 is closed.

**The scene.** Since DR-1 the generated `cas-replace` of every optimistic family is the delta replace, kind `dal:DeltaReplace`, whose contract declares `assertTriples` and `retractTriples` and no `payloadTriples`. The studio's six profiles in `contracts/config-studio/persistence-profile.ttl` are pinned to `dal:WholeState` so that nothing changed under the studio before this slice. The writer, `platform/config-studio-core/.../store/StudioOperations.java`, has `replace`, which fills the contract's payload parameters from what it is given and runs the caller check, and `replaceDelta`, which derives a delta write for a part or a document from the generated whole-state replace's syntax tree (TD-136). Since DR-2 the Java caller library's `CallerCheck` refuses an overlapping or empty delta and, given `Options.nextState(payload)`, checks the next state against the bound and the delta against it.

**Steps.**

1. Remove the six `dal:replaceEncoding dal:WholeState` declarations and their comment from `contracts/config-studio/persistence-profile.ttl`, and add a `dal:CapabilitySpec` for the studio's deployment declaring `dal:providesCas dal:Linearizable` and `dal:providesSnapshotUpdateSemantics true`, which is true of Fuseki over TDB2 (TSD-66) and is what a family that later declares `dal:WholeState` would select the rows form by. Recompile and check which operations each family now has: every family's `cas-replace` is a delta builder.
2. Delete `replaceDelta` and its sweep helpers, and route a part's and a document's save through `replace`, which already fills `assertTriples` and `retractTriples` from the delta it is given and ignores a `payloadTriples` the contract no longer declares. Pass the next state to the check, `CallerCheck.check(contract, values, Options.none().nextState(payload))`, so the boundary is checked over the state and not the slot (obligation 8). Keep the digest as the contract says, which is now over the delta alone, so the receipts of saves made before this slice were digested over the whole state and later ones over the change, which is fine, since a digest is compared only with the request that made it.
3. Make sure a save whose delta is empty is not sent and answers "already at this sequence" (STD-309). The writer computes the delta already, so this is a guard before `replace`.
4. Run the studio's unit tests, `mise run studio:integration`, and the `studio-api` benchmark against the head before the slice, and record the save times in the Validation Pack beside the 121 ms the hand-written delta gave at 3,000 triples.
5. Close TD-136 naming this slice, and add the release note to the studio's own notes if it keeps any. ADR-A149 decision 12's addendum, which recorded the hand-written replace, gains a dated line saying the generated delta replace replaced it.

**Not in this slice.** The projection refresh a publish waits for, which is `projection-maintenance`. Any change to LATTICE's compiler or libraries, which this unit's DR-1 and DR-2 made.

## 9. The studio line's slices

The studio's branch built a delta replace of its own on 2026-11-01, from DR-Q1 to DR-Q7 as they stood then, in four slices recorded in the Validation Packs [DR-1](../validation/DR-1.md), [DR-2](../validation/DR-2.md), [DR-3](../validation/DR-3.md) and [DR-4](../validation/DR-4.md). Its vocabulary and its generated delta SPARQL were the same as this plan's. It used the kind `dal:Replace` for the delta, which this plan's `dal:DeltaReplace` replaces. Its DR-2 built what DR-4 above carries over, and its DR-4 built what DR-3 above asks, the writer on the generated delta replace with the service taking a patch, At the merge the writer reads the kind, checks the next state, withholds a save that changes nothing (STD-309), and the studio's profile keeps the delta for its parts and documents and the whole state for its four small families, so TD-136 closed. DR-3's first step remains, a `dal:CapabilitySpec` for the studio's deployment declaring `dal:providesSnapshotUpdateSemantics`, which would give the four whole-state families the rows form and needs the writer to fill rows slots.
