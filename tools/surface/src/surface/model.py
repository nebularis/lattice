# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
The declaration model, and the analyser that extracts it from a contract graph.

Structurally this mirrors ``MorkGraphAnalyser`` in ``tools/mork/src/mork2rml.py``: a set
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

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, Union

from rdflib import Graph, Literal, URIRef
from rdflib.paths import InvPath, Path, SequencePath

from .expression import (
    ARITHMETIC_KINDS,
    COMPARISON_OPERATORS,
    EXPRESSION_KINDS,
    CHOICE,
    OPERAND_SLOTS,
    ORDERING_OPERATORS,
    QUOTIENT,
    ROUNDING,
    TYPED_LITERAL,
    comparable,
    is_numeric,
    promoted,
)
from .namespaces import FND, QNT, RDF, SRF, VOC, XSD


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

    def identity_hash(self) -> str:
        """A stable digest of ``identity()``.

        Used wherever a stage needs to compare profile identity without
        carrying the full identity string around — regeneration-reuse
        decisions, and the stack composition check ADR-A21 requires (law
        ``srf:R1``: every surface in a stack shares one profile identity).
        Whether this digest is ever asserted into the graph as
        ``srf:profileIdentityHash`` is a separate, still-open question (see
        the Surface outstanding items record §3.3); this method is a pure
        computation with no graph side effect either way.
        """
        return hashlib.sha256(self.identity().encode("utf-8")).hexdigest()


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
    active_binding_scope: Tuple[URIRef, ...] = field(default_factory=tuple)
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
# Projection declarations (ADR-A17, ADR-A20)
# ---------------------------------------------------------------------------

#: Role kinds a contract may declare at most one binding for (law srf:P3).
SINGLETON_ROLES = (str(SRF.EvaluationSubjectRole), str(SRF.ResultTargetRole), str(SRF.ClosureBasisRole))

#: Role kinds a join or derivation projection needs at least one of (law srf:P2).
EVIDENCE_ROLES = (str(SRF.CandidateEvidenceRole), str(SRF.RequiredEvidenceRole))

#: Projection kinds that require at least one evidence role binding (law srf:P2).
EVIDENCE_REQUIRED_KINDS = (str(SRF.JoinProjection), str(SRF.DerivationProjection))


@dataclass(frozen=True)
class RoleBinding:
    """One named role a projection contract binds to a property, or to a second carrier."""

    iri: URIRef
    role_kind: URIRef
    binds_property: Optional[URIRef] = None
    binds_carrier: Optional[URIRef] = None
    #: The datatype of the value the bound property carries (``srf:bindsDatatype``), as an expression reads it.
    datatype: Optional[URIRef] = None


@dataclass(frozen=True)
class Expression:
    """One node of a derivation's expression (``srf:ProjectionExpression``), with its operands transcribed.

    ``operands`` are in the order ``expression.OPERAND_SLOTS`` gives for the kind. An operand is another
    ``Expression`` or the ``RoleBinding`` of an evidence role of the same contract.
    """

    iri: URIRef
    kind: URIRef
    datatype: URIRef
    operands: Tuple["Operand", ...] = ()
    literal: Optional[Literal] = None
    scale: Optional[int] = None
    comparison: Optional[URIRef] = None


Operand = Union[Expression, RoleBinding]


def operand_datatype(operand: Operand) -> Optional[URIRef]:
    return operand.datatype


