<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK run cost

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It measures what a run of a compiled MORK mapping costs in peak memory and time as its source grows, so that the choices of how to run one rest on figures. The runner is [`tools/mork_rdf`](../../tools/mork_rdf/README.md), §12.

The mapping is the catalogue fixture of `tools/mork_rdf/tests/fixtures`, and the source is N synthetic book records of ten triples each, one of them a blank-node author, written to a Turtle file that Oxigraph parses itself. Each size runs twice, once keeping the output in memory and once streaming it to a sink, each in a process of its own so that its peak resident memory is its own.

## Pass criterion

Each record gives nine instance triples, so a run of N records writes 9N distinct triples, kept or streamed, and reports no finding. **A wrong count fails the check. Time and memory never do.** The figures go to `report.md` and `report.json` here, which are generated and git-ignored. A figure quoted elsewhere states its run (ADR-A124 decision 5).

## Run it

```bash
mise run check:mork-rdf-run-cost
```

```bash
MORK_RUN_COST_QUICK=1 mise run check:mork-rdf-run-cost
```

```bash
MORK_RUN_COST_LARGE=1 mise run check:mork-rdf-run-cost
```

The default sizes are 10,000 and 100,000 records, and the run takes about two minutes. `MORK_RUN_COST_QUICK` runs 2,000 records alone. `MORK_RUN_COST_LARGE` adds 1,000,000, which needs about 15 GB, so it is for a machine that has it, not a laptop. It is never a dependency of `check`, and nothing is written into the repository except the two report files.

## Measured results

Run of 2026-10-29 on a laptop (Python 3.14.7, pyoxigraph 0.5.13, macOS).

| Records | Mode | Written | Peak MB | Run s |
|---|---|---|---|---|
| 10,000 | in memory | 90,000 | 425 | 2.96 |
| 10,000 | streamed | 90,000 | 339 | 1.91 |
| 100,000 | in memory | 900,000 | 1,447 | 42.84 |
| 100,000 | streamed | 900,000 | 1,514 | 23.21 |

At 100,000 records the peak is set before the queries run, while the source is skolemised. Loading the same file plainly into a store peaks at 558 MB, and skolemising it, which canonicalises its 100,000 blank nodes with RDFC-1.0, at 1,699 MB. Streaming saves the output's copies and about half the time, but cannot lower a peak the input sets.
