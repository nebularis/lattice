<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK transform backends - Status

**Unit ID:** `mork-transforms`
**Status:** 🟢 XJ1 to XJ7 built 2026-10-30, ADR-A148 Proposed
**Last updated:** 2026-10-30
**Plan:** [mork-transforms.md](../plans/mork-transforms.md)
**ADR:** [A-148](../../architecture/decisions/ADR-A148-mork-transform-backends.md), Proposed
**Branch:** `claude/config-authoring-studio`

## Current position

The maintainer answered XJ-Q1 to XJ-Q7 on 2026-10-30, and XJ1 to XJ5 were built the same day. `tools/mork_rdf`'s reader takes the source format and its path parser. `tools/mork_transforms` lowers a reading to the logical plan and compiles it to XSLT and JOLT. `platform/mork-transforms` runs both engines. The `policies` example gives its expected graph on Saxon-HE and on JOLT.

Checks run 2026-10-30, all passing: `check:mork-transforms`, `check:mork-rdf`, `check:mork`, `check:java`, `check:catalogue`, `check:identifiers`, `check:knowledge`, `check:reasoning-isolation`, `check:published-decisions`, `check:agent-guidance`.

XJ6 and XJ7 were built on 2026-10-30 after the maintainer answered XJ-Q8 to XJ-Q13. A compile job of the mapping part writes each XML or JSON scheme's stylesheet or chain with its attribution table. The transforms worker, `platform/config-studio-transforms`, runs them over a sample source on request-reply through `POST /api/workspaces/{ws}/transforms`. Mapping mode has a format selector, offers a representation scheme's `skos:example` as the sample, and lists the compiled transforms to download. The sample "Policies from XML and JSON" holds the `policies` example. The engines cache what they compile (PRI-78).

Checked live on 2026-10-30 with the sample in a running studio: both examples run, each mapping's count shows, the compiled transforms download, and a warm transform answers in about 30 ms through the service and the worker. `Peril` writes nothing in either run, since its source concepts are sorted into the vocabulary part (TD-133).

**Next action, for the maintainer:** review ADR-A148, the facet values `xslt` and `jolt`, and PRI-77 and PRI-78, which record the principles stated on 2026-10-30.

## Log

- 2026-10-30: unit planned from BL-03. ADR-A148 proposed.
- 2026-10-30: the maintainer asked for the studio's slices. XJ6 and XJ7 planned, with XJ-Q8 to XJ-Q12.
- 2026-10-30: XJ1 to XJ5 built. JOLT writes JSON-LD's keywords and IRIs as keys when `.`, `#`, `@` and its other syntax are escaped with a backslash in `shift` and `modify-overwrite-beta`, while `remove` matches keys unescaped.
- 2026-10-30: the maintainer answered XJ-Q9 to XJ-Q12 and set the coordinator principle. The run was profiled, its cost is a cold JVM. XJ-Q8 reframed and XJ-Q13 added.
- 2026-10-30: the maintainer answered XJ-Q8 (a) and XJ-Q13 (a). The engines cache compiled stylesheets and chains. XJ6 and XJ7 built.
- 2026-10-31: TD-133 taken on by the `studio-publication` plan, and closed by its slice PB1.
