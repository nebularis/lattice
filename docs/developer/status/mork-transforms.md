<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK transform backends - Status

**Unit ID:** `mork-transforms`
**Status:** 🟢 XJ1 to XJ5 built 2026-10-30, ADR-A148 Proposed
**Last updated:** 2026-10-30
**Plan:** [mork-transforms.md](../plans/mork-transforms.md)
**ADR:** [A-148](../../architecture/decisions/ADR-A148-mork-transform-backends.md), Proposed
**Branch:** `claude/config-authoring-studio`

## Current position

The maintainer answered XJ-Q1 to XJ-Q7 on 2026-10-30, and XJ1 to XJ5 were built the same day. `tools/mork_rdf`'s reader takes the source format and its path parser. `tools/mork_transforms` lowers a reading to the logical plan and compiles it to XSLT and JOLT. `platform/mork-transforms` runs both engines. The `policies` example gives its expected graph on Saxon-HE and on JOLT.

Checks run 2026-10-30, all passing: `check:mork-transforms`, `check:mork-rdf`, `check:mork`, `check:java`, `check:catalogue`, `check:identifiers`, `check:knowledge`, `check:reasoning-isolation`, `check:published-decisions`, `check:agent-guidance`.

**Next action, for the maintainer:** review ADR-A148 and the two new unratified facet values, `xslt` and `jolt`. Answer XJ-Q8 to XJ-Q12 (plan §5) for the studio's slices XJ6 and XJ7.

## Log

- 2026-10-30: unit planned from BL-03. ADR-A148 proposed.
- 2026-10-30: the maintainer asked for the studio's slices. XJ6 and XJ7 planned, with XJ-Q8 to XJ-Q12.
- 2026-10-30: XJ1 to XJ5 built. JOLT writes JSON-LD's keywords and IRIs as keys when `.`, `#`, `@` and its other syntax are escaped with a backslash in `shift` and `modify-overwrite-beta`, while `remove` matches keys unescaped.
