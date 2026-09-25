# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
The surface compiler.

A run takes a contract, a source graph, and a profile, and emits four modules:

``core.ttl``        definitions — family classes, nominal classes, generated
                    relations, property chains
``closure.ttl``     closure rules, or materialised closure assertions
``assertions.ttl``  materialised memberships, promoted values, direct values
``manifest.ttl``    the generated-surface record, its read set, its symbol
                    records, its hashes, and its law discharges

Module boundaries follow invalidation classes rather than file size: a change
to the carrier instance graph must be able to leave ``core.ttl`` untouched.

The class structure follows ``MorkToRmlCompiler`` in ``tools/mork2rml.py``:
analyse, then plan, then emit, with a mutable context carried through. What
differs is the algebra — MORK folds a mapping DAG into RML triples maps; this
folds one contract plus its read set into a symbol inventory. Dependency order
is not derived here because a surface contract has no children; where surfaces
stack, the ordering is over whole contracts and is the caller's business.

The compiler is deterministic. Population order is IRI order, blank-node labels
are minted from the term they belong to, and the production timestamp is the
only non-reproducible value emitted — which is why it sits outside the artefact
hash.

**Staged pipeline (ADR-A19).** A Promotion or Index contract's run maps onto
the staged model as: validate (``model.py``'s analyser, at read time) →
normalise (population enumeration and read-path evaluation, below) → compile
(``SurfaceCompiler.compile``, this module) → emit (``serialise.py``) →
provenance (the manifest module, ``_manifest``). Promotion and Index end the
pipeline at emit, because ADR-A16 gives them a direct-emit form. A
``ProjectionContract`` has no direct-emit form (ADR-A17): its pipeline instead
ends at lower — ``lowering.py`` — which produces a MORK mapping graph for a
later backend compiler (ADR-A23) to read, rather than a compiled module
package. The two pipelines share validate and normalise; they diverge at the
stage ADR-A18 draws the line at.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Set, Tuple

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.term import Node

from vocabulary import BindingConflictError, NoApplicableBindingError, resolve

from . import canonical
from .model import Contract, ContractError, Population, SurfaceGraphAnalyser
from .namespaces import (
    DCTERMS,
    FND,
    OUTPUT_PREFIXES,
    OWL,
    RDF,
    RDFS,
    SH,
    SKOS,
    SRF,
    SURFACE_ONTOLOGY,
    XSD,
)
from .naming import Minter, check_injective, local_name
from .serialise import serialise

logger = logging.getLogger(__name__)

NOMINAL = SRF.NominalClass
MEMBERSHIP = SRF.MembershipAssertion
CLOSURE = SRF.ClosureRelation
DIRECT = SRF.DirectProperty

WARN_POPULATION = 500
DEFAULT_BUDGET = 5000

#: Entailment regimes this compiler acts on. It reads asserted triples only,
#: which is correct for NoEntailment and a silent gap for anything richer
#: (outstanding items §3.5) — so anything else is refused at compile time
#: rather than silently under-entailed.
SUPPORTED_ENTAILMENT_REGIMES = (str(SRF.NoEntailment),)


class CompileError(ValueError):
    """The contract cannot be compiled against this source graph."""


class CyclicClosureBasis(CompileError):
    """The declared closure basis is not well founded over the declared scope."""


def check_entailment_regime(profile) -> None:
    """Refuse to compile under an entailment regime this compiler does not act on.

    The compiler always reads asserted triples: correct for ``NoEntailment``,
    and a gap for ``RDFSEntailment``, ``OWL2ELEntailment``, and
    ``OWL2DLEntailment``, where a ``DefinitionOnly`` surface would answer
    nothing without a reasoner this compiler does not run. Claiming support and
    generating an under-entailed surface is worse than refusing outright.
    """
    if profile.entailment_regime not in SUPPORTED_ENTAILMENT_REGIMES:
        raise CompileError(
            f"profile {profile.iri} declares entailment regime "
            f"{profile.entailment_regime}, which this compiler does not act on. Only "
            f"srf:NoEntailment is currently supported (ontology/surface/docs/OUTSTANDING-ITEMS.md §3.5)."
        )


# ---------------------------------------------------------------------------
# Source reading
# ---------------------------------------------------------------------------

CARRIER_INSTANCES = """
SELECT DISTINCT ?instance WHERE {
    ?instance rdf:type/rdfs:subClassOf* ?carrier .
}
"""

SCHEME_MEMBERS = """
SELECT DISTINCT ?member WHERE {
    { ?member skos:inScheme ?scheme }
    UNION
    { ?scheme skos:hasTopConcept ?member }
}
"""

DIRECT_SUBCLASSES = """
SELECT DISTINCT ?member WHERE { ?member rdfs:subClassOf ?class . }
"""

TRANSITIVE_SUBCLASSES = """
SELECT DISTINCT ?member WHERE { ?member rdfs:subClassOf+ ?class . }
"""

NAMED_INDIVIDUALS = """
SELECT DISTINCT ?member WHERE { ?member rdf:type ?class . }
"""


def _query_iris(graph: Graph, query: str, **bindings) -> List[URIRef]:
    rows = graph.query(query, initBindings=bindings)
    found = {row[0] for row in rows if isinstance(row[0], URIRef)}
    return sorted(found, key=str)


def carrier_instances(graph: Graph, carrier: URIRef) -> List[URIRef]:
    """Every instance of the carrier, or of a subclass of it."""
    return _query_iris(graph, CARRIER_INSTANCES, carrier=carrier)


def enumerate_population(
    graph: Graph, population: Population, at: Optional[str] = None
) -> Tuple[List[URIRef], Optional[URIRef]]:
    """The population's members in IRI order, and the scheme they came from."""
    if population.kind == "enumerated":
        return list(population.members), None

    if population.kind == "contract-bound":
        if at is None:
            raise CompileError(
                f"{population.scheme_contract} needs a resolution time to resolve its "
                f"scheme binding (law srf:S2, ADR-A85)"
            )
        try:
            resolution = resolve(
                graph,
                population.scheme_contract,
                context=population.active_binding_scope,
                at=datetime.fromisoformat(at),
            )
        except (BindingConflictError, NoApplicableBindingError) as error:
            raise CompileError(
                f"{population.scheme_contract} has no scheme to enumerate its population "
                f"from (law srf:S2): {error}"
            ) from error
        return _query_iris(graph, SCHEME_MEMBERS, scheme=resolution.scheme), resolution.scheme

    if population.kind == "class-extent":
        query = {
            str(SRF.NamedIndividuals): NAMED_INDIVIDUALS,
            str(SRF.DirectSubClasses): DIRECT_SUBCLASSES,
            str(SRF.TransitiveSubClasses): TRANSITIVE_SUBCLASSES,
        }.get(population.extent_kind)
        if query is None:
            raise CompileError(f"unknown extent kind: {population.extent_kind}")
        return _query_iris(graph, query, **{"class": population.from_class}), None

    raise CompileError(f"population kind {population.kind} cannot be enumerated")


def evaluate_path(graph: Graph, start: URIRef, contract: Contract) -> List[Node]:
    """Follow a contract's read path from one carrier instance."""
    return sorted(graph.objects(start, contract.read_path()), key=str)


def ancestors(
    graph: Graph,
    value: URIRef,
    basis: URIRef,
    scope: Optional[Set[str]] = None,
) -> List[URIRef]:
    """The reflexive-transitive closure of ``basis`` from ``value``, within scope.

    Written as an explicit traversal rather than as ``MulPath(basis, ZeroOrMore)``
    because law ``srf:R5`` requires the generator to *establish* that the basis is
    well founded, and a path evaluation that silently terminates on a cycle
    establishes nothing.
    """
    reached: List[str] = []
    seen: Set[str] = set()

    def walk(node: URIRef, trail: Tuple[str, ...]) -> None:
        if str(node) in trail:
            raise CyclicClosureBasis(
                f"closure basis {basis} is cyclic: " + " -> ".join(trail + (str(node),))
            )
        if scope is not None and str(node) not in scope:
            return
        if str(node) not in seen:
            seen.add(str(node))
            reached.append(str(node))
        for parent in sorted(
            (o for o in graph.objects(node, basis) if isinstance(o, URIRef)), key=str
        ):
            walk(parent, trail + (str(node),))

    walk(value, ())
    return [URIRef(v) for v in sorted(reached)]


# ---------------------------------------------------------------------------
# Compilation result
# ---------------------------------------------------------------------------


@dataclass
class SymbolRecord:
    term: URIRef
    form: URIRef
    value: Optional[URIRef] = None


@dataclass
class ReadSetRecord:
    kind: URIRef
    source: Node
    digest: str
    version: Optional[str] = None

    def key(self) -> Tuple[str, str]:
        return (str(self.kind), str(self.source))


@dataclass(frozen=True)
class StackedInput:
    """One surface a stacked generation run reads (ADR-A21).

    ``profile_identity`` and ``signature_scope`` are optional so that a caller
    without a manifest to hand — or code written before this record existed —
    can still pass a bare ``(surface, artefact_hash, depth)`` tuple, which
    ``SurfaceCompiler`` coerces on the way in. Composition is only checked for
    inputs that supply the field it depends on: an input with no known profile
    identity is not silently treated as matching, it is simply not compared.
    """

    surface: URIRef
    artefact_hash: str
    depth: int
    profile_identity: Optional[str] = None
    signature_scope: Optional[str] = None

    @classmethod
    def coerce(cls, entry: "StackedInput | Tuple[URIRef, str, int]") -> "StackedInput":
        if isinstance(entry, StackedInput):
            return entry
        surface, artefact_hash, depth = entry
        return cls(surface=surface, artefact_hash=artefact_hash, depth=depth)


@dataclass
class CompiledSurface:
    """Everything one generation run produced, before it is written anywhere."""

    contract: Contract
    modules: Dict[str, Graph]
    symbols: List[SymbolRecord]
    population: List[URIRef]
    read_set: List[ReadSetRecord]
    stack_depth: int
    signature_scope: URIRef
    well_founded: bool
    produced_at: str = ""
    warnings: List[str] = field(default_factory=list)
    artefact_hash: str = ""
    semantic_hash: str = ""

    def content_modules(self) -> List[Graph]:
        return [self.modules[name] for name in ("core", "closure", "assertions")]

    @property
    def record(self) -> URIRef:
        return URIRef(f"{self.contract.target_namespace}surface_{self.contract.key}")

    @property
    def authority(self) -> URIRef:
        return SRF.Advisory if self.contract.lossy else SRF.CachedReproducible


# ---------------------------------------------------------------------------
# The compiler
# ---------------------------------------------------------------------------


class SurfaceCompiler:
    """Compiles one surface contract against one source graph."""

    def __init__(
        self,
        contract: Contract,
        source: Graph,
        produced_at: str,
        input_surfaces: Sequence["StackedInput | Tuple[URIRef, str, int]"] = (),
    ) -> None:
        self.contract = contract
        self.source = source
        self.produced_at = produced_at
        self.input_surfaces = [StackedInput.coerce(entry) for entry in input_surfaces]
        self.analyser = SurfaceGraphAnalyser(source)

        self.minter = Minter(
            target_namespace=contract.target_namespace,
            contract_key=contract.key,
            carrier=str(contract.carrier),
            normalisation=contract.profile.naming_normalisation,
            naming_policy=contract.naming_policy or "",
            naming_prefix=contract.naming_prefix,
        )

        self.core = Graph()
        self.closure = Graph()
        self.assertions = Graph()
        self.symbols: List[SymbolRecord] = []
        self.read_set: List[ReadSetRecord] = []
        self.warnings: List[str] = []
        self.population: List[URIRef] = []
        self.well_founded = True
        self.signature_scope = SRF.LocalSignature
        self.base = self._module_base()

    # -- helpers ------------------------------------------------------------

    def _module_base(self) -> str:
        namespace = str(self.contract.target_namespace)
        trimmed = namespace[:-1] if namespace.endswith(("#", "/")) else namespace
        return f"{trimmed}/{self.contract.key}"

    def _subgraph(self, subjects: Sequence[Node]) -> Graph:
        """A graph of every triple about the given subjects, for hashing."""
        extract = Graph()
        for subject in subjects:
            for triple in self.source.triples((subject, None, None)):
                extract.add(triple)
        return extract

    def _scope_members(self, population: Optional[Population]) -> Optional[Set[str]]:
        if population is None:
            return None
        members, _ = enumerate_population(self.source, population, at=self.produced_at)
        return {str(m) for m in members}

    # -- public API ---------------------------------------------------------

    def compile(self) -> CompiledSurface:
        """Execute the run and return everything it produced."""
        logger.info("Compiling %s", self.contract.iri)
        check_entailment_regime(self.contract.profile)

        self._read_declaration()
        if self.contract.is_index:
            self._compile_index()
        else:
            self._compile_promotion()
        self._compile_assertions()
        stack_depth = self._compile_stacked_inputs()

        for name, graph, comment in (
            ("core", self.core, "Generated surface definitions."),
            ("closure", self.closure, "Generated closure surface."),
            ("assertions", self.assertions, "Generated surface assertions."),
        ):
            if len(graph) == 0:
                continue
            imports = [URIRef(SURFACE_ONTOLOGY)]
            if name != "core" and len(self.core) > 0:
                imports.append(URIRef(f"{self.base}/core"))
            self._ontology_header(
                graph,
                URIRef(f"{self.base}/{name}"),
                imports,
                comment + " Compilation output, not an authored source.",
            )

        compiled = CompiledSurface(
            contract=self.contract,
            modules={"core": self.core, "closure": self.closure, "assertions": self.assertions},
            symbols=self.symbols,
            population=self.population,
            read_set=self.read_set,
            stack_depth=stack_depth,
            signature_scope=self.signature_scope,
            well_founded=self.well_founded,
            produced_at=self.produced_at,
            warnings=self.warnings,
        )
        compiled.artefact_hash = canonical.combine(
            canonical.hash_graph(module) for module in compiled.content_modules()
        )
        compiled.semantic_hash = canonical.combine(entry.digest for entry in self.read_set)
        compiled.modules["manifest"] = self._manifest(compiled)
        logger.info(
            "Compiled %s: %d symbol(s), artefact %s",
            self.contract.iri,
            len(self.symbols),
            compiled.artefact_hash[:16],
        )
        return compiled

    # -- read set -----------------------------------------------------------

    def _read_declaration(self) -> None:
        declaration = self._subgraph(self.analyser.declaration_subjects(self.contract))
        self.read_set.append(
            ReadSetRecord(
                kind=SRF.DeclarationSource,
                source=self.contract.iri,
                digest=canonical.hash_graph(declaration),
            )
        )

    # -- index contracts ----------------------------------------------------

    def _compile_index(self) -> None:
        contract = self.contract
        self.population, scheme = enumerate_population(
            self.source, contract.population, at=self.produced_at
        )

        if scheme is not None:
            scheme_graph = self._subgraph([scheme, *self.population])
            for triple in self.source.triples((None, SKOS.inScheme, scheme)):
                scheme_graph.add(triple)
            self.read_set.append(
                ReadSetRecord(
                    kind=SRF.BoundSchemeSource,
                    source=scheme,
                    digest=canonical.hash_graph(scheme_graph),
                )
            )

        if len(self.population) > WARN_POPULATION:
            self.warnings.append(
                f"{len(self.population)} values enumerated for a per-value index form; "
                f"consider a DirectProperty form instead"
            )
        if len(self.population) > contract.budget():
            raise CompileError(
                f"{contract.iri} enumerated {len(self.population)} values, over its budget "
                f"of {contract.budget()} (law srf:S4). Use a DirectProperty index form, or "
                f"raise the budget deliberately."
            )

        family = self.minter.family_class()
        self.core.add((family, RDF.type, OWL.Class))
        self.core.add((family, RDFS.subClassOf, SRF.GeneratedClass))
        self.core.add((family, RDFS.subClassOf, contract.carrier))
        self.core.add(
            (
                family,
                RDFS.comment,
                Literal(f"Generated family class for surface contract {contract.key}."),
            )
        )
        self.core.add((family, RDFS.isDefinedBy, self.minter.surface_record()))

        if contract.has_form(NOMINAL) or contract.has_form(MEMBERSHIP):
            self._compile_nominal_classes(family)
        if contract.has_form(CLOSURE):
            self._compile_closure_relation()
        if contract.has_form(DIRECT):
            self._compile_direct_property()

    def _compile_nominal_classes(self, family: URIRef) -> None:
        contract = self.contract
        minted = [(str(v), self.minter.nominal_class(str(v))) for v in self.population]
        check_injective(minted)

        for value, symbol in minted:
            self.core.add((symbol, RDF.type, OWL.Class))
            self.core.add((symbol, RDFS.subClassOf, family))
            self.core.add((symbol, RDFS.isDefinedBy, self.minter.surface_record()))
            if contract.has_form(NOMINAL) and contract.emits_definitions:
                if contract.has_inverse_step:
                    raise CompileError(
                        f"{contract.iri} declares a NominalClass definition over a read path "
                        f"containing an inverse step, which leaves OWL 2 EL. Emit "
                        f"MembershipAssertion instead, or drop the inverse step."
                    )
                self._nominal_definition(symbol, URIRef(value))
            self.symbols.append(SymbolRecord(symbol, NOMINAL, URIRef(value)))

    def _compile_closure_relation(self) -> None:
        contract = self.contract
        if contract.multi_hop:
            raise CompileError(
                f"{contract.iri} declares a ClosureRelation over a multi-hop read path; "
                f"promote the value first, then index the promoted property."
            )
        relation = self.minter.closure_relation()
        self.core.add((relation, RDF.type, OWL.ObjectProperty))
        self.core.add((relation, RDFS.subPropertyOf, SRF.generatedRelation))
        self.core.add((relation, RDFS.domain, contract.carrier))
        self.core.add((relation, RDFS.isDefinedBy, self.minter.surface_record()))
        self.symbols.append(SymbolRecord(relation, CLOSURE))

        if contract.emits_definitions:
            self._closure_rule(relation)

        basis_graph = Graph()
        for value in self.population:
            for triple in self.source.triples((value, contract.closure_basis, None)):
                basis_graph.add(triple)
        self.read_set.append(
            ReadSetRecord(
                kind=SRF.DeclarationSource,
                source=contract.closure_basis,
                digest=canonical.hash_graph(basis_graph),
            )
        )

    def _compile_direct_property(self) -> None:
        direct = self.minter.direct_property()
        self.core.add((direct, RDF.type, OWL.ObjectProperty))
        self.core.add((direct, RDFS.subPropertyOf, SRF.generatedRelation))
        self.core.add((direct, RDFS.domain, self.contract.carrier))
        self.core.add((direct, RDFS.isDefinedBy, self.minter.surface_record()))
        self.symbols.append(SymbolRecord(direct, DIRECT))

    # -- promotion contracts ------------------------------------------------

    def _compile_promotion(self) -> None:
        contract = self.contract
        in_namespace = str(contract.promotes_to).startswith(str(contract.target_namespace))
        self.signature_scope = SRF.LocalSignature if in_namespace else SRF.SourceSignature

        if not in_namespace and contract.lossy:
            raise CompileError(
                f"{contract.iri} promotes a derived or crosswalk-inexact value onto "
                f"{contract.promotes_to}, which is outside the contract's target namespace. "
                f"A lossy promotion lands on a generated property so that its derived nature "
                f"is visible in the identifier (law srf:X6)."
            )

        if in_namespace:
            # The promoted property is minted by this contract, so the surface
            # declares it and accounts for it as one of its own symbols.
            self.core.add((contract.promotes_to, RDF.type, OWL.ObjectProperty))
            self.core.add((contract.promotes_to, RDFS.subPropertyOf, SRF.generatedRelation))
            self.core.add((contract.promotes_to, RDFS.domain, contract.carrier))
            self.core.add((contract.promotes_to, RDFS.isDefinedBy, self.minter.surface_record()))
            self.symbols.append(SymbolRecord(contract.promotes_to, DIRECT))

        if contract.emits_definitions:
            if not in_namespace:
                raise CompileError(
                    f"{contract.iri} is definition-only but promotes onto an authored "
                    f"property; a property chain axiom on an authored term is not "
                    f"conservative (law srf:X6)."
                )
            if contract.has_inverse_step:
                raise CompileError(
                    f"{contract.iri} is definition-only over a read path containing an "
                    f"inverse step; emit a materialised promotion instead."
                )
            self._property_chain(contract.promotes_to)

    # -- assertions ---------------------------------------------------------

    def _compile_assertions(self) -> None:
        contract = self.contract
        if not contract.emits_assertions:
            return
        instances = carrier_instances(self.source, contract.carrier)
        if not instances:
            return

        instance_graph = Graph()
        for instance in instances:
            for triple in self.source.triples((instance, None, None)):
                instance_graph.add(triple)
            for value in evaluate_path(self.source, instance, contract):
                if isinstance(value, URIRef):
                    for triple in self.source.triples((value, None, None)):
                        instance_graph.add(triple)
        self.read_set.append(
            ReadSetRecord(
                kind=SRF.InstanceGraphSource,
                source=contract.carrier,
                digest=canonical.hash_graph(instance_graph),
            )
        )

        population = {str(v) for v in self.population}
        scope = self._scope_members(contract.closure_scope) if contract.is_index else None
        relation = self.minter.closure_relation() if contract.has_form(CLOSURE) else None

        for instance in instances:
            for value in evaluate_path(self.source, instance, contract):
                if not contract.is_index:
                    self.assertions.add((instance, contract.promotes_to, value))
                    continue
                if not isinstance(value, URIRef):
                    continue
                if contract.has_form(MEMBERSHIP) and str(value) in population:
                    self.assertions.add(
                        (instance, RDF.type, self.minter.nominal_class(str(value)))
                    )
                if contract.has_form(DIRECT):
                    self.assertions.add((instance, self.minter.direct_property(), value))
                if relation is not None:
                    try:
                        for ancestor in ancestors(
                            self.source, value, contract.closure_basis, scope
                        ):
                            self.closure.add((instance, relation, ancestor))
                    except CyclicClosureBasis:
                        self.well_founded = False
                        raise

    # -- stacking -----------------------------------------------------------

    def _compile_stacked_inputs(self) -> int:
        """Fold stacked inputs into the read set, and check the composition laws
        ADR-A21 states: signature scope and profile identity both compose
        across a stack, so a source-signature or mixed-profile input upgrades
        this surface rather than being silently absorbed.
        """
        depth = 0
        identities: Set[str] = set()
        for entry in self.input_surfaces:
            self.read_set.append(
                ReadSetRecord(
                    kind=SRF.SurfaceSource, source=entry.surface, digest=entry.artefact_hash
                )
            )
            depth = max(depth, entry.depth + 1)
            if entry.signature_scope == str(SRF.SourceSignature):
                # X1 composition: conservative over a non-conservative input is
                # not conservative either.
                self.signature_scope = SRF.SourceSignature
            if entry.profile_identity is not None:
                identities.add(entry.profile_identity)

        own_identity = self.contract.profile.identity_hash()
        identities.add(own_identity)
        if len(identities) > 1:
            raise CompileError(
                f"{self.contract.iri} stacks over input surface(s) generated under a "
                f"different profile identity; every surface in a stack shares one profile "
                f"identity, checked statically (law srf:R1 composition, ADR-A21)."
            )

        permitted = self.contract.profile.permitted_stack_depth
        if depth > permitted:
            raise CompileError(
                f"{self.contract.iri} reads {depth} surface(s) deep but its profile permits "
                f"{permitted} (law srf:S10)."
            )
        return depth

    # -- emission primitives ------------------------------------------------

    def _ontology_header(
        self, graph: Graph, iri: URIRef, imports: Sequence[URIRef], comment: str
    ) -> None:
        graph.add((iri, RDF.type, OWL.Ontology))
        for target in imports:
            graph.add((iri, OWL.imports, target))
        graph.add((iri, RDFS.comment, Literal(comment)))

    def _nominal_definition(self, symbol: URIRef, value: URIRef) -> None:
        """Emit ``symbol ≡ Carrier ⊓ ∃p1.(… ∃pn.{value})``.

        ``owl:hasValue`` and ``owl:someValuesFrom`` are both inside OWL 2 EL, so
        classification over a large generated surface stays tractable. Blank
        nodes are labelled from the symbol they belong to, so regeneration is
        byte-identical.
        """
        label = self.minter.blank_label(symbol, "def")
        definition = BNode(label)
        self.core.add((symbol, OWL.equivalentClass, definition))
        self.core.add((definition, RDF.type, OWL.Class))

        innermost: Node = value
        for position in reversed(range(len(self.contract.path))):
            step = self.contract.path[position]
            restriction = BNode(f"{label}_r{position}")
            self.core.add((restriction, RDF.type, OWL.Restriction))
            self.core.add((restriction, OWL.onProperty, step.prop))
            if position == len(self.contract.path) - 1:
                self.core.add((restriction, OWL.hasValue, innermost))
            else:
                self.core.add((restriction, OWL.someValuesFrom, innermost))
            innermost = restriction

        head = self._rdf_list(self.core, f"{label}_l", [self.contract.carrier, innermost])
        self.core.add((definition, OWL.intersectionOf, head))

    def _property_chain(self, prop: URIRef) -> None:
        label = self.minter.blank_label(prop, "chain")
        head = self._rdf_list(
            self.core, f"{label}_l", [step.prop for step in self.contract.path]
        )
        self.core.add((prop, OWL.propertyChainAxiom, head))

    @staticmethod
    def _rdf_list(graph: Graph, label_stem: str, items: Sequence[Node]) -> Node:
        """Write an rdf:List with deterministic cell labels.

        ``rdflib.collection.Collection`` would do this in one line, but it mints
        its own blank-node labels, and the whole point of labelling cells from
        the term they belong to is that a regenerated module diffs cleanly.
        """
        if not items:
            return RDF.nil
        cells = [BNode(f"{label_stem}{index}") for index in range(len(items))]
        for index, (cell, item) in enumerate(zip(cells, items)):
            graph.add((cell, RDF.first, item))
            rest = cells[index + 1] if index + 1 < len(cells) else RDF.nil
            graph.add((cell, RDF.rest, rest))
        return cells[0]

    def _closure_rule(self, relation: URIRef) -> None:
        """A per-contract SHACL rule with the declared basis bound into the query.

        SPARQL admits no property path over a variable predicate, so a rule that
        worked for any declared basis cannot be written once and shipped. The
        basis is bound here, at generation time, which is why this rule is
        generated rather than authored in the layer's own shapes.
        """
        rule_shape = self.minter.closure_rule()
        body = BNode(self.minter.blank_label(rule_shape, "rule"))
        step = self.contract.path[0]
        query = (
            "\n\t\t\tCONSTRUCT {\n"
            f"\t\t\t\t$this <{relation}> ?ancestor .\n"
            "\t\t\t}\n"
            "\t\t\tWHERE {\n"
            f"\t\t\t\t$this <{step.prop}> ?value .\n"
            f"\t\t\t\t?value <{self.contract.closure_basis}>* ?ancestor .\n"
            "\t\t\t}\n\t\t"
        )
        self.closure.add((rule_shape, RDF.type, SH.NodeShape))
        self.closure.add((rule_shape, SH.targetClass, self.contract.carrier))
        self.closure.add((rule_shape, SH.rule, body))
        self.closure.add((body, RDF.type, SH.SPARQLRule))
        self.closure.add((body, SH.construct, Literal(query)))

    # -- manifest -----------------------------------------------------------

    def _manifest(self, compiled: CompiledSurface) -> Graph:
        contract = self.contract
        graph = Graph()
        imports = [URIRef(SURFACE_ONTOLOGY)] + [
            URIRef(f"{self.base}/{name}")
            for name in ("core", "closure", "assertions")
            if len(compiled.modules[name]) > 0
        ]
        self._ontology_header(
            graph,
            URIRef(f"{self.base}/manifest"),
            imports,
            "Generated surface manifest: read set, symbol records, hashes, and law discharges.",
        )

        record = self.minter.surface_record()
        authority = compiled.authority
        graph.add((record, RDF.type, SRF.GeneratedSurface))
        graph.add((record, SRF.coversContract, contract.iri))
        graph.add((record, SRF.generatedByProfile, contract.profile.iri))
        graph.add((record, SRF.derivationAuthority, authority))
        graph.add((record, SRF.signatureScope, compiled.signature_scope))
        graph.add((record, SRF.producedAt, Literal(self.produced_at, datatype=XSD.dateTime)))
        graph.add(
            (
                record,
                SRF.stackDepth,
                Literal(compiled.stack_depth, datatype=XSD.nonNegativeInteger),
            )
        )
        graph.add((record, SRF.artefactHash, Literal(compiled.artefact_hash)))
        graph.add((record, SRF.semanticContentHash, Literal(compiled.semantic_hash)))
        if contract.is_index:
            graph.add(
                (
                    record,
                    SRF.populationSize,
                    Literal(len(compiled.population), datatype=XSD.nonNegativeInteger),
                )
            )

        for index, entry in enumerate(compiled.read_set):
            node = self.minter.read_set_entry(index)
            graph.add((record, SRF.hasReadSetEntry, node))
            graph.add((node, RDF.type, SRF.ReadSetEntry))
            graph.add((node, SRF.readsSource, entry.source))
            graph.add((node, SRF.readSourceKind, entry.kind))
            graph.add((node, SRF.readHash, Literal(entry.digest)))
            if entry.version is not None:
                graph.add((node, SRF.readVersion, Literal(entry.version)))

        counts: Dict[str, int] = {}
        for symbol in compiled.symbols:
            counts[str(symbol.form)] = counts.get(str(symbol.form), 0) + 1
            node = self.minter.symbol_record(symbol.term, contract.profile.punned)
            graph.add((record, SRF.hasSymbolCount, self.minter.symbol_count(str(symbol.form))))
            graph.add((node, RDF.type, SRF.GeneratedSymbol))
            graph.add((node, SRF.inSurface, record))
            graph.add((node, SRF.symbolForm, symbol.form))
            graph.add((node, SRF.denotes, symbol.term))
            graph.add((node, SRF.generatedByProfile, contract.profile.iri))
            graph.add((node, SRF.derivationAuthority, authority))
            graph.add((node, SRF.producedAt, Literal(self.produced_at, datatype=XSD.dateTime)))
            if symbol.value is not None:
                graph.add((node, SRF.fromValue, symbol.value))

        for form, count in sorted(counts.items()):
            tally = self.minter.symbol_count(form)
            graph.add((tally, RDF.type, SRF.SymbolCount))
            graph.add((tally, SRF.countForm, URIRef(form)))
            graph.add((tally, SRF.countValue, Literal(count, datatype=XSD.nonNegativeInteger)))

        if contract.is_index and contract.has_form(CLOSURE) and compiled.well_founded:
            self.discharge(graph, SRF.R5, "closure-basis-traversal")
        return graph

    def discharge(self, graph: Graph, law: URIRef, run: str) -> None:
        """Record that a runtime-conformance law held for this surface."""
        node = self.minter.law_discharge(str(law))
        graph.add((node, RDF.type, SRF.LawDischarge))
        graph.add((node, SRF.dischargesLaw, law))
        graph.add((node, SRF.dischargedForSurface, self.minter.surface_record()))
        graph.add((node, SRF.dischargedAt, Literal(self.produced_at, datatype=XSD.dateTime)))
        graph.add((node, SRF.executedRun, Literal(run)))


# ---------------------------------------------------------------------------
# Convenience entry points
# ---------------------------------------------------------------------------


def compile_contract(
    contract: Contract,
    source: Graph,
    produced_at: str,
    input_surfaces: Sequence[Tuple[URIRef, str, int]] = (),
) -> CompiledSurface:
    """Compile one contract. Kept as a function for symmetry with ``compile_mork_to_rml``."""
    return SurfaceCompiler(contract, source, produced_at, input_surfaces).compile()


def discharge_determinism(compiled: CompiledSurface, produced_at: str, run: str) -> None:
    """Record ``srf:R1`` on a surface whose regeneration was compared and matched."""
    compiler = SurfaceCompiler(compiled.contract, Graph(), produced_at)
    compiler.discharge(compiled.modules["manifest"], SRF.R1, run)


def stamp_content_version(graph: Graph) -> Graph:
    """Give a generated module a content-addressed version IRI: its ontology IRI
    followed by the first 16 hex digits of the module's canonical hash, taken
    without any version IRI. A regeneration that changes the module changes its
    version IRI, and one that does not keeps it (ADR-A86 addendum, item 5)."""
    ontologies = sorted(graph.subjects(RDF.type, OWL.Ontology))
    for ontology in ontologies:
        graph.remove((ontology, OWL.versionIRI, None))
    digest = canonical.hash_graph(graph)
    for ontology in ontologies:
        graph.add((ontology, OWL.versionIRI, URIRef(f"{ontology}/{digest[:16]}")))
    return graph


def render(compiled: CompiledSurface) -> Dict[str, str]:
    """Serialise every non-empty module, deterministically, each stamped with
    its content-addressed version IRI."""
    prefixes = dict(OUTPUT_PREFIXES)
    prefixes["exec"] = URIRef(str(compiled.contract.target_namespace))
    carrier = str(compiled.contract.carrier)
    source_namespace = (
        carrier.rsplit("#", 1)[0] + "#" if "#" in carrier else carrier.rsplit("/", 1)[0] + "/"
    )
    if source_namespace != str(compiled.contract.target_namespace):
        prefixes["src"] = URIRef(source_namespace)

    header = [
        "# SPDX-License-Identifier: MPL-2.0",
        "# Generated by the LATTICE surface compiler. Do not edit by hand.",
        f"# Contract: {compiled.contract.iri}",
        f"# Profile:  {compiled.contract.profile.iri}",
        "",
    ]
    return {
        name: serialise(stamp_content_version(graph), prefixes, header)
        for name, graph in compiled.modules.items()
        if len(graph) > 0
    }
