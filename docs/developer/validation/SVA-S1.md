<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-S1, the surface canvas and simulator

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-S1, built in four parts with a pause after each. This pack has one section for each part. Part 1 was built on 2026-11-26 in autonomous mode, from [section 9 of the sketch](../sketches/studio-visual-authoring.md) and its questions SVA-Q57 to SVA-Q62.

## Invariant

The surface canvas draws every kind of contract of the surface part, a promotion, an index and a projection of each kind, from the configuration as authored, in one grammar read left to right. It computes nothing and edits nothing. What a contract writes is drawn as types read from the ontology the workspace holds, and the lowered scheme of each projection is read from the latest finished surface compilation and marked out of date when the surface part or the baseline has changed since. Each finding the form shows is drawn on the element it concerns, and the form still edits every node.

## Part 1, the canvas that draws every kind of contract

### What changed

- **The pure part**, in `apps/config-studio/src/surface/`. `drawing.ts` draws a contract as nodes and edges, with the claims each element makes on nodes of the configuration. `expression.ts` reads a derivation's expression into a tree, with a placeholder where a part is missing, and writes it as one line of infix text, the seam of the expression editor of a later part. `paths.ts` reads a members path. `terms.ts` reads the targets from the ontology. `findings.ts` places a finding. `scheme.ts` reads the lowered schemes from the compilation, and `compilation.ts` finds the latest finished surface compilation as the persistence canvas finds its own.
- **The canvas**, `ui/SurfaceCanvas.tsx`, in the Surface view beside the form as the persistence canvas sits in its part. `ConfigView.tsx` offers the same Details and Canvas switch for the surface part, chosen for each part alone. A canvas shows below the form's list of nodes, with the selected node's form under it.
- **The mapping canvas**, `ui/MappingCanvas.tsx`. It gains the optional props `readOnly` and `describe`, and `graph`, `add` and `edit` become optional. With none of them given, every existing use draws and edits as before, and the file's other lines are the same except the calls of `edit` and `add`, which are guarded. A read only canvas has no drag to link, no node or link menu and no menu entry that adds.
- **The browser fixture**, `e2e/fixtures/compiled-surface-facility.json`, written by `workers/tests/test_config_studio_compiled_fixture.py` from the real compile job of the facility sample, which holds the `projections` group and the findings of the report. The fake service serves it for a compilation of a surface part that holds a projection. Without `LATTICE_WRITE_COMPILED_FIXTURE=1` the test fails when the file differs from what the job gives.
- **Styles**, a block of `.surface-*` classes in `styles.css`. **The samples README** gained "Facility agreement, surface canvas".
- **Tests.** 23 vitest tests in `src/surface/surface.test.ts` and 4 journeys in `e2e/studio.spec.ts`.

### What is drawn

| Kind | Drawn |
|---|---|
| promotion | the carrier, a class node for each hop but the last, each hop an edge labelled with its property and `←` where inverse, and the promoted property as a target at the end of the last hop |
| index | the same hops to a box of the entries, with its forms, its closure basis and its population |
| derivation | the carrier, an evidence node for each evidence binding, solid where required and dashed where not, and on the edge that writes the derived property the line `round(commitment × margin, 2) : decimal` |
| construction | a box for the constructed node with its class, its identity, with the key's bindings named, and each value it writes as `property ← binding`. An edge joins each evidence node to the box labelled with the property it writes, the result edge reaches the box from the carrier, and the box reaches the class, the link and each written property as targets |
| join | a box for the second carrier, an edge between the two key bindings labelled `=` and the datatype where one is stated, and a box with the two cardinality rules, a default marked as one |
| expansion | the members path hop by hop to the member class, a closure marked on its hop (`refinances +`), dashed where the evidence is candidate, and the link as a target |
| node for each member | the path, then the node's box as for a construction, with `the member` where its identity or a value reads it |

Each target a contract writes is a node on the right, `Property` or `Class`, with its declared range or its label, and marked `undeclared` where the ontology does not declare it and `range disagrees` where the contracts' stated datatype is not a declared range. Contracts that write the same term meet at the same node. The scheme box stands one rank beyond, joined by a dashed edge to the term the contract writes first.

### How the targets are read

The ontology is the baseline with the held imports and the pinned dependencies the workspace loaded merged beside it (`model.heldGraphs` and `model.dependencyGraphs`), read through `Baseline`, the class the ontology view reads. A property is declared where it is typed as a property, and a class where it is typed as a class. Its ranges are the named `rdfs:range` values.

