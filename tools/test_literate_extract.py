# SPDX-License-Identifier: MPL-2.0

"""The literate extractor's @output-file directive (ADR-A120, and its AIR-2.0 addendum for
nested modules and several vocabulary documents)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import literate_extract  # noqa: E402
from literate_extract import parse_blocks, plan  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

HEAD = """@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <https://example.org/x#> .

<https://example.org/x> a owl:Ontology ; owl:versionIRI <https://example.org/x/0.2.0> ."""

RUNTIME = """# @output-file "spec/x-runtime.ttl"
<https://example.org/x-runtime> a owl:Ontology ; owl:versionIRI <https://example.org/x-runtime/{v}> ."""

VOCAB_HEAD = """@prefix voc: <https://example.org/x/vocab#> .

<https://example.org/x/vocab> a owl:Ontology ; owl:versionIRI <https://example.org/x-vocab/0.1.0> ."""

VOCAB_EXTRA = """# @output-file "vocab/x-extra.ttl"
<https://example.org/x-extra> a owl:Ontology ; owl:versionIRI <https://example.org/x-extra/{v}> ."""


def _readme(*blocks: str) -> str:
    return "\n\n".join(f"```turtle-spec\n{b}\n```" for b in blocks)


def _mixed_readme(*tagged_blocks: tuple[str, str]) -> str:
    return "\n\n".join(f"```{tag}\n{body}\n```" for tag, body in tagged_blocks)


def test_directive_redirects_block_and_shares_prefixes() -> None:
    out = plan(parse_blocks(_readme(HEAD, RUNTIME.format(v="0.2.0"), "ex:A a owl:Class .")), "x", [])
    main, runtime = out["ontology/x/spec/x.ttl"], out["ontology/x/spec/x-runtime.ttl"]
    assert "ex:A a owl:Class" in main and "x-runtime" not in main
    assert "@output-file" not in runtime
    assert runtime.index("@prefix ex:") < runtime.index("<https://example.org/x-runtime>")


def test_directive_only_on_first_line() -> None:
    out = plan(parse_blocks(_readme(HEAD, "ex:A a owl:Class .\n" + RUNTIME.format(v="0.2.0"))), "x", [])
    assert list(out) == ["ontology/x/spec/x.ttl"]


def test_spec_documents_move_in_unison() -> None:
    with pytest.raises(ValueError, match="in unison"):
        plan(parse_blocks(_readme(HEAD, RUNTIME.format(v="0.3.0"))), "x", [])


@pytest.mark.parametrize("path", ["../y/spec/y.ttl", "/tmp/x.ttl", "spec/x.txt"])
def test_directive_stays_in_the_layer(path: str) -> None:
    with pytest.raises(ValueError, match="@output-file"):
        plan(parse_blocks(_readme(HEAD, f'# @output-file "{path}"\nex:B a owl:Class .')), "x", [])


# ---- AIR-2.0: nested modules and several vocabulary documents ----------------


def test_air20_01_nested_module_path_names_default_documents() -> None:
    readme = _mixed_readme(("turtle-spec", HEAD), ("turtle-vocab", VOCAB_HEAD))
    out = plan(parse_blocks(readme), "applied/insurance/peril", [])
    assert set(out) == {
        "ontology/applied/insurance/peril/spec/peril.ttl",
        "ontology/applied/insurance/peril/vocab/peril-vocab.ttl",
    }


def test_air20_02_vocab_directive_redirects_and_shares_prefixes() -> None:
    readme = _mixed_readme(
        ("turtle-spec", HEAD),
        ("turtle-vocab", VOCAB_HEAD),
        ("turtle-vocab", VOCAB_EXTRA.format(v="0.1.0")),
    )
    out = plan(parse_blocks(readme), "applied/insurance/peril", [])
    default_vocab = out["ontology/applied/insurance/peril/vocab/peril-vocab.ttl"]
    extra = out["ontology/applied/insurance/peril/vocab/x-extra.ttl"]
    assert "x-extra" not in default_vocab
    assert "@output-file" not in extra
    assert extra.index("@prefix voc:") < extra.index("<https://example.org/x-extra>")


