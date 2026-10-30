# SPDX-License-Identifier: MPL-2.0
"""Scoring a proposal run against a reference pack, and recording it in the history (MORK README §5.18): the run and its
mappings, the pack's review of each, the decisions' counts, and how far the proposal's output on a sample agrees with
the pack's. `mise run mork:propose-trial -- <run folder> ...` writes `score.json` beside the run's `proposal.mcn`."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from .history import MORK, History, agreement, patterns, review_against, scores


def score(run_dir: Path, pack: Path, pack_scheme: URIRef, history_path: Path, sample: Path | None, *, model: str, at: datetime,
          started: datetime | None = None, input_tokens: int | None = None, output_tokens: int | None = None,
          total_tokens: int | None = None) -> dict:
    import mcn_decoder
    from mork_rdf import compile_scheme, run

    proposal = mcn_decoder.decode((run_dir / "proposal.mcn").read_text(encoding="utf-8"))
    schemes = sorted(proposal.subjects(RDF.type, MORK.MappingScheme), key=str)
    if len(schemes) != 1:
        raise ValueError(f"the proposal holds {len(schemes)} mapping schemes, and a run is scored on one")
    scheme = schemes[0]
    reference = Graph().parse(pack)
    decisions = review_against(proposal, scheme, reference, pack_scheme, at)

    history = History(history_path)
    run_iri = URIRef(f"urn:mork-propose:run:{run_dir.name}")
    history.record_run(run_iri, proposal, scheme, model=model, pack="MTP, mork_propose", source=None, at=at, started=started,
                       input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens)
    reviewer = URIRef(str(pack_scheme))
    for n, (mapping, decision, corrected, note) in enumerate(decisions, start=1):
        history.record_review(URIRef(f"{run_iri}:review/{n}"), mapping, decision, reviewer=reviewer, at=at, note=note, corrected_by=corrected)
    history.save()

    result = {"run": run_dir.name, "scheme": str(scheme), "mappings": scores(decisions)}
    if any(v is not None for v in (started, input_tokens, output_tokens, total_tokens)):
        result["cost"] = {"seconds": round((at - started).total_seconds()) if started else None, "input_tokens": input_tokens,
                          "output_tokens": output_tokens, "total_tokens": total_tokens}
    if sample is not None:
        source = Graph().parse(sample)
        mine = compile_scheme(proposal, scheme, base="urn:trial:proposal/", at=at)
        theirs = compile_scheme(reference, pack_scheme, base="urn:trial:pack/", at=at)
        a, b = run(mine, source), run(theirs, source)
        result["output"] = agreement(patterns(a.graph + a.tbox, "urn:trial:proposal/"), patterns(b.graph + b.tbox, "urn:trial:pack/"))
        result["output"].update({"proposal_triples": len(a.graph) + len(a.tbox), "pack_triples": len(b.graph) + len(b.tbox)})
    result["decisions"] = [{"mapping": str(m).rsplit("#", 1)[-1], "decision": d, "note": note} for m, d, _, note in decisions]
    (run_dir / "score.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="mork_propose.trial")
    p.add_argument("run_dir")
    p.add_argument("--pack", required=True)
    p.add_argument("--pack-scheme", required=True)
    p.add_argument("--history", required=True)
    p.add_argument("--sample", default="")
    p.add_argument("--model", default="unknown")
    p.add_argument("--at", default="2026-10-29T00:00:00+00:00", help="the instant the mappings are read at, an input and never the clock")
    p.add_argument("--started", default="", help="when the run started, which with --at gives its duration")
    p.add_argument("--input-tokens", type=int, default=None)
    p.add_argument("--output-tokens", type=int, default=None)
    p.add_argument("--total-tokens", type=int, default=None, help="where only the total of read and written is known")
    a = p.parse_args(argv)
    started = datetime.fromisoformat(a.started).astimezone(timezone.utc) if a.started else None
    result = score(Path(a.run_dir), Path(a.pack), URIRef(a.pack_scheme), Path(a.history), Path(a.sample) if a.sample else None,
                   model=a.model, at=datetime.fromisoformat(a.at).astimezone(timezone.utc), started=started,
                   input_tokens=a.input_tokens, output_tokens=a.output_tokens, total_tokens=a.total_tokens)
    print(json.dumps({k: v for k, v in result.items() if k != "decisions"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
