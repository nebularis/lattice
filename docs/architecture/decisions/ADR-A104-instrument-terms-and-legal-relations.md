<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A104: Instrument: terms and legal relations

**Status:** Accepted
**Date:** 2026-10-01 (proposed), 2026-10-01 (accepted, Gate A)
**Supersedes:** ADR-A07b. Carries ADR-A96 onto terms
**Related:** ADR-A01 (addendum), ADR-A86, ADR-A87, ADR-A92, ADR-A102, ADR-A103, ADR-A105, ADR-A106,
ADR-A109, ADR-A112, ADR-A113, ADR-A-C2
**Unit:** [`computable-contract-substrate`](../../developer/plans/computable-contract-substrate.md)
(C1, decisions CC-D5, CC-D8, CC-D10, CC-D11, CC-D12). Delivers
[normative-rule-substrate](../../developer/plans/normative-rule-substrate.md) slice N4

## Context

**Premise.** An agreement binds its parties by terms, and the terms create legal relations: a
party must do something for another, must not do it, may do it despite a duty not to, need not
do it, or may by an act change another's position. A relation arises on an event, falls due by
a time, ends, and can be excepted in some cases. Some terms create no relation at all: they define
words or deem facts. Whether a relation applies can depend on where the agreement stands, in a
notice period or a suspension, which changes over time while what was agreed does not.

**Examples.**

1. *Facility agreement.* The borrower must repay each loan on its maturity date, must ensure its
   leverage stays below a ratio while the facility is in force, and must not grant security over
   its assets, except security the agreement permits. An event of default gives the lenders, acting
   by a majority, the power to declare every loan due.
2. *Clinical trial protocol.* An investigator must report a serious adverse event to the sponsor
   within 24 hours of learning of it. Unblinding is prohibited, except where the sponsor waives
   the prohibition for a patient's safety. The sponsor may end a site's participation, and the
   site's duties to report survive the ending.

**The problem.** ADR-A07b gave Instrument the smallest shape Behaviour could target: `ins:Element`,
`ins:Provision`, `ins:Obligation` and `ins:Qualifier`, with no modality, deadline, fulfilment,
breach, exception, power or time. Neither example can be stated in it. The design that fixes this
was tested clause by clause against four instruments, giving 101 scenarios (S1 to S101) and
sixteen laws. The [sketch](../../developer/sketches/computable-contract-substrate.md) §5 to §7 is
the design. This ADR records what is decided and points to it.

## Decision

1. **Instrument and term** (sketch §5.1). `ins:Instrument` is a versioned legal instrument,
   `ins:expressedIn` exactly one assembled `wrd:Wording` (ADR-A112). `ins:Term` is a provision the
   parties are bound by. It is not a version: it belongs to an owner and changes only with it
   (decision 2). `ins:Provision` is retired: a clause is a `wrd:Element`, and what it provides is
   an `ins:Term`. `ins:Element` is retired with it, since nothing needs a common superclass. A term
   stated in several elements (another language, a consolidated text) is ADR-A96's many-provision
   attachment, carried as `ins:alsoExpressedIn` beside the one element that owns it.
2. **Meaning belongs to its text** (sketch §5.9, CC-D12). Every clause's meaning has two tiers,
   each with exactly one owner:
   - **Stated meaning** (`ins:Template`) says what the clause says in its own words, naming roles,
     defined words and variables. It is part of exactly one element version
     (`ins:expressedIn`). A library clause's stated meaning is shared by every instrument that
     includes the clause. A bespoke clause's is a template used once.
   - **Bound meaning** says what the clause says for one instrument, naming occupancies and values.
     It is part of exactly one instrument version (`ins:boundIn`), `ins:boundFrom` exactly one
     stated node, or `ins:impliedBy` a source for a term implied by law. It is a derived artefact
     (ADR-A92) of stated meaning, the wording's variable values and the instance's definitions.

   Relations, definitions, deemings, qualifiers and regimes arise under a term and belong to it.
   Only `ins:Instrument` is a version in this layer: the text carries the history. A change of
   meaning is therefore a new element version, reached through an amendment (decision 11), or
   regenerated stated meaning for the same element version, which is a correction and not an
   amendment (law I18). An instrument version binds exactly the stated meaning of the elements its
   wording includes (law I17).
