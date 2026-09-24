# SPDX-License-Identifier: MPL-2.0
"""Data model and exception types for the Vocabulary resolver.

See ontology/vocabulary/README.md §4 and ADR-A85 for the law these types
implement, and docs/developer/sketches/vocabulary-temporal-binding.md for the
invariants they are meant to protect.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import FrozenSet, Optional, Tuple

from rdflib import URIRef


@dataclasses.dataclass(frozen=True)
class Binding:
    """One voc:SchemeBinding, read out of a graph in resolver-usable form."""

    node: URIRef
    contract: URIRef
    scheme: URIRef
    scopes: FrozenSet[URIRef]
    valid_from: datetime
    valid_to: Optional[datetime]

    def scope_matches(self, context: FrozenSet[URIRef]) -> bool:
        """True when every scope this binding names is present in `context`.
        A binding naming no scope always matches (README §4: "no scope means
        all contexts")."""
        return self.scopes.issubset(context)

    def temporal_matches(self, at: datetime) -> bool:
        """True when `at` falls within this binding's validity window.
        The end of an interval is exclusive; an open-ended interval
        (valid_to is None) never excludes on that side."""
        if at < self.valid_from:
            return False
        if self.valid_to is not None and at >= self.valid_to:
            return False
        return True

    def is_applicable(self, context: FrozenSet[URIRef], at: datetime) -> bool:
        return self.scope_matches(context) and self.temporal_matches(at)


@dataclasses.dataclass(frozen=True)
class CandidateTrace:
    """One line of a resolution's decision trace: what a single binding did
    against the supplied context and time, whether or not it ended up
    applicable or winning."""

    node: URIRef
    scopes: FrozenSet[URIRef]
    scope_match: bool
    temporal_match: bool
    applicable: bool

    @property
    def as_dict(self) -> dict:
        return {
            "node": str(self.node),
            "scopes": sorted(str(s) for s in self.scopes),
            "scope_match": self.scope_match,
            "temporal_match": self.temporal_match,
            "applicable": self.applicable,
        }


@dataclasses.dataclass(frozen=True)
class Resolution:
    """The outcome of a successful resolve() call: exactly one scheme, plus
    the full candidate trace that produced it (the validation pack's
    "resolver decision trace" artefact)."""

    contract: URIRef
    scheme: URIRef
    used_fallback: bool
    winning_binding: Optional[URIRef]
    candidates: Tuple[CandidateTrace, ...]

    def describe(self) -> str:
        lines = [f"resolution for {self.contract}:"]
        for c in self.candidates:
            lines.append(
                f"  {c.node}: scopes={sorted(str(s) for s in c.scopes)} "
                f"scope_match={c.scope_match} temporal_match={c.temporal_match} "
                f"applicable={c.applicable}"
            )
        if self.used_fallback:
            lines.append(f"  -> no applicable binding; used boundScheme fallback {self.scheme}")
        else:
            lines.append(f"  -> winner {self.winning_binding}, scheme {self.scheme}")
        return "\n".join(lines)


class ResolutionError(Exception):
    """Base class for every way resolve() can fail to produce a scheme."""


class NoApplicableBindingError(ResolutionError):
    """No binding applies in the supplied context/time, and the contract has
    no voc:boundScheme fallback either."""

    def __init__(self, contract: URIRef):
        super().__init__(
            f"no applicable binding and no boundScheme fallback for {contract}"
        )
        self.contract = contract


class BindingConflictError(ResolutionError):
    """More than one applicable binding survives strict-superset precedence.
    A governance error, per ADR-A85 — never resolved silently."""

    def __init__(self, contract: URIRef, candidates: Tuple[Binding, ...]):
        names = ", ".join(str(c.node) for c in candidates)
        super().__init__(
            f"equal-specificity binding conflict for {contract}: {names}"
        )
        self.contract = contract
        self.candidates = candidates
