# Clause map

Every leaf of the fragment's wording, with what it maps to. The Turtle IRIs are in `nonprofit-portfolio.ttl` (`ex:` for wording and words, `tmpl:` for stated meaning). The **Gap** column names the finding in [README.md](README.md#findings).

Status:

- **Encoded.** All of the leaf's effect is stated meaning.
- **Partial.** Some of it is. The rest is a gap.
- **Structural.** The effect is carried by how the model is built, such as sectioning or containment, and not by a term of the leaf's own. The leaf therefore looks unassessed (§18.5).
- **No meaning.** Recorded with `ins:encodingStatus ins-voc:NoMeaning`.
- **Gap.** Not encoded, and left unassessed on purpose.

## Front matter and Declarations

| Leaf | Text, in short | Instrument | Other layers | Status | Gap |
|---|---|---|---|---|---|
| `policyholder-notice` | broker compensation notice | none | | No meaning | |
| `front-notice` | claims-made, defence costs erode limits, no duty to defend unless stated | none (summarises GTC 3 and CPL 2) | | No meaning | |
| `item-1` | Named Entity, address, state of formation | `tmpl:def-named-entity`, a party word whose placeholder takes its value from the variable | Wording variables. Party: `ex:named-entity-occ` | Partial | G13 |
| `item-2` | Inception and Expiration Dates, 12:01 A.M. at the Named Entity Address | date words `InceptionDate`, `ExpirationDate` | Quantification: `xsd:dateTime` with offset −04:00 | Partial | G7, G8 |
| `item-3` | Premium $71,447 | value word `Premium` | | Partial | G1 |
| `item-4` | Insurer and Claims addresses, e-mail | none. The values go to `ins:noticeAddress` on `ex:insurer-occ` | Party details | Partial | G13 |
| `item-5` | Policy Aggregate $6,000,000 | value word `PolicyAggregate` | | Partial | G1 |
| `do-limit` | D&O Shared Limit $4M, shared with EPL | `SharedLimit` within D&O | | Partial | G2 |
| `do-excess` | Excess Limit for Executives $500k | `ExcessLimitForExecutives` within D&O | | Partial | G1 |
| `do-retention` | Retention $50k | `Retention` within D&O | | Partial | G1 |
| `do-continuity` | Continuity Date: an executive's own first-service date, or 26 Apr 2007 | `ContinuityDate` within D&O, the fixed date only | | Partial | G9 |
| `do-premium` | Section premium $32,570 | `CoverageSectionPremium` within D&O | | Partial | G1 |
| `epl-limit` | Shared Limit $4M, shared with D&O | `SharedLimit` within EPL | | Partial | G2 |
| `epl-retention` | Retention: class action $250k, third party $50k, other $50k | three words within EPL | | Partial | G1, G9 |
| `epl-continuity` | Continuity Date, as for D&O | `ContinuityDate` within EPL | | Partial | G9 |
| `epl-premium` | $33,590 | `CoverageSectionPremium` within EPL | | Partial | G1 |
| `fid-limit` | Separate Limit $1M | `SeparateLimit` within Fiduciary | | Partial | G1 |
| `fid-retention` | Securities $0, other $0 | two words within Fiduciary | | Partial | G1 |
| `fid-continuity` | 1 Aug 2019 | `ContinuityDate` within Fiduciary | | Encoded | |
| `fid-premium` | $2,800 | `CoverageSectionPremium` within Fiduciary | | Partial | G1 |
| `cpl-limit` | Separate Limit $1M | `SeparateLimit` within CPL | | Partial | G1 |
| `cpl-retention` | Retention $10,000 | `Retention` within CPL | | Partial | G1 |
| `cpl-continuity` | 1 Dec 2019 | `ContinuityDate` within CPL, read by exclusion 3(e) | Eligibility: `litigation-by-continuity` | Encoded | |
| `cpl-retro` | 1 Dec 2019 | `RetroactiveDate` within CPL, read by exclusion 3(c) | Eligibility: `act-before-retro-date` | Encoded | |
| `cpl-premium` | $2,487 | `CoverageSectionPremium` within CPL | | Partial | G1 |
| `item-7` | Passport: Not Applicable | none | | Gap | G14 |
| `item-8` | TRIA Premium $0, and its definition | value word `TRIAPremium` | | Partial | G1 |
| `attestation` | not valid unless signed for the Insurer | the regime's `tmpl:on-signed` (OnAcceptance by the Insurer), owned by the Policy Period term | Behaviour | Structural | G11 |
| `tria-disclosure` | statutory terrorism disclosure | none | | No meaning | |

## General Terms and Conditions

