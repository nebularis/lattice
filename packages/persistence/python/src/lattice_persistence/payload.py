# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The typed payload and the typed event rows (ADR-A132 decision 2, ADR-A123 and its fifth addendum).

A :class:`Payload` is a set of ground triples. Each term is a validated :class:`~lattice_persistence.terms.Iri` or a :class:`Lit`,
and a blank node cannot be built, so a payload cannot name a node the store would mint. It renders two texts.

* :meth:`Payload.nt` is the canonical N-Triples the request digest is taken over. One line per triple, sorted by the UTF-8 bytes of
  the line, with no duplicate. A literal escapes only backslash, quote, line feed and carriage return, a typed literal of
  ``xsd:string`` is written plain, and a language tag is lower case.
* :meth:`Payload.sparql` is the text that fills a request-time slot. It is built from the encoders of ``lattice_persistence.terms``
  and never from a string, because a slot can sit in an update's ``WHERE``, where a malformed text changes a guard.

:class:`Rows` does the same for the rows of an append's events. Its text is the ``VALUES`` rows of the ``eventRows`` slot.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Union

from rdflib import BNode, URIRef
from rdflib import Literal as RdfLiteral
from rdflib.namespace import RDF, XSD

from .namespaces import PAT
from .terms import Iri, Literal, SparqlTermError

_XSD_STRING = str(XSD.string)
_XSD_LONG = str(XSD.long)
_LONG_RANGE = range(-(2**63), 2**63)


class PayloadError(ValueError):
    """A payload, or a row, that cannot be built: a blank node, a term that is not typed, or a value out of range."""


@dataclass(frozen=True, order=True)
class Lit:
    """A ground literal. ``datatype`` and ``lang`` are mutually exclusive, and ``xsd:string`` is the same as no datatype."""

    value: str
    datatype: Optional[str] = None
    lang: Optional[str] = None

    def __post_init__(self) -> None:
        datatype = None if self.datatype == _XSD_STRING else self.datatype
        lang = self.lang.lower() if self.lang else None
        object.__setattr__(self, "datatype", datatype)
        object.__setattr__(self, "lang", lang)
        try:
            self.value.encode("utf-8")
            self.sparql()
        except (SparqlTermError, UnicodeEncodeError, AttributeError) as error:
            raise PayloadError(f"not a literal: {error}") from error

    def nt(self) -> str:
        escaped = self.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
        text = f'"{escaped}"'
        if self.datatype:
            return f"{text}^^<{self.datatype}>"
        return f"{text}@{self.lang}" if self.lang else text

    def sparql(self) -> str:
        return str(Literal.encode(self.value, self.datatype, self.lang))


Object = Union[Iri, Lit]


@dataclass(frozen=True, order=True)
class Triple:
    subject: Iri
    predicate: Iri
    object: Object

    def __post_init__(self) -> None:
        for name, term, allowed in (
            ("subject", self.subject, Iri), ("predicate", self.predicate, Iri), ("object", self.object, (Iri, Lit)),
        ):
            if not isinstance(term, allowed):
                shown = "a blank node" if isinstance(term, str) and term.startswith("_:") else repr(term)
                raise PayloadError(f"the {name} of a payload triple must be an Iri{' or a Lit' if name == 'object' else ''}, got {shown}")

    def nt(self) -> str:
        obj = self.object.nt() if isinstance(self.object, Lit) else str(self.object)
        return f"{self.subject} {self.predicate} {obj} ."

    def sparql(self) -> str:
        obj = self.object.sparql() if isinstance(self.object, Lit) else str(self.object)
        return f"{self.subject} {self.predicate} {obj} ."


def _term(node) -> Object:
    """The typed term for an rdflib node. A blank node is refused."""
    if isinstance(node, BNode):
        raise PayloadError(f"a payload holds no blank node, got {node.n3()}")
    try:
        if isinstance(node, URIRef):
            return Iri.encode(str(node))
        if isinstance(node, RdfLiteral):
            return Lit(str(node), str(node.datatype) if node.datatype else None, node.language)
    except SparqlTermError as error:
        raise PayloadError(str(error)) from error
    raise PayloadError(f"not an RDF term: {node!r}")


