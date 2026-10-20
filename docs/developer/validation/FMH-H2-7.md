<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.7, the vocabulary and the compiler's emission

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.7, planned in
[plan §4.7](../plans/formal-methods-track-h.md#47-h27-the-vocabulary-and-the-compilers-emission-planned-2026-10-14)
(H2.7-Q1 to Q4, decided 2026-10-20, with Q5 overtaken by TD-64) and built the same day for the maintainer's review. Authored and run in autonomous
mode, not committed. Versioning is ignored on this branch (TD-64), so no version IRI moved and the release table was not rebuilt.

**For the maintainer:** accept or change the ADR-A123 addendum and the ADR-A79 addendum (accepted with the slice's plan, so the decisions taken
alone are the part to read), the vocabulary in `spec/persistence.ttl` §10a, and the decisions taken alone below.
**For countersignature (non-weakening rule):** five tests were removed, two replaced and six changed, listed below with what covers each now.

## Invariant

`compile` emits, for every generated operation, the contract that `persistence.contract` derives from its builder, with a minted IRI for every
declaration, no blank node and no SPARQL text, and it records the run's choices. `instantiate` renders what the profile says and takes no flag.
Everything a compiled profile names is a documented term of the specification, every enumeration is closed, and the shapes check the structure of
the contract and three rules across it. The reviewed expected profiles equal what `compile` emits, up to graph isomorphism. No operation reads or
writes the default graph, and none is declared by hand.

## What changed

- **Vocabulary** (`spec/persistence.ttl` §10a, 122 terms). The classes and properties of the contract, and the enumerations that
  `kinds.expected.ttl` held, as individuals with their logical keys and realisations: operation kinds (with `dal:PayloadCheck`, Q3), resource
  kinds, access modes, parameter kinds, column kinds, guard status, graph naming, declaration source, digest part roles, rules, sources and
  payload encodings. Each is documented. `dal:templatePath` is removed, `dal:templateVersion` moves to the generated operation (domain and
  integer range) and `dal:boundaryShape` and `dal:referenceEdge` lose a domain they had for one use, since the contract is a second. The terms
  H2.6c to H2.6f added were already declared, and gained comments where they lacked one (the classes `dal:WriteDisciplineProfile`,
  `dal:WriteDiscipline`, `dal:MembershipEncoding`, `dal:ReceiptModel`, `dal:digestPart`, `dal:partRole`). `dal:dataGraph` and `dal:NoBoundary` say a family with
  no boundary keeps its values in a data graph.
- **The `pat:` terms** (`pat:currentVersion`, `previousVersion`, `addsMember`, `dropsMember`, `checkpoint`) are in Appendix A of the patterns guide, where the
  pattern vocabulary lives, with `pat:quarantinedOwner` and `pat:quarantinedAt`, which the quarantine operation wrote and the appendix lacked.
- **Shapes** (`shapes/constraints.ttl`, 13 new). One per declaration of the contract (`dal:OperationContractShape`, `ParameterDeclarationShape`,
  `ResourceAccessShape`, `ResultColumnShape`, `PayloadContractShape`, `DigestContractShape`, `DigestPartShape`), and the rules across them. Every
  enumeration value is closed with `sh:in`. `dal:ContractDeclarationIsIriShape` forbids a blank node. `dal:ContractHoldsNoSparqlTextShape` is a closed shape
  with a pattern on each name, so no property of a declaration but its own exists and no name is a query (SI-5). `dal:RequiredParametersGuardedShape`
  is the one SPARQL shape, and the guard rule holds in both directions. Three more close the configuration terms of H2.6c to H2.6f
  (`dal:WriteDisciplineProfileShape`, `ReceiptProfileShape`, `ReferenceModeShape`). All but one are SHACL Core, each targets one class, and the one
  query starts from `$this` and tests the parameters with `FILTER EXISTS` (efficient queries and shapes, R1, R4, R5).
- **Emission.** `persistence.contract_emit` (moved out of the test helper) writes the contract. `compile_to_graph` and `compile` take `guards` and
  `--no-parameter-guards`, and `graph_names` and `--caller-graph-names`, and record `dal:guardStatus` and `dal:graphNaming`. `instantiate` reads them
  per operation (`instantiate.run_choices`), finds the builder by `dal:templateId` (no suffix) and has no flags and no `guards` or `graph_names`
  arguments. `dal:templatePath` is no longer emitted.
- **TD-43 (Q1).** `dal:NoBoundary` with `dal:Optimistic` and a value guard needs `dal:dataGraph`, refused without it as `MissingDataGraph`. The builder
  `cas-replace-value-guard` writes and reads only that graph, with a parameter guard, and `HAND_DECLARED` is empty. The example gained
  `dal:dataGraph <urn:g:order-status>`.
- **Expected profiles.** Eleven of the twelve are unchanged in content. `value-based-cas` changed as TD-43 says (the `dataGraph` binding, builder
  version 2, `dal:Guarded` and `dal:BuilderDerived`). `kinds.expected.ttl` is deleted. `build:persistence-expected-profiles` removes a file no
  configuration produces, and `check:persistence-expected-profiles` compares by isomorphism.
- **Witnesses.** The witness check reads the expected profiles as conforming fixtures, and the 13 shapes have 13 negative witnesses over a shared
  `_base-contract.ttl`. `value-guard-MissingDataGraph.ttl` witnesses the new refusal. 122 of 122 rules are witnessed (shapes 49 of 49, from 36).
- **Documents.** The ontology README (§7.1, §9, §9.1, §12, §13), the compiler README, the aggregate boundaries note, the ADR-A123 addendum (and its
  status line, which said eight addenda and now says twelve), the ADR-A79 addendum, and TD-43, narrowed to its residual (the guards-off case).

## Tests removed or changed (for countersignature)

| Test | What happened | What covers it now |
|---|---|---|
| H2.6-T3, base profile: the file minus the new terms is `compile` output minus `dal:templatePath` | replaced, as the plan says | H2.7-T1 compares the whole file with `compile` output, up to isomorphism, for all 12 |
| H2.6-T4, agreement in three outcomes (equal, intended, failure) | replaced, as the plan says | H2.7-T1, since the emitted profile is the builder's contract (`contract_emit`) and the file equals it |
| H2.6-T5, every intended difference is used, and the value guard is hand-declared | removed, the table is empty (the `INTENDED` list and its dataclass are gone) | H2.7-T2, `HAND_DECLARED == {}` and every source is `dal:BuilderDerived` |
| H2.6-T8, the value guard's declared names are the `$` names of its template (H-D11) | removed, the guard has a builder | H2.6-T7, which runs for every builder and now includes it |
| H2.6-T9, two compiles in shuffled order give the same new triples | removed | H2.7-T9b, the same with whole-profile isomorphism and identical declaration IRIs |
| H2.6-T10, a blank node added to a declaration is detected | removed, it asserted what it had just done | H2.7-S2 (two blank-node witnesses) and H2.7-S6 |
| H2.6-T11, every term a profile names is in `kinds.expected.ttl` | removed with the file | H2.7-T1, T3 and T5 against the spec |
| H2.6-T1, T2 | changed: no `kinds` file (12 files), the `templatePath` check by predicate name, T2 over every file | |
| `test_h2_2_t1` (ported builders) | changed: gains `cas-replace-value-guard` | |
| H2.6-T12 (builder versions) | changed: the exception for the value guard is gone | |
| tests that passed `guards=` or `graph_names=` to `instantiate_*` or `templatecheck.operations` (H2.2-T17 to T19, H2.3-T30 and T31, HO1, HO5, H2.4a and HO7 helpers, and the two benchmarks) | changed: the choice is made at `compile` and the profile carries it | |
| `test_h2_6e_t3` | changed: counts the profile's own edges, since a payload contract also carries copies | |

No test was skipped or loosened. `builder-goldens.json` gained the value guard (version 2).

## Decisions taken alone, for the maintainer's review

1. **`GeneratedOperation.template_id` keeps its `.mustache` suffix in memory until H2.9.** Only the profile's `dal:templateId` drops it, and
   `instantiate` adds it back to read an overriding template library. About fifty tests assert the in-memory value, and H2.9 deletes it.
2. **`dal:templateVersion` is declared on the generated operation,** not on `dal:Template`, because the approved files and the compiler write it
   there. The range is `xsd:integer`, as written.
3. **`dal:boundaryShape` and `dal:referenceEdge` lose their `rdfs:domain`.** The approved files use both on the payload contract, and a domain would
   type that contract as a boundary profile or a compiled profile under entailment.
4. **Enumerations are closed with `sh:in`,** as `dal:ownership` already is, and not with `sh:class`. The closure then holds without the
   specification in the data graph. A test holds each list to the individuals of the specification, and each enum of the code to both.
5. **The scope of Q1's `MissingDataGraph`** is a `dal:NoBoundary` family that generates the value guard (`dal:Optimistic`, a
   `dal:valueGuardProperty`, not `dal:AppendRecords`). The other no-boundary families either already need one (`dal:AppendVersions`) or write
   nothing to a data graph. It has a refusal and a witness and no shape, since the condition spans a boundary and a concurrency profile.
