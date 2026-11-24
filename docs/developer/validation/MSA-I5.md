<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I5, the prover spike

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I5
**Brief:** [machine S brief of 2026-11-19, the multi-store half](../notes/machine-s-brief-2026-11-19-multi-store.md), sections 4.3 and 7, with the [handover of 2026-11-23](../notes/machine-s-handover-2026-11-23.md), sections 3 and 4, and the [brief of 2026-11-18](../notes/machine-s-brief-2026-11-18.md), section 3.
**Decisions:** the [sketch](../sketches/multi-store-architecture.md)'s D7 and D8, sections 4.6, 4.14 and 4.15. The plan's answers of 2026-11-18 on the order of the guards, who advances a sequence and what the patch log holds. [ADR-A-FM2](../../architecture/decisions/ADR-A-FM2-formal-methods-theory-home.md) and its addendum of 2026-11-18. [ADR-A124](../../architecture/decisions/ADR-A124-benchmark-root.md) for the replay task.
**Machine:** machine S, Windows, Isabelle2025-2 through `FMX_ISABELLE`, its bundled JDK 21.0.9 and Scala 3.3.4, Python 3.14.7 and pyoxigraph 0.5.13 from the worktree's `.venv` through mise. **Placement:** T0, public. Proof tooling and a spike, nothing domain-specific.
**Status:** built 2026-11-23, not verified.

## Invariant

The neutral IR of the paper lowering is an Isabelle datatype with one `exec`, and the four commands of that lowering are values of it. Every law the sketch names of `exec` is a theorem the gate holds, and the session imports `LatticeShared` and never the ledger's session. The interpreter Isabelle exports to Scala is used as generated, and it replays the histories of the persistence behaviour tests of the four operations to the same state as the RDF realisation on Oxigraph after every command, within ten times its time.

## What changed

- `spikes/multi-store-model/`, new. `ROOT` declares `session MultiStoreModel = LatticeBase +`, `sessions LatticeShared`, `quick_and_dirty = false`, `timeout = 120`, and four theories.
  - `IR.thy`: the datatypes, the evaluation of expressions and guards, the actions, `run` and `exec`. It imports `LatticeShared.Positions` for `position`.
  - `Commands.thy`: `create_if_absent`, `delta_replace`, `append_event` and `key_claim_write`, each as the paper lowering's section 3 writes it, with the store computing the successor in the replace as in the append.
  - `Laws.thy`: 11 laws between gate markers, MM1 to MM11, and the lemmas they rest on.
  - `Export.thy`: `exec_literal` and `replay_literal` at string atoms, and `export_code open ... in Scala (case_insensitive)`, with `HOL-Library.Code_Target_Numeral`.
  - `claims/MM1.json` to `claims/MM11.json`, written with `gate.py`'s own digest function.
  - `replay/histories.py`: 17 histories transcribed from three test modules, their replay on Oxigraph, and the reading of a store back into the model's resources.
  - `replay/Replay.scala`: the driver that parses the histories, builds the model's values and calls the generated code.
  - `README.md`: `exec`, the four commands and each law in prose, for the second formalisation.
- `tools/proofs/check.py`: `SPIKE_SESSIONS = ("multi-store-model",)`. A spike named on the command line is built and gated from its directory under the spikes root, found through the catalogue reader, with `-d` given as a relative POSIX path. A spike is never built by default.
- `tools/proofs/multi_store_replay.py`, new: the replay task's script. It builds and gates the session through `check.py`, exports the Scala, compiles it with the driver, runs the driver's check mode, runs the same histories on Oxigraph, compares, and times both.
- `mise.toml`: `check:proofs`'s description names the spike. `check:multi-store-model-replay`, new, depends on `bootstrap:persistence` and `bootstrap:testing-oxigraph`, and runs on demand.
- `tools/proofs/README.md`: a paragraph on a spike's session. `docs/developer/developer-guide.md`: a row for the replay task, and the spike named in `check:proofs`'s row.
- Generated output, the Scala, the classes, the histories file and the logs, is written under `.build/formal/multi-store-model/`, which `.build/formal/*` in `.gitignore` already covers. Nothing generated is tracked.
- `repository-catalogue.md` is unchanged. A spike has no row, and only a tool package under `tools/` with a `pyproject.toml` does. `check:catalogue` agrees.

