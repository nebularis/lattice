# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Ask the knowledge index a question, cheaply.

Opens the store read-only and exits, with no resident process. Measured as TSD-38: a read-only open
costs 23.8 ms against 141 ms read-write, a query 0.1 to 0.9 ms, and the whole process 50 ms end to
end, so twenty questions in a prompt cost a second and a server would not earn its supervision
([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md)
decision 14).

Four questions, which are the ones agents actually ask:

``exists <text>``
    does the project already have a term for this? Searches the 2,814 declared terms of every
    ontology module. This is the query that would have prevented an agent proposing a versioning
    system although Foundation already models one, which is the error the index exists to prevent
``node <id>``
    what is this identifier, in one line, and where do I read it
``reaches <id>``
    what does it touch, by the relations its own authors declared
``sparql <query>``
    anything else

**Every question that returns nothing is logged** (ADR-A134 decision 8). The vocabulary is what
recall matches on, so an unanswered question names either a missing tag or a missing register row,
and that log is the only admissible evidence for ever adding embeddings.

Usage, from the repository root::

    mise run graph:ask -- exists versioning
    mise run graph:ask -- node ADR-A131
    mise run graph:ask -- reaches ADR-A131
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import pyoxigraph as ox

sys.path.insert(0, str(Path(__file__).resolve().parent))

import identifiers  # noqa: E402

ROOT = identifiers.ROOT
STORE_PATH = ROOT / ".build" / "knowledge" / "store"
MISS_LOG = ROOT / ".build" / "knowledge" / "misses.log"
KI = "https://www.nebularis.org/neuro-semantic/lattice/dev/knowledge#"
PREFIXES = f"""
PREFIX ki: <{KI}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
"""

EXISTS = (
    PREFIXES
    + """
SELECT DISTINCT ?needle ?where ?module ?name ?kind ?label ?pointer WHERE {
  {
    # A declared term. Answers "is there already a class or property for this".
    GRAPH ki:terms {
      ?t ki:identifier ?term ; ki:declaredAs ?kind ; ki:ownedBy ?m ; ki:pointer ?pointer .
      OPTIONAL { ?t rdfs:label ?label }
      FILTER (CONTAINS(LCASE(?term), LCASE(?needle)) ||
              CONTAINS(LCASE(COALESCE(?label, "")), LCASE(?needle)))
      BIND ("term" AS ?where)
      BIND (REPLACE(STR(?m), "^.*module/", "") AS ?module)
      BIND (REPLACE(STR(?term), "^.*[#/]", "") AS ?name)
    }
  } UNION {
    # A design shape whose own name or a declared synonym matches, then whatever is tagged with it
    # or with a concept under it. This is the branch that bridges a gerund to a noun (§9.2), and
    # the only one that can answer a question phrased in words no document uses.
    GRAPH ki:shapes {
      ?c a skos:Concept .
      { ?c skos:prefLabel ?l } UNION { ?c skos:altLabel ?l } UNION { ?c skos:definition ?l }
      FILTER (CONTAINS(LCASE(STR(?l)), LCASE(?needle)))
      ?under skos:broader* ?c .
    }
    GRAPH ki:index {
      ?n ki:tagged ?under ; ki:identifier ?name ; ki:claim ?label ; ki:pointer ?pointer .
    }
    BIND ("shape" AS ?where)
    BIND (REPLACE(STR(?c), "^.*#", "") AS ?module)
    BIND ("tagged" AS ?kind)
  } UNION {
    # What the project already has, whichever register holds it: a mechanism adopted, a
    # capability invoked, or a pattern applied. Matched on the claim and on a stated problem shape,
    # so an untagged row is still found by its own words (sketch section 9.1).
    GRAPH ki:index {
      VALUES (?k ?where) { (ki:Mechanism "mechanism") (ki:Capability "capability") (ki:Pattern "pattern") }
      ?n a ?k ; ki:identifier ?name ; ki:claim ?label ; ki:pointer ?pointer .
      OPTIONAL { ?n ki:problemShape ?shape }
      OPTIONAL { ?n ki:built ?state }
      OPTIONAL { ?n ki:entryPoint ?entry }
      OPTIONAL { ?n rdfs:label ?title }
      FILTER (CONTAINS(LCASE(COALESCE(?shape, "")), LCASE(?needle)) ||
              CONTAINS(LCASE(COALESCE(?title, "")), LCASE(?needle)) ||
              CONTAINS(LCASE(?label), LCASE(?needle)))
      BIND (COALESCE(?shape, ?entry, "") AS ?module)
      BIND (IF(?state = ki:Built, "built", IF(?state = ki:PartlyBuilt, "partial",
             IF(?state = ki:NotBuilt, "proposed", ""))) AS ?kind)
    }
  }
} ORDER BY ?where ?module ?name LIMIT 40"""
)