def test_air20_03_vocabulary_documents_move_in_unison() -> None:
    readme = _mixed_readme(
        ("turtle-spec", HEAD),
        ("turtle-vocab", VOCAB_HEAD),
        ("turtle-vocab", VOCAB_EXTRA.format(v="0.2.0")),
    )
    with pytest.raises(ValueError, match="vocabulary documents carry different versions"):
        plan(parse_blocks(readme), "applied/insurance/peril", [])


@pytest.mark.parametrize("path", ["spec/x.ttl", "../y/vocab/y.ttl", "/tmp/x.ttl", "vocab/x.txt"])
def test_air20_04_vocab_directive_stays_in_the_modules_vocab(path: str) -> None:
    readme = _mixed_readme(
        ("turtle-spec", HEAD),
        ("turtle-vocab", VOCAB_HEAD),
        ("turtle-vocab", f'# @output-file "{path}"\nex:B a owl:Class .'),
    )
    with pytest.raises(ValueError, match="@output-file"):
        plan(parse_blocks(readme), "x", [])


# The literate layers whose README is the source of every file it generates. The shape files
# each takes come from its repository catalogue entry (ADR-A121).
LITERATE_LAYERS = ["foundation", "quantification", "wording", "behaviour", "instrument", "eligibility"]


@pytest.mark.parametrize("layer", LITERATE_LAYERS)
def test_air20_05_every_literate_layer_of_main_is_unchanged(layer: str) -> None:
    readme = ROOT / "ontology" / layer / "README.md"
    kwargs = ["--proofs-root", str(ROOT / "tools" / "proofs"), "--reference-root", str(ROOT / "tools" / "reference")] \
        if layer == "eligibility" else []
    assert literate_extract.main([str(readme), "--layer", layer, "--root", str(ROOT), *kwargs, "--check"]) == 0


# ---- ADR-A126, slice OD1: the fence- and marker-aware scanner, and the layout ----------
# Validation Pack: docs/developer/validation/OD1.md. Test IDs are OD1-Tn.

from literate_extract import layout_problems, scan  # noqa: E402

LEGACY_FENCE = __import__("re").compile(
    r"^```(?P<tag>turtle-spec|turtle-vocab|turtle-shapes|turtle-example|isabelle-spec)\s*$"
)


def _legacy_blocks(markdown: str) -> list[tuple[str, str, int]]:
    """The scanner before OD1, which knew only its own fences, kept to compare against."""
    lines, found, index = markdown.splitlines(), [], 0
    while index < len(lines):
        match = LEGACY_FENCE.match(lines[index])
        if match is None:
            index += 1
            continue
        end = index + 1
        while end < len(lines) and lines[end].rstrip() != "```":
            end += 1
        found.append((match.group("tag"), "\n".join(lines[index + 1:end]).rstrip() + "\n", index + 1))
        index = end + 1
    return found


READMES = sorted(p for p in (ROOT / "ontology").glob("**/README.md"))


