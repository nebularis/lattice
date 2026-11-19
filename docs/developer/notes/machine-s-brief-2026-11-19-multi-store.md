<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Machine S brief, 2026-11-19: the multi-store half, the PostgreSQL fixture, MSA-I5a and what follows

**For:** the agent on machine S. **Written on** `spi/multi-store-architecture` at the maintainer's request, by the session that reviews the multi-store work. It is the multi-store half of your next tranche, and the [ledger half](machine-s-brief-2026-11-19.md) is the other. It adds to the briefs of [2026-11-17](machine-s-brief-2026-11-17.md) and [2026-11-18](machine-s-brief-2026-11-18.md), which still hold for asking the index, for committing locally and never pushing, for keeping a local workaround out of every commit, and for what MSA-I5a delivers.

## 1. Your branch, and how work comes back

| | |
|---|---|
| Your branch | `spi/worktree-s`, cut from the merge of `docs/placement-vehicles-structure` into `spi/multi-store-architecture`. Fetch it and work on it alone |
| What it holds | your second bundle, the ledger's branch as of 2026-11-19, both halves of this brief and every text they name |
| What you never do | commit on `spi/multi-store-architecture` or on `docs/placement-vehicles-structure`. The first is a merging point, and the ledger session keeps working on the second |
| A decision you need midweek | arrives as a merge of `spi/multi-store-architecture` into your branch, which the maintainer brings you. Merge it, never rebase |

**Two bundles, of `spi/worktree-s`.**

1. **When the ledger's rework closes.** It carries the rework and every multi-store slice built by then. Do not start MSA-I8 before this bundle is sent and MSA-I6 is closed, so a review finding can still come back to you.
2. **When the tranche closes.**

A bundle carries the branch under its own name, so it is imported with a fetch of `spi/worktree-s` from the file.

## 2. What happened to your last work

- **Your second bundle is on the shared base and not yet reviewed.** MSA-F1 to MSA-F9, MSA-I2's rework and MSA-I6 as built stay off `main` until the maintainer has a verdict on each. The review of the fixes and the models is this session's, and the ledger's rework is reviewed by the ledger session.
- **The LG-27 identifier exception is gone,** since the merge defines the slice.
- **C1 to C3 of your census are decided,** as the ledger half's section 4 says. Section 5 below gives the two models that follow from it.

## 3. Two lanes

The ledger's rework is one lane with one writer. The slices here are the second lane, on your second sub-agent.

| Order | Slice | Waits on |
|---|---|---|
| 1 | MSA-I13, the PostgreSQL test fixture | nothing |
| 2 | MSA-I5a, the shared proof session | nothing. Its agreement lemma lands as section 4 says |
| 3 | MSA-I5, the prover spike, in Isabelle | MSA-I5a |
| 4 | MSA-I6, what is left of it | MSA-I13 for the probes, MSA-I5 for the trace validation |
| 5 | MSA-I10, two families in one mapping vocabulary | the ledger's rework, LG-28 |
| 6 | MSA-I7, the PostgreSQL arm of the ledger benchmark | MSA-I13 and LG-27 |
| 7 | MSA-I8, one ledger family in PostgreSQL behind the port | MSA-I5, MSA-I6, MSA-I7, MSA-I10, and the first bundle sent |
| when the lane waits | TD-154, then TD-153 | nothing |

Each slice keeps the falsifier and the estimate the [sketch](../sketches/multi-store-architecture.md)'s section 6 gives it, has one Validation Pack, and is marked `building` on the [board](../status/multi-store-architecture.md) in a commit of its own before its first edit.

## 4. The slices

### 4.1 MSA-I13, the PostgreSQL test fixture

A test-support package, `tools/testing/postgres/`, beside the Oxigraph and Jena packages (ADR-A125). The isolation probes, MSA-I7 and MSA-I8 all stand on it, so it comes first.

- **It gives a test a clean database** at a pinned PostgreSQL version, and reports the server version it actually ran on.
- **It runs on three machines.** Windows, macOS and a cloud session, since MSA-I7's figures are run off machine S. Assume no Docker on the last two.
- **A test that needs it is skipped with a reason where the server is absent,** through the `requires` package, as the Jena tests are. It never fails a check for want of a server.
- **It is test support only.** Nothing that runs imports it.
- **How the server is provided is a choice you report before building on it.** A container, a binary a bootstrap task installs, and a packaged server each differ in what they need on the three machines. Put the options and what each costs in the pack, build the one that meets the three-machine rule, and say which you chose and why. A new dependency is named in the pack for the maintainer.

**It delivers** the package with its README, a bootstrap or mise task where one is needed, one test that starts the server, writes and reads a row inside a transaction, and stops it, and the catalogue row for the package.

### 4.2 MSA-I5a, the shared proof session

As the brief of 2026-11-18's section 3 has it. One rule is added by the ledger half's section 6. The agreement lemma edits the ledger's proof session, so it lands before LG-25 starts or after the slice then in hand has its proofs green, never beside it. Build the session and its two definitions first, since they touch nothing of the ledger's.

