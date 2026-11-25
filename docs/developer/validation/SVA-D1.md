<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-D1, sample documents for every capability

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-D1, built on 2026-11-25 in autonomous mode. The slice is built in part. The LegalRuleML instance documents and the RDF they give are not built, for the two reasons under "Stopped", and the maintainer chooses how to go on.

## Invariant

Every capability the unit built can be demonstrated from documents in known places. [`contracts/config-studio/samples/README.md`](../../../contracts/config-studio/samples/README.md) lists each example, what it demonstrates, where each of its documents is, which studio sample offers it and the steps to demonstrate it, grouped by the plan's phases. Each file the README links exists, each heading it links to exists, each file of the samples folder is linked, and each studio sample it names is listed in `samples.ttl`, carries the label the README gives it, and loads as the studio loads samples. A capability no document can show is a row of the debt register.

## What changed

- **The inventory**, below. It is the README's skeleton, and its gaps are the changes that follow.
- **A folder `contracts/config-studio/samples/imports/`** holding a root ontology, a catalog, an import the catalog resolves to a file of the same name, an import it resolves to a file of an unrelated name (`export-0417.ttl`) and an import with no file and no entry, so the dialog reports it missing. It is opened from its files and is no studio sample. A scratch test over the browser's own `resolveImports` and `buildCatalogLookup` gave the plan the demonstration expects, the vehicles and depots imports `catalog` with the paths `imports/vehicles.ttl` and `imports/export-0417.ttl` and the calendar import `missing`, with no problem. The scratch test is removed.
- **A sample `species-mappings`** from `species-mappings.ttl`, an RDF mapping that compiles to 2 strata and 1 closure and carries its own example source, which the Sample pane offers. See choice 2.
- **A sample `axioms`** from `axioms-baseline.ttl`, which the inventory found missing (choice 3). A scratch test over the browser's `classAxioms` and `propertyAxioms` read `Vehicle`, `Van`, `Lorry`, `ElectricVan` and four properties with nothing under Other statements. The scratch test is removed.
- **The samples `policies-csv` and `policies-yaml`**, a scheme each (`csv.mork.ttl` and `yaml.mork.ttl`) beside the policies examples, with their sources `source.csv` and `source.yaml`. See choice 4.
- **`contracts/config-studio/odrl/software-licence.odrl.ttl`**, the ODRL pack's sample source as Turtle beside its JSON-LD. See choice 5.
- **`contracts/config-studio/samples/README.md`**, and rows for the new files in the contract's table.
- **The test**, seven tests and a parameter added to `tools/test_config_studio_stage.py`, which `mise run check:config-studio` runs.
- **`REUSE.toml`** gains an annotation for `source.csv`, which has no comment syntax. See choice 7.
- **Two debt rows**, TD-266 and TD-267, and the plan's SVA-D1 row, corrected where it disagrees with what is built.

## The inventory

| Capability (slices) | Documents it needs | Where they are today | Result |
|---|---|---|---|
| A run of a sample over XML, JSON, Turtle (R0 to R4a) | a mapping and a source of each format | the policies sample, `policies-sources.ttl`, the catalogue fixtures, and now the species sample | present, listed |
| The frames of a run (R1, R4a) | a complete run, a run that could not start, a run past its deadline | `samples/run-frames*.example.json` | present, listed |
| The run protocol's failure cases (R5) | a source to run | inline in `test/studio-integration/test_runs.py`, which `mise run studio:runs` runs | no file, listed with the command |
| The columns the author collapses and resizes (U1) | none | any workspace | listed as needing none |
| Imports resolved from a catalog, missing imports reported, a folder dropped (B1, B2a, B2d, B3, B5) | a folder with a catalog, a file of an unrelated name and a missing import | built inline by the journeys only | gap, filled with `imports/` |
| LATTICE's documents served by IRI, the import graph with a stated, a binds and a derived edge (B2b, B2c, B4, B5) | a baseline that imports a layer | the `library-imports` sample | present, listed |
| The ontology drawn with and without shapes, as a hierarchy (O1, O2, O2a, O4 to O7) | a baseline with a shape that states some links | the `facility` sample | present, listed |
| The axiom forms (O3) | a class with a restriction, an equivalent class, disjointness, a key, a datatype restriction | no sample held a restriction | gap, filled with `axioms` |
| The persistence canvas (P1, P1a to P1c) | a persistence configuration, its compiled profile | the `facility` sample and the e2e fixtures | present, listed |
| The persistence simulator, a create, a replace, a lost race, a generated object (P3, P3a, P4, P5) | the steps | `facility-step-*.trig` and the journey's fixture, which holds the four steps and their frames | present, listed |
| The simulator's delete (P4) | a tombstone step | none stored, the pane builds it from the profile | listed as built by the pane, no document |
| The surface simulator's steps and the projection step (S2 to S2c) | one step for each kind of edit | `facility-surface-step-*.trig`, eight files, the last also a projection step | present, listed, no pane (S1 and S3 are planned) |
| The mapping schemes listed, the Sample pane, the output explorer (M1, M3a, M3b, M4) | a mapping and a source | the policies sample, the catalogue fixtures | present, listed |
| An RDF mapping in strata with a closure (M3a) | a scheme | inline in `tools/mork_rdf/tests/test_mork_rdf.py` only | gap, filled with `species-mappings` |
| The RML form's waiting state for each format (M3b) | a scheme and a source of each format | JSON in the policies sample | gap, filled for CSV and YAML. XML cannot show it from a sample that holds JSON (TD-266) |
| A sample source for each mapping pack (M3a) | the ODRL policy as Turtle, LegalRuleML's sample source | ODRL's under `odrl/trial/`, LegalRuleML's under `legalruleml/trial/` | ODRL's now beside its JSON-LD. LegalRuleML's existed |
| LegalRuleML instance documents and their RDF | an `.lrml` document and the RDF a pack reads | none | stopped, see below |
| A large output, the explorer's paging, the frame limit (M4, R2) | a sample that writes hundreds of triples | none | TD-267 |
| Stack hygiene, the register's numbering (H1, X1, X2, X4) | none | not capabilities of a document | not listed |
| Libraries, the persistence edits, the surface canvas and pane (M2a to M2e, P2, S1, S3) | planned, not built | | not listed |

