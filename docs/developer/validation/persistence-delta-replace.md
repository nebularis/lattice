<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Packs: writing only what changed, as a persistence mode

**Unit:** `persistence-delta-replace` ([plan](../plans/persistence-delta-replace.md), [status](../status/persistence-delta-replace.md))
**Branch:** `claude/persistence-delta-replace`, off `claude/persistence-linear-replace`

## DR-1: the vocabulary, the compiler, the README

**For the maintainer:** re-approve the expected profiles listed below, accept or change the ADR-A123 addendum of 2026-11-02, and read §5.6.12 of the Persistence README, which is the narrative and the diagrams asked for on 2026-11-02.

### Invariant

A replace under `dal:ChangedTriples` leaves the aggregate in the state a whole-state replace with the same next state leaves, on every engine, without reading the aggregate, and writes nothing when its guard fails or its claim exists. The request carries the change alone, and its digest is over that change. A delta is refused wherever no version-row guard makes it safe (ADR-A123 addendum of 2026-11-02, decisions 1 to 5. ADR-A132 for the caller's side, which DR-2 builds).

### What changed

- `ontology/persistence/README.md`: §6 `dal:ReplaceEncoding`, `dal:replaceEncoding`, `dal:ChangedTriples`, `dal:WholeState`, `dal:DeltaReplace`, §7 the write-discipline shape, the class diagram, and the narrative: §5.3, §5.4, §5.6.2, §5.6.4, §5.6.10, a new §5.6.12 with four diagrams and the cost table, §5.8.1, §5.9, §5.10, §5.13.3 to §5.13.5, §5.13.8, §5.14, the release note. Spec and shapes regenerated.
- `tools/persistence/src/persistence/`: `builders.py` (ten delta builders), `contract.py` (`DeltaReplace`, versions, the digest without a payload part), `ir_render.py` (a payload slot in a `DELETE`), `operations.py` (`replace_encoding`, the selection), `model.py` and `resolver.py` (the dimension), `validator.py` (two refusals, one warning, and `ReplaceFormNotApplicable` for a delta family), `compiler.py`, `templatecheck.py`.
- `packages/persistence/python/src/lattice_persistence/contract.py`: `OperationKind.DELTA_REPLACE`, and `DigestContract.parts` omits the payload part of a change-only digest. The Java library follows in DR-2.
- `ontology/persistence/examples/replace-encoding.ttl`, `replace-form-rows.ttl` (its families declare `dal:WholeState`), the witnesses under `tools/persistence/tests/witnesses`, the expected profiles, the builder goldens, the caller library fixtures.
- `contracts/config-studio/persistence-profile.ttl`: six profiles pinned to `dal:WholeState` until DR-3.
- `benchmark/persistence-replace-forms`: the delta form rendered from the builders.
- `tools/persistence/README.md`, `docs/architecture/decisions/ADR-A123-typed-operation-ir.md`, TD-42, TD-136, the sketch, the plan, the status record, `docs/developer/INDEX.md`.

### Tests

`tools/persistence/tests/test_delta_replace.py`. Level L1 unless said. Every test is positive unless said.

| ID | Given / When / Then | Invariant | Pass criterion |
|---|---|---|---|
| DR1-T1 | the builders / listed / ten delta builders, one per receipt model of each family and per guard | decision 2 | the set equals the expected ten |
| DR1-T2 | each delta builder / built, checked, rendered / no sweep, no `UNION`, the retract slot in the `DELETE`, the assert slot in the `INSERT`, no `payloadTriples`, kind `DeltaReplace`, payload parameter `assertTriples`, digest parts kind, target, expected, add, del | decisions 2 to 4 | every assertion holds for every builder |
| DR1-T3 | `replace-encoding.ttl`, the baseline and the composite example / compiled / Ticket and Draft get the delta, Snapshot the rows form, the baseline and the project the delta, and a provided family resolves to whole state | decisions 1 and 5 | the template ids are as stated |
| DR1-T4 to T6 (negative) | the three witnesses / compiled / `ReplaceEncodingUnknown`, `ChangedTriplesNeedsOptimistic` refused, `ReplaceEncodingNotApplicable` warned | decision 1 | the diagnostic is raised or recorded by name |
| DR1-T7 | `dal:replaceForm` on a delta family and on a whole-state family / compiled / warned on the first, not the second | decision 5 | `ReplaceFormNotApplicable` on Ticket alone |
| DR1-T8 (L4, every engine) | the store of `test_patch_log` / the delta replace, both families, each receipt, both guards / the aggregate is the old state less the retracted plus the asserted, the bystander untouched, the row at seq 2, the claim, under a patch log the add and del graphs hold the delta, and the graph equals what the whole replace leaves | the invariant | state equality on rdflib, Oxigraph and Jena |
| DR1-T9 (L4, negative) | the row at seq 2 / a delta expecting seq 1 / nothing changes | the invariant | every graph unchanged |
| DR1-T10 (L4) | one request / run twice / the second changes nothing | the invariant | every graph unchanged after the second |
| DR1-T11 (L4) | a composite aggregate / the member's owning edge and triples retracted / the member is gone, the root's other triples and the bystander stay | the invariant | state equality |
| DR1-T12 (L4) | both slots empty / run / the row moves and a receipt is written | STD-309 is the caller's | row at seq 2 |
| DR1-T13 | the composite example / compiled / `payload-check` is still generated | decision 3 | the operation is present |

### One command

```bash
mise run check:persistence
```

Then, before the merge, `mise run check:persistence-conformance`.

### Artefacts to inspect

The expected profiles that changed, listed under Results. `ontology/persistence/README.md` §5.6.12. `tools/persistence/tests/witnesses/replace-encoding-whole-state-*.ttl`. The rendered delta builders, `mise run build:persistence-execution` and `ontology/persistence/execution/replace-encoding/`.

### Deliberate non-coverage

The caller libraries' checks and vectors, DR-2. The studio's writer, DR-3. A merge model for a delta under no guard, and a repair operation that heals drift, neither planned.

### Results

Run 2026-11-02 on this laptop (macOS, Python 3.14, rdflib, pyoxigraph with snapshot updates, Jena ARQ in memory), every figure read from the full output.

| Check | Result |
|---|---|
| `mise run check:persistence` | 4,721 passed, exit 0, 97 s |
| `mise run check:persistence-conformance`, rdflib, Oxigraph and Jena | 5,577 passed, 16 skipped (the rows tests on rdflib, by name), exit 0, 152 s |
| `test_delta_replace.py` alone on the three engines | 149 passed |
| `mise run check:persistence-expected-profiles` | 14 files current |
| builder goldens | 72 builders current |
| literate extraction `--check` | 5 artefacts consistent |
| the Python caller library | 119 passed |
| `benchmark/persistence-replace-forms` tests, and the quick run | 43 passed, and the quick run exit 0, with the delta form right in both families on rdflib and Oxigraph at M = 100, 300 and 1,000 and flat in M, 0.1 to 0.2 ms on Oxigraph and about 18 ms on rdflib |
| `mise run hooks:run` over the 86 staged files | 11 checks ok |
| the seven new or changed mermaid diagrams | rendered with mermaid 11.4.1 |

**Expected profiles that changed, for re-approval.** All thirteen existing files gain a `replaceEncoding` resolved dimension with no value, as `replaceForm` did, and eight of them change their replace to the delta: `baseline-single-class`, `baseline-single-class.caller-named`, `composite-project-ownership`, `epoch-dataset-level-guard`, `value-based-cas`, `claim-scheme-dual-rotation`, `uniqueness-merge-policy` and `uniqueness-quarantine-policy`. One is new, `replace-encoding`.

**Not run.** The Java caller library, which does not know the kind until DR-2, and the JVM benchmark.

**Deviations and findings.** The whole-state builders needed fixtures of their own once the default moved, so `replace-form-rows.ttl` and its composite witnesses declare `dal:WholeState` and six witnesses `replace-encoding-whole-state-*` cover the rest. The existing tests of the sweeping composite replace declare `dal:WholeState` through a `conftest` helper. The caller library's fixtures of the whole-state replace are two new files, `baseline-whole-state` and `composite-whole-state`, since the baseline and composite fixtures now hold the delta. The composite-cost benchmark's patch-log text had carried two unfilled slots since H2.6d, which is fixed, and its memory-capped test fails on macOS, where `RLIMIT_AS` cannot be set, before and after this slice. The payload-slot-in-`DELETE` refusal case of `test_ir.py` is removed, since the checker now accepts it by design. The subagent's report was read in full and every count above was re-run or re-read here.

## DR-2: the callers, the conformance run, the obligations as standards

**For the maintainer:** the seven caller obligations become standards for ratification, and both caller libraries gain the delta checks.

### Invariant

A caller library refuses a delta that cannot be right, overlapping or empty slots, and, given the next state, a delta that does not lead from the state read to that state or a next state outside the bound, before anything is sent. Both libraries digest a delta replace identically and as the vectors say (ADR-A132 decisions 2 and 4, ADR-A123 addendum of 2026-11-02 decisions 3 and 4).

### Tests

`packages/persistence/python/tests/test_delta_encoding.py` and the Java `DeltaEncodingTest`, level L3. Positive unless said.

| ID | Given / When / Then | Invariant | Pass criterion |
|---|---|---|---|
| DR2-T1 | the `replace-encoding` fixture / read / the ticket's replace is `DeltaReplace`, its digest parts are kind, target, expected, add, del | decision 4 | the parts match, no payload part |
| DR2-T2 (negative) | a delta with a triple in both slots / checked / `DeltaOverlap` | the invariant | the refusal, by code |
| DR2-T3 (negative) | two empty slots / checked / `EmptyDelta` | STD-309 | the refusal, by code |
| DR2-T4 (negative) | a next state, an asserted triple not in it / checked / `AssertOutsideNextState` | decision 3 | the refusal, by code |
| DR2-T5 (negative) | a next state, a retracted triple in it / checked / `RetractInNextState` | decision 3 | the refusal, by code |
| DR2-T6 (negative) | a next state with a subject outside the bound / checked / `PayloadOutsideBound` over the next state | decision 3 | the refusal, by code |
| DR2-T7 | a sound delta with and without the next state / checked / no refusal | the invariant | empty refusals |
| DR2-T8 | the delta vector / digested in Python and in Java / the vector's digest | decision 4 | equal hex |
| DR2-T9 | the whole-state fixtures / the existing contract, check and rows tests / unchanged behaviour | regression | both suites pass |

### One command

```bash
mise run check:persistence-library
```

Then `mise run check:persistence-vectors` and `mise run check:persistence-conformance`.

### Artefacts to inspect

`contracts/persistence/vectors.json`, the `digest-delta-replace` entry. The seven standards of the caller obligations in `docs/developer/standards.md`, numbered when minted, and the closed TD-140.

### Deliberate non-coverage

The studio's writer, DR-3. A check that reads the state from the store, which no library does.

### Results

Run 2026-11-02, every figure read from the full output, and re-run here after the subagent's report.

| Check | Result |
|---|---|
| `mise run check:persistence-library` | exit 0: vectors 94 passed, Python 127 passed, Java 118 tests with 0 failures and 0 errors, summed from the surefire reports |
| `mise run check:persistence` | 4,721 passed, exit 0 |
| `mise run check:persistence-conformance`, by the subagent after its change | 5,577 passed, 16 skipped, exit 0 |
| `mise run build:knowledge`, `mise run check:identifiers` | built, 12 passed |
| `mise run hooks:run` | ok |

**Standards minted, for ratification.** STD-310 to STD-315 for obligations 1 to 6, STD-316 for obligation 8, each pointing at the compiler README's obligations section, with STD-309 as obligation 7. TD-140 is closed by them.

**Not done.** A caller-check vector for `DeltaOverlap` or `EmptyDelta`, since the vector format carries no payload slots for a caller check and extending it is its own change. The two refusals are held by both libraries' tests instead.

**Deviations.** None from the plan. The Java tests of the whole-state replace read the two whole-state fixtures DR-1 added, since the baseline and composite fixtures now hold the delta.
