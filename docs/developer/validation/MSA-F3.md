<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F3, an id resent with another request is refused

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F3, from finding MSAI11-02 of [MSA-I11](MSA-I11.md)
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, Jena 6.2.0 in memory. **Placement:** T0, public. The studio's writer and its contract, nothing domain-specific.
**Status:** built 2026-11-18, not verified. It departs from the brief in where the digest comes from, below.

## Invariant

A command id names one request. A resend of the same request is answered from its receipt and applied once, as before. The same id with another request is refused with a 400 and changes nothing, where before it was answered 200 from the first request's receipt (MSAI11-02).

## Where the digest comes from, a departure from the brief

The brief says the digest is already in the store, in the claim of the command's operations (`pat:requestDigest`). That digest is of a persistence operation, computed from the state the writer read, so it cannot be recomputed for a resend. A save is written as a delta against the stored graph, and after the first application the same save plans an empty delta, which digests differently. Comparing it would refuse every honest resend of a save.

So the receipt now holds the digest of the command itself, `cst:requestDigest`. `Codec.digest` is the SHA-256 of the command's kind, its workspace, job, part, expected revision, label and sample, and its graphs as sorted N-Quads with every blank node read as one label, so a resend whose blank nodes were relabelled on the wire digests the same. Its sender, principal and times are not part of the request. A receipt written before this change has no digest, and any resend of its id is answered from it as before. The term is added to `contracts/config-studio/studio-vocabulary.ttl` and to the receipt paragraph of the contract's README.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F3-T1 | Given a save applied at revision 1, when its id is sent with another body, then the reply is 400, the revision stays 1, the graph is the first save's, and the first request sent again is still answered 200 at revision 1 | L4 | the invariant | `ReceiptsTest.aCommandIdResentWithAnotherRequestIsRefusedAndChangesNothing` passes | negative |
| F3-T2 | Given a save with a blank node applied, when it is encoded and decoded through the wire codec and sent again, then it is answered 200 at revision 1 and applied once | L4 | an honest resend is never refused | `ReceiptsTest.aResendThroughTheWireIsTheSameRequest` passes | positive |
| existing | `aRedeliveredCommandIsAnsweredFromItsReceiptAndAppliedOnce` and the rest of `ReceiptsTest` | L4 | unchanged | pass | |

## Commands and results

Run on 2026-11-18.

| Command | Result |
|---|---|
| `mise exec -- mvn -q -f platform/pom.xml -pl config-studio-service -am test -Dtest=ReceiptsTest -Dsurefire.failIfNoSpecifiedTests=false`, before the change | 9 tests, 1 failure, F3-T1: expected 400 but was 200 |
| the same, after the change | 9 tests, 0 failures |
| `mise run check:config-studio` | exit 0. pytest 157 passed, JUnit 234 tests across the studio's modules with 0 failures (the service's 185), the browser checks 121 passed |

The one command for the slice is `mise run check:config-studio`.

## Deliberate non-coverage

- `RabbitWrites`, after a timeout, reads only whether the command's receipt exists. A caller that reuses an id for another request and times out is told it applied. That path has no test against a broker and is left as it was.
- The Python worker's job updates carry their own ids and are not resent with another body.
- Two commands with one id in one batch.

## Decisions taken

- **The command's digest, not the operations'.** As above, the only digest a resend can recompute.
- **Blank nodes are read as one label.** It can only make two requests that differ in blank-node structure alone read as one, which answers the second from the receipt as before. It never refuses an honest resend.