## Stopped

**The LegalRuleML instance documents.** Item 4 of the brief is not built, for two reasons that each stop it.

1. The OASIS example is not fetched. The URL tried was `https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/os/examples/ex5-section29new-compact.lrml`, and the first try was the directory `https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/os/`. Both gave `curl: (56) CONNECT tunnel failed, response 403`, and the session's proxy reported `docs.oasis-open.org:443 connect_rejected, HTTP 403`, which it gives for a host the session does not allow. The file was not written from memory. No notice or provenance was written for it.
2. The repository holds no means to make the RDF. A search of the tree for a triplifier, an `.lrml` file and the OASIS normaliser and triplifier stylesheets found only the sketch that names them. The pack's trial hand-wrote its sample source, `sample-supply-terms.ttl`, in the metamodel's terms.

The clean-room document of our own was not written either, since it could not be checked against the OASIS schema, which the same refused host serves, and a document that claims to be LegalRuleML and has no RDF read from it demonstrates nothing in the studio, which reads RDF.

The options for the maintainer:

1. **Allow `docs.oasis-open.org` for a build session.** The session then copies the example with the notice and the provenance lines of `legalruleml/README.md`, and fetches the OASIS schemas and the two stylesheets the sketch names. The stylesheets are XSLT 2.0, which Saxon-HE runs, and the repository's transforms module already ships Saxon-HE. Each stylesheet would be a third-party file with its notice, and running them is the means the sketch names, so this is a decision of what the repository holds.
2. **Hand-write the RDF**, as the trial did for `sample-supply-terms.ttl`, for the clean-room document only. The cost is that nothing then keeps the XML and the RDF equal.
3. **Leave the item to the LegalRuleML pipeline's first slice**, whose step 1 runs the OASIS transforms and would produce both. The README then says, as it does now, that no LegalRuleML XML document is offered.

## Choices the brief did not settle

