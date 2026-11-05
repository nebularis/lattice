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
