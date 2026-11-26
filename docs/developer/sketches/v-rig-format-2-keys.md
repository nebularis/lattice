<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The rig format's next version, key by key

**Unit:** `v-rig`, prefix VR ([plan](../plans/v-rig.md), [status](../status/v-rig.md)). **Status:** drafted 2026-11-26, at the maintainer's request, outside any slice. It names keys and holds no content of any rig. VR-Q20 to VR-Q22 were answered on 2026-11-26, (a) each, and VR-Q23 is open. Nothing here is built.

## 1. What this is

The [list of what a rig states](v-rig-what-a-rig-states.md) names the facts. This sketch gives each fact a key, so that the next rig is written once (the list's order of work, step 3). The maintainer's answers of 2026-11-26 set its bounds. The placing history is in (VR-Q15), a rig holds insurance agreements only (VR-Q16), every row has a key whether or not a layer has a term for it (VR-Q17), and each event states when it became known (VR-Q18).

**What carries over from format 1.** The layout, a manifest that names documents, programme files and an events file. Every key is carried as a fact in one of three states (the plan's principles 3 and 6). Keys are tracked and tokens are not (VR-Q8), so this sketch names no token, and every token written below is an example. Front matter and body stay two views of one document (principle 7). A rig may still add keys of its own, which its extension maps.

**How a key is named.** For the fact a document states, in the word format 1 already uses where it has one, and never for the layer term the key maps to today. The list asks for facts and takes no side on the questions they serve, and a key named for a term would go stale when the term moves.

## 2. Seven rules that hold for every key

| | Rule | Written |
|---|---|---|
| R1 | **A fact is written bare or qualified.** The two forms state one fact, and the second adds what is said about it. Every key of format 1 keeps its meaning and its mapping (VR-Q20) | `limit: 1000000`, or `limit: {value: 1000000, unit: XCD}` |
| R2 | **An amount states its unit**, as the qualifier `unit`. A programme's `currency` stays a fact of the programme and never supplies the unit of an amount | `{value: 250000, unit: XCD}` |
| R3 | **A proportion is written as the document writes it.** A decimal where the document gives a decimal or a percentage, and `numerator` with `denominator` where it gives a fraction. The qualifier `of` names the whole it is a proportion of | `{value: 0.6, of: layer-limit}`, `{numerator: 1, denominator: 3, of: order}` |
| R4 | **An instant is a date and a time with its offset.** Where the document writes a bare date, the rig writes the bare date, and the file's `bare_dates` states the rule the document gives for it. Where the document gives no rule, `bare_dates` is listed as not known | `2027-01-01T00:01:00+00:00`, or `2027-01-01` with `bare_dates: {time: "00:01", zone: an-invented-zone}` |
| R5 | **A fact points at the provision that states it** with the qualifier `stated_in`, a record of the locator's own fields, `section`, `clause` and `row`, with `document` where the provision is in another document | `stated_in: {section: "4", clause: "4.2"}` |
| R6 | **Whatever another key refers to has an `id`**, unique in the rig. A reference is the id | `part_of: aggregate-a` |
| R7 | **A fact stated as not known is listed under `unknown`** on its carrier or its record, as an event lists one in format 1. A key left out is a fact not stated | `unknown: [signed]` |

## 3. The keys

Each table follows a section of the list, in its order. *On* says which file or record holds the key. *Was* says where the key stands in format 1. *Term* names a layer term the key could map to where one is known. An empty Term cell means the term was not looked up for this draft, which the slice that builds the mapping does through the index. *No term* is the list's own finding.

### 3.1 The rig's own files

| Key | On | Value | Was |
|---|---|---|---|
| `format_version` | manifest | `2` | format 1 |
| `parties` | manifest | the path of the parties file (VR-Q21) | new |
| `documents`, `programmes`, `events` | manifest | as format 1 | format 1 |
| `bare_dates` | a document, a programme file, the events file | `time`, `zone`, `stated_in` | new |

### 3.2 Identity, text and time (the list's 2.1)

| Key | On | Value | Was | Term |
|---|---|---|---|---|
| `agreement` | document | the id of the agreement the document belongs to. Several documents of one agreement share it | new | the persistent identity of Foundation |
| `dated` | document | the date of the document | new | no term |
| `effective` | document | the instant its terms take effect | new | |
| `form`, `edition` | document | as format 1 | not mapped | |
| `definitions` | document | a list of `word`, `stated_in` and `scope`, a section's id or nothing for the whole agreement | new | `ins:Definition`, and TD-183 |

A reference from one provision to another stays in the body, where the tool already finds it.

### 3.3 Parties and their capacities (2.2)

| Key | On | Value | Was | Term |
|---|---|---|---|---|
| `parties` | parties file | a list of `id`, `name` and `kind` | new. Format 1 names a party by a string | `pty:Actor` |
| `parties` | document | a list of `party`, `capacity` and `stated_in` | new | `pty:RoleOccupancy`, `pty:inRole` |
| `composition` | document | a token, for example each for its own share or bound together, with `stated_in` | new | `pty:hasCompositionRule` |
| `authorities` | document | a list of `holder`, `for`, `act`, `subject`, `bounds` and `stated_in` | new | Ensemble's K8, not built |
| `reserved` | document | a list of `party`, `matter` and `stated_in`, for what a member keeps for itself | new | Ensemble's K8, not built |

### 3.4 Amounts and units (2.3)

| Key | On | Value | Was | Term |
|---|---|---|---|---|
| `unit` | every amount | a token | on the programme only, not mapped | `qnt:Unit` |
| `units` | programme | a list of `unit` and `smallest`, the smallest amount settled | new | |
| `of` | every proportion | a token or an id, for example the limit, the loss or the order | new | |
| `conversion` | document | a list of `from`, `to`, `rate` or `rate_source`, `fixed_at` and `stated_in` | new | `qnt:Conversion` |

### 3.5 The agreement and its terms (2.4)

| Key | On | Value | Was | Term |
|---|---|---|---|---|
| `period` | document | two instants, with `stated_in` | on the programme only | `fnd:hasTemporalScope` |
| `sections` | document | a list of `id`, `covers` and `stated_in`, the heading's locator | new | `ins:Sectioning` |
| `follows_form_of` | document | as format 1, qualified by `as`, by edition or as changed from time to time, and by `condition`, with `stated_in` | not mapped | incorporation in Instrument |
| `follow_form_exceptions` | document | a list of pointers | not mapped | |
| `own_terms_prevail` | document | a token, with `stated_in` | new | |
| `changes` | the document that states the change | a list of `id`, `agreement`, `dated`, `effective`, `terms`, `agreed_by` and `stated_in`. Each of `terms` names what it changes by id or by key, with the value before and after. Each of `agreed_by` names a `party` and the parties it agreed `for` | new | `ins:Amendment`, `ldg:Supersession` |
| `governing_law` | document | as format 1 | not mapped | |

### 3.6 What each agreement does alone (2.5, and the dates sketch's 3.1)

Each key sits on a record of `sections`, or on the document where the agreement has no sections.

| Key | Value | Was | Term |
|---|---|---|---|
| `trigger` | a token, for example occurrence or claims made, with `stated_in` | for the whole agreement, not mapped | no term (`cover-basis`) |
| `retroactive_date` | an instant | not mapped | no term |
| `extended_reporting` | a length of time, with `stated_in` | new | no term |
| `one_loss` | a token, for example one cause or a span of hours, with `span` and `stated_in` | new | |
| `retention` | an amount, with `counts_towards`, a list of limit ids, and `stated_in` | new | |
| `on_refusal` | a token, for what follows where a request is turned away in whole or in part, with `stated_in` | new | BHL-Q1 is open |
| `reporting` | a list of `id`, `what`, `to`, `every`, `due_within`, `specification`, `correction`, by a later entry or by replacing what was reported, `against`, a limit's id, and `stated_in` | new | no term |

### 3.7 Limits as accounts (2.6)

The agreement's own limit stays `limit`, qualified. Every other limit, sublimit or aggregate is a record of `limits`, a new list on the document. Each key below is a qualifier of `limit` or a key of such a record.

| Key | Value | Term |
|---|---|---|
| `id`, `value`, `unit` | rules R6 and R2 | `ldg:statedAmount`, `ldg:unitOfAccount` |
| `section` | the id of the section it belongs to | |
| `part_of`, `in_addition_to` | a limit's id. One of the two, or neither | `ldg:partOf` |
| `each` | a list of tokens, for example each insured, each place or each loss | `ldg:keyDimension` |
| `period`, `renews`, `closes` | two instants, a token and a token | `ldg:periodRecurrence`, `ldg:resetRecurrence`, `ldg:closingRecurrence` |
| `restoration` | `to`, an amount, `by`, a list of tokens for the kinds of credit, `times`, `condition` and `stated_in` | `ldg:creditCeiling`, `ldg:restoredBy` |
| `counts`, `beside` | lists of tokens, for what counts against the limit and what is paid beside it | `ldg:countsPurpose` |
| `competing` | `rule`, `rounding`, `odd_unit`, `order`, `equal_rank`, `unplaced`, `unplaced_to`, `mixed_purposes` and `stated_in` | `ldg:MergePolicy` and its eleven properties |
| `held_for` | a list of `rank` and an amount | no term |
| `below_drawn` | on a record of `changes`, a token for whether a later amount below what is drawn is allowed and what follows | `ldg:admitsStatedBelowDrawn` |

### 3.8 Relations between agreements (2.7)

Ensemble is not built, so every key here is one a layer has no term for, except where the Term column says otherwise.

| Kind | Key | On | Value | Was |
|---|---|---|---|---|
| K1 | `under` | document | the id of the agreement this one is made under. Term: `ins:boundUnder` | new |
| K1 | `follows_form_of` | document | section 3.5 | not mapped |
| K2 | `exhaustion` | document | as format 1, a reading, qualified by `read_at` and `stated_in` | a reading |
| K2 | `underlying` | document | a list of `value`, an agreement's id, `limit`, the amount the document believes it has, and `stated_in` | a list of ids, not mapped |
| K2 | `underlying_shortfall` | document | a token, for what follows where an agreement beneath pays less than it states or cannot pay, with `stated_in` | new |
| K2 | `drop_down` | document | as format 1, a reading, qualified by `stated_in` | a reading |
| K3 | `payment_order`, `recovery_order` | programme, and a document that states one | a list of agreement ids, with `stated_in` on a document | new |
| K4 | `insurers` | a layer of the programme | section 3.9 | read in part |
| K5 | `one_agreement_for` | the master's document | a list of tokens, the purposes. Each member names the master with `under` | new |
| K6 | `shared_limits` | programme | a list of `limit`, `owner` and `drawn_by`, a list of agreement ids | new |
| K7 | `other_cover` | document | a token, for what the agreement says of other cover, with `stated_in` | new |
| K8 | `authorities`, `reserved` | document | section 3.3 | new |
| membership | `membership` | programme | a token, with `stated_in` | new |
| succession | `replaces` | the later document | the id of the agreement replaced, qualified by `act` and `stated_in` | new |
| visibility | `restricted` | document | a list of `terms`, a pointer, and `readable_by`, a list of party ids | new |

### 3.9 The programme and its placing (2.8)

| Key | On | Value | Was | Term |
|---|---|---|---|---|
| `layers`, `layer`, `position`, `document`, `documents` | programme | as format 1 | read in part | |
| `attachment` | a layer, a document | an amount, qualified by `basis`, the sum of the limits beneath or an amount of its own, and `stated_in` | the value is read | |
| `attachment_chained` | programme | as format 1 | not mapped | |
| `insurers` | a layer | a list of the keys below | format 1 | `pty:GroupMembership` |
| `party` | an insurer | a party's id. Format 1's `name` stays readable | new | `pty:occupiedBy` |
| `role`, `document` | an insurer | as format 1 | read | `pty:inRole` |
| `written`, `signed` | an insurer | a proportion each. Format 1's `share` stays readable | new | `pty:outwardShare` for one of them, and signed shares are Ensemble's |
| `signing` | an insurer | a pointer to the provision that signs the line | new | |
| `to_stand` | an insurer | true or false | new | |
| `states` | an insurer | a list of `state`, for example offered, written, signed or in force, `at`, `recorded_at` and `for`, a list of party ids | new | PDD-11 is open |

A market's answer to a request is a document of its own kind, with these keys beside the ones any document has.

| Key | Value | Term |
|---|---|---|
| `responds_to` | the id of the request or of the layer | |
| `standing` | a list of `aspect`, one of commitment, precision and completeness, `value`, `scope`, the whole response or a key of it, and `stated_in`. An aspect the market does not state is left out, which is the third state of a fact (STD-344) | the programme module, not built |

### 3.10 Events (2.9, and the dates sketch's 3.2)

| Key | Value | Was | Term |
|---|---|---|---|
| `id`, `programme`, `summary`, `facts`, `unknown` | as format 1 | format 1 | |
| `kind` | a token, for example a loss, a payment, a recovery, a reinstatement, a return, a report or a correction | new. Every event is a loss in format 1 | `icm:LossEvent` for one kind |
| `effective_at` | the instant it took effect | a key of `facts`, the rig's own | `ldg:effectivePosition` |
| `recorded_at` | the instant it became known | new. The file's order is the only order | `ldg:recordedPosition` |
| `notified_at` | an instant | the rig's own | no term |
| `agreement`, `section`, `limit` | ids | new | |
| `peril`, `place` | tokens | new | `icm:peril` |
| `parts` | a list of `part`, for example paid or reserved, an amount, `by`, a party's id, and `at` | one amount, not mapped | |
| `credit_kind` | a token, on a recovery, a reinstatement or a return | new | `ldg:creditKind` |
| `corrects` | the id of the event a correction corrects | new | |
| `reported_for` | two instants, the period a report is for | new | no term |

## 4. An invented fragment

Every name and value below is invented for this sketch, in the manner of the synthetic mini-rig.

```yaml
# documents/xs1-001.md, front matter
id: xs1-001
agreement: agr-xs1
kind: policy
dated: 2026-12-18
period: {value: [2027-01-01, 2027-12-31], stated_in: {section: "1", row: "3"}}
bare_dates: {time: "00:01", zone: an-invented-zone, stated_in: {section: "1", row: "3"}}
limit: {id: xs1-limit, value: 2000000, unit: XCD, stated_in: {section: "1", row: "5"}}
limits:
  - id: xs1-costs
    value: 250000
    unit: XCD
    part_of: xs1-limit
    counts: [an-invented-purpose]
    stated_in: {section: "3", clause: "3.4"}
attachment: {value: 1000000, unit: XCD, basis: sum-of-underlying}
underlying:
  - {value: agr-prim, limit: {value: 1000000, unit: XCD}, stated_in: {section: "7", row: "1"}}
exhaustion: {value: payment-by-insurer, read_at: date-of-payment, stated_in: {section: "2", clause: "2.1"}}
unknown: [governing_law]
```

```yaml
# programmes/prog-001.yaml, one insurer of one layer
- party: insurer-three
  role: lead
  document: xs2-001
  written: {numerator: 2, denominator: 3, of: order}
  signed: {value: 0.6, of: layer-limit}
  to_stand: false
  states:
    - {state: written, at: 2026-12-01T10:00:00+00:00, recorded_at: 2026-12-01T10:00:00+00:00}
    - {state: signed, at: 2026-12-15T16:30:00+00:00, recorded_at: 2026-12-16T09:00:00+00:00}
```

```yaml
# events.yaml, a recovery that took effect before it became known
- id: ev-004
  kind: recovery
  programme: prog-001
  agreement: agr-prim
  limit: prim-limit
  effective_at: 2027-05-02T00:00:00+00:00
  recorded_at: 2027-09-30T12:00:00+00:00
  credit_kind: recovery-from-a-third-party
  parts:
    - {part: paid, value: 150000, unit: XCD, by: third-party-one, at: 2027-09-28T00:00:00+00:00}
```

## 5. What the tool, the scheme and the module owe

None of it is built. The lifter already carries a nested mapping as a record with a fact for each key, so most of format 2 needs a mapping row and no code (principle 6).

| What | Where | Size |
|---|---|---|
| the tool accepts `format_version: 2`, and the run record names it | `rig.py` | one line |
| rule R1, a fact written `{value: ...}` is the fact its bare form states, with qualifiers | `lift.py` | small, and VR-Q20 |
| rule R7, `unknown` on every carrier and record | `lift.py` | small |
| the parties file | `rig.py` | small, and VR-Q21 |
| a party declared for the rig carried in the representation, which has a carrier for a document, a programme and an event and none for a party | the module and `lift.py` | VR-Q23 |
| an id of a party, an agreement, a limit, a section or an event resolves, as the id of a document does today | `lift.py` | small |
| rule R5, a pointer resolves to the body node at that locator, and one that resolves to nothing is an unresolved reference | `lift.py` | small |
| the keys of format 2 declared once, each with the fact it carries in generic words, so a run tells a key with no term from a key it does not know | the scheme and one property of the module | VR-Q22 |
| a mapping row for each key whose Term cell names a term | the tracked scheme | the larger part |
| a synthetic rig of format 2 beside the mini-rig, which stays as it is for the tests of format 1, holding the fourteen cases of the list's section 3 in small | the tool's tests | the largest part |

The competency questions do not change. A question that returns no row on a rig of format 1 because the format has no key for the fact can return one.

## 6. Questions for the maintainer

**VR-Q20. How a fact gains qualifiers.** A limit needs its unit and its provision, and format 1 writes it as a bare number that the scheme maps. (a) Rule R1, the lifter reads `{value: ...}` as the same fact with qualifiers. One mapping row serves both forms, and a rig of format 1 is a rig of format 2 with the version changed. It costs a rule in the lifter, and one reserved key, `value`. (b) No rule in the lifter. A qualified fact is a record, and the scheme reads it by a path, so each key that may be written both ways has two mapping rows. (c) Format 2 forbids the bare form of the keys that take qualifiers. One row each, a second tracked scheme, and the two formats share only their names. *Leaning (a).* The present rig stays a baseline at format 1, and under (a) its keys and the next rig's are the same keys, so two runs compare key by key. Answered 2026-11-26, (a), now the addendum of 2026-11-26 to [ADR-A153](../../architecture/decisions/ADR-A153-verification-rig-module.md). Decided by the maintainer. The module's constraint on a fact's three states already admits a value beside an item, as its shape is written, so the qualifiers are carried as a record on the fact. The slice that builds it shows that with an example graph first.

**VR-Q21. Where parties are declared.** (a) One file for the rig, named by the manifest, so a party in two programmes is one party. A small change to the reader. (b) A list in each programme file, with no change to the reader, and a party in two programmes declared twice under one id. *Leaning (a).* The rows on who owns a limit and whose a line is turn on one party being one node. Answered 2026-11-26, (a), now the addendum of 2026-11-26 to ADR-A153. Decided by the maintainer. The question put the cost as a small change to the reader and left out the representation's side, which is VR-Q23.

**VR-Q22. Where the keys of format 2 are declared.** The answer to VR-Q17 has the findings a missing term produces listed once, by row, which the tool can do only if it knows which keys the format has. (a) In the tracked scheme, each key declared with the row of the list it carries, as the scheme declares its reading keys today. A run then reports three things apart: a key mapped, a key of the format with no term, and a key the format does not know. It adds one property to the module, which is an addendum to its decision record and moves its version at the merge. (b) Nowhere. Every key without a mapping stays an unmapped key, and the rig's owner tells the two apart by this sketch. *Leaning (a).* The second kind is expected by design and the third is the one worth a reader's time. Answered 2026-11-26, (a), now the addendum of 2026-11-26 to ADR-A153. Decided by the maintainer. One correction to the question as it was put. The tracked scheme is a published document and cannot point at a row of a working document, so a key is declared with a statement of the fact it carries, in generic words, and the list keeps its rows to itself.

**VR-Q23. How a party declared for the rig is carried in the representation.** The module has a carrier for a document, a programme and an event, each with the id the rig gives it, and a record for whatever a fact holds. A party declared once for the rig is none of these. (a) A class for a party, a carrier with the rig's id for it, as an event is. One class and one generic word, and the module's version moves with the property VR-Q22 adds. (b) One class for anything a rig declares at its own level, with the kind as a token, so that a later file of the same sort, for example the units a rig settles in, adds no class. It costs a token that a mapping must read before it knows what it holds. (c) No carrier of its own. The lifter copies each party into the programmes that name it, as a record, which needs no class and gives back what VR-Q21 (a) was chosen to avoid, one party as several nodes. *Leaning (a).* Party is a word as generic as programme, a second file of the sort is a guess today, and (b) can still replace (a) before the module's first release that carries either.

## 7. Order of work

1. The maintainer's answers to VR-Q20 to VR-Q22, given on 2026-11-26, and to VR-Q23.
2. This draft goes to the rig's owner through the maintainer, who may ask for a key (the [protocol](../notes/rig-run-protocol.md), section 3).
3. What section 5 lists is built as VR-10 to VR-12 of the [plan](../plans/v-rig.md), with the synthetic rig of format 2 begun first.
4. The rig is written once, to the list and to these keys.
