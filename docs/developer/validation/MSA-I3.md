<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I3, every dimension against SPARQL, SQL and GQL

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I3
**Machine:** paper, checked against the source on `spi/sql-backend` at 2026-11-17. **Placement:** T0, public. Platform configuration, nothing domain-specific.
**Status:** authored, not accepted. The maintainer's review is the sign-off.

## Scope

- The note [MSA-I3-dimensions-by-dialect.md](../notes/multi-store/MSA-I3-dimensions-by-dialect.md), which classifies the thirty resolved dimensions of the persistence compiler, the settings carried on profile nodes, uniqueness, identity, resolution inputs and run options as semantic, layout, parameter or without meaning, per dialect, with the capability fields each depends on.
- An inventory of the configuration space gathered from `operations.py`, `capability.py`, `contract.py`, `resolver.py`, `model.py`, `validator.py`, `builders.py` and `persistence.ttl`, used as working material and not committed. Every claim the note makes about the code was read again in the source.
- Out of scope. Any change to the vocabulary or the compiler. The splits the note proposes are ontology changes under ADR-A86 and wait for MSA-Q11.

## Result in one paragraph

The falsifier does not fire. Twenty-seven of the thirty resolved dimensions have one class in every dialect as they stand. Three (`aggregateBoundary`, `deadlockPolicy`, `erasureStrategy`) carry values of two classes and split cleanly by value. Resolution makes the one capability-dependent choice in semantic selection, dropping profiles whose scope needs reasoning when the store does not reason, so the same configuration can mean different things on two stores. That has two repairs, of which a refusal after semantic selection is the smaller. The note's port test and the sketch's guarantee test disagree on `metaTopology` alone, which the note reads as a layout with a cost in retries and leaves for MSA-I6 to check.

## Checks

| Claim in the note | Checked against |
|---|---|
| `PreCreatedRow` replaces `create-if-absent` with `bootstrap-version-row` | `operations.py`, `select_operations` |
| the value of `metaTopology` is not read, only `metaShards` | `operations.py`, `select_operations` |
| resolution drops candidates needing reasoning when `provides_reasoning` is false | `resolver.py`, `_select` |
| `providesSingleWriter` and `providesStatementLevelConflictDetection` are read by nothing | `capability.py`, and a search of `tools/persistence` |
| `-rows` is chosen from `replaceForm` or `providesSnapshotUpdateSemantics` | `operations.py`, `rows_replace` |
| each of the six no-receipt and patch-log stems has a dataset-guard variant | `builders.py`, `_receipt_variants` |
| TD-118's stated blocker | `docs/developer/technical-debt.md` and `model.py`'s comment on the baseline |
| SQL and GQL realisations | [lattice-sql.md](../notes/rdf-engine/lattice-sql.md) §9 and [lpg-backend-options.md](../notes/lpg-backend-options.md) §4.3, cited and not repeated |

| Command | Result |
|---|---|
| `mise exec '--' python tools/writing_rules.py docs/developer/notes/multi-store/MSA-I3-dimensions-by-dialect.md` | 0 failures |

## Adversarial probes

1. The note looked for a dimension that is semantic in one dialect and a layout in another, which is what the falsifier names. `firstWrite` is the nearest case. It changes the operation set in every dialect, so it is semantic everywhere, and only its safety motive is SPARQL's.
2. The count was redone after the first draft, which had said twenty-one stable dimensions where the table gives twenty-seven.
3. The port test was checked against the RDF-shaped port of today. Under it `--caller-graph-names` and `graphIriTemplate` would look semantic, because the port exposes a graph name. The note records this as §4.8's case against that port.

## Decisions taken

- **The port test, not the guarantee test.** A dimension is semantic when a caller of the logical port can observe it. The sketch's wording asks whether a guarantee depends on it, which places `metaTopology` above the line for a cost in retries.
- **GQL is read as a product with transactions and a key constraint.** Products differ, and the capability record has to say which a store is.
- **The ETag dimensions are without meaning to a store.** They are read at the HTTP surface.

## Open matters

- The splits of §4.1 to §4.3 and the repair of §4.6 are proposed with MSA-Q11.
- The claim of §4.5 goes to MSA-I6.
- The observations of the note's §8 are for the maintainer's triage, among them TD-118's blocker, which may be gone.