6. **The value guard's resource is `dal:PropertyValue`, keyed by the root,** and its text is a change and not a port, so its builder is at
   version 2. The Mustache template changed in the same commit so that the equivalence harness still holds the two together.
7. **`instantiate` reads the guard and the graph naming per operation.** A profile that records neither renders with the guards on and the query
   naming its graphs. A profile compiled by hand is therefore guarded by default, and `dal:GuardsOff` is the only way to turn a guard off.
8. **Declaration IRIs include the deployment** when a target has one (`…/Behaviour/<deployment>/compiled/…`), so two deployments of a class do not share
   declarations. A target without one mints as the approved files do.
9. **`HAND_DECLARED` stays as an empty dictionary and `dal:HandDeclared` stays in the vocabulary,** as the escape hatch the brief's "emptied"
   implies. Removing the individual would change a closed enumeration for no gain.
10. **The expected profiles are the positive fixtures of the shapes through the witness check,** by adding them to the files `observe_shapes` reads.
    They are not compiled there.
11. **`test_contract_shapes.py` tests the property of each rule** by mutation and by the pair (shape, path), which the witness check, which needs
    only that a shape fires, cannot. The files under `witnesses/` serve that check.
12. **`--check` compares by isomorphism and `--write` removes a stale file,** so a deleted configuration leaves no orphan (`kinds.expected.ttl` went that way).
13. **TD-43 is narrowed and not removed,** since it carried TD-34's guards-off residual, which H2.8's `INFO` diagnostic closes.
14. **The ADR-A123 status line is corrected** (eight addenda became twelve), since it was already stale.
15. **`pat:quarantinedOwner` and `pat:quarantinedAt` are added to Appendix A** with the five terms the brief names, because a check I ran over the
    builders and templates found them missing. It was a manual check, since a test that reads the guide fails `test_rc3_t17` (the catalogue says the
    persistence tests reach `contracts/identity` and `ontology/persistence` and not `docs/architecture`). See what remains.

