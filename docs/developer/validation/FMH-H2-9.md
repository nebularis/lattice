<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.9, Mustache retired

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.9,
[plan §4.15](../plans/formal-methods-track-h.md#415-h29-mustache-retired-planned-2026-10-20). Authored and run in autonomous mode, not committed.
Versioning is ignored on this branch (TD-64), so no version IRI moved and `check:ontology-versioning` is not run here.

**Awaiting the maintainer's review.** Eight decisions were taken alone (D-42 to D-49), no expected profile changed, and the changed and removed tests are
listed below for countersignature.

## Invariant

Every generated operation is rendered from its builder, and nothing in the repository reads a Mustache template or imports a Mustache library. A request-time slot is the
plain-text marker `{{{name}}}`, filled by substitution in one pass. A builder's recorded text belongs to its operation and no fixture can move it. The
injection corpus runs over every builder and over the caller library's slot filling. `dal:SnapshotPerRevision` on a composite family written in place is refused
with a witness, and the receipt-only composite writes it alone reached are gone. S-3 reads the parameters an operation declares.

## What changed

1. **Removed.** `tools/persistence/src/persistence/templates/` (52 `.mustache` files), `render.py`, the `chevron` dependency and the `package-data` entry for the
   templates in `tools/persistence/pyproject.toml` (the only place it was declared, there is no lock file entry), `instantiate.BUILDER_ONLY`, `instantiate.TEMPLATE_SUFFIX`,
   the `template_dir` argument of `instantiate_*` and the `--template-dir` option of the command line, the equivalence harness (`tests/equivalence.py`),
   `tests/receipt_only.py`, and the stale lesson about Mustache comments in `environment-lessons.md`.
2. **Rendering.** `instantiate.build_operation` builds the typed operation from the builder `dal:templateId` names, and `instantiate` renders it. An operation that names a
   builder that does not exist is refused by name. `GeneratedOperation.template_id` has no suffix, in memory as in the profile (D-20 of H2.7 closed).
3. **H2.9-Q1, the slot marker.** `ir_render.slot_marker` and `ir_render.fill_slots` hold the convention. `fill_slots` substitutes in one pass, leaves a marker with no value
   alone, and so does not fill a marker that a value holds. The library already filled `logGraphs` by substitution, and its README now says so.
4. **H2.9-Q2, goldens keyed by operation.** `builder-goldens.json` is rendered from one canonical context (`builder_goldens.CANONICAL_CONTEXT`), so it no longer
   depends on the first fixture that generates a builder, and the `PINNED` workaround is gone (D-44).
5. **H2.9-Q3, the injection corpus.** `test_terms.py` puts every adversarial IRI and literal into every binding of every builder (1,059 cases) and counts the operations the text
   parses as. The library has `test_slot_injection.py`, which runs the corpus through `Payload`, `Rows` and `registry_text` and reads the values back from a store.
6. **D-12 (a).** The receipt-only create, replace and tombstone of a composite family (six builders with their dataset-guard variants) are deleted. `compile` refuses
   `dal:SnapshotPerRevision` on a composite family written in place with `CompositeBoundarySnapshotNotBuilt`. Witness: `witnesses/refusal-CompositeBoundarySnapshotNotBuilt.ttl`.
7. **S-3 (H-D11).** `templatecheck.Operation` carries the parameters the builder declares, and `analyse` takes them, where it scanned the text for `$name`. Only the
   BIND-with-bound-inputs assumption (H-D12) remains.
8. **Documents.** `tools/persistence/README.md` ("Using the generated SPARQL directly", the request-time slot section, the typed IR section, the test list, the receipt model
   bullet), `ontology/persistence/README.md` (the snapshot row, two stale "templates"), the comments of `dal:Template` and `dal:templateId` in the spec, the library README and docstring,
   an addendum to ADR-A123 (published, no working document outside its Provenance section), the sentences of ADR-A79's addenda that said the templates stay in use,
   TD-46 narrowed, and a sentence of TSD-34's record.

## Decisions taken alone

Numbered on from D-41 of the status record, which was the last (checked).

| # | Decision | Reason | To ratify |
|---|---|---|---|
| D-42 | The tests that reached the receipt-only composite writes through `receipt_only.py` are **ported to the patch-log variants, not removed**, with every assertion unchanged. `receipt_only.py` and the snapshot witnesses that only existed to reach those writes are removed | the brief said they are removed with the writes. Their subject is the sweep, the lifecycle of an aggregate and the guard, which the patch-log builders share, so removing them would lose coverage that still applies. Four modules, listed below | ratify, or remove them |
| D-43 | `CompositeBoundarySnapshotNotBuilt` is raised for a composite boundary with `dal:SnapshotPerRevision`, `dal:Optimistic` concurrency and no append discipline | those are the configurations that select the deleted writes, so a composite family that appends, or is append-only, still compiles with the existing warning. Row 2 (`CompositeBoundaryReceiptConflict`) is stated the same way, minus the concurrency | ratify |
| D-44 | The goldens use one canonical context. **48 of the 52 digests changed once**, so they were re-recorded by a one-time scratch run that skipped the "no changed text under an unchanged version" refusal. Before it, the old keying was run against the old record and all 52 builders still matched, so no builder's text changed. Versions did not move | the recorded text had to stop depending on which fixture came first. The refusal stays for every later update | ratify the re-baseline |
| D-45 | `fill_slots` is in `ir_render`, one pass, and `REQUEST_TIME_SLOTS` is gone (the static checks keep a stand-in for each name) | the slot is a rendering fact, and `ir_render` writes the marker | ratify the place |
| D-46 | `instantiate` and the CLI **lose** the template library override rather than keep it as an error | nothing reads a template, and the brief removes the machinery | ratify |
| D-47 | The `hygiene` message still says `templates:` | `test_h1_3_t21` and `t22` assert it and are not changed. A rename is a small follow-up | say if wanted |
| D-48 | The injection corpus counts operations, where it asserted `True` after a parse, and a literal corpus is added for the literal bindings | a corpus that cannot fail is not a gate | ratify |
| D-49 | The library gets its own corpus (`test_slot_injection.py`), which reads the values back from a store | the library does not import the compiler, so its slot filling cannot be reached from the compiler's tests | ratify |

## Changed tests (for countersignature)

No test was skipped or weakened. The assertions that changed are those whose subject was a template.

| Test | Change | Reason |
|---|---|---|
| `test_composite_lifecycle` (all, HO7), `test_composite_sweep` (all, HO1), `test_composite_boundary` (all, HO5), `test_composite_builders` (H2.4a) | run on the `-patch-log` composite builders (`witness._load_fixture`, which keeps `dal:PatchLog`) where they ran on the receipt-only ones (`receipt_only(...)`). The slots a patch log adds are filled with the checks' stand-ins. Every assertion is unchanged | D-12 (a), D-42 |
| `test_composite_lifecycle::test_ho7_t1` | expects the `-patch-log` ids | same |
| `test_composite_builders::test_h2_4a_t*` | the context comes from `test_builders.ported_operations`, which is `eq.ported_operations` without the harness | same |
| `test_builders::test_h2_2_t1` | the list of builders loses the six receipt-only composite ids and the name says builders | D-12 (a) |
| `test_builders::test_h2_2_t21` | was every graph slot and variable of every **template** is in the role table. Now every graph **variable** of every rendered builder is. Graph IRIs are held by t20 | the templates are gone |
| `test_graph_naming::test_ho8_t8` | was the 19 templates that name a graph encode the whole root. Now the 19 builders that read `graphPrefix` do, from their rendered text | same |
| `test_ir_render::test_h2_1_t12` | renamed ("plain text markers"), same assertions | the marker is not Mustache |
| `test_templatecheck::test_h1_3_t3` | takes the declared parameters, and a new test (`test_h2_9_t6`) shows an undeclared `$x` is reported | H-D11 |
| `test_templatecheck::test_h1_3_t16` | every builder, where it was every template file, is generated by some fixture | the templates are gone |
| `test_templatecheck::test_h1_3_t19`, `t20` | pass the operation's declared parameters | H-D11 |
| `test_patch_log::test_h2_6d_t19`, `t20` | a snapshot composite family is now refused, a snapshot named-graph family still gets the receipt-only writes and the warning | D-12 (a) |
| `test_expected_profiles::test_h2_6_t6` | the six `-patch-log` and `-no-receipt` composite stems, where it had the three receipt-only ones | D-12 (a) |
| `test_pat_vocabulary`, `test_tsd_34_builders::test_h2_6g_t1`, `t3` | the template halves removed. The builder halves are unchanged. `t3` reads the patch-log replace | the templates are gone |
| `test_slice_5_uniqueness` (three tests) | render the builders, where they rendered three templates. Same assertions | same |
| `test_builder_versions::test_h2_6_t13` | 52 cases, where there were 58 | the six builders are deleted |
| `test_terms` | the template corpus is replaced by the builder corpus (below), and the encoder tests no longer render through Mustache | H2.9-Q3 |
| `test_compiler_integration`, `test_membership`, `test_patch_log`, `test_slice_2_extensions`, `test_write_disciplines`, `test_reference_modes`, `test_contract_emission`, `test_expected_profiles` | the expected template ids lose `.mustache` | `template_id` has no suffix |

## Removed tests (for countersignature)

Their subject, the templates, the renderer or the harness, no longer exists. Counts are cases before the slice.

| Test | Cases | Why removed, and what holds the assurance now |
|---|---|---|
| `test_architecture::test_only_render_module_imports_chevron`, `test_chevron_render_is_never_called_with_a_dynamically_built_template_argument` | 2 | `persistence.render` is gone. Replaced by `test_no_module_imports_chevron` and `test_the_package_ships_no_template_files` |
| `test_builders::test_h2_2_t2` (every builder equals its template), `t3` (reads exactly the bindings its template uses), `t4` (the harness fails when it compares fewer than were ported), `t5` (a mutated builder is caught) | 1 + 57 + 1 + 6 | the equivalence harness. Held now by the recorded outputs, the expected profiles, the behaviour tests on both engines, and S-3 and S-4 |
| `test_builders::test_h2_2_t18` | 1 | an overriding template library is no longer read |
| `test_key_claims_and_audits::test_h2_5_t47` | 7 | the harness failing when a query is changed. The same seven changes are caught by the recorded outputs (the digest changes) |
| `test_template_alignment` (three tests of Mustache mechanics) | 57 + 57 + 57 + 1 | every template parses, no `{{` left, no template scans by prefix, and a slot cannot be bound at compile time. The first three are ported to the builders (52 cases each, renamed). The last has no subject, since the renderer that refused it is gone, and `SlotMisuse` in `test_ir_render` covers a slot used as a term |
| `test_pat_vocabulary::test_h2_8b_t19` | 1 | its builder twin `t18` stays |
| `test_terms::TestFullTemplateInjectionCorpus` | 684 | replaced by `TestBuilderInjectionCorpus` |

Collected cases in `tools/persistence/tests`: 4,008 before and 4,259 after. 77 cases were removed with no counterpart, and the 684 cases of the template corpus were replaced by
1,059 builder cases. The three Mustache-mechanics tests of `test_template_alignment` went from 171 cases to 156 builder cases, and 46 cases of tests parameterised over the builders went
with the six deleted builders. The library gains 38 cases.

## Tests added

| ID | Given / When / Then | Level | Pass criterion |
|---|---|---|---|
| H2.9-T1 | `witness.compile_fixtures` and `_load_fixture` raise, and `builder_goldens.current()` is called | L1 | equals the record |
| H2.9-T2 | a composite family with `dal:SnapshotPerRevision` compiles, with either guard | L2 | `CompositeBoundarySnapshotNotBuilt`, and the same family under `dal:PatchLog` compiles |
| H2.9-T3 | the three receipt-only composite stems are asked for | L1 | no builder, a `ValueError` naming TD-46, and a named-graph snapshot family still warns |
| H2.9-T4, T4b, T4c, T4d | every fixture's template ids are builders with no suffix. `render`, `BUILDER_ONLY`, `TEMPLATE_SUFFIX` and `chevron` are gone. An unknown builder is refused by name. `fill_slots` is one pass | L1 | as stated |
| H2.9-T5 | a built operation with an unfilled slot | L1 | does not parse, and parses filled |
| H2.9-T6 | S-3 over `INSERT { ... $x }` with no declaration | L1 | reported |
| builder corpus | 52 builders, 12 IRIs and 7 literals in every binding they read | L2 | one operation or no parse |
| library corpus | `Payload`, `Rows`, `registry_text` with the same values | L2 | the term read back from a store, or refused |
| witness | `refusal-CompositeBoundarySnapshotNotBuilt.ttl` | L2 | the refusal is witnessed |

## Expected profiles (for re-approval)

None changed. `mise run check:persistence-expected-profiles` reports "expected profiles are current" before and after, and no file under
`ontology/persistence/test/expected-profiles/` or `tools/persistence/tests/fixtures/` (other than the builder goldens, below) was regenerated. The six deleted builders
appear in no expected profile.

The builder goldens (`tools/persistence/tests/fixtures/ir/builder-goldens.json`) are re-recorded once, as data, and are for re-approval. 52 entries remain, six are gone, 48 digests
changed and no version did (D-44).

## Results (run 2026-10-21)

| Command | Result |
|---|---|
| `mise run check:persistence` | 4258 passed, 1 xfailed in 269.69s. "expected profiles are current". Collected cases rose from 4,008 to 4,259, as the section above counts |
| `mise run check:persistence-oxigraph` | 368 passed, 3891 deselected |
| `mise run check:persistence-library` | vectors 91 checks passed, 0 failed. Library 113 passed (75 before, 38 new) |
| `mise run check:persistence-vectors` | 91 checks passed, 0 failed |
| `mise run check:persistence-expected-profiles` | expected profiles are current |
| `mise run check:ontology-catalog` | 1136 passed, 7 skipped, "ontology catalog consistent, 2 known defect(s) reported", run with `ontology/persistence/execution` removed |
| `mise run check:published-decisions` | 6 passed, and the sources check reports 0 failures |
| `mise run check:deny-terms` | 0 finding(s) against 5 entries |
| `mise run check:catalogue` | 19 module(s) and 8 tool package(s) agree with the tree |
| `mise run check:agent-guidance` | 0 problem(s), 9 passed |
| `python -m persistence witness` | 129 of 129 rules witnessed, 0 listed gaps (one more rule than H2.8c, `CompositeBoundarySnapshotNotBuilt`) |

`check:ontology-versioning` is not run, as the brief says (TD-64). The last full run of `check:persistence` before the final edits to `test_expected_profiles` and
`test_templatecheck` had seven failures, all mine (a replacement that made `endswith(".mustache")` into `endswith("")` in two tests, three composite stems that no longer exist, a
stale S-3 allowance for four deleted builders, and one scenario naming a deleted builder), and all fixed before the run above.

## Probes

| Probe | Result |
|---|---|
| the new refusal made unreachable (kind renamed, concurrency test never true) | H2.9-T2, T4 and `test_h2_6d_t19` fail, and the witness check reports 128 of 129 with one unlisted gap. Restored |
| `fill_slots` replaced by a sequential `str.replace` per slot | 20 tests fail (H2.9-T4d and the 19 cases of the marker-in-a-value corpus). Restored |
| S-3 given no declared parameters | 3 tests fail (the real-operation corpus finds every `$name` unbound). Restored |
| `import chevron` added to `cli.py` | `test_no_module_imports_chevron` fails. Restored |
| a witness fixture with `dal:metaShards 5` (shard 47, where the canonical context has 17) added under `tests/witnesses/`, then removed | `test_builder_versions.py` 56 passed, so a fixture cannot move a golden (H2.9-T1 shows the converse, that none is read) |

## Store behaviour

Nothing new about a triple store was found, so `triple-store-discovery.md` has one edited sentence (TSD-34's list of guards, the harness is gone) and no new entry.

## What remains

- The `hygiene` command still prints "templates:" (D-47).
- Snapshots (`dal:SnapshotPerRevision`) are still not built (TD-46, H2.10).
- H2.11a migrates the Persistence README, which this slice edited only where a sentence was false, as the brief says.
- A one-time re-baseline of the goldens is a judgement for the maintainer (D-44).

## One command

```
mise run check:persistence
mise run check:persistence-oxigraph
mise run check:persistence-library
mise run check:published-decisions
```
