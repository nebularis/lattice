<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: TUT-3, chapters 7 to 9

**Unit:** [`lattice-tutorial`](../status/lattice-tutorial.md)
**Plan:** [lattice-tutorial.md](../plans/lattice-tutorial.md) §3 to §5, decisions TUT-D1 to TUT-D5

## Invariant

Chapters 7 to 9 add Quantification, Vocabulary, Eligibility and Behaviour to the running facility,
with Instrument's regimes and amendments, in the voice and depth of TUT-1 and TUT-2. Every excerpt
is a verbatim copy of its source, and every claim about a layer is checked against that layer's
README, spec, vocab or examples.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| TUT3-01 | chapters 0 to 9 / `check:tutorial-snippets` / `OK 43 excerpts and 17 repository links match the checkout` | L0 | + |
| TUT3-02 | the page / served / three Mermaid SVGs, none showing a syntax error. The state diagram shows performing, and default containing cure period and uncured | L6 | + |
| TUT3-03 | the page / served at 375 px / 43 Turtle blocks highlighted, no horizontal page scroll | L6 | + |
| TUT3-04 | the maintainer, as the intended reader / reads chapters 7 to 9 / no term used before it is explained, no claim that does not match the repository | review | + |

## One command

```bash
mise run check:tutorial-snippets
```

Pass: `OK 43 excerpts and 17 repository links match the checkout`, then `10 passed`. To read the
chapters as published, `mise run serve:jekyll` and open `http://127.0.0.1:4000/tutorial.html#amounts`.

## Artefacts to inspect

- `docs/_includes/tutorial/07-amounts-and-reference-data.md`, `08-rules-for-admission.md`,
  `09-change-over-time.md`

| Chapter | Sources re-read |
|---|---|
| 7 | `ontology/quantification/examples/additivity.ttl`, `ontology/quantification/vocab/quantification-vocab.ttl`, `ontology/vocabulary/README.md` §1 and §4, `ontology/vocabulary/examples/temporal-handover.ttl`, `alternative-regional-bindings.ttl`, `ontology/applied/classification/vocab/classification-vocab.ttl` |
| 8 | `ontology/eligibility/examples/flat-scheme-lending.ttl`, `evidence-binding.ttl`, `ontology/eligibility/README.md` §1, `ontology/eligibility/vocab/eligibility-vocab.ttl`, `ontology/instrument/examples/facility-agreement.ttl`, `tools/reference/eligibility/README.md` |
| 9 | `ontology/behaviour/examples/covenant-default.ttl`, `ontology/behaviour/README.md` (state records), `ontology/instrument/examples/facility-cure-period.ttl`, `facility-amendment.ttl` |

## Deliberate non-coverage

- Quantification's derived spaces, shares and signing down (cases 2 and 3 of `additivity.ttl`) are
  named only through `qnt:Intensive`.
- Behaviour's history states, concurrent regimes and allowances are not covered. Allowances return
  with capacity in chapter 10.
- Eligibility's evidence bindings are described and linked, not excerpted.

## Results

Run 2026-10-16 on Windows 11, against the maintainer's own `serve:jekyll` on port 4000.

| Check | Result |
|---|---|
| TUT3-01 | passed on the first run |
| TUT3-02 | passed, after one fix. `default` is a reserved word in Mermaid's state diagrams, so the first draft showed "Syntax error in text". The state is now `in_default`, labelled "default" |
| TUT3-03 | passed |
| TUT3-04 | awaiting the maintainer |

Three claims were corrected against their sources before the check ran: the list of match
strategies (chapter 8), what `bhv:isHypothetical` and `bhv:isCurrent` record, and what
`ins:affectsExisting false` covers (chapter 9).

Found while writing, not fixed in this slice: `tools/tutorial_snippets.py` compares excerpt lines as
written, so an excerpt indented inside a Markdown list never matches. Chapter 7 keeps its excerpts
outside the list. Teaching the check to remove a common indent is a small follow-up if lists with
excerpts are wanted.

## Adversarial probe

Not run for this slice. The check's behaviour on a mismatched excerpt was shown in TUT-1.