## The laws

Every law is proved. None resisted to the end. The column on cost says what each took beyond writing it, in builds of the session, since tokens were not counted per law.

| Claim | Theorems | Law | State | What it took |
|---|---|---|---|---|
| MM1 | `applied_exactly_when_every_guard_holds`, `otherwise_the_first_failed_guard_decides` | outcomes are total and disjoint: applied exactly when every guard holds, and otherwise the outcome of the first guard that fails | proved | one rebuild. `simp` would not use an iff as a premise, so the fact is derived first |
| MM2 | `a_command_not_applied_changes_nothing` | a command not applied leaves the state as it was | proved | first build |
| MM3 | `every_value_is_read_before_any_write` | an applied command writes its effects evaluated in the state before it | proved | first build |
| MM4 | `an_asserted_fact_is_present_whatever_is_retracted` | retract, then assert: an asserted fact is present whatever is retracted, unless the command puts that resource whole | proved | the session's 120 s timeout. Bisected by commenting sections out, the loop was `force` and `auto` over set membership in the concretised effects, replaced by explicit steps |
| MM5 | `a_resend_is_answered_duplicate_before_any_conflict`, `an_append_sent_again_is_answered_duplicate`, `a_claim_written_again_by_its_owner_changes_nothing` | a resend changes nothing, and is answered before any conflict | proved | one rebuild. `simp` turns `x ~= None` into an existential, so the lemma splits on the option |
| MM6 | `a_claim_held_by_another_is_refused_and_changes_nothing`, `an_applied_claim_names_its_owner` | a claim has one owner | proved | first build |
| MM7 | `a_tombstoned_row_refuses_a_replace_and_changes_nothing` | a tombstoned row refuses a replace | proved | first build |
| MM8 | `a_create_starts_the_sequence_at_one`, `a_replace_moves_the_sequence_to_its_successor`, `an_append_moves_the_sequence_to_its_successor` | the store computes a sequence's successor | proved | first build, once a lemma for the fields a set of fields leaves was proved, which took one rebuild |
| MM9 | `the_patch_log_holds_the_delta_as_requested` | the patch log holds the delta as requested | proved | first build |
| MM10 | `every_receipt_stays_at_or_below_its_rows_sequence`, `a_receipt_once_written_is_never_replaced`, `the_empty_state_has_its_receipts_below` | one receipt for each target, epoch and sequence: every receipt stays at or below its row's sequence, and none is ever replaced | proved | one rebuild. `blast` could not pick the case of the four commands, so the proof splits them |
| MM11 | `from_nothing_a_rows_receipts_are_its_positions_one_to_its_sequence` | no gap: from the empty state, a row's receipts are at exactly the positions 1 to its sequence | proved | three rebuilds. `OF` left a premise of each local fact as a goal with the set of written resources still schematic, which `simp_all` then closed with the universal set. Naming the set with `where` fixed it |

The session builds in 12 s on machine S (`Finished MultiStoreModel (0:00:12 elapsed time)`). The spike took about 20 builds of the session, each failing build stopping on the proofs the table names, four of them to bisect MM4's timeout, and two more for the export.

## The export

- **Used as generated.** `isabelle export` writes `multi_store_model.scala`, 44,813 bytes. `isabelle scalac` compiles it with the driver unedited. It gives three warnings, all in generated code: two unreachable cases of `equal_bool`, and `image` with no case for a cofinite set, which no command writes.
- **What it took.** Three things, none an edit of generated code.
  - The first export wrote natural numbers in unary, since the session's theories did not import `Code_Target_Numeral`, which the prelude's heap holds but only a theory's imports bring in. `Export.thy` imports it.
  - `case_insensitive` renames classes whose names differ only in case, as the spike under `spikes/isabelle-layers` found for macOS. Windows needs it too. So `EpochMismatch` is `Epochmismatch` and the datatype `val` is `vala`, and the driver names each reason by the theory's name.
  - `isabelle scala` passes its compiler options ahead of the program's arguments, so the driver reads its arguments from the mode on.

## The replay

**Which tests.** The sketch's criterion names "the existing behaviour tests' histories". STD-153 calls a test that runs generated SPARQL on Oxigraph a behaviour test, and the four operations are the paper lowering's four builders, so the histories are those of the persistence tests that run those builders. They are transcribed, each naming its test.

