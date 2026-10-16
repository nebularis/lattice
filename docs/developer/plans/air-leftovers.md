<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Insurance Reference — Leftovers

**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Purpose:** everything the epic decided not to build, so it is recorded once. A consumer may
build any of these on LATTICE, openly or in a proprietary product. Each row says what LATTICE
already provides for it to build on. Items deferred to a later LATTICE slice are not leftovers,
and are listed at the end only so they are not mistaken for them.
**Started:** 2026-10-14.

## 1. Information requests: the workflow around them

The earlier designs' carrier question bridge was compared with AIR-6.1 on 2026-10-14
(AIR-6.1-Q1). AIR-6.1 builds requests, answers as assessments and derived gaps. The rest is
workflow and presentation:

| Leftover | What it would do | What LATTICE provides to build on |
|---|---|---|
| answer review states | draft, reviewed and confirmed states on an answer before it counts | answers are `aeo:Assessment`s with evidence. A review state would sit on the assessment or in the consumer's workflow store |
| question-specific guidance | help text written for one insurer's question or one client | each attribute type's definition and notes (AIR-4.2) say what is meant |
| staleness policy | treating an answer older than a set age as a gap | every assessment's temporal scope and evidence date. The age limit is the consumer's policy, applied in its own `gaps` variant |
| remediation tasks | assigning each gap to the client, a broker or a data supplier, with a status and a deadline, and chasing it | `sbm:InformationGap`s, derived and re-derivable. The third-party enrichment assessment kind records data bought in |
| client data requests | rewording insurer questions for the client, explaining why each is asked, prioritising, setting deadlines, and presenting input forms | open gaps and the requests behind them, with each attribute type's form, space or scheme contract to drive an input control |
| a catalogue of answering queries | stored queries that answer recurring insurer questions from existing data (total insured value in a territory, locations near water) | derivations as code in `tools/` producing derived artefacts, spatial joins under the S6 guidance, and MORK query templates |
| question interpretation | mapping an insurer's free-text question to attribute types and profile families, by a person or a model | MORK's review queue (ADR-A13) for proposed mappings, and the attribute type contract as the target |
| question analytics | counting how often each question recurs, and deciding when a new attribute type or profile shape is worth adding | new attribute types and shapes are ordinary vocabulary editions and shape files. Generated classes are optional in Surface |

## 2. Other things this epic does not build

From [epic §7](applied-insurance-reference.md#7-out-of-scope):

| Leftover | Note |
|---|---|
| catastrophe model results: model runs, event sets, event and year loss tables, exceedance probability curves, hazard footprints | could become a LATTICE follow-on unit aligned with Oasis's Open Results Data. AIR-4.3's peril metrics cite a model's output by IRI as evidence |
| catastrophe model internals | vendors' hazard, vulnerability and financial modules |
| exposure of portfolios of many insureds (a cedent's treaty portfolio, a binding authority's bordereau) | Open CBAA's risks cover bordereaux. A treaty portfolio belongs with the contract module's reinsurance structures |
| pricing | technical and market pricing, rating, quote comparison |
| a consumer's statement modules and decision logs | |
| maintained market editions | every edition in the epic is an example. Real ones are published by their owners and bound by scope |
| runtime stores and user interfaces | |

## 3. Deferred inside LATTICE, not leftovers

| Item | Where it is tracked |
|---|---|
| an insured's licences and permits | epic §7, after the Instrument rewrite (CCS C9) |
| crosswalk of the CBAA cause-of-loss list | AIR-3.4-Q1, once its owner's terms are confirmed |
| maximum foreseeable interruption derived from dependencies | AIR-4.3, deferred |
| link from a requirement to `ins:Obligation` | Phase 5 (Q12) |
| contract module, claims, occurrence grouping, causation profiles | Phase 5, AIR-6.2 to AIR-6.4 |
| substrate items S1, S2, S4, S5, S7 | the substrate track |
