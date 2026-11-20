<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F12, a reply built from a failure carries a fixed message, and a message that is not a command is answered 400

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F12, from finding MSAF8-01 of the review of 2026-11-19 and the maintainer's answer on a message that cannot be decoded, as section 4.7 of the [machine S brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md) states it
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, stream-client 1.12.0, Jena 6.2.0. **Placement:** T0, public. The studio's stream writer, nothing domain-specific.
**Status:** built 2026-11-19, not verified.

## Invariant

A reply's message reaches a client, since `StudioApi` returns it as the response body. Before this slice, the reply to a write the store refused carried the exception's message, and so did the reply to a failure of the writer's own code. Either can name an endpoint, a query or a class (MSAF8-01). Now each carries a fixed message. The exception goes to the writer's log, with the command's id. A message the writer's own checks author for a refusal, for example a save under a deleted id, is answered as it is.

| What happened to the write | Reply | What the log holds |
|---|---|---|
| the store refused it, with 400, 413, 414, 415 or 422 | 400, "the store refused this write, which was not applied. The writer's log holds the reason under command {id}" | an error naming the stream, the offset and the command's id, the body the store answered with, and the exception |
| the writer's own code failed on it | 500, "the writer failed on this write, which was not applied. The writer's log holds the reason under command {id}" | an error naming the stream, the offset and the command's id, and the exception |
| the message is not a command: its headers name no known command, its N-Quads do not parse, its `at` is not a time, or its body cannot be read as bytes | 400, "the message is not a studio command, so it was not applied. The writer's log holds the reason under command {id}" | a warning naming the stream, the offset and the command's id, and the exception where one was thrown |
| the writer's checks refused it, for example "the document was deleted, so its id cannot be used again" | the writer's own reply, as before | as before |

The second sentence of each fixed message, naming the id, is there only where the message's `id` header is an id, a lower-case UUID (`Graphs.isId`). Any other value is neither echoed nor logged, so a header cannot write text into a reply or a log line. A message with no reply-to, as the worker's are, is answered and the reply dropped, as before.

### Decision: the reply names the command's id

The brief left it to this slice. The reply names the id. The service sets the AMQP `correlation_id` to the command's id (`contracts/config-studio/README.md`, Writes), but neither the service's answer nor the browser shows it, so without it in the message a user has nothing to quote to an operator. The id is the UUID the service minted for the command, not text from the request, and it says nothing about the store or the code.

### What happened to a message that could not be decoded

Read from the code before the change and from the first run below.

- **Headers or a body that are not a command's.** `Codec.decode` returned null, and `Writer.apply` answered the null with its first check, 400 "a write names a workspace by its id" (`Writer.java:179-180`). The status was right and the message wrong. The partition moved on.
- **A body the stream client cannot give as bytes.** `getBodyAsBinary()` threw inside the decoding of the whole batch, so the batch was tried one command at a time, and that message was answered 500 with the client's text: "the writer failed on this write, which was not applied: Body cannot by returned as array of bytes. Use #getBody() to get native representation." The partition moved on.

Neither escaped the thread. Now each message is decoded alone. One that is not a command is answered 400 and the others of the batch are applied together in one request, rather than one at a time.

## Change

- `platform/config-studio-writer/.../StreamWriter.java`.
  - `decoding`, the writer function the production consumer uses, decodes each message alone. A message that `Codec.decode` answers with null, or whose reading throws, is answered `Reply.refused` with the fixed message, and the rest are passed to the `Writer` in their order.
  - `answer` builds `Reply.refused` and `Reply.failed` from the fixed messages `REFUSED_BY_STORE` and `FAILED`, naming the command's id. Its two error lines name the command's id, and the refusal's line also logs the body the store answered with, which `HttpException.getMessage()` leaves out.
  - `commandId` reads the `id` header and keeps it only where it is an id.
  - `reply` is package-private, so a test sends a reply through it.
  - The class comment names the fixed messages and a message that is not a command.
