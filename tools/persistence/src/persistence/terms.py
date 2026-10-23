# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""RDF-term encoding for the compiler. The encoders live in ``lattice_persistence.terms`` (ADR-A132 decision 3), which the compiler
and every caller share, and this module re-exports them. :class:`PropertyPath` stays here, since it renders a path expression with
``persistence.paths`` and the library has no use for one."""

from __future__ import annotations

from lattice_persistence.terms import Integer, Iri, Literal, SparqlTerm, SparqlTermError, Var


class PropertyPath(SparqlTerm):
    """A validated SPARQL property path, such as the one that reaches an aggregate's members.

    A path is structure and not a term, and it cannot be a variable, so it reaches a template as
    compile-time text. The operators come from a fixed set (:mod:`persistence.paths`) and every
    predicate in it is encoded by :meth:`Iri.encode`, so no adopter string reaches the query's
    structure except as an encoded IRI. The text is also parsed as a path before it is returned."""

    __slots__ = ()

    @classmethod
    def encode(cls, expr: "object") -> "PropertyPath":
        from rdflib.plugins.sparql import prepareQuery

        from .paths import render

        text = render(expr)  # type: ignore[arg-type]
        try:
            prepareQuery("SELECT * WHERE { ?a " + text + " ?b }")
        except Exception as error:
            raise SparqlTermError(f"property path {text!r} does not parse: {error}") from error
        return cls(text)


__all__ = ["SparqlTerm", "SparqlTermError", "Iri", "Literal", "Var", "Integer", "PropertyPath"]
