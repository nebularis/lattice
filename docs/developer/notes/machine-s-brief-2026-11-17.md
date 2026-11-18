<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Machine S brief, 2026-11-17: the multi-store fixes, then the epic's next investigations

**For:** the agent on machine S, Windows 11, which built MSA-I1, MSA-I3, MSA-I4, MSA-I9, MSA-I11 and MSA-I12 of the [multi-store architecture epic](../plans/multi-store-architecture.md) on `spi/sql-backend`. **Written on** `docs/placement-vehicles-structure` at the maintainer's request, after that work was brought over and reviewed.

## What happened to your last bundle

The maintainer brought the eight commits of `spi/sql-backend` over and they were reviewed. Two files carried an absolute path with a user name in it, a Maven path in `spikes/multi-store-stream-probes/scripts/cluster-up.ps1` and a parser's message in `spikes/multi-store-shape-census/results/summary.md`. This repository is public, so the work was brought into `docs/placement-vehicles-structure` as one squashed commit with both files corrected, and from there into `main`. The census now cuts the repository root out of a parser's message, and the script runs Maven through `mise`. The first commit's subject also began with a byte-order mark, which the squash dropped.

**Delete your local `spi/sql-backend` and never push it.** Its history still holds the path. Everything of value in it is on `main`.

## The branch

`spi/multi-store-architecture`, cut from `main` at the squash, which holds this brief. Fetch it and work on it alone, one commit for each mark and one for each slice at least, each with the trailers [GENAI_CONTRIBUTION.md](../../../GENAI_CONTRIBUTION.md) requires and a `Placement:` trailer. Commit locally and never push, as before. The maintainer brings the bundle over.

```bash
git fetch origin
```

```bash
git switch -c spi/multi-store-architecture origin/spi/multi-store-architecture
```

Then `mise run bootstrap`, since `main` moved its pins, and `mise run work:here -- --role build --model <model>`.

## Before every decision, ask the index

