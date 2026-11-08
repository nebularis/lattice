<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: v-rig VR-4, P1 against the layers' shapes, the reasoner and the competency queries

**Unit:** `v-rig` ([plan](../plans/v-rig.md), [status](../status/v-rig.md)).
**Branch:** `docs/placement-vehicles-structure`. Commits by the agent under the maintainer's authorisation of 2026-11-07, one per slice.
**Plan and test cases:** [the plan](../plans/v-rig.md), VR-4 in detail, the Formal methods table's row for P1.
**Decisions:** [ADR-A153](../../architecture/decisions/ADR-A153-verification-rig-module.md) decisions 5 and 6, [ADR-A83](../../architecture/decisions/ADR-A83-test-only-reasoning-engine-isolation.md) for the reasoner.

## Invariant

The projected layer graph is validated by every target layer's shapes, checked for consistency with the layers' specifications where a reasoner is available and reported as unchecked where not, and asked the tracked competency questions, and every answer that is not clean is a finding located at the node of the representation it came from or at the tracked file that asked.

## Test cases

| Case | Expectation |
|---|---|
| VR4-01 | Every target layer with shapes is validated and its report kept |
| VR4-02 | Every shape violation is a located finding whose message names the layer |
| VR4-03 | A violation on a projected node is located at the node of the representation it came from, one finding per node and constraint |
| VR4-04 | The locator is read back from a projected identifier, by the locator it carries or by the id that ends it, and nothing else |
| VR4-05 | Every competency file parses into questions, each a question ending in a question mark and a `SELECT` |
| VR4-06 | A question with no answer is a finding and an answered one is not |
| VR4-07 | An empty-query finding is located at the file that asked, in the declared view |
| VR4-08 | With the reasoning test kit the projection is checked for consistency and an inconsistency is a finding, and without it the check is a reasoner-unavailable finding |
| VR4-09 | The findings written into the representation conform to the module's shapes |
| VR4-10 | The checks' findings are the same over two runs |

## One command

Run from the repository root.

```bash
mise run check:v-rig
```

## Artefacts to inspect

`tools/v_rig/src/v_rig/p1_checks.py`, `ontology/v-rig/projection/competency/` (its README and seven query files), `tools/v_rig/tests/test_p1_checks.py`, and a run's `p1/shapes/<layer>.txt` and `p1/competency.json`.

## Deliberate non-coverage

The report rendered from the findings (VR-6). Which empty answers are the encoding's gap and which the case's silence, which the tool cannot tell and the consumer triages. A reasoner explanation of the inconsistency, which the test kit does not offer.

## Handoff

**Delivered 2026-11-08.** `p1_checks.py` validates the layer graph with each target layer's shapes under pySHACL with every target specification as the ontology graph, runs the reasoning test kit's `consistent` command over the specifications and the projection where the kit is built and Java is present, and runs the competency queries, one tracked file per target layer under the module's `projection/competency/`, each a sequence of `# question <name>: <words>` lines over a shared `PREFIX` prologue. A violation on a projected node is located back at the representation's node through the locator the projection's identifiers carry, or the id that ends them, and a finding about the encoding, an empty query or the consistency of the whole, is located at the tracked file that asked, which the vocabulary's `vrig:documentId` now says it may be. A finding's key names the constraint that fired, the property or node shape and the constraint component, so two violations on one node have two identifiers.

**What the run on the mini-rig says, which is the point of the slice.** 142 shape violations in three groups. Foundation asks every versioned thing for a persistent identity, 90 times over the instruments, wordings, elements and definitions, since the format gives ids and the projection mints no `fnd:PersistentIdentity`. Ledger asks each account definition for its unit of account, the owner kinds it admits and its merge rule, 18 times, which the format states on the programme or not at all. Instrument asks a definition for the term it arises under, what it defines and what it means, and asks that an instrument be expressed in an assembled wording, which the projection cannot give from a body alone. Foundation refuses `xsd:date` where it wants `xsd:dateTime` for a temporal scope, and the reasoner finds the projection with the specifications inconsistent for that same reason, a date literal on a property whose range is dateTime. 14 of 28 competency questions have no answer. No layer term links an instrument to the account of its limit or the quantity of its attachment, or relates one instrument to another, so following form and sitting above are unsaid. No quantity states its unit. No account is part of another or admits an owner kind. No text part refers to another element. No instrument has a period, no actor acts for another, and no loss event carries a peril. These are the requirements the plan says P1 produces for the ensemble, ledger and programme work, and they go to those plans by the lifecycle's rule, not from here.

**One mapping row withdrawn.** The scheme no longer writes `wrd:rankKey`, since Wording wants a string and the representation's ordinal is an integer, which a mapping cannot cast. With it in, Wording refused every element and the reasoner's answer was dominated by it. The scheme's header says so.

**Checks run, with their results.**
- `mise run check:v-rig`, `python -m pytest tools/v_rig -q`: 52 passed, in about 19 seconds, the reasoner's share about 10.
- `mise run check:catalogue`: `21 module(s) and 17 tool package(s) agree with the tree`.
- `mise run check:ontology-versioning -- --base-ref main`: `52 in-scope ontology document(s) checked against main: no unbumped changes`.
- `literate_extract.py ... --check`: `4 extracted artefact(s) consistent`.
- `mise run v-rig -- --rig tools/v_rig/tests/mini-rig --extension tools/v_rig/tests/mini-rig.extension.ttl`: ran, foundation refused with 102 violations, ledger 18, instrument 22, vocabulary, quantification and wording conform, the projection inconsistent, 28 questions of which 14 empty, and 268 findings in all, 142 shape violations, 60 unmapped keys, 40 uncertain mappings, 14 empty queries, 8 prose-only, 3 unresolved references and 1 inconsistency.

## Results

| Case | Result |
|---|---|
| VR4-01 | pass |
| VR4-02 | pass |
| VR4-03 | pass, on Foundation's identity constraint, with the projected node's role in the key so an instrument and its wording, both from one document, keep two findings |
| VR4-04 | pass |
| VR4-05 | pass, seven files, 28 questions |
| VR4-06 | pass |
| VR4-07 | pass |
| VR4-08 | pass, two tests, the unavailable branch by setting the kit unavailable |
| VR4-09 | pass |
| VR4-10 | pass, once the violations were ordered by focus, message and shape rather than by the report's blank nodes |
