<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F14, a command's digest tells blank nodes apart by their own quads

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F14, from TD-165 of the [technical debt register](../technical-debt.md), as section 4.7 of the [machine S brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md) states it
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, Jena 6.2.0 in memory. **Placement:** T0, public. The studio's command codec, nothing domain-specific.
**Status:** built 2026-11-19, not verified.

## Invariant

A command id names one request (MSA-F3). Two bodies that differ only in how their blank nodes connect are two requests, so the second sent under the first's id is refused with a 400 and changes nothing. Before this slice, `Codec.digest` read every blank node as one label, so such a second body digested as the first and was answered 200 from the first's receipt, although it was not applied (TD-165). A resend whose blank nodes were only relabelled, as the wire does, still digests the same and is answered from its receipt.

[MSA-F12's pack](MSA-F12.md) settled that a body can hold a blank node when it reaches the digest, and that a part's save carries one in normal use, so the slice is built.

## Change

- `platform/config-studio-core/.../writes/Codec.java`, `digest`. Each blank node of the body gets a label, the SHA-256 of its own quads, the quads that name it in any position. In those quads it is written as `_:self` and every other blank node as `_:other`, and the lines are sorted before they are hashed. Each quad of the body is then written as an N-Quads line with each blank node as its label, and the lines are sorted and hashed with the command's kind and fields as before. Each quad gives one line, so two quads that come to read alike are both counted. A non-blank node is written by Jena's N-Triples formatter, the one the N-Quads writer uses, so a body with no blank node digests exactly as under MSA-F3. This was checked once with a test, since removed, that compared the two over a body with an empty, a language-tagged, an escaped, a typed and a non-ASCII literal and an IRI: the digests were equal. The regular expression that matched `_:` labels in the written text is gone, so a literal holding `_:x` is no longer read as a blank node.
- `CodecTest.java`, new in `platform/config-studio-core/src/test/java/.../writes/`. Two tests.
- `ReceiptsTest.java`. One test.

No other code, and no vocabulary or contract text, was changed.

## The limit

The label is one round of hashing, not canonicalisation. Two blank nodes whose own quads are the same, with itself and the others written as the two fixed labels, get the same label. So two bodies whose blank nodes form structures that look alike from each node still digest alike. For example, six blank nodes in one cycle on `ex:p` and six in two cycles of three: each node has one quad naming it as subject and one as object, so every node gets one label, both bodies give six equal lines, and the digests are equal. A sender that reuses an id for the second is answered from the first's receipt, as TD-165 described for every body before. Telling these apart needs RDF dataset canonicalisation (RDFC-1.0), which the brief does not want. More rounds of hashing would not separate this example either.

## Receipts written before this change

The writer compares the digest a receipt holds with the digest of the command sent again, and refuses a resend whose digest differs with a 400 that changes nothing (MSA-F3, `Writer.java:127-130`). A receipt with no digest, written before MSA-F3, is answered from as before.

- **A receipt of a body with no blank node.** Its digest is unchanged, so its resend is answered from it as before.
- **A receipt of a body with a blank node, written under MSA-F3's digest.** Its digest was of `_:b` lines, so a resend of the same request now digests otherwise and is refused with a 400, although the request was applied. Only a resend reaches this, after a lost acknowledgement.

Nothing is done for the second case. The studio is not released: ADR-A136 makes it part of a release once the release policy defines how software is released, and MSA-F3's digest is on the branches `spi/multi-store-architecture` and `spi/worktree-s` and not on `main`. So no production store holds such a receipt. A development store that does answers one resend of each such command with a 400, and a store rebuilt from its baseline has none. Accepting the old digest beside the new one would keep TD-165 open for every such receipt, and was not built.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F14-T1 | Given body A `_:x ex:p _:y . _:y ex:q "1" . _:z ex:q "2" .` and body B `_:x ex:p _:z . _:y ex:q "1" . _:z ex:q "2" .`, and body C `ex:a ex:p _:x . ex:b ex:p _:x .` and body D `ex:a ex:p _:x . ex:b ex:p _:y .`, when each is digested as a save, then A and B digest apart, and so do C and D. Each pair has the same sorted lines with every blank node as one label | L1 | two bodies that connect blank nodes otherwise are two requests | `CodecTest.twoBodiesThatDifferOnlyInHowTheirBlankNodesConnectDigestApart` passes | negative |
| F14-T2 | Given body A, when it is written with other labels and its triples in another order, then it digests as A | L1 | a relabelled resend is the same request | `CodecTest.aBodyWhoseBlankNodesAreRelabelledDigestsTheSame` passes | positive |
| F14-T3 | Given a save of body C applied at revision 1, when its id is sent with body D, then the reply is 400 and the revision stays 1 | L4 | the invariant, through the writer | `ReceiptsTest.anIdResentWithABodyWhoseBlankNodesConnectOtherwiseIsRefused` passes | negative |
| F3-T2 | MSA-F3's resend of a save holding a blank node, encoded and decoded through the codec, answered 200 at revision 1 and applied once | L4 | a relabelled resend is the same request | `ReceiptsTest.aResendThroughTheWireIsTheSameRequest` passes, unchanged | positive |
| existing | the rest of `ReceiptsTest`, including F3-T1, and `StudioApiTest`, including F12-T3, which reads the receipt's digest through `Codec.digest` | L4, L3 | theirs | pass, unchanged | |

F14-T2 passed before the fix as well, since one label for all also ignores labels. It guards the new labels against depending on the old ones.

## Commands and results

Run on 2026-11-19.

| Command | Result |
|---|---|
| `mise exec -- mvn -f platform/pom.xml -pl config-studio-core -am test -Dtest=CodecTest -Dsurefire.failIfNoSpecifiedTests=false`, before the fix | "Tests run: 2, Failures: 1". F14-T1: "x names the node holding 1, then the node holding 2 ==> expected: not equal but was: <bf97f466652734f5208728dbc0200ed0464c47f85f4241e939d5c7b30d18107c>". BUILD FAILURE |
| `mise exec -- mvn -f platform/pom.xml -pl config-studio-service -am test -Dtest=ReceiptsTest -Dsurefire.failIfNoSpecifiedTests=false`, before the fix | "Tests run: 10, Failures: 1". F14-T3: "expected: <400> but was: <200>". BUILD FAILURE |
| `mise exec -- mvn -f platform/pom.xml -pl config-studio-service -am test -Dtest=CodecTest,ReceiptsTest,StudioApiTest -Dsurefire.failIfNoSpecifiedTests=false`, after the fix | `CodecTest` "Tests run: 2, Failures: 0", `ReceiptsTest` "Tests run: 10, Failures: 0", `StudioApiTest` "Tests run: 33, Failures: 0". BUILD SUCCESS |
| `mise run check:config-studio` | exit 0, "Finished in 129.24s". pytest "159 passed". JUnit 256 tests across the studio's modules with 0 failures and 0 errors (authoring 9, core 26, service 199, transforms 2, writer 20), read from the run's surefire reports. The browser checks "Tests 121 passed (121)" |

The one command for the slice is `mise run check:config-studio`.

## Deliberate non-coverage

- No test runs a body whose blank nodes the one round cannot tell apart. The limit above is stated, not tested, since the brief accepts it.
- A blank node as a graph name is labelled by the same rule, and no test sends one. `Codec.decode` parses N-Quads, which allows it.
- The compatibility check for a body with no blank node was run once and not kept.
- The `rdfs:comment` of `cst:requestDigest` in `contracts/config-studio/studio-vocabulary.ttl` still says blank nodes are read as one label. The brief for this slice leaves the vocabulary unchanged, so the comment is now out of date. A question for the maintainer, below.

## Decisions taken

- **One round of hashing, as the brief states.** It separates the bodies TD-165 names unless two blank nodes have the same quads of their own.
- **One line for each quad.** Two blank nodes that get one label keep both their lines, so a body with two such nodes does not digest as a body with one.
- **The digest of a body with no blank node is unchanged.** Its receipts stay valid.
- **Receipts written under MSA-F3's digest are left as they are.** As above, no released store holds one.

## For the maintainer

- The comment of `cst:requestDigest` names the old rule. Should it be changed to "with each blank node labelled by the hash of its own quads", outside this slice?

## Doc delta

None. The contract's README names the digest without its rule for blank nodes, and the vocabulary is unchanged, as above.
