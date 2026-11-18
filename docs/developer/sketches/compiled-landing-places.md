<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Sketch: the compiled profile states where a target's data lands

**Unit:** `studio-visual-authoring` (SVA), raised by the maintainer on 2026-11-18 when choosing option (c) for the landing places of SVA-P1
**Status:** sketch. SVA-Q17 to SVA-Q22 answered by the maintainer on 2026-11-18, SVA-Q23 open. Nothing is built
**Plan:** [studio-visual-authoring.md](../plans/studio-visual-authoring.md), slices SVA-P1a and SVA-P1b
**Builds on:** the persistence module (`ontology/persistence`, `tools/persistence`, ADR-A78, ADR-A79), the typed operation IR (ADR-A123), graph naming (ADR-A122 decision 8), and the caller libraries (ADR-A132)

## 1. The scene

SVA-P1 gave the studio a picture of where each target's data lands: every graph an operation writes, its name or naming rule, and the operations that write it. The studio's worker builds it as `landing-places.json`. The maintainer chose on 2026-11-18 that the compiled profile should state these facts itself, in `dal:` terms, since they are facts about persistence and every adopter of the compiler would gain them.

What a `dal:CompiledProfile` states today, read from `tools/persistence/src/persistence/compiler.py` and `contract_emit.py` on 2026-11-18:

| Fact | Stated today | How the worker gets it now |
|---|---|---|
| the target, its deployment, the profiles that won each dimension | yes, `dal:forTarget`, `dal:forDeployment`, `dal:resolvedDimension` with `dal:wonBy` | read |
| the boundary's edges, owned or referenced, by identity or pinned | yes, `dal:ReferenceEdge` and its `dal:edge*` properties | read |
| each operation, its template and kind | yes, `dal:GeneratedOperation`, `dal:usesTemplate`, `dal:operationKind` | read |
| each resource an operation reads or writes, with the mode | yes, `dal:ResourceAccess` with `dal:resourceKind` and `dal:accessMode` (`Insert`, `Delete` or a read) | not used |
| which GRAPH a resource is in, or the rule that names it | no. `dal:ResourceKind`'s comments say it in prose, and the bindings hold its pieces (`dataGraph`, `graphPrefix`, `graphSuffix`, `metaGraphPrefix`, `logGraphPrefix` and others) | rebuilds each operation's IR with the compiler's builders and walks its insert and delete graph blocks |
| which uniqueness constraint a key claim serves | only as the `constraintId` binding, a string | reads the binding |
| which scope nodes match the target | no. Only the winning profiles, whose `dal:appliesTo` is in the configuration | runs the compiler's `scopes.matches` over the configuration |

So the gap is narrow. The compiled profile already says which resources each operation writes. It does not say where they are, and it does not say which scopes matched.

Three facts constrain the options.

1. **`dal:ResourceKind` is a logical model, settled under formal methods.** Each kind is a logical resource with a logical key (`tools/persistence/src/persistence/contract.py`, `LOGICAL_KEYS`), and its SPARQL realisation is the graph role the builders name. Track H decided that the pinned head is a realisation of receipt retention and not a resource of its own (NQ1 and NQ2 of the track H plan, 2026-10-13), that a bucket month is never part of a key, and that a patch log's added and removed triples are one resource whose key holds a direction (FMH-2.6's Validation Pack). The kinds are closed by `sh:in` in `ResourceAccessShape` and by the compiler's `ResourceKind` enumeration. The caller libraries under `packages/persistence` do not read the kind, read on 2026-11-18.
2. **A fact is recorded once** (the design standards). A second structure listing places beside the accesses would restate what the accesses say.
3. **A graph name has a precedent form.** `dal:graphIriTemplate` already names a family's graphs by a string with `{id}` replaced by the root, percent-encoded.

## 2. The design

The logical model stays as track H settled it. What is added is its realisation, stated beside it on nodes of its own.

**A place.** `dal:GraphPlace` is one graph, or one family of graphs named when an operation runs, in which a compiled target's data lands. It states:

