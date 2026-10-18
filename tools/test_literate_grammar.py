# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The grammar of a README in the layout of ADR-A126 (slices OD2 and OD3).
Validation Packs: docs/developer/validation/OD2.md and OD3.md. Test IDs are OD2-Tn and OD3-Tn."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF

sys.path.insert(0, str(Path(__file__).resolve().parent))

import literate_extract  # noqa: E402
import literate_grammar as lg  # noqa: E402
import ontology_releases  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FENCE = "```"
X = "https://example.org/x"
CARRY = "https://orcid.org/0000-0002-1825-0097"

HEADER_TABLE = f"""| Document | Ontology IRI | Version IRI | Imports |
|---|---|---|---|
| `spec/x.ttl` | <{X}> | <{X}/0.2.0> | <https://example.org/y/0.1.0> |"""
PREFIX_TABLE = f"""| Prefix | Namespace |
|---|---|
| `ex:` | <{X}#> |"""
PEOPLE_TABLE = f"""| Identifier | Role | Display name |
|---|---|---|
| {CARRY} | creator | Josiah Carberry |"""
ENTRY = f'{FENCE}toml repository-catalogue\n[module]\nkind = "substrate"\nroles = []\n{FENCE}'


def readme(purpose: str = "X models things.", section2: str | None = None, section3: str = ENTRY,
           section6: str = "None.", numbers: dict[int, int] | None = None) -> str:
    """A README in the layout, every section present, with the given contents."""
    body = {
        1: purpose,
        2: section2 if section2 is not None else "\n\n".join([HEADER_TABLE, PREFIX_TABLE, PEOPLE_TABLE]),
        3: section3,
        6: section6,
    }
    parts = ["<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->", "", "# X", ""]
    for number, title in enumerate(literate_extract.LAYOUT, 1):
        parts += [f"## {(numbers or {}).get(number, number)}. {title}", "", body.get(number, "None."), ""]
    return "\n".join(parts)


def compile_readme(text: str, layer: str = "x") -> dict[str, str]:
    result = literate_extract.scan(text)
    return lg.compile_layout(text, result, layer)


def extract(text: str, layer: str = "x") -> dict[str, str]:
    result = literate_extract.scan(text)
    return literate_extract.plan(result.blocks, layer, [], preambles=lg.compile_layout(text, result, layer))


def graph(turtle: str) -> Graph:
    return Graph().parse(data=turtle, format="turtle")


# ---- OD2: sections 1 and 2 --------------------------------------------------------------------


def test_od2_t1_section_2_and_section_1_become_the_ontology_header() -> None:
    out = extract(readme())
    assert list(out) == ["ontology/x/spec/x.ttl"]
    text = out["ontology/x/spec/x.ttl"]
    g = graph(text)
    head = URIRef(X)
    assert (head, RDF.type, OWL.Ontology) in g
    assert (head, OWL.versionIRI, URIRef(f"{X}/0.2.0")) in g
    assert (head, OWL.imports, URIRef("https://example.org/y/0.1.0")) in g
    assert (head, DCTERMS.description, Literal("X models things.")) in g
    assert (head, DCTERMS.creator, URIRef(CARRY)) in g
    assert (DCTERMS.description, RDF.type, OWL.AnnotationProperty) in g
    assert (DCTERMS.creator, RDF.type, OWL.AnnotationProperty) in g
    assert "Josiah Carberry" not in text  # a display name is never written (ADR-A126 decision 10)
    for prefix in ("@prefix ex:", "@prefix owl:", "@prefix xsd:", "@prefix dct:"):
        assert prefix in text
    assert text.startswith(literate_extract.SPDX_TTL)


def test_od2_t2_section_1_becomes_plain_text_with_links_at_the_release_tag() -> None:
    purpose = "\n".join([
        "X models `ex:Thing` and **bold** and *emphasis*, and keeps snake_case_names.",
        "It continues on a second line.",
        "",
        "- one item, see [the policy](../../docs/architecture/ontology-versioning-policy.md)",
        "- another, see [section 4](#4-overview) and [SHACL](https://www.w3.org/TR/shacl/)",
        "",
        '<!-- start: {"exclude": true} -->',
        "This sentence stays in the README only.",
        "<!-- end -->",
    ])
    text = graph(extract(readme(purpose))["ontology/x/spec/x.ttl"]).value(URIRef(X), DCTERMS.description)
    blob = f"{lg.REPOSITORY_BLOB}x-v0.2.0/"
    assert str(text) == (
        "X models ex:Thing and bold and emphasis, and keeps snake_case_names. It continues on a second line.\n\n"
        f"- one item, see the policy ({blob}docs/architecture/ontology-versioning-policy.md)\n"
        f"- another, see section 4 ({blob}ontology/x/README.md#4-overview) and SHACL (https://www.w3.org/TR/shacl/)"
    )


@pytest.mark.parametrize("purpose,message", [
    ("| a | b |\n|---|---|\n| 1 | 2 |", "a table cannot be extracted"),
    ("Text.\n\n### A subheading", "a heading cannot be extracted"),
    ("See ![a figure](figure.png).", "an image cannot be extracted"),
    ("See [outside](../../../../elsewhere.md).", "leaves the repository"),
])
def test_od2_t3_what_section_1_cannot_hold_is_refused(purpose: str, message: str) -> None:
    with pytest.raises(lg.GrammarError, match=message):
        compile_readme(readme(purpose))


