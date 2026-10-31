# SPDX-License-Identifier: MPL-2.0
"""A publish job (ADR-A149): the version a unit of a workspace's saved part would be published as. It finds the unit by
its root, takes the aggregate the units table says it owns, digests it under ADR-A143 and names the version under ADR-A51,
`{lineage}/rev/1-{digest}`, with the root rewritten to the version and `fnd:hasIdentity` to the lineage. It writes nothing
but the job. Publishing the version is the service's and the writer's, after the job."""

from __future__ import annotations

import functools
from collections import deque

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF

from .config_studio_jobs import CST, _Result, catalogue

FND = "https://www.nebularis.org/neuro-semantic/lattice/foundation#"
HAS_IDENTITY = URIRef(FND + "hasIdentity")
PERSISTENT_IDENTITY = URIRef(FND + "PersistentIdentity")
# The digest's width in the version's IRI, as a generated document's version IRI has it (STD-234).
WIDTH = 16


@functools.lru_cache(maxsize=1)
def units() -> Graph:
    """The units table, `contracts/config-studio/publication-units.ttl`."""
    c = catalogue()
    return Graph().parse(c.root / c.area("contracts") / "config-studio" / "publication-units.ttl", format="turtle")


def unit_of(g: Graph, root: URIRef) -> URIRef | None:
    """The unit whose root class `root` has in `g`, if any."""
    table = units()
    types = set(g.objects(root, RDF.type))
    return next((u for u in sorted(table.subjects(RDF.type, CST.PublicationUnit)) if types & set(table.objects(u, CST.rootClass))), None)


def aggregate(g: Graph, root: URIRef, unit: URIRef) -> Graph:
    """The root, the nodes naming it by the unit's member property, the blank nodes reached from either, and the named
    nodes minted under the root's IRI, with every triple of which one of them is the subject."""
    member = units().value(unit, CST.memberBy)
    owned = {root} | ({s for s in g.subjects(member, root) if isinstance(s, URIRef)} if member is not None else set())
    owned |= {s for s in g.subjects() if isinstance(s, URIRef) and (str(s).startswith(str(root) + "/") or str(s).startswith(str(root) + "#"))}
    pending = deque(owned)
    while pending:
        node = pending.popleft()
        for o in g.objects(node, None):
            if isinstance(o, BNode) and o not in owned:
                owned.add(o)
                pending.append(o)
    out = Graph()
    for prefix, namespace in g.namespaces():
        out.bind(prefix, namespace, override=False)
    for node in owned:
        for p, o in g.predicate_objects(node):
            out.add((node, p, o))
    return out


def version_of(content: Graph, lineage: URIRef) -> tuple[URIRef, str, Graph]:
    """The version's IRI, its digest and its graph: `content` with the lineage rewritten to the version, which names its
    identity. The digest is over `content` as drafted, so the same content always names the same version."""
    from mork_rdf.compile import digest

    full = digest(content)
    version = URIRef(f"{lineage}/rev/1-{full[:WIDTH]}")
    published = Graph()
    for prefix, namespace in content.namespaces():
        published.bind(prefix, namespace, override=False)
    swap = lambda t: version if t == lineage else t
    for s, p, o in content:
        published.add((swap(s), p, swap(o)))
    published.add((version, HAS_IDENTITY, lineage))
    published.add((lineage, RDF.type, PERSISTENT_IDENTITY))
    return version, full, published


def prepare(job: URIRef, config: Graph, root: URIRef) -> Graph:
    """The job's result: the version as an N-Triples artefact grouped by its lineage, and the job's `cst:lineage`,
    `cst:version`, `cst:digest` and `cst:unitKind`. A root that is no unit's, or a lineage the studio mints itself, fails."""
    if str(root).startswith("urn:lattice:studio:"):
        raise ValueError(f"{root} is named by the studio, so it cannot be a lineage")
    unit = unit_of(config, root)
    if unit is None:
        raise ValueError(f"{root} is the root of no unit of publication in this part")
    version, full, published = version_of(aggregate(config, root, unit), root)
    result = _Result(job)
    result.artefact("version.nt", "application/n-triples", published.serialize(format="nt"), str(root))
    result.graph.add((job, CST.lineage, root))
    result.graph.add((job, CST.version, version))
    result.graph.add((job, CST.digest, Literal(full)))
    result.graph.add((job, CST.unitKind, unit))
    result.conforms(True)
    return result.graph
