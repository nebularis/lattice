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
from bootstrap_vyvid import decide, install_kind  # noqa: E402
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


def test_vm1_07_bootstrap_installs_the_pinned_tag_over_a_git_install():
    message, command = decide("0.2.1", "0.2.2", have_uv=True, kind="git")
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


def write_receipt(tmp_path: Path, requirement: str) -> Path:
    receipt = tmp_path / "uv-receipt.toml"
    receipt.write_text(f'[tool]\nrequirements = [{{ name = "vyvid", {requirement} }}]\nentrypoints = [{{ name = "vyd", install-path = "/bin/vyd" }}]\n', encoding="utf-8")
    return receipt


def test_vm1_09_an_editable_install_at_another_version_is_left_alone(tmp_path):
    key, note = install_kind(write_receipt(tmp_path, 'extras = ["symbols"], editable = "/somewhere/vyvid"'))
    assert (key, note) == ("editable", None)
    message, command = decide("0.2.12", "0.2.11", have_uv=True, kind=key)
    assert command is None and "left alone" in message and "@v0.2.11" in message


def test_vm1_10_a_directory_install_is_left_alone(tmp_path):
    key, note = install_kind(write_receipt(tmp_path, 'directory = "/somewhere/vyvid"'))
    assert (key, note) == ("directory", None)
    message, command = decide("0.1.0", "0.2.11", have_uv=True, kind=key)
    assert command is None and "left alone" in message and "@v0.2.11" in message


def test_vm1_11_a_git_install_at_another_version_is_replaced(tmp_path):
    key, note = install_kind(write_receipt(tmp_path, 'git = "https://github.com/nebularis/vyvid?tag=v0.2.10"'))
    assert (key, note) == ("git", None)
    message, command = decide("0.2.10", "0.2.11", have_uv=True, kind=key)
    assert command is not None and command[-1].endswith("@v0.2.11") and "replacing 0.2.10" in message


def test_vm1_12_a_missing_receipt_leaves_an_installed_vyd_alone(tmp_path):
    """A vyd from pip or pipx has no uv receipt, and is never replaced."""
    key, note = install_kind(tmp_path / "absent" / "uv-receipt.toml")
    assert key is None and note is not None and "missing" in note
    message, command = decide("0.2.12", "0.2.11", have_uv=True, kind=key)
    assert command is None and "left alone" in message


def test_vm1_13_an_unreadable_receipt_leaves_an_installed_vyd_alone(tmp_path):
    receipt = tmp_path / "uv-receipt.toml"
    receipt.write_text("not = [toml", encoding="utf-8")
    key, note = install_kind(receipt)
    assert key is None and note is not None and "could not be read" in note
    message, command = decide("0.2.12", "0.2.11", have_uv=True, kind=key)
    assert command is None and "left alone" in message


def test_vm1_14_a_receipt_in_a_bad_encoding_is_unreadable_not_a_crash(tmp_path):
    receipt = tmp_path / "uv-receipt.toml"
    receipt.write_bytes(b"[tool]\nrequirements = [{ name = \"vyvid\", git = \"\xff\xfe\" }]\n")
    key, note = install_kind(receipt)
    assert key is None and note is not None and "could not be read" in note


def test_vm1_15_an_absent_vyd_is_installed_without_a_receipt():
    message, command = decide(None, "0.2.11", have_uv=True)
    assert command is not None and command[-1].endswith("@v0.2.11") and "replacing" not in message


def test_vm3_05_the_decision_pattern_matches_every_spelling_the_corpus_uses_and_no_prose(binding):
    """The ADR family's pattern is LATTICE's, declared in vyvid.toml, so the spellings it must match and the prose it
    must leave alone are pinned here as the old check pinned them."""
    pattern = re.compile(binding["project"]["families"]["ADR"]["pattern"])
    for spelling in ("ADR-A01", "ADR-A131", "ADR-A07b", "ADR-AC2", "ADR-A-C2", "ADR-A-FM2", "ADR-A-CAP1"):
        assert pattern.fullmatch(spelling), spelling
    for text in ("ADR", "an ADR for", "ADRs", "ADR-", "PDD-01", "TD-34"):
        assert not pattern.fullmatch(text), text
