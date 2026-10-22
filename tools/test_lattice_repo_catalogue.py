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
    assert names[:9] == ["foundation", "vocabulary", "quantification", "ledger", "party", "eligibility", "wording", "behaviour", "instrument"]
    assert len(names) == 20 and names[-1] == "governance"
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


# ADR-A01 and its 2026-10-01 and 2026-10-19 addenda, written out here so that an edit to the
# catalogue's order fails a test until the ADR is amended (ADR-A121 decision 2). The import guard
# reads the same entries since RC2.
_LOWER = ("foundation", "vocabulary", "quantification", "party", "eligibility")
ADR_A01_ORDER = {
    "foundation": frozenset(), "vocabulary": frozenset(_LOWER[:1]), "quantification": frozenset(_LOWER[:2]),
    "ledger": frozenset(_LOWER[:3]),
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


# ---- RC3: roots, tool packages, documentation areas, generated paths, the table and the bypass scan --------

import shutil  # noqa: E402

import agent_guidance  # noqa: E402

# AGENTS.md's "Where things are" table at commit 82fc2b25, before it was generated.
TABLE_AT_82FC2B25 = """\
| Root | Owns |
|---|---|
| `ontology/` | semantic assets only: sources, shapes, vocabularies, projections, examples, their documentation |
| `tools/` | executable reference implementations and developer toolchains. `tools/testing/` holds test-support packages, used only by tests, checks and benchmarks (ADR-A125) |
| `benchmark/` | checks that measure, run on demand and never part of `check`. They fail on a wrong result, never on time (ADR-A124) |
| `platform/`, `apps/`, `packages/`, `contracts/`, `deployment/`, `workers/`, `test/`, `spikes/` | services, applications, libraries, data contracts, the local environment, the worker runtime, end-to-end suites, experiments |
| `docs/architecture/` | architecture documents and the ADRs, in `decisions/` |
| `docs/developer/` | sketches, plans, status records, review requests, Validation Packs, and durable guidance |
| `.claude/skills/` | the skills below |"""

AREA = '[[roots]]\npath = "tools/"\nowns = "tools"\nrow = "tool row"\n'


def _write(root: Path, relative: str, text: str) -> None:
    (root / relative).parent.mkdir(parents=True, exist_ok=True)
    (root / relative).write_text(text, encoding="utf-8")


def test_rc3_t1_the_catalogue_declares_the_roots_tool_packages_documentation_areas_and_generated_paths() -> None:
    catalogue = rc.load(ROOT)
    assert [a.path for a in catalogue.roots][:3] == ["ontology/", "tools/", "benchmark/"] and len(catalogue.roots) == 11
    assert [a.path for a in catalogue.docs] == ["docs/architecture/", "docs/developer/", ".claude/skills/"]
    assert sorted(t.path for t in catalogue.tools) == sorted(
        p.parent.relative_to(ROOT).as_posix() for p in (ROOT / "tools").rglob("pyproject.toml") if ".venv" not in p.parts
    )
    assert catalogue.is_generated(".build/full-sweep") and catalogue.is_generated("docs/_site/")
    assert not catalogue.is_generated("docs/architecture/")
    assert rc.check(catalogue) == []


@pytest.mark.parametrize("extra,message", [
    ('[[roots]]\npath = "tools/"\nowns = "x"\nrow = "r"\ncolour = "red"', "unknown key"),
    ('[[roots]]\nowns = "x"\nrow = "r"', "needs 'path'"),
    ('[[roots]]\npath = "tools/"\nowns = 3\nrow = "r"', "must be a string"),
    ('[[roots]]\npath = "tools/"\nowns = "x"\nrow = "r"\nadrs = "ADR-A01"', "must be a list of strings"),
    ('[[roots]]\npath = "tools/"\nowns = "x"', "needs 'row'"),
    ('[[roots]]\npath = "a/"\nowns = "x"\ngroup = "g"\nrow = "r"\n[[roots]]\npath = "b/"\nowns = "x"\ngroup = "g"\nrow = "r"',
     "takes no 'row'"),
    ('[[roots]]\npath = "a/"\nowns = "x"\ngroup = "g"\nrow = "r"\n[[roots]]\npath = "b/"\nowns = "x"\nrow = "r"\n'
     '[[roots]]\npath = "c/"\nowns = "x"\ngroup = "g"\nrow = "r"', "next to each other"),
    ('[roots]\npath = "tools/"', "list of tables"),
    ('[[docs]]\npath = "docs/"\nowns = "x"\nrow = "r"\nname = "n"', "unknown key"),
    ('[[tools]]\nname = "t"\npath = "tools/t"', "needs 'import-names'"),
    ('[[tools]]\nname = "t"\npath = "tools/t"\nimport-names = ["t"]\nreaches = "ontology"', "must be a list of strings"),
    ('[[tools]]\nname = "t"\npath = "tools/t"\nimport-names = ["t"]\nversion = "1"', "unknown key"),
    ('[generated]\npaths = [".build/"]\nkind = "x"', "unknown key"),
    ('[generated]\npaths = ".build/"', "must be a list of strings"),
])
def test_rc3_t2_a_malformed_block_is_refused(tmp_path: Path, extra: str, message: str) -> None:
    with pytest.raises(rc.CatalogueError, match=message):
        rc.load(_tree(tmp_path, extra_root=extra))


def test_rc3_t3_a_declared_path_that_is_missing_is_found_unless_it_is_generated(tmp_path: Path) -> None:
    tool = '[[tools]]\nname = "t"\npath = "tools/t"\nimport-names = ["t"]\nreaches = ["out/jar"]\n'
    root = _tree(tmp_path, extra_root=AREA + tool)
    problems = "\n".join(rc.check(rc.load(root)))
    assert "roots entry tools/ does not exist" in problems and "tool package t: tools/t does not exist" in problems
    assert "reaches out/jar does not exist" in problems
    (root / "tools" / "t").mkdir(parents=True)
    assert "has no pyproject.toml" in "\n".join(rc.check(rc.load(root)))
    _write(root, "tools/t/pyproject.toml", "")
    generated = AREA + tool + '[generated]\npaths = ["out/"]\n'
    assert rc.check(rc.load(_tree(tmp_path, extra_root=generated))) == []


def test_rc3_t4_a_tool_package_on_disk_that_is_not_declared_is_found(tmp_path: Path) -> None:
    tool = '[[tools]]\nname = "t"\npath = "tools/t"\nimport-names = ["t"]\n'
    root = _tree(tmp_path, extra_root=AREA + tool)
    _write(root, "tools/t/pyproject.toml", "")
    _write(root, "tools/deep/u/pyproject.toml", "")
    _write(root, "tools/.venv/v/pyproject.toml", "")
    assert rc.check(rc.load(root)) == ["tools/deep/u is a tool package (it has a pyproject.toml), but is not in the catalogue's tools"]


def test_rc3_t5_the_generated_table_is_the_table_before_it_was_generated() -> None:
    table = rc.where_things_are(rc.load(ROOT))
    assert table == TABLE_AT_82FC2B25
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert agents.count(TABLE_AT_82FC2B25) == 1
    assert agents.index(agent_guidance.REGION_BEGIN) < agents.index(TABLE_AT_82FC2B25) < agents.index(agent_guidance.REGION_END)


def test_rc3_t6_an_edit_inside_the_region_is_stale_and_a_rebuild_repairs_it(tmp_path: Path) -> None:
    for name in ("AGENTS.md", "repository-catalogue.md", ".github/copilot-instructions.md", ".claude-plugin/marketplace.json"):
        _write(tmp_path, name, (ROOT / name).read_text(encoding="utf-8"))
    shutil.copytree(ROOT / ".claude/skills", tmp_path / ".claude/skills")
    shutil.copytree(ROOT / "ontology", tmp_path / "ontology", ignore=lambda d, names: [
        n for n in names if not (Path(d, n).is_dir() or n == "README.md")])
    def table_problems() -> list[str]:  # the copy has no docs/, so its links do not resolve and are not the point
        return [p for p in agent_guidance.check(tmp_path) if "Where things are" in p]

    assert table_problems() == []
    agents = tmp_path / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8").replace("the skills below", "the skills"), encoding="utf-8")
    assert "is stale" in "".join(table_problems())
    table = rc.where_things_are(rc.load(tmp_path))
    agents.write_text(agent_guidance.render_agents(agents.read_text(encoding="utf-8"), table), encoding="utf-8")
    assert table_problems() == []


def test_rc3_t7_the_region_needs_both_markers_once() -> None:
    table = rc.where_things_are(rc.load(ROOT))
    begin, end = agent_guidance.REGION_BEGIN, agent_guidance.REGION_END
    for text in ("no region", f"{end}\n{begin}", f"{begin}\n{begin}\n{end}", f"{begin}\n{end}\n{end}"):
        with pytest.raises(ValueError, match="generated 'Where things are' region"):
            agent_guidance.render_agents(text, table)
    once = f"before\n{begin}\nold\n{end}\nafter\n"
    assert agent_guidance.render_agents(agent_guidance.render_agents(once, table), table).count(table) == 1


def test_rc3_t8_a_group_is_one_row_and_a_row_without_a_group_is_its_own(tmp_path: Path) -> None:
    extra = (
        '[[roots]]\npath = "a/"\nowns = "x"\nrow = "alone"\n[[roots]]\npath = "b/"\nowns = "x"\ngroup = "g"\nrow = "pair"\n'
        '[[roots]]\npath = "c/"\nowns = "x"\ngroup = "g"\n[[docs]]\npath = "d/"\nowns = "x"\nrow = "last"\n'
    )
    assert rc.where_things_are(rc.load(_tree(tmp_path, extra_root=extra))) == (
        "| Root | Owns |\n|---|---|\n| `a/` | alone |\n| `b/`, `c/` | pair |\n| `d/` | last |"
    )


# The bypass scan. A repository with roots ontology/ and docs/, tool files and a debt register.


def _scanned(tmp: Path, *, files: dict[str, str], exceptions: str, count: int | None) -> Path:
    extra = '[[roots]]\npath = "ontology/"\nowns = "o"\nrow = "r"\n[[roots]]\npath = "docs/"\nowns = "d"\nrow = "r2"\n'
    root = _tree(tmp, extra_root=extra)
    (root / "docs").mkdir()
    for name, text in files.items():
        _write(root, name, text)
    _write(root, rc.EXCEPTIONS_FILE, exceptions)
    row = "" if count is None else f"| TD-1 | `lattice_repo_catalogue_exceptions.txt` lists {count} files |\n"
    _write(root, rc.DEBT_FILE, f"| # | Debt |\n|---|---|\n{row}")
    return root


BYPASS = 'from pathlib import Path\nROOT = Path(__file__).parent\nSPEC = ROOT / "ontology" / "alpha"\n'
CLEAN = 'from pathlib import Path\nSPEC = Path(".") / "elsewhere"\n'


def test_rc3_t9_a_planted_bypass_is_found_and_names_the_file_and_the_remedy(tmp_path: Path) -> None:
    root = _scanned(tmp_path, files={"tools/bad.py": BYPASS, "tools/ok.py": CLEAN}, exceptions="", count=0)
    assert rc.bypass_scan(rc.load(root)).found == {"tools/bad.py": 1}
    problems = rc.check(rc.load(root))
    assert len(problems) == 1 and "tools/bad.py builds a path to a catalogued root 1 time(s)" in problems[0]
    assert rc.EXCEPTIONS_FILE in problems[0]


@pytest.mark.parametrize("source,count", [
    ('x = base / "ontology"', 1), ('x = Path("ontology/alpha")', 1), ('x = pathlib.Path("docs") / "a"', 1),
    ('x = base / "ontology" / "alpha" / "docs"', 2), ('x = base / "other"', 0), ('x = Path(name) / name', 0),
    ('x = "ontology"', 0), ('x = Path("ontologies")', 0),
])
def test_rc3_t10_the_scan_counts_path_constructions_naming_a_root(source: str, count: int) -> None:
    assert rc.count_bypasses(source, frozenset({"ontology", "docs"})) == count


def test_rc3_t11_a_listed_exception_is_reported_and_does_not_fail(tmp_path: Path) -> None:
    root = _scanned(tmp_path, files={"tools/bad.py": BYPASS}, exceptions="# a comment\n\ntools/bad.py | predates the catalogue\n", count=1)
    scan = rc.bypass_scan(rc.load(root))
    assert scan.known == {"tools/bad.py": "predates the catalogue"} and scan.found == {"tools/bad.py": 1}
    assert rc.check(rc.load(root)) == []


def test_rc3_t12_a_fixed_exception_fails_until_it_is_removed_from_the_list(tmp_path: Path) -> None:
    root = _scanned(tmp_path, files={"tools/bad.py": CLEAN}, exceptions="tools/bad.py | predates the catalogue\n", count=1)
    assert rc.check(rc.load(root)) == [f"{rc.EXCEPTIONS_FILE} lists tools/bad.py, which no longer builds such a path. Remove it from the list"]
    _write(root, rc.EXCEPTIONS_FILE, "")
    _write(root, rc.DEBT_FILE, "| TD-1 | `lattice_repo_catalogue_exceptions.txt` lists 0 files |\n")
    assert rc.check(rc.load(root)) == []


@pytest.mark.parametrize("count,message", [
    (2, "must say 'lists 1 files', and lists 2 files"),
    (None, "needs one row that names lattice_repo_catalogue_exceptions.txt"),
])
def test_rc3_t13_a_debt_row_with_the_wrong_count_or_no_row_fails(tmp_path: Path, count, message: str) -> None:
    root = _scanned(tmp_path, files={"tools/bad.py": BYPASS}, exceptions="tools/bad.py | a reason\n", count=count)
    problems = rc.check(rc.load(root))
    assert len(problems) == 1 and message in problems[0]
    _write(root, rc.DEBT_FILE, "| TD-1 | `lattice_repo_catalogue_exceptions.txt` is long |\n")
    assert "gives no count" in "\n".join(rc.check(rc.load(root)))


def test_rc3_t14_an_exception_needs_a_reason_and_is_listed_once(tmp_path: Path) -> None:
    root = _scanned(tmp_path, files={"tools/bad.py": BYPASS}, exceptions="tools/bad.py\ntools/bad.py | r\ntools/bad.py | r\n", count=1)
    problems = "\n".join(rc.check(rc.load(root)))
    assert ":1: write 'path | reason'" in problems and ":3: tools/bad.py is listed twice" in problems


def test_rc3_t15_tests_and_the_reader_are_not_scanned(tmp_path: Path) -> None:
    names = ("test_a.py", "conftest.py", "pkg/tests/b.py", "lattice_repo_catalogue.py", "pkg/.venv/c.py", "pkg/node_modules/d.py")
    root = _scanned(tmp_path, files={f"tools/{n}": BYPASS for n in names}, exceptions="", count=0)
    assert rc.bypass_scan(rc.load(root)).found == {} and rc.check(rc.load(root)) == []


def test_rc3_t16_the_real_scan_lists_exactly_what_the_tools_build_and_the_reader_is_not_listed() -> None:
    scan = rc.bypass_scan(rc.load(ROOT))
    assert scan.problems == [] and set(scan.found) == set(scan.known) and len(scan.known) == 12
    assert "tools/lattice_repo_catalogue.py" not in scan.known
    assert all(not rc._is_test(Path(p)) for p in scan.known)


# RC3 review (2026-10-19): a package's declared reaches are what its Python reads or writes outside its tree.
import ast  # noqa: E402
import re  # noqa: E402

_ROOT_NAMES = {"ontology", "tools", "platform", "contracts", "test", "docs", "spikes", "apps", "packages",
               "deployment", "workers", "benchmark"}


def _path_parts(node: ast.AST) -> list[str]:
    """The string parts of a ``/`` chain or a ``Path(...)`` call, with ``?`` for anything computed."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _path_parts(node.left) + _path_parts(node.right)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", None)) == "Path":
        return [p for a in node.args for p in _path_parts(a)]
    return ["?"]


def _reached(parts: list[str]) -> str | None:
    """A path's first two segments from its first catalogued root on, if it names one."""
    segments = [s for p in parts if p != "?" for s in p.strip("/").split("/") if s]
    start = next((i for i, s in enumerate(segments) if s in _ROOT_NAMES), None)
    if start is None or len(segments) < start + 2 or not re.fullmatch(r"[\w.-]+", segments[start + 1]):
        return None
    return "/".join(segments[start:start + 2])


def derived_reaches(package: Path) -> set[str]:
    found: set[str] = set()
    for source in package.rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        docstrings = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr)}
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                parts = _path_parts(node)
            elif (isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
                  and "/" in node.value and not re.search(r"\s|^[a-z][\w+.-]*:", node.value)):
                parts = [node.value]
            else:
                continue
            reached = _reached(parts)
            if reached:
                found.add(reached)
    own = package.relative_to(ROOT).as_posix()
    return {r for r in found if not (r.startswith(own) or own.startswith(r))}


@pytest.mark.parametrize("tool", rc.load(ROOT).tools, ids=lambda t: t.name)
def test_rc3_t17_each_packages_reaches_are_what_its_code_reads(tool) -> None:
    assert derived_reaches(ROOT / tool.path) == set(tool.reaches)

