<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# v_rig: the verification rig tool

Reads a verification rig, a directory of invented documents in the stated format, into the intermediate representation of [`ontology/v-rig`](../../ontology/v-rig/README.md), and writes the representation and its projections under an ignored path. A rig is named at run time, read in place and never written. Nothing read from a rig enters a tracked file, a test or a log line, and the tool writes a deny list from each rig for the deny-terms check.

```bash
mise exec -- python -m v_rig --rig <path to a rig> [--out <ignored path>]
```

The first lines a run prints are the rig digest, the format version, the checkout's commit and substrate release, and the versions of the vocabulary and the canonicalisation rules. Outputs go to `.local/v-rig/<rig digest>/` in the checkout unless `--out` names another path, and either is refused where git does not ignore it or where it lies under the rig.

| File | Holds |
|---|---|
| `ir.ttl` | the whole representation, both views, the run and the lifter's own findings |
| `blind.ttl` | the blind view, documents reduced to their id with the body nodes of each body and rendering |
| `findings.ttl` | the findings and the run |
| `run.json` | the run record, with counts |
| `deny-terms` | one escaped regular expression per id, title, value and body text of the rig |

Every output is byte for byte the same for one rig revision. The tests run on the synthetic mini-rig under `tests/mini-rig/`, written from generic premises, the only rig any tracked file names.

```bash
mise run check:v-rig
```
