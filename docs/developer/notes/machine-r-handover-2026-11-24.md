<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Handover to macOS, 2026-11-24: machine S's second bundle of `spi/worktree-s2`

For the session on macOS that takes machine S's last work, called machine R here. Read this first. It says what the bundle holds, how to apply it, what to run again and what a pass prints, what waits on the maintainer, and what machine S learned about its tools. The slices' detail is in their Validation Packs, and the unit's state is in the [status record](../status/multi-store-architecture.md).

## 1. What the bundle holds

The bundle carries `spi/worktree-s2` from its base, `0d3fd302c6ca8633914fa52b4c9f110b9439c6d5`, the commit the maintainer cut the branch at, to the commit that adds this note. Every commit on it was made on machine S, on Windows, by the [handover of 2026-11-23](machine-s-handover-2026-11-23.md), with the maintainer's word on 2026-11-23 to run fully autonomously and commit locally. Nothing was pushed.

| Slice or debt | State | What it delivers | Pack |
|---|---|---|---|
| MSA-F15 | built | a creation under an id with a version row is refused, a deletion delivered twice after a lost tombstone is tested, and `CodecTest` holds the break a probe found in MSA-F14 | [MSA-F15](../validation/MSA-F15.md) |
| MSA-I5 | built | `spikes/multi-store-model/`, the neutral IR in Isabelle on `LatticeShared`, eleven laws proved, the interpreter exported to Scala and replayed against Oxigraph | [MSA-I5](../validation/MSA-I5.md) |
| MSA-I6 | built | models A to D, X1 to X6, Protocol A, the receipts and whole-command models, a manifest of 86 base and 25 wide configurations, one runner for every platform, trace validation against MSA-I5's interpreter, and isolation probes on PostgreSQL and Fuseki | [MSA-I6](../validation/MSA-I6.md) |
| MSA-I7 | built | a PostgreSQL arm in `benchmark/ledger-supersession-read`, correct on machine S, with no figure reported | [MSA-I7](../validation/MSA-I7.md) |
| MSA-I10 | built | the ledger and a promotion family in one mapping vocabulary, `spikes/multi-store-mapping/`, and the note on what a relational place needs | [MSA-I10](../validation/MSA-I10.md) |
| MSA-I14 | building | the model only, `X1_ReceiptsOnly` and `X5_WholeCommand`. The note with options, costs and a recommendation is written off machine S | [MSA-I14](../validation/MSA-I14.md) |
| TD-154 | narrowed | 284 of 286 text calls under `tools/`, `workers/` and `benchmark/` name their encoding, and `check:portability` reports 0 problems | the debt register |
| TD-153 | measured | the shared archive does not explain the stall, an out-of-date testkit jar does, and no fix is built | the debt register |

The mirror on machine S serves `com.apicatalog:titanium-rdfc` 2.0.0 with its dependencies, the one step of MSA-F16 that decides nothing. MSA-F16 still waits on PDD-24 (a).

## 2. Applying it

The maintainer brings the bundle file to machine R. Run from the root of a LATTICE checkout that holds the base commit.

```bash
git bundle verify worktree-s2.bundle
git fetch worktree-s2.bundle spi/worktree-s2:spi/worktree-s2
git switch spi/worktree-s2
mise run bootstrap
```

`git bundle verify` names the base it needs and says the bundle is okay. Where `spi/worktree-s2` is checked out in another worktree, fetch into a new name first, for example `spi/worktree-s2:spi/worktree-s2-r`, and fast-forward from there. The fetch is a fast-forward of the branch the maintainer cut, since nothing else was committed on it. After the runs below, merge it into `spi/multi-store-architecture` with `git merge --no-ff spi/worktree-s2`, never a rebase, as earlier bundles were.

## 3. What to run again, and what a pass prints

Each command is the slice's one command. The figures machine S read are in each pack's "What was run, in full".

| For | Command | A pass prints |
|---|---|---|
| MSA-F15 | `mise run check:config-studio` | pytest `159 passed`, 259 JUnit tests with no failure in the fresh surefire reports, browser `Tests 121 passed (121)` |
| MSA-I5 | `mise run check:proofs -- multi-store-model`, then `mise run check:multi-store-model-replay` | `GATE: pass` with 11 claims, then `CHECK: pass` and `within ten times the RDF realisation's time: first round yes, later rounds yes`, with each engine's version |
| MSA-I6, the models | `mise run check:models-multi-store`, then `mise run check:models-multi-store -- wide` | `models: 86 as expected, 0 failed, 0 skipped, 0 stopped` for the base tier. The wide tier skips with both figures any configuration whose heap does not fit the machine, and the two of X3's relay with a restart stop at 30 minutes |
| MSA-I6, the traces | `mise run check:models-multi-store-traces` | `GATE: pass` and `traces: 18 as expected, 0 failed, 2,672 interpreter steps` |
| MSA-I6, the probes | `mise run check:store-isolation-probes` | `13 passed`, then `isolation probes: 88 as expected, 0 failed, 0 skipped` |
| MSA-I7 | `mise run check:ledger-supersession-read` | `40 passed` with `lattice: PostgreSQL tests ran on server version 16.15`, the `postgresql` lines, and `report written to`. Its figures are the slice's result, and Jena runs where `mise run bootstrap:sparql-testkit` has built its jar |
| MSA-I10 | `mise exec -- python -m pytest spikes/multi-store-mapping -q -p no:cacheprovider` | `15 passed` |
| MSA-I14 | `mise run check:models-multi-store -- "X1R_*" "X5_*"` | `models: 22 as expected, 0 failed, 0 skipped, 0 stopped` |
| TD-154 | `mise run check:portability` | `portability: 0 problem(s)` and `25 passed` |
| the sweep | `mise run check:full-sweep` | 16 of 17 pass. Ontology versions fail on Persistence's spec at 0.23.0 and the substrate at 0.22.0, since the branch defers versioning |

