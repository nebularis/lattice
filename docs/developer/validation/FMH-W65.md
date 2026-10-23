<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-W65, Wording shares values across assembled wordings

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice W-65, planned in
[plan §4.13](../plans/formal-methods-track-h.md#413-w-65-wording-shares-values-across-assembled-wordings-planned-2026-10-20-td-65) (TD-65). Built on
2026-10-20 at our leaning, for the maintainer's review. Authored and run in autonomous mode, not committed. Versioning is ignored on this branch
(TD-64), so no version IRI moved.

**For the maintainer:** read the decisions taken alone and countersign the one changed test (below).
**For countersignature (non-weakening rule):** `test_c4_02_c5_01_every_example_conforms` counted five Wording examples and now counts six, since
`shared-values.ttl` is new. No test was removed or skipped. The shape that a value belongs to exactly one assembled wording is relaxed on purpose
(the slice's subject), and a value with no wording is still reported, by the same shape and by the existing case `value-in-no-wording`.

## Invariant

Two assembled wordings may supply the same value record, and a value record that no assembled wording supplies is still reported. A change to
a value is a new record, so a wording after an endorsement restates only the record it changes. A section whose clause is replaced is a new
version of the section, so a wording's tree is the evidence of its exact text.

## What changed

- **Wording README and its generated files** (`ontology/wording/README.md`, `spec/wording.ttl`, `shapes/structural.ttl`).
  `wrd:hasValue` is no longer `owl:InverseFunctionalProperty`. The shape on a variable value is `sh:minCount 1` on `sh:inversePath wrd:hasValue`,
  with `sh:maxCount 1` gone, and its message reads "at least one". §5.12 gains a paragraph and a link to the example, and §10 a release note.
  Regenerated with `tools/literate_extract.py`, not edited by hand.
- **Example** `ontology/wording/examples/shared-values.ttl`. A lease, `ex:lease-v1` and `ex:lease-v2`, one identity, from one form. They share
  `ex:v-rent` and `ex:v-notice` and differ in the return period, `ex:v-days-1` and `ex:v-days-2`. It passes every Wording shape.
- **Instrument example** `ontology/instrument/examples/property-endorsement.ttl`. New `ex:sec-2-v2` (identity `ex:sec-2-identity`,
  `prov:wasRevisionOf ex:sec-2`, comprising `ex:cl-2-1-v2`), and `ex:sec-2 fnd:supersededBy ex:sec-2-v2`. `ex:wording-v2` comprises
  `ex:sec-2-v2` and includes it and `ex:cl-2-1-v2`. The header table gains a row. Instrument's README §22.22 and release notes follow.
- **Tests** (`tools/test_wording.py`). New `test_td65_two_assembled_wordings_share_value_records`. The example count is six.

## Test cases

| ID | Checks |
|---|---|
| TD-65-T1 | the two wordings of `shared-values.ttl` share exactly the rent and notice records and differ only in the return-period records |
| TD-65-T2 | `wrd:hasValue` is not inverse-functional in the vocabulary closure |
| TD-65-T3 | the example has no violation, and an added value record in no wording is reported |
| existing | `c3_04`, `c3_14`, `c4_02_c5_01` and `c3_09` (README equals its generated files) now cover the new example and the regenerated files, and `test_instrument.py` covers the changed endorsement example against the Instrument and Wording shapes and laws |

## One command

```
mise run check:ontology-catalog
mise exec -- python tools/literate_extract.py ontology/wording/README.md --layer wording --root . --check
```

From the repository root. A pass is no failed test and "4 extracted artefact(s) consistent".

## Results

| Command | Result |
|---|---|
| literate extract `--check` on the Wording README | pass, 4 artefacts consistent |
| `pytest tools/test_wording.py tools/test_instrument.py` | 202 passed |
| `mise run check:ontology-catalog` | one run failed 3 tests in `test_lattice_repo_catalogue.py`, because a parallel developer's tree briefly held `ontology/persistence/execution`. Re-run, that file passes (112 passed), and the rest of the task ran 1133 passed, 7 skipped. `python tools/ontology_catalog.py check` reports consistent with 2 known defects (Mork imports) |
| `mise run check:ontology-versioning` | fails, `UNBUMPED`, as expected while this branch ignores versioning (TD-64) |

Not run: the whole `check:ontology-catalog` task end to end in one passing run (see above), `check:deny-terms` (needs a personal deny-list), and
the formal-methods checks, which this slice does not touch.

## Decisions taken alone, for the maintainer's review

1. **The shape keeps a minimum of one.** A value in no wording stays a finding. The plan said "at least one" and this follows it.
2. **`shared-values.ttl` is a small generic lease**, three variables and one clause, not an insurance example. It needed a form holding the tree
   (W1) and one `wrd:Text` (the test every example has one).
3. **`ex:sec-2` is marked `fnd:supersededBy ex:sec-2-v2`**, as the example already does for the wording and the policy.
4. **The section version repeats `wrd:objectId "2"` and `wrd:rankKey "b0"`**, as `ex:cl-2-1-v2` carries its identity's `objectId`.
5. **`ex:cl-2-1-v2` is not given a rank key,** as before, and the shapes accept it.

## Deliberate non-coverage

- No law checks that two wordings sharing a value record are versions of one identity. Sharing across unrelated instruments is allowed, and a
  value record is never edited, so it is harmless.
- No shape forbids a value record's variable being absent from the sharing wording's included elements, as before.
- Persistence and the applied ontologies are not touched, so any store that assumed one wording per value (a join on `wrd:hasValue`) is for those
  developers to review.