3. **Five legal relations** (sketch §5.2): `ins:Obligation`, with `ins:ContinuingObligation` and
   `ins:Prohibition` beneath it, `ins:Permission`, `ins:Exclusion` and `ins:Power`. Each arises
   under exactly one term and belongs to it (decision 2), and the four top classes are pairwise disjoint.
   `ins:excepts` links a permission to a prohibition, and an exclusion to an obligation or a
   power. They map onto Hohfeld's relations and deontic logic as the sketch §8 states, with one
   modal verb per class in controlled English (§8.1).
4. **Parties** (sketch §5.3). `ins:obligor` and `ins:obligee`, `ins:holder` and
   `ins:counterparty`, ranging over role occupancies, participation groups and, on templates only,
   roles. A party that depends on the case is a contingent occupancy (ADR-A102) with
   `ins:resolvedBy` an evidence binding. A group holds a joint power under an `ins:ConsentRule`.
   **Parties are fixed at arising** (law I11). A relation that resolves to a group whose mode of
   acting the instrument does not state is Undetermined until the graph holds an assertion of
   that mode (CC-D10).
5. **Content** (sketch §5.4): `ins:activity` (a concept), `ins:scope` (an Eligibility condition),
   `ins:maintains`, `ins:fulfilledWhen` (generated from the activity by default, and met by the
   obligor's act or a delegate's under `pty:Delegation`, replacing ADR-A07b's `ins:fulfilledBy`), and
   `ins:Qualifier`s that `ins:qualifies` a term or a relation. Qualifiers hold static parameters.
   Dynamic quantities, a running total against a limit, belong to capacity through a Surface
   projection capacity defines (sketch §7.8).
6. **Legal triggers** (sketch §5.5, §7.3). `ins:OnExercise` (`ins:ofPower`), `ins:OnBreach`
   (`ins:ofObligation`), `ins:OnAct` (an activity, `ins:by` a party), `ins:OnCondition` (an
   Eligibility condition) and `ins:OnExpiry` (`ins:after` a duration, or `ins:computedBy`), each a
   subclass of `bhv:TriggerDefinition` with its ranges set. A relation `ins:arisesOn` and
   `ins:endsOn` a legal trigger. `ins:arisesOnBreachOf` and `ins:arisesOnExerciseOf` are short
   forms. `ins:due` is a range anchored at a named valid time, never evaluation time (law I9).
7. **Regimes** (sketch §6.3, §7.4, CC-D8). `ins:Regime ⊑ bhv:StateSpace`, with `skos:altLabel
   "Dispensation"`, is a state space whose states gate relations. A regime arises under a term
   and belongs to it, like a relation (decision 2). `ins:RegimeTransition ⊑
   bhv:TransitionDefinition` carries value restrictions for single-match selection and immediate
   activation, so authors never state them, and takes legal triggers only. States stay
   `bhv:State`s, typed by `ins:stateKind` concepts. `ins:appliesInState` gates a relation on a
   regime's state. The three kinds are period, switching and threshold. No class names a contract
   state or a state change, and the T-Box does not use the word "lifecycle".
8. **Structure and state stay apart** (sketch §6.3). `ins:appliesInState` never enters a
   design-time comparison (authority envelopes, materiality, overlaps, gaps). A state may be a
   fixed parameter of a comparison, never a variable within one (law B8, ADR-A106).
9. **Constitutive terms** (sketch §5.6). `ins:Definition` (`ins:defines`, `ins:means`, optionally
   scoped) and `ins:Deeming` (`ins:deems`, `ins:when`, `ins:conclusive`, `ins:forPurposeOf`). A
   deeming is a closure source: the instrument licenses the absence its condition reads (ADR-A105
   as revised).
10. **Exceptions carry a burden** (sketch §5.7, law I7). An exception applies to a case only when
   its scope is Permitted. An Undetermined exception does not apply, and nothing that would follow
   from its not applying is derived as a breach: the outcome is Undetermined with
   `exe:ExceptionNotEstablished`, naming the party that bears the burden.
11. **Change and composition** (sketch §5.8). `ins:Amendment` from one instrument version to the
    next, with agreed, operational and effective times, `ins:affectsExisting` (default false, law
    I14), `ins:byExerciseOf` a power under its consent rule, and `ins:textChanges` to the wording
    amendments. `ins:incorporates`, `ins:boundUnder` (an instrument created by exercising a power)
    and `ins:takesEffectWhen`.
12. **Sections** (sketch §5.10, CC-D11). A section is a wording element of type Section within one
    instrument. `ins:appliesWithin` and `ins:notWithin` place terms, relations, definitions and
    qualifiers. A case's section is fixed by the power it was bound under (law I15). Definitions of
    one word combine by union where their parts overlap, unless one prevails, and every overlap is
    reported at design time (law I16).
13. **Binding and the template library** (sketch §5.9, §5.11, CC-D5). Stated meaning is bound per
    instance through `ins:ParameterBinding`s to wording variables. Only bound meaning is evaluated
    (law I13). Binding asserts the explicit `bhv:` type beside every `ins:` type (law B4). The
    substrate's library lives in `ontology/instrument/templates/`, a new directory carried by this
    ADR: library wording elements and the stated meaning they own, for periods, switching and
    threshold regimes, relation patterns, and term and qualifier templates. Domain templates live
    in their applied layers.
14. **Calculated values** (sketch §7.9). Every slot that takes a duration or an amount also admits
    `ins:computedBy`, whose target is defined by the contract amounts work. A value not yet
    computable evaluates Undetermined with a diagnostic.
15. **Evaluation** (sketch §6.1, §6.2). One algorithm per class, over Eligibility's three values,
    at a stimulus-log position. A condition may read another relation's recorded occasion state
    when the graph of breach, exercise and state-read edges is acyclic (law I6), which revises
    ADR-A109 (NRS N2).
16. **Laws I1 to I18** (sketch §5.12) are the layer's laws, each with its register. I17 and I18
    are decision 2's.

**Versioning.** ADR-A07b's contract (R-B7) carries for `ins:Instrument`: an instrument version is
never updated in place, and a material change is a new version superseding the old, made by an
`ins:Amendment`. Terms, relations and regimes need no contract of their own, because each belongs
to an immutable owner (decision 2). What changed between two instrument versions is computed from
their wordings (sketch §5.8). Where a replaced clause continues an earlier obligation for live
occasions, the amendment states it with `prov:wasRevisionOf`.

## Consequences

- Instrument is rewritten in CCS slices C6 to C9 and C8a, each a breaking MINOR under ADR-A113
  (`0.9.0` to `0.13.0`, after Foundation's keys cascade takes `0.8.0`, ADR-A114). Instrument imports Wording and Behaviour configuration. Once ADR-A106
  lands, nothing outside Instrument imports it, so the rewrite cascades only to its own documents.
- Instrument's shapes check ownership in SHACL Core and law I17 in two SHACL-SPARQL shapes,
  shipped for consumers who do not use the LATTICE runtime (sketch §5.9).
- Party's README reference to `ins:fulfilledBy` is updated in C6.
- `ins:InstrumentTarget` is declared in Instrument's vocabulary (ADR-A106 removes it from
  Behaviour's).
- The neutral examples E1 to E8 (sketch §9) are authored before the README, under ADR-A-C2 and its
  2026-10-01 addendum.
- NRS slice N4 is delivered here. ADR-A105 and ADR-A109 are revised in NRS. Applied insurance
  Phase 5 builds on this ADR (ADR-A101). Open CBAA migrates (CCS plan §7).

## Addendum (2026-10-04): a regime is stated once

**Status:** Accepted 2026-10-05, proposed 2026-10-04 (CCS slice C7a, C7a-Q1 to C7a-Q5). The reasoning, with an example
use-case, is the [CCS sketch](../../developer/sketches/computable-contract-substrate.md) §7.4.1.
The examples are `licence-notice.ttl`, `supply-suspension.ttl`, `facility-cure-period.ttl` and
`service-dispute.ttl` in `ontology/instrument/examples/`.

1. **One tier for regimes** (revises decisions 2 and 13). A regime is stated meaning only. It
   arises under the stated term of the clause that states it, and its states, transitions and
   triggers are shared by every instrument whose wording includes that clause. Each instrument's
   progress through it is an occupancy `bhv:forSubject` the instrument's persistent identity, so
   an amendment that leaves the regime's clause alone leaves the occupancy alone. A value the
   instance supplies, such as a notice length from a variable, is resolved per instrument at
   runtime from its assembled wording (C8). A bound term may therefore own no relation: a term
   whose clause states only a regime binds nothing.
2. **Law I13 restated.** Only bound *relations* are evaluated. Regimes are read as stated, per
   subject. A bound relation names the stated regime's state in `ins:appliesInState`.
3. **Triggers name stated relations.** A regime's `ins:ofPower` and `ins:ofObligation` name the
   stated relation, and match the exercise or breach of any bound relation instantiated from it.
   A per-occasion regime (`bhv:perOccasionOf`) likewise names the stated relation, and covers the
   occasions of every bound relation instantiated from it. A bound relation's own `ins:arisesOn`,
   `ins:arisesOnBreachOf`, `ins:arisesOnExerciseOf`, `ins:endsOn` and `ins:excepts` name bound
   nodes, since it restates its template in full.
4. **Whose state gates a relation** (C7a-Q5). A gate reads the occupancy of the relation's own
   instrument identity, or, for a per-occasion regime, of the occasion its arising chain reaches
   (decision 9 of ADR-A106's addendum). Gates on another subject, one participant's share or
   another agreement, are held (CCS plan, HQ-2).
5. **Behaviour's terms on a stated regime, with or without a reasoner** (revises decisions 7 and
   13, decided 2026-10-04). Behaviour's engine reads only Behaviour's terms: `bhv:StateSpace`,
   `bhv:TransitionDefinition` with its `bhv:selectionPolicy` and `bhv:activationPolicy`, and
   `bhv:TriggerDefinition` with its `bhv:triggerKind`. Behaviour's structural shapes require each
   policy (minimum one), and Instrument's require each legal trigger's kind, which Behaviour leaves
   optional. Decision 13 had instantiation assert them beside the `ins:`
   types. A regime is stated only (decision 1), so nothing instantiates it, and the `bhv:` terms
   come from one of two places:

   - **Asserted, for data read without a reasoner.** This is the baseline, and every example
     follows it. Each regime node carries its `bhv:` type beside its `ins:` type. Each
     `ins:RegimeTransition` states `bhv:selectionPolicy bhv:SingleMatch` and `bhv:activationPolicy
     bhv:ImmediateActivation`. Each legal trigger states its `bhv:triggerKind`. Law B4's shapes
     require the explicit `bhv:` type, because the engine matches the `rdf:type` triple as
     written, and a node typed only `ins:RegimeTransition` would be invisible to it. They check
     the triple itself (`sh:path rdf:type ; sh:hasValue`): `sh:class` follows the subclass axioms
     in the data graph, and would pass without it.
   - **Entailed, for authors working with a reasoner.** An optional convenience. Each Instrument
     class states its fixed Behaviour terms as axioms, so an author with an OWL 2 RL reasoner (or
     a more expressive one) writes the `ins:` type alone:

     | Class | Axioms (`rdfs:subClassOf`) |
     |---|---|
     | `ins:Regime` | `bhv:StateSpace` |
     | `ins:RegimeTransition` | `bhv:TransitionDefinition`, `owl:hasValue bhv:SingleMatch` on `bhv:selectionPolicy`, `owl:hasValue bhv:ImmediateActivation` on `bhv:activationPolicy` |
     | `ins:OnExercise`, `ins:OnAct` | `bhv:TriggerDefinition`, `owl:hasValue bhv:ExternalStimulus` on `bhv:triggerKind` |
     | `ins:OnBreach`, `ins:OnCondition` | `bhv:TriggerDefinition`, `owl:hasValue bhv:DerivedTrigger` on `bhv:triggerKind` |
     | `ins:OnExpiry` | `bhv:TriggerDefinition`, `owl:hasValue bhv:ScheduledTrigger` on `bhv:triggerKind` |

     The restrictions are `owl:hasValue`, not `owl:allValuesFrom`. An `allValuesFrom` restriction
     only constrains a value already stated, while `hasValue` in a superclass makes a reasoner add
     the value (OWL 2 RL rule cls-hv1). RDFS alone gives the `bhv:` types through `rdfs:subClassOf`
     but not the values, so the convenience needs the OWL 2 RL profile. `ins:ofPower`,
     `ins:ofObligation` and `ins:tolledIn` each have a domain (`ins:OnExercise`, `ins:OnBreach`,
     `ins:OnExpiry`), so a reasoner also derives the trigger's class, and from it the `bhv:` type
     and kind, from the property alone. Each of these properties has only that one subject, which
     meets the domain rule in `.github/copilot-instructions.md`. `ins:condition` and `ins:after`
     have no domain, since terms in time (C7b) may reuse them.

   **Validate the graph the engine reads.** Without a reasoner, that is the asserted graph. With
   one, it is the closed graph, and B4's shape holds there because the reasoner added the `bhv:`
   types. A library template (decision 13) is written in the asserted form, so it serves both.

   **A wrong stated value.** All three properties are functional, and Behaviour does not declare
   its policy or kind individuals distinct. An author who states `bhv:selectionPolicy
   bhv:AllMatches` on a regime transition, with the axioms above and a reasoner, leads it to infer
   `bhv:AllMatches owl:sameAs bhv:SingleMatch`, after which every transition in the graph has both
   values. Two measures, combined:

   - **Instrument's value shapes**, which list the one permitted value (`sh:in ( bhv:SingleMatch
     )`, and so on for activation and each trigger kind). On the asserted graph they report the
     wrong value at the node that states it, in either mode, and let a value the reasoner will add
     be absent. On the closed graph they report the wrong value at every node the merge reached.
     `sh:hasValue` is not used: it would reject correct data written for a reasoner (the value is
     not yet there), and miss a wrong value after the merge (the right one is also there).
     Presence stays with the minimum counts, Behaviour's for the policies and Instrument's for the
   kinds, on the graph the engine reads.
   - **Distinct individuals in Behaviour** (follow-up FU-C7a-a, CCS plan): `owl:AllDifferent` over
     the selection policies, the activation policies and the trigger kinds, so that a reasoner
     reports the merge as an inconsistency at the triple that caused it.

6. **Smaller settlements.** `ins:activity` has no domain, so `ins:OnAct` reuses it for the act a
   trigger fires on (C7a-Q2). Decision 5's three trigger domains follow the same rule. `ins:arisesOn`, `ins:arisesOnBreachOf`, `ins:arisesOnExerciseOf` and
   `ins:endsOn` (decision 6) land with the triggers in C7a (C7a-Q3). They take the four triggers
   other than `ins:OnExpiry`, which counts from entering a state, and a relation has none to enter
   (sketch §5.5). A relation's own periods are due ranges (C7b). `ins:tolledIn` names the
   states in which an `ins:OnExpiry` period does not run (C7a-Q4, ADR-A106 addendum decision 9).
   `ins:stateKind` takes a concept under `ins-voc:StateKindContract`, with a baseline scheme bound
   as fallback.

## Addendum (2026-10-05): terms in time

**Status:** Accepted 2026-10-05, proposed the same day (CCS slice C7b, C7b-Q1 to C7b-Q7 and TQ1 to TQ7). The design is the
[terms in time sketch](../../developer/sketches/terms-in-time.md), which this addendum summarises.
The examples are `trial-reporting.ttl`, `lease-expiry.ttl`, `licence-survival.ttl` and
`service-renewal.ttl` in `ontology/instrument/examples/`.

1. **Due ranges** (revises decision 6 and law I5). An obligation has at most one due range
   (`ins:due`, a `qnt:Range`), and none where its words fix no time. A continuing obligation and a
   prohibition have none. This layer does not model the reasonable time the law implies where no
   time is fixed, unless a contract's express words define one. A due range is anchored at a
   `qnt:ContextValue` (ADR-A115) whose role is a named time, never evaluation time (law I9):
   the occasion's arising, the instrument's inception or ending, the start or end of a recurrence
   period, or a date the wording defines and C8 binds. Its offsets carry units, business days
   included. `ins:dueTolledIn` names states in which its time does not run, as `ins:tolledIn` does
   for an expiry.
2. **Recurrences.** `ins:recurrence` gives an obligation one occasion per period of a
   `qnt:Recurrence` anchored at a context value. A continuing obligation's recurrence gives its test
   dates.
3. **Windows.** `ins:window` on a power or a permission is the range in which it may be exercised
   or used. An exercise outside it has no effect (law I10). An offer or option lapses when its
   window closes, with no trigger of its own.
4. **Ending is entering a state** (revises decision 6, `ins:ends`). `ins:ends` on a state of a
   regime names what entering the state ends: the instrument (`ins-voc:TheInstrument`) or stated
   terms, matched to the bound terms instantiated from them. Expiry, termination on notice, for
   breach, on an event, by performance and at a long-stop date are each a transition into an ending
   state on a legal trigger. `ins:OnExpiry` takes `ins:at`, a value such as the Expiry Date, as an
   alternative to `ins:after`.
5. **A sixth legal trigger.** `ins:OnEntry ⊑ bhv:TriggerDefinition`, with `ins:ofState` and the kind
   `bhv:DerivedTrigger` fixed by an `owl:hasValue` restriction (decision 5 of the 2026-10-04
   addendum), fires when the subject enters a state. A relation may arise on it, and another regime
   may react to it.
6. **What ending does.** On entering an ending state, no new occasion arises under an ended term,
   arisen occasions persist (accrued rights and liabilities, law I3), pending occasions end, and
   relations arising on an `ins:OnEntry` of the state arise.
7. **Survival.** `ins:survives` on a stated term names an `ins:Survival`, with an optional
   `ins:survivalPeriod` from the ending and an optional `ins:survivesUntil` condition. With neither,
   the term survives without limit. It is read for each instrument through the bound term's
   `ins:boundFrom`. A term whose relations arise on entering an ending state survives for that
   purpose without saying so, since requiring express wording would not work in practice (TQ5).
8. **Deferred.** `ins:computedBy` (decision 14) waits for contract amounts (C7b-Q7). Rescission
   ab initio, frustration, termination by agreement (C9), and a party's or a section's ending
   (C7c, C9) are outside C7b. Business day conventions and times of day are held design question
   HQ-3.

## Addendum (2026-10-06): what terms are, and who they bind

**Status:** Proposed 2026-10-06 (CCS slice C7c). Records C7c-Q1 to C7c-Q9 as revised after the
examples phase, as decisions D1 to D22 of the [CCS plan's C7c section](../../developer/plans/computable-contract-substrate.md),
which states each in full. Restates decisions 4 and 12, details decision 9, and revises the
2026-10-05 addendum's decision 4. The examples are `framework-lots.ttl`, `service-towers.ttl`,
`facility-definitions.ttl`, `trial-definitions.ttl` and `supply-classification.ttl` in
`ontology/instrument/examples/`.

1. **What an instance stores** (D1 to D4). An instance stores only what differs from its form:
   identity and keys, parties, the values it gives the wording's variables, the elements its
   wording includes, `ins:boundUnder`, and records filling a contingent party. Stated meaning is
   content-addressed with its element version, so a wording matched on its hash is never restated,
   and it is context-free: a stated term never names another element's version, and scopes and
   endings name a section's persistent identity, resolved within the assembled wording. Bound
   meaning is a derived artefact (ADR-A92), generated on demand, cached as need dictates, and kept
   in its own subgraph where processing allows. Only bound meaning is evaluated (law I13).
2. **Generation shares** (D5). Binding resolves every word in each section, and sections whose
   words resolve alike share one bound term, recorded with `ins:boundWithin`. Generated nodes have
   deterministic identities. Sharing across instruments is CCS slice C16b, under its own ADR.
3. **Sections** (D6 to D8, restating decision 12). A sectioning term (`ins:Sectioning`,
   `ins:section`) declares the sections and places within each the terms it contains. Without one,
   the instrument is one section, the whole, and an element a term's words scope to is a section
   by being named. Sections nest. `ins:appliesWithin` values are alternatives, `ins:notWithin`
   excludes what lies at or below it, and a term with no scope governs the whole.
4. **Cases** (D9, law I15, C7c-Q1). `ins:boundUnder`, brought forward from decision 11, names the
   bound power whose exercise created an instrument, and that instrument falls in the one section
   the power is bound within. Any other case is not placed: each section's bound relations
   evaluate it in their own right.
5. **Cross-section terms and ending** (D10, D11, revising the 2026-10-05 addendum's decision 4). A
   qualifier spanning sections is bound once and qualifies each section's bound relations. A
   cross-section term whose words vary by section is split and reported while drafting.
   `ins:ends` may name a section, and entering the state ends, for that section's cases, every term
   bound within it.
6. **Constitutive terms** (D12 to D15, detailing decision 9). An `ins:Definition` defines exactly
   one word, the node stated meaning names in its place (a role, or a concept for a condition or
   concept word), and means at least one thing. Stated meaning names words and bound meaning names
   meanings: a condition slot on stated meaning may take a defined word, which binding replaces. `ins:actingRule` states how several parties act together. Overlapping
   definitions combine at binding, per section, as D13 sets out (law I16), and `ins:prevailsOver`
   between definitions removes an overlap. An `ins:Deeming` deems one condition, on at most one
   footing, conclusively or not, for named purposes or all. `ins:classification` is read, never
   evaluated, under a scheme bound to `ins-voc:TermClassificationContract`.
7. **Who terms bind** (D16 to D18, restating decision 4). Bound relations always name their
   parties. A party that depends on the case is a contingent occupancy with at most one
   `ins:resolvedBy`, an `ins:PartyResolution` (`ins:resolvesFrom`, `ins:resolutionStep`,
   `ins:resolutionFilter`), and is otherwise filled by a record of each occasion. A group's duty is
   decided by its composition rule. A group's power, and a group with no rule, are Undetermined
   until C9 (CC-D10).
8. **Party is domain-neutral** (D19). Party states a member's outward and inward shares
   (`pty:outwardShare`, `pty:inwardShare`), and two composition rules, `pty:EachForOwnShare` and
   `pty:EachForWhole`, replacing `pty:share`, `pty:SeveralOnly` and `pty:JointAndSeveral`. What a
   share means is the instrument's or the applied layer's. Caps are qualifiers.
9. **Deferred.** Evaluation of all of the above (C12, C13). Date and amount words, and the values
   parameter bindings carry (C8). Consent rules (C9, HQ-5). The closure declaration, rebuttal and
   supersession of deemings (ADR-A105, HQ-6). Precedence between terms (NRS N10). Sharing across
   instruments (C16b). A shared path type in Foundation (its own unit). Portions of one order
   (HQ-7).
