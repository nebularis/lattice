<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Documentation link repair

**Unit ID:** `documentation-link-repair`
**Status:** Pending. Not started.
**Trigger:** human request, 2026-09-25, after `applied-ontology-readiness`
found `mise run topology:links` failing at `HEAD`.
**Status record:** [documentation-link-repair.md](../status/documentation-link-repair.md)
**Governing decision:** [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md) (canonical paths, relocation notes)

## Problem

`mise run topology:links` (`tools/repository_topology_check.py --links`)
reports 419 broken links, 340 of them distinct (2026-09-25):

| Group | Count | Cause |
|---|---|---|
| A. Jekyll build output | 290 | The checker walks `docs/**/*.md`, including `docs/_site/`, which `docs/.gitignore` ignores. These pages are copies built on one machine. |
| B. Wrong relative depth | about 15 | The target exists, but the path climbs one directory too many or too few, for example `../../architecture/…` from `docs/operator/` or `../../tools/surface/` from `docs/developer/plans/`. |
| C. Moved targets | about 20 | The target exists elsewhere: the phase handoffs in `status/`, `mtp-handoff.md` in `review/`, `governance-surfaces-integration.md` in `plans/`, `MorkEnhancements.md` and `eligibility-L9-replacement.md` under `ontology/surface/docs/`. |
| D. Missing targets | about 15 | No file exists: `toolchain.md`, `plans/repository-topology-and-documentation-governance.md`, `ordering-in-rdf.md`, `uniqueness-in-rdf.md`, `offline-phase-handoff.md`, `LLM Training.md`, `MORK UXD.md`, the `mtp/data` and `mtp/out` directories under `docs/`. |

Group A is a checker defect, not a documentation one. It hides the 50 real
failures (groups B to D) among 290 that nobody can fix.

## Slices

| Slice | Scope | Modules | Test level | Estimate |
|---|---|---|---|---|
| DLR-1 | The checker reads only Markdown git tracks or would track (`git ls-files --cached --others --exclude-standard docs`), as `tools/ontology_catalog.py` does. New test module for the link check: an ignored `_site` page with a broken link passes, a tracked one fails, a directory target resolves, a fragment on an existing file resolves | `tools/` | L1 | 40k |
| DLR-2 | Group B: correct each path's depth | `docs/` | L0 | 30k |
| DLR-3 | Group C: repoint each link to the target's current path | `docs/` | L0 | 40k |
| DLR-4 | Group D: per link, repoint to the document that replaced the target (for example ADR-A77 and its status record for the topology plan, ADR-A29 and `toolchain-jdk25-python314` for `toolchain.md`), or keep the text and remove the link with a relocation note, where the target never existed. Historical records keep their wording and gain a note, per ADR-A77 | `docs/` | L0 | 60k |
| DLR-5 | Add `topology:links` to the aggregate `mise run check` and to the `platform` workflow, once it passes | `mise.toml`, `.github/` | L0 | 10k |

Each slice ends with `mise run topology:links` reporting fewer failures, and
DLR-4 with none. DLR-2 to DLR-4 change links only, never the surrounding
text, except for relocation notes.

## Validation

- DLR-1 VP: four test cases above, plus a probe that reverting to `rglob`
  brings the `_site` failures back.
- DLR-2 to DLR-4: `mise run topology:links` before and after, with the list
  of links changed, and a spot check of five repaired links by the reviewer.
- DLR-5: the aggregate check fails when a broken link is introduced
  (mutation probe).

## Deliberate non-coverage

- Links in files outside `docs/`, such as layer READMEs under `ontology/`.
  A second pass can widen the checker's scope.
- External (`http`) links.
- Rewriting historical records beyond relocation notes.

## Token estimate

About 180k in total.
