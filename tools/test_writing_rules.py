# SPDX-License-Identifier: MPL-2.0
"""Tests of the writing rules on added Markdown lines (ADR-A133)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import writing_rules as wr  # noqa: E402


def rules(path: str, text: str, lines=None) -> list[tuple[int, str, bool]]:
    count = len(text.splitlines())
    found = wr.check_file(path, text, lines or range(1, count + 1))
    return [(f.line, f.rule.split(".")[0], f.blocking) for f in found]


def test_gh3_01_a_semicolon_in_prose_fails() -> None:
    assert rules("a.md", "One clause; another.\n") == [(1, "a semicolon in prose", True)]


def test_gh3_02_code_urls_entities_comments_and_front_matter_are_not_prose() -> None:
    text = "\n".join([
        "---",
        "title: a; b",
        "---",
        "<!-- SPDX; comment -->",
        "Write `ex:a ex:b ex:c ;` in Turtle, see <https://example.org/a;b> and a&nbsp;space.",
        "",
        "```turtle",
        "ex:a ex:b ex:c ;",
        "    ex:d ex:e .",
        "```",
        "",
        "Inline ``code; with ticks`` too.",
    ]) + "\n"
    assert rules("a.md", text) == []


def test_gh3_03_only_markdown_outside_generated_paths_is_judged() -> None:
    assert rules("a.py", "x = 1; y = 2\n") == []
    assert rules("docs/_includes/layers/x/README.md", "One; two.\n") == []
    assert rules(".github/copilot-instructions.md", "One; two.\n") == []


def test_gh3_04_this_document_fails_only_in_a_literate_readme() -> None:
    text = "This document is the configuration half.\n"
    assert rules("ontology/party/README.md", text) == [(1, '"this document" in a literate README, which generates '
                                                           "several documents", True)]
    assert rules("docs/developer/plans/x.md", text) == []


def test_gh3_05_a_hard_wrapped_paragraph_warns() -> None:
    text = "A paragraph that a writer wrapped\nat a fixed width.\n\nA paragraph on one line.\n"
    assert rules("a.md", text) == [(2, "a hard-wrapped line", False)]


def test_gh3_06_a_wrapped_list_entry_warns_and_separate_entries_do_not() -> None:
    text = "- an entry that a writer wrapped\n  at a fixed width\n- a second entry\n- a third entry\n"
    assert rules("a.md", text) == [(2, "a hard-wrapped line", False)]


def test_gh3_07_tables_headings_and_line_breaks_are_not_wraps() -> None:
    text = "# A heading\nText under it.\n\n| a | b |\n|---|---|\n\nA line ending in two spaces  \nthen a break.\n"
    assert rules("a.md", text) == []


def test_gh3_08_only_the_added_lines_are_judged() -> None:
    text = "Old; text.\nNew text.\n"
    assert rules("a.md", text, [2]) == [(2, "a hard-wrapped line", False)]
    assert rules("a.md", text, [1]) == [(1, "a semicolon in prose", True)]


def test_gh3_09_the_staged_lines_of_a_repository(tmp_path: Path) -> None:
    def sh(*args: str) -> None:
        subprocess.run(list(args), cwd=tmp_path, check=True, capture_output=True)
    sh("git", "init", "-q", "-b", "main")
    (tmp_path / "a.md").write_text("Fine.\n")
    sh("git", "add", ".")
    sh("git", "-c", "user.email=t@example.org", "-c", "user.name=T", "commit", "-q", "--no-verify", "-m", "x")
    (tmp_path / "a.md").write_text("Fine.\n\nNot fine; at all.\n")
    sh("git", "add", ".")
    found = wr.check(tmp_path, wr.staged(tmp_path))
    assert [str(f) for f in found] == ["a.md:3: a semicolon in prose. Use a period or a comma"]


def test_gh3_11_header_fields_are_not_wraps() -> None:
    text = "# A title\n\n**Status:** proposed\n**Date:** 2026-10-23\n**Unit:** `x`. More: text\n"
    assert rules("a.md", text) == []


README = "\n".join([
    "# A layer",
    "",
    "Literate specification, in the layout of [ADR-A126](../../docs/architecture/decisions/ADR-A126-x.md).",
    "",
    "## 3. Extraction Contract",
    "",
    "The two documents share one version (ADR-A131 decision 2).",
    "",
    "### 5.1 Design decisions",
    "",
    "- **Two documents.** Configuration and records ([ADR-A131](../../docs/architecture/decisions/ADR-A131-x.md)).",
    "- **Exact shares.** As decision 6 asks.",
    "",
    "### 5.2 Worked reading",
    "",
    "The example debits the pool (ADR-A131).",
    "",
    "## 7. Shapes",
    "",
    "```turtle-shapes",
    "# constraints for the account definition (ADR-A131 decisions 2 and 3)",
    'sh:message "A record must not be forward-dated." ;',
    "```",
    "",
    "## 12. Release Notes",
    "",
    "- **0.1.0**. no effect. New terms ([ADR-A131](../../docs/architecture/decisions/ADR-A131-x.md)).",
    "",
])
CITED = "a decision cited outside the Design decisions section"
BARE = "a bare decision number, which names no record"


def test_gh3_12_a_layer_readme_cites_a_decision_only_in_its_design_decisions_and_release_notes() -> None:
    found = rules("ontology/ledger/README.md", README)
    assert found == [(7, CITED, True), (12, BARE, True), (16, CITED, True), (21, CITED, True)]


def test_gh3_13_the_layout_line_before_the_first_section_and_other_documents_are_not_judged() -> None:
    assert not [f for f in rules("ontology/ledger/README.md", README) if f[0] == 3]
    assert rules("docs/developer/plans/ledger.md", README) == []
    assert rules("benchmark/ledger-credit-kinds/README.md", README) == []


def test_gh3_14_a_decision_inside_a_fenced_block_is_judged_since_the_block_is_published() -> None:
    assert (21, CITED, True) in rules("ontology/ledger/README.md", README)
    assert rules("ontology/ledger/README.md", README, lines=[22]) == []


def test_gh3_15_only_the_added_lines_of_a_readme_are_judged_for_decisions() -> None:
    assert rules("ontology/ledger/README.md", README, lines=[11, 27]) == []
    assert rules("ontology/ledger/README.md", README, lines=[7]) == [(7, CITED, True)]


WORKING = "\n".join([
    "# A layer",
    "",
    "### 5.1 Design decisions",
    "",
    "- **A period is an account.** Nothing resets (PDD-15), by the rule of STD-294.",
    "- **An exact share is two integers**, since no store compares the literal by value (TSD-70).",
    "",
    "## 6. Terms",
    "",
    "**Definition.** The purpose a draw names (LG-Q2). Hashed with SHA-256, in UTF-8.",
    "Removed with the allowance terms (LG-3), as AIR-2.6 planned.",
    "",
])


def working(path: str, slices=frozenset(), lines=None) -> list[tuple[int, str]]:
    found = wr.check_file(path, WORKING, lines or range(1, len(WORKING.splitlines()) + 1), slices)
    return [(f.line, f.rule.split(".")[0]) for f in found if "working-document" in f.rule]


def test_gh3_16_a_register_entry_or_a_question_fails_anywhere_in_a_layer_readme() -> None:
    assert working("ontology/ledger/README.md") == [(5, "a working-document identifier, PDD-15"),
                                                    (10, "a working-document identifier, LG-Q2")]


def test_gh3_17_a_slice_fails_only_where_the_index_defines_it_and_a_finding_or_a_hash_never_does() -> None:
    assert working("ontology/ledger/README.md", frozenset({"LG-3", "AIR-2.6"}), lines=[11]) == [
        (11, "a working-document identifier, LG-3")]
    assert working("ontology/ledger/README.md", frozenset({"LG-3"}), lines=[6]) == []
    assert working("ontology/ledger/README.md", frozenset({"SHA-256"}), lines=[10]) == [
        (10, "a working-document identifier, LG-Q2")]
    assert working("docs/developer/plans/ledger.md", frozenset({"LG-3"})) == []


def test_gh3_18_the_slices_are_read_from_the_developer_index(tmp_path: Path) -> None:
    (tmp_path / "docs" / "developer").mkdir(parents=True)
    (tmp_path / "docs" / "developer" / "INDEX.md").write_text(
        "| Slice | Scope |\n|---|---|\n| LG-3 | a migration |\n| ledger | unit |\n", encoding="utf-8", newline="\n")
    assert wr.slice_ids(tmp_path) == frozenset({"LG-3"})
    assert wr.slice_ids(tmp_path / "nowhere") == frozenset()

