# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Ask the knowledge index a question, cheaply.

Opens the store read-only and exits, with no resident process. Measured as TSD-38: a read-only open
costs 23.8 ms against 141 ms read-write, a query 0.1 to 0.9 ms, and the whole process 50 ms end to
end, so twenty questions in a prompt cost a second and a server would not earn its supervision
([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md)
decision 14).

The questions agents actually ask:

``find <words> [--kind k,...] [--phase p,...] [--audience a,...]``
    what does the project already have for this problem? Ranks every decision, register entry,
    store finding and plan question by how close its text is in meaning to the words, and the
    declared ontology terms only when ``--kind term`` asks for them, after filtering exactly on the facets given, and says so when nothing is close. Each row
    is flagged with what its own columns do not show, and the line under it holds the whole claim
    and names each flag's reason. The question to ask first, before a design, modelling, code or
    efficiency decision
``exists <text>``
    does the project already have a term for this? Searches the 2,814 declared terms of every
    ontology module. This is the query that would have prevented an agent proposing a versioning
    system although Foundation already models one, which is the error the index exists to prevent
``node <id>``
    what is this identifier, in one line, and where do I read it
``read <id>``
    the entry's fields, every entry linked to it by a declared edge, then the text itself: the
    current range or ranges the node's pointer resolves to, so an agent gets the section in one
    call and not a handle to go and read
``reaches <id>``
    what does it touch, by the relations its own authors declared
``sparql <query>``
    anything else
``misses [--limit n] [--near]``
    the questions answered weakly or not at all, newest first, and the gaps recorded, so the gaps
    they name can be discussed at a handoff and closed with an entry, a facet value or a relation.
    ``--near`` adds the questions answered from WEAK to under NEAR
``gap <what reading found> [id] [path:line]``
    record, at the moment of finding it, what the index did not say, with the entry it qualifies
``close <id> [...]``
    close the gaps on entries whose signpost is now written, and remove their log lines

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
import re
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
# Every find and read, with its best score and what it showed, and every gap an agent records
# (ADR-A134 decision 32). The evidence for which signpost would have carried what was missed.
ASK_LOG = ROOT / ".build" / "knowledge" / "asks.log"
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
SELECT ?subject ?p ?pointer WHERE { GRAPH ?g { ?subject ?p ?pointer . VALUES ?p { ki:row ki:pointer } } }"""
)

# What read prints before the text: the entry's own fields that find does not show, then each entry
# it is linked to by a declared edge, in either direction (ADR-A134 decision 28).
FIELDS = (
    PREFIXES
    + """
SELECT ?subject ?field ?value WHERE { GRAPH ki:index {
  VALUES (?p ?field) { (ki:problemShape "Problem shape") (ki:doesNotCover "Does not cover")
                       (ki:uncheckedBecause "Unchecked because") (ki:cost "Cost") }
  ?subject ?p ?value
} }"""
)

# Every entry with a claim, with the facets find filters on. One fixed query and a filter in Python,
# so no text from the command line is ever written into SPARQL (PRI-55).
CANDIDATES = (
    PREFIXES
    + """
