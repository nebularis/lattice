<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 9. Change over time
{: #behaviour}

A facility does not stand still. Covenants are tested each quarter, breaches put it into default,
defaults are cured, and the agreement itself is amended. A typical schema handles this with a
`status` column, an `updated_at` timestamp and perhaps a history table filled by a trigger. The
Behaviour layer replaces all three with a declared state machine, and keeps every state the facility
has been in, when, and what caused it.

### The configuration: states and how to move between them

The leverage covenant's regime has two top-level states, performing and default. Default has stages
of its own. It starts with a cure period, which becomes uncured if the borrower does not fix the
breach within 20 business days.

<div class="mermaid">
stateDiagram-v2
  direction LR
  [*] --> performing
  performing --> in_default: covenant breached
  state "default" as in_default {
    state "cure period" as cure_period
    [*] --> cure_period
    cure_period --> uncured: 20 business days pass
  }
  in_default --> performing: covenant met again
</div>

<!-- source: ontology/behaviour/examples/covenant-default.ttl -->
```turtle
ex:covenant-regime a bhv:StateSpace ;
    fnd:hasIdentity ex:covenant-regime-identity ;
    bhv:initialState ex:performing .

ex:performing a bhv:State ;
    bhv:inStateSpace ex:covenant-regime .

ex:default a bhv:State ;
    bhv:inStateSpace ex:covenant-regime .

# The region: default's own stages. Naming default with bhv:regionOf makes it
# compound. The region has an initial state of its own, as any space does.
ex:default-stages a bhv:StateSpace ;
    fnd:hasIdentity ex:default-stages-identity ;
    bhv:regionOf ex:default ;
    bhv:initialState ex:cure-period .
```

A **state space** is the set of states a subject can be in, with one to start in. A state can have a
**region**, a state space of its own inside it. The cure period means nothing outside a default, so
it lives inside default, and every way out of default ends it too.

Transitions name where they start, where they go and what triggers them.

<!-- source: ontology/behaviour/examples/covenant-default.ttl -->
```turtle
# Out of the composite: leaves whichever stage is active, then default.
ex:cure a bhv:TransitionDefinition ;
    bhv:fromState ex:default ;
    bhv:toState ex:performing ;
    bhv:hasTrigger ex:on-covenant-met ;
    bhv:selectionPolicy bhv:SingleMatch ;
    bhv:activationPolicy bhv:ImmediateActivation .
```

Because the cure starts from `ex:default` itself, it applies from either stage. Meeting the covenant
again cures the default whether the cure period is still running or has passed. A flat status column
would need one rule per stage, and a forgotten one is a bug.

### The runtime: what actually happened

Configuration says what may happen. Runtime records what did, in four kinds of node.

| Node | Records | Relational counterpart |
|---|---|---|
| `bhv:Stimulus` | something arrived, with when it was recorded | an inbound event |
| `bhv:ActRecord` | who did what, under which case, from which stimulus | an activity log row |
| `bhv:TransitionExecution` | a transition was taken, caused by which stimulus | the trigger firing |
| `bhv:StateOccupancy` | the subject was in a state, from when to when, entered and exited by which executions | a status history row |

Here is the stretch when the first default was uncured, which is when the lenders could accelerate.

<!-- source: ontology/behaviour/examples/covenant-default.ttl -->
```turtle
ex:occ-4-uncured a bhv:StateOccupancy ;
    bhv:forSubject ex:facility ;
    bhv:occupiesState ex:uncured ;
    bhv:isHypothetical false ;
    bhv:isCurrent false ;
    bhv:enteredBy ex:exec-2 ;
    bhv:exitedBy ex:exec-3 ;
    fnd:hasTemporalScope [ a fnd:TemporalScope ;
        fnd:validFrom "2027-04-28T00:00:00Z"^^xsd:dateTime ;
        fnd:validTo "2027-05-15T12:00:00Z"^^xsd:dateTime ] .
```

There is one occupancy per active state at every level, so during that stretch the facility occupies
both default and uncured. Each occupancy names the execution that entered it and the one that ended
it, and each execution names its stimulus. The question "why was this facility in default on 1 May"
is answered by following links, not by searching logs. `bhv:isHypothetical` marks an occupancy that
is hypothetical rather than actual, and `bhv:isCurrent` marks the one in force now. An actual
subject has at most one current occupancy in each state space.

The example's year, in short:

| Date | What happened | State afterwards |
|---|---|---|
| 1 Jan 2027 | facility takes effect | performing |
| 31 Mar 2027 | Q1 test failed, leverage 4.2x against 4.0x | default, cure period |
| 28 Apr 2027 | 20 business days pass | default, uncured |
| 15 May 2027 | equity injected, covenant met again | performing |
| 30 Sep 2027 | Q3 test failed | default, cure period |
| 20 Oct 2027 | cured inside the cure period | performing |

[Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/behaviour/examples/covenant-default.ttl).

### Tying states back to the agreement

An Instrument example of a cure period shows how the agreement's own clauses drive the machine. Its
cure period is 30 business days, and it stops running while force majeure prevents the borrower from
reporting.

<!-- source: ontology/instrument/examples/facility-cure-period.ttl -->
```turtle
tmpl:on-cure-expiry a ins:OnExpiry , bhv:TriggerDefinition ;
    bhv:triggerKind bhv:ScheduledTrigger ;
    ins:after [ a qnt:Quantity ; qnt:onSpace ex:duration-space ;
                qnt:numericValue "30"^^xsd:decimal ; qnt:inUnit ex:business-day ] ;
    ins:tolledIn tmpl:affected .                      # clause 22.2: time does not run here
```

The expiry is a quantity in a calendar unit, business days. `ins:tolledIn` names the state of
another regime, force majeure, in which the clock is stopped. The lender's power to accelerate is then
**gated** on the default state.

<!-- source: ontology/instrument/examples/facility-cure-period.ttl -->
```turtle
ex:accelerate a ins:Power ;
    ins:boundFrom tmpl:accelerate ; ins:arisesUnder ex:term-23-1 ;
    ins:holder ex:lender-occ ; ins:counterparty ex:borrower-occ ;
    ins:activity ins-voc:DeclareDue ;
    ins:appliesInState tmpl:default .
```

The power is part of the facility's bound meaning throughout, but applies only while the facility
occupies the default state. "Can
the lender accelerate today?" becomes a lookup of the facility's current occupancy, with the
clauses, the breach and the expiry behind it.
[Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/instrument/examples/facility-cure-period.ttl).

### Amendments, and the two clocks

Changing the agreement itself is an amendment, which produces the facility's next version under
chapter 4's rules. The amendment example also shows a pattern data architects know as
**bitemporal** modelling. Each fact has a time it is true from, and a time it was recorded.

<!-- source: ontology/instrument/examples/facility-amendment.ttl -->
```turtle
ex:amendment-1 a ins:Amendment ;
    ins:amends ex:acme-v1 ;
    ins:resultsIn ex:acme-v2 ;
    ins:statedIn wex:letter , wex:confirmation ;
    ins:affectsExisting false ;
    fnd:hasTemporalScope [ a fnd:TemporalScope ; fnd:validFrom "2028-01-01T00:00:00Z"^^xsd:dateTime ] ;
    fnd:hasEvidence [ a fnd:Evidence ;
        fnd:recordedAt "2028-02-03T10:00:00Z"^^xsd:dateTime ; fnd:assertedBy ex:agent-desk ] .
```

The amendment applies from 1 January 2028 but was recorded on 3 February. It needs every party's
assent, and the assents arrive one by one, each with both times.

<!-- source: ontology/instrument/examples/facility-amendment.ttl -->
```turtle
ex:assent-tidewater a ins:Assent ;
    ins:assentBy ex:tidewater-occ ; ins:assentTo ex:acme-v2 ;
    fnd:hasTemporalScope [ a fnd:TemporalScope ; fnd:validFrom "2028-02-12T17:00:00Z"^^xsd:dateTime ] ;
    fnd:hasEvidence [ a fnd:Evidence ;
        fnd:recordedAt "2028-02-14T11:00:00Z"^^xsd:dateTime ; fnd:assertedBy ex:agent-desk ] .
```

Tidewater assented on 12 February, and the desk recorded it two days later. The amendment is agreed
when the last assent it needs exists, on 20 February, and known to be agreed from 21 February, when
that assent was recorded. No "agreed on" date is stored. It is read from the assents, which is
chapter 0's principle again, a judgement evaluated from facts. `ins:affectsExisting false` says the
amendment changes nothing that had already arisen under the first version. [Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/instrument/examples/facility-amendment.ttl).
