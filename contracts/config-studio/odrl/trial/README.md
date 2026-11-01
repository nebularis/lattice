<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ODRL proposal trial

Whether a language model, given only `tools/mork`'s proposal tools (`mise run mork:propose`), MORK's teaching pack and ODRL's vocabulary, proposes a usable MORK mapping scheme from ODRL to LATTICE, scored against the hand-made pack [`../odrl-instrument.mork.ttl`](../odrl-instrument.mork.ttl) with `mise run mork:propose-trial`.

| File | What it is |
|---|---|
| [`software-licence.ttl`](software-licence.ttl) | the sample policy as Turtle, so a check runs offline |
| [`run-1/`](run-1) | the first run: each attempt the agent checked with its findings, its final `proposal.mcn`, its `notes.md`, and `score.json` |
| [`run-2/`](run-2) | the second run, with the improved proposal tools, laid out the same way |
| [`history.ttl`](history.ttl) | the proposal history: the run, the mappings it proposed, and the pack's review of each (MORK README §5.18) |

## Run 1, 2026-10-29

A Sonnet agent, told not to read the pack or anything that describes it, needed 9 check rounds to reach a scheme with no error, of 35 mappings writing 85 triples on the sample. The pack accepted 8 of the mappings as they stand, corrected 16 and rejected 11, and the two outputs on the sample agree at a precision of 0.29 and a recall of 0.20. The output measure is strict: the run names its own condition keys and builds no implied prohibition, so every pattern that touches them differs.

The run found the pack's structure without reading it: a term and a relation for each rule, the relation kinds, the parties as holder, counterparty, obligor and obligee, the action as the activity, a remedy or consequence arising on the breach of its rule, a permission's duty as the act it arises on, and a scope profile with one condition for each constraint, chosen by the operator with guards, and an interval's range, bound and value for a comparison. It did not see that a permission excepts an implied prohibition, and could not name a bound's sense or closure.

What it found missing, and what changed before the next run:

| Found | Changed |
|---|---|
| the cards named no namespaces, and no individuals such as `qnt:Upper` or `elg:ExactMatch` | the cards head each layer with its prefixes, read its vocabulary as well as its specification, and list its individuals |
| the teaching pack had no RDF source, no glue direction, no template and no guard, and contradicted the cassettes on weighting | MTP's doctrine gains them, and says confidence is weighting and its reason a note |
| a relative `mork:individualIRI` crashed the compiler | it is a `BadIRI` finding |
| MCN has no codes for `mork:appliesWhen`, `sh:declare` or the SHACL a guard needs, its `SH` payload makes only targeted shapes, and an inline node with an id is refused | not yet changed. A proposal writes them as CURIEs and raw triples |

## Run 2, 2026-10-30

The same brief to a Sonnet agent, with the tools improved from a review of the first trials: cards that give a term's utility in full, `describe` for one term with its laws, a check that holds the output on the sample to the layers' shapes, a translation table of legal words, and five target-side cassettes. The agent read nothing that describes the pack.

| | Run 1 | Run 2 |
|---|---|---|
| check rounds to no error | 9 | 3 |
| mappings | 35 | 52 |
| accepted by the pack | 8 (23%) | 30 (58%) |
| corrected | 16 | 22 |
| rejected | 11 | 0 |
| output on the sample, precision and recall against the pack's | 0.29 and 0.20 | 0.83 and 0.63 |
| tokens | 191,094 | 106,804 |
| time | 424 s | 136 s |

Run 2 stated the prohibition a permission excepts, which run 1 missed, a remedy arising on breach, and an interval condition with its bound's sense and closure. The improvement is larger than the LegalRuleML re-run's, and part of it is likely the cassettes, which were written from patterns the ODRL pack also uses. One run of each, so the figures suggest and do not settle.

What the agent found missing, not yet changed: a date bound written through `qnt:numericValue`, since no card says how a date is held, no report of what in the sample was left unmapped, and a permission's duty that the mapping could not tie to its permission.

