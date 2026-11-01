# SPDX-License-Identifier: MPL-2.0
"""The proposal tools on the command line, the same functions the MCP server offers, for an agent that runs commands
rather than speaking MCP. `python -m mork_propose.cli --help` lists them."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import server


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="mork_propose")
    sub = parser.add_subparsers(dest="tool", required=True)
    sub.add_parser("teaching-pack", help="MTP and the MCN codebook")
    t = sub.add_parser("target-cards", help="cards of LATTICE layers"); t.add_argument("layers", nargs="+")
    s = sub.add_parser("source-cards", help="cards of a source vocabulary"); s.add_argument("path"); s.add_argument("--namespace", default="")
    c = sub.add_parser("candidates", help="target terms for one source term")
    c.add_argument("path"); c.add_argument("term"); c.add_argument("layers", nargs="+"); c.add_argument("-k", type=int, default=8)
    c.add_argument("--namespace", default="")
    les = sub.add_parser("lessons", help="the rules a proposal history teaches, the most frequent first")
    les.add_argument("history"); les.add_argument("--reference", default="", help="the pack a correction names"); les.add_argument("--ledger", action="store_true", help="one line per reviewed mapping instead")
    d = sub.add_parser("describe", help="one LATTICE term in depth, with the laws its shapes state"); d.add_argument("term")
    k = sub.add_parser("check", help="decode, validate, compile and run a proposal in MCN"); k.add_argument("mcn"); k.add_argument("--sample", default="")
    a = parser.parse_args(argv)
    if a.tool == "teaching-pack":
        print(server.teaching_pack())
    elif a.tool == "target-cards":
        print(server.target_cards(a.layers))
    elif a.tool == "source-cards":
        print(server.source_cards(a.path, a.namespace))
    elif a.tool == "candidates":
        print(server.candidate_terms(a.path, a.term, a.layers, a.k, a.namespace))
    elif a.tool == "lessons":
        from rdflib import Graph

        from .history import History

        history, reference = History(a.history), Graph().parse(a.reference) if a.reference else None
        print("\n".join(history.lessons(reference) if a.ledger else history.rules(reference, server._target()[0])))
    elif a.tool == "describe":
        print(server.describe_term(a.term))
    elif a.tool == "check":
        print(server.check_mapping(Path(a.mcn).read_text(encoding="utf-8"), a.sample))
    return 0


if __name__ == "__main__":
    sys.exit(main())
