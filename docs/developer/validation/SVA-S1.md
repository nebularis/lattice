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

## Part 2, building a path by clicking, with the answers on part 1

Built on 2026-11-27 in autonomous mode, from the maintainer's answers on part 1 and SVA-Q60 (a).

### What changed

- **The answers on part 1.** The compile job holds each lowered scheme as `projections/{scheme}.mork.ttl` beside its compiled form, and the manifest entry names it as `mork` (`config_studio_projections.py`, `_compile_projections`). The read only mapping canvas draws that scheme in full, with its terms, and puts the compiled form's queries and review findings on a line under each mapping it concerns (`annotate` of `MappingCanvas`). A job without the file is drawn as part 1 drew it. The all-contracts view is an overview of carriers, contracts and targets, and the contract selected in the list is drawn in full among them (`drawContracts` with `overview` and `expand`). The facility sample declares most targets, leaves `ex:bookedAt` undeclared and gives `ex:marginWeightedCommitment` the range `xsd:integer` against the `xsd:decimal` its contract states, and its join states neither cardinality rule. The fixture was written again with `LATTICE_WRITE_COMPILED_FIXTURE=1`.
- **Path mode.** `surface/pathmode.ts` is the pure part and `ui/PathMode.tsx` the canvas. A **Build path** button on a promotion's or an index's carrier, on a binding's evidence node and on the members node of an expansion starts it. Each click is an edit of the surface part by `writePath` for a read path, and by the new `writeBindingProperty` and `writeMembersPath` beside it in `rdf/path.ts` for the other two places. The form and the canvas read the same graph, so neither keeps a path.
- **Tests.** 21 vitest tests in `surface/pathmode.test.ts`, the new and changed tests of `surface.test.ts`, a worker test that the manifest names each `.mork.ttl` and that its graph is the lowering's output, and 2 journeys beside the changed part 1 journeys and a new one for the overview.

### Triples written

For each place the test compares the Turtle a click gives with the Turtle the writer gives for the same path, and they are equal. One forward hop is `srf:readProperty`. Two hops, one inverse, are two `srf:PathStep` nodes named `{contract}-step-0` and `-1` with `srf:stepIndex`, `srf:stepProperty` and `srf:stepDirection`, which is `writePath`'s output. An index path is written as a promotion's. A binding's property is `srf:bindsProperty`. A members path is the property for one hop, a list for a sequence, `sh:inversePath` around an inverse hop and `sh:oneOrMorePath` or `sh:zeroOrMorePath` around a hop with a closure.

### Choices the brief did not settle

1. **The manifest key** is `mork`, and the lowered file holds the lowering's whole graph, including its `srf:producesMapping` triple on the contract.
2. **The fallback is per scheme.** A scheme whose file is missing or does not read is drawn from its compiled form, and the others from theirs.
3. **The overview shares carriers by class.** The expanded contract's own carrier node stands for its class. A join's second carrier is a carrier of the overview, joined by a dashed edge. A contract that writes nothing, such as an index, has no target edge. A contract that states no carrier has no carrier edge.
4. **The sample's ontology is the baseline.** The brief says "vocabulary". The canvas reads targets from the baseline, so the declarations are in `facility-baseline.ttl`. The disagreement is on the one target whose contract states a datatype. Declared terms now show their labels, so the canvas says "tests covenant" where it said `testsCovenant`, and the journeys were changed to match.
5. **Where path mode starts.** The places are the carrier of a promotion or an index, an evidence node, and the members node of an expansion. A result binding's property is a target the contract writes and has no place.
6. **A named source is written out on the first edit.** A statement states a source or a path, never both (`srf:P20`), so the first hop, undo or closure writes the path the source stands for as `srf:membersPath` and removes `srf:expansionSource`. Path mode says so. A members path in a form the canvas does not read is replaced by the first hop, and says so.
7. **The first hop of a members path is not forced to the binding's property.** `srf:P20` requires the path to read it, and the canvas leaves a breach to the findings the form shows.
8. **A class is unknown after a hop with no declared range.** Every property is then offered, marked `class unknown`. A forward property is offered of a class where a domain of it is the class or one above it, and under any class where it states none. Going back, a property is offered where a range is the class or one above it, and under any class where it states none. A datatype property is never offered going back.
9. **Many properties.** Each direction draws 12 properties and a filter and **Draw them all** reach the rest, so a class that is not known leaves the canvas readable.
10. **The closure toggle offers one or more and zero or more.** A hop read as zero or one is kept and drawn, and the toggle can replace it.
11. **Selecting.** Starting path mode selects the node it writes in the form, so the form beside the canvas is the one that shows the path.