On machine S, on 2026-11-24, the sweep gave 16 of 17 with exactly that failure, `check:persistence` 4816 passed and `check:ontology-catalog` 1482 passed. The models' commands need `TLA2TOOLS_JAR`, and the proofs and replay need Isabelle, found as `check:proofs` finds it. What machine S could not check is each command on macOS and on Linux, the wide tier on a smaller machine, MSA-I7's figures, and Jena in MSA-I7.

## 4. What waits on the maintainer

Each pack ends with its questions and their options. The ones that hold other work are these.

- **MSA-F15's exception for a command's own creation.** Point 5 of ADR-A149's addendum as written broke MSA-F9's verified F9-T1, so a row the command's own first step wrote is excepted. Keep it, take point 5 as written, or leave it to MSA-I14's guard.
- **MSA-I14, which ordering the design must meet.** The design as built reaches TD-166's and TD-169's states only where two writers do not share the stream's order. The note for MSA-I14 is written from this result.
- **Where PostgreSQL store findings are recorded.** MSAI6-10 to MSAI6-14 found five assumptions PostgreSQL keeps only in a stated form or at serializable, and no register holds relational store behaviour.
- **The Fuseki finding.** It is written in the triple-stores domain's shape as the appendix of the MSA-I6 pack, to be filed in the domain, since a new store finding takes the domain's identifier.
- **MSA-I10's question ids.** The sketch's MSA-Q19 and MSA-Q20 and the plan's decisions of 2026-11-18 use the same ids for different questions.
- **TD-153's fix,** between a test kit built on first use (BL-17), JVMs run from a copy of the jar, an archive named by the jar's size and time, and the kit's readers run after `check:java`, and whether TD-31's row goes.

## 5. The index

Gaps recorded while reading, each against the entry that should have carried it, for the change that writes its signpost: PRI-59 (no register for PostgreSQL behaviour), PAT-05 (models C and D), MSA-Q17 (the trace validation), ADR-A48 (the best-known audit), ADR-A131 (the two gaps of a pass over two ledgers), ADR-A125 (an on-demand check missing a test-support package), MSA-Q19 twice (the id collision, and a logical key with no record part), ADR-A-FM4 (TLC's temporary directory), STD-151 (a peak heap read from a GC log), CAP-108 (`tarfile.open` counted as a text open), STD-322 (a JVM's pipe in its native encoding), ADR-A149 (the states the addendum admits need two writers out of order), MEC-56 (the supersession benchmark), and MSA-I5 (which behaviour tests the replay means). `mise run graph:ask -- misses --near` lists them with the near answers.

## 6. What machine S learned about its tools

These are true of Windows and of the tools, not of one machine, and each belongs in a skill or a register when the maintainer agrees.

- **A bare `--` is dropped** when `mise` is the PowerShell function `mise activate pwsh` defines, so every separator in a `mise run` or `mise exec` call is quoted, `'--'`.
- **Windows PowerShell 5.1's `*>` and `>` write UTF-16,** so a log is read with that encoding or written through `cmd /c "... > file 2>&1"`.
- **`Select-Object -First` stops the pipeline it ends,** so a script piped through it can stop before its last step, a commit included.
- **pip 26 applies `PIP_CONSTRAINT` only outside an isolated build.** Where a constraint must hold for a package's build dependencies too, `PIP_BUILD_CONSTRAINT` names the same file.
- **The commit hook's catalogue check parses every Python file in the tree,** an untracked one included, so a file another session is still writing can fail a commit that does not touch it.
- **The knowledge index can answer nothing, or fail with `Corruption`, while another process rebuilds it.** `mise run build:knowledge` again restores it.
- **A studio test that needs the staged profile** fails on a missing `.build/config-studio/...` file until `mise run build:config-studio-assets` has run.
- **JDK 25.0.2 writes a shared archive only where the file is missing,** and Maven's shade rewrites a test kit's jar in place under the JVMs reading it, as TD-153's row says.
- **Two sessions in one terminal interleave,** so a long Maven, TLC or Isabelle run gets a terminal of its own with its output in a file.
