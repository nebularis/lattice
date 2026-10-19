<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Consent, groups and exercise

**Unit:** [`computable-contract-substrate`](../plans/computable-contract-substrate.md), slices C9b1 to
C9b4 (replacing the first C9b brief).
**Status:** decided 2026-10-09, from our own paper and a review of it
(§6). §1 moves into the Instrument README once the slices land.
**Reads with:** the [CCS sketch](computable-contract-substrate.md) §5.3 and §5.8, the
[change materiality sketch](change-materiality.md), the Instrument README §6.3, §15.1 and §17, ADR-A104
and its addenda, ADR-A106, ADR-A105 (deemings, not yet drafted, held question HQ-6).

The first C9b brief asked what a consent should name and where a group's threshold is stated.
Underneath those questions is a deeper one: what kind of thing consent is in law. Answered first, most
of the brief's constructs turn out to be things the model already has, seen from another angle, and
what is new is small.

## 1. What the law says consent is

### 1.1 Consent and assent are declarations of will

A declaration of will is an act whose legal effect is the effect the actor intends. English law has no
single word for the family, but uses the idea throughout. Its members differ by what they are
directed at:

| Act | Directed at | Legal effect | Example |
|---|---|---|---|
| **assent** | terms | the actor becomes bound by them | signing a facility, accepting an offer |
| **consent**, **approval** | another's proposed act | the act becomes permitted or effective | "shall not assign without the Licensor's consent" |
| **instruction**, **direction** | an agent's conduct | the agent comes under a duty, or gains authority | "the Agent shall, if directed by the Majority Lenders, ..." |
| **waiver** | one's own right | the right is not enforced, for a case or for good | "the Majority Lenders may waive any Default" |
| **objection**, **veto** | another's proposal | the proposal fails, or a deemed consent does not arise | "unless any Lender objects within 10 Business Days" |
| **ratification** | an act already done | the act is treated as authorised from the start | approval of a settlement already made |
| **withdrawal** | one's own earlier declaration | the declaration ceases to count, where the contract allows | revoking consent before the deadline |

**A dissenting lender is bound by a Majority Lenders amendment without assenting to it.** It is bound
because, when it first assented to the facility, it agreed to the amendment clause, which is a power.
The new version binds everyone through the exercise of that power, not through anyone's assent. If
consents under a power were recorded as assents to the resulting version, the data would say the
parties bound are those who assented, which under a power is false. So the two are siblings:

- **assent** is directed at a version. Formation and amendment by agreement read it (C9a)
- **consent** is directed at a proposal. Exercises under a power read it

Both are kinds of one class, the declaration.

### 1.2 In Hohfeld's terms, consent is the exercise of a power

Where "X may assign with Z's consent", X has a disability, since X cannot assign effectively alone. Z
has a power, because by consenting or not, Z changes X's legal position. Where the restriction is a
prohibition, Z's consent creates a permission. Where it is a condition on effect, Z's consent completes
X's power. Refusal is Z not exercising its power. An objection under "unless any Lender objects" is the
exercise of a different power, a veto.

So **a consent requirement needs no new kind of relation.** It is a power held by the consenter, with
other relations arising on its exercise, and the model already has `ins:Power` and
`ins:arisesOnExerciseOf`.

"Not to be unreasonably withheld" is an obligation on the consenter that qualifies how it uses its
power. In leases governed by English law, the Landlord and Tenant Act 1988 implies that obligation by
statute, with a duty to decide within a reasonable time. Both are implied terms, which `ins:impliedBy`
already covers. Whether a refusal was unreasonable is a determination by whoever the contract or the
court names, an outcome the evaluator records, never something stated meaning computes.

Implied terms are why the model is open-world. A drafter never gathers every legal influence into the
contract, and a closed-world model would demand it. A place on which implication can hang lets the
model reason about the effect of legislation on terms, express "whether express or implied by" wording,
and record rulings that change how implied terms are read in the jurisdictions a deployment serves.

### 1.3 A group's power is held by a defined word

