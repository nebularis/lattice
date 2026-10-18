# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The repository catalogue and its reader (ADR-A121, slice RC1).
Validation Pack: docs/developer/validation/RC1.md. Test IDs are RC1-Tn."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import import_guard  # noqa: E402
import lattice_repo_catalogue as rc  # noqa: E402
import literate_extract  # noqa: E402
import literate_grammar  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FENCE = "```"


def _tree(tmp: Path, entry: str = 'kind = "substrate"\nroles = ["spec"]\nimports = []', *, modules: str = '["alpha"]',
          extra_root: str = "", dirs: tuple[str, ...] = ("spec",)) -> Path:
    """A minimal repository: the root file and one module, alpha, with the given entry."""
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "repository-catalogue.md").write_text(
        f"# Catalogue\n\n{FENCE}toml repository-catalogue\n[conventions]\nroles = [\"spec\", \"vocab\", \"shapes\"]\n"
        f"[conventions.kinds]\nsubstrate = \"a layer\"\n{extra_root}\n[catalogue]\nschema = 1\nmodules = {modules}\n{FENCE}\n",
        encoding="utf-8",
    )
    module = tmp / "ontology" / "alpha"
    for d in dirs:
        (module / d).mkdir(parents=True, exist_ok=True)
    module.mkdir(parents=True, exist_ok=True)
    (module / "README.md").write_text(f"# Alpha\n\n{FENCE}toml repository-catalogue\n[module]\n{entry}\n{FENCE}\n", encoding="utf-8")
    return tmp


# ---- the real catalogue


def test_rc1_t1_the_catalogue_lists_every_module_in_order() -> None:
    catalogue = rc.load(ROOT)
    names = list(catalogue.modules)
    assert names[:8] == ["foundation", "vocabulary", "quantification", "party", "eligibility", "wording", "behaviour", "instrument"]
    assert len(names) == 19 and names[-1] == "governance"
    assert catalogue.module("instrument").files("shapes") == tuple(
        Path("ontology/instrument/shapes") / f for f in ("structural.ttl", "constraints.ttl", "single-expression.ttl")
    )


def test_rc1_t2_the_catalogue_agrees_with_the_tree() -> None:
    assert rc.check(rc.load(ROOT)) == []


@pytest.mark.parametrize("name", [m.name for m in rc.load(ROOT).modules.values() if m.literate])
def test_rc1_t3_each_extraction_contract_is_what_its_readme_generates(name: str) -> None:
    module = rc.load(ROOT).module(name)
    readme = ROOT / module.path / "README.md"
    text = readme.read_text(encoding="utf-8")
    result = literate_extract.scan(text)
    shapes = literate_extract.contract_shapes(result.blocks, name, readme)
    # A README in the layout compiles its documents' openings and its structural shapes (OD6 onwards).
    compiled = literate_grammar.compile_layout(text, result, name) if literate_extract.uses_layout(result.sections) else None
    outputs = literate_extract.plan(result.blocks, name, shapes, proofs_root="proofs", reference_root="reference",
                                    preambles=compiled and compiled.documents, generated_shapes=compiled and compiled.shapes)
    generated = {Path(p) for p in outputs if not p.startswith("@")}
    declared = {f for role in rc.EXTRACT_KEYS for f in module.files(role)}
    assert generated == declared


# ADR-A01 and its 2026-10-01 addendum, written out here so that an edit to the catalogue's order
# fails a test until the ADR is amended (ADR-A121 decision 2). The import guard reads the same
# entries since RC2.
_LOWER = ("foundation", "vocabulary", "quantification", "party", "eligibility")
ADR_A01_ORDER = {
    "foundation": frozenset(), "vocabulary": frozenset(_LOWER[:1]), "quantification": frozenset(_LOWER[:2]),
    "party": frozenset(_LOWER[:3]), "eligibility": frozenset(_LOWER[:4]), "wording": frozenset(_LOWER),
    "behaviour": frozenset(_LOWER), "instrument": frozenset(_LOWER) | {"wording", "behaviour"},
}


def test_rc1_t4_the_substrate_imports_are_adr_a01s_order_and_the_import_guard_reads_them() -> None:
    catalogue = rc.load(ROOT)
    substrate = {m.name: frozenset(m.imports or ()) for m in catalogue.modules_of_kind("substrate")}
    assert substrate == ADR_A01_ORDER == import_guard.ALLOWED
    assert all(m.imports is None for m in catalogue.modules.values() if m.kind != "substrate")


