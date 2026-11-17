<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: multi-store architecture

**Unit ID:** `multi-store-architecture`
**Prefix:** MSA
**Status:** planned 2026-11-17, from the [sketch](../sketches/multi-store-architecture.md) of 2026-11-12. The unit's name and prefix are the sketch's proposal, taken provisionally until the maintainer confirms them (MSA-Q14)
**Status record:** [multi-store-architecture.md](../status/multi-store-architecture.md)
**Decisions it builds on:** the sketch's D1 to D6, ADR-A48, ADR-A74, ADR-A75, ADR-A123, ADR-A124, ADR-A125, PRI-51, PRI-52
**Placement:** open. Platform, tooling and substrate configuration, nothing domain-specific

## Why

The sketch's §2 shows the fault the epic starts from: the logical contract of a generated operation is derived from its SPARQL, so a second realisation has nothing to be lowered from. The sketch states leanings about placement, crossings, the neutral IR, the mapping and the port, each ratified by the maintainer as a leaning and none decided. This plan runs the twelve investigations of its §6, which try to disprove those leanings cheaply before anything is built.

## Outcome

Each investigation reports whether the leaning it tests survives, with the evidence, against the falsifier the sketch's §6 states for it. The questions MSA-Q1 to MSA-Q18 are then put to the maintainer with that evidence. Building the port, the IR or a relational realisation is the next plan's, written on the answers.

## Out of scope

Everything the sketch's §9 leaves out. Any change to `tools/persistence`, the port or the store SPI beyond what an investigation needs to measure, and none of that merges into code that runs. Amending the texts in the sketch's §8, which waits for the answers.

## Order and dependencies

The sketch's §4.14 order holds. The persistence model rests on no ledger law, so MSA-I1, MSA-I3, MSA-I4, MSA-I9, MSA-I11 and MSA-I12 start now. MSA-I2 reads the ledger's examples and MSA-I5 uses the proof gate, and both take the ledger branch first. MSA-I7, MSA-I8 and MSA-I10 name the ledger's records and wait for its runtime document, LG-2. MSA-I6 waits on the choice of a protocol toolchain. The dependency graph is the sketch's §6.

## Slices

Each slice is the sketch's investigation of the same identifier, with the falsifier and estimate its §6 gives. One Validation Pack each, `docs/developer/validation/MSA-I<n>.md`.

| Slice | Kind | Where its work lives | Waits on |
|---|---|---|---|
| MSA-I1 | script | `spikes/multi-store-shape-census/` | the threshold, proposed below |
| MSA-I2 | paper | `docs/developer/notes/multi-store/` | the ledger branch |
| MSA-I3 | paper | `docs/developer/notes/multi-store/` | none |
| MSA-I4 | paper | `docs/developer/notes/multi-store/` | MSA-I3 |
| MSA-I5 | proofs | `spikes/multi-store-model/` | MSA-I4, the ledger branch's proof gate, and the shared types of positions and amounts agreed (sketch §4.14) |
| MSA-I6 | models | `tools/models/<topic>/` | MSA-I2, MSA-I9, and the choice of TLA+ or Quint (Track H records it as not chosen) |
| MSA-I7 | benchmark | `benchmark/` | the ledger's runtime document, LG-2 |
| MSA-I8 | proof of concept | `spikes/` | MSA-I5, MSA-I6, MSA-I7, MSA-I10 and the ledger's design |
| MSA-I9 | probes | `spikes/multi-store-stream-probes/` | none |
| MSA-I10 | paper | `docs/developer/notes/multi-store/` | MSA-I1, LG-2 |
| MSA-I11 | paper | `docs/developer/notes/multi-store/` | MSA-I4 |
| MSA-I12 | proof of concept | `spikes/multi-store-emitted-topology/` | none |

## Proposed for the maintainer's confirmation

- **MSA-Q14.** The unit is `multi-store-architecture` with prefix MSA, as the sketch proposes, and its slices are its investigations.
- **MSA-I1's threshold.** The sketch's falsifier for MSA-I1 needs a threshold agreed before the census runs. We propose that the mapping is worth building where closed shapes with bounded counts cover at least 80% of the subjects of the sample graphs, counted per family. The census reports the share whatever the threshold, so it runs before the answer and is read against it after.
- **The protocol toolchain for MSA-I6.** Both TLA+ (TLC 2.19) and Quint 0.33.1 with Apalache run here. The choice is Track H's FMH-5 toolchain spike, which the epic adopts (D5), and is put to the maintainer before MSA-I6 starts.