## Test cases

`test_contract_emission.py` (62 cases), `test_contract_shapes.py` (80), and `test_expected_profiles.py` (132, rewritten), on rdflib and Oxigraph where they
execute updates.

| ID | Checks |
|---|---|
| H2.7-T1 | every term a compiled profile uses (examples and expected profiles) is declared in the spec, with the right kind of declaration |
| H2.7-T2 (emission) | no `dal:templatePath` in the spec or any profile, no `.mustache` in a `dal:templateId`, and every id is a builder |
| H2.7-T3, T4 | each of 18 enumerations of the spec is the set the code uses, and each logical key is the spec's |
| H2.7-T5 | each of 16 `sh:in` lists of the shapes is the enumeration of the spec |
| H2.7-T6 | every term of the contract, of the disciplines and of the enumerations has an `rdfs:comment` |
| H2.7-T8 | `PayloadCheck` is a kind in the code and the spec, and no builder has it |
| H2.7-T9, T9b | no declaration is shared by two operations, even across deployments, and two compiles in any load order give one profile |
| H2.7-T10, T11 | `compile` records the guard status and graph naming, and refuses an unknown naming |
| H2.7-T12, T13, T14 | `instantiate` follows the profile, takes no flag, cannot disagree with its profile, and the flags moved to `compile` on the command line |
| H2.7-T15 to T18 | `MissingDataGraph` for no boundary, the value guard's builder, every pattern in the data graph, and `DefaultGraphPattern` for one outside it |
| H2.7-T19 to T21 | on both engines, with the guards on and off where it applies: the value is replaced in the data graph and the default graph copy is untouched, a stale old value writes nothing, and a missing parameter writes nothing with the guard on |
| H2.7-S1 | each expected profile conforms to every shape |
| H2.7-S2 | 48 mutations, each reported by its shape and path: closed values, cardinalities, datatypes, blank nodes, SPARQL text, and the guard rule in both directions |
| H2.7-S3 to S5 | the statuses that promise nothing, and the closed values of H2.6c to H2.6f |
| H2.7-S6 | what `compile` emits conforms to the shapes, for all 12 |
| H2.7-T1 (profiles) | the profile `compile` emits is isomorphic to each of the 12 expected files |

