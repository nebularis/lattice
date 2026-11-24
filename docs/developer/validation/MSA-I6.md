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
