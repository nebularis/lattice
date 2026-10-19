# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Published decisions and the sources rule (ADR-A127, slice DOC1).
Validation Pack: docs/developer/validation/DOC1.md. Test IDs are DOC1-Tn."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import published_decisions as pd  # noqa: E402
import sources_check as sc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FENCE = "```"
ABSOLUTE = "https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/"
PUBLISHED = """---
published: true
---
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A10: Ten

**Status:** Published, 2026-10-19. Accepted 2026-10-01.
**Described in:** [Alpha README](../../../ontology/alpha/README.md)

## Decision

{body}

## Provenance

{provenance}
"""
ACCEPTED = "<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->\n\n# ADR-A11: Eleven\n\n**Status:** Accepted\n"
PROPOSED = "<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->\n\n# ADR-A12: Twelve\n\n**Status:** Proposed\n"
LAYOUT = "\n".join(f"## {n}. {t}\n\nNone.\n" for n, t in enumerate(
    ["Purpose and Scope", "Namespace and Prefixes", "Extraction Contract", "Overview", "Detailed Design",
     "Description Logic Encoding"], 1))


def tree(tmp: Path, readme: str, body: str = "Decided.", provenance: str = "None.", migrated: bool = True) -> Path:
    """A repository with one module, alpha, whose README is ``readme``, and ADRs A10 (published), A11 and A12."""
    (tmp / "ontology/alpha").mkdir(parents=True)
    (tmp / "repository-catalogue.md").write_text(
        f'{FENCE}toml repository-catalogue\n[conventions]\nroles = []\n[conventions.kinds]\nsubstrate = "a layer"\n'
        f'[catalogue]\nschema = 1\nmodules = ["alpha"]\n[[docs]]\npath = "docs/architecture/"\nowns = "decisions"\nrow = "decisions"\n'
        f'adrs = []\n{FENCE}\n', encoding="utf-8")
    entry = f'{FENCE}toml repository-catalogue\n[module]\nkind = "substrate"\nroles = []\n{FENCE}\n'
    (tmp / "ontology/alpha/README.md").write_text(entry + readme + "\n" + (LAYOUT if migrated else ""), encoding="utf-8")
    decisions = tmp / "docs/architecture/decisions"
    decisions.mkdir(parents=True)
    (tmp / "docs/_config.yml").write_text("theme: null\n# BEGIN GENERATED published-decisions.\n# END GENERATED published-decisions\n",
                                 encoding="utf-8")
    (decisions / "ADR-A10-ten.md").write_text(PUBLISHED.format(body=body, provenance=provenance), encoding="utf-8")
    (decisions / "ADR-A11-eleven.md").write_text(ACCEPTED, encoding="utf-8")
    (decisions / "ADR-A12-twelve.md").write_text(PROPOSED, encoding="utf-8")
    return tmp


def test_doc1_t1_the_list_is_written_from_the_status_lines_and_goes_stale(tmp_path: Path, capsys) -> None:
    root = tree(tmp_path, "Cites ADR-A10.")
    assert pd.main(["build", "--root", str(root)]) == 0
    text = (root / pd.locations(root).listing).read_text(encoding="utf-8")
    assert "| [A10](decisions/ADR-A10-ten.md) | Ten | 2026-10-19 | [Alpha README](../../ontology/alpha/README.md) |" in text
    assert "[A11]" not in text and "[A12]" not in text
    assert "include:\n  - ADR-A10-ten.md\n" in (root / pd.locations(root).config).read_text(encoding="utf-8")
    assert pd.main(["check", "--root", str(root)]) == 0
    (root / pd.locations(root).listing).write_text(text + "edited\n", encoding="utf-8")
    assert pd.main(["check", "--root", str(root)]) == 1
    assert "stale" in capsys.readouterr().err


def test_doc1_t2_a_published_decision_needs_described_in_provenance_and_front_matter(tmp_path: Path) -> None:
    root = tree(tmp_path, "")
    path = root / pd.locations(root).decisions / "ADR-A10-ten.md"
    text = path.read_text(encoding="utf-8")
    broken = text.replace("published: true", "published: false").replace("## Provenance", "## Notes")
    path.write_text("\n".join(l for l in broken.splitlines() if not l.startswith("**Described in")), encoding="utf-8")
    found = pd.problems(pd.load(root))
    assert len(found) == 3 and all("ADR-A10" in p for p in found)
    (root / pd.locations(root).decisions / "ADR-A11-eleven.md").write_text("---\npublished: true\n---\n" + ACCEPTED, encoding="utf-8")
    (root / pd.locations(root).decisions / "ADR-A12-twelve.md").write_text(PROPOSED.replace("Proposed", "Published, 2026-10-19"),
                                                          encoding="utf-8")
    found = pd.problems(pd.load(root))
    assert any("ADR-A11" in p and "front matter" in p for p in found)
    assert any("ADR-A12" in p and "is not 'Published" in p for p in found)


def test_doc1_t3_a_working_document_fails_outside_provenance_only(tmp_path: Path) -> None:
    link = "[the plan](../../developer/plans/x.md)"
    root = tree(tmp_path, f"See {link}.", provenance=f"From {link}.")
    failures, _ = sc.check(root)
    assert failures == ["ontology/alpha/README.md:6: refers to a working document"]
    root = tree(tmp_path / "b", "Fine.", body=f"Decided after {link}.")
    failures, _ = sc.check(root)
    assert failures == ["docs/architecture/decisions/ADR-A10-ten.md:13: refers to a working document"]


def test_doc1_t4_an_unpublished_citation_fails_in_a_migrated_readme_and_is_reported_in_another(tmp_path: Path) -> None:
    failures, reports = sc.check(tree(tmp_path / "a", "Cites ADR-A10 and ADR-A11."))
    assert len(failures) == 1 and "ADR-A11" in failures[0] and reports == []
    failures, reports = sc.check(tree(tmp_path / "b", "Cites ADR-A10 and ADR-A11.", migrated=False))
    assert failures == [] and len(reports) == 1 and "ADR-A11" in reports[0]


def test_doc1_t5_a_published_decision_cites_accepted_ones_by_absolute_link(tmp_path: Path) -> None:
    ok = f"Builds on ADR-A11, [ADR-A11]({ABSOLUTE}ADR-A11-eleven.md) and [ADR-A10](ADR-A10-ten.md)."
    assert sc.check(tree(tmp_path / "a", "", body=ok))[0] == []
    failures, _ = sc.check(tree(tmp_path / "b", "", body="Builds on [ADR-A11](ADR-A11-eleven.md)."))
    assert len(failures) == 1 and "relative link" in failures[0]
    failures, _ = sc.check(tree(tmp_path / "c", "", body="Builds on ADR-A12."))
    assert len(failures) == 1 and "Proposed" in failures[0]


def test_doc1_t6_the_repository_meets_the_rule_and_hides_unpublished_decisions() -> None:
    failures, _ = sc.check(ROOT)
    assert failures == []
    assert pd.problems(pd.load(ROOT)) == []
    config = (ROOT / pd.locations(ROOT).config).read_text(encoding="utf-8")
    assert "  - architecture/decisions/ADR-*\n" in config
    assert pd.CONFIG_RE.search(config).group(0) == pd.config_block(pd.load(ROOT))
