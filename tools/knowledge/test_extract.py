# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Tests for the knowledge index extractor, over the real corpus.

The index is derived, so these tests are about whether the derivation tells the truth: that every
node it claims to have found exists, that a fact it could not read is reported rather than guessed,
and that one unreadable document does not take the corpus with it.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import pyoxigraph as ox
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import extract  # noqa: E402
import identifiers  # noqa: E402
import lattice_repo_catalogue  # noqa: E402

KI = extract.KI


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> tuple[extract.Extract, ox.Store]:
    """Build the index once, into a temporary store rather than the one in .build."""
    path = tmp_path_factory.mktemp("knowledge") / "store"
    out = extract.build(path)
    out.store_path = path
    return out, ox.Store.read_only(str(path))


def one(store: ox.Store, query: str) -> list:
    return list(store.query(query))


def test_every_decision_file_becomes_a_node(built):
    out, _ = built
    files = extract.tracked("docs/architecture/decisions/*.md")
    family = next(f for f in identifiers.FAMILIES if f.name == "decision")
    expected = sum(1 for p in files if family.mention.match(p.stem))
    assert out.counts["decision"] == expected


def test_a_known_decision_carries_its_claim_status_and_pointer(built):
    _, store = built
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?claim ?status ?pointer WHERE {{ GRAPH ki:index {{
          ?n ki:identifier "ADR-A131" ; ki:claim ?claim ; ki:status ?status ; ki:pointer ?pointer .
        }} }}""",
    )
    assert len(rows) == 1
    assert "Ledger" in str(rows[0]["claim"].value)
    assert str(rows[0]["status"].value).endswith("#Accepted")
    assert str(rows[0]["pointer"].value).startswith("docs/architecture/decisions/ADR-A131")


def test_no_decision_has_two_statuses(built):
    """A decision with a dated addendum carries a second Status line. Taking both would give one
    node two statuses and make the check that no Accepted decision depends on a Proposed one
    meaningless, so only the header's line counts."""
    _, store = built
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?n (COUNT(?s) AS ?c) WHERE {{ GRAPH ki:index {{ ?n a ki:Decision ; ki:status ?s }} }}
        GROUP BY ?n HAVING (COUNT(?s) > 1)""",
    )
    assert not [str(r["n"].value) for r in rows]


def test_a_decision_with_no_readable_status_is_reported_not_guessed(tmp_path, monkeypatch):
    """A node with no status is invisible to every check that compares one, so the extractor says
    so rather than inventing a default. Seven decisions once carried their status as a `## Status`
    section, which this caught."""
    decision = tmp_path / "docs/architecture/decisions/ADR-A999-fixture.md"
    decision.parent.mkdir(parents=True)
    decision.write_text("# ADR-A999: A fixture\n\n## Status\n\nAccepted\n", encoding="utf-8")
    monkeypatch.setattr(extract, "ROOT", tmp_path)
    monkeypatch.setattr(extract, "tracked", lambda *patterns: [decision])
    out = extract.Extract()
    extract.decisions(out)
    assert out.counts.get("decision-without-status") == 1
    assert sum("no **Status:** header field" in p for p in out.problems) == 1


def test_every_decision_in_the_corpus_states_its_status(built):
    out, _ = built
    assert out.counts.get("decision-without-status", 0) == 0, [p for p in out.problems if "Status:" in p]


def test_every_status_used_is_in_the_tbox_closed_set(built):
    """The status vocabulary exists to replace roughly fifteen freeform line shapes. If the
    extractor emitted one the T-Box does not declare, the set would not be closed."""
    _, store = built
    used = {
        str(r["s"].value)
        for r in one(
            store,
            f"PREFIX ki: <{KI}> SELECT DISTINCT ?s WHERE {{ GRAPH ki:index {{ ?n ki:status ?s }} }}",
        )
    }
    declared = {
        str(r["s"].value)
        for r in one(
            store,
            f"PREFIX ki: <{KI}> SELECT ?s WHERE {{ GRAPH ki:tbox {{ ?s a ki:Status }} }}",
        )
    }
    assert used <= declared, used - declared


def test_the_term_summary_answers_the_question_the_index_exists_for(built):
    """An agent once proposed a versioning system although Foundation already modelled one. This is
    that query, and it has to return Foundation's class with a pointer to read."""
    _, store = built
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?term ?pointer WHERE {{ GRAPH ki:terms {{
          ?t ki:identifier ?term ; ki:declaredAs "Class" ; ki:pointer ?pointer ;
             ki:ownedBy <{KI}module/foundation> .
          FILTER (CONTAINS(?term, "#Version"))
        }} }}""",
    )
    assert rows, "Foundation's Version class must be findable in the term summary"
    assert "foundation" in str(rows[0]["pointer"].value)


def test_every_tracked_ontology_document_parses_in_the_strict_store(built):
    """STD-023: every tracked ontology document parses in Oxigraph, which refuses what rdflib accepts.
    TSD-37 found one that did not, a MORK demonstration file, deleted on 2026-10-26."""
    out, _ = built
    assert out.counts["ontology-document"] > 250
    assert out.counts.get("ontology-document-failed", 0) == 0, [p for p in out.problems if "does not parse" in p]


def test_an_unparseable_document_is_reported_and_loses_only_itself(tmp_path, monkeypatch):
    """TSD-37: a document holding an IRI with two fragment separators, which Oxigraph refuses. A single
    batch load would lose every document to it, so the load is per document."""
    good = tmp_path / "good.ttl"
    good.write_text("<https://example.org/a> <https://example.org/p> <https://example.org/b> .\n", encoding="utf-8")
    bad = tmp_path / "bad.ttl"
    bad.write_text("<https://example.org/a#b#c> <https://example.org/p> <https://example.org/b> .\n", encoding="utf-8")
    monkeypatch.setattr(extract, "ROOT", tmp_path)
    monkeypatch.setattr(extract, "tracked", lambda *patterns: [good, bad])
    out = extract.Extract()
    store = ox.Store()
    extract.load_ontologies(store, out)
    assert out.counts.get("ontology-document") == 1
    assert out.counts.get("ontology-document-failed") == 1
    assert any("bad.ttl: does not parse" in p for p in out.problems)
    assert len(store) == 1


def test_the_registers_contribute_their_rows(built):
    out, _ = built
    assert out.counts["technical-debt"] > 40
    assert out.counts["pending-decision"] > 5
    assert out.counts["store-discovery"] > 30


def test_every_node_has_a_claim_and_a_pointer(built):
    """The index is a handle on prose. A node without a claim cannot be triaged and one without a
    pointer cannot be read, so either makes the node useless."""
    _, store = built
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?id WHERE {{ GRAPH ki:index {{
          ?n ki:identifier ?id .
          FILTER (NOT EXISTS {{ ?n ki:claim ?c }} || NOT EXISTS {{ ?n ki:pointer ?p }})
        }} }}""",
    )
    assert not [str(r["id"].value) for r in rows]


