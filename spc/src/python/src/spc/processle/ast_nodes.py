# src/spc/processle/ast_nodes.py
"""
AST node types for ProcessLE.

Every construct in the ProcessLE grammar maps to one of these dataclasses.
The AST is the intermediate representation between the parser and the
DL encoder.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# --- Top Level ---

@dataclass
class Protocol:
    """A complete protocol definition."""
    name: str
    participants: list[Participant]
    global_type: GlobalType
    subprotocols: list[SubprotocolDecl] = field(default_factory=list)
    extensions: list[ExtensionAnnotation] = field(default_factory=list)


@dataclass
class Participant:
    """A participant (role) declaration."""
    name: str
    sort_constraints: list[str] = field(default_factory=list)


@dataclass
class SubprotocolDecl:
    """A subprotocol declaration: protocol P(r1: T1, ..., rn: Tn) = G"""
    name: str
    role_params: list[RoleParam]
    body: GlobalType


@dataclass
class RoleParam:
    name: str
    type_ref: Optional[str] = None


# --- Global Types ---

@dataclass
class GlobalType:
    """Base class for global type AST nodes."""
    pass


@dataclass
class Communication(GlobalType):
    """p → q : {lᵢ⟨Sᵢ⟩.Gᵢ}"""
    sender: str
    receiver: str
    options: list[MessageOption]


@dataclass
class MessageOption:
    """One branch of a communication: l⟨S⟩.G with optional refinement."""
    label: str
    sort: str
    refinement: Optional[Refinement] = None
    continuation: Optional[GlobalType] = None


@dataclass
class ParallelComp(GlobalType):
    """G₁ | G₂"""
    left: GlobalType
    right: GlobalType


@dataclass
class Recursion(GlobalType):
    """μt.G"""
    var: str
    body: GlobalType


@dataclass
class RecursionVar(GlobalType):
    """t (recursion variable reference)"""
    var: str


@dataclass
class End(GlobalType):
    """Termination."""
    pass


@dataclass
class SubprotocolCall(GlobalType):
    """r calls P⟨s₁, ..., sₙ⟩.G"""
    caller: str
    protocol_name: str
    role_args: list[str]
    continuation: Optional[GlobalType] = None


# --- Refinements ---

@dataclass
class Refinement:
    """A refinement predicate on a sort."""
    pass


@dataclass
class ConceptMembership(Refinement):
    """x ∈ C (OWL concept membership)"""
    concept_iri: str


@dataclass
class RoleAssertion(Refinement):
    """(x, y) ∈ R"""
    role_iri: str
    target_var: str


@dataclass
class ConjunctionRef(Refinement):
    """φ₁ ∧ φ₂"""
    left: Refinement
    right: Refinement


# --- Extension Annotations ---

@dataclass
class ExtensionAnnotation:
    """Base for extension annotations attached to protocol elements."""
    target_participant: Optional[str] = None
    target_label: Optional[str] = None
    target_state_desc: Optional[str] = None  # e.g., "after submit_risk"


@dataclass
class TimerAnnotation(ExtensionAnnotation):
    """Timeout / timer annotation."""
    timer_type: str = "interrupting"        # interrupting | non_interrupting
    duration: Optional[str] = None          # ISO 8601 duration, e.g., "PT72H"
    cron: Optional[str] = None
    timeout_label: Optional[str] = None


@dataclass
class RetryAnnotation(ExtensionAnnotation):
    """Retry policy annotation."""
    max_attempts: int = 3
    backoff: str = "exponential"            # none | constant | exponential | jitter
    base_delay: str = "PT2S"                # ISO 8601 duration
    multiplier: float = 2.0
    jitter_pct: float = 0.1
    max_delay: str = "PT60S"
    on_exhausted_label: Optional[str] = None
    on_exhausted_escalate: Optional[str] = None


@dataclass
class ErrorAnnotation(ExtensionAnnotation):
    """Error handler annotation."""
    error_type: str = "unknown"             # business | transport | timeout | validation
    recovery_label: Optional[str] = None
    escalate_to: Optional[str] = None


@dataclass
class CompensationAnnotation(ExtensionAnnotation):
    """Compensation pair annotation."""
    scope_name: str = "default"
    action_label: Optional[str] = None
    comp_label: Optional[str] = None
    ordering: str = "sequential"            # sequential | parallel


@dataclass
class SignalAnnotation(ExtensionAnnotation):
    """Signal emission/subscription annotation."""
    topic: Optional[str] = None
    exchange_type: str = "topic"
    routing_key_template: Optional[str] = None
    correlation_fields: list[str] = field(default_factory=list)
    direction: str = "emit"                 # emit | subscribe


@dataclass
class ConnectorAnnotation(ExtensionAnnotation):
    """Connector binding annotation."""
    connector_name: Optional[str] = None
    connector_type: str = "http"            # http | amqp
    base_url: Optional[str] = None
    auth: Optional[dict] = None
    timeout: Optional[str] = None
    headers: dict = field(default_factory=dict)