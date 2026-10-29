# SPDX-License-Identifier: MPL-2.0
"""The history of proposals and their reviews (MORK README §5.18): each proposal run with the mappings it proposed, each
review's decision, and what the next proposer is told from them. It is one RDF graph, kept in a Turtle file, which a
deployment may instead keep in its graph store.

A review is made by a person, or by a reference pack when one exists. `review_against` compares a proposal with a pack
mapping by mapping, which is a heuristic: two mappings correspond when the first property of their source paths is the
same, and agree when they also write the same target terms. It suits a published standard whose pack was written by
hand, such as ODRL's, and it never replaces a person's review of a source with no pack."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import PROV, RDF, XSD

MORK = Namespace("http://www.nebularis.org/ontologies/Mork#")
DECISIONS = {"accepted": MORK.Accepted, "corrected": MORK.Corrected, "rejected": MORK.Rejected, "deferred": MORK.Deferred}


@dataclass(frozen=True)
class Signature:
    """What a mapping says, for comparing two schemes: the source it reads and the target terms it writes."""

    mapping: URIRef
    source: Optional[URIRef]        # the first property of its source path, or its source class
    targets: frozenset              # its T-Box types, R-Box property and A-Box individual
    label: str                      # how a reader names it


def signatures(g: Graph, scheme: URIRef, at: datetime) -> list[Signature]:
    """Each compiled mapping of a scheme, read with templates merged, as mork_rdf reads it."""
    from mork_rdf import paths
    from mork_rdf.read import read

    reading = read(g, scheme, at)
    out = []
    for node, spec in sorted(reading.specs.items(), key=lambda kv: str(kv[0])):
        if node in reading.templates and not spec.parents:
            continue
        path_text = next((str(p) for c in g.objects(node, MORK.mappingFor) for p in g.objects(c, MORK.path)), None) or spec.data_ref_text
        source = None
        if path_text:
            try:
                first = paths.parse(path_text, reading.prefixes)
                source = next(iter(_iris(first)), None)
            except paths.PathError:
                source = None
        elif spec.sources:
            source = spec.sources[0]
        targets = frozenset(set(spec.types) | set(spec.broader) | {v for v in spec.strata.rbox.values()} | {v for v in spec.strata.abox.values()})
        out.append(Signature(node, source, targets, str(node).rsplit("#", 1)[-1].rsplit("/", 1)[-1]))
    return out


def _iris(path) -> list:
    """The IRIs of a parsed path, depth first, so the first is the property it starts with."""
    from mork_rdf import paths

    if isinstance(path, paths.Iri):
        return [URIRef(path.value)]
    if isinstance(path, (paths.Inverse, paths.Mod)):
        return _iris(path.path)
    if isinstance(path, (paths.Seq, paths.Alt)):
        return [i for part in path.parts for i in _iris(part)]
    if isinstance(path, paths.NegSet):
        return [URIRef(iri) for _, iri in path.members]
    return []


class History:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.graph = Graph()
        self.graph.bind("mork", MORK)
        self.graph.bind("prov", PROV)
        if self.path.exists():
            self.graph.parse(self.path, format="turtle")

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.graph.serialize(format="turtle"), encoding="utf-8")

    def record_run(self, run: URIRef, proposal: Graph, scheme: URIRef, *, model: str, pack: str, source: Optional[URIRef],
                   at: datetime) -> list[URIRef]:
        """The run and every mapping of the proposal's scheme, each naming the run that generated it."""
        g = self.graph
        g += proposal
        g.add((run, RDF.type, MORK.ProposalRun))
        g.add((run, RDF.type, PROV.Activity))
        g.add((run, MORK.proposerModel, Literal(model)))
        g.add((run, MORK.teachingPackVersion, Literal(pack)))
        g.add((run, PROV.endedAtTime, Literal(at.isoformat(), datatype=XSD.dateTime)))
        if source is not None:
            g.add((run, MORK.proposedFor, source))
        mappings = sorted((m for m in proposal.subjects(MORK.mappingScheme, scheme) if isinstance(m, URIRef)), key=str)
        for m in mappings:
            g.add((m, PROV.wasGeneratedBy, run))
        return mappings

    def record_review(self, review: URIRef, mapping: URIRef, decision: str, *, reviewer: URIRef, at: datetime,
                      note: str = "", corrected_by: Optional[URIRef] = None) -> None:
        g = self.graph
        g.add((review, RDF.type, MORK.MappingReview))
        g.add((review, RDF.type, PROV.Activity))
        g.add((review, MORK.reviewOf, mapping))
        g.add((review, MORK.reviewDecision, DECISIONS[decision]))
        g.add((review, PROV.wasAssociatedWith, reviewer))
        g.add((review, PROV.endedAtTime, Literal(at.isoformat(), datatype=XSD.dateTime)))
        if note:
            g.add((review, MORK.reviewNote, Literal(note)))
        if corrected_by is not None:
            g.add((review, MORK.correctedBy, corrected_by))

    def decisions(self) -> dict:
        """Each reviewed mapping's latest decision, by its review's time."""
        g = self.graph
        latest: dict = {}
        for review in g.subjects(RDF.type, MORK.MappingReview):
            mapping, decision, when = g.value(review, MORK.reviewOf), g.value(review, MORK.reviewDecision), str(g.value(review, PROV.endedAtTime) or "")
            if mapping is not None and (mapping not in latest or when >= latest[mapping][1]):
                latest[mapping] = (decision, when, g.value(review, MORK.correctedBy), str(g.value(review, MORK.reviewNote) or ""))
        return {m: (d, c, n) for m, (d, _, c, n) in latest.items()}

    def lessons(self, sources: Graph) -> list[str]:
        """What the next proposer is told, one line for each reviewed mapping: the source term, the decision, the target
        terms accepted or refused, and the reviewer's note. `sources` labels the source terms."""
        out = []
        for mapping, (decision, corrected, note) in sorted(self.decisions().items(), key=lambda kv: str(kv[0])):
            kept = corrected if decision == MORK.Corrected and corrected is not None else mapping
            targets = sorted({str(o) for p in (MORK.exactTBoxMatch, MORK.exactRBoxMatch, MORK.inverseRBoxMatch, MORK.exactABoxMatch)
                              for o in self.graph.objects(kept, p)})
            what = str(decision).rsplit("#", 1)[-1].lower()
            out.append(f"{str(mapping).rsplit('#', 1)[-1]} | {what} | {', '.join(targets) or 'none'} | {note}")
        return out


