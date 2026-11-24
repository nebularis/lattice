<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I6, the protocol models

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I6, with TLA+ and TLC as the maintainer decided on 2026-11-17
**Machine:** machine S, Windows, TLA+ tools 1.7.4 (TLC 2.19) on Java 25, the jar installed locally and named to the runs by `TLA2TOOLS_JAR`. **Placement:** T0, public. Protocol models, nothing domain-specific.
**Status:** built 2026-11-18, not verified, in part. What is left is listed under deliberate non-coverage.

## Scope

- `tools/models/multi-store-protocols/`, five TLA+ modules and twenty-eight configurations, with a README that states what each models, what it abstracts away and every result.
  - `ModelA_GuardedCas`, FMH-5's model A, a guarded compare-and-set under an atomic store and under a snapshot store with no write-write conflict detection.
  - `X1_SerialisedApply`, one writer per key applying a stream's commands to two stores, with crashes, a zombie that outlives its turn, offsets stored as applied or as received, and a reader of both stores.
  - `X2_EvidenceAcrossStores`, a core reading evidence in another store under the watermark row and the best-known row, with an audit over the recorded read set.
  - `X3_ReceiptRelay`, receipts as the outbox, a relay publishing by one global commit position or by each stream's next sequence number, with late arrival and restarts.
  - `X4_AuthorityCutover`, a family's authority moved from one store to another while writers are live, naively or with the old authority fenced first.
- The models were written with two sub-agents and every configuration was run, its result read and recorded in the README.

## Result in one paragraph

The falsifier, that a row of the catalogue cannot state a guarantee the model keeps, does not fire for the five rows modelled. A single-store transaction keeps no lost update only where the store is atomic or detects write-write conflicts, which is a capability the row has to name. The serialised writer keeps order, at most once in effect and eventual application for up to three incarnations including a zombie, and gives no atomic visibility, as the sketch's revised row says. Storing received offsets breaks eventual application, which is MSAI9-06 reproduced in the model and the fix of MSA-F1 confirmed in it. The watermark read keeps evidence equal to the source as of the decision's position and waits forever when the source stalls. The best-known read never waits, and the audit over its read set flags every decision whose evidence was superseded, and some that were not. Receipts serve as the outbox only with a relay that follows each stream's sequence, since a relay by global commit position skips a late receipt for good. A cutover keeps every acknowledged write only with the old authority fenced before the copy.

## Each row of the catalogue against the models

| Row (sketch §4.2) | Model | Guarantee kept | What it needs |
|---|---|---|---|
| single-store transaction | Model A | no lost update | an atomic request, or write-write conflict detection, named in the capability record |
| outbox | X3 | every committed receipt published, in order within a stream, at least once | a relay that tracks each stream's next sequence number, and an idempotent consumer |
| named saga | none | not modelled | |
| one serialised writer per key | X1 | ordered, at most once in effect, eventually applied, never atomic visibility | a guard in each store and offsets stored as applied (MSA-F1) |
| read as of a position, gated on a watermark | X2 | the evidence is what the source held at the position | a source that advances its watermark, without which the evaluation waits for ever |
| read of the best known, with its read set | X2 | an audit over the read set finds every superseded read | the read set's positions recorded on the decision |
| a change of authority while live (model X4, not a row) | X4 | no acknowledged write lost, none acknowledged by both | the old authority fenced before the copy |

## Commands and results

Each configuration was run from the model directory with `java -XX:+UseParallelGC -cp $TLA2TOOLS_JAR tlc2.TLC -deadlock -config <cfg> <module>.tla`, `-workers auto` where no error was expected and `-workers 1` where a counterexample was. The README's results table has every run's states, distinct states, depth and counterexample. In summary, 28 configurations ran, 13 with no error and 15 violating the property they were built to show violated. No property expected to hold was violated.

| Command | Result |
|---|---|
| `mise exec -- python tools/writing_rules.py tools/models/multi-store-protocols/README.md` | 0 failures |

## Deliberate non-coverage

- **FMH-5's models B, C and D** (the append form, the create race, the key claim) and its capability-record extension. Track H owns FMH-5, which the epic adopts (D5). Model A is built here and FMH-5's board row is unchanged, since most of it is not built.
- **The named saga row.** Not modelled.
- **Isolation probes on PostgreSQL and Fuseki**, which the sketch's §6 asks to ground each model. Not run.
- **Trace validation against the Isabelle model.** It needs MSA-I5's mechanised IR, which waits on the shared types.
- **Scope.** Every result holds for the small constants of its configuration only, two or three writers, streams or commands, positions up to three and at most two crashes.
- **Apalache.** Not used. TLC's explicit search suffices at these sizes.

## Decisions taken

- **Configurations that show a failure are kept beside those that show a guarantee.** A row's guarantee is stated by what holds with its requirement and what breaks without it, so each requirement in the table above has a configuration that removes it.
- **`X1_Unguarded` and the timeouts of X4** were added beyond the brief, to show what the guard and the fence are each worth.

## The runner, the manifest and the wide instances, 2026-11-24

**Brief:** [machine S brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md), section 4.4, "Wider instances, sized to the machine" and "The models run everywhere, and that is a deliverable", and section 7. [Handover of 2026-11-23](../notes/machine-s-handover-2026-11-23.md), sections 3 and 6.
**Machine:** machine S, Windows 11, 16 logical cores, 64 GB installed, of which the runner reads 64,980 MB as physical memory, TLA+ tools 1.7.4 (TLC 2.19) on Java 25.0.2 through mise, the jar named by `TLA2TOOLS_JAR`. Every figure below comes from a run made on its own, with nothing else heavy running beside it, unless the row says otherwise. **Placement:** T0, public. A runner and protocol models, nothing domain-specific.
**Status:** built 2026-11-24, not verified. What MSA-I6 reported on 2026-11-18, above, stands.

This part was begun by one session and finished by another. The first left the runner, the manifest, the wide configurations and a draft of this section uncommitted, with the runner failing to compile and two limit runs still going. The second let both limit runs end, fixed and reviewed the runner, added its test, and measured every configuration again on its own, since most of the first session's runs shared the machine with each other and with other work. The figures here are the second session's.

### Invariant

A configuration fails only where TLC's verdict differs from what the manifest expects. Nothing fails for want of memory or of a tool. A run never holds more heap than a quarter of physical memory, than what is available, or than `LATTICE_MODELS_MAX_HEAP_MB`, and configurations run together never hold more than that between them.

### What changed

- `tools/models/check_tlc.py`, new. The runner, a Python script with the standard library and `mem_check`, every text call given its encoding.
- `tools/models/test_check_tlc.py`, new. 24 tests of the runner's budget, its heap for each run, its plan of what runs and what is skipped, its verdict, its reading of TLC's counts and of the GC log, and the manifest's agreement with the `.cfg` files. They need neither Java nor TLC.
- `tools/models/multi-store-protocols/manifest.toml`, new. One entry for each of the 75 configurations, 50 `base` and 25 `wide`: its module, its `.cfg`, its tier, the verdict expected, and the distinct states, depth, TLC's time, wall time and peak heap measured on machine S, or the limit it reached.
- 25 configurations of the wide tier, new, named for the base configuration and the constant stepped up, for example `X1_AppliedZombie2_K4W3.cfg`. Each differs from its base configuration in its comment and the constant stepped up. No `.tla` module changed.
- `mise.toml`, the task `check:models-multi-store` and the task `check:models-multi-store-runner`, which runs the runner's tests and which the first depends on.
- The models' [README](../../../tools/models/multi-store-protocols/README.md). The Running section's PowerShell lines are replaced by the one command, and the wide tier, its results and what they say are added.

The runner writes TLC's working files under `.build/formal/tlc/multi-store-protocols/<configuration>/`, inside `.build/formal/`, which the existing `.build/formal/*` line of `.gitignore` ignores. It is a `.build/<name>/` directory, so `tools/clean.py` is unchanged.

**What the second session changed in the runner.**

- `heap_mb`'s docstring ended in escaped quotes, `\"\"\"`, so the string ran on into the code after it and the file did not compile. With the quotes unescaped, `py_compile` passes.
- `--heap-mb` gives every selected run that heap, within the budget, so a configuration stopped at the limit or never measured can be run again, and a tier can be measured under one heap. Before, it applied only to a configuration with no peak in the manifest, and a limit run could not be repeated through the runner.
- Physical memory on Windows is read with `GlobalMemoryStatusEx`, 64,980 MB here, the memory Windows can use, in place of `GetPhysicallyInstalledSystemMemory`, 65,536 MB, which reads the installed modules and fails on a virtual machine that reports none.
- The budget, the plan, the verdict and the reading of TLC's counts are functions of their inputs alone, which the tests call. A runner stopped by an interruption stops its TLC process.
- `check:models-multi-store` runs the runner's tests first.

**How the runner sizes a run.** It reads physical memory from the operating system and what is available from `mem_check` (STD-151), each within a Linux cgroup's limit where one is set. The budget is a quarter of physical memory, never above what is available, and `LATTICE_MODELS_MAX_HEAP_MB` lowers it and never raises it. A run gets a heap of twice the manifest's peak and 64 MB more, at least 256 MB, in steps of 32 MB. A configuration expected to find no error runs with every core, divided between `--jobs`, and one expected to violate a property with one worker, so that its counts and trace do not vary.

**`mem_check` and ADR-A125.** `mem_check` is a test-support package under `tools/testing/`. ADR-A125's decision 2 lets tests, checks and benchmarks use one, and `check:models-multi-store` is a check run on demand, so the runner imports it. Where it is missing the runner names the task that installs it, `mise run bootstrap:testing-mem-check`, runs nothing and exits 0, as PRI-79 says of a missing tool. The addendum of 2026-10-21 says a check task that finds one missing "stops and names the task that installs it", which this does, though without failing. That reading is a question below.

**What the runs taught the runner.**

- The peak heap read from the GC log depends on the heap given, so it is not the heap a run needs. `X1_AppliedZombie2` read 111 MB under a heap of 2,048 MB, 232 MB under 288, 231 under 256, 234 under 240 and 218 to 220 under 224. Under 192 and 208 MB TLC printed "Error: Java ran out of memory during liveness checking", and under 224 MB it did so in one run of four and finished in the other three. So the margin is twice the peak and 64 MB, which gives it 288 MB, and a run that runs out of heap is reported as stopped and does not fail.
- TLC writes the standard modules it reads to Java's temporary directory. The first session found three runs started together in one temporary directory reading each other's half-written `Naturals.tla`, one failing with "Fatal errors while parsing TLA+ spec". Each run now has its own temporary directory. The second session did not reproduce the failure, and its four-job run below passed with the directories apart.

### The wide instances

Each configuration of X1 to X4 expected to find no error was stepped up one constant at a time, to at most four commands and, in X1, a window of three. A command is a command of the stream in X1, a position of the source and a decision in X2, a receipt of a stream in X3 and a write of a writer in X4. X3 and X4 have no window, so their second step adds a third stream or a third writer. That reading of the brief is a question below.

The 23 that completed were run in one command, one at a time on 16 workers under `--heap-mb 4096 --max-minutes 30`, with nothing else heavy running. The two that reached the limit were run under `--heap-mb 8192 --max-minutes 30`, each on its own, the first session's run of `X3_PerStreamRestart_N4` and the second session's of `X3_PerStreamRestart_S3`. The first session's run of `X3_PerStreamRestart_S3` shared the machine with its other runs for about a third of its 30 minutes, so the second session ran it again. Depth is TLC's "depth of the complete state graph search", the diameter it found, and for a run stopped at the limit the last level its progress line printed. TLC's time is its "Finished in" figure. Every distinct-state count equals the first session's for the same configuration.

| Configuration | Verdict | Distinct states | Generated | Depth | TLC time | Wall time | Peak heap |
|---|---|---|---|---|---|---|---|
| `X1_Applied_K4W2` | no error | 3,381 | 5,941 | 30 | 00s | 1.5 s | 40 MB |
| `X1_Applied_K4W3` | no error | 5,092 | 9,052 | 32 | 01s | 1.7 s | 47 MB |
| `X1_AppliedZombie2_K4W2` | no error | 174,940 | 791,227 | 50 | 23s | 24.4 s | 724 MB |
| `X1_AppliedZombie2_K4W3` | no error | 279,119 | 1,329,535 | 51 | 40s | 41.2 s | 1,116 MB |
| `X2_Watermark_P4` | no error | 691 | 1,867 | 11 | 00s | 1.6 s | 35 MB |
| `X2_Watermark_P4D4` | no error | 1,555 | 4,459 | 13 | 00s | 1.7 s | 36 MB |
| `X2_BestKnownAudit_P4` | no error | 28,777 | 62,387 | 11 | 01s | 2.1 s | 63 MB |
| `X2_BestKnownAudit_P4D4` | no error | 297,679 | 779,759 | 13 | 13s | 14.0 s | 572 MB |
| `X2_BestKnownStalled_P4` | no error | 28,777 | 62,387 | 11 | 01s | 1.9 s | 63 MB |
| `X2_BestKnownStalled_P4D4` | no error | 297,679 | 779,759 | 13 | 13s | 14.0 s | 567 MB |
| `X3_PerStream_N3` | no error | 23,151 | 56,051 | 20 | 02s | 2.9 s | 88 MB |
| `X3_PerStream_N4` | no error | 424,131 | 1,098,505 | 26 | 51s | 51.6 s | 1,674 MB |
| `X3_PerStream_S3` | no error | 392,848 | 971,581 | 20 | 38s | 39.2 s | 1,324 MB |
| `X3_PerStreamRestart_N3` | no error | 1,454,319 | 2,971,163 | 27 | 02min 07s | 128.4 s | 3,084 MB |
| `X3_PerStreamRestart_N4` | stopped at the limit of 30 minutes under a heap of 8,192 MB, with no error printed by then | 15,204,162 found, 5,178,623 on the queue | 33,918,649 | 27 reached | not printed | 1,800.8 s | 8,128 MB |
| `X3_PerStreamRestart_S3` | stopped at the limit of 30 minutes under a heap of 8,192 MB, with no error printed by then | 24,348,504 found, 8,286,182 on the queue | 47,624,388 | 24 reached | not printed | 1,801.1 s | 8,190 MB |
| `X4_NaiveSingle_P3` | no error | 3,009 | 6,390 | 17 | 00s | 1.1 s | 35 MB |
| `X4_NaiveSingle_P4` | no error | 8,806 | 18,951 | 21 | 00s | 1.2 s | 37 MB |
| `X4_NaiveSingle_W3` | no error | 18,430 | 55,341 | 18 | 00s | 1.2 s | 40 MB |
| `X4_Fenced_P3` | no error | 823 | 1,856 | 18 | 00s | 1.3 s | 36 MB |
| `X4_Fenced_P4` | no error | 1,687 | 3,792 | 22 | 00s | 1.4 s | 44 MB |
| `X4_Fenced_W3` | no error | 4,471 | 14,332 | 19 | 01s | 1.8 s | 51 MB |
| `X4_FencedTimeouts_P3` | no error | 3,436 | 13,745 | 22 | 01s | 1.7 s | 49 MB |
| `X4_FencedTimeouts_P4` | no error | 7,903 | 32,168 | 27 | 01s | 2.2 s | 72 MB |
| `X4_FencedTimeouts_W3` | no error | 33,797 | 195,904 | 25 | 06s | 6.7 s | 209 MB |

The largest run before, `X1_AppliedZombie2` with 50,513 distinct states, is passed by seven of these that completed, the largest `X3_PerStreamRestart_N3` with 1,454,319. The peak heap of a wide run is the one read under a heap of 4,096 MB, so by the finding above it is not what a smaller heap needs. Both limit runs filled their heap, at 8,128 MB of 8,192, so each reached the 8 GB limit as well as the 30 minutes. With 16 workers some depths differ by one or two from the first session's runs, for example `X4_Fenced_P4` at 22 against 24, while the counts are the same.

With a restart allowed, X3's relay could not be stepped past three receipts in a stream or a third stream within machine S's limits. `X3_PerStreamRestart_N4` spent 01min 31s and then 05min 10s of its 30 minutes in TLC's checks of the temporal properties during the search. `X3_PerStreamRestart_S3` spent 01min 33s and then 05min 28s in them, and in its last minute generated 568,496 states against about two million a minute before, as its heap filled. Run on its own it found 24,348,504 distinct states in 30 minutes, where its first run, sharing the machine, found 15,754,453.

### The base tier at 2 GB

`LATTICE_MODELS_MAX_HEAP_MB=2048 mise run check:models-multi-store`, the whole base tier through the runner with the budget at 2 GB, one configuration at a time, after the manifest's peaks were measured again under a heap of 2,048 MB. All 50 passed, and the run printed "models: 50 as expected, 0 failed, 0 skipped, 0 stopped" and exited 0. No configuration moves to `wide`. The first session's first run, with the margin at half again and at least 128 MB, failed `X1_AppliedZombie2` and `X1R_AppliedZombie2` with "Error: Java ran out of memory during liveness checking", which is why the margin is twice the peak.

Each configuration's peak heap in that run, under the heap the runner gave it. The manifest's peak, measured under a heap of 2,048 MB, is beside it.

