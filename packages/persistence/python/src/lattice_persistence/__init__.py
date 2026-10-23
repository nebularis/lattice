# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""LATTICE persistence caller library (ADR-A132). H2.8a: the typed terms, payload and rows, the profile's contract and the request digest. H2.8b: the payload bound, the caller check and the audit outcome."""

from .audit import AuditOutcome, AuditResult, SparqlClient, audit_outcome, run_audit
from .bound import outside_bound, outside_events
from .check import CallerCheckError, Membership, Refusal, check_request, refusals
from .contract import DigestContract, DigestSpec, OperationKind, ProfileOperation, read_contracts
from .digest import DigestError, request_digest
from .payload import EventRow, Lit, Payload, PayloadError, Rows, Triple
from .terms import Iri, Literal, SparqlTermError

__all__ = [
    "DigestContract", "DigestSpec", "OperationKind", "ProfileOperation", "read_contracts", "DigestError", "request_digest",
    "AuditOutcome", "AuditResult", "SparqlClient", "audit_outcome", "run_audit", "outside_bound", "outside_events", "CallerCheckError", "Membership",
    "Refusal", "check_request", "refusals", "EventRow", "Lit", "Payload", "PayloadError", "Rows", "Triple", "Iri", "Literal", "SparqlTermError",
]
