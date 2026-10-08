<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: WA11, Documentation and close-out

**Unit:** `word-authoring-poc` (WAP), ADR-A118
**Plan:** [word-authoring-poc.md](../plans/word-authoring-poc.md) section "WA11: Documentation and close-out"
**Status record:** [word-authoring-poc.md](../status/word-authoring-poc.md)

## Invariant

Every slice from WA0 to WA10 built and automatically tested its own piece. WA11 closes the unit:
a human who has never seen the POC can read one README to understand how the pieces fit together
and how the data changes shape as it moves through them, then load the real add-in into real Word
and confirm the thing on screen matches what every earlier slice's automated test already checked
in isolation or against the compose stack. Nothing here is new behaviour. It is the point where
the unit stops being validated piece by piece and starts being validated as a whole, by a human,
in the one place (real Word) no automated test in this unit has ever reached.

## What this slice adds

- [`apps/word-authoring-addin/README.md`](../../../apps/word-authoring-addin/README.md) gained "How
  the proof of concept fits together" (an architecture diagram, a request-flow sequence diagram,
  and a data-construction diagram, all Mermaid) and "Load the add-in in Word" (Word on the web,
  desktop Word's registry sideload, and central deployment, each with how to remove it). This goes
  beyond the plan's own WA11 scope, at the human's explicit request.
- One-line cross-references added to
  [`platform/authoring-service/README.md`](../../../platform/authoring-service/README.md) and
  [`workers/README.md`](../../../workers/README.md), pointing back to the add-in's new diagrams
  rather than duplicating them.
- `docs/developer/INDEX.md` and the status record updated (this pack included).

## Automated checks run for this slice

| Check | Result |
|---|---|
| `mise run check:authoring` | pass — `check:authoring-contracts` 35, `check:authoring-tools` 4, `check:authoring-worker` 83, `check:authoring-addin` 69 Vitest, `test:authoring-addin` 13 Playwright, `check:authoring-service` BUILD SUCCESS |
| `mise run check:java` | pass — 9 modules, BUILD SUCCESS |
| `mise run check:workers` | pass — 121 passed |
| `mise run check:ontology-versioning` | pass — 35 in-scope documents checked against HEAD, no unbumped changes |
| `mise run check:ontology-catalog` | pass — 84 passed |
| `mise run topology:links` | **fails, pre-existing** — 62 broken links, all in `docs/developer/sketches/`, `docs/developer/status/` and one ADR, none of them touched by this unit or this slice. Not caused by, or fixed by, `word-authoring-poc`. Recorded here rather than silently skipped |

`check:authoring-stack` was not re-run in this slice (no stack-affecting code changed since WA10's
own green run. It is a Docker-backed, several-minute check, not part of the default `check`
aggregate).

## Manual checklist (human, real Word)

Everything above is checked by a machine. This is not: it needs a real Word client. Complete it,
then sign off in the table below (or note a deviation).

| # | Step | Pass | Result |
|---|---|---|---|
| M1 | trust the CA, open `https://localhost:3443/addin/harness.html` in Edge | no certificate warning | |
| M2 | sideload in Word on the web or desktop | the ribbon button opens the pane, "Connected" shows | |
| M3 | new document, Apply template (facility) | headings and section boxes appear | |
| M4 | Insert sample (facility) | the sample text with coloured, titled controls | |
| M5 | select `GBP 250`, Mark variable | an orange `Variable:` control | |
| M6 | Analyse | findings and detections, then the LE and Graph tabs fill | |
| M7 | Accept the `[Agent]` detection | the text becomes a variable control | |
| M8 | save, close, reopen, Analyse | markup and metadata survive, revision 2 | |
| M9 | type a new clause inside a section, mark it Clause, Analyse | the new clause is read | |
| M10 | Copy body OOXML, save it as `apps/word-authoring-addin/src/domain/fixtures/word-captured-1.xml` | the file exists for a later parser test | |
| M11 | close the pane, select words in a clause, right-click, LATTICE, Mark as variable… | the pane opens on Markup with the form filled in, and confirming marks the words | |
| M12 | select two paragraphs in a section, Home, LATTICE, Clause | a blue Clause box wraps them | |
| M13 | right-click with the selection outside any clause, Mark as variable… | the pane opens and says the selection is not inside a clause | |
| M14 | repeat M11 in the other Word client (web or desktop) | record whether the ribbon group and the right-click submenu appear there | |

## One command

```
mise run check:authoring
```

Everything else in this slice is either a single-purpose `mise` task listed in the table above, or
the manual checklist, which has no command.

## Artefacts to inspect

- [`apps/word-authoring-addin/README.md`](../../../apps/word-authoring-addin/README.md)'s new
  sections, and in particular whether the three Mermaid diagrams render (GitHub and VS Code's
  Markdown preview both support Mermaid, so a renderer failure here is a real defect in this
  slice).
- `docs/developer/INDEX.md` and the status record's final state.

## Self-probe

Not applicable. This slice adds no behaviour and no test a self-probe could break. Its own
correctness is the Mermaid diagrams rendering and matching the system they describe (checked by
inspection above) and the manual checklist (checked by the human, in real Word).

## Implementer choices

- The "whole POC" README the human asked for is the add-in's own `README.md`, not a new file. It
  is the closest thing the repository already had to a POC entry point (WA11's own plan already
  extends it), and the other three parts (contracts, service, worker) each keep their own
  README scoped to their own concern, cross-referencing the add-in's diagrams rather than
  repeating them.
- `topology:links`'s pre-existing failures are reported rather than fixed. Fixing them is out of
  scope for a unit that did not create them, and silently dropping the check from this record
  would be worse than reporting a known, unrelated failure.

## Deliberate non-coverage

- The manual checklist (M1 to M14) is not run by the agent. It needs real Word, which no part of
  this unit's automated tooling has ever reached (a risk R5 in the plan already names: a tenant
  that blocks sideloading leaves only the harness, which every other slice already tests).
- No new automated test exists for this slice, consistent with its plan scope (documentation only).
