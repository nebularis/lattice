# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The cases of the aggregate-over-an-error matrix (TSD-41, TSD-43, CCS C9b3) and a runner that gives each cell as a string.

A case is a data state and a query. The data states are the row states of one group, built the way a generated query builds
one, as ``?s a <urn:T>`` with an ``OPTIONAL`` for ``?x``, so a row with no value leaves ``?x`` unbound. The aggregate is over
``?x`` or an expression of it. :func:`cell` runs a case on rdflib or Oxigraph and :func:`dump` writes the cases for a runner
of another engine (Jena ARQ, see the Validation Pack). Run ``python -m mork_compilers.aggregate_error_cases DIR`` to write them."""

from __future__ import annotations

import re
from decimal import Decimal
import sys
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import XSD

from .engines import run_query

PRE = "@prefix : <urn:> .\n"
STATES = {
    "bound": ":s1 a :T ; :p 1 . :s2 a :T ; :p 2 .",
    "one unbound": ":s1 a :T ; :p 1 . :s2 a :T ; :p 2 . :s3 a :T .",
    "iri": ":s1 a :T ; :p 1 . :s2 a :T ; :p 2 . :s3 a :T ; :p :a .",
    "bnode": ":s1 a :T ; :p 1 . :s2 a :T ; :p 2 . :s3 a :T ; :p [] .",
    "all unbound": ":s1 a :T . :s2 a :T .",
    "empty": ":s0 a :U .",
    "empty grouped": ":s0 a :U .",
    "groups": ":s1 a :T ; :p 1, 2 . :s2 a :T . :s3 a :T ; :p 5 .",
}
BODY = "?s a <urn:T> . OPTIONAL { ?s <urn:p> ?x }"
SEP = '; separator=" "'
AGGREGATES = {
    "COUNT(?x)": "COUNT(?x)",
    "COUNT(expr)": "COUNT(STR(?x))",
    "COUNT(*)": "COUNT(*)",
    "COUNT(DISTINCT ?x)": "COUNT(DISTINCT ?x)",
    "COUNT(DISTINCT expr)": "COUNT(DISTINCT STR(?x))",
    "SUM": "SUM(?x)",
    "AVG": "AVG(?x)",
    "MIN": "MIN(?x)",
    "MAX": "MAX(?x)",
    "SAMPLE": "SAMPLE(?x)",
    "GROUP_CONCAT(expr)": f"GROUP_CONCAT(STR(?x){SEP})",
    "GROUP_CONCAT(?x)": f"GROUP_CONCAT(?x{SEP})",
    "GROUP_CONCAT(DISTINCT expr)": f"GROUP_CONCAT(DISTINCT STR(?x){SEP})",
}


REMEDY_STATES = ("bound", "one unbound", "iri", "bnode", "all unbound", "empty", "empty grouped")


def query(aggregate: str, state: str, body: str = BODY, projection: str | None = None) -> str:
    """The query for ``aggregate`` over ``body``, grouped by ``?s`` in the ``empty grouped`` state. It also projects a constant,
    since rdflib drops a row whose projected variables are all unbound (TSD-10), which would make an unbound aggregate look like an empty result."""
    grouped = state == "empty grouped"
    select = f"(1 AS ?k) {projection or f'({aggregate} AS ?g)'}"
    return f"SELECT {select} WHERE {{ {body} }}" + (" GROUP BY ?s" if grouped else "")


def matrix_cases() -> dict[str, tuple[str, str]]:
    """``{id: (state, query text)}`` for every aggregate and every state."""
    return {f"{label} | {state}": (state, query(text, state)) for label, text in AGGREGATES.items() for state in REMEDY_STATES}


# Remedies are probed on the states a remedy has to handle, and over the aggregates it applies to.
FILTERED = BODY + " FILTER(BOUND(?x))"
SUBSELECT = "{ SELECT ?s ?v WHERE { ?s a <urn:T> . OPTIONAL { ?s <urn:p> ?x } BIND(STR(?x) AS ?v) } }"
SUBSELECT_NUM = "{ SELECT ?s ?v WHERE { ?s a <urn:T> . OPTIONAL { ?s <urn:p> ?x } BIND(?x + 0 AS ?v) } }"
GC = SEP


def remedy_cases() -> dict[str, tuple[str, str]]:
    cases: dict[str, tuple[str, str]] = {}

    def add(remedy: str, label: str, aggregate: str, body: str = BODY, projection: str | None = None) -> None:
        for state in REMEDY_STATES:
            cases[f"{remedy} | {label} | {state}"] = (state, query(aggregate, state, body, projection))

    for label, text in AGGREGATES.items():
        add("a filter", label, text, FILTERED)
    for label in ("SUM", "AVG", "MIN", "MAX"):
        add("a2 filter numeric", label, AGGREGATES[label], BODY + " FILTER(isNumeric(?x))")
    add("b coalesce", "SUM(COALESCE(?x, 0))", "SUM(COALESCE(?x, 0))")
    add("b coalesce", "AVG(COALESCE(?x, 0))", "AVG(COALESCE(?x, 0))")
    add("b coalesce", "MAX(COALESCE(?x, 0))", "MAX(COALESCE(?x, 0))")
    add("b coalesce", "COUNT(COALESCE(STR(?x), ''))", "COUNT(COALESCE(STR(?x), ''))")
    add("b coalesce", "GROUP_CONCAT(COALESCE(STR(?x), ''))", f"GROUP_CONCAT(COALESCE(STR(?x), ''){GC})")
    add("b coalesce", "GROUP_CONCAT(DISTINCT COALESCE(STR(?x), ''))", f"GROUP_CONCAT(DISTINCT COALESCE(STR(?x), ''){GC})")
    add("c detect", "IF(COUNT(?x) = COUNT(*), SUM(COALESCE(?x, 0)), 1/0)", "IF(COUNT(?x) = COUNT(*), SUM(COALESCE(?x, 0)), 1/0)")
    add("c detect", "IF(COUNT(?x) = COUNT(*), SUM(?x), 1/0)", "IF(COUNT(?x) = COUNT(*), SUM(?x), 1/0)")
    add("c detect", "IF(COUNT(?x) = COUNT(*), AVG(COALESCE(?x, 0)), 1/0)", "IF(COUNT(?x) = COUNT(*), AVG(COALESCE(?x, 0)), 1/0)")
    add("c detect", "IF(COUNT(?x) = COUNT(*), MIN(?x), 1/0)", "IF(COUNT(?x) = COUNT(*), MIN(?x), 1/0)")
    add("c detect", "IF(COUNT(?x) = COUNT(*), MAX(?x), 1/0)", "IF(COUNT(?x) = COUNT(*), MAX(?x), 1/0)")
    add("c detect", "IF(COUNT(?x) = COUNT(*), GROUP_CONCAT(COALESCE(STR(?x), '')), 1/0)", f"IF(COUNT(?x) = COUNT(*), GROUP_CONCAT(COALESCE(STR(?x), ''){GC}), 1/0)")
    add("c detect", "COUNT(*) - COUNT(?x)", "COUNT(*) - COUNT(?x)")
    add("c detect", "COUNT(*) - COUNT(STR(?x))", "COUNT(*) - COUNT(STR(?x))")
    add("c detect", "COUNT(*) - COUNT(?x) (a boolean)", "(COUNT(*) = COUNT(?x))")
    add("d sub-select", "SUM(?v) over BIND(?x + 0)", "SUM(?v)", SUBSELECT_NUM)
    add("d sub-select", "GROUP_CONCAT(?v) over BIND(STR(?x))", f"GROUP_CONCAT(?v{GC})", SUBSELECT)
    add("d sub-select", "COUNT(?v) over BIND(STR(?x))", "COUNT(?v)", SUBSELECT)
    add("d sub-select", "SUM(?v) over BIND(?x + 0), FILTER(BOUND(?v))", "SUM(?v)", SUBSELECT_NUM + " FILTER(BOUND(?v))")
    return cases


GROUPS = {
    "bare SUM": ("SUM(?x)", BODY),
    "a filter BOUND, SUM": ("SUM(?x)", FILTERED),
    "b coalesce, SUM": ("SUM(COALESCE(?x, 0))", BODY),
    "bare COUNT(*)": ("COUNT(*)", BODY),
    "a filter BOUND, COUNT(*)": ("COUNT(*)", FILTERED),
    "bare AVG": ("AVG(?x)", BODY),
    "b coalesce, AVG": ("AVG(COALESCE(?x, 0))", BODY),
    "bare MAX": ("MAX(?x)", BODY),
    "c detect, SUM": ("IF(COUNT(?x) = COUNT(*), SUM(COALESCE(?x, 0)), 1/0)", BODY),
}


def groups_cases() -> dict[str, tuple[str, str]]:
    """Remedies over several groups at once, ``GROUP BY ?s``, where one group has no value at all. The cell lists every group."""
    return {f"groups | {name}": ("groups", f"SELECT (1 AS ?k) ?s ({agg} AS ?g) WHERE {{ {body} }} GROUP BY ?s") for name, (agg, body) in GROUPS.items()}


def all_cases() -> dict[str, tuple[str, str]]:
    return {**matrix_cases(), **remedy_cases(), **groups_cases()}


def graph(state: str) -> Graph:
    return Graph().parse(data=PRE + STATES[state], format="turtle")


_SHORT = {str(XSD.integer): "", str(XSD.string): "", str(XSD.decimal): "dec", str(XSD.double): "dbl", str(XSD.float): "flt"}


def render(rows: int, lexical: str | None, datatype: str | None) -> str:
    """One cell. ``none`` when the query has no row, ``unbound`` when the row has no value, else the value with a
    short datatype when it is not an integer or a string. The order of a ``GROUP_CONCAT``'s elements is the engine's, so
    its elements are sorted."""
    if rows == 0:
        return "none"
    if lexical is not None:
        lexical = re.sub(r"(_:)?\bn?[0-9a-f]{30,}(b\d+)?\b", "_:b", lexical)
    if lexical is None:
        return "unbound"
    if lexical.count(" ") and datatype in (None, str(XSD.string)):
        lexical = " ".join(sorted(lexical.split(" ")))
    if datatype == str(XSD.decimal) and lexical is not None:
        lexical = format(Decimal(lexical).normalize(), "f")
    suffix = _SHORT.get(datatype, datatype.rsplit("#", 1)[-1]) if datatype else ""
    return f"{lexical}{'^' + suffix if suffix else ''}"


def _term(g) -> str:
    if g is None:
        return "unbound"
    if isinstance(g, Literal):
        return render(1, str(g), str(g.datatype) if g.datatype else None)
    return f"<{g}>"


def cell(engine: str, state: str, text: str) -> str:
    try:
        rows = run_query(graph(state), text, engine)
        rows = list(rows)
    except Exception as error:  # an engine that refuses the query is a cell too
        return f"refused({type(error).__name__})"
    if state == "groups":
        return ";".join(sorted(f"{str(r.asdict()['s']).rsplit(':', 1)[1]}={_term(r.asdict().get('g'))}" for r in rows)) or "none"
    if not rows:
        return render(0, None, None)
    g = rows[0].g
    if isinstance(g, URIRef):
        return f"<{g}>"
    if isinstance(g, BNode):
        return "_:b"
    if isinstance(g, Literal):
        return render(len(rows), str(g), str(g.datatype) if g.datatype else None)
    return render(len(rows), None if g is None else str(g), None)


def run(engine: str) -> dict[str, str]:
    """Every cell on ``engine``. ``SAMPLE`` may return any member of its group, so a member is recorded as ``a member``."""
    cells = {name: cell(engine, state, text) for name, (state, text) in all_cases().items()}
    members = {"1", "2", "<urn:a>", "_:b"}
    return {name: "a member" if "SAMPLE" in name and value in members else value for name, value in cells.items()}


def dump(directory: Path) -> None:
    """Write ``<state>.ttl`` for each state and ``cases.tsv`` (id, state, query) for a runner of another engine."""
    directory.mkdir(parents=True, exist_ok=True)
    for state, data in STATES.items():
        (directory / f"{state.replace(' ', '_')}.ttl").write_text(PRE + data + "\n")
    lines = [f"{name}\t{state.replace(' ', '_')}\t{text}" for name, (state, text) in all_cases().items()]
    (directory / "cases.tsv").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    dump(Path(sys.argv[1]))
