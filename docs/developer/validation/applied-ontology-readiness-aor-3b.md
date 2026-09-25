<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-3b, generated-document versions and trackable scope

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Follows:** [AOR-3](applied-ontology-readiness-aor-3.md), whose job-family item was deferred
**Decision:** [ADR-A86 addendum](../../architecture/decisions/ADR-A86-ontology-semantic-versioning.md#addendum-2026-09-25-guarantees-consumers-rely-on), item 5 (content-hash versions, agreed by the human 2026-09-25)

## Invariant

A generated ontology document's version IRI changes exactly when its content
does. The version check and the catalog read only files git tracks or would
track, so neither depends on one machine's build output.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR3B-01 | the job-family surface / rendered / every module's version IRI is its ontology IRI plus 16 hex digits | L1 | + |
| AOR3B-02 | same / rendered twice / versions unchanged | L2 | + |
| AOR3B-03 | a law discharge added after compilation / rendered / manifest version changes, core version does not | L1 | - |
| AOR3B-04 | an ignored `execution/` document importing an undeclared IRI / catalog check / no problem, not catalogued | L1 | + |
| AOR3B-05 | this repository / catalog check / consistent, no job-family entries | L1 | + |

## Commands

```bash
python -m unittest surface.test_surface
```

```bash
mise run check:ontology-catalog
```

```bash
mise run check:mtp
```

Pass: 63 Surface tests, 12 catalog tests and a consistent catalog with three
known defects (the insurance sketch and two MORK examples), and `MTP
structural checks passed`.

## Artefacts to inspect

- `tools/surface/src/surface/compile.py`: `stamp_content_version`, called by
  `render`. `_ontology_header` no longer writes `0.0.1`.
- `tools/ontology_version_check.py`: `repository_ttl_files`, used by both tools.
- `ontology/catalog-v001.xml`: the eight job-family entries committed in
  `6e36586` are gone. On a fresh clone they named files that do not exist,
  because `**/execution/*` is ignored.
- The SWRL catalog entry now points at `https://www.w3.org/Submission/SWRL/swrl.owl`.
  The namespace IRI returns HTTP 406.
- `ontology/mork/mtp/data/pins.lock.json`: the whole-graph hash, re-pinned. No
  term hash moved.

## Adversarial probe (run by the agent)

A constant version suffix failed AOR3B-03. Scanning with `rglob` again failed
AOR3B-04 and AOR3B-05.

## MTP pin

`pins.lock.json` records a hash of the whole `Mork.ttl` graph and one per
term, so any change to MORK is reviewed deliberately. `53eb210` changed the
header (version IRI, Foundation import) without re-pinning, and this change
set changed it again. `python -m mtp.cli update-pins` re-pinned it. The
aggregate `mise run check` runs `build:mtp` before `check:mtp`, and `build`
also rewrites the pins, so the pin check can fail only in CI. Separating
`build` from `update-pins` is an MTP pins decision, which
`docs/architecture/mork-teaching-pack.md` reserves for an ADR, and is not made
here.
