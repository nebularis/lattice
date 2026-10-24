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
