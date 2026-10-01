<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Contract amounts: limits, retentions, shares and accumulations

Draft for review, 2026-09-30. A requirements catalogue, not yet a design. The deontic model of
[computable-contract-substrate.md](computable-contract-substrate.md) says *that* a party must pay
or may not exceed something. This sketch collects every construct in the tested instruments that
decides *how much*, so that none is lost before the design is written. It feeds AIR Phase 5
(ADR-A101, term parameters) and Open CBAA's binding authority capacity.

Sources use the codes of the substrate sketch: AIG (package policy), IUA (IUA 09-069 BAA2018),
CBAA (Lloyd's computable binding authority collateral).

## 1. Catalogue

### 1.1 Limits

| # | Construct | Source |
|---|---|---|
| A1 | a policy aggregate: maximum for all loss under all sections combined | AIG Declarations item 5, GTC 3 |
| A2 | a separate limit per section, part of and not in addition to the aggregate | AIG GTC 3, Declarations item 6 |
| A3 | a shared limit across named sections, with a lesser amount stated for one section serving as that section's cap, reduced by prior payments under the shared limit | AIG GTC 3 |
| A4 | sublimits, part of and not in addition to every enclosing limit | AIG GTC 3, D&O 6, End. 8 H (EMTALA, governmental fraud defence costs, HIPAA penalties), End. 23 regulatory sublimit |
| A5 | per-person sublimits nested inside aggregate sublimits | AIG D&O 2.A(3), (4) personal reputation and asset protection, D&O 6 |
| A6 | an excess limit available only after the section limit and any other valid insurance are exhausted, then primary | AIG D&O 2.C, 6 Excess Limit for Executives |
| A7 | discovery period limits part of the policy period limits | AIG GTC 3 |
| A8 | a limit shared with another section's limit for one purpose | AIG CrisisFund 3, End. 12 item I |
| A9 | the highest limit across several policies from the same insurer applies, never their sum | AIG CrisisFund 2 |
| A10 | continuity dates that differ by limit layer (first 2,000,000 against the excess 2,000,000) | AIG End. 6, End. 7 |
| A11 | limits and sums insured an authority may bind up to, per segment, in several currencies | IUA 10, CBAA SoUA rows 20, 21, 42 |
| A12 | claims settlement authority per claim, and a claims loss fund with drawdowns and top-ups | IUA 21.1.1, CBAA M8 8.7D.3.2 |
| A13 | redress authority up to an amount "or equivalent in other currencies" | CBAA M9 9.1.3 |
| A14 | minimum limits the agent's own insurance must carry | CBAA M14 14.13.4 to 14.16 |

### 1.2 Retentions and coinsurance

| # | Construct | Source |
|---|---|---|
| A15 | one retention per claim or group of related claims | AIG GTC 2 |
| A16 | the highest applicable retention when a claim triggers several sections under a shared limit | AIG GTC 2 |
| A17 | separate retentions per section under separate limits, not satisfied by payments towards another section's retention | AIG GTC 2 |
| A18 | retentions that vary by claim kind, the highest applying when several are triggered | AIG End. 3 California, End. 17 class action, End. 23 regulatory, End. 24 highly compensated employees, End. 29 and 30 a named individual |
| A19 | no retention for some loss: non-indemnifiable loss, crisis loss, the first 25,000 of e-discovery consultant costs | AIG D&O 2.B, 5, CrisisFund 4 |
| A20 | coinsurance: 50% of loss above a retention up to a sublimit, the remainder uninsured "as a condition of this insurance" | AIG End. 8 H, End. 23 CA-1 |
| A21 | amounts within a retention remain uninsured, and an advance within the retention counts towards exhaustion | AIG GTC 2, D&O 3.A |
| A22 | minimum deductibles and excesses an agent must impose | IUA 11.2, CBAA SoUA rows 39, 40 |

### 1.3 Erosion, order and reinstatement

| # | Construct | Source |
|---|---|---|
| A23 | defence costs part of loss, eroding limits | AIG notice page, GTC 3 |
| A24 | order of payments: Side A first, then B and C only if limits remain, at a named officer's direction | AIG D&O 3.B |
| A25 | recovery of paid amounts reinstates limits, less recovery costs | AIG GTC 8 |
| A26 | a limit reduced by amounts recoverable under another policy from an affiliate | AIG D&O 12.B |
| A27 | excess over other valid and collectible insurance, primary to personal umbrella cover | AIG D&O 12.B |
| A28 | related claims treated as one, deemed made when the first was | AIG D&O 7(b), GTC 2 |
| A29 | a public cap: an insurer not liable above a statutory aggregate, and pro rata shares below it | AIG End. 32 TRIA |

### 1.4 Aggregates over bound business

| # | Construct | Source |
|---|---|---|
| A30 | a gross premium income limit over all business bound, with its definition (premiums less returns, before commission, excluding taxes) | IUA 12.1, 12.3, CBAA SoUA rows 41 to 45 |
| A31 | notification when income is likely to exceed a percentage of the limit | IUA 12.2, SoUA row 47 |
| A32 | aggregate exposure limits, and their monitoring basis | IUA 23.2, CBAA M5 5.13 |
| A33 | a loss ratio threshold as a condition ("gross loss ratio … less than 50%") | CBAA M12 12.24.2.4.2 |
| A34 | estimated premium income stated for information, not binding | CBAA M5 5.1.3 |

### 1.5 Remuneration and fees

| # | Construct | Source |
|---|---|---|
| A35 | commission as a percentage of each gross written premium, or of the total, "equal to" or "not exceeding" | IUA 16.1, CBAA M6 6.1B |
| A36 | commission as a fixed amount per policy, certificate, risk or endorsement | CBAA M6 6.1B.2 |
| A37 | a single fixed amount payable within a period of inception | CBAA M6 6.1A |
| A38 | profit commission by formula | IUA 16.2, CBAA M6 6.3B |
| A39 | refund of unearned commission on cancellations and return premiums at the original rates | IUA 17.1 |
| A40 | intermediary commission within or in addition to the agent's | CBAA M6 6.2 |
| A41 | brokerage in instalments | CBAA M6 6.7 |
| A42 | a leader fee as a percentage of premium, adjusted with premium, borne proportionally by participants or by the agent | CBAA M6 6.8 |
| A43 | fees charged to policyholders, disclosed and shown separately | IUA 29, CBAA M6 6.4 |
| A44 | fees and charges deducted from premium | IUA 24.7, CBAA M6 6.6 |
| A45 | premium and additional premium, pro rata return on cancellation, non-refundable additional premium | AIG GTC 4, 7(c), Declarations |
| A46 | a discovery premium of up to 125% of the full annual premium for one year, or to be determined | AIG D&O 8, End. 19 |

### 1.6 Shares and currencies

| # | Construct | Source |
|---|---|---|
| A47 | several shares: signed, written, order, broker share, participation basis (percentage or amount, of whole or of order), line to stand | CBAA Insurer Capacity Table rows 10 to 26, IUA 41 |
| A48 | payment in the instrument currency, or another at the payer's option, at a published rate on the date the obligation is established | AIG GTC 14 |
| A49 | one limit stated in several currencies, each read in its own unit | CBAA SoUA row 42, ADR-A95 |
| A50 | taxes shown separately and not concealed | IUA 28.2 |

### 1.7 Bases, aggregation and grouping

An amount rarely stands alone. A limit or a retention applies **on a basis**: per occurrence, per
claim, any one event, per policy year. An aggregate applies over a **window**, counting by a
**counting basis**. An hours clause **groups** losses into events. The idea is general, not
insurance-specific: a facility's commitment fee per annum, a licence fee per seat per year, a
notice period extended per year of service, a drawing limit per drawing.

The machinery a basis needs, independent of any domain:

| Part | What it says | Insurance example | Other domains |
|---|---|---|---|
| counting unit | what one application of the amount is measured against | occurrence, claim, event, risk, location | drawing, seat, employee, shipment |
| accumulation window | the period over which applications sum against an aggregate | policy year, calendar year, per event, custom | per annum, per quarter, per contract year |
| grouping rule | how separate happenings count as one unit | hours clause: 72 hours, selection by the insured, no overlap, maximum windows | related claims as one, a series of drawings as one |
| companion parameters | what a basis requires beside the amount | an aggregate basis needs a window. A linear payout needs a floor and a ceiling | an annual fee needs an anniversary |

| # | Construct | Source |
|---|---|---|
| A51 | a limit or retention on a basis: per occurrence, per claim ("any one claim"), per event, per risk, per location | AIG D&O 6 per-executive sublimits, GTC 2 "each Claim or group of Related Claims", CBAA SoUA row 21 limit or sum insured basis |
| A52 | an aggregate limit over a window: policy year, calendar year, per event, custom | AIG GTC 3, CBAA SoUA row 45 GWP income limit period |
| A53 | an aggregate deductible (annual aggregate deductible), distinct from the aggregate limit, with its own window and counting basis | term-parameters `ctr:AggregateParameter` |
| A54 | an aggregate counting basis: per occurrence, per claim, per event | term-parameters T2 (basis on aggregate parameters) |
| A55 | an hours clause: window duration, selection method (insured's choice, largest loss, first event), non-overlap, maximum windows | term-parameters `ctr:OccurrenceGroupingParameter` |
| A56 | reinstatements: count, percentage, automatic or optional, pro rata as to time, pro rata as to amount (independent elections, multiplicative when both apply) | term-parameters `ctr:ReinstatementParameter` |
| A57 | a parametric payout structure: binary, linear between a floor and a ceiling, graduated by tiers | parametric covers in general, no tested instrument |
| A58 | a premium basis: flat, rate on line, adjustable, minimum and deposit | term-parameters `ctr:PremiumParameter` |

**What exists.** The term-parameters sketch (A-101, applied insurance) already designs most of
this as insurance term parameters: a basis on every limit, retention and aggregate parameter (its
T2), companion parameters required by basis (T4), `ctr:AggregateParameter`,
`ctr:OccurrenceGroupingParameter` with maximum windows, and `ctr:ReinstatementParameter` with both
pro rata elections.

**What is missing.** The substrate has no general notion of a basis. Every domain would otherwise
restate the counting unit, window and grouping rule. The design of this catalogue should decide
whether the four parts above are a substrate qualifier pattern (a basis node with a counting unit
concept, a `qnt:Recurrence` or anchored window, and a grouping rule tied to substrate S4's
occurrence grouping), with insurance's bases as applied schemes. The CCS template library
(computable-contract-substrate §5.11) needs the answer for its term and qualifier templates.

## 2. What LATTICE already has

| Need | Existing construct |
|---|---|
| amounts, bounds, ranges in a unit, several currencies | Quantification `Quantity`, `Bound`, `Range`, `alternativeBound` (ADR-A95) |
| percentages of a base | `qnt:DerivedValueSpace` (ADR-A93) |
| relative changes ("more than 10%") | `qnt:AnchorBinding` with a proportional offset |
| conversion at a date | `qnt:Conversion` of kind contextual |
| caps consumed over a period, reset by recurrence | Behaviour `AllowanceDefinition`, `AllowanceAccount` |
| ordering between competing draws | `bhv:priority`, `bhv:PriorityOrdered` |
| grouping occurrences into one event | AIR substrate item S4 (occurrence grouping) |
| parameters attached to terms | A-101 term parameters, `ins:Qualifier` |
| shares of a group | Party `ParticipationGroup`, `GroupMembership`, `pty:share` |
| capacity accounting in insurance | `applied/capacity` and the MERIDIAN FBO capacity tank |

## 3. What a design must decide

1. **Nested accounts.** Whether "part of and not in addition to" is a tree of allowance accounts
   where each draw debits every ancestor (A1 to A5, A8), and how a lesser section cap under a
   shared limit (A3) and an excess layer that drops down (A6) fit it.
2. **Combinators.** The highest of several retentions (A16, A18), the highest of several limits
   (A9), coinsurance splits (A20), and order of payment (A24) as named, declared operations over
   accounts, not code.
3. **Grouping.** Related claims as one (A15, A28) through substrate S4.
4. **Reinstatement and reduction.** Recoveries crediting accounts (A25), and reductions for amounts
   recoverable elsewhere (A26, A27).
5. **Aggregates over bound instruments.** Income and exposure limits (A30 to A33) summing over the
   instruments `ins:boundUnder` a power, with the notification threshold as a derived trigger.
6. **Remuneration formulas.** Commission, fees and profit commission (A35 to A46) as derived
   amounts with a declared basis, adjustable with the premium they derive from.
7. **Bases.** The general basis pattern of §1.7, and whether it belongs in the substrate.
8. **Where each lives.** Which parts are substrate (accounts, combinators, derived amounts) and
   which applied (insurance limit kinds, capacity).

Each row above becomes a test case when the design is written.
