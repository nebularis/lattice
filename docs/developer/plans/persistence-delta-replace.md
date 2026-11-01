<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: writing only what changed, as a persistence mode

**Unit ID:** `persistence-delta-replace` (DR)
**Unit type:** multi-slice unit, validation gate per slice
**Status:** planned 2026-10-31, DR-Q1 to DR-Q7 answered
**Sketch:** [persistence-delta-replace.md](../sketches/persistence-delta-replace.md)
**Status record:** [persistence-delta-replace.md](../status/persistence-delta-replace.md)
**ADRs:** ADR-A123 (the typed operation IR) gains an addendum, ADR-A149 decision 12's addendum is closed by DR4
**Depends on:** nothing unmerged. The linear replace investigation (branch `claude/persistence-linear-replace`, LR-Q1 to LR-Q3) is not a dependency, see §4

## 1. Goal and acceptance

Under `dal:Optimistic` a family's replace writes only the triples that changed, guarded on the version row, and a whole replace is written only where a profile names `dal:WholeState`. Both callers fill the delta, the conformance run checks it on every engine we have, and the studio's writer runs the generated delta replace instead of its hand-written one. Accepted when every slice's Validation Pack passes and `mise run check:persistence-conformance` passes on the branch.

## 2. Decisions

The sketch's answers, each a rule a slice obeys:

| Answer | Rule |
|---|---|
| DR-Q1 (a) | `dal:ReplaceEncoding` on a `dal:InPlace` family's write discipline, `dal:ChangedTriples` or `dal:WholeState`, one replace a family, as `dal:membershipEncoding` is chosen today (`model.py`, `resolver.py`, `validator.py`, `operations.py`) |
| DR-Q2 (a) | `dal:ChangedTriples` is the default under `dal:Optimistic`. Under `dal:ProvidedConcurrency` and `dal:LockingConcurrency` the default is `dal:WholeState`, and the validator refuses `dal:ChangedTriples` there. The merge model of (c) is sketched in §5 of the sketch and not built |
| DR-Q3 (a), (c) as an option | the request digest of a delta replace is over the delta, `assertTriples` then `retractTriples`. A family may opt into a digest of the state the write leaves, recorded on the version row |
| DR-Q4 (a) | the delta slots are `assertTriples` and `retractTriples` whatever the receipt model. A family that feeds an incremental materialisation spanning aggregates keeps a `dal:PatchLog`, a check of the projection maintenance unit |
| DR-Q5 (c), DR-Q7 (b) | the studio's service accepts a patch, a Turtle document of what is added, one of what is removed and the base revision in a header, or the whole state, from which the writer computes the delta |
| DR-Q6 (a) | `load-whole` writes many aggregates' whole states in one request, each guarded on its own row, a create where there is none and a whole replace where there is one |

## 3. Slices

| Slice | What | Done when | Estimate |
|---|---|---|---|
| DR1 | the vocabulary (`dal:ReplaceEncoding`, `dal:ChangedTriples`, `dal:WholeState`, `dal:replaceEncoding`) with its shape, the resolver's default, the validator's refusal, and the builders `cas-replace-named-graph-delta` and `cas-replace-composite-property-delta` with their dataset-guard and receipt variants, the digest over the delta, goldens and expected profiles regenerated | a delta replace on rdflib and Oxigraph leaves the state a whole replace leaves, writes no quad of an unchanged triple, and does nothing when stale or replayed. A profile asking for `dal:ChangedTriples` under `dal:ProvidedConcurrency` is refused | 250k tokens |
| DR2 | the state digest option, and `load-whole` | a family opting in records the digest of the state it left, and an audit query generated for it reports a graph changed outside the operations. `load-whole` of a mix of new and existing aggregates creates the new and replaces the existing, each guarded on its own row | 150k tokens |
| DR3 | both callers fill the delta slots and render the delta digest, with conformance vectors, and the conformance run runs the delta replace on every engine | the Python and Java callers agree with the vectors, and `check:persistence-conformance` passes on rdflib, Oxigraph, Jena in memory, TDB2 and Fuseki | 200k tokens |
| DR4 | the studio: the writer runs the generated delta replace for its parts and documents (TD-136 closed), its digest moves to the delta, and the service accepts a patch beside the whole state, which the browser sends where it holds the part it read | the studio's tests pass on the generated replace, the `studio-api` benchmark is no slower than `2e8a02cc`, and a save sent as a patch writes the same state as the same save sent whole | 200k tokens |

## 4. The linear replace, and what waits for it

The investigation on `claude/persistence-linear-replace` measured four forms on six engines and leans to R2, the payload as `VALUES` rows, selected where a store declares snapshot update semantics, with R0 everywhere else (LR-Q1 to LR-Q3, unanswered). It does not block this unit. A delta replace has no sweep, so it is linear on every engine without it. What still writes a whole state, `dal:WholeState` and the replace half of `load-whole`, is generated as R0 in this unit, quadratic where TD-42 says it is, and moves to the linear form in the slice that carries out the answers to LR-Q1 to LR-Q3.

## 5. Not in this unit

The merge model of DR-Q2 (c), which the sketch's §5 describes for later. A client other than the studio's browser sending patches.

## 6. Demonstration

A profile regenerated with `dal:ChangedTriples`, a save of one edited value in a part of 3,000 triples written as two quads, one deleted and one inserted, on every engine, and the studio's `studio-api` report beside `2e8a02cc`'s.
