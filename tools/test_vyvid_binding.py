"""The binding to Вивід (ADR-A152, plan vyvid-migration, VM-1): vyvid.toml parses and names what LATTICE
defines, bootstrap:vyvid decides rightly, and `vyd context` names LATTICE where the binding is trusted."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
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


SETUP = ROOT / "tools/claude-cloud-setup.sh"


def pasted_lines() -> str:
    """The lines the setup script's header says to paste, without the leading comment."""
    lines = SETUP.read_text(encoding="utf-8").split("\n")
    start = next(i for i, line in enumerate(lines) if "mkdir -p ~/.config/vyvid" in line)
    end = next(i for i, line in enumerate(lines) if line.startswith("#") and "bash \"$s\"" in line)
    return "\n".join(line[1:].strip() for line in lines[start:end + 1])


def test_vm7_01_the_pasted_lines_trust_this_repository_and_name_its_domains(tmp_path):
    config = "\n".join(line for line in pasted_lines().split("\n") if not line.startswith(("s=$(", "[ -n")))
    subprocess.run(["bash", "-c", config], env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}, check=True)
    written = tomllib.loads((tmp_path / ".config/vyvid/config.toml").read_text(encoding="utf-8"))
    binding = tomllib.loads((ROOT / "vyvid.toml").read_text(encoding="utf-8"))
    assert written["framework"]["trusted_repositories"] == ["github.com/nebularis/lattice"]
    assert [d["name"] for d in written["domains"]] == binding["project"]["domains"]
    assert {d["trust"] for d in written["domains"]} == {"own"}


def test_vm7_02_the_setup_script_clones_the_domains_before_the_index_is_built():
    text = SETUP.read_text(encoding="utf-8")
    assert text.index('step "vyvid" install_vyvid') < text.index('step "index packages"') < text.index('step "index" mise run build:knowledge & index_pid=$!') < text.index('later 150 "dependencies"') < text.index('wait "$index_pid"')
    assert text.index('step "packages" install_packages') < text.index('later 250 "reasoning testkit"') < text.rindex('wait "$isabelle_pid"')
    assert subprocess.run(["bash", "-n", str(SETUP)]).returncode == 0


def session_env(tmp_path: Path, mise_exit: int = 0) -> dict[str, str]:
    """A home, a log folder and a fake mise that records each task it is asked for."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "mise"
    fake.write_text(f"#!/bin/sh\necho \"$2\" >> {tmp_path}/ran\nexit {mise_exit}\n", encoding="utf-8")
    fake.chmod(0o755)
    return {"HOME": str(tmp_path), "LATTICE_SETUP_LOGS": str(tmp_path / "logs"), "PATH": f"{bin_dir}:/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(ROOT)}


def ran(tmp_path: Path) -> list[str]:
    return (tmp_path / "ran").read_text(encoding="utf-8").split() if (tmp_path / "ran").exists() else []


def wait_for_background(tmp_path: Path) -> None:
    pid = (tmp_path / "logs/deferred.pid").read_text(encoding="utf-8").strip()
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and subprocess.run(["kill", "-0", pid], capture_output=True).returncode == 0:
        time.sleep(0.05)


@pytest.mark.parametrize("remote, runs", [("", False), ("false", False), ("true", True)])
def test_vm7_03_the_session_hook_runs_in_a_cloud_session_only(tmp_path, remote, runs):
    settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    done = subprocess.run(["bash", "-c", command], env={**session_env(tmp_path), "CLAUDE_CODE_REMOTE": remote}, capture_output=True, text=True)
    assert done.returncode == 0 and ("bootstrap:vyvid" in ran(tmp_path)) is runs


def test_vm8_01_a_session_with_nothing_deferred_only_keeps_the_pin(tmp_path):
    done = subprocess.run(["bash", str(SETUP), "--session"], env=session_env(tmp_path), capture_output=True, text=True)
    assert done.returncode == 0 and done.stdout == "" and ran(tmp_path) == ["bootstrap:vyvid"]


def test_vm8_02_a_session_finishes_what_setup_deferred_and_says_so(tmp_path):
    (tmp_path / ".lattice-setup-deferred").write_text("bootstrap:dependencies\nbootstrap:testing-oxigraph\n", encoding="utf-8")
    done = subprocess.run(["bash", str(SETUP), "--session"], env=session_env(tmp_path), capture_output=True, text=True)
    wait_for_background(tmp_path)
    assert done.returncode == 0 and "bootstrap:dependencies bootstrap:testing-oxigraph" in done.stdout and "index is ready" in done.stdout
    assert ran(tmp_path) == ["bootstrap:vyvid", "bootstrap:dependencies", "bootstrap:testing-oxigraph"]
    assert not (tmp_path / ".lattice-setup-deferred").exists()


def test_vm8_06_a_task_that_reads_standard_input_cannot_eat_the_deferred_list(tmp_path):
    env = session_env(tmp_path)
    fake = Path(env["PATH"].split(":")[0]) / "mise"
    fake.write_text(f"#!/bin/sh\ncat > /dev/null\necho \"$2\" >> {tmp_path}/ran\n", encoding="utf-8")
    (tmp_path / ".lattice-setup-deferred").write_text("bootstrap:testing-oxigraph\nbootstrap:frontend\n", encoding="utf-8")
    subprocess.run(["bash", str(SETUP), "--finish-deferred"], env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
    assert ran(tmp_path) == ["bootstrap:testing-oxigraph", "bootstrap:frontend"]
    assert not (tmp_path / ".lattice-setup-deferred").exists()


def test_vm8_03_a_deferred_task_that_fails_stays_deferred(tmp_path):
    (tmp_path / ".lattice-setup-deferred").write_text("bootstrap:dependencies\n", encoding="utf-8")
    subprocess.run(["bash", str(SETUP), "--session"], env=session_env(tmp_path, mise_exit=1), capture_output=True, text=True)
    wait_for_background(tmp_path)
    assert (tmp_path / ".lattice-setup-deferred").read_text(encoding="utf-8") == "bootstrap:dependencies\n"


@pytest.mark.parametrize("seconds, starts", [(10, True), (149, True), (150, False), (400, False)])
def test_vm8_04_a_step_starts_only_before_its_limit(tmp_path, seconds, starts):
    later = re.search(r"^later\(\) \{.*?^\}\n", SETUP.read_text(encoding="utf-8"), re.M | re.S).group(0)
    script = f'log() {{ :; }}\nstep() {{ echo "$1" > {tmp_path}/started; }}\nDEFERRED={tmp_path}/deferred\n{later}SECONDS={seconds}\nlater 150 dependencies bootstrap:dependencies\n'
    subprocess.run(["bash", "-c", script], check=True)
    assert (tmp_path / "started").exists() is starts
    assert (tmp_path / "deferred").exists() is not starts


def test_vm8_05_the_index_needs_no_task_the_rest_of_bootstrap_installs():
    tasks = tomllib.loads((ROOT / "mise.toml").read_text(encoding="utf-8"))["tasks"]
    assert set(tasks["bootstrap:index-packages"]["depends"]) == {"bootstrap:pip", "bootstrap:vyvid"}
    assert "depends" not in tasks["build:knowledge"], "it runs beside bootstrap:dependencies, so it must not start a second pip"
    assert set(tasks["bootstrap:dependencies"]["depends"]) | {"bootstrap:knowledge", "bootstrap:vyvid"} == set(tasks["bootstrap"]["depends"])
