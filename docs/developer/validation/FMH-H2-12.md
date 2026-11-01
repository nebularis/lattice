<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.12, the rows replace, selected by capability

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.12, planned in [plan §4.20](../plans/formal-methods-track-h.md#420-h212-the-rows-replace-selected-by-capability-planned-2026-11-01) from the [linear replace sketch](../sketches/persistence-linear-named-graph-replace.md), whose questions LR-Q1 to LR-Q4 the maintainer answered on 2026-11-01. Authored and run in autonomous mode on the branch `claude/persistence-linear-replace`, off the studio's branch. Versioning of the ontology is deferred on this branch, and the release note is written under Unreleased (STD-293).

**For the maintainer:** re-approve the thirteen expected profiles (below), accept or change the ADR-A123 addendum of 2026-11-01, and decide when the studio's deployment declares the field (TD-136). **Decided 2026-11-01.** The `replaceForm` node that every profile now carries, resolved by nobody with a candidate count of zero, stays, since the resolved dimension says whose choice a setting was and "nobody's, so by capability" is that answer. The addendum states the refusal of the opt-in against a declared false as its own decision, its fourth, rather than leaving it to the diagnostic. The studio's deployment waits for the delta replace unit, and declares the field in that unit's studio slice.

## Invariant

A replace of an aggregate of M triples by a payload of N fills its template a number of times linear in M + N where the store declares that it applies every deletion before any insertion, and once per sweep solution everywhere else, and the two forms leave the same state, take the same parameters and the same request digest, and differ to a caller in the slot encoding alone. An undeclared store is never assumed to follow the specification. An operator's opt-in is recorded, and one that contradicts a declared capability is refused.

## What changed

- **The IR** (`ir.py`, `ir_render.py`). `PayloadRows(vars, param)`, a `VALUES` of three variables filled from a `Payload` parameter. The checker takes its variables as bound within their branch, holds the parameter to kind `Payload`, refuses two variables, a variable twice, an undeclared parameter and a parameter of another kind, and records the `INSERT` triple made of its variables as the payload's access.
- **The builders** (`builders.py`). `cas-replace-named-graph-rows` with the three receipt models and `cas-replace-composite-property-rows` with its two, each with a dataset-guard variant, ten in all at version 1, in `builder-goldens.json`. The sweep is the first branch of a `UNION`, the payload and under a patch log the delta are rows branches, and an empty branch is last. Create and tombstone do not change.
- **The contract** (`contract.py`, `contract_emit.py`, the library's `contract.py`). `PayloadContract.encoding`, `GroundNTriples` or `TripleRows`, emitted as `dal:payloadEncoding` and read back by both libraries. Parameters, digest parts and accesses are the template form's.
- **The vocabulary** (the Persistence README's section 6 and 7, extracted to `spec/persistence.ttl` and `shapes/constraints.ttl`). `dal:providesSnapshotUpdateSemantics` on `dal:CapabilitySpec`, `dal:ReplaceForm` with `dal:TemplateReplace` and `dal:RowsReplace`, `dal:replaceForm` on `dal:ConcurrencyProfile`, `dal:TripleRows` as a `dal:PayloadEncoding`, and the shapes that close them.
- **The selection** (`capability.py`, `resolver.py`, `model.py`, `operations.py`, `compiler.py`, `validator.py`). The field on `CapabilitySpec`, the dimension `replaceForm` with no default, `rows_replace()` deciding the form, and the diagnostics `ReplaceFormContradictsCapability` (a refusal) and `ReplaceFormNotApplicable` (a warning). `templatecheck` fills rows stand-ins where the contract says rows.
- **The callers.** `Triple.row()`, `Payload.rows()` and `slot_text` in Python, `Triple.row()`, `Payload.rows()` and `Payload.slotText` in Java, each reading the contract's encoding. The studio's writer is unchanged, its profile declares no spec, so it stays on the template form (TD-136).
- **The example** `replace-form-rows.ttl`, three families: one selected by a spec, one by the opt-in, one left on the template form. Its expected profile and the library fixture of the same name.
- **The benchmark** `persistence-replace-forms` renders R2 from the builder instead of deriving it from R0's text.
- **Documents.** The compiler README (the form of the replace, the obligations), the Persistence README (§5.6.2, §5.7, §5.8, the release note), the ADR-A123 addendum, TD-42, TD-136, the sketch, the plan, the status record and the index.

## Expected profiles that changed (for re-approval)

| File | Change |
|---|---|
| `replace-form-rows.expected.ttl` | new. Invoice and Note take the rows replace, Memo the template replace |
| the twelve existing files | each gains one `dal:ResolvedDimension` for `replaceForm`, resolved from no candidate with no value, as every dimension without a declaration already appears. No operation, contract or diagnostic changes |

## Tests

`test_rows_replace.py`, test IDs H2.12-Tn, and `test_rows_encoding.py` in the Python library (H2.12-Ln). The Java library's `RowsEncodingTest`.

| ID | Checks | Level |
|---|---|---|
| T1 | ten rows builders exist, one per receipt model and guard of each family | L1 |
| T2 | each renders the payload as rows, the sweep first and an empty branch last, leaves no slot in a template, declares `TripleRows`, version 1, and the template form's parameters, digest, kind and accesses, with the rows triple recorded as the payload's access | L1 |
| T3 | the checker refuses two variables, a variable twice, an undeclared parameter and a parameter that is not a payload | L1, negative |
| T4 | on each engine where the form is safe, both families, both guards, each receipt model: the rows replace leaves what the template replace leaves from the same state, and a composite's bystander is untouched | L4 |
| T5 | a lost race and a retry write nothing | L4, negative |
| T6 | the four empty cases of the sketch's §5.3 leave what the template form leaves and move the row | L4 |
| T7 | `compile` selects the rows form by the spec (Invoice), by the opt-in (Note) and the template form otherwise (Memo) | L3 |
| T8 | a spec that declares false, and `dal:TemplateReplace` against a spec that declares true, keep the template form | L3 |
| T9 | `dal:RowsReplace` against a declared false is refused | L3, negative |
| T10 | a form on a family with no sweeping replace is warned and recorded | L3 |
| T11 | a composite family takes the rows form under a deployment-wide spec | L3 |
| T12 | the template check parses every operation of the example with rows stand-ins | L3 |
| L1 to L6 | a row holds the triple's terms, rows are sorted and unique, an empty payload is an empty block, the template contract gives triples and a rows contract gives rows from `slot_text`, the digest is equal under both encodings, event rows and a bare string | L1 |

T4 to T6 skip on rdflib by name, since the form is never selected for a store that applies each solution in turn (TSD-01), and on a pyoxigraph before 0.5.12.

## One command

```bash
mise run check:persistence
```

Then, before the merge, the conformance run and the two library suites:

```bash
mise run check:persistence-conformance
```

```bash
mise exec -- python -m pytest packages/persistence/python/tests -q
```

```bash
mise run check:persistence-library-java
```

## Results

Run 2026-11-01 on an Apple arm64 laptop, Python 3.14.7, rdflib 7.6.0, pyoxigraph 0.5.13, Jena ARQ 5.1.0 in memory, Java 25.

| Command | Result |
|---|---|
| `mise run check:persistence-conformance` (rdflib, Oxigraph, Jena, the whole suite) | 5105 passed, 16 skipped, 0 failed, in 149 s. The 16 skips are T4, T5 and T6 on rdflib, by name |
| `mise run check:persistence-expected-profiles` | the thirteen files are current |
| `mise exec -- python tools/persistence/tests/builder_goldens.py --check` | 62 builders recorded and current |
| `mise exec -- python -m pytest packages/persistence/python/tests -q` | 119 passed |
| `mise run check:persistence-library-java` | 110 passed, 0 failures, from the surefire reports (run by the mechanical subagent, counts read from the report files since the task runs Maven quietly) |
| `mise exec -- python -m pytest benchmark/persistence-replace-forms -q` and `REPLACE_FORMS_QUICK=1 REPLACE_FORMS_MAX_R0=300 mise run check:persistence-replace-forms` | 35 passed, and the quick run exited 0 with the generated rows form right in both families on Oxigraph at 100 and 300, and in the edge cases E1 to E5. The full run and the JVM run were not repeated for this slice |
| `mise exec -- python tools/literate_extract.py ontology/persistence/README.md --layer persistence --root . --check` | 5 extracted artefacts consistent with the README |
| `mise run hooks:run` over the staged change | 11 checks, all ok |
| `mise run build:knowledge`, `mise run check:identifiers` | built, 12 passed |

On the way, the first full run of `check:persistence` found 69 failures, all of one kind: a new builder must be generated by some shipped example or witness, have a witness per diagnostic, and be registered with the template check's allowance of branch-bound `INSERT` variables. Seven witnesses, two refusal witnesses, one warning witness and the allowances closed them. The witness coverage report then read 147 of 147 rules witnessed.

**Index.** `find` answered weakly for the caller obligations and for an operator's opt-in, which the new STD-299 and MEC-100 now carry, and for a named graph still listed after it is emptied, recorded as a gap on TSD-50.

## Deliberate non-coverage

- R1′, the two-operation form, which LR-Q5 places with H5 for a store that applies each solution in turn but makes a request one transaction.
- The studio's writer, which fills template slots by splicing quads and derives a delta write from the template form's shape. It is the studio's to move, and until its deployment declares the field it stays on the template form (TD-136).
- RDF4J, where no composite operation is right today for a reason of its own (TSD-Q36), and which the conformance run does not cover.
- A conformance probe of the new field beyond P1, which is already its probe (`test_store_probes.py`).
