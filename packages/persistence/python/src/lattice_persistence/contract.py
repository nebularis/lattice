# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The contract of a generated operation, as a caller reads it from a compiled profile (ADR-A132 decisions 2 and 3, ADR-A123 and its
addenda).

The data classes are the ones ``persistence.contract`` in the compiler derives from an operation, moved here so that the compiler
depends on the library and never the reverse. :func:`read_contracts` reads them back from the RDF a compile emits (slice H2.7).
A caller needs nothing else of the compiler: the profile is the interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from rdflib import Graph
from rdflib.term import Node

from .namespaces import DAL


class OperationKind(Enum):
    """The logical kind of an operation. A relational realisation and a model compare operations by kind, not by the SPARQL a
    builder writes."""

    CREATE = "Create"
    BOOTSTRAP = "Bootstrap"
    REPLACE = "Replace"
    TOMBSTONE = "Tombstone"
    APPEND = "Append"
    APPEND_VERSION = "AppendVersion"
    UNCONDITIONAL_WRITE = "UnconditionalWrite"
    VALUE_GUARDED_REPLACE = "ValueGuardedReplace"
    KEY_CLAIM_WRITE = "KeyClaimWrite"
    KEY_CLAIM_WRITE_DUAL = "KeyClaimWriteDual"
    KEY_CLAIM_RETIRE = "KeyClaimRetire"
    QUARANTINE = "Quarantine"
    MERGE_REWRITE = "MergeRewrite"
    AUDIT = "Audit"
    MEMBERS_READ = "MembersRead"
    PAYLOAD_CHECK = "PayloadCheck"


@dataclass(frozen=True, order=True)
class ParameterContract:
    name: str
    kind: str
    required: bool
    equals_graph_name: bool = False
    sourced_from_registry: bool = False


@dataclass(frozen=True, order=True)
class EdgeContract:
    """One edge of the boundary shape that leads to a node, as a caller's check reads it (H2.6e): where it leaves, the step, its
    ownership, the class it leads to and its reference mode (``ByIdentity`` or ``Pinned``)."""

    source_shape: str
    predicate: str
    inverse: bool
    ownership: str
    target_class: Optional[str]
    reference_mode: str
    target_shape: Optional[str] = None


@dataclass(frozen=True)
class PayloadContract:
    """What an operation takes as the aggregate's triples. ``root`` names the parameter whose value the payload's walk starts at, and
    ``shape`` is the family's boundary shape, ``None`` where it names none (H2.8b: then only the payload's form is checked)."""

    parameter: str
    root: Optional[str]
    edges: tuple = ()
    shape: Optional[str] = None


# The digest's content parts, in the fixed order of the contract: the payload of a write, or for an append the events, then for a
# replace under a patch log the asserted and the retracted triples, and for an append of versions under delta membership the added
# and the dropped members in the same two parts. The first three parts are the operation kind, the target and the expected seq.
CONTENT_ROLES = frozenset({"PayloadPart", "EventPart", "AddPart", "DelPart"})


@dataclass(frozen=True)
class DigestContract:
    """What the request digest is taken over, as the compiler derives it from an operation: the target it names, the sequence it
    expects, and the slots whose triples the request asserts. :meth:`parts` is the list a compiled profile declares."""

    target: Optional[str]
    expected: Optional[str]
    payload: Optional[str]
    event: tuple = ()
    add: Optional[str] = None
    delete: Optional[str] = None

    def parts(self) -> tuple:
        """``(role, sources)`` for each part, in order. A part with no source has an empty tuple. The event part replaces the payload
        part for an append, whose rows slot and triples slot are its two sources."""
        return (
            ("OperationKindPart", ()),
            ("TargetPart", (self.target,) if self.target else ()),
            ("ExpectedSeqPart", (self.expected,) if self.expected else ()),
            ("EventPart", self.event) if self.event else ("PayloadPart", (self.payload,) if self.payload else ()),
            *((("AddPart", (self.add,)),) if self.add else ()),
            *((("DelPart", (self.delete,)),) if self.delete else ()),
        )


@dataclass(frozen=True, order=True)
class DigestPart:
    order: int
    role: str
    sources: tuple = ()


@dataclass(frozen=True)
class DigestSpec:
    """The digest contract of one operation as a profile declares it: the algorithm and the parts, sorted by ``order``."""

    algorithm: str
    parts: tuple

    def as_pairs(self) -> tuple:
        return tuple((p.role, p.sources) for p in self.parts)


