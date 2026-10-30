# SPDX-License-Identifier: MPL-2.0
"""A communities baseline drawn from reviewed mappings of published standards (MORK README §5.18).

`mork_communities` reads a source as a tree of `mork:Representation` sections, as a document's schema holds fields.
An RDF source such as ODRL's is mapped by data concepts and paths instead, so this module observes the mappings
themselves: each root mapping of a scheme, with every mapping beneath it, is a section, and the source terms those
mappings read are the concepts observed in it. Community discovery runs over those observations, and each community's
projection records what its concepts were mapped to: the classes, the property under each parent class, and the shape
of each section as a DAG template. Target terms are named through shadow individuals, so the patterns stay in OWL 2 DL.

The result is deterministic for the same reviewed mappings: observations are sorted, communities are numbered by their
first member, and the scheme's version is a digest of its observations, never the clock. `mise run
mork:communities-baseline` writes it beside the trials."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, XSD

from .history import MORK, Signature, signatures

LATTICE = URIRef("https://www.nebularis.org/neuro-semantic/lattice/")


@dataclass(frozen=True)
class Section:
    """A root mapping of a scheme with every mapping beneath it, and the parent of each."""

    scheme: URIRef
    root: URIRef
    members: tuple  # Signature, root first
    parent: dict

    @property
    def concepts(self) -> frozenset:
        return frozenset(s.source for s in self.members if s.source is not None)


def sections(g: Graph, scheme: URIRef, keep: Callable[[URIRef], bool], at: datetime) -> list[Section]:
    """The sections of one scheme, of the mappings `keep` admits, such as those a review accepted."""
    sigs = {s.mapping: s for s in signatures(g, scheme, at) if keep(s.mapping)}
    parent = {}
    for m in sigs:
        p = g.value(m, MORK.compositeBroaderMapping) or next(g.subjects(MORK.compositeNarrowerMapping, m), None)
        if p in sigs:
            parent[m] = p

    def top(m):
        seen = set()
        while m in parent and m not in seen:
            seen.add(m)
            m = parent[m]
        return m

    groups: dict = defaultdict(list)
    for m in sorted(sigs, key=str):
        groups[top(m)].append(sigs[m])
    return [Section(scheme, root, tuple(sorted(ms, key=lambda s: (s.mapping != root, str(s.mapping)))), parent)
            for root, ms in sorted(groups.items(), key=lambda kv: str(kv[0]))]


def _kind(t: URIRef, vocabulary: Graph) -> URIRef:
    types = set(vocabulary.objects(t, RDF.type))
    return OWL.ObjectProperty if OWL.ObjectProperty in types else OWL.DatatypeProperty if OWL.DatatypeProperty in types else OWL.Class


_GENERIC = {URIRef("https://www.nebularis.org/neuro-semantic/lattice/instrument#Template")}


def _classes(s: Signature, g: Graph) -> list:
    """The classes a mapping writes, the most specific first: ins:Template, which every stated relation and term also
    is, after any other."""
    return sorted(g.objects(s.mapping, MORK.exactTBoxMatch), key=lambda c: (c in _GENERIC, str(c)))


def _properties(s: Signature, g: Graph) -> list:
    return sorted(set(g.objects(s.mapping, MORK.exactRBoxMatch)) | set(g.objects(s.mapping, MORK.inverseRBoxMatch)), key=str)


def build(sources: Iterable[tuple[Graph, URIRef, Callable[[URIRef], bool]]], vocabulary: Graph, base: str, at: datetime) -> Graph:
    """The baseline graph: the observations, the community scheme and each community's projection."""
    from mork_communities.communities import CommunityDiscovery, CommunityMaterialiser
    from mork_communities.graph_client import MorkGraphClient, SectionObservationRecord
    from mork_communities.namespaces import OBSERVATION_TIMESTAMP, OBSERVED_CONCEPT, OBSERVED_IN_SCHEME, OBSERVED_IN_SECTION, SECTION_OBSERVATION
    from mork_communities.projections import DAGTemplate, OntologicalProjection, ProjectionMaterialiser, PropertyProjection
    from mork_communities.shadow import ShadowOntologyBuilder

    found: list[tuple[Section, Graph]] = []
    for g, scheme, keep in sources:
        found += [(s, g) for s in sections(g, scheme, keep, at) if len(s.concepts) >= 2]
    found.sort(key=lambda sg: (str(sg[0].scheme), str(sg[0].root)))
    observations = [SectionObservationRecord(s.root, s.scheme, s.concepts, at.isoformat()) for s, _ in found]

    out = Graph()
    out.bind("mork", MORK)
    for s, _ in found:
        node = URIRef(f"{base}observation/{hashlib.sha256(f'{s.scheme} {s.root}'.encode()).hexdigest()[:16]}")
        out.add((node, RDF.type, SECTION_OBSERVATION))
        out.add((node, OBSERVED_IN_SECTION, s.root))
        out.add((node, OBSERVED_IN_SCHEME, s.scheme))
        out.add((node, OBSERVATION_TIMESTAMP, Literal(at.isoformat(), datatype=XSD.dateTime)))
        for c in sorted(s.concepts, key=str):
            out.add((node, OBSERVED_CONCEPT, c))

    scheme = CommunityDiscovery(MorkGraphClient(graph=Graph()), min_community_size=2).discover(observations=observations)
    # Numbered by first member and versioned by the observations, so the same reviews give the same baseline.
    scheme.communities.sort(key=lambda c: min(map(str, c.members)))
    for n, community in enumerate(scheme.communities):
        community.community_id = f"community-{n}"
    scheme.version = hashlib.sha256("\n".join(sorted(f"{o.scheme_iri} {o.section_iri} {' '.join(sorted(map(str, o.concepts)))}"
                                                    for o in observations)).encode()).hexdigest()[:16]
    CommunityMaterialiser(out, base).materialise_scheme(scheme)

    shadows = ShadowOntologyBuilder(out, URIRef(f"{base}lattice"), f"{base}shadow/")
    shadow = lambda t: shadows.get_or_create_shadow_for_entity(t, _kind(t, vocabulary), vocabulary)
    projections = ProjectionMaterialiser(out, base)
    for community in scheme.communities:
        mine = [(s, g) for s, g in found if s.concepts & community.member_set]
        classes: Counter = Counter()
        props: Counter = Counter()
        shapes: Counter = Counter()
        for s, g in mine:
            by_mapping = {m.mapping: m for m in s.members}
            for m in s.members:
                classes.update(_classes(m, g))
                parent = by_mapping.get(s.parent.get(m.mapping))
                parent_classes = _classes(parent, g) if parent is not None else []
                if m.source is not None and parent_classes:
                    for p in _properties(m, g):
                        props[(m.source, p, parent_classes[0])] += 1
            root_classes = _classes(s.members[0], g)
            if root_classes:
                children = tuple(sorted({(str(p), str(c)) for m in s.members[1:] for p in _properties(m, g) for c in (_classes(m, g)[:1] or [""])}))
                shapes[(root_classes[0], children)] += 1
        totals: Counter = Counter()
        for (concept, _, _), n in props.items():
            totals[concept] += n
        property_projections = {key: PropertyProjection(key[0], shadow(key[1]), shadow(key[2]), n, n / totals[key[0]])
                                for key, n in sorted(props.items(), key=lambda kv: tuple(map(str, kv[0])))}
        templates = []
        for (root_class, children), n in sorted(shapes.items(), key=lambda kv: (-kv[1], str(kv[0]))):
            written = {p for p, _ in children}
            kids = [pp for (_, p, _), pp in property_projections.items() if str(p) in written]
            templates.append(DAGTemplate(shadow(root_class), kids, n, hashlib.sha256(repr((str(root_class), children)).encode()).hexdigest()[:16]))
        projection = OntologicalProjection(LATTICE, {shadow(c): n for c, n in sorted(classes.items(), key=lambda kv: str(kv[0]))},
                                           list(property_projections.values()), templates)
        projections.materialise(community, projection)
    return out


