<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Claims sketch: references, definitions and crosswalks

Companion to [insurance-claims-ontology.md](insurance-claims-ontology.md) (the claims sketch), draft
for review, 2026-10-16. It records what the claims sketch took from each source, LATTICE's own and
external, the definitions it relies on, and two crosswalks: to ACORD's P&C claims messages and to
the claims fields of Lloyd's Coverholder Reporting Standards v5.2. The wire formats themselves are
explored in [claims-wire-formats.md](claims-wire-formats.md).

**How each source relates**, in the terms the peril and exposure work used:

| Relation | Meaning |
|---|---|
| **conformed** | the data is built on it |
| **mapped** | its codes are carried, or crosswalked, or used as a key scheme |
| **followed** | its definitions or rules are cited in notes, and shape the model |
| **exchanged** | it is a format MORK maps in or out |
| **influenced** | it shaped a design choice, and nothing in the model names it |

**Verification status.** Every external fact below carries one of three marks. **Checked** means
read from the publisher or a published schema on 2026-10-16. **Recalled** means cited from general
knowledge and not checked against the source in this session, so it must be checked before it goes
into a concept's note. **Counsel** means a legal proposition stated as background, to be confirmed
by counsel before any rule is encoded (claims sketch §2).

---

## Contents

1. [LATTICE's own sources](#1-lattices-own-sources)
2. [Law and regulation](#2-law-and-regulation)
3. [Standards and identifiers](#3-standards-and-identifiers)
4. [Market practice](#4-market-practice)
5. [Definitions used by the claims sketch](#5-definitions-used-by-the-claims-sketch)
6. [Crosswalk: ACORD P&C claims messages](#6-crosswalk-acord-pc-claims-messages)
7. [Crosswalk: Lloyd's claims bordereau (CRS v5.2)](#7-crosswalk-lloyds-claims-bordereau-crs-v52)
8. [What the crosswalks show](#8-what-the-crosswalks-show)
9. [Corrections to the claims sketch](#9-corrections-to-the-claims-sketch)

---

## 1. LATTICE's own sources

| Source | What the claims sketch took | Where in the sketch |
|---|---|---|
| [computable-contract-substrate.md](computable-contract-substrate.md) §1 | the three strata (wording, instrument, behaviour), so a claim reads the contract's meaning and state and never restates its cover | §1, CL2 |
| CCS §5.2 to §5.7 | the five legal relation classes, parties fixed at arising (law I11), the notice-duty chain, deemings as the licence for absence, the burden on the party relying on an exception (law I7) | §2, §7.3, §11.2 |
| CCS §6.3, §6.4 | structure and state kept apart (DP6), and the three kinds of judgement: findings, determinations by a party, deemings | §7.7, §11.1 |
| CCS §7.4, §7.4.1 | regimes stated once with occupancies per subject, which makes "one claim, many instruments" and what-if erosion over proposals possible without copying | §7.5, §10.2 |
| CCS §7.6 | occasions per case and their core states, roles filled later by new occupancy versions | §7.4, §8.2 |
| CCS §7.8, §7.9 | static parameters in Instrument and dynamic quantities elsewhere, `ins:computedBy` for computed amounts | §7.6.1, §9.3 |
| CCS §10 scenario catalogue (S1, S7, S14, S15, S25, S27, S30, S34, S46, S58) | notice and advancement deadlines, breach chains, conditions precedent, classification of terms, relation back, procedural conditions on powers, consent to settle, subrogation as a deeming, delegated claims authority, role tables per segment | §2, §7.3, §7.10, §10.1 |
| [CCS plan](../plans/computable-contract-substrate.md) C9b and `reinsurance-claims-cooperation.ttl` | follow the settlements and claims co-operation as a consent rule on the reinsured's power to settle | §2.1, §10.3 |
| [Instrument README](../../../ontology/instrument/README.md) §6.4 | legal acts: declarations, proposals, exercises, `ins:forCase`, `ins:pursuantTo`, "juristic acts only" | §7.3, §7.7, §7.10 |
| Instrument README §10, §13 | the six legal triggers and their kinds, anchored due ranges, tolling | §8.2 |
| [Behaviour README](../../../ontology/behaviour/README.md) and `occasion-refinement.ttl` | handling stages as a deployment's refinement of `bhv:Arisen`, deep history on reinstatement, law B9 | §8.2, CL-Q2 |
| `disputed-occasion.ttl`, `run-off.ttl` | a per-occasion dispute regime, claims servicing as a region of run-off | §4, §8.4 |
| [nested-states-and-history.md](nested-states-and-history.md) | composite states, history, concurrent regimes | §8.2 |
| [terms-in-time.md](terms-in-time.md) | anchored time and ending | §8 |
| [consent-and-group-powers.md](consent-and-group-powers.md) §4.2, §4.3 | consent of a group, consent delegated to a lead, the reinsurance case | §7.5, §10.3 |
| [contract-amounts.md](contract-amounts.md) A1 to A58 | the catalogue of limits, retentions, erosion, order of payment, reinstatement, aggregation bases, parametric payouts | §9.3, §7.11, §14 |
| [evaluation-context.md](evaluation-context.md) §3 to §5 | the ledger of nested accounts, combinators (`sum`, `max`, `proRata`, `split`, `convert`), Undetermined absorbing | §7.9, §9.3 |
| [term-parameters.md](term-parameters.md) §7 | four roles, direction derived, Sides A, B and C | §7.8, §14.2 |
| [ADR-A102](../../architecture/decisions/ADR-A102-liability-direction-from-party-roles.md) | the role individuals in `insurance/common`, contracts naming populations not people, direction as a derived artefact | §7.2, §7.8 |
| [asset-exposure-ontology.md](asset-exposure-ontology.md) and the exposure module (AIR-4.1 to AIR-4.5) | `aeo:LossCause` with recorded and effective characteristics, loss experience and loss record, assets, interests, valuations with rate and horizon, programme roles, counterparty populations | §7.1, §7.6, §13.3 |
| [peril-vocabulary.md](peril-vocabulary.md) §6.8, §8 | the cyber write-back profile over one cause link, what the vocabulary leaves to wording | §7.1, §14.1 |
| [peril-structure-whitepaper.md](peril-structure-whitepaper.md) §3.8, §3.11, N7, N10, W-Q2, W-Q3 | causation by governing law, occurrence grouping by peril window, the open legal review | §2.3, §2.4, §7.12 |
| [mork-bridge.md](mork-bridge.md) B1 to B6, §4, §6 | the operative scheme is the contract's, never guess, mapping is data, exactness sets authority, lowering never invents codes, bordereau ingestion as MORK mappings | CL7, CL8, §13 |
| [robustness-testing-approach.md](robustness-testing-approach.md) §4 | the claims workload: about 64,000 open claims market-wide, a catastrophe burst of about 130,000 claims and 2 to 3 first notices a second at peak | §14.3 |
| [Persistence README](../../../ontology/persistence/README.md) §7.1, §7.4, §7.9 | aggregate boundaries, receipt pruning, privacy profiles and `dal:ErasurePrecedence` | §12 |
| [ADR-A114](../../architecture/decisions/ADR-A114-external-and-natural-keys.md) | keys and key schemes for claim references | §7.4 |
| [assurance-records.md](assurance-records.md) | the EARL and PROV-O profile for what was checked | §16 |
| [air-leftovers.md](../plans/air-leftovers.md) §1 | workflow around requests stays with consumers | §8.3 |
| [AIR phase 6 plan](../plans/applied-insurance-reference-phase-6.md) | the original AIR-6.2 to AIR-6.4 slices, which §18 proposes to replace | §18 |
| [ADR-A98](../../architecture/decisions/ADR-A98-applied-layout-and-insurance-modules.md) | module layout, the claims prefix left to be fixed, claims importing exposure and contract | §6, CL-Q1, CL-Q7 |

---

## 2. Law and regulation

Each row: the proposition the claims sketch used, as it understood it, and its mark.

### 2.1 Case law

| Authority | Proposition used | Sketch | Mark |
|---|---|---|---|
| *Leyland Shipping v Norwich Union Fire Insurance Society* [1918] AC 350 (HL) | the proximate cause is the dominant or effective cause, not the last in time | §2.4 | Counsel |
| *Wayne Tank and Pump Co v Employers Liability Assurance Corp* [1974] QB 57 (CA) | where two concurrent proximate causes operate and one is excluded, the exclusion generally prevails | §2.4 | Counsel |
| *Ventouris v Mountain (The Italia Express) (No 2)* [1992] 2 Lloyd's Rep 281 | an indemnity insurer is in breach when the loss occurs, so the insured's claim is for damages | §2.1 | Counsel |
| *Sprung v Royal Insurance (UK) Ltd* [1999] Lloyd's Rep IR 111 (CA) | no damages for late payment beyond the indemnity under the law as it then stood, which s.13A later changed | §2.1 | Counsel |
| *Post Office v Norwich Union Fire Insurance Society* [1967] 2 QB 363 (CA) | a liability insured's right against its insurer arises when its liability is established and quantified | §2.1 | Counsel. Corrected in the sketch (§9) |
| *Bradley v Eagle Star Insurance* [1989] AC 957 (HL) | the same rule, applied to the 1930 Act's transfer of rights | §2.1 | Counsel |
| *Gray v Zurich Insurance Co* (1966) 65 Cal.2d 263 | the duty to defend is broader than the duty to indemnify and arises on a potential for cover | §2.1 | Counsel |
| *Gruenberg v Aetna Insurance Co* (1973) 9 Cal.3d 566 | tort liability for bad faith refusal to pay | §2.1 | Counsel |
| *Insurance Co of Africa v SCOR (UK) Reinsurance* [1985] 1 Lloyd's Rep 312 (CA) | follow the settlements, where the reinsured acted honestly and in a proper and businesslike way | §2.1 | Counsel, already cited by `reinsurance-claims-cooperation.ttl` |
| *Hill v Mercantile and General Reinsurance* [1996] 1 WLR 1239 (HL) | the limits of follow the settlements | §2.1 | Counsel. Corrected in the sketch (§9) |
| *Scor v Eras International (No 2)* [1995] 2 All ER 278 | a claims co-operation condition precedent stops the reinsurer's liability arising | §2.1 | Counsel |
| *Keene Corp v Insurance Co of North America* 667 F.2d 1034 (D.C. Cir. 1981) | continuous trigger for long-tail injury | §2.2 | Counsel |
| *Montrose Chemical Corp v Admiral Insurance Co* (1995) 10 Cal.4th 645 | continuous injury trigger for occurrence policies in California | §2.2 | Counsel |
| *Durham v BAI (Run Off) Ltd* (the Trigger litigation) [2012] UKSC 14 | for employers' liability mesothelioma cover, injury is "sustained" at exposure | §2.2 | Counsel |
| *Axa Reinsurance (UK) v Field* [1996] 1 WLR 1026 (HL) | "event" is narrower than "originating cause" | §2.3 | Counsel |
| *AIG Europe v Woodman* [2017] UKSC 18 | aggregation of related matters by a unifying factor | §2.3 | Counsel |
| *Lloyds TSB General Insurance Holdings v Lloyds Bank Group Insurance* [2003] UKHL 48 | aggregation on a related series of acts or omissions looks to the acts, not their consequences | §2.3 | Counsel |
| *Versloot Dredging v HDI Gerling* [2016] UKSC 45 | a collateral lie is not a fraudulent claim | §2.5, §11.2 | Counsel |
| *Castellain v Preston* (1883) 11 QBD 380 (CA) | the indemnity principle and the insurer's subrogation | §2.5, §10.1 | Counsel |

### 2.2 Statutes and rules

| Instrument | Provision used | Sketch | Mark |
|---|---|---|---|
| Insurance Act 2015 (UK) | s.12 remedies for fraudulent claims. s.13A implied term to pay sums due within a reasonable time | §2.5, §2.1 | Recalled |
| Enterprise Act 2016 (UK) | s.28 inserted s.13A | §2.1 | Recalled |
| Marine Insurance Act 1906 (UK) | s.79 subrogation, s.80 contribution, s.81 underinsurance | §2.5, §10.1 | Recalled |
| Third Parties (Rights against Insurers) Act 2010 (UK) | a third party's rights against the insurer of an insolvent insured | §2.1 | Recalled |
| Road Traffic Act 1988 (UK) | s.151 insurer's duty to satisfy judgments against insured persons | §2.1 | Recalled |
| Directive 2009/103/EC (EU Motor Insurance Directive) | art. 18, a direct right of action against the insurer | §2.1 | Recalled |
| Damages Act 1996 (UK) | s.2 periodical payments | §7.6.1 | Recalled |
| Civil Procedure Rules (England and Wales) | Part 36 offers to settle and their costs consequences | §7.10 | Recalled |
| FCA Handbook | ICOBS 8.1 claims handling, PRIN 2A Consumer Duty, DISP complaints | §2.6 | Recalled |
| NAIC model laws (US) | Unfair Claims Settlement Practices Act (Model #900), Unfair Property/Casualty Claims Settlement Practices Model Regulation (#902), enacted variously by states | §2.6 | Recalled |
| IAIS Insurance Core Principles | ICP 19, conduct of business | §2.6 | Recalled |
| GDPR (EU) 2016/679 and UK GDPR | art. 9 special categories, art. 10 criminal offence data, art. 17 erasure and its exceptions in 17(3) | §12 | Recalled |
| Data Protection Act 2018 (UK) | Sch. 1 para. 20, the insurance condition for special category data | §2.6 | Recalled |

---

## 3. Standards and identifiers

| Standard | Publisher | What it is | What the sketch took, and its definition | Relation | Mark |
|---|---|---|---|---|---|
| SKOS, OWL 2, SHACL, PROV-O | W3C | the semantic web stack LATTICE is built on | nothing new: claims inherits it | conformed | Checked (LATTICE) |
| Data Privacy Vocabulary (DPV) | W3C Data Privacy Vocabularies and Controls Community Group | open terms for personal data categories, special categories, purposes and legal bases | concepts to align the claims privacy classes with (`skos:exactMatch` where they coincide). A Community Group output, not a W3C Recommendation | mapped | Recalled |
| EARL | W3C (Working Group Note) | the evaluation and report language | via LATTICE's assurance records profile | conformed | Checked (LATTICE) |
| ISO 4217 | ISO | currency codes | every money amount's unit, through `insurance/common` | conformed | Checked (LATTICE) |
| QUDT | QUDT.org | units of measure | physical quantities, through `insurance/common` | conformed | Checked (LATTICE) |
| ISO 17442 (LEI) | ISO, operated by GLEIF | legal entity identifiers | keys for insurers, insureds and organisations on a claim | conformed (exposure) | Checked (LATTICE) |
| ISO 20275 | ISO | entity legal forms | legal form of organisations | mapped (exposure) | Checked (LATTICE) |
| ISO 3779 | ISO | vehicle identification number (VIN) | a key scheme for vehicles in motor claims | mapped | Recalled |
| ISO 20022 | ISO | financial messaging. pain.001 is customer credit transfer initiation, pacs.008 is FI-to-FI customer credit transfer | the payment instruction and confirmation formats a claims payment travels in | exchanged | Recalled |
| ICD-11 | WHO | the International Classification of Diseases, 11th revision | coding of injury and diagnosis on medical evidence, special category data. ACORD carries an ICD code (`ICDDiagnosticCd`, §6) | mapped | Recalled for ICD-11, Checked for the ACORD element |
| SNOMED CT | SNOMED International, licensed | clinical terminology | an alternative clinical coding where a deployment holds a licence | mapped | Recalled |
| HL7 FHIR financial module | HL7 | resources for health claims: `Claim` (a provider's list of services for payment), `ClaimResponse` (the adjudication), `ExplanationOfBenefit` (claim, adjudication and balances for the member), `Coverage`, `CoverageEligibilityRequest` | the shape "a claim against a coverage, answered by an adjudication per item", which converges with the sketch's response per instrument and quanta per loss item | influenced, and mapped for health claims | Checked |
| ECLI | the Council of the European Union (2011 conclusions) | the European Case Law Identifier | a key scheme for judgments | mapped | Recalled |
| OASIS LegalDocML (Akoma Ntoso) | OASIS | an XML vocabulary for legal documents | a format for judgments and legal texts held as evidence | mapped | Recalled |
| CMMN, BPMN, DMN | OMG | case management, process and decision notations | how a consumer's claims workflow might be expressed, calling the reference (sketch §8.3) | influenced | Recalled |
| IFRS 17 | IFRS Foundation | insurance contracts accounting. The liability for incurred claims (LIC) is measured from fulfilment cash flows with a risk adjustment | the claims module supplies cash flow facts. Measurement is the insurer's | followed | Recalled |
| Solvency II QRT S.19.01 | EIOPA | non-life insurance claims information, development triangles, reported in the EIOPA XBRL taxonomy | a reporting projection over movements | followed | Recalled |
| NAIC Annual Statement Schedule P | NAIC | US statutory loss development triangles by line | a reporting projection | followed | Recalled |
| GLIDE | Asian Disaster Reduction Center | the GLobal IDEntifier for disasters | the open key scheme for `icm:LossEvent` | mapped | Checked (AIR-4.4) |
| PCS catastrophe serial numbers | Verisk Property Claim Services | US industry catastrophe identifiers and industry loss estimates | a key scheme for loss events, and an industry loss index (parametric, sketch §7.11). Also carried by the Lloyd's bordereau as "PCS Code" (§7) | mapped | Recalled for PCS, Checked for the bordereau field |
| PERILS event identifiers | PERILS AG | industry loss data for non-US events | as PCS, outside the US | mapped | Recalled |
| Oasis Open Exposure Data and Open Results Data | Oasis LMF | exposure and modelled loss formats | through the peril and exposure modules | mapped | Checked (AIR) |
| ACORD P&C XML, the P&C/Surety claims service messages | ACORD, licensed to members | message formats for first notice, claim updates, payments, loss runs | the crosswalk of §6 and the wire formats sketch | exchanged | Checked through a published model viewer, version not stated there |
| ACORD Global Reinsurance and Large Commercial (GRLC) standards | ACORD | the messaging behind the London market's electronic claims file | named only. No element was checked | exchanged | Recalled |

---

## 4. Market practice

| Source | What it is | What the sketch took | Mark |
|---|---|---|---|
| Lloyd's Claims Lead Arrangements | the Lloyd's requirement, in force from 1 June 2023 and replacing the Lloyd's Claims Scheme, under which a lead (and, for complex claims, a second lead) agrees claims for the following syndicates | a delegated power under a consent rule, stated in the placement's terms (sketch §7.5) | Checked |
| Lloyd's Coverholder Reporting Standards v5.2 | the field set for delegated authority bordereaux, including the claims bordereau, whose fields carry codes CR0001 onwards | the crosswalk of §7 and the wire formats sketch | Checked for the version and the code scheme, field list read from a third-party rendering of the standard (§7) |
| Lloyd's Delegated Data Manager | Lloyd's platform for bordereaux submission and transformation into standard fields | a consumer of egress (wire formats sketch) | Checked |
| London market unique claim reference (UCR) | a market-wide claim reference used in the London market's claims processing | named as a key scheme in sketch §7.4 and §14.1 | Recalled. The CRS claims bordereau's own identifier is Claim Reference (CR0104) with the UMR (CR0005), see §9 |
| Unique Market Reference (UMR) | the London market's identifier for a placed contract | the contract key a claims bordereau row carries | Checked (field CR0005) |

---

## 5. Definitions used by the claims sketch

Working definitions, each with its source. "Ours" means the sketch's own definition, made to give
the word one sense (CCS's first test).

| Term | Definition | Source |
|---|---|---|
| loss | something that happened to someone or something, causing harm, dated, located and caused | ours, after the exposure ontology's loss cause and the peril vocabulary |
| loss event | one occurrence in the world many losses share | `icm:LossEvent` (AIR-4.4) |
| occurrence (in a wording) | a happening at a particular time, place and in a particular way, the unit a limit or retention applies to | *Axa v Field* (Counsel), contract amounts A51 |
| originating cause | a cause to which losses can be traced, wider than an event | *Axa v Field* (Counsel) |
| demand | an assertion by a claimant that someone owes them something | ours. Close to "claim" in D&O and E&O wordings, which usually define it as a written demand for monetary or non-monetary relief, a suit or a proceeding |
| circumstance | a situation that may give rise to a demand, notified under a claims-made cover | ours, after market wordings |
| notification | a legal act telling an insurer of a loss, demand or circumstance | ours, an `ins:Declaration` (Instrument §6.4) |
| claim (the matter) | the matter an insurer handles for one or more related notifications, and the case its policy's relations are evaluated for | ours. ACORD and the Lloyd's bordereau both use "claim" in this sense (§6, §7) |
| response | how one instrument version responds to a claim | ours. Converges with FHIR's `ClaimResponse` |
| coverage position | an insurer's communicated stance on cover | ours |
| reservation of rights | a position accepting a claim for handling while reserving the right to decline on stated grounds | market usage (US especially) |
| quantum | an amount claimed, assessed, agreed, offered or determined for a loss item | English legal usage |
| reserve (case reserve) | an estimate of what will be paid on a claim | market usage, and the bordereau's "Reserve" fields |
| IBNR | incurred but not reported, a portfolio estimate out of the claims module's scope | actuarial usage |
| incurred | paid plus outstanding reserve | market usage, and the bordereau's "Total Incurred" (§7) |
| ALAE, ULAE | allocated and unallocated loss adjustment expense, a US statutory split of claims expenses | NAIC usage (Recalled) |
| movement | a dated money fact on a claim | ours |
| settlement | an agreement ending all or part of a claim or demand | English legal usage |
| Part 36 offer | an offer to settle under CPR Part 36, with costs consequences | CPR (Recalled) |
| subrogation | the paying insurer's right to stand in the insured's place against third parties | *Castellain v Preston*, MIA 1906 s.79 (Counsel) |
| contribution | sharing between insurers covering the same loss | MIA 1906 s.80 (Counsel) |
| average | the insured bears the uninsured proportion of a loss when underinsured | MIA 1906 s.81 (Counsel) |
| salvage | the value of damaged property the insurer takes over | market usage |
| follow the settlements | a reinsurer bound by the reinsured's proper settlements | *Insurance Co of Africa v SCOR* (Counsel) |
| claims co-operation | a reinsurer's approval of a settlement made a condition of its liability | *Scor v Eras* (Counsel), CCS C9b |
| claims-made | cover triggered by a demand first made against the insured in the period | market usage |
| claims made and notified | as claims-made, also requiring notification in the period | market usage |
| losses occurring, occurrence, losses discovered, risks attaching | the other trigger bases | market usage, sketch §2.2 |
| extended reporting period | a period after expiry in which claims may still be made or notified | market usage, ACORD `ExtendedReptDt` (§6) |
| relation back | a deeming that a later claim was made at the time of an earlier notice | CCS S25 |
| finding | an outcome established by a court, arbitrator, expert or ombudsman | CCS §6.4 |
| determination | the exercise of a party's power to decide a standard | CCS §6.4 |
| parametric cover | cover paying on a measured index crossing a threshold, with no loss to prove | contract amounts A57 |

---

## 6. Crosswalk: ACORD P&C claims messages

**Source.** ACORD P&C/Surety claims service request messages, read through a published model viewer
(Checked, version not stated by the viewer). Five request messages: `ClaimsNotificationAddRq` (first
notice of loss and attachments), `ClaimActivityNotify` (claim activity, usually from an MGA or TPA),
`ClaimDownloadNotify` (a current image of one claim, including changes and payments),
`ClaimStatusInqRq` (payment information for one claim) and `LossRunInqRq` (historical loss data).

**Fit**, for every row: **exact** (one-to-one), **derived** (computed from several of ours or several
of theirs), **lossy** (one side carries less), **gap** (no counterpart).

### 6.1 Message and notice

| ACORD | Meaning | Claims sketch | Fit |
|---|---|---|---|
| `ClaimsNotificationAddRq` | submits a first notice of loss | `clm:Notification` of kind notice of loss or notice of demand, opening a `clm:Claim` | exact for the act. Ingress creates the notification, the claim and the loss |
| `BusinessPurposeTypeCd` | the business event of the message | the message's role in ingestion (new, change), held as evidence | lossy |
| `ClaimsOccurrence/ClaimNoticeCd` | notice of occurrence or claim | `clm:notificationKind` (notice of loss or circumstance, or notice of demand) | derived, the code list must be crosswalked |
| `ClaimsOccurrence/ClaimsReported` | when, by whom and to whom reported | the notification's valid time, `ins:actBy`, `clm:notifiedTo` | exact |
| `ClaimsOccurrence/PreviouslyReportedInd` | a follow-up to an earlier report | a link to the earlier notification, or the claim it opened | derived, needs identity resolution |
| `FileAttachmentInfo` | an attachment, attached or forthcoming | `fnd:Evidence` by external key | exact for a document, lossy for "forthcoming" (an open request) |
| `RemarkText` | free text | evidence text | lossy |
| `Policy`, `PolicyTypeCd` | the policy and its type | `clm:Response` `clm:underInstrument`, resolved by the policy number key | derived: a policy number names an instrument identity, the version is chosen by the trigger date (sketch §7.9) |
| `Producer` | the agency producing the business | the broker's role occupancy | exact |
| `InsuredOrPrincipal` | the insured or principal | the named insured occupancy (AIR-4.1 roles) | exact |

### 6.2 Occurrence and loss

| ACORD `ClaimsOccurrence` element | Claims sketch | Fit |
|---|---|---|
| `LOSSDATE_CHOICE` (a loss date and time, or a loss period) | `clm:occurredAt`, or a span for a continuing loss | exact for occurrence. ACORD has no separate manifestation, discovery or exposure dates, so triggers that read them have no source here | 
| `EventInfo` | when a specific event occurred | `clm:occurredAt`, or the loss event's span | derived |
| `IncidentDesc`, `DamageDesc`, `IncidentClaimTypeDesc` | evidence text on the loss | lossy |
| `LossCauseCd` | `aeo:peril` on one `aeo:LossCause`, coded in the ACORD list and lifted to the reference through a crosswalk (AIR-3.4) | lossy: one code, no chain, no position, no mechanism or agency |
| `ClaimTypeCd`, `IncidentClaimTypeCd` (from the LineOfBusiness list) | `icm:classOfBusiness` on the claim or response | derived, crosswalked |
| `Catastrophe`, `CatastropheLossInd` | `clm:inLossEvent` an `icm:LossEvent`, keyed by its catastrophe identifier | exact where the catastrophe carries an identifier of a known key scheme |
| `Addr`, `LocationCd`, `SiteCd`, `CountyTownCd`, `WhereOccurredDesc` | `clm:lossAt` an `aeo:Location`, matched to the exposure set's location by address or key | derived, needs location matching |
| `ClaimsMadeInd`, `CurrentRetroactiveDt`, `ExtendedReptDt`, `FullTailInd` | the instrument's claims basis and its dates | gap on our side by design: these are contract terms, read from the instrument, not stated on the claim (CL2). Ingress checks them against the instrument and reports a disagreement |
| `ClaimStatusCd`, `ClaimStatusDt`, `ClaimStatusExplanation`, `ClaimSubStatusCd` | mixes three things the sketch keeps apart: the record's governance state (open, closed, reopened), the occasions' legal state (paid, breached), and the deployment's handling stage | derived on egress, and on ingress an asserted status from the source, never our occasion state (wire formats sketch, gap G4) |
| `LitigationInd`, `LitigationStatusCd` | a `clm:Proceedings` and its litigation regime state | derived |
| `ProbableIncurredAmt` | the sender's estimate of incurred | a `clm:Quantum` of stage assessed, asserted by the sender, or a reserve movement | lossy |
| `TotalLossInd` | a loss item adjustment or a valuation basis outcome | derived |
| `SalvageInd` | a recovery of kind salvage expected | derived |
| `QuestionableClaimInfo` | a fraud indicator from the source, never a finding (sketch §11.2) | exact as an indicator |
| `PoliceFireContactedInd`, `ViolationsCitationsInd` | evidence attributes | lossy |
| `OutsideAuthorityConditionCd` | a claim beyond the handler's delegated authority, a referral | derived from the authority power's scope (CCS S46) |
| `ResponsibleDept` | the deployment's internal routing | gap by design: workflow (CL9) |
| `AdditionalClaimInd` | other loss types from the same incident | derived: other loss items or claims on the same loss |

### 6.3 Parties

| ACORD `ClaimsParty` element | Claims sketch | Fit |
|---|---|---|
| `ClaimsPartyRoleCd` | a role occupancy in one of `icm-voc:Claimant`, `HarmedParty`, `LiableParty`, `Payee`, or a `clm-voc:` handling role | derived: the ACORD role list must be crosswalked, and one ACORD role may need two of ours (an injured claimant is both claimant and harmed party) |
| `GeneralPartyInfo`, `PersonInfo`, `Age` | the actor, personal data under a privacy profile (sketch §12.2) | exact, special handling |
| `ClaimsInjury`, `ClaimsInjuredInfo`, `ICDDiagnosticCd`, `MedicalTreatment`, `SurgeryInd`, `FatalityInd`, `PreExistingDisabilityCd` | bodily injury loss items and medical evidence, special category data | derived, special handling |
| `LossDt`, `LossTime` (per party) | the injury's own date, distinct from the occurrence's | exact |
| `AtFaultPct`, `OperatorAtFaultInd` | an apportionment of liability, a finding or an assessment by its source | derived |
| `SuitFiledInd` | a `clm:Demand` of form suit, or `clm:Proceedings` | derived |
| `GrossTPARecoveriesReceivedAmt`, `GrossTPARecoveriesOutstandingAmt` | recovery receipts and recovery reserves | derived from movements on egress, cumulative figures on ingress (gap G1) |
| `OtherOrPriorPolicy` | other insurance, a further response (sketch §7.5) | derived |
| `AuthorizedRepInd`, `Relationship` | a representative's occupancy under delegation | exact |
| `WitnessInfo`, `WitnessIncidentInd` | evidence, and a witness occupancy | exact |
| `PartyInvestigationInfo` | investigation evidence | lossy |
| `SSNValidationCd`, `TINValidationCd`, `SuppressMatchInd` | US identity validation and industry matching controls | gap by design: a deployment's processing, outside the model |

### 6.4 Payments and reserves

| ACORD `ClaimsPayment` element | Claims sketch | Fit |
|---|---|---|
| `PaymentTypeCd` | `clm:movementKind` (reserve set or change, payment, reversal, recovery receipt) and `clm:costClass` | derived: one ACORD code carries both axes, which the sketch keeps apart |
| `TotalPaymentAmt`, `TotalPaymentDetails` | `clm:amount` on the movement, split into items | exact |
| `ClaimsPaymentCovInfo` | amounts by coverage | derived: a coverage code names a section or relation of the instrument, resolved through the response |
| `ReserveChangeInfo` | a reserve change movement | exact |
| `PaymentDt` | the movement's valid time | exact. Its record time comes from the message's own time, not this element |
| `CheckNumber`, `ReferenceNumber`, `MethodPaymentCd` | the payment's external key and method (and the ISO 20022 message where the payment travels that way) | exact |
| `LossKindCd`, `LossCauseCd` (on a payment) | the loss item's head of loss and cause | derived |
| `ServiceDuration` | the period a payment covers, for periodical or medical payments | exact |
| `TotalClaimLossPaidAmt` | paid to date, sent only on a closed claim | derived on egress from movements |
| `ClaimsPartyRef` (attribute) | `clm:payee` | exact |
| void "with a negative amount" | a reversing movement | exact |

### 6.5 Handling parties

| ACORD | Claims sketch | Fit |
|---|---|---|
| `AdjusterParty` | the loss adjuster's occupancy under delegation, on the response | exact |
| `ClaimActivityNotify` | activity by an MGA or TPA: the facts and acts it carries, each landing on its own term | derived, one message to many records |
| `ClaimDownloadNotify` | a full image of one claim | derived: compared with the claim as known, and only the differences become new facts or versions (wire formats sketch, gap G1) |
| `LossRunInqRq` | a request for loss history | egress: the derived loss run of sketch §13.3 |
| `ClaimStatusInqRq` | a request for payment information | egress: derived balances |

---

## 7. Crosswalk: Lloyd's claims bordereau (CRS v5.2)

**Source.** Lloyd's Coverholder Reporting Standards v5.2 (user guide dated 20 August 2019) and the
Lloyd's claims bordereaux standard operating procedure, which maps submissions against the standard's
mandatory and conditionally mandatory fields (Checked). The field codes and names below were read
from a third-party rendering of the standard (bdxflow's CRS reference), since the Lloyd's PDF's text
did not extract. Every code and name must be confirmed against the v5.2 user guide's Appendix One
before a mapping graph is authored. Which fields are mandatory is in the guide, and not recorded
here.

**The bordereau's shape** decides most of the fit: one row per claim per reporting period, carrying
cumulative and period figures (paid this month, previously paid, reserve, change this month, total
incurred), split into indemnity, fees and expense heads, in an original and a settlement currency.

### 7.1 References and identity

| CRS | Field | Claims sketch | Fit |
|---|---|---|---|
| CR0005 | Unique Market Reference (UMR) | the contract key of the placement or binding authority (`fnd:naturalKey` on the instrument identity) | exact |
| CR0006 | Agreement No | the binding authority agreement's key | exact |
| CR0007 | Section No | `clm:underSection`, the agreement section (CCS §5.10) | exact |
| CR0029 | Certificate Ref | the bound policy's key under the authority, resolving `clm:underInstrument` | exact |
| CR0104 | Claim Reference | the coverholder's claim key on `clm:ClaimIdentity` | exact |
| CR0122 | Claimant Name | the claimant occupancy's actor, personal data | exact, special handling, minimised on egress where the recipient does not need it |

### 7.2 Status, decisions and dates

| CRS | Field | Claims sketch | Fit |
|---|---|---|---|
| CR0105 | Claim Status | an asserted status from the coverholder (gap G4 of the wire formats sketch). On egress, derived from the claim's governance state and its occasions | derived |
| CR0106 | Refer Claim to Underwriters | an obligation to refer above authority (CCS S46), its occasion arisen | derived |
| CR0107 | Denial | a `clm:CoveragePosition` of kind declinature | exact for the act |
| CR0312 | Reason for Denial | `clm:citesTerm` on that position, free text on ingress | lossy |
| CR0311 | Date Claim Denied | the position's valid time | exact |
| CR0316 | Date Claim Withdrawn | a `ins:Withdrawal` of the notification, or the claim's closure with reason | derived |
| CR0317 | Ex Gratia Payment | a payment movement not performing any occasion (no obligation), marked ex gratia | exact. A shape reports an ex gratia payment where the coverholder's authority excludes them (CCS S46) |
| CR0119, CR0120 | Date of Loss (From), (To) | `clm:occurredAt` as a span | exact for occurrence. No manifestation, discovery or exposure dates |
| CR0136 | Date First Advised | the first notification's valid time | exact |
| CR0372 | Claim Notification Acknowledgement Date | the occasion of an acknowledgement duty performed (a conduct duty, sketch §11.4) | derived |
| CR0300 | Date Claim Opened | the claim identity's first version's record time | exact |
| CR0301 | Date Coverage Confirmed | a `clm:CoveragePosition` of kind acceptance, its valid time | exact |
| CR0302 | Date Claim Amount Agreed | a `clm:Quantum` of stage agreed, or a settlement's assent | derived |
| CR0303, CR0304 | Date Claims Paid (Final), Date Fees Paid (Final) | the last payment movement of each cost class, with the occasion Performed | derived |
| CR0137 | Date Closed | the claim's governance state closed, its version's valid time | exact |
| CR0306 | Date Reopened | a new claim version, governance state reopened | exact |
| CR0307 | Date of Subrogation | a recovery `clm:Demand` made (sketch §10.1) | exact |
| CR0371 | Date First Reserve Established | the first reserve movement's valid time | derived |
| CR0369 | Diary Date | workflow (CL9) | gap by design |
| CR0370 | Peer Review Date | workflow | gap by design |

### 7.3 Cause, nature and location

| CRS | Field | Claims sketch | Fit |
|---|---|---|---|
| CR0117 | Cause of Loss Code | `aeo:peril` on one cause link, in the coverholder's list, lifted through a crosswalk where exact (AIR-3.4, peril whitepaper W-Q3) | lossy: one code, no chain |
| CR0118 | Loss Description | evidence text | lossy |
| CR0364 | General Nature of Loss | `clm:headOfLoss` or the harm subject, crosswalked | derived |
| CR1273 | Nature of Claim | `clm:headOfLoss` or demand form, crosswalked | derived |
| CR0367 | Severity of Loss | an assessment of the claim by the coverholder | lossy |
| CR0368 | Litigation Status | the litigation regime's state on `clm:Proceedings` | derived |
| CR0138, CR0139 | Catastrophe Code, Catastrophe Name | `clm:inLossEvent`, an `icm:LossEvent` keyed in the market's catastrophe code scheme | exact where the code scheme is declared |
| CR0108 | PCS Code | a second key of the same `icm:LossEvent`, in the PCS scheme | exact |
| CR0112 to CR0116 | Location of Loss: Address, County, Sub-division, Postcode, Country | `clm:lossAt`, matched to an exposure location or a new `aeo:Location` with `aeo:Address` | derived |
| CR0103 | Claim - Sum Insured Amount | the instrument's sum insured, a contract term (CL2) | gap by design: read from the instrument, compared, a disagreement reported |
| CR0313 | Amount Claimed | a `clm:Quantum` of stage claimed | exact |

### 7.4 Money

| CRS | Field | Claims sketch | Fit |
|---|---|---|---|
| CR0109 | Claim - Original Currency | the currency of the movement amounts as recorded | exact |
| CR0110 | Claim - Settlement Currency | the currency of settlement, and the `qnt:Conversion` target | exact |
| CR0111 | Claim - Rate of Exchange | the conversion's rate, under a context at the reporting date | exact, with a date the field does not carry (gap G8) |
| CR0126, CR0127 | Paid This Month: Indemnity, Fees | on egress, `sum` of payment movements with record time in the month, by cost class. On ingress, payment movements inferred for the month | derived (gap G1) |
| CR0140 to CR0144 | Paid This Month: Expenses, Attorney Coverage Fees, Adjusters Fees, Defence Fees, TPA Fees | as above, each a `clm:costClass` value | derived |
| CR0128, CR0129, CR0145 to CR0149 | Previously Paid, by head | paid to date before the month | derived |
| CR0130, CR0131, CR0150 to CR0154 | Reserve, by head | outstanding reserve at the month end | derived |
| CR0132, CR0133 | Change This Month: Indemnity, Fees | the net of the month's movements | derived |
| CR0134, CR0135, CR0155 | Total Incurred: Indemnity, Fees, All | paid plus outstanding | derived |
| CR0375, CR0376 | Gross Third-Party Recoveries Received, Outstanding | recovery receipts and recovery reserves | derived |

The cost classes of the bordereau (indemnity, fees, expenses, attorney coverage fees, adjusters fees,
defence fees, TPA fees) are a finer split than the sketch's first draft of `clm:costClass`
(indemnity, defence, adjusting expense, other expense). §9 asks that the reference scheme follow the
bordereau's heads, which a coarser scheme can then group.

---

## 8. What the crosswalks show

| Finding | Consequence for the model |
|---|---|
| **Both formats report claims, neither carries a cause chain.** One cause code per claim (ACORD `LossCauseCd`, CRS CR0117) | ingress lands one `aeo:LossCause` link, position unknown, mechanism and agency defaulted where the code allows (AIR-4.4). Checks that need the chain are Undetermined until a person adds it (CL8) |
| **Status codes merge three things the model keeps apart** | ingress records a status as the source's assertion. Egress derives it from governance state, occasions and handling stage by a declared rule per format |
| **Money is reported as balances, not movements** (CRS cumulative and period columns, ACORD totals beside payment records) | ingress infers movements from successive snapshots, egress derives balances from movements. The wire formats sketch designs both (gap G1) |
| **Contract terms appear on the claim** (ACORD claims-made and retroactive dates, CRS sum insured) | read, not stored as claim facts. A disagreement with the instrument is reported, which turns a reporting field into a data quality check |
| **Workflow appears on the claim** (CRS diary and peer review dates, ACORD responsible department) | carried as the source's workflow data, outside the reference, if a deployment keeps it at all |
| **Trigger dates beyond occurrence are absent** (no manifestation, discovery, exposure dates in either) | claims-made and long-tail triggers need dates neither format supplies on the claim. ACORD's claims-made indicator and the CRS dates of loss are not enough. Those claims need data from the documents or a person |
| **Personal and special category data is rich in ACORD** (injuries, ICD codes, medical treatment) **and thin in the bordereau** (claimant name) | the privacy profile matters most for ACORD ingress, and minimisation matters most for bordereau egress |
| **Per-insurer figures are absent.** A bordereau row is for the coverholder's claim under one section, with the syndicates' shares on the agreement | egress per insurer is a `split` by the placement's shares, ingress lands on one response for the authority's group |

---

## 9. Corrections to the claims sketch

Found while writing this companion, and made in [insurance-claims-ontology.md](insurance-claims-ontology.md)
on 2026-10-16.

| Where | Correction |
|---|---|
| §2.1 | *Post Office v Norwich Union* is reported at [1967] 2 QB 363 (CA). The sketch gave [1968] 1 QB 363 |
| §2.1 | *Hill v M & G Re* is cited from the House of Lords report, [1996] 1 WLR 1239. The sketch gave [1996] LRLR 341. Both reports to be checked by counsel with the rest |
| §7.4, §14.1, §15 | the London market unique claim reference is Recalled, not Checked. The claims bordereau identifies a claim by Claim Reference (CR0104) with the UMR (CR0005) and the certificate (CR0029), and the sketch's key text and example now use a lead's claim reference |
| §9.1 | `clm:costClass`'s reference scheme now follows the bordereau's heads (indemnity, fees, expenses, attorney coverage fees, adjusters fees, defence fees, TPA fees), with ALAE and ULAE as a grouping for US statutory reporting |
| §15 | the ACORD row now names its source as a published model viewer of the P&C/Surety specification, version not stated, and the messages as the five listed in §6 |
| §7.1 | the loss's dates beyond occurrence (manifested, discovered, exposure) have no source in either format. The sketch now says they come from documents or a person, and that the claim stays Undetermined until they do |
