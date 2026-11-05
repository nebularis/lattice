# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Every `turtle-example` excerpt in the Persistence README's Examples section is part of the example file it names, so an
excerpt cannot drift from the tested fixture (H2.11 review, 2026-10-21). An excerpt opens with `# from examples/<file>.ttl` and
is read with that file's prefixes."""

from __future__ import annotations

import re
import sys

import pytest
from rdflib import Graph

from conftest import ONTOLOGY_DIR, REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))
from literate_migration_check import labelled  # noqa: E402  (blank nodes labelled by their own subtree)

README = (ONTOLOGY_DIR / "README.md").read_text(encoding="utf-8")
EXAMPLES = README[README.index("## 8. Examples"):README.index("## 9. Canonicalisation")]
EXCERPTS = re.findall(r"```turtle-example\n# from (examples/[\w./-]+\.ttl)\n(.*?)```", EXAMPLES, re.S)


def test_readme_t1_every_excerpt_in_the_examples_section_names_its_file() -> None:
    assert EXCERPTS, "the Examples section has no turtle-example excerpt"
    assert EXAMPLES.count("```turtle-example") == len(EXCERPTS)
    assert "```turtle\n" not in EXAMPLES


@pytest.mark.parametrize("source,excerpt", EXCERPTS, ids=[s for s, _ in EXCERPTS])
def test_readme_t2_an_excerpt_is_part_of_the_file_it_names(source: str, excerpt: str) -> None:
    text = (ONTOLOGY_DIR / source).read_text(encoding="utf-8")
    prefixes = "".join(line + "\n" for line in text.splitlines() if line.startswith("@prefix"))
    shown = labelled(Graph().parse(data=prefixes + excerpt, format="turtle"))
    missing = shown - labelled(Graph().parse(data=text, format="turtle"))
    assert shown and missing == set()
