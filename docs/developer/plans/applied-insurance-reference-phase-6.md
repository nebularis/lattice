<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 6, Submission and Claims

**Unit ID:** `applied-insurance-reference-phase-6`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** AIR-6.1 detailed 2026-10-13, for the one trip (lanes §4). AIR-6.2 onwards wait for
Phase 5 (epic D2).
**Sketches:** [asset-exposure-ontology.md](../sketches/asset-exposure-ontology.md) §1,
[peril-structure-whitepaper.md](../sketches/peril-structure-whitepaper.md) §5 (N7, N10), [term-parameters.md](../sketches/term-parameters.md) §7

## Scope

`submission/` packages an exposure set version, requirements and existing cover for one
placement. `claims/` records claims, loss cause chains and the filling of claimant, harmed and
payee roles against the responding contract.

**Changed by CCS (2026-09-30).** A claim is a case for the responding policy's relations, and its
handling is a set of occasions in Behaviour ([computable-contract-substrate](computable-contract-substrate.md)
tranche D): notice as a condition precedent, advancement duties, relation back as a deeming, and
parties resolved per claim.

## Slices

| Slice | Content |
|---|---|
| AIR-6.1 | submission package, its lifecycle and its citation of an exposure set version |
| AIR-6.2 onwards | claims, planned in [applied-insurance-reference-claims.md](applied-insurance-reference-claims.md) |

**Claims moved to their own plan (2026-10-16).** The [claims plan](applied-insurance-reference-claims.md)
subsumes AIR-6.2 to AIR-6.4 with a fuller treatment, from the [claims sketch](../sketches/insurance-claims-ontology.md)
and its companions. AIR-6.2 is now the claims core, AIR-6.3 (aggregation) and AIR-6.4 (causation
profiles) keep their meaning, and AIR-6.5 to AIR-6.12 and AIR-6.W0 to AIR-6.W7 are new. This plan
keeps AIR-6.1 (submission).

Milestone M6 closes in AIR-6.1 and the claims plan's AIR-6.5.

## AIR-6.1 in detail

**Added 2026-10-21, from phase 7's P7-Q2.** A request records the structure the broker asks for, as
requested layers: each an attachment, a limit and a basis on the loss axis, with the scope it is
asked for. A requested layer is a fact of what was asked, never the reference against which anything
is computed as missing. Placed layers are phase 7's (AIR-7.1). If AIR-6.1 is built on its trip
before this note reaches that branch, the requested layer is added by AIR-7.0's examples instead.

**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-6.1] …`, the
last being `[AIR-6.1] Handoff`. **Validation Pack:**
[applied-insurance-reference-6.1](../validation/applied-insurance-reference-6.1.md). **Decisions:**
ADR-A98 (decision 6: the prefix is fixed when the module is built). **Sketch:** asset exposure
ontology §1, §5.8. **Milestone:** M6, first half. **Decided 2026-10-14:** AIR-6.1-Q1 (below), at
its leaning.

**Invariant:** a submission cites one exposure set version and the requirements and existing cover
of that version, records which insurers were approached and how each responded, and records what
each insurer asked for. Information gaps are derived from the data, never authored, and adding data
only ever closes gaps.

**AIR-6.1-Q1, how much of the earlier designs' question bridge.** Decided: information requests,
answers as assessments, and gaps as derived artefacts, as below. Not the earlier designs' answer
types (an attribute type's value form already says what an answer looks like), placeholders (an
open request is the placeholder), remediation actions and client request packages (workflow, which
belongs to a consumer), or inference rules (derivations are code in `tools/`, as AIR-4.3's are).
What is left out, and what each item can build on, is in [leftovers](air-leftovers.md) §1.

### Module

`ontology/applied/insurance/submission/`, literate from the start (AIR-2.0): `README.md`,
`spec/submission.ttl`, `vocab/submission-vocab.ttl`, `shapes/` with `.version` `0.1.0`,
`examples/`. Namespace `https://www.nebularis.org/neuro-semantic/insurance/submission#`, prefix
`sbm:` (proposed here under ADR-A98 decision 6), vocabulary `…/insurance/submission/vocab#`
(`sbm-voc:`). Version IRIs `…/insurance/submission/0.1.0` and `…/insurance/submission-vocab/0.1.0`.
The spec imports the exposure spec (`0.1.0`), and Foundation, Vocabulary and Party at the versions
of `main` at the branch point. The `insurance/domain-README.md` and `ontology-architecture.md` rows
are added, and the tests go in `tools/test_submission.py`, modelled on `tools/test_exposure_ontology.py`.

### Spec