Read [AGENTS.md](../../../AGENTS.md) again, and its section on the knowledge index. Ask `mise run graph:ask -- find <the problem in your own words>` before a design choice and before searching the files, read what answers with `read <ID>`, record what reading finds that the index did not with `gap`, and report `misses --near` at the handoff. Open `.claude/skills/lattice-lifecycle/SKILL.md` before the first edit, and mark each slice `building <day>` on the [epic's board](../status/multi-store-architecture.md), committed alone, before touching it.

## Keeping a local workaround out of the commits

The probe script now runs `mise exec -- mvn`. If `mise` cannot run Maven on machine S, for example because a package registry or proxy refuses the download, work around it locally and keep the workaround out of every tracked file.

- Put a local path or setting in an environment variable, in a file under the git-ignored `.local/`, or in your own shell profile, never in a tracked script, a README or a result.
- Before each commit, read `git diff --cached` in full, and run `git grep -nI -e 'C:\\Users' -e 'AppData' -e '/Users/' -- spikes docs` on what is staged. Any machine path, user name or host name in a staged line is removed before the commit.
- A result file a tool writes is checked the same way. Where a tool prints an absolute path, make the tool print a path relative to the repository, as the census now does, rather than editing its output by hand.
- Say in the slice's Validation Pack that a workaround was used and what kind, without its path.

The skill `lattice-constrained-environments` covers a registry that refuses a fetch.

## What the maintainer decided on 2026-11-17

Recorded in the [plan](../plans/multi-store-architecture.md), "Decided by the maintainer, 2026-11-17". In short: the unit's name and prefix stand. MSA-I1's threshold is 80% of subjects under bounded shapes, counted per family chosen for a relational realisation, with closure declared by the mapping. MSA-I6 uses TLA+ with TLC. A resend is answered before a conflict (MSAI4-03). The store computes a sequence's successor and the caller's expected value is the guard (MSAI4-05). The patch log holds the delta as requested, said so (MSAI4-06).

## The fixes, first and in this order

Each is a slice on the epic's board, MSA-F1 to MSA-F6. Each starts with a test that fails on the code as it is, then the fix, then the test passing, one commit for the test and the fix together. None changes a decision record, and where a fix needs a choice that is not obvious, stop and ask.

| Slice | Where | Done when |
|---|---|---|
| MSA-F1, MSAI9-06 | `platform/config-studio-writer`, `StreamWriter.java` | the writer stores, for each partition a batch touched, the offset of the last message it applied, through `Environment.storeOffset(reference, stream, offset)`, which MSAI9-07 showed skips nothing. A unit test in `StreamWriterTest.java` fails on the current `Context.storeOffset()` path and passes after. Then rerun your P3a probe, `p3-before-apply`, against the fixed writer, and record 0 skipped in the slice's pack. This is the one that can lose a confirmed write |
| MSA-F2, MSAI11-05 | the same file's retry loop | a batch the store refuses for a reason a retry cannot change is answered as refused and the partition moves on. Only a store that cannot be reached is retried. Decide with the maintainer how the two are told apart if the store's exceptions do not already say |
| MSA-F3, MSAI11-02 | `platform/config-studio-core`, `writes/Writer.java` | a command whose id has a receipt and whose body's digest differs from the one its claim holds is refused, not answered 200. The digest is already in the store |
| MSA-F4, MSAI12-01 | `contracts/config-studio/amqp-topology.json`, `workers/src/lattice_workers/config-studio-topology.json`, `config_studio_worker.py` and `jobs/Topology.java` | each queue's dead-letter behaviour is stated once, by a field whose name says what it means, and the Python worker and the Java service declare the same broker objects from it. Your comparison in `spikes/multi-store-emitted-topology` reports no difference for it |
| MSA-F5, MSAI4-04 | `tools/persistence/src/persistence/contract.py`, `LOGICAL_KEYS` | the event's logical key names one event, by its IRI or by its operation sequence where `opSeqRequired` holds, and the contract's emission tests say so |
| MSA-F6, MSAI11-01 | the studio's writer tests | for each command that writes several aggregates, a test fails its later guard and shows that nothing a reader acts on remains and that a resend completes the command |

**MSAI11-01 is by design.** [ADR-A149](../../architecture/decisions/ADR-A149-publication-from-the-studio.md) decision 13 orders a command's operations so that a guard failing part way leaves nothing a reader acts on. MSA-F6 tests that claim and changes no code unless a test finds a command for which it does not hold. Cite the decision in your port note, and say there that a unit on the port is all or nothing, so a studio command moved onto the port gives its operations one guard.

The checks for these: `mise run check:config-studio` covers the studio's Python, Java and browser code, `mise run check:workers` the worker, and `mise run check:persistence` the contract. Run each slice's own tests and the task that covers it, and say in the pack which were run and their result.

## Then the investigations the ledger was holding

The ledger's work is on `main`: the target kernel in the ledger README and extracted to `tools/proofs/ledger/Kernel.thy`, 73 proved laws, and the merge policy, which moved `ldg:mergeRule`, `ldg:roundingMethod` and `ldg:residualAllocation` from the account definition to a `ldg:MergePolicy` the definition names. MSA-I2, the read-set census, reads the ledger's examples as they now stand. MSA-I6 has its toolchain. MSA-I5 waits only on the shared types of positions and amounts, which is a question for the maintainer before it starts.

The proof task changed. `mise run check:proofs` now prints `GATE: fail` for a layer whose session did not build, where it printed the claim records as passed. Read the build's own lines, never only the gate's.

## What you do not do

No benchmark. No change to a decision record or a ledger document. Nothing pushed. No `--no-verify` and no skipped hook.

## What you hand back

Each slice's Validation Pack, its row at `built <day>`, the status record's history, the roadmap attended to as AGENTS.md says, and the index report. A short note of anything the maintainer must decide, at the top of the status record's next action.
