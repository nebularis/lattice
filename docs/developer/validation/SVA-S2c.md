<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-S2c, projections in the studio

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-S2c, built on 2026-11-25 in autonomous mode, from the [projection backend sketch](../sketches/projection-backend.md) as the maintainer answered SVA-Q29 (a) on 2026-11-23. The slice is built without its pane, which is explained below. The same session first built the maintainer's choice 6 of [SVA-S2j](SVA-S2j.md), recorded in that pack's follow-up section.

## Invariant

The surface compile job lowers every projection contract of its configuration with Surface's lowering and compiles each scheme with `mork_rdf`, and holds each compiled form as an artefact with the review findings the compilation records as warnings of the job. A step's projection part is a run of its own, a `simulate` run of the target `projection` whose body is the TriG of a surface step, routed to the Python worker's queue and answered with `mork_rdf`'s driver over the world before the edit and over the world after it. Its parts are a function of the compile job and the body, so a repeat and the quads of the world in another order give the same frames. One worker answers a run, and the run protocol is unchanged.

## What changed

- **The compile job**, `config_studio_jobs.py` and a new `config_studio_projections.py`. `_compile_surface` keeps what it did and adds `_compile_projections`, which lowers each contract (`lower_projection`), compiles its scheme (`mork_rdf.compile_scheme`) and holds the compiled form and a manifest in the group `projections`. A configuration with no projection adds nothing.
- **The policy**, `projection_policy.py`, reads the review findings the compilation records. `review_requirements(findings)` gives `DerivationReview`, `ExpansionReview` and `MappingReview` each once, and `handoff_policy(kind, findings)` states them as `reviewRequirements`. The two schemas under `contracts/surface/` that named `engineering_review` and `mapping_review` state the new names, as a list.
- **The projection step**, a new `config_studio_projection_step.py` (the TriG of the step, the edit, the compiled forms, the driver and the parts), `config_studio_run_frames.of_step` (the frames of a step's parts) and `config_studio_runs.py`, whose worker now answers a `simulate` run of the target `projection`, fails a `persistence` or `surface` step with the wrong-worker frame and rejects only a pair no worker takes.
- **The service and the Java run worker.** `StudioApi` accepts `kind=simulate&target=projection`, checks it against a finished compilation of the surface part and routes it to `lattice.studio.runs.rdf`. `RunWorker` fails a `projection` run with the wrong-worker frame and reads no job for it. `studio-vocabulary.ttl` gains `cst:Projection`.
- **The contract**, `contracts/config-studio/README.md`: the Runs table, the request, the worker section, the message headers, the frame roles, the compile job's artefacts and a new section "A projection step". `run-frame.schema.json` says which parts a projection step has, and has no other change, so no wire type is regenerated, and the repository has no task that generates one for runs.
- **The facility sample.** `facility-surface.ttl` gains six projections, one of each kind, and `facility-surface-step-projection.trig` is a step over it whose edit changes what five of them write. The step is a surface step too, so the surface fixture of the run worker holds it as its eighth.
- **`mork_rdf`.** The description of a compiled mapping records the severity each check's rows are reported as (`sh:severity`). See choice 12.
- **The decision.** An addendum to ADR-A154, dated 2026-11-25 and Proposed.

### Names chosen

`exists` and `find` over the index found none of `projections` as an artefact group, `cst:Projection`, `reviewRequirements` or `ProjectionRefused`. The artefact group is `projections`, as the brief suggests, and its manifest is `projections/manifest.json`, after `maintenance/manifest.json`. The run's target is `projection`. The six projections' keys are `facility-margin` (derivation), `drawdown-schedule` (a node for each instance), `borrower-exposure` (keyed), `facility-branch` (join), `facility-refinancing` (expansion) and `facility-covenant-test` (a node for each member).

## The pane

The brief's item 4 asks that the surface pane in `apps/config-studio` send the `projection` run beside the `surface` run and show its parts as a surface step's. The studio has no surface pane. The surface simulator pane is SVA-S3, which is planned and depends on the surface canvas (SVA-S1), and the persistence simulator pane (`SimulatorPane.tsx`) sends a `persistence` step only. The run controller already takes the target as a string, so nothing in `runs.ts` or `api.ts` refuses `projection`, and no code was written for the pane. The options are below. The plan's SVA-S2c row no longer lists `apps/config-studio` and its SVA-S3 row says the pane sends both runs.

1. **Leave it to SVA-S3**, which builds the pane over both runs, as built here. The cost is that nothing in the browser shows a projection's rows until then.
2. **A thin pane for the surface step now**, with a body builder like the persistence simulator's, which is a second pane that SVA-S3 would replace.
3. **Extend the persistence simulator pane** to send the surface and projection runs for its edit, which needs the pane's world to hold the carrier data a projection reads and mixes two simulators in one pane.

## Choices the brief did not settle

1. **The base the projections' minted nodes fall under** is the contract's target namespace with its `#` made a `/`. A node's IRI is built by a relative IRI in the query, which resolves against the base, and a base that ends in `#` would drop the fragment. The facility's nodes are under `https://example.org/lending/projection/{key}/exec/`.
2. **A manifest beside the compiled forms.** The brief asks for the compiled form as `{scheme}.compiled.ttl` in a group of its own. A step needs the contract's key to name its parts, and the scheme's name holds it only by the lowering's habit, so the group also holds `projections/manifest.json`, one entry for each scheme with the key, the contract, its kind, the scheme and the file. The files are at `projections/{scheme}.compiled.ttl`, a path under the group as `maintenance/` is.
3. **The findings are on the contract.** Each compile finding is the job's, with its code and severity and the contract's IRI as its focus node, and not the lowered mapping node, which the author never wrote. A finding of severity error fails the job, so a compile that records one is a violation that names the contract. A contract that lowers into no scheme, which states nothing to write, is information (`ProjectionNotCompiled`) and has no form.
4. **The target terms are not declared for the compile.** The facility baseline gains no term. The compile reads the configuration, the baseline and the substrate's vocabulary as the vocabulary that types the target terms, and the six projections compile with no finding beyond the reviews.
5. **The rows are N-Triples lines in the default graph**, media type `application/trig`, which TriG reads. The brief says "the triples the scheme writes" and the surface step's rows are in a partition named by their source. A projection has no source and no partition, so the delta's `graph` is null as a persistence step's default graph is.
6. **The driver's source is the merged world**, every graph with the default graph, less the derived partitions `urn:lattice:studio:promoted:`. The brief says "the world".
7. **The outcome's shape.** `engine`, `sources` and `contracts`, each `{contract, key, kind, scheme, asserted, retracted}`. A surface step's `reached`, `kept`, `reason` and `readSetTouched` say what a write keeps, and a projection is not kept by the writer, so they have no meaning here.
8. **The report holds every finding of the driver over the world after**, each with its own severity, its code and its focus node, and a message that begins with the contract's key so two schemes' findings are told apart. The compiler's findings are the job's.
9. **The Python worker fails a `persistence` or `surface` step instead of rejecting it.** The brief says the Python worker refuses `surface`, and the worker rejected every `simulate` run before, as a pair its queue does not carry. Rejecting is for a pair no worker takes, so the existing test that listed `simulate` and `persistence` among the rejected pairs now lists `simulate` and `mapping`.
10. **The policy's shape.** The brief asks that the requirement be taken from the findings. A construction for each instance asks none, and a keyed expansion asks two, so a single value cannot hold it. `reviewRequirements` is a list that may be empty, in the policy and in both schemas, the old `review_requirement(kind)` is removed because no rule of a kind alone is right, and `graph_construction` joins the kinds the policy and the handoff schemas name.
11. **A projection step over a job with no projection is a failure**, one failed frame that says the job holds no compiled projection. The surface run beside it succeeds.
12. **A defect in the description of a compiled mapping, found and fixed.** `mork_rdf.to_rdf` did not record the severity each check's rows are reported as, which the text of the compilation, and so the digest the form is named by, reads for a check of information. `from_rdf` refused the compiled form of every expansion (`CollectionEmpty` is information) and of a join whose unmatched rows are information, so a sample run and a projection step could not read them back. The description now records `sh:severity` on a check, which the README states in section 11.1, and a test reads back the node for each member. The compiled forms in the sample runs' fixture are regenerated and gain that triple. A form written before the change is read back with each check as a warning, and is refused where it had a check of information.
13. **The sample runs' fixture gains the added triple only.** `apps/config-studio/e2e/fixtures/sample-runs.json` is written by the Python test with `LATTICE_WRITE_SAMPLE_RUNS=1`, which indents as Python does, where the file had been written in another layout. The reviewer kept the file's layout and changed only the two compiled forms that gain the triple, so its diff is two lines.
14. **The surface step fixture holds the new step as its eighth.** The new step is a surface step, so the Python test that writes the run worker's expectation, `expected.json`, and the Java tests that read it hold it too. The test that names the steps now names eight.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| S2c-T1 | `_compile_surface` over the facility sample / compiled / a compiled form and a manifest entry for each of the six projections, in a group `projections`, each form read back by `mork_rdf` | L1 | | |
| S2c-T2 | the same / compiled / `DerivationReview`, `ExpansionReview` and `MappingReview` are warnings on the contract each kind asks, a construction for each instance records none, and the job conforms | L1 | | |
| S2c-T3 | a configuration with no projection / compiled with and without the projection step / the same graph, and no `projections` artefact | L1 | | |
| S2c-T4 | `mork_rdf.compile_scheme` refusing / compiled / the job does not conform and each violation names its contract and holds no form | L1 | | |
| S2c-T5 | the sample compiled twice / compared / the same forms | L1 | | |
| S2c-T6 | each projection kind of the sample / the policy / the requirement the compilation records, none for a construction for each instance, two for a keyed expansion, and an unknown kind refused | L1 | | |
| S2c-T7 | the step file over the compile job / run by the Python worker / the parts in the contract's order, each scheme's rows after equal to its compiled form run by `mork_rdf`'s driver over the world after as rdflib computes it, and its rows before equal over the world before | L1 | | |
| S2c-T8 | the same / read / the edit changes five of the six, the delta and the outcome have the shapes of the contract, and the engine names `mork_rdf` and Oxigraph | L1 | | |
| S2c-T9 | the same step twice, and with the quads of the world in three other orders / run / the same frames | L1 | | |
| S2c-T10 | a malformed step (empty, not TriG, no request, a persistence step, no part, another part, a bad or missing time, a reserved graph, an edit of a derived partition or of the step's graph, a quad both added and removed) / run / one failed frame that names the part | L1 | | |
| S2c-T11 | a job with no compiled projection, an empty manifest, another part's job, an unfinished job, a form whose queries changed, and a query that reads the clock / run / one failed frame | L1 | | |
| S2c-T12 | a `surface` or `persistence` step at the Python worker, and a `projection` run at the Java run worker / handled / one failed frame that says it went to the wrong worker, and no job read at the Java worker | L1 | | |
| S2c-T13 | a step that is not `application/trig`, one over 5 MiB, one redelivered, one past its deadline and one that passes its deadline / handled / the failed frame each rule gives, and nothing published for a stopped run | L1 | | |
| S2c-T14 | the service / a `simulate` run of `projection` / routed to `lattice.studio.runs.rdf` with a deadline of 15 seconds and `application/trig`, `409` for a job of another part or unfinished, `415` for another media type, `400` for a deadline beyond 15 seconds | L1 | | |
| S2c-T15 | the contract and the vocabulary / read / the section "A projection step" with its parts, the target `cst:Projection`, the sample, no semicolon and no working identifier in the section | L1 | | |
| S2c-T16 | a compiled node for each member / described in RDF and read back / the same compilation with the same severity for each check | L1 | | |

## Checks run

| Command | Result |
|---|---|
| `mise run check:python-root` | 356 tests, OK, and the phase 8 conformance passed (3 Surface parity cases, 4 Eligibility cases) |
| `mise run check:mork-rdf` | 334 passed, 3 more than the 331 of SVA-S2j, two for the blank member with a name and one for the read back of a node for each member |
| `mise run check:mork` | 464 passed |
| `mise run check:mork-compilers` | 195 passed, 39 subtests |
| `mise run check:ontology-catalog` | 1319 passed, consistent, the 2 known defects |
| `mise run check:owl-profile` | 47 documents, 5 known findings, none new, and 5 tests passed |
| `literate_extract --layer surface --check` and `--layer mork --check` | 4 and 3 artefacts consistent |
| `mise run check:workers` | 377 passed in `workers/tests`, 39 of them the projection step's and the compile's, and 10 the policy's |
| `mise run check:config-studio` | exit 0. 315 Python tests (the studio's staging, contract, worker, rebuild, layers, imports and compiled fixture), `mvn verify` of the authoring, service, writer and transforms modules with 254 tests in the service and 78 in the run worker's module, and the app's type check and 564 unit tests in 36 files |
| `mvn -o test` of `RunsRouteTest`, `RunWorkerTest`, `SurfaceStepTest` and `TopologyTest` | 25, 19, 13 and 3 tests, none failing, run before the full verify |
| `yarn workspace @lattice/config-studio run check` | `tsc --noEmit` clean and 564 tests passed. The app has no change |
| `mise run check:identifiers` | passed, 2389 identifiers, 0 unresolved |
| `mise run check:published-decisions` | passed (6 tests) |
| `tools/writing_rules.py` over every line added to a Markdown file, and the deny-term pattern of the personal boundaries over every changed file | no finding |

`check:mork` rewrote `ontology/mork/mtp/data/pins.lock.json`, which was restored with `git checkout`, so the MTP's pins wait for `mise run build:mtp` at the merge, as for the earlier slices. A scratch comparison ran the compile job of three promotion-only examples (`clinical-trial-crosswalk.ttl`, `employment-job-family.ttl` and `keys.ttl`) with the code of `HEAD` and with this change, and the two graphs are the same triple for triple.

The reviewer ran each again on 2026-11-25 after restoring the fixture's layout: `check:python-root` 356 tests OK with the phase 8 conformance, `check:mork-rdf` 334 passed, `check:mork` 464, `check:mork-compilers` 195 with 39 subtests, `check:workers` 377, `check:config-studio` exit 0 with 315 Python tests, 564 app tests in 36 files and the Java modules' 9, 254, 10 and 85 tests with none failing or skipped, `check:identifiers` and `check:published-decisions` passed, and the Surface and MORK extractions consistent.

## Left open

- The pane that sends the projection run beside the surface run, which is SVA-S3's (see the pane above).
- The writer keeps no projection's rows, so a projection step shows what a scheme would write and not what the store holds. TD-265 records that the cost of a step over a world larger than a sample is not measured.
- MORK's definition of `mork:dataMember` still says a member is written as it is, which TD-264 records for the next change to MORK's specification.
- TD-261 is closed. It is removed from the register, as a closed row is, and the earlier packs that name it are history.
- ADR-A154's addendum was accepted by the maintainer on 2026-11-25, with the fourteen choices above as built, the pane given to SVA-S3, and the placement below.
- No version was bumped. Surface, MORK and the studio's contract wait for `mise run version:bump` at the merge, with the earlier slices' changes.

## Placement

T0 and T1. The studio's worker, service, contract and `mork_rdf` are open substrate (T0), and the facility sample's projections are generic lending examples with no private configuration (T1).
