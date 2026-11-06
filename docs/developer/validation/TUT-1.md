<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: TUT-1, chapters 0 to 3

**Unit:** [`lattice-tutorial`](../status/lattice-tutorial.md)
**Plan:** [lattice-tutorial.md](../plans/lattice-tutorial.md) §4 and §5, decisions TUT-D1 to TUT-D5

## Invariant

The orientation chapters give a data architect new to ontologies what every later chapter assumes:
why LATTICE exists (chapter 0), the counterpart of each ontology idea in a relational model and
where it misleads (chapter 1), enough Turtle to read every excerpt (chapter 2), and the layers and
their dependency order (chapter 3). Every excerpt is a verbatim copy of its source, and every claim
about LATTICE is checked against the file it describes.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| TUT1-01 | the four chapters / `check:tutorial-snippets` / `OK 9 excerpts and 3 repository links match the checkout` | L0 | + |
| TUT1-02 | chapter 3's Mermaid diagram / page served and loaded / one SVG with 12 nodes, no syntax error | L6 | + |
| TUT1-03 | the Turtle excerpts / page served / 9 blocks highlighted by Rouge, token colours applied | L6 | + |
| TUT1-04 | the page at 375 px / loaded / no horizontal page scroll, long excerpt lines scroll inside their block | L6 | + |
| TUT1-05 | the maintainer, as the intended reader / reads chapters 0 to 3 / finds no term used before it is explained, and no claim that does not match the repository | review | + |

TUT1-05 is the slice's acceptance. It sets the voice and depth TUT-2 to TUT-4 follow (plan §5).

## One command

```bash
mise run check:tutorial-snippets
```

Pass: `OK 9 excerpts and 3 repository links match the checkout`, then `10 passed`. To read the
chapters as published, `mise run serve:jekyll` and open `http://127.0.0.1:4000/tutorial.html`.

## Artefacts to inspect

- `docs/_includes/tutorial/00-why.md` to `03-layer-map.md`

Sources the chapters quote or describe, each re-read while writing:

| Chapter | Sources |
|---|---|
| 0 | `README.md`, `ontology/instrument/examples/facility-agreement.ttl`, `ontology/behaviour/examples/covenant-default.ttl` |
| 1 | `ontology/applied/classification/spec/classification.ttl`, `ontology/foundation/shapes/constraints.ttl` |
| 2 | `ontology/foundation/examples/keys.ttl` |
| 3 | `tools/import_guard.py`, `docs/architecture/ontology-architecture.md` §1 and §7, `ontology/applied/README.md`, the `owl:imports` of every applied module and of Persistence and Surface |

## Deliberate non-coverage

- Chapter 3's diagram draws only the main imports. The full lists are in each document's
  `owl:imports`, as the chapter says.
- Chapters 4 to 13 remain placeholders until TUT-2 to TUT-4.

## Results

Run 2026-10-14 on Windows 11.

| Check | Result |
|---|---|
| TUT1-01 | passed, after one fix. The first run reported drift in chapter 1. Its `cls:industry` excerpt had the last line of `cls:territory`'s `fnd:utility`. Corrected to the source |
| TUT1-02 | passed. One SVG, 12 nodes |
| TUT1-03 | passed. Classes `nn`, `k`, `s` and `p` carry the layout's colours |
| TUT1-04 | passed at 375 px. Below 320 px the page scrolls, from the `min-width: 320px` the layout inherits from the theory layout |
| TUT1-05 | awaiting the maintainer |

## Adversarial probe

The check's own probe happened unplanned in TUT1-01. A paraphrased line in an excerpt was reported
with its chapter, line and source, and passed once corrected.