### Results

- `yarn workspace @lattice/config-studio run check` passed, 38 files and 617 tests.
- `mise run test:config-studio` ran 80 journeys and 80 passed. A first run had one failure, the ontology drawing journey, whose counts of classes and links changed with the facility baseline's new declarations, and its expectations were updated. The browser used the build the installed Playwright does not name, reached through a directory of links in the scratch area as in part 1.
- `mise run check:workers` passed, 380 tests. `mise run check:config-studio` exited 0 when run alone, with the same 617 browser-code tests. `mise run check:identifiers` and `mise run check:published-decisions` passed.

The reviewer ran part 2's checks again on 2026-11-27: the app's check with 617 tests in 38 files, `check:workers` 380 passed, `check:config-studio` exit 0 with 588 Python tests and the Java modules' 9, 254, 10 and 85 tests with none failing, and `check:identifiers` and `check:published-decisions` passed. The journeys on the fake service, 80 of 80, were run by the delegated developer only.

## Part 3, the expression editor with its tree rendering, and two fixes

Built on 2026-11-27 in autonomous mode, from SVA-Q57 (b) and SVA-Q59, and the two fixes the maintainer asked for first.

### What changed

- **A named expansion source is never rewritten in path mode.** Where an expansion states `srf:expansionSource`, path mode draws the path the name stands for as a chain of classes marked **given by the name**, and edits nothing. The hop, undo and closure functions of `surface/pathmode.ts` return the graph unchanged for it. One action, **Replace the named source with a path** (`replaceNamedSource`), removes `srf:expansionSource` and writes `srf:membersPath` in the same edit, so exactly one of the two is stated after every edit (`srf:P20`). The part 2 behaviour and its tests are replaced.
- **The self-loop.** `classGraph` already kept an edge whose domain and range are one class. `ex:refinancesInChain` has its range `ex:Facility` again in `facility-baseline.ttl`, and the ontology view now shows 14 links where it showed 13, with a test of the loop in `ontologyGraph.test.ts`. Drawing it showed that the label of a loop covered the class it leaves, which `canvas/edges.test.ts` found for the facility drawing. `routeEdges` now puts a loop's label just beyond the loop's far point, moved along the side where another label is there, with a test.
- **The expression editor.** `surface/expressionEdit.ts` holds the edits, `surface/typing.ts` the typing, `surface/expression.ts` the reading, and `ui/ExpressionEditor.tsx` the editor. It opens on the canvas from a click on a derivation's result edge or its label, or from **Edit expression** where the derivation is drawn in full. The canvas kit gained `onEdgeClick` and a clickable edge label. `contractOf` now also finds a contract by the nodes its result edge claims, so selecting a derivation's result binding selects its contract.
- **Tests.** `surface/expression.test.ts` has 35 tests. The part 2 path mode tests were changed, `edges.test.ts` and `ontologyGraph.test.ts` gained one each, and `e2e/studio.spec.ts` has three new or rewritten journeys.

### Triples each edit writes

A new node is typed with its kind, states `srf:resultDatatype`, and is named in the baseline's namespace. A change of kind swaps the class and moves the operands by position. A rounding's scale is an `xsd:integer`, a choice's comparison is one of the six individuals, a literal states `srf:typedValue` with the datatype it states. An operand that goes takes with it each nested expression only it stated, so no node is left that `srf:P6` finds reached from nowhere. A refused edit returns the graph it was given, so undo history gains nothing.

### Typing rules followed

