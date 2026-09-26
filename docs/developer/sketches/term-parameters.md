# Term Parameters: Meeting the Facet Design's Aims in LATTICE and Open CBAA

Version 0.1, draft for review. Works through the contract structure and financial behaviour
design supplied for review (its parameter carriers are called "facets"), states the aims it
achieves, and shows how LATTICE's applied insurance reference implementation meets every aim in
full and how Open CBAA meets the ones a binding authority needs, pragmatically. It also answers
how liability direction is modelled when claimants are unknown at binding. Companion to the
[MORK bridge](mork-bridge.md), which connects the two treatments, and to the
[peril whitepaper](peril-structure-whitepaper.md).

---

## 1. Summary

The reviewed design attaches typed parameter nodes to the node that records what a clause does
(its function: grant, exclusion, sub-limit, condition), keeps parameters that describe one term
apart from relations between terms, validates each parameter kind with its own shapes, and
compiles the whole into behavioural resources (capacity, scope predicates, flows) that a
deterministic evaluator runs.

Every aim of that design can be met on LATTICE, with three differences of approach:

| Difference | Reviewed design | LATTICE and Open CBAA |
|---|---|---|
| name | "facet" | **term parameter** in the applied insurance contract module, **statement parameter** in Open CBAA. "Facet" is kept out of both (§2) |
| substrate | its own upper model | LATTICE Instrument's `ins:Qualifier` ("a qualifier constraining or refining another element") is the substrate class a term parameter specialises. Amounts, bounds and multiple currencies come from Quantification, scopes from Eligibility, parties from Party, finite resources from applied Capacity |
| compilation | mandatory: behaviour exists only as the compiled graph, kept in step with the structure | **optional**: the declarative graph is always evaluable directly, and compiled forms are derived artefacts that must agree with it. Compilation is used where performance needs it (§5) |

LATTICE's reference implementation gives the idea its fullest treatment, with every parameter
kind, relation and compiled capacity form. Open CBAA uses the subset a binding authority's scope
of underwriting authority needs, as statement parameters, and can use the LATTICE forms where a
deployment wants them, through the MORK bridge.

## 2. Naming

"Facet" is already used for several things these designs touch: faceted classification in
thesauri, the characteristics of a peril (which the peril vocabulary now calls
**characteristics**, not facets), and search facets in any user interface. It says nothing about
what the thing does. The replacements name the role:

