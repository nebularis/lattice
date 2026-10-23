# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""D-24 (H2.8b): every `pat:` term a builder uses is declared in Appendix A of the patterns guide. A term that is written and
not declared has no definition for a reader or an adopter's own shapes to rely on. Test IDs are H2.8b-Tn."""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
GUIDE = REPO / "docs" / "architecture" / "rdf-sparql-patterns-guide.md"
SRC = REPO / "tools" / "persistence" / "src" / "persistence"


def declared() -> set:
    """The terms of the Turtle block of Appendix A, each declared as `pat:name a owl:...`."""
    text = GUIDE.read_text(encoding="utf-8")
    appendix = text[text.index("## Appendix A"):text.index("## Appendix B")]
    return set(re.findall(r"^pat:(\w+)\s+a\s", appendix, re.M))


def used_by_builders() -> dict:
    """Each `pat:` term a builder or the contract names, with where. A call `_pat("seq")` and an attribute or item of `PAT` are the two ways."""
    out: dict = {}
    for name in ("builders.py", "contract.py"):
        for node in ast.walk(ast.parse((SRC / name).read_text(encoding="utf-8"))):
            term = None
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_pat" and node.args and isinstance(node.args[0], ast.Constant):
                term = node.args[0].value
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "PAT":
                term = node.attr
            elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "PAT" and isinstance(node.slice, ast.Constant):
                term = node.slice.value
            if term:
                out.setdefault(term, set()).add(name)
    return out


def test_h2_8b_t17_the_appendix_declares_a_good_many_terms():
    assert len(declared()) > 40 and {"seq", "epoch", "checkpoint", "previousVersion"} <= declared()


def test_h2_8b_t18_every_pat_term_a_builder_uses_is_declared_in_the_guide():
    used = used_by_builders()
    assert len(used) > 20
    assert {t: sorted(w) for t, w in used.items() if t not in declared()} == {}
