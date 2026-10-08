<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C9a, amendments and taking effect

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c9a-amendments`, created by the human from `main`.
Commits are the human's, examples first (ADR-A-C2), and the change is merged into `main` before its
release tags are created
**Plan:** [CCS plan](../plans/computable-contract-substrate.md), C9 in detail
**Decisions:** ADR-A104 decisions 4 and 11 and its addenda, ADR-A106, ADR-A112 and its references
by identity addendum. C9-Q1, C9-Q2 (choices 0, 1 and 2), C9-Q5, C9-Q6, as answered on 2026-10-07
and 2026-10-08

## Invariant

What an instrument means changes only by an amendment, recorded with when it was proposed, when it
takes effect and where it is stated, and agreed only when the assents it needs exist, whatever order
those facts arrive in. Each version keeps the meaning it was agreed with. An instrument whose effect
waits on its parties' assents is in no state that gives effect until they exist, and each party that
assents separately is bound from its own assent. Behaviour holds the instrument's states, never the
assents.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| C9a-01 | Instrument's spec / parsed / `0.15.0`, with `ins:Amendment`, `ins:amends`, `ins:resultsIn`, `ins:affectsExisting`, `ins:statedIn`, `ins:Assent`, `ins:begins` and `ins:OnAcceptance`, each stating its subject and value | L1 | + |
| C9a-02 | every Instrument and Wording example / every layer's shapes / conform | L1 | + |
| C9a-03 | the facility's amendment / its text changes, read through `ins:statedIn` / exactly the letter's three and the confirmation's one | L1 | + |
| C9a-04 | an amendment by agreement with every party's assent but one, then with all / agreement read from the assents / not agreed, then agreed at the valid time of the last assent | L1 | + − |
| C9a-05 | the events in any order: an amendment recorded before its assents, and effective before both / shapes and the agreement reading / conform, and the same agreed time whatever order the facts were added | L1 | + |
| C9a-06 | two agreed amendments of one version / shapes / reported. Two pending proposals of one version / conform. No amendment of a version / conform (the count at zero) | L1 | − + |
| C9a-07 | an amendment taking effect before the amendment that made the version it amends / shapes / a warning naming the overtaken window | L1 | − |
| C9a-08 | an amendment that affects existing occasions and replaces a stated relation with no `prov:wasRevisionOf` / shapes / a warning (I14) | L1 | − |
| C9a-09 | a formation regime / shapes / at most one state marked `ins:begins` per instrument, reported at two. An `ins:OnAcceptance` naming no parties reads every `ins:party` | L1 | + − |
| C9a-10 | the property policy's mid-term adjustment / which version decides each of three losses at the added unit, on its date, as known when notified and as known later / before the effective date v1, between the effective date and agreement v1 as then known and v2 as known after agreement, after agreement v2 | L1 | + |
| C9a-11 | a party leaving by amendment / its occasions arisen before the amendment / keep their parties (law I11) | L1 | + |
| C9a-12 | the licence ended by agreement / the amendment adding an expiry at the agreed date / the licence's regime enters its ending state on that date | L1 | + |
| C9a-13 | a relation whose conditions bind two subject classes / shapes / reported (law I4) | L1 | − |
| C9a-14 | the existing tests, the version and catalog checks, the import guard, `build:mtp`, `check:mtp`, the literate checks and `check:agent-guidance` / pass. Release notes for Instrument 0.15.0 | L1 | + |

## One command

Run from the repository root on machine R.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

## Artefacts to inspect

- `ontology/instrument/examples/`: the facility's amendment (the legal side of Wording's
  `facility-amendment.ttl`), the property policy's endorsement and mid-term adjustment, and the
  licence formed by separate signatures, released guarantor and ending by agreement,
  written before the model
- `ontology/instrument/README.md`: amendments, assents, formation as a regime, and the narrative and
  diagrams walking through the mid-term adjustment's market practice
- `ontology/instrument/shapes/`: the agreed-chain, overtaking, continuity and I4 shapes

## Deliberate non-coverage

- Consent rules, group powers, materiality and reinsurance
  recoveries (C9b)
- A regime run once per amendment, such as a proposal lapsing without consent (C9b)
- Incorporation (C9c)
- Deriving a version for an overtaken window, which the shapes only report (C16b, where C9-Q2's
  rule (iii) is revisited)
- Evaluating regimes and assents at runtime (C12)
- Assents with a share, conditional assents, and counter-offers (C9b's brief, HQ-1, HQ-7)

## Handoff

Written by the building machine when the work is ready for the human to commit.

Phase 1, examples first (ADR-A-C2), 2026-10-08:

- **Built:**
  - `ontology/instrument/examples/facility-amendment.ttl` (new): the legal side of Wording's
    `facility-amendment.ttl`, read with it and `facility-form.ttl`. An amendment by agreement, stated
    in the letter and the confirmation, effective 1 January 2028, recorded 3 February, agreed when
    the fourth party's assent arrives on 20 February, known from the 21st
  - `ontology/instrument/examples/licence-amendments.ttl` (new): formation as a regime, the three
    parties signing separately (S90), a guarantor released by amendment (C9-Q6), and ending by
    agreement through an added clause whose regime ends the licence at a date
  - `ontology/instrument/examples/property-endorsement.ttl` (new, the human's insurance example): a
    mid-term adjustment adding a unit to a property policy by endorsement, effective before the
    insurer agrees it, and three losses at the new unit before, inside and after that gap, with the
    version deciding each as known when notified and as known later
  - the ADR-A104 addendum "amendments, assents and taking effect" (Proposed)
- **Run by the agent:** the three examples against the current model and every layer's shapes,
  without inference. `facility-amendment.ttl` and `property-endorsement.ttl` report no violation.
  The facility's six warnings are coverage warnings for Wording's facility clauses, which carry no
  stated meaning. `licence-amendments.ttl` reports one violation, which the model phase removes:
  its formation transition's trigger, `ins:OnAcceptance`, is not yet a legal trigger.
- **Not run:** the tool tests, since the example conformance tests read every Instrument example
  and fail on the licence until the model phase.
- **Check first:** the deviations, then the endorsement example's header tables.
- **Deviations from the plan:**
  - **No subscription placement.** It needs each insurer bound from its own assent, which C9-Q5's
    formation regime does not give. The human withdrew the question (C9a-Q1) and chose an
    endorsement and mid-term adjustment instead, so row C9a-10 now tests that
  - **A deletion generates the assembled wording without the deleted element.** Wording's rule
    (W5, C5) needs `prov:generated` on a delete, which the licence's release now states
  - **The insured's assent comes with its request.** In the mid-term adjustment, the signed request
    is the insured's assent to the amended policy, so the amendment is agreed when the insurer
    assents
  - **Losses are the example's own records**, a place, a valid time and a recording time each, with
    an example property, `ex:at`. Instrument models no loss. The header tables give the expected
    version for each

## Results

Recorded at verification.
