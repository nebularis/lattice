<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Sketch: the compiled profile states where a target's data lands

**Unit:** `studio-visual-authoring` (SVA), raised by the maintainer on 2026-11-18 when choosing option (c) for the landing places of SVA-P1
**Status:** sketch. SVA-Q17 to SVA-Q22 open, each with a leaning. Nothing is built
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

**Each write access says where it writes.** A `dal:ResourceAccess` whose mode is `Insert` or `Delete` gains exactly one of:

- `dal:inGraph`, an IRI, where the graph is fixed, for example `urn:g:facilities` or `urn:g:keys`
- `dal:inGraphNamed`, a string template, where the graph is named when the operation runs. Its placeholders are a closed set, each defined once in the ontology:
  - `{root}`, the operation's root parameter, percent-encoded as `ENCODE_FOR_URI` encodes it, as `dal:graphIriTemplate`'s `{id}` is
  - `{newRev}`, the operation's new revision parameter
  - `{month}`, the month of the transaction time, as `YYYY-MM`

A key claim's access also gains `dal:forConstraint`, the `dal:UniquenessConstraint` it serves.

**The compiled profile names the scopes that match.** `dal:matchedScope`, on a `dal:CompiledProfile`, one for each scope node the compiler's resolution found to match the target, whether or not a profile applied through it won.

A landing place is then a query over what the profile states: the distinct pairs of resource kind and graph, or graph template, over every write access of the target's operations, each with the operations that hold such an access. Nothing is stated twice.

The studio follows. The worker stops building `landing-places.json`, the schema leaves the contract, and the canvas reads `compiled-profile.ttl`, which every persistence compilation already gives, with a small reader in the browser.

### 2.1 Worked example, the facility sample

The Facility target, a composite family under a patch log. Abridged, one operation:

```turtle
<ex/Facility/compiled/replace-whole#access-01> a dal:ResourceAccess ;
    dal:resourceKind dal:Aggregate ; dal:accessMode dal:Insert ;
    dal:keyedBy <ex/Facility/compiled/replace-whole#param-root> ;
    dal:inGraph <urn:g:facilities> .
<ex/Facility/compiled/replace-whole#access-04> a dal:ResourceAccess ;
    dal:resourceKind dal:VersionRow ; dal:accessMode dal:Insert ;
    dal:inGraph <urn:g:meta/6> .
<ex/Facility/compiled/replace-whole#access-06> a dal:ResourceAccess ;
    dal:resourceKind dal:Receipt ; dal:accessMode dal:Insert ;
    dal:inGraphNamed "urn:g:txlog/{month}" .
<ex/Facility/compiled/replace-whole#access-08> a dal:ResourceAccess ;
    dal:resourceKind dal:PatchContent ; dal:accessMode dal:Insert ;
    dal:inGraphNamed "{newRev}/add" .
<ex/Facility/compiled/replace-whole#access-09> a dal:ResourceAccess ;
    dal:resourceKind dal:PatchContent ; dal:accessMode dal:Insert ;
    dal:inGraphNamed "{newRev}/del" .
```

The key claim of `key-claim-write:facility-reference-per-branch`:

```turtle
<ex/Facility/compiled/key-claim-write-facility-reference-per-branch#access-01> a dal:ResourceAccess ;
    dal:resourceKind dal:KeyClaim ; dal:accessMode dal:Insert ;
    dal:inGraph <urn:g:keys> ; dal:forConstraint ex:FacilityReferencePerBranch .
```

The Borrower, a named-graph family, writes its aggregate with `dal:inGraphNamed "urn:g:borrower/{root}"`. The places SVA-P1's fixture lists come out the same: seven for the Facility, five for the Borrower.

### 2.2 What changes, and what reads it

