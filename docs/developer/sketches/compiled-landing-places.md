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

1. **The caller libraries read the contract.** `packages/persistence/python` and `packages/persistence/java` read `dal:ResourceAccess` and model `dal:ResourceKind` as a closed enumeration. A new term is ignored by them, but a new INDIVIDUAL of a closed class is a value they do not know.
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
| caller libraries | no change. They read the contract and ignore terms they do not know |
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

**SVA-Q19. Does `dal:ResourceKind` gain individuals?** The studio's places split some kinds further: a version from a data graph under append-versions, a patch log's added from its removed triples, a receipt's month bucket from the pinned graph. (a) No new kinds. A place is a kind and a graph, and the graph tells each of these apart. (b) New kinds for each. (b) breaks the caller libraries, which read the kind as a closed enumeration. Leaning (a). Whether a compiled operation ever writes the derived role (`GraphRole.DERIVED`), which has no kind today, is to be read in SVA-P1a, and if one does, a kind for it is the one addition, put to the maintainer then.

**SVA-Q20. How are the matching scopes stated?** (a) `dal:matchedScope` on the compiled profile, every scope that matched. (b) As (a), and on each resolved dimension the scope through which its winning profile applied. (b) answers which scope won each dimension, which nothing reads yet. Leaning (a).

**SVA-Q21. Does a key claim's access name its constraint?** (a) Yes, `dal:forConstraint` to the `dal:UniquenessConstraint`. (b) No, the `constraintId` binding is enough. (a) is a link a tool follows where the binding is a string to match. Leaning (a).

**SVA-Q22. What does the studio keep?** (a) The worker stops writing `landing-places.json`, its schema leaves the contract, and the canvas reads `compiled-profile.ttl`. (b) The worker keeps writing the JSON, now read from the compiled profile alone. (b) keeps a second form of one fact. Leaning (a).

An observation, not a question: the receipt's month bucket is named from `NOW()` in the generated SPARQL, which PRI-56 forbids in an identity. It is the compiler's behaviour today and is unchanged here. Stating `{month}` as the month of the transaction time says what it should be, and whether the generated query takes it from the transaction time is a question for the persistence unit.

## 5. Slices

| Slice | What | Done when |
|---|---|---|
| SVA-P1a | the four `dal:` terms in the persistence README and shapes, the compiler stating them, the fixtures regenerated, the release note under Unreleased | every compiled example states a graph or template on each write access, the shapes hold it, and the persistence suite and its conformance across engines pass |
| SVA-P1b | the studio reads the compiled profile: the worker's landing code and `landing-places.json` gone, the canvas reading `compiled-profile.ttl` | the canvas draws the facility sample as SVA-P1 does, from the compiled profile alone |
