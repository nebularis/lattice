# SPDX-License-Identifier: MPL-2.0

"""The literate extractor's @output-file directive (ADR-A120)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from literate_extract import parse_blocks, plan  # noqa: E402

HEAD = """@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <https://example.org/x#> .

<https://example.org/x> a owl:Ontology ; owl:versionIRI <https://example.org/x/0.2.0> ."""

RUNTIME = """# @output-file "spec/x-runtime.ttl"
<https://example.org/x-runtime> a owl:Ontology ; owl:versionIRI <https://example.org/x-runtime/{v}> ."""


def _readme(*blocks: str) -> str:
    return "\n\n".join(f"```turtle-spec\n{b}\n```" for b in blocks)


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