1. **The plan's premise about the RDF mapping was wrong in one place.** The plan row says the mapping with strata and a closure lives among `mork_rdf`'s fixtures. No fixture file holds one. `catalogue-mapping.ttl` and the other fixtures compile to 1 stratum and 0 closures, and the two-stratum scheme with a closure is inline in `test_mork_rdf.py` (the `species` helper and its `knows` mapping). The row is corrected.
2. **The species sample is new text**, written from that inline scheme and extended with a lookup from the animal records. It sits in `contracts/config-studio/samples/` and not among the fixtures, so `mise run check:mork-rdf` was not run, since no `mork_rdf` file changed. The sample's example source is carried as the example of a representation scheme with the format RDF, as the policies sample carries its XML and JSON examples. A scratch run of the worker's sample run over it gave 6 parts, the files `0/CreateSpecies.nt`, `0/Animal.nt`, `1/AnimalSpecies.nt`, `0/Knows.nt` and `1/Knows.nt` and a report that conforms with three warnings, and the README says what that run shows.
3. **A sample for the axiom forms.** The brief names no gap for the demonstration "a class with a restriction read in its form", and no existing sample holds a restriction. The sample is small and generic, and is added beside the named gaps. Delete it if the maintainer wants no addition.
4. **Two samples for CSV and YAML, not one.** The compile job records the one RML artefact under the first scheme only (TD-266), so a sample that held both schemes would show the waiting form for CSV and not for YAML. The schemes are in two files, each its own sample, and are named beside the XML and JSON ones as the brief asks. The pane offers no example source for either, since it reads three formats, so the README has the author paste the text. The pane also sends that text as Turtle on the first press of Run, so that run fails, which the README says.
5. **A copy of the ODRL Turtle beside the JSON-LD.** The Turtle already existed as `odrl/trial/software-licence.ttl`, which five tests, the trial's README and a note name. The plan asks for it beside the JSON-LD, so there is a copy, and a test keeps the two isomorphic. The alternative is to move the file and rewrite those seven files, which would change the trial's folder.
6. **The sample files' licence headers.** A `.ttl` file in `samples/` carries `MPL-2.0` and one under `odrl/` or the policies examples carries `CC-BY-SA-4.0`, as its neighbours do. The catalog is XML and carries the comment header `ontology/catalog-v001.xml` carries. `source.yaml` carries a comment.
7. **`source.csv` has no header**, since a comment line would be read back as a row. Its licence is a path annotation in `REUSE.toml`, as CONTRIBUTING.md gives JSON. Its siblings `source.json` and `expected.nt` carry no header and no annotation, which this slice does not change. `reuse lint` is not installed here, so the annotation is not run.
8. **The README's phases are named for what they show**, not by the plan's letters, since the README is user-facing and the letters are working identifiers. The sample's key is in each example's `Studio sample` line, which the test reads.
9. **The README tests the folder as well as the links.** Every file of the samples folder, bar `samples.ttl` and the README itself, must be linked, which found `facility-eligibility.ttl` and `facility-quantification.ttl` unlisted and gave the facility sample's eligibility section.
10. **The surface and projection steps are sent through the run request.** The studio has no surface pane (S1 and S3 are planned), so the README says to send each file with the run request the contract states, and does not show a pane.
11. **The simulator's delete has no stored step.** The pane builds a tombstone from the compiled profile, and `simulator.test.ts` and the run worker's `PersistenceStepTest` run one. No document holds it, and the README says so. It is not a debt row, since the facility sample is the document.
12. **The failure cases of a run have no document.** `mise run studio:runs` inlines the XML example. The README names the command and the test.
13. **The README steps are drawn from the browser journeys and the views' code, and no browser ran them.** The journeys run on a fake service, the real stack was not started (the brief forbids it), and the Playwright suites are SVA-V1's. Each label and each figure in a step is one a journey checks or one a scratch run gave. The steps that no journey checks, those of the older samples `employment`, `saas`, `quantities` and `vocabulary-bindings`, say less.
14. **No ADR is cited and none is marked Accepted.** The README links the operations guide and the contract.
15. **The status record and the roadmap are not touched.** The slice's row already reads `building 2026-11-25`. Its state, `mise run build:work` and `mise run build:roadmap -- --fetch` are the maintainer's at the commit, since the brief forbids a commit and the fetch reads the network.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| D1-T1 | the samples README / its links read / each target exists, each heading a link names exists in its file, and each file of the samples folder is linked | L1 | `(imports/base.ttl)` in the README's link changed to `(imports/base-x.ttl)` | `imports/base-x.ttl is linked and does not exist` |
| D1-T2 | the README's `Studio sample` lines and the staged `samples.ttl` / compared and each sample loaded / the same set of keys, the same labels, and each sample parses with triples | L1 | the label `Fleet axioms` in the README's `Studio sample` line changed to `Fleet axiom` | `the README calls axioms 'Fleet axiom' and samples.ttl calls it 'Fleet axioms'` |
| D1-T3 | the `imports` folder / its root, catalog and files read / the root imports three IRIs, the catalog names two, each named file declares the ontology the catalog says, one of the two has a name its IRI does not give, and no file declares the third | L1 | the catalog's entry for `depots` deleted | `the catalog names two of the three imports and no other`, `assert (1 == 2)` |
| D1-T4 | `species-mappings.ttl` / compiled with `mork_rdf` and run over its own example / 2 strata, 1 closure, no error, and the one finding `LookupUnresolved` for `Dodo` | L1 | the closure's `mork:assertsPropertyDomains` over the created classes removed | `assert (not () and 2 == 2 and 0 == 1)`, no closure |
| D1-T5 | the ODRL Turtle beside the JSON-LD and the trial's copy / compared / isomorphic | L1 | one literal of the copy changed | `assert False` from `isomorphic` |
| D1-T6 | `source.csv`, `source.yaml` and `source.json` / read / the YAML equals the JSON, the CSV has a row for each policy and cover, each column the CSV scheme names is a column, and each scheme names its format | L1 | the last CSV row changed to policy `P-3` | `At index 3 diff: {'policy': 'P-3', ...} != {'policy': 'P-2', ...}` |
| D1-T7 | `csv.mork.ttl` and `yaml.mork.ttl`, each alone / compiled by the studio's compile job / a conforming job, `mapping.rml.ttl` under the scheme, and no stylesheet or JOLT chain | L1 | `mork:format mork:CSV` changed to `mork:RDF` in the scheme | the assertion that the job has `cst:conforms true` fails, so the job did not conform |

