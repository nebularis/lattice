<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Candidate ranking

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It measures how often each way of ranking candidate target terms puts a confirmed target in its first five and first ten, so that the choice of what `mork:propose -- candidates` ranks by rests on figures. The confirmed pairs are the source term and each target term of every mapping of the hand-made ODRL pack, and of every mapping the LegalRuleML trial's history accepted. A pattern supplies some target terms that no source term names, such as `ins:Template`, `ins:Term` and `pty:Role`, and those are left out.

| Method | What it is |
|---|---|
| BM25 | `mork_propose.rank` over each target card's label, name and definition |
| BM25 + translations | the same, with each word of MTP's translation table indexed under the terms it may mean |
| recognition | `mork_communities.recognition`, edit distance, abbreviations and shared tokens, with the target terms loaded as its concepts |
| fused | BM25 with translations and recognition, by reciprocal rank |

## Pass criterion

Each source of pairs gives at least one pair, and BM25, with and without translations, and the fused ranking rank every pair's source. **A hit rate never fails the check.** The figures go to `report.md` and `report.json` here, which are generated and git-ignored. A figure quoted elsewhere states its run (ADR-A124 decision 5).

## Run it

```bash
mise run check:mork-candidate-ranking
```

It takes about ten seconds and is never a dependency of `check`.

## Measured results

Run 2026-10-30, after an object property was allowed to rank classes.

| | ODRL pack, 40 pairs, first 10 | LegalRuleML accepted, 10 pairs, first 10 |
|---|---|---|
| BM25 | 10% | 40% |
| BM25 + translations | 18% | 90% |
| recognition | 2% | 40% |
| fused | 15% | 80% |

- **The translation table carries the gain where a source uses legal words.** LegalRuleML's Obligation, Permission, Prohibition, Right and Bearer find their targets through it.
- **Recognition adds nothing here, and fusing it in lowers BM25's ranking.** It compares surface forms, which suits a field name such as `xs_point` or `somethingOrOther_Limit` against concepts named in full, not one vocabulary's terms against another's. Its place is the step before this one, reading a data dictionary's fields into concepts.
- **ODRL's misses are vocabulary.** Its assignee, assigner, action, constraint, consequence and operators share no word with what they map to, and the translation table holds legal words, not ODRL's. Adding ODRL's words would raise this figure by teaching the table the pack it is measured against.
- **Per-term ranking cannot find what a pattern supplies.** Counting those terms, the ODRL figure falls to 12% and the LegalRuleML one to 45%. The target-side cassettes in MTP teach them instead.
