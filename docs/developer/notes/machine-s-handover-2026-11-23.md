<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Handover to machine S, 2026-11-23

For the coordinating agent on machine S. Read this first. It says where your first bundle went, which branch you work on now, what to build in the days machine S has left, what not to touch, and how the second bundle is made. The slices themselves are in the [multi-store brief of 2026-11-19](machine-s-brief-2026-11-19-multi-store.md), by the sections named below.

## 1. What happened to the first bundle

- **It was run again on macOS on 2026-11-20 and merged** into `spi/multi-store-architecture`. Every check your packs report passed there. The full sweep failed only on versions, which the branch defers, and it names Persistence at 0.23.0 as well as the substrate.
- **The maintainer verified MSA-F1 to MSA-F14, MSA-I13 and MSA-I5a** that day.
- **The ledger's session reviewed the rework** and found nothing built differently from what was decided. It probed each slice on 2026-11-23. Three probes found a law that no test holds, in LG-11, LG-25 and LG-32, and LG-30 adds the tests.
- **LG-30 and LG-29 are built on macOS,** and your branch holds them. LG-30 is the review's corrections with the three missing tests. LG-29 adds the supersession and keys an account by its definition's identity. The [ledger's note of 2026-11-23](ledger-to-multi-store-2026-11-23.md) has a table of what a ledger record now holds against what it held at LG-28, in its section 3. ADR-A131's addenda of 2026-11-20 and 2026-11-23 are accepted.
- **The reasoner's tests had never run on your work.** Machine S has no reasoning testkit, so 79 tests skipped in every pack. They pass on macOS.
- **Each of MSA-F1 to MSA-F14 and MSA-I5a was probed on macOS,** one break at a time. Fourteen breaks failed a test and one did not, which section 3 gives to MSA-F15.
- **TD-165 is narrowed and kept, not paid.** MSA-F14's limit stands until PDD-24 is built.

## 2. Your branch from here

Your branch is `spi/worktree-s2`. The maintainer cut it from the merging point and brings it to machine S through the GitHub app, so it is already checked out when you read this. `spi/worktree-s` is merged and closed. Run no `git fetch`, `git pull` or `git push` on the command line, since none of them can reach the remote from machine S.

1. Before your first commit, run `git rev-parse HEAD` and write the commit it prints into the status record's history as the base of the second bundle. Section 5 needs it.
2. `mise run bootstrap`, since the base has moved, then `mise run bootstrap:reasoning-testkit`. If the mirror refuses the testkit's build, say so in each pack, and the run on macOS stands in.
3. `mise run work:here`, then mark the first slice of each lane before its first edit.

Commit on `spi/worktree-s2` alone. A decision you need later arrives the same way, pulled by the maintainer through the app, and is merged into your branch at a pause, never rebased.

## 3. What you build

Both sub-agents work on the multi-store unit. There is no ledger lane on machine S now.

| Lane | In order | Brief |
|---|---|---|
| A, the models and the writer | MSA-F15, then the model for MSA-I14, then the rest of MSA-I6 with the wide instances first | sections 4.8 and 4.4 |
| B, the proofs, the benchmark and Windows | MSA-I5, then MSA-I7, then TD-154 and TD-153, then MSA-I10 | sections 4.3, 4.5 and 4.6 |

- **MSA-F15 also adds one test to `CodecTest`.** A probe on macOS broke MSA-F14's labelling so that a blank node's own quads write itself and every other blank node with one label, and no test failed. The test digests a body in which one blank node names another on a predicate, and a body in which it names itself on the same predicate, and finds the digests apart. Show it fails on that break. It states behaviour, so it holds whatever PDD-24 decides.
- **The wide instances come first within MSA-I6,** since they are the one piece only machine S's memory can run. The runner and the manifest that size a run to the machine, in section 4.4, are part of the same work and are what lets the base tier run anywhere else.
- **MSA-I6's saga row takes one example from the ledger.** An effect on an account its subject does not own, such as a claim on a contract that erodes a programme's aggregate, is a second pass in a second ledger. No addendum of ADR-A131 decides a pass over two ledgers.
- **MSA-I5 imports `LatticeShared` only,** as section 4.3 says, so it does not wait on the ledger's kernel, which LG-35 changes on macOS while you work.
- **Lane A's two slices share `tools/models/multi-store-protocols/`,** which is why they are one lane.
- **MSA-I7 and MSA-I10 are released,** since what a ledger record holds is now built. Read the ledger's note before either, sections 3, 5, 6 and 7.
- **MSA-I7's read is no longer one row.** A balance is read against the latest version in force, so the PostgreSQL arm reads the owner's supersessions for the account's definition beside the running balance on the latest posting. LG-32's figures for the RDF engines are the ones to set its own beside. The note's two warnings on query forms, 40 s against 0.03 s for one and 21 s against 1.7 s for the other, apply to any query you write for the arm's RDF side.
- **MSA-I10 maps every record but one.** Leave the mapping of a supersession until LG-Q58 is answered, which decides whether it names its owner or an account, and say so in the pack. Where a supersession lives in a partitioned store is the sketch's MSA-Q20, which MSA-I10 answers with MSA-Q19.
- **MSA-F16 is not started.** It waits on the maintainer's yes to PDD-24 (a). One step decides nothing and can run now: say in the status record whether your mirror serves `com.apicatalog:titanium-rdfc` 2.0.0.

## 4. What you do not build, and do not touch

- **MSA-I8 is held.** It waits on the maintainer's decision from MSA-I14, and on MSA-I5, MSA-I6, MSA-I7 and MSA-I10. If machine S is gone before then, it is built elsewhere.
- **Nothing under `ontology/ledger/` or `tools/proofs/ledger/`.** The ledger's session builds LG-35 and LG-34 on macOS, which change the kernel, its proofs and the laws of a balance, and add no term. Its side writes nothing under `tools/proofs/shared/`.
- **Neither option of MSA-I14 in the studio's writer.** The model runs the design as built and each option. The maintainer decides before any is built.
- **No version bump.** Both bumps are made at the merge into `main`.

## 5. The second bundle

Make it a day before machine S is decommissioned, on the day the maintainer names, whatever is finished by then. A slice still building stays at `building` on the board with its state said in the status record.

1. Each lane's slice in hand is finished to a commit or left marked, no sub-agent is running and `git status` is empty.
2. Refresh the status record's next action and history, run `mise run build:work` and `mise run build:roadmap`, and commit.
3. `git bundle create worktree-s2.bundle <base>..spi/worktree-s2`, with the base you recorded in section 2
4. `git bundle verify worktree-s2.bundle`, and report its last line, the tip's commit and the count of commits it holds.

The bundle names its base, so it is small and applies only where that base exists. It is fetched here into `spi/worktree-s2`, run again on macOS, and merged into `spi/multi-store-architecture`.

## 6. What to report with it

As section 7 of the brief asks, and these.

- For MSA-F15, the failing test of each of its two cases, and whether a deletion delivered twice needed the attempt's id changed (TD-171).
- For the model of MSA-I14, the trace of the violation in the design as built, and the result for each option.
- For the wide instances, each configuration's peak heap and time, and the run on the smallest budget.
- Each slice left unfinished, and what the next builder needs to pick it up without you.
