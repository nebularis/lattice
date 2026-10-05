<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: InsurML Alignment, Phase 0: Decisions and Engagement

**Unit ID:** `insurml-alignment-phase-0`
**Epic:** [insurml-alignment](insurml-alignment.md)
**Status:** Proposed, awaiting human review
**Status record:** the epic's [status record](../status/insurml-alignment.md), one section per phase
**Changes:** paper only. No ontology, tool or app changes

## Scope

Settle what the epic needs before any file under `ontology/`, `tools/`, `contracts/` or `apps/`
changes: the licence and publication route, the profile's shape, the decisions of gate 0, an
engagement brief for InsurML's owner, and four ADRs drafted as Proposed.

## Slices

| Slice | Content | Output | Estimate (tokens) |
|---|---|---|---|
| IMA-0.1 | engagement brief for InsurML's owner: Q-1 to Q-15, a summary of P-1 to P-14 and what each would give InsurML, the profile's intent, and collaboration options (IMA-D16) | a local note, untracked until IMA-D5 is decided. The human sends it | under 0.05M |
| IMA-0.2 | licence, publication and edition record: the answers to Q-2, Q-3 and Q-11, IMA-D5 and its consequence for the epic's documents on public branches | a section of the status record | under 0.02M |
| IMA-0.3 | ADR: the InsurML profile. Scope of `applied/insurance/wording/`, the two documents, alignment rules (bridge §3), identity adoption and key schemes (§4), typing T1, edition pinning, builder properties, AIR-5.9 moved (IMA-D2) | ADR, Proposed | 0.05M |
| IMA-0.4 | ADR: bridge tooling and kits. Where the lift, lower, assembler and parity suite live, where kits are published, their versioning, and their relation to the XML egress sketch's kits (IMA-D11, IMA-D12) | ADR, Proposed, under the topology rule | 0.04M |
| IMA-0.5 | ADR: placement elements in Wording (bridge §8), with law W8, the neutral cases, and the interim reference element | ADR, Proposed. Accepted before phase 3, not at gate 0 | 0.05M |
| IMA-0.6 | ADR: inline placement in a text (bridge §9), covering optional words, inline blocks and the words of amounts | ADR, Proposed. Accepted before phase 3 | 0.04M |
| IMA-0.7 | alignment edits once gate-0 decisions are taken: AIR epic and Phase 5 plan (AIR-5.9 moved), CCS plan §6 and the C7c brief's inputs, ingestion vision Q9 and Q11 notes, `INDEX.md` | edited plans | under 0.03M |

IMA-0.3 and IMA-0.4 may be drafted together. IMA-0.5 and IMA-0.6 are drafted now, so InsurML's
owner can review the substrate changes the alignment depends on before LATTICE builds them.

## Gate 0

| Criterion | Evidence |
|---|---|
| IMA-D1 to IMA-D5 and IMA-D16 decided | the epic's §7, marked with dates |
| the licence and publication route recorded | IMA-0.2 |
| the ADRs of IMA-0.3 and IMA-0.4 Accepted | the ADR index |
| the ADRs of IMA-0.5 and IMA-0.6 Proposed and reviewed by the human | the ADR index |
| answers to Q-1 to Q-3 received, or the epic recorded as proceeding clean-room only | the status record |
| the Phase 1 plan written | `insurml-alignment-phase-1.md` |

## Validation

Paper only: link checks and the prose rules of `.github/copilot-instructions.md`. Every ADR cites
the sketch section it decides and names its neutral case where it changes a layer.

## Out of scope

Any file under `ontology/`, `tools/`, `contracts/` or `apps/`. Sending anything to InsurML's owner,
which the human does.