| Configuration | Verdict | Heap given | Peak heap | Manifest's peak | TLC time | Wall time |
|---|---|---|---|---|---|---|
| `ModelA_Atomic` | no error | 256 MB | 15 MB | 17 MB | 00s | 1.0 s |
| `ModelA_SnapshotNoWWDetect` | `NoLostUpdate` violated | 256 MB | 15 MB | 15 MB | 00s | 1.0 s |
| `X1_Applied` | no error | 256 MB | 21 MB | 28 MB | 00s | 1.3 s |
| `X1_AppliedZombie` | no error | 256 MB | 21 MB | 28 MB | 00s | 1.4 s |
| `X1_AppliedZombie2` | no error | 288 MB | 232 MB | 111 MB | 05s | 6.0 s |
| `X1_Received` | temporal properties violated | 256 MB | 19 MB | 26 MB | 00s | 1.5 s |
| `X1_Unguarded` | `EachAppliedOnceInEffect` violated | 256 MB | 15 MB | 18 MB | 00s | 1.0 s |
| `X1_Torn` | `NoTornRead` violated | 256 MB | 15 MB | 18 MB | 00s | 1.0 s |
| `X1_TornZombie` | `NoTornRead` violated | 256 MB | 15 MB | 18 MB | 00s | 1.0 s |
| `X1_TornReceived` | `NoTornRead` violated | 256 MB | 15 MB | 18 MB | 00s | 1.0 s |
| `X1_TornCrash` | `NoStrandedHalfApply` violated | 256 MB | 15 MB | 18 MB | 00s | 1.1 s |
| `X2_Watermark` | no error | 256 MB | 17 MB | 27 MB | 00s | 1.1 s |
| `X2_WatermarkStalled` | temporal properties violated | 256 MB | 17 MB | 17 MB | 00s | 1.1 s |
| `X2_BestKnown` | `EvidenceAsOfP` violated | 256 MB | 15 MB | 15 MB | 00s | 1.1 s |
| `X2_BestKnownAudit` | no error | 256 MB | 28 MB | 35 MB | 01s | 1.7 s |
| `X2_BestKnownStalled` | no error | 256 MB | 27 MB | 34 MB | 00s | 1.5 s |
| `X2_BestKnownSuperseded` | `NoneSuperseded` violated | 256 MB | 15 MB | 15 MB | 00s | 1.1 s |
| `X3_ByPositionLive` | temporal properties violated | 256 MB | 19 MB | 26 MB | 00s | 1.4 s |
| `X3_ByPositionOrder` | `PerStreamOrder` violated | 256 MB | 15 MB | 17 MB | 00s | 1.2 s |
| `X3_ByPositionRestart` | temporal properties violated | 256 MB | 24 MB | 32 MB | 01s | 1.8 s |
| `X3_PerStream` | no error | 256 MB | 21 MB | 28 MB | 00s | 1.2 s |
| `X3_PerStreamRestart` | no error | 256 MB | 43 MB | 51 MB | 01s | 2.3 s |
| `X3_PerStreamDuplicate` | `NoDuplicate` violated | 256 MB | 15 MB | 15 MB | 00s | 1.1 s |
| `X4_Naive` | `NoLostWrite` violated | 256 MB | 15 MB | 15 MB | 00s | 1.1 s |
| `X4_NaiveSingle` | no error | 256 MB | 15 MB | 17 MB | 00s | 1.1 s |
| `X4_NaiveTimeouts` | `SingleAuthority` violated | 256 MB | 15 MB | 17 MB | 00s | 1.0 s |
| `X4_Fenced` | no error | 256 MB | 21 MB | 28 MB | 00s | 1.2 s |
| `X4_FencedTimeouts` | no error | 256 MB | 23 MB | 30 MB | 00s | 1.4 s |
| `X1R_Applied` | no error | 256 MB | 21 MB | 28 MB | 00s | 1.4 s |
| `X1R_AppliedZombie2` | no error | 320 MB | 171 MB | 113 MB | 04s | 5.3 s |
| `X1R_Received` | temporal properties violated | 256 MB | 20 MB | 27 MB | 00s | 1.2 s |
| `X1R_ReceivedGap` | `NoGap` violated | 256 MB | 15 MB | 18 MB | 00s | 1.0 s |
| `X1R_ReceivedGapB` | `NoGapBehindA` violated | 256 MB | 15 MB | 18 MB | 00s | 1.0 s |
| `X1R_ReceivedRow` | `EachAppliedOnceInEffect` violated | 256 MB | 15 MB | 18 MB | 00s | 1.1 s |
| `X1R_ReceivedStep` | `VersionStepsByOne` violated | 256 MB | 15 MB | 18 MB | 00s | 1.0 s |
| `X5_BuiltAnyDoc` | `WholeCommands` violated | 256 MB | 15 MB | 16 MB | 00s | 1.1 s |
| `X5_BuiltAnyDesc` | `WholeCommands` violated | 256 MB | 15 MB | 16 MB | 00s | 1.1 s |
| `X5_BuiltStream` | no error | 256 MB | 22 MB | 24 MB | 00s | 1.2 s |
| `X5_BuiltStreamDelFirst` | no error | 256 MB | 18 MB | 24 MB | 00s | 1.2 s |
| `X5_BuiltStream3` | no error | 256 MB | 55 MB | 63 MB | 01s | 1.9 s |
| `X5_BuiltStreamAnswers` | `AnswersAgree` violated | 256 MB | 15 MB | 16 MB | 00s | 1.0 s |
| `X5_WholeAny` | no error | 256 MB | 23 MB | 30 MB | 00s | 1.4 s |
| `X5_WholeStream` | no error | 256 MB | 18 MB | 24 MB | 00s | 1.1 s |
| `X5_WholeStreamAnswers` | `AnswersAgree` violated | 256 MB | 15 MB | 16 MB | 00s | 1.0 s |
| `X5_FencedAny` | no error | 256 MB | 23 MB | 30 MB | 00s | 1.4 s |
| `X5_FencedStream` | no error | 256 MB | 18 MB | 24 MB | 00s | 1.1 s |
| `X5_FencedStreamAnswers` | `AnswersAgree` violated | 256 MB | 15 MB | 16 MB | 00s | 1.0 s |
| `X5_FencedAnswerAny` | no error | 256 MB | 23 MB | 30 MB | 00s | 1.3 s |
| `X5_FencedAnswerStream` | no error | 256 MB | 19 MB | 18 MB | 00s | 1.1 s |
| `X5_FencedAnswerStream3` | no error | 256 MB | 26 MB | 33 MB | 00s | 1.3 s |

The largest peak was 232 MB, `X1_AppliedZombie2` under a heap of 288 MB, and the largest heap given was 320 MB, to `X1R_AppliedZombie2`, whose peak was 171 MB. The task, the runner's tests included, finished in 75.08 s by mise's clock. Depth differs between runs for some configurations run with 16 workers, for example `X4_Fenced` printed 14 in the measurement and 16 here, while the distinct states never differed. TLC's depth with several workers is not exact, and the manifest's is one run's.

### Tests

| ID | Given / When / Then | Level | Pass criterion | Kind |
|---|---|---|---|---|
| I6R-T1 | Given the base tier and `LATTICE_MODELS_MAX_HEAP_MB=2048`, when the runner runs it, then every configuration gives the verdict the manifest expects within the budget | L2 | "models: 50 as expected, 0 failed, 0 skipped, 0 stopped", exit 0 | positive |
| I6R-T2 | Given the 25 wide configurations under a heap of 4,096 or 8,192 MB and 30 minutes, when TLC runs each, then each finds no error or is stopped at the limit | L2 | each line `PASS` with "no error", or `STOP` at the limit | positive |
| I6R-T3 | Given `TLA2TOOLS_JAR` unset, when the runner runs, then it says what it skipped and exits 0 | L1 | "SKIP: TLA2TOOLS_JAR is not set, so no configuration was checked. Set it to the TLA+ tools jar", exit 0 | negative |
| I6R-T4 | Given a budget of 280 MB, when the runner is asked for `X1_AppliedZombie2` and `X4_Naive`, then it never starts the first and names both figures, and runs the second | L1 | "SKIP X1_AppliedZombie2: needs a heap of 288 MB, and the budget is 280 MB", "models: 1 as expected, 0 failed, 1 skipped, 0 stopped", exit 0 | negative |
| I6R-T5 | Given a manifest that expects no error of `X4_Naive`, when the runner runs it, then the configuration fails | L1 | "FAIL X4_Naive: TLC printed invariant NoLostWrite violated, expected no error", exit 1 | negative |
| I6R-T6 | Given a heap of 192 or 208 MB for `X1_AppliedZombie2`, when TLC runs out of heap, then the run is stopped and does not fail | L1 | `STOP` "ran out of its heap", "models: 0 as expected, 0 failed, 0 skipped, 1 stopped" | negative |
| I6R-T7 | Given the base tier, `--jobs 4` and a budget of 600 MB, when the runner runs it, then configurations run together never hold more heap than the budget, and each has its own temporary directory | L1 | "models: 50 as expected, 0 failed, 0 skipped, 0 stopped", and from the `RUN` and result lines at most two at once holding at most 576 MB | positive |
| I6R-T8 | Given `--max-minutes 0.3`, when `X3_PerStream_S3` runs longer, then the run is stopped and reported with the last counts TLC printed, and does not fail | L1 | `STOP` "stopped at the limit of 0.3 min", "0 failed, 0 skipped, 1 stopped", exit 0 | negative |
| I6R-T9 | `tools/models/test_check_tlc.py`, 24 tests: the budget is a quarter of physical memory, never above what is available, lowered and never raised by the variable, which must be a number. A run's heap is twice its peak and 64 MB in steps of 32, at least 256 MB. A configuration over the budget is skipped with both figures and never planned, one at the budget runs, one stopped at the limit or never measured is skipped unless `--heap-mb` is given. Runs together never hold more than the budget. A verdict as expected passes, a different one fails, a run out of heap stops, no verdict fails. The counts are the last TLC printed. The peak heap is the largest before a collection. The manifest has one entry for each `.cfg` and 50 in `base` | L0 | "24 passed" | positive and negative |

### One command

From the repository's root, with `TLA2TOOLS_JAR` naming the TLA+ tools jar and the checkout bootstrapped, which installs `mem_check`.

On macOS and Linux:

```bash
export TLA2TOOLS_JAR=/path/to/tla2tools.jar
mise run check:models-multi-store                                    # the base tier
LATTICE_MODELS_MAX_HEAP_MB=2048 mise run check:models-multi-store    # the base tier within 2 GB
mise run check:models-multi-store -- wide                            # what of the wide tier fits the machine
```

On Windows, in PowerShell:

```powershell
$env:TLA2TOOLS_JAR = '<path to tla2tools.jar>'
mise run check:models-multi-store
mise run check:models-multi-store '--' wide
```

A pass of the base tier prints the runner's tests, "24 passed", then one line for the budget, then for each of the 50 configurations a `RUN` line and a `PASS` line with the verdict the manifest expects, the counts, the depth, the times and the peak heap, and ends with "models: 50 as expected, 0 failed, 0 skipped, 0 stopped". It exits 0. Twenty-four `PASS` lines read "no error", and twenty-six name the property violated, as the manifest lists. On a machine of 8 GB the budget is at most 2 GB, which every base configuration fits. The wide tier skips each configuration whose heap exceeds the budget, with both figures, and each stopped at machine S's limit, and exits 0 unless a run's verdict differs. With a budget of 2,048 MB it runs 19 of the 25 and skips `X1_AppliedZombie2_K4W3`, `X3_PerStream_N4`, `X3_PerStream_S3` and `X3_PerStreamRestart_N3` for their heap, from 2,304 to 6,240 MB, and the two limit runs. With a budget of 4,096 MB, on a machine of 16 GB, it runs 22 and skips `X3_PerStreamRestart_N3` and the two limit runs.

### What was run, in full

Every command was run on machine S from the repository's root, by the second session unless the row says otherwise, each output captured to a file and read in full. `PYTHONUTF8=1` and `TLA2TOOLS_JAR` were set in the shell.

| Command | Result |
|---|---|
| The first session's `mise run check:models-multi-store '--' X3_PerStreamRestart_S3 X3_PerStreamRestart_N4 --heap-mb 8192 --max-minutes 30`, started at 01:15 and left running, its output read by the second session | `STOP X3_PerStreamRestart_S3: stopped at the limit of 30 min`, peak heap 8190 MB, and `STOP X3_PerStreamRestart_N4: stopped at the limit of 30 min`, peak heap 8128 MB, "models: 0 as expected, 0 failed, 0 skipped, 2 stopped". The counts in the tables are from each run's `tlc.out`, whose last progress line the runner of that time did not parse. `X3_PerStreamRestart_N4` ran from 01:45:59 with no other heavy process, its TLC using 13,778 s of CPU in its first 29 minutes, and `X3_PerStreamRestart_S3` shared its first run with the first session's other runs |
| `mise exec '--' python -m py_compile tools/models/check_tlc.py` | exit 0, after the docstring's quotes were fixed |
| `mise run check:models-multi-store-runner` | "24 passed in 0.38s" |
| `mise run check:models-multi-store '--' base --heap-mb 2048` | "models: 50 as expected, 0 failed, 0 skipped, 0 stopped", "Finished in 74.32s". Its figures are the manifest's for the base tier, every distinct-state count the same as the README's results tables |
| `mise run check:models-multi-store '--' "X1_*_K4*" "X2_*_P4*" "X3_PerStream_*" X3_PerStreamRestart_N3 "X4_*_P3" "X4_*_P4" "X4_*_W3" --heap-mb 4096 --max-minutes 30` | "models: 23 as expected, 0 failed, 0 skipped, 0 stopped", "Finished in 348.95s". Its figures are the manifest's for the wide tier |
| `LATTICE_MODELS_MAX_HEAP_MB=2048 mise run check:models-multi-store`, I6R-T1 | "models: 50 as expected, 0 failed, 0 skipped, 0 stopped", exit 0, "Finished in 75.08s". Of the 50 `PASS` lines 24 read "no error" and 26 name a violation. An earlier attempt in the same shell was cut off after `X4_NaiveTimeouts` with no result line, and its runner and TLC processes were gone, so the run was made again |
| the same, with `TLA2TOOLS_JAR` unset, I6R-T3 | "SKIP: TLA2TOOLS_JAR is not set, so no configuration was checked. Set it to the TLA+ tools jar", exit 0 |
| `LATTICE_MODELS_MAX_HEAP_MB=280 mise run check:models-multi-store '--' X1_AppliedZombie2 X4_Naive`, I6R-T4 | "SKIP X1_AppliedZombie2: needs a heap of 288 MB, and the budget is 280 MB", `PASS X4_Naive: invariant NoLostWrite violated`, "models: 1 as expected, 0 failed, 1 skipped, 0 stopped", exit 0 |
| `mise exec '--' python tools/models/check_tlc.py X4_Naive` with the manifest's entry changed for the run to expect no error, then changed back, I6R-T5 | "FAIL X4_Naive: TLC printed invariant NoLostWrite violated, expected no error", "models: 0 as expected, 1 failed, 0 skipped, 0 stopped", exit 1 |
| `mise exec '--' python tools/models/check_tlc.py X1_AppliedZombie2 --heap-mb <h>` for 192, 224, 240 and 256 MB, then 208 and three more at 224, I6R-T6 | `STOP` "ran out of its heap" at 192 MB, peak 187 MB, and at 208 MB, peak 204 MB, TLC printing "Error: Java ran out of memory during liveness checking". At 224 MB `STOP` once, peak 220 MB, and `PASS` "no error" three times, peaks 220, 218 and 218 MB. `PASS` at 240 MB, peak 234 MB, and at 256 MB, peak 231 MB, each with 50,513 distinct states |
| `LATTICE_MODELS_MAX_HEAP_MB=600 mise exec '--' python tools/models/check_tlc.py base --jobs 4`, the output then counted line by line, I6R-T7 | "models: 50 as expected, 0 failed, 0 skipped, 0 stopped", exit 0, at most two running at once and at most 576 MB held together |
| `mise exec '--' python tools/models/check_tlc.py X3_PerStream_S3 --max-minutes 0.3`, I6R-T8 | "STOP X3_PerStream_S3: stopped at the limit of 0.3 min, 392,848 distinct of 971,581 generated", wall 18.2 s, "models: 0 as expected, 0 failed, 0 skipped, 1 stopped", exit 0. TLC had found every state and was in its last check of the temporal properties |
| `mise exec '--' python tools/models/check_tlc.py X3_PerStreamRestart_S3 --heap-mb 8192 --max-minutes 30`, on its own | "STOP X3_PerStreamRestart_S3: stopped at the limit of 30 min, 24,348,504 distinct of 47,624,388 generated, depth not printed, last progress 24, TLC time not printed, wall 1801.1 s, peak heap 8190 MB", "models: 0 as expected, 0 failed, 0 skipped, 1 stopped". Nothing else heavy ran from 02:31 to 03:01 |
| `LATTICE_MODELS_MAX_HEAP_MB=4096 mise exec '--' python tools/models/check_tlc.py wide --list`, and the same at 2048 with `all` | at 4,096 MB, 22 planned and `X3_PerStreamRestart_N3` skipped, "needs a heap of 6,240 MB, and the budget is 4,096 MB", with the two limit runs. At 2,048 MB, 69 of 75 planned and six of the wide tier skipped, four needing 2,304 to 6,240 MB and the two limit runs. Both exit 0 |
| `mise exec '--' python tools/writing_rules.py docs/developer/validation/MSA-I6.md tools/models/multi-store-protocols/README.md` | "writing rules: 0 failure(s), 0 warning(s)", exit 0 |
| `mise run check:portability` | "portability: 0 problem(s)", then its tests "25 passed in 2.97s", exit 0 |
| `mise run check:catalogue` | "repository catalogue: 22 module(s) and 19 tool package(s) agree with the tree. Bypass scan: 13 known file(s)", exit 0 |
| `mise exec '--' python -m py_compile tools/models/check_tlc.py`, last | exit 0, and `mise run check:models-multi-store-runner` after the manifest's last change, "24 passed in 0.32s" |