@dataclass(frozen=True)
class Payload:
    """Ground triples, with no blank node, as a set."""

    triples: frozenset = frozenset()

    def __post_init__(self) -> None:
        bad = [t for t in self.triples if not isinstance(t, Triple)]
        if bad:
            raise PayloadError(f"a payload holds Triple values only, got {bad[0]!r}")

    @classmethod
    def of(cls, *triples: Triple) -> "Payload":
        return cls(frozenset(triples))

    @classmethod
    def from_rdflib(cls, triples: Iterable[tuple]) -> "Payload":
        """A payload from rdflib ``(s, p, o)`` terms, such as a ``Graph``. A blank node is refused, since the store would mint it."""
        return cls(frozenset(Triple(_term(s), _term(p), _term(o)) for s, p, o in triples))  # type: ignore[arg-type]

    def lines(self) -> tuple:
        return tuple(sorted({t.nt() for t in self.triples}))

    def nt(self) -> str:
        return "\n".join(self.lines())

    def sparql(self) -> str:
        return "\n".join(sorted({t.sparql() for t in self.triples}))

    def subjects(self) -> frozenset:
        return frozenset(t.subject for t in self.triples)

    def __len__(self) -> int:
        return len(self.triples)


@dataclass(frozen=True, order=True)
class EventRow:
    """One row of an append: the event, its type, its position in the batch and when it occurred."""

    event: Iri
    event_type: Iri
    op_seq: int
    occurred_at: Lit

    def __post_init__(self) -> None:
        if not isinstance(self.event, Iri) or not isinstance(self.event_type, Iri):
            raise PayloadError("an event and its type must be Iri values")
        if isinstance(self.op_seq, bool) or not isinstance(self.op_seq, int) or self.op_seq not in _LONG_RANGE:
            raise PayloadError(f"opSeq must be an xsd:long, got {self.op_seq!r}")
        if not isinstance(self.occurred_at, Lit) or not self.occurred_at.datatype:
            raise PayloadError("occurredAt must be a typed literal")

    def op_seq_literal(self) -> Lit:
        return Lit(str(self.op_seq), _XSD_LONG)

    def triples(self) -> frozenset:
        """What the row asserts, and what the event part of the digest covers: the type, ``pat:opSeq`` and ``pat:occurredAt``."""
        s = self.event
        return frozenset({
            Triple(s, Iri.encode(str(RDF.type)), self.event_type),
            Triple(s, Iri.encode(str(PAT.opSeq)), self.op_seq_literal()),
            Triple(s, Iri.encode(str(PAT.occurredAt)), self.occurred_at),
        })

    def sparql(self) -> str:
        return f"({self.event} {self.event_type} {self.op_seq_literal().sparql()} {self.occurred_at.sparql()})"


@dataclass(frozen=True)
class Rows:
    """The rows of an append's events. The text fills the ``eventRows`` slot, which sits in the update's ``WHERE``."""

    rows: tuple = ()

    def __post_init__(self) -> None:
        bad = [r for r in self.rows if not isinstance(r, EventRow)]
        if bad:
            raise PayloadError(f"Rows holds EventRow values only, got {bad[0]!r}")
        object.__setattr__(self, "rows", tuple(sorted(set(self.rows), key=lambda r: (r.op_seq, str(r.event), str(r.event_type)))))

    def sparql(self) -> str:
        return "\n".join(r.sparql() for r in self.rows)

    def payload(self) -> Payload:
        """The triples the rows assert, as a payload."""
        return Payload(frozenset().union(*(r.triples() for r in self.rows)))

    def __len__(self) -> int:
        return len(self.rows)


__all__ = ["PayloadError", "Lit", "Triple", "Payload", "EventRow", "Rows"]