Contracts draft a group's threshold once, as a definition, and use it across powers. In a loan
facility, "Majority Lenders" is "a Lender or Lenders whose Commitments aggregate more than 66⅔% of the
Total Commitments", and acceleration, waiver, amendment, instructions to the Agent and the release of
security all use it. Likewise "Super Majority Lenders", "all the Lenders" and "each affected Lender"
are party words, a bond trust deed defines "Extraordinary Resolution", and the London market's General
Underwriters Agreement defines "Slip Leader" and "Agreement Parties".

So **the threshold is part of the meaning of the word that holds the power.** The word does not name a
fixed group. It says which groups qualify to act, and the particular set is resolved for each exercise
from whoever has actually consented.

The model already has the pattern. A contingent party is resolved per occasion
(`ins:PartyResolution`, README §17.2), a word's meaning is replaced at binding (§15.1), and a word that
means several parties says how they act together with `ins:actingRule` (§17.3). "Majority Lenders"
means the Lenders, the universe, and its acting rule is a **qualifying rule** (§2.2).

This inverts the brief's question. The brief asked who must consent. The word asks whether those who
consented qualify, which is the question the law asks, is monotone in the facts as they arrive, and
needs nothing beyond the facts and the definition. It also explains why CC-D10 is right that "the
Lenders may" alone is Undetermined. With no definition, the words do not say whether one lender, all of
them or a majority qualifies.

### 1.4 Four questions every decision rule answers

Across loan, bond and insurance practice, a rule for collective consent answers four questions:

1. **Who counts, the universe.** The Lenders as they stand at a reference time, less exclusions: a
   Defaulting Lender is disenfranchised, lenders affiliated with the sponsor are excluded, and under
   "snooze you lose" a lender that has not replied by the deadline leaves both the numerator and the
   denominator.
2. **What counts as yes.** An express consent, a deemed consent (silence for 10 Business Days unless
   there is an objection), a consent given through an agent, or a member's last declaration where
   withdrawal is allowed.
3. **When.** The window in which consent may be given, anchored at the request, and the reference time
   at which weights are measured: the request date, a record date, or the decision.
