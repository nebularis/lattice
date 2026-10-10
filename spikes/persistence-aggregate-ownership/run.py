# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Print both experiments. Run with ``python spikes/persistence-aggregate-ownership/run.py``."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import concurrency_model as cm  # noqa: E402
import payload_graph  # noqa: E402
import placement as pl  # noqa: E402


def closures() -> None:
    g = pl.placement_graph(shared_policy=True, inbound_quote=True)
    print("== Which nodes does a delete of the placement take?")
    for result in (
        pl.first_property_path(g),
        pl.flat_alternation(g),
        pl.unrolled_paths(g),
        pl.unrolled_sparql(g),
        pl.deny_list(g, label="every reference listed (attachment too)"),
        pl.deny_list(g, references=pl.REFERENCES_FORGETTING_ONE, label="contactedMarket forgotten"),
        pl.deny_list(g, references=pl.REFERENCES - {pl.EX.marketType, pl.EX.status}, label="vocabulary links forgotten"),
        pl.deny_list(g, references=pl.REFERENCES - {pl.EX.marketType, pl.EX.status}, guard_vocabulary=True, label="same, vocabulary guard on"),
    ):
        print(f"  {result.name:<42} {len(result.members):>2}  {', '.join(result.short())}")
    forgot = pl.deny_list(g, references=pl.REFERENCES_FORGETTING_ONE)
    print("  entities the forgotten reference takes:", sorted(str(n).rsplit('#', 1)[1] for n in forgot.members & {pl.EX.Axa, pl.EX.Chubb}))
    print("\n== A node with two owners")
    for member, roots in pl.owners(g, [pl.EX.P, pl.EX.P2]).items():
        print(f"  {str(member).rsplit('#', 1)[1]} is in the closure of {sorted(str(r).rsplit('#', 1)[1] for r in roots)}")
    print("\n== References into the aggregate from outside")
    for s, p, o in sorted(pl.inbound_from_outside(g, pl.unrolled_paths(g))):
        print(f"  {str(s).rsplit('#', 1)[1]} {str(p).rsplit('#', 1)[1]} {str(o).rsplit('#', 1)[1]}")


def concurrency() -> None:
    print("\n== Two overlapping writers (snapshot isolation, statement-level first-committer-wins)")
    table = cm.matrix()
    names = [d.name for d in cm.DISCIPLINES]
    print(f"  {'':<40}" + "".join(f"{n.split(' ')[0]:<26}" for n in names))
    for pair, row in table.items():
        cells = []
        for n in names:
            label = row[n].label()
            if cm.independent(pair) and label == "one conflicts":
                label += " (false)"
            cells.append(f"{label:<26}")
        print(f"  {pair:<40}" + "".join(cells))
    print("\n  " + "\n  ".join(n for n in names))


def payload() -> None:
    print("\n== Where the composite replace writes the new payload")
    for graph, values in payload_graph.payload_destination().items():
        print(f"  {graph}: {values}")


if __name__ == "__main__":
    closures()
    concurrency()
    payload()