### 4.3 MSA-I5, the prover spike

In Isabelle only. The sketch's section 4.14 and decisions D7 and D8 hold.

- **What it builds.** The neutral IR of guarded commands over logical resources as a datatype, its `exec` function, the laws the sketch names proved of it, and the interpreter exported to Scala.
- **The exported interpreter stays plain** and is used as generated, with no hand edit.
- **The one acceptance criterion.** The exported interpreter replays the histories of the existing behaviour tests within ten times the RDF realisation's time on Oxigraph. Report the two times and the engine version each ran on.
- **There is no budget limit and no fallback.** Where a law resists, say what resists and go on with the next. The cost is examined afterwards from your pack.
- **No Rocq on machine S.** Your images hold Rocq 9.1.1 and the spike's claim records name 9.3.0, so the second formalisation is built elsewhere. To serve it, the session's README states `exec` and each law in prose, exactly enough that someone could write them again without reading the theory.
- **Where it lives.** `spikes/multi-store-model/`, importing `LatticeShared` and never the ledger's session.

### 4.4 MSA-I6, what is left

Your pack lists the saga row, FMH-5's models B to D, the isolation probes on PostgreSQL and Fuseki, and the trace validation against Isabelle. Two models are added.

- **Protocol A in one ledger.** The ledger session modelled a pass and a ledger's revision exhaustively in plain Python, [`tools/models/ledger-pass-revision/`](../../../tools/models/ledger-pass-revision/README.md). Check it again in TLA+ on TLC as a second, independent model. Write it from ADR-A131's second addendum of 2026-11-19 and `ordered-draws.ttl`, and read the Python model only afterwards, to compare the counts. State O1 and O2 as it does, and report each difference between the two models' results as a finding.
- **A pass over two ledgers.** The addendum does not decide it. Each ledger takes a request of its own, so the two gaps of the ledger half's section 4 return. Model it with both gaps closed, the refusal returning the revision it found and the pass recording the revision it started from, and once with each gap open, so the pack shows what each closure buys. This is the saga row's ledger case, and model X1's torn read and torn crash are its starting point.

The probes run on MSA-I13's fixture. The trace validation waits for MSA-I5's exported interpreter.

### 4.5 MSA-I10, MSA-I7 and MSA-I8

They name the ledger's records, so each starts from the reworked vocabulary and never from the one it replaces.

- **MSA-I10** is written after LG-28, on the account definition as a versioned thing.
- **MSA-I7** needs LG-27, for the ledger node and its revision. Build the PostgreSQL arm beside the benchmark's existing backends and show it correct on machine S, against the same expected results the other backends are checked against. Its figures are run elsewhere, so the benchmark has to run on macOS from one command, which the pack gives. Report no figure of your own as the result.
- **MSA-I8** follows the ledger's design as reworked. The write of a pass is the addendum's request, which names the revision the pass was evaluated from, and is refused with the revision found when the ledger has moved. Realise that guard in SQL by the rules of the brief of 2026-11-18's section 4.1.

### 4.6 The two Windows debts

Machine S is where Windows behaviour is verified, so these are named work and not spare-time work. Take them whenever the lane waits on the rework.

- **TD-154.** Give each of the counted calls its encoding, lower the baseline with the command the row names, and run the suites of the files touched on Windows. One commit for each of `tools/`, `workers/`, `packages/` and `benchmark/`. Leave every file under `ontology/ledger/` and the ledger's proofs to the rework's lane, and say in the pack which files you left.
- **TD-153.** Run the measurement its row asks for, a run of `check:ontology-catalog` alone and then beside `check:java` with the JVM start times read, and say whether the shared archive's lock or load alone explains the stall. Propose a fix. Build it only where the measurement supports it.

## 5. What the logical port owes, for MSA-I8 and the next plan

The maintainer decided on 2026-11-19 that the port's half of C1 and C2 is stated by the plan that builds the port. Until then MSA-I8 builds to it as recorded in the [plan](../plans/multi-store-architecture.md). A write names the revision it expects. It returns the revision it produced or, where it is turned away, the revision it found. What the layer above records when its request is turned away is Behaviour's to state.

## 6. What you do not do

- The Rocq formalisation.
- Report MSA-I7's figures as the benchmark's result.
- Change `tools/persistence`, the port or the store SPI beyond what an investigation needs to measure.
- Amend the texts in the sketch's section 8, which waits for the maintainer's answers.
- Mark a decision record Accepted, or a row `verified`.

## 7. What you hand back

For each slice, its Validation Pack with the one command and its results read in full, its board row at `built`, and the index report. For MSA-I13, the options for providing the server and the one chosen. For MSA-I5, the two replay times, each law's state, and the prose statement of `exec` and the laws. For MSA-I6, the counts of both new models beside the Python model's. For TD-154, the baseline before and after.
