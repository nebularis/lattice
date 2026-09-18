"""
mork_communities/type_compatibility.py

Type compatibility filter implementing the hard feasibility gate
from Chapter 2 of the algorithms paper and §5.2 of the reference
architecture.

The type filter is a hard gate: incompatible types produce distance ∞,
which no amount of other evidence can overcome.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import math
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD

from mork_communities.namespaces import (
    SHADOW_DOMAIN,
    SHADOW_RANGE,
    OWL_CLASS,
    OWL_OBJECT_PROPERTY,
    OWL_DATA_PROPERTY,
    IRI_PROP,
)

logger = logging.getLogger(__name__)

# Standard XSD type hierarchy for compatibility checking
XSD_NUMERIC = {XSD.decimal, XSD.float, XSD.double, XSD.integer,
               XSD.long, XSD.int, XSD.short, XSD.byte,
               XSD.nonNegativeInteger, XSD.positiveInteger}
XSD_STRING = {XSD.string, XSD.normalizedString, XSD.token, XSD.Name,
              XSD.anyURI}
XSD_DATE = {XSD.date, XSD.dateTime, XSD.time, XSD.gYear, XSD.gYearMonth}
XSD_BOOLEAN = {XSD.boolean}


@dataclass(frozen=True)
class TypeProfile:
    """Expected type profile for a concept based on ontology range declarations."""
    concept_iri: URIRef
    expected_types: Set[URIRef]  # XSD types or OWL classes
    is_object_property: bool = False
    is_data_property: bool = True


class TypeCompatibilityEngine:
    """
    Computes type compatibility distance between source data types
    and target ontology range declarations.

    d_type = 0   : perfect match
    d_type = 0.5 : compatible with minor coercion
    d_type = ∞   : incompatible (eliminates candidate)
    """

    # Source type to XSD type mapping
    SOURCE_TYPE_MAP = {
        "decimal": XSD.decimal,
        "float": XSD.float,
        "double": XSD.double,
        "integer": XSD.integer,
        "int": XSD.integer,
        "long": XSD.long,
        "string": XSD.string,
        "text": XSD.string,
        "varchar": XSD.string,
        "char": XSD.string,
        "date": XSD.date,
        "datetime": XSD.dateTime,
        "timestamp": XSD.dateTime,
        "boolean": XSD.boolean,
        "bool": XSD.boolean,
        "uri": XSD.anyURI,
        "enum": XSD.string,  # enums treated as strings
    }

    # Type compatibility matrix
    # (source_group, target_group) -> distance
    INFINITY = float("inf")

    def __init__(
        self,
        mork_graph: Graph,
        shadow_builder=None,
    ):
        self._graph = mork_graph
        self._shadow = shadow_builder
        self._type_profiles: Dict[URIRef, TypeProfile] = {}

    def build_type_profiles(self) -> None:
        """
        Build type profiles for all concepts from shadow ontology
        domain/range declarations.
        """
        g = self._graph

        # For each shadow data property, extract range
        for prop_shadow in g.subjects(RDF.type, OWL_DATA_PROPERTY):
            range_vals = set(g.objects(prop_shadow, SHADOW_RANGE))
            expected = set()
            for rv in range_vals:
                # Get the IRI of the range entity
                for iri_lit in g.objects(rv, IRI_PROP):
                    iri = URIRef(str(iri_lit))
                    expected.add(iri)
            if not expected:
                # Default to string if no range declared
                expected.add(XSD.string)

            # Get the domain entity IRI for context
            iri_lit = next(g.objects(prop_shadow, IRI_PROP), None)
            if iri_lit:
                self._type_profiles[URIRef(str(iri_lit))] = TypeProfile(
                    concept_iri=URIRef(str(iri_lit)),
                    expected_types=expected,
                    is_data_property=True,
                )

        # For object properties
        for prop_shadow in g.subjects(RDF.type, OWL_OBJECT_PROPERTY):
            iri_lit = next(g.objects(prop_shadow, IRI_PROP), None)
            if iri_lit:
                range_vals = set()
                for rv in g.objects(prop_shadow, SHADOW_RANGE):
                    for r_iri in g.objects(rv, IRI_PROP):
                        range_vals.add(URIRef(str(r_iri)))

                self._type_profiles[URIRef(str(iri_lit))] = TypeProfile(
                    concept_iri=URIRef(str(iri_lit)),
                    expected_types=range_vals,
                    is_object_property=True,
                    is_data_property=False,
                )

    def compute_type_distance(
        self,
        source_type: str,
        target_property_iri: URIRef,
    ) -> float:
        """
        Compute type compatibility distance.

        Parameters
        ----------
        source_type : str
            The source field's data type (e.g., "decimal", "string", "date").
        target_property_iri : URIRef
            The target ontology property IRI.

        Returns
        -------
        float
            0.0 = perfect match, 0.5 = compatible with coercion, inf = incompatible.
        """
        source_xsd = self.SOURCE_TYPE_MAP.get(source_type.lower())
        if source_xsd is None:
            # Unknown source type — don't penalise
            return 0.5

        profile = self._type_profiles.get(target_property_iri)
        if profile is None:
            # No type info available — neutral
            return 0.25

        if profile.is_object_property:
            # Object properties expect individuals, not literals
            if source_xsd in XSD_STRING | {XSD.anyURI}:
                return 0.5  # String could be a reference
            return self.INFINITY

        # Check direct match
        for expected in profile.expected_types:
            if source_xsd == expected:
                return 0.0
            if self._types_compatible(source_xsd, expected):
                return 0.5

        return self.INFINITY

    def filter_candidates(
        self,
        candidates: List[Tuple[URIRef, float]],
        source_type: str,
        property_lookup: Optional[Dict[URIRef, URIRef]] = None,
    ) -> List[Tuple[URIRef, float]]:
        """
        Filter candidates by type compatibility.
        Removes candidates with type distance = ∞.

        Parameters
        ----------
        candidates : List[Tuple[URIRef, float]]
            (concept_iri, score) pairs.
        source_type : str
            The field's data type.
        property_lookup : Optional
            Mapping from concept_iri to target property IRI.

        Returns
        -------
        List[Tuple[URIRef, float]]
            Filtered candidates (incompatible removed).
        """
        if property_lookup is None:
            return candidates

        filtered = []
        for concept_iri, score in candidates:
            prop_iri = property_lookup.get(concept_iri)
            if prop_iri is None:
                filtered.append((concept_iri, score))
                continue

            d_type = self.compute_type_distance(source_type, prop_iri)
            if d_type < self.INFINITY:
                # Adjust score by type compatibility
                type_factor = math.exp(-d_type) if d_type > 0 else 1.0
                filtered.append((concept_iri, score * type_factor))
            else:
                logger.debug(
                    "Type filter eliminated %s for property %s (source type: %s)",
                    concept_iri, prop_iri, source_type,
                )

        return filtered

    def _types_compatible(self, source: URIRef, target: URIRef) -> bool:
        """Check if source type is compatible with target type (with coercion)."""
        # Numeric types are inter-compatible
        if source in XSD_NUMERIC and target in XSD_NUMERIC:
            return True
        # String types are inter-compatible
        if source in XSD_STRING and target in XSD_STRING:
            return True
        # Integer to decimal
        if source == XSD.integer and target == XSD.decimal:
            return True
        # String to date (parse attempt)
        if source in XSD_STRING and target in XSD_DATE:
            return True
        # String to enum
        if source in XSD_STRING and target in XSD_STRING:
            return True
        return False