def test_every_facet_tag_is_a_value_of_its_scheme(built):
    """An unknown facet value has to be reported rather than stored, because a silently forked
    vocabulary makes every filter unreliable and nothing would say so."""
    out, _ = built
    for scheme in ("Activity", "Quality", "Technology"):
        assert out.counts.get(f"facet:{scheme}", 0) > 0, f"the registers must be tagged with {scheme}"
    assert not [p for p in out.problems if "not a taggable value" in p]


def test_a_group_reaches_every_value_under_it(built):
    """A facet value may sit under several groups, so Java is both a language and a platform, and a
    filter on either group must reach what is tagged java. CAP-72, the Java minting library, is the
    entry a held-out question failed to find."""
    _, store = built
    for group in ("language", "platform"):
        rows = store.query(
            f"""PREFIX ki: <{KI}>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX fct: <https://www.nebularis.org/neuro-semantic/lattice/dev/facets#>
            SELECT DISTINCT ?id WHERE {{
              GRAPH ki:facets {{ ?value skos:broader* fct:{group} }}
              GRAPH ki:index {{ ?n ki:technology ?value ; ki:identifier ?id }}
            }}"""
        )
        assert "CAP-72" in {str(r["id"].value) for r in rows}, group


def test_the_term_summary_holds_only_declared_ontology_terms(built):
    """The T-Box and the facet schemes are loaded into graphs of their own. Without a filter they
    would also appear in the term summary, so a question about a facet value would come back as
    though a module had declared it."""
    _, store = built
    rows = list(
        store.query(
            f"""PREFIX ki: <{KI}>
            SELECT ?term WHERE {{ GRAPH ki:terms {{ ?t ki:identifier ?term }} }}"""
        )
    )
    leaked = [str(r["term"].value) for r in rows if "/dev/" in str(r["term"].value)]
    assert not leaked


