<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Handover to machine S, 2026-11-23

For the coordinating agent on machine S. Read this first. It says where your first bundle went, which branch you work on now, what to build in the days machine S has left, what not to touch, and how the second bundle is made. The slices themselves are in the [multi-store brief of 2026-11-19](machine-s-brief-2026-11-19-multi-store.md), by the sections named below.

## 1. What happened to the first bundle

- **It was run again on macOS on 2026-11-20 and merged** into `spi/multi-store-architecture`. Every check your packs report passed there. The full sweep failed only on versions, which the branch defers, and it names Persistence at 0.23.0 as well as the substrate.
- **The maintainer verified MSA-F1 to MSA-F14, MSA-I13 and MSA-I5a** that day.
- **The ledger's session reviewed the rework** and found nothing built differently from what was decided. It probed each slice on 2026-11-23. Three probes found a law that no test holds, in LG-11, LG-25 and LG-32, and LG-30 adds the tests.
- **The reasoner's tests had never run on your work.** Machine S has no reasoning testkit, so 79 tests skipped in every pack. They pass on macOS.
- **TD-165 is narrowed and kept, not paid.** MSA-F14's limit stands until PDD-24 is built.

## 2. Your branch from here

`spi/worktree-s` is merged and closed. Work on a new branch cut from the merging point, so you make no merge and the second bundle holds only new work.

1. Check that `git status` is empty and that `spi/worktree-s` is at `07109dee`, the handoff of the first bundle. If it holds a later commit, stop and tell the maintainer, who decides how it comes across.
2. `git fetch origin`
3. `git switch -c spi/worktree-s2 origin/spi/multi-store-architecture`
4. `mise run bootstrap`, since the base has moved, then `mise run bootstrap:reasoning-testkit`. If the mirror refuses the testkit's build, say so in each pack, and the run on macOS stands in.
5. `mise run work:here`, then mark the first slice of each lane before its first edit.

Commit on `spi/worktree-s2` alone. You cannot push, and nothing here asks you to.

## 3. What you build

Both sub-agents work on the multi-store unit. There is no ledger lane on machine S now.

| Lane | In order | Brief |
|---|---|---|
| A, the models and the writer | MSA-F15, then the model for MSA-I14, then the rest of MSA-I6 with the wide instances first | sections 4.8 and 4.4 |
| B, the proofs and Windows | MSA-I5, then TD-154 and TD-153 | sections 4.3 and 4.6 |

- **The wide instances come first within MSA-I6,** since they are the one piece only machine S's memory can run. The runner and the manifest that size a run to the machine, in section 4.4, are part of the same work and are what lets the base tier run anywhere else.
- **MSA-I6's saga row takes one example from the ledger.** An effect on an account its subject does not own, such as a claim on a contract that erodes a programme's aggregate, is a second pass in a second ledger. Neither of ADR-A131's proposed addenda decides a pass over two ledgers.
- **MSA-I5 imports `LatticeShared` only,** as section 4.3 says, so it does not wait on the ledger's kernel.
- **Lane A's two slices share `tools/models/multi-store-protocols/`,** which is why they are one lane.
- **MSA-F16 is not started.** It waits on the maintainer's yes to PDD-24 (a). One step decides nothing and can run now: say in the status record whether your mirror serves `com.apicatalog:titanium-rdfc` 2.0.0.

## 4. What you do not build, and do not touch

- **MSA-I7, MSA-I8 and MSA-I10 are held.** They name the ledger's records, and two slices still change those records. LG-30 narrows three positions, renames a reason and fixes a first pass at revision 1. LG-29 moves an account's key to its definition's identity and adds the supersession record. MSA-I8 also waits on the maintainer's decision from MSA-I14. If machine S is gone before they land, they are built elsewhere.
- **Nothing under `ontology/ledger/` or `tools/proofs/ledger/`.** The ledger's session builds LG-30, LG-29, LG-35 and LG-34 on macOS and edits the layer's one README. Its side writes nothing under `tools/proofs/shared/`.
- **Neither option of MSA-I14 in the studio's writer.** The model runs the design as built and each option. The maintainer decides before any is built.
- **No version bump.** Both bumps are made at the merge into `main`.

## 5. The second bundle

Make it a day before machine S is decommissioned, on the day the maintainer names, whatever is finished by then. A slice still building stays at `building` on the board with its state said in the status record.

1. Each lane's slice in hand is finished to a commit or left marked, no sub-agent is running and `git status` is empty.
2. Refresh the status record's next action and history, run `mise run build:work` and `mise run build:roadmap`, and commit.
3. `git bundle create worktree-s2.bundle origin/spi/multi-store-architecture..spi/worktree-s2`
4. `git bundle verify worktree-s2.bundle`, and report its last line, the tip's commit and the count of commits it holds.

The bundle names its base, so it is small and applies only where that base exists. It is fetched here into `spi/worktree-s2`, run again on macOS, and merged into `spi/multi-store-architecture`.

## 6. What to report with it

As section 7 of the brief asks, and these.

- For MSA-F15, the failing test of each of its two cases, and whether a deletion delivered twice needed the attempt's id changed (TD-171).
- For the model of MSA-I14, the trace of the violation in the design as built, and the result for each option.
- For the wide instances, each configuration's peak heap and time, and the run on the smallest budget.
- Each slice left unfinished, and what the next builder needs to pick it up without you.
