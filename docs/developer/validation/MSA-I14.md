<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I14, the model of a design that admits no inconsistent state

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), section "A design that admits no inconsistent state, MSA-I14 and MSA-F15", the model bullet. The states are TD-166 to TD-172 of the [technical debt register](../technical-debt.md).
**Brief:** [machine S brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md), section 4.8, and section 4.4's bullet "X1 with receipts and no partition row (MSAI6-01)". [Handover of 2026-11-23](../notes/machine-s-handover-2026-11-23.md), sections 3, 4 and 6.
**Decisions:** [ADR-A149](../../architecture/decisions/ADR-A149-publication-from-the-studio.md) decision 13 and its addendum of 2026-11-19, which the model follows as built.
**Machine:** machine S, Windows, TLA+ tools 1.7.4 (TLC 2.19) on Java 25.0.2 through mise, the jar installed locally and named to the runs by `TLA2TOOLS_JAR`. **Placement:** T0, public. Protocol models, nothing domain-specific.
**Status:** building 2026-11-23, the model built, the note not written.

## Scope

This pack is machine S's part of MSA-I14 only, the model. The design note, with the options, their costs in requests and in contention and a recommendation, is written off machine S by the session that reviews this unit, and the maintainer decides. Neither design is built in the studio's writer, and no Java was edited.

## Invariant

The plan's requirement, as the model states it. After any request commits, and after any crash or redelivery, the store is in a state that some sequence of whole commands gives. No command is answered as applied while part of it is not, and none leaves a row its answer does not account for.

- `WholeCommands` checks the state. The description's revision and listing, the document's revision and liveness and the set of receipts equal what some sequence of distinct commands gives, each applied whole from the start as one writer alone applies it.
- `AnswersAgree` checks the answers. No command answered as not applied has a receipt, then or later.

## What changed

- `tools/models/multi-store-protocols/X1_ReceiptsOnly.tla`, new. X1 with stores that keep a receipt for each command id and no row for the partition, the configuration MSAI6-01 asks for. It extends `X1_SerialisedApply.tla`, which is unchanged, and adds `ReceiptOutcome`, `AtMostOnce`, `NoGap` and `NoGapBehindA`.
- Seven configurations `X1R_*.cfg`, with offsets stored as applied and as received.
- `tools/models/multi-store-protocols/X5_WholeCommand.tla`, new. The studio's writers on one partition, from `Writer` and the generated operations as built. One workspace with a description and one document, a deletion of the document beside a save of the document, a save of the description, or both. The constant `Guard` selects the design as built (`PerStep`), one guard over every row a command writes (`Whole`), that guard with the partition's epoch in every request (`Fenced`), and a variant beyond the brief, `FencedAnswer`. The constant `Delivery` selects writers that each take the stream in order from the stored offset (`Stream`) or that take the commands in any order (`Any`).
- Fifteen configurations `X5_*.cfg`.
- The models' [README](../../../tools/models/multi-store-protocols/README.md): both modules, their constants, properties and abstractions, the 22 configurations, how they are run and measured, every result with its counterexample, and what the results say.

**Where the code left a choice, the model makes one, stated in the README's abstractions.** A batch holds one command. The plan's reads are one step and the request with its read-back is another. The tombstone a deletion makes again after its request is one step, so its first round lands. A document's revision is read through the description, as `StudioOperations.workspace` reads it.

## Tests

Every configuration is run under a heap of 2 GB. States, depth, time and peak heap are in the table under "What was run, in full".

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| I14-T1 `X1R_Applied` | Given X1 with receipts and no partition row, offsets stored as applied, one writer at a time and two crashes, when TLC explores every state, then S1, S2, `AThenB`, `NoGap` and L1 hold | L2 | MSAI6-01 | "No error has been found" | positive |
| I14-T2 `X1R_AppliedZombie2` | as I14-T1 with a successor that may start while its predecessor is alive, up to three incarnations | L2 | MSAI6-01 | "No error has been found" | positive |
| I14-T3 `X1R_Received` | as I14-T1 with offsets stored as received and one crash, checking `AtMostOnce`, S2, `AThenB` and L1 | L2 | MSAI6-01 | "Temporal properties were violated", the invariants holding | negative |
| I14-T4 `X1R_ReceivedGap` | as I14-T3, checking `NoGap` | L2 | MSAI6-01 | "Invariant NoGap is violated" | negative |
| I14-T5 `X1R_ReceivedGapB` | as I14-T3, checking that B holds no command after one that A holds and B lacks | L2 | MSAI6-01, the gap in the second store | "Invariant NoGapBehindA is violated" | negative |
| I14-T6 `X1R_ReceivedRow` | as I14-T3, checking S1 as X1 states it | L2 | MSAI6-01 | "Invariant EachAppliedOnceInEffect is violated" | negative |
| I14-T7 `X1R_ReceivedStep` | as I14-T3, checking `VersionStepsByOne` | L2 | MSAI6-01 | "Action property VersionStepsByOne is violated" | negative |
| I14-T8 `X5_BuiltAnyDoc` | Given the design as built, two writers that take a save of the document and its deletion in any order, when TLC explores, then a state no whole commands give is reached | L2 | `WholeCommands`, TD-166 | "Invariant WholeCommands is violated" | negative |
| I14-T9 `X5_BuiltAnyDesc` | as I14-T8 with a save of the description in place of the save of the document | L2 | `WholeCommands`, TD-169 | "Invariant WholeCommands is violated" | negative |
| I14-T10 `X5_BuiltStream` | Given the design as built, two writers that each take the stream in order from the stored offset, both saves then the deletion, one crash, then every state is one whole commands give | L2 | `WholeCommands` | "No error has been found" | positive |
| I14-T11 `X5_BuiltStreamDelFirst` | as I14-T10 with the deletion first | L2 | `WholeCommands` | "No error has been found" | positive |
| I14-T12 `X5_BuiltStream3` | as I14-T10 with three writers and two crashes | L2 | `WholeCommands` | "No error has been found" | positive |
| I14-T13 `X5_BuiltStreamAnswers` | as I14-T10, checking the answers | L2 | `AnswersAgree`, TD-172's kind | "Invariant AnswersAgree is violated" | negative |
| I14-T14 `X5_WholeAny` | Given one guard over every row a command writes, two writers in any order, both saves and the deletion, a refused command planned again up to three times, then every state is one whole commands give | L2 | `WholeCommands` | "No error has been found" | positive |
| I14-T15 `X5_WholeStream` | as I14-T14 with writers in stream order | L2 | `WholeCommands` | "No error has been found" | positive |
| I14-T16 `X5_WholeStreamAnswers` | as I14-T15, checking the answers | L2 | `AnswersAgree` | "Invariant AnswersAgree is violated" | negative |
| I14-T17 `X5_FencedAny` | as I14-T14 with the partition's epoch in every request | L2 | `WholeCommands` | "No error has been found" | positive |
| I14-T18 `X5_FencedStream` | as I14-T15 with the epoch | L2 | `WholeCommands` | "No error has been found" | positive |
| I14-T19 `X5_FencedStreamAnswers` | as I14-T18, checking the answers | L2 | `AnswersAgree` | "Invariant AnswersAgree is violated" | negative |
| I14-T20 `X5_FencedAnswerAny` | as I14-T17, and a command refused by its own check answered from one read of its rows, the epoch and its receipt, checking the state and the answers | L2 | both | "No error has been found" | positive |
| I14-T21 `X5_FencedAnswerStream` | as I14-T20 with writers in stream order | L2 | both | "No error has been found" | positive |
| I14-T22 `X5_FencedAnswerStream3` | as I14-T21 with three writers and two crashes | L2 | both | "No error has been found" | positive |

