# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What find and read show beside an answer, and what the ask log keeps (ADR-A134 decisions 28 to 32).

The index returns the right entry and lost what sits at its edge: the case it does not cover, the
entry it is confused with, the addendum that reversed it, the debt recorded against it. These tests
build small stores with a stand-in model and check that each of those reaches the reader in the
output a question already prints, and that every question leaves a line in the log.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyoxigraph as ox
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ask  # noqa: E402
import embed  # noqa: E402
from test_embed import INDEX, KI, Words, entry, section, table  # noqa: E402

TERMS = ox.NamedNode(KI + "terms")


def fact(store: ox.Store, ident: str, prop: str, value) -> None:
    obj = value if isinstance(value, ox.NamedNode) else ox.Literal(value)
    store.add(ox.Quad(ox.NamedNode(KI + "node/" + ident.replace("-", "")), ox.NamedNode(KI + prop), obj, INDEX))


def at(ident: str) -> ox.NamedNode:
    return ox.NamedNode(KI + "node/" + ident.replace("-", ""))


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """A stand-in model, and the store path and both logs in a temporary directory."""
    Words.calls = []
    monkeypatch.setattr(embed, "Model", Words)
    monkeypatch.setattr(ask, "STORE_PATH", tmp_path / "store")
    monkeypatch.setattr(ask, "ASK_LOG", tmp_path / "asks.log")
    monkeypatch.setattr(ask, "MISS_LOG", tmp_path / "misses.log")
    return tmp_path


def under_row(out: str, ident: str) -> str:
    """The indented line find prints under the row of ``ident``."""
    lines = out.splitlines()
    i = next(n for n, line in enumerate(lines) if not line.startswith(" ") and line.split()[1:2] == [ident])
    return lines[i + 1].strip()


def test_find_prints_the_whole_claim_under_each_row(isolated, capsys):
    """The table cuts a claim at 90 characters, and a qualification is usually written after that."""
    store = ox.Store()
    claim = "A ledger amount is never restored within a period, " + "except by the reinstatement credit the terms state. " * 2
    entry(store, "STD-1", "Standard", claim)
    embed.build(store, isolated)
    ask.find(store, "ledger", set(), set(), set(), 8)
    out = capsys.readouterr().out
    assert len(claim) > 90 and claim.strip() in under_row(out, "STD-1")


def test_flags_mark_a_boundary_a_debt_and_a_proposed_entry(isolated, capsys):
    """! says the entry states a case it does not cover, TD that an open debt bears on it, and ? that
    it is Proposed. The line under the row says what each is, and a legend names the marks shown."""
    store = ox.Store()
    entry(store, "MEC-1", "Mechanism", "a ledger account per key")
    fact(store, "MEC-1", "doesNotCover", "a keyed child under a keyed parent")
    fact(store, "MEC-1", "status", ox.NamedNode(KI + "Proposed"))
    entry(store, "TD-1", "Debt", "minting minting")
    fact(store, "TD-1", "status", ox.NamedNode(KI + "Open"))
    fact(store, "TD-1", "bearsOn", at("MEC-1"))
    embed.build(store, isolated)
    ask.find(store, "ledger", {"Mechanism"}, set(), set(), 8)
    out = capsys.readouterr().out
    row = table(out)[0]
    assert row[1] == "MEC-1" and row[4] == "!TD?"
    line = under_row(out, "MEC-1")
    assert "Does not cover: a keyed child under a keyed parent." in line and "Open debt: TD-1." in line
    assert "! the entry states a case it does not cover" in out and "TD an open debt" in out and "? the entry is Proposed" in out


def test_an_open_backlog_idea_flags_the_entry_it_bears_on(isolated, capsys):
    """BL says an unbuilt idea on the backlog bears on the entry, and the line under the row names it."""
    store = ox.Store()
    entry(store, "CAP-1", "Capability", "compile a mapping to RML")
    entry(store, "BL-1", "Backlog", "compile a mapping to XSLT")
    fact(store, "BL-1", "status", ox.NamedNode(KI + "Open"))
    fact(store, "BL-1", "bearsOn", at("CAP-1"))
    embed.build(store, isolated)
    ask.find(store, "mapping", {"Capability"}, set(), set(), 8)
    out = capsys.readouterr().out
    assert table(out)[0][4] == "BL" and "On the backlog, not built: BL-1." in under_row(out, "CAP-1")


