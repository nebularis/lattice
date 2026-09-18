# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
The declaration model, and the analyser that extracts it from a contract graph.

Structurally this mirrors ``MorkGraphAnalyser`` in ``tools/mork2rml.py``: a set
of frozen specification dataclasses, and one analyser class whose job is a
faithful transcription of what was declared. Nothing here decides anything. It
does apply the structural checks the layer's SHACL shapes also make, so that a
malformed contract fails loudly at read time rather than producing a surface
nobody can account for.

A read path is transcribed into an ``rdflib.paths.Path`` as well as a step
list. The path object is what evaluation uses; the step list is what hashing,
naming and the emitted property-chain axiom use, because a ``Path`` has no
canonical serialisation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from rdflib import Graph, Literal, URIRef
from rdflib.paths import InvPath, Path, SequencePath

from .namespaces import FND, QNT, RDF, SRF, VOC


class ContractError(ValueError):
    """A contract declaration is malformed or incomplete."""


# ---------------------------------------------------------------------------
# Specification dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Profile:
    """The generation configuration a surface is produced under."""

    iri: URIRef
    generator_version: str
    canonicalisation_version: str
    entailment_regime: str
    naming_normalisation: str
    symbol_mode: str
    permitted_stack_depth: int
    default_population_budget: Optional[int]

    @property
    def punned(self) -> bool:
        return self.symbol_mode == str(SRF.PunnedSymbols)

    def identity(self) -> str:
        """The generation/profile identity two artefacts must share to be interchangeable."""
        return "|".join(
            (
                str(self.iri),
                self.generator_version,
                self.canonicalisation_version,
                self.entailment_regime,
                self.naming_normalisation,
                self.symbol_mode,
                str(self.permitted_stack_depth),
            )
        )


@dataclass(frozen=True)
class PathStep:
    index: int
    prop: URIRef
    inverse: bool


@dataclass(frozen=True)
class Population:
    iri: URIRef
    kind: str
    scheme_contract: Optional[URIRef] = None
    from_class: Optional[URIRef] = None
    extent_kind: Optional[str] = None
    members: Sequence[URIRef] = field(default_factory=tuple)
    range_set: Optional[URIRef] = None


@dataclass(frozen=True)
class Contract:
    """One surface contract, transcribed."""

    iri: URIRef
    is_index: bool
    carrier: URIRef
    key: str
    target_namespace: str
    realisation_mode: str
    profile: Profile
    path: Sequence[PathStep]
    population_budget: Optional[int] = None
    # index contracts
    population: Optional[Population] = None
    index_forms: Sequence[str] = field(default_factory=tuple)
    naming_policy: Optional[str] = None
    naming_prefix: str = ""
    closure_basis: Optional[URIRef] = None
    closure_scope: Optional[Population] = None
    # promotion contracts
    promotes_to: Optional[URIRef] = None
    source_fidelity: Optional[str] = None
    via_match_relation: Optional[URIRef] = None

    def has_form(self, form: URIRef) -> bool:
        return str(form) in self.index_forms

    @property
    def emits_definitions(self) -> bool:
        return self.realisation_mode in (
            str(SRF.DefinitionOnly),
            str(SRF.DefinitionAndMaterialised),
        )

    @property
    def emits_assertions(self) -> bool:
        return self.realisation_mode in (
            str(SRF.Materialised),
            str(SRF.DefinitionAndMaterialised),
        )

    @property
    def lossy(self) -> bool:
        return self.source_fidelity in (str(SRF.DerivedSource), str(SRF.CrosswalkInexact))

    @property
    def multi_hop(self) -> bool:
        return len(self.path) > 1

    @property
    def has_inverse_step(self) -> bool:
        return any(step.inverse for step in self.path)

    def budget(self) -> int:
        if self.population_budget is not None:
            return self.population_budget
        if self.profile.default_population_budget is not None:
            return self.profile.default_population_budget
        return 5000

    def read_path(self) -> Path | URIRef:
        """The read path as an rdflib path expression, for evaluation."""
        segments: List[Path | URIRef] = [
            InvPath(step.prop) if step.inverse else step.prop for step in self.path
        ]
        if len(segments) == 1:
            return segments[0]
        return SequencePath(*segments)