### How the scheme box reads the compile job

The latest finished job of kind Compile and target Surface is read as the persistence canvas reads its own. The box takes the scheme from `projections/manifest.json`, the number of mappings from the mappings the compiled form names (`mork:confidenceOf`, `mork:compiledFrom` and the context paths of its queries), and the review findings from the `mork:CompileFinding` nodes of the compiled form whose codes are `DerivationReview`, `ExpansionReview` and `MappingReview`. The stale mark is the persistence canvas's: the surface part's text and the baseline's revision as the browser sent them, kept in this browser, so a compilation started elsewhere says the canvas cannot tell. A click opens the scheme in a dialog with `MappingCanvas` read only.

### Choices the brief did not settle

1. **The compiled form does not hold the scheme's mappings.** `mork_rdf`'s compiled form names each mapping and records the queries compiled from it, their context paths and the findings, but states no mapping's kind, terms or source. The read only mapping canvas therefore draws each mapping by the name the lowering gave it, nested as the context paths nest them, with under each what compiled from it (queries, checks and review findings), and no terms. If the maintainer wants the terms, the options are for the compile job to write the lowered scheme as a file of the `projections` group beside each compiled form, or for the browser to lower a contract itself, which SVA-Q58 forbids. This is the one place the brief could not be met as written.
2. **The form stays beside the canvas by stacking.** The canvas sits above the form of the selected node in the detail pane, so a click on a node selects its form below and nothing is hidden.
3. **Which node a click selects.** A carrier selects the contract, an evidence node its binding, a box its constructed node or join statement, and an index's box the contract. A target opens the ontology view where the ontology declares it and does nothing where it does not. A reached class node selects nothing of its own.
4. **What a click on a list node draws.** The contract the node is or belongs to, found by the claims of each contract's drawing. A node that belongs to none, or no selection, draws all contracts. The choice between the selected contract and all is a switch.
5. **The named sources of an expansion are drawn as the vocabulary defines them.** `srf:ListMembers` is the property, `rdf:rest` zero or more times and `rdf:first`, and `srf:TransitiveClosure` is the property one or more times. This restates the vocabulary's own definition, and the lowering is not consulted.
6. **The member class** is the declared range of the last hop, and `member` where there is none.
7. **A join's comparison is `=`**, since a key pair states no operator, and a cardinality left out is written with `(default)`, which is what the vocabulary says leaving it out means.
8. **A stated datatype disagrees on equality only.** `xsd:integer` against a declared `xsd:decimal` is marked, and no derivation of one datatype from the other is applied. A property with no declared range disagrees with nothing.
9. **A finding goes to the element that names its path, else to one that states its node generally, else to the first element that claims the node.** A finding on a blank node, which a report names differently from the browser, stays in the form's list, as does one on a node no element claims. The canvas says how many remain. A finding on an edge also changes the edge's colour and prefixes its label.
10. **The picture opens fitted, to at most its natural size**, as the other canvases do, so a contract with many ranks is drawn small and the author zooms. The all-contracts view is dense. It has no overlap of nodes but several edges cross, and a better ordering is a matter for the next part.

### Results

`yarn workspace @lattice/config-studio run check` passed, 37 files and 587 tests. `mise run check:config-studio` exited 0, with 588 Python tests, the Java modules and the same 587 browser-code tests. `mise run check:identifiers` and `mise run check:published-decisions` passed. `mise run test:config-studio` ran 77 journeys, 76 passed and 1 failed, the column handle test `a handle moves with the arrow keys`, which also fails on the unchanged tree in 2 of 6 runs and is not this part's. The 4 surface journeys passed. The browser suites ran with a Playwright browser of the build the installed Playwright does not name, reached through a directory of links in the scratch area, since the build it names is not installed here and was not fetched.

### Placement

T0. The canvas, its pure part, the read only mode of the mapping canvas, the fixture and the samples README are the studio's open substrate, and nothing in them is a protected asset.

The reviewer ran these again on 2026-11-26: the app's check with 587 tests in 37 files, `check:config-studio` exit 0 with 588 Python tests and the Java modules' 9, 254, 10 and 85 tests with none failing, and `check:identifiers` and `check:published-decisions` passed. The journeys on the fake service were run by the delegated developer only, 76 of 77 passing, the one failure the column handle's test that TD-257 records, which fails on the unchanged tree too.
