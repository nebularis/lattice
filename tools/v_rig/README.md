<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# v_rig: the verification rig tool

Reads a verification rig, a directory of invented documents in the stated format, into the intermediate representation of [`ontology/v-rig`](../../ontology/v-rig/README.md), and writes the representation and its projections under an ignored path. A rig is named at run time, read in place and never written. Nothing read from a rig enters a tracked file, a test or a log line, and the tool writes a deny list from each rig for the deny-terms check.

```bash
mise run v-rig -- --rig <path to a rig> [--extension <ttl>]... [--out <ignored path>]
```

The first lines a run prints are the rig digest, the format version, the checkout's commit and substrate release, and the versions of the vocabulary and the canonicalisation rules. Outputs go to `.local/v-rig/<rig digest>/` in the checkout unless `--out` names another path, and either is refused where git does not ignore it or where it lies under the rig.

| File | Holds |
|---|---|
| `ir.ttl` | the whole representation, both views, the run and the lifter's own findings |
| `blind.ttl` | the blind view, documents reduced to their id with the body nodes of each body and rendering |
| `findings.ttl` | P4, every finding of the run as a `vrig:Finding` under the identifier rule, and the run |
| `run.json` | the run record, with counts |
| `deny-terms` | one escaped regular expression per id, title, value and body text of the rig |
| `p1/source.ttl` | the mapping source, the representation plus one derived edge per fact, `<carrier> key:<name> <value>` |
| `p1/layers.ttl` | P1, the representation projected onto the layers by the tracked scheme and the extensions |
| `p1/compiled.sparql` | the compiled queries of every scheme that ran, for a reviewer |
| `p1/shapes/<layer>.txt`, `p1/competency.json` | each target layer's validation report over P1, and each competency question's row count |
| `p2/VRigP2.thy`, `p2/ROOT`, `p2/Ledger.thy` | P2, the generated theory with one section per case and reading, its session, and the Ledger theory it imports, copied |
| `p3/<case digest>/<key>=<token>.json`, `p3/index.json` | P3, one vector per case and reading under `contracts/v-rig/vectors.schema.json` |
| `report.md` | P4, the findings rendered as Markdown, by document and locator |

**The mapping.** The tracked scheme, [`ontology/v-rig/projection/layers.mork.ttl`](../../ontology/v-rig/projection/layers.mork.ttl), maps the format's keys to Instrument, Wording, Party, Quantification, Ledger, Foundation and the insurance common module, and declares the keys that carry a reading with `vrig:readingKey`. It reads a value by the derived edge `key:<name>` and a node by a fact datum guarded on `vrig:key`. A rig's tokens reach concepts through its extension, a graph named with `--extension`, whose reference nodes answer the scheme's lookups by `skos:notation` and whose own mapping schemes run after the tracked one on the same source. A key no scheme reads is a finding of kind unmapped key, and a row of a scheme's run-time checks is one of kind uncertain mapping, at the node it names.

Every output is byte for byte the same for one rig revision. The tests run on the synthetic mini-rig under `tests/mini-rig/`, written from generic premises, the only rig any tracked file names.

```bash
mise run check:v-rig
```
