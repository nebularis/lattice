# SPDX-License-Identifier: MPL-2.0

"""Read-set freshness and minimal regeneration planning.

This module is intentionally independent of RDF storage. The compiler already
records canonical digests in ``ReadSetRecord`` values. Callers provide current
digests for the same ``(readSourceKind, source)`` keys, and this module reports
staleness or propagates an invalidation through ``srf:SurfaceSource`` entries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Set, Tuple

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from .compile import ReadSetRecord
from .namespaces import MORK, SRF

ReadSetKey = Tuple[str, str]
EXE = Namespace("https://www.nebularis.org/neuro-semantic/lattice/executable#")


@dataclass(frozen=True)
class ReadSetChange:
    """One recorded input whose current digest differs or is unavailable."""

    kind: str
    source: str
    recorded_digest: str
    current_digest: str | None


@dataclass(frozen=True)
class FreshnessReport:
    """Freshness result for one generated surface."""

    changes: Tuple[ReadSetChange, ...]

    @property
    def fresh(self) -> bool:
        return not self.changes


@dataclass(frozen=True)
class RegenerationPlan:
    """Minimal regeneration scope and the reasons that produced it."""

    surfaces: Tuple[str, ...]
    mappings: Tuple[str, ...]
    artefacts: Tuple[str, ...]
    reasons: Tuple[str, ...]


def read_set_key(kind: URIRef, source: URIRef) -> ReadSetKey:
    """Return the stable key used by recorded and current read-set digests."""
    return str(kind), str(source)


def compare_read_set(
    read_set: Sequence[ReadSetRecord],
    current_digests: Mapping[ReadSetKey, str],
) -> FreshnessReport:
    """Compare recorded read-set digests with a caller's current digest map.

    A missing current digest is stale rather than implicitly fresh. This keeps
    invalidation conservative when a source was deleted or the caller has not
    yet computed its canonical digest.
    """
    changes = []
    for entry in read_set:
        key = read_set_key(entry.kind, entry.source)
        current = current_digests.get(key)
        if current != entry.digest:
            changes.append(
                ReadSetChange(
                    kind=key[0],
                    source=key[1],
                    recorded_digest=entry.digest,
                    current_digest=current,
                )
            )
    return FreshnessReport(tuple(changes))


def read_set_from_manifest(
    manifest: Graph,
    surface: URIRef | None = None,
) -> Tuple[ReadSetRecord, ...]:
    """Extract recorded read-set entries from a generated manifest graph.

    If ``surface`` is omitted, the manifest must contain exactly one generated
    surface record. Missing fields are rejected rather than treated as fresh.
    """
    records = list(manifest.subjects(RDF.type, SRF.GeneratedSurface))
    if surface is None:
        if len(records) != 1:
            raise ValueError(
                f"manifest contains {len(records)} generated surfaces; specify one"
            )
        surface = records[0]
    elif (surface, RDF.type, SRF.GeneratedSurface) not in manifest:
        raise ValueError(f"{surface} is not a generated surface in the manifest")

    entries = []
    for entry in manifest.objects(surface, SRF.hasReadSetEntry):
        source = manifest.value(entry, SRF.readsSource)
        kind = manifest.value(entry, SRF.readSourceKind)
        digest = manifest.value(entry, SRF.readHash)
        if not isinstance(source, URIRef) or not isinstance(kind, URIRef) or digest is None:
            raise ValueError(f"read-set entry {entry} is incomplete")
        entries.append(ReadSetRecord(kind=kind, source=source, digest=str(digest)))
    return tuple(sorted(entries, key=lambda item: item.key()))


def impacted_surfaces(
    manifests: Mapping[str, Sequence[ReadSetRecord]],
    changed_sources: Set[str],
) -> Tuple[str, ...]:
    """Return the minimal transitive regeneration scope.

    ``changed_sources`` contains source IRIs or surface record IRIs known to
    have changed. A manifest is impacted when it reads one of those sources,
    directly or through an already impacted surface. Cycles are handled by the
    fixed-point traversal and do not cause unbounded recursion.
    """
    impacted: Set[str] = set()
    changed = set(changed_sources)

    while True:
        newly_impacted = set()
        for surface, read_set in manifests.items():
            if surface in impacted:
                continue
            if any(str(entry.source) in changed or str(entry.source) in impacted
                   for entry in read_set):
                newly_impacted.add(surface)
        if not newly_impacted:
            return tuple(sorted(impacted))
        impacted.update(newly_impacted)


def impacted_mappings(
    mapping_graph: Graph,
    changed_sources: Set[str],
) -> Tuple[str, ...]:
    """Return mappings affected by changed Surface sources or dependencies.

    A mapping is directly affected when ``mork:mappingFor`` names a changed
    source. Dependency edges then propagate impact to mappings that depend on
    an affected mapping. This keeps the Surface-to-MORK boundary explicit
    without requiring the invalidation planner to understand backend syntax.
    """
    impacted: Set[URIRef] = {
        mapping
        for mapping, source in mapping_graph.subject_objects(MORK.mappingFor)
        if str(source) in changed_sources and isinstance(mapping, URIRef)
    }

    while True:
        newly_impacted = {
            mapping
            for mapping, dependency in mapping_graph.subject_objects(MORK.dependsOnMapping)
            if dependency in impacted and isinstance(mapping, URIRef)
        } - impacted
        if not newly_impacted:
            return tuple(sorted((str(mapping) for mapping in impacted)))
        impacted.update(newly_impacted)


def impacted_artefacts(
    graph: Graph,
    changed_mappings: Set[str],
) -> Tuple[str, ...]:
    """Return generated artefacts produced by impacted mappings or plans."""
    artefacts: Set[str] = {
        str(artefact)
        for artefact, mapping in graph.subject_objects(MORK.generatedBy)
        if str(mapping) in changed_mappings
    }
    for plan, mapping in graph.subject_objects(EXE.compiledFromMapping):
        if str(mapping) not in changed_mappings:
            continue
        artefacts.update(str(artefact) for artefact in graph.objects(plan, EXE.producesArtefact))
    return tuple(sorted(artefacts))


def plan_regeneration(
    manifests: Mapping[str, Sequence[ReadSetRecord]],
    mapping_graph: Graph,
    *,
    changed_sources: Optional[Set[str]] = None,
    changed_profiles: Optional[Set[str]] = None,
    changed_mappings: Optional[Set[str]] = None,
    canonicalisation_changed: bool = False,
) -> RegenerationPlan:
    """Compute a dependency-scoped regeneration plan.

    Profile or canonicalisation changes intentionally widen the scope to every
    known surface, mapping, and generated artefact. Ordinary source and
    mapping changes remain dependency-scoped.
    """
    changed_sources = set(changed_sources or ())
    changed_profiles = set(changed_profiles or ())
    changed_mappings = set(changed_mappings or ())
    all_surfaces = set(manifests)
    all_mappings = {
        str(mapping)
        for mapping in mapping_graph.subjects(MORK.mappingFor, None)
        if isinstance(mapping, URIRef)
    }
    global_reasons = []
    if changed_profiles:
        global_reasons.append("profile-change")
    if canonicalisation_changed:
        global_reasons.append("canonicalisation-change")

    if global_reasons:
        surfaces = tuple(sorted(all_surfaces))
        mappings = tuple(sorted(all_mappings))
        artefacts = impacted_artefacts(mapping_graph, set(mappings))
        if not artefacts:
            artefacts = tuple(
                sorted(
                    str(artefact)
                    for artefact, _ in mapping_graph.subject_objects(MORK.generatedBy)
                )
            )
        return RegenerationPlan(surfaces, mappings, artefacts, tuple(global_reasons))

    surfaces = impacted_surfaces(manifests, set(changed_sources))
    mapping_sources = set(changed_sources) | set(surfaces) | set(changed_mappings)
    mappings = tuple(sorted(set(impacted_mappings(mapping_graph, mapping_sources)) | set(changed_mappings)))
    artefacts = impacted_artefacts(mapping_graph, set(mappings))
    reasons = []
    if changed_sources:
        reasons.append("source-change")
    if changed_mappings:
        reasons.append("mapping-change")
    return RegenerationPlan(surfaces, mappings, artefacts, tuple(reasons))