4. **How much.** Every member of the universe (unanimity, each affected lender), some member ("any
   Lender may"), no member objecting (a veto), or an aggregate of a measure over the consenters
   compared with a threshold. The threshold is absolute, or relative to an aggregate over a
   denominator set: total commitments, votes cast at a quorate meeting, or those who responded.
   Combinations, such as a majority in Tranche A and in Tranche B, combine these.

The first three answers to "how much" are quantifiers. The last is arithmetic.

### 1.5 Five things to keep apart

| Thing | What it is | Example | Where it lives |
|---|---|---|---|
| **proposal** | what is put to the parties | a request to waive a covenant breach, an MTA request | an Instrument fact |
| **declaration** | one party's assent, consent, objection or withdrawal | Lender B consents on 20 February | an Instrument fact |
| **decision** | whether the declarations meet the rule | Majority Lenders met on 20 February | evaluated, never authored |
| **exercise** | the act that purports to have legal effect, made pursuant to the proposal | the Agent's acceleration notice | an Instrument fact, as purported |
| **effect** | whether the exercise changed anyone's position (law I10) | the loans are due | evaluated, recorded by the runtime |

Two of the five are judgements. Authoring either would let the data disagree with the rule that decides
it, which is why C9a reads an amendment's agreed time from its assents, and why whether an exercise
took effect is a finding.

## 2. The model, layer by layer

### 2.1 Instrument: the legal acts tier

C9a began a third tier beside stated and bound meaning: the acts the parties did, bitemporal and
evidence-bearing, written by any application. It becomes explicit, in its own document under ADR-A120,
so a consumer that only states meaning never imports a consent:

```text
ins:LegalAct          an act of a party that the instrument makes something turn on
  ins:Declaration     an act of will, whose effect is the effect intended
    ins:Assent        to a version (C9a)
    ins:Consent       to a proposal
    ins:Objection     against a proposal
    ins:Withdrawal    of an earlier declaration (ins:withdraws)
  ins:Exercise        a purported exercise of a bound power (ins:exercises)

ins:Proposal          a matter put to parties (ins:proposedBy), its valid time when made
  ins:Amendment ⊑ ins:Proposal     C9a's amendment already exists from its proposal

ins:pursuantTo        an act made in reliance on a proposal or a consent
```

Every act has a valid time and evidence, as an assent does. An exercise records only that the act was
done, and its effect is evaluated. An `ins:OnExercise` trigger fires on an exercise the evaluator finds
effective, Behaviour's stimulus for it is `prov:wasDerivedFrom` the exercise, and `bhv:ExerciseRecord`
becomes what it is, the evaluator's finding about an exercise (`bhv:tookEffect`, `bhv:reasonNotTaken`).
`bhv:exercised` has no range, so Behaviour still names nothing above it. `bhv:AcceptanceRecord`
becomes the evaluator's record that an assent was relied on.

**Instrument records what the parties did. Behaviour records what the evaluator concluded and
executed.**

**The tier holds juristic acts only** (decided, §6). Declarations of will, exercises of powers and
notices with legal effect, such as a notice of loss, are juristic acts and belong here. Acts of
performance, such as a payment or a delivery, are real acts, not declarations of will. They stay
performance facts the evaluator reads (`bhv:ActRecord` today).

One exercise of a forty-lender power costs one proposal, up to forty declarations (the information any
rule needs anyway) and one exercise, with no regimes, occupancies or bound nodes.

### 2.2 Instrument: qualifying rules

"Majority Lenders" is a party word, so a `pty:Role` on stated meaning. Its definition means the
Lenders, and its acting rule (`ins:actingRule`) is a **qualifying rule** (`ins:QualifyingRule`,
decided, §6), which says which sets of them qualify to act:

```turtle
tmpl:def-majority-lenders a ins:Definition , ins:Template ;
    ins:arisesUnder tmpl:term-1-1 ;
    ins:defines tmpl:MajorityLenders ;            # a pty:Role
    ins:means tmpl:Lender ;                       # the universe
    ins:actingRule tmpl:majority-lenders-rule .

tmpl:majority-lenders-rule a ins:QualifyingRule , ins:Template ;
    ins:excluding tmpl:is-defaulting-lender ;     # a condition on each member
    ins:measuredAt ins-voc:Proposed ;             # the reference time, a context role
    ins:qualifiedBy tmpl:more-than-two-thirds .   # a condition on the set (§2.3)

tmpl:accelerate-direction a ins:Power , ins:Template ;
    ins:holder tmpl:MajorityLenders ;             # the word, so one definition serves every power
    ins:counterparty tmpl:Agent ;
    ins:activity ins-voc:Direct ;
    ins:window tmpl:within-30-days-of-request .   # anchored at ins-voc:Proposed
```

The names other than `ins:QualifyingRule` are illustrative, for C9b4's brief.

A liability rule (`pty:EachForOwnShare`, `pty:EachForWhole`) and a qualifying rule are both acting
rules, answering how several parties act together, the first for duties and the second for powers. The
remaining group behaviours of HQ-5 become further acting rules.

**The universe and its measure are resolved at a reference time, not read from the version in force.**
Commitments change by transfer certificate, cancellation and prepayment, and the Lenders change by
novation, none of which amends the agreement. An insurer's signed line changes by signing down. Both are
facts at the reference time. The **reference time is stated once, by the word**, as a context role: the proposal's
date, a record date, or the decision. The proposal, or the meeting, supplies that role's value
(decided, §6).

**Joint and several powers are a separate axis from liability.** For a power, "jointly" means all must
act together, and "severally" means each may act alone for its own part, as with each finance party's
separate rights under a facility. A several power needs no forty copies: one bound power, with an
acting rule of each separately, is evaluated per acting member.

Two laws need restating. Law I13 says bound meaning names occupancies, groups and values, and a power
held by a qualifying word keeps an evaluation-time deferral (§2.3) in bound meaning, the first one.
Law I11 fixes a relation's parties when its occasion arises, and for such a power the acting members
are resolved at each exercise's reference time.

### 2.3 Eligibility: quantifiers and deferred values, with no arithmetic

Eligibility is a data layer, not an algorithm. It may say "every member", "some member" or "no member"
of a set, but never counts or sums. Counting, summing and forcing deferred values are the evaluator's,
and the layer that states legal meaning must not depend on a runtime.

**Quantifiers.** `elg:SomeValue` and `elg:EveryValue` are already "some" and "every" over the values a
path reaches, and "no member" is a negated "some" (law L16). What is missing is correlation. "Every
member of the universe has consented to this proposal" relates two sets reached from one case, the
proposal: the universe (proposal, power, holder word, members at the reference time) and the consenters
(proposal, consent, member). A per-value condition cannot refer back to the proposal. The smallest
declarative addition is a **set comparison** between two paths from the case:

| Comparison | Reads | Permitted | Denied | Undetermined |
|---|---|---|---|---|
| `elg:Subset` (A ⊆ B) | every member consented | every member of A is found in B | some member of A is closed out of B, by refusal or by the window closing under a closure the contract licenses | otherwise |
| `elg:Intersects` | some member did | a common member is found | the window closed with none | otherwise |
| `elg:Disjoint` | no member objected | the window closed with none | a common member is found | otherwise |

These need no counting, keep strong Kleene readings (L15), and keep a single case (law I4). Turning an
absence into Denied, or into Permitted for `elg:Disjoint`, needs a closure the contract licenses, which
is HQ-6's (ADR-A105). The same closure covers deemed consent and "snooze you lose".

**Deferred values.** The Instrument README already calls a defined word "a thunk binding forces"
(§15.1). There are two kinds of deferral, kept apart:

| | Binding-time | Evaluation-time |
|---|---|---|
| example | `ins:valueFrom` a variable: the 66⅔% from the schedule | the consenters' share of the Total Commitments |
| forced by | the instantiator | the evaluator, per exercise, at its reference time |
| in bound meaning | never (law I13, `ins:BoundNamesValuesShape`) | yes, by design, carrying its reference time |
| unforced | reported, not generated | `Undetermined`, with the reason |

An evaluation-time deferral declares how a value will be obtained, which Eligibility holds and never
computes. An `elg:EvidenceBinding` is already one, a candidate obtained along a path. The new case is a
candidate obtained by aggregating along a path:

```turtle
tmpl:more-than-two-thirds a elg:IntervalCondition ;
    elg:requiredRangeSet tmpl:above-two-thirds .      # (0.6667, 1], its bound from a variable

tmpl:commitment-share a elg:AggregateBinding ;        # declared here, computed by the evaluator
    elg:bindsCondition tmpl:more-than-two-thirds ;
    elg:subjectClass ins:Proposal ;
    elg:over tmpl:path-to-qualifying-consenters ;     # the numerator set
    elg:relativeTo tmpl:path-to-universe ;            # the denominator set
    elg:measure tmpl:Commitment ;                     # a word, its value per member
    elg:aggregation qnt:Sum .                         # its legitimacy declared by Quantification (§2.4)
```

The condition states how the outcome will be read, as an interval. The evaluator forces the value, and
until it does, or if any member's weight is missing, the decision is Undetermined. Eligibility owns the
paths, and Quantification, below it, owns what it means to add values.

### 2.4 Quantification: which values may be added

Measurement theory has the distinction ready-made. An **extensive** quantity is additive: commitments
in one currency, principal outstanding, signed lines on one order. An **intensive** quantity is not:
ratings, ratios, rates, and percentages of different bases. Value spaces declare which they are, and a
proportion declares its base:

- a written line is a percentage of the order
- a share of the whole is the signed line times the order, which is multiplicative, not additive
- a commitment in a multicurrency facility is additive only after conversion to the base currency at a
  stated date (ADR-A94's conversion context)

The rules follow. `qnt:Sum` over a space not declared extensive is a design-time violation. `qnt:Sum`
over values in mixed units or bases with no conversion is Undetermined at runtime. `qnt:Count` is the
sum of a unit measure, so voting by head, such as the Agreement Parties or a meeting's quorum, needs
nothing more.

### 2.5 Party: shares become measures

`pty:outwardShare` has four problems. It holds one value per membership, where a subscription line
needs several (the written line, the signed line, the share of the order, the share of the whole). Its
meaning is unstated (liability, benefit or votes). Its base is implicit. And it is fixed per membership
version, where the real values change by transfer and signing down, which are facts, not versions.
`pty:inwardShare` shares the first three.

Every per-member value becomes a **measure word**, whose meaning is a value per member, from a table on
stated meaning (`wrd:forEntry`) or deferred to facts at the reference time, with its base and
additivity declared by Quantification. The weight a qualifying rule reads is such a word, the only kind
that can carry a base and change over time. Party's composition rules stay, for liability only, and
read a measure word rather than a share property.

**Removal is tracked** (decided, §6). C9b4 narrows both properties' stated meaning, marks them
deprecated, and adds a warning shape that reports every use. Slice C16c removes them, and is required
before the CCS epic closes.

### 2.6 Behaviour: unchanged, and lighter

Behaviour keeps state machines, occupancies, stimuli and the evaluator's records. Nothing about consent
becomes a Behaviour state, and there are no regimes per exercise (§3). Behaviour is an abstract state
machine definition and tracking tool that applied ontologies use, and that deployments may implement
differently by market or jurisdiction, so outside a domain ontology its constructs are rarely named
directly.

## 3. No regime per exercise

Instrument README §4.2.13 justifies a regime gate over arising and ending on three grounds: situations
recur, they are shared, and they are not cases. A proposal's life is one-way, pending then decided or
lapsed, and never recurs. So by the README's own test, arising, ending and windows suffice:

| Clause | Modelled as |
|---|---|
| "consents must be given within 30 days of the request, or the request lapses" | `ins:window` on the consenting power, anchored at a context role `ins-voc:Proposed`. Lapse is the window closing (§13.3) |
| "a Lender that has not replied within 10 Business Days is disregarded" | an exclusion from the universe, licensed as a closure at the deadline |
| "deemed to consent unless it objects within 10 days" | an `ins:Deeming` over an absence, with a window (ADR-A105) |
| "notify Reinsurers of any loss within 14 days" | an obligation with a due range |
| "while a request is pending, the Borrower shall not ..." | a condition over facts: a proposal exists, is undecided, and its window is open |

"Pending", "decided" and "lapsed" are outcomes the evaluator derives, never stored states.

## 4. The hard examples

### 4.1 Acceleration under a loan facility

> "If an Event of Default is continuing, the Agent may, and shall if so directed by the Majority
> Lenders, by notice to the Company declare all Loans due."

Three relations: the Agent's power to accelerate, gated by the default state, which the model already
has, the Majority Lenders' power to direct the Agent, held by the word, and the Agent's obligation to
accelerate, arising on an effective direction (`ins:arisesOnExerciseOf`). The facts are the direction
request (a proposal), the lenders' consents, the direction itself (an exercise, pursuant to the
request) and the Agent's notice (a second exercise).

At runtime, the evaluator resolves the consenters at the reference time and drops any Defaulting
Lender, forces their share of the Total Commitments, and reads it against the interval (66⅔%, 1]. With
70%, the direction takes effect, the Agent's obligation arises, and the Agent's notice accelerates the
loans. Without a definition of "Majority Lenders", the direction stays Undetermined, as CC-D10 intends.
The example includes a transfer of commitments between the request and the decision, read at the
reference time.

### 4.2 Insurance: changes to a subscribed policy

Under the General Underwriters Agreement, a change to a subscribed policy is agreed by the Slip Leader
alone, by the Slip Leader with the Agreement Parties, or by all underwriters, by category. Each category
is a power to amend whose holder is a word. The Slip Leader alone is a single holder, needing no group
and no delegation, and the followers are bound because they agreed the GUA, as dissenting lenders are.
Agreement Parties are counted by head, not by line. "All underwriters" is `elg:Subset` of the
subscribing insurers. Which category applies is the change's grade, C9d's.

Weight must be a word with a base. Per member it carries the written line and the signed line, each a
percentage of the order, and the share of the whole, the signed line times the order. Each serves a
different purpose: liability for the signed line, and nothing at all when voting is by head. Lloyd's
claims scheme, with a single claims agreement party, a leader and a second, has the same shape.

### 4.3 Reinsurance: a claims co-operation clause

The first brief asked whether an assent may name an exercise. The law says neither assent nor a group
is involved.

- Under "follow the settlements", the reinsured's settlement with its insured fixes the reinsurer's
  liability, provided it was made honestly and in a proper and businesslike way (*Insurance Co of
  Africa v SCOR*, 1985).
- A claims co-operation clause that is a condition precedent prevents the liability arising at all
  unless the reinsurer approved the settlement (*Scor v Eras (No 2)*, 1995).
- The reinsurer must not withhold approval arbitrarily, an implied term (*Gan v Tai Ping (No 2)*,
  [2001] EWCA Civ 1047).

In the model, the reinsured's settlement is the exercise of its power to settle, with the claim as its
case. The reinsurer's approval is the exercise of the reinsurer's power to approve, for that claim. The
settlement is made `ins:pursuantTo` the approval. The reinsurer's obligation to indemnify arises on the
settlement, and its scope is the claims whose settlement was made pursuant to an effective approval, an
ordinary evidence path from the claim. Validating the acts checks that an approval precedes what relies
on it. The implied term is an obligation on the reinsurer, `ins:impliedBy` the case, and whether a
refusal was arbitrary is a determination. The 14 days in a claims co-operation clause usually bind the
reinsured's notice of loss, a due range, not a window for consent.

Consent here is one party exercising a power, directed at a proposed act under another instrument, the
direct policy. No group, threshold, regime or widening of `ins:assentTo` is needed. Two things are worth
recording: the condition precedent reading, an obligation that does not arise without the approval as
against a promissory term whose breach gives damages (`ins:classification` names the class, but the
scope does the work), and `ins:pursuantTo` as how a "with consent" act refers to its consent.

### 4.4 A test of generality: a bondholder Extraordinary Resolution

An Extraordinary Resolution passes by 75% of votes cast at a meeting where a quorum, a count, is
present, or by a written resolution of 75% of the principal outstanding. That is two qualifying
conditions, combined with `elg:AnySufficient`, with different denominators and a count. If the design
states this without new machinery, it is general enough.

## 5. Where this departs from the first C9b brief

1. The threshold lives in a definition's acting rule, not on the power.
2. Consent is a sibling of assent, not a wider assent.
3. `ins:Exercise` is the purported act and effect is evaluated. `ins:Proposal` generalises C9a's
   amendment. Behaviour's exercise and acceptance records become findings.
4. Weights are measure words with declared bases and additivity, resolved at a reference time from
   facts, not from the version in force. Party's shares are deprecated, then removed.
5. Eligibility gains set comparisons and aggregate bindings, and evaluates neither. The two kinds of
   deferral are named and kept apart.
6. No regime per exercise.
7. Instrument's acts get their own document.

The weight moves out of Instrument and into small, reusable pieces in Eligibility and Quantification.
C9d's selection by grade becomes another member condition, and HQ-5's "any one may act" an
`elg:Intersects` rather than a slice of its own.

## 6. Decisions (2026-10-09)

| # | Decision |
|---|---|
| 1 | "Majority Lenders" and its kind are definitions whose acting rule is a qualifying rule, `ins:QualifyingRule`. "Requisite" is avoided as lending-market vocabulary |
| 2 | Slices: C9b1 legal acts, C9b2 additivity, HQ-6 deemings, C9b3 set comparisons and aggregate bindings, C9b4 qualifying rules, then C9d materiality and C9c incorporation. Before C9b3, the formal-methods epic's Eligibility work is completed on its own branch and merged |
| 3 | Party's shares are narrowed and deprecated in C9b4, reported by a warning shape at every use, and removed in C16c, required before the epic closes |
| 4 | The acts tier holds juristic acts: declarations, exercises and notices with legal effect. Real acts of performance stay performance facts |
| 5 | The Quantification cascade is accepted |
| 6 | The reference time is stated once, by the word, as a context role whose value the proposal or meeting supplies. That covers a facility's request date and a bond's record date in one place |
| 7 | Withdrawal has no substrate default. The contract states it, or a deployment's evaluation profile does, since the rule differs between markets: a lender's consent is usually revocable until the decision, and a written line binds when it is written |