| History | Test | Commands and the outcome the model returned |
|---|---|---|
| H01, H02 | `test_patch_log.py`, `test_h2_6d_t1`, `t2` | a replace, Applied |
| H03 | `test_h2_6d_t4` | a create, Applied |
| H04 | `test_h2_6d_t5`, the create | a create, Applied, then the same, Duplicate |
| H05 | `test_h2_6d_t5`, the replace | a replace, Applied, then the same, Duplicate |
| H06 | `test_h2_6d_t6`, the create | a create on an existing row, Conflict Exists |
| H07 | `test_h2_6d_t6`, the replace | a replace at a stale sequence, Conflict Stale |
| H08 | `test_h2_6d_t9` | a replace with an empty delta, Applied |
| H09 | `test_h2_6d_t10`, without its tombstone | a create, then a replace, both Applied |
| H10 to H14 | `test_append_events.py`, `test_h2_6b_t1`, `t3`, `t5`, `t7`, `t8` | appends, Applied, and a resend, Duplicate |
| H15 | `test_h2_6b_t8`, the dataset epoch moved | an append, Refused EpochMismatch |
| H16, H17 | `test_key_claims_and_audits.py`, `test_h2_5_t15`, `t16` | claims, Applied, and one by another owner, Conflict HeldByOther |

**How each side runs.** On the RDF side, each builder is rendered once with its guards on, from one context for all four, and each command fills its request-time slots and runs on `OxigraphStore`, the test-support store the tests use, which binds the parameters into the text. On the model's side, the driver builds each history's seed and its list of clock, parameters and command once, and calls the generated `exec_literal` for the check and `replay_literal` for the timing. Both read their state back into one line for each resource, and the script compares the lines after every command. Each history is seeded outside the clock on both sides, and on the RDF side the slot filling and the binding are inside it, as they are part of each request.

**Result.** The state of the model equals Oxigraph's after each of the 25 commands, and each outcome is the one the test states. Over 200 rounds of the 17 histories, from the run of 2026-11-23 in full below:

| Side | Engine, as its run reports it | First round | Later rounds, median | Later rounds, mean |
|---|---|---|---|---|
| the exported interpreter | Scala, `scala3-library_3-3.3.4.jar` with library 2.13.14, on Java 21.0.9, OpenJDK 64-Bit Server VM | 23.976 ms | 0.882 ms | 1.011 ms |
| the RDF realisation | Oxigraph through pyoxigraph 0.5.13, on Python 3.14.7 (CPython) | 4.400 ms | 3.991 ms | 4.172 ms |

The interpreter takes 5.449 times the RDF realisation's time on the first round, while the JVM loads and compiles, and 0.221 times on the median of the later rounds. **The criterion is met on both.** These are one machine's figures for a spike, and not a benchmark's result.

## Tests

| ID | Given, when, then | Level | Positive or negative | Pass criterion |
|---|---|---|---|---|
| MSAI5-01 | the session built by `check:proofs -- multi-store-model` | L1 | positive | `Finished MultiStoreModel`, 11 claims passed, `Assumption audit: clean`, `GATE: pass` |
| MSAI5-02 | `check:proofs` with no argument | L1 | positive | the prelude, `shared`, `eligibility` and `ledger` gated with 10, 33 and 73 claims passed, and the spike not built |
| MSAI5-03 | the delta replace's delete patch changed to hold the asserted facts, the session built | L1 | negative | the build fails, at `replace_effects`, the lemma MM9 and MM10 rest on |
| MSAI5-04 | the generated Scala compiled with the driver | L0 | positive | `isabelle scalac` exits 0, with the generated file unedited |
| MSAI5-05 | the 17 histories replayed through the interpreter and on Oxigraph | L4 | positive | `CHECK: pass`, the state equal after each of the 25 commands and each outcome the test's |
| MSAI5-06 | a copy of the generated Scala whose successor adds two, compiled and replayed | L4 | negative | the comparison finds 13 of 25 steps differ |
| MSAI5-07 | both sides timed over 200 rounds | L7 | positive | each side's version printed from its own run, and the interpreter within ten times the RDF realisation's time |
| MSAI5-08 | the catalogue, the formal artefacts and the identifiers | L0 | positive | `check:catalogue`, `check:formal-freshness` and `check:identifiers` pass |

