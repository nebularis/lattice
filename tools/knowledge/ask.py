# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Ask the knowledge index a question, cheaply.

Opens the store read-only and exits, with no resident process. Measured as TSD-38: a read-only open
costs 23.8 ms against 141 ms read-write, a query 0.1 to 0.9 ms, and the whole process 50 ms end to
end, so twenty questions in a prompt cost a second and a server would not earn its supervision
([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md)
decision 14).

Six questions, which are the ones agents actually ask:

``find <words> [--kind k,...] [--phase p,...] [--audience a,...]``
    what does the project already have for this problem? Ranks every decision, register entry and
    store finding by how close its name, claim and problem shape are in meaning to the words, after
    filtering exactly on the facets given, and says so when nothing is close. The question to ask
    first, before a design, modelling, code or efficiency decision
``exists <text>``
    does the project already have a term for this? Searches the 2,814 declared terms of every
    ontology module. This is the query that would have prevented an agent proposing a versioning
    system although Foundation already models one, which is the error the index exists to prevent
``node <id>``
    what is this identifier, in one line, and where do I read it
``read <id>``
    the text itself: the current range or ranges the node's pointer resolves to, so an agent gets
    the section in one call and not a handle to go and read
``reaches <id>``
    what does it touch, by the relations its own authors declared
``sparql <query>``
    anything else
``misses [--limit n]``
    the questions answered weakly or not at all, newest first, so the gaps they name can be
    discussed at a handoff and closed with an entry, a facet value or a relation

**Every question that returns nothing, or only a weak match, is logged** (ADR-A134 decision 8 and
its addendum of 2026-10-26). An unanswered question names a missing register row, a missing tag or
a missing concept, and the log of them says which registers to fill next.

Usage, from the repository root::

    mise run graph:ask -- find tracking what state a contract is in --kind mechanism
    mise run graph:ask -- exists versioning
    mise run graph:ask -- node ADR-A131
    mise run graph:ask -- read MEC-01
    mise run graph:ask -- reaches ADR-A131
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

import pyoxigraph as ox

sys.path.insert(0, str(Path(__file__).resolve().parent))