- `StreamWriterTest.java`. Two tests, three helpers (a stream message, a reply channel, the log captured), and F8-T1's message assertion changed, below.
- `StudioApiTest.java`. One test, for MSA-F14's question.
- `contracts/config-studio/README.md`, Writes. One sentence on the fixed messages and a message that is not a command.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F12-T1 | Given a batch of five on one partition, whose second command the store refuses with a body naming its endpoint, whose third and fifth the writer's code fails on with a message naming a class and a query, and whose fourth the writer's checks refuse with "the document was deleted, so its id cannot be used again", when the batch is applied, then the replies are 200, 400, 500, 400 and 500, the 400 and the first 500 carry the fixed messages naming their ids, the fourth carries the writer's own message, the fifth, whose `id` header is not an id, carries the fixed message alone, the offset reaches 5, and the log names both ids and holds both exceptions' text | L1 | the first, second and fourth rows | `StreamWriterTest.aRefusalOrAFailureIsAnsweredWithAFixedMessageAndTheExceptionGoesToTheLogWithTheCommandsId` passes within 10 s | negative |
| F12-T2 | Given a real `Writer` over an in-memory store and five messages on one partition, a creation, a save whose N-Quads do not parse, a save whose body cannot be read as bytes, a message naming no known command and with no reply-to, and a save, when the batch runs through `decoding`, then the replies are 200, 400, 400, 400 and 200, a reply is published to each of the four reply-to queues and none for the fourth message, the two 400s published carry the fixed message naming their ids, the offset reaches 5 and all five are processed | L1 | the third row | `StreamWriterTest.aMessageThatIsNotACommandIsAnswered400WhereItHasAReplyToAndThePartitionMovesOn` passes within 10 s | negative |
| F8-T1, changed | MSA-F8's test of a 500, whose message assertion now expects "the writer failed on this write, which was not applied" in place of a message holding the exception's text | L1 | the second row | `StreamWriterTest.aFailureOfTheWritersOwnCodeIsAnsweredAsTheWritersFaultAndThePartitionMovesOn` passes | negative |
| F12-T3 | Given a workspace, when a surface part holding a blank node is saved through the API, then the save sent to the writer holds the blank node in its body, the answer is 204, and the receipt's `cst:requestDigest` is `Codec.digest` of that body | L3 | MSA-F14's question, below | `StudioApiTest.aPartSavedWithABlankNodeReachesTheCommandsDigestHoldingIt` passes | evidence |
| existing | MSA-F1's, MSA-F2's and MSA-F10's tests of `apply` and the thread, unchanged | L1 | theirs | pass | |

F8-T1 was changed because the brief removes the exception's text from the 500 that MSA-F8 built. Its statuses and offsets are unchanged.

F12-T3 is evidence, not a fix. It passed on the code before this slice, since nothing it reads was changed.

## Commands and results

Run on 2026-11-19.

| Command | Result |
|---|---|
| `mise exec -- mvn -f platform/pom.xml -pl config-studio-writer -am test -Dtest=StreamWriterTest -Dsurefire.failIfNoSpecifiedTests=false`, with `decoding` written to do what the production lambda did and `reply` package-private, the rest unchanged | 11 tests, 3 failures. F12-T1: "expected: <the store refused this write, which was not applied. The writer's log holds the reason under command 00000000-0000-4000-8000-000000000012> but was: <the store refused the write: 400 - Bad Request>". F12-T2: "expected: <[200, 400, 400, 400, 200]> but was: <[200, 400, 500, 400, 200]>". F8-T1: "the exception's text stays in the log (MSA-F12) ==> expected: <the writer failed on this write, which was not applied> but was: <the writer failed on this write, which was not applied: a bug in the writer>" |
| the same, after the fix, first run | 11 tests, 2 failures. F12-T1: the log held the store's status line but not its body, which `HttpException.getMessage()` leaves out, so the refusal's log line now logs it. F12-T2: the creation was answered 400, since the test's fifth command was a deletion of the same workspace, which clears the creation's receipt in the same batch. The fifth command became a save |
| the same, after both | 11 tests, 0 failures, BUILD SUCCESS |
| `mise exec -- mvn -f platform/pom.xml -pl config-studio-service -am test -Dtest=StudioApiTest -Dsurefire.failIfNoSpecifiedTests=false` | 33 tests, 0 failures, BUILD SUCCESS |
| `mise run check:config-studio` | exit 0. pytest "158 passed". JUnit 252 tests across the studio's modules with 0 failures and 0 errors (authoring 9, core 24, service 197, transforms 2, writer 20), 261 with mork-transforms and platform-outbox, which the run also builds. The browser checks "Tests 121 passed (121)" |

The one command for the slice is `mise run check:config-studio`.

**The first run of F12-T2 had a deletion as its fifth command.** Before the fix the batch was tried one command at a time, so the creation's reply did not depend on the deletion. Its failure, a 500 for the third message, does not depend on the fifth.

## For MSA-F14: blank nodes in a command's body

**Yes. A studio command's body can hold a blank node when it reaches `Codec.digest`, and the save of a part is the command that carries one in normal use.** Create, import, fence, publish and submit-job can carry one too. Patch, save-document and set-dependencies cannot.

`Codec.digest` runs on the command as it arrived: once for every command applied, when its receipt is written (`Writer.java:1158`), and again for a resend whose id has a receipt (`Writer.java:128`). The writer names blank nodes with skolem IRIs only when it writes a graph (`Writer.java:484`, `Writer.java:543`, `Writer.java:1083`), so ADR-A149's "a part's payload holds no blank node" holds for what is stored and says nothing of what is digested. Nothing before the writer skolemises a command's body: no factory in `Command.java` does, and no path in `StudioApi.java` calls `Skolem.skolemise`.