Those of the README's section 6.15, each as the shape that states it does, over the datatypes the direct operands state. An operand that states none has the datatype its own operands give.

- Numeric is integer, decimal, float or double. A sum, difference or product has the wider operand datatype under promotion, a quotient the same and at least decimal, a rounding its operand's, a choice the datatype of both branches, which must agree with each other and with the one it states. A typed literal has the datatype of its value, a plain literal being a string.
- Marked on a node: a missing part, a node or operand that states no datatype, a stated datatype that is not the one the rules give, an operand of arithmetic or rounding or of an ordering comparison that is not numeric, compared operands of different datatypes that are not both numeric, branches that disagree, a literal whose value is not of its datatype, an operand that is not evidence of the contract, a rounding with no scale, a choice with no comparison, and a result-target binding that states another datatype than the expression.
- The marks were checked against the shapes. 400 expressions of every kind over integer, decimal, float, string and literal operands were validated with pySHACL against the Surface shapes, and for each of the six families of finding the shape and the browser agreed on every case, 0 disagreements. This was a one-off check, and the script is not in the repository. The facility derivation has no mark, and the vitest cases state each rule.

### Choices the brief did not settle

1. **The tree is HTML, not React Flow.** Each node holds controls, so the tree is nested boxes with connectors in the canvas area, in place of the drawing as path mode is.
2. **The line is shown in both renderings.** The line mode is the line alone and the tree mode has the tree under the line.
3. **A new node states `xsd:decimal`,** the README's own example datatype, and nothing changes a stated datatype but the author. A mark offers **Use** the datatype that agrees, which is one edit.
4. **Operands move by position on a change of kind.** A sum's two operands become a product's, a rounding's operand a sum's left operand, a choice's compared operands a sum's. Those with no place go.
5. **The operand menu also offers an expression already in the tree** that would not be an operand of itself or of its ancestors, which makes a node stated twice. This is how `srf:P9` has a choice to refuse. The brief's list has no such choice, and it can be taken out.
6. **A typed literal's datatype is one of the four numeric ones,** and setting a literal node's datatype retypes its value, refusing a value not written as it.
7. **Neutral names.** A minted node is named after the contract, as `FacilityMarginExpression` and `FacilityMarginConstant`, since its kind can change.
8. **The brief's journey of the quotient** sees the datatype chip stay decimal, since a quotient of two decimals is decimal. The mark is shown by then stating integer.
9. **A named source with no property to stand for, or a name the vocabulary does not know,** is drawn with no path and cannot be replaced in path mode. The form edits it.
10. **A statement that states both a name and a path** is read as the path, and the first edit removes the name.
11. **The remembered rendering** is `lattice-studio:expression-view:<workspace>` in the browser, and the line where the browser keeps nothing.

### Unsure

In the dense facility drawing the loop on `Facility` leaves by the same side as most links, so its curve is crowded and its label sits some way above it. A loop leaving by the top side would be clearer, and is a change to the kit's rule.

### Results

- `yarn workspace @lattice/config-studio run check` passed, 39 files and 657 tests.
- `mise run test:config-studio` ran 81 journeys, 80 passed and 1 failed, the column handle test `a handle moves with the arrow keys`, which the part 1 results record as failing on the unchanged tree too. The new and rewritten journeys passed. The browser used the build the installed Playwright does not name, reached through a directory of links in the scratch area.
- `mise run check:workers` passed, 380 tests. `mise run check:config-studio` exited 0 when run alone, with 588 Python tests and 657 browser-code tests. `mise run check:identifiers` and `mise run check:published-decisions` passed.

The reviewer ran part 3's checks again on 2026-11-27: the app's check with 657 tests in 39 files, `check:config-studio` exit 0 with 588 Python tests and the Java modules' 9, 254, 10 and 85 tests with none failing, and `check:identifiers` and `check:published-decisions` passed. The journeys on the fake service were run by the delegated developer only, 80 of 81 passing, the one failure the column handle's test that TD-257 records.

## Part 4, the construction, join and expansion editors, and the loop rule

Built on 2026-11-28 in autonomous mode, from SVA-Q57 (b), the loop rule the maintainer accepted on 2026-11-27 and the declaration of `ex:refinances`.

