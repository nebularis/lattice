<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.8b, the payload checks, the caller check and the audit outcome

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.8b, the second half of
[plan §4.8](../plans/formal-methods-track-h.md#48-h28-the-typed-payload-and-the-caller-side-checks-planned-2026-10-14), built on the library of
[FMH-H2-8a](FMH-H2-8a.md) under [ADR-A132](../../architecture/decisions/ADR-A132-persistence-caller-library.md). Authored and run in autonomous mode, not
committed. Versioning is ignored on this branch (TD-64), so no version IRI moved.

**For the maintainer:** read the decisions taken alone below, above all decision 1 (the library walks the contract and does not run the query), decision 4
(an empty `logGraphs` is refused by default) and decision 5 (the audit outcome is not a result column). Re-approve the twelve expected profiles, which all
changed (below). Accept or change the ADR-A123 addendum (accepted with the slice's plan, so the decisions taken alone are the part to read).
**For countersignature (non-weakening rule):** no test was removed, skipped or weakened. Seven existing tests changed to admit the one operation that has
no template, and one inverted a statement that H2.8b made false (below).

## Invariant

A caller holding a compiled profile and the library cannot send a request that names a subject outside its aggregate, takes a position that is not exactly
`xsd:long`, names a graph the naming rule does not give, or audits no graph and calls the result clean. Each refusal says why, before anything is sent.
The same rules are fixed by vectors that a program sharing no code with the library decides, and the generated `payload-check` query returns on rdflib and
Oxigraph what the library's walk returns.

## What changed

- **Library** (`packages/persistence/python`).
  - `bound`: `outside_bound` walks the owned edges of the payload contract from the root over the payload alone, and `outside_events` applies the rule of
    ADR-A123's addendum on the subjects of an event append.
  - `check`: `refusals` and `check_request`, with `Refusal` and `CallerCheckError`. Parameters present, none unknown, each of its kind, `xsd:long` exactly, a
    caller-named `$g` equal to the rule, `logGraphs` non-empty IRIs, the payload and event bounds, the rows of a batch, reference modes (with `version_of`) and the
    checkpoint list (with `membership`).
  - `audit`: `AuditOutcome`, `audit_outcome`, `registry_text`, `examined_query`, `run_audit`, and the `SparqlClient` protocol.
  - `contract`: `EdgeContract.target_shape`, `PayloadContract.shape`, and `ProfileOperation.bindings`, `examines` and `outcomes`, all read from the profile.
- **Compiler** (`tools/persistence`).
  - The builder `payload-check`, kind `PayloadCheck`, selected for a family with a payload operation and a boundary shape (`operations.py`). It has no template and
    `instantiate.BUILDER_ONLY` says so. Its graph role is `data` with the constant graph `urn:g:payload`.
  - The contract: each edge names `dal:edgeTargetShape`, the payload of an append of versions is rooted at `newVersion`, the payload contract carries the shape, and each audit declares
    `dal:reportsOutcome` (three values) and `dal:examinedParameter`.
  - Diagnostics: severity `INFO`, with `UnboundedPayload` (a warning under `compile --warn-unbounded-payload`) and `ParameterGuardsOff`, and from the maintainer's additions
    `PatchLogNotWritten` and the refusal `NoReceiptSharesMetaShard`.
  - The witness harness gains the `info` family, the `# option:` directive for a fixture, and fixtures for every new rule.
- **Ontology** (`persistence.ttl`, `constraints.ttl`). `dal:edgeTargetShape`, `dal:AuditOutcome` with `dal:Clean`, `dal:Failed` and `dal:NothingExamined`, `dal:reportsOutcome`,
  `dal:examinedParameter`, the comment of `dal:PayloadCheck`, and two properties on the operation shape.
- **Vectors** (`contracts/persistence`). Six new sections, 55 vectors, and the independent decisions in `verify-vectors.py` (91 checks, up from 36).
- **Documents.** The compiler README's "Using the generated SPARQL directly" is rewritten around the library and the caller check. The library, contracts and
  ontology READMEs, the patterns guide (a dated note in §15.2, which narrows TD-69), ADR-A123's addendum and the technical debt register.
- **Catalogue.** The persistence tool package reaches `docs/architecture`, for the test of decision 12.

## Added by the maintainer

| Item | What was built | Witness and tests |
|---|---|---|
| D-10 | `PatchLogNotWritten`, a warning when a family declares `dal:PatchLog` and none of its operations has a `-patch-log` template: an append discipline, an append-only concurrency, an unconditional write and a value-guarded write | `warning-PatchLogNotWritten.ttl` on `append-stream-dataset-guard`, and `test_h2_8b_t13`. The shipped `append-stream-dataset-guard` warns, as expected, and its expected profile gained the diagnostic. No other example warns |
| D-11 | `NoReceiptSharesMetaShard`, a refusal. Two compiled families whose operations bind the same `metaGraphPrefix`, one `dal:NoReceipt` and the other with a gap scan | `refusal-NoReceiptSharesMetaShard.ttl`, `test_h2_8b_t14` to `t16`. No shipped example is refused, which `t16` checks over every example that compiles |
| D-24 | `test_pat_vocabulary.py`: every `pat:` term of `builders.py`, `contract.py` and the templates is declared in Appendix A of the patterns guide. 32 terms in the builders and 33 in the templates, 43 declared. Probe in the table of probes | `repository-catalogue.md` reaches `docs/architecture`, and `check:catalogue` and `check:ontology-catalog` pass |

## Decisions taken alone, for the maintainer's review

1. **The library walks the contract and does not run the query.** The brief says the Python type runs the same query. The library would then need rdflib's
   reading of a property path from a term in no triple (TSD-08), and an engine for a walk of eight lines. It walks the owned edges instead, each with the
   shape it leads to (state elimination's automaton, which the query's path was made from). `test_h2_8b_t5` holds the generated query and the walk equal on 200 random payloads
   each for a composite family, a named-graph family with a shape and one whose shape owns nothing, on rdflib and on Oxigraph. The query is what a caller in another language
   runs, and the vectors fix both.
2. **The contract names the target shape of each edge and the boundary shape of the payload** (`dal:edgeTargetShape`, `PayloadContract.shape`). Without the target shape a walker
   can only close over the predicates, which accepts a node the shape does not own (vector `pc-the-shape-of-the-source-matters`). All twelve expected profiles regenerate for it.
3. **The payload of an append of versions is rooted at `$newVersion`.** The new version's own triples are the payload, and the owned path starts at the version and not at the
   identity. `payloadRoot` for `append-version` therefore changed from `root` to `newVersion`.
4. **An empty `logGraphs` is refused by default and allowed by a flag.** The plan's step 4 says the caller check refuses it, and the maintainer's decision for Q3 is (c), the audit
   reports nothing examined. Both hold. `refusals` has `allow_empty_log_graphs`, and `audit_outcome` returns `NothingExamined` for the allowed case.
5. **The audit outcome is not a result column.** A `HAVING` removes the clean groups, so no column of the query can carry it. The contract declares the three outcomes
   (`dal:reportsOutcome`) and the parameter an audit examines (`dal:examinedParameter`), and the library derives the outcome from the rows and from `examined_query`, a count of
   the receipts in the pinned graph and the listed graphs. A row wins over an empty registry, because a row means the audit read something. The audits that read fixed graphs
   report `Clean` over an empty graph (TD-72).
6. **Reference modes are checked only where the caller says what a version is** (`version_of`). A pinned edge needs an object known to be a version, and an unknown one is refused.
   An identity edge refuses a version. Without the classifier the modes are not checked, and the README says so. The walk reads the edges of every node the owned walk reaches, and not
   of an unreached node (TD-67 narrowed).
7. **A checkpoint is checked against the members the caller supplies** (`Membership`). The profile names no membership property, so the caller passes it. The check does not decide when a
   checkpoint is due.
8. **Not built.** The assert and retract slots of a patch log and the added and dropped member slots are not bounded (TD-70), since a retracted triple names state the payload no longer
   holds. Deployment shapes per event type are the optional tightening of the addendum and have no hook (TD-71).
9. **`payload-check` is generated for a family with a boundary shape only.** A named-graph family without one has the form checks, and compile says so (`UnboundedPayload`). A family
   whose shape owns nothing gets the query without a path, which admits the root alone (the vector `pc-a-shape-that-owns-nothing-admits-the-root-alone`). Its graph is the constant
   `urn:g:payload` with the graph role `data`, so the contract reads the aggregate in a local copy of the payload.
10. **The caller check is strict about names and kinds.** A parameter the operation does not declare is refused (`UnknownParameter`), so a misspelling is not silent. A plain string
    is accepted for an `Iri` parameter if it is a valid IRI, which `request_digest` already allowed for a target. A digest is 64 lower-case hexadecimal characters.
11. **The witness harness records `INFO` as a family of its own.** A `Diagnostic(severity="INFO")` call is an `info` rule, and a fixture takes `# option: warn-unbounded-payload` or
    `# option: no-parameter-guards`. `UnboundedPayload` has two call sites, so it is a rule of both families, and both are witnessed.
12. **The D-24 scope is the builders, the contract table and the templates.** The two other places that name a `pat:` term, `ir_render`'s prefix map and the tests, are not scanned.
13. **The D-11 witness uses a class name found by search.** `Mortgage58` hashes to the same one of 64 meta shards as `LoanApplication`. A change to the shard hash moves it, and
    `refusal-NoReceiptSharesMetaShard.ttl` fails by name if it does.
14. **Technical debt.** TD-43 (TD-34's residual) is closed, TD-44, TD-67 and TD-69 are narrowed, and TD-70 to TD-72 are new. TD-34 has no row of its own.
15. **A fourth compiled profile is kept by the library** (`composite-project-ownership`), because it is the one with a boundary shape and edges.

## Changes to existing tests

| Test | Change |
|---|---|
| `test_key_claims_and_audits::test_h2_5_t40` | the expected role table gained `payloadGraph` |
| `test_named_graph_builders::test_h2_3_t32` | the expected binding roles gained `payloadGraph`, `data` |
| `test_contract_emission::test_h2_7_t8` | inverted. It said no builder emits `PayloadCheck`, which H2.8b makes false, and now says one does |
| `test_builders` (t1, t2, t3, t4) | t1 lists `payload-check`. t2, t3 and t4 compare the operations that have a template, through `equivalence.templated`, which leaves out `BUILDER_ONLY` |
| `equivalence.compare_all` | skips the builder with no template |
| `test_tsd_34_builders::test_h2_6g_t1` | `len(templates) >= len(BUILDERS) - 1` |
| `test_templatecheck::test_h1_3_t16` | every template is still generated by some fixture, and the generated set less `BUILDER_ONLY` equals the library |
| `test_library_contract` | the fourth fixture |

The stricter checks of these tests stand. The set of templates must equal the generated builders that have one, and the harness still fails when it compares fewer operations than were ported.

## Expected profiles (for re-approval)

All twelve changed. Each gained the three `dal:reportsOutcome` of every audit (and the `dal:examinedParameter` where it applies), and each payload contract its boundary
shape and the `dal:edgeTargetShape` of its edges. Three of them gained the `payload-check` operation, the families with a boundary shape and a payload
(`composite-project-ownership`, `write-discipline-composite-append-versions` and `write-discipline-delta-membership`). The two profiles of an append of versions have the payload root `newVersion`.
Diagnostics are new in eight. `UnboundedPayload` as information is in `baseline-single-class` (both variants), `claim-scheme-dual-rotation`, `epoch-dataset-level-guard`, `uniqueness-merge-policy`
and `uniqueness-quarantine-policy`. `PatchLogNotWritten` is in `append-stream-dataset-guard` (D-10). `ParameterGuardsOff` is in the caller-named variant of the baseline, which is compiled with the guards off.

## Tests

| ID | Checks |
|---|---|
| H2.8b-V1 | `verify-vectors.py` decides the payload checks (12), the events of an append (7), the caller check (18), the audit outcome (6), the reference modes (6) and the checkpoint list (6) with its own code, and recomputes the 36 earlier checks. 91 pass |
| H2.8b-L1 | `test_check.py`, 34 tests. The bound (a subject outside, a reference edge not followed, inverse, recursive and nested edges, a cycle, no shape), the parameters (missing, unknown, `xsd:integer` and untyped epochs, ill-typed and out-of-range longs, a literal for an IRI), the naming rule, the log graphs, the outcome, `run_audit` over a fake client, the events and their rows, the reference modes, the checkpoint |
| H2.8b-L2 | `test_vectors.py` runs every new vector through the library (6 tests) |
| H2.8b-T1 to T4 | which families get `payload-check`, its shape (one parameter `root`, one column `s`, no payload of its own), the root of a new version, the shape and target shapes in the contract |
| H2.8b-T5 | the generated query and the library walk return the same subjects on 200 random payloads for each of three families, on rdflib and Oxigraph |
| H2.8b-T6 | a payload with a subject outside the aggregate is returned, and a literal `} } ; DROP ALL ; INSERT { {` is one literal through the slot text on both engines |
| H2.8b-T7 | on rdflib, an initial binding of `root` and its substituted text give the same rows |
| H2.8b-T8 | every audit declares three outcomes and its examined parameter, no other operation does |
| H2.8b-T9 to T12 | `UnboundedPayload` as `INFO`, as `WARNING` under the option and absent for a shaped family or a composite one. `ParameterGuardsOff` and its message. Both in the compiled profile and through the command line |
| H2.8b-T13 to T16 | `PatchLogNotWritten`, `NoReceiptSharesMetaShard` and its limits (another shard, two without receipts, two with), and no shipped example refused |
| H2.8b-T17 to T19 | the `pat:` terms of the builders and the templates are declared in Appendix A |
| witness | 127 rules, all witnessed, no known gap (refusal 54, warning 17, info 2, shape 49, audit 5) |

## Results (run 2026-10-20)

| Command | Result |
|---|---|
| `mise run check:persistence` | 3998 passed, 1 xfailed (the expected profiles check ran and passed) |
| `mise run check:persistence-oxigraph` | 5 passed, then 367 passed, 3632 deselected |
| `mise run check:persistence-library` | vectors 91 checks passed, 0 failed. Library 75 passed |
| `mise run check:ontology-catalog` | 1136 passed, 7 skipped, "ontology catalog consistent, 2 known defect(s) reported" |
| `mise run check:catalogue` | 19 modules and 8 tool packages agree with the tree |
| `mise run check:agent-guidance`, `mise run check:published-decisions` | 9 passed, 6 passed |
| `python -m persistence witness` (through `check:persistence`) | 127 of 127 rules witnessed |
| `build:persistence-execution` | not run, and `ontology/persistence/execution` does not exist |

The first full run of `check:persistence` had three failures, all in tests that assumed every builder has a template or a role table without `payloadGraph`. They are the changed
tests above, and the run that is reported passed.

## Probes

| Probe | Result |
|---|---|
| A payload with a subject outside the aggregate | the caller check refuses with `PayloadOutsideBound` naming the subject, and the generated query returns it on both engines (T6) |
| A literal holding `} } ; DROP ALL` | stays one literal through `Payload.sparql()` into an `INSERT DATA` on both engines, and names no subject (T6, vector `pc-a-literal-is-only-an-object`) |
| An `xsd:integer` epoch | the caller check refuses with `NotXsdLong` for `Lit`, rdflib `Literal` and an untyped literal, and passes `xsd:long` in three forms (L1, vector `cc-an-xsd-integer-epoch`) |
| An empty `logGraphs` | refused with `EmptyLogGraphs`, and allowed with the flag it gives `NothingExamined` and not clean (L1, `run_audit`, vector `ao-an-empty-registry-examines-nothing`) |
| An event triple whose subject is an existing aggregate | `EventOutsideBound` naming the aggregate, while an event naming the aggregate as an object passes (L1, vector `ev-an-existing-aggregate-as-subject`) |
| The walk ignores the inverse flag | `test_the_walk_follows_inverse_recursive_and_nested_edges` and the payload check vectors fail (2 failed, 73 passed), and the code was restored |
| `NotXsdLong` disabled | the epoch tests and the vectors fail, and the code was restored |
| A `pat:` term removed from the guide (computed, not edited) | the builders' set minus the declared set names `checkpoint` |

## What remains

- Deployment shapes per event type (TD-71) and the bound on the patch-log and delta member slots (TD-70).
- An audit that returns its own count (TD-72).
- A source of what is a version that the library can read, so `version_of` is not the caller's alone (TD-67).
- The Java sibling.
- The typed IR sketch §4 and §7.3 and the plan and status records, which this slice was told not to edit.
- Nothing is committed.

## One command

```
mise run check:persistence
mise run check:persistence-oxigraph
mise run check:persistence-library
mise run check:ontology-catalog
mise run check:catalogue
```

From the repository root. A pass is no failed test, the vectors at 91 of 91 and the witness at 127 of 127.