import anchors  # noqa: E402
import embed  # noqa: E402
import extract  # noqa: E402
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
    # What the project already has, whichever register holds it: a mechanism adopted, a
    # capability invoked, or a pattern applied. Matched on the claim and on a stated problem shape,
    # so an untagged row is still found by its own words (sketch section 9.1).
    GRAPH ki:index {
      VALUES (?k ?where) { (ki:Mechanism "mechanism") (ki:Capability "capability") (ki:Pattern "pattern") (ki:Principle "principle") (ki:Standard "standard") }
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


POINTERS = (
    PREFIXES
    + """
SELECT ?subject ?pointer WHERE { GRAPH ?g { ?subject ki:pointer ?pointer } }"""
)

# Every entry with a claim, with the facets find filters on. One fixed query and a filter in Python,
# so no text from the command line is ever written into SPARQL (PRI-55).
CANDIDATES = (
    PREFIXES
    + """
SELECT ?n ?id ?kind ?status ?claim ?pointer
       (GROUP_CONCAT(DISTINCT ?ph) AS ?phases) (GROUP_CONCAT(DISTINCT ?au) AS ?audiences)
       (GROUP_CONCAT(DISTINCT ?ac) AS ?activities) (GROUP_CONCAT(DISTINCT ?qu) AS ?qualities)
       (GROUP_CONCAT(DISTINCT ?te) AS ?technologies) WHERE {
  GRAPH ki:index {
    ?n ki:identifier ?id ; ki:claim ?claim ; a ?k .
    OPTIONAL { ?n ki:pointer ?pointer }
    OPTIONAL { ?n ki:status ?s }
    OPTIONAL { ?n ki:phase ?p BIND (REPLACE(STR(?p), "^.*#", "") AS ?ph) }
    OPTIONAL { ?n ki:audience ?a BIND (REPLACE(STR(?a), "^.*#", "") AS ?au) }
    OPTIONAL { ?n ki:activity ?x BIND (REPLACE(STR(?x), "^.*#", "") AS ?ac) }
    OPTIONAL { ?n ki:quality ?y BIND (REPLACE(STR(?y), "^.*#", "") AS ?qu) }
    OPTIONAL { ?n ki:technology ?z BIND (REPLACE(STR(?z), "^.*#", "") AS ?te) }
    BIND (REPLACE(STR(?k), "^.*#", "") AS ?kind)
    BIND (REPLACE(STR(?s), "^.*#", "") AS ?status)
  }
} GROUP BY ?n ?id ?kind ?status ?claim ?pointer"""
)
KINDS = {
    "mechanism": "Mechanism", "capability": "Capability", "pattern": "Pattern",
    "principle": "Principle", "standard": "Standard", "discovery": "Discovery",
    "decision": "Decision", "pending-decision": "PendingDecision", "debt": "Debt",
}
PHASES = {"development": "Development", "authoring": "Authoring", "runtime": "Runtime"}
FACET_FLAGS = {"activity": ("Activity", "activities"), "quality": ("Quality", "qualities"), "tech": ("Technology", "technologies")}
# Each facet value with every value under it, through skos:broader, so a filter on a group finds what
# is tagged beneath it.
FACET_VALUES = (
    PREFIXES
    + """
SELECT ?scheme ?value ?under WHERE {
  GRAPH ki:facets { ?v skos:inScheme ?s . ?u skos:broader* ?v ; skos:inScheme ?s . }
  BIND (REPLACE(STR(?s), "^.*#", "") AS ?scheme)
  BIND (REPLACE(STR(?v), "^.*#", "") AS ?value)
  BIND (REPLACE(STR(?u), "^.*#", "") AS ?under)
}"""
)


# Related values, which may sit in different facets, so naming ux-design also raises entries tagged
# with a quality of interaction capability.
FACET_RELATED = (
    PREFIXES
    + """
SELECT ?value ?other ?scheme WHERE {
  GRAPH ki:facets { { ?v skos:related ?o } UNION { ?o skos:related ?v } ?o skos:inScheme ?s . }
  BIND (REPLACE(STR(?v), "^.*#", "") AS ?value)
  BIND (REPLACE(STR(?o), "^.*#", "") AS ?other)
  BIND (REPLACE(STR(?s), "^.*#", "") AS ?scheme)
}"""
)


def expand(db: ox.Store, given: dict[str, list[str]]) -> dict[str, set[str]]:
    """The values each candidate column must hold to match, from the values given per scheme.

    A value matches up and down its broader chain, and so does every value related to it, in
    whichever facet that one sits."""
    known = facet_values(db)
    related: dict[str, list[tuple[str, str]]] = {}
    for r in rows_of(db.query(FACET_RELATED)):
        related.setdefault(r["value"], []).append((r["scheme"], r["other"]))
    columns = {scheme: column for scheme, column in FACET_FLAGS.values()}
    wanted: dict[str, set[str]] = {}
    for scheme, values in given.items():
        for value in values:
            wanted.setdefault(columns[scheme], set()).update(known[scheme][value])
            for other_scheme, other in related.get(value, []):
                wanted.setdefault(columns[other_scheme], set()).update(known[other_scheme][other])
    return wanted


def facet_values(db: ox.Store) -> dict[str, dict[str, set[str]]]:
    """Per scheme, each value and the values it matches: itself, every value under it, and every
    value above it. A question about physical data modelling matches an entry tagged data modelling,
    and one about data modelling matches an entry tagged physical data modelling, but neither matches
    a sibling such as UX design through their shared group."""
    out: dict[str, dict[str, set[str]]] = {}
    for r in rows_of(db.query(FACET_VALUES)):
        scheme = out.setdefault(r["scheme"], {})
        scheme.setdefault(r["value"], {r["value"]}).add(r["under"])
        scheme.setdefault(r["under"], {r["under"]}).add(r["value"])
    return out
AUDIENCES = {"internal": "InternalUse", "published": "PublishedUse"}
# ponytail: one threshold on the meaning score alone, set from 52 questions on bge-small (answerable
# questions scored 0.69 or more in nine cases of ten, questions with no answer 0.64 to 0.68). The
# facet boost is left out of it, so naming facets never makes a weak answer look strong.
WEAK = 0.69
# What each matching facet adds to an entry's score. Measured in ADR-A134's addendum of 2026-10-26:
# 0.02 to 0.03 lifted recall on held-out questions, and 0.05 began to override meaning.
BOOST = 0.02
FALLBACK = (
    "Fall back to reading the documents as you would without the index. If the answer is there\n"
    "but no register entry holds it, that is a gap in the registers: tell the maintainer (STD-272)."
)


# The entries an answer is linked to by an edge its own author declared, in either direction, so a
# principle brings the standards that support it and a standard the decision behind it, whatever their
# words. Declared edges only, never citedWith (ADR-A134 decision 7).
LINKED = (
    PREFIXES
    + """
SELECT DISTINCT ?subject ?id ?kind ?status ?claim ?pointer ?edge WHERE {
  GRAPH ki:index {
    VALUES ?p { ki:supports ki:refines ki:decidedBy ki:evidencedBy ki:enforcedBy ki:dependsOn ki:waitsOn }
    { ?subject ?p ?o } UNION { ?o ?p ?subject }
    ?o ki:identifier ?id ; a ?k ; ki:claim ?claim .
    OPTIONAL { ?o ki:pointer ?pointer }
    OPTIONAL { ?o ki:status ?s }
    BIND (REPLACE(STR(?k), "^.*#", "") AS ?kind)
    BIND (REPLACE(STR(?s), "^.*#", "") AS ?status)
    BIND (REPLACE(STR(?p), "^.*#", "") AS ?edge)
  }
}"""
)


def linked(db: ox.Store, top: list[dict], shown: set[str], limit: int = 8) -> list[dict]:
    """The entries the top answers are linked to by declared edges, not already shown."""
    out: dict[str, dict] = {}
    for answer in top:
        for r in rows_of(db.query(LINKED, substitutions={ox.Variable("subject"): ox.NamedNode(answer["n"])})):
            if r["id"] not in shown and r["id"] not in out:
                r["via"] = f"{r['edge']} {answer['id']}"
                out[r["id"]] = r
    return list(out.values())[:limit]


def find(
    db: ox.Store, words: str, kinds: set[str], phases: set[str], audiences: set[str], limit: int,
    facets: dict[str, set[str]] | None = None,
) -> int:
    """Rank entries by meaning against the words, filtering exactly on kind, phase and audience and
    raising entries whose activity, quality or technology matches.

    Kind, phase and audience are closed facts an agent states on purpose, so they filter. Activity,
    quality and technology are judgements two taggers can disagree on, so a match adds BOOST to the
    score for each facet and a mismatch hides nothing. ``facets`` maps a candidate column, such as
    ``technologies``, to the values that match, broader and narrower values already included."""
    facets = facets or {}
    rows = [
        r for r in rows_of(db.query(CANDIDATES))
        if (not kinds or r["kind"] in kinds)
        and (not phases or phases & set((r["phases"] or "").split()))
        and (not audiences or audiences & set((r["audiences"] or "").split()))
    ]
    try:
        nodes, vectors = embed.load(STORE_PATH.parent)
        question = embed.Model().question(words)
    except embed.Unavailable as error:
        print(f"find cannot rank here: {error}")
        print("Try exists with a word the answer would use.")
        print(FALLBACK)
        return 0
    index = {node: i for i, node in enumerate(nodes)}
    for r in rows:
        r["meaning"] = float(vectors[index[r["n"]]] @ question) if r["n"] in index else -1.0
        r["facets"] = sum(bool(wanted & set((r[c] or "").split())) for c, wanted in facets.items())
        r["score"] = r["meaning"] + BOOST * r["facets"]
    best = max((r["meaning"] for r in rows), default=-1.0)
    rows = sorted(rows, key=lambda r: -r["score"])[:limit]
    if best < WEAK:
        log_miss(f"find {words}")
    if not rows:
        print(f"no entry has the facets asked for: {words}")
        print("Widen or drop a filter, or try other words.")
        print(FALLBACK)
        return 0
    for r in rows:
        r["score"] = f"{r['score']:.2f}" + ("+" * r["facets"])
    show(rows, ("score", "id", "kind", "status", "claim", "pointer"))
    also = linked(db, rows[:3], {r["id"] for r in rows})
    if also:
        print("\nlinked to the top answers by a declared edge:")
        show(also, ("via", "id", "kind", "status", "claim", "pointer"))
    if facets:
        print("\n+ marks each facet the entry matches, which raised it by", BOOST)
    if best < WEAK:
        print(f"\nweak match: no entry scored {WEAK} or more, so the index may not hold the answer.")
        print("Try other words, or a different or wider filter.")
        print(FALLBACK)
    return 0


def read_ranges(db: ox.Store, identifier: str) -> list[tuple[str, str]]:
    """The ``(path:start-end, text)`` of every range a node's pointer resolves to, as of the build.

    A bare path is the whole file. The ranges were resolved from anchors when the index was built,
    so the text read here is the text at those lines now, and a document edited since the build
    is answered by rebuilding."""
    subject = ox.NamedNode(KI + "node/" + identifiers.normalise(identifier))
    found: list[tuple[str, str]] = []
    for row in db.query(POINTERS, substitutions={ox.Variable("subject"): subject}):
        for part in str(row["pointer"].value).split(","):
            path, start, end = anchors.parse_range(part)
            lines = (ROOT / path).read_text(encoding="utf-8", errors="replace").splitlines()
            last = len(lines) if end is None else min(end, len(lines))
            found.append((f"{path}:{start}-{last}", "\n".join(lines[start - 1 : last])))
    return found


def stale() -> bool:
    """Whether any tracked file is newer than the build the store was made from.

    A pointer resolves an anchor to a line range at build time, so an edit to a document after the
    build would leave every pointer into it on the wrong lines, silently. Checking every tracked
    file, rather than the ones the index read, also catches a new document the index should hold.
    """
    # ponytail: stats all ~2,200 tracked files, about 55 ms, which doubles a 50 ms query. Record
    # the build's own source list with their mtimes if query latency comes to matter.
    if not STORE_PATH.exists() or not extract.STAMP_PATH.exists():
        return True
    built_from = float(extract.STAMP_PATH.read_text(encoding="utf-8").strip())
    names = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, text=True, check=True
    ).stdout.split("\0")
    for name in names:
        try:
            if name and os.stat(ROOT / name).st_mtime > built_from:
                return True
        except FileNotFoundError:
            continue
    return False