NODE = (
    PREFIXES
    + """
SELECT ?subject ?id ?kind ?claim ?status ?pointer WHERE {
  GRAPH ki:index {
    ?n ki:identifier ?id ; a ?k .
    OPTIONAL { ?n ki:claim ?claim }
    OPTIONAL { ?n ki:pointer ?pointer }
    OPTIONAL { ?n ki:status ?s BIND (REPLACE(STR(?s), "^.*#", "") AS ?status) }
    FILTER (?n = ?subject)
    BIND (REPLACE(STR(?k), "^.*#", "") AS ?kind)
  }
}"""
)

REACHES = (
    PREFIXES
    + """
SELECT ?subject ?direction ?id ?kind ?status ?claim WHERE {
  GRAPH ki:index {
    { ?subject ki:relatedTo|ki:dependsOn|ki:waitsOn ?other . BIND ("out" AS ?direction) }
    UNION
    { ?other ki:relatedTo|ki:dependsOn|ki:waitsOn ?subject . BIND ("in" AS ?direction) }
    ?other ki:identifier ?id ; a ?k .
    OPTIONAL { ?other ki:claim ?claim }
    OPTIONAL { ?other ki:status ?s BIND (REPLACE(STR(?s), "^.*#", "") AS ?status) }
    BIND (REPLACE(STR(?k), "^.*#", "") AS ?kind)
  }
} ORDER BY ?direction ?id"""
)


def store() -> ox.Store:
    if not STORE_PATH.exists():
        raise SystemExit(
            f"no index at {STORE_PATH.relative_to(ROOT).as_posix()}. Run: mise run build:knowledge"
        )
    return ox.Store.read_only(str(STORE_PATH))


def log_miss(question: str) -> None:
    """ADR-A134 decision 8. A question that returns nothing names a gap in the vocabulary or the
    registers, and the log of them is what decides whether embeddings are ever needed."""
    MISS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with MISS_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}\t{question}\n")


def show(rows: list, columns: tuple[str, ...]) -> None:
    widths = {c: max(len(c), *(len(str(r.get(c) or "")) for r in rows)) for c in columns}
    for c in columns:
        widths[c] = min(widths[c], 90)
    print("  ".join(c.ljust(widths[c]) for c in columns))
    print("  ".join("-" * widths[c] for c in columns))
    for row in rows:
        print("  ".join(str(row.get(c) or "")[: widths[c]].ljust(widths[c]) for c in columns))


def rows_of(solutions) -> list[dict]:
    """A query's solutions as plain dictionaries. The variable names live on the result set, not on
    each solution, so they are read once."""
    names = [str(v).lstrip("?") for v in solutions.variables]
    out = []
    for solution in solutions:
        row = {}
        for name in names:
            value = solution[name]
            row[name] = None if value is None else str(value.value)
        out.append(row)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="question", required=True)
    for name, helptext in (
        ("exists", "does a term for this already exist in any ontology module"),
        ("node", "what one identifier is, and where to read it"),
        ("reaches", "what an identifier touches, by declared relations"),
        ("sparql", "run a SPARQL query against the index"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("argument")
    arguments = parser.parse_args()

    db = store()
    question = f"{arguments.question} {arguments.argument}"

    if arguments.question == "exists":
        needle = ox.Literal(arguments.argument)
        rows = rows_of(db.query(EXISTS, substitutions={ox.Variable("needle"): needle}))
        columns = ("where", "name", "kind", "module", "label", "pointer")
    elif arguments.question in {"node", "reaches"}:
        subject = ox.NamedNode(KI + "node/" + identifiers.normalise(arguments.argument))
        query = NODE if arguments.question == "node" else REACHES
        rows = rows_of(db.query(query, substitutions={ox.Variable("subject"): subject}))
        columns = (
            ("id", "kind", "status", "claim", "pointer")
            if arguments.question == "node"
            else ("direction", "id", "kind", "status", "claim")
        )
    else:
        rows = rows_of(db.query(arguments.argument))
        columns = tuple(rows[0]) if rows else ()

    if not rows:
        log_miss(question)
        print(f"nothing found for: {question}")
        print(f"logged to {MISS_LOG.relative_to(ROOT).as_posix()}, which is what decides whether the")
        print("vocabulary needs a new concept or a register needs a new row.")
        return 0

    show(rows, columns)
    print(f"\n{len(rows)} row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
