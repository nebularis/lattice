<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A104: Instrument: terms and legal relations

**Status:** Accepted
**Date:** 2026-10-01 (proposed), 2026-10-01 (accepted, Gate A)
**Supersedes:** ADR-A07b. Carries ADR-A96 onto terms
**Related:** ADR-A01 (addendum), ADR-A86, ADR-A92, ADR-A102, ADR-A103, ADR-A105, ADR-A106,
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