# ---- root discovery


def test_rc1_t5_the_root_is_found_from_below_from_the_environment_or_given(tmp_path: Path, monkeypatch) -> None:
    root = _tree(tmp_path / "repo")
    monkeypatch.delenv("LATTICE_ROOT", raising=False)
    monkeypatch.chdir(root / "ontology" / "alpha" / "spec")
    assert rc.find_root() == root.resolve()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(rc.CatalogueError, match="LATTICE_ROOT"):
        rc.find_root()
    monkeypatch.setenv("LATTICE_ROOT", str(root))
    assert rc.find_root() == root.resolve()
    assert rc.find_root(root / "ontology") == (root / "ontology").resolve()


# ---- what the reader and the check refuse


def test_rc1_t6_a_block_shown_inside_another_fence_is_not_read() -> None:
    text = f"````markdown\n{FENCE}toml repository-catalogue\n[module]\n{FENCE}\n````\n{FENCE}toml repository-catalogue\nx = 1\n{FENCE}\n"
    assert rc.blocks(text) == ["x = 1"]


@pytest.mark.parametrize("entry,dirs,message", [
    ('kind = "substrate"\nroles = ["spec", "vocab"]\nimports = []', ("spec",), "declares role 'vocab'"),
    ('kind = "substrate"\nroles = ["spec"]\nimports = []', ("spec", "shapes"), "is not one of its roles"),
    ('kind = "substrate"\nroles = ["spec"]\nimports = ["omega"]', ("spec",), "which is not a module"),
    ('kind = "substrate"\nroles = ["spec"]\n[module.extract]\nspec = ["spec/alpha.ttl"]', ("spec",), "which does not exist"),
])
def test_rc1_t7_the_check_finds_where_the_tree_and_an_entry_disagree(tmp_path: Path, entry: str, dirs, message: str) -> None:
    root = _tree(tmp_path, entry, dirs=dirs)
    assert any(message in p for p in rc.check(rc.load(root)))


def test_rc1_t8_a_module_on_disk_that_is_not_listed_is_found(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "ontology" / "beta" / "spec").mkdir(parents=True)
    (root / "ontology" / "beta" / "README.md").write_text("# Beta\n", encoding="utf-8")
    assert rc.check(rc.load(root)) == ["ontology/beta holds a module, but is not in the catalogue"]


@pytest.mark.parametrize("entry,message", [
    ('kind = "substrate"\nroles = ["spec"]\ncolour = "red"', "unknown key"),
    ('kind = "planet"\nroles = ["spec"]', "is not one of the conventions' kinds"),
    ('kind = "substrate"\nroles = "spec"', "must be a list of strings"),
    ('kind = "substrate"\nroles = ["spec"]\n[module.extract]\ndocs = ["docs/x.md"]', "unknown extracted role"),
    (f'kind = "substrate"\nroles = ["spec"]\n{FENCE}\n\n{FENCE}toml repository-catalogue\n[module]\nkind = "substrate"', "defined twice"),
    ('kind = "substrate"\nroles = [', "does not parse"),
])
def test_rc1_t9_a_malformed_entry_is_refused(tmp_path: Path, entry: str, message: str) -> None:
    with pytest.raises(rc.CatalogueError, match=message):
        rc.load(_tree(tmp_path, entry))


def test_rc1_t10_a_listed_module_without_an_entry_or_a_readme_is_refused(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "ontology" / "alpha" / "README.md").write_text("# Alpha, with no entry\n", encoding="utf-8")
    with pytest.raises(rc.CatalogueError, match="needs one catalogue entry"):
        rc.load(root)
    with pytest.raises(rc.CatalogueError, match="does not exist"):
        rc.load(_tree(tmp_path / "other", modules='["alpha", "gamma"]'))
    with pytest.raises(rc.CatalogueError, match="unknown key"):
        rc.load(_tree(tmp_path / "third", extra_root="[sites]\nx = 1"))


# ---- the command line


