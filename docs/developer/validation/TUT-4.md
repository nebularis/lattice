<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: TUT-4, chapters 10 to 13

**Unit:** [`lattice-tutorial`](../status/lattice-tutorial.md)
**Plan:** [lattice-tutorial.md](../plans/lattice-tutorial.md) §3 to §5, decisions TUT-D1 to TUT-D5 and TUT-Q4

## Invariant

Chapters 10 to 13 finish the tutorial: the applied Capacity module, Persistence and Surface, how a
domain is built on the substrate, and where to go next. Content still under construction is taught
as it is merged and marked as such (TUT-Q4). Every excerpt is a verbatim copy of its source, and every
claim is checked against the file it describes. With this slice the page has no placeholder chapter.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| TUT4-01 | all fourteen chapters / `check:tutorial-snippets` / `OK 48 excerpts and 34 repository links match the checkout` | L0 | + |
| TUT4-02 | the page / served / 14 chapters, no "Being written" placeholder, three Mermaid SVGs with no syntax error, 48 Turtle blocks highlighted | L6 | + |
| TUT4-03 | the page at 375 px / served / no horizontal page scroll | L6 | + |
| TUT4-04 | the four links to other site pages (`book.html`, `theory.html`, `glossary.html`, `architecture/ontology-releases.html`) / requested from the served site / each returns 200 | L6 | + |
| TUT4-05 | the maintainer, as the intended reader / reads chapters 10 to 13, and the tutorial end to end / no term used before it is explained, no claim that does not match the repository | review | + |

TUT4-05 is also the unit's acceptance criterion 5 (plan §1).

## One command

```bash
mise run check:tutorial-snippets
```

Pass: `OK 48 excerpts and 34 repository links match the checkout`, then `10 passed`. To read the
chapters as published, `mise run serve:jekyll` and open `http://127.0.0.1:4000/tutorial.html#capacity`.

## Artefacts to inspect

- `docs/_includes/tutorial/10-drawing-down.md`, `11-storing-and-serving.md`, `12-building-a-domain.md`,
  `13-where-next.md`
- `docs/_includes/tutorial/03-layer-map.md`, one table row corrected (below)

| Chapter | Sources re-read |
|---|---|
| 10 | `ontology/applied/capacity/README.md`, `docs/architecture-overview.md` (dependency kinds, lending use case), `spec/applied_capacity_execution_spec_capx_Version2.ttl`, `ontology/behaviour/examples/sequential-allowance.ttl`, `ordered-draws.ttl` |
| 11 | `ontology/persistence/README.md` §1, §2, §9, `ontology/persistence/examples/lending-credit-shared-class.ttl`, `ontology/surface/README.md` §1, `ontology/surface/examples/saas-subscription-currency.ttl`, `ontology/surface/vocab/surface-vocab.ttl` |
| 12 | `ontology/applied/README.md`, `ontology/applied/insurance/domain-README.md`, `common/README.md`, `common/vocab/common-vocab.ttl`, `peril/README.md`, `peril/examples/well-formed.ttl`, `CONTRIBUTING.md` |
| 13 | `ontology/mork/README.md`, `ontology/governance/README.md`, `docs/architecture/ontology-architecture.md` §1 and §7, `docs/developer/formal-methods-lifecycle.md`, `docs/book.html` |

## Deliberate non-coverage

- Capacity's source ontology (`cap:`) is designed but not written, so chapter 10 teaches it from the
  design document and the authored `capx:` profile, with a note saying so.
- Persistence's dimensions are listed, not taught one by one. The README and the patterns guide are
  linked.
- The insurance `exposure/`, `submission/`, `claims/` and `contract/` modules are named as planned.
- MORK, Governance and SPC are described in a paragraph each, as chapter 3 promised.

## Results

Run 2026-10-16 on Windows 11, against the maintainer's own `serve:jekyll` on port 4000.

| Check | Result |
|---|---|
| TUT4-01 | passed on the first run |
| TUT4-02 | passed |
| TUT4-03 | passed |
| TUT4-04 | passed |
| TUT4-05 | awaiting the maintainer |

Corrected against sources while writing:

- Chapter 3, committed in TUT-1, said Governance runs checks across all layers. `ontology/governance/`
  holds only an empty README, so the row now says it is the planned home for such checks.
- Chapter 10's example of a gating dependency now uses the design document's own, a secondary
  facility opened once a primary one is exhausted.
- Chapter 12 no longer names agency values the example does not show, and its table heading no
  longer says three levels for a four-row table.

Found while writing, not fixed in this unit: `ontology/applied/insurance/domain-README.md` says
`peril/` imports `common/`, but `peril/spec/peril.ttl` imports only Foundation and Quantification.
Chapter 3's diagram follows the spec.

## Adversarial probe

Not run for this slice. The check's behaviour on a mismatched excerpt was shown in TUT-1.