@pytest.mark.parametrize("readme", READMES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_od1_t1_every_readme_scans_as_before(readme: Path) -> None:
    text = readme.read_text(encoding="utf-8")
    result = scan(text)
    assert [(b.tag, b.body, b.start_line) for b in result.blocks] == _legacy_blocks(text)
    assert result.regions == [] and not any(b.hidden or b.output_file for b in result.blocks)


def test_od1_t2_a_tagged_fence_inside_another_fence_is_text() -> None:
    text = "````markdown\n```turtle-spec\nex:A a owl:Class .\n```\n<!-- start: {\"exclude\": true} -->\n````\n"
    assert scan(text).blocks == [] and scan(text).regions == []


def test_od1_t3_a_tagged_fence_inside_an_ordinary_comment_is_not_extracted() -> None:
    assert scan("<!-- end of a table -->\n<!-- hidden things below -->\n").regions == []
    text = "<!-- commented out\n```turtle-spec\nex:A a owl:Class .\n```\n-->\n```turtle-spec\nex:B a owl:Class .\n```\n"
    assert [b.body for b in scan(text).blocks] == ["ex:B a owl:Class .\n"]


def test_od1_t4_a_hidden_block_is_extracted_to_its_output_file() -> None:
    text = _readme(HEAD) + '\n\n<!-- hidden: {"output-file": "spec/x-runtime.ttl"}\n\n```turtle-spec\n' \
        + "<https://example.org/x-runtime> a owl:Ontology ; owl:versionIRI <https://example.org/x-runtime/0.2.0> .\n```\n\n-->\n"
    blocks = parse_blocks(text)
    assert blocks[1].hidden and blocks[1].output_file == "spec/x-runtime.ttl"
    out = plan(blocks, "x", [])
    assert "x-runtime" in out["ontology/x/spec/x-runtime.ttl"] and "x-runtime" not in out["ontology/x/spec/x.ttl"]


def test_od1_t5_an_end_marker_closes_the_innermost_region() -> None:
    text = ('<!-- start: {"output-file": "spec/x-runtime.ttl"} -->\n<!-- start: {"exclude": true} -->\ntext\n'
            '<!-- end -->\n<!-- start: {"generated": "axiom-index"} -->\n<!-- end -->\n<!-- end -->\n')
    assert [(r.key, r.value, r.start_line, r.end_line) for r in scan(text).regions] == [
        ("exclude", True, 2, 4), ("generated", "axiom-index", 5, 6), ("output-file", "spec/x-runtime.ttl", 1, 7),
    ]


def test_od1_t6_an_output_file_region_sends_the_blocks_inside_it() -> None:
    text = (_readme(HEAD) + '\n<!-- start: {"output-file": "spec/x-runtime.ttl"} -->\n'
            + _readme("<https://example.org/x-runtime> a owl:Ontology ; owl:versionIRI <https://example.org/x-runtime/0.2.0> .")
            + "\n<!-- end -->\n" + _readme("ex:A a owl:Class ."))
    out = plan(parse_blocks(text), "x", [])
    assert "x-runtime" in out["ontology/x/spec/x-runtime.ttl"]
    assert "ex:A a owl:Class" in out["ontology/x/spec/x.ttl"] and "x-runtime" not in out["ontology/x/spec/x.ttl"]


def test_od1_t7_a_shapes_block_with_an_output_file_takes_no_shapes_argument() -> None:
    text = _mixed_readme(("turtle-shapes", "ex:S1 a sh:NodeShape ."),
                         ("turtle-shapes", '# @output-file "shapes/rules.ttl"\nex:S2 a sh:NodeShape .'))
    out = plan(parse_blocks(text), "x", ["shapes/structural.ttl"])
    assert "ex:S1" in out["ontology/x/shapes/structural.ttl"] and "ex:S2" in out["ontology/x/shapes/rules.ttl"]
    with pytest.raises(ValueError, match="without an output-file"):
        plan(parse_blocks(text), "x", ["shapes/structural.ttl", "shapes/rules.ttl"])


SPEC = "```turtle-spec\nex:A a owl:Class .\n```\n"


@pytest.mark.parametrize("text,message", [
    ('<!-- start: {"exclude": true} -->\ntext\n', "never closed"),
    ("text\n<!-- end -->\n", "closes no region"),
    ('<!-- start: {"colour": "red"} -->\n<!-- end -->\n', "unknown marker key"),
    ('<!-- start: {"exclude": true, "generated": "x"} -->\n<!-- end -->\n', "exactly one key"),
    ('<!-- start: {"exclude": "yes"} -->\n<!-- end -->\n', "takes a bool"),
    ("<!-- start: {exclude} -->\n<!-- end -->\n", "does not parse"),
    ("<!-- start -->\n", "malformed marker"),
    ("<!-- hidden\n```turtle-spec\nex:A rdfs:comment \"a --> b\" .\n```\n-->\n", "end its comment early"),
    ("<!-- hidden\n```mermaid\nflowchart LR\n```\n-->\n", "never hidden"),
    ("<!-- hidden\nsome text\n-->\n", "one extracted fenced block"),
    ("<!-- hidden\n" + SPEC + "more text\n-->\n", "holding only '-->'"),
    ('<!-- start: {"output-file": "spec/y.ttl"} -->\n<!-- hidden: {"output-file": "spec/z.ttl"}\n' + SPEC + "-->\n<!-- end -->\n",
     "given twice"),
    ('<!-- hidden: {"output-file": "spec/y.ttl"}\n```turtle-example\nex:A a ex:B .\n```\n-->\n', "takes no output-file"),
    ("```mermaid\nflowchart LR\n", "Unterminated fence"),
    ("<!-- a comment\nthat never ends\n", "Unterminated HTML comment"),
])
def test_od1_t8_malformed_markers_are_refused(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        scan(text)


def test_od1_t9_both_forms_of_output_file_on_one_block_are_refused() -> None:
    text = ('<!-- start: {"output-file": "spec/y.ttl"} -->\n```turtle-spec\n# @output-file "spec/z.ttl"\n'
            "ex:A a owl:Class .\n```\n<!-- end -->\n")
    with pytest.raises(ValueError, match="given twice"):
        plan(parse_blocks(text), "x", [])


def _layout(numbers: dict[int, str] | None = None, drop: str = "", extra: str = "") -> str:
    titles = list(literate_extract.LAYOUT)
    lines = [f"## {(numbers or {}).get(i, i)}. {t}" for i, t in enumerate(titles, 1) if t != drop]
    return "\n\n".join(lines + ([f"## 14. {extra}"] if extra else [])) + "\n"


def test_od1_t10_the_layout_is_checked_only_once_a_readme_uses_it() -> None:
    assert layout_problems(scan(_layout()).sections) == ([], [])
    errors, warnings = layout_problems(scan(_layout({7: 8})).sections)
    assert errors == [] and warnings == ["line 13: 'Shapes' is numbered 8, the layout numbers it 7"]
    errors, _ = layout_problems(scan(_layout(drop="Release Notes", extra="Appendix")).sections)
    assert errors == ["line 25: section 'Appendix' is not in the layout (ADR-A126)", "section 12, 'Release Notes', is missing"]
    unmigrated = "## 1. Purpose and Scope\n\n## 4. Design Decisions\n"
    assert layout_problems(scan(unmigrated).sections) == ([], [])


def _extractable(text: str) -> str:
    """A layout README with what extraction needs since OD2 and OD3: a header table in section 2, the
    catalogue entry in section 3 and section 6's subsections."""
    text = text.replace("Namespace and Prefixes\n", "Namespace and Prefixes\n\n| Document | Ontology IRI | Version IRI | Imports |\n"
                        "|---|---|---|---|\n| `spec/x.ttl` | <https://example.org/x> | <https://example.org/x/0.1.0> | |\n")
    text = text.replace("Extraction Contract\n", "Extraction Contract\n\n```toml repository-catalogue\n[module]\n```\n")
    regions = '<!-- start: {"generated": "axiom-index"} -->\n<!-- end -->\n'
    text = text.replace("## 4. Overview\n", '## 4. Overview\n\n<!-- start: {"generated": "class-diagram"} -->\n<!-- end -->\n')
    subsections = "".join(f"\n### 6.{i} {t}\n\n{regions if i == 7 else 'None.'}\n" for i, t in enumerate(
        ("Classes", "Object Properties", "Datatype Properties", "Individuals", "Disjointness and Keys", "Other Axioms",
         "Axiom Index"), 1))
    return text.replace("Description Logic Encoding\n", "Description Logic Encoding\n" + subsections)


def test_od1_t11_main_warns_on_a_misnumbered_section_and_fails_on_a_missing_one(tmp_path: Path, capsys) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(_extractable(_layout({7: 8})), encoding="utf-8")
    assert literate_extract.main([str(readme), "--layer", "x", "--root", str(tmp_path)]) == 0
    assert "WARNING" in capsys.readouterr().err
    readme.write_text(_layout(drop="Open Issues"), encoding="utf-8")
    assert literate_extract.main([str(readme), "--layer", "x", "--root", str(tmp_path), "--check"]) == 1
    assert "LAYOUT" in capsys.readouterr().err
