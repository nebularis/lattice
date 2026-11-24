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