The first session's other runs, listed in its draft of this section, are superseded by these and are not repeated here. Its outputs that this section cites, the first 2 GB run and the limit runs, were read from the files it left.

### Deliberate non-coverage

- **The run on macOS and on Linux.** Not possible on machine S. The one command above is what to run there, and what a pass prints is stated with it. The memory reading on those platforms, `os.sysconf` for physical memory and the cgroup's limit on Linux, has not run, and the tests do not reach it.
- **A runner without `mem_check`.** Authored to say what it skipped and exit 0, not run, since the package is installed in this checkout.
- **The heap a configuration needs.** The manifest states the peak read under one heap, and the runner doubles it. Only `X1_AppliedZombie2`'s least heap was looked for, and it lies at about 224 MB, where one run of four ran out.
- **Wider instances of the configurations that violate a property, of X1 with receipts only and of X5.** Not run. A counterexample found in the base instance is found in a wider one, and the brief names X1 to X4.
- **More crashes, writers or restarts than the base configurations have.** Not stepped. Only the commands, the window, and in X3 and X4 a third stream or writer.
- **TLC's `-lncheck final`,** which checks the temporal properties once at the end rather than during the search, and might let a limit run finish. Not tried, since it changes how the wide tier is checked. It is a question below.
- **The saga row, models B to D, the isolation probes and the trace validation.** As before, other parts of MSA-I6.

### Doc delta

- The models' README, as above.
- For the coordinator. The base tier fits a heap budget of 2 GB, the largest heap given 320 MB and the largest peak 232 MB. Seven wide configurations that completed pass the largest run before, and TLC printed "No error has been found" for every wide configuration of X1 to X4 that it finished, up to four commands and a window of three. With a restart, X3's relay at four receipts in a stream or at three streams reached the 30-minute limit and filled its 8 GB heap with no error printed by then. Nothing is concluded for those two, since TLC had not reached every state. The figures of each configuration are in the manifest.

### Index report

- `mise run graph:ask -- find` with "a runner that sizes a model checker heap to the machine and skips a run that does not fit the memory budget" answered weakly, the best TD-150 at 0.69 and STD-151 at 0.66, which sizes test workers with `mem_check`, and the runner follows it. "a check that skips and exits zero when its tool is missing" answered PRI-79 at 0.78 and ADR-A125 at 0.73, which the runner follows. "test-support package used by a check task run on demand" answered ADR-A125 at 0.76 and ADR-A124 at 0.75.
- The first session recorded two gaps, against STD-151, that a TLC run's peak heap depends on the heap given and liveness checking needs about twice the peak a large heap shows, and against ADR-A-FM4, that TLC writes its standard modules to Java's temporary directory, so runs started together need one each. Their pointers name lines 84 and 228 of `tools/models/check_tlc.py`, which are now `heap_mb` at line 85 and the temporary directory at line 282.
- One gap recorded by the second session, against ADR-A125, that its addendum says a check that finds a test-support package missing stops and names the task that installs it, and PRI-79 says a task whose tool is missing says what it skipped and passes, and no entry says which an on-demand check follows. Its pointer names `tools/models/check_tlc.py:347`, and the import is at line 355. PRI-79's statement of the cases it does not cover, or an edge from it to ADR-A125's addendum, would carry it.
- `mise run graph:ask -- misses --near` lists the sizing query as a near miss and the first session's two queries on the runner as misses. A `--tech` value for TLC on STD-151, or an edge from STD-151 to the formal-methods track's model runs, would have carried them.

### For the maintainer

- **What "commands" and "a window" mean in X2 to X4.** The brief names both for X1 to X4, and only X1 has a window. We read a command as each model's unit of work, a position and a decision in X2, a receipt in X3 and a write in X4, and took a third stream or writer as X3's and X4's second step. (a) Keep that. (b) Step only the commands in X2 to X4. (c) Step other constants as well, for example X1's crashes or X3's restarts. We lean to (a), and it is your decision.
- **What the manifest states as a configuration's need.** The GC log's peak varies with the heap given, so the runner doubles it and adds 64 MB. `X1_AppliedZombie2` gets 288 MB, and ran out of 224 MB once in four runs. (a) Keep the doubled peak. (b) Find each configuration's least heap by bisection and state that, with a smaller margin, which costs a run per step for each configuration and, at the edge, gives a run that fails one time in several. (c) Give TLC's own sizing options, `-fpmem`, a fixed share. We lean to (a), since the base tier fits 2 GB with room.
- **Liveness checked at the end.** TLC checks the temporal properties during the search as well as at the end. `X3_PerStreamRestart_N4` spent 01min 31s and then 05min 10s of its 30 minutes in two such checks. `X3_PerStreamRestart_S3` spent 01min 33s and then 05min 28s. `-lncheck final` checks them once, at the end, so a larger instance may finish within 30 minutes, and a violation is found later. Should the runner pass it for the wide tier?
- **A missing `mem_check`.** The runner names the task that installs it and exits 0, as PRI-79 says of a missing tool. ADR-A125's addendum says a check task that finds a test-support package missing "stops and names the task that installs it". (a) Keep the exit 0. (b) Exit non-zero. (c) Read available memory with the standard library, as `mem_check` does, so the runner needs no test-support package. We lean to (a), since the brief asks that nothing fail for want of a tool.
- **`mem_check` has no reading of physical memory.** The runner reads it itself. Should `mem_check` gain one, so that one package reads memory?
- **The runner's tests and `check`.** `check:models-multi-store-runner` runs in under a second with neither Java nor TLC, and runs only before `check:models-multi-store`. Should it join `check`, so a change to the runner or the manifest is tested on every run?
- **Wide configurations that fit 2 GB.** Nineteen of the 25 fit a budget of 2,048 MB, and most of X2 and X4's need 256 MB. They are in the `wide` tier as the brief asks. Should those that fit 2 GB move to `base`, so that a small machine runs them by default?

## Protocol A in one ledger, a pass over two ledgers and X2's audit, 2026-11-24

**Brief:** [machine S brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md), section 4.4, "Protocol A in one ledger", "A pass over two ledgers" and "X2's audit, settled by a run", and section 7. [Handover of 2026-11-23](../notes/machine-s-handover-2026-11-23.md), sections 3 and 4. The ledger half of the [brief of 2026-11-19](../notes/machine-s-brief-2026-11-19.md), section 4, for the two gaps.
**Machine:** machine S, Windows 11, 16 logical cores, 64 GB installed, TLA+ tools 1.7.4 (TLC 2.19) on Java 25.0.2 through mise, the jar named by `TLA2TOOLS_JAR`. At most 8 TLC workers at a time, since another session timed JVM start-up on the machine and ran Maven tests while these runs were made. **Placement:** T0, public. Protocol models, nothing domain-specific beyond the example of a claim on a contract that the handover names.
**Status:** built 2026-11-24, not verified. What this pack reported before stands.

### Invariant

A pass written as one request on the revision it was evaluated from keeps every outcome one that the evaluations give made one after the other, with a stop and without. Over two ledgers, a claim keeps that only where a refused request returns the revision it found and the first pass records the revisions its decision started from.

### What changed

- `tools/models/multi-store-protocols/PA_PassRevision.tla`, new. Protocol A in one ledger, with `OnLatest` and `PerPosting` beside it, two position rules, a credit or a second activation, one stop, and the invariants O1 to O4 and `Census`.
- `tools/models/multi-store-protocols/X6_PassTwoLedgers.tla`, new. A claim on a contract that erodes a programme's aggregate, a pass in each of two ledgers, each gap of the ledger half's section 4 a constant.
- `tools/models/multi-store-protocols/X2_AuditFlags.tla`, new. It extends `X2_EvidenceAcrossStores.tla`, which is unchanged, and adds `FlaggedIsStale`.
- 18 configurations, new, all in the `base` tier: `PA_OnRead`, `PA_OnReadAligned`, `PA_OnLatestO1`, `PA_OnLatestO3`, `PA_PerPostingO1`, `PA_StimulusO3`, `PA_Census`, `PA_CensusAligned`, `X6_Closed`, `X6_ClosedTorn`, `X6_ClosedTornCrash`, `X6_ClosedPositions`, `X6_RefusalOpen`, `X6_RefusalOpenHalf`, `X6_StartOpen`, `X6_StartOpenHalf`, `X2A_FlaggedIsStale` and `X2A_FlaggedIsStaleOneStep`.
- `tools/models/multi-store-protocols/manifest.toml`, an entry for each, and a line in its header that says they were measured with 8 workers.
- `tools/models/test_check_tlc.py`, the count of `base` entries the manifest test expects, from 50 to 68. No other test changed.
- The models' [README](../../../tools/models/multi-store-protocols/README.md). The three modules, their configurations, results and conclusions, the Running section's counts, and X2's two sentences rewritten.

No existing module, the runner or `mise.toml` changed.

### The configurations

Each was run through the runner under `--heap-mb 2048`, one at a time, on 8 workers where no error was expected and one where a counterexample was. Diameter is TLC's "depth of the complete state graph search", and for a counterexample the depth when it stopped. The figures are those of the run of all 18, except `PA_OnRead`, `PA_OnLatestO1` and `PA_OnLatestO3`, which were run again because the machine was shared, and whose faster run the manifest takes.

| Configuration | Verdict | Distinct states | Generated | Diameter | Peak heap | TLC time | Wall time |
|---|---|---|---|---|---|---|---|
| `PA_OnRead` | no error | 1,764 | 2,664 | 7 | 29 MB | 01s | 3.1 s |
| `PA_OnReadAligned` | no error | 900 | 1,224 | 7 | 28 MB | 01s | 2.3 s |
| `PA_OnLatestO1` | `SerialOutcomes` violated | 1,234 | 1,662 | 5 | 23 MB | 03s | 4.9 s |
| `PA_OnLatestO3` | `PassOrder` violated | 941 | 1,232 | 5 | 15 MB | 01s | 2.7 s |
| `PA_PerPostingO1` | `SerialOutcomes` violated | 3,480 | 5,394 | 7 | 28 MB | 01s | 2.7 s |
| `PA_StimulusO3` | `PassOrder` violated | 505 | 505 | 5 | 15 MB | 00s | 1.6 s |
| `PA_Census` | no error, census printed | 31,098 | 45,414 | 13 | 59 MB | 01s | 2.6 s |
| `PA_CensusAligned` | no error, census printed | 15,976 | 21,012 | 14 | 47 MB | 01s | 2.9 s |
| `X6_Closed` | no error | 4,950 | 8,745 | 15 | 28 MB | 01s | 1.6 s |
| `X6_ClosedTorn` | `NoTornRead` violated | 1,406 | 2,788 | 6 | 23 MB | 00s | 1.4 s |
| `X6_ClosedTornCrash` | `NoStrandedHalf` violated | 435 | 687 | 5 | 15 MB | 00s | 1.3 s |
| `X6_ClosedPositions` | `OnePosition` violated | 1,655 | 2,878 | 8 | 27 MB | 00s | 1.3 s |
| `X6_RefusalOpen` | `SerialClaims` violated | 3,367 | 5,805 | 10 | 28 MB | 00s | 1.4 s |
| `X6_RefusalOpenHalf` | `NoHalfClaim` violated | 4,055 | 6,935 | 11 | 28 MB | 01s | 1.6 s |
| `X6_StartOpen` | `SerialClaims` violated | 5,195 | 8,957 | 13 | 28 MB | 00s | 1.4 s |
| `X6_StartOpenHalf` | no error | 8,256 | 13,911 | 20 | 31 MB | 01s | 1.7 s |
| `X2A_FlaggedIsStale` | `FlaggedIsStale` violated | 361 | 453 | 5 | 15 MB | 00s | 1.6 s |
| `X2A_FlaggedIsStaleOneStep` | no error | 13 | 15 | 4 | 15 MB | 00s | 1.7 s |

Every one fits the base tier's budget of 2 GB, the largest peak 59 MB under a heap of 2,048 MB, and the runner gives each 256 MB. In the base run below, under those heaps, the largest of these peaks was 51 MB. The README's results table has each counterexample.

### Protocol A in one ledger, against the Python model

**How it was done.** We wrote `PA_PassRevision.tla` from ADR-A131's second addendum of 2026-11-19, its addendum of 2026-11-20 and `ordered-draws.ttl`, and ran it, before reading [`tools/models/ledger-pass-revision/`](../../../tools/models/ledger-pass-revision/README.md). That first version had one licence, a credit of one seat cut at a stated 3, a refused alert as a record, either actor able to stop, the bundle at 0 to 3 and the quota at 0 to 2. It checked O1, that every outcome once both actors are done is one the two evaluations give made one after the other, and checked the order of positions under the name O2. `PA_OnRead` gave 1,764 distinct states with no error, and the census 31,098.

**Aligning the statements.** The Python model's O2 is "every outcome with a crash is an outcome without one", and the order of positions is its O3, with "never before its stimulus" its O4. We renamed ours to match, and added O2, `StopSafe`, which the first version did not check. It is checked inside TLC, by a recursion over the steps with no stop from the behaviour's starting state. We then added constants that let the model run on the Python model's instance, `PA_OnReadAligned` and `PA_CensusAligned`. With the constants at the first version's values, `PA_OnRead` and `PA_Census` give the same counts as before, 1,764 and 31,098.

**The counts side by side.** The Python model's figures were printed on machine S by its two scripts, and its cells were listed by a script that imports them. Ours are counted from the census on the Python model's instance, 12 revision cells and 36 position cells, the same as its own. "With a crash" is a run in which a stop is allowed, those without one among them, in both models.

| Protocol | Python: O1 fails, no crash | TLA+ | Python: O1 fails, with a crash | TLA+ | Python: O2 fails | TLA+ | Python: outcomes no order gives, no crash | TLA+ |
|---|---|---|---|---|---|---|---|---|
| A, `OnRead` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| A', `OnLatest` | 1 | 5 | 7 | 5 | 6 | 0 | 1 | 9 |
| B | 7 | not modelled | 12 | not modelled | 12 | not modelled | 9 | not modelled |
| C | 7 | | 7 | | 2 | | 13 | |
| C+ | 7 | | 7 | | 2 | | 9 | |
| C++ | 7 | | 7 | | 0 | | 9 | |
| `PerPosting` | | 7 | | 7 | | 0 | | 9 |

| Protocol, rule | Python: O3 fails, one after another | TLA+ | Python: no crash | TLA+ | Python: with a crash | TLA+ | Python: O4 fails | TLA+ |
|---|---|---|---|---|---|---|---|---|
| A, stimulus | 20 | 24 | 20 | 24 | 20 | 24 | 0 | 0 |
| A, read (`LaterOf`) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| A', stimulus | 20 | 24 | 20 | 24 | 20 | 24 | 0 | 0 |
| A', read (`LaterOf`) | 0 | 0 | 10 | 24 | 10 | 24 | 0 | 0 |
| `PerPosting`, stimulus | | 24 | | 24 | | 24 | | 0 |
| `PerPosting`, `LaterOf` | | 0 | | 0 | | 0 | | 0 |

On its own instance the TLA+ model has 24 revision cells and 72 position cells. There `OnRead` breaks nothing, `OnLatest` breaks O1 in the 12 cells with a second activation, `PerPosting` in 9, O2 fails nowhere, and the stimulus rule breaks O3 in 36. The README has both tables.

**What agrees.** Both models find that a pass written as one request on the revision it read keeps O1 to O4 in every cell, with a stop and without, and that the later of the two positions, read with the revision, keeps the order. Both find that writing on the latest revision breaks O1 and, with the position read, O3, that a posting written alone breaks O1, that the stimulus's position breaks O3 even one after another, and that no rule puts a pass before its stimulus. The TLA+ `PerPosting` breaks O1 in the same 7 cells as the Python model's C, C+ and C++, bundle 0 and 1 with a credit at either quota, bundle 1 with a second activation at quota 1, and bundle 2 with a second activation at either quota.

**Findings.** Each is a difference between the two models' results.