@dataclass(frozen=True)
class ProfileOperation:
    """One generated operation of a compiled profile, as far as a caller needs it. ``node`` is the operation's node in the
    profile and ``template_id`` is its builder's name."""

    node: Node
    template_id: str
    kind: OperationKind
    version: int
    parameters: tuple
    payload: Optional[PayloadContract]
    digest: Optional[DigestSpec]
    bindings: tuple = ()
    examines: Optional[str] = None
    outcomes: tuple = ()

    def binding(self, name: str) -> Optional[str]:
        """The text of a compile-time binding of the operation, such as ``graphPrefix``. ``None`` where it has none."""
        return next((value for key, value in self.bindings if key == name), None)

    def parameter(self, name: str) -> Optional[ParameterContract]:
        return next((p for p in self.parameters if p.name == name), None)


class ProfileError(ValueError):
    """A compiled profile that does not say what a caller needs."""


def _local(node) -> str:
    return str(node).rsplit("#", 1)[-1]


def _one(g: Graph, subject, predicate):
    values = list(g.objects(subject, predicate))
    if len(values) != 1:
        raise ProfileError(f"{subject} should have exactly one {_local(predicate)}, found {len(values)}")
    return values[0]


def _param_name(g: Graph, node) -> str:
    return str(_one(g, node, DAL.parameterName))


def _suffixless(node, suffix: str) -> str:
    name = _local(node)
    return name.removesuffix(suffix)


def _digest(g: Graph, node) -> DigestSpec:
    parts = []
    for p in g.objects(node, DAL.digestPart):
        sources = tuple(sorted(_param_name(g, s) for s in g.objects(p, DAL.partSource) if s != DAL.NoSource))
        parts.append(DigestPart(int(_one(g, p, DAL.partOrder)), _local(_one(g, p, DAL.partRole)), sources))
    parts.sort()
    return DigestSpec(str(_one(g, node, DAL.digestAlgorithm)), tuple(parts))


def _payload(g: Graph, node) -> PayloadContract:
    root = next(iter(g.objects(node, DAL.payloadRoot)), None)
    edges = tuple(sorted(
        EdgeContract(
            str(_one(g, e, DAL.edgeSource)), str(_one(g, e, DAL.edgePredicate)), bool(_one(g, e, DAL.edgeInverse).toPython()),
            _local(_one(g, e, DAL.edgeOwnership)), None if (t := next(iter(g.objects(e, DAL.edgeTargetClass)), None)) is None else str(t),
            _local(_one(g, e, DAL.referenceMode)),
            None if (ts := next(iter(g.objects(e, DAL.edgeTargetShape)), None)) is None else str(ts),
        )
        for e in g.objects(node, DAL.referenceEdge)
    ))
    shape = _one(g, node, DAL.boundaryShape)
    return PayloadContract(
        _param_name(g, _one(g, node, DAL.payloadParameter)), None if root is None else _param_name(g, root), edges,
        None if shape == DAL.NoBoundaryShape else str(shape),
    )


def _bindings(g: Graph, node) -> tuple:
    """``(name, text)`` for each compile-time binding of an operation, the text as the compile encoded it."""
    return tuple(sorted((str(_one(g, b, DAL.paramName)), str(_one(g, b, DAL.paramValue))) for b in g.objects(node, DAL.hasParameterBinding)))


def read_contracts(g: Graph) -> tuple:
    """The :class:`ProfileOperation` of every generated operation in a compiled profile, in a stable order (template, then kind,
    then the operation's parameters). The profile is read as RDF and nothing is looked up in the compiler."""
    out = []
    for node in set(g.subjects(DAL.operationKind, None)):
        template = _one(g, node, DAL.usesTemplate)
        parameters = []
        for pn in g.objects(node, DAL.parameter):
            parameters.append(ParameterContract(
                _param_name(g, pn), _suffixless(_one(g, pn, DAL.parameterKind), "Kind"), bool(_one(g, pn, DAL.required).toPython()),
                (pn, DAL.mustEqual, None) in g, (pn, DAL.sourcedFrom, None) in g,
            ))
        pc = next(iter(g.objects(node, DAL.payloadContract)), None)
        dc = next(iter(g.objects(node, DAL.digestContract)), None)
        out.append(ProfileOperation(
            node, str(_one(g, template, DAL.templateId)), OperationKind(_local(_one(g, node, DAL.operationKind))),
            int(_one(g, node, DAL.templateVersion)), tuple(sorted(parameters)),
            None if pc is None else _payload(g, pc), None if dc is None else _digest(g, dc), _bindings(g, node),
            None if (ex := next(iter(g.objects(node, DAL.examinedParameter)), None)) is None else _param_name(g, ex),
            tuple(sorted(_local(o) for o in g.objects(node, DAL.reportsOutcome))),
        ))
    return tuple(sorted(out, key=lambda o: (o.template_id, o.kind.value, tuple(p.name for p in o.parameters), str(o.node))))


__all__ = [
    "OperationKind", "ParameterContract", "EdgeContract", "PayloadContract", "DigestContract", "DigestPart", "DigestSpec",
    "ProfileOperation", "ProfileError", "CONTENT_ROLES", "read_contracts",
]
