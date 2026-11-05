# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The documentation site's sections (OD-D29 to OD-D31). Validation Pack: docs/developer/validation/DOC2.md.
Test IDs are DOC2-Tn."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue as rc  # noqa: E402
import site_sections as ss  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FENCE = "```"
SECTION = 'name = "guide"\ntitle = "Guide"\npage = "docs/guide.md"\nlayout = "architecture"\norder = 1\nsources = ["notes/a.md"]'
CONFIG = f"exclude:\n  - vendor\n{ss.BEGIN}\n{ss.END}\n"


def _tree(tmp: Path, section: str = SECTION) -> Path:
    """A minimal repository with one site section whose source lies outside docs/."""
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "repository-catalogue.md").write_text(
        f"# Catalogue\n\n{FENCE}toml repository-catalogue\n[conventions]\nroles = []\n[conventions.kinds]\n"
        f"[catalogue]\nschema = 1\nmodules = []\n\n[[site]]\n{section}\n{FENCE}\n", encoding="utf-8")
    (tmp / "docs" / "_layouts").mkdir(parents=True)
    (tmp / "docs" / "_layouts" / "architecture.html").write_text("{{ content }}", encoding="utf-8")
    (tmp / "docs" / "_config.yml").write_text(CONFIG, encoding="utf-8")
    (tmp / "docs" / "guide.md").write_text("{% include guide/notes/a.md %}\n", encoding="utf-8")
    (tmp / "notes").mkdir()
    (tmp / "notes" / "a.md").write_text("# A\n\nUses {{ braces }}.\n", encoding="utf-8")
    return tmp


def test_doc2_t1_the_real_catalogue_declares_ordered_sections_that_exist() -> None:
    catalogue = rc.load(ROOT)
    assert [s.order for s in catalogue.site] == sorted(s.order for s in catalogue.site)
    assert {"home", "field-guide", "theory", "layers", "architecture", "decisions", "operations", "glossary", "contributing"} <= {s.name for s in catalogue.site}
    for s in catalogue.site:
        assert (ROOT / s.page).is_file(), s.page
    assert rc._site_problems(catalogue) == []


def test_doc2_t2_the_site_block_refuses_what_it_cannot_read() -> None:
    bad = {
        "unknown key": SECTION + '\nextra = "x"',
        "needs 'title'": SECTION.replace('title = "Guide"\n', ""),
        "same name": None,
        "page must be a path under docs/": SECTION.replace('"docs/guide.md"', '"guide.md"'),
        "'order' must be": SECTION.replace("order = 1", 'order = "1"'),
        "lower case words": SECTION.replace('"guide"', '"Guide"', 1),
        "never absolute": SECTION.replace('"notes/a.md"', '"../a.md"'),
    }
    for message, section in bad.items():
        if section is None:
            section = SECTION + "\n\n[[site]]\n" + SECTION.replace("order = 1", "order = 2")
        with pytest.raises(rc.CatalogueError, match=message):
            rc.load(_tree(Path(tempfile.mkdtemp()), section))


def test_doc2_t3_a_missing_page_layout_or_source_is_reported(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "docs" / "guide.md").unlink()
    (root / "docs" / "_layouts" / "architecture.html").unlink()
    (root / "notes" / "a.md").unlink()
    found = "\n".join(rc._site_problems(rc.load(root)))
    assert "page docs/guide.md does not exist" in found and "layout 'architecture'" in found and "source notes/a.md" in found


def test_doc2_t4_a_stale_copy_fails_the_check_and_the_copy_task_clears_it(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    assert any("missing" in p for p in ss.problems(rc.load(root)))
    ss.build(rc.load(root))
    assert ss.problems(rc.load(root)) == []
    copy = root / "docs/_includes/guide/notes/a.md"
    assert "{% raw %}" in copy.read_text(encoding="utf-8")
    (root / "notes" / "a.md").write_text("# A changed\n", encoding="utf-8")
    assert any("stale" in p for p in ss.problems(rc.load(root)))
    ss.build(rc.load(root))
    assert ss.problems(rc.load(root)) == []
    (root / "docs/_includes/guide/notes/old.md").write_text("x", encoding="utf-8")
    assert any("copy of nothing" in p for p in ss.problems(rc.load(root)))
    ss.build(rc.load(root))
    assert not (root / "docs/_includes/guide/notes/old.md").exists()


def test_doc2_t5_stale_defaults_and_a_page_that_hides_a_source_fail(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    ss.build(rc.load(root))
    config = root / "docs" / "_config.yml"
    assert "layout: architecture" in config.read_text(encoding="utf-8") and "vendor" in config.read_text(encoding="utf-8")
    config.write_text(config.read_text(encoding="utf-8").replace("layout: architecture", "layout: other"), encoding="utf-8")
    assert any("stale section defaults" in p for p in ss.problems(rc.load(root)))
    ss.build(rc.load(root))
    (root / "docs" / "guide.md").write_text("nothing shown\n", encoding="utf-8")
    assert any("does not show notes/a.md" in p for p in ss.problems(rc.load(root)))


def test_doc2_t6_the_repository_site_is_current() -> None:
    assert ss.problems(rc.load(ROOT)) == []