- **MSAI6-02, where the state change is written.** In the TLA+ model the move to overage is a record of the pass, written in its one request. In the Python model it is one of Behaviour's records, written in a step after the ledger's write. Two differences follow. The stimulus rule breaks O3 in 24 cells against 20, the four more being a second activation at bundle 0 or 1 and quota 1 in either order, whose only transition is its move, which writes a pass in the TLA+ model and none in the Python. And O2 never fails in the TLA+ model, where the Python model's A' fails it in 6 cells, all with a credit. There a crash falls after the ledger's write and before Behaviour's records, the replay evaluates from the revision before its receipt, which under A' is not the revision read, and it records transitions that are not the postings written. The Python model's 7 cells of O1 with a crash under A' are those 6 and its one cell with no crash. Which arrangement the runtime has is the maintainer's question below.
- **MSAI6-03, what writing on the latest revision means.** The Python model's writer refuses such a request whole where it would overdraw, and the pass is evaluated again. The TLA+ `OnLatest` applies each draw by the ledger's arithmetic, records a refused draw, and never evaluates again. So O1 fails with no stop in 5 cells against 1, and gives 9 outcomes no order gives against 1. The position rule read with the revision fails in 24 cells against 10. Beside the refusal, the Python model's credit is read and written in the writer's own turn, so its position is never stale, where the TLA+ credit reads in a step of its own and falls behind in either order. Both protocols are broken, and the counts measure two readings of a protocol the ADR rejects, so neither is a defect.
- **MSAI6-04, a posting written alone.** The TLA+ `PerPosting` evaluates every transition not yet written again from the revision a refusal returns, including one its first evaluation left out, and records no start. The Python model's C, C+ and C++ go on past a refused posting. The cells where O1 fails are the same, and O2 holds in `PerPosting` as in C++. In `PerPosting` a refused posting's remaining transitions are evaluated again, so by its definition a seat can be drawn after the pass's own alert with no stop, which C and C+ reach only through a crash. O2 holding in `PerPosting` says only that a stop adds no outcome the protocol does not already reach.
- **MSAI6-05, the instance.** The first version's instance differs from the Python model's in five ways: one licence for both activations, where ordered-draws.ttl has one licence and the Python model gives the second activation a state of its own, a credit of one seat cut at a stated 3 against 3 seats with no ceiling, a refused alert recorded against the quota in the alert's guard, either actor able to stop against the first activation alone, and its starting cells. On it `OnLatest` breaks O1 in all 12 cells with a second activation, since a second activation of one licence that finds it on overage writes nothing, which a stale pass contradicts. The aligned configurations take these differences out, and the counts of the two tables above are on the same instance.

### A pass over two ledgers

The example is the handover's, a claim on a contract that erodes a programme's aggregate. The contract's ledger C and the programme's ledger P each take a request of their own under Protocol A. A claim reads C, then P in a later step, decides to pay one unit where both have one, and writes C, then P. A claim whose C pass is written and that is then not paid compensates it with a pass that restores the draw, the saga row's compensation. Two claims on one contract, one stop, each balance at 0, 1 or 2, and every order of the stimuli.

| Run | Gap 1, the refusal returns the revision | Gap 2, the pass records its start | Property checked | Result |
|---|---|---|---|---|
| `X6_Closed` | closed | closed | every claim whole (`SerialClaims`), each claim in both ledgers or neither at the end (`NoHalfClaim`), each ledger's passes in order of position, none before its stimulus | holds |
| `X6_ClosedTorn` | closed | closed | X1's torn read, a reader of C then P sees each claim in both or neither | violated, by a reader between E1's two passes, no stop needed |
| `X6_ClosedTornCrash` | closed | closed | X1's torn crash, a stopped claim is in both or neither | violated, by E1 stopping between its passes |
| `X6_ClosedPositions` | closed | closed | a claim's draw takes one position in both ledgers | violated, E1's draw at 2 in C and 1 in P |
| `X6_RefusalOpen` | open | closed | every claim whole | violated, with no stop |
| `X6_RefusalOpenHalf` | open | closed | each claim in both ledgers or neither at the end | violated, with no stop |
| `X6_StartOpen` | closed | open | every claim whole | violated, after a stop |
| `X6_StartOpenHalf` | closed | open | each claim in both or neither at the end, order of positions, none before its stimulus | holds |

**What each closure buys.**

- **Both closed.** Every outcome is one that the two claims give evaluated whole one after the other, and every claim ends in both ledgers or in neither, with one stop. The saga's intermediate states stay visible, as X1's row says of two stores, and a claim's two passes take different positions.
- **The refusal returning the revision.** Without it, a refused claim names the revision it already held and is refused again for good, with no stop involved. TLC printed a claim not paid where one after the other both are (`X6_RefusalOpen`), and a claim drawn on the contract and not on the aggregate, which nothing compensates since its decision never changes (`X6_RefusalOpenHalf`). So the first closure buys completion, and with it the saga's ending in both ledgers or neither.
- **The start recorded.** Without it, a claim that stops after its C pass reads C at its latest revision, takes its own draw for the contract's account being empty, decides not to pay and compensates. TLC printed no claim paid where one after the other one is (`X6_StartOpen`). Every claim still ends in both ledgers or neither (`X6_StartOpenHalf`, no error). So the second closure buys a replay that decides as the claim did, and in these constants its absence costs a wrong decision and never a half claim.

**MSAI6-06, one position for a pass over two ledgers.** Under the addendum of 2026-11-20 each ledger gives a pass the later of its stimulus's position and that ledger's latest pass's, so one evaluation's two passes can take different positions. TLC printed E1's draw at position 2 in C, behind E2's, and at position 1 in P, which had no pass. No text says whether that is allowed.

### X2's audit, settled by a run

`X2A_FlaggedIsStale` has the constants of `X2_BestKnownAudit.cfg`, S passing three positions with two values, so a value can change and change back. TLC printed "Error: Invariant FlaggedIsStale is violated." The core for position 2 read "a" at position 0, S committed "b" at 1 and "a" at 2, and the core committed its decision with "a" read at 0. S held "a" at 2, so the evidence is correct, and the audit flags it because S changed at 1. `X2A_FlaggedIsStaleOneStep`, with S reaching position 1 and a decision there only, where no value can change back, printed no error for `FlaggedIsStale` and `AuditFindsStale`. Both sentences now come from these runs.

| README section | Before | After |
|---|---|---|
| X2's abstractions | "The audit is conservative. Whether it flags a decision whose evidence is correct, for instance when the value changes and changes back, was not checked." | "The audit is conservative, and flags a decision whose evidence is correct. Where S changes the value and changes it back between the position read at and `p`, the decision carries the value S held at `p` and is flagged all the same, as TLC printed for `X2A_FlaggedIsStale` under `X2_AuditFlags.tla`." |
| What the results say | "The audit also flags a decision whose evidence is stale and one whose evidence is not, so it is a trigger for review and not a verdict." | "TLC also printed a decision that the audit flags and whose evidence is correct. The core for position 2 read "a" at position 0, S committed "b" at 1 and "a" at 2, and the decision carries "a", which S held at 2. So the audit is a trigger for review and not a verdict. With S one position past the start and a decision at that position only, where no value can change back, TLC found no flagged decision whose evidence was correct." |

### Tests

| ID | Given / When / Then | Level | Pass criterion | Kind |
|---|---|---|---|---|
| I6P-T1 `PA_OnRead` | Given Protocol A, the later position read with the revision, a credit or a second activation of one licence and one stop, over 72 initial states, when TLC explores every state, then O1 to O4 hold | L2 | "No error has been found" | positive |
| I6P-T2 `PA_OnReadAligned` | as I6P-T1 on the Python model's instance | L2 | "No error has been found" | positive |
| I6P-T3 `PA_OnLatestO1` | Given a pass written on the latest revision, then O1 fails | L2 | "Invariant SerialOutcomes is violated" | negative |
| I6P-T4 `PA_OnLatestO3` | as I6P-T3, then O3 fails | L2 | "Invariant PassOrder is violated" | negative |
| I6P-T5 `PA_PerPostingO1` | Given each posting a request of its own, then O1 fails | L2 | "Invariant SerialOutcomes is violated" | negative |
| I6P-T6 `PA_StimulusO3` | Given Protocol A with each pass at its stimulus's position, one after another and no stop, then O3 fails | L2 | "Invariant PassOrder is violated" | negative |
| I6P-T7 `PA_Census`, `PA_CensusAligned` | Given every variant, when TLC explores every state, then it prints a line for each end state, from which the cells of the tables above are counted | L2 | "No error has been found", and the counts above | positive |
| I6X-T1 `X6_Closed` | Given a pass over two ledgers with both gaps closed and one stop, then every claim is whole, ends in both ledgers or neither, and each ledger's passes keep their order | L2 | "No error has been found" | positive |
| I6X-T2 `X6_ClosedTorn`, `X6_ClosedTornCrash` | as I6X-T1, then X1's torn read and torn crash are reached | L2 | "Invariant NoTornRead is violated", "Invariant NoStrandedHalf is violated" | negative |
| I6X-T3 `X6_ClosedPositions` | as I6X-T1, then a claim's draw takes two positions | L2 | "Invariant OnePosition is violated" | negative |
| I6X-T4 `X6_RefusalOpen`, `X6_RefusalOpenHalf` | Given the first gap open, then a claim is not whole and one ends in one ledger only | L2 | "Invariant SerialClaims is violated", "Invariant NoHalfClaim is violated" | negative |
| I6X-T5 `X6_StartOpen`, `X6_StartOpenHalf` | Given the second gap open, then a claim is not whole, and each claim still ends in both ledgers or neither | L2 | "Invariant SerialClaims is violated", and "No error has been found" | negative and positive |
| I6A-T1 `X2A_FlaggedIsStale` | Given the best-known row where a value can change and change back, then a flagged decision has correct evidence | L2 | "Invariant FlaggedIsStale is violated" | negative |
| I6A-T2 `X2A_FlaggedIsStaleOneStep` | Given one position past the start and a decision there only, then every flagged decision is stale | L2 | "No error has been found" | positive |

### One command

From the repository's root, with `TLA2TOOLS_JAR` naming the TLA+ tools jar. On macOS and Linux:

```bash
mise run check:models-multi-store                                     # the base tier, the 18 new configurations among the 68
mise run check:models-multi-store -- "PA_*" "X6_*" "X2A_*"            # the new configurations alone
```

On Windows, in PowerShell, the separator is quoted, as in `mise run check:models-multi-store '--' "PA_*" "X6_*" "X2A_*"`. A pass of the base tier prints "24 passed", then for each of the 68 configurations a `RUN` line and a `PASS` line, and ends with "models: 68 as expected, 0 failed, 0 skipped, 0 stopped". The census lines of `PA_Census` and `PA_CensusAligned` are in `.build/formal/tlc/multi-store-protocols/<configuration>/tlc.out`, one `<< "End", ... >>` tuple for each end state, over several lines.

### What was run, in full

Every command was run on machine S from the repository's root, each output captured to a file and read in full. `PYTHONUTF8=1` and `TLA2TOOLS_JAR` were set in the shell, and `PYTHON_CPU_COUNT=8` for the runner's runs, as the environment note below says.

| Command | Result |
|---|---|
| TLC by hand on the first version of `PA_PassRevision.tla`, `PA_OnRead.cfg` on 8 workers, in a scratch directory under the temporary directory | "Model checking completed. No error has been found.", 2,664 generated, 1,764 distinct, depth 7 |
| TLC by hand on the first version's violating configurations and its two census configurations, the census counted by a scratch script | the violations as above, the census "No error has been found" with 31,098 distinct, `OnRead` and `LaterOf` breaking no cell |
| `mise exec '--' python tools/models/ledger-pass-revision/pass_revision_model.py`, read after the first version had run | "the example's table reproduced", and each protocol's counts as its README's table, exit 0 |
| `mise exec '--' python tools/models/ledger-pass-revision/pass_position_model.py` | each rule's counts as its README's table, exit 0 |
| a scratch script importing both Python models, listing the cells each protocol breaks | A breaks none. A' breaks O1 with no crash in (2, 3, second). C, C+ and C++ break O1 in (0, 1, credit), (0, 3, credit), (1, 1, credit), (1, 1, second), (1, 3, credit), (2, 1, second) and (2, 3, second). A' with the position read breaks O3 in 10 cells, 6 with a credit at its stimulus at 2, 4 with a second activation |
| TLC by hand on `X6_*` and `X2A_*`, in the scratch directory, while the models were built | the verdicts in the table above |
| `mise exec '--' python tools/models/check_tlc.py "PA_*" "X6_*" "X2A_*" --heap-mb 2048` | "models: 18 as expected, 0 failed, 0 skipped, 0 stopped", each with "8 worker(s)" or "1 worker(s)" |
| `mise exec '--' python tools/models/check_tlc.py PA_OnRead PA_OnLatestO3 PA_OnLatestO1 --heap-mb 2048` | "models: 3 as expected, 0 failed, 0 skipped, 0 stopped". `PA_OnRead` TLC 01s and wall 3.1 s against 06s and 8.1 s in the first run, `PA_OnLatestO3` 01s and 2.7 s against 05s and 8.5 s, `PA_OnLatestO1` 09s and 11.0 s against 03s and 4.9 s, with the same counts |
| the census count script over the runner's `tlc.out` of `PA_Census` and `PA_CensusAligned` | 4,485 and 2,037 distinct end lines, and the counts of the tables above |
| `mise run check:models-multi-store-runner` | "24 passed in 2.65s" |
| `mise run check:models-multi-store` | "24 passed in 5.24s", then "models: 68 as expected, 0 failed, 0 skipped, 0 stopped", "Finished in 181.94s". Every distinct-state count equals the manifest's. `X1_Applied` took TLC 20s and wall 39.2 s, against 00s and 1.4 s in the manifest, while another session's Maven tests ran |
| `mise exec '--' python tools/writing_rules.py tools/models/multi-store-protocols/README.md` | "writing rules: 0 failure(s), 0 warning(s)" |
| `mise run graph:ask '--' gap ...` twice, and `mise run graph:ask '--' misses --near` | two gaps recorded, as the index report says |
| `mise exec '--' python tools/writing_rules.py docs/developer/validation/MSA-I6.md tools/models/multi-store-protocols/README.md`, last | "writing rules: 0 failure(s), 0 warning(s)" |

### Deliberate non-coverage

- **Variants B, C, C+ and C++ of the Python model** are not modelled one by one. `PerPosting` is one reading of a posting written alone, and its cells are compared with theirs.
- **Behaviour's records written after the ledger's write**, the Python model's arrangement, is not modelled, since which the runtime has is the question below.
- **A pass over two ledgers with a third writer, a claim on another contract, or a dirty read of a draw later compensated.** With two claims on one contract a compensation follows only the other claim's P pass, so no claim decides from a draw that is later compensated. A wider instance of X6 would show whether one does.
- **Both gaps open at once** is not run, since each open gap already breaks a property alone.
- **Liveness in X6.** Every behaviour ends, and a claim that gives up is done, so no temporal property is checked.
- **Wider instances of the new models.** Not run. All 18 are in the base tier, and the largest has 31,098 distinct states.
- **The run on macOS and on Linux.** The one command above is what to run there.

### Doc delta

- The models' README, as above.
- For the coordinator. Protocol A in one ledger holds in a second, independent model, and the comparison with the Python model has five findings, MSAI6-02 to MSAI6-06, none of which changes Protocol A's verdict. A pass over two ledgers holds with both gaps closed, and each open gap breaks it, the first by stranding a claim and the second by a wrong decision. X2's audit flags a decision whose evidence is correct, which TLC printed.

### Index report

- `find a pass that writes two ledgers, each ledger taking a request of its own, saga` answered ADR-A131 at 0.74 at its second addendum of 2026-11-19, PDD-22 at 0.73 and ADR-A48 at 0.68, which names the named saga with a compensation and a detector. `find named saga compensation detector for a write to two stores` answered ADR-A48 at 0.80.
- `find a refusal returns the revision it found and the pass records the revision it started from` answered ADR-A131 at 0.77 at its third addendum, which does not hold the two gaps. Gap recorded against ADR-A131, pointing at `docs/developer/notes/machine-s-brief-2026-11-19.md:52`, the only place that states them. A register entry for the two conditions, or an edge from ADR-A131's second addendum to PDD-22, would carry it.
- `find an audit of a best known read flags a decision whose evidence is correct when a value changes and changes back` answered weakly, STD-336 at 0.70, and is listed by `misses --near`. Gap recorded against ADR-A48, pointing at `tools/models/multi-store-protocols/README.md:601`. An entry for the catalogue's best-known row, with the statement that its audit is not exact, would carry it.
- `mise run graph:ask '--' misses --near` lists that query among the near misses, beside the earlier sessions' queries.

### For the maintainer

- **Where Behaviour's records of a pass are written (MSAI6-02).** (a) In the ledger's one request, as the TLA+ model has it, so no step falls between a pass and its state change. (b) After it, as the Python model has it, where a replay evaluates from the revision before its receipt and, written on the revision read, records what the pass wrote. Under Protocol A both kept O1 and O2 in every cell. BHL-Q1 asks the neighbouring question of what Behaviour records when its request is turned away. It is your decision, and we do not lean.
- **What a claim does when its second pass is refused and it is then not paid.** (a) Compensate its first pass with a pass that restores the draw, as X6 does, the saga row's compensation. (b) Keep its first pass and record a refusal on the second ledger. (c) Order the two passes so the ledger more likely to refuse is written first, which narrows and does not remove the case. We lean to (a), since the claim's rule pays only where both have room, and it is your decision.
- **One position for a pass over two ledgers (MSAI6-06).** (a) Each ledger gives its pass the later of the stimulus's position and that ledger's latest pass's, as modelled, and the two passes may differ. (b) The evaluation reads both ledgers' latest passes with their revisions and gives both passes the later of all three. (c) No rule until a reading by position across ledgers needs one. We do not lean.
- **The reading of the first gap open.** The model reads a refusal that returns nothing as the claim naming the revision it already held. A claim that reads the ledger again instead would not need the returned revision, at the cost of a read and of a further refusal where another write lands in between. Should the port's contract say the refusal returns the revision, as the plan records, or only that the claim must not name a revision it was refused at?
- **The census configurations in the base tier.** `PA_Census` and `PA_CensusAligned` never fail, and their counts are read from TLC's output by a script we did not commit. (a) Keep them as they are, and the README's tables as their record. (b) Commit the count script beside the runner, with a test. (c) Move them out of the manifest. We lean to (a) for this slice, and it is your decision.

