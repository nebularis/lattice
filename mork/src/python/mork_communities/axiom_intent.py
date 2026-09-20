"""
mork_communities/axiom_intent.py

Axiom Intent Profiler and Alignment Scorer.

Implements §3.2-3.3 (Definition 3.3), Chapter 7 of the algorithms paper,
and §5.4 of the reference architecture.

Extracts axiom intent profiles from OWL ontologies and scores candidate
mappings against the target class's declared requirements.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD

from mork_communities.namespaces import (
    SHADOW_DOMAIN,
    SHADOW_RANGE,
    SHADOW_SUB_CLASS_OF,
    SHADOW_OF,
    OWL_CLASS,
    OWL_OBJECT_PROPERTY,
    OWL_DATA_PROPERTY,
    IRI_PROP,
)

logger = logging.getLogger(__name__)


class AxiomIntentType(Enum):
    """Classification of axiom intents (Table in §3.2)."""
    DEFINITIONAL = "definitional"       # From equivalence axiom
    EXISTENTIAL = "existential"         # From existential restriction in GCI
    UNIVERSAL = "universal"             # Universal restriction ∀R.C
    CARDINALITY_MIN = "cardinality_min" # Min cardinality
    CARDINALITY_MAX = "cardinality_max" # Max cardinality
    CARDINALITY_EXACT = "cardinality_exact"  # Exact cardinality
    DISJOINTNESS = "disjointness"       # Disjoint with another class


@dataclass(frozen=True)
class AxiomIntent:
    """A single axiom intent from the ontology."""
    intent_type: AxiomIntentType
    property_iri: Optional[URIRef] = None
    filler_type: Optional[URIRef] = None
    cardinality_value: Optional[int] = None
    disjoint_class: Optional[URIRef] = None


@dataclass
class AxiomIntentProfile:
    """
    The ontological intent profile ℐ(Ĉ) for a class.
    Implements Definition 3.3 of the foundations paper.
    """
    class_iri: URIRef
    definitional: Set[AxiomIntent] = field(default_factory=set)
    existential: Set[AxiomIntent] = field(default_factory=set)
    constraints: Set[AxiomIntent] = field(default_factory=set)
    exclusions: Set[AxiomIntent] = field(default_factory=set)

    @property
    def all_intents(self) -> Set[AxiomIntent]:
        return self.definitional | self.existential | self.constraints | self.exclusions

    @property
    def required_properties(self) -> Set[URIRef]:
        """Properties that MUST be present (definitional + existential)."""
        return {
            ai.property_iri
            for ai in self.definitional | self.existential
            if ai.property_iri is not None
        }

    @property
    def definitional_properties(self) -> Set[URIRef]:
        """Properties in the equivalence axiom."""
        return {
            ai.property_iri
            for ai in self.definitional
            if ai.property_iri is not None
        }


class AxiomIntentProfiler:
    """
    Extracts axiom intent profiles from an OWL ontology.

    Analyses equivalence axioms, GCIs, restrictions, disjointness
    declarations, and cardinality constraints to build a complete
    intent profile for each class.
    """

    def __init__(self, domain_ontology: Graph):
        self._ontology = domain_ontology
        self._profiles: Dict[URIRef, AxiomIntentProfile] = {}

    def extract_all_profiles(self) -> Dict[URIRef, AxiomIntentProfile]:
        """Extract intent profiles for all named classes."""
        for cls in self._ontology.subjects(RDF.type, OWL.Class):
            if isinstance(cls, URIRef):
                self._profiles[cls] = self._extract_profile(cls)

        # Add inherited intents (presheaf restriction maps)
        self._propagate_inheritance()

        logger.info(
            "Extracted axiom intent profiles for %d classes",
            len(self._profiles),
        )
        return self._profiles

    def get_profile(self, class_iri: URIRef) -> Optional[AxiomIntentProfile]:
        """Get the intent profile for a class."""
        return self._profiles.get(class_iri)

    def _extract_profile(self, cls: URIRef) -> AxiomIntentProfile:
        """Extract the intent profile for a single class."""
        profile = AxiomIntentProfile(class_iri=cls)
        g = self._ontology

        # 1. Equivalence axioms (definitional)
        for equiv in g.objects(cls, OWL.equivalentClass):
            self._extract_from_class_expression(equiv, profile, definitional=True)

        # 2. Subclass axioms (existential/constraints)
        for superclass in g.objects(cls, RDFS.subClassOf):
            self._extract_from_class_expression(superclass, profile, definitional=False)

        # 3. Disjointness
        # owl:disjointWith
        for disj in g.objects(cls, OWL.disjointWith):
            if isinstance(disj, URIRef):
                profile.exclusions.add(AxiomIntent(
                    intent_type=AxiomIntentType.DISJOINTNESS,
                    disjoint_class=disj,
                ))

        # AllDisjointClasses
        for adj in g.subjects(RDF.type, OWL.AllDisjointClasses):
            members = list(g.objects(adj, OWL.members))
            # RDF list parsing
            class_members = self._parse_rdf_list(members[0] if members else None)
            if cls in class_members:
                for other in class_members:
                    if other != cls and isinstance(other, URIRef):
                        profile.exclusions.add(AxiomIntent(
                            intent_type=AxiomIntentType.DISJOINTNESS,
                            disjoint_class=other,
                        ))

        return profile

    def _extract_from_class_expression(
        self,
        expr,
        profile: AxiomIntentProfile,
        definitional: bool,
    ) -> None:
        """Extract intents from a class expression (restriction, intersection, etc.)."""
        g = self._ontology

        if isinstance(expr, URIRef):
            # Named class — nothing to extract
            return

        if not isinstance(expr, BNode):
            return

        # Check for intersection (owl:intersectionOf)
        intersection = next(g.objects(expr, OWL.intersectionOf), None)
        if intersection is not None:
            members = self._parse_rdf_list(intersection)
            for member in members:
                self._extract_from_class_expression(member, profile, definitional)
            return

        # Check for restriction (owl:Restriction)
        if (expr, RDF.type, OWL.Restriction) in g:
            on_property = next(g.objects(expr, OWL.onProperty), None)
            if on_property is None or not isinstance(on_property, URIRef):
                return

            # someValuesFrom (existential)
            some_values = next(g.objects(expr, OWL.someValuesFrom), None)
            if some_values is not None:
                filler = some_values if isinstance(some_values, URIRef) else None
                intent_type = (AxiomIntentType.DEFINITIONAL if definitional
                               else AxiomIntentType.EXISTENTIAL)
                target = profile.definitional if definitional else profile.existential
                target.add(AxiomIntent(
                    intent_type=intent_type,
                    property_iri=on_property,
                    filler_type=filler,
                ))

            # allValuesFrom (universal)
            all_values = next(g.objects(expr, OWL.allValuesFrom), None)
            if all_values is not None:
                filler = all_values if isinstance(all_values, URIRef) else None
                profile.constraints.add(AxiomIntent(
                    intent_type=AxiomIntentType.UNIVERSAL,
                    property_iri=on_property,
                    filler_type=filler,
                ))

            # Cardinality constraints
            for card_pred, card_type in [
                (OWL.minCardinality, AxiomIntentType.CARDINALITY_MIN),
                (OWL.maxCardinality, AxiomIntentType.CARDINALITY_MAX),
                (OWL.cardinality, AxiomIntentType.CARDINALITY_EXACT),
                (OWL.minQualifiedCardinality, AxiomIntentType.CARDINALITY_MIN),
                (OWL.maxQualifiedCardinality, AxiomIntentType.CARDINALITY_MAX),
                (OWL.qualifiedCardinality, AxiomIntentType.CARDINALITY_EXACT),
            ]:
                card_val = next(g.objects(expr, card_pred), None)
                if card_val is not None:
                    try:
                        val = int(card_val)
                    except (ValueError, TypeError):
                        continue
                    on_class = next(g.objects(expr, OWL.onClass), None)
                    filler = on_class if isinstance(on_class, URIRef) else None
                    target_set = profile.definitional if definitional else profile.constraints
                    target_set.add(AxiomIntent(
                        intent_type=card_type,
                        property_iri=on_property,
                        filler_type=filler,
                        cardinality_value=val,
                    ))

            # hasValue
            has_value = next(g.objects(expr, OWL.hasValue), None)
            if has_value is not None:
                intent_type = (AxiomIntentType.DEFINITIONAL if definitional
                               else AxiomIntentType.EXISTENTIAL)
                target = profile.definitional if definitional else profile.existential
                target.add(AxiomIntent(
                    intent_type=intent_type,
                    property_iri=on_property,
                    filler_type=has_value if isinstance(has_value, URIRef) else None,
                ))

    def _parse_rdf_list(self, head) -> List:
        """Parse an RDF list (linked list of rdf:first/rdf:rest)."""
        g = self._ontology
        items = []
        current = head
        while current is not None and current != RDF.nil:
            first = next(g.objects(current, RDF.first), None)
            if first is not None:
                items.append(first)
            current = next(g.objects(current, RDF.rest), None)
        return items

    def _propagate_inheritance(self) -> None:
        """
        Propagate axiom intents down the class hierarchy.
        Implements the presheaf restriction maps (Proposition 3.5).
        """
        g = self._ontology

        # Build hierarchy
        children: Dict[URIRef, Set[URIRef]] = defaultdict(set)
        for sub, _, sup in g.triples((None, RDFS.subClassOf, None)):
            if isinstance(sub, URIRef) and isinstance(sup, URIRef):
                children[sup].add(sub)

        # BFS from roots
        visited = set()
        queue = [
            cls for cls in self._profiles
            if not any(
                isinstance(s, URIRef) and s in self._profiles
                for s in g.objects(cls, RDFS.subClassOf)
            )
        ]

        while queue:
            cls = queue.pop(0)
            if cls in visited:
                continue
            visited.add(cls)

            parent_profile = self._profiles.get(cls)
            if parent_profile is None:
                continue

            for child in children.get(cls, set()):
                child_profile = self._profiles.get(child)
                if child_profile is None:
                    continue

                # Inherit constraints (not definitional — those are class-specific)
                child_profile.existential |= parent_profile.existential
                child_profile.constraints |= parent_profile.constraints
                child_profile.exclusions |= parent_profile.exclusions

                queue.append(child)


class AxiomAlignmentScorer:
    """
    Scores candidate mappings against axiom intent profiles.

    Implements Chapter 7.1 of the algorithms paper and
    Definition 3.9 (Π_axiom) of the foundations paper.
    """

    # Score weights for different axiom intent types
    DEFINITIONAL_SCORE = 0.95
    EXISTENTIAL_SCORE = 0.80
    PERMITTED_SCORE = 0.50
    NO_SUPPORT_SCORE = 0.20

    def __init__(
        self,
        profiler: AxiomIntentProfiler,
        domain_ontology: Graph,
    ):
        self._profiler = profiler
        self._ontology = domain_ontology

    def score_alignment(
        self,
        concept_iri: URIRef,
        target_property_iri: URIRef,
        target_class_iri: URIRef,
        other_mappings_to_property: int = 0,
    ) -> Tuple[float, bool, str]:
        """
        Score the alignment of a candidate mapping against axiom intents.

        Parameters
        ----------
        concept_iri : URIRef
            The candidate DataConcept.
        target_property_iri : URIRef
            The target property in the ontology.
        target_class_iri : URIRef
            The target class for the parent mapping.
        other_mappings_to_property : int
            Number of other fields already mapped to this property.

        Returns
        -------
        (score, is_feasible, explanation)
            score in [0, 1], feasibility flag, explanation string.
        """
        profile = self._profiler.get_profile(target_class_iri)
        if profile is None:
            return (self.PERMITTED_SCORE, True, "No axiom profile available")

        # Check 1: Is the property DEFINITIONAL?
        is_definitional = target_property_iri in profile.definitional_properties
        if is_definitional:
            base_score = self.DEFINITIONAL_SCORE
            explanation = f"DEFINITIONAL: {target_property_iri} in equivalence axiom of {target_class_iri}"
        elif target_property_iri in profile.required_properties:
            base_score = self.EXISTENTIAL_SCORE
            explanation = f"EXISTENTIAL: {target_property_iri} required by {target_class_iri}"
        else:
            # Check if property domain includes target class
            if self._property_applicable_to_class(target_property_iri, target_class_iri):
                base_score = self.PERMITTED_SCORE
                explanation = f"PERMITTED: {target_property_iri} applicable to {target_class_iri}"
            else:
                return (0.0, False, f"INFEASIBLE: {target_property_iri} not applicable to {target_class_iri}")

        # Check 2: Cardinality constraints
        for intent in profile.constraints | profile.definitional:
            if intent.property_iri != target_property_iri:
                continue

            if intent.intent_type == AxiomIntentType.CARDINALITY_MAX:
                if other_mappings_to_property >= intent.cardinality_value:
                    return (
                        0.0, False,
                        f"INFEASIBLE: cardinality max {intent.cardinality_value} "
                        f"for {target_property_iri} exceeded"
                    )
            elif intent.intent_type == AxiomIntentType.CARDINALITY_EXACT:
                if other_mappings_to_property >= intent.cardinality_value:
                    return (
                        0.0, False,
                        f"INFEASIBLE: exact cardinality {intent.cardinality_value} "
                        f"for {target_property_iri} exceeded"
                    )

        # Check 3: Disjointness
        for intent in profile.exclusions:
            if intent.intent_type == AxiomIntentType.DISJOINTNESS:
                # If the property's domain is disjoint with target class
                prop_domain = self._get_property_domain(target_property_iri)
                if prop_domain and intent.disjoint_class == prop_domain:
                    return (
                        0.0, False,
                        f"INFEASIBLE: {target_property_iri} domain "
                        f"{prop_domain} disjoint with {target_class_iri}"
                    )

        # Check 4: Range compatibility (type check already done elsewhere)
        range_score = 1.0  # Assumed checked by type filter

        return (base_score * range_score, True, explanation)

    def compute_axiom_distance(
        self,
        concept_iri: URIRef,
        target_property_iri: URIRef,
        target_class_iri: URIRef,
    ) -> float:
        """
        Compute Π_axiom(c, ô, Ĉ) = -ln(axiom_alignment_score).
        Returns ∞ if infeasible.
        """
        score, feasible, _ = self.score_alignment(
            concept_iri, target_property_iri, target_class_iri
        )
        if not feasible or score <= 0:
            return float("inf")
        return -math.log(score)

    def _property_applicable_to_class(
        self, property_iri: URIRef, class_iri: URIRef
    ) -> bool:
        """Check if a property's domain includes the class."""
        g = self._ontology
        domains = set(g.objects(property_iri, RDFS.domain))
        if not domains:
            return True  # No domain declared — property is global

        for domain in domains:
            if domain == class_iri:
                return True
            # Check subclass
            if self._is_subclass(class_iri, domain):
                return True

        return False

    def _get_property_domain(self, property_iri: URIRef) -> Optional[URIRef]:
        """Get the declared domain of a property."""
        for domain in self._ontology.objects(property_iri, RDFS.domain):
            if isinstance(domain, URIRef):
                return domain
        return None

    def _is_subclass(self, sub: URIRef, sup: URIRef) -> bool:
        """Check if sub is a subclass of sup (transitive)."""
        g = self._ontology
        visited = set()
        queue = [sub]
        while queue:
            current = queue.pop(0)
            if current == sup:
                return True
            if current in visited:
                continue
            visited.add(current)
            for parent in g.objects(current, RDFS.subClassOf):
                if isinstance(parent, URIRef):
                    queue.append(parent)
        return False