# ---------------------------------------------------------------------------
# Analyser
# ---------------------------------------------------------------------------


class SurfaceGraphAnalyser:
    """Extracts contract specifications from a declaration graph."""

    def __init__(self, graph: Graph) -> None:
        self.g = graph

    # -- primitive accessors ------------------------------------------------

    def _literal(self, subject, predicate, *, required: bool = True) -> Optional[str]:
        value = self.g.value(subject, predicate, any=False)
        if value is None:
            if required:
                raise ContractError(f"{subject} is missing {predicate}")
            return None
        if not isinstance(value, Literal):
            raise ContractError(f"{predicate} on {subject} must be a literal")
        return str(value)

    def _iri(self, subject, predicate, *, required: bool = True) -> Optional[URIRef]:
        value = self.g.value(subject, predicate, any=False)
        if value is None:
            if required:
                raise ContractError(f"{subject} is missing {predicate}")
            return None
        if not isinstance(value, URIRef):
            raise ContractError(f"{predicate} on {subject} must name a term")
        return value

    def _types(self, subject) -> set:
        return {str(t) for t in self.g.objects(subject, RDF.type)}

    # -- specification extraction ------------------------------------------

    def profile(self, iri: URIRef) -> Profile:
        budget = self._literal(iri, SRF.defaultPopulationBudget, required=False)
        return Profile(
            iri=iri,
            generator_version=self._literal(iri, SRF.generatorVersion),
            canonicalisation_version=self._literal(iri, SRF.canonicalisationVersion),
            entailment_regime=str(self._iri(iri, SRF.entailmentRegime)),
            naming_normalisation=str(self._iri(iri, SRF.namingNormalisation)),
            symbol_mode=str(self._iri(iri, SRF.symbolMode)),
            permitted_stack_depth=int(self._literal(iri, SRF.permittedStackDepth)),
            default_population_budget=int(budget) if budget is not None else None,
        )

    def population(self, iri: URIRef) -> Population:
        types = self._types(iri)
        if str(SRF.ContractBoundPopulation) in types:
            return Population(
                iri=iri,
                kind="contract-bound",
                scheme_contract=self._iri(iri, SRF.fromSchemeContract),
            )
        if str(SRF.ClassExtentPopulation) in types:
            return Population(
                iri=iri,
                kind="class-extent",
                from_class=self._iri(iri, SRF.fromClass),
                extent_kind=str(self._iri(iri, SRF.extentKind)),
            )
        if str(SRF.EnumeratedPopulation) in types:
            members = sorted(
                (m for m in self.g.objects(iri, SRF.hasPopulationMember) if isinstance(m, URIRef)),
                key=str,
            )
            if not members:
                raise ContractError(f"{iri} declares no population members")
            return Population(iri=iri, kind="enumerated", members=tuple(members))
        if str(SRF.RangePartitionPopulation) in types:
            raise ContractError(
                f"{iri} is a range-partition population; declared and not yet permitted"
            )
        raise ContractError(f"{iri} is not a recognised value population")

    def path(self, contract: URIRef) -> List[PathStep]:
        single = self._iri(contract, SRF.readProperty, required=False)
        steps = list(self.g.objects(contract, SRF.hasPathStep))
        if single is not None and steps:
            raise ContractError(
                f"{contract} declares both readProperty and hasPathStep; "
                f"exactly one read-path form is permitted (law srf:S1)"
            )
        if single is not None:
            return [PathStep(index=0, prop=single, inverse=False)]
        if not steps:
            raise ContractError(f"{contract} declares no read path (law srf:S1)")

        parsed = [
            PathStep(
                index=int(self._literal(step, SRF.stepIndex)),
                prop=self._iri(step, SRF.stepProperty),
                inverse=str(self._iri(step, SRF.stepDirection)) == str(SRF.Inverse),
            )
            for step in steps
        ]
        parsed.sort(key=lambda s: s.index)
        if [s.index for s in parsed] != list(range(len(parsed))):
            raise ContractError(
                f"{contract} has non-contiguous or duplicated path step indices: "
                f"{[s.index for s in parsed]}"
            )
        return parsed

    def contract(self, iri: URIRef) -> Contract:
        types = self._types(iri)
        is_index = str(SRF.IndexContract) in types
        is_promotion = str(SRF.PromotionContract) in types
        if is_index == is_promotion:
            raise ContractError(
                f"{iri} must be exactly one of IndexContract or PromotionContract"
            )

        budget = self._literal(iri, SRF.populationBudget, required=False)
        common = dict(
            iri=iri,
            is_index=is_index,
            carrier=self._iri(iri, SRF.carrier),
            key=self._literal(iri, SRF.contractKey),
            target_namespace=self._literal(iri, SRF.targetNamespace),
            realisation_mode=str(self._iri(iri, SRF.realisationMode)),
            profile=self.profile(self._iri(iri, SRF.surfaceProfile)),
            path=tuple(self.path(iri)),
            population_budget=int(budget) if budget is not None else None,
        )

        if is_promotion:
            fidelity = str(self._iri(iri, SRF.sourceFidelity))
            relation = self._iri(iri, SRF.viaMatchRelation, required=False)
            crosswalk = fidelity in (str(SRF.CrosswalkExact), str(SRF.CrosswalkInexact))
            if crosswalk and relation is None:
                raise ContractError(
                    f"{iri} declares crosswalk fidelity but names no match relation (law srf:X5)"
                )
            if not crosswalk and relation is not None:
                raise ContractError(
                    f"{iri} names a match relation but declares non-crosswalk fidelity (law srf:X5)"
                )
            return Contract(
                **common,
                promotes_to=self._iri(iri, SRF.promotesTo),
                source_fidelity=fidelity,
                via_match_relation=relation,
            )

        forms = tuple(
            sorted(str(f) for f in self.g.objects(iri, SRF.indexForm) if isinstance(f, URIRef))
        )
        if not forms:
            raise ContractError(f"{iri} declares no index form")
        if str(SRF.ExternalIndex) in forms:
            raise ContractError(
                f"{iri} declares the ExternalIndex form, which is declared and not yet permitted"
            )
        basis = self._iri(iri, SRF.closureBasis, required=False)
        if (str(SRF.ClosureRelation) in forms) != (basis is not None):
            raise ContractError(
                f"{iri} must declare a closure basis exactly when it declares the "
                f"ClosureRelation form (law srf:S3)"
            )
        scope_iri = self._iri(iri, SRF.closureScope, required=False)
        return Contract(
            **common,
            population=self.population(self._iri(iri, SRF.valuePopulation)),
            index_forms=forms,
            naming_policy=str(self._iri(iri, SRF.namingPolicy)),
            naming_prefix=self._literal(iri, SRF.namingPrefix, required=False) or "",
            closure_basis=basis,
            closure_scope=self.population(scope_iri) if scope_iri is not None else None,
        )

    def contracts(self, only: Optional[str] = None) -> List[Contract]:
        declared: List[URIRef] = []
        for class_iri in (SRF.IndexContract, SRF.PromotionContract):
            declared.extend(
                s for s in self.g.subjects(RDF.type, class_iri) if isinstance(s, URIRef)
            )
        declared = sorted(set(declared), key=str)
        found = [self.contract(iri) for iri in declared]
        if only is not None:
            found = [c for c in found if str(c.iri) == str(only)]
            if not found:
                raise ContractError(f"no surface contract named {only}")
        return found

    # -- declaration subgraph, for the read set ------------------------------

    def declaration_subjects(self, contract: Contract) -> List[URIRef]:
        subjects: List[URIRef] = [contract.iri, contract.profile.iri]
        subjects.extend(
            s for s in self.g.objects(contract.iri, SRF.hasPathStep) if isinstance(s, URIRef)
        )
        if contract.population is not None:
            subjects.append(contract.population.iri)
            if contract.population.scheme_contract is not None:
                subjects.append(contract.population.scheme_contract)
        if contract.closure_scope is not None:
            subjects.append(contract.closure_scope.iri)
        return subjects


def read_contracts(graph: Graph, only: Optional[str] = None) -> List[Contract]:
    """Convenience wrapper, matching the shape of ``tools/mork2rml.py``'s entry points."""
    return SurfaceGraphAnalyser(graph).contracts(only=only)