## One command

```bash
mise run check:multi-store-model-replay
```

It needs Isabelle as `check:proofs` does, found through `FMX_ISABELLE` or the install of `bootstrap:formal-native-isabelle`. A pass prints `GATE: pass` for `multi-store-model`, `CHECK: pass, the model's state equals Oxigraph's after every command, and every outcome is the one the test states`, each engine's version, the two times, and `within ten times the RDF realisation's time: first round yes, later rounds yes`. It fails on a difference in state or outcome, never on time. `mise run check:proofs -- multi-store-model` builds and gates the session alone.

## What was run, in full

- `mise run check:proofs -- multi-store-model`, first run: exit 1, `Inner syntax error`, since `o` is HOL's composition and was a variable's name. Every later build of the session went through the driver as `check.py` calls it, until the laws were proved.
- `mise run check:multi-store-model-replay`, first run: exit 1. `bootstrap:persistence` and `bootstrap:testing-oxigraph` failed with `HTTP error 403` on `packaging-26.4` in pip's isolated build environment. Second run, with `PIP_CONSTRAINT` set as the machine's rules say: the same. Third run, with `PIP_BUILD_CONSTRAINT` set to the same file of pins: the bootstraps passed, and the script ended `CHECK: fail` on two outcome names, `Refused Epochmismatch` and `Conflict Heldbyother`, the renamed classes. Every state was already equal. The driver now names each reason by the theory's name.
- `mise run check:multi-store-model-replay`, the run reported above: exit 0. `GATE: pass` for `base` (nothing to gate), `shared` and `multi-store-model`. `isabelle export: exit 0`, 44,813 bytes. `isabelle scalac: exit 0`, `3 warnings found`. `Scala check: exit 0`. `CHECK: pass, the model's state equals Oxigraph's after every command, and every outcome is the one the test states`. `Scala run reports: scala scala3-library_3-3.3.4.jar library 2.13.14`, `java 21.0.9 OpenJDK 64-Bit Server VM`, `histories 17 commands 25 rounds 200`. `Oxigraph run reports: pyoxigraph 0.5.13, Python 3.14.7 (CPython)`. `exported interpreter (Scala): first round 23.976 ms, later rounds mean 1.011 ms, median 0.882 ms, min 0.699 ms, over 200 rounds`. `RDF realisation (Oxigraph): first round 4.400 ms, later rounds mean 4.172 ms, median 3.991 ms, min 3.711 ms, over 200 rounds`. `ratio, interpreter over RDF: first round 5.449, later rounds (median) 0.221`. `within ten times the RDF realisation's time: first round yes, later rounds yes`. `Finished in 210.69s`. Two earlier passing runs gave the medians 0.909 ms against 3.952 ms and 0.878 ms against 3.942 ms.
- The probe of MSAI5-06, a script outside the tree that compiled a changed copy of the generated Scala into its own directory and compared: `exit 0` for both Isabelle steps, `steps that differ: 13 of 25`. Its first attempt waited on standard input for minutes and was stopped, and its second failed to compile on a class the driver named that the Scala 3 library lacks. The script now gives the tools no input.
- The probe of MSAI5-03, a script outside the tree that kept the file's bytes: `sha256 before 48a443ad57453439`, `probe build exit: 1`, `MultiStoreModel FAILED`, at command `by` (line 399 of `Laws.thy`), `restored: True sha256 after 48a443ad57453439`.
- `mise run check:proofs -- multi-store-model` after the probe: exit 0. `Running MultiStoreModel ...`, `Finished MultiStoreModel (0:00:12 elapsed time)`, 21 rows `Proof passed`, 10 for `shared` and 11 for the spike, `Assumption audit: clean, no sorry/oops/admit/oracle/by-eval found`, `GATE: pass`.
- `mise run check:proofs`: exit 0. `Finished Eligibility (0:00:04 elapsed time)`, `Finished Ledger (0:00:22 elapsed time)`, 116 rows passed, 10, 33 and 73, `GATE: pass` for each, and no row for the spike.
- `mise run check:catalogue`: exit 0, `repository catalogue: 22 module(s) and 19 tool package(s) agree with the tree. Bypass scan: 13 known file(s)`.
- `mise run check:formal-freshness`: exit 0, `3 formal-methods artefact(s) consistent with their literate READMEs`.
- `mise run check:identifiers`: exit 0, `identifier check passed: 2438 identifiers mentioned in 1045 files, 0 unresolved, 0 defined twice`.
- `mise run check:portability`: exit 1, `portability: 10 problem(s)`. Each names a file this slice did not touch: two under `benchmark/ledger-credit-kinds-jvm/`, `tools/bootstrap_erlang.py`, `tools/test_asset_class.py`, `tools/test_hooks.py`, `tools/test_v_rig.py` and four under `tools/v_rig/tests/`. None names `tools/proofs/check.py` or `tools/proofs/multi_store_replay.py`. They are the debt TD-154 names.
- `mise exec -- python tools/writing_rules.py` on this pack, the spike's README, `tools/proofs/README.md` and `docs/developer/developer-guide.md`: first `writing rules: 2 failure(s), 28 warning(s)`, a semicolon in each of two rows of the developer guide this slice had not written, both rewritten. Then exit 0, `writing rules: 0 failure(s), 28 warning(s)`. Each warning is a hard-wrapped line of `tools/proofs/README.md` or the developer guide in a paragraph this slice did not change, and none is in the pack or the spike's README.