def _register(tmp_path, monkeypatch, header: str, row: str) -> extract.Extract:
    """Run register_rows over a one-row register standing in for the mechanism register."""
    (tmp_path / "docs/developer").mkdir(parents=True)
    table = f"{header}\n|{'---|' * (header.count('|') - 1)}\n{row}\n"
    (tmp_path / "docs/developer/mechanisms.md").write_text(table, encoding="utf-8")
    monkeypatch.setattr(extract, "ROOT", tmp_path)
    out = extract.Extract()
    extract.register_rows(out)
    return out


def test_an_unknown_column_header_is_reported(tmp_path, monkeypatch):
    """A misspelled header must fail loudly, not vanish from the index."""
    out = _register(tmp_path, monkeypatch, "| ID | Claim | Audiance |", "| MEC-1 | **A claim.** | published |")
    assert any("'Audiance'" in p for p in out.problems)


def test_an_audience_outside_the_set_is_reported_not_stored(tmp_path, monkeypatch):
    out = _register(tmp_path, monkeypatch, "| ID | Claim | Audience |", "| MEC-1 | **A claim.** | public |")
    assert any("Audience 'public'" in p for p in out.problems)
    assert not [q for q in out.quads if q.predicate.value.endswith("#audience")]


def test_an_owner_that_names_no_catalogue_unit_is_reported_not_minted(tmp_path, monkeypatch):
    out = _register(tmp_path, monkeypatch, "| ID | Claim | Owner |", "| MEC-1 | **A claim.** | nowhere-in-particular |")
    assert any("Owner 'nowhere-in-particular'" in p for p in out.problems)
    assert not [q for q in out.quads if q.predicate.value.endswith("#ownedBy")]


def test_a_capability_is_invoked_and_a_mechanism_is_adopted(built):
    """The class definitions in knowledge.ttl, as checks. A capability has an entry point or a
    pointer into code, and a mechanism never has an entry point."""
    _, store = built
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?id ?pointer WHERE {{ GRAPH ki:index {{
          ?n a ki:Capability ; ki:identifier ?id ; ki:pointer ?pointer .
          FILTER NOT EXISTS {{ ?n ki:entryPoint ?e }}
        }} }}""",
    )
    assert rows, "the capability register must contribute capabilities"
    prose = [str(r["id"].value) for r in rows if str(r["pointer"].value).split(":")[0].endswith(".md")]
    assert not prose, f"capabilities with neither an entry point nor a pointer into code: {prose}"
    mechanisms = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?id WHERE {{ GRAPH ki:index {{ ?n a ki:Mechanism ; ki:identifier ?id ; ki:entryPoint ?e }} }}""",
    )
    assert not [str(r["id"].value) for r in mechanisms]


def test_every_capability_row_is_a_capability_node(built):
    out, _ = built
    assert out.counts["capability"] == len(
        [l for l in (extract.ROOT / "docs/developer/capabilities.md").read_text().splitlines() if l.startswith("| CAP-")]
    )