SELECT ?n ?id ?kind ?status ?claim ?pointer
       (GROUP_CONCAT(DISTINCT ?ph) AS ?phases) (GROUP_CONCAT(DISTINCT ?au) AS ?audiences)
       (GROUP_CONCAT(DISTINCT ?ac) AS ?activities) (GROUP_CONCAT(DISTINCT ?qu) AS ?qualities)
       (GROUP_CONCAT(DISTINCT ?te) AS ?technologies) (SAMPLE(?dn) AS ?uncovered)
       (GROUP_CONCAT(DISTINCT ?debt) AS ?debts) (GROUP_CONCAT(DISTINCT ?idea) AS ?ideas) (SAMPLE(?sp) AS ?successor) WHERE {
  GRAPH ki:index {
    ?n ki:identifier ?id ; ki:claim ?claim ; a ?k .
    OPTIONAL { ?n ki:pointer ?pointer }
    OPTIONAL { ?n ki:status ?s }
    OPTIONAL { ?n ki:doesNotCover ?dn }
    OPTIONAL { ?d ki:bearsOn ?n ; a ki:Debt ; ki:status ki:Open ; ki:identifier ?debt }
    OPTIONAL { ?b ki:bearsOn ?n ; a ki:Backlog ; ki:status ki:Open ; ki:identifier ?idea }
    OPTIONAL { ?n ki:supersededBy ?successorNode . ?successorNode ki:identifier ?sp }
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
# The sections of a decision, which find scores beside the decision's own text (ADR-A134 decision 29), with the
# addendum sections that reverse or narrow each (ADR-A134 decision 29).
SECTIONS = (
    PREFIXES
    + """
SELECT ?s ?n ?pointer ?text (SAMPLE(?rp) AS ?reversed) (SAMPLE(?np) AS ?narrowed) WHERE { GRAPH ki:index {
  ?s ki:sectionOf ?n ; ki:pointer ?pointer ; ki:claim ?text
  OPTIONAL { ?s ki:supersededBy ?r . ?r ki:pointer ?rp }
  OPTIONAL { ?s ki:narrowedBy ?w . ?w ki:pointer ?np }
} } GROUP BY ?s ?n ?pointer ?text"""
)
# Every declared term with the claim the term summary derived for it (ADR-A134 decision 31). A term
# is no register entry and carries no phase, audience or facet, so a filter on any of them hides it.
TERM_CANDIDATES = (
    PREFIXES
    + """
SELECT ?n ?iri ?claim ?pointer ?module WHERE { GRAPH ki:terms {
  ?n ki:identifier ?iri ; ki:claim ?claim ; ki:pointer ?pointer ; ki:ownedBy ?m .
  BIND (REPLACE(STR(?m), "^.*module/", "") AS ?module)
} }"""
)
KINDS = {
    "mechanism": "Mechanism", "capability": "Capability", "pattern": "Pattern",
    "principle": "Principle", "standard": "Standard", "discovery": "Discovery",
    "decision": "Decision", "pending-decision": "PendingDecision", "debt": "Debt", "backlog": "Backlog",
    "question": "Question", "term": "Term",
}
PHASES = {
    "development": "Development", "authoring": "Authoring", "runtime": "Runtime",
    "testing": "Testing", "benchmarking": "Benchmarking", "production": "Production",
}
# Each phase with every phase under it, through skos:broader in the T-Box.
PHASE_CHAIN = (
    PREFIXES
    + """
SELECT ?value ?under WHERE {
  GRAPH ki:tbox { ?v a ki:Phase . ?u skos:broader* ?v ; a ki:Phase . }
  BIND (REPLACE(STR(?v), "^.*#", "") AS ?value)
  BIND (REPLACE(STR(?u), "^.*#", "") AS ?under)
}"""
)
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


def phase_matches(db: ox.Store, given: set[str]) -> set[str]:
    """The phases an entry may carry to match the phases given: each one, every phase under it and
    every phase above it, as a facet value matches. Runtime finds testing, and production finds
    runtime, but testing never finds production."""
    out = set(given)
    for r in rows_of(db.query(PHASE_CHAIN)):
        if r["value"] in given:
            out.add(r["under"])
        if r["under"] in given:
            out.add(r["value"])
    return out
# ponytail: one threshold on the meaning score alone, set from 52 questions on bge-small (answerable
# questions scored 0.69 or more in nine cases of ten, questions with no answer 0.64 to 0.68). The
# facet boost is left out of it, so naming facets never makes a weak answer look strong.
WEAK = 0.69
# What each matching facet adds to an entry's score. Measured in ADR-A134's addendum of 2026-10-26:
# 0.02 to 0.03 lifted recall on held-out questions, and 0.05 began to override meaning.
BOOST = 0.02
# What a superseded decision loses, so its successor ranks above it at equal meaning while the
# superseded one is still shown, marked, for a question about the history (ADR-A134 decision 29).
# Measured 2026-10-28 on six questions about the two superseded decisions: 0.03 dropped the
# superseded one out of the top ten in two, which the decision keeps for history, and 0.01 kept it
# in every top ten. The ~ mark and the successor under the row protect the reader at any rank.
SUPERSEDED = 0.01
# Questions answered at or above WEAK and below this are near answers, where a confident and
# incomplete answer lives, and misses --near lists them (ADR-A134 decision 32).
NEAR = 0.74
# find prints each answer's whole claim under its row when it shows this many rows or fewer.
FULL_CLAIMS = 8
# A pointer to more lines than this that names a whole file is a pointer defect, and read refuses it.
WHOLE_FILE = 200
FALLBACK = (
    "If the question was what a class or property means, or whether one already exists, ask again\n"
    "with --kind term, since declared terms are searched only when that kind is named.\n"
    "Fall back to reading the documents as you would without the index. If the answer is there\n"
    "but no register entry holds it, that is a gap in the registers: tell the maintainer (STD-272).\n"
    f"The index holds the decisions, the registers, the declared terms and the questions plans and\n"
    f"sketches raise, never the rest of a plan or a status record, so what a unit is doing now and what\n"
    f"it does next is in {identifiers.DEVELOPER}/status/<unit>.md, and its scope and slices are in\n"
    f"{identifiers.DEVELOPER}/plans/<unit>.md."
)


# The entries an answer is linked to by an edge its own author declared, in either direction, so a
# principle brings the standards that support it and a standard the decision behind it, whatever their
# words. Declared edges only, never citedWith (ADR-A134 decision 7).
LINKED = (
    PREFIXES
    + """
SELECT DISTINCT ?subject ?id ?kind ?status ?claim ?pointer ?edge ?direction WHERE {
  GRAPH ki:index {
    VALUES ?p { ki:supports ki:refines ki:decidedBy ki:evidencedBy ki:enforcedBy ki:dependsOn ki:waitsOn
                ki:distinguishedFrom ki:bearsOn ki:answers ki:supersededBy }
    { ?subject ?p ?o BIND ("out" AS ?direction) } UNION { ?o ?p ?subject BIND ("in" AS ?direction) }
    ?o ki:identifier ?id ; a ?k ; ki:claim ?claim .
    OPTIONAL { ?o ki:pointer ?pointer }
    OPTIONAL { ?o ki:status ?s }
    BIND (REPLACE(STR(?k), "^.*#", "") AS ?kind)
    BIND (REPLACE(STR(?s), "^.*#", "") AS ?status)
    BIND (REPLACE(STR(?p), "^.*#", "") AS ?edge)
  }
}"""
)


# The words an edge is shown with, where its property name would read wrongly.
EDGE_WORDS = {
    "distinguishedFrom": "distinguished from", "bearsOn": "bears on", "supersededBy": "superseded by",
    "decidedBy": "decided by", "evidencedBy": "evidenced by", "enforcedBy": "enforced by",
    "dependsOn": "depends on", "waitsOn": "waits on",
}


def linked(db: ox.Store, top: list[dict], shown: set[str], limit: int = 8) -> list[dict]:
    """The entries the top answers are linked to by declared edges, not already shown."""
    out: dict[str, dict] = {}
    for answer in top:
        for r in rows_of(db.query(LINKED, substitutions={ox.Variable("subject"): ox.NamedNode(answer["n"])})):
            if r["id"] not in shown and r["id"] not in out:
                r["via"] = f"{EDGE_WORDS.get(r['edge'], r['edge'])} {answer['id']}"
                out[r["id"]] = r
    return list(out.values())[:limit]


def candidates(db: ox.Store, kinds: set[str], phases: set[str], audiences: set[str]) -> list[dict]:
    """Every entry the filters admit, and the declared terms only when ``--kind`` names ``term``.

    Ranked among the entries, 2,774 terms crowded the entries out of questions about a design, and
    no bias kept both kinds of question answered, so a term is asked for or not shown (ADR-A134
    decision 31). A term states no phase or audience, so a filter on either hides it."""
    rows = [
        r for r in rows_of(db.query(CANDIDATES))
        if (not kinds or r["kind"] in kinds)
        and (not phases or phases & set((r["phases"] or "").split()))
        and (not audiences or audiences & set((r["audiences"] or "").split()))
    ]
    if "Term" in kinds and not phases and not audiences:
        for r in rows_of(db.query(TERM_CANDIDATES)):
            local = re.split(r"[#/]", r["iri"])[-1]
            rows.append({"n": r["n"], "id": local, "kind": "Term", "module": r["module"], "claim": r["claim"], "pointer": r["pointer"]})
    return rows


def without(kinds: set[str], excluded: set[str]) -> set[str]:
    """The kinds left once ``excluded`` are taken out: of those named, or of every entry kind when
    none is. Terms stay out unless named, so excluding nothing leaves the default (decision 30)."""
    if not excluded:
        return kinds
    return (kinds or set(KINDS.values()) - {"Term"}) - excluded


def flags(r: dict) -> str:
    """What the row's own columns do not show, one mark each (ADR-A134 decisions 28 and 29)."""
    marks = ""
    if r.get("uncovered"):
        marks += "!"
    if r.get("reversed") or r.get("successor") or r.get("status") == "Superseded":
        marks += "~"
    if r.get("debts"):
        marks += "TD"
    if r.get("ideas"):
        marks += "BL"
    if r.get("status") == "Proposed":
        marks += "?"
    return marks


def under(r: dict) -> str:
    """The line find prints under a row: the whole claim, then each signpost the flags mark."""
    text = [r["claim"].rstrip()]
    if r.get("section") and not r["section"].startswith(r["claim"].rstrip("…")):
        cut = r["section"] if len(r["section"]) <= 200 else r["section"][:199].rstrip() + "…"
        text.append(f"The section that answered: {cut}")
    if r.get("uncovered"):
        text.append(f"Does not cover: {r['uncovered'].rstrip('.')}.")
    if r.get("successor"):
        text.append(f"Superseded by {r['successor']}.")
    if r.get("reversed"):
        text.append(f"Reversed by {r['reversed']}.")
    if r.get("narrowed"):
        text.append(f"Narrowed by {r['narrowed']}.")
    if r.get("debts"):
        text.append(f"Open debt: {', '.join(sorted(r['debts'].split()))}.")
    if r.get("ideas"):
        text.append(f"On the backlog, not built: {', '.join(sorted(r['ideas'].split()))}.")
    return " ".join(text)


def find(
    db: ox.Store, words: str, kinds: set[str], phases: set[str], audiences: set[str], limit: int,
    facets: dict[str, set[str]] | None = None,
) -> int:
    """Rank entries by meaning against the words, filtering exactly on kind, phase and audience and
    raising entries whose activity, quality or technology matches.

    Kind, phase and audience are closed facts an agent states on purpose, so they filter. Activity,
    quality and technology are judgements two taggers can disagree on, so a match adds BOOST to the
    score for each facet and a mismatch hides nothing. ``facets`` maps a candidate column, such as
    ``technologies``, to the values that match, broader and narrower values already included.

    A superseded decision loses SUPERSEDED and is kept, marked ~, with its successor named under it.
    So is a section an addendum reversed, which keeps its rank and names the addendum (decision 29)."""
    try:
        rows, best = rank(db, words, kinds, phases, audiences, facets)
    except embed.Unavailable as error:
        print(f"find cannot rank here: {error}")
        print("Try exists with a word the answer would use.")
        print(FALLBACK)
        return 0
    rows = rows[:limit]
    log_ask("find", words, best, [r["id"] for r in rows])
    if best < WEAK:
        log_miss(f"find {words}")
    if not rows:
        print(f"no entry has the facets asked for: {words}")
        print("Widen or drop a filter, or try other words.")
        print(FALLBACK)
        return 0
    for r in rows:
        r["score"] = f"{r['score']:.2f}" + ("+" * r["facets"])
        r["flags"] = flags(r)
    _show_found(db, rows, facets, best)
    return 0


def rank(
    db: ox.Store, words: str, kinds: set[str], phases: set[str], audiences: set[str],
    facets: dict[str, set[str]] | None = None, model=None,
) -> tuple[list[dict], float]:
    """Every candidate scored against the words, best first, and the best meaning score. Raises
    embed.Unavailable where the vectors or the model are missing."""
    facets = facets or {}
    rows = candidates(db, kinds, phases, audiences)
    nodes, vectors = embed.load(STORE_PATH.parent)
    question = (model or embed.Model()).question(words)
    index = {node: i for i, node in enumerate(nodes)}
    sections: dict[str, list[dict]] = {}
    for section in rows_of(db.query(SECTIONS)):
        sections.setdefault(section["n"], []).append(section)
    # An identifier written in the question names one entry outright, which no amount of meaning can
    # beat and which the embedding scores poorly, since a name carries no sense of its own. Ranking it
    # first stops `find PDD-08` reporting that the index may not hold PDD-08.
    named = {identifiers.normalise(word) for word in words.split()}
    for r in rows:
        r["meaning"] = float(vectors[index[r["n"]]] @ question) if r["n"] in index else -1.0
        if r["kind"] != "Term" and identifiers.normalise(r["id"]) in named:
            r["meaning"] = 1.0
        # An entry is as close as its closest section and then points at it. After the name, so that
        # a named entry keeps its whole-file pointer.
        for section in sections.get(r["n"], []):
            if section["s"] in index and (m := float(vectors[index[section["s"]]] @ question)) > r["meaning"]:
                r["meaning"], r["pointer"] = m, section["pointer"]
                r["reversed"], r["narrowed"] = section["reversed"], section["narrowed"]
                r["section"] = section["text"]
        r["facets"] = sum(bool(wanted & set((r.get(c) or "").split())) for c, wanted in facets.items())
        r["score"] = r["meaning"] + BOOST * r["facets"]
        if r["kind"] == "Decision" and (r.get("successor") or r.get("status") == "Superseded"):
            r["score"] -= SUPERSEDED
    best = max((r["meaning"] for r in rows), default=-1.0)
    return sorted(rows, key=lambda r: -r["score"]), best


def _show_found(db: ox.Store, rows: list[dict], facets: dict, best: float) -> None:
    """The ranked rows, the entries linked to the top three, a legend for the flags shown, and
    the fallback advice when the best meaning was weak."""
    # A term has a module and no lifecycle status, so its module gets a column of its own when terms
    # are shown, and status is left out when nothing but terms is.
    terms = [r["kind"] == "Term" for r in rows]
    columns = ("score", "id", "kind") + (("module",) if any(terms) else ()) + (() if all(terms) else ("status",)) + ("flags", "claim", "pointer")
    show(rows, columns, under if len(rows) <= FULL_CLAIMS else None)
    also = linked(db, rows[:3], {r["id"] for r in rows})
    if also:
        print("\nlinked to the top answers by a declared edge:")
        show(also, ("via", "id", "kind", "status", "claim", "pointer"))
    marks = {m for r in rows for m in ("!", "~", "TD", "BL", "?") if m in r["flags"]}
    if marks:
        print("\n" + ". ".join(FLAG_WORDS[m] for m in ("!", "~", "TD", "BL", "?") if m in marks) + ". The line under the row says which.")
    if facets:
        print("\n+ marks each facet the entry matches, which raised it by", BOOST)
    if best < WEAK:
        print(f"\nweak match: no entry scored {WEAK} or more, so the index may not hold the answer.")
        print("Try other words, or a different or wider filter.")
        print(FALLBACK)


FLAG_WORDS = {
    "!": "! the entry states a case it does not cover",
    "~": "~ the text returned was superseded or reversed",
    "TD": "TD an open debt bears on the entry",
    "BL": "BL an idea on the backlog, not built, bears on the entry",
    "?": "? the entry is Proposed, not ratified",
}


def read_ranges(db: ox.Store, identifier: str) -> list[tuple[str, str]]:
    """The ``(path:start-end, text)`` of every range a node's pointer resolves to, as of the build.

    A bare path is the whole file. The ranges were resolved from anchors when the index was built,
    so the text read here is the text at those lines now, and a document edited since the build
    is answered by rebuilding."""
    subject = ox.NamedNode(KI + "node/" + identifiers.normalise(identifier))
    found: list[tuple[str, str]] = []
    # The defining register row first, then what the row points at, labelled as such.
    rows = sorted(db.query(POINTERS, substitutions={ox.Variable("subject"): subject}), key=lambda r: r["p"].value != KI + "row")
    for row in rows:
        for part in str(row["pointer"].value).split(","):
            path, start, end = anchors.parse_range(part)
            lines = (ROOT / path).read_text(encoding="utf-8", errors="replace").splitlines()
            last = len(lines) if end is None else min(end, len(lines))
            where = f"{path}:{start}-{last}"
            if row["p"].value == KI + "row":
                where = f"row {where}"
            elif any(w == f"row {where}" for w, _ in found):
                continue
            else:
                where = f"pointed-at {where}" if found else where
            found.append((where, "\n".join(lines[start - 1 : last])))
    return found


def whole_file(where: str) -> int | None:
    """The length of the file a range covers whole, when it is longer than WHOLE_FILE, else None.

    ``where`` is a label from read_ranges, so the row and pointed-at prefixes are dropped first."""
    path, start, end = anchors.parse_range(where.removeprefix("row ").removeprefix("pointed-at "))
    total = len((ROOT / path).read_text(encoding="utf-8", errors="replace").splitlines())
    return total if start == 1 and end in (None, total) and total > WHOLE_FILE else None


def read(db: ox.Store, identifier: str) -> int:
    """An entry's fields, its neighbours by declared edge, then the text its pointer names.

    A pointer naming the whole of a long file is refused, since it hands the reader a register or a
    document and not the entry, and the fields above stand in for it (ADR-A134 decision 28)."""
    subject = ox.NamedNode(KI + "node/" + identifiers.normalise(identifier))
    pieces = read_ranges(db, identifier)
    log_ask("read", identifier, None, [identifier] if pieces else [])
    if not pieces:
        log_miss(f"read {identifier}")
        print(f"nothing to read for: {identifier}")
        return 0
    head = rows_of(db.query(NODE, substitutions={ox.Variable("subject"): subject}))
    if head:
        h = head[0]
        print(f"{h['id']}  {h['kind']}  {h['status'] or ''}".rstrip())
        print(f"Claim: {h['claim'] or ''}")
    for r in rows_of(db.query(FIELDS, substitutions={ox.Variable("subject"): subject})):
        print(f"{r['field']}: {r['value']}")
    neighbours = rows_of(db.query(LINKED, substitutions={ox.Variable("subject"): subject}))
    if neighbours:
        print("Linked:")
        for r in sorted(neighbours, key=lambda r: (r["direction"], r["edge"], r["id"])):
            edge = EDGE_WORDS.get(r["edge"], r["edge"])
            arrow = f"{edge} {r['id']}" if r["direction"] == "out" else f"{r['id']} {edge} this"
            print(f"  {arrow} ({r['kind']}{', ' + r['status'] if r['status'] else ''}): {r['claim']}")
    for where, text in pieces:
        if (total := whole_file(where)) is not None:
            print(f"== {where}")
            print(f"Not printed: the pointer names the whole of a {total}-line file, which is a pointer defect. "
                  f"The fields above are the entry. Point it at a section, path#slug, instead.")
            continue
        print(f"== {where}")
        print(text)
    return 0


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


def shown(path: Path) -> str:
    """A path as the reader would type it, from the root where it lies under it."""
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


def log_ask(verb: str, text: str, best: float | None, ids: list[str], asked: str | None = None) -> None:
    """One line per find, read or gap: when, which, the best meaning score, what it showed, the text,
    and for a gap the question asked just before it."""
    ASK_LOG.parent.mkdir(parents=True, exist_ok=True)
    score = "" if best is None else f"{best:.2f}"
    tail = "" if asked is None else f"\t{asked}"
    with ASK_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}\t{verb}\t{score}\t{','.join(ids)}\t{text}{tail}\n")


def asks() -> list[dict]:
    if not ASK_LOG.exists():
        return []
    rows = []
    for line in ASK_LOG.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 5:
            # A gap carries a sixth field, the question asked just before it was found.
            rows.append(dict(zip(("when", "verb", "best", "ids", "text", "asked"), parts), line=line))
    return rows


def _keep(path: Path, drop) -> int:
    """Rewrite a log without the lines ``drop`` says are closed, and say how many went."""
    if not path.exists():
        return 0
    lines = path.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if not drop(line)]
    path.write_text("".join(line + "\n" for line in kept), encoding="utf-8", newline="\n")
    return len(lines) - len(kept)


