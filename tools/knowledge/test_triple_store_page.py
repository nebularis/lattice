# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Every link the triple-store page makes into the domain's findings names a heading the domain has (ADR-A152 decision 7's
addendum of 2026-11-25, TD-148). The page follows the domain's main branch, so a heading reworded there breaks a link here."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lattice_repo_catalogue  # noqa: E402
import vyd  # noqa: E402

CATALOGUE = lattice_repo_catalogue.load()
ROOT = CATALOGUE.root
PAGE = ROOT / CATALOGUE.area("architecture") / "triple-store-discovery.md"
LINK = re.compile(r"vyvid-triple-stores/blob/([^/]+)/findings\.md#([^)\s]+)")


def anchor(heading: str) -> str:
    """The fragment GitHub gives a heading: lower case, punctuation dropped but for hyphens and underscores, spaces as hyphens."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def findings() -> Path:
    """The domain's findings file in the clone vyd reads, or a skip with the reason."""
    code, output, skipped = vyd.run(["context"], cwd=str(ROOT))
    if skipped or code != 0:
        pytest.skip("vyd did not run, so the page's links were not checked. Run `mise run bootstrap`")
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"\bdomain triple-stores\b", line):
            for after in lines[i + 1 : i + 4]:
                found = re.search(r"\bskill\s+(.+)$", after)
                if found and (Path(found[1].strip()).parent / "findings.md").is_file():
                    return Path(found[1].strip()).parent / "findings.md"
    pytest.skip("vyd lists no clone of the triple-stores domain, so the page's links were not checked")


def test_the_anchor_rule_keeps_an_underscore_and_drops_backticks():
    assert anchor("TSD-19. The order of `GROUP_CONCAT`") == "tsd-19-the-order-of-group_concat"
    assert anchor("TSD-68. Oxigraph refuses a prologue after the `;` of an update request").endswith("after-the--of-an-update-request")


def test_every_link_into_the_findings_follows_main_and_names_a_heading_the_domain_has():
    headings = {anchor(m[1]) for m in re.finditer(r"^#{2,4} (.+)$", findings().read_text(encoding="utf-8"), re.M)}
    links = LINK.findall(PAGE.read_text(encoding="utf-8"))
    assert links, "the page links no finding"
    assert {branch for branch, _ in links} == {"main"}
    assert sorted(fragment for _, fragment in links if fragment not in headings) == []
