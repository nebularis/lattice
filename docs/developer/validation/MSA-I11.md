<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I11, the logical port on paper

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I11
**Machine:** paper, checked against the studio's writer and the persistence caller library on `spi/sql-backend` at 2026-11-17. **Placement:** T0, public. Platform configuration, nothing domain-specific.
**Status:** authored, not accepted. The maintainer's review is the sign-off.

## Scope

- The note [MSA-I11-logical-port.md](../notes/multi-store/MSA-I11-logical-port.md). The port in Java form, the studio's commands moved onto it, the outcome classification of SPARQL, SQL, GQL and the exported interpreter side by side, and six findings.
- An inventory of the studio's write path gathered from `Writer`, `StudioOperations`, `StudioStore`, `Command`, `Reply`, `RabbitWrites`, `StreamWriter`, `persistence-profile.ttl`, the caller library and the guide's §25.1, used as working material and not committed. The claims the findings rest on were read again in the source.
- Out of scope. Any change to the studio, the caller library or the guide.

## Result in one paragraph

The falsifier does not fire for the port the note writes, and fires against the guide's. Every studio write that runs a generated operation moves onto the port as one unit, and the studio stops choosing transaction ids, revision IRIs, sequence numbers and the request digest. For that the port needs five things the guide's lacks, a multi-operation unit as its basic write, a batch of units in one commit, named business guards, a version the caller can report and housekeeping for retention. Jobs and promotion maintenance in the same request are needs no port of generated operations meets today, and are recorded. Three findings concern running code.

## Checks

| Claim | Checked against |
|---|---|
| a batch is one request, receipts are read by id before and after, and a command with a receipt is answered 200 | `Writer.apply` in `platform/config-studio-core` |
| a command's receipt is guarded on one operation's claim, the last by default | `Writer.Steps.commit` |
| the transaction id is `urn:txn:{command id}/{n}` | `Writer.Steps.op` |
| the epoch is `LATTICE_STUDIO_EPOCH`, default 1 | `StudioConfig.epoch` |
| the families are named graphs under `dal:Optimistic`, parts and documents under a patch log | `contracts/config-studio/persistence-profile.ttl` |
| `GraphReference` accepts only `http` and `https` IRIs | `platform/semantic-dataset-spi`, `GraphReference` |
| `StreamWriter` retries a batch on any `RuntimeException` | `StreamWriter.apply` in `platform/config-studio-writer` |
| `DERIVED` has no resource kind | `tools/persistence/src/persistence/contract.py`, `_ROLE_RESOURCE` |
| the guide's port | `docs/architecture/rdf-sparql-patterns-guide.md` §25.1 |

| Command | Result |
|---|---|
| `mise exec '--' python tools/writing_rules.py docs/developer/notes/multi-store/MSA-I11-logical-port.md` | 0 failures |

## Adversarial probes

1. Every studio command type was put against the port, not only create, replace and tombstone, to find what the port cannot say. Jobs and promotion maintenance were what it found.
2. The outcome table was checked for an outcome one realisation cannot tell apart. SPARQL can tell every outcome only by the reads after the request, and SQL and GQL within the transaction. `Unknown` exists only where a commit's answer can be lost.
3. The claim that a unit is all or nothing on SPARQL was checked against how an Update request applies its operations. Separate operations apply separately, so the note requires one `WHERE` for a unit, and that requirement is what MSAI11-01 finds the studio lacks.

## Decisions taken

- **The unit, not the operation, is the port's write.** Every studio command that writes two aggregates needs it, and every realisation here can provide it in one store.
- **No `Conflict` outcome.** MSA-I4's guards make every non-application definite, and an engine's abort is the adapter's to retry.
- **Business guards are named in the profile.** A caller-written pattern would be SPARQL.

## Open matters

- MSAI11-01, MSAI11-02 and MSAI11-05 concern running code and are for the maintainer's triage. This slice changes no code, and MSAI11-01 was found by reading and not reproduced.
- Jobs on the port wait for a decision to make them a family.
- Promotion maintenance in a unit waits for `DERIVED` to map to a resource.