| Leaf | Text, in short | Instrument | Other layers | Status | Gap |
|---|---|---|---|---|---|
| `gtc-recital` | in consideration of the premium | `tmpl:pay-premium`, an obligation of the Named Entity | | Partial (no amount, no due date) | G1 |
| `gtc-1` | GTC apply to all sections. Section terms apply only within their section | `tmpl:coverage-sections`, a Sectioning over the four sections | | Encoded | |
| `gtc-2` | Retention per Claim, highest of shared sections, separate sections separately | `tmpl:retention`, a Qualifier on `term-ccp-1` | | Partial | G1, G2, G3 |
| `gtc-3` | Aggregate, separate, shared and sublimits, related claims, Defence Costs erode | `tmpl:policy-aggregate`, `tmpl:separate-limit` on `term-ccp-1` | | Partial | G1, G2, G3, G4 |
| `gtc-4` | Discovery Period: 6 years, 30-day election, additional premium, Transaction offer, not cancellable, not after non-payment cancellation | `tmpl:elect-discovery` (power, window 30 days from ending, arising on NE cancellation or either nonrenewal), `tmpl:pay-discovery-premium`, `tmpl:request-discovery-offer`, `tmpl:offer-discovery` | Behaviour: OnAct nonrenewal triggers. Quantification: ranges | Partial | G1, G5, G6, G10 |
| `gtc-5` | Transaction: run-off, no refund, no cancellation, waiver by endorsement | `tmpl:waive-transaction`, `tmpl:no-refund-after-transaction`. Run-off and the bar on cancellation are the regime's | Behaviour: `run-off` state | Partial | G6, G10, G11 |
| `gtc-6a` | worldwide territory | none | | No meaning (see G12) | G12 |
| `gtc-6b` | Passport master and underlyer | none | | Gap | G14 |
| `gtc-6c` | spousal, partner and legal representative extension | `tmpl:pay-spouse`, obligee resolved from the Claim | Party: `spouse-occ`. Eligibility: `spousal-scope` | Encoded | |
| `gtc-7a` | Named Entity may cancel at any time by notice | `tmpl:cancel-by-named-entity`, in force or in notice | Behaviour | Partial (effective date chosen by the notice) | G7 |
| `gtc-7b` | Insurer may cancel only for non-payment, at least 15 days' notice | `tmpl:cancel-by-insurer` (scope `premium-unpaid`), notice state, 15-day expiry | Behaviour | Partial (the notice names the date) | G7 |
| `gtc-7c` | pro rata return premium | `tmpl:return-premium`, arising on entering `cancelled` | | Partial | G1 |
| `gtc-8` | recovery reinstates limits, net of costs | none | | Gap | G1 |
| `gtc-9` | notice in writing to the Insurer Address. Named Entity acts for all Insureds | none (addresses on occupancies) | Party | Gap | G13 |
| `gtc-10` | no assignment without consent | `tmpl:no-assignment`, `tmpl:assignment-with-consent` | | Encoded | G10 (consent) |
| `gtc-11` | no action until compliance and final determination. No joinder | `tmpl:no-premature-action`, classed condition precedent | Vocabulary: term class | Partial | G15 |
| `gtc-12` | insolvency does not relieve the Insurer. Mutual cooperation | `tmpl:insurer-cooperates`, `tmpl:insured-cooperates` | | Encoded (first sentence holds by absence) | |
| `gtc-13` | conformance to law, the more favourable notice period | none | | Gap | G16 |
| `gtc-14` | US dollars, and the published exchange rate | none | | Gap | G17 |
| `gtc-15` | headings form no part | none | | No meaning | |
| `gtc-16a` | section definitions apply within their section, then the Declarations and 16(c) | none | | Structural (D12, D13) | G18 |
| `gtc-16b` | undefined GTC terms take section or Declarations meanings | none | | Structural | G18 |
| `def-continuity` | Continuity Date means the Item 6 date | none (definitions on the Item 6 rows) | | Structural | G18 |
| `def-coverage-section` | Coverage Section means each purchased section | none (the Sectioning) | | Structural | |
| `def-e-consultant` | E-Consultant Firm | condition word | Eligibility | Encoded | |
| `def-e-discovery` | E-Discovery | condition word | Eligibility | Encoded | |
| `def-e-services` | E-Discovery Consultant Services | condition word | Eligibility | Encoded | |
| `def-enforcement-body` | Enforcement Body | condition word | Eligibility | Encoded | |
| `def-foreign-jurisdiction` | Foreign Jurisdiction | condition word | Eligibility | Encoded | |
| `def-organization` | Named Entity, each Subsidiary, a debtor-in-possession | party word over three roles, no acting rule | Party: contingent occupancies | Partial | G13 |
| `def-policy-period` | Inception to the earlier of Expiration or cancellation, at 12:01 A.M. local | `tmpl:def-policy-period` (interval condition) and `tmpl:policy-regime` | Behaviour, Eligibility, Quantification | Partial | G7, G8, I-1 |
| `def-retroactive` | Retroactive Date means the Item 6 date | none (definition on `cpl-retro`) | | Structural | G18 |
| `def-separate-limit` | the Item 6 Separate Limit | none | | Structural | G18 |
| `def-shared-limit` | the Item 6 Shared Limit, shared between listed sections | none | | Structural | G2, G18 |
| `def-transaction` | merger, sale or change of control, plus section meanings | condition word, AnySufficient of two facts | Eligibility | Partial (section additions) | G18 |