### What changed

- **The loop rule, for every canvas.** `canvas/edges.ts` draws a loop on a side across the layout's flow, the top or the bottom in LR and the left or the right in TB, the one with fewer edge ends on the node, and the top, or the left, on a tie (`loopSide`). The loops of a node lie side by side along that side, as the maintainer's follow-up of 2026-11-28 decided (below), and the label of each lies just beyond its far point and never over a node. `canvas/layout.ts` leaves room for them (`loopRoom`). A node's loops take the gap on their side, and the nodes after it in the rank move on by what they need, so a loop and its label never meet a neighbour whatever the row or the column gap. The layout reads the ends across the flow from the edges between nodes of one rank, the only ones that end on those sides, and takes a node of unknown size as `DEFAULT_NODE_SIZE`. A graph with no loop is laid out as before. The kit passes a loop's label to the layout.
- **The facility sample** declares `ex:refinances` with the facility as its domain and range. The class graph draws 15 links where it drew 14, and the facility expansion's path now reaches a known class. The pinned counts of `ontologyGraph.test.ts`, the ontology journey and the samples README changed with it.
- **The pure part**, in `apps/config-studio/src/surface/`. `statement.ts` holds the context of a contract, the mark, the mint and the checks the editors share. `constructionEdit.ts` edits a constructed node and a node for each member, `joinEdit.ts` a join, and `expansionEdit.ts` an expansion. Each edit is a graph in and a graph out, one `model.edit`, and a refusal returns the graph it was given. Nodes and values are minted in the baseline's namespace as the expression editor mints, a new value, pair and binding by the contract's name and the property.
- **The editors**, `ui/ConstructionEditor.tsx` for a construction and for a node for each member, `ui/JoinEditor.tsx`, `ui/ExpansionEditor.tsx` and the shared `ui/StatementKit.tsx`. Each opens on the canvas from a click on the box of its statement, from an **Edit** button on the box and from the toolbar, which offers **Add a construction**, **Add a join** or **Add an expansion** where the result-target binding of that kind of contract states none. The expansion's box is the members node. Path mode (part 2) builds the link property and the members path, and returns to the editor. A place can now bar properties (`PathPlace.except`).
- **Tests.** 29 vitest tests in `surface/statements.test.ts`, and new and changed tests for the loop rule and the layout in `canvas/edges.test.ts` and `canvas/layout.test.ts`, which with the changed pins of `ontologyGraph.test.ts` make 723 tests where part 3 had 657. Four journeys in `e2e/studio.spec.ts`, and the ontology journey changed.

### Triples each edit writes

A new construction is a node typed `srf:ConstructedNode` with `srf:nodeIdentity srf:PerInstance`, stated by `srf:constructedAs` on the result-target binding. A value is a node with `srf:writesProperty` and either `srf:fromBinding` or `srf:fromMember true`. A key part is `srf:keyBinding`, the member as a part `srf:keyMember true`, and a stable name `srf:memberName`. A join is a node typed `srf:JoinStatement` stated by `srf:joinedAs`. A pair is a node with `srf:joinLeft` and `srf:joinRight` named by `srf:joinsOn`, and a binding the editor mints is typed, has the statement's evidence kind, `srf:bindsProperty`, and on the right `srf:bindsCarrier` and the pair's `srf:bindsDatatype`, and is added to the contract's `srf:hasRoleBinding`. A rule returned to its default removes `srf:joinMatches` or `srf:joinLinks`. An expansion is a node typed `srf:ExpansionStatement` with `srf:expandsFrom`, and its members are `srf:expansionSource` or `srf:membersPath`, never both. A node for each member is a construction on the binding that states the expansion.

### Laws the editors keep and mark

