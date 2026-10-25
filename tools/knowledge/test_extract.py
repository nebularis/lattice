# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Tests for the knowledge index extractor, over the real corpus.

The index is derived, so these tests are about whether the derivation tells the truth: that every
node it claims to have found exists, that a fact it could not read is reported rather than guessed,
and that one unreadable document does not take the corpus with it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyoxigraph as ox
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import extract  # noqa: E402
import identifiers  # noqa: E402

KI = extract.KI


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> tuple[extract.Extract, ox.Store]:
    """Build the index once, into a temporary store rather than the one in .build."""
    path = tmp_path_factory.mktemp("knowledge") / "store"
    out = extract.build(path)
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


def test_a_decision_with_no_readable_status_is_reported_not_guessed(built):
    """Seven decisions carry their status as a `## Status` section rather than a header field. A
    node with no status is invisible to every check that compares one, so the extractor says so
    rather than inventing a default."""
    out, _ = built
    assert out.counts.get("decision-without-status", 0) > 0
    assert sum("no **Status:** header field" in p for p in out.problems) == out.counts[
        "decision-without-status"
    ]


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


def test_an_unparseable_document_is_reported_and_loses_only_itself(built):
    """TSD-37: one tracked fixture holds IRIs with two fragment separators, which Oxigraph refuses.
    A single batch load would lose all 270 documents to it, so the load is per document."""
    out, _ = built
    assert out.counts.get("ontology-document-failed", 0) == 1
    assert out.counts["ontology-document"] > 250
    assert any("does not parse" in p for p in out.problems)


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


def test_a_tag_outside_the_scheme_is_refused(built):
    """ADR-A134 decision 9. An unknown tag has to fail rather than be stored, because a silently
    forked vocabulary makes every recall query unreliable and nothing would say so."""
    out, _ = built
    assert out.counts.get("tagged", 0) > 0, "the worked examples must be tagged"
    assert not [p for p in out.problems if "not a concept of the design-shape scheme" in p]


def test_the_gerund_reaches_the_noun(built):
    """The whole design, in one assertion. An agent asking about "versioning" must reach MEC-01,
    Foundation's versioning, although MEC-01's own text never uses that word and the model's term
    is the noun `fnd:Version`. Measured in sketch §9.1 and §9.2: a term lookup fails, the author's
    free-text problem shape fails, and a declared synonym on a tagged concept succeeds. If this
    breaks, the index has stopped doing the one thing it exists for."""
    _, store = built
    rows = list(
        store.query(
            f"""PREFIX ki: <{KI}>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT DISTINCT ?id WHERE {{
              GRAPH ki:shapes {{
                ?c a skos:Concept ; skos:altLabel ?alt .
                FILTER (LCASE(STR(?alt)) = "versioning")
                ?under skos:broader* ?c .
              }}
              GRAPH ki:index {{ ?n ki:tagged ?under ; ki:identifier ?id . }}
            }}"""
        )
    )
    assert "MEC-01" in {str(r["id"].value) for r in rows}


def test_the_term_summary_holds_only_declared_ontology_terms(built):
    """The T-Box and the design-shape scheme are loaded into graphs of their own. Without a filter
    they also appeared in the term summary, so a question about a design shape came back as though
    a module had declared it."""
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
    (tmp_path / "docs/developer/plans").mkdir(parents=True)
    table = f"{header}\n|{'---|' * (header.count('|') - 1)}\n{row}\n"
    (tmp_path / "docs/developer/plans/mechanisms.md").write_text(table, encoding="utf-8")
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