def test_a_closed_debt_does_not_flag_its_entry(isolated, capsys):
    store = ox.Store()
    entry(store, "MEC-1", "Mechanism", "a ledger account")
    entry(store, "TD-1", "Debt", "minting")
    fact(store, "TD-1", "status", ox.NamedNode(KI + "Accepted"))
    fact(store, "TD-1", "bearsOn", at("MEC-1"))
    embed.build(store, isolated)
    ask.find(store, "ledger", {"Mechanism"}, set(), set(), 8)
    assert "TD" not in table(capsys.readouterr().out)[0][4:5]


def test_a_superseded_decision_is_kept_marked_and_ranked_below_its_successor(isolated, capsys):
    """Equal in meaning, the superseded decision loses SUPERSEDED and so follows its successor. It
    is still shown, since a question may be about the history, and names the decision that replaced it."""
    store = ox.Store()
    entry(store, "ADR-1", "Decision", "a ledger account")
    fact(store, "ADR-1", "status", ox.NamedNode(KI + "Superseded"))
    fact(store, "ADR-1", "supersededBy", at("ADR-2"))
    entry(store, "ADR-2", "Decision", "a ledger account")
    embed.build(store, isolated)
    ask.find(store, "a ledger account", set(), set(), set(), 8)
    out = capsys.readouterr().out
    rows = table(out)
    assert [r[1] for r in rows] == ["ADR-2", "ADR-1"]
    assert rows[1][4] == "~" and "Superseded by ADR-2." in under_row(out, "ADR-1")
    assert abs(float(rows[0][0]) - float(rows[1][0]) - ask.SUPERSEDED) < 0.011


def test_a_reversed_section_is_marked_and_names_the_addendum(isolated, capsys):
    """When the section that answered was reversed by an addendum, the row keeps its rank, is marked
    ~, and the line under it names the addendum's lines, so the reader lands on the live text."""
    store = ox.Store()
    entry(store, "ADR-1", "Decision", "a ledger account")
    section(store, "ADR-1", 1, "minting minting slow", "adr.md:10-12")
    section(store, "ADR-1", 2, "graph graph", "adr.md:40-60")
    reversed_, addendum = (ox.NamedNode(f"{KI}node/ADR1/section-{n}") for n in (1, 2))
    store.add(ox.Quad(reversed_, ox.NamedNode(KI + "supersededBy"), addendum, INDEX))
    embed.build(store, isolated)
    ask.find(store, "minting slow", set(), set(), set(), 8)
    out = capsys.readouterr().out
    row = table(out)[0]
    assert row[1] == "ADR-1" and row[4] == "~" and row[-1] == "adr.md:10-12"
    line = under_row(out, "ADR-1")
    assert "Reversed by adr.md:40-60." in line and "The section that answered: minting minting slow" in line


def test_declared_terms_are_searched_only_when_their_kind_is_named(isolated, capsys):
    """Terms crowded the entries out of questions about a design, so a question without --kind term
    never sees one. Named alone, the kind finds only terms, named with another it ranks both, and a
    phase or audience filter hides terms, which state neither (ADR-A134 decision 31)."""
    store = ox.Store()
    entry(store, "MEC-1", "Mechanism", "a ledger account", phase="Runtime")
    t = ox.NamedNode(KI + "term/ledger.keyDimension")
    store.extend([
        ox.Quad(t, ox.NamedNode(KI + "identifier"), ox.Literal("https://example.org/ledger#keyDimension"), TERMS),
        ox.Quad(t, ox.NamedNode(KI + "claim"), ox.Literal("key dimension. ledger ledger per key. functional"), TERMS),
        ox.Quad(t, ox.NamedNode(KI + "pointer"), ox.Literal("ledger.ttl:9"), TERMS),
        ox.Quad(t, ox.NamedNode(KI + "ownedBy"), ox.NamedNode(KI + "module/ledger"), TERMS),
    ])
    assert embed.build(store, isolated) == 2, "the term is embedded beside the entry"
    ask.find(store, "ledger", set(), set(), set(), 8)
    out = capsys.readouterr().out
    assert [r[1] for r in table(out)] == ["MEC-1"] and "module" not in out.splitlines()[0]
    ask.find(store, "ledger", {"Term"}, set(), set(), 8)
    out = capsys.readouterr().out
    assert out.splitlines()[0].split()[:5] == ["score", "id", "kind", "module", "flags"], "a term has a module and no status"
    assert [r[1:4] for r in table(out)] == [["keyDimension", "Term", "ledger"]]
    ask.find(store, "ledger", {"Term", "Mechanism"}, set(), set(), 8)
    assert sorted(r[1] for r in table(capsys.readouterr().out)) == ["MEC-1", "keyDimension"]
    ask.find(store, "ledger", {"Term", "Mechanism"}, {"Runtime"}, set(), 8)
    assert [r[1] for r in table(capsys.readouterr().out)] == ["MEC-1"]