| Where | Change |
|---|---|
| `ontology/persistence` README, sections 4, 5.8, 6 and 12 | the four properties, the placeholders' definitions, the class diagram of the operation contract, and a release note: "New: `dal:inGraph`, `dal:inGraphNamed`, `dal:forConstraint`, `dal:matchedScope` (no effect)" |
| `ontology/persistence/shapes` | `ResourceAccessShape`: a write access has exactly one of the two graph properties, a read access neither, a template's placeholders only from the closed set |
| `tools/persistence` | the contract's emission states each write's graph from the operation's IR, which it already builds, and the compile stage states the matched scopes it already computes |
| fixtures | every `ontology/persistence/test/expected-profiles/*.expected.ttl` and `packages/persistence/python/tests/data/*.compiled.ttl` regenerated, since each compiled profile gains triples |
| version | the persistence module's minor version and its shapes, by `mise run version:bump -- --layer-target persistence --increment minor --with-shapes`, at the merge. Release tags are the maintainer's |
| caller libraries | no change. They do not read the accesses |
| the studio | SVA-P1b, below |

One more effect to name. Today the compiler emits one access for each resource, mode and key, so a patch log's two graphs are one access. Stating the graph makes them two, since they write two graphs. A reader that counted accesses would see more of them. No reader in the repository counts them, read on 2026-11-18.

## 3. Costs

| | Today | After |
|---|---|---|
| triples a compiled target gains | | one for each write access, about 10 to 20 for a target, and one for each matching scope |
| the studio worker's landing code | rebuilds each operation's IR, walks its graph blocks, imports a private helper | gone. It reads triples, or the browser does |
| a reader with no compiler code | cannot tell where a write lands | reads it |

## 4. Questions

**SVA-Q17. Where is a place's graph stated?** (a) On each write `dal:ResourceAccess`, which already exists and already says what the operation writes. (b) A new `dal:LandingPlace` on the compiled profile, listing kind, graph and the operations that write it. (b) is simpler to read but states again what the accesses say. Leaning (a).

**SVA-Q18. What form does a graph that is named at run time take?** (a) A string template with a closed set of placeholders, `{root}`, `{newRev}` and `{month}`, as `dal:graphIriTemplate` already is. (b) A structured list of parts, each a constant, a parameter or the month. (c) A rendered phrase for people only. (b) is the more exact and needs an RDF list on every such access. (c) cannot be read by a tool. Leaning (a), with the placeholders defined once in the ontology.

**SVA-Q19. Does `dal:ResourceKind` gain individuals?** **Why it might.** The studio's canvas tells apart, as places of their own, some things one kind covers. Under append-versions the data graph and a new version are both `Aggregate`. A patch log's added and removed triples are both `PatchContent`. A receipt's month bucket and the pinned graph that keeps a retained head are both `Receipt`. And the materialised rows of a surface contract, the graph role `derived`, have no kind at all. SVA-P1's worker made these distinctions itself, from an operation's name, a variable's name and a graph role in the IR. If the compiled profile is to say everything the canvas draws, something in it has to make them.