## Models B to D and the trace validation, 2026-11-24

**Brief:** [machine S brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md), section 4.4, "The trace validation waits for MSA-I5's exported interpreter", and section 7. The [sketch](../sketches/multi-store-architecture.md)'s section 6 row for MSA-I6, sections 4.6 and 4.14 and MSA-Q17. The [track H plan](../plans/formal-methods-track-h.md)'s row FMH-5, protocol models A to D. The guards are those of [`tools/persistence`](../../../tools/persistence/README.md)'s builders and the [MSA-I4 note](../notes/multi-store/MSA-I4-four-operations-lowered.md), and the IR is MSA-I5's, [`spikes/multi-store-model/`](../../../spikes/multi-store-model/README.md).
**Machine:** machine S, Windows 11, 16 logical cores, 64 GB installed, TLC 2.19 of 08 August 2024 on Java 25.0.2 through mise, as TLC and `java -version` printed, the jar named by `TLA2TOOLS_JAR`, and Isabelle2025-2 named by `FMX_ISABELLE` for the session, its export and its Scala. At most 8 TLC workers, `PYTHON_CPU_COUNT=8`, since another session ran isolation probes on PostgreSQL and Fuseki, with Maven and Jena JVMs, while these runs were made. **Placement:** T0, public. Protocol models and a check, nothing domain-specific.
**Status:** built 2026-11-24, not verified. What this pack reported before stands. FMH-5's models B to D and the trace validation, which its deliberate non-coverage lists, are built here.

### Invariant

Under a store that serialises its writers, each of the four operations takes the same steps in the protocol models as in the IR's `exec`, in every behaviour TLC finds for the instances run, step for step, outcome for outcome and state for state where both hold the state. Under a store that evaluates on a snapshot, the same holds only where the store's conflict detection makes racing writers write a statement in common, and never across a bump of the dataset epoch.

### What changed

- `tools/models/multi-store-protocols/ModelB_AppendForm.tla`, new. The append form under the dataset guard, as `append-event-dataset-guard` is generated, with four isolation levels, a bump of the dataset epoch, a resend and aborted commits sent again. Invariants `OnePerPosition`, `NoLostAppend`, `FencedAppends`.
- `tools/models/multi-store-protocols/ModelC_CreateRace.tla`, new. The first write raced, as `create-if-absent` is generated, or, with `FirstWrite = "PreCreatedRow"`, as a guarded replace of a row created at seq 0. Invariants `OneFirstWrite`, `OneHead`.
- `tools/models/multi-store-protocols/ModelD_KeyClaim.tla`, new. Owners racing for one claim, as `key-claim-write` is generated, and, with `Sentinel`, the patterns guide's P3 counter added. Invariant `OneOwner`.
- 18 configurations, new, all in the `base` tier, each listed below.
- `tools/models/multi-store-protocols/manifest.toml`, an entry for each, a `trace` key on the 18 configurations the trace validation runs, Model A's two among them, and the header's lines for both.
- `tools/models/trace_validation.py`, new. The trace validation, every text call given its encoding.
- `tools/models/TraceReplay.scala`, new. The driver that runs a tree of IR steps through the exported interpreter. It is compiled with the generated Scala and the spike's `replay/Replay.scala`, whose command values, parameters and reading of a state it reuses, and computes nothing the model computes.
- `tools/models/test_trace_validation.py`, new. 8 tests of the dump's reading, the counts, the tree and model B's and D's reading of a step and a state, which need neither Java, TLC nor Isabelle.
- `tools/models/test_check_tlc.py`, the count of `base` entries the manifest test expects, from 68 to 86. No other test changed.
- `mise.toml`, the tasks `check:models-multi-store-traces` and `check:models-multi-store-traces-runner`, which runs the 8 tests and which the first depends on.
- The models' [README](../../../tools/models/multi-store-protocols/README.md), the three modules, the stores they share, their configurations, results and conclusions, the Running section's counts, and a section on the trace validation. [`tools/models/README.md`](../../../tools/models/README.md), its line for the directory.

No existing `.tla` module, no Isabelle theory, no spike file and nothing under `tools/persistence`, `tools/proofs`, `ontology/`, `benchmark/` or `platform/` changed. The trace validation needed no new export, since `Export.thy` already exports `exec_literal` and the four commands. The runner and `check:models-multi-store` are unchanged.

**How the stores are modelled.** Each writer sends one request, its guards in the IR's order. `Atomic` evaluates and writes in one step. The three snapshot levels evaluate the guards and compute the writes in one step and commit them in a later one. Each records the statements a committed transaction deleted and inserted, as a pair of a kind and a value. `SnapshotInsertWW` aborts a commit where a transaction committed since its snapshot wrote a statement it writes, an identical insert counting as a write. `SnapshotDeleteWW` aborts only where both deleted a statement. `SnapshotNoWW` never aborts. These are the cases of TSD-Q4, which asks whether inserting an identical statement conflicts. TSD-73 found Oxigraph on disk losing guarded writes, which `SnapshotNoWW` stands for, and TSD-74 found Jena serialising its writers, which `Atomic` stands for, and two writes of an identical statement not conflicting there. The isolation probes of this slice, run by another session, say which store takes which level.

### The configurations

Each was run through the runner under `--heap-mb 2048`, one at a time, on 8 workers where no error was expected and one where a counterexample was. Diameter is TLC's "depth of the complete state graph search", and for a counterexample the depth when it stopped. The figures are those of the last run, made after the last change to the modules. The last two changes stated the commit's conflict check so that TLC evaluates it as one value rather than generating a successor twice, which lowered the generated counts and left every distinct-state count as before.

| Configuration | Verdict | Distinct states | Generated | Diameter | Peak heap | TLC time | Wall time |
|---|---|---|---|---|---|---|---|
| `ModelB_Atomic` | no error | 2,652 | 5,301 | 14 | 28 MB | 00s | 1.3 s |
| `ModelB_SnapshotDeleteWW` | no error | 7,179 | 17,686 | 25 | 29 MB | 00s | 1.4 s |
| `ModelB_SnapshotDeleteWWBump` | `FencedAppends` violated | 33 | 40 | 5 | 18 MB | 00s | 1.2 s |
| `ModelB_SnapshotInsertWWBump` | `FencedAppends` violated | 33 | 40 | 5 | 18 MB | 00s | 1.2 s |
| `ModelB_SnapshotNoWW` | `OnePerPosition` violated | 19 | 25 | 7 | 18 MB | 00s | 1.2 s |
| `ModelB_SnapshotNoWWLost` | `NoLostAppend` violated | 19 | 25 | 7 | 18 MB | 00s | 1.5 s |
| `ModelC_Atomic` | no error | 37 | 64 | 6 | 18 MB | 00s | 1.3 s |
| `ModelC_SnapshotInsertWW` | no error | 596 | 1,306 | 14 | 18 MB | 00s | 1.4 s |
| `ModelC_SnapshotDeleteWW` | `OneFirstWrite` violated | 12 | 13 | 5 | 15 MB | 00s | 1.2 s |
| `ModelC_SnapshotDeleteWWHead` | `OneHead` violated | 12 | 13 | 5 | 15 MB | 00s | 1.2 s |
| `ModelC_PreCreatedAtomic` | no error | 37 | 64 | 6 | 18 MB | 00s | 1.2 s |
| `ModelC_PreCreatedDeleteWW` | no error | 596 | 1,306 | 14 | 18 MB | 00s | 1.3 s |
| `ModelC_PreCreatedNoWW` | `OneFirstWrite` violated | 12 | 13 | 5 | 15 MB | 00s | 1.2 s |
| `ModelD_Atomic` | no error | 37 | 64 | 6 | 18 MB | 00s | 1.3 s |
| `ModelD_SnapshotInsertWW` | no error | 692 | 1,474 | 14 | 18 MB | 00s | 1.2 s |
| `ModelD_SnapshotDeleteWW` | `OneOwner` violated | 12 | 13 | 5 | 15 MB | 00s | 1.1 s |
| `ModelD_SentinelDeleteWW` | no error | 692 | 1,474 | 14 | 17 MB | 00s | 1.2 s |
| `ModelD_SentinelNoWW` | `OneOwner` violated | 12 | 13 | 5 | 15 MB | 00s | 1.2 s |

Every one fits the base tier's budget of 2 GB, the largest peak 29 MB under a heap of 2,048 MB, and the runner gives each 256 MB. The README's results table has each counterexample.

### The trace validation

**Method.** We chose the smallest form we could show sound. TLC dumps each configuration's whole state graph with each step's action, `-dump dot,actionlabels`, with every invariant but `TypeOK` taken out so that a configuration that violates one is still explored in full. The check reads each step. A store request is the IR's command, `delta_replace` for model A and for model C's row created beforehand, `append_event` for B, `create_if_absent` for C and `key_claim_write` for D, with the parameters the step's writer sent and the outcome the model gave it. It walks the product of the graph and a tree of the IR steps met so far, so every step of every behaviour is a step of the product, and each is checked once for each IR state that reaches it. The tree is run through the exported interpreter in one call of `isabelle scala`, the generated code as generated. After each step the outcome and the state are compared, each state read into the lines both hold. The behaviours are counted from the graph, not enumerated.

**Counts.** 18 configurations, 2,672 nodes of the tree run through the interpreter, each a seed, an IR command or the bump. Every behaviour of every configuration was checked through the product, from 6 behaviours in the smallest to 363,363,336 behaviours of 8,275,348,368 steps in `ModelB_SnapshotDeleteWW`, there by 9,880 checks over 23,001 steps of the product.

| Configuration | Expected | Result | Behaviours | Their steps | Of them store steps | Checks | The IR's outcomes over the checks |
|---|---|---|---|---|---|---|---|
| `ModelA_Atomic` | agree | every step agrees | 90 | 540 | 270 | 79 | `Applied` 42, `Conflict Stale` 36 |
| `ModelA_SnapshotNoWWDetect` | differ | 60 outcomes and 12 states differ | 1,680 | 15,120 | 5,040 | 202 | `Applied` 81, `Conflict Stale` 120 |
| `ModelB_Atomic` | agree | every step agrees | 278,418 | 3,571,950 | 1,925,184 | 4,737 | `Applied` 681, `Duplicate` 1,689, `Refused EpochMismatch` 1,704 |
| `ModelB_SnapshotDeleteWW` | agree | every step agrees | 363,363,336 | 8,275,348,368 | 2,180,180,016 | 9,880 | `Applied` 1,215, `Duplicate` 8,664 |
| `ModelB_SnapshotDeleteWWBump` | differ | 18 outcomes and 10 states differ | 164 | 1,300 | 492 | 108 | `Applied` 34, `Refused EpochMismatch` 48 |
| `ModelB_SnapshotInsertWWBump` | differ | 18 outcomes and 10 states differ | 164 | 1,300 | 492 | 108 | `Applied` 34, `Refused EpochMismatch` 48 |
| `ModelB_SnapshotNoWW` | differ | 2 states differ | 20 | 120 | 40 | 11 | `Applied` 10 |
| `ModelC_Atomic` | agree | every step agrees | 36 | 180 | 144 | 61 | `Applied` 3, `Conflict Exists` 42, `Duplicate` 15 |
| `ModelC_SnapshotInsertWW` | agree | every step agrees | 37,590 | 472,710 | 150,360 | 532 | `Applied` 12, `Conflict Exists` 360, `Duplicate` 159 |
| `ModelC_SnapshotDeleteWW` | differ | 2 outcomes differ | 6 | 24 | 12 | 9 | `Applied` 4, `Conflict Exists` 4 |
| `ModelC_PreCreatedAtomic` | agree | every step agrees | 36 | 180 | 144 | 61 | `Applied` 3, `Conflict Stale` 42, `Duplicate` 15 |
| `ModelC_PreCreatedDeleteWW` | agree | every step agrees | 37,590 | 472,710 | 150,360 | 532 | `Applied` 12, `Conflict Stale` 360, `Duplicate` 159 |
| `ModelC_PreCreatedNoWW` | differ | 2 outcomes differ | 6 | 24 | 12 | 9 | `Applied` 4, `Conflict Stale` 4 |
| `ModelD_Atomic` | agree | every step agrees | 36 | 180 | 144 | 61 | `Applied` 18, `Conflict HeldByOther` 42 |
| `ModelD_SnapshotInsertWW` | agree | every step agrees | 37,590 | 472,710 | 150,360 | 688 | `Applied` 171, `Conflict HeldByOther` 516 |
| `ModelD_SnapshotDeleteWW` | differ | 2 outcomes differ | 6 | 24 | 12 | 9 | `Applied` 4, `Conflict HeldByOther` 4 |
| `ModelD_SentinelDeleteWW` | agree | every step agrees | 37,590 | 472,710 | 150,360 | 688 | `Applied` 171, `Conflict HeldByOther` 516 |
| `ModelD_SentinelNoWW` | differ | 2 outcomes differ | 6 | 24 | 12 | 9 | `Applied` 4, `Conflict HeldByOther` 4 |

The configurations marked to differ are the check's negative controls. Each is a store weaker than the IR's atomic step, and in each the check found the step where the model's store and `exec` part, the shortest behaviour to it printed. In the nine marked to agree no step differs, and every outcome the IR names among the four operations was compared, `Applied`, `Duplicate`, `Conflict Exists`, `Conflict Stale`, `Conflict HeldByOther` and `Refused EpochMismatch`. No disagreement was found where agreement was expected, so the trace validation reports no defect in either the models or the Isabelle model.

**What the evidence says for MSA-Q17.**

- **Steps with no IR command.** A client's read, a store's evaluation against a snapshot, a store's aborted commit and a writer's resend change no store state, and the check asserts that they do not. The bump of the dataset epoch changes the store and the IR has no command for it, so `TraceReplay.scala` writes the new epoch into the IR's state as the entry the append's guard reads. That is the one place the driver edits a state.
- **An outcome the IR lacks.** An aborted commit is sent again, and a writer that gives up is answered `Aborted`, which is not one of the IR's four outcomes. No step compared has it, since an abort writes nothing and is not an IR step.
- **Fields the IR's state lacks.** The models hold two heads on a row, two receipts at one position and two owners of a claim, which an RDF store that misses a conflict writes. The IR keys a receipt by its target, epoch and sequence and holds one head and one owner, so such a state shows in the comparison as a line the model holds and the IR does not. Every disagreement of model C and D is of this kind.
- **Fields the models lack.** The IR holds a row's head and tombstone flag, a receipt's revision and previous head, a claim's revision and digest, the patch log and the aggregate's facts, which models A to D abstract away and the comparison leaves out.
- **What one declared state model would give.** The comparison reads both states into one set of lines, the row's sequence and epoch, receipts by position and transaction, the claims, the events, the dataset epoch and the claim's owners, written by hand in `trace_validation.py` for each model. Option (a) of MSA-Q17 would generate those types into both. The runs say the generated types would need a collection where the IR has a single field, if the protocol models are to state what a weak store writes, and that the transitions would still differ, since the IR has no step between a snapshot and a commit.

**Findings.**

- **MSAI6-07, the dataset guard does not fence a write already evaluated.** On a snapshot store an append evaluated against the epoch before a bump commits after it with the old epoch, whether the store detects a statement both delete or an identical insert as well, since the append writes no statement the bump writes. TLC printed "Invariant FencedAppends is violated" for both, and the trace validation found the IR refusing the same commit, `Refused EpochMismatch`. A store that serialises its writers refused every such append. This is what STD-315, quiescing writers at a bump, is for, now shown by a run.
- **MSAI6-08, the create and the key claim race where an identical insert is no conflict.** `create-if-absent` and `key-claim-write` delete nothing, so on a snapshot store that detects only a statement both delete two creates both commit and two owners claim one key. Where an identical insert is a conflict, the shared statements collide and one writer is aborted and then refused. A row created beforehand at seq 0, `dal:firstWrite dal:PreCreatedRow`, and the sentinel of PAT-05 give racing writers a statement both delete, and with them the weaker detection suffices. So FMH-5's capability field for whether inserting an identical statement is a write-write conflict decides whether these two operations are safe, on a store that does not serialise its writers.
- **MSAI6-09, the append's position on a store with no conflict detection.** Two appends from one snapshot both answer `Applied`, and the model puts both at position 1 where the IR, computing the next position at the commit, puts the second at 2. The outcomes agree and the states differ, so a check of outcomes alone would not have found this store wrong for the append.

### Tests

