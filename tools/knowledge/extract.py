# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Derive the knowledge index from the working documents, and load it into an Oxigraph store.

The index holds no content of its own ([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md)
decision 1). Every fact here is read from a tracked Markdown or Turtle document, every claim is the
lead sentence of its own entry rather than a second copy of it, and deleting the store loses nothing
but speed. The family table, the normalisation rule and the definition rules live in
``identifiers.py``, so a family is described once.

What this writes, as named graphs:

``ki:index``
    the nodes of the resolvable identifier families, with claim, pointer, status and the relations
    their documents declare
``ki:terms``
    the ontology term summary: every class, property and vocabulary a module declares, with its
    label and owning module. This is what answers "does this already exist" without reading 270
    documents, which is the error class the index is for
``https://lattice.local/graph/<path>``
    one graph per ontology document, the full axioms, loaded for a query that needs them

Two rules the corpus forced, both measured.

**Enumeration is from ``git ls-files``, never a filesystem walk** (ADR-A134 decision 11). A checkout
can hold ignored directories of confidential third-party material.

**The load is per document and reports what failed** (TSD-37). One tracked fixture holds IRIs with
two fragment separators, which rdflib accepts and Oxigraph refuses, so a single batch load would
lose the whole corpus to one bad file.

Usage, from the repository root::

    mise run build:knowledge        # derive and load
    mise run graph:ask --help       # query it
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import pyoxigraph as ox
# ponytail: PyYAML is declared by tools/mork, not by this tooling, which declares nothing of its
# own. Declare it here if tools/knowledge becomes a package.
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import anchors  # noqa: E402
import embed  # noqa: E402
import facets  # noqa: E402
import identifiers  # noqa: E402
import lattice_repo_catalogue  # noqa: E402
import quanta  # noqa: E402

ROOT = identifiers.ROOT
ONTOLOGY = identifiers.CATALOGUE.area("ontology")
STORE_PATH = ROOT / ".build" / "knowledge" / "store"
# When the store was built from, as the build's start time. A query compares every tracked file
# against it, so the index never answers from lines a document no longer holds.
STAMP_PATH = ROOT / ".build" / "knowledge" / "built-from"
TBOX_PATH = Path(__file__).resolve().parent / "knowledge.ttl"
# Generated from the facet register on every build, never committed (ADR-A134 decision 26, STD-003).
FACETS_PATH = facets.OUTPUT_PATH
FACET_NS = "https://www.nebularis.org/neuro-semantic/lattice/dev/facets#"

KI = "https://www.nebularis.org/neuro-semantic/lattice/dev/knowledge#"
RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
RDFS_LABEL = ox.NamedNode("http://www.w3.org/2000/01/rdf-schema#label")
INDEX_GRAPH = ox.NamedNode(KI + "index")
TERMS_GRAPH = ox.NamedNode(KI + "terms")
TBOX_GRAPH = ox.NamedNode(KI + "tbox")
FACETS_GRAPH = ox.NamedNode(KI + "facets")

# Which node class each identifier family becomes.
FAMILY_CLASS = {
    "decision": "Decision",
    "pending-decision": "PendingDecision",
    "technical-debt": "Debt",
    "store-discovery": "Discovery",
    "mechanism": "Mechanism",
    "capability": "Capability",
    "pattern": "Pattern",
    "principle": "Principle",
    "standard": "Standard",
}

# The status words a decision's Status line may open with, longest first so "Published" is not read
# as a prefix of nothing. The line's freeform tail is discarded: the typed individual is the fact.
PUBLISHED_RE = re.compile(r"^Published, (?P<date>\d{4}-\d{2}-\d{2})\.")

STATUS_WORDS = (
    "Superseded",
    "Proposed",
    "Accepted",
    "Rejected",
    "Withdrawn",
    "Deferred",
    "Complete",
)

STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(?P<status>.+?)\s*$")
RELATED_RE = re.compile(r"^\*\*Related:\*\*\s*(?P<rest>.+?)\s*$")
TITLE_RE = re.compile(r"^#\s+ADR[-‑ ]A[\w.-]*?\d+[a-z]?\s*[:.]\s*(?P<title>.+?)\s*$")
BOLD_RE = re.compile(r"\*\*(?P<claim>.+?)\*\*")
DECLARES_RE = re.compile(
    r"^(?P<term>[a-z][\w.-]*:[A-Za-z][\w-]*)\s+(?:a|rdf:type)\s+"
    r"(?P<kind>owl:Class|owl:ObjectProperty|owl:DatatypeProperty|skos:Concept|skos:ConceptScheme)"
)
LABEL_RE = re.compile(r'rdfs:label\s+"(?P<label>[^"]{1,200})"')