## The result for each design

**MSAI6-01, receipts and no partition row.** With offsets stored as applied every property of X1 holds, for one writer at a time and for up to three incarnations with a zombie, and TLC printed the same counts as for X1 with the guard. With offsets stored as received, `AtMostOnce`, `OrderPerKey` and `AThenB` hold, and `EventuallyApplied`, `NoGap`, `NoGapBehindA`, `EachAppliedOnceInEffect` and `VersionStepsByOne` are violated. The expectation holds. Store B applies command 3 after missing command 2, which X1's guard refused, and nothing in the store stops it.

**The design as built.** `WholeCommands` is violated where two writers take the commands in any order, by TD-166's state and by TD-169's. It holds where each writer takes the stream in order from the stored offset, for two writers in either order of the stream and for three writers with two crashes. `AnswersAgree` is violated in stream order.

**One guard over every row a command writes.** `WholeCommands` holds in both deliveries. `AnswersAgree` is violated in stream order, by the same trace as the design as built.

**One guard with the partition's epoch in every request.** `WholeCommands` holds in both deliveries. `AnswersAgree` is violated in stream order, by the writer that lost the partition, which answers a command its own check refuses without sending a request.

**The variant `FencedAnswer`,** which answers such a command from one read of its rows, the epoch and its receipt. Both properties hold, in both deliveries and with three writers in stream order. It is not one of the designs the brief names. We added it to find what the epoch's run left open, and the note may weigh it or not.

## The trace of the violation in the design as built

From `X5_BuiltAnyDoc`, trimmed to the steps that matter. The store starts with the description at revision 1 listing the document, and the document at revision 1.

1. Writer 1 takes the save of the document, reads no receipt, and plans it at document revision 1.
2. Writer 2 starts, takes the deletion, reads no receipt, and plans it at description revision 1 and document revision 1.
3. Writer 1's request applies the save. The document is at revision 2 and the save has its receipt.
4. Writer 2's request applies the description step, so the description is at revision 2 and no longer lists the document. Its tombstone, guarded on document revision 1, writes nothing. The receipt is guarded on the description step's claim, so the deletion has its receipt.

The deletion has a receipt and the document's row is live at revision 2, unlisted. No sequence of whole commands gives that, since a whole deletion tombstones the document. This is TD-166's state. Writer 2 would remove the row in a later request before it answers, and a crash between leaves it until the deletion is delivered again.

From `X5_BuiltAnyDesc`, with a save of the description.

1. Writer 1 plans the save of the description at revision 1.
2. Writer 2 plans the deletion at description revision 1 and document revision 1.
3. Writer 1's request moves the description to revision 2.
4. Writer 2's request writes nothing for the description step, and its tombstone applies. The receipt's guard finds no claim on the description step, so there is no receipt, and writer 2 answers the deletion as not applied.

The description lists a tombstoned document, and no receipt accounts for the tombstone. This is TD-169's first state, a row moved with no receipt.

From `X5_BuiltStreamAnswers`, the answers in stream order.

1. Writer 1 takes the save of the document and plans it.
2. Writer 2 starts at offset 0, takes the same save and reads no receipt.
3. Writer 1's request applies the save and writes its receipt.
4. Writer 2 plans, reads the document at revision 2, and answers the save stale.

`X5_WholeStreamAnswers` prints the same trace. `X5_FencedStreamAnswers` prints it with the writers' parts exchanged. Writer 2 starts, which sets the epoch, and applies the save, and writer 1, which read no receipt before, answers it stale without sending a request.

## One command

From the repository's root, on Windows, macOS and Linux, with `TLA2TOOLS_JAR` naming the TLA+ tools jar, through the runner MSA-I6 added on 2026-11-24, which reads each configuration's expected verdict from the manifest:

```bash
mise run check:models-multi-store -- "X1R_*" "X5_*"
```

In PowerShell quote the separator, `'--'`. The PowerShell lines the model was first run with are below.

