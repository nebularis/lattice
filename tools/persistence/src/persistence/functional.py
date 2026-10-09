# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Reading a property that is meant to have one value.

``Graph.value`` returns whichever matching triple comes first, so a subject
that wrongly declares two values resolves differently according to the order
its triples were written in, and the compiler's output is no longer a
function of the configuration (law L1). Every read of a ``dal:`` property
that the compiler treats as single-valued goes through :func:`functional_value`
instead, which refuses a second value by name.

The structural SHACL shapes reject the same input (``sh:maxCount 1``), but
``compile`` does not run them, so the refusal is made here as well.
"""

from __future__ import annotations

from rdflib import Graph
from rdflib.term import Identifier, Node

from .model import CrossAxisViolation


def functional_value(graph: Graph, subject: Node | None, predicate: Node) -> Identifier | None:
    """The one value of ``predicate`` on ``subject``, or ``None`` if it has none.

    Raises :class:`~persistence.model.CrossAxisViolation` of kind
    ``MultiValuedFunctionalProperty`` if it has more than one distinct value.
    A ``None`` subject has no value, as with ``Graph.value``."""
    if subject is None:
        return None
    values = sorted(set(graph.objects(subject, predicate)), key=lambda term: (type(term).__name__, str(term)))
    if len(values) > 1:
        listed = ", ".join(repr(str(v)) for v in values)
        raise CrossAxisViolation(
            "MultiValuedFunctionalProperty",
            str(subject),
            f"{predicate} is single-valued but {subject} declares {len(values)} values ({listed}). "
            "Which one wins would depend on the order the triples were written in. Declare exactly one.",
        )
    return values[0] if values else None


__all__ = ["functional_value"]
