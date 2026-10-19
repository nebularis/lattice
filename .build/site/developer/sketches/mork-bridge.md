# The MORK Bridge: Industry Models and the LATTICE Reference

Version 0.2, draft for review. Specifies how Open CBAA works with the vocabularies and data the
market brings today (flat code lists, simple taxonomies, spreadsheet rows, bordereaux) and, where
a deployment wants it, with LATTICE's applied insurance reference implementation (the
[reference peril vocabulary](peril-vocabulary.md), [term parameters](term-parameters.md) and the
[asset exposure ontology](asset-exposure-ontology.md)), with MORK mappings between the two.
Nothing here is implemented yet.


Citations of `design-spec` and of codes AP, DP, D and I refer to Open CBAA's [design
specification](https://github.com/nebularis/open-cbaa/blob/main/docs/design/design-spec.md) and
[LATTICE integration
specification](https://github.com/nebularis/open-cbaa/blob/main/docs/design/lattice-integration.md).
Where this sketch and the [applied insurance reference
epic](../plans/applied-insurance-reference.md) or its ADRs (A-98 to A-102) differ, they take
precedence.

---

## 1. Two Worlds

| | Industry as it stands | LATTICE reference |
|---|---|---|
| perils | whatever the contract's drafter supplies: a market cause-of-loss code list, a carrier's or MGA's own list, a simple two-level taxonomy, or a view the LMA may publish | a cause hierarchy with kind and part links, characteristics, collections, overlaps, thresholds |
| contract terms | SoUA table rows, schedule fields, free text | term parameters and term relations, optionally compiled into capacity behaviour |
| exposure | bordereau rows, statements of values, open exposure data files | the asset exposure ontology |
| who owns the meaning | the drafter and the market | LATTICE, as a reference that anyone may adopt |

Open CBAA must operate in the first world, because that is where agreements are written, and
must be able to use the second, because that is where the richer checks live. Neither may be
forced on a deployment. The bridge is how the two meet without either rewriting the other.

**Principles**

| # | Principle |
|---|---|
| B1 | **The operative vocabulary is the contract's.** The scheme a wording's values are drawn from is authoritative for that wording. A reference vocabulary is a lens, never an override |
| B2 | **Capability follows structure.** A check runs at the level of detail the operative scheme supports, and no further. A flat list supports membership only. A taxonomy supports hierarchical match. Characteristics, collections and thresholds exist only where the scheme or a crosswalk supplies them |
| B3 | **Never guess.** A check that needs structure the operative scheme lacks returns `Undetermined` with a reason naming the missing capability (`exe:NoHierarchy` under ADR-A100, `exe:MissingCandidate` for absent characteristics), which becomes a referral (design-spec §6.3) |
| B4 | **Mapping is data.** Every bridge between worlds is reviewed data: a crosswalk of SKOS triples for vocabularies, a MORK mapping graph compiled to RML for recurring data formats. Never code |
| B5 | **Exactness sets authority.** A value reached through an exact correspondence may decide. One reached through a broader, narrower or close correspondence may only advise (Surface source fidelity and derivation authority) |
| B6 | **Consumers declare what they trust.** Each check states which graph roles and which mapping fidelities it accepts (ADR-A13) |

## 2. Where a Peril Scheme Comes From

Open CBAA authors no peril scheme. The scheme bound to `rsk:PerilContract` for an agreement is
resolved by LATTICE Vocabulary's scoped bindings, most specific first:

| Precedence | Binding scope | Typical source |
|---|---|---|
| 1 | the agreement | the drafter's own list, for this agreement only |
| 2 | the drafting organisation and the market | an MGA's, carrier's or broker's house list |
| 3 | the market, with a regime where needed | a market edition, including one the LMA may publish, and the code list the CBAA SoUA tables reference |
| 4 | none (`voc:boundScheme`) | LATTICE's reference edition, the fallback when nothing more specific is bound |

LATTICE's precedence rule (a binding whose scopes are a strict superset wins, and a tie is a
governance error) gives this order without Open CBAA logic. Each agreement version records the
binding its values were resolved under (`voc:resolvedUnder`), so a later change of list does not
change what an accepted agreement meant.

A published LMA view is welcome and fits at precedence 3. If it is richer than the reference, it
serves directly. If it is flat, the bridge maps it to the reference as it would any other list.

## 3. What a Check Can Do

### 3.1 Kinds of peril scheme

| Kind of scheme | Structure it has | Examples |
|---|---|---|
| flat list | codes and labels, no `skos:broader` | the market cause-of-loss list behind the SoUA "Perils List" |
| taxonomy | a `skos:broader` hierarchy | a house list grouped into families |
| crosswalked list | either of the above, plus a reviewed crosswalk to the reference (§4) | a house list mapped once, at onboarding |
| reference-structured | kind and part links, characteristics, collections, overlaps, thresholds | the reference edition, a market edition built as an override of it |

A crosswalk does not give a list the reference's structure. A code mapped exactly is lifted to the
reference concept when data is ingested (§6), and is then decided against the reference. A code
mapped inexactly may advise, never decide (B5). A list may be 90% exactly mapped and 10% not, and
each code is treated by its own mapping.

### 3.2 What each check can do

| CBAA check | flat list | taxonomy | crosswalked list | reference-structured |
|---|---|---|---|---|
| segment included and excluded perils (SoUA U1, U2) | exact set membership | hierarchical match with exclusions | as its own structure, and as the reference for exactly mapped codes | full |
| open grant with exclusions ("all perils excluding flood and earthquake") | membership in the list minus exclusions | hierarchical | as above | full |
| standard exclusions present and unchanged (U4) | code set comparison | hierarchical comparison | comparison with the reference standard set through the crosswalk | full |
| cyber inclusion, exclusion and write-back (U5) | membership of the listed cyber code | hierarchical | cause, agency and mechanism through the crosswalk | full (peril vocabulary §6.8) |
| overlap needing a classification statement (surge and flood) | not detectable | not detectable | detectable for exactly mapped codes | full |
| materiality of a change to perils (M3) | set difference | subsumption between old and new scopes | as its own structure, plus collections | full, with design-time classes |
| accumulation by peril grouping (U9, GWP limits) | groupings declared by the drafter | by family | reference model groupings | full |
| natural catastrophe obligation (U8) | a drafter-declared set | family "natural hazard" if the taxonomy has one | reference natural hazard family | full |
| threshold-defined peril against event data | no | no | exact mappings only | full |

No check needs a rule of its own to degrade. A hierarchical match written for the reference and
evaluated against a flat list leaves every code it does not name Undetermined with
`exe:NoHierarchy` (ADR-A100). A condition on a characteristic finds no value on a flat list's code
and is Undetermined with `exe:MissingCandidate`. A cell that says "no" is one of these. A referral
carries the diagnostic, so an underwriter sees why the system could not decide.

## 4. Bridging Peril Schemes

### 4.1 From a drafter's list to the reference

A crosswalk is authored once per list edition, when a drafter's organisation is onboarded, and
reused for every agreement and bordereau that uses the list. A person reviews every mapping. A
model may propose them, in which case the proposals wait in MORK's review queue (ADR-A13) and only
accepted ones enter the crosswalk.

```mermaid
flowchart LR
    SRC["Drafter's list<br/>codes, labels, definitions"] -->|"author, or a model proposes"| PROP["Proposed mappings<br/>(MORK review queue, when proposed)"]
    PROP -->|"a person reviews"| ART["Crosswalk<br/>SKOS triples, characteristic values<br/>fnd:DerivedArtefact"]
    ART -->|"lookup at ingestion"| ING["Risk and loss records<br/>drafter code and reference concept"]
```

| Source code shape | Crosswalk content |
|---|---|
| one code, one reference concept | `skos:exactMatch` or `skos:closeMatch` |
| a code broader or narrower than any concept | `skos:broadMatch` or `skos:narrowMatch` |
| a code naming several axes ("accident railway crossing", "arson by a third person") | a cause match plus characteristic values on the code (`prl:typicalAgency`, `prl:typicalMechanism`) and, where present, a consequence or harm subject |
| a code with no cause ("delay", "no details", "liability for buildings") | characteristic or consequence values only. No cause match, so cause checks leave it Undetermined |
| a group code | membership of a `prl:ModelGrouping` |

### 4.2 From the reference to a drafter's list

The reverse direction serves a deployment that authors in the reference but must report or bind
in a market's codes. A reference concept lowers to the market code it maps exactly. Where only
broader codes exist, the lowering is inexact and flagged, and where no code exists, the value is
reported with the nearest broader code and a note. Lowering never invents codes.

### 4.3 Between two market lists

Two lists are bridged through the reference rather than to each other: each maps once to the
reference, and the list-to-list correspondence is derived by composition. Composition of an
exact and an inexact mapping is inexact (B5).

## 5. Bridging Contract Terms

Open CBAA's statement parameters and LATTICE's term parameters describe the same rows at
different depth ([term parameters](term-parameters.md) §6).

| Direction | What happens | Fidelity |
|---|---|---|
| lift: bound authority grant → LATTICE terms | each SoUA row parameter becomes a term parameter on a coverage-grant term. Scope limits become limit parameters with their basis, claims basis a claims basis parameter, GWP limits an aggregate parameter with its window, perils the term's scope | exact, row by row. The lifted terms are derived artefacts citing the bound statement |
| lower: LATTICE terms → SoUA rows | term parameters with a SoUA row counterpart lower to it | exact where a row exists. Parameters with no row (reinstatement, collateral, occurrence grouping) cannot lower, and are reported as "not expressible in a SoUA table" |
| from a spreadsheet SoUA | the base table's rows and their embedded variables map to statement parameters | MORK templates per row type. Human review of each first mapping, then reuse |

Lifting is how an Open CBAA deployment uses LATTICE's compiled capacity behaviour (accumulators
by peril, scenario runs) without Open CBAA owning term parameters or capacity. The lift is a
mapping, not a copy: re-running it on an amended agreement regenerates the terms.