| ID | Given / When / Then | Level | Pass criterion | Kind |
|---|---|---|---|---|
| I6B-T1 `ModelB_Atomic` | Given three appenders on a serialising store, a bump and a resend, when TLC explores every state, then one receipt per position, a row counting its appends and every append at the epoch in force | L2 | "No error has been found" | positive |
| I6B-T2 `ModelB_SnapshotDeleteWW` | as I6B-T1 on a snapshot store detecting a statement both delete, with no bump | L2 | "No error has been found" | positive |
| I6B-T3 `ModelB_SnapshotDeleteWWBump`, `ModelB_SnapshotInsertWWBump` | Given a snapshot store and a bump, then an append lands after the bump with the old epoch | L2 | "Invariant FencedAppends is violated" | negative |
| I6B-T4 `ModelB_SnapshotNoWW`, `ModelB_SnapshotNoWWLost` | Given a snapshot store with no conflict detection, then two appends take one position and the row loses one | L2 | "Invariant OnePerPosition is violated", "Invariant NoLostAppend is violated" | negative |
| I6C-T1 `ModelC_Atomic`, `ModelC_PreCreatedAtomic` | Given three writers creating one root on a serialising store, in either form, then one first write and one head | L2 | "No error has been found" | positive |
| I6C-T2 `ModelC_SnapshotInsertWW`, `ModelC_PreCreatedDeleteWW` | as I6C-T1 on a snapshot store where an identical insert conflicts, or with the row created beforehand where only a statement both delete does | L2 | "No error has been found" | positive |
| I6C-T3 `ModelC_SnapshotDeleteWW`, `ModelC_SnapshotDeleteWWHead`, `ModelC_PreCreatedNoWW` | Given a create on a store detecting only shared deletes, or the row created beforehand on a store detecting nothing, then two first writes and two heads | L2 | "Invariant OneFirstWrite is violated", "Invariant OneHead is violated" | negative |
| I6D-T1 `ModelD_Atomic`, `ModelD_SnapshotInsertWW`, `ModelD_SentinelDeleteWW` | Given three owners claiming one key on a serialising store, on a store where an identical insert conflicts, or with the sentinel where only shared deletes do, then one owner | L2 | "No error has been found" | positive |
| I6D-T2 `ModelD_SnapshotDeleteWW`, `ModelD_SentinelNoWW` | Given the claim on a store detecting only shared deletes, or with the sentinel on one detecting nothing, then two owners | L2 | "Invariant OneOwner is violated" | negative |
| I6T-T1 | Given the 9 configurations marked to agree, when every behaviour TLC finds is run through the exported interpreter, then every step's outcome and state agree | L3 | each `PASS` "every step agrees, expected to agree" | positive |
| I6T-T2 | Given the 9 configurations marked to differ, then the check finds a step where the model and the IR part, and prints the shortest behaviour to it | L3 | each `PASS` "disagrees, ..., expected to differ" | negative |
| I6T-T3 | Given `TLA2TOOLS_JAR` unset, or no Isabelle from `FMX_ISABELLE`, the formal root or the path, then the check says what it skipped and exits 0 | L1 | "SKIP: TLA2TOOLS_JAR is not set, so no trace was checked. Set it to the TLA+ tools jar", "SKIP: no Isabelle was found from FMX_ISABELLE, the formal root or the path, so no trace was checked. Run `mise run bootstrap:formal-native-isabelle`, or set FMX_ISABELLE", exit 0 | negative |
| I6T-T4 | `tools/models/test_trace_validation.py`, 8 tests: TLC's values and states are read, the dump gives its states, initial state and each step once, behaviours and their steps are counted, the trace configuration keeps `TypeOK` alone, the tree shares a prefix and writes a parent first, and model B and D read a step and a state as the IR does | L0 | "8 passed" | positive |

### One command

From the repository's root, with `TLA2TOOLS_JAR` naming the TLA+ tools jar, and for the trace validation Isabelle installed as `check:proofs` needs it, by `mise run bootstrap:formal-native-isabelle` or with `FMX_ISABELLE` naming it. On macOS and Linux:

```bash
mise run check:models-multi-store -- "ModelB_*" "ModelC_*" "ModelD_*"   # models B to D, among the base tier's 86
mise run check:models-multi-store-traces                                   # the trace validation, 18 configurations
mise run check:models-multi-store-traces -- "ModelB_*"                     # one model's
```

On Windows, in PowerShell, the separator is quoted, as in `mise run check:models-multi-store-traces '--' "ModelB_*"`. A pass of the first prints "models: 18 as expected, 0 failed, 0 skipped, 0 stopped". A pass of the second prints "8 passed", the session's gate, "GATE: pass", a `PASS` line for each configuration, and "traces: 18 as expected, 0 failed, 2,672 interpreter steps". It builds the session if it is not built, which takes Isabelle's time, and runs on demand, not as part of `check`.

### What was run, in full

Every command was run on machine S from the repository's root, each output captured to a file and read in full. `PYTHONUTF8=1`, `TLA2TOOLS_JAR`, `FMX_ISABELLE` and `PYTHON_CPU_COUNT=8` were set in the shell.

| Command | Result |
|---|---|
| TLC by hand on the 18 configurations of models B to D, `-workers 1`, in a scratch directory under the temporary directory, while the modules were written | the verdicts in the table above |
| `mise exec '--' python tools/models/check_tlc.py "ModelB_*" "ModelC_*" "ModelD_*" --heap-mb 2048`, four times | the first, in a terminal another session shared, stopped after `ModelB_SnapshotNoWW` with exit 1 and no message, and that configuration then passed alone. The other three ran in a terminal of our own, each "models: 18 as expected, 0 failed, 0 skipped, 0 stopped", the last after the last change to the modules and its figures those above. Between them the generated counts fell, as the two changes took out successors TLC generated twice, and the distinct counts did not change |
| `mise exec '--' python -m pytest tools/models/test_trace_validation.py -q -p no:cacheprovider` | "8 passed in 0.10s" |
| `mise exec '--' python tools/models/trace_validation.py`, twice while the modules changed | "traces: 18 as expected, 0 failed, 2,672 interpreter steps", each time with the same counts |
| `mise run check:models-multi-store-traces`, after the last change | "8 passed in 0.11s", "GATE: pass" for `multi-store-model` with MM1 to MM11 passed, "isabelle export: exit 0", "isabelle scalac: exit 0", "TraceReplay: exit 0", a `PASS` line for each of the 18 configurations, "traces: 18 as expected, 0 failed, 2,672 interpreter steps", "Finished in 211.53s" |
| `mise exec '--' python tools/models/trace_validation.py ModelA_Atomic` with `TLA2TOOLS_JAR` unset, then with `FMX_ISABELLE` and `LATTICE_FORMAL_ROOT` naming no directory, I6T-T3 | the two `SKIP` lines of I6T-T3, each exit 0 |
| `mise run check:models-multi-store-runner` | "24 passed in 0.39s" |
| `mise run check:models-multi-store`, the base tier | "24 passed in 0.36s", then "models: 86 as expected, 0 failed, 0 skipped, 0 stopped", "Finished in 138.01s". Of the 86 `PASS` lines 40 read "no error" and 46 name a violation, and none says the distinct states differ from the manifest's. Each of models B to D was given 256 MB, its peak at most 22 MB |
| `mise run check:portability` | "portability: 0 problem(s)", then its tests "25 passed in 4.26s", exit 0 |
| `mise run check:catalogue` | "repository catalogue: 22 module(s) and 19 tool package(s) agree with the tree. Bypass scan: 13 known file(s)", exit 0 |
| `mise run graph:ask '--' gap ...` twice, and `mise run graph:ask '--' misses --near` | two gaps recorded, as the index report says |
| `mise exec '--' python tools/writing_rules.py docs/developer/validation/MSA-I6.md tools/models/multi-store-protocols/README.md tools/models/README.md`, last | "writing rules: 0 failure(s), 0 warning(s)" |

### Deliberate non-coverage

- **The isolation probes on PostgreSQL and Fuseki.** Run by another session in this slice, which reports them. The models here take each isolation level as a constant, and the probes say which store has which.
- **Trace validation of X1 to X6 and Protocol A.** Their steps are not commands of the IR, which states the four operations only. A model of the studio's writers, a relay or a pass is held to Isabelle once the IR states those operations.
- **Model A parametrised by boundary strategy, model C covering the composite create, and the capability-record extension,** which FMH-5's row also names. Not built. Model C covers the named-graph create and the first write of a row created beforehand.
- **Wider instances of models B to D.** Not run. All 18 are in the base tier, the largest at 7,179 distinct states, and three writers is the most any has.
- **A store that loses a commit it acknowledged, a writer that crashes, and the dataset guard's absence.** Not modelled. X1 has crashes, and the bump is the only failure of the epoch modelled.
- **Liveness.** Not checked in models B to D. Every behaviour ends, since sends and retries are bounded.
- **One state model declared once, MSA-Q17's option (a).** Not built. The trace validation is the evidence its question asks for, above.
- **The run on macOS and on Linux.** The one command above is what to run there.

### Doc delta

- The models' README and `tools/models/README.md`, as above.
- For the coordinator. FMH-5's models B to D are built, and the trace validation holds models A to D to MSA-I5's exported interpreter, with every step of every behaviour agreeing where the store serialises its writers and where the store's conflict detection makes racing writers share a statement, and disagreeing, as expected, on every weaker store. Three findings, MSAI6-07 to MSAI6-09, and the evidence for MSA-Q17 are above.

### Index report

- `find inserting an identical statement is a write-write conflict on a snapshot store, create race` answered PAT-05 at 0.81, TSD-Q4 of the triple-stores domain at 0.71 and PAT-21 at 0.69. `find two concurrent claims of one key on a store without write-write conflict detection both commit, duplicate audit` answered TSD-Q4 at 0.79, PAT-04 and ADR-A48 at 0.78, PAT-05 at 0.77 and PAT-03 at 0.75. These carried model D's sentinel and the isolation levels.
- `find append event dataset epoch guard concurrent append and epoch bump write skew` answered ADR-A123 at 0.75, OR-Q15 and STD-315 at 0.71, which states MSAI6-07's case as a practice.
- `find trace validation of a model checker trace replayed through the exported interpreter` answered weakly, MSA-Q16 at 0.76 and ADR-A-FM1 and MSA-Q17 at 0.74. Gap recorded against MSA-Q17, pointing at `tools/models/multi-store-protocols/README.md:561`, the section on the trace validation. A capability entry for the check, or an edge from MSA-Q17 to it, would carry it.
- Gap recorded against PAT-05, that models C and D show the create and the key claim racing where an identical insert is no conflict and a row created beforehand or the sentinel restoring them, pointing at `tools/models/multi-store-protocols/README.md:823`. An edge from PAT-05 and TSD-Q4 to model C and D's configurations would carry it.
- `mise run graph:ask -- misses --near` lists none of this part's queries among the near misses, each having answered at 0.74 or above, and lists the two gaps above among the gaps recorded by reading.

### For the maintainer

- **MSA-Q17, one state model.** (a) Declare the closed datatypes once and generate them into Isabelle and TLA+, as the sketch leans, with the comparison of this check reading both. (b) Keep each written by hand, with this check as what holds them together. (c) Widen the IR's state so that it can hold what a weak store writes, two heads, two receipts at one position, two owners, so that the comparison needs no projection. The runs say (a) needs a collection where the IR has a single field, or a projection as here. We lean to (a) with this check kept, and it is your decision.
- **The bump of the dataset epoch has no IR command.** (a) Add one to the IR, which is a change to the theories and a law to prove of it. (b) Keep it outside the IR, written into the state by the driver as here. We lean to (b) until the IR states the epoch authority's operations.
- **An aborted commit has no IR outcome.** The models send the request again and answer `Aborted` when they give up. (a) The port retries an abort inside the adapter and never returns it. (b) The port's outcomes gain one for a write whose fate is unknown, which the caller confirms, as the persistence README's fourth obligation says of a transport failure. We lean to (b), since a confirmation read already classifies an unknown outcome, and it is your decision.
- **MSAI6-08, the create and the key claim on a store where an identical insert is no conflict.** (a) The capability record states whether inserting an identical statement conflicts, and the compiler selects `dal:PreCreatedRow` and a sentinel for the claim where it does not. (b) Such a store is refused for families that create by insert or claim keys, unless it serialises its writers. (c) Keep the generated operations, and rely on the claim's duplicate audit. We do not lean, since the isolation probes may show which stores this concerns.
- **The trace validation in `check`.** It needs Isabelle and takes about three and a half minutes here. (a) Keep it on demand, as `check:multi-store-model-replay` is. (b) Run it in the formal-methods freshness check when a model or a theory changes. We lean to (a).

## The isolation probes on PostgreSQL and Fuseki, 2026-11-24

**Brief:** [machine S brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md), section 4.4, "The probes run on MSA-I13's fixture", and section 4.9, the fixture at PostgreSQL 16.15. The [sketch](../sketches/multi-store-architecture.md)'s section 6, MSA-I6's row, "Each grounded by isolation probes on PostgreSQL and Fuseki", and sections 4.2, 4.3, 4.5 and 4.9.
**Machine:** machine S, Windows 11, 16 logical cores, 64 GB installed. PostgreSQL 16.15 from the PostgreSQL test fixture, psycopg 3.3.6, Python 3.14.7. Apache Jena 5.1.0 and 6.2.0, Fuseki main and TDB2 from Maven, on Java 25.0.2, all through mise. Docker was not started. **Placement:** T0, public. Store probes, nothing domain-specific.
**Status:** built 2026-11-24, not verified.

### Invariant

Every assumption a protocol model makes of a store has a probe on PostgreSQL and on Fuseki over TDB2, with the clients interleaved on purpose, and every probe's row says whether the store did what the model assumes, at each isolation level PostgreSQL offers and at each Jena version. A form that breaks the assumption on purpose, a control, shows the anomaly in every repetition, so a row that shows none means what it says.

### What changed

- `benchmark/store-isolation-probes/`, new, a benchmark under ADR-A124.
  - `check.py`, the eleven assumptions, the expected answer of every row, the PostgreSQL probes, the run of the Jena arm, the verdict and the report. Every text call names its encoding.
  - `test_check.py`, 13 tests: the expectations against the probes and against the rows the Java arm writes, the verdict, the reading of the Jena results, the skip of the Jena arm without Maven, and three PostgreSQL probes on the fixture's server, which skip where it is absent.
  - `pom.xml` and `src/main/java/org/nebularis/lattice/benchmark/isolation/IsolationProbes.java`, the Jena arm, a standalone Maven project outside the platform reactor, as the other JVM benchmarks are. It starts Fuseki main over a TDB2 dataset in a temporary directory on a free loopback port, drives it with concurrent HTTP clients, runs two probes on TDB2 in process, and writes what it observed to `target/jena-<version>/results.json`. It judges nothing.
  - `README.md`, the assumptions, the forms, how the clients are interleaved, the pass criterion and the one command.
- `mise.toml`, the task `check:store-isolation-probes`. It installs the PostgreSQL fixture as its first step, as `check:ledger-supersession-read` does, then runs the tests, then both arms. It is not a dependency of `check`.

The reports, `report.md` and `report.json`, and `target/` are git-ignored by the existing `benchmark/*/report.*` and `**/target/` lines.

**Where the probes live.** `benchmark/`, beside `persistence-store-probes`, and not `spikes/`. ADR-A124 makes `benchmark/` the home of checks that measure and run on demand, each with a `check:<area>-<topic>` task, and the brief asks for one command. A spike has no maintained task. The probes count how often an anomaly appears, which is a measurement, and fail only where a store does other than what is recorded of it, never on time. `mise run check:catalogue` passes with the new directory, since a benchmark's subdirectory needs no catalogue row. PRI-59 says store isolation is verified "with the conformance suite", and whether these probes should move into one is a question below.

**Fuseki without Docker.** The Jena arm runs Fuseki main, `org.apache.jena:jena-fuseki-main`, in its own JVM over `TDB2Factory.connectDataset`, as `benchmark/persistence-replace-forms-jvm` already does. Fuseki main serves the same engine as the Fuseki server jar the studio's stack downloads, without its user interface. Maven resolved Jena 5.1.0 and 6.2.0 from the configured repository. Since each HTTP request is one transaction, the two probes that need a transaction held open, ISO-04 and ISO-06, also run on TDB2 called in process, the transaction engine Fuseki serves. `tools/testing/jena` was not used, since its engine is an in-memory dataset behind one request at a time on standard input, which can neither hold TDB2 nor take two clients at once.

**How the clients are interleaved.** On PostgreSQL one thread drives every connection step by step, each in autocommit with its transactions begun and ended by the probe. A statement that has to wait on another transaction's lock runs on a thread of its own, and the next step is taken once `pg_stat_activity` shows it waiting on a lock, never after a sleep. On Fuseki two clients that must act at the same moment meet at a `CyclicBarrier` and then send, and a step that must follow another is taken once the first has had its reply. In process, transactions on two threads are held apart by barriers. Every repetition writes under keys or IRIs of its own.

### The assumptions, the probes and their results

Each probe states one assumption of a model. The models and configurations named are those whose conclusions rest on it. Every PostgreSQL row ran 50 repetitions on PostgreSQL 16.15, and every Jena row 20 at each of Jena 5.1.0 and 6.2.0, except ISO-02, one run of four writers, and ISO-08's position computed in the request, 5 runs of four clients. A cell gives the repetitions that showed the anomaly. **Bold** marks a row where a store does not keep the assumption in a form a realisation could use.

