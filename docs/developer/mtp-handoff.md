<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MTP Validation Handoff

## Scope

MTP authoring establishes `mork/src/python/mtp/`, curated inputs under `mork/mtp/data/`, generated-output ownership under `mork/mtp/out/`, structural tests, `mise` tasks, and a manual CI job. It does not implement LLM backend selection or model-quality evaluation.

## Commands

Run in a clean network-enabled checkout:

```text
mise install
mise run bootstrap:mork
python -m pytest mork/src/python/test_mtp.py mork/src/python/test_mcn_decoder.py
mise run build:mtp
mise run check:mtp
git diff --exit-code mork/mtp/out/ mork/mtp/data/pins.lock.json
```

Then dispatch the `Platform checks` workflow and inspect `mtp-structural` output. It must install `mork`, run the structural test module, build, check, and reject uncommitted generated output or pin changes.

## Expected Artifacts

The build writes L0 content, corpus statistics, lens renderings, routing, diagnostics, and manifest under `mork/mtp/out/`. It updates `mork/mtp/data/pins.lock.json` from the current ontology and logical term hashes. Generated files and pin changes must be reviewed and committed together with the curated source change that caused them.

## Deferred Work

MTP Phase 7 remains deferred until the LLM backend interface exists. It owns held-out evaluation sets, model invocation, model-quality metrics, eval CI gates, retrieval indexing, SFT or LoRA corpora, and grammar/schema targets intended for backend evaluation.

## Restricted-environment Statement

No Python, dependency installation, MCN decoding, YAML parsing, build, CI, or generated-output validation ran in the restricted authoring environment. Only static source inspection, editor diagnostics, link checks, metadata parsing where available, and whitespace checks were performed.