def test_every_pattern_states_a_cost(built):
    """A technique with no trade-off is a rule, not a pattern. An empty Cost cell is reported here
    rather than filled with a guess."""
    _, store = built
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?id WHERE {{ GRAPH ki:index {{
          ?n a ki:Pattern ; ki:identifier ?id .
          FILTER NOT EXISTS {{ ?n ki:cost ?c }}
        }} }}""",
    )
    assert not [str(r["id"].value) for r in rows], "patterns with no stated cost"


def test_every_evidenced_by_target_exists(built):
    """A declared edge to an identifier that no register defines would point at nothing."""
    _, store = built
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?n ?o WHERE {{ GRAPH ki:index {{
          ?n ki:evidencedBy ?o .
          FILTER NOT EXISTS {{ ?o ki:identifier ?id }}
        }} }}""",
    )
    assert not [(str(r["n"].value), str(r["o"].value)) for r in rows]


def test_exists_reaches_every_register_that_records_what_exists(built):
    """An agent asks one question, "does this already exist", and must not need to know which
    register holds the answer. The query once searched mechanisms alone, so every capability and
    every pattern was invisible to it until tagged, and none were. A pattern is found by its name,
    which is its most findable handle, and a capability by its claim. Reaching MEC-01 from
    "versioning", a word its text never uses, is find's job by meaning, measured in ADR-A134's
    addendum of 2026-10-26 and not testable here without the model."""
    import ask

    _, store = built

    def found(needle: str) -> set[str]:
        rows = store.query(ask.EXISTS, substitutions={ox.Variable("needle"): ox.Literal(needle)})
        return {str(r["name"].value) for r in rows if r["name"] is not None}

    assert "PAT-12" in found("pagination"), "a pattern must be found by its name"
    assert "CAP-22" in found("imports or names"), "a capability must be found by its claim"


def test_every_index_entry_states_its_scope(built):
    """Each entry says who may depend on it and when it applies, so a rule of LATTICE's own test
    harness is never read as a rule for designing a runtime component."""
    _, store = built
    rows = _rows(store, """SELECT ?id WHERE { GRAPH ki:index {
        VALUES ?k { ki:Mechanism ki:Capability ki:Pattern ki:Principle ki:Standard }
        ?s a ?k ; ki:identifier ?id .
        FILTER (NOT EXISTS { ?s ki:audience ?a } || NOT EXISTS { ?s ki:phase ?p }) } }""")
    assert not [str(r["id"].value) for r in rows]

def test_a_principle_is_found_by_a_word_in_its_claim(built):
    import ask

    _, store = built
    rows = list(store.query(ask.EXISTS, substitutions={ox.Variable("needle"): ox.Literal("Undetermined")}))
    assert any(str(r["where"].value) == "principle" for r in rows)


def test_every_table_in_a_register_is_a_data_table():
    """A register shows its structure with metadata, not with words: a column's meaning is the
    rdfs:comment of the T-Box property it maps to, written once. A register that explains its own
    columns does so in a second table, whose first column is not an identifier, so that is what
    fails. The first register written carried one, and every later register would have repeated it."""
    registers = {
        path
        for family in identifiers.FAMILIES
        if family.definition == "table-row"
        for pattern in family.defines
        for path in identifiers.ROOT.glob(pattern)
    }
    assert len(registers) >= 6
    offenders = []
    for path in sorted(registers):
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, (line, below) in enumerate(zip(lines, lines[1:]), 1):
            if line.startswith("|") and extract.SEPARATOR_RE.match(below.strip()):
                first = line.strip().strip("|").split("|")[0].strip()
                if first not in {"ID", "#"}:
                    offenders.append(f"{path.relative_to(identifiers.ROOT)}:{number} starts with {first!r}")
    assert not offenders, offenders