- `dal:inGraphRole`, exactly one `dal:GraphRole`, the part of the store the graph belongs to
- exactly one of `dal:inGraph`, an IRI, where the graph is fixed, for example `urn:g:facilities` or `urn:g:keys`, and `dal:inGraphNamed`, a string template, where the graph is named when the operation runs. A template's placeholders are a closed set, each defined once in the ontology:
  - `{root}`, the operation's root parameter, percent-encoded as `ENCODE_FOR_URI` encodes it, as `dal:graphIriTemplate`'s `{id}` is
  - `{newRev}`, the operation's new revision parameter
  - `{month}`, the month of the transaction time, as `YYYY-MM`

**The roles.** `dal:GraphRole` is a closed class whose individuals mirror the typed operation IR's `GraphRole` (ADR-A123): `dal:DataRole`, `dal:MetaRole`, `dal:TxnRole`, `dal:LogRole`, `dal:EventRole`, `dal:KeysRole`, `dal:QuarantineRole`, `dal:RetentionRole`, `dal:PinnedRole`, `dal:DatasetRole` and `dal:PatchRole`. The IR's `derived` role is the surface compiler's and has no individual here. The names end in `Role` since `dal:Event`, `dal:Pinned` and `dal:Quarantine` already name other terms. A runtime or deployment reader finds, for example, every pinned graph by comparing one IRI, never by matching a template's text.

**Each write access lands in one place.** A `dal:ResourceAccess` whose mode is `Insert` or `Delete` gains exactly one `dal:landsIn`, a `dal:GraphPlace`. A read access has none. Every access that lands in the same place points at the same node, so a profile states each distinct place once, and the places the canvas draws are exactly its `dal:GraphPlace` nodes. The access keeps only logical facts, so the paper check, the formal models and any other realisation read it unchanged. A relational realisation would add a place of another class beside it.

**A place's identity.** The compiler mints a place's IRI from the compiled profile's IRI, the role and the graph or template, percent-encoded, for example `<ex/Facility/compiled#place-log-urn%3Ag%3Atxlog%2F%7Bmonth%7D>`. The same compilation gives the same IRIs, so expected profiles compare as they do today, without graph isomorphism.

**A key claim names its constraint.** A key claim's access gains `dal:forConstraint`, the `dal:UniquenessConstraint` it serves.

**The compiled profile names the scopes that match, and through which one each value won.** `dal:matchedScope`, on a `dal:CompiledProfile`, one for each scope node the compiler's resolution found to match the target, whether or not a profile applied through it won. `dal:wonThrough`, on each `dal:resolvedDimension`, the matched scope or scopes through which its winning profile applied. Which scopes did not match and why, and how the precedence chose the winner, are not stated. Only an author explaining a value asks them, and the compiler's diagnostics answer them from the configuration.

The studio follows. The worker stops building `landing-places.json`, the schema leaves the contract, and the canvas reads `compiled-profile.ttl`, which every persistence compilation already gives, with a small reader in the browser.

### 2.1 Worked example, the facility sample

The Facility target, a composite family under a patch log. Abridged, one operation and its places:

```turtle
<ex/Facility/compiled/replace-whole#access-01> a dal:ResourceAccess ;
    dal:resourceKind dal:Aggregate ; dal:accessMode dal:Insert ;
    dal:keyedBy <ex/Facility/compiled/replace-whole#param-root> ;
    dal:landsIn <ex/Facility/compiled#place-data-urn%3Ag%3Afacilities> .
<ex/Facility/compiled/replace-whole#access-06> a dal:ResourceAccess ;
    dal:resourceKind dal:Receipt ; dal:accessMode dal:Insert ;
    dal:landsIn <ex/Facility/compiled#place-log-urn%3Ag%3Atxlog%2F%7Bmonth%7D> .
<ex/Facility/compiled/replace-whole#access-08> a dal:ResourceAccess ;
    dal:resourceKind dal:PatchContent ; dal:accessMode dal:Insert ;
    dal:landsIn <ex/Facility/compiled#place-patch-%7BnewRev%7D%2Fadd> .

<ex/Facility/compiled#place-data-urn%3Ag%3Afacilities> a dal:GraphPlace ;
    dal:inGraphRole dal:DataRole ; dal:inGraph <urn:g:facilities> .
<ex/Facility/compiled#place-log-urn%3Ag%3Atxlog%2F%7Bmonth%7D> a dal:GraphPlace ;
    dal:inGraphRole dal:LogRole ; dal:inGraphNamed "urn:g:txlog/{month}" .
<ex/Facility/compiled#place-patch-%7BnewRev%7D%2Fadd> a dal:GraphPlace ;
    dal:inGraphRole dal:PatchRole ; dal:inGraphNamed "{newRev}/add" .
```