## 6. Bridging Exposure

| Source | Target | Construct |
|---|---|---|
| bordereau risk rows | `rsk:Risk` and asset exposure exposure units | MORK data mappings compiled to RML, one mapping graph per reporting format version |
| statements of values, open exposure data files | asset exposure locations, assets, valuations, assessments | same, with reference data mappings for construction, occupancy and peril codes |
| asset exposure data → bordereau reporting items | lowering for reporting | exact where the data item exists, flagged otherwise |

Peril codes in exposure data go through the same peril crosswalk as contract perils, so a risk's
exposed perils and a segment's covered perils are compared in one scheme.

## 7. Governance

| Concern | Rule |
|---|---|
| where mappings live | a crosswalk is a reviewed graph in `insurance/peril/crosswalk/` or in a deployment. Proposals, when a model makes them, live in MORK's Mapping graph role (ADR-A13) until reviewed |
| review | every crosswalk mapping is reviewed by a person. For recurring data formats (§5, §6), template instantiations above the confidence threshold may be accepted without individual review, and are sampled |
| versioning | a crosswalk is versioned with both its source list edition and the reference edition. Either changing makes the crosswalk stale, which its read set shows |
| provenance | the crosswalk is a `fnd:DerivedArtefact` with its evidence and reviewer. A crosswalk from model proposals also cites the MORK proposals it accepted |
| disagreement | when the drafter's definition and the reference concept differ, the mapping is inexact (close or broad), never exact. The contract's definition stands (B1) |
| machine proposals | extraction and proposal follow design-spec §3.7: a proposal is not meaning until reviewed |

## 8. What LATTICE Provides

No bridge module exists. Each piece lives where its concern already lives:

| Piece | Home |
|---|---|
| hierarchical match over a list without a hierarchy, and `exe:NoHierarchy` | Eligibility and its compilers (ADR-A100) |
| some-value and every-value readings for checks across several values | Eligibility and its compilers (ADR-A103) |
| crosswalks as reviewed SKOS graphs with Foundation provenance, and published crosswalks | `insurance/peril/crosswalk/` (ADR-A100) |
| loss cause links carrying peril, mechanism and agency together | `insurance/exposure/` (`aeo:LossCause`) |
| proposals awaiting review, and ingestion of recurring formats compiled to RML | MORK |

## 9. Open Questions

| # | Question |
|---|---|
| MB-Q1 | Should an agreement-scoped peril binding be created for every agreement, or only when the drafter supplies a list other than their organisation's? |
| MB-Q2 | What confidence threshold, and what sampling rate, for accepting template mappings of recurring data formats without individual review? |
| MB-Q3 | Answered (ADR-A100 decision 10): a reviewed crosswalk of a widely used list may be published beside the reference edition where the list owner's terms allow, so a deployment using the list starts aligned |