def test_a_range_follows_an_edit(tmp_path):
    """The maintainer's requirement: when a document changes, a rebuild picks up the new range. A
    pointer names an anchor, so inserting lines above a section moves its range by exactly that
    many, and renaming the heading is reported and never answered with a guessed range."""
    import anchors

    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\n## Alpha\na\n\n## Beta\nb1\nb2\n", encoding="utf-8")
    assert anchors.resolve_part(tmp_path, "doc.md#beta") == "doc.md:6-8"
    doc.write_text("new\nlines\nabove\n" + doc.read_text(encoding="utf-8"), encoding="utf-8")
    assert anchors.resolve_part(tmp_path, "doc.md#beta") == "doc.md:9-11"
    doc.write_text(doc.read_text(encoding="utf-8").replace("## Beta", "## Gamma"), encoding="utf-8")
    ranges, problems = anchors.resolve(tmp_path, "doc.md#beta")
    assert not ranges and problems and "no heading" in problems[0]


def test_a_repeated_heading_is_suffixed_as_github_does(tmp_path):
    import anchors

    (tmp_path / "doc.md").write_text("## Same\nx\n## Same\ny\n```\n# not a heading\n```\n", encoding="utf-8")
    assert anchors.resolve_part(tmp_path, "doc.md#same") == "doc.md:1-2"
    assert anchors.resolve_part(tmp_path, "doc.md#same-1") == "doc.md:3-7"


def test_a_line_number_is_refused_as_a_pointer(tmp_path):
    import anchors

    (tmp_path / "doc.md").write_text("# T\n", encoding="utf-8")
    _, problems = anchors.resolve(tmp_path, "doc.md:1-3")
    assert problems and "line number" in problems[0]


def test_a_python_definition_resolves_to_its_ast_span(tmp_path):
    import anchors

    (tmp_path / "m.py").write_text('"""Doc."""\n\n\ndef f():\n    return 1\n\n\nclass C:\n    x = 1\n', encoding="utf-8")
    assert anchors.resolve_part(tmp_path, "m.py::f") == "m.py:4-5"
    assert anchors.resolve_part(tmp_path, "m.py::C") == "m.py:8-9"
    assert anchors.resolve_part(tmp_path, "m.py::__doc__") == "m.py:1-1"
    _, problems = anchors.resolve(tmp_path, "m.py::gone")
    assert problems


def test_a_toml_table_resolves_to_its_span(tmp_path):
    import anchors

    (tmp_path / "t.toml").write_text('[tasks."a:b"]\nrun = "x"\n\n[tasks.c]\nrun = "y"\n', encoding="utf-8")
    assert anchors.resolve_part(tmp_path, "t.toml::a:b") == "t.toml:1-3"
    assert anchors.resolve_part(tmp_path, "t.toml::c") == "t.toml:4-5"


def test_the_slug_rule_matches_every_link_the_guides_already_use():
    """The anchors mirror GitHub's, so the repository's own in-page links are the oracle."""
    import re
    import anchors

    for rel in ("docs/architecture/rdf-sparql-patterns-guide.md", "docs/architecture/triple-store-discovery.md"):
        text = (extract.ROOT / rel).read_text(encoding="utf-8")
        slugs = {s for _, _, s in anchors.headings(text.splitlines())}
        missing = sorted(l for l in set(re.findall(r"\]\(#([^)\s]+)\)", text)) if l not in slugs)
        assert not missing, (rel, missing[:5])