def close(ids: list[str]) -> int:
    """Close the gaps recorded against these entries, once their signpost is written, and remove
    every log line related to each: the gap, and the miss and near answers of the question asked
    just before it was found (ADR-A134 decision 32)."""
    wanted = {identifiers.normalise(i) for i in ids}
    gaps = [r for r in asks() if r["verb"] == "gap" and wanted & {identifiers.normalise(i) for i in r["ids"].split(",") if i}]
    questions = {r.get("asked") for r in gaps if r.get("asked")}
    lines = {r["line"] for r in gaps}
    removed = _keep(ASK_LOG, lambda line: line in lines or (line.split("\t")[1:2] == ["find"] and line.split("\t", 4)[-1] in questions))
    removed += _keep(MISS_LOG, lambda line: line.partition("\t")[2] in {f"find {q}" for q in questions})
    print(f"closed {len(gaps)} gap(s) on {', '.join(ids)}, and removed {removed} related log line(s)")
    return 0


def recheck(db: ox.Store) -> int:
    """Ask each logged weak or near question again, and remove the lines of those the index now
    answers at NEAR or above, since an entry or a signpost written since has closed them."""
    logged = asks()
    questions = {line.partition("\t")[2].removeprefix("find ") for line in
                 (MISS_LOG.read_text(encoding="utf-8").splitlines() if MISS_LOG.exists() else [])
                 if line.partition("\t")[2].startswith("find ")}
    questions |= {r["text"] for r in logged if r["verb"] == "find" and r["best"] and float(r["best"]) < NEAR}
    if not questions:
        return 0
    try:
        model = embed.Model()
        answered = {q for q in questions if rank(db, q, set(), set(), set(), model=model)[1] >= NEAR}
    except embed.Unavailable:
        return 0
    removed = _keep(MISS_LOG, lambda line: line.partition("\t")[2] in {f"find {q}" for q in answered})
    removed += _keep(ASK_LOG, lambda line: line.split("\t")[1:2] == ["find"] and line.split("\t", 4)[-1] in answered)
    if answered:
        print(f"{len(answered)} question(s) the index now answers at {NEAR} or above were closed, and {removed} log line(s) removed\n")
    return len(answered)