def review_against(proposal: Graph, scheme: URIRef, reference: Graph, reference_scheme: URIRef, at: datetime) -> list[tuple]:
    """For each mapping of the proposal, (mapping, decision, corrected_by, note), decided by the reference pack."""
    theirs = signatures(reference, reference_scheme, at)
    by_source: dict = {}
    for s in theirs:
        by_source.setdefault(s.source, []).append(s)
    out = []
    for mine in signatures(proposal, scheme, at):
        same = by_source.get(mine.source, [])
        exact = [s for s in same if s.targets == mine.targets]
        if exact:
            out.append((mine.mapping, "accepted", None, f"as the pack's {exact[0].label}"))
        elif same and mine.targets & set().union(*(s.targets for s in same)):
            best = max(same, key=lambda s: len(s.targets & mine.targets))
            out.append((mine.mapping, "corrected", best.mapping, f"the pack's {best.label} writes {', '.join(sorted(str(t).rsplit('#', 1)[-1] for t in best.targets))}"))
        elif same:
            best = same[0]
            out.append((mine.mapping, "corrected", best.mapping, f"the pack maps this source with {best.label}, to {', '.join(sorted(str(t).rsplit('#', 1)[-1] for t in best.targets))}"))
        else:
            out.append((mine.mapping, "rejected", None, "the pack maps nothing from this source"))
    return out


def scores(decisions: Iterable[tuple]) -> dict:
    """How many of each decision, and the share accepted."""
    counts = {"accepted": 0, "corrected": 0, "rejected": 0, "deferred": 0}
    for _, decision, _, _ in decisions:
        counts[decision] += 1
    total = sum(counts.values())
    return {**counts, "total": total, "accepted_share": round(counts["accepted"] / total, 3) if total else 0.0}


def patterns(output: Graph, minted: str) -> set:
    """What a run wrote, as patterns that do not depend on minted names: each triple with every minted node replaced by
    its sorted types, so two schemes that write the same meaning under different names agree."""
    def shape(node):
        if isinstance(node, URIRef) and str(node).startswith(minted):
            return "[" + " ".join(sorted(str(t).rsplit("#", 1)[-1] for t in output.objects(node, RDF.type))) + "]"
        return str(node).rsplit("#", 1)[-1] if isinstance(node, URIRef) else str(node)
    return {(shape(s), str(p).rsplit("#", 1)[-1], shape(o)) for s, p, o in output if p != RDF.type} | \
           {(shape(s), "type", str(o).rsplit("#", 1)[-1]) for s, o in output.subject_objects(RDF.type)}


def agreement(proposed: set, reference: set) -> dict:
    """How far a proposal's output agrees with the reference's: the share of its patterns the reference also writes
    (precision), and the share of the reference's it writes (recall)."""
    both = proposed & reference
    return {"precision": round(len(both) / len(proposed), 3) if proposed else 0.0,
            "recall": round(len(both) / len(reference), 3) if reference else 0.0,
            "missing": sorted(reference - proposed)[:40], "extra": sorted(proposed - reference)[:40]}
