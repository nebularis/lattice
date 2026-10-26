# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The embedding cache and find's filtering, ranking and fallback, with a stand-in model.

The real model is 130 MB and fetched from the network, so these tests never load it. They check what
this repository's code decides: what is re-embedded, what a stale or missing set of vectors does, and
which entries find offers in what order and with what advice.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pyoxigraph as ox
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ask  # noqa: E402
import embed  # noqa: E402

KI = embed.KI
FCT = "https://www.nebularis.org/neuro-semantic/lattice/dev/facets#"
INDEX = ox.NamedNode(KI + "index")
RDFS_LABEL = ox.NamedNode("http://www.w3.org/2000/01/rdf-schema#label")
RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")


def entry(store: ox.Store, ident: str, kind: str, claim: str, phase: str | None = None, activity: str | None = None) -> None:
    n = ox.NamedNode(KI + "node/" + ident.replace("-", ""))
    quads = [
        (n, ox.NamedNode(KI + "identifier"), ox.Literal(ident)),
        (n, ox.NamedNode(KI + "claim"), ox.Literal(claim)),
        (n, RDF_TYPE, ox.NamedNode(KI + kind)),
        (n, RDFS_LABEL, ox.Literal(ident.lower())),
    ]
    if phase:
        quads.append((n, ox.NamedNode(KI + "phase"), ox.NamedNode(KI + phase)))
    if activity:
        quads.append((n, ox.NamedNode(KI + "activity"), ox.NamedNode(FCT + activity)))
    store.extend([ox.Quad(s, p, o, INDEX) for s, p, o in quads])


