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


LITERATE_LAYERS = [
    ("foundation", ["shapes/constraints.ttl"]),
    ("quantification", ["shapes/constraints.ttl"]),
    ("wording", ["shapes/structural.ttl", "shapes/constraints.ttl"]),
    ("behaviour", ["shapes/structural.ttl"]),
    (
        "instrument",
        ["shapes/structural.ttl", "shapes/constraints.ttl", "shapes/single-expression.ttl"],
    ),
    ("eligibility", ["shapes/structural.ttl", "shapes/constraints.ttl", "shapes/rules.ttl"]),
]


@pytest.mark.parametrize("layer,shapes", LITERATE_LAYERS)
def test_air20_05_every_literate_layer_of_main_is_unchanged(layer: str, shapes: list[str]) -> None:
    readme = ROOT / "ontology" / layer / "README.md"
    kwargs = ["--proofs-root", str(ROOT / "tools" / "proofs"), "--reference-root", str(ROOT / "tools" / "reference")] \
        if layer == "eligibility" else []
    assert literate_extract.main(
        [str(readme), "--layer", layer, "--root", str(ROOT), "--shapes", *shapes, *kwargs, "--check"]
    ) == 0
