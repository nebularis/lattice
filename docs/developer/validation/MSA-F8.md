<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F8, a failure of the writer's own code is answered as the writer's fault

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F8, from the second half of [MSA-F2](MSA-F2.md), as the maintainer decided it on 2026-11-18
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, Jena 6.2.0. **Placement:** T0, public. The studio's stream writer and service, nothing domain-specific.
**Status:** built 2026-11-18, not verified.

## Invariant

MSA-F2 stopped retrying a write that fails the same way each time, and answered a failure of the writer's own code as refused, with a 400, like a request the store refused. A 400 says the request is at fault. A failure of the writer's own code is the service's fault, and after a fix the same request may apply. So it is now answered with a 500 and its message, still not retried, and the partition still moves on. A request the store refused keeps its 400.

| Failure, after the batch is tried command by command | Reply | Retried |
|---|---|---|
| the store answered 400, 413, 414, 415 or 422 | 400, "the store refused the write: ..." | no |
| any other exception, which carries no status from the store, from the writer's own code before or after the request | 500, "the writer failed on this write, which was not applied: ..." | no |
| a store that cannot be reached, a 5xx, 401, 403, 404, 408, 429 | none, the batch waits | yes, as MSA-F2 has it |

The service answers a writer's 500 with a 500 and the message, where before every status it did not name became a 400. `Reply.failed` is the new reply, and the status list in `Reply`'s comment names it.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F8-T1 | Given a batch of three on one partition, whose second command the writer's code fails on and whose third the store refuses with a 400, when the batch is applied, then the replies are 200, 500 and 400, the 500's message names the failure, and the partition's offset reaches the third | L1 | the invariant | `StreamWriterTest.aFailureOfTheWritersOwnCodeIsAnsweredAsTheWritersFaultAndThePartitionMovesOn` passes within 10 s | negative |
| F8-T2 | Given a service whose writer answers 500, when a workspace is deleted through the API, then the answer is 500 with the writer's message | L3 | the service's answer | `StudioApiTest.aWriteTheWriterFailedOnIsAnsweredAsTheServicesFault` passes | negative |
| existing | MSA-F2's tests, F2-T1 to F2-T3, unchanged | L1 | MSA-F2's | pass | |

## Commands and results

Run on 2026-11-18.

| Command | Result |
|---|---|
| `mise exec -- mvn -f platform/pom.xml -pl config-studio-writer -am test -Dtest=StreamWriterTest -Dsurefire.failIfNoSpecifiedTests=false`, before the change | 6 tests, 1 failure, F8-T1: expected 200, 500, 400 but was 200, 400, 400 |
| `mise exec -- mvn -f platform/pom.xml -pl config-studio-service -am test -Dtest=StudioApiTest -Dsurefire.failIfNoSpecifiedTests=false`, before the change | 32 tests, 1 failure, F8-T2: expected 500 but was 400 |
| both, after the change | 6 tests and 32 tests, 0 failures |
| `mise run check:config-studio` | exit 0. pytest 158 passed, JUnit 243 tests across the studio's modules with 0 failures, the browser checks 121 passed |

The one command for the slice is `mise run check:config-studio`.

## Deliberate non-coverage

- The browser shows a 500 as it shows any failed save. No message of its own was added.
- The worker's writes carry no reply-to, so a 500 to one of them is logged by the writer and reaches no one, as a 400 did.