## Checks run

| Command | Result |
|---|---|
| `mise run check:config-studio`, first run | exit 1 at `mvn verify` of `config-studio-transforms`. `RunWorkerTest.anRdfSampleThatReachedTheWrongWorkerAndASurfaceStepOverAJobOfAnotherPartEachGiveTheirOneFailedFrame` raised a `ConcurrentModificationException` in `awaitSettled`, which streams the test's `sink.log` while the worker thread appends to it. The Python part had passed first, 323 tests. Nothing in Java, the contract or a fixture was changed by this slice, and another command of mine was running beside it |
| `mise run check:config-studio`, second run, nothing else running | exit 0. 323 Python tests passed (315 before this slice, 8 added), `mvn verify` of the authoring, service, writer and transforms modules with 9, 254, 10 and 85 tests, 0 failures, 0 errors and 0 skipped from their surefire reports, and the app's type check and 564 unit tests in 36 files. `check:authoring-domain` ran first with 21 tests in 4 files |
| `python -m pytest tools/test_config_studio_stage.py` | 21 passed, 7 of them new with one parameter, after the breaks below were each restored |
| `mise run check:workers` | 377 passed in `workers/tests`, as for SVA-S2c, exit 0 |
| `mise run check:identifiers` | passed, 2391 identifiers in 1005 files, 0 unresolved, 0 defined twice |
| `mise run check:published-decisions` | passed, 6 tests. `tools/published_decisions.py check` printed nothing and `tools/sources_check.py --quiet` reported 0 failures |
| `tools/lattice_repo_catalogue.py check` | the catalogue agrees with the tree, so the new folder is no new kind of directory |
| `check_links_in` of `tools/repository_topology_check.py`, the hooks' link check, over the five Markdown files changed | no finding |
| `tools/writing_rules.py` over every Markdown file changed or added | 0 failures. 12 warnings on lines of `technical-debt.md` that this slice did not write |
| the deny-term pattern of the personal boundaries, over tracked and untracked files | no finding |

`mise run check:mork-rdf` was not run, since no file of `mork_rdf` or its fixtures changed. `mise run check:mork` was not run, so no `pins.lock.json` was rewritten and none needed restoring. The browser suites (`mise run test:config-studio-browser`, `mise run studio:runs`, `mise run studio:liveness`) were not run, as the brief assigns them to SVA-V1. `reuse lint` is not installed here.

A scratch test under `apps/config-studio/src`, written for the folder and the axiom sample and removed after, and a scratch run of the worker's sample run over the species sample, gave the figures the choices above quote.

The reviewer ran these again on 2026-11-25 with nothing else running: `check:config-studio` exit 0 with 323 Python tests, the Java modules' 9, 254, 10 and 85 tests with none failing, and the app's 564 tests in 36 files, `check:workers` 377 passed, `check:identifiers` and `check:published-decisions` passed, and the writing rules on the README and this pack with no finding.

## Left open

- The LegalRuleML instance documents and their RDF, with the options above.
- TD-266, the RML form held under one scheme, and the reference formulation `mork2rml` writes for a scheme of CSV, XML or YAML. Until it is paid, the waiting form is shown for XML only from a workspace that holds no JSON scheme.
- TD-267, no sample large enough for the output explorer's paging and the frame limit.
- The surface simulator has no pane, so the plan's demonstration "the same edit followed into the rows a promotion keeps" runs through the request and the worker suites and not in the studio. SVA-S3 plans the pane.
- The real-stack browser suite and the run of the README's steps in a browser are SVA-V1's.
- No version was bumped. The studio's contract README gained rows and no rule, and no ontology file changed.

## Placement

T0 and T1. The README, the test, the samples manifest and the contract's table are the studio's open substrate (T0). The folder `imports/`, `axioms-baseline.ttl`, `species-mappings.ttl`, the CSV and YAML schemes and sources and the ODRL Turtle copy are generic examples with no private configuration (T1). Gate 0: every new file is written by the project from generic meaning, and the ODRL Turtle is a byte copy of a file the repository already holds. Nothing is copied from a policy wording, a market form or a client's document.