| Probe | Assumption | Rests on it |
|---|---|---|
| ISO-01 | A guarded compare-and-set request is one atomic step. Of two writers that read one version, one applies and the other changes nothing | `ModelA_Atomic`, X1's guard (`X1_Applied*`), X5's per-step guards, `PA_OnRead*`, `X6_Closed` |
| ISO-02 | The same, for four writers looping to a target | `ModelA_Atomic` with three writers, `X1_AppliedZombie*` |
| ISO-03 | A store answers a command that has a receipt and applies any other in one step | `X1R_Applied`, `X1R_AppliedZombie2`, X1's `Duplicate`, X5's receipts and claims |
| ISO-04 | A request is applied all or nothing, and no reader sees a request that is later rolled back | Model A's atomic step, `X5_Whole*`, `X5_Fenced*`, `PA_*` |
| ISO-05 | Two requests that write the same two rows are each applied whole | X5, `PA_OnRead*` |
| ISO-06 | One read of one store sees a request's effects together or not at all. Two reads may see two states | `X1_Torn*`, X5's plan read in one step, X2's `ReadSetTrue` |
| ISO-07 | A write whose reply has come is seen by the next read from any client | X1's `Duplicate`, X5's read of the receipt, X3's relay |
| ISO-08 | A relay that has published every position up to its mark never finds a lower one committed later | `X2_Watermark*`, `X3_ByPosition*`, `X3_PerStream*` |
| ISO-09 | A fenced store refuses every write that commits after the fence | `X4_Fenced`, `X4_FencedTimeouts` and their wide instances |
| ISO-10 | A refused guarded write can return the version it found, which differs from the one it expected | `X6_Closed`, `X6_StartOpen*`, `PA_OnRead*` |
| ISO-11 | A check of another row and a write made on it are not interleaved with another writer's | `ModelA_Atomic` against `ModelA_SnapshotNoWWDetect`, the catalogue's single-store transaction row |

**PostgreSQL 16.15, 50 repetitions a row.**

| Probe | Form | Read committed | Repeatable read | Serializable | Outcome where the anomaly does not appear |
|---|---|---|---|---|---|
| ISO-01 | guarded | 0 | 0 | 0 | the second refused by its guard (read committed), by a serialization failure (the others) |
| ISO-01 | unguarded, a control at read committed | 50 | 0 | 0 | a serialization failure |
| ISO-02 | guarded, four writers to 200 | 0 | | 0 | one marker at each version, 594 races lost at read committed and 600 at serializable |
| ISO-03 | **receipt checked by an earlier read** | **50** | **50** | 0 | a serialization failure |
| ISO-03 | receipt with a unique key | 0 | 0 | 0 | a unique violation, at serializable a serialization failure |
| ISO-03 | receipt inserted first, `ON CONFLICT DO NOTHING` | 0 | 0 | 0 | the second wrote nothing at read committed, a serialization failure at the others |
| ISO-04 | a reader during a transaction that fails on a division by zero | 0 | | | read uncommitted 0, nothing seen and nothing left |
| ISO-05 | two transactions over rows a and b in opposite orders, each step guarded | 0 | 0 | 0 | one applied both steps, the other ended by a deadlock |
| ISO-06 | **two reads in one transaction** | **50** | 0 | 0 | the two reads agree |
| ISO-06 | two reads in two transactions, a control | 50 | | | |
| ISO-07 | a new transaction | 0 | | | seen |
| ISO-07 | a transaction begun before the commit | 0 | 50 | 50 | seen at read committed. Not seen at the others, as their snapshot is documented to do |
| ISO-08 | **a position from a sequence** | **50** | | **50** | |
| ISO-08 | a position from a counter row the transaction locks | 0 | | | no lower position appeared |
| ISO-09 | **the fence read in the write's transaction** | **50** | **50** | 0 | refused by a serialization failure |
| ISO-09 | the fence row read `FOR SHARE` | 0 | | | the fence waited for the write, and the copy held it |
| ISO-10 | **one statement, the version from its snapshot** | **50** | 0 | 0 | refused by a serialization failure |
| ISO-10 | a locking read before the guard | 0 | | | refused, version 1 returned |
| ISO-10 | the version read by a later statement | 0 | | | refused, version 1 returned |
| ISO-11 | the check by an earlier read | 50 | 50 | 0 | one taken off, the other refused by a serialization failure |
| ISO-11 | the check in the write's statement | 50 | 50 | 0 | the same |

**Fuseki over TDB2 by HTTP, and TDB2 in process, 20 repetitions a row, the same at Jena 5.1.0 and 6.2.0.**

| Probe | Store | Form | 5.1.0 | 6.2.0 | Outcome where the anomaly does not appear |
|---|---|---|---|---|---|
| ISO-01 | Fuseki | guarded | 0 | 0 | one applied, the other wrote nothing |
| ISO-01 | Fuseki | unguarded, a control | 20 | 20 | |
| ISO-02 | Fuseki | guarded, four clients to 40 | 0 | 0 | one marker at each version, 120 races lost at each version |
| ISO-03 | Fuseki | receipt checked by an earlier read, a control | 20 | 20 | |
| ISO-03 | Fuseki | receipt checked in the request | 0 | 0 | applied once |
| ISO-04 | Fuseki | a reader polling while a request of 20,000 triples runs and fails on `CLEAR GRAPH` of a graph that holds nothing | 0 | 0 | HTTP 500 at 5.1.0 and 400 at 6.2.0, nothing left, none of 13,877 reads at 5.1.0 and 5,226 at 6.2.0 saw the marker |
| ISO-04 | TDB2 | a read transaction during a write transaction that aborts | 0 | 0 | nothing seen, during or after |
| ISO-05 | Fuseki | two requests over rows a and b in opposite orders, each step guarded | 0 | 0 | one applied both steps, the other neither |
| ISO-06 | Fuseki | one query, beside ten requests that each move the version and add its receipt | 0 | 0 | every read saw the version and its receipt together, 1,362 reads at 5.1.0 and 800 at 6.2.0 |
| ISO-06 | Fuseki | **two queries**, a control | **20** | **20** | |
| ISO-06 | TDB2 | one read transaction across another thread's commit | 0 | 0 | the two reads agree |
| ISO-06 | TDB2 | two read transactions, a control | 20 | 20 | |
| ISO-07 | Fuseki | a new request from another client | 0 | 0 | seen |
| ISO-08 | Fuseki | a position computed in the request, four clients of five receipts | 0 | 0 | positions 1 to 20, no gap seen in 669 reads at 5.1.0 and 448 at 6.2.0 by a reader polling beside them |
| ISO-08 | Fuseki | a position taken by a request of its own, a control | 20 | 20 | |
| ISO-09 | Fuseki | the fence checked by an earlier read, a control | 20 | 20 | |
| ISO-09 | Fuseki | the fence checked in the write's request | 0 | 0 | refused |
| ISO-10 | Fuseki | the version read after the refusal | 0 | 0 | version 1 read |
| ISO-11 | Fuseki | the check by an earlier read, a control | 20 | 20 | |
| ISO-11 | Fuseki | the check in the request | 0 | 0 | one left on |

**What holds.** On both stores a guard on the row a request writes is one atomic step at every level and version, ISO-01 and ISO-02, so the store side of Model A, X1's guard, Protocol A's pass and each pass of X6 is grounded. A request is all or nothing and no reader saw one that rolled back, ISO-04. A write is seen by the next request, ISO-07. On Fuseki every check made inside the request holds, whether of a receipt, a fence, another row or a position, since TDB2 applies one write transaction at a time, TSD-62 and TSD-74, and the same check made by an earlier query fails every time. On PostgreSQL the same checks hold only in the forms the findings below name.

### Findings

- **MSAI6-10, a receipt checked by a read on PostgreSQL.** X1 with receipts only and X5's claims take "a command with a receipt is answered, any other applied" to be one step. On PostgreSQL a transaction that reads that no receipt exists and then writes the effect and the receipt applied a command delivered twice by two writers in 50 of 50 repetitions at read committed and at repeatable read, since the two inserts touch no common row. It held with a unique key on the receipt's command id, with the receipt inserted first by `ON CONFLICT DO NOTHING`, and at serializable. It weakens `X1R_AppliedZombie2`, where a zombie delivers a command its successor delivers, and X5's configurations with two writers, on a PostgreSQL realisation that checks a receipt or a claim by a read. On Fuseki the check in the request held, 0 of 20 at each version.
- **MSAI6-11, a fence read without a lock on PostgreSQL.** X4's fenced store refuses a write in the step it would apply it. On PostgreSQL a write whose transaction read the fence unset, before the migrator set it and copied, was acknowledged and missing from the copy in 50 of 50 at read committed and at repeatable read. It held where the write's transaction read the fence row `FOR SHARE`, so the fence waited for the write, and at serializable, where the write was refused by a serialization failure. It weakens `X4_Fenced`, `X4_FencedTimeouts` and their six wide instances on a PostgreSQL realisation that reads the fence without a lock below serializable. On Fuseki the fence checked in the write's request held, 0 of 20.
- **MSAI6-12, the revision a refusal returns on PostgreSQL.** X6 with its first gap closed and Protocol A's writer take a refusal to return the revision found. On PostgreSQL at read committed a guarded `UPDATE` in a `WITH` clause, with the version read beside it in the same statement, waited for the other writer's commit and was refused, and returned version 0, the version it expected, in 50 of 50, since the read beside it uses the statement's snapshot. A writer that names the version returned is refused again, which is the first gap open for one more round. A locking read before the guard and a read by a later statement returned version 1, and at repeatable read and serializable the statement was refused by a serialization failure, after which the version is read in a new transaction. It weakens `X6_Closed`, `X6_ClosedTorn`, `X6_ClosedTornCrash`, `X6_ClosedPositions`, `X6_StartOpen`, `X6_StartOpenHalf`, `PA_OnRead` and `PA_OnReadAligned` on a PostgreSQL realisation that returns the version from the guarded statement's own snapshot. On Fuseki an update returns nothing, and the version read after the refusal was 1, 0 of 20.
- **MSAI6-13, positions committed out of order on PostgreSQL.** X2 takes the source to commit at consecutive positions one at a time, in the order of the positions, and leaves late arrival to X3. On PostgreSQL two transactions that took positions from a sequence committed out of order, so a position below the highest already committed appeared afterwards, in 50 of 50 at read committed and at serializable. A position from a counter row the transaction locks did not, 0 of 50. It weakens `X2_Watermark`, `X2_WatermarkStalled`, `X2_Watermark_P4` and `X2_Watermark_P4D4`, where the watermark is the highest committed position, on a PostgreSQL source whose writers take positions from a sequence. It confirms that X3's skip by commit position is reachable there. On Fuseki a position computed in the request kept the order, 0 of 5 runs, and one taken by a request of its own did not, 20 of 20.
- **MSAI6-14, a plan read in several queries.** X5 says "The plan's reads are one step, although the writer makes several." Two queries to Fuseki saw two committed states in 20 of 20 at each version, as did two statements in one read committed transaction on PostgreSQL in 50 of 50, so the studio's writer as built can plan from a state that never existed. One query to Fuseki saw one state in every one of 1,362 reads at 5.1.0 and 800 at 6.2.0, and one transaction at repeatable read or serializable did on PostgreSQL. It weakens every X5 configuration's reading of the design as built. Whether the guards of the request then refuse what a plan from two states would write is not checked by any probe or model.

**Seen and not findings.**

- **ISO-05 on PostgreSQL.** Two requests over the same two rows in opposite orders ended one by a deadlock in every repetition at every level. Each request was whole, so the assumption holds, but the writer receives an error that is neither an application nor a guard's refusal. No X5 instance has two commands that write the same two rows, so no configuration reaches it. A PostgreSQL writer orders its row writes by key or treats a deadlock as a refusal to plan again, which MSA-I8's realisation states.
- **ISO-07 on PostgreSQL.** A transaction at repeatable read or serializable begun before a commit does not see it, as documented. A writer that reads a receipt back reads it in its own request's transaction or in a new one.
- **ISO-11.** A check of another row inside the write's statement does not stop write skew on PostgreSQL below serializable, 50 of 50, while the same check in a SPARQL request does on Fuseki. No configuration guards on a row its request does not write, apart from the fence and the receipt, which MSAI6-10 and MSAI6-11 cover. The capability record of a store states the level at which such a guard holds.
- **`CREATE GRAPH` on TDB2.** A first form of ISO-04 failed its request with `CREATE GRAPH` of the graph its own insert had just filled, without `SILENT`. Fuseki at 5.1.0 and 6.2.0 answered HTTP 204 and kept all 20,001 triples, in 20 of 20, where the specification has `CREATE` of an existing graph fail. The probe was changed to `CLEAR GRAPH` of a graph that holds nothing, which fails as TSD-50 records. This is a candidate finding for the domain, not probed on its own.

### Store findings

- **A finding for the triple-stores domain, not yet filed.** Fuseki over TDB2 keeps a guarded update, a check in the request and a position computed in the request when HTTP clients send at once, and a TDB2 read transaction does not see a commit made after it began. It answers what TSD-74 left unprobed, a guarded update over HTTP to Fuseki, and the HTTP half of TSD-Q4 for Fuseki. A new store finding is recorded in the domain under the domain's identifiers, and `docs/architecture/triple-store-discovery.md` keeps only what the domain holds, so the record is not changed here. The finding in the domain's shape is the appendix at the end of this pack, filed in the domain off machine S, where TSD-Q4's row gains it as a partial answer.
- **PostgreSQL.** No register records how PostgreSQL behaves, and the triple-store record holds triple stores only. MSAI6-10 to MSAI6-13 and the seen items above are PostgreSQL behaviour that MSA-I8's realisation needs. A gap is recorded against PRI-59. Where they go is a question below.

### Tests

| ID | Given / When / Then | Level | Pass criterion | Kind |
|---|---|---|---|---|
| I6S-T1 | Given each PostgreSQL probe, form and level, when two or three connections are interleaved as the probe states, 50 times, then the anomaly appears in no repetition or in every one, as `EXPECTED` says | L3 | `PASS` on each of the 48 PostgreSQL rows | positive and negative |
| I6S-T2 | Given each Fuseki and TDB2 probe and form at Jena 5.1.0 and 6.2.0, when the clients are interleaved, 20 times, then the same | L3 | `PASS` on each of the 20 rows at each version | positive and negative |
| I6S-T3 | Given a control at each store, when it runs, then the anomaly appears every time, so the interleaving happened | L3 | the control rows show m of m | negative |
| I6S-T4 | Given a polling or racing probe, when no read ran beside the writes or no race was lost, then the row fails | L0 | `test_a_probe_that_never_ran_beside_another_client_fails` | negative |
| I6S-T5 | `test_check.py`, 13 tests: every expected row has an assumption and a runner, the Java arm writes exactly the expected Jena rows, the verdict, a missing row listed, the Jena results read, the Jena arm skipped without Maven, and ISO-01, ISO-10 and ISO-11 on the fixture's server | L0, L3 | "13 passed" | positive and negative |
| I6S-T6 | Given no PostgreSQL server or no Maven, when the task runs, then that arm is skipped with the reason and the run exits 0 | L1 | `SKIP postgresql: needs ...` or `SKIP fuseki and tdb2: needs mvn ...` | authored, not run |

### One command

From the repository's root, on Windows, macOS and Linux:

```bash
mise run check:store-isolation-probes
STORE_ISOLATION_QUICK=1 mise run check:store-isolation-probes    # 10 repetitions on PostgreSQL and 5 on Jena
```

On Windows, in PowerShell, a variable is set first, as in `$env:STORE_ISOLATION_QUICK = '1'`. A pass prints the tests' "13 passed", a line for each PostgreSQL row as it runs, then a `PASS` line for each of the 48 PostgreSQL rows and the 20 rows at each Jena version, and ends with the line below and exit 0. Where the PostgreSQL server or Maven is absent, that arm prints a `SKIP` line with the reason and the count of skipped arms rises, still exit 0.

```text
isolation probes: 88 as expected, 0 failed, 0 skipped, <seconds> s
```

### What was run, in full

Every command was run on machine S from the repository's root, each output captured to a file and read in full. `PYTHONUTF8=1`, `PIP_CONSTRAINT` and `PIP_BUILD_CONSTRAINT` were set in the shell.

