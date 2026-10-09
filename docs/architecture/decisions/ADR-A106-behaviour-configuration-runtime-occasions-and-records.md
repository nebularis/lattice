<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A106: Behaviour configuration, runtime, occasions and records

**Status:** Accepted
**Date:** 2026-10-01 (proposed), 2026-10-01 (accepted, Gate A)
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
   **Runtime state belongs to persistent things.** A state occupancy is for a subject's persistent
   identity where the subject is versioned, so a regime's state outlives a new version of the
   instrument it governs (ADR-A104 decision 2). An occasion is for the bound relation in force when
   it arose, and moves to a later version's relation only when an amendment affects existing
   occasions (sketch §5.8, §5.9).
6. **Alignment by subclass, no runtime inference** (sketch §7.3). Instrument specialises
   Behaviour only where a legal construct adds axioms or shapes (ADR-A104). The runtime engine
   reads Behaviour's terms only, so every specialised node carries its `bhv:` type explicitly
   (law B4). Instrument needs no compiled wiring: its triggers are Behaviour triggers.
   **Engine settings stay explicit.** ADR-A09 and ADR-A10 stand: every transition definition
   declares its selection and activation policy, with no Behaviour-wide default. Regime authors
   never state them, because `ins:RegimeTransition` restricts them (ADR-A104) and template binding
   asserts them (B4).
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

## Addendum (2026-10-02): nested states, history and concurrent regimes

**Status:** Accepted 2026-10-02 (CCS slice C11a, phase 1). The design is the
[nested states sketch](../../developer/sketches/nested-states-and-history.md), which this addendum
summarises. It settles what "Not decided here" deferred.

1. **Reference semantics.** Behaviour takes W3C SCXML as its reference, without claiming
   conformance. It follows SCXML's compound and parallel states, initial
   states, history, inner-first transition selection and exit and entry order, and departs where
   RDF and the evidence rule need it: no pseudo-state nodes, no document order, no clock, no
   datamodel or executable content, no final states, and internal self-transitions by default
   (sketch §2).
2. **Regions.** A state holds sub-states through regions. A region is a `bhv:StateSpace` naming
   the state it refines with `bhv:regionOf`, with its own `bhv:initialState`. One region makes a
   compound state, several a parallel one. A machine is nested in a state only when its states
   have no meaning outside it, must end on every exit from it, or must be found again on return.
   Otherwise it is a separate regime, with guards and legal triggers for any interaction (sketch
   §3, §3.1).
3. **History per transition.** `bhv:entryMode` on a transition definition is `bhv:DefaultEntry`
   (when absent), `bhv:ShallowHistory` or `bhv:DeepHistory`. History reads the occupancies the
   target's last exit ended (`bhv:exitedBy`), and each resumed occupancy names the one it resumes
   (`bhv:resumedFrom`). Nothing else is stored for it (sketch §4).
4. **Occupancies per level.** A subject holds one current occupancy for every active state, at
   every level. B6 applies to every occupancy an execution creates or ends (sketch §5).
5. **Concurrency.** Separate regimes on one subject and parallel regions within a state are both
   kept. Behaviour never ranks regimes. A relation's `ins:appliesInState` holds when, for each
   regime its states belong to, the subject is in one of them. Conflicts between the relations
   regimes gate are resolved in Instrument. A guard may read a state with `bhv:requiresState` and
   `bhv:excludesState` (sketch §6).
6. **Evaluation order.** One macrostep per positioned stimulus: inner-first selection, the state's
   selection policy, conflicts by depth then priority (a remaining tie takes no transition and is
   Undetermined), exit deepest first, entry outermost first, then derived triggers to quiescence
   (sketch §7).
7. **Occasions.** `bhv:perOccasionOf` gives a state space one instance per occasion of a
   declaration: a refinement of a core occasion state (also a region of it) or a parallel regime on
   the occasion. A refinement's transitions stay inside it, and moves between core states remain
   the evaluator's (sketch §8).
8. **Laws.** B5 is restated as the history rule. B6 is extended to ancestors, default sub-states and
   exits. B9 (one tree per transition, refinements closed), B10 (no cycle of derived triggers at one
   position) and B11 (a well-formed active configuration) are added (sketch §10).

9. **Answered 2026-10-02.** Occasion suspension uses history: a seventh core state, `bhv:Live`,
   holds `Pending` and `Arisen`, and reinstatement enters it by deep history (C11a-Q1, breaking
   for `behaviour-vocab`). A period may declare states during which it does not run, on
   `ins:OnExpiry`, counted by C12 over the occupancy history (C11a-Q2, in C7a). A relation gated by
   a per-occasion state reads the occasion its arising trigger refers to, and is Undetermined when
   that is not exactly one (C11a-Q4, in C7a).
10. **Internal transitions.** A transition whose source and target are the same state is internal
   unless it declares `bhv:transitionType bhv:External`: it applies its effects without leaving
   the state, so it creates no occupancy and keeps the state's entry time and history. Re-entry
   must be declared (sketch §4.1).

11. **`AllMatches` (C11a-Q3, answered 2026-10-02).** `AllMatches` applies only to internal
   transitions. Every enabled internal transition of the state fires, its effects composed in one
   computation in the sequential environment: in `bhv:priority` order, each guard reading what the
   one before it left. Competing `AllMatches` transitions have distinct priorities. State-changing
   transitions from one state on one trigger agree on `SingleMatch` or `PriorityOrdered`. In one
   pass the internal transitions fire before the state change. The parallel environment is left to
   the [evaluation context](../../developer/sketches/evaluation-context.md) design.

## Addendum (2026-10-09): records are findings

**Status:** Proposed 2026-10-09 (CCS slice C9b1, C9b1-Q2). The reasoning is the
[consent sketch](../../developer/sketches/consent-and-group-powers.md), §2.1 and §2.6. Narrows
decision 5.

1. **What the parties did is the layer above's fact.** An exercise, an assent, a consent or a notice
   with legal effect is a legal act of Instrument's acts document (ADR-A104, 2026-10-09 addendum).
   Behaviour records what the evaluator concluded about it.
2. **An exercise record is the finding about one exercise.** `bhv:exercised` names the exercise act,
   with no range (law B7). `bhv:tookEffect` and `bhv:reasonNotTaken` are unchanged. `bhv:actor` on an
   exercise record is deprecated, since the act names its party and a second copy can disagree.
3. **`bhv:AcceptanceRecord` and `bhv:accepted` are deprecated** (C9b1-Q2, answer (a)), reported by a
   warning shape, and removed in CCS C16c. Whether a version is agreed is read from assents.
4. **Act records keep performance.** A notice with legal effect kept as an act record in an example
   shows the notice's performance. The examples are annotated, not moved, since Behaviour names no
   Instrument term.
5. **The narrowing changes what the records mean**, so Behaviour's documents take a MINOR version
   marked breaking (ADR-A113).
