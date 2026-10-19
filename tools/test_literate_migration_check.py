# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The migration check (ADR-A126, slice OD6, OD-D33).
Validation Pack: docs/developer/validation/OD6.md. Test IDs are OD6-Tn."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import literate_migration_check as mc  # noqa: E402

FENCE = "```"
SPEC = "@prefix ex: <https://example.org/x#> .\nex:A a ex:C ; ex:p [ ex:q 1 ] .\n"


def test_od6_t6_a_reordered_relabelled_graph_has_no_difference_and_a_changed_triple_has_two() -> None:
    reordered = "@prefix ex: <https://example.org/x#> .\nex:A ex:p [ ex:q 1 ] .\nex:A a ex:C .\n"
    assert mc.differences("f.ttl", SPEC, reordered) == []
    changed = mc.differences("f.ttl", SPEC, SPEC.replace("ex:C", "ex:D"))
    assert [line.split()[1] for line in changed] == ["only-at-ref", "only-in-tree"]
    assert mc.differences("f.ttl", None, SPEC) == ["f.ttl added in the tree"]


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repository(root: Path) -> Path:
    (root / "ontology/alpha/spec").mkdir(parents=True)
    (root / "repository-catalogue.md").write_text(
        f'{FENCE}toml repository-catalogue\n[conventions]\nroles = ["spec"]\n[conventions.kinds]\nsubstrate = "a layer"\n'
        f'[catalogue]\nschema = 1\nmodules = ["alpha"]\n{FENCE}\n', encoding="utf-8")
    (root / "ontology/alpha/README.md").write_text(
        f'{FENCE}toml repository-catalogue\n[module]\nkind = "substrate"\nroles = ["spec"]\n[module.extract]\n'
        f'spec = ["spec/alpha.ttl"]\n{FENCE}\n', encoding="utf-8")
    (root / "ontology/alpha/spec/alpha.ttl").write_text(SPEC, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "-c", "user.email=test@example.org", "-c", "user.name=test", "add", ".")
    _git(root, "-c", "user.email=test@example.org", "-c", "user.name=test", "commit", "-q", "-m", "base")
    return root


def test_od6_t7_the_check_fails_on_a_change_and_passes_once_it_is_reconciled(tmp_path: Path, capsys) -> None:
    root = _repository(tmp_path)
    args = ["alpha", "HEAD", "--root", str(root)]
    assert mc.main(args) == 0
    spec = root / "ontology/alpha/spec/alpha.ttl"
    spec.write_text(SPEC.replace("ex:C", "ex:D"), encoding="utf-8")
    capsys.readouterr()
    assert mc.main(args) == 1
    lines = [line.removeprefix("MIGRATION unreconciled: ") for line in capsys.readouterr().err.splitlines()
             if line.startswith("MIGRATION unreconciled: ")]
    assert len(lines) == 2
    reconciliations = tmp_path / "reconciliations.txt"
    reconciliations.write_text("# approved\n" + "\n".join(lines) + "\n", encoding="utf-8")
    assert mc.main([*args, "--reconciliations", str(reconciliations)]) == 0
    spec.write_text(SPEC, encoding="utf-8")
    capsys.readouterr()
    assert mc.main([*args, "--reconciliations", str(reconciliations)]) == 1
    assert "no longer applies" in capsys.readouterr().err


def test_elc_t1_a_multi_line_literal_is_one_difference_on_one_line() -> None:
    query = '@prefix ex: <https://example.org/x#> .\nex:S ex:select """\nSELECT $this\nWHERE { }\n""" .\n'
    changed = mc.differences("f.ttl", query, query.replace("WHERE", "where"))
    assert len(changed) == 2 and all("\n" not in line and "\\n" in line for line in changed)