| Command | Where its body comes from | A blank node reaches the digest | Evidence |
|---|---|---|---|
| save | a part as Turtle, `PUT /api/workspaces/{id}/graphs/{part}`, parsed at `StudioApi.java:700` and sent at `StudioApi.java:709`. The browser sends the whole part, not a patch, when the change names a blank node (`apps/config-studio/src/api.ts:176-183`, `apps/config-studio/src/rdf/patch.ts:16-21`), and mints one for a temporal scope (`apps/config-studio/src/ui/Specials.tsx:122`). The MCP tools save the review and mapping parts the same way (`StudioMcp.java:396`, `StudioMcp.java:516`) | yes | F12-T3. MSA-F3's `ReceiptsTest.aResendThroughTheWireIsTheSameRequest` saves `[ a ex:Part ]` and resends it through the codec |
| create | the baseline as Turtle, parsed at `StudioApi.java:576` and sent at `StudioApi.java:586` | yes | written through `write`, skolemised at `Writer.java:543` |
| import | an export as TriG, parsed at `StudioApi.java:607` and sent at `StudioApi.java:617`. An export reads each skolem IRI back as a blank node (`StudioStore.java:133`), so a part that held one is imported holding one | yes | written through `write` |
| fence | the worker's `import.nt` (`workers/src/lattice_workers/config_studio_publish.py:175`), any RDF a user imports, parsed at `StudioApi.java:1101` and sent at `StudioApi.java:1105` | yes | skolemised at `Writer.java:484` |
| publish | the worker's `version.nt`, whose aggregate follows the blank nodes reached from its root (`config_studio_publish.py:41-58`), parsed at `StudioApi.java:1057` and sent at `StudioApi.java:1061` | yes | skolemised at `Writer.java:1083` |
| submit-job | the job's input, the request's body, parsed at `StudioApi.java:923` and sent at `StudioApi.java:966` | yes | inserted as it is at `Writer.java:930` |
| patch | the browser never sends a blank node in a patch (`patch.ts:16-21`), and the writer refuses one before planning (`Writer.java:608-609`), so no receipt is written. A fresh id has no receipt, so `Writer.java:128` does not digest it either | no | |
| save-document | the document's XML through the document-to-wording kit, which mints IRIs and writes no `_:` (`contracts/xml/document-to-wording/1.0.0/document-to-wording.xsl:124-125`). The writer refuses a subject that is not a named node under the document (`Writer.java:1294`) | no, through the API | a blank node as an object alone would pass the writer's check, but nothing builds one |
| set-dependencies | the request's Turtle, parsed at `StudioApi.java:1454`. The writer refuses any object that is not an IRI before planning (`Writer.java:445`) | no | |
| job-update | the worker's job graph, whose result nodes it names (`config_studio_jobs.py:137`, `config_studio_jobs.py:144`). A rebuild's promoted partitions are refused with a blank node (`Writer.java:973`) | not settled | every job kind's results were not read |
| delete-workspace, delete-document, delete-job, set-access, release | an empty body | no | |

So MSA-F14 applies. The digest reads every blank node as `_:b` (`Codec.java:69`), so two saves of a part that differ only in which of two blank nodes a triple names, for example `ex:a ex:p _:x . ex:b ex:p _:x .` and `ex:a ex:p _:x . ex:b ex:p _:y .`, digest alike, and a resend of one under the other's id is answered from the receipt.

## Deliberate non-coverage

- `StudioApi` is unchanged. It answers a 400 as a 400 with the message, and an import's 400 as a 422 with the message (`StudioApi.java:619`), so an import the store refused now shows the fixed message under 422.
- The browser is unchanged. It shows the message of a failed save as before.
- No broker. A message whose body is not AMQP data is made by a test double that throws as the stream client's message does. No test sends one through RabbitMQ.
- F12-T1 reads the log from standard error, where slf4j-simple writes it. A logging set-up that writes elsewhere would need another reader.
- The contract's list of reply statuses names 200, 400, 404 and 412, and not 403 or 500, which earlier slices added. This slice adds one sentence on messages and leaves the list.

## Found while building

- **A creation and a deletion of the same workspace in one batch.** The deletion clears the workspace's receipt graph, so the creation's receipt is gone after the commit, and the creation is answered 400 "the workspace exists" although it was applied. The service waits for a creation's reply before it can send the deletion, so only a resend could put both in one batch. Not fixed here. A question for the maintainer.

## Doc delta

- `contracts/config-studio/README.md`, Writes: a message that is not a command is refused, and a refusal by the store, a failure of the writer and a message that is not a command each carry a fixed message naming the command's id, with the reason in the writer's log.
