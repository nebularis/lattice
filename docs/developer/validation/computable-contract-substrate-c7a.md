<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C7a, regimes and gating

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c7a-regimes`. Commits are the human's, and the change is
merged into `main` before its release tags are created
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C7a in detail)
**Decisions:** ADR-A104 decisions 6, 7 and 8, ADR-A106 and its addendum (C11a-Q2, C11a-Q4), CC-D8,
DP6, ADR-A113. C7a-Q1 to C7a-Q5 answered 2026-10-04 (Q4: `ins:tolledIn`). C7a-R1, authoring with
or without a reasoner, decided 2026-10-04 after the examples (ADR-A104 2026-10-04 addendum,
decision 5)

## Invariant

A contract's regimes are Behaviour state spaces that arise under a term and gate legal relations. The same legal triggers move a regime between states and make relations arise and end. State gates evaluation and never enters a design-time comparison (DP6).

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

## Artefacts to inspect

- `ontology/instrument/examples/`: the four regime examples, written before the model.
- `ontology/instrument/README.md`: regimes, legal triggers and gating, with diagrams and the worked examples.
- `ontology/instrument/shapes/`: the regime, trigger and gating shapes.
- The ADR-A104 addendum (2026-10-04), "a regime is stated once".

## Deliberate non-coverage

Evaluation of gating and per-occasion resolution (C12, C13). Due ranges, recurrence, survival, `ins:ends`, constitutive terms, sections and party resolution (C7b). Parameter bindings, including a regime's durations from wording variables (C8). Threshold regimes over measured values held in capacity (applied layer, §7.8). Gates whose subject is another participant's share or another agreement (held design question HQ-2). Instruments without wording (HQ-1). `owl:AllDifferent` over Behaviour's policy and kind individuals (FU-C7a-a, TD-17).

## Handoff

Written by the building machine when the work is ready for the human to commit.

Phase 1, examples first (ADR-A-C2), 2026-10-04:

- **Built:** the four examples in `ontology/instrument/examples/` (`licence-notice.ttl`,
  `supply-suspension.ttl`, `facility-cure-period.ttl`, `service-dispute.ttl`), and the ADR-A104
  addendum "a regime is stated once" (Proposed). Between them the examples use every legal trigger
  (`OnExercise`, `OnCondition`, `OnExpiry` in days and in business days, `OnAct`), `ins:tolledIn`,
  `ins:arisesOnBreachOf`, a per-occasion regime, and gates within one regime and across two.
- **Run by the agent:** each example with the C6 model, every lower layer's vocab, and the shapes of
  Foundation, Vocabulary, Quantification, Eligibility, Wording, Behaviour and Instrument, under
  pySHACL with and without RDFS inference. All four conform without inference. With RDFS,
  `service-dispute.ttl` fails Instrument's relation shapes on `tmpl:on-dispute`: C6's domain on
  `ins:activity` makes the `ins:OnAct` trigger a legal relation. That is the case C7a-Q2 removes,
  and it passes once the model drops the domain. A probe with a transition's selection policy removed
  is rejected by Behaviour's structural shape, so the run is not vacuous.
- **Not run:** the `mise` checks, which belong to the model phase.
- **Check first:** the addendum's decisions 1, 3 and 5, and the clause texts, which carry the
  examples' meaning.
- **Deviations from the plan:**
  - Stated regimes assert Behaviour's terms explicitly. Behaviour's structural shapes require
    `bhv:selectionPolicy` and `bhv:activationPolicy` on every transition, and with regimes stated
    once no instantiation step asserts them. So every regime node carries its `bhv:` type, every
    regime transition its two policies, and every trigger its kind. Decided as C7a-R1 (addendum
    decision 5): the assertions are the baseline, and `owl:hasValue` restrictions plus domains on
    `ins:ofPower`, `ins:ofObligation` and `ins:tolledIn` let an OWL 2 RL reasoner supply them. A
    scratch test confirmed it: `licence-notice.ttl` with every `bhv:` type, kind and policy removed
    conforms to Behaviour's shapes after an owlrl closure, and a trigger with only `ins:ofPower`
    gains its class, type and kind. Rows C7a-15 to C7a-18 test it in the model phase.
  - The value shapes use `sh:in`, not the `sh:hasValue` first proposed. The same scratch test showed
    that `sh:hasValue` rejects correct lean data on the asserted graph, and misses a wrongly stated
    `bhv:AllMatches` on the closed graph, where the reasoner has merged it with `bhv:SingleMatch`.
    `sh:in ( bhv:SingleMatch )` reports the wrong value at its transition on the asserted graph in
    both modes, and at every transition on the closed graph.
  - A clause that states only a regime binds no term (14.1 in `supply-suspension.ttl`, 22.1 and
    22.2 in `facility-cure-period.ttl`). Nothing requires a bound term per stated term, and binding
    an empty one would add a node no evaluation reads (addendum decision 1).
  - The baseline activity scheme gains six activities the examples need: `GrantSublicence`,
    `Deliver`, `Suspend`, `Reinstate`, `ProvideService` and `Dispute`. The plan's vocab step named
    only the state kinds.
  - `ins:stateKind` is optional. A state with no common kind (unaffected, undisputed, a settled
    dispute) has none. The kinds used are `InForce`, `NoticePeriod`, `Terminated`, `Suspended`,
    `ForceMajeure`, `CurePeriod`, `Default` and `Disputed`, the baseline scheme's first contents.
  - The licence's exit on termination for cause takes two transitions, from in force and from the
    notice period, since a transition has one source state.

Phase 2, the model, 2026-10-04:

- **Built:** `instrument` 0.10.0 (additive), `instrument-vocab` 0.10.0, `instrument-shapes` 0.3.0,
  all generated from `ontology/instrument/README.md`, which gains:
  - terminology for regimes, regime transitions, the five legal triggers and twelve properties,
    with the words not used (lifecycle, status, suspended or paused, event)
  - §5.7 (an overview picture)
  - §10 Legal Triggers (kinds, expiry, tolling, arising and ending)
  - §11 Regimes and Gating (stated once, with the layered insurance cover as one labelled use-case
    among three, the regime kinds with state diagrams, the gating rule, whose state gates, DP6)
  - §12 Authoring With and Without a Reasoner (C7a-R1)
  - four worked examples (§16.5 to §16.8), laws and release notes
  - 46 Mermaid diagrams, every one parsed by mermaid 11
  - sections 10 to 14 renumbered to 13 to 17. No document links to them by number

  `tools/test_regimes.py` holds rows C7a-01 to C7a-13 and C7a-15 to C7a-18. `tools/test_instrument.py`
  now asserts the current versions, 0.10.0 and shapes 0.3.0, and keeps its release-note assertions.
  The ontology architecture's Instrument rows, the catalog and the release table are updated.
- **Check first:**
  - §12 and the B4 finding below.
  - The default in `ins:arisesOn`'s comment: a relation with no arising trigger has arisen once
    its instrument takes effect. C6's relations read that way, but no decision states it.
  - `ins:Regime ⊑ bhv:StateSpace ⊑ fnd:Version`, so a regime is a Foundation version through
    Behaviour, while ADR-A104 decision 2 says only `ins:Instrument` is a version in this layer.
    Nothing breaks: `ins:Template` is disjoint only with `ins:Instrument`, and every example is
    consistent. What a new clause version does to a regime's identity, and to the occupancies of
    its states, is C9's amendment question.
- **Deviations from the plan:**
  - **The B4 shapes check `rdf:type` itself.** Written first with `sh:class bhv:StateSpace`, they
    could never fire: SHACL's `sh:class` and `sh:targetClass` follow the `rdfs:subClassOf` triples
    in the data graph, and the data is validated with Instrument's spec, where `ins:Regime ⊑
    bhv:StateSpace`. They now use `sh:path rdf:type ; sh:hasValue`, which no subclass axiom
    satisfies. The same fact corrects a claim in the phase 1 write-up and the addendum's first
    draft: Behaviour's shapes do select a node typed only `ins:RegimeTransition` when Instrument's
    spec is in the data graph, and report its missing policies. They skip it only without the
    spec. The engine matches the literal type, which is why B4 stays. Addendum decision 5 and
    README §12.1 are corrected.
  - **Tolling is checked per state space, not per regime.** The plan said a tolling state belongs to
    a different regime from the one its expiry fires in. That would also reject a sub-state of the
    period's own state, which may meaningfully stop its clock. `ins:TollingShape` rejects only a
    state of the state space the period runs in: a sibling, or the period's own state.
  - **The addendum's first draft said Behaviour's shapes require a trigger kind.** They require
    only the two policies. Instrument's trigger shapes now require the kind (`sh:minCount 1` with
    `sh:in`). Corrected in addendum decision 5.
  - `ins:by` is optional on `ins:OnAct`: without it, an act of the kind by any party fires the
    trigger.
  - `ins:stateKind` has no domain, under the domain rule. A shape checks that its subject is a
    state.
  - No threshold regime is in an example: its measured value lives in an applied layer's capacity
    model. §11.2 draws one.
  - Row C7a-11 (DP6) is tested structurally: nothing reachable from a relation's scope, activity or
    maintained condition is a state, and the licence's grant has no gate. No design-time envelope
    comparison exists yet to run.
  - Row C7a-14 is the existing suites, run below. It has no test of its own.
  - **Arising and ending take four triggers, not five** (found at README review, 2026-10-04). The
    shape first allowed `ins:OnExpiry` in `ins:arisesOn` and `ins:endsOn`. The sketch's §5.5 lists
    four, and an expiry has no anchor on a relation: it counts from entering a state. Corrected in
    `ins:ArisingShape`, the two properties' comments, the README and addendum decision 6, with a
    test in C7a-08.
  - **README review, 2026-10-04.** At the human's request, §4.2.4 now explains arising in the legal
    sense (source and moment, Hohfeld's operative facts, arising against falling due, ending,
    occasions), and §4.2.13 explains how regimes work: what they are for, where an instrument's
    regimes come from, the one state per regime at every moment, what a relation's regimes are,
    the three questions of existence, gate and scope, why a gate and not arising and ending, and
    per-occasion regimes. The human's edits to §4.2.13 are kept. Thirteen diagrams are added (59 in
    all), and every one renders under mermaid 11, which a parse alone does not show: a colon in a
    gantt task name parses and fails to render.

## Results

Run by the agent on machine R, 2026-10-04, with every tool package importing from this checkout.

| Row | Result |
|---|---|
| C7a-01 | pass: 0.10.0, imports unchanged, every new property states subject and value, `ins:activity` has no domain, the three trigger domains and no others, the fixed values are `owl:hasValue` |
| C7a-02 | pass: all eight examples conform to the structural and constraint shapes of Foundation, Vocabulary, Quantification, Party, Eligibility, Wording, Behaviour and Instrument. Also conform under pySHACL's RDFS and OWL RL inference |
| C7a-03 | pass: the four regime examples are consistent (reasoning harness) |
| C7a-04 to C7a-09 | pass: each change reported at its node, with its message |
| C7a-10 | pass: an `ins:OnAct` with an activity is consistent with not being a legal relation |
| C7a-11 | pass, structurally (see deviations) |
| C7a-12 | pass: the state kind contract, and every kind and activity the examples use is in the baselines |
| C7a-13 | pass: the README is the source of all five files, release notes recorded, shapes `.version` 0.3.0 |
| C7a-14 | pass: `tools/test_instrument.py` (with its two current-version assertions moved), `check:python-root` (84), `check:mork-compilers` (114), `check:persistence` (778), `check:vocabulary` (16), `check:ontology-catalog`, `check:ontology-versioning`, `check:import-guard`, `build:mtp` (lock unchanged), `check:mtp`, and the literate check of Foundation, Wording, Behaviour, Surface and Instrument |
| C7a-15 to C7a-18 | pass: the lean licence conforms after an OWL 2 RL closure, fails B4 at all eight regime nodes without one, a wrong policy is reported once where stated and at all four transitions after closure, and `ins:ofPower` alone yields the trigger's class, type and kind |

`tools/test_instrument.py` and `tools/test_regimes.py`: 105 passed, and 106 after the README review's arising test. Release rows added for
`instrument-v0.10.0`, `instrument-shapes-v0.3.0` and `instrument-vocab-v0.10.0`. Nothing else
imports Instrument, so nothing cascades.