def gap(text: str, extras: list[str]) -> int:
    """Record what was found by reading and that the index did not say, with the entry it qualifies
    and the line it was read from, at the moment it is found (ADR-A134 decision 32)."""
    where = [e for e in extras if anchors.LINE_NUMBER_RE.search(e) or "/" in e]
    ids = [e for e in extras if e not in where]
    asked = next((r["text"] for r in reversed(asks()) if r["verb"] == "find"), "")
    log_ask("gap", text + (f" @ {', '.join(where)}" if where else ""), None, ids, asked)
    print(f"gap recorded in {shown(ASK_LOG)}. Name it at the handoff with the column or edge that would have carried it")
    return 0


def _distinct(entries: list[tuple[str, str]]) -> list[dict]:
    seen: dict[str, list] = {}
    for when, text in entries:
        entry = seen.setdefault(text, [0, when])
        entry[0] += 1
        entry[1] = when
    return sorted(({"last": w[:10], "times": str(n), "question": q} for q, (n, w) in seen.items()),
                  key=lambda r: r["last"], reverse=True)


def misses(limit: int, near: bool = False, db: ox.Store | None = None) -> int:
    """The distinct questions answered weakly or not at all, newest first, then the gaps recorded,
    and with ``near`` the questions answered between WEAK and NEAR. Given the store, each is asked
    again first and those now answered are removed (``recheck``)."""
    if db is not None:
        recheck(db)
    logged = asks()
    if MISS_LOG.exists():
        lines = [line.partition("\t") for line in MISS_LOG.read_text(encoding="utf-8").splitlines()]
        rows = _distinct([(when, question) for when, _, question in lines])
        show(rows[:limit], ("last", "times", "question")) if rows else None
        print(f"\n{len(rows)} distinct question(s) in {shown(MISS_LOG)}")
    else:
        print("no misses recorded")
    gaps = [r for r in logged if r["verb"] == "gap"]
    if gaps:
        print("\ngaps recorded by reading:")
        show([{"last": g["when"][:10], "entry": g["ids"], "gap": g["text"]} for g in gaps][::-1][:limit], ("last", "entry", "gap"))
        print("Close one with graph:ask -- close <ID> once its signpost is written.")
    if near:
        close = [(r["when"], f"{r['verb']} {r['text']}  [{r['best']}: {r['ids']}]") for r in logged
                 if r["verb"] == "find" and r["best"] and WEAK <= float(r["best"]) < NEAR]
        print(f"\nnear answers, best score from {WEAK} to under {NEAR}:")
        rows = _distinct(close)
        show(rows[:limit], ("last", "times", "question")) if rows else print("none recorded")
    return 0


