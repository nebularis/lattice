<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# What a rig states, layer by layer

**Unit:** `v-rig`, prefix VR ([plan](../plans/v-rig.md), [status](../status/v-rig.md)). **Status:** drafted 2026-11-25, at the maintainer's request, outside any slice. It lists kinds of statement and holds no content. Nothing here is built, and nothing here is decided.

## 1. Why this list

A rig is costly to write and cheap to run. A run can be repeated whenever a layer or a mapping changes, and a rig is written again only when its documents do not state a fact some layer needs. So the list below is of facts, and it is meant to be complete before a rig is next written.

**The test for a row.** A fact is listed where an agreement, a placing record or an event states it, and where the answer to some open design question could turn on it. A rig that states what real documents state survives a change of design, since only the mapping moves. A rig is evidence for a decision and never a specification (the plan's principle for P1), so a row asks for the fact and takes no side on the question it serves.

**What a rig does not state.** A rig records what was agreed and what happened. It holds nothing about what might be placed, how a structure is chosen or what it should cost, as the applied insurance reference's phase 7 plan says of its own modules (P7-1).

**How to read the tables.** *Carried in* says where a rig would state the fact. Front matter is the declared view of a document, and where a row adds the provision's locator the front matter also points at the clause that states it, so the declared view and the blind view can be compared. The last column says where the fact stands today. *Read* means the tracked scheme maps a key for it to a layer in format 1. *A key, not mapped* means rigs of format 1 state the fact under a key and the tracked scheme maps that key to nothing, so the fact stops at the representation. *No key* means the format has nothing to carry the fact. The tracked scheme maps eleven keys, `attachment`, `document`, `documents`, `limit`, `lines`, `name`, `period`, `role`, `share`, `summary` and `title`, and reads `drop_down` and `exhaustion` as readings. An earlier draft of this list marked five more rows as read, which the first run on a rig outside the repository showed to be wrong. *No term* means no layer can hold it yet, so a rig that states it produces a finding, which is the result wanted. The dates and reporting rows are in the [dates sketch](v-rig-dates-periods-and-reporting.md) §3 and are not repeated.

## 2. The facts

### 2.1 Identity, text and time, for Foundation and Wording

| A statement of | Carried in | Serves | Today |
|---|---|---|---|
| an identity for each agreement that outlasts its versions, apart from the identifier of one document | front matter | every layer, and the 90 refusals of the first run on the mini-rig (VR-4's pack) | no key |
| the date of each document, apart from the date its terms take effect | front matter | an amendment that reaches back, LG-Q62 | no term |
| each instant as a date and a time with its zone, or a rule for the instant a bare date means | every file that writes a date | positions that compare across agreements, ES-Q10, and the first run's one inconsistency | no key |
| a reference from one provision to another, and from a provision to a defined word | the body | Wording's cross references, which the first run found none of | no key |
| the form and the edition an agreement is written on | front matter | incorporation by edition | a key, not mapped |

### 2.2 Parties and their capacities, for Party

| A statement of | Carried in | Serves | Today |
|---|---|---|---|
| each party by an identity of its own, the same party named alike in every document it appears in | a list of parties in the programme file, named from front matter | owner kinds, membership by rule (ES-Q4) | no key. The mini-rig names a party by a string |
| the capacity in which each party acts in each agreement | front matter | owner kinds an account admits | read in part, as a role on a line |
| who may act for whom, on which subject, within which bounds | front matter, with the provision's locator | representation, ADR-A130 decision 11 | no key |
| several parties each bound for their own share only, or bound together | front matter | which party a line's account belongs to | no key |

### 2.3 Amounts and units, for Quantification

| A statement of | Carried in | Serves | Today |
|---|---|---|---|
| the unit of every amount, on the amount | wherever an amount is written | the first run, where no quantity states its unit | a key on the programme, not mapped |
| the smallest unit an amount is settled in | the programme file | rounding, a discrete unit's floor | no key |
| what a share is a share of, the limit, the loss or the order | front matter and the programme file | STD-340, signed shares | no key. The mini-rig writes `0.6 x layer_limit` as a string |
| two agreements of one structure in different units, with the rate and the date the terms fix | front matter, with the provision's locator | a draw arrives in its account's unit (ADR-A131's addendum of 2026-11-09), an attachment in one unit above a limit in another | no key |

### 2.4 The agreement and its terms, for Instrument

| A statement of | Carried in | Serves | Today |
|---|---|---|---|
| the period of each agreement, with its first and last instant | front matter | the first run, where no instrument has a period | read on the programme only |
| the sections of an agreement, each with what it covers | front matter, a list of sections, each with its heading's locator | an endpoint narrowed to a section (ADR-A130 decision 4), evaluation units | no key |
| each defined word, with the provision that defines it and what it means | the body, with the defined words listed in front matter | Instrument's 22 refusals in the first run | no key |
| the terms of another document taken as one's own, by edition or as changed from time to time, with any condition on taking a change | front matter, with the provision's locator | ES-Q7 | a key, `follows_form_of`, not mapped, and with no condition |
| a change of terms: the document that states it, its date, the instant it takes effect, each term it changes, and who agreed it for whom | a document of its own or a part of one, with front matter for each change | the supersession, LG-Q59 to LG-Q62, representation | no key |
| where one's own terms prevail over terms taken from another document | front matter, with the provision's locator | a follower that differs from what it follows | no key |
| the law that governs | front matter | a rule outside the terms where they are silent (ADR-A130 decision 3) | a key, not mapped |

### 2.5 What each agreement does alone, for Behaviour

| A statement of | Carried in | Serves | Today |
|---|---|---|---|
| what places a loss within an agreement, for each section | front matter, by section | the dates sketch's `cover-basis` | a key, `trigger`, for the whole agreement, not mapped |
| what makes several losses one, for example a span of hours or one cause | front matter, with the provision's locator | which draws are one request | no key |
| what counts against a limit and what is paid beside it, for example costs | front matter, by limit | purposes, BHL-Q3 | no key |
| an amount the insured bears first, and whether paying it counts towards anything above | front matter, by section | a guard on a balance (BHL-Q3), an account owned by another party (BHL-Q5) | no key |
| what follows where a request is turned away, in whole or in part | front matter, with the provision's locator | BHL-Q1 | no key |

### 2.6 Limits as accounts, for Ledger

Each row is asked of every limit, sublimit and aggregate a document states.

| A statement of | Carried in | Serves | Today |
|---|---|---|---|
| its amount and unit | front matter, by limit | `ldg:statedAmount`, the unit of account | the amount is read, and the unit is not |
| whether it is part of another limit or in addition to it | front matter, by limit | the parent edge, ADR-A131 decision 3 | no key |
| what it is counted for each of, for example each insured, each place or each loss | front matter, by limit | the key dimension | no key |
| the period it runs for, whether it renews, and when its book closes | front matter, by limit | PDD-15, the dates sketch's `aggregate-period` | no key |
| how far it may be restored, by which kinds of credit, how many times and on what condition | front matter, by limit, with the provision's locator | the ceiling, `ldg:restoredBy`, LG-Q61 | no key |
| which purposes it counts where a draw elsewhere names them | front matter, by limit | `ldg:countsPurpose`, MEC-112 | no key |
| how claims that compete for it are settled: the rule, the rounding, where an odd unit goes, what orders the claims, whether two of one rank are allowed, whether a part may stay unplaced and where it goes, whether claims of different purposes may compete | front matter, by limit, with the provision's locator | the merge policy's eleven terms, VR-8's ten questions | no key |
| an amount held back for one rank of claims | front matter, by limit | `held-rank`, MEC-110 | no term |
| whether a later amount below what is drawn is allowed, and what follows | the front matter of the change of terms | `ldg:admitsStatedBelowDrawn` | no key |
| who owns it where several agreements draw on it | the programme file | an account an ensemble owns, BHL-Q5 | no key |

### 2.7 Relations between agreements, for Ensemble

The kinds are those of ADR-A130 decision 3. Ensemble is not built, so every row is *no term* today. The first run on the mini-rig said so, since no layer term relates one instrument to another.

| Kind | A statement of | Carried in | Serves |
|---|---|---|---|
| K1, derivation | the agreement another is made under, and the document whose terms it takes | front matter | incorporation, ES-Q7 |
| K2, dependency | what an agreement waits on in another: the event, how it is read, for example paid by the insurer, paid by anyone or incurred, and the instant it is read at | front matter, with the provision's locator | exhaustion readings, STD-328, the Instrument hook of decision 6 |
| K2, dependency | the agreements beneath, each named with the amount the document believes it has | front matter, a list | ES-Q8, STD-341, a named agreement that is absent or replaced |
| K2, dependency | what follows where an agreement beneath pays less than it states, or cannot pay | front matter, with the provision's locator | a rule outside the terms |
| K2, dependency | whether an agreement above pays sooner where one beneath is reduced and not exhausted | front matter, with the provision's locator | a second reading of the same balance |
| K3, priority | the order in which agreements pay, and the order in which amounts recovered are given back, which may be the reverse | the programme file, and front matter where an agreement states it | rank, credits by kind, MEC-110 |
| K4, portion and share | each line: its share as written, its share as signed or the provision that signs it, whether it stands in full, and the whole the shares are of | the programme file, with each line's own document | signed shares (decision 10), STD-340, the `floor` gap, MEC-111 |
| K5, single agreement | a master and the agreements under it, and the purposes for which they are one | the master's front matter and the programme file | a limit over several agreements |
| K6, shared resource | a limit several agreements draw on, with its owner | the programme file | LG-Q3, PDD-04 |
| K7, contribution | two agreements that each cover one loss, with what each says of other cover | front matter, with the provision's locator | a cycle that stays refused until ES-8 |
| K8, representation | who agrees a change, who agrees a claim and who gives notice for the others, each with its bounds, and what each member keeps for itself | front matter, with the provision's locator | decision 11 |
| membership | the rule by which an agreement belongs, where the terms state one | the programme file | ES-Q4 |
| succession | the agreement a later one replaces, with the act that makes the replacement, and interim cover replaced by an issued policy | the later agreement's front matter | ES-Q9, P7-Q8, STD-342, STD-343 |
| visibility | terms one member agreed that the others may not read | front matter, as a marking on the terms | decision 12 |

### 2.8 The programme and its placing

| A statement of | Carried in | Serves | Today |
|---|---|---|---|
| the structure as placed: each layer with its attachment, its limit and the agreements on it | the programme file | AIR-7.0 | read in part. A layer's number and its position are keys the scheme does not map |
| whether a layer's attachment is the sum of the limits beneath or an amount of its own, and any gap or overlap between them | the programme file | attachment as one fact or two | a key, one flag, not mapped |
| agreements of one structure whose periods differ | front matter of each agreement | an account for each period against a structure that spans them | no key |
| how far each line is bound: offered, written, signed, in force, and from when for each party | the programme file, with the instant of each state | PDD-11 | no key |
| a market's answer to a request, with how far it commits, how exact it is and how complete, each at the scope the market states it | a document of its own kind, with front matter | PRI-35, STD-344 | no key |

### 2.9 Events

| A statement of | Carried in | Serves | Today |
|---|---|---|---|
| the order in which events became known, apart from the instant each took effect | the events file | a recorded and an effective position (STD-330), every backdated case of §3 | no key. The file's order is the only order |
| a loss in its parts, what was paid, what is reserved, by whom and when | the events file | exhaustion by payment against exhaustion by incurred loss | a key for one amount, not mapped |
| a payment by a party other than the insurer of the agreement it counts against | the events file | the readings of K2 | no key |
| an amount recovered, a limit reinstated and an amount returned, each with its kind | the events file | credit kinds, `ldg:restoredBy` | no key |
| the peril, the place and the section a loss falls under | the events file | the first run, where no loss event carries a peril | no key |
| a fact marked as not known, apart from one not stated | any file, as today | the three states of a fact | read |

## 3. Cases that tell the open options apart

A rig that holds these is evidence for each question whichever way it is answered.

| Question | The case |
|---|---|
| LG-Q59 | a credit that takes effect before a change of terms and is recorded after later draws, larger than what was drawn before the change |
| LG-Q60 | a draw paid from a credit that took effect later, then a change of terms in force from an instant between the two |
| LG-Q61 | a limit restorable only to an amount below what it states, under a wider limit, with a credit on the narrower one |
| LG-Q62 | two changes of terms to one limit, the second in force from before the first |
| BHL-Q1 | a request refused whole, and one cut to what is left, each with what the agreement then concludes |
| BHL-Q5 | a loss on one agreement that erodes a limit a programme owns |
| ES-Q7 | a change to an agreement beneath that the one above takes, and one it objects to in time |
| ES-Q8 | a schedule of the agreements beneath that names one since replaced |
| ES-Q10 | two losses on two agreements that draw on one limit, with no stated order between them |
| K2 readings | one loss paid in part by the insured, so the agreement beneath is exhausted on one reading and not on another |
| K3 | a recovery after two layers have paid, given back from the top down |
| K4 | lines written to more than the whole, one marked to stand, and a share no decimal states exactly |
| periods | an agreement above whose period starts three months after the one beneath |
| units | an agreement above in another unit than the one beneath |

## 4. Where a decision in one layer fixes another

Each row is a place where building Ensemble on today's Ledger, or the reverse, settles something by default. The rig rows of §2 keep each of them open.

| Where they meet | Ledger's side | Ensemble's side | Decided? |
|---|---|---|---|
| order | one order for an account, supplied by its owner (LG-Q4) | positions that compare across agreements, so an acyclic graph has one outcome | ES-Q10 is open |
| who owns a limit | an account names one owner, and its owner kinds say who may open it | a shared limit is owned by the ensemble, whose members come and go by rule | BHL-Q5 is open |
| a layer with several lines | one account whose grants are attributed among parties, or an account for each line | a line is a commitment of its own, and its signed share is a judgement | ES-Q11 is open |
| exhaustion | a balance read as recorded, or a reading by effective day that a report declares (STD-328) | a dependant reads a fact, with the position it was produced at | ES-Q12 is open. Which reading an agreement above takes is a term of that agreement |
| a restoration after exhaustion | a credit restores a balance at its recorded position | an agreement above already paid on the fact that the one beneath was exhausted | ES-Q13 is open |
| a change of terms | a supersession, for the accounts of one period, in order (LG-Q62) | a relation's endpoint names an identity or one version (decision 4), and a follower takes a change or objects (ES-Q7) | LG-Q59 to LG-Q62 are open |
| a refusal | a merge refused whole, with one of eight reasons | a fact passed to a dependant is Undetermined until its producer has run | BHL-Q1 is open |
| units | the ledger never converts | a relation may join agreements in different units | ES-Q14 is open |
| periods | an account for each period | members whose periods differ | ES-Q15 is open |
| sections | a purpose debits an account outside the path | an endpoint narrows to a section, which is then an evaluation unit | ES-Q16 is open |
| shares and rounding | a proportion is exact and only a posted amount is rounded (STD-340) | a signed share scales written shares to the order | the `floor` gap |
| who may read | a merge record names every request | a member's terms may be kept from the others (decision 12) | ES-Q17 is open |

Seven rows were raised nowhere before this list. They are ES-Q11 to ES-Q17 of the [Ensemble plan](../plans/ensemble.md) since 2026-11-25, with no option proposed. None needs an answer before a rig is written, since §2 asks for the facts both sides read.

## 5. Questions for the maintainer

**VR-Q15. What the next rig covers.** (a) The agreements, the structure and the events of §2.1 to §2.7 and §2.9, with no placing history. (b) Those and §2.8's placing, the states of each line and the market's answers. (c) Those and a vehicle that takes risk from the structure, as instruments and what they pay. *Leaning (b).* The placing rows are what phase 7's examples need, and they add documents of another kind, which is the costly part to add later. A vehicle is a further set of agreements and can be a rig of its own. Answered 2026-11-26, (b). Decided by the maintainer, who notes there may be no real placing documents to work from. The placing history is then invented, from published market forms and generic premises, as every other part of a rig is.

**VR-Q16. Whether a rig holds agreements from outside insurance.** Ensemble's examples come from lending and construction as well. (a) Insurance only, with the other fields left to the examples ES-0 writes by hand. (b) One small structure from another field in the same rig. *Leaning (a).* The reading restrictions that make a rig costly apply to its sources, and ES-0's examples are invented from generic premises at no such cost. Answered 2026-11-26, (a). Decided by the maintainer. A rig is for checking insurance examples safely and lawfully.

**VR-Q17. How the format carries a fact no layer has a term for.** (a) A key for every row of §2, tracked, so a missing term is an unmapped key and a finding. (b) Keys only for rows a layer can hold, with the rest left in the text of the documents. *Leaning (a).* A fact that is only in the text reaches no finding, so a run cannot tell that the documents state it. Answered 2026-11-26, (a). Decided by the maintainer. The findings a missing term produces by design are listed once, by row, and are not triaged one by one.

**VR-Q18. Whether the recorded order of events is a key.** Today the events file's own order is the only order. (a) Each event states the instant it became known beside the instant it took effect. (b) The file's order stays the recorded order. *Leaning (a).* Every backdated case of §3 depends on the two being apart, and a file's order is lost by any tool that sorts it. Answered 2026-11-26, (a). Decided by the maintainer, since the ledger's open questions LG-Q59 to LG-Q62 all turn on it.

VR-Q12 to VR-Q14 are kept for the slice that points projection P2 at the ledger's kernel.

## 6. Order of work

1. A run of projection P1 on the present rig, which needs no change to anything and says which rows of §2 its documents already state.
2. The maintainer's answers to VR-Q15 to VR-Q18, given on 2026-11-26, and a pass over §2 and §4 with the run's findings beside them.
3. The format's next version, a key for each row kept, drafted on 2026-11-26 in the [keys of format 2](v-rig-format-2-keys.md), with VR-Q20 to VR-Q22 answered the same day, VR-Q24 the next and VR-Q23 open, and planned as VR-10 to VR-12. Format 1 stays readable beside it, and every run record names the format version, since the present rig is kept as a baseline.
4. The answers to ES-Q11 to ES-Q17, each in the brief of the first slice it bears on.
5. The rig written once, to §2 and §3.
