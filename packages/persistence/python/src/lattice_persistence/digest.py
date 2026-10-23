# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The request digest (ADR-A123 fifth addendum, patterns guide section 15.2, ADR-A132 decision 2).

``requestDigest = hex(SHA-256(enc([kind, target, expected, part, part, ...])))``

* ``enc`` is the length-prefixed tuple encoding of the guide's Chapter 5. For each component, the decimal length of its UTF-8 bytes,
  a colon, and the bytes.
* ``kind`` is the operation's kind as the profile names it (``Replace``, ``Append``), ``target`` is the IRI of the target without
  angle brackets, and ``expected`` is the expected seq as a decimal string. A part the operation does not have is the empty string.
* Each content part is one component. It is ``enc`` of the sorted, de-duplicated canonical N-Triples lines of the part's slots
  (the sorted lines, each a component). A triple's role is therefore part of what is hashed, and a triple in the added part is not the
  same request as the same triple in the dropped part. The parts follow the profile's ``partOrder``.
"""

from __future__ import annotations

import hashlib
from typing import Iterable, Mapping, Union

from .contract import CONTENT_ROLES, ProfileOperation
from .payload import Payload, Rows
from .terms import Iri


class DigestError(ValueError):
    """A digest that cannot be computed from the values given."""


def enc(components: Iterable[Union[str, bytes]]) -> bytes:
    """Length-prefixed tuple encoding: ``len(c) ":" c`` for each component, the length in bytes."""
    out = bytearray()
    for c in components:
        b = c.encode("utf-8") if isinstance(c, str) else c
        out += str(len(b)).encode("ascii") + b":" + b
    return bytes(out)


def digest_input(kind: str, target: str, expected: str, parts: Iterable[Iterable[str]]) -> bytes:
    """The bytes that are hashed. Each of ``parts`` is the canonical N-Triples lines of one content part, in the contract's order."""
    return enc([kind, target, expected, *(enc(sorted(set(lines))) for lines in parts)])


def digest_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iri_text(value) -> str:
    if isinstance(value, Iri):
        return str(value)[1:-1]
    if isinstance(value, str):
        return value
    raise DigestError(f"a target must be an IRI string, got {value!r}")


def _lines(slot: str, value) -> tuple:
    if isinstance(value, Payload):
        return value.lines()
    if isinstance(value, Rows):
        return value.payload().lines()
    raise DigestError(f"slot {slot!r} must be a Payload or Rows, got {type(value).__name__}")


def request_input(operation: ProfileOperation, values: Mapping[str, object]) -> bytes:
    """The bytes to hash for ``operation`` with the parameter and slot ``values`` of the request, read by the profile's digest contract."""
    spec = operation.digest
    if spec is None:
        raise DigestError(f"operation {operation.template_id} has no requestDigest")
    if spec.algorithm != "SHA-256":
        raise DigestError(f"unsupported digest algorithm {spec.algorithm!r}")
    kind, target, expected, content = operation.kind.value, "", "", []
    for part in spec.parts:
        for source in part.sources:
            if source not in values:
                raise DigestError(f"{operation.template_id} digest part {part.role} needs {source!r}, which was not given")
        if part.role == "OperationKindPart":
            continue
        if part.role == "TargetPart":
            target = _iri_text(values[part.sources[0]]) if part.sources else ""
        elif part.role == "ExpectedSeqPart":
            if part.sources:
                seq = values[part.sources[0]]
                if isinstance(seq, bool) or not isinstance(seq, int):
                    raise DigestError(f"the expected seq must be an int, got {seq!r}")
                expected = str(seq)
        elif part.role in CONTENT_ROLES:
            content.append([line for s in part.sources for line in _lines(s, values[s])])
        else:
            raise DigestError(f"unknown digest part role {part.role!r}")
    return digest_input(kind, target, expected, content)


def request_digest(operation: ProfileOperation, values: Mapping[str, object]) -> str:
    """The ``requestDigest`` of a request, as lower-case hex."""
    return digest_hex(request_input(operation, values))


__all__ = ["DigestError", "enc", "digest_input", "digest_hex", "request_input", "request_digest"]