def test_a_weak_answer_points_at_the_terms(isolated, capsys):
    store = ox.Store()
    entry(store, "MEC-1", "Mechanism", "a ledger account")
    embed.build(store, isolated)
    ask.find(store, "graph", set(), set(), set(), 8)
    assert "ask again\nwith --kind term" in capsys.readouterr().out


def test_the_case_an_entry_does_not_cover_is_embedded_with_it():
    """So a question about the uncovered case still finds the entry, which is then flagged."""
    row = {k: (ox.Literal(v) if v else None) for k, v in
           {"label": "keyed accounts", "claim": "One account per key.", "shape": None, "uncovered": "a keyed child under a keyed parent"}.items()}
    assert embed.text_of(row) == "keyed accounts. One account per key.. a keyed child under a keyed parent"


def neighbourhood(tmp_path: Path) -> ox.Store:
    store = ox.Store()
    entry(store, "STD-1", "Standard", "a period's amount is never restored")
    fact(store, "STD-1", "problemShape", "restoring an amount drawn in a period")
    fact(store, "STD-1", "doesNotCover", "the reinstatement credit")
    fact(store, "STD-1", "distinguishedFrom", at("MEC-2"))
    entry(store, "MEC-2", "Mechanism", "a reinstatement restores within a period")
    entry(store, "TD-3", "Debt", "the range disagrees with the shape")
    fact(store, "TD-3", "bearsOn", at("STD-1"))
    short = tmp_path / "short.md"
    short.write_text("\n".join(f"line {n}" for n in range(1, 11)), encoding="utf-8")
    long = tmp_path / "register.md"
    long.write_text("\n".join(f"row {n}" for n in range(1, ask.WHOLE_FILE + 50)), encoding="utf-8")
    fact(store, "STD-1", "pointer", "short.md:2-3")
    fact(store, "MEC-2", "pointer", f"register.md:1-{ask.WHOLE_FILE + 49}")
    return store


def test_read_prints_the_fields_and_every_neighbour_before_the_text(tmp_path, monkeypatch, capsys):
    """read STD-1 gives what find does not show and each entry linked to it, in either direction:
    the entry it is distinguished from and the debt that bears on it, with their claims."""
    monkeypatch.setattr(ask, "ROOT", tmp_path)
    monkeypatch.setattr(ask, "ASK_LOG", tmp_path / "asks.log")
    ask.read(neighbourhood(tmp_path), "STD-1")
    out = capsys.readouterr().out
    assert "Problem shape: restoring an amount drawn in a period" in out
    assert "Does not cover: the reinstatement credit" in out
    assert "distinguished from MEC-2 (Mechanism): a reinstatement restores within a period" in out
    assert "TD-3 bears on this (Debt): the range disagrees with the shape" in out
    assert out.index("Linked:") < out.index("== short.md:2-3") and "line 2\nline 3" in out


def test_a_symmetric_neighbour_is_shown_from_either_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ask, "ROOT", tmp_path)
    monkeypatch.setattr(ask, "ASK_LOG", tmp_path / "asks.log")
    ask.read(neighbourhood(tmp_path), "MEC-2")
    assert "STD-1 distinguished from this (Standard)" in capsys.readouterr().out


def test_read_refuses_a_pointer_to_a_whole_long_file(tmp_path, monkeypatch, capsys):
    """A pointer naming all of a long register hands the reader every row of it. read says so and
    prints none of it, and the entry's own fields stand in."""
    monkeypatch.setattr(ask, "ROOT", tmp_path)
    monkeypatch.setattr(ask, "ASK_LOG", tmp_path / "asks.log")
    ask.read(neighbourhood(tmp_path), "MEC-2")
    out = capsys.readouterr().out
    assert "pointer defect" in out and "row 1\n" not in out
    assert ask.whole_file("short.md:1-10") is None


def test_read_prints_an_entry_with_a_register_row_and_a_pointer(tmp_path, monkeypatch, capsys):
    """An entry with its defining register row and a pointer, as every register entry has, prints
    both under their labels, rather than reading the label as a path."""
    monkeypatch.setattr(ask, "ROOT", tmp_path)
    monkeypatch.setattr(ask, "ASK_LOG", tmp_path / "asks.log")
    (tmp_path / "register.md").write_text("| MEC-1 | a row |", encoding="utf-8")
    (tmp_path / "short.md").write_text("\n".join(f"line {n}" for n in range(1, 11)), encoding="utf-8")
    store = ox.Store()
    entry(store, "MEC-1", "Mechanism", "a mechanism")
    fact(store, "MEC-1", "row", "register.md:1-1")
    fact(store, "MEC-1", "pointer", "short.md:2-3")
    ask.read(store, "MEC-1")
    out = capsys.readouterr().out
    assert "== row register.md:1-1\n| MEC-1 | a row |" in out
    assert "== pointed-at short.md:2-3\nline 2\nline 3" in out