- **Never offered.** A member identity, key member, member name or value from the member unless an expansion stands beside the node (srf:P23). A key part that is not required evidence that binds a property (srf:P13), and any key under an identity that names none (srf:P24). A value read from a binding that is not the contract's evidence or that binds no property (srf:P12), a property written twice (srf:P11). Choosing an identity removes what it forbids. A left side of a pair that names the second carrier or a right side that names none or the contract's own, and any binding of the other evidence kind (srf:P16, srf:P17). An expansion from evidence that reads another carrier, that binds the property the result writes (srf:P21) or, where a path is stated, that the path does not read (srf:P20). The property the result writes is not offered the property the members are reached by in path mode. An expansion cannot be removed while a node for each member stands beside it (srf:P22).
- **Marked.** srf:P10 to srf:P25 as the README assigns them, each by the rule of the shape that discharges it, 45 families of finding in all, 19 for the constructed node, its values and its key, 14 for the join and 12 for the expansion. A mark never stops an edit.
- **Cross-check.** The marks were checked against pySHACL on the Surface shapes, as part 3's were. 800 random mutations of the facility surface part, each of one to four edits to the statements, their bindings, their pairs, their values, their members paths, the kinds of the contracts and their carriers, were validated with pySHACL against the shapes that state srf:P10 to srf:P25, and for each contract the families of finding the shapes report were compared with the families the marks name. 0 cases disagreed, and each of the 45 families was flagged by shape and mark together in at least one case. Where a statement is stated by bindings of two contracts a result names the statement alone, so 84 items of the families that read the stating contract's evidence were left out of both sides. A first run found two differences, a statement a contract states as another kind and a binding that states more than one carrier or a contract more than one kind, which the marks now read as the shapes do. This was a one-off check, and the script is not in the repository.

### Choices the brief did not settle

1. **The loop rule's way is the kit's own.** The kit does not use elk. Its layout is `canvas/layout.ts` and its routing `canvas/edges.ts`, and `elkjs` is in the tree only as a dependency of the documentation tooling. Its layered algorithm has self-loop options, but using it is BL-23's decision, so the loop rule grows the gap on the loop's side by the loops' reach in the kit's own layout.
2. **Which loop side the layout reserves.** The router counts the ends of the positions it is given. The layout counts them from the ranks, which agree wherever the nodes are where the layout put them. A node the author has moved keeps the side its place gives, and the room the layout left may not fit.
3. **Label placement.** Superseded by the follow-up below.
4. **A statement is edited from its box with a click.** A click on a statement box or the members node opens its editor and selects the statement's node in the form, and **Done** selects the contract.
5. **The new construction states a node for each instance,** the identity that merges nothing, and no class or value, which are marked until stated. A new join states no pair and a new expansion expands from the contract's one evidence binding where it has one.
6. **Written values, pairs and bindings are named nodes,** minted from the contract's name, where the sample writes blank nodes. Both are read, and a blank node is addressed by the key its term gives.
7. **A pair's comparison is `=`,** the only relation the vocabulary gives. Its datatype is the right binding's, offered from the XSD datatypes the README's examples use, and the left binding's datatype is read and marked but not set.
8. **The second carrier is stated on the right bindings,** so with no pair it is only chosen, and the first pair states it.
9. **Removing a pair removes the bindings nothing else refers to.** Superseded by the maintainer's choice of 2026-11-28 below.
10. **Changing the evidence an expansion with a path expands from** is offered only for properties the path reads. A named source is the way to another property, then **Replace the named source with a path**.
11. **A mark is shown on the part it concerns and the form's findings on the statement's nodes.** A finding on a blank node stays in the form's list, as in part 1.
12. **The mark for a statement stated by two contracts** names it for each, and the cross-check leaves those families out where it cannot tell the contract.

### Slice acceptance, checked against what is built

The plan's SVA-S1 row states the slice's acceptance as "a path built on the canvas writes the triples the hop-by-hop control writes". Part 2's tests of each place a path is built compare the canvas's triples with `writePath`'s for the same steps, and its journey checks the form's hop-by-hop control shows the hops built on the canvas, so the acceptance is met. The row's scope, the canvas drawing every kind, a path built by clicking, the expression editor with its tree and the construction, join and expansion editors, is built across parts 1 to 4. The targets drawn as instances (SVA-Q62 (b)) and the simulator pane are SVA-S3's.

### Unsure

