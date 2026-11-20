<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I6, the protocol models

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I6, with TLA+ and TLC as the maintainer decided on 2026-11-17
**Machine:** machine S, Windows, TLA+ tools 1.7.4 (TLC 2.19) on Java 25, the jar installed locally and named to the runs by `TLA2TOOLS_JAR`. **Placement:** T0, public. Protocol models, nothing domain-specific.
**Status:** built 2026-11-18, not verified, in part. What is left is listed under deliberate non-coverage.

## Scope

- `tools/models/multi-store-protocols/`, five TLA+ modules and twenty-eight configurations, with a README that states what each models, what it abstracts away and every result.
  - `ModelA_GuardedCas`, FMH-5's model A, a guarded compare-and-set under an atomic store and under a snapshot store with no write-write conflict detection.
  - `X1_SerialisedApply`, one writer per key applying a stream's commands to two stores, with crashes, a zombie that outlives its turn, offsets stored as applied or as received, and a reader of both stores.
  - `X2_EvidenceAcrossStores`, a core reading evidence in another store under the watermark row and the best-known row, with an audit over the recorded read set.
  - `X3_ReceiptRelay`, receipts as the outbox, a relay publishing by one global commit position or by each stream's next sequence number, with late arrival and restarts.
  - `X4_AuthorityCutover`, a family's authority moved from one store to another while writers are live, naively or with the old authority fenced first.
- The models were written with two sub-agents and every configuration was run, its result read and recorded in the README.

## Result in one paragraph

The falsifier, that a row of the catalogue cannot state a guarantee the model keeps, does not fire for the five rows modelled. A single-store transaction keeps no lost update only where the store is atomic or detects write-write conflicts, which is a capability the row has to name. The serialised writer keeps order, at most once in effect and eventual application for up to three incarnations including a zombie, and gives no atomic visibility, as the sketch's revised row says. Storing received offsets breaks eventual application, which is MSAI9-06 reproduced in the model and the fix of MSA-F1 confirmed in it. The watermark read keeps evidence equal to the source as of the decision's position and waits forever when the source stalls. The best-known read never waits, and the audit over its read set flags every decision whose evidence was superseded, and some that were not. Receipts serve as the outbox only with a relay that follows each stream's sequence, since a relay by global commit position skips a late receipt for good. A cutover keeps every acknowledged write only with the old authority fenced before the copy.

## Each row of the catalogue against the models

| Row (sketch §4.2) | Model | Guarantee kept | What it needs |
|---|---|---|---|
| single-store transaction | Model A | no lost update | an atomic request, or write-write conflict detection, named in the capability record |
| outbox | X3 | every committed receipt published, in order within a stream, at least once | a relay that tracks each stream's next sequence number, and an idempotent consumer |
| named saga | none | not modelled | |
| one serialised writer per key | X1 | ordered, at most once in effect, eventually applied, never atomic visibility | a guard in each store and offsets stored as applied (MSA-F1) |
| read as of a position, gated on a watermark | X2 | the evidence is what the source held at the position | a source that advances its watermark, without which the evaluation waits for ever |
| read of the best known, with its read set | X2 | an audit over the read set finds every superseded read | the read set's positions recorded on the decision |
| a change of authority while live (model X4, not a row) | X4 | no acknowledged write lost, none acknowledged by both | the old authority fenced before the copy |

## Commands and results

Each configuration was run from the model directory with `java -XX:+UseParallelGC -cp $TLA2TOOLS_JAR tlc2.TLC -deadlock -config <cfg> <module>.tla`, `-workers auto` where no error was expected and `-workers 1` where a counterexample was. The README's results table has every run's states, distinct states, depth and counterexample. In summary, 28 configurations ran, 13 with no error and 15 violating the property they were built to show violated. No property expected to hold was violated.

| Command | Result |
|---|---|
| `mise exec -- python tools/writing_rules.py tools/models/multi-store-protocols/README.md` | 0 failures |

## Deliberate non-coverage

- **FMH-5's models B, C and D** (the append form, the create race, the key claim) and its capability-record extension. Track H owns FMH-5, which the epic adopts (D5). Model A is built here and FMH-5's board row is unchanged, since most of it is not built.
- **The named saga row.** Not modelled.
- **Isolation probes on PostgreSQL and Fuseki**, which the sketch's §6 asks to ground each model. Not run.
- **Trace validation against the Isabelle model.** It needs MSA-I5's mechanised IR, which waits on the shared types.
- **Scope.** Every result holds for the small constants of its configuration only, two or three writers, streams or commands, positions up to three and at most two crashes.
- **Apalache.** Not used. TLC's explicit search suffices at these sizes.

## Decisions taken

- **Configurations that show a failure are kept beside those that show a guarantee.** A row's guarantee is stated by what holds with its requirement and what breaks without it, so each requirement in the table above has a configuration that removes it.
- **`X1_Unguarded` and the timeouts of X4** were added beyond the brief, to show what the guard and the fence are each worth.
