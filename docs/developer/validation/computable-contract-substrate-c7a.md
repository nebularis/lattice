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

## Results

Written on machine R at verification.
