<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.11b, the Persistence README told through its examples

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.11b,
[plan §4.19](../plans/formal-methods-track-h.md#419-h211-the-persistence-readme-as-a-literate-specification-planned-2026-10-20),
[sketch](../sketches/persistence-readme-literate.md) (RL-Q1 to RL-Q7). Authored and run in autonomous mode, not committed.
Versioning is ignored on this branch (TD-64), so no version IRI moved. Prose and diagrams only. No generated graph, test, builder or example changed.

**Awaiting the maintainer's review.** Three decisions were taken alone (D-65 to D-67), listed below.

## Invariant

Every graph generated from `ontology/persistence/README.md` is the same as after H2.11a. `check:literate-migration` against `f25008b2` reports the same
137 reconciled differences and no new one, and the extractor finds the 4 artefacts consistent. The generated class diagram and the Axiom Index are untouched.
The README cites only published decisions and no working document.

## What was built

1. **A running case in §5.13**, in eight steps, each with its example, its generated operation and its test. The case is the project aggregate of
   `composite-project-ownership` for writes and history, with `baseline-single-class`, `value-based-cas`, `append-stream-dataset-guard`,
   `write-discipline-composite-append-versions`, `write-discipline-delta-membership` and `persistent-foundation-keys` joining where a step needs them. No new example,
   no domain content, and none of the history sketch's examples. Every number in a picture was read by running the generated update on the test fixture
   (rdflib, `tools/persistence/tests/fixtures/project-data.ttl` and the harnesses of the tests named) and is the builder's arithmetic.

   | Step | Example | Operation | Test |
   |---|---|---|---|
   | 5.13.1 declare | `composite-project-ownership`, `baseline-single-class` | none | `test_ownership_tree` ho4_t5, `test_ownership_refusals` ho6_t2, `test_named_graph_builders` h2_3_t9 |
   | 5.13.2 compile | the same, `invalid-compositeboundary-receiptonly` | compiled profile | `test_resolver`, `test_compiler_integration` |
   | 5.13.3 generate | `composite-project-ownership` | `cas-replace` contract | `test_expected_profiles` h2_7_t1, t7 |
   | 5.13.4 write | the project, `append-stream-dataset-guard`, the two write-discipline examples | `create-if-absent`, `cas-replace`, `tombstone-delete`, `append-event`, `append-version`, `append-version-delta` | `test_composite_lifecycle`, `test_patch_log`, `test_append_events`, `test_write_disciplines`, `test_membership` |
   | 5.13.5 race and retry | the project, `value-based-cas`, `persistent-foundation-keys` | the guards, the value guard, `key-claim-write` | `test_patch_log` h2_6d_t5, t6, `test_composite_lifecycle` ho7_t6, t7, `test_contract_emission` h2_7_t20, `test_key_claims_and_audits` h2_5_t15 |
   | 5.13.6 history | the project, `write-discipline-composite-append-versions` | receipts, delta graphs, versions | `test_patch_log` h2_6d_t10, `test_write_disciplines` h2_6c_t3 |
   | 5.13.7 read back | `write-discipline-delta-membership` | `members`, the audits | `test_membership` h2_6f_t5, t8, t9, `test_key_claims_and_audits` h2_5_t36, the caller library's `test_check` |
   | 5.13.8 keep it small | `write-discipline-delta-membership` | retention by a housekeeper | `benchmark/persistence-membership`, `test_key_claims_and_audits` h2_5_t36 |

2. **Pictures of SPARQL on the graph** for create, replace, tombstone, append of events, append of a version and a delta version (flowcharts of the graphs before
   and after, with what each arrow deletes and inserts), sequence diagrams for a race, a retry after a lost reply and a stale seq (and a race for a key claim),
   a retention timeline and the chain of the members read. Each was checked against `tools/persistence/src/persistence/builders.py` and against the real generated text.
3. **§5.14 Best practices, gotchas and considerations**, fourteen items in three groups, with pictures for the structural ones.

   | Gotcha | Source |
   |---|---|
   | an integer is not an `xsd:long` | TSD-07, `test_store_probes` h2_5_t1, the caller library's `test_check` |
   | the order an update is applied in | TSD-01, `test_store_probes` h2_4b_t1, t2, `test_composite_builders` h2_4a_t7 |
   | `NOT EXISTS` and the graph | TSD-34, `test_tsd_34_builders` h2_6g_t1, t2 |
   | a request of several operations | TSD-06, `test_store_probes` h2_4b_t3 |
   | an empty `VALUES` | TSD-21, `test_append_events` h2_6b_t6 |
   | the cost of a sweep | TSD-02, `check:persistence-composite-cost`, the efficient queries document (TD-42 described in words) |
   | a slot left unfilled | `test_patch_log` h2_6d_t7, t8 |
   | inverse functional properties | the patterns guide chapter 4, `tools/test_keys.py` f1_04, f1_05 |
   | blank nodes | TSD-29, the identity guide section 9, the caller library's `test_payload` |
   | guards off | `test_builders` h2_2_t14, `test_composite_builders` h2_4a_t3, `test_payload_check` h2_8b_t11 |
   | no receipt and the meta shard | `test_payload_check` h2_8b_t14, t15 |
   | pinned or by identity | `test_reference_modes` h2_6e_t9, t10 |
   | full or delta membership | `check:persistence-membership`, `test_membership` h2_6f_t1, t12, t13 |
   | an event names an aggregate and never describes it | the caller library's `test_check` |

4. **The palette** of the sketch's §5 on all 49 diagrams outside the generated class diagram (18 old and 31 new, one of them the legend near the start of §5). Flowcharts and state
   diagrams use `classDef` with the sketch's fills and strokes and `color:#000`. See D-65 for the sequence, class and subgraph diagrams.
5. **§8 keeps its contents.** The narrative links to 8.5. Its three diagrams only take the palette, and the 8.4 one is laid out left to right.
6. **D-64.** `ontology/persistence/docs/precedence-and-resolution.md` and `aggregate-boundaries.md` no longer link a sketch (three links removed, each sentence kept in words
   or pointing at the README).
7. **Section numbers.** 5.13 to 5.15 are new, and the cross references became 5.15. Nothing cited 5.13. §1, §2, §3, §6, §7 and §12 are unchanged.

## The diagrams

Rendered with mermaid 10.9.1 (`mermaid.min.js` from `cdn.jsdelivr.net/npm/mermaid@10.9.1`) in headless Chromium through Playwright, in the `default` and the `dark` theme.
All 49 parse and render. Sizes are the natural width and height in pixels. The layout, and so the size, is the same in both themes. The generated class diagram is not rendered here (D-59).

| # | Section | Kind | Age | What it shows | Light | Dark |
|---|---|---|---|---|---|---|
| 1 | 4. Overview | flowchart | old | the compile pipeline, palette applied, laid out top to bottom (was 1911 px wide) | 635x997 | 635x997 |
| 2 | 5. Detailed Design | flowchart | new | the palette legend | 162x847 | 162x847 |
| 3 | 5.1 Why persistence in RDF is hard | sequenceDiagram | old | lost update by set semantics (rects) | 1049x502 | 1049x502 |
| 4 | 5.2 The infrastructure the patterns add | flowchart | old | the infrastructure graphs | 716x573 | 716x573 |
| 5 | 5.3 One write, end to end | sequenceDiagram | old | one write, end to end (rects) | 743x1038 | 743x1038 |
| 6 | 5.4 The configuration model | classDiagram | old | the configuration model (class diagram, style lines) | 676x1046 | 676x1046 |
| 7 | 5.5.3 Precedence | stateDiagram-v2 | old | precedence resolution | 429x945 | 429x945 |
| 8 | 5.6.3 Ordering | flowchart | old | three clocks | 429x425 | 429x425 |
| 9 | 5.6.3 Ordering | sequenceDiagram | old | a counter allocated before commit (rects) | 710x709 | 710x709 |
| 10 | 5.6.4 Receipts, history and retention | flowchart | old | the receipt models | 391x574 | 391x574 |
| 11 | 5.6.6 Uniqueness | flowchart | old | the uniqueness patterns, wrapped labels (was 1253 px) | 769x576 | 769x576 |
| 12 | 5.6.6 Uniqueness | stateDiagram-v2 | old | claim scheme rotation | 284x487 | 284x487 |
| 13 | 5.6.8 Epoch | sequenceDiagram | old | epoch and restore (rects) | 568x659 | 568x659 |
| 14 | 5.6.10 Write discipline | flowchart | old | in place and appended versions | 378x524 | 378x524 |
| 15 | 5.9 Choosing a profile | stateDiagram-v2 | old | choosing a profile (1230 px, left as it was) | 1230x758 | 1230x758 |
| 16 | 5.11 Keys: `persistent-foundation` | flowchart | old | keys and persistent-foundation | 894x448 | 894x448 |
| 17 | 5.13 A running case, from declaration to | flowchart | new | the eight steps | 1118x50 | 1118x50 |
| 18 | 5.13.1 Declare | flowchart | new | the declared profile of the project | 612x332 | 612x332 |
| 19 | 5.13.1 Declare | flowchart | new | the aggregate of ex:p1 and what stays outside | 1034x550 | 1034x550 |
| 20 | 5.13.1 Declare | flowchart | new | a named-graph family, graph and row | 741x191 | 741x191 |
| 21 | 5.13.2 Compile | flowchart | new | compile for the project | 272x673 | 272x673 |
| 22 | 5.13.2 Compile | flowchart | new | a refusal beside an accepted configuration | 615x172 | 615x172 |
| 23 | 5.13.3 Generate | flowchart | new | the contract of cas-replace | 589x1296 | 589x1296 |
| 24 | 5.13.4 Write | flowchart | new | create, graphs before and after | 1059x329 | 1059x329 |
| 25 | 5.13.4 Write | flowchart | new | replace, graphs before and after | 1278x463 | 1278x463 |
| 26 | 5.13.4 Write | flowchart | new | tombstone, graphs before and after | 1003x329 | 1003x329 |
| 27 | 5.13.4 Write | flowchart | new | append of events, graphs before and after | 1224x329 | 1224x329 |
| 28 | 5.13.4 Write | flowchart | new | append of a version, graphs before and after | 993x348 | 993x348 |
| 29 | 5.13.4 Write | flowchart | new | a delta version, graphs before and after | 1110x348 | 1110x348 |
| 30 | 5.13.5 Race and retry | sequenceDiagram | new | two writers, one winner | 943x860 | 943x860 |
| 31 | 5.13.5 Race and retry | sequenceDiagram | new | a retry after a lost reply and the claim | 772x850 | 772x850 |
| 32 | 5.13.5 Race and retry | sequenceDiagram | new | a stale seq, and Gone | 812x811 | 812x811 |
| 33 | 5.13.5 Race and retry | sequenceDiagram | new | a race for a key claim | 836x565 | 836x565 |
| 34 | 5.13.6 History | flowchart | new | receipt chain and delta graphs | 474x576 | 474x576 |
| 35 | 5.13.6 History | flowchart | new | version chain with shared members | 394x416 | 394x416 |
| 36 | 5.13.7 Read back | flowchart | new | rebuilding a state from the deltas | 708x191 | 708x191 |
| 37 | 5.13.7 Read back | flowchart | new | the members chain to a checkpoint | 884x69 | 884x69 |
| 38 | 5.13.7 Read back | flowchart | new | the three audit outcomes | 651x1016 | 651x1016 |
| 39 | 5.13.8 Keep it small | flowchart | new | a retention pass on a timeline | 1018x331 | 1018x331 |
| 40 | 5.14 What a store does | sequenceDiagram | new | order of solutions (rects) | 654x597 | 654x597 |
| 41 | 5.14 What a store does | flowchart | new | NOT EXISTS and its graph | 1182x158 | 1182x158 |
| 42 | 5.14 What a store does | flowchart | new | the sweep cost | 510x172 | 510x172 |
| 43 | 5.14 What the model does not give | flowchart | new | inverse functional merge against a key claim | 652x192 | 652x192 |
| 44 | 5.14 What a choice costs | flowchart | new | no receipt in a shared meta shard | 801x325 | 801x325 |
| 45 | 5.14 What a choice costs | flowchart | new | pinned or by identity | 245x378 | 245x378 |
| 46 | 5.14 What a choice costs | flowchart | new | an event names and never describes | 238x440 | 238x440 |
| 47 | 8.2 A shared class, two deployments | flowchart | old | a shared class, two deployments | 438x275 | 438x275 |
| 48 | 8.3 A composite-property aggregate, decl | flowchart | old | an owned edge and a reference | 609x138 | 609x138 |
| 49 | 8.4 Identity, epoch and privacy together | flowchart | old | identity, epoch and privacy at one scope (now left to right, was 1519 px) | 865x535 | 865x535 |

Diagrams over about 1200 px in the first render were reduced (the overview, the replace, the NOT EXISTS, the contract, the uniqueness patterns and 8.4). Three stay between 1200 and 1300
(5.9's state diagram as it was, the replace picture at 1278 and the append of events at 1224).

## Decisions taken alone

| # | Decision | Reason |
|---|---|---|
| D-65 | a sequence diagram carries the palette as `rect rgba(...)` phases with the palette's fills at 50 percent opacity, a class diagram as `style` lines, and every subgraph box is drawn with no fill and a grey outline | mermaid has no class for these. Opaque palette fills put the theme's light text on pale colour in the dark theme. The default cluster fill is a pale yellow, which would read as the receipts colour |
| D-66 | the new subsections are 5.13 and 5.14, and the cross references moved to 5.15, instead of appending after 5.13 | no section anchor of the README is cited elsewhere (checked), and the narrative reads before the cross references |
| D-67 | two §6 definitions still described the Mustache templates H2.9 retired (`dal:GeneratedOperation`, `dal:ParameterBinding`), and the compiler diagram of §4 had a "select named templates" step. Both definitions are rewritten to name the builder, as four reconciliation lines in a fourth group of the H2.11a file (141 in all), and the diagram step reads "select a builder per operation". Three stale anchors in `tools/persistence/README.md` are repointed to §5.6.1, §5.6.10 and §5.6.11 | found in our own review of the slice. Each changed comment is a graph difference, so it is reconciled, not hidden |

## Probes

| Probe | Expected | Result |
|---|---|---|
| a doubled arrow in the diagram of 5.13 (`A --> --> B`), rendered with the script in the scratchpad | the render check fails naming the diagram | diagram 17 (line 1874) failed in both themes with a parse error on line 2, 2 failures, exit 1. Restored |
| a link to the sketch in the paragraph under 5.13.1 | `check:published-decisions` fails | `SOURCES ontology/persistence/README.md:1902: refers to a working document`, `sources: 1 failure(s)`. Restored, 0 failures |

The render script is in the session scratchpad and not in the repository, so the render check is not a task. A task would be a tool change for the maintainer to approve.

## Checks, run in this session

| Command | Result |
|---|---|
| `mise exec -- python tools/literate_extract.py ontology/persistence/README.md --layer persistence --check` | `4 extracted artefact(s) consistent with ontology/persistence/README.md` |
| `mise run check:literate-migration -- persistence a1df48b7` | 833 differences, all only in the tree, the axioms and shapes listed above (D-73) |
| `mise run check:published-decisions` | `sources: 0 failure(s), 545 report(s) for READMEs not yet migrated`, 6 passed |
| `mise run check:deny-terms` (and with `--all`) | `0 finding(s) against 5 entries` |
| `mise run check:catalogue` | `19 module(s) and 8 tool package(s) agree with the tree` |
| `mise run check:site-sections` | `9 section(s), 1 copy(ies) current`, 6 passed |
| `rm -rf ontology/persistence/execution && mise run check:ontology-catalog` | `1137 passed, 7 skipped`, `ontology catalog consistent, 2 known defect(s) reported` |

`check:persistence` and `check:persistence-oxigraph` were not run, since no code, test, builder or example changed. `build:persistence-execution` was run to read the generated SPARQL and its output deleted.
`check:ontology-versioning` fails with `UNBUMPED` as on the rest of the branch (TD-64), and is not run here.

## Files

`ontology/persistence/README.md`, `ontology/persistence/docs/precedence-and-resolution.md`, `ontology/persistence/docs/aggregate-boundaries.md`, this Pack, the status record, plan §4.19 and the sketch's status line.

## Open

- `tools/persistence/README.md` links `persistence/README.md#710-write-discipline`, `#7101-membership-encoding` and `#71-aggregate-boundary`, anchors that H2.11a renumbered (5.6.10, 5.6.11, 5.6.1). Not changed here.
- Three diagrams are a little over the 1200 px aim (5.9 at 1230, the replace at 1278, the append of events at 1224).

## Follow-ups of 2026-10-21

At the maintainer's request, after the review of H2.11b. Built autonomously.

**What we did.**

- **6.6 split.** The 12 kinds of logical resource and the 3 Unicode pipelines are in two new tables of 6.4 (type, definition), and 6.6 keeps the 15 `dal:logicalKey` and `dal:unicodeVersion` statements. The extractor accepts a 6.6 block that states a subject already in a table. The split changes no graph.
- **Enumerations.** Each of the 43 classes below has `**Equivalent to.** { ... }` in 6.1, which compiles to `owl:equivalentClass [ a owl:Class ; owl:oneOf ( ... ) ]`. No `owl:AllDifferent` is added, as asked.
- **SHACL.** 26 object properties ranging over a closed class had no `sh:in` of that class's list. They have one now, in `dal:<Class>EnumerationsShape` shapes (D-70). The others existed.
- **Witnesses.** The witness coverage test requires every node shape to be seen reporting and seen conforming. The 10 new shapes have one `shape-<Class>EnumerationsShape.ttl` each in `tools/persistence/tests/witnesses/` (a value outside the spec), and `ok-MintingRecipeEnumerationsShape.ttl` gives the one shape that no fixture had a conforming node for. These 11 files are new, and no existing test file changed.
- **Axiom Index.** The generated region of 6.7 is inside `<details>`, with a sentence before it. `--check` is consistent.
- **Test.** `tools/persistence/tests/test_enumerations.py` (88 cases) asserts that each `owl:oneOf` list is the set of individuals the spec types with the class, and that every property ranging over the class has a property shape whose `sh:in` equals it. The examples and the expected profiles are validated against the shapes by `test_compiler_integration.py` and `test_contract_shapes.py`, which we rely on.

**Closed (43).** `dal:AggregateBoundaryStrategy`, `OwnershipKind`, `ReferenceMode`, `ConcurrencyStrategy`, `OrderingGrain`, `DatasetTierModel`, `ReceiptModel`, `MetaTopology`, `OperationKind`, `ParameterKind`, `Rule`, `Source`, `AccessMode`, `AuditOutcome`, `GuardStatus`, `GraphNaming`, `DeclarationSource`, `ColumnKind`, `PayloadEncoding`, `BoundaryShapeAbsence`, `DigestPartRole`, `ResourceRole`, `IdentityStrategy`, `OccurrenceNamespaceDerivation`, `EventIdentityStrategy`, `SurrogateKind`, `SelfReferenceRule`, `EpochAuthority`, `EpochGuardScope`, `PrivacyClass`, `ErasureStrategy`, `ErasurePrecedence`, `GlobalReadStrategy`, `ContiguityCheckMode`, `RetentionMode`, `EtagForm`, `EtagRepresentation`, `FirstWriteMode`, `DeadlockPolicy`, `WriteDiscipline`, `MembershipEncoding`, `SchemeState` and `ResourceKind`. In each the spec defines the members, and the compiler or the contract emitter reads them by name, case by case.

**Left open.** The classes without individuals in the spec are not enumerations. The scopes (`dal:ProfileScope` and its five subclasses), the profiles (`dal:DataAccessProfile` and the per-dimension profiles), `dal:UniquenessConstraint`, `dal:ClaimScheme`, `dal:DigestScheme`, `dal:CapabilitySpec`, `dal:CapabilityRequirement`, `dal:CapabilityCheck`, `dal:Template`, the contract declarations, `dal:CompiledProfile`, `dal:MintingRecipe`, `dal:Diagnostic` and `dal:ReferenceEdge` are all instantiated by an adopter or by the compiler. `dal:DigestScheme` is the only candidate that looks like an enumeration, and an adopter declares its own schemes.

**No reconciliation group (D-73).** The migration was proven at `a1df48b7`, where the check against `f25008b2` passes with the 141 differences of groups 1 to 4. The enumerations are a modelling change after the migration, reviewed as one, so they are not listed as migration differences. Against `a1df48b7`, `check:literate-migration -- persistence a1df48b7` lists 833 differences, every one only in the tree and none only at the ref: the 43 `owl:oneOf` classes, the 40 `owl:AllDifferent` axioms, their list cells, and the 26 `sh:in` property shapes in 11 node shapes. So the 6.6 split moved text and lost nothing.

**Decisions taken alone.** D-68 to D-72 in the status record.

**Anchors.** A script in the session scratchpad (not in the repository) read every markdown link with a fragment against GitHub's slugs.

- Fixed in Persistence. `ontology/persistence/README.md` (TSD-01), `ontology/persistence/docs/aggregate-boundaries.md` (`#71-aggregate-boundary` to `#561-aggregate-boundary`, text §7.1 to §5.6.1), `ontology/persistence/docs/precedence-and-resolution.md` (worked example 2 to `#82-a-shared-class-two-deployments`), and `tools/persistence/README.md` had none left.
- Fixed elsewhere. the TSD-01 and TSD-18 slugs in `docs/developer/plans/formal-methods-track-h.md`, `docs/developer/technical-debt.md`, `docs/developer/validation/FMH-H2-4b.md`, `tools/testing/oxigraph/README.md` and `docs/architecture/triple-store-discovery.md`. The `(planned ..., built ...)` plan headings 4.3, 4.4 and 4.10 in `docs/developer/INDEX.md`, `docs/developer/status/formal-methods-track-h.md`, `docs/developer/sketches/formal-methods-track-h-typed-ir.md`, `docs/developer/validation/FMH-H2-5.md` and `FMH-H2-6.md`. `#7-documentation-rule` in the two insurance READMEs. `#r9-...-what-n7-means` in `docs/developer/sketches/logic-encoding-research.md`. No published ADR is touched.
- Not fixed, 26 in all. `docs/_includes/theory/04-three-valued-logic.md` and `06-session-types-spc.md` link `#dl` and `#conservative`, ids of the page that includes them. `docs/developer/INDEX.md` links 17 `#phase-N` fragments of the two surface-MORK documents, whose headings carry a title after the number, and `#vocabulary-consumer-hardening--planned-2026-09-25` and four `#3N-...` fragments of `surface-outstanding-items.md`, whose headings were renumbered. `docs/developer/sketches/REFERENCE_rdf-sparql-patterns.md` links `#plan` and `#sketch`, which have no heading. The right target is not certain for these.

**Reasoners.** No check runs a reasoner over Persistence (`check:reasoning-isolation` only guards the poms, and no other module imports it), so `owl:oneOf` is not exercised by one.

**Checks.**

| Command | Result |
|---|---|
| `literate_extract.py ... --layer persistence --check` | `4 extracted artefact(s) consistent with ontology/persistence/README.md` |
| `mise run check:literate-migration -- persistence a1df48b7` | 833 differences, all only in the tree, the axioms and shapes listed above (D-73) |
| `mise run check:persistence` | `4346 passed, 1 xfailed`. A first run failed 5 witness coverage tests (10 unwitnessed new shapes), fixed by the witness files above |
| `mise run check:persistence-oxigraph` | `368 passed, 3979 deselected` (run before the witness files, which no Oxigraph test reads) |
| `mise run check:persistence-expected-profiles` | `expected profiles are current` |
| `mise run check:published-decisions` | 0 source failures, 6 passed |
| `mise run check:deny-terms` | `0 finding(s) against 5 entries` |
| `rm -rf ontology/persistence/execution && mise run check:ontology-catalog` | `ontology catalog consistent, 2 known defect(s) reported` |

**Applied by us after the follow-ups.** Each enumeration of two members or more has an `**All different.**` paragraph in 6.5 (40), which
compiles to `owl:AllDifferent`, so a reasoner can tell the values of a closed set apart. The one class diagram of §4.2 is eight generated parts
(D-59), each drawing its own classes with their members, a class it links to in another part as a bare box, and each enumeration's
individuals. Every class of §6 is in a part, which the extractor checks.


## Follow-ups of 2026-10-21, second review

**What changed.** Seven individuals had no class. `dal:UniquenessEnforcementLevel` ({ `dal:Advisory`, `dal:Transactional`, `dal:Strong` }),
`dal:ViolationPolicy` ({ `dal:Reject`, `dal:Merge`, `dal:Quarantine` }) and `dal:ConcurrencyLevel` ({ `dal:Linearizable`, `dal:BestEffort`,
the new `dal:NoConcurrencyGuarantee` }) close them, each with a definition, an `**All different.**` paragraph and its individuals' definitions.
`dal:CommitValidationLevel` ({ `dal:NoCommitValidation`, `dal:ShaclCoreValidation`, `dal:ShaclSparqlValidation`, `dal:CustomRulesValidation` })
replaces the strings of `dal:providesCommitValidation`. `dal:providesCas`, `dal:requiresCas` and `dal:providesCommitValidation` are object
properties. `dal:minConcurrencyLevel`, `dal:onViolation`, `dal:minEnforcementLevel` and `dal:requiresUniquenessLevel` gain a range.
Shapes: `dal:UniquenessConstraintEnumerationsShape`, `dal:CapabilityRequirementEnumerationsShape` and `dal:CapabilitySpecEnumerationsShape` are new,
`dal:ConcurrencyProfileEnumerationsShape` gains `dal:minConcurrencyLevel` (`dal:Linearizable`, `dal:BestEffort` only, D-74), and
`dal:CapabilitySpecShape` loses its string `sh:in`. The compiler (`capability.py`, `compiler.py`) ranks levels by IRI and emits `dal:requiresCas`
as an IRI. The generated spec and shapes and the README's diagrams and axiom index are regenerated, and the 0.19.0 release notes list the changes.

**Expected profiles changed (for re-approval).** All eight differ only in `dal:requiresCas`, now an IRI:
`baseline-single-class`, `baseline-single-class.caller-named`, `composite-project-ownership`, `epoch-dataset-level-guard`, `value-based-cas`,
`write-discipline-composite-append-versions`, `write-discipline-delta-membership` and `write-discipline-noboundary-append-versions`
(`.expected.ttl`). The library fixtures `baseline-single-class`, `composite-project-ownership` and `write-discipline-delta-membership`
(`.compiled.ttl`, `packages/persistence/python/tests/data/`) change the same way.

**Tests changed.** `test_capability.py` states levels as IRIs and gains three cases (ranking, a spec naming no level, the loader reading an IRI).
`test_enumerations.py` gains the exception for `dal:minConcurrencyLevel` and two cases (no-guarantee level refused, strings refused), and its
floor of enumerations is 47. Witnesses: `shape-` and `ok-` for the three new shapes, `shape-CapabilitySpecShape` now fires on a non-boolean flag,
and `refusal-CapabilityCheckFailed` and `capability-spec-example.ttl` name individuals.

**Checks.** Extractor `--check`: 4 artefacts consistent. `ontology_version_check.py --base-ref origin/main`: no unbumped changes.
`check:persistence`: 3975 passed, 1 xfailed. `check:persistence-conformance`: 4371 passed, 1 xfailed. `check:persistence-expected-profiles`: current.
`check:persistence-library`: 91 vectors passed and 113 tests passed. `check:full-sweep` after removing `ontology/persistence/execution`: all 17 checks passed.

**Approved 2026-10-23.** The maintainer re-approved the eight expected profiles and the three library fixtures, accepted D-74 to D-77, and countersigned the changed tests of this section.