| Concept | Name | Why |
|---|---|---|
| a node that qualifies one contract term with a value and its basis | **term parameter** (`ctr:TermParameter ⊑ ins:Qualifier`) | it is a parameter of a term, and LATTICE already has the qualifier concept |
| the node recording what a clause does | **term** (the reviewed design's "term application") | in LATTICE a term is an `ins:Provision` or `ins:Obligation`. In Open CBAA it is a statement (`stm:Statement`) |
| a dependency between two terms (erosion, attachment, contribution) | **term relation** (`ctr:TermRelation`) | compiled, where compilation is used, into applied Capacity dependencies |
| Open CBAA's per-statement parameters | **statement parameter** | existing name (design-spec §3.5) |
| a governed extension parameter | **registered parameter kind** | the extension is a kind with a shape, not a free-text node |
| the characteristics of a peril | **peril characteristics** | peril vocabulary §6.3 |

## 3. The Aims, One by One

Each aim is stated as the reviewed design achieves it, then how LATTICE's reference and Open
CBAA achieve it.

| # | Aim | Reviewed design | LATTICE reference (`insurance/contract`) | Open CBAA |
|---|---|---|---|---|
| T1 | a parameter inherits scope, peril and validity from the term it qualifies | parameter hangs off the term application | `ins:qualifies` to the term (functional). Scope is an `elg:AdmissionProfile` on the term, validity the term's `fnd:TemporalScope` | parameters are properties and bindings of the statement, whose `stm:scope` and agreement validity apply |
| T2 | each parameter states its own basis, so several limits on one term are self-describing | `hasBasis` on every limit and retention | `ctr:basis` exactly one on limit, retention and aggregate parameters, bound to a basis scheme contract | a scope limit binding gains `stm:limitBasis` (the SoUA "limit or sum insured basis" row). Two limits of different kinds are different parameter kinds already (per-risk sum insured, GWP income limit) |
| T3 | parameter kinds are disjoint and composed in bundles on one term | disjoint facet classes, bundles by convention | disjoint `ctr:TermParameter` subclasses (§4). Bundles are checked by shapes per term function ("a coverage grant has at least one limit and exactly one claims basis") | parameter kinds are a closed set of `stm:ParameterKind` individuals. Composition shapes per statement kind (§6) |
| T4 | a basis may require companion parameters (aggregate basis needs a window, linear trigger needs floor and ceiling) | SHACL-SPARQL | same, as constraint shapes per parameter kind | same, per statement kind |
| T5 | one economic quantity stated in several currencies | limit to value node to several monetary extents | `qnt:Bound` with `qnt:alternativeBound` (ADR-A95): one bound, several statements in different units, compared in the candidate's own unit, never converted | the same Quantification construct, already used in the worked agreement (GBP or EUR limit) |
| T6 | intrinsic parameters are separate from relations between terms | facets against flow directives | term parameters against term relations. Relations compile into Capacity dependencies | Open CBAA has few relations: aggregate GWP accumulators (Behaviour allowances, design-spec §6.4) and precedence statements. Towers and layers are not a binding authority's concern |
| T7 | extension is governed: a new kind is admissible only with its own shape | custom facet plus registered shape | a new kind is a concept in the parameter kind scheme, `fnd:Governable`, admitted when Active and its shape exists. An unadmitted kind's parameters are carried but excluded from evaluation and compilation | same, for statement parameter kinds |
| T8 | structural and behavioural vocabularies are authoritative in their own layer, joined by explicit crosswalks | two scheme sets and crosswalks | Vocabulary scheme contracts on both sides. Exact crosswalks use `skos:exactMatch`, weaker ones are advisory (Surface source fidelity) | uses the same contracts, and the MORK bridge for anything not one-to-one |
| T9 | compilation is deterministic, many-to-many and traceable | compiler with projection links | applied Capacity projection (§5): each compiled node is a `fnd:DerivedArtefact` with its read set and input hashes | not required. Available by lifting through the MORK bridge |
| T10 | an unconstrained dimension means "any", never the empty set | explicit wildcard concepts | Eligibility has no empty-set trap: a profile with no condition on a dimension does not constrain it. A shape warns when a hierarchical condition names no required concept | same |
| T11 | peril membership follows the hierarchy | subsumption-aware membership | `elg:HierarchicalMatch` with exclusions (ADR-A87) | same, degrading to set membership for flat editions ([MORK bridge](mork-bridge.md) §3) |
| T12 | liability direction and party roles qualify parameters | role facet, claimant and payee roles | §7 below | §7 below |
| T13 | time: claims basis, waiting period, indemnity period, occurrence grouping, retroactive dates | temporal facets, some declared without properties | durations and anchored ranges from Quantification, validity from Foundation. Retroactive and continuity dates are parameters with values, not a gap | SoUA claims basis, usual and maximum duration, advance binding and quoting periods become statement parameters (§6) |
| T14 | runtime tractability without hard-wiring vocabularies | generated local shadows | Surface generated classes and closures, and the Capacity runtime profile, all optional | compiled closures per pinned edition (design-spec §4.4), optional |
| T15 | evaluation is deterministic on well-formed graphs | stated as a theorem | Behaviour and Capacity laws with recorded discharges | the same laws, through the same layers |
| T16 | known modelling mistakes are caught | a defect catalogue | each defect becomes a shape or a law test (§8) | shapes |

## 4. Term Parameters in LATTICE's Reference Contract Module

### 4.1 Classes

```
ctr:TermParameter ⊑ ins:Qualifier ⊓ =1 ins:qualifies.ctr:Term
```

`ctr:Term` is the applied insurance term: an `ins:Provision` or `ins:Obligation` with a
function concept (coverage grant, exclusion, sub-limit, condition, deductible, declaration,
extension, write-back) from a function scheme.

| Kind | Carries | Replaces |
|---|---|---|
| `ctr:LimitParameter` | a `qnt:Bound` (upper, with alternative bounds), basis | limit facet |
| `ctr:RetentionParameter` | a `qnt:Bound` (lower, for a retention), basis, optional coinsurance ratio | retention facet |
| `ctr:DefenceCostParameter` | defence cost treatment concept | defence cost facet |
| `ctr:ClaimsBasisParameter` | claims trigger basis concept, retroactive date, continuity date | claims basis facet and the unfinished temporal facet |
| `ctr:WaitingPeriodParameter` | a duration `qnt:Quantity`, calendar basis | waiting period facet |
| `ctr:IndemnityPeriodParameter` | a duration, basis | indemnity period facet |
| `ctr:ExtendedReportingParameter` | a duration, activation condition | unfinished temporal facet |
| `ctr:AggregateParameter` | aggregation window, counting basis, aggregate deductible as a `qnt:Bound` | the aggregate context of the aggregation facet |
| `ctr:OccurrenceGroupingParameter` | window duration, overlap rule, maximum windows, anchoring method | the hours-clause context of the aggregation facet |
| `ctr:ReinstatementParameter` | count, percentage, pro rata time, pro rata amount, automatic | reinstatement facet |
| `ctr:TriggerParameter` | trigger type, payout structure, thresholds as `qnt:RangeSet` on an intensity space, tiers, composition | trigger facet |
| `ctr:CollateralParameter` | collateral type, minimum ratio, facility reference | collateral facet |
| `ctr:PoolShareParameter` | pool, share, payout basis, cap | pool participation facet |
| `ctr:PremiumParameter` | premium basis, amount, rate, minimum, deposit | premium facet |
| `ctr:PartyRoleParameter` | the harm, claim, liable and payment roles it qualifies (§7) | actor facet |
| `ctr:DeclarationParameter` | declared values as references to asset exposure valuations and financial metrics | the unfinished declaration facet |

All pairwise disjoint. Two changes from the reviewed design are deliberate:

1. **The aggregation facet is split in two.** It carried two unrelated property groups (an
   aggregate's window and deductible, and an hours clause's grouping of losses), one of which was
   always dormant. Two kinds let each shape require what its kind needs, with no "dormant group"
   rules.
2. **Declarations point at exposure data.** Declared TIV and revenue are facts the asset
   exposure ontology holds (valuations, financial metrics). A declaration parameter references
   them, so a declared value and the exposure record cannot disagree silently.

### 4.2 Values

Amounts are `qnt:Quantity` values. A limit, retention or aggregate deductible is a `qnt:Bound`,
so the same comparison and alternative-bound semantics apply everywhere. Durations are
quantities on a duration space with calendar units where needed (ADR-A94). Percentages and
ratios are quantities on a proportion space. No bare decimals, so every number carries its
space, and a shape never needs a "currency present if amount present" rule.

### 4.3 Term relations

```
ctr:TermRelation ⊑ fnd:Version ⊓ =1 ctr:relationSource ⊓ =1 ctr:relationTarget ⊓ =1 ctr:relationKind
```

Kinds: erosion, defence erosion, aggregation, aggregate deductible feed, attachment, drop-down,
primacy, contribution, pool distribution, collateral draw, override, follow form, scope
expansion (write-back), scope narrowing. The reviewed design's split between relations that
become behaviour and relations that only reshape structure is kept: follow form, override and
scope expansion are resolved structurally (they change which parameters a term has) before any
evaluation.

## 5. Compilation Is Optional

### 5.1 Three routes to an answer

| Route | What runs | Authority | When |
|---|---|---|---|
| R1, direct | evaluation over the declarative graph: Eligibility's SPARQL reference evaluation for scopes, a parameter interpreter for amounts and time | normative | always available, the specification of meaning |
| R2, compiled | applied Capacity projection (resources, accumulators, dependencies), Surface restatements and closures, OWL classes for design-time checks, the Capacity runtime profile | `srf:CachedReproducible`: authoritative only because it is reproducible from R1's inputs | where throughput or latency needs it: bind-time checks at volume, scenario runs, portfolio accumulation |
| R3, advisory | projections through inexact crosswalks, heuristic summaries | `srf:Advisory` | discovery, triage, dashboards |

The reviewed design had only R2: behaviour existed only once compiled, and structure and
behaviour had to be kept in step. Here R1 always exists, so R2 is an optimisation that can be
switched on per deployment, per term kind or per check, and switched off again without loss of
meaning.

### 5.2 No two-way synchronisation

Compiled forms are derived one way from the declarative graph, never edited, and never written
back. Each carries its read set and input hashes (Surface manifests, `fnd:DerivedArtefact`), so
staleness is detectable by comparing hashes, and regeneration follows the hash-based invalidation
LATTICE already defines ([ontology architecture](../../architecture/ontology-architecture.md#10-hash-identities) §10). A deployment that
never compiles never has anything to keep in step.

### 5.3 Parity

A compiled form must give R1's answer. Parity is tested, not assumed: a conformance corpus of
terms and cases runs through both routes, and a discrepancy fails the compiled form's
publication. Surface's parity shapes and the Capacity runtime profile's invariants are the
existing mechanisms. Surface itself restates and indexes only: creating behavioural nodes
(capacity resources, dependencies) is the Capacity projection compiler's job, which Surface then
accelerates.

## 6. Statement Parameters in Open CBAA

A binding authority's scope of underwriting authority is a table of rows per segment (M5 SoUA
base table). Open CBAA meets the aims those rows need without term parameter classes. Each row
is a statement parameter: a property of the bound authority grant, or a parameter binding from
a template to an agreement variable (design-spec §3.5, ontology README §4).

| SoUA row | Statement parameter | Aim met |
|---|---|---|
| maximum limits of liability or sums insured | scope limit (interval condition on the case's sum insured), alternative bounds for several currencies | T5 |
| limit or sum insured basis | `stm:limitBasis` on the scope limit binding, from the CBAA sum insured basis list | T2 |
| claims basis | new parameter kind, claims basis concept from the CBAA list | T13 |
| usual and maximum duration of policies bound | new parameter kinds, durations | T13 |
| maximum advance period for binding and for quoting | new parameter kinds, durations in calendar days | T13 |
| included and excluded perils | scope inclusion and exclusion over the bound peril edition | T11 |
| standard exclusions | scope exclusions, compared with the standard set to flag a non-standard table | T7 |
| minimum deductible and excess | new parameter kinds, bounds | T5 |
| GWP income limit and period | accumulator (Behaviour allowance) with its recurrence | T6 |
| level of authority | `stm:level` | existing |
| applicable pool schemes | new parameter kind, pool concepts | T8 |

Shapes check composition per statement kind (an authority grant has a scope, a limit basis when
it has a scope limit, a claims basis). A deployment that wants capacity behaviour (accumulators
by peril, scenario runs) lifts the bound grant into LATTICE term parameters through the MORK
bridge ([MORK bridge](mork-bridge.md) §5), and gets R2 from the reference implementation without
Open CBAA owning any of it.

## 7. Liability Direction and Unknown Parties

### 7.1 Direction is not a peril characteristic

The peril vocabulary's agency characteristic says who or what **acted** to cause the event
(natural, accidental, negligent, malicious). Liability direction is a different question: who
**suffered** the harm, who is **alleged liable**, who **brings the claim**, and who is **paid**.
A director's breach of duty (a cause, with agency negligent or deliberate) can reach the insurer
along several directions, and a D&O programme prices and responds differently to each.

### 7.2 Four roles

Each is a `pty:Role`. Party already allows an occupancy to exist before anyone fills it ("the
role slot can exist before anyone fills it"), which is what unknown claimants need.

| Role | Question | D&O example |
|---|---|---|
| harmed party | who suffered the loss | shareholders who lost value, the company itself, an employee |
| liable party | who is alleged responsible | a director, an officer, the company (entity cover) |
| claimant | who asserts the claim, possibly for another | a shareholder bringing a derivative action on the company's behalf, a regulator |
| payee | who receives the insurer's payment | the director (non-indemnifiable loss), the company (reimbursement of its indemnity), the claimant directly where direct action applies |

At binding, a contract names **role types and populations**, not people. "Claims by
shareholders", "claims by the insured entity against its own directors", "regulatory
investigations" are conditions over the claimant role's type and its relation to the insured.
At claim time, occupancies are created and filled with actors. Nothing about an unknown claimant
has to be invented at binding.

### 7.3 Direction is derived

| Direction | Condition over the roles | Example |
|---|---|---|
| first party | the harmed party is an insured | property damage to the insured's building, the entity's own cyber costs |
| third party | the harmed party is not an insured, and the liable party is | a customer sues the company |
| insured against insured | the claimant is an insured, and so is the liable party | the company sues its former director |
| derivative | the claimant acts for the harmed party, which is an insured | shareholders sue directors on the company's behalf |
| fourth party | the harmed party's relation to the insured runs through an intermediary | a customer of the insured's customer, a supplier's supplier whose failure the insured is blamed for |

Because direction is derived from roles and relationships, it is never asserted by hand, and a
new direction is a new derivation rule, not a new concept on every claim. Fourth-party distance
needs the relationship graph (who stands in what relationship to the insured, directly or
through whom), which the asset exposure ontology holds as counterparty populations and
dependencies ([asset exposure ontology](asset-exposure-ontology.md) §5.15).

### 7.4 In a D&O programme

| D&O construct | Expression |
|---|---|
| Side A (directors, non-indemnifiable loss) | payee role director, liable role director, condition: the company has not indemnified |
| Side B (company reimbursement) | payee role company, liable role director |
| Side C (entity, often securities claims only) | liable role company, claimant type securities holder |
| insured against insured exclusion | exclusion over claimant ∈ insureds, with write-backs for derivative actions, whistleblowers and insolvency practitioners as classification statements |
| order of payments (Side A first) | a precedence statement, and under compilation a priority among capacity draws |
| claims made with continuity dates | claims basis parameter with retroactive and continuity dates |

In LATTICE's reference this is a `ctr:PartyRoleParameter` plus Eligibility conditions over the
role occupancies. In Open CBAA, a binding authority rarely writes D&O, but the same roles serve
its existing statements: obligations already name obligor and obligee occupancies, and claims
authority by claimant type (M8) is a scope over the claimant role.

## 8. The Defect Catalogue as Shapes

Every recurring mistake the reviewed design lists becomes a check. The main ones:

| Mistake | Check |
|---|---|
| basis on the term instead of the parameter | limit, retention and aggregate parameters require a basis, terms may not have one |
| one node as two parameter kinds | disjointness (OWL) and a shape |
| aggregate basis without a window | aggregate-basis limits require an aggregate parameter on the same term |
| deductible and excess as separate kinds | not possible: one retention kind, the difference is an attachment relation |
| amount without currency | impossible by construction: amounts are quantities in a unit |
| grouping window without overlap rule and maximum windows | occurrence grouping parameter requires all three |
| waiting period confused with occurrence grouping | different kinds with different value spaces |
| coverage grant without claims basis | required by shape per function |
| unadmitted extension kind evaluated | parameters of a kind that is not Active with a shape are excluded from R1 and R2 |
| cyclic term relations | acyclicity shape over relations, as MORK does for mapping precedence (ADR-A97) |
| empty scope set | no empty-set semantics exist. A condition naming nothing is warned |

## 9. Where It Lives

| Piece | Home |
|---|---|
| `ins:Qualifier`, `ins:Provision`, `ins:Obligation` | LATTICE Instrument (substrate, unchanged) |
| term, term parameters, term relations, function and basis schemes | LATTICE `applied/insurance/contract/` |
| compiled capacity forms and runtime profile | LATTICE `applied/capacity/` and its projection profile |
| harm, liable, claimant and payee role types, direction derivation | LATTICE `applied/insurance/common/`, used by `contract/` and `claims/` |
| statement parameters for SoUA rows | Open CBAA `statement/` |
| lifting and lowering between them | the MORK bridge, in Open CBAA's mapping graphs |

## 10. Open Questions

| # | Question |
|---|---|
| TP-Q1 | Adopt "term parameter", "term relation" and "peril characteristic" as the names? |
| TP-Q2 | Should the reference contract module be rebuilt on these classes now, or migrated from its current form when the applied insurance sub-folders are created? |
| TP-Q3 | Which checks, if any, should Open CBAA compile by default (bind-time authority at volume is the likely first)? |
