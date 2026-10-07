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
| C9a-10 | the subscription placement / which insurers are bound on each date / each insurer from its own assent and none before it, and the share placed on each date the sum of the outward shares (`pty:outwardShare`) of the insurers who have assented | L1 | + |
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
  `facility-amendment.ttl`), the subscription placement, and the licence ended by agreement,
  written before the model
- `ontology/instrument/README.md`: amendments, assents, formation as a regime, and the narrative and
  diagrams walking through the placement's market practice
- `ontology/instrument/shapes/`: the agreed-chain, overtaking, continuity and I4 shapes

## Deliberate non-coverage

- Consent rules, group powers, materiality, the placement's inception rule and reinsurance
  recoveries (C9b)
- A regime run once per amendment, such as a proposal lapsing without consent (C9b)
- Incorporation (C9c)
- Deriving a version for an overtaken window, which the shapes only report (C16b, where C9-Q2's
  rule (iii) is revisited)
- Evaluating regimes and assents at runtime (C12)
- Assents with a share, conditional assents, and counter-offers (C9b's brief, HQ-1, HQ-7)

## Handoff

Written by the building machine when the work is ready for the human to commit.

## Results

Recorded at verification.
