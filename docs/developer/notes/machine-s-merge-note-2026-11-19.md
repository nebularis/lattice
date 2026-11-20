<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Machine S merge note, 2026-11-19: take the review's updates into `spi/worktree-s`

**For:** the coordinating agent on machine S. **Written on** `spi/multi-store-architecture` at the maintainer's request, after you started work. Your branch is not moved for you. You fetch this branch and merge it into yours, once, at a pause you choose.

## 1. What the merge brings

Documents only, in commits after the one your branch was cut from. No code, no ontology and no proof changes.

| Change | Where to read it |
|---|---|
| five fixes to the studio's writer, MSA-F10 to MSA-F14, from the review of MSA-F1 to MSA-F9 | the [multi-store half of the brief](machine-s-brief-2026-11-19-multi-store.md), section 4.7, and the [plan](../plans/multi-store-architecture.md)'s section on fixes to running code |
| three additions to MSA-I6: a configuration of X1 with receipts and no partition row, an invariant that settles the README on X2's audit, and wider instances | the brief's section 4.4 |
| the models run on every machine, sized to the memory each has | the brief's section 4.4. Read it before MSA-I6 is taken up again |
| MSA-I10 also answers the sketch's MSA-Q19, on a relational place | the brief's section 4.5 |
| TD-165, and a unit that is planned and not yours, `component-administration` | the debt register and its plan |

## 2. When to merge

Your sub-agents are working, and a merge under an agent that is editing loses or tangles its work. So do not merge on reading this. Find a pause.

- **Finish the slice each lane has in hand to a commit.** For the ledger's lane that is the slice now building, with its proofs green. For the second lane it is the slice now building, with its one command run.
- **Start no new slice in either lane** until the merge is committed.
- **Have no sub-agent running** while you merge, and an empty `git status`.
- **Merge before either of these starts,** whichever comes first: the second lane's next slice, and any work on MSA-I6.

## 3. How to merge

1. Fetch, then merge `origin/spi/multi-store-architecture` into `spi/worktree-s`. Merge, never rebase, and never move your branch to this one.
2. Expect conflicts in the multi-store [status record](../status/multi-store-architecture.md), and possibly the ledger's. Join each board row by the row furthest along the ladder, then the later day, so every row you have marked `building` or `built` keeps your state. Keep both sides' new rows and both sides' history lines, in date order. Take this branch's text for the next action and for what the maintainer decides, then add what you have built since.
3. Do not resolve a generated region by hand. For `docs/developer/INDEX.md` and the generated sections of `docs/developer/ROADMAP.md`, take either side and regenerate. For the roadmap's hand-written sections, take this branch's.
4. Run `mise run work:normalise -- --apply`, `mise run work:rename -- --apply`, `mise run build:work` and `mise run build:roadmap`, then `mise run check:identifiers`. A debt or backlog number you assigned since the cut that this branch also assigned is renumbered on your side, since this branch's row was committed first.
5. Commit the merge, with one history line in each status record it touched.

## 4. What changes in your order of work

- **The second lane takes MSA-F10 to MSA-F14 next,** in that order, after the slice it has in hand. The brief's lane table shows them first, which was written before you started. MSA-F10 leads because a writer whose thread has ended holds its partitions.
- **MSA-F14 is built only where MSA-F12's pack shows a studio command's body can hold a blank node.**
- **The ledger's lane is unchanged.**
- **Everything else in the two halves of the brief holds,** the two bundles included.

## 5. What you report

In your next handoff, the commit of the merge, each conflict and how it was joined, and any number you renumbered.