**What the kinds are for.** A kind is a logical resource with a logical key, and track H separated it from its SPARQL realisation on purpose: so a contract can be checked against a relational realisation as well as a SPARQL one (FMH-2.6's paper check), so the conformance and the formal models reason about a small fixed set, and so a change of realisation, a new bucket scheme or a moved graph, never changes the contract. The four distinctions above are each realisation or key. The pinned graph and the month bucket are where a receipt is kept, the direction is part of a patch's key, and a version is an aggregate written by an append-versions operation, which `dal:operationKind dal:AppendVersion` already says.

**The derived role is not a persistence resource.** No builder of the persistence compiler writes it. It is written by the surface compiler's maintenance operations (`tools/surface/src/surface/maintenance.py`), which the studio's writer runs in a write's request (PM-2). So it is not in a compiled persistence profile today, and the surface canvas (SVA-S1) draws it from a surface contract.

| | (a) No new kinds | (b) New kinds for each distinction | (c) No new kinds, and each write states its graph role |
|---|---|---|---|
| what is added | nothing beyond SVA-Q17's graph | `Version`, `PatchAdded`, `PatchRemoved`, `PinnedReceipt` and `DerivedRow`, each with a logical key | a closed class `dal:GraphRole` mirroring the IR's roles (`Data`, `Meta`, `Txn`, `Log`, `Pinned`, `Patch`, `Keys` and the rest) and `dal:inGraphRole` on a write access |
| how the canvas tells the cases apart | the graph and the operation's kind: `{newRev}/add` from `{newRev}/del`, `urn:g:txlog/pinned` from `urn:g:txlog/{month}`, and an `AppendVersion` operation's aggregate as a version | by the kind | by the role, without reading the graph's text |
| the logical model | unchanged | five realisation and key distinctions made kinds, which reverses NQ1 and NQ2 and the key of `PatchContent`, and puts a surface resource into persistence | unchanged. The role is stated beside the kind as the realisation it is |
| what else changes | nothing | the shapes' `sh:in`, the compiler's enumeration and logical keys, the access sets, every expected profile, FMH-2.6's paper check and the formal models that enumerate the kinds | one class with its individuals and `sh:in`, one property |
| what a reader gains over (a) | nothing a graph does not say, at much higher cost | kinds a person reads as labels | a label for each place that needs no parsing of a template, for example "receipt, retained head" for `Pinned` |
| the design standard that weighs on it | | a classification that changes no answer the graph already gives | the same standard: the role changes no answer the graph does not give, unless a reader must tell places apart without reading graph names |

Leaning (a). (b) reopens decisions track H settled for reasons that still hold, and pulls a surface resource into persistence, for labels. (c) is sound and cheap, and is worth adding only if a reader needs a place's role without reading its graph, which neither the canvas nor the simulator does, since both already have the graph.

**SVA-Q20. How are the matching scopes stated?** (a) `dal:matchedScope` on the compiled profile, every scope that matched. (b) As (a), and on each resolved dimension, `dal:wonThrough`, the matched scope or scopes through which its winning profile applied. (b) costs one triple for each dimension a profile won, about 10 for a target. Leaning (a).

What (a) leaves a reader without, the compiled profile alone in hand:

- **Which scope a value came through.** A dimension names the profile that won it, and the scopes match the target, but the profile's `dal:appliesTo` is in the configuration. A reader cannot say "the receipt model is a patch log because `ex:FacilityClass` matched and `ex:FacilityReceiptProfile` applies through it" without the configuration beside it, and where a profile applies through several matched scopes it cannot say which. (b) answers it.
- **Which scopes did not match, and why.** A profile an author expected to apply and that did not appears nowhere. Neither option answers it. It belongs with the compiler's diagnostics, if anyone asks for it.
- **How the winner was chosen.** The resolution's precedence, by scope kind and `dal:priority`, is the compiler's, and a reader cannot reproduce it from either option. Both state the outcome, as the dimensions already do.

None of these limits the canvas. The Profile lens draws the targets each winning profile shapes, and the Scope node lens the targets each scope matches, both from what (a) states. (b) would serve a view that explains a value, which no slice plans, and it can be added later without changing (a).

**SVA-Q21. Does a key claim's access name its constraint?** (a) Yes, `dal:forConstraint` to the `dal:UniquenessConstraint`. (b) No, the `constraintId` binding is enough. (a) is a link a tool follows where the binding is a string to match. Leaning (a).

**SVA-Q22. What does the studio keep?** (a) The worker stops writing `landing-places.json`, its schema leaves the contract, and the canvas reads `compiled-profile.ttl`. (b) The worker keeps writing the JSON, now read from the compiled profile alone. (b) keeps a second form of one fact. Leaning (a).

An observation, not a question: the receipt's month bucket is named from `NOW()` in the generated SPARQL, which PRI-56 forbids in an identity. It is the compiler's behaviour today and is unchanged here. Stating `{month}` as the month of the transaction time says what it should be, and whether the generated query takes it from the transaction time is a question for the persistence unit.

## 5. Slices

| Slice | What | Done when |
|---|---|---|
| SVA-P1a | the four `dal:` terms in the persistence README and shapes, the compiler stating them, the fixtures regenerated, the release note under Unreleased | every compiled example states a graph or template on each write access, the shapes hold it, and the persistence suite and its conformance across engines pass |
| SVA-P1b | the studio reads the compiled profile: the worker's landing code and `landing-places.json` gone, the canvas reading `compiled-profile.ttl` | the canvas draws the facility sample as SVA-P1 does, from the compiled profile alone |