@dataclass(frozen=True)
class BackendPolicy:
    """The declared backend eligibility and LLM-participation policy a projection lowers under."""

    iri: URIRef
    allowed_backends: Sequence[URIRef] = field(default_factory=tuple)
    denied_backends: Sequence[URIRef] = field(default_factory=tuple)
    deterministic_only: bool = False
    llm_completion_policy: Optional[URIRef] = None
    approved_templates: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProjectionContract:
    """One projection contract, transcribed (ADR-A17). Never a ``Contract``: a
    projection has no read path and no value population — it reads its
    evidence through role bindings and lowers into MORK (ADR-A18) rather than
    emitting an artefact directly, so it is deliberately a distinct shape
    rather than a third branch bolted onto ``Contract``.
    """

    iri: URIRef
    carrier: URIRef
    key: str
    target_namespace: str
    realisation_mode: str
    profile: Profile
    projection_kind: URIRef
    role_bindings: Sequence[RoleBinding]
    backend_policy: Optional[BackendPolicy] = None
    population_budget: Optional[int] = None
    #: The expression a derivation states on its result-target role binding (law ``srf:P6``).
    expression: Optional[Expression] = None

    def roles(self, kind: URIRef) -> List[RoleBinding]:
        return [b for b in self.role_bindings if str(b.role_kind) == str(kind)]


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
            scopes = sorted(
                (s for s in self.g.objects(iri, SRF.activeBindingScope) if isinstance(s, URIRef)),
                key=str,
            )
            return Population(
                iri=iri,
                kind="contract-bound",
                scheme_contract=self._iri(iri, SRF.fromSchemeContract),
                active_binding_scope=tuple(scopes),
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

    # -- projection contracts (ADR-A17, ADR-A20) -----------------------------

    def role_binding(self, iri: URIRef) -> RoleBinding:
        return RoleBinding(
            iri=iri,
            role_kind=self._iri(iri, SRF.roleKind),
            binds_property=self._iri(iri, SRF.bindsProperty, required=False),
            binds_carrier=self._iri(iri, SRF.bindsCarrier, required=False),
            datatype=self._iri(iri, SRF.bindsDatatype, required=False),
        )

    # -- a derivation's expression (laws srf:P6 to srf:P9) --------------------

    def expression(
        self,
        iri: URIRef,
        contract: URIRef,
        bindings: Dict[str, RoleBinding],
        reaching: Tuple[str, ...] = (),
    ) -> Expression:
        """Transcribe the expression rooted at ``iri``, applying the checks the shapes make."""
        if str(iri) in reaching:
            raise ContractError(f"{contract} states an expression that is an operand of itself at {iri} (law srf:P9)")
        kinds = [kind for kind in EXPRESSION_KINDS if str(kind) in self._types(iri)]
        if len(kinds) != 1:
            raise ContractError(
                f"{iri} in the expression of {contract} is not exactly one kind of projection expression (law srf:P7)"
            )
        kind = kinds[0]
        name = str(kind).rsplit("#", 1)[-1]
        datatype = self._iri(iri, SRF.resultDatatype, required=False)
        if datatype is None:
            raise ContractError(f"{iri} is a {name} with no result datatype (law srf:P8)")

        operands: List[Operand] = []
        for slot in OPERAND_SLOTS[kind]:
            slot_name = str(slot).rsplit("#", 1)[-1]
            value = self._iri(iri, slot, required=False)
            if value is None:
                raise ContractError(f"{iri} is a {name} with no {slot_name} (law srf:P7)")
            binding = bindings.get(str(value))
            if binding is not None:
                if str(binding.role_kind) not in EVIDENCE_ROLES or binding.binds_property is None:
                    raise ContractError(
                        f"{iri} reads {value} as its {slot_name}, which is not an evidence role binding that "
                        f"binds a property (law srf:P7)"
                    )
                operands.append(binding)
            elif any(str(k) in self._types(value) for k in EXPRESSION_KINDS):
                operands.append(self.expression(value, contract, bindings, reaching + (str(iri),)))
            else:
                raise ContractError(
                    f"{iri} reads {value} as its {slot_name}, which is neither an expression nor an evidence "
                    f"role binding of {contract} (law srf:P7)"
                )
            if operand_datatype(operands[-1]) is None:
                raise ContractError(f"{iri} reads {value} as its {slot_name}, which states no datatype (law srf:P8)")

        literal: Optional[Literal] = None
        scale: Optional[int] = None
        comparison: Optional[URIRef] = None

        if kind in ARITHMETIC_KINDS:
            left, right = (operand_datatype(o) for o in operands)
            if not (is_numeric(left) and is_numeric(right)):
                raise ContractError(f"{iri} is a {name} with an operand that is not numeric (law srf:P8)")
            expected = promoted(left, right, at_least_decimal=kind == QUOTIENT)
            if str(datatype) != str(expected):
                raise ContractError(
                    f"{iri} is a {name} of {left} and {right}, so its result datatype is {expected} "
                    f"and not {datatype} (law srf:P8)"
                )
        elif kind == ROUNDING:
            operand_type = operand_datatype(operands[0])
            if not is_numeric(operand_type):
                raise ContractError(f"{iri} rounds an operand that is not numeric (law srf:P8)")
            if str(datatype) != str(operand_type):
                raise ContractError(
                    f"{iri} rounds a {operand_type} so its result datatype is {operand_type} and not {datatype} (law srf:P8)"
                )
            raw_scale = self.g.value(iri, SRF.roundingScale, any=False)
            if not isinstance(raw_scale, Literal) or str(raw_scale.datatype) != str(XSD.integer):
                raise ContractError(f"{iri} states no integer rounding scale (law srf:P8)")
            scale = int(raw_scale)
        elif kind == TYPED_LITERAL:
            raw = self.g.value(iri, SRF.typedValue, any=False)
            if not isinstance(raw, Literal):
                raise ContractError(f"{iri} is a typed literal expression with no literal value (law srf:P8)")
            if str(raw.datatype) != str(datatype):
                raise ContractError(
                    f"{iri} states a literal of datatype {raw.datatype} and a result datatype {datatype} (law srf:P8)"
                )
            literal = raw
        else:
            assert kind == CHOICE
            comparison = self._iri(iri, SRF.comparisonOperator, required=False)
            if comparison is None or str(comparison) not in {str(o) for o in COMPARISON_OPERATORS}:
                raise ContractError(f"{iri} is a choice with no comparison operator of the vocabulary (law srf:P8)")
            left, right, when_true, when_false = (operand_datatype(o) for o in operands)
            if not comparable(left, right):
                raise ContractError(
                    f"{iri} compares a {left} with a {right}, which are neither one datatype nor both numeric (law srf:P8)"
                )
            if str(comparison) in {str(o) for o in ORDERING_OPERATORS} and not (is_numeric(left) and is_numeric(right)):
                raise ContractError(f"{iri} compares by order operands that are not numeric (law srf:P8)")
            for branch in (when_true, when_false):
                if str(branch) != str(datatype):
                    raise ContractError(
                        f"{iri} is a choice of datatype {datatype} with a branch of datatype {branch} (law srf:P8)"
                    )

        return Expression(
            iri=iri,
            kind=kind,
            datatype=datatype,
            operands=tuple(operands),
            literal=literal,
            scale=scale,
            comparison=comparison,
        )

    def backend_policy(self, iri: URIRef) -> BackendPolicy:
        allowed = tuple(
            sorted(
                (o for o in self.g.objects(iri, SRF.allowedBackend) if isinstance(o, URIRef)),
                key=str,
            )
        )
        denied = tuple(
            sorted(
                (o for o in self.g.objects(iri, SRF.deniedBackend) if isinstance(o, URIRef)),
                key=str,
            )
        )
        overlap = {str(a) for a in allowed} & {str(d) for d in denied}
        if overlap:
            raise ContractError(
                f"{iri} names {sorted(overlap)} in both allowedBackend and deniedBackend "
                f"(law srf:P4)"
            )
        deterministic_text = self._literal(iri, SRF.deterministicOnly)
        deterministic_only = deterministic_text.strip().lower() in ("true", "1")
        llm_policy = self._iri(iri, SRF.llmCompletionPolicy)
        if deterministic_only and str(llm_policy) != str(SRF.NoLLMCompletion):
            raise ContractError(
                f"{iri} declares deterministicOnly true but llmCompletionPolicy is not "
                f"NoLLMCompletion (law srf:P5)"
            )
        templates = tuple(sorted(str(t) for t in self.g.objects(iri, SRF.approvedTemplate)))
        return BackendPolicy(
            iri=iri,
            allowed_backends=allowed,
            denied_backends=denied,
            deterministic_only=deterministic_only,
            llm_completion_policy=llm_policy,
            approved_templates=templates,
        )

    def projection_contract(self, iri: URIRef) -> ProjectionContract:
        types = self._types(iri)
        if str(SRF.ProjectionContract) not in types:
            raise ContractError(f"{iri} is not a ProjectionContract")

        binding_iris = sorted(
            (b for b in self.g.objects(iri, SRF.hasRoleBinding) if isinstance(b, URIRef)), key=str
        )
        if not binding_iris:
            raise ContractError(f"{iri} declares no role binding (law srf:P2)")
        bindings = [self.role_binding(b) for b in binding_iris]
        kinds = [str(b.role_kind) for b in bindings]

        if str(SRF.EvaluationSubjectRole) not in kinds:
            raise ContractError(f"{iri} has no evaluation-subject role binding (law srf:P2)")
        if str(SRF.ResultTargetRole) not in kinds:
            raise ContractError(f"{iri} has no result-target role binding (law srf:P2)")
        for role in SINGLETON_ROLES:
            if kinds.count(role) > 1:
                raise ContractError(
                    f"{iri} declares more than one {role.rsplit('#', 1)[-1]} role binding "
                    f"(law srf:P3)"
                )

        projection_kind = self._iri(iri, SRF.projectionKind)
        if str(projection_kind) in EVIDENCE_REQUIRED_KINDS and not any(
            k in EVIDENCE_ROLES for k in kinds
        ):
            raise ContractError(
                f"{iri} is a {str(projection_kind).rsplit('#', 1)[-1]} but declares no "
                f"candidate-evidence or required-evidence role binding (law srf:P2)"
            )

        expression = self._derived_expression(iri, projection_kind, bindings)

        policy_iri = self._iri(iri, SRF.backendPolicy, required=False)
        budget = self._literal(iri, SRF.populationBudget, required=False)
        return ProjectionContract(
            iri=iri,
            carrier=self._iri(iri, SRF.carrier),
            key=self._literal(iri, SRF.contractKey),
            target_namespace=self._literal(iri, SRF.targetNamespace),
            realisation_mode=str(self._iri(iri, SRF.realisationMode)),
            profile=self.profile(self._iri(iri, SRF.surfaceProfile)),
            projection_kind=projection_kind,
            role_bindings=tuple(bindings),
            backend_policy=self.backend_policy(policy_iri) if policy_iri is not None else None,
            population_budget=int(budget) if budget is not None else None,
            expression=expression,
        )

    def _derived_expression(
        self, iri: URIRef, projection_kind: URIRef, bindings: Sequence[RoleBinding]
    ) -> Optional[Expression]:
        """The expression a derivation states on its result-target binding, and none for any other kind (law srf:P6)."""
        by_iri = {str(b.iri): b for b in bindings}
        derived = [(b, self.g.value(b.iri, SRF.derivedAs, any=False)) for b in bindings]
        stated = [(b, e) for b, e in derived if e is not None]
        is_derivation = str(projection_kind) == str(SRF.DerivationProjection)
        for binding, _ in stated:
            if str(binding.role_kind) != str(SRF.ResultTargetRole) or not is_derivation:
                raise ContractError(
                    f"{iri} states an expression on {binding.iri}, which is not the result-target role binding "
                    f"of a derivation (law srf:P6)"
                )
        if not is_derivation:
            return None
        if not stated:
            raise ContractError(
                f"{iri} is a derivation and states no expression on its result-target role binding (law srf:P6)"
            )
        target, root = stated[0]
        if target.binds_property is None:
            raise ContractError(
                f"{iri} states an expression on {target.iri}, which binds no property to write the value on (law srf:P6)"
            )
        if not isinstance(root, URIRef):
            raise ContractError(f"{iri} states an expression that is not named by an IRI (law srf:P6)")
        expression = self.expression(root, iri, by_iri)
        if target.datatype is None or str(target.datatype) != str(expression.datatype):
            raise ContractError(
                f"{iri} states a result-target datatype of {target.datatype} for an expression of "
                f"datatype {expression.datatype} (law srf:P8)"
            )
        return expression

    def projection_contracts(self, only: Optional[str] = None) -> List[ProjectionContract]:
        declared = sorted(
            {s for s in self.g.subjects(RDF.type, SRF.ProjectionContract) if isinstance(s, URIRef)},
            key=str,
        )
        found = [self.projection_contract(iri) for iri in declared]
        if only is not None:
            found = [c for c in found if str(c.iri) == str(only)]
            if not found:
                raise ContractError(f"no projection contract named {only}")
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
    """Convenience wrapper, matching the shape of ``tools/mork/src/mork2rml.py``'s entry points."""
    return SurfaceGraphAnalyser(graph).contracts(only=only)


def read_projection_contracts(
    graph: Graph, only: Optional[str] = None
) -> List[ProjectionContract]:
    """Convenience wrapper for projection contracts, kept separate from ``read_contracts``
    because a ``ProjectionContract`` is a distinct shape, not a third ``Contract`` branch.
    """
    return SurfaceGraphAnalyser(graph).projection_contracts(only=only)