def test_every_find_and_read_is_logged_with_its_best_score(isolated, capsys):
    store = ox.Store()
    entry(store, "MEC-1", "Mechanism", "a ledger account")
    embed.build(store, isolated)
    ask.find(store, "ledger", set(), set(), set(), 8)
    logged = ask.asks()
    assert [(r["verb"], r["ids"], r["text"]) for r in logged] == [("find", "MEC-1", "ledger")]
    assert float(logged[0]["best"]) > 0.9


def test_a_gap_is_recorded_with_its_entry_and_line(isolated, capsys):
    """An agent records what reading found at the moment it finds it, with the entry it qualifies and
    the line it was read from, so the handoff report is a query rather than a memory."""
    ask.gap("LG-Q7 covers an unkeyed parent only", ["STD-280", "docs/developer/plans/ledger.md:416"])
    capsys.readouterr()
    (recorded,) = ask.asks()
    assert recorded["verb"] == "gap" and recorded["ids"] == "STD-280"
    assert recorded["text"] == "LG-Q7 covers an unkeyed parent only @ docs/developer/plans/ledger.md:416"
    ask.misses(20)
    out = capsys.readouterr().out
    assert "gaps recorded by reading" in out and "LG-Q7 covers an unkeyed parent only" in out


def test_misses_near_lists_the_confident_and_incomplete(isolated, capsys):
    """A question answered at 0.71 leaves no miss, and is where a confident wrong answer lives."""
    ask.log_ask("find", "a child account finds its parent", 0.71, ["PAT-41"])
    ask.log_ask("find", "a ledger account", 0.86, ["MEC-1"])
    ask.log_ask("find", "nothing like it", 0.60, [])
    ask.misses(20, near=True)
    out = capsys.readouterr().out.split("near answers", 1)[1]
    assert "a child account finds its parent" in out and "PAT-41" in out
    assert "a ledger account" not in out and "nothing like it" not in out


def test_a_kind_can_be_excluded_and_every_other_kept():
    """Questions cost some ranking, so an agent whose answers are crowded by them leaves them out
    without naming every other kind, and terms stay out unless they are named."""
    every = set(ask.KINDS.values()) - {"Term"}
    assert ask.without(set(), {"Question"}) == every - {"Question"}
    assert ask.without({"Standard", "Question"}, {"Question"}) == {"Standard"}
    assert ask.without(set(), set()) == set()


def test_closing_a_gap_removes_its_lines_and_the_question_behind_it(isolated, capsys):
    """Pruning happens when a gap is closed: the gap goes, with the miss and the near answers of the
    question asked just before it, and nothing else."""
    ask.log_ask("find", "a child account finds its parent", 0.71, ["PAT-41"])
    ask.log_miss("find a child account finds its parent")
    ask.gap("LG-Q7 covers an unkeyed parent only", ["STD-280"])
    ask.log_ask("find", "something else", 0.70, ["MEC-1"])
    ask.gap("another entry's gap", ["MEC-9"])
    assert next(r for r in ask.asks() if r["ids"] == "STD-280")["asked"] == "a child account finds its parent"
    ask.close(["STD-280"])
    left = ask.asks()
    assert [r["text"] for r in left] == ["something else", "another entry's gap"]
    assert not ask.MISS_LOG.read_text(encoding="utf-8").strip()
    assert "closed 1 gap(s) on STD-280" in capsys.readouterr().out


def test_misses_removes_a_question_the_index_now_answers(isolated, capsys):
    """A logged question asked again that now scores at NEAR or above was closed by an entry
    written since, so its lines go. One still weak stays."""
    store = ox.Store()
    entry(store, "MEC-1", "Mechanism", "a ledger account")
    embed.build(store, isolated)
    ask.log_miss("find ledger")
    ask.log_ask("find", "ledger", 0.60, [])
    ask.log_ask("find", "graph", 0.60, [])
    ask.log_miss("find graph")
    ask.misses(20, db=store)
    out = capsys.readouterr().out
    assert "1 question(s) the index now answers" in out
    assert [r["text"] for r in ask.asks()] == ["graph"]
    assert ask.MISS_LOG.read_text(encoding="utf-8").count("find ") == 1
