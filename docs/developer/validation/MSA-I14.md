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