def show(rows: list, columns: tuple[str, ...], below=None) -> None:
    """A table whose cells are cut at 90 characters, with ``below(row)`` printed under each row,
    indented, where it is given and returns text."""
    widths = {c: max(len(c), *(len(str(r.get(c) or "")) for r in rows)) for c in columns}
    for c in columns:
        widths[c] = min(widths[c], 90)
    print("  ".join(c.ljust(widths[c]) for c in columns).rstrip())
    print("  ".join("-" * widths[c] for c in columns))
    for row in rows:
        print("  ".join(str(row.get(c) or "")[: widths[c]].ljust(widths[c]) for c in columns).rstrip())
        if below and (text := below(row)):
            print("    " + text)


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
    p.add_argument("--kind", default="", help=f"comma-separated, of {', '.join(KINDS)}. Declared ontology terms are searched only when term is named, for a question about what a class or property means or whether one exists")
    p.add_argument("--exclude", default="", help="comma-separated kinds to leave out and keep every other, such as question when plan questions crowd out the entries that answer")
    p.add_argument("--phase", default="", help=f"comma-separated, of {', '.join(PHASES)}")
    p.add_argument("--audience", default="", help=f"comma-separated, of {', '.join(AUDIENCES)}")
    for flag, (scheme, _) in FACET_FLAGS.items():
        p.add_argument(f"--{flag}", default="", help=f"comma-separated values of the {scheme} facet, which raise matching entries and hide none. See docs/developer/facets.md")
    p.add_argument("--limit", type=int, default=8)
    m = sub.add_parser("misses", help="the questions answered weakly or not at all, newest first, and the gaps recorded")
    m.add_argument("--limit", type=int, default=20)
    m.add_argument("--near", action="store_true", help=f"also the questions answered from {WEAK} to under {NEAR}")
    c = sub.add_parser("close", help="close the gaps recorded against entries whose signpost is now written, and remove their log lines")
    c.add_argument("ids", nargs="+")
    g = sub.add_parser("gap", help="record what reading found that the index did not say, as you find it")
    g.add_argument("text", help="what was found, in a sentence")
    g.add_argument("extras", nargs="*", help="the entry it qualifies, such as STD-280, and the path:line it was read from")
    arguments = parser.parse_args()

    if arguments.question == "misses":
        return misses(arguments.limit, arguments.near, store())
    if arguments.question == "close":
        return close(arguments.ids)
    if arguments.question == "gap":
        return gap(arguments.text, arguments.extras)

    if arguments.question == "find":
        chosen = []
        for flag, values in (("kind", KINDS), ("phase", PHASES), ("audience", AUDIENCES)):
            given = [v.strip() for v in getattr(arguments, flag).split(",") if v.strip()]
            unknown = [v for v in given if v not in values]
            if unknown:
                parser.error(f"--{flag} {', '.join(unknown)} is not one of {', '.join(values)}")
            chosen.append({values[v] for v in given})
        excluded = [v.strip() for v in arguments.exclude.split(",") if v.strip()]
        if unknown := [v for v in excluded if v not in KINDS]:
            parser.error(f"--exclude {', '.join(unknown)} is not one of {', '.join(KINDS)}")
        chosen[0] = without(chosen[0], {KINDS[v] for v in excluded})
        db = store()
        known = facet_values(db)
        given = {}
        for flag, (scheme, _) in FACET_FLAGS.items():
            given[scheme] = [v.strip() for v in getattr(arguments, flag).split(",") if v.strip()]
            unknown = [v for v in given[scheme] if v not in known.get(scheme, {})]
            if unknown:
                parser.error(f"--{flag} {', '.join(unknown)} is not a value of the {scheme} facet. See docs/developer/facets.md")
        chosen[1] = phase_matches(db, chosen[1])
        return find(db, " ".join(arguments.words), *chosen, arguments.limit, expand(db, given))

    db = store()
    question = f"{arguments.question} {arguments.argument}"

    if arguments.question == "read":
        return read(db, arguments.argument)

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