def store() -> ox.Store:
    """The index, rebuilt first if any tracked file changed since it was built.

    So an agent that edits a document and asks again gets the document as it now is, and never the
    lines it held before. The rebuild costs about two seconds and happens once per change.
    """
    # ponytail: two agents finding the store stale at once both rebuild into the same directory.
    # Build into a temporary directory and rename it into place if that race is ever seen.
    if stale():
        print("knowledge index is older than the files it reads, so rebuilding it", file=sys.stderr)
        extract.build(STORE_PATH)
    return ox.Store.read_only(str(STORE_PATH))


def log_miss(question: str) -> None:
    """ADR-A134 decision 8. A question that returns nothing names a gap in the vocabulary or the
    registers, and the log of them is what decides whether embeddings are ever needed."""
    MISS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with MISS_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}\t{question}\n")


def misses(limit: int) -> int:
    """The distinct questions in the miss log, newest first, with how often and when last asked."""
    if not MISS_LOG.exists():
        print("no misses recorded")
        return 0
    seen: dict[str, list] = {}
    for line in MISS_LOG.read_text(encoding="utf-8").splitlines():
        when, _, question = line.partition("\t")
        entry = seen.setdefault(question, [0, when])
        entry[0] += 1
        entry[1] = when
    rows = sorted(({"last": w[:10], "times": str(n), "question": q} for q, (n, w) in seen.items()),
                  key=lambda r: r["last"], reverse=True)[:limit]
    show(rows, ("last", "times", "question"))
    print(f"\n{len(seen)} distinct question(s) in {MISS_LOG.relative_to(ROOT).as_posix()}")
    return 0


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
        ("read", "the text of the section or definition an identifier's pointer names"),
        ("reaches", "what an identifier touches, by declared relations"),
        ("sparql", "run a SPARQL query against the index"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("argument")
    p = sub.add_parser("find", help="entries ranked by how close their meaning is to your words")
    p.add_argument("words", nargs="+")
    p.add_argument("--kind", default="", help=f"comma-separated, of {', '.join(KINDS)}")
    p.add_argument("--phase", default="", help=f"comma-separated, of {', '.join(PHASES)}")
    p.add_argument("--audience", default="", help=f"comma-separated, of {', '.join(AUDIENCES)}")
    for flag, (scheme, _) in FACET_FLAGS.items():
        p.add_argument(f"--{flag}", default="", help=f"comma-separated values of the {scheme} facet, which raise matching entries and hide none. See docs/developer/facets.md")
    p.add_argument("--limit", type=int, default=8)
    m = sub.add_parser("misses", help="the questions answered weakly or not at all, newest first")
    m.add_argument("--limit", type=int, default=20)
    arguments = parser.parse_args()

    if arguments.question == "misses":
        return misses(arguments.limit)

    if arguments.question == "find":
        chosen = []
        for flag, values in (("kind", KINDS), ("phase", PHASES), ("audience", AUDIENCES)):
            given = [v.strip() for v in getattr(arguments, flag).split(",") if v.strip()]
            unknown = [v for v in given if v not in values]
            if unknown:
                parser.error(f"--{flag} {', '.join(unknown)} is not one of {', '.join(values)}")
            chosen.append({values[v] for v in given})
        db = store()
        known = facet_values(db)
        given = {}
        for flag, (scheme, _) in FACET_FLAGS.items():
            given[scheme] = [v.strip() for v in getattr(arguments, flag).split(",") if v.strip()]
            unknown = [v for v in given[scheme] if v not in known.get(scheme, {})]
            if unknown:
                parser.error(f"--{flag} {', '.join(unknown)} is not a value of the {scheme} facet. See docs/developer/facets.md")
        return find(db, " ".join(arguments.words), *chosen, arguments.limit, expand(db, given))

    db = store()
    question = f"{arguments.question} {arguments.argument}"

    if arguments.question == "read":
        pieces = read_ranges(db, arguments.argument)
        if not pieces:
            log_miss(question)
            print(f"nothing to read for: {arguments.argument}")
            return 0
        for where, text in pieces:
            print(f"== {where}")
            print(text)
        return 0

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
