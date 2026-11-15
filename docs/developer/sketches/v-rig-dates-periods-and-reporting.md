<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Competency questions on dates, periods and reporting, for the verification rig

**Unit:** `v-rig`, prefix VR ([plan](../plans/v-rig.md), [status](../status/v-rig.md)). **Status:** sketched 2026-11-13, at the maintainer's request after the ledger's LG-Q26 was decided, for an agent the maintainer assigns. It bears on projection P1, the layer graph and its competency queries. Nothing here is built, and no run of the rig is due until the ledger's remaining design questions are settled, since they may add to it.

## 1. Why these questions

LG-Q26 decided that a reading of a balance by effective day is a derivation a report declares, its value taken from the agreement's clauses, then a document it cites, then a rule the deployment imposes ([balances sketch](ledger-balances-under-post-once.md) §4.9, MEC-107). Whether that sourcing can work depends on two things the rig can show: whether contract documents state a date basis, a reporting arrangement and a way of correcting a figure, and whether the layers have a term to hold each.

A competency question lives in `ontology/v-rig/projection/competency/<layer>.rq` as a `# question <name>: <text>` line and one `SELECT`. A question that returns no row is a finding.

## 2. The questions

"Askable today" means a declared term exists, so the query can be written now. "No term" means the knowledge index found none, so the question cannot be written as a query until a term is decided. The second table is the more useful result, since each row is a gap to confirm against a rig and then to decide. The term searches were made on 2026-11-13 with `mise run graph:ask -- find ... --kind term` and `exists`, and a weak answer there never proves that no term exists.

### 2.1 Askable today

| File | Name | Question | Query body, as a draft |
|---|---|---|---|
| `ledger.rq` | closing | Which account definitions state the recurrence at whose boundaries their book closes? | `?account a ldg:AccountDefinition ; ldg:closingRecurrence ?recurrence .` |
| `instrument.rq` | amendment-effect | Which amendments state when their effect holds? | `?amendment a ins:Amendment ; fnd:hasTemporalScope/fnd:validFrom ?from .` |
| `instrument.rq` | amendment-source | Which amendments name the document that states them? | `?amendment a ins:Amendment ; ins:statedIn ?document .` |
| `foundation.rq` | recorded-and-effective | Which records carry both the time they hold from and the time they were recorded? | to be written against Foundation's shapes, since `fnd:hasTemporalScope` and `fnd:recordedAt` have different domains |

`insurance-common.rq` already asks which loss events state the time they occurred.

### 2.2 No term found, so the question is the finding

| Candidate home | Name | Question | What the index found instead |
|---|---|---|---|
| common insurance, or Instrument | cover-basis | Which sections of cover state the date that places a loss in a period, the date it occurred, the date a claim was made or the date it was notified? | `aeo:triggerBasis`, which is indemnity, parametric or index, a different basis |
| common insurance | retroactive | Which claims-made sections state a retroactive date, or an extended period for reporting? | nothing |
| common insurance, or Behaviour | notified | Which loss events state when they were notified, apart from when they occurred? | `claim-notified`, an occasion in a Behaviour example only |
| Behaviour, or Instrument | reporting | Which agreements oblige a party to report, and state what is reported, to whom, how often and how long after a period ends? | nothing |
| Behaviour, or Instrument | correction | Which agreements state how a reported figure is corrected, by a later correcting entry or by replacing what was reported? | nothing |
| Ledger | aggregate-period | Which account definitions state the period their amount runs over, the agreement's own period or a fixed period of their own? | `ldg:resetRecurrence`, deprecated, and PDD-15 is open on whether a periodic amount is one account or one a period |
| Ledger, or a layer for reports | reading | Which reports declare the reading they show, the day and the known-at recording (MEC-107, STD-329)? | nothing, since no report is modelled yet |
| Instrument | amendment-retrospective | Which amendments take effect before the date of the document that states them? | no term for a document's own date was found |

Each candidate home is a guess for the agent to test against the layers' own scopes ([skill `lattice-architecture`](../../../.claude/skills/lattice-architecture/SKILL.md)). Declaring a term is a modelling decision, presented with its options and never made in passing.

## 3. What a rig must state to answer them

A rig written to exercise attachment, exhaustion and allocation need not say on what date basis its cover applies, what is reported under it or how a reported figure is corrected. Where it is silent, every question above returns nothing, and a run cannot tell "the documents do not say" from "the layers cannot hold it". The lists below name kinds of statement and hold no content. A rig's documents stay outside every repository, as the [plan](../plans/v-rig.md)'s scope says.

### 3.1 In the documents

| A statement of | So the rig can show |
|---|---|
| the date that places a loss in a period, for each section of cover, with one section on an occurrence basis and one on a claims-made basis | that the basis is declared per section and differs within one agreement |
| a retroactive date and an extended period for reporting, on the claims-made section | the two dates beside occurrence and notification |
| the period of the agreement, and an aggregate limit with a period of its own that differs from it | which period an amount runs over |
| an aggregate limit by a narrower scope inside a wider one, for example by place | an account that is part of another, each with its amount |
| a reporting clause: what is reported, to whom, how often, how long after a period ends, and the data specification it follows | the reporting arrangement as a declared thing |
| two reporting arrangements in one agreement, for different sections | that the declaration is per arrangement and never per agreement |
| a correction clause in each of the two forms, a later correcting entry in one arrangement and a replacement of what was reported in the other | the two conventions, of which only the first is a late posting |
| a requirement to report against the aggregate, with its own timing | a report that shows erosion |
| an amendment whose effect starts before its own date, and one whose effect starts after | retrospective and prospective effect |

### 3.2 In the events file

| An event | So the rig can show |
|---|---|
| a loss with the date it occurred and a later date it was notified, the two in different periods | which date the basis picks |
| a loss recorded after a period has closed, taking effect inside the closed period | a late posting |
| a figure reported in one period and corrected in the next | a correction as a later entry |
| a cancellation or adjustment that returns part of an aggregate, dated back | a credit that is late |
| a loss, a reinstatement and a recovery, with the recovery arriving after a further loss | the history of the [balances sketch](ledger-balances-under-post-once.md) §4.8, with one event late |
| an event whose notification date is marked as not known | the unknown state of an input |

### 3.3 In the programme file

Two layers at least, one with an aggregate that has its own period, so an account above another exists.

### 3.4 Beside the content

The keys of a rig are the author's own, so a rig's extension binds each new key to the input it carries (`vrig:InputBinding`). Until a term exists for a row of §2.2, a binding for it has nothing to map to, and the fact stays in the representation and reaches no layer. That is a finding in itself and no fault of the rig.

## 4. What a run would give, and the order of work

1. For §2.1, add the four questions to their files and run the mini-rig, which gives a row count for each and a finding where it is none.
2. For §2.2, read a rig's blind view for the documents that state such a thing and record each as a finding by hand, since nothing can be queried yet.
3. Bring each confirmed gap to the maintainer as a modelling question, with its options and the layer it belongs to.
4. Add the query for each term that is decided.

The result is a list of what contracts say about dates and reports that the layers cannot yet hold, which is what LG-Q26's sourcing needs.

## 5. What this sketch asks for

- An agent to take §4's steps 1 and 2, as a slice of the `v-rig` unit the maintainer names.
- A decision, for each row of §2.2 a rig confirms, on whether a term is declared and where.
- No run of the rig on a private corpus before the ledger's remaining questions are settled.