```powershell
Set-Location tools/models/multi-store-protocols
foreach ($c in Get-ChildItem X1R_*.cfg) { $c.Name; mise exec '--' java '-Xmx2g' '-Xmn16m' '-XX:+UseParallelGC' '-Xlog:gc' -cp $env:TLA2TOOLS_JAR tlc2.TLC -workers 1 -deadlock -config $c.Name X1_ReceiptsOnly.tla }
foreach ($c in Get-ChildItem X5_*.cfg) { $c.Name; mise exec '--' java '-Xmx2g' '-Xmn16m' '-XX:+UseParallelGC' '-Xlog:gc' -cp $env:TLA2TOOLS_JAR tlc2.TLC -workers 1 -deadlock -config $c.Name X5_WholeCommand.tla }
```

A pass prints, for each of the 22 configurations, the result, the counts and the depth of the README's table. Twelve print "Model checking completed. No error has been found." Ten print the violation the table names, and none other.

## What was run, in full

Run on machine S. The day is 2026-11-23 on the status record and 2026-11-24 by the machine's clock, which TLC printed. Each run's output was captured to a file and read in full, and no warning or exception appeared in any.

**The figures.** Each configuration was run once with `-workers auto` where no error was expected and `-workers 1` where a counterexample was, under `-Xmx2g -Xmn16m -XX:+UseParallelGC -Xlog:gc`. The peak heap is the largest heap in use before a collection that the GC log printed. With the young generation at 16 MB a collection runs at least every 16 MB allocated, so the true peak is at most 16 MB above it. TLC's time is its "Finished in" figure in whole seconds, and the wall time, measured around the command, includes the JVM's start. For a violated invariant the depth is the depth of the search when it stopped. For `X1R_Received` TLC printed no depth, and its last progress line read `Progress(21)`.

| Configuration | Result | States generated | Distinct states | Depth | TLC time | Wall time | Peak heap |
|---|---|---|---|---|---|---|---|
| `X1R_Applied` | no error | 2,411 | 1,479 | 25 | 00s | 2.5 s | 28 MB |
| `X1R_AppliedZombie2` | no error | 216,611 | 50,513 | 41 | 05s | 7.0 s | 114 MB |
| `X1R_Received` | "Temporal properties were violated" | 632 | 397 | not printed | 00s | 2.2 s | 27 MB |
| `X1R_ReceivedGap` | "Invariant NoGap is violated" | 385 | 235 | 14 | 00s | 2.1 s | 15 MB |
| `X1R_ReceivedGapB` | "Invariant NoGapBehindA is violated" | 505 | 312 | 16 | 00s | 2.1 s | 15 MB |
| `X1R_ReceivedRow` | "Invariant EachAppliedOnceInEffect is violated" | 385 | 235 | 14 | 00s | 2.2 s | 15 MB |
| `X1R_ReceivedStep` | "Action property VersionStepsByOne is violated" | 385 | 235 | 14 | 00s | 2.3 s | 15 MB |
| `X5_BuiltAnyDoc` | "Invariant WholeCommands is violated" | 536 | 243 | 11 | 00s | 2.1 s | 16 MB |
| `X5_BuiltAnyDesc` | "Invariant WholeCommands is violated" | 536 | 242 | 11 | 00s | 2.1 s | 16 MB |
| `X5_BuiltStream` | no error | 3,535 | 1,344 | 31 | 00s | 2.3 s | 24 MB |
| `X5_BuiltStreamDelFirst` | no error | 2,786 | 1,080 | 31 | 00s | 2.2 s | 24 MB |
| `X5_BuiltStream3` | no error | 249,875 | 56,474 | 39 | 01s | 3.0 s | 63 MB |
| `X5_BuiltStreamAnswers` | "Invariant AnswersAgree is violated" | 157 | 81 | 10 | 00s | 2.1 s | 16 MB |
| `X5_WholeAny` | no error | 41,580 | 14,308 | 31 | 00s | 2.5 s | 30 MB |
| `X5_WholeStream` | no error | 3,020 | 1,181 | 30 | 00s | 2.2 s | 24 MB |
| `X5_WholeStreamAnswers` | "Invariant AnswersAgree is violated" | 157 | 81 | 10 | 00s | 2.1 s | 16 MB |
| `X5_FencedAny` | no error | 24,745 | 9,335 | 31 | 00s | 2.5 s | 30 MB |
| `X5_FencedStream` | no error | 1,955 | 827 | 30 | 00s | 2.2 s | 24 MB |
| `X5_FencedStreamAnswers` | "Invariant AnswersAgree is violated" | 165 | 84 | 10 | 00s | 2.1 s | 16 MB |
| `X5_FencedAnswerAny` | no error | 18,789 | 7,083 | 29 | 00s | 2.4 s | 30 MB |
| `X5_FencedAnswerStream` | no error | 1,299 | 540 | 24 | 00s | 2.2 s | 18 MB |
| `X5_FencedAnswerStream3` | no error | 55,386 | 14,597 | 35 | 01s | 2.7 s | 33 MB |

Every configuration fits a heap of 2 GB, so all 22 are in the base tier.

| Command | Result |
|---|---|
| the 22 configurations, one run each, as above | the table above, each result the one expected |
| the one command above, every configuration with `-workers 1` | the same 22 results, counts and depths, "Model checking completed. No error has been found." twelve times and the ten violations of the table |
| `mise exec -- python tools/writing_rules.py docs/developer/validation/MSA-I14.md tools/models/multi-store-protocols/README.md` | exit 0, "writing rules: 0 failure(s), 0 warning(s)" |

## Deliberate non-coverage

- **The design note,** with the options' costs in requests and contention, what a sender is told when a command loses three times, what a deletion's receipt then means, where an answer is read from, and what stays outside one guard. Written off machine S, by the session that reviews the unit.
- **The writer itself.** Neither design is built, as the handover's section 4 says. No Java was edited.
- **Scope.** Every result holds for the configuration's constants only. One workspace, one document, two or three commands, two or three writers, at most two crashes, a batch of one command, and the abstractions the README lists.
- **The wide instances of MSA-I6.** More commands and wider windows for X1 to X4, and the runner and manifest that size a run to the machine, are the next work in this lane.
- **Liveness in X5.** Not checked. Whether every command is eventually applied or answered under each design is not stated.
- **Jobs and the promotion maintenance** done in the same request, which the note asks about. Not modelled.