The three other sections, `do`, `epl` and `fid`, are empty in the fragment. Their Item 6 rows are bound within them.

## CPL Coverage Section

| Leaf | Text, in short | Instrument | Other layers | Status | Gap |
|---|---|---|---|---|---|
| `cpl-notice` | GTC incorporated | none | | Structural | |
| `cpl-recital` | consideration | none (the GTC recital states it) | | Structural | |
| `ccp-1` | claims-made, A: Insured Person's Loss unless indemnified. B: the Organization's indemnification | `tmpl:pay-a`, `tmpl:pay-b`, one trigger `on-covered-claim` | Party: two resolutions from the Claim. Eligibility: `covered-claim`, `indemnified` and its negation | Partial (the extent of indemnification is an amount) | G1, G3 |
| `ccp-2a` | duty to defend, Defence Costs, no defence of D&O or Securities Claims | `tmpl:defend` (with 2(c)'s endings), `tmpl:pay-defense-costs`, `tmpl:no-defence-of-do-or-securities` | | Encoded | |
| `ccp-2b` | consented Defence Costs for Securities or excess Claims | `tmpl:indemnify-defense-costs` | | Encoded | G10 (consent) |
| `ccp-2c` | duty ends on exhaustion or refused settlement. The 70% hammer. Guilty-plea carve-out | `tmpl:hammer-cap` Qualifier. The endings are on `tmpl:defend` | Behaviour: OnCondition endings | Partial | G1, G11 |
| `ccp-2d1` | copies, record, documents on request, cooperation | four obligations and the request power | | Partial (no due ranges) | G5 |
| `ccp-2d2` | no settlement without consent, at own expense, not toward the Retention | prohibition, permission, two exclusions | | Partial | G1, G10 |
| `ccp-2d3` | Insurer's right to associate | `tmpl:permit-association`, the correlative duty | | Encoded | G19 |
| `ccp-2d4` | no cover for an entity's own liability | `tmpl:entity-liability-excluded`. The rest by construction | | Encoded | |
| `ccp-2d5` | Panel Counsel | selection obligation, panel power, no unreasonable refusal | | Partial (choice rules, nearest jurisdiction, delisted firms) | G20 |
| `ccp-2d6` | no intentional prejudice | `tmpl:no-prejudice` | | Encoded | |
| `ccp-3-intro` | the exclusions' common stem | none (each exclusion restates it) | | Structural | |
| `ccp-3a` | conduct, after final adjudication, then reimbursement | two exclusions, `tmpl:reimburse-defense-costs` | Eligibility: `conduct-adjudicated` composite | Encoded | |
| `ccp-3a-imputation` | knowledge not imputed between persons, and only from named officers to the Organization | none | | Gap | G21 |
| `ccp-3b` … `ccp-3r`, `ccp-3wage` | the exclusions | two exclusions each, scopes with carve-backs negated | Eligibility | Encoded, except as noted | |
| `ccp-3c` | before the Retroactive Date, or related acts | scope `act-before-retro-date`, an interval with a placeholder | Eligibility, Quantification | Partial (relatedness) | G22, I-2 |
| `ccp-3d` | noticed under a prior policy | scope `noticed-under-prior-policy`, a fact | | Partial | G23 |
| `ccp-3e` | pending or prior as of the Continuity Date | interval for litigation, a fact for proceedings with notice | | Partial (relatedness) | G22, I-2 |
| `ccp-3g`, `ccp-3q` | carve-back for Defence Costs, Non-Indemnifiable Loss | negated loss-component facts | | Partial | G3 |
| `ccp-4` | no Retention for Non-Indemnifiable Loss or excess Securities Claims | none | | Gap | G1 |
| `ccp-5-intro` | written notice to the Claims Address. Mailed means given | `tmpl:mailed-is-given`, a conclusive deeming | | Partial (which address) | G13 |
| `ccp-5a` | report as soon as practicable after the RM or GC knows, and within 90 days of the period's end | `tmpl:notify-claim`, due by 90 days after ending, classed condition precedent | Vocabulary: term class | Partial | G5, G21, G24 |
| `ccp-5b` | related claims relate back. No cover for earlier Loss | deeming for four relations, two exclusions | | Encoded | G25 |
| `ccp-5c` | notified circumstances relate back. Specificity, tolling presumption | two deemings (one rebuttable), two exclusions | | Encoded | G25 |
