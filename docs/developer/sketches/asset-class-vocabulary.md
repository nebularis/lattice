<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Sketch: a reference asset class vocabulary

**Status:** written 2026-11-08 for the unit `asset-class`. The maintainer answered ASC-Q1 to ASC-Q6 the same day, and the [plan](../plans/asset-class.md) takes the answers.
**Decisions it rests on:** [ADR-A98](../../architecture/decisions/ADR-A98-applied-layout-and-insurance-modules.md) (decisions 1, 2 and 5, and its addendum of 2026-11-08), [ADR-A99](../../architecture/decisions/ADR-A99-reference-vocabularies-and-peril-structure.md) (decisions 1 and 5), [ADR-A100](../../architecture/decisions/ADR-A100-hierarchical-match-over-flat-schemes.md) (decisions 4 and 5), [ADR-A126](../../architecture/decisions/ADR-A126-literate-specification-layout-and-grammar.md) and its addendum of 2026-11-08.

## 1. The problem

`cls:assetClass` is a cross-domain property in `applied/classification/`, governed by `cls-voc:AssetClassContract`, and no scheme is bound to the contract. `aeo:assetClass` and `aeo:unitAssetClass` in the exposure module specialise it, and every asset must have exactly one. With nothing bound, the exposure examples borrow the value types of `aeo:valueType` (`aeo-voc:Building`, `aeo-voc:Machinery`, `aeo-voc:Stock`) as asset classes, which conflates what a thing is with which bucket of value is exposed.

The exposure sketch planned an insurance asset class scheme, crosswalked to the CBAA insurable interest hierarchy. Asset classes are not an insurance notion, though. Lending takes collateral by asset class, an investor or a fund declares its holdings by asset class, and accounting classifies property, plant and equipment the same way. ADR-A98 decision 1 places a module at the lowest level that covers every module that uses it or is planned to, and its consequences name a lending domain reusing the asset class property.

## 2. Where it lives (ASC-Q1)

| Option | For | Against |
|---|---|---|
| **(a) `applied/asset-class/`, beside `classification/`** | the lowest level covering insurance now and lending and investment as planned. No namespace move later, which would break every importer | a third cross-domain module, which ADR-A98's decision 2 must list. Its text must stay free of domain vocabulary |
| (b) inside `classification/vocab` | one module fewer | that module only declares that the classifications exist, and territory, industry and asset class would then version together |
| (c) under `applied/insurance/` | the exposure sketch's plan | awkward for lending and investment, and a later move is a breaking change |

**Answered (a), 2026-11-08.** ADR-A98 gains an addendum naming the module. It imports the substrate, `classification/` for the contract it binds, and nothing of a domain.

## 3. The dimensions, kept apart (ASC-Q4)

An asset carries several classifications, and each answers a different question. Merging any two makes a scheme whose members are not mutually exclusive, so a value stops answering either question cleanly. The maintainer asked for the dimensions to be right the first time, since Surface can always combine them later for runtime efficiency.

| Question | Dimension | Where it lives |
|---|---|---|
| what kind of thing is it | **asset class** | this module |
| how does it behave in place: one location, or moving between locations | **mobility**, a characteristic of an asset class | this module |
| what is it used for, by whom | occupancy or industry | `cls:industry` |
| how is it built, protected, maintained | construction and protection attributes | the exposure module's attribute values |
| which value of it is exposed | value type (building value, contents, stock, gross profit) | `aeo:valueType` |
| who has what stake in it | interest kind | `aeo:interestKind` |
| when does a debt fall due, is a share listed, what does a fund invest in | maturity, listing, fund strategy | attributes of a holding, not kinds. Open as ASC-Q8 |

Three consequences follow.

- **The exposure sketch's `ex:SemiconductorFab`** is a non-residential building whose occupancy is semiconductor manufacturing. Its class is `NonResidentialBuilding`, and the fab is its industry.
- **Business income is not an asset class.** It is the value of an operation exposed to interruption, so it is a value type (`GrossProfit`, `Revenue`) of the location or asset whose loss interrupts it. The exposure sketch's "asset of the income kind" is not taken up.
- **Maturity, listing and fund type are not kinds.** The national accounts classification splits debt securities and loans by original maturity, shares by listing, and fund shares by money market or other. Each split is an attribute of a holding that can change while the instrument stays the same instrument, so the reference edition keeps the instrument and leaves the split to a characteristic, if a check ever reads one.

## 4. What it draws on (ASC-Q2)

| Source | Gives | Used as |
|---|---|---|
| **UN System of National Accounts 2008, Annex 1** (with ESA 2010 Annex 7.1, which follows it) | the one international classification spanning non-financial and financial assets: produced assets (fixed assets, inventories, valuables), non-produced assets (natural resources, contracts and licences, goodwill) and financial assets (monetary gold to receivables), mutually exclusive and coded | the backbone. Each concept cites its SNA category in a note |
| **IMF Classification of Financial Assets and Liabilities 2017** | the financial branch, as SNA's | confirms the financial branch |
| **IAS 16 and IAS 38** | the accounting classes of property, plant and equipment (land, buildings, machinery, ships, aircraft, motor vehicles, furniture and fixtures) and of intangible assets | the grain below SNA's machinery and transport equipment |
| **ISO 10962, CFI** | financial instrument categories (equities, debt, funds, entitlements, options, futures, swaps, others) | the grain below SNA's derivatives, futures and swaps under forward-type contracts. Its codes are not reproduced |
| **FIBO** | listings of instruments, securities, derivatives and loans, aligned to CFI | read for coverage. FIBO states these as deep OWL class trees with restrictions, and we keep them as SKOS concepts, which is the lesson taken |
| **EIOPA Solvency II CIC** and **ESMA AIFMD Annex IV asset types** | what an insurer's investments and a fund's holdings are declared as | read for coverage of the financial branch. Candidate published crosswalks |
| **CBAA insurable interest hierarchy** and **OED** | how a policy groups what it insures, and exposure value buckets | insurance-side crosswalks, never part of the reference edition |

