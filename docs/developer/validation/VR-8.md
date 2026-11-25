<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: VR-8, questions on dates and on what an account declares, and three faults the first run found

**Unit:** `v-rig` ([plan](../plans/v-rig.md), VR-8, [status](../status/v-rig.md)). **Brief:** [rig agent brief](../notes/rig-agent-brief-2026-11-16.md), with its note of 2026-11-25.
**Placement:** T0, public substrate.
**Decisions:** none. No layer gains a term, and no decision record was edited.

**Status:** built 2026-11-25, awaiting the maintainer's verification. Two sessions built it. The first marked it and added eight questions, and the ledger unit's session took it over the same day, at the maintainer's word.

## Invariant

Projection P1 asks eighteen more competency questions of a projected case, each against a term a layer declares, and each returns no row on the synthetic mini-rig, which states none of those facts. A schedule and a section of one number are two elements. The bytes of every graph the tool writes follow the triples alone. A run on a rig outside the checkout writes a deny list that holds no word the checkout's tracked text already holds.

## What changed

- **Eighteen questions.** `foundation.rq` gains `recorded-and-effective`, `instrument.rq` gains `amendment-effect` and `amendment-source`, and `ledger.rq` gains `closing`, `period`, `ceiling`, `purposes` and `restoring-kinds`, then ten on what a merge policy states, each asked of an account definition through `ldg:mergePolicy`: `policy`, `merge-rule`, `rounding`, `residual-rule`, `rounding-treatment`, `order-criterion`, `order-check`, `unit-order`, `residual-allowed` and `mixed-position`. The questions number 46.
- **Three rows of the brief have no question.** `tie-rule`, `refuse-or-cut` and `whole-or-nothing` are values of `ldg:mergeRule`, which `merge-rule` returns.
- **A key is the text written.** `rig.py` reads a mapping's key as its scalar's own text, since YAML 1.1 reads `on`, `yes` and `no` as booleans and the canonical form then failed on a mapping with keys of two kinds.
- **A locator names one element.** In `lift.py`, the later of two top-level elements that would take one section label takes its kind before the label.
- **Prefixes in a fixed order.** `canonical_turtle` binds a prefix for each namespace a predicate uses, in the order of the namespaces, where the serialiser had numbered them in the order a set gave.
- **A deny list that can gate.** `deny_terms` leaves out an entry the checkout's tracked text holds, where the rig is outside the checkout. A rig inside the checkout keeps every entry.

## Test cases

| ID | Given, when, then | Level | Positive or negative | Pass criterion |
|---|---|---|---|---|
| VR8-01 | the mini-rig projected, and the eight questions on dates and on what an account declares | L3 | positive | `test_the_questions_on_dates_and_on_what_an_account_declares_are_asked`: each is asked, returns no row and is an empty-query finding |
| VR8-02 | the same, and the ten questions on a merge policy | L3 | positive | `test_the_questions_on_what_a_merge_policy_states_are_asked` |
| VR8-03 | front matter with keys written `on`, `no` and `3`, and a value written `yes` | L1 | positive | `test_a_key_is_the_text_its_author_wrote`: the keys are text, the value is a boolean, and the mapping has a digest |
| VR8-04 | a document with a Section 1 and a Schedule 1 | L1 | negative | `test_a_schedule_and_a_section_of_one_number_are_two_elements`: two elements, each of one kind, with two locators |
| VR8-05 | one graph serialised in five processes under five hash seeds | L2 | positive | `test_canonical_turtle_is_the_same_under_every_hash_seed`: one output |
| VR8-06 | the mini-rig's deny list, with and without tracked text that holds one of its entries | L1 | both | `test_deny_list_leaves_out_what_the_checkout_already_holds`: the entry held is left out and an entry not held stays |

## Command

```bash
mise exec -- python -m pytest tools/v_rig -q -p no:cacheprovider
mise exec -- python tools/literate_extract.py ontology/v-rig/README.md --layer v-rig --root . --check
```

A pass of the first is 79 tests, and of the second 4 artefacts consistent.

## Probes

- **The hash seed.** With the two lines that bind the prefixes removed from `canonical_turtle`, `test_canonical_turtle_is_the_same_under_every_hash_seed` failed and the test beside it passed. The file was restored.
- **The key.** Before the change to `rig.py` the tool itself failed on such a key, with `TypeError: '<' not supported between instances of 'bool' and 'str'`, which is how the fault was found.

## Requirements this slice hands on

- **For the ledger's vocabulary.** Nothing states an amount held back for one rank of claims. The ledger unit takes it.
- **For Ensemble.** Nothing states a floor on a share, which is decided before the ledger.
- **No published definition was found to disagree with an addendum** among the eighteen terms the questions read.

## Deliberate non-coverage

- No question reads a runtime record, such as the kind of a credit or the rank on a request.
- No rig holds a merge policy, so no question has an answer anywhere yet. Whether the format carries one is VR-Q17.
- A locator changes only where two elements would have shared one, so a rig with such a document gets other identifiers for the findings on the later element.
- The deny list is narrowed against the tracked text of the checkout the tool runs in, and a word that only another branch holds is not left out.

## What was run

2026-11-25, on this checkout, through `mise`.

| Command | Result |
|---|---|
| `python -m pytest tools/v_rig -q -p no:cacheprovider` | 79 passed in 49 seconds |
| `python tools/literate_extract.py ontology/v-rig/README.md --layer v-rig --root . --check` | 4 extracted artefacts consistent, run by the subagent that wrote the ten questions |
| `mise run check:ontology-versioning -- --base-ref main` | failed, as it does on this branch, naming three unbumped things: Persistence's specification, the rig module's projection and the substrate release. Versions move once, at the merge |
| the tool on a rig outside the repository | ran to the end. Its counts are with the maintainer, and whether they are recorded here is VR-Q19 |