class Words:
    """A stand-in model: a text's vector counts four words, so closeness is checkable by eye."""

    calls: list[int] = []
    AXES = ("ledger", "minting", "slow", "graph")

    def __init__(self) -> None:
        pass

    def embed(self, texts: list[str]) -> np.ndarray:
        Words.calls.append(len(texts))
        v = np.array([[t.lower().count(a) + 0.01 for a in self.AXES] for t in texts], dtype=np.float32)
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    def question(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


@pytest.fixture
def words(monkeypatch):
    Words.calls = []
    monkeypatch.setattr(embed, "Model", Words)
    return Words


def test_a_rebuild_embeds_only_changed_text(tmp_path, words):
    store = ox.Store()
    entry(store, "MEC-1", "Mechanism", "a ledger account")
    entry(store, "CAP-1", "Capability", "minting in Java")
    assert embed.build(store, tmp_path) == 2
    assert embed.build(store, tmp_path) == 0
    store.remove(next(iter(store.quads_for_pattern(None, ox.NamedNode(KI + "claim"), ox.Literal("a ledger account"), INDEX))))
    store.add(ox.Quad(ox.NamedNode(KI + "node/MEC1"), ox.NamedNode(KI + "claim"), ox.Literal("a ledger posting"), INDEX))
    assert embed.build(store, tmp_path) == 1
    nodes, vectors = embed.load(tmp_path)
    assert len(nodes) == 2 and vectors.shape == (2, 4)


def test_vectors_from_another_revision_are_refused_and_rebuilt(tmp_path, words, monkeypatch):
    store = ox.Store()
    entry(store, "MEC-1", "Mechanism", "a ledger account")
    embed.build(store, tmp_path)
    monkeypatch.setattr(embed, "REVISION", "another")
    with pytest.raises(embed.Unavailable, match="another model revision"):
        embed.load(tmp_path)
    assert embed.build(store, tmp_path) == 1


def test_an_unavailable_model_leaves_no_stale_vectors(tmp_path, words, monkeypatch):
    store = ox.Store()
    entry(store, "MEC-1", "Mechanism", "a ledger account")
    embed.build(store, tmp_path)
    entry(store, "CAP-1", "Capability", "minting in Java")

    def unavailable():
        raise embed.Unavailable("no network")

    monkeypatch.setattr(embed, "Model", unavailable)
    with pytest.raises(embed.Unavailable):
        embed.build(store, tmp_path)
    assert not (tmp_path / embed.VECTORS).exists()


@pytest.fixture
def index(tmp_path, words, monkeypatch):
    store = ox.Store()
    entry(store, "MEC-1", "Mechanism", "a ledger account consumed and restored", "Runtime")
    entry(store, "CAP-1", "Capability", "minting in Java", "Runtime")
    entry(store, "STD-1", "Standard", "slow slow tests", "Development")
    embed.build(store, tmp_path)
    monkeypatch.setattr(ask, "STORE_PATH", tmp_path / "store")
    monkeypatch.setattr(ask, "log_miss", lambda question: None)
    return store


def test_find_ranks_by_meaning_and_filters_exactly(index, capsys):
    ask.find(index, "a ledger", set(), set(), set(), 8)
    lines = capsys.readouterr().out.splitlines()
    assert lines[2].split()[1] == "MEC-1"
    ask.find(index, "a ledger", {"Capability", "Standard"}, set(), set(), 8)
    out = capsys.readouterr().out
    assert "MEC-1" not in out and "CAP-1" in out
    ask.find(index, "slow", set(), {"Runtime"}, set(), 8)
    assert "STD-1" not in capsys.readouterr().out


def test_find_falls_back_when_nothing_is_close(index, capsys):
    ask.find(index, "graph", set(), set(), set(), 8)
    out = capsys.readouterr().out
    assert "weak match" in out and "Fall back to reading the documents" in out and "STD-272" in out


def test_find_falls_back_when_no_entry_has_the_facets(index, capsys):
    ask.find(index, "a ledger", {"Debt"}, set(), set(), 8)
    out = capsys.readouterr().out
    assert "no entry has the facets" in out and "Fall back to reading the documents" in out


def test_find_falls_back_when_there_are_no_vectors(index, tmp_path, capsys):
    (tmp_path / embed.VECTORS).unlink()
    ask.find(index, "a ledger", set(), set(), set(), 8)
    out = capsys.readouterr().out
    assert "find cannot rank here" in out and "Fall back to reading the documents" in out


def test_a_matching_facet_raises_an_entry_and_a_mismatch_hides_none(tmp_path, words, monkeypatch, capsys):
    """Activity is a judgement two taggers can disagree on, so it boosts and never filters. PAT-1
    trails MEC-1 by about 0.01 in meaning, less than one boost, so naming its activity puts it first,
    and MEC-1 is still listed."""
    store = ox.Store()
    entry(store, "MEC-1", "Mechanism", "ledger", activity="ontology-design")
    entry(store, "PAT-1", "Pattern", "ledger " * 7 + "minting", activity="solution-design")
    embed.build(store, tmp_path)
    monkeypatch.setattr(ask, "STORE_PATH", tmp_path / "store")
    monkeypatch.setattr(ask, "log_miss", lambda question: None)
    ask.find(store, "ledger", set(), set(), set(), 8)
    assert capsys.readouterr().out.splitlines()[2].split()[1] == "MEC-1"
    ask.find(store, "ledger", set(), set(), set(), 8, {"activities": {"solution-design"}})
    out = capsys.readouterr().out.splitlines()
    assert out[2].split()[1] == "PAT-1" and out[2].split()[0].endswith("+")
    assert any(line.split()[1:2] == ["MEC-1"] for line in out[2:4]), "a mismatched activity must not hide an entry"


def test_misses_lists_each_question_once_newest_first(tmp_path, monkeypatch, capsys):
    """The miss log is read at a handoff to decide what the index lacks, so a question asked three
    times is one row with its count, and the newest gap comes first."""
    log = tmp_path / "misses.log"
    log.write_text("2026-10-24T09:00:00+00:00\tfind a\n2026-10-26T09:00:00+00:00\tfind b\n"
                   "2026-10-25T09:00:00+00:00\tfind a\n2026-10-25T10:00:00+00:00\tfind a\n", encoding="utf-8")
    monkeypatch.setattr(ask, "MISS_LOG", log)
    monkeypatch.setattr(ask, "ROOT", tmp_path)
    ask.misses(20)
    lines = capsys.readouterr().out.splitlines()
    assert lines[2].split() == ["2026-10-26", "1", "find", "b"]
    assert lines[3].split() == ["2026-10-25", "3", "find", "a"]
    assert "2 distinct question(s)" in lines[-1]
