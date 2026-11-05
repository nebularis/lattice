# SPDX-License-Identifier: MPL-2.0
"""The facet schemes are generated from the facet register, never authored as Turtle (ADR-A134 decision 26).

Run by ``mise run check:knowledge``.
"""

from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

import pytest
import rdflib
from rdflib.compare import to_isomorphic

sys.path.insert(0, str(Path(__file__).resolve().parent))

import facets  # noqa: E402

SKOS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
FCT = rdflib.Namespace(facets.NS)

HEAD = """# Facet register

## Schemes

| ID | Label | Definition |
|---|---|---|
| Activity | activity | What is being done. |
| Quality | quality | What is protected. |
| Technology | technology | What it is specific to. |
"""

VALUES = """
## Activity

| ID | Label | Broader | Related | Group | Definition | Scope note | Ratified |
|---|---|---|---|---|---|---|---|
| design | design |  |  | yes | Any design activity. |  | yes |
| api-design | API design | design | interaction |  | Designing an interface. | Not for a UI. | yes |
| query-writing | query writing | design |  |  | Writing queries. |  | no |

## Quality

| ID | Label | Broader | Related | Group | Definition | Scope note | Ratified |
|---|---|---|---|---|---|---|---|
| interaction | interaction capability |  |  |  | Being usable. |  | yes |

## Technology

| ID | Label | Broader | Related | Group | Definition | Scope note | Ratified |
|---|---|---|---|---|---|---|---|
| language | programming language |  |  | yes | A language. |  | yes |
| platform | platform |  |  | yes | A platform. |  | yes |
| java | Java | language platform |  |  | The Java language and platform. |  | yes |
"""


def graph_of(text: str) -> rdflib.Graph:
    return rdflib.Graph().parse(data=facets.turtle(*facets.parse(text)), format="turtle")


def problems_of(text: str) -> str:
    with pytest.raises(facets.RegisterError) as error:
        facets.parse(text)
    return str(error.value)


def test_the_register_is_read_into_three_schemes_of_ratified_values():
    schemes, values = facets.parse(facets.SOURCE_PATH.read_text(encoding="utf-8"))
    assert [s.slug for s in schemes] == list(facets.SCHEMES)
    assert len(values) > 300
    assert all(v.definition for v in values)


def test_each_column_becomes_the_skos_property_that_states_its_meaning():
    g = graph_of(HEAD + VALUES)
    assert (FCT.design, SKOS.topConceptOf, FCT.Activity) in g
    assert (FCT["api-design"], SKOS.topConceptOf, None) not in g
    assert (FCT["api-design"], SKOS.broader, FCT.design) in g
    assert (FCT["api-design"], SKOS.related, FCT.interaction) in g, "a related value may sit in another scheme"
    assert (FCT["api-design"], SKOS.scopeNote, rdflib.Literal("Not for a UI.")) in g
    assert (FCT.design, SKOS.editorialNote, rdflib.Literal("group")) in g
    assert (FCT["query-writing"], SKOS.editorialNote, rdflib.Literal("proposed")) in g
    assert set(g.objects(FCT.java, SKOS.broader)) == {FCT.language, FCT.platform}, "a value may have several broader values"


def test_the_same_register_gives_the_same_bytes_and_any_row_order_the_same_graph():
    """PRI-58: a repeat gives the same bytes, and a permutation of each scheme's rows the same graph."""
    first = facets.turtle(*facets.parse(HEAD + VALUES))
    assert facets.turtle(*facets.parse(HEAD + VALUES)) == first
    sections = VALUES.split("\n## ")
    shuffled = []
    for section in sections:
        lines = section.split("\n")
        rows = [i for i, line in enumerate(lines) if line.startswith("| ") and not line.startswith("| ID ")]
        body = [lines[i] for i in rows]
        random.Random(7).shuffle(body)
        for i, line in zip(rows, body):
            lines[i] = line
        shuffled.append("\n".join(lines))
    assert to_isomorphic(graph_of(HEAD + "\n## ".join(shuffled))) == to_isomorphic(graph_of(HEAD + VALUES))


def test_the_real_register_generates_the_same_bytes_twice(tmp_path: Path):
    a = facets.generate(output=tmp_path / "a.ttl").read_bytes()
    b = facets.generate(output=tmp_path / "b.ttl").read_bytes()
    assert a == b
    assert len(rdflib.Graph().parse(data=a.decode(), format="turtle")) > 1500


def test_a_broader_or_related_value_defined_nowhere_is_refused_with_its_line():
    broken = VALUES.replace("| query writing | design |", "| query writing | desgin |")
    broken = broken.replace("| design | interaction |", "| design | interactoin |")
    found = problems_of(HEAD + broken)
    assert "query-writing's broader value desgin is defined nowhere" in found
    assert "api-design's related value interactoin is defined nowhere" in found
    assert "facets.md:" in found


def test_a_broader_value_in_another_scheme_is_refused():
    found = problems_of(HEAD + VALUES.replace("| java | Java | language platform |", "| java | Java | design |"))
    assert "broader value design is in Activity, not Technology" in found


def test_a_value_defined_twice_is_refused():
    found = problems_of(HEAD + VALUES + "| java | Java again |  |  |  | Again. |  | yes |\n")
    assert "java is already defined" in found


def test_a_table_with_other_columns_or_a_flag_outside_yes_and_no_is_refused():
    assert "the columns are" in problems_of(HEAD + VALUES.replace("| Scope note | Ratified |", "| Note | Ratified |", 1))
    assert "Ratified is 'maybe'" in problems_of(HEAD + VALUES.replace("| Writing queries. |  | no |", "| Writing queries. |  | maybe |"))
    assert "Group is 'y'" in problems_of(HEAD + VALUES.replace("| design |  |  | yes |", "| design |  |  | y |"))


def test_the_generated_turtle_is_never_committed():
    """STD-003: a derived file has one source, the register, so no copy of it is tracked."""
    tracked = subprocess.run(
        ["git", "-C", str(facets.ROOT), "ls-files", "--", "tools/knowledge/facets.ttl", ".build/knowledge/facets.ttl"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    assert tracked == []
    assert facets.OUTPUT_PATH.is_relative_to(facets.ROOT / ".build")