## Doc delta

- The models' README, as above.
- For the coordinator. TD-166 and TD-169's first state are reproduced by TLC, where two writers do not share one order. TD-172's kind of answer, a command answered as not applied although applied, is reproduced in stream order under each of the three designs, and closed by the variant.
- For the note's author. With each writer taking the stream in order, TLC found no state outside `WholeCommands` as built, which narrows the addendum's "each needs a second writer on the partition first" in these configurations.

## Index report

- `mise run graph:ask -- find` with "whole command guard fence epoch", "a studio deletion answered applied before the tombstone lands", "serialised writer fence" and "a deletion whose tombstone lost" each answered "no entry has the facets asked for". `read TD-166` answered "nothing to read for: TD-166", and `exists Receipt` "nothing found". The index answered nothing in this checkout, so every fact here was read from the documents and the code.
- One gap recorded against ADR-A149, at `tools/models/multi-store-protocols/README.md:380`. The states the addendum admits are reached in model X5 only where two writers do not share the stream's order. The addendum's "What it admits" would carry it, as a condition on the second writer.
- `mise run graph:ask -- misses --near` lists this session's seven queries, the six above and one longer form of the first, as misses. The technical debt register's rows would have carried the questions on TD-166 and the deletion, had the index held them.

## For the maintainer

- **Which delivery must the design meet?** As built, TLC reaches TD-166 and TD-169's states only where two writers take the commands in an order the stream does not give them, which the model's `Any` stands for. (a) Treat that as a case the store must meet, for example two partitions carrying one workspace's commands during a repartition, or two writers fed directly as MSA-F6's test does. Then the design as built fails the requirement and either guard passes it. (b) Rely on each writer taking the stream in order from the stored offset, and record it as an assumption the addendum states. Then the design as built meets the state half of the requirement in these configurations, and only the answers fail. We lean to (a), since the store cannot see the order it is given, and it is your decision.
- **Is a second writer's answer within the requirement?** Every design asked for answers a command as not applied after another writer applied it, in stream order. Which reply the service keeps when two arrive for one command is not modelled. If the requirement covers every reply sent, the fence alone does not meet it, and the variant `FencedAnswer` does in these configurations. If only the first reply counts, `AnswersAgree` is stronger than the requirement.
- **A refusal after three losses, then an application.** `AnswersAgree` counts a command answered "send again" after its retries and applied later by another delivery as a disagreement. Is that what the requirement means by an answer that does not account for a row?
- **The abstractions where the code left a choice,** listed in the README. A batch of one command, the plan's reads as one step, and the later tombstone as one step. Each could hide an interleaving the writer has. Are they acceptable for the note, or should a wider model drop one?

## Addendum of 2026-11-24, model X7

Written on macOS, after the maintainer asked for what X5 leaves out before MSA-Q22 and MSA-Q23 are decided. `X7_WorkspaceBatch.tla` is a module of its own, so X5's measured configurations stand unchanged.

**Invariant.** R2, a command answered as applied was applied and one answered as not applied was not, then or later (`AnswersAgree`). R4, the commands take effect in the order the partition gives them (`PartitionOrder`). No command takes effect twice (`AppliedOnce`).

**What it adds to X5.** A creation, a deletion of the workspace, a command with no expected revision, a batch of up to two commands planned together, a sender's resend of the first command, a deletion that clears the workspace's receipts as built, spares its batch's or keeps them all, and a variant with no token whose planning read takes the batch's receipts.

| ID | Given, when, then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| I14-T23 `X7_ClearedBatch` | Given receipts cleared by a deletion as built, one writer and a creation and the deletion in one batch, when TLC explores every behaviour, then the creation is answered as not applied although applied | L2 | `AnswersAgree`, TD-172 | "Invariant AnswersAgree is violated" | negative |
| I14-T24 `X7_SpareBatch` | as I14-T23 with the batch's receipts spared | L2 | `AnswersAgree` | "No error has been found" | positive |
| I14-T25 `X7_SpareResend` | as I14-T24 with a resend of the creation after the deletion and one crash | L2 | `AnswersAgree`, MSA-Q23 (a) | "Invariant AnswersAgree is violated" | negative |
| I14-T26 `X7_SpareResendToken` | as I14-T25 with the token and its read, a command between, three writers and two crashes | L2 | `AnswersAgree`, MSA-Q23 (a) | "Invariant AnswersAgree is violated" | negative |
| I14-T27 `X7_ClearedRedelivery` | Given receipts cleared, the token and its read, batches of one, three writers and two crashes and no resend, then a redelivery after the deletion answers a command as not applied | L2 | `AnswersAgree` | "Invariant AnswersAgree is violated" | negative |
| I14-T28 `X7_KeptResend` | as I14-T25 with every receipt kept | L2 | `AnswersAgree`, `PartitionOrder`, MSA-Q23 (b) | "No error has been found" | positive |
| I14-T29 `X7_OrderNoToken` | Given no token, three commands with no expected revision, three writers, two crashes and one more plan of a refused batch | L2 | `PartitionOrder`, `AnswersAgree`, MSA-Q22 (a) | "No error has been found" | positive |
| I14-T30 `X7_OrderNoTokenNoRetry` | as I14-T29 with a refused batch never planned again | L2 | `PartitionOrder` | "Invariant PartitionOrder is violated" | negative |
| I14-T31 `X7_OrderTokenNoRetry` | as I14-T30 with the token | L2 | `PartitionOrder`, `AnswersAgree`, MSA-Q22 (b) | "No error has been found" | positive |
| I14-T32 `X7_OrderNoTokenCreate` | as I14-T29 with a creation, a command, a deletion and a resend, three plans | L2 | `PartitionOrder` | "No error has been found" | positive |
| I14-T33 `X7_AnswersNoToken` | as I14-T32, checking the answers | L2 | `AnswersAgree` | "Invariant AnswersAgree is violated" | negative |
| I14-T34 `X7_AnswersToken` | as I14-T33 with the token in the request alone | L2 | `AnswersAgree` | "Invariant AnswersAgree is violated" | negative |
| I14-T35 `X7_AnswersRead` | as I14-T33 with no token and a planning read that takes the receipts, one more plan | L2 | `AnswersAgree`, `PartitionOrder`, MSA-Q22 (c) | "No error has been found" | positive |
| I14-T36 `X7_AnswersReadNoRetry` | as I14-T35 on three commands with no expected revision, a refused batch never planned again | L2 | both | "No error has been found" | positive |
| I14-T37 `X7_All` | Given the token with its read and every receipt kept, a creation, a command, a deletion and a resend, three writers and two crashes | L2 | both, MSA-Q22 (b) with MSA-Q23 (b) | "No error has been found" | positive |