def main(argv=None) -> int:
    """Writes the baseline from the ODRL pack and the accepted mappings of the ODRL and LegalRuleML trials."""
    import argparse

    import lattice_repo_catalogue as reader

    from .history import History
    from .server import _target

    parser = argparse.ArgumentParser(prog="mork_propose.baseline")
    parser.add_argument("--at", default="2026-10-30T00:00:00+00:00", help="the instant the mappings are read at, an input and never the clock")
    parser.add_argument("--out", default="", help="the file to write, by default communities-baseline.ttl beside the trials")
    a = parser.parse_args(argv)
    catalogue = reader.load()
    studio = catalogue.root / catalogue.area("contracts") / "config-studio"
    at = datetime.fromisoformat(a.at)
    sources = [(Graph().parse(studio / "odrl" / "odrl-instrument.mork.ttl"),
                URIRef("https://www.nebularis.org/neuro-semantic/lattice/config-studio/odrl-mapping#Scheme"), lambda m: True)]
    for path in (studio / "odrl" / "trial" / "history.ttl", studio / "legalruleml" / "trial" / "history.ttl"):
        history = History(path)
        accepted = {m for m, (d, _, _) in history.decisions().items() if d == MORK.Accepted}
        sources += [(history.graph, s, accepted.__contains__) for s in sorted(history.graph.subjects(RDF.type, MORK.MappingScheme), key=str)]
    g = build(sources, _target()[0], "https://www.nebularis.org/neuro-semantic/lattice/config-studio/communities/", at)
    out = a.out or str(studio / "communities-baseline.ttl")
    header = ("# SPDX-License-Identifier: CC-BY-SA-4.0\n# Generated by `mise run mork:communities-baseline` (tools/mork/src/mork_propose/baseline.py) from the ODRL pack\n"
              "# and the mappings the ODRL and LegalRuleML trials' reviews accepted. Do not edit by hand.\n")
    with open(out, "w", encoding="utf-8") as f:
        f.write(header + g.serialize(format="turtle"))
    print(f"wrote {out}: {len(g)} triples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