def test_rc1_t11_the_command_line_prints_paths_in_order_and_names_a_missing_role(capsys) -> None:
    assert rc.main(["--root", str(ROOT), "paths", "instrument", "shapes"]) == 0
    assert capsys.readouterr().out.split() == [
        "ontology/instrument/shapes/structural.ttl", "ontology/instrument/shapes/constraints.ttl",
        "ontology/instrument/shapes/single-expression.ttl",
    ]
    assert rc.main(["--root", str(ROOT), "path", "party", "projection"]) == 0
    assert capsys.readouterr().out.strip() == "ontology/party/projection"
    assert rc.main(["--root", str(ROOT), "path", "vocabulary", "vocab"]) == 1
    assert "declare it in the roles of the catalogue entry in ontology/vocabulary/README.md" in capsys.readouterr().err
    assert rc.main(["--root", str(ROOT), "dump", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["modules"]["behaviour"]["kind"] == "substrate"
    assert rc.main(["--root", str(ROOT), "check"]) == 0


# ---- RC2: the tools read the catalogue ------------------------------------------------------

import check_formal_freshness  # noqa: E402
import ontology_version_check  # noqa: E402


def test_rc2_t1_the_extractor_takes_no_shapes_argument(capsys) -> None:
    with pytest.raises(SystemExit):
        literate_extract.main([str(ROOT / "ontology/wording/README.md"), "--layer", "wording", "--shapes", "x.ttl"])
    assert "--shapes" in capsys.readouterr().err


def test_rc2_t2_the_extractor_reads_a_modules_shape_files_from_its_entry() -> None:
    blocks = literate_extract.parse_blocks((ROOT / "ontology/instrument/README.md").read_text(encoding="utf-8"))
    assert literate_extract.contract_shapes(blocks, "instrument") == [
        "shapes/structural.ttl", "shapes/constraints.ttl", "shapes/single-expression.ttl",
    ]


def test_rc2_t3_a_readme_needs_the_catalogue_only_for_a_shape_block_that_names_no_file(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("LATTICE_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    named = literate_extract.parse_blocks(f'{FENCE}turtle-shapes\n# @output-file "shapes/a.ttl"\nex:S a sh:NodeShape .\n{FENCE}\n')
    assert literate_extract.contract_shapes(named, "nowhere") == []
    readme = tmp_path / "README.md"
    readme.write_text(f"{FENCE}turtle-shapes\nex:S a sh:NodeShape .\n{FENCE}\n", encoding="utf-8")
    assert literate_extract.main([str(readme), "--layer", "nowhere", "--root", str(tmp_path), "--check"]) == 1
    assert "CATALOGUE" in capsys.readouterr().err


def test_rc2_t4_the_versioning_check_reads_its_directories_from_the_conventions() -> None:
    conventions = rc.load(ROOT).conventions
    assert ontology_version_check.VERSIONED_DIRECTORIES == frozenset(conventions["versioned"]) == {"spec", "vocab"}
    assert ontology_version_check.ARTEFACT_DIRECTORIES == tuple(conventions["artefact-directories"]) == ("shapes", "projection")


def test_rc2_t5_the_freshness_check_extracts_with_the_contract_and_names_a_directory_with_no_readme() -> None:
    assert check_formal_freshness.check_kernel_freshness("eligibility") == []
    assert "no README" in check_formal_freshness.check_kernel_freshness("nowhere")[0]


# Where a command for the extractor is written for people or for continuous integration. Historical
# records (plans, status records, Validation Packs, sketches, notes) keep the commands they ran.
COMMAND_DOCUMENTS = (
    [ROOT / "tools/README.md", ROOT / "tools/proofs/README.md", ROOT / "docs/developer/developer-guide.md",
     ROOT / "docs/book.html", ROOT / "docs/architecture/ontology-versioning-policy.md",
     ROOT / ".claude/skills/lattice-ontology-authoring/SKILL.md"]
    + sorted((ROOT / ".github/workflows").glob("*.yml"))
    + sorted((ROOT / "ontology").glob("**/README.md"))
)


@pytest.mark.parametrize("document", COMMAND_DOCUMENTS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_rc2_t6_no_command_passes_the_removed_shapes_argument(document: Path) -> None:
    assert "--shapes " not in document.read_text(encoding="utf-8")


def test_rc2_t7_the_extractor_finds_the_catalogue_above_its_readme_from_any_directory(tmp_path: Path, monkeypatch) -> None:
    """RC2-C1 option (c): the catalogue is the nearest one above the README, not the working directory's."""
    monkeypatch.delenv("LATTICE_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    readme = ROOT / "ontology" / "wording" / "README.md"
    assert rc.root_above(readme) == ROOT.resolve() and rc.root_above(tmp_path) is None
    assert literate_extract.main([str(readme), "--layer", "wording", "--root", str(ROOT), "--check"]) == 0
