<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A106: Behaviour configuration, runtime, occasions and records

**Status:** Proposed
**Date:** 2026-10-01 (proposed)
**Amends:** ADR-A11 (target binding). Applies ADR-A08's tiers to documents
**Related:** ADR-A01 (addendum), ADR-A08, ADR-A09, ADR-A10, ADR-A67, ADR-A92, ADR-A102, ADR-A104,
ADR-A105, ADR-A112, ADR-A113, ADR-A-C2
**Unit:** [`computable-contract-substrate`](../../developer/plans/computable-contract-substrate.md)
(C2, decision CC-D8). Takes over the Behaviour part of
[normative-rule-substrate](../../developer/plans/normative-rule-substrate.md) slice N8, under its
retitled scope

## Context

**Premise.** Many things change state over time on recorded events: an account is opened, frozen
and closed, an order is placed, shipped and returned, a duty arises, is performed or is breached.
What states exist and what moves between them is configured once. What happened is recorded each
time, and every state an entity has been in must be traceable to the event that put it there. A
model of state that change should not need to know what kind of thing is changing.

**Examples.**

1. *Software licence.* The licensor may suspend the licence for non-payment and must reinstate it
   when payment arrives. Each suspension and reinstatement is an act on a date, and the licence's
   state on any date is answerable from the record of those acts.
2. *Clinical trial protocol.* The duty to report a serious adverse event arises once per event.
   Each event gives an occasion of the duty, with its own deadline, which is performed when the
   report is made or breached when the deadline passes unreported.

**The problem.** Behaviour imports Instrument for one axiom: `bhv:targetsElement` has
`rdfs:range ins:Element`. That range is an inference axiom, so anything an effect targets is
classified an `ins:Element`, and under Instrument's disjointness an effect targeting a relation
or an occasion makes the graph inconsistent. It also blocks Instrument from building on Behaviour
(ADR-A104) without an import cycle. `bhv:forSubject` is limited to role occupancies, so a state
cannot belong to an instrument or an occasion (Open CBAA L15). Configuration and runtime records
share one document, so anything that imports Behaviour's configuration also imports its records.
The design is the [sketch](../../developer/sketches/computable-contract-substrate.md) §7.

## Decision

1. **Behaviour names no higher layer** (sketch §7.1). `bhv:targetsElement` is replaced by
   `bhv:targets`, with no range. `bhv:forSubject` loses its range. Behaviour stops importing
   Instrument, and `bhv:InstrumentTarget` moves to Instrument's vocabulary (ADR-A104). Behaviour
   sits below Instrument (ADR-A01's addendum, ADR-A112).
2. **ADR-A11 amended.** An effect definition declares one `bhv:targetKind` and at least one
   explicit target through `bhv:targets`, to any resource. Which targets are proper for a target
   kind is checked by the shapes of the layer that declares the kind, not by an axiom in Behaviour.
3. **Configuration and runtime documents** (sketch §7.2), in one namespace:

   | Document | ADR-A08 tier | Holds |
   |---|---|---|
   | configuration | declaration | state spaces, states, transitions, triggers, guards, effects, allowance definitions, the policy individuals |
   | runtime | occurrence, execution, state record | stimuli, transition executions, effect applications, state occupancies, allowance accounts, occasions, the records of decision 5 |

   The runtime document imports the configuration document. Instrument imports configuration only.
   Applied layers may import either.
4. **Every state entry is recorded** (sketch §7.5, law B6): at minimum a state occupancy naming its
   transition execution and cause, or carrying `fnd:Evidence` pointing to an external log entry.
   The initial state is recorded when the subject takes effect. The restriction that a transition
   definition has at least one effect is removed: being in a state is often the whole effect, and
   the evidence rule keeps the record the restriction stood in for.
5. **Occasions and records** (sketch §7.6). An occasion is one legal relation for one case, with
   the state space Pending, Arisen, Performed, Breached, Ended, and Suspended. Its occupancies are
   derived artefacts (ADR-A92) recording their read set. Runtime records: act, transition
   execution and state occupancy, breach (derived, or asserted with `fnd:assertedBy`), exercise
   (of a power, with whether it took effect and why not), determination, deemed fact, and
   amendment acceptance. Their properties are the sketch's table.
6. **Alignment by subclass, no runtime inference** (sketch §7.3). Instrument specialises
   Behaviour only where a legal construct adds axioms or shapes (ADR-A104). The runtime engine
   reads Behaviour's terms only, so every specialised node carries its `bhv:` type explicitly
   (law B4). Instrument needs no compiled wiring: its triggers are Behaviour triggers.
7. **Roles filled later** stay in Party. A role occupancy is a temporally scoped version, so
   filling a role is a new version with `pty:occupiedBy`, superseding the unfilled one (sketch
   §7.6). The split does not touch it.
8. **Laws B1 to B8** (sketch §7.11) are the layer's laws:

   | Law | Statement |
   |---|---|
   | B1 | An occasion occupancy is derived, never asserted, and records its read set |
   | B2 | An occasion's state follows only from records |
   | B3 | Every scheduled trigger is a positioned stimulus. The engine never reads a clock |
   | B4 | Every `ins:` specialisation in the data also carries its `bhv:` type |
   | B5 | A suspended occasion or regime resumes its prior state on reinstatement, pending the history design |
   | B6 | Every entry into a state is recorded, with its execution and cause or external evidence |
   | B7 | Behaviour names no Instrument or Wording term, and no layer names a higher one, checked at design time |
   | B8 | Design-time comparisons never read runtime records. A state may parameterise a comparison, never vary within one |

**Not decided here.** Nested states, history and concurrent regimes per subject need statechart
semantics and conflict rules of their own (sketch §7.10). They are CCS slice C11a, which amends
this ADR. Until then B5 holds for one level of suspension.

## Consequences

- Behaviour takes a breaking MINOR under ADR-A113 (CCS slice C10): a range and an import are
  removed, a property is renamed, a document is split. `behaviour-vocab` and `applied/capacity`'s
  execution profile re-pin.
- C10a builds B7's import guard, the import-closure check ADR-A01 promised. C11 adds occasions,
  records and B6's shapes. C12 builds the runtime evaluator, with NRS N6's positioned stimuli.
- Every Behaviour example and capacity fixture runs before and after C10, so data relying on the
  removed range's inferred types is found (CCS plan risk R8).
- The platform's behaviour engine loads configuration and writes runtime records (Phase 3 plan).
- ADR-A105 (closure declarations) and the evidence rule meet in B6: the external log an occupancy
  cites is a fact source a closure may name.

**Open point at acceptance**, with a recommendation:

- **Engine settings.** ADR-A09 and ADR-A10 require every transition definition to declare its
  selection and activation policy, so that ambiguity is visible in data. Recommended: they stand,
  with no Behaviour default. Authors of regimes never state the policies because
  `ins:RegimeTransition` restricts them (ADR-A104) and template binding asserts them (B4). The
  plan's "engine-setting defaults" means exactly this. A Behaviour-wide default is the alternative,
  and would amend A-09 and A-10.