| Command | Result |
|---|---|
| `mise run work:here` | one session, ours |
| `mise exec '--' mvn -q dependency:get '-Dartifact=org.apache.jena:jena-fuseki-main:6.2.0'` | exit 0, Jena 6.2.0 resolved from the configured repository |
| `mise exec '--' mvn -q -f benchmark/store-isolation-probes/pom.xml compile "-Djena.version=<v>"`, for 5.1.0 and 6.2.0 | exit 0 each, nothing printed |
| `mise exec '--' python benchmark/store-isolation-probes/check.py` with `STORE_ISOLATION_QUICK=1`, `STORE_ISOLATION_ARMS=jena` and `STORE_ISOLATION_JENA_VERSIONS=5.1.0`, a first trial | "isolation probes: 20 as expected, 0 failed, 0 skipped, 16.5 s" |
| the same with `STORE_ISOLATION_ARMS=postgresql`, three trials | the first two, through a PowerShell pipe, printed nothing after ISO-01, as the environment note says. The third, redirected by `cmd`, printed "isolation probes: 48 as expected, 0 failed, 0 skipped, 16.1 s", with 0 races lost in both ISO-02 rows, since the four writers had not started together. The writers now meet at a barrier first, and a racing row with no race lost fails |
| `mise exec '--' python -m pytest benchmark/store-isolation-probes -q -p no:cacheprovider -rs` | "13 passed, 1 warning in 19.41s", "lattice: PostgreSQL tests ran on server version 16.15". The warning is pytest's "Unknown config option: cache_dir", which every run here prints |
| `mise run check:store-isolation-probes` with the trial's `STORE_ISOLATION_QUICK=1` and `STORE_ISOLATION_ARMS=postgresql` left set by mistake | "13 passed", "isolation probes: 48 as expected, 0 failed, 0 skipped, 14.3 s". Not a run of record |
| `mise run check:store-isolation-probes`, in full, with ISO-04's request failing on `LOAD <urn:iso:no-such-document>` | "isolation probes: 88 as expected, 0 failed, 0 skipped, 140.9 s". ISO-04 on Fuseki answered HTTP 500 at 5.1.0 and 400 at 6.2.0. ISO-04 was changed so that its request fails on an operation that can only fail when it runs |
| the Jena arm alone, in a sync terminal shared with another session | stopped by a `KeyboardInterrupt` in `subprocess.communicate`, no result |
| the Jena arm alone, twice, with ISO-04's request failing on `CREATE GRAPH` of the graph it had filled | "isolation probes: 38 as expected, 2 failed, 0 skipped, 138.7 s". Both ISO-04 Fuseki rows read "HTTP 204, 20001 triples left (20)", with 42 and 29 reads that saw the marker, since the request had not failed. ISO-04 was changed to `CLEAR GRAPH` of a graph that holds nothing |
| the Jena arm alone with `STORE_ISOLATION_QUICK=1` | "isolation probes: 40 as expected, 0 failed, 0 skipped, 40.5 s", ISO-04 "refused with HTTP 500, nothing left" at 5.1.0 and "HTTP 400" at 6.2.0 |
| `mise run check:store-isolation-probes`, the run of record, nothing set but `PYTHONUTF8` and the pip constraints | the fixture's bootstrap, "13 passed, 1 warning in 16.15s", a line for each of the 46 PostgreSQL rows that repeat, 88 `PASS` lines, "isolation probes: 88 as expected, 0 failed, 0 skipped, 137.7 s", exit 0. The report's first line reads "Run 2026-11-24: Python 3.14.7 on Windows AMD64. postgresql 16.15, psycopg 3.3.6, jena 5.1.0 jena-tdb2-5.1.0.jar, jena-fuseki-main-5.1.0.jar, java 25.0.2, 52.8 s, jena 6.2.0 jena-tdb2-6.2.0.jar, jena-fuseki-main-6.2.0.jar, java 25.0.2, 43.0 s." The tables above are from this run |
| `mise run check:portability` | "portability: 0 problem(s)", then "25 passed in 2.94s", exit 0 |
| `mise run check:catalogue` | "repository catalogue: 22 module(s) and 19 tool package(s) agree with the tree. Bypass scan: 13 known file(s)", exit 0 |
| `mise exec '--' python tools/writing_rules.py benchmark/store-isolation-probes/README.md .local/msa-i6-probes-section.md` | "writing rules: 0 failure(s), 0 warning(s)" |
| `mise exec '--' python tools/writing_rules.py docs/architecture/triple-store-discovery.md` | "writing rules: 0 failure(s), 0 warning(s)" |
| `mise run graph:ask '--' find ...` four times, `read` of TSD-62, TSD-66, TSD-74, TSD-73, TSD-Q4, TSD-Q13, TSD-44 and TSD-50, `gap` once, `misses --near` | as the index report says. A `read` of the new finding's row answered nothing, since the domain does not hold it |

### Deliberate non-coverage

- **The run on macOS and on Linux.** Not possible on machine S. The one command above is what to run there. The Jena arm resolves Jena from Maven on its first run at each version.
- **The skip of each arm.** Authored, and the Maven skip has a test. The run without the PostgreSQL server installed was not made, since the server is installed in this checkout.
- **Fuseki server jar.** Fuseki main was probed in its own JVM, not the `jena-fuseki-server` jar the studio's stack downloads, which adds a user interface over the same engine.
- **A crash of the store, a network partition, and more than four clients.** The probes are about isolation. Durability across a crash is TSD-66's abandoned request and the studio's own tests.
- **Oxigraph, rdflib and RDF4J.** TSD-73 and TSD-74 cover Oxigraph and Jena in process, and the brief names PostgreSQL and Fuseki.
- **PostgreSQL's `SELECT ... FOR UPDATE SKIP LOCKED`, advisory locks and `NOWAIT`.** No model's step needs them.
- **Trace validation and models B to D.** Other parts of MSA-I6. Models B to D, the append form, the create race and the key claim, appeared in the tree while this was built. Their store assumptions, write-write detection on a delete, on an insert and on a sentinel, are not probed here beyond what ISO-01, ISO-02 and ISO-11 show, that TDB2 applies one write transaction at a time and that PostgreSQL detects a write-write conflict on a row below serializable only where both write the same row.

### Doc delta

- `benchmark/store-isolation-probes/README.md`, new.
- For the coordinator. On both stores a guarded write on the row it writes is one atomic step, so the store side of Model A, X1's guard, Protocol A and X6 is grounded. On Fuseki every check inside a request holds and every check made by an earlier query fails. On PostgreSQL a receipt checked by a read, a fence read without a lock, a refusal's version read from its statement's snapshot and positions from a sequence each break a model's assumption below serializable, MSAI6-10 to MSAI6-13, and each has a form that holds. Several reads see several states on both stores, which X5's abstraction of the plan's reads does not allow for, MSAI6-14.

### Index report

- `find isolation concurrent writers transaction atomic update --kind discovery` answered TSD-44, TSD-Q4, TSD-Q13, TSD-73, TSD-62, TSD-74 and TSD-66, each read in full. TSD-74 says a guarded update over HTTP to Fuseki is not probed, which the finding for the domain now answers.
- `find CREATE GRAPH of a graph that already exists without SILENT succeeds on Jena TDB2 --kind discovery` answered TSD-69 at 0.75 and TSD-50 at 0.74, which records `CREATE GRAPH` of a new graph and not of an existing one.
- `find where a finding about how PostgreSQL behaves under concurrent transactions is recorded` answered weakly, PAT-25, ADR-A33 and TSD-Q4 at 0.72. Gap recorded against PRI-59, pointing at `benchmark/store-isolation-probes/check.py:85`. A register for relational store findings, or a column of the triple-store record for a store that is not a triple store, would carry it.
- `find a probe of store isolation with concurrent clients run on demand, benchmark or spike` answered MEC-81 at 0.74, ADR-A124 at 0.72 and PRI-59 at 0.71, and settled the placement.
- `mise run graph:ask '--' misses --near` lists two reads of the new finding's row among the misses, and the gap against PRI-59.

### For the maintainer

- **Where PostgreSQL store findings are recorded.** (a) A record beside the triple-store record, for example `docs/architecture/relational-store-discovery.md`, with its own identifiers and an entry in `vyvid.toml`. (b) The domain's record widened to stores that are not triple stores, under TSD identifiers. (c) The probes' README and MSA-I8's pack only. We lean to (a), since MSA-I8 and MSA-I10 realise families in SQL, and it is your decision.
- **The Fuseki finding in the domain.** It is filed in the triple-stores domain off machine S, from the appendix, and LATTICE's record gains its pointer once the domain is pinned at a version that holds it, as for TSD-75.
- **A benchmark or a conformance suite.** PRI-59 verifies isolation "with the conformance suite", and the probing skill puts a probe of behaviour into a tool's tests marked `conformance` and a probe of cost into a benchmark. These probes count anomalies and fail where a store changes, which is both. (a) Keep them a benchmark run on demand. (b) Move the expectations into a `check:store-isolation-conformance` task under a test-support package. We lean to (a), since they start a server and a JVM and run for minutes, and it is your decision.
- **The realisation rules the findings imply.** For MSA-I8, on PostgreSQL: a receipt or claim with a unique key or inserted first, a fence row read `FOR SHARE` or a fence checked under serializable, the revision of a refusal read by a locking read or a later statement, and positions from a counter row the transaction locks, or a relay that follows each stream. Should these be stated as rules of the relational realisation, with each probe's row as its evidence, or left to MSA-I8's design?
- **The plan's reads in X5 (MSAI6-14).** (a) Model the plan's reads as several steps, with another writer's commit between them, and run X5 again. (b) Read the plan in one query on Fuseki and one transaction at repeatable read on PostgreSQL, so the abstraction holds. (c) Leave the abstraction, since the guards of the request refuse what a stale plan writes, which no probe or model has shown. We do not lean.

### Environment

- **A PowerShell pipe lost the probes' output.** Two first runs of the PostgreSQL arm through `mise exec '--' python ... 2>&1 | Out-File` stopped printing after ISO-01, and one ended with exit 1 and no traceback. The same run with its output redirected by `cmd /c "... > file 2>&1"` printed every row. A sync terminal shared with another session also sent an interruption to one Jena run (`KeyboardInterrupt` in `subprocess.communicate`). Every run of record was made in a terminal of our own with `cmd /c` redirection.

## Appendix: a finding proposed for the triple-stores domain

### Fuseki over TDB2 keeps a guarded update, a check in the request and a position computed in the request when HTTP clients send at once, and a TDB2 read transaction does not see a commit made after it began

**Evidence:** Observed on Apache Jena 5.1.0 and 6.2.0, Fuseki main in its own JVM over TDB2 on disk in a temporary directory, driven over HTTP/1.1 by Java clients, and TDB2 called in process, on Java 25.0.2 on a 16-core x86-64 machine running Windows 11, 2026-11-24. Not read from Jena's source. Jena documents a dataset's transactions as multiple readers and a single writer, which TSD-62 and TSD-74 rest on. Not measured: the Fuseki server jar, Linux, macOS, and more than four clients.

**Context.** A multi-store protocol model takes a guarded write, a check of a receipt, of a fence or of another row, and the position a write takes to be one step of the store. TSD-74 found that Jena called in process makes a second write transaction wait, and left a guarded update over HTTP to Fuseki unprobed.

**How we found it.** Each probe ran 20 times at each version, with every repetition under IRIs of its own. Two clients that must act at the same moment met at a barrier and then sent, and a step that must follow another was taken once the first had its reply.

1. *A guarded update from two clients.* Both read the version `N`, then sent at once `DELETE { c v N } INSERT { c v N+1 . m_i at N+1 } WHERE { c v N }`, each with its own marker.
2. *The same from four clients looping to a version of 40,* each confirming its marker, as TSD-74's probe does in process.
3. *A check of a triple the request does not write,* made in the request's `WHERE` and, as a control, by an earlier query: a receipt (`FILTER NOT EXISTS`), a fence, and another row (`a on true` taken off only where `b on true`).
4. *A position computed in the request,* `INSERT { r pos ?n } WHERE { { SELECT ((COALESCE(MAX(?q), 0) + 1) AS ?n) WHERE { OPTIONAL { ?x pos ?q } } } }`, from four clients of five receipts each, with a fifth client reading every position as often as it could. As a control, a position taken by a request of its own before the insert.
5. *A read beside a write.* One query reading a version and the highest receipt while another client made ten requests that each move the version and add its receipt, and as a control two queries with one such request between them.
6. *A request that fails,* `INSERT DATA` of a marker and 20,000 triples into a graph `; CLEAR GRAPH <absent>`, while another client read the marker as often as it could.
7. *In process,* a read transaction on one thread across a write transaction on another that commits, and one during a write transaction that aborts, held apart by barriers.

**What the store does.** The same at 5.1.0 and 6.2.0.

| Probe | Result |
|---|---|
| 1, guarded | one applied and the other wrote nothing, 20 of 20. Without the guard both applied, 20 of 20 |
| 2, four clients | one marker at each of 40 versions, none with two, 120 races lost |
| 3, check in the request | held, 20 of 20 for each of the three. By an earlier query, failed 20 of 20 for each |
| 4, position in the request | positions 1 to 20, and no read saw a gap below the highest position in 669 reads at 5.1.0 and 448 at 6.2.0. Taken by a request of its own, a lower position appeared after a higher one, 20 of 20 |
| 5, read beside a write | one query never saw the version apart from its receipt, in 1,362 reads at 5.1.0 and 800 at 6.2.0. Two queries saw them apart, 20 of 20 |
| 6, a request that fails | HTTP 500 at 5.1.0 and HTTP 400 at 6.2.0, nothing left, and none of 13,877 reads at 5.1.0 and 5,226 at 6.2.0 saw the marker |
| 7, in process | the read transaction kept the state it began with across the commit, and saw nothing of the aborted write, during or after, 20 of 20 |

**Why.** Fuseki runs each update request as one write transaction on the dataset, and TDB2 admits one write transaction at a time (TSD-74), so a request's `WHERE` is evaluated on the result of every request committed before it, and a stale guard or a check that has become false matches nothing. A query runs in a read transaction on the last committed state and does not wait for a writer (TSD-62), so one query sees one state and two queries may see two. A position computed in the request is the highest committed plus one, and commits are one at a time, so positions commit in their order. We did not read the source.

**What it means for a project.** A guarded update, a check of another triple, a receipt or a fence, and a position computed from what is stored are safe over HTTP to Fuseki on TDB2 when they are in the request they guard, and unsafe when an earlier query makes them. Several queries are several states. Fuseki 6.2.0 answers an update that fails when it runs with HTTP 400 where 5.1.0 answered 500, so a client that tells a refused request from a server fault by its status reads the two versions differently. This answers the HTTP half of TSD-Q4 for Fuseki on TDB2.

**Reproduce it.** `mise run check:store-isolation-probes` in LATTICE, or `STORE_ISOLATION_ARMS=jena` for this half. Its Maven project starts Fuseki main over a TDB2 dataset on a free port and runs every probe above. A store that keeps these prints 0 for each form in the request and the repetitions for each control.

## Addendum, 2026-11-24: the relay's restart with no position taken

**What changed.** `X3_ReceiptRelay.tla` gains `BeginUnplaced`, `NextUnplaced`, `FairnessUnplaced` and `SpecUnplaced`, and no existing definition changed. Three wide configurations are new, `X3_PerStreamRestartUnplaced_N3`, `_N4` and `_S3`, each its namesake's constants, invariants and property under `SpecUnplaced`. The manifest has 28 wide configurations.

**Why.** `X3_PerStreamRestart_N4` and `X3_PerStreamRestart_S3` have no verdict on any machine. The per-stream relay and R1 to R3 read neither `pos` nor `nextPos`, so the order in which positions were taken multiplies the states and changes no answer.

| ID | Given, when, then | Level | Pass criterion | Kind |
|---|---|---|---|---|
| I6U-T1 | Given `SpecUnplaced` with a restart and three receipts in two streams, when TLC runs, then no error, as `X3_PerStreamRestart_N3` gives | L2 | `PASS`, no error, 88,941 distinct | positive |
| I6U-T2 | The same with four receipts | L2 | `PASS`, no error, 1,840,645 distinct | positive |
| I6U-T3 | The same with three streams of two receipts | L2 | `PASS`, no error, 1,002,485 distinct | positive |

**One command.** `mise run check:models-multi-store -- 'X3_PerStreamRestartUnplaced_*'`, which gives the three heaps of 2,048, 3,136 and 2,368 MB, so a machine of 8 GB skips the second and third unless `--heap-mb 1536` is given and that much is free.

**What was run, on macOS, 8 cores and 8 GB, TLA+ tools 1.7.4.**

| Command | Result |
|---|---|
| `mise run check:models-multi-store -- 'X3_PerStreamRestartUnplaced_*' --heap-mb 1152` | `PASS` for `_N3`, 88941 distinct of 193535 generated, depth 27, TLC 08s, peak heap 983 MB. `STOP` for `_N4`, ran out of its heap at 868,135 distinct. `PASS` for `_S3`, 1002485 distinct of 2105380 generated, depth 27, TLC 01min 31s, peak heap 1150 MB. "models: 2 as expected, 0 failed, 0 skipped, 1 stopped" |
| `mise run check:models-multi-store -- X3_PerStreamRestartUnplaced_N4 --heap-mb 1536` | `PASS`, no error, 1840645 distinct of 4332039 generated, depth 35, TLC 06min 31s, wall 392.4 s, peak heap 1535 MB. "models: 1 as expected, 0 failed, 0 skipped, 0 stopped" |
| `mise run check:models-multi-store-runner` | 27 passed |

**Deliberate non-coverage.** That `SpecUnplaced` and `Spec` agree for the per-stream relay was unchecked when this was written, and the addendum below checks it. The two instances with positions still have no verdict. The new configurations are not run on Windows, and of the other models only X3's were run again after the module changed, `mise run check:models-multi-store -- 'X3_*'` giving its six base configurations as expected.

## Addendum, 2026-11-24: the full relay model implements the one with no position

**What changed.** `X3_Unplaced.tla` is new. It instantiates X3 with `pos` and `nextPos` at their first values and states `Refines`, which is `SpecUnplaced` of that instance, and `UnplacedSteps`, its step half. Two base configurations are new, and the base tier is 88.

| ID | Given, when, then | Level | Pass criterion | Kind |
|---|---|---|---|---|
| I6U-T4 | Given `Spec` with the per-stream relay, two streams of two receipts and one restart, when TLC checks `Refines`, then no error | L2 | `PASS`, no error, 17,863 distinct | positive |
| I6U-T5 | Given `Spec` with the relay by position, when TLC checks `UnplacedSteps`, then it is violated | L2 | `PASS`, action `UnplacedSteps` violated | negative |

**One command.** `mise run check:models-multi-store -- 'X3_Unplaced*'`.

**Deliberate non-coverage.** The refinement is checked at the base instance. That it holds at four receipts or three streams rests on the actions having the same shape at every size. `X3_PerStreamRestart_N4` and `X3_PerStreamRestart_S3` keep their `limit` and have no verdict of their own.