**One command.**

```bash
mise run check:models-multi-store -- "X7_*"
```

A pass ends `models: 15 as expected, 0 failed, 0 skipped, 0 stopped`. The figures of each run are in the models' README.

**What the results say, for these constants only.**

- **MSA-Q23.** Receipts cleared as built answer a creation as not applied in the batch that deletes its workspace, with one writer, which is TD-172. They also answer a redelivered command so with the token. Sparing the batch closes TD-172's case and leaves a sender's resend answered both ways. Keeping every receipt shows no error.
- **MSA-Q22.** With each writer taking the stream in order from the stored offset, the order held with no token wherever a refused batch is planned again at least once. It broke with no token where a refused batch is answered at once, and held there with the token. So in this delivery the token is not what keeps the order. The answers disagreed with no token and with the token in the request alone, as in X5, and agreed where the planning read takes the receipts, with the token or without.

**Deliberate non-coverage.** The workspace is one aggregate, so a creation or a deletion over a part and the description in a batch is not modelled, and X5 stays the evidence on a command over two aggregates. A delivery outside the stream's order is not modelled here. A command refused by its own check and applicable later, for example one sent before its workspace's creation, is in no script. Retention of receipts, the patch log (TD-180), jobs (TD-181), promotions and the broker are not modelled, and liveness is not checked. Not run on Windows.

**For the maintainer.** MSA-Q22 has a third option the note did not have, (c) of the sketch. Whether it replaces the token rests on the question above of which delivery the design must meet.

## Addendum of 2026-11-24, the cases left unmodelled

Written on macOS, after the maintainer asked for the cases the addendum on model X7 lists as not covered. Two changes to existing modules and two new modules, so the configurations measured before stand, each of the fifteen of `X7_*` and of `X5_*` giving the same distinct states with the new constants set. `X7_WorkspaceBatch.tla` gains `Delivery`, a script `SetCreate` and a fair specification. `X5_WholeCommand.tla` gains the guard `WholeAnswer`, the patch log's variable and the invariant `LogKept`, and a fair specification. `X8_BatchParts.tla` is X7 with a part beside the description. `X9_JobUpdate.tla` is the rule that a succeeded job stays succeeded, written from `Writer.jobUpdate` in `platform/config-studio-core`.

