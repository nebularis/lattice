"""The binding to Вивід (ADR-A152, plan vyvid-migration, VM-1): vyvid.toml parses and names what LATTICE
defines, bootstrap:vyvid decides rightly, and `vyd context` names LATTICE where the binding is trusted."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap_vyvid import decide  # noqa: E402
from lattice_repo_catalogue import find_root  # noqa: E402

ROOT = find_root()

# The families LATTICE's own check defines by a register row, which the binding must name too.
ROW_FAMILIES = {"STD", "PRI", "PAT", "MEC", "CAP", "TD", "PDD", "BL"}


@pytest.fixture(scope="module")
def binding() -> dict:
    return tomllib.loads((ROOT / "vyvid.toml").read_text(encoding="utf-8"))


def expand(spec: str) -> Path:
    """A `docs:` or `code:` path of vyvid.toml, as a path under the root."""
    kind, _, rest = spec.partition(":")
    base = ROOT / "docs" if kind == "docs" else ROOT
    return base / rest


def test_vm1_01_project_is_lattice_and_public(binding):
    assert binding["project"]["name"] == "lattice"
    assert binding["project"]["visibility"] == "public"


def test_vm1_02_every_family_is_defined_by_a_file_that_exists(binding):
    missing = []
    for name, family in binding["project"]["families"].items():
        defined = family["defined"]
        for spec in [defined] if isinstance(defined, str) else defined:
            path = expand(spec)
            found = list(path.parent.glob(path.name)) if any(c in path.name for c in "*?[") else [path] if path.exists() else []
            if not found:
                missing.append(f"{name}: {spec}")
    assert not missing, missing


def test_vm1_03_the_row_families_are_all_named(binding):
    assert ROW_FAMILIES <= set(binding["project"]["families"])


def test_vm1_04_the_exceptions_baseline_is_the_one_file(binding):
    spec = binding["project"]["identifiers"]["exceptions"]
    assert expand(spec) == ROOT / "tools/knowledge/identifier-exceptions.txt"
    assert expand(spec).exists()


def test_vm1_05_bootstrap_is_a_noop_at_the_pinned_version():
    message, command = decide("0.2.2", "0.2.2", have_uv=True)
    assert command is None and "is installed" in message


def test_vm1_06_bootstrap_says_what_it_skipped_without_uv():
    message, command = decide(None, "0.2.2", have_uv=False)
    assert command is None and "uv is missing" in message


def test_vm1_07_bootstrap_installs_the_pinned_tag_otherwise():
    message, command = decide("0.2.1", "0.2.2", have_uv=True)
    assert command is not None and command[-1].endswith("@v0.2.2") and "replacing 0.2.1" in message


def test_vm1_08_vyd_context_names_lattice_where_trusted():
    if shutil.which("vyd") is None:
        pytest.skip("vyd is not installed")
    config = subprocess.run(["vyd", "config"], capture_output=True, text=True, timeout=60, cwd=ROOT).stdout
    if "is not trusted" in config or "projects: none" in config:
        pytest.skip("the binding is not trusted here, run `vyd trust` in the checkout")
    done = subprocess.run(["vyd", "context", str(ROOT)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr[-400:]
    assert "project: lattice" in done.stdout


def test_vm3_05_the_decision_pattern_matches_every_spelling_the_corpus_uses_and_no_prose(binding):
    """The ADR family's pattern is LATTICE's, declared in vyvid.toml, so the spellings it must match and the prose it
    must leave alone are pinned here as the old check pinned them."""
    pattern = re.compile(binding["project"]["families"]["ADR"]["pattern"])
    for spelling in ("ADR-A01", "ADR-A131", "ADR-A07b", "ADR-AC2", "ADR-A-C2", "ADR-A-FM2", "ADR-A-CAP1"):
        assert pattern.fullmatch(spelling), spelling
    for text in ("ADR", "an ADR for", "ADRs", "ADR-", "PDD-01", "TD-34"):
        assert not pattern.fullmatch(text), text
