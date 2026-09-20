"""
mork_communities/observation_materialiser.py

Materialises SectionObservation individuals from completed mapping runs
into the MORK graph. This is the bridge between completed Phase 2 results
and the community discovery input.

Typically called by the mapping orchestrator after a mapping run is
validated and accepted.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional, Set

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from mork_communities.namespaces import *
from mork_communities.graph_client import (
    MorkGraphClient,
    SectionObservationRecord,
)

logger = logging.getLogger(__name__)


class ObservationMaterialiser:
    """
    Extracts section observations from a completed mapping run
    and materialises them as SectionObservation individuals.
    """

    def __init__(
        self,
        graph: Graph,
        base_namespace: str = "http://www.nebularis.org/observations/",
    ):
        self._graph = graph
        self._ns = base_namespace
        self._client = MorkGraphClient(graph=graph)

    def extract_and_materialise(
        self,
        scheme_iri: URIRef,
        run_id: Optional[str] = None,
    ) -> List[SectionObservationRecord]:
        """
        Extract observations from a specific RepresentationScheme
        and materialise them.

        Parameters
        ----------
        scheme_iri : URIRef
            The RepresentationScheme that was just mapped.
        run_id : Optional[str]
            Identifier for this mapping run (for IRI minting).

        Returns
        -------
        List[SectionObservationRecord]
            The extracted and materialised observations.
        """
        if run_id is None:
            run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        g = self._graph
        observations = []

        sections = self._client._find_structural_sections(scheme_iri)

        for section_iri in sections:
            concepts = self._client._find_concepts_in_section(section_iri)

            if len(concepts) < 2:
                continue

            record = SectionObservationRecord(
                section_iri=section_iri,
                scheme_iri=scheme_iri,
                concepts=frozenset(concepts),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            observations.append(record)

            # Materialise
            section_local = (
                str(section_iri).split("/")[-1].split("#")[-1]
            )
            obs_iri = URIRef(
                f"{self._ns}{run_id}/{section_local}"
            )

            g.add((obs_iri, RDF.type, SECTION_OBSERVATION))
            g.add((obs_iri, OBSERVED_IN_SECTION, section_iri))
            g.add((obs_iri, OBSERVED_IN_SCHEME, scheme_iri))
            g.add(
                (
                    obs_iri,
                    OBSERVATION_TIMESTAMP,
                    Literal(record.timestamp, datatype=XSD.dateTime),
                )
            )
            for concept in concepts:
                g.add((obs_iri, OBSERVED_CONCEPT, concept))

        logger.info(
            "Materialised %d section observations for scheme %s",
            len(observations),
            scheme_iri,
        )
        return observations