CLAIM_LIMIT = 200


def tracked(*patterns: str) -> list[Path]:
    """Tracked files matching any pattern, from git rather than the filesystem."""
    listing = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", *patterns],
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted({ROOT / name for name in listing.stdout.split("\0") if name})


def node(identifier: str) -> ox.NamedNode:
    return ox.NamedNode(KI + "node/" + identifiers.normalise(identifier))


def term(name: str) -> ox.NamedNode:
    return ox.NamedNode(KI + "term/" + name.replace(":", "."))


def ki(local: str) -> ox.NamedNode:
    return ox.NamedNode(KI + local)


def shorten(text: str) -> str:
    """A claim is one sentence. Anything longer is a narrative and is cut, not stored whole."""
    text = re.sub(r"\s+", " ", re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)).strip()
    return text if len(text) <= CLAIM_LIMIT else text[: CLAIM_LIMIT - 1].rstrip() + "…"


def status_of(line: str) -> str | None:
    """The typed status an ADR's Status line opens with, or None if it opens with nothing known."""
    for word in STATUS_WORDS:
        if line.startswith(word):
            return word
    return None


@dataclass
class Extract:
    quads: list[ox.Quad] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    def bump(self, key: str, by: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + by


def decision_claim(lines: list[str]) -> str | None:
    """What a decision decides: the start of its Decision section, read as text.

    A title names a decision, often by a noun phrase such as "Provenance Model", which says too
    little for a question phrased as the problem to reach it. So the claim is the section's own
    words up to the claim limit: paragraphs, subheadings and table rows, without code blocks or a
    table's header row. A bold lead that is a whole sentence, as in a numbered list of decisions,
    is the claim by itself. A lead-in such as "Rules:" is not."""
    start = next((i for i, l in enumerate(lines) if re.match(r"^##\s+Decision", l)), None)
    if start is None:
        return None
    items: list[str] = []
    fenced = False
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if line.startswith("## "):
            break
        if stripped.startswith("```"):
            fenced = not fenced
            continue
        if fenced or not stripped or stripped.startswith(("<!--", ">")):
            continue
        if SEPARATOR_RE.match(stripped):
            if items:
                items.pop()  # the row above a separator is the table's header
            continue
        if stripped.startswith("|"):
            items.append(", ".join(c for c in table_cells(stripped) if c))
        else:
            items.append(re.sub(r"^(#+\s*|[-*]\s+)", "", stripped))
        if not items[:-1] and (bold := BOLD_RE.match(re.sub(r"^\d+\.\s*", "", items[-1]))):
            lead = bold.group("claim").strip()
            if len(lead) > 30 and not lead.endswith(":"):
                return shorten(lead)
        if sum(map(len, items)) >= CLAIM_LIMIT:
            break
    text = re.sub(r"\*\*|`", "", " ".join(items))
    return shorten(text) if text.strip() else None


def decisions(out: Extract) -> dict[str, ox.NamedNode]:
    """One node per decision file, named by its title, with what it decides as the claim and its
    Related line as declared edges."""
    known: dict[str, ox.NamedNode] = {}
    family = next(f for f in identifiers.FAMILIES if f.name == "decision")
    defined = identifiers.definitions(family)
    for path in tracked((identifiers.ARCHITECTURE / "decisions" / "*.md").as_posix()):
        match = family.mention.match(path.stem)
        if not match:
            continue
        canonical = match.group(1)
        subject = node(canonical)
        known[identifiers.normalise(canonical)] = subject
        rel = path.relative_to(ROOT).as_posix()
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        seen_status = False

        out.quads.append(ox.Quad(subject, RDF_TYPE, ki("Decision"), INDEX_GRAPH))
        out.quads.append(ox.Quad(subject, ki("identifier"), ox.Literal(canonical), INDEX_GRAPH))
        out.quads.append(
            ox.Quad(subject, ki("definedIn"), ox.NamedNode(f"https://lattice.local/doc/{rel}"), INDEX_GRAPH)
        )
        for number, line in enumerate(lines, 1):
            if (title := TITLE_RE.match(line)) is not None:
                name = shorten(title.group("title"))
                out.quads.append(ox.Quad(subject, RDFS_LABEL, ox.Literal(name), INDEX_GRAPH))
                out.quads.append(
                    ox.Quad(subject, ki("claim"), ox.Literal(decision_claim(lines) or name), INDEX_GRAPH)
                )
                start, end = anchors.section_at(lines, number)
                out.quads.append(
                    ox.Quad(subject, ki("pointer"), ox.Literal(f"{rel}:{start}-{end}"), INDEX_GRAPH)
                )
            elif (st := STATUS_RE.match(line)) is not None and not seen_status:
                # Only the header's Status line is the decision's status. A later one belongs to a
                # dated addendum, and taking both would give one node two statuses, which would
                # make the check that no Accepted decision depends on a Proposed one meaningless.
                seen_status = True
                line_status = st.group("status")
                # Publication is a flag, not a lifecycle state, so a published decision keeps the
                # state its own line gives it after the publication clause.
                if (published := PUBLISHED_RE.match(line_status)) is not None:
                    out.quads.append(
                        ox.Quad(subject, ki("publishedOn"),
                                ox.Literal(published.group("date")), INDEX_GRAPH)
                    )
                    out.bump("published")
                    line_status = line_status[published.end():].strip()
                word = status_of(line_status)
                if word is None:
                    out.problems.append(f"{rel}:{number}: Status line opens with no known word")
                else:
                    out.quads.append(ox.Quad(subject, ki("status"), ki(word), INDEX_GRAPH))
                    out.bump(f"status:{word}")
            elif (related := RELATED_RE.match(line)) is not None:
                for spelling in family.mention.findall(related.group("rest")):
                    key = identifiers.normalise(spelling)
                    if key in defined and key != identifiers.normalise(canonical):
                        out.quads.append(ox.Quad(subject, ki("relatedTo"), node(spelling), INDEX_GRAPH))
                        out.bump("relatedTo")
        if not seen_status:
            # Measured: 7 of the 120 decisions carry their status as a `## Status` section rather
            # than a `**Status:**` header field, which is the older of two conventions in the
            # catalogue. Reported rather than guessed at, because a node with no status is invisible
            # to every check that compares one.
            out.problems.append(f"{rel}: no **Status:** header field, so {canonical} has no status")
            out.bump("decision-without-status")
        out.bump("decision")
    return known


def facet_slugs() -> dict[str, set[str]]:
    """The taggable values of each facet scheme, so a tag outside its scheme can be refused.

    A group, a value carrying the editorial note "group", is filtered on and never tagged."""
    graph = ox.Store()
    graph.load(path=str(facets.generate()), format=ox.RdfFormat.TURTLE)
    rows = graph.query(
        "PREFIX skos: <http://www.w3.org/2004/02/skos/core#> "
        "SELECT ?c ?scheme WHERE { ?c a skos:Concept ; skos:inScheme ?scheme "
        "FILTER NOT EXISTS { ?c skos:editorialNote \"group\" } }"
    )
    slugs: dict[str, set[str]] = {}
    for row in rows:
        slugs.setdefault(row["scheme"].value.removeprefix(FACET_NS), set()).add(row["c"].value.removeprefix(FACET_NS))
    return slugs


# A register's table header IS its schema. Each column header maps to a T-Box property, and the
# meaning of a column is that property's rdfs:comment in knowledge.ttl, written once. The kinds:
# ``id`` the identifier, ``claim`` the first bolded span, ``label`` rdfs:label, ``text`` a plain
# literal, ``module`` ki:ownedBy, ``audience``, ``phase`` and ``ratified`` controlled.
COLUMNS: dict[str, tuple[str, str]] = {
    "ID": ("identifier", "id"),
    "#": ("identifier", "id"),
    "Claim": ("claim", "claim"),
    "Capability": ("claim", "claim"),
    "Debt": ("claim", "claim"),
    "Decision": ("claim", "claim"),
    "Name": ("label", "label"),
    "Pointer": ("pointer", "text"),
    "Problem shape": ("problemShape", "text"),
    "Activity": ("activity", "facet:Activity"),
    "Quality": ("quality", "facet:Quality"),
    "Technology": ("technology", "facet:Technology"),
    "Waits for": ("waitsOn", "ids"),
    "Evidenced by": ("evidencedBy", "ids"),
    "Decided by": ("decidedBy", "ids"),
    "Refines": ("refines", "ids"),
    "Supports": ("supports", "ids"),
    "Enforced by": ("enforcedBy", "ids"),
    "Stratum": ("stratum", "stratum"),
    "Governs": ("governs", "names"),
    "Fitness scope": ("fitnessScope", "fitnessScope"),
    "Cadence": ("cadence", "cadence"),
    "Origin": ("origin", "origin"),
    "Cost": ("cost", "text"),
    "Owner": ("ownedBy", "module"),
    "Provided by": ("ownedBy", "module"),
    "Audience": ("audience", "audience"),
    "Phase": ("phase", "phase"),
    "Entry point": ("entryPoint", "text"),
    "Built": ("built", "built"),
    "Ratified": ("status", "ratified"),
}

# Human-only columns, deliberately not indexed. A header in neither table is a reported problem.
UNMAPPED_COLUMNS = frozenset(
    {
        "Conf", "Reuse note",
        "Spotted", "Cost while it stays", "Likely home",
        "Raised", "Cost of deferring", "Options known",
    }
)

CONTROLLED = {
    "audience": {"internal": "InternalUse", "published": "PublishedUse"},
    "phase": {"development": "Development", "authoring": "Authoring", "runtime": "Runtime",
              "testing": "Testing", "benchmarking": "Benchmarking", "production": "Production"},
    "built": {"built": "Built", "partial": "PartlyBuilt", "proposed": "NotBuilt"},
    "ratified": {"yes": "Accepted", "no": "Proposed"},
    "stratum": {"architectural": "ArchitecturalStratum", "design": "DesignStratum",
                "practice": "PracticeStratum", "convention": "ConventionStratum"},
    "origin": {"stated": "Stated", "extrapolated": "Extrapolated"},
    "fitnessScope": {"atomic": "Atomic", "holistic": "Holistic"},
    "cadence": {"triggered": "Triggered", "continual": "Continual"},
}

SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|?$")


_UNITS: dict[str, list[str]] | None = None


def owner_units(value: str) -> list[str] | None:
    """The catalogue units an owner value names, as module IRI tails, or None if it names nothing.

    The catalogue is the one source of modules and tool packages (ADR-A121), read by its own reader.
    A value is a module name, a tool package's path or name, a root area's path, or a module kind
    such as ``substrate``, which is every module of that kind. An annotation in parentheses is
    stripped. A module IRI is its name and any other unit's is its path, so a tool package never
    collides with the module of the same name.
    """
    global _UNITS
    if _UNITS is None:
        catalogue = lattice_repo_catalogue.load(identifiers.ROOT)
        units: dict[str, list[str]] = {}
        for tool in catalogue.tools:
            units[tool.name] = units[tool.path] = [tool.path]
        for area in catalogue.roots + catalogue.docs:
            units[area.path.rstrip("/")] = [area.path.rstrip("/")]
        for kind in {m.kind for m in catalogue.modules.values()}:
            units[kind] = [m.name for m in catalogue.modules_of_kind(kind)]
        for name in catalogue.modules:
            units[name] = [name]
        _UNITS = units
    return _UNITS.get(re.sub(r"\s*\(.*?\)", "", value).strip(" `").rstrip("/"))


def table_cells(line: str) -> list[str]:
    cells = line.strip().split("|")[1:]
    if cells and not cells[-1].strip():
        cells.pop()
    return [c.strip() for c in cells]


def waited_on(cell: str) -> list[str]:
    """Every identifier of a resolvable family written in a cell, once each, in order."""
    found: dict[str, str] = {}
    for family in identifiers.FAMILIES:
        if family.resolvable:
            for spelling in family.mention.findall(cell):
                found.setdefault(identifiers.normalise(spelling), spelling)
    return list(found.values())


def register_rows(out: Extract) -> None:
    """One node per row of each register, read by column header (see ``COLUMNS``)."""
    known_facets = facet_slugs()
    for family in identifiers.FAMILIES:
        if family.name not in FAMILY_CLASS or family.definition != "table-row":
            continue
        for pattern in family.defines:
            for path in sorted(ROOT.glob(pattern)):
                rel = path.relative_to(ROOT).as_posix()
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                headers: list[str] | None = None
                checked = False
                for number, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if not stripped.startswith("|"):
                        headers = None
                        continue
                    following = lines[number].strip() if number < len(lines) else ""
                    if SEPARATOR_RE.match(following) and not SEPARATOR_RE.match(stripped):
                        headers, checked = table_cells(stripped), False
                        continue
                    if headers is None or SEPARATOR_RE.match(stripped):
                        continue
                    cells = table_cells(stripped)
                    id_at = next((i for i, h in enumerate(headers) if COLUMNS.get(h, ("", ""))[1] == "id"), 0)
                    match = family.mention.fullmatch(cells[id_at]) if id_at < len(cells) else None
                    if not match:
                        continue
                    if not checked:
                        checked = True
                        for header in headers:
                            if header not in COLUMNS and header not in UNMAPPED_COLUMNS:
                                out.problems.append(
                                    f"{rel}:{number}: column '{header}' is neither mapped to a "
                                    f"property nor on the unmapped list"
                                )
                    canonical = match.group(1)
                    subject = node(canonical)
                    if len(cells) != len(headers):
                        out.problems.append(
                            f"{rel}:{number}: {canonical} has {len(cells)} cells under "
                            f"{len(headers)} headers, so its columns cannot be trusted"
                        )
                        continue
                    here = f"{rel}:{number}: {canonical}"

                    def add(prop: str, obj) -> None:
                        out.quads.append(ox.Quad(subject, ki(prop), obj, INDEX_GRAPH))

                    out.quads.append(
                        ox.Quad(subject, RDF_TYPE, ki(FAMILY_CLASS[family.name]), INDEX_GRAPH)
                    )
                    add("identifier", ox.Literal(canonical))
                    status = "Open"
                    has_claim = has_pointer = False
                    for header, cell in zip(headers, cells):
                        if header not in COLUMNS or not cell or COLUMNS[header][1] == "id":
                            continue
                        prop, kind = COLUMNS[header]
                        if kind == "claim":
                            bold = BOLD_RE.search(cell)
                            claim = shorten(bold.group("claim") if bold else cell)
                            add("claim", ox.Literal(claim))
                            has_claim = True
                        elif kind == "label":
                            out.quads.append(ox.Quad(subject, RDFS_LABEL, ox.Literal(cell), INDEX_GRAPH))
                        elif kind == "text" and prop == "pointer":
                            # An anchor, resolved against the files as they are now. One that no longer
                            # resolves is reported, never replaced by a guessed range.
                            ranges, failed = anchors.resolve(ROOT, cell)
                            out.problems.extend(f"{here} has Pointer {reason}" for reason in failed)
                            if ranges:
                                add("pointer", ox.Literal(",".join(ranges)))
                            has_pointer = True
                        elif kind == "text":
                            add(prop, ox.Literal(cell.replace("`", "") if prop == "entryPoint" else cell))
                            if prop == "problemShape":
                                out.bump("problem-shape")
                        elif kind == "module":
                            for owner in (o.strip() for o in cell.split(",")):
                                units = owner_units(owner) if owner else []
                                if units is None:
                                    out.problems.append(
                                        f"{here} has {header} '{owner}', which names no catalogue module or tool package"
                                    )
                                for unit in units or []:
                                    add(prop, ox.NamedNode(KI + "module/" + unit))
                        elif kind == "names":
                            # A quantum is derived, so it is named rather than defined in a
                            # document. A test checks every name resolves to a derived quantum.
                            for name in (n.strip() for n in cell.split(",")):
                                if name:
                                    add(prop, node(name))
                                    out.bump(prop)
                        elif kind == "ids":
                            for other in waited_on(cell):
                                if other != canonical:
                                    add(prop, node(other))
                                    out.bump(prop)
                        elif kind == "ratified":
                            value = CONTROLLED["ratified"].get(cell.lower())
                            if value is None:
                                out.problems.append(f"{here} has Ratified '{cell}', not yes or no")
                            else:
                                status = value
                        elif kind.startswith("facet:"):
                            scheme = kind.removeprefix("facet:")
                            for value in (v.strip() for v in cell.split(",")):
                                if value and value not in known_facets[scheme]:
                                    out.problems.append(f"{here} has {header} '{value}', which is not a taggable value of the {scheme} facet")
                                elif value:
                                    add(prop, ox.NamedNode(FACET_NS + value))
                                    out.bump(f"facet:{scheme}")
                        else:
                            allowed = CONTROLLED[kind]
                            for value in (v.strip() for v in cell.split(",")):
                                if not value:
                                    continue
                                if value not in allowed:
                                    out.problems.append(f"{here} has {header} '{value}', outside {sorted(allowed)}")
                                    continue
                                add(prop, ki(CONTROLLED[kind][value]))
                    add("status", ki(status))
                    if not has_pointer:
                        add("pointer", ox.Literal(f"{rel}:{number}-{number}"))
                    if not has_claim:
                        out.problems.append(f"{here} has no extractable claim")
                    out.bump(family.name)


def technology_words() -> dict[str, re.Pattern[str]]:
    """Each taggable Technology value, with a pattern that finds its slug or label as a whole word."""
    graph = ox.Store()
    graph.load(path=str(facets.generate()), format=ox.RdfFormat.TURTLE)
    rows = graph.query(
        "PREFIX skos: <http://www.w3.org/2004/02/skos/core#> "
        "SELECT ?c ?l WHERE { ?c skos:inScheme <" + FACET_NS + "Technology> ; skos:prefLabel ?l "
        "FILTER NOT EXISTS { ?c skos:editorialNote \"group\" } }"
    )
    words = {}
    for row in rows:
        slug = row["c"].value.removeprefix(FACET_NS)
        names = {slug, row["l"].value}
        words[slug] = re.compile(r"(?<![\w.-])(" + "|".join(map(re.escape, names)) + r")(?![\w-])", re.I)
    return words


def discoveries(out: Extract) -> None:
    """One node per discovery, whose heading already is its claim.

    A finding's technology is derived from its Evidence line, which names the engines and versions it
    was found on, so the fact is read where the record states it and never authored twice. "Both
    stores" means the stores the record's own Stores covered line names, and an engine named in the
    heading, which is the finding's claim, counts too. Its
    activity and quality are not stated, so it carries none, which hides it from no question."""
    family = next(f for f in identifiers.FAMILIES if f.name == "store-discovery")
    words = technology_words()
    for pattern in family.defines:
        for path in sorted(ROOT.glob(pattern)):
            rel = path.relative_to(ROOT).as_posix()
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            covered = next((l for l in lines if l.startswith("**Stores covered:**")), "")
            both = {slug for slug, pattern in words.items() if pattern.search(covered)}
            for number, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped.startswith("#"):
                    continue
                heading = stripped.lstrip("#").strip()
                match = family.mention.match(heading)
                if not match:
                    continue
                canonical = match.group(1)
                subject = node(canonical)
                claim = heading[match.end() :].lstrip(". ").strip()
                out.quads.append(ox.Quad(subject, RDF_TYPE, ki("Discovery"), INDEX_GRAPH))
                out.quads.append(ox.Quad(subject, ki("identifier"), ox.Literal(canonical), INDEX_GRAPH))
                start, end = anchors.section_at(lines, number)
                out.quads.append(ox.Quad(subject, ki("pointer"), ox.Literal(f"{rel}:{start}-{end}"), INDEX_GRAPH))
                out.quads.append(ox.Quad(subject, ki("claim"), ox.Literal(shorten(claim)), INDEX_GRAPH))
                evidence = next((l for l in lines[start - 1 : end] if l.startswith("**Evidence:**")), "")
                for slug, pattern in words.items():
                    if pattern.search(evidence) or pattern.search(heading) or ("both stores" in evidence and slug in both):
                        out.quads.append(ox.Quad(subject, ki("technology"), ox.NamedNode(FACET_NS + slug), INDEX_GRAPH))
                        out.bump("facet:Technology:derived")
                out.bump("store-discovery")


def source_lines() -> dict[str, str]:
    """Best-effort map from a declared term's name to the `path:line` that declares it.

    A query over the loaded graphs gives the complete term set and every label, but an RDF graph has
    no line numbers, and a pointer an agent cannot jump to is worth much less. So the authoritative
    facts come from the query below and the line number is grafted on from a line-wise pass, which
    misses some declarations and is therefore never the source of the term set itself.
    """
    found: dict[str, str] = {}
    for path in tracked((ONTOLOGY / "*.ttl").as_posix(), (ONTOLOGY / "**" / "*.ttl").as_posix()):
        rel = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if (declared := DECLARES_RE.match(line)) is not None:
                found.setdefault(declared.group("term"), f"{rel}:{number}")
    return found


def term_summary(store: ox.Store, out: Extract) -> None:
    """Every term a module declares, with its label, kind and owner.

    Derived by query over the documents already loaded, which is both complete and robust: a
    line-wise read of the Turtle found 2,204 of the terms and only 279 of their labels, and labels
    are what a recall query matches on. The owning module comes from the graph IRI, which is the
    document's own path, so the fact still has exactly one source (ADR-A134 decision 2).
    """
    lines = source_lines()
    rows = store.query(
        """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?g ?s ?kind ?label WHERE {
          GRAPH ?g {
            ?s a ?kind .
            FILTER (?kind IN (owl:Class, owl:ObjectProperty, owl:DatatypeProperty,
                              skos:Concept, skos:ConceptScheme))
            OPTIONAL { ?s rdfs:label ?label }
          }
          FILTER (STRSTARTS(STR(?g), "https://lattice.local/graph/"))
        }"""
    )
    quads: list[ox.Quad] = []
    seen: set[str] = set()
    for row in rows:
        graph, subject, kind, label = row["g"], row["s"], row["kind"], row["label"]
        if not isinstance(subject, ox.NamedNode):
            continue
        rel = str(graph.value).removeprefix("https://lattice.local/graph/")
        parts = rel.split("/")
        if len(parts) < 2:
            continue
        module = "/".join(parts[1:3]) if parts[1] == "applied" else parts[1]
        name = str(subject.value)
        node_iri = ox.NamedNode(KI + "term/" + name.rsplit("/", 1)[-1].replace("#", "."))
        if name not in seen:
            seen.add(name)
            quads.append(ox.Quad(node_iri, RDF_TYPE, ki("Term"), TERMS_GRAPH))
            quads.append(ox.Quad(node_iri, ki("identifier"), ox.Literal(name), TERMS_GRAPH))
            quads.append(ox.Quad(node_iri, ki("ownedBy"), ox.NamedNode(KI + "module/" + module), TERMS_GRAPH))
            quads.append(
                ox.Quad(node_iri, ki("declaredAs"), ox.Literal(str(kind.value).rsplit("#", 1)[-1]), TERMS_GRAPH)
            )
            short = name.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            pointer = next((v for k, v in lines.items() if k.rsplit(":", 1)[-1] == short), rel)
            quads.append(ox.Quad(node_iri, ki("pointer"), ox.Literal(pointer), TERMS_GRAPH))
            out.bump("term")
        if label is not None:
            quads.append(ox.Quad(node_iri, RDFS_LABEL, ox.Literal(str(label.value)), TERMS_GRAPH))
            out.bump("term-label")
    store.bulk_extend(quads)


def load_ontologies(store: ox.Store, out: Extract) -> None:
    """Every ontology document in a graph of its own, parsed one at a time so one bad file loses only
    itself (TSD-37), then written to the store in a single bulk write.

    Not one bulk load per document: each writes SST files of its own, which compaction does not merge
    back, so 270 of them left over a thousand files in the store, and a query or a read-only open that
    has to open them all exceeds macOS's default limit of 256 open files (TSD-39).
    """
    quads: list[ox.Quad] = []
    for path in tracked((ONTOLOGY / "*.ttl").as_posix(), (ONTOLOGY / "**" / "*.ttl").as_posix()):
        rel = path.relative_to(ROOT).as_posix()
        graph = ox.NamedNode(f"https://lattice.local/graph/{rel}")
        try:
            # Parsed in full before anything is kept, so a document failing part-way contributes nothing.
            # Blank nodes are renamed so each document's stay its own, as a per-document load kept them.
            parsed = [ox.Quad(q.subject, q.predicate, q.object, graph)
                      for q in ox.parse(path=str(path), format=ox.RdfFormat.TURTLE,
                                                 rename_blank_nodes=True)]
        except (SyntaxError, ValueError) as error:
            out.problems.append(f"{rel}: does not parse, so its axioms are absent ({error.__class__.__name__})")
            out.bump("ontology-document-failed")
            continue
        quads += parsed
        out.bump("ontology-document")
    store.bulk_extend(quads)


VIEW = {"data": "DataView", "software": "SoftwareView"}


def derive_quanta(store: ox.Store, out: Extract) -> None:
    """Every architectural quantum of the data and software views, derived from coupling.

    The data view reads the imports between the ontology documents already loaded, and the software
    view each deployment's compose file. See quanta.py for the rules.
    """
    catalogue = lattice_repo_catalogue.load(ROOT)
    modules = {m.name: m for m in catalogue.modules.values()}
    paths = sorted(
        ((Path(m.path).resolve().relative_to(ROOT).as_posix(), m.name) for m in modules.values()),
        key=lambda pair: -len(pair[0]),
    )

    def module_of(rel: str) -> str | None:
        return next((name for path, name in paths if rel == path or rel.startswith(path + "/")), None)

    graph = "https://lattice.local/graph/"
    declared: dict[str, str] = {}
    for row in store.query(
        "PREFIX owl: <http://www.w3.org/2002/07/owl#> SELECT ?g ?o ?v WHERE { GRAPH ?g { ?o a owl:Ontology "
        "OPTIONAL { ?o owl:versionIRI ?v } } }"
    ):
        rel = str(row["g"].value).removeprefix(graph)
        for term in (row["o"], row["v"]):
            if term is not None:
                declared[str(term.value)] = rel
    imports: set[tuple[str, str]] = set()
    for row in store.query(
        "PREFIX owl: <http://www.w3.org/2002/07/owl#> SELECT ?g ?t WHERE { GRAPH ?g { ?x owl:imports ?t } }"
    ):
        importer = module_of(str(row["g"].value).removeprefix(graph))
        target = declared.get(str(row["t"].value))
        imported = module_of(target) if target else None
        if importer and imported and importer != imported:
            imports.add((importer, imported))

    readme = {
        name: f"{path}/README.md" for path, name in paths if (ROOT / path / "README.md").exists()
    }
    found, straddling = quanta.data_quanta(
        {n: m.kind for n, m in modules.items()},
        imports,
        {m.name for m in catalogue.release_members()},
        readme,
    )
    for name in straddling:
        out.findings.append(
            f"{name} shares the substrate's release number although nothing in the substrate imports "
            f"it, so the release policy places it across a quantum boundary"
        )
    for path in tracked("deployment/*/docker-compose.yml", "deployment/**/docker-compose.yml"):
        rel = path.relative_to(ROOT).as_posix()
        # A deployment is named by its directory below the deployment root, read from the path git
        # gave, so the root is never rebuilt here (ADR-A121).
        deployment = "/".join(Path(rel).parts[1:-1])
        found += quanta.software_quanta(deployment, yaml.safe_load(path.read_text(encoding="utf-8")) or {}, rel)

    quads: list[ox.Quad] = []
    for q in found:
        subject = node(q.identifier)
        quads += [
            ox.Quad(subject, RDF_TYPE, ki("Quantum"), INDEX_GRAPH),
            ox.Quad(subject, ki("identifier"), ox.Literal(q.identifier), INDEX_GRAPH),
            ox.Quad(subject, ki("claim"), ox.Literal(q.claim), INDEX_GRAPH),
            ox.Quad(subject, ki("pointer"), ox.Literal(anchors.resolve_part(ROOT, q.pointer)), INDEX_GRAPH),
            ox.Quad(subject, ki("view"), ki(VIEW[q.view]), INDEX_GRAPH),
        ]
        if q.deployment:
            quads.append(ox.Quad(subject, ki("deployment"), ox.Literal(q.deployment), INDEX_GRAPH))
        for part in q.parts:
            if q.view == "data":
                iri, kind = ox.NamedNode(KI + "module/" + part), "Module"
            else:
                iri, kind = ox.NamedNode(KI + f"component/{q.deployment}/{part}"), "Component"
            quads += [
                ox.Quad(subject, ki("includes"), iri, INDEX_GRAPH),
                ox.Quad(iri, RDF_TYPE, ki(kind), INDEX_GRAPH),
                ox.Quad(iri, RDFS_LABEL, ox.Literal(part), INDEX_GRAPH),
            ]
        out.bump(f"quantum:{q.view}")
    store.bulk_extend(quads)


def build(store_path: Path) -> Extract:
    out = Extract()
    start = time.perf_counter()
    # Taken before reading anything, so a file edited while the build runs is caught next time.
    built_from = time.time()
    if store_path.exists():
        shutil.rmtree(store_path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store = ox.Store(str(store_path))

    store.bulk_load(path=str(TBOX_PATH), format=ox.RdfFormat.TURTLE, to_graph=TBOX_GRAPH)
    store.bulk_load(path=str(facets.generate()), format=ox.RdfFormat.TURTLE, to_graph=FACETS_GRAPH)
    decisions(out)
    register_rows(out)
    discoveries(out)
    store.bulk_extend(out.quads)
    load_ontologies(store, out)
    # After the documents are loaded, because the summary is derived by query over them.
    term_summary(store, out)
    # After the documents are loaded, because data-view coupling is read from their imports.
    derive_quanta(store, out)
    store.flush()
    store.optimize()

    out.counts["quads"] = len(list(store.quads_for_pattern(None, None, None, None)))
    if store_path == STORE_PATH:
        # Only the real index is embedded, so a test building elsewhere never loads the model.
        try:
            out.counts["embedded"] = embed.build(store, store_path.parent)
        except embed.Unavailable as error:
            out.problems.append(f"no embeddings, so graph:ask -- find cannot rank: {error}")
            out.bump("embeddings-unavailable")
        STAMP_PATH.write_text(f"{built_from}\n", encoding="utf-8")
    out.counts["seconds"] = round(time.perf_counter() - start, 2)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--store", default=str(STORE_PATH), help="where to build the store")
    parser.add_argument("--quiet", action="store_true")
    arguments = parser.parse_args()

    out = build(Path(arguments.store))
    for key in sorted(out.counts):
        if not arguments.quiet or key in {"quads", "seconds"}:
            print(f"  {key:<28} {out.counts[key]}")
    for problem in out.problems:
        print(f"NOTE: {problem}")
    for finding in out.findings:
        print(f"FINDING: {finding}")
    print(f"knowledge index built at {Path(arguments.store).relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