## One command

```
mise run check:persistence
mise run check:persistence-oxigraph
mise run check:ontology-catalog
mise run check:persistence-membership
```

From the repository root. A pass is no failed test, the expected profiles current, and the witness coverage at 122 of 122.

## Results

Run of 2026-10-20 on the finished tree.

| Command | Result |
|---|---|
| `mise run check:persistence` | 3938 passed, 1 xfailed, no failures, expected profiles current (H2.6f recorded 3802) |
| `mise run check:persistence-oxigraph` | 361 passed in the persistence tests marked for Oxigraph (H2.6f recorded 353), and the support tests |
| `mise run check:ontology-catalog` | 1136 passed, 7 skipped |
| `mise run check:persistence-membership` | passed, the benchmark's 10 tests and the counts of FMH-H2-6f unchanged (about 5 minutes). Its two scripts now compile with `guards=False` and not instantiate with it |
| `python -m persistence witness` | 122 of 122 rules witnessed, 0 listed gaps |
| `mise run check:ontology-versioning` | not run, which fails `UNBUMPED` as expected on this branch (TD-64) |

`build:persistence-execution` was not run, so no `execution` directory was left. `check:deny-terms` was not run (it needs a personal deny-list).
The first catalogue run failed `test_rc3_t17` on a test that read the patterns guide, which the test was changed to avoid (decision 15).

## Adversarial probes

Each was run on the finished tree and reverted, and the file was compared with its copy.

1. **An operation with a blank-node declaration** (the `root` parameter written as a blank node). H2.7-S6 fails on all 12 profiles, reported by
   `dal:ContractDeclarationIsIriShape` and the property constraints of `dal:OperationContractShape`, and the isomorphism test fails with them.
2. **A profile emitted differently from its expected file** (every guard status written as `dal:GuardsOff`). H2.7-T1 fails for 11 of the 12
   files, and `expected_profiles.py --check` lists them as stale.
3. **A no-boundary family without a data graph accepted** (the check disabled). H2.7-T15 fails. The compile then fails on a missing binding, so the family
   is not silently accepted even without the check.

The sketch's other two probes, an enumeration value outside its kind and the pattern moved back to the default graph, are H2.7-S2 and H2.7-T18.

## Deliberate non-coverage and what remains

- **Emission of the `payload-check` operation** and the payload's checks (H2.8). **Retiring Mustache (H2.9)**, so the templates, the equivalence harness
  and the suffix handling stay.
- **A test that the `pat:` terms of the builders are in Appendix A.** The check is correct and was run by hand with nothing missing, but a test in
  `tools/persistence` that reads the guide must be declared in the repository catalogue (`reaches`, `docs/architecture`), which this slice was not to edit.
  Add the reach and restore the test, or leave it manual.
- **Versioning (TD-64).** No version IRI moved, `check:ontology-versioning` was not run and `build:ontology-releases` was not run. The release number
  and the tag are for the merge into `main`.
- **A shape for `MissingDataGraph` on a no-boundary family.** The refusal and its witness cover it.
- **The plan §4.7 "Built" note, the status record and the index** are not edited by this slice, as instructed.
- Fuseki and the other stores.
