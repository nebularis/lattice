<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Configuration Studio samples

Every example the [Configuration Studio](../../../apps/config-studio) can be shown with, grouped by what it demonstrates. Each example lists what it demonstrates, where its documents are, which studio sample offers it, and the steps to demonstrate it. A studio sample is an entry of [`samples.ttl`](samples.ttl), which the studio lists under New workspace. An example with no studio sample is opened from its files.

## Before you start

Start the studio with `mise run studio:up -- --dev` and browse <http://127.0.0.1:4175>. `mise run studio:down` stops it. The [operations guide](../../../docs/operator/configuration-studio-operations.md) says what the stack needs.

To open a studio sample, press **New workspace**, choose the card with the sample's label and press **Create workspace**. To open an example from its files, choose the **Your own Turtle** card instead, name the workspace, choose the files and press **Create workspace**. The studio sorts each subject of the files into the baseline or the part its terms belong to.

| Studio sample | Key | Example |
|---|---|---|
| Policies from XML and JSON | `policies-transforms` | [runs, and mapping over XML and JSON](#policies-from-xml-and-json) |
| Library, with imports | `library-imports` | [imports from LATTICE's documents](#library-with-imports) |
| Fleet axioms | `axioms` | [the axiom forms](#fleet-axioms) |
| Facility agreement, every part | `facility` | [drawing](#facility-agreement-the-drawing), [persistence](#facility-agreement-persistence-canvas-and-simulator), [surface canvas](#facility-agreement-surface-canvas), [surface](#facility-agreement-surface-steps) and [vocabulary, quantities and eligibility](#facility-agreement-vocabulary-quantities-and-eligibility) |
| Species, an RDF mapping in two strata | `species-mappings` | [an RDF mapping with strata and a closure](#species-an-rdf-mapping-in-two-strata) |
| Policies from CSV | `policies-csv` | [a CSV source and the waiting RML form](#policies-from-csv-and-from-yaml) |
| Policies from YAML | `policies-yaml` | [a YAML source and the waiting RML form](#policies-from-csv-and-from-yaml) |
| ODRL mappings | `odrl-mappings` | [the ODRL pack](#odrl) |
| LegalRuleML mappings | `legalruleml-mappings` | [the LegalRuleML pack](#legalruleml) |
| Lending | `lending` | [the lending sample](#lending) |
| Lending eligibility | `lending-eligibility` | [eligibility](#lending-eligibility) |
| Scheme bindings | `vocabulary-bindings` | [vocabulary](#scheme-bindings) |
| Quantities and units | `quantities` | [quantification](#quantities-and-units) |
| Employment job families | `employment` | [a surface index](#employment-job-families) |
| SaaS subscriptions | `saas` | [a surface promotion](#saas-subscriptions) |
| Contract builder, a facility form | `builder` | [the builder](#contract-builder-a-facility-form) |

## Runs

A run executes a compiled mapping or one step of a simulator over an input the studio does not save, and its result reaches the browser as numbered frames.

### Policies from XML and JSON

**Demonstrates:** a mapping of policies with their holders and covers, written twice, as a scheme over an XML source and a scheme over a JSON source. The XML scheme compiles to an XSLT stylesheet and the JSON scheme to a JOLT chain. A sample runs when Run is pressed and never by itself, shows each mapping's output and counts, and marks the counts out of date when the scheme or the sample changes. The run worker answers a run over XML or JSON.

**Documents:**

- [`xml.mork.ttl`](../../../tools/mork_transforms/tests/examples/policies/xml.mork.ttl) and [`json.mork.ttl`](../../../tools/mork_transforms/tests/examples/policies/json.mork.ttl), the two schemes
- [`policies-sources.ttl`](policies-sources.ttl), which carries each example source for the Sample pane to offer
- [`source.xml`](../../../tools/mork_transforms/tests/examples/policies/source.xml) and [`source.json`](../../../tools/mork_transforms/tests/examples/policies/source.json), the same two sources as files
- [`expected.nt`](../../../tools/mork_transforms/tests/examples/policies/expected.nt), what a run writes from either source
- [`compiled/xml.xsl`](../../../tools/mork_transforms/tests/examples/policies/compiled/xml.xsl) and [`compiled/json.jolt.json`](../../../tools/mork_transforms/tests/examples/policies/compiled/json.jolt.json), the compiled forms, each with its attribution table, [`xml.xsl.attribution.json`](../../../tools/mork_transforms/tests/examples/policies/compiled/xml.xsl.attribution.json) and [`json.jolt.json.attribution.json`](../../../tools/mork_transforms/tests/examples/policies/compiled/json.jolt.json.attribution.json)

**Studio sample:** Policies from XML and JSON (`policies-transforms`)

**Steps:**

1. Make a workspace from the sample and open the Mapping view. The list on the left holds two schemes, one for each source.
2. Open the Sample tab of the dock and press **Use the XML example**. Nothing runs yet.
3. Press **Run**. The pane compiles the mapping part, runs the XSLT form and reports `Complete, 7 parts` with the engine that evaluated it, Saxon-HE and XSLT 3.0. Each mapping's output is under its part, and the tree and the scheme list show how many triples each mapping wrote.
4. Edit the sample's text. The counts are marked out of date and nothing runs until **Run** is pressed again.
5. Press **Clear**, then **Use the JSON example** and **Run**. The JSON scheme runs its JOLT form and reports `Complete, 7 parts`.
6. The JSON scheme also lists an RML form marked `No runtime yet`. Choose it. **Run** is off, and the pane says `Waits on an RML runtime.`
7. To read what a run's output looks like in each rendering, see [the output explorer](#reading-a-runs-output).

### Run frames

**Demonstrates:** the frames a run's result arrives as, in the three shapes a client meets. A run that completes, a run that could not start, and a run that missed its deadline, whose lost frame the client reports.

**Documents:**

- [`run-frames.example.json`](run-frames.example.json), a complete small `sample` run as a request with `wait=true` answers it. It has a report part, two artefact parts and a last frame that succeeded
- [`run-frames-failed.example.json`](run-frames-failed.example.json), a run that could not start, which is one failed frame
- [`run-frames-deadline.example.json`](run-frames-deadline.example.json), a run whose frame 2 never arrived and whose last frame is the service's failed frame at the deadline
- [`run-frame.schema.json`](../run-frame.schema.json), the schema each of them is valid against

**Studio sample:** none, opened from a file

**Steps:**

1. Open `run-frames.example.json`. Its four frames are numbered 0 to 3, and only the last has `last` set and a `status` of `succeeded`.
2. Open `run-frames-failed.example.json`. One frame has `seq` 0, `last` set and a `status` of `failed` with its message.
3. Open `run-frames-deadline.example.json`. The numbers 0, 1, 3 and 4 are present and 2 is missing, so the run is incomplete, yet its failed last frame settles it.
4. The same shape comes back from a live run. [The request](../README.md#the-request) says how to send one with `wait=true`.

### The failure cases of a run

**Demonstrates:** that a run survives the faults of a real stack. A worker stopped in the middle of a run does not run it twice, an instance that stops takes its runs with it, a workspace locked during a run hears nothing more, a tab that was away learns the run failed, a run no worker takes expires, and a tab holds at most four runs.

**Documents:** none to open. The suite carries the XML example of [the policies sample](#policies-from-xml-and-json) as its input and starts its own broker, store, workers and two service instances.

**Studio sample:** none, the suite carries its input

**Steps:**

1. Run `mise run studio:runs`. It runs on demand and never as part of `mise run check`.
2. Read each test's result. The worker-stopped case is `test_r5_t3_a_worker_that_stops_mid_run_does_not_run_it_twice`.

## Imports

An author imports an ontology with its own imports resolved from a catalog, and sees what is missing.

### A folder with a catalog

**Demonstrates:** an ontology whose imports a catalog resolves. Of its three imports the catalog resolves two, one to a file named as the import is and one to a file of an unrelated name. The third has no file and no catalog entry, so the import dialog reports it missing. Nothing is held until the author confirms, and a missing import never blocks the rest.

**Documents:**

- [`imports/base.ttl`](imports/base.ttl), the root ontology, which imports `https://example.org/import-folder/vehicles`, `https://example.org/import-folder/depots` and `https://example.org/import-folder/calendar`
- [`imports/catalog-v001.xml`](imports/catalog-v001.xml), the catalog, with an entry for `vehicles` and one for `depots`
- [`imports/vehicles.ttl`](imports/vehicles.ttl), the vehicles ontology, named as its import is
- [`imports/export-0417.ttl`](imports/export-0417.ttl), the depots ontology, in a file whose name says nothing of it

**Studio sample:** none, opened from a file

**Steps:**

1. Choose **New workspace** and the **Your own Turtle** card, name the workspace, choose `imports/base.ttl` and press **Create workspace**.
2. Open the Baseline view. The Ontologies list shows three imports as `missing` and says `3 imports are not held.`
3. Press **Import ontologies**. Under **Folder**, choose the `imports` folder, or drop it on the drop area. The chosen files list the catalog with a `catalog` chip.
4. Press **Show the plan**. The vehicles and depots imports resolve `from the catalog`, the depots import to `imports/export-0417.ttl`. The calendar import is `missing`. The status reads `2 to hold now, 0 already held, 1 missing.`
5. Press **Hold 2 imports**. The Ontologies list shows two imports `held` and says `1 import is not held.`
6. To see a missing import reported before anything is held, repeat steps 3 and 4 choosing the same files with **Files** and leaving out `vehicles.ttl`. The plan then names the catalog's entry as `The catalog maps https://example.org/import-folder/vehicles to vehicles.ttl, which was not dropped.` and the status reads `1 to hold now, 0 already held, 2 missing.`
7. Open **Diagram** and choose **Import graph**. It draws the workspace's ontology, the two held imports and the missing one, and the status reads `1 ontology of the workspace, 2 imports held, 1 missing, 0 schemes.`

### Library, with imports

**Demonstrates:** imports resolved from LATTICE's own documents with no file given. The baseline imports the vocabulary layer, which imports the foundation layer, and uses a foundation term without importing that layer. The import graph draws a stated import, a binds edge and an edge derived from the term used.

**Documents:**

- [`library-baseline.ttl`](library-baseline.ttl)
- [`library-vocabulary.ttl`](library-vocabulary.ttl)

**Studio sample:** Library, with imports (`library-imports`)

**Steps:**

1. Make a workspace from the sample and open the Baseline view.
2. Press **Import ontologies**, then **Show the plan**, and press **Hold 2 imports**. The plan resolves both from LATTICE's documents.
3. Open **Diagram** and choose **Import graph**. Four nodes are drawn, and the status reads `1 ontology of the workspace, 2 imports held, 0 missing, 1 scheme.`
4. Hold the pointer over the edges. The library imports the vocabulary layer, the vocabulary layer imports the foundation layer, the scheme contract binds the sample's own scheme of subject headings, and a dashed edge marked as derived joins the library to the foundation layer.

## Ontology drawings and axioms

### Facility agreement, the drawing

**Demonstrates:** the ontology drawn as classes and the properties that link them, with and without the links its shapes state, and as a class hierarchy.

**Documents:**

- [`lending-baseline.ttl`](lending-baseline.ttl), the lending baseline that the facility baseline extends
- [`facility-baseline.ttl`](facility-baseline.ttl), the facility, its lenders and drawdowns, the boundary shape of the facility and the carrier data

**Studio sample:** Facility agreement, every part (`facility`)

**Steps:**

1. Make a workspace from the sample and open the Baseline view. Press **Diagram** in the detail pane.
2. The drawing shows the classes of the baseline, and the status reads `12 classes and 14 links drawn.` The property `refinances in chain` has the facility as its domain and its range, so it is drawn as a loop on `Facility`.
3. Tick **Include shapes**. The facility's shape states four of the links, none is added, and the status reads `12 classes and 14 links, 4 stated by shapes drawn.` Hold the pointer over a link to read `stated by ex:FacilityShape`.
4. Choose **Class hierarchy**. The status reads `12 classes and 3 links drawn.` Choose **Classes and properties** again.
5. Click the Drawdown class. The list selects it, and the status says the drawing is around Drawdown. **Hops around the selected class** takes more or fewer neighbours.
6. Drag a class. Its links and their labels follow it, and the class stays where it was left after the page is loaded again.

### Fleet axioms

**Demonstrates:** what the Baseline view's axiom forms read. Selecting a class or a property shows each construct in a section of its own and never as text, and any statement the reader does not know is listed under Other statements, which is empty here. The forms only read.

**Documents:** [`axioms-baseline.ttl`](axioms-baseline.ttl), with a restriction in each quantifier on `ex:Van` and `ex:Lorry`, an equivalent class that is an intersection holding a restriction on `ex:ElectricVan`, disjointness of `ex:Van` and `ex:Lorry`, a key and labels in two languages on `ex:Vehicle`, a datatype restriction on `ex:weight` and property characteristics on `ex:axleOf` and `ex:registration`.

**Studio sample:** Fleet axioms (`axioms`)

**Steps:**

1. Make a workspace from the sample and open the Baseline view. Keep **Details** chosen in the detail pane.
2. Select Van. The **Superclasses** section lists Vehicle, a restriction that some axle is an Axle and one that it has at most 2 axles. The **Disjoint classes** section lists Lorry.
3. Select Lorry. The **Superclasses** section lists a restriction of at least 3 heavy axles and one that every axle is a heavy axle.
4. Select Electric van. The **Equivalent classes** section shows an intersection of Van and a restriction with the value `electricity`.
5. Select Vehicle. The **Annotations** section groups the labels by language, and the **Keys** section lists the registration.
6. Select the properties `weight`, `axle of` and `registration`. The **Range** section of `weight` shows a datatype restriction with a minimum and a maximum, and the **Characteristics** section of the other two says functional.

## Persistence

### Facility agreement, persistence canvas and simulator

**Demonstrates:** where the facility's data lands once its persistence configuration is compiled, drawn as a canvas, and a simulator that runs one write at a time over a sample world. The simulator shows what a write does to each graph, which landing places it wrote, and what a second writer's lost race looks like.

**Documents:**

- [`lending-baseline.ttl`](lending-baseline.ttl) and [`facility-baseline.ttl`](facility-baseline.ttl), the baseline
- [`facility-persistence.ttl`](facility-persistence.ttl), the persistence configuration
- [`facility-vocabulary.ttl`](facility-vocabulary.ttl), the vocabulary that scopes a key
- [`facility-step-create.trig`](facility-step-create.trig), a step that creates `facility-1` in an empty world, with the operation `create-if-absent`
- [`facility-step-replace.trig`](facility-step-replace.trig), a step that changes the margin of `facility-1` with the operation `cas-replace`, which keeps a patch log. Sending it from position 1 instead of 2 shows the guard refusing a write made from an earlier position
- [`simulator-facility-journey.json`](../../../apps/config-studio/e2e/fixtures/simulator-facility-journey.json), the four steps the browser sends, the create, the replace, the replace as another writer and the generated create, each with the frames a worker answered
- [`compiled-profile-facility.ttl`](../../../apps/config-studio/e2e/fixtures/compiled-profile-facility.ttl) and [`compiled-profile-facility.paths.txt`](../../../apps/config-studio/e2e/fixtures/compiled-profile-facility.paths.txt), the compiled profile the canvas draws and the paths of the files a compilation writes

**Studio sample:** Facility agreement, every part (`facility`)

**Steps:**

1. Make a workspace from the sample, open the Persistence view and choose **Canvas** in the detail pane. It says `No persistence compilation yet`. Press **Compile**.
2. Choose the target **Facility**. The canvas draws the root Facility, its owned Drawdown, three references drawn dashed, `arrangedBy`, `borrower` and `lender`, and seven landing places, among them `urn:g:facilities`, `urn:g:meta/6`, `urn:g:keys` and the patch logs `{newRev}/add` and `{newRev}/del`.
3. Open the **Simulator** tab and choose the target **Facility**. The sample world holds 0 steps.
4. Step 1, a create. Fill the facility reference, commitment, margin, arranged by, borrower, lenders and a drawdown, or press **Generate from the shape**, which fills what the boundary shape requires and nothing else. Press **Run**. The outcome is `Applied`, the delta lists the graphs written, and the canvas lights five landing places.
5. Step 2, a replace. Choose **Replace**, change the margin and press **Run**. The removed patch log is written, six places are lit, and the delta shows the old margin removed.
6. Step 3, a lost race. Tick **As another writer** and press **Run**. The guard refuses the step, the outcome is `Lost race` with `PreconditionFailed`, nothing is lit, and the world stays as it was.
7. Press **Step back** twice to return to the empty world.
8. **Delete** is a write kind the same profile offers, run as a tombstone. No stored step holds one, and the pane builds it from the profile. **Append** is off, since the profile has no append operation a step runs.
9. To give the object as Turtle, choose **Turtle** under Object source. A blank node is refused before anything is sent.

### Facility agreement, surface steps

The facility sample's surface part promotes a borrower's sector onto the facility's drawdowns over a three-hop read path, indexes borrowers by sector and holds six projections. The steps below follow one edit into the rows a promotion keeps.

**Demonstrates:** the surface simulator's step, which runs the writer's own maintenance over the world before an edit and the world after it and answers each contract's rows before and after, the rows asserted and retracted, and each contract whose read set the edit touched.

**Documents:**

- [`facility-surface.ttl`](facility-surface.ttl), the surface configuration with its promotion, index and six projections
- [`facility-surface-step-first.trig`](facility-surface-step-first.trig), the first drawdown is added to a world with none, so the first instance of a class names its contracts
- [`facility-surface-step-drawdown.trig`](facility-surface-step-drawdown.trig), a drawdown is added under `facility-1`
- [`facility-surface-step-repay.trig`](facility-surface-step-repay.trig), every drawdown is removed
- [`facility-surface-step-borrower.trig`](facility-surface-step-borrower.trig), `facility-1` changes its borrower, so its drawdowns change sector
- [`facility-surface-step-sector.trig`](facility-surface-step-sector.trig), the borrower `acme-foods` changes sector, which the rows read from the borrower's graph
- [`facility-surface-step-subtype.trig`](facility-surface-step-subtype.trig), a revolving drawdown typed by a subclass of the carrier's class is added
- [`facility-surface-step-vocabulary.trig`](facility-surface-step-vocabulary.trig), the vocabulary says a revolving drawdown is a drawdown, which retypes a drawdown the facilities graph holds
- [`facility-surface-step-projection.trig`](facility-surface-step-projection.trig), a step whose edit changes what five of the six projections write. It is a surface step and a projection step, so it is sent as a `surface` run and as a `projection` run

**Studio sample:** Facility agreement, every part (`facility`)

**Steps:**

1. Make a workspace from the sample and press **Compile surface** in the Build view. The finished job is the one a step runs against, and its identifier is the run's `job` parameter.
2. Send a step file as the body of a `simulate` run of target `surface`, with `Content-Type` `application/trig`, `wait=true` and the job's id, as [A surface step](../README.md#a-surface-step) states. Use `facility-surface-step-first.trig` first.
3. Read the answer. It holds the compile job's checks, each contract's rows before and after, the rows the edit asserted and retracted, and which contracts' read sets it touched, with the engine named.
4. Send the others and compare. Each file's header says what its edit does, for example that the `repay` step removes every drawdown, that the `borrower` and `sector` steps change the sector the drawdowns' rows read, and that the `subtype` and `vocabulary` steps reach a drawdown through the class hierarchy.
5. Send `facility-surface-step-projection.trig` as a `simulate` run of target `projection`. [A projection step](../README.md#a-projection-step) lists its parts, one for each of the six projections.
6. The studio has no surface simulator pane yet, so these steps are sent through the run request and are checked by the worker and service suites, `mise run check:workers` and `mise run check:config-studio`.

### Facility agreement, surface canvas

**Demonstrates:** the surface canvas, which draws each contract of the facility sample's surface part from its carrier class, through what is read from it, to what is written. It draws the promotion over its three-hop read path, the index, and a projection of each kind, a derivation, two constructions, a join, an expansion and a node for each member. All contracts are an overview of carriers, contracts and targets, and the contract selected in the list expands in place. The targets a contract writes are drawn as types from the baseline in three states, declared, undeclared and with a declared range that disagrees with the contract, and a small box for each projection reads the lowered scheme from a surface compilation. A path is built by clicking, in path mode, and an expression is edited as a line of text or as a tree.

**Documents:**

- [`facility-surface.ttl`](facility-surface.ttl), the surface configuration the canvas draws
- [`lending-baseline.ttl`](lending-baseline.ttl) and [`facility-baseline.ttl`](facility-baseline.ttl), the ontology the targets are read from. It declares most of the terms the projections write with their ranges, leaves `ex:bookedAt` undeclared and declares `ex:marginWeightedCommitment` with the range `xsd:integer` where its contract states `xsd:decimal`, each on purpose and each with a comment
- [`compiled-surface-facility.json`](../../../apps/config-studio/e2e/fixtures/compiled-surface-facility.json), the `projections` group and the findings of the surface compilation, which the browser journeys' fake service serves and the worker's own test keeps equal to what the compiler gives

**Studio sample:** Facility agreement, every part (`facility`)

**Steps:**

1. Make a workspace from the sample, open the Surface view and choose **Canvas** in the detail pane. Nothing is selected, so the canvas is the overview of all eight contracts, with a carrier for each class they read from and the terms they write. Select a contract in the list, then **All contracts**, and that contract is drawn in full among the others.
2. Select `facility-margin` in the list. The result edge reads `commitment × margin : decimal`, the two required evidence nodes are solid, and the target `margin weighted commitment` is marked `range disagrees`, since the ontology declares an integer range. The scheme box says there is no compilation yet. The form below the canvas edits the contract as before.
3. Select `facility-branch`. A box for the second carrier, `Branch`, joins its code to the facility's by an edge marked `=`, and the join box states its two cardinality rules, both marked `(default)`. The target `bookedAt` is marked `undeclared`.
4. Select `facility-covenant-test` to see the members path `covenants`, `rdf:rest *`, `rdf:first`, and the node made for each member with its identity and what it writes from the member. Select `facility-refinancing` to see a closure marked on a dashed hop.
5. Press **Compile**. Each scheme box now gives its name, its mappings and its review findings, for example `MappingReview × 1` for the join. Click it to open the lowered scheme in the mapping canvas, read only, with the terms each mapping writes and the review findings on the mappings they concern.
6. Edit the surface part, for example add a promotion. The boxes are marked out of date until the next compilation.
7. A click on a node of the canvas selects the matching node in the form. The findings the form shows for a node are drawn on the element they concern, for example the undeclared property on the result edge.
8. To build a path, select `drawdown-sector` and press **Build path** on its carrier. Path mode shows the class at the end of the path, outgoing properties to its right and incoming ones to its left. **Undo** the three hops, then click `drawn under`, `borrower` and `legal name`. A datatype property ends the path. The form's hop-by-hop control below shows the same hops at once, and an edit there shows on the canvas. **Done** leaves the path as written.
9. Select `facility-refinancing` and press **Build path** on its members node. The expansion names `srf:TransitiveClosure`, so path mode draws the path the name stands for, `refinances +`, marked **given by the name**, and edits nothing. **Replace the named source with a path** removes `srf:expansionSource` and writes the path as `srf:membersPath` in one edit. The hop `refinances` then has a toggle for one or more times and zero or more times, written as `sh:oneOrMorePath` or `sh:zeroOrMorePath`.
10. To edit an expression, select `facility-margin` and press **Edit expression**, or click the result edge `commitment × margin : decimal` or its label. The expression opens as that one line of text, which is read only. Choose **Tree** to draw one node for each expression node, each with its kind, its datatype and its operands as children. The choice of rendering is kept in this browser for the workspace.
11. In the tree, change the **Kind** of the product to a quotient. Both operands stay and the line reads `commitment ÷ margin : decimal`. Set its **Datatype** to integer and the node marks that it states integer where its operands give decimal, with a button that states the datatype that agrees. Each change is one edit, so **Undo** in the toolbar takes it back.
12. Each operand has an **Operand** choice of the contract's own evidence, which never offers its subject or its result, a new expression, a typed literal with its value and datatype, or an expression already in the tree that would not be an operand of itself. **Remove** leaves a placeholder. A rounding has a scale, which may be negative, and a choice has one of six comparisons. To build an expression, remove the root with **Remove**, and the editor offers **Add an expression**, then add a rounding, set its operand to a new sum, and set the sum's operands to the two evidence bindings.

## Mapping

Mapping mode lists every mapping scheme of the workspace on the left, explores and edits each scheme, and runs the compiled scheme over a sample source in the dock's Sample pane when **Run** is pressed.

### Reading a run's output

**Demonstrates:** an artefact of a run shown as Turtle text, as a table that filters and as a graph, with the choice kept in the browser for the media type.

**Documents:** those of [the policies sample](#policies-from-xml-and-json).

**Studio sample:** Policies from XML and JSON (`policies-transforms`)

**Steps:**

1. Follow steps 1 to 3 of [the policies sample](#policies-from-xml-and-json), so that a run has finished.
2. Open the artefact of part 2. Turtle text is the default, and **N-Triples** is offered beside **Turtle**.
3. Choose **Table**. The triples are rows, and the search box filters them.
4. Choose **Graph**. The nodes are drawn on the canvas.
5. Reload the page and run again. The artefact opens as a graph, as it did before.
6. Open the report part. It is Turtle text with `sh:conforms` and the engine, and it too can be read as a table.

### Species, an RDF mapping in two strata

**Demonstrates:** a mapping over an RDF source that is compiled to SPARQL and run in two strata, with a closure. A species record makes a class, so the animal mapping, which looks that class up by name, runs in stratum 1. The property mapping creates a property whose domain is a union of the classes stratum 0 made, which a closure query states once those classes exist. A record that names a species no record creates is reported as unresolved.

**Documents:** [`species-mappings.ttl`](species-mappings.ttl), the scheme, which carries its example source as the example of its representation scheme.

**Studio sample:** Species, an RDF mapping in two strata (`species-mappings`)

**Steps:**

1. Make a workspace from the sample and open the Mapping view.
2. Open the Sample tab and press **Use the Turtle example**, then **Run**.
3. The form is the SPARQL CONSTRUCT the scheme compiles to, and the run reports `Complete, 6 parts, conforms.` The parts are the report and five outputs. `0/CreateSpecies.nt` holds the classes `Falcon` and `Owl`, `0/Animal.nt` holds the two animals, `1/AnimalSpecies.nt` types the Falcon animal with its class, which only stratum 1 can read, `0/Knows.nt` holds the property and `1/Knows.nt` holds the closure, the property's domain as a union of both classes and `tgt:Animal`.
4. The report holds three warnings, two that the scheme creates classes and a property from the source's values, and one that no reference node matches the value `Dodo`, so that animal is not typed with a class.

### Policies from CSV and from YAML

**Demonstrates:** that a scheme over a CSV source and a scheme over a YAML source compile to RML, and that the Sample pane lists that form as waiting for a runtime and keeps **Run** off, as it does for the JSON scheme. The RML form belongs to the first scheme of a mapping part, so each format has a sample of its own.

**Documents:**

- [`csv.mork.ttl`](../../../tools/mork_transforms/tests/examples/policies/csv.mork.ttl) and its source [`source.csv`](../../../tools/mork_transforms/tests/examples/policies/source.csv), one row for each policy and cover
- [`yaml.mork.ttl`](../../../tools/mork_transforms/tests/examples/policies/yaml.mork.ttl) and its source [`source.yaml`](../../../tools/mork_transforms/tests/examples/policies/source.yaml), the JSON source written as YAML

**Studio sample:** Policies from CSV (`policies-csv`) and Policies from YAML (`policies-yaml`)

**Steps:**

1. Make a workspace from **Policies from CSV** and open the Mapping view. Open the **Sample** tab and paste the text of `source.csv` into the sample box. The sources are not offered as examples, since no runtime reads them.
2. Press **Run** once. The pane compiles the mapping and then sends the text, which the studio reads as Turtle, so the run itself reports a failure. The compile is what matters here, and the **Compiled form** group now lists **RML** with `mapping.rml.ttl` and `No runtime yet`.
3. Choose **RML**. **Run** is off and the pane says `Waits on an RML runtime.`
4. Repeat with a workspace made from **Policies from YAML** and the text of `source.yaml`.

### Catalogue, an RDF mapping from a file

**Demonstrates:** a mapping with one mapping for each construct the SPARQL backend covers, run over an RDF sample. A run is reported as not conforming, since the catalogue holds records the mapping cannot place.

**Documents:**

- [`catalogue-mapping.ttl`](../../../tools/mork_rdf/tests/fixtures/catalogue-mapping.ttl), the mapping
- [`catalogue-source.ttl`](../../../tools/mork_rdf/tests/fixtures/catalogue-source.ttl), the sample source of four records
- [`catalogue-reference.ttl`](../../../tools/mork_rdf/tests/fixtures/catalogue-reference.ttl) and [`catalogue-vocabulary.ttl`](../../../tools/mork_rdf/tests/fixtures/catalogue-vocabulary.ttl), the reference data and the target vocabulary the library's own tests run it with

**Studio sample:** none, opened from a file

**Steps:**

1. Open the **Your own Turtle** card and choose `catalogue-mapping.ttl`.
2. Open the Mapping view and the Sample tab. Paste the text of `catalogue-source.ttl` into the sample box. Its format is Turtle.
3. Press **Run**. The pane reports `Complete, 10 parts, does not conform.`, the form is the SPARQL CONSTRUCT, and each mapping's output is under its part.

### ODRL

**Demonstrates:** the hand-made MORK mapping pack from an ODRL 2.2 policy to stated meaning, run over a sample policy, and a language model's proposal for the same source with each mapping reviewed against the pack. The policy can also be imported in the Meaning view.

**Documents:**

- [`odrl-instrument.mork.ttl`](../odrl/odrl-instrument.mork.ttl), the pack
- [`odrl/trial/history.ttl`](../odrl/trial/history.ttl), the proposal and its reviews
- [`software-licence.odrl.ttl`](../odrl/software-licence.odrl.ttl), the sample source for a run, as Turtle
- [`software-licence.odrl.jsonld`](../odrl/software-licence.odrl.jsonld), the same policy as JSON-LD, which the Meaning view's import reads
- [`odrl.jsonld`](../odrl/odrl.jsonld) and [`odrl22.ttl`](../odrl/odrl22.ttl), the ODRL context and vocabulary the studio reads without fetching them

**Studio sample:** ODRL mappings (`odrl-mappings`)

**Steps:**

1. Make a workspace from the sample and open the Mapping view. The hand-made pack is the first scheme, and the proposal is beside it, each mapping with its review.
2. Open the Sample tab, press **Load a file** and choose `software-licence.odrl.ttl`, then press **Run**. Each mapping's output is under its part.
3. To import the policy as stated meaning, make a workspace from [the contract builder sample](#contract-builder-a-facility-form), open the Builder, choose Meaning, choose `software-licence.odrl.jsonld` under **Import ODRL policy**, tick **This file is an ODRL 2.2 policy** and press **Import**. The outcome says how many proposals were added.

### LegalRuleML

**Demonstrates:** two proposals mapping LegalRuleML's metamodel to stated meaning, one made cold and one made with the ODRL trial's history, each mapping with its review. LegalRuleML's source is RDF in the metamodel's terms, so its sample sources are Turtle. Two LegalRuleML documents are offered with the RDF each gives, an OASIS example and the project's own clean-room document of a cover, an exclusion and a condition.

**Documents:**

- [`legalruleml/trial/history.ttl`](../legalruleml/trial/history.ttl), both proposals and each review
- [`sample-supply-terms.ttl`](../legalruleml/trial/sample-supply-terms.ttl), the sample source, a made-up supply agreement in the metamodel
- [`legalruleml-metamodel.ttl`](../legalruleml/trial/legalruleml-metamodel.ttl), the metamodel as one Turtle source, which the proposer reads
- [`rdfs/`](../legalruleml/rdfs), the twelve RDFS files of the metamodel, copied from OASIS with their notice
- [`ex5-section29new-compact.lrml`](../legalruleml/examples/ex5-section29new-compact.lrml) and [`ex5-section29new-normal.lrml`](../legalruleml/examples/ex5-section29new-normal.lrml), an OASIS example in the compact and the normal syntax, copied unmodified with their notice, and [`ex5-section29new-normal.ttl`](../legalruleml/examples/ex5-section29new-normal.ttl), its RDF
- [`cover-exclusion-condition.lrml`](../legalruleml/examples/cover-exclusion-condition.lrml), the project's own clean-room document in the normal syntax, and [`cover-exclusion-condition.ttl`](../legalruleml/examples/cover-exclusion-condition.ttl), its RDF
- [`triplifyMerger-ids-noxi.xsl`](../legalruleml/xslt/triplifyMerger-ids-noxi.xsl), the OASIS stylesheet that makes the RDF, and [`examples/README.md`](../legalruleml/examples/README.md), which says how and records where each file comes from

**Studio sample:** LegalRuleML mappings (`legalruleml-mappings`)

**Steps:**

1. Make a workspace from the sample and open the Mapping view. The two proposals are listed, each mapping with its review.
2. Open the Sample tab, press **Load a file** and choose `sample-supply-terms.ttl`, then press **Run**.
3. To run it over a LegalRuleML document, press **Load a file** and choose `cover-exclusion-condition.ttl`, then **Run**. Nine of the 74 outputs hold triples, those of the obligation and the prohibition, and the override gives nothing to the proposals' mappings. Choose `ex5-section29new-normal.ttl` for the OASIS example, which gives more. The Turtle is what the OASIS stylesheet makes of the `.lrml` next to it, and the document opens in any XML reader to read beside it.
4. To make the RDF again, follow [How the RDF is made](../legalruleml/examples/README.md#how-the-rdf-is-made).
5. To propose a scheme afresh, give the proposer the metamodel as its source vocabulary and the namespace `http://docs.oasis-open.org/legalruleml/ns/v1.0/metamodel#`. It needs a language model the worker is configured with.

## Parts older than the above

### Facility agreement, vocabulary, quantities and eligibility

**Demonstrates:** the facility sample's other three configurations, which refer to one another. Sector editions handed over at a date and region schemes bound by scope give a resolution table with Resolved, Fallback, Unresolved and Conflict rows. Eligibility conditions combine the concepts of those schemes with amount and margin ranges, and seventeen questions cover Permitted, Denied and Undetermined, one before the handover and some under a scope.

**Documents:**

- [`facility-vocabulary.ttl`](facility-vocabulary.ttl), the schemes, their bindings and the contracts that resolve them
- [`facility-quantification.ttl`](facility-quantification.ttl), the value spaces and range sets of the amount and the margin
- [`facility-eligibility.ttl`](facility-eligibility.ttl), the conditions and their questions

**Studio sample:** Facility agreement, every part (`facility`)

**Steps:**

1. Make a workspace from the sample and open the Vocabulary view. Select a scheme contract and read its resolution table, then choose a resolution time to see which binding resolves it.
2. Open the Eligibility view and select a condition. Its questions are listed with their expected decisions, and each shows whether it passes.
3. Add a question of your own and read its decision against the expectation you chose.

### Lending

**Demonstrates:** a baseline of loan applications, parties and branches, with a strong persistence profile and a uniqueness key per branch.

**Documents:** [`lending-baseline.ttl`](lending-baseline.ttl) and [`baseline-single-class.ttl`](../../../ontology/persistence/examples/baseline-single-class.ttl).

**Studio sample:** Lending (`lending`)

**Steps:** make a workspace from the sample. The Overview lists the Loan application row with its data access profile, a named graph boundary with optimistic concurrency.

### Lending eligibility

**Demonstrates:** a sector condition that meets a hierarchical classification or one lender's flat list depending on the binding scope, and a credit score range, each with questions that test it.

**Documents:** [`flat-scheme-lending.ttl`](../../../ontology/eligibility/examples/flat-scheme-lending.ttl) and [`interval-containment.ttl`](../../../ontology/eligibility/examples/interval-containment.ttl).

**Studio sample:** Lending eligibility (`lending-eligibility`)

**Steps:**

1. Make a workspace from the sample. It is sorted into vocabulary, quantification and eligibility.
2. Open the sector contract in the Vocabulary view. Its resolution table has a column for each segment. Try a moment of 2026-06-01 and it resolves to Lender B's codes, and 2025-06-01 resolves as the contract's fallback.
3. Open the sector condition in the Eligibility view. It shows each concept's decision, and a new test is decided against its expectation.
4. Open the credit condition. Ranges are drawn on a number line, and a candidate value is tested against them.

### Scheme bindings

**Demonstrates:** category schemes bound by region and tier, and an edition handed over to its successor at a date, to explore how a concept scheme resolves.

**Documents:** [`conjunctive-scopes.ttl`](../../../ontology/vocabulary/examples/conjunctive-scopes.ttl) and [`temporal-handover.ttl`](../../../ontology/vocabulary/examples/temporal-handover.ttl).

**Studio sample:** Scheme bindings (`vocabulary-bindings`)

**Steps:** make a workspace from the sample, open the Vocabulary view, select a scheme contract and read its resolution table. Choose a resolution time to see which binding applies.

### Quantities and units

**Demonstrates:** value spaces, units, conversions and derived rate spaces, with the operations each space permits.

**Documents:** [`additivity.ttl`](../../../ontology/quantification/examples/additivity.ttl).

**Studio sample:** Quantities and units (`quantities`)

**Steps:** make a workspace from the sample and open the Quantification view. Select a value space to read its units and the operations it permits.

### Employment job families

**Demonstrates:** role assignments classified by a job family hierarchy, with an index contract that retrieves by any ancestor family.

**Documents:** [`employment-job-family.ttl`](../../../ontology/surface/examples/employment-job-family.ttl).

**Studio sample:** Employment job families (`employment`)

**Steps:** make a workspace from the sample, open the Surface view and select the index contract. Compile it to read what it retrieves.

### SaaS subscriptions

**Demonstrates:** subscriptions, plans and pricing, with a promotion of the billing currency over a three-step read path.

**Documents:** [`saas-subscription-currency.ttl`](../../../ontology/surface/examples/saas-subscription-currency.ttl).

**Studio sample:** SaaS subscriptions (`saas`)

**Steps:** make a workspace from the sample, open the Surface view and select the promotion. Its read path has three steps from the subscription to the currency.

### Contract builder, a facility form

**Demonstrates:** the Wording layer's facility form in the library, with a variation slot, an optional clause and a clause included when the facility is syndicated, two assemblies of it, one that assembles and one refused for a missing lender count, and the stated meaning of three clauses, two confirmed and one waiting for review.

**Documents:**

- [`facility-form.ttl`](../../../ontology/wording/examples/facility-form.ttl), the form
- [`builder-assemblies.ttl`](builder-assemblies.ttl), the two assemblies
- [`builder-meaning.ttl`](builder-meaning.ttl), the stated meaning

**Studio sample:** Contract builder, a facility form (`builder`)

**Steps:**

1. Make a workspace from the sample and open the Builder. The library is an outline of the form's sections, and a clause opens in the shape-driven editor.
2. Open the Assembly view and choose the assembly named `Syndicated, three lenders, UK and Ireland`. Its choices and values are listed, and assembling shows the findings and the document.
3. Choose the other assembly. Assembling it is refused for the missing lender count.
4. Open Meaning. Each clause reads as its stated meaning, one clause has none, and one has a proposal waiting for review.
5. Open Instrument. Terms are shown in their tier and the regime is drawn as a state machine.
