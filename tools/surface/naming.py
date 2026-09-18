# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Identifier minting.

Every identifier a surface generator emits is a pure function of the contract
key, the target namespace, the carrier's local name, and the value, under a
normalisation the generation profile declares. That is what makes regeneration
comparable: two runs over the same read set under the same profile mint the
same symbols or one of them is defective.

Injectivity is checked, not assumed. ``LocalNameFromValue`` is injective only
while local names are unique across the population; the moment two schemes bind
one dimension, or two namespaces share a local name, it is not.
``DigestLocalName`` is injective for any population and exists for that case.
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict, Iterable, List, Sequence, Tuple

from rdflib import URIRef

from .namespaces import SRF

UNRESERVED = re.compile(r"[^A-Za-z0-9_-]+")

VERBATIM = str(SRF.VerbatimLocalName)
SANITISED = str(SRF.SanitisedLocalName)

LOCAL_NAME_FROM_VALUE = str(SRF.LocalNameFromValue)
QUALIFIED_LOCAL_NAME = str(SRF.QualifiedLocalName)
DIGEST_LOCAL_NAME = str(SRF.DigestLocalName)

DIGEST_LENGTH = 16


class NamingCollision(ValueError):
    """Two distinct population members minted the same identifier (law srf:S6)."""


def local_name(iri: str) -> str:
    """The fragment after '#', or the segment after the final '/'."""
    text = str(iri)
    if "#" in text:
        return text.rsplit("#", 1)[1]
    return text.rstrip("/").rsplit("/", 1)[-1]


def normalise(text: str, mode: str) -> str:
    if mode == VERBATIM:
        return text
    if mode == SANITISED:
        return UNRESERVED.sub("_", text)
    raise ValueError(f"unknown naming normalisation: {mode}")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:DIGEST_LENGTH]


class Minter:
    """Mints every identifier one surface contract emits."""

    def __init__(
        self,
        target_namespace: str,
        contract_key: str,
        carrier: str,
        normalisation: str,
        naming_policy: str = LOCAL_NAME_FROM_VALUE,
        naming_prefix: str = "",
    ) -> None:
        self.namespace = str(target_namespace)
        self.key = normalise(contract_key, normalisation)
        self.carrier = normalise(local_name(carrier), normalisation)
        self.normalisation = normalisation
        self.policy = naming_policy
        self.prefix = normalise(naming_prefix, normalisation) if naming_prefix else ""

    # -- structural symbols -------------------------------------------------

    def family_class(self) -> URIRef:
        return URIRef(f"{self.namespace}{self.carrier}_{self.key}")

    def closure_relation(self) -> URIRef:
        return URIRef(f"{self.namespace}matches_{self.key}")

    def direct_property(self) -> URIRef:
        return URIRef(f"{self.namespace}value_{self.key}")

    def surface_record(self) -> URIRef:
        return URIRef(f"{self.namespace}surface_{self.key}")

    def read_set_entry(self, index: int) -> URIRef:
        return URIRef(f"{self.namespace}surface_{self.key}_read_{index}")

    def symbol_count(self, form: str) -> URIRef:
        return URIRef(f"{self.namespace}surface_{self.key}_count_{local_name(form)}")

    def law_discharge(self, law: str) -> URIRef:
        return URIRef(f"{self.namespace}surface_{self.key}_discharge_{local_name(law)}")

    def closure_rule(self) -> URIRef:
        return URIRef(f"{self.namespace}{self.carrier}_{self.key}_ClosureRule")

    def projection_mapping(self) -> URIRef:
        return URIRef(f"{self.namespace}projection_{self.key}")

    def projection_provenance(self) -> URIRef:
        return URIRef(f"{self.namespace}projection_{self.key}_provenance")

    def targeting_spec(self) -> URIRef:
        return URIRef(f"{self.namespace}projection_{self.key}_target")

    def parameter_binding(self, name: str) -> URIRef:
        return URIRef(f"{self.namespace}projection_{self.key}_param_{name}")

    # -- per-value symbols --------------------------------------------------

    def value_fragment(self, value: str) -> str:
        if self.policy == DIGEST_LOCAL_NAME:
            return digest(str(value))
        fragment = normalise(local_name(value), self.normalisation)
        if self.policy == QUALIFIED_LOCAL_NAME:
            return f"{self.prefix}_{fragment}" if self.prefix else fragment
        if self.policy == LOCAL_NAME_FROM_VALUE:
            return fragment
        raise ValueError(f"unknown naming policy: {self.policy}")

    def nominal_class(self, value: str) -> URIRef:
        return URIRef(f"{self.family_class()}_{self.value_fragment(value)}")

    def symbol_record(self, term: URIRef, punned: bool) -> URIRef:
        return term if punned else URIRef(f"{term}_symbol")

    def blank_label(self, term: URIRef, role: str) -> str:
        """A deterministic blank-node label, scoped to the term it belongs to."""
        return f"{local_name(str(term))}_{role}"


def check_injective(minted: Sequence[Tuple[str, URIRef]]) -> None:
    """Fail where two distinct values minted one identifier (law srf:S6)."""
    seen: Dict[str, str] = {}
    clashes: List[str] = []
    for value, term in minted:
        previous = seen.get(str(term))
        if previous is not None and previous != value:
            clashes.append(f"{term} <- {previous} and {value}")
        seen[str(term)] = value
    if clashes:
        raise NamingCollision(
            "naming policy is not injective over this population:\n  "
            + "\n  ".join(sorted(clashes))
        )


def sorted_values(values: Iterable[object]) -> List[URIRef]:
    """Population order is IRI order, so that emission order never varies."""
    return sorted((v for v in values if isinstance(v, URIRef)), key=str)