The key claim of `key-claim-write:facility-reference-per-branch`:

```turtle
<ex/Facility/compiled/key-claim-write-facility-reference-per-branch#access-01> a dal:ResourceAccess ;
    dal:resourceKind dal:KeyClaim ; dal:accessMode dal:Insert ;
    dal:landsIn <ex/Facility/compiled#place-keys-urn%3Ag%3Akeys> ;
    dal:forConstraint ex:FacilityReferencePerBranch .
```

A resolved dimension:

```turtle
<ex/Facility/compiled> dal:matchedScope ex:FacilityClass, ex:AllFamilies ;
    dal:resolvedDimension [ dal:dimension dal:ReceiptModel ;
        dal:wonBy ex:FacilityReceiptProfile ; dal:wonThrough ex:FacilityClass ] .
```

The Borrower, a named-graph family, writes its aggregate to a place with `dal:inGraphNamed "urn:g:borrower/{root}"`. The places SVA-P1's fixture lists come out the same, seven for the Facility and five for the Borrower, as `dal:GraphPlace` nodes.

### 2.2 What changes, and what reads it

| Where | Change |
|---|---|
| `ontology/persistence` README, sections 4, 5.8, 6 and 12 | `dal:GraphPlace`, `dal:GraphRole` and its eleven individuals, `dal:landsIn`, `dal:inGraphRole`, `dal:inGraph`, `dal:inGraphNamed`, `dal:forConstraint`, `dal:matchedScope` and `dal:wonThrough`, the placeholders' definitions, the class diagram of the operation contract, and a release note under Unreleased (no effect) |
| `ontology/persistence/shapes` | `ResourceAccessShape`: a write access has exactly one `dal:landsIn`, a read access none. A new `GraphPlaceShape`: exactly one role from the closed set, exactly one of the two graph properties, a template's placeholders only from the closed set. `dal:wonThrough` names a scope the same profile states as matched |
| `tools/persistence` | the contract's emission collects the distinct places from each operation's IR, which it already builds, mints their IRIs and links each write access to its place. The compile stage states the matched scopes and the scope each dimension won through, which it already computes |
| fixtures | every `ontology/persistence/test/expected-profiles/*.expected.ttl` and `packages/persistence/python/tests/data/*.compiled.ttl` regenerated, since each compiled profile gains triples |
| version | the persistence module's minor version and its shapes, by `mise run version:bump -- --layer-target persistence --increment minor --with-shapes`, at the merge. Release tags are the maintainer's |
| caller libraries | no change. They do not read the accesses |
| the studio | SVA-P1b, below |

One more effect to name. Today the compiler emits one access for each resource, mode and key, so a patch log's two graphs are one access. Landing in two places makes them two accesses. A reader that counted accesses would see more of them. No reader in the repository counts them, read on 2026-11-18. How the two accesses differ is SVA-Q23.

## 3. Costs

| | Today | After |
|---|---|---|
| triples a compiled target gains | | one for each write access, three for each distinct place, one for each matching scope and one for each resolved dimension, about 40 to 60 for a target |
| a query asking where an access lands | | one more hop, through the place. A design-time cost, accepted by the maintainer on 2026-11-18 |
| the studio worker's landing code | rebuilds each operation's IR, walks its graph blocks, imports a private helper | gone. It reads triples, or the browser does |
| a reader with no compiler code | cannot tell where a write lands | reads it, and finds a place by its role |

## 4. Questions

