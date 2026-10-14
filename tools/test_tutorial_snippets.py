# SPDX-License-Identifier: MPL-2.0

"""The tutorial's excerpt and link check (plan lattice-tutorial §5, TUT-0)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tutorial_snippets import CHAPTERS, check  # noqa: E402

SOURCE = """@prefix ex: <https://example.org/x#> .

ex:a a ex:Thing ;
    ex:name "A" .

ex:b a ex:Thing ;
    ex:name "B" .
"""

LINK = "https://github.com/nebularis/lattice/blob/main/"


def _repo(tmp_path: Path, chapter: str) -> Path:
    (tmp_path / "ontology").mkdir()
    (tmp_path / "ontology" / "x.ttl").write_text(SOURCE, encoding="utf-8")
    (tmp_path / CHAPTERS).mkdir(parents=True)
    (tmp_path / CHAPTERS / "01-x.md").write_text(chapter, encoding="utf-8")
    return tmp_path


def _excerpt(body: str, source: str = "ontology/x.ttl") -> str:
    return f"Text.\n\n<!-- source: {source} -->\n```turtle\n{body}\n```\n"


def test_matching_excerpt_passes(tmp_path: Path) -> None:
    report = check(_repo(tmp_path, _excerpt('ex:a a ex:Thing ;\n    ex:name "A" .')))
    assert report.findings == [] and report.excerpts == 1


def test_changed_line_is_drift(tmp_path: Path) -> None:
    report = check(_repo(tmp_path, _excerpt('ex:a a ex:Thing ;\n    ex:name "Z" .')))
    assert len(report.findings) == 1 and "no longer matches ontology/x.ttl" in report.findings[0]


def test_missing_source_is_drift(tmp_path: Path) -> None:
    report = check(_repo(tmp_path, _excerpt("ex:a a ex:Thing ;", source="ontology/gone.ttl")))
    assert len(report.findings) == 1 and "does not exist" in report.findings[0]


def test_source_outside_repository_is_drift(tmp_path: Path) -> None:
    report = check(_repo(tmp_path, _excerpt("ex:a a ex:Thing ;", source="../x.ttl")))
    assert len(report.findings) == 1 and "outside the repository" in report.findings[0]


def test_turtle_without_source_comment_is_drift(tmp_path: Path) -> None:
    report = check(_repo(tmp_path, "Text.\n\n```turtle\nex:a a ex:Thing ;\n```\n"))
    assert len(report.findings) == 1 and "no source comment" in report.findings[0]


def test_other_languages_need_no_source(tmp_path: Path) -> None:
    report = check(_repo(tmp_path, "```bash\nmise run check\n```\n"))
    assert report.findings == [] and report.excerpts == 0


def test_elision_checks_each_part_in_order(tmp_path: Path) -> None:
    report = check(_repo(tmp_path, _excerpt('ex:a a ex:Thing ;\n# …\nex:b a ex:Thing ;\n    ex:name "B" .')))
    assert report.findings == []


def test_elided_parts_out_of_order_are_drift(tmp_path: Path) -> None:
    report = check(_repo(tmp_path, _excerpt("ex:b a ex:Thing ;\n# …\nex:a a ex:Thing ;")))
    assert len(report.findings) == 1 and "part 2" in report.findings[0]


def test_link_to_present_path_passes(tmp_path: Path) -> None:
    report = check(_repo(tmp_path, f"See [x]({LINK}ontology/x.ttl) and [dir]({LINK.replace('blob', 'tree')}ontology).\n"))
    assert report.findings == [] and report.links == 2


def test_link_to_missing_path_is_drift(tmp_path: Path) -> None:
    report = check(_repo(tmp_path, f"See [x]({LINK}ontology/gone.ttl).\n"))
    assert len(report.findings) == 1 and "ontology/gone.ttl names no path" in report.findings[0]