## Deliberate non-coverage

- **Histories left out.** The tombstone of `test_h2_6d_t10`, since a tombstone is not one of the four operations. `test_h2_6b_t6`, an empty rows slot, which Oxigraph answers with no solution and the model with an applied append, as the README says, and which the caller refuses before sending. `test_h2_6b_t9`, a missing parameter, since the model does not check a parameter's datatype. The composite family, the no-receipt variants and the dataset-guard variants of the create and the replace, since the paper lowering read the four builders named.
- **The append's histories run on the dataset-guard variant.** Most of `test_append_events.py` runs `append-event`. The histories run `append-event-dataset-guard`, the builder the paper lowering read, with the dataset's epoch seeded at 3, the epoch the tests' parameters name.
- **One context.** The four builders run with one meta graph and one context, where the tests use two. A graph's name is a layout, and no guard reads it. A seeded row has no `rdf:type`, which no guard reads either.
- **The Rocq formalisation** is built off machine S on Rocq 9.3.0, from the README's prose. No Rocq is on machine S.
- **Trace validation against the protocol models** is MSA-I6's, now that the interpreter is exported.
- **Concurrency.** `exec` is one atomic step, and the protocol models check interleavings.

## Questions for the maintainer

- **The model's append writes when its rows slot is empty, and Oxigraph does not.** The options are (a) leave it to the caller's check, as today, (b) add a guard that a list of facts is not empty, a construct beyond the paper lowering's, or (c) make an empty append a refusal in the IR with its own reason. We lean to (a) for the spike, since the lowering is not changed by it, and say so in the README.
- **A field is read only from a resource named by a parameter or a constant.** This keeps value expressions and resource expressions apart. A later operation that reads a field of a resource named by a computed key, for example a receipt's, needs the two defined together. Is that wanted now, or when an operation needs it?
- **The replay task's place.** It measures and runs on demand, as a benchmark does, but builds a spike's proofs. It lives under `tools/proofs/` beside `check.py`. Should it move under `benchmark/`?

## Doc delta

- `spikes/multi-store-model/README.md`, new, with `exec`, the commands and each law in prose.
- `tools/proofs/README.md`: a paragraph on a spike's session.
- `docs/developer/developer-guide.md`: the replay task's row, and the spike in `check:proofs`'s row. Two rows lose a semicolon each, for the writing rules.
- No ontology README changed, so no release note and no version.

## Index report

- **Asked.** `find isabelle proof session claim record check proofs` answered with CAP-32, `check.py`, at 0.79. `find behaviour tests histories replay persistence conformance oxigraph` answered with STD-153 at 0.75, which says what a behaviour test is.
- **Gap recorded.** Against MSA-I5, at the paper lowering's line 17: the behaviour tests whose histories the spike replays are the persistence tests that run the four builders on Oxigraph, which no entry says. A `defines` or `reads` edge from the investigation to the tests it replays would carry it.
- **`misses --near`.** It lists eight misses and eleven near answers, none from this slice's questions.