def test_od2_t4_the_release_tag_follows_the_versioning_policy_for_every_current_document() -> None:
    iris = set()
    for path in subprocess.run(["git", "ls-files", "ontology/**/spec/*.ttl", "ontology/**/vocab/*.ttl"],
                               cwd=ROOT, capture_output=True, text=True, check=True).stdout.split():
        iris.update(re.findall(r"owl:versionIRI\s+<([^>]+/\d+\.\d+\.\d+)>", (ROOT / path).read_text(encoding="utf-8")))
    assert len(iris) > 20
    for iri in iris:
        name, version = ontology_releases.release_name(iri)
        assert lg.release_tag(iri) == f"{name}-v{version}"


@pytest.mark.parametrize("section2,message", [
    (PREFIX_TABLE, "no header table"),
    (HEADER_TABLE + "\n\n| Colour | Shade |\n|---|---|\n| red | dark |", "only the header, prefix and contributor tables"),
    (HEADER_TABLE.replace("`spec/x.ttl`", "`shapes/x.ttl`"), "not a .ttl file under spec/ or vocab/"),
    (HEADER_TABLE + "\n\n" + PEOPLE_TABLE.replace("creator", "author"), "not creator or contributor"),
    (HEADER_TABLE + "\n\n" + PEOPLE_TABLE.replace(CARRY, "Josiah Carberry"), "not an absolute IRI"),
    (HEADER_TABLE + "\n\n| Prefix | Namespace |\n|---|---|\n| xsd: | <https://example.org/not-xsd#> |", "standard namespace"),
    (HEADER_TABLE + "\n\n" + PREFIX_TABLE + "\n| `ex:` | <https://example.org/other#> |", "not a new prefix"),
    (HEADER_TABLE.replace("/0.2.0>", "/latest>"), "does not end in a version"),
    (HEADER_TABLE + "\n\n" + HEADER_TABLE, "two documents tables"),
])
def test_od2_t5_a_malformed_section_2_is_refused(section2: str, message: str) -> None:
    with pytest.raises(lg.GrammarError, match=message):
        compile_readme(readme(section2=section2))


def _two_documents(version: str) -> str:
    rows = HEADER_TABLE + f"\n| `spec/x-runtime.ttl` | <{X}-runtime> | <{X}-runtime/{version}> | <{X}/0.2.0> |"
    return readme(section2=rows + "\n\n" + PREFIX_TABLE, section6="\n".join([
        f'{FENCE}turtle-spec\n# @output-file "spec/x-runtime.ttl"\nex:R a owl:Class .\n{FENCE}',
        "", f"{FENCE}turtle-spec\nex:A a owl:Class .\n{FENCE}",
    ]))


def test_od2_t6_each_document_opens_with_its_own_header_and_takes_its_blocks() -> None:
    out = extract(_two_documents("0.2.0"))
    main, runtime = out["ontology/x/spec/x.ttl"], out["ontology/x/spec/x-runtime.ttl"]
    assert "ex:A a owl:Class" in main and "ex:R" not in main
    assert runtime.index(f"<{X}-runtime> a owl:Ontology") < runtime.index("ex:R a owl:Class")
    assert "@output-file" not in runtime and "@prefix ex:" in runtime
    assert (URIRef(f"{X}-runtime"), OWL.imports, URIRef(f"{X}/0.2.0")) in graph(runtime)
    with pytest.raises(ValueError, match="in unison"):
        extract(_two_documents("0.3.0"))


def test_od2_t7_a_block_for_a_document_section_2_does_not_name_is_refused() -> None:
    text = readme(section6=f'{FENCE}turtle-spec\n# @output-file "spec/other.ttl"\nex:A a owl:Class .\n{FENCE}')
    with pytest.raises(ValueError, match="section 2's header table does not name"):
        extract(text)


@pytest.mark.parametrize("section3,problem", [
    (ENTRY, None),
    ("No entry.", "found 0, 0 of them in section 3"),
    (ENTRY + "\n\n" + ENTRY, "found 2, 2 of them in section 3"),
])
def test_od2_t8_a_migrated_readme_holds_one_catalogue_entry_in_section_3(section3: str, problem: str | None) -> None:
    result = literate_extract.scan(readme(section3=section3))
    errors, _ = literate_extract.layout_problems(result.sections, result.catalogue_lines)
    assert errors == ([] if problem is None else [next(e for e in errors if problem in e)])


def test_od2_t8b_an_entry_outside_section_3_is_refused() -> None:
    text = readme(section3="No entry here.", section6=ENTRY)
    result = literate_extract.scan(text)
    errors, _ = literate_extract.layout_problems(result.sections, result.catalogue_lines)
    assert any("found 1, 0 of them in section 3" in e for e in errors)


def test_od2_t9_extraction_writes_the_document_and_then_finds_no_drift(tmp_path: Path) -> None:
    source = tmp_path / "README.md"
    source.write_text(readme(section6=f"{FENCE}turtle-spec\nex:A a owl:Class .\n{FENCE}"), encoding="utf-8")
    args = [str(source), "--layer", "x", "--root", str(tmp_path)]
    assert literate_extract.main(args) == 0
    written = (tmp_path / "ontology/x/spec/x.ttl").read_text(encoding="utf-8")
    assert "ex:A a owl:Class" in written
    assert literate_extract.main([*args, "--check"]) == 0