| Term | Definition |
|---|---|
| `sbm:Submission` | `⊑ fnd:Version ⊓ fnd:Governable ⊓ fnd:Evidenced`, identity `sbm:SubmissionIdentity`. Exactly one `sbm:exposureSet` (an `aeo:ExposureSet` version, not its identity), any number of `sbm:requirement` (`aeo:CoverageRequirement`) and `sbm:existingCover` (`aeo:ExistingCover`), at least one `sbm:classOfBusiness` (`⊑ icm:classOfBusiness`), any number of `sbm:placementScope` (`voc:BindingScope`, the markets and regimes, which select the scheme bindings and the market profile, AIR-4.6), at most one `sbm:proposedPeriod` (`fnd:TemporalScope`), at most one `sbm:presentedBy` (`pty:RoleOccupancy`, the broker) |
| `sbm:Approach` | `⊑ fnd:Evidenced ⊓ fnd:TemporallyScoped`. Exactly one `sbm:approachOf` (submission), exactly one `sbm:insurer` (`pty:Actor`), exactly one `sbm:approachStatus` |
| `sbm:InformationRequest` | `⊑ fnd:Evidenced`. Exactly one `sbm:requestOf` (approach), exactly one `sbm:requestStatus`, any number of `sbm:asksForAttribute` (attribute type concepts, AIR-4.2) and `sbm:asksForFamily` (profile family concepts), at most one `sbm:questionText` (the insurer's own words, `xsd:string`), any number of `sbm:answeredBy` (`aeo:Assessment` or `fnd:Evidence`) |
| `sbm:InformationGap` | `⊑ fnd:DerivedArtefact`. Exactly one `sbm:gapIn` (submission), exactly one `sbm:missingAttribute`, exactly one `sbm:gapSubject` (location, asset or legal entity), at most one `sbm:gapFor` (the request it answers, or none when the gap comes from a peril's relevant attributes) |

A submission is a new version when the exposure set version it cites changes, so an insurer's
quote always refers to the data it saw.

### Vocabulary

| Contract, constrains | Reference concepts |
|---|---|
| `ApproachStatusContract` | `Sent`, `InformationRequested`, `Declined`, `Quoted`, `Withdrawn` |
| `RequestStatusContract` | `Open`, `Answered`, `Waived`, `Withdrawn` |

A decline here is a response to this submission. When it should count as cover history (AIR-4.4's
`Declined`) is the broker's judgement, recorded there as its own evidenced fact, and the notes say
so.

### Code (`tools/submission_gaps.py`)

`gaps(graph, submission, run)` returns the gaps as a separate graph: for each open request asking
for attribute types (directly or through a family's profile shape), each subject of the cited
exposure set of the right kind with no value of that type in any assessment, and for each peril in
the scope of a cited requirement, the relevant attributes AIR-4.2's completeness shape would warn
about. Gaps are derived, so answering a request is adding an assessment and re-running the
function, never editing a gap.

### Shapes

| Shape | Rule | Severity |
|---|---|---|
| submission | the cardinalities above | violation |
| members of the version | every cited requirement and existing cover is a member of the cited exposure set version | violation |
| active data | an Active submission cites an exposure set version that is not Draft | violation |
| approach | the cardinalities above | violation |
| answered | a request with status `Answered` has at least one `sbm:answeredBy` | violation |
| gap | the cardinalities above, and a gap is never authored without a derivation run | violation |

### Examples (`examples/submission.ttl`) and tests

AIR-4.6's US worked example, submitted to two insurers under `ex:us-market` and
`ex:us-risk-regime`, one of which asks for the roof attributes of every location and the cyber
posture of the insured. One location already has them, so the gaps are the others'.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR61-01 | the module / loaded with its imports / parses, its contracts conform | L1 | + |
| AIR61-02 | the example / every shape of the submission and exposure modules / no result | L1 | + |
| AIR61-03 | M6, first half: the submission / read / it cites one exposure set version, and every requirement and cover it cites is a member of it | L1 | + |
| AIR61-04 | a submission citing a requirement of another version / validated / violation | L1 | − |
| AIR61-05 | `gaps` over the example / called / one gap per location without roof attributes, and the cyber posture gap | L2 | + |
| AIR61-06 | an assessment answering one gap added / `gaps` again / exactly that gap gone, none added (monotonicity) | L2 | + |
| AIR61-07 | a request marked `Answered` with no answer / validated / violation | L1 | − |
| AIR61-08 | every concept / the documentation shape / each has a note | L1 | + |

## Exit gate

AIR-6.1's part of M6 demonstrated. The claims plan has its own exit gate (its §10), which closes the rest of M6, and M7 and M8.
