"""
mork_communities/validation.py

SHACL-based validation of community and projection graph structures.

Provides programmatic validation equivalent to the SHACL shapes
defined in §10.13 of the addendum, for use when a SHACL engine
is not available or for fast pre-validation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from mork_communities.namespaces import *

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation issue."""

    severity: str  # "violation", "warning", "info"
    focus_node: URIRef
    path: Optional[URIRef]
    message: str
    shape_name: str


class CommunityValidator:
    """
    Validates community and projection graph structures against
    the GCI axioms and SHACL shapes from §10.4.4, §10.6.5, §10.13.
    """

    def __init__(self, graph: Graph):
        self._graph = graph

    def validate_all(self) -> List[ValidationIssue]:
        """Run all validation checks."""
        issues = []
        issues.extend(self._validate_communities())
        issues.extend(self._validate_memberships())
        issues.extend(self._validate_observations())
        issues.extend(self._validate_projections())
        issues.extend(self._validate_property_projections())
        issues.extend(self._validate_dag_templates())
        issues.extend(self._validate_community_schemes())
        return issues

    def _validate_communities(self) -> List[ValidationIssue]:
        """Validate SemanticCommunity well-formedness (10.4a-b)."""
        g = self._graph
        issues = []

        for comm in g.subjects(RDF.type, SEMANTIC_COMMUNITY):
            # 10.4a: Must belong to a CommunityScheme
            schemes = list(g.objects(comm, COMMUNITY_SCHEME_PROP))
            if not schemes:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=comm,
                        path=COMMUNITY_SCHEME_PROP,
                        message="SemanticCommunity must belong to a CommunityScheme",
                        shape_name="SemanticCommunityShape",
                    )
                )

            # 10.4b: Must have at least 2 memberships
            memberships = list(g.objects(comm, HAS_COMMUNITY_MEMBERSHIP))
            if len(memberships) < 2:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=comm,
                        path=HAS_COMMUNITY_MEMBERSHIP,
                        message=f"SemanticCommunity must have ≥2 members, has {len(memberships)}",
                        shape_name="SemanticCommunityShape",
                    )
                )

            # Coherence in [0, 1]
            for coh in g.objects(comm, COMMUNITY_COHERENCE):
                val = float(coh)
                if val < 0.0 or val > 1.0:
                    issues.append(
                        ValidationIssue(
                            severity="violation",
                            focus_node=comm,
                            path=COMMUNITY_COHERENCE,
                            message=f"Coherence {val} not in [0, 1]",
                            shape_name="SemanticCommunityShape",
                        )
                    )

            # Observation count ≥ 1
            obs_counts = list(g.objects(comm, COMMUNITY_OBSERVATION_COUNT))
            if not obs_counts:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=comm,
                        path=COMMUNITY_OBSERVATION_COUNT,
                        message="Community must have observation count",
                        shape_name="SemanticCommunityShape",
                    )
                )
            else:
                for oc in obs_counts:
                    if int(oc) < 1:
                        issues.append(
                            ValidationIssue(
                                severity="violation",
                                focus_node=comm,
                                path=COMMUNITY_OBSERVATION_COUNT,
                                message="Observation count must be ≥ 1",
                                shape_name="SemanticCommunityShape",
                            )
                        )

        return issues

    def _validate_memberships(self) -> List[ValidationIssue]:
        """Validate CommunityMembership well-formedness (10.4c-d)."""
        g = self._graph
        issues = []

        for mem in g.subjects(RDF.type, COMMUNITY_MEMBERSHIP):
            # 10.4c: Exactly one memberConcept
            concepts = list(g.objects(mem, MEMBER_CONCEPT))
            if len(concepts) != 1:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=mem,
                        path=MEMBER_CONCEPT,
                        message=f"CommunityMembership must reference exactly 1 DataConcept, has {len(concepts)}",
                        shape_name="CommunityMembershipShape",
                    )
                )

            # 10.4d: Must have weight
            weights = list(g.objects(mem, COMMUNITY_MEMBER_WEIGHT))
            if not weights:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=mem,
                        path=COMMUNITY_MEMBER_WEIGHT,
                        message="CommunityMembership must have a weight",
                        shape_name="CommunityMembershipShape",
                    )
                )
            else:
                for w in weights:
                    val = float(w)
                    if val < 0.0 or val > 1.0:
                        issues.append(
                            ValidationIssue(
                                severity="violation",
                                focus_node=mem,
                                path=COMMUNITY_MEMBER_WEIGHT,
                                message=f"Weight {val} not in [0, 1]",
                                shape_name="CommunityMembershipShape",
                            )
                        )

        return issues

    def _validate_observations(self) -> List[ValidationIssue]:
        """Validate SectionObservation well-formedness (10.4e-g)."""
        g = self._graph
        issues = []

        for obs in g.subjects(RDF.type, SECTION_OBSERVATION):
            # 10.4e: Must reference a section
            sections = list(g.objects(obs, OBSERVED_IN_SECTION))
            if not sections:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=obs,
                        path=OBSERVED_IN_SECTION,
                        message="SectionObservation must reference a section",
                        shape_name="SectionObservationShape",
                    )
                )

            # 10.4f: Must reference a scheme
            schemes = list(g.objects(obs, OBSERVED_IN_SCHEME))
            if not schemes:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=obs,
                        path=OBSERVED_IN_SCHEME,
                        message="SectionObservation must reference a RepresentationScheme",
                        shape_name="SectionObservationShape",
                    )
                )

            # 10.4g: Must have ≥ 1 observed concept
            concepts = list(g.objects(obs, OBSERVED_CONCEPT))
            if len(concepts) < 1:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=obs,
                        path=OBSERVED_CONCEPT,
                        message="SectionObservation must have ≥1 observed concept",
                        shape_name="SectionObservationShape",
                    )
                )

        return issues

    def _validate_projections(self) -> List[ValidationIssue]:
        """Validate OntologicalProjection well-formedness (10.6a-b)."""
        g = self._graph
        issues = []

        for proj in g.subjects(RDF.type, ONTOLOGICAL_PROJECTION):
            # 10.6a: Must reference target ontology
            targets = list(g.objects(proj, PROJECTION_TARGET_ONTOLOGY))
            if not targets:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=proj,
                        path=PROJECTION_TARGET_ONTOLOGY,
                        message="OntologicalProjection must reference a target OntologicalScheme",
                        shape_name="OntologicalProjectionShape",
                    )
                )

            # 10.6b: Must have ≥ 1 projected class
            classes = list(g.objects(proj, PROJECTED_CLASS))
            if not classes:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=proj,
                        path=PROJECTED_CLASS,
                        message="OntologicalProjection must have ≥1 projected class",
                        shape_name="OntologicalProjectionShape",
                    )
                )

        return issues

    def _validate_property_projections(self) -> List[ValidationIssue]:
        """Validate PropertyProjection well-formedness (10.6c-e)."""
        g = self._graph
        issues = []

        for pp in g.subjects(RDF.type, PROPERTY_PROJECTION):
            # 10.6c: Exactly one projectedConcept
            concepts = list(g.objects(pp, PROJECTED_CONCEPT))
            if len(concepts) != 1:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=pp,
                        path=PROJECTED_CONCEPT,
                        message=f"PropertyProjection must have exactly 1 concept, has {len(concepts)}",
                        shape_name="PropertyProjectionShape",
                    )
                )

            # 10.6d: Exactly one projectedProperty
            props = list(g.objects(pp, PROJECTED_PROPERTY))
            if len(props) != 1:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=pp,
                        path=PROJECTED_PROPERTY,
                        message=f"PropertyProjection must have exactly 1 property, has {len(props)}",
                        shape_name="PropertyProjectionShape",
                    )
                )

            # 10.6e: Exactly one projectedParentClass
            parents = list(g.objects(pp, PROJECTED_PARENT_CLASS))
            if len(parents) != 1:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=pp,
                        path=PROJECTED_PARENT_CLASS,
                        message=f"PropertyProjection must have exactly 1 parent class, has {len(parents)}",
                        shape_name="PropertyProjectionShape",
                    )
                )

            # Confidence in [0, 1]
            for conf in g.objects(pp, PROPERTY_PROJECTION_CONFIDENCE):
                val = float(conf)
                if val < 0.0 or val > 1.0:
                    issues.append(
                        ValidationIssue(
                            severity="violation",
                            focus_node=pp,
                            path=PROPERTY_PROJECTION_CONFIDENCE,
                            message=f"Confidence {val} not in [0, 1]",
                            shape_name="PropertyProjectionShape",
                        )
                    )

            # Frequency ≥ 1
            for freq in g.objects(pp, PROPERTY_PROJECTION_FREQUENCY):
                if int(freq) < 1:
                    issues.append(
                        ValidationIssue(
                            severity="violation",
                            focus_node=pp,
                            path=PROPERTY_PROJECTION_FREQUENCY,
                            message="Frequency must be ≥ 1",
                            shape_name="PropertyProjectionShape",
                        )
                    )

        return issues

    def _validate_dag_templates(self) -> List[ValidationIssue]:
        """Validate DAGTemplate well-formedness (10.6f)."""
        g = self._graph
        issues = []

        for dt in g.subjects(RDF.type, DAG_TEMPLATE):
            # 10.6f: Exactly one root
            roots = list(g.objects(dt, DAG_TEMPLATE_ROOT))
            if len(roots) != 1:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=dt,
                        path=DAG_TEMPLATE_ROOT,
                        message=f"DAGTemplate must have exactly 1 root, has {len(roots)}",
                        shape_name="DAGTemplateShape",
                    )
                )

            # Must have ≥ 1 child
            children = list(g.objects(dt, DAG_TEMPLATE_CHILD))
            if len(children) < 1:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=dt,
                        path=DAG_TEMPLATE_CHILD,
                        message="DAGTemplate must have ≥1 child",
                        shape_name="DAGTemplateShape",
                    )
                )

            # Frequency ≥ 1
            for freq in g.objects(dt, DAG_TEMPLATE_FREQUENCY):
                if int(freq) < 1:
                    issues.append(
                        ValidationIssue(
                            severity="violation",
                            focus_node=dt,
                            path=DAG_TEMPLATE_FREQUENCY,
                            message="Frequency must be ≥ 1",
                            shape_name="DAGTemplateShape",
                        )
                    )

        return issues

    def _validate_community_schemes(self) -> List[ValidationIssue]:
        """Validate CommunityScheme well-formedness."""
        g = self._graph
        issues = []

        for cs in g.subjects(RDF.type, COMMUNITY_SCHEME):
            versions = list(g.objects(cs, COMMUNITY_SCHEME_VERSION))
            if not versions:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=cs,
                        path=COMMUNITY_SCHEME_VERSION,
                        message="CommunityScheme must have a version",
                        shape_name="CommunitySchemeShape",
                    )
                )

            algorithms = list(g.objects(cs, DETECTION_ALGORITHM))
            if not algorithms:
                issues.append(
                    ValidationIssue(
                        severity="violation",
                        focus_node=cs,
                        path=DETECTION_ALGORITHM,
                        message="CommunityScheme must record the detection algorithm",
                        shape_name="CommunitySchemeShape",
                    )
                )

        return issues