**Invariant.** As in the addendum above, and in addition that a live, listed document keeps its patch log (`LogKept`), that the description and the part are both absent, live or gone (`WholeCommands` in X8), that no save of the part takes effect after the deletion (`NoSaveAfterDel`), that a job once succeeded is never failed (`SucceededStays`), and that where the last writer to start stays alive every command is eventually answered (`EventuallyAnswered`, a temporal property run under weak fairness on each writer's actions but its crash).

| ID | Given, when, then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| I14-T38 `X7_AnyWholeAnswer` | Given a start from any position of the stream, a creation, a change and a deletion with a resend, no token and a planning read that takes the receipts, two writers and one crash, when TLC explores every behaviour, then a change answered as not applied by a writer that took it alone applies in the batch of the writer that took the creation with it | L2 | `AnswersAgree` | "Invariant AnswersAgree is violated" | negative |
| I14-T39 `X7_AnyFencedAnswer` | as I14-T38 with the token and its read | L2 | `AnswersAgree`, MSA-Q22 (b) | "Invariant AnswersAgree is violated" | negative |
| I14-T40 `X7_AnyWhole` | as I14-T38 with no planning read of receipts | L2 | `AnswersAgree` | "Invariant AnswersAgree is violated" | negative |
| I14-T41 `X7_AnyFencedAnswerOrder` | as I14-T39, checking the order | L2 | `PartitionOrder` | "No error has been found" | positive |
| I14-T42 `X7_AnyFencedAnswerOrderSets` | Given the token and its read, a start from any position, three changes that carry no expected revision on a live workspace, two writers and one crash, then the changes take effect out of the stream's order | L2 | `PartitionOrder`, MSA-Q22 | "Invariant PartitionOrder is violated" | negative |
| I14-T43 `X7_RefusedThenApplies` | Given a change sent before its workspace's creation, then the creation, then the change again under its first id, no token, one writer and no crash, then the change is answered as not applied and then applies | L2 | `AnswersAgree` | "Invariant AnswersAgree is violated" | negative |
| I14-T44 `X7_RefusedThenAppliesToken` | as I14-T43 with the token and its read | L2 | `AnswersAgree` | "Invariant AnswersAgree is violated" | negative |
| I14-T45 `X7_RefusedThenAppliesBatch` | as I14-T43 with the three deliveries in one batch | L2 | `AnswersAgree` | "Invariant AnswersAgree is violated" | negative |
| I14-T46 `X7_LiveWholeAnswer` | Given the planning read that takes the receipts, a creation, a change and a deletion with a resend, two writers in stream order and one crash, weak fairness on each writer's actions but its crash, then where the last writer to start stays alive every command is answered | L2 | `EventuallyAnswered` | "No error has been found" | positive |
| I14-T47 `X7_LiveFencedAnswer` | as I14-T46 with the token | L2 | `EventuallyAnswered` | "No error has been found" | positive |
| I14-T48 `X5_BuiltLog` | Given the design as built, each writer taking the stream in order, both saves and the deletion, two writers and one crash, then a live, listed document keeps its patch log | L2 | `LogKept`, TD-180 | "No error has been found" | positive |
| I14-T49 `X5_BuiltLogAny` | as I14-T48 with each writer taking every command in any order, then a deletion planned before both saves applied drops the log of a live document | L2 | `LogKept`, TD-180 | "Invariant LogKept is violated" | negative |
| I14-T50 `X5_WholeLog` | as I14-T48 with one guard over every row a command writes, the log removed only with the command's receipt | L2 | `LogKept` | "No error has been found" | positive |
| I14-T51 `X5_WholeAnswerStream` | Given one guard and no epoch, a command refused by its own check answered from a read that also reads its receipt, both saves and the deletion in stream order, two writers and one crash | L2 | `WholeCommands`, `AnswersAgree`, `LogKept` | "No error has been found" | positive |
| I14-T52 `X5_WholeAnswerAny` | as I14-T51 with every command taken in any order | L2 | `WholeCommands`, `AnswersAgree`, `LogKept` | "No error has been found" | positive |
| I14-T53 `X5_WholeAnswerAny3` | as I14-T52 with three writers and two crashes | L2 | `WholeCommands`, `AnswersAgree`, `LogKept` | "No error has been found" | positive |
| I14-T54 `X5_LiveWholeAnswer` | Given the guard of I14-T51, weak fairness on each writer's actions but its crash, then where the last writer to start stays alive every command is finished | L2 | `EventuallyAnswered` | "No error has been found" | positive |
| I14-T55 `X5_LiveFencedAnswer` | as I14-T54 with the epoch and its read | L2 | `EventuallyAnswered` | "No error has been found" | positive |
| I14-T56 `X8_ClearedBatch` | Given a workspace of a description and a part, a creation, a save of the part and a deletion in one batch, receipts cleared as built and one writer, then the creation and the save are answered as not applied although applied | L2 | `AnswersAgree`, TD-172 | "Invariant AnswersAgree is violated" | negative |
| I14-T57 `X8_SpareBatch` | as I14-T56 with the batch's receipts spared | L2 | `AnswersAgree` | "No error has been found" | positive |
| I14-T58 `X8_KeptResend` | as I14-T56 with every receipt kept, a resend of the creation and one crash | L2 | `AnswersAgree`, `PartitionOrder`, `WholeCommands` | "No error has been found" | positive |
| I14-T59 `X8_OrderNoToken` | Given a change, a save of the part and a change on a live workspace, no token, three writers, two crashes and one more plan of a refused batch | L2 | `PartitionOrder`, `AnswersAgree`, `WholeCommands` | "No error has been found" | positive |
| I14-T60 `X8_OrderNoTokenNoRetry` | as I14-T59 with a refused batch never planned again, which reaches the same states since no command is refused for a stale revision | L2 | `PartitionOrder` | "No error has been found" | positive |
| I14-T61 `X8_OrderTokenNoRetry` | as I14-T60 with the token | L2 | `PartitionOrder` | "No error has been found" | positive |
| I14-T62 `X8_AnswersNoToken` | Given a creation, a change, a save of the part and a deletion, a resend, no token, two writers and one crash, then a writer answers from a read another writer's request outdates | L2 | `AnswersAgree` | "Invariant AnswersAgree is violated" | negative |
| I14-T63 `X8_AnswersRead` | as I14-T62 with a planning read that takes the receipts | L2 | `AnswersAgree`, `PartitionOrder` | "No error has been found" | positive |
| I14-T64 `X8_AnyWholeAnswer` | as I14-T63 with a start from any position, then a command refused by its own check applies later | L2 | `AnswersAgree` | "Invariant AnswersAgree is violated" | negative |
| I14-T65 `X8_AnyOrder` | Given a start from any position, a change, a save of the part and a change on a live workspace, no token, two writers and one crash, then the commands take effect out of the stream's order | L2 | `PartitionOrder` | "Invariant PartitionOrder is violated" | negative |
| I14-T66 `X8_AnySaveAfterDel` | Given a start from any position, a creation, a save of the part and a deletion, no token, two writers and one crash, then no save of the part takes effect after the deletion and every command is whole | L2 | `NoSaveAfterDel`, `WholeCommands` | "No error has been found" | positive |
| I14-T67 `X8_All` | Given the token with its read, a creation, a change, a save of the part and a deletion with a resend, every receipt kept, three writers and two crashes | L2 | `AnswersAgree`, `PartitionOrder`, `WholeCommands` | "No error has been found" | positive |
| I14-T68 `X8_AllRead` | as I14-T67 with no token and the planning read of receipts | L2 | `AnswersAgree`, `PartitionOrder`, `WholeCommands` | "No error has been found" | positive |
| I14-T69 `X9_ReadAny` | Given the rule decided from the job as read, as `jobUpdate` does, an update to succeeded and one to failed in any order, two writers and one crash, then a job that succeeded is failed | L2 | `SucceededStays`, TD-181 | "Invariant SucceededStays is violated" | negative |
| I14-T70 `X9_ReadAnyOneWriter` | as I14-T69 with one writer | L2 | `SucceededStays` | "No error has been found" | positive |
| I14-T71 `X9_ReadStream` | as I14-T69 with each writer taking the stream in order | L2 | `SucceededStays` | "No error has been found" | positive |
| I14-T72 `X9_ReadStreamFailFirst` | as I14-T71 with the update to failed first | L2 | `SucceededStays` | "No error has been found" | positive |
| I14-T73 `X9_GuardAny` | as I14-T69 with the condition in the request's guard | L2 | `SucceededStays`, TD-181 | "No error has been found" | positive |
| I14-T74 `X9_GuardStream` | as I14-T71 with the condition in the request's guard | L2 | `SucceededStays` | "No error has been found" | positive |

**One command.**

```bash
mise run check:models-multi-store -- "X5_*" "X7_*" "X8_*" "X9_*"
```

A pass ends `models: 67 as expected, 0 failed, 0 skipped, 0 stopped`. The runner's own tests, run first, pass with the base tier's count at 140. The figures of each run are in the models' README. The runs of this addendum were made one at a time by pattern, `X5_*`, `X7_*`, `X8_*` and `X9_*`, each ending with every configuration as expected.

**What the results say, for these constants only.** Five results differ from what the brief for this work expected, and the models are not changed to meet them.

- **A command refused by its own check applies later, with or without a token.** With each writer starting at any position of the stream, `X7_AnyWholeAnswer` and `X7_AnyFencedAnswer` printed `AnswersAgree` violated where the brief expected no error. A writer takes a change alone before the creation it waits on, answers it as not applied and writes no receipt. The writer that takes the creation applies the change in its batch. In stream order it needs a resend of the refused command, which `X7_RefusedThenApplies` and `X7_RefusedThenAppliesToken` printed with one writer and no crash, and `X7_RefusedThenAppliesBatch` printed with the three deliveries in one batch. The planning read of receipts and the token do not close it, since the answer was true of the read it was given from. The design records nothing for a refused command, and this is that gap. `X8_AnyWholeAnswer` printed the same with a part.
- **The token gives no order where delivery has none, but only where commands can be taken in more than one order.** `X7_AnyFencedAnswerOrder` printed no error where the brief expected a violation, since a creation, a change and a deletion each apply only after the one before. `X7_AnyFencedAnswerOrderSets` is added, with three changes that carry no expected revision, and printed `PartitionOrder` violated.
- **The log is not lost in stream order as built.** `X5_BuiltLog` printed no error where the brief expected a violation, since under stream order no writer plans a deletion from a read that two saves then outdate. With each writer taking every command in any order, the brief's own fallback, `X5_BuiltLogAny` printed `LogKept` violated with two writers. A deletion's request fails both guards and still drops the log of a live, listed document (TD-180). The configuration with three writers was not needed. Under one guard the log is removed only with the receipt and `LogKept` held.
- **The rule that a succeeded job stays so held in stream order.** `X9_ReadStream` and `X9_ReadStreamFailFirst` printed no error where the brief expected a violation with two writers. Each update has a receipt of its own, so a writer that reaches the update to failed after the update to succeeded was applied reads a job that has succeeded and drops it. `X9_ReadAny` printed `SucceededStays` violated with two writers that do not share one order, and `X9_ReadAnyOneWriter` held with one, so a second writer is what breaks it. `X9_GuardAny` and `X9_GuardStream` held, so the condition in the request's guard is enough. The comment on `jobUpdate` says the check cannot race because a workspace's writes are applied in order, and these runs say that holds as far as delivery keeps that order.
- **A second aggregate changed nothing in stream order.** Every command in X8 writes all its aggregates in one guarded step, so `WholeCommands` held in every configuration. A save of the part planned before the deletion was refused after it, as `NoSaveAfterDel` said, and `X8_AnySaveAfterDel` held. Under stream order no command was refused for a stale revision, so `Retries=0` and `Retries=1` reached the same states (`X8_OrderNoTokenNoRetry` and `X8_OrderNoToken`). The order broke under any position (`X8_AnyOrder`).
- **Liveness.** Under weak fairness on each writer's actions but its crash, every command was answered where the last writer stayed alive, for `WholeAnswer` and `FencedAnswer` in X5 and in X7, with two writers and one crash in stream order. The same property under the specification with no fairness was violated. In X5 an answer is a command finished, since the model has no variable for the reply apart from the offset.

**Deliberate non-coverage.** Delivery is a starting position and a contiguous batch, so a reordering inside a batch is not modelled. `X8` plans one state for the workspace, so a part created or deleted alone, further parts and content are not. The per-step guards over two aggregates in a batch are not modelled in X8, and X5 stays the evidence on them. The record the design would keep for a refused command, and the sweep for TD-167, are not modelled. A job's results, owner, events and the rebuild job that deletes itself are not modelled in X9. The three-writer instance of `X5_BuiltLogAny` and of X9 were not run. Retention of receipts, promotions and the broker are not modelled. Liveness is checked for two writers and one crash in stream order and not for three writers or for `Any`. Not run on Windows.

**For the maintainer.** The first result above bears on MSA-Q23. A record for a command its own check refused, kept as a receipt of a refusal and read by the same read that reads the receipts, is the option that would close it, and none of the three of the note records one. That is a design decision and is not made here.

## Addendum of 2026-11-24, the two store behaviours a unit written receipt first relies on

A unit lowered to SPARQL writes its receipt first, under the joint guard of every row it writes, and each of its operations then requires the receipt (the design note's section 5). Two probes, kept as conformance tests in `tools/persistence/tests/test_store_probes.py`.

| Test | Given, when, then | Level | Result on rdflib 7.6.0, Oxigraph 0.5.13 and Jena ARQ in memory |
|---|---|---|---|
| I14-P1 | a request of a receipt and two operations that require it. With every row as planned all three apply, and with one row moved none does | L4 | passed on each |
| I14-P2 | the receipt's guard as a list of rows and revisions and a list of rows to create, over four states of the store. The receipt is written only where every row is as planned | L4 | passed on each |
| I14-P2, at size | thirty listed rows among a thousand others | L4 | passed on each |

**The one command.** `mise run check:persistence-conformance`, which runs them with every other conformance test. They were run alone on 2026-11-24 on macOS, 21 passed.

**Cost, observed once and not a benchmark.** Thirty listed rows among 5,000 others took 0.01 s on Oxigraph, 0.11 s on Jena and 31.5 s on rdflib.

**Not covered.** Fuseki over TDB2 and Oxigraph on disk were not run, the generated operations were not used, and no finding is recorded in the store discovery record yet.

## Addendum of 2026-11-24, R2 as option (a) of MSA-Q29 restates it

**The invariant.** Only an answer of applied is final. A command answered as applied was applied (`AppliedIsFinal`), and none is answered as not applied once it has applied (`NoRefusalAfterApplied`, an action property). A command answered as not applied may apply later, on a resend. X7 and X8 gain the two properties, and no existing configuration changes.

| ID | Given, when, then | Level | Property | Pass criterion | Kind |
|---|---|---|---|---|---|
| I14-T75 `X7_RefusedThenAppliesFinal` | Given one writer in stream order and a change sent before its creation, with a resend, when the resend applies, then no answer of applied is wrong and no refusal follows an apply | L2 | `AppliedIsFinal`, `NoRefusalAfterApplied` | "No error has been found" | positive |
| I14-T76 `X7_AnyWholeAnswerFinal` | Given two writers that start from any position, no token and the planning read of receipts, when a writer answers from a plan older than the other's apply, then a command is answered as not applied after it applied | L2 | `NoRefusalAfterApplied` | the action property is violated | negative |
| I14-T77 `X7_AnyFencedAnswerFinal` | as I14-T76 with the token | L2 | `AppliedIsFinal`, `NoRefusalAfterApplied` | "No error has been found" | positive |
| I14-T78 `X8_AnyWholeAnswerFinal` | as I14-T76 with a workspace and its part | L2 | `NoRefusalAfterApplied` | the action property is violated | negative |
| I14-T79 `X8_AnyFencedAnswerFinal` | as I14-T78 with the token | L2 | `AppliedIsFinal`, `NoRefusalAfterApplied`, `WholeCommands` | "No error has been found" | positive |

**The one command.** `mise run check:models-multi-store -- "X*Final"`, which ends `models: 5 as expected, 0 failed, 0 skipped, 0 stopped`. Run on 2026-11-24 on macOS. The base tier is now 145 configurations.

**Not covered.** `PartitionOrder` is left out of the two X8 configurations, since a writer that takes the stream from any position breaks it first, with the token too (`X7_AnyFencedAnswerOrderSets`). In stream order the stronger `AnswersAgree` already holds wherever no refused command applies later, so no stream-order configuration was added beyond I14-T75.

## Addendum of 2026-11-25, two aggregates and a batch planned again

**The invariant.** With a workspace and its part, a batch refused for a moved revision is planned again and its commands still take effect whole, once and in the partition's order. X8 gains the script `Sets`, two changes of the description, a save of the part and a third change, since its script `SetSave` never reached a planning again.

| ID | Given, when, then | Level | Property | Pass criterion | Kind |
|---|---|---|---|---|---|
| I14-T80 `X8_OrderSetsNoToken` | Given a live workspace, the script `Sets`, three writers, two crashes, no token and one planning again, when a batch is refused for a moved revision, then every property holds | L2 | `WholeCommands`, `AppliedOnce`, `AnswersAgree`, `PartitionOrder` | "No error has been found" | positive |
| I14-T81 `X8_OrderSetsNoTokenNoRetry` | as I14-T80 with no planning again, when the refused batch is answered at once, then a change is answered as not applied and applies later | L2 | `AnswersAgree` | the invariant is violated | negative |
| I14-T82 `X8_OrderSetsTokenNoRetry` | as I14-T81 with the token | L2 | the four of I14-T80 | "No error has been found" | positive |

**The one command.** `mise run check:models-multi-store -- "X8_OrderSets*"`, which ends `models: 3 as expected, 0 failed, 0 skipped, 0 stopped`. Run on 2026-11-25 on macOS under a heap of 576 MB, which the two runs with no error filled. The base tier is now 148 configurations.

**The probes' finding.** I14-P1 and I14-P2 are recorded as TSD-80 in the `triple-stores` domain, written on 2026-11-25.

## Addendum of 2026-11-25, the unit on Fuseki by HTTP and on Oxigraph on disk

| ID | Given, when, then | Level | Property | Pass criterion | Kind |
|---|---|---|---|---|---|
| I14-P3 `test_msa_i14_p3_...` | Given Oxigraph's on-disk store and one client, when the unit's request is sent with every row as planned, one moved, one missing, or a row to create present, then it applies whole or not at all, and reads the same after the store is reopened | L4 | whole or nothing | 4 passed in the Oxigraph run, skipped in the others | positive and negative |
| ISO-12 `unitReceiptFirst` | Given Fuseki over TDB2 by HTTP at Jena 5.1.0 and 6.2.0, when the unit's request is sent with every row as planned and with one row moved, then it applies whole or not at all in every repetition, and with members that do not require the receipt it applies in part in every repetition | L4 | whole or nothing | `PASS` on six rows, the control `always` | positive, with a control |

**The commands.** `mise run check:persistence-conformance -- -k msa_i14`, which ended `25 passed, 8 skipped` on 2026-11-25, the skips being I14-P3 in the rdflib and Jena runs. `STORE_ISOLATION_QUICK=1 STORE_ISOLATION_ARMS=jena mise run check:store-isolation-probes`, which ended `isolation probes: 46 as expected, 0 failed, 0 skipped`, five repetitions a row.

**Not covered.** Two clients at once on any store. Oxigraph on disk lets two concurrent updates both commit (TSD-73), which the unit's guard does not answer. The probes' full run of 20 repetitions and the PostgreSQL arm were not run for this addendum.