The reference edition carries no mapping triple to any of these. A crosswalk is a reviewed artefact of its own (ADR-A99 decision 5, ADR-A100 decisions 4 and 5), published beside the edition only where the list owner's terms allow. SNA, the IMF classification, EIOPA's and ESMA's tables are published for reuse. ISO 10962's text is copyright, so a CFI crosswalk waits on its terms (ASC-Q9).

**SNA 2025.** The UN Statistical Commission adopted the 2025 SNA in March 2025, and its final text is due in 2026. It revises the asset classification, for example data in intellectual property products and crypto assets. The reference edition follows the 2008 classification, which is published and coded, and the move to 2025 is ASC-Q7.

## 5. Where the edition departs from SNA

Each departure is recorded beside its concept, as the modelling skill asks of any drift.

| Departure | Why |
|---|---|
| `BuildingOrStructure` and `Building` group SNA's dwellings (AN.111) and buildings other than dwellings (AN.1121), which SNA places under different parents | a building is the class most domains name first, insurance and lending among them, and SNA's split is by use, which a narrower concept keeps |
| transport equipment, other machinery and software are split further | SNA stops at AN.1131, AN.1139 and AN.1173. IAS 16's classes and the insurance lines need vessels, aircraft, road and rail vehicles and mobile plant apart |
| maturity, listing and fund type are dropped | §3: attributes of a holding, not kinds |
| futures and swaps under forward-type contracts | SNA names them in its definition of AF.712 without codes. CFI separates them |
| AN.116, the costs of ownership transfer on non-produced assets, is left out | a cost capitalised into an asset in the national accounts, never a class anything is |

## 6. Mobility (ASC-Q3)

The exposure module gives a fixed asset one `aeo:locatedAt` and a mobile asset `aeo:presence` nodes instead, and its sketch says a shape enforces this by asset class. So mobility is a characteristic of an asset class concept, `asc:mobility`, with the values `Stationary` and `Mobile`, stated only where it holds for everything the class covers. A class that covers both, or where location means nothing (software, a loan), states none. One shape keeps it honest: a concept that states a mobility has every narrower concept state the same one, so a value on a broad class is trustworthy. The exposure module's shape then refuses an asset of a mobile class with a single location, and an asset of a stationary class with presences.

No tangibility characteristic is added. No check reads one, and SNA's tree does not give it for free, since intellectual property products are fixed assets.

## 7. The literate tooling (ASC-Q5)

ADR-A126's individuals tables carry a name, its types and a fixed set of annotation columns. A SKOS scheme needs scheme membership, top concepts, the hierarchy, notes and characteristics, and Vocabulary's governed schemes need an identity, a governance state and an editorial note. Without a change, each of those would be a Turtle block beside the table, which is the opposite of what the tables are for.

**The change (answered, 2026-11-08):** a column of an individuals table whose header is a CURIE in backticks states that property. Each cell is a comma-separated list of CURIEs and Turtle literals. One rule covers `skos:inScheme`, `skos:topConceptOf`, `skos:hasTopConcept`, `skos:broader`, `skos:note`, `skos:notation`, `skos:editorialNote`, `fnd:hasIdentity`, `fnd:hasGovernanceState` and a module's own characteristic, so no further labels are needed. ADR-A126 gains an addendum for it.

## 8. Questions

| ID | Question | Options | Leaning |
|---|---|---|---|
| **ASC-Q1** | Where does the reference asset class edition live | (a) `applied/asset-class/`. (b) `classification/vocab`. (c) `applied/insurance/` | **Answered (a)**, 2026-11-08, the maintainer |
| **ASC-Q2** | Which standards does it draw on, and how | §4 | **Answered**, 2026-11-08: all of them inform it, SNA 2008 is the backbone, and crosswalks are separate artefacts |
| **ASC-Q3** | Does the scheme carry a mobility characteristic | (a) yes, read by the exposure shape. (b) no | **Answered (a)**, 2026-11-08 |
| **ASC-Q4** | How fine, and which dimensions | §3 | **Answered**, 2026-11-08: dimensions apart, about three levels below the tops |
| **ASC-Q5** | How a README states a SKOS scheme | (a) CURIE columns in the individuals tables, with an ADR-A126 addendum. (b) Turtle blocks | **Answered (a)**, 2026-11-08 |
| **ASC-Q6** | Lifecycle | a plan, a status record and Validation Packs, built autonomously on `air/asset-classes` and committed locally | **Answered**, 2026-11-08 |
| **ASC-Q7** | When the edition moves to SNA 2025 | (a) when the final text is published, as a release that may invalidate. (b) now, from the pre-edit text | open, leaning (a) |
| **ASC-Q8** | Whether maturity, listing and fund type become characteristics | (a) when a check or query reads one. (b) now | open, leaning (a) |
| **ASC-Q9** | Which crosswalks are published beside the edition | CBAA and OED (insurance side), CIC, AIFMD, CFI (subject to ISO's terms) | open, each its own slice once a consumer needs it |
