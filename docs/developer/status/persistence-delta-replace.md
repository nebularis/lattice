<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Writing only what changed, as a persistence mode - Status

**Unit ID:** `persistence-delta-replace`
**Status:** 🟢 planned 2026-10-31, DR1 next
**Last updated:** 2026-11-01
**Plan:** [persistence-delta-replace.md](../plans/persistence-delta-replace.md)
**Sketch:** [persistence-delta-replace.md](../sketches/persistence-delta-replace.md)

## Current position

Sketched and planned on 2026-10-31 at the maintainer's request, after SQ-Q1 asked that a write write only what changed unless its profile chose a whole replace. DR-Q1 to DR-Q7 were answered the same day. The studio already writes its parts' and documents' deltas by hand (TD-136), which DR4 moves onto the generated replace. The linear replace investigation, on its own branch and unanswered, does not block the unit: what still writes a whole state is generated as R0 until LR-Q1 to LR-Q3 are answered.

**Next action:** DR1, on `claude/config-authoring-studio`, which the maintainer named on 2026-11-01.

## Log

- 2026-10-31: sketched, every question answered, planned.
- 2026-11-01: the maintainer asked for every planned slice on `claude/config-authoring-studio`, built autonomously, with the linear replace branch kept apart until later.
