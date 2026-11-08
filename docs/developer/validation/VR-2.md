<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: v-rig VR-2, the mini-rig and the lifter

**Unit:** `v-rig` ([plan](../plans/v-rig.md), [status](../status/v-rig.md)).
**Branch:** `docs/placement-vehicles-structure`. Commits by the agent under the maintainer's authorisation of 2026-11-07, one per slice.
**Plan and test cases:** [the plan](../plans/v-rig.md), VR-2 in detail, principles 1 to 7, 9 and 10.
**Decisions:** [ADR-A153](../../architecture/decisions/ADR-A153-verification-rig-module.md), Proposed. VR-Q2, VR-Q3, VR-Q5.

## Invariant

A rig read in place is unchanged by a run, every key reaches the representation as a fact in one of three states, the body reaches it as located body nodes in the blind view and in each rendering's view, nothing read from a rig reaches a tracked file or a log line, and the outputs of one rig revision are byte for byte the same.

## Test cases

| Case | Expectation |
|---|---|
| VR2-01 | A fact stated with a value, a fact stated as not known and a key not stated give a value, the unknown marker and no fact |
| VR2-02 | Front matter facts carry the declared view, body nodes the blind view, a rendering's nodes the rendering's view, and the blind graph holds no fact and documents reduced to their id |
| VR2-03 | Every key of a front matter reaches a fact, a key the format does not list included, and the provenance key reaches nothing |
| VR2-04 | A list key is one fact with several values, a list of mappings is records with facts, and the programme's layers and placements are typed records |
| VR2-05 | A non-numeric limit is a formula with its expression and inputs |
| VR2-06 | An id-valued fact resolves to its document or programme, an internal reference resolves, an external reference resolves through the documents the front matter names, and one nothing names stays unresolved with a finding |
| VR2-07 | Definitions are defined terms and paragraphs are prose-only nodes with findings |
| VR2-08 | Every body node is located and digested, and a document's digest is the digest of its normalised file |
| VR2-09 | The representation conforms to the module's shapes with the spec loaded beside it |
| VR2-10 | Two lifts of one rig give the same Turtle bytes and the same finding identifiers |
| VR2-11 | The digest of every rig file is unchanged after a run that writes outputs |
| VR2-12 | No log line carries a line of body text or an invented name |
| VR2-13 | The deny list matches every id, title and body text of the rig |
| VR2-14 | A manifest with an unsupported or absent format version is refused by key and value |
| VR2-15 | An output path under the rig, or one git does not ignore, is refused, and the default is `.local/v-rig/<rig digest>/` |
| VR2-16 | The tuple encoding, the locator string and the finding identifier follow the README's section 9 |

## One command

Run from the repository root.

```bash
mise run check:v-rig
```

## Artefacts to inspect

`tools/v_rig/` (`pyproject.toml`, `README.md`, `src/v_rig/canon.py`, `rig.py`, `markdown.py`, `lift.py`, `out.py`, `cli.py`), the mini-rig under `tools/v_rig/tests/mini-rig/`, `tools/v_rig/tests/test_v_rig_tool.py`, the `[[tools]]` entry in `repository-catalogue.md`, the `bootstrap:v-rig` and `check:v-rig` tasks and the `bootstrap:python` line in `mise.toml`.

## Deliberate non-coverage

The mapping scheme (VR-3), the projections (VR-4 to VR-6), the read-case seam (VR-7). A run on a rig other than the mini-rig, which no test may name.

## Handoff

**Delivered 2026-11-08.** The mini-rig, four invented documents, a primary, a first excess that follows form with an exception and a drop-down reading, and a second excess written on two lines, the lead line with its limit as a formula and the second line on its own terms, one rendering of the primary, a programme file with three layers and four placements, and an events file with two events. Every name and value is invented. The lifter reads a rig from its manifest in place, refuses an unsupported format version by key and value, drops the provenance key at the gate, lifts every key to a fact with the three states and the empty marker, lifts a body and each rendering to body nodes with locators and digests by the README's section 9, finds and resolves references, and writes `ir.ttl`, `blind.ttl`, `findings.ttl`, `run.json` and `deny-terms` under an ignored path, refusing any other. Outputs are canonical Turtle, sorted before serialisation, so the bytes depend on the triples alone.

**What the lifter emits as findings already.** An unresolved reference and a prose-only body node, each a `vrig:Finding` with the identifier rule of section 9. The remaining kinds arrive with the mapping (VR-3), the projections (VR-4) and the report (VR-6).

**The deny list.** The tool writes `deny-terms` beside its outputs, one escaped regular expression per id, title, value and body text. The deny-terms check reads one list, the first of `LATTICE_DENY_TERMS`, the user's configuration file, so the generated list is fed by naming it in that variable for a run of the check, as the file's header says, which sets the personal list aside for that run. The hook reads the personal list. Reading every candidate list would be a two-line change to `tools/deny_terms.py`, recorded as a technical-debt row rather than made here, since the plan said the check does not change.

**Checks run, with their results.**
- `mise run check:v-rig`, `python -m pytest tools/v_rig -q`: 27 passed.
- `mise run check:catalogue`: `21 module(s) and 17 tool package(s) agree with the tree`.
- `python -m pytest tools/test_lattice_repo_catalogue.py tools/test_python_requirements.py -q`: 137 passed, after `test_rc1_t1_the_catalogue_lists_every_module_in_order` was moved from 20 to 21 modules, the count VR-1's module made true.
- `mise exec -- python -m v_rig --rig tools/v_rig/tests/mini-rig`: ran, 75 body nodes, 111 facts, 13 references, 10 findings, printing the rig digest, the checkout commit `20a23568`, substrate release 0.21.0 and vocabulary 0.1.0 first.
- The whole of `check:ontology-catalog` was not run. The hook checks ran at the commit.

## Results

| Case | Result |
|---|---|
| VR2-01 | pass, four tests, the null value in a record as the empty marker included |
| VR2-02 | pass, three tests |
| VR2-03 | pass, two tests |
| VR2-04 | pass, two tests |
| VR2-05 | pass |
| VR2-06 | pass, two tests. The mini-rig's unresolved reference was first written as a condition the primary does have, and the lifter resolved it, so the mini-rig now names one it does not have |
| VR2-07 | pass |
| VR2-08 | pass |
| VR2-09 | pass |
| VR2-10 | pass |
| VR2-11 | pass |
| VR2-12 | pass |
| VR2-13 | pass |
| VR2-14 | pass |
| VR2-15 | pass, two tests |
| VR2-16 | pass, two tests, the minting specification's own example bytes included |
