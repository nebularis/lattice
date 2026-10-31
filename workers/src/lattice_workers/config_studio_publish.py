# SPDX-License-Identifier: MPL-2.0
"""A publish job (ADR-A149): the version a unit of a workspace's saved part would be published as. It finds the unit by
its root, takes the aggregate the units table says it owns, digests it under ADR-A143 and names the version under ADR-A51,
`{lineage}/rev/1-{digest}`, with the root rewritten to the version and `fnd:hasIdentity` to the lineage. It writes nothing
but the job. Publishing the version is the service's and the writer's, after the job."""

from __future__ import annotations

import functools
import hashlib
from collections import deque
from typing import Callable

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF

from .config_studio_jobs import CST, _Result, catalogue

FND = "https://www.nebularis.org/neuro-semantic/lattice/foundation#"
HAS_IDENTITY = URIRef(FND + "hasIdentity")
PERSISTENT_IDENTITY = URIRef(FND + "PersistentIdentity")
PINS = CST.pins
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


def registry_graph(lineage: str) -> str:
    """The registry graph of `lineage`, as the writer names it."""
    return "urn:lattice:studio:pub:" + hashlib.sha256(lineage.encode("utf-8")).hexdigest()[:32]


def pin(content: Graph, root: URIRef, context: Graph, registry: Callable[[str], Graph]) -> Graph:
    """The aggregate with every reference to a published unit pinned (ADR-A149 decision 5). A reference to a lineage,
    followed, is rewritten to its current version, and a reference to a node a published version holds, such as a concept
    of a scheme's edition, is kept. Either way the root names the version with `cst:pins`. A reference to the root of a
    unit nobody has published fails, since a version may depend only on versions."""
    owned = set(content.subjects())
    versions: dict[URIRef, URIRef] = {}  # each version the context holds, by its lineage
    holders: dict[URIRef, URIRef] = {}  # the version each member of a version in the context belongs to
    for version, lineage in context.subject_objects(HAS_IDENTITY):
        versions[lineage] = version
    # A member of a version names it, as a concept names its scheme's edition with skos:inScheme.
    for version in set(versions.values()):
        for s in context.subjects(None, version):
            if isinstance(s, URIRef) and s != version:
                holders.setdefault(s, version)

    def current(lineage: URIRef) -> URIRef | None:
        if lineage in versions:
            return versions[lineage]
        v = registry(registry_graph(str(lineage))).value(lineage, CST.current)
        return v if isinstance(v, URIRef) else None

    out = Graph()
    for prefix, namespace in content.namespaces():
        out.bind(prefix, namespace, override=False)
    pins: set[URIRef] = set()
    for s, p, o in content:
        if isinstance(o, URIRef) and o not in owned and o != root and p != RDF.type:
            if (published := current(o)) is not None:
                o = published
                pins.add(published)
            elif o in holders:
                pins.add(holders[o])
            elif unit_of(context, o) is not None:
                raise ValueError(f"{root} refers to {o}, which is not published. Publish it first")
        out.add((s, p, o))
    for v in pins:
        out.add((root, PINS, v))
    return out


def prepare(job: URIRef, config: Graph, root: URIRef, context: Graph | None = None,
            registry: Callable[[str], Graph] = lambda iri: Graph()) -> Graph:
    """The job's result: the version as an N-Triples artefact grouped by its lineage, and the job's `cst:lineage`,
    `cst:version`, `cst:digest`, `cst:unitKind` and each `cst:pins`. `context` is the workspace's other parts and the
    versions it depends on, and `registry` reads a registry graph. A root that is no unit's, a lineage the studio mints
    itself, or a unit that refers to an unpublished one, fails."""
    if str(root).startswith("urn:lattice:studio:"):
        raise ValueError(f"{root} is named by the studio, so it cannot be a lineage")
    unit = unit_of(config, root)
    if unit is None:
        raise ValueError(f"{root} is the root of no unit of publication in this part")
    context = (context if context is not None else Graph()) + config
    content = pin(aggregate(config, root, unit), root, context, registry)
    version, full, published = version_of(content, root)
    result = _Result(job)
    result.artefact("version.nt", "application/n-triples", published.serialize(format="nt"), str(root))
    result.graph.add((job, CST.lineage, root))
    result.graph.add((job, CST.version, version))
    result.graph.add((job, CST.digest, Literal(full)))
    result.graph.add((job, CST.unitKind, unit))
    for v in sorted(content.objects(root, PINS)):
        result.graph.add((job, PINS, v))
    result.conforms(True)
    return result.graph