Answered by the maintainer on 2026-11-18:

| Question | Answer |
|---|---|
| SVA-Q17. Where is a place's graph stated? | on a `dal:GraphPlace` node of its own, with a minted IRI, one for each distinct place, linked from each write access by `dal:landsIn`. Considered: the graph on the access itself, which puts a realisation fact on a logical node, and a `dal:LandingPlace` listing that restates the accesses. The extra hop, the identity rule and the compiler's extra emission are accepted as worth it |
| SVA-Q18. What form does a graph named at run time take? | a string template with the closed placeholders `{root}`, `{newRev}` and `{month}`, as `dal:graphIriTemplate` is, defined once in the ontology. Considered: a structured list of parts, and a phrase for people only |
| SVA-Q19. Does `dal:ResourceKind` gain individuals? | no. The kinds stay the logical model track H settled (NQ1, NQ2, design review 2.2, FMH-2.6), and the realisation gains its own closed kinds, `dal:GraphRole`, stated on the place. A runtime or deployment reader must find a place by its role without reading a graph's name. Considered: no roles, which leaves that reader parsing templates, and new resource kinds for each distinction, which reverses track H's decisions and pulls the surface compiler's `derived` rows into persistence |
| SVA-Q20. How are the matching scopes stated? | `dal:matchedScope` on the compiled profile and `dal:wonThrough` on each resolved dimension, so a reader can tell which scope a value came through without the configuration, for example for impact analysis. Which scopes did not match, and how the precedence chose, stay with the compiler's diagnostics |
| SVA-Q21. Does a key claim's access name its constraint? | yes, `dal:forConstraint`, a link a tool follows where the `constraintId` binding is a string to match |
| SVA-Q22. What does the studio keep? | nothing of its own. The worker stops writing `landing-places.json`, its schema leaves the contract, and the canvas reads `compiled-profile.ttl` |

**SVA-Q23. How do a patch log's two accesses differ?** A patch log's added and removed triples land in two places, `{newRev}/add` and `{newRev}/del`, both with the role `dal:PatchRole`, as both are `PATCH` in the IR. So a reader that must tell them apart without reading the template has nothing to compare. The direction is part of `PatchContent`'s logical key (FMH-2.6).

| | (a) Two roles | (b) The direction on the access | (c) The direction on the place |
|---|---|---|---|
| what is added | `dal:PatchAddedRole` and `dal:PatchRemovedRole` in place of `dal:PatchRole` | `dal:patchDirection`, `dal:Added` or `dal:Removed`, on a `PatchContent` access, the constant part of its logical key | `dal:patchDirection` on a place whose role is `dal:PatchRole` |
| where the fact sits | the realisation, though the direction is logical | the logical node, where the rest of the key is | the realisation, though the direction is logical |
| agreement with the IR | departs from the IR's one `PATCH` role | the IR's roles mirrored as they are | the IR's roles mirrored as they are |
| what else changes | the role set and its mirror of the IR | the access's shape, and the paper check gains a key part it already names | the place's shape |

Leaning (b). The direction is a value of the logical key, and the access is where the logical facts live. It keeps the role set the IR's, and a reader asking "the removed triples of a patch" asks the access, then its place.

An observation, not a question: the receipt's month bucket is named from `NOW()` in the generated SPARQL, which PRI-56 forbids in an identity. It is the compiler's behaviour today and is unchanged here. Stating `{month}` as the month of the transaction time says what it should be, and whether the generated query takes it from the transaction time is a question for the persistence unit.

## 5. Slices

| Slice | What | Done when |
|---|---|---|
| SVA-P1a | the terms of section 2 in the persistence README and shapes, the compiler stating them, the fixtures regenerated, the release note under Unreleased | every compiled example links each write access to one place with a role and a graph or template, each resolved dimension to the scope it won through, the shapes hold it, and the persistence suite and its conformance across engines pass |
| SVA-P1b | the studio reads the compiled profile: the worker's landing code and `landing-places.json` gone, the canvas reading `compiled-profile.ttl` | the canvas draws the facility sample as SVA-P1 does, from the compiled profile alone |