def test_every_authored_pointer_resolves_against_the_real_corpus(built):
    out, store = built
    assert not [p for p in out.problems if "has Pointer" in p], [p for p in out.problems if "has Pointer" in p][:5]
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?id ?pointer WHERE {{ GRAPH ki:index {{ ?n ki:identifier ?id ; ki:pointer ?pointer }} }}""",
    )
    bad = [
        str(r["id"].value)
        for r in rows
        for part in str(r["pointer"].value).split(",")
        if not re.fullmatch(r".+:\d+-\d+", part)
    ]
    assert not bad, bad[:5]


def test_read_returns_the_bounded_text_of_a_pointer(built):
    import ask

    _, store = built
    pieces = ask.read_ranges(store, "MEC-01")
    assert pieces and all(text.strip() for _, text in pieces)
    path = pieces[0][0].removeprefix("row ").rsplit(":", 1)[0]
    whole = (extract.ROOT / path).read_text(encoding="utf-8").count("\n")
    assert sum(text.count("\n") + 1 for _, text in pieces) < whole


@pytest.mark.parametrize("identifier", ["CAP-64", "STD-153"])
def test_read_prints_the_register_row_before_what_its_pointer_names(built, identifier):
    import ask

    _, store = built
    pieces = ask.read_ranges(store, identifier)
    where, text = pieces[0]
    assert where.startswith("row docs/developer/") and text.startswith(f"| {identifier} |")
    assert len(pieces) > 1 and all(w.startswith("pointed-at ") for w, _ in pieces[1:])


def test_a_query_rebuilds_an_index_older_than_the_files_it_reads(tmp_path, monkeypatch):
    """The maintainer's requirement: when a document changes, the index must pick up the new line
    range. A rebuild resolves every anchor afresh, but nothing made one happen, so an agent that
    edited a document and asked again got the lines the document used to hold. Every query now
    checks whether any tracked file is newer than the build, driven here through the stamp so no
    tracked file is touched."""
    import ask

    store = tmp_path / "store"
    store.mkdir()
    stamp = tmp_path / "built-from"
    monkeypatch.setattr(ask, "STORE_PATH", store)
    monkeypatch.setattr(extract, "STAMP_PATH", stamp)

    assert ask.stale(), "a store with no stamp has to be rebuilt"
    stamp.write_text("0\n", encoding="utf-8")
    assert ask.stale(), "a build older than every tracked file is stale"
    stamp.write_text(f"{time.time() + 3600}\n", encoding="utf-8")
    assert not ask.stale(), "a build newer than every tracked file is current"


def _rows(store, query):
    return list(store.query(f"PREFIX ki: <{KI}>\n" + query))


def test_every_standard_has_a_stratum(built):
    _, store = built
    rows = _rows(store, "SELECT ?id WHERE { GRAPH ki:index { ?s a ki:Standard ; ki:identifier ?id "
                        "FILTER NOT EXISTS { ?s ki:stratum ?x } } }")
    assert not [str(r["id"].value) for r in rows]


def test_a_standard_refines_only_one_at_its_own_level_or_above(built):
    """A narrow rule must not be made to govern a broad one. Refinement runs from convention and
    practice up towards design and architecture, never down, and so can never form a cycle."""
    _, store = built
    rows = _rows(store, """SELECT ?a ?b WHERE {
        GRAPH ki:index { ?s ki:refines ?t ; ki:stratum ?ls ; ki:identifier ?a .
                         ?t ki:stratum ?lt ; ki:identifier ?b . }
        GRAPH ki:tbox { ?ls ki:level ?x . ?lt ki:level ?y . }
        FILTER (?y > ?x) }""")
    assert not [(str(r["a"].value), str(r["b"].value)) for r in rows]


def test_enforcement_names_a_capability(built):
    """A standard is enforced by a check the index holds, never by a review, which is not a check."""
    _, store = built
    rows = _rows(store, "SELECT ?id WHERE { GRAPH ki:index { ?s ki:enforcedBy ?c ; ki:identifier ?id "
                        "FILTER NOT EXISTS { ?c a ki:Capability } } }")
    assert not [str(r["id"].value) for r in rows]


def test_an_extrapolated_standard_rests_on_something(built):
    """A standard an agent extrapolated was found written nowhere, so it must name what it was
    extrapolated from: a principle it serves, a decision, or a discovery. Otherwise it is an opinion
    with an identifier."""
    _, store = built
    rows = _rows(store, """SELECT ?id WHERE { GRAPH ki:index {
        ?s ki:origin ki:Extrapolated ; ki:identifier ?id .
        FILTER NOT EXISTS { ?s ki:supports|ki:decidedBy|ki:evidencedBy ?g } } }""")
    assert not [str(r["id"].value) for r in rows]


def test_the_enforcement_gap_is_one_query(built):
    """The governance question no skill can answer: which standards does nothing check."""
    _, store = built
    def count(where: str) -> int:
        return int(_rows(store, f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ GRAPH ki:index {{ "
                                f"?s a ki:Standard {where} }} }}")[0]["n"].value)

    enforced = count(". ?s ki:enforcedBy ?c")
    unenforced = count("FILTER NOT EXISTS { ?s ki:enforcedBy ?c }")
    # Both halves, because each alone passes vacuously: a register whose enforcement edges were all
    # lost still has standards nothing enforces, and one with every edge still has a capability.
    assert enforced > 0, "no standard is enforced, so the enforcement column was not read"
    assert unenforced > 0
    assert enforced + unenforced == count("")


def test_the_release_is_one_data_quantum(built):
    """The release holds exactly the substrate's data quantum. MORK, Persistence, SPC and Surface shared
    it until ADR-A129's addendum of 2026-10-26, coupled to the substrate by nothing but the number. A
    module that newly joins the release without being coupled to the substrate fails here."""
    out, store = built
    substrate = {
        str(r["p"].value) for r in _rows(store, """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?p WHERE { GRAPH ki:index { ?q ki:identifier "data/substrate" ; ki:includes ?m . ?m rdfs:label ?p } }""")
    }
    catalogue = lattice_repo_catalogue.load(identifiers.ROOT)
    assert substrate == {m.name for m in catalogue.modules.values() if m.kind == "substrate"}
    assert {m.name for m in catalogue.release_members()} == substrate


def test_a_broker_does_not_separate_the_authoring_service_from_its_worker(built):
    """The finding the software view exists to make: in the authoring deployment the service and the
    worker talk through RabbitMQ and share Fuseki, so they are one quantum."""
    _, store = built
    rows = _rows(store, """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?id WHERE { GRAPH ki:index { ?q ki:deployment "compose/authoring" ; ki:identifier ?id ;
        ki:includes ?a , ?b . ?a rdfs:label "authoring-service" . ?b rdfs:label "authoring-worker" } }""")
    assert len(rows) == 1


def test_a_governed_quantum_exists(built):
    _, store = built
    rows = _rows(store, "SELECT ?id ?q WHERE { GRAPH ki:index { ?s ki:governs ?q ; ki:identifier ?id "
                        "FILTER NOT EXISTS { ?q a ki:Quantum } } }")
    assert not [(str(r["id"].value), str(r["q"].value)) for r in rows]


def test_every_architectural_and_design_standard_names_its_check_or_why_it_has_none(built):
    """STD-002: a standard nobody can tell is broken holds only while every reader remembers it. A
    standard with a check does not also say why it has none."""
    _, store = built
    rows = _rows(store, """SELECT ?id WHERE { GRAPH ki:index {
        ?s a ki:Standard ; ki:identifier ?id ; ki:stratum ?l .
        FILTER (?l IN (ki:ArchitecturalStratum, ki:DesignStratum))
        FILTER (NOT EXISTS { ?s ki:enforcedBy ?c } && NOT EXISTS { ?s ki:uncheckedBecause ?r }) } }""")
    assert not [str(r["id"].value) for r in rows]
    both = _rows(store, "SELECT ?id WHERE { GRAPH ki:index { ?s ki:enforcedBy ?c ; ki:uncheckedBecause ?r ; ki:identifier ?id } }")
    assert not [str(r["id"].value) for r in both]


def test_every_enforcing_check_is_classified_as_a_fitness_function(built):
    """So the absence of a holistic or a continual check is a query, not an impression."""
    _, store = built
    rows = _rows(store, """SELECT DISTINCT ?id WHERE { GRAPH ki:index { ?s ki:enforcedBy ?c . ?c ki:identifier ?id
        FILTER (NOT EXISTS { ?c ki:fitnessScope ?f } || NOT EXISTS { ?c ki:cadence ?k }) } }""")
    assert not [str(r["id"].value) for r in rows]


def test_the_store_stays_within_a_default_open_file_limit(built):
    """TSD-39: one bulk load per document left over a thousand SST files, which compaction did not
    merge, so a build or a read-only open exceeded macOS's default limit of 256 open files. It passed
    in an agent's shell, whose limit was a million, and failed in the maintainer's terminal."""
    out, _ = built
    files = list(out.store_path.glob("*.sst"))
    assert len(files) <= 32, f"{len(files)} SST files: the store has fragmented again"


def test_a_facet_value_matches_up_and_down_its_chain_but_not_its_siblings(built):
    """A question about physical data modelling must raise an entry tagged with the broader data
    modelling, and the reverse, so tags written before the scheme grew still count. A sibling under
    the same group must not, or naming any design activity would raise every design entry."""
    import ask

    _, store = built
    values = ask.facet_values(store)["Activity"]
    assert {"data-modelling", "design"} <= values["physical-data-modelling"]
    assert "physical-data-modelling" in values["data-modelling"]
    assert "ux-design" not in values["physical-data-modelling"]


def test_a_related_value_raises_entries_in_another_facet(built):
    """UX design is an activity and accessibility a quality, linked by skos:related through the
    interaction-capability group. Naming the activity must raise entries tagged with the quality,
    while a value with no relation adds nothing to another facet."""
    import ask

    _, store = built
    wanted = ask.expand(store, {"Activity": ["ux-design"]})
    assert "accessibility" in wanted["qualities"] and "ux-design" in wanted["activities"]
    assert set(ask.expand(store, {"Activity": ["refactoring"]})) == {"activities"}
    # Two siblings a tagger confuses are related, so naming either raises entries tagged with the
    # other: the persistence patterns tagged physical data modelling for a solution-design question,
    # and the test-speed standards tagged efficiency for a performance-tuning one.
    assert "physical-data-modelling" in ask.expand(store, {"Activity": ["solution-design"]})["activities"]
    assert "efficiency" in ask.expand(store, {"Activity": ["performance-tuning"]})["qualities"]


def test_a_store_finding_takes_its_technology_from_its_evidence(built):
    """TSD-23's Evidence line names pySHACL, so it carries pySHACL without anyone authoring it.
    TSD-07's says "both stores", which the record's Stores covered line names as rdflib and
    Oxigraph."""
    _, store = built
    rows = _rows(store, """SELECT ?id ?t WHERE { GRAPH ki:index {
        ?n ki:identifier ?id ; ki:technology ?t . FILTER (?id IN ("TSD-23", "TSD-07")) } }""")
    found = {(str(r["id"].value), str(r["t"].value).rsplit("#", 1)[1]) for r in rows}
    assert ("TSD-23", "pyshacl") in found
    assert {("TSD-07", "rdflib"), ("TSD-07", "oxigraph")} <= found


def test_a_decision_is_claimed_by_what_it_decides_not_its_title():
    """A title such as "Provenance Model" says too little for a question phrased as the problem, so
    the claim is the Decision section's own words. A bold lead that is a whole sentence stands alone,
    a lead-in such as "Rules:" does not, a table's rows are read without its header, and code is not
    read at all."""
    lead = ["# ADR-A1: X", "## Decision", "", "**1. We keep one release number for the substrate layers.** More text."]
    assert extract.decision_claim(lead) == "1. We keep one release number for the substrate layers."
    table = ["## Decision", "", "```", "Principal { subject }", "```", "**Rules:**", "",
             "| Tier | Contract |", "|---|---|", "| **Core** | Every adapter implements it. |", "## Consequences", "later"]
    claim = extract.decision_claim(table)
    assert claim.startswith("Rules: Core, Every adapter implements it.")
    assert "Tier" not in claim and "Principal" not in claim and "later" not in claim
    assert extract.decision_claim(["# ADR-A1: X", "## Context", "text"]) is None
