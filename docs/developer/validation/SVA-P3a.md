<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-P3a, the caller libraries' confirmation read

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-P3a, built on 2026-11-19 in autonomous mode, after the maintainer decided that the caller libraries own the read that confirms a write.

## Invariant

After a write, one read on the writer classifies its outcome, specified once in the persistence contract and given by both caller libraries. The outcome is `applied`, `refused` for a reused key, or `lostRace` with its cause, and each cause answers one guard of a generated operation. The read is a prepared query whose graphs come from the operation's bindings, every term typed (PRI-55), and the request's epoch, position and digest are compared in the classification and never sent. The studio's simulator classifies a step with the Java library's read, so a caller and the simulator cannot disagree.

## What changed

- The section "The confirmation" of `contracts/persistence/README.md` specifies the read, the facts it asks for by the guards of the operation, and eight rules applied in order. ADR-A132 has a dated note saying the libraries give it.
- The causes, each with the guard it answers:

| Cause | Guard |
|---|---|
| `Applied` | the transaction's claim holds the request's digest and no other |
| `IdempotencyKeyReuse`, refused | the claim holds another digest, or none |
| `EpochChanged` | the dataset's epoch for a template that guards on it, the version row's epoch otherwise |
| `Gone` | the aggregate is not tombstoned |
| `PreconditionFailed` | the expected position, or for an append that the stream's row exists |
| `AlreadyExists` | a create's absence of a version row, and a composite create's absence of the root's data |
| `KeyClaimHeld` | a key claim's absence of another owner |
| `NotApplied` | a guard that leaves no trace, such as a parameter's type, or a request still in flight, so the caller resends the identical request |

- Three points go beyond section 15.2 of the patterns guide, which has four rows. The epoch read follows the guard in force, since a template without the dataset guard guards on the row's epoch (TD-118). `AlreadyExists`, `KeyClaimHeld` and `NotApplied` are added, each defined by its guard.
- 42 vectors under `confirmationChecks` in `contracts/persistence/vectors.json`, decided by `verify-vectors.py` with its own code and by both libraries, cover every outcome and cause, the dataset-guarded and row-level forms of each kind of write, a claim in another graph or for another transaction, a claim with two digests or none, and the order of the rules.
- `lattice_persistence.confirm` in Python and `Confirmation.run` in Java. `PersistenceStep` calls the Java read, and its own classification is gone. A composite create over a root whose data exists, with no version row, is now `AlreadyExists` where the simulator said `NotApplied`. The run contract's outcome paragraph cites the library's read.
- The debt row on the confirmation read is closed and its row removed.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| P3a-T1 | each confirmation vector / classified by the verifier, by Python and by Java / the same outcome, cause and revision | L1 | | |
| P3a-T2 | the simulator's steps of SVA-P3 / run / the outcome the library gives, with the composite create now `AlreadyExists` | L1 | | |

## Checks run

| Command | Result |
|---|---|
| `mise run check:persistence-library` | vectors 136 checks passed, 0 failed. Python 136 passed. Java verify exit 0, 128 tests in its reports |
| `mise exec -- mvn -o -f platform/pom.xml -pl config-studio-transforms -am verify` | BUILD SUCCESS, the caller library 128, the outbox 2, the MORK transforms 7, the studio's core 24 and the run worker 60 tests, 0 failures |
| `mise run check:persistence` | 4941 passed, run by the delegated developer |
| `mise run check:identifiers`, `check:catalogue`, `check:published-decisions`, `check:agent-guidance` | passed, run by the delegated developer |

The first two were run by the delegated developer and again by the reviewer.

## Placement

T0. The persistence contract and its caller libraries are open.
