<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F2, a refused batch is answered and its partition moves on

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F2, from finding MSAI11-05 of [MSA-I11](MSA-I11.md)
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, Jena 6.2.0. **Placement:** T0, public. The studio's store writer, nothing domain-specific.
**Status:** built 2026-11-18, not verified. One choice is open for the maintainer, below.

## Invariant

A partition is held only while holding it can help. The writer retried every failed batch for ever, so a batch the store will refuse on every attempt held its partition, and every workspace on it, for good (MSAI11-05). Now a failure that says nothing about the request is retried with the whole batch, as before, holding the partition in order. A failure that is the request's fault is not retried. The batch is tried one command at a time in its order, so the command at fault is answered as refused with a 400 and the rest apply, and the partition moves on. Every batch runs as one SPARQL Update request, which is one transaction, so a refused batch applied nothing and trying its commands alone applies each once. Receipts already make any resend safe.

## How the two are told apart

The store's exceptions say which is which. Jena's `HttpException` and `QueryExceptionHTTP` carry the HTTP status, `-1` when no response came, and a connection failure carries an `IOException` as its cause. `StreamWriter.retried` reads the cause chain.

| Failure | Retried | Why |
|---|---|---|
| an `IOException` or `UncheckedIOException` anywhere in the chain, or no status | yes | the store was not reached |
| a 5xx | yes | the store failed on its side |
| 401, 403, 404, 408, 429 and every other status outside the next row | yes | the store refused the writer, its credentials or its dataset, or asked it to wait, which an operator can fix while the batch waits |
| 400, 413, 414, 415, 422 | no | the request itself is at fault, and sending it again cannot succeed |
| any other exception, thrown by the writer's own code before or after the request | no | it says nothing about the store, and the same input gives the same failure |

## Tests

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F2-T1 | Given a batch of three on one partition whose middle command the store refuses with a 400, when the batch is applied, then the batch is tried once, then each command alone, the replies are 200, 400, 200, and the partition's offset reaches the third | L1 | the partition moves on | `aBatchTheStoreRefusesIsAnsweredCommandByCommandAndThePartitionMovesOn` passes within 10 s | negative |
| F2-T2 | Given a store that fails with a connection error, then a 503, then succeeds, when a batch of two is applied, then it is tried three times whole and both are answered 200 | L1 | an unreachable store is waited for | `aStoreThatCannotBeReachedIsRetriedWithTheWholeBatch` passes | positive |
| F2-T3 | the classification of twelve failures, as the table above | L1 | the two are told apart | `onlyAFailureThatSaysNothingAboutTheRequestIsRetried` passes | both |
| F1-T1, F1-T2 | MSA-F1's tests, unchanged | L1 | MSA-F1's | pass | |

## Commands and results

Run on 2026-11-18.

| Command | Result |
|---|---|
| `mise exec -- mvn -q -f platform/pom.xml -pl config-studio-writer -am test -Dtest=StreamWriterTest -Dsurefire.failIfNoSpecifiedTests=false`, with `retried` answering true for every failure as the writer did | 5 tests, 2 failures. F2-T1 timed out after 10 s, retrying the refused batch. F2-T3 failed on the first refusal it expects |
| the same, after the fix | 5 tests, 0 failures |
| `mise run check:config-studio` | exit 0. pytest 157 passed, JUnit 232 tests across the studio's modules with 0 failures (the writer's 14), the browser checks 121 passed |

The one command for the slice is `mise run check:config-studio`.

## Deliberate non-coverage

- A live store returning each status. The classification is tested on the exceptions Jena 6.2.0 raises, and the statuses Fuseki returns for a malformed request are those of the SPARQL protocol. No test drives a Fuseki into each.
- A command that the store refuses only together with another in its batch. Applied alone, each succeeds, which is what the command-by-command pass does.

## Decisions taken, one for the maintainer

- **For the maintainer: a failure of the writer's own code is answered as refused, not retried.** The brief asks for a maintainer's decision where the store's exceptions do not say. They do say for the store, and this slice classifies them as the table shows. A failure that is not the store's, such as a payload the caller library rejects, is deterministic for the same input, so retrying it is the poison case MSAI11-05 found. It is answered with a 400 and its message. The alternative is to retry it and alert, which keeps the write and holds the partition. The choice is recorded in the status record's next action.
- **401, 403 and 404 are retried.** They refuse the writer's configuration, not the request, and refusing every write while a password is wrong would answer writes that a fixed configuration would apply.