A loop is drawn from the layout's own place and the room it left. A node the author drags next to another can still meet a loop, since the router keeps the rule and not the room. The editors offer properties of the ontology as the part 2 rules do, so a class that is not known offers every property.

### Results

- `yarn workspace @lattice/config-studio run check` passed, 40 files and 723 tests.
- `mise run test:config-studio` ran 86 journeys and 86 passed, the column handle test included on this run. The 4 new journeys, the changed ontology journey and every earlier journey passed. The browser used the build the installed Playwright does not name, reached through a directory of links in the scratch area.
- `mise run check:workers` passed, 380 tests. `mise run check:config-studio` exited 0 when run alone, with 588 Python tests, the Java modules and the same 723 browser-code tests. `mise run check:identifiers` and `mise run check:published-decisions` passed, the second with 6 tests.
- The writing rules were run on this pack and the samples README, with no failure and no warning.

The reviewer ran part 4's checks again on 2026-11-28, with nothing else running: `check:config-studio` exit 0, with the app's 723 tests in 40 files, 588 Python tests and the Java modules' surefire reports showing no failure (config-studio-authoring 9, config-studio-service 254, config-studio-writer 10, config-studio-transforms 78), `check:workers` 380 passed, and `check:identifiers` and `check:published-decisions` (6) passed. The journeys on the fake service were run by the delegated developer only, 86 of 86 passing. The reviewer saw the screenshots. In the class graph and the top-down view a second loop's label sits far from its loop, beyond the first loop's label, which reads as detached, and the screenshot of a top-down view came from a harness outside the repository, since no canvas in the app is laid out top-down with a loop.

### Follow-up, the labels of several loops on one node

The maintainer asked on 2026-11-28 for the labels of several loops on one node to be fixed, since the second label sat far from its loop. Loops nested one outside the other cannot hold a wide label, because the outer loop's legs bend inward and cross the label of the loop inside it, and `ex:refinances` is about 100 pixels wide on a side of 250. The loops of one node now lie side by side along their side (`loopSpan`): one loop spans the middle half of the side as before, and several share its middle three quarters in equal parts, each reaching as far out. A loop's label is tried just beyond its own loop, and where a node or the label of a loop beside it is in the way, at the nearest free place out from the side or along it by whole labels, so in TB a second label moves 27 pixels along the side rather than a label's width outward. `loopRoom` reserves the loops' reach and a label for each loop. A test with labels as wide as the facility sample's checks that each loop has its own part of the side, every loop reaches as far out, and no loop passes through another loop's label, and it fails on the nested routing. In the facility class graph the second loop's label sits one label above its loop, because the two labels are wider than their parts of the side.

The reviewer ran the app's check after the follow-up, 724 tests in 40 files passed, and the journeys on the fake service, 85 of 86 passing in the full run. The one failure was the column handle's test that TD-257 records, which passed when run again alone.

### Follow-up, a binding no statement reads

The maintainer chose on 2026-11-28 that removing a join pair, or changing one of its sides, never removes a binding, since an author part way through wiring a statement would lose work. A required-evidence binding is not only wiring, because an instance that lacks its value is excluded from the contract, so a binding left read by nothing is marked rather than removed. `unreadEvidence` in `surface/statement.ts` gives each required-evidence or candidate-evidence binding of a projection contract that nothing names an Info mark on the edge that reads it. It says that required evidence still excludes an instance that lacks the value, or that a candidate binding has no effect. The mark is information and no law, so it is not one of the form's findings and never counts as one left in the form's list. It goes as soon as a statement reads the binding again. Tests cover removing a pair, removing the join, changing a side, and a candidate binding, and that the facility sample's contracts read every binding they state. A removal of every unread binding in one action is not built and waits on the maintainer.

The reviewer ran the app's check after this follow-up, 726 tests in 40 files passed. In a full run of the journeys 84 of 86 passed. The composite key journey, which expected the old rule, was changed to expect the bindings kept and marked, and passed. The column handle's test failed with the symptom TD-257 records, the handle reading 300 where 316 was expected, and passed three times in three when run alone.
